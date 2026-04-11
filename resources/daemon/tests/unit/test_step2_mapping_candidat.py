"""Tests de l'étape 2 — Mapping candidat — Story 2.1.

Vérifie que les mappers produisent un MappingResult avec le sous-bloc mapping
correctement rempli, et que le sous-bloc projection_validity n'est pas touché
par le mapper (P2 — isolation). Démontre la compatibilité AR2 (skipped state
peut être affecté explicitement pour préparer la trace complète du pipeline).
Tests en isolation totale : aucune dépendance MQTT, daemon, pytest-asyncio.
"""
from models.mapping import (
    LightCapabilities,
    CoverCapabilities,
    SwitchCapabilities,
    MappingResult,
    ProjectionValidity,
)
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from mapping.light import LightMapper
from mapping.cover import CoverMapper
from mapping.switch import SwitchMapper


# ---------------------------------------------------------------------------
# Task 1.1 — Helpers locaux (pas de conftest.py)
# ---------------------------------------------------------------------------

def _make_snapshot() -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-04-11T00:00:00", objects={}, eq_logics={})


def _cmd(id: int, name: str, generic_type: str, type_: str = "action", sub_type: str = "other") -> JeedomCmd:
    return JeedomCmd(id=id, name=name, generic_type=generic_type, type=type_, sub_type=sub_type)


def _make_eq(id: int, name: str, cmds: list) -> JeedomEqLogic:
    return JeedomEqLogic(id=id, name=name, cmds=cmds)


# ---------------------------------------------------------------------------
# Task 1.2 — Test nominal LightMapper sure (AC #1, #3)
# ---------------------------------------------------------------------------

def test_light_mapper_nominal_sure_on_off_state():
    """LIGHT_ON + LIGHT_OFF + LIGHT_STATE → sure, light_on_off_only, LightCapabilities."""
    cmds = [
        _cmd(1, "On",    "LIGHT_ON",    type_="action", sub_type="other"),
        _cmd(2, "Off",   "LIGHT_OFF",   type_="action", sub_type="other"),
        _cmd(3, "State", "LIGHT_STATE", type_="info",   sub_type="binary"),
    ]
    eq = _make_eq(10, "Lampe salon", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "light"
    assert result.confidence == "sure"
    assert result.reason_code == "light_on_off_only"
    assert isinstance(result.capabilities, LightCapabilities)
    assert result.capabilities.has_on_off is True
    assert result.capabilities.has_brightness is False


# ---------------------------------------------------------------------------
# Task 1.3 — Test nominal LightMapper probable (AC #1, #3)
# ---------------------------------------------------------------------------

def test_light_mapper_nominal_probable_state_on_only():
    """LIGHT_STATE + LIGHT_ON (sans LIGHT_OFF) → probable, light_on_off_only."""
    cmds = [
        _cmd(1, "On",    "LIGHT_ON",    type_="action", sub_type="other"),
        _cmd(3, "State", "LIGHT_STATE", type_="info",   sub_type="binary"),
    ]
    eq = _make_eq(11, "Lampe bureau", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.confidence == "probable"
    assert result.reason_code == "light_on_off_only"


# ---------------------------------------------------------------------------
# Task 1.4 — Test nominal CoverMapper sure (AC #1, #3)
# ---------------------------------------------------------------------------

def test_cover_mapper_nominal_sure_up_down_state():
    """FLAP_UP + FLAP_DOWN + FLAP_STATE → sure, cover_open_close, CoverCapabilities."""
    cmds = [
        _cmd(4, "Up",    "FLAP_UP",    type_="action", sub_type="other"),
        _cmd(5, "Down",  "FLAP_DOWN",  type_="action", sub_type="other"),
        _cmd(6, "State", "FLAP_STATE", type_="info",   sub_type="numeric"),
    ]
    eq = _make_eq(20, "Volet salon", cmds)
    result = CoverMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "cover"
    assert result.confidence == "sure"
    assert result.reason_code == "cover_open_close"
    assert isinstance(result.capabilities, CoverCapabilities)
    assert result.capabilities.has_open_close is True


# ---------------------------------------------------------------------------
# Task 1.5 — Test nominal SwitchMapper sure (AC #1, #3)
# ---------------------------------------------------------------------------

def test_switch_mapper_nominal_sure_on_off_state():
    """ENERGY_ON + ENERGY_OFF + ENERGY_STATE → sure, switch_on_off_state, SwitchCapabilities."""
    cmds = [
        _cmd(7, "On",    "ENERGY_ON",    type_="action", sub_type="other"),
        _cmd(8, "Off",   "ENERGY_OFF",   type_="action", sub_type="other"),
        _cmd(9, "State", "ENERGY_STATE", type_="info",   sub_type="binary"),
    ]
    eq = _make_eq(30, "Prise cuisine", cmds)
    result = SwitchMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "switch"
    assert result.confidence == "sure"
    assert result.reason_code == "switch_on_off_state"
    assert isinstance(result.capabilities, SwitchCapabilities)
    assert result.capabilities.has_on_off is True
    assert result.capabilities.has_state is True


# ---------------------------------------------------------------------------
# Task 1.6 — Test FR12 — champs requis du sous-bloc mapping (AC #1)
# ---------------------------------------------------------------------------

def test_fr12_mapping_sub_bloc_has_required_fields():
    """Pour chaque mapper nominal, ha_entity_type/confidence/reason_code/capabilities
    sont tous non-None et confidence in ('sure', 'probable')."""
    # LightMapper sure
    light_eq = _make_eq(10, "Lampe salon", [
        _cmd(1, "On",    "LIGHT_ON",    type_="action", sub_type="other"),
        _cmd(2, "Off",   "LIGHT_OFF",   type_="action", sub_type="other"),
        _cmd(3, "State", "LIGHT_STATE", type_="info",   sub_type="binary"),
    ])
    # CoverMapper sure
    cover_eq = _make_eq(20, "Volet salon", [
        _cmd(4, "Up",    "FLAP_UP",    type_="action", sub_type="other"),
        _cmd(5, "Down",  "FLAP_DOWN",  type_="action", sub_type="other"),
        _cmd(6, "State", "FLAP_STATE", type_="info",   sub_type="numeric"),
    ])
    # SwitchMapper sure
    switch_eq = _make_eq(30, "Prise cuisine", [
        _cmd(7, "On",    "ENERGY_ON",    type_="action", sub_type="other"),
        _cmd(8, "Off",   "ENERGY_OFF",   type_="action", sub_type="other"),
        _cmd(9, "State", "ENERGY_STATE", type_="info",   sub_type="binary"),
    ])

    results = [
        LightMapper().map(light_eq, _make_snapshot()),
        CoverMapper().map(cover_eq, _make_snapshot()),
        SwitchMapper().map(switch_eq, _make_snapshot()),
    ]

    for result in results:
        assert result is not None
        assert result.ha_entity_type is not None
        assert result.confidence is not None
        assert result.reason_code is not None
        assert result.capabilities is not None
        assert result.confidence in ("sure", "probable")


# ---------------------------------------------------------------------------
# Task 1.7 — Test P2 isolation — projection_validity non touché (AC #2)
# ---------------------------------------------------------------------------

def test_p2_isolation_projection_validity_is_none_after_mapping():
    """Après LightMapper().map(), result.projection_validity is None.

    étape 3 n'est pas câblée — None = non évalué (pré-Epic 3)
    """
    cmds = [
        _cmd(1, "On",    "LIGHT_ON",    type_="action", sub_type="other"),
        _cmd(2, "Off",   "LIGHT_OFF",   type_="action", sub_type="other"),
        _cmd(3, "State", "LIGHT_STATE", type_="info",   sub_type="binary"),
    ]
    eq = _make_eq(10, "Lampe salon", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.projection_validity is None


# ---------------------------------------------------------------------------
# Task 1.8 — Test P2 isolation — publication_decision_ref non touché (AC #2)
# ---------------------------------------------------------------------------

def test_p2_isolation_publication_decision_ref_is_none_after_mapping():
    """Après LightMapper().map(), result.publication_decision_ref is None.

    étape 4 non câblée — None = non évalué (pré-Epic 5)
    """
    cmds = [
        _cmd(1, "On",    "LIGHT_ON",    type_="action", sub_type="other"),
        _cmd(2, "Off",   "LIGHT_OFF",   type_="action", sub_type="other"),
        _cmd(3, "State", "LIGHT_STATE", type_="info",   sub_type="binary"),
    ]
    eq = _make_eq(10, "Lampe salon", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.publication_decision_ref is None


# ---------------------------------------------------------------------------
# Task 1.9 — Test AR2 compatibilité — skipped state assignable (AC #1)
# ---------------------------------------------------------------------------

def test_ar2_skipped_projection_validity_can_be_set_after_mapping():
    """MappingResult retourné par le mapper est structurellement compatible AR2.

    Un appelant (orchestrateur en Epic 5) peut affecter ProjectionValidity(is_valid=None)
    sans erreur — prouve que le contrat de transport est prêt pour la traversée complète
    du pipeline sans que le mapper viole P2.
    """
    cmds = [
        _cmd(1, "On",    "LIGHT_ON",    type_="action", sub_type="other"),
        _cmd(2, "Off",   "LIGHT_OFF",   type_="action", sub_type="other"),
        _cmd(3, "State", "LIGHT_STATE", type_="info",   sub_type="binary"),
    ]
    eq = _make_eq(10, "Lampe salon", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    # Simule ce que l'orchestrateur fera en Epic 5 (P1 — trace complète)
    result.projection_validity = ProjectionValidity(
        is_valid=None,
        reason_code="skipped_no_mapping_candidate",
        missing_fields=[],
        missing_capabilities=[],
    )
    assert result.projection_validity.is_valid is None
    assert result.projection_validity.reason_code == "skipped_no_mapping_candidate"
    assert result.publication_decision_ref is None  # étape 4 non câblée


# ---------------------------------------------------------------------------
# Task 1.10 — Test FR15 — indépendance structurelle des mappers (AC #2)
# ---------------------------------------------------------------------------

def test_fr15_light_cover_switch_mappers_are_independent_modules():
    """Chaque mapper n'expose pas de symboles des autres mappers dans son espace de noms.

    Vérifie que mapping.light n'importe pas CoverMapper ni SwitchMapper,
    que mapping.cover n'importe pas LightMapper ni SwitchMapper,
    que mapping.switch n'importe pas LightMapper ni CoverMapper.
    Chaque module dépend uniquement de models.topology et models.mapping.
    """
    import mapping.light as light_mod
    import mapping.cover as cover_mod
    import mapping.switch as switch_mod

    # mapping.light ne doit pas exposer les mappers des autres domaines
    assert "CoverMapper" not in vars(light_mod)
    assert "SwitchMapper" not in vars(light_mod)

    # mapping.cover ne doit pas exposer les mappers des autres domaines
    assert "LightMapper" not in vars(cover_mod)
    assert "SwitchMapper" not in vars(cover_mod)

    # mapping.switch ne doit pas exposer les mappers des autres domaines
    assert "LightMapper" not in vars(switch_mod)
    assert "CoverMapper" not in vars(switch_mod)
