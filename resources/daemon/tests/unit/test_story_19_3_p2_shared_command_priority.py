"""Story 19.3 (P2, relecture ClaudeBox PR #176 tour 2) — priorité PRIMAIRE d'abord sur une
commande partagée entre le mapping primaire et un secondaire.

Avant ce correctif, trois logiques différentes résolvaient « quel mapping couvre cette
commande ? » : le contrat (`evaluate_equipment()`, `covered.setdefault` primaire PUIS
secondaires), l'arbre (sa propre paire `is_covered`/`is_secondary`, déjà primaire-d'abord
par coïncidence), et l'aperçu (`_target_mapping_for_cmd`, SECONDAIRE d'abord — l'inverse du
contrat). Sur le corpus doré aucune commande n'est jamais partagée entre un primaire et un
secondaire, donc la divergence de l'aperçu restait invisible en pratique.

Ce test force la collision : la commande Etat du primaire (133003, switch) est injectée
dans les commandes du capteur secondaire (power, sensor) d'une prise avec conso
(fixture identique à la Story 16.8). Il vérifie que l'arbre ET l'aperçu s'accordent tous
les deux sur le PRIMAIRE — jamais le secondaire — via la fonction unique
`_resolve_command_mapping()` désormais partagée par les deux endpoints.
"""

import pytest

from mapping.overrides import save_override
from mapping.registry import MapperRegistry
from models.evaluate_equipment import evaluate_equipment
from models.topology import assess_eligibility
from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd,
)

SECRET = "test_secret"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(
        id=cmd_id, name=name, type=cmd_type, sub_type=sub_type,
        generic_type=generic_type, unit=unit, current_value=value,
    )


def _metering_plug(eq_id=13300):
    """Prise avec conso : primaire switch + capteur secondaire power (cmd 133004).

    Fixture identique à la Story 16.8 (`test_story_16_8_secondary_sensor_diagnostic.py`).
    """
    eq = JeedomEqLogic(
        id=eq_id, name="Prise bureau", object_id=1, eq_type_name="prise",
        cmds=[
            _cmd(133001, "On", "action", "other", "ENERGY_ON"),
            _cmd(133002, "Off", "action", "other", "ENERGY_OFF"),
            _cmd(133003, "Etat", "info", "binary", "ENERGY_STATE", value="1"),
            _cmd(133004, "Conso W", "info", "numeric", None, "W", 42),
        ],
    )
    snapshot = TopologySnapshot(
        timestamp="2026-07-20T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Bureau")},
        eq_logics={eq_id: eq},
    )
    return snapshot, eq


def _headers():
    return {"X-Local-Secret": SECRET}


def _row(payload, cmd_id):
    return next(c for c in payload["commands"] if c["jeedom_cmd_id"] == cmd_id)


def _make_shared_command_evaluator(real_evaluate_equipment):
    """Enveloppe `evaluate_equipment` pour injecter la collision APRÈS la vraie décision :
    la commande Etat (133003, primaire ENERGY_STATE) est ajoutée aux commandes du premier
    secondaire, sans toucher au primaire ni rejouer aucune logique de mapping."""

    def _patched(*args, **kwargs):
        evaluation = real_evaluate_equipment(*args, **kwargs)
        primary = evaluation.mapping
        if primary is not None and primary.additional_mappings:
            shared_cmd = primary.commands.get("ENERGY_STATE")
            secondary = primary.additional_mappings[0]
            if shared_cmd is not None:
                secondary.commands = dict(secondary.commands)
                secondary.commands["_shared_test_cmd"] = shared_cmd
        return evaluation

    return _patched


async def test_tree_resolves_shared_command_to_primary(cli, app, tmp_path, monkeypatch):
    """GET /system/mapping_overrides/{eq_id} : la commande partagée (133003) reste
    diagnostiquée "switch" (primaire), jamais "sensor" (secondaire)."""
    import transport.http_server as http_server_module

    snapshot, _ = _metering_plug()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    monkeypatch.setattr(
        http_server_module, "evaluate_equipment",
        _make_shared_command_evaluator(http_server_module.evaluate_equipment),
    )

    resp = await cli.get("/system/mapping_overrides/13300", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    shared = _row(payload, 133003)
    assert shared["covered"] is True
    assert shared["attendu_ha"] == "switch"
    assert shared["effective_ha"] == "switch"
    assert shared["diagnostic"]["ha_entity_type"] == "switch"
    assert payload["equipment_decision"]["should_publish"] is True
    assert len(payload["entities"]) == 2
    assert all("reason_details" in entity for entity in payload["entities"])
    # La commande partagée ne peut devenir la clé d'action d'aucune entité.
    assert all(entity["override_command_id"] != 133003 for entity in payload["entities"])


async def test_preview_resolves_shared_command_to_primary(cli, app, monkeypatch):
    """POST /system/overrides/preview : cibler la commande partagée (133003) évalue le
    PRIMAIRE (switch), pas le secondaire (sensor). Échoue sur 9f4be56 : `_target_mapping_
    for_cmd` y résolvait le secondaire en premier (recherche secondaire-first)."""
    import transport.http_server as http_server_module

    snapshot, _ = _metering_plug()
    app["topology"] = snapshot

    monkeypatch.setattr(
        http_server_module, "evaluate_equipment",
        _make_shared_command_evaluator(http_server_module.evaluate_equipment),
    )

    resp = await cli.post(
        "/system/overrides/preview", headers=_headers(),
        json={"payload": {
            "jeedom_eq_id": 13300,
            "jeedom_cmd_id": 133003,
            "ha_entity_type": "switch",
        }},
    )
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    assert payload["auto"]["ha_entity_type"] == "switch"
    assert payload["overridden"]["ha_entity_type"] == "switch"


async def test_tree_secondary_pending_uses_its_last_applied_decision(cli, app, tmp_path):
    """AC7 : exclure seulement le secondaire le rend pending, pas le principal."""
    snapshot, eq = _metering_plug()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    previous = evaluate_equipment(
        eq, snapshot, assess_eligibility(eq), mapper_registry=MapperRegistry(),
    )
    assert previous.mapping is not None
    app["publications"] = {eq.id: previous.equipment_decision}

    save_override(eq.id, 133004, {
        "ha_entity_type": "sensor", "publication_override": "exclude",
    }, str(tmp_path))
    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    payload = (await resp.json())["payload"]

    primary, secondary = payload["entities"]
    assert primary["ha_entity_type"] == "switch"
    assert primary["override_pending"] is False
    assert secondary["ha_entity_type"] == "sensor"
    assert secondary["override_pending"] is True
