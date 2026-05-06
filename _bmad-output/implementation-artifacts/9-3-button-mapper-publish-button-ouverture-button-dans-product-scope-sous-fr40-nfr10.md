# Story 9.3 : ButtonMapper + publish_button + ouverture `button` dans PRODUCT_SCOPE sous FR40 / NFR10

Status: ready-for-dev

## Story

En tant que mainteneur,
je veux un `ButtonMapper` qui projette les commandes Jeedom Action ponctuelles (sub_type "other", ex. scénarios, déclencheurs one-shot) en entité HA `button`,
afin que les actions discrètes Jeedom soient déclenchables depuis Home Assistant.

## Acceptance Criteria

**AC1 — Mapping button nominal**
**Given** un eqLogic Jeedom avec au moins une commande `Action` dont le `sub_type` est `"other"` et dont le `generic_type` est non-None (ex. `GENERIC_ACTION`, `MEDIA_PAUSE`, `SIREN_ON`, ...)
**When** le `ButtonMapper` est invoqué dans la cascade registry-driven
**Then** un `MappingResult` non-`None` est produit avec :
- `ha_entity_type = "button"`
- `confidence = "sure"`
- `command_topic = jeedom2ha/{eq_id}/cmd`
- `reason_code = f"button_{generic_type.lower()}"` (basé sur le generic_type de la première commande Action "other" trouvée)
- `capabilities = SwitchCapabilities(has_on_off=True)` (satisfait `has_command` dans `validate_projection`)

**AC2 — Validation projection**
**Given** le mapping issu de `ButtonMapper`
**When** il passe par `validate_projection()` (Story 3.2 + Story 7.3)
**Then** `is_valid = True` sur les cas nominaux
**And** les required_fields de `button.mqtt` sont satisfaits : `availability > keys > topic`, `command_topic`, `platform`
[Source: `_bmad-output/planning-artifacts/ha-projection-reference.md#button.mqtt`]

**AC3 — Publication MQTT Discovery**
**Given** la méthode `publish_button` du `DiscoveryPublisher`
**When** elle est appelée sur un mapping button valide
**Then** elle produit un payload MQTT Discovery conforme à `button.mqtt` (topic = `homeassistant/button/jeedom2ha_{eq_id}/config`)
**And** le payload inclut : `name`, `unique_id`, `object_id`, `command_topic`, `platform`, `device`, `availability`
**And** le payload N'INCLUT PAS de `state_topic` (button n'a pas d'état)
**And** elle est enregistrée dans `PublisherRegistry` sous la clé `"button"`

**AC4 — Position cascade : ButtonMapper APRÈS SensorMapper, AVANT FallbackMapper**
**Given** la cascade registry-driven complète
**When** un eqLogic ne correspond à aucun mapper antérieur (Light, Cover, Switch, BinarySensor, Sensor)
**Then** `ButtonMapper` est invoqué en dernier avant `FallbackMapper`
**And** l'ordre final est : `LightMapper`, `CoverMapper`, `SwitchMapper`, `BinarySensorMapper`, `SensorMapper`, `ButtonMapper`, `FallbackMapper`

**AC5 — PRODUCT_SCOPE + gate FR40/NFR10**
**Given** l'ajout de `"button"` dans `PRODUCT_SCOPE` de `ha_component_registry.py`
**When** les gates FR40/NFR10 sont appliqués
**Then** dans le MÊME increment :
- `button` est déjà présent dans `HA_COMPONENT_REGISTRY` (Story 7.2) ✓
- au moins un cas nominal `validate_projection("button", SwitchCapabilities(has_on_off=True))` → `is_valid=True`
- au moins un cas d'échec `validate_projection("button", SwitchCapabilities(has_on_off=False))` → `is_valid=False, reason_code="ha_missing_command_topic"`
- non-régression du contrat 4D : test existant 4.3 passe toujours

**AC6 — Fix `_resolve_state_topic` : button exclut state_topic**
**Given** la fonction `_resolve_state_topic` dans `http_server.py`
**When** `button` est ajouté au `PublisherRegistry.known_types()`
**Then** `_resolve_state_topic` retourne `""` pour les mappings `ha_entity_type == "button"` (pas de state_topic pour button)
**And** les autres types (`light`, `cover`, `switch`, `sensor`, `binary_sensor`) continuent de retourner `jeedom2ha/{eq_id}/state`
**And** les tests Story 8.3 (dispatch) restent PASS

**AC7 — Extension golden-file (PE8-AI-04 discipline)**
**Given** le golden-file Story 8.4 (40 équipements : 30 initiaux + 5 sensor + 5 binary_sensor)
**When** il est étendu avec 3 équipements button représentatifs (IDs 9000-9002)
**Then** la non-régression du corpus initial (40 équipements) reste verte
**And** les 40 équipements précédents ne sont pas modifiés
**And** `buttons_published=3` apparaît dans `mapping_summary` du snapshot attendu

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [ ] Task 1 — Filtre `_is_action_other_command` et classe `ButtonMapper` (AC1, AC4)
  - [ ] 1.1 Créer `resources/daemon/mapping/button.py`
  - [ ] 1.2 Définir `_is_action_other_command(cmd: JeedomCmd) -> bool` :
    - `(cmd.type or "").lower() == "action"` ET `(cmd.sub_type or "").lower() == "other"` ET `cmd.generic_type is not None`
  - [ ] 1.3 Classe `ButtonMapper` avec méthode `map(eq, snapshot) -> Optional[MappingResult]`
  - [ ] 1.4 Itérer les commandes, prendre la PREMIÈRE correspondant à `_is_action_other_command`
  - [ ] 1.5 Construire `MappingResult` avec :
    - `ha_entity_type="button"`, `confidence="sure"`
    - `reason_code=f"button_{cmd.generic_type.lower()}"`
    - `commands={cmd.generic_type: cmd}`
    - `capabilities=SwitchCapabilities(has_on_off=True)` — satisfait `has_command`
    - `reason_details={"command_topic": f"jeedom2ha/{eq.id}/cmd"}`
  - [ ] 1.6 Si aucune commande Action "other" avec generic_type → retourner `None`

- [ ] Task 2 — Enregistrement dans `MapperRegistry` (AC4)
  - [ ] 2.1 Modifier `resources/daemon/mapping/registry.py` : importer `ButtonMapper`
  - [ ] 2.2 Insérer `ButtonMapper()` **APRÈS** `SensorMapper()`, **AVANT** `FallbackMapper()`
  - [ ] 2.3 Ordre final : `[LightMapper(), CoverMapper(), SwitchMapper(), BinarySensorMapper(), SensorMapper(), ButtonMapper(), FallbackMapper()]`

- [ ] Task 3 — Implémentation de `publish_button` (AC3)
  - [ ] 3.1 Ajouter méthode `async publish_button(mapping, snapshot) -> bool` dans `DiscoveryPublisher`
  - [ ] 3.2 Builder `_build_button_payload(mapping, snapshot)` :
    - `command_topic = f"jeedom2ha/{eq_id}/cmd"` (PAS `/set` — sémantique différente du switch)
    - `platform = "mqtt"` dans le payload
    - Champs requis : `name`, `unique_id`, `object_id`, `command_topic`, `platform`, `device`, `availability`
    - PAS de `state_topic`, PAS de `payload_on`/`payload_off`
  - [ ] 3.3 Topic MQTT Discovery : `homeassistant/button/jeedom2ha_{eq_id}/config`
  - [ ] 3.4 Pattern identique à `publish_sensor` / `publish_binary_sensor` : log info, publish QoS 1 retain

- [ ] Task 4 — Enregistrement dans `PublisherRegistry` (AC3)
  - [ ] 4.1 Modifier `resources/daemon/discovery/registry.py` : ajouter `"button"` dans `_known_types`
  - [ ] 4.2 Ajouter `"button": publisher.publish_button` dans `_publishers`
  - [ ] 4.3 `known_types()` retourne `["light", "cover", "switch", "sensor", "binary_sensor", "button"]`

- [ ] Task 5 — PRODUCT_SCOPE : ouverture `button` sous FR40/NFR10 (AC5)
  - [ ] 5.1 Modifier `resources/daemon/validation/ha_component_registry.py`
  - [ ] 5.2 `PRODUCT_SCOPE = ["light", "cover", "switch", "sensor", "binary_sensor", "button"]`
  - [ ] 5.3 Commentaire commentaire inline : `# button ouvert Story 9.3 sous FR40/NFR10`
  - [ ] 5.4 Ajouter tests `validate_projection` pour button : nominal (`SwitchCapabilities(has_on_off=True)` → `is_valid=True`) et échec (`SwitchCapabilities(has_on_off=False)` → `is_valid=False, reason_code="ha_missing_command_topic"`)

- [ ] Task 6 — Fix `_resolve_state_topic` pour button (AC6)
  - [ ] 6.1 Dans `resources/daemon/transport/http_server.py`, localiser `_resolve_state_topic` (~ligne 70)
  - [ ] 6.2 Ajouter un ensemble `_TYPES_WITHOUT_STATE_TOPIC = {"button"}` (constante module-level)
  - [ ] 6.3 Modifier la condition : retourner `state_topic` SEULEMENT si `ha_entity_type not in _TYPES_WITHOUT_STATE_TOPIC`
  - [ ] 6.4 Tests Story 8.3 restent PASS (le renommage est déjà fait en 9.2)

- [ ] Task 7 — Extension du golden-file (AC7, PE8-AI-04)
  - [ ] 7.1 3 eqLogics button ajoutés dans `sync_payload.json` (IDs 9000-9002) :
    - `9000` : GENERIC_ACTION (scénario Jeedom one-shot)
    - `9001` : MEDIA_PAUSE (action multimédia)
    - `9002` : SIREN_ON (action sécurité)
  - [ ] 7.2 `expected_sync_snapshot.json` étendu avec les 3 résultats button attendus + `buttons_published=3` dans `mapping_summary`
  - [ ] 7.3 `test_story_8_4_golden_file.py` : mettre à jour `_assert_corpus_shape` → 43 équipements
  - [ ] 7.4 Les 40 équipements précédents (IDs 1000-8004) non modifiés — confirmé

- [ ] Task 8 — Tests unitaires ButtonMapper + publish_button (AC1-AC3, AC5)
  - [ ] 8.1 Créer `test_story_9_3_button_mapper.py` — calqué sur `test_story_9_2_binary_sensor_mapper.py`
  - [ ] 8.2 Tests ButtonMapper :
    - Nominal `GENERIC_ACTION` (sub_type "other") → button sure
    - Nominal `MEDIA_PAUSE` → button sure, reason_code "button_media_pause"
    - Négatif : Action sub_type "slider" → None
    - Négatif : Action sub_type "string" → None
    - Négatif : Info sub_type "other" → None (doit être Action)
    - Négatif : Action sub_type "other" sans generic_type → None
    - Coexistence Action "other" + Info numeric → ButtonMapper retourne button (SensorMapper déjà passé avant)
  - [ ] 8.3 Tests `publish_button` : payload requis (command_topic, platform, availability), absence state_topic, topic format `homeassistant/button/...`
  - [ ] 8.4 Tests `validate_projection("button", ...)` : nominal is_valid=True, échec is_valid=False reason_code="ha_missing_command_topic"
  - [ ] 8.5 Test `known_types()` : retourne `["light", "cover", "switch", "sensor", "binary_sensor", "button"]`

- [ ] Task 9 — Validation non-régression + terrain (AC2, AC7)
  - [ ] 9.1 Suite complète : X/X PASS — zéro régression
  - [ ] 9.2 `test_story_8_4_golden_file.py` : PASS avec 43 équipements
  - [ ] 9.3 Déployer sur box Alexandre et relever la mesure terrain
  - [ ] 9.4 Documenter la mesure dans les Completion Notes (gate terrain pe-epic-9 PE8-AI-05)

## Dev Notes

### Architecture et patterns à suivre

**Pattern mapper** : calquer exactement `mapping/binary_sensor.py` (Story 9.2) :
- PAS de table dict `_GENERIC_TYPE_MAP` — ButtonMapper est broadband (tout Action "other")
- Fonction `_is_action_other_command(cmd)` — symétrique de `_is_binary_info_command`
- Classe `ButtonMapper` avec méthode `map(eq, snapshot) -> Optional[MappingResult]`
- Réutilisation de `SwitchCapabilities(has_on_off=True)` — NE PAS créer de `ButtonCapabilities`

**Pourquoi `SwitchCapabilities(has_on_off=True)` pour button** :
- `validate_projection("button", caps)` requiert `has_command`
- `_resolve_capability("has_command", SwitchCapabilities)` retourne `capabilities.has_on_off`
- Fallback dans `ha_component_registry.py:106-108` : `getattr(capabilities, "has_on_off", False)` → True ✓
- Pattern cohérent avec Story 9.2 qui réutilise `SensorCapabilities` pour `binary_sensor`

**Réutilisation garantie** :
- `SwitchCapabilities` déjà importable depuis `models.mapping`
- `HA_COMPONENT_REGISTRY["button"]` déjà défini en `ha_component_registry.py:46-49` avec `required_capabilities: ["has_command"]`
- `validate_projection("button", ...)` fonctionne SANS modification du registre (Story 7.2)

**Pattern publisher** : calquer `publish_binary_sensor` / `_build_binary_sensor_payload` avec différences clés :
- `command_topic = f"jeedom2ha/{eq_id}/cmd"` (PAS `state_topic` — button est un actionneur sans état)
- Pas de `state_topic`, pas de `device_class`, pas de `unit_of_measurement`
- `platform = "mqtt"` inclus explicitement dans le payload (requis par `button.mqtt` required_fields)
- Topic prefix : `homeassistant/button/` (pas `homeassistant/sensor/`)

### Source de vérité contraintes HA button.mqtt

Required fields (section 2 de `ha-projection-reference.md`) :
- `availability > keys > topic` (string, required)
- `command_topic` (string, required) — format : `jeedom2ha/{eq_id}/cmd`
- `platform` (string, required, valeur = `"mqtt"`)

HA button : pas de `state_topic`, pas de `payload_on`/`payload_off`. Le payload HA "PRESS" est le défaut.
[Source: `_bmad-output/planning-artifacts/ha-projection-reference.md#button.mqtt`]

### Cascade order — CRITIQUE

```
MapperRegistry._mappers = [
    LightMapper(),         # LIGHT_* → ha_entity_type="light"
    CoverMapper(),         # FLAP_* → ha_entity_type="cover"
    SwitchMapper(),        # ENERGY_* → ha_entity_type="switch"
    BinarySensorMapper(),  # Info binary types → ha_entity_type="binary_sensor"
    SensorMapper(),        # Info numeric types → ha_entity_type="sensor"
    ButtonMapper(),        # Action "other" types → ha_entity_type="button"  ← NOUVEAU
    FallbackMapper(),      # Terminal (câblé Story 8.1, activé Story 9.4)
]
```

**Pourquoi ButtonMapper APRÈS SensorMapper** : un eqLogic avec TEMPERATURE (Info numeric) + GENERIC_ACTION (Action other) est capturé par SensorMapper. Button ne voit que les eqLogics sans Info numeric/binary détectés par les mappers antérieurs.

**Types Action "other" couverts effectivement par ButtonMapper** (non capturés en amont) :
- Generic : `GENERIC_ACTION` (scénarios Jeedom)
- Caméra : `CAMERA_UP/DOWN/LEFT/RIGHT/ZOOM/DEZOOM/STOP/PRESET/RECORD/TAKE`
- Multimédia : `MEDIA_PAUSE/RESUME/STOP/NEXT/PREVIOUS/ON/OFF/MUTE/UNMUTE`
- Sécurité : `SIREN_ON/OFF`, `ALARM_ARMED/RELEASED/SET_MODE`
- Thermostat : `THERMOSTAT_SET_MODE/SET_LOCK/SET_UNLOCK`
- Robot : `DOCK`
- Serrure : `LOCK_OPEN/CLOSE`
- Portail/garage : `GB_OPEN/CLOSE/TOGGLE`
- Chauffage : `HEATING_ON/OFF/OTHER` (eqLogic sans HEATING_STATE binary)
- Autre : `TIMER_PAUSE/RESUME`, `REBOOT`, `MODE_SET_STATE`

**Types Action "other" capturés AVANT par mappers spécifiques** (exclus de facto de ButtonMapper) :
- `LIGHT_ON/OFF/TOGGLE/MODE` → LightMapper
- `FLAP_UP/DOWN/BSO_UP/BSO_DOWN` → CoverMapper
- `ENERGY_ON/OFF` → SwitchMapper

### Fix `_resolve_state_topic` — CRITIQUE

```python
# AVANT (http_server.py:70-75) — INCORRECT après ajout button à known_types()
def _resolve_state_topic(mapping: MappingResult) -> str:
    if mapping.ha_entity_type in PublisherRegistry.known_types():
        return f"jeedom2ha/{mapping.jeedom_eq_id}/state"
    return ""

# APRÈS — CORRECT
_TYPES_WITHOUT_STATE_TOPIC = {"button"}

def _resolve_state_topic(mapping: MappingResult) -> str:
    if (mapping.ha_entity_type in PublisherRegistry.known_types()
            and mapping.ha_entity_type not in _TYPES_WITHOUT_STATE_TOPIC):
        return f"jeedom2ha/{mapping.jeedom_eq_id}/state"
    return ""
```

**Pourquoi** : button n'a pas de `state_topic`. Si on retourne un state_topic pour button, le contrat runtime est incorrect. La constante `_TYPES_WITHOUT_STATE_TOPIC` sera étendue par Story 9.4 si FallbackMapper produit des mappings button.

### command_topic format pour button

Format : `jeedom2ha/{eq_id}/cmd` (NE PAS utiliser `/set` — sémantique distincte)

Rationale :
- `/set` = modifier un état (switch ON/OFF, light ON/OFF) — light, switch, cover
- `/cmd` = déclencher une action ponctuelle — button
- Pas de risque de collision : un eqLogic ne peut être mappé qu'à UN SEUL type

Le payload HA qui déclenche le bouton est `"PRESS"` (défaut HA). Le daemon devra souscrire à ce topic pour déclencher l'action Jeedom (implémentation runtime hors scope Story 9.3 — la story publie uniquement la configuration Discovery).

### `reason_details` pour ButtonMapper

Stocker `command_topic` dans `reason_details` pour permettre au publisher d'y accéder sans reconstruire le topic :
```python
reason_details={"command_topic": f"jeedom2ha/{eq.id}/cmd"}
```

Puis dans `_build_button_payload` :
```python
reason_details = mapping.reason_details or {}
command_topic = reason_details.get("command_topic", f"jeedom2ha/{eq_id}/cmd")
```

### Golden-file — 3 équipements button à ajouter

Dans `sync_payload.json`, ajouter après les 5 binary_sensor (IDs 8000-8004) :

```json
{
  "id": "9000",
  "name": "Scénario alarme sécurité",
  "object_id": "1",
  "eq_type": "scenario",
  "generic_type": null,
  "is_enable": "1",
  "is_visible": "1",
  "cmds": [
    {
      "id": "90001",
      "name": "Activer",
      "generic_type": "GENERIC_ACTION",
      "type": "action",
      "sub_type": "other"
    }
  ]
},
{
  "id": "9001",
  "name": "Lecteur salon",
  "object_id": "1",
  "eq_type": "virtual",
  "generic_type": null,
  "is_enable": "1",
  "is_visible": "1",
  "cmds": [
    {
      "id": "90011",
      "name": "Pause",
      "generic_type": "MEDIA_PAUSE",
      "type": "action",
      "sub_type": "other"
    }
  ]
},
{
  "id": "9002",
  "name": "Sirène garage",
  "object_id": "1",
  "eq_type": "virtual",
  "generic_type": null,
  "is_enable": "1",
  "is_visible": "1",
  "cmds": [
    {
      "id": "90021",
      "name": "Activer sirène",
      "generic_type": "SIREN_ON",
      "type": "action",
      "sub_type": "other"
    }
  ]
}
```

Dans `expected_sync_snapshot.json`, ajouter les 3 résultats button et s'assurer que `mapping_summary` inclut `buttons_published: 3`.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

#### Guardrail — Golden-file discipline (PE8-AI-04)

- Les 40 équipements précédents (IDs 1000-8004) sont un verrou de non-régression
- Tout drift sur ces 40 cas bloque la PR
- Les 3 nouveaux cas (IDs 9000-9002) s'ajoutent en fin de liste, pas intercalés
- Le test `test_story_8_4_golden_file.py` doit rester vert avant ET après les ajouts
- NE PAS régénérer le snapshot depuis le code — construire manuellement les 3 nouvelles entrées

#### Guardrail — NE PAS créer ButtonCapabilities

- Réutiliser `SwitchCapabilities(has_on_off=True)` — NE PAS créer `ButtonCapabilities`
- `_resolve_capability("has_command", SwitchCapabilities(has_on_off=True))` → `True` via ligne 103
- Pattern cohérent avec Story 9.2 (`SensorCapabilities` réutilisé pour `binary_sensor`)

#### Guardrail — command_topic DISTINCT de switch/light

- Button : `jeedom2ha/{eq_id}/cmd` — déclencher une action ponctuelle
- Switch/Light/Cover : `jeedom2ha/{eq_id}/set` — modifier un état
- Ces deux formats ne doivent PAS être confondus — la sémantique est différente

#### Guardrail — Pas de state_topic dans le payload button

- `_build_button_payload` NE DOIT PAS inclure `state_topic`
- `_resolve_state_topic` doit retourner `""` pour `ha_entity_type == "button"`
- Sinon : contrat runtime incorrect et confusion dans le diagnostic

#### Guardrail — PRODUCT_SCOPE gate FR40/NFR10 OBLIGATOIRE

- L'ajout de `"button"` dans `PRODUCT_SCOPE` EXIGE dans le MÊME increment :
  1. `button` dans `HA_COMPONENT_REGISTRY` ✓ (déjà fait Story 7.2)
  2. Tests nominaux et d'échec `validate_projection("button", ...)` ← Story 9.3 doit les ajouter
  3. Non-régression test 4D passant ← à vérifier

#### Guardrail — NE PAS modifier

- `LightMapper`, `CoverMapper`, `SwitchMapper`, `BinarySensorMapper`, `SensorMapper`
- `SwitchCapabilities` (réutilisée telle quelle — `has_on_off=True` sert de proxy `has_command`)
- `HA_COMPONENT_REGISTRY` (button déjà modélisé Story 7.2)
- `validate_projection()` — fonctionne déjà pour button via `has_command`
- Les 40 équipements existants du golden-file (IDs 1000-8004)

#### Guardrail — _is_action_other_command ne doit pas matcher slider/string

- `sub_type == "slider"` → futur `number` entity (pas button)
- `sub_type == "string"` → futur `text` entity (pas button)
- Seul `sub_type == "other"` déclenche ButtonMapper

### Project Structure Notes

```
resources/daemon/
├── mapping/
│   ├── light.py           (existant — NE PAS MODIFIER)
│   ├── cover.py           (existant — NE PAS MODIFIER)
│   ├── switch.py          (existant — NE PAS MODIFIER)
│   ├── sensor.py          (existant — NE PAS MODIFIER)
│   ├── binary_sensor.py   (existant — NE PAS MODIFIER)
│   ├── button.py          ← NOUVEAU (ButtonMapper + _is_action_other_command)
│   ├── fallback.py        (existant — NE PAS MODIFIER)
│   └── registry.py        (modifier : importer ButtonMapper, insérer AVANT FallbackMapper)
├── discovery/
│   ├── publisher.py       (modifier : ajouter publish_button + _build_button_payload)
│   └── registry.py        (modifier : ajouter "button" dans _known_types + _publishers)
├── transport/
│   └── http_server.py     (modifier : _resolve_state_topic + _TYPES_WITHOUT_STATE_TOPIC)
├── models/
│   └── mapping.py         (NE PAS MODIFIER — SwitchCapabilities réutilisé)
├── validation/
│   └── ha_component_registry.py  (modifier : PRODUCT_SCOPE += "button")
└── tests/
    ├── fixtures/golden_corpus/
    │   ├── sync_payload.json             (modifier : +3 eqLogics button 9000-9002)
    │   ├── expected_sync_snapshot.json   (modifier : +3 résultats attendus + buttons_published)
    │   └── README.md                     (modifier : documenter section button)
    └── unit/
        ├── test_story_9_3_button_mapper.py  ← NOUVEAU
        ├── test_story_8_4_golden_file.py    (modifier : _assert_corpus_shape → 43)
        ├── test_story_8_1_mapper_registry.py  (modifier : ButtonMapper dans ordre)
        └── test_story_8_2_publisher_registry.py  (modifier : "button" dans assertions)
```

### Baseline et Gate terrain pe-epic-9

- Baseline post-9.2 : 278 eqLogics, 81 éligibles, 58 publiés (ratio 71.6%)
- Mesure attendue post-9.3 : `buttons_published > 0`, ratio ≥ 71.6%
- Format de mesure : `total_eq=278, eligible=81, published=X, sensors_published=Y, binary_sensors_published=Z, buttons_published=W, ratio=X/81*100%`
- Le compteur `buttons_published` sera automatiquement exposé dans `mapping_summary` (Story 9.0 rend le total dynamique)

### Précédents Story 9.2 — Erreurs à éviter

**L1 [LOW Story 9.2]** : `_hardcoded_cascade` dans `test_story_8_1_mapper_registry.py:106-114` — ne pas oublier de l'actualiser avec `ButtonMapper`. Les tests passent même si cette fonction helper n'inclut pas `ButtonMapper` (car aucun cas button ne l'utilise), mais c'est une dette de test à maintenir.

**L2 [LOW Story 9.2]** : Ne PAS régénérer `expected_sync_snapshot.json` via le pipeline — construire manuellement les entrées button pour respecter la discipline golden-file PE8-AI-04.

### References

- [Source: `_bmad-output/planning-artifacts/ha-projection-reference.md#button.mqtt`] — required_fields et contraintes structurelles
- [Source: `_bmad-output/planning-artifacts/ha-projection-reference.md#3. Types génériques Jeedom Core 4.2`] — table des types Action "other" éligibles
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md#Story 9.3`] — définition epic-level + AC PRODUCT_SCOPE gate
- [Source: `_bmad-output/implementation-artifacts/9-2-binary-sensor-mapper-publish-binary-sensor-info-binary-presence-ouverture-fuite.md`] — pattern de référence (BinarySensorMapper + publish_binary_sensor + guardrails)
- [Source: `resources/daemon/mapping/binary_sensor.py`] — pattern mapper à reproduire (broadband sans table)
- [Source: `resources/daemon/discovery/publisher.py#publish_binary_sensor`] — pattern publisher à reproduire
- [Source: `resources/daemon/mapping/registry.py`] — enregistrement MapperRegistry
- [Source: `resources/daemon/discovery/registry.py`] — enregistrement PublisherRegistry + known_types()
- [Source: `resources/daemon/transport/http_server.py#L70-75`] — `_resolve_state_topic` à corriger (AC6)
- [Source: `resources/daemon/validation/ha_component_registry.py#L46-49`] — button déjà dans HA_COMPONENT_REGISTRY
- [Source: `resources/daemon/validation/ha_component_registry.py#L64`] — PRODUCT_SCOPE à modifier
- [Source: `resources/daemon/validation/ha_component_registry.py#L91-117`] — `_resolve_capability` — fallback `has_command` via `has_on_off`
- [Source: `resources/daemon/models/mapping.py`] — SwitchCapabilities à réutiliser
- [Source: `_bmad-output/implementation-artifacts/pe-epic-8-retro-2026-05-05.md#Action Items`] — PE8-AI-04 (discipline golden-file)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
