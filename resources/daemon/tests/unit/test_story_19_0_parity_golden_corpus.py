"""Story 19.0 — Task 4 : harnais de parité sur le corpus doré (AC3).

Exécute `evaluate_equipment()` (overrides persistés seuls, sans override
"proposé"/preview) et le pipeline classique (`decide_publication()` appelé
directement) sur le même corpus doré (`fixtures/golden_corpus/sync_payload.json`,
59 eqLogics couvrant lights/covers/switches/ambiguous/ineligible/blocked/
sensors/binary_sensors) et vérifie qu'aucun écart n'apparaît.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# NOTE : le paquet racine `tests/` (rootdir) et `resources/daemon/tests/` portent
# le même nom `tests`, ce qui rend `tests.tools...` ambigu selon l'ordre de
# résolution de `pythonpath`. On importe donc le harnais par chemin direct
# plutôt que via un import de paquet, pour rester indépendant de cet ordre.
_TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from parity_harness_19_0 import compute_parity_report  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus"
SYNC_FIXTURE_PATH = FIXTURES_DIR / "sync_payload.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ac3_parity_harness_golden_corpus_no_discrepancy():
    payload = _load_json(SYNC_FIXTURE_PATH)

    discrepancies = compute_parity_report(payload)

    assert discrepancies == [], (
        "Écart(s) détecté(s) entre evaluate_equipment() et le pipeline classique "
        f"sur le corpus doré : {discrepancies}"
    )


def test_ac3_parity_harness_golden_corpus_covers_eligible_equipments():
    """Garde-fou : le harnais doit réellement comparer un nombre significatif
    d'équipements (sinon un test qui "passe" pourrait masquer un corpus vide
    ou une éligibilité cassée en amont)."""
    payload = _load_json(SYNC_FIXTURE_PATH)

    from models.topology import TopologySnapshot, assess_all

    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    eligibility = assess_all(snapshot)
    eligible_count = sum(1 for res in eligibility.values() if res.is_eligible)

    assert eligible_count > 10, (
        f"Corpus doré : seulement {eligible_count} équipement(s) éligible(s), "
        "harnais de parité insuffisamment représentatif"
    )
