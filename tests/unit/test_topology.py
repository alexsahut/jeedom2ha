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
