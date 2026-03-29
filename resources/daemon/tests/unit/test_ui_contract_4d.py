"""Tests unitaires pour models/ui_contract_4d.py — Story 4.1 (AC 1–7).

Couvre : reason_code_to_perimetre, compute_ecart, build_ui_counters.
Isolation totale — aucune dépendance sur http_server, aggregation, taxonomy.

Fix terrain 2026-03-27 : compute_ecart est fonction pure de (perimetre, statut).
has_pending_home_assistant_changes n'est plus un paramètre — c'est un XOR ambigü
qui ne peut pas servir de proxy de présence HA réelle.
"""

import pytest
from models.ui_contract_4d import reason_code_to_perimetre, compute_ecart, build_ui_counters


# ---------------------------------------------------------------------------
# Task 5.1 — reason_code_to_perimetre
# ---------------------------------------------------------------------------

def test_perimetre_exclu_sur_equipement():
    assert reason_code_to_perimetre("excluded_eqlogic") == "exclu_sur_equipement"


def test_perimetre_exclu_par_plugin():
    assert reason_code_to_perimetre("excluded_plugin") == "exclu_par_plugin"


def test_perimetre_exclu_par_piece():
    assert reason_code_to_perimetre("excluded_object") == "exclu_par_piece"


def test_perimetre_fallback_published_sure():
    """Tout reason_code non-exclusion → inclus."""
    assert reason_code_to_perimetre("sure") == "inclus"


def test_perimetre_fallback_ambiguous():
    assert reason_code_to_perimetre("ambiguous_skipped") == "inclus"


def test_perimetre_fallback_no_commands():
    assert reason_code_to_perimetre("no_commands") == "inclus"


def test_perimetre_fallback_unknown():
    assert reason_code_to_perimetre("unknown_xyz") == "inclus"


def test_perimetre_never_inherit():
    """La valeur 'inherit' ne doit jamais être retournée."""
    result = reason_code_to_perimetre("inherit")
    assert result != "inherit"
    assert result == "inclus"


# ---------------------------------------------------------------------------
# Task 5.2 — compute_ecart : matrice des 4 cas obligatoires
# Fix terrain 2026-03-27 : compute_ecart(perimetre, statut) sans has_pending
# ---------------------------------------------------------------------------

def test_ecart_aligne_inclus_publie():
    """Cas aligné : inclus + publié → ecart = false."""
    assert compute_ecart("inclus", "publie") is False


def test_ecart_direction_1_inclus_non_publie():
    """Direction 1 : inclus + non_publie → ecart = true."""
    assert compute_ecart("inclus", "non_publie") is True


def test_ecart_aligne_exclu_non_publie():
    """Cas aligné : exclu + non_publie → ecart = false."""
    assert compute_ecart("exclu_sur_equipement", "non_publie") is False


def test_ecart_direction_2_exclu_publie():
    """Direction 2 : exclu + statut=publie (présence HA réelle) → ecart = true."""
    assert compute_ecart("exclu_sur_equipement", "publie") is True


def test_ecart_direction_2_exclu_par_plugin():
    """Direction 2 fonctionne aussi pour exclu_par_plugin."""
    assert compute_ecart("exclu_par_plugin", "publie") is True


def test_ecart_direction_2_exclu_par_piece():
    """Direction 2 fonctionne aussi pour exclu_par_piece."""
    assert compute_ecart("exclu_par_piece", "publie") is True


# ---------------------------------------------------------------------------
# Garde-fou sémantique : has_pending != présence HA réelle
# ---------------------------------------------------------------------------

def test_ecart_signature_rejects_has_pending_parameter():
    """compute_ecart n'accepte que (perimetre, statut) — pas de has_pending.

    Garde-fou : empêche de re-canoniser has_pending comme proxy de présence HA.
    Le terrain 2026-03-27 a prouvé que has_pending est un XOR ambigü.
    """
    import inspect
    sig = inspect.signature(compute_ecart)
    param_names = list(sig.parameters.keys())
    assert param_names == ["perimetre", "statut"], (
        f"compute_ecart ne doit accepter que (perimetre, statut), pas {param_names}. "
        "has_pending_home_assistant_changes n'est PAS un indicateur de présence HA."
    )


# ---------------------------------------------------------------------------
# Task 5.3 — build_ui_counters : liste mixte
# ---------------------------------------------------------------------------

def test_build_ui_counters_mixed():
    """Liste mixte avec inclus/exclus/écarts — vérifie compteurs et invariant."""
    equipments = [
        {"perimetre": "inclus", "ecart": False},          # inclus aligné
        {"perimetre": "inclus", "ecart": True},           # inclus direction 1
        {"perimetre": "exclu_sur_equipement", "ecart": False},  # exclu aligné
        {"perimetre": "exclu_par_plugin", "ecart": True},  # exclu direction 2
        {"perimetre": "inclus", "ecart": False},          # inclus aligné
    ]
    result = build_ui_counters(equipments)

    assert result["total"] == 5
    assert result["inclus"] == 3
    assert result["exclus"] == 2
    assert result["ecarts"] == 2
    # Invariant arithmétique
    assert result["total"] == result["inclus"] + result["exclus"]


# ---------------------------------------------------------------------------
# Task 5.4 — build_ui_counters avec liste vide
# ---------------------------------------------------------------------------

def test_build_ui_counters_empty():
    result = build_ui_counters([])
    assert result == {"total": 0, "inclus": 0, "exclus": 0, "ecarts": 0}
    assert result["total"] == result["inclus"] + result["exclus"]


# ---------------------------------------------------------------------------
# Task 5.5 — ecarts compte les deux directions
# ---------------------------------------------------------------------------

def test_build_ui_counters_both_directions():
    """ecarts compte direction 1 ET direction 2 dans la même liste."""
    equipments = [
        {"perimetre": "inclus", "ecart": True},           # direction 1
        {"perimetre": "exclu_sur_equipement", "ecart": True},  # direction 2
        {"perimetre": "inclus", "ecart": False},          # aligné
        {"perimetre": "exclu_par_piece", "ecart": False},  # aligné
    ]
    result = build_ui_counters(equipments)

    assert result["total"] == 4
    assert result["inclus"] == 2
    assert result["exclus"] == 2
    assert result["ecarts"] == 2  # direction 1 + direction 2
    assert result["total"] == result["inclus"] + result["exclus"]


def test_build_ui_counters_only_direction_1():
    equipments = [
        {"perimetre": "inclus", "ecart": True},
        {"perimetre": "inclus", "ecart": True},
        {"perimetre": "inclus", "ecart": False},
    ]
    result = build_ui_counters(equipments)
    assert result["total"] == 3
    assert result["inclus"] == 3
    assert result["exclus"] == 0
    assert result["ecarts"] == 2


def test_build_ui_counters_only_direction_2():
    equipments = [
        {"perimetre": "exclu_sur_equipement", "ecart": True},
        {"perimetre": "exclu_par_plugin", "ecart": False},
    ]
    result = build_ui_counters(equipments)
    assert result["total"] == 2
    assert result["inclus"] == 0
    assert result["exclus"] == 2
    assert result["ecarts"] == 1
    assert result["total"] == result["inclus"] + result["exclus"]


# ---------------------------------------------------------------------------
# Story 4.3 — Task 7.2 : absorption "Partiellement publié" via le contrat 4D
# ---------------------------------------------------------------------------

def test_absorption_partially_published_sure_mapping():
    """Story 4.3 / Task 7.2 — reason_code=sure_mapping, matched_commands < total_commands
    → perimetre=inclus, ecart=false, cause_code=null.
    Le cas "Partiellement publié" (ancienne dénomination) est absorbé dans statut=publie.
    """
    # sure_mapping → perimetre=inclus (règle reason_code_to_perimetre : tout non-exclusion → inclus)
    perimetre = reason_code_to_perimetre("sure_mapping")
    assert perimetre == "inclus"

    # statut=publie (présence HA réelle simulée)
    statut = "publie"

    # ecart = compute_ecart("inclus", "publie") → False
    ecart = compute_ecart(perimetre, statut)
    assert ecart is False, "Un équipement inclus + publié ne doit pas générer d'écart"


def test_absorption_sure_reason_code_no_ecart():
    """Story 4.3 — reason_code=sure + statut=publie → pas d'écart."""
    assert compute_ecart(reason_code_to_perimetre("sure"), "publie") is False


def test_absorption_probable_reason_code_no_ecart():
    """Story 4.3 — reason_code=probable + statut=publie → pas d'écart."""
    assert compute_ecart(reason_code_to_perimetre("probable"), "publie") is False
