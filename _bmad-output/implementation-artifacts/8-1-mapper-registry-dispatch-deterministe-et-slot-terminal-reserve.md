# Story 8.1 : MapperRegistry — dispatch déterministe et slot terminal réservé

Status: review

## Story

En tant que mainteneur,
je veux un `MapperRegistry` qui enregistre les mappers HA dans un ordre déterministe et réserve explicitement un slot terminal pour un futur `FallbackMapper`,
afin de remplacer la cascade hardcodée `LightMapper -> CoverMapper -> SwitchMapper` par une itération registry-driven sans introduire de nouveau comportement.

## Acceptance Criteria

**AC1 — Ordre du registre**
Given le registre des mappers,
When il est inspecté au démarrage du daemon,
Then il contient dans cet ordre exact : `LightMapper`, `CoverMapper`, `SwitchMapper`, `FallbackMapper` (terminal).

**AC2 — FallbackMapper no-op**
Given le `FallbackMapper` est appelé dans cet epic,
When son résultat est inspecté,
Then il retourne `None` systématiquement (slot câblé, comportement réel ouvert dans `pe-epic-9`).

**AC3 — Parité comportementale registry vs cascade**
Given une itération registry-driven sur un équipement éligible,
When elle est comparée à la cascade hardcodée actuelle sur les 30 équipements de référence,
Then le mapper qui produit un mapping non-`None` est strictement le même dans les deux paths.

> *Note de scope Story 8.1* : la parité formelle sur les 30 équipements de référence est portée par le gate golden-file Story 8.4 (corpus à construire). Pour Story 8.1, la parité est validée à l'échelle unit-test sur 4 cas représentatifs (light, cover, switch, sans mapper) — voir Task 3.3-3.6. Le corpus 30-eq construit en Story 8.4 devient la baseline de régression-control réutilisée par pe-epic-9. (Précision ajoutée suite au LOW finding du code review 2026-05-02.)

## Tasks / Subtasks

- [x] Task 1 — Créer `FallbackMapper` stub dans `resources/daemon/mapping/fallback.py` (AC: 2)
  - [x] 1.1 — Créer le fichier `resources/daemon/mapping/fallback.py` avec classe `FallbackMapper`
  - [x] 1.2 — Implémenter `map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]` retournant `None` systématiquement — aucune logique de projection dans cet epic
  - [x] 1.3 — Ne pas implémenter `decide_publication()` sur `FallbackMapper` — hors scope Story 8.1

- [x] Task 2 — Créer `MapperRegistry` dans `resources/daemon/mapping/registry.py` (AC: 1, 3)
  - [x] 2.1 — Créer le fichier `resources/daemon/mapping/registry.py`
  - [x] 2.2 — Implémenter `MapperRegistry` avec liste ordonnée : `[LightMapper(), CoverMapper(), SwitchMapper(), FallbackMapper()]` — ordre fixé, non configurable
  - [x] 2.3 — Exposer propriété `mappers` retournant la liste des instances dans l'ordre (pour inspection AC1)
  - [x] 2.4 — Implémenter `map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]` : itérer `self.mappers`, retourner le premier résultat non-`None`, ou `None` si tous retournent `None`
  - [x] 2.5 — Exposer `__iter__` ou `__len__` si utile pour les tests ; priorité à la lisibilité

- [x] Task 3 — Tests unitaires `resources/daemon/tests/unit/test_story_8_1_mapper_registry.py` (AC: 1, 2, 3)
  - [x] 3.1 — Test AC1 : instancier `MapperRegistry()`, vérifier que `registry.mappers` est `[LightMapper, CoverMapper, SwitchMapper, FallbackMapper]` (types dans l'ordre)
  - [x] 3.2 — Test AC2 : vérifier que `FallbackMapper().map(eq, snapshot)` retourne `None` pour tout équipement (light, cover, switch, inconnu)
  - [x] 3.3 — Test AC3 parité light : construire un eqLogic avec commandes LIGHT_*, exécuter cascade hardcodée et `registry.map()`, vérifier que les deux retournent un `MappingResult` de type `"light"` (même mapper gagne)
  - [x] 3.4 — Test AC3 parité cover : idem avec commandes FLAP_*, vérifier que les deux retournent `"cover"`
  - [x] 3.5 — Test AC3 parité switch : idem avec commandes ENERGY_*, vérifier que les deux retournent `"switch"`
  - [x] 3.6 — Test AC3 parité équipement sans mapper : eqLogic sans commandes LIGHT_*/FLAP_*/ENERGY_*, vérifier que les deux paths retournent `None` (le `continue` historique et `registry.map()` donnent tous deux `None`)

## Dev Notes

### Contrat d'interface des nouveaux modules

**`resources/daemon/mapping/fallback.py`**

```python
from typing import Optional
from models.topology import JeedomEqLogic, TopologySnapshot
from models.mapping import MappingResult

class FallbackMapper:
    """Slot terminal réservé pe-epic-9 Story 9.4. Retourne None systématiquement dans cet epic."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        return None
```

Même signature que `LightMapper.map()`, `CoverMapper.map()`, `SwitchMapper.map()`. Pas de méthode `decide_publication()` — hors scope Story 8.1. Aucun log requis dans ce stub (le FallbackMapper réel de pe-epic-9 Story 9.4 ajoutera les logs).

**`resources/daemon/mapping/registry.py`**

```python
from typing import Iterator, List, Optional
from models.topology import JeedomEqLogic, TopologySnapshot
from models.mapping import MappingResult
from mapping.light import LightMapper
from mapping.cover import CoverMapper
from mapping.switch import SwitchMapper
from mapping.fallback import FallbackMapper

class MapperRegistry:
    """Registry ordonné des mappers HA — ordre déterministe, slot FallbackMapper terminal."""

    def __init__(self) -> None:
        self._mappers = [
            LightMapper(),
            CoverMapper(),
            SwitchMapper(),
            FallbackMapper(),  # slot terminal — no-op dans cet epic
        ]

    @property
    def mappers(self) -> List:
        return list(self._mappers)

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        for mapper in self._mappers:
            result = mapper.map(eq, snapshot)
            if result is not None:
                return result
        return None
```

### Ce que Story 8.1 ne touche PAS — garder intact

| Fichier | Statut |
|---|---|
| `resources/daemon/transport/http_server.py` | **Non modifié** — refactor boucle dans Story 8.3 |
| `resources/daemon/mapping/light.py` | **Non modifié** — LightMapper inchangé |
| `resources/daemon/mapping/cover.py` | **Non modifié** — CoverMapper inchangé |
| `resources/daemon/mapping/switch.py` | **Non modifié** — SwitchMapper inchangé |
| `resources/daemon/discovery/publisher.py` | **Non modifié** — PublisherRegistry dans Story 8.2 |
| `resources/daemon/validation/ha_component_registry.py` | **Non modifié** — PRODUCT_SCOPE et HA_COMPONENT_REGISTRY intacts |
| Tout fichier causant un nouveau type publié | **Interdit** — gate pe-epic-8 |

### Cascade hardcodée actuelle à comprendre (http_server.py lignes 997-1047)

```python
# Actuel — hardcodé (ne pas modifier dans Story 8.1)
light_mapper = LightMapper()
cover_mapper = CoverMapper()
switch_mapper = SwitchMapper()

# Dans la boucle for eq_id, result in eligibility.items():
mapping = light_mapper.map(eq, snapshot)
if mapping is None:
    mapping = cover_mapper.map(eq, snapshot)
if mapping is None:
    mapping = switch_mapper.map(eq, snapshot)
if mapping is None:
    continue  # ligne 1047 — skip silencieux (remplacé Story 8.3)
```

Le `MapperRegistry` réplique exactement ce comportement : `LightMapper` → `CoverMapper` → `SwitchMapper` → `FallbackMapper` (retourne `None` → équivalent au `continue` ligne 1047). La parité est garantie par les tests AC3 de Task 3.

### Patterns de tests à suivre

Exemples de fixtures dans les tests existants :
- `test_step2_mapping_candidat.py` — construction de `JeedomEqLogic` / `JeedomCmd` pour les tests mappers
- `test_story_7_2_wave_registry.py` — pattern de test de registre HA (comparable structure)
- `test_ha_component_registry.py` — pattern d'inspection d'un registre

Pour les tests AC3, construire des fixtures minimalistes (pas de mock aléatoire) :
- Light : `eq` avec `JeedomCmd(generic_type="LIGHT_ON")` + `JeedomCmd(generic_type="LIGHT_OFF")` + `JeedomCmd(generic_type="LIGHT_STATE")`
- Cover : `eq` avec `JeedomCmd(generic_type="FLAP_UP")` + `FLAP_DOWN` + `FLAP_STATE`
- Switch : `eq` avec `JeedomCmd(generic_type="ENERGY_ON")` + `ENERGY_OFF` + `ENERGY_STATE`
- Sans mapper : `eq` avec `JeedomCmd(generic_type="TEMPERATURE")` (hors LIGHT_*/FLAP_*/ENERGY_*)

### Relation avec les stories suivantes

- **Story 8.2** crée `PublisherRegistry` (`discovery/publisher.py`) — indépendant, peut se développer en parallèle
- **Story 8.3** remplace la cascade hardcodée de `http_server.py` par `MapperRegistry` — préréquis Story 8.1
- **Story 8.4** crée le golden-file sur 30 équipements — préréquis Stories 8.1+8.2+8.3
- **Story 9.4** branche la logique `FallbackMapper` réelle dans `mapping/fallback.py` — préréquis pe-epic-8 clos

### Localisation dans l'arbre source

```
resources/daemon/
├── mapping/
│   ├── __init__.py          (inchangé)
│   ├── light.py             (inchangé)
│   ├── cover.py             (inchangé)
│   ├── switch.py            (inchangé)
│   ├── fallback.py          ← NOUVEAU Story 8.1
│   └── registry.py          ← NOUVEAU Story 8.1
├── tests/
│   └── unit/
│       └── test_story_8_1_mapper_registry.py  ← NOUVEAU Story 8.1
```

### Dev Agent Guardrails

**Cadre de garantie pe-epic-8 — non négociable :**
- Aucune story n'introduit un nouveau type publié côté HA
- `PRODUCT_SCOPE` reste `["light", "cover", "switch", "sensor", "binary_sensor"]` — non modifié
- `HA_COMPONENT_REGISTRY` — non modifié
- `cause_label`, `cause_action`, `reason_code` — non modifiés
- `http_server.py` — non modifié dans Story 8.1 (Story 8.3 le modifie, pas maintenant)

**Si un test AC3 échoue :** la parité est rompue. Chercher la divergence dans l'ordre des mappers ou dans la logique du `map()` du registry — ne pas "corriger" un comportement existant, restaurer la parité exacte.

**FallbackMapper stub :** aucune logique de projection dans ce fichier. `return None` et c'est tout. La Story 9.4 ajoutera la logique réelle ; ne pas anticiper.

**Imports dans `registry.py` :** importer directement depuis `mapping.light`, `mapping.cover`, `mapping.switch`, `mapping.fallback` — ne pas importer depuis `transport/` ou `validation/` (séparation AR3).

### Project Structure Notes

Alignement avec l'architecture :
- AR3 (séparation registre/mapping/discovery) : `MapperRegistry` vit dans `mapping/`, importe depuis `mapping.*`, n'importe pas `transport/` ni `validation/`
- FR15 (faire évoluer les règles de mapping sans modifier l'ordre canonique des étapes) : le registry isole le dispatch de l'ordre canonique du pipeline `http_server.py`
- Règle de dépendance architecture : `mapping/` importe depuis `models/` — `registry.py` suit ce principe

### References

- [Source: epics-projection-engine.md#Story 8.1] — user story, AC, dev notes
- [Source: epics-projection-engine.md#Epic 8] — cadre de garantie zero-comportement
- [Source: sprint-change-proposal-2026-04-30.md §5.2] — rationale et séquençage pe-epic-8
- [Source: architecture-projection-engine.md AR3] — séparation mapping/discovery/validation
- [Source: architecture-projection-engine.md FR15] — règle d'évolution mapping sans modification pipeline
- [Source: resources/daemon/transport/http_server.py:997-1047] — cascade hardcodée à répliquer via registry
- [Source: resources/daemon/mapping/light.py] — interface LightMapper.map() à reproduire dans FallbackMapper
- [Source: resources/daemon/mapping/cover.py] — interface CoverMapper.map()
- [Source: resources/daemon/mapping/switch.py] — interface SwitchMapper.map()
- [Source: active-cycle-manifest.md §7] — règle : citer golden-file 8.4 comme baseline de regression-control pour toute story touchant le dispatch

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- RED : ajout du test Story 8.1 puis exécution ciblée ; échec attendu sur `ModuleNotFoundError: No module named 'mapping.fallback'`
- GREEN : ajout minimal de `FallbackMapper` no-op et `MapperRegistry` ordonné `LightMapper -> CoverMapper -> SwitchMapper -> FallbackMapper`
- REFACTOR : correction compatibilité Python 3.9 dans le test, contrôle flake8 ciblé, aucune modification des fichiers interdits

### Debug Log References

- `python3 -m pytest tests/unit/test_story_8_1_mapper_registry.py` — RED confirmé : `ModuleNotFoundError: No module named 'mapping.fallback'`
- `python3 -m pytest tests/unit/test_story_8_1_mapper_registry.py` — 6 passed
- `python3 -m pytest tests` — 657 passed, 587 warnings existants
- `python3 -m flake8 resources/daemon/mapping/fallback.py resources/daemon/mapping/registry.py resources/daemon/tests/unit/test_story_8_1_mapper_registry.py` — 0

### Completion Notes List

Story créée le 2026-05-02. Analyse exhaustive des sources :
- epics-projection-engine.md (Stories 8.1-8.4, Gates pe-epic-8, Story 9.4)
- sprint-change-proposal-2026-04-30.md (cadre de garantie, séquençage, rationale)
- active-cycle-manifest.md (règles prescriptives section 7)
- architecture-projection-engine.md (AR3, FR15, règles de dépendance)
- http_server.py:997-1047 (cascade hardcodée à remplacer par Story 8.3)
- mapping/light.py, cover.py, switch.py (interface mapper à reproduire)
- Terrain story : false (pas de daemon/MQTT/discovery HA dans cette story)
- Implémenté `FallbackMapper` terminal no-op : `map()` retourne `None` systématiquement, aucune logique de projection, aucun `decide_publication()`
- Implémenté `MapperRegistry` ordonné et non configurable : `LightMapper`, `CoverMapper`, `SwitchMapper`, `FallbackMapper`
- Ajouté les tests AC1/AC2/AC3 : ordre canonique, fallback no-op sur 4 équipements, parité registry vs cascade pour light/cover/switch/sans mapper
- Scope pe-epic-8 respecté : aucun nouveau type publié, aucun câblage dans `http_server.py`, aucun fichier interdit modifié

### File List

- `resources/daemon/mapping/fallback.py` (NOUVEAU)
- `resources/daemon/mapping/registry.py` (NOUVEAU)
- `resources/daemon/tests/unit/test_story_8_1_mapper_registry.py` (NOUVEAU)
- `_bmad-output/implementation-artifacts/8-1-mapper-registry-dispatch-deterministe-et-slot-terminal-reserve.md` (statut BMAD)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (statut BMAD)

## Change Log

- 2026-05-02 — Implémentation Story 8.1 : `FallbackMapper` no-op, `MapperRegistry` ordonné, tests AC1/AC2/AC3 ; corpus daemon 657 passed ; statut prêt pour review
