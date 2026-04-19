"""Invariant I7 — Tests non-permissifs : séparation decision_trace / publication_trace.

Trois dérives identifiées en story 5.2 sont couvertes individuellement :

  D1 — _build_traceability lit publication_result.technical_reason_code
       pour alimenter decision_trace.reason_code.
  D2 — _CLOSED_REASON_MAP accepte un code technique (ex. discovery_publish_failed),
       ou top_reason_code prend la priorité sur publication_decision_ref.
  D3 — publication_decision_ref=None (fallback legacy) devient source primaire
       alors que publication_decision_ref est présent.

Règle fondamentale :
  canonical_reason = publication_decision_ref.reason (source unique)
  top_reason_code  = fallback EXCLUSIVEMENT si publication_decision_ref est None.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models.mapping import PublicationDecision, PublicationResult
from transport.http_server import _CLOSED_REASON_MAP, _build_traceability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eq_no_cmds() -> MagicMock:
    eq = MagicMock()
    eq.cmds = []
    return eq


def _map_result(
    *,
    decision_reason: str,
    should_publish: bool = True,
    pub_status: str = "failed",
    pub_technical_code: str | None = "discovery_publish_failed",
    confidence: str = "sure",
    ha_entity_type: str = "light",
) -> MagicMock:
    """MagicMock de MappingResult câblé avec publication_decision_ref et publication_result."""
    mr = MagicMock()
    mr.commands = {}
    mr.confidence = confidence
    mr.ha_entity_type = ha_entity_type
    mr.publication_decision_ref = PublicationDecision(
        should_publish=should_publish,
        reason=decision_reason,
    )
    mr.publication_result = PublicationResult(
        status=pub_status,
        technical_reason_code=pub_technical_code,
        attempted_at="2026-04-19T00:00:00+00:00",
    )
    return mr


# ---------------------------------------------------------------------------
# D1 — Contamination par technical_reason_code
#
# Scénario : étape 4 → reason = "sure" (should_publish=True)
#            étape 5 → échec  (technical_reason_code = "discovery_publish_failed")
#
# Violation déclenchée si _build_traceability lit publication_result
# pour alimenter canonical_reason au lieu de publication_decision_ref.reason.
# ---------------------------------------------------------------------------

def test_i7_d1_technical_reason_code_never_reaches_decision_trace():
    """D1 — decision_trace.reason_code provient de publication_decision_ref.reason, pas de publication_result.

    top_reason_code = "ambiguous_skipped" (contradictoire avec decision_ref.reason = "sure")
    pour prouver que c'est bien publication_decision_ref.reason qui est lu :
      - si publication_decision_ref.reason est utilisé → canonical_reason = "sure"
        → _CLOSED_REASON_MAP["sure"] = "published" → reason_code = "published" ✓
      - si publication_result.technical_reason_code est utilisé → canonical_reason = "discovery_publish_failed"
        → not in _CLOSED_REASON_MAP → reason_code = "discovery_publish_failed" ✗
      - si top_reason_code est utilisé → canonical_reason = "ambiguous_skipped"
        → _CLOSED_REASON_MAP["ambiguous_skipped"] = "ambiguous_skipped" → reason_code = "ambiguous_skipped" ✗

    Les trois sources produisent des valeurs distinctes : toute dérive est immédiatement visible.
    """
    mr = _map_result(
        decision_reason="sure",
        should_publish=True,
        pub_status="failed",
        pub_technical_code="discovery_publish_failed",
    )

    # top_reason_code contradictoire avec decision_ref.reason — prouve que la bonne source est lue
    result = _build_traceability(_eq_no_cmds(), mr, "Incident infrastructure", "ambiguous_skipped")

    decision_trace = result["decision_trace"]
    publication_trace = result["publication_trace"]

    # Seul publication_decision_ref.reason = "sure" → "published" produit ce résultat
    assert decision_trace["reason_code"] == "published", (
        f"VIOLATION I7/D1 : decision_trace.reason_code == {decision_trace['reason_code']!r}, "
        "attendu 'published' (de publication_decision_ref.reason='sure'). "
        "'ambiguous_skipped' = dérive top_reason_code ; 'discovery_publish_failed' = dérive technique."
    )

    # Le code technique est dans publication_trace — et uniquement là
    assert publication_trace.get("technical_reason_code") == "discovery_publish_failed", (
        f"technical_reason_code absent ou incorrect dans publication_trace : {publication_trace!r}"
    )


# ---------------------------------------------------------------------------
# D2a — Contamination via _CLOSED_REASON_MAP
#
# Violation : un code technique de l'étape 5 ajouté dans _CLOSED_REASON_MAP
# permettrait à canonical_reason = "discovery_publish_failed" d'être normalisé
# silencieusement au lieu d'être rejeté.
# ---------------------------------------------------------------------------

def test_i7_d2a_closed_reason_map_contains_no_technical_codes():
    """D2a — _CLOSED_REASON_MAP ne doit contenir aucun code technique de l'étape 5.

    Si quelqu'un ajoute 'discovery_publish_failed' ou 'local_availability_publish_failed'
    dans _CLOSED_REASON_MAP, ce test échoue immédiatement.
    """
    _TECHNICAL_CODES = {
        "discovery_publish_failed",
        "local_availability_publish_failed",
    }

    for code in _TECHNICAL_CODES:
        assert code not in _CLOSED_REASON_MAP, (
            f"VIOLATION I7/D2a : '{code}' trouvé dans _CLOSED_REASON_MAP. "
            "Les codes techniques de l'étape 5 sont interdits dans cette map (invariant I7). "
            "Seuls les codes décisionnels des étapes 1–4 sont autorisés."
        )


# ---------------------------------------------------------------------------
# D2b — publication_decision_ref prioritaire sur top_reason_code
#
# Violation : si _build_traceability utilisait top_reason_code en priorité
# (ou en égalité) sur publication_decision_ref, un top_reason_code technique
# passerait dans decision_trace.
# ---------------------------------------------------------------------------

def test_i7_d2b_publication_decision_ref_takes_strict_priority_over_top_reason_code():
    """D2b — publication_decision_ref.reason prime sur top_reason_code sans exception.

    Scénario : top_reason_code = "discovery_publish_failed" (cas déviant imaginé),
               publication_decision_ref présent avec reason = "sure".

    Si _build_traceability utilise top_reason_code en priorité ou en fallback
    même quand publication_decision_ref est présent, ce test échoue.
    """
    mr = _map_result(
        decision_reason="sure",
        should_publish=True,
        pub_status="failed",
        pub_technical_code="discovery_publish_failed",
    )

    result = _build_traceability(
        _eq_no_cmds(),
        mr,
        "Incident infrastructure",
        "discovery_publish_failed",  # top_reason_code technique — doit être ignoré
    )

    decision_trace = result["decision_trace"]

    assert decision_trace["reason_code"] == "published", (
        f"VIOLATION I7/D2b : decision_trace.reason_code == {decision_trace['reason_code']!r}, "
        "attendu 'published'. "
        "top_reason_code ne doit jamais primer sur publication_decision_ref.reason."
    )
    assert decision_trace["reason_code"] != "discovery_publish_failed", (
        "VIOLATION I7/D2b : top_reason_code technique a contaminé decision_trace."
    )


# ---------------------------------------------------------------------------
# D3 — Fallback legacy publication_decision_ref=None
#
# Le fallback top_reason_code est légitimement utilisé dans un seul cas :
# publication_decision_ref est None (objets pré-story-5.2).
#
# Violation : le fallback devient source primaire même quand
# publication_decision_ref est présent, créant un double système de vérité.
# ---------------------------------------------------------------------------

def test_i7_d3_fallback_used_only_when_publication_decision_ref_is_none():
    """D3 — top_reason_code est utilisé EXCLUSIVEMENT si publication_decision_ref=None.

    Deux branches vérifiées explicitement :
      A — publication_decision_ref=None   → fallback top_reason_code actif (mode legacy)
      B — publication_decision_ref présent → top_reason_code ignoré (mode canonique)

    Si quelqu'un réintroduit un double système de vérité, ce test échoue.
    """
    eq = _eq_no_cmds()

    # Branche A — mode legacy : publication_decision_ref absent, fallback actif
    mr_legacy = MagicMock()
    mr_legacy.commands = {}
    mr_legacy.confidence = "ambiguous"
    mr_legacy.ha_entity_type = "light"
    mr_legacy.publication_decision_ref = None
    mr_legacy.publication_result = None

    result_a = _build_traceability(eq, mr_legacy, "Non publié", "ambiguous_skipped")
    assert result_a["decision_trace"]["reason_code"] == "ambiguous_skipped", (
        "VIOLATION I7/D3 (branche A) : fallback top_reason_code non utilisé quand "
        f"publication_decision_ref=None. Obtenu : {result_a['decision_trace']['reason_code']!r}"
    )

    # Branche B — mode canonique : publication_decision_ref présent, top_reason_code ignoré
    mr_canonical = _map_result(
        decision_reason="sure",
        should_publish=True,
        pub_status="success",
        pub_technical_code=None,
    )

    result_b = _build_traceability(
        eq,
        mr_canonical,
        "Incident infrastructure",
        "ambiguous_skipped",  # top_reason_code différent — doit être ignoré
    )
    assert result_b["decision_trace"]["reason_code"] == "published", (
        f"VIOLATION I7/D3 (branche B) : decision_trace.reason_code == "
        f"{result_b['decision_trace']['reason_code']!r}, attendu 'published'. "
        "top_reason_code a pris la place de publication_decision_ref.reason."
    )
    assert result_b["decision_trace"]["reason_code"] != "ambiguous_skipped", (
        "VIOLATION I7/D3 : top_reason_code utilisé malgré publication_decision_ref présent — "
        "double système de vérité réintroduit."
    )


# ---------------------------------------------------------------------------
# D3 (suite) — État legacy dangereux : publication_decision_ref=None + code technique
#
# Ce scénario est invalide dans un pipeline correct :
# top_reason_code est toujours dérivé de PublicationDecision.reason dans le handler,
# et PublicationDecision.reason ne doit jamais contenir un code technique étape 5.
#
# L'implémentation n'ajoute pas de garde explicite contre cet état invalide.
# Ce test de caractérisation documente le comportement actuel : la violation I7
# est VISIBLE (non normalisée silencieusement), ce qui permet de la détecter.
# Il couvre également la branche `elif closed_reason == "discovery_publish_failed"`
# dans la construction de publication_trace (http_server.py ~ligne 1728).
# ---------------------------------------------------------------------------

def test_i7_d3_legacy_dangerous_state_produces_visible_i7_violation():
    """D3 — ÉTAT INVALIDE : publication_decision_ref=None + top_reason_code technique.

    Caractérisation : quand cet état invalide est atteint, la violation I7 est visible
    dans decision_trace.reason_code. Ce test garantit qu'elle ne sera pas normalisée
    silencieusement (ce qui la rendrait indétectable).

    Si une garde explicite est ajoutée dans _build_traceability ou le handler amont,
    ce test devra être mis à jour pour refléter le nouveau comportement attendu.
    """
    mr_invalid = MagicMock()
    mr_invalid.commands = {}
    mr_invalid.confidence = "sure"
    mr_invalid.ha_entity_type = "light"
    mr_invalid.publication_decision_ref = None  # état invalide — aucune décision step-4
    mr_invalid.publication_result = None        # aucun résultat step-5 non plus

    result = _build_traceability(_eq_no_cmds(), mr_invalid, "Non publié", "discovery_publish_failed")

    decision_trace = result["decision_trace"]
    publication_trace = result["publication_trace"]

    # La violation I7 est présente et visible — le code technique atteint decision_trace
    assert decision_trace["reason_code"] == "discovery_publish_failed", (
        "Caractérisation : en état invalide (publication_decision_ref=None + "
        "top_reason_code='discovery_publish_failed'), decision_trace.reason_code vaut "
        f"{decision_trace['reason_code']!r} au lieu de 'discovery_publish_failed'. "
        "Si cette valeur a changé, vérifier qu'une garde explicite a été ajoutée "
        "ou que le handler amont empêche désormais cet état invalide."
    )

    # La branche `elif closed_reason == "discovery_publish_failed"` est déclenchée :
    # publication_result=None mais pub_result="failed" (inféré depuis closed_reason)
    assert publication_trace["last_discovery_publish_result"] == "failed", (
        "Branche elif non déclenchée : en état invalide (closed_reason='discovery_publish_failed', "
        "publication_result=None), last_discovery_publish_result devrait être 'failed'."
    )


# ---------------------------------------------------------------------------
# Test 4 — Séparation stricte des champs
#
# Aucun champ de publication_trace ne doit apparaître dans decision_trace,
# et réciproquement.
# ---------------------------------------------------------------------------

def test_i7_decision_trace_and_publication_trace_share_no_fields():
    """Séparation structurelle — decision_trace et publication_trace n'ont aucun champ commun.

    Vérifie également les champs interdits nommément :
      - 'technical_reason_code' ne doit jamais apparaître dans decision_trace
      - 'reason_code' ne doit jamais apparaître dans publication_trace
    """
    mr = _map_result(
        decision_reason="sure",
        should_publish=True,
        pub_status="failed",
        pub_technical_code="discovery_publish_failed",
    )

    result = _build_traceability(_eq_no_cmds(), mr, "Incident infrastructure", "sure")

    decision_keys = set(result["decision_trace"].keys())
    publication_keys = set(result["publication_trace"].keys())

    shared = decision_keys & publication_keys
    assert not shared, (
        f"VIOLATION I7 : champs partagés entre decision_trace et publication_trace : {shared!r}. "
        "Les deux sous-blocs doivent être strictement disjoints."
    )

    assert "technical_reason_code" not in result["decision_trace"], (
        "VIOLATION I7 : 'technical_reason_code' (champ étape 5) présent dans decision_trace."
    )
    assert "reason_code" not in result["publication_trace"], (
        "VIOLATION I7 : 'reason_code' (champ décisionnel) présent dans publication_trace."
    )


# ---------------------------------------------------------------------------
# Test 5 — Priorité stricte : matrice multi-raisons
#
# Vérifie que publication_decision_ref.reason prime sur top_reason_code
# quelle que soit la valeur de top_reason_code — y compris des codes techniques
# ou des codes d'une autre étape que la décision réelle.
#
# Ce test est complémentaire à D2b et D3 : il couvre la priorité sur un
# ensemble de cas, pas un seul scénario ponctuel.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("decision_reason,top_reason_code_candidate,expected_closed_reason", [
    # decision "sure" + divers top_reason_code (techniques et décisionnels d'autres étapes)
    ("sure", "discovery_publish_failed",          "published"),
    ("sure", "local_availability_publish_failed", "published"),
    ("sure", "ambiguous_skipped",                 "published"),
    ("sure", "ha_missing_state_topic",            "published"),
    ("sure", "ha_component_not_in_product_scope", "published"),
    ("sure", "no_commands",                       "published"),
    # decision != "sure" — prouve que la priorité est générale, pas conditionnelle à "sure"
    # "ambiguous_skipped" + top=technique → expected "ambiguous_skipped" (pas "discovery_publish_failed")
    ("ambiguous_skipped", "discovery_publish_failed", "ambiguous_skipped"),
    # "ambiguous_skipped" + top="sure" → expected "ambiguous_skipped" (pas "published")
    ("ambiguous_skipped", "sure",                     "ambiguous_skipped"),
    # "probable_skipped" → _CLOSED_REASON_MAP["probable_skipped"] = "confidence_policy_skipped"
    ("probable_skipped",  "discovery_publish_failed", "confidence_policy_skipped"),
])
def test_i7_publication_decision_ref_always_wins_over_any_top_reason_code(
    decision_reason: str, top_reason_code_candidate: str, expected_closed_reason: str
):
    """Priorité stricte — publication_decision_ref.reason l'emporte sur tout top_reason_code.

    Matrice : decision_reason × top_reason_code, chaque ligne produit une valeur attendue
    distincte des deux autres sources possibles. Toute mutation du chemin de priorité
    produit une valeur différente de expected_closed_reason et fait échouer le test.
    """
    mr = _map_result(
        decision_reason=decision_reason,
        should_publish=True,
        pub_status="failed",
        pub_technical_code="discovery_publish_failed",
    )

    result = _build_traceability(
        _eq_no_cmds(),
        mr,
        "Incident infrastructure",
        top_reason_code_candidate,  # doit être ignoré dans tous les cas
    )

    assert result["decision_trace"]["reason_code"] == expected_closed_reason, (
        f"VIOLATION I7 : decision_reason={decision_reason!r}, "
        f"top_reason_code={top_reason_code_candidate!r} → "
        f"decision_trace.reason_code == {result['decision_trace']['reason_code']!r}, "
        f"attendu {expected_closed_reason!r}. publication_decision_ref doit toujours primer."
    )
