# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2026.04.10] - 2026-04-10

### Fixed
- **ConfigEntryNotReady raised in forwarded platform** — Moved coordinator creation and `async_config_entry_first_refresh()` from `sensor.py` into `__init__.py` so the initial data fetch occurs before `async_forward_entry_setups`. Previously, a failed first refresh raised `ConfigEntryNotReady` inside the sensor platform, which HA does not handle correctly at that stage

## [2026.04.09] - 2026-04-09

### Changed
- **Dynamic polling** — The coordinator now computes the next poll time based on collection dates, scheduling the next fetch for the day after the earliest upcoming collection. This reduces requests from ~1/day to ~1/week
- **Removed user-configurable scan interval** — The `scan_interval` config option has been removed from the setup and options flows since polling is now automatic. Existing config entries with a stored value are unaffected (the value is simply ignored)
- **Renamed `DEFAULT_SCAN_INTERVAL` to `FALLBACK_SCAN_INTERVAL`** — Clarifies that the 24-hour interval is only used until the first successful data fetch
- **Replaced `verbose_logging` toggle with native HA debug logging** — Removed the custom `verbose_logging` config option from the setup and options flows. All diagnostic messages now use standard `_LOGGER.debug()` calls, which are controlled via Home Assistant's built-in "Enable debug logging" button (Settings → Devices & Services → integration menu) or `logger` configuration in `configuration.yaml`

### Fixed
- **Excessive proxy requests** — Switched sensor base class from `SensorEntity` to `CoordinatorEntity`, which sets `should_poll = False`. Previously HA's default ~30s entity polling called `async_request_refresh()` on every cycle, bypassing the coordinator's update interval and causing ~2-3 HTTP requests per minute
- **Redundant startup request** — Removed the `_validate_property_id()` HTTP call from `__init__.py` that duplicated the coordinator's first refresh, eliminating a second proxy hit on every startup and options-change reload

### Temporary Addition
- **Cloudflare Worker proxy support** — Optional proxy URL and token can be configured to route requests through a Cloudflare Worker, providing a fallback when direct requests are blocked by Auckland Council rate limiting. *If you get HTTP 406 errors please contact me for more information.*


## [2026.03.25] - 2026-03-25

### Changed
- **HACS store readiness** — Added `country: "NZ"` to `hacs.json` for country-specific discovery
- **Improved Property ID labelling** — Config flow now shows "Property ID (Assessment Number)" to match Auckland Council's terminology
- **Config flow description** — Reworded setup text to guide users to find the Assessment Number on the Auckland Council collection days page
- **Hassfest-compliant translations** — Removed inline URLs and `description_placeholders` from `strings.json` and `translations/en.json` to pass hassfest validation

### Added
- **HACS & hassfest validation workflow** — New `validate.yml` GitHub Action running `hacs/action` and `home-assistant/actions/hassfest` on every push, PR, and daily schedule
- **Validate badge** — Added HACS/hassfest validation status badge to README

## [2026.03.24] - 2026-03-24

### Security
- **Property ID validation** — Added regex-based validation (`^\d{5,15}$`) at all entry points (config flow, init, coordinator) to prevent URL injection via unsanitised property IDs
- **Removed raw HTML logging** — Diagnostic logs no longer contain raw HTML content that could leak sensitive data
- **SECURITY.md** — Added vulnerability reporting policy using GitHub Private Vulnerability Reporting

### Changed
- **Shared HTTP session** — Switched from standalone `aiohttp.ClientSession` to Home Assistant's managed `async_get_clientsession(hass)` for proper SSL handling, connection pooling, and lifecycle management
- **Replaced `async_timeout`** — Migrated from deprecated `async-timeout` package to Python 3.11+ built-in `asyncio.timeout()`
- **Error handling** — Errors during data fetch now raise `UpdateFailed` instead of being silently swallowed, enabling HA's built-in retry/backoff and marking entities as unavailable
- **Property ID now required** — Removed default property ID; users must enter their own during setup
- **Verbose logging toggle** — Added optional `verbose_logging` config option to gate diagnostic log output
- **Moved `import re`** — Relocated inline import to module-level in config_flow.py

### Fixed
- **HTTP 406 Not Acceptable** — Switched to browser-style `User-Agent` and full `Accept` headers; Auckland Council's server rejects non-browser User-Agent strings (including HA's default one)
- **Duplicate method** — Removed second `_get_empty_data()` definition that was shadowing the first
- **Unused imports** — Removed unused `pytest` imports from test files

### Added
- **Options flow** — Users can now reconfigure collection time, scan interval, and verbose logging after setup via the integration's Configure button (no need to delete and re-add)
- **REQUEST_HEADERS regression tests** — 5 new tests ensure browser-style headers are maintained, preventing 406 regressions
- **strings.json** — Created HA-standard source-of-truth for user-facing translation strings
- **Unit tests** — 39 tests covering property ID validation, date parsing, HTML data extraction, and request headers
- **CI/CD pipeline** — GitHub Actions workflow with ruff linting and pytest across Python 3.12/3.13
- **CHANGELOG.md** — This file

## [2026.03.21] - 2026-03-21

### Added
- Initial release of Auckland Council HACS integration
- Rubbish, food scraps, and recycling collection date sensors
- Config flow UI for property setup
- Automatic daily polling of Auckland Council website
