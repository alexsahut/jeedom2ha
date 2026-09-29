"""Story 19.4 — AC3 (filtre de scope unique) et AC7 (parité à 4 points d'appel).

Tests d'acceptation rédigés par ClaudeBox (unité 5).

AC3 — `_scope_entry_is_included` est le filtre de scope unique, appliqué APRÈS la décision
(`evaluate_equipment()`) par le sync comme par « Publier » :
- Q1 : un équipement publié puis exclu du périmètre (scope `exclude`) est dépublié par le
  sync suivant, sa disponibilité est effacée, et rien d'autre ne bouge ;
- Q2 : exclu dès le premier sync ⇒ jamais publié ;
- Q3 : exclusion héritée d'une pièce ⇒ même effet (le filtre lit l'état EFFECTIF) ;
- Q4 (golden) : sur le corpus doré avec un scope `exclude`, l'ensemble des topics publiés
  par le sync et par un « Publier » global est identique.
- Q5 : la surface applique le même filtre à sa décision courante : un équipement hors
  périmètre n'affiche pas « pas encore appliqué » (`override_pending`).

AC7 — pour un même équipement, le sync, « Publier », la surface
(`GET /system/mapping_overrides/{eq_id}`) et l'aperçu (`POST /system/overrides/preview`)
produisent exactement la même décision :
- R1 : confiance `sure_mapping` (injectée au niveau du mapper, en amont des 4 chemins) ;
- R2 : exclusion par override d'équipement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mapping.overrides import save_equipment_override
from mapping.registry import MapperRegistry
from transport.http_server import create_app


def _load_sibling(filename: str):
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(f"{path.stem}_scope", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = _load_sibling("test_story_19_4_guard_publisher_calls.py")

LIGHT_1000 = "homeassistant/light/jeedom2ha_1000/config"
AVAIL_1000 = "jeedom2ha/1000/availability"


def _published(bridge) -> set[str]:
    return {c["topic"] for c in bridge.calls if c["payload"] != ""}


def _deleted(bridge) -> list[str]:
    return [c["topic"] for c in bridge.calls if c["payload"] == ""]


def _avail(bridge, topic: str) -> list[str]:
    return [c["payload"] for c in bridge.avail_calls if c["topic"] == topic]


def _reset(bridge) -> None:
    bridge.calls.clear()
    bridge.avail_calls.clear()


async def _client(aiohttp_client, tmp_path):
    app = create_app(local_secret=G.SECRET)
    app["data_dir"] = str(tmp_path)
    bridge = G.MqttRecordingBridge()
    app["mqtt_bridge"] = bridge
    return await aiohttp_client(app), app, bridge


def _golden_body(request_id: str, published_scope: dict | None = None) -> dict:
    body = G._sync_body(G._load_golden_corpus(), request_id=request_id)
    if published_scope is not None:
        body["payload"]["published_scope"] = published_scope
    return body


def _eq_scope(eq_id: int, state: str) -> dict:
    return {"equipements": {str(eq_id): {"raw_state": state, "source": "equipement"}}}


async def _publier(cli, portee: str, selection: list) -> None:
    body = {"intention": "publier", "portee": portee, "selection": selection}
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        resp = await cli.post("/action/execute", json=body, headers={"X-Local-Secret": G.SECRET})
    assert resp.status == 200, await resp.text()


# ---------------------------------------------------------------------------
# AC3 — filtre de scope unique, appliqué après la décision, sync compris
# ---------------------------------------------------------------------------


async def test_q1_sync_depublie_un_equipement_sorti_du_perimetre(aiohttp_client, tmp_path):
    cli, app, bridge = await _client(aiohttp_client, tmp_path)
    await G._post_sync(cli, _golden_body("q1-1"))
    assert LIGHT_1000 in _published(bridge)
    _reset(bridge)

    await G._post_sync(cli, _golden_body("q1-2", _eq_scope(1000, "exclude")))

    assert _deleted(bridge) == [LIGHT_1000]
    assert _avail(bridge, AVAIL_1000)[-1:] == [""]
    decision = app["publications"][1000]
    assert decision.should_publish is False
    assert decision.reason == "excluded"
    assert 1000 in app["mappings"]


async def test_q2_exclu_des_le_premier_sync_jamais_publie(aiohttp_client, tmp_path):
    cli, app, bridge = await _client(aiohttp_client, tmp_path)

    await G._post_sync(cli, _golden_body("q2", _eq_scope(1000, "exclude")))

    assert LIGHT_1000 not in _published(bridge)
    assert _avail(bridge, AVAIL_1000) in ([], [""])
    assert app["publications"][1000].should_publish is False


async def test_q3_exclusion_heritee_de_la_piece(aiohttp_client, tmp_path):
    cli, app, bridge = await _client(aiohttp_client, tmp_path)
    await G._post_sync(cli, _golden_body("q3-1"))
    piece_id = app["topology"].eq_logics[1000].object_id
    _reset(bridge)

    scope = {"pieces": {str(piece_id): {"raw_state": "exclude", "source": "piece"}}}
    await G._post_sync(cli, _golden_body("q3-2", scope))

    assert LIGHT_1000 in _deleted(bridge)
    assert app["publications"][1000].should_publish is False


async def test_q4_golden_meme_ensemble_publie_par_le_sync_et_publier(aiohttp_client, tmp_path):
    cli, app, bridge = await _client(aiohttp_client, tmp_path)
    await G._post_sync(cli, _golden_body("q4", _eq_scope(1000, "exclude")))
    by_sync = {t for t in _published(bridge) if "/jeedom2ha_" in t}
    _reset(bridge)

    await _publier(cli, "global", list(app["topology"].eq_logics.keys()))
    by_publier = {t for t in _published(bridge) if "/jeedom2ha_" in t}

    assert LIGHT_1000 not in by_sync
    assert by_publier == by_sync


async def test_q5_surface_hors_perimetre_sans_faux_pas_encore_applique(aiohttp_client, tmp_path):
    cli, app, bridge = await _client(aiohttp_client, tmp_path)
    await G._post_sync(cli, _golden_body("q5", _eq_scope(1000, "exclude")))

    resp = await cli.get("/system/mapping_overrides/1000", headers={"X-Local-Secret": G.SECRET})
    assert resp.status == 200
    status = (await resp.json())["payload"]["sync_status"]

    assert status == {
        "synced_should_publish": False,
        "current_should_publish": False,
        "override_pending": False,
    }


# ---------------------------------------------------------------------------
# AC7 — parité à 4 points d'appel : sync, « Publier », surface, aperçu
# ---------------------------------------------------------------------------


async def _four_verdicts(cli, app, bridge, eq_id: int) -> tuple[dict, set[str]]:
    """Décision (should_publish, reason) du même équipement vue par les 4 points d'appel,
    et topics réellement publiés par le clic « Publier » (pas seulement la décision stockée)."""
    headers = {"X-Local-Secret": G.SECRET}
    via_sync = app["publications"][eq_id]
    verdicts = {"sync": (via_sync.should_publish, via_sync.reason)}

    principal_cmd = next(iter(app["mappings"][eq_id].commands.values())).id
    resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=headers)
    assert resp.status == 200
    tree = (await resp.json())["payload"]
    row = next(r for r in tree["commands"] if r["jeedom_cmd_id"] == principal_cmd)
    assert tree["sync_status"]["current_should_publish"] == row["diagnostic"]["should_publish"]
    verdicts["surface"] = (row["diagnostic"]["should_publish"], row["diagnostic"]["publication_reason"])

    resp = await cli.post(
        "/system/overrides/preview",
        headers=headers,
        json={"payload": {
            "jeedom_eq_id": eq_id,
            "jeedom_cmd_id": principal_cmd,
            "ha_entity_type": app["mappings"][eq_id].ha_entity_type,
        }},
    )
    assert resp.status == 200
    auto = (await resp.json())["payload"]["auto"]
    verdicts["apercu"] = (auto["should_publish"], auto["publication_reason"])

    _reset(bridge)
    await _publier(cli, "equipement", [eq_id])
    via_publier = app["publications"][eq_id]
    verdicts["publier"] = (via_publier.should_publish, via_publier.reason)
    return verdicts, _published(bridge)


async def test_r1_parite_sure_mapping(aiohttp_client, tmp_path):
    real_map = MapperRegistry.map

    def _sure_mapping(self, eq, snapshot):
        result = real_map(self, eq, snapshot)
        if result is not None and eq.id == 1000:
            result.confidence = "sure_mapping"
        return result

    cli, app, bridge = await _client(aiohttp_client, tmp_path)
    with patch.object(MapperRegistry, "map", _sure_mapping):
        await G._post_sync(cli, _golden_body("r1"))
        verdicts, clicked = await _four_verdicts(cli, app, bridge, 1000)

    assert verdicts["sync"] == (True, "sure_mapping")
    assert set(verdicts.values()) == {verdicts["sync"]}, verdicts
    assert LIGHT_1000 in clicked


async def test_r2_parite_exclusion_par_override(aiohttp_client, tmp_path):
    cli, app, bridge = await _client(aiohttp_client, tmp_path)
    save_equipment_override(1000, {"publication_override": "exclude"}, str(tmp_path))
    await G._post_sync(cli, _golden_body("r2"))

    verdicts, clicked = await _four_verdicts(cli, app, bridge, 1000)

    assert verdicts["sync"][0] is False
    assert set(verdicts.values()) == {verdicts["sync"]}, verdicts
    assert LIGHT_1000 not in clicked
