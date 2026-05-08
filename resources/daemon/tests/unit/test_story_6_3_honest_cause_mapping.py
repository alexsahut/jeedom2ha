"""Story 6.3 — Sémantique honnête cause_label / cause_action — règle no faux CTA.

Objectifs couverts :
- AC1 : cause_label jamais null/vide pour tous les reason_codes actifs
- AC2 : codes class 2 → cause_action = None (contrainte physique, pas d'action utilisateur)
- AC3 : code class 3 → cause_action = None (gouvernance de cycle)
- AC4 : cause_action non-null uniquement si action réelle — jamais "Choisir manuellement..."
- AC5 : libellés distincts step 3 vs step 4 pour ambiguous_skipped
- AC6 : trois catégories step 2 produisent des libellés distincts
- AC7 : non-régression des invariants pipeline (I4 / I7)
"""

from __future__ import annotations

import pytest

from models.cause_mapping import (
    CAUSE_MAPPING,
    _REASON_CODE_TO_CAUSE,
    reason_code_to_cause,
    resolve_cause_ux,
)

# --- Reason codes actifs (direction 1, inclus mais non publié) ---
ACTIVE_REASON_CODES = [
    "excluded_eqlogic",
    "excluded_plugin",
    "excluded_object",
    "ambiguous_skipped",
    "probable_skipped",
    "no_mapping",
    "no_supported_generic_type",
    "no_generic_type_configured",
    "disabled_eqlogic",
    "disabled",
    "no_commands",
    "discovery_publish_failed",
    "local_availability_publish_failed",
    "low_confidence",
    "ha_component_not_in_product_scope",
    "eligible",
    "ha_missing_command_topic",
    "ha_missing_state_topic",
    "ha_missing_required_option",
    "ha_component_unknown",
]

CLASS_2_REASON_CODES = [
    "ha_missing_command_topic",
    "ha_missing_state_topic",
    "ha_missing_required_option",
]

CLASS_3_REASON_CODES = [
    "ha_component_not_in_product_scope",
]

FAUX_CTA_FORBIDDEN = "Choisir manuellement le type d'équipement"


# ==============================================================
# AC1 — cause_label jamais null/vide pour 100 % des reason_codes actifs
# ==============================================================

@pytest.mark.parametrize("reason_code", ACTIVE_REASON_CODES)
def test_ac1_cause_label_never_null_or_empty(reason_code):
    """AC1 : tout reason_code actif produit un cause_label non vide."""
    _, cause_label, _ = reason_code_to_cause(reason_code)
    assert isinstance(cause_label, str), f"{reason_code!r} → cause_label doit être str"
    assert cause_label.strip(), f"{reason_code!r} → cause_label ne doit pas être vide"


@pytest.mark.parametrize("reason_code", ACTIVE_REASON_CODES)
def test_ac1_resolve_cause_ux_always_provides_label(reason_code):
    """AC1 : resolve_cause_ux retourne un cause_label non vide pour tout reason_code actif."""
    result = resolve_cause_ux(reason_code, 2)
    assert isinstance(result["cause_label"], str)
    assert result["cause_label"].strip(), f"{reason_code!r} → cause_label vide via resolve_cause_ux"


# ==============================================================
# AC2 — codes class 2 (invalidité HA) : cause_action = None
# ==============================================================

@pytest.mark.parametrize("reason_code", CLASS_2_REASON_CODES)
def test_ac2_class2_cause_action_is_none(reason_code):
    """AC2 : codes class 2 → cause_action = None — contrainte physique."""
    _, _, cause_action = reason_code_to_cause(reason_code)
    assert cause_action is None, (
        f"{reason_code!r} est class 2 — cause_action doit être None, pas {cause_action!r}"
    )


@pytest.mark.parametrize("reason_code", CLASS_2_REASON_CODES)
def test_ac2_resolve_cause_ux_class2_returns_null_action(reason_code):
    """AC2 : resolve_cause_ux retourne cause_action=None pour les codes class 2."""
    result = resolve_cause_ux(reason_code, 3)
    assert result["cause_action"] is None, (
        f"{reason_code!r} step 3 → cause_action={result['cause_action']!r}, attendu None"
    )


@pytest.mark.parametrize("reason_code", CLASS_2_REASON_CODES)
def test_ac2_class2_labels_express_ha_invalidity(reason_code):
    """AC2 : les libellés class 2 expriment clairement l'invalidité de la projection HA."""
    _, cause_label, _ = reason_code_to_cause(reason_code)
    assert "Projection HA incomplète" in cause_label, (
        f"{reason_code!r} → cause_label doit contenir 'Projection HA incomplète', got {cause_label!r}"
    )


# ==============================================================
# AC3 — code class 3 (scope produit) : cause_action = None
# ==============================================================

@pytest.mark.parametrize("reason_code", CLASS_3_REASON_CODES)
def test_ac3_class3_cause_action_is_none(reason_code):
    """AC3 : codes class 3 → cause_action = None — gouvernance de cycle."""
    _, _, cause_action = reason_code_to_cause(reason_code)
    assert cause_action is None, (
        f"{reason_code!r} est class 3 — cause_action doit être None, pas {cause_action!r}"
    )


def test_ac3_class3_label_expresses_governance():
    """AC3 : le libellé class 3 distingue la gouvernance d'ouverture du produit d'un problème de mapping."""
    _, cause_label, _ = reason_code_to_cause("ha_component_not_in_product_scope")
    label_lower = cause_label.lower()
    assert cause_label.strip()
    assert "arbitraire" not in label_lower, (
        "Le libellé ne doit pas suggérer une fermeture arbitraire du produit"
    )
    # Gouvernance explicite : doit mentionner au moins cycle OU périmètre
    assert "cycle" in label_lower or "périmètre" in label_lower, (
        "Le libellé doit exprimer la gouvernance de cycle / périmètre"
    )
    # Distinction avec un problème de mapping : le libellé ne doit pas évoquer une erreur de mapping
    forbidden_mapping_terms = ["ambig", "incompatible", "aucun mapping", "non reconnu", "inconnu"]
    for term in forbidden_mapping_terms:
        assert term not in label_lower, (
            f"Le libellé class 3 ne doit pas évoquer un problème de mapping ({term!r}), "
            f"got {cause_label!r}"
        )


# ==============================================================
# AC4 — cause_action null si aucune remédiation réelle, jamais faux CTA
# ==============================================================

def test_ac4_faux_cta_eliminated_step4_ambiguous_skipped():
    """AC4 : 'Choisir manuellement...' éliminé ; Story 9.5 — CTA réel non-null (types génériques Jeedom)."""
    result = resolve_cause_ux("ambiguous_skipped", 4)
    # Story 9.5 — cause_action est maintenant non-null : surface vague 1 réelle (types génériques dans Jeedom)
    assert result["cause_action"] is not None and len(result["cause_action"]) > 0, (
        f"step 4 ambiguous_skipped → cause_action attendu non-null (CTA réel Story 9.5), got {result['cause_action']!r}"
    )
    assert result["cause_action"] != FAUX_CTA_FORBIDDEN


def test_ac4_faux_cta_eliminated_step4_ambiguous():
    """AC4 : 'Choisir manuellement...' éliminé ; Story 9.5 — CTA réel non-null (symétrie legacy)."""
    result = resolve_cause_ux("ambiguous", 4)
    assert result["cause_action"] is not None and len(result["cause_action"]) > 0
    assert result["cause_action"] != FAUX_CTA_FORBIDDEN


@pytest.mark.parametrize("reason_code", ACTIVE_REASON_CODES)
@pytest.mark.parametrize("step", [2, 3, 4, 5])
def test_ac4_no_faux_cta_in_any_resolve(reason_code, step):
    """AC4 : aucun faux CTA dans tous les appels à resolve_cause_ux."""
    result = resolve_cause_ux(reason_code, step)
    assert result.get("cause_action") != FAUX_CTA_FORBIDDEN, (
        f"{reason_code!r} step {step} → faux CTA détecté : {result['cause_action']!r}"
    )


# ==============================================================
# AC5 — libellés distincts step 3 vs step 4 pour ambiguous_skipped
# ==============================================================

def test_ac5_step3_and_step4_different_labels_ambiguous_skipped():
    """AC5 : step 3 et step 4 produisent des cause_label distincts pour ambiguous_skipped."""
    step3 = resolve_cause_ux("ambiguous_skipped", 3)
    step4 = resolve_cause_ux("ambiguous_skipped", 4)
    assert step3["cause_label"] != step4["cause_label"], (
        "step 3 et step 4 doivent avoir des cause_label distincts pour ambiguous_skipped"
    )


def test_ac5_step3_label_expresses_projection_problem():
    """AC5 : le libellé step 3 exprime un problème de projection / validation technique."""
    result = resolve_cause_ux("ambiguous_skipped", 3)
    label = result["cause_label"]
    # doit contenir un terme lié à la projection HA, pas uniquement à la publication
    assert any(term in label.lower() for term in ["projection", "validation", "ha", "structurel"]), (
        f"step 3 cause_label doit exprimer un problème de projection, got {label!r}"
    )


def test_ac5_step4_label_expresses_publication_decision():
    """AC5 : le libellé step 4 exprime un arbitrage de décision / publication."""
    result = resolve_cause_ux("ambiguous_skipped", 4)
    label = result["cause_label"]
    assert any(term in label.lower() for term in ["arbitrage", "publication", "décision", "automatique"]), (
        f"step 4 cause_label doit exprimer la décision/publication, got {label!r}"
    )


def test_ac5_step3_and_step4_no_faux_cta():
    """AC5 : aucun faux CTA dans step 3 ou step 4 pour ambiguous_skipped."""
    for step in (3, 4):
        result = resolve_cause_ux("ambiguous_skipped", step)
        assert result["cause_action"] != FAUX_CTA_FORBIDDEN


# ==============================================================
# AC6 — trois catégories step 2 produisent des libellés distincts
# ==============================================================

def test_ac6_three_step2_categories_have_distinct_labels():
    """AC6 : impossibilité / ambiguïté / scope produisent des cause_label distincts."""
    # impossibilité de mapping
    no_mapping_label = resolve_cause_ux("no_mapping", 2)["cause_label"]
    # ambiguïté de mapping
    ambiguous_label = resolve_cause_ux("ambiguous_skipped", 2)["cause_label"]
    # limitation de scope produit
    scope_label = resolve_cause_ux("no_supported_generic_type", 2)["cause_label"]

    assert no_mapping_label != ambiguous_label, "impossibilité ≠ ambiguïté"
    assert no_mapping_label != scope_label, "impossibilité ≠ scope"
    assert ambiguous_label != scope_label, "ambiguïté ≠ scope"


def test_ac6_no_supported_generic_type_label_no_v1_branding():
    """AC6 : no_supported_generic_type ne doit pas référencer 'V1' arbitrairement."""
    _, cause_label, _ = reason_code_to_cause("no_supported_generic_type")
    assert "V1" not in cause_label, (
        "Le libellé ne doit pas faire référence à 'V1' (gouvernance de scope, pas de version)"
    )
    assert cause_label.strip(), "cause_label ne doit pas être vide"


def test_ac6_scope_label_expresses_cycle_governance():
    """AC6 : le libellé 'limitation de scope' exprime la gouvernance de cycle."""
    _, cause_label, _ = reason_code_to_cause("no_supported_generic_type")
    assert "cycle" in cause_label.lower() or "périmètre" in cause_label.lower(), (
        "Le libellé de scope doit exprimer la gouvernance de cycle / périmètre"
    )


def test_ac6_ambiguity_label_expresses_configuration_problem():
    """AC6 : le libellé 'ambiguïté' exprime une configuration Jeedom à préciser."""
    _, cause_label, _ = reason_code_to_cause("ambiguous_skipped")
    assert "ambigu" in cause_label.lower() or "plusieurs" in cause_label.lower(), (
        "Le libellé d'ambiguïté doit exprimer les multiples types possibles"
    )


# ==============================================================
# AC7 — non-régression des reason_codes et invariants pipeline
# ==============================================================

def test_ac7_no_reason_code_removed():
    """AC7 : aucun reason_code existant n'est supprimé de la table."""
    for code in ACTIVE_REASON_CODES:
        entry = _REASON_CODE_TO_CAUSE.get(code)
        assert entry is not None, f"{code!r} a été supprimé de _REASON_CODE_TO_CAUSE"


def test_ac7_reason_code_to_cause_keys_unchanged():
    """AC7 : les clés de _REASON_CODE_TO_CAUSE n'ont pas changé."""
    historical_keys = {
        "excluded_eqlogic", "excluded_plugin", "excluded_object",
        "ambiguous_skipped", "probable_skipped", "no_mapping",
        "no_supported_generic_type", "no_generic_type_configured",
        "disabled_eqlogic", "disabled", "no_commands",
        "discovery_publish_failed", "local_availability_publish_failed",
        "low_confidence", "ha_component_not_in_product_scope",
        "eligible",
        "ha_missing_command_topic", "ha_missing_state_topic",
        "ha_missing_required_option", "ha_component_unknown",
        "sure", "probable", "sure_mapping",
    }
    current_keys = set(_REASON_CODE_TO_CAUSE.keys())
    removed = historical_keys - current_keys
    assert not removed, f"Clés supprimées de _REASON_CODE_TO_CAUSE : {removed}"


def test_ac7_ambiguous_skipped_cause_code_unchanged():
    """AC7 (NFR8) : le cause_code de ambiguous_skipped reste 'ambiguous_skipped'."""
    cause_code, _, _ = reason_code_to_cause("ambiguous_skipped")
    assert cause_code == "ambiguous_skipped", (
        f"cause_code modifié : {cause_code!r}, attendu 'ambiguous_skipped'"
    )


def test_ac7_ha_component_not_in_product_scope_cause_code_unchanged():
    """AC7 (NFR8) : le cause_code de ha_component_not_in_product_scope reste 'not_in_product_scope'."""
    cause_code, _, _ = reason_code_to_cause("ha_component_not_in_product_scope")
    assert cause_code == "not_in_product_scope"


def test_ac7_fallback_still_returns_label_for_unknown_code():
    """AC7 : le fallback reste fonctionnel pour un reason_code inconnu."""
    result = resolve_cause_ux("__unknown__", 1)
    assert isinstance(result["cause_label"], str) and result["cause_label"]


# ==============================================================
# Contrat de sortie explicite (table de référence story 6.3)
# ==============================================================

def test_contract_ha_missing_command_topic():
    result = resolve_cause_ux("ha_missing_command_topic", 3)
    assert result["cause_label"] == "Projection HA incomplète — commande requise absente"
    assert result["cause_action"] is None


def test_contract_ha_missing_state_topic():
    result = resolve_cause_ux("ha_missing_state_topic", 3)
    assert result["cause_label"] == "Projection HA incomplète — état requis absent"
    assert result["cause_action"] is None


def test_contract_ha_missing_required_option():
    result = resolve_cause_ux("ha_missing_required_option", 3)
    assert result["cause_label"] == "Projection HA incomplète — champ obligatoire manquant"
    assert result["cause_action"] is None


def test_contract_ha_component_unknown_still_null_action():
    result = resolve_cause_ux("ha_component_unknown", 3)
    assert isinstance(result["cause_label"], str) and result["cause_label"]
    assert result["cause_action"] is None


def test_contract_ambiguous_skipped_step4_null_action():
    # Story 9.5 — renommé sémantiquement : cause_action est maintenant non-null (CTA réel vague 1)
    result = resolve_cause_ux("ambiguous_skipped", 4)
    assert result["cause_action"] is not None and len(result["cause_action"]) > 0


def test_contract_ha_component_not_in_product_scope_step4():
    result = resolve_cause_ux("ha_component_not_in_product_scope", 4)
    assert result["cause_action"] is None
    assert result["cause_label"].strip()
