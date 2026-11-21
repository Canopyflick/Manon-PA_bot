from datetime import date

from features.home.format import format_door, format_sensors


def test_door_shows_the_three_newest_oldest_first():
    text = format_door(
        [
            {"local": "2026-11-21T10:53:28.173+0100", "door": "closed", "what": "closed"},
            {"local": "2026-11-21T10:53:21.325+0100", "door": "open", "what": "opened"},
            {"local": "2026-11-21T10:17:08.090+0100", "door": "closed", "what": "closed"},
        ],
        today=date(2026, 11, 21),
    )
    assert text == "Front door\n10:17 closed\n10:53 open\n10:53 closed"


def test_an_older_door_reading_keeps_its_date():
    text = format_door(
        [{"local": "2026-11-20T22:05:00.000+0100", "door": "open", "what": "opened"}],
        today=date(2026, 11, 21),
    )
    assert text == "Front door\n20 Nov 22:05 open"


def test_sensors_include_the_light_as_on_or_off():
    text = format_sensors(
        {
            "light": "off",
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
            "Light: off",
        ]
    )
