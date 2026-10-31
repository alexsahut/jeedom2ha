"""Story 25.2 — corpus fictif partagé (Task 1.1) : couvre les règles R1-R8 de 25.1 et la
partition D3. Aucun nom réel d'équipement, de pièce ou de personne (CC-48).

Le corpus est construit en mémoire (topologie + décisions « synchronisées » calculées avec le
vrai `evaluate_equipment`), puis les overrides sont posés sur disque (`data_dir`)."""

from __future__ import annotations

from mapping.overrides import save_equipment_override, save_override
from mapping.registry import MapperRegistry
from models.evaluate_equipment import evaluate_equipment
from models.topology import (
    JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot, assess_eligibility,
)


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(id=cmd_id, name=name, type=cmd_type, sub_type=sub_type,
                     generic_type=generic_type, unit=unit, current_value=value)


def light(eq_id, object_id=1, **kw):
    base = eq_id * 10
    return JeedomEqLogic(id=eq_id, name=f"Eq-{eq_id}", object_id=object_id, cmds=[
        _cmd(base + 1, "Etat", "info", "binary", "LIGHT_STATE", value="1"),
        _cmd(base + 2, "Slider", "action", "slider", "LIGHT_SLIDER"),
    ], **kw)


def multi_sensor(eq_id, object_id=1, **kw):
    base = eq_id * 10
    return JeedomEqLogic(id=eq_id, name=f"Eq-{eq_id}", object_id=object_id, eq_type_name="zwave", cmds=[
        _cmd(base + 1, "On", "action", "other", "LIGHT_ON"),
        _cmd(base + 2, "Off", "action", "other", "LIGHT_OFF"),
        _cmd(base + 3, "Etat", "info", "binary", "LIGHT_STATE", value="1"),
        _cmd(base + 4, "Niveau", "action", "slider", "LIGHT_SLIDER"),
        _cmd(base + 5, "Puissance", "info", "numeric", "POWER", unit="W", value=12),
        _cmd(base + 6, "Conso", "info", "numeric", "CONSUMPTION", unit="kWh", value=3.5),
    ], **kw)


def untyped(eq_id, object_id=2, **kw):
    base = eq_id * 10
    return JeedomEqLogic(id=eq_id, name=f"Eq-{eq_id}", object_id=object_id, cmds=[
        _cmd(base + 1, "Inconnue", "info", "string", None, value="x"),
        _cmd(base + 2, "Autre", "action", "other", None),
    ], **kw)


def build_corpus_topology() -> TopologySnapshot:
    eqs = [
        light(101, 1),                                  # publié (synchronisé), override_pending plus bas
        multi_sensor(102, 1),                           # principal + 2 secondaires
        JeedomEqLogic(id=103, name="Eq-103", object_id=1, cmds=[]),  # sans commande
        light(104, 2, is_enable=False),                 # désactivé (Jeedom)
        light(105, 2),                                  # exclu par override équipement (pending)
        untyped(106, 2),                                # types génériques absents (D3 « Ignorée »)
        light(107, 3),                                  # jamais synchronisé
        light(108, None),                               # pseudo-pièce (object_id absent)
        light(109, 3),                                  # override de type par commande (pending)
        light(110, 3, is_excluded=True, exclusion_source="eqlogic"),  # exclu à la source
    ]
    return TopologySnapshot(
        timestamp="2026-10-18T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Piece-1"), 2: JeedomObject(id=2, name="Piece-2"),
                 3: JeedomObject(id=3, name="Piece-3")},
        eq_logics={eq.id: eq for eq in eqs},
    )


NEVER_SYNCED = {107}
PUBLISHED_IN_HA = {101, 102, 105, 109}


def populate_app(app, data_dir) -> TopologySnapshot:
    """Peuple `app` comme après une synchro (topology / eligibility / publications), puis pose
    les overrides sur disque : 105 (exclusion équipement) et 109 (type par commande) deviennent
    `override_pending`."""
    topology = build_corpus_topology()
    registry = MapperRegistry()
    eligibility = {eq_id: assess_eligibility(eq) for eq_id, eq in topology.eq_logics.items()}
    publications = {}
    for eq_id, eq in topology.eq_logics.items():
        if eq_id in NEVER_SYNCED:
            continue
        evaluation = evaluate_equipment(
            eq, topology, eligibility[eq_id], mapper_registry=registry,
            confidence_policy="strict", persisted_overrides={}, persisted_equipment_overrides={},
        )
        decision = evaluation.equipment_decision
        decision.mapping_result = evaluation.mapping
        decision.discovery_published = eq_id in PUBLISHED_IN_HA
        decision.active_or_alive = eq_id in PUBLISHED_IN_HA
        publications[eq_id] = decision
    app["topology"] = topology
    app["eligibility"] = eligibility
    app["publications"] = publications
    app["data_dir"] = str(data_dir)
    save_equipment_override(105, {"publication_override": "exclude"}, str(data_dir))
    save_override(109, 1091, {"ha_entity_type": "binary_sensor"}, str(data_dir))
    return topology
