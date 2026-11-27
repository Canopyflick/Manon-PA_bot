"""Short house stories for a day, a week, and a month."""

from datetime import date, datetime

_TITLES = {"today": "Today", "week": "This week", "month": "This month"}


def format_story(summary: dict) -> str:
    period = summary.get("period") if isinstance(summary.get("period"), str) else ""
    title = _TITLES.get(period, "This period")
    sentences = [
        _coverage(summary),
        _door(summary, period),
        _temperature(summary, period),
        _humidity(summary),
        _air(summary, period),
    ]
    body = " ".join(sentence for sentence in sentences if sentence)
    if not body:
        return f"{title}. Nothing has been logged yet."
    return f"{title}. {body}"


def _door(summary: dict, period: str) -> str:
    door = summary.get("door") if isinstance(summary.get("door"), dict) else {}
    opens = door.get("opens") if isinstance(door.get("opens"), int) else 0
    if opens == 0:
        return "The front door stayed shut."
    if opens <= 2:
        times = _open_labels(door.get("opens_at"), period)
        if opens == 1 and times:
            return f"The front door opened once, at {times[0]}."
        if opens == 2 and len(times) == 2:
            return f"The front door opened twice, at {times[0]} and {times[1]}."
    sentence = f"The front door opened {opens} times"
    busiest = door.get("busiest_day")
    count = door.get("busiest_count")
    if period in ("week", "month") and isinstance(busiest, str) and isinstance(count, int) and count > 0:
        day = _weekday(busiest)
        if count == opens:
            sentence += f", all on {day}"
        else:
            sentence += f", most of them on {day}"
    return sentence + "."


def _temperature(summary: dict, period: str) -> str:
    reading = summary.get("thermometer") if isinstance(summary.get("thermometer"), dict) else None
    if reading is None:
        return ""
    low = reading.get("min_temperature")
    high = reading.get("max_temperature")
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
        return ""
    if high - low < 1:
        return f"Indoors held steady around {high:.1f}°C."
    if period == "today" or reading.get("min_temperature_on") == reading.get("max_temperature_on"):
        return f"Indoors ran from {low:.1f}°C to {high:.1f}°C."
    cold = _weekday(reading.get("min_temperature_on"))
    warm = _weekday(reading.get("max_temperature_on"))
    if not cold or not warm:
        return f"Indoors ran from {low:.1f}°C to {high:.1f}°C."
    return f"The coldest was {low:.1f}°C on {cold} and the warmest {high:.1f}°C on {warm}."


def _humidity(summary: dict) -> str:
    reading = summary.get("thermometer") if isinstance(summary.get("thermometer"), dict) else None
    if reading is None:
        return ""
    low = reading.get("min_humidity")
    high = reading.get("max_humidity")
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
        return ""
    if high - low < 10:
        return ""
    return f"Humidity ran from {low:.0f}% to {high:.0f}%."


def _air(summary: dict, period: str) -> str:
    reading = summary.get("airguard") if isinstance(summary.get("airguard"), dict) else None
    if reading is None:
        return ""
    peak = reading.get("max_co2")
    if not isinstance(peak, (int, float)):
        return ""
    sentence = f"The air peaked at {peak:.0f} ppm"
    clock = _clock(reading.get("max_co2_at"))
    if period in ("week", "month"):
        day = _weekday(reading.get("max_co2_on"))
        if day and clock:
            sentence += f" on {day} at {clock}"
        elif day:
            sentence += f" on {day}"
        elif clock:
            sentence += f" at {clock}"
    elif clock:
        sentence += f" at {clock}"
    if peak >= 1000:
        sentence += " and got stuffy"
    return sentence + "."


def _coverage(summary: dict) -> str:
    door = summary.get("door") if isinstance(summary.get("door"), dict) else {}
    started = door.get("log_starts")
    since = summary.get("since")
    if not isinstance(started, str) or not isinstance(since, str) or len(started) < 10 or len(since) < 10:
        return ""
    if started[:10] <= since[:10]:
        return ""
    return f"The door log starts on {_day_month(started[:10])}."


def _clock(value: object) -> str:
    if isinstance(value, str) and len(value) >= 16:
        return value[11:16]
    return ""


def _open_labels(values: object, period: str) -> list[str]:
    if not isinstance(values, list):
        return []
    labels = []
    for value in values:
        if not isinstance(value, str) or len(value) < 16:
            continue
        clock = value[11:16]
        if period == "today":
            labels.append(clock)
        else:
            labels.append(f"{_weekday(value[:10])} {clock}")
    return labels


def _weekday(value: object) -> str:
    if not isinstance(value, str) or len(value) < 10:
        return ""
    try:
        return date.fromisoformat(value[:10]).strftime("%A")
    except ValueError:
        return ""


def _day_month(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return value
    return f"{parsed.day} {parsed.strftime('%b')}"
