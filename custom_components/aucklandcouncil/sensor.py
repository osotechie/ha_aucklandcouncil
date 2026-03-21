"""Auckland Council sensor platform."""
from __future__ import annotations

import logging
import re
import asyncio
from datetime import timedelta, datetime
from typing import Any

import aiohttp
import async_timeout

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_PROPERTY_ID,
    CONF_COLLECTION_TIME,
    CONF_SCAN_INTERVAL,
    BASE_URL,
    COLLECTION_TYPES,
    COLLECTION_PATTERNS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_COLLECTION_TIME,
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
    collection_time = entry.data.get(CONF_COLLECTION_TIME, DEFAULT_COLLECTION_TIME)
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    
    coordinator = AucklandCouncilDataUpdateCoordinator(hass, property_id, collection_time, scan_interval)
    
    # Get initial data - this sets up the coordinator without throwing exceptions
    await coordinator.async_config_entry_first_refresh()
    
    entities = []
    for description in SENSOR_DESCRIPTIONS:
        entities.append(AucklandCouncilSensor(coordinator, description, property_id))
    
    async_add_entities(entities)


class AucklandCouncilDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Auckland Council."""

    def __init__(self, hass: HomeAssistant, property_id: str, collection_time: str, scan_interval: int) -> None:
        """Initialize."""
        self.property_id = property_id
        self.collection_time = collection_time
        self.url = BASE_URL.format(property_id)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            async with async_timeout.timeout(20):  # Reduced timeout
                data = await self._fetch_collection_data()
                _LOGGER.debug(f"Successfully fetched data: {data}")
                return data
        except asyncio.TimeoutError:
            _LOGGER.warning("Request timeout - will retry on next update")
            return self._get_empty_data()
        except Exception as exception:
            _LOGGER.error(f"Error communicating with API: {exception}")
            return self._get_empty_data()

    async def _fetch_collection_data(self) -> dict[str, Any]:
        """Fetch collection data from Auckland Council website."""
        timeout = aiohttp.ClientTimeout(total=15)  # Set reasonable timeout
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.url) as response:
                    if response.status != 200:
                        _LOGGER.error(f"Error fetching data: HTTP {response.status}")
                        return self._get_empty_data()
                    
                    content = await response.text()
                    
                    # Log some debug info about the response
                    _LOGGER.debug(f"Received response of {len(content)} characters")
                    
                    return self._parse_collection_data(content)
                    
        except aiohttp.ClientError as error:
            _LOGGER.error(f"Network error fetching data: {error}")
            return self._get_empty_data()
        except Exception as error:
            _LOGGER.error(f"Unexpected error fetching data: {error}")
            return self._get_empty_data()

    def _get_empty_data(self) -> dict[str, Any]:
        """Return empty data structure when fetch fails."""
        return {
            "rubbish": None,
            "food_scraps": None,
            "recycling": None
        }

    def _parse_collection_data(self, content: str) -> dict[str, Any]:
        """Parse collection dates from the webpage content."""
        data = {}
        
        # Log debug info about content
        _LOGGER.debug(f"Content length: {len(content)} characters")
        
        for collection_type, pattern in COLLECTION_PATTERNS.items():
            try:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    date_text = match.group(1).strip()
                    # Parse the date string and convert to proper datetime
                    parsed_date = self._parse_date_string(date_text, self.collection_time)
                    data[collection_type] = parsed_date
                    _LOGGER.info(f"Found {collection_type}: '{date_text}' -> {parsed_date}")
                else:
                    data[collection_type] = None
                    _LOGGER.warning(f"No match found for {collection_type}")
                    
                    # For debugging: try to find the collection type name to see if it exists
                    type_name = collection_type.replace("_", " ").title()
                    simple_search = content.lower().find(type_name.lower() + ":")
                    if simple_search != -1:
                        # Show context around where we found the type name
                        start = max(0, simple_search - 50)
                        end = min(len(content), simple_search + 150)
                        context = content[start:end].replace('\n', ' ').replace('\r', '')
                        _LOGGER.debug(f"Found '{type_name}:' in content around: ...{context}...")
                    
            except Exception as e:
                _LOGGER.error(f"Error parsing {collection_type}: {e}")
                data[collection_type] = None
        
        # Log final results
        _LOGGER.info(f"Parsed collection data: {data}")
        
        # If we got no data at all, log a sample of content for debugging
        if not any(data.values()):
            # Look for the word "collection" to see if we're on the right page
            if "collection" in content.lower():
                _LOGGER.debug("Content contains 'collection' but no dates found - patterns may need updating")
                # Show first occurrence of "collection" for debugging
                collection_index = content.lower().find("collection")
                start = max(0, collection_index - 100)
                end = min(len(content), collection_index + 200)
                sample = content[start:end].replace('\n', ' ').replace('\r', '')
                _LOGGER.debug(f"Sample content around 'collection': ...{sample}...")
            else:
                _LOGGER.warning("Content doesn't contain expected collection information")
        
        return data

    def _parse_date_string(self, date_text: str, collection_time: str) -> datetime | None:
        """Parse date string like 'Friday, 20 March' into a timezone-aware datetime object."""
        try:
            # Extract day and month from the text
            # Pattern: "Friday, 20 March" or "Friday 20 March" 
            date_pattern = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)'
            match = re.search(date_pattern, date_text, re.IGNORECASE)
            
            if not match:
                _LOGGER.warning(f"Could not parse date format: {date_text}")
                return None
                
            day = int(match.group(1))
            month_name = match.group(2).title()
            
            # Convert month name to month number
            month_map = {
                'January': 1, 'February': 2, 'March': 3, 'April': 4,
                'May': 5, 'June': 6, 'July': 7, 'August': 8, 
                'September': 9, 'October': 10, 'November': 11, 'December': 12
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
                _LOGGER.warning(f"Invalid collection time format: {collection_time}, using 07:00")
                hour, minute = 7, 0
            
            # Determine the year - start with current year
            now = dt_util.now()
            year = now.year
            
            # Create the date with current year and specified time
            try:
                naive_date = datetime(year, month, day, hour, minute)
                collection_date = dt_util.as_local(naive_date)
            except ValueError as e:
                _LOGGER.warning(f"Invalid date {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}: {e}")
                return None
            
            # If the date is in the past (more than 1 day ago), use next year
            if collection_date < now - timedelta(days=1):
                year += 1
                try:
                    naive_date = datetime(year, month, day, hour, minute)
                    collection_date = dt_util.as_local(naive_date)
                except ValueError as e:
                    _LOGGER.warning(f"Invalid date {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}: {e}")
                    return None
            
            _LOGGER.debug(f"Parsed '{date_text}' as {collection_date}")
            return collection_date
            
        except Exception as e:
            _LOGGER.error(f"Error parsing date '{date_text}': {e}")
            return None

    def _get_empty_data(self) -> dict[str, Any]:
        """Return empty data structure when fetch fails."""
        return {
            "rubbish": None,
            "food_scraps": None, 
            "recycling": None
        }


class AucklandCouncilSensor(SensorEntity):
    """Auckland Council sensor."""

    def __init__(
        self,
        coordinator: AucklandCouncilDataUpdateCoordinator,
        description: SensorEntityDescription,
        property_id: str,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self.coordinator = coordinator
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
        # Entity is available if we have data (even if collection date is None)
        return self.coordinator.data is not None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self) -> None:
        """Update the entity."""
        await self.coordinator.async_request_refresh()