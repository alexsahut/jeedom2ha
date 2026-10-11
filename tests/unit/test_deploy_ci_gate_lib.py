"""
test_deploy_ci_gate_lib.py — CC-50 : preuve unitaire, SANS réseau, du garde-fou
CI de scripts/deploy-to-box.sh (scripts/deploy-ci-gate-lib.sh).

`gh` est remplacé par une fonction shell qui répond depuis des fixtures JSON ;
les runs d'événement `schedule` doivent être ignorés.

Rejouer :
    pytest tests/unit/test_deploy_ci_gate_lib.py -v
"""
import json
import subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parents[2] / "scripts" / "deploy-ci-gate-lib.sh"
SHA = "abc123"


def _run(workflow_runs, check_runs, tmp_path, runs_pages=None):
    """runs_pages permet de simuler --paginate (plusieurs documents JSON
    concaténés)."""
    runs_file = tmp_path / "runs.json"
    checks_file = tmp_path / "checks.json"
    pages = runs_pages or [workflow_runs]
    runs_file.write_text("\n".join(json.dumps({"workflow_runs": p}) for p in pages))
    checks_file.write_text(json.dumps({"check_runs": check_runs}))
    mock = (
        'gh() { case "$*" in '
        f'*actions/runs?head_sha={SHA}*) cat "{runs_file}";; '
        f'*commits/{SHA}/check-runs*) cat "{checks_file}";; '
        '*) echo "unexpected gh call: $*" >&2; return 1;; esac; }; '
    )
    return subprocess.run(
        ["bash", "-c", f"set -euo pipefail; {mock}source '{LIB}'; "
                       f"jeedom2ha_verify_ci_green owner/repo {SHA}"],
        capture_output=True, text=True,
    )


def _run_ev(event, suite):
    return {"event": event, "check_suite_id": suite}


def _cr(suite, status="completed", conclusion="success"):
    return {"status": status, "conclusion": conclusion, "check_suite": {"id": suite}}


def test_failing_schedule_run_ignored_when_push_is_green(tmp_path):
    r = _run([_run_ev("schedule", 1), _run_ev("push", 2)],
             [_cr(1, conclusion="failure"), _cr(2), _cr(2, conclusion="skipped")], tmp_path)
    assert r.returncode == 0, r.stderr


def test_in_progress_schedule_check_ignored(tmp_path):
    r = _run([_run_ev("schedule", 1), _run_ev("pull_request", 2)],
             [_cr(1, "in_progress", None), _cr(2, conclusion="neutral")], tmp_path)
    assert r.returncode == 0, r.stderr


def test_only_relevant_run_failing_is_refused(tmp_path):
    r = _run([_run_ev("workflow_dispatch", 2), _run_ev("schedule", 1)],
             [_cr(1), _cr(2, conclusion="failure")], tmp_path)
    assert r.returncode == 1
    assert "CI non verte" in r.stderr


def test_relevant_check_in_progress_is_refused(tmp_path):
    r = _run([_run_ev("push", 2)], [_cr(2, "in_progress", None)], tmp_path)
    assert r.returncode == 1
    assert "non terminé" in r.stderr


def test_no_relevant_run_is_refused(tmp_path):
    r = _run([_run_ev("schedule", 1)], [_cr(1)], tmp_path)
    assert r.returncode == 1
    assert "aucun workflow run" in r.stderr


def test_no_workflow_run_at_all_is_refused(tmp_path):
    r = _run([], [_cr(1)], tmp_path)
    assert r.returncode == 1


def test_relevant_run_without_check_runs_is_refused(tmp_path):
    r = _run([_run_ev("push", 2)], [_cr(1)], tmp_path)
    assert r.returncode == 1
    assert "aucun check-run" in r.stderr


def test_other_events_are_not_retained(tmp_path):
    r = _run([_run_ev("workflow_run", 3)], [_cr(3)], tmp_path)
    assert r.returncode == 1


def test_check_run_without_check_suite_is_not_retained(tmp_path):
    r = _run([_run_ev("push", 2)], [{"status": "completed", "conclusion": "success"}], tmp_path)
    assert r.returncode == 1


def test_paginated_runs_are_all_considered(tmp_path):
    r = _run(None, [_cr(2, conclusion="failure")], tmp_path,
             runs_pages=[[_run_ev("schedule", 1)], [_run_ev("push", 2)]])
    assert r.returncode == 1
    assert "CI non verte" in r.stderr
