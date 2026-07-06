---
stepsCompleted: [1, 2, 4, 5, 6, 7, 8]
inputDocuments:
  - prd.md
  - ux-design-delta-pe-epic-16-mapping-configurable.md
  - architecture-delta-pe-epic-16-mapping-configurable.md
  - _bmad-output/project-context.md
workflowType: 'architecture'
project_name: 'jeedom2ha'
user_name: 'Alexandre'
date: '2026-07-06'
lastStep: 8
status: 'complete'
completedAt: '2026-07-06'
---

# Architecture Decision Document — Delta pe-epic-16b (endpoint HTTP mapping configurable)

_Ce document est un delta additif au cycle actif "Moteur de projection explicable" et au delta 16a (`architecture-delta-pe-epic-16-mapping-configurable.md`, backend pipeline/persistance, clos). Il couvre le gap identifié en step 7 de 16a : le endpoint HTTP (GET statuts + POST dry-run) et l'écriture d'override déclenchée par le dry-run réussi, requis par l'UX design 16b déjà bouclé._

## Documents d'entrée

- PRD : `prd.md` (canonique actif) — FR23, FR24, FR25, FR31, FR40, FR44, FR45
- UX Design : `ux-design-delta-pe-epic-16-mapping-configurable.md` (steps 1-14, complet) — contrat d'interaction : GET initial par équipement, POST dry-run par commande (débounce 300-500ms), auto-validation au succès, race condition gérée côté client
- Architecture amont : `architecture-delta-pe-epic-16-mapping-configurable.md` (16a, `status: complete`) — D8-D12, module `overrides.py` (`apply_type_override`, `resolve_publication_override`), schéma `data/ha_overrides.json`, gap "endpoint public manquant" noté en step 7
- Project context : `_bmad-output/project-context.md`
- Pas de brief/research dédié supplémentaire

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

FR23/FR24/FR25 (contrat de dry-run et diagnostic explicite par commande), FR31 (accordéon et affichage triptyque natif/override/diagnostic), FR40/FR44/FR45 (auto-validation immédiate au succès du dry-run, sans étape "Enregistrer" séparée) imposent un endpoint HTTP inédit : GET (statuts agrégés par équipement, incluant `reason_details`) et POST (dry-run par commande, avec écriture sur `data/ha_overrides.json` en cas de succès).

**Non-Functional Requirements:**

- Latence : debounce client 300-500ms, indicateur de chargement <200ms — impose que le POST reste rapide (un seul appel `validate_projection()` sur copie patchée, pas de re-sync complet).
- Sécurité : le endpoint doit respecter le mécanisme d'authentification déjà en place — bind `127.0.0.1` + header `X-Local-Secret` validé par `_check_secret()` (`http_server.py:63-68`), appliqué systématiquement en tête de chaque handler existant (ex. L.917-921, L.1065-1069, L.1142-1146, L.1208-1212, L.2006-2010, L.2297-2301, L.2327-2331, L.2365-2369, L.2845-2847), sans introduire de nouveau schéma d'auth.
- Cohérence : la responsabilité d'écriture (déclenchée par un dry-run réussi) ne doit pas être portée par `overrides.py` (module de calcul pur, lecture seule en mémoire, D8/16a) — elle doit vivre dans la couche endpoint ou une fonction dédiée qu'elle appelle, pour ne pas coupler le pipeline de sync à de l'I/O disque hors cycle.

**Scale & Complexity:**

- Primaire : ajout d'un endpoint HTTP (2 routes : GET + POST) dans un serveur `aiohttp` existant (`http_server.py`, ~2900 lignes, pattern de routes bien établi).
- Complexité : faible à modérée — pas de nouvelle techno, pas de nouveau schéma d'auth ; l'essentiel du risque porte sur la conception de la fonction d'écriture (nom, signature, emplacement) et la gestion de la race condition/idempotence côté serveur (le client annule déjà les requêtes en vol, mais faut-il une garde serveur ?).
- Domaine technique : API backend Python (aiohttp), consommée par le plugin PHP Jeedom (frontend de la fiche équipement).

### Technical Constraints & Dependencies

- Dépendance amont : 16a (`architecture-delta-pe-epic-16-mapping-configurable.md`, clos) fournit `apply_type_override`/`resolve_publication_override` dans `overrides.py`, le schéma `ha_overrides.json` (D9), et exclut explicitement tout endpoint public de son scope — 16b comble ce gap.
- Contrainte d'authentification : réutiliser strictement `_check_secret()` / `X-Local-Secret` (`http_server.py:63-68`), même pattern que les ~9 autres routes protégées déjà présentes.
- Contrainte de non-régression : le dry-run reste une lecture pure sur une copie patchée de `MappingResult` (jamais d'effet de bord sur le pipeline de sync réel) ; seule l'écriture post-succès touche `ha_overrides.json`.
- Validation d'entrée : les `jeedom_eq_id`/`jeedom_cmd_id` reçus par le POST doivent être vérifiés contre le référentiel équipement existant avant toute écriture, pour éviter des entrées orphelines dans `ha_overrides.json`.
- Contraintes héritées non renégociables : D10 (`generic_type` jamais muté), D9 (schéma `ha_overrides.json`), D8 (`overrides.py` sens unique, pas de dépendance vers les mappers).

### Cross-Cutting Concerns Identified

- Séparation calcul/écriture : `overrides.py` reste pur (lecture seule) ; l'écriture déclenchée par succès de dry-run est portée par l'endpoint (ou une fonction dédiée qu'il appelle) — architecture à trancher précisément dans les steps suivants (nom/signature/emplacement de la fonction d'écriture).
- Idempotence/race condition : le client annule les requêtes en vol sur nouvelle édition, mais la nécessité d'une garde serveur (ex. version/timestamp check avant écriture) reste à décider.
- Réutilisation du pattern d'auth existant plutôt que réinvention — évite tout risque de divergence de sécurité entre routes.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

D13 (routes HTTP), D14 (emplacement fonction d'écriture)

**Important Decisions (Shape Architecture):**

D15 (pas de garde serveur pour la race condition)

**Deferred Decisions (Post-MVP):**

Aucune — scope 16b entièrement tranché.

### Data Architecture

**D14 — Écriture de l'override après dry-run réussi**

Nouvelle fonction `save_override(eq_id, cmd_id, ha_entity_type) -> None` dans `overrides.py`, distincte de `apply_*`/`resolve_*` (calcul mémoire, D8/16a) et de `list_*`/`remove_*` (CRUD futur, stories 16.1-16.2). Convention de préfixe : `save_*` = écriture disque déclenchée par un événement externe (ici, succès du dry-run HTTP). `overrides.py` reste donc le point d'entrée unique pour toutes les opérations sur `ha_overrides.json` (lecture ET écriture), mais chaque catégorie d'opération a son propre préfixe de nommage — pas de couplage caché avec le pipeline de sync (`save_override` n'est jamais appelée par `map()`/`validate_projection()`/`decide_publication()`/`publish()`, uniquement par le handler HTTP `/action/mapping_dry_run`).

### Authentication & Security

Réutilisation stricte du mécanisme existant : bind `127.0.0.1` + header `X-Local-Secret` validé par `_check_secret()` (`http_server.py:63-68`), même garde en tête des deux nouveaux handlers, cohérent avec les ~9 routes déjà protégées. Aucun nouveau schéma d'auth introduit.

Validation d'entrée : `jeedom_eq_id`/`jeedom_cmd_id` vérifiés contre le référentiel équipement existant avant tout appel à `save_override()`, pour prévenir les entrées orphelines dans `ha_overrides.json`.

### API & Communication Patterns

**D13 — Routes HTTP** (cohérentes avec les conventions existantes `/system/*` lecture, `/action/*` action) :

- `GET /system/mapping_overrides/{jeedom_eq_id}` → statuts de toutes les commandes de l'équipement (incluant `reason_details`)
- `POST /action/mapping_dry_run` → body `{jeedom_eq_id, jeedom_cmd_id, ha_entity_type}` → `validate_projection()` sur copie patchée du `MappingResult` ; si succès, appel à `save_override()` ; réponse contient le diagnostic (reason_details) + statut de l'écriture

**D15 — Pas de garde serveur pour la race condition**

Le client annule les requêtes en vol (comportement UX déjà spécifié) ; contexte mono-utilisateur/LAN local, volume de requêtes trivial → pas de mécanisme d'idempotence/séquencement serveur. Décision explicitement documentée comme acceptée pour ne pas sur-ingénierer un cas limite à faible probabilité/impact ; à revisiter si le contexte d'usage change (multi-utilisateur concurrent, par exemple).

### Decision Impact Analysis

**Implementation Sequence:**

1. `save_override()` dans `overrides.py` (dépend de D9/16a — schéma `ha_overrides.json` déjà défini)
2. Handler `GET /system/mapping_overrides/{jeedom_eq_id}` (dépend de `resolve_publication_override()`/16a)
3. Handler `POST /action/mapping_dry_run` (dépend des deux précédents + `validate_projection()` du pipeline canonique)

**Cross-Component Dependencies:**

`http_server.py` devient dépendant de `overrides.py::save_override()` (nouvelle relation, sens unique daemon HTTP → module override, jamais l'inverse — cohérent avec D8/16a). Aucun impact sur le pipeline de sync `assess_all→map→validate_projection→decide_publication→publish`.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 4 zones où deux agents IA pourraient diverger — format de réponse, distinction diagnostic/erreur HTTP, nommage JSON, logging des écritures.

### API Response Formats

Les 2 nouvelles routes réutilisent le schéma déjà en place dans `http_server.py` : `{"status": "ok"|"error", ...}`, avec `message` en cas d'erreur. Aucun nouveau format introduit.

- `GET /system/mapping_overrides/{jeedom_eq_id}` → `{"status": "ok", "commands": [{"jeedom_cmd_id": ..., "reason_details": {...}, "override_applied": bool, "override_source": "..."}]}`. Conformément à D11/16a, `override_source` est **omis** (jamais renvoyé comme `null`) lorsque `override_applied: false`.
- `POST /action/mapping_dry_run` → `{"status": "ok", "dry_run_result": {...reason_details...}, "override_saved": bool}` en cas de dry-run traité (succès OU échec métier) ; `{"status": "error", "message": "..."}` uniquement pour une vraie erreur serveur/auth/validation d'ID. `dry_run_result` est un **sous-ensemble contrôlé** du diagnostic — uniquement `reason_details`, `override_applied`, `override_saved` — jamais une sérialisation brute/complète de l'objet interne `MappingResult`, pour ne pas exposer de détails d'implémentation via l'API publique.

### Error Handling Patterns

**Distinction stricte diagnostic-métier vs erreur HTTP :**
- Un dry-run refusé par `validate_projection()` (ex. type incompatible) → HTTP 200, `status: "ok"`, diagnostic dans `dry_run_result.reason_details`. Ce n'est jamais une erreur HTTP.
- Auth invalide → HTTP 401 (comme les routes existantes via `_check_secret()`).
- `jeedom_eq_id`/`jeedom_cmd_id` inconnu du référentiel → HTTP 404, `{"status": "error", "message": "Unknown equipment or command"}`.
- Exception inattendue → HTTP 500, message générique (jamais de stacktrace exposée au client).

### Naming Patterns (JSON)

`snake_case` strict pour tous les champs des 2 nouvelles routes, cohérent avec le reste de l'API existante (`jeedom_eq_id`, `jeedom_cmd_id`, `reason_details`, `override_applied`, `override_source` — champs déjà nommés en D11/16a).

### Process Patterns

**Logging :** chaque écriture réussie via `save_override()` doit être loguée en `INFO` (équipement, commande, type choisi), au même niveau que les autres mutations d'état du daemon (cohérence avec les logs existants de `disk_cache.py`/sync).

### Enforcement Guidelines

**All AI Agents MUST:**
- Ne jamais renvoyer un code HTTP ≥400 pour un dry-run métier échoué — seulement pour une vraie erreur technique/auth/validation.
- Utiliser `snake_case` pour tous les champs JSON des 2 nouvelles routes.
- Valider `jeedom_eq_id`/`jeedom_cmd_id` contre le référentiel équipement AVANT d'appeler `save_override()`.
- Ne jamais appeler `save_override()` depuis le pipeline de sync (`map`/`validate_projection`/`decide_publication`/`publish`) — uniquement depuis le handler HTTP.

### Pattern Examples

**Bon exemple :** dry-run refusé → `200 {"status": "ok", "dry_run_result": {"override_applied": false}, "override_saved": false}`
**Anti-pattern :** dry-run refusé → `400 {"error": "validation failed"}` (confond diagnostic métier et erreur HTTP, casse le contrat UX qui attend un affichage "diagnostic" pas une erreur réseau).

## Project Structure & Boundaries

### Fichiers Impactés (Delta additif, aucune nouvelle arborescence)

- `resources/daemon/transport/http_server.py` — ajout de 2 handlers (`GET /system/mapping_overrides/{jeedom_eq_id}`, `POST /action/mapping_dry_run`) et de leur enregistrement via `app.router.add_get`/`add_post` (pattern existant, L.2900-2910)
- `resources/daemon/mapping/overrides.py` — ajout de `save_override(eq_id, cmd_id, ha_entity_type) -> None` (D14)
- Tests associés : emplacement et convention de nommage hérités de D12/16a, pas de nouvelle structure de test

### Frontière d'Intégration

Sens unique `http_server.py → overrides.py` (D8/16a, confirmé D14) : le module `overrides.py` reste un module de calcul/persistance pur, jamais consommateur de `http_server.py`. Aucune autre frontière de composant n'est introduite par ce delta.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** D13/D14/D15 cohérentes entre elles et avec D8-D12/16a ; aucune contradiction, aucun nouveau schéma d'auth ou de format introduit.

**Pattern Consistency:** Patterns du step 5 dérivés des conventions réelles du code (`_check_secret()`, format `{"status": ...}`), pas de divergence.

**Structure Alignment:** Structure minimale (step 6) suffisante pour porter D13/D14 ; frontière `http_server.py → overrides.py` respectée.

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:** FR23/24/25 (dry-run + diagnostic) → D13/POST + Error Handling Patterns. FR31 (triptyque UI) → D13/GET. FR40/44/45 (auto-validation) → D13 + D14 (`save_override` sur succès, sans étape "Enregistrer").

**Non-Functional Requirements Coverage:** Latence (debounce client, appel unique `validate_projection()`) → D13. Sécurité (réutilisation stricte de l'auth existante) → D13/Authentication & Security. Cohérence (séparation calcul/écriture) → D14.

### Implementation Readiness Validation ✅

Décisions, patterns et structure documentés de façon suffisamment précise pour une implémentation cohérente par un agent IA en dev-story, sans ambiguïté sur le format de réponse, la gestion d'erreur, ou l'emplacement du code.

### Gap Analysis Results

Aucun gap critique ni important. Point mineur (non bloquant) : vérifier en tests que le message d'erreur 404 reste générique (`"Unknown equipment or command"`) sans distinguer eq_id/cmd_id invalide (déjà cadré en step 5).

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION
**Confidence Level:** high — scope étroit, conventions existantes réutilisées, aucune décision en suspens.

### Implementation Handoff

**AI Agent Guidelines:** Suivre D13/D14/D15 et les patterns du step 5 sans déviation ; ne jamais introduire de nouveau format de réponse ou schéma d'auth.

**First Implementation Priority:** `save_override()` dans `overrides.py`, puis le handler GET, puis le handler POST (ordre de dépendance déjà établi en step 4).
