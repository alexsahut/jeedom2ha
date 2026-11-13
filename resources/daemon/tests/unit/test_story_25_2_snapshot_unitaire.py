"""Story 25.2 (Task 1.2, AC17) — instantané octet pour octet de
`GET /system/mapping_overrides/{eq_id}` sur le corpus fictif, écrit AVANT tout refactor de
`_build_mapping_override_tree` : il doit passer avant comme après.

Régénérer volontairement (jamais pour « faire passer » un refactor) :
    JEEDOM2HA_UPDATE_SNAPSHOT=1 python3 -m pytest resources/daemon/tests/unit/test_story_25_2_snapshot_unitaire.py
"""

import json
import os
from pathlib import Path

import pytest

from transport.http_server import create_app
from .story_25_2_corpus import build_corpus_topology, populate_app

SECRET = "test_secret"
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "story_25_2_unit_tree"
EQ_IDS = sorted(build_corpus_topology().eq_logics)

# Front v2 Lot 3 — champs ADDITIFS de la route unitaire (contrat front v2, section 4). Les
# instantanés (une ligne JSON sous resources/daemon/) ne peuvent pas être réécrits sans retirer
# de ligne (garde 25.4) : on compare donc la réponse privée de ces seuls champs, octet pour octet,
# à l'instantané d'origine. Leur forme est vérifiée par test_front_v2_lot3_champs_additifs.py.
LOT3_ROOT_KEYS = ("hints",)
LOT3_ENTITY_KEYS = (
    "ha_unique_id", "ha_default_entity_id", "ha_name", "ha_device_name", "ha_device_class",
    "ha_unit", "ha_controllable", "ha_capabilities",
)
LOT3_COMMAND_KEYS = ("cmd_type", "cmd_sub_type", "linked_state_cmd_id")


def _sans_champs_lot3(body: bytes) -> bytes:
    """Retire exactement les champs du Lot 3 (tous présents) et resérialise comme aiohttp."""
    document = json.loads(body)
    tree = document["payload"]
    for key in LOT3_ROOT_KEYS:
        tree.pop(key)
    for entity in tree["entities"]:
        for key in LOT3_ENTITY_KEYS:
            entity.pop(key)
    for command in tree["commands"]:
        for key in LOT3_COMMAND_KEYS:
            command.pop(key)
    return json.dumps(document).encode("utf-8")


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
    body = _sans_champs_lot3(body)  # Front v2 Lot 3 : voir LOT3_ROOT_KEYS
    path = SNAPSHOT_DIR / f"{eq_id}.json"
    if os.environ.get("JEEDOM2HA_UPDATE_SNAPSHOT") == "1":
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    assert body == path.read_bytes()
