"""Story 22.2 — présence par entité / par commande (Q1 A, champs additifs de l'arbre) et
Task 0 a (CC-60) : cause du refus `ha_missing_state_topic` de la forme « 380 ».

Identifiants synthétiques seulement (CC-48) : aucun nom réel d'équipement, de pièce ou de scénario.
"""

import asyncio
import json
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from mapping.registry import MapperRegistry
from models.evaluate_equipment import evaluate_equipment
from models.mapping import CoverCapabilities, PublicationDecision
from models.topology import (
    JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot, assess_eligibility,
)
from transport.http_server import create_app

SECRET = "test_secret_22_2"
HEADERS = {"X-Local-Secret": SECRET}
STATE_CMD = 9001


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(
        id=cmd_id, name=name, type=cmd_type, sub_type=sub_type,
        generic_type=generic_type, unit=unit, current_value=value,
    )


def _snapshot(eq):
    return TopologySnapshot(
        timestamp="2026-10-12T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Zone")},
        eq_logics={eq.id: eq},
    )


def _multi_entity_eq(eq_id=900):
    """Forme « 579 » : état seul (principal `switch` refusé) + secondaire `binary_sensor`
    portant la même commande d'état + un capteur de puissance."""
    return JeedomEqLogic(
        id=eq_id, name="eq", object_id=1, eq_type_name="type",
        cmds=[
            _cmd(STATE_CMD, "Etat", "info", "binary", "ENERGY_STATE", value="1"),
            _cmd(9002, "Puissance", "info", "numeric", "POWER", "W", 5),
            _cmd(9003, "Autre", "info", "numeric", None, "W", 5),
            _cmd(9004, "Libre", "info", "string", None),
        ],
    )


def _evaluate(eq, overrides=None):
    snapshot = _snapshot(eq)
    return evaluate_equipment(
        eq, snapshot, assess_eligibility(eq), mapper_registry=MapperRegistry(),
        persisted_overrides=overrides or {},
    ), snapshot


@pytest.fixture
def app(tmp_path):
    application = create_app(local_secret=SECRET)
    application["data_dir"] = str(tmp_path)
    return application


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _tree(cli, app, eq, synced_decision=None, pending=None):
    app["topology"] = _snapshot(eq)
    app["publications"] = {eq.id: synced_decision} if synced_decision is not None else {}
    app["pending_discovery_unpublish"] = pending or {}
    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=HEADERS)
    assert resp.status == 200
    return (await resp.json())["payload"]


def _synced(eq, published_secondary_types=(), primary_published=False):
    """Décision synchronisée : principal avec l'état d'exécution demandé, secondaires marqués
    `discovery_published` selon leur type HA."""
    evaluation, _ = _evaluate(eq)
    primary = evaluation.mapping
    secondaries = []
    for secondary in primary.additional_mappings:
        ref = secondary.publication_decision_ref
        published = secondary.ha_entity_type in published_secondary_types
        secondaries.append(replace(
            secondary, publication_decision_ref=replace(ref, discovery_published=published),
        ))
    primary = replace(primary, additional_mappings=secondaries)
    return replace(
        evaluation.equipment_decision, mapping_result=primary,
        discovery_published=primary_published, active_or_alive=primary_published,
    )


def _entity(payload, ha_type):
    return next(e for e in payload["entities"] if e["ha_entity_type"] == ha_type)


def _row(payload, cmd_id):
    return next(c for c in payload["commands"] if c["jeedom_cmd_id"] == cmd_id)


# ---------------------------------------------------------------------------
# Q1 A — présence par entité (`entities[].present_in_ha`) et par commande
# (`commands[].published_in_ha`)
# ---------------------------------------------------------------------------

async def test_forme_579_principal_refuse_secondaire_publie(cli, app):
    eq = _multi_entity_eq()
    payload = await _tree(cli, app, eq, _synced(eq, published_secondary_types=("binary_sensor",)))
    assert _entity(payload, "switch")["present_in_ha"] is False
    assert _entity(payload, "binary_sensor")["present_in_ha"] is True
    assert _entity(payload, "sensor")["present_in_ha"] is False
    # La commande d'état est portée par le principal (refusé) ET par le secondaire (publié).
    carriers = [e for e in payload["entities"] if STATE_CMD in e["command_ids"]]
    assert len(carriers) == 2
    assert _row(payload, STATE_CMD)["published_in_ha"] is True
    assert _row(payload, 9002)["published_in_ha"] is False
    assert _row(payload, 9004)["published_in_ha"] is False
    assert payload["sync_status"]["published_in_ha"] is True


async def test_invariant_equipement_publie_ssi_une_entite_presente(cli, app):
    eq = _multi_entity_eq()
    for secondary_types, primary_published in [
        ((), False), (("sensor",), False), (("binary_sensor", "sensor"), False), ((), True),
    ]:
        payload = await _tree(cli, app, eq, _synced(eq, secondary_types, primary_published))
        any_entity = any(e["present_in_ha"] for e in payload["entities"])
        assert payload["sync_status"]["published_in_ha"] is any_entity, (secondary_types, primary_published)


async def test_jamais_synchronise_rien_de_present(cli, app):
    eq = _multi_entity_eq()
    payload = await _tree(cli, app, eq, None)
    assert all(e["present_in_ha"] is False for e in payload["entities"])
    assert all(c["published_in_ha"] is False for c in payload["commands"])
    assert payload["sync_status"]["published_in_ha"] is False


async def test_depublication_differee_les_entites_publiees_restent_presentes(cli, app):
    eq = _multi_entity_eq()
    synced = _synced(eq, published_secondary_types=())
    payload = await _tree(cli, app, eq, synced, pending={eq.id: "binary_sensor"})
    assert payload["sync_status"]["published_in_ha"] is True
    # Les entités dont le verdict synchronisé autorisait la publication sont encore dans HA.
    assert _entity(payload, "binary_sensor")["present_in_ha"] is True
    assert _entity(payload, "switch")["present_in_ha"] is False
    assert _row(payload, STATE_CMD)["published_in_ha"] is True


async def test_aucun_changement_de_decision_ni_de_topic(cli, app):
    """AC10 : champs additifs seulement — la décision de l'arbre est celle d'`evaluate_equipment`."""
    eq = _multi_entity_eq()
    evaluation, _ = _evaluate(eq)
    payload = await _tree(cli, app, eq, _synced(eq, published_secondary_types=("binary_sensor",)))
    assert payload["equipment_decision"]["should_publish"] is evaluation.equipment_decision.should_publish
    assert payload["equipment_decision"]["publication_reason"] == evaluation.equipment_decision.reason
    assert [e["ha_entity_type"] for e in payload["entities"]] == [
        m.ha_entity_type for m in [evaluation.mapping, *evaluation.mapping.additional_mappings]
    ]


# ---------------------------------------------------------------------------
# Task 0 a (CC-60) — cause du refus `ha_missing_state_topic` sur la forme « 380 »
# ---------------------------------------------------------------------------

EQ_380 = 380
CMD_FLAP_STATE = 2971


def _eq_forme_380():
    """Cover dont la seule commande typée est `FLAP_STATE` (état sans ordre d'ouverture) ;
    trois autres commandes info sans type générique."""
    return JeedomEqLogic(
        id=EQ_380, name="eq", object_id=1, eq_type_name="type",
        cmds=[
            _cmd(2968, "a", "info", "numeric", None, value=1),
            _cmd(2969, "b", "info", "numeric", None, value=1),
            _cmd(2970, "c", "info", "string", None, value="x"),
            _cmd(CMD_FLAP_STATE, "d", "info", "binary", "FLAP_STATE", value="1"),
        ],
    )


def _override(ha_type, force=False):
    entry = {"ha_entity_type": ha_type}
    if force:
        entry["publication_override"] = "force_publish"
    return {f"{EQ_380}:{CMD_FLAP_STATE}": entry}


def test_cc60_automatique_cover_ambigu_orphelin():
    evaluation, _ = _evaluate(_eq_forme_380())
    assert evaluation.mapping.ha_entity_type == "cover"
    assert evaluation.mapping.reason_code == "state_orphan"
    assert evaluation.mapping.confidence == "ambiguous"
    assert evaluation.equipment_decision.should_publish is False
    assert evaluation.equipment_decision.reason == "ambiguous_skipped"
    assert isinstance(evaluation.mapping.capabilities, CoverCapabilities)


@pytest.mark.parametrize("ha_type", ["sensor", "binary_sensor"])
def test_cc60_cause_les_capacites_restent_celles_du_cover(ha_type):
    """CAUSE : l'override ne change que `ha_entity_type` ; `capabilities` reste un
    `CoverCapabilities` (sans `has_state`), donc la validation du type `sensor`/`binary_sensor`
    échoue sur `has_state` → `ha_missing_state_topic`, indépendamment de l'état de la commande."""
    evaluation, _ = _evaluate(_eq_forme_380(), _override(ha_type))
    mapping = evaluation.mapping
    assert mapping.ha_entity_type == ha_type
    assert isinstance(mapping.capabilities, CoverCapabilities)
    assert not hasattr(mapping.capabilities, "has_state")
    assert mapping.projection_validity.is_valid is False
    assert mapping.projection_validity.reason_code == "ha_missing_state_topic"
    assert mapping.projection_validity.missing_capabilities == ["has_state"]
    assert evaluation.equipment_decision.should_publish is False
    assert evaluation.equipment_decision.reason == "ambiguous_skipped"


@pytest.mark.parametrize("ha_type", ["sensor", "binary_sensor"])
def test_cc60_le_forcage_ne_leve_pas_la_validation(ha_type):
    """Aujourd'hui, le forçage ne contourne pas la validation de projection : le type reste refusé."""
    evaluation, _ = _evaluate(_eq_forme_380(), _override(ha_type, force=True))
    assert evaluation.equipment_decision.should_publish is False
    assert evaluation.equipment_decision.reason == "ha_missing_state_topic"


@pytest.mark.parametrize("ha_type", ["sensor", "binary_sensor"])
def test_cc60_constat_une_projection_corrigee_ferait_aboutir_type_puis_forcage(ha_type, monkeypatch):
    """CONSTAT (Task 0 a, réserve de Q7 A) : si la projection reprenait l'état de la commande
    `FLAP_STATE` (simulé ici par `has_state` sur les capacités du cover), « type + Forcer »
    ABOUTIRAIT et le payload de découverte aurait un `state_topic`. L'AC6 (liste filtrée) n'est
    donc PAS implémentée dans cette story : décision d'Alexandre attendue. Ce test ne change
    aucun code de production ; il documente le constat."""
    monkeypatch.setattr(CoverCapabilities, "has_state", True, raising=False)
    # Type seul : validation levée, mais l'ambiguïté (`state_orphan`) bloque encore.
    seul, _ = _evaluate(_eq_forme_380(), _override(ha_type))
    assert seul.mapping.projection_validity.is_valid is True
    assert seul.equipment_decision.should_publish is False
    assert seul.equipment_decision.reason == "ambiguous_skipped"
    # Type puis forçage : publié.
    force, snapshot = _evaluate(_eq_forme_380(), _override(ha_type, force=True))
    assert force.equipment_decision.should_publish is True
    assert force.equipment_decision.reason == "publication_forced"
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(mqtt_bridge=bridge)
    assert asyncio.run(getattr(publisher, f"publish_{ha_type}")(force.mapping, snapshot)) is True
    topic, raw_payload = bridge.publish_message.call_args[0][:2]
    assert topic == f"homeassistant/{ha_type}/jeedom2ha_{EQ_380}/config"
    assert json.loads(raw_payload)["state_topic"] == f"jeedom2ha/{EQ_380}/state"


def test_cc60_publication_decision_importable():
    # Garde-fou d'import : le test de présence ci-dessus s'appuie sur `PublicationDecision`.
    assert PublicationDecision is not None


async def test_depublication_differee_d_une_entite_absente_du_mapping_courant(cli, app):
    """Relecture Codex : une entité retirée du mapping mais encore dans HA (dépublication
    différée) garde ses commandes « publiées » ; l'équipement et ses commandes restent cohérents."""
    eq = _multi_entity_eq()
    synced = _synced(eq, published_secondary_types=("binary_sensor", "sensor"))
    # Le capteur de la commande 9003 disparaît du mapping courant (plus d'unité) : la commande reste lue.
    current = _multi_entity_eq()
    current.cmds[2] = _cmd(9003, "Autre", "info", "string", None)
    payload = await _tree(cli, app, current, synced, pending={eq.id: "sensor"})
    assert 9003 not in {cid for e in payload["entities"] for cid in e["command_ids"]}
    assert payload["sync_status"]["published_in_ha"] is True
    assert _row(payload, 9003)["published_in_ha"] is True


async def test_sans_depublication_differee_une_commande_retiree_n_est_pas_publiee(cli, app):
    eq = _multi_entity_eq()
    synced = _synced(eq, published_secondary_types=())
    current = _multi_entity_eq()
    current.cmds[2] = _cmd(9003, "Autre", "info", "string", None)
    payload = await _tree(cli, app, current, synced)
    assert _row(payload, 9003)["published_in_ha"] is False


# ---------------------------------------------------------------------------
# R2 (AC6, option A) — `commands[].override_types_allowed` : types « Override HA » qui peuvent aboutir
# ---------------------------------------------------------------------------

def _allowed(payload, cmd_id):
    return _row(payload, cmd_id).get("override_types_allowed")


async def _preview_validity(cli, eq_id, cmd_id, ha_type):
    resp = await cli.post(
        "/system/overrides/preview", headers=HEADERS,
        json={"payload": {"jeedom_eq_id": eq_id, "jeedom_cmd_id": cmd_id, "ha_entity_type": ha_type}},
    )
    assert resp.status == 200
    return (await resp.json())["payload"]["overridden"]["projection_validity"]["is_valid"]


async def test_r2_forme_380_sensor_et_binary_sensor_retires(cli, app):
    """Commande 2971 : `sensor` et `binary_sensor` (refusés par la validation, même forcés) ne sont plus
    proposés ; seul `cover` (son type automatique, valide) reste."""
    payload = await _tree(cli, app, _eq_forme_380())
    allowed = _allowed(payload, CMD_FLAP_STATE)
    assert allowed == ["cover"]
    assert "sensor" not in allowed and "binary_sensor" not in allowed
    # Commandes non couvertes : pas de liste (le sélecteur y est de toute façon grisé).
    for uncovered in (2968, 2969, 2970):
        assert "override_types_allowed" not in _row(payload, uncovered)


async def test_r2_le_filtre_est_celui_de_l_apercu(cli, app):
    """Critère : exactement la validité de projection que rend l'aperçu pour chaque type."""
    eq = _eq_forme_380()
    payload = await _tree(cli, app, eq)
    allowed = _allowed(payload, CMD_FLAP_STATE)
    for ha_type in ["alarm_control_panel", "binary_sensor", "button", "climate", "cover", "light", "sensor", "switch"]:
        valid = await _preview_validity(cli, EQ_380, CMD_FLAP_STATE, ha_type)
        assert (ha_type in allowed) is valid, ha_type


async def test_r2_commande_ordinaire_liste_inchangee(cli, app):
    """Un éclairage ordinaire (On/Off/État) : tous les types dont la validation passe restent proposés,
    dans l'ordre alphabétique de la liste de l'interface ; liste identique pour toutes ses commandes."""
    eq = JeedomEqLogic(
        id=910, name="eq", object_id=1, eq_type_name="light",
        cmds=[
            _cmd(9101, "On", "action", "other", "LIGHT_ON"),
            _cmd(9102, "Off", "action", "other", "LIGHT_OFF"),
            _cmd(9103, "Etat", "info", "binary", "LIGHT_STATE"),
        ],
    )
    payload = await _tree(cli, app, eq)
    lists = [_allowed(payload, cid) for cid in (9101, 9102, 9103)]
    assert lists[0] == lists[1] == lists[2]
    assert lists[0] == sorted(lists[0])
    assert "light" in lists[0]
    for ha_type in ["alarm_control_panel", "binary_sensor", "button", "climate", "cover", "light", "sensor", "switch"]:
        valid = await _preview_validity(cli, 910, 9101, ha_type)
        assert (ha_type in lists[0]) is valid, ha_type


async def test_r2_type_valide_mais_ambigu_reste_propose(cli, app):
    """Forme « état seul » (switch orphelin, ambigu) : `binary_sensor` est valide mais refusé seulement
    pour l'ambiguïté ; « Forcer » peut le faire aboutir, donc il reste proposé."""
    eq = JeedomEqLogic(
        id=901, name="eq", object_id=1, eq_type_name="type",
        cmds=[_cmd(9101, "Etat", "info", "binary", "ENERGY_STATE", value="1")],
    )
    payload = await _tree(cli, app, eq)
    allowed = _allowed(payload, 9101)
    assert "binary_sensor" in allowed
    resp = await cli.post(
        "/system/overrides/preview", headers=HEADERS,
        json={"payload": {"jeedom_eq_id": 901, "jeedom_cmd_id": 9101, "ha_entity_type": "binary_sensor"}},
    )
    over = (await resp.json())["payload"]["overridden"]
    assert over["projection_validity"]["is_valid"] is True
    assert over["publication_reason"] == "ambiguous_skipped"
    assert over["should_publish"] is False


async def test_r2_champ_additif_aucune_publication_ni_decision_modifiee(cli, app):
    """Lecture seule : l'arbre de la forme 380 garde sa décision et ne crée aucun override."""
    eq = _eq_forme_380()
    evaluation, _ = _evaluate(eq)
    payload = await _tree(cli, app, eq)
    assert payload["equipment_decision"]["publication_reason"] == evaluation.equipment_decision.reason
    assert payload["equipment_decision"]["should_publish"] is False
    assert all(c["override_applied"] is False for c in payload["commands"])
