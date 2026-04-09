"""Auckland Council sensor platform."""

from __future__ import annotations

import logging
import re
import asyncio
from datetime import timedelta, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_PROPERTY_ID,
    validate_property_id,
    CONF_COLLECTION_TIME,
    CONF_PROXY_URL,
    CONF_PROXY_TOKEN,
    BASE_URL,
    COLLECTION_PATTERNS,
    FALLBACK_SCAN_INTERVAL,
    DEFAULT_COLLECTION_TIME,
    REQUEST_HEADERS,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key="rubbish",
        name="Rubbish",
        icon="mdi:delete",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="food_scraps",
        name="Food Scraps",
        icon="mdi:food-apple",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="recycling",
        name="Recycling",
        icon="mdi:recycle",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Auckland Council sensors."""
    property_id = entry.data[CONF_PROPERTY_ID]
    collection_time = entry.options.get(
        CONF_COLLECTION_TIME,
        entry.data.get(CONF_COLLECTION_TIME, DEFAULT_COLLECTION_TIME),
    )
    proxy_url = entry.options.get(CONF_PROXY_URL, entry.data.get(CONF_PROXY_URL, ""))
    proxy_token = entry.options.get(
        CONF_PROXY_TOKEN, entry.data.get(CONF_PROXY_TOKEN, "")
    )

    coordinator = AucklandCouncilDataUpdateCoordinator(
        hass,
        property_id,
        collection_time,
        proxy_url,
        proxy_token,
    )

    # Get initial data - this sets up the coordinator without throwing exceptions
    await coordinator.async_config_entry_first_refresh()

    entities = []
    for description in SENSOR_DESCRIPTIONS:
        entities.append(AucklandCouncilSensor(coordinator, description, property_id))

    async_add_entities(entities)


class AucklandCouncilDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Auckland Council."""

    def __init__(
        self,
        hass: HomeAssistant,
        property_id: str,
        collection_time: str,
        proxy_url: str = "",
        proxy_token: str = "",
    ) -> None:
        """Initialize."""
        if not validate_property_id(property_id):
            raise ValueError(
                f"Invalid property ID: must be numeric and between 5-15 digits, got '{property_id}'"
            )

        self.property_id = property_id
        self.collection_time = collection_time
        self.url = BASE_URL.format(property_id)
        self.proxy_url = proxy_url.strip() if proxy_url else ""
        self.proxy_token = proxy_token.strip() if proxy_token else ""

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=FALLBACK_SCAN_INTERVAL),
        )

    def _compute_next_update_interval(self, data: dict[str, Any]) -> timedelta:
        """Compute the next update interval based on the earliest collection date.

        Schedules the next poll for the day after the earliest upcoming collection,
        at the configured collection time. Falls back to 24 h on error.
        """
        fallback = timedelta(seconds=FALLBACK_SCAN_INTERVAL)
        now = dt_util.now()

        # Collect all valid future collection datetimes
        upcoming: list[datetime] = []
        for value in data.values():
            if isinstance(value, datetime) and value > now:
                upcoming.append(value)

        if not upcoming:
            _LOGGER.debug(
                "No upcoming collection dates found, using fallback interval of %s",
                fallback,
            )
            return fallback

        earliest = min(upcoming)
        # Schedule for the day after the earliest collection, at collection time
        next_poll = earliest + timedelta(days=1)
        # Replace time with the configured collection time
        try:
            time_parts = self.collection_time.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            next_poll = next_poll.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        except (ValueError, IndexError):
            pass

        interval = next_poll - now
        # Ensure we never set an interval shorter than 1 hour
        min_interval = timedelta(hours=1)
        if interval < min_interval:
            interval = min_interval

        _LOGGER.debug(
            "Next collection: %s — next poll in %s (at %s)",
            earliest.isoformat(),
            interval,
            next_poll.isoformat(),
        )
        return interval

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            async with asyncio.timeout(20):
                _LOGGER.debug(
                    "Coordinator requesting data update (property %s)",
                    self.property_id,
                )
                data = await self._fetch_collection_data()
                _LOGGER.debug("Successfully fetched data: %s", data)
                # Dynamically adjust the next poll interval
                self.update_interval = self._compute_next_update_interval(data)
                return data
        except TimeoutError as exception:
            raise UpdateFailed(
                "Request timeout fetching collection data"
            ) from exception
        except UpdateFailed:
            raise
        except Exception as exception:
            raise UpdateFailed(
                f"Error communicating with API: {exception}"
            ) from exception

    async def _fetch_collection_data(self) -> dict[str, Any]:
        """Fetch collection data from Auckland Council website (direct or via proxy)."""
        session = async_get_clientsession(self.hass)

        if self.proxy_url and self.proxy_token:
            # Route through the Cloudflare Worker proxy
            from urllib.parse import quote

            fetch_url = f"{self.proxy_url}?url={quote(self.url, safe='')}"
            headers = {
                **REQUEST_HEADERS,
                "X-Proxy-Token": self.proxy_token,
            }
            _LOGGER.debug("Fetching via proxy: %s", self.proxy_url)
        else:
            fetch_url = self.url
            headers = REQUEST_HEADERS

        async with session.get(fetch_url, headers=headers) as response:
            if response.status != 200:
                raise UpdateFailed(f"HTTP {response.status} fetching collection data")

            content = await response.text()

            _LOGGER.debug("Received response of %d characters", len(content))

            return self._parse_collection_data(content)

    def _get_empty_data(self) -> dict[str, Any]:
        """Return empty data structure when fetch fails."""
        return {"rubbish": None, "food_scraps": None, "recycling": None}

    def _parse_collection_data(self, content: str) -> dict[str, Any]:
        """Parse collection dates from the webpage content."""
        data = {}

        _LOGGER.debug("Content length: %d characters", len(content))

        for collection_type, pattern in COLLECTION_PATTERNS.items():
            try:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    date_text = match.group(1).strip()
                    # Parse the date string and convert to proper datetime
                    parsed_date = self._parse_date_string(
                        date_text, self.collection_time
                    )
                    data[collection_type] = parsed_date
                    _LOGGER.info(
                        f"Found {collection_type}: '{date_text}' -> {parsed_date}"
                    )
                else:
                    data[collection_type] = None
                    _LOGGER.warning(f"No match found for {collection_type}")

                    type_name = collection_type.replace("_", " ").title()
                    found_in_content = type_name.lower() + ":" in content.lower()
                    _LOGGER.debug(
                        "'%s:' present in content: %s", type_name, found_in_content
                    )

            except Exception as e:
                _LOGGER.error(f"Error parsing {collection_type}: {e}")
                data[collection_type] = None

        # Log final results
        _LOGGER.info(f"Parsed collection data: {data}")

        # If we got no data at all, check if we're on the right page
        if not any(data.values()):
            if "collection" in content.lower():
                _LOGGER.debug(
                    "Content contains 'collection' but no dates found - patterns may need updating"
                )
            else:
                _LOGGER.warning(
                    "Content doesn't contain expected collection information"
                )

        return data

    def _parse_date_string(
        self, date_text: str, collection_time: str
    ) -> datetime | None:
        """Parse date string like 'Friday, 20 March' into a timezone-aware datetime object."""
        try:
            # Extract day and month from the text
            # Pattern: "Friday, 20 March" or "Friday 20 March"
            date_pattern = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)"
            match = re.search(date_pattern, date_text, re.IGNORECASE)

            if not match:
                _LOGGER.warning(f"Could not parse date format: {date_text}")
                return None

            day = int(match.group(1))
            month_name = match.group(2).title()

            # Convert month name to month number
            month_map = {
                "January": 1,
                "February": 2,
                "March": 3,
                "April": 4,
                "May": 5,
                "June": 6,
                "July": 7,
                "August": 8,
                "September": 9,
                "October": 10,
                "November": 11,
                "December": 12,
            }
            month = month_map.get(month_name)
            if not month:
                _LOGGER.warning(f"Unknown month: {month_name}")
                return None

            # Parse collection time (e.g. "07:00")
            try:
                time_parts = collection_time.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            except (ValueError, IndexError):
                _LOGGER.warning(
                    f"Invalid collection time format: {collection_time}, using 07:00"
                )
                hour, minute = 7, 0

            # Determine the year - start with current year
            now = dt_util.now()
            year = now.year

            # Create the date with current year and specified time
            try:
                naive_date = datetime(year, month, day, hour, minute)
                collection_date = dt_util.as_local(naive_date)
            except ValueError as e:
                _LOGGER.warning(
                    f"Invalid date {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}: {e}"
                )
                return None

            # If the date is in the past (more than 1 day ago), use next year
            if collection_date < now - timedelta(days=1):
                year += 1
                try:
                    naive_date = datetime(year, month, day, hour, minute)
                    collection_date = dt_util.as_local(naive_date)
                except ValueError as e:
                    _LOGGER.warning(
                        f"Invalid date {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}: {e}"
                    )
                    return None

            _LOGGER.debug(f"Parsed '{date_text}' as {collection_date}")
            return collection_date

        except Exception as e:
            _LOGGER.error(f"Error parsing date '{date_text}': {e}")
            return None


class AucklandCouncilSensor(CoordinatorEntity, SensorEntity):
    """Auckland Council sensor."""

    def __init__(
        self,
        coordinator: AucklandCouncilDataUpdateCoordinator,
        description: SensorEntityDescription,
        property_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._property_id = property_id
        self._attr_unique_id = f"aucklandcouncil_{property_id}_{description.key}"
        self._attr_entity_id = f"sensor.aucklandcouncil_{property_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._property_id)},
            name=f"Auckland Council Property {self._property_id}",
            manufacturer="Auckland Council",
            model="Collection Schedule",
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the native value of the sensor."""
        if self.coordinator.data is None:
            return None

        collection_date = self.coordinator.data.get(self.entity_description.key)
        return collection_date  # Already a datetime object or None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.coordinator.data is not None
