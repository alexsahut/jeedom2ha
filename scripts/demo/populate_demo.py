#!/usr/bin/env python3
"""Peuple une box Jeedom *vierge* avec le jeu de démonstration synthétique (Story 23.1).

Crée, de façon idempotente, via l'API JSON-RPC Jeedom (`core/api/jeeApi.php`) :
5 pièces, 16 équipements Virtuel (types génériques posés), 3 scénarios.
Le jeu contient volontairement un équipement sans type générique et un
équipement exclu (`jeedom2ha_excluded`) pour les écrans « Ne sera pas publié »
et « Exclu ».

Secrets (CC-48) : aucun argument de ligne de commande ne porte de secret.
L'URL et la clé API sont lues dans un fichier `.env` situé HORS du dépôt
(`--env-file`), variables `JEEDOM_API_URL`, `JEEDOM_API_KEY` et
`JEEDOM_DEMO_TARGET=demo` (garde-fou : confirme que la cible est la box de démo).
Aucune URL, clé ni identifiant interne n'est écrit sur stdout/stderr.

Contrat JSON-RPC : voir `docs/dev-demo-env.md` (section « Contrat API »).
Les noms de méthodes d'écriture sont isolés dans `JsonRpcContract` ; ils
sont NON DÉMONTRÉS sur box réelle (cf. règle de vérité du projet).

Usage :
    python3 scripts/demo/populate_demo.py --dry-run                  # plan hors-ligne
    python3 scripts/demo/populate_demo.py --env-file ~/.jeedom2ha-demo.env --dry-run
    python3 scripts/demo/populate_demo.py --env-file ~/.jeedom2ha-demo.env
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
EQ_TYPE = "virtual"
DEMO_TARGET_VALUE = "demo"
INVENTORY_SCHEMA = 1
OWNER_MARKER = "jeedom2ha_demo_key"  # marque les équipements créés par ce script


class DemoError(Exception):
    """Erreur d'exécution lisible, sans secret ni URL."""


# ---------------------------------------------------------------------------
# Jeu de démonstration (100 % synthétique : aucune donnée maison)
# ---------------------------------------------------------------------------

ROOMS = ["Salon", "Cuisine", "Chambre", "Bureau", "Garage"]


def _info(name, generic, sub="binary", unit="", history=False):
    return {"name": name, "type": "info", "subType": sub, "generic_type": generic, "unit": unit,
            "isHistorized": 1 if history else 0}


def _act(name, generic, sub="other", info=None, value=None):
    """Action Virtuel ; `value` = valeur écrite dans l'info liée (on/off).

    Lien info + valeur : NON DÉMONTRÉ (cf. docs/dev-demo-env.md, « Contrat API »).
    """
    cmd = {"name": name, "type": "action", "subType": sub, "generic_type": generic, "unit": "",
           "isHistorized": 0}
    if info:
        cmd["configuration"] = {"infoName": info}
        if value is not None:
            cmd["configuration"]["value"] = value
    return cmd


def _light(on_off_state="Etat"):
    return [_info(on_off_state, "LIGHT_STATE"),
            _act("On", "LIGHT_ON", info=on_off_state, value="1"),
            _act("Off", "LIGHT_OFF", info=on_off_state, value="0")]


def _dimmer():
    return _light() + [_info("Luminosite", "LIGHT_BRIGHTNESS", "numeric", "%"),
                       _act("Regler luminosite", "LIGHT_SLIDER", "slider", info="Luminosite")]


def _cover():
    return [_info("Position", "FLAP_STATE", "numeric", "%"),
            _act("Positionner", "FLAP_SLIDER", "slider", info="Position"),
            _act("Monter", "FLAP_UP", info="Position", value="100"),
            _act("Descendre", "FLAP_DOWN", info="Position", value="0")]


def _plug():
    return [_info("Etat", "ENERGY_STATE"),
            _act("On", "ENERGY_ON", info="Etat", value="1"),
            _act("Off", "ENERGY_OFF", info="Etat", value="0"),
            _info("Puissance", "POWER", "numeric", "W", history=True)]


def _temp_hum():
    return [_info("Temperature", "TEMPERATURE", "numeric", "°C", history=True),
            _info("Humidite", "HUMIDITY", "numeric", "%", history=True)]


EQUIPMENTS: List[Dict[str, Any]] = [
    {"key": "salon-lumiere", "room": "Salon", "name": "Lumiere Salon", "cmds": _light()},
    {"key": "salon-lampe-variable", "room": "Salon", "name": "Lampe Variable Salon", "cmds": _dimmer()},
    {"key": "salon-volet", "room": "Salon", "name": "Volet Salon", "cmds": _cover()},
    {"key": "salon-climat", "room": "Salon", "name": "Climat Salon", "cmds": _temp_hum()},
    {"key": "cuisine-lumiere", "room": "Cuisine", "name": "Lumiere Cuisine", "cmds": _light()},
    {"key": "cuisine-prise", "room": "Cuisine", "name": "Prise Cafetiere", "cmds": _plug()},
    {"key": "cuisine-compteur", "room": "Cuisine", "name": "Compteur Energie",
     "cmds": [_info("Energie", "CONSUMPTION", "numeric", "kWh", history=True)]},
    {"key": "cuisine-fenetre", "room": "Cuisine", "name": "Fenetre Cuisine",
     "cmds": [_info("Ouverture", "OPENING_WINDOW")]},
    {"key": "chambre-lampe-variable", "room": "Chambre", "name": "Lampe Variable Chambre",
     "cmds": _dimmer()},
    {"key": "chambre-volet", "room": "Chambre", "name": "Volet Chambre", "cmds": _cover()},
    {"key": "chambre-climat", "room": "Chambre", "name": "Climat Chambre", "cmds": _temp_hum()},
    {"key": "chambre-presence", "room": "Chambre", "name": "Presence Chambre",
     "cmds": [_info("Presence", "PRESENCE")]},
    {"key": "bureau-prise", "room": "Bureau", "name": "Prise Bureau", "cmds": _plug()},
    # Sans aucun type générique : « Ne sera pas publié — et pourquoi ».
    {"key": "bureau-sans-type", "room": "Bureau", "name": "Equipement Libre Bureau",
     "cmds": [_info("Mesure libre", "", "numeric"),
              _act("Action libre", "", info="Mesure libre", value="1")]},
    {"key": "garage-porte", "room": "Garage", "name": "Porte Garage",
     "cmds": [_info("Ouverture", "OPENING")]},
    # Exclu côté jeedom2ha : « Exclu ».
    {"key": "garage-lumiere-exclue", "room": "Garage", "name": "Lumiere Garage Exclue",
     "excluded": True, "cmds": _light()},
]

SCENARIOS: List[Dict[str, str]] = [
    {"key": "scenario-cinema", "name": "Scenario Cinema", "description": "Demo : ambiance cinema"},
    {"key": "scenario-depart", "name": "Scenario Depart", "description": "Demo : tout eteindre au depart"},
    {"key": "scenario-nuit", "name": "Scenario Nuit", "description": "Demo : mode nuit"},
]
SCENARIO_GROUP = "Demo"


# ---------------------------------------------------------------------------
# Adaptateur JSON-RPC Jeedom (seul endroit qui connaît les méthodes/champs)
# ---------------------------------------------------------------------------

class JsonRpcContract:
    """Noms de méthodes JSON-RPC. À prouver sur la VM 122.

    Seuls `cmd::execCmd` et `event::changes` sont prouvés par le projet
    (cf. jeedom2ha-test-context-jeedom-reel.md) ; les méthodes ci-dessous sont
    vérifiées dans les sources Jeedom 4.6.1 / Virtuel ``master``. La VM 122
    reste la preuve de compatibilité d'exécution.
    """
    ROOM_ALL = "jeeObject::all"
    ROOM_SAVE = "jeeObject::save"
    EQ_ALL = "eqLogic::all"
    EQ_SAVE = "eqLogic::save"
    CMD_BY_EQ = "cmd::byEqLogicId"
    SCENARIO_ALL = "scenario::all"
    SCENARIO_SAVE = "scenario::save"


class JeedomRpc:
    """Client JSON-RPC 2.0 minimal. Ne journalise jamais l'URL ni la clé."""

    def __init__(self, url: str, apikey: str, timeout: float = 15.0):
        if not url.lower().startswith(("http://", "https://")):
            raise DemoError("JEEDOM_API_URL doit commencer par http:// ou https://")
        self._url = url
        self._apikey = apikey
        self._timeout = timeout
        self._seq = 0

    def call(self, method: str, **params: Any) -> Any:
        self._seq += 1
        body = json.dumps({"jsonrpc": "2.0", "id": str(self._seq), "method": method,
                           "params": dict(params, apikey=self._apikey)}).encode()
        req = urllib.request.Request(self._url, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, socket.timeout, ValueError, OSError) as exc:
            # Message volontairement générique : l'exception peut contenir l'URL.
            raise DemoError("appel %s impossible (%s)" % (method, type(exc).__name__)) from None
        if not isinstance(payload, dict):
            raise DemoError("réponse JSON-RPC invalide pour %s" % method)
        if payload.get("error"):
            err = payload["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise DemoError("%s refusée par Jeedom : %s (contrat API non démontré ?)"
                            % (method, str(msg)[:120]))
        return payload.get("result")


class JeedomAdapter:
    """Traduit nos besoins métier en appels JSON-RPC (contrat isolé ici)."""

    def __init__(self, rpc: JeedomRpc, contract=JsonRpcContract):
        self.rpc = rpc
        self.c = contract

    def rooms(self) -> List[Dict[str, Any]]:
        return self.rpc.call(self.c.ROOM_ALL) or []

    def save_room(self, name: str) -> Dict[str, Any]:
        return self.rpc.call(self.c.ROOM_SAVE, name=name, isVisible=1)

    def eqlogics(self) -> List[Dict[str, Any]]:
        return self.rpc.call(self.c.EQ_ALL) or []

    def save_eqlogic(self, eq: Dict[str, Any]) -> Dict[str, Any]:
        return self.rpc.call(self.c.EQ_SAVE, **eq)

    def cmds(self, eq_id: Any) -> List[Dict[str, Any]]:
        return self.rpc.call(self.c.CMD_BY_EQ, eqLogic_id=eq_id) or []

    def scenarios(self) -> List[Dict[str, Any]]:
        return self.rpc.call(self.c.SCENARIO_ALL) or []

    def save_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        return self.rpc.call(self.c.SCENARIO_SAVE, **scenario)


# ---------------------------------------------------------------------------
# Réconciliation idempotente
# ---------------------------------------------------------------------------

def _bool(value: Any) -> bool:
    return str(value).lower() in ("1", "true")


def _owner_key(eq: Dict[str, Any]) -> str:
    cfg = eq.get("configuration")
    if not isinstance(cfg, dict) or str(eq.get("eqType_name", EQ_TYPE)) != EQ_TYPE:
        return ""
    return str(cfg.get(OWNER_MARKER) or "")


def _eq_excluded(eq: Dict[str, Any]) -> bool:
    cfg = eq.get("configuration")
    return isinstance(cfg, dict) and _bool(cfg.get("jeedom2ha_excluded", 0))


def _cmd_drift(existing: Dict[str, Any], wanted: Dict[str, Any]) -> bool:
    for field in ("type", "subType", "unit"):
        if str(existing.get(field) or "") != str(wanted.get(field) or ""):
            return True
    return str(existing.get("generic_type") or "") != str(wanted.get("generic_type") or "")


def _without_none(value: Any) -> Any:
    """Ne laisse jamais ``utils::a2o`` appliquer une clé JSON ``null``."""
    if isinstance(value, dict):
        return {key: _without_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_without_none(item) for item in value]
    return value


def _eqlogic_payload(spec: Dict[str, Any], room_id: Any, existing: Optional[Dict[str, Any]],
                     existing_cmds: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Construit le contrat ``eqLogic::save`` complet d'un Virtuel.

    Jeedom retire les commandes absentes de ``cmd``. Chaque sauvegarde transmet donc
    toutes les commandes, avec leur identifiant relu par nom, afin que les identifiants
    (et par conséquent les unique_id MQTT/HA) restent stables au second passage.
    """
    payload: Dict[str, Any] = {
        "eqType_name": EQ_TYPE, "name": spec["name"], "object_id": room_id,
        "isEnable": 1, "isVisible": 1,
        "configuration": {"jeedom2ha_excluded": 1 if spec.get("excluded") else 0,
                          OWNER_MARKER: spec["key"]},
        "cmd": [],
    }
    if existing:
        payload["id"] = existing.get("id")
    for wanted in spec["cmds"]:
        # jeeApi.php rattache lui-même chaque virtualCmd au nouvel eqLogic avant a2o().
        # Envoyer eqLogic_id=null le réinitialiserait ensuite via utils::a2o().
        cmd = dict(wanted, isVisible=1)
        previous = existing_cmds.get(wanted["name"])
        if previous:
            cmd["id"] = previous.get("id")
        payload["cmd"].append(cmd)
    return _without_none(payload)


def populate(adapter: Optional[JeedomAdapter], dry_run: bool,
             allow_non_empty: bool = False) -> Dict[str, Any]:
    """Applique (ou planifie) le jeu de démo et retourne l'inventaire anonymisé.

    `adapter=None` ⇒ plan hors-ligne (dry-run sans connexion).
    """
    live = adapter is not None
    write = live and not dry_run
    demo_names = {e["name"] for e in EQUIPMENTS}

    rooms_by_name: Dict[str, Any] = {}
    eq_by_key: Dict[Any, Dict[str, Any]] = {}
    scen_by_name: Dict[str, Any] = {}
    if live:
        for r in adapter.rooms():
            rooms_by_name[r.get("name")] = r.get("id")
        existing_eqs = adapter.eqlogics()
        owned = [e for e in existing_eqs if _owner_key(e)]
        foreign = [e for e in existing_eqs if not _owner_key(e)]
        collisions = [e for e in foreign if e.get("name") in demo_names]
        if collisions:
            raise DemoError("%d équipement(s) existant(s) portent un nom du jeu de démo sans "
                            "être des équipements de démo : abandon (aucune réutilisation)."
                            % len(collisions))
        if foreign and not allow_non_empty:
            raise DemoError("%d équipement(s) hors jeu de démo détecté(s) : cette box n'est pas "
                            "vierge. Abandon (--allow-non-empty pour forcer)." % len(foreign))
        for e in owned:
            eq_by_key[(str(e.get("object_id")), _owner_key(e))] = e
        for s in adapter.scenarios():
            scen_by_name[s.get("name")] = s

    def _status(exists: bool, changed: bool = False) -> str:
        if not live:
            return "planned"
        if dry_run:
            return "would_update" if exists and changed else ("exists" if exists else "would_create")
        return "updated" if exists and changed else ("exists" if exists else "created")

    inventory: Dict[str, Any] = {"schema": INVENTORY_SCHEMA, "dry_run": dry_run,
                                 "connected": live, "rooms": [], "equipments": [], "scenarios": []}

    for name in ROOMS:
        exists = name in rooms_by_name
        if write and not exists:
            saved = adapter.save_room(name)
            rooms_by_name[name] = (saved or {}).get("id")
        inventory["rooms"].append({"name": name, "status": _status(exists)})

    for spec in EQUIPMENTS:
        room_id = rooms_by_name.get(spec["room"])
        existing = eq_by_key.get((str(room_id), spec["key"])) if room_id is not None else None
        excluded = bool(spec.get("excluded"))
        changed = existing is not None and (_eq_excluded(existing) != excluded
                                            or not _bool(existing.get("isEnable", 1)))
        eq_id = existing.get("id") if existing else None
        existing_cmds = {}
        if live and existing is not None:
            existing_cmds = {c.get("name"): c for c in adapter.cmds(eq_id)}
        command_changed = any(
            cmd["name"] not in existing_cmds or _cmd_drift(existing_cmds[cmd["name"]], cmd)
            for cmd in spec["cmds"]
        )
        if write and (existing is None or changed or command_changed):
            payload = _eqlogic_payload(spec, room_id, existing, existing_cmds)
            saved = adapter.save_eqlogic(payload)
            eq_id = (saved or {}).get("id", eq_id)
        cmd_report = []
        for cmd in spec["cmds"]:
            ex = existing_cmds.get(cmd["name"])
            drift = ex is not None and _cmd_drift(ex, cmd)
            cmd_report.append({"name": cmd["name"], "type": cmd["type"], "subType": cmd["subType"],
                               "generic_type": cmd["generic_type"] or None,
                               "status": _status(ex is not None, drift)})
        inventory["equipments"].append({
            "key": spec["key"], "room": spec["room"], "name": spec["name"],
            "excluded": excluded, "status": _status(existing is not None, changed),
            "write_plan": {"method": JsonRpcContract.EQ_SAVE, "cmd_count": len(spec["cmds"])},
            "cmds": cmd_report})

    for spec in SCENARIOS:
        exists = spec["name"] in scen_by_name
        if write and not exists:
            adapter.save_scenario({"name": spec["name"], "group": SCENARIO_GROUP,
                                   "description": spec["description"], "isActive": 1,
                                   "mode": "provoke"})
        inventory["scenarios"].append({"key": spec["key"], "name": spec["name"],
                                       "status": _status(exists)})

    inventory["summary"] = _summarize(inventory)
    return inventory


def _summarize(inv: Dict[str, Any]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for item in inv["rooms"] + inv["scenarios"] + inv["equipments"]:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
        for cmd in item.get("cmds", []):
            counts[cmd["status"]] = counts.get(cmd["status"], 0) + 1
    typed = [c for e in inv["equipments"] for c in e["cmds"] if c["generic_type"]]
    return {"rooms": len(inv["rooms"]), "equipments": len(inv["equipments"]),
            "cmds": sum(len(e["cmds"]) for e in inv["equipments"]), "cmds_typed": len(typed),
            "scenarios": len(inv["scenarios"]),
            "excluded_equipments": sum(1 for e in inv["equipments"] if e["excluded"]),
            "untyped_equipments": sum(1 for e in inv["equipments"]
                                      if not any(c["generic_type"] for c in e["cmds"])),
            "by_status": counts}


# ---------------------------------------------------------------------------
# Configuration (.env hors dépôt) et CLI
# ---------------------------------------------------------------------------

def parse_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        env[key] = value
    return env


def load_config(env_file: str, repo_root: Path = REPO_ROOT) -> Dict[str, str]:
    path = Path(env_file).expanduser().resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError:
        pass
    else:
        raise DemoError("le fichier .env doit être HORS du dépôt (CC-48)")
    if not path.is_file():
        raise DemoError("fichier .env introuvable")
    if path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        print("avertissement : le fichier .env est lisible par d'autres utilisateurs "
              "(chmod 600 recommandé)", file=sys.stderr)
    env = parse_env_file(path)
    missing = [k for k in ("JEEDOM_API_URL", "JEEDOM_API_KEY") if not env.get(k)]
    if missing:
        raise DemoError("variable(s) manquante(s) dans le .env : " + ", ".join(missing))
    if env.get("JEEDOM_DEMO_TARGET") != DEMO_TARGET_VALUE:
        raise DemoError("JEEDOM_DEMO_TARGET=%s absent du .env : refus d'écrire sur une cible "
                        "non confirmée comme box de démo" % DEMO_TARGET_VALUE)
    return env


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--env-file", help="fichier .env hors dépôt (JEEDOM_API_URL, JEEDOM_API_KEY, "
                                      "JEEDOM_DEMO_TARGET=demo)")
    p.add_argument("--dry-run", action="store_true",
                   help="n'écrit rien ; sans --env-file, plan hors-ligne sans connexion")
    p.add_argument("--allow-non-empty", action="store_true",
                   help="autorise l'exécution si la box contient des équipements hors démo")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        adapter = None
        if args.env_file:
            cfg = load_config(args.env_file)
            adapter = JeedomAdapter(JeedomRpc(cfg["JEEDOM_API_URL"], cfg["JEEDOM_API_KEY"]))
        elif not args.dry_run:
            raise DemoError("--env-file est requis hors --dry-run")
        inventory = populate(adapter, args.dry_run, args.allow_non_empty)
    except DemoError as exc:
        print("erreur : %s" % exc, file=sys.stderr)
        return 1
    json.dump(inventory, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
