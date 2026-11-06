# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2026.11.07] - 2026-11-07

### Changed
- **Custom proxy clarification** — Setup and options screens now label the proxy fields as custom integration proxy settings, explain that access is privately provided with no public service available, and explicitly exclude standard HTTP/HTTPS forward proxies. Leaving both fields blank continues to use direct council access; existing proxy settings and behavior are unchanged
- **Current browser User-Agent** — Updated the Chrome token to `Chrome/158.0.0.0`, matching the latest Windows stable major version verified through Google's Version History API on 6 November 2026. Retained the frozen Windows, Mozilla, AppleWebKit, and Safari compatibility tokens required by Chrome's reduced User-Agent format
- **Official Home Assistant testing** — Migrated to `pytest-homeassistant`, using real Home Assistant instances, configuration entries, coordinators, flow managers, storage, and entity registries instead of global module stubs and copied parser implementations
- **Standard local and CI checks** — Local development and GitHub Actions now invoke Ruff and pytest directly, without a custom check runner; lint and formatting checks cover both integration code and tests
- **Python 3.14 framework tests** — Replaced the mock-based Python 3.12/3.13 matrix with framework tests on Python 3.14, as current Home Assistant and its testing package require Python 3.14.2 or newer; retained the Python 3.12 Ruff compatibility target and existing minimum Home Assistant version
- **Latest development tooling** — Added unpinned Ruff and `pytest-homeassistant` dependencies in `requirements-dev.txt`; CI upgrades them on every run, while the framework supplies matching Home Assistant and pytest versions internally
- **Explicit lint configuration** — Added shared Ruff settings targeting Python 3.12, including import sorting, broad-exception checks, and minimum/maximum simplification rules

### Fixed
- **Six CI lint failures** — Sorted imports across the integration and simplified the minimum polling interval calculation to `max(interval, min_interval)`, preserving the one-hour minimum
- **Parser exception diagnostics** — Parsing recovery handlers now log full exception tracebacks while retaining the existing behavior of returning no date or continuing with other collection types

### Added
- **Production-method regression coverage** — Added tests for date parsing, exception recovery and traceback logging, polling schedules, fallback intervals, and the one-hour minimum using actual coordinator objects
- **Integration lifecycle tests** — Added configuration and options flow validation, duplicate-entry prevention, setup and unload, timestamp sensor states, options-triggered reloads, HTTP failure handling, direct/proxy request headers, and persistent cache restoration
- **Offline test fixtures** — Council responses use fixture HTML and the framework's HTTP mocks; pytest blocks external network access
- **Reduced User-Agent regression test** — Validates the complete browser-style header format and prevents regression to a Chrome major version older than 158
- **Verified framework suite** — Tests pass against Home Assistant and `pytest-homeassistant` 2026.11.0 on Linux with Python 3.14.10, with Ruff 0.17.4 lint and formatting checks passing; upstream Home Assistant/aiohttp and backoff deprecation warnings remain visible

## [2026.07.14] - 2026-07-14

### Added
- **Persistent data caching** — Collection data is now saved to disk (via HA `Store`) after each successful fetch. On restart, the integration loads cached data and skips the API call only if all collection dates are still in the future. If any date has passed (e.g. rubbish collected but recycling still upcoming), a fresh fetch is triggered to get updated dates. This avoids unnecessary network requests on every HA restart for data that only changes weekly
- **State restoration** — Sensors now use `RestoreEntity` to immediately show their last known value during startup, eliminating a brief "unavailable" flash while the coordinator initialises

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
