"""Front v3 — Lot 8 (revue P2 #406) : un retrait de bouton de scénario non confirmé reste visible dans le statut.

`_withdraw_unselected_scenario` en échec produit `scenario_not_selected_pending` avec
`discovery_published=False` : le statut ne doit pas en déduire que le bouton est absent de Home
Assistant. `in_ha` devient inconnu (None), `withdraw_pending` et `ha_pending` le disent, jusqu'à la
synchro qui confirme le retrait. Symétrique : une publication non confirmée a `ha_pending: true`.
Données fictives.
"""

from __future__ import annotations

from transport.http_server import create_app

from .front_v3_lot4a_corpus import RetainingRecordingBridge, lot4a_scenarios, sync_body

SECRET = "test-secret-lot8"
H = {"X-Local-Secret": SECRET}


def _cfg(sc_id):
    return f"homeassistant/button/jeedom2ha_scenario_{sc_id}/config"


class FlakyBridge(RetainingRecordingBridge):
    """Le broker refuse les écritures sur les topics listés dans `failing` (retrait ou publication)."""

    def __init__(self, retained=None):
        super().__init__(retained)
        self.failing = set()

    def publish_message(self, topic, payload, qos=1, retain=False):
        if any(key in topic for key in self.failing):
            self.calls.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain, "refused": True})
            return False
        return super().publish_message(topic, payload, qos=qos, retain=retain)


async def _setup(aiohttp_client):
    app = create_app(local_secret=SECRET)
    bridge = FlakyBridge()
    app["mqtt_bridge"] = bridge
    return app, bridge, await aiohttp_client(app)


async def _sync(cli, published, request_id):
    resp = await cli.post("/action/sync", json=sync_body(lot4a_scenarios(published=published), request_id), headers=H)
    assert resp.status == 200, await resp.text()
    return await resp.json()


async def _rows(cli):
    resp = await cli.get("/system/status", headers=H)
    return {row["id"]: row for row in (await resp.json())["payload"]["scenarios"]}


ALL = {20: True, 21: True, 22: True, 23: True}
WITHOUT_22 = {20: True, 21: True, 22: False, 23: True}


async def test_retrait_en_echec_reste_en_attente_puis_confirme(aiohttp_client):
    app, bridge, cli = await _setup(aiohttp_client)
    await _sync(cli, ALL, "lot8-a")
    rows = await _rows(cli)
    assert rows[22]["in_ha"] is True and rows[22]["withdraw_pending"] is False and rows[22]["ha_pending"] is False

    # Retrait demandé, le broker refuse : le bouton est peut-être encore dans Home Assistant.
    bridge.failing = {"jeedom2ha_scenario_22/", "scenario_22/availability"}
    result = await _sync(cli, WITHOUT_22, "lot8-b")
    assert result["scenario_availability_complete"] is False
    assert _cfg(22) in bridge.retained, "le bouton est toujours retenu sur le broker"
    rows = await _rows(cli)
    assert rows[22]["published"] is False
    assert rows[22]["in_ha"] is None, "retrait non confirmé : présence inconnue, jamais « absent »"
    assert rows[22]["withdraw_pending"] is True and rows[22]["ha_pending"] is True
    assert rows[20]["withdraw_pending"] is False and rows[20]["ha_pending"] is False and rows[20]["in_ha"] is True

    # Une relecture qui échoue encore garde l'attente.
    await _sync(cli, WITHOUT_22, "lot8-c")
    rows = await _rows(cli)
    assert rows[22]["withdraw_pending"] is True and rows[22]["in_ha"] is None

    # Le broker répond : retrait confirmé, plus rien en attente.
    bridge.failing = set()
    result = await _sync(cli, WITHOUT_22, "lot8-d")
    assert result["scenario_availability_complete"] is True
    assert _cfg(22) not in bridge.retained
    rows = await _rows(cli)
    assert rows[22]["in_ha"] is False and rows[22]["withdraw_pending"] is False and rows[22]["ha_pending"] is False
    assert app["scenario_publications"][22].reason == "scenario_not_selected"


async def test_publication_en_echec_est_en_attente(aiohttp_client):
    _app, bridge, cli = await _setup(aiohttp_client)
    await _sync(cli, WITHOUT_22, "lot8-p1")
    bridge.failing = {"jeedom2ha_scenario_22/"}
    result = await _sync(cli, ALL, "lot8-p2")
    assert result["scenario_availability_complete"] is False
    rows = await _rows(cli)
    assert rows[22]["published"] is True and rows[22]["in_ha"] is False
    assert rows[22]["ha_pending"] is True and rows[22]["withdraw_pending"] is False

    bridge.failing = set()
    await _sync(cli, ALL, "lot8-p3")
    rows = await _rows(cli)
    assert rows[22]["in_ha"] is True and rows[22]["ha_pending"] is False


async def test_disponibilite_en_echec_est_en_attente(aiohttp_client):
    _app, bridge, cli = await _setup(aiohttp_client)
    bridge.failing = {"scenario_20/availability"}
    await _sync(cli, ALL, "lot8-av")
    rows = await _rows(cli)
    assert rows[20]["in_ha"] is True and rows[20]["ha_pending"] is True and rows[20]["withdraw_pending"] is False
