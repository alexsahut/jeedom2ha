"""Story 3.1 — Tests unitaires Python : taxonomie et endpoint diagnostics.

ACs couverts :
  AC 1 — taxonomie verrouillée côté backend
  AC 2 — 'Partiellement publié' éliminé comme statut principal
  AC 3 — 'Non publié' remplacé par un statut précis
  AC 5 — taxonomy.py expose un contrat importable et complet
"""
import pytest
from unittest.mock import MagicMock

from models.taxonomy import (
    PRIMARY_STATUSES,
    REASON_CODE_TO_PRIMARY_STATUS,
    PRIMARY_STATUS_LABELS,
    get_primary_status,
)
from transport.http_server import create_app
from models.topology import (
    TopologySnapshot,
    JeedomObject,
    JeedomEqLogic,
    JeedomCmd,
    EligibilityResult,
)
from models.mapping import MappingResult, PublicationDecision, LightCapabilities


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_STATUSES = frozenset(
    {"Publié", "Exclu", "Ambigu", "Non supporté", "Incident infrastructure"}
)
_FORBIDDEN_STATUSES = frozenset({"Non publié", "Partiellement publié"})


def _make_app():
    app = create_app(local_secret="test_secret")
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.state = "connected"
    app["mqtt_bridge"] = bridge
    return app


# ---------------------------------------------------------------------------
# AC 5 — Contrat importable et complet
# ---------------------------------------------------------------------------


def test_primary_statuses_has_five_entries():
    """PRIMARY_STATUSES contient exactement 5 entrées (AC 5)."""
    assert len(PRIMARY_STATUSES) == 5


def test_primary_statuses_keys():
    """PRIMARY_STATUSES contient les 5 codes machine attendus (AC 5)."""
    expected_keys = {"published", "excluded", "ambiguous", "not_supported", "infra_incident"}
    assert set(PRIMARY_STATUSES.keys()) == expected_keys


def test_primary_statuses_labels():
    """PRIMARY_STATUSES contient les 5 labels français attendus (AC 5)."""
    expected_labels = {"Publié", "Exclu", "Ambigu", "Non supporté", "Incident infrastructure"}
    assert set(PRIMARY_STATUSES.values()) == expected_labels


def test_primary_status_labels_frozenset():
    """PRIMARY_STATUS_LABELS est un frozenset cohérent avec PRIMARY_STATUSES.values (AC 5)."""
    assert isinstance(PRIMARY_STATUS_LABELS, frozenset)
    assert PRIMARY_STATUS_LABELS == frozenset(PRIMARY_STATUSES.values())


# ---------------------------------------------------------------------------
# Task 5.2 — get_primary_status résout tous les reason_codes du tableau
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reason_code,expected_label", [
    ("sure",                              "Publié"),
    ("probable",                          "Publié"),
    ("excluded_eqlogic",                  "Exclu"),
    ("excluded_plugin",                   "Exclu"),
    ("excluded_object",                   "Exclu"),
    ("disabled_eqlogic",                  "Non supporté"),
    ("disabled",                          "Non supporté"),
    ("no_commands",                       "Non supporté"),
    ("no_supported_generic_type",         "Non supporté"),
    ("no_generic_type_configured",        "Non supporté"),
    ("no_mapping",                        "Non supporté"),
    ("low_confidence",                    "Non supporté"),
    ("probable_skipped",                  "Ambigu"),
    ("ambiguous_skipped",                 "Ambigu"),
    ("discovery_publish_failed",          "Incident infrastructure"),
    ("local_availability_publish_failed", "Incident infrastructure"),
])
def test_get_primary_status_known_codes(reason_code, expected_label):
    """get_primary_status résout correctement chaque reason_code du mapping (Task 5.2)."""
    result = get_primary_status(reason_code)
    assert result == expected_label, (
        f"get_primary_status('{reason_code}') returned '{result}', expected '{expected_label}'"
    )


# ---------------------------------------------------------------------------
# Task 5.3 — 'eligible' ne doit jamais apparaître comme valeur finale
# ---------------------------------------------------------------------------


def test_get_primary_status_eligible_is_not_final():
    """'eligible' est un code intermédiaire — get_primary_status('eligible') tombe en fallback.

    Ce test documente que 'eligible' n'est pas un statut final valide.
    """
    result = get_primary_status("eligible")
    assert result not in _VALID_STATUSES or result == "Non supporté", (
        f"'eligible' ne devrait pas produire un statut principal valide distinct. Got: '{result}'"
    )
    # Vérification explicite : 'eligible' n'est pas dans REASON_CODE_TO_PRIMARY_STATUS
    assert "eligible" not in REASON_CODE_TO_PRIMARY_STATUS


# ---------------------------------------------------------------------------
# Task 5.4 — Fallback sécuritaire pour code inconnu
# ---------------------------------------------------------------------------


def test_get_primary_status_unknown_code_fallback():
    """Code inconnu → 'Non supporté' (fallback sécuritaire — Task 5.4)."""
    result = get_primary_status("code_inexistant")
    assert result == "Non supporté"


def test_get_primary_status_empty_string_fallback():
    """Chaîne vide → 'Non supporté' (fallback sécuritaire)."""
    result = get_primary_status("")
    assert result == "Non supporté"


# ---------------------------------------------------------------------------
# Tasks 5.5–5.11 — Tests d'intégration endpoint /system/diagnostics
# ---------------------------------------------------------------------------


async def test_excluded_eqlogic_status(aiohttp_client):
    """Équipement exclu → status == 'Exclu' (Task 5.5)."""
    app = _make_app()
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={10: JeedomEqLogic(id=10, name="Prise Exclue", object_id=1, is_excluded=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {10: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 10)

    assert eq["status"] == "Exclu"
    assert eq["status"] in _VALID_STATUSES
    assert eq["status"] not in _FORBIDDEN_STATUSES


async def test_disabled_eqlogic_status(aiohttp_client):
    """Équipement désactivé → status == 'Non supporté' (Task 5.6)."""
    app = _make_app()
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={20: JeedomEqLogic(id=20, name="Eq Désactivé", object_id=1, is_enable=False)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {20: EligibilityResult(is_eligible=False, reason_code="disabled_eqlogic")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 20)

    assert eq["status"] == "Non supporté"
    assert eq["status"] in _VALID_STATUSES
    assert eq["status"] not in _FORBIDDEN_STATUSES


async def test_ambiguous_skipped_status(aiohttp_client):
    """ambiguous_skipped → status == 'Ambigu' (Task 5.7)."""
    app = _make_app()
    cli = await aiohttp_client(app)

    cmd1 = JeedomCmd(id=301, name="On", generic_type="LIGHT_ON")
    cmd2 = JeedomCmd(id=302, name="Monter", generic_type="COVER_UP")
    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={30: JeedomEqLogic(id=30, name="Eq Ambigu", object_id=1, is_enable=True, cmds=[cmd1, cmd2])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="ambiguous",
        reason_code="ambiguous",
        jeedom_eq_id=30,
        ha_unique_id="light_30",
        ha_name="Eq Ambigu",
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {30: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {30: mapping_res}
    app["publications"] = {
        30: PublicationDecision(
            should_publish=False,
            reason="ambiguous_skipped",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 30)

    assert eq["status"] == "Ambigu"
    assert eq["status"] in _VALID_STATUSES
    assert eq["status"] not in _FORBIDDEN_STATUSES


async def test_discovery_publish_failed_status(aiohttp_client):
    """discovery_publish_failed → status == 'Incident infrastructure' (Task 5.8)."""
    app = _make_app()
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=401, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={40: JeedomEqLogic(id=40, name="Lumiere Fail", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=40,
        ha_unique_id="light_40",
        ha_name="Lumiere Fail",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {40: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {40: mapping_res}
    app["publications"] = {
        40: PublicationDecision(
            should_publish=False,
            reason="discovery_publish_failed",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 40)

    assert eq["status"] == "Incident infrastructure"
    assert eq["status"] in _VALID_STATUSES
    assert eq["status"] not in _FORBIDDEN_STATUSES


async def test_published_full_status(aiohttp_client):
    """Équipement publié complet → status == 'Publié' + unmatched_commands == [] (Task 5.9)."""
    app = _make_app()
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=501, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={50: JeedomEqLogic(id=50, name="Lumiere Pub", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=50,
        ha_unique_id="light_50",
        ha_name="Lumiere Pub",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {50: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {50: mapping_res}
    app["publications"] = {
        50: PublicationDecision(
            should_publish=True,
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 50)

    assert eq["status"] == "Publié"
    assert eq["unmatched_commands"] == []
    assert eq["status"] in _VALID_STATUSES
    assert eq["status"] not in _FORBIDDEN_STATUSES


async def test_published_partial_status(aiohttp_client):
    """Équipement publié partiel → status == 'Publié' + unmatched_commands non vide.

    'Partiellement publié' est INTERDIT comme valeur de status (Task 5.10, AC 2).
    """
    app = _make_app()
    cli = await aiohttp_client(app)

    cmd_on = JeedomCmd(id=601, name="On", generic_type="LIGHT_ON")
    cmd_dim = JeedomCmd(id=602, name="Dim", generic_type="LIGHT_SLIDER")
    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            60: JeedomEqLogic(
                id=60, name="Lumiere Partielle", object_id=1, is_enable=True, cmds=[cmd_on, cmd_dim]
            )
        },
    )
    # Le mapper ne couvre que LIGHT_ON (pas LIGHT_SLIDER)
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=60,
        ha_unique_id="light_60",
        ha_name="Lumiere Partielle",
        commands={"LIGHT_ON": cmd_on},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {60: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {60: mapping_res}
    app["publications"] = {
        60: PublicationDecision(
            should_publish=True,
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 60)

    # AC 2 : status est "Publié", pas "Partiellement publié"
    assert eq["status"] == "Publié"
    assert eq["status"] != "Partiellement publié"
    # Le détail partiel est accessible via unmatched_commands
    assert len(eq["unmatched_commands"]) > 0
    assert eq["status"] in _VALID_STATUSES
    assert eq["status"] not in _FORBIDDEN_STATUSES


async def test_no_response_contains_forbidden_statuses(aiohttp_client):
    """Aucun équipement ne retourne 'Non publié' ou 'Partiellement publié' (Task 5.11, AC 1).

    Vérifie tous les statuts possibles en un seul appel avec plusieurs équipements.
    """
    app = _make_app()
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=701, name="On", generic_type="LIGHT_ON")
    cmd_dim = JeedomCmd(id=702, name="Dim", generic_type="LIGHT_SLIDER")
    snapshot = TopologySnapshot(
        timestamp="2026-03-25T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            70: JeedomEqLogic(id=70, name="Pub Complet", object_id=1, is_enable=True, cmds=[cmd]),
            71: JeedomEqLogic(id=71, name="Pub Partiel", object_id=1, is_enable=True, cmds=[cmd, cmd_dim]),
            72: JeedomEqLogic(id=72, name="Exclu", object_id=1, is_excluded=True),
            73: JeedomEqLogic(id=73, name="Désactivé", object_id=1, is_enable=False),
            74: JeedomEqLogic(id=74, name="Sans Cmd", object_id=1, is_enable=True),
        },
    )
    mapping_full = MappingResult(
        ha_entity_type="light", confidence="sure", reason_code="light_on_off",
        jeedom_eq_id=70, ha_unique_id="light_70", ha_name="Pub Complet",
        commands={"LIGHT_ON": cmd}, capabilities=LightCapabilities(has_on_off=True),
    )
    mapping_partial = MappingResult(
        ha_entity_type="light", confidence="sure", reason_code="light_on_off",
        jeedom_eq_id=71, ha_unique_id="light_71", ha_name="Pub Partiel",
        commands={"LIGHT_ON": cmd},  # seul LIGHT_ON mappé, pas LIGHT_SLIDER
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        70: EligibilityResult(is_eligible=True, reason_code="eligible"),
        71: EligibilityResult(is_eligible=True, reason_code="eligible"),
        72: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
        73: EligibilityResult(is_eligible=False, reason_code="disabled_eqlogic"),
        74: EligibilityResult(is_eligible=False, reason_code="no_commands"),
    }
    app["mappings"] = {70: mapping_full, 71: mapping_partial}
    app["publications"] = {
        70: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_full, active_or_alive=True
        ),
        71: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_partial, active_or_alive=True
        ),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    for eq in data["payload"]["equipments"]:
        assert eq["status"] not in _FORBIDDEN_STATUSES, (
            f"eq_id={eq['eq_id']} a un statut interdit : '{eq['status']}'"
        )
        assert eq["status"] in _VALID_STATUSES, (
            f"eq_id={eq['eq_id']} a un statut hors taxonomie : '{eq['status']}'"
        )
