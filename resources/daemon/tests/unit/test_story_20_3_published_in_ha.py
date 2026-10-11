"""Story 20.3 (R2-1) — `sync_status.published_in_ha` : présence réelle dans HA, exposée par l'arbre
`GET /system/mapping_overrides/{eq_id}` avec `_is_currently_published_in_ha` (la fonction que les actions
publier/supprimer utilisent). Champ additif, lecture seule, aucune décision recalculée.
"""

import pytest

from transport.http_server import create_app
from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot

SECRET = "test_secret_20_3_pih"
EQ_ID = 90500


@pytest.fixture
def app(tmp_path):
    application = create_app(local_secret=SECRET)
    eq = JeedomEqLogic(
        id=EQ_ID, name="Lampe simple", object_id=1, eq_type_name="light",
        cmds=[
            JeedomCmd(id=EQ_ID * 10 + 1, name="On", type="action", sub_type="other", generic_type="LIGHT_ON"),
            JeedomCmd(id=EQ_ID * 10 + 2, name="Off", type="action", sub_type="other", generic_type="LIGHT_OFF"),
            JeedomCmd(id=EQ_ID * 10 + 3, name="Etat", type="info", sub_type="binary", generic_type="LIGHT_STATE"),
        ],
    )
    application["topology"] = TopologySnapshot(
        timestamp="2026-09-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Pièce A")},
        eq_logics={EQ_ID: eq},
    )
    application["data_dir"] = str(tmp_path)
    return application


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _published_in_ha(cli):
    resp = await cli.get(f"/system/mapping_overrides/{EQ_ID}", headers={"X-Local-Secret": SECRET})
    assert resp.status == 200
    return (await resp.json())["payload"]["sync_status"]["published_in_ha"]


def _secondary(discovery_published):
    ref = PublicationDecision(should_publish=True, reason="sure", active_or_alive=False,
                              discovery_published=discovery_published)
    return MappingResult(ha_entity_type="sensor", confidence="sure", reason_code="sure_mapping",
                         jeedom_eq_id=EQ_ID, ha_unique_id=f"jeedom2ha_eq_{EQ_ID}_s", ha_name="Secondaire", capabilities=LightCapabilities(has_on_off=True),
                         publication_decision_ref=ref)


def _primary(secondaries):
    return MappingResult(ha_entity_type="light", confidence="sure", reason_code="sure_mapping",
                         jeedom_eq_id=EQ_ID, ha_unique_id=f"jeedom2ha_eq_{EQ_ID}", ha_name="Principal", capabilities=LightCapabilities(has_on_off=True),
                         additional_mappings=secondaries)


async def test_principal_publie(cli, app):
    app["publications"] = {EQ_ID: PublicationDecision(should_publish=True, reason="sure")}
    assert await _published_in_ha(cli) is True


async def test_principal_refuse_secondaire_publie(cli, app):
    """Forme 579/585 : principal refusé (donc `synced_should_publish` False), secondaire publié."""
    primary = _primary([_secondary(True)])
    app["publications"] = {EQ_ID: PublicationDecision(
        should_publish=False, reason="ha_missing_command_topic", active_or_alive=False,
        discovery_published=False, mapping_result=primary)}
    resp = await cli.get(f"/system/mapping_overrides/{EQ_ID}", headers={"X-Local-Secret": SECRET})
    status = (await resp.json())["payload"]["sync_status"]
    assert status["synced_should_publish"] is False
    assert status["published_in_ha"] is True


async def test_principal_refuse_secondaire_non_publie(cli, app):
    primary = _primary([_secondary(False)])
    app["publications"] = {EQ_ID: PublicationDecision(
        should_publish=False, reason="ha_missing_command_topic", active_or_alive=False,
        mapping_result=primary)}
    assert await _published_in_ha(cli) is False


async def test_depublication_en_attente(cli, app):
    app["publications"] = {EQ_ID: PublicationDecision(
        should_publish=False, reason="publication_excluded_eqlogic", active_or_alive=False)}
    app["pending_discovery_unpublish"] = {EQ_ID: "light"}
    assert await _published_in_ha(cli) is True


async def test_jamais_publie(cli, app):
    app["publications"] = {}
    assert await _published_in_ha(cli) is False
