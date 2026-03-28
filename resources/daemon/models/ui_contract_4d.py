# ARTEFACT — Story 4.1 (corrigé 4.1-fix terrain 2026-03-27).
from __future__ import annotations

"""Fonctions de calcul du contrat UI canonique 4D.

Périmètre / Statut / Écart / Cause — couche de sérialisation API uniquement.
Aucune dépendance sur http_server, aggregation, taxonomy.

NOTE TERRAIN 2026-03-27 : has_pending_home_assistant_changes N'EST PAS un
indicateur de présence HA réelle. C'est un XOR (desired != actual) qui vaut
True aussi bien pour un inclus-non-publié que pour un exclu-encore-publié.
Le vrai signal est publications[eq_id].active_or_alive || pending_discovery_unpublish.
"""

_EXCLUSION_REASON_TO_PERIMETRE: dict[str, str] = {
    "excluded_eqlogic": "exclu_sur_equipement",
    "excluded_plugin":  "exclu_par_plugin",
    "excluded_object":  "exclu_par_piece",
}


def reason_code_to_perimetre(reason_code: str) -> str:
    """Mappe un reason_code vers la valeur canonique du champ perimetre.

    Les trois reason_codes d'exclusion retournent leur valeur d'exclusion spécifique.
    Tout autre reason_code (published, ambiguous, not_supported, infra) → 'inclus'.
    La valeur 'inherit' n'est jamais retournée (résolue en amont du pipeline).
    """
    return _EXCLUSION_REASON_TO_PERIMETRE.get(reason_code, "inclus")


def compute_ecart(perimetre: str, statut: str) -> bool:
    """Calcule l'écart bidirectionnel entre périmètre et état HA réel.

    Direction 1 : inclus dans le périmètre mais non publié dans HA.
    Direction 2 : exclu du périmètre mais encore physiquement présent dans HA.

    Fonction pure de (perimetre, statut) uniquement — pas de has_pending.
    Le champ statut doit refléter l'état HA réel (via publications/pending_discovery_unpublish),
    pas le flag has_pending_home_assistant_changes qui est un XOR ambigü.
    """
    direction_1 = (perimetre == "inclus") and (statut == "non_publie")
    direction_2 = perimetre.startswith("exclu_") and (statut == "publie")
    return direction_1 or direction_2


def build_ui_counters(equipments_4d: list[dict]) -> dict:
    """Calcule les compteurs 4D agrégés à partir d'une liste d'équipements résolus.

    Paramètre : liste de dicts contenant au moins les clés 'perimetre' et 'ecart'.
    Invariant obligatoire : total = inclus + exclus.
    'ecarts' compte les deux directions (direction 1 ET direction 2).
    """
    total = len(equipments_4d)
    inclus = sum(1 for eq in equipments_4d if eq.get("perimetre") == "inclus")
    exclus = total - inclus
    ecarts = sum(1 for eq in equipments_4d if eq.get("ecart") is True)
    return {
        "total": total,
        "inclus": inclus,
        "exclus": exclus,
        "ecarts": ecarts,
    }
