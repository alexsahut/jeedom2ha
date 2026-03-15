"""Integration-style tests for Story 3.2 command namespace coexistence."""
from __future__ import annotations

from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock

import pytest

from resources.daemon.models.mapping import MappingResult, PublicationDecision, SwitchCapabilities
from resources.daemon.models.topology import JeedomCmd
from resources.daemon.sync.command import CommandSynchronizer


class _FakeStateSynchronizer:
    def __init__(self, active: bool):
        self.is_active = active


def _switch_mapping(eq_id: int = 9) -> MappingResult:
    return MappingResult(
        ha_entity_type="switch",
        confidence="sure",
        reason_code="switch_on_off_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Switch {eq_id}",
        commands={
            "ENERGY_ON": JeedomCmd(id=9101, name="On", generic_type="ENERGY_ON", type="action", sub_type="other"),
            "ENERGY_OFF": JeedomCmd(id=9102, name="Off", generic_type="ENERGY_OFF", type="action", sub_type="other"),
            "ENERGY_STATE": JeedomCmd(id=9103, name="State", generic_type="ENERGY_STATE", type="info", sub_type="binary"),
        },
        capabilities=SwitchCapabilities(
            has_on_off=True,
            has_state=True,
            on_off_confidence="sure",
            device_class="outlet",
        ),
    )


@pytest.mark.asyncio
async def test_command_sync_ignores_non_jeedom2ha_topics_and_preserves_runtime_registry():
    mapping = _switch_mapping(eq_id=9)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {
            mapping.ha_unique_id: PublicationDecision(
                should_publish=True,
                reason="sure",
                mapping_result=mapping,
                state_topic="jeedom2ha/9/state",
                active_or_alive=True,
            )
        },
        "state_synchronizer": _FakeStateSynchronizer(active=True),
    }
    app_before = deepcopy(app)

    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True

    sync = CommandSynchronizer(
        app=app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
        jeedom_core_apikey="core-apikey",
    )
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    out_of_scope = await sync.handle_command_message("otherpublisher/9/set", "ON")
    in_scope = await sync.handle_command_message("jeedom2ha/9/set", "ON")

    assert out_of_scope is False
    assert in_scope is True
    sync._execute_exec_cmd.assert_awaited_once_with(9101, {})
    bridge.publish_message.assert_not_called()
    assert app["mappings"].keys() == app_before["mappings"].keys()
    assert app["publications"].keys() == app_before["publications"].keys()
