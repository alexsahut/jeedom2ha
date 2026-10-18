# Story 25.2 : Route agrégée côté démon — états par pièce et par équipement en un appel

Status: backlog

> **Statut : `backlog` (2026-10-18).** Story rédigée par une session cloud déléguée (`create-story`, documentaire : aucun code, aucun test, aucun accès box / VM / Home Assistant / secret, CC-48). **`ready-for-dev` n'est pas accordé** : relecture ClaudeBox obligatoire, puis décisions sur les questions Q1 à Q13 (§ Questions ouvertes). Pointeurs de code pris sur `main` à `560f344` (après 25.1 : #279 `a704dd0`, R2 #282 `c940ac3`, statuts #285). Aucun nom réel d'équipement, de pièce, de scénario ou de personne : identifiants et données fictives seulement (CC-48).

## Story

En tant que développeur de la page principale (25.3) et de la vue maître-détail (25.4),
je veux appeler **une seule route du démon** qui me rend, pour toutes les pièces et tous les équipements, les **entrées** dont la fonction d'état `resolveEquipmentState` a besoin,
afin d'afficher la jauge « N publiés sur M », les cartes de pièce et l'arbre pièces → équipements **sans jamais lancer une boucle de ~300 `GET /system/mapping_overrides/{eq_id}`** à l'ouverture de la page.

**Parcours : démon seul** (`resources/daemon/`, tests Python). **Lecture seule stricte.** Aucun consommateur JS dans cette story (la consommation est pour 25.3 / 25.4) ; `resolveEquipmentState` n'est pas modifiée.

## Décisions transmises (ClaudeBox, par délégation d'Alexandre du 2026-10-18 23:50)

Consignées telles que transmises ; la session n'en a tranché aucune autre (voir § Questions ouvertes).

1. **Une seule source de vérité pour l'état.** La route renvoie, par pièce et par équipement, les **entrées** consommées par `resolveEquipmentState` (`sync_status`, éléments par catégorie, `equipment_decision`), **pas un état déjà résolu côté serveur**. Le JS calcule l'état final en appelant la même fonction `resolveEquipmentState`, alimentée par cette route au lieu d'appels unitaires.
2. **Pas de réécriture de la logique d'état en Python**, sauf justification concrète documentée ; dans ce cas, elle est une **question ouverte**, pas une décision de la session (→ Q1 : la lecture du code montre que « comptes par catégorie » précalculés en Python dupliqueraient la partition D3 du JS).
3. **`enabled` vient de Jeedom** (`j2haRoomsTree`), pas du démon : la route ne l'invente pas et ne le duplique pas (→ Q2 : relais ou non).
4. **Lecture seule stricte** : aucun nouveau champ de décision, aucune écriture, aucune publication modifiée.
5. **Cache invalidé à la fin de chaque synchro et après chaque écriture d'override** ; mécanisme exact (totale / partielle) à poser en question si ambigu (→ Q4).
6. **Budget de temps de réponse mesuré sur le parc réel (292 équipements)**, pas estimé ; aucune mesure terrain dans cette story (CC-48), elle est prévue (→ AC16, Task 7, Q10).

## Sources lues

- `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/epic-25-draft.md` §25.2 (« lecture seule, dérivé de la fonction d'état de 25.1, cache, invalidation à la synchro ; prérequis de performance pour 25.3 et 25.4 »).
- `…/CADRAGE.md`, section « Contraintes Jeedom » > Performance (« jauges B et arbre C = une route agrégée côté démon (états par pièce et par équipement en un appel) ; jamais 300 GET à l'ouverture »).
- `…/diagnostic-ux.md` § 5 point 9 (« les arbres ne sont lus qu'à l'ouverture d'une pièce (un GET par équipement) … route agrégée côté démon, la plus propre : un appel, quelques octets par pièce, ou chargement différé mis en cache. Ne pas lancer 300 GET ») et § 6 point 5.
- `_bmad-output/implementation-artifacts/25-1-socle-etat-unique-glossaire-palette-theme.md` (D1, D2, D3, décisions Q1-Q11) ; `_bmad-output/planning-artifacts/epics-projection-engine.md#Epic-25` ; `sprint-status.yaml` (entrée `25-2-route-agregee-cote-demon`, `backlog`).
- Code : `desktop/js/jeedom2ha_mapping_override.js` (lecture seule), `resources/daemon/transport/http_server.py`, `resources/daemon/mapping/overrides.py`, `core/ajax/jeedom2ha.ajax.php` (relais), `desktop/php/jeedom2ha.php` (`j2haRoomsTree`), `19-6-duree-action-ha-bornee-cc32.md` (précédent de test de charge, AC7).

## Contexte et périmètre

### Ce qui existe aujourd'hui (relevé sur `560f344`, à re-vérifier au SHA courant)

- **Un seul chemin de lecture, par équipement.** `GET /system/mapping_overrides/{eq_id}` (`http_server.py:4743` enregistrement, `_handle_mapping_overrides_get` `:3262`) appelle `_build_mapping_override_tree` (`:3074`). Le JS le lit via l'action ajax `getMappingOverrides` (`core/ajax/jeedom2ha.ajax.php:924+`, budget `JEEDOM2HA_RELAY_BUDGET_SHORT_S` = 15 s, `core/php/jeedom2ha_action_budget.php:39`), appelée depuis `jeedom2ha_mapping_surface.js:1434`. Aujourd'hui les arbres ne sont lus qu'à l'ouverture d'une pièce, un GET par équipement.
- **Coût par équipement du builder** : `list_overrides` + `list_equipment_overrides` (**deux lectures disque** du fichier d'overrides, `mapping/overrides.py:241/253` → `_load_raw`, sans cache mémoire), `assess_eligibility`, `evaluate_equipment`, `_resolve_command_mapping` par commande, et `_projection_valid_override_types` **par entité** (`:3162`, recalcule des évaluations pour le sélecteur « Type HA »). Ce dernier calcul (`override_types_allowed`) **n'est lu par aucune règle d'état**.
- **`resolveEquipmentState` (25.1)** est exportée par `jeedom2ha_mapping_override.js` (`:951`, exportée dans le bloc d'exports en fin de fichier). **Sa signature réelle est `resolveEquipmentState(tree, enabled)`** (la définition D1 de 25.1 écrivait `(tree)` ; `enabled` y est un paramètre explicite pour que « Désactivé » prime sur « Exclu » — R3). Elle normalise l'arbre (`normalizeTree` `:97`) puis lit :
  - `sync_status.{published_in_ha, current_should_publish, synced_should_publish, override_pending}` (`normalizeSyncStatus` `:86`) ;
  - `entities[].override_pending` (`entityIsPending` `:943`) ;
  - `equipment_decision` (vue de décision : `publication_reason`, `reason_code`, `should_publish`, `projection_validity.*`) pour « Désactivé »/« Exclu » (`isDisabledDiagnostic` / `isExcludedDiagnostic`) ;
  - **par commande** (`analyzeEquipment` `:909` → `classifyCommandCategory` `:869`) : `jeedom_cmd_id`, `published_in_ha`, `covered`, `diagnostic` (`ha_entity_type`, `reason_code`, `should_publish`, `publication_reason`, `projection_validity.{is_valid, reason_code, missing_capabilities, missing_fields}` via `readDiagnosticView` `:460`).
  La **partition « Ignorée / Bloquée »** (D3) vit dans le JS (`COMMAND_CAUSE_CATEGORIES`, `categoryOfCause` `:836`) à partir de ces codes de cause : **le démon ne sait pas ce qu'est une commande « Ignorée »**.
- **Consommateurs de l'état** qui s'appuieront sur la route : `summarizeEquipmentCounters` (`:1144`) et `summarizeRoom` (`:1167`, qui prend une liste d'arbres, `enabledById` et un total d'équipements pour signaler les « non lus »).
- **Pièces et `enabled`** : le PHP construit `j2haRoomsTree` (`desktop/php/jeedom2ha.php:12-56`) depuis Jeedom : `object_id`, `object_name`, `parent_number`, équipements `{eq_id, eq_name, enabled}`, pseudo-pièce `object_id = 0` pour les équipements sans objet. Le démon connaît `JeedomEqLogic.object_id` / `is_enable` (`models/topology.py:126+`) mais **depuis la dernière synchro seulement**.
- **État muté par** (les seuls événements qui changent une entrée de l'arbre) :
  - **fin de synchro** : `_handle_action_sync` (`:1576`, enveloppe) → `_do_handle_action_sync` (`:1781`, verrou `action_lock`) → corps (`:1813`), qui remplace `app["topology"]` / `["eligibility"]` (`:1841-1849`) et met à jour `["publications"]`, `["published_scope"]` (`:2194-2202`) ;
  - **écritures d'override** : `_handle_mapping_override_save` (`:3307`), `_handle_publication_override_save` (`:3376`), `_handle_mapping_override_revert` (`:3416`), `_handle_publication_override_revert` (`:3524`) — toutes via `overrides.save_*` / `remove_*` ;
  - **actions Publier / Supprimer / Republier** : `_handle_action_execute` (`:3953`, route `/action/execute`) qui modifie `app["publications"]`, `["pending_discovery_unpublish"]`, `["published_scope"]` (`:4117-4121`, `:4288`, `:4593`) — donc `sync_status.published_in_ha` (voir Q5) ; `_republish_all_from_cache` (`:1161`, sur reconnexion broker / naissance HA) ;
  - `overrides.import_profile` (`mapping/overrides.py:618`) **n'a aucun appelant HTTP** aujourd'hui (relevé par recherche dans `resources/`, `core/`, `desktop/`) : ce n'est pas un chemin d'écriture vivant, mais le garde-fou « signature du fichier » (AC10) le couvrirait s'il le devenait.
- **Précédent d'agrégat** : `GET /system/published_scope` (`:4748`, contrat `published_scope`, 200 + `status:"error"` avant la première synchro). **Précédent de test de charge** : `resources/daemon/tests/unit/test_story_19_6_load_ac7.py` (marqueur pytest `load`, exclu de la suite par défaut ; coût unitaire = maximum des mesures × `MARGE_MESURE` 1,5 × `MACHINE_FACTOR` 3 pour une box ≤ 3× plus lente que la VM de mesure). Parc de référence : 292 équipements au total (mesure 19-6 du 30/09).

### Dans le périmètre

- une route `GET` du démon, authentifiée par `X-Local-Secret`, qui rend en **un appel** les entrées d'état de tous les équipements connus du démon (AC1-AC8) ;
- un cache en mémoire du résultat, avec règles de construction, de durée de vie et d'invalidation (AC9-AC14) ;
- un refactor **minimal et non régressif** de `_build_mapping_override_tree` pour réutiliser *le même* constructeur sans recalculer ce qui n'est pas une entrée d'état (AC9, AC17) ;
- la mesure du budget de temps (test de charge synthétique ; procédure terrain à exécuter par ClaudeBox) (AC15-AC16).

### Hors périmètre (ne pas faire ici)

- toute modification de `desktop/` (donc de `resolveEquipmentState`, de la surface, du gate 20-0) — la consommation est pour 25.3 / 25.4 ;
- tout calcul de l'**état final** (`published`, `to_apply`, …), de ses **compteurs** ou de la partition D3 en Python (→ Q1) ;
- tout nouveau champ de décision, toute écriture, toute publication MQTT, tout changement de `evaluate_equipment()`, `CommandDecision`, `models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`, tables de mapping, fichiers *golden* ;
- le relais PHP `core/ajax/` et tout JS (→ Q9 : à trancher, **par défaut hors périmètre** puisque le périmètre transmis est le démon) ;
- toute mesure sur la box, la VM ou Home Assistant réels (CC-48) ; tout flag beta / stable / Market, tout autre plugin, les dongles.

## Contrat de la route (proposition, à confirmer par Q1-Q3, Q11-Q12)

**Méthode et chemin :** `GET /system/equipment_states` *(nom provisoire, Q11 ; pas `/system/mapping_overrides/aggregate`, qui entrerait en collision avec `/system/mapping_overrides/{eq_id}`)*. En-tête `X-Local-Secret` obligatoire (401 sinon, comme `_check_secret`). Paramètre optionnel `refresh=1` (contourne le cache pour cet appel, lecture toujours seule). Aucun corps.

**Réponse (HTTP 200)** — enveloppe identique à celle des routes voisines (`status`, `payload`) :

```json
{
  "status": "ok",
  "payload": {
    "schema_version": 1,
    "available": true,
    "meta": { "generated_at": "2026-10-18T12:00:00Z", "generation": 7, "cache": { "hit": false, "build_ms": 0 }, "equipments_total": 292, "equipments_read": 292 },
    "rooms": [ { "object_id": 3, "equipment_ids": [101, 102] }, { "object_id": 0, "equipment_ids": [205] } ],
    "equipments": {
      "101": {
        "jeedom_eq_id": 101,
        "equipment_decision": { "...": "vue de décision, contrat _decision_view" },
        "entities": [ { "override_pending": false } ],
        "commands": [ { "jeedom_cmd_id": 1001, "covered": true, "published_in_ha": true, "diagnostic": { "...": "vue de décision, contrat _decision_view" } } ],
        "sync_status": { "synced_should_publish": true, "current_should_publish": true, "override_pending": false, "published_in_ha": true }
      }
    },
    "unread": [ { "eq_id": 999, "reason": "not_in_topology" } ]
  }
}
```

- **`equipments[eq_id]` = l'arbre unitaire réduit à une liste blanche** des champs lus par `resolveEquipmentState` / `summarizeEquipmentCounters` (liste ci-dessus) ; les valeurs sont **celles que renverrait `GET /system/mapping_overrides/{eq_id}`** (même constructeur, AC3), jamais recalculées. Sont **exclus** : `override_types_allowed` (coût élevé, hors état), `attendu_ha`, `effective_ha`, `generic_type`, `cmd_name`, `eq_name`, `mapped`, `eligible`, `equipment_publication_override`, `entities[].decision` / `reason_details` / `publication_override` / `command_ids` / `present_in_ha` — rechargés par le GET unitaire quand l'utilisateur ouvre un équipement (25.4). *Hypothèse à confirmer : Q1.*
- **Pas d'état résolu, pas de compteur par catégorie, pas de `enabled`** dans la réponse (AC5).
- **`rooms`** : index **d'identifiants seulement** (`object_id` selon la convention du démon : `null`/`-1` → `0`, comme `j2haRoomsTree`), aucun nom, aucun compteur, **non autoritaire** (instantané de la dernière synchro) : la liste des pièces, leurs noms, leur ordre et `enabled` restent ceux de Jeedom (`j2haRoomsTree`). → Q3.
- **`unread`** : équipement connu de l'appelant mais absent de la topologie du démon, ou dont la construction échoue (`not_in_topology`, `build_error`) — isolé, jamais fatal pour la réponse (AC7). Le JS le compte déjà comme « non lu » (`summarizeRoom`, `equipments_read` / `equipments_total`).
- **Avant la première synchro** (`app["topology"]` est `None`) : `payload.available = false`, `equipments = {}`, `rooms = []` (→ Q12).

## Acceptance Criteria

Convention : chaque AC est vérifiable par un test nommé (pytest, Node, PHP) ou par une commande dont le résultat est écrit dans l'AC. Tout nombre de budget est celui de Q10 (aucun chiffre n'est inventé ici).

### A. La route et son contrat

**AC1 — La route existe, authentifiée, documentée**
**Given** le démon (`create_app`)
**When** on appelle `GET <chemin de Q11>` avec puis sans `X-Local-Secret` valide
**Then** la réponse est 200 `status:"ok"` avec le secret, **401** `{"status":"error","message":"Unauthorized"}` sans (comme `_handle_mapping_overrides_get`) ; toute autre méthode que `GET` est refusée par aiohttp (405)
**And** la méthode, le chemin, les paramètres et la forme de la réponse (section « Contrat de la route », éventuellement amendée par les décisions Q1-Q3/Q11-Q12) sont repris dans la docstring du handler et dans cette story (§ Dev Notes > Contrat final), sans autre document à créer
**And** le test `test_story_25_2_route_agregee.py` couvre l'enregistrement de la route dans `create_app` (à côté de `:4743`).

**AC2 — Forme de la réponse**
**Given** une topologie fictive de ≥ 3 pièces (dont la pseudo-pièce `object_id=0`) et de plusieurs équipements (publié, exclu, désactivé, sans commande, multi-entités)
**When** la route est appelée
**Then** `payload` contient `schema_version`, `available`, `meta` (`generated_at`, `generation`, `cache.hit`, `equipments_total`, `equipments_read`), `rooms`, `equipments` (clés = `str(eq_id)`), `unread`
**And** chaque `equipments[eq_id]` ne porte **que** les champs de la liste blanche (test d'égalité de l'ensemble des clés à chaque niveau : équipement, `entities[]`, `commands[]`, `sync_status`)
**And** l'ordre des commandes et des entités est l'ordre natif de l'arbre unitaire (le JS ne trie pas : AC3 de 22-2, rappelé dans `normalizeTree`).

**AC3 — Mêmes valeurs que l'arbre unitaire (un seul constructeur)**
**Given** un corpus d'équipements fictifs couvrant les règles R1-R8 de D1 (25.1) et la partition D3
**When** on compare, pour chaque `eq_id`, `equipments[eq_id]` à la **projection sur la liste blanche** de la réponse de `GET /system/mapping_overrides/{eq_id}`
**Then** les deux sont **strictement égaux** (`==` profond) ; le builder est le même (`_build_mapping_override_tree`), pas une seconde implémentation
**And** le test échoue si un champ de la liste blanche diverge de l'arbre unitaire, ou si la liste blanche contient un champ absent de l'arbre unitaire.

**AC4 — Parité d'état prouvée côté JS (la source de vérité reste `resolveEquipmentState`)**
**Given** le test Node `tests/unit/test_story_25_2_parite_etat.node.test.js` et des fixtures JSON fictives dérivées du corpus de l'AC3 (arbre unitaire complet / entrée agrégée correspondante, versionnées dans `tests/fixtures/`)
**When** on exécute `resolveEquipmentState(arbre, enabled)` et `summarizeEquipmentCounters(arbre, enabled)` **sur l'arbre complet et sur l'entrée agrégée**, pour `enabled ∈ {true, false, undefined}`
**Then** les résultats sont `deepEqual` pour chacun des 6 états de D1 et pour les croisements de l'AC2 de 25.1 (désactivé+exclu, jamais synchronisé, présence `null`, capteur secondaire seul publié…)
**And** `git diff main...HEAD -- desktop/` est **vide** : `resolveEquipmentState` et ses helpers ne sont pas modifiés.

**AC5 — Aucune décision pré-calculée**
**Given** la réponse de la route
**When** on cherche, à tous les niveaux, les clés `state`, `blocked_mention`, `by_state`, `defects`, `counts`, `enabled`, `category`, `to_apply`, `blocked_count`, `ignored`
**Then** aucune n'existe (test table-driven sur l'arbre JSON)
**And** aucun module de `resources/daemon/` ne contient la partition D3 (`no_generic_type_configured`… regroupés en « Ignorée »/« Bloquée ») : `grep -rn "COMMAND_CAUSE_CATEGORIES\|categoryOfCause" resources/daemon/` ne renvoie rien.

**AC6 — Lecture seule stricte**
**Given** un appel de la route (à froid, à chaud, avec `refresh=1`)
**When** on observe le démon
**Then** aucun message MQTT n'est publié (faux pont : 0 appel `publish_message`), `app["publications"]`, `["pending_discovery_unpublish"]`, `["published_scope"]`, `["topology"]` sont **identiques** avant/après (comparaison profonde), le fichier d'overrides et le cache disque de publications ne sont **pas réécrits** (`mtime_ns` inchangé)
**And** `git diff --stat main...HEAD -- resources/daemon/models/ resources/daemon/mapping/ resources/daemon/discovery/ resources/daemon/sync/ resources/daemon/transport/mqtt_client.py` est vide, hors le refactor autorisé à l'AC9 (qui ne touche que `transport/http_server.py`)
**And** aucun champ de décision nouveau n'est ajouté à une route existante.

**AC7 — Isolation des erreurs par équipement**
**Given** un équipement dont la construction lève une exception (fixture : `cmds` incohérents, builder patché) et des identifiants absents de la topologie
**When** la route est appelée
**Then** la réponse reste 200, l'équipement fautif est dans `unread` (`reason:"build_error"`, **sans message d'exception ni nom** ; détail seulement dans le log du démon), les autres équipements sont complets, `equipments_read` = `equipments_total − len(unread)`
**And** un équipement fautif n'est pas mis en cache comme valide (il est reconstruit à la prochaine génération).

**AC8 — Avant la première synchro**
**Given** `app["topology"]` à `None`
**When** la route est appelée
**Then** la réponse suit la décision de Q12 (par défaut : 200 `status:"ok"`, `available:false`, `equipments:{}`, `rooms:[]`, `unread:[]`), sans exception, sans mise en cache d'un résultat vide qui survivrait à la première synchro (test : GET avant, synchro, GET après → équipements présents).

### B. Cache

**AC9 — Construction : une passe, un seul chargement des overrides, pas de calcul hors état**
**Given** un parc fictif de N équipements
**When** le cache est construit
**Then** le fichier d'overrides est lu **une seule fois** pour toute la passe (test : le nombre d'appels à `list_overrides` + `list_equipment_overrides` est ≤ 2, pas 2 × N ; `_build_mapping_override_tree` accepte les dictionnaires déjà chargés en paramètre optionnel, repli sur le comportement actuel quand ils sont absents)
**And** `_projection_valid_override_types` **n'est pas appelée** pour la route agrégée (test : mock non appelé), via un paramètre explicite du builder (valeur par défaut = comportement actuel inchangé)
**And** les deux modifications du builder sont additives : appelé comme aujourd'hui, `_build_mapping_override_tree` rend exactement la même structure (AC17).

**AC10 — Durée de vie et validité**
**Given** une entrée de cache construite à la génération G
**When** une requête arrive
**Then** l'entrée est servie (`meta.cache.hit:true`) tant que **toutes** ces conditions tiennent : (a) aucune invalidation explicite depuis sa construction (AC11-AC13) ; (b) la signature du fichier d'overrides (`os.stat` : `st_mtime_ns`, `st_size`, ou absence) est inchangée — filet de sécurité contre une écriture hors des handlers listés ; (c) l'objet `app["topology"]` est le même (identité) ; (d) l'âge est inférieur au plafond de sécurité de Q8 (sans plafond si Q8 le supprime)
**And** sinon elle est reconstruite à la requête suivante ; deux requêtes concurrentes pendant une construction ne la lancent qu'**une fois** (test avec deux `await` simultanés : un seul build, deux réponses identiques) (Q6, Q7)
**And** le cache est **en mémoire, par processus** ; il n'est jamais écrit sur disque et disparaît au redémarrage du démon (aucun besoin de migration).

**AC11 — Invalidation à la fin de chaque synchro**
**Given** un cache construit
**When** une synchro se termine (succès, succès partiel **ou échec** après avoir muté `topology` / `publications` / `published_scope`)
**Then** le cache est invalidé sur **toutes** les sorties du handler de synchro (idéalement une seule fois, dans l'enveloppe `_handle_action_sync`, `try/finally`, à vérifier au dev-story contre `_do_handle_action_sync` `:1781+`) ; la requête suivante reconstruit et reflète le nouvel état (test : GET → synchro fictive qui change `published_in_ha` → GET)
**And** une construction **démarrée avant la fin de la synchro** et terminée après ne remplace pas l'entrée (comparaison de génération : un résultat périmé est rendu à son appelant mais jamais stocké) (test déterministe par barrière)
**And** un `GET` pendant une synchro ne bloque pas la synchro (le verrou `action_lock` n'est pas pris par la route).

**AC12 — Invalidation après chaque écriture d'override**
**Given** un cache construit
**When** l'un des quatre handlers d'écriture (`mapping_override` save/revert, `publication_override` save/revert) **persiste** un changement
**Then** le cache est invalidé avant que le handler ne réponde ; le `GET` agrégé suivant montre le nouvel `override_pending` de l'équipement concerné (test : GET → POST `publication_override` `force_publish` → GET : `sync_status.override_pending` ou `entities[].override_pending` passe à `true` conformément à l'arbre unitaire)
**And** une écriture refusée (400/404/409/500) n'a pas besoin d'invalider ; si elle le fait par prudence, c'est sans effet visible (non testé comme exigence)
**And** le mécanisme (totale / partielle) est celui de Q4 ; **par défaut, totale**.

**AC13 — Invalidation après les actions qui changent la présence dans HA** *(sous réserve de Q5)*
**Given** un cache construit
**When** `/action/execute` publie, supprime ou republie (y compris `_republish_all_from_cache`, reconnexion broker, naissance HA)
**Then** le cache est invalidé ; le `GET` suivant montre `sync_status.published_in_ha` à jour pour les équipements concernés
**And** un test table-driven énumère **chaque** chemin du démon qui écrit dans `app["publications"]`, `["pending_discovery_unpublish"]` ou `["published_scope"]` (recherche par `grep` dans le test lui-même, échoue si un chemin n'est pas dans la liste connue) pour qu'un futur chemin d'écriture oublié soit détecté.

**AC14 — Contournement explicite et observabilité**
**Given** une entrée en cache
**When** on appelle avec `refresh=1`
**Then** une reconstruction a lieu et remplace l'entrée (la génération avance) ; `meta.cache.hit:false` ; sans `refresh`, `meta.cache.hit:true`
**And** chaque construction journalise **une ligne** `INFO` au format `[AGGREGATE] build equipments=N unread=U build_ms=X bytes=B generation=G` (aucun nom ni identifiant d'équipement dans cette ligne ; `bytes` = taille JSON de la réponse) — c'est l'instrument de mesure de l'AC16.

### C. Performance

**AC15 — Budget de temps mesuré en test de charge (parc synthétique de 292 équipements)**
**Given** un test `resources/daemon/tests/unit/test_story_25_2_load.py` marqué `load` (exclu de la suite par défaut, comme `test_story_19_6_load_ac7.py`) avec **292 équipements fictifs** de formes représentatives (peu de commandes, beaucoup de commandes, multi-entités, mappings secondaires, exclus, désactivés, sans commande ; la forme la plus coûteuse déclarée)
**When** il mesure la construction à froid, l'appel à chaud (cache), la taille de la charge utile, avec le **vrai** `MapperRegistry` et le vrai `evaluate_equipment` (pas de `MagicMock`)
**Then** le test consigne `c_eq` (coût unitaire = maximum des mesures × `MARGE_MESURE` × `MACHINE_FACTOR`, méthode de 19-6), `build_cold_ms`, `hit_ms`, `bytes`, et vérifie : `build_cold_ms ≤ budget_froid`, `hit_ms ≤ budget_chaud`, `bytes ≤ budget_taille`, les trois budgets étant ceux fixés par **Q10** (aucun chiffre n'est inscrit tant que Q10 n'est pas tranchée)
**And** il compare à la **boucle actuelle** (292 × `_build_mapping_override_tree` sans les optimisations de l'AC9) et consigne le rapport, pour justifier la route
**And** les chiffres mesurés sont reportés dans le Dev Agent Record de la story ; si un budget n'est pas tenu, la story le dit (elle ne l'ajuste pas à la hausse sans décision).

**AC16 — Mesure sur le parc réel : procédure écrite, exécution réservée à ClaudeBox**
**Given** le déploiement de la story sur la box (Task 7, hors session cloud)
**When** ClaudeBox appelle la route localement depuis la box (secret local, jamais consigné) sur le parc réel de 292 équipements
**Then** il relève, **à froid puis à chaud** (3 appels chacun, plus un appel après une écriture d'override puis après une synchro), la durée de bout en bout, `build_ms` et `bytes` de la ligne `[AGGREGATE]`, et le temps total du relais PHP si Q9 inclut le relais
**And** les valeurs sont consignées (identifiants seuls, aucun nom réel, CC-48) dans `25-2-preuve-terrain-<date>.md`, comparées aux budgets de Q10 ; la story ne passe pas à `done` sans ce relevé
**And** la session cloud ne fait **aucune** de ces mesures (CC-48) et le dit dans la PR.

### D. Non-régression et conventions

**AC17 — Les routes existantes ne changent pas**
**Given** les routes consommées par 25.1 : `GET /system/mapping_overrides/{eq_id}`, `POST /action/mapping_override` et `_revert`, `POST /action/publication_override` et `_revert`, `POST /system/overrides/preview`, `POST /action/execute`, `POST /action/sync`, `GET /system/published_scope`, `GET /system/status`
**When** les suites existantes tournent et qu'un test d'instantané compare la réponse de `GET /system/mapping_overrides/{eq_id}` avant/après le refactor de l'AC9 sur le corpus de l'AC3
**Then** la réponse est **identique octet pour octet** (test d'instantané écrit *avant* le refactor, Task 1), y compris `override_types_allowed`
**And** `test_story_16_5_mapping_override_ui_endpoints.py`, `test_story_8_3_http_server_dispatch.py`, les tests des stories 19.3, 20.2, 21.1, 22.2 touchant l'arbre, `test_story_8_4_golden_file.py` et `test_story_19_0_parity_golden_corpus.py` passent **sans modification**
**And** les seuls changements des handlers d'écriture et de synchro sont l'ajout d'un appel d'invalidation (diff relu : aucune autre ligne ne change).

**AC18 — Aucun effet sur l'interface**
**Given** la branche de la story
**When** on exécute `git diff --stat main...HEAD -- desktop/ core/ plugin_info/`
**Then** la sortie est **vide** (sauf décision Q9 en faveur du relais, auquel cas seul `core/ajax/jeedom2ha.ajax.php` et son test PHP changent, lecture seule, budget `JEEDOM2HA_RELAY_BUDGET_SHORT_S`)
**And** l'inventaire des requêtes du gate (`tests/e2e/gate/page-load-request-inventory.mjs`) est inchangé : la route n'est appelée par aucune page tant que 25.3 n'est pas livrée.

**AC19 — Conventions de la story**
**Given** CLAUDE.md et `_bmad-output/project-context.md`
**When** la PR de dev est ouverte
**Then** une branche / une PR ; titre Conventional Commits ; `make test`, `pytest`, `flake8`, `node --test tests/unit/*.node.test.js` passent ; `scripts/ci-local.sh` vert avant push ; aucune fixture ne contient de nom réel d'équipement, de pièce, de scénario ou de personne, ni IP privée ni secret (CC-48)
**And** la Task 0 et la Task 7 (réservées à l'humain / ClaudeBox) sont sautées par la session cloud et la PR le dit.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) **[réservé à l'humain / ClaudeBox ; une session cloud NE LA FAIT PAS (CC-48 : aucun accès box, SSH ni Home Assistant)]**
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
- [ ] Task 1 — Filet de non-régression **avant tout code** (AC: 3, 17)
  - [ ] 1.1 Corpus fictif d'équipements couvrant R1-R8 / D3 (fixtures partagées pytest + JSON pour Node).
  - [ ] 1.2 Test d'instantané de `GET /system/mapping_overrides/{eq_id}` sur ce corpus (octet pour octet), écrit et vert **avant** de toucher le builder.
- [ ] Task 2 — Parité (tests d'abord) (AC: 2, 3, 4, 5)
  - [ ] 2.1 `test_story_25_2_route_agregee.py` : forme, liste blanche, égalité avec la projection de l'arbre unitaire, clés interdites, absence de la partition D3 dans le démon.
  - [ ] 2.2 `test_story_25_2_parite_etat.node.test.js` : `resolveEquipmentState` / `summarizeEquipmentCounters` identiques sur arbre complet et entrée agrégée.
- [ ] Task 3 — Builder réutilisable, additif (AC: 9, 17)
  - [ ] 3.1 `_build_mapping_override_tree` : paramètres optionnels (dictionnaires d'overrides déjà chargés ; omission du calcul `override_types_allowed`) ; valeurs par défaut = comportement actuel.
  - [ ] 3.2 Instantané de la Task 1.2 toujours vert.
- [ ] Task 4 — Route et cache (AC: 1, 2, 6, 7, 8, 10, 14)
  - [ ] 4.1 Handler `GET` + enregistrement dans `create_app` ; état du cache sous une clé `app[…]` unique initialisée dans `create_app`.
  - [ ] 4.2 Construction en une passe, isolation des erreurs (`unread`), single-flight, comparaison de génération, signature du fichier d'overrides, plafond (Q8), `refresh=1`, journal `[AGGREGATE]`.
- [ ] Task 5 — Invalidation (AC: 11, 12, 13)
  - [ ] 5.1 Fin de synchro (toutes sorties) ; 4 handlers d'override ; `/action/execute` et `_republish_all_from_cache` (selon Q5).
  - [ ] 5.2 Tests GET → écriture → GET, GET → synchro → GET, test d'énumération des chemins d'écriture de l'état.
- [ ] Task 6 — Charge et non-régression (AC: 15, 17, 18, 19)
  - [ ] 6.1 `test_story_25_2_load.py` (`load`), 292 équipements fictifs, comparaison avec la boucle actuelle.
  - [ ] 6.2 `make test`, `pytest`, `flake8`, `node --test tests/unit/*.node.test.js`, `scripts/ci-local.sh` ; `git diff --stat` des AC6 / AC18 vides comme attendu.
- [ ] Task 7 — Preuve terrain (humain / ClaudeBox, après fusion ; CC-48)
  - [ ] 7.1 Relevé du budget sur le parc réel (AC16) dans `25-2-preuve-terrain-<date>.md`.
  - [ ] 7.2 Vérification qu'aucune publication HA ni inventaire MQTT n'a changé (gate d'inventaire identique) et 0 `ERROR` dans le journal du démon.

## Dev Notes

### Dev Agent Guardrails

- **Ne jamais** écrire l'état final, des compteurs ou la partition « Ignorée / Bloquée » en Python (décision 1-2, AC5) : ce serait une seconde implémentation de `resolveEquipmentState`. Si l'implémentation bute sur une impossibilité technique, **s'arrêter** et la consigner sous Q1, ne pas contourner.
- **Un seul constructeur** : l'entrée agrégée est une projection de `_build_mapping_override_tree`, jamais un calcul parallèle (AC3).
- **Ne rien changer au comportement de `GET /system/mapping_overrides/{eq_id}`** (AC17) : paramètres du builder additifs, instantané avant/après.
- **Lecture seule** : pas de publication MQTT, pas d'écriture disque, pas de mutation de `app[…]` autre que l'état du cache (AC6).
- `enabled` n'est pas relayé par défaut (Q2) ; le démon ne devine jamais l'activation Jeedom autrement que par la décision déjà portée (`disabled_eqlogic`).
- Pas de nom ni de message d'exception dans `unread` ni dans la ligne `[AGGREGATE]` (CC-48 côté preuve).
- Le cache ne doit jamais servir un état **antérieur à une invalidation** : en cas de doute, reconstruire. Un oubli d'invalidation est un bug d'affichage silencieux (AC13).
- Une session cloud saute la Task 0 et la Task 7 et le dit dans la PR ; aucun accès box, SSH, Home Assistant, secret.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Contrat final

*(à compléter au `dev-story` : copier ici la forme définitive de la réponse, après décisions Q1-Q3 et Q11-Q12.)*

### Précédents et garde-fous réutilisables

- Test de charge : `resources/daemon/tests/unit/test_story_19_6_load_ac7.py` (marqueur `load`, coût unitaire = maximum × `MARGE_MESURE` × `MACHINE_FACTOR`, vrai `MapperRegistry`, écriture dans `tmp_path`).
- Convention d'agrégat avant première synchro : `_handle_system_published_scope` (`:4748`).
- Fixtures de topologie : `test_story_16_5_mapping_override_ui_endpoints.py` (`create_app`, `aiohttp_client`, `TopologySnapshot`, `JeedomEqLogic`).
- Verrou d'actions : `app["action_lock"]` (`:1787`) — la route ne le prend pas (AC11).

### Tests existants à surveiller

`test_story_16_5_mapping_override_ui_endpoints`, `test_story_8_3_http_server_dispatch`, tests 19.3 / 20.2 / 21.1 / 22.2 qui lisent l'arbre, `test_story_19_6_*`, `test_story_8_4_golden_file`, `test_story_19_0_parity_golden_corpus`, et côté Node les suites `test_story_25_1_*` (doivent rester vertes sans modification).

### Fichiers probablement touchés (pour le `dev-story`)

`resources/daemon/transport/http_server.py` (route, cache, invalidations, paramètres additifs du builder) ; nouveaux `resources/daemon/tests/unit/test_story_25_2_route_agregee.py`, `test_story_25_2_load.py`, `tests/unit/test_story_25_2_parite_etat.node.test.js`, fixtures sous `tests/fixtures/` ; éventuellement `core/ajax/jeedom2ha.ajax.php` + un test PHP **seulement** si Q9 est tranchée en ce sens.

### Definition of done

AC1 à AC19 tenus ; suites locales vertes ; budgets de Q10 respectés en test de charge ; PR relue par ClaudeBox ; preuve terrain (Task 7) ; statut `done` après la preuve terrain (pas de validation UX : aucune surface ne change, `UI Impact: Non`).

### References

- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/epic-25-draft.md`#Stories proposées, 25.2]
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/CADRAGE.md`#Contraintes Jeedom — Performance]
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/diagnostic-ux.md`#5 point 9, #6 point 5]
- [Source: `_bmad-output/implementation-artifacts/25-1-socle-etat-unique-glossaire-palette-theme.md`#D1, #D2, #D3, #Décisions]
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md`#Epic-25]
- [Source: `_bmad-output/implementation-artifacts/19-6-duree-action-ha-bornee-cc32.md`#AC7] — précédent de test de charge
- [Source: `CLAUDE.md`, `docs/delegation-claude-cloud.md`, `_bmad-output/project-context.md`]

## UI Impact

- **UI Impact:** Non — route de démon en lecture seule, aucun fichier de `desktop/`, `core/` (sauf Q9) ni `plugin_info/` modifié ; la consommation par l'interface est livrée par 25.3 et 25.4 (qui porteront le gate 20-0 et `ready-for-UX-validation`).

## Dev Agent Record

### Agent Model Used

Session cloud déléguée Claude Code (`create-story`, documentaire), 2026-10-18.

### Debug Log References

### Completion Notes List

- Rédaction `create-story` : documentaire seulement ; aucun fichier de code, de test ou de doc utilisateur modifié ; statut **`backlog` conservé** (`ready-for-dev` non accordé : relecture ClaudeBox obligatoire, Q1-Q13 à trancher). `sprint-status.yaml` : seul le commentaire de l'entrée `25-2-route-agregee-cote-demon` est complété, le statut reste `backlog`.
- Écarts relevés par rapport au brief et à 25.1, à confirmer par ClaudeBox :
  1. Le brief parle de « comptes par catégorie » parmi les entrées : `resolveEquipmentState` ne reçoit **pas** de comptes, elle les **dérive** des diagnostics par commande, via une partition (D3) qui n'existe qu'en JS. La story retient donc des **lignes de commande réduites**, pas des comptes précalculés (→ Q1).
  2. La signature réelle est `resolveEquipmentState(tree, enabled)` (D1 de 25.1 écrivait `(tree)`).
  3. Les écritures d'override et la synchro ne sont pas les seuls événements qui changent `published_in_ha` : `/action/execute` (Publier / Supprimer / Republier) et `_republish_all_from_cache` aussi (→ Q5).
  4. Sans relais `core/ajax`, la route n'est pas atteignable depuis le JS ; le périmètre transmis étant le démon, il est posé en question (→ Q9).
- Aucune mesure de budget n'a été faite ni inventée (CC-48) ; la méthode est écrite (AC15-AC16).

### File List

- Story : ce fichier.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (commentaire de l'entrée 25-2 seulement).

## Questions ouvertes pour ClaudeBox / Alexandre

Chaque question porte une **recommandation** ; **aucune n'est tranchée par la session**. Les AC écrits « par défaut » ci-dessus suivent la recommandation, pour qu'une réponse « je valide les recommandations » rende la story prête sans réécriture.

**Q1 — Quelles « entrées » exactement : lignes de commande réduites, comptes précalculés, ou arbres complets ?**
- A. **Arbre unitaire réduit à une liste blanche** (`sync_status`, `equipment_decision`, `entities[].override_pending`, et par commande `jeedom_cmd_id`/`covered`/`published_in_ha`/`diagnostic`) — fidèle à « les entrées de `resolveEquipmentState` », aucune logique dupliquée, parité testable (AC3-AC4). *(recommandé)* Contrepartie : charge utile plus lourde qu'avec des comptes (à mesurer, Q10).
- B. **Comptes par catégorie précalculés** par le démon (publiées / bloquées / ignorées…) : charge minimale, mais impose la partition D3 « Ignorée/Bloquée » en Python, soit une **seconde implémentation** de l'état — contraire à la décision 2 sauf justification ; justification technique concrète : aucune relevée (la partition ne dépend que de codes déjà portés).
- C. **Arbres complets** (même contenu que le GET unitaire) : zéro projection, mais recalcule `override_types_allowed` (coûteux) et alourdit la charge utile pour rien.

**Q2 — Faut-il relayer `enabled` (activation Jeedom vue par le démon) ?**
- A. Non : `enabled` vient de `j2haRoomsTree` (live, PHP) ; le démon l'exprime déjà par `equipment_decision.publication_reason = disabled_eqlogic`. *(recommandé)*
- B. Oui, un champ informatif `daemon_is_enable` relayé tel quel — source de divergence possible (instantané de la dernière synchro), donc déconseillé.

**Q3 — Index `rooms` dans la réponse ?**
- A. Garder `rooms: [{object_id, equipment_ids}]`, ids seulement, non autoritaire (la liste, les noms et l'ordre des pièces restent ceux de Jeedom) ; sert à repérer un écart pièce/équipement entre Jeedom et le démon. *(recommandé : « par pièce » du brief, coût négligeable)*
- B. Supprimer `rooms` : carte plate `equipments`, le JS regroupe avec `j2haRoomsTree` (une seule source pour l'appartenance aux pièces).

**Q4 — Invalidation totale ou partielle ?**
- A. **Totale** à chaque fin de synchro, écriture d'override et action ; reconstruction paresseuse. *(recommandé : simple, pas d'état intermédiaire faux ; à justifier par la mesure)*
- B. Partielle pour les écritures d'override (reconstruire seulement l'`eq_id` touché), totale à la synchro — moins de CPU par écriture, plus de cas à tester (une entité partagée, `_apply_pending_scope_flags`…). À n'envisager que si le coût de construction à froid mesuré (AC15) dépasse le budget de Q10.

**Q5 — Les actions Publier / Supprimer / Republier (et la republication sur reconnexion broker / naissance HA) doivent-elles aussi invalider ?**
- A. Oui (AC13) : elles changent `published_in_ha` ; sans cela, la jauge « après chaque action » de 25.3 (Q2 du cadrage) afficherait un état périmé. *(recommandé)* Cela étend le texte transmis (« synchro et écriture d'override ») à un troisième événement.
- B. Non : le cache est alors rafraîchi seulement par synchro, override et plafond de Q8 ; 25.3 devrait appeler `refresh=1` après chaque action.

**Q6 — Construction paresseuse ou réchauffage après synchro ?**
- A. **Paresseuse** (au premier appel après invalidation), single-flight. *(recommandé : n'allonge pas la synchro, dont la durée est bornée par le relais, cf. 19-6)*
- B. Réchauffage en tâche de fond à la fin de la synchro : première lecture instantanée, mais travail inutile si personne n'ouvre la page et risque de contention avec la fin de synchro.

**Q7 — Où s'exécute la construction : boucle d'événements ou `run_in_executor` ?**
- A. **Synchrone dans la boucle, en une passe sans `await`** si le coût à froid mesuré tient dans le budget de Q10 : atomique par rapport à la synchro et aux actions (pas d'état mi-muté lu). *(recommandé)*
- B. `run_in_executor` si la construction bloque trop longtemps la boucle (écouteurs MQTT, autres routes) : exige la comparaison de génération (AC11) pour écarter un résultat construit sur un état en cours de mutation.

**Q8 — Plafond de durée de vie de sécurité et contournement (`refresh=1`) ?**
- A. Plafond de sécurité (valeur à fixer par ClaudeBox, de l'ordre de quelques minutes) **et** `refresh=1` (utile au bouton « Actualiser » de 25.3). Le plafond ne remplace pas les invalidations : il borne l'effet d'un chemin d'écriture oublié. *(recommandé)*
- B. Pas de plafond : seulement les invalidations explicites et la signature du fichier d'overrides.

**Q9 — Le relais PHP `core/ajax/jeedom2ha.ajax.php` est-il dans 25.2 ?**
- A. Oui, minimal : une action ajax en lecture seule qui relaie la route (budget `JEEDOM2HA_RELAY_BUDGET_SHORT_S`), plus un test PHP, pour que la route soit atteignable et testée de bout en bout avant 25.3. *(recommandé)* Le périmètre transmis étant « démon + lecture de `desktop/` », le relais est hors périmètre tant que ClaudeBox ne l'accorde pas.
- B. Non : le relais est livré par 25.3 avec son premier consommateur ; 25.2 reste strictement démon.

**Q10 — Quels budgets chiffrés ?** (la session n'en invente aucun ; ils conditionnent AC15-AC16)
Proposition de forme, valeurs à fixer par ClaudeBox : un budget de **construction à froid** et un budget **à chaud (cache)** au niveau du démon, un budget de **taille de charge utile**, et le **budget de bout en bout avec relais** à tenir sous `JEEDOM2HA_RELAY_BUDGET_SHORT_S` (15 s) avec marge. Méthode (recommandée) : test de charge synthétique (AC15, méthode de 19-6) pour la non-régression ; **mesure terrain unique** par ClaudeBox sur les 292 équipements (AC16) pour la valeur de référence ; les budgets sont arrêtés **après** cette première mesure terrain si besoin et le test de charge ajusté par décision explicite.

**Q11 — Nom de la route.** Recommandation : `GET /system/equipment_states` (cohérent avec `/system/…`, pas de collision avec `/system/mapping_overrides/{eq_id}`). Alternative : `/system/mapping_states`.

**Q12 — Réponse avant la première synchro (`topology` à `None`).**
- A. 200 `status:"ok"`, `payload.available:false`, collections vides : le JS distingue « pas encore prêt » sans traiter une erreur. *(recommandé)*
- B. Convention de `published_scope` : 200 `status:"error"` + message « appelez /action/sync d'abord ».

**Q13 — Cohérence avec 25.3 sur la fraîcheur.** Le cadrage (Q2) calcule les jauges « à l'ouverture, après chaque action, à chaque fin de synchro, plus un bouton Actualiser ». Confirmer que 25.3 s'appuiera sur l'invalidation côté démon (AC11-AC13) et réservera `refresh=1` au bouton « Actualiser », plutôt que de forcer `refresh=1` à chaque ouverture (ce qui annulerait le cache). *(recommandé : oui)*

## Change Log

- 2026-10-18 — Création (`create-story`, session cloud déléguée) : story rédigée, statut `backlog`, 19 AC, 13 questions ouvertes pour ClaudeBox / Alexandre ; décisions de ClaudeBox du 2026-10-18 23:50 (par délégation d'Alexandre) consignées ; `ready-for-dev` non accordé.
