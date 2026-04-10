import pytest
from resources.daemon.models.topology import (
    JeedomEqLogic, JeedomCmd, TopologySnapshot,
    assess_eligibility, assess_all,
)

def _make_eq(id=1, is_excluded=False, is_enable=True, cmds=None):
    """Helper to create minimal eqLogic for testing."""
    return JeedomEqLogic(
        id=id,
        name="Test",
        is_excluded=is_excluded,
        is_enable=is_enable,
        cmds=cmds or []
    )

def test_assess_eligibility_rules():
    # Rule 1: Excluded (priority over disabled)
    eq_excluded = _make_eq(is_excluded=True, is_enable=False)
    res = assess_eligibility(eq_excluded)
    assert res.is_eligible is False
    assert res.reason_code == "excluded_eqlogic"
    assert res.confidence == "sure"

    # Rule 2: Disabled
    eq_disabled = _make_eq(is_enable=False)
    res = assess_eligibility(eq_disabled)
    assert res.is_eligible is False
    assert res.reason_code == "disabled_eqlogic"
    assert res.confidence == "sure"

    # Rule 3: No commands
    eq_no_cmds = _make_eq(cmds=[])
    res = assess_eligibility(eq_no_cmds)
    assert res.is_eligible is False
    assert res.reason_code == "no_commands"
    assert res.confidence == "sure"

    # Rule 4: No generic type
    cmd_no_gt = JeedomCmd(id=1, name="Cmd", generic_type=None)
    eq_no_gt = _make_eq(cmds=[cmd_no_gt])
    res = assess_eligibility(eq_no_gt)
    assert res.is_eligible is False
    assert res.reason_code == "no_supported_generic_type"
    assert res.confidence == "sure"

    # Rule 5: Eligible — confidence starts at "unknown" (refined by mapping engine later)
    cmd_gt = JeedomCmd(id=2, name="Cmd", generic_type="LIGHT_STATE")
    eq_eligible = _make_eq(cmds=[cmd_gt])
    res = assess_eligibility(eq_eligible)
    assert res.is_eligible is True
    assert res.reason_code == "eligible"
    assert res.confidence == "unknown"

def test_assess_eligibility_mixed_commands():
    # Eligible if AT LEAST one command has a generic type
    cmds = [
        JeedomCmd(id=1, name="Cmd 1", generic_type=None),
        JeedomCmd(id=2, name="Cmd 2", generic_type="TEMPERATURE")
    ]
    eq = JeedomEqLogic(id=1, name="Test", cmds=cmds)
    res = assess_eligibility(eq)
    assert res.is_eligible is True
    assert res.confidence == "unknown"

def test_assess_all_covers_all_eqlogics():
    """M5: assess_all must return a result for every eqLogic in the snapshot."""
    cmd_with_gt = JeedomCmd(id=10, name="State", generic_type="LIGHT_STATE")
    snapshot = TopologySnapshot(
        timestamp="2026-03-13T12:00:00Z",
        eq_logics={
            1: _make_eq(id=1, cmds=[cmd_with_gt]),        # eligible
            2: _make_eq(id=2, is_enable=False),             # disabled
            3: _make_eq(id=3, is_excluded=True),            # excluded
            4: _make_eq(id=4, cmds=[]),                     # no commands
        }
    )
    results = assess_all(snapshot)

    # Must cover all eqLogics
    assert set(results.keys()) == {1, 2, 3, 4}
    assert results[1].is_eligible is True
    assert results[2].reason_code == "disabled_eqlogic"
    assert results[3].reason_code == "excluded_eqlogic"
    assert results[4].reason_code == "no_commands"
