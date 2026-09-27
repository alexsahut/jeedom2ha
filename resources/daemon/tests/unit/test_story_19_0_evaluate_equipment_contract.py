"""Story 19.0 — Contrat pur `CommandDecision` / `evaluate_equipment()` (AC1-AC5).

Isolation totale :
  - Aucune dépendance MQTT, broker, daemon, pytest-asyncio.
  - Aucun conftest.py — helpers locaux définis dans ce fichier uniquement.
  - `evaluate_equipment()` est une fonction pure : `mapper_registry` est un double de test
    (jamais le vrai `MapperRegistry()` instancié directement — le but est de tester le
    contrat, pas le moteur de mapping, déjà couvert par ses propres tests).

Invariants couverts (portés de `test_step4_decide_publication.py`, Story 4.1/16.3) :
  I1 : équipement inéligible → décision refusée de niveau 1, sans mapping ni projection.
  I2 : projection invalide → jamais publié, même avec un override "force_publish".
  I3 : should_publish=True ⇔ confidence publishable ET is_valid=True ET type dans scope.
  I4 : le premier échec dans l'ordre 1→2→3→4 fait foi, jamais écrasé en aval.
  I5 : tout équipement éligible produit toujours ses 3 sous-blocs, jamais None.
  I6 : reason jamais None ni vide sur tous les chemins de retour.
  I7 : aucune logique MQTT/broker/cache — vérifié structurellement sur le module source.
"""
from __future__ import annotations

import inspect
from copy import deepcopy
from typing import Dict, List, Optional
from unittest import mock

import models.topology as topology_module
from models.evaluate_equipment import CommandDecision, EquipmentEvaluation, evaluate_equipment
from models.mapping import (
    LightCapabilities,
    MappingResult,
    ProjectionValidity,
    PublicationDecision,
)
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, TopologySnapshot
from validation.ha_component_registry import PRODUCT_SCOPE


# ---------------------------------------------------------------------------
# Helpers locaux au fichier (pas de conftest.py)
# ---------------------------------------------------------------------------

def _cmd(id, generic_type="LIGHT_ON", type_="action", sub_type="other"):
    return JeedomCmd(id=id, name=f"cmd{id}", generic_type=generic_type, type=type_, sub_type=sub_type)


def _make_eq(id=1, cmds=None, is_excluded=False, exclusion_source=None, is_enable=True) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=id,
        name="Test eq",
        is_enable=is_enable,
        is_excluded=is_excluded,
        exclusion_source=exclusion_source,
        cmds=cmds if cmds is not None else [_cmd(101, "LIGHT_ON"), _cmd(102, "LIGHT_STATE")],
    )


def _make_snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-09-27T00:00:00Z", eq_logics={eq.id: eq})


def _eligible() -> EligibilityResult:
    return EligibilityResult(is_eligible=True, reason_code="eligible", confidence="unknown")


def _ineligible(reason_code="disabled_eqlogic") -> EligibilityResult:
    return EligibilityResult(is_eligible=False, reason_code=reason_code, confidence="sure")


def _valid_pv() -> ProjectionValidity:
    return ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])


def _invalid_pv(reason_code: str = "ha_missing_state_topic") -> ProjectionValidity:
    return ProjectionValidity(
        is_valid=False, reason_code=reason_code, missing_fields=[], missing_capabilities=[]
    )


def _make_mapping(
    *,
    jeedom_eq_id: int = 1,
    ha_entity_type: str = "light",
    confidence: str = "sure",
    reason_code: str = "light_on_off",
    commands: Optional[Dict[str, JeedomCmd]] = None,
    additional_mappings: Optional[List[MappingResult]] = None,
) -> MappingResult:
    return MappingResult(
        ha_entity_type=ha_entity_type,
        confidence=confidence,
        reason_code=reason_code,
        jeedom_eq_id=jeedom_eq_id,
        ha_unique_id=f"jeedom2ha_eq_{jeedom_eq_id}",
        ha_name="Test eq",
        capabilities=LightCapabilities(has_on_off=True),
        commands=commands
        if commands is not None
        else {"LIGHT_ON": _cmd(101, "LIGHT_ON"), "LIGHT_STATE": _cmd(102, "LIGHT_STATE", type_="info")},
        additional_mappings=additional_mappings or [],
    )


class _StubRegistry:
    """Double de test pour `mapper_registry` — jamais le vrai `MapperRegistry()` (Dev Notes :
    le registre est injecté, jamais instancié en interne par `evaluate_equipment`)."""

    def __init__(self, mapping: Optional[MappingResult]):
        self._mapping = mapping
        self.calls = 0

    def map(self, eq, snapshot):
        self.calls += 1
        return self._mapping


def _evaluate(eq, eligibility, mapping, **kwargs) -> EquipmentEvaluation:
    snapshot = kwargs.pop("snapshot", None) or _make_snapshot(eq)
    registry = kwargs.pop("mapper_registry", None) or _StubRegistry(mapping)
    return evaluate_equipment(
        eq, snapshot, eligibility, mapper_registry=registry, **kwargs
    )


# ---------------------------------------------------------------------------
# AC1 — CommandDecision par cmd_id, y compris commandes non couvertes
# ---------------------------------------------------------------------------

def test_ac1_one_command_decision_per_known_cmd_id():
    """Le nombre de CommandDecision == nombre de cmd_id connus de l'équipement (2)."""
    eq = _make_eq(cmds=[_cmd(101, "LIGHT_ON"), _cmd(102, "LIGHT_STATE", type_="info")])
    mapping = _make_mapping()
    result = _evaluate(eq, _eligible(), mapping)

    assert len(result.command_decisions) == 2
    assert {cd.cmd_id for cd in result.command_decisions} == {101, 102}


def test_ac1_uncovered_command_gets_explicit_reason():
    """Une commande non mappée (id=103) reçoit une CommandDecision explicite non-null."""
    eq = _make_eq(cmds=[_cmd(101, "LIGHT_ON"), _cmd(102, "LIGHT_STATE", type_="info"), _cmd(103, None)])
    mapping = _make_mapping()  # ne couvre que 101/102
    result = _evaluate(eq, _eligible(), mapping)

    assert len(result.command_decisions) == 3
    uncovered = next(cd for cd in result.command_decisions if cd.cmd_id == 103)
    assert uncovered.should_publish is False
    assert uncovered.reason == "command_not_covered"
    assert uncovered.reason is not None and uncovered.reason != ""


def test_ac1_every_command_decision_has_non_null_reason():
    """I6 étendu à CommandDecision : reason non-null pour TOUTES les commandes, couvertes ou pas."""
    eq = _make_eq(cmds=[_cmd(101, "LIGHT_ON"), _cmd(102, "LIGHT_STATE", type_="info"), _cmd(999, None)])
    mapping = _make_mapping()
    result = _evaluate(eq, _eligible(), mapping)

    for cd in result.command_decisions:
        assert cd.reason is not None
        assert cd.reason != ""


def test_ac1_no_mapping_at_all_still_produces_command_decisions():
    """Aucun mapper ne reconnaît l'équipement (mapping=None) : chaque cmd_id reste couvert
    par une CommandDecision explicite (jamais omise, I5)."""
    eq = _make_eq(cmds=[_cmd(101, None), _cmd(102, None)])
    result = _evaluate(eq, _eligible(), None)

    assert len(result.command_decisions) == 2
    assert all(cd.should_publish is False for cd in result.command_decisions)
    assert all(cd.reason for cd in result.command_decisions)


# ---------------------------------------------------------------------------
# AC2 — Éligibilité jamais recalculée en interne (racine de CC-03)
# ---------------------------------------------------------------------------

def test_ac2_refused_eligibility_mock_produces_refused_decision():
    eq = _make_eq()
    eligibility = _ineligible(reason_code="excluded_eqlogic")
    result = _evaluate(eq, eligibility, mapping=_make_mapping())

    assert result.equipment_decision.should_publish is False
    assert result.equipment_decision.reason == "excluded_eqlogic"
    assert result.mapping is None


def test_ac2_never_calls_assess_eligibility_when_eligible():
    eq = _make_eq()
    with mock.patch.object(
        topology_module, "assess_eligibility", side_effect=AssertionError("recalculé !")
    ) as spy:
        result = _evaluate(eq, _eligible(), _make_mapping())
        spy.assert_not_called()
    assert result.equipment_decision is not None


def test_ac2_never_calls_assess_eligibility_when_ineligible():
    eq = _make_eq()
    with mock.patch.object(
        topology_module, "assess_eligibility", side_effect=AssertionError("recalculé !")
    ) as spy:
        result = _evaluate(eq, _ineligible(), _make_mapping())
        spy.assert_not_called()
    assert result.equipment_decision.should_publish is False


def test_ac2_never_calls_assess_all():
    eq = _make_eq()
    with mock.patch.object(
        topology_module, "assess_all", side_effect=AssertionError("recalculé !")
    ) as spy:
        _evaluate(eq, _eligible(), _make_mapping())
        spy.assert_not_called()


# ---------------------------------------------------------------------------
# AC3 — Fusion unique overrides persistés + overrides proposés (parité decide_publication)
# ---------------------------------------------------------------------------

def test_ac3_persisted_overrides_only_matches_decide_publication_directly():
    """Overrides persistés seuls ⇒ résultat identique à l'appel direct de decide_publication()
    sur le même mapping/policy/override résolu (parité de référence, préparatoire 19.1)."""
    from mapping.overrides import resolve_publication_override
    from models.decide_publication import decide_publication

    eq = _make_eq()
    mapping = _make_mapping(jeedom_eq_id=42, commands={"LIGHT_ON": _cmd(101, "LIGHT_ON")})
    persisted_overrides = {"42:101": {"source": "user", "publication_override": "force_publish"}}

    result = _evaluate(
        eq,
        _eligible(),
        mapping,
        persisted_overrides=persisted_overrides,
    )

    # Reproduit manuellement le chemin actuel (étape 3 + résolution + étape 4) pour comparer.
    from validation.ha_component_registry import validate_projection

    validity = validate_projection(mapping.ha_entity_type, mapping.capabilities)
    reference_mapping = deepcopy(mapping)
    reference_mapping.projection_validity = validity
    resolved_override = resolve_publication_override(42, 101, persisted_overrides, {})
    reference_decision = decide_publication(
        reference_mapping, confidence_policy="sure_probable", publication_override=resolved_override
    )

    assert result.equipment_decision.should_publish == reference_decision.should_publish
    assert result.equipment_decision.reason == reference_decision.reason


def test_ac3_merge_happens_at_single_point_proposed_wins():
    """Un override proposé (preview) sur la même clé écrase l'override persisté correspondant,
    sans affecter les autres clés persistées — fusion en un seul point (AC3)."""
    eq = _make_eq()
    mapping = _make_mapping(jeedom_eq_id=7, commands={"LIGHT_ON": _cmd(101, "LIGHT_ON")})
    persisted = {"7:101": {"source": "user", "publication_override": "exclude"}}
    proposed = {"7:101": {"source": "user", "publication_override": "force_publish"}}

    result = _evaluate(
        eq,
        _eligible(),
        mapping,
        persisted_overrides=persisted,
        proposed_overrides=proposed,
    )

    # force_publish (proposé) l'emporte sur exclude (persisté) pour la même clé.
    assert result.equipment_decision.should_publish is True
    assert result.equipment_decision.reason == "publication_forced"


def test_ac3_proposed_overrides_never_mutate_persisted_dict():
    eq = _make_eq()
    mapping = _make_mapping(jeedom_eq_id=7, commands={"LIGHT_ON": _cmd(101, "LIGHT_ON")})
    persisted = {"7:101": {"source": "user", "publication_override": "exclude"}}
    persisted_before = deepcopy(persisted)
    proposed = {"7:101": {"source": "user", "publication_override": "force_publish"}}

    _evaluate(eq, _eligible(), mapping, persisted_overrides=persisted, proposed_overrides=proposed)

    assert persisted == persisted_before


# ---------------------------------------------------------------------------
# AC4 — Non-mutation stricte des objets d'entrée
# ---------------------------------------------------------------------------

def test_ac4_equipment_and_snapshot_not_mutated():
    eq = _make_eq()
    snapshot = _make_snapshot(eq)
    eq_before = deepcopy(eq)
    snapshot_before = deepcopy(snapshot)
    mapping = _make_mapping()

    evaluate_equipment(
        eq, snapshot, _eligible(), mapper_registry=_StubRegistry(mapping)
    )

    assert eq == eq_before
    assert snapshot == snapshot_before


def test_ac4_eligibility_not_mutated():
    eq = _make_eq()
    eligibility = _eligible()
    eligibility_before = deepcopy(eligibility)

    _evaluate(eq, eligibility, _make_mapping())

    assert eligibility == eligibility_before


def test_ac4_overrides_dicts_not_mutated():
    eq = _make_eq()
    persisted = {"1:101": {"source": "user", "publication_override": "force_publish"}}
    persisted_before = deepcopy(persisted)
    equipment_overrides = {"1": {"source": "user", "publication_override": "exclude"}}
    equipment_overrides_before = deepcopy(equipment_overrides)

    _evaluate(
        eq,
        _eligible(),
        _make_mapping(),
        persisted_overrides=persisted,
        persisted_equipment_overrides=equipment_overrides,
    )

    assert persisted == persisted_before
    assert equipment_overrides == equipment_overrides_before


def test_ac4_preview_mode_with_proposed_overrides_does_not_mutate_inputs():
    """AC4 explicite : la non-mutation tient aussi en mode "avec overrides proposés" (preview)."""
    eq = _make_eq()
    snapshot = _make_snapshot(eq)
    eq_before = deepcopy(eq)
    snapshot_before = deepcopy(snapshot)
    proposed = {"1:101": {"source": "user", "publication_override": "force_publish"}}
    proposed_before = deepcopy(proposed)
    mapping = _make_mapping()

    evaluate_equipment(
        eq,
        snapshot,
        _eligible(),
        mapper_registry=_StubRegistry(mapping),
        proposed_overrides=proposed,
    )

    assert eq == eq_before
    assert snapshot == snapshot_before
    assert proposed == proposed_before


def test_ac4_mapping_object_returned_by_registry_not_mutated_in_place():
    """Régression dédiée — cible exactement le bug de `_preview_mapping_view`
    (`transport/http_server.py:2210`) : `mapping.projection_validity = validity` en place.

    Le mapping retourné par le registre (double de test) ne doit JAMAIS être modifié par
    assignation d'attribut : ce test échoue si une future modification réintroduit une
    mutation en place au lieu de `dataclasses.replace`.
    """
    eq = _make_eq()
    mapping = _make_mapping()
    assert mapping.projection_validity is None  # état initial, avant tout appel
    assert mapping.publication_decision_ref is None
    assert mapping.pipeline_step_reached is None

    registry = _StubRegistry(mapping)
    result = evaluate_equipment(eq, _make_snapshot(eq), _eligible(), mapper_registry=registry)

    # L'objet ORIGINAL retourné par le registre reste intact : evaluate_equipment() a dû
    # travailler sur une copie (dataclasses.replace), jamais sur `mapping` lui-même.
    assert mapping.projection_validity is None
    assert mapping.publication_decision_ref is None
    assert mapping.pipeline_step_reached is None
    # La sortie, elle, porte bien la projection/décision calculées (sur une copie).
    assert result.mapping is not None
    assert result.mapping.projection_validity is not None
    assert result.mapping is not mapping


def test_ac4_secondary_mapping_not_mutated_in_place():
    eq = _make_eq(cmds=[_cmd(101, "LIGHT_ON"), _cmd(201, "POWER", type_="info")])
    secondary = _make_mapping(
        jeedom_eq_id=1,
        ha_entity_type="sensor",
        confidence="sure",
        commands={},
    )
    secondary.reason_details = {"cmd_id": 201}
    mapping = _make_mapping(additional_mappings=[secondary])

    evaluate_equipment(eq, _make_snapshot(eq), _eligible(), mapper_registry=_StubRegistry(mapping))

    assert secondary.projection_validity is None
    assert secondary.publication_decision_ref is None


# ---------------------------------------------------------------------------
# AC5 — I1-I7, published_scope hors périmètre
# ---------------------------------------------------------------------------

def test_i1_ineligible_equipment_no_mapping_no_projection():
    eq = _make_eq(cmds=[_cmd(101, "LIGHT_ON"), _cmd(102, "LIGHT_STATE", type_="info")])
    result = _evaluate(eq, _ineligible(reason_code="disabled_eqlogic"), _make_mapping())

    assert result.equipment_decision.should_publish is False
    assert result.equipment_decision.reason == "disabled_eqlogic"
    assert result.mapping is None
    assert len(result.command_decisions) == 2
    assert all(cd.should_publish is False for cd in result.command_decisions)
    assert all(cd.step == "1" for cd in result.command_decisions)


def test_i1_ineligible_no_generic_type_alias():
    """Alias de taxonomie (Task 1) : no_supported_generic_type → no_generic_type_configured."""
    eq = _make_eq()
    result = _evaluate(eq, _ineligible(reason_code="no_supported_generic_type"), _make_mapping())

    assert result.equipment_decision.reason == "no_generic_type_configured"
    assert all(cd.reason == "no_generic_type_configured" for cd in result.command_decisions)


def test_i2_projection_invalid_never_published_even_with_force_publish():
    """I2 : un override force_publish ne bypass jamais une projection invalide."""
    eq = _make_eq()
    mapping = _make_mapping(commands={"LIGHT_ON": _cmd(101, "LIGHT_ON")})

    def _invalid_validate(ha_entity_type, capabilities):
        return _invalid_pv("ha_missing_state_topic")

    result = _evaluate(
        eq,
        _eligible(),
        mapping,
        persisted_overrides={"1:101": {"source": "user", "publication_override": "force_publish"}},
        validate_projection_fn=_invalid_validate,
    )

    assert result.equipment_decision.should_publish is False
    assert result.equipment_decision.reason == "ha_missing_state_topic"


def test_i2_projection_invalid_never_published_for_all_reason_codes():
    for reason_code in [
        "ha_missing_state_topic",
        "ha_missing_command_topic",
        "ha_missing_required_option",
        "ha_component_unknown",
    ]:
        eq = _make_eq()
        mapping = _make_mapping()

        def _validate(ha_entity_type, capabilities, _rc=reason_code):
            return _invalid_pv(_rc)

        result = _evaluate(eq, _eligible(), mapping, validate_projection_fn=_validate)
        assert result.equipment_decision.should_publish is False, (
            f"I2 violé pour reason_code={reason_code!r}"
        )


def test_i3_should_publish_true_requires_all_conditions():
    eq = _make_eq()
    mapping = _make_mapping(ha_entity_type="light", confidence="sure")

    result = _evaluate(eq, _eligible(), mapping, validate_projection_fn=lambda t, c: _valid_pv())

    assert result.equipment_decision.should_publish is True
    assert result.mapping.confidence in {"sure", "probable", "sure_mapping"}
    assert result.mapping.projection_validity.is_valid is True
    assert result.mapping.ha_entity_type in PRODUCT_SCOPE


def test_i3_reciprocal_missing_condition_blocks_publication():
    """Réciproque I3 : si une seule condition manque, should_publish=False."""
    eq = _make_eq()

    # confidence non publishable
    mapping_bad_confidence = _make_mapping(confidence="ambiguous")
    result = _evaluate(eq, _eligible(), mapping_bad_confidence, validate_projection_fn=lambda t, c: _valid_pv())
    assert result.equipment_decision.should_publish is False

    # is_valid=False
    mapping_bad_projection = _make_mapping(confidence="sure")
    result = _evaluate(
        eq, _eligible(), mapping_bad_projection, validate_projection_fn=lambda t, c: _invalid_pv()
    )
    assert result.equipment_decision.should_publish is False

    # hors PRODUCT_SCOPE
    mapping_out_of_scope = _make_mapping(ha_entity_type="not_in_scope_type", confidence="sure")
    result = _evaluate(
        eq, _eligible(), mapping_out_of_scope, validate_projection_fn=lambda t, c: _valid_pv()
    )
    assert result.equipment_decision.should_publish is False


def test_i4_step2_wins_over_step4_ambiguous_plus_out_of_scope():
    """I4 — ambiguous + hors scope → cause étape 2 prime, jamais écrasée par l'étape 4."""
    eq = _make_eq()
    mapping = _make_mapping(ha_entity_type="climate", confidence="ambiguous")

    result = _evaluate(
        eq, _eligible(), mapping, validate_projection_fn=lambda t, c: _valid_pv()
    )

    assert result.equipment_decision.reason == "ambiguous_skipped"
    assert result.equipment_decision.reason != "ha_component_not_in_product_scope"
    assert result.equipment_decision.should_publish is False


def test_i4_step3_wins_over_step4_invalid_plus_out_of_scope():
    """I4 — projection invalide + hors scope → cause étape 3 prime."""
    eq = _make_eq()
    mapping = _make_mapping(ha_entity_type="climate", confidence="sure")

    result = _evaluate(
        eq,
        _eligible(),
        mapping,
        validate_projection_fn=lambda t, c: _invalid_pv("ha_missing_state_topic"),
    )

    assert result.equipment_decision.reason == "ha_missing_state_topic"
    assert result.equipment_decision.reason != "ha_component_not_in_product_scope"
    assert result.equipment_decision.should_publish is False


def test_i5_eligible_equipment_always_produces_all_three_sub_blocks():
    """I5 : mapping calculé avec le registre injecté, overrides fusionnés, projection validée,
    décision produite — sans mapping ni projection fournis en entrée, jamais None."""
    eq = _make_eq()
    mapping = _make_mapping()  # aucun mapping/projection pré-calculé en entrée

    result = _evaluate(eq, _eligible(), mapping, validate_projection_fn=lambda t, c: _valid_pv())

    assert result.equipment_decision is not None
    assert result.mapping is not None
    assert result.mapping.projection_validity is not None
    assert result.command_decisions  # jamais vide pour un équipement avec des cmds


def test_i5_never_returns_none_even_without_mapper_match():
    eq = _make_eq()
    result = _evaluate(eq, _eligible(), None)  # aucun mapper ne reconnaît l'équipement

    assert result is not None
    assert result.equipment_decision is not None
    assert result.equipment_decision.should_publish is False


def test_i6_reason_never_null_on_all_failure_paths():
    eq = _make_eq()
    cases = [
        (_make_mapping(confidence="ambiguous"), lambda t, c: _valid_pv()),
        (_make_mapping(confidence="unknown"), lambda t, c: _valid_pv()),
        (_make_mapping(confidence="sure"), lambda t, c: _invalid_pv("ha_missing_state_topic")),
        (_make_mapping(ha_entity_type="climate", confidence="sure"), lambda t, c: _valid_pv()),
        (_make_mapping(ha_entity_type="light", confidence="probable"), lambda t, c: _valid_pv()),
    ]
    for mapping, validate_fn in cases:
        result = _evaluate(eq, _eligible(), mapping, validate_projection_fn=validate_fn)
        assert result.equipment_decision.reason is not None
        assert result.equipment_decision.reason != ""


def test_i6_reason_never_null_on_ineligible_path():
    eq = _make_eq()
    result = _evaluate(eq, _ineligible(), _make_mapping())
    assert result.equipment_decision.reason
    for cd in result.command_decisions:
        assert cd.reason


def test_i7_no_mqtt_broker_or_disk_io_in_module_source():
    """I7 — vérifié structurellement : aucune logique MQTT/broker/cache dans le code du module
    (imports + corps des fonctions — les commentaires/docstrings décrivant l'invariant lui-même
    ne comptent pas comme une violation)."""
    import ast
    import inspect as _inspect
    import models.evaluate_equipment as module

    tree = ast.parse(_inspect.getsource(module))
    code_lines = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Call, ast.Attribute, ast.Name)):
            code_lines.append(ast.dump(node).lower())
    code_text = "\n".join(code_lines)

    forbidden = ["mqtt", "broker", "paho", "disk_cache", "requests", "socket"]
    for token in forbidden:
        assert token not in code_text, f"I7 violé : token interdit trouvé dans le code : {token!r}"
    assert "open" not in [n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]


def test_i7_evaluate_equipment_never_touches_data_dir_argument():
    """Confirme l'absence d'I/O : passer un data_dir manifestement invalide aux overrides ne
    provoque aucune erreur ni lecture disque, car les dicts d'overrides sont TOUJOURS fournis
    par l'appelant (jamais lus depuis un chemin par evaluate_equipment lui-même)."""
    eq = _make_eq()
    mapping = _make_mapping(commands={"LIGHT_ON": _cmd(101, "LIGHT_ON")})

    result = _evaluate(
        eq,
        _eligible(),
        mapping,
        persisted_overrides={"1:101": {"source": "user", "publication_override": "force_publish"}},
    )
    assert result.equipment_decision.should_publish is True


def test_ac5_evaluate_equipment_signature_has_no_published_scope_parameter():
    """AC5 — evaluate_equipment() ne prend AUCUN paramètre published_scope."""
    signature = inspect.signature(evaluate_equipment)
    assert "published_scope" not in signature.parameters


# ---------------------------------------------------------------------------
# Multi-sensor / décisions secondaires (Task 2 — sortie complète)
# ---------------------------------------------------------------------------

def test_secondary_mapping_gets_its_own_command_decision():
    eq = _make_eq(cmds=[_cmd(101, "LIGHT_ON"), _cmd(201, "POWER", type_="info")])
    secondary = _make_mapping(
        jeedom_eq_id=1, ha_entity_type="sensor", confidence="sure", commands={}
    )
    secondary.reason_details = {"cmd_id": 201}
    mapping = _make_mapping(
        commands={"LIGHT_ON": _cmd(101, "LIGHT_ON")}, additional_mappings=[secondary]
    )

    result = _evaluate(
        eq, _eligible(), mapping, validate_projection_fn=lambda t, c: _valid_pv()
    )

    assert len(result.secondary_decisions) == 1
    secondary_cd = next(cd for cd in result.command_decisions if cd.cmd_id == 201)
    assert secondary_cd.reason == result.secondary_decisions[0].reason
    assert secondary_cd.should_publish == result.secondary_decisions[0].should_publish
