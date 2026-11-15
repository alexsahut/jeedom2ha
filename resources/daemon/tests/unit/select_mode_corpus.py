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
# Formes réelles relevées en relecture (identifiants fictifs) : aucune ne doit gagner un select en double.
VOLET_ID = 9830           # volet : info texte 1/0 posée par FLAP_UP / FLAP_DOWN reliées
VOITURE_ID = 9831         # lumière : info texte « OnOff fictif » posée par LIGHT_ON / LIGHT_OFF reliées
ROUTEUR_ID = 9832         # routeur solaire : actions « liste » reliées à des infos numériques publiées en capteurs
MODES_ID = 9833           # « Modes » (forme réelle, plugin mode) : 7 actions reliées par la « Valeur » du cœur, 3 non
BORNE_ID = 9834           # borne (forme 583) : trois trios SWITCH_* par nom, action_ev action, ordres à deux liens
SERRURE_ID = 9835         # serrure virtuelle : état texte posé par LOCK_OPEN / LOCK_CLOSE reliées


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


def real_shape_eq_logics() -> List[Dict[str, Any]]:
    routeur_list = "0|bal-off_rad-off;1|bal-manu_rad-off;2|bal-auto_rad-off;4|baloff_rad-manu;5|bal-manu_rad-manu"
    modes = ["Absent", "Normal", "Vacances scolaires", "Travail", "Soirée", "Nuit", "Réveil"]
    return [
        _eq(VOLET_ID, "Volet bassin", [
            _cmd(983001, "Etat", "FLAP_STATE", "info", "string"),
            _cmd(983002, "Monter", "FLAP_UP", "action", "other", virtual_info_id="983001", virtual_value="1"),
            _cmd(983003, "Descendre", "FLAP_DOWN", "action", "other", virtual_info_id="983001", virtual_value="0"),
        ]),
        _eq(VOITURE_ID, "Voiture", [
            _cmd(983101, "Etat lumière", "LIGHT_STATE", "info", "binary"),
            _cmd(983102, "OnOff fictif", None, "info", "string"),
            _cmd(983103, "Allumer", "LIGHT_ON", "action", "other", virtual_info_id="983102", virtual_value="1"),
            _cmd(983104, "Eteindre", "LIGHT_OFF", "action", "other", virtual_info_id="983102", virtual_value="0"),
        ]),
        _eq(ROUTEUR_ID, "Routeur", [
            _cmd(983201, "Puissance panneaux", "POWER", "info", "numeric", unit="W"),
            _cmd(983202, "Etat sortie 1", None, "info", "numeric", unit="%"),
            _cmd(983203, "Etat sortie 2", None, "info", "numeric", unit="%"),
            _cmd(983204, "Commande 1", None, "action", "select", linked_value="983202", list_value=routeur_list),
            _cmd(983205, "Commande 2", None, "action", "select", linked_value="983203", list_value=routeur_list),
        ], eq_type="msunpv"),
        # Forme réelle de « Modes » (plugin mode, relue en prod) : MODE_STATE « Mode », logicalId currentMode (valeur
        # « Normal »), 7 actions MODE_SET_STATE reliées par la seule « Valeur » du cœur (le plugin écrit
        # leur NOM dans l'info), 3 actions MODE_SET_STATE non reliées, dont « Rejouer » qui porte
        # aujourd'hui le bouton d'équipement ; lock / unlock sans type générique.
        _eq(MODES_ID, "Modes", [
            _cmd(983375, "Rejouer", "MODE_SET_STATE", "action", "other"),
            _cmd(983301, "Mode", "MODE_STATE", "info", "string", current_value="Normal", logical_id="currentMode"),
            _cmd(983302, "previousMode", "DONT", "info", "string"),
            _cmd(983303, "lock_state", None, "info", "binary"),
            *[_cmd(983310 + i, name, "MODE_SET_STATE", "action", "other", linked_value="983301")
              for i, name in enumerate(modes)],
            _cmd(983352, "Retour mode précédent", "MODE_SET_STATE", "action", "other", linked_value=""),
            _cmd(983376, "Aller au mode suivant", "MODE_SET_STATE", "action", "other"),
            _cmd(983377, "lock", None, "action", "other", linked_value="983303"),
            _cmd(983378, "unlock", None, "action", "other", linked_value="983303"),
        ], eq_type="mode"),
        # Forme réelle de la borne (583) : trois trios SWITCH_* regroupés par nom, infos GENERIC_INFO, et
        # « action_ev » qui est une ACTION. Chaque ordre porte deux liens : son état (updateCmdId) et
        # l'info texte « Mode de charge » (infoId + value) — candidat select dont toutes les actions sont
        # déjà portées par les switchs : jamais publié.
        _eq(BORNE_ID, "Borne garage", [
            _cmd(983401, "Branche", "SWITCH_STATE", "info", "binary"),
            _cmd(983402, "Connecte", "SWITCH_STATE", "info", "binary"),
            _cmd(983403, "Charge", "SWITCH_STATE", "info", "binary"),
            _cmd(983404, "Charge On", "SWITCH_ON", "action", "other", update_cmd_id="983403", update_cmd_to_value="1",
                 virtual_info_id="983420", virtual_value="charge"),
            _cmd(983405, "Charge Off", "SWITCH_OFF", "action", "other", update_cmd_id="983403", update_cmd_to_value="0",
                 virtual_info_id="983420", virtual_value="arret"),
            _cmd(983406, "Charge solaire", "SWITCH_STATE", "info", "binary"),
            _cmd(983407, "Charge solaire On", "SWITCH_ON", "action", "other", update_cmd_id="983406",
                 update_cmd_to_value="1", virtual_info_id="983420", virtual_value="solaire"),
            _cmd(983408, "Charge solaire Off", "SWITCH_OFF", "action", "other", update_cmd_id="983406",
                 update_cmd_to_value="0", virtual_info_id="983420", virtual_value="arret solaire"),
            _cmd(983409, "Charge manuelle", "SWITCH_STATE", "info", "binary"),
            _cmd(983410, "Charge manuelle On", "SWITCH_ON", "action", "other", update_cmd_id="983409",
                 update_cmd_to_value="1", virtual_info_id="983420", virtual_value="manuelle"),
            _cmd(983411, "Charge manuelle Off", "SWITCH_OFF", "action", "other", update_cmd_id="983409",
                 update_cmd_to_value="0", virtual_info_id="983420", virtual_value="arret manuel"),
            _cmd(983412, "Puissance", "GENERIC_INFO", "info", "numeric", unit="W"),
            _cmd(983413, "Etat connecteur", "GENERIC_INFO", "info", "string"),
            _cmd(983420, "Mode de charge", "GENERIC_INFO", "info", "string"),
            _cmd(983421, "action_ev", None, "action", "other"),
            _cmd(983422, "Rafraichir", None, "action", "other"),
        ]),
        _eq(SERRURE_ID, "Serrure portillon", [
            _cmd(983501, "Etat", "LOCK_STATE", "info", "string"),
            _cmd(983502, "Ouvrir", "LOCK_OPEN", "action", "other", virtual_info_id="983501", virtual_value="0"),
            _cmd(983503, "Fermer", "LOCK_CLOSE", "action", "other", virtual_info_id="983501", virtual_value="1"),
        ]),
    ]


def load_scene() -> Dict[str, Any]:
    corpus = _base.load_scene(links=True)
    corpus["eq_logics"] = list(corpus["eq_logics"]) + mode_eq_logics() + real_shape_eq_logics()
    return corpus
