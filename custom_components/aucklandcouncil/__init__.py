"""The Auckland Council integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_PROPERTY_ID,
    BASE_URL,
    REQUEST_HEADERS,
    validate_property_id,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Auckland Council from a config entry."""
    _LOGGER.debug("Setting up Auckland Council integration")

    property_id = entry.data[CONF_PROPERTY_ID]

    # Validate the property ID by attempting to fetch data
    try:
        await _validate_property_id(hass, property_id)
    except Exception as ex:
        _LOGGER.error(f"Failed to validate property ID {property_id}: {ex}")
        raise ConfigEntryNotReady(
            f"Cannot connect to Auckland Council for property {property_id}: {ex}"
        )

    # Store the config entry data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Reload integration when options change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _validate_property_id(hass: HomeAssistant, property_id: str) -> None:
    """Validate that the property ID works by fetching data."""
    if not validate_property_id(property_id):
        raise ValueError(
            f"Invalid property ID: must be numeric and between 5-15 digits, got '{property_id}'"
        )

    url = BASE_URL.format(property_id)
    session = async_get_clientsession(hass)

    try:
        async with asyncio.timeout(30):
            async with session.get(url, headers=REQUEST_HEADERS) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                content = await response.text()
                if "Your next collection dates" not in content:
                    raise Exception("Invalid property ID - no collection data found")

                _LOGGER.info(f"Successfully validated property ID {property_id}")

    except TimeoutError:
        raise Exception("Request timed out while validating property ID")
    except Exception:
        raise


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Auckland Council integration")

    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
