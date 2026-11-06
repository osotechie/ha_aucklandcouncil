"""Exercise configuration and options through Home Assistant's flow managers."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aucklandcouncil.const import (
    CONF_COLLECTION_TIME,
    CONF_PROPERTY_ID,
    CONF_PROXY_TOKEN,
    CONF_PROXY_URL,
    DOMAIN,
)

from .const import PROPERTY_ID


@pytest.mark.parametrize(
    ("category", "step"), [("config", "user"), ("options", "init")]
)
async def test_custom_proxy_guidance(
    hass: HomeAssistant, category: str, step: str
) -> None:
    translations = await async_get_translations(hass, "en", category, {DOMAIN})
    prefix = f"component.{DOMAIN}.{category}.step.{step}"
    assert translations[f"{prefix}.data.proxy_url"] == "Custom proxy URL (optional)"
    assert translations[f"{prefix}.data.proxy_token"].startswith("Custom proxy token")
    description = translations[f"{prefix}.description"]
    assert "private proxy service built for this integration" in description
    assert "No public proxy service is available." in description
    assert "Standard HTTP/HTTPS forward proxies are not supported." in description
    assert (
        "Leave both fields blank to connect directly to Auckland Council."
        in description
    )


async def test_user_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch(
        "custom_components.aucklandcouncil.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_PROPERTY_ID: PROPERTY_ID,
                CONF_COLLECTION_TIME: "07:00",
                CONF_PROXY_URL: " https://proxy.example ",
                CONF_PROXY_TOKEN: " token ",
            },
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == PROPERTY_ID
    assert result["data"] == {
        CONF_PROPERTY_ID: PROPERTY_ID,
        CONF_COLLECTION_TIME: "07:00",
        CONF_PROXY_URL: "https://proxy.example",
        CONF_PROXY_TOKEN: "token",
    }


@pytest.mark.parametrize(
    ("overrides", "errors"),
    [
        ({CONF_PROPERTY_ID: "not-an-id"}, {CONF_PROPERTY_ID: "invalid_property_id"}),
        (
            {CONF_COLLECTION_TIME: "25:00"},
            {CONF_COLLECTION_TIME: "invalid_time_format"},
        ),
        (
            {CONF_PROXY_URL: "https://proxy.example"},
            {CONF_PROXY_TOKEN: "proxy_token_required"},
        ),
        ({CONF_PROXY_TOKEN: "token"}, {CONF_PROXY_URL: "proxy_url_required"}),
        (
            {CONF_PROXY_URL: "ftp://proxy.example", CONF_PROXY_TOKEN: "token"},
            {CONF_PROXY_URL: "invalid_proxy_url"},
        ),
    ],
)
async def test_invalid_user_input(
    hass: HomeAssistant, overrides: dict[str, str], errors: dict[str, str]
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PROPERTY_ID: PROPERTY_ID, CONF_COLLECTION_TIME: "07:00", **overrides},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors


async def test_already_configured(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PROPERTY_ID: PROPERTY_ID, CONF_COLLECTION_TIME: "07:00"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_COLLECTION_TIME: "08:30",
            CONF_PROXY_URL: " https://proxy.example ",
            CONF_PROXY_TOKEN: " token ",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        CONF_COLLECTION_TIME: "08:30",
        CONF_PROXY_URL: "https://proxy.example",
        CONF_PROXY_TOKEN: "token",
    }


@pytest.mark.parametrize(
    ("overrides", "errors"),
    [
        ({CONF_COLLECTION_TIME: "bad"}, {CONF_COLLECTION_TIME: "invalid_time_format"}),
        (
            {CONF_PROXY_URL: "https://proxy.example"},
            {CONF_PROXY_TOKEN: "proxy_token_required"},
        ),
        ({CONF_PROXY_TOKEN: "token"}, {CONF_PROXY_URL: "proxy_url_required"}),
        (
            {CONF_PROXY_URL: "ftp://proxy.example", CONF_PROXY_TOKEN: "token"},
            {CONF_PROXY_URL: "invalid_proxy_url"},
        ),
    ],
)
async def test_invalid_options(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    overrides: dict[str, str],
    errors: dict[str, str],
) -> None:
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_COLLECTION_TIME: "07:00", **overrides}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors
    assert not config_entry.options
