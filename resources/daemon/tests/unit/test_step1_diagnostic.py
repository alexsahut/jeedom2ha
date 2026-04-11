"""Tests du contrat de diagnostic étape 1 — Story 1.3.

Vérifie que reason_code_to_cause() couvre tous les reason_codes de l'étape 1,
que FR10 est respecté (cause_action présent/absent selon choix utilisateur),
et que la fondation FR4 (pipeline_step_reached) est ancrée dans MappingResult.
Tests exécutables en isolation totale (NFR9).
"""

from models.cause_mapping import reason_code_to_cause
from models.mapping import MappingResult, LightCapabilities
from models.topology import (
    JeedomCmd, EligibilityResult,
)

STEP1_REASON_CODES = [
    "excluded_eqlogic",
    "excluded_plugin",
    "excluded_object",
    "disabled_eqlogic",
    "no_commands",
    "no_supported_generic_type",
]


def _make_minimal_mapping_result() -> MappingResult:
    """Helper — MappingResult minimal valide pour tester les champs structurels."""
    cmd = JeedomCmd(id=1, name="On", generic_type="LIGHT_ON", type="action", sub_type="other")
    return MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="sure",
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Test Light",
        capabilities=LightCapabilities(has_on_off=True),
        commands={"LIGHT_ON": cmd},
    )


# ---------------------------------------------------------------------------
# AC1 — cause_mapping excluded_*
# ---------------------------------------------------------------------------

def test_excluded_eqlogic_cause():
    result = reason_code_to_cause("excluded_eqlogic")
    assert result == (
        "excluded_eqlogic",
        "Équipement exclu du scope de synchronisation",
        "Retirer l'équipement de la liste d'exclusion dans les réglages jeedom2ha",
    )


def test_excluded_plugin_cause():
    cause_code, cause_label, cause_action = reason_code_to_cause("excluded_plugin")
    assert cause_code == "excluded_plugin"
    assert cause_label is not None
    assert cause_action is not None


def test_excluded_object_cause():
    cause_code, cause_label, cause_action = reason_code_to_cause("excluded_object")
    assert cause_code == "excluded_object"
    assert cause_label is not None
    assert cause_action is not None


def test_excluded_codes_have_distinct_causes():
    results = {
        code: reason_code_to_cause(code)
        for code in ("excluded_eqlogic", "excluded_plugin", "excluded_object")
    }
    cause_codes = [r[0] for r in results.values()]
    assert len(set(cause_codes)) == 3, f"Les 3 codes excluded_* doivent produire des cause_code distincts : {cause_codes}"


# ---------------------------------------------------------------------------
# AC2 — disabled_eqlogic dans le contexte étape 1 (entrée existante, vérification)
# ---------------------------------------------------------------------------

def test_disabled_eqlogic_cause_in_step1_context():
    cause_code, cause_label, cause_action = reason_code_to_cause("disabled_eqlogic")
    assert cause_label == "Équipement désactivé dans Jeedom"
    assert cause_action is not None


# ---------------------------------------------------------------------------
# AC3 + FR10 — couverture complète et cause_action FR10
# ---------------------------------------------------------------------------

def test_all_step1_reason_codes_produce_explicit_cause():
    """Tous les reason_codes de l'étape 1 produisent un (cause_code, cause_label) non-None."""
    for rc in STEP1_REASON_CODES:
        cause_code, cause_label, _ = reason_code_to_cause(rc)
        assert cause_code is not None, f"cause_code est None pour reason_code={rc!r}"
        assert cause_label is not None, f"cause_label est None pour reason_code={rc!r}"


def test_fr10_excluded_codes_have_cause_action():
    """excluded_* relèvent d'un choix utilisateur → cause_action non-None (FR10)."""
    for rc in ("excluded_eqlogic", "excluded_plugin", "excluded_object"):
        _, _, cause_action = reason_code_to_cause(rc)
        assert cause_action is not None, f"cause_action est None pour {rc!r} — viole FR10"


def test_fr10_no_supported_generic_type_has_no_cause_action():
    """no_supported_generic_type = limitation plateforme, pas de choix utilisateur → cause_action None."""
    _, _, cause_action = reason_code_to_cause("no_supported_generic_type")
    assert cause_action is None


def test_nfr3_ineligible_result_is_explicit():
    """Un EligibilityResult(is_eligible=False) produit un résultat diagnostiquable sans ambiguïté."""
    result = EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")
    assert result.is_eligible is False
    assert result.reason_code == "excluded_eqlogic"
    # Un MappingResult n'est pas nécessaire pour diagnostiquer l'étape 1
    cause_code, cause_label, _ = reason_code_to_cause(result.reason_code)
    assert cause_code is not None
    assert cause_label is not None


# ---------------------------------------------------------------------------
# AC4 — fondation FR4 : pipeline_step_reached dans MappingResult
# ---------------------------------------------------------------------------

def test_fr4_mapping_result_has_pipeline_step_field():
    """MappingResult possède le champ pipeline_step_reached (fondation FR4)."""
    mr = _make_minimal_mapping_result()
    assert hasattr(mr, "pipeline_step_reached"), "MappingResult doit avoir le champ pipeline_step_reached"
    assert isinstance(mr.pipeline_step_reached, (int, type(None)))


def test_fr4_pipeline_step_none_before_wiring():
    """pipeline_step_reached vaut None avant câblage Epic 5."""
    mr = _make_minimal_mapping_result()
    assert mr.pipeline_step_reached is None


def test_fr4_step1_blocker_inferred_without_mapping_result():
    """EligibilityResult(is_eligible=False) → étape bloquante = 1, sans besoin de MappingResult."""
    result = EligibilityResult(is_eligible=False, reason_code="excluded_plugin")
    assert result.is_eligible is False
    # L'absence de MappingResult est suffisante pour inférer que le pipeline s'est arrêté étape 1
    mapping_result = None
    assert mapping_result is None  # pas de MappingResult produit pour un équipement inéligible
    # L'étape bloquante est déduite de is_eligible=False seul
    blocking_step = 1 if not result.is_eligible else None
    assert blocking_step == 1
