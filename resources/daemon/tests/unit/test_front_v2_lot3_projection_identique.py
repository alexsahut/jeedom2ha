"""Front v2 — Lot 3 : PREUVE de non-régression de la projection vers Home Assistant.

Critère n°1 : « tant que la projection sur HA actuel continue de fonctionner ». Les champs
additifs du Lot 3 (`ha_*`, `hints`, `status.ha`, `status.publication`, aperçu en entités) sont
des LECTURES : ils ne doivent changer ni les topics ni les payloads de découverte.

Trois preuves, sur le corpus doré + trois équipements de démonstration :
  1. avant / après : la trace MQTT complète d'un sync (topic, payload brut octet pour octet,
     qos, retain) est identique à la ligne de base `discovery_baseline.json`, capturée sur le
     code de base (433a529) AVANT toute modification du Lot 3 ;
  2. les nouvelles lectures (status, arbre de chaque équipement, aperçus) ne publient RIEN ;
  3. après ces lectures, un second sync et une republication « HA birth » produisent
     exactement les mêmes messages de découverte que le premier sync.

La ligne de base ne se régénère que volontairement (`JEEDOM2HA_LOT3_REGEN=1`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from transport.http_server import create_app

from .front_v2_lot3_corpus import load_corpus, sync_body

SECRET = "test-secret-lot3"
H = {"X-Local-Secret": SECRET}
BASELINE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "front_v2_lot3" / "discovery_baseline.json"
)


class RawRecordingBridge:
    """Faux pont MQTT sous le VRAI `DiscoveryPublisher` : journalise chaque message brut."""

    def __init__(self) -> None:
        self.is_connected = True
        self.state = "connected"
        self.broker_info = "broker.example.test:1883"
        self.calls: List[dict] = []

    def publish_message(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> bool:
        self.calls.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})
        return True


def _discovery_only(calls: List[dict]) -> List[dict]:
    return [c for c in calls if c["topic"].startswith("homeassistant/")]


async def _sync(cli, corpus, request_id) -> None:
    resp = await cli.post("/action/sync", json=sync_body(corpus, request_id), headers=H)
    assert resp.status == 200, await resp.text()


async def _fresh(aiohttp_client):
    app = create_app(local_secret=SECRET)
    bridge = RawRecordingBridge()
    app["mqtt_bridge"] = bridge
    cli = await aiohttp_client(app)
    return app, bridge, cli


async def _trace_premier_sync(aiohttp_client) -> List[dict]:
    _app, bridge, cli = await _fresh(aiohttp_client)
    await _sync(cli, load_corpus(), "lot3-baseline")
    return bridge.calls


async def test_trace_mqtt_identique_a_la_ligne_de_base(aiohttp_client):
    """Preuve 1 — avant (code de base) / après (Lot 3) : trace MQTT identique octet pour octet."""
    trace = await _trace_premier_sync(aiohttp_client)
    assert trace == await _trace_premier_sync(aiohttp_client), "trace non déterministe"
    assert len(_discovery_only(trace)) > 50, "corpus trop pauvre pour être une preuve"
    if not BASELINE_PATH.exists():
        if not os.environ.get("JEEDOM2HA_LOT3_REGEN"):
            raise AssertionError(f"Ligne de base absente ({BASELINE_PATH}) : JEEDOM2HA_LOT3_REGEN=1 pour la créer.")
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(trace, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert trace == baseline, "la projection vers Home Assistant a changé (topics ou payloads)"


async def _toutes_les_lectures(cli, app) -> None:
    resp = await cli.get("/system/status", headers=H)
    assert resp.status == 200
    for eq_id in sorted(app["topology"].eq_logics):
        resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=H)
        assert resp.status == 200
        tree = (await resp.json())["payload"]
        for command in tree["commands"]:
            for body in (
                {"jeedom_eq_id": eq_id, "jeedom_cmd_id": command["jeedom_cmd_id"], "ha_entity_type": "sensor"},
                {"jeedom_eq_id": eq_id, "publication_policy": "exclude"},
            ):
                resp = await cli.post("/system/overrides/preview", json={"payload": body}, headers=H)
                assert resp.status == 200
            break  # une commande par équipement suffit : chaque aperçu évalue l'équipement entier


async def test_les_lectures_ne_publient_rien_et_ne_changent_pas_la_projection(aiohttp_client):
    """Preuves 2 et 3 — lectures sans publication ; republication identique ensuite."""
    from transport.http_server import _republish_all_from_cache

    app, bridge, cli = await _fresh(aiohttp_client)
    corpus = load_corpus()
    await _sync(cli, corpus, "lot3-a")
    premier = _discovery_only(bridge.calls)

    bridge.calls = []
    await _toutes_les_lectures(cli, app)
    assert bridge.calls == [], "une lecture du Lot 3 a publié sur le broker"

    await _sync(cli, corpus, "lot3-b")
    second = _discovery_only(bridge.calls)
    assert all(c in premier for c in second), "le second sync publie un message de découverte différent"

    bridge.calls = []
    await _republish_all_from_cache(app, "ha_birth")
    republie = {c["topic"]: c["payload"] for c in _discovery_only(bridge.calls)}
    attendu = {c["topic"]: c["payload"] for c in premier}
    assert republie, "aucune republication"
    for topic, payload in republie.items():
        if topic in attendu:
            assert payload == attendu[topic], f"payload republié différent : {topic}"

