"""Harnais de parité — Story 19.0, Task 4.

Compare, sur un même corpus, la décision de publication produite par le pipeline
classique (`decide_publication()` appelé directement, comme dans
`_do_handle_action_sync`) et celle produite par `evaluate_equipment()` avec
overrides persistés seuls (AC3 : aucun override "proposé"/preview).

Ce module n'est pas un test en lui-même : c'est un outil réutilisable par les
tests pytest (voir `test_story_19_0_evaluate_equipment_contract.py`), afin de
documenter tout écart constaté entre les deux chemins sur le corpus doré.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from mapping.overrides import apply_type_override
from mapping.registry import MapperRegistry
from models.decide_publication import decide_publication
from models.evaluate_equipment import evaluate_equipment
from models.topology import TopologySnapshot, assess_all
from validation.ha_component_registry import validate_projection


@dataclass
class ParityDiscrepancy:
    eq_id: int
    classic_should_publish: Optional[bool]
    classic_reason: Optional[str]
    evaluate_should_publish: Optional[bool]
    evaluate_reason: Optional[str]
    detail: str


def _classic_decision_for_eq(eq_id, eq, snapshot, *, confidence_policy, mapper_registry,
                              overrides_cache, equipment_overrides_cache):
    """Reproduit le chemin classique (`_do_handle_action_sync`, hors MQTT/publisher)."""
    mapping = mapper_registry.map(eq, snapshot)
    if mapping is None:
        return None

    mapping = apply_type_override(mapping, "", overrides=overrides_cache)

    projection_validity = validate_projection(mapping.ha_entity_type, mapping.capabilities)
    mapping.projection_validity = projection_validity
    mapping.pipeline_step_reached = 3

    publication_override = None
    from mapping.overrides import mapping_cmd_ids, resolve_publication_override
    for cmd_id in mapping_cmd_ids(mapping) or [-1]:
        candidate = resolve_publication_override(
            mapping.jeedom_eq_id, cmd_id, overrides_cache, equipment_overrides_cache
        )
        if candidate is not None:
            publication_override = candidate
            break

    decision = decide_publication(
        mapping,
        confidence_policy=confidence_policy,
        publication_override=publication_override,
    )
    decision.mapping_result = mapping
    mapping.publication_decision_ref = decision
    mapping.pipeline_step_reached = 4
    return decision


def compute_parity_report(
    payload: dict,
    *,
    confidence_policy: Optional[str] = None,
    overrides: Optional[Dict[str, dict]] = None,
    equipment_overrides: Optional[Dict[str, dict]] = None,
) -> List[ParityDiscrepancy]:
    """Exécute le pipeline classique et `evaluate_equipment()` sur le même corpus.

    Un seul `MapperRegistry()` est partagé entre les deux chemins pour ne pas
    introduire d'écart artificiel dû à une double instanciation mappant le même
    eqLogic deux fois (les mappers sont sans état mais on garde l'appel unique
    par équipement, comme le fait le pipeline réel).

    Retourne la liste des écarts constatés (vide = parité totale). Chaque écart
    documente l'eq_id, la décision de chaque chemin et un détail explicite.
    """
    sync_config = payload.get("sync_config", {})
    effective_policy = confidence_policy or sync_config.get("confidence_policy", "sure_probable")

    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    eligibility = assess_all(snapshot)

    overrides_cache = dict(overrides or {})
    equipment_overrides_cache = dict(equipment_overrides or {})

    discrepancies: List[ParityDiscrepancy] = []

    for eq_id, result in eligibility.items():
        if not result.is_eligible:
            continue

        eq = snapshot.eq_logics.get(eq_id)
        if not eq:
            continue

        classic_registry = MapperRegistry()
        classic_decision = _classic_decision_for_eq(
            eq_id, eq, snapshot,
            confidence_policy=effective_policy,
            mapper_registry=classic_registry,
            overrides_cache=overrides_cache,
            equipment_overrides_cache=equipment_overrides_cache,
        )

        evaluate_registry = MapperRegistry()
        evaluation = evaluate_equipment(
            eq, snapshot, result,
            mapper_registry=evaluate_registry,
            confidence_policy=effective_policy,
            persisted_overrides=overrides_cache,
            persisted_equipment_overrides=equipment_overrides_cache,
        )
        evaluate_decision = evaluation.equipment_decision

        if classic_decision is None:
            if evaluate_decision.reason != "no_mapping":
                discrepancies.append(ParityDiscrepancy(
                    eq_id=eq_id,
                    classic_should_publish=None,
                    classic_reason=None,
                    evaluate_should_publish=evaluate_decision.should_publish,
                    evaluate_reason=evaluate_decision.reason,
                    detail="classique: no_mapping (mapper_registry.map()->None) vs "
                           f"evaluate_equipment: reason={evaluate_decision.reason!r}",
                ))
            continue

        if (classic_decision.should_publish != evaluate_decision.should_publish
                or classic_decision.reason != evaluate_decision.reason):
            discrepancies.append(ParityDiscrepancy(
                eq_id=eq_id,
                classic_should_publish=classic_decision.should_publish,
                classic_reason=classic_decision.reason,
                evaluate_should_publish=evaluate_decision.should_publish,
                evaluate_reason=evaluate_decision.reason,
                detail=(
                    f"classique: should_publish={classic_decision.should_publish!r} "
                    f"reason={classic_decision.reason!r} vs evaluate_equipment: "
                    f"should_publish={evaluate_decision.should_publish!r} "
                    f"reason={evaluate_decision.reason!r}"
                ),
            ))

    return discrepancies
