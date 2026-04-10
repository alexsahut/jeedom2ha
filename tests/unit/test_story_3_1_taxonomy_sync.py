"""Story 3.1 — Test de synchronisation contrat backend/frontend.

AI-3 guard — Story 3.1. Ce test cible le bloc getStatusLabel. Ne pas affaiblir en testant le fichier entier.
Permanent pour Epic 3+.

Ce test valide que chaque label français de PRIMARY_STATUSES est présent
dans la *fonction* getStatusLabel de jeedom2ha.js — pas dans le fichier entier.
Dérive détectée : label ajouté à taxonomy.py sans mise à jour de getStatusLabel.
"""
import re
import pathlib

import pytest

from models.taxonomy import PRIMARY_STATUSES


_JS_FILE = pathlib.Path(__file__).parents[2] / "desktop" / "js" / "jeedom2ha.js"

# Regex pour extraire le bloc complet de getStatusLabel (fermeture sur };)
_GETSTATUS_PATTERN = re.compile(
    r"var getStatusLabel\s*=\s*function\b.*?};",
    re.DOTALL,
)


@pytest.fixture(scope="module")
def js_content():
    return _JS_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def getstatus_block(js_content):
    m = _GETSTATUS_PATTERN.search(js_content)
    assert m is not None, (
        "getStatusLabel introuvable dans jeedom2ha.js — "
        "le fichier n'expose plus la fonction attendue, ou le pattern a changé."
    )
    return m.group(0)


# ------------------------------------------------------------
# 1. Le bloc getStatusLabel est extractible
# ------------------------------------------------------------

def test_getstatus_block_found(getstatus_block):
    """Le bloc getStatusLabel doit être localisable via regex dans jeedom2ha.js."""
    assert len(getstatus_block) > 0


# ------------------------------------------------------------
# 2. Chaque label français de PRIMARY_STATUSES est dans le bloc
# ------------------------------------------------------------

@pytest.mark.parametrize("code,label", PRIMARY_STATUSES.items())
def test_label_present_in_getstatus_block(code, label, getstatus_block):
    """Chaque label français de taxonomy.PRIMARY_STATUSES doit apparaître dans le bloc getStatusLabel."""
    assert label in getstatus_block, (
        f"Le label '{label}' (code '{code}') est absent du bloc getStatusLabel. "
        f"Mettre à jour getStatusLabel dans jeedom2ha.js."
    )


# ------------------------------------------------------------
# 3. Les anciens statuts ne sont pas des cas nominaux dans le bloc
# ------------------------------------------------------------

def test_ancien_statut_partiel_absent_nominal(getstatus_block):
    """'Partiellement publié' ne doit pas apparaître comme cas nominal dans getStatusLabel."""
    # Un cas nominal serait un if/return pour ce statut. On cherche la chaîne dans une condition.
    # On accepte qu'elle soit absente (idéal) ou uniquement en commentaire.
    nominal_pattern = re.compile(r"(?:===|==)\s*['\"]Partiellement publié['\"]")
    assert not nominal_pattern.search(getstatus_block), (
        "'Partiellement publié' est encore un cas nominal (if/===) dans getStatusLabel. "
        "Ce statut doit être supprimé après Story 3.1."
    )


def test_ancien_statut_non_publie_absent_nominal(getstatus_block):
    """'Non publié' ne doit pas apparaître comme cas nominal dans getStatusLabel."""
    nominal_pattern = re.compile(r"(?:===|==)\s*['\"]Non publié['\"]")
    assert not nominal_pattern.search(getstatus_block), (
        "'Non publié' est encore un cas nominal (if/===) dans getStatusLabel. "
        "Ce statut doit être supprimé après Story 3.1."
    )


# ------------------------------------------------------------
# 4. Nombre de statuts dans la taxonomie = 5 (garde-fou de dérive)
# ------------------------------------------------------------

def test_primary_statuses_count_five():
    """PRIMARY_STATUSES doit contenir exactement 5 entrées (taxonomie fermée Story 3.1)."""
    assert len(PRIMARY_STATUSES) == 5, (
        f"PRIMARY_STATUSES contient {len(PRIMARY_STATUSES)} entrées au lieu de 5. "
        f"Si un statut a été ajouté, une story dédiée est requise."
    )
