# Story 16.6: Preview / dry-run avant application

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur expert,
je veux prévisualiser l'effet d'un override **avant** de l'appliquer,
afin d'éviter de polluer Home Assistant avec une configuration approximative.

## Acceptance Criteria

1. **AC1 — Dry-run auto vs override (lecture seule).** Étant donné un override en cours d'édition (proposé dans le corps de requête, **non persisté**), quand l'utilisateur demande une preview, alors le backend retourne le résultat **"auto"** (mapping sans override) **et** le résultat **"avec override"** (mapping avec l'override proposé appliqué en mémoire), pour le même équipement/commande. Aucune écriture dans `ha_overrides.json` ni dans `data_dir`.

2. **AC2 — Aucune publication MQTT pendant le dry-run.** Le cycle de preview ne déclenche **aucune** publication MQTT (discovery ni state). Prouvé par un spy/mock sur le publisher : `publish`/`publish_discovery` jamais appelés pendant la preview.

3. **AC3 — Erreurs de validation HA visibles avant sauvegarde.** Le résultat "avec override" passe par `validate_projection()` (même moteur que le pipeline de sync, pas de bypass). Les erreurs de validation HA (override incompatible avec les capabilities réelles) sont exposées dans la réponse **avant** toute sauvegarde, en consommant le verdict existant (aucun nouveau reason_code inventé).

4. **AC4 — Export support enrichi (trace de preview + raisons de refus).** Quand un override est impliqué, l'export support (payload diagnostic existant / endpoint de support) inclut les **raisons de refus** (validation échouée) et une **trace de preview** utile au support, en réutilisant les champs override-aware déjà exposés (Story 16.4 : `attendu_ha`/`mapping_decision`/`type_override`/`publication_override`).

5. **AC5 — Additif, non-régression, `generic_type` natif intact.** La preview est strictement additive : aucune régression sur `/action/sync`, `/system/diagnostics`, le contrat 4D eq-level, ni le golden snapshot. Le `generic_type` Jeedom natif n'est **jamais** muté (non-régression Homebridge). Suite unit complète verte.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run box **déféré au gate terrain Story 16.7** (consolidation epic-level). Aucun accès box requis pour valider 16.6 : l'AC2 « no MQTT publish » est prouvée par **spy** unitaire sur le bridge MQTT (`test_preview_no_mqtt_publish`). Décision prise à create-story et confirmée à l'implémentation (endpoint strictement lecture seule, ne construit jamais de publisher).

- [x] Task 1 — Endpoint de preview override-aware (AC1, AC2) — `POST /system/overrides/preview`
  - [x] Handler `_handle_overrides_preview` + route ajoutés dans `transport/http_server.py`, protégé par `X-Local-Secret`.
  - [x] Corps de requête : override **proposé** `{jeedom_eq_id, jeedom_cmd_id, ha_entity_type}` et/ou `{jeedom_eq_id[, jeedom_cmd_id], publication_policy}`. Validation d'entrée stricte → 400 ; équipement absent → 404 ; secret absent → 401.
  - [x] Résultat **"auto"** : `MapperRegistry().map(eq, snapshot)` sans override.
  - [x] Résultat **"avec override"** : override proposé construit **en mémoire** depuis le body, passé à `apply_type_override` / `_resolve_publication_override_for_mapping` (**jamais** `save_override`).
  - [x] **Zéro effet de bord** : aucun `save_*`, aucun write `data_dir`, aucun `publish*` (garde-fou test `test_preview_does_not_persist_override` + spy MQTT).

- [x] Task 2 — Validation HA avant sauvegarde (AC3)
  - [x] Résultat "avec override" passé par `validate_projection()` (step 3, moteur du pipeline, aucun bypass).
  - [x] Verdict de validation exposé (`is_valid`, `reason_code`, `missing_capabilities`, `missing_fields`) — reason_codes existants uniquement.
  - [x] Cas override incompatible (`climate` sur une lampe → `ha_missing_temperature_command_topic`) : preview signale l'échec, `should_publish=False`.

- [x] Task 3 — Export support (AC4)
  - [x] `support_export` = `{preview_trace: {native, effective, publication_override}, refusal_reasons: [...]}`, uniquement quand un override est impliqué (mapped=True).
  - [x] Additif : réutilise la sémantique 16.4 (native vs effective) ; pas de reason_code inventé.

- [x] Task 4 — Tests unitaires ciblés + non-régression (AC1–AC5)
  - [x] `tests/unit/test_story_16_6_preview_dry_run.py` : 7 tests (auto vs override, spy no-publish, override incompatible, no-persist, override publication exclude, 404, 401).
  - [x] Golden snapshot **inchangé** (l'endpoint preview n'affecte pas `/action/sync` → aucun diff, aucune régénération nécessaire).
  - [x] Suite unit complète : `python3 -m pytest tests/unit -q` → **1035 passed** (1028 + 7).

## Dev Notes

- **Nature de la story** : backend pur, lecture seule, **aucune** mutation d'état (ni disque, ni MQTT). C'est le pendant "preview" des overrides déjà persistés par le PHP Jeedom.
- **Surface d'implémentation** : `resources/daemon/transport/http_server.py` (nouveau handler + route), en réutilisant `mapping/overrides.py` (`apply_type_override`, `resolve_publication_override` — accepter un dict d'overrides ad hoc **en mémoire**), `mapping/registry.py` (`resolve_expected_ha`, `MapperRegistry`) et la validation `validate_projection()` déjà câblée dans le pipeline de sync (`_handle_action_sync`).
- **Overrides côté daemon = lecture seule** : le daemon ne persiste pas les overrides (c'est le PHP Jeedom qui écrit `ha_overrides.json` dans `data_dir`) ; `apply_type_override`/`resolve_publication_override` consomment un dict déjà chargé (`list_overrides` / `list_equipment_overrides`). Pour la preview, injecter un dict **construit à partir du corps de requête**, sans jamais écrire le fichier.
- **Réutiliser, ne pas réinventer** : le "auto vs override" repose sur les mêmes primitives que Story 16.2/16.4. La validation HA repose sur `validate_projection()` (step 3 pipeline). L'honnêteté diagnostique (16.4) fournit déjà `attendu_ha`/`mapping_decision`/`type_override`/`publication_override` pour la trace support.
- **Testing standards** : pytest, harness `create_app(local_secret="test_secret")` + `aiohttp_client`, header `X-Local-Secret`. Spy MQTT : mocker le publisher/bridge exposé dans `app[...]` et asserter zéro appel `publish*`. cwd des tests = `resources/daemon` ; `python3 -m pytest tests/unit/... -q`.

### Dev Agent Guardrails

- **AC2 est une garantie négative** : prouver l'absence de publication MQTT par un spy sur le publisher (pas par un test terrain). Aucun `save_override`/`save_equipment_override`, aucun write `data_dir`, aucun `publish*` pendant la preview.
- **Pas de nouveau reason_code** : consommer les verdicts `validate_projection` et les champs override-aware 16.3/16.4 existants.
- **`generic_type` natif jamais muté** (non-régression Homebridge). L'override ne touche que `ha_entity_type` sur une **copie** (`dataclasses.replace`).
- **Additivité stricte** : golden réaligné seulement si diff purement additif ; sinon investiguer la régression.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.
- **Pour cette story** : le gate terrain réel est consolidé dans la Story 16.7. Ici, la validation est unitaire (spy MQTT + fixtures).

### Project Structure Notes

- Nouveau handler + route dans `transport/http_server.py` (aligné sur les handlers `/system/*` existants).
- Nouveau fichier de test `tests/unit/test_story_16_6_preview_dry_run.py`.
- Aucune nouvelle dépendance ; réutilisation des modules `mapping/*` et de la validation existante.

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story 16.6 : Preview / dry-run avant application]
- [Source: resources/daemon/mapping/overrides.py#apply_type_override] (patch copie, `generic_type` natif intact, pas de bypass validation)
- [Source: resources/daemon/mapping/overrides.py#resolve_publication_override]
- [Source: resources/daemon/mapping/registry.py#resolve_expected_ha] (moteur brut sans override)
- [Source: resources/daemon/transport/http_server.py#_handle_action_sync] (câblage `validate_projection` step 3, chargement overrides one-shot)
- [Source: resources/daemon/transport/http_server.py#_enrich_command_drilldown] (Story 16.4 — champs override-aware réutilisés pour la trace support)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8

### Debug Log References

- `python3 -m pytest tests/unit/test_story_16_6_preview_dry_run.py -q` → 7 passed (après implémentation).
- `python3 -m pytest tests/unit -q` → **1035 passed** (1028 baseline + 7 nouveaux), aucune régression, golden inchangé.
- Probe manuel : `MapperRegistry().map` sur lampe LIGHT_STATE+LIGHT_SLIDER → `light`/probable ; override `switch` valide ; override `climate` → `ha_missing_temperature_command_topic`.

### Completion Notes List

- **create-story** — 2026-07-17 — statut résultant : `ready-for-dev`. Story cadrée : preview/dry-run backend lecture seule (endpoint `POST /system/overrides/preview`), auto vs override en mémoire, `validate_projection` avant sauvegarde, export support enrichi, non-régression additive. Mot-clé terrain « MQTT » présent → Task 0 injectée ; verdict story-context : AC2 (no publish) prouvable par spy, gate terrain réel consolidé en Story 16.7.
- **dev-story** — 2026-07-17 — statut résultant : `review`. Endpoint `POST /system/overrides/preview` implémenté (red-green-refactor) : helper `_preview_mapping_view` (validate_projection + decide_publication, JSON-safe) + handler `_handle_overrides_preview`. AUTO = moteur brut ; OVERRIDDEN = override PROPOSÉ construit en mémoire depuis le body (jamais persisté), `apply_type_override` patch une copie (generic_type natif intact). AC3 : validation HA consommée sans bypass ni nouveau reason_code. AC2 : endpoint ne construit jamais de publisher → prouvé par spy MQTT (zéro appel). AC4 : `support_export` (preview_trace + refusal_reasons). Golden inchangé (aucun impact `/action/sync`). 7 tests ciblés + suite complète 1035 verte.

### File List

- `resources/daemon/transport/http_server.py` (modifié) — helper `_preview_mapping_view`, handler `_handle_overrides_preview`, route `POST /system/overrides/preview`.
- `resources/daemon/tests/unit/test_story_16_6_preview_dry_run.py` (nouveau) — 7 tests AC1–AC5.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié) — 16-6 ready-for-dev → in-progress → review.

### Change Log

- 2026-07-17 — Story 16.6 implémentée : endpoint preview/dry-run override-aware lecture seule (auto vs override en mémoire, validation HA avant sauvegarde, no MQTT publish, export support). Additif, non-régression (1035 tests).
- 2026-07-17 — code-review : PASS. Statut → `done`.

## Senior Developer Review (2026-07-17)

**Verdict : PASS — aucun finding Critical/High/Medium.**

- **AC1 (auto vs override lecture seule)** ✅ — L'endpoint calcule AUTO (`MapperRegistry().map`) et OVERRIDDEN (override proposé construit en mémoire depuis le body, `apply_type_override` sur une copie). Aucun `save_*`, aucun write `data_dir` — garde-fou `test_preview_does_not_persist_override` (monkeypatch `save_override`/`save_equipment_override` → raise).
- **AC2 (no MQTT publish)** ✅ — Le handler ne construit jamais de publisher. Prouvé par spy `test_preview_no_mqtt_publish` (`not bridge.publish.called` + `not bridge.method_calls`).
- **AC3 (validation HA avant sauvegarde)** ✅ — `validate_projection()` (step 3 pipeline) consommé sans bypass ni nouveau reason_code ; verdict exposé (`is_valid`/`reason_code`/`missing_*`). Cas `climate` sur lampe → `ha_missing_temperature_command_topic`, `should_publish=False`.
- **AC4 (export support)** ✅ — `support_export` (preview_trace native/effective/publication_override + refusal_reasons) uniquement quand override impliqué, réutilise la sémantique 16.4.
- **AC5 (additif / non-régression)** ✅ — Diff strictement additif (+167 `http_server.py`, endpoint isolé). Golden inchangé (aucun impact `/action/sync`). `generic_type` natif jamais muté. Suite complète 1035 verte (1028 + 7).

**Qualité** — Input validation robuste (400 body invalide, 401 secret absent, 404 équipement inconnu). Aucune dette introduite. Endpoint aligné sur les handlers `/system/*` existants.
