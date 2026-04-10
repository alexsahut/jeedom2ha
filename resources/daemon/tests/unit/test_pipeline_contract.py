"""Tests du contrat de pipeline — Story 1.1.

Vérifie la structure MappingResult à 3 sous-blocs, les types ProjectionValidity
et MappingCapabilities, et le déterminisme de assess_eligibility() (NFR1).
"""
from models.mapping import (
    MappingResult,
    ProjectionValidity,
    MappingCapabilities,
    LightCapabilities,
    CoverCapabilities,
    SwitchCapabilities,
)
from models.topology import JeedomEqLogic, JeedomCmd, assess_eligibility


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mapping_result(**kwargs) -> MappingResult:
    """Construit un MappingResult minimal valide pour les tests structurels."""
    defaults = dict(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Lampe salon",
        capabilities=LightCapabilities(has_on_off=True),
    )
    defaults.update(kwargs)
    return MappingResult(**defaults)


def _make_eq_with_generic_type() -> JeedomEqLogic:
    """Équipement minimal éligible : une commande avec generic_type."""
    return JeedomEqLogic(
        id=42,
        name="Lumière test",
        cmds=[JeedomCmd(
            id=1,
            name="On",
            generic_type="LIGHT_ON",
            type="action",
            sub_type="other",
        )],
    )


# ---------------------------------------------------------------------------
# Test Task 1 — MappingCapabilities est un type alias Union correct
# ---------------------------------------------------------------------------

def test_mapping_capabilities_type_alias_covers_all_concrete_types():
    """MappingCapabilities doit accepter les 3 types concrets de capabilities."""
    light = LightCapabilities(has_on_off=True)
    cover = CoverCapabilities(has_open_close=True)
    switch = SwitchCapabilities(has_on_off=True)

    # Le type alias est résolu à l'exécution via __args__ du Union
    import typing
    args = typing.get_args(MappingCapabilities)
    assert LightCapabilities in args, "LightCapabilities absent du Union MappingCapabilities"
    assert CoverCapabilities in args, "CoverCapabilities absent du Union MappingCapabilities"
    assert SwitchCapabilities in args, "SwitchCapabilities absent du Union MappingCapabilities"

    # Les instances sont bien des membres admissibles
    assert isinstance(light, tuple(args))
    assert isinstance(cover, tuple(args))
    assert isinstance(switch, tuple(args))


# ---------------------------------------------------------------------------
# Test Task 2 — ProjectionValidity : les 3 cas sémantiques
# ---------------------------------------------------------------------------

def test_projection_validity_nominal():
    """Cas nominal : étape 3 exécutée, résultat valide."""
    pv = ProjectionValidity(
        is_valid=True,
        reason_code=None,
        missing_fields=[],
        missing_capabilities=[],
    )
    assert pv.is_valid is True
    assert pv.reason_code is None
    assert pv.missing_fields == []
    assert pv.missing_capabilities == []


def test_projection_validity_skip():
    """Cas skip : étape upstream échouée, sous-bloc rempli explicitement."""
    pv = ProjectionValidity(
        is_valid=None,
        reason_code="skipped_no_mapping_candidate",
        missing_fields=[],
        missing_capabilities=[],
    )
    assert pv.is_valid is None
    assert pv.reason_code == "skipped_no_mapping_candidate"
    assert pv.missing_fields == []
    assert pv.missing_capabilities == []


def test_projection_validity_invalid():
    """Cas invalide : validation échouée avec détail des champs/capabilities manquants."""
    pv = ProjectionValidity(
        is_valid=False,
        reason_code="ha_missing_command_topic",
        missing_fields=["command_topic"],
        missing_capabilities=["has_command"],
    )
    assert pv.is_valid is False
    assert pv.reason_code == "ha_missing_command_topic"
    assert pv.missing_fields == ["command_topic"]
    assert pv.missing_capabilities == ["has_command"]


# ---------------------------------------------------------------------------
# Test Task 3 — MappingResult possède les deux nouveaux sous-blocs (AC#1)
# ---------------------------------------------------------------------------

def test_mapping_result_has_projection_validity_field():
    """MappingResult doit exposer l'attribut projection_validity (default None)."""
    mr = _make_mapping_result()
    assert hasattr(mr, "projection_validity"), "Attribut projection_validity absent"
    assert mr.projection_validity is None


def test_mapping_result_has_publication_decision_ref_field():
    """MappingResult doit exposer l'attribut publication_decision_ref (default None)."""
    mr = _make_mapping_result()
    assert hasattr(mr, "publication_decision_ref"), "Attribut publication_decision_ref absent"
    assert mr.publication_decision_ref is None


def test_mapping_result_existing_fields_unchanged():
    """Les champs existants du sous-bloc mapping (étape 2) restent intacts."""
    mr = _make_mapping_result()
    assert mr.ha_entity_type == "light"
    assert mr.confidence == "sure"
    assert mr.reason_code == "light_on_off"
    assert mr.jeedom_eq_id == 1
    assert mr.ha_unique_id == "jeedom2ha_eq_1"
    assert mr.ha_name == "Lampe salon"
    assert isinstance(mr.capabilities, LightCapabilities)


# ---------------------------------------------------------------------------
# Test AR2 — Trace complète : les 3 sous-blocs sont renseignés, aucun trou (AC#2)
# ---------------------------------------------------------------------------

def test_full_trace_three_sub_blocs_no_gap():
    """AR2 : un MappingResult complet avec les 3 sous-blocs doit être constructible
    sans AttributeError ni champ inattendu absent."""
    pv = ProjectionValidity(
        is_valid=True,
        reason_code=None,
        missing_fields=[],
        missing_capabilities=[],
    )
    mr = _make_mapping_result(projection_validity=pv)

    assert mr.projection_validity is pv
    assert mr.projection_validity.is_valid is True
    assert mr.publication_decision_ref is None  # étape 4 non encore câblée (Epic 5)

    # Vérification que tous les sous-blocs attendus sont accessibles
    for attr in ("ha_entity_type", "confidence", "reason_code", "capabilities",
                 "projection_validity", "publication_decision_ref"):
        assert hasattr(mr, attr), f"Champ attendu absent : {attr}"


# ---------------------------------------------------------------------------
# Test NFR1 — Déterminisme de assess_eligibility() (AC#3)
# ---------------------------------------------------------------------------

def test_assess_eligibility_deterministic_eligible():
    """NFR1 : deux appels avec le même équipement éligible produisent le même résultat."""
    eq = _make_eq_with_generic_type()
    result1 = assess_eligibility(eq)
    result2 = assess_eligibility(eq)

    assert result1.is_eligible == result2.is_eligible
    assert result1.reason_code == result2.reason_code
    assert result1.confidence == result2.confidence


def test_assess_eligibility_deterministic_excluded():
    """NFR1 : deux appels avec un équipement exclu produisent le même résultat."""
    eq = JeedomEqLogic(
        id=99,
        name="Exclu",
        is_excluded=True,
        exclusion_source="eqlogic",
        cmds=[JeedomCmd(id=1, name="On", generic_type="LIGHT_ON", type="action", sub_type="other")],
    )
    result1 = assess_eligibility(eq)
    result2 = assess_eligibility(eq)

    assert result1.is_eligible == result2.is_eligible
    assert result1.reason_code == result2.reason_code
    assert result1.confidence == result2.confidence


def test_assess_eligibility_deterministic_no_generic_type():
    """NFR1 : deux appels avec un équipement sans generic_type → même résultat."""
    eq = JeedomEqLogic(
        id=55,
        name="Sans type",
        cmds=[JeedomCmd(id=1, name="Cmd", generic_type=None, type="info", sub_type="other")],
    )
    result1 = assess_eligibility(eq)
    result2 = assess_eligibility(eq)

    assert result1.is_eligible == result2.is_eligible
    assert result1.reason_code == result2.reason_code
    assert result1.confidence == result2.confidence
