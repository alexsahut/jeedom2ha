"""Story 19.3 (P1, relecture ClaudeBox PR #176 tour 2) — contrat `covered:false` / raison.

La surface JS (`shouldShowUncoveredLabel`, `jeedom2ha_mapping_override.js`) n'affiche le
libellé générique « non couverte par un mapping » que quand AUCUNE vraie cause n'accompagne
`covered:false` (absence de diagnostic, ou `publication_reason == "command_not_covered"") —
sinon elle affiche le vrai diagnostic (raison d'exclusion/inéligibilité amont, I4). Ce contrat
suppose que le backend ne produit JAMAIS `covered:false` avec une autre raison que
`command_not_covered` ou l'une des 6 raisons d'inéligibilité/exclusion amont connues
(`models/topology.py`, `_EXCLUSION_SOURCE_TO_REASON` + `assess_eligibility`).

Ce test vérifie ce contrat sur les 59 équipements du corpus doré : si le backend venait à
introduire une SEPTIÈME raison sur une ligne `covered:false`, ce test échoue AVANT que la
surface JS ne l'affiche silencieusement comme « non couverte » à tort.
"""

import json
from pathlib import Path

import pytest

from transport.http_server import create_app
from models.topology import TopologySnapshot

SECRET = "test_secret_19_3_p1"

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus"
SYNC_FIXTURE_PATH = FIXTURES_DIR / "sync_payload.json"

# Story 4.3 (topology.py `_EXCLUSION_SOURCE_TO_REASON`) + evaluate_equipment.py
# (`_ELIGIBILITY_REASON_ALIAS` : `no_supported_generic_type` -> `no_generic_type_configured`)
# — les seules raisons d'inéligibilité/exclusion amont qui peuvent légitimement accompagner
# `covered:false` avec une vraie cause à afficher (au lieu du libellé générique).
ELIGIBILITY_REASON_CODES = {
    "excluded_eqlogic",
    "excluded_plugin",
    "excluded_object",
    "disabled_eqlogic",
    "no_commands",
    "no_generic_type_configured",
}

ALLOWED_COVERED_FALSE_REASONS = ELIGIBILITY_REASON_CODES | {"command_not_covered"}


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _golden_snapshot():
    payload = json.loads(SYNC_FIXTURE_PATH.read_text(encoding="utf-8"))
    return TopologySnapshot.from_jeedom_payload(payload)


async def test_covered_false_rows_only_carry_known_uncovered_or_eligibility_reasons(cli, app, tmp_path):
    """Sur les 59 équipements du corpus doré, toute ligne `covered:false` porte un
    `publication_reason` parmi `command_not_covered` ou l'une des 6 raisons d'éligibilité
    amont connues — jamais une autre raison qui casserait silencieusement le contrat
    `shouldShowUncoveredLabel` côté surface JS."""
    snapshot = _golden_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    unexpected = []
    covered_false_seen = 0
    for eq_id in snapshot.eq_logics:
        resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=_headers())
        assert resp.status == 200, f"eq {eq_id} : statut HTTP inattendu {resp.status}"
        payload = (await resp.json())["payload"]
        for row in payload["commands"]:
            if row["covered"] is not False:
                continue
            covered_false_seen += 1
            reason = row["diagnostic"]["publication_reason"] if row["diagnostic"] else None
            if reason not in ALLOWED_COVERED_FALSE_REASONS:
                unexpected.append((eq_id, row["jeedom_cmd_id"], reason))

    assert unexpected == [], f"raison inattendue sur une ligne covered:false : {unexpected}"
    assert covered_false_seen > 0, (
        "le corpus doré doit contenir au moins une ligne covered:false pour que ce test "
        "exerce réellement le contrat"
    )
