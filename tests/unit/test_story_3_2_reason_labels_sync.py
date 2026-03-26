# AI-3 guard layer 4 — Story 3.2. Complétude reasonLabels JS. Ne pas affaiblir ni supprimer. Permanent Epic 3+.
"""Story 3.2 — Garde-fou AI-3 couche 4 : complétude du bloc reasonLabels dans jeedom2ha.js.

AC 4 — Les gardes-fous AI-3 couches 3 et 4 sont opérationnels.
AI-3 — Synchronisation backend/frontend des reason_code gouvernés.
AI-7 — Vérification intégrée à la code review.

Ce test vérifie :
  1. Le bloc reasonLabels est extractible depuis jeedom2ha.js via regex.
  2. Chaque code de REASON_CODE_TO_PRIMARY_STATUS a une clé dans ce bloc.

Ne pas affaiblir ni supprimer ce test. Permanent pour Epic 3+.
"""
import re
import pathlib

import pytest

from models.taxonomy import REASON_CODE_TO_PRIMARY_STATUS


_JS_FILE = pathlib.Path(__file__).parents[2] / "desktop" / "js" / "jeedom2ha.js"

# Regex pour extraire le bloc reasonLabels (var/let/const, DOTALL pour multilignes)
_REASON_LABELS_PATTERN = re.compile(
    r"(?:var|let|const)\s+reasonLabels\s*=\s*\{.*?\};",
    re.DOTALL,
)


@pytest.fixture(scope="module")
def js_content():
    return _JS_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def reason_labels_block(js_content):
    """Extrait le bloc reasonLabels depuis jeedom2ha.js.

    Échec ici → le bloc n'est plus localisable, vérifier la structure du fichier JS.
    """
    m = _REASON_LABELS_PATTERN.search(js_content)
    if not m:
        raise AssertionError(
            "reasonLabels introuvable dans jeedom2ha.js. "
            "Le bloc doit être déclaré avec var/let/const reasonLabels = {...};"
        )
    return m.group(0)


# ---------------------------------------------------------------------------
# Couche 4.1 — Le bloc reasonLabels est extractible
# ---------------------------------------------------------------------------


def test_reason_labels_block_found(reason_labels_block):
    """Le bloc reasonLabels doit être localisable via regex dans jeedom2ha.js."""
    assert len(reason_labels_block) > 0


# ---------------------------------------------------------------------------
# Couche 4.2 — Chaque code du mapping a un label dans le bloc
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason_code", list(REASON_CODE_TO_PRIMARY_STATUS.keys()))
def test_reason_code_has_label_in_js(reason_code, reason_labels_block):
    """Chaque code de REASON_CODE_TO_PRIMARY_STATUS doit avoir une clé dans le bloc reasonLabels.

    Échec → ajouter l'entrée manquante dans le bloc reasonLabels de jeedom2ha.js.
    """
    # On cherche la clé sous forme 'code' ou "code" dans le bloc JS
    pattern = re.compile(r"""['"]""" + re.escape(reason_code) + r"""['"]""")
    assert pattern.search(reason_labels_block), (
        f"Le reason_code '{reason_code}' est absent du bloc reasonLabels dans jeedom2ha.js. "
        f"Ajouter une entrée dans le bloc reasonLabels."
    )
