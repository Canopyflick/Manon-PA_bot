# features/weather/monitoring.py
import requests
import logging
from datetime import datetime, timedelta
from utils.helpers import BERLIN_TZ

logger = logging.getLogger(__name__)

LEIPZIG_LAT = 51.34
LEIPZIG_LON = 12.38


async def get_weather_change_message() -> str:
    """
    Fetch yesterday's, today's, and 4-days-from-now max temperatures for Leipzig.
    Returns a formatted remark if significant temperature swings are detected,
    or an empty string if nothing noteworthy.

    Thresholds:
    - Today vs yesterday difference >= 4°C
    - 4 days from now vs yesterday difference > 9°C
    """
    try:
        today = datetime.now(BERLIN_TZ).date()
        yesterday = today - timedelta(days=1)
        target_day = today + timedelta(days=4)

        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LEIPZIG_LAT,
                "longitude": LEIPZIG_LON,
                "daily": "temperature_2m_max",
                "past_days": 1,
                "forecast_days": 5,
                "timezone": "Europe/Berlin",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        dates = data["daily"]["time"]
        temps = data["daily"]["temperature_2m_max"]
        temp_lookup = dict(zip(dates, temps))

        temp_yesterday = temp_lookup.get(yesterday.isoformat())
        temp_today = temp_lookup.get(today.isoformat())
        temp_target = temp_lookup.get(target_day.isoformat())

        if temp_yesterday is None or temp_today is None:
            logger.warning(f"Weather data missing: yesterday={temp_yesterday}, today={temp_today}")
            return ""

        parts = []

        # Check 1: today vs yesterday (>= 4°C)
        diff_today = temp_today - temp_yesterday
        if abs(diff_today) >= 4:
            direction = "warmer" if diff_today > 0 else "colder"
            parts.append(
                f"Today is {abs(diff_today):.0f}°C {direction} than yesterday "
                f"({temp_yesterday:.0f}°C → {temp_today:.0f}°C)"
            )

        # Check 2: 4 days from now vs yesterday (> 9°C)
        if temp_target is not None:
            diff_target = temp_target - temp_yesterday
            if abs(diff_target) > 9:
                direction = "warmer" if diff_target > 0 else "colder"
                day_name = target_day.strftime("%A")
                parts.append(
                    f"{day_name} will be {abs(diff_target):.0f}°C {direction} "
                    f"than yesterday ({temp_yesterday:.0f}°C → {temp_target:.0f}°C)"
                )

        if not parts:
            return ""

        return "\n\n🌡️ " + "\n🌡️ ".join(parts)

    except Exception as e:
        logger.error(f"Error in get_weather_change_message: {e}")
        return ""
