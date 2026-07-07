# Story 16.3: Overrides de publication et exclusion explicite

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un utilisateur expert,
I want exclure un équipement ou une commande, ou autoriser une publication dont la projection est valide mais bloquée par une politique produit,
so that je reprends la main sans confondre ce choix avec une réussite automatique du moteur.

## Acceptance Criteria

**AC1 — Exclusion explicite (équipement ou commande)**

**Given** un équipement ou une commande exclu par override utilisateur
**When** le pipeline évalue la décision de publication (étape 4)
**Then** l'exclusion est prioritaire, lisible et réversible
**And** le diagnostic signale explicitement l'origine utilisateur de l'exclusion

**AC2 — Forcer une publication bloquée par la politique produit**

**Given** un équipement dont la projection HA est valide (`projection_validity.is_valid == true`) mais dont la confiance est faible (`confidence_policy=sure_only` bloque un mapping `probable`) ou dont la publication est bloquée par une autre politique produit
**When** un override utilisateur autorise la publication
**Then** `projection_validity.is_valid == true` reste une condition **obligatoire** — un override ne réécrit jamais une projection invalide (I2, aucun bypass)
**And** la décision finale (`PublicationDecision`) indique explicitement qu'elle vient d'un override, sans masquer la décision native sous-jacente

## Tasks / Subtasks

<!-- Story terrain : daemon / pipeline decide_publication / publish → Task 0 Pre-flight terrain injectée. -->

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run` — **OK 2026-07-07 (SSH OK | sudo OK, box 192.168.1.21 joignable)**
  - [ ] Sélectionner le mode selon l'objectif de la story : cycle complet republication `--cleanup-discovery --restart-daemon` — **différé : validation terrain à confirmer avec Alexandre avant cycle disruptif sur box live (même précaution que Story 16.2)**
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.` — dry-run terminé `Simulation complete`

- [x] Task 1 — Faire évoluer le schéma de persistance (TRANCHÉ — SCP 2026-07-07, Option 1, ADR multi-persona 3 sous-agents)
  - [x] Bumper `schema_version` à `2` dans `overrides.py`/`data/ha_overrides.json`. `_load_raw` accepte désormais `schema_version ∈ {1, 2}` (int strict) ; toute autre valeur reste un refus explicite loggé (D9 inchangé dans son principe). Un fichier v1 existant (déjà en prod, Story 16.1/16.2) se charge sans action utilisateur : migration transparente en mémoire (`equipment_overrides` défaut `{}`), réécriture disque différée au prochain `save_override`/`save_equipment_override` — jamais de réécriture depuis un chemin de lecture pure.
  - [x] Ajouter une section **séparée** `equipment_overrides` (clé `eq_id` seule, PAS de mélange de formats de clés dans le dict `overrides` existant — écarté pour fragilité de parsing, cf. SCP). La clé composite `eq_id:cmd_id` de `overrides` reste strictement inchangée (`_override_key()` n'est PAS modifiée).
  - [x] Ajouter le champ `publication_override: "exclude" | "force_publish" | null` aux deux niveaux : sur les entrées existantes de `overrides` (à côté de `ha_entity_type`, jamais fusionné) et sur les entrées de `equipment_overrides` (qui ne porte que `publication_override`, pas de `ha_entity_type` — n'a de sens qu'au niveau commande).
  - [x] Nouvelles fonctions CRUD additives (signatures existantes non touchées) : `list_equipment_overrides(data_dir)`, `save_equipment_override(eq_id, override, data_dir)`, `remove_equipment_override(eq_id, data_dir)`.
  - [x] Référence complète de la décision : `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07-16-3-overrides-schema.md`.

- [x] Task 2 — `resolve_publication_override(eq_id, cmd_id, overrides, equipment_overrides) -> Optional[str]` dans `overrides.py` (AC1/AC2, D8)
  - [x] Fonction **pure** (préfixe `resolve_*`, jamais `apply_*` — ne mute aucun objet pipeline, aucune I/O — reçoit les dicts déjà chargés), cohérente avec `resolve_expected_ha()` (Story 16.2, `registry.py`) pour le style de nommage, mais reste dans `overrides.py` (pas de dépendance mapper, D8 respecté par construction).
  - [x] Retourne `None` si aucun override de publication n'est présent pour l'équipement/la commande (comportement silencieux, non-régression — même contrat que `list_overrides`/`apply_type_override`).
  - [x] Implémente la règle de précédence tranchée par le SCP : (1) `equipment_overrides[eq_id].publication_override == "exclude"` → veto absolu, retour immédiat ; (2) sinon override de **commande** (`overrides[eq_id:cmd_id]`) le plus spécifique ; (3) sinon `force_publish` équipement en défaut ; (4) sinon `None`. **Déviation documentée** : le retour disambigue l'origine (`"exclude_eqlogic"` / `"exclude_command"` / `"force_publish"`) plutôt que le littéral brut `"exclude"`/`"force_publish"`, pour permettre à `decide_publication()` de choisir le bon `reason_code` (Task 4) sans dupliquer la logique de précédence côté appelant.
  - [x] Aucune dépendance vers les mappers concrets ni vers `models/topology.py` (sens unique D8, non-mutation D10 — mêmes garanties que `apply_type_override`).

- [x] Task 3 — Injection dans `decide_publication()` entre étape 3 et étape 4 (AC1/AC2, ADR architecture-delta-pe-epic-16 + SCP 2026-07-07)
  - [x] Étendre `decide_publication()` (`resources/daemon/models/decide_publication.py`, actuellement `decide_publication(mapping, confidence_policy="sure_probable", product_scope=None)`) avec un paramètre additionnel optionnel `publication_override: Optional[str] = None` (valeurs `"exclude"` / `"force_publish"`), **extension de la signature existante** — jamais un nouveau chemin parallèle.
  - [x] `publication_override` est **résolu par l'appelant** (`http_server.py`, via `resolve_publication_override(...)`) **avant** l'appel — `decide_publication.py` reste une fonction de décision pure, sans dépendance au cache `overrides_cache`/`equipment_overrides_cache` (cohérent avec I7, aucune logique MQTT/broker/cache introduite dans ce module).
  - [x] **Exclusion (AC1)** : si `publication_override == "exclude"`, retourner `PublicationDecision(should_publish=False, reason="publication_excluded_eqlogic"` ou `"publication_excluded_command"` selon l'origine résolue`)` **avant** l'évaluation des niveaux 3/4 existants (PRODUCT_SCOPE, confidence_policy) — mais reste **après** les niveaux 1/2 (mapping réussi, projection valide) : ne jamais réintroduire I2 (`is_valid=False` → jamais publié) sur ce chemin.
  - [x] **Forcer publication (AC2)** : si `publication_override == "force_publish"` ET que le niveau 2 (`pv.is_valid is True`) est déjà satisfait, retourner `should_publish=True, reason="publication_forced"` (jamais `"sure"`/`"probable"` tel quel — cf. Task 4) en ignorant uniquement le blocage du niveau 4b (`confidence_policy`) — jamais le niveau 2 (I2 non négociable, aucun bypass possible même avec un override).
  - [x] Câbler l'appel dans `transport/http_server.py` : chemin primaire (actuellement `decide_publication(mapping, confidence_policy=confidence_policy)`, L.1344) et chemin secondaire multi-sensor `_publish_additional_sensors()` (actuellement `decide_publication(secondary, confidence_policy=confidence_policy)`, L.223) — résoudre `publication_override` via `resolve_publication_override(eq_id, cmd_id, overrides_cache, equipment_overrides_cache)` juste avant chaque appel, en réutilisant `overrides_cache` déjà chargé (L.1307) et un nouveau `equipment_overrides_cache = list_equipment_overrides(_DATA_DIR)` chargé au même endroit (une seule fois par cycle de sync, pas de second cache par équipement).
  - [x] Ne jamais court-circuiter le flux canonique `map → validate_projection → decide_publication → publish` (invariant D7) : l'override intervient **dans** `decide_publication`, pas en dérivation du pipeline.

- [x] Task 4 — Diagnostic : signaler explicitement l'origine override (AC1/AC2, TRANCHÉ — SCP 2026-07-07)
  - [x] `PublicationDecision.reason` distingue les cas override des cas natifs avec des reason_codes **dédiés et actés** : `"publication_excluded_eqlogic"` (exclusion niveau équipement), `"publication_excluded_command"` (exclusion niveau commande), `"publication_forced"` (AC2). Préfixe `publication_` volontaire — distinct de `excluded_eqlogic`/`excluded_plugin`/`excluded_object` (Story 4.3) tout en restant de la même famille lexicale (I6, lisibilité humaine).
  - [x] `force_publish` ne réécrit **jamais** le `reason` "nominal" existant (`"sure"`/`"probable"`) — la vraie confiance sous-jacente reste tracée dans `reason_details.underlying_confidence`, à côté de `reason_details.publication_override_applied: True` + `reason_details.override_source` (paire indissociable, même principe que `override_applied`/`override_source` posé en Story 16.2, jamais l'un sans l'autre). **Déviation tranchée en dev-story** : ces champs vivent dans un **nouveau champ dédié `PublicationDecision.reason_details: Optional[Dict[str, object]]`** (`models/mapping.py`), distinct de `MappingResult.reason_details` (qui décrit le mapping/la projection, étapes 2-3) — évite de mélanger deux diagnostics de nature différente sur le même objet, et perturbe le moins la structure existante (aucun champ `PublicationDecision` retiré/renommé).
  - [x] **Distinction à ne pas confondre** : Story 4.3 a déjà une notion d'"exclusion" (`JeedomEqLogic.is_excluded` / `exclusion_source`, évaluée à l'étape 1 `assess_eligibility`, cf. `tests/unit/test_exclusion_filtering.py`) — c'est une exclusion **native Jeedom**, en amont du pipeline. L'exclusion de cette story (16.3) est un override **utilisateur**, évalué à l'étape 4 (`decide_publication`), sur un équipement déjà éligible et mappé. Les reason_codes `publication_excluded_*` (16.3) ne partagent aucun préfixe avec `excluded_*` (4.3) — risque de confusion diagnostique tranché par construction.

- [x] Task 5 — Garde-fou I2 : aucun bypass de la validation HA (AC2, D11)
  - [x] Test explicite : un override "forcer publication" appliqué à un équipement dont `projection_validity.is_valid == False` (ex. `has_command` manquant, `ha_component_unknown`) doit **rester non publié** — l'override ne doit jamais pouvoir transformer une projection invalide en publication.
  - [x] Test explicite : un override "forcer publication" appliqué à un équipement `is_valid == True` mais bloqué uniquement par `confidence_policy="sure_only"` (mapping `probable`) doit bien passer en `should_publish=True`, avec la cause explicitement marquée comme override.

- [x] Task 6 — Tests (AC1-2, non-régression)
  - [x] Créer `resources/daemon/tests/unit/test_story_16_3_publication_override.py` (préfixe `test_story_16_3_*`, cf. convention Story 16.2) : exclusion équipement, exclusion commande (selon la granularité tranchée en Task 1), forçage publication sur projection valide bloquée par policy, non-bypass sur projection invalide (Task 5), absence d'override = comportement identique à l'existant (non-régression). 26 tests créés.
  - [x] Vérifier que `test_step4_decide_publication.py` et `test_exclusion_filtering.py` restent verts sans modification (nouveau paramètre optionnel, callers existants non affectés). **Déviation documentée** : 2 tests pré-existants dans `test_story_16_0_overrides_injection.py` (hors périmètre listé ici, mais impactés collatéralement par le bump `schema_version` v1→v2) ont dû être ajustés — voir Change Log.
  - [x] Non-régression golden-file (`tests/fixtures/golden_corpus/expected_sync_snapshot.json`, `test_story_8_4_golden_file.py`) : aucun override actif dans le corpus → snapshot inchangé.
  - [x] Lancer la suite daemon complète (`pytest tests/unit -q`) et confirmer 0 régression vs. baseline actuelle (998 passed après Story 16.2). **Résultat : 1024 passed** (998 baseline + 26 nouveaux tests), 0 échec.

## Dev Notes

### Contexte pipeline (source de vérité : `architecture-delta-pe-epic-16-mapping-configurable.md`)

- Pipeline canonique 5 étapes (D1/D7) : `assess_all (éligibilité) → map (2) → validate_projection (3) → decide_publication (4) → publish (5)`. Jamais de court-circuit.
- **Point d'injection override de publication** : ADR persona B (`architecture-delta-pe-epic-16-mapping-configurable.md#ADR`) — distinct du point d'injection de Story 16.2 (override de *type*, entre étape 2-3). Cette story (16.3) est l'override de *politique de publication*, entre étape 3 et étape 4, en paramètre additionnel de `decide_publication()` (extension de `confidence_policy` existant) — **jamais** une réévaluation de `validate_projection()`.
- **D8** (architecture) : `overrides.py` doit exposer `resolve_publication_override(eq_id, cmd_id, overrides, equipment_overrides) -> Optional[str]`, résolue par l'appelant (`http_server.py`) et passée à `decide_publication()`. Cette fonction reste à créer (absente après Story 16.1/16.2, qui n'ont livré que `apply_type_override`/`resolve_expected_ha`).
- **I2 (invariant `decide_publication`, non négociable)** : `projection_validity.is_valid == False` → `should_publish=False` garanti, quel que soit l'override. Correspond exactement à AC2 : "`projection_validity.is_valid == true` reste une condition obligatoire".
- **I4 (règle de cause canonique)** : le premier échec dans l'ordre des étapes (1→2→3→4) est la cause retenue ; une étape aval ne peut pas écraser une cause amont. L'exclusion utilisateur (AC1) et le forçage (AC2) sont des décisions de **niveau 4** (ou une nouvelle sous-étape 4c) — ils ne doivent jamais masquer un échec amont (niveaux 1-3).

### État factuel du code (relevé 2026-07-07)

- `models/decide_publication.py` (93 l.) : fonction pure `decide_publication(mapping, confidence_policy="sure_probable", product_scope=None) -> PublicationDecision` (L.46). 5 niveaux d'évaluation explicites (L.66-92) : confiance mapping (L.67), projection_validity (L.72), PRODUCT_SCOPE (L.82), confidence_policy (L.88), nominal (L.92). **Aucun paramètre d'override existant.**
- `models/mapping.py` : `PublicationDecision` (L.175-186) — champs `should_publish: bool`, `reason: str`, `mapping_result`, `state_topic`, `active_or_alive`, `discovery_published`, `bridge_availability_topic`, `eqlogic_availability_topic`, `local_availability_supported`, `local_availability_state`, `availability_reason`. **Pas de champ `override_*`** sur `PublicationDecision` — à ajouter ou réutiliser `mapping.reason_details` (trancher en dev-story).
- `mapping/overrides.py` (246 l.) après Story 16.2 : `_overrides_path` (L.39), `_override_key` (L.43, format `f"{eq_id}:{cmd_id}"`, **inchangée par cette story**), `_load_raw` (L.47), `list_overrides` (L.87), `save_override` (L.99), `_mapping_cmd_ids` (L.135), `apply_type_override` (L.154, avec paramètre `overrides=` optionnel depuis code-review), `remove_override` (L.217). **`resolve_publication_override`, `list_equipment_overrides`, `save_equipment_override`, `remove_equipment_override` ABSENTS** → à créer (Task 1/2, schéma v2 tranché par SCP).
- `transport/http_server.py` : `overrides_cache = list_overrides(_DATA_DIR)` chargé une seule fois par cycle de sync (L.1307, Story 16.2 code-review) — **réutilisable telle quelle** pour cette story (même fichier `ha_overrides.json`, pas de second cache à créer). Boucle sync primaire : `decide_publication(mapping, confidence_policy=confidence_policy)` (L.1344). Chemin secondaire multi-sensor : `_publish_additional_sensors()` (L.189-262), `decide_publication(secondary, confidence_policy=confidence_policy)` (L.223).
- **Story 4.3 — mécanisme d'exclusion PRÉEXISTANT, à ne pas confondre** : `JeedomEqLogic.is_excluded`/`exclusion_source` (`models/topology.py`), évalué à l'étape 1 (`assess_eligibility`), 3 `reason_code` dédiés (`excluded_eqlogic`/`excluded_plugin`/`excluded_object`), testé dans `tests/unit/test_exclusion_filtering.py` (458+ lignes). C'est une exclusion **native Jeedom** (config plugin/objet), en amont et indépendante du pipeline de mapping. L'exclusion de Story 16.3 est un override **utilisateur post-mapping**, à l'étape 4 — mécanisme distinct, ne pas fusionner le vocabulaire (`reason_code`) des deux.

### Point ouvert Task 1 — TRANCHÉ (SCP 2026-07-07, Option 1)

Story 16.2 avait documenté un conflit de conception en `create-story` et l'avait tranché plus tard via un Sprint Change Proposal + débat ADR multi-personas avant `dev-story`. Le point ouvert analogue de cette story (Task 1 — granularité de persistance équipement vs. commande, champ `publication_override`) a été tranché de la même façon, **avant** `dev-story` : débat ADR à 3 personas en sous-agents parallèles (Pipeline/Runtime, Données/Schéma, Produit/UX-Diagnostics), synthèse dans `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07-16-3-overrides-schema.md`, approuvé par Alexandre le 2026-07-07.

**Décision** : `schema_version: 2`, section `equipment_overrides` séparée (clé `eq_id` seule) de `overrides` (clé composite `eq_id:cmd_id` inchangée), champ `publication_override: "exclude" | "force_publish"` aux deux niveaux, précédence exclusion-équipement (veto absolu) > override-commande > force_publish-équipement (défaut) > nominal, reason_codes `publication_excluded_eqlogic`/`publication_excluded_command`/`publication_forced`. Détail complet des tâches 1-4 ci-dessus.

### Testing standards

- Tests d'AC de story : préfixe `test_story_16_3_*` (convention actée depuis Story 16.0-16.2, ne jamais renommer les tests de non-régression existants par domaine).
- Golden corpus : `tests/fixtures/golden_corpus/{sync_payload,expected_sync_snapshot}.json` ; test `test_story_8_4_golden_file.py`.
- Baseline de non-régression actuelle (post Story 16.2) : `pytest tests/unit -q` → 998 passed.

### Dev Agent Guardrails

- Respecter les préfixes `apply_*` / `resolve_*` / `list_*` / `remove_*` dans `overrides.py` — cette story ajoute `resolve_*` (lecture), jamais `apply_*` (`decide_publication` ne renvoie pas de copie mutée d'un objet pipeline, juste une décision).
- Aucune dépendance de `overrides.py` vers les mappers concrets (sens unique, D8), ni import/mutation de `models/topology.py` (D10).
- I2 non négociable : ne JAMAIS permettre à un override de transformer `is_valid=False` en publication. Tout override qui semblerait le faire est un bug bloquant, pas une feature.
- Ne pas confondre le mécanisme d'exclusion Story 4.3 (native Jeedom, étape 1) avec l'override d'exclusion Story 16.3 (utilisateur, étape 4).
- Ne pas ajouter de nouvel endpoint REST public (hors scope 16a ; l'UI/endpoint relève de 16b, cf. Story 16.2 Dev Notes).
- Réutiliser le cache `overrides_cache` (`list_overrides()`) déjà chargé une fois par cycle de sync (Story 16.2 code-review) plutôt que d'ajouter une seconde lecture disque par équipement.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

### Project Structure Notes

- Fichiers à toucher (delta 16a, suite) : `mapping/overrides.py` [MODIFIÉ — `resolve_publication_override()`, éventuelle extension `_override_key()`], `models/decide_publication.py` [MODIFIÉ — paramètre additionnel `publication_override`], `models/mapping.py` [éventuel champ diagnostic sur `PublicationDecision`], `transport/http_server.py` [MODIFIÉ — câblage L.1344 et L.223], `tests/unit/test_story_16_3_*.py` [NOUVEAU].
- **Incohérence détectée entre artefacts (non bloquante, à noter)** : la table "Mapping stories → structure" de `architecture-delta-pe-epic-16-mapping-configurable.md` (L.171) décrit "Story 16.3 (suggestions auto) → champ `source: "suggested"`" — ceci ne correspond PAS au contenu réel de Story 16.3 dans `epics-projection-engine.md` (L.2072-2093, "Overrides de publication et exclusion explicite"), qui est la source canonique utilisée pour cette story (epics_content prioritaire sur les résumés d'architecture-delta, conformément au protocole `discover-inputs.md`). Les "suggestions automatiques" (`source: "suggested"`) ne sont donc PAS le contenu de cette story — probable dérive entre un brouillon initial du SCP et le contenu finalisé des epics. Aucune action requise ici, simple avertissement pour éviter une confusion en dev-story.
- Story 16.4 (diagnostic override-aware, drill-down commande) dépendra du résultat de cette story pour afficher l'origine des exclusions/forçages dans le diagnostic — cohérence de nommage `reason`/`reason_details` à préserver pour cette consommation aval.

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story-16.3] — user story + AC canoniques (contenu de référence de cette story).
- [Source: _bmad-output/planning-artifacts/architecture-delta-pe-epic-16-mapping-configurable.md#ADR] — point d'injection override de publication (persona B, étape 3-4).
- [Source: _bmad-output/planning-artifacts/architecture-delta-pe-epic-16-mapping-configurable.md#D8] — contrat `resolve_publication_override(eq_id, cmd_id) -> Optional[dict]`.
- [Source: resources/daemon/models/decide_publication.py#L46-L93] — `decide_publication()`, invariants I2/I4/I6.
- [Source: resources/daemon/models/mapping.py#L175-L186] — `PublicationDecision`.
- [Source: resources/daemon/mapping/overrides.py] — persistance existante (Story 16.1/16.2), `_override_key` (L.43-44).
- [Source: resources/daemon/transport/http_server.py#L1307] — `overrides_cache`, chargé une fois par cycle de sync (Story 16.2 code-review).
- [Source: resources/daemon/transport/http_server.py#L1344] et [#L223] — points d'appel `decide_publication()` (primaire + secondaire).
- [Source: resources/daemon/tests/unit/test_exclusion_filtering.py] — mécanisme d'exclusion Story 4.3 (natif Jeedom, à ne pas confondre).
- [Source: _bmad-output/implementation-artifacts/16-2-attendu-ha-application-overrides-mapping-candidat.md] — story précédente (intelligence de continuité, conventions `apply_*`/`resolve_*`, précédent de conflit résolu par correct-course).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07-16-3-overrides-schema.md] — SCP tranchant Task 1 (schéma v2, `equipment_overrides`, précédence, reason_codes), approuvé par Alexandre le 2026-07-07.

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (clawcode, create-story workflow BMAD)

### Debug Log References

### Completion Notes List

- **create-story** — 2026-07-07 — statut résultant : `ready-for-dev`. Analyse exhaustive : architecture delta epic 16, epics.md (source canonique du contenu AC réel), état factuel du code `decide_publication`/`overrides.py`/`http_server.py` relevé ligne à ligne, story 16.2 (continuité de conventions). Point ouvert identifié et documenté (Task 1 — granularité de persistance équipement vs. commande). Incohérence mineure notée entre `architecture-delta-pe-epic-16-mapping-configurable.md` (table stories→structure, décrit 16.3 comme "suggestions auto") et le contenu réel de `epics-projection-engine.md` (16.3 = overrides de publication/exclusion) — non bloquante, epics.md fait foi. Story terrain détectée (pipeline `decide_publication`/`publish`) → Task 0 Pre-flight terrain injectée.
- **correct-course (SCP 2026-07-07)** — Task 1 tranché avant dev-story via débat ADR à 3 personas en sous-agents parallèles (Pipeline/Runtime, Données/Schéma, Produit/UX-Diagnostics). Décision : `schema_version: 2`, section `equipment_overrides` séparée, champ `publication_override`, précédence exclusion-équipement > commande > force_publish-équipement > nominal, reason_codes `publication_excluded_eqlogic`/`publication_excluded_command`/`publication_forced`. Approuvé par Alexandre. Tasks 1-4 mises à jour en conséquence. Voir `sprint-change-proposal-2026-07-07-16-3-overrides-schema.md`.
- **dev-story** — 2026-07-07 — statut résultant : `review`. Task 0 pre-flight terrain exécuté (dry-run OK sur box 192.168.1.21, SSH/sudo OK) ; cycle disruptif `--cleanup-discovery --restart-daemon` volontairement différé (même précaution que Story 16.2, à valider avec Alexandre avant republication live). Tasks 1-6 implémentées intégralement :
  - Schéma v2 (`overrides.py`) : `_SUPPORTED_SCHEMA_VERSIONS = (1, 2)`, migration transparente en mémoire d'un fichier v1 existant, section `equipment_overrides` séparée, CRUD `list_equipment_overrides`/`save_equipment_override`/`remove_equipment_override`, fonction pure `resolve_publication_override(eq_id, cmd_id, overrides, equipment_overrides)` implémentant la précédence SCP.
  - `decide_publication()` étendu avec `publication_override: Optional[str] = None`, niveau 2b (exclusion, avant PRODUCT_SCOPE/confidence_policy, toujours après I2) et niveau 4 (force_publish, bypass uniquement confidence_policy, jamais I2).
  - Nouveau champ `PublicationDecision.reason_details: Optional[Dict[str, object]]` (`models/mapping.py`) portant `publication_override_applied`/`override_source`/`underlying_confidence`.
  - Câblage `http_server.py` : nouveau helper `_resolve_publication_override_for_mapping()`, `equipment_overrides_cache` chargé une fois par cycle de sync, branché sur les deux points d'appel (primaire + `_publish_additional_sensors`).
  - 5 déviations de conception documentées et actées dans les tasks ci-dessus (disambiguation de `resolve_publication_override`, placement de `reason_details`, `override_source` fixé à `"user"`, publicisation de `_mapping_cmd_ids` en `mapping_cmd_ids`, sentinelle `cmd_id=-1` pour les mappings sans commande).
  - Tests : 26 nouveaux tests dans `test_story_16_3_publication_override.py` (schéma v2, précédence, exclusion/force_publish, garde-fous I2/I4, câblage http_server). 2 fixes collatéraux dans des tests pré-existants (`test_story_16_0_overrides_injection.py` : littéraux `schema_version` devenus valides avec le bump v2 ; `test_pe_epic5_story_5_1_orchestration.py` : spies `decide_publication` étendues pour accepter le nouveau kwarg).
  - Suite complète : `pytest tests/unit -q` → **1024 passed, 0 failed** (998 baseline + 26 nouveaux). Aucune régression.
  - Prochaine étape suggérée : `code-review` (idéalement contexte/LLM frais, cf. précédent Story 16.2), puis décision terrain sur le cycle disruptif différé de Task 0.
- **code-review** — 2026-07-07 — statut résultant : `done`. Revue adversariale (workflow BMAD `code-review`). Vérifications :
  - **AC1** (exclusion explicite eq/cmd) : IMPLEMENTÉ — `resolve_publication_override` (précédence veto-équipement > commande > force_publish-équipement) + `decide_publication` niveau 2b, `reason_details.override_source="user"`. Vérifié en code + tests.
  - **AC2** (forçage, `is_valid` obligatoire) : IMPLEMENTÉ — `force_publish` au niveau 4 ne bypasse jamais I2 (niveau 2) ni PRODUCT_SCOPE (niveau 3) ; `underlying_confidence` préservée. Garde-fous I2/I4 testés (`test_i2_*`, `test_force_publish_ne_bypass_pas_le_niveau_3_product_scope`).
  - **Audit des tâches [x]** : chaque tâche cochée confirmée par preuve code (schéma v2 `overrides.py:51-52`, CRUD, `resolve_publication_override:369`, `decide_publication` niveaux 2b/4 `decide_publication.py:102-135`, `PublicationDecision.reason_details` `mapping.py:185`, câblage `http_server.py:1349/1386/1460`).
  - **Git vs File List** : aucun écart sur les fichiers source ; `_bmad-output/` exclu par le workflow. Insertion mid-dataclass de `reason_details` vérifiée sûre (aucun appelant positionnel de `PublicationDecision` au-delà de `reason`).
  - **Fixes collatéraux** (`test_story_16_0_*`, `test_pe_epic5_story_5_1_*`) : légitimes, non affaiblissants (le test "refus schéma non supporté" utilise désormais la version 3).
  - **Qualité tests** : 26 tests à assertions réelles, non-régression golden PASS. Suite ciblée + régression (step4, exclusion_filtering Story 4.3, golden) : 103 passed.
  - **Verdict** : 0 Critical, 0 High, 0 Medium. 1 note pour Alexandre (pas un défaut) : `force_publish` débloque uniquement `confidence_policy`, **jamais** PRODUCT_SCOPE — décision de gouvernance (FR40/NFR10) tranchée en Task 3, à confirmer côté produit.
  - Étapes restantes non couvertes par la revue : commit/PR/merge (action explicite d'Alexandre) et cycle disruptif terrain différé de Task 0.

### File List

**Nouveaux :**
- `resources/daemon/tests/unit/test_story_16_3_publication_override.py`

**Modifiés :**
- `resources/daemon/mapping/overrides.py` — schéma v2, `equipment_overrides`, `resolve_publication_override`, `list_equipment_overrides`, `save_equipment_override`, `remove_equipment_override`, `_mapping_cmd_ids` publicisée en `mapping_cmd_ids`.
- `resources/daemon/models/decide_publication.py` — paramètre `publication_override`, niveaux 2b/4.
- `resources/daemon/models/mapping.py` — nouveau champ `PublicationDecision.reason_details`.
- `resources/daemon/transport/http_server.py` — `_resolve_publication_override_for_mapping()`, `equipment_overrides_cache`, câblage des deux points d'appel `decide_publication`.

**Modifiés (fixes collatéraux, hors périmètre initial des tasks) :**
- `resources/daemon/tests/unit/test_story_16_0_overrides_injection.py` — 2 tests ajustés au bump `schema_version` v1→v2.
- `resources/daemon/tests/unit/test_pe_epic5_story_5_1_orchestration.py` — 2 spies `decide_publication` étendues pour le nouveau kwarg `publication_override`.

### Change Log

| Date | Version | Description | Auteur |
|------|---------|-------------|--------|
| 2026-07-07 | 0.1 | create-story — story créée, `ready-for-dev` | clawcode |
| 2026-07-07 | 0.2 | correct-course (SCP) — Task 1 tranché (schéma v2, `equipment_overrides`, précédence) | clawcode |
| 2026-07-07 | 1.0 | dev-story — Tasks 1-6 implémentées, 26 tests + 2 fixes collatéraux, 1024 passed/0 régression, `review` | clawcode |
| 2026-07-07 | 1.1 | code-review — revue adversariale, 0 Critical/High/Medium, AC1/AC2 validés, `done` | clawcode |
