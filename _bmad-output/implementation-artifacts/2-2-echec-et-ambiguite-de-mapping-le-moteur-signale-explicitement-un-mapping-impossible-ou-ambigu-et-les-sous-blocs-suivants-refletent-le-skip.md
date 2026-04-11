# Story 2.2 : Échec et ambiguïté de mapping — le moteur signale explicitement un mapping impossible ou ambigu, et les sous-blocs suivants reflètent le skip

Status: done

## Story

En tant qu'utilisateur,
je veux voir, lorsque le système ne peut pas produire un mapping utilisable pour un équipement éligible, un motif d'échec de mapping clair et distinct de tout refus ultérieur du pipeline,
afin de comprendre que l'équipement a été reconnu par Jeedom mais que le système n'a pas pu déterminer quel type d'entité HA il devrait représenter.

## Acceptance Criteria

1. **Given** un équipement éligible avec des generic_types conflictuels (ex. `LIGHT_ON` + `FLAP_UP`)
   **When** l'étape de mapping s'exécute
   **Then** le sous-bloc `mapping` contient `confidence="ambiguous"` et un `reason_code` de classe 1 (ex. `"conflicting_generic_types"`)
   **And** le sous-bloc `projection_validity` peut être présent avec `is_valid=None` et `reason_code="skipped_no_mapping_candidate"` — jamais absent (AR2)
   **And** le sous-bloc `publication_decision_ref` peut être présent avec `should_publish=False` et un motif explicite — jamais absent (AR2)

2. **Given** un équipement éligible où aucun generic_type ne produit un mapping connu
   **When** l'étape de mapping s'exécute
   **Then** le mapper retourne `None` (aucun `MappingResult` produit)
   **And** le diagnostic présentera cette cause comme distincte d'un refus de validation HA (FR14) — les reason_codes de classe 1 n'appartiennent pas à la classe 2

3. **Given** un cas de test d'échec pour l'étape 2 (mapping ambigu ou absent)
   **When** le test s'exécute en isolation (sans MQTT, sans runtime Jeedom)
   **Then** le test passe et vérifie que le reason_code de classe 1 correct est positionné dans le sous-bloc `mapping`
   **And** les sous-blocs suivants peuvent être explicitement définis avec statut skipped — pas de trou implicite (AR2)

## Tasks / Subtasks

- [x] Task 1 — Créer `resources/daemon/tests/unit/test_step2_mapping_failure.py` (AC: #1, #2, #3)
  - [x] **1.1 — Helpers locaux (identiques à `test_step2_mapping_candidat.py`)**
    - [x] `_make_snapshot()`, `_cmd()`, `_make_eq()` — pas de conftest.py
  - [x] **1.2 — Test AC1 — conflicting generic_types LightMapper** (AC #1, #3)
    - [x] `test_ambiguous_conflicting_light_and_flap_commands`
      - Eq avec `LIGHT_ON` + `FLAP_UP` → `LightMapper().map()` retourne `MappingResult(confidence="ambiguous", reason_code="conflicting_generic_types")`
      - `FLAP_UP` ∈ `_ANTI_LIGHT_GENERIC_TYPES` → déclenche le guardrail conflicting
      - `LightMapper().decide_publication(result)` → `PublicationDecision(should_publish=False, reason="ambiguous_skipped")`
  - [x] **1.3 — Test AC1 — duplicate generic_types même sub_type** (AC #1, #3)
    - [x] `test_ambiguous_duplicate_light_state_same_subtype`
      - Deux `LIGHT_STATE` avec `sub_type="binary"` → même sub_type, pas de préférence applicable → `confidence="ambiguous"`, `reason_code="duplicate_generic_types"`
      - Input : `[_cmd(1, "State1", "LIGHT_STATE", type_="info", sub_type="binary"), _cmd(2, "State2", "LIGHT_STATE", type_="info", sub_type="binary"), _cmd(3, "On", "LIGHT_ON", type_="action", sub_type="other")]`
  - [x] **1.4 — Test AC1 — name heuristic rejection** (AC #1, #3)
    - [x] `test_ambiguous_name_heuristic_light_named_volet`
      - Eq nommé `"Volet salon"` avec `LIGHT_ON + LIGHT_OFF + LIGHT_STATE` → `"volet"` ∈ `_NON_LIGHT_KEYWORDS` → `confidence="ambiguous"`, `reason_code="name_heuristic_rejection"`
  - [x] **1.5 — Test AC1 — color_only_unsupported** (AC #1, #3)
    - [x] `test_ambiguous_color_only_light`
      - Eq nommé `"Ampoule RGB"` avec seulement `LIGHT_SET_COLOR` (`sub_type="color"`) → `confidence="ambiguous"`, `reason_code="color_only_unsupported"`
      - **Precondition assert obligatoire en tête du test** : importer `_NON_LIGHT_KEYWORDS` depuis `mapping.light` et asserter `"ampoule" not in _NON_LIGHT_KEYWORDS` — si cette précondition échoue, le reason_code attendu serait `"name_heuristic_rejection"` et non `"color_only_unsupported"`, ce qui rendrait le test silencieusement faux
      - Forme attendue : `from mapping.light import _NON_LIGHT_KEYWORDS` puis `assert "ampoule" not in _NON_LIGHT_KEYWORDS`
  - [x] **1.6 — Test AC1 — state_orphan (LIGHT_STATE sans action)** (AC #1, #3)
    - [x] `test_ambiguous_state_orphan_light`
      - Eq nommé `"Lampe orpheline"` avec seulement `LIGHT_STATE` (`type_="info"`) → aucune commande action → `confidence="ambiguous"`, `reason_code="state_orphan"`
  - [x] **1.7 — Test AC2 — LightMapper retourne None pour ENERGY_*** (AC #2, #3)
    - [x] `test_no_mapping_light_mapper_returns_none_for_energy_commands`
      - Eq avec `ENERGY_ON + ENERGY_OFF + ENERGY_STATE` → aucune commande `LIGHT_*` → `LightMapper().map()` retourne `None`
  - [x] **1.8 — Test AC2 — CoverMapper retourne None pour LIGHT_*** (AC #2, #3)
    - [x] `test_no_mapping_cover_mapper_returns_none_for_light_commands`
      - Eq avec `LIGHT_ON + LIGHT_OFF + LIGHT_STATE` → LIGHT_* vont dans `anti_cover_cmds`, `flap_cmds` est vide → `CoverMapper().map()` retourne `None`
  - [x] **1.9 — Test AC2 — SwitchMapper retourne None pour FLAP_*** (AC #2, #3)
    - [x] `test_no_mapping_switch_mapper_returns_none_for_flap_commands`
      - Eq avec `FLAP_UP + FLAP_DOWN + FLAP_STATE` → FLAP_* vont dans `anti_switch_cmds`, `energy_cmds` est vide → `SwitchMapper().map()` retourne `None`
  - [x] **1.10 — Test AR2 — sub-blocs explicitement définis après mapping ambigu** (AC #1)
    - [x] `test_ar2_sub_blocs_present_when_mapping_ambiguous`
      - Après `LightMapper().map()` retournant `confidence="ambiguous"` :
        - `result.projection_validity is None` (pas encore câblé par l'orchestrateur)
        - Affecter `result.projection_validity = ProjectionValidity(is_valid=None, reason_code="skipped_no_mapping_candidate", missing_fields=[], missing_capabilities=[])`
        - Affecter `result.publication_decision_ref = PublicationDecision(should_publish=False, reason="no_mapping", mapping_result=result)`
        - Vérifier les deux affectations sans erreur — `result.projection_validity.is_valid is None`, `result.publication_decision_ref.should_publish is False`
        - Commenter : "Simule ce que l'orchestrateur fera en Epic 5 (P1 — trace complète, AR2 — jamais absent)"
        - Note : `reason="no_mapping"` dans `publication_decision_ref` est la convention orchestrateur (Epic 5) — distinct de `"ambiguous_skipped"` produit par `decide_publication()`
  - [x] **1.11 — Test FR14 — reason_codes classe 1 distincts de la classe 2** (AC #2)
    - [x] `test_fr14_class1_reason_codes_not_in_class2`
      - `CLASS_1_REASON_CODES = {"conflicting_generic_types", "duplicate_generic_types", "name_heuristic_rejection", "color_only_unsupported", "state_orphan", "ambiguous_skipped", "probable_skipped", "no_mapping"}`
      - `CLASS_2_REASON_CODES = {"ha_missing_command_topic", "ha_missing_state_topic", "ha_missing_required_option", "ha_component_unknown"}`
      - `assert CLASS_1_REASON_CODES.isdisjoint(CLASS_2_REASON_CODES)` — diagnostic distinguable sans ambiguïté
  - [x] **1.12 — Test NFR9 — cas d'échec CoverMapper et SwitchMapper** (AC #3)
    - [x] `test_nfr9_cover_ambiguous_conflicting_light_and_flap_commands`
      - Eq avec `FLAP_UP` + `LIGHT_ON` → `LIGHT_ON` ∈ `_ANTI_COVER_GENERIC_TYPES`, `FLAP_UP` ∈ `flap_cmds` → `CoverMapper().map()` retourne `MappingResult(confidence="ambiguous", reason_code="conflicting_generic_types")`
    - [x] `test_nfr9_switch_ambiguous_conflicting_energy_and_flap_commands`
      - Eq avec `ENERGY_ON` + `FLAP_UP` → `FLAP_UP` ∈ `_ANTI_SWITCH_GENERIC_TYPES`, `ENERGY_ON` ∈ `energy_cmds` → `SwitchMapper().map()` retourne `MappingResult(confidence="ambiguous", reason_code="conflicting_generic_types")`

- [x] Task 2 — Vérifier la non-régression (AC: #3)
  - [x] `pytest resources/daemon/tests/` depuis `resources/daemon/` : 325 + N PASS (N = nouveaux tests de cette story)
  - [x] Confirmer 0 failure, 0 error

## Dev Notes

### Contexte de la story dans le pipeline

Story 2.1 a formalisé le cas nominal de l'étape 2 (equip. avec generic_types non ambigus → MappingResult `sure`/`probable`). Story 2.2 est la moitié NFR9 manquante : le **cas d'échec** de l'étape 2. Ensemble, elles satisfont NFR9 pour l'étape 2 : "au moins un cas nominal et un cas d'échec exécutables en isolation".

Comme Story 2.1, **cette story n'ajoute pas de code de production** — elle formalise les tests de contrat sur la logique d'échec déjà implémentée dans les mappers existants depuis le cycle V1.1.

### Aucune modification de code de production requise

Fichiers non modifiés :
- `mapping/light.py`, `mapping/cover.py`, `mapping/switch.py` — logique ambiguous déjà implémentée et correcte
- `models/mapping.py` — `MappingResult`, `ProjectionValidity`, `PublicationDecision` déjà corrects depuis Story 1.1
- `models/cause_mapping.py` — figé depuis Story 1.3

### Convention terminologique — quatre niveaux distincts à ne pas confondre

Ces quatre niveaux coexistent dans cette story. Ils désignent des choses différentes à des couches différentes :

| Niveau | Expression dans le code | Signification | Couche |
|---|---|---|---|
| **1 — no_mapping** | `mapper.map() → None` | Aucune commande du domaine trouvée — le mapper ne produit rien | Mapper étape 2 |
| **2 — mapping ambigu** | `mapper.map() → MappingResult(confidence="ambiguous")` | Commandes trouvées mais contradictoires ou insuffisantes | Mapper étape 2 |
| **3 — raison interne mapper** | `mapper.decide_publication(result) → reason="ambiguous_skipped"` | Décision de publication bloquée par politique de confiance | Mapper (couche décision V1.1) |
| **4 — convention orchestrateur** | `PublicationDecision(reason="no_mapping")` dans le test AR2 | Simulation de ce que l'orchestrateur Epic 5 écrira dans `publication_decision_ref` quand l'étape 2 n'a pas produit de candidat publiable pour poursuivre le pipeline (couvre les deux formes d'échec : `None` et `confidence="ambiguous"`) | Test AR2 (Epic 5 simulé) |

Les niveaux 1 et 2 sont deux formes d'échec de l'étape 2. Le niveau 3 est une raison interne au mapper V1.1. Le niveau 4 est une convention d'orchestration aval — elle n'est pas produite par le mapper, elle est affectée **explicitement** dans le test pour démontrer la compatibilité AR2. Elle ne présuppose pas que `mapper.map()` a retourné `None` : elle signale que l'étape 2 n'a pas fourni de sortie exploitable en aval, quelle qu'en soit la forme.

Ne jamais confondre niveau 3 (`"ambiguous_skipped"`) et niveau 4 (`"no_mapping"`) : ils sont distincts par couche et par sémantique.

### Taxonomie complète des cas d'échec à couvrir

**Cas ambiguous — mapper retourne `MappingResult(confidence="ambiguous")` :**

| `reason_code` | Mapper(s) | Trigger |
|---|---|---|
| `conflicting_generic_types` | Light, Cover, Switch | Commands de domaines différents (ex. LIGHT_ON + FLAP_UP) |
| `duplicate_generic_types` | Light, Cover | Deux commandes de même generic_type, même sub_type (non résolvable) |
| `name_heuristic_rejection` | Light, Cover, Switch | Nom contient un mot-clé anti-domaine (_NON_LIGHT/COVER/SWITCH_KEYWORDS) |
| `color_only_unsupported` | Light uniquement | Seulement LIGHT_SET_COLOR/LIGHT_COLOR/LIGHT_COLOR_TEMP (V1 unsupported) |
| `state_orphan` | Light, Cover, Switch | STATE orphan sans commande action |

**Cas no_mapping — mapper retourne `None` :**

| Inputs | Mapper | Raison |
|---|---|---|
| `ENERGY_ON + ENERGY_OFF + ENERGY_STATE` | LightMapper | Aucune commande LIGHT_* |
| `LIGHT_ON + LIGHT_OFF + LIGHT_STATE` | CoverMapper | flap_cmds vide (LIGHT_* → anti_cover_cmds, jamais flap_cmds) |
| `FLAP_UP + FLAP_DOWN + FLAP_STATE` | SwitchMapper | energy_cmds vide (FLAP_* → anti_switch_cmds, jamais energy_cmds) |

### Distinction classe 1 vs classe 2 (FR14 — contrat de distinguabilité)

La classe 1 est produite par l'**interprétation des données Jeedom** (étape 2). La classe 2 est produite par la **vérification des contraintes HA** (étape 3 — Epic 3, non encore implémentée).

```python
# Classe 1 — reason_codes mapping (étape 2, ce cycle) :
{"conflicting_generic_types", "duplicate_generic_types", "name_heuristic_rejection",
 "color_only_unsupported", "state_orphan",
 "ambiguous_skipped", "probable_skipped", "no_mapping"}

# Classe 2 — reason_codes validation HA (étape 3, Epic 3 à venir) :
{"ha_missing_command_topic", "ha_missing_state_topic",
 "ha_missing_required_option", "ha_component_unknown"}

# Contrat FR14 : ces deux ensembles sont disjoints → diagnostic distinguable
```

### Signatures et comportement des mappers en cas d'échec

```python
# decide_publication() pour confidence="ambiguous" (tous les mappers) :
decision = LightMapper().decide_publication(ambiguous_result)
# → PublicationDecision(should_publish=False, reason="ambiguous_skipped", mapping_result=ambiguous_result)

# PUBLICATION_POLICY (light/cover/switch identiques) :
# "ambiguous": False → should_publish=False, reason="ambiguous_skipped"
```

### Inputs exacts pour les cas d'échec

```python
# Test 1.2 — LightMapper conflicting (LIGHT_ON + FLAP_UP)
# FLAP_UP ∈ _ANTI_LIGHT_GENERIC_TYPES → guardrail conflicting actif
cmds = [
    _cmd(1, "On", "LIGHT_ON", type_="action", sub_type="other"),
    _cmd(2, "Up", "FLAP_UP",  type_="action", sub_type="other"),
]
eq = _make_eq(10, "Lampe conflit", cmds)
result = LightMapper().map(eq, _make_snapshot())
assert result.confidence == "ambiguous"
assert result.reason_code == "conflicting_generic_types"

# Test 1.3 — duplicate LIGHT_STATE même sub_type (non résolvable)
# Deux sub_type="binary" → _LIGHT_DEDUP_PREFERENCE ne peut pas résoudre → ambiguous
cmds = [
    _cmd(1, "State1", "LIGHT_STATE", type_="info", sub_type="binary"),
    _cmd(2, "State2", "LIGHT_STATE", type_="info", sub_type="binary"),
    _cmd(3, "On",     "LIGHT_ON",    type_="action", sub_type="other"),
]

# Test 1.4 — name heuristic rejection
# "volet" ∈ _NON_LIGHT_KEYWORDS → pattern \bvolet\b match sur "Volet salon"
eq = _make_eq(10, "Volet salon", [
    _cmd(1, "On",    "LIGHT_ON",    type_="action", sub_type="other"),
    _cmd(2, "Off",   "LIGHT_OFF",   type_="action", sub_type="other"),
    _cmd(3, "State", "LIGHT_STATE", type_="info",   sub_type="binary"),
])

# Test 1.5 — color_only_unsupported
# Seulement LIGHT_SET_COLOR ∈ _COLOR_GENERIC_TYPES
# PRECONDITION : "ampoule" doit être absent de _NON_LIGHT_KEYWORDS
# Si ce n'est plus le cas, le mapper retournera "name_heuristic_rejection" au lieu de "color_only_unsupported"
from mapping.light import _NON_LIGHT_KEYWORDS as _NLK
assert "ampoule" not in _NLK  # précondition du test — échoue si la liste évolue
cmds = [_cmd(1, "Couleur", "LIGHT_SET_COLOR", type_="action", sub_type="color")]
eq = _make_eq(10, "Ampoule RGB", cmds)

# Test 1.6 — state_orphan (LIGHT_STATE sans aucune action)
cmds = [_cmd(1, "State", "LIGHT_STATE", type_="info", sub_type="binary")]
eq = _make_eq(10, "Lampe orpheline", cmds)

# Tests 1.7/1.8/1.9 — no_mapping (None retourné)
# LightMapper + ENERGY_* → not light_cmds → return None
# CoverMapper + LIGHT_* → LIGHT_* vont dans anti_cover_cmds, flap_cmds vide → return None
# SwitchMapper + FLAP_* → FLAP_* vont dans anti_switch_cmds, energy_cmds vide → return None

# Test 1.12 — CoverMapper conflicting
# FLAP_UP ∈ _FLAP_GENERIC_TYPES → flap_cmds non vide
# LIGHT_ON ∈ _ANTI_COVER_GENERIC_TYPES → anti_cover_cmds non vide → conflicting
cmds = [
    _cmd(1, "Up",  "FLAP_UP",   type_="action", sub_type="other"),
    _cmd(2, "On",  "LIGHT_ON",  type_="action", sub_type="other"),
]

# Test 1.12 — SwitchMapper conflicting
# ENERGY_ON ∈ _SWITCH_GENERIC_TYPES → energy_cmds non vide
# FLAP_UP ∈ _ANTI_SWITCH_GENERIC_TYPES → anti_switch_cmds non vide → conflicting
cmds = [
    _cmd(1, "On", "ENERGY_ON", type_="action", sub_type="other"),
    _cmd(2, "Up", "FLAP_UP",   type_="action", sub_type="other"),
]
```

### Rôle du test AR2 (Task 1.10) — trace complète sans trou

```python
# Après mapping ambigu, le MappingResult est structurellement compatible AR2.
# L'orchestrateur (Epic 5) peut y affecter les sous-blocs sans erreur.
result = LightMapper().map(eq_conflicting, _make_snapshot())
# result.confidence == "ambiguous" ; result.projection_validity is None (pas encore câblé)

# Simule ce que l'orchestrateur fera en Epic 5 (P1 — trace complète, AR2 — jamais absent)
result.projection_validity = ProjectionValidity(
    is_valid=None,
    reason_code="skipped_no_mapping_candidate",  # étape 3 skippée — étape 2 a échoué
    missing_fields=[],
    missing_capabilities=[],
)
result.publication_decision_ref = PublicationDecision(
    should_publish=False,
    reason="no_mapping",  # convention orchestrateur — distinct de "ambiguous_skipped"
    mapping_result=result,
)
assert result.projection_validity.is_valid is None
assert result.projection_validity.reason_code == "skipped_no_mapping_candidate"
assert result.publication_decision_ref.should_publish is False
assert result.publication_decision_ref.reason == "no_mapping"
```

Note : `reason="no_mapping"` dans `publication_decision_ref` est la **convention orchestrateur Epic 5** pour signaler "pas de candidat de mapping à décider". C'est distinct de `reason="ambiguous_skipped"` retourné par `mapper.decide_publication()`, qui est la raison interne de la couche mapper.

### Pattern d'imports du fichier de test

```python
"""Tests de l'étape 2 — Cas d'échec et ambiguïté de mapping — Story 2.2.

Vérifie que les mappers signalent explicitement les mappings impossibles (None)
et ambigus (confidence="ambiguous"), et que les sous-blocs suivants peuvent
être définis avec statut skipped (AR2 — trace complète sans trou implicite).

Tests en isolation totale : aucune dépendance MQTT, daemon, pytest-asyncio.
"""
from models.mapping import (
    MappingResult,
    ProjectionValidity,
    PublicationDecision,
)
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from mapping.light import LightMapper
from mapping.cover import CoverMapper
from mapping.switch import SwitchMapper
```

### Dev Agent Guardrails

- **NE PAS modifier** `mapping/light.py`, `cover.py`, `switch.py` — la logique d'échec est déjà implémentée correctement
- **NE PAS modifier** `models/mapping.py` — structure correcte depuis Story 1.1
- **NE PAS modifier** `models/cause_mapping.py` — figé depuis Story 1.3. Les reason_codes de classe 2 (Epic 3) sont hors scope
- **Pas de conftest.py** — helpers locaux au fichier test uniquement
- **Pas de dépendances MQTT, pytest-asyncio, daemon** — tests en isolation totale (NFR9)
- **Portée stricte** : 1 seul fichier créé (`test_step2_mapping_failure.py`). Aucun fichier de production modifié
- Avant de coder le test 1.5 (`color_only_unsupported`), tracer le chemin dans `light.py` depuis la collecte des LIGHT_* commands jusqu'à l'émission du reason_code pour s'assurer que l'input `LIGHT_SET_COLOR` seul déclenche bien ce cas
- **`reason="no_mapping"`** dans Task 1.10 est la convention orchestrateur (Epic 5) — ne pas confondre avec `"ambiguous_skipped"` retourné par `decide_publication()`

### Project Structure Notes

**Fichier créé :**
- `resources/daemon/tests/unit/test_step2_mapping_failure.py`

**Aucun fichier de production modifié.**

**Continuité de structure avec Story 2.1 :**
```
resources/daemon/tests/unit/
├── test_step2_mapping_candidat.py   ← Story 2.1 — cas nominaux (sure/probable)
└── test_step2_mapping_failure.py    ← Story 2.2 — cas d'échec (ambiguous/None) — À créer
```

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 2.2] — User story, AC, dev notes canoniques
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §FR13, FR14] — Signalement explicite de l'échec, distinguabilité classe 1 / classe 2
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §AR2] — Sous-blocs jamais absents même en cas d'échec amont
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §NFR9] — 1 cas nominal + 1 cas d'échec par étape (Story 2.1 = nominal, Story 2.2 = échec)
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §D1] — Sous-blocs bornés : mapping écrit par étape 2, projection_validity par étape 3
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §Classe 1, Classe 2] — Définition et frontière des 4 classes d'échec canoniques
- [Source: `resources/daemon/mapping/light.py`] — `LightMapper.map()`, `decide_publication()`, `_ANTI_LIGHT_GENERIC_TYPES`, `_NON_LIGHT_KEYWORDS`, `_COLOR_GENERIC_TYPES`, logique state_orphan
- [Source: `resources/daemon/mapping/cover.py`] — `CoverMapper.map()`, `_ANTI_COVER_GENERIC_TYPES`, `_FLAP_GENERIC_TYPES` — LIGHT_ON ∈ anti-cover ✓
- [Source: `resources/daemon/mapping/switch.py`] — `SwitchMapper.map()`, `_ANTI_SWITCH_GENERIC_TYPES`, `_SWITCH_GENERIC_TYPES` — FLAP_UP ∈ anti-switch ✓
- [Source: `resources/daemon/models/mapping.py`] — `MappingResult`, `ProjectionValidity`, `PublicationDecision` — structure et champs
- [Source: `resources/daemon/tests/unit/test_step2_mapping_candidat.py`] — Pattern helpers locaux, imports, structure identique à réutiliser

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story-only tests — 0 fichier de production modifié, 0 changement comportemental.
- 12 tests créés dans `test_step2_mapping_failure.py` : 5 cas ambiguous LightMapper (conflicting, duplicate, name_heuristic, color_only, state_orphan), 3 cas None (LightMapper/CoverMapper/SwitchMapper), test AR2 compatibilité sous-blocs, test FR14 disjonction classe 1/2, 2 cas NFR9 (Cover + Switch conflicting).
- Résultats : 12/12 PASS nouveaux, 337/337 PASS non-régression (baseline 325 + 12 nouveaux).
- Précondition "ampoule ∉ _NON_LIGHT_KEYWORDS" incluse dans test 1.5 pour sécuriser le reason_code attendu.

### File List

- `resources/daemon/tests/unit/test_step2_mapping_failure.py` — créé
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — mis à jour (story 2.2 → done, code review PASS)

## Change Log

- 2026-04-11 — Création de `test_step2_mapping_failure.py` : 12 tests cas d'échec étape 2 (ambiguous + None). 337/337 non-régression PASS.
