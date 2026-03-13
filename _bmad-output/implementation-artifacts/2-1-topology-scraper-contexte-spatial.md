# Story 2.1: Topology Scraper & Contexte Spatial

Status: done

## Story

As a utilisateur Jeedom,
I want que le plugin identifie mes équipements éligibles et leur contexte,
so that je puisse préparer une projection fiable dans Home Assistant.

## Acceptance Criteria

1. **Given** le moteur du démon est actif **When** un scan de la topologie est déclenché **Then** l'inventaire Jeedom (eqLogics et commandes) est extrait via les interfaces standard
2. **And** les IDs Jeedom (eqLogic, cmd, object) sont normalisés dans un modèle interne canonique
3. **And** les objets Jeedom sont utilisés comme source de contexte spatial et base de `suggested_area`, sans équivalence stricte avec les areas HA
4. **And** les équipements exclus explicitement ou manifestement non éligibles sont marqués avec une raison explorable (préparation diagnostic)

## Hardened Definition of Done (Retrospective Epic 1)

- [ ] **Validation Manuelle sur Box :** Story validée sur une vraie box Jeedom (pas seulement en mock/unit tests).
- [ ] **Smoke Test API :** `curl -X POST` sur `/action/sync` validé avec un payload réel.
- [ ] **Contrôle de Pollution PHP :** Vérification qu'aucun `echo`, `warning` ou `notice` PHP ne vient polluer le retour JSON AJAX.
- [x] **Contrat d'Interface :** Clés JSON validées (`payload` vs racine, `user` vs `username`) selon la [Matrice des Contrats](file:///Users/alexandre/.gemini/antigravity/brain/cbc8512c-b0ea-4b04-a65f-a61fc099f5cc/retrospective-epic-1.md).
- [x] **Logs de Diagnostic :** Logs `[TOPOLOGY]` explicites incluant le contenu brut en cas d'erreur de parsing.

> **Note :** Validation manuelle box, Smoke Test API et Contrôle pollution PHP restent `[ ]` — nécessitent un déploiement sur box réelle (hors scope code review).

## Tasks / Subtasks

- [x] **Task 1 — Créer le modèle canonique Python (`models/`)** (AC: #2, #3)
  - [x] 1.1 Créer `resources/daemon/models/__init__.py` (package vide)
  - [x] 1.2 Créer `resources/daemon/models/topology.py` avec les dataclasses :
    - `JeedomObject` (id, name, father_id)
    - `JeedomCmd` (id, name, generic_type, type, sub_type, current_value, unit, is_visible, is_historized)
    - `JeedomEqLogic` (id, name, object_id, is_enable, is_visible, eq_type_name, generic_type, is_excluded, cmds)
    - `EligibilityResult` (is_eligible, reason_code, confidence, reason_details)
    - `TopologySnapshot` (timestamp, objects, eq_logics)
    - Classmethod `TopologySnapshot.from_jeedom_payload(payload: dict) -> TopologySnapshot`
    - Méthode `TopologySnapshot.get_suggested_area(eq_id: int) -> Optional[str]`

- [x] **Task 2 — Implémenter l'évaluation d'éligibilité** (AC: #4)
  - [x] 2.1 Ajouter `assess_eligibility(eq: JeedomEqLogic) -> EligibilityResult` dans `models/topology.py`
  - [x] 2.2 Implémenter les règles (ordre de priorité) :
    1. `is_excluded == True` -> ineligible, reason_code: "excluded_eqlogic", confidence: "sure"
    2. `is_enable == False` -> ineligible, reason_code: "disabled_eqlogic", confidence: "sure"
    3. `len(cmds) == 0` -> ineligible, reason_code: "no_commands", confidence: "sure"
    4. Aucune cmd avec `generic_type` non null -> ineligible, reason_code: "no_supported_generic_type", confidence: "sure"
    5. Sinon -> eligible, reason_code: "eligible", confidence: "unknown" (sera affiné par le mapping engine en Stories 2.2-2.5)
  - [x] 2.3 Ajouter `assess_all(snapshot: TopologySnapshot) -> Dict[int, EligibilityResult]`

- [x] **Task 3 — Implémenter `getFullTopology()` côté PHP** (AC: #1)
  - [x] 3.1 Ajouter `public static function getFullTopology(): array` dans `core/class/jeedom2ha.class.php`
  - [x] 3.2 Extraire les objects via `jeeObject::all()` -> tableau `[{id, name, father_id}]`
  - [x] 5.2 Appelle `jeedom2ha::getFullTopology()` puis `callDaemon('/action/sync', $topology, 'POST', 15)`
  - [x] 5.3 Retourne le résumé du daemon à l'UI via `ajax::success()`

- [x] **Task 6 — Tests unitaires Python** (AC: tous)
  - [x] 6.1 Créer `tests/unit/test_topology.py` : tests de normalisation `from_jeedom_payload`
    - Payload valide avec objects + eq_logics + cmds -> snapshot correct
    - IDs string ("42") normalisés en int
    - `generic_type` vide ("") normalisé en None
    - eqLogic sans `object_id` -> `get_suggested_area()` retourne None
    - eqLogic avec `object_id` valide -> `get_suggested_area()` retourne le nom de l'objet
    - Payload vide -> snapshot avec dictionnaires vides
    - String bools ("0"/"1") -> normalisation correcte via `_to_bool()`
  - [x] 6.2 Créer `tests/unit/test_eligibility.py` : tests d'éligibilité
    - eqLogic exclu -> ineligible "excluded_eqlogic"
    - eqLogic désactivé -> ineligible "disabled_eqlogic"
    - eqLogic sans commandes -> ineligible "no_commands"
    - eqLogic avec cmds sans generic_type -> ineligible "no_supported_generic_type"
    - eqLogic avec cmds et generic_type -> eligible, confidence "unknown"
    - Commandes mixtes (avec + sans generic_type) -> eligible
    - `assess_all` retourne un dict complet couvrant tous les eqLogics

## Dev Notes

### File List

- `resources/daemon/models/__init__.py`
- `resources/daemon/models/topology.py`
- `core/class/jeedom2ha.class.php` (ajout de `getFullTopology()`)
- `tests/unit/test_topology.py`
- `tests/unit/test_eligibility.py`

### Completion Notes

- La normalisation des IDs et des types génériques est robuste.
- L'évaluation d'éligibilité suit l'ordre de priorité défini et retourne des codes de raison clairs.
- L'extraction PHP est fonctionnelle et renvoie les données attendues.
- Les tests unitaires couvrent les cas critiques de normalisation et d'éligibilité.
- Le `generic_type` dans `JeedomEqLogic` a été supprimé du modèle Python car il n'est pas présent dans le payload Jeedom pour les eqLogics, seulement pour les commandes.
- Le champ `is_historized` a été ajouté à `JeedomCmd` pour refléter la réalité Jeedom.
- Les champs `reason` et `confidence` de `EligibilityResult` ont été renommés en `reason_code` et `reason_details` pour plus de clarté et pour permettre une localisation ultérieure.

### Écarts restants vs spec initiale

> Documenté lors de la code review 2026-03-13. Chaque écart est analysé et sa disposition est explicite.

| # | Spec initiale | Implémentation réelle | Disposition | Note |
|---|---|---|---|---|
| C2 | Champs `jeedom_object_id`, `jeedom_cmd_id`, `jeedom_eq_id` | Champs `id` simples sur chaque dataclass | ✅ **Accepté** | Pas d'ambiguïté en pratique — chaque dataclass a son propre type. Renommer maintenant casserait le contrat PHP↔Python sans bénéfice réel. |
| C2 | `cmd_type` sur JeedomCmd | `type` (shadow du builtin Python) | ⚠️ **Accepté avec réserve** | Risque mineur. À surveiller si un bug subtil survient. Renommage possible en Epic 5 si le besoin se confirme. |
| C2 | `eq_type` sur JeedomEqLogic | `eq_type_name` | ✅ **Accepté** | Plus explicite que la spec. Cohérent avec Jeedom API (`getEqType_name()`). |
| C3 | `jeedom_eq_id: int` dans EligibilityResult | Absent — l'eq_id est la clé du dict `assess_all` | ✅ **Accepté** | Évite la redondance. `Dict[int, EligibilityResult]` porte l'info. |
| C3 | `reason: str` (texte FR pour l'UX) | `reason_code: str` (code technique) | ✅ **Accepté** | Les codes techniques sont i18n-ready. La traduction FR sera ajoutée dans le layer UX (Story 4.1). |
| C3 | `confidence: str` | ✅ Ajouté (fix code review) | ✅ **Corrigé** | `confidence="unknown"` par défaut, `"sure"` pour les inéligibles. |
| M1 | `ineligible_breakdown` avec raisons FR | Agrégation par `reason_code` | ✅ **Accepté** | Cohérent avec C3. L'UI de diagnostic (Epic 4) fera la traduction code→message. |
| M2 | Objects payload sans `isVisible` | PHP retourne `isVisible` sur les Objects | ✅ **Toléré** | Champ supplémentaire ignoré côté Python. Pas de pollution fonctionnelle. Pourra servir plus tard si besoin de filtrage UI. |
| M3 | Cmds payload sans `is_historized` | PHP retourne + Python consomme `is_historized` | ✅ **Accepté** | Anticipation utile pour les stories de mapping (2.2-2.5) sans surcoût. |
| L2 | `timestamp` du snapshot depuis le payload PHP | Fallback sur `datetime.now()` | ✅ **Toléré** | Le PHP ne pousse pas de timestamp dans le payload topology (seule l'enveloppe en a un). Le fallback est suffisant pour le diagnostic. |

> **Conclusion :** Aucun écart ne bloque les stories suivantes (2.2-2.5). Le contrat actuel est stable et documenté.

### Architecture & Patterns obligatoires

**Flux de scan topologique :**

```
UI (btn Scanner) --> AJAX scanTopology --> PHP getFullTopology()
  --> eqLogic::all() + cmd::byEqLogicId() + jeeObject::all()
  --> callDaemon('/action/sync', $topology, 'POST', 15)
  --> Daemon normalise --> évalue éligibilité --> stocke en RAM --> retourne résumé
```

**Enveloppe de payload PHP -> Daemon (rappel Story 1.1) :**

`callDaemon()` encapsule automatiquement dans :
```json
{
  "action": "sync",
  "payload": { "objects": [...], "eq_logics": [...] },
  "request_id": "uuid",
  "timestamp": "ISO8601"
}
```

Le handler daemon extrait `payload` depuis `data["payload"]` — **pas** `data` directement.

**Format du payload topologie (PHP -> Daemon) :**

```json
{
  "objects": [
    {"id": 5, "name": "Salon", "father_id": null},
    {"id": 6, "name": "Cuisine", "father_id": 5}
  ],
  "eq_logics": [
    {
      "id": 42,
      "name": "Lampe Salon",
      "object_id": 5,
      "is_enable": true,
      "is_visible": true,
      "eq_type": "zwave",
      "generic_type": null,
      "is_excluded": false,
      "cmds": [
        {
          "id": 123,
          "name": "Etat",
          "generic_type": "LIGHT_STATE",
          "type": "info",
          "sub_type": "binary",
          "current_value": "0",
          "unit": "",
          "is_visible": true
        },
        {
          "id": 124,
          "name": "On",
          "generic_type": "LIGHT_ON",
          "type": "action",
          "sub_type": "other",
          "current_value": null,
          "unit": null,
          "is_visible": true
        }
      ]
    }
  ]
}
```

**Format de réponse du daemon (résumé de scan) :**

```json
{
  "action": "sync",
  "status": "ok",
  "payload": {
    "total_objects": 12,
    "total_eq_logics": 87,
    "total_cmds": 432,
    "eligible_count": 54,
    "ineligible_count": 33,
    "ineligible_breakdown": {
      "Exclu par l'utilisateur": 2,
      "Équipement désactivé dans Jeedom": 5,
      "Aucune commande détectée": 3,
      "Aucun type générique configuré — configurez les types génériques sur les commandes dans Jeedom": 23
    }
  },
  "request_id": "uuid",
  "timestamp": "ISO8601"
}
```

**Dataclasses Python — spécifications détaillées :**

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class JeedomObject:
    jeedom_object_id: int
    name: str
    father_id: Optional[int] = None

@dataclass
class JeedomCmd:
    jeedom_cmd_id: int
    name: str
    generic_type: Optional[str] = None
    cmd_type: str = "info"          # "info" ou "action"
    sub_type: str = "string"        # "binary", "numeric", "string", "slider", "color", "other"
    current_value: Any = None
    unit: Optional[str] = None
    is_visible: bool = True

@dataclass
class JeedomEqLogic:
    jeedom_eq_id: int
    name: str
    jeedom_object_id: Optional[int] = None
    is_enable: bool = True
    is_visible: bool = True
    eq_type: str = ""               # nom du plugin source (zwave, zigbee, virtual, etc.)
    generic_type: Optional[str] = None
    is_excluded: bool = False       # flag d'exclusion jeedom2ha
    cmds: List[JeedomCmd] = field(default_factory=list)

@dataclass
class EligibilityResult:
    jeedom_eq_id: int
    is_eligible: bool
    reason: str                     # raison en français pour le diagnostic UX
    confidence: str = "unknown"     # "sure", "probable", "ambiguous", "ignore", "unknown"

@dataclass
class TopologySnapshot:
    timestamp: str                                          # ISO 8601
    objects: Dict[int, JeedomObject] = field(default_factory=dict)
    eq_logics: Dict[int, JeedomEqLogic] = field(default_factory=dict)

    @classmethod
    def from_jeedom_payload(cls, payload: dict) -> "TopologySnapshot":
        """Normalise le payload brut Jeedom en modèle canonique."""
        # ... normalisation des IDs en int, generic_type "" -> None, etc.

    def get_suggested_area(self, eq_id: int) -> Optional[str]:
        """Retourne le nom de l'objet Jeedom associé, ou None."""
        eq = self.eq_logics.get(eq_id)
        if eq and eq.jeedom_object_id and eq.jeedom_object_id in self.objects:
            return self.objects[eq.jeedom_object_id].name
        return None
```

**Normalisation dans `from_jeedom_payload()` — règles critiques :**

- IDs : `int(raw.get('id', 0))` — Jeedom retourne parfois des strings (`"42"`)
- `generic_type` : normaliser `""` et `null` vers `None`
- `is_enable` / `is_visible` : `bool(raw.get('is_enable', True))` — Jeedom peut retourner `"1"`/`"0"`
- `current_value` : conserver tel quel (sera interprété par le mapping engine plus tard)
- `unit` : normaliser `""` vers `None`

**Éligibilité — ordre de priorité des règles :**

| Priorité | Condition | Raison | Note |
|---|---|---|---|
| 1 | `is_excluded == True` | "Exclu par l'utilisateur" | Action volontaire, prioritaire sur tout |
| 2 | `is_enable == False` | "Équipement désactivé dans Jeedom" | |
| 3 | `len(cmds) == 0` | "Aucune commande détectée" | |
| 4 | Aucune cmd avec `generic_type` | "Aucun type générique configuré — configurez les types génériques sur les commandes dans Jeedom" | Raison la plus fréquente |
| 5 | Sinon | eligible, confidence "unknown" | Affiné par mapping engine Stories 2.2-2.5 |

> L'ordre est important : un équipement exclu ET désactivé affiche "Exclu" (action volontaire), pas "Désactivé".

**Stockage en RAM du daemon :**

```python
# Dans le handler /action/sync — stocker dans app state
request.app['topology'] = snapshot          # TopologySnapshot
request.app['eligibility'] = results       # Dict[int, EligibilityResult]
```

Pas de persistance disque en Story 2.1 (cache disque = Epic 5).

**PHP `getFullTopology()` — extraction sûre :**

```php
public static function getFullTopology(): array {
    $result = array('objects' => array(), 'eq_logics' => array());

    // Objects Jeedom (pièces/zones)
    foreach (jeeObject::all() as $obj) {
        $result['objects'][] = array(
            'id'        => intval($obj->getId()),
            'name'      => $obj->getName(),
            'father_id' => $obj->getFather_id() !== null
                           ? intval($obj->getFather_id()) : null,
        );
    }

    // EqLogics — exclure notre propre plugin
    foreach (eqLogic::all() as $eq) {
        if ($eq->getEqType_name() === __CLASS__) {
            continue;
        }
        $cmds = array();
        foreach (cmd::byEqLogicId($eq->getId()) as $cmd) {
            $cmds[] = array(
                'id'            => intval($cmd->getId()),
                'name'          => $cmd->getName(),
                'generic_type'  => $cmd->getGeneric_type() ?: null,
                'type'          => $cmd->getType(),
                'sub_type'      => $cmd->getSubType(),
                'current_value' => $cmd->getCache('value', null),
                'unit'          => $cmd->getUnite() ?: null,
                'is_visible'    => (bool)$cmd->getIsVisible(),
            );
        }
        $result['eq_logics'][] = array(
            'id'           => intval($eq->getId()),
            'name'         => $eq->getName(),
            'object_id'    => $eq->getObject_id() !== null
                              ? intval($eq->getObject_id()) : null,
            'is_enable'    => (bool)$eq->getIsEnable(),
            'is_visible'   => (bool)$eq->getIsVisible(),
            'eq_type'      => $eq->getEqType_name(),
            'generic_type' => $eq->getGeneric_type() ?: null,
            'is_excluded'  => (bool)$eq->getConfiguration('jeedom2ha_excluded', false),
            'cmds'         => $cmds,
        );
    }

    log::add(__CLASS__, 'info', '[TOPOLOGY] Scan complet : '
        . count($result['objects']) . ' objets, '
        . count($result['eq_logics']) . ' eqLogics');
    return $result;
}
```

> **`getCache('value', null)` au lieu de `execCmd()`** : `execCmd()` sur une commande `action` exécuterait l'action physiquement (allumer une lampe, ouvrir un volet). `getCache('value')` lit uniquement la dernière valeur connue sans effet de bord.

> **`getGeneric_type() ?: null`** : Jeedom peut retourner `""` pour les champs non renseignés. Normaliser en `null` pour simplifier les vérifications Python.

> **`__CLASS__` au lieu de `'jeedom2ha'`** : évite les erreurs de renommage.

### Contexte spatial — `suggested_area`

Le `suggested_area` de MQTT Discovery HA est un hint pour regrouper les entités dans une pièce. L'architecture spécifie : **les objets Jeedom servent de source de contexte spatial comme heuristique, pas comme équivalence stricte avec les HA areas**.

- `get_suggested_area(eq_id)` retourne le `name` de l'objet Jeedom associé, ou `None`
- Ce `suggested_area` sera injecté dans les payloads MQTT Discovery en Stories 2.2-2.5
- Pas de création automatique d'areas HA — juste un hint textuel

### Règle transverse Epic 2

> **Toute décision de mapping doit être déterministe, confidence-aware, diagnostiquable, et respecter la règle : ne pas publier plutôt que publier faux.**

Story 2.1 prépare cette règle en :
- Associant une `EligibilityResult` à chaque eqLogic
- Fournissant une `reason` explorable pour chaque inéligibilité
- Ne publiant rien vers MQTT (la publication vient en Stories 2.2-2.5)

### Project Structure Notes

**Fichiers à créer :**

```
resources/daemon/
  models/
    __init__.py               # CRÉER: package vide
    topology.py               # CRÉER: dataclasses + normalisation + éligibilité
tests/unit/
  test_topology.py            # CRÉER: tests normalisation TopologySnapshot
  test_eligibility.py         # CRÉER: tests éligibilité
```

**Fichiers à modifier :**

```
core/class/jeedom2ha.class.php               # MODIFIER: ajouter getFullTopology()
core/ajax/jeedom2ha.ajax.php                 # MODIFIER: ajouter case 'scanTopology'
resources/daemon/transport/http_server.py    # MODIFIER: ajouter route POST /action/sync
```

**Fichiers à NE PAS toucher :**

- `resources/daemon/main.py` — pas de changement daemon lifecycle
- `core/php/jeedom2ha.php` — callback stub inchangé (pure PHP, pas de dépendance Jeedom)
- `plugin_info/configuration.php` — pas de changement UI config
- `desktop/php/jeedom2ha.php` — l'UI de gestion sera modifiée dans les stories suivantes
- `desktop/js/jeedom2ha.js` — idem

### Pièges à éviter

- **NE PAS** appeler `$cmd->execCmd()` pour récupérer `current_value` — utiliser `$cmd->getCache('value', null)`. `execCmd()` exécuterait les commandes action (allumer des lampes, ouvrir des volets).
- **NE PAS** inclure la `configuration` complète des eqLogics/cmds dans le payload — extraire uniquement les champs nécessaires (`is_excluded` via `getConfiguration('jeedom2ha_excluded')`).
- **NE PAS** créer de modules `mapping/`, `discovery/`, `sync/`, `diagnostic/` dans cette story — ils seront créés dans les stories appropriées.
- **NE PAS** publier vers MQTT dans cette story — Story 2.1 est le scraping et la normalisation uniquement.
- **NE PAS** persister sur disque — le stockage RAM est suffisant. Le cache disque est Epic 5.
- **NE PAS** implémenter le mapping engine (traduction generic_type -> entité HA) — scope Stories 2.2-2.5. Story 2.1 se limite à l'éligibilité binaire.
- **NE PAS** appeler directement l'API JSON-RPC Jeedom depuis le daemon Python — le PHP pousse les données via POST. Le daemon reste découplé.
- **NE PAS** inclure les eqLogics de type `jeedom2ha` dans le scan — ce sont nos propres équipements.
- **NE PAS** confondre `generic_type` de l'eqLogic avec `generic_type` des commandes — le premier est rarement utilisé, le second est la clé de mapping.
- **NE PAS** trier ou filtrer les objects par `isVisible` — tous les objets sont des candidats pour `suggested_area`.

### Intelligences des Stories 1.x à réutiliser

- `callDaemon($endpoint, $payload, $method, $timeout)` dans `jeedom2ha.class.php` — POST avec timeout configurable. Utiliser timeout 15s pour le scan (peut prendre quelques secondes sur un gros parc).
- Enveloppe JSON standard — le daemon extrait `payload` depuis `data["payload"]`.
- `_check_secret(request, local_secret)` dans `http_server.py` — réutiliser pour `/action/sync`.
- Fixtures de test (`jeedom_eq_factory`, `jeedom_cmd_factory`) dans `tests/conftest.py` — les réutiliser ou les étendre.
- URL AJAX : `plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php`.
- Logger avec préfixes catégorisés : `[TOPOLOGY]` pour cette story.

### Déviation architecture documentée (héritée Story 1.1)

Les tests sont dans `tests/` (racine du repo) et non dans `resources/daemon/tests/` comme le spécifie l'architecture. Continuer avec cette convention jusqu'à arbitrage.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns — Naming Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns — Mapping Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Internal Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/project-context.md#Architecture Plugin Jeedom]
- [Source: _bmad-output/project-context.md#MQTT Discovery Home Assistant]
- [Source: _bmad-output/project-context.md#Règles PHP (Plugin Jeedom)]
- [Source: _bmad-output/project-context.md#Règles Python (Daemon)]
- [Source: _bmad-output/project-context.md#MVP Scope Guardrails]
- [Source: _bmad-output/project-context.md#Règles Critiques — Anti-Patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Status Badges]
- [Source: _bmad-output/implementation-artifacts/1-2-configuration-et-onboarding-mqtt-auto-manuel.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/1-2-bis-fiabilisation-auto-detection-mqtt-manager-import-force.md#Dev Notes]
- [Source: Jeedom dev docs — eqLogic::all(), cmd::byEqLogicId(), jeeObject::all(), getCache()]

## Dev Agent Record

### Agent Model Used

Antigravity (Claude) — code review session 2026-03-13

### Debug Log References

- Commit `623b623`: initial Story 2.1 implementation (models, http handler, PHP, tests)
- Commit `fdca7cb`: fix topology extraction resilience for plugin-specific eqLogic methods
- Code review fix commit: harden bool parsing (`_to_bool()`), add `confidence` field, add missing tests

### Completion Notes List

- Normalisation des IDs string→int robuste, avec skip silencieux des IDs invalides
- Normalisation `generic_type "" → None` fonctionne partout
- Normalisation booleans Jeedom (`"0"`/`"1"`) corrigée via `_to_bool()` (bug M4 fixé en code review)
- `confidence` ajouté à `EligibilityResult` ("sure" pour inéligibles, "unknown" pour éligibles)
- `getFullTopology()` PHP avec guards `method_exists()` pour plugins exotiques
- Handler `/action/sync` intégré dans `http_server.py` avec stockage RAM `app['topology']` et `app['eligibility']`
- 8 tests unitaires passent (5 topology + 3 eligibility)
- Suite complète : 99/99 passent

### File List

| Fichier | Action | Détail |
|---|---|---|
| `resources/daemon/models/__init__.py` | Créé | Package vide |
| `resources/daemon/models/topology.py` | Créé | Dataclasses + normalisation + éligibilité + `_to_bool()` |
| `resources/daemon/transport/http_server.py` | Modifié | Route POST `/action/sync` + import `TopologySnapshot`, `assess_all` |
| `core/class/jeedom2ha.class.php` | Modifié | `getFullTopology()` avec guards `method_exists()` |
| `core/ajax/jeedom2ha.ajax.php` | Modifié | Case `scanTopology` |
| `tests/unit/test_topology.py` | Créé | 5 tests (normalisation, robustesse, suggested_area, payload vide, string bools) |
| `tests/unit/test_eligibility.py` | Créé | 3 tests (règles, commandes mixtes, assess_all) |
| `tests/unit/test_http_server.py` | Modifié | Fix version assertion 0.1.0→0.2.0 (pre-existing) |
