"""Story 25.2 (AC15) — budgets de la route agrégée sur un parc synthétique de 292 équipements.

Marqueur `load` (exclu de la suite par défaut) : `pytest -m load resources/daemon/tests/unit/test_story_25_2_load.py -s`.
Vrai `MapperRegistry` et vrai `evaluate_equipment` (aucun mock). Méthode de 19-6 : coût mesuré = maximum des
mesures x `MARGE_MESURE` x `MACHINE_FACTOR` (box <= 3x plus lente que la VM de mesure). Budgets de Q10.
Mesure synthétique uniquement : aucune mesure terrain (CC-48, preuve terrain réservée à ClaudeBox).
"""

import time

import pytest

from models.mapping import PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from transport.http_server import create_app

pytestmark = pytest.mark.load

SECRET = "test_secret_25_2_load"
H = {"X-Local-Secret": SECRET}
PARC = 292
MACHINE_FACTOR = 3.0
MARGE_MESURE = 1.5
MESURES = 3

BUDGET_FROID_MS = 4000
BUDGET_CHAUD_MS = 50
BUDGET_TAILLE_OCTETS = 1_500_000


def _cmd(eq_id, n, name, generic_type, type_="info", sub_type="binary", **kw):
    return JeedomCmd(id=eq_id * 100 + n, name=name, generic_type=generic_type, type=type_, sub_type=sub_type, **kw)


def _equipment(eq_id):
    """Formes représentatives, la plus coûteuse (beaucoup de commandes + capteur secondaire) en tête de cycle."""
    shape = eq_id % 7
    object_id = 1 + eq_id % 12
    if shape == 0:  # beaucoup de commandes (forme la plus coûteuse déclarée)
        cmds = [_cmd(eq_id, 1, "On", "ENERGY_ON", "action", "other"),
                _cmd(eq_id, 2, "Off", "ENERGY_OFF", "action", "other"),
                _cmd(eq_id, 3, "Etat", "ENERGY_STATE")]
        cmds += [_cmd(eq_id, 10 + i, f"Mesure {i}", None, "info", "numeric", unit="W", current_value=i) for i in range(30)]
        return JeedomEqLogic(id=eq_id, name=f"Eq {eq_id}", object_id=object_id, eq_type_name="prise", cmds=cmds)
    if shape == 1:  # sans commande
        return JeedomEqLogic(id=eq_id, name=f"Eq {eq_id}", object_id=object_id, eq_type_name="virtual", cmds=[])
    if shape == 2:  # désactivé
        return JeedomEqLogic(id=eq_id, name=f"Eq {eq_id}", object_id=object_id, is_enable=False, eq_type_name="light",
                             cmds=_light(eq_id))
    if shape == 3:  # exclu
        return JeedomEqLogic(id=eq_id, name=f"Eq {eq_id}", object_id=object_id, is_excluded=True,
                             exclusion_source="eqlogic", eq_type_name="light", cmds=_light(eq_id))
    if shape == 4:  # prise avec conso (multi-entités)
        return JeedomEqLogic(id=eq_id, name=f"Eq {eq_id}", object_id=object_id, eq_type_name="prise", cmds=[
            _cmd(eq_id, 1, "On", "ENERGY_ON", "action", "other"),
            _cmd(eq_id, 2, "Off", "ENERGY_OFF", "action", "other"),
            _cmd(eq_id, 3, "Etat", "ENERGY_STATE"),
            _cmd(eq_id, 4, "Conso", None, "info", "numeric", unit="W", current_value=42)])
    if shape == 5:  # sans pièce
        return JeedomEqLogic(id=eq_id, name=f"Eq {eq_id}", object_id=None, eq_type_name="light", cmds=_light(eq_id))
    return JeedomEqLogic(id=eq_id, name=f"Eq {eq_id}", object_id=object_id, eq_type_name="light", cmds=_light(eq_id))


def _light(eq_id):
    return [_cmd(eq_id, 1, "On", "LIGHT_ON", "action", "other"),
            _cmd(eq_id, 2, "Off", "LIGHT_OFF", "action", "other"),
            _cmd(eq_id, 3, "Etat", "LIGHT_STATE")]


@pytest.fixture
def app(tmp_path):
    application = create_app(local_secret=SECRET)
    eqs = {1000 + i: _equipment(1000 + i) for i in range(PARC)}
    application["topology"] = TopologySnapshot(
        timestamp="2026-10-18T12:00:00Z",
        objects={i: JeedomObject(id=i, name=f"Pièce {i}") for i in range(1, 13)},
        eq_logics=eqs,
    )
    application["data_dir"] = str(tmp_path)
    application["publications"] = {
        eq_id: PublicationDecision(should_publish=True, reason="sure") for eq_id in list(eqs)[::2]
    }
    return application


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _timed_get(cli, path):
    start = time.perf_counter()
    resp = await cli.get(path, headers=H)
    body = await resp.read()
    return (time.perf_counter() - start) * 1000, len(body), resp.status


async def test_ac15_budgets_on_292_equipments(app, cli):
    froid, chaud, octets = [], [], 0
    for _ in range(MESURES):
        app["equipment_states_cache"]["entry"] = None
        ms, octets, status = await _timed_get(cli, "/system/equipment_states")
        assert status == 200
        froid.append(ms)
    for _ in range(MESURES * 2):
        ms, _, _ = await _timed_get(cli, "/system/equipment_states")
        chaud.append(ms)

    boucle = []
    for _ in range(MESURES):
        total = 0.0
        for eq_id in app["topology"].eq_logics:
            ms, _, _ = await _timed_get(cli, f"/system/mapping_overrides/{eq_id}")
            total += ms
        boucle.append(total)

    facteur = MARGE_MESURE * MACHINE_FACTOR
    build_cold_ms = max(froid) * facteur
    hit_ms = max(chaud) * facteur
    boucle_ms = max(boucle) * facteur
    c_eq = max(froid) / PARC * facteur
    print(
        f"\n[25.2 AC15] equipements={PARC} c_eq={c_eq:.2f}ms build_cold_ms={build_cold_ms:.0f} (mesure {max(froid):.0f}) "
        f"hit_ms={hit_ms:.1f} (mesure {max(chaud):.1f}) bytes={octets} "
        f"boucle_actuelle_ms={boucle_ms:.0f} rapport_boucle/route={boucle_ms / build_cold_ms:.1f}"
    )
    assert build_cold_ms <= BUDGET_FROID_MS
    assert hit_ms <= BUDGET_CHAUD_MS
    assert octets <= BUDGET_TAILLE_OCTETS
