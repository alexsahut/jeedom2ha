# Story 9.2 : BinarySensorMapper + publish_binary_sensor — Info binary (présence, ouverture, fuite, ...)

Status: ready-for-dev

## Story

En tant que mainteneur,
je veux un `BinarySensorMapper` qui projette les commandes Jeedom de type `Info` binary (présence, ouverture, fuite, mouvement, etc.) en entité HA `binary_sensor`,
afin que les capteurs binaires correctement typés dans Jeedom apparaissent automatiquement dans Home Assistant.

## Acceptance Criteria

**AC1 — Mapping binary_sensor nominal**
**Given** un eqLogic Jeedom avec au moins une commande Info dont le sous-type est `binary` (PRESENCE, OPENING, SMOKE, FLOOD, etc.)
**When** le `BinarySensorMapper` est invoqué dans la cascade registry-driven
**Then** un `MappingResult` non-`None` est produit avec :
- `ha_entity_type = "binary_sensor"`
- `state_topic` dérivé de la commande source (`jeedom2ha/{eq_id}/state`)
- `device_class` résolu par le type générique via `_BINARY_SENSOR_GENERIC_TYPE_MAP`
- `capabilities = SensorCapabilities(has_state=True)` (réutilisation de la classe existante)
- `reason_code = "binary_sensor_{generic_type_lower}"`

**AC2 — Validation projection**
**Given** le mapping issu de `BinarySensorMapper`
**When** il passe par `validate_projection()` (Story 3.2 + Story 7.3)
**Then** `is_valid = True` sur les cas nominaux
**And** les required_fields de `binary_sensor.mqtt` sont satisfaits : `availability > keys > topic`, `platform`, `state_topic`
[Source: _bmad-output/planning-artifacts/ha-projection-reference.md#binary_sensor.mqtt]

**AC3 — Publication MQTT Discovery**
**Given** la méthode `publish_binary_sensor` du `DiscoveryPublisher`
**When** elle est appelée sur un mapping binary_sensor valide
**Then** elle produit un payload MQTT Discovery conforme à `binary_sensor.mqtt` (topic = `homeassistant/binary_sensor/jeedom2ha_{eq_id}/config`)
**And** le payload inclut : `name`, `unique_id`, `object_id`, `state_topic`, `platform`, `device`, `availability`
**And** `device_class` est présent si non-None dans `reason_details`
**And** elle est enregistrée dans `PublisherRegistry` sous la clé `"binary_sensor"`

**AC4 — Cascade order : BinarySensorMapper AVANT SensorMapper**
**Given** un eqLogic portant à la fois des commandes Info numeric ET des commandes Info binary
**When** la cascade registry-driven est exécutée
**Then** `BinarySensorMapper` est invoqué AVANT `SensorMapper` dans la liste
**And** l'ordre final est : `LightMapper`, `CoverMapper`, `SwitchMapper`, `BinarySensorMapper`, `SensorMapper`, `FallbackMapper`
**And** si une commande Info binary est présente, c'est le mapping `binary_sensor` qui l'emporte

**AC5 — Extension golden-file (PE8-AI-04)**
**Given** le golden-file Story 8.4 (35 équipements : 30 initiaux + 5 sensor 7000-7004)
**When** il est étendu avec 5 équipements binary_sensor représentatifs (IDs 8000-8004)
**Then** la non-régression du corpus initial (35 équipements) reste verte
**And** les 35 équipements précédents ne sont pas modifiés

**AC6 — Renommage test orchestration (L2 rétro pe-epic-9)**
**Given** le test `test_run_sync_publishes_light_cover_and_switch_through_publisher_registry` dans `test_story_8_3_http_server_dispatch.py:180`
**When** Story 9.2 est implémentée
**Then** ce test est renommé `test_run_sync_publishes_known_types_through_publisher_registry`
**And** le comportement du test reste identique (seul le nom change)

**AC7 — Refactor `_resolve_state_topic` (L3 rétro pe-epic-9)**
**Given** la fonction `_resolve_state_topic` dans `http_server.py:70-75` hardcode `("light", "cover", "switch", "sensor")`
**When** `binary_sensor` est ajouté au `PublisherRegistry`
**Then** la liste hardcodée est remplacée par `PublisherRegistry.known_types()`
**And** `binary_sensor` est automatiquement inclus via `known_types()`

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [ ] Task 1 — Table de mapping Jeedom Info binary → HA device_class (AC1)
  - [ ] 1.1 Créer `resources/daemon/mapping/binary_sensor.py`
  - [ ] 1.2 Définir `_BINARY_SENSOR_GENERIC_TYPE_MAP : Dict[str, Optional[str]]` → `generic_code → device_class` (pas d'unité : binary_sensor n'a pas d'`unit_of_measurement`)
  - [ ] 1.3 Table dérivée de `ha-projection-reference.md` section 3 (types Info, subtype contenant "binary") :
    - `"BATTERY_CHARGING"` → `"battery_charging"`
    - `"CAMERA_RECORD_STATE"` → `"running"`
    - `"HEATING_STATE"` → `"heat"`
    - `"PRESENCE"` → `"occupancy"`
    - `"SMOKE"` → `"smoke"`
    - `"FILTER_CLEAN_STATE"` → `"problem"`
    - `"WATER_LEAK"` → `"moisture"` (subtype vide dans la ref, inclus pour couverture terrain)
    - `"LOCK_STATE"` → `"lock"`
    - `"BARRIER_STATE"` → `"garage_door"`
    - `"GARAGE_STATE"` → `"garage_door"`
    - `"OPENING"` → `"door"`
    - `"OPENING_WINDOW"` → `"window"`
    - `"DOCK_STATE"` → `None`
    - `"SIREN_STATE"` → `"sound"`
    - `"ALARM_STATE"` → `"safety"`
    - `"ALARM_ENABLE_STATE"` → `"safety"`
    - `"FLOOD"` → `"moisture"`
    - `"SABOTAGE"` → `"tamper"`
    - `"SHOCK"` → `"vibration"`
    - `"THERMOSTAT_LOCK"` → `"lock"`
    - `"THERMOSTAT_STATE"` → `None` (nom contient "BINAIRE" mais subtype vide en ref)
    - `"MEDIA_STATE"` → `"running"`
    - `"TIMER_STATE"` → `"running"`
  - [ ] 1.4 NE PAS inclure LIGHT_STATE_BOOL, FLAP_STATE, FLAP_BSO_STATE, ENERGY_STATE — LightMapper/CoverMapper/SwitchMapper les capturent avant dans la cascade

- [ ] Task 2 — Filtre `_is_binary_info_command` et classe `BinarySensorMapper` (AC1)
  - [ ] 2.1 Définir `_is_binary_info_command(cmd: JeedomCmd) -> bool` — symétrique de `_is_numeric_info_command` de Story 9.1 :
    ```python
    def _is_binary_info_command(cmd: JeedomCmd) -> bool:
        if (cmd.type or "").lower() != "info":
            return False
        sub_type = (cmd.sub_type or "").lower()
        if "numeric" in sub_type:
            return False
        return "binary" in sub_type
    ```
    Note : `"binary" in ""` = False, donc les commandes sans subtype (ex. WATER_LEAK) ne matcheront que si elles ont explicitement sub_type="binary" à runtime.
  - [ ] 2.2 Classe `BinarySensorMapper` avec méthode `map(eq, snapshot) -> Optional[MappingResult]` :
    - Itérer les commandes de l'eqLogic
    - Sélectionner la première commande dont `generic_type` est dans `_BINARY_SENSOR_GENERIC_TYPE_MAP` ET `_is_binary_info_command(cmd)` est True
    - Construire `MappingResult` avec :
      - `ha_entity_type = "binary_sensor"`
      - `confidence = "sure"`
      - `reason_code = f"binary_sensor_{generic_type.lower()}"`
      - `capabilities = SensorCapabilities(has_state=True)`
      - `commands = {generic_type: cmd}`
      - `ha_unique_id = f"jeedom2ha_eq_{eq.id}"`
      - `ha_name = eq.name`
      - `suggested_area = snapshot.get_suggested_area(eq.id)`
      - `reason_details = {"device_class": device_class}` (la valeur peut être None — le publisher filtre)
  - [ ] 2.3 Si aucune commande Info binary matchante → retourner `None`

- [ ] Task 3 — Enregistrement dans `MapperRegistry` (AC4)
  - [ ] 3.1 Modifier `resources/daemon/mapping/registry.py` : importer `BinarySensorMapper`
  - [ ] 3.2 Insérer `BinarySensorMapper()` **AVANT** `SensorMapper()` dans `self._mappers`
  - [ ] 3.3 Ordre final : `[LightMapper(), CoverMapper(), SwitchMapper(), BinarySensorMapper(), SensorMapper(), FallbackMapper()]`

- [ ] Task 4 — Implementation de `publish_binary_sensor` (AC3)
  - [ ] 4.1 Ajouter méthode `async publish_binary_sensor(mapping, snapshot) -> bool` dans `DiscoveryPublisher` (`resources/daemon/discovery/publisher.py`)
  - [ ] 4.2 Builder `_build_binary_sensor_payload(mapping, snapshot)` :
    - `name`, `unique_id`, `object_id`
    - `state_topic = f"jeedom2ha/{eq_id}/state"`
    - `platform = "mqtt"`
    - `device` bloc via `_build_device_block(mapping, snapshot)`
    - `availability` via `_build_availability_fields(mapping, snapshot)`
    - `device_class` depuis `mapping.reason_details["device_class"]` — ajouter UNIQUEMENT si non-None
    - Pas de `unit_of_measurement` (binary_sensor n'en a pas)
  - [ ] 4.3 Topic MQTT Discovery : `homeassistant/binary_sensor/jeedom2ha_{eq_id}/config`
  - [ ] 4.4 Pattern identique à `publish_sensor` : log info, publish QoS 1 retain

- [ ] Task 5 — Enregistrement dans `PublisherRegistry` + `known_types()` (AC3, AC7)
  - [ ] 5.1 Modifier `resources/daemon/discovery/registry.py` :
    - Mettre à jour `_known_types = ["light", "cover", "switch", "sensor", "binary_sensor"]`
    - Ajouter `"binary_sensor": publisher.publish_binary_sensor` dans le dict `_publishers`
  - [ ] 5.2 `known_types()` retourne automatiquement `["light", "cover", "switch", "sensor", "binary_sensor"]` sans modification supplémentaire

- [ ] Task 6 — Refactor `_resolve_state_topic` (L3 rétro pe-epic-9, AC7)
  - [ ] 6.1 Modifier `http_server.py:_resolve_state_topic` (ligne 70-75) :
    - Remplacer `if mapping.ha_entity_type in ("light", "cover", "switch", "sensor"):`
    - Par `if mapping.ha_entity_type in PublisherRegistry.known_types():`
  - [ ] 6.2 Vérifier que l'import `PublisherRegistry` est déjà présent dans `http_server.py` (ligne ~195, `PublisherRegistry.known_types()` est déjà utilisé)
  - [ ] 6.3 Lancer les tests Story 8.3 après refactor pour vérifier zéro régression

- [ ] Task 7 — Renommage test orchestration (L2 rétro pe-epic-9, AC6)
  - [ ] 7.1 Dans `resources/daemon/tests/unit/test_story_8_3_http_server_dispatch.py:180` :
    - Renommer `test_run_sync_publishes_light_cover_and_switch_through_publisher_registry`
    - En `test_run_sync_publishes_known_types_through_publisher_registry`
  - [ ] 7.2 Le corps du test reste identique
  - [ ] 7.3 Vérifier que pytest découvre le test avec le nouveau nom

- [ ] Task 8 — Extension du golden-file (AC5, PE8-AI-04)
  - [ ] 8.1 Ajouter 5 eqLogics binary_sensor dans `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json` :
    - `8000` : PRESENCE (détecteur de présence salon) — sub_type=binary
    - `8001` : OPENING (capteur d'ouverture porte entrée) — sub_type=binary
    - `8002` : SMOKE (détecteur de fumée cuisine) — sub_type=binary
    - `8003` : FLOOD (capteur d'inondation cave) — sub_type=binary
    - `8004` : LOCK_STATE (serrure connectée) — sub_type=binary
  - [ ] 8.2 Ajouter les entrées correspondantes dans `expected_sync_snapshot.json` :
    - Diagnostics : `ha_entity_type="binary_sensor"`, reason_code correct, confidence="sure"
    - mapping_summary : `binary_sensors_published` incrémenté de 5
  - [ ] 8.3 Vérifier que `test_story_8_4_golden_file.py` passe avec les 40 équipements (35 initiaux + 5 nouveaux)
  - [ ] 8.4 NE PAS modifier les 35 équipements précédents (IDs 1000-7004)
  - [ ] 8.5 Mettre à jour `resources/daemon/tests/fixtures/golden_corpus/README.md` avec la section binary_sensor

- [ ] Task 9 — Tests unitaires BinarySensorMapper + publish_binary_sensor (AC1, AC2, AC3)
  - [ ] 9.1 Créer `resources/daemon/tests/unit/test_story_9_2_binary_sensor_mapper.py`
  - [ ] 9.2 Reproduire le pattern de `test_story_9_1_sensor_mapper.py` avec helpers `_eq_with_cmd` et `_snapshot`
  - [ ] 9.3 Tests BinarySensorMapper :
    - Nominal : eqLogic avec PRESENCE (sub_type=binary) → MappingResult binary_sensor, device_class=occupancy
    - Nominal : eqLogic avec OPENING (sub_type=binary) → device_class=door
    - Nominal : eqLogic avec SMOKE (sub_type=binary) → device_class=smoke
    - Négatif : eqLogic sans commande Info binary → None
    - Exclusion : eqLogic avec commande Info numeric (ex. TEMPERATURE) → None
    - Exclusion : eqLogic avec commande Action → None
    - Validation : MappingResult passe `validate_projection()` → `is_valid=True`
    - Coexistence : eqLogic avec PRESENCE (binary) + TEMPERATURE (numeric) → BinarySensorMapper gagne (cascade)
  - [ ] 9.4 Tests publish_binary_sensor :
    - Payload structure : champs requis présents (state_topic, platform, device, availability)
    - `device_class` présent si non-None dans reason_details
    - Topic format : `homeassistant/binary_sensor/jeedom2ha_{eq_id}/config`
    - `unit_of_measurement` ABSENT du payload (binary_sensor n'en a pas)
  - [ ] 9.5 Test `known_types()` : retourne `["light", "cover", "switch", "sensor", "binary_sensor"]`

- [ ] Task 10 — Validation non-régression + terrain (AC2, AC5)
  - [ ] 10.1 Lancer la suite complète : `pytest resources/daemon/tests/` — zéro régression
  - [ ] 10.2 Lancer spécifiquement `test_story_8_4_golden_file.py` — PASS avec 40 équipements
  - [ ] 10.3 Déployer sur box Alexandre et relever la mesure terrain :
    - `sensors_published`, `binary_sensors_published`, total publié, ratio publié/éligible
    - Attente : `binary_sensors_published > 0`, ratio progresse vs 67.9% (baseline post-9.1)
  - [ ] 10.4 Documenter la mesure dans les Completion Notes (gate terrain pe-epic-9 PE8-AI-05)

## Dev Notes

### Architecture et patterns à suivre

**Pattern mapper** : calquer exactement `mapping/sensor.py` (Story 9.1) :
- Table dict `_BINARY_SENSOR_GENERIC_TYPE_MAP: Dict[str, Optional[str]]` — clé = generic_code, valeur = device_class (ou None)
- Fonction `_is_binary_info_command(cmd)` — filtre exact symétrique de `_is_numeric_info_command`
- Classe `BinarySensorMapper` avec méthode `map(eq, snapshot) -> Optional[MappingResult]`
- Réutilisation de `SensorCapabilities(has_state=True)` — pas de nouvelle dataclass capabilities

**Réutilisation garantie** :
- `SensorCapabilities` déjà en `models/mapping.py:58` — NE PAS créer de `BinarySensorCapabilities`
- `HA_COMPONENT_REGISTRY["binary_sensor"]` déjà défini en `ha_component_registry.py:44-46` avec `required_capabilities: ["has_state"]` — `validate_projection()` fonctionne sans modification
- `PRODUCT_SCOPE` inclut déjà `"binary_sensor"` depuis Story 7.4 — NE PAS modifier

**Pattern publisher** : calquer `publish_sensor` / `_build_sensor_payload` avec différence clé :
- Pas de `unit_of_measurement` dans le payload binary_sensor (uniquement `device_class`)
- Topic prefix : `homeassistant/binary_sensor/` (pas `homeassistant/sensor/`)

### Source de vérité contraintes HA binary_sensor.mqtt

Required fields (section 2 de `ha-projection-reference.md`, identiques à `sensor.mqtt`) :
- `availability > keys > topic` (string, required)
- `platform` (string, required, valeur = `"mqtt"`)
- `state_topic` (string, required) — format : `jeedom2ha/{eq_id}/state`

HA binary_sensor valid states : `ON` et `OFF` (par défaut). Pas de `unit_of_measurement`.
[Source: _bmad-output/planning-artifacts/ha-projection-reference.md#binary_sensor.mqtt]

### Cascade order — CRITIQUE

```
MapperRegistry._mappers = [
    LightMapper(),         # LIGHT_* → ha_entity_type="light"
    CoverMapper(),         # FLAP_* → ha_entity_type="cover"
    SwitchMapper(),        # ENERGY_* → ha_entity_type="switch"
    BinarySensorMapper(),  # Info binary types → ha_entity_type="binary_sensor"  ← NOUVEAU
    SensorMapper(),        # Info numeric types → ha_entity_type="sensor"
    FallbackMapper(),      # Terminal no-op (câblé en 9.4)
]
```

**Pourquoi BinarySensor AVANT Sensor** : un eqLogic peut porter à la fois des commandes Info binary (PRESENCE, OPENING) ET des commandes Info numeric (TEMPERATURE). Les signaux binaires (présence, ouverture) sont plus actionnables en domotique. La décision est documentée story-level (AC4) et consensée avec l'architecte.

**Types exclus de la table malgré subtype binary** :
- `LIGHT_STATE_BOOL`, `LIGHT_STATE` (binary) → LightMapper capture les eqLogics LIGHT_* en priorité
- `FLAP_STATE`, `FLAP_BSO_STATE` (binary, numeric) → CoverMapper en priorité
- `ENERGY_STATE` (numeric, binary) → SwitchMapper en priorité

### Action Items rétro pe-epic-8 intégrés

| AI | Description | Critère de sortie |
|---|---|---|
| PE8-AI-04 | Extension disciplinée du golden-file | 5 équipements binary_sensor (IDs 8000-8004) ajoutés sans modifier les 35 précédents |
| L2 (rétro pe-epic-9) | Renommer test orchestration obsolète | `test_run_sync_publishes_known_types_through_publisher_registry` remplace `test_run_sync_publishes_light_cover_and_switch_through_publisher_registry` dans `test_story_8_3_http_server_dispatch.py:180` |
| L3 (rétro pe-epic-9) | Refactor `_resolve_state_topic` | Liste hardcodée remplacée par `PublisherRegistry.known_types()` dans `http_server.py:70-75` |

**L3 détail** : La modification de `_resolve_state_topic` EST nécessaire car `binary_sensor` a un `state_topic`. La fonction actuelle (`http_server.py:72`) hardcode `("light", "cover", "switch", "sensor")` — remplacer par `PublisherRegistry.known_types()`. L'import `PublisherRegistry` est déjà présent dans `http_server.py` (utilisé à la ligne ~195). Note : quand Story 9.3 ajoutera `button` à `known_types()`, ce refactor devra être revisité car `button` n'utilise pas `state_topic`.

### Table de mapping complète (référence pour le dev)

Extraite de `ha-projection-reference.md` section 3, tous types Info avec subtype contenant "binary" et non capturés par les mappers antérieurs :

| generic_code | label_fr | device_class HA |
|---|---|---|
| PRESENCE | Présence | `"occupancy"` |
| SMOKE | Détection de fumée | `"smoke"` |
| FILTER_CLEAN_STATE | Etat du filtre | `"problem"` |
| WATER_LEAK | Fuite d'eau | `"moisture"` |
| BATTERY_CHARGING | Batterie en charge | `"battery_charging"` |
| CAMERA_RECORD_STATE | État enregistrement caméra | `"running"` |
| HEATING_STATE | Chauffage fil pilote Etat | `"heat"` |
| LOCK_STATE | Serrure Etat | `"lock"` |
| BARRIER_STATE | Portail (ouvrant) Etat | `"garage_door"` |
| GARAGE_STATE | Garage (ouvrant) Etat | `"garage_door"` |
| OPENING | Porte | `"door"` |
| OPENING_WINDOW | Fenêtre | `"window"` |
| DOCK_STATE | Base Etat | `None` |
| SIREN_STATE | Sirène Etat | `"sound"` |
| ALARM_STATE | Alarme Etat | `"safety"` |
| ALARM_ENABLE_STATE | Alarme Etat activée | `"safety"` |
| FLOOD | Inondation | `"moisture"` |
| SABOTAGE | Sabotage | `"tamper"` |
| SHOCK | Choc | `"vibration"` |
| THERMOSTAT_LOCK | Thermostat Verrouillage | `"lock"` |
| THERMOSTAT_STATE | Thermostat Etat (BINAIRE) | `None` |
| MEDIA_STATE | Etat (multimédia) | `"running"` |
| TIMER_STATE | Minuteur Etat (pause ou non) | `"running"` |

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

#### Guardrail — Golden-file discipline

- Les 35 équipements précédents (IDs 1000-7004) sont un verrou de non-régression
- Tout drift sur ces 35 cas bloque la PR
- Les 5 nouveaux cas (IDs 8000-8004) s'ajoutent en fin de liste, pas intercalés
- Le test `test_story_8_4_golden_file.py` doit rester vert avant ET après les ajouts
- Ne pas régénérer le snapshot depuis le code — construire manuellement les 5 nouvelles entrées

#### Guardrail — Séparation binary_sensor / sensor

- `BinarySensorMapper` ne traite QUE les commandes Info dont le subtype contient `"binary"` et PAS `"numeric"`
- Les commandes Info numeric (TEMPERATURE, HUMIDITY, etc.) restent réservées à SensorMapper (Story 9.1)
- Si `sub_type` est vide ou absent → `_is_binary_info_command` retourne False → pas de match
- Coexistence Info binary + Info numeric : BinarySensorMapper gagne car il est AVANT SensorMapper dans la cascade

#### Guardrail — Pas de champ HA "créatif"

- Le payload MQTT Discovery ne doit contenir QUE des champs documentés dans `ha-projection-reference.md`
- `unit_of_measurement` est ABSENT du payload binary_sensor (pas documenté requis pour ce composant)
- Source de vérité : section 2 `binary_sensor.mqtt` required_fields + documentation HA officielle pour `device_class`

#### Guardrail — NE PAS modifier

- `LightMapper`, `CoverMapper`, `SwitchMapper`, `SensorMapper`, `FallbackMapper`
- `SensorCapabilities` (réutilisée telle quelle pour binary_sensor)
- `PRODUCT_SCOPE` ni `HA_COMPONENT_REGISTRY` (binary_sensor déjà modélisé Story 7.2, déjà ouvert Story 7.4)
- Les 35 équipements existants du golden-file (IDs 1000-7004)
- `validate_projection()` (binary_sensor déjà validable Story 7.3)

### Project Structure Notes

```
resources/daemon/
├── mapping/
│   ├── light.py           (existant — NE PAS MODIFIER)
│   ├── cover.py           (existant — NE PAS MODIFIER)
│   ├── switch.py          (existant — NE PAS MODIFIER)
│   ├── sensor.py          (existant — NE PAS MODIFIER)
│   ├── binary_sensor.py   ← NOUVEAU (BinarySensorMapper + _BINARY_SENSOR_GENERIC_TYPE_MAP)
│   ├── fallback.py        (existant — NE PAS MODIFIER)
│   └── registry.py        (modifier : insérer BinarySensorMapper avant SensorMapper)
├── discovery/
│   ├── publisher.py       (modifier : ajouter publish_binary_sensor + _build_binary_sensor_payload)
│   └── registry.py        (modifier : ajouter "binary_sensor" dans _known_types + _publishers)
├── transport/
│   └── http_server.py     (modifier : _resolve_state_topic:70-75 → known_types() ; + rename test L2)
├── models/
│   └── mapping.py         (NE PAS MODIFIER — SensorCapabilities réutilisé)
├── validation/
│   └── ha_component_registry.py  (NE PAS MODIFIER — binary_sensor déjà modélisé)
└── tests/
    ├── fixtures/golden_corpus/
    │   ├── sync_payload.json           (modifier : +5 eqLogics binary_sensor 8000-8004)
    │   ├── expected_sync_snapshot.json  (modifier : +5 résultats attendus + binary_sensors_published)
    │   └── README.md                   (modifier : documenter section binary_sensor)
    └── unit/
        ├── test_story_9_2_binary_sensor_mapper.py  ← NOUVEAU
        └── test_story_8_3_http_server_dispatch.py  (modifier : renommage test L2 ligne 180)
```

### Baseline et Gate terrain pe-epic-9

- Baseline post-9.1 : 278 eqLogics, 81 éligibles, 55 publiés (ratio 67.9%)
- Mesure attendue post-9.2 : `binary_sensors_published > 0`, ratio > 67.9%
- Format de mesure à documenter : `total_eq=278, eligible=81, published=X, sensors_published=Y, binary_sensors_published=Z, ratio=X/81*100%`
- Le compteur `binary_sensors_published` sera automatiquement exposé dans `mapping_summary` (Story 9.0 rend le total dynamique)

### References

- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md#binary_sensor.mqtt] — required_fields et contraintes structurelles
- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md#3. Types génériques Jeedom Core 4.2] — table des types Info binary éligibles
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story 9.2] — définition epic-level + AC cascade order
- [Source: _bmad-output/implementation-artifacts/pe-epic-8-retro-2026-05-05.md#Action Items] — PE8-AI-04, L2, L3
- [Source: _bmad-output/implementation-artifacts/9-1-sensor-mapper-publish-sensor-info-numeric-et-capteurs-simples.md] — pattern de référence (SensorMapper + publish_sensor)
- [Source: resources/daemon/mapping/sensor.py] — pattern mapper à reproduire
- [Source: resources/daemon/discovery/publisher.py#publish_sensor] — pattern publisher à reproduire
- [Source: resources/daemon/mapping/registry.py] — enregistrement MapperRegistry
- [Source: resources/daemon/discovery/registry.py] — enregistrement PublisherRegistry + known_types()
- [Source: resources/daemon/transport/http_server.py#L70-75] — `_resolve_state_topic` à refactorer (L3)
- [Source: resources/daemon/tests/unit/test_story_8_3_http_server_dispatch.py#L180] — test à renommer (L2)
- [Source: resources/daemon/models/mapping.py#L58] — SensorCapabilities réutilisé
- [Source: resources/daemon/validation/ha_component_registry.py#L44-46] — binary_sensor déjà modélisé

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
