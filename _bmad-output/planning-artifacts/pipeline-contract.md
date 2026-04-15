# Contrat global du pipeline de projection

**Artefact :** AI-1 rétro pe-epic-3
**Date :** 2026-04-14
**Révision :** V2 — 2026-04-14
**Statut :** canonique — prérequis pe-epic-4

---

## 1. Contrat par étape

### Étape 1 — Éligibilité

| Dimension | Contrat |
|---|---|
| **Entrée** | `TopologySnapshot` (eq + cmds + scope utilisateur) |
| **Sortie** | `EligibilityResult` par équipement : éligible ou rejeté avec motif |
| **Garanties** | Un eq éligible possède au moins une commande et au moins un `generic_type`. Le scope utilisateur (global > pièce > eq) est résolu. |
| **Reason_codes** | `excluded_eqlogic`, `excluded_plugin`, `excluded_object`, `disabled_eqlogic`, `disabled`, `no_commands`, `no_generic_type_configured` |
| **Interdits** | Aucune logique de mapping ne s'exécute ici. Aucun accès au registre HA. Un eq inéligible ne produit ni `mapping`, ni `projection_validity`, ni `publication_decision` (il sort du pipeline). |
| **Dépendances** | Aucune étape amont. Les overrides utilisateur (inclusion/exclusion) sont résolus ici et uniquement ici. |

### Étape 2 — Mapping candidat

| Dimension | Contrat |
|---|---|
| **Entrée** | Eq éligible + ses commandes + `generic_types` |
| **Sortie** | Sous-bloc `mapping` dans `MappingResult` : `ha_entity_type`, `confidence`, `reason_code`, `capabilities`, `commands` |
| **Garanties** | Si `confidence` in (`sure`, `probable`, `sure_mapping`) : un `ha_entity_type` valide est produit et les `capabilities` sont renseignées. Si mapping échoué : `confidence` = `unknown` et `reason_code` explicite. |
| **Reason_codes** | `no_mapping`, `ambiguous_skipped`, `probable_skipped`, `no_supported_generic_type`, `low_confidence`, `eligible` (fallback) |
| **Interdits** | Ne vérifie pas la validité HA. Ne consulte pas `PRODUCT_SCOPE`. N'écrit dans aucun sous-bloc autre que `mapping`. |
| **Dépendances** | Étape 1 réussie. |

### Étape 3 — Validation HA

| Dimension | Contrat |
|---|---|
| **Entrée** | `mapping.ha_entity_type` + `mapping.capabilities` + `HA_COMPONENT_REGISTRY` |
| **Sortie** | Sous-bloc `projection_validity` dans `MappingResult` : `is_valid`, `reason_code`, `missing_fields`, `missing_capabilities` |
| **Garanties** | Si `is_valid=True` : le candidat peut produire un payload HA structurellement valide pour ce composant. Si `is_valid=False` : `reason_code`, `missing_fields` et `missing_capabilities` sont renseignés. Si le mapping a échoué en amont : `is_valid=None`, `reason_code=skipped_no_mapping_candidate`. |
| **Reason_codes** | `ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown`, `skipped_no_mapping_candidate` |
| **Interdits** | Ne modifie jamais le sous-bloc `mapping`. Ne consulte pas `PRODUCT_SCOPE`. Ne prend aucune décision de publication. |
| **Dépendances** | Étape 2 exécutée (même si échouée — produit alors un skip explicite). `HA_COMPONENT_REGISTRY` comme source de contraintes. |

### Étape 4 — Décision de publication

| Dimension | Contrat |
|---|---|
| **Entrée** | `mapping.confidence` + `projection_validity.is_valid` + `PRODUCT_SCOPE` + politique de confiance |
| **Sortie** | Sous-bloc `publication_decision` dans `MappingResult` : `should_publish`, `reason_code`, `active_or_alive`, `discovery_published`. Note : le champ code s'appelle `reason` dans `PublicationDecision` mais porte une valeur `reason_code` canonique. |
| **Garanties** | `should_publish=True` uniquement si : mapping réussi ET `is_valid=True` ET composant dans `PRODUCT_SCOPE` ET confiance suffisante. `reason_code` est toujours renseigné, y compris en cas positif (valeur = le `reason_code` du mapping, ex: `sure`). `should_publish=False` + `reason_code` explicite dans tous les autres cas. |
| **Reason_codes** | `ha_component_not_in_product_scope` + tout `reason_code` hérité d'une étape amont bloquante |
| **Interdits** | Ne modifie ni `mapping` ni `projection_validity`. Ne publie rien vers MQTT. `reason_code` absent ou `None` est interdit. |
| **Dépendances** | Étapes 2 et 3 exécutées. `PRODUCT_SCOPE` comme référence. |

### Étape 5 — Publication MQTT

| Dimension | Contrat |
|---|---|
| **Entrée** | `publication_decision` avec `should_publish=True` |
| **Sortie** | Payload MQTT Discovery envoyé + état enregistré + résultat technique de publication |
| **Garanties** | Seuls les eq avec `should_publish=True` produisent un payload MQTT. Le résultat technique (succès ou échec d'infrastructure) est enregistré séparément de la cause décisionnelle (étapes 1-4). |
| **Reason_codes techniques** | `discovery_publish_failed`, `local_availability_publish_failed` |
| **Interdits** | Ne réévalue aucune étape amont. Ne modifie pas la cause décisionnelle canonique établie par les étapes 1-4. |
| **Dépendances** | Étape 4 avec `should_publish=True`. |

---

## 2. Règles globales du pipeline

1. **Ordre strict et stable.** Éligibilité → Mapping → Validation HA → Décision → Publication. Cet ordre ne change jamais.
2. **Cause décisionnelle canonique unique (étapes 1-4).** Le premier échec décisionnel dans l'ordre du pipeline est la cause principale retenue dans le diagnostic. Une étape aval ne peut pas écraser une cause amont. L'étape 5 ne produit pas de cause décisionnelle — elle produit un résultat technique de publication (voir règle 9).
3. **Traversée complète pour les eq éligibles.** Un eq éligible produit toujours les trois sous-blocs (`mapping`, `projection_validity`, `publication_decision`), même si une étape amont a échoué (sous-blocs skippés avec statut explicite). Un eq inéligible sort du pipeline à l'étape 1 et ne produit aucun sous-bloc.
4. **Isolation des sous-blocs.** Chaque étape écrit dans son sous-bloc. Elle lit les sous-blocs précédents mais ne les modifie jamais.
5. **`reason_code` toujours explicite.** Tout sous-bloc porte un `reason_code` non-null — y compris les cas positifs. Terminologie canonique : `reason_code` dans tout le pipeline. Le champ `PublicationDecision.reason` dans le code porte une valeur `reason_code`.
6. **Migration additive uniquement.** Aucun `reason_code` existant n'est renommé, supprimé ou inversé. Les nouveaux codes s'ajoutent.
7. **Registre HA séparé du mapping.** `HA_COMPONENT_REGISTRY` porte les contraintes, `PRODUCT_SCOPE` porte l'ouverture. Ni le mapping ni le publisher ne codent en dur des contraintes HA.
8. **Jeedom source de vérité.** Le moteur lit Jeedom, ne le modifie jamais. Aucune source de vérité parallèle.
9. **Deux dimensions dans le diagnostic.** Le diagnostic d'un équipement porte deux informations distinctes : (a) la **cause décisionnelle** (étapes 1-4) — pourquoi le pipeline a décidé de publier ou non ; (b) le **résultat technique de publication** (étape 5) — si la publication effective a réussi ou échoué. Ces deux dimensions coexistent sans se remplacer.

---

## 3. Invariants critiques testables

| # | Invariant | Test |
|---|---|---|
| I1 | Un eq inéligible (étape 1) sort du pipeline — aucun sous-bloc produit | `assert mapping_result.mapping is None and mapping_result.projection_validity is None and mapping_result.publication_decision_ref is None` pour tout eq exclu/désactivé |
| I2 | Un eq avec `is_valid=False` a toujours `should_publish=False` | `for eq where projection_validity.is_valid == False: assert publication_decision.should_publish == False` |
| I3 | Un eq avec `should_publish=True` a passé les 4 premières étapes positivement | `assert confidence in ("sure","probable","sure_mapping") and is_valid == True and ha_entity_type in PRODUCT_SCOPE` |
| I4 | Cause décisionnelle = premier échec dans l'ordre pipeline (étapes 1-4) | Soumettre un eq avec mapping ambigu + composant hors scope → cause = `ambiguous_skipped` (étape 2), pas `ha_component_not_in_product_scope` (étape 4) |
| I5 | Tout eq éligible produit les 3 sous-blocs (traversée complète) | `for eq where eligible: assert mapping is not None and projection_validity is not None and publication_decision is not None` |
| I6 | `reason_code` jamais absent dans `publication_decision` | `for all eligible eq: assert publication_decision.reason is not None` |
| I7 | Cause décisionnelle et résultat technique sont indépendants | Soumettre un eq `should_publish=True` + broker down → cause décisionnelle = `sure` (étape 4 réussie), résultat technique = `discovery_publish_failed` (étape 5 échouée). Les deux coexistent dans le diagnostic. |
| I8 | `PRODUCT_SCOPE` est un sous-ensemble strict de `HA_COMPONENT_REGISTRY.keys()` | `assert set(PRODUCT_SCOPE) <= set(HA_COMPONENT_REGISTRY.keys())` |
| I9 | Les `reason_code` sont uniques et sans collision de préfixe | Vérifier unicité dans le catalogue complet |
| I10 | Déterminisme : mêmes entrées → même cause décisionnelle, même `should_publish` | Exécuter le pipeline 2x sur un corpus fixe → résultats identiques |

---

## 4. Scénarios traversants

### Succès — Lumière ON/OFF standard

```
Eq: "Lampe salon" — LIGHT_ON + LIGHT_OFF + LIGHT_STATE

Étape 1: éligible (actif, dans le scope, commandes présentes, generic_types configurés)
Étape 2: mapping → ha_entity_type=light, confidence=sure, reason_code=sure,
         capabilities={has_on_off=True, has_state=True}
Étape 3: validate_projection("light", caps) → is_valid=True (has_command satisfait)
Étape 4: light ∈ PRODUCT_SCOPE, confidence=sure
         → should_publish=True, reason_code=sure
Étape 5: payload MQTT Discovery envoyé → résultat technique = succès

Diagnostic:
  cause décisionnelle : projeté, aucun écart
  résultat technique  : publié
```

### Échec — Capteur de température (composant connu, hors scope produit)

```
Eq: "Thermomètre salon" — TEMPERATURE (info)

Étape 1: éligible
Étape 2: mapping → ha_entity_type=sensor, confidence=sure, reason_code=sure,
         capabilities={has_state=True}
Étape 3: validate_projection("sensor", caps) → is_valid=True (has_state satisfait)
Étape 4: sensor ∉ PRODUCT_SCOPE
         → should_publish=False, reason_code=ha_component_not_in_product_scope
Étape 5: non exécutée (should_publish=False)

Diagnostic:
  cause décisionnelle : cause_code=not_in_product_scope,
                        cause_label="Type d'entité non supporté dans cette version"
                        Cause principale = étape 4 (étapes 2 et 3 ont réussi)
  résultat technique  : N/A (non publié)
```
