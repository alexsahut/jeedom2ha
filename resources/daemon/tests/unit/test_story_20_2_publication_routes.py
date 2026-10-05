"""Story 20.2 review point 5: publication override HTTP contract."""
import pytest

from mapping.overrides import list_equipment_overrides, list_overrides, save_override
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from transport.http_server import create_app

SECRET = "x2c"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _snapshot():
    eq = JeedomEqLogic(id=201, name="x", object_id=1, eq_type_name="light", cmds=[
        JeedomCmd(id=2011, name="on", type="action", sub_type="other", generic_type="LIGHT_ON"),
        JeedomCmd(id=2012, name="off", type="action", sub_type="other", generic_type="LIGHT_OFF"),
        JeedomCmd(id=2013, name="state", type="info", sub_type="binary", generic_type="LIGHT_STATE"),
    ])
    other = JeedomEqLogic(id=202, name="y", object_id=1, eq_type_name="light", cmds=[
        JeedomCmd(id=2021, name="state", type="info", sub_type="binary", generic_type="LIGHT_STATE"),
        JeedomCmd(id=2022, name="x", type="action", sub_type="other", generic_type=None)])
    return TopologySnapshot(timestamp="2026-10-05T00:00:00Z", objects={1: JeedomObject(id=1, name="r")}, eq_logics={201: eq, 202: other}), eq, other


async def test_publication_save_auth_validation_not_found_and_persistence(cli, app, tmp_path):
    snapshot, eq, _ = _snapshot()
    app["topology"], app["data_dir"] = snapshot, str(tmp_path)
    url = "/action/publication_override"
    assert (await cli.post(url, json={"payload": {}})).status == 401
    for payload in ({"jeedom_eq_id": True, "publication_policy": "exclude"},
                    {"jeedom_eq_id": eq.id, "jeedom_cmd_id": "2011", "publication_policy": "exclude"},
                    {"jeedom_eq_id": eq.id, "publication_policy": "bad"}):
        assert (await cli.post(url, headers=_headers(), json={"payload": payload})).status == 400
    assert (await cli.post(url, headers=_headers(), json={"payload": {"jeedom_eq_id": 999, "publication_policy": "exclude"}})).status == 404
    assert (await cli.post(url, headers=_headers(), json={"payload": {"jeedom_eq_id": eq.id, "jeedom_cmd_id": 999, "publication_policy": "exclude"}})).status == 404
    response = await cli.post(url, headers=_headers(), json={"payload": {"jeedom_eq_id": eq.id, "jeedom_cmd_id": 2011, "publication_policy": "force_publish"}})
    assert response.status == 200
    assert list_overrides(str(tmp_path))["201:2011"]["publication_override"] == "force_publish"
    response = await cli.post(url, headers=_headers(), json={"payload": {"jeedom_eq_id": eq.id, "publication_policy": "exclude"}})
    assert response.status == 200
    assert list_equipment_overrides(str(tmp_path))["201"]["publication_override"] == "exclude"


async def test_publication_save_refuses_command_without_entity(cli, app, tmp_path):
    snapshot, _, other = _snapshot()
    app["topology"], app["data_dir"] = snapshot, str(tmp_path)
    response = await cli.post("/action/publication_override", headers=_headers(), json={"payload": {
        "jeedom_eq_id": other.id, "jeedom_cmd_id": 2022, "publication_policy": "exclude",
    }})
    assert response.status == 409


async def test_publication_revert_entity_and_equipment_scope(cli, app, tmp_path):
    snapshot, eq, other = _snapshot()
    app["topology"], app["data_dir"] = snapshot, str(tmp_path)
    for cmd_id in (2011, 2012):
        save_override(eq.id, cmd_id, {"ha_entity_type": "switch", "publication_override": "exclude"}, str(tmp_path))
    save_override(other.id, 2021, {"ha_entity_type": "sensor", "publication_override": "exclude"}, str(tmp_path))
    url = "/action/publication_override_revert"
    assert (await cli.post(url, json={"payload": {"jeedom_eq_id": eq.id}})).status == 401
    assert (await cli.post(url, headers=_headers(), json={"payload": {"jeedom_eq_id": eq.id, "jeedom_cmd_id": "x"}})).status == 400
    assert (await cli.post(url, headers=_headers(), json={"payload": {"jeedom_eq_id": 999}})).status == 404
    response = await cli.post(url, headers=_headers(), json={"payload": {"jeedom_eq_id": eq.id, "jeedom_cmd_id": 2011}})
    assert response.status == 200
    assert "201:2011" not in list_overrides(str(tmp_path))
    assert "201:2012" not in list_overrides(str(tmp_path))
    assert list_overrides(str(tmp_path))["202:2021"]["publication_override"] == "exclude"
    response = await cli.post(url, headers=_headers(), json={"payload": {"jeedom_eq_id": eq.id}})
    assert response.status == 200
    assert "201:2012" not in list_overrides(str(tmp_path))
    assert list_overrides(str(tmp_path))["202:2021"]["ha_entity_type"] == "sensor"
