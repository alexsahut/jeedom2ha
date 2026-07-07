"""overrides.py — Story 16.1: persistance backend du schéma d'overrides utilisateur v1.

Persiste les overrides HA locaux (mapping candidat / décision, Story 16.2+) dans
`data/ha_overrides.json`, jamais dans le modèle topologie Jeedom (`JeedomCmd`/`JeedomEqLogic`
restent intouchés — D10). Ce module ne fait que lire/écrire ce fichier et ne dépend d'aucun
mapper concret (sens unique, D8). Depuis la Story 16.2, `apply_type_override` (lecture seule)
EST appelée par le pipeline de sync, entre l'étape 2 (`map`) et l'étape 3 (`validate_projection`)
— seules les écritures (`save_override`/`remove_override`) restent réservées à un futur handler
HTTP (Story 16.6) ou à une édition manuelle du JSON.

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
from dataclasses import replace
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime mapper dependency (D8)
    from models.mapping import MappingResult

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


def _mapping_cmd_ids(mapping: "MappingResult") -> List[int]:
    """Collect the Jeedom cmd_id(s) that a MappingResult covers, for override lookup.

    Order matters (deterministic first-match): a secondary sensor carries its own
    `cmd_id` in `reason_details` (multi-entity, Story 11.1) and is checked first ;
    then the cumulated `commands` dict of a primary mapping.
    """
    cmd_ids: List[int] = []
    reason_details = mapping.reason_details or {}
    rd_cmd_id = reason_details.get("cmd_id")
    if isinstance(rd_cmd_id, int) and not isinstance(rd_cmd_id, bool):
        cmd_ids.append(rd_cmd_id)
    for cmd in (mapping.commands or {}).values():
        cmd_id = getattr(cmd, "id", None)
        if isinstance(cmd_id, int) and not isinstance(cmd_id, bool) and cmd_id not in cmd_ids:
            cmd_ids.append(cmd_id)
    return cmd_ids


def apply_type_override(
    mapping: "MappingResult",
    data_dir: str,
    *,
    overrides: Optional[Dict[str, dict]] = None,
) -> "MappingResult":
    """Apply a persisted HA-type override to a mapping candidate (D8/D10/D11).

    Returns a PATCHED COPY of `mapping` (via `dataclasses.replace`) when a user override
    matches one of the mapping's commands ; otherwise returns the SAME object unchanged.

    Contract:
    - Never mutates the source `MappingResult`, nor the Jeedom topology (`JeedomCmd` /
      `JeedomEqLogic` `generic_type` stay native — D10). The patch only touches
      `ha_entity_type` on the copy ; `capabilities` are kept as detected so that the
      downstream `validate_projection()` (pipeline step 3) still judges the OVERRIDDEN
      type against the real capabilities — an incompatible override therefore fails
      validation instead of bypassing it (D11, no bypass).
    - No dependency on concrete mappers (one-way, D8) : selection is driven purely by the
      persisted override file, never by re-running the mapping engine.
    - Diagnostic honesty: on a match, `reason_details` gains the inseparable pair
      `override_applied: True` + `override_source: "<source>"` ; absent otherwise (no null keys).
    - Performance: a sync cycle calls this once per mapped equipment (and once per
      secondary sensor). Pass `overrides=` with an already-loaded `list_overrides(data_dir)`
      dict to avoid re-reading/re-parsing `ha_overrides.json` from disk on every call ; if
      omitted, this function loads it itself (used by direct/unit-test callers).
    """
    if overrides is None:
        overrides = list_overrides(data_dir)
    if not overrides:
        return mapping

    eq_id = mapping.jeedom_eq_id
    for cmd_id in _mapping_cmd_ids(mapping):
        entry = overrides.get(_override_key(eq_id, cmd_id))
        if not entry:
            continue
        forced_type = entry.get("ha_entity_type")
        if not isinstance(forced_type, str) or not forced_type:
            _LOGGER.warning(
                "[OVERRIDES] Override %s sans 'ha_entity_type' exploitable — ignoré",
                _override_key(eq_id, cmd_id),
            )
            continue

        source = entry.get("source", "user")
        patched_reason_details = dict(mapping.reason_details or {})
        patched_reason_details["override_applied"] = True
        patched_reason_details["override_source"] = source

        _LOGGER.info(
            "[OVERRIDES] Override appliqué eq_id=%d cmd_id=%d : %s → %s (source=%s)",
            eq_id, cmd_id, mapping.ha_entity_type, forced_type, source,
        )
        return replace(
            mapping,
            ha_entity_type=forced_type,
            reason_details=patched_reason_details,
        )

    return mapping


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
