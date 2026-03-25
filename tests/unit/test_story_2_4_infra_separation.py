"""Story 2.4 — Distinction stable entre infrastructure et configuration.

Valide que la raison métier d'un équipement non publié reste stable
quel que soit l'état MQTT / infrastructure au moment de la lecture diagnostique.

ACs couverts :
  AC1 — incident infra séparé de la raison métier
  AC2 — aucun code visuel infra pour un problème de configuration
  AC3 — qualification du type de blocage en première lecture
"""
import pytest
from unittest.mock import MagicMock

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot,
    JeedomObject,
    JeedomEqLogic,
    JeedomCmd,
    EligibilityResult,
)
from models.mapping import MappingResult, PublicationDecision, LightCapabilities


_INFRA_REASON_CODES = frozenset(
    {"discovery_publish_failed", "local_availability_publish_failed"}
)
_CONFIG_REASON_CODES = frozenset(
    {
        "excluded_eqlogic",
        "excluded_plugin",
        "excluded_object",
        "disabled_eqlogic",
        "disabled",
        "no_commands",
    }
)
_COVERAGE_REASON_CODES = frozenset(
    {
        "no_supported_generic_type",
        "ambiguous_skipped",
        "no_mapping",
        "probable_skipped",
    }
)


def _app_with_mqtt_state(is_connected: bool):
    """Return a test app with a mock bridge in the requested connectivity state."""
    app = create_app(local_secret="test_secret")
    bridge = MagicMock()
    bridge.is_connected = is_connected
    bridge.state = "connected" if is_connected else "disconnected"
    app["mqtt_bridge"] = bridge
    return app


# ---------------------------------------------------------------------------
# AC1 / AC2 — la raison métier reste stable quelle que soit la connectivité MQTT
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mqtt_connected", [True, False])
async def test_excluded_reason_stable_under_mqtt_state(aiohttp_client, mqtt_connected):
    """Exclusion explicite : reason_code = excluded_eqlogic, indépendamment de l'état MQTT."""
    app = _app_with_mqtt_state(mqtt_connected)
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            100: JeedomEqLogic(id=100, name="Prise Exclue", object_id=1, is_excluded=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        100: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    assert resp.status == 200
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 100)

    # AC1: raison métier stable quel que soit l'état MQTT
    assert eq["reason_code"] == "excluded_eqlogic", (
        f"mqtt_connected={mqtt_connected}: expected 'excluded_eqlogic', got '{eq['reason_code']}'"
    )
    assert eq["status"] == "Exclu"
    # AC2: reason_code décrit un problème de configuration, pas d'infrastructure
    assert eq["reason_code"] in _CONFIG_REASON_CODES
    assert eq["reason_code"] not in _INFRA_REASON_CODES


@pytest.mark.parametrize("mqtt_connected", [True, False])
async def test_ambiguous_reason_stable_under_mqtt_state(aiohttp_client, mqtt_connected):
    """Mapping ambigu : reason_code = ambiguous_skipped, indépendamment de l'état MQTT."""
    app = _app_with_mqtt_state(mqtt_connected)
    cli = await aiohttp_client(app)

    cmd1 = JeedomCmd(id=201, name="On", generic_type="LIGHT_ON")
    cmd2 = JeedomCmd(id=202, name="Monter", generic_type="COVER_UP")

    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            200: JeedomEqLogic(
                id=200, name="Eq Ambigu", object_id=1, is_enable=True, cmds=[cmd1, cmd2]
            ),
        },
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="ambiguous",
        reason_code="ambiguous",
        jeedom_eq_id=200,
        ha_unique_id="light_200",
        ha_name="Eq Ambigu",
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {200: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {200: mapping_res}
    app["publications"] = {
        200: PublicationDecision(
            should_publish=False,
            reason="ambiguous_skipped",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 200)

    # AC1: raison couverture stable quel que soit l'état MQTT
    assert eq["reason_code"] == "ambiguous_skipped", (
        f"mqtt_connected={mqtt_connected}: expected 'ambiguous_skipped', got '{eq['reason_code']}'"
    )
    assert eq["status"] == "Non publié"
    # AC2: reason_code décrit un problème de couverture, pas d'infrastructure
    assert eq["reason_code"] in _COVERAGE_REASON_CODES
    assert eq["reason_code"] not in _INFRA_REASON_CODES


@pytest.mark.parametrize("mqtt_connected", [True, False])
async def test_no_supported_generic_type_stable_under_mqtt_state(aiohttp_client, mqtt_connected):
    """Couverture non supportée : reason_code stable quel que soit l'état MQTT."""
    app = _app_with_mqtt_state(mqtt_connected)
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Cuisine")},
        eq_logics={
            300: JeedomEqLogic(id=300, name="Thermostat", object_id=1, is_enable=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        300: EligibilityResult(is_eligible=False, reason_code="no_supported_generic_type"),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 300)

    assert eq["reason_code"] == "no_supported_generic_type", (
        f"mqtt_connected={mqtt_connected}: expected 'no_supported_generic_type', got '{eq['reason_code']}'"
    )
    assert eq["reason_code"] in _COVERAGE_REASON_CODES
    assert eq["reason_code"] not in _INFRA_REASON_CODES


# ---------------------------------------------------------------------------
# AC1 — Scénario mixte : MQTT down ET équipement avec raison config/couverture
# Les deux signaux restent distincts et non fusionnés
# ---------------------------------------------------------------------------


async def test_mixed_scenario_mqtt_down_config_reason_visible(aiohttp_client):
    """Scénario mixte : MQTT déconnecté + équipement exclu.

    La raison métier (exclusion) reste visible et distincte.
    Le diagnostic ne substitue pas un code infra à la raison config.
    Le payload diagnostic ne contient pas de champs infra (contrat /system/status séparé).
    """
    app = _app_with_mqtt_state(is_connected=False)
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            400: JeedomEqLogic(id=400, name="Lumiere Exclue", object_id=1, is_excluded=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        400: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    assert data["status"] == "ok"

    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 400)

    # AC1: la raison métier est visible même quand l'infra est dégradée
    assert eq["reason_code"] == "excluded_eqlogic"
    assert eq["status"] == "Exclu"

    # AC1: le signal infrastructure (état MQTT) n'est PAS dans la réponse /system/diagnostics
    # (il est sur /system/status — contrats séparés, Story 2.1)
    assert "broker" not in data
    assert "mqtt" not in data
    assert "daemon" not in data

    # AC3: le reason_code permet une qualification directe
    assert eq["reason_code"] not in _INFRA_REASON_CODES


async def test_mixed_scenario_mqtt_down_ambiguous_reason_visible(aiohttp_client):
    """Scénario mixte : MQTT déconnecté + équipement ambigu.

    La raison de couverture reste visible et non polluée.
    """
    app = _app_with_mqtt_state(is_connected=False)
    cli = await aiohttp_client(app)

    cmd1 = JeedomCmd(id=601, name="On", generic_type="LIGHT_ON")
    cmd2 = JeedomCmd(id=602, name="Monter", generic_type="COVER_UP")

    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Cuisine")},
        eq_logics={
            600: JeedomEqLogic(
                id=600, name="Eq Multi", object_id=1, is_enable=True, cmds=[cmd1, cmd2]
            ),
        },
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="ambiguous",
        reason_code="ambiguous",
        jeedom_eq_id=600,
        ha_unique_id="light_600",
        ha_name="Eq Multi",
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {600: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {600: mapping_res}
    app["publications"] = {
        600: PublicationDecision(
            should_publish=False,
            reason="ambiguous_skipped",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 600)

    assert eq["reason_code"] == "ambiguous_skipped"
    assert eq["reason_code"] not in _INFRA_REASON_CODES


# ---------------------------------------------------------------------------
# AC3 — Les familles de reason_codes permettent la qualification rapide
# Infra (discovery_publish_failed) vs config (exclusion, no_commands) distinctes
# ---------------------------------------------------------------------------


async def test_reason_code_families_are_qualified_distinctly(aiohttp_client):
    """AC3 : un mix d'équipements permet de qualifier infrastructure vs configuration.

    - discovery_publish_failed → famille infra (MQTT a empêché la publication)
    - excluded_eqlogic → famille configuration (décision utilisateur)
    - no_commands → famille configuration (état de l'équipement dans Jeedom)

    Les trois familles sont lisibles distinctement dans la même réponse.
    """
    app = _app_with_mqtt_state(is_connected=True)
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=701, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            700: JeedomEqLogic(id=700, name="Lumiere Fail", object_id=1, is_enable=True, cmds=[cmd]),
            701: JeedomEqLogic(id=701, name="Prise Exclue", object_id=1, is_excluded=True),
            702: JeedomEqLogic(id=702, name="Eq Sans Cmd", object_id=1, is_enable=True),
        },
    )
    mapping_fail = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=700,
        ha_unique_id="light_700",
        ha_name="Lumiere Fail",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        700: EligibilityResult(is_eligible=True, reason_code="eligible"),
        701: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
        702: EligibilityResult(is_eligible=False, reason_code="no_commands"),
    }
    app["mappings"] = {700: mapping_fail}
    app["publications"] = {
        700: PublicationDecision(
            should_publish=False,
            reason="discovery_publish_failed",
            mapping_result=mapping_fail,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    by_id = {e["eq_id"]: e for e in data["payload"]["equipments"]}

    # eq 700 : publication échouée → famille infra
    assert by_id[700]["reason_code"] in _INFRA_REASON_CODES

    # eq 701 : exclusion explicite → famille configuration
    assert by_id[701]["reason_code"] in _CONFIG_REASON_CODES

    # eq 702 : équipement sans commande → famille configuration
    assert by_id[702]["reason_code"] in _CONFIG_REASON_CODES

    # Vérification croisée : aucun code config ne se retrouve dans la famille infra
    assert by_id[701]["reason_code"] not in _INFRA_REASON_CODES
    assert by_id[702]["reason_code"] not in _INFRA_REASON_CODES

    # Vérification croisée : le code infra ne se retrouve pas dans une famille config/couverture
    assert by_id[700]["reason_code"] not in _CONFIG_REASON_CODES
    assert by_id[700]["reason_code"] not in _COVERAGE_REASON_CODES


# ---------------------------------------------------------------------------
# Garde-fou : le contrat /system/diagnostics ne contient pas d'état de santé infra
# Le contrat santé est sur /system/status (Story 2.1) — contrats séparés
# ---------------------------------------------------------------------------


async def test_diagnostics_contract_does_not_contain_infra_health(aiohttp_client):
    """AC1 : le contrat /system/diagnostics n'expose pas de champs d'infra (daemon, broker, mqtt).

    Les champs de santé infrastructure appartiennent au contrat /system/status (Story 2.1).
    Les deux contrats sont distincts et non mixés.
    """
    app = _app_with_mqtt_state(is_connected=False)  # MQTT down volontairement
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            800: JeedomEqLogic(id=800, name="Lumiere", object_id=1, is_enable=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        800: EligibilityResult(is_eligible=False, reason_code="no_commands"),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    # Le payload ne doit PAS contenir les champs santé infrastructure
    assert "daemon" not in data
    assert "broker" not in data
    assert "mqtt" not in data
    assert "uptime" not in data

    # Mais doit contenir uniquement les données d'équipements
    assert data["status"] == "ok"
    assert "equipments" in data["payload"]
