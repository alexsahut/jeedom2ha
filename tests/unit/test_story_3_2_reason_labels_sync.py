"""Story 3.2 / 6.2 — Garde-fou de synchronisation backend/frontend des libellés de raison.

Story 20.3 (R1-G) : la modale Diagnostic (eq.cause_label / eq.cause_action) et le garde-fou sur
jeedom2ha.js n'ont plus d'objet. Ce test est recentré sur la table de libellés de la surface
(REASON_LABELS dans desktop/js/jeedom2ha_mapping_override.js) : chaque raison de décision par
commande que `evaluate_equipment()` peut produire sans publier doit y avoir un libellé français,
sinon la surface afficherait un code brut ou rien.
"""

import re
from pathlib import Path

from models import evaluate_equipment as ee

_ROOT = Path(__file__).parents[2]
_OVERRIDE_JS = _ROOT / "desktop" / "js" / "jeedom2ha_mapping_override.js"
_HOME_JS = _ROOT / "desktop" / "js" / "jeedom2ha.js"

# Raisons nominales : la commande est publiée, la surface n'affiche aucune cause de blocage.
_NOMINAL_REASONS = frozenset({"sure", "probable"})


def _js_reason_labels() -> set:
    source = _OVERRIDE_JS.read_text(encoding="utf-8")
    block = source[source.index("var REASON_LABELS = {"):]
    block = block[:block.index("};")]
    return set(re.findall(r"^\s+([a-z_0-9]+):", block, re.M))


def test_every_non_nominal_decision_reason_has_a_surface_label():
    emitted = (
        set(ee._STEP2_REASONS)
        | set(ee._STEP2B_REASONS)
        | set(ee._STEP4_REASONS)
        | {ee._COMMAND_NOT_COVERED_REASON}
    ) - _NOMINAL_REASONS
    missing = sorted(emitted - _js_reason_labels())
    assert not missing, (
        f"Raisons de décision sans libellé dans REASON_LABELS (mapping_override.js) : {missing}"
    )


def test_no_reason_labels_mapping_in_page_js():
    source = _HOME_JS.read_text(encoding="utf-8")
    assert "reasonLabels" not in source, (
        "La page ne doit pas maintenir de table locale reason_code -> libellé."
    )
