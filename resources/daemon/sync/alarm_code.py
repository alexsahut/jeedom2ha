"""FR49 (CC-64) — code de désarmement de l'alarme, en mémoire du démon uniquement.

Le code est saisi par l'utilisateur dans la configuration du plugin (champ mot de passe, chiffré
par Jeedom). Il arrive au démon dans le corps HTTP local de ``/action/mqtt_connect`` (protégé par
le secret local), comme le mot de passe du broker : jamais en ligne de commande (visible par
``ps``), jamais dans un journal, un topic retenu, la discovery ni sur disque.

La discovery n'en publie que la présence (``code: REMOTE_CODE``) ; la vérification se fait ici,
en temps constant (``hmac.compare_digest``).
"""

from __future__ import annotations

import hmac
import logging
import time
from typing import Any, Callable, Dict, Optional

_LOGGER = logging.getLogger(__name__)

# Revue Codex de 12.4 — limite d'essais du code de désarmement (par équipement).
ALARM_CODE_MAX_FAILURES = 5
ALARM_CODE_LOCKOUT_SECONDS = 300.0


class _AlarmCodeVault:
    """Détenteur unique du code ; ne le rend jamais, ne sait que le comparer."""

    __slots__ = ("_code", "_unreadable")

    def __init__(self) -> None:
        self._code: Optional[bytes] = None
        # Revue de 12.4 — un code est enregistré dans Jeedom mais n'a pas pu être déchiffré :
        # le désarmement reste exigé (discovery) et tout DISARM est refusé (jamais « sans code »).
        self._unreadable = False

    def set(self, code: Any, unreadable: bool = False) -> None:
        """Pose le code (texte non vide), sinon l'efface : sans code, comportement sans code.

        ``unreadable`` : un code est configuré côté Jeedom mais illisible ; il l'emporte sur
        ``code`` (aucun code n'est alors gardé, aucun désarmement n'est possible).
        """
        if unreadable:
            self._code = None
            self._unreadable = True
        elif isinstance(code, str) and code.strip() != "":
            self._code = code.encode("utf-8")
            self._unreadable = False
        else:
            self._code = None
            self._unreadable = False

    def clear(self) -> None:
        self._code = None
        self._unreadable = False

    def is_configured(self) -> bool:
        """Un code est exigé pour désarmer (lisible ou non)."""
        return self._code is not None or self._unreadable

    def is_unreadable(self) -> bool:
        return self._unreadable

    def matches(self, candidate: Any) -> bool:
        """Vrai seulement si un code lisible est configuré et que ``candidate`` lui est égal."""
        if self._code is None or not isinstance(candidate, str) or candidate == "":
            return False
        return hmac.compare_digest(candidate.encode("utf-8"), self._code)

    def __repr__(self) -> str:  # jamais le code, même par mégarde dans un journal
        return f"<AlarmCodeVault configured={self.is_configured()} unreadable={self._unreadable}>"

    __str__ = __repr__


class AlarmDisarmLockout:
    """Limite d'essais du code de désarmement, par équipement (horloge injectable).

    Après ``max_failures`` codes faux pour un même équipement, tout DISARM de cet équipement
    est refusé pendant ``lock_seconds``. Le compteur revient à zéro au premier code bon ou à
    l'expiration du verrou. Rien ici ne voit ni ne journalise le code.
    """

    def __init__(
        self,
        max_failures: int = ALARM_CODE_MAX_FAILURES,
        lock_seconds: float = ALARM_CODE_LOCKOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_failures = max_failures
        self.lock_seconds = lock_seconds
        self.clock = clock
        self._failures: Dict[Any, int] = {}
        self._locked_until: Dict[Any, float] = {}

    def is_locked(self, eq_id: Any) -> bool:
        until = self._locked_until.get(eq_id)
        if until is None:
            return False
        if self.clock() >= until:
            # Expiration : verrou levé et compteur remis à zéro.
            self._locked_until.pop(eq_id, None)
            self._failures.pop(eq_id, None)
            return False
        return True

    def record_failure(self, eq_id: Any) -> bool:
        """Compte un code faux ; vrai si ce code faux déclenche le verrou."""
        count = self._failures.get(eq_id, 0) + 1
        self._failures[eq_id] = count
        if count >= self.max_failures:
            self._locked_until[eq_id] = self.clock() + self.lock_seconds
            _LOGGER.warning(
                "[ALARM] eq_id=%s : %d codes de désarmement faux, désarmement verrouillé %d s",
                eq_id, count, int(self.lock_seconds),
            )
            return True
        return False

    def record_success(self, eq_id: Any) -> None:
        self._failures.pop(eq_id, None)
        self._locked_until.pop(eq_id, None)

    def reset(self) -> None:
        self._failures.clear()
        self._locked_until.clear()


ALARM_CODE = _AlarmCodeVault()
ALARM_LOCKOUT = AlarmDisarmLockout()


def set_alarm_code(code: Any, unreadable: bool = False) -> None:
    """Pose (ou retire) le code ; un nouveau code remet aussi la limite d'essais à zéro."""
    ALARM_CODE.set(code, unreadable=unreadable)
    ALARM_LOCKOUT.reset()


def alarm_code_configured() -> bool:
    return ALARM_CODE.is_configured()


def alarm_code_unreadable() -> bool:
    return ALARM_CODE.is_unreadable()


def alarm_code_matches(candidate: Any) -> bool:
    return ALARM_CODE.matches(candidate)
