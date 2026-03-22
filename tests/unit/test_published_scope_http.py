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


async def test_published_scope_contract_fields_for_ui_console_are_stable(http_client):
    payload = {
        "version": "1.0",
        "objects": [
            {"id": "1", "name": "Salon"},
            {"id": "2", "name": "Cuisine"},
        ],
        "eq_logics": [
            {
                "id": "20",
                "name": "Lampe Salon",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [
                    {"id": "510", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "LIGHT_STATE"},
                ],
            },
            {
                "id": "21",
                "name": "Prise Cuisine",
                "object_id": "2",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [
                    {"id": "610", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                    {"id": "611", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                    {"id": "612", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                ],
            },
        ],
        "published_scope": {
            "global": {"raw_state": "include"},
            "pieces": {"2": {"raw_state": "exclude"}},
            "equipements": {"21": {"raw_state": "inherit"}},
        },
    }

    sync_resp = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": payload},
    )
    assert sync_resp.status == 200
    sync_data = await sync_resp.json()
    contract = sync_data["payload"]["published_scope"]

    assert set(contract["global"]["counts"].keys()) == {"total", "include", "exclude", "exceptions"}
    assert isinstance(contract["pieces"], list)
    assert len(contract["pieces"]) == 2
    for piece in contract["pieces"]:
        assert {"object_id", "object_name", "counts"}.issubset(piece.keys())
        assert set(piece["counts"].keys()) == {"total", "include", "exclude", "exceptions"}
    assert isinstance(contract["equipements"], list)
    assert len(contract["equipements"]) == 2
    for equipment in contract["equipements"]:
        assert {
            "eq_id",
            "object_id",
            "effective_state",
            "decision_source",
            "is_exception",
            "has_pending_home_assistant_changes",
        }.issubset(equipment.keys())

    scope_resp = await http_client.get(
        "/system/published_scope",
        headers={"X-Local-Secret": LOCAL_SECRET},
    )
    assert scope_resp.status == 200
    scope_data = await scope_resp.json()
    assert scope_data["status"] == "ok"
    assert scope_data["payload"] == contract


async def test_published_scope_contract_is_replaced_after_second_sync(http_client):
    first_payload = {
        "version": "1.0",
        "objects": [{"id": "1", "name": "Salon"}],
        "eq_logics": [
            {
                "id": "30",
                "name": "Lampe A",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [
                    {"id": "710", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "LIGHT_STATE"},
                ],
            },
            {
                "id": "31",
                "name": "Lampe B",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [
                    {"id": "810", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "LIGHT_STATE"},
                ],
            },
        ],
        "published_scope": {
            "global": {"raw_state": "include"},
            "pieces": {},
            "equipements": {},
        },
    }
    second_payload = {
        "version": "1.0",
        "objects": [{"id": "1", "name": "Salon"}],
        "eq_logics": first_payload["eq_logics"],
        "published_scope": {
            "global": {"raw_state": "include"},
            "pieces": {"1": {"raw_state": "exclude"}},
            "equipements": {"30": {"raw_state": "include"}},
        },
    }

    first_sync = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": first_payload},
    )
    assert first_sync.status == 200
    first_contract = (await first_sync.json())["payload"]["published_scope"]
    assert first_contract["global"]["counts"]["include"] == 2
    assert first_contract["global"]["counts"]["exclude"] == 0

    second_sync = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": second_payload},
    )
    assert second_sync.status == 200
    second_contract = (await second_sync.json())["payload"]["published_scope"]
    assert second_contract["global"]["counts"]["include"] == 1
    assert second_contract["global"]["counts"]["exclude"] == 1
    assert second_contract != first_contract

    scope_resp = await http_client.get(
        "/system/published_scope",
        headers={"X-Local-Secret": LOCAL_SECRET},
    )
    assert scope_resp.status == 200
    scope_data = await scope_resp.json()
    assert scope_data["status"] == "ok"
    assert scope_data["payload"] == second_contract


async def test_published_scope_legacy_object_fallback_with_default_inherit_piece_entry(http_client):
    payload = {
        "version": "1.0",
        "objects": [{"id": "1", "name": "Bureau"}],
        "eq_logics": [
            {
                "id": "40",
                "name": "Lampe Bureau",
                "object_id": "1",
                "is_enable": "1",
                "is_excluded": "1",
                "exclusion_source": "object",
                "eq_type": "virtual",
                "cmds": [
                    {"id": "910", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "LIGHT_STATE"},
                ],
            }
        ],
        "published_scope": {
            "global": {"raw_state": "include"},
            "pieces": {
                "1": {"raw_state": "inherit", "source": "default_inherit"},
            },
            "equipements": {
                "40": {"raw_state": "inherit", "source": "default_inherit"},
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
    eq = data["payload"]["published_scope"]["equipements"][0]

    assert eq["eq_id"] == 40
    assert eq["effective_state"] == "exclude"
    assert eq["decision_source"] == "piece"


async def test_published_scope_contract_replaced_after_legacy_object_change(http_client):
    base_eq = {
        "id": "50",
        "name": "Prise Bureau",
        "object_id": "1",
        "is_enable": "1",
        "eq_type": "virtual",
        "cmds": [
            {"id": "1010", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
            {"id": "1011", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
            {"id": "1012", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
        ],
    }
    default_scope = {
        "global": {"raw_state": "include"},
        "pieces": {"1": {"raw_state": "inherit", "source": "default_inherit"}},
        "equipements": {"50": {"raw_state": "inherit", "source": "default_inherit"}},
    }
    first_payload = {
        "version": "1.0",
        "objects": [{"id": "1", "name": "Bureau"}],
        "eq_logics": [base_eq],
        "published_scope": default_scope,
    }
    second_payload = {
        "version": "1.0",
        "objects": [{"id": "1", "name": "Bureau"}],
        "eq_logics": [{**base_eq, "is_excluded": "1", "exclusion_source": "object"}],
        "published_scope": default_scope,
    }

    first_sync = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": first_payload},
    )
    assert first_sync.status == 200
    first_contract = (await first_sync.json())["payload"]["published_scope"]
    assert first_contract["global"]["counts"]["include"] == 1
    assert first_contract["global"]["counts"]["exclude"] == 0

    second_sync = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": second_payload},
    )
    assert second_sync.status == 200
    second_contract = (await second_sync.json())["payload"]["published_scope"]
    eq = second_contract["equipements"][0]
    assert eq["effective_state"] == "exclude"
    assert eq["decision_source"] == "piece"
    assert second_contract["global"]["counts"]["exclude"] == 1
    assert second_contract != first_contract

    scope_resp = await http_client.get(
        "/system/published_scope",
        headers={"X-Local-Secret": LOCAL_SECRET},
    )
    assert scope_resp.status == 200
    scope_data = await scope_resp.json()
    assert scope_data["status"] == "ok"
    assert scope_data["payload"] == second_contract
