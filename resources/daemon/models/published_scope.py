"""Canonical published-scope resolver for V1.1 (global -> piece -> equipement)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from models.topology import TopologySnapshot

STATE_INHERIT = "inherit"
STATE_INCLUDE = "include"
STATE_EXCLUDE = "exclude"
_SUPPORTED_STATES = {STATE_INHERIT, STATE_INCLUDE, STATE_EXCLUDE}


def normalize_scope_state(raw_state: Any, default: str = STATE_INHERIT) -> str:
    """Normalize a raw scope state to inherit/include/exclude with deterministic fallback."""
    if isinstance(raw_state, str):
        normalized = raw_state.strip().lower()
        if normalized in _SUPPORTED_STATES:
            return normalized
    return default


def _extract_raw_state(entry: Any) -> Any:
    """Accept both {'raw_state': '...'} entries and plain state values."""
    if isinstance(entry, dict):
        return entry.get("raw_state")
    return entry


def _extract_scope_entry(entry: Any) -> tuple[Any, Any]:
    """Extract (raw_state, source) from scope entries."""
    if isinstance(entry, dict):
        return entry.get("raw_state"), entry.get("source")
    return entry, None


def _state_entry_by_id(scope_map: Any, identifier: int) -> tuple[Any, Any]:
    if not isinstance(scope_map, dict):
        return None, None
    if identifier in scope_map:
        return _extract_scope_entry(scope_map.get(identifier))
    return _extract_scope_entry(scope_map.get(str(identifier)))


def _normalized_state_and_explicit(scope_map: Any, identifier: int) -> tuple[str, bool]:
    raw_state, source = _state_entry_by_id(scope_map, identifier)
    normalized_state = normalize_scope_state(raw_state, default=STATE_INHERIT)
    has_supported_raw_state = (
        isinstance(raw_state, str) and raw_state.strip().lower() in _SUPPORTED_STATES
    )
    source_value = source.strip().lower() if isinstance(source, str) else ""

    # getFullTopology pre-remplit "inherit/default_inherit" pour chaque pièce/équipement:
    # ce cas n'est pas une règle utilisateur explicite et doit conserver les fallbacks legacy.
    is_default_inherit_marker = (
        normalized_state == STATE_INHERIT and source_value == "default_inherit"
    )
    is_explicit = has_supported_raw_state and not is_default_inherit_marker
    return normalized_state, is_explicit


def _new_counts() -> Dict[str, int]:
    return {
        "total": 0,
        "include": 0,
        "exclude": 0,
        "exceptions": 0,
    }


def _effective_from_root(global_state: str) -> str:
    # Root cannot inherit from an upper level. Keep include as deterministic baseline.
    return STATE_INCLUDE if global_state == STATE_INHERIT else global_state


def resolve_published_scope(
    snapshot: TopologySnapshot,
    raw_scope: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve canonical effective states with strict precedence equipement > piece > global."""
    raw_scope = raw_scope or {}

    global_raw = _extract_raw_state(raw_scope.get("global"))
    global_state = normalize_scope_state(global_raw, default=STATE_INHERIT)
    global_effective = _effective_from_root(global_state)

    raw_pieces = raw_scope.get("pieces", {})
    raw_equipements = raw_scope.get("equipements", {})
    if not raw_equipements and isinstance(raw_scope.get("equipments"), dict):
        raw_equipements = raw_scope.get("equipments", {})

    legacy_excluded_pieces = {
        (eq.object_id if eq.object_id is not None else 0)
        for eq in snapshot.eq_logics.values()
        if eq.is_excluded and eq.exclusion_source == "object"
    }

    global_counts = _new_counts()
    piece_entries: Dict[int, Dict[str, Any]] = {}
    equipement_entries = []

    for eq_id in sorted(snapshot.eq_logics.keys()):
        eq = snapshot.eq_logics[eq_id]
        piece_id = eq.object_id if eq.object_id is not None else 0

        piece_state, piece_explicit = _normalized_state_and_explicit(raw_pieces, piece_id)
        if (
            piece_state == STATE_INHERIT
            and not piece_explicit
            and piece_id in legacy_excluded_pieces
        ):
            # Compatibilité technique testée: exclusion historique par objet => pièce "exclude".
            piece_state = STATE_EXCLUDE
        piece_effective = global_effective if piece_state == STATE_INHERIT else piece_state

        eq_state, eq_explicit = _normalized_state_and_explicit(raw_equipements, eq_id)
        if (
            eq_state == STATE_INHERIT
            and not eq_explicit
            and eq.is_excluded
            and eq.exclusion_source in {"eqlogic", "plugin"}
        ):
            # Compatibilité technique testée: exclusions legacy eqlogic/plugin => équipement "exclude".
            eq_state = STATE_EXCLUDE

        if eq_state == STATE_INHERIT:
            effective_state = piece_effective
            decision_source = "piece" if piece_state != STATE_INHERIT else "global"
            is_exception = False
        else:
            effective_state = eq_state
            if piece_effective != eq_state:
                decision_source = "exception_equipement"
                is_exception = True
            else:
                decision_source = "equipement"
                is_exception = False

        global_counts["total"] += 1
        global_counts[effective_state] += 1
        if is_exception:
            global_counts["exceptions"] += 1

        if piece_id not in piece_entries:
            if piece_id == 0:
                object_name = "Aucun"
            else:
                obj = snapshot.objects.get(piece_id)
                object_name = obj.name if obj is not None else "Aucun"
            home_perimetre = "Incluse" if piece_effective == STATE_INCLUDE else "Exclue"
            piece_entries[piece_id] = {
                "object_id": piece_id,
                "object_name": object_name,
                "counts": _new_counts(),
                "home_perimetre": home_perimetre,
                "has_pending_home_assistant_changes": False,
            }

        piece_counts = piece_entries[piece_id]["counts"]
        piece_counts["total"] += 1
        piece_counts[effective_state] += 1
        if is_exception:
            piece_counts["exceptions"] += 1

        equipement_entries.append(
            {
                "eq_id": eq_id,
                "name": eq.name or "",
                "object_id": piece_id,
                "effective_state": effective_state,
                "decision_source": decision_source,
                "is_exception": is_exception,
                "has_pending_home_assistant_changes": False,
            }
        )

    return {
        "global": {
            "raw_state": global_state,
            "effective_state": global_effective,
            "counts": global_counts,
            "has_pending_home_assistant_changes": False,
        },
        "pieces": [piece_entries[piece_id] for piece_id in sorted(piece_entries.keys())],
        "equipements": equipement_entries,
    }
