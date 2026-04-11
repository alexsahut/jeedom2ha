"""ha_component_registry.py - Registre statique des composants HA connus.

Trois etats distincts (AR6) :
  - connu    : entree presente dans HA_COMPONENT_REGISTRY (contraintes modelisees)
  - validable: validate_projection() aboutit positivement sur cas nominaux (Story 3.2)
  - ouvert   : present dans PRODUCT_SCOPE apres satisfaction simultanee de FR40 (Story 3.3)

Dependances : aucune. Ce module ne doit pas importer depuis mapping/, discovery/ ni
transport/ (AR3).
"""

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
        "required_capabilities": [],
    },
}

PRODUCT_SCOPE = ["light", "cover", "switch"]  # V1.x - versionne par cycle produit
# AR13 : toute modification de PRODUCT_SCOPE exige simultanement dans le meme increment :
#   (1) entree dans HA_COMPONENT_REGISTRY avec required_fields + required_capabilities,
#   (2) au moins un cas nominal + un cas d'echec validate_projection() pour ce type,
#   (3) test de non-regression du contrat 4D passant.
