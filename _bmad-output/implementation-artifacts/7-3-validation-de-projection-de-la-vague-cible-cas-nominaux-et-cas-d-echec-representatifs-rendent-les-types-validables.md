# Story 7.3 : Validation de projection de la vague cible — cas nominaux et cas d'échec représentatifs rendent les types `validables`

Status: done

## Story

En tant que mainteneur de jeedom2ha,
je veux prouver que les types de la vague cible (`sensor`, `binary_sensor`) sont structurellement validables par `validate_projection()` via une suite de tests dédiée,
afin de satisfaire la condition 2 de FR40 et de faire passer officiellement ces types de l'état `connu` à l'état `validable` selon AR6.

## Contexte

### Positionnement dans la séquence pe-epic-7

| Story | Transition d'état | Moyen |
|-------|------------------|-------|
| 7.2 (done) | ∅ → `connu` | `HA_COMPONENT_REGISTRY` + `SensorCapabilities` |
| **7.3 (cette story)** | `connu` → `validable` | tests unitaires `validate_projection()` |
| 7.4 (backlog) | `validable` → `ouvert` | `PRODUCT_SCOPE` + contrat FR40 |

La story 7.3 est **100 % test-driven**. Aucun code applicatif n'est modifié sauf bug réel avéré.

### Socle validé par 7.2

- `HA_COMPONENT_REGISTRY` : entrées `sensor` et `binary_sensor` conformes à l'architecture D3
  - `required_fields = ["state_topic", "platform", "availability"]`
  - `required_capabilities = ["has_state"]`
- `SensorCapabilities(has_state: bool = False)` dans `models/mapping.py` — inclus dans `MappingCapabilities`
- `_resolve_capability("has_state", SensorCapabilities(...))` utilise le chemin `isinstance`
- `PRODUCT_SCOPE == ["light", "cover", "switch"]` inchangé
- Corpus 7.2 : **1150 passed** (baseline de non-régression)

### Contrat `validate_projection()` — à lire impérativement avant d'écrire les tests

La fonction est dans `validation/ha_component_registry.py`, ligne 124.

```python
def validate_projection(ha_entity_type: str, capabilities: object) -> ProjectionValidity:
    """Retourne toujours un ProjectionValidity complet (is_valid jamais None).
    None reste un statut d'orchestration injecté par l'orchestrateur quand
    l'étape 3 n'est pas exécutée (upstream a échoué).
    """
```

**is_valid pour composant inconnu = `False`, jamais `None`** :
```python
if ha_entity_type not in HA_COMPONENT_REGISTRY:
    return ProjectionValidity(
        is_valid=False,
        reason_code="ha_component_unknown",
        missing_fields=[],
        missing_capabilities=[],
    )
```

Le test existant `test_validate_projection_unknown_component_is_invalid` (dans `test_step3_validate_projection.py`, ligne 164) confirme : `assert result.is_valid is False`.

`None` n'est jamais retourné par `validate_projection()` — c'est le marqueur injecté par l'orchestrateur quand l'étape 3 est skippée. **Ne pas écrire de test qui attend `is_valid is None` pour un composant inconnu.**

## Acceptance Criteria

### AC1 — Cas nominaux validables

**Given** `validate_projection("sensor", SensorCapabilities(has_state=True))`
**When** la fonction est appelée
**Then** `is_valid is True`
**And** `reason_code is None`
**And** `missing_capabilities == []`
**And** `missing_fields == []`

**Given** `validate_projection("binary_sensor", SensorCapabilities(has_state=True))`
**When** la fonction est appelée
**Then** `is_valid is True`
**And** `reason_code is None`
**And** `missing_capabilities == []`
**And** `missing_fields == []`

### AC2 — Cas d'échec capability (has_state=False)

**Given** `validate_projection("sensor", SensorCapabilities(has_state=False))`
**When** la fonction est appelée
**Then** `is_valid is False`
**And** `reason_code == "ha_missing_state_topic"`
**And** `missing_capabilities == ["has_state"]`
**And** `missing_fields == ["state_topic"]`

Idem pour `"binary_sensor"` avec `SensorCapabilities(has_state=False)`.

### AC3 — Cas composant inconnu

**Given** `validate_projection("unknown_component", SensorCapabilities(has_state=True))`
**When** la fonction est appelée
**Then** `is_valid is False` (**pas `None`** — cf. contrat `validate_projection()` ci-dessus)
**And** `reason_code == "ha_component_unknown"`
**And** `missing_capabilities == []`
**And** `missing_fields == []`

### AC4 — Complétude ProjectionValidity

**Given** tout résultat de `validate_projection()`
**When** ses champs sont inspectés
**Then** les 4 champs sont présents : `is_valid`, `reason_code`, `missing_fields`, `missing_capabilities`
**And** sur un cas valide : `reason_code is None`, les deux listes vides
**And** sur un cas invalide : `reason_code` non nul, au moins une liste non vide
**And** aucun champ n'est absent ou indéterminé dans les cas couverts

### AC5 — Non-régression light/cover/switch

**Given** les tests nominaux et d'échec pour `light`, `cover`, `switch` dans le nouveau fichier
**When** le corpus complet est exécuté
**Then** tous passent sans modification du comportement existant

### AC6 — Compatibilité doubles `_SensorLikeCapabilities`

**Given** une instance de `_SensorLikeCapabilities` (double local sans `isinstance` vers `SensorCapabilities`)
**When** passée à `validate_projection("sensor", ...)`
**Then** la résolution via le fallback `getattr` fonctionne correctement
**And** `has_state=True` → `is_valid=True` ; `has_state=False` → `is_valid=False`

### AC7 — Aucun effet de bord produit

**Given** la story implémentée
**When** `PRODUCT_SCOPE` est inspecté
**Then** sa valeur est exactement `["light", "cover", "switch"]`
**And** aucun code applicatif n'a été modifié

## Tasks / Subtasks

- [x] Task 1 — Écrire les tests nominaux sensor/binary_sensor (AC: #1, #4)
  - [x] `test_sensor_with_has_state_true_is_valid()` — 4 assertions sur `ProjectionValidity`
  - [x] `test_binary_sensor_with_has_state_true_is_valid()` — 4 assertions sur `ProjectionValidity`
  - [x] `test_projection_validity_completeness_on_success()` — vérifier que les 4 champs existent et sont cohérents

- [x] Task 2 — Écrire les tests d'échec capability et fields (AC: #2, #4)
  - [x] `test_sensor_with_has_state_false_is_invalid()` — vérifier `is_valid=False`, `reason_code`, `missing_capabilities`, `missing_fields`
  - [x] `test_binary_sensor_with_has_state_false_is_invalid()` — mêmes 4 assertions
  - [x] `test_projection_validity_completeness_on_failure()` — aucun champ vide/None quand invalide

- [x] Task 3 — Écrire le test composant inconnu (AC: #3)
  - [x] `test_unknown_component_returns_false_with_ha_component_unknown()` — `is_valid is False` (PAS `None`), `reason_code=="ha_component_unknown"`, listes vides

- [x] Task 4 — Écrire les tests de non-régression et compatibilité doubles (AC: #5, #6, #7)
  - [x] `test_light_nominal_non_regression()` — `LightCapabilities(has_on_off=True)` → `is_valid=True`
  - [x] `test_light_failure_non_regression()` — `LightCapabilities(has_on_off=False)` → `reason_code=="ha_missing_command_topic"`
  - [x] `test_cover_nominal_non_regression()` — `CoverCapabilities()` → `is_valid=True`
  - [x] `test_switch_nominal_non_regression()` — `SwitchCapabilities(has_on_off=True)` → `is_valid=True`
  - [x] `test_sensor_like_double_with_state_true_works()` — double local sans `isinstance` → `is_valid=True`
  - [x] `test_sensor_like_double_with_state_false_works()` — double local → `is_valid=False`, `reason_code=="ha_missing_state_topic"`
  - [x] `test_product_scope_unchanged()` — `PRODUCT_SCOPE == ["light", "cover", "switch"]`

- [x] Task 5 — Valider la non-régression corpus complet
  - [x] Exécuter `python3 -m pytest resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py` → tous passent
  - [x] Exécuter `python3 -m pytest resources/daemon/tests/unit/test_step3_validate_projection.py resources/daemon/tests/unit/test_story_7_2_wave_registry.py` → 0 régression
  - [x] Exécuter `python3 -m pytest` (corpus complet depuis racine daemon) → baseline ≥ 1150 passed, 0 régression

## Dev Notes

### Fichier à créer — unique livrable de la story

```
resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py
```

Naming pattern cohérent avec :
- `test_story_7_1_projection_validity_diagnostic.py`
- `test_story_7_2_wave_registry.py`

### Structure minimale prescrite du fichier de tests

```python
"""Tests story 7.3 — validation de projection de la vague cible.

Prouve que sensor et binary_sensor sont structurellement validables
via validate_projection() — état 'validable' selon AR6.
Tests en isolation totale : aucun daemon, MQTT, asyncio.
"""

from models.mapping import (
    BinaryCapabilities,  # N'existe pas — utiliser SensorCapabilities pour les deux
    LightCapabilities,
    CoverCapabilities,
    SwitchCapabilities,
    SensorCapabilities,
    ProjectionValidity,
)
from validation.ha_component_registry import validate_projection, PRODUCT_SCOPE
```

**Attention** : `sensor` et `binary_sensor` partagent `SensorCapabilities` — il n'y a pas de `BinarySensorCapabilities` distincte. Les tests AC1 et AC2 utilisent `SensorCapabilities` pour les deux types.

### Double local pour AC6 (à définir dans le fichier de test)

```python
class _SensorLikeCapabilities:
    """Double minimal — simule le fallback getattr path dans _resolve_capability."""
    def __init__(self, has_state: bool = True):
        self.has_state = has_state
```

Ce double coexiste avec `SensorCapabilities` : les deux chemins (`isinstance` et `getattr`) doivent continuer à fonctionner.

### Cas `is_valid` pour composant inconnu — clarification contrat

Le type `Optional[bool]` de `ProjectionValidity.is_valid` est intentionnel : `None` est une valeur **d'orchestration** (étape 3 skippée en amont). La fonction `validate_projection()` elle-même n'émet jamais `None` :

```python
# is_valid=False (pas None) pour type inconnu — source: ha_component_registry.py ligne 138
return ProjectionValidity(
    is_valid=False,
    reason_code="ha_component_unknown",
    missing_fields=[],
    missing_capabilities=[],
)
```

Écrire `assert result.is_valid is False` dans AC3, pas `is None`.

### Chemin `_resolve_capability` pour `has_state`

```python
if abstract == "has_state":
    if isinstance(capabilities, SensorCapabilities):   # chemin typé — Story 7.2
        return capabilities.has_state
    return bool(getattr(capabilities, "has_state", False))  # fallback — doubles
```

Les tests AC6 exercent le fallback `getattr` (double local). Les tests AC1/AC2 exercent le chemin `isinstance`.

### Imports nécessaires dans le fichier de test

```python
from models.mapping import (
    LightCapabilities,
    CoverCapabilities,
    SwitchCapabilities,
    SensorCapabilities,
    ProjectionValidity,
)
from validation.ha_component_registry import validate_projection, PRODUCT_SCOPE
```

Pas de `conftest.py`, pas d'imports `asyncio`, pas d'imports `mqtt`. Tests purement synchrones.

### Commandes de validation

```bash
# RED → GREEN ciblé
python3 -m pytest resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py -v

# Non-régression ciblée
python3 -m pytest resources/daemon/tests/unit/test_step3_validate_projection.py \
                  resources/daemon/tests/unit/test_story_7_2_wave_registry.py \
                  resources/daemon/tests/unit/test_ha_component_registry.py -v

# Corpus complet (depuis resources/daemon/)
python3 -m pytest

# Qualité code
python3 -m flake8 resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py
```

### Dev Agent Guardrails

- **Ne pas modifier `validate_projection()`** — elle est correcte. Si un test échoue, c'est le test qui est faux, pas l'implémentation.
- **Ne pas modifier `HA_COMPONENT_REGISTRY`** ni `PRODUCT_SCOPE`.
- **Ne pas créer de mapper** (`mapping/sensor.py`) — hors scope pe-epic-7.
- **Ne pas toucher `cause_mapping.py`**, `models/cause_mapping.py`, ni aucun fichier UX.
- **`is_valid is False` pour composant inconnu** — jamais `is_valid is None` dans les assertions (cf. contrat ci-dessus).
- **`SensorCapabilities` partagée pour sensor et binary_sensor** — pas de dataclass séparée.
- **Conserver les doubles `_SensorLikeCapabilities`** dans `test_step3_validate_projection.py` — ne pas les supprimer ni les remplacer.
- **Tests synchrones uniquement** — aucun `pytest.mark.asyncio`, aucune fixture daemon.
- **Isolation totale** — le fichier doit s'exécuter sans MQTT, sans daemon, sans connexion réseau.

### Project Structure Notes

- Nouveau fichier : `resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py`
- Aucun autre fichier créé ou modifié
- Chemin d'import standard depuis `resources/daemon/` : `from models.mapping import ...` et `from validation.ha_component_registry import ...`

### References

- [Source: `resources/daemon/validation/ha_component_registry.py` — `validate_projection()` lignes 124–184, `_resolve_capability()` lignes 91–117, `HA_COMPONENT_REGISTRY`, `PRODUCT_SCOPE`]
- [Source: `resources/daemon/models/mapping.py` — `SensorCapabilities`, `ProjectionValidity`, `MappingCapabilities`]
- [Source: `resources/daemon/tests/unit/test_step3_validate_projection.py` — doubles locaux `_SensorLikeCapabilities`, pattern tests existants]
- [Source: `resources/daemon/tests/unit/test_story_7_2_wave_registry.py` — 4 tests validate_projection déjà présents (baseline)]
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` — Epic 7, Story 7.3, AR6, FR40, FR42]
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` — D3, AR7 (pureté fonctionnelle)]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 — 2026-04-27

### Debug Log References

_Aucun — implémentation directe, tous les tests verts dès le premier run._

### Completion Notes List

- 14 tests créés dans `test_story_7_3_projection_validation_wave.py` — 14/14 PASS
- Chemin `isinstance(SensorCapabilities)` exercé par AC1/AC2 ; chemin `getattr` fallback exercé par AC6
- `is_valid is False` (jamais `None`) pour composant inconnu confirmé AC3
- `PRODUCT_SCOPE == ["light", "cover", "switch"]` inchangé AC7
- Aucun code applicatif modifié
- Corpus complet : **1164 passed**, baseline 1150 + 14 nouveaux — 0 régression

### Review Fixes Applied (2026-04-27)

- M2 : `test_sensor_like_double_with_state_false_works` étendu — assertions ajoutées sur `missing_capabilities == ["has_state"]` et `missing_fields == ["state_topic"]` pour verrouiller la propagation côté fallback `getattr`
- L1 : tests non-régression light/cover/switch alignés sur le pattern AC1/AC2 — 4 assertions complètes (`is_valid`, `reason_code`, `missing_capabilities`, `missing_fields`)
- L2 : `hasattr(...)` redondants retirés des tests de complétude (les attributs sont garantis par `@dataclass`)
- Re-run post-fix : 14/14 PASS, corpus complet 1164 passed, flake8 clean

### File List

- `resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py` (nouveau)

### Change Log

- 2026-04-27 — Story 7.3 implémentée : 14 tests de validation de projection vague cible (sensor/binary_sensor) créés — état `connu → validable` selon AR6 satisfait
- 2026-04-27 — Code review : corrections M2/L1/L2 appliquées (assertions `missing_*` étendues, non-régression light/cover/switch alignée 4 assertions, `hasattr` redondants retirés) — 14/14 PASS, 1164 passed, status → done
