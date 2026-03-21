"""Constants for the Auckland Council integration."""

DOMAIN = "auckland_council"
DEFAULT_NAME = "Auckland Council"
DEFAULT_SCAN_INTERVAL = 86400  # 24 hours

# Configuration keys
CONF_PROPERTY_ID = "property_id"
CONF_COLLECTION_TIME = "collection_time"
CONF_SCAN_INTERVAL = "scan_interval"

# Default property ID (Auckland Council's Main Office)
DEFAULT_PROPERTY_ID = "12344153300"
DEFAULT_COLLECTION_TIME = "07:00"

# Base URL for Auckland Council collection data
BASE_URL = "https://www.aucklandcouncil.govt.nz/en/rubbish-recycling/rubbish-recycling-collections/rubbish-recycling-collection-days/{}.html"

# Collection types
COLLECTION_TYPES = {
    "rubbish": "Rubbish",
    "food_scraps": "Food Scraps", 
    "recycling": "Recycling"
}

# Regex patterns for extracting collection dates from HTML
COLLECTION_PATTERNS = {
    "rubbish": r'Rubbish:\s*<b[^>]*>((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)[^<]*)</b>',
    "food_scraps": r'Food scraps:\s*<b[^>]*>((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)[^<]*)</b>', 
    "recycling": r'Recycling:\s*<b[^>]*>((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)[^<]*)</b>'
}