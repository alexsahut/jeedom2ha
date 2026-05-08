# ARTEFACT FIGÉ — Story 4.1 / Story 4.3 / Story 6.2 (CAUSE_MAPPING + resolve_cause_ux) / Story 6.3 (sémantique honnête) / Story 9.4 (3 codes dégradation élégante §11) / Story 9.5 (cause_action non-null FallbackMapper). Ne pas modifier sans story dédiée.
"""Table de traduction reason_code → (cause_code, cause_label, cause_action).

Module pur, standalone — aucune dépendance sur http_server, aggregation, taxonomy.
Direction 1 : inclus mais non publié (20 entrées actives + 3 published + fallback contractuel).
Direction 2 : exclu mais encore publié dans HA (build_cause_for_pending_unpublish).

Règle de contrat cause_action (Story 6.3) :
- cause_action = None si aucune remédiation utilisateur directe n'existe.
- class 2 (invalidité HA) et class 3 (scope produit) → cause_action = None.
- La couche d'affichage présente un message standardisé pour tout cause_action None.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

# Table figée : reason_code → (cause_code, cause_label, cause_action)
# None dans cause_action signifie "aucune action recommandée pour ce cas".
_REASON_CODE_TO_CAUSE: dict = {
    # --- 20 entrées actives (direction 1 — inclus mais non publié) ---
    # --- Exclusions de scope utilisateur (étape 1 — ordre canonique : exclu > désactivé > ...) ---
    "excluded_eqlogic": (
        "excluded_eqlogic",
        "Équipement exclu du scope de synchronisation",
        "Retirer l'équipement de la liste d'exclusion dans les réglages jeedom2ha",
    ),
    "excluded_plugin": (
        "excluded_plugin",
        "Plugin exclu du scope de synchronisation",
        "Retirer le plugin de la liste d'exclusion dans les réglages jeedom2ha",
    ),
    "excluded_object": (
        "excluded_object",
        "Objet Jeedom exclu du scope de synchronisation",
        "Retirer l'objet de la liste d'exclusion dans les réglages jeedom2ha",
    ),
    "ambiguous_skipped": (
        "ambiguous_skipped",
        "Mapping ambigu — plusieurs types possibles",
        "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
    ),
    "probable_skipped": (
        "ambiguous_skipped",
        "Mapping ambigu — plusieurs types possibles",
        "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
    ),
    "no_mapping": (
        "no_mapping",
        "Aucun mapping compatible",
        "Vérifier les types génériques des commandes dans Jeedom",
    ),
    "no_supported_generic_type": (
        "no_supported_generic_type",
        "Types génériques Jeedom hors périmètre du cycle courant",
        None,
    ),
    "no_generic_type_configured": (
        "no_generic_type_configured",
        "Types génériques non configurés sur les commandes",
        "Configurer les types génériques via le plugin Jeedom concerné, puis relancer un rescan",
    ),
    "disabled_eqlogic": (
        "disabled_eqlogic",
        "Équipement désactivé dans Jeedom",
        "Activer l'équipement dans sa page de configuration Jeedom",
    ),
    "disabled": (
        "disabled_eqlogic",
        "Équipement désactivé dans Jeedom",
        "Activer l'équipement dans sa page de configuration Jeedom",
    ),
    "no_commands": (
        "no_commands",
        "Équipement sans commandes exploitables",
        "Vérifier que l'équipement possède des commandes actives dans Jeedom",
    ),
    "discovery_publish_failed": (
        "discovery_publish_failed",
        "Publication MQTT échouée",
        "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
    ),
    "local_availability_publish_failed": (
        "discovery_publish_failed",
        "Publication MQTT échouée",
        "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
    ),
    "low_confidence": (
        "low_confidence",
        "Confiance insuffisante pour la politique active",
        "Assouplir la politique de confiance si vous souhaitez autoriser un mapping moins fiable.",
    ),
    "ha_component_not_in_product_scope": (
        "not_in_product_scope",
        "Type d'entité HA reconnu — hors périmètre d'ouverture du cycle courant",
        None,  # class 3 — gouvernance de cycle, aucune action utilisateur directe
    ),
    "eligible": (
        "no_mapping",
        "Aucun mapping compatible",
        "Relancer un sync complet depuis l'interface du plugin",
    ),
    # --- Codes classe 2 — Validation HA (étape 3, AR8) ---
    # cause_action = None : contrainte structurelle de l'appareil physique, pas d'action utilisateur directe
    "ha_missing_command_topic": (
        "ha_missing_command_topic",
        "Projection HA incomplète — commande requise absente",
        None,
    ),
    "ha_missing_state_topic": (
        "ha_missing_state_topic",
        "Projection HA incomplète — état requis absent",
        None,
    ),
    "ha_missing_required_option": (
        "ha_missing_required_option",
        "Projection HA incomplète — champ obligatoire manquant",
        None,
    ),
    "ha_component_unknown": (
        "ha_component_unknown",
        "Type d'entité HA inconnu du moteur",
        None,
    ),
    # --- 3 codes dégradation élégante Story 9.4 (§11 cadrage) ---
    # Story 9.5 : fallback_sensor_default / fallback_button_default → cause_action non-null (surface vague 1 réelle)
    # no_projection_possible → cause_action = None (aucune remédiation directe)
    "fallback_sensor_default": (
        "fallback_sensor_default",
        "Projection en dégradation élégante — capteur par défaut",
        "Configurer les types génériques des commandes Info dans Jeedom pour permettre une projection spécifique",
    ),
    "fallback_button_default": (
        "fallback_button_default",
        "Projection en dégradation élégante — bouton par défaut",
        "Configurer les types génériques des commandes Action dans Jeedom pour permettre une projection spécifique",
    ),
    "no_projection_possible": (
        "no_projection_possible",
        "Projection impossible — aucune commande exploitable détectée",
        None,
    ),
    # --- 3 codes published → pas d'écart direction 1 ---
    "sure": (None, None, None),
    "probable": (None, None, None),
    "sure_mapping": (None, None, None),
}

# Story 6.2 / 6.3 — mapping UX contextuel (reason_code canonique + étape pipeline visible).
# Fonction pure, sans logique métier : traduit uniquement la présentation utilisateur.
# Règle no faux CTA (Story 6.3) : action = None si aucune surface réelle dans jeedom2ha.
CAUSE_MAPPING: dict = {
    "ambiguous": {
        "step_3": {
            "label": "Projection HA structurellement incomplète — ambiguïté de mapping non résolue",
            "action": "Préciser les types génériques sur les commandes dans Jeedom pour lever l'ambiguïté",
        },
        "step_4": {
            "label": "Arbitrage de publication non automatique — ambiguïté de mapping non résolue",
            "action": "Préciser les types génériques sur les commandes dans Jeedom pour lever l'ambiguïté",  # Story 9.5 : surface vague 1 réelle ouverte
        },
    },
    "ambiguous_skipped": {
        "step_3": {
            "label": "Projection HA structurellement incomplète — ambiguïté de mapping non résolue",
            "action": "Préciser les types génériques sur les commandes dans Jeedom pour lever l'ambiguïté",
        },
        "step_4": {
            "label": "Arbitrage de publication non automatique — ambiguïté de mapping non résolue",
            "action": "Préciser les types génériques sur les commandes dans Jeedom pour lever l'ambiguïté",  # Story 9.5 : chemin critique FallbackMapper — surface vague 1 réelle
        },
    },
}

# Alias fermés provenant de la taxonomie decision_trace.reason_code.
_CAUSE_UX_REASON_ALIASES: dict = {
    "confidence_policy_skipped": "probable_skipped",
}

_CAUSE_UX_FALLBACK: dict = {
    "cause_label": "Cause non catégorisée — vérifier le diagnostic détaillé",
    "cause_action": "Relancer un sync complet puis consulter les logs du démon si le blocage persiste.",
}


def reason_code_to_cause(reason_code: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Traduit un reason_code en (cause_code, cause_label, cause_action).

    Retourne (None, None, None) si le reason_code ne produit pas d'écart direction 1
    (cas published ou reason_code inconnu — fallback sécuritaire).
    """
    return _REASON_CODE_TO_CAUSE.get(reason_code, (None, None, None))


def resolve_cause_ux(reason_code: str, pipeline_step: int) -> Dict[str, Optional[str]]:
    """Résout (cause_label, cause_action) depuis reason_code + étape visible.

    Règles :
    - lecture pure depuis des mappings backend (aucune logique métier)
    - fallback explicite si mapping absent
    - cause_action = None si aucune remédiation utilisateur directe n'existe (Story 6.3)
    """
    normalized_reason = str(reason_code or "").strip()
    step_key = f"step_{pipeline_step}" if isinstance(pipeline_step, int) else ""

    contextual = CAUSE_MAPPING.get(normalized_reason, {}).get(step_key)
    if contextual:
        action_val = contextual.get("action")
        return {
            "cause_label": str(contextual.get("label", "")).strip(),
            "cause_action": action_val if isinstance(action_val, str) and action_val else None,
        }

    aliased_reason = _CAUSE_UX_REASON_ALIASES.get(normalized_reason, normalized_reason)
    _, cause_label, cause_action = reason_code_to_cause(aliased_reason)
    if isinstance(cause_label, str) and cause_label:
        return {
            "cause_label": cause_label,
            "cause_action": cause_action if isinstance(cause_action, str) and cause_action else None,
        }

    return dict(_CAUSE_UX_FALLBACK)


def build_cause_for_pending_unpublish() -> Tuple[str, str, str]:
    """Retourne la cause figée pour un équipement exclu mais encore publié dans HA (direction 2)."""
    return (
        "pending_unpublish",
        "Changement en attente d'application",
        "Republier pour appliquer le changement",
    )
