"""Pytest conftest — mock Home Assistant modules before any test collection."""
import sys
from unittest.mock import MagicMock

# These must be in place before pytest collects test files that import
# custom_components.aucklandcouncil.*, because the package __init__.py
# imports homeassistant at the module level.

_HA_MODULES = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.data_entry_flow",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.helpers.config_validation",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.util",
    "homeassistant.util.dt",
]

for mod in _HA_MODULES:
    sys.modules.setdefault(mod, MagicMock())

# Provide real class stubs for base classes used in multiple inheritance
# to avoid metaclass conflicts between MagicMock instances.
_CoordinatorEntity = type("CoordinatorEntity", (), {})
_RestoreEntity = type("RestoreEntity", (), {})
_SensorEntity = type("SensorEntity", (), {})
_DataUpdateCoordinator = type("DataUpdateCoordinator", (), {"__init__": lambda *a, **kw: None})

sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = _CoordinatorEntity
sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = _DataUpdateCoordinator
sys.modules["homeassistant.helpers.restore_state"].RestoreEntity = _RestoreEntity
sys.modules["homeassistant.components.sensor"].SensorEntity = _SensorEntity

# Provide real stub classes for bases used in multi-inheritance so that
# class AucklandCouncilSensor(CoordinatorEntity, SensorEntity) does not
# trigger a metaclass conflict between two unrelated MagicMock objects.


class _StubCoordinatorEntity:
    """Minimal stand-in for CoordinatorEntity."""

    def __init__(self, coordinator=None):
        self.coordinator = coordinator


class _StubSensorEntity:
    """Minimal stand-in for SensorEntity."""


sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = (
    _StubCoordinatorEntity
)
sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = type(
    "DataUpdateCoordinator", (), {"__init__": lambda self, *a, **kw: None}
)
sys.modules["homeassistant.components.sensor"].SensorEntity = _StubSensorEntity
