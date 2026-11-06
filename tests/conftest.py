"""Shared fixtures using the official Home Assistant test framework."""

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aucklandcouncil.const import (
    CONF_COLLECTION_TIME,
    CONF_PROPERTY_ID,
    DEFAULT_COLLECTION_TIME,
    DOMAIN,
)
from custom_components.aucklandcouncil.sensor import (
    AucklandCouncilDataUpdateCoordinator,
)

from .const import NOW, PROPERTY_ID


@pytest.fixture(autouse=True)
async def configure_time(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(NOW)
    await hass.config.async_set_time_zone("Pacific/Auckland")


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=PROPERTY_ID,
        data={
            CONF_PROPERTY_ID: PROPERTY_ID,
            CONF_COLLECTION_TIME: DEFAULT_COLLECTION_TIME,
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def coordinator(hass: HomeAssistant) -> AucklandCouncilDataUpdateCoordinator:
    return AucklandCouncilDataUpdateCoordinator(
        hass, PROPERTY_ID, DEFAULT_COLLECTION_TIME
    )
