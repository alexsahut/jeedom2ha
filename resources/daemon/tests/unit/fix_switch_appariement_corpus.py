"""fix/switch-appariement-etat — scène représentative d'une installation existante.

Corpus doré + trois équipements de démonstration du Front v2 (Lot 3), auxquels s'ajoutent :

- le chauffe-eau virtuel (plusieurs paires On/Off, chacune reliée à son info), tel que l'exporte
  le PHP de ce correctif (liens ``update_cmd_id`` / ``virtual_info_id``) ;
- le même chauffe-eau sans aucun lien (PHP d'avant, ou liens absents dans Jeedom) : cas ambigu ;
- des équipements à une seule paire, reliée ou non, pour prouver qu'ils ne bougent pas.

Noms et identifiants fictifs, sauf les ids de commandes du chauffe-eau (déjà dans le corpus de la
story 11.2). Aucun nom réel, aucune adresse. Ce module ne dépend que de la bibliothèque standard :
il est aussi chargé par chemin pour capturer la ligne de base sur le code d'avant.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
GOLDEN_CORPUS_PATH = _FIXTURES / "golden_corpus" / "sync_payload.json"
BASELINE_PATH = _FIXTURES / "fix_switch_appariement" / "projection_baseline.json"

CHAUFFE_EAU_ID = 554
CHAUFFE_EAU_SANS_LIEN_ID = 9810
PRISE_RELIEE_ID = 9811
PRESENCE_ID = 9812
PRISE_LIEN_AILLEURS_ID = 9813


def _cmd(cmd_id, name, generic_type, cmd_type, sub_type, **extra) -> Dict[str, Any]:
    entry = {"id": cmd_id, "name": name, "generic_type": generic_type, "type": cmd_type, "sub_type": sub_type}
    entry.update(extra)
    return entry


def _eq(eq_id, name, cmds, eq_type="virtual", object_id=1) -> Dict[str, Any]:
    return {
        "id": eq_id, "name": name, "eq_type": eq_type, "object_id": object_id,
        "is_enable": True, "is_excluded": False, "is_visible": True,
        "status": {"timeout": 0}, "cmds": cmds,
    }


def chauffe_eau_cmds(offset: int = 0, links: bool = True) -> List[Dict[str, Any]]:
    """Commandes du chauffe-eau (ordre Jeedom de la capture terrain de la story 11.2)."""
    def i(cmd_id):
        return cmd_id + offset

    def link(**fields):
        return {k: (str(i(v)) if k.endswith("_id") else v) for k, v in fields.items()} if links else {}

    return [
        _cmd(i(5205), "Routage", None, "info", "numeric", unit="%"),
        _cmd(i(5530), "Routage réel", "ENERGY_STATE", "info", "numeric", unit="%"),
        _cmd(i(5706), "On_5701", "ENERGY_ON", "action", "other", **link(update_cmd_id=5708)),
        _cmd(i(5707), "Off_5702", "ENERGY_OFF", "action", "other", **link(update_cmd_id=5708)),
        _cmd(i(5204), "Rafraichir", None, "action", "other"),
        _cmd(i(5206), "Puissance", None, "info", "numeric", unit="W"),
        _cmd(i(5489), "etat", None, "info", "string"),
        _cmd(i(5372), "Absence", None, "action", "other", **link(virtual_info_id=5489)),
        _cmd(i(5490), "Manu", "ENERGY_ON", "action", "other", **link(virtual_info_id=5489)),
        _cmd(i(5491), "auto", "ENERGY_OFF", "action", "other", **link(virtual_info_id=5489)),
        _cmd(i(5510), "chauffe complète dans la journée", None, "info", "binary"),
        _cmd(i(5535), "CE Kwh chauffe complete", None, "info", "numeric", unit="kWh"),
        _cmd(i(5708), "activé", "ENERGY_STATE", "info", "binary"),
    ]


def scene_eq_logics(links: bool = True) -> List[Dict[str, Any]]:
    return [
        _eq(CHAUFFE_EAU_ID, "Chauffe-eau", chauffe_eau_cmds(links=links)),
        _eq(CHAUFFE_EAU_SANS_LIEN_ID, "Ballon buanderie", chauffe_eau_cmds(offset=900000, links=False)),
        _eq(PRISE_RELIEE_ID, "Prise atelier", [
            _cmd(981101, "Etat", "ENERGY_STATE", "info", "binary"),
            _cmd(981102, "On", "ENERGY_ON", "action", "other", linked_value="981101"),
            _cmd(981103, "Off", "ENERGY_OFF", "action", "other", update_cmd_id="981101"),
        ], eq_type="zwavejs"),
        _eq(PRISE_LIEN_AILLEURS_ID, "Prise cellier", [
            _cmd(981301, "Etat", "ENERGY_STATE", "info", "binary"),
            _cmd(981302, "Mode", None, "info", "string"),
            _cmd(981303, "On", "ENERGY_ON", "action", "other", virtual_info_id="981302"),
            _cmd(981304, "Off", "ENERGY_OFF", "action", "other"),
        ]),
        _eq(PRESENCE_ID, "Présence maison", [
            _cmd(981201, "Présent", "PRESENCE", "info", "binary"),
            _cmd(981202, "Arriver", "SET_ON", "action", "other", update_cmd_id="981201"),
            _cmd(981203, "Partir", "SET_OFF", "action", "other"),
        ], object_id=2),
    ]


def load_scene(links: bool = True) -> Dict[str, Any]:
    corpus = copy.deepcopy(json.loads(GOLDEN_CORPUS_PATH.read_text(encoding="utf-8")))
    from_lot3 = _lot3_demo()
    # Le corpus doré porte déjà le chauffe-eau : la scène le remplace par sa version (avec ou sans liens).
    golden = [eq for eq in corpus["eq_logics"] if eq["id"] != CHAUFFE_EAU_ID]
    corpus["eq_logics"] = golden + from_lot3 + scene_eq_logics(links=links)
    return corpus


def _lot3_demo() -> List[Dict[str, Any]]:
    """Les trois équipements de démonstration du Lot 3 (copie, sans import de paquet)."""
    import importlib.util

    path = Path(__file__).resolve().parent / "front_v2_lot3_corpus.py"
    spec = importlib.util.spec_from_file_location("_lot3_corpus_for_appariement", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.demo_eq_logics()


def sync_body(corpus: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    return {
        "action": "sync",
        "payload": {
            "objects": corpus["objects"],
            "eq_logics": corpus["eq_logics"],
            "sync_config": corpus.get("sync_config", {"confidence_policy": "sure_probable"}),
        },
        "request_id": request_id,
        "timestamp": "2026-11-15T00:00:00Z",
    }


def entity_commands(mappings: Dict[int, Any]) -> Dict[str, Dict[str, Any]]:
    """Projection lisible : par entité, type HA, confiance et commandes Jeedom portées (rôle → id)."""
    out: Dict[str, Dict[str, Any]] = {}
    for eq_id in sorted(mappings):
        primary = mappings[eq_id]
        if primary is None:
            continue
        for mapping in [primary, *(getattr(primary, "additional_mappings", None) or [])]:
            out[mapping.ha_unique_id] = {
                "type": mapping.ha_entity_type,
                "confidence": mapping.confidence,
                "commands": {role: int(cmd.id) for role, cmd in sorted((mapping.commands or {}).items())},
            }
    return out
