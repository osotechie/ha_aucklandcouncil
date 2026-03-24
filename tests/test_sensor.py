"""Tests for Auckland Council sensor.py — date parsing and HTML data extraction."""
import pytest
from datetime import datetime, timezone, timedelta
import re
from custom_components.aucklandcouncil.const import COLLECTION_PATTERNS


# --------------------------------------------------------------------------- #
# Reusable: standalone copies of the pure parsing logic from sensor.py        #
# These avoid needing a full coordinator instance for unit testing.           #
# --------------------------------------------------------------------------- #

def _parse_date_string(date_text: str, collection_time: str, now: datetime) -> datetime | None:
    """Standalone version of AucklandCouncilDataUpdateCoordinator._parse_date_string."""
    try:
        date_pattern = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)'
        match = re.search(date_pattern, date_text, re.IGNORECASE)
        if not match:
            return None

        day = int(match.group(1))
        month_name = match.group(2).title()
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12,
        }
        month = month_map.get(month_name)
        if not month:
            return None

        try:
            time_parts = collection_time.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        except (ValueError, IndexError):
            hour, minute = 7, 0

        year = now.year
        try:
            collection_date = datetime(year, month, day, hour, minute, tzinfo=now.tzinfo)
        except ValueError:
            return None

        if collection_date < now - timedelta(days=1):
            year += 1
            try:
                collection_date = datetime(year, month, day, hour, minute, tzinfo=now.tzinfo)
            except ValueError:
                return None

        return collection_date
    except Exception:
        return None


def _parse_collection_data(content: str) -> dict[str, str | None]:
    """Extract raw date strings from HTML using COLLECTION_PATTERNS (no datetime conversion)."""
    data = {}
    for collection_type, pattern in COLLECTION_PATTERNS.items():
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        data[collection_type] = match.group(1).strip() if match else None
    return data


# --------------------------------------------------------------------------- #
# Sample HTML fragments that mimic the Auckland Council page structure        #
# --------------------------------------------------------------------------- #

SAMPLE_HTML_ALL = """
<div class="collection-info">
    Rubbish: <b class="date">Friday, 28 March</b><br>
    Food scraps: <b class="date">Friday, 28 March</b><br>
    Recycling: <b class="date">Friday, 4 April</b>
</div>
"""

SAMPLE_HTML_MISSING_RECYCLING = """
<div class="collection-info">
    Rubbish: <b class="date">Monday, 31 March</b><br>
    Food scraps: <b class="date">Monday, 31 March</b>
</div>
"""

SAMPLE_HTML_NONE = """
<div class="no-data">
    <p>Sorry, no collection information available.</p>
</div>
"""


# =========================================================================== #
#  Test suite: _parse_date_string                                              #
# =========================================================================== #

class TestParseDateString:

    # Freeze "now" to a known date so tests are deterministic
    NOW = datetime(2026, 3, 24, 12, 0, tzinfo=timezone(timedelta(hours=13)))  # NZDT

    def test_standard_format(self):
        result = _parse_date_string("Friday, 28 March", "07:00", self.NOW)
        assert result is not None
        assert result.month == 3
        assert result.day == 28
        assert result.hour == 7
        assert result.minute == 0
        assert result.year == 2026

    def test_no_comma_variant(self):
        result = _parse_date_string("Friday 28 March", "07:00", self.NOW)
        assert result is not None
        assert result.day == 28
        assert result.month == 3

    def test_custom_collection_time(self):
        result = _parse_date_string("Friday, 28 March", "18:30", self.NOW)
        assert result is not None
        assert result.hour == 18
        assert result.minute == 30

    def test_past_date_rolls_to_next_year(self):
        result = _parse_date_string("Wednesday, 1 January", "07:00", self.NOW)
        assert result is not None
        assert result.year == 2027  # Jan 1 is in the past relative to Mar 24

    def test_future_date_stays_current_year(self):
        result = _parse_date_string("Wednesday, 25 December", "07:00", self.NOW)
        assert result is not None
        assert result.year == 2026

    def test_invalid_format_returns_none(self):
        result = _parse_date_string("Next week sometime", "07:00", self.NOW)
        assert result is None

    def test_empty_string_returns_none(self):
        result = _parse_date_string("", "07:00", self.NOW)
        assert result is None

    def test_bad_collection_time_falls_back(self):
        result = _parse_date_string("Friday, 28 March", "invalid", self.NOW)
        assert result is not None
        assert result.hour == 7
        assert result.minute == 0

    def test_invalid_day_returns_none(self):
        # February 30 doesn't exist
        result = _parse_date_string("Monday, 30 February", "07:00", self.NOW)
        assert result is None

    def test_all_months_recognised(self):
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        for month in months:
            result = _parse_date_string(f"Monday, 1 {month}", "07:00", self.NOW)
            # Some combos may be past and roll over, but should not be None
            # (except Feb 30 etc, but day=1 is always valid)
            assert result is not None, f"Failed for {month}"


# =========================================================================== #
#  Test suite: _parse_collection_data (HTML extraction)                        #
# =========================================================================== #

class TestParseCollectionData:

    def test_all_types_found(self):
        data = _parse_collection_data(SAMPLE_HTML_ALL)
        assert data["rubbish"] == "Friday, 28 March"
        assert data["food_scraps"] == "Friday, 28 March"
        assert data["recycling"] == "Friday, 4 April"

    def test_missing_recycling(self):
        data = _parse_collection_data(SAMPLE_HTML_MISSING_RECYCLING)
        assert data["rubbish"] == "Monday, 31 March"
        assert data["food_scraps"] == "Monday, 31 March"
        assert data["recycling"] is None

    def test_no_data_page(self):
        data = _parse_collection_data(SAMPLE_HTML_NONE)
        assert data["rubbish"] is None
        assert data["food_scraps"] is None
        assert data["recycling"] is None

    def test_empty_html(self):
        data = _parse_collection_data("")
        assert all(v is None for v in data.values())

    def test_all_three_keys_present(self):
        data = _parse_collection_data(SAMPLE_HTML_ALL)
        assert set(data.keys()) == {"rubbish", "food_scraps", "recycling"}
