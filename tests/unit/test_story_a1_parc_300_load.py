"""Story A1 (AC3, T4) — charge réelle à 300 équipements sur les endpoints des relais de parc.

Exerce le vrai serveur HTTP du démon (create_app + aiohttp), sans simulateur du relais :
/action/sync (scanTopology) puis /system/diagnostics (exportDiagnostic/getDiagnostics).
Preuve d'audit : ni l'un ni l'autre n'appelle `asyncio.sleep` avec une pause de lissage, donc
`deadline_s`/`plafond_pauses` n'ont rien à plafonner pour ces relais ; seul le budget fixe R
du relais PHP (60 s) importe, et la durée réelle reste très en dessous.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

LOCAL_SECRET = "test-secret-abc123"
N_EQUIPEMENTS = 300
BUDGET_RELAIS_R_S = 60  # JEEDOM2HA_ACTION_BUDGET_R (tests/fixtures/action_budget_constants.json)

_FAKE_CLI_ARGS = [
    "--loglevel", "debug", "--sockethost", "127.0.0.1", "--socketport", "0",
    "--callback", "http://127.0.0.1/fake", "--apikey", "test-api-key",
    "--pid", "/tmp/test-jeedom2ha.pid", "--cycle", "0.5",
]


@pytest.fixture(autouse=True)
def fake_cli_args():
    with patch("sys.argv", ["main.py"] + _FAKE_CLI_ARGS):
        yield


@pytest.fixture
def http_app():
    from resources.daemon.transport.http_server import create_app

    app = create_app(local_secret=LOCAL_SECRET)
    bridge = MagicMock()
    bridge.is_connected = False
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    return app


@pytest.fixture
async def http_client(http_app, aiohttp_client):
    return await aiohttp_client(http_app)


def _parc(n):
    return {
        "version": "1.0",
        "objects": [{"id": "1", "name": "Salon"}],
        "eq_logics": [
            {
                "id": str(1000 + i),
                "name": f"Prise {i}",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [
                    {"id": str(10000 + i * 3), "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                    {"id": str(10001 + i * 3), "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                    {"id": str(10002 + i * 3), "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                ],
            }
            for i in range(n)
        ],
    }


async def test_scan_et_diagnostics_a_300_equipements_sans_pause_de_lissage(http_client):
    sleeps = []
    real_sleep = __import__("asyncio").sleep

    async def spy_sleep(delay, *args, **kwargs):
        sleeps.append(delay)
        return await real_sleep(delay, *args, **kwargs)

    with patch("resources.daemon.transport.http_server.asyncio.sleep", spy_sleep):
        t0 = time.monotonic()
        resp = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET, "X-Jeedom2ha-Sync-Mode": "rescan"},
            json={"payload": _parc(N_EQUIPEMENTS)},
        )
        scan_s = time.monotonic() - t0
        assert resp.status == 200
        assert (await resp.json())["status"] == "ok"

        t1 = time.monotonic()
        diag = await http_client.get("/system/diagnostics", headers={"X-Local-Secret": LOCAL_SECRET})
        diag_s = time.monotonic() - t1
        assert diag.status == 200
        body = await diag.json()

    assert len(body["payload"]["equipments"]) == N_EQUIPEMENTS
    # Aucune pause de lissage : rien à plafonner côté démon pour ces deux relais.
    assert [d for d in sleeps if d and d > 0] == []
    # Le travail réel tient très largement dans le budget fixe du relais.
    assert scan_s < BUDGET_RELAIS_R_S / 2
    assert diag_s < BUDGET_RELAIS_R_S / 2
