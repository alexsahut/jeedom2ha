"""Harnais de parité — Story 19.0, Task 4 (étendu revue Alexandre PR #167).

Compare sur un même corpus, à granularité multiple (primaire, secondaires, commande),
la décision de publication produite par le pipeline classique
(`decide_publication()` appelé directement, comme dans `_do_handle_action_sync` et
`_publish_additional_sensors`) et celle produite par `evaluate_equipment()`.

Ce module n'est pas un test en lui-même : c'est un outil réutilisable par les
tests pytest (voir `test_story_19_0_parity_golden_corpus.py`), afin de documenter
tout écart constaté entre les deux chemins sur le corpus doré.

Comparaisons couvertes (revue Alexandre, extension du harnais) :
    a. décisions PRIMAIRES : `should_publish` + `reason` identiques ;
    b. décisions SECONDAIRES (capteurs additionnels multi-sensor) : `should_publish`
       + `reason` par secondaire identiques, dans le même ordre ;
    c. niveau COMMANDE : chaque `cmd_id` d'une entité couverte porte la décision de
       publication de cette entité (parité au niveau commande) ;
    d. OVERRIDES : type_override, exclusion équipement, exclusion commande, force_publish
       (jeu représentatif appliqué au golden corpus dans les tests) ;
    e. POLITIQUE : `sure_probable` (défaut) ET `sure_only` (bascule config, Story 4.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from mapping.overrides import (
    apply_type_override,
    mapping_cmd_ids,
    resolve_publication_override,
)
from mapping.registry import MapperRegistry
from models.decide_publication import decide_publication
from models.evaluate_equipment import evaluate_equipment
from models.mapping import MappingResult, PublicationDecision
from models.topology import TopologySnapshot, assess_all
from validation.ha_component_registry import validate_projection


@dataclass
class ParityDiscrepancy:
    eq_id: int
    scope: str  # "primary" | "secondary[i]" | "cmd[<cmd_id>]"
    classic_should_publish: Optional[bool]
    classic_reason: Optional[str]
    evaluate_should_publish: Optional[bool]
    evaluate_reason: Optional[str]
    detail: str


def _classic_decision_for_mapping(
    mapping: MappingResult,
    *,
    confidence_policy: str,
    overrides_cache: Dict[str, dict],
    equipment_overrides_cache: Dict[str, dict],
) -> PublicationDecision:
    """Rejoue étape 3 (validate_projection) + étape 4 (decide_publication) sur UN mapping
    (primaire ou secondaire), à l'identique de `http_server.py:1429-1442` et
    `_publish_additional_sensors:255-269`. Mute le mapping en place, exactement comme le
    chemin classique."""
    projection_validity = validate_projection(mapping.ha_entity_type, mapping.capabilities)
    mapping.projection_validity = projection_validity
    mapping.pipeline_step_reached = 3

    publication_override = None
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


def _classic_full_pipeline_for_eq(
    eq, snapshot, *, confidence_policy, mapper_registry,
    overrides_cache, equipment_overrides_cache,
):
    """Reproduit le chemin classique complet (`_do_handle_action_sync` + `_publish_additional_sensors`,
    hors MQTT/publisher) : mapping primaire + décision primaire + N décisions secondaires."""
    mapping = mapper_registry.map(eq, snapshot)
    if mapping is None:
        return None, None, []

    mapping = apply_type_override(mapping, "", overrides=overrides_cache)
    primary_decision = _classic_decision_for_mapping(
        mapping,
        confidence_policy=confidence_policy,
        overrides_cache=overrides_cache,
        equipment_overrides_cache=equipment_overrides_cache,
    )

    secondary_decisions: List[PublicationDecision] = []
    for index, secondary in enumerate(mapping.additional_mappings or []):
        secondary = apply_type_override(secondary, "", overrides=overrides_cache)
        mapping.additional_mappings[index] = secondary
        sec_decision = _classic_decision_for_mapping(
            secondary,
            confidence_policy=confidence_policy,
            overrides_cache=overrides_cache,
            equipment_overrides_cache=equipment_overrides_cache,
        )
        secondary_decisions.append(sec_decision)

    return mapping, primary_decision, secondary_decisions


def compute_parity_report(
    payload: dict,
    *,
    confidence_policy: Optional[str] = None,
    overrides: Optional[Dict[str, dict]] = None,
    equipment_overrides: Optional[Dict[str, dict]] = None,
) -> List[ParityDiscrepancy]:
    """Exécute le pipeline classique et `evaluate_equipment()` sur le même corpus.

    Un `MapperRegistry()` séparé est utilisé pour chaque chemin, afin qu'aucun état
    interne de mapping (ex. mutations en place du pipeline classique sur les
    secondaires) ne fuite d'un chemin à l'autre.

    Compare, à trois granularités (primaire / secondaire / commande) et pour chaque
    équipement éligible, les décisions produites par les deux chemins.

    Retourne la liste des écarts constatés (vide = parité totale). Chaque écart
    documente `eq_id`, `scope`, la décision de chaque chemin et un détail explicite.
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

        # Chemin classique — registre dédié, ne partage AUCUN état avec le chemin evaluate.
        classic_registry = MapperRegistry()
        classic_mapping, classic_decision, classic_secondaries = _classic_full_pipeline_for_eq(
            eq, snapshot,
            confidence_policy=effective_policy,
            mapper_registry=classic_registry,
            overrides_cache=overrides_cache,
            equipment_overrides_cache=equipment_overrides_cache,
        )

        # Chemin evaluate_equipment — registre dédié, isolé.
        evaluate_registry = MapperRegistry()
        evaluation = evaluate_equipment(
            eq, snapshot, result,
            mapper_registry=evaluate_registry,
            confidence_policy=effective_policy,
            persisted_overrides=overrides_cache,
            persisted_equipment_overrides=equipment_overrides_cache,
        )
        evaluate_decision = evaluation.equipment_decision

        # === Comparaison primaire ===
        if classic_decision is None:
            if evaluate_decision.reason != "no_mapping":
                discrepancies.append(ParityDiscrepancy(
                    eq_id=eq_id,
                    scope="primary",
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
                scope="primary",
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

        # === Comparaison secondaires (multi-sensor, Story 11.1) ===
        evaluate_secondaries = evaluation.secondary_decisions
        if len(classic_secondaries) != len(evaluate_secondaries):
            discrepancies.append(ParityDiscrepancy(
                eq_id=eq_id,
                scope="secondary[count]",
                classic_should_publish=None,
                classic_reason=None,
                evaluate_should_publish=None,
                evaluate_reason=None,
                detail=(
                    f"nombre de secondaires différent : classique={len(classic_secondaries)} "
                    f"vs evaluate={len(evaluate_secondaries)}"
                ),
            ))
        else:
            for i, (c_sec, e_sec) in enumerate(zip(classic_secondaries, evaluate_secondaries)):
                if (c_sec.should_publish != e_sec.should_publish
                        or c_sec.reason != e_sec.reason):
                    discrepancies.append(ParityDiscrepancy(
                        eq_id=eq_id,
                        scope=f"secondary[{i}]",
                        classic_should_publish=c_sec.should_publish,
                        classic_reason=c_sec.reason,
                        evaluate_should_publish=e_sec.should_publish,
                        evaluate_reason=e_sec.reason,
                        detail=(
                            f"secondaire #{i} : classique={c_sec.should_publish!r}/{c_sec.reason!r} "
                            f"vs evaluate={e_sec.should_publish!r}/{e_sec.reason!r}"
                        ),
                    ))

        # === Comparaison niveau COMMANDE ===
        # Pour chaque cmd_id couvert par le primaire (ou un secondaire), on vérifie que la
        # CommandDecision d'`evaluate_equipment` porte la même décision de publication que
        # l'entité qui la couvre côté classique.
        classic_cmd_index: Dict[int, PublicationDecision] = {}
        for cmd_id in mapping_cmd_ids(classic_mapping):
            classic_cmd_index.setdefault(cmd_id, classic_decision)
        for c_sec_mapping, c_sec_decision in zip(
            classic_mapping.additional_mappings or [], classic_secondaries
        ):
            for cmd_id in mapping_cmd_ids(c_sec_mapping):
                classic_cmd_index.setdefault(cmd_id, c_sec_decision)

        evaluate_cmd_index = {cd.cmd_id: cd for cd in evaluation.command_decisions}

        for cmd_id, classic_cmd_decision in classic_cmd_index.items():
            evaluate_cmd_decision = evaluate_cmd_index.get(cmd_id)
            if evaluate_cmd_decision is None:
                discrepancies.append(ParityDiscrepancy(
                    eq_id=eq_id,
                    scope=f"cmd[{cmd_id}]",
                    classic_should_publish=classic_cmd_decision.should_publish,
                    classic_reason=classic_cmd_decision.reason,
                    evaluate_should_publish=None,
                    evaluate_reason=None,
                    detail=f"cmd_id={cmd_id} manquante dans evaluate_equipment.command_decisions",
                ))
                continue
            if (classic_cmd_decision.should_publish != evaluate_cmd_decision.should_publish
                    or classic_cmd_decision.reason != evaluate_cmd_decision.reason):
                discrepancies.append(ParityDiscrepancy(
                    eq_id=eq_id,
                    scope=f"cmd[{cmd_id}]",
                    classic_should_publish=classic_cmd_decision.should_publish,
                    classic_reason=classic_cmd_decision.reason,
                    evaluate_should_publish=evaluate_cmd_decision.should_publish,
                    evaluate_reason=evaluate_cmd_decision.reason,
                    detail=(
                        f"cmd_id={cmd_id} : classique={classic_cmd_decision.should_publish!r}/"
                        f"{classic_cmd_decision.reason!r} vs evaluate="
                        f"{evaluate_cmd_decision.should_publish!r}/{evaluate_cmd_decision.reason!r}"
                    ),
                ))

    return discrepancies
