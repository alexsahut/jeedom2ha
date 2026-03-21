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
                result[eq_id] = {
                    "entity_type": str(value.get("entity_type", "") or ""),
                    "published": bool(value.get("published", False)),
                    "ha_name": str(value.get("ha_name", "") or ""),        # BC: absent in 5.1
                    "suggested_area": value.get("suggested_area", None),   # BC: absent in 5.1
                }
            except (ValueError, TypeError):
                continue

        _LOGGER.info("[CACHE] Cache disque chargé : %d entrées", len(result))
        return result

    except (json.JSONDecodeError, OSError, Exception) as exc:
        _LOGGER.info("[CACHE] Cache disque absent ou invalide — cold start (raison: %s)", type(exc).__name__)
        return {}
