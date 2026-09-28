"""evaluate_equipment.py — Story 19.0 : contrat pur `CommandDecision` / `evaluate_equipment()`.

Rôle :
    Fonction pure qui encapsule `decide_publication()` (étape 4, Story 16.3) pour produire,
    en plus de la décision principale/secondaire déjà connue, une granularité nouvelle :
    une `CommandDecision` par `cmd_id` de l'équipement, y compris les commandes non
    couvertes par le mapping (AC1).

    Cette fonction n'est branchée dans AUCUN point d'appel réel (sync, navigation par pièce,
    aperçu, bouton "Publier") — ce câblage arrive en Story 19.1+. Elle ne recalcule jamais
    l'éligibilité (AC2, racine de CC-03) : le résultat `EligibilityResult` est un paramètre
    d'entrée obligatoire, consommé tel quel.

Invariants I1-I7 (portés de `decide_publication()`, Story 16.3) :
    I1 : équipement inéligible → décision refusée de niveau 1, sans mapping ni projection.
    I2 : projection invalide → jamais publié, même avec un override "force_publish".
    I3 : should_publish=True ⇔ confidence publishable ET is_valid=True ET type dans PRODUCT_SCOPE.
    I4 : le premier échec dans l'ordre 1→2→3→4 fait foi, jamais écrasé en aval.
    I5 : tout équipement éligible produit ses 3 sous-blocs (mapping → overrides → projection
         → décision) — jamais `None`, jamais une décision omise.
    I6 : `reason` toujours non-null et non-vide sur tous les chemins de retour.
    I7 : aucune logique MQTT/broker/cache dans ce module — aucune I/O disque, aucun réseau.

Non-mutation stricte (AC4) — révisée revue Alexandre PR #167 :
    Aucun objet d'ENTRÉE (`eq`, `snapshot`, `eligibility`, dicts d'overrides, mapping
    retourné par `mapper_registry.map()`, secondaires portés par ce mapping) n'est muté.
    Cette garantie est portée par les tests avant/après (AC4) — plus de `deepcopy` défensif
    systémique du snapshot complet : le coût est linéaire au nombre d'équipements du snapshot
    même quand on n'en évalue qu'un seul, ce qui rend le total d'un sync quadratique.
    La non-mutation est maintenant assurée par construction : `apply_type_override` renvoie
    une copie via `dataclasses.replace` en cas de match (sinon l'objet inchangé), et notre
    propre `replace(mapping, projection_validity=..., pipeline_step_reached=3)` produit un
    NOUVEAU mapping "working copy" que la fonction possède — celui-ci peut être muté
    directement pour créer le lien croisé bidirectionnel décision ↔ mapping (voir plus bas).

Liens croisés bidirectionnels (correction revue Alexandre PR #167) :
    Le mapping working et la décision produits par la fonction lui APPARTIENNENT — la
    contrainte de non-mutation ne porte que sur les entrées, pas sur les objets qu'elle vient
    de créer. On établit donc directement les deux références par assignation d'attribut sur
    ces objets nouvellement créés (comme le fait le pipeline classique de `http_server.py`,
    lignes 1440-1441) :
        - `decision.mapping_result is final_mapping`               → True
        - `final_mapping.publication_decision_ref is decision`     → True
        - idem pour CHAQUE décision/mapping secondaire.
    Ces liens sont réels (identité `is`, pas juste égalité `==`), ce qui permet au consumer
    (Story 19.1+) de naviguer d'une décision vers son mapping et réciproquement sans
    reconstruire d'index externe.

Registre de mappeurs et fonctions du pipeline injectables (Dev Notes) :
    `mapper_registry` est un paramètre obligatoire (jamais instancié en interne). Les deux
    fonctions du pipeline (`decide_publication`, `validate_projection`) sont injectables via
    `decide_publication_fn`/`validate_projection_fn` (défaut = implémentations réelles), pour
    permettre au harnais de parité (Task 4) de substituer des doublures instrumentées sans
    modifier cette fonction.

Fusion des overrides (AC3) :
    Point unique de fusion overrides persistés + overrides proposés (aperçu, non sauvegardés) :
    `merge_override_layer`. La fusion est CHAMP PAR CHAMP à une même clé (schéma v2,
    `mapping/overrides.py` : une entrée peut porter à la fois `ha_entity_type` et
    `publication_override`) — un `proposed` partiel ne fait jamais disparaître un champ
    persisté non recouvert (correction revue bot, PR #167). Fournir uniquement des overrides
    persistés (aucun `proposed_*`) produit un résultat identique à l'appel actuel de
    `decide_publication()` sur le même cas.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional

from mapping.overrides import apply_type_override, mapping_cmd_ids, resolve_publication_override
from models.decide_publication import (
    DEFAULT_CONFIDENCE_POLICY,
    decide_publication as _default_decide_publication,
)
from models.mapping import MappingResult, ProjectionValidity, PublicationDecision
from models.topology import EligibilityResult, JeedomEqLogic, TopologySnapshot
from validation.ha_component_registry import validate_projection as _default_validate_projection

# Story 19.0 (Task 1) — commande d'un équipement éligible et mappé, mais qu'aucun mapper ni
# aucun override n'a rattachée à un `cmd_id` de la sortie (ni mapping primaire, ni secondaire).
_COMMAND_NOT_COVERED_REASON = "command_not_covered"

# Story 19.0 (Task 1) — alias de la taxonomie fermée déjà en vigueur côté diagnostic UX
# (`transport/http_server.py:1949`, `_CLOSED_REASON_MAP`) : un équipement inéligible pour
# absence de type générique supporté porte ce reason_code aliasé, jamais le legacy brut.
_ELIGIBILITY_REASON_ALIAS: Dict[str, str] = {
    "no_supported_generic_type": "no_generic_type_configured",
}

# Reasons produits par decide_publication() au "Niveau 1" (cause étape 2 — mapping non
# publiable) → pipeline step "2" du point de vue de CommandDecision.step (I4).
_STEP2_REASONS = frozenset({"no_mapping", "ambiguous_skipped"})

# Reasons du "Niveau 2b" (Story 16.3, override d'exclusion explicite) → step "2b".
_STEP2B_REASONS = frozenset({"publication_excluded_eqlogic", "publication_excluded_command"})

# Reasons des "Niveaux 3/4" (cause étape 4a/4b, ou nominal) → step "4".
_STEP4_REASONS = frozenset(
    {
        "ha_component_not_in_product_scope",
        "probable_skipped",
        "publication_forced",
        "sure",
        "probable",
        "sure_mapping",
    }
)


@dataclass
class CommandDecision:
    """Décision de publication pour une seule commande (`cmd_id`) — Story 19.0, AC1.

    Une instance par `cmd_id` connu de l'équipement en entrée, y compris les commandes non
    couvertes par le mapping (`reason=="command_not_covered"`). `reason` est toujours
    non-null (I6). `step` porte le niveau I4 du premier échec retenu : "1" (éligibilité),
    "2" (mapping/commande non couverte), "2b" (override d'exclusion), "3" (projection HA),
    "4" (scope produit / politique de confiance / nominal).
    """

    cmd_id: int
    should_publish: bool
    reason: str
    step: str
    reason_details: Optional[Dict[str, object]] = None


@dataclass
class EquipmentEvaluation:
    """Sortie complète de `evaluate_equipment()` — décision principale, secondaires, commandes."""

    equipment_decision: PublicationDecision
    secondary_decisions: List[PublicationDecision] = field(default_factory=list)
    command_decisions: List[CommandDecision] = field(default_factory=list)
    mapping: Optional[MappingResult] = None


def merge_override_layer(
    persisted: Optional[Dict[str, dict]],
    proposed: Optional[Dict[str, dict]],
) -> Dict[str, dict]:
    """Point unique de fusion overrides persistés + overrides proposés (AC3).

    Le calque `proposed` (aperçu, non encore sauvegardé) est prioritaire CHAMP PAR CHAMP sur
    `persisted` à une même clé (schéma v2, `mapping/overrides.py` : une entrée peut porter à la
    fois `ha_entity_type` et `publication_override`) — un `proposed` partiel (ex. seulement
    `publication_override`) ne doit jamais faire disparaître un champ persisté non recouvert
    (ex. `ha_entity_type`). Les clés persistées non recouvertes par `proposed` restent inchangées.
    Ne mute jamais `persisted` ni `proposed` — retourne toujours de nouveaux dicts (deepcopy).

    Public depuis Story 19.3 (était `_merge_override_layer`) : réutilisé par
    `transport/http_server.py` pour reconstruire, à l'identique, le calque fusionné qui sert
    UNIQUEMENT à l'affichage du champ `publication_override` brut de l'aperçu — jamais pour
    recalculer une décision (celle-ci vient exclusivement d'`evaluate_equipment()`).
    """
    merged: Dict[str, dict] = deepcopy(dict(persisted or {}))
    for key, entry in (proposed or {}).items():
        base = dict(merged.get(key) or {})
        base.update(deepcopy(dict(entry)))
        merged[key] = base
    return merged


def _resolve_publication_override_for_mapping(
    mapping: MappingResult,
    overrides: Dict[str, dict],
    equipment_overrides: Dict[str, dict],
) -> Optional[str]:
    """Résout l'override de publication effectif pour un mapping (mêmes règles que
    `transport/http_server.py:_resolve_publication_override_for_mapping`, répliquées ici en
    pur car ce module ne peut pas importer `transport/` — sens unique D8)."""
    for cmd_id in mapping_cmd_ids(mapping) or [-1]:
        candidate = resolve_publication_override(
            mapping.jeedom_eq_id, cmd_id, overrides, equipment_overrides
        )
        if candidate is not None:
            return candidate
    return None


def _apply_type_override_with_proposed_priority(
    mapping: MappingResult,
    merged_overrides: Dict[str, dict],
    proposed_overrides: Optional[Dict[str, dict]],
) -> MappingResult:
    """Applique l'override TYPE en priorisant le calque `proposed` (Story 19.3, AC2).

    `apply_type_override` retient le PREMIER `cmd_id` (ordre `mapping_cmd_ids`) qui a une
    entrée dans le dict d'overrides fourni. Une fois `persisted` et `proposed` aplatis en un
    seul `merged_overrides` (`merge_override_layer`), un override persisté sur un `cmd_id`
    frère du même mapping peut donc l'emporter sur l'override réellement proposé (aperçu)
    d'un AUTRE `cmd_id` de ce même mapping, par simple accident d'ordre d'itération — c'est le
    test « conflit inter-commandes » exigé par les Dev Notes de la story 19.3.

    Fix : si `proposed_overrides` couvre au moins une clé de `merged_overrides`, on tente
    D'ABORD `apply_type_override` restreint à CES clés proposées uniquement ; si ça matche,
    c'est ce résultat qui gagne. Sinon (aucune clé proposée ne matche ce mapping), on retombe
    sur le comportement historique avec le dict fusionné complet.

    No-op garanti pour le sync : le sync n'appelle jamais `evaluate_equipment` avec
    `proposed_overrides` (toujours `None`), donc `proposed_keys` est vide et cette fonction
    se réduit strictement à `apply_type_override(mapping, "", overrides=merged_overrides)`.
    """
    proposed_keys = set((proposed_overrides or {}).keys())
    if proposed_keys:
        priority_overrides = {k: v for k, v in merged_overrides.items() if k in proposed_keys}
        if priority_overrides:
            patched = apply_type_override(mapping, "", overrides=priority_overrides)
            if patched is not mapping:
                return patched
    return apply_type_override(mapping, "", overrides=merged_overrides)


def _step_for_decision(decision: PublicationDecision) -> str:
    """Dérive le niveau I4 (step) d'une `PublicationDecision` déjà résolue."""
    if decision.reason in _STEP2_REASONS:
        return "2"
    if decision.reason in _STEP2B_REASONS:
        return "2b"
    if decision.reason in _STEP4_REASONS:
        return "4"
    # Tout le reste provient du reason_code de projection_validity (étape 3), y compris les
    # chemins défensifs anti-contrat (`skipped_no_mapping_candidate`/`skipped_upstream_failure`).
    return "3"


def _decide_for_mapping(
    mapping: MappingResult,
    *,
    confidence_policy: str,
    overrides: Dict[str, dict],
    equipment_overrides: Dict[str, dict],
    validate_projection_fn: Callable[[str, object], ProjectionValidity],
    decide_publication_fn: Callable[..., PublicationDecision],
) -> "tuple[MappingResult, PublicationDecision]":
    """Étape 3 (validation projection) puis 4 (décision) pour un seul `MappingResult`
    (primaire ou secondaire) — sans finaliser encore `additional_mappings` (fait par
    l'appelant une fois les secondaires eux-mêmes décidés, cf. `evaluate_equipment`).

    Retourne un "working mapping" NEUF (via `dataclasses.replace`) que l'appelant possède
    et peut muter librement pour poser `publication_decision_ref` (finalisation, étape 4).
    Le mapping d'entrée reste intact (source retournée par le registre / patchée par
    `apply_type_override`).
    """
    validity = validate_projection_fn(mapping.ha_entity_type, mapping.capabilities)
    working_mapping = replace(
        mapping, projection_validity=validity, pipeline_step_reached=3
    )

    publication_override = _resolve_publication_override_for_mapping(
        working_mapping, overrides, equipment_overrides
    )
    decision = decide_publication_fn(
        working_mapping,
        confidence_policy=confidence_policy,
        publication_override=publication_override,
    )
    return working_mapping, decision


def _finalize_cross_reference(
    working_mapping: MappingResult,
    decision: PublicationDecision,
    *,
    additional_mappings: Optional[List[MappingResult]] = None,
) -> None:
    """Établit le lien croisé bidirectionnel décision ↔ mapping — Story 19.0 (revue Alexandre).

    Le `working_mapping` et la `decision` sont des objets NOUVELLEMENT CRÉÉS par la fonction
    (via `replace()` et `decide_publication_fn()`) — la contrainte de non-mutation ne s'applique
    pas à eux (elle ne porte que sur les entrées d'`evaluate_equipment`). On peut donc leur
    assigner directement leurs références croisées comme le fait `http_server.py:1440-1441` :

        decision.mapping_result = working_mapping
        working_mapping.publication_decision_ref = decision

    Cela produit un lien réel `is`-identifiable dans les deux sens, ce qui n'était pas possible
    tant qu'on repassait par `replace` (chaque `replace` casse l'identité côté opposé).

    L'appelant fait circuler `additional_mappings` finalisées côté primaire uniquement (une
    fois les secondaires eux-mêmes finalisées).
    """
    if additional_mappings is not None:
        working_mapping.additional_mappings = additional_mappings
    working_mapping.pipeline_step_reached = 4
    decision.mapping_result = working_mapping
    working_mapping.publication_decision_ref = decision


def evaluate_equipment(
    eq: JeedomEqLogic,
    snapshot: TopologySnapshot,
    eligibility: EligibilityResult,
    *,
    mapper_registry: object,
    confidence_policy: str = DEFAULT_CONFIDENCE_POLICY,
    persisted_overrides: Optional[Dict[str, dict]] = None,
    persisted_equipment_overrides: Optional[Dict[str, dict]] = None,
    proposed_overrides: Optional[Dict[str, dict]] = None,
    proposed_equipment_overrides: Optional[Dict[str, dict]] = None,
    decide_publication_fn: Callable[..., PublicationDecision] = _default_decide_publication,
    validate_projection_fn: Callable[[str, object], ProjectionValidity] = _default_validate_projection,
) -> EquipmentEvaluation:
    """Évalue un équipement et produit une `CommandDecision` par `cmd_id` (Story 19.0).

    Args:
        eq: équipement Jeedom (snapshot topologie) — jamais muté (AC4, vérifié par test
            avant/après ; plus de `deepcopy` défensif systémique).
        snapshot: instantané topologie complet — jamais muté (AC4, vérifié par test avant/
            après). Transmis tel quel au registre : le coût d'une copie linéaire du snapshot
            à chaque appel devient quadratique sur un sync complet (revue Alexandre PR #167 —
            292 équipements × ~13 ms/copie ≈ 3.7 s de surcoût par sync sur le matériel de la
            box).
        eligibility: résultat d'éligibilité déjà calculé en amont — jamais recalculé ici
            (AC2, racine de CC-03) ; consommé tel quel, jamais muté (AC4).
        mapper_registry: registre de mappeurs (ex. `mapping.registry.MapperRegistry()`)
            injecté par l'appelant — jamais instancié en interne (Dev Notes).
        confidence_policy: transmis tel quel à `decide_publication`.
        persisted_overrides / persisted_equipment_overrides: overrides déjà sauvegardés
            (`ha_overrides.json`), fournis par l'appelant — cette fonction ne lit jamais
            le disque (I7).
        proposed_overrides / proposed_equipment_overrides: overrides proposés, non encore
            sauvegardés (cas de l'aperçu/preview) — fusionnés en un point unique avec les
            overrides persistés (AC3).
        decide_publication_fn / validate_projection_fn: fonctions du pipeline injectables
            (défaut = implémentations réelles), pour permettre au harnais de parité (Task 4)
            de substituer des doublures instrumentées.

    Returns:
        EquipmentEvaluation : décision principale, décisions secondaires (multi-sensor),
        et une CommandDecision par cmd_id connu de `eq` — jamais vide si `eq.cmds` est non
        vide, jamais `None` (I5). La décision principale et son mapping partagent des
        références croisées bidirectionnelles `is`-identifiables (idem pour chaque secondaire).
    """
    merged_overrides = merge_override_layer(persisted_overrides, proposed_overrides)
    merged_equipment_overrides = merge_override_layer(
        persisted_equipment_overrides, proposed_equipment_overrides
    )

    known_cmd_ids: List[int] = list(dict.fromkeys(cmd.id for cmd in eq.cmds))

    # I1 — équipement inéligible : décision refusée de niveau 1, sans mapping ni projection.
    if not eligibility.is_eligible:
        aliased_reason = _ELIGIBILITY_REASON_ALIAS.get(
            eligibility.reason_code, eligibility.reason_code
        )
        equipment_decision = PublicationDecision(
            should_publish=False,
            reason=aliased_reason,
            reason_details={"eligibility_reason_code": eligibility.reason_code},
        )
        command_decisions = [
            CommandDecision(
                cmd_id=cmd_id,
                should_publish=False,
                reason=aliased_reason,
                step="1",
                reason_details={"eligibility_reason_code": eligibility.reason_code},
            )
            for cmd_id in known_cmd_ids
        ]
        return EquipmentEvaluation(
            equipment_decision=equipment_decision,
            secondary_decisions=[],
            command_decisions=command_decisions,
            mapping=None,
        )

    # I5 — équipement éligible : mapping (registre injecté) → fusion overrides → validation
    # → décision, sans mapping ni projection fournis en entrée. Jamais None, jamais omise.
    raw_mapping = mapper_registry.map(eq, snapshot)

    if raw_mapping is None:
        equipment_decision = PublicationDecision(should_publish=False, reason="no_mapping")
        command_decisions = [
            CommandDecision(
                cmd_id=cmd_id,
                should_publish=False,
                reason=_COMMAND_NOT_COVERED_REASON,
                step="2",
                reason_details={"covered": False},
            )
            for cmd_id in known_cmd_ids
        ]
        return EquipmentEvaluation(
            equipment_decision=equipment_decision,
            secondary_decisions=[],
            command_decisions=command_decisions,
            mapping=None,
        )

    # Story 16.2 — override de type utilisateur, injecté ENTRE étape 2 (map) et étape 3
    # (validate_projection), même point d'insertion que le sync (D10/D11 préservés). Le
    # `raw_mapping` retourné par le registre reste intact : `apply_type_override` renvoie
    # une copie via `replace` si un override matche, sinon l'objet inchangé.
    patched_primary = _apply_type_override_with_proposed_priority(
        raw_mapping, merged_overrides, proposed_overrides
    )

    primary_mapping, primary_decision = _decide_for_mapping(
        patched_primary,
        confidence_policy=confidence_policy,
        overrides=merged_overrides,
        equipment_overrides=merged_equipment_overrides,
        validate_projection_fn=validate_projection_fn,
        decide_publication_fn=decide_publication_fn,
    )
    original_secondaries = raw_mapping.additional_mappings or []

    secondary_decisions: List[PublicationDecision] = []
    updated_secondaries: List[MappingResult] = []
    for raw_secondary in original_secondaries:
        patched_secondary = _apply_type_override_with_proposed_priority(
            raw_secondary, merged_overrides, proposed_overrides
        )
        working_secondary, secondary_decision = _decide_for_mapping(
            patched_secondary,
            confidence_policy=confidence_policy,
            overrides=merged_overrides,
            equipment_overrides=merged_equipment_overrides,
            validate_projection_fn=validate_projection_fn,
            decide_publication_fn=decide_publication_fn,
        )
        # Chaque secondaire est un objet NOUVEAU (créé par `replace` dans `_decide_for_mapping`),
        # on peut donc y assigner directement le lien croisé bidirectionnel.
        _finalize_cross_reference(
            working_secondary,
            secondary_decision,
            additional_mappings=working_secondary.additional_mappings,
        )
        secondary_decisions.append(secondary_decision)
        updated_secondaries.append(working_secondary)

    # Finalisation étape 4 du primaire une fois les secondaires eux-mêmes finalisées, pour
    # que `primary_decision.mapping_result.additional_mappings` reflète les décisions
    # secondaires réelles (revue Codex, PR #167). Assignation directe : `primary_mapping`
    # a été créé par `replace()` dans `_decide_for_mapping`, il nous appartient.
    _finalize_cross_reference(
        primary_mapping, primary_decision, additional_mappings=updated_secondaries
    )

    # AC1 — une CommandDecision par cmd_id connu de l'équipement, y compris non couvertes.
    covered: Dict[int, "tuple[PublicationDecision, str]"] = {}
    for cmd_id in mapping_cmd_ids(primary_mapping):
        covered.setdefault(cmd_id, (primary_decision, _step_for_decision(primary_decision)))
    for secondary, secondary_decision in zip(updated_secondaries, secondary_decisions):
        for cmd_id in mapping_cmd_ids(secondary):
            covered.setdefault(cmd_id, (secondary_decision, _step_for_decision(secondary_decision)))

    command_decisions: List[CommandDecision] = []
    for cmd_id in known_cmd_ids:
        if cmd_id in covered:
            decision, step = covered[cmd_id]
            command_decisions.append(
                CommandDecision(
                    cmd_id=cmd_id,
                    should_publish=decision.should_publish,
                    reason=decision.reason,
                    step=step,
                    reason_details=deepcopy(decision.reason_details),
                )
            )
        else:
            command_decisions.append(
                CommandDecision(
                    cmd_id=cmd_id,
                    should_publish=False,
                    reason=_COMMAND_NOT_COVERED_REASON,
                    step="2",
                    reason_details={"covered": False},
                )
            )

    return EquipmentEvaluation(
        equipment_decision=primary_decision,
        secondary_decisions=secondary_decisions,
        command_decisions=command_decisions,
        mapping=primary_mapping,
    )
