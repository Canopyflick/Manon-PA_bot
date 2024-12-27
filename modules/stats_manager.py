from utils.helpers import emoji_stopwatch, get_random_philosophical_message, escape_markdown_v2, check_chat_owner, PA, add_delete_button, delete_message, BERLIN_TZ
import asyncio, random, re, logging
from utils.db import get_first_name, register_user, fetch_user_stats, Database
from utils.scheduler import send_goals_today, fetch_overdue_goals, fetch_upcoming_goals
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class StatsManager:
    @staticmethod
    async def update_daily_stats():
        """Run at midnight to create daily snapshot"""
        try:
            async with Database.acquire() as conn:
                today = datetime.now(BERLIN_TZ).date()
                users = await conn.fetch("SELECT user_id, chat_id FROM manon_users")
                
                for user in users:
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
                                THEN ROUND(goals_finished::float / (goals_finished + goals_failed) * 100, 2)
                                ELSE NULL 
                            END as completion_rate
                        FROM today_goals
                    """, today, user['user_id'], user['chat_id'])

                    # Insert daily snapshot
                    await conn.execute("""
                        INSERT INTO stats_snapshots (
                            user_id, chat_id, date, goals_set, goals_finished, 
                            goals_failed, score_gained, penalties_incurred, completion_rate
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, user['user_id'], user['chat_id'], today, 
                        daily_metrics['goals_set'], daily_metrics['goals_finished'],
                        daily_metrics['goals_failed'], daily_metrics['score_gained'],
                        daily_metrics['penalties_incurred'], daily_metrics['completion_rate'])

        except Exception as e:
            logging.error(f"Error updating daily stats: {e}")
            raise

    @staticmethod
    async def get_stats_for_period(user_id: int, chat_id: int, days: int) -> Dict:
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
                        COALESCE(AVG(completion_rate), 0) as avg_completion_rate,
                        COALESCE(AVG(goals_set), 0) as avg_daily_goals_set,
                        COALESCE(AVG(goals_finished), 0) as avg_daily_goals_finished
                    FROM stats_snapshots
                    WHERE user_id = $1 
                        AND chat_id = $2
                        AND date BETWEEN $3 AND $4
                """, user_id, chat_id, start_date, end_date)

                # Convert to dict and ensure no None values
                result = dict(stats)
                return {k: v if v is not None else 0 for k, v in result.items()}

        except Exception as e:
            logging.error(f"Error fetching period stats: {e}")
            # Return default values in case of error
            return {
                'total_goals_set': 0,
                'total_goals_finished': 0,
                'total_goals_failed': 0,
                'total_score_gained': 0,
                'total_penalties': 0,
                'avg_completion_rate': 0,
                'avg_daily_goals_set': 0,
                'avg_daily_goals_finished': 0
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
                user_id, chat_id, days
            )
            
        return stats


