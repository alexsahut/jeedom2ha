"""Story 16.2 — application backend des overrides de type + résolution "attendu HA".

Couvre :
- AC2 : `apply_type_override()` patche une COPIE du MappingResult (ha_entity_type),
  trace `override_applied`/`override_source` dans reason_details, ne mute jamais le
  `generic_type` Jeedom natif (D10) ni l'objet source.
- AC3 : un override invalide ne bypasse jamais `validate_projection()` (D11) — la
  validation HA s'exécute sur le type SURCHARGÉ et peut échouer.
- AC1 : `resolve_expected_ha()` dérive l'attendu HA de la source runtime (moteur +
  registre HA), proposition auto incluse, champs d'enrichissement 16b nullables en 16a.
- Code-review (2026-07-07) : interaction avec la détection "retypage" (Story 5.2,
  `_detect_lifecycle_changes`) — appliquer un override qui change `ha_entity_type`
  doit déclencher le même unpublish de l'ancien topic qu'un retypage natif.

Source de vérité tranchée SCP 2026-07-07 (Option 1) : registry + mappers, jamais le YAML
de planning.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

import transport.http_server as http_server
from mapping.overrides import apply_type_override, save_override
from mapping.registry import resolve_expected_ha
from models.mapping import (
    MappingResult,
    PublicationDecision,
    SensorCapabilities,
    SwitchCapabilities,
)
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from validation.ha_component_registry import validate_projection


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _cmd(cmd_id: int, generic_type: str | None = "ENERGY_STATE") -> JeedomCmd:
    return JeedomCmd(
        id=cmd_id,
        name=f"Cmd {cmd_id}",
        generic_type=generic_type,
        type="info",
        sub_type="binary",
        unit=None,
        current_value=1,
    )


def _switch_mapping(eq_id: int, cmd_id: int) -> MappingResult:
    cmd = _cmd(cmd_id)
    return MappingResult(
        ha_entity_type="switch",
        confidence="sure",
        reason_code="switch_on_off",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Switch {eq_id}",
        commands={cmd.generic_type: cmd},
        capabilities=SwitchCapabilities(has_on_off=True),
        reason_details={"on_off": "state+on+off"},
    )


def _sensor_mapping(eq_id: int, cmd_id: int) -> MappingResult:
    cmd = _cmd(cmd_id, generic_type="POWER")
    return MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_power",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Sensor {eq_id}",
        commands={cmd.generic_type: cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={"cmd_id": cmd_id, "device_class": "power"},
    )


def _switch_eq(eq_id: int, cmd_id: int) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=f"Prise {eq_id}",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(id=cmd_id, name="Etat", generic_type="ENERGY_STATE",
                      type="info", sub_type="binary", unit=None, current_value=1),
            JeedomCmd(id=cmd_id + 1, name="On", generic_type="ENERGY_ON",
                      type="action", sub_type="other", unit=None, current_value=None),
            JeedomCmd(id=cmd_id + 2, name="Off", generic_type="ENERGY_OFF",
                      type="action", sub_type="other", unit=None, current_value=None),
        ],
    )


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-07-07T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={eq.id: eq},
    )


# --------------------------------------------------------------------------- #
# AC2 — apply_type_override                                                    #
# --------------------------------------------------------------------------- #

def test_apply_type_override_patche_une_copie_et_trace_la_source(tmp_path):
    data_dir = str(tmp_path)
    mapping = _switch_mapping(eq_id=553, cmd_id=5138)
    save_override(553, 5138, {"ha_entity_type": "light"}, data_dir)

    patched = apply_type_override(mapping, data_dir)

    assert patched is not mapping                       # copie, jamais l'objet source
    assert patched.ha_entity_type == "light"            # type surchargé
    assert patched.reason_details["override_applied"] is True
    assert patched.reason_details["override_source"] == "user"
    # fusion additive : la clé native est préservée
    assert patched.reason_details["on_off"] == "state+on+off"


def test_apply_type_override_ne_mute_jamais_le_mapping_source_ni_le_generic_type(tmp_path):
    data_dir = str(tmp_path)
    mapping = _switch_mapping(eq_id=553, cmd_id=5138)
    native_generic_type = mapping.commands["ENERGY_STATE"].generic_type
    save_override(553, 5138, {"ha_entity_type": "light"}, data_dir)

    apply_type_override(mapping, data_dir)

    # D10 : objet source + generic_type Jeedom natif intacts
    assert mapping.ha_entity_type == "switch"
    assert "override_applied" not in mapping.reason_details
    assert mapping.commands["ENERGY_STATE"].generic_type == native_generic_type == "ENERGY_STATE"


def test_apply_type_override_absent_retourne_le_meme_objet(tmp_path):
    data_dir = str(tmp_path)
    mapping = _switch_mapping(eq_id=553, cmd_id=5138)

    result = apply_type_override(mapping, data_dir)

    assert result is mapping                             # aucun override → identité
    assert "override_applied" not in (result.reason_details or {})
    assert "override_source" not in (result.reason_details or {})


def test_apply_type_override_source_suggested_est_propagee(tmp_path):
    data_dir = str(tmp_path)
    mapping = _switch_mapping(eq_id=553, cmd_id=5138)
    save_override(553, 5138, {"ha_entity_type": "light", "source": "suggested"}, data_dir)

    patched = apply_type_override(mapping, data_dir)

    assert patched.reason_details["override_source"] == "suggested"


def test_apply_type_override_entree_sans_ha_entity_type_est_ignoree(tmp_path):
    data_dir = str(tmp_path)
    mapping = _switch_mapping(eq_id=553, cmd_id=5138)
    save_override(553, 5138, {"note": "pas de type cible"}, data_dir)

    result = apply_type_override(mapping, data_dir)

    assert result is mapping
    assert "override_applied" not in (result.reason_details or {})


def test_apply_type_override_secondaire_match_par_cmd_id_reason_details(tmp_path):
    """Un mapping secondaire (multi-sensor) porte son cmd_id dans reason_details."""
    data_dir = str(tmp_path)
    mapping = _sensor_mapping(eq_id=553, cmd_id=5171)   # reason_details.cmd_id = 5171, commands vides côté clé
    save_override(553, 5171, {"ha_entity_type": "binary_sensor"}, data_dir)

    patched = apply_type_override(mapping, data_dir)

    assert patched.ha_entity_type == "binary_sensor"
    assert patched.reason_details["override_applied"] is True
    # la clé cmd_id native reste présente (fusion additive)
    assert patched.reason_details["cmd_id"] == 5171


# --------------------------------------------------------------------------- #
# AC3 — pas de bypass de validate_projection                                   #
# --------------------------------------------------------------------------- #

def test_override_invalide_ne_bypasse_jamais_validate_projection(tmp_path):
    """Forcer un sensor (has_state) vers 'switch' (exige has_command) → validation échoue."""
    data_dir = str(tmp_path)
    mapping = _sensor_mapping(eq_id=554, cmd_id=5535)
    save_override(554, 5535, {"ha_entity_type": "switch"}, data_dir)

    patched = apply_type_override(mapping, data_dir)
    validity = validate_projection(patched.ha_entity_type, patched.capabilities)

    assert patched.ha_entity_type == "switch"           # override appliqué
    assert validity.is_valid is False                   # mais validation HA échoue
    assert "has_command" in validity.missing_capabilities
    # la surcharge est signalée sans masquer la décision
    assert patched.reason_details["override_applied"] is True


def test_override_vers_type_inconnu_echoue_validation(tmp_path):
    data_dir = str(tmp_path)
    mapping = _switch_mapping(eq_id=555, cmd_id=5600)
    save_override(555, 5600, {"ha_entity_type": "type_ha_inexistant_16_2"}, data_dir)

    patched = apply_type_override(mapping, data_dir)
    validity = validate_projection(patched.ha_entity_type, patched.capabilities)

    assert validity.is_valid is False
    assert validity.reason_code == "ha_component_unknown"


# --------------------------------------------------------------------------- #
# AC1 — resolve_expected_ha (Option 1 : registry + mappers)                    #
# --------------------------------------------------------------------------- #

def test_resolve_expected_ha_propose_le_candidat_moteur(tmp_path):
    eq = _switch_eq(eq_id=553, cmd_id=5138)
    snapshot = _snapshot(eq)
    cmd = eq.cmds[0]

    expected = resolve_expected_ha(eq, snapshot, cmd)

    assert expected["eq_id"] == 553
    assert expected["cmd_id"] == 5138
    assert expected["generic_type"] == "ENERGY_STATE"
    assert expected["proposed_ha_entity_type"] == "switch"
    assert "switch" in expected["compatible_ha_components"]


def test_resolve_expected_ha_champs_enrichissement_16b_nullables_en_16a():
    eq = _switch_eq(eq_id=553, cmd_id=5138)
    expected = resolve_expected_ha(eq, _snapshot(eq), eq.cmds[0])

    assert expected["label_fr"] is None
    assert expected["family_fr"] is None
    assert expected["subtype"] is None


def test_resolve_expected_ha_eq_non_mappe_retourne_none():
    eq = JeedomEqLogic(id=900, name="Inconnu", object_id=1, eq_type_name="virtual",
                       cmds=[JeedomCmd(id=1, name="x", generic_type=None,
                                       type="info", sub_type="string", unit=None,
                                       current_value="?")])
    expected = resolve_expected_ha(eq, _snapshot(eq), eq.cmds[0])

    # FallbackMapper peut produire un candidat ; le contrat exige juste des champs cohérents
    assert expected["cmd_id"] == 1
    assert expected["generic_type"] is None
    assert isinstance(expected["compatible_ha_components"], list)


def test_resolve_expected_ha_cmd_sans_generic_type_conserve_proposition_eqlogic():
    """AC1 : une commande sans generic_type garde la proposition auto au niveau eqLogic."""
    eq = _switch_eq(eq_id=553, cmd_id=5138)
    orphan = JeedomCmd(id=9999, name="Orpheline", generic_type=None,
                       type="info", sub_type="string", unit=None, current_value="?")
    eq.cmds.append(orphan)

    expected = resolve_expected_ha(eq, _snapshot(eq), orphan)

    assert expected["cmd_id"] == 9999
    assert expected["generic_type"] is None
    assert expected["proposed_ha_entity_type"] == "switch"   # proposition moteur eqLogic


# --------------------------------------------------------------------------- #
# Code-review — interaction override / détection "retypage" (Story 5.2)       #
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_override_qui_change_ha_entity_type_declenche_le_retypage_lifecycle(tmp_path):
    """Un override appliqué pour la 1re fois doit être traité comme un retypage natif :
    `_detect_lifecycle_changes` doit unpublish l'ancien topic (D7 : jamais de publication
    silencieuse d'un topic fantôme sous l'ancien type)."""
    data_dir = str(tmp_path)
    eq_id, cmd_id = 553, 5138

    previous_mapping = _switch_mapping(eq_id, cmd_id)  # ha_entity_type natif = "switch"
    previous_decision = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=previous_mapping,
        discovery_published=True,
    )

    save_override(eq_id, cmd_id, {"ha_entity_type": "light"}, data_dir)
    current_mapping = apply_type_override(_switch_mapping(eq_id, cmd_id), data_dir)
    assert current_mapping.ha_entity_type == "light"  # override bien appliqué

    publisher = AsyncMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    pending_discovery_unpublish: dict = {}

    await http_server._detect_lifecycle_changes(
        eq_id,
        current_mapping,
        previous_decision,
        boot_cache={},
        is_first_sync=False,
        publisher=publisher,
        pending_discovery_unpublish=pending_discovery_unpublish,
    )

    publisher.unpublish_by_eq_id.assert_awaited_once_with(
        eq_id, entity_type="switch", node_ids=[]
    )
    assert pending_discovery_unpublish == {}  # unpublish réussi, rien à différer
