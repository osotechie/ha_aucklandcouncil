"""Config flow for Auckland Council integration."""

from __future__ import annotations

import logging
import re
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_PROPERTY_ID,
    CONF_COLLECTION_TIME,
    CONF_VERBOSE_LOGGING,
    CONF_PROXY_URL,
    CONF_PROXY_TOKEN,
    DEFAULT_COLLECTION_TIME,
    DEFAULT_NAME,
    validate_property_id,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROPERTY_ID): cv.string,
        vol.Optional(CONF_COLLECTION_TIME, default=DEFAULT_COLLECTION_TIME): cv.string,
        vol.Optional(CONF_VERBOSE_LOGGING, default=False): cv.boolean,
        vol.Optional(CONF_PROXY_URL, default=""): cv.string,
        vol.Optional(CONF_PROXY_TOKEN, default=""): cv.string,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Auckland Council."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

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
        proxy_url = user_input.get(CONF_PROXY_URL, "").strip()
        proxy_token = user_input.get(CONF_PROXY_TOKEN, "").strip()

        # Validate property ID is numeric and between 5-15 digits
        if not validate_property_id(property_id):
            errors[CONF_PROPERTY_ID] = "invalid_property_id"

        # Validate collection time format (HH:MM)
        if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", collection_time):
            errors[CONF_COLLECTION_TIME] = "invalid_time_format"

        # Validate proxy: if one is set, both must be set
        if proxy_url and not proxy_token:
            errors[CONF_PROXY_TOKEN] = "proxy_token_required"
        if proxy_token and not proxy_url:
            errors[CONF_PROXY_URL] = "proxy_url_required"

        # Validate proxy URL format
        if proxy_url and not proxy_url.startswith(("https://", "http://")):
            errors[CONF_PROXY_URL] = "invalid_proxy_url"

        if not errors:
            # Check if already configured
            await self.async_set_unique_id(property_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"{DEFAULT_NAME} - {property_id}",
                data={
                    CONF_PROPERTY_ID: property_id,
                    CONF_COLLECTION_TIME: collection_time,
                    CONF_VERBOSE_LOGGING: user_input.get(CONF_VERBOSE_LOGGING, False),
                    CONF_PROXY_URL: proxy_url,
                    CONF_PROXY_TOKEN: proxy_token,
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


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Auckland Council."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            errors = {}

            collection_time = user_input[CONF_COLLECTION_TIME]
            if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", collection_time):
                errors[CONF_COLLECTION_TIME] = "invalid_time_format"

            proxy_url = user_input.get(CONF_PROXY_URL, "").strip()
            proxy_token = user_input.get(CONF_PROXY_TOKEN, "").strip()

            if proxy_url and not proxy_token:
                errors[CONF_PROXY_TOKEN] = "proxy_token_required"
            if proxy_token and not proxy_url:
                errors[CONF_PROXY_URL] = "proxy_url_required"
            if proxy_url and not proxy_url.startswith(("https://", "http://")):
                errors[CONF_PROXY_URL] = "invalid_proxy_url"

            # Normalize: store trimmed values
            user_input[CONF_PROXY_URL] = proxy_url
            user_input[CONF_PROXY_TOKEN] = proxy_token

            if not errors:
                return self.async_create_entry(title="", data=user_input)

            return self.async_show_form(
                step_id="init",
                data_schema=self._build_options_schema(),
                errors=errors,
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self._build_options_schema(),
        )

    def _build_options_schema(self) -> vol.Schema:
        """Build the options schema with current values as defaults."""
        return vol.Schema(
            {
                vol.Optional(
                    CONF_COLLECTION_TIME,
                    default=self.config_entry.options.get(
                        CONF_COLLECTION_TIME,
                        self.config_entry.data.get(
                            CONF_COLLECTION_TIME, DEFAULT_COLLECTION_TIME
                        ),
                    ),
                ): cv.string,
                vol.Optional(
                    CONF_VERBOSE_LOGGING,
                    default=self.config_entry.options.get(
                        CONF_VERBOSE_LOGGING,
                        self.config_entry.data.get(CONF_VERBOSE_LOGGING, False),
                    ),
                ): cv.boolean,
                vol.Optional(
                    CONF_PROXY_URL,
                    default=self.config_entry.options.get(
                        CONF_PROXY_URL,
                        self.config_entry.data.get(CONF_PROXY_URL, ""),
                    ),
                ): cv.string,
                vol.Optional(
                    CONF_PROXY_TOKEN,
                    default=self.config_entry.options.get(
                        CONF_PROXY_TOKEN,
                        self.config_entry.data.get(CONF_PROXY_TOKEN, ""),
                    ),
                ): cv.string,
            }
        )
