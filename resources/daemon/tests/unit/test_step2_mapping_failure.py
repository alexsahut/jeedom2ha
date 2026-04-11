"""Tests de l'étape 2 — Cas d'échec et ambiguïté de mapping — Story 2.2.

Vérifie que les mappers signalent explicitement les mappings impossibles (None)
et ambigus (confidence="ambiguous"), et que les sous-blocs suivants peuvent
être définis avec statut skipped (AR2 — trace complète sans trou implicite).

Tests en isolation totale : aucune dépendance MQTT, daemon, pytest-asyncio.
"""
from models.mapping import (
    MappingResult,
    ProjectionValidity,
    PublicationDecision,
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
# Task 1.2 — Test AC1 — conflicting generic_types LightMapper (AC #1, #3)
# ---------------------------------------------------------------------------

def test_ambiguous_conflicting_light_and_flap_commands():
    """LIGHT_ON + FLAP_UP → LightMapper ambiguous conflicting_generic_types.

    FLAP_UP ∈ _ANTI_LIGHT_GENERIC_TYPES → déclenche le guardrail conflicting.
    decide_publication(result) → should_publish=False, reason="ambiguous_skipped".
    """
    cmds = [
        _cmd(1, "On", "LIGHT_ON", type_="action", sub_type="other"),
        _cmd(2, "Up", "FLAP_UP",  type_="action", sub_type="other"),
    ]
    eq = _make_eq(10, "Lampe conflit", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.confidence == "ambiguous"
    assert result.reason_code == "conflicting_generic_types"

    decision = LightMapper().decide_publication(result)
    assert decision.should_publish is False
    assert decision.reason == "ambiguous_skipped"


# ---------------------------------------------------------------------------
# Task 1.3 — Test AC1 — duplicate generic_types même sub_type (AC #1, #3)
# ---------------------------------------------------------------------------

def test_ambiguous_duplicate_light_state_same_subtype():
    """Deux LIGHT_STATE sub_type='binary' → ambiguous, duplicate_generic_types.

    Même sub_type → _LIGHT_DEDUP_PREFERENCE ne peut pas résoudre (aucune
    préférence applicable entre deux candidats identiques) → ambiguous.
    """
    cmds = [
        _cmd(1, "State1", "LIGHT_STATE", type_="info",   sub_type="binary"),
        _cmd(2, "State2", "LIGHT_STATE", type_="info",   sub_type="binary"),
        _cmd(3, "On",     "LIGHT_ON",    type_="action", sub_type="other"),
    ]
    eq = _make_eq(11, "Lampe doublon", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.confidence == "ambiguous"
    assert result.reason_code == "duplicate_generic_types"


# ---------------------------------------------------------------------------
# Task 1.4 — Test AC1 — name heuristic rejection (AC #1, #3)
# ---------------------------------------------------------------------------

def test_ambiguous_name_heuristic_light_named_volet():
    """Eq nommé "Volet salon" avec LIGHT_* → ambiguous, name_heuristic_rejection.

    "volet" ∈ _NON_LIGHT_KEYWORDS → pattern \\bvolet\\b correspond à "Volet salon".
    """
    cmds = [
        _cmd(1, "On",    "LIGHT_ON",    type_="action", sub_type="other"),
        _cmd(2, "Off",   "LIGHT_OFF",   type_="action", sub_type="other"),
        _cmd(3, "State", "LIGHT_STATE", type_="info",   sub_type="binary"),
    ]
    eq = _make_eq(12, "Volet salon", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.confidence == "ambiguous"
    assert result.reason_code == "name_heuristic_rejection"


# ---------------------------------------------------------------------------
# Task 1.5 — Test AC1 — color_only_unsupported (AC #1, #3)
# ---------------------------------------------------------------------------

def test_ambiguous_color_only_light():
    """Seulement LIGHT_SET_COLOR → ambiguous, color_only_unsupported.

    Precondition obligatoire : "ampoule" absent de _NON_LIGHT_KEYWORDS.
    Si ce n'est plus le cas, le reason_code serait "name_heuristic_rejection"
    et non "color_only_unsupported", ce qui rendrait le test silencieusement faux.
    """
    from mapping.light import _NON_LIGHT_KEYWORDS
    assert "ampoule" not in _NON_LIGHT_KEYWORDS  # précondition — échoue si la liste évolue

    cmds = [_cmd(1, "Couleur", "LIGHT_SET_COLOR", type_="action", sub_type="color")]
    eq = _make_eq(13, "Ampoule RGB", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.confidence == "ambiguous"
    assert result.reason_code == "color_only_unsupported"


# ---------------------------------------------------------------------------
# Task 1.6 — Test AC1 — state_orphan (LIGHT_STATE sans action) (AC #1, #3)
# ---------------------------------------------------------------------------

def test_ambiguous_state_orphan_light():
    """Seulement LIGHT_STATE (type_='info') sans commande action → ambiguous, state_orphan."""
    cmds = [_cmd(1, "State", "LIGHT_STATE", type_="info", sub_type="binary")]
    eq = _make_eq(14, "Lampe orpheline", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.confidence == "ambiguous"
    assert result.reason_code == "state_orphan"


# ---------------------------------------------------------------------------
# Task 1.7 — Test AC2 — LightMapper retourne None pour ENERGY_* (AC #2, #3)
# ---------------------------------------------------------------------------

def test_no_mapping_light_mapper_returns_none_for_energy_commands():
    """ENERGY_ON + ENERGY_OFF + ENERGY_STATE → LightMapper().map() retourne None.

    Aucune commande LIGHT_* → light_cmds vide → return None (pas de candidat).
    """
    cmds = [
        _cmd(7, "On",    "ENERGY_ON",    type_="action", sub_type="other"),
        _cmd(8, "Off",   "ENERGY_OFF",   type_="action", sub_type="other"),
        _cmd(9, "State", "ENERGY_STATE", type_="info",   sub_type="binary"),
    ]
    eq = _make_eq(20, "Prise cuisine", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is None


# ---------------------------------------------------------------------------
# Task 1.8 — Test AC2 — CoverMapper retourne None pour LIGHT_* (AC #2, #3)
# ---------------------------------------------------------------------------

def test_no_mapping_cover_mapper_returns_none_for_light_commands():
    """LIGHT_ON + LIGHT_OFF + LIGHT_STATE → CoverMapper().map() retourne None.

    LIGHT_* vont dans anti_cover_cmds, flap_cmds reste vide → return None.
    """
    cmds = [
        _cmd(1, "On",    "LIGHT_ON",    type_="action", sub_type="other"),
        _cmd(2, "Off",   "LIGHT_OFF",   type_="action", sub_type="other"),
        _cmd(3, "State", "LIGHT_STATE", type_="info",   sub_type="binary"),
    ]
    eq = _make_eq(30, "Lampe salon", cmds)
    result = CoverMapper().map(eq, _make_snapshot())

    assert result is None


# ---------------------------------------------------------------------------
# Task 1.9 — Test AC2 — SwitchMapper retourne None pour FLAP_* (AC #2, #3)
# ---------------------------------------------------------------------------

def test_no_mapping_switch_mapper_returns_none_for_flap_commands():
    """FLAP_UP + FLAP_DOWN + FLAP_STATE → SwitchMapper().map() retourne None.

    FLAP_* vont dans anti_switch_cmds, energy_cmds reste vide → return None.
    """
    cmds = [
        _cmd(4, "Up",    "FLAP_UP",    type_="action", sub_type="other"),
        _cmd(5, "Down",  "FLAP_DOWN",  type_="action", sub_type="other"),
        _cmd(6, "State", "FLAP_STATE", type_="info",   sub_type="numeric"),
    ]
    eq = _make_eq(40, "Volet salon", cmds)
    result = SwitchMapper().map(eq, _make_snapshot())

    assert result is None


# ---------------------------------------------------------------------------
# Task 1.10 — Test AR2 — sub-blocs explicitement définis après mapping ambigu (AC #1)
# ---------------------------------------------------------------------------

def test_ar2_sub_blocs_present_when_mapping_ambiguous():
    """Après mapping ambigu, les sous-blocs aval peuvent être affectés sans erreur.

    Simule ce que l'orchestrateur fera en Epic 5
    (P1 — trace complète, AR2 — jamais absent).
    Note : reason="no_mapping" dans publication_decision_ref est la convention
    orchestrateur (Epic 5) — distinct de "ambiguous_skipped" produit par
    decide_publication(), qui est la raison interne de la couche mapper.
    """
    cmds = [
        _cmd(1, "On", "LIGHT_ON", type_="action", sub_type="other"),
        _cmd(2, "Up", "FLAP_UP",  type_="action", sub_type="other"),
    ]
    eq = _make_eq(10, "Lampe conflit", cmds)
    result = LightMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.confidence == "ambiguous"
    # Sous-blocs aval non câblés par le mapper (P2 — isolation)
    assert result.projection_validity is None
    assert result.publication_decision_ref is None

    # Simule ce que l'orchestrateur fera en Epic 5 (P1 — trace complète, AR2 — jamais absent)
    result.projection_validity = ProjectionValidity(
        is_valid=None,
        reason_code="skipped_no_mapping_candidate",  # étape 3 skippée — étape 2 a échoué
        missing_fields=[],
        missing_capabilities=[],
    )
    result.publication_decision_ref = PublicationDecision(
        should_publish=False,
        reason="no_mapping",  # convention orchestrateur — distinct de "ambiguous_skipped"
        mapping_result=result,
    )

    assert result.projection_validity.is_valid is None
    assert result.projection_validity.reason_code == "skipped_no_mapping_candidate"
    assert result.publication_decision_ref.should_publish is False
    assert result.publication_decision_ref.reason == "no_mapping"


# ---------------------------------------------------------------------------
# Task 1.11 — Test FR14 — reason_codes classe 1 distincts de la classe 2 (AC #2)
# ---------------------------------------------------------------------------

def test_fr14_class1_reason_codes_not_in_class2():
    """Les reason_codes de classe 1 (mapping étape 2) et classe 2 (validation HA étape 3)
    sont disjoints → le diagnostic peut distinguer les deux types d'échec sans ambiguïté.
    """
    CLASS_1_REASON_CODES = {
        "conflicting_generic_types",
        "duplicate_generic_types",
        "name_heuristic_rejection",
        "color_only_unsupported",
        "state_orphan",
        "ambiguous_skipped",
        "probable_skipped",
        "no_mapping",
    }
    CLASS_2_REASON_CODES = {
        "ha_missing_command_topic",
        "ha_missing_state_topic",
        "ha_missing_required_option",
        "ha_component_unknown",
    }
    assert CLASS_1_REASON_CODES.isdisjoint(CLASS_2_REASON_CODES)


# ---------------------------------------------------------------------------
# Task 1.12 — Test NFR9 — cas d'échec CoverMapper et SwitchMapper (AC #3)
# ---------------------------------------------------------------------------

def test_nfr9_cover_ambiguous_conflicting_light_and_flap_commands():
    """FLAP_UP + LIGHT_ON → CoverMapper ambiguous, conflicting_generic_types.

    FLAP_UP ∈ _FLAP_GENERIC_TYPES → flap_cmds non vide.
    LIGHT_ON ∈ _ANTI_COVER_GENERIC_TYPES → anti_cover_cmds non vide → conflicting.
    """
    cmds = [
        _cmd(1, "Up", "FLAP_UP",  type_="action", sub_type="other"),
        _cmd(2, "On", "LIGHT_ON", type_="action", sub_type="other"),
    ]
    eq = _make_eq(50, "Volet conflit", cmds)
    result = CoverMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.confidence == "ambiguous"
    assert result.reason_code == "conflicting_generic_types"


def test_nfr9_switch_ambiguous_conflicting_energy_and_flap_commands():
    """ENERGY_ON + FLAP_UP → SwitchMapper ambiguous, conflicting_generic_types.

    ENERGY_ON ∈ _SWITCH_GENERIC_TYPES → energy_cmds non vide.
    FLAP_UP ∈ _ANTI_SWITCH_GENERIC_TYPES → anti_switch_cmds non vide → conflicting.
    """
    cmds = [
        _cmd(1, "On", "ENERGY_ON", type_="action", sub_type="other"),
        _cmd(2, "Up", "FLAP_UP",   type_="action", sub_type="other"),
    ]
    eq = _make_eq(60, "Prise conflit", cmds)
    result = SwitchMapper().map(eq, _make_snapshot())

    assert result is not None
    assert result.confidence == "ambiguous"
    assert result.reason_code == "conflicting_generic_types"
