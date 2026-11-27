from datetime import date

from features.home.format import format_door, format_sensors
from features.home.story import format_story


def test_door_shows_how_long_each_close_had_been_open():
    text = format_door(
        [
            {"local": "2026-11-21T10:53:28.173+0100", "door": "closed", "what": "closed", "open_seconds": 7},
            {"local": "2026-11-21T10:53:21.325+0100", "door": "open", "what": "opened"},
            {"local": "2026-11-21T10:17:08.090+0100", "door": "closed", "what": "closed", "open_seconds": 64},
        ],
        today=date(2026, 11, 21),
    )
    assert text == "Front door\n10:53 closed (7s)\n10:53 open\n10:17 closed (1m 4s)"


def test_an_older_door_reading_keeps_its_date():
    text = format_door(
        [{"local": "2026-11-20T22:05:00.000+0100", "door": "open", "what": "opened"}],
        today=date(2026, 11, 21),
    )
    assert text == "Front door\n20 Nov 22:05 open"


def test_sensors_name_only_the_lights_that_are_on():
    text = format_sensors(
        {
            "light": "off",
            "lights": [
                {"name": "Strip", "on": False},
                {"name": "Study", "on": True},
                {"name": "Hall", "on": False},
            ],
            "sensors": {
                "front_door": {"contact": False},
                "thermometer": {"temperature": 18.1, "humidity": 51.2},
                "airguard": {"co2": 900, "temperature": 19.5, "humidity": 44},
                "motion": {"occupancy": False},
            },
        }
    )
    assert text == "\n".join(
        [
            "Front door: open",
            "Thermometer: 18.1°C, 51%",
            "AirGuard: 900 ppm, 19.5°C, 44%",
            "Motion: clear",
            "Lights: Study",
        ]
    )
    off = format_sensors(
        {
            "lights": [
                {"name": "Strip", "on": False},
                {"name": "Study", "on": False},
            ],
            "sensors": {},
        }
    )
    assert off.endswith("Lights: all off")


def test_a_quiet_day_names_the_two_openings_and_a_steady_room():
    text = format_story(
        {
            "period": "today",
            "since": "2026-11-21T00:00:00+0100",
            "door": {
                "opens": 2,
                "opens_at": [
                    "2026-11-21T10:16:04.609+0100",
                    "2026-11-21T12:14:00.000+0100",
                ],
                "busiest_day": "2026-11-21",
                "busiest_count": 2,
                "log_starts": "2026-11-21T10:11:34.907+0100",
            },
            "thermometer": {
                "min_temperature": 17.1,
                "max_temperature": 17.6,
                "min_humidity": 48,
                "max_humidity": 52,
                "min_temperature_on": "2026-11-21",
                "max_temperature_on": "2026-11-21",
            },
            "airguard": {"max_co2": 640, "max_co2_on": "2026-11-21", "max_co2_at": "2026-11-21T14:20:00.000+0100"},
        }
    )
    assert text == (
        "Today. The front door opened twice, at 10:16 and 12:14. "
        "Indoors held steady around 17.6°C. The air peaked at 640 ppm at 14:20."
    )


def test_the_fridge_is_counted_apart_from_the_front_door():
    text = format_story(
        {
            "period": "today",
            "since": "2026-11-27T00:00:00+0100",
            "door": {"opens": 0, "opens_at": [], "log_starts": "2026-11-21T10:11:34.907+0100"},
            "fridge": {
                "opens": 2,
                "opens_at": [
                    "2026-11-27T08:10:00.000+0100",
                    "2026-11-27T13:05:00.000+0100",
                ],
                "log_starts": "2026-11-27T08:10:00.000+0100",
            },
            "thermometer": None,
            "airguard": None,
        }
    )
    assert "The front door stayed shut." in text
    assert "The fridge was opened twice, at 08:10 and 13:05." in text


def test_a_busy_stuffy_week_names_the_days():
    text = format_story(
        {
            "period": "week",
            "since": "2026-11-16T00:00:00+0100",
            "door": {
                "opens": 8,
                "opens_at": [],
                "busiest_day": "2026-11-18",
                "busiest_count": 5,
                "log_starts": "2026-11-16T08:00:00.000+0100",
            },
            "thermometer": {
                "min_temperature": 16.0,
                "max_temperature": 19.5,
                "min_humidity": 40,
                "max_humidity": 55,
                "min_temperature_on": "2026-11-16",
                "max_temperature_on": "2026-11-18",
            },
            "airguard": {"max_co2": 1250, "max_co2_on": "2026-11-17", "max_co2_at": "2026-11-17T09:00:00+0100"},
        }
    )
    assert text == (
        "This week. The front door opened 8 times, most of them on Wednesday. "
        "The coldest was 16.0°C on Monday and the warmest 19.5°C on Wednesday. "
        "Humidity ran from 40% to 55%. The air peaked at 1250 ppm on Tuesday at 09:00 and got stuffy."
    )


def test_a_month_says_when_the_door_log_actually_starts():
    text = format_story(
        {
            "period": "month",
            "since": "2026-11-01T00:00:00+0100",
            "door": {
                "opens": 0,
                "opens_at": [],
                "busiest_day": None,
                "busiest_count": 0,
                "log_starts": "2026-11-21T10:11:34.907+0100",
            },
            "thermometer": None,
            "airguard": None,
        }
    )
    assert text == "This month. The door log starts on 21 Nov. The front door stayed shut."
