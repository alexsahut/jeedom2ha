"""pairing.py — appariement des ordres On / Off avec l'info d'état retenue (fix/switch-appariement-etat).

Un équipement peut porter plusieurs actions de même sens (par exemple deux ``ENERGY_ON`` : l'une
pilote le relais, l'autre change un mode). Le mapper ne doit jamais garder « la dernière vue ».

Règles (pas de devinette) :

- au plus une action par sens : comportement d'avant, inchangé (rétrocompatibilité), que l'action
  soit reliée à une info ou non ;
- plusieurs actions d'un même sens : pour chaque sens présent, on garde l'unique action reliée à
  l'info d'état retenue ; zéro ou plusieurs actions reliées dans un sens → ``ambiguous``.

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
    for key, cmds in ((on_key, ons), (off_key, offs)):
        if not cmds:
            chosen[key] = None
            continue
        linked = [c for c in cmds if _linked_to(c, state_id)]
        if len(linked) != 1:
            return OnOffPairing(on=None, off=None, status=PAIRING_AMBIGUOUS, candidates=candidates)
        chosen[key] = linked[0]
    return OnOffPairing(
        on=chosen[on_key], off=chosen[off_key], status=PAIRING_LINKED, candidates=candidates
    )
