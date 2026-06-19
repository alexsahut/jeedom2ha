"""Story 11.2 PE — Chauffe-eau eq554 multi-domaine lecture seule.

L'eqLogic « Chauffe-eau » eq554 (eq_type virtual, partagé par 64 eqLogics) doit
projeter PLUSIEURS domaines HA rattachés au même device `jeedom2ha_554` :

- 1 ``switch`` (préservé — ENERGY_ON/OFF/STATE) : comportement historique intact ;
- 12 ``sensor`` (commandes info numériques, identité par commande) ;
- 1 ``binary_sensor`` (#5510 « chauffe complète ») ; la binaire ENERGY_STATE
  (#5708 « activé ») est EXCLUE car déjà portée par le switch (anti-doublon).

Gating volontairement borné à un allowlist d'IDs eqLogic (`MULTI_DOMAIN_EQ_IDS`,
Option A) : `virtual` est mutualisé, on ne peut pas gater sur eq_type sans
emporter 63 autres équipements. Aucun autre eqLogic ne devient multi-domaine.

Fixture fidèle au terrain (box 192.168.1.21, capture 2026-06-19).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from cache.disk_cache import load_publications_cache, save_publications_cache
from discovery.publisher import DiscoveryPublisher
from models.mapping import PublicationDecision
from mapping.binary_sensor import BinarySensorMapper
from mapping.registry import MapperRegistry
from mapping.sensor import SensorMapper
from mapping.switch import SwitchMapper
from models.mapping import SwitchCapabilities
from models.topology import (
    MULTI_DOMAIN_EQ_IDS,
    JeedomCmd,
    JeedomEqLogic,
    JeedomObject,
    TopologySnapshot,
)
from transport.http_server import _collect_unpublish_node_ids, create_app

_SECRET = "test-secret-story-11-2"

# Capture terrain eq554 — (id, name, type, sub_type, generic_type, unit).
# 21 commandes : 12 info/numeric, 2 info/binary, 1 info/string, 6 action.
_EQ554_CMDS = [
    (5205, "Routage", "info", "numeric", None, "%"),
    (5530, "Routage réel", "info", "numeric", "ENERGY_STATE", "%"),
    (5706, "On_5701", "action", "other", "ENERGY_ON", None),
    (5707, "Off_5702", "action", "other", "ENERGY_OFF", None),
    (5204, "Rafraichir", "action", "other", None, None),
    (5206, "Puissance", "info", "numeric", None, "W"),
    (5489, "etat", "info", "string", None, None),
    (5372, "Absence", "action", "other", None, None),
    (5490, "Manu", "action", "other", "ENERGY_ON", None),
    (5491, "auto", "action", "other", "ENERGY_OFF", None),
    (5510, "chauffe complète dans la journée", "info", "binary", None, None),
    (5531, "Routage chauffe complete", "info", "numeric", None, "%"),
    (5535, "CE Kwh chauffe complete", "info", "numeric", None, "kWh"),
    (5532, "Routage 24H jusqua 22H36 hier", "info", "numeric", None, "%"),
    (5533, "Routage aujourdhui", "info", "numeric", None, "%"),
    (5534, "CE kWh 24H jusqua 22H36 hier", "info", "numeric", None, "kWh"),
    (5527, "CE kWh depuis 22H36 hier", "info", "numeric", None, "kWh"),
    (5542, "eq H de chauffe hier", "info", "numeric", None, "H"),
    (5538, "eq H de chauffe aujourdhui", "info", "numeric", None, "H"),
    (5543, "mediane chauffe complete sur 7 jours", "info", "numeric", None, "%"),
    (5708, "activé", "info", "binary", "ENERGY_STATE", None),
]

# Sous-ensembles attendus.
_EXPECTED_SENSOR_CMD_IDS = {
    5205, 5530, 5206, 5531, 5535, 5532, 5533, 5534, 5527, 5542, 5538, 5543,
}
_EXPECTED_BINARY_CMD_ID = 5510  # #5708 (ENERGY_STATE) volontairement exclu


def _eq554() -> JeedomEqLogic:
    return JeedomEqLogic(
        id=554,
        name="Chauffe-eau",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(
                id=cmd_id,
                name=name,
                generic_type=generic_type,
                type=cmd_type,
                sub_type=sub_type,
                unit=unit,
            )
            for cmd_id, name, cmd_type, sub_type, generic_type, unit in _EQ554_CMDS
        ],
    )


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-06-19T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={eq.id: eq},
    )


# ---------------------------------------------------------------------------
# Gating — allowlist borné (Option A)
# ---------------------------------------------------------------------------


def test_eq554_is_in_multi_domain_allowlist():
    assert 554 in MULTI_DOMAIN_EQ_IDS


# ---------------------------------------------------------------------------
# Registry — agrégation multi-domaine (AC 1, 2, 3)
# ---------------------------------------------------------------------------


def test_registry_map_all_returns_switch_plus_12_sensors_plus_1_binary():
    eq = _eq554()
    results = MapperRegistry().map_all(eq, _snapshot(eq))

    assert len(results) == 14
    types = [r.ha_entity_type for r in results]
    assert types.count("switch") == 1
    assert types.count("sensor") == 12
    assert types.count("binary_sensor") == 1
    # Tout est rattaché au même device/eqLogic.
    assert all(r.jeedom_eq_id == 554 for r in results)


def test_registry_switch_is_primary_and_preserved():
    eq = _eq554()
    primary = MapperRegistry().map(eq, _snapshot(eq))

    assert primary is not None
    # Le switch reste primaire avec son identité eqLogic historique (AC 4).
    assert primary.ha_entity_type == "switch"
    assert primary.ha_unique_id == "jeedom2ha_eq_554"
    assert primary.confidence == "sure"
    assert isinstance(primary.capabilities, SwitchCapabilities)
    # Les 13 entités secondaires (12 sensor + 1 binary) sont rattachées.
    assert len(primary.additional_mappings) == 13
    secondary_types = sorted({m.ha_entity_type for m in primary.additional_mappings})
    assert secondary_types == ["binary_sensor", "sensor"]


# ---------------------------------------------------------------------------
# SensorMapper — 12 sensors par commande (AC 2)
# ---------------------------------------------------------------------------


def test_sensor_mapper_emits_twelve_per_command_sensors():
    eq = _eq554()
    mappings = SensorMapper().map_all(eq, _snapshot(eq))

    assert len(mappings) == 12
    assert all(m.ha_entity_type == "sensor" for m in mappings)
    cmd_ids = {(m.reason_details or {}).get("cmd_id") for m in mappings}
    assert cmd_ids == _EXPECTED_SENSOR_CMD_IDS


def test_sensor_identifiers_derived_from_command_ids():
    eq = _eq554()
    for m in SensorMapper().map_all(eq, _snapshot(eq)):
        cmd_id = (m.reason_details or {})["cmd_id"]
        assert m.ha_unique_id == f"jeedom2ha_eq_554_cmd_{cmd_id}"
        assert (m.reason_details or {})["object_id"] == f"jeedom2ha_554_{cmd_id}"
        assert (m.reason_details or {})["node_id"] == f"jeedom2ha_554_{cmd_id}"
        assert (m.reason_details or {})["state_topic"] == f"jeedom2ha/554/{cmd_id}/state"


def test_sensor_unit_inference_is_honest():
    eq = _eq554()
    by_cmd = {(m.reason_details or {})["cmd_id"]: m for m in SensorMapper().map_all(eq, _snapshot(eq))}

    # W -> power, kWh -> energy
    assert by_cmd[5206].reason_details["device_class"] == "power"
    assert by_cmd[5206].reason_details["unit_of_measurement"] == "W"
    assert by_cmd[5535].reason_details["device_class"] == "energy"
    assert by_cmd[5535].reason_details["unit_of_measurement"] == "kWh"
    # % et H : aucune classe HA fiable -> device_class None (publication honnête)
    assert by_cmd[5205].reason_details["device_class"] is None
    assert by_cmd[5205].reason_details["unit_of_measurement"] == "%"
    assert by_cmd[5542].reason_details["device_class"] is None
    assert by_cmd[5542].reason_details["unit_of_measurement"] == "H"


# ---------------------------------------------------------------------------
# BinarySensorMapper — 1 binaire, ENERGY_STATE exclu (AC 2, 4)
# ---------------------------------------------------------------------------


def test_binary_sensor_mapper_emits_single_binary_excluding_energy_state():
    eq = _eq554()
    mappings = BinarySensorMapper().map_all(eq, _snapshot(eq))

    assert len(mappings) == 1
    only = mappings[0]
    assert only.ha_entity_type == "binary_sensor"
    assert (only.reason_details or {})["cmd_id"] == _EXPECTED_BINARY_CMD_ID
    # #5708 (ENERGY_STATE binaire) ne doit JAMAIS devenir un binary_sensor (doublon switch).
    assert all((m.reason_details or {})["cmd_id"] != 5708 for m in mappings)


def test_binary_sensor_identity_is_per_command():
    eq = _eq554()
    only = BinarySensorMapper().map_all(eq, _snapshot(eq))[0]
    cmd_id = _EXPECTED_BINARY_CMD_ID
    assert only.ha_unique_id == f"jeedom2ha_eq_554_cmd_{cmd_id}"
    assert (only.reason_details or {})["object_id"] == f"jeedom2ha_554_{cmd_id}"
    assert (only.reason_details or {})["node_id"] == f"jeedom2ha_554_{cmd_id}"
    assert (only.reason_details or {})["state_topic"] == f"jeedom2ha/554/{cmd_id}/state"
    # #5510 ne porte pas de generic_type -> pas de device_class inventé.
    assert (only.reason_details or {})["device_class"] is None


# ---------------------------------------------------------------------------
# Non-régression — aucun débordement de l'allowlist (AC 4)
# ---------------------------------------------------------------------------


def test_other_virtual_eq_is_not_multi_domain():
    """Un autre eqLogic virtual avec ENERGY_* reste un simple switch mono-entité."""
    eq = JeedomEqLogic(
        id=9001,
        name="Prise garage",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(id=90011, name="On", generic_type="ENERGY_ON", type="action", sub_type="other"),
            JeedomCmd(id=90012, name="Off", generic_type="ENERGY_OFF", type="action", sub_type="other"),
            JeedomCmd(id=90013, name="Etat", generic_type="ENERGY_STATE", type="info", sub_type="binary"),
            JeedomCmd(id=90014, name="Conso", generic_type=None, type="info", sub_type="numeric", unit="W"),
        ],
    )
    results = MapperRegistry().map_all(eq, _snapshot(eq))
    assert len(results) == 1
    assert results[0].ha_entity_type == "switch"


def test_non_554_sensor_mapper_stays_mono():
    eq = JeedomEqLogic(
        id=7000,
        name="Capteur temperature salon",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(id=70001, name="Temp", generic_type="TEMPERATURE", type="info", sub_type="numeric"),
        ],
    )
    mappings = SensorMapper().map_all(eq, _snapshot(eq))
    assert len(mappings) == 1
    assert mappings[0].ha_unique_id == "jeedom2ha_eq_7000"


def test_non_554_binary_mapper_stays_mono():
    eq = JeedomEqLogic(
        id=7100,
        name="Detecteur fumee",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(id=71001, name="Smoke", generic_type="SMOKE", type="info", sub_type="binary"),
        ],
    )
    mappings = BinarySensorMapper().map_all(eq, _snapshot(eq))
    assert len(mappings) == 1
    assert mappings[0].ha_unique_id == "jeedom2ha_eq_7100"
    # Identité historique au niveau eqLogic (pas de cmd_id).
    assert "cmd_id" not in (mappings[0].reason_details or {})


# ---------------------------------------------------------------------------
# Task 3 — publication discovery binary_sensor par commande (AC 3, 5)
# ---------------------------------------------------------------------------


async def test_publish_binary_sensor_multi_uses_per_command_topic():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)

    eq = _eq554()
    snapshot = _snapshot(eq)
    binary = BinarySensorMapper().map_all(eq, snapshot)[0]

    published = await publisher.publish_binary_sensor(binary, snapshot)
    assert published is True

    topic, payload_json = mqtt_bridge.publish_message.call_args.args[:2]
    payload = json.loads(payload_json)

    assert topic == "homeassistant/binary_sensor/jeedom2ha_554_5510/config"
    assert payload["unique_id"] == "jeedom2ha_eq_554_cmd_5510"
    assert payload["object_id"] == "jeedom2ha_554_5510"
    assert payload["state_topic"] == "jeedom2ha/554/5510/state"
    # Device commun rattaché à l'eqLogic Jeedom.
    assert payload["device"]["identifiers"] == ["jeedom2ha_554"]


async def test_publish_binary_sensor_mono_backward_compatible_topic():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)

    eq = JeedomEqLogic(
        id=7100,
        name="Detecteur fumee",
        object_id=1,
        eq_type_name="virtual",
        cmds=[JeedomCmd(id=71001, name="Smoke", generic_type="SMOKE", type="info", sub_type="binary")],
    )
    snapshot = _snapshot(eq)
    mapping = BinarySensorMapper().map(eq, snapshot)

    await publisher.publish_binary_sensor(mapping, snapshot)
    topic, payload_json = mqtt_bridge.publish_message.call_args.args[:2]
    payload = json.loads(payload_json)

    assert topic == "homeassistant/binary_sensor/jeedom2ha_7100/config"
    assert payload["unique_id"] == "jeedom2ha_eq_7100"
    assert payload["object_id"] == "jeedom2ha_7100"
    assert payload["state_topic"] == "jeedom2ha/7100/state"


# ---------------------------------------------------------------------------
# Task 4 — orchestration /action/sync : compteurs multi-domaine (AC 4, 6)
# ---------------------------------------------------------------------------


def _eq554_cmd_payload():
    return [
        {
            "id": cmd_id,
            "name": name,
            "generic_type": generic_type,
            "type": cmd_type,
            "sub_type": sub_type,
            "unit": unit,
        }
        for cmd_id, name, cmd_type, sub_type, generic_type, unit in _EQ554_CMDS
    ]


def _sync_body():
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Local technique"}],
            "eq_logics": [
                {
                    "id": 554,
                    "name": "Chauffe-eau",
                    "object_id": 1,
                    "is_enable": True,
                    "is_visible": True,
                    "eq_type": "virtual",
                    "is_excluded": False,
                    "status": {"timeout": 0},
                    "cmds": _eq554_cmd_payload(),
                }
            ],
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "story-11-2-test",
        "timestamp": "2026-06-19T00:00:00Z",
    }


async def test_sync_publishes_switch_sensors_and_binary_for_eq554(aiohttp_client):
    app = create_app(local_secret=_SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge
    client = await aiohttp_client(app)

    with patch("transport.http_server.save_publications_cache"):
        resp = await client.post(
            "/action/sync", json=_sync_body(), headers={"X-Local-Secret": _SECRET}
        )
    assert resp.status == 200
    body = await resp.json()

    summary = body["payload"]["mapping_summary"]
    assert summary["sensors_published"] == 12
    assert summary["binary_sensors_published"] == 1
    assert summary["switches_published"] == 1

    sensor_topics = {
        call.args[0]
        for call in bridge.publish_message.call_args_list
        if call.args[0].startswith("homeassistant/sensor/jeedom2ha_554_")
    }
    binary_topics = {
        call.args[0]
        for call in bridge.publish_message.call_args_list
        if call.args[0].startswith("homeassistant/binary_sensor/jeedom2ha_554_")
    }
    assert len(sensor_topics) == 12
    assert binary_topics == {"homeassistant/binary_sensor/jeedom2ha_554_5510/config"}


# ---------------------------------------------------------------------------
# Task 4 — dépublication exhaustive ET domain-aware (anti-fantômes) (AC 4, 6)
# ---------------------------------------------------------------------------


def test_collect_unpublish_entries_are_domain_aware_for_eq554():
    eq = _eq554()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    entries = _collect_unpublish_node_ids(primary)

    # Hétérogène (switch + sensor + binary_sensor) -> chaque entrée porte son type.
    assert all(isinstance(e, tuple) and len(e) == 2 for e in entries)
    assert ("switch", "jeedom2ha_554") in entries
    assert ("binary_sensor", "jeedom2ha_554_5510") in entries
    for cmd_id in _EXPECTED_SENSOR_CMD_IDS:
        assert ("sensor", f"jeedom2ha_554_{cmd_id}") in entries
    # 1 switch + 12 sensors + 1 binary = 14 cibles, aucune perdue.
    assert len(entries) == 14


async def test_unpublish_by_eq_id_removes_every_domain_topic_for_eq554():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)

    eq = _eq554()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    entries = _collect_unpublish_node_ids(primary)

    ok = await publisher.unpublish_by_eq_id(554, entity_type=primary.ha_entity_type, node_ids=entries)
    assert ok is True

    # Tous les topics effacés, chacun avec son bon domaine (anti-fantôme cross-domaine).
    erased = {call.args[0] for call in mqtt_bridge.publish_message.call_args_list}
    assert "homeassistant/switch/jeedom2ha_554/config" in erased
    assert "homeassistant/binary_sensor/jeedom2ha_554_5510/config" in erased
    for cmd_id in _EXPECTED_SENSOR_CMD_IDS:
        assert f"homeassistant/sensor/jeedom2ha_554_{cmd_id}/config" in erased
    # Aucun topic mal typé (ex. switch/jeedom2ha_554_5510).
    assert all(call.args[1] == "" for call in mqtt_bridge.publish_message.call_args_list)
    assert len(erased) == 14


def test_collect_unpublish_node_ids_msunpv_stays_string_contract():
    """Non-régression 11.1.bis : multi-sensor homogène -> liste de chaînes."""
    eq = JeedomEqLogic(
        id=553,
        name="MSunPV",
        object_id=1,
        eq_type_name="msunpv",
        cmds=[
            JeedomCmd(id=5138, name="P", generic_type=None, type="info", sub_type="numeric", unit="W"),
            JeedomCmd(id=5137, name="R", generic_type=None, type="info", sub_type="numeric", unit="W"),
        ],
    )
    primary = MapperRegistry().map(eq, _snapshot(eq))
    entries = _collect_unpublish_node_ids(primary)
    assert entries == ["jeedom2ha_553_5138", "jeedom2ha_553_5137"]


def test_collect_unpublish_node_ids_mono_returns_empty():
    eq = JeedomEqLogic(
        id=7000,
        name="Capteur",
        object_id=1,
        eq_type_name="virtual",
        cmds=[JeedomCmd(id=70001, name="Temp", generic_type="TEMPERATURE", type="info", sub_type="numeric")],
    )
    primary = MapperRegistry().map(eq, _snapshot(eq))
    assert _collect_unpublish_node_ids(primary) == []


def test_disk_cache_round_trips_eq554_domain_aware_entries(tmp_path):
    """Anti-fantôme cross-reboot : les domaines de eq554 survivent au redémarrage."""
    eq = _eq554()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=primary, discovery_published=True
    )
    save_publications_cache({554: decision}, str(tmp_path))

    reloaded = load_publications_cache(str(tmp_path))
    entries = reloaded[554]["node_ids"]
    assert ("switch", "jeedom2ha_554") in entries
    assert ("binary_sensor", "jeedom2ha_554_5510") in entries
    for cmd_id in _EXPECTED_SENSOR_CMD_IDS:
        assert ("sensor", f"jeedom2ha_554_{cmd_id}") in entries
    assert len(entries) == 14
