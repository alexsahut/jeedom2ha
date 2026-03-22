import itertools

import pytest

from resources.daemon.models.published_scope import resolve_published_scope
from resources.daemon.models.topology import TopologySnapshot

_STATES = ("inherit", "include", "exclude")


def _single_eq_snapshot() -> TopologySnapshot:
    payload = {
        "objects": [{"id": 1, "name": "Salon"}],
        "eq_logics": [{"id": 10, "name": "Lampe", "object_id": 1}],
    }
    return TopologySnapshot.from_jeedom_payload(payload)


def _expected_resolution(global_state: str, piece_state: str, eq_state: str):
    global_effective = "include" if global_state == "inherit" else global_state
    piece_effective = global_effective if piece_state == "inherit" else piece_state

    if eq_state == "inherit":
        effective = piece_effective
        source = "piece" if piece_state != "inherit" else "global"
        is_exception = False
    else:
        effective = eq_state
        if eq_state != piece_effective:
            source = "exception_equipement"
            is_exception = True
        else:
            source = "equipement"
            is_exception = False
    return effective, source, is_exception


@pytest.mark.parametrize(
    ("global_state", "piece_state", "eq_state"),
    list(itertools.product(_STATES, _STATES, _STATES)),
)
def test_resolver_matrix_global_piece_eq_states(global_state, piece_state, eq_state):
    snapshot = _single_eq_snapshot()
    raw_scope = {
        "global": {"raw_state": global_state},
        "pieces": {"1": {"raw_state": piece_state}},
        "equipements": {"10": {"raw_state": eq_state}},
    }

    resolved = resolve_published_scope(snapshot, raw_scope=raw_scope)
    eq = resolved["equipements"][0]
    expected_effective, expected_source, expected_exception = _expected_resolution(
        global_state, piece_state, eq_state
    )

    assert eq["effective_state"] == expected_effective
    assert eq["decision_source"] == expected_source
    assert eq["is_exception"] == expected_exception
    assert resolved["global"]["counts"]["total"] == 1
    assert resolved["global"]["counts"][expected_effective] == 1


def test_resolver_precedence_piece_over_global_when_eq_inherit():
    snapshot = _single_eq_snapshot()
    resolved = resolve_published_scope(
        snapshot,
        raw_scope={
            "global": {"raw_state": "exclude"},
            "pieces": {"1": {"raw_state": "include"}},
            "equipements": {"10": {"raw_state": "inherit"}},
        },
    )

    eq = resolved["equipements"][0]
    assert eq["effective_state"] == "include"
    assert eq["decision_source"] == "piece"
    assert eq["is_exception"] is False


def test_resolver_exception_equipement_include_in_excluded_piece():
    snapshot = _single_eq_snapshot()
    resolved = resolve_published_scope(
        snapshot,
        raw_scope={
            "global": {"raw_state": "include"},
            "pieces": {"1": {"raw_state": "exclude"}},
            "equipements": {"10": {"raw_state": "include"}},
        },
    )

    eq = resolved["equipements"][0]
    assert eq["effective_state"] == "include"
    assert eq["decision_source"] == "exception_equipement"
    assert eq["is_exception"] is True
    assert resolved["global"]["counts"]["exceptions"] == 1
    assert resolved["pieces"][0]["counts"]["exceptions"] == 1


def test_resolver_deterministic_same_snapshot_same_scope():
    payload = {
        "objects": [{"id": 1, "name": "Salon"}, {"id": 2, "name": "Cuisine"}],
        "eq_logics": [
            {"id": 10, "name": "Lampe Salon", "object_id": 1},
            {"id": 11, "name": "Prise Salon", "object_id": 1},
            {"id": 20, "name": "Lampe Cuisine", "object_id": 2},
        ],
    }
    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    raw_scope = {
        "global": {"raw_state": "include"},
        "pieces": {
            "1": {"raw_state": "exclude"},
            "2": {"raw_state": "inherit"},
        },
        "equipements": {
            "10": {"raw_state": "include"},
            "11": {"raw_state": "inherit"},
            "20": {"raw_state": "inherit"},
        },
    }

    first = resolve_published_scope(snapshot, raw_scope=raw_scope)
    second = resolve_published_scope(snapshot, raw_scope=raw_scope)
    assert first == second


def test_resolver_invalid_values_fallback_is_deterministic():
    snapshot = _single_eq_snapshot()
    resolved = resolve_published_scope(
        snapshot,
        raw_scope={
            "global": {"raw_state": "???"},
            "pieces": {"1": {"raw_state": None}},
            "equipements": {"10": {"raw_state": "invalid"}},
        },
    )

    # All invalid/missing values normalize to inherit, then root inherit -> include.
    eq = resolved["equipements"][0]
    assert eq["effective_state"] == "include"
    assert eq["decision_source"] == "global"
    assert eq["is_exception"] is False
    assert resolved["global"]["effective_state"] == "include"


def test_resolver_legacy_eqlogic_exclusion_fallback_is_tested():
    payload = {
        "objects": [{"id": 1, "name": "Salon"}],
        "eq_logics": [
            {
                "id": 10,
                "name": "Lampe Exclue Legacy",
                "object_id": 1,
                "is_excluded": True,
                "exclusion_source": "eqlogic",
            }
        ],
    }
    snapshot = TopologySnapshot.from_jeedom_payload(payload)

    resolved = resolve_published_scope(snapshot, raw_scope={})
    eq = resolved["equipements"][0]

    assert eq["effective_state"] == "exclude"
    assert eq["decision_source"] == "exception_equipement"
    assert eq["is_exception"] is True


def test_resolver_legacy_object_exclusion_fallback_is_tested():
    payload = {
        "objects": [{"id": 1, "name": "Salon"}],
        "eq_logics": [
            {
                "id": 10,
                "name": "Eq 10",
                "object_id": 1,
                "is_excluded": True,
                "exclusion_source": "object",
            },
            {
                "id": 11,
                "name": "Eq 11",
                "object_id": 1,
                "is_excluded": True,
                "exclusion_source": "object",
            },
        ],
    }
    snapshot = TopologySnapshot.from_jeedom_payload(payload)

    resolved = resolve_published_scope(snapshot, raw_scope={})
    eq_by_id = {eq["eq_id"]: eq for eq in resolved["equipements"]}

    assert eq_by_id[10]["effective_state"] == "exclude"
    assert eq_by_id[10]["decision_source"] == "piece"
    assert eq_by_id[11]["effective_state"] == "exclude"
    assert eq_by_id[11]["decision_source"] == "piece"
    assert resolved["global"]["counts"]["exclude"] == 2


def test_resolver_legacy_plugin_exclusion_fallback_is_tested():
    payload = {
        "objects": [{"id": 1, "name": "Salon"}],
        "eq_logics": [
            {
                "id": 10,
                "name": "Eq Plugin Exclu",
                "object_id": 1,
                "is_excluded": True,
                "exclusion_source": "plugin",
            }
        ],
    }
    snapshot = TopologySnapshot.from_jeedom_payload(payload)

    resolved = resolve_published_scope(snapshot, raw_scope={})
    eq = resolved["equipements"][0]

    assert eq["effective_state"] == "exclude"
    assert eq["decision_source"] == "exception_equipement"
    assert eq["is_exception"] is True


def test_resolver_legacy_object_exclusion_fallback_with_default_inherit_piece_entry():
    payload = {
        "objects": [{"id": 1, "name": "Salon"}],
        "eq_logics": [
            {
                "id": 10,
                "name": "Eq Legacy Piece Exclue",
                "object_id": 1,
                "is_excluded": True,
                "exclusion_source": "object",
            }
        ],
    }
    snapshot = TopologySnapshot.from_jeedom_payload(payload)

    # Cas réel getFullTopology(): entrée pièce préremplie "inherit/default_inherit".
    resolved = resolve_published_scope(
        snapshot,
        raw_scope={
            "global": {"raw_state": "include"},
            "pieces": {"1": {"raw_state": "inherit", "source": "default_inherit"}},
            "equipements": {"10": {"raw_state": "inherit", "source": "default_inherit"}},
        },
    )
    eq = resolved["equipements"][0]

    assert eq["effective_state"] == "exclude"
    assert eq["decision_source"] == "piece"
    assert eq["is_exception"] is False
