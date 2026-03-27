"""Tests unitaires pour models/cause_mapping.py — Story 4.1 (AC 4).

16 tests : 12 entrées actives direction 1 + 3 codes published + 1 fallback + direction 2.
Isolation totale — aucune dépendance sur http_server, aggregation, taxonomy.
"""

import pytest
from models.cause_mapping import reason_code_to_cause, build_cause_for_pending_unpublish


# ---------------------------------------------------------------------------
# Task 4.1 — 12 entrées actives direction 1
# ---------------------------------------------------------------------------

def test_ambiguous_skipped():
    assert reason_code_to_cause("ambiguous_skipped") == (
        "ambiguous_skipped",
        "Mapping ambigu — plusieurs types possibles",
        "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
    )


def test_probable_skipped():
    assert reason_code_to_cause("probable_skipped") == (
        "ambiguous_skipped",
        "Mapping ambigu — plusieurs types possibles",
        "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
    )


def test_no_mapping():
    assert reason_code_to_cause("no_mapping") == (
        "no_mapping",
        "Aucun mapping compatible",
        "Vérifier les types génériques des commandes dans Jeedom",
    )


def test_no_supported_generic_type():
    code, label, action = reason_code_to_cause("no_supported_generic_type")
    assert code == "no_supported_generic_type"
    assert label == "Type non supporté en V1"
    assert action is None


def test_no_generic_type_configured():
    assert reason_code_to_cause("no_generic_type_configured") == (
        "no_generic_type_configured",
        "Types génériques non configurés sur les commandes",
        "Configurer les types génériques via le plugin Jeedom concerné, puis relancer un rescan",
    )


def test_disabled_eqlogic():
    assert reason_code_to_cause("disabled_eqlogic") == (
        "disabled_eqlogic",
        "Équipement désactivé dans Jeedom",
        "Activer l'équipement dans sa page de configuration Jeedom",
    )


def test_disabled():
    """Legacy alias 'disabled' → même cause que disabled_eqlogic."""
    assert reason_code_to_cause("disabled") == (
        "disabled_eqlogic",
        "Équipement désactivé dans Jeedom",
        "Activer l'équipement dans sa page de configuration Jeedom",
    )


def test_no_commands():
    assert reason_code_to_cause("no_commands") == (
        "no_commands",
        "Équipement sans commandes exploitables",
        "Vérifier que l'équipement possède des commandes actives dans Jeedom",
    )


def test_discovery_publish_failed():
    assert reason_code_to_cause("discovery_publish_failed") == (
        "discovery_publish_failed",
        "Publication MQTT échouée",
        "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
    )


def test_local_availability_publish_failed():
    """local_availability_publish_failed → même cause que discovery_publish_failed."""
    assert reason_code_to_cause("local_availability_publish_failed") == (
        "discovery_publish_failed",
        "Publication MQTT échouée",
        "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
    )


def test_low_confidence():
    """low_confidence → cause_code no_mapping."""
    assert reason_code_to_cause("low_confidence") == (
        "no_mapping",
        "Aucun mapping compatible",
        "Vérifier les types génériques des commandes dans Jeedom",
    )


def test_eligible():
    """eligible → cause_code no_mapping, cause_action différente."""
    assert reason_code_to_cause("eligible") == (
        "no_mapping",
        "Aucun mapping compatible",
        "Relancer un sync complet depuis l'interface du plugin",
    )


# ---------------------------------------------------------------------------
# Task 4.2 — 3 codes published → (None, None, None)
# ---------------------------------------------------------------------------

def test_published_sure():
    assert reason_code_to_cause("sure") == (None, None, None)


def test_published_probable():
    assert reason_code_to_cause("probable") == (None, None, None)


def test_published_sure_mapping():
    assert reason_code_to_cause("sure_mapping") == (None, None, None)


# ---------------------------------------------------------------------------
# Task 4.3 — Fallback sécuritaire (reason_code inconnu)
# ---------------------------------------------------------------------------

def test_fallback_unknown_reason_code():
    assert reason_code_to_cause("unknown_xyz") == (None, None, None)


def test_fallback_empty_string():
    assert reason_code_to_cause("") == (None, None, None)


# ---------------------------------------------------------------------------
# Task 4.4 — build_cause_for_pending_unpublish (direction 2)
# ---------------------------------------------------------------------------

def test_build_cause_for_pending_unpublish():
    assert build_cause_for_pending_unpublish() == (
        "pending_unpublish",
        "Changement en attente d'application",
        "Republier pour appliquer le changement",
    )
