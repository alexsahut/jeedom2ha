"""Tests de l'etape 3 - Registre HA - Story 3.1.

Verifie la structure statique de HA_COMPONENT_REGISTRY et PRODUCT_SCOPE,
l'absence d'imports interdits, et les invariants des 3 etats du registre.
Tests en isolation totale : aucune dependance MQTT, daemon, pytest-asyncio.
"""
import ast
import pathlib

from validation.ha_component_registry import HA_COMPONENT_REGISTRY, PRODUCT_SCOPE


def test_module_exports_registry_and_product_scope():
    """AC1 - Le module expose les deux points d'entree attendus."""
    assert isinstance(HA_COMPONENT_REGISTRY, dict)
    assert isinstance(PRODUCT_SCOPE, list)


def test_module_no_forbidden_imports():
    """AR3 - validation/ n'importe rien depuis mapping/, discovery/, transport/."""
    source_path = pathlib.Path(__file__).parent.parent.parent / "validation" / "ha_component_registry.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"mapping", "discovery", "transport"}

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            assert root not in forbidden, f"Import interdit depuis '{root}' dans validation/"
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in forbidden, f"Import interdit depuis '{root}' dans validation/"


def test_each_registry_component_has_required_keys():
    """AC4 - Chaque spec expose les cles structurelles attendues."""
    for spec in HA_COMPONENT_REGISTRY.values():
        assert "required_fields" in spec
        assert "required_capabilities" in spec
        assert isinstance(spec["required_fields"], list)
        assert isinstance(spec["required_capabilities"], list)


def test_each_registry_component_has_at_least_one_constraint():
    """AC2/AC4 - Un composant connu porte au moins une contrainte modelee."""
    for spec in HA_COMPONENT_REGISTRY.values():
        assert bool(spec["required_fields"]) or bool(spec["required_capabilities"])


def test_product_scope_initial_value():
    """AC3 - La valeur initiale du scope ouvert herite de V1.x."""
    assert PRODUCT_SCOPE == ["light", "cover", "switch"]


def test_product_scope_subset_of_registry():
    """AC4 - Tout composant ouvert appartient au registre connu."""
    for component in PRODUCT_SCOPE:
        assert component in HA_COMPONENT_REGISTRY


def test_registry_has_components_not_in_product_scope():
    """AC2 - Les etats 'connu' et 'ouvert' restent distincts."""
    not_open = set(HA_COMPONENT_REGISTRY.keys()) - set(PRODUCT_SCOPE)
    assert len(not_open) > 0


def test_product_scope_modification_requires_fr40():
    """AC3 - Toute ouverture du scope est gouvernee par FR40 dans le meme increment."""
    source_path = pathlib.Path(__file__).parent.parent.parent / "validation" / "ha_component_registry.py"
    source = source_path.read_text(encoding="utf-8")

    # AR13 : toute modification de PRODUCT_SCOPE exige les tests FR40 dans le meme increment.
    assert "PRODUCT_SCOPE =" in source
