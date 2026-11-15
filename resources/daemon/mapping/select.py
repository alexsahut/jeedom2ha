"""select.py — Mode d'un équipement publié en HA ``select`` (story/select-mode).

Motif Jeedom : une info texte dont la valeur est posée par au moins deux actions, chacune écrivant
une valeur constante différente (par exemple un chauffe-eau virtuel : « Manu » écrit ``manu``,
« auto » écrit ``auto``, « Absence » écrit ``Absence`` dans l'info « etat »).

Trois sources, par ordre de confiance (une info n'est reconnue que par la première qui la voit) :

1. types génériques standard Jeedom (``core/config/jeedom.config.php``, famille « Mode ») : info
   ``MODE_STATE`` et actions ``MODE_SET_STATE`` — ou les mêmes rôles posés à la main par
   « Corriger le type » (« Mode (état) » / « Mode (commande) », ``TopologySnapshot.mode_roles``,
   jamais écrits dans Jeedom). L'option d'une action est la valeur qu'elle écrit dans l'info si
   Jeedom la donne, sinon son nom (convention du type générique « Mode », lue aussi par Homebridge) ;
2. action Jeedom de sous-type ``select`` avec sa liste ``listValue`` (``valeur|libellé;…``), reliée
   à une info : les options sont les valeurs de la liste ;
3. actions reliées à l'info par ``updateCmdId`` / ``updateCmdToValue`` (cœur) ou ``infoId`` /
   ``value`` (plugin virtual), chacune écrivant une constante.

Règles (pas de devinette) :
- options = valeurs exactes écrites (casse et espaces gardés), au moins deux, toutes différentes ;
  deux actions écrivant la même valeur, ou une valeur non constante (expression, ``#…#``) : pas
  de select pour cette info ;
- le select est une entité SECONDAIRE de l'équipement : il s'ajoute aux entités existantes, n'en
  remplace aucune et ne change aucun de leurs topics (``MapperRegistry.map_all``) ;
- le select n'est publié que si NI son info NI aucune de ses actions n'est déjà portée par une entité
  de l'équipement (``MapperRegistry.map_all`` : une info déjà publiée en capteur, un ordre de volet,
  de lumière, de serrure… restent à leur entité, sans select en double) ;
- familles sensibles exclues, comme pour les boutons (serrure, alarme, sirène, portail, vanne,
  arrosage) et commandes d'actionneurs (volet, lumière, chauffage, thermostat) ;
- identité dans un espace de noms propre, sans collision possible avec un capteur par commande :
  ``jeedom2ha_eq_<eq>_select_<info>``, topics ``jeedom2ha/<eq>/select_<info>/state|set``.

Dépendances : models uniquement.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from models.mapping import MappingResult, SelectCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

_LOGGER = logging.getLogger(__name__)

MODE_STATE = "MODE_STATE"
MODE_SET_STATE = "MODE_SET_STATE"

ROLE_STATE = "state"
ROLE_COMMAND = "command"

SOURCE_GENERIC = "generic_mode"
SOURCE_ACTION_SELECT = "action_select"
SOURCE_LINKED = "linked_actions"

# Les trois sources reposent sur un lien explicite de Jeedom (type générique, liste, info mise à jour)
# et sur des valeurs constantes : « sure ». L’ordre des sources ne sert qu’à la priorité.
# Familles jamais publiées en select (gardes des boutons, story 24.12, et ordres d'actionneurs).
SENSITIVE_GENERIC_TYPE_PREFIXES = (
    "GB_", "LOCK_", "ALARM_", "SIREN_", "IRRIG_", "FAUCET_", "VALVE_", "BARRIER_", "GARAGE_",
    "FLAP_", "LIGHT_", "THERMOSTAT_", "HEATING_",
)

_CONFIDENCE_BY_SOURCE = {SOURCE_GENERIC: "sure", SOURCE_ACTION_SELECT: "sure", SOURCE_LINKED: "sure"}

# Valeur du plugin virtual : évaluée par ``jeedom::evaluateExpression`` ; seule une constante
# simple (mot, nombre) est sûre. Tout opérateur, guillemet, parenthèse ou tag la rend non constante.
_VIRTUAL_FORBIDDEN = set("#\"'()+-*/%<>=!&|?:$[]{}\\;")
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def is_sensitive(cmd: JeedomCmd) -> bool:
    return bool(cmd.generic_type) and str(cmd.generic_type).startswith(SENSITIVE_GENERIC_TYPE_PREFIXES)


def normalize_option_value(value: str) -> str:
    """Valeur comparée d'une liste : un nombre entier écrit « 2.0 » vaut « 2 » ; le reste tel quel."""
    text = str(value).strip()
    if _NUMBER_RE.fullmatch(text):
        try:
            number = float(text.replace(",", "."))
        except ValueError:
            return str(value)
        if number.is_integer():
            return str(int(number))
        return repr(number)
    return str(value)


def _kind(cmd: JeedomCmd) -> Tuple[str, str]:
    return (cmd.type or "").lower(), (cmd.sub_type or "").lower()


def _is_info_text(cmd: JeedomCmd) -> bool:
    return _kind(cmd) == ("info", "string")


def _is_order(cmd: JeedomCmd) -> bool:
    return _kind(cmd) == ("action", "other")


def _is_select_action(cmd: JeedomCmd) -> bool:
    return _kind(cmd) == ("action", "select")


def role_of(cmd: JeedomCmd, snapshot: TopologySnapshot) -> Optional[str]:
    """Rôle « Mode » d'une commande : type générique Jeedom, sinon réglage « Corriger le type »."""
    forced = (getattr(snapshot, "mode_roles", None) or {}).get(int(cmd.id))
    if forced in (ROLE_STATE, ROLE_COMMAND):
        return forced
    if cmd.generic_type == MODE_STATE:
        return ROLE_STATE
    if cmd.generic_type == MODE_SET_STATE:
        return ROLE_COMMAND
    return None


def _core_constant(value: Optional[str]) -> Optional[str]:
    """``updateCmdToValue`` du cœur : écrit tel quel, sauf les tags ``#slider#``…"""
    if value is None or "#" in value or not value.strip():
        return None
    return value


def _virtual_constant(value: Optional[str]) -> Optional[str]:
    """``value`` du plugin virtual : une constante simple seulement (jamais une expression)."""
    if value is None or not value.strip():
        return None
    if _NUMBER_RE.fullmatch(value.strip()):
        return value
    if set(value) & _VIRTUAL_FORBIDDEN:
        return None
    return value


def written_value(action: JeedomCmd, info_id: int) -> Optional[str]:
    """Valeur constante qu'une action écrit dans l'info ``info_id``, sinon None (jamais devinée)."""
    if action.update_cmd_id == info_id:
        value = _core_constant(action.update_cmd_to_value)
        if value is not None:
            return value
    if action.virtual_info_id == info_id:
        value = _virtual_constant(action.virtual_value)
        if value is not None:
            return value
    return None


def parse_list_value(raw: Optional[str]) -> List[Tuple[str, str]]:
    """``listValue`` du cœur (``valeur|libellé;valeur;…``) → [(valeur, libellé)] ; vide si illisible."""
    if raw is None or not str(raw).strip():
        return []
    out: List[Tuple[str, str]] = []
    for element in str(raw).split(";"):
        if element == "":
            continue
        value, _sep, label = element.partition("|")
        if value == "":
            return []
        out.append((value, label if label else value))
    return out


def _has_manual_role(snapshot: TopologySnapshot, info: JeedomCmd, options) -> bool:
    """Un rôle « Mode » posé à la main (« Corriger le type ») sur l'info ou une de ses actions.

    La voie manuelle se fait commande par commande : un mode réglé à la main est publié dès sa
    première action (une seule option), pour que chaque étape ait un aperçu publiable.
    """
    roles = getattr(snapshot, "mode_roles", None) or {}
    return int(info.id) in roles or any(int(o.action.id) in roles for o in options)


def _linked_by_core_value_only(action: JeedomCmd, info_id: int) -> bool:
    """Action reliée à l'info par la seule « Valeur » du cœur (aucun updateCmdId / infoId vers elle)."""
    return (
        action.linked_value == info_id
        and action.update_cmd_id != info_id
        and action.virtual_info_id != info_id
    )


def _warn_not_constant(eq: JeedomEqLogic, info: JeedomCmd, action: JeedomCmd) -> None:
    _LOGGER.warning(
        "[MAPPING] eq_id=%d: action %s reliée à l'info %s sans valeur constante → pas une option",
        eq.id, action.id, info.id,
    )


class _Option:
    __slots__ = ("value", "action", "select_value")

    def __init__(self, value: str, action: JeedomCmd, select_value: Optional[str] = None) -> None:
        self.value = value
        self.action = action
        self.select_value = select_value


class SelectMapper:
    """Reconnaît les modes d'un équipement et les publie en ``select`` secondaires."""

    def map_all(
        self,
        eq: JeedomEqLogic,
        snapshot: TopologySnapshot,
        carried_cmd_ids: Optional[set] = None,
        taken_unique_ids: Optional[set] = None,
    ) -> List[MappingResult]:
        """Selects de l'équipement. ``carried_cmd_ids`` : commandes déjà portées par une entité de la
        projection (aucun select n'en reprend une) ; ``taken_unique_ids`` : identifiants déjà pris."""
        carried = set(carried_cmd_ids or ())
        taken_ids = set(taken_unique_ids or ())
        # Exclues : commandes déjà portées par une entité, familles sensibles. Un select dont l'info OU
        # UNE SEULE de ses actions est exclue n'est pas publié du tout (jamais un select partiel).
        excluded = carried | {int(c.id) for c in eq.cmds if is_sensitive(c)}
        infos = {int(c.id): c for c in eq.cmds if (c.type or "").lower() == "info"}
        taken_infos: set = set()
        taken_actions: set = set()
        results: List[MappingResult] = []
        for source, finder in (
            (SOURCE_GENERIC, self._generic),
            (SOURCE_ACTION_SELECT, self._action_select),
            (SOURCE_LINKED, self._linked),
        ):
            for info, options, labels in finder(eq, snapshot, infos, taken_infos, taken_actions):
                touched = {int(info.id)} | {int(o.action.id) for o in options}
                if touched & excluded:
                    _LOGGER.info(
                        "[MAPPING] eq_id=%d: info %s, commandes %s déjà portées par une entité ou sensibles "
                        "→ pas de select", eq.id, info.id, sorted(touched & excluded),
                    )
                    continue
                if any(int(o.action.id) in taken_actions for o in options):
                    continue
                manual = _has_manual_role(snapshot, info, options)
                result = self._result(eq, snapshot, info, options, labels, source, min_options=1 if manual else 2)
                if result is None:
                    continue
                if result.ha_unique_id in taken_ids:
                    _LOGGER.warning("[MAPPING] eq_id=%d: identifiant %s déjà pris → pas de select",
                                    eq.id, result.ha_unique_id)
                    continue
                taken_infos.add(int(info.id))
                taken_actions.update(int(o.action.id) for o in options)
                results.append(result)
        return results

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        results = self.map_all(eq, snapshot)
        return results[0] if results else None

    # --- Sources -------------------------------------------------------------------------------

    @staticmethod
    def _generic(eq, snapshot, infos, taken_infos, taken_actions):
        states = [c for c in eq.cmds if role_of(c, snapshot) == ROLE_STATE and int(c.id) in infos]
        orders = [c for c in eq.cmds if role_of(c, snapshot) == ROLE_COMMAND and _is_order(c)
                  and int(c.id) not in taken_actions]
        for state in states:
            state_id = int(state.id)
            linked = [a for a in orders if state_id in a.linked_info_ids()]
            options: List[_Option] = []
            if linked:
                # Au moins une action reliée à ce mode : seules les actions reliées comptent (une
                # action « Rejouer » ou « Mode suivant » non reliée n'est jamais une option).
                for action in linked:
                    value = written_value(action, state_id)
                    if value is None and _is_info_text(state) and _linked_by_core_value_only(action, state_id):
                        # Couple standard MODE_STATE / MODE_SET_STATE relié par la « Valeur » du cœur,
                        # sans valeur écrite connue : c'est le plugin qui écrit le NOM de l'action dans
                        # l'info (convention suivie par Homebridge). L'option est ce nom.
                        options.append(_Option(action.name, action))
                        continue
                    if value is None:
                        _warn_not_constant(eq, state, action)
                        continue
                    options.append(_Option(value, action))
            elif len(states) == 1 and not any(state_id in a.linked_info_ids() for a in eq.cmds):
                # Aucune action reliée : convention du type générique « Mode », l'option est le nom.
                # Si une action quelconque de l'équipement est reliée à ce mode (prise par une autre
                # entité, ou typée autrement), les actions non reliées restantes (« Rejouer »,
                # « Retour », « Suivant ») ne sont pas des modes : pas de repli sur leurs noms.
                options = [_Option(a.name, a) for a in orders if not a.linked_info_ids()]
            yield state, options, {}

    @staticmethod
    def _action_select(eq, snapshot, infos, taken_infos, taken_actions):
        by_info: Dict[int, List[JeedomCmd]] = {}
        for action in eq.cmds:
            if not _is_select_action(action) or int(action.id) in taken_actions:
                continue
            linked = [i for i in action.linked_info_ids() if i in infos]
            if len(linked) == 1 and linked[0] not in taken_infos:
                by_info.setdefault(linked[0], []).append(action)
        for info_id, actions in by_info.items():
            if len(actions) != 1:
                _LOGGER.warning(
                    "[MAPPING] eq_id=%d: plusieurs actions « liste » pour l'info %d → pas de select",
                    eq.id, info_id,
                )
                continue
            action = actions[0]
            pairs = parse_list_value(getattr(action, "list_value", None))
            # Options = libellés (ce que l'utilisateur lit) ; l'ordre envoie la valeur, l'état
            # (une valeur, normalisée « 2.0 » → « 2 ») est ramené à son libellé.
            options = [_Option(label, action, select_value=value) for value, label in pairs]
            value_to_option = {normalize_option_value(value): label for value, label in pairs}
            yield infos[info_id], options, value_to_option

    @staticmethod
    def _linked(eq, snapshot, infos, taken_infos, taken_actions):
        for info in eq.cmds:
            info_id = int(info.id)
            if not _is_info_text(info) or info_id in taken_infos:
                continue
            options = []
            for action in eq.cmds:
                if not _is_order(action) or int(action.id) in taken_actions:
                    continue
                if not ({action.update_cmd_id, action.virtual_info_id} & {info_id}):
                    continue
                value = written_value(action, info_id)
                if value is None:
                    _warn_not_constant(eq, info, action)
                    continue
                options.append(_Option(value, action))
            if options:
                yield info, options, {}

    # --- Résultat ------------------------------------------------------------------------------

    @staticmethod
    def _result(eq, snapshot, info, options: List[_Option], value_to_option, source,
                min_options=2) -> Optional[MappingResult]:
        values = [o.value for o in options]
        if len(values) < min_options or not values:
            if values:
                _LOGGER.info(
                    "[MAPPING] eq_id=%d: info %s, une seule valeur écrite (%s) → pas de select",
                    eq.id, info.id, source,
                )
            return None
        if len(set(values)) != len(values):
            _LOGGER.warning(
                "[MAPPING] eq_id=%d: info %s, plusieurs actions écrivent la même valeur %s → pas de select",
                eq.id, info.id, sorted(values),
            )
            return None
        info_id = int(info.id)
        commands: Dict[str, JeedomCmd] = {MODE_STATE: info}
        for option in options:
            commands[f"{MODE_SET_STATE}#{option.action.id}"] = option.action
        option_commands = {
            o.value: {"cmd_id": int(o.action.id), "select": o.select_value} for o in options
        }
        _LOGGER.info(
            "[MAPPING] eq_id=%d: select sur l'info %d (%s), options %s",
            eq.id, info_id, source, values,
        )
        return MappingResult(
            ha_entity_type="select",
            confidence=_CONFIDENCE_BY_SOURCE[source],
            reason_code=f"select_{source}",
            jeedom_eq_id=eq.id,
            ha_unique_id=f"jeedom2ha_eq_{eq.id}_select_{info_id}",
            ha_name=info.name,
            suggested_area=snapshot.get_suggested_area(eq.id),
            commands=commands,
            capabilities=SelectCapabilities(
                has_state=True, has_command=True, has_options=True, options=list(values),
            ),
            reason_details={
                "cmd_id": info_id,
                "object_id": f"jeedom2ha_{eq.id}_select_{info_id}",
                "node_id": f"jeedom2ha_{eq.id}_select_{info_id}",
                "state_topic": f"jeedom2ha/{eq.id}/select_{info_id}/state",
                "command_topic": f"jeedom2ha/{eq.id}/select_{info_id}/set",
                "options": list(values),
                "option_commands": option_commands,
                "value_to_option": dict(value_to_option),
                "select_source": source,
            },
        )
