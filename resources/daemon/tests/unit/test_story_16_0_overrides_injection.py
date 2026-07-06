"""Story 16.0 - Contrat d'override : invariants D10/D11 posés avant toute implémentation (16.1+).

Ce module ne teste pas encore un module `overrides.py` (introduit en Story 16.1) : il fige,
sous forme de tests exécutables, les invariants architecturaux non négociables du contrat
d'override (gates epic-level pe-epic-16) tels que documentés dans
`architecture-delta-pe-epic-16-mapping-configurable.md` (D10, D11) :

- un override HA ne modifie jamais le `generic_type` Jeedom natif (D10) ;
- une décision de mapping reste soumise à `validate_projection()` même en présence d'un
  override, qui ne bypasse jamais un échec de validation structurelle (D11).

Story 16.1 doit étendre ce fichier (pas en créer un nouveau) une fois `overrides.py` disponible.
"""

from __future__ import annotations

from mapping.switch import SwitchMapper
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from validation.ha_component_registry import validate_projection


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-07-06T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={eq.id: eq},
    )


def _switch_eq(*, eq_id: int, cmd_id: int, generic_type: str = "SWITCH_STATE") -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=f"Switch {eq_id}",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(
                id=cmd_id,
                name=f"Cmd {cmd_id}",
                generic_type=generic_type,
                type="info",
                sub_type="binary",
                unit=None,
                current_value=1,
            )
        ],
    )


def test_generic_type_natif_jamais_mute_par_le_pipeline_de_mapping():
    """D10 : le pipeline de mapping (`map()`) ne mute jamais le `generic_type` Jeedom natif.

    Baseline de non-régression : ce test doit rester vert une fois `overrides.py` (Story 16.1)
    introduit, puisque D8/16a garantit que le patch d'override s'applique uniquement sur une
    copie du `MappingResult`, jamais sur l'objet `JeedomCmd`/`JeedomEqLogic` source.
    """
    eq = _switch_eq(eq_id=16001, cmd_id=160011, generic_type="SWITCH_STATE")
    original_generic_type = eq.cmds[0].generic_type

    SwitchMapper().map(eq, _snapshot(eq))

    assert eq.cmds[0].generic_type == original_generic_type == "SWITCH_STATE"


def test_validate_projection_reste_autoritaire_sur_un_ha_entity_type_incompatible():
    """D11 : une projection structurellement invalide n'est jamais considérée valide.

    Ce test fige le comportement de `validate_projection()` face à un `ha_entity_type`
    inconnu du registre HA — invariant que Story 16.1+ doit respecter : un override
    référençant un `ha_entity_type` incompatible avec les capabilities détectées ne doit
    jamais transformer un `is_valid=False` en `is_valid=True` par contournement.
    """
    validity = validate_projection("ha_entity_type_inexistant_16_0", capabilities=None)

    assert validity.is_valid is False
    assert validity.reason_code == "ha_component_unknown"
