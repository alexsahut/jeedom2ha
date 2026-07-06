# Story 16.0: Préfixe d'architecture — contrat d'override double granularité, points d'injection et limites

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a mainteneur,
I want formaliser les types d'overrides autorisés (dont la distinction override Jeedom vs override HA local), leurs points d'injection dans le pipeline et leurs limites,
so that la configuration utilisateur ne casse ni la validation HA, ni le diagnostic, ni une configuration Homebridge existante.

## Acceptance Criteria

1. **Given** le pipeline canonique à 5 étapes (`assess_all` → `map()` → `validate_projection()` → `decide_publication()` → `publish()`), **when** la story est exécutée, **then** les types d'overrides autorisés sont listés et bornés : override de type/capabilities HA (éligibilité + candidat mapping), override de politique de publication (décision), champ `source`/traçabilité (métadata).
2. Un override HA local est explicitement distingué d'une modification du `generic_type` Jeedom natif — cette dernière reste hors scope et interdite (non-régression Homebridge, D10).
3. L'interdiction de publier une projection structurellement invalide est documentée comme invariant bloquant : un override ne bypasse jamais un échec de `validate_projection()` (D11).
4. **Given** un override de mapping ou de décision, **when** son point d'injection est décrit, **then** le document d'architecture précise l'ordre d'application par rapport au mapping automatique, à `validate_projection()` et à `decide_publication()` (ADR "point d'injection", D6/D7/D8).
5. Le format du schéma JSON v1 (`data/ha_overrides.json`, `schema_version: 1`, clé composite `jeedom_eq_id:jeedom_cmd_id`) est tranché — décisions ultérieures de granularité fine (ex. propositions automatiques `source: "suggested"`) renvoyées explicitement à Story 16.1+ sans rupture de schéma.

## Tasks / Subtasks

- [x] Task 1 — Consolider le contrat d'override en un document de référence unique (AC: 1, 2, 3, 4, 5)
  - [x] Subtask 1.1 : Vérifié que `architecture-delta-pe-epic-16-mapping-configurable.md` (D6-D12) et `architecture-delta-pe-epic-16b-mapping-configurable-endpoint.md` (D13-D15) couvrent intégralement les 5 AC ci-dessus — les deux documents sont `status: complete`.
  - [x] Subtask 1.2 : Aucun gap identifié entre les AC et les deltas existants — pas de nouvelle ADR nécessaire.
  - [x] Subtask 1.3 : Ajouté dans `architecture.md` (canonique) une section "Overrides — Contrat de Référence (Epic 16)" qui pointe vers les deux deltas comme source de vérité et rappelle les invariants non négociables (gates epic-level pe-epic-16).
- [x] Task 2 — Poser le squelette de non-régression du contrat (AC: 2, 3)
  - [x] Subtask 2.1 : Créé `resources/daemon/tests/unit/test_story_16_0_overrides_injection.py` avec un test d'assertion que `generic_type` (`JeedomCmd`/`JeedomEqLogic`) n'est jamais muté par le pipeline de mapping (`SwitchMapper().map()`) — baseline de non-régression pour D10, à étendre en Story 16.1 avec `overrides.py`.
  - [x] Subtask 2.2 : Ajouté un second test documentant l'invariant D11 via `validate_projection()` (`validation/ha_component_registry.py`) : un `ha_entity_type` incompatible/inconnu reste `is_valid=False`, jamais bypassé.
- [x] Task 3 — Mettre à jour le tracking (AC: tous)
  - [x] Subtask 3.1 : `sprint-status.yaml` — `pe-epic-16` passé de `backlog` à `in-progress` (create-story), puis story `16-0-prefixe-architecture-contrat-override` suivie `ready-for-dev` → `in-progress` → `review`.
  - [x] Subtask 3.2 : `Dev Agent Record > Completion Notes List` renseigné ci-dessous avec le détail des workflows BMAD exécutés.

## Dev Notes

- Cette story est un **préfixe architectural obligatoire** (gate epic-level pe-epic-16) — elle ne doit débloquer aucune implémentation d'override tant que le contrat n'est pas explicitement consolidé et référencé. Elle ne modifie pas le comportement runtime du daemon.
- Le contrat qu'elle formalise a déjà été largement tranché durant la session d'architecture BMAD du 2026-07-06 (deltas 16a et 16b, tous deux `status: complete`) — le travail de cette story est donc principalement un travail de **consolidation et de référencement**, pas de nouvelle décision architecturale. Ne pas rouvrir de débat sur des décisions déjà actées (D6-D15) sans ADR explicite.
- `sprint-change-proposal-2026-07-06-mapping-configurable.md` documente le cadrage initial de l'epic 16 (reprise de l'ancien epic 12) — à citer en contexte, ne pas y chercher de contrat technique (c'est un document de cadrage produit, pas d'architecture).
- Aucune story terrain : pas de daemon à redémarrer, pas de box réelle, pas de MQTT — travail purement documentaire/architectural + squelette de test.

### Contrat d'override — résumé technique (source : deltas 16a/16b)

**Types d'overrides autorisés et bornés :**
1. Override de type/capabilities HA (mapping candidat) — injecté **entre l'étape 2 (`map()`) et l'étape 3 (`validate_projection()`)**, patch d'une **copie** du `MappingResult`, jamais du modèle source `JeedomCmd`/`JeedomEqLogic` (D6/D8/D10).
2. Override de politique de publication (décision) — injecté **entre l'étape 3 et l'étape 4 (`decide_publication()`)**, en paramètre additionnel (extension de `confidence_policy` existant), jamais de retour en arrière vers `validate_projection()` (D7).
3. Métadata/traçabilité — `reason_details.override_applied` (bool) + `reason_details.override_source` (string) : paire indissociable, `override_source` **absent** (jamais nullé) si `override_applied: false` (D11).

**Limite bloquante (invariant non négociable) :** un override référençant un `ha_entity_type` incompatible avec les capabilities détectées reste soumis à `validate_projection()` — celle-ci peut renvoyer `is_valid=False`, l'override ne bypasse jamais un échec de validation structurelle (D11). Aucune projection invalide n'est jamais publiée, override ou non.

**`generic_type` Jeedom natif :** jamais modifié par un override HA (D10) — le patch vit uniquement sur la copie mémoire `MappingResult`. Non-régression Homebridge garantie par construction (pas de test manuel requis à ce stade, mais assertion explicite requise en Task 2).

**Schéma de persistance v1 (D9) :** fichier `data/ha_overrides.json`, `schema_version: 1`, entrée indexée par `f"{jeedom_eq_id}:{jeedom_cmd_id}"` (jamais par nom), champ `source: "user"` dès le départ (anticipe `source: "suggested"` en Story 16.3 sans migration de schéma).

**Endpoint HTTP (16b, D13-D15) :** `GET /system/mapping_overrides/{jeedom_eq_id}` (statuts agrégés) et `POST /action/mapping_dry_run` (dry-run + écriture sur succès via `save_override()`) — réutilisent strictement `_check_secret()`/`X-Local-Secret` existant, aucun nouveau schéma d'auth. `save_override()` n'est jamais appelée par le pipeline de sync (`map`/`validate_projection`/`decide_publication`/`publish`), uniquement par le handler HTTP.

### Dev Agent Guardrails

- Ne pas créer `resources/daemon/mapping/overrides.py` dans cette story — c'est le scope de Story 16.1 (persistance backend). Cette story ne fait que poser le contrat et un test-squelette.
- Ne pas introduire de nouvelle route HTTP dans cette story — c'est le scope différé de la partie endpoint (16b/Story 16.6), déjà architecturée mais pas encore implémentée.
- Respecter les préfixes de fonction déjà actés pour tout futur code du module `overrides.py` : `apply_*` (patch copie mémoire), `resolve_*` (lecture décision), `list_*`/`remove_*` (CRUD futur), `save_*` (écriture disque déclenchée par événement externe) — ne pas inventer de nouveau préfixe.

### Project Structure Notes

- Aucun nouveau fichier de code de production dans cette story. Fichiers concernés : `architecture.md` (section de référence ajoutée), `resources/daemon/tests/unit/test_story_16_0_overrides_injection.py` (nouveau, squelette de contrat), `_bmad-output/implementation-artifacts/sprint-status.yaml` (mise à jour tracking).
- Aucune variance détectée par rapport à la structure projet existante — `resources/daemon/tests/` est déjà le répertoire de tests conventionnel du daemon.

### References

- [Source: architecture-delta-pe-epic-16-mapping-configurable.md#ADR — Point d'injection de l'override] (D6-D8, D10-D12)
- [Source: architecture-delta-pe-epic-16-mapping-configurable.md#Core Architectural Decisions (Step 4 — scope 16a backend)] (D9)
- [Source: architecture-delta-pe-epic-16b-mapping-configurable-endpoint.md#Core Architectural Decisions] (D13-D15)
- [Source: epics-projection-engine.md#Story 16.0 : Préfixe d'architecture — contrat d'override double granularité, points d'injection et limites]
- [Source: epics-projection-engine.md#Gates epic-level pe-epic-16]
- [Source: sprint-change-proposal-2026-07-06-mapping-configurable.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (Claude Code)

### Debug Log References

- Suite complète daemon : `python3 -m pytest -q` → 970 passed, aucune régression.
- Tests ciblés story : `python3 -m pytest tests/unit/test_story_16_0_overrides_injection.py -v` → 2 passed.

### Completion Notes List

- create-story exécuté le 2026-07-06 pour Story 16.0 (epic pe-epic-16), suite au cadrage clarifié avec l'utilisateur (16.0 = préfixe architectural obligatoire, distinct des labels informels "16a"/"16b" utilisés pour les deux documents d'architecture delta). Statut résultant : `ready-for-dev`.
- dev-story exécuté le 2026-07-06 : cette story étant un préfixe architectural (pas de nouveau code de production), l'implémentation a consisté à (1) consolider le contrat d'override dans `architecture.md` par référence explicite aux deux deltas `status: complete`, (2) figer les invariants D10/D11 sous forme de tests exécutables (baseline de non-régression pour Story 16.1+), (3) aligner le tracking. Aucun gap trouvé entre les AC de la story et les décisions déjà actées en architecture — pas de nouvelle ADR nécessaire. Statut résultant : `review`.
- code-review (adversarial) exécuté le 2026-07-06 : 5/5 AC validés, 3/3 tâches réelles, 2 tests rejoués PASS (symboles/signatures vérifiés dans le code source). Issues : 0 High, 1 Medium, 3 Low — toutes corrigées. Correctifs appliqués : (1) [Medium] deltas d'architecture source-de-vérité (`architecture-delta-pe-epic-16*.md`, `ux-design-delta-*.md`) mis sous suivi git pour ne plus référencer des fichiers absents du contrôle de version ; (2) [Low] typo de chemin de test corrigée dans « Project Structure Notes » (`tests/` → `tests/unit/`) ; (3) [Low] règles `__pycache__/` + `*.pyc` ajoutées au `.gitignore` (hygiène). Le [Low] restant (couverture D10 limitée à `SwitchMapper`) est une baseline assumée à élargir en Story 16.1, laissée telle quelle. Statut résultant : `done`.

### File List

- `_bmad-output/planning-artifacts/architecture.md` (modifié — section "Overrides — Contrat de Référence (Epic 16)" ajoutée)
- `resources/daemon/tests/unit/test_story_16_0_overrides_injection.py` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié — tracking epic/story)
- `.gitignore` (modifié — règles `__pycache__/` + `*.pyc` ajoutées lors du code-review)
