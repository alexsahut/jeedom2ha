"""Tests unitaires du moteur d'agrégation — Story 3.3 (Action Item AI-6).

Couverture obligatoire :
- Une règle de priorité par niveau (empty, infra_incident, ambiguous, partially_published,
  not_supported, excluded, published)
- Cas partially_published (préconditions exactes)
- Mixité sans published : not_supported + excluded → not_supported
- Cas vide (pièce et global)
- Stabilité : somme counts_by_status == total_equipments
"""
import pytest
from models.aggregation import build_summary, compute_primary_aggregated_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_eq(status_code: str, reason_code: str = "some_reason") -> dict:
    """Construit un mini-dict d'équipement avec les champs requis par build_summary."""
    return {"status_code": status_code, "reason_code": reason_code}


def _zero_counts() -> dict:
    return {
        "published": 0,
        "excluded": 0,
        "ambiguous": 0,
        "not_supported": 0,
        "infra_incident": 0,
    }


# ---------------------------------------------------------------------------
# Tests de compute_primary_aggregated_status (logique pure)
# ---------------------------------------------------------------------------

class TestComputePrimaryAggregatedStatus:
    """Règle 1 : empty."""

    def test_empty_when_zero_equipments(self):
        assert compute_primary_aggregated_status(_zero_counts(), 0) == "empty"

    """Règle 2 : infra_incident."""

    def test_infra_incident_beats_everything(self):
        counts = {
            "published": 3,
            "excluded": 1,
            "ambiguous": 1,
            "not_supported": 1,
            "infra_incident": 1,
        }
        assert compute_primary_aggregated_status(counts, 7) == "infra_incident"

    def test_infra_incident_alone(self):
        counts = _zero_counts()
        counts["infra_incident"] = 1
        assert compute_primary_aggregated_status(counts, 1) == "infra_incident"

    """Règle 3 : ambiguous."""

    def test_ambiguous_beats_partially_published(self):
        counts = {
            "published": 3,
            "excluded": 1,
            "ambiguous": 1,
            "not_supported": 0,
            "infra_incident": 0,
        }
        assert compute_primary_aggregated_status(counts, 5) == "ambiguous"

    def test_ambiguous_alone(self):
        counts = _zero_counts()
        counts["ambiguous"] = 2
        assert compute_primary_aggregated_status(counts, 2) == "ambiguous"

    """Règle 4 : partially_published."""

    def test_partially_published_with_published_and_excluded(self):
        counts = {
            "published": 2,
            "excluded": 1,
            "ambiguous": 0,
            "not_supported": 0,
            "infra_incident": 0,
        }
        assert compute_primary_aggregated_status(counts, 3) == "partially_published"

    def test_partially_published_with_published_and_not_supported(self):
        counts = {
            "published": 2,
            "excluded": 0,
            "ambiguous": 0,
            "not_supported": 1,
            "infra_incident": 0,
        }
        assert compute_primary_aggregated_status(counts, 3) == "partially_published"

    def test_partially_published_requires_at_least_one_published(self):
        # 0 published + excluded + not_supported → not partially_published
        counts = {
            "published": 0,
            "excluded": 1,
            "ambiguous": 0,
            "not_supported": 1,
            "infra_incident": 0,
        }
        result = compute_primary_aggregated_status(counts, 2)
        assert result != "partially_published"
        assert result == "not_supported"

    """Règle 5 : not_supported."""

    def test_not_supported_beats_excluded_without_published(self):
        counts = {
            "published": 0,
            "excluded": 1,
            "ambiguous": 0,
            "not_supported": 1,
            "infra_incident": 0,
        }
        assert compute_primary_aggregated_status(counts, 2) == "not_supported"

    def test_not_supported_alone(self):
        counts = _zero_counts()
        counts["not_supported"] = 3
        assert compute_primary_aggregated_status(counts, 3) == "not_supported"

    """Règle 6 : excluded."""

    def test_excluded_when_only_excluded(self):
        counts = _zero_counts()
        counts["excluded"] = 2
        assert compute_primary_aggregated_status(counts, 2) == "excluded"

    """Règle 7 : published."""

    def test_published_when_all_published(self):
        counts = _zero_counts()
        counts["published"] = 5
        assert compute_primary_aggregated_status(counts, 5) == "published"

    def test_published_single(self):
        counts = _zero_counts()
        counts["published"] = 1
        assert compute_primary_aggregated_status(counts, 1) == "published"


# ---------------------------------------------------------------------------
# Tests de build_summary (contrat de sortie)
# ---------------------------------------------------------------------------

class TestBuildSummary:
    """Cas vide — pièce vide."""

    def test_empty_room_returns_empty_status(self):
        result = build_summary([])
        assert result["primary_aggregated_status"] == "empty"
        assert result["total_equipments"] == 0
        assert result["counts_by_reason"] == {}

    def test_empty_room_counts_all_zero(self):
        result = build_summary([])
        assert result["counts_by_status"] == {
            "published": 0,
            "excluded": 0,
            "ambiguous": 0,
            "not_supported": 0,
            "infra_incident": 0,
        }

    """Stabilité : somme des counts == total_equipments."""

    def test_counts_sum_equals_total_equipments(self):
        equipments = [
            _make_eq("published", "sure"),
            _make_eq("published", "sure"),
            _make_eq("excluded", "excluded_eqlogic"),
            _make_eq("not_supported", "no_mapping"),
        ]
        result = build_summary(equipments)
        assert sum(result["counts_by_status"].values()) == result["total_equipments"]

    def test_counts_sum_equals_total_equipments_single(self):
        result = build_summary([_make_eq("published")])
        assert sum(result["counts_by_status"].values()) == result["total_equipments"] == 1

    """counts_by_reason — agrégation des reason_code bruts."""

    def test_counts_by_reason_aggregation(self):
        equipments = [
            _make_eq("published", "sure"),
            _make_eq("published", "sure"),
            _make_eq("excluded", "excluded_eqlogic"),
        ]
        result = build_summary(equipments)
        assert result["counts_by_reason"]["sure"] == 2
        assert result["counts_by_reason"]["excluded_eqlogic"] == 1

    def test_counts_by_reason_multiple_codes(self):
        equipments = [
            _make_eq("published", "sure"),
            _make_eq("ambiguous", "ambiguous_skipped"),
            _make_eq("not_supported", "no_commands"),
        ]
        result = build_summary(equipments)
        assert result["counts_by_reason"] == {
            "sure": 1,
            "ambiguous_skipped": 1,
            "no_commands": 1,
        }

    """partially_published."""

    def test_partially_published_published_and_excluded(self):
        equipments = [
            _make_eq("published", "sure"),
            _make_eq("excluded", "excluded_eqlogic"),
        ]
        result = build_summary(equipments)
        assert result["primary_aggregated_status"] == "partially_published"
        assert result["counts_by_status"]["published"] == 1
        assert result["counts_by_status"]["excluded"] == 1

    """Mixité sans published : not_supported + excluded → not_supported."""

    def test_not_supported_plus_excluded_no_published(self):
        equipments = [
            _make_eq("not_supported", "no_mapping"),
            _make_eq("excluded", "excluded_eqlogic"),
        ]
        result = build_summary(equipments)
        assert result["primary_aggregated_status"] == "not_supported"

    """Tous les statuts canoniques sont initialisés."""

    def test_all_canonical_statuses_initialized(self):
        result = build_summary([])
        assert set(result["counts_by_status"].keys()) == {
            "published",
            "excluded",
            "ambiguous",
            "not_supported",
            "infra_incident",
        }

    """Structure complète du dict retourné."""

    def test_summary_structure_has_all_required_fields(self):
        result = build_summary([_make_eq("published")])
        assert "primary_aggregated_status" in result
        assert "total_equipments" in result
        assert "counts_by_status" in result
        assert "counts_by_reason" in result

    """Défense — status_code non canonique normalisé vers not_supported."""

    def test_non_canonical_status_code_normalized_to_not_supported(self):
        equipments = [
            _make_eq("published", "sure"),
            _make_eq("not_published", "some_weird_reason"),  # non canonique
        ]
        result = build_summary(equipments)
        # L'invariant sum == total doit rester vrai
        assert sum(result["counts_by_status"].values()) == result["total_equipments"]
        # Le status_code inconnu doit être compté dans not_supported
        assert result["counts_by_status"]["not_supported"] == 1
        # Aucune nouvelle clé dans counts_by_status
        assert set(result["counts_by_status"].keys()) == {
            "published", "excluded", "ambiguous", "not_supported", "infra_incident",
        }

    def test_non_canonical_status_code_invariant_with_mix(self):
        equipments = [
            _make_eq("published", "sure"),
            _make_eq("bogus_status", "unknown_reason"),
            _make_eq("excluded", "excluded_eqlogic"),
        ]
        result = build_summary(equipments)
        assert sum(result["counts_by_status"].values()) == result["total_equipments"] == 3
        assert result["counts_by_status"]["not_supported"] == 1
        # published + not_supported (normalisé) + excluded → partially_published
        assert result["primary_aggregated_status"] == "partially_published"
