"""Story 8.4/9.1 - Golden-file gate de non-regression et extension sensor."""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from mapping.registry import MapperRegistry as RealMapperRegistry
from models.mapping import LightCapabilities, MappingResult
from transport.http_server import create_app

SECRET = "test-secret-story-8-4-golden"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus"
SYNC_FIXTURE_PATH = FIXTURES_DIR / "sync_payload.json"
EXPECTED_SNAPSHOT_PATH = FIXTURES_DIR / "expected_sync_snapshot.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_sync_body(payload: dict) -> dict:
    return {
        "action": "sync",
        "payload": payload,
        "request_id": "story-8-4-golden-fixture",
        "timestamp": "2026-05-04T00:00:00Z",
    }


def _connected_bridge(app) -> None:
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge


class _Story84MapperRegistry:
    """Registry double to force one in-scope governance block (ha_component_not_in_product_scope)."""

    def __init__(self) -> None:
        self._real = RealMapperRegistry()

    def map(self, eq, snapshot):
        if eq.id == 6001:
            commands = {c.generic_type: c for c in eq.cmds if c.generic_type}
            return MappingResult(
                ha_entity_type="climate",
                confidence="sure",
                reason_code="climate_forced_for_scope_gate",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=commands,
                capabilities=LightCapabilities(has_on_off=True),
            )
        return self._real.map(eq, snapshot)


def _normalize_volatiles(value):
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key == "request_id":
                normalized[key] = "<normalized-request-id>"
            elif key in {"timestamp", "attempted_at", "derniere_synchro_terminee"}:
                normalized[key] = "<normalized-timestamp>"
            else:
                normalized[key] = _normalize_volatiles(item)
        return normalized

    if isinstance(value, list):
        return [_normalize_volatiles(item) for item in value]

    return value


def _sorted_dict_by_int_key(data: dict) -> dict:
    return {
        str(eq_id): data[eq_id]
        for eq_id in sorted(data.keys())
    }


def _serialize_mapping(mapping) -> dict:
    commands = {
        role: {
            "id": cmd.id,
            "generic_type": cmd.generic_type,
            "type": cmd.type,
            "sub_type": cmd.sub_type,
        }
        for role, cmd in sorted(mapping.commands.items())
    }

    capabilities = {
        key: getattr(mapping.capabilities, key)
        for key in sorted(vars(mapping.capabilities).keys())
    }

    projection_validity = None
    if mapping.projection_validity is not None:
        projection_validity = {
            "is_valid": mapping.projection_validity.is_valid,
            "reason_code": mapping.projection_validity.reason_code,
            "missing_fields": list(mapping.projection_validity.missing_fields),
            "missing_capabilities": list(mapping.projection_validity.missing_capabilities),
        }

    publication_decision_ref = None
    if mapping.publication_decision_ref is not None:
        publication_decision_ref = {
            "should_publish": mapping.publication_decision_ref.should_publish,
            "reason": mapping.publication_decision_ref.reason,
            "state_topic": mapping.publication_decision_ref.state_topic,
            "active_or_alive": mapping.publication_decision_ref.active_or_alive,
            "discovery_published": mapping.publication_decision_ref.discovery_published,
            "bridge_availability_topic": mapping.publication_decision_ref.bridge_availability_topic,
            "eqlogic_availability_topic": mapping.publication_decision_ref.eqlogic_availability_topic,
            "local_availability_supported": mapping.publication_decision_ref.local_availability_supported,
            "local_availability_state": mapping.publication_decision_ref.local_availability_state,
            "availability_reason": mapping.publication_decision_ref.availability_reason,
        }

    publication_result = None
    if mapping.publication_result is not None:
        publication_result = {
            "status": mapping.publication_result.status,
            "technical_reason_code": mapping.publication_result.technical_reason_code,
            "attempted_at": mapping.publication_result.attempted_at,
        }

    return {
        "ha_entity_type": mapping.ha_entity_type,
        "confidence": mapping.confidence,
        "reason_code": mapping.reason_code,
        "jeedom_eq_id": mapping.jeedom_eq_id,
        "ha_unique_id": mapping.ha_unique_id,
        "ha_name": mapping.ha_name,
        "suggested_area": mapping.suggested_area,
        "commands": commands,
        "capabilities": capabilities,
        "reason_details": mapping.reason_details,
        "projection_validity": projection_validity,
        "publication_decision_ref": publication_decision_ref,
        "pipeline_step_reached": mapping.pipeline_step_reached,
        "publication_result": publication_result,
    }


def _serialize_publication(decision) -> dict:
    return {
        "should_publish": decision.should_publish,
        "reason": decision.reason,
        "state_topic": decision.state_topic,
        "active_or_alive": decision.active_or_alive,
        "discovery_published": decision.discovery_published,
        "bridge_availability_topic": decision.bridge_availability_topic,
        "eqlogic_availability_topic": decision.eqlogic_availability_topic,
        "local_availability_supported": decision.local_availability_supported,
        "local_availability_state": decision.local_availability_state,
        "availability_reason": decision.availability_reason,
        "mapping_ref": {
            "jeedom_eq_id": decision.mapping_result.jeedom_eq_id,
            "ha_entity_type": decision.mapping_result.ha_entity_type,
            "reason_code": decision.mapping_result.reason_code,
            "confidence": decision.mapping_result.confidence,
        }
        if decision.mapping_result is not None
        else None,
    }


def _canonicalize_diagnostics_payload(payload: dict) -> dict:
    canonical = dict(payload)
    canonical["equipments"] = sorted(payload.get("equipments", []), key=lambda item: item.get("eq_id", 0))
    canonical["in_scope_equipments"] = sorted(
        payload.get("in_scope_equipments", []),
        key=lambda item: item.get("eq_id", 0),
    )
    canonical["rooms"] = sorted(payload.get("rooms", []), key=lambda item: item.get("object_id", 0))
    return canonical


def _build_canonical_snapshot(sync_response: dict, diagnostics_response: dict, app) -> dict:
    serialized_mappings = {
        eq_id: _serialize_mapping(mapping)
        for eq_id, mapping in app["mappings"].items()
    }
    serialized_publications = {
        eq_id: _serialize_publication(decision)
        for eq_id, decision in app["publications"].items()
    }

    snapshot = {
        "meta": {
            "story": "8.4",
            "fixture": "sync_payload.json",
            "normalization": {
                "request_id": True,
                "timestamp": True,
                "publication_attempted_at": True,
                "derniere_synchro_terminee": True,
            },
        },
        "sync": {
            "action": sync_response["action"],
            "status": sync_response["status"],
            "request_id": sync_response["request_id"],
            "timestamp": sync_response["timestamp"],
            "payload": sync_response["payload"],
        },
        "diagnostics": {
            "action": diagnostics_response["action"],
            "status": diagnostics_response["status"],
            "request_id": diagnostics_response["request_id"],
            "timestamp": diagnostics_response["timestamp"],
            "payload": _canonicalize_diagnostics_payload(diagnostics_response["payload"]),
        },
        "runtime": {
            "derniere_synchro_terminee": app.get("derniere_synchro_terminee"),
            "mappings": _sorted_dict_by_int_key(serialized_mappings),
            "publications": _sorted_dict_by_int_key(serialized_publications),
            "mapping_counters": sync_response["payload"].get("mapping_summary", {}),
        },
    }

    return _normalize_volatiles(snapshot)


def _assert_corpus_shape(sync_payload: dict) -> None:
    eq_ids = {eq["id"] for eq in sync_payload["eq_logics"]}
    assert len(eq_ids) == 40

    assert len([i for i in eq_ids if 1000 <= i <= 1009]) == 10
    assert len([i for i in eq_ids if 2000 <= i <= 2007]) == 8
    assert len([i for i in eq_ids if 3000 <= i <= 3004]) == 5
    assert len([i for i in eq_ids if 4000 <= i <= 4002]) == 3
    assert len([i for i in eq_ids if 5000 <= i <= 5001]) == 2
    assert len([i for i in eq_ids if 6000 <= i <= 6001]) == 2
    assert len([i for i in eq_ids if 7000 <= i <= 7004]) == 5
    assert len([i for i in eq_ids if 8000 <= i <= 8004]) == 5


async def test_story_8_4_golden_file_non_regression_snapshot(aiohttp_client):
    app = create_app(local_secret=SECRET)
    _connected_bridge(app)
    client = await aiohttp_client(app)

    sync_payload = _load_json(SYNC_FIXTURE_PATH)
    expected_snapshot = _load_json(EXPECTED_SNAPSHOT_PATH)
    _assert_corpus_shape(sync_payload)

    with patch("transport.http_server.MapperRegistry", _Story84MapperRegistry), patch(
        "transport.http_server.save_publications_cache",
    ):
        sync_resp = await client.post(
            "/action/sync",
            json=_build_sync_body(sync_payload),
            headers={"X-Local-Secret": SECRET},
        )

        assert sync_resp.status == 200
        sync_json = await sync_resp.json()

        diagnostics_resp = await client.get(
            "/system/diagnostics",
            headers={"X-Local-Secret": SECRET},
        )
        assert diagnostics_resp.status == 200
        diagnostics_json = await diagnostics_resp.json()

    assert 5000 not in app["mappings"]
    assert 5001 not in app["mappings"]

    diagnostics_by_id = {
        item["eq_id"]: item
        for item in diagnostics_json["payload"]["equipments"]
    }
    assert diagnostics_by_id[6000]["reason_code"] == "ha_missing_command_topic"
    assert diagnostics_by_id[6001]["reason_code"] == "ha_component_not_in_product_scope"

    mapping_summary = sync_json["payload"]["mapping_summary"]
    assert "lights_sure" in mapping_summary
    assert "covers_sure" in mapping_summary
    assert "switches_sure" in mapping_summary
    assert "sensors_sure" in mapping_summary

    current_snapshot = _build_canonical_snapshot(sync_json, diagnostics_json, app)

    expected_text = json.dumps(expected_snapshot, indent=2, sort_keys=True) + "\n"
    current_text = json.dumps(current_snapshot, indent=2, sort_keys=True) + "\n"

    if current_text != expected_text:
        diff = "\n".join(
            difflib.unified_diff(
                expected_text.splitlines(),
                current_text.splitlines(),
                fromfile=str(EXPECTED_SNAPSHOT_PATH),
                tofile="current_runtime_snapshot",
                lineterm="",
            )
        )
        raise AssertionError(
            "Drift golden-file detecte sur Story 8.4. "
            "Toute divergence est bloquante pour pe-epic-8.\n\n"
            f"{diff}"
        )
