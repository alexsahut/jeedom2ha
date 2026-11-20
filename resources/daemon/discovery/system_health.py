"""system_health.py — publication et purge de l'appareil « Santé de Jeedom » (story/system-health).

Hors du circuit des équipements : aucune entrée dans ``publications``, ``mappings`` ni les compteurs ; aucune action
d'équipement, de pièce ou de maison (« Supprimer de Home Assistant ») ne vise ces topics. Seule la case de la
configuration du plugin décide : cochée, le relevé est publié ; décochée, tout est purgé.

Purge : les configurations retenues de l'appareil sont relues sur le broker (source de vérité, même après un
redémarrage du démon) et vidées, avec leur état retenu, ainsi que celles publiées depuis le démarrage. Seul le motif
strict ``<prefix>/(binary_sensor|sensor)/jeedom2ha_system_<clé>/config`` est jamais vidé.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from mapping.system_health import (
    SYSTEM_COMPONENTS,
    SYSTEM_TOPIC_ROOT,
    SYSTEM_UNIQUE_ID_PREFIX,
    SystemHealthEntity,
    build_system_health_payload,
    map_system_health,
    system_config_topic_pattern,
)

_LOGGER = logging.getLogger(__name__)

# (composant, clé) publiés depuis le démarrage du démon.
PublishedKeys = Set[Tuple[str, str]]


class SystemHealthPublisher:
    """Publie le relevé, retire ce qui n'en fait plus partie, purge tout à la désactivation."""

    def __init__(self, mqtt_bridge: Any, published: Optional[PublishedKeys] = None,
                 topic_prefix: str = "homeassistant") -> None:
        self._bridge = mqtt_bridge
        self._prefix = topic_prefix
        # Ensemble partagé (``app["system_health_published"]``) : survit au remplacement du pont MQTT.
        self.published: PublishedKeys = published if published is not None else set()

    def _publish(self, topic: str, payload: str) -> bool:
        return bool(self._bridge.publish_message(topic, payload, qos=1, retain=True))

    def _empty(self, component: str, key: str) -> bool:
        config_topic = f"{self._prefix}/{component}/{SYSTEM_UNIQUE_ID_PREFIX}{key}/config"
        ok = self._publish(config_topic, "")
        ok = self._publish(f"{SYSTEM_TOPIC_ROOT}/{key}/state", "") and ok
        if ok:
            self.published.discard((component, key))
        return ok

    async def _retained_keys(self) -> Optional[PublishedKeys]:
        """Configurations retenues de l'appareil lues sur le broker ; None si la lecture est impossible."""
        collect = getattr(self._bridge, "collect_retained_topics", None)
        if collect is None:
            return None
        pattern = system_config_topic_pattern(self._prefix)
        found: PublishedKeys = set()
        for component in SYSTEM_COMPONENTS:
            try:
                topics = await collect(f"{self._prefix}/{component}/+/config")
            except Exception:
                _LOGGER.exception("[SYSTEM_HEALTH] Lecture des configurations retenues impossible")
                return None
            if not isinstance(topics, list):
                return None
            for topic in topics:
                match = pattern.fullmatch(topic) if isinstance(topic, str) else None
                if match and match.group(1) == component:
                    found.add((component, match.group(2)))
        return found

    async def apply(self, snapshot: Any) -> Dict[str, Any]:
        """Publie le relevé (configurations puis états retenus) et retire les entités qui n'en font plus partie."""
        entities: List[SystemHealthEntity] = map_system_health(snapshot)
        wanted = {(e.component, e.key) for e in entities}
        failed = 0
        for entity in entities:
            payload = json.dumps(build_system_health_payload(entity), ensure_ascii=False)
            if not self._publish(entity.config_topic(self._prefix), payload):
                failed += 1
                continue
            self.published.add((entity.component, entity.key))
            if entity.state is not None and not self._publish(entity.state_topic, entity.state):
                failed += 1
        removed = await self._remove(lambda key: key not in wanted)
        _LOGGER.info(
            "[SYSTEM_HEALTH] Santé de Jeedom publiée : %d entité(s), %d retirée(s), %d échec(s)",
            len(entities), len(removed), failed,
        )
        return {"entities": len(entities), "removed": sorted(k for _c, k in removed), "failed": failed}

    async def purge(self) -> Dict[str, Any]:
        """Vide toute l'appareil (configurations et états retenus). ``purge_complete`` vrai seulement si le broker a
        pu être relu et que chaque vidage a réussi."""
        retained = await self._retained_keys()
        candidates = set(self.published) | (retained or set())
        failed = [k for k in sorted(candidates) if not self._empty(*k)]
        complete = retained is not None and not failed
        _LOGGER.info(
            "[SYSTEM_HEALTH] Santé de Jeedom retirée : %d entité(s) vidée(s)%s",
            len(candidates) - len(failed), "" if complete else " (purge incomplète, nouvel essai demandé)",
        )
        removed = sorted(key for component, key in candidates if (component, key) not in failed)
        return {"removed": removed, "purge_complete": complete}

    async def _remove(self, keep_out: Any) -> List[Tuple[str, str]]:
        retained = await self._retained_keys()
        candidates: Iterable[Tuple[str, str]] = set(self.published) | (retained or set())
        removed = []
        for component, key in sorted(candidates):
            if keep_out((component, key)) and self._empty(component, key):
                removed.append((component, key))
        return removed
