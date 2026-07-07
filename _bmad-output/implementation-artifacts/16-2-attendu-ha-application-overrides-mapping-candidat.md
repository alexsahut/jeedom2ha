# Story 16.2: Table "attendu Home Assistant par commande" et application backend des overrides de mapping candidat

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un utilisateur expert,
I want voir ce que Home Assistant attend pour chaque commande et pouvoir forcer un candidat HA (ou mapper explicitement certaines commandes),
so that je résous un cas que le moteur automatique ne peut pas inférer correctement, et je comprends pourquoi.

## Acceptance Criteria

**AC1 — Lecture de "l'attendu HA par commande" + proposition automatique**

**Given** une commande Jeedom, mappée ou non
**When** le backend résout son "attendu HA"
**Then** il expose, en lecture, le(s) composant(s) HA et `generic_type` compatibles pour cette commande, dérivés de la source de vérité de projection HA
**And** si la commande n'a aucun `generic_type` configuré, une proposition automatique est calculée à partir du moteur de mapping existant.

**AC2 — Application backend de l'override de type dans le pipeline**

**Given** un équipement éligible avec override de mapping
**When** le pipeline exécute l'étape de mapping
**Then** le moteur conserve le candidat natif
**And** applique le candidat surchargé **avant** la validation HA (`validate_projection`, étape 3)
**And** trace la source `override_*` dans le résultat de diagnostic (`reason_details`), **sans jamais réécrire le `generic_type` Jeedom natif**.

**AC3 — Un override invalide ne bypasse jamais la validation**

**Given** un override qui produit un candidat HA invalide
**When** `validate_projection()` s'exécute
**Then** la validation HA échoue explicitement (`is_valid == False`)
**And** la publication reste interdite
**And** la cause indique que l'override est invalide, sans masquer la décision native.

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / discovery HA / pipeline / publish → Task 0 Pre-flight terrain injectée. -->

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run` — **OK 2026-07-07 (SSH OK | sudo OK, box 192.168.1.21 joignable)**
  - [ ] Sélectionner le mode selon l'objectif de la story : cycle complet republication `--cleanup-discovery --restart-daemon` — **différé : validation terrain à confirmer avec Alexandre avant cycle disruptif sur box live**
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.` — dry-run terminé `Simulation complete`

- [x] Task 1 — `apply_type_override()` dans `overrides.py` (AC2)
  - [x] Ajouter `apply_type_override(mapping: MappingResult, data_dir: str) -> MappingResult` dans `resources/daemon/mapping/overrides.py`, en respectant le préfixe `apply_*` (patch d'une **copie** via `dataclasses.replace`, jamais l'objet source ni les modèles topologie).
  - [x] Lire l'override pertinent via la persistance existante (`list_overrides` / clé composite `f"{eq_id}:{cmd_id}"` ; helper `_mapping_cmd_ids` : `reason_details.cmd_id` du secondaire d'abord, puis `commands`). Absence d'override = retour du `mapping` inchangé (silencieux, non-régression).
  - [x] Patcher uniquement `ha_entity_type` sur la copie ; capabilities conservées telles que détectées (pour que `validate_projection` juge le type surchargé) ; ne jamais toucher `JeedomCmd.generic_type` / `JeedomEqLogic.generic_type` (D10).
  - [x] Aucune dépendance vers les mappers concrets (`switch.py`, `light.py`, …) — sens unique (D8) ; import `MappingResult` uniquement sous `TYPE_CHECKING`.

- [x] Task 2 — Câblage dans le pipeline de sync (AC2)
  - [x] Dans `resources/daemon/transport/http_server.py`, injecter `apply_type_override` **entre l'étape 2 (map) et l'étape 3 (validate_projection)** — après `mapper_registry.map(...)` (L.1303) et avant `validate_projection(...)` (L.1327), sur la variable locale `mapping` (L.1310).
  - [x] Répercuter la même injection sur le chemin secondaire multi-sensor `_publish_additional_sensors(...)` (variable `secondary`, L.211), pour cohérence, avec réécriture `additional_mappings[index] = secondary`.
  - [x] Ne jamais court-circuiter le flux canonique `map → validate_projection → decide_publication → publish` (invariant D7).

- [x] Task 3 — Diagnostic `reason_details` override-aware (AC2, D11)
  - [x] Quand un override est appliqué, ajouter dans `reason_details` la paire indissociable `override_applied: true` + `override_source: "<source>"` (valeur issue du champ `source` de l'override, ex. `"user"`).
  - [x] Si aucun override : ne PAS ajouter `override_applied`/`override_source` (omission, pas de clé `null`) — cohérent avec le style `reason_details` existant.
  - [x] Ne pas écraser les clés `reason_details` natives déjà posées par les mappers (fusion additive via `dict(mapping.reason_details or {})`).

- [x] Task 4 — Override invalide → échec explicite (AC3, D11)
  - [x] Vérifier que `validate_projection()` s'exécute bien sur le candidat **surchargé** et peut renvoyer `is_valid=False` (aucun bypass) — testé sensor→switch (`has_command` manquant) et type inconnu (`ha_component_unknown`).
  - [x] `capabilities` non patchées garantissent que `decide_publication()` refuse la publication quand la projection surchargée est invalide.
  - [x] La cause reste lisible : le `reason_code` de validation natif est conservé, et `override_applied/override_source` signalent l'origine de la surcharge sans masquer la décision.

- [x] Task 5 — Résolution "attendu HA par commande" + proposition auto (AC1) — **TRANCHÉ Option 1 (SCP 2026-07-07)**
  - [x] Ajouter `resolve_expected_ha(eq, snapshot, cmd=None, *, registry=None)` dérivant l'attendu HA de la **source runtime = moteur `MapperRegistry` + registre HA** (`PRODUCT_SCOPE`/`validate_projection`), composants compatibles dérivés des capabilities réellement détectées. **Placée dans `registry.py`** (et non `overrides.py`) pour respecter D8 : `resolve_expected_ha` a besoin du moteur, `overrides.py` doit rester mapper-free — déviation justifiée vs. l'emplacement littéral de la story.
  - [x] Couvrir explicitement `FallbackMapper` (candidat moteur retourné) et le multi-entités (`additional_mappings` → `secondary_ha_entity_types`).
  - [x] La structure de retour prévoit `label_fr` / `family_fr` / `subtype` **nullable** (remplis en 16b, `None` en 16a).
  - [x] Si la commande n'a pas de `generic_type`, la proposition auto reste calculée au niveau eqLogic via `registry.map(eq, snapshot)`.
  - [x] Aucun loader YAML, aucune 2e source de vérité runtime — `ha-projection-reference.yaml` reste un artefact de planning (documenté Dev Notes + Project Structure Notes).

- [x] Task 6 — Tests (AC1-3, non-régression)
  - [x] Créé `resources/daemon/tests/unit/test_story_16_2_apply_type_override.py` (12 tests) : override valide appliqué (copie + trace source), invalide (→ `validate_projection` False, `has_command`/`ha_component_unknown`), proposition auto (commande sans `generic_type`), non-régression sans override (objet identique), secondaire matché par `reason_details.cmd_id`.
  - [x] Garde-fou AST de `test_story_16_0_overrides_injection.py` (L.311 `test_overrides_module_n_importe_jamais_transport_sync_ou_mqtt`) : **inchangé, reste vert**. Il asserte la disjonction des **imports** de `overrides.py` avec {transport, sync, paho, mqtt}, PAS l'absence de fonctions `apply_*`/`resolve_*` (premisse du sous-item inexacte). `apply_type_override` n'importe aucun module interdit et `resolve_expected_ha` vit dans `registry.py` → invariant préservé, aucune modification requise.
  - [x] Non-régression golden-file (`tests/fixtures/golden_corpus/expected_sync_snapshot.json`) : `test_story_8_4_golden_file.py` vert (sans override, snapshot inchangé).
  - [x] Assertion explicite : `generic_type` natif jamais muté sur l'objet source (`test_apply_type_override_ne_mute_jamais_le_mapping_source_ni_le_generic_type`).
  - [x] Suite daemon complète : **997 passed, 0 régression** (`tests/unit`, 72.8s). Tests ciblés 16.2 + 16.0 : 33 passed.

## Dev Notes

### Contexte pipeline (source de vérité : `architecture-delta-pe-epic-16-mapping-configurable.md`)

- Pipeline canonique 5 étapes (D1/D7) : `assess_all (éligibilité) → map (2) → validate_projection (3) → decide_publication (4) → publish (5)`. Jamais de court-circuit.
- **Point d'injection override de type** : entre étape 2 et 3 (ADR + D6), patch d'une **copie** du `MappingResult`. Injecter après avoir le candidat natif, avant validation — sinon `validate_projection` jugerait l'ancien type et `ProjectionValidity` deviendrait mensongère.
- **D8** : `overrides.py` expose `apply_type_override(mapping) -> MappingResult` (câblé cette story) ; `resolve_publication_override(...)` (override de politique de publication) relève de la **Story 16.3**, hors scope ici.
- **D10** : `generic_type` Jeedom natif jamais modifié — garantie non-régression Homebridge, testée explicitement.
- **D11** : un override incompatible avec les capabilities passe quand même par `validate_projection` et peut renvoyer `is_valid=False` — jamais de bypass. `reason_details` distingue `override_applied: true` + `override_source` du calcul natif.
- **Naming** (D5 patterns) : `apply_*` = patch copie `MappingResult` en mémoire ; `resolve_*` = lecture d'une décision/config sans muter d'objet pipeline. Pas de `get_override()` générique.
- **Format `reason_details`** : `override_applied`/`override_source` = paire indissociable ; si `override_applied` absent/false → `override_source` omis (jamais `null`).

### État factuel du code (relevé 2026-07-07)

- `mapping/overrides.py` (158 l.) après Story 16.1 : persistance pure (`_overrides_path` L.33, `_override_key` L.37, `_load_raw` L.41, `list_overrides` L.81, `save_override` L.93, `remove_override` L.129). **`apply_type_override`/`resolve_publication_override` ABSENTS** → à créer.
- `models/mapping.py` : `MappingResult` (L.133-171), champs dont `ha_entity_type` (L.142), `capabilities` (L.152), `reason_details: Optional[Dict[str,object]]` (L.153), `projection_validity` (L.154), `pipeline_step_reached` (L.156). **Pas de champ `override_*`** — les clés d'override vivent DANS `reason_details` (D11), pas en attribut top-level.
- `transport/http_server.py` : boucle sync L.1289-1364. `mapper_registry.map(eq, snapshot)` → `mapping` (L.1297) ; agrégation `mappings[eq_id]=mapping` (L.1301) ; `validate_projection(mapping.ha_entity_type, mapping.capabilities)` (L.1316) → `pipeline_step_reached=3` (L.1318) ; `decide_publication(mapping, confidence_policy=…)` (L.1319) ; `publish(mapping, snapshot)` (L.1340). Chemin secondaire multi-sensor : `_publish_additional_sensors(...)` (~L.185-240, var `secondary`, validate ~L.208, decide ~L.212, publish ~L.227).
- `mapping/registry.py` : `MapperRegistry.map(eq, snapshot) -> Optional[MappingResult]` (L.46) ; `map_all` (L.61). Proposition auto = candidat au niveau **eqLogic**, pas par commande isolée.
- `models/topology.py` : `JeedomCmd.id` (L.74, cmd_id), `JeedomCmd.generic_type` (L.77, natif) ; `JeedomEqLogic.id` (L.87, eq_id), `JeedomEqLogic.generic_type` (L.93). Clé composite override = `eq_id:cmd_id`.
- `validation/ha_component_registry.py` : `validate_projection(ha_entity_type, capabilities) -> ProjectionValidity` (L.136-196, fonction pure). Invalide si `ha_entity_type` inconnu (`reason_code="ha_component_unknown"`) ou capabilities manquantes (reason_code par priorité déterministe). `PRODUCT_SCOPE` = light, cover, switch, sensor, binary_sensor, button, climate, alarm_control_panel.

### Testing standards

- Tests d'AC de story : préfixe `test_story_16_2_*` (ne renomme jamais les tests de non-régression par domaine).
- Golden corpus : `tests/fixtures/golden_corpus/{sync_payload,expected_sync_snapshot}.json` ; test `test_story_8_4_golden_file.py`.
- Le fichier `test_story_16_0_overrides_injection.py` (21 tests) contient un test d'inspection AST (~L.315) affirmant que les fonctions pipeline `apply_*`/`resolve_*` ne sont pas encore câblées — **il DEVIENDRA faux** dès Task 1/2 : le mettre à jour (adapter l'invariant), pas le supprimer.

### Dev Agent Guardrails

- Respecter les préfixes `apply_*` / `resolve_*` / `list_*` / `remove_*` dans `overrides.py`.
- Aucune dépendance de `overrides.py` vers les mappers concrets (sens unique, D8), ni import/mutation de `models/topology.py` (D10).
- Jamais d'exception fatale : override absent = silencieux (non-régression) ; override corrompu = `logger.warning` + fallback "aucun override".
- Jamais `override_source` sans `override_applied: true`.
- Ne pas ajouter de nouvel endpoint REST public (hors scope 16a ; l'UI/endpoint relève de 16b).

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

### Project Structure Notes

- Fichiers touchés (delta 16a) : `mapping/overrides.py` [MODIFIÉ — `apply_type_override`, `resolve_expected_ha`], `models/mapping.py` [éventuel helper `reason_details`], `transport/http_server.py` [MODIFIÉ — injection étapes 2-3, primaire + secondaire], `tests/unit/test_story_16_2_*.py` [NOUVEAU], `tests/unit/test_story_16_0_overrides_injection.py` [MODIFIÉ — garde-fou AST].
- **✅ Source de vérité "attendu HA" — TRANCHÉ (SCP 2026-07-07, Option 1, approuvé Alexandre)** : la vérité runtime = `validation/ha_component_registry.py::HA_COMPONENT_REGISTRY` **+ logique des mappers** (`registry.py` + allowlists `generic_type` par mapper) ; le YAML `ha-projection-reference.yaml` reste un **artefact de planning** (conforme à son `_meta.note` qui prescrit une *dérivation* vers l'artefact consommé par le daemon, non un chargement direct). Aucun loader YAML, aucune 2e source de vérité runtime. Contexte du choix : le YAML n'est chargé nulle part par le daemon et ne fait pas de mapping direct `generic_type → composant HA` (2 sections indépendantes) ; 4 personas ADR sur 5 → Option 1, drift structurellement impossible.
- **Frontière 16b actée (pré-requis bloquant)** : le sélecteur d'override par commande (stories 16.5-16.7) consommera les labels FR / familles / subtypes de la section `jeedom_generic_types` de `ha-projection-reference.yaml` via un chargeur/export dédié cadré en 16b. **Interdiction de démarrer 16b sans cette source** ; ne pas livrer un sélecteur affichant des identifiants HA crus (anti-régression Homebridge). La lecture 16.2 expose une structure ouverte à enrichissement (champs label nullable en 16a).
- **Concern séparé (hors epic 16)** : le `ha_component_registry.yaml` "dérivé, consommé par le daemon" prévu par le `_meta.note` n'a jamais été généré ; le daemon maintient un dict Python à la main — dette de gouvernance à cadrer indépendamment, PAS un blocage de 16.2.
- Convention persistance déjà en place : `data/ha_overrides.json`, `schema_version: 1`, clé `eq_id:cmd_id`, `source: "user"` (Story 16.1, ne pas redéfinir).

### References

- [Source: _bmad-output/planning-artifacts/architecture-delta-pe-epic-16-mapping-configurable.md#D8-D12] — contrat module, injection 2-3, non-mutation generic_type, non-bypass validation, tests.
- [Source: _bmad-output/planning-artifacts/architecture-delta-pe-epic-16-mapping-configurable.md#ADR] — point d'injection override (personas A/B/C).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-06-mapping-configurable.md#Story-16.2] — user story + AC + dev notes epic.
- [Source: resources/daemon/mapping/overrides.py] — persistance existante (Story 16.1).
- [Source: resources/daemon/transport/http_server.py#L1289-L1364] — boucle pipeline de sync.
- [Source: resources/daemon/validation/ha_component_registry.py#L136-L196] — `validate_projection`.
- [Source: resources/daemon/models/mapping.py#L133-L171] — `MappingResult` / `reason_details`.
- [Source: resources/daemon/models/topology.py#L73-L100] — `JeedomCmd` / `JeedomEqLogic`.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (clawcode, dev-story workflow BMAD)

### Debug Log References

- `python3 -m pytest tests/unit/test_story_16_2_apply_type_override.py tests/unit/test_story_16_0_overrides_injection.py -q` → 33 passed (0.14s).
- `python3 -m pytest tests/unit -q` → **997 passed, 0 failure** (72.8s).
- `python3 -m pytest -k "golden or snapshot"` → 19 passed (golden-file + snapshots non-régression).
- **code-review (2026-07-07)** — après fixes : `python3 -m pytest tests/unit/test_story_16_2_apply_type_override.py -q` → **13 passed** (12 initiaux + 1 nouveau test lifecycle). `python3 -m pytest tests/unit -q` → **998 passed, 0 failure** (72.8s). `python3 -m pytest -k "golden or snapshot"` → 19 passed (inchangé).

### Completion Notes List

- **create-story** — 2026-07-07 — statut résultant : `ready-for-dev`. Analyse exhaustive des artefacts (architecture delta epic 16, SCP, code runtime relevé ligne à ligne). Conflit "source de vérité attendu HA" (YAML non chargé) identifié et documenté pour arbitrage en dev-story. Task 0 Pre-flight terrain injectée (story terrain : pipeline/daemon/MQTT/discovery).
- **correct-course (SCP 2026-07-07, approuvé Alexandre)** — conflit source de vérité TRANCHÉ Option 1 (Hybride borné). Débat ADR 5 personas : 4× Option 1, 1× Hybride. Task 5 réécrite (dérivation registry + mappers, pas registry seul ; Fallback/multi-entités ; champs label nullable). Project Structure Notes : conflit → résolu ; frontière 16b actée (labels FR depuis `jeedom_generic_types`, chargeur dédié 16b) ; dette gouvernance `ha_component_registry.yaml` dérivé notée hors epic 16. Réf : `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07.md`.
- **dev-story** — 2026-07-07 — statut résultant : `review`. AC1/AC2/AC3 implémentés (Tasks 1-6). Points de conception tranchés en cours d'implémentation :
  - **Déviation D8 justifiée** : `resolve_expected_ha` placée dans `mapping/registry.py` (et non `overrides.py` comme le suggérait littéralement la story), car elle dépend du moteur `MapperRegistry` ; `overrides.py` reste strictement mapper-free (seul `apply_type_override` y est ajouté, sans import de mapper).
  - **Garde-fou AST 16.0 inchangé** : `test_overrides_module_n_importe_jamais_transport_sync_ou_mqtt` (L.311) asserte la disjonction des **imports** de `overrides.py`, pas l'absence de `apply_*`/`resolve_*`. La prémisse du sous-item Task 6 était inexacte → aucun test à adapter, l'invariant reste vert.
  - **D11 par construction** : `apply_type_override` ne patche que `ha_entity_type` et conserve `capabilities` détectées → `validate_projection` juge le type surchargé et échoue sur override incompatible (aucun bypass), vérifié par tests.
  - **Terrain** : Task 0 dry-run OK (box 192.168.1.21 joignable, SSH/sudo OK). Cycle disruptif `--cleanup-discovery --restart-daemon` **différé** — validation terrain à confirmer avec Alexandre avant tout cycle sur box live. Impl. purement pipeline in-process, couverte par le golden-file → non-régression déjà prouvée hors terrain.
  - **AC1 — statut d'exposition** : `resolve_expected_ha()` est implémentée et testée (4 tests dédiés) mais **n'est appelée par aucune route HTTP** à ce stade — c'est un choix de scope assumé (l'endpoint/UI de lecture est différé au sélecteur d'override, Story 16.6/16b, cf. Project Structure Notes "Ne pas ajouter de nouvel endpoint REST public"). AC1 est donc satisfaite au niveau logique/backend, pas encore "exposée" à un appelant réel.
- **code-review** — 2026-07-07 — statut résultant : `done`. 0 High, 3 Medium, 1 Low. Tous corrigés (choix 1 : fix immédiat) :
  - **[Medium] Docstring `overrides.py` obsolète** : corrigée — reflète maintenant que `apply_type_override` (lecture) EST appelée par le pipeline de sync depuis cette story, seules les écritures restent réservées à un futur handler HTTP.
  - **[Medium] N+1 I/O `list_overrides`** : `apply_type_override()` accepte désormais un paramètre optionnel `overrides=` (dict pré-chargé) ; `_do_handle_action_sync` charge `list_overrides(_DATA_DIR)` **une seule fois par cycle de sync** et le transmet au chemin primaire et à `_publish_additional_sensors` (nouveau paramètre `overrides_cache`). Signature rétro-compatible (paramètre optionnel, callers existants/tests inchangés).
  - **[Medium] Interaction non testée avec le retypage (Story 5.2)** : documentée dans la docstring de `_detect_lifecycle_changes` (comportement intentionnel) + nouveau test `test_override_qui_change_ha_entity_type_declenche_le_retypage_lifecycle` prouvant qu'un override changeant `ha_entity_type` déclenche bien l'unpublish de l'ancien topic.
  - **[Low] Nommage `_publish_secondary_mappings` → `_publish_additional_sensors`** : corrigé dans les Dev Notes de cette story (Task 2, État factuel du code) pour correspondre au nom réel de la fonction.
  - Validation post-fix : suite ciblée 13 passed, suite daemon complète **998 passed, 0 régression**, golden-file/snapshots inchangés (19 passed).

### File List

**Modifiés :**
- `resources/daemon/mapping/overrides.py` — `_mapping_cmd_ids()` (helper), `apply_type_override()` (AC2/D8/D10/D11, + paramètre optionnel `overrides=` pour éviter la relecture disque par appel — fix code-review), docstring module corrigée (rôle réel dans le pipeline).
- `resources/daemon/mapping/registry.py` — `resolve_expected_ha()` (AC1, module-level), imports `Any/Dict`, `JeedomCmd`, `PRODUCT_SCOPE`/`validate_projection`.
- `resources/daemon/transport/http_server.py` — import `apply_type_override` + `list_overrides` ; injection chemin primaire (L.1310) et secondaire multi-sensor (L.211/`_publish_additional_sensors`), entre map et validate_projection ; `overrides_cache` chargé une fois par cycle de sync et transmis aux deux chemins (fix code-review) ; docstring `_detect_lifecycle_changes` complétée (interaction override/retypage).
- `resources/daemon/tests/unit/test_story_16_2_apply_type_override.py` — 12 tests initiaux + 1 nouveau test (`test_override_qui_change_ha_entity_type_declenche_le_retypage_lifecycle`) ajouté en code-review.

**Artefacts de planning MAJ (correct-course, appliqués avant dev-story) :**
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07.md` — `status: approved`.
- `_bmad-output/planning-artifacts/architecture-delta-pe-epic-16-mapping-configurable.md` — note correction Option 1.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 16.2 → `review`.
