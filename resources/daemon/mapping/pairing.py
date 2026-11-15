"""pairing.py — appariement des ordres On / Off avec l'info d'état retenue (fix/switch-appariement-etat).

Un équipement peut porter plusieurs actions de même sens (par exemple deux ``ENERGY_ON`` : l'une
pilote le relais, l'autre change un mode). Le mapper ne doit jamais garder « la dernière vue ».

Règles (pas de devinette) :

- au plus une action par sens : comportement d'avant, inchangé (rétrocompatibilité), que l'action
  soit reliée à une info ou non ;
- plusieurs actions d'un même sens : pour chaque sens en double, on garde l'unique action reliée à
  l'info d'état retenue (zéro ou plusieurs reliées → ``ambiguous``) ; un sens qui n'a qu'une action
  la garde si elle est reliée à l'état, ou si elle n'est reliée à rien alors que l'autre sens a été
  retenu par son lien (une action unique reliée à une AUTRE info → ``ambiguous``) ;
- plusieurs infos d'état candidates (cas « plusieurs paires » seulement) : l'état retenu est celui
  que visent les actions reliées, s'il est unique (``choose_state``), sinon le dernier vu (avant).

Le lien d'une action vers une info se lit dans Jeedom, en lecture seule
(``JeedomCmd.linked_info_ids``) : champ « Valeur » du cœur (``linked_value``), configuration
``updateCmdId`` du cœur, configuration ``infoId`` du plugin virtual.

Dépendances : models.topology uniquement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from models.topology import JeedomCmd

# Raison de mapping dédiée (MappingResult.reason_code), libellée à l'écran (REASON_LABELS).
SWITCH_PAIRING_AMBIGUOUS = "switch_pairing_ambiguous"

PAIRING_SINGLE = "single"
PAIRING_LINKED = "linked"
PAIRING_AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class OnOffPairing:
    """Résultat de l'appariement : les ordres retenus (ou None) et comment ils l'ont été."""

    on: Optional[JeedomCmd]
    off: Optional[JeedomCmd]
    status: str
    # Ids des actions candidates par sens, pour le diagnostic (vide si un seul candidat par sens).
    candidates: Dict[str, List[int]] = field(default_factory=dict)


def _linked_to(cmd: JeedomCmd, state_id: int) -> bool:
    return state_id in cmd.linked_info_ids()


def pair_on_off(
    ons: List[JeedomCmd],
    offs: List[JeedomCmd],
    state: Optional[JeedomCmd],
    *,
    on_key: str = "ON",
    off_key: str = "OFF",
) -> OnOffPairing:
    """Choisit la paire On / Off reliée à ``state`` (voir les règles du module)."""
    if len(ons) <= 1 and len(offs) <= 1:
        return OnOffPairing(
            on=ons[-1] if ons else None,
            off=offs[-1] if offs else None,
            status=PAIRING_SINGLE,
        )

    candidates = {on_key: [int(c.id) for c in ons], off_key: [int(c.id) for c in offs]}
    if state is None:
        return OnOffPairing(on=None, off=None, status=PAIRING_AMBIGUOUS, candidates=candidates)

    state_id = int(state.id)
    chosen: Dict[str, Optional[JeedomCmd]] = {}
    by_link: Dict[str, bool] = {}
    for key, cmds in ((on_key, ons), (off_key, offs)):
        if not cmds:
            chosen[key] = None
            continue
        linked = [c for c in cmds if _linked_to(c, state_id)]
        if len(linked) == 1:
            chosen[key], by_link[key] = linked[0], True
            continue
        if len(cmds) == 1 and not cmds[0].linked_info_ids():
            chosen[key], by_link[key] = cmds[0], False  # sens unique, non relié : décidé ci-dessous
            continue
        return OnOffPairing(on=None, off=None, status=PAIRING_AMBIGUOUS, candidates=candidates)
    # Une action unique non reliée n'est gardée que si l'autre sens a été retenu par son lien.
    if by_link and not any(by_link.values()):
        return OnOffPairing(on=None, off=None, status=PAIRING_AMBIGUOUS, candidates=candidates)
    return OnOffPairing(
        on=chosen[on_key], off=chosen[off_key], status=PAIRING_LINKED, candidates=candidates
    )


def choose_state(states: List[JeedomCmd], ons: List[JeedomCmd], offs: List[JeedomCmd]) -> Optional[JeedomCmd]:
    """Info d'état retenue quand plusieurs paires On/Off existent.

    Plusieurs infos d'état candidates : celle que visent les actions reliées, si elle est unique ;
    sinon la dernière vue (comportement d'avant). Ainsi l'ordre des commandes dans Jeedom ne
    change pas le résultat dès que les actions sont reliées.
    """
    if not states:
        return None
    if len(states) == 1 or (len(ons) <= 1 and len(offs) <= 1):
        return states[-1]
    state_ids = {int(c.id) for c in states}
    targeted = set()
    for cmd in [*ons, *offs]:
        targeted |= set(cmd.linked_info_ids()) & state_ids
    if len(targeted) == 1:
        target = next(iter(targeted))
        return next(c for c in states if int(c.id) == target)
    return states[-1]
