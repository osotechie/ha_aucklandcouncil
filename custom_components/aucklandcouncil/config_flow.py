"""Config flow for Auckland Council integration."""
from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_PROPERTY_ID, CONF_COLLECTION_TIME, CONF_SCAN_INTERVAL, DEFAULT_PROPERTY_ID, DEFAULT_COLLECTION_TIME, DEFAULT_SCAN_INTERVAL, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_PROPERTY_ID, default=DEFAULT_PROPERTY_ID): cv.string,
        vol.Optional(CONF_COLLECTION_TIME, default=DEFAULT_COLLECTION_TIME): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=3600, max=604800)),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Auckland Council."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", 
                data_schema=STEP_USER_DATA_SCHEMA,
                description_placeholders={},
            )

        errors = {}

        property_id = user_input[CONF_PROPERTY_ID]
        collection_time = user_input[CONF_COLLECTION_TIME]
        scan_interval = user_input[CONF_SCAN_INTERVAL]
        
        # Basic validation - ensure property ID is numeric
        if not property_id.isdigit():
            errors[CONF_PROPERTY_ID] = "invalid_property_id"
            
        # Validate collection time format (HH:MM)
        import re
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', collection_time):
            errors[CONF_COLLECTION_TIME] = "invalid_time_format"
        
        if not errors:
            # Check if already configured
            await self.async_set_unique_id(property_id)
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=f"{DEFAULT_NAME} - {property_id}",
                data={
                    CONF_PROPERTY_ID: property_id,
                    CONF_COLLECTION_TIME: collection_time,
                    CONF_SCAN_INTERVAL: scan_interval
                },
            )

        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors,
            description_placeholders={},
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidPropertyId(Exception):
    """Error to indicate there is invalid property ID."""