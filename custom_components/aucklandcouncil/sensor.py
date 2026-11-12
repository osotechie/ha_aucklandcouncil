"""Auckland Council sensor platform."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    BASE_URL,
    COLLECTION_DATE_FUTURE_DAYS,
    COLLECTION_DATE_PAST_DAYS,
    COLLECTION_PATTERNS,
    COLLECTION_TYPES,
    CONF_PROPERTY_ID,
    DOMAIN,
    FALLBACK_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    REQUEST_HEADERS,
    STORAGE_KEY,
    STORAGE_VERSION,
    validate_property_id,
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
    coordinator: AucklandCouncilDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]
    property_id = entry.data[CONF_PROPERTY_ID]

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
        self._next_refresh: datetime | None = None
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{property_id}",
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=FALLBACK_SCAN_INTERVAL),
        )

    def _compute_next_update_interval(self, data: dict[str, Any]) -> timedelta:
        """Refresh after collection, retry stale data daily, and cap waits at a week."""
        fallback = timedelta(seconds=FALLBACK_SCAN_INTERVAL)
        now = dt_util.now()
        interval = timedelta(seconds=MAX_SCAN_INTERVAL)

        for key in COLLECTION_TYPES:
            value = data.get(key)
            if not isinstance(value, datetime) or value.tzinfo is None:
                interval = min(interval, fallback)
                continue

            collection_poll = dt_util.as_local(value) + timedelta(days=1)
            try:
                time_parts = self.collection_time.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                collection_poll = collection_poll.replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
            except (ValueError, IndexError):
                _LOGGER.warning(
                    "Invalid collection time %r, keeping the parsed collection time",
                    self.collection_time,
                )

            collection_interval = dt_util.as_utc(collection_poll) - dt_util.as_utc(now)
            if collection_interval <= timedelta(0):
                collection_interval = fallback
            interval = min(interval, collection_interval)

        interval = max(interval, timedelta(hours=1))
        _LOGGER.debug(
            "Next poll in %s (at %s)",
            interval,
            (dt_util.as_utc(now) + interval).isoformat(),
        )
        return interval

    async def async_load_stored_data(self) -> bool:
        """Restore cached data until its persisted refresh deadline."""
        stored = await self._store.async_load()
        if not stored or not isinstance(stored, dict):
            _LOGGER.debug("No stored data found for property %s", self.property_id)
            return False

        data: dict[str, Any] = {}
        now = dt_util.now()
        now_utc = dt_util.as_utc(now)
        for key in COLLECTION_TYPES:
            raw = stored.get(key)
            if raw is None:
                data[key] = None
                continue
            try:
                dt = datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid cached collection date for %s", key)
                return False
            if dt.tzinfo is None or not (
                now.date() - timedelta(days=COLLECTION_DATE_PAST_DAYS)
                <= dt_util.as_local(dt).date()
                <= now.date() + timedelta(days=COLLECTION_DATE_FUTURE_DAYS)
            ):
                _LOGGER.warning(
                    "Cached collection date outside supported window: %s", dt
                )
                return False
            data[key] = dt

        raw_deadline = stored.get("next_refresh")
        if raw_deadline is None:
            # Migrate legacy caches once so reloads cannot keep extending the deadline.
            if not any(data.values()) or any(
                value is not None and value <= now for value in data.values()
            ):
                return False
            self._next_refresh = now_utc + self._compute_next_update_interval(data)
            await self._async_save_data(data)
        else:
            try:
                deadline = datetime.fromisoformat(raw_deadline)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid cached refresh deadline")
                return False
            if deadline.tzinfo is None or deadline > now_utc + timedelta(
                seconds=MAX_SCAN_INTERVAL
            ):
                _LOGGER.warning(
                    "Cached refresh deadline outside supported window: %s", deadline
                )
                return False
            if deadline <= now:
                _LOGGER.debug("Cached refresh deadline reached, fetching fresh data")
                return False
            self._next_refresh = dt_util.as_utc(deadline)
            cached_time = stored.get("collection_time")
            if cached_time is not None and cached_time != self.collection_time:
                try:
                    collection_time = datetime.strptime(
                        self.collection_time, "%H:%M"
                    ).time()
                except ValueError:
                    _LOGGER.warning("Invalid collection time %r", self.collection_time)
                    return False
                for key, value in data.items():
                    if value is not None:
                        data[key] = dt_util.as_local(value).replace(
                            hour=collection_time.hour,
                            minute=collection_time.minute,
                            second=0,
                            microsecond=0,
                        )
                self._next_refresh = now_utc + self._compute_next_update_interval(data)
                await self._async_save_data(data)

        self.update_interval = self._next_refresh - now_utc
        self.async_set_updated_data(data)
        _LOGGER.debug(
            "Restored stored data for property %s, next poll at %s",
            self.property_id,
            self._next_refresh.isoformat(),
        )
        return True

    async def _async_save_data(self, data: dict[str, Any]) -> None:
        """Persist collection data and its absolute refresh deadline."""
        serialisable = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialisable[key] = value.isoformat()
            else:
                serialisable[key] = value
        if self._next_refresh is not None:
            serialisable["next_refresh"] = self._next_refresh.isoformat()
        serialisable["collection_time"] = self.collection_time
        await self._store.async_save(serialisable)

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
                self._next_refresh = dt_util.utcnow() + self.update_interval
                # Persist to disk for next startup
                await self._async_save_data(data)
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
            # Use the integration's custom fetch service, not a forward proxy.
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

            except Exception:
                _LOGGER.exception("Error parsing %s", collection_type)
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

            now = dt_util.now()
            earliest = now.date() - timedelta(days=COLLECTION_DATE_PAST_DAYS)
            latest = now.date() + timedelta(days=COLLECTION_DATE_FUTURE_DAYS)
            for year in (now.year - 1, now.year, now.year + 1):
                try:
                    collection_date = datetime(
                        year, month, day, hour, minute, tzinfo=now.tzinfo
                    )
                except ValueError:
                    continue
                if earliest <= collection_date.date() <= latest:
                    if collection_date <= now:
                        _LOGGER.warning(
                            "Council returned a past collection date: %s",
                            collection_date.isoformat(),
                        )
                    _LOGGER.debug("Parsed '%s' as %s", date_text, collection_date)
                    return collection_date

            _LOGGER.warning(
                "Invalid collection date or no year within the supported window "
                "(%s to %s): %s",
                earliest,
                latest,
                date_text,
            )
            return None

        except Exception:
            _LOGGER.exception("Error parsing date '%s'", date_text)
            return None


class AucklandCouncilSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
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

    async def async_added_to_hass(self) -> None:
        """Restore last known state when added to HA."""
        await super().async_added_to_hass()

        # If coordinator already has data (from Store), no need to restore
        if self.coordinator.data is not None:
            return

        # Fall back to HA's state machine for the previous value
        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in ("unknown", "unavailable"):
            return

        try:
            restored = datetime.fromisoformat(last_state.state)
            _LOGGER.debug(
                "Restored %s state: %s",
                self.entity_description.key,
                restored,
            )
            self._attr_native_value = restored
        except (ValueError, TypeError):
            pass

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
        if self.coordinator.data is not None:
            return self.coordinator.data.get(self.entity_description.key)

        # Return restored state if coordinator hasn't fetched yet
        return getattr(self, "_attr_native_value", None)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self.coordinator.data is not None:
            return super().available
        # Available if we have a restored value
        return getattr(self, "_attr_native_value", None) is not None
