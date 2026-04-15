# ARTEFACT FIGÉ — Story 4.1. Ne pas modifier sans story dédiée.
"""Table de traduction reason_code → (cause_code, cause_label, cause_action).

Module pur, standalone — aucune dépendance sur http_server, aggregation, taxonomy.
Direction 1 : inclus mais non publié (15 entrées actives + 3 published + 1 fallback).
Direction 2 : exclu mais encore publié dans HA (build_cause_for_pending_unpublish).
"""

from __future__ import annotations

from typing import Optional, Tuple

# Table figée : reason_code → (cause_code, cause_label, cause_action)
# None dans cause_action signifie "aucune action recommandée pour ce cas".
_REASON_CODE_TO_CAUSE: dict = {
    # --- 15 entrées actives (direction 1 — inclus mais non publié) ---
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
        "Type non supporté en V1",
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
        "Composant Home Assistant non ouvert dans ce cycle",
        "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant.",
    ),
    "eligible": (
        "no_mapping",
        "Aucun mapping compatible",
        "Relancer un sync complet depuis l'interface du plugin",
    ),
    # --- 3 codes published → pas d'écart direction 1 ---
    "sure": (None, None, None),
    "probable": (None, None, None),
    "sure_mapping": (None, None, None),
}


def reason_code_to_cause(reason_code: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Traduit un reason_code en (cause_code, cause_label, cause_action).

    Retourne (None, None, None) si le reason_code ne produit pas d'écart direction 1
    (cas published ou reason_code inconnu — fallback sécuritaire).
    """
    return _REASON_CODE_TO_CAUSE.get(reason_code, (None, None, None))


def build_cause_for_pending_unpublish() -> Tuple[str, str, str]:
    """Retourne la cause figée pour un équipement exclu mais encore publié dans HA (direction 2)."""
    return (
        "pending_unpublish",
        "Changement en attente d'application",
        "Republier pour appliquer le changement",
    )
