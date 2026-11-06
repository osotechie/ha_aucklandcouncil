"""Test production parsing and scheduling with real Home Assistant objects."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant.common import load_fixture

from custom_components.aucklandcouncil.const import FALLBACK_SCAN_INTERVAL
from custom_components.aucklandcouncil.sensor import (
    AucklandCouncilDataUpdateCoordinator,
)

from .const import NOW


@pytest.mark.parametrize(
    ("text", "time", "expected"),
    [
        ("Saturday, 28 March", "07:00", NOW.replace(day=28, hour=7)),
        ("Saturday 28 March", "07:00", NOW.replace(day=28, hour=7)),
        ("Saturday, 28 March", "18:30", NOW.replace(day=28, hour=18, minute=30)),
        (
            "Thursday, 1 January",
            "07:00",
            NOW.replace(year=2027, month=1, day=1, hour=7),
        ),
        ("Friday, 25 December", "07:00", NOW.replace(month=12, day=25, hour=7)),
        ("Saturday, 28 March", "invalid", NOW.replace(day=28, hour=7)),
        ("Monday, 30 February", "07:00", None),
        ("Saturday, 28 March", "25:00", None),
        ("Next week sometime", "07:00", None),
        ("", "07:00", None),
    ],
)
def test_parse_date(
    coordinator: AucklandCouncilDataUpdateCoordinator,
    text: str,
    time: str,
    expected: datetime | None,
) -> None:
    assert coordinator._parse_date_string(text, time) == expected


@pytest.mark.parametrize(
    ("month", "name"),
    enumerate(
        (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        start=1,
    ),
)
def test_parse_all_months(
    coordinator: AucklandCouncilDataUpdateCoordinator, month: int, name: str
) -> None:
    result = coordinator._parse_date_string(f"Monday, 1 {name}", "07:00")
    assert result is not None
    assert (result.month, result.day, result.hour) == (month, 1, 7)
    assert result.tzinfo == NOW.tzinfo


def test_parse_collection_data(
    coordinator: AucklandCouncilDataUpdateCoordinator,
) -> None:
    assert coordinator._parse_collection_data(load_fixture("collections.html")) == {
        "rubbish": NOW.replace(day=28, hour=7),
        "food_scraps": NOW.replace(day=28, hour=7),
        "recycling": NOW.replace(month=4, day=4, hour=7),
    }


@pytest.mark.parametrize("content", ["", "<p>No collection information available</p>"])
def test_parse_missing_data(
    coordinator: AucklandCouncilDataUpdateCoordinator, content: str
) -> None:
    assert coordinator._parse_collection_data(content) == {
        "rubbish": None,
        "food_scraps": None,
        "recycling": None,
    }


def test_parse_missing_recycling(
    coordinator: AucklandCouncilDataUpdateCoordinator,
) -> None:
    content = (
        "Rubbish: <b>Saturday, 28 March</b> Food scraps: <b>Saturday, 28 March</b>"
    )
    data = coordinator._parse_collection_data(content)
    assert data == {
        "rubbish": NOW.replace(day=28, hour=7),
        "food_scraps": NOW.replace(day=28, hour=7),
        "recycling": None,
    }


def test_date_failure_logs_traceback(
    coordinator: AucklandCouncilDataUpdateCoordinator, caplog: pytest.LogCaptureFixture
) -> None:
    with patch(
        "custom_components.aucklandcouncil.sensor.dt_util.now",
        side_effect=RuntimeError("clock failed"),
    ):
        assert coordinator._parse_date_string("Saturday, 28 March", "07:00") is None
    record = next(r for r in caplog.records if "Error parsing date" in r.message)
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], RuntimeError)


def test_collection_failure_does_not_skip_other_types(
    coordinator: AucklandCouncilDataUpdateCoordinator, caplog: pytest.LogCaptureFixture
) -> None:
    date = NOW.replace(day=28, hour=7)
    with patch.object(
        coordinator,
        "_parse_date_string",
        side_effect=[RuntimeError("parser failed"), date, date],
    ):
        assert coordinator._parse_collection_data(load_fixture("collections.html")) == {
            "rubbish": None,
            "food_scraps": date,
            "recycling": date,
        }
    record = next(r for r in caplog.records if "Error parsing rubbish" in r.message)
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], RuntimeError)


def test_poll_interval(coordinator: AucklandCouncilDataUpdateCoordinator) -> None:
    data = {
        "rubbish": NOW.replace(day=28, hour=7),
        "recycling": NOW.replace(month=4, day=4, hour=7),
    }
    expected_poll = NOW.replace(day=29, hour=7)
    assert coordinator._compute_next_update_interval(data) == expected_poll - NOW


def test_minimum_poll_interval(
    coordinator: AucklandCouncilDataUpdateCoordinator, freezer: FrozenDateTimeFactory
) -> None:
    now = NOW.replace(hour=23, minute=45)
    freezer.move_to(now)
    coordinator.collection_time = "00:00"
    assert coordinator._compute_next_update_interval(
        {"rubbish": now + timedelta(minutes=5)}
    ) == timedelta(hours=1)


@pytest.mark.parametrize("value", [None, NOW - timedelta(days=1)])
def test_fallback_poll_interval(
    coordinator: AucklandCouncilDataUpdateCoordinator, value: datetime | None
) -> None:
    assert coordinator._compute_next_update_interval({"rubbish": value}) == timedelta(
        seconds=FALLBACK_SCAN_INTERVAL
    )
