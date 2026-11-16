"""barrier_state_sensor.py — capteur compagnon de l'état d'une barrière (story/barrier-state-sensor).

Une porte de garage ou un portail publié en ``cover`` par la story 24.7 reçoit les 5 états de la
convention barrière (0 / 252 / 253 / 254 / 255 → ``closed`` / ``closing`` / ``stopped`` /
``opening`` / ``open``). Home Assistant n'a pas d'état « arrêté » pour une cover : il l'affiche
ouverte ou fermée, et l'état ``stopped`` est perdu à l'écran.

Le compagnon est un ``sensor`` ``device_class: enum`` en LECTURE SEULE, rattaché au même appareil
que la cover, nommé « État », qui affiche les 5 états avec les mêmes clés et la même table de
traduction que la cover (``BARRIER_STATE_TABLE`` / ``barrier_state`` de ``sync/readback.py``) ;
une valeur hors convention ne publie rien.

EXCEPTION ASSUMÉE à la règle « une commande = une entité » : l'info d'état (``BARRIER_STATE`` /
``GARAGE_STATE`` numérique) est portée à la fois par la cover et par ce capteur. L'exception est
limitée à ce cas : une cover barrière publiée (``barrier_mode`` non nul). Le compagnon suit sa
cover : jamais d'override de type propre, et il n'est publié que si la cover l'est en barrière
(voir ``models/evaluate_equipment.py``).

Identité dans un espace de noms propre, sur la convention des secondaires « par commande »
(``jeedom2ha_eq_<eq>_cmd_<cmd>``) suivie d'un suffixe que rien d'autre ne produit :
- unique_id ``jeedom2ha_eq_<eq>_cmd_<cmd>_barrier_state`` ;
- object_id / node_id ``jeedom2ha_<eq>_<cmd>_barrier_state`` ;
- state_topic ``jeedom2ha/<eq>/<cmd>/barrier_state`` (aucune commande : pas de command_topic).
"""

from typing import Any, Optional

from models.mapping import MappingResult, SensorCapabilities
from sync.readback import BARRIER_STATE_TABLE, barrier_mode

BARRIER_STATE_SENSOR_NAME = "État"
BARRIER_STATE_SENSOR_SUFFIX = "barrier_state"
# Mêmes clés que la cover, dans l'ordre des valeurs de la convention barrière.
BARRIER_STATE_OPTIONS = list(BARRIER_STATE_TABLE.values())


def is_barrier_state_sensor(mapping: Any) -> bool:
    """True pour le capteur compagnon d'une cover barrière (et pour lui seul)."""
    if getattr(mapping, "ha_entity_type", None) != "sensor":
        return False
    return bool((getattr(mapping, "reason_details", None) or {}).get("barrier_companion_of"))


def barrier_state_companion(cover: MappingResult, snapshot: Any) -> Optional[MappingResult]:
    """Le capteur « État » d'une cover barrière, ou None pour toute autre entité."""
    if barrier_mode(cover) is None:
        return None
    details = cover.reason_details or {}
    state_cmd = (cover.commands or {}).get(details.get("barrier_state"))
    if state_cmd is None:
        return None
    eq_id = cover.jeedom_eq_id
    cmd_id = int(state_cmd.id)
    node_id = f"jeedom2ha_{eq_id}_{cmd_id}_{BARRIER_STATE_SENSOR_SUFFIX}"
    return MappingResult(
        ha_entity_type="sensor",
        confidence=cover.confidence,
        reason_code="sensor_barrier_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}_cmd_{cmd_id}_{BARRIER_STATE_SENSOR_SUFFIX}",
        ha_name=BARRIER_STATE_SENSOR_NAME,
        suggested_area=cover.suggested_area,
        commands={details["barrier_state"]: state_cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={
            "cmd_id": cmd_id,
            "object_id": node_id,
            "node_id": node_id,
            "state_topic": f"jeedom2ha/{eq_id}/{cmd_id}/{BARRIER_STATE_SENSOR_SUFFIX}",
            "device_class": "enum",
            "options": list(BARRIER_STATE_OPTIONS),
            "barrier_companion_of": cover.ha_unique_id,
        },
    )
