# Story 13.2: Auto-detection des commandes W/Wh/kWh sans generic_type

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur Home Assistant,
je veux que jeedom2ha publie les commandes Jeedom info numeric non taguees quand leur unite W/Wh/kWh suffit a etablir une semantique HA fiable,
afin que mes mesures de puissance et d'energie deja presentes dans Jeedom deviennent exploitables sans corriger manuellement tous les `generic_type`.

## Acceptance Criteria

1. **Puissance sans generic_type.** Given un eqLogic actif, non exclu, sans `generic_type`, avec une commande Jeedom `info` / `numeric` sans `generic_type` et `unit="W"`, When le sync evalue l'equipement puis le mapper sensor, Then l'equipement devient eligible par unite fiable et un `sensor` HA est produit avec `device_class="power"`, `unit_of_measurement="W"` et `state_class="measurement"`.
2. **Energie Wh/kWh seulement si cumulative fiable.** Given une commande Jeedom `info` / `numeric` sans `generic_type` et `unit="Wh"` ou `unit="kWh"`, When la semantique cumulative est fiable pour cette commande, Then le sensor produit porte `device_class="energy"`, conserve l'unite source et porte `state_class="total_increasing"` ; When la commande n'est pas cumulative de facon fiable, Then aucune classe energy ni `state_class` energy n'est inventee.
3. **Unites non fiables sans classe inventee.** Given une commande non taguee avec `unit="%"`, `unit="H"` ou une unite texte libre non reconnue, When le mapping sensor est evalue, Then jeedom2ha ne deduit pas de `device_class` power/energy, ne renseigne pas de `state_class` opportuniste et ne rend pas l'equipement eligible par ce seul chemin.
4. **Exclusions prioritaires.** Given un equipement exclu par Jeedom, par plugin ou par objet, When il porte pourtant une commande `W`, `Wh` ou `kWh`, Then l'exclusion existante reste prioritaire et l'equipement reste non eligible avec le `reason_code` d'exclusion existant.
5. **Generalisation hors MSunPV bornee.** Given un eqLogic hors `MULTI_SENSOR_EQ_TYPES` sans `generic_type` mais avec une commande info numeric W/Wh/kWh fiable, When `assess_eligibility()` est appele, Then il peut devenir eligible par cette unite fiable sans dependance a l'allowlist MSunPV ; les cas MSunPV existants restent non regresses.
6. **Mono-sensor reutilise la derivation existante.** Given un eqLogic mono-sensor avec une seule mesure W/Wh/kWh exploitable, When `SensorMapper._map_single()` est utilise, Then il reutilise la meme logique de metadata que le chemin multi-sensor (`_derive_sensor_metadata()` ou equivalent extrait) au lieu de dupliquer une table divergente.
7. **Reason codes explicites.** Given un sensor non tague publie par unite, When le `MappingResult` est produit, Then son `reason_code` distingue le chemin par unite, par exemple `sensor_unit_power` ou `sensor_unit_energy`, sans collision avec les reason codes existants `sensor_power` / `sensor_consumption`.
8. **Tests cibles.** Given la story implementee, When la suite de tests daemon ciblee est lancee, Then elle couvre `sensor.py`, `topology.py` et les regressions MSunPV / 13.1 : W sans `generic_type` -> power, Wh/kWh fiables -> energy, `%` / `H` / texte libre -> pas de classe inventee, exclusions prioritaires, et non-regression des sensors tagues.

## Tasks / Subtasks

- [x] Task 0 - Pre-flight terrain (DEV/TEST ONLY - pas la release Market)
  - [x] Dry-run : verifier sans transferer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Selectionner le mode selon l'objectif de la story :
    - Verification disparition entites HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Verifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup termine.` / simulation dry-run terminee sans transfert.

- [x] Task 1 - Etendre l'eligibilite par unite fiable dans `resources/daemon/models/topology.py` (AC: 1, 3, 4, 5)
  - [x] Ajouter une detection explicite des commandes `info` / `numeric` sans `generic_type` dont l'unite est une unite energie fiable (`W`, `Wh`, `kWh`; `kW` seulement si conserve dans le perimetre existant).
  - [x] Remplacer le contournement limite a `MULTI_SENSOR_EQ_TYPES` par une eligibilite additive par unite fiable.
  - [x] Conserver l'ordre canonique : exclusion eqLogic/plugin/objet > desactive > sans commande > chemin par `generic_type` ou unite fiable.
  - [x] Ne pas rendre eligible par ce chemin les unites `%`, `H` ou texte libre.

- [x] Task 2 - Generaliser le mapping sensor par unite dans `resources/daemon/mapping/sensor.py` (AC: 1, 2, 3, 6, 7)
  - [x] Extraire/reutiliser la logique `_derive_sensor_metadata()` pour le chemin mono-sensor et multi-sensor.
  - [x] Autoriser `_map_single()` a choisir une commande `info` / `numeric` sans `generic_type` quand son unite suffit a deduire power/energy.
  - [x] Associer `W` a `device_class="power"` et `state_class="measurement"` via le mecanisme livre en Story 13.1.
  - [x] Associer `Wh` / `kWh` a `device_class="energy"` et `state_class="total_increasing"` seulement quand la commande est cumulative de facon fiable.
  - [x] Produire des `reason_code` distincts pour le chemin par unite (`sensor_unit_power`, `sensor_unit_energy` ou equivalent).

- [x] Task 3 - Ajouter les tests unitaires cibles (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [x] Ajouter un test `topology.py` : eqLogic sans `generic_type`, commande W -> eligible.
  - [x] Ajouter un test `topology.py` : eqLogic exclu avec commande W/kWh -> reste exclu avec le reason code existant.
  - [x] Ajouter un test `sensor.py` : commande W sans `generic_type` -> sensor power + state_class measurement.
  - [x] Ajouter un test `sensor.py` : commande Wh/kWh cumulative fiable -> sensor energy + state_class total_increasing.
  - [x] Ajouter des tests negatifs : `%`, `H`, unite texte libre -> pas de classe power/energy inventee.
  - [x] Conserver les tests 11.1 MSunPV et 13.1 energy metadata comme regressions ciblees.

## Dev Notes

### Source de verite produit

- `pe-epic-13` vient du Sprint Change Proposal `sprint-change-proposal-2026-06-30-energy-dashboard-ha.md`, approuve le 2026-06-30.
- Story 13.1 est terminee : elle a ajoute le transport de `state_class` pour les sensors power/energy et le publisher ne publie `state_class` que si le mapper le renseigne.
- Story 13.2 ne doit pas creer une integration d'energie dans jeedom2ha : les valeurs et unites Jeedom restent brutes ; l'integration puissance -> energie reste cote Home Assistant.

### Etat actuel utile au dev agent

- `resources/daemon/mapping/sensor.py` contient deja `_UNIT_DEVICE_CLASS = {"W": "power", "kW": "power", "Wh": "energy", "kWh": "energy", "V": "voltage", "A": "current"}` et `_derive_sensor_metadata()`, mais `_map_single()` ignore encore les commandes sans `generic_type`.
- Le chemin multi-sensor utilise deja l'inference par unite, notamment pour MSunPV, et passe par `_sensor_reason_details()` pour ajouter `state_class` quand applicable.
- `resources/daemon/models/topology.py` garde aujourd'hui une exception d'eligibilite sans `generic_type` limitee a `MULTI_SENSOR_EQ_TYPES = {"msunpv"}` et `_has_numeric_info_command()`. Cette story doit generaliser par unite fiable, pas par plugin.
- Les exclusions sont deja normalisees via `_EXCLUSION_SOURCE_TO_REASON` (`excluded_eqlogic`, `excluded_plugin`, `excluded_object`) et doivent rester prioritaires.

### Dev Agent Guardrails

- Ne pas modifier `PRODUCT_SCOPE` : `sensor` est deja ouvert.
- Ne pas changer les identifiants historiques des sensors tagues (`ha_unique_id`, `object_id`, `state_topic`).
- Ne pas deduire `energy` sur une unite non cumulative ou ambigue. Si la fiabilite cumulative ne peut pas etre etablie dans les donnees disponibles, publier sans classe inventee ou ne pas publier par ce chemin.
- Ne pas introduire de conversion W -> kWh, d'historique retroactif, ni de calcul d'integration dans le daemon.
- Ne pas utiliser les noms Jeedom comme identifiants ; rester sur les IDs Jeedom stables.

### Guardrail - Deploiement terrain (DEV/TEST ONLY)

- Utiliser exclusivement `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom reelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procedure parallele.
- Reference complete modes + cycle valide terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplace par le script) : `main -> beta -> stable -> Jeedom Market`.

### Project Structure Notes

- Fichiers cibles explicitement bornes : `resources/daemon/mapping/sensor.py`, `resources/daemon/models/topology.py`, tests daemon sous `resources/daemon/tests/unit/`.
- Les tests naturels a etendre sont `test_story_13_1_sensor_energy_metadata.py`, `test_story_11_1_msunpv_multi_sensor.py`, `test_story_9_1_sensor_mapper.py` et/ou `test_step1_eligibility.py`, ou un nouveau fichier cible `test_story_13_2_unit_based_sensor_detection.py`.
- `resources/daemon/mapping/registry.py` ne devrait pas etre necessaire pour cette story ; les prises mesureuses multi-entites sont cadrees par Story 13.3.

### References

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-30-energy-dashboard-ha.md` - Story 13.2, fichiers cibles et AC.
- `_bmad-output/planning-artifacts/epics-projection-engine.md` - Epic 13 / Story 13.2.
- `_bmad-output/planning-artifacts/architecture.md` - Jeedom source de verite, IDs stables, MQTT Discovery, tests `pytest`.
- `_bmad-output/planning-artifacts/architecture-projection-engine.md` - pipeline a 5 etapes, ordre des sous-blocs, conventions `reason_code`.
- `_bmad-output/project-context.md` - regles critiques : fallback raisonne seulement quand une representation honnete existe.
- `_bmad-output/implementation-artifacts/13-1-ha-energy-metadata-pour-sensors-power-energy.md` - contexte precedent et metadata `state_class`.
- `_bmad-output/implementation-artifacts/11-1-msunpv-routeursolaire-sensors-lecture-seule.md` - precedent sans `generic_type` borne a MSunPV.
- `resources/daemon/mapping/sensor.py`
- `resources/daemon/models/topology.py`
- `resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py`
- `resources/daemon/tests/unit/test_step1_eligibility.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex (`create-story`, `dev-story`)

### Debug Log References

- Pendant `create-story` : aucun test, script terrain, ni validation d'implementation execute, conformement au workflow BMAD et a la contrainte utilisateur "Ne code rien".
- Pendant `dev-story` : `python3 -m pytest resources/daemon/tests/unit/test_story_13_2_unit_based_sensor_detection.py resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py resources/daemon/tests/unit/test_step1_eligibility.py` -> 42 passed, 10 warnings.
- Pendant `dev-story` : `python3 -m pytest resources/daemon/tests/unit` -> 932 passed, 607 warnings.
- Pendant `dev-story` : `./scripts/deploy-to-box.sh --dry-run` -> SSH OK, sudo OK, rsync simulation complete, no files transferred.
- Pendant `code-review` : finding corrige - le chemin no-generic `Wh`/`kWh` deduisait `energy` et `state_class=total_increasing` sans preuve cumulative fiable.
- Pendant `code-review` : `python3 -m pytest resources/daemon/tests/unit/test_story_13_2_unit_based_sensor_detection.py resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py resources/daemon/tests/unit/test_story_11_2_eq554_multi_domain.py resources/daemon/tests/unit/test_step1_eligibility.py` -> 64 passed, 15 warnings.
- Pendant `code-review` : `python3 -m pytest resources/daemon/tests/unit` -> 934 passed, 607 warnings.
- Pendant `code-review` gate terrain : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` -> PASS (`Deploy complete.`, sync `total_eq=284 eligible=96 published=241`, 318 topics discovery presents apres sync).
- Pendant `code-review` gate terrain : preuves MQTT retenues - `homeassistant/sensor/jeedom2ha_461_4147/config` publie `device_class=power`, `unit_of_measurement=W`, `state_class=measurement`; `homeassistant/sensor/jeedom2ha_548_5352/config` publie `device_class=energy`, `unit_of_measurement=Wh`, `state_class=total_increasing`; eq553 conserve `W -> power`, `Wh -> energy`, `% -> aucune device_class`.
- Post-review investigation HA : reproduction sur capture terrain eq583 #5992 `Énergie session` ; avant correctif, le garde-fou cumulatif ne reconnaissait pas le libelle accentue/session et supprimait `device_class/state_class`. `pytest resources/daemon/tests/unit/test_story_13_2_unit_based_sensor_detection.py resources/daemon/tests/unit/test_story_13_3_metering_plug_secondary_sensors.py` -> 15 passed.
- Post-review regression ciblee : `pytest resources/daemon/tests/unit/test_story_11_3_iq_ev_pilotage.py resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py resources/daemon/tests/unit/test_story_13_2_unit_based_sensor_detection.py resources/daemon/tests/unit/test_story_13_3_metering_plug_secondary_sensors.py` -> 27 passed.

### Completion Notes List

- 2026-06-30 - workflow lance : `create-story`. Story 13.2 materialisee depuis l'Epic 13 et le Sprint Change Proposal Energy HA approuve. Statut resultant : `ready-for-dev`.
- 2026-06-30 - sprint-status mis a jour : entree `13-2-auto-detection-des-commandes-w-wh-kwh-sans-generic-type` ajoutee en `ready-for-dev`.
- 2026-06-30 - Dev Agent Record renseigne ; aucune tache dev cochee et aucune preuve de run dev ajoutee.
- 2026-07-01 - workflow lance : `dev-story`. Preconditions verifiees (`ready-for-dev`) puis statut passe a `in-progress`.
- 2026-07-01 - `topology.py` etend l'eligibilite aux commandes info/numeric non taguees dont l'unite est exactement `W`, `Wh` ou `kWh`, apres exclusions/desactivation/no_commands et sans elargir `%`, `H` ou texte libre.
- 2026-07-01 - `sensor.py` reutilise `_derive_sensor_metadata()` pour le chemin mono-sensor no-generic et produit des reason codes dedies `sensor_unit_power` / `sensor_unit_energy` avec identifiants par cmd Jeedom.
- 2026-07-01 - Tests cibles et suite unit daemon completes PASS ; dry-run officiel PASS sans transfert.
- 2026-07-01 - workflow `dev-story` termine. Statut resultant : `review` (pas `done`, en attente de code-review).
- 2026-07-01 - workflow lance : `code-review`. Finding HIGH corrige : les unites `Wh`/`kWh` non taguees ne deduisent plus `energy` sans indice cumulatif fiable ; une commande `kWh` non cumulative reste ineligible/non mappee par ce chemin.
- 2026-07-01 - Review finale validee : pas d'eligibilite trop large, pas de `device_class` invente sur unites non fiables/non cumulatives, exclusions prioritaires conservees, MSunPV eq553 et eq554 non regresses, tests fiables/non fiables ajoutes, suite unit daemon complete PASS et gate terrain PASS. Statut resultant : `done`.
- 2026-07-01 - Correctif post-investigation HA : normalisation accent-insensitive des libelles cumulatifs et marqueur `session` ajoute, pour conserver `state_class=total_increasing` sur `Énergie session` (#5992) sans accepter les mesures Wh/kWh instantanees.

### File List

- `_bmad-output/implementation-artifacts/13-2-auto-detection-des-commandes-w-wh-kwh-sans-generic-type.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/models/topology.py`
- `resources/daemon/mapping/sensor.py`
- `resources/daemon/tests/unit/test_story_13_2_unit_based_sensor_detection.py`
- `resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py`

### Change Log

- 2026-06-30 - Story creee via workflow `create-story`; statut initial `ready-for-dev`.
- 2026-07-01 - Story implementee via workflow `dev-story`; statut final `review`.
- 2026-07-01 - Code review finale : correction du garde-fou cumulatif `Wh`/`kWh`; statut final `done`.
- 2026-07-01 - Correctif post-investigation HA : `Énergie session` reconnue comme energie cumulative fiable malgre accent/session ; tests 13.2/13.3 et regressions 11.3/13.1/13.2/13.3 PASS.
