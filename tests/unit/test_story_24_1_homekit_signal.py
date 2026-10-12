"""Story 24.1 — signal d'exposition HomeKit et identifiants physiques (démon, additif).

Normalisation à trois états, payload ancien inchangé, et garde-fou « lecture seule » sur le
code PHP ajouté. Identifiants génériques uniquement (CC-48).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from models.topology import (
    TopologySnapshot,
    _normalize_logical_id,
    _to_tristate,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "raw,expected",
    [
        (1, True), (0, False), ("1", True), ("0", False),
        (True, True), (False, False), ("true", True), ("false", False),
        (" 1 ", True), (1.0, True), (0.0, False),
        (None, None), ("", None), ("x", None), (2, None), (-1, None), ([], None),
    ],
)
def test_tristate_normalisation(raw, expected):
    assert _to_tristate(raw) is expected


@pytest.mark.parametrize(
    "raw,expected",
    [("", None), ("  ", None), (None, None), (True, None), (["a"], None),
     ("ab:01", "ab:01"), (42, "42"), (" x ", "x")],
)
def test_logical_id_normalisation(raw, expected):
    assert _normalize_logical_id(raw) == expected


def _payload(**eq_extra):
    eq = {"id": 1, "name": "Eq 1", "object_id": 10, "eq_type": "virtual",
          "cmds": [{"id": 5, "name": "Cmd 5", "type": "info", "sub_type": "binary"}]}
    eq.update(eq_extra)
    return {"timestamp": "t", "objects": [{"id": 10, "name": "Room 10"}], "eq_logics": [eq],
            "scenarios": [{"id": 3, "name": "Sc 3", "is_active": True}]}


def test_old_payload_gives_unknown_signal_and_same_snapshot_fields():
    snap = TopologySnapshot.from_jeedom_payload(_payload())
    eq = snap.eq_logics[1]
    assert eq.homekit_exposed is None
    assert eq.homekit_exposed_source is None
    assert eq.logical_id is None
    assert eq.cmds[0].logical_id is None
    sc = snap.scenarios[3]
    assert sc.homekit_exposed is None and sc.homekit_exposed_source is None
    # Les champs existants sont identiques à ceux d'un payload portant le signal.
    other = TopologySnapshot.from_jeedom_payload(
        _payload(homekit_exposed=True, homekit_exposed_source="equipement", logical_id="x")
    ).eq_logics[1]
    for name in ("id", "name", "object_id", "is_enable", "is_visible", "eq_type_name",
                 "generic_type", "is_excluded", "exclusion_source"):
        assert getattr(eq, name) == getattr(other, name)


@pytest.mark.parametrize("raw,expected", [(True, True), (False, False), (None, None), ("0", False), ("1", True)])
def test_eq_signal_three_states_never_none_to_false(raw, expected):
    snap = TopologySnapshot.from_jeedom_payload(_payload(homekit_exposed=raw, homekit_exposed_source="piece"))
    eq = snap.eq_logics[1]
    assert eq.homekit_exposed is expected
    assert eq.homekit_exposed_source == "piece"


def test_unknown_signal_keeps_source():
    snap = TopologySnapshot.from_jeedom_payload(
        _payload(homekit_exposed=None, homekit_exposed_source="homebridge_absent")
    )
    assert snap.eq_logics[1].homekit_exposed is None
    assert snap.eq_logics[1].homekit_exposed_source == "homebridge_absent"


def test_logical_ids_empty_become_none_and_stay_out_of_repr():
    payload = _payload(logical_id="")
    payload["eq_logics"][0]["cmds"][0]["logical_id"] = "dev:01"
    snap = TopologySnapshot.from_jeedom_payload(payload)
    assert snap.eq_logics[1].logical_id is None
    assert snap.eq_logics[1].cmds[0].logical_id == "dev:01"
    assert "dev:01" not in repr(snap.eq_logics[1])


def test_scenario_signal_three_states():
    payload = _payload()
    payload["scenarios"] = [
        {"id": 1, "name": "a", "homekit_exposed": True, "homekit_exposed_source": "scenario_configuration"},
        {"id": 2, "name": "b", "homekit_exposed": False, "homekit_exposed_source": "scenario_configuration"},
        {"id": 3, "name": "c", "homekit_exposed": None, "homekit_exposed_source": "illisible"},
    ]
    sc = TopologySnapshot.from_jeedom_payload(payload).scenarios
    assert (sc[1].homekit_exposed, sc[2].homekit_exposed, sc[3].homekit_exposed) == (True, False, None)


def test_signal_does_not_change_exclusion_or_eligibility_fields():
    payload = _payload(is_excluded=True, exclusion_source="plugin",
                       homekit_exposed=False, homekit_exposed_source="plugin_excluded")
    eq = TopologySnapshot.from_jeedom_payload(payload).eq_logics[1]
    assert eq.is_excluded is True and eq.exclusion_source == "plugin"


def test_php_additions_are_read_only():
    """Aucune écriture sur la configuration Jeedom ou Homebridge dans le code ajouté."""
    forbidden = re.compile(
        r"setConfiguration|setLogicalId|->save\(|config::save|config::remove|->remove\(|setIsEnable|setObject_id"
    )
    exposure = (ROOT / "core/php/jeedom2ha_homekit_exposure.php").read_text(encoding="utf-8")
    assert not forbidden.search(exposure)
    cls = (ROOT / "core/class/jeedom2ha.class.php").read_text(encoding="utf-8")
    start = cls.index("public static function buildHomekitExposureContext")
    end = cls.index("Extrait la topologie complète")
    assert not forbidden.search(cls[start:end])
    # Aucun journal de niveau info+ ne cite un logicalId.
    assert not re.search(r"log::add\([^;]*(logical_id|getLogicalId)", cls)
