"""Story 21.1 (AC10, Q3 C) — test de caractérisation PERMANENT du chemin « type puis forçage ».

Aucun changement de mapper dans la story 21.1 : un équipement à UNE seule entité dont l'unique
commande est un état sans ordre On/Off (`ENERGY_STATE` seul) reste « ambigu »
(`switch_state_orphan`) et n'est pas publié automatiquement. L'utilisateur peut toutefois, au
cas par cas, choisir le type `binary_sensor` pour la commande PUIS « Forcer » : ce test fige les
trois étapes (équipement synthétique, identifiants numériques seulement).
"""

import asyncio
import json
from unittest.mock import MagicMock

from discovery.publisher import DiscoveryPublisher
from mapping.registry import MapperRegistry
from models.evaluate_equipment import evaluate_equipment
from models.topology import (
    JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot, assess_eligibility,
)

EQ_ID = 901
CMD_ID = 9101
KEY = f"{EQ_ID}:{CMD_ID}"


def _eq_and_snapshot():
    eq = JeedomEqLogic(
        id=EQ_ID, name="eq", object_id=1, eq_type_name="type",
        cmds=[JeedomCmd(
            id=CMD_ID, name="Etat", type="info", sub_type="binary",
            generic_type="ENERGY_STATE", unit=None, current_value="1",
        )],
    )
    snapshot = TopologySnapshot(
        timestamp="2026-10-11T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Zone")},
        eq_logics={EQ_ID: eq},
    )
    return eq, snapshot


def _evaluate(overrides=None):
    eq, snapshot = _eq_and_snapshot()
    evaluation = evaluate_equipment(
        eq, snapshot, assess_eligibility(eq),
        mapper_registry=MapperRegistry(), persisted_overrides=overrides or {},
    )
    return evaluation, snapshot


def test_automatic_state_only_is_ambiguous_and_not_published():
    evaluation, _ = _evaluate()
    assert evaluation.mapping.ha_entity_type == "switch"
    assert evaluation.mapping.reason_code == "switch_state_orphan"
    assert evaluation.equipment_decision.should_publish is False
    assert evaluation.equipment_decision.reason == "ambiguous_skipped"
    assert evaluation.secondary_decisions == []


def test_force_alone_is_refused():
    evaluation, _ = _evaluate({KEY: {"ha_entity_type": "switch", "publication_override": "force_publish"}})
    assert evaluation.equipment_decision.should_publish is False
    assert evaluation.equipment_decision.reason == "ha_missing_command_topic"


def test_type_alone_is_refused():
    evaluation, _ = _evaluate({KEY: {"ha_entity_type": "binary_sensor"}})
    assert evaluation.mapping.ha_entity_type == "binary_sensor"
    assert evaluation.equipment_decision.should_publish is False
    assert evaluation.equipment_decision.reason == "ambiguous_skipped"


def test_type_then_force_is_published_with_complete_binary_sensor_payload():
    evaluation, snapshot = _evaluate(
        {KEY: {"ha_entity_type": "binary_sensor", "publication_override": "force_publish"}}
    )
    assert evaluation.equipment_decision.should_publish is True
    assert evaluation.equipment_decision.reason == "publication_forced"
    assert evaluation.mapping.ha_entity_type == "binary_sensor"

    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(mqtt_bridge=bridge)
    assert asyncio.run(publisher.publish_binary_sensor(evaluation.mapping, snapshot)) is True

    topic, raw_payload = bridge.publish_message.call_args[0][:2]
    assert topic == f"homeassistant/binary_sensor/jeedom2ha_{EQ_ID}/config"
    payload = json.loads(raw_payload)
    assert payload["unique_id"] == f"jeedom2ha_eq_{EQ_ID}"
    assert payload["object_id"] == f"jeedom2ha_{EQ_ID}"
    assert payload["state_topic"] == f"jeedom2ha/{EQ_ID}/state"
    assert payload["platform"] == "mqtt"
    assert payload["device"]
    assert payload["origin"]["name"] == "jeedom2ha"
    assert payload.get("availability") or payload.get("availability_topic")
    assert "command_topic" not in payload
