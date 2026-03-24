"""Tests for Auckland Council const.py — property ID validation."""
import pytest

from custom_components.aucklandcouncil.const import validate_property_id


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
