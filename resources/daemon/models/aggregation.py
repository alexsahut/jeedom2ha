# ARTEFACT FIGÉ — Story 3.3. Ne pas modifier sans story dédiée.
# Story 3.4 consomme en lecture seule.

"""Moteur d'agrégation pur des statuts d'équipements.

Prend une liste de dicts d'équipements (chacun avec 'status_code' et 'reason_code')
et retourne un objet summary agrégé.

Identifiants canoniques des statuts (Story 3.1) :
  published, excluded, ambiguous, not_supported, infra_incident

Statuts agrégés produits :
  empty, infra_incident, ambiguous, partially_published, not_supported, excluded, published
"""

_CANONICAL_STATUSES: tuple = (
    "published",
    "excluded",
    "ambiguous",
    "not_supported",
    "infra_incident",
)


def build_summary(equipments: list) -> dict:
    """Construit le summary agrégé à partir d'une liste d'équipements.

    Args:
        equipments: liste de dicts, chacun avec au moins 'status_code' et 'reason_code'.

    Returns:
        dict avec primary_aggregated_status, total_equipments, counts_by_status, counts_by_reason.
    """
    total = len(equipments)
    counts_by_status: dict = {s: 0 for s in _CANONICAL_STATUSES}
    counts_by_reason: dict = {}

    for eq in equipments:
        status_code = eq.get("status_code", "not_supported")
        if status_code not in counts_by_status:
            status_code = "not_supported"
        counts_by_status[status_code] += 1
        reason_code = eq.get("reason_code", "unknown")
        counts_by_reason[reason_code] = counts_by_reason.get(reason_code, 0) + 1

    return {
        "primary_aggregated_status": compute_primary_aggregated_status(counts_by_status, total),
        "total_equipments": total,
        "counts_by_status": counts_by_status,
        "counts_by_reason": counts_by_reason,
    }


def compute_primary_aggregated_status(counts_by_status: dict, total_equipments: int) -> str:
    """Calcule le statut agrégé principal selon la hiérarchie de priorité stricte.

    Hiérarchie (par ordre décroissant de priorité) :
      1. empty           — aucun équipement
      2. infra_incident  — au moins 1 incident infrastructure
      3. ambiguous       — au moins 1 ambigu
      4. partially_published — au moins 1 publié ET au moins 1 exclu ou non-supporté
      5. not_supported   — au moins 1 non-supporté
      6. excluded        — au moins 1 exclu
      7. published       — sinon (tous publiés)

    Note : l'identifiant canonique est 'infra_incident' (jamais 'infrastructure_incident').
    """
    if total_equipments == 0:
        return "empty"
    if counts_by_status.get("infra_incident", 0) > 0:
        return "infra_incident"
    if counts_by_status.get("ambiguous", 0) > 0:
        return "ambiguous"
    if (
        counts_by_status.get("published", 0) > 0
        and (
            counts_by_status.get("excluded", 0) > 0
            or counts_by_status.get("not_supported", 0) > 0
        )
    ):
        return "partially_published"
    if counts_by_status.get("not_supported", 0) > 0:
        return "not_supported"
    if counts_by_status.get("excluded", 0) > 0:
        return "excluded"
    return "published"
