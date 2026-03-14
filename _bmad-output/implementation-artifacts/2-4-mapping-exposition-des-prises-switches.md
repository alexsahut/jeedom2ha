# Story 2.4: Mapping & Exposition des Prises / Switches

Status: ready-for-review

## Story

As a utilisateur Jeedom,
I want retrouver mes prises et relais simples dans HA,
so that je puisse piloter mes appareils électriques.

## Acceptance Criteria

1. **Given** le moteur de mapping traite un actionneur simple **When** ses *generic types de commandes* correspondent à un switch (Prise, Relais) **Then** le mapping produit une entité `switch` HA fiable
2. **And** le `device_class` HA est ajouté uniquement si le type plugin source (`eq_type_name`) confirme explicitement qu'il s'agit d'une prise électrique — aucun autre champ de métadonnée HA n'est ajouté
3. **And** les commandes ou valeurs invalides ne produisent aucune publication mensongère

## Hardened Definition of Done (Retrospective Epic 1 + Story 2.3)

- [x] **Validation Manuelle sur Box :** Story validée sur une vraie box Jeedom (pas seulement en mock/unit tests).
- [x] **Smoke Test MQTT Discovery :** Après `/action/sync`, vérifier avec `mosquitto_sub -t 'homeassistant/switch/#' -v --retained-only` que les topics de config sont publiés avec `retain=true` et un payload JSON valide.
- [x] **Contrôle de Pollution PHP :** Vérification qu'aucun `echo`, `warning` ou `notice` PHP ne vient polluer le retour JSON AJAX.
- [x] **Contrat d'Interface :** Payloads MQTT Discovery JSON validés par le schéma HA attendu (champs requis présents, `device_class` absent si non confirmé).
- [x] **Logs de Diagnostic :** Logs `[MAPPING]` et `[DISCOVERY]` explicites incluant la raison et la confiance de chaque décision, ainsi que la source de la décision `device_class`.
- [x] **Pas de Régression :** Lumières (2.2) et Volets (2.3) continuent de fonctionner sans changement.

## Tasks / Subtasks

- [x] **Task 1 — Créer le SwitchMapper capability-based (`mapping/switch.py`)** (AC: #1, #2, #3)
  - [x] 1.1 Créer `resources/daemon/mapping/switch.py` avec la classe `SwitchMapper`
    - Méthode `map(eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]`
    - Retourne `None` si l'équipement ne contient aucun *generic type de commande* `ENERGY_*`
    - Retourne un `MappingResult` avec capacités, confiance, raison
  - [x] 1.2 Créer `SwitchCapabilities` dans `resources/daemon/models/mapping.py` :
    ```python
    @dataclass
    class SwitchCapabilities:
        has_on_off: bool = False
        has_state: bool = False              # ENERGY_STATE présent parmi les cmds
        on_off_confidence: str = "unknown"   # "sure", "probable", "ambiguous"
        device_class: Optional[str] = None   # "outlet" si prise confirmée par eq_type_name, None sinon
    ```
  - [x] 1.3 Implémenter le mapping **capability-based** :

    > **Distinction vocabulaire :** Les *generic types de commandes* (`ENERGY_ON`, `ENERGY_OFF`, `ENERGY_STATE`) sont des attributs portés par les objets `JeedomCmd`. Le *`eq_type_name`* est un attribut de `JeedomEqLogic` qui indique le plugin Jeedom source. Ces deux sources servent à des choses distinctes (voir tableau ci-dessous).

    **Generic types de commandes Jeedom pour les prises / switches :**

    | Generic Type (cmd) | Type cmd | Sous-type | Rôle |
    |---|---|---|---|
    | `ENERGY_STATE` | info | binary | État on/off du switch |
    | `ENERGY_ON` | action | other | Allumer le switch |
    | `ENERGY_OFF` | action | other | Éteindre le switch |

    > `POWER` et `CONSUMPTION` sont des generic types de commandes Jeedom liés à l'énergie mais hors scope Story 2.4 — ils relèvent de Story 2.5 (capteurs numériques). Le SwitchMapper ne les traite pas et ne les inclut pas dans ses listes.

    **Phase 1 — Détection On/Off (basée sur generic types de commandes) :**

    | Commandes trouvées | `has_on_off` | `has_state` | `on_off_confidence` | Cas métier |
    |---|---|---|---|---|
    | `ENERGY_ON` + `ENERGY_OFF` + `ENERGY_STATE` | ✅ | ✅ | `sure` | Prise/relais avec retour d'état |
    | `ENERGY_ON` + `ENERGY_OFF` (sans `ENERGY_STATE`) | ✅ | ❌ | `probable` | Relais simple sans retour d'état |
    | `ENERGY_ON` seul (sans OFF ni STATE) | ✅ | ❌ | `probable` | Actionneur d'enclenchement sans retour |
    | `ENERGY_OFF` seul (sans ON ni STATE) | ✅ | ❌ | `probable` | Actionneur de déclenchement sans retour |
    | `ENERGY_STATE` seul (sans action) | ❌ | ✅ | orphan → `ambiguous` | Capteur d'état sans action — non publiable |

    > Un switch sans `ENERGY_STATE` reste publiable en `probable` — c'est un cas nominal pour les relais simples Jeedom qui n'exposent pas de retour d'état.

    **Phase 2 — `device_class` (basé sur `eq_type_name` du plugin source) :**

    La règle est conservatrice et figée :

    - `device_class = "outlet"` uniquement si `eq.eq_type_name.lower()` contient l'un de ces mots : `"prise"`, `"energie"`, `"energy"`, `"plug"`, `"outlet"`
    - `device_class = None` dans tous les autres cas — y compris `"z2m"`, `"mqtt"`, `"jeelink"` qui sont des plugins génériques qui gèrent aussi des lumières et capteurs

    > **Règle de décision unique :** Si `eq_type_name` ne contient pas un indice explicite de prise/énergie parmi la liste ci-dessus → `device_class = None`. Aucune autre logique. Aucune exception.

    **Tableau des cas métier relais / prise :**

    | Type d'équipement | Capacités détectées | `device_class` | Confiance | Publiable |
    |---|---|---|---|---|
    | Prise électrique confirmée (plugin énergie) | `ENERGY_ON + OFF + STATE` | `"outlet"` | `sure` | ✅ |
    | Prise électrique confirmée (plugin énergie) | `ENERGY_ON + OFF` | `"outlet"` | `probable` | ✅ |
    | Relais simple (plugin générique) | `ENERGY_ON + OFF + STATE` | `None` | `sure` | ✅ |
    | Relais simple (plugin générique) | `ENERGY_ON + OFF` | `None` | `probable` | ✅ |
    | Capteur d'état orphelin | `ENERGY_STATE` seul | `None` | `ambiguous` | ❌ |

    **Phase 3 — Confiance globale :**

    ```
    confidence = on_off_confidence
    ```

    > Les switches n'ont pas de capacité secondaire en V1. La confiance globale est directement celle de la détection On/Off. `device_class` ne contribue pas à la confiance.

    > **Un seul `MappingResult` par eqLogic.**

  - [x] 1.4 Implémenter la politique d'exposition **bornée à Story 2.4** :
    ```python
    SWITCH_PUBLICATION_POLICY = {
        "sure": True,
        "probable": True,    # bounded to switch cases listed in Task 1.3 Phase 1
        "ambiguous": False,
        "unknown": False,
        "ignore": False,
    }
    ```

    > La politique `probable → publier` est bornée aux cas de Story 2.4 uniquement. Ne pas l'extrapoler.

  - [x] 1.5 Implémenter les garde-fous anti faux-positifs :

    **Anti-affinité (basée sur generic types de commandes des autres domaines) :**
    ```python
    _ANTI_SWITCH_GENERIC_TYPES = {
        # Lumières — le LightMapper a déjà ENERGY_* dans ses anti-affinités ; symétrique ici
        "LIGHT_STATE", "LIGHT_ON", "LIGHT_OFF", "LIGHT_BRIGHTNESS", "LIGHT_SLIDER",
        # Volets
        "FLAP_STATE", "FLAP_UP", "FLAP_DOWN", "FLAP_STOP", "FLAP_SLIDER",
        "FLAP_BSO_STATE", "FLAP_BSO_UP", "FLAP_BSO_DOWN",
        # Chauffage
        "HEATING_STATE", "HEATING_ON", "HEATING_OFF",
        "THERMOSTAT_STATE", "THERMOSTAT_MODE", "THERMOSTAT_SETPOINT",
        # Alarme / serrure
        "SIREN_STATE", "SIREN_ON", "SIREN_OFF",
        "LOCK_STATE", "LOCK_OPEN", "LOCK_CLOSE",
    }
    ```

    Si un eqLogic contient des generic types de commandes `ENERGY_*` ET des generic types d'anti-affinité → `confidence = "ambiguous"`, pas de publication.

    **Exclusion par `eq.generic_type` (attribut équipement, distinct des generic types de commandes) :**
    - `eq.generic_type` est l'attribut de type d'équipement global, distinct des generic types portés par les commandes
    - Si `eq.generic_type` est fourni et n'est pas dans la liste `{"", "switch", "energy", "plug", "outlet", "prise"}` → retourner `None`

    **Heuristiques de noms :**
    ```python
    _NON_SWITCH_KEYWORDS = {
        "lumière", "lumiere", "light", "lampe", "ampoule",
        "volet", "store", "cover", "blind", "shutter", "portail", "garage",
        "chauffage", "radiateur", "thermostat", "heater",
        "fumée", "smoke", "alarme", "sirene",
    }
    ```
    Si le nom de l'équipement (`eq.name.lower()`) contient un de ces mots **et** que les generic types de commandes ne désambiguïsent pas → `confidence = "ambiguous"`.

    > Les mots-clés de prise (`prise`, `plug`, `socket`) ne sont PAS dans cette liste — ils sont intentionnellement publiables.

- [x] **Task 2 — Étendre le publisher pour les switches (`discovery/publisher.py`)** (AC: #1, #2)
  - [x] 2.1 Créer `publish_switch()` :
    ```python
    async def publish_switch(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        payload = self._build_switch_payload(mapping, snapshot)
        topic = self._build_topic(mapping.jeedom_eq_id, entity_type="switch")
        return await self.mqtt_bridge.publish_message(topic, payload, retain=True)
    ```
  - [x] 2.2 Implémenter `_build_switch_payload()` :

    **Topic de discovery :**
    ```
    homeassistant/switch/jeedom2ha_{jeedom_eq_id}/config
    ```

    **Payload JSON — Switch sans `device_class` (cas général) :**
    ```json
    {
      "name": "{eq_name}",
      "unique_id": "jeedom2ha_eq_{jeedom_eq_id}",
      "object_id": "jeedom2ha_{jeedom_eq_id}",
      "command_topic": "jeedom2ha/{jeedom_eq_id}/set",
      "payload_on": "ON",
      "payload_off": "OFF",
      "state_topic": "jeedom2ha/{jeedom_eq_id}/state",
      "state_on": "ON",
      "state_off": "OFF",
      "availability_topic": "jeedom2ha/bridge/status",
      "device": {
        "identifiers": ["jeedom2ha_{jeedom_eq_id}"],
        "name": "{eq_name}",
        "manufacturer": "Jeedom ({eq_type_name})",
        "model": "{eq_type_name}",
        "suggested_area": "{object_name or null}",
        "via_device": "jeedom2ha_bridge"
      },
      "origin": {
        "name": "jeedom2ha",
        "sw_version": "0.2.0"
      }
    }
    ```

    **Champ conditionnel `device_class` :**

    Si `capabilities.device_class == "outlet"` → ajouter au payload :
    ```json
    { "device_class": "outlet" }
    ```

    Si `capabilities.device_class is None` → **ne pas inclure `device_class`** dans le payload. Le champ est absent, pas à `null`.

    > Il n'y a pas d'autre champ conditionnel pour les switches en V1. Le payload est complet avec ou sans `device_class`.

  - [x] 2.3 Le payload MUST être publié avec `retain=True` sur le topic de config
  - [x] 2.4 L'unpublish = publier un payload vide `""` avec `retain=True` sur le topic switch via `unpublish_by_eq_id(eq_id, entity_type="switch")` — cette méthode est déjà entity-aware depuis Story 2.3, aucune modification nécessaire
  - [x] 2.5 Réutiliser `_build_device_block()` (méthode commune extraite en Story 2.3) pour construire le bloc `device`

- [x] **Task 3 — Intégrer le SwitchMapper dans le handler sync (`http_server.py`)** (AC: #1, #2, #3)
  - [x] 3.1 Importer `SwitchMapper` dans `http_server.py` :
    ```python
    from mapping.switch import SwitchMapper
    ```
  - [x] 3.2 Dans `_handle_action_sync`, instancier et chaîner le SwitchMapper **après** le CoverMapper :
    ```python
    light_mapper = LightMapper()
    cover_mapper = CoverMapper()
    switch_mapper = SwitchMapper()

    # Dans la boucle sur eligibility.items() :
    mapping = light_mapper.map(eq, snapshot)
    if mapping is None:
        mapping = cover_mapper.map(eq, snapshot)
    if mapping is None:
        mapping = switch_mapper.map(eq, snapshot)
    # mapping is None → eqLogic non mappé, continuer
    ```
  - [x] 3.3 Étendre `mapping_counters` avec les entrées switch :
    ```python
    mapping_counters = {
        "lights_sure": 0, "lights_probable": 0, "lights_ambiguous": 0,
        "lights_published": 0, "lights_skipped": 0,
        "covers_sure": 0, "covers_probable": 0, "covers_ambiguous": 0,
        "covers_published": 0, "covers_skipped": 0,
        "switches_sure": 0, "switches_probable": 0, "switches_ambiguous": 0,
        "switches_published": 0, "switches_skipped": 0,
    }
    ```
  - [x] 3.4 Ajouter le bloc `elif mapping.ha_entity_type == "switch":` dans la logique de comptage et publication :
    ```python
    elif mapping.ha_entity_type == "switch":
        if mapping.confidence == "sure":
            mapping_counters["switches_sure"] += 1
        elif mapping.confidence == "probable":
            mapping_counters["switches_probable"] += 1
        elif mapping.confidence == "ambiguous":
            mapping_counters["switches_ambiguous"] += 1

        decision = switch_mapper.decide_publication(mapping)
        publications[eq_id] = decision
        nouveaux_eq_ids.add(eq_id)

        if decision.should_publish:
            mapping_counters["switches_published"] += 1
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                await publisher.publish_switch(mapping, snapshot)
        else:
            mapping_counters["switches_skipped"] += 1
    ```
  - [x] 3.5 Mettre à jour le log de résumé `[MAPPING]` pour inclure les compteurs switch (pattern identique aux lights et covers existants)
  - [x] 3.6 Vérifier que `unpublish_by_eq_id(old_eq_id, entity_type=entity_type)` fonctionne sans modification avec `entity_type="switch"` — la méthode est déjà générique depuis Story 2.3
  - [x] 3.7 Le résumé `mapping_summary` dans la réponse JSON inclut les compteurs switch :
    ```json
    {
      "mapping_summary": {
        "lights_sure": 5, "lights_probable": 2, "lights_ambiguous": 1,
        "lights_published": 7, "lights_skipped": 1,
        "covers_sure": 3, "covers_probable": 1, "covers_ambiguous": 0,
        "covers_published": 4, "covers_skipped": 0,
        "switches_sure": 4, "switches_probable": 2, "switches_ambiguous": 0,
        "switches_published": 6, "switches_skipped": 0
      }
    }
    ```

- [x] **Task 4 — Tests unitaires Python** (AC: tous)
  - [x] 4.1 Créer `tests/unit/test_switch_mapper.py` — cas à couvrir :
    - **Cas `sure` :** EqLogic avec generic types `ENERGY_ON` + `ENERGY_OFF` + `ENERGY_STATE` → `confidence=sure`, `has_on_off=True`, `has_state=True`
    - **Cas `probable` (On+Off) :** EqLogic avec `ENERGY_ON` + `ENERGY_OFF` (sans `ENERGY_STATE`) → `confidence=probable`, `has_state=False`
    - **Cas `probable` (On seul) :** EqLogic avec `ENERGY_ON` seul → `confidence=probable`
    - **Cas `probable` (Off seul) :** EqLogic avec `ENERGY_OFF` seul → `confidence=probable`
    - **Cas orphan :** EqLogic avec `ENERGY_STATE` seul → `confidence=ambiguous`, pas de publication
    - **Cas None :** EqLogic sans aucun generic type `ENERGY_*` → `map()` retourne `None`
    - **Anti-affinité LIGHT_* :** EqLogic avec `ENERGY_ON + OFF` ET `LIGHT_ON` → `confidence=ambiguous`
    - **Anti-affinité FLAP_* :** EqLogic avec `ENERGY_ON + OFF` ET `FLAP_UP` → `confidence=ambiguous`
    - **Exclusion `eq.generic_type` :** EqLogic avec `eq.generic_type = "HEATER"` et `ENERGY_ON + OFF` → `map()` retourne `None`
    - **`device_class=outlet` :** EqLogic avec `eq_type_name = "plugin_energie_gestion"` → `capabilities.device_class = "outlet"`
    - **`device_class=None` (plugin générique) :** EqLogic avec `eq_type_name = "z2m"` → `capabilities.device_class = None`
    - **`device_class=None` (plugin MQTT) :** EqLogic avec `eq_type_name = "mqtt"` → `capabilities.device_class = None`
    - **Heuristique nom :** EqLogic avec `name = "Volet garage"` ET `ENERGY_ON + OFF` → `confidence=ambiguous`
    - **Heuristique nom — non rejeté :** EqLogic avec `name = "Prise cuisine"` ET `ENERGY_ON + OFF` → `confidence=sure` ou `probable` (le mot "prise" n'est pas dans `_NON_SWITCH_KEYWORDS`)
    - **`ha_unique_id` :** Vérifié au format `"jeedom2ha_eq_{eq.id}"`
    - **`suggested_area` :** Extrait depuis `snapshot.get_suggested_area(eq.id)`
    - **PublicationDecision :** `sure` → `should_publish=True`, `probable` → `should_publish=True`, `ambiguous` → `should_publish=False`
  - [x] 4.2 Ajouter des tests switch dans `tests/unit/test_discovery_publisher.py` :
    - **Payload basique :** Contient tous les champs requis (`command_topic`, `payload_on`, `payload_off`, `state_topic`, `state_on`, `state_off`, `availability_topic`, `device`, `origin`)
    - **Sans `device_class` :** Payload avec `capabilities.device_class = None` → le payload ne contient pas la clé `"device_class"`
    - **Avec `device_class` :** Payload avec `capabilities.device_class = "outlet"` → le payload contient `"device_class": "outlet"`
    - **Topic :** `homeassistant/switch/jeedom2ha_{id}/config`
    - **Retain :** `publish_message()` appelé avec `retain=True`
    - **Unpublish :** `unpublish_by_eq_id(eq_id, entity_type="switch")` publie payload vide avec `retain=True` sur le bon topic
    - **`suggested_area` absent :** Si `snapshot.get_suggested_area()` retourne `None` → clé `"suggested_area"` absente du bloc `device`

- [x] **Task 5 — Smoke Test MQTT Discovery** (DoD)
  - [x] 5.1 Sur une box Jeedom avec broker MQTT actif :
    1. Daemon lancé
    2. `/action/sync` déclenché
    3. `mosquitto_sub -t 'homeassistant/switch/#' -v --retained-only` → topics publiés avec payload JSON valide
    4. `retain=true` effectif vérifié
    5. Lumières (2.2) et Volets (2.3) continuent de fonctionner — aucune régression

## Dev Notes

### Distinction des deux sources d'information

> **Règle transverse Story 2.4 — à mémoriser :**
>
> | Source | Attribut | Sert à |
> |---|---|---|
> | `JeedomCmd.generic_type` | `ENERGY_ON`, `ENERGY_OFF`, `ENERGY_STATE` | Détecter les capacités → mapping |
> | `JeedomEqLogic.eq_type_name` | ex: `"plugin_energie"`, `"z2m"` | Déduire le `device_class` |
> | `JeedomEqLogic.generic_type` | ex: `"switch"`, `"HEATER"`, `""` | Exclusion par type d'équipement |
>
> Ces trois niveaux sont distincts. Ne pas les confondre dans le code.

### Architecture & Patterns obligatoires

**Flux de mapping + publication (extension de Stories 2.2 et 2.3) :**

```
Topologie normalisée (RAM)
  → SwitchMapper.map(eqLogic) → MappingResult (type="switch", capabilities, confiance, raison)
  → PublicationDecision (should_publish basé sur confiance + politique bornée Story 2.4)
  → DiscoveryPublisher.publish_switch(mapping, snapshot) → MQTT publish retained
  → Décisions détaillées stockées en RAM (app['publications']) pour Epic 4
```

**Chaîne de mappers dans le sync handler :**

```python
# Ordre : LightMapper → CoverMapper → SwitchMapper → (Story 2.5+)
# Premier mapper retournant non-None gagne.
# LIGHT_* est prioritaire (explicite). FLAP_* avant ENERGY_* (moins ambigu).
# SwitchMapper en dernier : ENERGY_* est le generic type le plus partagé.
mapping = light_mapper.map(eq, snapshot)
if mapping is None:
    mapping = cover_mapper.map(eq, snapshot)
if mapping is None:
    mapping = switch_mapper.map(eq, snapshot)
```

**Organisation des modules Python :**

```
resources/daemon/
  mapping/
    __init__.py           # EXISTE
    light.py              # EXISTE — ne pas modifier
    cover.py              # EXISTE — ne pas modifier
    switch.py             # CRÉER : SwitchMapper
  discovery/
    publisher.py          # MODIFIER : ajouter publish_switch(), _build_switch_payload()
  models/
    mapping.py            # MODIFIER : ajouter SwitchCapabilities, étendre MappingResult.capabilities
  transport/
    http_server.py        # MODIFIER : SwitchMapper dans la boucle sync, compteurs switch
```

**Réutilisation du code Stories 2.2 et 2.3 :**

- `_min_confidence()` + `_CONFIDENCE_ORDER` : Dupliquer dans `switch.py` (3 lignes — décision Story 2.3 : duplication > refactoring prématuré)
- Interfaces `map()` et `decide_publication()` : identiques à `LightMapper` et `CoverMapper`
- `_build_device_block()` : méthode existante sur `DiscoveryPublisher` — réutiliser directement
- `_build_topic(eq_id, entity_type="switch")` : méthode existante — appel direct
- `MqttBridge.publish_message()` : API publique — ne pas accéder à `_client` directement
- Fixtures de tests `_make_eq()`, `_cmd()` : reprendre le pattern de `test_cover_mapper.py`

### HA MQTT Discovery — Switch schema

- `command_topic` : `jeedom2ha/{eq_id}/set`
- `payload_on` = `"ON"`, `payload_off` = `"OFF"` (valeurs par défaut HA — ne pas changer)
- `state_topic` : `jeedom2ha/{eq_id}/state`
- `state_on` = `"ON"`, `state_off` = `"OFF"` (valeurs par défaut HA)
- `device_class` : `"outlet"` si confirmé / **absent** sinon — jamais `"switch"` (n'est pas un `device_class` HA valide)
- `retain=True` sur le topic de config uniquement

**Référence :** [HA MQTT Switch — Default Schema](https://www.home-assistant.io/integrations/switch.mqtt/)

### Convention unique_id et topics MQTT

- `unique_id` : `"jeedom2ha_eq_{eq.id}"` — même format que lights et covers
- `object_id` : `"jeedom2ha_{eq.id}"`
- `command_topic` : `"jeedom2ha/{eq.id}/set"`
- `state_topic` : `"jeedom2ha/{eq.id}/state"`
- `availability_topic` : `"jeedom2ha/bridge/status"` (configuré Story 1.3)

> Un même eqLogic ne peut produire qu'une seule entité HA. La chaîne Light→Cover→Switch le garantit (premier mapper non-`None` gagne).

### HA UX — Entités Inertes (Dette Technique Epic 2)

> Les topics `state_topic` et `command_topic` ne sont pas alimentés en Epic 2. Les switches apparaîtront dans HA sans état ni contrôle réel. Résolu en Epic 3.

### Garde-fous aiohttp

`app['mappings']` et `app['publications']` sont pré-initialisés depuis Story 2.2. `app['topology']` et `app['eligibility']` depuis Story 2.3. **Aucune nouvelle clé `app` à ajouter** — les switches s'insèrent dans les dicts existants.

### Architecture Note V2 (Story 2.4)

> [!IMPORTANT]
> **Discovery vs Sync :** La découverte MQTT des switches est complète et validée en Epic 2. Cependant, les entités apparaissent comme **inertes** dans Home Assistant (pas de retour d'état, pas de contrôle possible). L'alimentation réelle du `state_topic` et la gestion du `command_topic` sont l'objectif de l'Epic 3.

### Pièges à éviter

- **NE PAS** mettre `device_class: "switch"` dans le payload — non valide comme `device_class` HA pour switch.mqtt
- **NE PAS** mettre `device_class: "outlet"` sans confirmation par `eq_type_name` — respecte AC#2
- **NE PAS** inclure `POWER` ou `CONSUMPTION` dans `_SWITCH_GENERIC_TYPES` — scope Story 2.5
- **NE PAS** modifier `mapping/light.py`, `mapping/cover.py`, `models/topology.py`
- **NE PAS** créer deux entités HA pour un même eqLogic
- **NE PAS** créer le module `sync/` — scope Epic 3
- **NE PAS** implémenter la réception de commandes HA → Jeedom — scope Story 3.2
- **NE PAS** ajouter de clés `request.app[...]` dynamiquement
- **NE PAS** extrapoler la politique `probable=True` aux stories suivantes

### Écarts hérités à respecter

| Champ spec | Champ réel dans le code | Raison |
|---|---|---|
| `jeedom_eq_id` | `eq.id` sur `JeedomEqLogic` | Convention adoptée Story 2.1 |
| `cmd_type` | `cmd.type` sur `JeedomCmd` | Shadow du builtin Python, accepté |
| `eq_type` | `eq.eq_type_name` sur `JeedomEqLogic` | Plus explicite |

### Déviation architecture documentée

Tests dans `tests/` (racine du repo), non dans `resources/daemon/tests/` — déviation héritée Story 1.1, à conserver.

### Project Structure Notes

- Nouveaux fichiers : `resources/daemon/mapping/switch.py`, `tests/unit/test_switch_mapper.py`
- Fichiers modifiés : `resources/daemon/models/mapping.py`, `resources/daemon/discovery/publisher.py`, `resources/daemon/transport/http_server.py`, `tests/unit/test_discovery_publisher.py`
- Aucun conflit avec la structure existante

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4]
- [Source: _bmad-output/planning-artifacts/architecture.md#Mapping Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#MVP Guardrails]
- [Source: _bmad-output/implementation-artifacts/2-3-mapping-exposition-des-ouvrants-volets.md#Dev Notes]
- [Source: home-assistant.io/integrations/switch.mqtt — Default Schema]
- [Source: doc.jeedom.com/en_US/core/4.3/types — Energy Generic Types]

---

## Supervisor Notes

> Section de cadrage final — à lire avant de lancer le workflow dev.

### Décisions figées (ne pas ré-ouvrir)

| Décision | Valeur retenue |
|---|---|
| `device_class` valide | `"outlet"` uniquement |
| Critère déclenchement `"outlet"` | `eq_type_name` contient `"prise"`, `"energie"`, `"energy"`, `"plug"` ou `"outlet"` ; sinon `None` |
| Plugins génériques (`z2m`, `mqtt`, `jeelink`) | → `device_class = None` |
| Icon HA | Géré automatiquement par HA selon `device_class` — aucun champ `icon` dans le payload |
| confidence `probable` | Publiable en Story 2.4 (bounded) |
| Ordre de chaîne de mappers | Light → Cover → Switch — non négociable |
| Tests | Dans `tests/` racine (déviation héritée 2.1) |

### Points volontairement hors scope

- `POWER`, `CONSUMPTION` — Story 2.5 (sensors numériques)
- Réception commandes HA → Jeedom — Story 3.2
- Alimentation `state_topic` et `command_topic` — Story 3.1
- Politique de confiance configurable — Story 4.3
- Exclusions multicritères — Story 4.3

### Risques résiduels connus

- **Faux positifs relais/chauffage :** Certains plugins thermostat utilisent `ENERGY_ON/OFF` pour piloter des relais. Les heuristiques de noms (`_NON_SWITCH_KEYWORDS`) et anti-affinités (`HEATING_*`) réduisent ce risque mais ne l'éliminent pas totalement. Accepté en V1 — diagnostic Epic 4.
- **`eq_type_name` non normalisé :** Les valeurs de `eq_type_name` sont libres (plugin Jeedom). La règle de détection `device_class` est donc best-effort, non exhaustive. `None` par défaut est le comportement sûr.
- **Entités inertes en Epic 2 :** Les switches publiés n'auront pas d'état ni de contrôle réel avant Epic 3. Comportement documenté et attendu.

---

## Validation Record (Story 2.4)

### 1. Log [MAPPING] — Succès (Prise/Outlet)
```text
[INFO] [MAPPING] eq_id=42 name='Prise Salon': switch_on_off_state confidence=sure (has_on_off=True/sure, has_state=True, device_class=outlet)
[DEBUG] [MAPPING] eq_id=42 eq_type_name='plugin_energie_gestion' → device_class='outlet' (keyword='energie')
```

### 2. Payload MQTT Discovery — Outlet
**Topic :** `homeassistant/switch/jeedom2ha_42/config` (Retained)
```json
{
  "name": "Prise Salon",
  "unique_id": "jeedom2ha_eq_42",
  "object_id": "jeedom2ha_42",
  "command_topic": "jeedom2ha/42/set",
  "payload_on": "ON",
  "payload_off": "OFF",
  "state_topic": "jeedom2ha/42/state",
  "state_on": "ON",
  "state_off": "OFF",
  "device_class": "outlet",
  "availability_topic": "jeedom2ha/bridge/status",
  "device": {
    "identifiers": ["jeedom2ha_42"],
    "name": "Prise Salon",
    "manufacturer": "Jeedom (plugin_energie_gestion)",
    "model": "plugin_energie_gestion",
    "via_device": "jeedom2ha_bridge"
  }
}
```

### 3. Log [MAPPING] — Cas Ambigu (Heuristique Nom)
```text
[INFO] [MAPPING] eq_id=99 name='Lumière Plafond': name contains non-switch keyword 'lumière' → ambiguous
[INFO] [MAPPING] eq_id=99 publication_decision: should_publish=False reason=ambiguous_skipped confidence=ambiguous
```

---

## Dev Agent Record

### Agent Model Used

Antigravity (Google DeepMind)

### Completion Notes List

- Implémentation du SwitchMapper avec gestion des generic types ENERGY_ON/OFF/STATE.
- Politique d'exposition probable = True appliquée uniquement aux switches.
- Garde-fous implémentés : anti-affinité (Light/Cover/Heating/Alarm), exclusions par eq.generic_type, et heuristiques de noms.
- device_class restreint à "outlet" basé sur une whitelist de mots-clés dans eq_type_name.
- Intégration complète dans http_server.py avec mise à jour des compteurs et du résumé JSON.
- Validation par 119 tests unitaires (35 nouveaux tests switch).

### File List

- resources/daemon/mapping/switch.py
- resources/daemon/models/mapping.py
- resources/daemon/discovery/publisher.py
- resources/daemon/transport/http_server.py
- tests/unit/test_switch_mapper.py
- tests/unit/test_discovery_publisher.py
