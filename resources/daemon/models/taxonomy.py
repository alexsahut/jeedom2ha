# ARTEFACT FIGÉ — Story 3.1. Ne pas modifier sans story dédiée.
# Stories 3.2, 3.3, 3.4 consomment en lecture seule.

PRIMARY_STATUSES: dict[str, str] = {
    "published":      "Publié",
    "excluded":       "Exclu",
    "ambiguous":      "Ambigu",
    "not_supported":  "Non supporté",
    "infra_incident": "Incident infrastructure",
}

REASON_CODE_TO_PRIMARY_STATUS: dict[str, str] = {
    "sure":                              "published",
    "probable":                          "published",
    "excluded_eqlogic":                  "excluded",
    "excluded_plugin":                   "excluded",
    "excluded_object":                   "excluded",
    "disabled_eqlogic":                  "not_supported",
    "disabled":                          "not_supported",
    "no_commands":                       "not_supported",
    "no_supported_generic_type":         "not_supported",
    "no_generic_type_configured":        "not_supported",
    "no_mapping":                        "not_supported",
    "low_confidence":                    "not_supported",
    "probable_skipped":                  "ambiguous",
    "ambiguous_skipped":                 "ambiguous",
    "discovery_publish_failed":          "infra_incident",
    "local_availability_publish_failed": "infra_incident",
}

PRIMARY_STATUS_LABELS: frozenset[str] = frozenset(PRIMARY_STATUSES.values())


def get_primary_status(reason_code: str) -> str:
    """Résout le statut principal à partir d'un reason_code.
    Fallback sécuritaire vers 'not_supported' si code inconnu.
    """
    return PRIMARY_STATUSES.get(
        REASON_CODE_TO_PRIMARY_STATUS.get(reason_code, "not_supported"),
        "Non supporté",
    )
