import pytest
from resources.daemon.models.topology import TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd

def test_topology_snapshot_normalisation():
    payload = {
        "timestamp": "2026-03-13T12:00:00Z",
        "objects": [
            {"id": "5", "name": "Salon", "father_id": None},
            {"id": 6, "name": "Cuisine", "father_id": "5"}
        ],
        "eq_logics": [
            {
                "id": "42",
                "name": "Lampe Salon",
                "object_id": "5",
                "is_enable": "1",
                "is_visible": "1",
                "eq_type": "zwave",
                "generic_type": "",
                "is_excluded": False,
                "cmds": [
                    {
                        "id": "123",
                        "name": "Etat",
                        "generic_type": "LIGHT_STATE",
                        "type": "info",
                        "sub_type": "binary",
                        "current_value": "0",
                        "unit": "",
                        "is_visible": True,
                        "is_historized": "1"
                    }
                ]
            }
        ]
    }
    
    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    
    # Check objects
    assert 5 in snapshot.objects
    assert snapshot.objects[5].id == 5
    assert snapshot.objects[5].name == "Salon"
    assert 6 in snapshot.objects
    assert snapshot.objects[6].father_id == 5
    
    # Check eq_logics
    assert 42 in snapshot.eq_logics
    eq = snapshot.eq_logics[42]
    assert eq.id == 42
    assert eq.object_id == 5
    assert eq.is_enable is True
    assert eq.generic_type is None
    
    # Check cmds
    assert len(eq.cmds) == 1
    cmd = eq.cmds[0]
    assert cmd.id == 123
    assert cmd.generic_type == "LIGHT_STATE"
    assert cmd.unit is None
    assert cmd.is_historized is True

def test_topology_snapshot_robustness():
    # Test with missing fields and bad types
    payload = {
        "objects": [
            {"id": "invalid", "name": "Bad Object"}, # Should be skipped
            {"id": 7, "name": "Good Object"}
        ],
        "eq_logics": [
            {
                "id": 43,
                # Missing name, missing object_id
                "cmds": [
                    {"id": "bad_cmd"} # Should be skipped
                ]
            }
        ]
    }
    
    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    
    assert len(snapshot.objects) == 1
    assert 7 in snapshot.objects
    assert len(snapshot.eq_logics) == 1
    assert 43 in snapshot.eq_logics
    assert snapshot.eq_logics[43].name == "Eq 43"
    assert snapshot.eq_logics[43].object_id is None
    assert len(snapshot.eq_logics[43].cmds) == 0

def test_suggested_area():
    payload = {
        "objects": [{"id": 1, "name": "Living Room"}],
        "eq_logics": [
            {"id": 10, "name": "Light", "object_id": 1},
            {"id": 11, "name": "Hidden", "object_id": 99} # Unknown object
        ]
    }
    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    
    assert snapshot.get_suggested_area(10) == "Living Room"
    assert snapshot.get_suggested_area(11) is None
    assert snapshot.get_suggested_area(999) is None

def test_topology_snapshot_empty_payload():
    """L1: Empty payload should produce a snapshot with empty dicts."""
    snapshot = TopologySnapshot.from_jeedom_payload({})
    assert snapshot.objects == {}
    assert snapshot.eq_logics == {}
    assert snapshot.timestamp  # should have a fallback timestamp

def test_topology_string_bool_normalisation():
    """M4: Jeedom returns "0"/"1" strings for booleans — bool("0") is True in Python!"""
    payload = {
        "eq_logics": [
            {
                "id": 1,
                "name": "Disabled EqLogic",
                "is_enable": "0",
                "is_visible": "1",
                "is_excluded": "0",
                "cmds": [
                    {
                        "id": 10,
                        "name": "Hidden Cmd",
                        "is_visible": "0",
                        "is_historized": "0",
                    }
                ],
            },
            {
                "id": 2,
                "name": "Excluded EqLogic",
                "is_excluded": "1",
                "is_enable": "1",
            },
        ]
    }
    snapshot = TopologySnapshot.from_jeedom_payload(payload)

    eq1 = snapshot.eq_logics[1]
    assert eq1.is_enable is False, "String '0' must be False"
    assert eq1.is_visible is True, "String '1' must be True"
    assert eq1.is_excluded is False
    cmd = eq1.cmds[0]
    assert cmd.is_visible is False, "String '0' must be False for cmd"
    assert cmd.is_historized is False

    eq2 = snapshot.eq_logics[2]
    assert eq2.is_excluded is True, "String '1' must be True"
    assert eq2.is_enable is True
