"""Story 25.2 (AC17, Task 1.2) — instantané octet pour octet de GET /system/mapping_overrides/{eq_id}.

Écrit et vert AVANT tout refactor de `_build_mapping_override_tree` : le réemploi du même
constructeur par la route agrégée ne doit changer aucun octet de la réponse unitaire.
Régénérer l'instantané (jamais sans décision) : `J2HA_UPDATE_SNAPSHOT=1 pytest <ce fichier>`.
"""

import json
import os
from pathlib import Path

import pytest

from transport.http_server import create_app
from .corpus_25_2 import ALL_EQ_IDS, SECRET, apply_corpus

SNAPSHOT = Path(__file__).resolve().parent.parent / "fixtures" / "story_25_2_mapping_override_snapshot.json"


@pytest.fixture
def app(tmp_path):
    return apply_corpus(create_app(local_secret=SECRET), tmp_path)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _raw_bodies(cli):
    bodies = {}
    for eq_id in ALL_EQ_IDS:
        resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers={"X-Local-Secret": SECRET})
        assert resp.status == 200
        bodies[str(eq_id)] = (await resp.read()).decode("utf-8")
    return bodies


async def test_unit_tree_response_is_byte_identical_to_snapshot(cli):
    bodies = await _raw_bodies(cli)
    if os.environ.get("J2HA_UPDATE_SNAPSHOT") == "1":
        SNAPSHOT.write_text(json.dumps(bodies, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert sorted(bodies) == sorted(expected)
    for eq_id, body in bodies.items():
        assert body == expected[eq_id], f"réponse unitaire modifiée pour eq {eq_id}"


async def test_snapshot_corpus_is_representative(cli):
    """Le corpus couvre bien les formes d'état (sinon l'instantané ne protège rien)."""
    trees = {k: json.loads(v)["payload"] for k, v in (await _raw_bodies(cli)).items()}
    assert any(t["sync_status"]["published_in_ha"] for t in trees.values())
    assert any(t["sync_status"]["override_pending"] for t in trees.values())
    assert any(not t["commands"] for t in trees.values())
    assert any(not t["mapped"] for t in trees.values())
    assert any(len(t["entities"]) > 1 for t in trees.values())
    assert any(c.get("override_types_allowed") for t in trees.values() for c in t["commands"])
