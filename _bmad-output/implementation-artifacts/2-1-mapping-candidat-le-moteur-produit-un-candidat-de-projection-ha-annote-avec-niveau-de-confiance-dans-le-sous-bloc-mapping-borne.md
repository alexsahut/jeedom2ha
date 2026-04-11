# Story 2.1 : Mapping candidat — le moteur produit un candidat de projection HA annoté avec niveau de confiance dans le sous-bloc mapping borné

Status: done

## Story

En tant qu'utilisateur,
je veux que le système produise, pour chaque équipement éligible, un candidat de projection nommant le type d'entité HA cible et exprimant un niveau de confiance,
afin que chaque équipement qui atteint le pipeline reçoive une intention de mapping structurée et traçable — et non une simple heuristique opaque.

## Acceptance Criteria

1. **Given** un équipement éligible avec des generic_types non ambigus
   **When** le pipeline applique l'étape de mapping
   **Then** le sous-bloc `mapping` est rempli avec `ha_entity_type`, `confidence` (sure ou probable) et un `reason_code`
   **And** les sous-blocs `projection_validity` et `publication_decision` sont présents en tant que champs structurels dans le `MappingResult`, leur valeur après l'étape 2 étant `None` (pas encore exécutés) — ce que le test peut rendre explicite en y affectant un `ProjectionValidity(is_valid=None, ...)` pour démontrer la compatibilité AR2

2. **Given** le module de mapping (`mapping/light.py`, `cover.py`, `switch.py`)
   **When** le développeur modifie une règle de mapping
   **Then** la modification est circonscrite au module mapping — aucune modification requise dans les modules éligibilité (`models/topology.py`), validation (Epic 3) ou publication (Epic 5) (FR15 — séparation structurelle)
   **And** le mapper n'écrit pas dans `projection_validity` ni `publication_decision_ref` (P2 — isolation des sous-blocs)

3. **Given** un cas de test nominal pour l'étape 2
   **When** le test s'exécute en isolation (sans MQTT, sans runtime Jeedom, sans daemon)
   **Then** le test passe et produit un `MappingResult` valide avec niveau de confiance `sure` ou `probable`
   **And** le corpus de non-régression complet passe sans modification (NFR8)

## Tasks / Subtasks

- [x] Task 1 — Créer `resources/daemon/tests/unit/test_step2_mapping_candidat.py` (AC: #1, #2, #3)
  - [x] **1.1 — Helpers locaux (pas de conftest.py)**
    - [x] `_make_snapshot()` → `TopologySnapshot(timestamp="2026-04-11T00:00:00", objects={}, eq_logics={})`
    - [x] `_cmd(id, name, generic_type, type_="action", sub_type="other")` → `JeedomCmd`
    - [x] `_make_eq(id, name, cmds)` → `JeedomEqLogic` minimal (is_enable=True, is_excluded=False)

  - [x] **1.2 — Test nominal LightMapper sure** (AC #1, #3)
    - [x] `test_light_mapper_nominal_sure_on_off_state` : `LIGHT_ON + LIGHT_OFF + LIGHT_STATE`
      → `ha_entity_type="light"`, `confidence="sure"`, `reason_code="light_on_off_only"`, `isinstance(result.capabilities, LightCapabilities)`
      → `result.capabilities.has_on_off is True`

  - [x] **1.3 — Test nominal LightMapper probable** (AC #1, #3)
    - [x] `test_light_mapper_nominal_probable_state_on_only` : `LIGHT_STATE + LIGHT_ON` (pas de LIGHT_OFF)
      → `confidence="probable"`, `reason_code="light_on_off_only"`

  - [x] **1.4 — Test nominal CoverMapper sure** (AC #1, #3)
    - [x] `test_cover_mapper_nominal_sure_up_down_state` : `FLAP_UP + FLAP_DOWN + FLAP_STATE`
      → `ha_entity_type="cover"`, `confidence="sure"`, `reason_code="cover_open_close"`, `isinstance(result.capabilities, CoverCapabilities)`
      → `result.capabilities.has_open_close is True`

  - [x] **1.5 — Test nominal SwitchMapper sure** (AC #1, #3)
    - [x] `test_switch_mapper_nominal_sure_on_off_state` : `ENERGY_ON + ENERGY_OFF + ENERGY_STATE`
      → `ha_entity_type="switch"`, `confidence="sure"`, `reason_code="switch_on_off_state"`, `isinstance(result.capabilities, SwitchCapabilities)`
      → `result.capabilities.has_on_off is True`, `result.capabilities.has_state is True`

  - [x] **1.6 — Test FR12 — champs requis du sous-bloc mapping** (AC #1)
    - [x] `test_fr12_mapping_sub_bloc_has_required_fields` : pour chaque résultat de mapper nominal, vérifier que `ha_entity_type`, `confidence`, `reason_code`, `capabilities` sont tous non-None et que `confidence in ("sure", "probable")`

  - [x] **1.7 — Test P2 isolation — projection_validity non touché** (AC #2)
    - [x] `test_p2_isolation_projection_validity_is_none_after_mapping` : après `LightMapper().map(eq, snapshot)`, `result.projection_validity is None`
    - [x] Commenter explicitement : "étape 3 n'est pas câblée — None = non évalué (pré-Epic 3)"

  - [x] **1.8 — Test P2 isolation — publication_decision_ref non touché** (AC #2)
    - [x] `test_p2_isolation_publication_decision_ref_is_none_after_mapping` : `result.publication_decision_ref is None`
    - [x] Commenter : "étape 4 non câblée — None = non évalué (pré-Epic 5)"

  - [x] **1.9 — Test AR2 compatibilité — skipped state assignable** (AC #1)
    - [x] `test_ar2_skipped_projection_validity_can_be_set_after_mapping` :
      ```python
      result = LightMapper().map(eq, snapshot)
      # Simule ce que l'orchestrateur fera en Epic 5 (P1 — trace complète)
      result.projection_validity = ProjectionValidity(
          is_valid=None,
          reason_code="skipped_no_mapping_candidate",
          missing_fields=[],
          missing_capabilities=[],
      )
      assert result.projection_validity.is_valid is None
      assert result.projection_validity.reason_code == "skipped_no_mapping_candidate"
      assert result.publication_decision_ref is None  # étape 4 non câblée
      ```

  - [x] **1.10 — Test FR15 — indépendance structurelle des mappers** (AC #2)
    - [x] `test_fr15_light_cover_switch_mappers_are_independent_modules` :
      - `from mapping.light import LightMapper` ne requiert pas d'importer `CoverMapper` ou `SwitchMapper`
      - `from mapping.cover import CoverMapper` ne requiert pas d'importer `LightMapper` ou `SwitchMapper`
      - `from mapping.switch import SwitchMapper` ne requiert pas d'importer `LightMapper` ou `CoverMapper`
      - Chaque mapper importe uniquement depuis `models.topology` et `models.mapping` (pas de dépendances croisées entre mappers)

- [x] Task 2 — Vérifier la non-régression (AC: #3)
  - [x] `pytest resources/daemon/tests/` depuis `resources/daemon/` : N + 316 PASS (N = nouveaux tests)
  - [x] Confirmer 0 failure, 0 error

## Dev Notes

### Contexte de la story dans le pipeline

Epic 1 a posé le contrat structurel du pipeline (Story 1.1 : MappingResult à sous-blocs bornés ; Stories 1.2-1.3 : éligibilité + diagnostic étape 1). Story 2.1 formalise l'**étape 2 — Mapping candidat** en tant que première étape substantielle du pipeline post-éligibilité.

Les mappers (`LightMapper`, `CoverMapper`, `SwitchMapper`) sont **déjà implémentés et corrects** depuis le cycle V1.1 (Stories 2.2, 2.3, 2.4 du cycle précédent). Story 2.1 **n'ajoute pas de code de production** — elle ajoute les tests de contrat qui formalisent cette étape dans la nomenclature du cycle Moteur de Projection Explicable.

### Aucune modification de code de production requise

Les fichiers de production suivants ne sont **pas modifiés** dans cette story :
- `mapping/light.py`, `mapping/cover.py`, `mapping/switch.py` — non ciblés par ce delta (architecture-projection-engine.md §Fichiers non ciblés)
- `models/mapping.py` — déjà correct depuis Story 1.1 (sous-blocs `projection_validity`, `publication_decision_ref`, `pipeline_step_reached` présents)
- `models/cause_mapping.py` — déjà à 15 entrées actives depuis Story 1.3

### Rôle de chaque mapper dans l'étape 2

| Mapper | Classe `MappingCapabilities` | Generic_types détectés | reason_code nominal sure |
|---|---|---|---|
| `LightMapper` | `LightCapabilities` | `LIGHT_*` | `"light_on_off_only"` (ON+OFF+STATE) |
| `CoverMapper` | `CoverCapabilities` | `FLAP_*` | `"cover_open_close"` (UP+DOWN+STATE) |
| `SwitchMapper` | `SwitchCapabilities` | `ENERGY_*` | `"switch_on_off_state"` (ON+OFF+STATE) |

Chaque mapper retourne `None` si l'équipement ne contient aucune commande du domaine concerné — ce n'est pas un échec, c'est l'absence de signal. L'échec de mapping (ambiguïté, orphelin) est couvert par Story 2.2.

### Signatures exactes des mappers

```python
# Toutes les mêmes :
def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:

# Pour les tests, TopologySnapshot minimal suffit :
snapshot = TopologySnapshot(timestamp="2026-04-11T00:00:00", objects={}, eq_logics={})
# get_suggested_area() retourne None si eq.object_id absent du snapshot → acceptable
```

### Construction du MappingResult attendu

```python
# LightMapper nominal sure — inputs :
cmds = [
    JeedomCmd(id=1, name="On",    generic_type="LIGHT_ON",    type="action", sub_type="other"),
    JeedomCmd(id=2, name="Off",   generic_type="LIGHT_OFF",   type="action", sub_type="other"),
    JeedomCmd(id=3, name="State", generic_type="LIGHT_STATE", type="info",   sub_type="binary"),
]
eq = JeedomEqLogic(id=10, name="Lampe salon", cmds=cmds)
result = LightMapper().map(eq, _make_snapshot())
# Attendu :
assert result.ha_entity_type == "light"
assert result.confidence == "sure"
assert result.reason_code == "light_on_off_only"
assert isinstance(result.capabilities, LightCapabilities)
assert result.capabilities.has_on_off is True
assert result.capabilities.has_brightness is False

# CoverMapper nominal sure — inputs :
cmds = [
    JeedomCmd(id=4, name="Up",    generic_type="FLAP_UP",    type="action", sub_type="other"),
    JeedomCmd(id=5, name="Down",  generic_type="FLAP_DOWN",  type="action", sub_type="other"),
    JeedomCmd(id=6, name="State", generic_type="FLAP_STATE", type="info",   sub_type="numeric"),
]
# result.confidence == "sure", result.reason_code == "cover_open_close"

# SwitchMapper nominal sure — inputs :
cmds = [
    JeedomCmd(id=7, name="On",    generic_type="ENERGY_ON",    type="action", sub_type="other"),
    JeedomCmd(id=8, name="Off",   generic_type="ENERGY_OFF",   type="action", sub_type="other"),
    JeedomCmd(id=9, name="State", generic_type="ENERGY_STATE", type="info",   sub_type="binary"),
]
# result.confidence == "sure", result.reason_code == "switch_on_off_state"
```

### Pattern de test P2 + AR2

```python
"""Tests de l'étape 2 — Mapping candidat — Story 2.1.

Vérifie que les mappers produisent un MappingResult avec le sous-bloc mapping
correctement rempli, et que le sous-bloc projection_validity n'est pas touché
par le mapper (P2 — isolation). Démontre la compatibilité AR2 (skipped state
peut être affecté explicitement pour préparer la trace complète du pipeline).
Tests en isolation totale : aucune dépendance MQTT, daemon, pytest-asyncio.
"""
from models.mapping import (
    LightCapabilities, CoverCapabilities, SwitchCapabilities,
    MappingResult, ProjectionValidity,
)
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from mapping.light import LightMapper
from mapping.cover import CoverMapper
from mapping.switch import SwitchMapper


def _make_snapshot() -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-04-11T00:00:00", objects={}, eq_logics={})


def _cmd(id: int, name: str, generic_type: str, type_: str = "action", sub_type: str = "other") -> JeedomCmd:
    return JeedomCmd(id=id, name=name, generic_type=generic_type, type=type_, sub_type=sub_type)


def _make_eq(id: int, name: str, cmds: list) -> JeedomEqLogic:
    return JeedomEqLogic(id=id, name=name, cmds=cmds)
```

### Règle AR2 — rôle du test 1.9

Le test 1.9 démontre que le `MappingResult` retourné par le mapper est **structurellement compatible** avec la convention AR2 : un appelant (l'orchestrateur en Epic 5) peut y affecter explicitement un `ProjectionValidity(is_valid=None, ...)` sans erreur. Cela prouve que le contrat de transport est prêt pour la traversée complète du pipeline, sans que le mapper lui-même ne viole P2.

La valeur `None` post-étape-2 signifie "étape 3 non encore exécutée" — c'est le statut attendu et correct pour cette story. Le `is_valid=None` affecté dans le test est le statut "skipped" qui sera produit par l'orchestrateur quand mapping échoue (Story 2.2) ou par `validate_projection()` quand mapping réussit (Epic 3).

### Dev Agent Guardrails

- **NE PAS modifier `mapping/light.py`, `cover.py`, `switch.py`** — ces fichiers sont corrects et non ciblés.
- **NE PAS modifier `models/mapping.py`** — `MappingResult`, `ProjectionValidity`, `LightCapabilities`, `CoverCapabilities`, `SwitchCapabilities` sont corrects depuis Story 1.1.
- **NE PAS modifier `models/cause_mapping.py`** — figé (15 entrées actives depuis Story 1.3). Les nouveaux reason_codes de classe 1 (Story 2.2) iront dans une story dédiée.
- **Pas de conftest.py** — helpers locaux au fichier test uniquement.
- **Pas de dépendances MQTT, pytest-asyncio, daemon** — tests en isolation totale (NFR9).
- **Portée stricte** : 1 seul fichier créé (`test_step2_mapping_candidat.py`). Aucun fichier de production modifié.
- **Reason_codes de la classe 1** (pour référence, non modifiés) : `no_mapping`, `ambiguous_skipped`, `probable_skipped`, `duplicate_generic_types`, `conflicting_generic_types`, `name_heuristic_rejection`, `color_only_unsupported`, `state_orphan` — tous dans les mappers existants.

### Project Structure Notes

**Fichier créé :**
- `resources/daemon/tests/unit/test_step2_mapping_candidat.py`

**Aucun fichier de production modifié.**

**Structure de dépendance respectée :**
```
mapping/light.py        →   models/mapping.py
mapping/cover.py        →   models/topology.py
mapping/switch.py       →   models/availability.py
test_step2_*.py         →   mapping/*, models/*
```

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 2.1] — User story, AC, dev notes canoniques
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §FR11-FR15] — Feature 2 — Mapping candidat découplé
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §AR1, AR2] — Sous-blocs bornés, trace complète sans trou
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §NFR9] — 1 cas nominal + 1 cas échec par étape (Story 2.2 couvre le cas échec)
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §P2] — Isolation des sous-blocs — mapping écrit uniquement dans son sous-bloc
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §P1] — Traversée complète du pipeline, skipped = `is_valid: None` + `reason_code`
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §Mapping pipeline → code] — étape 2 : `mapping/light.py`, `cover.py`, `switch.py`
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §Fichiers non ciblés] — les mappers ne sont pas modifiés dans ce cycle
- [Source: `resources/daemon/mapping/light.py`] — `LightMapper.map()`, reason_codes classe 1, confidence logic
- [Source: `resources/daemon/mapping/cover.py`] — `CoverMapper.map()`, FLAP_* commands
- [Source: `resources/daemon/mapping/switch.py`] — `SwitchMapper.map()`, ENERGY_* commands, reason_code=`switch_on_off_state` pour sure
- [Source: `resources/daemon/models/mapping.py`] — `MappingResult`, `ProjectionValidity`, `MappingCapabilities`
- [Source: `resources/daemon/models/topology.py`] — `JeedomEqLogic`, `JeedomCmd`, `TopologySnapshot.get_suggested_area()`
- [Source: `resources/daemon/tests/unit/test_pipeline_contract.py`] — pattern de test Story 1.1, helpers `_make_mapping_result()`
- [Source: `resources/daemon/tests/unit/test_step1_eligibility.py`] — pattern de test étape 1 : helpers locaux, imports, structure

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Créé `resources/daemon/tests/unit/test_step2_mapping_candidat.py` : 9 tests, 0 fichier de production modifié.
- Tests nominaux : LightMapper sure (1.2), LightMapper probable (1.3), CoverMapper sure (1.4), SwitchMapper sure (1.5) — tous PASS.
- FR12 vérifié : sous-bloc mapping toujours rempli (ha_entity_type/confidence/reason_code/capabilities non-None).
- P2 isolation confirmée : projection_validity=None et publication_decision_ref=None après mapping (étapes 3 et 4 non câblées).
- AR2 compatibilité démontrée : affectation explicite de ProjectionValidity(is_valid=None) sans erreur.
- FR15 indépendance vérifiée par inspection des espaces de noms des modules mappers.
- Non-régression : 325/325 PASS (316 précédents + 9 nouveaux), 0 failure, 0 error.

### File List

- `resources/daemon/tests/unit/test_step2_mapping_candidat.py` — créé (9 tests étape 2)
