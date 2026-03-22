from unittest.mock import MagicMock, patch

import pytest

_FAKE_CLI_ARGS = [
    "--loglevel", "debug",
    "--sockethost", "127.0.0.1",
    "--socketport", "0",
    "--callback", "http://127.0.0.1/fake",
    "--apikey", "test-api-key",
    "--pid", "/tmp/test-jeedom2ha.pid",
    "--cycle", "0.5",
]

LOCAL_SECRET = "test-secret-abc123"


@pytest.fixture(autouse=True)
def fake_cli_args():
    with patch("sys.argv", ["main.py"] + _FAKE_CLI_ARGS):
        yield


@pytest.fixture
def http_app():
    from resources.daemon.transport.http_server import create_app

    app = create_app(local_secret=LOCAL_SECRET)
    bridge = MagicMock()
    bridge.is_connected = False
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    return app


@pytest.fixture
async def http_client(http_app, aiohttp_client):
    return await aiohttp_client(http_app)


async def test_published_scope_contract_is_available_after_sync(http_client, http_app):
    payload = {
        "version": "1.0",
        "objects": [{"id": "1", "name": "Salon"}],
        "eq_logics": [
            {
                "id": "10",
                "name": "Prise Incluse",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [
                    {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                    {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                    {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                ],
            },
            {
                "id": "11",
                "name": "Prise Exclue Visible",
                "object_id": "1",
                "is_enable": "1",
                "is_excluded": "1",
                "eq_type": "virtual",
                "cmds": [
                    {"id": "310", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                ],
            },
        ],
        "published_scope": {
            "global": {"raw_state": "include"},
            "pieces": {"1": {"raw_state": "exclude"}},
            "equipements": {
                "10": {"raw_state": "include"},
                "11": {"raw_state": "inherit"},
            },
        },
    }

    resp = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": payload},
    )
    assert resp.status == 200
    data = await resp.json()

    contract = data["payload"]["published_scope"]
    assert contract["global"]["counts"]["total"] == 2
    assert contract["global"]["counts"]["include"] == 1
    assert contract["global"]["counts"]["exclude"] == 1
    assert contract["global"]["counts"]["exceptions"] == 1
    assert "has_pending_home_assistant_changes" in contract["global"]

    eq_by_id = {eq["eq_id"]: eq for eq in contract["equipements"]}
    assert 10 in eq_by_id
    assert 11 in eq_by_id  # Exclu mais visible dans le contrat backend

    assert eq_by_id[10]["effective_state"] == "include"
    assert eq_by_id[10]["decision_source"] == "exception_equipement"
    assert eq_by_id[10]["is_exception"] is True
    assert isinstance(eq_by_id[10]["has_pending_home_assistant_changes"], bool)

    assert eq_by_id[11]["effective_state"] == "exclude"
    assert eq_by_id[11]["decision_source"] == "piece"
    assert eq_by_id[11]["is_exception"] is False
    assert isinstance(eq_by_id[11]["has_pending_home_assistant_changes"], bool)

    # Contrat persisté en mémoire backend (réutilisable par stories suivantes sans recalcul UI)
    assert http_app["published_scope"]["global"]["counts"]["total"] == 2

    scope_resp = await http_client.get(
        "/system/published_scope",
        headers={"X-Local-Secret": LOCAL_SECRET},
    )
    assert scope_resp.status == 200
    scope_data = await scope_resp.json()
    assert scope_data["action"] == "system.published_scope"
    assert scope_data["status"] == "ok"
    assert len(scope_data["payload"]["equipements"]) == 2


async def test_published_scope_endpoint_requires_prior_sync(http_client):
    resp = await http_client.get(
        "/system/published_scope",
        headers={"X-Local-Secret": LOCAL_SECRET},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "error"
    assert "appelez /action/sync" in data["message"]


async def test_published_scope_legacy_plugin_fallback_avoids_include_drift(http_client):
    payload = {
        "version": "1.0",
        "objects": [{"id": "1", "name": "Salon"}],
        "eq_logics": [
            {
                "id": "12",
                "name": "Eq Legacy Plugin Exclu",
                "object_id": "1",
                "is_enable": "1",
                "is_excluded": "1",
                "exclusion_source": "plugin",
                "eq_type": "virtual",
                "cmds": [
                    {"id": "410", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                    {"id": "411", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                    {"id": "412", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                ],
            }
        ],
        "published_scope": {
            "global": {"raw_state": "include"},
            "pieces": {},
            "equipements": {},
        },
    }

    resp = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": payload},
    )
    assert resp.status == 200
    data = await resp.json()
    eq = data["payload"]["published_scope"]["equipements"][0]
    assert eq["eq_id"] == 12
    assert eq["effective_state"] == "exclude"
