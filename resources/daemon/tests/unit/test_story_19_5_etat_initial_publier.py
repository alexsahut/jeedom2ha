"""Story 19.5 (CC-29) — état initial avec la valeur courante au clic « Publier »."""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sync.state import StateSynchronizer
from transport.http_server import create_app


def _load_sibling(filename: str):
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(f"{path.stem}_19_5", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S12_1 = _load_sibling("test_story_12_1_state_streaming.py")
G = _load_sibling("test_story_19_4_guard_publisher_calls.py")


def _sync(publications, bridge):
    return StateSynchronizer(app={"publications": publications}, mqtt_bridge=bridge)


# --- AC1 : principal + secondaire (y compris sous principal refusé, I11) ---

@pytest.mark.asyncio
async def test_ac1_mono_sensor_publie_valeur_du_clic():
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001, current_value="9999")
    bridge = S12_1._FakeBridge()
    sync = _sync({100: decision}, bridge)

    published, failed = await sync.publish_click_states(
        decision, fresh_values={4001: "231.0"}, fresh_since=time.monotonic() - 10,
    )

    assert (published, failed) == (1, 0)
    assert bridge.published == [("jeedom2ha/100/state", "231.0", 1, True)]


@pytest.mark.asyncio
async def test_ac1_secondaire_publie_sous_principal_refuse():
    decision = S12_1._multi_sensor_decision(eq_id=553, cmd_ids=(5301, 5302))
    decision.should_publish = False  # principal refusé (I11)
    bridge = S12_1._FakeBridge()
    sync = _sync({553: decision}, bridge)

    published, failed = await sync.publish_click_states(
        decision, fresh_values={5302: "13.1"}, fresh_since=time.monotonic() - 10,
    )

    # Le principal (5301) n'a pas de valeur fraîche fournie : il n'est pas publié.
    assert (published, failed) == (1, 0)
    assert bridge.published == [("jeedom2ha/553/5302/state", "13.1", 1, True)]


# --- AC2 : jamais la valeur du dernier sync ---

@pytest.mark.asyncio
async def test_ac2_commande_absente_de_current_values_ne_publie_rien():
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001, current_value="230.5")
    bridge = S12_1._FakeBridge()
    sync = _sync({100: decision}, bridge)

    published, failed = await sync.publish_click_states(
        decision, fresh_values={}, fresh_since=time.monotonic() - 10,
    )

    assert (published, failed) == (0, 0)
    assert bridge.published == []


# --- AC3 : même traduction que le sync (parité) ---

@pytest.mark.asyncio
async def test_ac3_parite_traduction_sensor():
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge_sync = S12_1._FakeBridge()
    bridge_click = S12_1._FakeBridge()
    sync_a = _sync({100: decision}, bridge_sync)
    sync_b = _sync({100: decision}, bridge_click)

    await sync_a.publish_initial_states(decision)
    await sync_b.publish_click_states(
        decision, fresh_values={4001: decision.mapping_result.commands["POWER"].current_value},
        fresh_since=time.monotonic() - 10,
    )

    assert bridge_sync.published == bridge_click.published


@pytest.mark.asyncio
async def test_ac3_parite_traduction_binaire():
    decision = S12_1._binary_decision(eq_id=200, cmd_id=6001, current_value="1")
    bridge_sync = S12_1._FakeBridge()
    bridge_click = S12_1._FakeBridge()
    sync_a = _sync({200: decision}, bridge_sync)
    sync_b = _sync({200: decision}, bridge_click)

    await sync_a.publish_initial_states(decision)
    await sync_b.publish_click_states(
        decision, fresh_values={6001: "1"}, fresh_since=time.monotonic() - 10,
    )

    assert bridge_sync.published == bridge_click.published == [
        ("jeedom2ha/200/state", "ON", 1, True)
    ]


# --- AC4 : refusé ou hors périmètre => aucun état ---

@pytest.mark.asyncio
async def test_ac4_candidat_refuse_par_sa_propre_decision():
    decision = S12_1._multi_sensor_decision(eq_id=553, cmd_ids=(5301, 5302))
    secondary = decision.mapping_result.additional_mappings[0]
    secondary.publication_decision_ref.discovery_published = False
    bridge = S12_1._FakeBridge()
    sync = _sync({553: decision}, bridge)

    published, failed = await sync.publish_click_states(
        decision, fresh_values={5301: "232", 5302: "13.1"}, fresh_since=time.monotonic() - 10,
    )

    assert (published, failed) == (1, 0)
    assert bridge.published == [("jeedom2ha/553/5301/state", "232", 1, True)]


@pytest.mark.asyncio
async def test_ac4_equipement_exclu_hors_perimetre():
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001, published=False)
    bridge = S12_1._FakeBridge()
    sync = _sync({100: decision}, bridge)

    published, failed = await sync.publish_click_states(
        decision, fresh_values={4001: "231.0"}, fresh_since=time.monotonic() - 10,
    )

    assert (published, failed) == (0, 0)
    assert bridge.published == []


# --- AC5 : équipement déjà publié republié avec la valeur du clic ---

@pytest.mark.asyncio
async def test_ac5_equipement_deja_publie_republie_valeur_du_clic():
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001, current_value="10", published=True)
    bridge = S12_1._FakeBridge()
    sync = _sync({100: decision}, bridge)

    published, failed = await sync.publish_click_states(
        decision, fresh_values={4001: "42"}, fresh_since=time.monotonic() - 10,
    )

    assert (published, failed) == (1, 0)
    assert bridge.published == [("jeedom2ha/100/state", "42", 1, True)]


# --- AC7 : sans current_values (None) : rien de publié — testé au niveau http_server ---

@pytest.mark.asyncio
async def test_ac7_fresh_values_none_est_gere_au_niveau_appelant():
    # `publish_click_states` exige un mapping ; le garde "fresh_values is not None"
    # est posé côté http_server AVANT l'appel (AC7), donc non testé ici directement.
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge = S12_1._FakeBridge()
    sync = _sync({100: decision}, bridge)

    published, failed = await sync.publish_click_states(
        decision, fresh_values={}, fresh_since=time.monotonic() - 10,
    )
    assert (published, failed) == (0, 0)


# --- AC8 : un évènement reçu pendant le clic l'emporte ---

@pytest.mark.asyncio
async def test_ac8_evenement_publie_pendant_le_clic_lemporte():
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge = S12_1._FakeBridge()
    sync = _sync({100: decision}, bridge)
    fresh_since = time.monotonic()

    # Évènement Jeedom reçu (et publié) après le début du clic.
    assert await sync.handle_state_message(eq_id=100, cmd_id=4001, value="500") is True
    bridge.published.clear()

    published, failed = await sync.publish_click_states(
        decision, fresh_values={4001: "231.0"}, fresh_since=fresh_since,
    )

    assert (published, failed) == (1, 0)
    assert bridge.published == [("jeedom2ha/100/state", "500", 1, True)]


@pytest.mark.asyncio
async def test_ac8_evenement_rejete_pendant_le_clic_lemporte_aussi():
    # Entité pas encore publiée : l'évènement est rejeté (state_target_not_found)
    # mais reste enregistré comme "plus récent que le clic" (AC8).
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001, published=False)
    bridge = S12_1._FakeBridge()
    sync = _sync({100: decision}, bridge)
    fresh_since = time.monotonic()

    assert await sync.handle_state_message(eq_id=100, cmd_id=4001, value="777") is False

    # Le clic "publie" désormais l'entité (discovery vient de réussir) : la valeur
    # de l'évènement rejeté doit l'emporter sur celle lue au clic.
    decision.discovery_published = True
    published, failed = await sync.publish_click_states(
        decision, fresh_values={4001: "231.0"}, fresh_since=fresh_since,
    )

    assert (published, failed) == (1, 0)
    assert bridge.published == [("jeedom2ha/100/state", "777", 1, True)]


# --- AC9 : le sync ne change pas ---

@pytest.mark.asyncio
async def test_ac9_publish_initial_states_signature_et_comportement_inchanges():
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001, current_value="231.0")
    bridge = S12_1._FakeBridge()
    sync = _sync({100: decision}, bridge)

    count = await sync.publish_initial_states(decision)

    assert count == 1
    assert bridge.published == [("jeedom2ha/100/state", "231.0", 1, True)]


@pytest.mark.asyncio
async def test_ac9_publish_initial_states_echec_non_journalise_en_warning(caplog):
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001, current_value="231.0")
    bridge = S12_1._FakeBridge(publish_ok=False)
    sync = _sync({100: decision}, bridge)

    with caplog.at_level("WARNING"):
        count = await sync.publish_initial_states(decision)

    assert count == 0
    assert "initial_state_publish_failed" not in caplog.text


# --- AC10 : un échec de publication d'état compte comme une erreur ---

@pytest.mark.asyncio
async def test_ac10_echec_publication_etat_compte_et_journalise(caplog):
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge = S12_1._FakeBridge(publish_ok=False)
    sync = _sync({100: decision}, bridge)

    with caplog.at_level("WARNING"):
        published, failed = await sync.publish_click_states(
            decision, fresh_values={4001: "231.0"}, fresh_since=time.monotonic() - 10,
        )

    assert (published, failed) == (0, 1)
    assert "initial_state_publish_failed" in caplog.text


@pytest.mark.asyncio
async def test_ac10_commande_sans_valeur_nest_pas_un_echec():
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge = S12_1._FakeBridge(publish_ok=False)
    sync = _sync({100: decision}, bridge)

    published, failed = await sync.publish_click_states(
        decision, fresh_values={}, fresh_since=time.monotonic() - 10,
    )

    assert (published, failed) == (0, 0)


# --- Résiduel AC6 : équipement résolu par le démon sans valeur au clic ---

@pytest.mark.asyncio
async def test_residuel_ac6_equipement_sans_valeur_au_clic_aucun_etat(caplog):
    decision = S12_1._mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge = S12_1._FakeBridge()
    sync = _sync({100: decision}, bridge)

    with caplog.at_level("DEBUG"):
        published, failed = await sync.publish_click_states(
            decision, fresh_values={9999: "231.0"}, fresh_since=time.monotonic() - 10,
        )

    assert (published, failed) == (0, 0)
    assert bridge.published == []
    # Revue ClaudeBox (PR #184) : le résiduel est tracé en DEBUG, sans erreur.
    assert "reason_code=initial_state_no_click_value" in caplog.text
    assert "initial_state_publish_failed" not in caplog.text


# --- Câblage http_server (AC1, AC7, AC9) : /action/execute publier => state_synchronizer ---

class _StateRecordingBridge(G.MqttRecordingBridge):
    """Étend le bridge factice 19-4 pour journaliser aussi les topics d'état
    (`jeedom2ha/.../state`), non journalisés par la classe parente."""

    def publish_message(self, topic, payload, qos=0, retain=False):
        if topic.startswith("jeedom2ha/") and topic.endswith("/state"):
            self.calls.append({"topic": topic, "payload": payload, "retain": retain})
            return True
        return super().publish_message(topic, payload, qos=qos, retain=retain)


async def _client_with_state_sync(aiohttp_client, tmp_path):
    app = create_app(local_secret=G.SECRET)
    app["data_dir"] = str(tmp_path)
    bridge = _StateRecordingBridge()
    app["mqtt_bridge"] = bridge
    app["state_synchronizer"] = StateSynchronizer(app=app, mqtt_bridge=bridge)
    cli = await aiohttp_client(app)
    return cli, app, bridge


async def _publier_with_current_values(cli, portee, selection, current_values):
    body = {
        "intention": "publier", "portee": portee, "selection": selection,
        "current_values": current_values,
    }
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        resp = await cli.post("/action/execute", json=body, headers={"X-Local-Secret": G.SECRET})
    assert resp.status == 200, await resp.text()
    return await resp.json()


def _state_calls(bridge):
    return [c for c in bridge.calls if c["topic"].endswith("/state")]


@pytest.mark.asyncio
async def test_wiring_ac1_publier_publie_letat_avec_la_valeur_du_clic(aiohttp_client, tmp_path):
    cli, app, bridge = await _client_with_state_sync(aiohttp_client, tmp_path)
    await G._post_sync(cli, G._sync_body(G._load_golden_corpus(), request_id="golden"))
    bridge.calls.clear()

    await _publier_with_current_values(cli, "equipement", [3000], {"30003": "1"})

    assert _state_calls(bridge) == [
        {"topic": "jeedom2ha/3000/state", "payload": "ON", "retain": True}
    ]


@pytest.mark.asyncio
async def test_wiring_ac7_sans_current_values_aucun_etat_publie(aiohttp_client, tmp_path):
    cli, app, bridge = await _client_with_state_sync(aiohttp_client, tmp_path)
    await G._post_sync(cli, G._sync_body(G._load_golden_corpus(), request_id="golden"))
    bridge.calls.clear()

    body = {"intention": "publier", "portee": "equipement", "selection": [3000]}
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        resp = await cli.post("/action/execute", json=body, headers={"X-Local-Secret": G.SECRET})
    assert resp.status == 200

    assert _state_calls(bridge) == []


@pytest.mark.asyncio
async def test_wiring_ac7_current_values_liste_vide_aucun_etat_publie(aiohttp_client, tmp_path):
    cli, app, bridge = await _client_with_state_sync(aiohttp_client, tmp_path)
    await G._post_sync(cli, G._sync_body(G._load_golden_corpus(), request_id="golden"))
    bridge.calls.clear()

    await _publier_with_current_values(cli, "equipement", [3000], [])

    assert _state_calls(bridge) == []


@pytest.mark.asyncio
async def test_wiring_ac9_sync_publie_toujours_la_valeur_de_la_topologie(aiohttp_client, tmp_path):
    cli, app, bridge = await _client_with_state_sync(aiohttp_client, tmp_path)
    bridge.calls.clear()

    await G._post_sync(cli, G._sync_body(G._load_golden_corpus(), request_id="golden"))

    # eq 3000 (ENERGY_STATE=30003) n'a pas de current_value dans le corpus doré
    # (jamais streamé avant ce sync) : aucun état n'est donc publié pour lui — le sync
    # continue à publier depuis la topologie (comportement AC9 inchangé) pour les
    # autres équipements qui, eux, en ont une.
    assert "jeedom2ha/3000/state" not in [c["topic"] for c in _state_calls(bridge)]
    assert len(_state_calls(bridge)) > 0


# --- Revue ClaudeBox (PR #184) : AC10 câblé jusqu'au résultat du clic ---

class _StateFailingBridge(_StateRecordingBridge):
    """Discovery et disponibilité acceptées, publication des topics d'état en échec
    (pont annoncé connecté) : cas d'AC10."""

    def publish_message(self, topic, payload, qos=0, retain=False):
        if topic.startswith("jeedom2ha/") and topic.endswith("/state"):
            self.calls.append({"topic": topic, "payload": payload, "retain": retain, "ok": False})
            return False
        return super().publish_message(topic, payload, qos=qos, retain=retain)


@pytest.mark.asyncio
async def test_wiring_ac10_echec_etat_initial_rend_le_clic_en_erreur(aiohttp_client, tmp_path, caplog):
    app = create_app(local_secret=G.SECRET)
    app["data_dir"] = str(tmp_path)
    bridge = _StateFailingBridge()
    app["mqtt_bridge"] = bridge
    app["state_synchronizer"] = StateSynchronizer(app=app, mqtt_bridge=bridge)
    cli = await aiohttp_client(app)
    await G._post_sync(cli, G._sync_body(G._load_golden_corpus(), request_id="golden"))
    bridge.calls.clear()

    with caplog.at_level("WARNING"):
        payload = await _publier_with_current_values(cli, "equipement", [3000], {"30003": "1"})

    assert [c["topic"] for c in _state_calls(bridge)] == ["jeedom2ha/3000/state"]
    assert "initial_state_publish_failed" in caplog.text
    body = payload.get("payload", payload)
    assert body["resultat"] in ("echec", "succes_partiel")
    assert body["scope_reel"]["equipements_publies_ou_crees"] == 0


@pytest.mark.asyncio
async def test_wiring_ac10_temoin_meme_clic_sans_echec_reussit(aiohttp_client, tmp_path):
    cli, app, bridge = await _client_with_state_sync(aiohttp_client, tmp_path)
    await G._post_sync(cli, G._sync_body(G._load_golden_corpus(), request_id="golden"))
    bridge.calls.clear()

    payload = await _publier_with_current_values(cli, "equipement", [3000], {"30003": "1"})

    body = payload.get("payload", payload)
    assert body["resultat"] == "succes"
    assert body["scope_reel"]["equipements_publies_ou_crees"] == 1
