"""system_health.py — appareil « Santé de Jeedom », hors du circuit des équipements (story/system-health).

Le relevé vient du cron du plugin (``core/php/jeedom2ha_system_health.php``) par ``POST /action/system_health``,
seulement si la case « Publier la santé de Jeedom » est cochée (désactivée par défaut) et seulement quand son
empreinte change. Ce module est PUR : il transforme le relevé en entités Home Assistant, sans MQTT ni état.

Toutes les entités sont en LECTURE SEULE (aucun ``command_topic``) et en ``entity_category: diagnostic``, sur un
seul appareil « Santé de Jeedom » rattaché au pont :
- un ``binary_sensor`` ``running`` par plugin actif à démon propre (nom = nom du plugin) ;
- ``sensor`` « Démons en service » et « Démons arrêtés » : agrégats exacts des ``binary_sensor`` ci-dessus (même
  périmètre, même relevé ; un démon à l'état illisible compte comme arrêté) ;
- ``sensor`` nombre de mises à jour disponibles ;
- ``sensor`` nombre de messages du centre de messages (le nombre seulement, jamais leur texte) ;
- ``sensor`` version du cœur.

Espace de noms propre, sans collision possible avec les autres entités du plugin (équipements
``jeedom2ha_eq_<id>`` / ``jeedom2ha_<id>…``, scénarios ``jeedom2ha_scenario_<id>``, pont ``jeedom2ha_bridge…`` ;
leurs topics ``jeedom2ha/<id>/…``, ``jeedom2ha/scenario_<id>/…``, ``jeedom2ha/bridge/…``) :
- unique_id / object_id ``jeedom2ha_system_<clé>`` (clé ``daemon_<plugin>``, ``daemons_running``,
  ``daemons_stopped``, ``updates``, ``messages``, ``core_version``) ; ``daemon_`` suivi de l'identifiant ne peut
  jamais donner ``daemons_…`` ;
- topic d'état ``jeedom2ha/system/<clé>/state`` ;
- appareil ``jeedom2ha_system``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from models.availability import BRIDGE_AVAILABILITY_TOPIC

SYSTEM_DEVICE_ID = "jeedom2ha_system"
SYSTEM_DEVICE_NAME = "Santé de Jeedom"
SYSTEM_UNIQUE_ID_PREFIX = "jeedom2ha_system_"
SYSTEM_TOPIC_ROOT = "jeedom2ha/system"
SYSTEM_COMPONENTS = ("binary_sensor", "sensor")
BRIDGE_DEVICE_ID = "jeedom2ha_bridge"  # même valeur que discovery.publisher.BRIDGE_DEVICE_ID (via_device)
_SW_VERSION = "0.2.0"  # même valeur que discovery.publisher._SW_VERSION

# Une clé n'a que des minuscules, chiffres et « _ » : topic MQTT et identifiant sûrs.
SYSTEM_KEY_RE = re.compile(r"[a-z0-9_]{1,80}")
_PLUGIN_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
_MAX_NAME = 100
_MAX_VERSION = 64

DAEMONS_RUNNING_KEY = "daemons_running"
DAEMONS_STOPPED_KEY = "daemons_stopped"
UPDATES_KEY = "updates"
MESSAGES_KEY = "messages"
CORE_VERSION_KEY = "core_version"
DAEMON_KEY_PREFIX = "daemon_"


@dataclass(frozen=True)
class SystemHealthEntity:
    """Une entité de l'appareil « Santé de Jeedom » (fonction pure de son relevé)."""

    component: str          # binary_sensor | sensor
    key: str                # daemon_<plugin> | updates | messages | core_version
    name: str
    state: Optional[str]    # charge publiée sur le topic d'état ; None = rien à publier (valeur illisible)
    device_class: Optional[str] = None
    state_class: Optional[str] = None

    @property
    def unique_id(self) -> str:
        return f"{SYSTEM_UNIQUE_ID_PREFIX}{self.key}"

    @property
    def state_topic(self) -> str:
        return f"{SYSTEM_TOPIC_ROOT}/{self.key}/state"

    def config_topic(self, prefix: str = "homeassistant") -> str:
        return f"{prefix}/{self.component}/{self.unique_id}/config"


def daemon_key(plugin_id: Any) -> Optional[str]:
    """Clé d'un plugin : ``daemon_`` + identifiant en minuscules (``-`` -> ``_``) ; None si l'identifiant est invalide."""
    text = str(plugin_id or "").strip()
    if not _PLUGIN_ID_RE.fullmatch(text):
        return None
    key = DAEMON_KEY_PREFIX + text.lower().replace("-", "_")
    return key if SYSTEM_KEY_RE.fullmatch(key) else None


def _count(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,9}", value.strip()):
        return int(value.strip())
    return None


def _text(value: Any, limit: int) -> Optional[str]:
    if value is None or isinstance(value, (dict, list, bool)):
        return None
    text = " ".join(str(value).split())
    return text[:limit] if text else None


def map_system_health(snapshot: Any) -> List[SystemHealthEntity]:
    """Relevé -> entités, dans un ordre stable (démons triés par clé, puis les cinq capteurs).

    Un démon à l'identifiant invalide ou en double (même clé) est ignoré. Les cinq capteurs sont toujours déclarés ;
    une valeur illisible ne publie pas d'état (``state`` None), jamais une valeur inventée.
    """
    data = snapshot if isinstance(snapshot, dict) else {}
    daemons: Dict[str, SystemHealthEntity] = {}
    for row in data.get("daemons") or []:
        if not isinstance(row, dict):
            continue
        key = daemon_key(row.get("id"))
        if key is None or key in daemons:
            continue
        name = _text(row.get("name"), _MAX_NAME) or str(row.get("id"))
        daemons[key] = SystemHealthEntity(
            component="binary_sensor", key=key, name=name,
            state="ON" if row.get("running") is True else "OFF", device_class="running",
        )
    updates = _count(data.get("updates"))
    messages = _count(data.get("messages"))
    version = _text(data.get("core_version"), _MAX_VERSION)
    # Agrégats « démons en service X/Y » : MÊME périmètre et MÊME relevé que les binary_sensor ci-dessus (un démon
    # illisible y est déjà « OFF », il compte donc comme arrêté) ; aucun démon : 0 et 0, publiés quand même.
    running = sum(1 for e in daemons.values() if e.state == "ON")
    stopped = len(daemons) - running
    return [
        *(daemons[k] for k in sorted(daemons)),
        SystemHealthEntity("sensor", DAEMONS_RUNNING_KEY, "Démons en service", str(running),
                           state_class="measurement"),
        SystemHealthEntity("sensor", DAEMONS_STOPPED_KEY, "Démons arrêtés", str(stopped),
                           state_class="measurement"),
        SystemHealthEntity("sensor", UPDATES_KEY, "Mises à jour disponibles",
                           None if updates is None else str(updates)),
        SystemHealthEntity("sensor", MESSAGES_KEY, "Messages", None if messages is None else str(messages)),
        SystemHealthEntity("sensor", CORE_VERSION_KEY, "Version du cœur", version),
    ]


def build_system_health_payload(entity: SystemHealthEntity) -> Dict[str, Any]:
    """Charge de découverte (fonction pure) : lecture seule, diagnostic, disponibilité du pont."""
    payload: Dict[str, Any] = {
        "name": entity.name,
        "unique_id": entity.unique_id,
        "object_id": entity.unique_id,
        "default_entity_id": f"{entity.component}.{entity.unique_id}",
        "state_topic": entity.state_topic,
        "entity_category": "diagnostic",
        "availability_topic": BRIDGE_AVAILABILITY_TOPIC,
        "platform": "mqtt",
        "device": {
            "identifiers": [SYSTEM_DEVICE_ID],
            "name": SYSTEM_DEVICE_NAME,
            "manufacturer": "jeedom2ha",
            "model": SYSTEM_DEVICE_NAME,
            "via_device": BRIDGE_DEVICE_ID,
        },
        "origin": {"name": "jeedom2ha", "sw_version": _SW_VERSION},
    }
    if entity.device_class:
        payload["device_class"] = entity.device_class
    if entity.state_class:
        payload["state_class"] = entity.state_class
    if entity.component == "binary_sensor":
        payload["payload_on"] = "ON"
        payload["payload_off"] = "OFF"
    return payload


def system_config_topic_pattern(prefix: str = "homeassistant") -> "re.Pattern[str]":
    """Motif STRICT des configurations de l'appareil : rien d'autre n'est jamais vidé par la purge."""
    return re.compile(
        rf"{re.escape(prefix)}/(binary_sensor|sensor)/{re.escape(SYSTEM_UNIQUE_ID_PREFIX)}([a-z0-9_]{{1,80}})/config"
    )
