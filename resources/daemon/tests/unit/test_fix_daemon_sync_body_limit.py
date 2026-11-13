"""Correctif fix/daemon-sync-body-limit — une synchro de plus de 1 Mio est acceptée.

Incident : la topologie complète d'une installation réelle, envoyée en un seul corps JSON à
/action/sync, a dépassé la limite par défaut d'aiohttp (1 Mio) après l'ajout des bornes des
commandes (24.15) : chaque synchro répondait 413. Données fictives uniquement (CC-48).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import transport.http_server as http_server
from models.topology import TopologySnapshot

SECRET = "secret-fix-body-limit"
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus" / "sync_payload.json"
ONE_MIB = 1024 * 1024


def _large_payload(min_bytes: int) -> dict:
    """Corpus golden démultiplié (ids décalés) jusqu'à dépasser ``min_bytes``."""
    base = json.loads(GOLDEN.read_text(encoding="utf-8"))
    payload = copy.deepcopy(base)
    payload["eq_logics"] = []
    copy_index = 0
    while len(json.dumps(payload, separators=(",", ":")).encode()) < min_bytes:
        copy_index += 1
        offset = copy_index * 10_000_000
        for eq in base["eq_logics"]:
            clone = copy.deepcopy(eq)
            clone["id"] = eq["id"] + offset
            for cmd in clone.get("cmds", []):
                cmd["id"] = cmd["id"] + offset
            payload["eq_logics"].append(clone)
    return payload


def test_limit_is_explicit_generous_and_bounded():
    assert http_server.SYNC_REQUEST_MAX_BYTES == 32 * ONE_MIB
    app = http_server.create_app(local_secret=SECRET)
    assert app._client_max_size == http_server.SYNC_REQUEST_MAX_BYTES


@pytest.mark.asyncio
async def test_sync_body_larger_than_one_mib_is_accepted(aiohttp_client):
    payload = _large_payload(2 * ONE_MIB)
    body = {"action": "sync", "payload": payload, "request_id": "r",
            "timestamp": "2026-11-13T00:00:00Z"}
    raw = json.dumps(body, separators=(",", ":"))
    assert len(raw.encode()) > 2 * ONE_MIB
    app = http_server.create_app(local_secret=SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge
    cli = await aiohttp_client(app)
    resp = await cli.post("/action/sync", data=raw, headers={
        "X-Local-Secret": SECRET, "Content-Type": "application/json"})
    assert resp.status == 200, await resp.text()
    assert len(app["topology"].eq_logics) == len(payload["eq_logics"])


def test_absent_bounds_are_none_and_present_bounds_are_read():
    snapshot = TopologySnapshot.from_jeedom_payload({
        "objects": [],
        "eq_logics": [{"id": 1, "name": "Eq 1", "cmds": [
            {"id": 11, "name": "Sans bornes", "type": "action", "sub_type": "slider"},
            {"id": 12, "name": "Avec bornes", "type": "action", "sub_type": "slider",
             "min_value": "7", "max_value": "30,5"},
        ]}],
    })
    without, with_bounds = snapshot.eq_logics[1].cmds
    assert (without.min_value, without.max_value) == (None, None)
    assert (with_bounds.min_value, with_bounds.max_value) == (7.0, 30.5)
