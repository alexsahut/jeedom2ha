"""Unit tests for Story 4.3 — Exclusion multicritères et politique de confiance.

Couvre :
- assess_eligibility() : les 3 reason_codes d'exclusion
- Priorité exclusion : eqlogic > plugin > object
- Rétro-compatibilité : exclusion_source absent → "excluded_eqlogic"
- decide_publication() sur les 3 mappers : sure_only / sure_probable / défaut
- Dépublication sur changement de policy (AC B.2)
- _handle_system_diagnostics : excluded_plugin / excluded_object → "Exclu"
- _CLOSED_REASON_MAP : nouveaux codes → "excluded"
- Non-régression : exclusion individuelle inchangée
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.topology import (
    JeedomCmd, JeedomEqLogic, TopologySnapshot, JeedomObject,
    assess_eligibility, EligibilityResult,
)
from models.mapping import MappingResult, PublicationDecision, LightCapabilities
from mapping.light import LightMapper
from mapping.cover import CoverMapper
from mapping.switch import SwitchMapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_eq(id=1, is_excluded=False, exclusion_source=None, is_enable=True, cmds=None):
    return JeedomEqLogic(
        id=id,
        name="Test",
        is_excluded=is_excluded,
        exclusion_source=exclusion_source,
        is_enable=is_enable,
        cmds=cmds or [],
    )


def _make_light_mapping(eq_id=1, confidence="probable"):
    return MappingResult(
        ha_entity_type="light",
        confidence=confidence,
        reason_code="light_on_off_only",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name="Test Light",
        capabilities=LightCapabilities(has_on_off=True),
    )


def _make_cover_mapping(eq_id=1, confidence="probable"):
    from models.mapping import CoverCapabilities
    return MappingResult(
        ha_entity_type="cover",
        confidence=confidence,
        reason_code="cover_open_close",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name="Test Cover",
        capabilities=CoverCapabilities(has_open_close=True),
    )


def _make_switch_mapping(eq_id=1, confidence="probable"):
    from models.mapping import SwitchCapabilities
    return MappingResult(
        ha_entity_type="switch",
        confidence=confidence,
        reason_code="switch_on_off_only",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name="Test Switch",
        capabilities=SwitchCapabilities(has_on_off=True, device_class=None),
    )


# ---------------------------------------------------------------------------
# assess_eligibility() — les 3 reason_codes d'exclusion
# ---------------------------------------------------------------------------

def test_assess_eligibility_excluded_eqlogic():
    eq = _make_eq(is_excluded=True, exclusion_source="eqlogic")
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"
    assert not result.is_eligible
    assert result.confidence == "sure"


def test_assess_eligibility_excluded_plugin():
    eq = _make_eq(is_excluded=True, exclusion_source="plugin")
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_plugin"
    assert not result.is_eligible
    assert result.confidence == "sure"


def test_assess_eligibility_excluded_object():
    eq = _make_eq(is_excluded=True, exclusion_source="object")
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_object"
    assert not result.is_eligible
    assert result.confidence == "sure"


def test_assess_eligibility_no_source_defaults_to_eqlogic():
    """Rétro-compatibilité : exclusion_source absent → "excluded_eqlogic"."""
    eq = _make_eq(is_excluded=True, exclusion_source=None)
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"
    assert not result.is_eligible


# ---------------------------------------------------------------------------
# Priorité d'exclusion : eqlogic > plugin > object
# ---------------------------------------------------------------------------

def test_exclusion_priority_eqlogic_wins():
    """exclusion_source="eqlogic" → reason_code="excluded_eqlogic" (priorité 1)."""
    eq = _make_eq(is_excluded=True, exclusion_source="eqlogic")
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"


def test_exclusion_priority_plugin():
    """exclusion_source="plugin" → reason_code="excluded_plugin" (priorité 2)."""
    eq = _make_eq(is_excluded=True, exclusion_source="plugin")
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_plugin"


def test_exclusion_priority_object():
    """exclusion_source="object" → reason_code="excluded_object" (priorité 3)."""
    eq = _make_eq(is_excluded=True, exclusion_source="object")
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_object"


# ---------------------------------------------------------------------------
# decide_publication() — politique de confiance sur les 3 mappers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("MapperClass,make_mapping", [
    (LightMapper, _make_light_mapping),
    (CoverMapper, _make_cover_mapping),
    (SwitchMapper, _make_switch_mapping),
])
def test_decide_publication_sure_only_blocks_probable(MapperClass, make_mapping):
    """sure_only bloque probable sur tous les mappers."""
    mapper = MapperClass()
    mapping = make_mapping(confidence="probable")
    decision = mapper.decide_publication(mapping, confidence_policy="sure_only")
    assert not decision.should_publish


@pytest.mark.parametrize("MapperClass,make_mapping", [
    (LightMapper, _make_light_mapping),
    (CoverMapper, _make_cover_mapping),
    (SwitchMapper, _make_switch_mapping),
])
def test_decide_publication_sure_probable_allows_probable(MapperClass, make_mapping):
    """sure_probable autorise probable sur tous les mappers."""
    mapper = MapperClass()
    mapping = make_mapping(confidence="probable")
    decision = mapper.decide_publication(mapping, confidence_policy="sure_probable")
    assert decision.should_publish


@pytest.mark.parametrize("MapperClass,make_mapping", [
    (LightMapper, _make_light_mapping),
    (CoverMapper, _make_cover_mapping),
    (SwitchMapper, _make_switch_mapping),
])
def test_decide_publication_default_policy_allows_probable(MapperClass, make_mapping):
    """Appel sans confidence_policy → défaut sure_probable → probable autorisé (non-régression)."""
    mapper = MapperClass()
    mapping = make_mapping(confidence="probable")
    decision = mapper.decide_publication(mapping)
    assert decision.should_publish


@pytest.mark.parametrize("MapperClass,make_mapping", [
    (LightMapper, _make_light_mapping),
    (CoverMapper, _make_cover_mapping),
    (SwitchMapper, _make_switch_mapping),
])
def test_decide_publication_sure_only_still_allows_sure(MapperClass, make_mapping):
    """sure_only n'affecte pas les équipements sûrs."""
    mapper = MapperClass()
    mapping = make_mapping(confidence="sure")
    decision = mapper.decide_publication(mapping, confidence_policy="sure_only")
    assert decision.should_publish


def test_decide_publication_does_not_mutate_module_constant():
    """La constante module LIGHT_PUBLICATION_POLICY ne doit pas être modifiée."""
    from mapping.light import LIGHT_PUBLICATION_POLICY
    original_probable = LIGHT_PUBLICATION_POLICY["probable"]
    mapper = LightMapper()
    mapping = _make_light_mapping(confidence="probable")
    mapper.decide_publication(mapping, confidence_policy="sure_only")
    # La constante doit être inchangée
    assert LIGHT_PUBLICATION_POLICY["probable"] == original_probable


# ---------------------------------------------------------------------------
# Dépublication sur changement de policy (AC B.2) — test via _handle_action_sync
# ---------------------------------------------------------------------------

async def test_policy_change_probable_to_sure_only_triggers_unpublish(aiohttp_client):
    """AC B.2 : équipement probable précédemment publié → unpublish lors du passage à sure_only."""
    from transport.http_server import create_app

    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    # Simuler un état précédent : eq_id=10, publié avec confidence "probable"
    prev_mapping = _make_light_mapping(eq_id=10, confidence="probable")
    prev_decision = PublicationDecision(
        should_publish=True,
        reason="probable",
        mapping_result=prev_mapping,
        active_or_alive=True,
        discovery_published=True,
    )
    app["publications"][10] = prev_decision
    app["mappings"][10] = prev_mapping

    # Mocker le publisher pour intercepter les appels unpublish
    mock_publisher = AsyncMock()
    mock_publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    mock_publisher.publish_light = AsyncMock(return_value=True)
    mock_publisher.publish_cover = AsyncMock(return_value=True)
    mock_publisher.publish_switch = AsyncMock(return_value=True)

    # Mocker le mqtt_bridge comme connecté
    mock_bridge = MagicMock()
    mock_bridge.is_connected = True
    mock_bridge.state = "connected"
    app["mqtt_bridge"] = mock_bridge

    # Payload topology : LIGHT_STATE + LIGHT_ON sans LIGHT_OFF → confidence "probable"
    # (state+on missing off). Avec sure_only, cette lumière sera bloquée → unpublish.
    cmd_on = {"id": 101, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"}
    cmd_state = {"id": 103, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"}
    payload = {
        "objects": [{"id": 1, "name": "Salon"}],
        "eq_logics": [{
            "id": 10,
            "name": "Lumiere Probable",
            "object_id": 1,
            "is_enable": True,
            "is_visible": True,
            "eq_type": "virtual",
            "is_excluded": False,
            "status": {"timeout": 0},
            "cmds": [cmd_on, cmd_state],
        }],
        "sync_config": {"confidence_policy": "sure_only"},
    }

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post(
            "/action/sync",
            json={"action": "sync", "payload": payload, "request_id": "test-123", "timestamp": "2026-03-19T00:00:00Z"},
            headers={"X-Local-Secret": "test_secret"},
        )

    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"

    # Vérifier que unpublish_by_eq_id a été appelé pour l'équipement probable
    mock_publisher.unpublish_by_eq_id.assert_called_once_with(10, entity_type="light")


# ---------------------------------------------------------------------------
# _handle_system_diagnostics : excluded_plugin / excluded_object → "Exclu"
# ---------------------------------------------------------------------------

async def test_diagnostic_excluded_plugin_shows_exclu_status(aiohttp_client):
    """excluded_plugin → statut 'Exclu' dans le diagnostic."""
    from transport.http_server import create_app

    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-19T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            200: JeedomEqLogic(id=200, name="Eq Plugin Exclu", object_id=1,
                               is_excluded=True, exclusion_source="plugin"),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {200: EligibilityResult(is_eligible=False, reason_code="excluded_plugin")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 200)

    assert eq["status"] == "Exclu"
    assert eq["reason_code"] == "excluded_plugin"
    assert eq["detail"] != ""
    assert eq["remediation"] != ""
    assert "plugin" in eq["detail"].lower()


async def test_diagnostic_excluded_object_shows_exclu_status(aiohttp_client):
    """excluded_object → statut 'Exclu' dans le diagnostic."""
    from transport.http_server import create_app

    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-19T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Chambre")},
        eq_logics={
            201: JeedomEqLogic(id=201, name="Eq Object Exclu", object_id=1,
                               is_excluded=True, exclusion_source="object"),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {201: EligibilityResult(is_eligible=False, reason_code="excluded_object")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 201)

    assert eq["status"] == "Exclu"
    assert eq["reason_code"] == "excluded_object"
    assert eq["detail"] != ""
    assert "pièce" in eq["detail"].lower() or "objet" in eq["detail"].lower()


# ---------------------------------------------------------------------------
# _CLOSED_REASON_MAP — nouveaux codes → "excluded"
# ---------------------------------------------------------------------------

def test_closed_reason_map_excluded_plugin():
    from transport.http_server import _CLOSED_REASON_MAP
    assert _CLOSED_REASON_MAP["excluded_plugin"] == "excluded"


def test_closed_reason_map_excluded_object():
    from transport.http_server import _CLOSED_REASON_MAP
    assert _CLOSED_REASON_MAP["excluded_object"] == "excluded"


def test_excluded_reason_codes_in_closed_reason_map():
    """_CLOSED_REASON_MAP contient les 3 codes d'exclusion mappés vers 'excluded'."""
    from transport.http_server import _CLOSED_REASON_MAP
    assert _CLOSED_REASON_MAP["excluded_eqlogic"] == "excluded"
    assert _CLOSED_REASON_MAP["excluded_plugin"] == "excluded"
    assert _CLOSED_REASON_MAP["excluded_object"] == "excluded"


# ---------------------------------------------------------------------------
# Non-régression : exclusion individuelle (jeedom2ha_excluded) inchangée
# ---------------------------------------------------------------------------

def test_non_regression_individual_exclusion_unchanged():
    """exclusion individuelle (exclusion_source=eqlogic) → excluded_eqlogic inchangé."""
    eq = JeedomEqLogic(
        id=99, name="Test Individuel",
        is_excluded=True, exclusion_source="eqlogic",
        cmds=[],
    )
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"
    assert not result.is_eligible


def test_non_regression_excluded_eqlogic_no_source():
    """Équipement exclu sans exclusion_source (anciens payloads) → excluded_eqlogic."""
    eq = JeedomEqLogic(id=98, name="Test Legacy", is_excluded=True, cmds=[])
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"


# ---------------------------------------------------------------------------
# Non-régression : traceability pour excluded_plugin / excluded_object
# ---------------------------------------------------------------------------

async def test_diagnostics_traceability_excluded_plugin(aiohttp_client):
    """AC1/AC2 — traceability.decision_trace.reason_code = "excluded" pour excluded_plugin."""
    from transport.http_server import create_app

    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-19T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            300: JeedomEqLogic(id=300, name="Eq Plugin Exclu Trace", object_id=1,
                               is_excluded=True, exclusion_source="plugin"),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {300: EligibilityResult(is_eligible=False, reason_code="excluded_plugin")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 300)

    tr = eq["traceability"]
    dt = tr["decision_trace"]
    assert dt["reason_code"] == "excluded"  # AC2: excluded_plugin → "excluded" dans taxonomie fermée


async def test_diagnostics_traceability_excluded_object(aiohttp_client):
    """AC1/AC2 — traceability.decision_trace.reason_code = "excluded" pour excluded_object."""
    from transport.http_server import create_app

    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-19T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Chambre")},
        eq_logics={
            301: JeedomEqLogic(id=301, name="Eq Object Exclu Trace", object_id=1,
                               is_excluded=True, exclusion_source="object"),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {301: EligibilityResult(is_eligible=False, reason_code="excluded_object")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 301)

    dt = eq["traceability"]["decision_trace"]
    assert dt["reason_code"] == "excluded"


# ---------------------------------------------------------------------------
# probable_skipped — diagnostic enrichi (H1) + traceability (H2)
# ---------------------------------------------------------------------------

def test_diagnostic_messages_probable_skipped_exists():
    """_DIAGNOSTIC_MESSAGES contient une entrée pour probable_skipped."""
    from transport.http_server import _DIAGNOSTIC_MESSAGES
    entry = _DIAGNOSTIC_MESSAGES.get("probable_skipped")
    assert entry is not None
    detail, remediation, v1_limitation = entry
    assert "probable" in detail.lower()
    assert "sûr uniquement" in detail.lower() or "sure_only" in detail.lower()
    assert v1_limitation is False


def test_closed_reason_map_probable_skipped():
    """_CLOSED_REASON_MAP normalise probable_skipped → confidence_policy_skipped."""
    from transport.http_server import _CLOSED_REASON_MAP
    assert _CLOSED_REASON_MAP["probable_skipped"] == "confidence_policy_skipped"


async def test_diagnostic_probable_skipped_shows_correct_detail(aiohttp_client):
    """Équipement probable bloqué par sure_only → diagnostic avec detail/remediation corrects."""
    from transport.http_server import create_app

    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    # Simuler un équipement éligible, mappé en light probable, bloqué par sure_only
    snapshot = TopologySnapshot(
        timestamp="2026-03-19T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            400: JeedomEqLogic(
                id=400, name="Lumiere Probable", object_id=1,
                is_enable=True,
                cmds=[
                    JeedomCmd(id=401, name="On", generic_type="LIGHT_ON", type="action", sub_type="other"),
                    JeedomCmd(id=402, name="Etat", generic_type="LIGHT_STATE", type="info", sub_type="binary"),
                ],
            ),
        },
    )
    app["topology"] = snapshot

    # Eligibility: éligible
    app["eligibility"] = {400: EligibilityResult(is_eligible=True, reason_code="eligible")}

    # Mapping: light probable (state+on missing off)
    mapping = _make_light_mapping(eq_id=400, confidence="probable")
    app["mappings"] = {400: mapping}

    # Publication: bloqué par sure_only → should_publish=False, reason=probable_skipped
    decision = PublicationDecision(
        should_publish=False,
        reason="probable_skipped",
        mapping_result=mapping,
        active_or_alive=False,
    )
    app["publications"] = {400: decision}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 400)

    # H1: detail et remediation explicites (pas "Cause inconnue")
    # Story 3.1 : probable_skipped → "Ambigu" (pas "Non publié")
    assert eq["status"] == "Ambigu"
    assert eq["reason_code"] == "probable_skipped"
    assert "probable" in eq["detail"].lower()
    assert "sûr uniquement" in eq["detail"].lower() or "sure_only" in eq["detail"].lower()
    assert eq["remediation"] != ""
    assert "Cause inconnue" not in eq["detail"]

    # H2: traceability correcte (pas discovery_publish_failed)
    dt = eq["traceability"]["decision_trace"]
    assert dt["reason_code"] == "confidence_policy_skipped"
    assert dt["reason_code"] != "discovery_publish_failed"
