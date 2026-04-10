"""The Auckland Council integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    CONF_PROPERTY_ID,
    CONF_COLLECTION_TIME,
    CONF_PROXY_URL,
    CONF_PROXY_TOKEN,
    DEFAULT_COLLECTION_TIME,
)
from .sensor import AucklandCouncilDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Auckland Council from a config entry."""
    _LOGGER.debug("Setting up Auckland Council integration")

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

    # Fetch initial data — raises ConfigEntryNotReady on failure
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator for platforms to access
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Reload integration when options change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


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
