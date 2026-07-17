"""Story 16.4 — Diagnostic override-aware avec drill-down commande par commande.

Lecture seule, additif : on vérifie que chaque entrée du drill-down commande
(`matched_commands` / `unmatched_commands`) porte `attendu_ha`, `mapping_decision`
et `retained`, que l'override de TYPE (16.2) expose native vs surchargée, et que
l'override de PUBLICATION (16.3) est exposé en consommant EXACTEMENT ses reason_codes.
"""

import pytest

from transport.http_server import create_app
from mapping.registry import resolve_expected_ha
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd, EligibilityResult
)
from models.mapping import (
    MappingResult, PublicationDecision, LightCapabilities, SwitchCapabilities
)


@pytest.fixture
def app():
    return create_app(local_secret="test_secret")


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _light_eq(eq_id, cmd_state_id, cmd_slider_id, extra_cmds=None):
    cmds = [
        JeedomCmd(id=cmd_state_id, name="Etat", generic_type="LIGHT_STATE"),
        JeedomCmd(id=cmd_slider_id, name="Slider", generic_type="LIGHT_SLIDER"),
    ]
    if extra_cmds:
        cmds.extend(extra_cmds)
    return JeedomEqLogic(id=eq_id, name=f"Lampe {eq_id}", object_id=1, is_enable=True, cmds=cmds)


async def _get_equipments(cli, app, snapshot, eligibility, mappings, publications):
    app["topology"] = snapshot
    app["eligibility"] = eligibility
    app["mappings"] = mappings
    app["publications"] = publications
    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    return {e["eq_id"]: e for e in data["payload"]["equipments"]}


async def test_matched_command_carries_attendu_ha_and_decision(cli, app):
    """AC1 — chaque commande retenue porte generic_type + attendu_ha + décision, retained=True."""
    state = JeedomCmd(id=2001, name="Etat", generic_type="LIGHT_STATE")
    slider = JeedomCmd(id=2002, name="Slider", generic_type="LIGHT_SLIDER")
    eq = JeedomEqLogic(id=200, name="Lampe", object_id=1, is_enable=True, cmds=[state, slider])
    snapshot = TopologySnapshot(
        timestamp="2026-07-17T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={200: eq},
    )
    mapping_res = MappingResult(
        ha_entity_type="light", confidence="sure", reason_code="light_on_off_brightness",
        jeedom_eq_id=200, ha_unique_id="light_200", ha_name="Lampe",
        capabilities=LightCapabilities(has_on_off=True, has_brightness=True),
        commands={"LIGHT_STATE": state, "LIGHT_SLIDER": slider},
    )
    equipments = await _get_equipments(
        cli, app, snapshot,
        {200: EligibilityResult(is_eligible=True, reason_code="eligible")},
        {200: mapping_res},
        {200: PublicationDecision(should_publish=True, reason="sure",
                                  mapping_result=mapping_res, active_or_alive=True)},
    )
    matched = equipments[200]["matched_commands"]
    assert len(matched) == 2
    for entry in matched:
        assert entry["generic_type"] in ("LIGHT_STATE", "LIGHT_SLIDER")
        assert entry["attendu_ha"] == "light"
        assert entry["mapping_decision"] == "light"
        assert entry["retained"] is True
        assert "type_override" not in entry  # pas d'override => pas de clé
    # AC4 — pas d'override publication => pas de clé publication_override
    assert "publication_override" not in equipments[200]


async def test_type_override_exposes_native_and_overridden(cli, app):
    """AC2 — override de TYPE : décision native ET surchargée visibles, additif au 4D."""
    state = JeedomCmd(id=3001, name="Etat", generic_type="LIGHT_STATE")
    slider = JeedomCmd(id=3002, name="Slider", generic_type="LIGHT_SLIDER")
    eq = JeedomEqLogic(id=201, name="Lampe forcee switch", object_id=1, is_enable=True,
                       cmds=[state, slider])
    snapshot = TopologySnapshot(
        timestamp="2026-07-17T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={201: eq},
    )
    # ha_entity_type = décision EFFECTIVE (surchargée) ; override_applied dans reason_details.
    mapping_res = MappingResult(
        ha_entity_type="switch", confidence="sure", reason_code="light_on_off_brightness",
        jeedom_eq_id=201, ha_unique_id="switch_201", ha_name="Lampe forcee switch",
        capabilities=LightCapabilities(has_on_off=True, has_brightness=True),
        commands={"LIGHT_STATE": state, "LIGHT_SLIDER": slider},
        reason_details={"override_applied": True, "override_source": "user"},
    )
    equipments = await _get_equipments(
        cli, app, snapshot,
        {201: EligibilityResult(is_eligible=True, reason_code="eligible")},
        {201: mapping_res},
        {201: PublicationDecision(should_publish=True, reason="sure",
                                  mapping_result=mapping_res, active_or_alive=True)},
    )
    # Décision native attendue = moteur brut (sans override) sur les mêmes commandes.
    expected_native = resolve_expected_ha(eq, snapshot).get("proposed_ha_entity_type")
    matched = equipments[201]["matched_commands"]
    assert len(matched) == 2
    for entry in matched:
        assert entry["mapping_decision"] == "switch"       # effective
        assert entry["attendu_ha"] == expected_native      # native (moteur brut)
        assert entry["type_override"]["effective"] == "switch"
        assert entry["type_override"]["native"] == expected_native
        assert entry["type_override"]["source"] == "user"
        assert expected_native != "switch"                 # native != surchargée
    # 4D eq-level inchangé : les champs canoniques restent présents et non pollués.
    for key in ("perimetre", "statut", "ecart", "cause_code"):
        assert key in equipments[201]


async def test_publication_override_consumes_16_3_reason_codes(cli, app):
    """AC4 — override de publication exposé en consommant EXACTEMENT les reason_codes 16.3."""
    state = JeedomCmd(id=4001, name="Etat", generic_type="LIGHT_STATE")
    slider = JeedomCmd(id=4002, name="Slider", generic_type="LIGHT_SLIDER")
    eq = JeedomEqLogic(id=202, name="Lampe forcee publication", object_id=1, is_enable=True,
                       cmds=[state, slider])
    snapshot = TopologySnapshot(
        timestamp="2026-07-17T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={202: eq},
    )
    mapping_res = MappingResult(
        ha_entity_type="light", confidence="ambiguous", reason_code="light_on_off_brightness",
        jeedom_eq_id=202, ha_unique_id="light_202", ha_name="Lampe forcee publication",
        capabilities=LightCapabilities(has_on_off=True, has_brightness=True),
        commands={"LIGHT_STATE": state, "LIGHT_SLIDER": slider},
    )
    pub = PublicationDecision(
        should_publish=True, reason="publication_forced",
        mapping_result=mapping_res, active_or_alive=True,
        reason_details={
            "publication_override_applied": True,
            "override_source": "user",
            "underlying_confidence": "ambiguous",
        },
    )
    equipments = await _get_equipments(
        cli, app, snapshot,
        {202: EligibilityResult(is_eligible=True, reason_code="eligible")},
        {202: mapping_res},
        {202: pub},
    )
    po = equipments[202]["publication_override"]
    assert po["reason_code"] == "publication_forced"  # reason_code 16.3, non réinventé
    assert po["override_source"] == "user"
    assert po["underlying_confidence"] == "ambiguous"  # confiance native jamais perdue


async def test_unmatched_command_is_rejected_and_read_only(cli, app):
    """AC1 — une commande couvrable non mappée est exposée rejetée (retained=False)."""
    state = JeedomCmd(id=5001, name="Etat", generic_type="LIGHT_STATE")
    slider = JeedomCmd(id=5002, name="Slider", generic_type="LIGHT_SLIDER")
    orphan = JeedomCmd(id=5003, name="Conso", generic_type="POWER")  # couvrable, non mappée
    eq = JeedomEqLogic(id=203, name="Lampe + conso", object_id=1, is_enable=True,
                       cmds=[state, slider, orphan])
    snapshot = TopologySnapshot(
        timestamp="2026-07-17T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={203: eq},
    )
    mapping_res = MappingResult(
        ha_entity_type="light", confidence="sure", reason_code="light_on_off_brightness",
        jeedom_eq_id=203, ha_unique_id="light_203", ha_name="Lampe + conso",
        capabilities=LightCapabilities(has_on_off=True, has_brightness=True),
        commands={"LIGHT_STATE": state, "LIGHT_SLIDER": slider},  # POWER non consommé
    )
    equipments = await _get_equipments(
        cli, app, snapshot,
        {203: EligibilityResult(is_eligible=True, reason_code="eligible")},
        {203: mapping_res},
        {203: PublicationDecision(should_publish=True, reason="sure",
                                  mapping_result=mapping_res, active_or_alive=True)},
    )
    unmatched = equipments[203]["unmatched_commands"]
    assert any(e["cmd_id"] == 5003 for e in unmatched)
    for entry in unmatched:
        assert entry["retained"] is False
        assert entry["attendu_ha"] is None
        assert entry["mapping_decision"] is None
