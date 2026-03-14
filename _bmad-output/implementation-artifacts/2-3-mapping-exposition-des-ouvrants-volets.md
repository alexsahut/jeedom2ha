# Story 2.3: Mapping & Exposition des Ouvrants (Volets)

Status: done

## Story

As a utilisateur Jeedom,
I want retrouver mes volets et brise-soleil dans HA sans fausse représentation,
so that je gère les ouvertures de ma maison sereinement.

## Acceptance Criteria

1. **Given** le moteur de mapping traite un volet **When** les commandes de positionnement sont analysées **Then** si la position n'est pas disponible ou pas honnêtement mappable, le volet reste publié avec les capacités disponibles (open/close/stop) sans inventer de position
2. **And** la publication MQTT Discovery reflète fidèlement les capacités réelles détectées
3. **And** les inversions de sens configurées dans Jeedom sont respectées

## Hardened Definition of Done (Retrospective Epic 1)

- [ ] **Validation Manuelle sur Box :** Story validée sur une vraie box Jeedom (pas seulement en mock/unit tests).
- [ ] **Smoke Test MQTT Discovery :** Après `/action/sync`, vérifier avec `mosquitto_sub -t 'homeassistant/cover/#' -v --retained-only` que les topics de config sont publiés avec `retain=true` et un payload JSON valide.
- [ ] **Contrôle de Pollution PHP :** Vérification qu'aucun `echo`, `warning` ou `notice` PHP ne vient polluer le retour JSON AJAX.
- [ ] **Contrat d'Interface :** Payloads MQTT Discovery JSON validés par le schéma HA attendu.
- [ ] **Logs de Diagnostic :** Logs `[MAPPING]` et `[DISCOVERY]` explicites incluant la raison et la confiance de chaque décision.

## Tasks / Subtasks

- [x] **Task 1 — Créer le CoverMapper capability-based (`mapping/cover.py`)** (AC: #1, #3)
  - [x] 1.1 Créer `resources/daemon/mapping/cover.py` avec la classe `CoverMapper`
    - Méthode `map(eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]`
    - Retourne `None` si l'équipement ne contient aucune commande `FLAP_*`
    - Retourne un `MappingResult` avec capacités cumulées, confiance, raison
  - [x] 1.2 Créer `CoverCapabilities` dans `resources/daemon/models/mapping.py` :
    ```python
    @dataclass
    class CoverCapabilities:
        has_open_close: bool = False
        has_stop: bool = False
        has_position: bool = False
        is_bso: bool = False              # Brise-Soleil Orientable
        open_close_confidence: str = "unknown"
        position_confidence: str = "unknown"
    ```
  - [x] 1.3 Implémenter le mapping **capability-based** :

    Le mapper détecte les capacités **indépendamment** puis les cumule en une seule entité `cover` :

    **Jeedom Generic Types pour les volets :**

    | Generic Type | Type cmd | Sous-type | Rôle |
    |---|---|---|---|
    | `FLAP_STATE` | info | binary ou numeric | État du volet |
    | `FLAP_UP` | action | other | Monter |
    | `FLAP_DOWN` | action | other | Descendre |
    | `FLAP_STOP` | action | other | Stop |
    | `FLAP_SLIDER` | action | slider | Position (0-100) |
    | `FLAP_BSO_STATE` | info | binary ou numeric | État BSO |
    | `FLAP_BSO_UP` | action | other | Monter BSO |
    | `FLAP_BSO_DOWN` | action | other | Descendre BSO |

    **Phase 1 — Détection Open/Close :**

    | Commandes trouvées | Résultat `has_open_close` | `open_close_confidence` |
    |---|---|---|
    | `FLAP_UP` + `FLAP_DOWN` + `FLAP_STATE` | ✅ | `sure` |
    | `FLAP_UP` + `FLAP_DOWN` (sans `FLAP_STATE`) | ✅ | `probable` — pas de retour d'état |
    | `FLAP_BSO_UP` + `FLAP_BSO_DOWN` + `FLAP_BSO_STATE` | ✅ | `sure` (BSO) |
    | `FLAP_BSO_UP` + `FLAP_BSO_DOWN` (sans `FLAP_BSO_STATE`) | ✅ | `probable` (BSO) |
    | `FLAP_SLIDER` seul (sans UP/DOWN) | ✅ implicite | `sure` — le slider gère open/close via valeur 0/100 |

    **Phase 2 — Détection Stop :**

    | Commandes trouvées | Résultat `has_stop` |
    |---|---|
    | `FLAP_STOP` présent | ✅ |
    | `FLAP_STOP` absent | ❌ |

    > Stop n'affecte pas la confiance globale — c'est une capacité optionnelle.

    **Phase 3 — Détection Position :**

    | Commandes trouvées | Résultat `has_position` | `position_confidence` |
    |---|---|---|
    | `FLAP_SLIDER` (action/slider) + `FLAP_STATE` (info/numeric) | ✅ | `sure` — slider + état numérique |
    | `FLAP_SLIDER` sans `FLAP_STATE` numérique | ✅ | `probable` — slider sans retour de position |

    > **NE PAS** inventer de position si `FLAP_SLIDER` est absent (AC#1).

    **Phase 4 — Détection BSO :**

    | Commandes trouvées | Résultat `is_bso` |
    |---|---|
    | Présence d'au moins un `FLAP_BSO_*` | ✅ |
    | Aucun `FLAP_BSO_*` | ❌ |

    > BSO affecte le `device_class` dans le payload discovery (`blind` vs `shutter`).

    **Phase 5 — Confiance globale de l'entité :**

    ```
    confidence = worst(open_close_confidence, position_confidence) si position détectée
    confidence = open_close_confidence si pas de position
    ```

    > Utilise la même fonction `_min_confidence` que `LightMapper` (sémantique = `max()` sur l'ordre).

    - Si au moins Open/Close → entité `cover` publiable (selon politique)
    - Si `FLAP_STATE` orphelin (seul, sans action) → `ambiguous`

    > **Un seul `MappingResult` par eqLogic**, avec les flags `has_open_close`, `has_stop`, `has_position`, `is_bso` cumulés.

  - [x] 1.4 Implémenter la politique d'exposition **bornée à Story 2.3** :
    ```python
    COVER_PUBLICATION_POLICY = {
        "sure": True,
        "probable": True,     # bounded to cover cases listed in Task 1.3
        "ambiguous": False,
        "unknown": False,
        "ignore": False,
    }
    ```

    > La politique `probable → publier` est bornée aux cas de Story 2.3 uniquement.

  - [x] 1.5 Implémenter les garde-fous anti faux-positifs (comme LightMapper) :

    **Anti-affinité (Conflits) :**
    ```python
    _ANTI_COVER_GENERIC_TYPES = {
        "LIGHT_STATE", "LIGHT_ON", "LIGHT_OFF", "LIGHT_BRIGHTNESS", "LIGHT_SLIDER",
        "HEATING_STATE", "HEATING_ON", "HEATING_OFF",
        "THERMOSTAT_STATE", "THERMOSTAT_MODE", "THERMOSTAT_SETPOINT",
        "ENERGY_STATE", "ENERGY_ON", "ENERGY_OFF",
        "SIREN_STATE", "SIREN_ON", "SIREN_OFF",
        "LOCK_STATE", "LOCK_OPEN", "LOCK_CLOSE",
    }
    ```

    **Exclusion par eq.generic_type explicite :**
    - Si `eq.generic_type` est fourni et n'est pas `"shutter"`, `"cover"`, `"blind"`, `"flap"`, `""` → retourner `None`

    **Heuristiques de noms :** (optionnel pour les volets — moins de risque de faux positifs que pour les lumières, mais garder les cas évidents)
    ```python
    _NON_COVER_KEYWORDS = {
        "lumière", "lumiere", "light", "lampe", "ampoule",
        "chauffage", "radiateur", "thermostat", "heater",
        "prise", "plug", "socket",
        "fumée", "smoke", "alarme", "sirene",
    }
    ```

- [x] **Task 2 — Étendre le publisher pour les covers (`discovery/publisher.py`)** (AC: #2)
  - [x] 2.1 Refactorer `_build_topic()` pour accepter le type d'entité :
    ```python
    def _build_topic(self, eq_id: int, entity_type: str = "light") -> str:
        return f"{self._topic_prefix}/{entity_type}/jeedom2ha_{eq_id}/config"
    ```
  - [x] 2.2 Mettre à jour `publish_light()` pour passer `entity_type="light"` à `_build_topic()`
  - [x] 2.3 Mettre à jour `unpublish_by_eq_id()` pour accepter `entity_type` :
    ```python
    async def unpublish_by_eq_id(self, eq_id: int, entity_type: str = "light") -> bool:
    ```
  - [x] 2.4 Créer `publish_cover()` :
    ```python
    async def publish_cover(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
    ```
  - [x] 2.5 Implémenter `_build_cover_payload()` :

    **Topic de discovery :**
    ```
    homeassistant/cover/jeedom2ha_{jeedom_eq_id}/config
    ```

    **Payload JSON — Cover Open/Close basique (sans position) :**
    ```json
    {
      "name": "{eq_name}",
      "unique_id": "jeedom2ha_eq_{jeedom_eq_id}",
      "object_id": "jeedom2ha_{jeedom_eq_id}",
      "command_topic": "jeedom2ha/{jeedom_eq_id}/set",
      "payload_open": "OPEN",
      "payload_close": "CLOSE",
      "state_topic": "jeedom2ha/{jeedom_eq_id}/state",
      "state_open": "open",
      "state_closed": "closed",
      "device_class": "shutter",
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

    **Champs conditionnels :**

    Si `has_stop=True` :
    ```json
    { "payload_stop": "STOP" }
    ```

    Si `has_position=True` :
    ```json
    {
      "position_topic": "jeedom2ha/{jeedom_eq_id}/position",
      "set_position_topic": "jeedom2ha/{jeedom_eq_id}/position/set",
      "position_open": 100,
      "position_closed": 0
    }
    ```

    Si `is_bso=True` :
    ```json
    { "device_class": "blind" }
    ```
    (remplace "shutter" par défaut)

    > Le payload est **un seul JSON** qui inclut les champs conditionnels si les capacités sont détectées.

  - [x] 2.6 Le payload MUST être publié avec `retain=True` sur le topic de config
  - [x] 2.7 L'unpublish = publier un payload vide `""` avec `retain=True` sur le même topic cover

- [x] **Task 3 — Intégrer le CoverMapper dans le handler sync (`http_server.py`)** (AC: #1, #2)
  - [x] 3.1 Importer `CoverMapper` dans `http_server.py` :
    ```python
    from mapping.cover import CoverMapper
    ```
  - [x] 3.2 Dans `_handle_action_sync`, ajouter le CoverMapper **après** le LightMapper :
    ```python
    light_mapper = LightMapper()
    cover_mapper = CoverMapper()

    for eq_id, result in eligibility.items():
        if not result.is_eligible:
            continue
        eq = snapshot.eq_logics.get(eq_id)
        if not eq:
            continue

        # Try light first
        mapping = light_mapper.map(eq, snapshot)
        if mapping is None:
            # Try cover
            mapping = cover_mapper.map(eq, snapshot)

        if mapping is None:
            continue  # Not mapped by any mapper

        mappings[eq_id] = mapping
        # ... rest of logic
    ```
  - [x] 3.3 Étendre `mapping_counters` avec les compteurs cover :
    ```python
    mapping_counters = {
        "lights_sure": 0, "lights_probable": 0, "lights_ambiguous": 0,
        "lights_published": 0, "lights_skipped": 0,
        "covers_sure": 0, "covers_probable": 0, "covers_ambiguous": 0,
        "covers_published": 0, "covers_skipped": 0,
    }
    ```
  - [x] 3.4 Adapter la logique de comptage et de publication selon `ha_entity_type` :
    ```python
    if mapping.ha_entity_type == "light":
        decision = light_mapper.decide_publication(mapping)
        # count lights_...
        if decision.should_publish and publisher and mqtt_bridge.is_connected:
            await publisher.publish_light(mapping, snapshot)
    elif mapping.ha_entity_type == "cover":
        decision = cover_mapper.decide_publication(mapping)
        # count covers_...
        if decision.should_publish and publisher and mqtt_bridge.is_connected:
            await publisher.publish_cover(mapping, snapshot)
    ```
  - [x] 3.5 Adapter le nettoyage des équipements disparus (unpublish) pour connaître le `entity_type` :
    ```python
    for old_eq_id in eq_ids_supprimes:
        old_decision = request.app["publications"].get(old_eq_id)
        if old_decision and old_decision.should_publish:
            entity_type = old_decision.mapping_result.ha_entity_type
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                await publisher.unpublish_by_eq_id(old_eq_id, entity_type=entity_type)
    ```
  - [x] 3.6 Le résumé `mapping_summary` dans la réponse JSON inclut les compteurs cover :
    ```json
    {
      "mapping_summary": {
        "lights_sure": 5, "lights_probable": 2, "lights_ambiguous": 1,
        "lights_published": 7, "lights_skipped": 1,
        "covers_sure": 3, "covers_probable": 1, "covers_ambiguous": 0,
        "covers_published": 4, "covers_skipped": 0
      }
    }
    ```

- [x] **Task 4 — Tests unitaires Python** (AC: tous)
  - [x] 4.1 Créer `tests/unit/test_cover_mapper.py` :
    - EqLogic avec `FLAP_STATE` + `FLAP_UP` + `FLAP_DOWN` → Open/Close `sure`, `has_position=False`
    - EqLogic avec `FLAP_UP` + `FLAP_DOWN` (sans `FLAP_STATE`) → Open/Close `probable`
    - EqLogic avec `FLAP_STATE` + `FLAP_UP` + `FLAP_DOWN` + `FLAP_STOP` → Open/Close `sure`, `has_stop=True`
    - EqLogic avec `FLAP_STATE` (numeric) + `FLAP_UP` + `FLAP_DOWN` + `FLAP_SLIDER` → `has_position=True`, position `sure`
    - EqLogic avec `FLAP_SLIDER` sans `FLAP_STATE` numérique → `has_position=True`, position `probable`
    - EqLogic avec `FLAP_SLIDER` seul (sans UP/DOWN) → Open/Close `sure` (implicite via slider)
    - EqLogic avec `FLAP_BSO_STATE` + `FLAP_BSO_UP` + `FLAP_BSO_DOWN` → `is_bso=True`, confiance `sure`
    - EqLogic avec `FLAP_STATE` seul → confidence `ambiguous` (orphan)
    - EqLogic sans aucun `FLAP_*` → retourne `None`
    - EqLogic avec commandes mixtes (FLAP + LIGHT) → `ambiguous` via anti-affinité
    - EqLogic avec `eq.generic_type = "HEATER"` et commandes FLAP → retourne `None`
    - Vérifier `ha_unique_id` au format `jeedom2ha_eq_{id}`
    - Vérifier `suggested_area` extrait du snapshot
    - PublicationDecision : `sure` → publish, `probable` → publish, `ambiguous` → skip
    - **Capacités cumulées complètes :** `FLAP_STATE(numeric)` + `FLAP_UP` + `FLAP_DOWN` + `FLAP_STOP` + `FLAP_SLIDER` → une seule entité cover avec `has_open_close=True(sure)` + `has_stop=True` + `has_position=True(sure)`, confiance globale `sure`
  - [x] 4.2 Ajouter des tests cover dans `tests/unit/test_discovery_publisher.py` :
    - Payload cover basique contient tous les champs requis (command_topic, payload_open/close, state_topic, device_class, device, origin)
    - Payload cover avec stop contient `payload_stop`
    - Payload cover avec position contient `position_topic`, `set_position_topic`, `position_open=100`, `position_closed=0`
    - Payload BSO a `device_class: "blind"` au lieu de `"shutter"`
    - Topic = `homeassistant/cover/jeedom2ha_{id}/config`
    - Retain = True sur publish
    - Unpublish cover envoie payload vide avec retain=True sur le topic cover
    - `suggested_area` absent du `device` si l'objet Jeedom est None

- [x] **Task 5 — Smoke Test MQTT Discovery** (DoD) — ✅ Validé sur box Jeedom 2026-03-14
  - [x] 5.1 Sur une box Jeedom avec broker MQTT actif :
    1. Daemon lancé
    2. `/action/sync` déclenché
    3. `mosquitto_sub -t 'homeassistant/cover/#' -v --retained-only` : topics publiés ✅
    4. Payload JSON valide avec champs requis ✅
    5. `retain=true` effectif ✅
    6. Lumières (Story 2.2) continuent de fonctionner ✅ (pas de régression)

## Dev Notes

### Architecture & Patterns obligatoires

**Flux de mapping + publication (extension de Story 2.2) :**

```
Topologie normalisée (RAM)
  → CoverMapper.map(eqLogic) → MappingResult (type="cover", capabilities cumulées, confiance, raison)
  → PublicationDecision (should_publish basé sur confiance + politique bornée)
  → DiscoveryPublisher.publish_cover(mapping, snapshot) → MQTT publish retained
  → Décisions détaillées stockées en RAM (app['publications']) pour Epic 4
```

**Chaîne de mappers dans le sync handler :**

```python
# Ordre d'évaluation : LightMapper → CoverMapper → (futurs mappers Story 2.4+)
# Premier mapper qui retourne non-None gagne.
# Les anti-affinités de chaque mapper empêchent les conflits.
mapping = light_mapper.map(eq, snapshot)
if mapping is None:
    mapping = cover_mapper.map(eq, snapshot)
```

**Organisation des modules Python (architecture.md §3) :**

```
resources/daemon/
  mapping/
    __init__.py           # EXISTE
    light.py              # EXISTE — ne pas modifier
    cover.py              # CRÉER: CoverMapper
  discovery/
    __init__.py           # EXISTE
    publisher.py          # MODIFIER: ajouter publish_cover(), refactorer _build_topic()
  models/
    __init__.py            # EXISTE
    topology.py            # EXISTE — ne pas modifier
    mapping.py             # MODIFIER: ajouter CoverCapabilities
  transport/
    http_server.py         # MODIFIER: ajouter CoverMapper dans la boucle sync
```

**Réutilisation du code Story 2.2 :**

- `_min_confidence()` de `mapping/light.py` : Extraire dans un module partagé ou ré-implémenter dans cover.py (préférer la duplication plutôt qu'un refactoring prématuré — la fonction est courte, 3 lignes)
- `_CONFIDENCE_ORDER` : Même dict, même sémantique
- Pattern de mapper : même interface `map() → Optional[MappingResult]` + `decide_publication() → PublicationDecision`
- Pattern de publisher : même approche `_build_*_payload()` → JSON → publish retained
- Pattern de tests : même structure `_make_eq()`, `_cmd()`, classes TestXxx

### HA MQTT Discovery — Cover schema

Le plugin utilise le **default schema** pour `cover`. Champs critiques :

- `command_topic` : topic pour les commandes (OPEN/CLOSE/STOP)
- `payload_open` = `"OPEN"`, `payload_close` = `"CLOSE"`, `payload_stop` = `"STOP"` : valeurs par défaut HA
- `state_topic` : topic pour l'état (open/closed)
- `state_open` = `"open"`, `state_closed` = `"closed"` : valeurs par défaut HA
- `position_topic` + `set_position_topic` : ajoutés seulement si `has_position=True`
- `position_open` = 100, `position_closed` = 0 : convention standard (Jeedom et HA concordent)
- `device_class` : `"shutter"` (volet roulant) ou `"blind"` (BSO)
- `retain: True` sur le topic `config` pour que HA redécouvre après redémarrage

### Convention unique_id et topics MQTT

- `unique_id` : `jeedom2ha_eq_{jeedom_eq_id}` — **même format que les lumières**
- `object_id` : `jeedom2ha_{jeedom_eq_id}`
- `command_topic` : `jeedom2ha/{jeedom_eq_id}/set`
- `state_topic` : `jeedom2ha/{jeedom_eq_id}/state`
- `position_topic` : `jeedom2ha/{jeedom_eq_id}/position`
- `set_position_topic` : `jeedom2ha/{jeedom_eq_id}/position/set`
- `availability_topic` : `jeedom2ha/bridge/status` (global, configuré dans Story 1.3)

> **Important unique_id :** Un même eqLogic ne peut produire qu'UNE SEULE entité (light OU cover, jamais les deux). Les anti-affinités de chaque mapper le garantissent. Si un eqLogic a à la fois des FLAP_* et des LIGHT_*, les deux mappers le marqueront `ambiguous` (via anti-affinité croisée).

### Décision architecture — Single-component discovery (maintenu Story 2.3)

> Story 2.3 continue avec le single-component discovery (`homeassistant/cover/jeedom2ha_{id}/config`) car chaque eqLogic volet ne produit qu'une seule entité `cover`. La migration vers device discovery reste planifiée pour quand un eqLogic produira plusieurs entités de types différents.

### Inversion de sens (AC#3)

**Approche V1 :** Jeedom et HA utilisent la même convention par défaut : 0 = fermé, 100 = ouvert. Les valeurs de `FLAP_SLIDER` sont passées telles quelles à HA via `position_topic`.

Si un utilisateur Jeedom a configuré une inversion dans son plugin (ex: plugin Z-Wave), la valeur renvoyée par `FLAP_STATE`/`FLAP_SLIDER` est déjà inversée côté Jeedom. Nous la passons telle quelle — l'inversion est respectée.

Si l'inversion est au niveau HA (convention opposée), on peut ajuster `position_open` / `position_closed` dans le payload discovery. **Pour V1, on utilise les valeurs par défaut (0=closed, 100=open) et on documente que les corrections se font dans la config Jeedom.**

### HA UX — Entités Inertes (Dette Technique Epic 2)

> **Important :** Comme pour les lumières (Story 2.2), les topics `state_topic`, `command_topic` et `position_topic` ne sont pas encore alimentés dans l'Epic 2. Les volets apparaîtront "Disponibles" dans HA mais sans contrôle réel. Résolu en Epic 3.

### Garde-fou aiohttp — pré-initialisation des clés app

Les conteneurs `app['mappings']` et `app['publications']` sont déjà pré-initialisés dans `create_app()` (Story 2.2). Pas de nouvelle clé à ajouter — les covers sont stockés dans les mêmes dicts, avec `ha_entity_type="cover"` dans le MappingResult.

### Purge MQTT et RAM (hérité Story 2.2)

Le mécanisme d'unpublish des équipements disparus est déjà en place. La seule modification : passer `entity_type` à `unpublish_by_eq_id()` pour que le bon topic soit utilisé (`cover` ou `light`).

### Pièges à éviter

- **NE PAS** inventer une position si `FLAP_SLIDER` est absent — publier seulement les capacités réellement détectées (AC#1)
- **NE PAS** toucher à `mapping/light.py` — chaque mapper est indépendant
- **NE PAS** toucher au modèle `topology.py` — les contrats sont stables depuis Story 2.1
- **NE PAS** créer deux entités HA pour un même eqLogic volet (même si BSO + standard)
- **NE PAS** hardcoder les topics MQTT — les calculer depuis `jeedom_eq_id` avec le namespace `jeedom2ha/`
- **NE PAS** créer le module `sync/` dans cette story — la synchronisation d'état vient en Epic 3
- **NE PAS** implémenter la réception de commandes HA → Jeedom dans cette story — scope Story 3.2
- **NE PAS** confondre `publish()` MQTT (discovery config, retained) avec la publication d'état (state topic, non-retained)
- **NE PAS** ajouter de clés `request.app[...]` dynamiquement — les conteneurs existent déjà
- **NE PAS** extrapoler la politique `probable=True` aux stories suivantes — elle est bornée à Story 2.3
- **NE PAS** ajouter de tilt (inclinaison) en V1 — les données Jeedom ne fournissent pas cette information de manière fiable
- **NE PAS** refactorer le LightMapper ou le publisher de manière disproportionnée — modifications ciblées uniquement

### Intelligences des Stories précédentes à réutiliser

- `TopologySnapshot` et `assess_all()` dans `models/topology.py` — prêt à l'emploi
- `MqttBridge` dans `transport/mqtt_client.py` — expose `publish(topic, payload, retain)` via `_client.publish()`
- `_handle_action_sync` dans `transport/http_server.py` — point d'intégration pour l'ajout du CoverMapper
- `request.app['topology']`, `request.app['eligibility']`, `request.app['mappings']`, `request.app['publications']` — déjà pré-initialisés
- `LightMapper` : pattern de référence pour la structure du CoverMapper (mêmes interfaces, même politique)
- `DiscoveryPublisher._build_light_payload()` : pattern de référence pour `_build_cover_payload()`
- `_min_confidence()` et `_CONFIDENCE_ORDER` dans `mapping/light.py` : même logique à dupliquer
- Fixtures `_make_eq()` et `_cmd()` dans `tests/unit/test_light_mapper.py` — même pattern pour les tests cover
- Logger avec préfixes : `[MAPPING]` pour le mapping cover, `[DISCOVERY]` pour la publication MQTT
- Tests dans `tests/` (racine du repo), pas dans `resources/daemon/tests/` — déviation héritée de Story 1.1

### Déviation architecture documentée

Les tests sont dans `tests/` (racine du repo) et non dans `resources/daemon/tests/` comme le spécifie l'architecture. Continuer avec cette convention (déviation héritée de Story 1.1).

### Écarts Story 2.1 à respecter

| Champ spec | Champ réel | Raison |
|---|---|---|
| `jeedom_eq_id` | `id` sur `JeedomEqLogic` | Convention adoptée en 2.1 |
| `cmd_type` | `type` sur `JeedomCmd` | Shadow du builtin Python, accepté |
| `eq_type` | `eq_type_name` sur `JeedomEqLogic` | Plus explicite |

> **Attention :** utiliser `eq.id` et `cmd.id` (pas `jeedom_eq_id`) dans le code.

### Project Structure Notes

- Alignment avec la structure établie par Stories 2.1 et 2.2
- Nouveaux fichiers : `mapping/cover.py`, `tests/unit/test_cover_mapper.py`
- Fichiers modifiés : `models/mapping.py`, `discovery/publisher.py`, `transport/http_server.py`, `tests/unit/test_discovery_publisher.py`
- Aucun conflit avec la structure existante

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Mapping Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#File Module Log Structure]
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns Fallbacks]
- [Source: _bmad-output/planning-artifacts/architecture.md#MVP Guardrails]
- [Source: _bmad-output/implementation-artifacts/2-2-mapping-exposition-des-lumieres.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/2-2-mapping-exposition-des-lumieres.md#Durcissement du Mapping]
- [Source: home-assistant.io/integrations/cover.mqtt — Default Schema Configuration]
- [Source: doc.jeedom.com/en_US/core/4.3/types — Shutter Generic Types]

## Dev Agent Record

### Agent Model Used

Antigravity (Google DeepMind)

### Debug Log References

Aucun problème rencontré — implémentation linéaire sans blocage.

### Completion Notes List

- ✅ CoverMapper créé avec mapping capability-based en 5 phases (Open/Close, Stop, Position, BSO, Confidence globale)
- ✅ Anti-affinité croisée : LIGHT_* empêche un cover, FLAP_* empêche une lumière
- ✅ Publication policy bornée Story 2.3 : sure→publish, probable→publish, ambiguous→skip
- ✅ Publisher étendu : `publish_cover()`, `_build_cover_payload()` avec champs conditionnels (stop, position, BSO)
- ✅ `_build_topic()` refactoré pour accepter `entity_type` (backward compatible)
- ✅ `unpublish_by_eq_id()` accepte `entity_type` — purge sur le bon topic
- ✅ `_build_device_block()` extrait comme méthode commune (refactoring ciblé)
- ✅ Sync handler chaîne LightMapper → CoverMapper (premier non-None gagne)
- ✅ Compteurs séparés lights_*/covers_* dans mapping_summary
- ✅ 168 tests passent (30 nouveaux tests cover dont 1 ajouté post-review, 0 régressions)
- ✅ [Code Review Fix] MqttBridge.publish_message() API publique — élimine accès direct à _client (H2)
- ✅ [Code Review Fix] MappingResult.capabilities typé Union[LightCapabilities, CoverCapabilities] (M1)
- ✅ [Code Review Fix] Logs [MAPPING] enrichis avec reason_details pour les cas positifs (M2)
- ✅ [Code Review Fix] app["topology"] et app["eligibility"] pré-initialisés dans create_app() (M3)
- ✅ [Code Review Fix] Test explicite FLAP_UP seul → ambiguous ajouté (L1)
- ⏳ Task 5 (Smoke Test MQTT) nécessite une box Jeedom avec broker actif

### File List

- [NEW] resources/daemon/mapping/cover.py — CoverMapper
- [MODIFIED] resources/daemon/models/mapping.py — CoverCapabilities ajouté, MappingResult.capabilities typé Union[LightCapabilities, CoverCapabilities]
- [MODIFIED] resources/daemon/discovery/publisher.py — publish_cover(), _build_cover_payload(), _build_device_block(), _build_topic(entity_type), unpublish_by_eq_id(entity_type) ; utilise publish_message() API publique
- [MODIFIED] resources/daemon/transport/http_server.py — CoverMapper intégré dans sync, compteurs cover, unpublish entity-aware, pré-init topology/eligibility
- [MODIFIED] resources/daemon/transport/mqtt_client.py — publish_message() API publique ajoutée (code review fix H2)
- [NEW] tests/unit/test_cover_mapper.py — 21 tests unitaires CoverMapper (20 initiaux + 1 post-review)
- [MODIFIED] tests/unit/test_discovery_publisher.py — 9 tests cover publisher ajoutés, mocks migrés vers publish_message()

## Change Log

- **2026-03-14** — Implémentation Story 2.3 : CoverMapper capability-based avec 5 phases de détection, garde-fous anti faux-positifs, publisher cover, intégration sync handler, 30 tests unitaires. 168/168 tests passent.
- **2026-03-14** — Code Review fixes : API publish_message() sur MqttBridge (H2), typing Union sur capabilities (M1), logs reason_details enrichis (M2), pré-init topology/eligibility (M3), test FLAP_UP seul (L1).
