# Story 4.1 : Étape 4 — decide_publication() arbitre la publication à partir de la projection validée, de la politique de confiance et du PRODUCT_SCOPE

Status: done

## Story

En tant qu'utilisateur,
je veux que le système prenne une décision de publication uniquement une fois la projection structurellement validée, en s'appuyant sur la politique de confiance et le PRODUCT_SCOPE courant, avec un motif toujours explicite,
afin de savoir que la décision de publication est distincte de la validation HA et reflète une politique produit délibérée.

## Acceptance Criteria

> **Note de terminologie — invariant de codage :**
> Le dataclass `PublicationDecision` a un champ `reason: str` (PAS `reason_code`). Ce champ porte une valeur `reason_code` canonique.
> - `PublicationDecision(reason="sure")` ✓
> - `PublicationDecision(reason_code="sure")` ✗ — AttributeError
> - `PublicationDecision(reason=None)` ✗ — I6 interdit
> Toute référence à "le `reason_code` de la décision" dans les ACs ci-dessous désigne la valeur portée par `PublicationDecision.reason`.

1. **Given** un équipement avec `projection_validity.is_valid=True`, confiance `sure` et composant dans `PRODUCT_SCOPE`
   **When** `decide_publication()` s'exécute
   **Then** elle retourne `PublicationDecision(should_publish=True, reason="sure")`

2. **Given** un équipement avec `projection_validity.is_valid=True`, confiance `probable`, politique `sure_probable`
   **When** `decide_publication()` s'exécute
   **Then** elle retourne `PublicationDecision(should_publish=True, reason="probable")`

3. **Given** un équipement avec `projection_validity.is_valid=True`, confiance `probable`, politique `sure_only`
   **When** `decide_publication()` s'exécute
   **Then** elle retourne `PublicationDecision(should_publish=False, reason="low_confidence")`

4. **Given** un équipement avec `projection_validity.is_valid=True`, confiance `sure`, mais composant NON dans `PRODUCT_SCOPE`
   **When** `decide_publication()` s'exécute
   **Then** elle retourne `PublicationDecision(should_publish=False, reason="ha_component_not_in_product_scope")`

5. **Given** un équipement avec `projection_validity.is_valid=False` (validation HA échouée)
   **When** `decide_publication()` est appelée
   **Then** `PublicationDecision.reason` prend la valeur de `projection_validity.reason_code` (ex. `reason="ha_missing_state_topic"`) — `should_publish=False`
   **And** `decide_publication()` NE réévalue PAS les contraintes structurelles HA (AR9 — l'étape 4 ne revalide pas)

6. **Given** un équipement avec `mapping.confidence not in {"sure", "probable", "sure_mapping"}` (mapping échoué étape 2)
   **When** `decide_publication()` est appelée
   **Then** elle retourne `PublicationDecision(should_publish=False)` avec `reason` correspondant au type d'échec mapping
   **And** la cause est issue de l'étape 2, pas de l'étape 4

7. **Given** un équipement avec mapping ambigu (`confidence="ambiguous"`) ET composant hors `PRODUCT_SCOPE`
   **When** `decide_publication()` est appelée
   **Then** elle retourne `reason="ambiguous_skipped"` (étape 2 prime sur étape 4 — I4)
   **And** `reason` N'est PAS `"ha_component_not_in_product_scope"`

8. **Given** un équipement avec `is_valid=False` ET composant hors `PRODUCT_SCOPE`
   **When** `decide_publication()` est appelée
   **Then** `PublicationDecision.reason` est valorisé avec `projection_validity.reason_code` (étape 3 prime sur étape 4 — I4)
   **And** `PublicationDecision.reason` N'est PAS `"ha_component_not_in_product_scope"`

9. **Given** tout chemin de code à travers `decide_publication()`
   **When** la fonction retourne
   **Then** `PublicationDecision.reason` est toujours non-null et non-vide (I6 — motif toujours explicite)

10. **Given** un équipement avec `should_publish=True`
    **When** `decide_publication()` a retourné
    **Then** `mapping.confidence ∈ {"sure", "probable", "sure_mapping"}` ET `projection_validity.is_valid is True` ET `ha_entity_type ∈ PRODUCT_SCOPE` (I3 — toutes conditions respectées)

11. **Given** la suite de tests `test_step4_decide_publication.py`
    **When** les tests sont exécutés
    **Then** `test_step4_decide_publication.py` passe avec 0 failure
    **And** la suite complète `tests/` passe avec 0 failure, 0 error
    **And** aucune régression n'est introduite sur la suite existante

## Tasks / Subtasks

- [x] Task 1 — Créer `resources/daemon/models/decide_publication.py` — fonction pure étape 4 (AC: #1–#9)
  - [x] 1.1 — Header de fichier : docstring décrivant le rôle de l'étape 4, la règle de cause canonique I4, et les invariants I2/I3/I6
  - [x] 1.2 — Importer `PublicationDecision`, `MappingResult` depuis `models.mapping` ; importer `PRODUCT_SCOPE` depuis `validation.ha_component_registry` ; importer `Optional`, `List` depuis `typing`
  - [x] 1.3 — Définir la constante module-level : `_PUBLISHABLE_CONFIDENCES = frozenset({"sure", "probable", "sure_mapping"})`
  - [x] 1.4 — Implémenter `decide_publication(mapping, confidence_policy, product_scope)` avec la logique canonique à 4 niveaux (voir Dev Notes §Algorithme)
    - [x] Niveau 1 (étape 2) : `mapping.confidence not in _PUBLISHABLE_CONFIDENCES` → reason dérivé + `should_publish=False`
    - [x] Niveau 2 (étape 3 — nominal + défensif) :
      - Nominal : `pv.is_valid is False` ou `pv.is_valid is None` → `reason=pv.reason_code`, `should_publish=False`
      - Défensif (anti-contrat) : `pv is None` → `reason="skipped_no_mapping_candidate"`, `should_publish=False` — ce cas viole l'invariant pipeline (étape 3 toujours exécutée avant étape 4) et ne doit pas survenir en nominal
    - [x] Niveau 3 (étape 4a — scope) : `mapping.ha_entity_type not in product_scope` → `reason="ha_component_not_in_product_scope"` + `should_publish=False`
    - [x] Niveau 4 (étape 4b — policy) : `confidence_policy == "sure_only" and mapping.confidence == "probable"` → `reason="low_confidence"` + `should_publish=False`
    - [x] Niveau 5 (nominal) : `should_publish=True`, `reason=mapping.confidence`
  - [x] 1.5 — Vérifier qu'aucune logique MQTT, aucune référence à `http_server`, aucun effet de bord n'est présent

- [x] Task 2 — Créer `resources/daemon/tests/unit/test_step4_decide_publication.py` — suite de tests isolée (AC: #1–#11)
  - [x] 2.1 — Header de fichier : docstring documentant story 4.1, isolation totale (pas de MQTT, pas de conftest), invariants testés (I2, I3, I4, I6, I7)
  - [x] 2.2 — Importer `MappingResult`, `ProjectionValidity`, `PublicationDecision`, `LightCapabilities`, `CoverCapabilities`, `SwitchCapabilities` depuis `models.mapping` ; importer `decide_publication` depuis `models.decide_publication` ; importer `PRODUCT_SCOPE` depuis `validation.ha_component_registry`
  - [x] 2.3 — Définir les helpers locaux (pas de conftest) : `_make_mapping()`, `_valid_pv()`, `_failed_pv()` (voir Dev Notes §Helpers de test)
  - [x] 2.4 — Implémenter les cas nominaux (AC: #1, #2)
    - [x] `test_nominal_sure_publishes()` — confidence=sure, is_valid=True, in scope → should_publish=True, reason="sure"
    - [x] `test_nominal_probable_sure_probable_policy_publishes()` — confidence=probable, policy=sure_probable → should_publish=True, reason="probable"
  - [x] 2.5 — Implémenter les cas d'échec mapping (AC: #6)
    - [x] `test_mapping_failed_ambiguous_skipped()` — confidence="ambiguous" → should_publish=False, reason="ambiguous_skipped"
    - [x] `test_mapping_failed_no_mapping()` — confidence="unknown" → should_publish=False, reason="no_mapping"
  - [x] 2.6 — Implémenter les cas d'échec validation HA (AC: #5)
    - [x] `test_projection_invalid_propagates_reason_code()` — is_valid=False, reason_code="ha_missing_state_topic" → reason="ha_missing_state_topic"
    - [x] `test_projection_invalid_does_not_publish()` — I2 : is_valid=False → should_publish=False toujours
  - [x] 2.7 — Implémenter les cas d'échec scope/policy (AC: #3, #4)
    - [x] `test_component_not_in_scope()` — in scope=[], ha_entity_type="light" → reason="ha_component_not_in_product_scope"
    - [x] `test_low_confidence_sure_only_policy()` — confidence=probable, policy=sure_only → reason="low_confidence"
  - [x] 2.8 — Implémenter les tests de priorité des causes — CRITIQUE I4 (AC: #7, #8)
    - [x] `test_i4_step2_wins_over_step4_ambiguous_plus_out_of_scope()` — ambiguous + out of scope → "ambiguous_skipped" (pas "ha_component_not_in_product_scope")
    - [x] `test_i4_step3_wins_over_step4_invalid_plus_out_of_scope()` — is_valid=False + out of scope → reason_code étape 3 (pas "ha_component_not_in_product_scope")
  - [x] 2.9 — Implémenter les tests d'invariants (AC: #9, #10)
    - [x] `test_i6_reason_never_null_on_all_failure_paths()` — vérifier que reason != None sur tous les chemins
    - [x] `test_i3_should_publish_true_requires_all_conditions()` — vérifier les 3 conditions quand should_publish=True
  - [x] 2.10 — Implémenter le test de déterminisme
    - [x] `test_determinism_same_inputs_same_output()` — appeler 2 fois avec les mêmes entrées, résultats identiques

- [x] Task 3 — Vérifier la non-régression et la suite complète (AC: #11)
  - [x] 3.1 — `python3 -m pytest tests/unit/test_step4_decide_publication.py -v` → 0 failure, ≥ 13 tests
  - [x] 3.2 — `python3 -m pytest tests/` → 0 failure, 0 error ; noter le total dans `Debug Log References`
  - [x] 3.3 — Vérifier qu'aucun fichier de production existant (`mapping/*.py`, `http_server.py`, `models/mapping.py`) n'a été modifié

- [x] Task 4 — Mettre à jour le tracker
  - [x] 4.1 — Mettre à jour `_bmad-output/implementation-artifacts/sprint-status.yaml` : status `4-1-*` → `done`

## Dev Notes

### Contexte dans le pipeline

Story 4.1 implémente l'étape 4 du pipeline canonique comme **fonction pure standalone** :

```
Étape 1 (éligibilité)    → assess_eligibility()   — models/topology.py
Étape 2 (mapping)        → LightMapper.map() etc.  — mapping/*.py
Étape 3 (validation HA)  → validate_projection()   — validation/ha_component_registry.py
Étape 4 (décision)       → decide_publication()    — models/decide_publication.py  ← CETTE STORY
Étape 5 (publication)    → http_server.py          — Story 5.1 (hors scope ici)
```

**Ce que cette story produit :**
- Un nouveau fichier `resources/daemon/models/decide_publication.py` avec la fonction pure `decide_publication()`
- Un nouveau fichier `resources/daemon/tests/unit/test_step4_decide_publication.py`

**Ce que cette story NE fait PAS :**
- NE modifie PAS `http_server.py` (l'orchestration est Epic 5)
- NE modifie PAS les méthodes `decide_publication()` sur les mappers existants (`light.py`, `cover.py`, `switch.py`) — ces méthodes survivent intactes pour ne pas régresser le pipeline actuel
- NE modifie PAS `models/mapping.py` (pas de changement structurel)
- NE modifie PAS `cause_mapping.py` — `ha_component_not_in_product_scope` reste un string literal dans cette story (Story 4.2/4.3 centralise les codes)
- N'ajoute PAS `ha_component_not_in_product_scope` à `_REASON_CODE_TO_CAUSE` dans `cause_mapping.py`

### Signature de la fonction

```python
def decide_publication(
    mapping: MappingResult,
    confidence_policy: str = "sure_probable",
    product_scope: Optional[List[str]] = None,
) -> PublicationDecision:
```

- `mapping`: MappingResult complet avec `.projection_validity` déjà populé par l'étape 3
- `confidence_policy`: `"sure_probable"` (défaut, publie sure+probable) ou `"sure_only"` (bloque probable)
- `product_scope`: liste des composants ouverts — par défaut `PRODUCT_SCOPE` importé de `validation.ha_component_registry`
- Retourne: `PublicationDecision` avec `.should_publish` et `.reason` **toujours renseigné** (I6)

### Algorithme canonique (4 niveaux — ordre strict I4)

```python
_PUBLISHABLE_CONFIDENCES = frozenset({"sure", "probable", "sure_mapping"})

def decide_publication(
    mapping: MappingResult,
    confidence_policy: str = "sure_probable",
    product_scope: Optional[List[str]] = None,
) -> PublicationDecision:
    if product_scope is None:
        product_scope = PRODUCT_SCOPE

    # Niveau 1 — Cause étape 2 : mapping réussi ?
    if mapping.confidence not in _PUBLISHABLE_CONFIDENCES:
        reason = "ambiguous_skipped" if mapping.confidence == "ambiguous" else "no_mapping"
        return PublicationDecision(should_publish=False, reason=reason)

    # Niveau 2 — Cause étape 3 : projection valide ? (AR9 — consommée, non réévaluée)
    pv = mapping.projection_validity
    if pv is None or pv.is_valid is not True:
        reason = (pv.reason_code if pv is not None and pv.reason_code else "skipped_no_mapping_candidate")
        return PublicationDecision(should_publish=False, reason=reason)

    # Niveau 3 — Cause étape 4a : composant dans PRODUCT_SCOPE ?
    if mapping.ha_entity_type not in product_scope:
        return PublicationDecision(should_publish=False, reason="ha_component_not_in_product_scope")

    # Niveau 4 — Cause étape 4b : confiance conforme à la politique ?
    if confidence_policy == "sure_only" and mapping.confidence == "probable":
        return PublicationDecision(should_publish=False, reason="low_confidence")

    # Nominal — publication autorisée
    return PublicationDecision(should_publish=True, reason=mapping.confidence)
```

**Points critiques du code :**

1. `mapping.confidence == "ambiguous"` → `reason = "ambiguous_skipped"` (code canonique cause_mapping existant)
2. Tout autre cas de mapping échoué → `reason = "no_mapping"` (fallback canonique existant)
3. `pv.reason_code` est propagé tel quel depuis l'étape 3 (codes classe 2 : `ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown`)
4. `"ha_component_not_in_product_scope"` est un NEW reason_code (classe 3) — string literal ici, Epic 4.2/4.3 l'ajoutera à `cause_mapping.py`
5. `"low_confidence"` est DÉJÀ dans `cause_mapping.py` — pas de nouveau code
6. `reason=mapping.confidence` pour les cas nominaux — reason_codes existants : `"sure"`, `"probable"`, `"sure_mapping"`

### Piège d'import à éviter — CRITIQUE

`models/mapping.py` importe rien de `validation/`. Si `decide_publication()` était ajoutée dans `models/mapping.py`, elle devrait importer `PRODUCT_SCOPE` depuis `validation/ha_component_registry.py` → **import circulaire** (car `validation/ha_component_registry.py` importe depuis `models.mapping`).

**Solution** : créer `models/decide_publication.py` — module séparé qui importe depuis les deux :

```python
# models/decide_publication.py
from models.mapping import MappingResult, PublicationDecision
from validation.ha_component_registry import PRODUCT_SCOPE
```

Aucun import circulaire. La chaîne de dépendances est :
```
models/mapping.py  ←  validation/ha_component_registry.py  ←  models/decide_publication.py
```

### PublicationDecision — champ `reason` (pas `reason_code`)

Le dataclass `PublicationDecision` a un champ `reason: str`, PAS `reason_code`. C'est un écart de nommage legacy dans le code (documenté dans pipeline-contract.md V2). La valeur portée est néanmoins un `reason_code` canonique.

```python
# CORRECT
PublicationDecision(should_publish=False, reason="ambiguous_skipped")

# INCORRECT — le champ s'appelle reason, pas reason_code
PublicationDecision(should_publish=False, reason_code="ambiguous_skipped")  # AttributeError
```

### Helpers de test recommandés

```python
def _make_mapping(
    ha_entity_type: str = "light",
    confidence: str = "sure",
    reason_code: str = "light_on_off",
    projection_validity: Optional[ProjectionValidity] = None,
) -> MappingResult:
    pv = projection_validity if projection_validity is not None else ProjectionValidity(
        is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[]
    )
    mr = MappingResult(
        ha_entity_type=ha_entity_type,
        confidence=confidence,
        reason_code=reason_code,
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Test eq",
        capabilities=LightCapabilities(has_on_off=True),
    )
    mr.projection_validity = pv
    return mr

def _valid_pv() -> ProjectionValidity:
    return ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])

def _failed_pv(reason_code: str = "ha_missing_state_topic") -> ProjectionValidity:
    return ProjectionValidity(is_valid=False, reason_code=reason_code, missing_fields=[], missing_capabilities=[])
```

### Invariants à tester obligatoirement

| Invariant | Test obligatoire |
|---|---|
| I2 : `is_valid=False` → jamais publié | `test_projection_invalid_does_not_publish` |
| I3 : `should_publish=True` → toutes conditions | `test_i3_should_publish_true_requires_all_conditions` |
| I4 : premier échec = cause canonique | `test_i4_step2_wins_over_step4_ambiguous_plus_out_of_scope`, `test_i4_step3_wins_over_step4_invalid_plus_out_of_scope` |
| I6 : `reason` jamais null | `test_i6_reason_never_null_on_all_failure_paths` |
| I7 : aucune logique technique | Vérification structurelle (pas de MQTT dans le code) |

### Cas limites à ne pas oublier

1. `mapping.projection_validity = None` — **fallback défensif uniquement, non nominal.**
   Le pipeline canonique garantit que `validate_projection()` est toujours exécutée avant `decide_publication()` pour tout équipement ayant passé le mapping. Ce cas est un invariant de pipeline violé — il ne fait pas partie des chemins nominaux et ne doit pas survenir en production.
   Comportement défensif attendu : `reason="skipped_no_mapping_candidate"`, `should_publish=False`.
   **Ce chemin ne doit pas être couvert par un test nominal. Un test défensif unique peut le documenter, mais il doit être explicitement labellisé "fallback anti-contrat".**

2. `pv.is_valid = None` (étape 3 a produit un skip explicite — cas nominal en cascade d'échec mapping) → traité comme `is_valid is not True` → `reason=pv.reason_code`, `should_publish=False`

3. `product_scope = []` (scope vide) → tout composant est hors scope → `reason="ha_component_not_in_product_scope"`

4. `confidence = "sure_mapping"` → traité comme publishable (dans `_PUBLISHABLE_CONFIDENCES`)

### Cause principale canonique — rappel I4

La règle est **stricte et non-négociable** :

> Le PREMIER échec dans l'ordre étapes 1→4 est la cause retenue.
> Une étape aval NE PEUT PAS écraser une cause amont.

Exemple obligatoire (I4 — invariant critique) :
```
mapping.confidence = "ambiguous"   # étape 2 échoue
ha_entity_type = "sensor"          # hors PRODUCT_SCOPE — étape 4a aussi échoue

→ cause = "ambiguous_skipped"  ✓  (étape 2 prime)
→ cause = "ha_component_not_in_product_scope"  ✗  (étape 4 ne peut pas gagner)
```

### Séparation étapes 4 et 5

L'étape 4 ne connait pas :
- Le broker MQTT
- L'état de connexion du bridge
- `discovery_published`
- `active_or_alive`

`PublicationDecision` a des champs pour tout cela (`active_or_alive=True` par défaut, `discovery_published=False` par défaut) — les laisser à leurs valeurs par défaut. L'étape 5 les mettra à jour dans `http_server.py` (Epic 5).

### Codes reason — référence rapide

| Source | reason | Où défini |
|---|---|---|
| Étape 2 — ambiguous | `"ambiguous_skipped"` | cause_mapping.py (existant) |
| Étape 2 — unknown | `"no_mapping"` | cause_mapping.py (existant) |
| Étape 3 — commande manquante | `"ha_missing_command_topic"` | hérité de projection_validity.reason_code |
| Étape 3 — état manquant | `"ha_missing_state_topic"` | hérité de projection_validity.reason_code |
| Étape 3 — option manquante | `"ha_missing_required_option"` | hérité de projection_validity.reason_code |
| Étape 3 — composant inconnu | `"ha_component_unknown"` | hérité de projection_validity.reason_code |
| Étape 4a — hors scope | `"ha_component_not_in_product_scope"` | **NOUVEAU** — string literal — Epic 4.2 l'ajoutera à cause_mapping |
| Étape 4b — politique | `"low_confidence"` | cause_mapping.py (existant) |
| Nominal — sure | `"sure"` | cause_mapping.py (existant, code "publié") |
| Nominal — probable | `"probable"` | cause_mapping.py (existant, code "publié") |
| Nominal — sure_mapping | `"sure_mapping"` | cause_mapping.py (existant, code "publié") |

### Action item AI-5 rétro pe-epic-3 — spécification des bords

Conformément à AI-5 de la rétro pe-epic-3, cette story intègre dans ses Dev Notes et ses tâches :

- **Cas limites obligatoires** : `projection_validity=None`, `pv.is_valid=None`, `product_scope=[]`, `confidence="sure_mapping"` (voir §Cas limites)
- **Reason_codes attendus** : tableau complet ci-dessus
- **Comportements interdits** : `reason=None`, modifier `mapping` ou `projection_validity`, ajouter logique MQTT
- **Tests anti-contrat** : I4 (priorité des causes) — obligatoires par design, pas seulement via code review

### Dev Agent Guardrails

- **NE PAS** modifier `models/mapping.py` — PublicationDecision et MappingResult sont figés pour cette story
- **NE PAS** modifier `mapping/light.py`, `mapping/cover.py`, `mapping/switch.py` — les méthodes `decide_publication()` existantes restent
- **NE PAS** modifier `transport/http_server.py` — l'orchestration est Story 5.1
- **NE PAS** modifier `models/cause_mapping.py` — `ha_component_not_in_product_scope` reste string literal dans cette story
- **NE PAS** ajouter `ha_component_not_in_product_scope` à `_REASON_CODE_TO_CAUSE` — c'est Story 4.2
- **NE PAS** retourner `reason=None` dans aucun chemin — I6 interdit
- **NE PAS** appeler `validate_projection()` depuis `decide_publication()` — AR9 : l'étape 4 NE revalide PAS
- **NE PAS** référencer MQTT, broker, `publish_light`, `publish_cover`, `publish_switch` — isolation étape 5
- **NE PAS** créer de conftest.py — helpers locaux dans le fichier de test uniquement
- **CONFIRMER** qu'il n'y a aucun import circulaire entre `models/decide_publication.py`, `models/mapping.py`, et `validation/ha_component_registry.py`
- **CONFIRMER** que `PublicationDecision` est construit avec `reason=...` (pas `reason_code=...`)

### Project Structure Notes

**Fichiers à créer :**

| Fichier | Rôle |
|---|---|
| `resources/daemon/models/decide_publication.py` | Fonction pure `decide_publication()` — étape 4 |
| `resources/daemon/tests/unit/test_step4_decide_publication.py` | Suite de tests isolée — ≥ 13 tests |

**Fichiers explicitement inchangés (hors scope) :**

| Fichier | Raison |
|---|---|
| `resources/daemon/models/mapping.py` | Structures figées — MappingResult, PublicationDecision, ProjectionValidity |
| `resources/daemon/models/cause_mapping.py` | Centralisation des codes = Story 4.2/4.3 |
| `resources/daemon/mapping/light.py` | Méthode `decide_publication` existante sur LightMapper intacte |
| `resources/daemon/mapping/cover.py` | Méthode `decide_publication` existante sur CoverMapper intacte |
| `resources/daemon/mapping/switch.py` | Méthode `decide_publication` existante sur SwitchMapper intacte |
| `resources/daemon/transport/http_server.py` | Orchestration pipeline = Story 5.1 |
| `resources/daemon/validation/ha_component_registry.py` | Registre figé — pas de modification PRODUCT_SCOPE ici |
| `resources/daemon/tests/unit/test_pipeline_contract.py` | Non modifié |
| `resources/daemon/tests/unit/test_step3_*.py` | Non modifiés |

### References

- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` §Étape 4] — contrat formel entrée/sortie, reason_codes, invariants I2/I3/I4/I6/I7
- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` §Règles globales règle 2] — cause décisionnelle canonique unique, ordre 1→4
- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` §Invariants I4] — exemple obligatoire ambigu + hors scope → "ambiguous_skipped"
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 4.1] — user story, AC, dev notes (FR21, FR22, FR23, AR9, AR12)
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §AR9] — étape 4 ne revalide pas, 4 inputs
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §Classe 3] — ha_component_not_in_product_scope
- [Source: `_bmad-output/implementation-artifacts/pe-epic-3-retro-2026-04-13.md` §AI-5] — spécification des bords obligatoire pour toute story pe-epic-4 critique
- [Source: `resources/daemon/models/mapping.py`] — PublicationDecision (champ `reason`, pas `reason_code`), MappingResult, ProjectionValidity
- [Source: `resources/daemon/validation/ha_component_registry.py`] — PRODUCT_SCOPE = ["light", "cover", "switch"], validate_projection() — NE PAS appeler depuis étape 4
- [Source: `resources/daemon/models/cause_mapping.py`] — codes existants : "ambiguous_skipped", "no_mapping", "low_confidence", "sure", "probable", "sure_mapping"
- [Source: `resources/daemon/tests/unit/test_step3_validate_projection.py`] — pattern de tests isolés (helpers locaux, pas de conftest)
- [Source: `resources/daemon/mapping/light.py:325`] — `decide_publication` existant sur LightMapper — NE PAS MODIFIER
- [Source: `resources/daemon/transport/http_server.py:1044`] — appel actuel mapper.decide_publication — câblage futur étape 4 (Story 5.1)

## Note Scrum Master — Statut Epic pe-epic-4

Le workflow `create-story` a automatiquement transitionné `pe-epic-4` de `backlog` → `in-progress` lors de la création de cette story (comportement standard du workflow BMad). Cette décision a été **annulée** dans `sprint-status.yaml` pour laisser le Scrum Master choisir explicitement parmi les deux options :

**Option A** (conservative — recommandée par défaut) : `pe-epic-4: backlog`
- L'epic reste `backlog` tant que le dev n'a pas démarré concrètement
- Le SM met à jour manuellement en `in-progress` à la première session dev
- Avantage : pas d'ambiguïté sur l'état réel du cycle

**Option B** (active) : `pe-epic-4: in-progress`
- L'epic est `in-progress` dès que la story est `ready-for-dev`
- Conforme au comportement automatique du workflow
- Avantage : cohérence avec le modèle de transition BMad

**Statut actuel dans `sprint-status.yaml` : `backlog` (option A appliquée par défaut).**
Pour activer l'option B, mettre à jour manuellement.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Task 3.1 : 19/19 PASS (`test_step4_decide_publication.py`) — 2026-04-14
- Task 3.2 : 384/384 PASS (suite complète `tests/`) — 0 régression — 2026-04-14

### Completion Notes List

- Créé `resources/daemon/models/decide_publication.py` : fonction pure `decide_publication()` (étape 4 du pipeline canonique). Logique à 5 niveaux (étapes 2→3→4a→4b→nominal), invariants I2/I3/I4/I6/I7 respectés, aucune logique MQTT, aucun import circulaire.
- Créé `resources/daemon/tests/unit/test_step4_decide_publication.py` : 19 tests isolés couvrant ACs #1–#11, invariants I2/I3/I4/I6, cas limites AI-5 (pv=None, is_valid=None, scope=[], sure_mapping), fallback anti-contrat labellisé.
- Aucun fichier de production existant modifié (git diff `resources/daemon/` vide).
- Suite complète : 384/384 PASS, 0 régression.

### File List

- `resources/daemon/models/decide_publication.py` (créé)
- `resources/daemon/tests/unit/test_step4_decide_publication.py` (créé)

### Change Log

- 2026-04-14 : Implémentation story 4.1 — fonction pure `decide_publication()` (étape 4 du pipeline canonique) + suite de 19 tests isolés — 384/384 PASS, 0 régression.
- 2026-04-14 : Code review APPROVE — 0 HIGH, 0 MEDIUM, 1 LOW (libellé Task 4.1 cosmétique). 11/11 ACs vérifiés, 16/16 tasks [x] confirmés, 10/10 guardrails respectés. 19/19 tests + 384/384 non-régression.
