"""Tests Story 4.3 — Diagnostic centré in-scope, confiance en diagnostic uniquement,
traitement de "Partiellement publié".

Couvre :
- AC 1 : surface filtrée in_scope_equipments (perimetre=inclus uniquement)
- AC 4 : absorption "Partiellement publié" (statut=publie, ecart=false, cause_code=null)
- AC 6 : non-régression champs techniques dans la surface filtrée
"""

import pytest

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd, EligibilityResult
)
from models.mapping import MappingResult, PublicationDecision, LightCapabilities


# ---------------------------------------------------------------------------
# Helpers partagés
# ---------------------------------------------------------------------------

def _make_snapshot(eq_logics):
    return TopologySnapshot(
        timestamp="2026-03-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics=eq_logics,
    )


def _published_decision(mapping_res):
    return PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping_res,
        active_or_alive=True,
    )


def _light_mapping(eq_id, reason_code="sure", confidence="sure"):
    return MappingResult(
        ha_entity_type="light",
        confidence=confidence,
        reason_code=reason_code,
        jeedom_eq_id=eq_id,
        ha_unique_id=f"light_{eq_id}",
        ha_name=f"Lumiere {eq_id}",
        capabilities=LightCapabilities(has_on_off=True),
    )


# ---------------------------------------------------------------------------
# AC 1 — Surface filtrée in_scope_equipments (Task 7.1)
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    return create_app(local_secret="test_secret")


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def test_in_scope_equipments_filtrage_inclus_uniquement(cli, app):
    """AC 1 — La surface filtrée contient uniquement les équipements perimetre=inclus."""
    # 3 inclus + 2 exclus
    eq_inclus_1 = JeedomEqLogic(id=10, name="Lumière 1", object_id=1, is_enable=True)
    eq_inclus_2 = JeedomEqLogic(id=11, name="Lumière 2", object_id=1, is_enable=True)
    eq_inclus_3 = JeedomEqLogic(id=12, name="Lumière 3", object_id=1, is_enable=True)
    eq_exclu_piece = JeedomEqLogic(id=20, name="Exclu Pièce", object_id=1, is_excluded=True)
    eq_exclu_eq = JeedomEqLogic(id=21, name="Exclu Équip", object_id=1, is_excluded=True)

    app["topology"] = _make_snapshot({10: eq_inclus_1, 11: eq_inclus_2, 12: eq_inclus_3, 20: eq_exclu_piece, 21: eq_exclu_eq})

    m10 = _light_mapping(10)
    m11 = _light_mapping(11)
    m12 = _light_mapping(12)
    app["eligibility"] = {
        10: EligibilityResult(is_eligible=True, reason_code="eligible"),
        11: EligibilityResult(is_eligible=True, reason_code="eligible"),
        12: EligibilityResult(is_eligible=True, reason_code="eligible"),
        20: EligibilityResult(is_eligible=False, reason_code="excluded_object"),
        21: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }
    app["mappings"] = {10: m10, 11: m11, 12: m12}
    app["publications"] = {
        10: _published_decision(m10),
        11: _published_decision(m11),
        12: _published_decision(m12),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    assert resp.status == 200
    data = await resp.json()

    in_scope = data["payload"]["in_scope_equipments"]
    assert isinstance(in_scope, list)
    assert len(in_scope) == 3

    in_scope_ids = {eq["eq_id"] for eq in in_scope}
    assert in_scope_ids == {10, 11, 12}, f"Attendu {{10, 11, 12}}, obtenu {in_scope_ids}"

    # Tous les in-scope ont bien perimetre=inclus
    for eq in in_scope:
        assert eq["perimetre"] == "inclus", f"eq_id={eq['eq_id']} perimetre={eq['perimetre']}"


async def test_in_scope_equipments_sections_non_filtrees_intactes(cli, app):
    """AC 1 — payload.equipments contient tous les équipements (non filtré)."""
    eq_inclus = JeedomEqLogic(id=30, name="Inclus", object_id=1, is_enable=True)
    eq_exclu = JeedomEqLogic(id=31, name="Exclu", object_id=1, is_excluded=True)

    app["topology"] = _make_snapshot({30: eq_inclus, 31: eq_exclu})
    m30 = _light_mapping(30)
    app["eligibility"] = {
        30: EligibilityResult(is_eligible=True, reason_code="eligible"),
        31: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }
    app["mappings"] = {30: m30}
    app["publications"] = {30: _published_decision(m30)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    # Collection complète : 2 équipements (inclus + exclu)
    all_equipments = data["payload"]["equipments"]
    assert len(all_equipments) == 2
    all_ids = {eq["eq_id"] for eq in all_equipments}
    assert 30 in all_ids
    assert 31 in all_ids

    # Surface filtrée : 1 seul équipement
    in_scope = data["payload"]["in_scope_equipments"]
    assert len(in_scope) == 1
    assert in_scope[0]["eq_id"] == 30


async def test_in_scope_compteur_coherent(cli, app):
    """AC 1 — Le nombre d'équipements dans in_scope_equipments est cohérent avec inclus."""
    eq1 = JeedomEqLogic(id=40, name="Inc 1", object_id=1, is_enable=True)
    eq2 = JeedomEqLogic(id=41, name="Inc 2", object_id=1, is_enable=True)
    eq3 = JeedomEqLogic(id=42, name="Exclu", object_id=1, is_excluded=True)

    app["topology"] = _make_snapshot({40: eq1, 41: eq2, 42: eq3})
    m40 = _light_mapping(40)
    m41 = _light_mapping(41)
    app["eligibility"] = {
        40: EligibilityResult(is_eligible=True, reason_code="eligible"),
        41: EligibilityResult(is_eligible=True, reason_code="eligible"),
        42: EligibilityResult(is_eligible=False, reason_code="excluded_object"),
    }
    app["mappings"] = {40: m40, 41: m41}
    app["publications"] = {40: _published_decision(m40), 41: _published_decision(m41)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    in_scope = data["payload"]["in_scope_equipments"]
    summary_inclus = data["payload"]["summary"]["compteurs"]["inclus"]
    assert len(in_scope) == summary_inclus, (
        f"len(in_scope_equipments)={len(in_scope)} devrait == compteurs.inclus={summary_inclus}"
    )


async def test_in_scope_exclu_encore_publie_absent_de_surface_filtree(cli, app):
    """AC 1 direction 2 — équipement exclu encore publié (écart) : présent dans equipments, absent de in_scope."""
    eq_exclu = JeedomEqLogic(id=50, name="Exclu Encore Publié", object_id=1, is_excluded=True)
    app["topology"] = _make_snapshot({50: eq_exclu})
    m50 = _light_mapping(50)
    app["eligibility"] = {50: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}
    # Encore publié dans HA malgré exclusion → active_or_alive=True
    app["mappings"] = {50: m50}
    app["publications"] = {
        50: PublicationDecision(
            should_publish=False,
            reason="excluded_eqlogic",
            mapping_result=m50,
            active_or_alive=True,  # encore présent dans HA
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    all_equipments = data["payload"]["equipments"]
    assert any(eq["eq_id"] == 50 for eq in all_equipments), "eq 50 doit être dans equipments"

    in_scope = data["payload"]["in_scope_equipments"]
    assert not any(eq["eq_id"] == 50 for eq in in_scope), "eq 50 ne doit PAS être dans in_scope_equipments (exclu)"

    # Vérification du contrat 4D : ecart=true (direction 2)
    eq50 = next(eq for eq in all_equipments if eq["eq_id"] == 50)
    assert eq50["perimetre"].startswith("exclu_")
    assert eq50["statut"] == "publie"  # encore publié dans HA
    assert eq50["ecart"] is True


# ---------------------------------------------------------------------------
# AC 4 — Absorption "Partiellement publié" (Task 2.3 + 7.1)
# ---------------------------------------------------------------------------

async def test_absorption_partially_published_sure_mapping_partiel(cli, app):
    """AC 4 — Équipement published avec couverture partielle : statut=publie, ecart=false, cause_code=null."""
    cmd_on = JeedomCmd(id=3001, name="On", generic_type="LIGHT_ON")
    cmd_off = JeedomCmd(id=3002, name="Off", generic_type="LIGHT_OFF")
    cmd_slider = JeedomCmd(id=3003, name="Slider", generic_type="LIGHT_SLIDER")

    eq = JeedomEqLogic(id=60, name="Lumière Partielle", object_id=1, is_enable=True, cmds=[cmd_on, cmd_off, cmd_slider])
    app["topology"] = _make_snapshot({60: eq})

    m60 = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",  # only ON/OFF mapped → couverture partielle
        jeedom_eq_id=60,
        ha_unique_id="light_60",
        ha_name="Lumière Partielle",
        commands={"LIGHT_ON": cmd_on, "LIGHT_OFF": cmd_off},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["eligibility"] = {60: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {60: m60}
    app["publications"] = {60: _published_decision(m60)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    eq60 = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 60)

    # AC 4 — absorption : statut=publie, ecart=false, cause_code=null
    assert eq60["perimetre"] == "inclus"
    assert eq60["statut"] == "publie"
    assert eq60["ecart"] is False
    assert eq60["cause_code"] is None

    # L'information de couverture partielle reste via les commandes
    assert len(eq60["matched_commands"]) >= 2
    assert len(eq60["unmatched_commands"]) >= 1

    # Présent dans in_scope_equipments
    in_scope_ids = {eq["eq_id"] for eq in data["payload"]["in_scope_equipments"]}
    assert 60 in in_scope_ids


# ---------------------------------------------------------------------------
# AC 6 — Non-régression champs techniques dans la surface filtrée (Task 7.3)
# ---------------------------------------------------------------------------

async def test_in_scope_champs_techniques_presents(cli, app):
    """AC 6 — Les champs techniques restent présents dans in_scope_equipments."""
    eq = JeedomEqLogic(id=70, name="Lumière Technique", object_id=1, is_enable=True)
    app["topology"] = _make_snapshot({70: eq})
    m70 = _light_mapping(70, reason_code="sure", confidence="sure")
    app["eligibility"] = {70: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {70: m70}
    app["publications"] = {70: _published_decision(m70)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    in_scope = data["payload"]["in_scope_equipments"]
    assert len(in_scope) == 1
    eq70 = in_scope[0]

    # Champs techniques obligatoires
    assert "status_code" in eq70, "status_code doit être présent dans in_scope_equipments"
    assert "confidence" in eq70, "confidence doit être présent dans in_scope_equipments"
    assert "reason_code" in eq70, "reason_code doit être présent dans in_scope_equipments"
    assert "detail" in eq70, "detail doit être présent dans in_scope_equipments"
    assert "remediation" in eq70, "remediation doit être présent dans in_scope_equipments"
    assert "v1_limitation" in eq70, "v1_limitation doit être présent dans in_scope_equipments"

    # Champs 4D aussi présents
    assert eq70["perimetre"] == "inclus"
    assert eq70["statut"] in ("publie", "non_publie")
    assert isinstance(eq70["ecart"], bool)
