"""Constants for the Auckland Council integration."""

import re

DOMAIN = "aucklandcouncil"
DEFAULT_NAME = "Auckland Council"
FALLBACK_SCAN_INTERVAL = 86400  # 24 hours — retry stale or incomplete schedules
MAX_SCAN_INTERVAL = 7 * 86400
COLLECTION_DATE_PAST_DAYS = 7
COLLECTION_DATE_FUTURE_DAYS = 35
DEFAULT_COLLECTION_TIME = "07:00"
STORAGE_KEY = "aucklandcouncil_collection_data"
STORAGE_VERSION = 1

# Configuration keys
CONF_PROPERTY_ID = "property_id"
CONF_COLLECTION_TIME = "collection_time"
CONF_PROXY_URL = "proxy_url"
CONF_PROXY_TOKEN = "proxy_token"

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

# HTTP request headers — Auckland Council's Fastly WAF returns 406 if browser Client Hints
# or navigation headers are missing, or for non-browser User-Agent strings.
# Chrome's reduced UA exposes only the major version; other version tokens are frozen.
REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-NZ,en;q=0.9",
    "Sec-CH-UA": '"Chromium";v="158", "Not_A Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36",
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
