"""Integration tests for the inbound /action/state_update route (Story 12.1)."""

import pytest

from transport.http_server import create_app
from sync.state import StateSynchronizer
from models.mapping import MappingResult, PublicationDecision, SensorCapabilities
from models.topology import JeedomCmd


SECRET = "test-secret-12.1"


class _FakeBridge:
    def __init__(self, connected=True, publish_ok=True):
        self.is_connected = connected
        self._publish_ok = publish_ok
        self.published = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return self._publish_ok


def _published_sensor(eq_id=553, cmd_id=5302):
    cmd = JeedomCmd(id=cmd_id, name="Courant", type="info", sub_type="numeric",
                    current_value="12.0", unit="A")
    mapping = MappingResult(
        ha_entity_type="sensor", confidence="sure",
        reason_code="sensor_multi_routeur_solaire", jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}_cmd_{cmd_id}", ha_name="Courant",
        commands={str(cmd_id): cmd}, capabilities=SensorCapabilities(has_state=True),
        reason_details={"cmd_id": cmd_id, "state_topic": f"jeedom2ha/{eq_id}/{cmd_id}/state"},
    )
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic=f"jeedom2ha/{eq_id}/{cmd_id}/state", discovery_published=True,
    )
    mapping.publication_decision_ref = decision
    return decision


@pytest.fixture
def bridge():
    return _FakeBridge()


@pytest.fixture
def app(bridge):
    app = create_app(local_secret=SECRET)
    app["mqtt_bridge"] = bridge
    app["publications"] = {553: _published_sensor(553, 5302)}
    app["state_synchronizer"] = StateSynchronizer(app=app, mqtt_bridge=bridge)
    return app


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def test_state_update_publishes_via_route(cli, bridge):
    resp = await cli.post(
        "/action/state_update",
        headers={"X-Local-Secret": SECRET},
        json={"action": "state_update",
              "payload": {"eq_id": 553, "cmd_id": 5302, "value": "13.5"}},
    )
    assert resp.status == 200
    body = await resp.json()
    assert body == {"status": "ok", "published": True}
    assert bridge.published == [("jeedom2ha/553/5302/state", "13.5", 1, True)]


async def test_state_update_accepts_direct_payload(cli, bridge):
    resp = await cli.post(
        "/action/state_update",
        headers={"X-Local-Secret": SECRET},
        json={"eq_id": 553, "cmd_id": 5302, "value": "14"},
    )
    assert resp.status == 200
    assert (await resp.json())["published"] is True
    assert bridge.published[-1] == ("jeedom2ha/553/5302/state", "14", 1, True)


async def test_state_update_rejects_without_secret(cli, bridge):
    resp = await cli.post(
        "/action/state_update",
        json={"eq_id": 553, "cmd_id": 5302, "value": "1"},
    )
    assert resp.status == 401
    assert bridge.published == []


async def test_state_update_requires_eq_and_cmd(cli, bridge):
    resp = await cli.post(
        "/action/state_update",
        headers={"X-Local-Secret": SECRET},
        json={"payload": {"value": "1"}},
    )
    assert resp.status == 400
    assert bridge.published == []


async def test_state_update_unknown_entity_returns_not_published(cli, bridge):
    resp = await cli.post(
        "/action/state_update",
        headers={"X-Local-Secret": SECRET},
        json={"payload": {"eq_id": 999, "cmd_id": 1, "value": "1"}},
    )
    assert resp.status == 200
    assert (await resp.json())["published"] is False
    assert bridge.published == []


async def test_state_listeners_lists_published_targets(cli):
    resp = await cli.get(
        "/system/state_listeners",
        headers={"X-Local-Secret": SECRET},
    )
    assert resp.status == 200
    body = await resp.json()
    assert body["status"] == "ok"
    assert body["listeners"] == [
        {"eq_id": 553, "cmd_id": 5302, "ha_type": "sensor",
         "state_topic": "jeedom2ha/553/5302/state"},
    ]


async def test_state_listeners_rejects_without_secret(cli):
    resp = await cli.get("/system/state_listeners")
    assert resp.status == 401
