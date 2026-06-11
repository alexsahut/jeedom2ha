# Story 10.2 : Ouverture gouvernée de `climate` pour les thermostats Homebridge représentatifs

Status: done

## Story

En tant qu'utilisateur,
je veux retrouver dans Home Assistant les thermostats déjà exposés via Homebridge,
afin que la compatibilité minimale utile couvre aussi le chauffage et les consignes principales.

## Acceptance Criteria

**AC1 — Cadrage des contraintes `climate` depuis la référence HA**
**Given** les thermostats représentatifs identifiés par l'audit (`Thermostat chambre Arthur`, `Thermostat chambre Margaux`, `Thermostat chambre parent`, `Thermostat Galerie`, `Thermostat RDC`, `Thermostat SDB`, `Thermostat SPA`)
**When** la story est cadrée contre `ha-projection-reference.md`
**Then** les contraintes `climate` nécessaires sont citées explicitement depuis la référence HA

**AC2 — Mapper `climate` nominal**
**Given** un eqLogic Jeedom thermostat correctement typé
**When** le mapper `climate` est invoqué
**Then** il produit un `MappingResult` `ha_entity_type = "climate"` structurellement valide sur les cas nominaux représentatifs
**And** la publication MQTT correspondante est disponible dans `PublisherRegistry`

**AC3 — Ouverture `PRODUCT_SCOPE` sous FR40 / NFR10**
**Given** l'ouverture de `climate` dans `PRODUCT_SCOPE`
**When** la story est revue
**Then** elle embarque dans le même incrément les preuves FR40 / NFR10 :
**And** cas nominaux
**And** cas d'échec de validation
**And** golden-file étendu
**And** non-régression diagnostic

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Validation complète republication + discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
    - Vérification suppression/cleanup ciblée (si nécessaire) : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
  - [x] Vérifier que le script termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Cadrage story-level `climate` et preuves de référence (AC1)
  - [x] 1.1 Citer explicitement la ligne preuve `ha-projection-reference.md#climate.mqtt`
  - [x] 1.2 Confirmer les 7 thermostats cibles de l'audit Homebridge (6 pièces + `Thermostat SPA`)
  - [x] 1.3 Documenter la borne produit : compatibilité minimale utile, pas d'équivalence HVAC exhaustive

- [x] Task 2 — Mapper `climate` dans la cascade registry-driven (AC2)
  - [x] 2.1 Créer `resources/daemon/mapping/climate.py` (ou étendre un mapper existant si déjà présent)
  - [x] 2.2 Produire un `MappingResult` avec `ha_entity_type="climate"` pour thermostat correctement typé
  - [x] 2.3 Définir les `reason_code` nominaux/stables associés au mapping thermostat
  - [x] 2.4 Enregistrer le mapper dans `resources/daemon/mapping/registry.py` à une position documentée et déterministe

- [x] Task 3 — Publication MQTT Discovery `climate` + registry publisher (AC2)
  - [x] 3.1 Ajouter `publish_climate` dans `resources/daemon/discovery/publisher.py`
  - [x] 3.2 Ajouter la clé `"climate"` dans `PublisherRegistry._known_types`
  - [x] 3.3 Ajouter la résolution `"climate": publisher.publish_climate` dans `_publishers`
  - [x] 3.4 Vérifier le topic : `homeassistant/climate/jeedom2ha_{eq_id}/config`

- [x] Task 4 — Gouvernance d'ouverture `PRODUCT_SCOPE` (AC3)
  - [x] 4.1 Mettre à jour `resources/daemon/validation/ha_component_registry.py` : ajout de `"climate"` à `PRODUCT_SCOPE`
  - [x] 4.2 Ajouter tests FR40/NFR10 minimum pour `validate_projection("climate", ...)` :
    - [x] nominal (`is_valid=True`)
    - [x] échec (`is_valid=False` + `reason_code` stable)
  - [x] 4.3 Vérifier que les tests de non-régression sur types déjà ouverts restent PASS

- [x] Task 5 — Golden-file et diagnostic non-régression (AC3)
  - [x] 5.1 Étendre le corpus golden-file Story 8.4 avec thermostats représentatifs
  - [x] 5.2 Mettre à jour `expected_sync_snapshot.json` (counters + résultats attendus)
  - [x] 5.3 Vérifier la non-régression des équipements historiques du corpus
  - [x] 5.4 Vérifier la stabilité diagnostic (`projection_validity`, `publication_decision`, `reason_code`)

- [x] Task 6 — Tests unitaires ciblés story 10.2 (AC2, AC3)
  - [x] 6.1 Créer `resources/daemon/tests/unit/test_story_10_2_climate_opening.py`
  - [x] 6.2 Cas nominaux mapper/publisher pour thermostats représentatifs
  - [x] 6.3 Cas d'échec de validation (capabilities manquantes ou structure incomplète)
  - [x] 6.4 Cas `PublisherRegistry.known_types()` incluant `climate`

- [x] Task 7 — Gate terrain box réelle + clôture BMAD story-level (AC1, AC2, AC3)
  - [x] 7.1 Déployer via script officiel `deploy-to-box.sh`
  - [x] 7.2 Vérifier présence des entités `climate` cibles dans Home Assistant
  - [x] 7.3 Vérifier commandabilité minimale utile (consigne/mode selon capacités réellement exposées)
  - [x] 7.4 Documenter preuves terrain dans Completion Notes
  - [x] 7.5 Passer `Status` à `done` après gate terrain PASS

## Dev Notes

### Contexte actif

`pe-epic-10` vise une parité Homebridge -> HA minimale utile, gouvernée par le pipeline canonique (étapes 1→5), le registre HA et la règle d'ouverture FR40/NFR10. Story 10.1 a clôturé le chemin `button` des 5 scénarios HomeKit. Story 10.2 est la première ouverture de type nouvelle de l'epic (`climate`).

### Guardrails story-level

- Ne pas élargir cette story à une équivalence HVAC exhaustive (modes avancés, presets, programmes, etc.)
- `Thermostat SPA` reste un cas représentatif ; ne pas généraliser ici les composites métier (renvoyés à 10.4)
- Toute modification `PRODUCT_SCOPE` doit rester strictement couplée aux preuves FR40/NFR10 dans le même incrément
- Ne pas ouvrir d'autres types (`alarm_control_panel`, `number`, `select`) dans cette story

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser exclusivement `scripts/deploy-to-box.sh` pour les tests box réelle
- Ne pas substituer par copie manuelle SSH/rsync ad hoc
- Référence opérationnelle : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`

### Références de cadrage

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md#Story-10.2--Ouverture-gouvernee-de-climate-pour-les-thermostats-Homebridge-representatifs`]
- [Source: `_bmad-output/planning-artifacts/pe-epic-10-perimetre-prefixe-2026-06-08.md#Story-10.2--Ouverture-gouvernee-de-climate-pour-les-thermostats-Homebridge-representatifs`]
- [Source: `_bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md`]
- [Source: `_bmad-output/planning-artifacts/ha-projection-reference.md#climate.mqtt`]
- [Source: `resources/daemon/validation/ha_component_registry.py`]
- [Source: `resources/daemon/mapping/registry.py`]
- [Source: `resources/daemon/discovery/registry.py`]

## Dev Agent Record

### Agent Model Used

claude-cli/claude-sonnet-4-6

### Debug Log References

- `grep -n "Story 10.2" _bmad-output/planning-artifacts/epics-projection-engine.md`
- `grep -n "Story 10.2" _bmad-output/planning-artifacts/pe-epic-10-perimetre-prefixe-2026-06-08.md`
- `grep -n "climate.mqtt" _bmad-output/planning-artifacts/ha-projection-reference.md`
- `sed -n '1,220p' resources/daemon/validation/ha_component_registry.py`
- `sed -n '1,220p' resources/daemon/mapping/registry.py`
- `sed -n '1,220p' resources/daemon/discovery/registry.py`

### Completion Notes List

- 2026-06-09 — Story 10.2 créée via workflow BMAD `create-story` avec statut `ready-for-dev`.
- 2026-06-09 — Scope borné confirmé : ouverture `climate` uniquement, gouvernée FR40/NFR10 dans le même incrément.
- 2026-06-09 — Préparation des tâches orientée preuves : mapper + publisher + PRODUCT_SCOPE + golden-file + gate terrain.
- 2026-06-09 — Implémentation Tasks 0–6 complète (claude-sonnet-4-6) :
  - `mapping/climate.py` créé : détection signal `THERMOSTAT_SET_SETPOINT` (action/slider), reason_code `climate_thermostat_setpoint`, capabilities `ClimateCapabilities(has_setpoint=True)`, topics temperature command + state + current (optionnel).
  - `ClimateMapper` inséré avant `SensorMapper` dans `MapperRegistry` (ordre déterministe critique : les thermostats portent `THERMOSTAT_TEMPERATURE` info/numeric que `SensorMapper` aurait capturé en premier).
  - `publish_climate` ajouté dans `DiscoveryPublisher` ; payload : `temperature_command_topic`, `temperature_state_topic`, `modes=["heat","off"]`, availability, device/origin.
  - `PublisherRegistry._known_types` + `_publishers` mis à jour pour `"climate"`.
  - `PRODUCT_SCOPE` étendu à 7 types ; `ClimateCapabilities` + `has_setpoint` ajoutés au registre de validation et `_CAPABILITY_TO_REASON`.
  - `test_step3_governance_fr40.py` : preuve `climate` ajoutée dans `_GOVERNED_SCOPE`.
  - 3 eqLogics thermostats (11000–11002) ajoutés au corpus golden-file (51 total) ; `expected_sync_snapshot.json` régénéré ; test golden-file PASS.
  - 14 tests story-10.2 écrits ; suite complète : 769 PASS, 1 échec préexistant (Story 10.1 — hors scope).
  - Status passé à `review` ; Task 7 (gate terrain) en attente d'Alexandre.
- 2026-06-09 — Gate terrain PASS après correctif mapping thermostat (gpt-5.3-codex) :
  - Correctif 1 : `ClimateMapper` accepte `THERMOSTAT_SET_SETPOINT` action avec `subType=""` (en plus de `slider`) ; tests unitaires story 10.2 mis à jour.
  - Correctif 2 : ordre `MapperRegistry` ajusté pour prioriser `ClimateMapper` avant `BinarySensorMapper` afin d'éviter la capture des thermostats via `THERMOSTAT_STATE`.
  - Validation locale : `pytest -q resources/daemon/tests/unit/test_story_10_2_climate_opening.py resources/daemon/tests/unit/test_story_8_1_mapper_registry.py` → `24 passed`.
  - Validation box réelle (sync) : `mapping_summary.climates_published = 7` ; logs daemon : publication `homeassistant/climate/jeedom2ha_{240,242,219,217,128,193,595}/config` + unpublish des `binary_sensor` thermostats.
  - Validation HA live : 7 entités `climate` visibles (`Thermostat chambre Arthur`, `Thermostat chambre Margaux`, `Thermostat chambre parent`, `Thermostat Galerie`, `Thermostat RDC`, `Thermostat SDB`, `Thermostat SPA`).
  - Commandabilité minimale utile validée structurellement via payload discovery (`temperature_command_topic`, `temperature_state_topic`, `modes=["heat","off"]`) pour les 7 thermostats.
- Status passé à `done`.

### File List

- `_bmad-output/implementation-artifacts/10-2-ouverture-gouvernee-de-climate-pour-les-thermostats-homebridge-representatifs.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/mapping/climate.py` (CREATED)
- `resources/daemon/mapping/registry.py` (MODIFIED — ClimateMapper avant SensorMapper)
- `resources/daemon/discovery/publisher.py` (MODIFIED — publish_climate)
- `resources/daemon/discovery/registry.py` (MODIFIED — climate dans known_types + _publishers)
- `resources/daemon/models/mapping.py` (MODIFIED — ClimateCapabilities + MappingCapabilities union)
- `resources/daemon/validation/ha_component_registry.py` (MODIFIED — climate PRODUCT_SCOPE + has_setpoint)
- `resources/daemon/tests/unit/test_story_10_2_climate_opening.py` (CREATED)
- `resources/daemon/tests/unit/test_step3_governance_fr40.py` (MODIFIED — preuve climate)
- `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json` (MODIFIED — +3 thermostats)
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json` (REGENERATED)
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py` (MODIFIED — corpus shape + eq 6001)
- `resources/daemon/tests/unit/test_ha_component_registry.py` (MODIFIED — PRODUCT_SCOPE 7 types)
- `resources/daemon/tests/unit/test_story_7_2_wave_registry.py` (MODIFIED — climate hors NON_WAVE_TYPES)
- `resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py` (MODIFIED — scope snapshot)
- `resources/daemon/tests/unit/test_story_7_4_governance_product_scope.py` (MODIFIED — 7 types)
- `resources/daemon/tests/unit/test_story_8_1_mapper_registry.py` (MODIFIED — ClimateMapper dans ordre)
- `resources/daemon/tests/unit/test_story_8_2_publisher_registry.py` (MODIFIED — sets + unknown type)
- `resources/daemon/tests/unit/test_story_9_1_sensor_mapper.py` (MODIFIED — known_types)
- `resources/daemon/tests/unit/test_story_9_2_binary_sensor_mapper.py` (MODIFIED — known_types)
- `resources/daemon/tests/unit/test_story_9_3_button_mapper.py` (MODIFIED — known_types)

## Change Log

- 2026-06-09 — Story 10.2 créée (BMAD create-story), statut `ready-for-dev`.
- 2026-06-09 — Implémentation Tasks 0–6 complète ; statut passé à `review`. ClimateMapper, publish_climate, PRODUCT_SCOPE ouvert (7 types), golden-file régénéré (51 eqLogics), 769 tests PASS.
