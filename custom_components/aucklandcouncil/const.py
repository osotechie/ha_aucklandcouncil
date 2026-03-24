"""Constants for the Auckland Council integration."""

import re

DOMAIN = "aucklandcouncil"
DEFAULT_NAME = "Auckland Council"
DEFAULT_SCAN_INTERVAL = 86400  # 24 hours
DEFAULT_COLLECTION_TIME = "07:00"

# Configuration keys
CONF_PROPERTY_ID = "property_id"
CONF_COLLECTION_TIME = "collection_time"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_VERBOSE_LOGGING = "verbose_logging"

# Property ID validation
PROPERTY_ID_MIN_LENGTH = 5
PROPERTY_ID_MAX_LENGTH = 15
_PROPERTY_ID_PATTERN = re.compile(
    r"^\d{" + str(PROPERTY_ID_MIN_LENGTH) + "," + str(PROPERTY_ID_MAX_LENGTH) + "}$"
)


def validate_property_id(property_id: str) -> bool:
    """Return True if property_id is a numeric string between 5 and 15 digits."""
    return bool(_PROPERTY_ID_PATTERN.match(property_id))


# Base URL for Auckland Council collection data
BASE_URL = "https://www.aucklandcouncil.govt.nz/en/rubbish-recycling/rubbish-recycling-collections/rubbish-recycling-collection-days/{}.html"

# HTTP request headers — the council site returns 406 for non-browser User-Agent strings
REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Collection types
COLLECTION_TYPES = {
    "rubbish": "Rubbish",
    "food_scraps": "Food Scraps",
    "recycling": "Recycling",
}

# Regex patterns for extracting collection dates from HTML
COLLECTION_PATTERNS = {
    "rubbish": r"Rubbish:\s*<b[^>]*>((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)[^<]*)</b>",
    "food_scraps": r"Food scraps:\s*<b[^>]*>((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)[^<]*)</b>",
    "recycling": r"Recycling:\s*<b[^>]*>((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)[^<]*)</b>",
}
