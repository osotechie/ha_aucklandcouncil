"""Tests for Auckland Council const.py — property ID validation and constants."""

import re

from custom_components.aucklandcouncil.const import (
    REQUEST_HEADERS,
    validate_property_id,
)


class TestValidatePropertyId:
    """Tests for validate_property_id()."""

    # --- Valid IDs ---

    def test_valid_5_digits(self):
        assert validate_property_id("12345") is True

    def test_valid_11_digits(self):
        assert validate_property_id("12344153300") is True

    def test_valid_15_digits(self):
        assert validate_property_id("123456789012345") is True

    def test_valid_all_zeros(self):
        assert validate_property_id("00000") is True

    # --- Too short ---

    def test_too_short_4_digits(self):
        assert validate_property_id("1234") is False

    def test_too_short_1_digit(self):
        assert validate_property_id("1") is False

    # --- Too long ---

    def test_too_long_16_digits(self):
        assert validate_property_id("1234567890123456") is False

    # --- Non-numeric ---

    def test_letters(self):
        assert validate_property_id("abcdefg") is False

    def test_alphanumeric(self):
        assert validate_property_id("1234abc") is False

    def test_special_characters(self):
        assert validate_property_id("12345!@#") is False

    def test_spaces(self):
        assert validate_property_id("123 456") is False

    def test_leading_space(self):
        assert validate_property_id(" 12345") is False

    def test_trailing_space(self):
        assert validate_property_id("12345 ") is False

    # --- Edge cases ---

    def test_empty_string(self):
        assert validate_property_id("") is False

    def test_newline_injection(self):
        assert validate_property_id("12345\n67890") is False

    # --- Injection attempts ---

    def test_sql_injection(self):
        assert validate_property_id("12345; DROP TABLE--") is False

    def test_url_injection(self):
        assert validate_property_id("../../../etc/passwd") is False

    def test_html_injection(self):
        assert validate_property_id("<script>alert(1)</script>") is False

    def test_url_path_traversal(self):
        assert validate_property_id("12345/../admin") is False


class TestRequestHeaders:
    """Tests for REQUEST_HEADERS — Auckland Council rejects non-browser User-Agents with 406."""

    def test_accept_header_present(self):
        assert "Accept" in REQUEST_HEADERS

    def test_accept_header_includes_text_html(self):
        assert "text/html" in REQUEST_HEADERS["Accept"]

    def test_user_agent_present(self):
        assert "User-Agent" in REQUEST_HEADERS

    def test_user_agent_is_browser_style(self):
        ua = REQUEST_HEADERS["User-Agent"]
        assert "Mozilla" in ua or "AppleWebKit" in ua or "Chrome" in ua

    def test_user_agent_not_custom_string(self):
        """Ensure we don't regress to a custom UA that the council server rejects."""
        ua = REQUEST_HEADERS["User-Agent"].lower()
        assert "homeassistant" not in ua
        assert "aucklandcouncil" not in ua

    def test_user_agent_uses_current_reduced_chrome_format(self):
        match = re.fullmatch(
            r"Mozilla/5\.0 \(Windows NT 10\.0; Win64; x64\) "
            r"AppleWebKit/537\.36 \(KHTML, like Gecko\) "
            r"Chrome/(\d+)\.0\.0\.0 Safari/537\.36",
            REQUEST_HEADERS["User-Agent"],
        )
        assert match is not None
        assert int(match.group(1)) >= 158

    def test_browser_client_hints_and_navigation_headers_present(self):
        """Auckland Council Fastly WAF rejects requests without Client Hints with 406."""
        assert "Accept-Language" in REQUEST_HEADERS
        assert "Sec-CH-UA" in REQUEST_HEADERS
        assert "Sec-Fetch-Site" in REQUEST_HEADERS
