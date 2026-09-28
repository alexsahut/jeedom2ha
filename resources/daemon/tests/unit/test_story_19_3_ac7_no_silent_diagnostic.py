"""Story 19.3 — AC7 : aucun silence dans le diagnostic. Chaque commande de chaque
équipement porte une `CommandDecision` (jamais `None`), un `publication_reason`, et ce
code a un libellé français dans `REASON_LABELS` (desktop/js). Sur le corpus doré (59
équipements), zéro commande sans raison — y compris les commandes non couvertes par le
mapping (`command_not_covered`, avant Story 19.3 le diagnostic valait `None`,
`http_server.py:2496`).
"""

import json
import re
from pathlib import Path

import pytest

from transport.http_server import create_app
from models.topology import TopologySnapshot

SECRET = "test_secret_19_3_ac7"

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus"
SYNC_FIXTURE_PATH = FIXTURES_DIR / "sync_payload.json"

DESKTOP_JS_PATH = (
    Path(__file__).resolve().parents[4] / "desktop" / "js" / "jeedom2ha_mapping_override.js"
)


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


def _reason_labels_from_js():
    """Extrait les clés de `REASON_LABELS` directement du fichier JS source (pas de
    duplication de la liste en dur ici : une clé ajoutée/retirée côté JS doit faire
    échouer ce test si la surface Python en dépend)."""
    text = DESKTOP_JS_PATH.read_text(encoding="utf-8")
    start = text.index("var REASON_LABELS = {")
    end = text.index("\n  };", start)
    block = text[start:end]
    return set(re.findall(r"^\s*(\w+):\s*'", block, flags=re.MULTILINE))


async def test_ac7_golden_59_zero_command_without_diagnostic_or_reason(cli, app, tmp_path):
    """Sur les 59 équipements du corpus doré, chaque commande de chaque équipement a un
    `diagnostic` non `None` et un `publication_reason` non vide — jamais de silence."""
    snapshot = _golden_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    missing_diagnostic = []
    empty_reason = []
    for eq_id in snapshot.eq_logics:
        resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=_headers())
        assert resp.status == 200, f"eq {eq_id} : statut HTTP inattendu {resp.status}"
        payload = (await resp.json())["payload"]
        for row in payload["commands"]:
            if row["diagnostic"] is None:
                missing_diagnostic.append((eq_id, row["jeedom_cmd_id"]))
                continue
            reason = row["diagnostic"].get("publication_reason")
            if not reason:
                empty_reason.append((eq_id, row["jeedom_cmd_id"]))

    assert missing_diagnostic == [], f"commandes sans diagnostic : {missing_diagnostic}"
    assert empty_reason == [], f"commandes avec raison vide : {empty_reason}"


async def test_ac7_golden_59_blocking_reasons_all_have_french_label(cli, app, tmp_path):
    """Chaque `publication_reason` d'une commande dont `should_publish=False` a un libellé
    français dans `REASON_LABELS` (desktop/js) — une raison de blocage n'est jamais un code
    brut affiché tel quel à l'utilisateur."""
    snapshot = _golden_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    labels = _reason_labels_from_js()

    unlabeled = []
    for eq_id in snapshot.eq_logics:
        resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=_headers())
        payload = (await resp.json())["payload"]
        for row in payload["commands"]:
            diag = row["diagnostic"]
            if diag["should_publish"] is False and diag["publication_reason"] not in labels:
                unlabeled.append((eq_id, row["jeedom_cmd_id"], diag["publication_reason"]))

    assert unlabeled == [], f"raisons de blocage sans libellé français : {unlabeled}"


async def test_ac7_uncovered_command_gets_command_not_covered_reason(cli, app, tmp_path):
    """Une commande d'un équipement mappé mais non couverte par le mapping (ex. commande
    d'info secondaire hors mapping primaire/secondaire) reçoit explicitement le code
    `command_not_covered` — jamais un diagnostic `None` (régression CC-03/AC7,
    `http_server.py:2496` avant Story 19.3). On identifie le cas directement par le
    `publication_reason` (source de vérité `evaluation.command_decisions`), pas par le
    champ `row["covered"]` de l'arbre — celui-ci utilise sa propre détection de secondaire
    par `reason_details["cmd_id"]` (`_secondary_mapping_by_cmd`) qui peut diverger de la
    couverture réelle retenue par `evaluate_equipment()` (cf. rapport Reprise 2 : cas
    "Charge solaire On" eq 583, `should_publish=True`/`covered=False` simultanés)."""
    snapshot = _golden_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    found_uncovered = False
    for eq_id in snapshot.eq_logics:
        resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=_headers())
        payload = (await resp.json())["payload"]
        for row in payload["commands"]:
            if row["diagnostic"]["publication_reason"] == "command_not_covered":
                found_uncovered = True
                assert row["diagnostic"]["should_publish"] is False
                assert row["diagnostic"]["ha_entity_type"] is None

    assert found_uncovered, (
        "le corpus doré doit contenir au moins une commande command_not_covered pour que ce "
        "test exerce réellement le cas AC7"
    )
