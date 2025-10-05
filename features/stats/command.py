# features/stats/command.py
from features.stats.stats_manager import StatsManager
from features.stats.nonsense import nonsense
from utils.db import get_first_name
from telegram_helpers.delete_message import add_delete_button
from utils.session_avatar import PA


async def stats_command(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    first_name = await get_first_name(context, user_id, chat_id)

    # Get comprehensive stats
    stats = await StatsManager.get_comprehensive_stats(user_id, chat_id)

    def get_trend_arrow(current, baseline, metric_name):
        """Returns emoji arrow based on comparison with weekly baseline"""
        if current == baseline:
            return "→"
        # Invert logic for penalties (lower is better)
        if metric_name in ['Penalties/Day', 'Penalties/Week']:
            return "🟢↑" if current < baseline else "🔴↓"
        return "🟢↑" if current > baseline else "🔴↓"

    def format_metric_line(metric_name: str, metric_values: dict, periods: list) -> str:
        """Formats a single metric line with fixed-width columns"""
        values = []
        for period in periods:
            value = metric_values.get(period, 0) or 0
            trend = get_trend_arrow(value, metric_values['week'], metric_name)
            values.append(f"{value:7.1f}{trend}")
        return f"{metric_name:<14} {' | '.join(values)}"

    # Get both today's and total stats
    today_stats = await StatsManager.get_today_stats(user_id, chat_id)
    total_stats = await StatsManager.get_total_stats(user_id, chat_id)

    # Calculate today's completion rate
    today_completed = today_stats.get('completed_goals', 0)
    today_failed = today_stats.get('failed_goals', 0)
    today_total = today_completed + today_failed
    today_completion_rate = (today_completed / today_total * 100) if today_total > 0 else 0

    # Calculate all-time completion rate
    total_completed = total_stats['total_completed']
    total_failed = total_stats['total_failed']
    total_all = total_completed + total_failed
    total_completion_rate = (total_completed / total_all * 100) if total_all > 0 else 0

    # Combined metrics dictionary
    combined_metrics = {
        'Points': {
            'today': today_stats.get('points_delta', 0),
            'total': total_stats['total_score']
        },
        'Pending': {
            'today': today_stats.get('pending_goals', 0),
            'total': total_stats.get('total_pending', 0)
        },
        'Completed': {
            'today': today_completed,
            'total': total_completed
        },
        'Failed': {
            'today': today_failed,
            'total': total_failed
        },
        'New Goals': {
            'today': today_stats.get('new_goals_set', 0),
            'total': total_stats.get('total_goals_set', 0)
        },
        'Success Rate': {
            'today': today_completion_rate,
            'total': total_completion_rate
        }
    }

    # Format message
    # create separate functions for generating different parts of the message
    message_parts = [
        f"<b>Stats for {first_name}</b> 👤{PA}\n",
        "<b>📊 Today & Total</b>",
        "<pre>",
        "Metric          Today | All-time",
        "──────────────────────────────"
    ]

    # Add combined metrics
    for metric_name, values in combined_metrics.items():
        if metric_name == 'Success Rate':
            message_parts.append(
                f"{metric_name:<14} {values['today']:6.1f}% | {values['total']:6.1f}%"
            )
        else:
            message_parts.append(
                f"{metric_name:<14} {values['today']:7.1f} | {values['total']:7.1f}"
            )

    message_parts.extend(["</pre>"])

    # Trends section
    message_parts.extend([
        "<b>📈 Trends</b>",
        "<pre>",
        "Metric                7d | 30d",
        "──────────────────────────────"
    ])

    # Calculate weekly averages for each period
    periods = ['week', 'month', 'quarter', 'year']
    days_in_period = {'week': 7, 'month': 30, 'quarter': 90, 'year': 365}
    weeks_in_period = {'week': 1, 'month': 30/7, 'quarter': 90/7, 'year': 365/7}

    metrics = {
        'Goals/Week': {
            period: (stats[period].total_goals_finished + stats[period].total_goals_failed) / weeks_in_period[period]
            for period in periods
        },
        'Points/Day': {
            period: stats[period].total_score_gained / days_in_period[period]
            for period in periods
        },
        'Penalties/Day': {
            period: stats[period].total_penalties / days_in_period[period]
            for period in periods
        },
        'Complete %': {
            period: stats[period].avg_completion_rate
            for period in periods
        }
    }

    # Add metrics for week/month
    for metric_name, metric_data in metrics.items():
        message_parts.append(format_metric_line(
            metric_name,
            metric_data,
            ['week', 'month']
        ))

    message_parts.extend([
        "",
        "                      90d | 365d",
        "──────────────────────────────"
    ])

    # Add metrics for quarter/year
    for metric_name, metric_data in metrics.items():
        message_parts.append(format_metric_line(
            metric_name,
            metric_data,
            ['quarter', 'year']
        ))

    message_parts.extend([
        "</pre>",
        f"\n<i>{await nonsense(update, context, first_name)}</i>"
    ])

    stats_message = await update.message.reply_text(
        "\n".join(message_parts),
        parse_mode="HTML"
    )
    await add_delete_button(update, context, stats_message.message_id)
