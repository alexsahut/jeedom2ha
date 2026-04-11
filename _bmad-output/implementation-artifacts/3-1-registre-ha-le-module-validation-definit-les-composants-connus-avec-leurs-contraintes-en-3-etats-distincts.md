# Story 3.1 : Registre HA — le module validation/ définit les composants connus avec leurs contraintes en 3 états distincts

Status: review

## Story

En tant que mainteneur,
je veux un module `validation/` physiquement séparé qui contient le registre statique des composants HA connus avec leurs contraintes structurelles, organisé selon les trois états distincts (connu / validable / ouvert),
afin de pouvoir faire évoluer le registre sans toucher aux modules mapping ou publication, et de ne jamais confondre les états du registre avec les étapes du pipeline.

## Acceptance Criteria

1. **Given** le module `resources/daemon/validation/ha_component_registry.py`
   **When** il est importé
   **Then** il exporte `HA_COMPONENT_REGISTRY` (dict des composants connus avec `required_fields` et `required_capabilities`) et `PRODUCT_SCOPE` (liste des composants ouverts)
   **And** le module n'importe rien depuis `mapping/`, `discovery/` ni `transport/` (AR3 — séparation physique)

2. **Given** un composant présent dans `HA_COMPONENT_REGISTRY`
   **When** son état est évalué
   **Then** il est dans l'état `connu` — ses contraintes structurelles sont modélisées (`required_fields` + `required_capabilities`)
   **And** l'état `connu` est distinct de `validable` (nécessite que `validate_projection()` aboutisse positivement sur des cas nominaux — câblé en Story 3.2)
   **And** l'état `validable` est distinct de `ouvert` (nécessite satisfaction simultanée des 3 conditions de FR40 — câblé en Story 3.3)

3. **Given** la valeur initiale de `PRODUCT_SCOPE`
   **When** le cycle commence
   **Then** `PRODUCT_SCOPE = ["light", "cover", "switch"]` (AR5, héritage V1.1)
   **And** toute modification de `PRODUCT_SCOPE` sans satisfaire FR40 dans le même incrément est explicitement interdite par contrat documenté (AR6, AR13)

4. **Given** un test d'intégrité structurelle du registre
   **When** le test s'exécute
   **Then** chaque composant dans `PRODUCT_SCOPE` est également dans `HA_COMPONENT_REGISTRY`
   **And** pour chaque composant dans `HA_COMPONENT_REGISTRY`, au moins un `required_field` ou une `required_capability` est définie

## Tasks / Subtasks

- [x] Task 1 — Créer `resources/daemon/validation/__init__.py` (AC: #1)
  - [x] Fichier vide — package Python nécessaire pour les imports `from validation.ha_component_registry import ...`

- [x] Task 2 — Créer `resources/daemon/validation/ha_component_registry.py` (AC: #1, #2, #3)
  - [x] Définir `HA_COMPONENT_REGISTRY` dict statique avec 9 composants (voir Dev Notes — contenu canonique D3)
  - [x] Définir `PRODUCT_SCOPE = ["light", "cover", "switch"]` avec commentaire versionné
  - [x] Aucun import depuis `mapping/`, `discovery/`, `transport/` — les données sont purement statiques, aucun import du tout n'est nécessaire
  - [x] NE PAS implémenter `validate_projection()` — c'est le travail de Story 3.2

- [x] Task 3 — Créer `resources/daemon/tests/unit/test_ha_component_registry.py` (AC: #1, #2, #3, #4)
  - [x] **3.1 — Test AC1 exports** : `test_module_exports_registry_and_product_scope`
    - `from validation.ha_component_registry import HA_COMPONENT_REGISTRY, PRODUCT_SCOPE`
    - `assert isinstance(HA_COMPONENT_REGISTRY, dict)`
    - `assert isinstance(PRODUCT_SCOPE, list)`
  - [x] **3.2 — Test AC1 no forbidden imports** : `test_module_no_forbidden_imports`
    - Parser le source de `validation/ha_component_registry.py` avec `ast`
    - Asserter qu'aucun `import` ou `from` ne référence `mapping`, `discovery`, `transport`
  - [x] **3.3 — Test AC4 structure clés** : `test_each_registry_component_has_required_keys`
    - Pour chaque composant dans `HA_COMPONENT_REGISTRY` : assert `"required_fields"` et `"required_capabilities"` présents
    - `isinstance(spec["required_fields"], list)` et `isinstance(spec["required_capabilities"], list)`
  - [x] **3.4 — Test AC2 + AC4 contraintes modélisées** : `test_each_registry_component_has_at_least_one_constraint`
    - Pour chaque composant : `bool(spec["required_fields"]) or bool(spec["required_capabilities"])` == True
    - Vérifie l'état `connu` — un composant sans aucune contrainte ne peut pas être `connu`
  - [x] **3.5 — Test AC3 valeur initiale** : `test_product_scope_initial_value`
    - `assert PRODUCT_SCOPE == ["light", "cover", "switch"]`
  - [x] **3.6 — Test AC4 PRODUCT_SCOPE ⊆ HA_COMPONENT_REGISTRY** : `test_product_scope_subset_of_registry`
    - Pour chaque composant dans `PRODUCT_SCOPE` : assert présent dans `HA_COMPONENT_REGISTRY`
  - [x] **3.7 — Test AC2 état connu ≠ ouvert** : `test_registry_has_components_not_in_product_scope`
    - `not_open = set(HA_COMPONENT_REGISTRY.keys()) - set(PRODUCT_SCOPE)` → `assert len(not_open) > 0`
    - Vérifie que la distinction `connu`/`ouvert` est réelle — des composants sont connus mais non ouverts
  - [x] **3.8 — Test AC3 gouvernance PRODUCT_SCOPE documentée** : `test_product_scope_modification_requires_fr40`
    - Assertion documentaire : vérifie que `PRODUCT_SCOPE` est défini dans le module (pas inline dans le test)
    - Ajoute un commentaire dans le test explicitant le contrat AR13 (toute modification = tests FR40 dans le même incrément)

- [x] Task 4 — Vérifier la non-régression (AC: #1 à #4)
  - [x] `pytest resources/daemon/tests/` depuis `resources/daemon/` : 337 + N PASS (N = nouveaux tests de cette story)
  - [x] Confirmer 0 failure, 0 error

## Dev Notes

### Contexte dans le pipeline

Story 3.1 est l'entrée de `pe-epic-3`. Elle crée la **fondation de données** (registre + scope) que :
- Story 3.2 consommera pour implémenter `validate_projection()` dans le même fichier
- Story 3.3 consommera pour démontrer la gouvernance d'ouverture (ajout `sensor` à `PRODUCT_SCOPE`)
- Epic 4 consommera via `PRODUCT_SCOPE` dans `decide_publication()`
- Epic 5 consommera via `validate_projection()` dans le sync handler

Cette story **ne touche pas de code de production** au sens workflow — elle crée un nouveau module de zéro, sans modifier les modules existants.

### Contenu canonique du module (D3 — architecture-projection-engine.md)

```python
"""ha_component_registry.py — Registre statique des composants HA connus.

Trois états distincts (AR6) :
  - connu    : entrée présente dans HA_COMPONENT_REGISTRY (contraintes modélisées)
  - validable: validate_projection() aboutit positivement sur cas nominaux (Story 3.2)
  - ouvert   : présent dans PRODUCT_SCOPE après satisfaction simultanée de FR40 (Story 3.3)

Dépendances : aucune. Ce module ne doit pas importer depuis mapping/, discovery/ ni transport/ (AR3).
"""

HA_COMPONENT_REGISTRY = {
    "light": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "cover": {
        "required_fields": ["platform", "availability"],
        "required_capabilities": [],  # cover read-only valide côté HA (pas de command_topic requis)
    },
    "switch": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "sensor": {
        "required_fields": ["state_topic", "platform", "availability"],
        "required_capabilities": ["has_state"],
    },
    "binary_sensor": {
        "required_fields": ["state_topic", "platform", "availability"],
        "required_capabilities": ["has_state"],
    },
    # Composants connus mais non ouverts en V1.x (PRODUCT_SCOPE restreint) :
    "button": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "number": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "select": {
        "required_fields": ["command_topic", "options", "platform", "availability"],
        "required_capabilities": ["has_command", "has_options"],
    },
    "climate": {
        "required_fields": ["availability"],
        "required_capabilities": [],
    },
}

PRODUCT_SCOPE = ["light", "cover", "switch"]  # V1.x — versionné par cycle produit
# AR13 : toute modification de PRODUCT_SCOPE exige simultanément dans le même incrément :
#   (1) entrée dans HA_COMPONENT_REGISTRY avec required_fields + required_capabilities,
#   (2) au moins un cas nominal + un cas d'échec validate_projection() pour ce type,
#   (3) test de non-régression du contrat 4D passant.
```

**Note critique** : `cover` a `required_capabilities: []` mais `required_fields: ["platform", "availability"]` → il est bien `connu` (au moins un required_field). Le test 3.4 doit vérifier `bool(required_fields) or bool(required_capabilities)`, pas `and`.

### Abstraction des capabilities — note pour Story 3.2

Les noms abstraits dans `required_capabilities` (`"has_command"`, `"has_state"`, `"has_options"`) **ne correspondent pas directement** aux champs de `LightCapabilities`/`CoverCapabilities`/`SwitchCapabilities`. La résolution de cette correspondance est l'affaire de `validate_projection()` (Story 3.2). Ne pas tenter de la câbler dans cette story.

| Capability abstraite | Champ concret par mapper |
|---|---|
| `"has_command"` | `LightCapabilities.has_on_off` / `CoverCapabilities.has_open_close` / `SwitchCapabilities.has_on_off` |
| `"has_state"` | `SwitchCapabilities.has_state` |
| `"has_options"` | (Story 3.2 + au-delà) |

### Pattern d'import du test

```python
"""Tests de l'étape 3 — Registre HA — Story 3.1.

Vérifie la structure statique de HA_COMPONENT_REGISTRY et PRODUCT_SCOPE,
l'absence d'imports interdits, et les invariants des 3 états du registre.
Tests en isolation totale : aucune dépendance MQTT, daemon, pytest-asyncio.
"""
import ast
import pathlib
from validation.ha_component_registry import HA_COMPONENT_REGISTRY, PRODUCT_SCOPE
```

### Test no_forbidden_imports — pattern AST

```python
def test_module_no_forbidden_imports():
    """AR3 — validation/ n'importe rien depuis mapping/, discovery/, transport/."""
    source_path = pathlib.Path(__file__).parent.parent.parent / "validation" / "ha_component_registry.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"mapping", "discovery", "transport"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            assert root not in forbidden, f"Import interdit depuis '{root}' dans validation/"
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in forbidden, f"Import interdit depuis '{root}' dans validation/"
```

Note : le chemin AST depuis le fichier test → `../../../validation/ha_component_registry.py`. Vérifier que `pathlib.Path(__file__).parent` pointe vers `tests/unit/`, donc remonter 3 niveaux pour atteindre `daemon/`.

### Arborescence créée

```
resources/daemon/
├── validation/                        ← NOUVEAU (Epic 3)
│   ├── __init__.py                    ← vide — package Python
│   └── ha_component_registry.py      # HA_COMPONENT_REGISTRY, PRODUCT_SCOPE
│                                     # (validate_projection() ajouté en Story 3.2)
└── tests/unit/
    └── test_ha_component_registry.py  ← NOUVEAU
```

### Dev Agent Guardrails

- **NE PAS implémenter `validate_projection()`** — c'est le travail de Story 3.2. Le fichier `ha_component_registry.py` ne doit contenir que les données.
- **NE PAS modifier** `models/mapping.py`, `mapping/light.py`, `cover.py`, `switch.py` — aucun fichier existant modifié.
- **NE PAS modifier** `models/cause_mapping.py` — les reason_codes de classe 2 (`ha_missing_command_topic`, etc.) seront câblés en Epic 3/4, hors scope ici.
- **Aucun import** dans `ha_component_registry.py` — le module est purement statique. Si un import apparaît, c'est une erreur de scope.
- **Pas de conftest.py** — helpers locaux au fichier test si nécessaire.
- **Pas de dépendances MQTT, pytest-asyncio, daemon** — tests en isolation totale.
- **Portée stricte** : 3 fichiers créés. 0 fichier existant modifié.
- Le test 3.4 vérifie `bool(required_fields) OR bool(required_capabilities)` — le composant `cover` (required_capabilities=[]) passe grâce à ses required_fields non vides.
- Le chemin AST dans le test 3.2 doit être calculé depuis `__file__` (test file) en remontant jusqu'à `daemon/` — tester ce chemin avant de coder le test.

### Project Structure Notes

**Fichiers créés :**
- `resources/daemon/validation/__init__.py`
- `resources/daemon/validation/ha_component_registry.py`
- `resources/daemon/tests/unit/test_ha_component_registry.py`

**Aucun fichier de production existant modifié.**

**Continuité Epic 3 :**
```
resources/daemon/validation/
├── __init__.py                    ← Story 3.1 — crée le package
└── ha_component_registry.py      ← Story 3.1 (données) + Story 3.2 (validate_projection)
```

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 3.1] — User story, AC, dev notes canoniques
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §FR36, FR37, FR38, FR40] — Registre gouverné, 3 états, gouvernance d'ouverture
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §AR3, AR4, AR5, AR6, AR13] — Séparation physique, registre statique, PRODUCT_SCOPE initial, 3 états verrouillés, NFR10 obligatoire
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §D2] — Module validation/ : rôle, exports, rationale
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §D3] — Contenu canonique de HA_COMPONENT_REGISTRY et PRODUCT_SCOPE
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §D4] — Signature validate_projection (Story 3.2 — pour ne pas l'anticiper)
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §P6] — Stratégie de vérification registre vs spec Excel HA (3 couches — non implémentée en Story 3.1)
- [Source: `resources/daemon/models/mapping.py`] — `LightCapabilities`, `CoverCapabilities`, `SwitchCapabilities`, `MappingCapabilities`, `ProjectionValidity` — types consommés par Story 3.2
- [Source: `resources/daemon/tests/unit/test_step2_mapping_candidat.py`] — Pattern isolation totale, helpers locaux, pas de conftest.py

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Implementation Plan

- Creer le package `validation/` minimal puis ecrire les tests Story 3.1 avant le module pour valider un cycle rouge/vert.
- Ajouter un registre HA purement statique, sans import et sans anticipation de `validate_projection()`.
- Verifier les invariants du registre et la non-regression complete du daemon avant passage en review.

### Debug Log References

- Rouge valide : `python3 -m pytest resources/daemon/tests/unit/test_ha_component_registry.py` -> `ModuleNotFoundError` attendu avant creation du module.
- Vert cible : `python3 -m pytest resources/daemon/tests/unit/test_ha_component_registry.py` -> `8 passed`.
- Non-regression complete : `python3 -m pytest tests/` depuis `resources/daemon/` -> `345 passed, 374 warnings`.

### Completion Notes List

- Ajout du package `resources/daemon/validation/` avec `ha_component_registry.py` exportant `HA_COMPONENT_REGISTRY` et `PRODUCT_SCOPE`.
- Registre statique implemente avec 9 composants connus et commentaire de gouvernance AR13 sur `PRODUCT_SCOPE`.
- Tests unitaires isoles ajoutes pour les exports, l'absence d'imports interdits, les invariants structurels et la distinction `connu`/`ouvert`.
- Non-regression daemon complete validee : 345 tests passent, aucun echec ni erreur.

### File List

- `_bmad-output/implementation-artifacts/3-1-registre-ha-le-module-validation-definit-les-composants-connus-avec-leurs-contraintes-en-3-etats-distincts.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/tests/unit/test_ha_component_registry.py`
- `resources/daemon/validation/__init__.py`
- `resources/daemon/validation/ha_component_registry.py`

## Change Log

- 2026-04-12 : implementation complete de la Story 3.1, ajout du registre HA statique, des tests d'integrite associes et validation de non-regression du daemon.
