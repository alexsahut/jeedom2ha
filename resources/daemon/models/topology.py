from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


def _to_bool(value: Union[bool, str, int, None], default: bool = True) -> bool:
    """Convert Jeedom-style booleans to Python bool.

    Jeedom may return '0'/'1' strings, ints 0/1, or actual booleans.
    Python's bool('0') is True, which is wrong for Jeedom semantics.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value not in ('0', '', 'false', 'False')
    return bool(value)

@dataclass
class JeedomObject:
    id: int
    name: str
    father_id: Optional[int] = None

@dataclass
class JeedomCmd:
    id: int
    name: str
    generic_type: Optional[str] = None
    type: str = "info"          # "info" ou "action"
    sub_type: str = "string"        # "binary", "numeric", "string", "slider", "color", "other"
    current_value: Any = None
    unit: Optional[str] = None
    is_visible: bool = True
    is_historized: bool = False

@dataclass
class JeedomEqLogic:
    id: int
    name: str
    object_id: Optional[int] = None
    is_enable: bool = True
    is_visible: bool = True
    eq_type_name: str = ""          # nom du plugin source (zwave, zigbee, virtual, etc.)
    generic_type: Optional[str] = None
    is_excluded: bool = False       # flag d'exclusion jeedom2ha
    cmds: List[JeedomCmd] = field(default_factory=list)

@dataclass
class EligibilityResult:
    is_eligible: bool
    reason_code: str                # stable code for diagnostic (e.g., "excluded_eqlogic")
    confidence: str = "unknown"     # "sure", "probable", "ambiguous", "ignore", "unknown"
    reason_details: Optional[Dict[str, Any]] = None

@dataclass
class TopologySnapshot:
    timestamp: str                                          # ISO 8601
    objects: Dict[int, JeedomObject] = field(default_factory=dict)
    eq_logics: Dict[int, JeedomEqLogic] = field(default_factory=dict)

    @classmethod
    def from_jeedom_payload(cls, payload: Dict[str, Any]) -> "TopologySnapshot":
        """
        Normalise le payload brut Jeedom en modèle canonique.
        Tolérant aux données manquantes, IDs string -> int, generic_type "" -> None.
        """
        objects_data = payload.get("objects", [])
        eq_logics_data = payload.get("eq_logics", [])
        
        objects = {}
        for obj_raw in objects_data:
            try:
                obj_id = int(obj_raw.get("id"))
                objects[obj_id] = JeedomObject(
                    id=obj_id,
                    name=str(obj_raw.get("name", f"Object {obj_id}")),
                    father_id=int(obj_raw["father_id"]) if obj_raw.get("father_id") is not None else None
                )
            except (ValueError, TypeError, KeyError):
                continue
                
        eq_logics = {}
        for eq_raw in eq_logics_data:
            try:
                eq_id = int(eq_raw.get("id"))
                
                cmds = []
                for cmd_raw in eq_raw.get("cmds", []):
                    try:
                        cmd_id = int(cmd_raw.get("id"))
                        cmds.append(JeedomCmd(
                            id=cmd_id,
                            name=str(cmd_raw.get("name", f"Cmd {cmd_id}")),
                            generic_type=cmd_raw.get("generic_type") or None,
                            type=str(cmd_raw.get("type", "info")),
                            sub_type=str(cmd_raw.get("sub_type", "other")),
                            current_value=cmd_raw.get("current_value"),
                            unit=cmd_raw.get("unit") or None,
                            is_visible=_to_bool(cmd_raw.get("is_visible"), default=True),
                            is_historized=_to_bool(cmd_raw.get("is_historized"), default=False)
                        ))
                    except (ValueError, TypeError, KeyError):
                        continue
                
                eq_logics[eq_id] = JeedomEqLogic(
                    id=eq_id,
                    name=str(eq_raw.get("name", f"Eq {eq_id}")),
                    object_id=int(eq_raw["object_id"]) if eq_raw.get("object_id") is not None else None,
                    is_enable=_to_bool(eq_raw.get("is_enable"), default=True),
                    is_visible=_to_bool(eq_raw.get("is_visible"), default=True),
                    eq_type_name=str(eq_raw.get("eq_type", "")),
                    generic_type=eq_raw.get("generic_type") or None,
                    is_excluded=_to_bool(eq_raw.get("is_excluded"), default=False),
                    cmds=cmds
                )
            except (ValueError, TypeError, KeyError):
                continue
                
        return cls(
            timestamp=payload.get("timestamp", datetime.now().isoformat()),
            objects=objects,
            eq_logics=eq_logics
        )

    def get_suggested_area(self, eq_id: int) -> Optional[str]:
        """Retourne le nom de l'objet Jeedom associé, ou None."""
        eq = self.eq_logics.get(eq_id)
        if eq and eq.object_id and eq.object_id in self.objects:
            return self.objects[eq.object_id].name
        return None

def assess_eligibility(eq: JeedomEqLogic) -> EligibilityResult:
    """
    Évalue l'éligibilité d'un équipement selon les règles métier.
    Ordre de priorité : Exclu > Désactivé > Sans commandes > Sans type générique.
    """
    if eq.is_excluded:
        return EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic", confidence="sure")

    if not eq.is_enable:
        return EligibilityResult(is_eligible=False, reason_code="disabled_eqlogic", confidence="sure")

    if not eq.cmds:
        return EligibilityResult(is_eligible=False, reason_code="no_commands", confidence="sure")

    # Vérifie si au moins une commande possède un type générique
    has_generic_type = any(cmd.generic_type is not None for cmd in eq.cmds)
    if not has_generic_type:
        return EligibilityResult(is_eligible=False, reason_code="no_supported_generic_type", confidence="sure")

    return EligibilityResult(is_eligible=True, reason_code="eligible", confidence="unknown")

def assess_all(snapshot: TopologySnapshot) -> Dict[int, EligibilityResult]:
    """Évalue l'éligibilité de tous les équipements d'un snapshot."""
    return {eq_id: assess_eligibility(eq) for eq_id, eq in snapshot.eq_logics.items()}
