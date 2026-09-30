"""Story 19.6 (AC1bis) — plafond du lissage d'une action HA (publier/supprimer).

Module pur, sans dépendance asyncio/aiohttp : les fonctions ci-dessous ne font
que du calcul, pour rester testables sans faux MQTT ni faux serveur HTTP.
"""

from __future__ import annotations

# Plafond du total des pauses de lissage d'une action (AC1bis).
P_MAX_S: float = 15.0

# Marge couvrant le retard de réveil d'`asyncio.sleep` sur une boucle chargée (AC1bis).
MARGE_REVEIL_S: float = 1.0


def plafond_pauses(deadline_s: float) -> float:
    """Retourne le plafond du total des pauses de lissage pour `deadline_s`."""
    return min(P_MAX_S, deadline_s / 2)


def budget_travail(deadline_s: float) -> float:
    """Retourne le budget de travail pur restant une fois le plafond et la marge retirés."""
    return deadline_s - plafond_pauses(deadline_s) - MARGE_REVEIL_S


def prochaine_pause(
    action_delay: float,
    plafond: float,
    pauses_faites: float,
    pauses_restantes: int,
) -> float:
    """Retourne la durée de la prochaine pause de lissage.

    `pauses_restantes` compte la pause courante et doit être >= 1 : c'est
    l'appelant qui décide qu'une pause a lieu (dernière itération exclue).
    """
    if pauses_restantes < 1:
        raise ValueError("pauses_restantes doit être >= 1")
    return min(action_delay, max(0.0, (plafond - pauses_faites) / pauses_restantes))
