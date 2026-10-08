"""Story 3.1 — Garde-fou de la taxonomie des statuts primaires.

Story 20.3 : le tableau de diagnostic (modale « Diagnostic de Couverture », fonction JS
`getStatusLabel`) est supprimé de l'interface au profit de la surface pièce -> équipement
-> commande. La synchronisation « label de taxonomy.py présent dans getStatusLabel » n'a donc
plus de consommateur frontend à garder ; les contrôles liés au fichier JS sont retirés.
Le garde-fou de dérive côté démon (taxonomie fermée à 5 statuts) est conservé : le démon
continue d'exposer ces statuts dans l'export « diagnostic support ».
"""
import pathlib

from models.taxonomy import PRIMARY_STATUSES


_JS_FILE = pathlib.Path(__file__).parents[2] / "desktop" / "js" / "jeedom2ha.js"


def test_primary_statuses_count_five():
    """PRIMARY_STATUSES doit contenir exactement 5 entrées (taxonomie fermée Story 3.1)."""
    assert len(PRIMARY_STATUSES) == 5, (
        f"PRIMARY_STATUSES contient {len(PRIMARY_STATUSES)} entrées au lieu de 5. "
        f"Si un statut a été ajouté, une story dédiée est requise."
    )


def test_ui_ne_porte_plus_de_table_de_labels_de_statut():
    """Story 20.3 : l'interface n'embarque plus de traduction locale des statuts (aucune dérive possible)."""
    assert "getStatusLabel" not in _JS_FILE.read_text(encoding="utf-8")
