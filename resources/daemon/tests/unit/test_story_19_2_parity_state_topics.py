"""Story 19.2 — extension en LECTURE SEULE de `tools/parity_snapshot.py` :
preuve terrain complémentaire pour l'invariant I11 (Task "Préparation de la
preuve terrain"), jamais exécutée contre la box réelle dans ces tests.

L'outil (Story 19.1) détecte déjà des candidats I11 par corrélation avec
l'inventaire MQTT discovery retained (heuristique documentée, non modifiée
ici). Cette extension ajoute une VÉRIFICATION supplémentaire, opt-in via
`--mqtt-state-inventory-file`/`mqtt_state_inventory_file` : pour chaque
candidat I11 déjà détecté, le topic d'état retenu correspondant
(`jeedom2ha/<eq_id>/<cmd_id>/state`) est-il bien présent dans un second
inventaire MQTT (retained state topics, `jeedom2ha/+/+/state`) ?

Sans cette option, le format et le comportement restent strictement
identiques à Story 19.1 (couvert par
`test_story_19_1_parity_tool_readonly.py`, non modifié).
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


# ---------------------------------------------------------------------------
# _detect_i11_state_coverage — fonction pure
# ---------------------------------------------------------------------------

def test_state_coverage_marks_present_when_state_topic_retained():
    candidates = [{
        "eq_id": 579,
        "primary_reason_code": "no_mapping",
        "matching_topics": ["homeassistant/sensor/jeedom2ha_579_5369/config"],
    }]
    state_topics = ["jeedom2ha/579/5369/state"]

    augmented = pt._detect_i11_state_coverage(candidates, state_topics)

    assert len(augmented) == 1
    assert augmented[0]["eq_id"] == 579
    assert augmented[0]["secondary_cmd_ids"] == [5369]
    assert augmented[0]["state_topics_present"] == [5369]
    assert augmented[0]["state_topics_missing"] == []
    # Le candidat original (Story 19.1) reste intact, seulement complété.
    assert augmented[0]["matching_topics"] == candidates[0]["matching_topics"]


def test_state_coverage_marks_missing_when_state_topic_absent():
    """C'est exactement le cas que la correction I11 (sync/state.py,
    sync/command.py) est censée éliminer : un secondaire publié (topic
    discovery présent) mais SANS état streamé (topic state absent)."""
    candidates = [{
        "eq_id": 42,
        "primary_reason_code": "no_mapping",
        "matching_topics": ["homeassistant/sensor/jeedom2ha_42_3/config"],
    }]

    augmented = pt._detect_i11_state_coverage(candidates, state_topics=[])

    assert augmented[0]["secondary_cmd_ids"] == [3]
    assert augmented[0]["state_topics_present"] == []
    assert augmented[0]["state_topics_missing"] == [3]


def test_state_coverage_handles_multiple_secondaries_per_candidate():
    candidates = [{
        "eq_id": 585,
        "primary_reason_code": "no_mapping",
        "matching_topics": [
            "homeassistant/sensor/jeedom2ha_585_5497/config",
            "homeassistant/sensor/jeedom2ha_585_5504/config",
        ],
    }]
    state_topics = ["jeedom2ha/585/5497/state"]  # 5504 manquant

    augmented = pt._detect_i11_state_coverage(candidates, state_topics)

    assert augmented[0]["secondary_cmd_ids"] == [5497, 5504]
    assert augmented[0]["state_topics_present"] == [5497]
    assert augmented[0]["state_topics_missing"] == [5504]


def test_state_coverage_ignores_stale_primary_topic_without_cmd_id():
    """Même garde-fou que Finding 3 (PR #169, Story 19.1) : un topic discovery
    égal exactement au node_id primaire (sans suffixe `_<cmd_id>`) ne doit
    jamais produire de faux cmd_id de secondaire."""
    candidates = [{
        "eq_id": 42,
        "primary_reason_code": "no_mapping",
        "matching_topics": ["homeassistant/light/jeedom2ha_42/config"],
    }]

    augmented = pt._detect_i11_state_coverage(candidates, state_topics=[])

    assert augmented[0]["secondary_cmd_ids"] == []
    assert augmented[0]["state_topics_present"] == []
    assert augmented[0]["state_topics_missing"] == []


def test_state_coverage_on_empty_candidates_is_a_noop():
    assert pt._detect_i11_state_coverage([], ["jeedom2ha/1/2/state"]) == []


# ---------------------------------------------------------------------------
# capture_snapshot — câblage bout-en-bout, opt-in via fichier (mode box SSH)
# ---------------------------------------------------------------------------

def test_capture_snapshot_without_state_file_keeps_story_19_1_shape(monkeypatch):
    """Backward-compat stricte : sans --mqtt-state-inventory-file, le format
    et le contenu de i11_candidates restent identiques à Story 19.1 (aucune
    clé secondary_cmd_ids/state_topics_present/state_topics_missing)."""
    monkeypatch.setattr(
        pt, "fetch_diagnostics",
        lambda *a, **k: _diagnostics_payload([_eq(42, reason_code="no_mapping", statut="non_publie")]),
    )
    monkeypatch.setattr(pt, "fetch_published_scope", lambda *a, **k: {"payload": {}})

    snapshot = pt.capture_snapshot(
        base_url="http://x", local_secret=SECRET,
        mqtt_host="x", mqtt_port=1883, label="before",
        mqtt_inventory_file=None,
        mqtt_runner=_fake_runner(stdout="homeassistant/sensor/jeedom2ha_42_3/config\n"),
    )

    assert snapshot.state_topics == []
    assert len(snapshot.i11_candidates) == 1
    assert "secondary_cmd_ids" not in snapshot.i11_candidates[0]
    assert set(snapshot.i11_candidates[0]) == {"eq_id", "primary_reason_code", "matching_topics"}


def test_capture_snapshot_with_state_inventory_file_augments_i11_candidates(monkeypatch, tmp_path):
    """Mode box SSH (scripts/parity-snapshot.sh) : les deux inventaires MQTT
    (discovery + state) arrivent déjà collectés dans des fichiers, aucun
    mosquitto_sub local requis."""
    monkeypatch.setattr(
        pt, "fetch_diagnostics",
        lambda *a, **k: _diagnostics_payload([_eq(579, reason_code="no_mapping", statut="non_publie")]),
    )
    monkeypatch.setattr(pt, "fetch_published_scope", lambda *a, **k: {"payload": {}})

    discovery_file = tmp_path / "topics"
    discovery_file.write_text("homeassistant/sensor/jeedom2ha_579_5369/config\n")
    state_file = tmp_path / "state_topics"
    state_file.write_text("jeedom2ha/579/5369/state\n")

    def _unexpected(*a, **kw):
        pytest.fail("File-based inventories must not launch a local MQTT client")

    snapshot = pt.capture_snapshot(
        base_url="http://x", local_secret=SECRET,
        mqtt_host="x", mqtt_port=1883, label="before",
        mqtt_inventory_file=str(discovery_file),
        mqtt_state_inventory_file=str(state_file),
        mqtt_runner=_unexpected,
    )

    assert snapshot.state_topics == ["jeedom2ha/579/5369/state"]
    assert len(snapshot.i11_candidates) == 1
    assert snapshot.i11_candidates[0]["state_topics_present"] == [5369]
    assert snapshot.i11_candidates[0]["state_topics_missing"] == []


def test_capture_snapshot_with_state_inventory_file_reports_missing_state(monkeypatch, tmp_path):
    """La preuve terrain doit signaler un candidat I11 dont le secondaire n'a
    PAS son état streamé — exactement le bug que Story 19.2 corrige."""
    monkeypatch.setattr(
        pt, "fetch_diagnostics",
        lambda *a, **k: _diagnostics_payload([_eq(42, reason_code="no_mapping", statut="non_publie")]),
    )
    monkeypatch.setattr(pt, "fetch_published_scope", lambda *a, **k: {"payload": {}})

    discovery_file = tmp_path / "topics"
    discovery_file.write_text("homeassistant/sensor/jeedom2ha_42_3/config\n")
    state_file = tmp_path / "state_topics"
    state_file.write_text("")  # aucun état retenu

    snapshot = pt.capture_snapshot(
        base_url="http://x", local_secret=SECRET,
        mqtt_host="x", mqtt_port=1883, label="before",
        mqtt_inventory_file=str(discovery_file),
        mqtt_state_inventory_file=str(state_file),
        mqtt_runner=lambda *a, **k: pytest.fail("unexpected mosquitto_sub"),
    )

    assert snapshot.state_topics == []
    assert snapshot.i11_candidates[0]["state_topics_missing"] == [3]


def test_state_inventory_file_does_not_raise_when_empty(monkeypatch, tmp_path):
    """Contrairement à l'inventaire discovery (AC3, échec explicite si vide),
    un inventaire d'état vide n'est pas un échec de la capture : c'est la
    preuve elle-même (candidats I11 tous marqués `state_topics_missing`)."""
    monkeypatch.setattr(
        pt, "fetch_diagnostics", lambda *a, **k: _diagnostics_payload([_eq(1)]),
    )
    monkeypatch.setattr(pt, "fetch_published_scope", lambda *a, **k: {"payload": {}})

    discovery_file = tmp_path / "topics"
    discovery_file.write_text("homeassistant/light/jeedom2ha_1/config\n")
    state_file = tmp_path / "state_topics"
    state_file.write_text("")

    snapshot = pt.capture_snapshot(
        base_url="http://x", local_secret=SECRET,
        mqtt_host="x", mqtt_port=1883, label="before",
        mqtt_inventory_file=str(discovery_file),
        mqtt_state_inventory_file=str(state_file),
        mqtt_runner=lambda *a, **k: pytest.fail("unexpected mosquitto_sub"),
    )

    assert snapshot.state_topics == []


def test_snapshot_to_dict_includes_state_topics_key():
    snapshot = pt.ParitySnapshot(
        captured_at="2026-09-28T00:00:00Z", label="before",
        decisions=[], mqtt_topics=[], state_topics=["jeedom2ha/1/2/state"],
    )
    assert snapshot.to_dict()["state_topics"] == ["jeedom2ha/1/2/state"]


# ---------------------------------------------------------------------------
# CLI — --mqtt-state-inventory-file reste optionnel
# ---------------------------------------------------------------------------

def test_cli_accepts_optional_mqtt_state_inventory_file_flag(tmp_path):
    parser = pt.build_arg_parser()
    args = parser.parse_args([
        "capture", "--base-url", "http://192.0.2.1:9999",
        "--mqtt-host", "192.0.2.1", "--mqtt-port", "1883",
        "--mqtt-inventory-file", str(tmp_path / "topics"),
        "--mqtt-state-inventory-file", str(tmp_path / "state_topics"),
        "--label", "before", "--output", str(tmp_path / "out.json"),
    ])
    assert args.mqtt_state_inventory_file == str(tmp_path / "state_topics")


def test_cli_omits_mqtt_state_inventory_file_by_default(tmp_path):
    parser = pt.build_arg_parser()
    args = parser.parse_args([
        "capture", "--base-url", "http://192.0.2.1:9999",
        "--mqtt-host", "192.0.2.1", "--mqtt-port", "1883",
        "--label", "before", "--output", str(tmp_path / "out.json"),
    ])
    assert args.mqtt_state_inventory_file is None
