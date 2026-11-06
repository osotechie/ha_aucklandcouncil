"""Test real entry lifecycle, entity states, storage, and council HTTP requests."""

from datetime import UTC, timedelta
from typing import Any
from unittest.mock import patch
from urllib.parse import quote

import pytest
from aiohttp import ClientConnectionError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant.common import MockConfigEntry, load_fixture
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.aucklandcouncil.const import (
    BASE_URL,
    CONF_COLLECTION_TIME,
    DOMAIN,
    REQUEST_HEADERS,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from custom_components.aucklandcouncil.sensor import (
    AucklandCouncilDataUpdateCoordinator,
)

from .const import NOW, PROPERTY_ID


async def test_setup_and_unload(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict[str, Any],
) -> None:
    aioclient_mock.get(
        BASE_URL.format(PROPERTY_ID), text=load_fixture("collections.html")
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][3] == REQUEST_HEADERS

    registry = er.async_get(hass)
    for key, date in {
        "rubbish": NOW.replace(day=28, hour=7),
        "food_scraps": NOW.replace(day=28, hour=7),
        "recycling": NOW.replace(month=4, day=4, hour=7),
    }.items():
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"aucklandcouncil_{PROPERTY_ID}_{key}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == date.astimezone(UTC).isoformat()
        assert state.attributes["device_class"] == "timestamp"

    stored = hass_storage[f"{STORAGE_KEY}_{PROPERTY_ID}"]["data"]
    assert stored["rubbish"] == NOW.replace(day=28, hour=7).isoformat()
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert config_entry.entry_id not in hass.data[DOMAIN]
    for entity_id, entity in registry.entities.items():
        if entity.config_entry_id == config_entry.entry_id:
            state = hass.states.get(entity_id)
            assert state is not None
            assert state.state == "unavailable"


@pytest.mark.parametrize("past", [False, True])
async def test_cached_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    aioclient_mock: AiohttpClientMocker,
    past: bool,
) -> None:
    date = NOW + timedelta(days=-1 if past else 4)
    key = f"{STORAGE_KEY}_{PROPERTY_ID}"
    hass_storage[key] = {
        "version": STORAGE_VERSION,
        "minor_version": 1,
        "key": key,
        "data": {
            "rubbish": date.isoformat(),
            "food_scraps": (NOW + timedelta(days=4)).isoformat(),
            "recycling": (NOW + timedelta(days=11)).isoformat(),
        },
    }
    if past:
        aioclient_mock.get(
            BASE_URL.format(PROPERTY_ID), text=load_fixture("collections.html")
        )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == int(past)
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator.data["rubbish"] == (
        NOW.replace(day=28, hour=7) if past else date
    )


async def test_initial_http_failure(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    aioclient_mock.get(BASE_URL.format(PROPERTY_ID), status=406)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert config_entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_refresh_failure_and_recovery(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    url = BASE_URL.format(PROPERTY_ID)
    aioclient_mock.get(url, text=load_fixture("collections.html"))
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"aucklandcouncil_{PROPERTY_ID}_rubbish"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    expected_state = state.state
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    aioclient_mock.clear_requests()
    aioclient_mock.get(url, status=503)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"

    aioclient_mock.clear_requests()
    aioclient_mock.get(url, text=load_fixture("collections.html"))
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected_state


@pytest.mark.parametrize("failure", [ClientConnectionError("offline"), TimeoutError()])
async def test_update_failure(
    coordinator: AucklandCouncilDataUpdateCoordinator,
    aioclient_mock: AiohttpClientMocker,
    failure: Exception,
) -> None:
    aioclient_mock.get(coordinator.url, exc=failure)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_proxy_request(
    coordinator: AucklandCouncilDataUpdateCoordinator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    coordinator.proxy_url = "https://proxy.example"
    coordinator.proxy_token = "secret-token"
    url = f"{coordinator.proxy_url}?url={quote(coordinator.url, safe='')}"
    aioclient_mock.get(url, text=load_fixture("collections.html"))
    data = await coordinator._fetch_collection_data()
    assert data["rubbish"] == NOW.replace(day=28, hour=7)
    assert aioclient_mock.mock_calls[0][3] == {
        **REQUEST_HEADERS,
        "X-Proxy-Token": "secret-token",
    }


async def test_options_reload(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    aioclient_mock.get(
        BASE_URL.format(PROPERTY_ID), text=load_fixture("collections.html")
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        hass.config_entries.async_update_entry(
            config_entry, options={CONF_COLLECTION_TIME: "08:30"}
        )
        await hass.async_block_till_done()
    reload.assert_awaited_once_with(config_entry.entry_id)
