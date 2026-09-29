"""Story 19-2b — disponibilite locale publiee quand seuls des secondaires publient.

Defaut terrain (eq 579/585) : quand le principal est refuse (ambiguous_skipped) mais
qu'au moins un secondaire est publie, `jeedom2ha/<eq>/availability` n'etait jamais
publie -> les secondaires restent `unavailable` dans HA (availability_mode="all").

Invariant attendu : la disponibilite locale est publiee des qu'au moins un candidat
(principal ou secondaire) est publie.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_FIXTURE_PATH = (
    Path(__file__).parent / "test_story_19_2_decouplage_state_command_i11.py"
)
_spec = importlib.util.spec_from_file_location("_story_19_2_fixture", _FIXTURE_PATH)
_fixture_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture_module)
_build_multi_switch = _fixture_module._build_multi_switch


def _make_evaluation(primary, primary_decision):
    from models.evaluate_equipment import EquipmentEvaluation

    secondary_decisions = [
        sec.publication_decision_ref for sec in primary.additional_mappings
    ]
    return EquipmentEvaluation(
        mapping=primary,
        equipment_decision=primary_decision,
        secondary_decisions=secondary_decisions,
    )


def _mock_publisher():
    mock_publisher = AsyncMock()
    mock_publisher.publish_switch = AsyncMock(return_value=True)
    mock_publisher.publish_light = AsyncMock(return_value=True)
    mock_publisher.publish_cover = AsyncMock(return_value=True)
    return mock_publisher


def _sync_payload():
    return {
        "objects": [{"id": 1, "name": "Energie"}],
        "eq_logics": [{
            "id": 628,
            "name": "Pilotage priorisation solaire",
            "object_id": 1,
            "is_enable": True,
            "is_visible": True,
            "eq_type": "virtual",
            "is_excluded": False,
            "status": {"timeout": 0},
            "cmds": [{
                "id": 5977, "name": "Filtration piscine", "type": "info",
                "sub_type": "binary", "generic_type": "SWITCH_STATE",
            }],
        }],
        "sync_config": {"confidence_policy": "sure_probable"},
    }


async def _run_sync(aiohttp_client, evaluation):
    from transport.http_server import create_app

    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    mock_bridge = MagicMock()
    mock_bridge.is_connected = True
    mock_bridge.state = "connected"
    mock_bridge.published = []

    def _publish_message(topic, payload, qos=0, retain=False):
        mock_bridge.published.append((topic, payload, qos, retain))
        return True

    mock_bridge.publish_message = MagicMock(side_effect=_publish_message)
    app["mqtt_bridge"] = mock_bridge

    mock_publisher = _mock_publisher()

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher), \
         patch("transport.http_server.evaluate_equipment", return_value=evaluation):
        resp1 = await cli.post(
            "/action/sync",
            json={"action": "sync", "payload": _sync_payload(),
                  "request_id": "t1", "timestamp": "2026-09-29T00:00:00Z"},
            headers={"X-Local-Secret": "test_secret"},
        )
        assert resp1.status == 200

        resp2 = await cli.post(
            "/action/sync",
            json={"action": "sync", "payload": _sync_payload(),
                  "request_id": "t2", "timestamp": "2026-09-29T00:01:00Z"},
            headers={"X-Local-Secret": "test_secret"},
        )
        assert resp2.status == 200

    return mock_bridge.published


def _availability_publishes(published, eq_id=628):
    topic = f"jeedom2ha/{eq_id}/availability"
    return [entry for entry in published if entry[0] == topic]


@pytest.mark.asyncio
async def test_case_a_principal_refuse_secondaire_publie(aiohttp_client):
    """Principal refuse / secondaires acceptes -> availability publiee, retain, 1x/sync."""
    primary, primary_decision = _build_multi_switch(principal_should_publish=False)
    primary_decision.local_availability_supported = True
    primary_decision.local_availability_state = "online"
    primary_decision.eqlogic_availability_topic = "jeedom2ha/628/availability"

    evaluation = _make_evaluation(primary, primary_decision)
    published = await _run_sync(aiohttp_client, evaluation)

    avail = _availability_publishes(published)
    assert len(avail) == 2, f"attendu 1 publication par sync (2 syncs), obtenu: {avail}"
    for topic, payload, qos, retain in avail:
        assert payload == "online"
        assert retain is True


@pytest.mark.asyncio
async def test_case_b_principal_et_secondaires_refuses(aiohttp_client):
    """Principal refuse et tous les secondaires refuses -> aucune publication d'availability."""
    probe, _ = _build_multi_switch(principal_should_publish=False)
    all_secondary_cmd_ids = frozenset(
        sec.reason_details["cmd_id"] for sec in probe.additional_mappings
    )
    primary, primary_decision = _build_multi_switch(
        principal_should_publish=False,
        refused_cmd_ids=all_secondary_cmd_ids,
    )
    primary_decision.local_availability_supported = True
    primary_decision.local_availability_state = "online"
    primary_decision.eqlogic_availability_topic = "jeedom2ha/628/availability"

    evaluation = _make_evaluation(primary, primary_decision)
    published = await _run_sync(aiohttp_client, evaluation)

    assert _availability_publishes(published) == []


@pytest.mark.asyncio
async def test_case_c_principal_publie_comportement_inchange(aiohttp_client):
    """Principal publie -> comportement inchange (une seule publication d'availability)."""
    primary, primary_decision = _build_multi_switch(principal_should_publish=True)
    primary_decision.local_availability_supported = True
    primary_decision.local_availability_state = "online"
    primary_decision.eqlogic_availability_topic = "jeedom2ha/628/availability"

    evaluation = _make_evaluation(primary, primary_decision)
    published = await _run_sync(aiohttp_client, evaluation)

    avail = _availability_publishes(published)
    assert len(avail) == 2
    for topic, payload, qos, retain in avail:
        assert payload == "online"
        assert retain is True
