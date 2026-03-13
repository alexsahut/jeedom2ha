# Story 2.2: Mapping & Exposition des Lumières

Status: review

## Story

As a utilisateur Jeedom,
I want retrouver mes lumières (On/Off, Dimmer) dans HA avec un niveau de confiance explicite,
so that je puisse les piloter avec une configuration fiable.

## Acceptance Criteria

1. **Given** la topologie Jeedom est scrapée **When** le moteur de mapping traite un équipement d'éclairage **Then** la décision de mapping produit : un type cible, un niveau de confiance (Sûr / Probable / Ambigu) et une raison
2. **And** les entités "Sûres" sont publiées via MQTT Discovery
3. **And** les entités "Probables" ne sont publiées que si la politique d'exposition le permet, sinon elles restent diagnostiquées mais non publiées
4. **And** les entités "Ambigües" ne sont pas publiées par défaut ; les cas non sûrs sont expliqués dans le diagnostic

## Hardened Definition of Done (Retrospective Epic 1)

- [ ] **Validation Manuelle sur Box :** Story validée sur une vraie box Jeedom (pas seulement en mock/unit tests).
- [ ] **Smoke Test MQTT Discovery :** Après `/action/sync`, vérifier avec `mosquitto_sub -t 'homeassistant/#' -v` que les topics de config sont publiés avec `retain=true` et un payload JSON valide.
- [ ] **Contrôle de Pollution PHP :** Vérification qu'aucun `echo`, `warning` ou `notice` PHP ne vient polluer le retour JSON AJAX.
- [ ] **Contrat d'Interface :** Payloads MQTT Discovery JSON validés par le schéma HA attendu.
- [ ] **Logs de Diagnostic :** Logs `[MAPPING]` et `[DISCOVERY]` explicites incluant la raison et la confiance de chaque décision.

## Tasks / Subtasks

- [x] **Task 1 — Créer le Mapping Engine capability-based pour les lumières (`mapping/`)** (AC: #1)
  - [x] 1.1 Créer `resources/daemon/mapping/__init__.py` (package vide)
  - [x] 1.2 Créer `resources/daemon/mapping/light.py` avec la classe `LightMapper`
    - Méthode `map(eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]`
    - Retourne `None` si l'équipement ne contient aucune commande `LIGHT_*`
    - Retourne un `MappingResult` avec **capacités cumulées** détectées, confiance, raison
  - [x] 1.3 Créer `resources/daemon/models/mapping.py` avec les dataclasses :
    - `MappingResult(ha_entity_type: str, confidence: str, reason_code: str, jeedom_eq_id: int, ha_unique_id: str, ha_name: str, suggested_area: Optional[str], commands: Dict[str, JeedomCmd], capabilities: LightCapabilities, reason_details: Optional[Dict])`
    - `LightCapabilities(has_on_off: bool, has_brightness: bool, on_off_confidence: str, brightness_confidence: str)` — capacités cumulées
    - `PublicationDecision(should_publish: bool, reason: str, mapping_result: MappingResult)`
  - [x] 1.4 Implémenter le mapping **capability-based** (pas de lignes exclusives) :

    Le mapper détecte les capacités **indépendamment** puis les cumule en une seule entité `light` :

    **Phase 1 — Détection On/Off :**

    | Commandes trouvées | Résultat `has_on_off` | `on_off_confidence` |
    |---|---|---|
    | `LIGHT_STATE` (info) + `LIGHT_ON` + `LIGHT_OFF` | ✅ | `sure` |
    | `LIGHT_STATE` + `LIGHT_ON` (sans `LIGHT_OFF`) | ✅ | `probable` — manque `LIGHT_OFF` |
    | `LIGHT_STATE` + `LIGHT_OFF` (sans `LIGHT_ON`) | ✅ | `probable` — manque `LIGHT_ON` |
    | Aucun des 3 mais `LIGHT_SLIDER` présent | ✅ implicite | `sure` — le slider gère on/off via valeur 0 |

    **Phase 2 — Détection Brightness :**

    | Commandes trouvées | Résultat `has_brightness` | `brightness_confidence` |
    |---|---|---|
    | `LIGHT_BRIGHTNESS` (info/numeric) + `LIGHT_SLIDER` (action/slider) | ✅ | `sure` |
    | `LIGHT_SLIDER` sans `LIGHT_BRIGHTNESS` | ✅ | `probable` — slider présent mais pas d'info brightness dédiée |
    | `LIGHT_STATE` (info/numeric, sub_type=numeric) comme fallback brightness | ✅ | `probable` — utilise `LIGHT_STATE` comme source brightness |

    **Phase 3 — Confiance globale de l'entité :**

    ```
    confidence = worst(on_off_confidence, brightness_confidence) si les deux existent
    confidence = on_off_confidence si pas de brightness
    ```

    > **Note d'implémentation :** "worst" = `max()` sur l'ordre sémantique (`sure=0 < probable=1 < ambiguous=2`).
    > En Python : `max(on_off_order, brightness_order)` → on prend la **pire confiance**.
    > (Utiliser `min()` serait une régression : `min(sure, probable)` retournerait `sure`, ce qui est incorrect.)

    - Si au moins On/Off → entité `light` publiable (selon politique)
    - Si seul `LIGHT_SET_COLOR` / `LIGHT_COLOR` / `LIGHT_COLOR_TEMP` → `ambiguous` (V1 non supporté)
    - Si `LIGHT_STATE` orphelin (seul, sans action) → `ambiguous`

    > **Un seul `MappingResult` par eqLogic**, avec les deux flags `has_on_off` et `has_brightness` cumulés.

    **Exemple concret :** `LIGHT_STATE` + `LIGHT_ON` + `LIGHT_OFF` + `LIGHT_BRIGHTNESS` + `LIGHT_SLIDER`
    → **une seule** entité `light` avec `has_on_off=True` (sure) + `has_brightness=True` (sure) → confidence globale `sure`

  - [x] 1.5 Implémenter la politique d'exposition **bornée** :
    - `sure` → toujours publier
    - `probable` → publier **uniquement pour les cas explicitement listés dans Task 1.4** (on/off partiel, brightness sans info dédiée)
    - `ambiguous` → **jamais** publier, raison dans le diagnostic
    - `unknown` / `ignore` → **jamais** publier

    > La politique `probable → publier` est bornée aux cas de Story 2.2 uniquement. Elle ne constitue pas une règle générale pour les stories suivantes.

- [x] **Task 2 — Créer le moteur de Discovery MQTT — device discovery first (`discovery/`)** (AC: #2, #3)
  - [x] 2.1 Créer `resources/daemon/discovery/__init__.py` (package vide)
  - [x] 2.2 Créer `resources/daemon/discovery/publisher.py` avec la classe `DiscoveryPublisher`
    - `__init__(self, mqtt_bridge: MqttBridge, topic_prefix: str = "homeassistant")`
    - `async publish_light(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool`
    - `async unpublish(self, ha_unique_id: str) -> bool`
  - [x] 2.3 Implémenter la génération du payload MQTT Discovery — **device discovery prioritaire** :

    > **Décision architecture :** L'architecture impose le device discovery comme mode principal (`homeassistant/device/...`). Story 2.2 utilise **single-component discovery** (`homeassistant/light/...`) comme exception documentée. Justification : en Story 2.2, chaque eqLogic Jeedom ne produit qu'une seule entité `light`. Le device discovery multi-composant sera adopté en Story 2.3+ quand un même eqLogic pourra produire plusieurs entités (ex: volet avec position + état binaire). Cette décision est réversible sans impact utilisateur grâce aux `unique_id` stables.

    **Topic de discovery :**
    ```
    homeassistant/light/jeedom2ha_{jeedom_eq_id}/config
    ```

    **Payload JSON — Light On/Off uniquement :**
    ```json
    {
      "name": "{eq_name}",
      "unique_id": "jeedom2ha_eq_{jeedom_eq_id}",
      "object_id": "jeedom2ha_{jeedom_eq_id}",
      "state_topic": "jeedom2ha/{jeedom_eq_id}/state",
      "command_topic": "jeedom2ha/{jeedom_eq_id}/set",
      "payload_on": "ON",
      "payload_off": "OFF",
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

    **Payload JSON — Light On/Off + Brightness (capacités cumulées) :**
    ```json
    {
      "...": "mêmes champs que On/Off",
      "brightness_state_topic": "jeedom2ha/{jeedom_eq_id}/brightness",
      "brightness_command_topic": "jeedom2ha/{jeedom_eq_id}/brightness/set",
      "brightness_scale": 100,
      "supported_color_modes": ["brightness"],
      "color_mode": true
    }
    ```

    > Le payload est **un seul JSON** qui inclut les champs brightness si `has_brightness=True`. Pas de publication séparée pour On/Off et brightness.

  - [x] 2.4 Le payload MUST être publié avec `retain=True` sur le topic de config
  - [x] 2.5 L'unpublish = publier un payload vide `""` avec `retain=True` sur le même topic

- [x] **Task 3 — Intégrer le mapping + discovery dans le handler sync** (AC: #2, #3, #4)
  - [x] 3.1 Pré-initialiser les conteneurs dans `create_app()` de `http_server.py` :
    ```python
    app["mappings"] = {}      # Dict[int, MappingResult]
    app["publications"] = {}  # Dict[int, PublicationDecision]
    ```
    > **NE PAS** ajouter de clés `request.app[...]` dynamiquement après le démarrage — garde-fou aiohttp DeprecationWarning hérité de Epic 1.
  - [x] 3.2 Modifier `_handle_action_sync` :
    - Après l'évaluation d'éligibilité, appliquer le `LightMapper` sur chaque eqLogic éligible
    - Stocker les `MappingResult` dans `request.app['mappings']` (pré-initialisé)
    - Stocker les `PublicationDecision` dans `request.app['publications']` (pré-initialisé)
    - Pour chaque mapping avec `should_publish=True`, appeler `DiscoveryPublisher.publish_light()`
    - Enrichir le résumé avec les compteurs de mapping + publication
  - [x] 3.3 Conserver les décisions **détaillées** en RAM (pas seulement les compteurs) :
    ```python
    # request.app['publications'] contient pour chaque eqLogic:
    # {
    #   42: PublicationDecision(
    #     should_publish=True,
    #     reason="sure",
    #     mapping_result=MappingResult(
    #       confidence="sure",
    #       reason_code="light_on_off_brightness",
    #       capabilities=LightCapabilities(has_on_off=True, has_brightness=True, ...),
    #       ...
    #     )
    #   )
    # }
    ```
    > **Objectif :** préparer l'Epic 4 (diagnostic) qui aura besoin de la confiance, raison, et décision de publication par équipement — pas seulement des compteurs globaux.
  - [x] 3.4 Enrichir la réponse du sync avec un résumé (les détails restent en RAM) :
    ```json
    {
      "...": "champs existants",
      "payload": {
        "...": "champs existants",
        "mapping_summary": {
          "lights_sure": 5,
          "lights_probable": 2,
          "lights_ambiguous": 1,
          "lights_published": 7,
          "lights_skipped": 1
        }
      }
    }
    ```

- [x] **Task 4 — Tests unitaires Python** (AC: tous)
  - [x] 4.1 Créer `tests/unit/test_light_mapper.py` :
    - EqLogic avec `LIGHT_STATE` + `LIGHT_ON` + `LIGHT_OFF` → On/Off `sure`, `has_brightness=False`
    - EqLogic avec `LIGHT_STATE` + `LIGHT_ON` (sans `LIGHT_OFF`) → On/Off `probable`
    - EqLogic avec `LIGHT_BRIGHTNESS` + `LIGHT_SLIDER` → brightness `sure`
    - EqLogic avec `LIGHT_STATE` + `LIGHT_SLIDER` (sans `LIGHT_BRIGHTNESS`) → brightness `probable`
    - **Capacités cumulées :** `LIGHT_STATE` + `LIGHT_ON` + `LIGHT_OFF` + `LIGHT_BRIGHTNESS` + `LIGHT_SLIDER` → **une seule** entité avec `has_on_off=True` + `has_brightness=True`, confidence `sure`
    - **Capacités cumulées partielles :** `LIGHT_STATE` + `LIGHT_ON` + `LIGHT_SLIDER` → `has_on_off=True` (probable) + `has_brightness=True` (probable), confidence globale `probable`
    - EqLogic avec `LIGHT_SET_COLOR` seul → confidence `ambiguous` (V1 non supporté)
    - EqLogic avec `LIGHT_STATE` seul → confidence `ambiguous`
    - EqLogic sans aucun `LIGHT_*` → retourne `None` (pas une lumière)
    - EqLogic avec commandes mixtes (LIGHT + TEMPERATURE) → seules les commandes LIGHT sont retenues
    - Vérifier que `ha_unique_id` est généré au format `jeedom2ha_eq_{id}`
    - Vérifier que `suggested_area` est extrait du snapshot
  - [x] 4.2 Créer `tests/unit/test_discovery_publisher.py` :
    - Payload On/Off contient tous les champs requis (state_topic, command_topic, payload_on/off, device, origin)
    - Payload On/Off+Brightness contient `brightness_state_topic`, `brightness_command_topic`, `brightness_scale=100`, `supported_color_modes=["brightness"]`, `color_mode=true`
    - Topic = `homeassistant/light/jeedom2ha_{id}/config`
    - Retain = True sur publish
    - Unpublish envoie payload vide avec retain=True
    - `device.identifiers` contient `jeedom2ha_{id}`
    - `origin.name` = `jeedom2ha`
    - `availability_topic` = `jeedom2ha/bridge/status`
    - `suggested_area` absent du `device` si l'objet Jeedom est None

- [ ] **Task 5 — Smoke Test MQTT Discovery** (DoD)
  - [ ] 5.1 Sur une box Jeedom avec broker MQTT actif :
    1. Lancer le daemon
    2. Déclencher `/action/sync` via AJAX ou curl
    3. Vérifier avec `mosquitto_sub -t 'homeassistant/light/#' -v --retained-only` que les topics sont publiés
    4. Vérifier que le payload JSON est valide et contient les champs requis
    5. Vérifier que `retain=true` est effectif (le message persiste après reconnexion du subscriber)

## Dev Notes

### Architecture & Patterns obligatoires

**Flux de mapping + publication (extension de Story 2.1) :**

```
Topologie normalisée (RAM)
  → LightMapper.map(eqLogic) → MappingResult (type, capabilities cumulées, confiance, raison)
  → PublicationDecision (should_publish basé sur confiance + politique bornée)
  → DiscoveryPublisher.publish_light(mapping, snapshot) → MQTT publish retained
  → Décisions détaillées stockées en RAM (app['publications']) pour Epic 4
```

**Organisation des modules Python (architecture.md §3) :**

```
resources/daemon/
  mapping/
    __init__.py           # CRÉER: package
    light.py              # CRÉER: LightMapper
  discovery/
    __init__.py           # CRÉER: package
    publisher.py          # CRÉER: DiscoveryPublisher
  models/
    __init__.py            # EXISTE: package
    topology.py            # EXISTE: ne pas modifier
    mapping.py             # CRÉER: MappingResult, LightCapabilities, PublicationDecision
  transport/
    http_server.py         # MODIFIER: enrichir create_app() + _handle_action_sync
```

**Jeedom generic_type pour les lumières :**

| Generic Type | Type cmd | Sous-type | Rôle |
|---|---|---|---|
| `LIGHT_STATE` | info | binary ou numeric | État on/off ou niveau luminosité |
| `LIGHT_ON` | action | other | Allumer |
| `LIGHT_OFF` | action | other | Éteindre |
| `LIGHT_BRIGHTNESS` | info | numeric | Niveau de luminosité actuel (0-100 ou 0-255) |
| `LIGHT_SLIDER` | action | slider | Régler la luminosité |
| `LIGHT_SET_COLOR` | action | color | Régler la couleur (V1: non supporté) |
| `LIGHT_COLOR` | info | string | Couleur courante (V1: non supporté) |
| `LIGHT_COLOR_TEMP` | info | numeric | Température de couleur (V1: non supporté) |

**HA MQTT Discovery — default schema pour `light` :**

Le plugin utilise le **default schema** (pas JSON schema ni template schema). Champs critiques :
- `state_topic` + `command_topic` : obligatoires pour On/Off
- `payload_on` = `"ON"`, `payload_off` = `"OFF"` : valeurs par défaut HA
- `brightness_state_topic` + `brightness_command_topic` : ajoutés seulement si `has_brightness=True`
- `brightness_scale` : 100 (convention Jeedom) — HA par défaut attend 0-255, cette valeur adapte l'échelle
- `supported_color_modes` : `["brightness"]` quand `has_brightness=True`, sinon omis (On/Off basique)
- `color_mode: true` : obligatoire quand `supported_color_modes` est présent
- `retain: True` sur le topic `config` pour que HA redécouvre après redémarrage

**Convention unique_id et topics MQTT (architecture.md §1) :**
- `unique_id` : `jeedom2ha_eq_{jeedom_eq_id}` — stable, basé sur l'ID Jeedom, jamais sur le nom
- `object_id` : `jeedom2ha_{jeedom_eq_id}` — dérivé lisible, non autoritatif
- `state_topic` : `jeedom2ha/{jeedom_eq_id}/state`
- `command_topic` : `jeedom2ha/{jeedom_eq_id}/set`
- `brightness_state_topic` : `jeedom2ha/{jeedom_eq_id}/brightness`
- `brightness_command_topic` : `jeedom2ha/{jeedom_eq_id}/brightness/set`
- `availability_topic` : `jeedom2ha/bridge/status` (global, configuré dans Story 1.3)

> Le namespace `jeedom2ha/` est isolé (NFR16). Pas de collision avec d'autres plugins ou intégrations.

**Politique d'exposition V1 — bornée à Story 2.2 :**

```python
# La politique "probable" est bornée aux cas explicitement listés dans cette story.
# Elle ne constitue PAS une règle générale pour les stories suivantes (2.3, 2.4, 2.5).
LIGHT_PUBLICATION_POLICY = {
    "sure": True,        # Toujours publier
    "probable": True,    # Publier UNIQUEMENT les cas light listés en Task 1.4
    "ambiguous": False,  # Jamais publier, diagnostic uniquement
    "unknown": False,    # Jamais publier
    "ignore": False,     # Jamais publier
}
```

### Décision architecture — Single-component vs Device Discovery

> **Exception documentée pour Story 2.2 :** utilisation du single-component discovery (`homeassistant/light/jeedom2ha_{id}/config`) car chaque eqLogic ne produit qu'une seule entité `light`.
>
> **Migration vers device discovery :** sera effectuée en Story 2.3+ quand un même eqLogic peut produire plusieurs entités HA. Les `unique_id` stables rendent cette migration transparente pour l'utilisateur.

### HA UX — Entités Inertes (Dette Technique Epic 2)

> **Important :** Le payload MQTT Discovery publie un `state_topic` et `command_topic`. Ces topics **ne sont pas encore implémentés ni alimentés** dans l'Epic 2.
> Conséquence UX : Les lumières apparaîtront "Disponibles" dans Home Assistant, mais la vérification de leur état et l'envoi de commandes (On/Off/Dimmer) n'auront aucun effet.
> **Cette limitation est assumée et documentée comme dette technique.** Elle sera résolue lors de l'Epic 3 (synchronisation bidirectionnelle d'état).

### Garde-fou aiohttp — pré-initialisation des clés app

Les conteneurs `app['mappings']` et `app['publications']` doivent être pré-initialisés dans `create_app()` (pas ajoutés dynamiquement dans les handlers). Ceci évite le `DeprecationWarning` aiohttp rencontré en Epic 1.

### Purge MQTT et RAM (Issue Review Epic 2.2)

Lors de chaque appel global `/action/sync`, le plugin maintient une liste des équipements publiés et purge (RAM + unpublish MQTT) tous les équipements Jeedom qui étaient précédemment éligibles/lus mais qui ne remontent plus dans la nouvelle payload d'éligibilité (ou dont le type générique ne match plus). Cela prévient les "Entités fantômes" dans HA.

### Durcissement du Mapping (Faux Positifs)

Suite au Smoke Test, des équipements non-lumière (chauffage, chauffe-eau, module piscine, prise) étaient exposés à tort car historiquement typés `LIGHT_ON`/`LIGHT_OFF` dans Jeedom par certains plugins relais. Pour y remédier, des garde-fous stricts ont été ajoutés dans `LightMapper` :
1. **Exclusion explicite :** Si `eq.generic_type` est fourni et différent de `light` (ex: `HEATER`, `FLAP`), le mapping est purement annulé.
2. **Anti-affinité (Conflits) :** Si l'équipement possède des commandes de domaines antagonistes (`HEATING_*`, `SMOKE`, `ENERGY_POWER`, `FLAP_*`, etc.), le mapping devient `ambiguous` avec motif `conflicting_generic_types`.
3. **Heuristiques de Noms :** Si le nom de l'équipement contient des mots-clés d'autres domaines (chauffage, prise, piscine, fumée, etc.), le mapping devient `ambiguous` avec motif `name_heuristic_rejection`.

### Pièges à éviter

- **NE PAS** traiter le mapping comme des lignes exclusives — les capacités sont **cumulées** (on/off + brightness forment une seule entité)
- **NE PAS** créer deux entités HA pour un même eqLogic qui a à la fois on/off et brightness
- **NE PAS** implémenter les couleurs (`LIGHT_SET_COLOR`, `LIGHT_COLOR`, `LIGHT_COLOR_TEMP`) en V1 — marquer comme `ambiguous`
- **NE PAS** publier de `brightness_state_topic` si `has_brightness=False` — HA interpréterait un topic inexistant comme broken
- **NE PAS** inventer une valeur de brightness si `LIGHT_BRIGHTNESS` (info) est absente — utiliser `LIGHT_STATE` en fallback seulement si son `sub_type == "numeric"`
- **NE PAS** hardcoder les topics MQTT — les calculer depuis `jeedom_eq_id` avec le namespace `jeedom2ha/`
- **NE PAS** créer le module `sync/` dans cette story — la synchronisation d'état vient en Epic 3
- **NE PAS** implémenter la réception de commandes HA → Jeedom dans cette story — scope Story 3.2
- **NE PAS** confondre `publish()` MQTT (discovery config, retained) avec la publication d'état (state topic, non-retained) — Story 2.2 ne publie **que le discovery config**
- **NE PAS** toucher au modèle `topology.py` — les contrats sont stables depuis Story 2.1
- **NE PAS** utiliser `MqttBridge.publish()` directement dans le mapper — le mapper produit des données, le publisher publie via MQTT
- **NE PAS** confondre `brightness_scale: 100` (Jeedom) avec l'échelle par défaut HA (0-255) — le champ `brightness_scale` dans le payload discovery adapte l'échelle
- **NE PAS** ajouter de clés `request.app[...]` dynamiquement — pré-initialiser dans `create_app()`
- **NE PAS** extrapoler la politique `probable=True` aux stories suivantes — elle est bornée à Story 2.2

### Intelligences des Stories 1.x et 2.1 à réutiliser

- `TopologySnapshot` et `assess_all()` dans `models/topology.py` — prêt à l'emploi, ne pas recréer
- `MqttBridge` dans `transport/mqtt_client.py` — expose une méthode `publish(topic, payload, retain)` pour MQTT
- `_handle_action_sync` dans `transport/http_server.py` — point d'intégration pour le mapping + publication
- `request.app['topology']` et `request.app['eligibility']` — snapshot et éligibilité stockés en RAM
- Fixtures `jeedom_eq_factory` et `jeedom_cmd_factory` dans `tests/conftest.py` — les étendre pour les cas lumière
- Logger avec préfixes : `[MAPPING]` pour cette story, `[DISCOVERY]` pour la publication MQTT
- Tests dans `tests/` (racine du repo), pas dans `resources/daemon/tests/` — déviation documentée Story 1.1

### Déviation architecture documentée

Les tests sont dans `tests/` (racine du repo) et non dans `resources/daemon/tests/` comme le spécifie l'architecture. Continuer avec cette convention (déviation héritée de Story 1.1).

### Écarts Story 2.1 à respecter

| Champ spec | Champ réel | Raison |
|---|---|---|
| `jeedom_eq_id` | `id` sur `JeedomEqLogic` | Convention adoptée en 2.1 — pas d'ambiguïté |
| `cmd_type` | `type` sur `JeedomCmd` | Shadow du builtin Python, accepté |
| `eq_type` | `eq_type_name` sur `JeedomEqLogic` | Plus explicite, cohérent Jeedom API |
| `reason: str` | `reason_code: str` sur `EligibilityResult` | Codes techniques i18n-ready |

> **Attention :** utiliser `eq.id` et `cmd.id` (pas `jeedom_eq_id`) dans le code.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Mapping Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#File Module Log Structure]
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns Fallbacks]
- [Source: _bmad-output/planning-artifacts/architecture.md#MVP Guardrails]
- [Source: _bmad-output/project-context.md#MQTT Discovery Home Assistant]
- [Source: _bmad-output/project-context.md#Règles Critiques — Anti-Patterns]
- [Source: _bmad-output/project-context.md#MVP Scope Guardrails]
- [Source: _bmad-output/implementation-artifacts/2-1-topology-scraper-contexte-spatial.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/2-1-topology-scraper-contexte-spatial.md#Écarts restants vs spec]
- [Source: home-assistant.io/integrations/light.mqtt — Default Schema Configuration]
- [Source: Jeedom docs — Generic Types LIGHT_*]

## Change Log

- 2026-03-13: Implémentation complète Tasks 1-4 — mapping engine capability-based, discovery publisher MQTT, intégration sync handler, 34 tests unitaires ajoutés (136 total pass).
- 2026-03-13: Refinement post Code Review (Fix Doublons de generic_type: passe l'équipement en Ambigu, Fix RAM leak & MQTT Ghost entities: `unpublish` des disparus de l'éligibilité, unpublish by id plus robuste, documentation dette HA UX inerte).
- 2026-03-13: Fix bug `_min_confidence` — utilisait `min()` (meilleure confiance) au lieu de `max()` (pire confiance) pour le calcul semantique.
- 2026-03-13: Smoke Test terrain partiel — Validation de la publication MQTT, mais détection de faux-positifs (chauffage, modules piscines exposés en `light`). Durcissement du `LightMapper` via 3 garde-fous (type explicite, anti-affinité de commandes, heuristique de nom). Faux-positifs corrigés et couverts par tests.

## Dev Agent Record

### Agent Model Used

Antigravity (Claude 3.7)

### Debug Log References

- Bug `_min_confidence`: `min()` Python retournait `sure` (ordre 0) au lieu de `probable` (ordre 1) pour `min(sure, probable)`. La sémantique business est "pire confiance" → corrigé en `max()` sur l'ordre.
- Review Fix (Commandes doublons): Si deux commandes possèdent le même `generic_type`, l'écrasement silencieux initial (dict insert) empêchait le mapper de réagir, potentiellement faussant le mapping. On remonte à présent "ambiguous" (avec le code de raison \`duplicate_generic_types\`).
- Review Fix (RAM leak / Zombies HA): En synchronisant `http_server` avec les décisions de publication existantes, un unpublish() est envoyé explicitement pour les clés qui disparaissent d'une invocation de \`sync()\` à l'autre.

### Completion Notes List

- ✅ Task 1: LightMapper capability-based avec détection On/Off (3 patterns), Brightness (3 patterns), confiance globale = worst(per-capability) via `max()` sur l'ordre sémantique, politique d'exposition bornée.
- ✅ Task 2: DiscoveryPublisher avec single-component discovery, payloads On/Off et On/Off+Brightness, retain=True, unpublish payload vide.
- ✅ Task 3: Intégration dans `_handle_action_sync` — pré-initialisation app keys, mapping loop, publication MQTT, décisions détaillées en RAM, mapping_summary dans la réponse.
- ✅ Task 4: 34 tests unitaires — 20 pour LightMapper (12 cas de mapping + publication decisions), 14 pour DiscoveryPublisher (payload structure, topics, retain, device, origin, availability).
- ⏳ Task 5: Smoke test MQTT Discovery — requiert une box Jeedom avec broker MQTT actif (validation manuelle).

### File List

- [NEW] resources/daemon/mapping/__init__.py
- [NEW] resources/daemon/mapping/light.py
- [NEW] resources/daemon/discovery/__init__.py
- [NEW] resources/daemon/discovery/publisher.py
- [NEW] resources/daemon/models/mapping.py
- [MOD] resources/daemon/transport/http_server.py
- [NEW] tests/unit/test_light_mapper.py
- [NEW] tests/unit/test_discovery_publisher.py
