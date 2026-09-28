"""Story 19.2 — P2 (revue ClaudeBox, commit 3a408db) : `GET
/system/state_listeners` est la seule preuve terrain qui distingue réellement
l'avant de l'après un déploiement I11 — `state_topics`/`publish_initial_states`
ne filtrent pas sur le principal et publient déjà l'état des secondaires I11
en retained sur `main` (avant tout déploiement de la correction).

Ces tests couvrent le câblage de `tools/parity_snapshot.py` : capture
systématique du champ `state_listeners`, extension du diff
(`listeners_added`/`listeners_removed`) sans jamais influencer
`is_empty_diff` (qui reste la parité Story 19.1, décisions + topics
discovery), et compatibilité ascendante avec un relevé pré-P2 sans le champ.
"""

from __future__ import annotations

import pytest

from tools import parity_snapshot as pt


SECRET = "super-secret-value-should-never-leak"


def _diagnostics_payload(equipments):
    return {
        "action": "system.diagnostics",
        "status": "ok",
        "payload": {"equipments": equipments},
    }


def _eq(eq_id, *, reason_code="sure", statut="publie"):
    return {
        "eq_id": eq_id,
        "name": f"Eq {eq_id}",
        "status_code": "published" if statut == "publie" else "not_published",
        "reason_code": reason_code,
        "perimetre": "inclus",
        "statut": statut,
        "matched_commands": [],
        "unmatched_commands": [],
    }


def _fake_runner(stdout: str = "", returncode: int = 0):
    from unittest.mock import MagicMock

    def _run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = stdout
        result.stderr = ""
        result.returncode = returncode
        return result

    return _run


def test_fetch_state_listeners_uses_same_header_mechanism_as_diagnostics():
    """AC5 (même garantie que fetch_diagnostics) : le secret ne transite que
    par l'en-tête HTTP, jamais par l'URL."""
    import inspect

    source = inspect.getsource(pt.fetch_state_listeners)
    assert 'headers={"X-Local-Secret": local_secret}' in source
    assert "/system/state_listeners" in source


def test_capture_snapshot_captures_state_listeners(monkeypatch):
    """Capture avec écouteurs : le champ state_listeners est peuplé, trié par
    (eq_id, cmd_id), à partir de /system/state_listeners."""
    monkeypatch.setattr(
        pt, "fetch_diagnostics", lambda *a, **k: _diagnostics_payload([_eq(1)]),
    )
    monkeypatch.setattr(pt, "fetch_published_scope", lambda *a, **k: {"payload": {}})
    monkeypatch.setattr(
        pt, "fetch_state_listeners",
        lambda *a, **k: {
            "status": "ok",
            "listeners": [
                {"eq_id": 585, "cmd_id": 5546, "ha_type": "sensor", "state_topic": "jeedom2ha/585/5546/state"},
                {"eq_id": 579, "cmd_id": 5369, "ha_type": "sensor", "state_topic": "jeedom2ha/579/5369/state"},
            ],
        },
    )

    snapshot = pt.capture_snapshot(
        base_url="http://x", local_secret=SECRET,
        mqtt_host="x", mqtt_port=1883, label="before",
        mqtt_runner=_fake_runner(stdout="homeassistant/light/jeedom2ha_1/config\n"),
    )

    assert snapshot.state_listeners == [
        {"eq_id": 579, "cmd_id": 5369},
        {"eq_id": 585, "cmd_id": 5546},
    ]
    assert snapshot.to_dict()["state_listeners"] == snapshot.state_listeners


def test_capture_snapshot_state_listeners_empty_is_not_a_failure(monkeypatch):
    """Contrairement aux décisions/topics discovery (AC3), une liste
    d'écouteurs vide (vague 1 pas encore publiée) n'est jamais un échec."""
    monkeypatch.setattr(
        pt, "fetch_diagnostics", lambda *a, **k: _diagnostics_payload([_eq(1)]),
    )
    monkeypatch.setattr(pt, "fetch_published_scope", lambda *a, **k: {"payload": {}})
    monkeypatch.setattr(pt, "fetch_state_listeners", lambda *a, **k: {"status": "ok", "listeners": []})

    snapshot = pt.capture_snapshot(
        base_url="http://x", local_secret=SECRET,
        mqtt_host="x", mqtt_port=1883, label="before",
        mqtt_runner=_fake_runner(stdout="homeassistant/light/jeedom2ha_1/config\n"),
    )

    assert snapshot.state_listeners == []


def test_diff_snapshots_reports_listeners_added(monkeypatch):
    """Diff avec écouteurs ajoutés : les 12 cmd_ids d'un déploiement I11
    (modèle eq 579/585) doivent apparaître dans listeners_added, sans
    influencer is_empty_diff (qui reste la parité Story 19.1)."""
    common = {
        "decisions": [{"eq_id": 1, "reason_code": "sure", "statut": "publie"}],
        "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
    }
    before = {**common, "state_listeners": [{"eq_id": 579, "cmd_id": 5369}]}
    after = {
        **common,
        "state_listeners": [
            {"eq_id": 579, "cmd_id": 5369},
            {"eq_id": 579, "cmd_id": 5493},
            {"eq_id": 585, "cmd_id": 5497},
        ],
    }

    result = pt.diff_snapshots(before, after)

    assert result["listeners_added"] == [
        {"eq_id": 579, "cmd_id": 5493},
        {"eq_id": 585, "cmd_id": 5497},
    ]
    assert result["listeners_removed"] == []
    assert result["is_empty_diff"] is True


def test_diff_snapshots_reports_listeners_removed():
    common = {
        "decisions": [{"eq_id": 1, "reason_code": "sure", "statut": "publie"}],
        "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
    }
    before = {**common, "state_listeners": [{"eq_id": 553, "cmd_id": 5137}]}
    after = {**common, "state_listeners": []}

    result = pt.diff_snapshots(before, after)

    assert result["listeners_added"] == []
    assert result["listeners_removed"] == [{"eq_id": 553, "cmd_id": 5137}]
    assert result["is_empty_diff"] is True


def test_diff_snapshots_old_report_without_state_listeners_field_stays_comparable():
    """Un relevé capturé AVANT ce champ (pré-P2) ne doit jamais faire
    échouer le diff — absence traitée comme une liste vide, jamais une
    KeyError."""
    before = {
        "decisions": [{"eq_id": 1, "reason_code": "sure", "statut": "publie"}],
        "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
    }
    after = {
        "decisions": [{"eq_id": 1, "reason_code": "sure", "statut": "publie"}],
        "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
        "state_listeners": [{"eq_id": 579, "cmd_id": 5369}],
    }

    result = pt.diff_snapshots(before, after)

    assert result["listeners_added"] == [{"eq_id": 579, "cmd_id": 5369}]
    assert result["listeners_removed"] == []
    assert result["is_empty_diff"] is True


def test_diff_snapshots_is_empty_diff_not_influenced_by_listeners_when_decisions_differ():
    """is_empty_diff reste calculé UNIQUEMENT sur décisions + topics
    discovery (parité Story 19.1) : un changement d'écouteurs seul ne doit
    jamais, à l'inverse, masquer une vraie régression de décision."""
    before = {
        "decisions": [{"eq_id": 1, "reason_code": "sure", "statut": "publie"}],
        "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
        "state_listeners": [{"eq_id": 579, "cmd_id": 5369}],
    }
    after = {
        "decisions": [{"eq_id": 1, "reason_code": "no_mapping", "statut": "non_publie"}],
        "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
        "state_listeners": [{"eq_id": 579, "cmd_id": 5369}],
    }

    result = pt.diff_snapshots(before, after)

    assert result["listeners_added"] == []
    assert result["listeners_removed"] == []
    assert result["is_empty_diff"] is False


def test_snapshot_to_dict_includes_state_listeners_key():
    snapshot = pt.ParitySnapshot(
        captured_at="2026-09-28T00:00:00Z", label="before",
        decisions=[], mqtt_topics=[], state_listeners=[{"eq_id": 1, "cmd_id": 2}],
    )
    assert snapshot.to_dict()["state_listeners"] == [{"eq_id": 1, "cmd_id": 2}]
