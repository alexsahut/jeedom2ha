"""story/select-mode — scène représentative d'une installation existante, pour prouver que seuls des select
s'AJOUTENT (aucune entité ni aucun topic existant ne change).

Scène du correctif fix/switch-appariement-etat (corpus doré, équipements de démonstration, chauffe-eau avec
ses liens) + des équipements portant un mode sous chacune des trois formes, et des cas refusés. Noms et
identifiants fictifs. Bibliothèque standard seulement : chargé aussi par chemin pour capturer la ligne de base.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, List

_HERE = Path(__file__).resolve().parent
BASELINE_PATH = _HERE.parent / "fixtures" / "select_mode" / "projection_baseline.json"

THERMOSTAT_ID = 9820      # MODE_STATE + MODE_SET_STATE (noms des actions = options)
CLIM_ID = 9821            # action « liste » (listValue) reliée à l'info, + prise (entité unique avant)
DOUBLON_ID = 9822         # deux actions écrivent la même valeur : refusé
EXPRESSION_ID = 9823      # valeur calculée : refusée
SEUL_ETAT_ID = 9824       # MODE_STATE sans action : rien


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_select_{name}", _HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_base = _load("fix_switch_appariement_corpus")
_cmd = _base._cmd
_eq = _base._eq
sync_body = _base.sync_body
entity_commands = _base.entity_commands


def mode_eq_logics() -> List[Dict[str, Any]]:
    return [
        _eq(THERMOSTAT_ID, "Radiateur salle de bain", [
            _cmd(982001, "Température", "TEMPERATURE", "info", "numeric", unit="°C"),
            _cmd(982002, "Mode", "MODE_STATE", "info", "string"),
            _cmd(982003, "Confort", "MODE_SET_STATE", "action", "other"),
            _cmd(982004, "Eco", "MODE_SET_STATE", "action", "other"),
            _cmd(982005, "Hors-gel", "MODE_SET_STATE", "action", "other"),
        ], eq_type="zwavejs"),
        _eq(CLIM_ID, "Prise climatiseur", [
            _cmd(982101, "Etat", "ENERGY_STATE", "info", "binary"),
            _cmd(982102, "On", "ENERGY_ON", "action", "other"),
            _cmd(982103, "Off", "ENERGY_OFF", "action", "other"),
            _cmd(982104, "Mode clim", None, "info", "string"),
            _cmd(982105, "Choisir le mode", None, "action", "select",
                 linked_value="982104", list_value="cool|Froid;heat|Chaud;auto|Auto"),
        ], eq_type="zwavejs"),
        _eq(DOUBLON_ID, "Ballon cave", [
            _cmd(982201, "Etat", "ENERGY_STATE", "info", "binary"),
            _cmd(982202, "On", "ENERGY_ON", "action", "other"),
            _cmd(982203, "Off", "ENERGY_OFF", "action", "other"),
            _cmd(982204, "etat", None, "info", "string"),
            _cmd(982205, "Manu", None, "action", "other", virtual_info_id="982204", virtual_value="manu"),
            _cmd(982206, "Manuel", None, "action", "other", virtual_info_id="982204", virtual_value="manu"),
        ]),
        _eq(EXPRESSION_ID, "Ballon atelier", [
            _cmd(982301, "Etat", "ENERGY_STATE", "info", "binary"),
            _cmd(982302, "On", "ENERGY_ON", "action", "other"),
            _cmd(982303, "Off", "ENERGY_OFF", "action", "other"),
            _cmd(982304, "etat", None, "info", "string"),
            _cmd(982305, "Plus", None, "action", "other", virtual_info_id="982304", virtual_value="#982304# + 1"),
            _cmd(982306, "auto", None, "action", "other", virtual_info_id="982304", virtual_value="auto"),
        ]),
        _eq(SEUL_ETAT_ID, "Station météo", [
            _cmd(982401, "Température", "TEMPERATURE", "info", "numeric", unit="°C"),
            _cmd(982402, "Mode", "MODE_STATE", "info", "string"),
        ], eq_type="zwavejs"),
    ]


def load_scene() -> Dict[str, Any]:
    corpus = _base.load_scene(links=True)
    corpus["eq_logics"] = list(corpus["eq_logics"]) + mode_eq_logics()
    return corpus
