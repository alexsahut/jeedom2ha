"""Cadre de gouvernance FR40 — Story 3.3 (pe-epic-3).

FR40 : un composant HA validable ne peut être ajouté à PRODUCT_SCOPE que si
les 3 conditions suivantes sont satisfaites dans le même incrément :
  (1) Le composant est déclaré dans HA_COMPONENT_REGISTRY avec ses contraintes.
  (2) validate_projection() aboutit positivement sur des cas nominaux représentatifs
      ET retourne is_valid=False sur les cas d'échec attendus.
  (3) La suite de tests de non-régression passe intégralement dans le même incrément.

AR13 : toute modification de PRODUCT_SCOPE exige simultanément dans le même incrément
les trois preuves ci-dessus. Ce fichier est le verrou CI de FR40.

Séparation stricte : gouvernance statique vs décision runtime
-------------------------------------------------------------
PRODUCT_SCOPE est un artefact STATIQUE de cycle, modifié uniquement lors de
l'implémentation d'une story dédiée satisfaisant FR40.

La décision runtime "ce composant n'est pas dans le scope produit"
(reason_code : ha_component_not_in_product_scope) appartient à l'étape 4
(decide_publication()) — Story 4.1. Elle ne définit PAS la gouvernance d'ouverture.

_GOVERNED_SCOPE : le verrou CI
-------------------------------
_GOVERNED_SCOPE est le registre audité des ouvertures gouvernées.
test_product_scope_has_governance_proof en est le gardien automatique :
  - Si un composant entre dans PRODUCT_SCOPE sans être dans _GOVERNED_SCOPE → échec CI.
  - Pour ajouter un composant à _GOVERNED_SCOPE, il faut ajouter son
    test_governance_fr40_proof_{type}() dans ce fichier → la code review le vérifie.
  - Les deux ensemble forment le verrou actif de FR40 : code review + CI.

Tests en isolation totale : aucune dépendance MQTT, daemon, pytest-asyncio.
Helpers locaux uniquement — pas de conftest.py.
"""

import pytest

from models.mapping import LightCapabilities, CoverCapabilities, SwitchCapabilities, SensorCapabilities
from validation.ha_component_registry import (
    PRODUCT_SCOPE,
    HA_COMPONENT_REGISTRY,
    validate_projection,
)

# ---------------------------------------------------------------------------
# Registre audité des ouvertures gouvernées — verrou CI de FR40
# ---------------------------------------------------------------------------

_GOVERNED_SCOPE = {
    # Chaque clé est un composant présent dans PRODUCT_SCOPE.
    # Chaque valeur est le nom exact de la fonction de preuve FR40 dans ce fichier.
    # L'association explicite empêche l'ajout mécanique d'un composant dans PRODUCT_SCOPE
    # sans qu'une preuve de gouvernance nommée existe dans le même incrément.
    "light": "test_governance_fr40_proof_light",
    "cover": "test_governance_fr40_proof_cover",
    "switch": "test_governance_fr40_proof_switch",
    "sensor": "test_governance_fr40_proof_sensor",
    "binary_sensor": "test_governance_fr40_proof_binary_sensor",
    "button": "test_governance_fr40_proof_button",
}
# 3 conditions FR40 — mécanismes d'enforcement (AR13) :
#
#   Condition 1 — registre :
#     assert component in HA_COMPONENT_REGISTRY
#     → vérifiée par test_product_scope_has_governance_proof (CI paramétré, ce fichier)
#
#   Condition 2 — preuve validate_projection :
#     _GOVERNED_SCOPE[component] pointe vers test_governance_fr40_proof_{type}()
#     → la fonction doit exister dans ce fichier et passer (code review + CI)
#
#   Condition 3 — non-régression :
#     exécution de `python3 -m pytest tests/` dans le même incrément
#     → gate CI avant merge — aucun code dans ce fichier ne peut simuler cette condition
#
# _GOVERNED_SCOPE.keys() doit rester en stricte égalité avec set(PRODUCT_SCOPE).


# ---------------------------------------------------------------------------
# Task 1.4 — Gardien CI de FR40 (AC: #1, #2)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("component", PRODUCT_SCOPE)
def test_product_scope_has_governance_proof(component):
    """Chaque composant de PRODUCT_SCOPE satisfait les conditions 1 et 2 de FR40 vérifiables en CI.

    Condition 1 (registre) vérifiée ici     : component in HA_COMPONENT_REGISTRY.
    Condition 2 (preuve validate_projection) : component in _GOVERNED_SCOPE, avec
                                              _GOVERNED_SCOPE[component] nommant la preuve.
    Condition 3 (non-régression)            : garantie par `python3 -m pytest tests/` —
                                              gate CI, pas de code dans ce fichier.

    Ce test paramétré est le gardien automatique :
      - Si un composant entre dans PRODUCT_SCOPE sans être dans HA_COMPONENT_REGISTRY,
        la condition 1 de FR40 n'est pas satisfaite → échec CI.
      - Si un composant entre dans PRODUCT_SCOPE sans entrée dans _GOVERNED_SCOPE,
        aucune preuve de gouvernance nommée n'existe → échec CI avec message explicite.
    """
    assert component in HA_COMPONENT_REGISTRY, (
        f"condition 1 de FR40 non satisfaite : '{component}' est dans PRODUCT_SCOPE "
        f"mais absent de HA_COMPONENT_REGISTRY — ajouter l'entrée avec required_fields "
        f"+ required_capabilities avant tout ajout à PRODUCT_SCOPE"
    )
    assert component in _GOVERNED_SCOPE, (
        f"condition 2 de FR40 non satisfaite : '{component}' est dans PRODUCT_SCOPE "
        f"mais absent de _GOVERNED_SCOPE — ajouter "
        f"_GOVERNED_SCOPE['{component}'] = 'test_governance_fr40_proof_{component}' "
        f"et implémenter la fonction correspondante dans ce fichier (AR13)"
    )
    proof_fn_name = _GOVERNED_SCOPE[component]
    assert proof_fn_name, (
        f"_GOVERNED_SCOPE['{component}'] est vide — "
        f"la valeur doit nommer la fonction de preuve FR40 "
        f"(ex. 'test_governance_fr40_proof_{component}')"
    )


# ---------------------------------------------------------------------------
# Task 1.5 — Preuve de gouvernance FR40 : light (AC: #5)
# ---------------------------------------------------------------------------

def test_governance_fr40_proof_light():
    """Preuve de gouvernance FR40 pour le composant 'light'.

    Cas nominal : LightCapabilities avec has_on_off=True → is_valid=True.
    Cas d'échec : LightCapabilities avec has_on_off=False → is_valid=False,
                  reason_code="ha_missing_command_topic".
    """
    # Cas nominal
    result_nominal = validate_projection("light", LightCapabilities(has_on_off=True))
    assert result_nominal.is_valid is True
    assert result_nominal.reason_code is None

    # Cas d'échec
    result_fail = validate_projection("light", LightCapabilities(has_on_off=False))
    assert result_fail.is_valid is False
    assert result_fail.reason_code == "ha_missing_command_topic"


# ---------------------------------------------------------------------------
# Task 1.6 — Preuve de gouvernance FR40 : cover (AC: #5)
# ---------------------------------------------------------------------------

def test_governance_fr40_proof_cover():
    """Preuve de gouvernance FR40 pour le composant 'cover'.

    Cas nominal : CoverCapabilities() → is_valid=True.

    Note : cover a required_capabilities=[] dans HA_COMPONENT_REGISTRY — aucun cas
    d'échec par capabilities possible par design (AR6 : cover read-only valide selon
    architecture HA MQTT). validate_projection("cover", any_caps) retourne toujours
    is_valid=True. La preuve de gouvernance est complète sur le cas nominal seul.
    L'absence de cas d'échec est voulue et documentée — ce n'est pas une lacune.
    """
    # Cas nominal
    result_nominal = validate_projection("cover", CoverCapabilities())
    assert result_nominal.is_valid is True
    assert result_nominal.reason_code is None


# ---------------------------------------------------------------------------
# Task 1.7 — Preuve de gouvernance FR40 : switch (AC: #5)
# ---------------------------------------------------------------------------

def test_governance_fr40_proof_switch():
    """Preuve de gouvernance FR40 pour le composant 'switch'.

    Cas nominal : SwitchCapabilities avec has_on_off=True → is_valid=True.
    Cas d'échec : SwitchCapabilities avec has_on_off=False → is_valid=False,
                  reason_code="ha_missing_command_topic".
    """
    # Cas nominal
    result_nominal = validate_projection("switch", SwitchCapabilities(has_on_off=True))
    assert result_nominal.is_valid is True
    assert result_nominal.reason_code is None

    # Cas d'échec
    result_fail = validate_projection("switch", SwitchCapabilities(has_on_off=False))
    assert result_fail.is_valid is False
    assert result_fail.reason_code == "ha_missing_command_topic"


# ---------------------------------------------------------------------------
# Preuves de gouvernance FR40 : vague cible pe-epic-7 (Story 7.4)
# ---------------------------------------------------------------------------

def test_governance_fr40_proof_sensor():
    """Preuve de gouvernance FR40 pour le composant 'sensor'.

    Cas nominal : SensorCapabilities avec has_state=True → is_valid=True.
    Cas d'échec : SensorCapabilities avec has_state=False → is_valid=False,
                  reason_code="ha_missing_state_topic".
    """
    result_nominal = validate_projection("sensor", SensorCapabilities(has_state=True))
    assert result_nominal.is_valid is True
    assert result_nominal.reason_code is None

    result_fail = validate_projection("sensor", SensorCapabilities(has_state=False))
    assert result_fail.is_valid is False
    assert result_fail.reason_code == "ha_missing_state_topic"


def test_governance_fr40_proof_binary_sensor():
    """Preuve de gouvernance FR40 pour le composant 'binary_sensor'.

    sensor et binary_sensor partagent SensorCapabilities (has_state).
    Cas nominal : SensorCapabilities avec has_state=True → is_valid=True.
    Cas d'échec : SensorCapabilities avec has_state=False → is_valid=False,
                  reason_code="ha_missing_state_topic".
    """
    result_nominal = validate_projection("binary_sensor", SensorCapabilities(has_state=True))
    assert result_nominal.is_valid is True
    assert result_nominal.reason_code is None

    result_fail = validate_projection("binary_sensor", SensorCapabilities(has_state=False))
    assert result_fail.is_valid is False
    assert result_fail.reason_code == "ha_missing_state_topic"


# ---------------------------------------------------------------------------
# Task 1.8 — Gardien de la condition 1 de FR40 : composant inconnu (AC: #4)
# ---------------------------------------------------------------------------

def test_governance_gate_blocks_condition1_violation():
    """Un composant absent de HA_COMPONENT_REGISTRY ne satisfait pas la condition 1 de FR40.

    Son ajout à PRODUCT_SCOPE est interdit : validate_projection retourne
    ha_component_unknown, ce qui rend la preuve de gouvernance nominale impossible.

    Utilise un type fictif "__gov_test_unknown__" garanti hors-registre.
    """
    result = validate_projection("__gov_test_unknown__", LightCapabilities(has_on_off=True))
    assert result.is_valid is False
    assert result.reason_code == "ha_component_unknown"


# ---------------------------------------------------------------------------
# Task 1.9 — Gardien de la condition 2 de FR40 : capabilities insuffisantes (AC: #3)
# ---------------------------------------------------------------------------

def test_governance_gate_blocks_condition2_violation():
    """Un composant connu mais dont validate_projection échoue sur les capabilities
    ne remplit pas la condition 2 de FR40.

    Sa preuve de gouvernance nominale est impossible dans cette configuration :
    ajouter ce composant à PRODUCT_SCOPE sans corriger ses capabilities serait
    une ouverture non gouvernée.

    Démontre sur 'light' (composant connu) avec has_on_off=False : les capabilities
    ne satisfont pas required_capabilities=["has_command"] → is_valid=False.
    """
    result = validate_projection("light", LightCapabilities(has_on_off=False))
    assert result.is_valid is False
    assert result.reason_code == "ha_missing_command_topic"
    assert "has_command" in result.missing_capabilities


# ---------------------------------------------------------------------------
# Preuve de gouvernance FR40 : button (Story 9.3)
# ---------------------------------------------------------------------------

def test_governance_fr40_proof_button():
    """Preuve de gouvernance FR40 pour le composant 'button'.

    Cas nominal : SwitchCapabilities avec has_on_off=True → is_valid=True.
    Cas d'échec : SwitchCapabilities avec has_on_off=False → is_valid=False,
                  reason_code="ha_missing_command_topic".
    """
    result_nominal = validate_projection("button", SwitchCapabilities(has_on_off=True))
    assert result_nominal.is_valid is True
    assert result_nominal.reason_code is None

    result_fail = validate_projection("button", SwitchCapabilities(has_on_off=False))
    assert result_fail.is_valid is False
    assert result_fail.reason_code == "ha_missing_command_topic"
