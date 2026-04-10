# AI-3 guard layer 3 — Story 3.2. Complétude _DIAGNOSTIC_MESSAGES. Ne pas affaiblir ni supprimer. Permanent Epic 3+.
"""Story 3.2 — Garde-fou AI-3 couche 3 : complétude de _DIAGNOSTIC_MESSAGES.

AC 4 — Les gardes-fous AI-3 couches 3 et 4 sont opérationnels.
AI-3 — Synchronisation backend/frontend des reason_code gouvernés.
AI-7 — Vérification intégrée à la code review.

Ce test vérifie :
  1. Chaque code de REASON_CODE_TO_PRIMARY_STATUS a une entrée dans _DIAGNOSTIC_MESSAGES.
  2. Pour chaque code, _get_diagnostic_enrichment(code)[0] ne vaut pas _DIAGNOSTIC_DEFAULT[0].
  3. Les codes avec v1_limitation=True contiennent "Home Assistant" dans leur detail.

Ne pas affaiblir ni supprimer ce test. Permanent pour Epic 3+.
"""
import pytest

from models.taxonomy import REASON_CODE_TO_PRIMARY_STATUS
from transport.http_server import (
    _DIAGNOSTIC_MESSAGES,
    _DIAGNOSTIC_DEFAULT,
    _get_diagnostic_enrichment,
)


# ---------------------------------------------------------------------------
# Couche 3.1 — Chaque code du mapping a une entrée dans _DIAGNOSTIC_MESSAGES
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason_code", list(REASON_CODE_TO_PRIMARY_STATUS.keys()))
def test_reason_code_has_diagnostic_message_entry(reason_code):
    """Chaque code de REASON_CODE_TO_PRIMARY_STATUS doit avoir une clé dans _DIAGNOSTIC_MESSAGES.

    Échec → ajouter l'entrée manquante dans _DIAGNOSTIC_MESSAGES (http_server.py).
    """
    assert reason_code in _DIAGNOSTIC_MESSAGES, (
        f"Le reason_code '{reason_code}' est absent de _DIAGNOSTIC_MESSAGES. "
        f"Il retomberait sur _DIAGNOSTIC_DEFAULT ('Cause inconnue.'). "
        f"Ajouter une entrée dans http_server.py."
    )


# ---------------------------------------------------------------------------
# Couche 3.2 — Aucun code du mapping ne retourne _DIAGNOSTIC_DEFAULT
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason_code", list(REASON_CODE_TO_PRIMARY_STATUS.keys()))
def test_reason_code_does_not_return_default_fallback(reason_code):
    """_get_diagnostic_enrichment(code)[0] ne doit pas valoir 'Cause inconnue.' pour un code gouverné.

    Échec → le code retombe sur le fallback générique, inacceptable pour un cas nominal.
    """
    detail, remediation, v1_limitation = _get_diagnostic_enrichment(reason_code)
    assert detail != _DIAGNOSTIC_DEFAULT[0], (
        f"Le reason_code '{reason_code}' retourne le fallback _DIAGNOSTIC_DEFAULT "
        f"('{_DIAGNOSTIC_DEFAULT[0]}'). "
        f"Ce code doit avoir une entrée dédiée dans _DIAGNOSTIC_MESSAGES."
    )
    assert detail != "", (
        f"Le reason_code '{reason_code}' retourne un detail vide depuis _DIAGNOSTIC_MESSAGES. "
        f"Le detail doit être non-vide pour un code gouverné hors 'published'."
    )


# ---------------------------------------------------------------------------
# Couche 3.3 — Les codes v1_limitation=True mentionnent "Home Assistant"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason_code", list(REASON_CODE_TO_PRIMARY_STATUS.keys()))
def test_v1_limitation_codes_mention_home_assistant(reason_code):
    """Si _DIAGNOSTIC_MESSAGES[code][2] est True (v1_limitation), le detail doit contenir 'Home Assistant'.

    Échec → mettre à jour le detail pour mention HA explicite (AC 2, AI-3).
    """
    if reason_code not in _DIAGNOSTIC_MESSAGES:
        pytest.skip(f"'{reason_code}' absent de _DIAGNOSTIC_MESSAGES (géré par autre test).")

    detail, remediation, v1_limitation = _DIAGNOSTIC_MESSAGES[reason_code]
    if v1_limitation:
        assert "home assistant" in detail.lower(), (
            f"Le reason_code '{reason_code}' a v1_limitation=True mais son detail "
            f"ne mentionne pas 'Home Assistant' : '{detail}'"
        )
