"""Front v2 — Lot 3 : champs additifs du démon (contrat section 4), un cas par champ et par conseil.

Corpus : corpus doré + trois équipements fictifs (multiprise, portail, ventilateur). Lecture
seule : la non-régression de la projection est prouvée dans
`test_front_v2_lot3_projection_identique.py`.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from models import ha_side
from transport.http_server import create_app

from .front_v2_lot3_corpus import (
    MULTIPRISE_ID, NAME_MISMATCH_ID, PORTAIL_ID, VENTILATEUR_ID, load_corpus, sync_body,
)
from .test_front_v2_lot3_projection_identique import RawRecordingBridge

SECRET = "test-secret-lot3-champs"
H = {"X-Local-Secret": SECRET}
HA_KEYS = {
    "ha_unique_id", "ha_default_entity_id", "ha_name", "ha_device_name", "ha_device_class",
    "ha_unit", "ha_controllable", "ha_capabilities",
}
CMD_KEYS = {"cmd_type", "cmd_sub_type", "linked_state_cmd_id"}
CAPABILITIES = {
    "on_off", "brightness", "position", "tilt", "stop", "temperature", "mode", "press", "lock",
    "open_close", "read",
}
PREVIEW_ENTITY_KEYS = {
    "ha_entity_type", "ha_unique_id", "ha_name", "ha_default_entity_id", "ha_controllable",
    "ha_capabilities", "will_publish", "reason",
}


@pytest.fixture
async def synced(aiohttp_client, tmp_path):
    app = create_app(local_secret=SECRET)
    bridge = RawRecordingBridge()
    app["mqtt_bridge"] = bridge
    app["data_dir"] = str(tmp_path)
    cli = await aiohttp_client(app)
    resp = await cli.post("/action/sync", json=sync_body(load_corpus()), headers=H)
    assert resp.status == 200, await resp.text()
    return app, bridge, cli


async def _tree(cli, eq_id):
    resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=H)
    assert resp.status == 200
    return (await resp.json())["payload"]


async def _status(cli):
    resp = await cli.get("/system/status", headers=H)
    assert resp.status == 200
    return (await resp.json())["payload"]


async def _preview(cli, body):
    resp = await cli.post("/system/overrides/preview", json={"payload": body}, headers=H)
    assert resp.status == 200, await resp.text()
    return (await resp.json())["payload"]


# ---------------------------------------------------------------------------
# GET /system/status
# ---------------------------------------------------------------------------

async def test_status_porte_ha_et_publication(synced):
    _app, bridge, cli = synced
    payload = await _status(cli)
    assert payload["ha"] == {"birth_seen_at": None, "discovery_prefix": "homeassistant"}
    # Dénombrement recoupé avec ce qui est réellement parti sur le broker au sync.
    configs = [c for c in bridge.calls if c["topic"].startswith("homeassistant/") and c["payload"]]
    devices = {json.loads(c["payload"])["device"]["identifiers"][0] for c in configs}
    assert payload["publication"] == {
        "equipments_published": len(devices),
        "entities_published": len(configs),
        "scenarios_published": 0,
    }
    # Champs historiques intacts.
    for key in ("version", "uptime", "mqtt", "demon", "broker", "derniere_synchro_terminee"):
        assert key in payload


async def test_status_avant_tout_sync(aiohttp_client):
    cli = await aiohttp_client(create_app(local_secret=SECRET))
    payload = await _status(cli)
    assert payload["ha"]["birth_seen_at"] is None
    assert payload["publication"] == {"equipments_published": 0, "entities_published": 0, "scenarios_published": 0}


async def test_birth_seen_at_pose_par_le_rappel_birth(aiohttp_client):
    app = create_app(local_secret=SECRET)
    captured = {}

    async def fake_start(params, on_reconnect_cb=None, on_ha_birth_cb=None):
        captured["birth"] = on_ha_birth_cb

    bridge = app["mqtt_bridge"]
    cli = await aiohttp_client(app)
    with patch.object(bridge, "stop", AsyncMock()), patch.object(bridge, "start", side_effect=fake_start):
        resp = await cli.post("/action/mqtt_connect", json={"payload": {"host": "broker.example.test"}}, headers=H)
        assert resp.status == 200
    with patch("transport.http_server._publish_bridge_discovery", AsyncMock()), \
            patch("transport.http_server._republish_all_from_cache", AsyncMock()) as republish:
        await captured["birth"]()
        republish.assert_awaited_once()
    seen = (await _status(cli))["ha"]["birth_seen_at"]
    assert seen is not None and datetime.fromisoformat(seen).tzinfo is not None


# ---------------------------------------------------------------------------
# GET /system/mapping_overrides/{eq_id}
# ---------------------------------------------------------------------------

async def test_multiprise_trois_entites_lecture_seule_et_conseil(synced):
    _app, _bridge, cli = synced
    tree = await _tree(cli, MULTIPRISE_ID)
    assert len(tree["entities"]) == 3
    for entity in tree["entities"]:
        assert HA_KEYS <= set(entity)
        assert entity["ha_entity_type"] == "binary_sensor"
        assert entity["ha_controllable"] is False
        assert entity["ha_capabilities"] == ["read"]
        assert entity["ha_device_name"] == "Multiprise bureau"
    assert [e["ha_default_entity_id"] for e in tree["entities"]] == [
        "binary_sensor.jeedom2ha_9801_980101",
        "binary_sensor.jeedom2ha_9801_980102",
        "binary_sensor.jeedom2ha_9801_980103",
    ]
    assert tree["hints"] == [{
        "code": "actions_not_linked_to_state",
        "cmd_ids": [980111, 980112, 980113, 980121, 980122, 980123],
        "details": {
            "families": ["SWITCH"],
            "outputs": 3,
            "state_cmd_ids": [980101, 980102, 980103],
            "unlinked_order_cmd_ids": [980111, 980112, 980113, 980121, 980122, 980123],
        },
    }]


async def test_champs_ha_lus_dans_le_payload_publie(synced):
    """Chaque entité publiée : identifiant, nom, appareil, classe, unité et pilotable = payload parti sur le broker."""
    app, bridge, cli = synced
    published = {}
    for call in bridge.calls:
        if call["topic"].startswith("homeassistant/") and call["payload"]:
            payload = json.loads(call["payload"])
            published[payload["unique_id"]] = payload
    checked = 0
    for eq_id in sorted(app["topology"].eq_logics):
        for entity in (await _tree(cli, eq_id))["entities"]:
            payload = published.get(entity["ha_unique_id"])
            if payload is None:
                continue
            checked += 1
            assert entity["ha_default_entity_id"] == payload["default_entity_id"]
            assert entity["ha_name"] == payload.get("name")
            assert entity["ha_device_name"] == payload["device"]["name"]
            assert entity["ha_device_class"] == payload.get("device_class")
            assert entity["ha_unit"] == payload.get("unit_of_measurement")
            assert entity["ha_controllable"] == any(
                k.endswith("command_topic") or k == "set_position_topic" for k in payload
            )
            assert set(entity["ha_capabilities"]) <= CAPABILITIES
    assert checked == len(published)


async def test_capacites_types_varies(synced):
    _app, _bridge, cli = synced
    by_eq = {}
    for eq_id in (1005, 2003, 230, 7000, VENTILATEUR_ID):
        by_eq[eq_id] = (await _tree(cli, eq_id))["entities"][0]
    assert by_eq[1005]["ha_capabilities"] == ["on_off", "brightness", "read"]
    assert by_eq[2003]["ha_capabilities"] == ["open_close", "stop", "read"]
    assert by_eq[230]["ha_capabilities"] == ["mode", "read"]
    assert by_eq[7000]["ha_controllable"] is False and by_eq[7000]["ha_unit"] == "°C"
    assert by_eq[VENTILATEUR_ID]["ha_capabilities"] == ["on_off", "read"]


async def test_commandes_type_sous_type_etat_relie(synced):
    _app, _bridge, cli = synced
    commands = {c["jeedom_cmd_id"]: c for c in (await _tree(cli, VENTILATEUR_ID))["commands"]}
    for command in commands.values():
        assert CMD_KEYS <= set(command)
    assert commands[980301]["cmd_type"] == "info" and commands[980301]["cmd_sub_type"] == "binary"
    assert commands[980302]["cmd_type"] == "action" and commands[980302]["linked_state_cmd_id"] == 980301
    assert commands[980304]["cmd_sub_type"] == "slider" and commands[980304]["linked_state_cmd_id"] == 980305
    assert commands[980305]["linked_state_cmd_id"] is None


async def test_conseil_portail_sans_ordres(synced):
    _app, _bridge, cli = synced
    tree = await _tree(cli, PORTAIL_ID)
    assert tree["entities"][0]["ha_controllable"] is False
    assert tree["hints"] == [{
        "code": "binary_state_without_orders", "cmd_ids": [980201],
        "details": {"generic_types": ["BARRIER_STATE"]},
    }]


async def test_conseil_vitesse_non_reprise(synced):
    _app, _bridge, cli = synced
    tree = await _tree(cli, VENTILATEUR_ID)
    assert tree["hints"] == [{
        "code": "speed_not_carried", "cmd_ids": [980304, 980305], "details": {"carried_as": "switch"},
    }]


async def test_conseil_nom_et_type_en_desaccord(synced):
    _app, _bridge, cli = synced
    tree = await _tree(cli, NAME_MISMATCH_ID)
    assert tree["hints"] == [{
        "code": "name_type_mismatch", "cmd_ids": [40021, 40022, 40023],
        "details": {"ha_entity_type": "switch", "matched_keyword": "volet"},
    }]


async def test_prudence_conseils_sur_tout_le_corpus(synced):
    """Corpus doré entier : seuls les cas attendus portent un conseil (en cas de doute, aucun)."""
    app, _bridge, cli = synced
    found = {}
    for eq_id in sorted(app["topology"].eq_logics):
        tree = await _tree(cli, eq_id)
        assert isinstance(tree["hints"], list)
        if tree["hints"]:
            found[eq_id] = [hint["code"] for hint in tree["hints"]]
    assert found == {
        NAME_MISMATCH_ID: ["name_type_mismatch"],
        8004: ["binary_state_without_orders"],  # corpus doré : état de serrure seul, aucun ordre
        MULTIPRISE_ID: ["actions_not_linked_to_state"],
        PORTAIL_ID: ["binary_state_without_orders"],
        VENTILATEUR_ID: ["speed_not_carried"],
    }


async def test_route_agregee_inchangee(synced):
    """Les champs du Lot 3 n'entrent pas dans `/system/equipment_states` (liste blanche)."""
    _app, _bridge, cli = synced
    resp = await cli.get("/system/equipment_states", headers=H)
    assert resp.status == 200
    text = await resp.text()
    for key in ("hints", "ha_unique_id", "ha_controllable", "cmd_type", "linked_state_cmd_id", "entities_before"):
        assert f'"{key}"' not in text


# ---------------------------------------------------------------------------
# POST /system/overrides/preview
# ---------------------------------------------------------------------------

async def test_apercu_changement_de_type(synced):
    _app, _bridge, cli = synced
    payload = await _preview(cli, {"jeedom_eq_id": PORTAIL_ID, "jeedom_cmd_id": 980201, "ha_entity_type": "sensor"})
    assert [set(e) for e in payload["entities_before"]] == [PREVIEW_ENTITY_KEYS]
    assert payload["entities_before"][0]["ha_default_entity_id"] == "binary_sensor.jeedom2ha_9802"
    assert payload["entities_after"][0]["ha_default_entity_id"] == "sensor.jeedom2ha_9802"
    assert payload["entity_id_changes"] == [
        {"from": "binary_sensor.jeedom2ha_9802", "to": "sensor.jeedom2ha_9802"},
    ]
    # Champs historiques intacts.
    for key in ("auto", "overridden", "support_export", "native_generic_types", "covered", "mapped"):
        assert key in payload


async def test_apercu_exclusion_equipement(synced):
    _app, _bridge, cli = synced
    payload = await _preview(cli, {"jeedom_eq_id": MULTIPRISE_ID, "publication_policy": "exclude"})
    assert all(e["will_publish"] for e in payload["entities_before"])
    assert not any(e["will_publish"] for e in payload["entities_after"])
    assert payload["entity_id_changes"] == [
        {"from": f"binary_sensor.jeedom2ha_9801_{cid}", "to": None} for cid in (980101, 980102, 980103)
    ]


async def test_apercu_sans_changement(synced):
    _app, _bridge, cli = synced
    payload = await _preview(cli, {"jeedom_eq_id": 1005, "jeedom_cmd_id": 10051, "ha_entity_type": "light"})
    assert payload["entities_before"] == payload["entities_after"]
    assert payload["entity_id_changes"] == []


async def test_apercu_equipement_inelegible(synced):
    _app, _bridge, cli = synced
    payload = await _preview(cli, {"jeedom_eq_id": 5000, "publication_policy": "force_publish"})
    assert payload["mapped"] is False
    assert payload["entities_before"] == [] and payload["entities_after"] == []
    assert payload["entity_id_changes"] == []


async def test_apercu_commande_non_couverte(synced):
    app, _bridge, cli = synced
    tree = await _tree(cli, 230)
    uncovered = next(c["jeedom_cmd_id"] for c in tree["commands"] if not c["covered"])
    payload = await _preview(cli, {"jeedom_eq_id": 230, "jeedom_cmd_id": uncovered, "ha_entity_type": "sensor"})
    assert payload["covered"] is False
    assert payload["entities_before"][0]["ha_entity_type"] == "alarm_control_panel"
    assert payload["entities_after"] is None and payload["entity_id_changes"] is None


# ---------------------------------------------------------------------------
# models/ha_side.py — fonctions pures
# ---------------------------------------------------------------------------

def test_pilotable_et_capacites_depuis_un_payload():
    assert ha_side.is_controllable(None) is None
    assert ha_side.is_controllable({"state_topic": "x"}) is False
    assert ha_side.is_controllable({"set_position_topic": "x"}) is True
    cover = {
        "command_topic": "c", "state_topic": "s", "payload_stop": None,
        "position_topic": "p", "set_position_topic": "sp",
    }
    assert ha_side.capabilities_from_payload("cover", cover) == ["open_close", "position", "read"]
    climate = {"temperature_command_topic": "t", "mode_command_topic": "m", "current_temperature_topic": "c"}
    assert ha_side.capabilities_from_payload("climate", climate) == ["temperature", "mode", "read"]
    assert ha_side.capabilities_from_payload("button", {"command_topic": "b"}) == ["press"]
    assert ha_side.capabilities_from_payload("lock", {"command_topic": "l", "state_topic": "s"}) == ["lock", "read"]
    assert ha_side.capabilities_from_payload("valve", {"command_topic": "v"}) == ["open_close"]
    assert ha_side.capabilities_from_payload("sensor", None) is None


def test_changements_d_identifiant():
    def row(uid, eid, publish=True):
        return {"ha_unique_id": uid, "ha_default_entity_id": eid, "will_publish": publish}

    before = [row("a", "switch.a"), row("b", "sensor.b"), row("c", "sensor.c", publish=False)]
    after = [row("a", "light.a"), row("c", "sensor.c")]
    assert ha_side.entity_id_changes(before, after) == [
        {"from": "switch.a", "to": "light.a"},
        {"from": "sensor.b", "to": None},
        {"from": None, "to": "sensor.c"},
    ]


def test_mapping_hors_contrat_ne_casse_pas_la_lecture():
    class Broken:
        ha_entity_type = "light"
        ha_unique_id = "jeedom2ha_eq_1"

    fields = ha_side.entity_ha_fields(Broken(), object())
    assert fields["ha_unique_id"] == "jeedom2ha_eq_1"
    assert fields["ha_controllable"] is None and fields["ha_capabilities"] is None
