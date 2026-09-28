"""tools/parity_snapshot.py — Story 19.1 (Task 3, AC3-AC5).

Outil de parité en LECTURE SEULE STRICTE, exécuté depuis la VM de dev contre
une box Jeedom réelle (jamais l'inverse) : relève l'état de publication actuel
(décisions par équipement/commande, inventaire MQTT retained) pour comparer un
"avant" et un "après" déploiement du sync migré (Story 19.1), sans écriture ni
effet de bord.

Hors chemin de production : jamais importé par `transport/http_server.py` ni
par `main.py`, jamais exécuté automatiquement (invocation manuelle uniquement,
`python3 -m tools.parity_snapshot ...` depuis la VM de dev).

Entrée VM recommandée : `scripts/parity-snapshot.sh capture|diff`. Le wrapper
collecte MQTT sur la box par SSH et fournit --mqtt-inventory-file ; aucun
mosquitto_sub local ni sudo sur la VM requis.

Garanties de conception (guardrails Story 19.1) :
  - Lecture seule stricte : uniquement des requêtes HTTP GET
    (`/system/diagnostics`, `/system/published_scope`) et `mosquitto_sub`
    (jamais `mosquitto_pub`, jamais `/action/sync`, jamais d'écriture sur
    `data/ha_overrides.json`, aucun redémarrage daemon déclenché par l'outil
    lui-même).
  - Un relevé (décisions OU inventaire MQTT) VIDE est un ÉCHEC EXPLICITE (exit
    non-zéro, message clair), jamais un succès déguisé. C'est le piège déjà
    présent dans `jeedom2ha_diff_topic_lists`
    (`scripts/deploy-inventory-diff.sh`) : un flux `mosquitto_sub` vide y est
    traité silencieusement comme "0 avant / 0 après" — comportement correct
    pour l'affichage informatif de `deploy-to-box.sh`, mais inacceptable comme
    preuve de non-régression (AC3). Cet outil ne reproduit jamais ce piège.
  - Secrets jamais en argument de ligne de commande, jamais journalisés (AC5) :
    `local_secret` transite uniquement via variable d'environnement (ou fichier
    dont le CHEMIN est fourni par variable d'environnement) + en-tête HTTP.
    Les identifiants MQTT réutilisent exactement la technique CC-20
    (`scripts/deploy-to-box.sh::jeedom2ha_mqtt_auth_snippet`, PR #168) :
    fichier de config par défaut `mosquitto_sub` dans un dossier temporaire
    chmod 700 / fichier chmod 600, `XDG_CONFIG_HOME` positionné uniquement
    pour l'appel subprocess, jamais `-u`/`-P` en argv, jamais l'option `-o`
    (absente de mosquitto-clients 2.0.11 sur la box réelle).
  - Ordre déterministe (tri par eq_id / tri alphabétique des topics) pour
    qu'un diff "avant/après" ne dépende jamais de l'ordre d'itération.

Ce que l'outil NE FAIT PAS :
  - Il ne déclenche jamais de sync (`/action/sync`) : il lit l'état déjà en
    mémoire dans le daemon (rempli par le cycle de sync normal du plugin).
  - Il ne corrige aucune violation I11 ni aucun scope explicite détecté : il se
    contente de les relever et de les journaliser dans le rapport (AC4) — la
    correction de I11 est le sujet exclusif de Story 19.2.

Limite connue (I11) : `/system/diagnostics` n'expose pas de décision par
sous-capteur secondaire — la détection I11 ci-dessous est donc une heuristique
basée sur l'inventaire MQTT retained (un topic `jeedom2ha_<eq_id>[...]` publié
alors que l'équipement primaire n'est pas publié), pas une lecture directe du
`CommandDecision` du secondaire. Documenté ici pour Story 19.2, qui possède la
correction et pourra affiner cette mesure avec un accès direct à
`evaluate_equipment()`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

_LOCAL_SECRET_ENV = "JEEDOM2HA_LOCAL_SECRET"
_LOCAL_SECRET_FILE_ENV = "JEEDOM2HA_LOCAL_SECRET_FILE"
_MQTT_USER_ENV = "JEEDOM2HA_MQTT_USER"
_MQTT_PASS_ENV = "JEEDOM2HA_MQTT_PASS"

# Même convention de filtrage que scripts/deploy-to-box.sh (grep '/jeedom2ha_').
_MQTT_DISCOVERY_SUBSTRING = "jeedom2ha_"

# Reasons de niveau 2b/4 (models/evaluate_equipment.py, Story 19.0) portant un
# scope explicite (exclusion ou forçage) déjà décidé par un override persisté.
_EXPLICIT_SCOPE_REASONS = frozenset({
    "publication_excluded_eqlogic",
    "publication_excluded_command",
    "publication_forced",
})


class ParitySnapshotError(RuntimeError):
    """Échec explicite d'un relevé ou d'une comparaison — jamais un résultat
    vide/dégradé traité comme un succès (AC3)."""


def _load_local_secret(env: Optional[Dict[str, str]] = None) -> str:
    """Résout `local_secret` depuis l'environnement — JAMAIS depuis un argument
    de ligne de commande (AC5, non négociable). Accepte soit la valeur directe
    (`JEEDOM2HA_LOCAL_SECRET`), soit le CHEMIN d'un fichier à lire
    (`JEEDOM2HA_LOCAL_SECRET_FILE`) — jamais les deux à la fois (ambigu)."""
    env = os.environ if env is None else env
    direct = env.get(_LOCAL_SECRET_ENV)
    file_path = env.get(_LOCAL_SECRET_FILE_ENV)
    if direct and file_path:
        raise ParitySnapshotError(
            f"{_LOCAL_SECRET_ENV} et {_LOCAL_SECRET_FILE_ENV} sont tous deux définis — ambigu, "
            "fournissez UNE SEULE source pour local_secret."
        )
    if direct:
        return direct
    if file_path:
        with open(file_path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    raise ParitySnapshotError(
        f"local_secret introuvable : définissez {_LOCAL_SECRET_ENV} (valeur) ou "
        f"{_LOCAL_SECRET_FILE_ENV} (chemin de fichier) — jamais en argument de ligne de commande."
    )


def fetch_diagnostics(base_url: str, local_secret: str, *, timeout: float = 10.0) -> dict:
    """GET /system/diagnostics — lecture seule stricte (aucun /action/* appelé
    par cet outil). Le secret ne transite que par l'en-tête HTTP, jamais par
    l'URL (donc jamais dans un log d'accès en clair sous forme de querystring).
    """
    url = base_url.rstrip("/") + "/system/diagnostics"
    request = urllib.request.Request(
        url, headers={"X-Local-Secret": local_secret}, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ParitySnapshotError(f"Échec de connexion à {url} : {exc}") from exc
    if payload.get("status") != "ok":
        raise ParitySnapshotError(
            f"/system/diagnostics a répondu status={payload.get('status')!r} : "
            f"{payload.get('message', '(aucun message)')}"
        )
    return payload


def _command_records(commands: List[dict]) -> List[dict]:
    """Normalise une liste `matched_commands`/`unmatched_commands` (tri par
    cmd_id) en conservant `mapping_decision` : deux relevés avec les mêmes
    cmd_id mais une décision de mapping différente pour une commande (ex.
    `sure` -> `publication_forced`) ne doivent JAMAIS produire un diff vide
    (une comparaison réduite aux seuls cmd_id masquerait ce changement)."""
    return sorted(
        (
            {"cmd_id": c["cmd_id"], "mapping_decision": c.get("mapping_decision")}
            for c in commands
        ),
        key=lambda c: c["cmd_id"],
    )


def fetch_published_scope(base_url: str, local_secret: str, *, timeout: float = 10.0) -> dict:
    """GET /system/published_scope — contrat canonique du périmètre de
    publication (global -> pièce -> équipement), lecture seule stricte, mêmes
    garanties que `fetch_diagnostics` (secret uniquement via en-tête HTTP,
    jamais dans l'URL)."""
    url = base_url.rstrip("/") + "/system/published_scope"
    request = urllib.request.Request(
        url, headers={"X-Local-Secret": local_secret}, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ParitySnapshotError(f"Échec de connexion à {url} : {exc}") from exc
    if payload.get("status") != "ok":
        raise ParitySnapshotError(
            f"/system/published_scope a répondu status={payload.get('status')!r} : "
            f"{payload.get('message', '(aucun message)')}"
        )
    return payload


def _decision_records(diagnostics_payload: dict) -> List[dict]:
    """Normalise `payload.equipments` en relevé déterministe (tri par eq_id),
    une entrée par équipement avec la liste des commandes couvertes/non
    couvertes et leur décision de mapping respective."""
    equipments = diagnostics_payload.get("payload", {}).get("equipments", [])
    records = []
    for eq in equipments:
        records.append({
            "eq_id": eq["eq_id"],
            "name": eq.get("name"),
            "status_code": eq.get("status_code"),
            "reason_code": eq.get("reason_code"),
            "perimetre": eq.get("perimetre"),
            "statut": eq.get("statut"),
            "publication_override": eq.get("publication_override"),
            "matched_commands": _command_records(eq.get("matched_commands", [])),
            "unmatched_commands": _command_records(eq.get("unmatched_commands", [])),
        })
    records.sort(key=lambda r: r["eq_id"])
    return records


def _mqtt_auth_dir(user: Optional[str], password: Optional[str]) -> Optional[str]:
    """Réplique exacte de la technique CC-20 (PR #168,
    scripts/deploy-to-box.sh::jeedom2ha_mqtt_auth_snippet) : écrit un fichier
    de config par défaut `mosquitto_sub` — JAMAIS `mosquitto_pub`, cet outil ne
    publie jamais rien — dans un dossier temporaire chmod 700, fichier chmod
    600, en dehors de tout argv. mosquitto-clients 2.0.11 (box réelle) n'a pas
    l'option -o (disponible seulement depuis 2.1) : seul le fichier de config
    par défaut fonctionne sur le binaire réellement présent sur la box.
    """
    if not user:
        return None
    password = password or ""
    if "\n" in user or "\n" in password:
        raise ParitySnapshotError(
            "Identifiants MQTT contenant un retour à la ligne — incompatible avec le fichier "
            "de config mosquitto (format ligne par ligne, sans échappement). Voir CC-20."
        )
    auth_dir = tempfile.mkdtemp(prefix="jeedom2ha-parity-mqtt-")
    os.chmod(auth_dir, stat.S_IRWXU)  # 700
    config_path = os.path.join(auth_dir, "mosquitto_sub")
    with open(config_path, "w", encoding="utf-8") as fh:
        fh.write(f"-u {user}\n-P {password}\n")
    os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)  # 600
    return auth_dir


def fetch_mqtt_retained_inventory(
    host: str,
    port: int,
    *,
    user: Optional[str] = None,
    password: Optional[str] = None,
    timeout: float = 2.0,
    topic_filter: str = "homeassistant/+/+/config",
    discovery_substring: str = _MQTT_DISCOVERY_SUBSTRING,
    runner=subprocess.run,
) -> List[str]:
    """Relève l'inventaire des topics discovery retained via `mosquitto_sub -W`
    (lecture seule stricte — jamais `mosquitto_pub`, jamais `-r` en écriture).

    `runner` est injectable (Dev Notes AC3/Task 4) pour permettre aux tests de
    simuler `mosquitto_sub` sans jamais se connecter à un broker réel.

    Ne reproduit JAMAIS le pattern `|| true` de `deploy-to-box.sh` : toute
    erreur d'exécution (binaire absent, timeout subprocess) remonte comme
    `ParitySnapshotError` explicite plutôt que d'être avalée en résultat vide.
    """
    auth_dir = _mqtt_auth_dir(user, password)
    try:
        env = os.environ.copy()
        if auth_dir:
            env["XDG_CONFIG_HOME"] = auth_dir
        cmd = [
            "mosquitto_sub", "-h", host, "-p", str(port),
            "-W", str(timeout), "-t", topic_filter, "-F", "%t",
        ]
        try:
            result = runner(cmd, env=env, capture_output=True, text=True, timeout=timeout + 10)
        except FileNotFoundError as exc:
            raise ParitySnapshotError("mosquitto_sub introuvable sur cette VM de dev.") from exc
        except subprocess.TimeoutExpired as exc:
            raise ParitySnapshotError(
                f"mosquitto_sub n'a pas répondu dans le délai imparti ({timeout + 10}s) — "
                f"broker {host}:{port} probablement injoignable."
            ) from exc
    finally:
        if auth_dir:
            shutil.rmtree(auth_dir, ignore_errors=True)

    if result.returncode not in (0, 27):
        raise ParitySnapshotError(f"mosquitto_sub a échoué (code {result.returncode}).")
    topics = sorted({
        line.strip() for line in result.stdout.splitlines()
        if discovery_substring in line and line.strip()
    })
    return topics


def _detect_explicit_scope(decisions: List[dict]) -> List[dict]:
    """AC4 — relève, SANS corriger, tout état de scope explicite (override de
    publication Story 16.3 déjà actif : exclusion ou forçage) déjà présent sur
    la box. Détecté via `reason_code` (niveaux 2b/4 de `evaluate_equipment()`)
    et/ou la clé additive `publication_override` exposée par
    `/system/diagnostics` (Story 16.4)."""
    found = []
    for record in decisions:
        if record["reason_code"] in _EXPLICIT_SCOPE_REASONS or record.get("publication_override"):
            found.append({
                "eq_id": record["eq_id"],
                "reason_code": record["reason_code"],
                "publication_override": record.get("publication_override"),
            })
    return found


def _detect_published_scope_exceptions(published_scope_payload: dict) -> List[dict]:
    """AC4 — relève, SANS corriger, les équipements dont l'état de périmètre
    (`/system/published_scope`, contrat canonique global -> pièce ->
    équipement) est explicitement défini au niveau ÉQUIPEMENT
    (`decision_source` == `equipement`/`exception_equipement`) plutôt
    qu'hérité de la pièce ou du global.

    Couche INDÉPENDANTE de `_detect_explicit_scope` : cette dernière ne
    couvre que les overrides de POLITIQUE de publication (Story 16.3,
    `decide_publication`), pas le périmètre d'inclusion/exclusion résolu par
    `models/published_scope.py`. Les deux sont pertinentes pour Story 19.2 et
    doivent être relevées séparément (provenance distincte dans le rapport).

    Limite connue : `/system/published_scope` n'expose pas de drapeau "état
    pièce explicite" indépendant de son état effectif — seul le niveau
    équipement est détectable ici."""
    equipements = published_scope_payload.get("payload", {}).get("equipements", [])
    found = [
        {
            "eq_id": entry["eq_id"],
            "effective_state": entry.get("effective_state"),
            "decision_source": entry.get("decision_source"),
            "is_exception": entry.get("is_exception"),
        }
        for entry in equipements
        if entry.get("decision_source") in ("equipement", "exception_equipement")
    ]
    found.sort(key=lambda e: e["eq_id"])
    return found


def _detect_i11_candidates(decisions: List[dict], mqtt_topics: List[str]) -> List[dict]:
    """AC4 — heuristique I11 (primaire refusé, secondaire publié) — voir la
    limite documentée en tête de module : `/system/diagnostics` n'expose pas
    de décision par secondaire, donc la détection se fait par corrélation avec
    l'inventaire MQTT retained (un topic secondaire `jeedom2ha_<eq_id>_<cmd_id>`
    présent alors que le primaire n'est pas publié).

    Le node_id primaire lui-même (`jeedom2ha_<eq_id>`, SANS suffixe `_<cmd_id>`,
    cf. `discovery/publisher.py`) est délibérément exclu de la correspondance :
    un topic retained portant exactement ce segment n'est que le résidu/topic
    obsolète du primaire, jamais la preuve qu'un secondaire est publié — le
    confondre produirait un faux candidat I11."""
    candidates = []
    for record in decisions:
        if record["statut"] == "publie":
            continue  # primaire déjà publié : pas un cas I11
        eq_id = record["eq_id"]
        node_prefix = f"jeedom2ha_{eq_id}"
        secondary_prefix = node_prefix + "_"
        matching_topics = sorted(
            topic for topic in mqtt_topics
            if any(segment.startswith(secondary_prefix) for segment in topic.split("/"))
        )
        if matching_topics:
            candidates.append({
                "eq_id": eq_id,
                "primary_reason_code": record["reason_code"],
                "matching_topics": matching_topics,
            })
    return candidates


@dataclass
class ParitySnapshot:
    captured_at: str
    label: str
    decisions: List[dict]
    mqtt_topics: List[str]
    i11_candidates: List[dict] = field(default_factory=list)
    explicit_scope_entries: List[dict] = field(default_factory=list)
    published_scope_exceptions: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "captured_at": self.captured_at,
            "label": self.label,
            "decisions": self.decisions,
            "mqtt_topics": self.mqtt_topics,
            "i11_candidates": self.i11_candidates,
            "explicit_scope_entries": self.explicit_scope_entries,
            "published_scope_exceptions": self.published_scope_exceptions,
        }


def capture_snapshot(
    *,
    base_url: str,
    local_secret: str,
    mqtt_host: str,
    mqtt_port: int,
    label: str,
    mqtt_user: Optional[str] = None,
    mqtt_password: Optional[str] = None,
    mqtt_timeout: float = 2.0,
    http_timeout: float = 10.0,
    mqtt_runner=subprocess.run,
    mqtt_inventory_file: Optional[str] = None,
) -> ParitySnapshot:
    """Relève un snapshot complet (décisions + inventaire MQTT + I11/scope
    explicite). Échoue explicitement (ParitySnapshotError) si le relevé de
    décisions OU l'inventaire MQTT est vide — jamais un succès déguisé (AC3)."""
    diagnostics_payload = fetch_diagnostics(base_url, local_secret, timeout=http_timeout)
    decisions = _decision_records(diagnostics_payload)
    if not decisions:
        raise ParitySnapshotError(
            f"Relevé '{label}' : ÉCHEC — aucune décision de publication renvoyée par "
            f"{base_url}/system/diagnostics. Un relevé vide n'est jamais un succès déguisé "
            "(topologie probablement non initialisée côté daemon — appelez /action/sync depuis "
            "le plugin Jeedom AVANT ce relevé ; cet outil ne déclenche jamais de sync lui-même)."
        )

    if mqtt_inventory_file is not None:
        # Inventory collected on the box by scripts/parity-snapshot.sh over SSH.
        # The VM needs only Python's standard library, not mosquitto-clients.
        with open(mqtt_inventory_file, encoding="utf-8") as inventory:
            mqtt_topics = sorted({
                line.strip() for line in inventory
                if "/" + _MQTT_DISCOVERY_SUBSTRING in line and line.strip()
            })
    else:
        mqtt_topics = fetch_mqtt_retained_inventory(
            mqtt_host, mqtt_port,
            user=mqtt_user, password=mqtt_password,
            timeout=mqtt_timeout, runner=mqtt_runner,
        )
    if not mqtt_topics:
        raise ParitySnapshotError(
            f"Relevé '{label}' : ÉCHEC — inventaire MQTT retained vide pour "
            f"{mqtt_host}:{mqtt_port}. Un relevé vide (broker injoignable, mauvais topic, "
            "timeout) n'est JAMAIS traité comme un succès par cet outil — contrairement à "
            "scripts/deploy-to-box.sh qui avale ce cas avec `|| true` dans son inventaire "
            "informatif. Vérifiez la connectivité MQTT avant de relancer."
        )

    published_scope_payload = fetch_published_scope(base_url, local_secret, timeout=http_timeout)

    return ParitySnapshot(
        captured_at=datetime.now(timezone.utc).isoformat(),
        label=label,
        decisions=decisions,
        mqtt_topics=mqtt_topics,
        i11_candidates=_detect_i11_candidates(decisions, mqtt_topics),
        explicit_scope_entries=_detect_explicit_scope(decisions),
        published_scope_exceptions=_detect_published_scope_exceptions(published_scope_payload),
    )


def diff_snapshots(before: dict, after: dict) -> dict:
    """Compare deux relevés (dicts issus de `ParitySnapshot.to_dict()` ou
    rechargés depuis un fichier JSON). Échoue explicitement si l'un des deux
    relevés est vide (fichier invalide/tronqué) plutôt que de rapporter un
    diff vide trompeur — même garde-fou qu'à la capture (AC3)."""
    for role, snap in (("before", before), ("after", after)):
        if not snap.get("decisions"):
            raise ParitySnapshotError(
                f"Relevé '{role}' chargé sans aucune décision — fichier invalide/tronqué, "
                "refus de comparer (un diff vide ne doit jamais reposer sur une entrée vide)."
            )
        if not snap.get("mqtt_topics"):
            raise ParitySnapshotError(
                f"Relevé '{role}' chargé sans aucun topic MQTT — fichier invalide/tronqué, "
                "refus de comparer."
            )

    before_by_eq = {record["eq_id"]: record for record in before["decisions"]}
    after_by_eq = {record["eq_id"]: record for record in after["decisions"]}

    changed_decisions = []
    for eq_id in sorted(set(before_by_eq) | set(after_by_eq)):
        b = before_by_eq.get(eq_id)
        a = after_by_eq.get(eq_id)
        if b != a:
            changed_decisions.append({"eq_id": eq_id, "before": b, "after": a})

    before_topics = set(before["mqtt_topics"])
    after_topics = set(after["mqtt_topics"])
    return {
        "changed_decisions": changed_decisions,
        "topics_added": sorted(after_topics - before_topics),
        "topics_removed": sorted(before_topics - after_topics),
        "topic_count_before": len(before_topics),
        "topic_count_after": len(after_topics),
        "is_empty_diff": not changed_decisions and before_topics == after_topics,
    }


def _write_snapshot(snapshot: ParitySnapshot, output_path: str) -> None:
    # Exclusive creation: do not truncate an existing proof or follow a symlink.
    fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(snapshot.to_dict(), fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def _cmd_capture(args: argparse.Namespace) -> int:
    local_secret = _load_local_secret()
    mqtt_user = os.environ.get(_MQTT_USER_ENV)
    mqtt_password = os.environ.get(_MQTT_PASS_ENV)
    snapshot = capture_snapshot(
        base_url=args.base_url,
        local_secret=local_secret,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        label=args.label,
        mqtt_user=mqtt_user,
        mqtt_password=mqtt_password,
        mqtt_timeout=args.mqtt_timeout,
        mqtt_inventory_file=args.mqtt_inventory_file,
    )
    _write_snapshot(snapshot, args.output)
    print(f"Relevé '{args.label}' écrit : {args.output}")
    print(f"  Décisions : {len(snapshot.decisions)} équipement(s)")
    print(f"  Topics MQTT retained ({_MQTT_DISCOVERY_SUBSTRING}*) : {len(snapshot.mqtt_topics)}")
    if snapshot.i11_candidates:
        print(
            "  ATTENTION — candidats I11 détectés (relevé seul, correction Story 19.2) : "
            f"{len(snapshot.i11_candidates)}"
        )
    if snapshot.explicit_scope_entries:
        print(
            "  Scope explicite détecté — override de politique de publication (relevé seul, "
            f"aucune correction) : {len(snapshot.explicit_scope_entries)}"
        )
    if snapshot.published_scope_exceptions:
        print(
            "  Scope explicite détecté — périmètre équipement /system/published_scope (relevé "
            f"seul, aucune correction) : {len(snapshot.published_scope_exceptions)}"
        )
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    with open(args.before, "r", encoding="utf-8") as fh:
        before = json.load(fh)
    with open(args.after, "r", encoding="utf-8") as fh:
        after = json.load(fh)
    result = diff_snapshots(before, after)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    if not result["is_empty_diff"]:
        print("ÉCHEC — le relevé avant/après n'est PAS identique (AC3).", file=sys.stderr)
        return 1
    print("OK — relevé avant/après strictement identique (AC3).")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Story 19.1 — outil de parité en lecture seule (AC3-AC5). local_secret et "
            "identifiants MQTT jamais en argument : utilisez "
            f"{_LOCAL_SECRET_ENV}/{_LOCAL_SECRET_FILE_ENV} et "
            f"{_MQTT_USER_ENV}/{_MQTT_PASS_ENV}."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    capture_parser = sub.add_parser(
        "capture", help="Relève un snapshot (décisions + MQTT retained)."
    )
    capture_parser.add_argument("--base-url", required=True, help="ex. http://192.168.1.21:PORT")
    capture_parser.add_argument("--mqtt-inventory-file", help="Inventaire SSH du wrapper VM (aucun client MQTT local requis).")
    capture_parser.add_argument("--mqtt-host", required=True)
    capture_parser.add_argument("--mqtt-port", type=int, default=1883)
    capture_parser.add_argument("--mqtt-timeout", type=float, default=2.0)
    capture_parser.add_argument("--label", required=True, choices=("before", "after"))
    capture_parser.add_argument("--output", required=True)
    capture_parser.set_defaults(func=_cmd_capture)

    diff_parser = sub.add_parser("diff", help="Compare deux snapshots déjà capturés.")
    diff_parser.add_argument("--before", required=True)
    diff_parser.add_argument("--after", required=True)
    diff_parser.set_defaults(func=_cmd_diff)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ParitySnapshotError, OSError) as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
