# Story 7.2 : Vague cible HA — les types candidats sont modélisés dans le registre comme `connus`, avec contraintes explicites et périmètre borné

Status: review

## Story

En tant que mainteneur de jeedom2ha,
je veux déclarer explicitement la vague cible de pe-epic-7 dans le registre et dans les artefacts de story, avec les contraintes documentées et les types candidats identifiés,
afin de préparer une ouverture produit pilotable, bornée et testable dans le même incrément plutôt qu'une extension opportuniste du scope.

## Déclaration de la vague cible pe-epic-7

**Vague cible déclarée : `sensor` et `binary_sensor`**

**Justification :**
- Types Jeedom les plus fréquents après `light` / `cover` / `switch` (capteurs de température, humidité, présence, mouvement)
- Contrainte unique et partagée : `has_state` — validation en isolation triviale (story 7.3)
- Entrées déjà présentes dans `HA_COMPONENT_REGISTRY` per architecture D3 — vérification et consolidation, pas recréation
- Testables dans le même incrément via stories 7.3 et 7.4

**Hors vague (non ciblés par pe-epic-7) :** `button`, `number`, `select`, `climate`
— présents dans le registre comme `connus` mais ni vérifiés ni ouverts dans ce cycle.

**État atteint par cette story :** `connu` (entrée dans `HA_COMPONENT_REGISTRY` + dataclass capabilities dédiée). L'état `validable` est atteint en 7.3, l'état `ouvert` en 7.4. Aucune modification de `PRODUCT_SCOPE` dans cette story.

**Absence de mapper :** aucune story pe-epic-7 ne crée de mapper Jeedom → `sensor`/`binary_sensor`. L'ouverture en 7.4 est une ouverture de governance (pipeline peut valider et décider) — l'exploitation réelle en production viendra d'un cycle futur avec mapper dédié.

## Acceptance Criteria

### AC1 — Entrées registre complètes et vérifiées pour la vague cible

**Given** les entrées `sensor` et `binary_sensor` dans `HA_COMPONENT_REGISTRY`
**When** elles sont inspectées après implémentation
**Then** chaque type dispose de `required_fields` non vide et de `required_capabilities` non vide
**And** `required_capabilities` inclut `"has_state"` pour les deux types
**And** `required_fields` inclut au moins `"state_topic"`, `"platform"`, `"availability"` pour les deux types
**And** les entrées sont identiques à la spec architecture D3 — aucun champ ajouté ou supprimé opportunément
_[Source : AR4, AR6, architecture D3]_

### AC2 — Frontière de vague : types hors vague non affectés

**Given** les types hors vague (`button`, `number`, `select`, `climate`) dans `HA_COMPONENT_REGISTRY`
**When** cette story est implémentée
**Then** leurs entrées registry restent strictement identiques à leur état pré-story
**And** aucun de ces types ne devient implicitement `validable` ou `ouvert` par effet de bord
**And** `PRODUCT_SCOPE` reste `["light", "cover", "switch"]` — inchangé
_[Source : AR6, AR13, epics Story 7.2 AC2]_

### AC3 — `SensorCapabilities` modélise l'état `connu` de façon explicite

**Given** le module `models/mapping.py`
**When** la story est implémentée
**Then** une dataclass `SensorCapabilities` est présente avec au moins le champ `has_state: bool`
**And** `MappingCapabilities` Union inclut `SensorCapabilities`
**And** `_resolve_capability("has_state", SensorCapabilities(has_state=True))` retourne `True`
**And** `_resolve_capability("has_state", SensorCapabilities(has_state=False))` retourne `False`
**And** `_resolve_capability()` utilise `isinstance(capabilities, SensorCapabilities)` (pas uniquement le fallback `getattr`)
_[Source : AR4, AR6 état `connu` = contraintes modélisées explicitement]_

### AC4 — `SensorCapabilities` compatible avec `validate_projection()` sans régression

**Given** `validate_projection("sensor", SensorCapabilities(has_state=True))`
**When** la fonction est appelée
**Then** elle retourne `ProjectionValidity(is_valid=True)` — aucune missing capability

**Given** `validate_projection("binary_sensor", SensorCapabilities(has_state=True))`
**When** la fonction est appelée
**Then** elle retourne `ProjectionValidity(is_valid=True)`

**Given** `validate_projection("sensor", SensorCapabilities(has_state=False))`
**When** la fonction est appelée
**Then** elle retourne `ProjectionValidity(is_valid=False, reason_code="ha_missing_state_topic")`

**And** les cas nominaux `light`, `cover`, `switch` existants continuent de passer sans modification (non-régression)
_[Source : Story 3.2 pattern, AR7, NFR9]_

### AC5 — Aucun changement de `PRODUCT_SCOPE` ni d'état d'ouverture

**Given** le fichier `validation/ha_component_registry.py` après implémentation
**When** `PRODUCT_SCOPE` est inspecté
**Then** sa valeur est exactement `["light", "cover", "switch"]`
**And** `sensor` et `binary_sensor` ne sont pas dans `PRODUCT_SCOPE`
**And** aucun composant n'a été ajouté ou retiré de `PRODUCT_SCOPE`
_[Source : AR5, AR13, Story 7.2 dev notes, NFR10]_

### AC6 — Non-régression corpus existant

**Given** le corpus de tests de non-régression existant
**When** les tests sont exécutés après implémentation de cette story
**Then** le corpus complet passe sans modification
**And** les tests de `test_ha_component_registry.py` passent — notamment `test_product_scope_initial_value`
**And** les tests de `test_step3_validate_projection.py` passent — les `_SensorLikeCapabilities` inline continuent de fonctionner en parallèle
**And** aucun test existant n'est modifié ou supprimé pour compenser un changement
_[Source : NFR11, NFR12, FR45]_

## Tasks / Subtasks

- [x] Task 1 — Vérifier et consolider les entrées registry pour la vague cible (AC: #1, #2)
  - [x] Relire les entrées `sensor` et `binary_sensor` dans `HA_COMPONENT_REGISTRY` et vérifier leur alignement exact avec l'architecture D3
  - [x] Si une entrée dévie de la spec D3, corriger le minimum nécessaire (ne pas enrichir opportunément)
  - [x] Vérifier que `_CAPABILITY_TO_REASON` couvre `"has_state"` → `("ha_missing_state_topic", ["state_topic"])` — déjà présent, confirmer
  - [x] Poser un commentaire inline dans `ha_component_registry.py` identifiant explicitement `sensor` et `binary_sensor` comme la vague cible pe-epic-7

- [x] Task 2 — Ajouter `SensorCapabilities` dans `models/mapping.py` (AC: #3, #4)
  - [x] Ajouter `@dataclass SensorCapabilities` avec `has_state: bool = False` et éventuellement `on_off_confidence: str = "unknown"` si applicable
  - [x] Mettre à jour la `Union` `MappingCapabilities` pour inclure `SensorCapabilities`
  - [x] Mettre à jour `_resolve_capability()` dans `ha_component_registry.py` avec bloc `isinstance(capabilities, SensorCapabilities)` pour `has_state`
  - [x] Vérifier que `from models.mapping import ..., SensorCapabilities` ne crée pas de dépendance circulaire

- [x] Task 3 — Écrire `test_story_7_2_wave_registry.py` (AC: #1-#6)
  - [x] Test AC1 : entrées sensor/binary_sensor présentes avec required_fields et required_capabilities corrects
  - [x] Test AC2 : types hors vague non affectés — snapshot pré/post des entrées button/number/select/climate
  - [x] Test AC3 : `SensorCapabilities` dataclass importable, `_resolve_capability` via isinstance
  - [x] Test AC4 : appels `validate_projection` avec `SensorCapabilities` — cas nominal et cas d'échec pour sensor et binary_sensor
  - [x] Test AC5 : `PRODUCT_SCOPE == ["light", "cover", "switch"]` toujours vrai
  - [x] Test AC6 (import test) : les doubles locaux `_SensorLikeCapabilities` de `test_step3_validate_projection.py` continuent de fonctionner — à vérifier en exécution, pas à modifier

- [x] Task 4 — Verrouiller la non-régression et la frontière de périmètre (AC: #2, #5, #6)
  - [x] Exécuter le corpus complet — cible : 0 régression
  - [x] Vérifier que `test_product_scope_initial_value` passe
  - [x] Vérifier que `test_all_registry_capabilities_have_reason_mapping` passe avec les nouvelles capabilities
  - [x] Confirmer qu'aucun fichier `cause_mapping.py`, `PRODUCT_SCOPE`, `cause_label/cause_action` ni mapper (`mapping/*.py`) n'a été touché
  - [x] Documenter le delta de schéma attendu : ajout de `SensorCapabilities` dans `models/mapping.py`, commentaire vague dans `ha_component_registry.py`, imports mis à jour dans `ha_component_registry.py`

## Dev Notes

### État actuel du code à exploiter

- `HA_COMPONENT_REGISTRY` dans `validation/ha_component_registry.py` contient déjà les entrées `sensor` et `binary_sensor` avec les bonnes contraintes (spec D3 architecture) — **ne pas recréer, vérifier seulement**.
- `_CAPABILITY_TO_REASON` couvre déjà `has_state` → `("ha_missing_state_topic", ["state_topic"])` — **aucune modification nécessaire**.
- `_resolve_capability("has_state", caps)` utilise `getattr(caps, "has_state", False)` comme fallback — fonctionne mais n'est pas typé explicitement. Story 7.2 ajoute l'`isinstance` pour être cohérent avec le pattern des types existants.
- `test_step3_validate_projection.py` utilise des doubles locaux `_SensorLikeCapabilities` et `_SelectLikeCapabilities`. Ces doubles continuent de fonctionner après l'ajout de `SensorCapabilities` — pas de conflit, les deux approches coexistent.
- `MappingCapabilities = Union[LightCapabilities, CoverCapabilities, SwitchCapabilities]` dans `models/mapping.py` — à étendre.

### Fichiers / zones candidates

- `resources/daemon/models/mapping.py` — **cible principale** : ajouter `SensorCapabilities`, mettre à jour `MappingCapabilities` Union.
- `resources/daemon/validation/ha_component_registry.py` — ajout commentaire vague cible + bloc `isinstance(SensorCapabilities)` dans `_resolve_capability()` + import `SensorCapabilities`.
- `resources/daemon/tests/unit/test_story_7_2_wave_registry.py` — **nouveau fichier** : tests de la wave boundary, registry completeness, capabilities.
- Fichiers non touchés : `mapping/light.py`, `mapping/cover.py`, `mapping/switch.py`, `models/cause_mapping.py`, `transport/http_server.py`, `core/`, `desktop/`.

### `SensorCapabilities` — design decision

`sensor` et `binary_sensor` partagent la même exigence unique `has_state`. Un seul dataclass suffit :

```python
@dataclass
class SensorCapabilities:
    """Capabilities detected for sensor/binary_sensor Jeedom equipment.

    Story 7.2 — state connu pour la vague cible pe-epic-7.
    """
    has_state: bool = False
    on_off_confidence: str = "unknown"  # conservé par symétrie avec LightCapabilities
```

Le champ `on_off_confidence` est optionnel — l'inclure par cohérence avec le pattern existant n'est pas obligatoire. Décision au dev : `has_state: bool = False` seul est suffisant.

### Pattern `_resolve_capability()` à respecter

```python
def _resolve_capability(abstract: str, capabilities: object) -> bool:
    if abstract == "has_command":
        if isinstance(capabilities, LightCapabilities):
            ...
        # etc.
    if abstract == "has_state":
        if isinstance(capabilities, SensorCapabilities):   # ← NOUVEAU
            return capabilities.has_state
        if isinstance(capabilities, SwitchCapabilities):
            return capabilities.has_state
        # Fallback générique conservé pour les types futurs
        return bool(getattr(capabilities, "has_state", False))
```

**Ordre critique** : le bloc `SwitchCapabilities` pour `has_state` existe déjà — ne pas le supprimer, ajouter `SensorCapabilities` avant ou après en bloc séparé. Le fallback `getattr` reste en dernière position.

### Contrainte AR3 — pas d'import mapping/

`validation/ha_component_registry.py` importe `SensorCapabilities` depuis `models.mapping` — OK. Ce module **ne doit pas importer** depuis `mapping/`, `discovery/`, `transport/`. Le test `test_module_no_forbidden_imports` vérifie cela automatiquement.

### Absence de mapper — implication pour la suite

`sensor` et `binary_sensor` n'ont pas de mapper dans `mapping/`. En conséquence :
- Aucun équipement Jeedom réel ne produira `ha_entity_type="sensor"` via le pipeline en production (étape 2 retourne `no_mapping` ou `ambiguous_skipped` pour les équipements non mappés).
- L'ouverture en 7.4 ouvre la governance, pas la fonctionnalité visible utilisateur. C'est intentionnel.
- Le mapper sensor est hors scope pe-epic-7 — travail d'un cycle futur.
- `validate_projection("sensor", SensorCapabilities(has_state=True))` est tout de même testable en isolation (story 7.3) : la fonction pure n'a pas besoin d'un mapper pour fonctionner.

### Dev Agent Guardrails

- **Ne pas modifier `PRODUCT_SCOPE`** — `test_product_scope_initial_value` doit rester vert.
- **Ne pas toucher `cause_mapping.py`** — aucun nouveau `reason_code` dans cette story.
- **Ne pas créer de mapper** (`mapping/sensor.py`) — hors scope.
- **Ne pas enrichir opportunément** les entrées registry hors vague (`button`, `number`, `select`, `climate`).
- **Ne pas supprimer les doubles locaux** `_SensorLikeCapabilities` dans `test_step3_validate_projection.py` — ils coexistent avec `SensorCapabilities`, les deux approches sont valides.
- **Isolation des tests** : `test_story_7_2_wave_registry.py` doit s'exécuter sans MQTT, daemon, ni dépendances externes.
- **Minimal delta** : si les entrées registry sont déjà conformes à D3, ne rien modifier dans `ha_component_registry.py` sauf le commentaire vague et le bloc `isinstance`.

### Stratégie de test ciblée

Tests dans `test_story_7_2_wave_registry.py` :

```
test_wave_target_types_in_registry()          # sensor + binary_sensor présents
test_wave_types_have_has_state_capability()   # required_capabilities = ["has_state"]
test_wave_types_have_state_topic_field()      # required_fields inclut state_topic
test_non_wave_types_not_in_product_scope()    # button/number/select/climate hors scope
test_product_scope_unchanged()               # ["light","cover","switch"] exact
test_sensor_capabilities_dataclass()          # SensorCapabilities instanciable
test_resolve_capability_has_state_sensor()    # isinstance path fonctionne
test_validate_projection_sensor_nominal()     # is_valid=True avec has_state=True
test_validate_projection_sensor_no_state()    # is_valid=False reason ha_missing_state_topic
test_validate_projection_binary_sensor_nominal()
test_validate_projection_binary_sensor_no_state()
test_non_wave_registry_entries_unchanged()   # snapshot structural des types hors vague
```

### Prépare 7.3 et 7.4 sans les préfigurer

- 7.3 écrira les cas nominaux et d'échec pour `validate_projection()` — les tests de cette story (Task 3) en posent quelques-uns, 7.3 les complètera et les officialisera.
- 7.4 ajoutera `sensor` et `binary_sensor` à `PRODUCT_SCOPE` après que FR40 est satisfait — cette story pose l'état `connu`, pas l'état `ouvert`.
- Aucun code de cette story ne préfigure un mapper, un CTA utilisateur, ou une modification de `cause_action`.

### Project Structure Notes

- `models/mapping.py` : fichier de modèles de données — ajouter `SensorCapabilities` par analogie avec `LightCapabilities`, `CoverCapabilities`, `SwitchCapabilities`. Conserver l'ordre alphabétique ou logique existant.
- `validation/ha_component_registry.py` : import de `SensorCapabilities` en tête du fichier, bloc `isinstance` dans `_resolve_capability()`.
- Tests : fichier `test_story_7_2_wave_registry.py` — naming pattern cohérent avec `test_story_7_1_projection_validity_diagnostic.py`.

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` — Epic 7, Story 7.2, AR4, AR6, AR13]
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` — D2, D3, D4, P4, P6]
- [Source: `resources/daemon/validation/ha_component_registry.py` — HA_COMPONENT_REGISTRY, PRODUCT_SCOPE, _CAPABILITY_TO_REASON, _resolve_capability()]
- [Source: `resources/daemon/models/mapping.py` — LightCapabilities, CoverCapabilities, SwitchCapabilities, MappingCapabilities, ProjectionValidity]
- [Source: `resources/daemon/tests/unit/test_ha_component_registry.py` — test_product_scope_initial_value, test_all_registry_capabilities_have_reason_mapping]
- [Source: `resources/daemon/tests/unit/test_step3_validate_projection.py` — _SensorLikeCapabilities (double local à conserver)]
- [Source: `_bmad-output/implementation-artifacts/7-1-...md` — Story 7.1 done, projection_validity exposé, socle stable]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex — 2026-04-25

### Debug Log References

- Préflight Git : worktree dédié `/Users/alexandre/Dev/jeedom/plugins/jeedom2ha-story-pe-7.2`, branche `story/pe-7.2-wave-registry`, working tree clean avant implémentation.
- RED : `python3 -m pytest resources/daemon/tests/unit/test_story_7_2_wave_registry.py` → échec attendu `ImportError: cannot import name 'SensorCapabilities'`.
- GREEN ciblé : `python3 -m pytest resources/daemon/tests/unit/test_story_7_2_wave_registry.py` → 13 passed.
- Non-régression ciblée : `python3 -m pytest resources/daemon/tests/unit/test_ha_component_registry.py resources/daemon/tests/unit/test_step3_validate_projection.py` → 20 passed.
- Corpus complet : `python3 -m pytest` → 1150 passed, 993 warnings de dépréciation existants.
- Qualité : `python3 -m flake8 resources/daemon/models/mapping.py resources/daemon/validation/ha_component_registry.py resources/daemon/tests/unit/test_story_7_2_wave_registry.py` → 0.

### Implementation Plan

- Conserver les entrées `sensor` et `binary_sensor` strictement conformes à D3, sans ajout de champ ni changement de `PRODUCT_SCOPE`.
- Ajouter uniquement `SensorCapabilities(has_state: bool = False)` comme dataclass dédiée à l'état `connu`.
- Résoudre `has_state` via un chemin typé `isinstance(SensorCapabilities)` tout en conservant le fallback `getattr` pour les doubles et types futurs.
- Couvrir la vague cible, la frontière hors vague, `PRODUCT_SCOPE`, les cas `validate_projection()` et la non-régression des doubles `_SensorLikeCapabilities`.

### Completion Notes List

- Entrées `sensor` et `binary_sensor` vérifiées conformes à l'architecture D3 : `required_fields == ["state_topic", "platform", "availability"]`, `required_capabilities == ["has_state"]`.
- `SensorCapabilities` ajouté dans `models/mapping.py` et inclus dans `MappingCapabilities`.
- `_resolve_capability("has_state", ...)` utilise désormais explicitement `isinstance(capabilities, SensorCapabilities)` avant le fallback générique.
- Nouveau fichier de tests story 7.2 couvrant AC1 à AC6, avec snapshots stricts des types hors vague et vérification de `PRODUCT_SCOPE`.
- Aucun mapper, aucun fichier UX, aucun `cause_mapping.py`, aucun `PRODUCT_SCOPE` et aucun `cause_label/cause_action` modifié.

### File List

- `_bmad-output/implementation-artifacts/7-2-vague-cible-ha-les-types-candidats-sont-modelises-dans-le-registre-comme-connus-avec-contraintes-explicites-et-perimetre-borne.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/models/mapping.py`
- `resources/daemon/validation/ha_component_registry.py`
- `resources/daemon/tests/unit/test_story_7_2_wave_registry.py`

### Change Log

- 2026-04-25 — Implémentation story 7.2 : vague cible `sensor`/`binary_sensor` déclarée comme connue, `SensorCapabilities` ajouté, tests AC1-AC6 ajoutés, non-régression complète verte.
- 2026-04-27 — Senior Developer Review (BMAD) PASS — verdict `PASS`, 0 finding HIGH/MEDIUM, 1 LOW non bloquante (cf. section ci-dessous). Story laissée en `review`.

## Senior Developer Review (AI) — 2026-04-27

**Reviewer :** Senior Developer + QA BMAD (claude-opus-4-7)
**Verdict :** ✅ **PASS** — aucune correction requise.

### Préflight Git
- Branche active : `story/pe-7.2-wave-registry` ✅
- Worktree dédié : `/Users/alexandre/Dev/jeedom/plugins/jeedom2ha-story-pe-7.2` ✅
- `main` non modifié (working tree clean dans le worktree principal) ✅
- File List vs `git status` : 100% concordant (4 modif + 1 nouveau = 5 entrées) ✅

### Fichiers inspectés
- `resources/daemon/models/mapping.py` (diff +19 / -3) — `SensorCapabilities` ajouté, `MappingCapabilities` Union étendu, type-hint de `MappingResult.capabilities` consolidé en `Optional[MappingCapabilities]`.
- `resources/daemon/validation/ha_component_registry.py` (diff +11 / -1) — import `SensorCapabilities`, commentaire vague cible, bloc `isinstance(SensorCapabilities)` dans `_resolve_capability("has_state", ...)` avant fallback `getattr`.
- `resources/daemon/tests/unit/test_story_7_2_wave_registry.py` (nouveau, 13 tests) — couvre AC1-AC6 strictement, snapshot des 4 types hors-vague, `inspect.getsource` pour verrouiller le chemin `isinstance`.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — story 7.2 = `review`, last_updated 2026-04-25.
- `_bmad-output/implementation-artifacts/7-2-...md` — File List, Change Log, Dev Agent Record cohérents.

### Confirmation des guardrails
| Guardrail | Statut |
|---|---|
| Aucun mapper `sensor.py` créé | ✅ |
| `mapping/light.py`/`cover.py`/`switch.py` non touchés | ✅ |
| `PRODUCT_SCOPE == ["light","cover","switch"]` inchangé | ✅ |
| `models/cause_mapping.py` non touché | ✅ |
| Aucun `cause_label`/`cause_action` modifié | ✅ |
| Aucune surface FE/UX modifiée | ✅ |
| Doubles locaux `_SensorLikeCapabilities` conservés et toujours verts | ✅ |
| Hors-vague `button`/`number`/`select`/`climate` non impactés | ✅ |
| Fallback `getattr(..., "has_state", False)` conservé | ✅ |

### Validation AC1-AC6
- **AC1** ✅ PASS — `test_wave_target_types_in_registry` + `test_wave_types_have_exact_d3_constraints`
- **AC2** ✅ PASS — `test_non_wave_registry_entries_unchanged` + `test_non_wave_types_not_in_product_scope`
- **AC3** ✅ PASS — `test_sensor_capabilities_dataclass_defaults` + `test_resolve_capability_has_state_sensor` + `test_resolve_capability_uses_sensor_isinstance_path` (verrou source)
- **AC4** ✅ PASS — 4 cas validate_projection (nominal + échec, sensor + binary_sensor) + non-régression `test_step3_validate_projection.py` 11/11
- **AC5** ✅ PASS — `test_product_scope_unchanged` (assert exact)
- **AC6** ✅ PASS — corpus complet 1150 passed (vs 1137 baseline pe-7.1)

### Tests exécutés
| Commande | Résultat |
|---|---|
| `pytest test_story_7_2_wave_registry.py` | **13 passed** |
| `pytest test_ha_component_registry.py test_step3_validate_projection.py` | **20 passed** |
| `pytest` (corpus complet, racine worktree) | **1150 passed**, 993 warnings (préexistants) |
| `flake8` sur les 3 fichiers cibles | **0 erreur** |

### Remarques non bloquantes
- **LOW (dette préexistante, hors scope 7.2)** : `MappingResult.__post_init__` (`models/mapping.py:140-142`) lève une `ValueError` listant uniquement `« LightCapabilities or CoverCapabilities »` — message déjà obsolète depuis Story 2.4 (Switch) et reste muet sur Sensor. À cleanup dans un futur cycle de dette technique (Epic 4 recadrage UX ou suite pe-epic-7). **Ne pas corriger ici** : la story interdit explicitement les enrichissements opportunistes, et `SensorCapabilities` ne sera pas utilisé comme `MappingResult.capabilities` en production tant que 7.4 + mapper sensor n'existent pas.

### Décision workflow BMAD
- Statut conservé : `review` (pas de transition automatique vers `done` — décision laissée à l'opérateur BMAD selon le pattern projet : merge PR puis closeout pe-7.2).
- Aucun push, aucun merge, aucune modification du code applicatif effectués pendant cette review.
