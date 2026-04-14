"""decide_publication.py — Étape 4 du pipeline canonique : décision de publication.

Rôle de l'étape 4 :
    À partir d'un MappingResult complet (étapes 1–3 déjà exécutées), arbitre si
    l'équipement doit être publié vers Home Assistant via MQTT Discovery.

    La décision intègre deux critères propres à l'étape 4 :
      - 4a : le composant HA cible est-il présent dans PRODUCT_SCOPE ?
      - 4b : la confiance du mapping satisfait-elle la politique configurée ?

    Les causes amont (étapes 2 et 3) sont propagées telles quelles — l'étape 4
    ne réinspecte jamais la structure du candidat HA (AR9).

Règle de cause canonique I4 :
    Le PREMIER échec dans l'ordre des étapes (1 → 2 → 3 → 4) est la cause retenue.
    Une étape aval NE PEUT PAS écraser une cause amont.

    Ordre d'évaluation dans decide_publication() :
      Niveau 1 — Cause étape 2 : mapping réussi ?
      Niveau 2 — Cause étape 3 : projection valide ?
      Niveau 3 — Cause étape 4a : composant dans PRODUCT_SCOPE ?
      Niveau 4 — Cause étape 4b : confiance conforme à la politique ?
      Niveau 5 — Nominal : publication autorisée.

Invariants critiques :
    I2 : is_valid=False → jamais publié (should_publish=False garanti)
    I3 : should_publish=True → mapping publishable ET is_valid=True ET ha_entity_type in scope
    I6 : reason toujours non-null et non-vide sur tous les chemins de retour
    I7 : aucune logique MQTT, broker, état de connexion dans ce module

Chaîne d'imports (aucun import circulaire) :
    models/mapping.py ← validation/ha_component_registry.py ← models/decide_publication.py
"""

from __future__ import annotations

from typing import List, Optional

from models.mapping import MappingResult, PublicationDecision
from validation.ha_component_registry import PRODUCT_SCOPE

# Confidences qui résultent d'un mapping réussi (étape 2 aboutie)
_PUBLISHABLE_CONFIDENCES = frozenset({"sure", "probable", "sure_mapping"})


def decide_publication(
    mapping: MappingResult,
    confidence_policy: str = "sure_probable",
    product_scope: Optional[List[str]] = None,
) -> PublicationDecision:
    """Arbitre la publication à partir de la projection validée (étape 4).

    Args:
        mapping: MappingResult complet — projection_validity déjà populé par l'étape 3.
        confidence_policy: "sure_probable" (défaut) publie sure + probable ;
                           "sure_only" bloque probable.
        product_scope: liste des composants ouverts. Par défaut PRODUCT_SCOPE importé
                       depuis validation.ha_component_registry.

    Returns:
        PublicationDecision avec should_publish et reason toujours renseignés (I6).
    """
    if product_scope is None:
        product_scope = PRODUCT_SCOPE

    # Niveau 1 — Cause étape 2 : mapping réussi ?
    if mapping.confidence not in _PUBLISHABLE_CONFIDENCES:
        reason = "ambiguous_skipped" if mapping.confidence == "ambiguous" else "no_mapping"
        return PublicationDecision(should_publish=False, reason=reason)

    # Niveau 2 — Cause étape 3 : projection valide ? (AR9 — consommée, non réévaluée)
    pv = mapping.projection_validity
    if pv is None or pv.is_valid is not True:
        reason = (
            pv.reason_code
            if pv is not None and pv.reason_code
            else "skipped_no_mapping_candidate"
        )
        return PublicationDecision(should_publish=False, reason=reason)

    # Niveau 3 — Cause étape 4a : composant dans PRODUCT_SCOPE ?
    if mapping.ha_entity_type not in product_scope:
        return PublicationDecision(
            should_publish=False, reason="ha_component_not_in_product_scope"
        )

    # Niveau 4 — Cause étape 4b : confiance conforme à la politique ?
    if confidence_policy == "sure_only" and mapping.confidence == "probable":
        return PublicationDecision(should_publish=False, reason="low_confidence")

    # Niveau 5 — Nominal : publication autorisée
    return PublicationDecision(should_publish=True, reason=mapping.confidence)
