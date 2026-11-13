"""Front v2 — Lot 3 : corpus de test (corpus doré + trois équipements fictifs de démonstration).

Les trois équipements ajoutés illustrent chacun un conseil (`hints`) que le corpus doré ne
porte pas : multiprise aux ordres non reliés, portail sans ordres, ventilateur à vitesse.
Noms et identifiants fictifs uniquement.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

GOLDEN_CORPUS_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus" / "sync_payload.json"
)

MULTIPRISE_ID = 9801
PORTAIL_ID = 9802
VENTILATEUR_ID = 9803
NAME_MISMATCH_ID = 4002  # corpus doré : « Volet conflit switch 4002 » (name_heuristic_rejection)


def _cmd(cmd_id, name, generic_type, cmd_type, sub_type, **extra) -> Dict[str, Any]:
    entry = {
        "id": cmd_id, "name": name, "generic_type": generic_type,
        "type": cmd_type, "sub_type": sub_type,
    }
    entry.update(extra)
    return entry


def _eq(eq_id, name, cmds, eq_type="virtual", object_id=1) -> Dict[str, Any]:
    return {
        "id": eq_id, "name": name, "eq_type": eq_type, "object_id": object_id,
        "is_enable": True, "is_excluded": False, "is_visible": True,
        "status": {"timeout": 0}, "cmds": cmds,
    }


def demo_eq_logics() -> list:
    multiprise = _eq(MULTIPRISE_ID, "Multiprise bureau", [
        _cmd(980101, "Sortie 1", "SWITCH_STATE", "info", "binary"),
        _cmd(980102, "Sortie 2", "SWITCH_STATE", "info", "binary"),
        _cmd(980103, "Sortie 3", "SWITCH_STATE", "info", "binary"),
        _cmd(980111, "Allumer 1", "SWITCH_ON", "action", "other"),
        _cmd(980112, "Allumer 2", "SWITCH_ON", "action", "other"),
        _cmd(980113, "Allumer 3", "SWITCH_ON", "action", "other"),
        _cmd(980121, "Couper 1", "SWITCH_OFF", "action", "other"),
        _cmd(980122, "Couper 2", "SWITCH_OFF", "action", "other"),
        _cmd(980123, "Couper 3", "SWITCH_OFF", "action", "other"),
    ])
    portail = _eq(PORTAIL_ID, "Portail entree", [
        _cmd(980201, "Etat", "BARRIER_STATE", "info", "binary"),
    ], object_id=3)
    ventilateur = _eq(VENTILATEUR_ID, "Ventilateur chambre", [
        _cmd(980301, "Ventilation", "FAN_STATE", "info", "binary"),
        _cmd(980302, "Ventilation On", "FAN_ON", "action", "other", linked_value=980301),
        _cmd(980303, "Ventilation Off", "FAN_OFF", "action", "other", linked_value=980301),
        _cmd(980304, "Vitesse", "FAN_SPEED", "action", "slider", linked_value=980305),
        _cmd(980305, "Vitesse etat", "FAN_SPEED_STATE", "info", "numeric"),
    ], object_id=2)
    return [multiprise, portail, ventilateur]


def load_corpus() -> Dict[str, Any]:
    """Corpus doré complet + les trois équipements de démonstration (copie neuve à chaque appel)."""
    corpus = json.loads(GOLDEN_CORPUS_PATH.read_text(encoding="utf-8"))
    corpus = copy.deepcopy(corpus)
    corpus["eq_logics"] = list(corpus["eq_logics"]) + demo_eq_logics()
    return corpus


def sync_body(corpus: Dict[str, Any], request_id: str = "lot3") -> Dict[str, Any]:
    return {
        "action": "sync",
        "payload": {
            "objects": corpus["objects"],
            "eq_logics": corpus["eq_logics"],
            "sync_config": corpus.get("sync_config", {"confidence_policy": "sure_probable"}),
        },
        "request_id": request_id,
        "timestamp": "2026-11-13T00:00:00Z",
    }
