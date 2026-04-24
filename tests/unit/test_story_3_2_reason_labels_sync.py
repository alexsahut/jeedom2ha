"""Story 6.2 — Guardrail frontend backend-first.

Le diagnostic ne doit plus maintenir de mapping local reason_code -> libellé.
La surface lit exclusivement cause_label/cause_action fournis par le backend.
"""

from pathlib import Path


_JS_FILE = Path(__file__).parents[2] / "desktop" / "js" / "jeedom2ha.js"


def test_no_reason_labels_mapping_in_diagnostic_js():
    source = _JS_FILE.read_text(encoding="utf-8")
    assert "reasonLabels" not in source, (
        "Le diagnostic frontend ne doit plus contenir de table locale reason_code -> libellé."
    )


def test_diagnostic_reads_backend_cause_fields():
    source = _JS_FILE.read_text(encoding="utf-8")
    assert "eq.cause_label" in source
    assert "eq.cause_action" in source
