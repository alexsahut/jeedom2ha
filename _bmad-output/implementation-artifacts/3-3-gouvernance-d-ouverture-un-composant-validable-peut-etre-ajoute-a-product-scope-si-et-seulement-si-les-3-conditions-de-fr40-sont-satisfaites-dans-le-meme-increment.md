# Story 3.3 : Gouvernance d'ouverture — un composant validable peut être ajouté à `PRODUCT_SCOPE` si et seulement si les 3 conditions de FR40 sont satisfaites dans le même incrément

Status: done

## Story

En tant que mainteneur produit,
je veux qu'un composant HA validable ne puisse être ajouté à `PRODUCT_SCOPE` que si les 3 conditions de FR40 sont satisfaites dans le même incrément,
afin que l'ouverture du périmètre produit soit explicite, gouvernée, testable et non arbitraire.

## Acceptance Criteria

1. **Given** chaque composant actuellement présent dans `PRODUCT_SCOPE`
   **When** `test_product_scope_has_governance_proof(component)` s'exécute (test parametré CI)
   **Then** chaque composant est présent dans `HA_COMPONENT_REGISTRY` (condition 1 de FR40 rétroactivement satisfaite)
   **And** chaque composant est déclaré dans `_GOVERNED_SCOPE` de `test_step3_governance_fr40.py` (preuve de gouvernance enregistrée)

2. **Given** une tentative d'ajout d'un composant dans `PRODUCT_SCOPE` sans déclaration correspondante dans `_GOVERNED_SCOPE`
   **When** le test `test_product_scope_has_governance_proof` s'exécute en CI
   **Then** le test échoue avec un message explicite listant les 3 obligations non satisfaites (AR13)
   **And** aucun ajout silencieux dans `PRODUCT_SCOPE` ne peut passer sans déclencher un échec CI

3. **Given** un composant connu dans `HA_COMPONENT_REGISTRY` mais dont `validate_projection()` retourne `is_valid=False` pour les capabilities présentées
   **When** la preuve de gouvernance FR40 est tentée pour ce composant
   **Then** la condition 2 de FR40 n'est pas satisfaite
   **And** le composant ne peut pas être déclaré dans `_GOVERNED_SCOPE` sans faire échouer son test de gouvernance nominale

4. **Given** un type de composant absent de `HA_COMPONENT_REGISTRY`
   **When** la preuve de gouvernance FR40 est tentée pour ce type
   **Then** la condition 1 de FR40 n'est pas satisfaite (`ha_component_unknown`)
   **And** le composant ne peut pas être déclaré dans `_GOVERNED_SCOPE` sans faire échouer son test de gouvernance de condition 1

5. **Given** les preuves de gouvernance FR40 des composants `light`, `cover`, `switch` formalisées rétroactivement dans `test_step3_governance_fr40.py`
   **When** la suite s'exécute
   **Then** `test_governance_fr40_proof_light()` — cas nominal + cas d'échec — passe
   **And** `test_governance_fr40_proof_cover()` — cas nominal uniquement (cover : `required_capabilities=[]` par design AR6) — passe, absence de cas d'échec structurel documentée
   **And** `test_governance_fr40_proof_switch()` — cas nominal + cas d'échec — passe

6. **Given** la suite complète après création de `test_step3_governance_fr40.py`
   **When** `python3 -m pytest tests/` s'exécute
   **Then** 0 failure, 0 error, total ≥ 357 (tests de la story ajoutés)
   **And** `PRODUCT_SCOPE` reste `["light", "cover", "switch"]` — cette story n'ouvre aucun composant

7. **Given** le fichier `test_step3_governance_fr40.py`
   **When** on consulte sa structure
   **Then** aucune référence à `http_server.py`, `decide_publication()`, ou flux MQTT n'est présente
   **And** le header documente explicitement que `PRODUCT_SCOPE` est une gouvernance statique de cycle, distincte de la décision de publication runtime (étape 4)

## Tasks / Subtasks

- [x] Task 1 — Créer `resources/daemon/tests/unit/test_step3_governance_fr40.py` — cadre de gouvernance FR40 (AC: #1, #2, #3, #4, #5)
  - [x] 1.1 — Header de fichier : docstring documentant FR40/AR13, la distinction gouvernance statique vs décision runtime, et que `_GOVERNED_SCOPE` est le verrou CI
  - [x] 1.2 — Définir `_GOVERNED_SCOPE = {"light": "test_governance_fr40_proof_light", "cover": "...", "switch": "..."}` — `dict` associant chaque composant de `PRODUCT_SCOPE` au nom exact de sa fonction de preuve FR40 ; commentaire documentant les 3 conditions FR40 et leurs mécanismes d'enforcement (AR13)
  - [x] 1.3 — Importer `PRODUCT_SCOPE`, `HA_COMPONENT_REGISTRY`, `validate_projection` depuis `validation.ha_component_registry` ; importer `LightCapabilities`, `CoverCapabilities`, `SwitchCapabilities` depuis `models.mapping` ; importer `pytest`
  - [x] 1.4 — Implémenter `test_product_scope_has_governance_proof(component)` via `@pytest.mark.parametrize("component", PRODUCT_SCOPE)` (AC: #1, #2)
    - [x] Assert `component in HA_COMPONENT_REGISTRY` — message : "condition 1 de FR40 non satisfaite"
    - [x] Assert `component in _GOVERNED_SCOPE` — message : "composant dans PRODUCT_SCOPE sans preuve de gouvernance — ajouter à _GOVERNED_SCOPE + test_governance_fr40_proof_{component}() (AR13)"
  - [x] 1.5 — Implémenter `test_governance_fr40_proof_light()` (AC: #5)
    - [x] Nominal : `validate_projection("light", LightCapabilities(has_on_off=True))` → `is_valid=True, reason_code=None`
    - [x] Échec : `validate_projection("light", LightCapabilities(has_on_off=False))` → `is_valid=False, reason_code="ha_missing_command_topic"`
  - [x] 1.6 — Implémenter `test_governance_fr40_proof_cover()` (AC: #5)
    - [x] Nominal : `validate_projection("cover", CoverCapabilities())` → `is_valid=True`
    - [x] Documenter dans la docstring : "cover a `required_capabilities=[]` — aucun cas d'échec par capabilities possible par design (AR6). Preuve de gouvernance complète sur le cas nominal seul."
  - [x] 1.7 — Implémenter `test_governance_fr40_proof_switch()` (AC: #5)
    - [x] Nominal : `validate_projection("switch", SwitchCapabilities(has_on_off=True))` → `is_valid=True, reason_code=None`
    - [x] Échec : `validate_projection("switch", SwitchCapabilities(has_on_off=False))` → `is_valid=False, reason_code="ha_missing_command_topic"`
  - [x] 1.8 — Implémenter `test_governance_gate_blocks_condition1_violation()` (AC: #4)
    - [x] Utiliser un type fictif non enregistré (ex. `"__gov_test_unknown__"`) avec `LightCapabilities(has_on_off=True)`
    - [x] Assert `result.is_valid is False, result.reason_code == "ha_component_unknown"`
    - [x] Docstring : "Un composant absent de HA_COMPONENT_REGISTRY ne satisfait pas la condition 1 de FR40 — son ajout à PRODUCT_SCOPE est interdit"
  - [x] 1.9 — Implémenter `test_governance_gate_blocks_condition2_violation()` (AC: #3)
    - [x] Montrer que `validate_projection` retourne `is_valid=False` quand les capabilities sont insuffisantes — utiliser un composant connu du registre avec des capabilities qui ne satisfont pas ses `required_capabilities`
    - [x] Assert `result.is_valid is False` avec le `reason_code` attendu
    - [x] Docstring : "Un composant connu du registre mais dont les capabilities ne satisfont pas validate_projection ne remplit pas la condition 2 de FR40 — sa preuve nominale est impossible dans cette configuration"

- [x] Task 2 — Vérifier la non-régression locale et la suite complète (AC: #6)
  - [x] 2.1 — `python3 -m pytest tests/unit/test_ha_component_registry.py tests/unit/test_step3_validate_projection.py tests/unit/test_step3_governance_fr40.py` → 0 failure
  - [x] 2.2 — `python3 -m pytest tests/` → 0 failure, 0 error ; noter le total dans `Debug Log References`
  - [x] 2.3 — Vérifier que `PRODUCT_SCOPE` est toujours `["light", "cover", "switch"]` après l'exécution

- [x] Task 3 — Mettre à jour la story et le tracker
  - [x] 3.1 — Mettre à jour le statut dans `_bmad-output/implementation-artifacts/sprint-status.yaml` à `in-progress` au démarrage, puis `done` à la complétion

## Dev Notes

### Contexte dans le pipeline

Story 3.3 clôt `pe-epic-3`. Elle s'inscrit dans la séquence stricte :

- **Story 3.1** : a créé `validation/ha_component_registry.py` avec `HA_COMPONENT_REGISTRY`, `PRODUCT_SCOPE`, et les invariants des 3 états
- **Story 3.2** : a implémenté `validate_projection()` — preuve que l'état `validable` est testable en isolation
- **Story 3.3** (cette story) : installe le **cadre de gouvernance FR40** — rend l'état `ouvert` vérifiable et non-arbitraire, **sans ouvrir aucun nouveau composant**
- **Story 4.1** : consommera `PRODUCT_SCOPE` dans `decide_publication()` — le reason_code `ha_component_not_in_product_scope` (classe 3) appartient à l'étape 4
- **Story 5.1** : orchestrera l'étape 3 dans le flux complet

### Modèle à 3 états — rappel critique

```
connu    := composant présent dans HA_COMPONENT_REGISTRY
validable := validate_projection() aboutit positivement sur cas nominaux représentatifs
ouvert   := présent dans PRODUCT_SCOPE ET preuve de gouvernance FR40 dans le même incrément
```

**Séquence stricte et non commutative : `connu → validable → ouvert`.**

Ces états sont **distincts des étapes du pipeline** :
- Un composant peut être `connu` sans qu'aucun équipement ait passé l'étape 3
- Un composant peut être `validable` par test sans être `ouvert` dans ce cycle
- La décision de publication runtime (étape 4) consomme `PRODUCT_SCOPE` comme fait établi — elle ne définit pas la gouvernance

### Périmètre exact de cette story

**Ce que cette story produit :**
- Un fichier `test_step3_governance_fr40.py` qui est le verrou CI de FR40
- Des preuves de gouvernance rétroactives pour `light`, `cover`, `switch` (déjà dans `PRODUCT_SCOPE`)
- Des tests négatifs montrant ce qui bloque une ouverture non gouvernée

**Ce que cette story ne fait pas :**
- Elle n'ouvre aucun composant dans `PRODUCT_SCOPE`
- Elle ne modifie pas `ha_component_registry.py` (ni `PRODUCT_SCOPE`, ni le registre)
- Elle ne modifie pas `test_ha_component_registry.py`
- Elle ne modifie pas `test_step3_validate_projection.py`

### Les 3 conditions de FR40 — où vit chaque preuve

| Condition | Mécanisme d'enforcement | Responsable |
|---|---|---|
| 1. Composant connu dans `HA_COMPONENT_REGISTRY` | `test_product_scope_has_governance_proof` — assert `component in HA_COMPONENT_REGISTRY` | CI — automatique |
| 2. `validate_projection()` aboutit positivement sur cas nominaux + négatifs | `test_governance_fr40_proof_{type}()` dans `_GOVERNED_SCOPE` | CI — automatique |
| 3. Tests de non-régression passent dans le même incrément | `pytest tests/` | CI — gate avant merge |

Le mécanisme d'enforcement CI fonctionne ainsi :
- `_GOVERNED_SCOPE` est le registre audité des ouvertures gouvernées
- `test_product_scope_has_governance_proof` est le gardien : si un composant entre dans `PRODUCT_SCOPE` sans être dans `_GOVERNED_SCOPE`, le test **échoue automatiquement**
- Pour ajouter un composant à `_GOVERNED_SCOPE`, il faut ajouter son `test_governance_fr40_proof_{type}()` — **la code review le vérifie**
- Les deux ensemble forment le verrou actif de FR40 : code review + CI

### Gouvernance `cover` — absence de cas d'échec par design

`cover` a `required_capabilities: []` dans le registre (AR6 : `cover` read-only valide selon architecture HA MQTT). `validate_projection("cover", any_caps)` retourne toujours `is_valid=True`. La preuve de gouvernance pour `cover` est complète sur le cas nominal seul. Documenter explicitement dans la docstring de `test_governance_fr40_proof_cover()` que l'absence de cas d'échec est voulue.

### Séparation stricte : gouvernance statique vs décision runtime

`PRODUCT_SCOPE` est un artefact **statique de cycle**, modifié uniquement lors de l'implémentation d'une story dédiée satisfaisant FR40. Il ne doit **jamais** être consulté depuis `validate_projection()`. Il ne doit **jamais** être modifié dynamiquement à l'exécution.

La décision runtime "ce composant n'est pas dans le scope produit" (`ha_component_not_in_product_scope`) appartient à l'étape 4 (`decide_publication()`), pas à l'étape 3.

### Pas de conftest.py

Les helpers locaux (types de capabilities pour les tests négatifs) doivent être définis directement dans `test_step3_governance_fr40.py`. Ne pas créer de `conftest.py`, ne pas importer depuis d'autres fichiers de test.

### Fichiers à créer / modifier

| Fichier | Action |
|---|---|
| `resources/daemon/tests/unit/test_step3_governance_fr40.py` | **Créer** — cadre de gouvernance FR40 |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | **Modifier** — status story 3.3 |

**Fichiers explicitement inchangés (hors scope) :**

| Fichier | Raison |
|---|---|
| `resources/daemon/validation/ha_component_registry.py` | PRODUCT_SCOPE inchangé — aucun composant ouvert dans cette story |
| `resources/daemon/tests/unit/test_ha_component_registry.py` | Aucun invariant à mettre à jour |
| `resources/daemon/tests/unit/test_step3_validate_projection.py` | Aucune docstring à toucher — la story ne modifie pas PRODUCT_SCOPE |
| `resources/daemon/transport/http_server.py` | Hors scope — Story 5.1 |
| `resources/daemon/models/cause_mapping.py` | Hors scope — pe-epic-4 |
| `resources/daemon/mapping/*.py` | Hors scope — étape 2 figée |
| `resources/daemon/discovery/publisher.py` | Hors scope — étape 5 |

### Dev Agent Guardrails

- Ne **pas** modifier `PRODUCT_SCOPE` — aucun composant n'est ouvert dans cette story
- Ne **pas** modifier `validate_projection()` — correcte depuis Story 3.2
- Ne **pas** modifier `ha_component_registry.py` sauf besoin mécanique minimal documenté
- Ne **pas** conditionner `validate_projection()` à `PRODUCT_SCOPE` — violation d'architecture
- Ne **pas** brancher la gouvernance sur `decide_publication()` — Story 4.1
- Ne **pas** référencer `http_server.py`, MQTT, broker, ou publication dans les tests de gouvernance
- Ne **pas** utiliser `PRODUCT_SCOPE` comme argument de "ce composant peut être publié" — c'est la responsabilité de l'étape 4
- Ne **pas** ouvrir un composant "pour démonstration" — les tests négatifs (AC #3, #4) utilisent des types fictifs ou des configurations insuffisantes sur des composants déjà ouverts
- **Confirmer** que `_GOVERNED_SCOPE` est un `dict` Python — clés = composants, valeurs = noms des fonctions de preuve FR40 ; assertion `in` en O(1)
- **Confirmer** que `set(_GOVERNED_SCOPE.keys()) == set(PRODUCT_SCOPE)` à la fin de la story — égalité stricte des clés

### Project Structure Notes

Localisation des fichiers existants :

- `resources/daemon/validation/ha_component_registry.py` — lu pour import mais non modifié
- `resources/daemon/tests/unit/test_ha_component_registry.py` — tests Story 3.1 (pas de modification)
- `resources/daemon/tests/unit/test_step3_validate_projection.py` — tests Story 3.2 (pas de modification)
- `resources/daemon/tests/unit/test_step3_governance_fr40.py` — **créé** (Task 1)

Pattern de nommage : `test_step3_*.py`. Le fichier de gouvernance suit ce pattern.

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 3.3] — user story, AC, Dev notes d'origine
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Feature 7] — FR36, FR37, FR38, FR39, FR40
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §AR6] — 3 états verrouillés (`connu → validable → ouvert`), séquence stricte
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §AR13] — NFR10 : toute modification de PRODUCT_SCOPE exige les tests FR40 dans le même incrément
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §AR4, §AR5] — structure registre, valeur de départ de PRODUCT_SCOPE
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §P4] — règle d'accès centralisé au registre
- [Source: `resources/daemon/validation/ha_component_registry.py`] — état réel : `PRODUCT_SCOPE = ["light", "cover", "switch"]`, registre, `validate_projection()`
- [Source: `resources/daemon/tests/unit/test_ha_component_registry.py`] — tests invariants 3.1 — non modifiés par cette story
- [Source: `resources/daemon/tests/unit/test_step3_validate_projection.py`] — tests 3.2 — non modifiés par cette story

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Task 2.1 : 28/28 tests ciblés PASS (test_ha_component_registry + test_step3_validate_projection + test_step3_governance_fr40)
- Task 2.2 : 365 PASS, 0 failure, 0 error — total ≥ 357 (AC #6) ✅
- Task 2.3 : PRODUCT_SCOPE = ["light", "cover", "switch"] — inchangé ✅

### Completion Notes List

- Créé `test_step3_governance_fr40.py` — 8 tests : 3 paramétrés (gardien CI FR40), 3 preuves nominales (light/cover/switch), 2 gardiens conditions 1 et 2
- `_GOVERNED_SCOPE` dict — association explicite composant → nom de preuve (correction review point 1)
- 3 conditions FR40 documentées avec mécanisme d'enforcement dans le bloc de commentaire `_GOVERNED_SCOPE` (correction review point 2)
- Condition 3 (non-régression) documentée comme gate CI (`pytest tests/`) — aucun faux code CI ajouté
- `_GOVERNED_SCOPE.keys()` == `set(PRODUCT_SCOPE)` — égalité stricte confirmée
- Aucun composant ouvert dans PRODUCT_SCOPE — story purement governance
- Aucun fichier de production modifié — seul le fichier de test modifié
- cover : absence de cas d'échec documentée par design (AR6 : required_capabilities=[])
- AC #7 respecté : aucune référence à http_server.py, decide_publication(), MQTT dans le fichier de test

### File List

- `resources/daemon/tests/unit/test_step3_governance_fr40.py` — **créé**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — **modifié** (status story 3.3)
- `_bmad-output/implementation-artifacts/3-3-gouvernance-d-ouverture-un-composant-validable-peut-etre-ajoute-a-product-scope-si-et-seulement-si-les-3-conditions-de-fr40-sont-satisfaites-dans-le-meme-increment.md` — **modifié** (tâches, statut, notes)

## Change Log

- 2026-04-13 — Implémentation Story 3.3 : création de `test_step3_governance_fr40.py` — cadre de gouvernance FR40 avec verrou CI (`_GOVERNED_SCOPE`), preuves rétroactives pour light/cover/switch, gardiens conditions 1 et 2. 8 tests ajoutés, 365/365 non-régression PASS.
- 2026-04-13 — Correction review (2 points) : `_GOVERNED_SCOPE` transformé en dict `{component: proof_fn_name}` (lien explicite composant → preuve) ; documentation des 3 conditions FR40 avec enforcement dans le bloc `_GOVERNED_SCOPE` et dans la docstring du gardien CI. 365/365 PASS.
- 2026-04-13 — Correctif documentaire post-review : réalignement story file avec l'implémentation acceptée — Task 1.2 décrit la structure `dict` (non `set`), guardrails corrigés (`dict` + `_GOVERNED_SCOPE.keys()`), Project Structure Notes mis à jour (fichier de test existe). Aucun changement de code.
