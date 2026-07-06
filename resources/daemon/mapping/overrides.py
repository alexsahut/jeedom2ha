"""overrides.py — Story 16.1: persistance backend du schéma d'overrides utilisateur v1.

Persiste les overrides HA locaux (mapping candidat / décision, Story 16.2+) dans
`data/ha_overrides.json`, jamais dans le modèle topologie Jeedom (`JeedomCmd`/`JeedomEqLogic`
restent intouchés — D10). Ce module ne fait que lire/écrire ce fichier : il n'est jamais
appelé par le pipeline de sync (`assess_all`/`map`/`validate_projection`/`decide_publication`/
`publish`), uniquement par un futur handler HTTP (Story 16.6) ou une édition manuelle du JSON.

Format v1 (D9) :
    {
        "schema_version": 1,
        "overrides": {
            "<jeedom_eq_id>:<jeedom_cmd_id>": {"source": "user", ...}
        }
    }

Contrairement à `cache/disk_cache.py` (cold-start silencieux `{}` sur fichier absent/corrompu),
un `schema_version` absent, non entier ou non supporté est un refus explicite avec diagnostic
loggé — un override ne doit jamais s'appliquer silencieusement sur un schéma inconnu (D9/D11).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, Optional

_LOGGER = logging.getLogger(__name__)
_OVERRIDES_FILENAME = "ha_overrides.json"
_SCHEMA_VERSION = 1


def _overrides_path(data_dir: str) -> str:
    return os.path.join(data_dir, _OVERRIDES_FILENAME)


def _override_key(jeedom_eq_id: int, jeedom_cmd_id: int) -> str:
    return f"{jeedom_eq_id}:{jeedom_cmd_id}"


def _load_raw(data_dir: str) -> Optional[Dict]:
    """Load and validate the overrides file.

    Returns `{"schema_version": 1, "overrides": {}}` if the file does not exist yet
    (expected on first save — not a schema error). Returns None — with an explicit
    `_LOGGER.error(...)` — if the file exists but is corrupted, malformed, or carries
    an unsupported `schema_version`.
    """
    path = _overrides_path(data_dir)

    if not os.path.exists(path):
        return {"schema_version": _SCHEMA_VERSION, "overrides": {}}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _LOGGER.error("[OVERRIDES] Fichier d'overrides illisible ou corrompu : %s (%s)", path, exc)
        return None

    if not isinstance(raw, dict):
        _LOGGER.error("[OVERRIDES] Fichier d'overrides invalide (racine non-objet) : %s", path)
        return None

    schema_version = raw.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != _SCHEMA_VERSION:
        _LOGGER.error(
            "[OVERRIDES] schema_version invalide ou non supportée (%r) dans %s — override refusé",
            schema_version, path,
        )
        return None

    overrides = raw.get("overrides")
    if not isinstance(overrides, dict):
        _LOGGER.error("[OVERRIDES] Clé 'overrides' absente ou invalide dans %s", path)
        return None

    return {"schema_version": schema_version, "overrides": overrides}


def list_overrides(data_dir: str) -> Dict[str, dict]:
    """Return all persisted overrides keyed by 'jeedom_eq_id:jeedom_cmd_id'.

    Returns {} if the file is absent, OR if its schema is invalid/unsupported
    (diagnostic already logged by `_load_raw`).
    """
    raw = _load_raw(data_dir)
    if raw is None:
        return {}
    return dict(raw["overrides"])


def save_override(jeedom_eq_id: int, jeedom_cmd_id: int, override: dict, data_dir: str) -> None:
    """Persist a single override, merging with any existing entries.

    Adds `"source": "user"` if not already present in `override`.

    Raises:
        ValueError: if the existing file has an invalid/unsupported `schema_version` —
            never silently overwritten (D9/D11 — no bypass of a broken/unknown schema).
    """
    raw = _load_raw(data_dir)
    if raw is None:
        raise ValueError(
            f"Impossible de sauvegarder l'override {jeedom_eq_id}:{jeedom_cmd_id} — "
            f"fichier d'overrides existant invalide ou schema_version non supportée"
        )

    entry = dict(override)
    entry.setdefault("source", "user")
    raw["overrides"][_override_key(jeedom_eq_id, jeedom_cmd_id)] = entry

    if not os.path.isdir(data_dir):
        _LOGGER.warning("[OVERRIDES] data_dir introuvable : %s — override non sauvegardé", data_dir)
        return

    path = _overrides_path(data_dir)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        _LOGGER.info(
            "[OVERRIDES] Override sauvegardé : %s dans %s",
            _override_key(jeedom_eq_id, jeedom_cmd_id), path,
        )
    except OSError as exc:
        _LOGGER.error("[OVERRIDES] Échec sauvegarde override : %s", exc)


def remove_override(jeedom_eq_id: int, jeedom_cmd_id: int, data_dir: str) -> bool:
    """Remove a single override entry if present.

    Returns:
        True if the entry existed and was removed, False otherwise.
    """
    raw = _load_raw(data_dir)
    if raw is None:
        return False

    key = _override_key(jeedom_eq_id, jeedom_cmd_id)
    if key not in raw["overrides"]:
        return False

    del raw["overrides"][key]

    if not os.path.isdir(data_dir):
        _LOGGER.warning("[OVERRIDES] data_dir introuvable : %s — suppression non persistée", data_dir)
        return True

    path = _overrides_path(data_dir)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        _LOGGER.info("[OVERRIDES] Override supprimé : %s dans %s", key, path)
    except OSError as exc:
        _LOGGER.error("[OVERRIDES] Échec sauvegarde après suppression : %s", exc)

    return True
