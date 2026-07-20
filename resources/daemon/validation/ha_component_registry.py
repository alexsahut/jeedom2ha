"""ha_component_registry.py - Registre statique des composants HA connus.

Trois etats distincts (AR6) :
  - connu    : entree presente dans HA_COMPONENT_REGISTRY (contraintes modelisees)
  - validable: validate_projection() aboutit positivement sur cas nominaux (Story 3.2)
  - ouvert   : present dans PRODUCT_SCOPE apres satisfaction simultanee de FR40 (Story 3.3)

Dependances : models.mapping uniquement (AR3). Ce module ne doit pas importer depuis
mapping/, discovery/ ni transport/.
"""

from __future__ import annotations

from typing import List

from models.mapping import (
    AlarmCapabilities,
    ClimateCapabilities,
    CoverCapabilities,
    LightCapabilities,
    ProjectionValidity,
    SensorCapabilities,
    SwitchCapabilities,
)

HA_COMPONENT_REGISTRY = {
    "light": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "cover": {
        "required_fields": ["platform", "availability"],
        "required_capabilities": [],
    },
    "switch": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    # Vague cible pe-epic-7 : composants connus, non ouverts dans PRODUCT_SCOPE.
    "sensor": {
        "required_fields": ["state_topic", "platform", "availability"],
        "required_capabilities": ["has_state"],
    },
    "binary_sensor": {
        "required_fields": ["state_topic", "platform", "availability"],
        "required_capabilities": ["has_state"],
    },
    "button": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "number": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "select": {
        "required_fields": ["command_topic", "options", "platform", "availability"],
        "required_capabilities": ["has_command", "has_options"],
    },
    "climate": {
        "required_fields": ["availability"],
        "required_capabilities": ["has_setpoint"],
    },
    "alarm_control_panel": {
        "required_fields": ["state_topic", "command_topic", "platform", "availability"],
        "required_capabilities": ["has_state", "has_command"],
    },
}

PRODUCT_SCOPE = ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"]  # climate ouvert Story 10.2 sous FR40/NFR10 # alarm_control_panel ouvert Story 10.3 sous FR40/NFR10
# AR13 : toute modification de PRODUCT_SCOPE exige simultanement dans le meme increment :
#   (1) entree dans HA_COMPONENT_REGISTRY avec required_fields + required_capabilities,
#   (2) au moins un cas nominal + un cas d'echec validate_projection() pour ce type,
#   (3) test de non-regression du contrat 4D passant.


# ---------------------------------------------------------------------------
# Résolution des capabilities abstraites → valeurs concrètes (Story 3.2)
# ---------------------------------------------------------------------------

# Priorité déterministe pour le reason_code quand plusieurs capabilities manquent.
# Ordre : ha_missing_required_option > ha_missing_state_topic > ha_missing_command_topic > ha_missing_temperature_command_topic
_REASON_PRIORITY: List[str] = [
    "ha_missing_required_option",
    "ha_missing_state_topic",
    "ha_missing_command_topic",
    "ha_missing_temperature_command_topic",
]

# Correspondance capability abstraite → (reason_code, missing_fields)
_CAPABILITY_TO_REASON = {
    "has_command":  ("ha_missing_command_topic",             ["command_topic"]),
    "has_state":    ("ha_missing_state_topic",               ["state_topic"]),
    "has_options":  ("ha_missing_required_option",           ["options"]),
    "has_setpoint": ("ha_missing_temperature_command_topic", ["temperature_command_topic"]),
}


def _resolve_capability(abstract: str, capabilities: object) -> bool:
    """Résout une capability abstraite du registre vers sa valeur concrète.

    Utilise isinstance pour les dataclasses connues afin d'éviter les
    collisions sémantiques. Fallback getattr pour les types futurs.
    Fonction pure — aucun effet de bord.
    """
    if abstract == "has_command":
        if isinstance(capabilities, LightCapabilities):
            return capabilities.has_on_off
        if isinstance(capabilities, CoverCapabilities):
            return capabilities.has_open_close
        if isinstance(capabilities, SwitchCapabilities):
            return capabilities.has_on_off
        # Fallback pour les capabilities futures non encore dataclassées
        return bool(
            getattr(capabilities, "has_on_off", False)
            or getattr(capabilities, "has_command", False)
        )
    if abstract == "has_state":
        if isinstance(capabilities, SensorCapabilities):
            return capabilities.has_state
        return bool(getattr(capabilities, "has_state", False))
    if abstract == "has_options":
        return bool(getattr(capabilities, "has_options", False))
    if abstract == "has_setpoint":
        if isinstance(capabilities, ClimateCapabilities):
            return capabilities.has_setpoint
        return bool(getattr(capabilities, "has_setpoint", False))
    # Capability abstraite inconnue — non satisfaite par précaution
    return False


def _cross_family_action_mismatch(ha_entity_type: str, capabilities: object) -> bool:
    """Détecte un override cross-type dont la famille de commande est non routable (Story 16.7, Codex P1).

    `has_command` se résout à True à travers les familles (un cover via `has_open_close`, un
    light/switch via `has_on_off`), si bien qu'un override cross-type peut passer la
    vérification générique de capability tout en étant impilotable : `_translate_command`
    (`sync/command.py`) ne route un light/switch que via des commandes ON/OFF
    (`LIGHT_ON/OFF`, `SWITCH_ON/OFF`, ...) et un cover que via `FLAP_UP/DOWN/STOP`. Quand la
    famille de commande du type forcé diffère de la famille native des capabilities source,
    la commande d'action requise est absente → la projection doit être refusée plutôt que
    publiée comme entité non-actionnable (D11, pas de bypass).
    """
    if ha_entity_type in ("light", "switch"):
        return isinstance(capabilities, CoverCapabilities)
    if ha_entity_type == "cover":
        return isinstance(capabilities, (LightCapabilities, SwitchCapabilities))
    return False


# ---------------------------------------------------------------------------
# Fonction pure d'étape 3 (Story 3.2)
# ---------------------------------------------------------------------------

def validate_projection(
    ha_entity_type: str,
    capabilities: object,
) -> "ProjectionValidity":
    """Vérifie que le mapping candidat peut produire un payload HA
    structurellement valide pour le composant cible.

    Fonction pure — aucun effet de bord, pas de log, pas d'état global.

    Retourne toujours un ProjectionValidity complet (is_valid jamais None).
    None reste un statut d'orchestration injecté par l'orchestrateur quand
    l'étape 3 n'est pas exécutée (upstream a échoué).
    """
    if ha_entity_type not in HA_COMPONENT_REGISTRY:
        return ProjectionValidity(
            is_valid=False,
            reason_code="ha_component_unknown",
            missing_fields=[],
            missing_capabilities=[],
        )

    # Story 16.7 (Codex P1) — refuse un override cross-type dont la famille de commande
    # (ON/OFF vs OPEN/CLOSE) ne peut être routée : la commande d'action requise est absente.
    if _cross_family_action_mismatch(ha_entity_type, capabilities):
        return ProjectionValidity(
            is_valid=False,
            reason_code="ha_missing_command_topic",
            missing_fields=["command_topic"],
            missing_capabilities=["has_command"],
        )

    spec = HA_COMPONENT_REGISTRY[ha_entity_type]
    required_caps: List[str] = spec["required_capabilities"]

    missing_caps: List[str] = []
    missing_fields: List[str] = []

    # Itère dans l'ordre stable du registre pour des listes déterministes
    for abstract_cap in required_caps:
        if not _resolve_capability(abstract_cap, capabilities):
            missing_caps.append(abstract_cap)
            reason_info = _CAPABILITY_TO_REASON.get(abstract_cap)
            if reason_info:
                missing_fields.extend(reason_info[1])

    if not missing_caps:
        return ProjectionValidity(
            is_valid=True,
            reason_code=None,
            missing_fields=[],
            missing_capabilities=[],
        )

    # Choisir le reason_code de plus haute priorité parmi ceux présents
    first_info = _CAPABILITY_TO_REASON.get(missing_caps[0])
    reason_code: str = first_info[0] if first_info else "ha_validation_failed"
    for priority_code in _REASON_PRIORITY:
        for cap in missing_caps:
            if _CAPABILITY_TO_REASON.get(cap, ("",))[0] == priority_code:
                reason_code = priority_code
                break
        else:
            continue
        break

    return ProjectionValidity(
        is_valid=False,
        reason_code=reason_code,
        missing_fields=missing_fields,
        missing_capabilities=missing_caps,
    )
