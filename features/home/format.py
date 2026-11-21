"""Turn a house readings payload into the two chat replies."""

from datetime import date, datetime


def format_door(events: list[dict], today: date) -> str:
    if not events:
        return "No door readings yet."
    lines = ["Front door"]
    for event in reversed(events):
        when = _when(event.get("local"), today)
        door = event.get("door")
        label = door if door in ("open", "closed") else event.get("what") or "unknown"
        lines.append(f"{when} {label}")
    return "\n".join(lines)


def format_sensors(payload: dict) -> str:
    sensors = payload.get("sensors") if isinstance(payload.get("sensors"), dict) else {}
    door = sensors.get("front_door") if isinstance(sensors.get("front_door"), dict) else {}
    thermo = sensors.get("thermometer") if isinstance(sensors.get("thermometer"), dict) else {}
    air = sensors.get("airguard") if isinstance(sensors.get("airguard"), dict) else {}
    motion = sensors.get("motion") if isinstance(sensors.get("motion"), dict) else {}
    return "\n".join(
        [
            f"Front door: {_contact(door.get('contact'))}",
            f"Thermometer: {_climate(thermo.get('temperature'), thermo.get('humidity'))}",
            f"AirGuard: {_air(air)}",
            f"Motion: {_motion(motion.get('occupancy'))}",
            f"Light: {_light(payload.get('light'))}",
        ]
    )


def _contact(value: object) -> str:
    if value is True:
        return "closed"
    if value is False:
        return "open"
    return "unknown"


def _motion(value: object) -> str:
    if value is True:
        return "occupied"
    if value is False:
        return "clear"
    return "unknown"


def _light(value: object) -> str:
    if value in ("on", "off"):
        return value
    return "unknown"


def _climate(temperature: object, humidity: object) -> str:
    if not isinstance(temperature, (int, float)):
        return "unknown"
    text = f"{temperature:.1f}°C"
    if isinstance(humidity, (int, float)):
        text += f", {humidity:.0f}%"
    return text


def _air(reading: dict) -> str:
    co2 = reading.get("co2")
    if not isinstance(co2, (int, float)):
        return "unknown"
    text = f"{co2:.0f} ppm"
    climate = _climate(reading.get("temperature"), reading.get("humidity"))
    if climate != "unknown":
        text += f", {climate}"
    return text


def _when(value: object, today: date) -> str:
    if not isinstance(value, str):
        return "?"
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        return "?"
    if parsed.date() == today:
        return parsed.strftime("%H:%M")
    return parsed.strftime("%d %b %H:%M")
