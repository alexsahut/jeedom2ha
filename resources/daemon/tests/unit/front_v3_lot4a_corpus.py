"""Front v3 — Lot 4a : scène de test des scénarios (corpus du Lot 3 de la v2 + scénarios fictifs).

La scène « mise à jour » reprend le corpus doré augmenté du Lot 3 de la v2 et y ajoute quatre
scénarios fictifs (actifs, inactif, exposé HomeKit) ainsi qu'un bouton de scénario supprimé de
Jeedom mais encore retenu sur le broker (id 99), pour que la purge « le broker fait foi » soit
exercée. Noms et identifiants fictifs uniquement.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from .front_v2_lot3_corpus import load_corpus

DELETED_SCENARIO_ID = 99
DELETED_SCENARIO_TOPIC = f"homeassistant/button/jeedom2ha_scenario_{DELETED_SCENARIO_ID}/config"


def legacy_scenarios() -> List[Dict[str, Any]]:
    """Scénarios tels que les envoie le PHP d'avant le Lot 4a (aucun champ de publication)."""
    return [
        {"id": 20, "name": "Scène soirée", "is_active": True,
         "homekit_exposed": True, "homekit_exposed_source": "scenario_config"},
        {"id": 21, "name": "Arrosage nuit", "is_active": False,
         "homekit_exposed": None, "homekit_exposed_source": None},
        {"id": 22, "name": "Tout éteindre", "is_active": True,
         "homekit_exposed": False, "homekit_exposed_source": None},
        {"id": 23, "name": "Départ maison", "is_active": True,
         "homekit_exposed": None, "homekit_exposed_source": None},
    ]


_EXTRA = {
    20: {"group": "Ambiances", "mode": "provoke", "has_trigger": False, "has_schedule": False, "manual": True},
    21: {"group": "Jardin", "mode": "schedule", "has_trigger": False, "has_schedule": True, "manual": False},
    22: {"group": "", "mode": "all", "has_trigger": True, "has_schedule": True, "manual": False},
    23: {"group": "Ambiances", "mode": "provoke", "has_trigger": True, "has_schedule": False, "manual": False},
}


def lot4a_scenarios(published: Optional[Dict[int, bool]] = None,
                    is_new: Optional[Dict[int, bool]] = None) -> List[Dict[str, Any]]:
    """Scénarios du PHP du Lot 4a : champs additifs ; `published` / `is_new` par identifiant.

    `published` absent (None) : le champ n'est pas envoyé (PHP sans configuration de publication).
    """
    rows = []
    for row in legacy_scenarios():
        row = dict(row)
        row.update(_EXTRA[row["id"]])
        if published is not None:
            row["published"] = bool(published.get(row["id"], False))
            row["is_new"] = bool((is_new or {}).get(row["id"], False))
        rows.append(row)
    return rows


def upgrade_scenarios() -> List[Dict[str, Any]]:
    """Après la migration d'une installation mise à jour : tous publiés, aucun nouveau."""
    return lot4a_scenarios(published={row["id"]: True for row in legacy_scenarios()})


def sync_body(scenarios: List[Dict[str, Any]], request_id: str = "lot4a",
              complete: bool = True) -> Dict[str, Any]:
    corpus = load_corpus()
    return {
        "action": "sync",
        "payload": {
            "objects": corpus["objects"],
            "eq_logics": corpus["eq_logics"],
            "scenarios": copy.deepcopy(scenarios),
            "scenarios_complete": complete,
            "sync_config": corpus.get("sync_config", {"confidence_policy": "sure_probable"}),
        },
        "request_id": request_id,
        "timestamp": "2026-11-14T00:00:00Z",
    }


class RetainingRecordingBridge:
    """Faux pont MQTT sous le VRAI `DiscoveryPublisher` : journal brut + messages retenus.

    `collect_retained_topics` rend les topics retenus correspondant au filtre (seul `+` en
    avant-dernier niveau est utilisé par la purge des boutons de scénario).
    """

    def __init__(self, retained: Optional[Dict[str, str]] = None) -> None:
        self.is_connected = True
        self.state = "connected"
        self.broker_info = "broker.example.test:1883"
        self.calls: List[dict] = []
        self.retained: Dict[str, str] = dict(retained or {})

    def publish_message(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> bool:
        self.calls.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})
        if retain:
            if payload == "":
                self.retained.pop(topic, None)
            else:
                self.retained[topic] = payload
        return True

    async def collect_retained_topics(self, topic_filter: str) -> List[str]:
        prefix, _plus, suffix = topic_filter.partition("+")
        return sorted(
            topic for topic in self.retained
            if topic.startswith(prefix) and topic.endswith(suffix)
            and "/" not in topic[len(prefix):len(topic) - len(suffix)]
        )


def deleted_scenario_retained() -> Dict[str, str]:
    """Broker de départ : le bouton d'un scénario supprimé de Jeedom est encore retenu."""
    return {DELETED_SCENARIO_TOPIC: '{"name": "ancien"}'}
