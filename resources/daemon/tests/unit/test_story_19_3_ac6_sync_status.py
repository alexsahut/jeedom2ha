"""Story 19.3 — AC6 : le triptyque expose `sync_status` — comparaison de la dernière décision
SYNCÉE (`app["publications"]`, posée par le dernier `/action/sync`) à la décision COURANTE
(overrides persistés actuels). `override_pending=True` signale un override sauvegardé mais pas
encore appliqué par un sync (badge « pas encore appliqué » côté UI, AC6/desktop JS).
"""

import pytest

from transport.http_server import create_app
from mapping.overrides import save_equipment_override
from models.mapping import PublicationDecision
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd,
)

SECRET = "test_secret_19_3_ac6"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _plain_light(eq_id=90400):
    eq = JeedomEqLogic(
        id=eq_id, name="Lampe simple", object_id=1, eq_type_name="light",
        cmds=[
            JeedomCmd(id=eq_id * 10 + 1, name="On", type="action", sub_type="other", generic_type="LIGHT_ON"),
            JeedomCmd(id=eq_id * 10 + 2, name="Off", type="action", sub_type="other", generic_type="LIGHT_OFF"),
            JeedomCmd(id=eq_id * 10 + 3, name="Etat", type="info", sub_type="binary", generic_type="LIGHT_STATE"),
        ],
    )
    snapshot = TopologySnapshot(
        timestamp="2026-09-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={eq_id: eq},
    )
    return snapshot, eq


async def test_ac6_sync_status_no_pending_override(cli, app, tmp_path):
    """Décision syncée == décision courante (aucun override) → override_pending=False."""
    snapshot, eq = _plain_light()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    app["publications"] = {eq.id: PublicationDecision(should_publish=True, reason="sure")}

    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    payload = (await resp.json())["payload"]

    assert payload["sync_status"] == {
        "synced_should_publish": True,
        "current_should_publish": True,
        "override_pending": False,
    }


async def test_ac6_sync_status_override_pending_after_unsynced_exclusion(cli, app, tmp_path):
    """Un override d'exclusion sauvegardé mais pas encore appliqué par un sync : la décision
    syncée dit encore "publié", la décision courante dit "non publié" → override_pending=True."""
    snapshot, eq = _plain_light()
    app["topology"] = snapshot
    data_dir = str(tmp_path)
    app["data_dir"] = data_dir
    app["publications"] = {eq.id: PublicationDecision(should_publish=True, reason="sure")}

    save_equipment_override(eq.id, {"publication_override": "exclude"}, data_dir)

    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    payload = (await resp.json())["payload"]

    assert payload["sync_status"] == {
        "synced_should_publish": True,
        "current_should_publish": False,
        "override_pending": True,
    }


async def test_ac6_sync_status_no_prior_sync(cli, app, tmp_path):
    """Équipement jamais synchronisé (absent de `app["publications"]`) : synced_should_publish
    est `None`, jamais un faux `override_pending=True` par comparaison à `None`."""
    snapshot, eq = _plain_light()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    app["publications"] = {}

    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    payload = (await resp.json())["payload"]

    assert payload["sync_status"]["synced_should_publish"] is None
    assert payload["sync_status"]["override_pending"] is False
