"""overrides.py — Story 16.1-16.3: persistance backend du schéma d'overrides utilisateur.

Persiste les overrides HA locaux (mapping candidat / décision, Story 16.2+ ; politique de
publication, Story 16.3+) dans `data/ha_overrides.json`, jamais dans le modèle topologie
Jeedom (`JeedomCmd`/`JeedomEqLogic` restent intouchés — D10). Ce module ne fait que lire/
écrire ce fichier et ne dépend d'aucun mapper concret (sens unique, D8). Depuis la Story 16.2,
`apply_type_override` (lecture seule) EST appelée par le pipeline de sync, entre l'étape 2
(`map`) et l'étape 3 (`validate_projection`) ; depuis la Story 16.3, `resolve_publication_override`
(lecture seule, pure) EST résolue par l'appelant (`http_server.py`) et passée à l'étape 4
(`decide_publication`) — seules les écritures (`save_override`/`save_equipment_override`/
`remove_override`/`remove_equipment_override`) restent réservées à un futur handler HTTP
(Story 16.6) ou à une édition manuelle du JSON.

Format v2 (D9, Story 16.3 — SCP 2026-07-07) :
    {
        "schema_version": 2,
        "overrides": {
            "<jeedom_eq_id>:<jeedom_cmd_id>": {
                "source": "user", "ha_entity_type": "...", "publication_override": "exclude" | "force_publish" | null
            }
        },
        "equipment_overrides": {
            "<jeedom_eq_id>": {"source": "user", "publication_override": "exclude" | "force_publish"}
        }
    }

Un fichier v1 (Story 16.1/16.2, sans clé `equipment_overrides`) reste lisible tel quel :
migration transparente en mémoire (`equipment_overrides` par défaut `{}`), jamais de
réécriture disque depuis un chemin de lecture pure — le bump vers `schema_version: 2` sur
disque n'intervient qu'au prochain `save_override`/`save_equipment_override`/`remove_override`/
`remove_equipment_override` (D9/D11, aucune migration silencieuse déclenchée par une lecture).

Contrairement à `cache/disk_cache.py` (cold-start silencieux `{}` sur fichier absent/corrompu),
un `schema_version` absent, non entier ou non supporté (hors `{1, 2}`) est un refus explicite
avec diagnostic loggé — un override ne doit jamais s'appliquer silencieusement sur un schéma
inconnu (D9/D11).
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
_SCHEMA_VERSION = 2
_SUPPORTED_SCHEMA_VERSIONS = (1, 2)


def _overrides_path(data_dir: str) -> str:
    return os.path.join(data_dir, _OVERRIDES_FILENAME)


def _override_key(jeedom_eq_id: int, jeedom_cmd_id: int) -> str:
    return f"{jeedom_eq_id}:{jeedom_cmd_id}"


# Story 16.7 (AC5/AC6) — champs sémantiques de mapping autorisés dans un profil partageable.
# Whitelist (jamais blacklist) : un champ inconnu ajouté par une édition manuelle de
# `ha_overrides.json` (identifiant machine, chemin, hostname, token/localSecret, donnée
# personnelle) ne peut pas fuiter dans un profil exporté ni s'injecter à l'import.
_PROFILE_COMMAND_FIELDS = ("source", "ha_entity_type", "publication_override")
_PROFILE_EQUIPMENT_FIELDS = ("source", "publication_override")


def _sanitize_profile_entry(entry: dict, allowed_fields) -> dict:
    """Keep only the whitelisted mapping-semantic fields of an override entry (Story 16.7).

    `None` values are dropped : a portable profile carries no null noise, and an absent
    `publication_override` is semantically identical to `None` (no override).
    """
    return {
        field: entry[field]
        for field in allowed_fields
        if field in entry and entry[field] is not None
    }


def _parse_override_key(key: str) -> tuple:
    """Parse a composite command key 'eq_id:cmd_id' back to (int, int) (Story 16.7 import)."""
    try:
        eq_str, cmd_str = str(key).split(":", 1)
        return int(eq_str), int(cmd_str)
    except (ValueError, AttributeError):
        raise ValueError(f"[OVERRIDES] Clé d'override composite invalide : {key!r}")


def _parse_equipment_key(key: str) -> int:
    """Parse an equipment key 'eq_id' back to int (Story 16.7 import)."""
    try:
        return int(key)
    except (ValueError, TypeError):
        raise ValueError(f"[OVERRIDES] Clé d'override équipement invalide : {key!r}")


def _load_raw(data_dir: str) -> Optional[Dict]:
    """Load and validate the overrides file.

    Returns a fresh `{"schema_version": 2, "overrides": {}, "equipment_overrides": {}}`
    if the file does not exist yet (expected on first save — not a schema error).
    Returns None — with an explicit `_LOGGER.error(...)` — if the file exists but is
    corrupted, malformed, or carries an unsupported `schema_version` (outside {1, 2}).

    A v1 file (no `equipment_overrides` key) is accepted as-is (`schema_version` stays
    `1` in the returned dict) with `equipment_overrides` synthesized to `{}` in memory —
    transparent migration, no disk rewrite from this read-only path (D9/D11).
    """
    path = _overrides_path(data_dir)

    if not os.path.exists(path):
        return {"schema_version": _SCHEMA_VERSION, "overrides": {}, "equipment_overrides": {}}

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
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version not in _SUPPORTED_SCHEMA_VERSIONS
    ):
        _LOGGER.error(
            "[OVERRIDES] schema_version invalide ou non supportée (%r) dans %s — override refusé",
            schema_version, path,
        )
        return None

    overrides = raw.get("overrides")
    if not isinstance(overrides, dict):
        _LOGGER.error("[OVERRIDES] Clé 'overrides' absente ou invalide dans %s", path)
        return None

    equipment_overrides = raw.get("equipment_overrides", {})
    if not isinstance(equipment_overrides, dict):
        _LOGGER.error("[OVERRIDES] Clé 'equipment_overrides' invalide dans %s", path)
        return None

    return {
        "schema_version": schema_version,
        "overrides": overrides,
        "equipment_overrides": equipment_overrides,
    }


def list_overrides(data_dir: str) -> Dict[str, dict]:
    """Return all persisted command-level overrides keyed by 'jeedom_eq_id:jeedom_cmd_id'.

    Returns {} if the file is absent, OR if its schema is invalid/unsupported
    (diagnostic already logged by `_load_raw`).
    """
    raw = _load_raw(data_dir)
    if raw is None:
        return {}
    return dict(raw["overrides"])


def list_equipment_overrides(data_dir: str) -> Dict[str, dict]:
    """Return all persisted equipment-level overrides keyed by 'jeedom_eq_id' (Story 16.3).

    Separate section from `list_overrides` (SCP 2026-07-07 — no mixed key formats in a
    single dict). Returns {} if the file is absent, OR if its schema is invalid/unsupported
    (diagnostic already logged by `_load_raw`).
    """
    raw = _load_raw(data_dir)
    if raw is None:
        return {}
    return dict(raw["equipment_overrides"])


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
    raw["schema_version"] = _SCHEMA_VERSION  # migration transparente v1 → v2 au premier write

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


def save_equipment_override(jeedom_eq_id: int, override: dict, data_dir: str) -> None:
    """Persist a single equipment-level override, merging with any existing entries (Story 16.3).

    Adds `"source": "user"` if not already present in `override`. Separate section from
    `save_override` (SCP 2026-07-07 — key is `eq_id` alone, no `cmd_id`).

    Raises:
        ValueError: if the existing file has an invalid/unsupported `schema_version` —
            never silently overwritten (D9/D11 — no bypass of a broken/unknown schema).
    """
    raw = _load_raw(data_dir)
    if raw is None:
        raise ValueError(
            f"Impossible de sauvegarder l'override équipement {jeedom_eq_id} — "
            f"fichier d'overrides existant invalide ou schema_version non supportée"
        )

    entry = dict(override)
    entry.setdefault("source", "user")
    raw["equipment_overrides"][str(jeedom_eq_id)] = entry
    raw["schema_version"] = _SCHEMA_VERSION  # migration transparente v1 → v2 au premier write

    if not os.path.isdir(data_dir):
        _LOGGER.warning("[OVERRIDES] data_dir introuvable : %s — override non sauvegardé", data_dir)
        return

    path = _overrides_path(data_dir)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        _LOGGER.info(
            "[OVERRIDES] Override équipement sauvegardé : %s dans %s", jeedom_eq_id, path,
        )
    except OSError as exc:
        _LOGGER.error("[OVERRIDES] Échec sauvegarde override équipement : %s", exc)


def mapping_cmd_ids(mapping: "MappingResult") -> List[int]:
    """Collect the Jeedom cmd_id(s) that a MappingResult covers, for override lookup.

    Order matters (deterministic first-match): a secondary sensor carries its own
    `cmd_id` in `reason_details` (multi-entity, Story 11.1) and is checked first ;
    then the cumulated `commands` dict of a primary mapping.

    Public since Story 16.3 (was `_mapping_cmd_ids`) : reused by `http_server.py` to derive
    the candidate cmd_id(s) for `resolve_publication_override(eq_id, cmd_id, ...)`, avoiding
    a second, duplicated cmd_id-extraction implementation outside this module.
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
    for cmd_id in mapping_cmd_ids(mapping):
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
    raw["schema_version"] = _SCHEMA_VERSION  # migration transparente v1 → v2 au premier write

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


def remove_equipment_override(jeedom_eq_id: int, data_dir: str) -> bool:
    """Remove a single equipment-level override entry if present (Story 16.3).

    Returns:
        True if the entry existed and was removed, False otherwise.
    """
    raw = _load_raw(data_dir)
    if raw is None:
        return False

    key = str(jeedom_eq_id)
    if key not in raw["equipment_overrides"]:
        return False

    del raw["equipment_overrides"][key]
    raw["schema_version"] = _SCHEMA_VERSION  # migration transparente v1 → v2 au premier write

    if not os.path.isdir(data_dir):
        _LOGGER.warning("[OVERRIDES] data_dir introuvable : %s — suppression non persistée", data_dir)
        return True

    path = _overrides_path(data_dir)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        _LOGGER.info("[OVERRIDES] Override équipement supprimé : %s dans %s", key, path)
    except OSError as exc:
        _LOGGER.error("[OVERRIDES] Échec sauvegarde après suppression équipement : %s", exc)

    return True


def resolve_publication_override(
    jeedom_eq_id: int,
    jeedom_cmd_id: int,
    overrides: Dict[str, dict],
    equipment_overrides: Dict[str, dict],
) -> Optional[str]:
    """Resolve the effective publication-policy override for one eq/cmd pair (AC1/AC2, D8).

    Pure function (prefix `resolve_*`, never `apply_*`) : no I/O, no mutation of any
    pipeline object, no dependency on concrete mappers or `models/topology.py` (D8/D10).
    Receives already-loaded dicts — same contract as `list_overrides`/`apply_type_override`
    (call once per sync cycle, reuse the cached dicts, never re-read disk per equipment).

    Returns `None` if no publication override applies (silent no-op, non-regression — same
    contract as `list_overrides`).

    Precedence (SCP 2026-07-07, tranché) :
        1. `equipment_overrides[eq_id].publication_override == "exclude"` → veto absolu.
        2. Sinon override de **commande** (`overrides[eq_id:cmd_id].publication_override`),
           le plus spécifique.
        3. Sinon `force_publish` équipement en défaut.
        4. Sinon `None`.

    Return values are the RESOLVED decision, not the raw persisted literal : `"exclude"` is
    disambiguated into `"exclude_eqlogic"` / `"exclude_command"` so the caller (`decide_publication`)
    can select the correct dedicated `reason` (`publication_excluded_eqlogic` vs.
    `publication_excluded_command`, Task 4) without re-inspecting the override dicts itself.
    `"force_publish"` is returned as-is (equipment-level only, no command-level `force_publish`
    per the precedence rule above).
    """
    equipment_entry = equipment_overrides.get(str(jeedom_eq_id))
    if equipment_entry and equipment_entry.get("publication_override") == "exclude":
        return "exclude_eqlogic"

    command_entry = overrides.get(_override_key(jeedom_eq_id, jeedom_cmd_id))
    if command_entry:
        command_override = command_entry.get("publication_override")
        if command_override == "exclude":
            return "exclude_command"
        if command_override == "force_publish":
            return "force_publish"

    if equipment_entry and equipment_entry.get("publication_override") == "force_publish":
        return "force_publish"

    return None


def export_profile(data_dir: str) -> dict:
    """Export the persisted overrides as an anonymisable, shareable profile (Story 16.7 / AC5).

    Pure read path : reuses `_load_raw` (no write, no `sync`/`transport`/MQTT). Returns a
    profile dict `{"schema_version", "overrides", "equipment_overrides"}` carrying ONLY the
    mapping semantics, indexed by the composite keys `eq_id:cmd_id` (commands) / `eq_id`
    (equipment). Each entry is whitelisted to the known mapping fields (`_PROFILE_*_FIELDS`)
    so no secret / hostname / absolute path / machine id can leak into the profile — even if
    `ha_overrides.json` was hand-edited with extra keys.

    Never mutates the Jeedom topology nor the `generic_type` native (D10) : the profile only
    carries the jeedom2ha override layer, indexed by Jeedom IDs. Returns a well-formed empty
    profile if the overrides file is absent, invalid or carries an unsupported schema_version
    (diagnostic already logged by `_load_raw`).
    """
    raw = _load_raw(data_dir)
    if raw is None:
        return {"schema_version": _SCHEMA_VERSION, "overrides": {}, "equipment_overrides": {}}

    return {
        "schema_version": raw["schema_version"],
        "overrides": {
            key: _sanitize_profile_entry(entry, _PROFILE_COMMAND_FIELDS)
            for key, entry in raw["overrides"].items()
            if isinstance(entry, dict)
        },
        "equipment_overrides": {
            key: _sanitize_profile_entry(entry, _PROFILE_EQUIPMENT_FIELDS)
            for key, entry in raw["equipment_overrides"].items()
            if isinstance(entry, dict)
        },
    }


def import_profile(profile: dict, data_dir: str) -> None:
    """Import a shared overrides profile, reusing the versioned-schema refusal contract (AC6).

    Validates `profile["schema_version"]` against `_SUPPORTED_SCHEMA_VERSIONS` : an absent,
    non-integer or unsupported version is refused explicitly (`ValueError`), never a silent
    cold-start (same contract as `_load_raw` — no `disk_cache`-style fallback). Writes
    exclusively through the existing persistence primitives (`save_override` /
    `save_equipment_override`) — no parallel write path — and performs no `sync`/`transport`/
    MQTT call (import only reads the profile and writes the file, D8). Imported entries are
    re-whitelisted so a malicious/hand-edited profile cannot inject secret keys locally.

    Raises:
        ValueError: on an invalid/unsupported `schema_version`, or a malformed profile body.
    """
    if not isinstance(profile, dict):
        raise ValueError("[OVERRIDES] Profil d'import invalide (racine non-objet)")

    schema_version = profile.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version not in _SUPPORTED_SCHEMA_VERSIONS
    ):
        raise ValueError(
            f"[OVERRIDES] schema_version de profil invalide ou non supportée "
            f"({schema_version!r}) — import refusé"
        )

    overrides = profile.get("overrides", {})
    equipment_overrides = profile.get("equipment_overrides", {})
    if not isinstance(overrides, dict) or not isinstance(equipment_overrides, dict):
        raise ValueError(
            "[OVERRIDES] Profil d'import invalide (sections 'overrides'/'equipment_overrides')"
        )

    for key, entry in overrides.items():
        if not isinstance(entry, dict):
            raise ValueError(f"[OVERRIDES] Entrée d'override de profil invalide : {key!r}")
        eq_id, cmd_id = _parse_override_key(key)
        save_override(eq_id, cmd_id, _sanitize_profile_entry(entry, _PROFILE_COMMAND_FIELDS), data_dir)

    for key, entry in equipment_overrides.items():
        if not isinstance(entry, dict):
            raise ValueError(f"[OVERRIDES] Entrée d'override équipement de profil invalide : {key!r}")
        eq_id = _parse_equipment_key(key)
        save_equipment_override(eq_id, _sanitize_profile_entry(entry, _PROFILE_EQUIPMENT_FIELDS), data_dir)
