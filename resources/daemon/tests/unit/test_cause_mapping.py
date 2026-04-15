"""Tests unitaires pour models/cause_mapping.py — Story 4.1 / Story 4.3.

31 tests : 20 entrées actives direction 1 + 3 codes published + fallback + direction 2
+ snapshot non-régression + tests anti-contrat.
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
    """low_confidence → cause décisionnelle dédiée, distincte du no_mapping générique."""
    assert reason_code_to_cause("low_confidence") == (
        "low_confidence",
        "Confiance insuffisante pour la politique active",
        "Assouplir la politique de confiance si vous souhaitez autoriser un mapping moins fiable.",
    )


def test_eligible():
    """eligible → cause_code no_mapping, cause_action différente."""
    assert reason_code_to_cause("eligible") == (
        "no_mapping",
        "Aucun mapping compatible",
        "Relancer un sync complet depuis l'interface du plugin",
    )


def test_ha_component_not_in_product_scope():
    """Étape 4 — composant hors scope produit → cause dédiée et non assimilable au mapping."""
    assert reason_code_to_cause("ha_component_not_in_product_scope") == (
        "not_in_product_scope",
        "Composant Home Assistant non ouvert dans ce cycle",
        "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant.",
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


# ---------------------------------------------------------------------------
# Task 2.1 — Snapshot de non-régression (Story 4.3)
# ---------------------------------------------------------------------------

# Oracle de non-régression — Story 4.3.
# Établi lors de la création de la story. Vérifié (pas reconstruit) en Phase 0.
# Contient UNIQUEMENT les codes existants avant implémentation (19 entrées).
# NE PAS modifier ce snapshot — toute divergence après implémentation est une régression.
_BASELINE_SNAPSHOT = {
    "excluded_eqlogic": (
        "excluded_eqlogic",
        "Équipement exclu du scope de synchronisation",
        "Retirer l'équipement de la liste d'exclusion dans les réglages jeedom2ha",
    ),
    "excluded_plugin": (
        "excluded_plugin",
        "Plugin exclu du scope de synchronisation",
        "Retirer le plugin de la liste d'exclusion dans les réglages jeedom2ha",
    ),
    "excluded_object": (
        "excluded_object",
        "Objet Jeedom exclu du scope de synchronisation",
        "Retirer l'objet de la liste d'exclusion dans les réglages jeedom2ha",
    ),
    "ambiguous_skipped": (
        "ambiguous_skipped",
        "Mapping ambigu — plusieurs types possibles",
        "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
    ),
    "probable_skipped": (
        "ambiguous_skipped",
        "Mapping ambigu — plusieurs types possibles",
        "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
    ),
    "no_mapping": (
        "no_mapping",
        "Aucun mapping compatible",
        "Vérifier les types génériques des commandes dans Jeedom",
    ),
    "no_supported_generic_type": ("no_supported_generic_type", "Type non supporté en V1", None),
    "no_generic_type_configured": (
        "no_generic_type_configured",
        "Types génériques non configurés sur les commandes",
        "Configurer les types génériques via le plugin Jeedom concerné, puis relancer un rescan",
    ),
    "disabled_eqlogic": (
        "disabled_eqlogic",
        "Équipement désactivé dans Jeedom",
        "Activer l'équipement dans sa page de configuration Jeedom",
    ),
    "disabled": (
        "disabled_eqlogic",
        "Équipement désactivé dans Jeedom",
        "Activer l'équipement dans sa page de configuration Jeedom",
    ),
    "no_commands": (
        "no_commands",
        "Équipement sans commandes exploitables",
        "Vérifier que l'équipement possède des commandes actives dans Jeedom",
    ),
    "discovery_publish_failed": (
        "discovery_publish_failed",
        "Publication MQTT échouée",
        "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
    ),
    "local_availability_publish_failed": (
        "discovery_publish_failed",
        "Publication MQTT échouée",
        "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
    ),
    "low_confidence": (
        "low_confidence",
        "Confiance insuffisante pour la politique active",
        "Assouplir la politique de confiance si vous souhaitez autoriser un mapping moins fiable.",
    ),
    "ha_component_not_in_product_scope": (
        "not_in_product_scope",
        "Composant Home Assistant non ouvert dans ce cycle",
        "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant.",
    ),
    "eligible": (
        "no_mapping",
        "Aucun mapping compatible",
        "Relancer un sync complet depuis l'interface du plugin",
    ),
    "sure":         (None, None, None),
    "probable":     (None, None, None),
    "sure_mapping": (None, None, None),
}


def test_non_regression_snapshot():
    """SNAPSHOT — baseline figée au checkpoint Phase 0 de Story 4.3.

    Si ce test échoue après un changement de code : régression détectée sur un code existant.
    Ce snapshot NE DOIT PAS être modifié — sauf si une story dédiée l'autorise explicitement.
    """
    for reason_code, expected in _BASELINE_SNAPSHOT.items():
        actual = reason_code_to_cause(reason_code)
        assert actual == expected, (
            f"RÉGRESSION sur {reason_code!r}:\n"
            f"  attendu : {expected!r}\n"
            f"  obtenu  : {actual!r}"
        )


# ---------------------------------------------------------------------------
# Task 2.2 — Tests individuels des codes sans test dans la baseline
# ---------------------------------------------------------------------------

def test_excluded_eqlogic():
    assert reason_code_to_cause("excluded_eqlogic") == (
        "excluded_eqlogic",
        "Équipement exclu du scope de synchronisation",
        "Retirer l'équipement de la liste d'exclusion dans les réglages jeedom2ha",
    )


def test_excluded_plugin():
    assert reason_code_to_cause("excluded_plugin") == (
        "excluded_plugin",
        "Plugin exclu du scope de synchronisation",
        "Retirer le plugin de la liste d'exclusion dans les réglages jeedom2ha",
    )


def test_excluded_object():
    assert reason_code_to_cause("excluded_object") == (
        "excluded_object",
        "Objet Jeedom exclu du scope de synchronisation",
        "Retirer l'objet de la liste d'exclusion dans les réglages jeedom2ha",
    )


# ---------------------------------------------------------------------------
# Task 3 — Tests des nouveaux codes AR8 (classe 2 — étape 3)
# ---------------------------------------------------------------------------

def test_ha_missing_command_topic():
    assert reason_code_to_cause("ha_missing_command_topic") == (
        "ha_missing_command_topic",
        "Projection HA invalide — commande d'action manquante",
        "Vérifier que les commandes de l'équipement incluent une commande d'action compatible dans Jeedom",
    )


def test_ha_missing_state_topic():
    assert reason_code_to_cause("ha_missing_state_topic") == (
        "ha_missing_state_topic",
        "Projection HA invalide — commande d'état manquante",
        "Vérifier que les commandes de l'équipement incluent une commande d'état compatible dans Jeedom",
    )


def test_ha_missing_required_option():
    assert reason_code_to_cause("ha_missing_required_option") == (
        "ha_missing_required_option",
        "Projection HA invalide — option requise par le composant Home Assistant manquante",
        "Vérifier que les commandes de l'équipement couvrent les options requises par le composant Home Assistant cible",
    )


def test_ha_component_unknown():
    """ha_component_unknown — cause_action None explicite (FR33)."""
    cause_code, cause_label, cause_action = reason_code_to_cause("ha_component_unknown")
    assert cause_code == "ha_component_unknown"
    assert cause_label == "Composant Home Assistant non reconnu par le moteur"
    assert cause_action is None


# ---------------------------------------------------------------------------
# Task 4 — Tests anti-contrat
# ---------------------------------------------------------------------------

def test_unknown_code_contractual_return():
    """Contrat explicite : un reason_code absent de _REASON_CODE_TO_CAUSE retourne (None, None, None).

    Ce retour signifie "absence de cause mappable". Ce n'est pas un alias ni une redirection
    vers le triplet d'un code existant. C'est le comportement contractuel documenté du module.
    """
    assert reason_code_to_cause("__unknown_xyz__") == (None, None, None)
    assert reason_code_to_cause("") == (None, None, None)
    from models.cause_mapping import _REASON_CODE_TO_CAUSE
    assert "__unknown_xyz__" not in _REASON_CODE_TO_CAUSE


def test_no_partial_mapping_in_table():
    """Aucune entrée de la table ne doit avoir un mapping partiel.

    Règle : si cause_code est non-null, cause_label doit être non-null.
    Un triplet (cause_code, None, ...) est interdit — ce serait un mapping incomplet.
    Seul le triplet (None, None, None) est accepté comme "pas d'écart direction 1".
    """
    from models.cause_mapping import _REASON_CODE_TO_CAUSE
    for code, triple in _REASON_CODE_TO_CAUSE.items():
        assert isinstance(triple, tuple) and len(triple) == 3, (
            f"{code!r}: entrée malformée — attendu un tuple à 3 éléments, obtenu {triple!r}"
        )
        cause_code, cause_label, cause_action = triple
        if cause_code is not None:
            assert isinstance(cause_code, str) and cause_code, (
                f"{code!r}: cause_code non-null doit être une chaîne non vide"
            )
            assert isinstance(cause_label, str) and cause_label, (
                f"{code!r}: cause_code={cause_code!r} présent mais cause_label={cause_label!r} — mapping partiel interdit"
            )
        if cause_action is not None:
            assert isinstance(cause_action, str) and cause_action, (
                f"{code!r}: cause_action renseignée doit être une chaîne non vide"
            )


def test_classe2_codes_distinct_from_mapping_failures():
    """Après Task 1 : chaque code classe 2 présent dans la table a un cause_code distinct des classes mapping.

    Ce test s'applique aux codes effectivement présents dans _REASON_CODE_TO_CAUSE.
    Il commence par asserter la présence de chaque code pour éviter un faux négatif
    si Task 1 n'a pas été exécutée — dans ce cas, le test échoue explicitement sur l'absence.
    """
    from models.cause_mapping import _REASON_CODE_TO_CAUSE
    classe2_codes = [
        "ha_missing_command_topic",
        "ha_missing_state_topic",
        "ha_missing_required_option",
        "ha_component_unknown",
    ]
    for code in classe2_codes:
        assert code in _REASON_CODE_TO_CAUSE, (
            f"{code!r} absent de _REASON_CODE_TO_CAUSE — ce test doit s'exécuter après Task 1"
        )
        cause_code, _, _ = reason_code_to_cause(code)
        assert cause_code not in (None, "no_mapping", "ambiguous_skipped"), (
            f"{code!r}: cause_code={cause_code!r} — confond validation HA avec un échec de mapping"
        )


def test_ha_component_not_in_product_scope_maps_to_not_in_product_scope():
    """cause_code = 'not_in_product_scope' — invariant AR8 / classe 3."""
    cause_code, cause_label, _ = reason_code_to_cause("ha_component_not_in_product_scope")
    assert cause_code == "not_in_product_scope"
    assert cause_label is not None and len(cause_label) > 0
