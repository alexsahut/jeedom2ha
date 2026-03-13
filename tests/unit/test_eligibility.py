import pytest
from resources.daemon.models.topology import JeedomEqLogic, JeedomCmd, assess_eligibility

def test_assess_eligibility_rules():
    # Helper to create minimal eqLogic
    def make_eq(id=1, is_excluded=False, is_enable=True, cmds=None):
        return JeedomEqLogic(
            id=id,
            name="Test",
            is_excluded=is_excluded,
            is_enable=is_enable,
            cmds=cmds or []
        )

    # Rule 1: Excluded
    eq_excluded = make_eq(is_excluded=True, is_enable=False) # Excluded priority
    res = assess_eligibility(eq_excluded)
    assert res.is_eligible is False
    assert res.reason_code == "excluded_eqlogic"

    # Rule 2: Disabled
    eq_disabled = make_eq(is_enable=False)
    res = assess_eligibility(eq_disabled)
    assert res.is_eligible is False
    assert res.reason_code == "disabled_eqlogic"

    # Rule 3: No commands
    eq_no_cmds = make_eq(cmds=[])
    res = assess_eligibility(eq_no_cmds)
    assert res.is_eligible is False
    assert res.reason_code == "no_commands"

    # Rule 4: No generic type
    cmd_no_gt = JeedomCmd(id=1, name="Cmd", generic_type=None)
    eq_no_gt = make_eq(cmds=[cmd_no_gt])
    res = assess_eligibility(eq_no_gt)
    assert res.is_eligible is False
    assert res.reason_code == "no_supported_generic_type"

    # Rule 5: Eligible
    cmd_gt = JeedomCmd(id=2, name="Cmd", generic_type="LIGHT_STATE")
    eq_eligible = make_eq(cmds=[cmd_gt])
    res = assess_eligibility(eq_eligible)
    assert res.is_eligible is True
    assert res.reason_code == "eligible"

def test_assess_eligibility_mixed_commands():
    # Eligible if AT LEAST one command has a generic type
    cmds = [
        JeedomCmd(id=1, name="Cmd 1", generic_type=None),
        JeedomCmd(id=2, name="Cmd 2", generic_type="TEMPERATURE")
    ]
    eq = JeedomEqLogic(id=1, name="Test", cmds=cmds)
    res = assess_eligibility(eq)
    assert res.is_eligible is True
