"""disk_cache.py — Disk persistence for jeedom2ha publications.

Story 5.1: Warm-start cache to survive daemon restarts.
Story 5.2: Extended format with ha_name and suggested_area for lifecycle change detection.

The cache format is:
    {
        "<eq_id>": {
            "entity_type": "<type>",
            "published": <bool>,
            "ha_name": "<str>",
            "suggested_area": "<str | null>"
        }
    }

Keys are strings in JSON (JSON limitation); converted to int on load.
Backward compatible: caches written by Story 5.1 (without ha_name/suggested_area) are loaded
with ha_name="" and suggested_area=None defaults — no error, no warning.
This module only handles save/load — publishing decisions come from app["publications"] in RAM.
"""
import json
import logging
import os
from typing import Dict

_LOGGER = logging.getLogger(__name__)
_CACHE_FILENAME = "jeedom2ha_cache.json"


def _extract_node_ids(mapping_result) -> list:
    """Collect node-scoped topic identifiers (multi-sensor) from a mapping result.

    Returns the node_id of the primary (if node-scoped) plus each secondary's node_id.
    Empty for mono-entity eqLogics (no node_id in reason_details).

    Story 11.2 — cas MULTI-DOMAINE hétérogène (switch + sensor + binary_sensor) :
    chaque entité porte son propre domaine HA, donc on persiste des entrées
    ``{"entity_type": ..., "node_id": ...}`` (JSON) couvrant toutes les entités, switch
    primaire eq-level inclus. Au boot, ``unpublish_by_eq_id`` les efface chacune dans
    son bon domaine. Le cas homogène conserve le contrat list[str] (Story 11.1.bis).
    Doit rester aligné avec ``transport.http_server._collect_unpublish_node_ids``.
    """
    if mapping_result is None:
        return []

    def _nid(m) -> "str | None":
        rd = getattr(m, "reason_details", None) or {}
        nid = rd.get("node_id")
        return nid if isinstance(nid, str) and nid else None

    def _etype(m) -> str:
        return str(getattr(m, "ha_entity_type", "") or "")

    secondaries = list(getattr(mapping_result, "additional_mappings", None) or [])
    all_types = {_etype(mapping_result)} | {_etype(s) for s in secondaries}

    if len(all_types) > 1:
        eq_id = getattr(mapping_result, "jeedom_eq_id", None)
        entries: list = []
        primary_nid = _nid(mapping_result) or f"jeedom2ha_{eq_id}"
        entries.append({"entity_type": _etype(mapping_result), "node_id": primary_nid})
        for secondary in secondaries:
            sec_nid = _nid(secondary) or f"jeedom2ha_{getattr(secondary, 'jeedom_eq_id', eq_id)}"
            entries.append({"entity_type": _etype(secondary), "node_id": sec_nid})
        return entries

    node_ids: list = []
    primary_nid = _nid(mapping_result)
    if primary_nid:
        node_ids.append(primary_nid)
    for secondary in secondaries:
        sec_nid = _nid(secondary)
        if sec_nid:
            node_ids.append(sec_nid)
    return node_ids


def _normalize_loaded_node_ids(raw_node_ids) -> list:
    """Normalize persisted node_ids into the unpublish contract.

    - plain string  -> kept as string (homogeneous multi-sensor, Story 11.1.bis)
    - {"entity_type","node_id"} or [type, nid] -> (entity_type, node_id) tuple
      (heterogeneous multi-domain, Story 11.2)
    Anything malformed is skipped (no ghost, no crash).
    """
    if not isinstance(raw_node_ids, list):
        return []
    normalized: list = []
    for n in raw_node_ids:
        if isinstance(n, str) and n:
            normalized.append(n)
        elif isinstance(n, dict):
            etype = str(n.get("entity_type", "") or "")
            nid = str(n.get("node_id", "") or "")
            if etype and nid:
                normalized.append((etype, nid))
        elif isinstance(n, (list, tuple)) and len(n) == 2:
            etype = str(n[0] or "")
            nid = str(n[1] or "")
            if etype and nid:
                normalized.append((etype, nid))
    return normalized


def save_publications_cache(publications: dict, data_dir: str) -> None:
    """Persist the current publications dict to disk.

    Args:
        publications: Dict[int, PublicationDecision] — from app["publications"].
        data_dir: Absolute path to the data directory (must already exist).
    """
    cache_path = os.path.join(data_dir, _CACHE_FILENAME)
    cache: Dict[str, dict] = {}

    for eq_id, decision in publications.items():
        entity_type = ""
        mapping_result = getattr(decision, "mapping_result", None)
        if mapping_result is not None:
            entity_type = str(getattr(mapping_result, "ha_entity_type", "") or "")
        published = bool(getattr(decision, "discovery_published", False))
        ha_name = str(getattr(mapping_result, "ha_name", "") or "") if mapping_result is not None else ""
        suggested_area = getattr(mapping_result, "suggested_area", None) if mapping_result is not None else None
        cache[str(eq_id)] = {
            "entity_type": entity_type,
            "published": published,
            "ha_name": ha_name,
            "suggested_area": suggested_area,
            # Story 11.1.bis — node_ids node-scoped (multi-sensor) pour une dépublication
            # exhaustive au boot sans re-parser la topologie. Vide pour le cas mono-entité.
            "node_ids": _extract_node_ids(mapping_result),
        }

    if not os.path.isdir(data_dir):
        _LOGGER.warning("[CACHE] data_dir introuvable : %s — cache non sauvegardé", data_dir)
        return

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        _LOGGER.info("[CACHE] Cache disque sauvegardé : %d entrées dans %s", len(cache), cache_path)
    except Exception as exc:
        _LOGGER.error("[CACHE] Échec sauvegarde cache disque : %s", exc)


def load_publications_cache(data_dir: str) -> Dict[int, dict]:
    """Load the publications cache from disk.

    Returns:
        Dict[int, dict] mapping eq_id (int) to:
            {"entity_type": str, "published": bool, "ha_name": str, "suggested_area": str | None}.
        Returns {} if file absent or corrupted (cold start).
        Backward-compatible: caches without ha_name/suggested_area (format 5.1) return
        ha_name="" and suggested_area=None for those entries.
    """
    cache_path = os.path.join(data_dir, _CACHE_FILENAME)

    if not os.path.exists(cache_path):
        _LOGGER.info("[CACHE] Cache disque absent ou invalide — cold start")
        return {}

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if not isinstance(raw, dict):
            _LOGGER.info("[CACHE] Cache disque absent ou invalide — cold start")
            return {}

        result: Dict[int, dict] = {}
        for key, value in raw.items():
            try:
                eq_id = int(key)
                if not isinstance(value, dict):
                    continue
                raw_node_ids = value.get("node_ids", None)   # BC: absent before 11.1.bis
                node_ids = _normalize_loaded_node_ids(raw_node_ids)
                result[eq_id] = {
                    "entity_type": str(value.get("entity_type", "") or ""),
                    "published": bool(value.get("published", False)),
                    "ha_name": str(value.get("ha_name", "") or ""),        # BC: absent in 5.1
                    "suggested_area": value.get("suggested_area", None),   # BC: absent in 5.1
                    "node_ids": node_ids,
                }
            except (ValueError, TypeError):
                continue

        _LOGGER.info("[CACHE] Cache disque chargé : %d entrées", len(result))
        return result

    except (json.JSONDecodeError, OSError, Exception) as exc:
        _LOGGER.info("[CACHE] Cache disque absent ou invalide — cold start (raison: %s)", type(exc).__name__)
        return {}
