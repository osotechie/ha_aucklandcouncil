# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
- **Duplicate method** — Removed second `_get_empty_data()` definition that was shadowing the first

### Added
- **strings.json** — Created HA-standard source-of-truth for user-facing translation strings
- **Unit tests** — 34 tests covering property ID validation, date parsing, and HTML data extraction
- **CI/CD pipeline** — GitHub Actions workflow with ruff linting and pytest across Python 3.12/3.13
- **CHANGELOG.md** — This file

## [2026.03.21] - 2026-03-21

### Added
- Initial release of Auckland Council HACS integration
- Rubbish, food scraps, and recycling collection date sensors
- Config flow UI for property setup
- Automatic daily polling of Auckland Council website
