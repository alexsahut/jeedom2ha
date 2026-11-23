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
from typing import Any, Optional


class _AlarmCodeVault:
    """Détenteur unique du code ; ne le rend jamais, ne sait que le comparer."""

    __slots__ = ("_code",)

    def __init__(self) -> None:
        self._code: Optional[bytes] = None

    def set(self, code: Any) -> None:
        """Pose le code (texte non vide), sinon l'efface : sans code, comportement sans code."""
        if isinstance(code, str) and code.strip() != "":
            self._code = code.encode("utf-8")
        else:
            self._code = None

    def clear(self) -> None:
        self._code = None

    def is_configured(self) -> bool:
        return self._code is not None

    def matches(self, candidate: Any) -> bool:
        """Vrai seulement si un code est configuré et que ``candidate`` lui est égal."""
        if self._code is None or not isinstance(candidate, str) or candidate == "":
            return False
        return hmac.compare_digest(candidate.encode("utf-8"), self._code)

    def __repr__(self) -> str:  # jamais le code, même par mégarde dans un journal
        return f"<AlarmCodeVault configured={self.is_configured()}>"

    __str__ = __repr__


ALARM_CODE = _AlarmCodeVault()


def set_alarm_code(code: Any) -> None:
    ALARM_CODE.set(code)


def alarm_code_configured() -> bool:
    return ALARM_CODE.is_configured()


def alarm_code_matches(candidate: Any) -> bool:
    return ALARM_CODE.matches(candidate)
