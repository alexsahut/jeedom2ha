---
artifact_type: ha-projection-reference
project: jeedom2ha
source: docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx
source_xlsx_alongside: ha-projection-reference.xlsx
extracted_on: 2026-04-30
extracted_sheets: [README, Jeedom_Generic_Types, HA_MQTT_Components, HA_MQTT_Required_Fields]
skipped_sheets: [HomeKit_Services, HomeKit_Service_Char_Map, HomeKit_Characteristics, HA_MQTT_All_Doc_Fields]
skipped_reason: HomeKit_* = ecosystem parallele Homebridge non utilise par jeedom2ha ; HA_MQTT_All_Doc_Fields = surensemble (1397 lignes) dont seuls les required fields portent la validation projection.
status: source-of-truth
---

# Reference projection HA - source-of-truth jeedom2ha

Cet artefact transcrit en markdown les onglets operationnels du fichier Excel `docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx`. Il est la **source de verite** pour :

- la liste exhaustive des **types generiques Jeedom** Core 4.2 (cote entree du moteur de projection),
- la liste exhaustive des **composants MQTT Home Assistant officiellement documentes** (cote cible),
- les **champs structurellement requis** par composant HA (contrat de validation `validate_projection()`).

Toute extension du perimetre publie dans HA derive de ce document. Les artefacts code (`ha_component_registry.py`, mappers, publishers) doivent rester **derives** de cette reference - pas l'inverse.

## Statut BMAD et regles d'evolution

### Statut

Cette reference est **source-of-truth officielle** du cycle `Moteur de projection explicable` depuis le correct-course du 2026-04-30 (voir `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md`). Elle est inscrite a ce titre dans `_bmad-output/planning-artifacts/active-cycle-manifest.md` section 4.

### Usages BMAD obligatoires

| Surface produit | Usage prescriptif de cette reference |
|---|---|
| `resources/daemon/validation/ha_component_registry.py` (`HA_COMPONENT_REGISTRY`) | Les `required_fields` de chaque entree doivent correspondre aux `explicit_required_fields` de la section 1 de cette reference (composants HA MQTT). Toute divergence doit etre justifiee story-level. |
| `resources/daemon/validation/ha_component_registry.py` (`PRODUCT_SCOPE`) | Aucun composant ne peut entrer dans `PRODUCT_SCOPE` s'il n'est pas reference en section 1. La gouvernance FR40 / NFR10 (Story 7.4) prend appui sur cette reference. |
| `resources/daemon/mapping/*.py` | Tout mapper specifique doit produire un `MappingResult` dont les champs satisfont au minimum les `explicit_required_fields` du composant HA cible declare dans cette reference. |
| `resources/daemon/discovery/*.py` (publishers) | Les payloads MQTT Discovery emis par les `publish_*` methodes doivent inclure les `explicit_required_fields` de cette reference et **uniquement** des champs documentes par cette reference (pas de champ "creatif" hors documentation HA officielle). |
| `validate_projection()` (`pe-epic-7` Story 7.3) | Les cas nominaux et cas d'echec testes doivent porter sur les contraintes listees en section 2 de cette reference (champs structurellement requis par composant). |
| Sequencing des vagues d'ouverture (`pe-epic-9`, `pe-epic-10+`) | Le decoupage des vagues d'extension produit derive de la liste des 31 composants HA documentes en section 1 et des 163 types generiques Jeedom de la section dediee. |
| Stories qui ouvrent un nouveau type | Doivent citer explicitement la ligne correspondante de cette reference dans leurs Acceptance Criteria et Dev notes. |

### Regles d'evolution

- Cette reference est **derivee mecaniquement** de `docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx` lui-meme construit depuis les sources officielles (Jeedom Core 4.2, HAP-NodeJS, Home Assistant MQTT Discovery). Elle n'est **jamais** editee a la main.
- Toute mise a jour de cette reference passe par une re-extraction de l'Excel source. Le commit qui modifie ce `.md` doit aussi modifier le `.xlsx` source ou indiquer la nouvelle version source en frontmatter.
- L'extension du fichier Excel source (ajout de composants HA, evolution de la documentation HA officielle) declenche une re-extraction puis une revue d'impact sur `HA_COMPONENT_REGISTRY` et le sequencing des vagues. Aucune modification arbitraire.
- Les onglets `HomeKit_*` de l'Excel source ne sont pas extraits ici (voir `skipped_sheets` en frontmatter) car Homebridge / HAP-NodeJS reste un ecosysteme parallele non utilise par jeedom2ha. Toute decision de les integrer un jour passe par un correct-course explicite.

### Niveaux d'abstraction

`ha-projection-reference.md` et `ha_component_registry.py` operent a **deux niveaux d'abstraction differents** (regle posee par `architecture-projection-engine.md`) :

- **Niveau 1 — Spec HA officielle (cette reference)** : champs MQTT Discovery requis par composant tels que documentes par Home Assistant. Cle JSON littérale (`command_topic`, `state_topic`, `options`, `platform`, `availability > keys > topic`).
- **Niveau 2 — Contrat moteur de projection (`HA_COMPONENT_REGISTRY`)** : capabilities abstraites resolues a runtime (`has_command`, `has_state`, `has_options`) qui se traduisent en champs Niveau 1 via `_CAPABILITY_TO_REASON`.

La verification de coherence entre Niveau 1 et Niveau 2 est tracable story-level mais reste deux representations distinctes ; ce fichier est la source-of-truth du Niveau 1.

### Sequencing d'ouverture documente

A ce jour (post correct-course 2026-04-30) :

| Composant HA | Etat (Story 7.4) | Vague d'ouverture |
|---|---|---|
| `light` | ouvert (pre-pe-epic-7) | historique |
| `cover` | ouvert (pre-pe-epic-7) | historique |
| `switch` | ouvert (pre-pe-epic-7) | historique |
| `sensor` | ouvert (`PRODUCT_SCOPE` post 7.4) | publication reelle ouverte par `pe-epic-9` Story 9.1 |
| `binary_sensor` | ouvert (`PRODUCT_SCOPE` post 7.4) | publication reelle ouverte par `pe-epic-9` Story 9.2 |
| `button` | connu (registre 7.2) | ouverture `PRODUCT_SCOPE` + publication par `pe-epic-9` Story 9.3 |
| `number`, `select`, `climate` | connus (registre 7.2) | vagues ulterieures (`pe-epic-10+`) |
| 22 autres composants HA officiels | non encore connus (registre fermé sur 9 entrees) | vagues ulterieures gouvernees |

L'existence d'un composant en section 1 de cette reference **n'est pas** un engagement produit a l'ouvrir. Elle est seulement une garantie que sa modelisation future suivra les contraintes officielles HA documentees ici.

## Meta-referentiel (onglet README)

- **Objectif** : Référence documentaire exhaustive au périmètre Option B demandé : Jeedom (types génériques Core), Homebridge/HAP-NodeJS (services et characteristics documentés), Home Assistant (composants MQTT et champs explicitement documentés).
- **Périmètre Jeedom** : Liste des types génériques du Core selon la documentation officielle Jeedom Core 4.2.
- **Périmètre Homebridge** : Services et characteristics issus de la documentation officielle HAP-NodeJS / Homebridge.
- **Périmètre Home Assistant** : Option B retenue : composants MQTT officiellement documentés par Home Assistant, avec uniquement les champs explicitement marqués required dans la documentation source.
- **Règle de transcription** : Aucune hypothèse métier ajoutée. Les colonnes reprennent soit le libellé de la documentation, soit une extraction mécanique de la source officielle.
- **Limite importante** : Pour Home Assistant, ce classeur couvre le périmètre MQTT officiellement documenté, pas l'ensemble de toutes les integrations non-MQTT du produit.
- **Source Jeedom** : https://doc.jeedom.com/fr_FR/core/4.2/types
- **Source Homebridge services** : https://developers.homebridge.io/HAP-NodeJS/modules/_definitions.Services.html
- **Source Homebridge characteristics** : https://developers.homebridge.io/HAP-NodeJS/modules/_definitions.Characteristics.html
- **Source Home Assistant MQTT** : https://www.home-assistant.io/integrations/mqtt/
- **Comptage Jeedom** : 163 lignes de types génériques
- **Comptage Homebridge** : 73 services, 249 characteristics, 409 relations service/characteristic
- **Comptage HA MQTT** : 31 documents MQTT, 77 champs explicitement requis, 1397 champs documentés

## 1. Composants HA MQTT cibles

**31 composants** documentes officiellement par Home Assistant cote MQTT Discovery. C'est le catalogue cible exhaustif du moteur de projection. La colonne `explicit_required_fields` liste les champs marques required dans la documentation source ; ils sont le contrat minimal de `validate_projection()`.

| doc_id | title | ha_domain | ha_category | discovery_or_setup_doc | explicit_required_fields | source_url |
|---|---|---|---|---|---|---|
| alarm_control_panel.mqtt | MQTT Alarm control panel | mqtt | Alarm | yes | availability > keys > topic, command_topic, platform, state_topic | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/alarm_control_panel.mqtt.markdown |
| binary_sensor.mqtt | MQTT binary sensor | mqtt | Binary sensor | yes | availability > keys > topic, platform, state_topic | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/binary_sensor.mqtt.markdown |
| button.mqtt | MQTT button | mqtt | Button | yes | availability > keys > topic, command_topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/button.mqtt.markdown |
| camera.mqtt | MQTT Camera | mqtt | Camera | yes | availability > keys > topic, topic | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/camera.mqtt.markdown |
| climate.mqtt | MQTT climate (HVAC) | mqtt | Climate | yes | availability > keys > topic | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/climate.mqtt.markdown |
| cover.mqtt | MQTT Cover | mqtt | Cover | yes | availability > keys > topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/cover.mqtt.markdown |
| device_tracker.mqtt | MQTT device tracker | mqtt | Presence detection | yes | availability > keys > topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_tracker.mqtt.markdown |
| device_trigger.mqtt | MQTT Device trigger | mqtt | Device automation | yes | automation_type, platform, topic, type, subtype, device | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_trigger.mqtt.markdown |
| event.mqtt | MQTT Event | mqtt | Event | yes | availability > keys > topic, event_types, platform, state_topic | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/event.mqtt.markdown |
| fan.mqtt | MQTT Fan | mqtt | Fan | yes | availability > keys > topic, command_topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/fan.mqtt.markdown |
| humidifier.mqtt | MQTT Humidifier | mqtt | Humidifier | yes | availability > keys > topic, command_topic, target_humidity_command_topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/humidifier.mqtt.markdown |
| image.mqtt | MQTT Image | mqtt | Image | yes | availability > keys > topic | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/image.mqtt.markdown |
| lawn_mower.mqtt | MQTT lawn mower | mqtt | Lawn mower | yes | availability > keys > topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/lawn_mower.mqtt.markdown |
| light.mqtt | MQTT Light | mqtt | Light | yes | availability > keys > topic, command_topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/light.mqtt.markdown |
| lock.mqtt | MQTT Lock | mqtt | Lock | yes | availability > keys > topic, command_topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/lock.mqtt.markdown |
| manual_mqtt | Manual MQTT Alarm control panel | manual_mqtt | Alarm |  |  | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/manual_mqtt.markdown |
| mqtt_json | MQTT JSON | mqtt_json | Presence detection |  | devices | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/mqtt_json.markdown |
| mqtt_room | MQTT room presence | mqtt_room | Presence detection |  | device_id, state_topic | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/mqtt_room.markdown |
| notify.mqtt | MQTT notify | mqtt | Notifications | yes | availability > keys > topic | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/notify.mqtt.markdown |
| number.mqtt | MQTT Number | mqtt | Number | yes | availability > keys > topic, command_topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/number.mqtt.markdown |
| scene.mqtt | MQTT Scene | mqtt | Scene | yes | availability > keys > topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/scene.mqtt.markdown |
| select.mqtt | MQTT Select | mqtt | Select | yes | availability > keys > topic, command_topic, options, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/select.mqtt.markdown |
| sensor.mqtt | MQTT Sensor | mqtt | Sensor | yes | availability > keys > topic, platform, state_topic | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/sensor.mqtt.markdown |
| siren.mqtt | MQTT Siren | mqtt | Siren | yes | availability > keys > topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/siren.mqtt.markdown |
| switch.mqtt | MQTT Switch | mqtt | Switch | yes | availability > keys > topic, command_topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/switch.mqtt.markdown |
| tag.mqtt | MQTT tag scanner | mqtt | Tag scanner | yes | topic, device | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/tag.mqtt.markdown |
| text.mqtt | MQTT Text | mqtt | Text | yes | availability > keys > topic, command_topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/text.mqtt.markdown |
| update.mqtt | MQTT Update | mqtt | Update | yes | availability > keys > topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/update.mqtt.markdown |
| vacuum.mqtt | MQTT Vacuum | mqtt | Vacuum | yes | availability > keys > topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/vacuum.mqtt.markdown |
| valve.mqtt | MQTT Valve | mqtt | Valve | yes | availability > keys > topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/valve.mqtt.markdown |
| water_heater.mqtt | MQTT water heater | mqtt | Water heater | yes | availability > keys > topic, platform | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/water_heater.mqtt.markdown |

## 2. Champs structurellement requis par composant HA

**77 champs** explicitement marques `required: true` dans la documentation HA, groupes par `doc_id` (composant). Cette table est le contrat operationnel utilise par `validate_projection()` pour decider `is_valid=True/False`. Elle alimente le futur `ha_component_registry.yaml` (architecture pe-epic-8).

### alarm_control_panel.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| alarm_control_panel.mqtt | MQTT Alarm control panel | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/alarm_control_panel.mqtt.markdown |
| alarm_control_panel.mqtt | MQTT Alarm control panel | command_topic | command_topic |  | true | string |  | The MQTT topic to publish commands to change the alarm state. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/alarm_control_panel.mqtt.markdown |
| alarm_control_panel.mqtt | MQTT Alarm control panel | platform | platform |  | true | string |  | Must be `alarm_control_panel`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/alarm_control_panel.mqtt.markdown |
| alarm_control_panel.mqtt | MQTT Alarm control panel | state_topic | state_topic |  | true | string |  | "The MQTT topic subscribed to receive state updates. A \"None\" payload resets to an `unknown` state. An empty payload is ignored. Valid state payloads are: `armed_away`, `armed_custom_bypass`, `arme… | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/alarm_control_panel.mqtt.markdown |

### binary_sensor.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| binary_sensor.mqtt | MQTT binary sensor | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/binary_sensor.mqtt.markdown |
| binary_sensor.mqtt | MQTT binary sensor | platform | platform |  | true | string |  | Must be `binary_sensor`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/binary_sensor.mqtt.markdown |
| binary_sensor.mqtt | MQTT binary sensor | state_topic | state_topic |  | true | string |  | The MQTT topic subscribed to receive sensor's state. Valid states are `OFF` and `ON`. Custom `OFF` and `ON` values can be set with the `payload_off` and `payload_on` config options. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/binary_sensor.mqtt.markdown |

### button.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| button.mqtt | MQTT button | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/button.mqtt.markdown |
| button.mqtt | MQTT button | command_topic | command_topic |  | true | string |  | The MQTT topic to publish commands to trigger the button. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/button.mqtt.markdown |
| button.mqtt | MQTT button | platform | platform |  | true | string |  | Must be `button`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/button.mqtt.markdown |

### camera.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| camera.mqtt | MQTT Camera | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/camera.mqtt.markdown |
| camera.mqtt | MQTT Camera | topic | topic |  | true | string |  | The MQTT topic to subscribe to. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/camera.mqtt.markdown |

### climate.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| climate.mqtt | MQTT climate (HVAC) | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/climate.mqtt.markdown |

### cover.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| cover.mqtt | MQTT Cover | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/cover.mqtt.markdown |
| cover.mqtt | MQTT Cover | platform | platform |  | true | string |  | Must be `cover`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/cover.mqtt.markdown |

### device_tracker.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| device_tracker.mqtt | MQTT device tracker | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_tracker.mqtt.markdown |
| device_tracker.mqtt | MQTT device tracker | platform | platform |  | true | string |  | Must be `device_tracker`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_tracker.mqtt.markdown |

### device_trigger.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| device_trigger.mqtt | MQTT Device trigger | automation_type | automation_type |  | true | string |  | The type of automation, must be 'trigger'. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_trigger.mqtt.markdown |
| device_trigger.mqtt | MQTT Device trigger | platform | platform |  | true | string |  | Must be `device_automation`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_trigger.mqtt.markdown |
| device_trigger.mqtt | MQTT Device trigger | topic | topic |  | true | string |  | The MQTT topic subscribed to receive trigger events. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_trigger.mqtt.markdown |
| device_trigger.mqtt | MQTT Device trigger | type | type |  | true | string |  | "The type of the trigger, e.g. `button_short_press`. Entries supported by the frontend: `button_short_press`, `button_short_release`, `button_long_press`, `button_long_release`, `button_double_press`… | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_trigger.mqtt.markdown |
| device_trigger.mqtt | MQTT Device trigger | subtype | subtype |  | true | string |  | "The subtype of the trigger, e.g. `button_1`. Entries supported by the frontend: `turn_on`, `turn_off`, `button_1`, `button_2`, `button_3`, `button_4`, `button_5`, `button_6`. If set to an unsupporte… | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_trigger.mqtt.markdown |
| device_trigger.mqtt | MQTT Device trigger | device | device |  | true | map |  | "Information about the device this device trigger is a part of to tie it into the [device registry](https://developers.home-assistant.io/docs/en/device_registry_index.html). At least one of identifie… | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/device_trigger.mqtt.markdown |

### event.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| event.mqtt | MQTT Event | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/event.mqtt.markdown |
| event.mqtt | MQTT Event | event_types | event_types |  | true | list |  | A list of valid `event_type` strings. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/event.mqtt.markdown |
| event.mqtt | MQTT Event | platform | platform |  | true | string |  | Must be `event`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/event.mqtt.markdown |
| event.mqtt | MQTT Event | state_topic | state_topic |  | true | string |  | The MQTT topic subscribed to receive JSON event payloads. The JSON payload should contain the `event_type` element. The event type should be one of the configured `event_types`. Note that replayed re… | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/event.mqtt.markdown |

### fan.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| fan.mqtt | MQTT Fan | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/fan.mqtt.markdown |
| fan.mqtt | MQTT Fan | command_topic | command_topic |  | true | string |  | The MQTT topic to publish commands to change the fan state. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/fan.mqtt.markdown |
| fan.mqtt | MQTT Fan | platform | platform |  | true | string |  | Must be `fan`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/fan.mqtt.markdown |

### humidifier.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| humidifier.mqtt | MQTT Humidifier | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/humidifier.mqtt.markdown |
| humidifier.mqtt | MQTT Humidifier | command_topic | command_topic |  | true | string |  | The MQTT topic to publish commands to change the humidifier state. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/humidifier.mqtt.markdown |
| humidifier.mqtt | MQTT Humidifier | target_humidity_command_topic | target_humidity_command_topic |  | true | string |  | The MQTT topic to publish commands to change the humidifier target humidity state based on a percentage. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/humidifier.mqtt.markdown |
| humidifier.mqtt | MQTT Humidifier | platform | platform |  | true | string |  | Must be `humidifier`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/humidifier.mqtt.markdown |

### image.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| image.mqtt | MQTT Image | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/image.mqtt.markdown |

### lawn_mower.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| lawn_mower.mqtt | MQTT lawn mower | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/lawn_mower.mqtt.markdown |
| lawn_mower.mqtt | MQTT lawn mower | platform | platform |  | true | string |  | Must be `lawn_mower`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/lawn_mower.mqtt.markdown |

### light.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| light.mqtt | MQTT Light | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/light.mqtt.markdown |
| light.mqtt | MQTT Light | command_topic | command_topic |  | true | string |  | The MQTT topic to publish commands to change the switch state. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/light.mqtt.markdown |
| light.mqtt | MQTT Light | platform | platform |  | true | string |  | Must be `light`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/light.mqtt.markdown |

### lock.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| lock.mqtt | MQTT Lock | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/lock.mqtt.markdown |
| lock.mqtt | MQTT Lock | command_topic | command_topic |  | true | string |  | The MQTT topic to publish commands to change the lock state. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/lock.mqtt.markdown |
| lock.mqtt | MQTT Lock | platform | platform |  | true | string |  | Must be `lock`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/lock.mqtt.markdown |

### mqtt_json

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| mqtt_json | MQTT JSON | devices | devices |  | true | list |  | List of devices with their topic. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/mqtt_json.markdown |

### mqtt_room

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| mqtt_room | MQTT room presence | device_id | device_id |  | true | string |  | The device id to track for this sensor. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/mqtt_room.markdown |
| mqtt_room | MQTT room presence | state_topic | state_topic |  | true | string |  | The topic that contains all subtopics for the rooms. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/mqtt_room.markdown |

### notify.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| notify.mqtt | MQTT notify | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/notify.mqtt.markdown |

### number.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| number.mqtt | MQTT Number | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/number.mqtt.markdown |
| number.mqtt | MQTT Number | command_topic | command_topic |  | true | string |  | The MQTT topic to publish commands to change the number. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/number.mqtt.markdown |
| number.mqtt | MQTT Number | platform | platform |  | true | string |  | Must be `number`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/number.mqtt.markdown |

### scene.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| scene.mqtt | MQTT Scene | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/scene.mqtt.markdown |
| scene.mqtt | MQTT Scene | platform | platform |  | true | string |  | Must be `scene`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/scene.mqtt.markdown |

### select.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| select.mqtt | MQTT Select | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/select.mqtt.markdown |
| select.mqtt | MQTT Select | command_topic | command_topic |  | true | string |  | The MQTT topic to publish commands to change the selected option. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/select.mqtt.markdown |
| select.mqtt | MQTT Select | options | options |  | true | list |  | List of options that can be selected. An empty list or a list with a single item is allowed. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/select.mqtt.markdown |
| select.mqtt | MQTT Select | platform | platform |  | true | string |  | Must be `select`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/select.mqtt.markdown |

### sensor.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| sensor.mqtt | MQTT Sensor | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/sensor.mqtt.markdown |
| sensor.mqtt | MQTT Sensor | platform | platform |  | true | string |  | Must be `sensor`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/sensor.mqtt.markdown |
| sensor.mqtt | MQTT Sensor | state_topic | state_topic |  | true | string |  | The MQTT topic subscribed to receive sensor values. If `device_class`, `state_class`, `unit_of_measurement` or `suggested_display_precision` is set, and a numeric value is expected, an empty value `'… | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/sensor.mqtt.markdown |

### siren.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| siren.mqtt | MQTT Siren | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/siren.mqtt.markdown |
| siren.mqtt | MQTT Siren | platform | platform |  | true | string |  | Must be `siren`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/siren.mqtt.markdown |

### switch.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| switch.mqtt | MQTT Switch | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/switch.mqtt.markdown |
| switch.mqtt | MQTT Switch | command_topic | command_topic |  | true | string |  | The MQTT topic to publish commands to change the switch state. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/switch.mqtt.markdown |
| switch.mqtt | MQTT Switch | platform | platform |  | true | string |  | Must be `switch`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/switch.mqtt.markdown |

### tag.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| tag.mqtt | MQTT tag scanner | topic | topic |  | true | string |  | The MQTT topic subscribed to receive tag scanned events. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/tag.mqtt.markdown |
| tag.mqtt | MQTT tag scanner | device | device |  | true | map |  | "Information about the device this device trigger is a part of to tie it into the [device registry](https://developers.home-assistant.io/docs/en/device_registry_index.html). At least one of identifie… | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/tag.mqtt.markdown |

### text.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| text.mqtt | MQTT Text | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/text.mqtt.markdown |
| text.mqtt | MQTT Text | command_topic | command_topic |  | true | string |  | The MQTT topic to publish the text value that is set. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/text.mqtt.markdown |
| text.mqtt | MQTT Text | platform | platform |  | true | string |  | Must be `text`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/text.mqtt.markdown |

### update.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| update.mqtt | MQTT Update | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/update.mqtt.markdown |
| update.mqtt | MQTT Update | platform | platform |  | true | string |  | Must be `update`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/update.mqtt.markdown |

### vacuum.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| vacuum.mqtt | MQTT Vacuum | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/vacuum.mqtt.markdown |
| vacuum.mqtt | MQTT Vacuum | platform | platform |  | true | string |  | Must be `vacuum`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/vacuum.mqtt.markdown |

### valve.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| valve.mqtt | MQTT Valve | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/valve.mqtt.markdown |
| valve.mqtt | MQTT Valve | platform | platform |  | true | string |  | Must be `valve`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/valve.mqtt.markdown |

### water_heater.mqtt

| doc_id | title | field_path | field_name | parent_path | required | type | default | description | source_url |
|---|---|---|---|---|---|---|---|---|---|
| water_heater.mqtt | MQTT water heater | availability > keys > topic | topic | availability > keys | true | string |  | An MQTT topic subscribed to receive availability (online/offline) updates. | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/water_heater.mqtt.markdown |
| water_heater.mqtt | MQTT water heater | platform | platform |  | true | string |  | Must be `water_heater`. Only allowed and required in [MQTT auto discovery device messages](/integrations/mqtt/#device-discovery-payload). | https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/water_heater.mqtt.markdown |

## 3. Types generiques Jeedom Core 4.2

**163 types generiques** documentes par Jeedom, source des regles de mapping. Groupes par `family_fr`. La colonne `command_kind` distingue Info (entite de lecture en HA) vs Action (entite pilotable). Les `subtypes` indiquent les widgets compatibles cote Jeedom (`binary`, `numeric`, `slider`, `string`, `other`) et conditionnent le choix du composant HA cible (sensor vs binary_sensor, number vs select, button vs switch...).

### Autre (5 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Autre | Other | TIMER | Minuteur Etat | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Autre | Other | TIMER_STATE | Minuteur Etat (pause ou non) | Info | binary, numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Autre | Other | SET_TIMER | Minuteur | Action | slider | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Autre | Other | TIMER_PAUSE | Minuteur pause | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Autre | Other | TIMER_RESUME | Minuteur reprendre | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Batterie (2 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Batterie | Battery | BATTERY | Batterie | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Batterie | Battery | BATTERY_CHARGING | Batterie en charge | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Caméra (12 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Caméra | Camera | CAMERA_URL | URL caméra | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_RECORD_STATE | État enregistrement caméra | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_UP | Mouvement caméra vers le haut | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_DOWN | Mouvement caméra vers le bas | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_LEFT | Mouvement caméra vers la gauche | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_RIGHT | Mouvement caméra vers la droite | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_ZOOM | Zoom caméra vers l’avant | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_DEZOOM | Zoom caméra vers l’arrière | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_STOP | Stop caméra | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_PRESET | Preset caméra | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_RECORD | Enregistrement caméra | Action |  | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Caméra | Camera | CAMERA_TAKE | Snapshot caméra | Action |  | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Chauffage (4 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Chauffage | Heating | HEATING_STATE | Chauffage fil pilote Etat | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Chauffage | Heating | HEATING_ON | Chauffage fil pilote Bouton ON | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Chauffage | Heating | HEATING_OFF | Chauffage fil pilote Bouton OFF | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Chauffage | Heating | HEATING_OTHER | Chauffage fil pilote Bouton | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Electricité (4 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Electricité | Electricity | POWER | Puissance Electrique | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Electricité | Electricity | CONSUMPTION | Consommation Electrique | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Electricité | Electricity | VOLTAGE | Tension | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Electricité | Electricity | REBOOT | Redémarrage | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Environnement (13 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Environnement | Environment | TEMPERATURE | Température | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | AIR_QUALITY | Qualité de l’air | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | BRIGHTNESS | Luminosité | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | PRESENCE | Présence | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | SMOKE | Détection de fumée | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | HUMIDITY | Humidité | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | UV | UV | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | CO2 | CO2 (ppm) | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | CO | CO (ppm) | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | NOISE | Son (dB) | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | PRESSURE | Pression | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | WATER_LEAK | Fuite d’eau | Info |  | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Environnement | Environment | FILTER_CLEAN_STATE | Etat du filtre | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Generic (5 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Generic | Generic | DEPTH | Profondeur | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Generic | Generic | DISTANCE | Distance | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Generic | Generic | BUTTON | Bouton | Info | binary, numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Generic | Generic | GENERIC_INFO | Générique | Info |  | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Generic | Generic | GENERIC_ACTION | Générique | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Lumière (12 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Lumière | Light | LIGHT_STATE | Lumière Etat | Info | binary, numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_BRIGHTNESS | Lumière Luminosité | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_COLOR | Lumière Couleur | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_STATE_BOOL | Lumière Etat (Binaire) | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_COLOR_TEMP | Lumière Température Couleur | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_TOGGLE | Lumière Toggle | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_ON | Lumière Bouton On | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_OFF | Lumière Bouton Off | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_SLIDER | Lumière Slider | Action | slider | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_SET_COLOR | Lumière Couleur | Action | color | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_MODE | Lumière Mode | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Lumière | Light | LIGHT_SET_COLOR_TEMP | Lumière Température Couleur | Action |  | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Mode (2 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Mode | Mode | MODE_STATE | Mode Etat | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Mode | Mode | MODE_SET_STATE | Changer Mode | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Multimédia (19 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Multimédia | Multimedia | VOLUME | Volume | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_STATUS | Status | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_ALBUM | Album | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_ARTIST | Artiste | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_TITLE | Titre | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_POWER | Power | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | CHANNEL | Chaine | Info | numeric, string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_STATE | Etat | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | SET_VOLUME | Volume | Action | slider | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | SET_CHANNEL | Chaine | Action | other, slider | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_PAUSE | Pause | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_RESUME | Lecture | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_STOP | Stop | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_NEXT | Suivant | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_PREVIOUS | Précedent | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_ON | On | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_OFF | Off | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_MUTE | Muet | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Multimédia | Multimedia | MEDIA_UNMUTE | Non Muet | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Météo (31 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Météo | Weather | WEATHER_TEMPERATURE | Météo Température | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MAX_2 | Météo condition j+1 max j+2 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WIND_SPEED | Vent (vitesse) | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | RAIN_TOTAL | Pluie (accumulation) | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | RAIN_CURRENT | Pluie (mm/h) | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION_ID_4 | Météo condition (id) j+4 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION_4 | Météo condition j+4 | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MAX_4 | Météo Température max j+4 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MIN_4 | Météo Température min j+4 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION_ID_3 | Météo condition (id) j+3 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION_3 | Météo condition j+3 | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MAX_3 | Météo Température max j+3 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MIN_3 | Météo Température min j+3 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION_ID_2 | Météo condition (id) j+2 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION_2 | Météo condition j+2 | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MIN_2 | Météo Température min j+2 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_HUMIDITY | Météo Humidité | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION_ID_1 | Météo condition (id) j+1 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION_1 | Météo condition j+1 | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MAX_1 | Météo Température max j+1 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MIN_1 | Météo Température min j+1 | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION_ID | Météo condition (id) | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_CONDITION | Météo condition | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MAX | Météo Température max | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_TEMPERATURE_MIN | Météo Température min | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_SUNRISE | Météo coucher de soleil | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_SUNSET | Météo lever de soleil | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_WIND_DIRECTION | Météo direction du vent | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_WIND_SPEED | Météo vitesse du vent | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WEATHER_PRESSURE | Météo Pression | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Météo | Weather | WIND_DIRECTION | Vent (direction) | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Ouvrant (10 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Ouvrant | Opening | LOCK_STATE | Serrure Etat | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ouvrant | Opening | BARRIER_STATE | Portail (ouvrant) Etat | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ouvrant | Opening | GARAGE_STATE | Garage (ouvrant) Etat | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ouvrant | Opening | OPENING | Porte | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ouvrant | Opening | OPENING_WINDOW | Fenêtre | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ouvrant | Opening | LOCK_OPEN | Serrure Bouton Ouvrir | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ouvrant | Opening | LOCK_CLOSE | Serrure Bouton Fermer | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ouvrant | Opening | GB_OPEN | Portail ou garage bouton d’ouverture | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ouvrant | Opening | GB_CLOSE | Portail ou garage bouton de fermeture | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ouvrant | Opening | GB_TOGGLE | Portail ou garage bouton toggle | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Prise (4 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Prise | Outlet | ENERGY_STATE | Prise Etat | Info | numeric, binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Prise | Outlet | ENERGY_ON | Prise Bouton On | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Prise | Outlet | ENERGY_OFF | Prise Bouton Off | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Prise | Outlet | ENERGY_SLIDER | Prise Slider | Action |  | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Robot (2 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Robot | Robot | DOCK_STATE | Base Etat | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Robot | Robot | DOCK | Retour base | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Sécurité (12 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Sécurité | Security | SIREN_STATE | Sirène Etat | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | ALARM_STATE | Alarme Etat | Info | binary, string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | ALARM_MODE | Alarme mode | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | ALARM_ENABLE_STATE | Alarme Etat activée | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | FLOOD | Inondation | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | SABOTAGE | Sabotage | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | SHOCK | Choc | Info | binary, numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | SIREN_OFF | Sirène Bouton Off | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | SIREN_ON | Sirène Bouton On | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | ALARM_ARMED | Alarme armée | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | ALARM_RELEASED | Alarme libérée | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Sécurité | Security | ALARM_SET_MODE | Alarme Mode | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Thermostat (14 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Thermostat | Thermostat | THERMOSTAT_STATE | Thermostat Etat (BINAIRE) (pour Plugin Thermostat uniquement) | Info |  | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_TEMPERATURE | Thermostat Température ambiante | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_SETPOINT | Thermostat consigne | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_MODE | Thermostat Mode (pour Plugin Thermostat uniquement) | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_LOCK | Thermostat Verrouillage (pour Plugin Thermostat uniquement) | Info | binary | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_TEMPERATURE_OUTDOOR | Thermostat Température Exterieur (pour Plugin Thermostat uniquement) | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_STATE_NAME | Thermostat Etat (HUMAIN) (pour Plugin Thermostat uniquement) | Info | string | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_HUMIDITY | Thermostat humidité ambiante | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | HUMIDITY_SETPOINT | Humidité consigne | Info | slider | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_SET_SETPOINT | Thermostat consigne | Action | slider | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_SET_MODE | Thermostat Mode (pour Plugin Thermostat uniquement) | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_SET_LOCK | Thermostat Verrouillage (pour Plugin Thermostat uniquement) | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | THERMOSTAT_SET_UNLOCK | Thermostat Déverrouillage (pour Plugin Thermostat uniquement) | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Thermostat | Thermostat | HUMIDITY_SET_SETPOINT | Humidité consigne | Action | slider | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Ventilateur (4 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Ventilateur | Fan | FAN_SPEED_STATE | Vitesse ventilateur Etat | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ventilateur | Fan | ROTATION_STATE | Rotation Etat | Info | numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ventilateur | Fan | FAN_SPEED | Vitesse ventilateur | Action | slider | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Ventilateur | Fan | ROTATION | Rotation | Action | slider | https://doc.jeedom.com/fr_FR/core/4.2/types |

### Volet (8 types)

| family_fr | family_id | generic_code | label_fr | command_kind | subtypes | source_url |
|---|---|---|---|---|---|---|
| Volet | Shutter | FLAP_STATE | Volet Etat | Info | binary, numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Volet | Shutter | FLAP_BSO_STATE | Volet BSO Etat | Info | binary, numeric | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Volet | Shutter | FLAP_UP | Volet Bouton Monter | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Volet | Shutter | FLAP_DOWN | Volet Bouton Descendre | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Volet | Shutter | FLAP_STOP | Volet Bouton Stop | Action |  | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Volet | Shutter | FLAP_SLIDER | Volet Bouton Slider | Action | slider | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Volet | Shutter | FLAP_BSO_UP | Volet BSO Bouton Monter | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |
| Volet | Shutter | FLAP_BSO_DOWN | Volet BSO Bouton Descendre | Action | other | https://doc.jeedom.com/fr_FR/core/4.2/types |

## 4. Implications pour le moteur de projection

### 4.1 Perimetre actuel vs cible

| Mesure | Etat actuel (post pe-epic-7) | Cible (vision) |
|---|---|---|
| Composants HA modelises `connu` dans `HA_COMPONENT_REGISTRY` | 9 (light, cover, switch, sensor, binary_sensor, button, number, select, climate) | 31 |
| Composants HA `ouvert` dans `PRODUCT_SCOPE` | 5 (light, cover, switch, sensor, binary_sensor) | tous les composants `validable` |
| Mappers en production | 3 (light, cover, switch) | un par composant ouvrable + FallbackMapper |
| Publishers en production | 3 | un par composant ouvert, dispatch dynamique |
| Types generiques Jeedom couverts par mapping deterministe | < 20 | tendre vers 163 avec fallback elegant |

### 4.2 Regle de degradation elegante (cadrage section 11)

Quand aucun composant riche (light/cover/switch/climate/number/select) ne capte un eqLogic mais que celui-ci porte au moins une commande typee :

- commande `Info` (binary/numeric/string) -> projeter en `binary_sensor` / `sensor`
- commande `Action` sans etat correlable -> projeter en `button`

Cette regle evite le skip silencieux. Plus aucun equipement eligible ne reste non publie sans cause explicite tracee dans le diagnostic.

### 4.3 Maintenance du referentiel

Source autoritative = `ha-projection-reference.xlsx` (a cote de ce `.md`). Toute mise a jour HA doc -> re-extraction Excel -> re-export ce `.md` + le `.yaml`. Le code (registre Python) consomme ces artefacts ; il ne les redefinit pas.
