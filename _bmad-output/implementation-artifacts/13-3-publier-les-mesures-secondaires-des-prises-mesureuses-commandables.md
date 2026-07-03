# Story 13.3: Publier les mesures secondaires des prises mesureuses commandables

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur Home Assistant,
je veux qu'une prise Jeedom commandable conserve son switch primaire historique tout en exposant ses mesures de puissance/energie comme sensors secondaires,
afin de piloter la prise sans casser mes automatisations HA et d'exploiter ses mesures dans Riemann, Energy ou mes dashboards.

## Acceptance Criteria

1. **Switch primaire preserve.** Given une prise Jeedom commandable deja reconnue comme `switch` par `ENERGY_ON` / `ENERGY_OFF` / `ENERGY_STATE` ou `SWITCH_ON` / `SWITCH_OFF` / `SWITCH_STATE`, When le sync s'execute, Then l'entite primaire reste un `switch` en premiere position de mapping et conserve son comportement historique de pilotage.
2. **Sensor secondaire W/kWh.** Given la meme prise porte au moins une commande Jeedom `info` / `numeric` de mesure fiable en `W`, `Wh` ou `kWh`, When le registry agrege les mappings, Then un `sensor` secondaire est publie sous le meme device HA avec une identite derivee de l'ID commande Jeedom.
3. **Une seule mesure suffit.** Given une prise commandable ne porte qu'une seule mesure fiable `W`, When les mappers sont evalues, Then le sensor secondaire est cree ; le seuil historique `secondary_count > 1` ne bloque pas ce cas.
4. **Aucun changement de unique_id du switch.** Given le switch primaire existait avant cette story avec `ha_unique_id = jeedom2ha_eq_{eq_id}`, When la prise gagne un sensor secondaire, Then le switch garde strictement `ha_unique_id = jeedom2ha_eq_{eq_id}`, `object_id = jeedom2ha_{eq_id}` et son topic de commande historique.
5. **Identite stable des sensors secondaires.** Given une mesure secondaire de commande `{cmd_id}`, When elle est mappee puis publiee, Then elle utilise `ha_unique_id = jeedom2ha_eq_{eq_id}_cmd_{cmd_id}`, `object_id = jeedom2ha_{eq_id}_{cmd_id}`, `node_id = jeedom2ha_{eq_id}_{cmd_id}` et `state_topic = jeedom2ha/{eq_id}/{cmd_id}/state`.
6. **Pas de doublon readback switch.** Given une commande `ENERGY_STATE` ou `SWITCH_STATE` est deja consommee par le switch primaire comme readback, When les sensors secondaires sont construits, Then cette commande n'est pas aussi publiee comme `sensor` ou `binary_sensor` secondaire.
7. **Metadata energie reutilisee.** Given le sensor secondaire est une mesure `W`, `Wh` ou `kWh` fiable, When le payload MQTT Discovery est construit, Then il reutilise les metadonnees livrees par 13.1/13.2 : `W` -> `device_class=power`, `state_class=measurement`; `Wh`/`kWh` cumulatif fiable -> `device_class=energy`, `state_class=total_increasing`.
8. **Device commun.** Given le switch primaire et le sensor secondaire sont publies, When les payloads MQTT Discovery sont inspectes, Then ils partagent le meme bloc `device.identifiers = ["jeedom2ha_{eq_id}"]`.
9. **Perimetre borne.** Given un equipement non commandable ou une commande numeric non fiable (`%`, `H`, texte libre, valeur non cumulative), When le mapping est evalue, Then cette story ne cree pas de sensor power/energy opportuniste et ne contourne pas les exclusions Jeedom/plugin/objet existantes.
10. **Tests multi-entite.** Given la story implementee, When la suite de tests daemon ciblee est lancee, Then elle couvre au minimum `registry.py`, `sensor.py`, `publisher.py` si necessaire, et un cas "Prise garage" ou equivalent `ENERGY_ON/OFF/STATE + Conso W` retourne deux mappings : switch primaire historique + sensor secondaire sans doublon de readback.

## Tasks / Subtasks

- [ ] Task 0 - Pre-flight terrain (DEV/TEST ONLY - pas la release Market)
  - [ ] Dry-run : verifier sans transferer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Selectionner le mode selon l'objectif de la story :
    - Verification disparition entites HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Verifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup termine.`

- [x] Task 1 - Adapter l'agregation multi-entite dans `resources/daemon/mapping/registry.py` (AC: 1, 2, 3, 4)
  - [x] Conserver l'ordre primaire : tous les `switch` primaires restent avant les sensors secondaires.
  - [x] Autoriser `switch + 1 sensor` pour les prises mesureuses ; ne plus exiger `secondary_count > 1` quand un switch primaire actionnable existe et qu'une mesure W/Wh/kWh fiable est presente.
  - [x] Verrouiller la non-regression des cas multi-switch 11.3 et multi-domaine eq554 11.2.

- [x] Task 2 - Borner les sensors secondaires dans `resources/daemon/mapping/sensor.py` (AC: 2, 5, 6, 7, 9)
  - [x] Produire un mapping sensor par commande de mesure W/Wh/kWh fiable avec identifiants par `cmd_id`.
  - [x] Exclure explicitement les commandes readback `ENERGY_STATE` et `SWITCH_STATE` consommees par le switch primaire.
  - [x] Reutiliser `_derive_sensor_metadata()` / `_sensor_reason_details()` ou l'equivalent existant pour eviter une table metadata divergente.
  - [x] Ne pas publier par opportunisme les unites ambigues ou non cumulatives.

- [x] Task 3 - Verifier le publisher et les topics Discovery (AC: 5, 7, 8)
  - [x] Confirmer que `resources/daemon/discovery/publisher.py` accepte deja `node_id`, `object_id`, `state_topic` et `state_class` via `reason_details`.
  - [x] Modifier `publisher.py` uniquement si un test prouve que le sensor secondaire ne publie pas le bon topic/payload.
  - [x] Verifier que le device commun reste derive de l'eqLogic, pas de la commande.

- [x] Task 4 - Ajouter les tests multi-entite cibles (AC: 1-10)
  - [x] Ajouter ou completer un test "Prise garage" : `ENERGY_ON/OFF/STATE + Conso W` -> `switch` primaire + `sensor` secondaire.
  - [x] Assert `ha_unique_id` du switch inchange : `jeedom2ha_eq_{eq_id}`.
  - [x] Assert sensor secondaire : `jeedom2ha_eq_{eq_id}_cmd_{cmd_id}`, `jeedom2ha_{eq_id}_{cmd_id}`, `jeedom2ha/{eq_id}/{cmd_id}/state`.
  - [x] Assert absence de doublon pour `ENERGY_STATE` / `SWITCH_STATE`.
  - [x] Couvrir la regression `switch + 0 sensor`, `switch + unite non fiable`, multi-switch 11.3 et eq554 11.2.

## Dev Notes

### Source de verite produit

- `pe-epic-13` vient du Sprint Change Proposal `sprint-change-proposal-2026-06-30-energy-dashboard-ha.md`, approuve le 2026-06-30.
- Story 13.1 est terminee : le publisher transporte `state_class` uniquement quand le mapper l'a renseigne.
- Story 13.2 est terminee : la detection par unite W/Wh/kWh existe pour les commandes `info` / `numeric` sans `generic_type`, avec garde-fou cumulatif pour `Wh`/`kWh`.
- Story 13.3 ne doit pas creer de conversion W -> kWh, d'historique retroactif ni de mapping configurable manuel.

### Etat actuel utile au dev agent

- `MapperRegistry._map_structural_multi_entity()` agrege aujourd'hui `switch`, `sensor`, `binary_sensor`, mais ne retourne l'agregation que si `len(switch_results) > 1` ou `secondary_count > 1`. Ce seuil bloque le cas simple d'une prise commandable avec une seule mesure `W`.
- `SensorMapper` sait deja produire des sensors par commande avec `ha_unique_id`, `object_id`, `node_id` et `state_topic` derives de `cmd.id` dans les chemins multi-sensor et no-generic par unite.
- `DiscoveryPublisher._build_sensor_payload()` lit deja `object_id`, `state_topic`, `device_class`, `unit_of_measurement` et `state_class` depuis `reason_details`, et rattache le payload au device `jeedom2ha_{eq_id}`.
- Le precedent eq554 (Story 11.2) a montre le pattern multi-domaine et l'anti-doublon `ENERGY_STATE`; la presente story generalise le cas minimal "switch + une mesure" sans reintroduire d'allowlist par ID.

### Dev Agent Guardrails

- Ne pas changer les identifiants du switch primaire : `ha_unique_id`, `object_id`, `command_topic` et `state_topic` historiques doivent rester stables.
- Ne pas deplacer le pilotage de la prise vers un sensor secondaire ; le `switch` reste l'entite primaire actionnable.
- Ne pas publier `ENERGY_STATE` / `SWITCH_STATE` deux fois : ces commandes restent le readback du switch quand elles sont consommees par le switch.
- Ne pas modifier `PRODUCT_SCOPE` : `switch` et `sensor` sont deja ouverts.
- Ne pas utiliser les noms Jeedom comme identifiants ; rester sur les IDs Jeedom stables.
- Ne pas coder de logique specifique a un eq_id. Le predicate doit etre structurel.
- Ne pas lancer de tests terrain ou de scripts pendant `create-story`; ils appartiennent a `dev-story`.

### Guardrail - Deploiement terrain (DEV/TEST ONLY)

- Utiliser exclusivement `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom reelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procedure parallele.
- Reference complete modes + cycle valide terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplace par le script) : `main -> beta -> stable -> Jeedom Market`.

### Project Structure Notes

- Fichiers cibles bornes : `resources/daemon/mapping/registry.py`, `resources/daemon/mapping/sensor.py`, `resources/daemon/discovery/publisher.py` seulement si necessaire, tests daemon sous `resources/daemon/tests/unit/`.
- Tests naturels a etendre ou consulter : `test_story_11_2_eq554_multi_domain.py`, `test_story_11_3_iq_ev_pilotage.py`, `test_story_13_1_sensor_energy_metadata.py`, `test_story_13_2_unit_based_sensor_detection.py`, et un nouveau test cible `test_story_13_3_metering_plug_secondary_sensors.py` si plus lisible.
- Le golden corpus peut devoir etre realigne uniquement si les attentes multi-entite changent pour des prises mesureuses existantes.

### References

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-30-energy-dashboard-ha.md` - Story 13.3, edits precis et AC.
- `_bmad-output/planning-artifacts/epics-projection-engine.md` - Epic 13 / Story 13.3.
- `_bmad-output/planning-artifacts/architecture.md` - IDs Jeedom stables, MQTT Discovery, device commun.
- `_bmad-output/planning-artifacts/architecture-projection-engine.md` - pipeline a 5 etapes, ordre des sous-blocs, conventions `reason_code`.
- `_bmad-output/project-context.md` - principe de moindre nuisance, pas d'identifiants par noms, tests `pytest`.
- `_bmad-output/implementation-artifacts/13-1-ha-energy-metadata-pour-sensors-power-energy.md` - metadata `state_class`.
- `_bmad-output/implementation-artifacts/13-2-auto-detection-des-commandes-w-wh-kwh-sans-generic-type.md` - detection W/Wh/kWh sans `generic_type`.
- `_bmad-output/implementation-artifacts/11-2-chauffe-eau-eq554-detail-routage.md` - precedent multi-domaine et anti-doublon readback.
- `resources/daemon/mapping/registry.py`
- `resources/daemon/mapping/sensor.py`
- `resources/daemon/discovery/publisher.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex (`dev-story`)

### Debug Log References

- Aucun test, script terrain, commande de validation d'implementation, ni modification de code execute pendant `create-story`, conformement aux contraintes utilisateur et au workflow BMAD.
- `pytest resources/daemon/tests/unit/test_story_13_3_metering_plug_secondary_sensors.py resources/daemon/tests/unit/test_story_11_2_eq554_multi_domain.py resources/daemon/tests/unit/test_story_11_3_iq_ev_pilotage.py resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py resources/daemon/tests/unit/test_story_13_2_unit_based_sensor_detection.py` - PASS, 46 tests.
- `pytest resources/daemon/tests/unit` - PASS, 939 tests, warnings de deprecation existants.

### Completion Notes List

- 2026-07-01 - workflow lance : `create-story`. Story 13.3 materialisee depuis l'Epic 13 et le Sprint Change Proposal Energy HA approuve. Statut resultant : `ready-for-dev`.
- 2026-07-01 - sprint-status mis a jour : entree `13-3-publier-les-mesures-secondaires-des-prises-mesureuses-commandables` ajoutee en `ready-for-dev`.
- 2026-07-01 - Dev Agent Record renseigne ; aucune tache dev cochee et aucune preuve de run dev ajoutee.
- 2026-07-01 - workflow lance : `dev-story`. Preconditions verifiees : story et sprint-status en `ready-for-dev`. Statut resultant initial : `in-progress`.
- 2026-07-01 - `registry.py` agrege desormais le cas `switch + 1 sensor` quand le sensor secondaire est une mesure `power`/`energy`, sans changer l'ordre primaire.
- 2026-07-01 - `sensor.py` exclut les readbacks actionnables effectivement consommes par le switch et conserve les identifiants secondaires par commande `jeedom2ha_eq_{eq_id}_cmd_{cmd_id}`.
- 2026-07-01 - Tests locaux cibles et suite daemon unitaire PASS. Aucun deploy terrain lance pendant cette carte. Statut resultant : `review`.
- 2026-07-01 - workflow lance : `code-review`. Review finale APPROVE : aucun finding HIGH/MEDIUM/LOW. Statut resultant : `done`.

### File List

- `_bmad-output/implementation-artifacts/13-3-publier-les-mesures-secondaires-des-prises-mesureuses-commandables.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/mapping/registry.py`
- `resources/daemon/mapping/sensor.py`
- `resources/daemon/tests/unit/test_story_11_2_eq554_multi_domain.py`
- `resources/daemon/tests/unit/test_story_13_3_metering_plug_secondary_sensors.py`

## Senior Developer Review (AI)

### Review Summary

APPROVE - Aucun finding.

Points verifies :
- Switch primaire preserve : `MapperRegistry` retourne le switch avant les sensors, et les tests assertent `ha_unique_id = jeedom2ha_eq_{eq_id}` sans `object_id` secondaire sur le switch.
- Aucun doublon readback : `ENERGY_STATE` est exclu des sensors secondaires quand il est consomme par le switch ; `SWITCH_STATE` reste couvert par les regressions 11.3 / `BinarySensorMapper` et les chemins multi-switch.
- Sensors secondaires rattaches au meme device HA : le publisher garde `device.identifiers = ["jeedom2ha_{eq_id}"]` tout en utilisant `node_id`, `object_id` et `state_topic` par `cmd_id`.
- Depublication / lifecycle compatible : `_collect_unpublish_node_ids()` et `unpublish_by_eq_id()` couvrent les mappings secondaires via `additional_mappings`, avec regression 11.2 domain-aware toujours verte.
- Tests de non-regression : suite cible 13.3 + 11.2 + 11.3 + 13.1 + 13.2 verte, puis suite unitaire daemon complete verte.

### Verification

- `pytest resources/daemon/tests/unit/test_story_13_3_metering_plug_secondary_sensors.py resources/daemon/tests/unit/test_story_11_2_eq554_multi_domain.py resources/daemon/tests/unit/test_story_11_3_iq_ev_pilotage.py resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py resources/daemon/tests/unit/test_story_13_2_unit_based_sensor_detection.py` - PASS, 46 tests.
- `pytest resources/daemon/tests/unit` - PASS, 939 tests, warnings de deprecation existants.

### Change Log

- 2026-07-01 - Story creee via workflow `create-story`; statut initial `ready-for-dev`.
- 2026-07-01 - Dev-story : aggregation `switch + sensor` pour prises mesureuses, exclusion readback actionnable, tests 13.3 ajoutes, story passee en `review`.
- 2026-07-01 - Code-review finale APPROVE ; story passee en `done`.
