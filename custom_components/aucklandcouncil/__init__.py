"""The Auckland Council integration."""
from __future__ import annotations

import logging
import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_PROPERTY_ID, BASE_URL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Auckland Council from a config entry."""
    _LOGGER.debug("Setting up Auckland Council integration")
    
    property_id = entry.data[CONF_PROPERTY_ID]
    
    # Validate the property ID by attempting to fetch data
    try:
        await _validate_property_id(property_id)
    except Exception as ex:
        _LOGGER.error(f"Failed to validate property ID {property_id}: {ex}")
        raise ConfigEntryNotReady(f"Cannot connect to Auckland Council for property {property_id}: {ex}")
    
    # Store the config entry data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def _validate_property_id(property_id: str) -> None:
    """Validate that the property ID works by fetching data."""
    url = BASE_URL.format(property_id)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with async_timeout.timeout(30):
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}")
                    
                    content = await response.text()
                    if "Your next collection dates" not in content:
                        raise Exception("Invalid property ID - no collection data found")
                    
                    _LOGGER.info(f"Successfully validated property ID {property_id}")
                    
        except aiohttp.ClientError as error:
            raise Exception(f"Network error: {error}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Auckland Council integration")
    
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok