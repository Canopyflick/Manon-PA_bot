from models.stats_snapshot import StatsSnapshot
from utils.helpers import BERLIN_TZ
import asyncio, random, re, logging
from utils.db import get_first_name, fetch_user_stats, Database
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class StatsManager:
    @staticmethod
    async def update_daily_stats(specific_chat_id=None):
        """Run at midnight to create daily snapshot"""
        try:
            logger.info("Starting daily stats update...")
            async with Database.acquire() as conn:
                today = datetime.now(BERLIN_TZ).date()
                users = await conn.fetch("SELECT user_id, chat_id FROM manon_users")
                logger.info(f"Fetched {len(users)} users for daily stats update.")

                for user in users:
                    # If specific_chat_id is provided, process only that chat
                    if specific_chat_id and user['chat_id'] != specific_chat_id:
                        continue
                    logger.info(f"Processing user_id: {user['user_id']}, chat_id: {user['chat_id']}")

                    # Fetch totals snapshot from manon_users
                    user_totals = await conn.fetchrow("""
                        SELECT score, pending_goals, finished_goals, failed_goals
                        FROM manon_users
                        WHERE user_id = $1 AND chat_id = $2
                    """, user['user_id'], user['chat_id'])

                    if not user_totals:
                        logger.warning(f"No totals found for user_id: {user['user_id']}, chat_id: {user['chat_id']}")
                        continue
                    
                    # Calculate daily metrics
                    daily_metrics = await conn.fetchrow("""
                        WITH today_goals AS (
                            SELECT 
                                COUNT(*) FILTER (WHERE status = 'pending') as goals_set,
                                COUNT(*) FILTER (WHERE status = 'archived_done' 
                                    AND DATE(completion_time) = $1) as goals_finished,
                                COUNT(*) FILTER (WHERE status = 'archived_failed' 
                                    AND DATE(completion_time) = $1) as goals_failed,
                                SUM(CASE 
                                    WHEN status = 'archived_done' AND DATE(completion_time) = $1 
                                    THEN goal_value * COALESCE(difficulty_multiplier, 1) * COALESCE(impact_multiplier, 1)
                                    ELSE 0 
                                END) as score_gained,
                                SUM(CASE 
                                    WHEN status = 'archived_failed' AND DATE(completion_time) = $1 
                                    THEN COALESCE(penalty, 0) 
                                    ELSE 0 
                                END) as penalties_incurred
                            FROM manon_goals 
                            WHERE user_id = $2 AND chat_id = $3
                        )
                        SELECT 
                            *,
                            CASE 
                                WHEN (goals_finished + goals_failed) > 0 
                                THEN ROUND(CAST(goals_finished::float / (goals_finished + goals_failed) * 100 AS numeric), 2)
                                ELSE NULL 
                            END as completion_rate
                        FROM today_goals
                    """, today, user['user_id'], user['chat_id'])

                    if not daily_metrics:
                        logger.warning(f"No metrics found for user_id: {user['user_id']}, chat_id: {user['chat_id']}")
                        continue

                    await conn.execute("""
                        INSERT INTO manon_stats_snapshots (
                            user_id, chat_id, date, goals_set, goals_finished, 
                            goals_failed, score_gained, penalties_incurred, completion_rate,
                            score, pending_goals, finished_goals, failed_goals
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """, user['user_id'], user['chat_id'], today, 
                        daily_metrics['goals_set'], daily_metrics['goals_finished'],
                        daily_metrics['goals_failed'], daily_metrics['score_gained'],
                        daily_metrics['penalties_incurred'], daily_metrics['completion_rate'],
                        user_totals['score'], user_totals['pending_goals'],
                        user_totals['finished_goals'], user_totals['failed_goals'])
                    logger.info(f"Inserted stats for user_id: {user['user_id']}, chat_id: {user['chat_id']}")

        except Exception as e:
            logger.error(f"Error updating daily stats: {e}", exc_info=True)
            raise

    @staticmethod
    async def get_stats_for_period(user_id: int, chat_id: int, days: int, label: str) -> StatsSnapshot:
        """Get aggregated stats for a specific period"""
        try:
            async with Database.acquire() as conn:
                end_date = datetime.now(BERLIN_TZ).date()
                start_date = end_date - timedelta(days=days)

                stats = await conn.fetchrow("""
                    SELECT 
                        COALESCE(SUM(goals_set), 0) as total_goals_set,
                        COALESCE(SUM(goals_finished), 0) as total_goals_finished,
                        COALESCE(SUM(goals_failed), 0) as total_goals_failed,
                        COALESCE(SUM(score_gained), 0) as total_score_gained,
                        COALESCE(SUM(penalties_incurred), 0) as total_penalties,
                        COALESCE(AVG(goals_set), 0) as avg_daily_goals_set,
                        COALESCE(AVG(goals_finished), 0) as avg_daily_goals_finished
                    FROM manon_stats_snapshots
                    WHERE user_id = $1 
                        AND chat_id = $2
                        AND date BETWEEN $3 AND $4
                """, user_id, chat_id, start_date, end_date)

                if stats is None:
                    raise ValueError(f"No stats found for user {user_id} in chat {chat_id} for the last {days} days.")

                # Calculate completion rate correctly from period totals
                total_completed_and_failed = stats['total_goals_finished'] + stats['total_goals_failed']
                completion_rate = (
                    (stats['total_goals_finished'] / total_completed_and_failed * 100) 
                    if total_completed_and_failed > 0 else 0
                )

                return StatsSnapshot(
                    total_goals_set=stats['total_goals_set'],
                    total_goals_finished=stats['total_goals_finished'],
                    total_goals_failed=stats['total_goals_failed'],
                    total_score_gained=stats['total_score_gained'],
                    total_penalties=stats['total_penalties'],
                    avg_completion_rate=completion_rate,
                    avg_daily_goals_set=stats['avg_daily_goals_set'],
                    avg_daily_goals_finished=stats['avg_daily_goals_finished'],
                    period_name=label
                )

        except Exception as e:
            logger.error(f"Error fetching period stats: {e}")
            raise

    @staticmethod
    async def get_today_stats(user_id: int, chat_id: int) -> dict:
        """Get statistics for today"""
        try:
            today_start = datetime.now(BERLIN_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            # Convert datetime objects to strings
            today_start_str = today_start.isoformat()
            today_end_str = today_end.isoformat()

            async with Database.acquire() as conn:
                # Update queries to use string parameters
                pending_query = """
                    SELECT COUNT(*) 
                    FROM manon_goals 
                    WHERE user_id = $1 
                    AND chat_id = $2 
                    AND status = 'pending'
                    AND deadline >= $3::timestamptz
                    AND deadline < $4::timestamptz
                """
                pending_count = await conn.fetchval(pending_query, user_id, chat_id, today_start_str, today_end_str)

                # Update other queries similarly...
                completed_query = """
                    SELECT COUNT(*) 
                    FROM manon_goals 
                    WHERE user_id = $1 
                    AND chat_id = $2 
                    AND status = 'archived_done'
                    AND completion_time >= $3::timestamptz
                    AND completion_time < $4::timestamptz
                """
                completed_count = await conn.fetchval(completed_query, user_id, chat_id, today_start_str, today_end_str)

                # Get failed goals
                failed_query = """
                    SELECT COUNT(*) 
                    FROM manon_goals 
                    WHERE user_id = $1 
                    AND chat_id = $2 
                    AND status = 'archived_failed'
                    AND deadline >= $3::timestamptz
                    AND deadline < $4::timestamptz
                """
                failed_count = await conn.fetchval(failed_query, user_id, chat_id, today_start_str, today_end_str)

                # Get points gained today
                points_query = """
                    SELECT COALESCE(SUM(goal_value), 0)
                    FROM manon_goals 
                    WHERE user_id = $1 
                    AND chat_id = $2 
                    AND status = 'archived_done'
                    AND completion_time >= $3::timestamptz
                    AND completion_time < $4::timestamptz
                """
                points_delta = await conn.fetchval(points_query, user_id, chat_id, today_start_str, today_end_str)

                # Get new goals set today
                new_goals_query = """
                    SELECT COUNT(*) 
                    FROM manon_goals 
                    WHERE user_id = $1 
                    AND chat_id = $2 
                    AND set_time >= $3::timestamptz
                    AND set_time < $4::timestamptz
                    AND status NOT IN ('limbo', 'archived_canceled')
                """
                new_goals = await conn.fetchval(new_goals_query, user_id, chat_id, today_start_str, today_end_str)

                return {
                    'pending_goals': pending_count,
                    'completed_goals': completed_count,
                    'failed_goals': failed_count,
                    'points_delta': points_delta,
                    'new_goals_set': new_goals
                }

        except Exception as e:
            logger.error(f"Error getting today's stats: {e}")
            return {
                'pending_goals': 0,
                'completed_goals': 0,
                'failed_goals': 0,
                'points_delta': 0,
                'new_goals_set': 0
            }

    @staticmethod
    async def get_total_stats(user_id: int, chat_id: int) -> dict:
        """Get all-time totals"""
        try:
            async with Database.acquire() as conn:
                # Get total score from manon_users table
                score_query = """
                    SELECT score 
                    FROM manon_users 
                    WHERE user_id = $1 
                    AND chat_id = $2
                """
                total_score = await conn.fetchval(score_query, user_id, chat_id)

                # Get counts for different goal statuses
                stats_query = """
                    SELECT 
                        COUNT(*) FILTER (WHERE status = 'pending') as total_pending,
                        COUNT(*) FILTER (WHERE status = 'archived_done') as total_completed,
                        COUNT(*) FILTER (WHERE status = 'archived_failed') as total_failed,
                        COUNT(*) as total_goals_set
                    FROM manon_goals 
                    WHERE user_id = $1 
                    AND chat_id = $2
                """
                stats = await conn.fetchrow(stats_query, user_id, chat_id)

                return {
                    'total_score': total_score or 0,
                    'total_pending': stats['total_pending'] or 0,
                    'total_completed': stats['total_completed'] or 0,
                    'total_failed': stats['total_failed'] or 0,
                    'total_goals_set': stats['total_goals_set'] or 0
                }

        except Exception as e:
            logger.error(f"Error getting total stats: {e}")
            return {
                'total_score': 0,
                'total_pending': 0,
                'total_completed': 0,
                'total_failed': 0,
                'total_goals_set': 0
            }

    @staticmethod
    async def get_comprehensive_stats(user_id: int, chat_id: int) -> Dict:
        """Get stats for multiple time periods"""
        periods = {
            'week': 7,
            'month': 30,
            'quarter': 90,
            'year': 365
        }
        
        stats = {}
        for period_name, days in periods.items():
            stats[period_name] = await StatsManager.get_stats_for_period(
                user_id, chat_id, days, period_name
            )
            
        return stats


