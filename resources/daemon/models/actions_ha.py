# ARTEFACT — Story 5.1 : signal actions_ha par équipement.
from __future__ import annotations

"""Constructeur du signal `actions_ha` par équipement.

Fonction pure — pas de dépendance sur http_server, topology, mqtt_bridge.
Le signal est consommé en lecture seule par le frontend (aucun recalcul JS).

`est_publie_ha` = présence effective d'une configuration MQTT Discovery retained
(active_or_alive dans le cache publications ou pending_discovery_unpublish).
"""

# Labels canoniques — fonctions pures testables en isolation.
_LABEL_PUBLIER_CREER = "Créer dans Home Assistant"
_LABEL_PUBLIER_REPUBLIER = "Republier dans Home Assistant"
_LABEL_SUPPRIMER = "Supprimer de Home Assistant"

# Raisons d'indisponibilité canoniques.
_RAISON_BRIDGE_INDISPONIBLE = "Le pont Home Assistant est indisponible (démon ou broker hors service)"
_RAISON_AUCUNE_ENTITE = "Aucune entité publiée dans Home Assistant"

# Niveaux de confirmation (cf. ux-delta-review §7.2).
CONFIRMATION_AUCUNE = "aucune"
CONFIRMATION_FORTE = "forte"


def label_publier(est_publie_ha: bool) -> str:
    """Retourne le label contextuel du bouton positif selon l'état de publication."""
    if est_publie_ha:
        return _LABEL_PUBLIER_REPUBLIER
    return _LABEL_PUBLIER_CREER


def build_actions_ha(
    *,
    est_publie_ha: bool,
    est_inclus: bool,
    bridge_disponible: bool,
) -> dict:
    """Construit le signal `actions_ha` pour un équipement donné.

    Matrice de disponibilité minimale (Story 5.1 — scope équipement) :
    - bridge indisponible → tout grisé avec raison infrastructure
    - est_publie_ha=False, inclus → publier actif, supprimer grisé
    - est_publie_ha=True, inclus → publier actif, supprimer actif
    - non inclus → pas de signal actions_ha (géré par l'appelant)

    Niveaux de confirmation (scope équipement uniquement) :
    - publier : "aucune" (pas de modale si scope explicite)
    - supprimer : "forte" (modale forte)

    Retourne un dict prêt à être sérialisé dans la réponse API.
    """
    # Bridge indisponible → tout grisé
    if not bridge_disponible:
        return {
            "publier": {
                "label": label_publier(est_publie_ha),
                "disponible": False,
                "raison_indisponibilite": _RAISON_BRIDGE_INDISPONIBLE,
                "niveau_confirmation": CONFIRMATION_AUCUNE,
            },
            "supprimer": {
                "label": _LABEL_SUPPRIMER,
                "disponible": False,
                "raison_indisponibilite": _RAISON_BRIDGE_INDISPONIBLE,
                "niveau_confirmation": CONFIRMATION_FORTE,
            },
        }

    # Matrice nominale (bridge disponible)
    publier_disponible = est_inclus
    supprimer_disponible = est_inclus and est_publie_ha

    supprimer_raison = None
    if not est_inclus:
        supprimer_raison = _RAISON_BRIDGE_INDISPONIBLE  # never reached if caller filters
    elif not est_publie_ha:
        supprimer_raison = _RAISON_AUCUNE_ENTITE

    publier_raison = None
    if not est_inclus:
        publier_raison = None  # caller should not generate signal for non-inclus

    return {
        "publier": {
            "label": label_publier(est_publie_ha),
            "disponible": publier_disponible,
            "raison_indisponibilite": publier_raison,
            "niveau_confirmation": CONFIRMATION_AUCUNE,
        },
        "supprimer": {
            "label": _LABEL_SUPPRIMER,
            "disponible": supprimer_disponible,
            "raison_indisponibilite": supprimer_raison,
            "niveau_confirmation": CONFIRMATION_FORTE,
        },
    }
