"""Story 3.2 — Tests unitaires du contenu enrichi de _DIAGNOSTIC_MESSAGES.

ACs couverts :
  AC 1 — Les reason_code non publiés ou ambigus ont un detail non-fallback
  AC 2 — Les limites Home Assistant sont explicitement libellées
  AC 3 — Le reason_code est déterministe

AI-3 — Synchronisation backend/frontend des reason_code gouvernés.
"""
import pytest

from models.taxonomy import REASON_CODE_TO_PRIMARY_STATUS
from transport.http_server import (
    _DIAGNOSTIC_MESSAGES,
    _DIAGNOSTIC_DEFAULT,
    _get_diagnostic_enrichment,
)


# ---------------------------------------------------------------------------
# AC 1 — Codes ajoutés Task 2 : detail non-vide et non-fallback
# ---------------------------------------------------------------------------


def test_probable_has_non_fallback_detail():
    """probable doit avoir un detail non-fallback dans _DIAGNOSTIC_MESSAGES (Task 2.1)."""
    detail, remediation, v1_limitation = _get_diagnostic_enrichment("probable")
    assert detail != _DIAGNOSTIC_DEFAULT[0], (
        f"probable retourne _DIAGNOSTIC_DEFAULT : '{detail}'"
    )
    assert detail != "", "probable a un detail vide dans _DIAGNOSTIC_MESSAGES."


def test_no_generic_type_configured_has_non_fallback_detail():
    """no_generic_type_configured doit avoir un detail non-fallback (Task 2.1)."""
    detail, remediation, v1_limitation = _get_diagnostic_enrichment("no_generic_type_configured")
    assert detail != _DIAGNOSTIC_DEFAULT[0], (
        f"no_generic_type_configured retourne _DIAGNOSTIC_DEFAULT : '{detail}'"
    )
    assert detail != "", "no_generic_type_configured a un detail vide."
    assert "Jeedom" in detail or "types génériques" in detail, (
        f"Le detail de no_generic_type_configured ne parle pas de types génériques : '{detail}'"
    )


def test_low_confidence_has_non_fallback_detail():
    """low_confidence doit avoir un detail non-fallback (Task 2.1)."""
    detail, remediation, v1_limitation = _get_diagnostic_enrichment("low_confidence")
    assert detail != _DIAGNOSTIC_DEFAULT[0], (
        f"low_confidence retourne _DIAGNOSTIC_DEFAULT : '{detail}'"
    )
    assert detail != "", "low_confidence a un detail vide."
    assert "Home Assistant" in detail or "correspondance" in detail, (
        f"Le detail de low_confidence ne parle pas de correspondance ou de HA : '{detail}'"
    )


def test_no_generic_type_configured_has_remediation():
    """no_generic_type_configured doit avoir une remediation non-vide (AC 1)."""
    detail, remediation, v1_limitation = _get_diagnostic_enrichment("no_generic_type_configured")
    assert remediation != "", "no_generic_type_configured doit avoir une remediation."


def test_low_confidence_has_remediation():
    """low_confidence doit avoir une remediation non-vide (AC 1)."""
    detail, remediation, v1_limitation = _get_diagnostic_enrichment("low_confidence")
    assert remediation != "", "low_confidence doit avoir une remediation."


# ---------------------------------------------------------------------------
# AC 2 — Codes v1_limitation=True : mention explicite de Home Assistant
# ---------------------------------------------------------------------------


def test_no_supported_generic_type_detail_mentions_home_assistant():
    """no_supported_generic_type.detail doit mentionner 'Home Assistant' (Task 3.1, AC 2)."""
    detail, remediation, v1_limitation = _get_diagnostic_enrichment("no_supported_generic_type")
    assert v1_limitation is True, "no_supported_generic_type doit avoir v1_limitation=True."
    assert "Home Assistant" in detail, (
        f"no_supported_generic_type.detail ne mentionne pas 'Home Assistant' : '{detail}'"
    )


def test_no_mapping_detail_mentions_home_assistant():
    """no_mapping.detail doit mentionner 'Home Assistant' (AC 2 — déjà sain, vérification)."""
    detail, remediation, v1_limitation = _get_diagnostic_enrichment("no_mapping")
    assert v1_limitation is True, "no_mapping doit avoir v1_limitation=True."
    assert "Home Assistant" in detail, (
        f"no_mapping.detail ne mentionne pas 'Home Assistant' : '{detail}'"
    )


@pytest.mark.parametrize("reason_code", [
    rc for rc, _ in REASON_CODE_TO_PRIMARY_STATUS.items()
    if rc in _DIAGNOSTIC_MESSAGES and _DIAGNOSTIC_MESSAGES[rc][2] is True
])
def test_all_v1_limitation_codes_mention_home_assistant(reason_code):
    """Tous les codes v1_limitation=True doivent mentionner 'Home Assistant' dans le detail (AC 2)."""
    detail, remediation, v1_limitation = _DIAGNOSTIC_MESSAGES[reason_code]
    assert "home assistant" in detail.lower(), (
        f"'{reason_code}' a v1_limitation=True mais son detail ne mentionne pas 'Home Assistant' : '{detail}'"
    )


# ---------------------------------------------------------------------------
# AC 3 — Déterminisme du reason_code et du detail
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason_code", [
    "ambiguous_skipped",
    "discovery_publish_failed",
    "no_supported_generic_type",
    "no_generic_type_configured",
    "low_confidence",
    "probable",
    "no_mapping",
])
def test_diagnostic_enrichment_is_deterministic(reason_code):
    """Deux appels _get_diagnostic_enrichment(code) produisent le même résultat (AC 3)."""
    result1 = _get_diagnostic_enrichment(reason_code)
    result2 = _get_diagnostic_enrichment(reason_code)
    assert result1 == result2, (
        f"_get_diagnostic_enrichment('{reason_code}') produit des résultats différents : "
        f"{result1} vs {result2}"
    )


def test_ambiguous_skipped_deterministic():
    """Stabilité spécifique pour ambiguous_skipped (Task 7.4, AC 3)."""
    r1 = _get_diagnostic_enrichment("ambiguous_skipped")
    r2 = _get_diagnostic_enrichment("ambiguous_skipped")
    assert r1 == r2


def test_discovery_publish_failed_deterministic():
    """Stabilité spécifique pour discovery_publish_failed (Task 7.5, AC 3)."""
    r1 = _get_diagnostic_enrichment("discovery_publish_failed")
    r2 = _get_diagnostic_enrichment("discovery_publish_failed")
    assert r1 == r2


# ---------------------------------------------------------------------------
# Audit Task 1.3 — sure_mapping : code fantôme documenté, pas supprimé
# ---------------------------------------------------------------------------


def test_sure_mapping_not_in_taxonomy():
    """sure_mapping n'est pas dans REASON_CODE_TO_PRIMARY_STATUS (code fantôme — Task 1.3).

    Ce test documente que sure_mapping n'est pas un code taxonomique officiel.
    Sa présence dans _DIAGNOSTIC_MESSAGES est intentionnelle (legacy safety net).
    """
    assert "sure_mapping" not in REASON_CODE_TO_PRIMARY_STATUS, (
        "sure_mapping ne doit pas être dans REASON_CODE_TO_PRIMARY_STATUS. "
        "Si ce code a été promu, créer une story dédiée."
    )
    # Sa présence dans _DIAGNOSTIC_MESSAGES est acceptable (safety net legacy)
    assert "sure_mapping" in _DIAGNOSTIC_MESSAGES, (
        "sure_mapping doit rester dans _DIAGNOSTIC_MESSAGES comme safety net legacy. "
        "Ne pas le supprimer sans vérification complète des émetteurs."
    )


# ---------------------------------------------------------------------------
# Audit Task 1.4 — eligible : non-terminal documenté
# ---------------------------------------------------------------------------


def test_eligible_not_in_taxonomy():
    """eligible n'est pas dans REASON_CODE_TO_PRIMARY_STATUS (non-terminal — Task 1.4).

    Ce test documente que eligible est un code intermédiaire non-terminal.
    Sa présence dans _DIAGNOSTIC_MESSAGES est inoffensive.
    """
    assert "eligible" not in REASON_CODE_TO_PRIMARY_STATUS, (
        "eligible ne doit pas être dans REASON_CODE_TO_PRIMARY_STATUS. "
        "C'est un code non-terminal intermédiaire (documenté Story 3.1)."
    )


# ---------------------------------------------------------------------------
# AI-3 — Cohérence globale : aucun code de la taxonomie ne retourne _DIAGNOSTIC_DEFAULT
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason_code,primary_status", [
    (rc, ps) for rc, ps in REASON_CODE_TO_PRIMARY_STATUS.items()
    if ps != "published"
])
def test_non_published_codes_have_non_empty_detail(reason_code, primary_status):
    """Les codes non-published doivent avoir un detail non-vide et non-fallback (AC 1).

    Note: published codes (sure, probable) ont detail="" dans l'endpoint
    mais sont couverts par test_reason_code_does_not_return_default_fallback.
    """
    detail, remediation, v1_limitation = _get_diagnostic_enrichment(reason_code)
    assert detail != _DIAGNOSTIC_DEFAULT[0], (
        f"'{reason_code}' (primary_status={primary_status}) retourne _DIAGNOSTIC_DEFAULT."
    )
    assert detail != "", (
        f"'{reason_code}' (primary_status={primary_status}) retourne un detail vide. "
        f"Un code non-published doit avoir une raison lisible."
    )
