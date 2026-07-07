---
stepsCompleted: [1, 2, 4, 5, 6, 7, 8]
inputDocuments:
  - prd.md
  - architecture-projection-engine.md
  - architecture-delta-review-prd-final.md
  - sprint-change-proposal-2026-07-06-mapping-configurable.md
  - _bmad-output/project-context.md
workflowType: 'architecture'
project_name: 'jeedom2ha'
user_name: 'Alexandre'
date: '2026-07-06'
lastStep: 8
status: 'complete'
completedAt: '2026-07-06'
---

# Architecture Decision Document — Delta pe-epic-16 (mapping configurable commande par commande)

_Ce document est un delta additif au cycle actif "Moteur de projection explicable". Il ne remplace ni `architecture.md` (V1.1 Pilotable, historique) ni `architecture-projection-engine.md` (canonique actif), il les complète pour le scope pe-epic-16._

## Documents d'entrée

- PRD : `prd.md` (canonique actif) — FR23, FR24, FR25, FR31, FR40, FR44, FR45
- Architecture : `architecture-projection-engine.md` (canonique actif, D1-D7), `architecture-delta-review-prd-final.md` (réconciliation)
- SCP source : `sprint-change-proposal-2026-07-06-mapping-configurable.md` (renumérotation `pe-epic-12` historique → `pe-epic-16`, commit `843481f`)
- Project context : `_bmad-output/project-context.md`
- Pas de brief/research dédié supplémentaire

## Analyse du contexte projet (Step 2)

**Exigences (PRD) :**
- FR23 : le système peut appliquer en étape 4 des politiques produit, exceptions et overrides autorisés sans les confondre avec la validité structurelle HA
- FR24 : distinguer un blocage de décision explicite d'un composant HA invalide/inconnu/échec de mapping
- FR25 : l'utilisateur expert peut appliquer les overrides avancés sans effacer la décision native du moteur
- FR31/FR40/FR44/FR45 : diagnostic 4D stable, additif, non-régressif

**Epics/Stories :** `pe-epic-16`, 8 stories (16.0→16.7), découpage 16a (backend) / 16b (UI), absorbant `backlog-icebox.md` §1 (drill-down commande par commande).

**Aspects architecturaux clés :**
- Pipeline canonique à 5 étapes : `assess_all(éligibilité) → map → validate_projection → decide_publication → publish` (`architecture-projection-engine.md` D1/D7), `MappingResult` en sous-blocs bornés, jamais de court-circuit.
- D6 (existant) anticipait un override "entre les étapes 2 et 4" comme différé — Story 16.0 le rend ferme.
- Contrainte produit dure : double granularité — un override HA ne réécrit jamais le `generic_type` Jeedom natif (non-régression Homebridge).
- Source de vérité pour "l'attendu HA par commande" = `ha-projection-reference.md/.yaml` existant, pas de table dupliquée.
- Aucune UI riche avant contrat backend stabilisé (leçon Homebridge : absence de visibilité sur l'attendu HomeKit).

**Échelle :** backend Python (pipeline mapping/validation) + persistance JSON versionnée + UI native Jeedom (PHP/JS, sans framework front). Complexité moyenne à élevée.

## ADR — Point d'injection de l'override (débat de personas)

**Contexte factuel confirmé dans le code** : `http_server.py` — `assess_all` (L.1236) → `mapper_registry.map()` (L.1297, étape 2) → `validate_projection()` (L.1316, étape 3) → `decide_publication()` (L.1319, étape 4) → `publish()` (L.1340, étape 5). `MappingResult.pipeline_step_reached` (`mapping/mapping.py` L.157-158) documente déjà cette numérotation. D6 (`architecture-projection-engine.md` L.418-424) anticipait l'extension comme différée entre étapes 2 et 4 ; D7 (L.426-437) fixe l'invariant de non-court-circuit du flux `map → validate_projection → decide_publication → publish`.

**Persona A — Architecte Pipeline (garant D7)** : l'override de type/capabilities doit patcher le `MappingResult` entre l'étape 2 et 3, jamais après — sinon `validate_projection()` s'exécuterait sur un état déjà jugé valide/invalide sur la base de l'ancien type, rendant `ProjectionValidity` mensongère.

**Persona B — Architecte Produit/UX** : deux besoins distincts existent — (1) forcer un `ha_entity_type` différent → doit repasser par `validate_projection` (Persona A) ; (2) forcer la *publication* malgré confiance insuffisante (étape 4) → override de politique, ne doit pas re-rentrer dans `validate_projection` sous peine de dupliquer la logique. Deux points d'injection distincts, pas un seul.

**Persona C — Architecte Données** : le stockage à froid compte plus que le point d'injection en mémoire. Trois options : (1) JSON dédié par équipement (clé `jeedom_eq_id`/`jeedom_cmd_id`, IDs stables confirmés) ; (2) table centrale unique ; (3) extension de `reason_details` — rejetée, car c'est un canal de *sortie* recalculé à chaque sync, pas fait pour être une source de vérité d'input (serait écrasé au sync suivant).

**Décision tranchée :**
- Overrides de type HA/capabilities : injection entre étape 2 et 3, patch d'une copie du `MappingResult`, jamais en entrée de `reason_details`.
- Overrides de politique de publication : injection entre étape 3 et 4, en paramètre additionnel de `decide_publication()` (extension de `confidence_policy` existant).
- Stockage : fichier JSON persistant dédié, indexé par IDs Jeedom stables, lu en début de cycle de sync.

## Core Architectural Decisions (Step 4 — scope 16a backend)

Pas de nouvelle techno : backend Python pur, persistance fichier JSON (cohérent avec le reste du daemon, pas de DB).

**D8 — Emplacement et responsabilité du module**
- Nouveau fichier `resources/daemon/mapping/overrides.py` (confirmé absent, à créer).
- Expose `apply_type_override(mapping: MappingResult) -> MappingResult` (patch avant `validate_projection`, L.1316) et `resolve_publication_override(eq_id, cmd_id) -> Optional[dict]` (consommé par `decide_publication`, L.1319, en paramètre additionnel).
- Aucune dépendance vers les mappers existants (`switch.py`, `light.py`, etc.) — sens unique, pas de couplage circulaire avec le registry.

**D9 — Schéma de persistance versionné**
- Fichier dédié `data/ha_overrides.json` (résolu step 7 : sibling de `resources/`, même convention que `disk_cache.py` — `jeedom2ha_cache.json` calculé via `os.path.dirname(os.path.abspath(__file__))` + `..`/`..`, cf. `main.py:15,28` et `http_server.py:53-54` ; aucun dossier `config/` n'existe dans le daemon), clé racine `schema_version: 1`.
- Entrée indexée par `f"{jeedom_eq_id}:{jeedom_cmd_id}"` (jamais par nom).
- Champ `source: "user"` dès le départ, anticipant un futur `source: "suggested"` (Story 16.3, propositions automatiques) sans migration de schéma.

**D10 — `generic_type` Jeedom jamais modifié**
- `JeedomCmd`/`JeedomEqLogic` (modèles topologie natifs) ne sont jamais mutés par `overrides.py` — le patch s'applique uniquement sur la copie `MappingResult` en mémoire. Garantit la non-régression Homebridge.

**D11 — Ordre de préséance en cas de conflit**
- Un override référençant un `ha_entity_type` incompatible avec les `capabilities` détectées par `map()` : `validate_projection()` s'exécute quand même dessus et peut renvoyer `is_valid=False` — l'override ne bypasse jamais un échec de validation structurelle.
- `reason_details` distingue explicitement `override_applied: true` + `override_source` du calcul natif (consommé par Story 16.4, diagnostic override-aware).

**D12 — Tests**
- `test_story_16_0_overrides_injection.py` : override valide appliqué avant validation, override invalide rejeté par `validate_projection` (pas de bypass), absence d'override = comportement identique à aujourd'hui (non-régression golden-file), `generic_type` natif jamais modifié (assertion explicite sur l'objet source).

## Implementation Patterns & Consistency Rules (Step 5)

Scope restreint : backend Python pur + persistance JSON, pas de DB, pas de nouvel endpoint REST public. Les catégories de conflit "naming DB/table", "routes API publiques" et "state management front" sont hors périmètre pour 16a et volontairement omises.

### Naming Patterns

**Persistance JSON (`ha_overrides.json`) :**
- Toutes les clés en `snake_case`, cohérent avec `schema_version`, `jeedom_eq_id`, `jeedom_cmd_id` déjà actés (D9).
- Clé composite d'entrée : `f"{jeedom_eq_id}:{jeedom_cmd_id}"` — jamais par nom d'équipement/commande (D9, confirmé).
- Champ `source` en valeur `snake_case` (`"user"`, futur `"suggested"`) — jamais de valeur `CamelCase`/`PascalCase`.

**Fonctions du module `overrides.py` :**
- `apply_*` : réservé aux fonctions qui patchent une **copie** de `MappingResult` (mutation en mémoire uniquement, jamais l'objet source). Ex : `apply_type_override()`.
- `resolve_*` : réservé aux fonctions qui **lisent** une décision/config sans muter d'objet pipeline. Ex : `resolve_publication_override()`.
- `list_*` / `remove_*` : réservés aux futures opérations CRUD sur le fichier JSON lui-même (gestion des overrides en tant que données), jamais utilisés pour des opérations sur le pipeline `MappingResult`.
- Toute nouvelle fonction du module doit respecter l'un de ces 4 préfixes — pas de nom générique type `get_override()` qui chevaucherait la sémantique de `resolve_*`.

### Structure Patterns

- `overrides.py` reste dans `resources/daemon/mapping/`, sans dépendance vers les mappers concrets (`switch.py`, `light.py`, etc. — D8, confirmé, sens unique).
- Tests spécifiques à l'AC d'une story : préfixe `test_story_16_X_*` (ex : `test_story_16_0_overrides_injection.py`), réservé aux tests qui valident un critère d'acceptation précis d'une story 16.x.
- Tests de non-régression golden-file existants (par domaine fonctionnel, ex : `test_mapping_sensor.py`) restent nommés par domaine — le préfixe `test_story_*` ne les remplace jamais, même s'ils touchent au même périmètre de code.
- Fichier de persistance `data/ha_overrides.json` (D9, résolu step 7 — cf. `disk_cache.py`).

### Format Patterns

**`reason_details` (champ diagnostic) :**
- `override_applied` (bool) et `override_source` (string) forment une paire indissociable : jamais l'un sans l'autre quand un override est présent.
- Si `override_applied: false` : `override_source` est **absent** de la structure (pas de clé avec valeur `null`) — cohérent avec le style existant de `reason_details` où les champs optionnels non pertinents sont omis plutôt que nullés.

### Process Patterns — Gestion d'erreur fichier JSON

Distinction actée entre deux cas radicalement différents :

1. **Fichier `ha_overrides.json` absent** (cas normal — aucun override n'a jamais été créé) : comportement **silencieux**, traité comme "aucun override", aucun log. Comportement du pipeline strictement identique à l'existant (non-régression garantie par D12).
2. **Fichier présent mais corrompu, illisible, ou `schema_version` inconnue** (anomalie) : `logger.warning()` explicite décrivant la cause (parse error / version inattendue), **puis** fallback au comportement "aucun override" — jamais bloquant pour le daemon, mais jamais silencieux non plus. Rationale : un override perdu silencieusement romprait la traçabilité de la décision (esprit D11) — Sébastien doit pouvoir comprendre après coup pourquoi un override qu'il croyait actif ne l'était plus.
- Dans les deux cas : jamais d'exception non catchée qui interromprait le cycle de sync — le fallback "aucun override" est toujours le filet de sécurité final.

### Enforcement Guidelines

**All AI Agents MUST :**
- Respecter les préfixes de fonction `apply_*` / `resolve_*` / `list_*` / `remove_*` dans `overrides.py`.
- Ne jamais introduire de log au chargement normal (fichier absent), et toujours logger un warning en cas d'anomalie de schéma/corruption avant fallback.
- Ne jamais faire exister `override_source` sans `override_applied: true`.
- Nommer les tests d'AC de story avec le préfixe `test_story_16_X_*`, sans renommer les tests de non-régression existants.

**Anti-Patterns à éviter :**
- Lever une exception fatale au démarrage du daemon si `ha_overrides.json` est absent ou corrompu.
- Ajouter un `override_source: null` au lieu d'omettre la clé.
- Nommer une fonction `get_override()` en doublon sémantique de `resolve_publication_override()`.

## Project Structure & Boundaries (Step 6)

### Fichiers ajoutés/modifiés (delta 16a backend)

```
resources/daemon/
├── mapping/
│   ├── overrides.py          [NOUVEAU] apply_type_override(), resolve_publication_override()
│   ├── mapping.py             [MODIFIÉ] reason_details étendu (override_applied/override_source, D11)
│   └── registry.py            [inchangé — aucune dépendance vers overrides.py, D8]
├── transport/
│   └── http_server.py         [MODIFIÉ] injection overrides entre étapes 2-3 (L.1297/1316) et 3-4 (L.1319, D6/ADR)
├── tests/unit/
│   └── test_story_16_0_overrides_injection.py   [NOUVEAU]
data/
└── ha_overrides.json          [NOUVEAU, runtime] — sibling de resources/, même convention que jeedom2ha_cache.json (disk_cache.py), schéma versionné D9, absent au premier lancement (comportement silencieux)
```

### Boundaries architecturales

**Boundary `overrides.py` ↔ pipeline :** sens unique — `overrides.py` ne dépend d'aucun mapper concret (`switch.py`, `light.py`, etc.), le pipeline (`http_server.py`) l'appelle, jamais l'inverse (D8, confirmé).

**Boundary données ↔ code :** `ha_overrides.json` est lu en début de cycle de sync uniquement (pas de watch/hot-reload dans ce scope) — une modification externe du fichier n'est prise en compte qu'au sync suivant, cohérent avec le "GET initial = source de vérité" déjà acté côté UX 16b.

**Boundary `generic_type` natif :** `JeedomCmd`/`JeedomEqLogic` (topologie native, `models/topology.py`) ne sont jamais importés/mutés par `overrides.py` — garantie D10, vérifiable par audit d'imports.

**Hors scope de cette structure :** tout le code PHP/JS de l'onglet "HA / jeedom2ha" (16b) — couvert par l'UX design delta séparé, aucun fichier de présentation n'est mappé ici.

### Mapping stories → structure

- Story 16.0 (injection overrides) → `overrides.py` (nouveau) + `http_server.py` (modifié) + `test_story_16_0_*`
- Story 16.1-16.2 (CRUD overrides, futur) → extensions `list_*`/`remove_*` dans `overrides.py`, même fichier
- Story 16.3 (suggestions auto) → champ `source: "suggested"` dans `ha_overrides.json`, aucun nouveau fichier (schéma déjà anticipé D9)
- Story 16.4 (diagnostic override-aware, absorbe backlog-icebox §1) → `mapping.py` (reason_details) uniquement
- Story 16.5-16.7 (UI 16b) → hors périmètre de cette architecture backend, référence `ux-design-delta-pe-epic-16-mapping-configurable.md`

## Architecture Validation Results (Step 7)

### Coherence Validation ✅

**Decision Compatibility :** D8-D12 (step 4) sont cohérents avec l'ADR (point d'injection 2-3 / 3-4) et avec les patterns step 5 (naming, error handling). Aucun choix contradictoire — le module `overrides.py` reste isolé, sens unique, pas de dépendance circulaire.

**Pattern Consistency :** Les préfixes `apply_*`/`resolve_*` (step 5) correspondent exactement aux deux fonctions publiques définies en D8. La règle `override_applied`/`override_source` (step 5, format patterns) est directement consommée par D11. La distinction silencieux/warning (step 5, process patterns) répond à l'anomalie possible sur le fichier JSON de D9.

**Structure Alignment :** L'arbre step 6 place `overrides.py` exactement là où D8 l'exige (`resources/daemon/mapping/`), et `ha_overrides.json` là où D9 le résout désormais (`data/`, sibling de `resources/`, convention `disk_cache.py`).

### Requirements Coverage Validation ✅

- FR23 (politiques/exceptions/overrides distincts de la validité structurelle) → D11 (l'override ne bypasse jamais `validate_projection`).
- FR24 (distinguer blocage explicite vs composant invalide) → `reason_details.override_applied/override_source` (D11 + step 5 format).
- FR25 (override avancé sans effacer la décision native) → D10 (`generic_type` jamais muté) + D8 (patch sur copie mémoire).
- FR31/FR40/FR44/FR45 (diagnostic 4D stable, additif, non-régressif) → D12 (tests non-régression golden-file explicites) + process pattern silencieux si absence de fichier.

Couverture complète pour le scope 16a backend (stories 16.0, 16.4 directement ; 16.1-16.3 anticipées par le schéma D9 sans migration).

### Implementation Readiness Validation ✅

- Décisions versionnées et complètes (D8-D12), aucun `TBD` restant — le seul point ouvert (chemin du fichier) est résolu.
- Patterns exhaustifs pour ce scope restreint (naming, structure, format, erreurs) ; catégories hors-scope (DB, routes REST publiques, state front) explicitement écartées en step 5, ce n'est pas un oubli.
- Structure complète et spécifique (arbre step 6, pas de placeholder générique), boundaries clairement posées (overrides↔pipeline, données↔code, generic_type natif).

### Gap Analysis Results

**Gap important — RÉSOLU :** l'emplacement du fichier de persistance (`config/` vs autre) était non confirmé depuis step 4. Vérifié dans le repo : aucun dossier `config/` n'existe dans le daemon ; la seule persistance disque existante (`disk_cache.py` → `jeedom2ha_cache.json`) résout vers `data/` (sibling de `resources/`, calculé via `__file__` + `../..`, cf. `main.py:15,28`, `http_server.py:53-54`). D9 et l'arbre step 6 mis à jour en conséquence.

**Gap mineur — accepté, non bloquant :** performance/scalabilité de la lecture de `ha_overrides.json` à chaque cycle de sync (284 équipements actuellement). Non critique tant que le volume reste de cet ordre ; à surveiller si la volumétrie change significativement (pas d'action architecturale requise maintenant).

**Gap hors-scope identifié post-validation (à traiter dans un delta 16b dédié) :** l'UX design 16b (`ux-design-delta-pe-epic-16-mapping-configurable.md`, steps 1-14 bouclés) suppose un nouvel endpoint HTTP public (GET statuts + POST dry-run par commande) et une fonction d'écriture d'override déclenchée par le dry-run réussi — capacités non couvertes par ce document (qui exclut explicitement tout nouvel endpoint REST public, step 6). Ce gap ne bloque pas la clôture de 16a (scope backend pipeline/persistance uniquement) mais doit être résolu par une architecture delta 16b séparée avant le démarrage des stories 16.5-16.7.

**Correction 2026-07-07 (Sprint Change Proposal, approuvé Alexandre) — source de vérité "attendu HA" :** la "source de vérité pour l'attendu HA par commande" au **runtime** est le registre runtime dérivé (`validation/ha_component_registry.py::HA_COMPONENT_REGISTRY` **+ logique des mappers** `registry.py`/allowlists), conforme au `_meta.note` de `ha-projection-reference.yaml` qui prescrit une **dérivation** vers l'artefact consommé par le daemon, non un chargement direct du YAML de planning. Le YAML `ha-projection-reference.yaml` demeure la source de vérité **documentaire / de planning** (rectification de la ligne "Analyse du contexte projet" qui le désignait comme source runtime sans acter qu'il n'est pas chargé). Décision tranchée par débat ADR 5 personas (4× Option 1). **Frontière 16b :** les labels FR / familles / subtypes du sélecteur d'override viendront de la section `jeedom_generic_types` de ce même YAML via un chargeur/export dédié cadré en 16b (pré-requis bloquant des stories 16.5-16.7 ; anti-régression Homebridge). **Concern séparé (hors epic 16) :** le `ha_component_registry.yaml` "dérivé, consommé par le daemon" prévu par le `_meta.note` n'a jamais été généré ; le daemon maintient un dict Python à la main — dette de gouvernance à cadrer indépendamment. Réf : `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07.md`.

**Correction 2026-07-07 (Sprint Change Proposal Story 16.3, approuvé Alexandre) — schéma de persistance des overrides de publication/exclusion :** le schéma de persistance `data/ha_overrides.json` passe en `schema_version: 2` avec une section **séparée** `equipment_overrides` (clé `eq_id` seule) à côté de `overrides` (clé composite `eq_id:cmd_id`, **inchangée**, D9). Un champ `publication_override: "exclude" | "force_publish"` est ajouté aux deux niveaux. Migration v1→v2 transparente en mémoire (aucune réécriture disque au chemin de lecture ; fichiers déjà en prod, Story 16.1/16.2, se chargent sans action utilisateur). Précédence actée : exclusion équipement (veto absolu) > override commande > force_publish équipement (défaut) > nominal. Nouvelle fonction pure `resolve_publication_override(eq_id, cmd_id, overrides, equipment_overrides) -> Optional[str]` dans `overrides.py`, résolue par l'appelant (`http_server.py`) et passée en paramètre à `decide_publication()` (D8 étendu à ce besoin, `decide_publication.py` reste sans dépendance cache — I7). Reason_codes actés : `publication_excluded_eqlogic` / `publication_excluded_command` / `publication_forced` — préfixe `publication_` distinct de `excluded_eqlogic`/`excluded_plugin`/`excluded_object` (Story 4.3, exclusion native Jeedom étape 1) pour éviter toute confusion diagnostique. Décision tranchée par débat ADR 3 personas (Pipeline/Runtime, Données/Schéma, Produit/UX-Diagnostics ; 2/3 pour cette forme de clé, désaccord résiduel uniquement sur la forme, pas sur le vocabulaire diagnostique). Réf : `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07-16-3-overrides-schema.md`.

### Validation Issues Addressed

Le seul point bloquant identifié pour le scope 16a (chemin du fichier) a été résolu par vérification directe du code plutôt que par supposition — évite un choix arbitraire qui aurait pu diverger de la convention existante du daemon.

### Architecture Completeness Checklist

**✅ Requirements Analysis** — contexte projet, échelle, contraintes (Homebridge non-régression) analysés (step 2).
**✅ Architectural Decisions** — D8-D12 documentées, versionnées, sans ambiguïté résiduelle.
**✅ Implementation Patterns** — naming/structure/format/process actés avec exemples et anti-patterns.
**✅ Project Structure** — arbre complet, boundaries définies, mapping stories→structure exhaustif (16.0-16.7).

### Architecture Readiness Assessment

**Overall Status :** READY FOR IMPLEMENTATION (scope 16a backend uniquement — 16b nécessite un delta d'architecture séparé, cf. gap ci-dessus)

**Confidence Level :** Élevé — scope restreint (backend pur, pas de nouvelle techno), tous les points de friction identifiés en step 5 ont une décision, le seul gap bloquant a été vérifié contre le code réel plutôt que supposé.

**Key Strengths :** ADR à personas multiples ayant tranché le point d'injection le plus risqué (double granularité type vs politique) ; alignement strict avec la convention de persistance déjà existante du daemon (pas de nouveau pattern introduit) ; non-régression Homebridge garantie par construction (D10) et testée explicitement (D12).

**Areas for Future Enhancement :** CRUD complet des overrides (`list_*`/`remove_*`, stories 16.1-16.2) ; suggestions automatiques (`source: "suggested"`, story 16.3) — toutes deux déjà anticipées sans migration de schéma ; architecture du endpoint HTTP + écriture dry-run pour 16b (gap identifié, delta séparé à venir).

### Implementation Handoff

**AI Agent Guidelines :** suivre D8-D12 et les patterns step 5 exactement ; respecter les boundaries step 6 (sens unique `overrides.py`→pipeline, jamais l'inverse).

**First Implementation Priority :** Story 16.0 — créer `resources/daemon/mapping/overrides.py` avec `apply_type_override()` et `resolve_publication_override()`, injection dans `http_server.py` (L.1297/1316 et L.1319), tests `test_story_16_0_overrides_injection.py`.
