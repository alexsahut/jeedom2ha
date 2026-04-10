"""
conftest.py — Root pytest configuration for jeedom2ha daemon tests.
Provides shared fixtures and test utilities for unit and integration tests.
"""
import pytest
from typing import Optional, Union, List


# ---------------------------------------------------------------------------
# Global fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def jeedom_eq_factory():
    """
    Factory fixture that returns a callable for generating minimal Jeedom
    eqLogic dictionaries (backend mapping-engine input).

    Usage:
        def test_something(jeedom_eq_factory):
            eq = jeedom_eq_factory(id=42, name="Lampe salon")
    """
    def _make_eq(
        id: int = 1,
        name: str = "Test Equipment",
        object_id: int = 10,
        is_enable: bool = True,
        generic_type: Optional[str] = None,
        cmds: Optional[List] = None,
    ) -> dict:
        return {
            "jeedom_eq_id": id,
            "name": name,
            "jeedom_object_id": object_id,
            "is_enable": is_enable,
            "generic_type": generic_type,
            "cmds": cmds or [],
        }

    return _make_eq


@pytest.fixture
def jeedom_cmd_factory():
    """
    Factory fixture for generating Jeedom command dictionaries.

    Usage:
        def test_something(jeedom_cmd_factory):
            cmd = jeedom_cmd_factory(id=100, generic_type="LIGHT_STATE")
    """
    def _make_cmd(
        id: int = 100,
        name: str = "Test Command",
        generic_type: str = "",
        cmd_type: str = "info",
        sub_type: str = "numeric",
        current_value: Optional[Union[float, str]] = None,
    ) -> dict:
        return {
            "jeedom_cmd_id": id,
            "name": name,
            "generic_type": generic_type,
            "type": cmd_type,
            "sub_type": sub_type,
            "current_value": current_value,
        }

    return _make_cmd
