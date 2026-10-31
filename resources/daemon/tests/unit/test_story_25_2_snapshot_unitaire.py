"""Story 25.2 (Task 1.2, AC17) — instantané octet pour octet de
`GET /system/mapping_overrides/{eq_id}` sur le corpus fictif, écrit AVANT tout refactor de
`_build_mapping_override_tree` : il doit passer avant comme après.

Régénérer volontairement (jamais pour « faire passer » un refactor) :
    JEEDOM2HA_UPDATE_SNAPSHOT=1 python3 -m pytest resources/daemon/tests/unit/test_story_25_2_snapshot_unitaire.py
"""

import os
from pathlib import Path

import pytest

from transport.http_server import create_app
from .story_25_2_corpus import build_corpus_topology, populate_app

SECRET = "test_secret"
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "story_25_2_unit_tree"
EQ_IDS = sorted(build_corpus_topology().eq_logics)


@pytest.fixture
def app(tmp_path):
    app = create_app(local_secret=SECRET)
    populate_app(app, tmp_path)
    return app


@pytest.mark.parametrize("eq_id", EQ_IDS)
async def test_arbre_unitaire_octet_pour_octet(aiohttp_client, app, eq_id):
    cli = await aiohttp_client(app)
    resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers={"X-Local-Secret": SECRET})
    assert resp.status == 200
    body = await resp.read()
    path = SNAPSHOT_DIR / f"{eq_id}.json"
    if os.environ.get("JEEDOM2HA_UPDATE_SNAPSHOT") == "1":
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    assert body == path.read_bytes()
