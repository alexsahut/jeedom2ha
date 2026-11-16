"""story/barrier-state-sensor — scène représentative d'une installation existante, pour prouver que seuls
les capteurs « État » des covers barrière s'AJOUTENT (aucune entité ni aucun topic existant ne change).

Scène de story/select-mode (corpus doré, démonstrations, chauffe-eau, modes, formes réelles) + des portes
de garage et portails sous chacune des formes de la story 24.7, dont les deux formes relevées en
production (garage à bascule et 5 actions de forçage invisibles ; portail à ordres directs ET bascule),
et les cas sans compagnon. Noms et identifiants fictifs. Bibliothèque standard seulement : chargé aussi
par chemin pour capturer la ligne de base sur main.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, List

_HERE = Path(__file__).resolve().parent
BASELINE_PATH = _HERE.parent / "fixtures" / "barrier_state_sensor" / "projection_baseline.json"

GARAGE_ID = 9840          # forme réelle « Garage » : GARAGE_STATE numérique, GB_TOGGLE, 5 forçages invisibles
PORTAIL_ID = 9841         # forme réelle « Portail » : BARRIER_STATE numérique, GB_OPEN, GB_CLOSE, GB_TOGGLE
PORTAIL_DIRECT_ID = 9842  # GB_OPEN / GB_CLOSE seuls (mode direct)
PORTAIL_EXCLU_ID = 9843   # BARRIER_STATE binaire, équipement exclu par son objet : rien
GARAGE_BINAIRE_ID = 9844  # GARAGE_STATE binaire : binary_sensor garage_door, pas de compagnon
BARRIERE_NON_ELIGIBLE_ID = 9845  # GB_OPEN seul : pas de cover, pas de compagnon
VOLET_FLAP_ID = 9846      # volet FLAP_* numérique : cover non barrière, pas de compagnon

RUE_OBJECT_ID = 98

BARRIER_COVER_IDS = (GARAGE_ID, PORTAIL_ID, PORTAIL_DIRECT_ID)
# Identifiant de l'info d'état d'une cover barrière : ``eq_id * 100 + décalage``.
BARRIER_STATE_ID_OFFSET = {GARAGE_ID: 26, PORTAIL_ID: 43, PORTAIL_DIRECT_ID: 1}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_barrier_{name}", _HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_modes = _load("select_mode_corpus")
_cmd = _modes._cmd
_eq = _modes._eq
sync_body = _modes.sync_body
entity_commands = _modes.entity_commands


def garage_cmds(eq_id: int = GARAGE_ID) -> List[Dict[str, Any]]:
    """Forme de l'équipement « Garage » relevée en production (identifiants décalés)."""
    base = eq_id * 100
    state = base + 26
    forcings = [(27, "Ouverture", "254"), (28, "Fermeture", "252"), (29, "Arrêt", "253"),
                (30, "Ouvert", "255"), (31, "Fermé", "0")]
    return [
        _cmd(base + 24, "Ouvrir/Fermer", "GB_TOGGLE", "action", "other"),
        _cmd(state, "Etat", "GARAGE_STATE", "info", "numeric", current_value="0"),
        *[_cmd(base + i, name, None, "action", "other", is_visible=False,
               virtual_info_id=str(state), virtual_value=value) for i, name, value in forcings],
    ]


def portail_cmds(eq_id: int = PORTAIL_ID) -> List[Dict[str, Any]]:
    """Forme de l'équipement « Portail » relevée en production : la bascule est prioritaire."""
    base = eq_id * 100
    return [
        _cmd(base + 42, "Ouvrir/Fermer", "GB_TOGGLE", "action", "other"),
        _cmd(base + 43, "Etat", "BARRIER_STATE", "info", "numeric", current_value="255"),
        _cmd(base + 45, "Ouvrir", "GB_OPEN", "action", "other"),
        _cmd(base + 46, "Fermer", "GB_CLOSE", "action", "other"),
    ]


def barrier_eq_logics() -> List[Dict[str, Any]]:
    excluded = _eq(PORTAIL_EXCLU_ID, "Portail rue", [
        _cmd(PORTAIL_EXCLU_ID * 100 + 76, "Etat", "BARRIER_STATE", "info", "binary"),
        _cmd(PORTAIL_EXCLU_ID * 100 + 77, "Ouvrir", "GB_OPEN", "action", "other"),
        _cmd(PORTAIL_EXCLU_ID * 100 + 78, "Fermer", "GB_CLOSE", "action", "other"),
    ], eq_type="zwavejs", object_id=RUE_OBJECT_ID)
    # Exclu par son objet (pièce exclue) : l'objet ne contient que lui dans la scène.
    excluded.update({"is_excluded": True, "exclusion_source": "object"})
    return [
        _eq(GARAGE_ID, "Garage", garage_cmds()),
        _eq(PORTAIL_ID, "Portail", portail_cmds()),
        _eq(PORTAIL_DIRECT_ID, "Portail allée", [
            _cmd(PORTAIL_DIRECT_ID * 100 + 1, "Etat", "BARRIER_STATE", "info", "numeric", current_value="0"),
            _cmd(PORTAIL_DIRECT_ID * 100 + 2, "Ouvrir", "GB_OPEN", "action", "other"),
            _cmd(PORTAIL_DIRECT_ID * 100 + 3, "Fermer", "GB_CLOSE", "action", "other"),
        ]),
        excluded,
        _eq(GARAGE_BINAIRE_ID, "Garage atelier", [
            _cmd(GARAGE_BINAIRE_ID * 100 + 1, "Etat", "GARAGE_STATE", "info", "binary"),
            _cmd(GARAGE_BINAIRE_ID * 100 + 2, "Ouvrir/Fermer", "GB_TOGGLE", "action", "other"),
        ]),
        _eq(BARRIERE_NON_ELIGIBLE_ID, "Barrière parking", [
            _cmd(BARRIERE_NON_ELIGIBLE_ID * 100 + 1, "Etat", "BARRIER_STATE", "info", "numeric"),
            _cmd(BARRIERE_NON_ELIGIBLE_ID * 100 + 2, "Ouvrir", "GB_OPEN", "action", "other"),
        ]),
        _eq(VOLET_FLAP_ID, "Volet bureau", [
            _cmd(VOLET_FLAP_ID * 100 + 1, "Etat", "FLAP_STATE", "info", "numeric"),
            _cmd(VOLET_FLAP_ID * 100 + 2, "Monter", "FLAP_UP", "action", "other"),
            _cmd(VOLET_FLAP_ID * 100 + 3, "Descendre", "FLAP_DOWN", "action", "other"),
            _cmd(VOLET_FLAP_ID * 100 + 4, "Stop", "FLAP_STOP", "action", "other"),
        ]),
    ]


def load_scene() -> Dict[str, Any]:
    corpus = _modes.load_scene()
    corpus["objects"] = list(corpus["objects"]) + [{"id": RUE_OBJECT_ID, "name": "Rue"}]
    corpus["eq_logics"] = list(corpus["eq_logics"]) + barrier_eq_logics()
    return corpus
