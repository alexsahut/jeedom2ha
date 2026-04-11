"""Tests de l'étape 1 — Éligibilité — Story 1.2.

Vérifie que assess_eligibility() classe chaque équipement dans une catégorie
stable et distincte. Tests exécutables en isolation (NFR9) : aucune dépendance
MQTT, pytest-asyncio, ou runtime Jeedom.
"""
from models.topology import (
    JeedomCmd,
    JeedomEqLogic,
    TopologySnapshot,
    assess_eligibility,
    assess_all,
    EligibilityResult,
)


# ---------------------------------------------------------------------------
# Helpers locaux au fichier (pas de conftest.py)
# ---------------------------------------------------------------------------

def _make_eq(id=1, is_excluded=False, exclusion_source=None,
             is_enable=True, cmds=None) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=id,
        name="Test",
        is_excluded=is_excluded,
        exclusion_source=exclusion_source,
        is_enable=is_enable,
        cmds=cmds or [],
    )


def _cmd_with_generic(gt="LIGHT_ON") -> JeedomCmd:
    return JeedomCmd(id=1, name="On", generic_type=gt, type="action", sub_type="other")


def _cmd_no_generic() -> JeedomCmd:
    return JeedomCmd(id=2, name="Info", generic_type=None, type="info", sub_type="other")


# ---------------------------------------------------------------------------
# Task 1 — Cas nominaux (AC #1, #6)
# ---------------------------------------------------------------------------

def test_eligibility_nominal_eligible():
    """AC #1 : équipement avec is_enable=True, cmds=[cmd avec generic_type],
    is_excluded=False → is_eligible=True, reason_code="eligible"."""
    eq = _make_eq(is_enable=True, cmds=[_cmd_with_generic()])
    result = assess_eligibility(eq)
    assert result.is_eligible is True
    assert result.reason_code == "eligible"


def test_eligibility_eligible_confidence_unknown():
    """AC #1 : un équipement éligible porte confidence="unknown" — incertitude sur
    le mapping (étape 2), pas sur l'éligibilité elle-même."""
    eq = _make_eq(is_enable=True, cmds=[_cmd_with_generic()])
    result = assess_eligibility(eq)
    assert result.confidence == "unknown"


def test_assess_all_batch():
    """AC #6/NFR9 : assess_all(snapshot) retourne un dict {eq_id: EligibilityResult}
    pour tous les équipements du snapshot, sans dépendance MQTT ni runtime."""
    snapshot = TopologySnapshot(
        timestamp="2026-04-10T00:00:00Z",
        eq_logics={
            1: _make_eq(id=1, is_enable=True, cmds=[_cmd_with_generic()]),
            2: _make_eq(id=2, is_enable=False),
            3: _make_eq(id=3, is_excluded=True, exclusion_source="plugin"),
        },
    )
    results = assess_all(snapshot)
    assert isinstance(results, dict)
    assert set(results.keys()) == {1, 2, 3}
    assert all(isinstance(v, EligibilityResult) for v in results.values())
    assert results[1].is_eligible is True
    assert results[2].is_eligible is False
    assert results[3].is_eligible is False


# ---------------------------------------------------------------------------
# Task 2 — Cas d'exclusion de scope (AC #2)
# ---------------------------------------------------------------------------

def test_eligibility_excluded_eqlogic():
    """AC #2 : exclusion individuelle → reason_code="excluded_eqlogic", is_eligible=False."""
    eq = _make_eq(is_excluded=True, exclusion_source="eqlogic")
    result = assess_eligibility(eq)
    assert result.is_eligible is False
    assert result.reason_code == "excluded_eqlogic"
    assert result.confidence == "sure"


def test_eligibility_excluded_plugin():
    """AC #2 : exclusion par plugin → reason_code="excluded_plugin", is_eligible=False."""
    eq = _make_eq(is_excluded=True, exclusion_source="plugin")
    result = assess_eligibility(eq)
    assert result.is_eligible is False
    assert result.reason_code == "excluded_plugin"
    assert result.confidence == "sure"


def test_eligibility_excluded_object():
    """AC #2 : exclusion par objet Jeedom → reason_code="excluded_object", is_eligible=False."""
    eq = _make_eq(is_excluded=True, exclusion_source="object")
    result = assess_eligibility(eq)
    assert result.is_eligible is False
    assert result.reason_code == "excluded_object"
    assert result.confidence == "sure"


def test_eligibility_excluded_source_absent_defaults_eqlogic():
    """AC #2 — rétro-compatibilité : exclusion_source=None → reason_code="excluded_eqlogic"."""
    eq = _make_eq(is_excluded=True, exclusion_source=None)
    result = assess_eligibility(eq)
    assert result.is_eligible is False
    assert result.reason_code == "excluded_eqlogic"


# ---------------------------------------------------------------------------
# Task 3 — Cas d'inéligibilité hors exclusion (AC #3, #4, #5)
# ---------------------------------------------------------------------------

def test_eligibility_disabled_eqlogic():
    """AC #3 : équipement désactivé (is_enable=False) → reason_code="disabled_eqlogic",
    is_eligible=False, confidence="sure"."""
    eq = _make_eq(is_enable=False, cmds=[_cmd_with_generic()])
    result = assess_eligibility(eq)
    assert result.is_eligible is False
    assert result.reason_code == "disabled_eqlogic"
    assert result.confidence == "sure"


def test_eligibility_no_commands():
    """AC #4 : aucune commande (cmds=[]) → reason_code="no_commands",
    is_eligible=False, confidence="sure"."""
    eq = _make_eq(is_enable=True, cmds=[])
    result = assess_eligibility(eq)
    assert result.is_eligible is False
    assert result.reason_code == "no_commands"
    assert result.confidence == "sure"


def test_eligibility_no_generic_type():
    """AC #5 : commandes présentes mais toutes generic_type=None →
    reason_code="no_supported_generic_type" (NFR8 : code existant V1.1, pas renommé),
    is_eligible=False, confidence="sure"."""
    eq = _make_eq(is_enable=True, cmds=[_cmd_no_generic()])
    result = assess_eligibility(eq)
    assert result.is_eligible is False
    assert result.reason_code == "no_supported_generic_type"
    assert result.confidence == "sure"


def test_eligibility_partial_generic_type_is_eligible():
    """AC #5 — distinction FR8 : au moins une commande avec generic_type non-None,
    même si d'autres sont None → is_eligible=True (l'éligibilité ne requiert qu'UN generic_type)."""
    eq = _make_eq(is_enable=True, cmds=[_cmd_no_generic(), _cmd_with_generic("LIGHT_ON")])
    result = assess_eligibility(eq)
    assert result.is_eligible is True
    assert result.reason_code == "eligible"


# ---------------------------------------------------------------------------
# Task 4 — Tests de priorité d'évaluation (ordre canonique)
# exclu > désactivé > sans cmds > sans generic_type
# ---------------------------------------------------------------------------

def test_priority_excluded_over_disabled():
    """Priorité : un équipement à la fois exclu et désactivé →
    reason_code="excluded_eqlogic" (exclu gagne, priorité 1)."""
    eq = _make_eq(is_excluded=True, exclusion_source="eqlogic", is_enable=False)
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"
    assert result.is_eligible is False


def test_priority_disabled_over_no_commands():
    """Priorité : équipement désactivé sans commandes →
    reason_code="disabled_eqlogic" (désactivé gagne, priorité 2)."""
    eq = _make_eq(is_excluded=False, is_enable=False, cmds=[])
    result = assess_eligibility(eq)
    assert result.reason_code == "disabled_eqlogic"
    assert result.is_eligible is False


def test_priority_no_commands_over_no_generic_type():
    """Priorité : équipement actif, non-exclu, sans commandes (et donc implicitement
    sans generic_type) → reason_code="no_commands" (no_commands gagne, priorité 3)."""
    eq = _make_eq(is_excluded=False, is_enable=True, cmds=[])
    result = assess_eligibility(eq)
    assert result.reason_code == "no_commands"
    assert result.is_eligible is False
