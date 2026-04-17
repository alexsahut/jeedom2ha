"""Story 5.2 PE — résultat de publication traçable.

Contrat vérifié :
- Le résultat technique de publication (étape 5) est enregistré dans un sous-bloc
  dédié `publication_result` sur le MappingResult.
- La décision produit (étape 4) reste intacte après toute issue de l'étape 5
  (succès, échec technique, non-tentée).
- La cause canonique issue des étapes 1–4 n'est jamais écrasée ni masquée.
- `pipeline_step_reached = 5` après l'étape 5.
- Non-régression sur les invariants I2/I4/I7 du pipeline.

AC couverts : AC1, AC2, AC3, AC4, AC5, AC6.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.mapping import PublicationDecision, PublicationResult
from transport.http_server import create_app


SECRET = "test-secret-pe-5-2-publication-result"


def _sync_body(eq_logics: list[dict]) -> dict:
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Salon"}],
            "eq_logics": eq_logics,
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "pe-5-2-test",
        "timestamp": "2026-04-17T00:00:00Z",
    }


def _light_eq(eq_id: int) -> dict:
    return {
        "id": eq_id,
        "name": f"Lumiere {eq_id}",
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": False,
        "status": {"timeout": 0},
        "cmds": [
            {"id": 1, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"},
            {"id": 2, "name": "Off", "generic_type": "LIGHT_OFF", "type": "action", "sub_type": "other"},
            {"id": 3, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
        ],
    }


def _ambiguous_light_eq(eq_id: int) -> dict:
    """Équipement ambiguous : commandes LIGHT_* ET FLAP_* → ambiguous_skipped."""
    return {
        "id": eq_id,
        "name": f"Ambigu {eq_id}",
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": False,
        "status": {"timeout": 0},
        "cmds": [
            {"id": 1, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"},
            {"id": 2, "name": "Off", "generic_type": "LIGHT_OFF", "type": "action", "sub_type": "other"},
            {"id": 3, "name": "Open", "generic_type": "FLAP_UP", "type": "action", "sub_type": "other"},
        ],
    }


def _probable_light_eq(eq_id: int) -> dict:
    """Équipement probable : LIGHT_STATE + LIGHT_ON (sans LIGHT_OFF)."""
    return {
        "id": eq_id,
        "name": f"Probable {eq_id}",
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": False,
        "status": {"timeout": 0},
        "cmds": [
            {"id": 1, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"},
            {"id": 3, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
        ],
    }


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _set_connected_bridge(app):
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge


def _get_mapping_and_decision(app, eq_id: int):
    mapping = app["mappings"][eq_id]
    decision = app["publications"][eq_id]
    return mapping, decision


# ---------------------------------------------------------------------------
# AC2 — Décision positive + publication OK → publication_result = success
# ---------------------------------------------------------------------------

async def test_publish_success_records_publication_result_success(cli, app):
    """AC2 — should_publish=True + broker OK → publication_result.status='success'."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=True)
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_light_eq(201)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    mapping, decision = _get_mapping_and_decision(app, 201)

    # AC1 — décision étape 4 intacte
    assert decision is not None
    assert decision.should_publish is True
    assert decision.reason in ("sure", "probable", "sure_mapping", "probable_bounded")

    # AC2 — résultat technique enregistré séparément
    assert mapping.publication_result is not None
    assert isinstance(mapping.publication_result, PublicationResult)
    assert mapping.publication_result.status == "success"
    assert mapping.publication_result.technical_reason_code is None
    assert mapping.publication_result.attempted_at is not None

    # Étape 5 atteinte
    assert mapping.pipeline_step_reached == 5

    # État runtime HA correct
    assert decision.active_or_alive is True
    assert decision.discovery_published is True


# ---------------------------------------------------------------------------
# AC2 + AC4 — Décision positive + publication échouée → publication_result = failed
# ---------------------------------------------------------------------------

async def test_publish_failed_records_publication_result_failed(cli, app):
    """AC2/AC4 — should_publish=True + broker KO → publication_result.status='failed'."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=False)  # échec MQTT
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_light_eq(202)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    mapping, decision = _get_mapping_and_decision(app, 202)

    # AC1 — décision étape 4 intacte : should_publish=True, reason canonique préservée
    assert decision is not None
    assert decision.should_publish is True
    assert decision.reason in ("sure", "probable", "sure_mapping", "probable_bounded")

    # AC2 — résultat technique enregistré séparément
    assert mapping.publication_result is not None
    assert mapping.publication_result.status == "failed"

    # AC4 — technical_reason_code distinct des reason_codes décisionnels
    assert mapping.publication_result.technical_reason_code == "discovery_publish_failed"
    assert mapping.publication_result.attempted_at is not None

    # Étape 5 atteinte
    assert mapping.pipeline_step_reached == 5

    # État runtime : non actif car publication échouée
    assert decision.active_or_alive is False


# ---------------------------------------------------------------------------
# AC1 — Invariant : should_publish et reason de l'étape 4 non modifiés après échec
# ---------------------------------------------------------------------------

async def test_publish_failed_does_not_modify_step4_decision(cli, app):
    """AC1 — l'échec technique étape 5 ne modifie jamais should_publish ni reason étape 4."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=False)
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_light_eq(203)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    mapping, decision = _get_mapping_and_decision(app, 203)

    # La décision étape 4 préserve should_publish=True
    assert decision.should_publish is True

    # Le reason_code de l'étape 4 n'est pas "discovery_publish_failed"
    assert decision.reason != "discovery_publish_failed"
    assert decision.reason != "local_availability_publish_failed"

    # Le résultat technique est dans publication_result, pas dans la décision
    assert mapping.publication_result.technical_reason_code == "discovery_publish_failed"
    assert decision.reason != mapping.publication_result.technical_reason_code


# ---------------------------------------------------------------------------
# AC3 — Décision négative → publication non tentée, cause canonique conservée
# ---------------------------------------------------------------------------

async def test_not_attempted_when_decision_negative(cli, app):
    """AC3 — should_publish=False → publication_result='not_attempted', cause canonique inchangée."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=True)
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_ambiguous_light_eq(204)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    mapping, decision = _get_mapping_and_decision(app, 204)

    # AC3 — publication non tentée
    assert decision is not None
    assert decision.should_publish is False
    assert decision.reason == "ambiguous_skipped"
    assert mapping.publication_result is not None
    assert mapping.publication_result.status == "not_attempted"
    assert mapping.publication_result.technical_reason_code is None
    assert mapping.pipeline_step_reached == 5
    mock_publisher.publish_light.assert_not_awaited()


# ---------------------------------------------------------------------------
# AC3 — Non-masquage : cause canonique prioritaire (I7 renforcé)
# ---------------------------------------------------------------------------

async def test_canonical_cause_not_masked_by_technical_failure(cli, app):
    """AC3/I7 — la cause canonique (étape 4) reste prioritaire même si étape 5 échoue."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=False)  # échec technique
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_light_eq(205)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    mapping, decision = _get_mapping_and_decision(app, 205)

    # La cause canonique (étape 4) est distincte du résultat technique
    canonical_reason = decision.reason
    technical_reason = mapping.publication_result.technical_reason_code

    assert canonical_reason != technical_reason
    assert technical_reason == "discovery_publish_failed"
    assert canonical_reason in ("sure", "probable", "sure_mapping", "probable_bounded")

    # Le reason_code technique est dans publication_result, jamais dans la décision étape 4
    assert decision.reason != "discovery_publish_failed"
    assert decision.should_publish is True  # décision étape 4 : toujours vouloir publier


# ---------------------------------------------------------------------------
# AC5 — Non-régression : invariants I2 et I4 du pipeline
# ---------------------------------------------------------------------------

async def test_i2_policy_block_never_publishes_and_not_attempted(cli, app):
    """AC5/I2 — décision négative (policy) → should_publish=False → publication_result='not_attempted'."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=True)
    payload = _sync_body([_probable_light_eq(206)])
    payload["payload"]["sync_config"]["confidence_policy"] = "sure_only"

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    mapping, decision = _get_mapping_and_decision(app, 206)

    # I2 : décision négative en étape 4 → should_publish=False
    assert decision.should_publish is False
    assert decision.reason == "probable_skipped"
    # Publication non tentée car décision négative
    assert mapping.publication_result is not None
    assert mapping.publication_result.status == "not_attempted"
    # Publish jamais appelé
    mock_publisher.publish_light.assert_not_awaited()
    # Étape 5 atteinte
    assert mapping.pipeline_step_reached == 5


async def test_i4_cause_etape2_not_overwritten_by_etape5(cli, app):
    """AC5/I4 — cause étape 2 (ambiguous_skipped) non écrasée par résultat étape 5."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=True)
    payload = _sync_body([_ambiguous_light_eq(207)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    mapping, decision = _get_mapping_and_decision(app, 207)
    assert decision is not None
    assert decision.reason == "ambiguous_skipped"
    assert decision.should_publish is False
    assert mapping.publication_result is not None
    assert mapping.publication_result.status == "not_attempted"
    assert mapping.publication_result.technical_reason_code is None
    mock_publisher.publish_light.assert_not_awaited()


async def test_failed_publish_exposes_technical_reason_in_diagnostics(cli, app):
    """Régression HIGH — échec technique étape 5 visible en diagnostics (reason/cause infra)."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=False)
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_light_eq(212)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        sync_resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert sync_resp.status == 200

    diag_resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    assert diag_resp.status == 200
    diag_body = await diag_resp.json()
    eq = next(item for item in diag_body["payload"]["equipments"] if item["eq_id"] == 212)

    assert eq["reason_code"] == "discovery_publish_failed"
    assert eq["status"] == "Incident infrastructure"
    assert eq["statut"] == "non_publie"
    assert eq["ecart"] is True
    assert eq["cause_code"] == "discovery_publish_failed"
    assert eq["traceability"]["publication_trace"]["technical_reason_code"] == "discovery_publish_failed"
    assert eq["traceability"]["publication_trace"]["last_discovery_publish_result"] == "failed"


async def test_failed_first_publish_does_not_trigger_cleanup_unpublish_on_next_sync(cli, app):
    """Régression MEDIUM — un échec initial jamais publié ne doit pas déclencher d'unpublish cleanup."""
    _set_connected_bridge(app)

    first_publisher = AsyncMock()
    first_publisher.publish_light = AsyncMock(return_value=False)
    first_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    with patch("transport.http_server.DiscoveryPublisher", return_value=first_publisher):
        first_resp = await cli.post(
            "/action/sync",
            json=_sync_body([_light_eq(213)]),
            headers={"X-Local-Secret": SECRET},
        )
    assert first_resp.status == 200

    mapping, decision = _get_mapping_and_decision(app, 213)
    assert mapping.publication_result is not None
    assert mapping.publication_result.status == "failed"
    assert decision.discovery_published is False

    second_publisher = AsyncMock()
    second_publisher.publish_light = AsyncMock(return_value=True)
    second_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    with patch("transport.http_server.DiscoveryPublisher", return_value=second_publisher):
        second_resp = await cli.post(
            "/action/sync",
            json=_sync_body([]),
            headers={"X-Local-Secret": SECRET},
        )
    assert second_resp.status == 200
    second_publisher.unpublish_by_eq_id.assert_not_awaited()


# ---------------------------------------------------------------------------
# AC5/AC6 — Testabilité isolée : pipeline_step_reached différencie les étapes
# ---------------------------------------------------------------------------

async def test_pipeline_step_reached_is_5_after_successful_publish(cli, app):
    """AC6 — pipeline_step_reached=5 après publication réussie."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=True)
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_light_eq(208)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    mapping = app["mappings"][208]
    assert mapping.pipeline_step_reached == 5
    assert mapping.publication_result is not None


async def test_pipeline_step_reached_is_5_after_failed_publish(cli, app):
    """AC6 — pipeline_step_reached=5 même après échec publication."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=False)
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_light_eq(209)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    mapping = app["mappings"][209]
    assert mapping.pipeline_step_reached == 5
    assert mapping.publication_result is not None
    assert mapping.publication_result.status == "failed"


# ---------------------------------------------------------------------------
# AC2 — Structure du sous-bloc PublicationResult
# ---------------------------------------------------------------------------

async def test_publication_result_is_dedicated_subbloc_not_on_decision(cli, app):
    """AC2 — publication_result est sur MappingResult, pas sur PublicationDecision."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=True)
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_light_eq(210)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    mapping, decision = _get_mapping_and_decision(app, 210)

    # Sous-bloc sur MappingResult (étape 5)
    assert hasattr(mapping, "publication_result")
    assert mapping.publication_result is not None

    # Pas de champ publication_result sur PublicationDecision
    assert not hasattr(decision, "publication_result")

    # Séparation structurelle : les deux sous-blocs sont distincts
    assert mapping.publication_result is not decision


# ---------------------------------------------------------------------------
# AC4 — Reason codes techniques distincts des reason codes décisionnels
# ---------------------------------------------------------------------------

async def test_technical_reason_codes_are_class4_and_distinct_from_decisional(cli, app):
    """AC4 — discovery_publish_failed est un technical_reason_code, jamais un reason décisionnel."""
    _set_connected_bridge(app)

    mock_publisher = AsyncMock()
    mock_publisher.publish_light = AsyncMock(return_value=False)
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    payload = _sync_body([_light_eq(211)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    mapping, decision = _get_mapping_and_decision(app, 211)

    # Reason codes décisionnels (étape 4) — ne doivent jamais contenir "discovery_publish_failed"
    _DECISIONAL_REASON_CODES = {
        "sure", "probable", "sure_mapping", "probable_bounded",
        "ambiguous_skipped", "probable_skipped", "unknown_skipped",
        "ha_missing_command_topic", "ha_missing_state_topic",
        "ha_component_not_in_product_scope", "no_mapping", "skipped_no_mapping_candidate",
    }
    assert decision.reason in _DECISIONAL_REASON_CODES

    # Reason codes techniques (étape 5) — dans publication_result uniquement
    assert mapping.publication_result.technical_reason_code == "discovery_publish_failed"
    assert mapping.publication_result.technical_reason_code not in _DECISIONAL_REASON_CODES


# ---------------------------------------------------------------------------
# AC3/I7 — Non-masquage : ambiguous_skipped + échec technique étape 5
# (test de régression pour violation AC3 — doit FAIL avant fix, PASS après)
# ---------------------------------------------------------------------------

def test_decision_trace_reason_code_is_canonical_not_technical_when_ambiguous_and_publish_fails():
    """AC3/I7 — decision_trace.reason_code = 'ambiguous_skipped', jamais 'discovery_publish_failed'.

    Cas : étape 4 décide should_publish=True avec reason='ambiguous_skipped',
    étape 5 échoue techniquement (discovery_publish_failed).
    La cause canonique doit rester visible dans decision_trace — pas le résultat technique.
    """
    from unittest.mock import MagicMock
    from models.mapping import PublicationDecision, PublicationResult, LightCapabilities
    from transport.http_server import _build_traceability

    # Simuler un équipement sans commandes (minimal)
    eq = MagicMock()
    eq.cmds = []

    # Créer la décision produit (étape 4) avec cause canonique = "ambiguous_skipped"
    pd = PublicationDecision(
        should_publish=True,
        reason="ambiguous_skipped",
        mapping_result=MagicMock(),
    )

    # Créer le résultat technique (étape 5) : échec MQTT
    pr = PublicationResult(
        status="failed",
        technical_reason_code="discovery_publish_failed",
        attempted_at="2026-04-17T00:00:00+00:00",
    )

    # map_result minimal avec publication_decision_ref et publication_result
    mr = MagicMock()
    mr.commands = {}
    mr.confidence = "sure"
    mr.ha_entity_type = "light"
    mr.publication_decision_ref = pd
    mr.publication_result = pr

    # status pré-calculé (comme le ferait le diagnostic handler)
    from models.taxonomy import get_primary_status
    status = get_primary_status("ambiguous_skipped")  # → "ambiguous"

    result = _build_traceability(eq, mr, pd, status, "ambiguous_skipped")

    decision_trace = result["decision_trace"]
    publication_trace = result["publication_trace"]

    # AC3/I7 — la cause canonique (étape 4) doit rester dans decision_trace
    assert decision_trace["reason_code"] == "ambiguous_skipped", (
        f"VIOLATION AC3 : decision_trace.reason_code == {decision_trace['reason_code']!r}, "
        "attendu 'ambiguous_skipped' — le résultat technique ne doit jamais masquer la cause canonique"
    )

    # Le résultat technique est bien exposé dans publication_trace uniquement
    assert publication_trace.get("technical_reason_code") == "discovery_publish_failed", (
        f"technical_reason_code absent ou incorrect dans publication_trace : {publication_trace}"
    )

    # Séparation stricte : les deux dimensions coexistent sans fusion
    assert decision_trace["reason_code"] != publication_trace.get("technical_reason_code")
