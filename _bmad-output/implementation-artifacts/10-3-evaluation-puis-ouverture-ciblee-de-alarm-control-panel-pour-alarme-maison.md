# Story 10.3: Évaluation puis ouverture ciblée de `alarm_control_panel` pour `Alarme maison`

Status: done

## Story

En tant qu'utilisateur,
je veux retrouver dans Home Assistant l'alarme maison déjà visible via Homebridge,
afin que la parité minimale utile couvre aussi l'état armé/désarmé et les commandes armer/désarmer sans miroir trompeur.

## Acceptance Criteria

1. **AC1 — Verdict explicite d’ouvrabilité**  
   **Given** le cas représentatif `Alarme maison` dans la matrice 10.0  
   **When** la story est exécutée  
   **Then** elle tranche explicitement entre `ouvrable`, `non ouvrable dans cette vague`, ou `recadrage produit`, avec justification story-level.

2. **AC2 — Mapper `alarm_control_panel` nominal**  
   **Given** un eqLogic Jeedom alarme avec `ALARM_STATE` + `ALARM_ENABLE` + `ALARM_DISABLE`  
   **When** le mapper `alarm_control_panel` est invoqué  
   **Then** il produit un `MappingResult` `ha_entity_type = "alarm_control_panel"` structurellement valide.

3. **AC3 — Publication MQTT disponible**  
   **Given** le mapper produit un `MappingResult` `alarm_control_panel`  
   **When** la publication est déclenchée  
   **Then** `PublisherRegistry` résout `alarm_control_panel` → `publish_alarm_control_panel` et génère un payload discovery HA valide (`state_topic`, `command_topic`, payloads arm/disarm).

4. **AC4 — Ouverture `PRODUCT_SCOPE` sous FR40 / NFR10**  
   **Given** l’ouverture de `alarm_control_panel` dans `PRODUCT_SCOPE`  
   **When** la story est revue  
   **Then** elle embarque dans le même incrément les preuves FR40/NFR10 :
   - cas nominal : `AlarmCapabilities(has_state=True, has_command=True)` → `is_valid=True`
   - cas d’échec état : `AlarmCapabilities(has_state=False, has_command=True)` → `ha_missing_state_topic`
   - cas d’échec commande : `AlarmCapabilities(has_state=True, has_command=False)` → `ha_missing_command_topic`
   - golden-file étendu avec `eq_id=12000` (`Alarme maison`)
   - non-régression des snapshots de registre/known_types.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run validé sur commande canonique (`./scripts/deploy-to-box.sh --dry-run`) dans le protocole story
  - [x] Modes `--stop-daemon-cleanup` et `--cleanup-discovery --restart-daemon` documentés pour la validation terrain
  - [x] Critère de fin de script (`Deploy complete.` / `Stop+cleanup terminé.`) confirmé dans la procédure

- [x] Task 1 — Évaluer l’ouvrabilité `alarm_control_panel` sur `Alarme maison` (AC: #1)
  - [x] Generic types confirmés (`ALARM_STATE`, `ALARM_ENABLE_STATE`, `ALARM_ENABLE`, `ALARM_DISABLE`)
  - [x] Verdict documenté: **ouvrable** dans cette vague

- [x] Task 2 — Implémenter le mapper dédié (AC: #2)
  - [x] `AlarmControlPanelMapper` implémenté
  - [x] Priorité garantie avant `BinarySensorMapper` dans `MapperRegistry`
  - [x] `reason_details` alignés (`state_topic`, `command_topic`)

- [x] Task 3 — Implémenter la publication discovery (AC: #3)
  - [x] `publish_alarm_control_panel` ajouté dans `DiscoveryPublisher`
  - [x] Payload HA MQTT conforme (`platform`, `state_topic`, `command_topic`, `value_template`, payloads arm/disarm)
  - [x] `PublisherRegistry` étendu (`_known_types` + `_publishers`)

- [x] Task 4 — Gouvernance registre + scope produit (AC: #4)
  - [x] `HA_COMPONENT_REGISTRY` étendu pour `alarm_control_panel`
  - [x] `PRODUCT_SCOPE` ouvert à `alarm_control_panel`
  - [x] Contrat FR40/NFR10 validé (nominal + 2 cas d’échec)

- [x] Task 5 — Golden corpus & snapshots (AC: #4)
  - [x] `eq_id=12000` (`Alarme maison`) ajouté au corpus
  - [x] `expected_sync_snapshot.json` mis à jour
  - [x] Snapshots impactés alignés (registry/known_types/compteurs)

- [x] Task 6 — Tests story-level et non-régression (AC: #2, #3, #4)
  - [x] Tests unitaires Story 10.3 ajoutés
  - [x] Non-régression vérifiée sur les suites impactées
  - [x] Campagne globale tracée avec 1 échec préexistant hors scope (Story 10.1)

- [x] Task 7 — Validation terrain contrôlée (AC: #1, #3)
  - [x] Déploiement terrain exécuté: `./scripts/deploy-to-box.sh --dry-run` puis `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Sync terrain OK: `total_eq=282`, `eligible=82`, `published=71`, daemon `mqtt.state=connected`
  - [x] Résultat terrain: **pas de publication alarm_control_panel sur cette box** (aucun eqLogic alarme présent, `eq_id=12000` absent, aucun generic type `ALARM_*`), donc validation fonctionnelle spécifique reportée à une box contenant l’alarme cible

## Dev Notes

- Story 10.3 est la première ouverture de type réellement nouvelle de `pe-epic-10`; rester strictement dans la compatibilité minimale utile.
- Le pattern de gouvernance est identique à la checklist canonique d’ouverture de type : mapper → publisher → registry/known_types → validation FR40/NFR10 → PRODUCT_SCOPE → golden/snapshots → terrain.
- Le mapping `ALARM_STATE` pourrait être capté à tort par `binary_sensor` si l’ordre des mappers n’est pas contrôlé ; l’ordre de `MapperRegistry` est donc critique.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

### Project Structure Notes

- Implémentation attendue dans `resources/daemon/` (mapping, discovery, validation, tests).
- Ne pas modifier `_bmad/` pendant l’implémentation ; conserver les artefacts story dans `_bmad-output/implementation-artifacts/`.
- Respecter les conventions existantes de snapshots/golden dans `resources/daemon/tests/fixtures/golden_corpus/`.

### References

- `_bmad-output/planning-artifacts/epics-projection-engine.md` (section Story 10.3)
- `_bmad-output/planning-artifacts/pe-epic-10-perimetre-prefixe-2026-06-08.md` (Story 10.3)
- `_bmad-output/planning-artifacts/ha-projection-reference.md` (`alarm_control_panel.mqtt` requis)
- `resources/daemon/validation/ha_component_registry.py` (contrat de validation FR40)

## Dev Agent Record

### Agent Model Used

github-copilot/gpt-5.3-codex

### Debug Log References

- BMAD create relancé (story régénérée) — 2026-06-09
- `python3 -m pytest projects/jeedom2ha/resources/daemon/tests/unit/test_story_10_3_alarm_control_panel.py -q` → **9 passed**
- `python3 -m pytest resources/daemon/tests -q` (repo `projects/jeedom2ha`) → **787 passed, 1 failed préexistant (Story 10.1, hors scope 10.3)**

### Completion Notes List

- Create: story 10.3 reconstruite avec garde-fous terrain et AC explicites.
- Dev: implémentation `alarm_control_panel` validée (mapper dédié + publisher + registre + PRODUCT_SCOPE + golden).
- Review: audit adversarial relancé, aucune anomalie bloquante nouvelle détectée sur le périmètre Story 10.3.
- Run terrain exécuté le 2026-06-09: déploiement + restart + sync OK sur box test.
- Constats de preuve: `alarm_control_panels_published=0`, aucun topic `homeassistant/alarm_control_panel/jeedom2ha_*/config` car la topologie box ne contient ni `eq_id=12000` ni commandes `ALARM_*`.
- Point restant hors code: validation terrain réelle de l’entité `alarm_control_panel` à refaire sur une box contenant l’équipement alarme.

### File List

- `_bmad-output/implementation-artifacts/10-3-evaluation-puis-ouverture-ciblee-de-alarm-control-panel-pour-alarme-maison.md`
- `resources/daemon/mapping/alarm_control_panel.py`
- `resources/daemon/mapping/registry.py`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/discovery/registry.py`
- `resources/daemon/validation/ha_component_registry.py`
- `resources/daemon/tests/unit/test_story_10_3_alarm_control_panel.py`
- `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`

### Senior Developer Review (AI)

**Date :** 2026-06-09  
**Reviewer :** github-copilot/gpt-5.3-codex  
**Verdict : PASS — 0 HIGH, 0 MEDIUM, 0 LOW (périmètre Story 10.3)**

- AC1 ✓ verdict d’ouvrabilité explicite (`ouvrable`)
- AC2 ✓ mapper `AlarmControlPanelMapper` présent et priorisé avant `BinarySensorMapper`
- AC3 ✓ `publish_alarm_control_panel` câblé et payload discovery conforme
- AC4 ✓ `PRODUCT_SCOPE` + validation FR40/NFR10 + golden/snapshots alignés

**Note de campagne globale :** 1 échec préexistant subsiste sur Story 10.1, inchangé et hors scope de la Story 10.3.

### Change Log

- 2026-06-09 — BMAD create: story 10.3 régénérée en `ready-for-dev`.
- 2026-06-09 — BMAD dev: tâches story 10.3 tracées comme réalisées, validations/tests rejoués.
- 2026-06-09 — BMAD review: revue adversariale relancée, statut final `done`.
