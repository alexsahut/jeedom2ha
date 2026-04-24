"""Unit tests for Story 4.4 — Diagnostic Export.

Tests:
  - /system/status: python_version présent, format X.Y.Z
  - /system/status: non-régression version, uptime, mqtt
  - /system/diagnostics: status_code présent dans chaque équipement
  - /system/diagnostics: valeurs status_code dans l'enum attendu
  - /system/diagnostics: non-régression champs existants
"""

import sys

import pytest
from aiohttp import web
from unittest.mock import MagicMock

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd, EligibilityResult
)
from models.mapping import MappingResult, ProjectionValidity, PublicationDecision, LightCapabilities

# Story 3.1 : taxonomie fermée à 5 statuts — plus de "partially_published" ni "not_published"
_VALID_STATUS_CODES = {"published", "excluded", "ambiguous", "not_supported", "infra_incident"}

# ---------------------------------------------------------------------------
# /system/status — python_version (Task 1.1 / 1.2)
# ---------------------------------------------------------------------------

async def test_system_status_python_version_present(aiohttp_client):
    """/system/status doit exposer python_version dans le payload."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/status", headers={"X-Local-Secret": "test_secret"})
    assert resp.status == 200
    data = await resp.json()

    assert data["status"] == "ok"
    assert "python_version" in data["payload"]


async def test_system_status_python_version_format(aiohttp_client):
    """python_version doit être au format X.Y.Z (trois composants numériques)."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/status", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    pv = data["payload"]["python_version"]
    parts = pv.split(".")
    assert len(parts) == 3, f"Format attendu X.Y.Z, obtenu : {pv}"
    for part in parts:
        assert part.isdigit(), f"Composant non numérique dans python_version : {pv}"


async def test_system_status_python_version_matches_runtime(aiohttp_client):
    """python_version doit correspondre à sys.version_info du process courant."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/status", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    assert data["payload"]["python_version"] == expected


async def test_system_status_non_regression_existing_fields(aiohttp_client):
    """Non-régression : version, uptime et mqtt toujours présents dans le payload."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/status", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    payload = data["payload"]
    assert "version" in payload
    assert "uptime" in payload
    assert "mqtt" in payload
    # uptime est un nombre
    assert isinstance(payload["uptime"], (int, float))


# ---------------------------------------------------------------------------
# /system/diagnostics — status_code (Task 1.3)
# ---------------------------------------------------------------------------

def _make_simple_app_with_published_eq():
    """Crée une app avec un équipement publié, un exclu, un non publié."""
    app = create_app(local_secret="test_secret")

    cmd = JeedomCmd(id=1001, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-20T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            10: JeedomEqLogic(id=10, name="Lumiere", object_id=1, is_enable=True, cmds=[cmd]),
            11: JeedomEqLogic(id=11, name="Eq Exclu", object_id=1, is_excluded=True),
            12: JeedomEqLogic(id=12, name="Eq Non Publie", object_id=1, is_enable=True),
        }
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=10,
        ha_unique_id="light_10",
        ha_name="Lumiere",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    mapping_res.projection_validity = ProjectionValidity(
        is_valid=True,
        reason_code=None,
        missing_fields=[],
        missing_capabilities=[],
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        10: EligibilityResult(is_eligible=True, reason_code="eligible"),
        11: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
        12: EligibilityResult(is_eligible=False, reason_code="no_commands"),
    }
    app["mappings"] = {10: mapping_res}
    app["publications"] = {
        10: PublicationDecision(
            should_publish=True,
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }
    return app


async def test_diagnostics_status_code_present_in_all_equipments(aiohttp_client):
    """status_code doit être présent dans chaque entrée équipement."""
    app = _make_simple_app_with_published_eq()
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    assert data["status"] == "ok"
    equipments = data["payload"]["equipments"]
    assert len(equipments) == 3
    for eq in equipments:
        assert "status_code" in eq, f"status_code absent pour eq_id={eq.get('eq_id')}"


async def test_diagnostics_status_code_values_in_enum(aiohttp_client):
    """status_code doit être dans l'enum attendu."""
    app = _make_simple_app_with_published_eq()
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    for eq in data["payload"]["equipments"]:
        assert eq["status_code"] in _VALID_STATUS_CODES, (
            f"status_code invalide '{eq['status_code']}' pour eq_id={eq.get('eq_id')}"
        )


async def test_diagnostics_status_code_published(aiohttp_client):
    """Équipement publié → status_code='published'."""
    app = _make_simple_app_with_published_eq()
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    eq_10 = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 10)
    assert eq_10["status"] == "Publié"
    assert eq_10["status_code"] == "published"


async def test_diagnostics_status_code_excluded(aiohttp_client):
    """Équipement exclu → status_code='excluded'."""
    app = _make_simple_app_with_published_eq()
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    eq_11 = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 11)
    assert eq_11["status"] == "Exclu"
    assert eq_11["status_code"] == "excluded"


async def test_diagnostics_status_code_not_published(aiohttp_client):
    """Équipement non supporté → status_code='not_supported' (Story 3.1 : taxonomie fermée)."""
    app = _make_simple_app_with_published_eq()
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    eq_12 = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 12)
    assert eq_12["status"] == "Non supporté"
    assert eq_12["status_code"] == "not_supported"


async def test_diagnostics_status_code_published_with_unmatched(aiohttp_client):
    """Équipement publié avec commandes non couvertes → status_code='published' (Story 3.1)."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd_mapped   = JeedomCmd(id=2001, name="On",     generic_type="LIGHT_ON")
    cmd_unmapped = JeedomCmd(id=2002, name="Couleur", generic_type="LIGHT_COLOR")
    snapshot = TopologySnapshot(
        timestamp="2026-03-20T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={20: JeedomEqLogic(id=20, name="RGB", object_id=1, is_enable=True, cmds=[cmd_mapped, cmd_unmapped])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_only",
        jeedom_eq_id=20,
        ha_unique_id="light_20",
        ha_name="RGB",
        commands={"LIGHT_ON": cmd_mapped},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {20: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {20: mapping_res}
    app["publications"] = {
        20: PublicationDecision(
            should_publish=True,
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    eq_20 = data["payload"]["equipments"][0]
    # Story 3.1 : publication partielle → "Publié" + unmatched_commands
    assert eq_20["status"] == "Publié"
    assert eq_20["status_code"] == "published"


async def test_diagnostics_non_regression_existing_fields(aiohttp_client):
    """Non-régression : tous les champs existants sont toujours présents."""
    app = _make_simple_app_with_published_eq()
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    existing_fields = {
        "eq_id", "object_name", "name", "eq_type_name",
        "status", "confidence", "reason_code",
        "detail", "remediation", "v1_limitation", "v1_compatibility",
        "matched_commands", "unmatched_commands", "detected_generic_types",
        "traceability",
    }
    for eq in data["payload"]["equipments"]:
        for field in existing_fields:
            assert field in eq, f"Champ existant '{field}' absent pour eq_id={eq.get('eq_id')}"
        assert "projection_validity" in eq["traceability"]
        assert set(eq["traceability"]["projection_validity"]) == {
            "is_valid",
            "reason_code",
            "missing_fields",
            "missing_capabilities",
        }
