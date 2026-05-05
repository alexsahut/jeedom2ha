# Story 9.1 : SensorMapper + publish_sensor — Info numeric et capteurs simples

Status: ready-for-dev

## Story

En tant que mainteneur,
je veux un `SensorMapper` qui projette les commandes Jeedom de type `Info` numeric (temperature, humidite, puissance, luminosite, etc.) en entite HA `sensor`,
afin que les capteurs simples deja types correctement dans Jeedom apparaissent automatiquement dans Home Assistant.

## Acceptance Criteria

**AC1 — Mapping sensor nominal**
**Given** un eqLogic Jeedom avec au moins une commande Info numeric typee (TEMPERATURE, HUMIDITY, POWER, CONSUMPTION, VOLTAGE, etc.)
**When** le `SensorMapper` est invoque dans la cascade registry-driven
**Then** un `MappingResult` non-`None` est produit avec :
- `ha_entity_type = "sensor"`
- `state_topic` derive de la commande source (`jeedom2ha/{eq_id}/state`)
- `device_class` resolu par le type generique via la table de mapping
- `unit_of_measurement` resolu par le sous-type
- `capabilities = SensorCapabilities(has_state=True)`

**AC2 — Validation projection**
**Given** le mapping issu de `SensorMapper`
**When** il passe par `validate_projection()` (Story 3.2 + Story 7.3)
**Then** `is_valid = True` sur les cas nominaux
**And** les required_fields de `sensor.mqtt` sont satisfaits : `availability > keys > topic`, `platform`, `state_topic`
[Source: _bmad-output/planning-artifacts/ha-projection-reference.md#sensor.mqtt]

**AC3 — Publication MQTT Discovery**
**Given** la methode `publish_sensor` du `DiscoveryPublisher`
**When** elle est appelee sur un mapping sensor valide
**Then** elle produit un payload MQTT Discovery conforme a `sensor.mqtt` (topic = `homeassistant/sensor/jeedom2ha_{eq_id}/config`)
**And** le payload inclut : `name`, `unique_id`, `object_id`, `state_topic`, `device_class`, `unit_of_measurement`, `platform`, `device`, `availability`
**And** elle est enregistree dans `PublisherRegistry` sous la cle `"sensor"`

**AC4 — API statique `PublisherRegistry.known_types()` (PE8-AI-03)**
**Given** le `PublisherRegistry`
**When** `PublisherRegistry.known_types()` est appele (classmethod)
**Then** il retourne la liste statique des types connus (`["light", "cover", "switch", "sensor"]`) sans necessiter d'instance
**And** `http_server.py:_build_mapping_counters_from_publisher_registry()` utilise cette API au lieu d'instancier `PublisherRegistry(DiscoveryPublisher(None))`

**AC5 — Extension golden-file (PE8-AI-04)**
**Given** le golden-file Story 8.4
**When** il est etendu avec 5 equipements sensor representatifs (IDs 7000-7004)
**Then** la non-regression du corpus initial (30 equipements IDs 1000-6001) reste verte
**And** les 30 equipements initiaux ne sont pas modifies

**AC6 — Enregistrement dans MapperRegistry**
**Given** le `MapperRegistry`
**When** il est initialise
**Then** `SensorMapper` est present dans la cascade AVANT `FallbackMapper` (slot terminal)
**And** l'ordre est : `LightMapper`, `CoverMapper`, `SwitchMapper`, `SensorMapper`, `FallbackMapper`

**AC7 — Cas d'exclusion : pas de capture des commandes deja traitees**
**Given** un eqLogic avec des commandes LIGHT_*, FLAP_* ou ENERGY_* (deja couvertes par les mappers riches)
**When** `SensorMapper` est invoque APRES ces mappers dans la cascade
**Then** il ne produit pas de doublon (puisque les mappers riches retournent un resultat non-None AVANT dans la cascade)

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : verifier sans transferer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Selectionner le mode selon l'objectif de la story :
    - Verification disparition entites HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Verifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup termine.`

- [ ] Task 1 — API statique `PublisherRegistry.known_types()` (AC4, PE8-AI-03)
  - [ ] 1.1 Ajouter `@classmethod known_types()` a `PublisherRegistry` dans `resources/daemon/discovery/registry.py`
  - [ ] 1.2 La liste retournee doit etre `["light", "cover", "switch"]` avant enregistrement de `sensor` (maintenue en dur + mise a jour quand le constructeur enregistre un nouveau type)
  - [ ] 1.3 Refactorer `http_server.py:_build_mapping_counters_from_publisher_registry()` pour utiliser `PublisherRegistry.known_types()` au lieu d'instancier `PublisherRegistry(DiscoveryPublisher(None))`
  - [ ] 1.4 Verifier que les tests Story 8.3 (`test_story_8_3_http_server_dispatch.py`) restent verts apres refactor
  - [ ] 1.5 Ajouter un test unitaire pour `known_types()` retournant la bonne liste

- [ ] Task 2 — Table de mapping Jeedom Info numeric → HA device_class (AC1)
  - [ ] 2.1 Creer `resources/daemon/mapping/sensor.py`
  - [ ] 2.2 Definir la table `_SENSOR_GENERIC_TYPE_MAP` : dictionnaire `generic_code → (device_class, unit_of_measurement)`
  - [ ] 2.3 Table derivee de `ha-projection-reference.md` section 3 (types Info, subtype numeric) :
    - `TEMPERATURE` → `("temperature", "°C")`
    - `HUMIDITY` → `("humidity", "%")`
    - `POWER` → `("power", "W")`
    - `CONSUMPTION` → `("energy", "kWh")`
    - `VOLTAGE` → `("voltage", "V")`
    - `AIR_QUALITY` → `("aqi", None)`
    - `BRIGHTNESS` → `("illuminance", "lx")`
    - `UV` → `("irradiance", None)`
    - `CO2` → `("carbon_dioxide", "ppm")`
    - `CO` → `("carbon_monoxide", "ppm")`
    - `NOISE` → `("sound_pressure", "dB")`
    - `PRESSURE` → `("atmospheric_pressure", "hPa")`
    - `DEPTH` → `("distance", "m")`
    - `DISTANCE` → `("distance", "m")`
    - `BATTERY` → `("battery", "%")`
    - `VOLUME` → `(None, None)` (multimedia, pas assez specifique pour un device_class)
    - `WEATHER_TEMPERATURE` → `("temperature", "°C")`
    - `WEATHER_HUMIDITY` → `("humidity", "%")`
    - `WEATHER_PRESSURE` → `("atmospheric_pressure", "hPa")`
    - `WIND_SPEED` → `("wind_speed", "km/h")`
    - `WEATHER_WIND_SPEED` → `("wind_speed", "km/h")`
    - `RAIN_TOTAL` → `("precipitation", "mm")`
    - `RAIN_CURRENT` → `("precipitation_intensity", "mm/h")`
    - `THERMOSTAT_TEMPERATURE` → `("temperature", "°C")`
    - `THERMOSTAT_SETPOINT` → `("temperature", "°C")`
    - `THERMOSTAT_HUMIDITY` → `("humidity", "%")`
    - `THERMOSTAT_TEMPERATURE_OUTDOOR` → `("temperature", "°C")`
    - `FAN_SPEED_STATE` → `(None, "rpm")`
    - `ROTATION_STATE` → `(None, "rpm")`
  - [ ] 2.4 Les types generiques avec `command_kind = Action` sont exclus (Info seulement)
  - [ ] 2.5 Les types generiques avec `subtypes = binary` sont exclus (reserves a Story 9.2 BinarySensorMapper)

- [ ] Task 3 — Implementation de `SensorMapper` (AC1, AC6)
  - [ ] 3.1 Classe `SensorMapper` dans `resources/daemon/mapping/sensor.py` avec methode `map(eq, snapshot) -> Optional[MappingResult]`
  - [ ] 3.2 Logique de `map()` :
    - Iterer les commandes de l'eqLogic
    - Selectionner la premiere commande Info dont `generic_type` est dans `_SENSOR_GENERIC_TYPE_MAP` et dont le subtype inclut `numeric` (exclure `binary`)
    - Construire `MappingResult` avec :
      - `ha_entity_type = "sensor"`
      - `confidence = "sure"` (type generique explicitement type)
      - `reason_code = "sensor_{generic_type_lower}"` (ex. `"sensor_temperature"`)
      - `capabilities = SensorCapabilities(has_state=True)`
      - `commands = {generic_type: cmd}`
      - `ha_unique_id = f"jeedom2ha_eq_{eq.id}"`
      - `ha_name = eq.name`
      - `suggested_area = snapshot.get_suggested_area(eq.id)`
  - [ ] 3.3 Si aucune commande Info numeric matchant la table → retourner `None`
  - [ ] 3.4 Stocker `device_class` et `unit_of_measurement` dans `reason_details` pour usage par le publisher

- [ ] Task 4 — Enregistrement dans `MapperRegistry` (AC6)
  - [ ] 4.1 Modifier `resources/daemon/mapping/registry.py` : importer `SensorMapper`
  - [ ] 4.2 Inserer `SensorMapper()` AVANT `FallbackMapper()` dans `self._mappers`
  - [ ] 4.3 Ordre final : `[LightMapper(), CoverMapper(), SwitchMapper(), SensorMapper(), FallbackMapper()]`

- [ ] Task 5 — Implementation de `publish_sensor` (AC3)
  - [ ] 5.1 Ajouter methode `async publish_sensor(mapping, snapshot) -> bool` dans `DiscoveryPublisher` (`resources/daemon/discovery/publisher.py`)
  - [ ] 5.2 Builder de payload `_build_sensor_payload(mapping, snapshot)` :
    - `name`, `unique_id`, `object_id`
    - `state_topic = f"jeedom2ha/{eq_id}/state"`
    - `device_class` depuis `mapping.reason_details["device_class"]`
    - `unit_of_measurement` depuis `mapping.reason_details["unit_of_measurement"]` (si non-None)
    - `device` bloc via `_build_device_block(mapping, snapshot)`
    - `availability` via `_build_availability_fields(mapping, snapshot)`
    - `platform = "mqtt"`
  - [ ] 5.3 Topic MQTT Discovery : `homeassistant/sensor/jeedom2ha_{eq_id}/config`
  - [ ] 5.4 Pattern identique a `publish_light`/`publish_cover`/`publish_switch` : log info, publish QoS 1 retain

- [ ] Task 6 — Enregistrement dans `PublisherRegistry` (AC3, AC4)
  - [ ] 6.1 Modifier `resources/daemon/discovery/registry.py` : ajouter `"sensor": publisher.publish_sensor` dans le dict `_publishers` du constructeur
  - [ ] 6.2 Mettre a jour `known_types()` pour inclure `"sensor"` dans la liste retournee

- [ ] Task 7 — Extension du golden-file (AC5, PE8-AI-04)
  - [ ] 7.1 Ajouter 5 eqLogics sensor dans `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json` :
    - `7000` : TEMPERATURE (capteur temperature salon) — device_class=temperature, unit=°C
    - `7001` : HUMIDITY (capteur humidite sdb) — device_class=humidity, unit=%
    - `7002` : POWER (compteur puissance elec) — device_class=power, unit=W
    - `7003` : CO2 (capteur qualite air) — device_class=carbon_dioxide, unit=ppm
    - `7004` : BRIGHTNESS (capteur luminosite) — device_class=illuminance, unit=lx
  - [ ] 7.2 Ajouter les entrees correspondantes dans `expected_sync_snapshot.json` (diagnostics + mapping_summary counters)
  - [ ] 7.3 Verifier que `test_story_8_4_golden_file.py` passe avec les 35 equipements (30 initiaux + 5 nouveaux)
  - [ ] 7.4 NE PAS modifier les 30 equipements initiaux (IDs 1000-6001)
  - [ ] 7.5 Mettre a jour `resources/daemon/tests/fixtures/golden_corpus/README.md` avec la section sensor

- [ ] Task 8 — Tests unitaires SensorMapper + publish_sensor (AC1, AC2, AC3)
  - [ ] 8.1 Creer `resources/daemon/tests/unit/test_story_9_1_sensor_mapper.py`
  - [ ] 8.2 Tests SensorMapper :
    - Test nominal : eqLogic avec TEMPERATURE → MappingResult sensor
    - Test nominal : eqLogic avec HUMIDITY → MappingResult sensor
    - Test nominal : eqLogic avec POWER → MappingResult sensor
    - Test negatif : eqLogic sans commande Info numeric matchante → None
    - Test exclusion : eqLogic avec seulement des commandes binary → None (reserve 9.2)
    - Test validation : MappingResult passe validate_projection() → is_valid=True
  - [ ] 8.3 Tests publish_sensor :
    - Test payload structure : tous les champs requis presents
    - Test device_class et unit_of_measurement correctement remontes
    - Test topic format correct
  - [ ] 8.4 Test known_types() : retourne la bonne liste apres enregistrement sensor

- [ ] Task 9 — Validation non-regression + terrain (AC2, AC5, AC7)
  - [ ] 9.1 Lancer la suite complete : `pytest resources/daemon/tests/` — zero regression
  - [ ] 9.2 Lancer specifiquement `test_story_8_4_golden_file.py` — PASS avec 35 equipements
  - [ ] 9.3 Deployer sur box Alexandre et verifier que les nouveaux sensors apparaissent dans HA Discovery
  - [ ] 9.4 Relever le comptage : baseline 30 → attendu > 30 publies (nouveaux sensors en plus)

## Dev Notes

### Architecture et patterns a suivre

- **Pattern mapper** : suivre exactement `mapping/light.py` comme reference architecturale (interface `map(eq, snapshot) -> Optional[MappingResult]`, dataclass capabilities, reason_code)
- **Pattern publisher** : suivre `publish_light` / `publish_cover` / `publish_switch` (methode async, payload builder prive, QoS 1 retain, logging structure)
- **Cascade registry-driven** : un seul mapper "gagne" par eqLogic — le premier non-None dans l'ordre du registre. SensorMapper s'inserant APRES les mappers riches (light/cover/switch), il ne capturera que les eqLogics non deja mappes.
- **device_class / unit_of_measurement** : transportes dans `reason_details` du MappingResult (pas de nouveau champ au dataclass pour ne pas casser l'interface commune)
- **SensorCapabilities** : deja defini dans `models/mapping.py` (Story 7.2), ne pas le modifier — utiliser `SensorCapabilities(has_state=True)` directement

### Source de verite des contraintes HA sensor.mqtt

Required fields (section 2 de `ha-projection-reference.md`) :
- `availability > keys > topic` (string, required)
- `platform` (string, required, valeur = `"mqtt"` pour discovery)
- `state_topic` (string, required)

Champs optionnels pertinents pour sensor :
- `device_class` : permet a HA de choisir l'icone et le formatage
- `unit_of_measurement` : permet a HA d'afficher l'unite et d'agreger les statistiques
- `state_class` : `"measurement"` pour les capteurs instantanes (temperature, humidite, puissance)

[Source: _bmad-output/planning-artifacts/ha-projection-reference.md#sensor.mqtt]

### Contraintes structurelles

- `PRODUCT_SCOPE` inclut deja `"sensor"` depuis Story 7.4 — **ne pas le modifier**
- `HA_COMPONENT_REGISTRY["sensor"]` existe deja (Story 7.2) avec `required_capabilities: ["has_state"]` — **ne pas le modifier**
- `validate_projection()` fonctionne deja pour `sensor` via `_resolve_capability("has_state", SensorCapabilities)` — **ne pas le modifier**
- Le `FallbackMapper` actuel est no-op (retourne None) — il sera cable en Story 9.4, ne pas le toucher

### Action Items retro pe-epic-8 integres

| AI | Description | Critere de sortie |
|---|---|---|
| PE8-AI-03 | `PublisherRegistry.known_types()` classmethod | L'inspection des types connus ne depend plus d'une instance `PublisherRegistry(DiscoveryPublisher(None))` |
| PE8-AI-04 | Extension disciplinee du golden-file | 5 equipements sensor (IDs 7000-7004) ajoutes sans modifier les 30 initiaux |

### Contexte de la cascade complete post-9.1

```
MapperRegistry._mappers = [
    LightMapper(),       # LIGHT_* → ha_entity_type="light"
    CoverMapper(),       # FLAP_* → ha_entity_type="cover"
    SwitchMapper(),      # ENERGY_* → ha_entity_type="switch"
    SensorMapper(),      # Info numeric types → ha_entity_type="sensor"  ← NOUVEAU
    FallbackMapper(),    # Terminal no-op (cable en 9.4)
]
```

### Intelligence Story 9.0 (story precedente)

Story 9.0 (prefixe pe-epic-9) a :
- Rendu dynamique le calcul du total publie dans `plugin_info/configuration.php` (somme de toutes les cles `*_published`)
- Rendu dynamique le comptage dans `scripts/deploy-to-box.sh` via jq
- Scope strict : aucun code daemon Python modifie
- Consequence pour Story 9.1 : quand `sensors_published` apparaitra dans `mapping_summary`, il sera automatiquement comptabilise dans l'UI et le script terrain sans autre changement

### Contraintes d'implementation strictes (INTERDIT)

- **NE PAS** modifier `LightMapper`, `CoverMapper`, `SwitchMapper`
- **NE PAS** modifier `SensorCapabilities` (deja cree Story 7.2 avec exactement les champs necessaires)
- **NE PAS** ouvrir d'autres types que `sensor` (binary_sensor = 9.2, button = 9.3)
- **NE PAS** modifier les 30 equipements initiaux du golden-file (IDs 1000-6001)
- **NE PAS** toucher `PRODUCT_SCOPE` ni `HA_COMPONENT_REGISTRY`
- **NE PAS** introduire de `cause_action` (reserve a Story 9.5)
- **NE PAS** modifier `FallbackMapper` (reserve a Story 9.4)

### Dev Agent Guardrails

#### Guardrail — Deploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom reelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procedure parallele
- Reference complete modes + cycle valide terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplace par le script) : `main → beta → stable → Jeedom Market`

#### Guardrail — Golden-file discipline

- Les 30 equipements initiaux (IDs 1000-6001) sont un verrou de non-regression
- Tout drift sur ces 30 cas bloque la PR
- Les 5 nouveaux cas (IDs 7000-7004) s'ajoutent en fin de liste, pas intercales
- Le test `test_story_8_4_golden_file.py` doit rester vert avant ET apres les ajouts

#### Guardrail — Separation sensor / binary_sensor

- `SensorMapper` ne traite QUE les commandes Info dont le subtype inclut `numeric`
- Les commandes Info binary (PRESENCE, OPENING, SMOKE, FLOOD, etc.) sont reservees a Story 9.2
- Les commandes Action sont reservees a Stories 9.3 (ButtonMapper) et 9.4 (FallbackMapper)
- Si un eqLogic a des commandes Info numeric ET Info binary, seul le premier type matchant dans la cascade gagne (determinisme registre)

#### Guardrail — Pas de champ HA "creatif"

- Le payload MQTT Discovery ne doit contenir QUE des champs documentes dans `ha-projection-reference.md`
- Pas de champ invente ou "utile mais non documente"
- Source de verite : section 2 (required_fields sensor.mqtt) + documentation officielle HA pour les champs optionnels standards (`device_class`, `unit_of_measurement`, `state_class`)

### Project Structure Notes

```
resources/daemon/
├── mapping/
│   ├── light.py          (existant — NE PAS MODIFIER)
│   ├── cover.py          (existant — NE PAS MODIFIER)
│   ├── switch.py         (existant — NE PAS MODIFIER)
│   ├── sensor.py         ← NOUVEAU (SensorMapper + _SENSOR_GENERIC_TYPE_MAP)
│   ├── fallback.py       (existant — NE PAS MODIFIER)
│   └── registry.py       (modifier : ajouter SensorMapper dans la liste)
├── discovery/
│   ├── publisher.py      (modifier : ajouter publish_sensor + _build_sensor_payload)
│   └── registry.py       (modifier : ajouter "sensor" + known_types() classmethod)
├── transport/
│   └── http_server.py    (modifier : refactorer _build_mapping_counters pour known_types())
├── models/
│   └── mapping.py        (NE PAS MODIFIER — SensorCapabilities existe deja)
├── validation/
│   └── ha_component_registry.py  (NE PAS MODIFIER — sensor deja modelise)
└── tests/
    ├── fixtures/golden_corpus/
    │   ├── sync_payload.json           (modifier : +5 eqLogics sensor)
    │   ├── expected_sync_snapshot.json  (modifier : +5 resultats attendus)
    │   └── README.md                   (modifier : documenter section sensor)
    └── unit/
        └── test_story_9_1_sensor_mapper.py  ← NOUVEAU
```

### References

- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md#sensor.mqtt] — required_fields et contraintes structurelles
- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md#3. Types generiques Jeedom Core 4.2] — table des types Info numeric eligibles
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story 9.1] — definition epic-level
- [Source: _bmad-output/implementation-artifacts/pe-epic-8-retro-2026-05-05.md#Action Items] — PE8-AI-03, PE8-AI-04
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md#§5.3] — cadrage Story 9.1
- [Source: resources/daemon/mapping/light.py] — pattern mapper reference
- [Source: resources/daemon/discovery/publisher.py] — pattern publisher reference
- [Source: resources/daemon/mapping/registry.py] — enregistrement MapperRegistry
- [Source: resources/daemon/discovery/registry.py] — enregistrement PublisherRegistry
- [Source: resources/daemon/transport/http_server.py#L188] — `_build_mapping_counters_from_publisher_registry()` a refactorer
- [Source: resources/daemon/models/mapping.py#L58] — SensorCapabilities existant
- [Source: resources/daemon/validation/ha_component_registry.py] — sensor deja modelise dans HA_COMPONENT_REGISTRY

### Gate terrain pe-epic-9

- Baseline box Alexandre : 278 eqLogics, 81 eligibles, 30 publies (ratio 37%)
- Attente apres Story 9.1 : augmentation significative des publies grace aux sensors
- Mesure : comptage par type (`sensors_published`) et par mapper d'origine (`SensorMapper` vs `FallbackMapper`)
- Le compteur est deja expose dynamiquement (Story 9.0) — pas de changement UI necessaire

## Dev Agent Record

### Agent Model Used

(a remplir par le dev agent)

### Debug Log References

### Completion Notes List

### File List
