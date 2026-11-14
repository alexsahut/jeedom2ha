"""Front v3 — Lot 4a : PREUVE de non-régression de la projection des scénarios à la mise à jour.

Décision d'Alexandre (option B) : les scénarios déjà publiés le restent. Sur une installation mise
à jour, la migration inscrit tous les scénarios lisibles dans `publishedScenarios` ; le PHP envoie
alors `published: true` pour chacun. La trace MQTT complète d'une synchro (topic, payload brut octet
pour octet, qos, retain ; découverte, disponibilités et purge comprises) doit rester celle du code
de base.

La ligne de base `scenarios_upgrade_baseline.json` est capturée sur le code de base (bea9062) AVANT
toute modification du Lot 4a, avec la charge d'un PHP d'avant le Lot 4a (aucun champ de
publication). Elle ne se régénère que volontairement (`JEEDOM2HA_LOT4A_REGEN=1`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from transport.http_server import create_app

from .front_v3_lot4a_corpus import (
    RetainingRecordingBridge,
    deleted_scenario_retained,
    legacy_scenarios,
    lot4a_scenarios,
    sync_body,
    upgrade_scenarios,
)

SECRET = "test-secret-lot4a"
H = {"X-Local-Secret": SECRET}
BASELINE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "front_v3_lot4a" / "scenarios_upgrade_baseline.json"
)


async def _trace(aiohttp_client, scenarios, request_id="lot4a-baseline") -> List[dict]:
    app = create_app(local_secret=SECRET)
    bridge = RetainingRecordingBridge(deleted_scenario_retained())
    app["mqtt_bridge"] = bridge
    cli = await aiohttp_client(app)
    resp = await cli.post("/action/sync", json=sync_body(scenarios, request_id), headers=H)
    assert resp.status == 200, await resp.text()
    return bridge.calls


def _baseline(trace: List[dict]) -> List[dict]:
    if not BASELINE_PATH.exists():
        if not os.environ.get("JEEDOM2HA_LOT4A_REGEN"):
            raise AssertionError(f"Ligne de base absente ({BASELINE_PATH}) : JEEDOM2HA_LOT4A_REGEN=1 pour la créer.")
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(trace, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


async def test_charge_d_avant_le_lot_4a_trace_identique(aiohttp_client):
    """PHP ancien (aucun champ `published`) : le démon publie comme avant, octet pour octet."""
    trace = await _trace(aiohttp_client, legacy_scenarios())
    assert trace == await _trace(aiohttp_client, legacy_scenarios()), "trace non déterministe"
    scenario_topics = {c["topic"] for c in trace if "scenario" in c["topic"]}
    assert len(scenario_topics) >= 9, "scène trop pauvre : 4 boutons, 4 disponibilités, 1 purge attendus"
    assert trace == _baseline(trace), "la projection vers Home Assistant a changé (topics ou payloads)"
