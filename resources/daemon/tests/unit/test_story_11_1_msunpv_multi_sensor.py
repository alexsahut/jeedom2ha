"""Story 11.1 - MSunPV / RouteurSolaire multi-sensor lecture seule.

L'eqLogic MSunPV eq553 doit produire plusieurs entités `sensor` HA rattachées
au même device Jeedom, avec identifiants/topics distincts par commande, sans
régression sur le comportement mono-sensor historique du SensorMapper.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from unittest.mock import patch

from discovery.publisher import DiscoveryPublisher
from mapping.registry import MapperRegistry
from mapping.sensor import SensorMapper
from models.mapping import SensorCapabilities
from models.topology import (
    JeedomCmd,
    JeedomEqLogic,
    JeedomObject,
    TopologySnapshot,
    assess_eligibility,
)
from transport.http_server import create_app

_SECRET = "test-secret-story-11-1"

# Inventaire MSunPV eq553 — backlog-icebox §3.1.
# Terrain réel (box 192.168.1.21) : AUCUNE commande ne porte de generic_type.
# Le device_class est inféré honnêtement depuis l'unité Jeedom (W->power, Wh->energy).
# Garder ce jeu fidèle au terrain est volontaire : un fixture avec generic_type="POWER"
# masquait le gate d'éligibilité (assess_eligibility) qui rejetait eq553 en prod.
_MSUNPV_CMDS = [
    (5138, "Puissance panneaux", None, "W"),
    (5137, "Puissance reseau", None, "W"),
    (5139, "Routage cumulus", None, "%"),
    (5140, "Routage radiateur", None, "%"),
    (5177, "Etat sortie 1 (CE %)", None, "%"),
    (5171, "Production panneaux journaliere", None, "Wh"),
    (5170, "Production injectee journaliere", None, "Wh"),
    (5169, "Consommation reseau journaliere", None, "Wh"),
]


def _msunpv_eq(eq_id: int = 553) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name="MSunPV / RouteurSolaire",
        object_id=1,
        eq_type_name="msunpv",
        cmds=[
            JeedomCmd(
                id=cmd_id,
                name=name,
                generic_type=generic_type,
                type="info",
                sub_type="numeric",
                unit=unit,
            )
            for cmd_id, name, generic_type, unit in _MSUNPV_CMDS
        ],
    )


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-06-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={eq.id: eq},
    )


# ---------------------------------------------------------------------------
# Gate d'éligibilité — terrain réel (AC 4 / régression masquée par fixture)
# ---------------------------------------------------------------------------


def test_msunpv_eligible_without_any_generic_type():
    """eq553 réel ne porte aucun generic_type : il doit rester éligible.

    Régression terrain : assess_eligibility rejetait l'eqLogic (no_supported_generic_type)
    avant le multi-sensor mapper, donc 0 sensor publié sur la box. Les eqTypes
    multi-sensor (msunpv) sont éligibles dès qu'ils portent ≥1 commande info numérique.
    """
    eq = _msunpv_eq()
    assert all(cmd.generic_type is None for cmd in eq.cmds)

    result = assess_eligibility(eq)
    assert result.is_eligible is True
    assert result.reason_code == "eligible"


def test_non_msunpv_without_generic_type_stays_ineligible():
    """Garde-fou AC#4 : aucun autre eqType ne bénéficie du contournement."""
    eq = JeedomEqLogic(
        id=8000,
        name="Capteur exotique",
        object_id=1,
        eq_type_name="virtual",
        cmds=[JeedomCmd(id=80001, name="Mesure", generic_type=None, type="info", sub_type="numeric")],
    )
    result = assess_eligibility(eq)
    assert result.is_eligible is False
    assert result.reason_code == "no_supported_generic_type"


# ---------------------------------------------------------------------------
# Task 1 — caractérisation multi-sensor (AC 1, 2, 3)
# ---------------------------------------------------------------------------


def test_msunpv_maps_to_eight_distinct_sensors():
    eq = _msunpv_eq()
    mappings = SensorMapper().map_all(eq, _snapshot(eq))

    assert len(mappings) == 8
    assert all(m.ha_entity_type == "sensor" for m in mappings)
    assert all(m.jeedom_eq_id == 553 for m in mappings)
    assert all(isinstance(m.capabilities, SensorCapabilities) for m in mappings)
    assert all(m.capabilities.has_state is True for m in mappings)


def test_msunpv_entities_have_distinct_identifiers_per_command():
    eq = _msunpv_eq()
    mappings = SensorMapper().map_all(eq, _snapshot(eq))

    unique_ids = {m.ha_unique_id for m in mappings}
    object_ids = {(m.reason_details or {}).get("object_id") for m in mappings}
    state_topics = {(m.reason_details or {}).get("state_topic") for m in mappings}

    assert len(unique_ids) == 8
    assert len(object_ids) == 8
    assert len(state_topics) == 8
    # Identité dérivée des IDs cmd Jeedom (stables), jamais des noms.
    for m in mappings:
        cmd_id = (m.reason_details or {}).get("cmd_id")
        assert cmd_id is not None
        assert m.ha_unique_id == f"jeedom2ha_eq_553_cmd_{cmd_id}"
        assert (m.reason_details or {})["object_id"] == f"jeedom2ha_553_{cmd_id}"
        assert (m.reason_details or {})["state_topic"] == f"jeedom2ha/553/{cmd_id}/state"


def test_msunpv_unit_inference_for_commands_without_generic_type():
    eq = _msunpv_eq()
    mappings = {(_m.reason_details or {})["cmd_id"]: _m for _m in SensorMapper().map_all(eq, _snapshot(eq))}

    # W -> power, Wh -> energy, % -> pas de device_class (honnête, pas de classe HA fiable)
    assert mappings[5138].reason_details["device_class"] == "power"
    assert mappings[5138].reason_details["unit_of_measurement"] == "W"
    assert mappings[5171].reason_details["device_class"] == "energy"
    assert mappings[5171].reason_details["unit_of_measurement"] == "Wh"
    assert mappings[5139].reason_details["device_class"] is None
    assert mappings[5139].reason_details["unit_of_measurement"] == "%"


def test_msunpv_only_info_numeric_no_action_command_created():
    eq = _msunpv_eq()
    eq.cmds.append(
        JeedomCmd(id=5999, name="Action parasite", generic_type=None, type="action", sub_type="other")
    )
    mappings = SensorMapper().map_all(eq, _snapshot(eq))

    assert len(mappings) == 8  # la commande action est ignorée
    assert all(m.ha_entity_type == "sensor" for m in mappings)


# ---------------------------------------------------------------------------
# Task 1 — non-régression mono-sensor (AC 4)
# ---------------------------------------------------------------------------


def _mono_eq() -> JeedomEqLogic:
    return JeedomEqLogic(
        id=7000,
        name="Capteur temperature salon",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(id=70001, name="Temp", generic_type="TEMPERATURE", type="info", sub_type="numeric"),
            JeedomCmd(id=70002, name="Hum", generic_type="HUMIDITY", type="info", sub_type="numeric"),
        ],
    )


def test_non_msunpv_eq_keeps_single_historical_sensor():
    eq = _mono_eq()
    mappings = SensorMapper().map_all(eq, _snapshot(eq))

    assert len(mappings) == 1
    only = mappings[0]
    # Comportement historique strict : identifiants au niveau eqLogic, pas de cmd_id.
    assert only.ha_unique_id == "jeedom2ha_eq_7000"
    assert only.reason_details == {"device_class": "temperature", "unit_of_measurement": "°C"}


def test_map_returns_primary_mapping_for_backward_compat():
    eq = _msunpv_eq()
    primary = SensorMapper().map(eq, _snapshot(eq))
    assert primary is not None
    assert primary.ha_entity_type == "sensor"
    assert primary.jeedom_eq_id == 553


# ---------------------------------------------------------------------------
# Task 2 — registry additif (AC 3, 4)
# ---------------------------------------------------------------------------


def test_registry_map_all_returns_eight_for_msunpv():
    eq = _msunpv_eq()
    mappings = MapperRegistry().map_all(eq, _snapshot(eq))
    assert len(mappings) == 8
    assert all(m.ha_entity_type == "sensor" for m in mappings)


def test_registry_map_still_returns_single_primary():
    eq = _msunpv_eq()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    assert primary is not None
    assert primary.jeedom_eq_id == 553


def test_registry_map_all_single_for_mono_sensor():
    eq = _mono_eq()
    assert len(MapperRegistry().map_all(eq, _snapshot(eq))) == 1


# ---------------------------------------------------------------------------
# Task 3 — publication discovery par commande (AC 3, 5)
# ---------------------------------------------------------------------------


async def test_publish_sensor_uses_per_command_topic_and_payload():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)

    eq = _msunpv_eq()
    snapshot = _snapshot(eq)
    mappings = {(_m.reason_details or {})["cmd_id"]: _m for _m in SensorMapper().map_all(eq, snapshot)}

    published = await publisher.publish_sensor(mappings[5139], snapshot)
    assert published is True

    topic, payload_json = mqtt_bridge.publish_message.call_args.args[:2]
    payload = json.loads(payload_json)

    assert topic == "homeassistant/sensor/jeedom2ha_553_5139/config"
    assert payload["unique_id"] == "jeedom2ha_eq_553_cmd_5139"
    assert payload["object_id"] == "jeedom2ha_553_5139"
    assert payload["state_topic"] == "jeedom2ha/553/5139/state"
    assert payload["unit_of_measurement"] == "%"
    assert "device_class" not in payload  # % -> pas de classe HA
    # Device commun rattaché à l'eqLogic Jeedom.
    assert payload["device"]["identifiers"] == ["jeedom2ha_553"]


async def test_publish_sensor_mono_backward_compatible_topic():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)

    eq = _mono_eq()
    snapshot = _snapshot(eq)
    mapping = SensorMapper().map(eq, snapshot)

    await publisher.publish_sensor(mapping, snapshot)
    topic, payload_json = mqtt_bridge.publish_message.call_args.args[:2]
    payload = json.loads(payload_json)

    assert topic == "homeassistant/sensor/jeedom2ha_7000/config"
    assert payload["unique_id"] == "jeedom2ha_eq_7000"
    assert payload["object_id"] == "jeedom2ha_7000"
    assert payload["state_topic"] == "jeedom2ha/7000/state"


# ---------------------------------------------------------------------------
# Task 4 — orchestration /action/sync : compteurs + honnêteté diagnostique (AC 4, 6)
# ---------------------------------------------------------------------------


def _msunpv_cmd_payload():
    return [
        {
            "id": cmd_id,
            "name": name,
            "generic_type": generic_type,
            "type": "info",
            "sub_type": "numeric",
            "unit": unit,
        }
        for cmd_id, name, generic_type, unit in _MSUNPV_CMDS
    ]


def _sync_body():
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Local technique"}],
            "eq_logics": [
                {
                    "id": 553,
                    "name": "MSunPV / RouteurSolaire",
                    "object_id": 1,
                    "is_enable": True,
                    "is_visible": True,
                    "eq_type": "msunpv",
                    "is_excluded": False,
                    "status": {"timeout": 0},
                    "cmds": _msunpv_cmd_payload(),
                }
            ],
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "story-11-1-test",
        "timestamp": "2026-06-17T00:00:00Z",
    }


async def test_sync_publishes_eight_sensors_and_counts_them(aiohttp_client):
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

    # Les 8 sensors MSunPV doivent être publiés et comptés.
    assert body["payload"]["mapping_summary"]["sensors_published"] == 8

    # 8 topics discovery distincts pour eq553.
    sensor_topics = {
        call.args[0]
        for call in bridge.publish_message.call_args_list
        if call.args[0].startswith("homeassistant/sensor/jeedom2ha_553_")
    }
    assert len(sensor_topics) == 8


async def test_sync_partial_failure_is_reported_honestly(aiohttp_client):
    app = create_app(local_secret=_SECRET)
    bridge = MagicMock()
    bridge.is_connected = True

    def _publish(topic, *_args, **_kwargs):
        # Une seule entité secondaire échoue à publier.
        return not topic.endswith("jeedom2ha_553_5140/config")

    bridge.publish_message = MagicMock(side_effect=_publish)
    app["mqtt_bridge"] = bridge
    client = await aiohttp_client(app)

    with patch("transport.http_server.save_publications_cache"):
        resp = await client.post(
            "/action/sync", json=_sync_body(), headers={"X-Local-Secret": _SECRET}
        )
    assert resp.status == 200

    primary = app["mappings"][553]
    # Le mapping primaire ne doit pas afficher un faux succès si un secondaire échoue.
    assert primary.publication_result.status == "failed"
    assert primary.publication_result.technical_reason_code == "multi_sensor_partial_publish_failed"
    # 7 publiés, le 8e en échec → compteur honnête.
    assert app["mappings"][553] is primary
