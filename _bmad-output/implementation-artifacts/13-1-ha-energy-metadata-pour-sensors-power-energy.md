# Story 13.1: HA Energy metadata pour sensors power/energy

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur Home Assistant,
je veux que les sensors Jeedom de puissance et d'energie deja publies par jeedom2ha portent les metadonnees statistiques HA attendues,
afin de pouvoir les exploiter dans les statistiques long-terme, le dashboard Energy et l'integration Riemann sans conversion implicite dans le daemon.

## Acceptance Criteria

1. **Puissance instantanee POWER/W.** Given une commande Jeedom `POWER` de type info numeric avec unite `W`, When le sensor est mappe puis publie en MQTT Discovery, Then le payload contient `device_class: "power"`, `unit_of_measurement: "W"` et `state_class: "measurement"`.
2. **Energie cumulative Wh/kWh.** Given une commande d'energie cumulative fiable avec unite `Wh` ou `kWh`, When le sensor est mappe puis publie en MQTT Discovery, Then le payload contient `device_class: "energy"`, l'unite source `Wh` ou `kWh`, et `state_class: "total_increasing"`.
3. **Aucune conversion W -> kWh.** Given une valeur Jeedom de puissance instantanee en `W`, When le daemon publie l'etat ou la discovery, Then il conserve la valeur brute et l'unite source ; il ne calcule, n'integre, ni ne convertit jamais de `W` en `kWh`.
4. **Propagation bornee dans le publisher.** Given un `MappingResult` sensor dont `reason_details["state_class"]` est renseigne, When `DiscoveryPublisher` construit le payload sensor, Then `payload["state_class"]` est ajoute ; When `state_class` est absent ou `None`, Then le champ n'est pas publie.
5. **Pas de metadata incertaine.** Given un sensor non numerique, une classe HA incertaine, ou une unite hors perimetre power/energy de cette story, When le payload discovery est construit, Then aucun `state_class` energy/power n'est ajoute par opportunisme.
6. **Tests unitaires attendus.** Given la suite de tests daemon, When l'implementation est livree, Then des tests ciblent `resources/daemon/mapping/sensor.py` pour la resolution `device_class` / `unit_of_measurement` / `state_class`, et `resources/daemon/discovery/publisher.py` pour la presence ou l'absence du champ `state_class` dans le payload MQTT Discovery.
7. **Gate terrain Energy/Riemann.** Given une box Jeedom reelle et Home Assistant apres deploy/restart/sync, When au moins un payload MQTT Discovery `sensor` power est inspecte, Then il expose `state_class=measurement`, et le capteur est exploitable cote HA Energy ou comme source d'integration Riemann.
8. **Non-regression des sensors existants.** Given les sensors deja publies hors power/energy, When la discovery est republiee, Then leurs `unique_id`, `object_id`, `state_topic`, `device_class` et `unit_of_measurement` existants restent stables sauf ajout explicitement justifie de `state_class`.

## Tasks / Subtasks

- [x] Task 1 — Etendre les metadonnees sensor dans `resources/daemon/mapping/sensor.py` (AC: 1, 2, 3, 5)
  - [x] Ajouter le transport de `state_class` dans `reason_details` pour les sensors eligibles.
  - [x] Associer `device_class == "power"` / unite `W` a `state_class = "measurement"`.
  - [x] Associer `device_class == "energy"` / unite `Wh` ou `kWh` cumulative a `state_class = "total_increasing"`.
  - [x] Verrouiller l'absence de conversion de valeur et d'unite dans le mapper.

- [x] Task 2 — Publier `state_class` dans `resources/daemon/discovery/publisher.py` (AC: 1, 2, 4, 5)
  - [x] Lire `mapping.reason_details["state_class"]` pour les sensors.
  - [x] Ajouter `payload["state_class"]` uniquement si la valeur est renseignee.
  - [x] Conserver le comportement actuel pour les sensors sans `state_class`.

- [x] Task 3 — Ajouter les tests unitaires attendus (AC: 1, 2, 3, 4, 5, 6, 8)
  - [x] Couvrir `POWER` / `W` -> `device_class=power`, `state_class=measurement`.
  - [x] Couvrir energie cumulative `Wh/kWh` -> `device_class=energy`, `state_class=total_increasing`.
  - [x] Couvrir l'absence de conversion W -> kWh dans le daemon.
  - [x] Couvrir le payload MQTT Discovery avec et sans `state_class`.
  - [x] Couvrir la non-regression des sensors non concernes.

- [x] Task 4 — Gate terrain avant passage a `done` (AC: 7)
  - [x] Deployer/restart/sync sur box Jeedom reelle DEV/TEST.
  - [x] Verifier au moins un payload MQTT Discovery `sensor` power avec `state_class=measurement`.
  - [x] Verifier dans Home Assistant que le capteur est exploitable par HA Energy ou par l'integration Riemann.
    - 2026-06-30 : verification HA par registre WebSocket et REST `/api/states` ; les `unique_id` cibles sont actifs (`disabled_by=null`), plateforme `mqtt`, et exposes avec `state_class` correct. Les `entity_id` reels HA sont ceux deja derives par HA depuis les noms, pas les `object_id` MQTT bruts.
  - [x] Confirmer qu'aucune conversion W -> kWh n'est faite par jeedom2ha.

## Dev Notes

### Source de verite produit

- `pe-epic-13` vient du Sprint Change Proposal `sprint-change-proposal-2026-06-30-energy-dashboard-ha.md`, approuve le 2026-06-30.
- Cette story est la premiere action BMAD attendue pour l'epic 13 ; elle ne code rien pendant `create-story`.
- L'objectif est de rendre exploitables les sensors power/energy deja publies, pas de creer une integration d'energie dans le daemon.

### Regles metadonnees HA

- Puissance instantanee : `device_class = "power"`, unite source attendue `W`, `state_class = "measurement"`.
- Energie cumulative : `device_class = "energy"`, unite source `Wh` ou `kWh`, `state_class = "total_increasing"`.
- La valeur Jeedom reste brute. L'integration temporelle puissance -> energie reste cote Home Assistant, notamment via Riemann ou le dashboard Energy.

### Contraintes de perimetre

- Ne pas modifier `PRODUCT_SCOPE` pour cette story : `sensor` est deja ouvert.
- Ne pas changer les `unique_id` / `object_id` historiques des sensors.
- Ne pas rendre eligible une commande incertaine par simple opportunisme ; l'auto-decouverte par unite pour les commandes non taguees est cadree par Story 13.2.
- Ne pas creer de conversion, d'historique retroactif, ni de source de verite concurrente a Jeedom.

### References

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-30-energy-dashboard-ha.md`
- `_bmad-output/planning-artifacts/epics-projection-engine.md` — Epic 13 / Story 13.1
- `_bmad-output/planning-artifacts/ha-projection-reference.md` — `sensor.mqtt`
- `_bmad-output/implementation-artifacts/9-1-sensor-mapper-publish-sensor-info-numeric-et-capteurs-simples.md`
- `resources/daemon/mapping/sensor.py`
- `resources/daemon/discovery/publisher.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex (`create-story`)

GPT-5 Codex (`dev-story`)

### Debug Log References

- Aucun test ni gate terrain execute pendant `create-story` conformement au workflow BMAD.
- 2026-06-30 — `pytest resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py resources/daemon/tests/unit/test_story_9_1_sensor_mapper.py resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py` → 30 passed.
- 2026-06-30 — `GOLDEN_REGEN=1 pytest resources/daemon/tests/unit/test_story_8_4_golden_file.py` → 1 passed ; snapshot golden realigne sur l'ajout explicite de `state_class`.
- 2026-06-30 — `pytest resources/daemon/tests/unit` → 925 passed, 607 warnings deprecation existants.
- 2026-06-30 — Gate terrain AC7 execute sur box reelle `192.168.1.21` via `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → deploy OK, daemon/MQTT ready, sync OK (`total_eq=284`, `eligible=95`, `published=240`), 318 topics discovery presents apres sync.
- 2026-06-30 — MQTT Discovery terrain : `homeassistant/sensor/jeedom2ha_553_5138/config` et `..._5137/config` portent `device_class=power`, `unit_of_measurement=W`, `state_class=measurement`; `..._5171/config` porte `device_class=energy`, `unit_of_measurement=Wh`, `state_class=total_increasing`; `..._554_5535/config` porte `unit_of_measurement=kWh`, `state_class=total_increasing`.
- 2026-06-30 — Comptage broker terrain : 22 sensors `power`/`W`/`measurement`, 21 sensors `energy`/`Wh|kWh`/`total_increasing`.
- 2026-06-30 — Non-conversion terrain : valeurs MQTT comparees aux `cmd::execCmd()` Jeedom pour 5138/5137/5171/5206/5535 ; les unites sources restent `W`, `Wh`, `kWh`, sans calcul W→kWh dans jeedom2ha.
- 2026-06-30 — Verification HA directe AC7 via WebSocket `config/entity_registry/list` puis REST `/api/states` : `jeedom2ha_eq_553_cmd_5138` -> `sensor.garage_puissance_panneaux_puissance_panneaux` (`power`, `W`, `measurement`), `jeedom2ha_eq_553_cmd_5137` -> `sensor.garage_puissance_reseau_puissance_reseau` (`power`, `W`, `measurement`), `jeedom2ha_eq_553_cmd_5171` -> `sensor.garage_production_panneaux_journaliere_production_panneaux_journaliere` (`energy`, `Wh`, `total_increasing`), `jeedom2ha_eq_554_cmd_5206` -> `sensor.garage_puissance_puissance` (`power`, `W`, `measurement`), `jeedom2ha_eq_554_cmd_5535` -> `sensor.garage_ce_kwh_chauffe_complete_ce_kwh_chauffe_complete` (`energy`, `kWh`, `total_increasing`) ; entites live, activees, non cachees, plateforme `mqtt`.

### Completion Notes List

- 2026-06-30 — workflow lancé : `create-story`. Story 13.1 matérialisée depuis le SCP Energy HA approuvé et l'Epic 13. Statut résultant : `ready-for-dev`.
- 2026-06-30 — workflow lancé : `dev-story`. Story 13.1 passee `in-progress`, implementation daemon livree, validations unitaires daemon terminees. Statut résultant : `review`.
- 2026-06-30 — workflow lancé : `code-review`. Review finale PASS, 0 finding bloquant, tests cibles et golden-file PASS. Statut résultant : `done`.
- `state_class` est porte dans `reason_details` pour `POWER`/`W` (`measurement`) et energy `Wh`/`kWh` (`total_increasing`).
- `DiscoveryPublisher` publie `state_class` uniquement quand le mapper l'a renseigne ; les sensors hors power/energy ne recoivent pas de metadata opportuniste.
- Aucune conversion W -> kWh n'a ete introduite dans le daemon ; les valeurs et unites Jeedom restent brutes.
- Gate terrain AC7 valide : deploy/restart/sync, payloads MQTT Discovery power/energy, comptage broker, absence de conversion et verification directe HA par `unique_id` PASS.

### Senior Developer Review (AI)

- 2026-06-30 — Outcome: APPROVE / 0 finding bloquant.
- Preconditions BMAD: story et `sprint-status.yaml` verifies en `review` avant execution `code-review`.
- AC verifies: payload power `W` publie `state_class=measurement`; payload energy `Wh`/`kWh` publie `state_class=total_increasing`; aucune conversion W -> kWh dans le mapper/publisher/state streaming ; `unique_id`, `object_id` et `state_topic` existants inchanges.
- File List audit: ecart documentaire corrige pendant review en ajoutant les artefacts de planification pe-epic-13 touches par `create-story`.
- Tests review: `pytest resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py resources/daemon/tests/unit/test_story_9_1_sensor_mapper.py resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py resources/daemon/tests/unit/test_story_11_2_eq554_multi_domain.py resources/daemon/tests/unit/test_story_12_1_state_streaming.py` -> 73 passed ; `pytest resources/daemon/tests/unit/test_story_8_4_golden_file.py` -> 1 passed.

### File List

- `_bmad-output/implementation-artifacts/13-1-ha-energy-metadata-pour-sensors-power-energy.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-30-energy-dashboard-ha.md`
- `resources/daemon/mapping/sensor.py`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py`
- `resources/daemon/tests/unit/test_story_9_1_sensor_mapper.py`
- `resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`

### Change Log

- 2026-06-30 — Story creee via workflow `create-story`; statut initial `ready-for-dev`.
- 2026-06-30 — Story implementee via workflow `dev-story`; ajout `state_class` borne pour sensors power/energy, publication MQTT Discovery conditionnelle, tests unitaires et golden-file mis a jour ; statut `review`.
- 2026-06-30 — Gate terrain AC7 execute sur box reelle ; preuves MQTT/Jeedom PASS et verification directe Home Assistant par registre PASS.
- 2026-06-30 — Code review finale PASS ; story passee `done` et sprint-status synchronise.
