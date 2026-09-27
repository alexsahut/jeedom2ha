"""Story 19.1 — Task 3/Task 4 : outil de parité `tools/parity_snapshot.py`
(AC3, AC4, AC5).

Ces tests s'exécutent EXCLUSIVEMENT en local, avec un serveur HTTP mocké
(`aiohttp` test client) et un `mosquitto_sub` simulé (fonction `runner`
injectée) — jamais de connexion réseau réelle, jamais la box 192.168.1.21.

Couverture :
  - AC5 (non négociable) : `local_secret` n'apparaît JAMAIS en clair dans les
    arguments, les logs ou la sortie de l'outil, quel que soit le mode d'appel
    (recherche statique du code source + assertion sur la sortie capturée).
  - AC3 : un relevé de décisions vide OU un inventaire MQTT vide échoue de
    façon explicite (jamais un succès déguisé) — au niveau capture ET diff.
  - AC3 : ordre déterministe (tri par eq_id, tri alphabétique des topics).
  - AC4 : détection (lecture seule) des candidats I11 et du scope explicite.
  - Le tool ne fait jamais aucune écriture (jamais `mosquitto_pub`, jamais
    `/action/sync`) — vérifié par revue du code source (aucun appel).
"""

from __future__ import annotations

import inspect
import io
import json
import subprocess
import tokenize
from contextlib import redirect_stdout
from unittest.mock import MagicMock

import pytest

from tools import parity_snapshot as pt


SECRET = "super-secret-value-should-never-leak"


def _fake_runner(stdout: str = "", returncode: int = 0):
    def _run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = stdout
        result.stderr = ""
        result.returncode = returncode
        return result
    return _run


def _diagnostics_payload(equipments):
    return {
        "action": "system.diagnostics",
        "status": "ok",
        "payload": {"equipments": equipments},
    }


def _cmd(entry):
    """Une commande peut être un simple cmd_id (str) ou un dict complet
    `{"cmd_id": ..., "mapping_decision": ...}` pour les tests qui vérifient la
    préservation de `mapping_decision` (Finding 2, revue Codex PR #169)."""
    if isinstance(entry, dict):
        return entry
    return {"cmd_id": entry}


def _eq(eq_id, *, reason_code="sure", statut="publie", matched=None, unmatched=None,
        publication_override=None):
    entry = {
        "eq_id": eq_id,
        "name": f"Eq {eq_id}",
        "status_code": "published" if statut == "publie" else "not_published",
        "reason_code": reason_code,
        "perimetre": "inclus",
        "statut": statut,
        "matched_commands": [_cmd(c) for c in (matched or [])],
        "unmatched_commands": [_cmd(c) for c in (unmatched or [])],
    }
    if publication_override is not None:
        entry["publication_override"] = publication_override
    return entry


# ---------------------------------------------------------------------------
# AC5 — local_secret jamais exposé
# ---------------------------------------------------------------------------

def test_source_code_never_prints_or_logs_the_secret_variable():
    """Recherche statique : aucune ligne du module n'imprime/journalise une
    variable nommée localement `secret`/`local_secret` en clair. Seule
    utilisation légitime : transmission via l'en-tête HTTP `X-Local-Secret`."""
    source = inspect.getsource(pt)
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if ("print(" in stripped or "_LOGGER" in stripped) and "secret" in stripped.lower():
            assert "X-Local-Secret" in stripped, (
                f"Ligne suspecte imprimant potentiellement le secret : {line!r}"
            )
    # Vérification positive : le secret ne transite QUE via le header de la requête.
    assert 'headers={"X-Local-Secret": local_secret}' in source


def test_load_local_secret_rejects_both_sources_defined(monkeypatch):
    env = {pt._LOCAL_SECRET_ENV: SECRET, pt._LOCAL_SECRET_FILE_ENV: "/tmp/whatever"}
    with pytest.raises(pt.ParitySnapshotError):
        pt._load_local_secret(env)


def test_load_local_secret_missing_raises(monkeypatch):
    with pytest.raises(pt.ParitySnapshotError):
        pt._load_local_secret({})


def test_load_local_secret_from_file(tmp_path):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text(SECRET + "\n", encoding="utf-8")
    env = {pt._LOCAL_SECRET_FILE_ENV: str(secret_file)}
    assert pt._load_local_secret(env) == SECRET


def test_capture_cli_never_prints_secret_to_stdout_or_stderr(monkeypatch, tmp_path):
    """Exécution bout-en-bout de `capture` (HTTP + mosquitto_sub mockés) —
    la sortie capturée (stdout) ne doit jamais contenir le secret, même si
    l'outil échoue en cours de route."""
    monkeypatch.setenv(pt._LOCAL_SECRET_ENV, SECRET)

    captured_headers = {}

    class _FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _fake_urlopen(request, timeout=None):
        captured_headers.update(request.headers)
        body = json.dumps(_diagnostics_payload([_eq(1)])).encode("utf-8")
        return _FakeResponse(body)

    monkeypatch.setattr(pt.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(
        pt, "fetch_mqtt_retained_inventory",
        lambda *a, **k: ["homeassistant/light/jeedom2ha_1/config"],
    )

    output_path = tmp_path / "before.json"
    parser = pt.build_arg_parser()
    args = parser.parse_args([
        "capture", "--base-url", "http://192.0.2.1:9999",
        "--mqtt-host", "192.0.2.1", "--mqtt-port", "1883",
        "--label", "before", "--output", str(output_path),
    ])

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = pt._cmd_capture(args)

    assert rc == 0
    assert SECRET not in buf.getvalue()
    # Header casing normalisé par urllib.request.Request ("X-local-secret").
    assert captured_headers.get("X-local-secret") == SECRET
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert SECRET not in json.dumps(written)


# ---------------------------------------------------------------------------
# AC3 — relevé vide = échec explicite, jamais un succès déguisé
# ---------------------------------------------------------------------------

def test_capture_snapshot_fails_loudly_on_empty_decisions(monkeypatch):
    monkeypatch.setattr(pt, "fetch_diagnostics", lambda *a, **k: _diagnostics_payload([]))
    with pytest.raises(pt.ParitySnapshotError, match="aucune décision"):
        pt.capture_snapshot(
            base_url="http://x", local_secret=SECRET,
            mqtt_host="x", mqtt_port=1883, label="before",
        )


def test_capture_snapshot_fails_loudly_on_empty_mqtt_inventory(monkeypatch):
    monkeypatch.setattr(pt, "fetch_diagnostics", lambda *a, **k: _diagnostics_payload([_eq(1)]))
    with pytest.raises(pt.ParitySnapshotError, match="inventaire MQTT retained vide"):
        pt.capture_snapshot(
            base_url="http://x", local_secret=SECRET,
            mqtt_host="x", mqtt_port=1883, label="before",
            mqtt_runner=_fake_runner(stdout=""),
        )


def test_fetch_mqtt_inventory_never_swallows_subprocess_errors(monkeypatch):
    """Contrairement au `|| true` de deploy-to-box.sh, une erreur subprocess
    (mosquitto_sub absent) doit remonter explicitement, jamais un résultat vide
    silencieux."""
    def _raise(*a, **k):
        raise FileNotFoundError("mosquitto_sub")

    with pytest.raises(pt.ParitySnapshotError, match="introuvable"):
        pt.fetch_mqtt_retained_inventory("host", 1883, runner=_raise)


def test_fetch_mqtt_inventory_timeout_raises_explicitly():
    def _timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd="mosquitto_sub", timeout=12)

    with pytest.raises(pt.ParitySnapshotError, match="injoignable"):
        pt.fetch_mqtt_retained_inventory("host", 1883, runner=_timeout)


def test_diff_snapshots_fails_loudly_when_before_is_empty():
    empty = {"decisions": [], "mqtt_topics": []}
    non_empty = {
        "decisions": [{"eq_id": 1}], "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
    }
    with pytest.raises(pt.ParitySnapshotError, match="before"):
        pt.diff_snapshots(empty, non_empty)


def test_diff_snapshots_fails_loudly_when_after_is_empty():
    empty = {"decisions": [], "mqtt_topics": []}
    non_empty = {
        "decisions": [{"eq_id": 1}], "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
    }
    with pytest.raises(pt.ParitySnapshotError, match="after"):
        pt.diff_snapshots(non_empty, empty)


def test_diff_snapshots_reports_empty_diff_when_identical():
    snap = {
        "decisions": [
            {"eq_id": 1, "reason_code": "sure", "statut": "publie"},
        ],
        "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
    }
    result = pt.diff_snapshots(snap, snap)
    assert result["is_empty_diff"] is True
    assert result["changed_decisions"] == []
    assert result["topics_added"] == []
    assert result["topics_removed"] == []


def test_diff_snapshots_detects_changed_decision():
    before = {
        "decisions": [{"eq_id": 1, "reason_code": "sure", "statut": "publie"}],
        "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
    }
    after = {
        "decisions": [{"eq_id": 1, "reason_code": "no_mapping", "statut": "non_publie"}],
        "mqtt_topics": ["homeassistant/light/jeedom2ha_1/config"],
    }
    result = pt.diff_snapshots(before, after)
    assert result["is_empty_diff"] is False
    assert result["changed_decisions"] == [{"eq_id": 1, "before": before["decisions"][0], "after": after["decisions"][0]}]


# ---------------------------------------------------------------------------
# Ordre déterministe
# ---------------------------------------------------------------------------

def test_decision_records_sorted_deterministically_by_eq_id():
    payload = _diagnostics_payload([_eq(30), _eq(5), _eq(17)])
    records = pt._decision_records(payload)
    assert [r["eq_id"] for r in records] == [5, 17, 30]


def test_mqtt_inventory_sorted_and_deduplicated():
    unordered = (
        "homeassistant/light/jeedom2ha_2/config\n"
        "homeassistant/light/jeedom2ha_1/config\n"
        "homeassistant/light/jeedom2ha_1/config\n"  # doublon volontaire
        "homeassistant/light/other_vendor/config\n"  # ne matche pas le filtre
    )
    topics = pt.fetch_mqtt_retained_inventory(
        "host", 1883, runner=_fake_runner(stdout=unordered)
    )
    assert topics == [
        "homeassistant/light/jeedom2ha_1/config",
        "homeassistant/light/jeedom2ha_2/config",
    ]


# ---------------------------------------------------------------------------
# AC4 — I11 (heuristique) et scope explicite, lecture seule, sans correction
# ---------------------------------------------------------------------------

def test_detect_i11_candidate_when_primary_refused_but_topic_published():
    decisions = [_eq(42, reason_code="no_mapping", statut="non_publie")]
    records = pt._decision_records(_diagnostics_payload(decisions))
    topics = ["homeassistant/sensor/jeedom2ha_42_3/config"]
    candidates = pt._detect_i11_candidates(records, topics)
    assert len(candidates) == 1
    assert candidates[0]["eq_id"] == 42
    assert candidates[0]["matching_topics"] == topics


def test_no_i11_candidate_when_primary_published():
    decisions = [_eq(42, reason_code="sure", statut="publie")]
    records = pt._decision_records(_diagnostics_payload(decisions))
    topics = ["homeassistant/light/jeedom2ha_42/config"]
    assert pt._detect_i11_candidates(records, topics) == []


def test_no_i11_candidate_when_no_matching_topic():
    decisions = [_eq(42, reason_code="no_mapping", statut="non_publie")]
    records = pt._decision_records(_diagnostics_payload(decisions))
    topics = ["homeassistant/light/jeedom2ha_999/config"]
    assert pt._detect_i11_candidates(records, topics) == []


def test_detect_explicit_scope_via_reason_code():
    decisions = [_eq(7, reason_code="publication_forced", statut="publie")]
    records = pt._decision_records(_diagnostics_payload(decisions))
    found = pt._detect_explicit_scope(records)
    assert found == [{"eq_id": 7, "reason_code": "publication_forced", "publication_override": None}]


def test_detect_explicit_scope_via_publication_override_key():
    decisions = [_eq(8, reason_code="sure", statut="publie", publication_override={"source": "user"})]
    records = pt._decision_records(_diagnostics_payload(decisions))
    found = pt._detect_explicit_scope(records)
    assert found and found[0]["eq_id"] == 8


def test_no_explicit_scope_on_plain_decision():
    decisions = [_eq(9, reason_code="sure", statut="publie")]
    records = pt._decision_records(_diagnostics_payload(decisions))
    assert pt._detect_explicit_scope(records) == []


# ---------------------------------------------------------------------------
# Régressions — revue bot Codex sur PR #169 (3 remarques)
# ---------------------------------------------------------------------------

def test_decision_records_preserves_mapping_decision_per_command():
    """Finding 2 : `_decision_records` réduisait `matched_commands`/
    `unmatched_commands` aux seuls `cmd_id`, perdant `mapping_decision` — un
    changement de décision sur une commande (ex. `sure` -> `publication_forced`)
    sans changement de l'ensemble des cmd_id produisait alors à tort un diff
    vide."""
    before = _eq(1, matched=[{"cmd_id": "sure", "mapping_decision": "sure"}])
    after = _eq(1, matched=[{"cmd_id": "sure", "mapping_decision": "publication_forced"}])
    before_records = pt._decision_records(_diagnostics_payload([before]))
    after_records = pt._decision_records(_diagnostics_payload([after]))

    assert before_records[0]["matched_commands"] == [
        {"cmd_id": "sure", "mapping_decision": "sure"}
    ]
    assert after_records[0]["matched_commands"] == [
        {"cmd_id": "sure", "mapping_decision": "publication_forced"}
    ]

    topics = ["homeassistant/light/jeedom2ha_1/config"]
    result = pt.diff_snapshots(
        {"decisions": before_records, "mqtt_topics": topics},
        {"decisions": after_records, "mqtt_topics": topics},
    )
    assert result["is_empty_diff"] is False
    assert result["changed_decisions"][0]["eq_id"] == 1


def test_no_i11_candidate_when_only_stale_primary_topic_matches():
    """Finding 3 : un topic retained égal EXACTEMENT au node_id primaire
    (`jeedom2ha_<eq_id>`, sans suffixe `_<cmd_id>`) est le résidu/topic obsolète
    du primaire lui-même, jamais la preuve qu'un secondaire est publié — ne
    doit jamais produire de faux candidat I11."""
    decisions = [_eq(42, reason_code="no_mapping", statut="non_publie")]
    records = pt._decision_records(_diagnostics_payload(decisions))
    topics = ["homeassistant/light/jeedom2ha_42/config"]
    assert pt._detect_i11_candidates(records, topics) == []


def test_detect_published_scope_exceptions_via_equipment_decision_source():
    """Finding 1 : `_detect_explicit_scope` ne couvrait que les overrides de
    politique de publication (Story 16.3, `decide_publication`), pas le
    périmètre canonique global -> pièce -> équipement exposé par
    `/system/published_scope` (`models/published_scope.py`) — une exception au
    niveau équipement y passait inaperçue."""
    payload = {
        "status": "ok",
        "payload": {
            "equipements": [
                {
                    "eq_id": 5, "effective_state": "exclu",
                    "decision_source": "equipement", "is_exception": True,
                },
                {
                    "eq_id": 3, "effective_state": "inclus",
                    "decision_source": "piece", "is_exception": False,
                },
            ]
        },
    }
    found = pt._detect_published_scope_exceptions(payload)
    assert found == [
        {"eq_id": 5, "effective_state": "exclu", "decision_source": "equipement", "is_exception": True},
    ]


def test_detect_published_scope_exceptions_via_exception_equipement_source():
    payload = {
        "status": "ok",
        "payload": {
            "equipements": [
                {
                    "eq_id": 9, "effective_state": "inclus",
                    "decision_source": "exception_equipement", "is_exception": True,
                },
            ]
        },
    }
    found = pt._detect_published_scope_exceptions(payload)
    assert found and found[0]["eq_id"] == 9


def test_no_published_scope_exception_when_inherited_from_global():
    payload = {
        "status": "ok",
        "payload": {
            "equipements": [
                {
                    "eq_id": 3, "effective_state": "inclus",
                    "decision_source": "global", "is_exception": False,
                },
            ]
        },
    }
    assert pt._detect_published_scope_exceptions(payload) == []


def test_capture_snapshot_includes_published_scope_exceptions(monkeypatch):
    """Vérifie le câblage bout-en-bout (pas seulement la fonction pure) :
    `capture_snapshot` appelle bien `fetch_published_scope` et propage le
    résultat de `_detect_published_scope_exceptions` dans le snapshot."""
    monkeypatch.setattr(pt, "fetch_diagnostics", lambda *a, **k: _diagnostics_payload([_eq(1)]))
    monkeypatch.setattr(
        pt, "fetch_published_scope",
        lambda *a, **k: {
            "status": "ok",
            "payload": {
                "equipements": [
                    {
                        "eq_id": 1, "effective_state": "exclu",
                        "decision_source": "equipement", "is_exception": True,
                    },
                ]
            },
        },
    )
    snapshot = pt.capture_snapshot(
        base_url="http://x", local_secret=SECRET,
        mqtt_host="x", mqtt_port=1883, label="before",
        mqtt_runner=_fake_runner(stdout="homeassistant/light/jeedom2ha_1/config\n"),
    )
    assert snapshot.published_scope_exceptions == [
        {"eq_id": 1, "effective_state": "exclu", "decision_source": "equipement", "is_exception": True},
    ]


# ---------------------------------------------------------------------------
# Lecture seule stricte : aucune écriture MQTT, aucun appel /action/*
# ---------------------------------------------------------------------------

def test_module_never_calls_mosquitto_pub_or_action_endpoints():
    """Recherche statique restreinte au CODE réel (hors docstrings/commentaires,
    qui mentionnent volontairement ces termes pour documenter l'interdiction) :
    aucun appel effectif à `mosquitto_pub` ni `/action/*` ni écriture de
    `ha_overrides.json`."""
    source = inspect.getsource(pt)
    code_tokens = [
        tok.string
        for tok in tokenize.generate_tokens(io.StringIO(source).readline)
        if tok.type not in (tokenize.STRING, tokenize.COMMENT)
    ]
    code_only = " ".join(code_tokens)
    assert "mosquitto_pub" not in code_only
    assert "/action/" not in code_only
    assert "ha_overrides.json" not in code_only
