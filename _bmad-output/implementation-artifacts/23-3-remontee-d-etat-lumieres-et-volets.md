# Story 23.3 : Remontée d'état des lumières et volets

Status: draft

> Brouillon. Relecture ClaudeBox obligatoire avant `ready-for-dev`.

## Story

En tant qu'utilisateur HA, je veux voir l'état réel des lumières et la position des volets, afin d'éviter les états optimistes ou absents avant la bêta Market.

## Critères d'acceptation proposés

1. La vague streaming inclut `LIGHT_STATE`/luminosité et `FLAP_STATE`/position sans régression sensor, binary_sensor, switch.
2. Les payloads MQTT publient états compatibles; action et retour convergent sans boucle ni état périmé.
3. Tests unitaires/intégration/parité: changement d'état, luminosité, position, commandes absentes et golden.
4. Preuve 23.1: lumière variable et volet positionnable, inventaire MQTT/HA avant-après.
5. README et `docs/fr_FR/index.md` « Limites » distinguent couverture et limites restantes.
6. Une lumière ou un volet sans commande d'état Jeedom reste optimiste; la discovery n'envoie `optimistic: false` que lorsqu'un état réel existe, et cette règle figure dans « Limites ».

## Tâches proposées

- [ ] **Prérequis :** 23.1 fournit lumière variable et volet positionnable synthétiques; CC-48 s'applique aux fixtures, preuves et PR.
- [ ] Revalider `_STREAMED_TYPES`, publishers et types génériques actuels.
- [ ] Définir contrat état/brightness/position et dégradations.
- [ ] Implémenter listener, routage, publication et tests/parité; prouver sur 23.1.
- [ ] Mettre à jour Limites; ne pas ouvrir climate/alarm.

---

# Cadrage documentaire (revalidation du code de `main`, 2026-10-12)

> **Nature.** Préparation documentaire en lecture seule du code de `main` (`78cf903`). Aucun code, test, fixture, accès VM/Jeedom/HA ni donnée réelle (CC-48 : identifiants numériques et noms synthétiques seulement). La story reste `draft` : ce cadrage prépare la relecture ClaudeBox, il ne la remplace pas. Rien ici ne touche A1, A2, A3 ni 22.2, qui restent prioritaires.
> **Références de lignes** : état de `main` à `78cf903` ; à revérifier au passage en `ready-for-dev`.

## 1. État exact du streaming runtime (revalidation)

| Élément | Constat sur `main` | Source |
|---|---|---|
| Types streamés | `_STREAMED_TYPES = ("sensor", "binary_sensor") + ("switch",)`. `light` et `cover` n'y sont **pas**. | `sync/state.py:36` |
| Clés de lecture d'état | `_READBACK_KEYS` connaît déjà `light → LIGHT_STATE` et `cover → FLAP_STATE, FLAP_BSO_STATE` (préparées, inutilisées faute d'être dans `_STREAMED_TYPES`). **Aucune clé pour la luminosité (`LIGHT_BRIGHTNESS`) ni la position.** | `sync/state.py:44` |
| Portée côté commande | `streams_actionable_type()` ne renvoie vrai que pour `switch` ; `is_active` vaut `bool(_VAGUE2_ACTIONABLE)`. | `sync/state.py:76`, `:86` |
| Traduction de valeur | `_ONOFF_TYPES = ("binary_sensor", "switch")` → `ON`/`OFF` (`_BINARY_TRUE = {1,true,on,open,opened}`) ; sensor → valeur brute. Aucune branche `light`/`cover`. | `sync/state.py:51`, `:463` |
| Cible d'état | `_resolve_state_target` / `list_state_targets` / `publish_initial_states` itèrent `_iter_streamed_candidates` (filtre `_STREAMED_TYPES`) ; **une commande Jeedom ↔ un seul `state_topic`** (clé `(eq_id, cmd_id)` dédupliquée). | `sync/state.py:148`, `:340`, `:392` |
| Listeners PHP | `syncStateListeners()` crée un listener par cible renvoyée par `GET /system/state_listeners` (source autoritative = démon) ; `stateListener()` relaie `(eq_id, cmd_id, value)` vers `POST /action/state_update`. **Aucune modification PHP nécessaire** tant que `list_state_targets()` inclut les nouvelles cibles. | `core/class/jeedom2ha.class.php:402`, `:462` ; `http_server.py:3742`, `:4544` |
| Publisher light | `state_topic = jeedom2ha/{eq}/state`, `command_topic = …/set`, `payload_on/off = ON/OFF` ; si `has_brightness` : `brightness_state_topic = …/brightness`, `brightness_command_topic = …/brightness/set`, `brightness_scale = 100`, `supported_color_modes = ["brightness"]`. | `discovery/publisher.py:454` |
| Publisher cover | `state_topic = …/state`, `state_open/closed = open/closed`, `payload_open/close = OPEN/CLOSE` ; si `has_position` : `position_topic = …/position`, `set_position_topic = …/position/set`, `position_open = 100`, `position_closed = 0`. | `discovery/publisher.py:490` |
| `optimistic` en discovery | **Le mot n'apparaît dans aucun payload de discovery** (light, cover, switch). Light et cover déclarent un `state_topic` : HA applique donc son défaut (non optimiste) et attend un état qu'aucun flux réel n'alimente aujourd'hui. | `grep optimistic resources/daemon/discovery` → aucun résultat |
| Optimiste côté démon | `CommandSynchronizer` publie l'état « optimiste » sur le `state_topic` (retain=False) après un ordre `light`/`switch` **sans** état fiable (`optimistic_controlled`) ; pour `cover` sans état fiable la politique est `stateless` (rien n'est publié). Avec état fiable : `real_state_confirmation` (aucune publication optimiste). | `sync/command.py:385`, `:403`, `:479` |
| Synchronisation à tenir | `CommandSynchronizer._has_reliable_state` duplique la liste des clés d'état (`LIGHT_STATE`, `ENERGY_STATE`, `SWITCH_STATE`, `PRESENCE`, `FLAP_STATE`, `FLAP_BSO_STATE`) et le commentaire de `state.py:39` impose qu'elle reste alignée avec `_READBACK_KEYS`. | `sync/command.py:403`, `sync/state.py:39` |
| Canaux de commande entrants | `set` (light/switch : ON/OFF ; cover : OPEN/CLOSE/STOP), `brightness` → `LIGHT_SLIDER`, `position` → `FLAP_SLIDER`, valeur 0-100 entière. | `sync/command.py:338`, `:355` |
| Types génériques actuels | `LIGHT_STATE`, `LIGHT_ON/OFF`, `LIGHT_BRIGHTNESS` (info numérique), `LIGHT_SLIDER` (action) ; `FLAP_STATE`, `FLAP_UP/DOWN/STOP`, `FLAP_SLIDER`, `FLAP_BSO_*`. Position = slider + `FLAP_STATE` numérique (« sure ») ou slider sans état numérique (« probable »). | `mapping/light.py`, `mapping/cover.py:365` |

**Conséquence.** Aujourd'hui, une lumière ou un volet n'a **aucun** flux d'état réel : les lumières retombent sur l'état optimiste, les volets sur `stateless` (ni état ni position visibles). C'est exactement l'écart que la story ferme.

## 2. Contrat proposé

Principe directeur, hérité des vagues 1 et 2 : le démon est autoritatif (`state ⊆ discovery`) ; aucune reconstruction de topic à la main ; aucune valeur inventée ; une valeur vide ou illisible ne publie rien.

### 2.1 Topics (inchangés)

Aucun nouveau topic : on alimente ceux que la discovery déclare déjà.

| Entité | Topic | Alimenté par | Payload | Retain |
|---|---|---|---|---|
| light | `jeedom2ha/{eq}/state` | `LIGHT_STATE` (info) | `ON` / `OFF` | oui, QoS 1 |
| light variable | `jeedom2ha/{eq}/brightness` | `LIGHT_BRIGHTNESS` (info numérique) | entier 0–100 (échelle `brightness_scale = 100`) | oui, QoS 1 |
| cover | `jeedom2ha/{eq}/state` | `FLAP_STATE` / `FLAP_BSO_STATE` | `open` / `closed` | oui, QoS 1 |
| cover positionnable | `jeedom2ha/{eq}/position` | `FLAP_STATE` numérique | entier 0–100 (`position_open = 100`, `position_closed = 0`) | oui, QoS 1 |

Les topics de commande (`…/set`, `…/brightness/set`, `…/position/set`) ne changent pas.

### 2.2 Règles de traduction

- **light / état** : même table que switch (`_BINARY_TRUE`) → `ON`/`OFF`.
- **light / luminosité** : valeur numérique bornée à [0, 100], entière (arrondi explicite, documenté) ; valeur non numérique ou hors bornes → rien publié (cohérent avec `_normalize_slider_payload` côté commande). Une luminosité `0` n'impose pas `OFF` : l'état ON/OFF vient de `LIGHT_STATE` quand il existe.
- **cover / position** : valeur numérique bornée [0, 100] sur `…/position`. **Inversion** (certains plugins Jeedom inversent 0/100) : hors périmètre de 23.3, signalée comme limite (voir §6, Q2).
- **cover / état** : `open`/`closed` dérivé de l'état binaire si `FLAP_STATE` est binaire ; si `FLAP_STATE` est numérique, `closed` si position = 0, `open` sinon (état intermédiaire = `open`, `opening`/`closing`/`stopped` non gérés).
- **Plusieurs topics par commande.** Une même commande (`FLAP_STATE` numérique) alimente `…/state` **et** `…/position`. Le contrat impose donc qu'une cible d'état puisse produire **plusieurs publications** ; la clé de déduplication de `list_state_targets()` reste `(eq_id, cmd_id)` pour les listeners PHP (un listener par commande), mais `handle_state_message` publie sur tous les topics rattachés à la commande.
- **Plusieurs commandes par entité (cas inverse).** Une lumière variable normale porte `LIGHT_STATE` **et** `LIGHT_BRIGHTNESS` (deux commandes, deux topics). Aujourd'hui `_candidate_cmd_id()` ne renvoie que la première clé trouvée et `_iter_streamed_candidates()` ne produit qu'un candidat par mapping : seule `LIGHT_STATE` aurait un listener et un état initial, la luminosité ne serait jamais publiée. Le contrat impose donc d'énumérer, pour une même entité, **tous les couples (commande de lecture → topic)** : `LIGHT_STATE → state`, `LIGHT_BRIGHTNESS → brightness`, `FLAP_STATE`/`FLAP_BSO_STATE → state` (+ `position` si numérique). `list_state_targets()` renvoie un listener par commande distincte ; `_resolve_state_target`, `publish_initial_states` et `publish_click_states` parcourent la même énumération. Tests dédiés : lumière avec les deux commandes (deux listeners, deux états initiaux), avec une seule des deux, et cas où les deux clés pointent la même commande.

### 2.3 Élargissement du périmètre streamé

Sont ajoutés à `_STREAMED_TYPES` : `light` et `cover`. Les trois points suivants doivent bouger **ensemble** (sinon régression : optimiste supprimé sans état réel, ou l'inverse) :

1. `_STREAMED_TYPES` / `_VAGUE2_ACTIONABLE`-équivalent + `streams_actionable_type`.
2. `_READBACK_KEYS` : ajout des clés luminosité/position ; `_candidate_cmd_id` / `_candidate_current_value` / `publish_initial_states` / `publish_click_states` / `list_state_targets` doivent les résoudre.
3. `CommandSynchronizer._has_reliable_state` : même liste de clés, avec la règle de §3. **La fiabilité s'évalue par canal, pas globalement.** Le prédicat qui décide de supprimer l'optimiste **ON/OFF** reste limité aux clés ON/OFF (`LIGHT_STATE`, `ENERGY_STATE`, `SWITCH_STATE`, `PRESENCE`, `FLAP_STATE`, `FLAP_BSO_STATE`) : `LIGHT_BRIGHTNESS` seule ne rend **pas** l'ON/OFF fiable (sinon une lumière avec luminosité mais sans `LIGHT_STATE` passerait en `real_state_confirmation` sans qu'aucun retour ON/OFF puisse arriver, contre l'AC6 et Q4). La luminosité et la position ont leur propre prédicat de fiabilité (commande `info` présente), utilisé pour `optimistic` du canal luminosité/position en discovery. Le test de dérive de §5 compare donc `_READBACK_KEYS` ↔ prédicats **par canal**.

### 2.4 Convergence action ↔ retour (pas de boucle, pas d'état périmé)

- Chaîne : HA publie sur `…/set` → démon exécute la commande Jeedom → Jeedom change la valeur de la commande info → listener PHP → `POST /action/state_update` → publication sur le `state_topic`. Le démon **ne s'abonne pas** à ses propres topics d'état : pas de boucle possible.
- Avec état fiable : politique `real_state_confirmation`, **aucune** publication optimiste ; l'état affiché est celui de Jeedom (donc jamais « en avance » sur la réalité).
- Sans état fiable : voir §3 ; l'optimiste existant (light) reste la seule source, jamais mélangé à un état réel.
- État périmé : la publication retenue (retain=True) est celle de la dernière valeur reçue ; l'état initial à la (re)publication reprend `current_value` (`publish_initial_states`) et l'arbitrage 19.5 (valeur d'événement plus récente que celle du clic) s'applique tel quel à light et cover.

## 3. Règle `optimistic` (AC6) et dégradations

Règle : **`optimistic: false` est déclaré uniquement si un état réel est effectivement streamé**, c'est-à-dire si la commande d'état existe, est de type `info`, et si l'entité est dans le périmètre streamé. Sinon la discovery ne promet pas d'état réel.

| Cas | Discovery | Comportement démon | Visible dans HA |
|---|---|---|---|
| Lumière avec `LIGHT_STATE` (info) | `optimistic: false` + `state_topic` | `real_state_confirmation`, pas d'optimiste | état réel |
| Lumière **sans** commande d'état | pas de `state_topic` (HA applique `optimistic` = vrai) — ou `optimistic: true` explicite, voir Q1 | `optimistic_controlled` conservé | état supposé, assumé |
| Lumière variable avec état mais **sans** `LIGHT_BRIGHTNESS` | `brightness_state_topic` retiré ou `optimistic` côté luminosité, voir Q1 | luminosité non remontée ; ON/OFF réel | ON/OFF réel, curseur supposé |
| Volet avec `FLAP_STATE` (info) | `optimistic: false` + `state_topic` (+ `position_topic` si numérique) | `real_state_confirmation` | état réel (+ position) |
| Volet **sans** commande d'état | pas de `state_topic`/`position_topic`, `optimistic: true` | `stateless` → à remplacer par un optimiste cover explicite **ou** conservation de `stateless` (Q1) | état supposé ou inconnu, assumé |
| Commande d'état présente mais valeur absente/illisible | inchangé | rien publié, dernier état retenu conservé | dernier état connu |
| Commande d'état non `info` | traitée comme absente | idem « sans commande d'état » | idem |

**Transition état réel → sans commande d'état (retained).** Les états réels sont publiés `retain=True`, les optimistes `retain=False` : si une lumière ou un volet perd sa commande de lecture (retrait de la commande, changement de type générique) après avoir publié un état réel, ce dernier reste au broker et serait relu par HA après reconnexion ou redémarrage, en plus du chemin optimiste — ce qui contredit « jamais mélangé ». Le contrat impose, lors d'une (re)publication où l'entité n'a plus de lecture fiable, d'**effacer les retained devenus invalides** (publication vide retain sur `state`, `brightness`, `position` concernés), avec le même garde-fou « uniquement `jeedom2ha/…` » que les autres purges. Tests : transition réel → sans lecture (retained effacés), sans lecture → réel (état initial publié), absence de purge sur une entité qui garde sa lecture.

La règle et ces cas figureront dans « Limites » (README et `docs/fr_FR/index.md`) en langage utilisateur.

## 4. Non-régression sensor / binary_sensor / switch

- `_VAGUE1_TYPES` et `("switch",)` inchangés ; mêmes clés (`ENERGY_STATE`, `SWITCH_STATE`, `PRESENCE`) ; mêmes traductions (`ON`/`OFF`, brut pour sensor).
- Les secondaires `sensor` command-scoped d'une lumière avec compagnons de conso (story 11.4) gardent leur topic `jeedom2ha/{eq}/{cmd}/state` : le flux light/cover ne doit jamais s'écrire dessus.
- Le switch conserve son optimiste si `on_off_only` (pas de commande d'état) ; la présence conserve son comportement (story 10.7).
- Les listeners existants ne changent pas de forme : `syncStateListeners` reste tout-ou-rien (19.5) ; les nouvelles cibles s'y ajoutent.
- Le périmètre publié (discovery, décisions, `published_scope`) ne change pas ; seule la discovery light/cover gagne `optimistic` conditionnel.

## 5. Plan de tests et de parité (à écrire à l'implémentation)

**Unitaires** (`resources/daemon/tests/unit/`, sur le modèle de `test_story_12_1_state_streaming.py` et `test_story_12_2_switch_state_streaming.py`) :
- light : valeur ON/OFF → `ON`/`OFF` ; luminosité 0, 1, 50, 100 ; hors bornes, texte, `None` → rien publié.
- cover : position 0, 50, 100 ; binaire ; numérique vers `state` + `position` (deux publications) ; hors bornes/illisible.
- `list_state_targets` : inclut light/cover publiés, exclut non publiés ; une commande partagée n'apparaît qu'une fois.
- Commandes absentes : light sans `LIGHT_STATE`, light variable sans `LIGHT_BRIGHTNESS`, cover sans `FLAP_STATE` → pas de cible, optimiste/stateless conservé, `optimistic` correct en discovery.
- Alignement `_READBACK_KEYS` ↔ `_has_reliable_state` (test qui compare les deux listes pour éviter la dérive).
- Régression : tous les tests 12.1, 12.2, 10.7, 11.4, 14.1 inchangés et verts ; `test_command_sync_light_keeps_optimistic_path` / `…cover…` **mis à jour** (leur raison d'être change avec le périmètre).

**Discovery** : snapshots des payloads light/cover (avec/sans état, avec/sans luminosité/position) ; le corpus d'or existant (`resources/daemon/tests/fixtures/golden_corpus`, `test_story_19_0_parity_golden_corpus.py`) ne doit bouger que sur les champs `optimistic` attendus, diff relu à la main.

**Intégration** : `/action/state_update` → publication pour light/cover ; `/system/state_listeners` inclut les nouvelles cibles ; enchaînement commande → état réel sans publication optimiste.

**PHP** : aucun changement attendu ; les tests `tests/unit/test_story_19_5_php_relay.php` doivent rester verts (pas de modification de `core/`).

**Parité** (outil 19.1 `scripts/parity-snapshot.sh` / `tools/parity_snapshot.py`) : relevé avant/après sur l'environnement 23.1 ; seuls écarts autorisés = champs `optimistic` des discovery light/cover concernés + nouveaux topics d'état retenus + nouveaux écouteurs ; aucun écart sur sensor/binary_sensor/switch (topics discovery, état, écouteurs).
**Limite de l'outil actuel (à traiter dans l'implémentation, vérifiée sur `main`).** Le script ne souscrit qu'à `jeedom2ha/+/+/state` (`scripts/parity-snapshot.sh:74-75`), alors que les topics de 23.3 sont `jeedom2ha/{eq}/state`, `jeedom2ha/{eq}/brightness` et `jeedom2ha/{eq}/position` ; et `diff_snapshots()` compare les décisions, les topics discovery et les écouteurs, **pas** `state_topics`. Sans extension, la parité ne peut ni inventorier ni différencier les états introduits par 23.3. L'implémentation doit soit étendre l'outil (souscription `jeedom2ha/#` filtrée sur `state|brightness|position`, comparaison de `state_topics` dans le diff, lecture seule conservée), soit prévoir un relevé MQTT séparé, décidé avant la preuve (Q6). Les valeurs retenues relevées restent des identifiants/valeurs synthétiques (CC-48).

## 6. Preuve prévue sur l'environnement 23.1

Prérequis : VM 122, Mosquitto local et HA de test fournis par 23.1 (équipements synthétiques : lumière on/off, **lumière variable**, **volet positionnable**) ; déploiement et accès par les mécanismes de 23.1 (humain/clawcode), jamais depuis une session cloud.

1. Inventaire MQTT retenu et registre HA **avant** (`parity-snapshot.sh capture --label before`).
2. Déploiement du SHA exact par l'humain.
3. Inventaire **après** (`--label after`) + `diff` : écarts limités à ceux annoncés en §5.
4. Scénarios à observer côté HA : allumer/éteindre la lumière variable ; régler la luminosité (25/75) ; ouvrir/fermer/positionner le volet (0/50/100) ; modifier la valeur **dans Jeedom** et constater la remontée côté HA ; lumière et volet synthétiques **sans** commande d'état (à ajouter à 23.1 si absents) pour prouver la dégradation optimiste/stateless.
5. Artefact `23-3-preuve-terrain-<date>.md` : identifiants numériques seulement, aucun nom réel, IP ni secret (CC-48, contrôle par empreintes).

## 7. Questions ouvertes à trancher avant `ready-for-dev`

- **Q1 — forme de la dégradation en discovery.** Pour une entité sans état réel : (a) retirer `state_topic` (HA bascule en optimiste) ou (b) garder `state_topic` et envoyer `optimistic: true` ? Le code actuel publie l'optimiste du démon sur `state_topic`, ce qui plaide pour (b) ; (a) est plus simple côté HA mais change la structure du payload. Pour le volet sans état : conserver `stateless` ou publier un optimiste ?
- **Q2 — sens de la position.** Certains plugins Jeedom inversent 0/100 pour `FLAP_STATE`. Le contrat ci-dessus n'inverse pas ; faut-il l'assumer comme limite documentée ?
- **Q3 — état `open`/`closed` d'un volet à position intermédiaire.** `open` proposé ; `opening`/`closing`/`stopped` hors périmètre.
- **Q4 — luminosité sans `LIGHT_STATE`.** Déduire ON/OFF de la luminosité (>0) ou rester optimiste ? Proposition : rester optimiste (aucune valeur inventée).
- **Q5 — publication multiple par commande.** Confirmer que l'extension de `handle_state_message` (plusieurs topics par `(eq_id, cmd_id)`) est préférée à une seconde commande dédiée.

- **Q6 — outil de parité.** Étendre `parity-snapshot.sh` / `diff_snapshots()` aux topics `state`, `brightness`, `position` (changement d'outil, donc de code, à porter par l'implémentation) ou relevé MQTT séparé pour la preuve 23.1 ?
- **Q7 — purge des retained.** Confirmer l'effacement des retained d'état réel quand l'entité perd sa lecture (§3), et à quel moment (republication, rescan).

## Décisions ClaudeBox, 12/10 15:40

- **Q1 — retenu (b).** Une lumière sans état conserve `state_topic` et reçoit `optimistic: true` explicite. Un volet sans état reçoit aussi `optimistic: true` en discovery; la politique démon `stateless` est conservée.
- **Q2 — retenu.** Aucune inversion 0/100 : cette limite reste documentée.
- **Q3 — retenu.** Une position intermédiaire de volet publie l'état `open`.
- **Q4 — retenu.** Une luminosité sans `LIGHT_STATE` reste optimiste; aucune valeur ON/OFF n'est inventée.
- **Q5 — retenu.** `handle_state_message` publie plusieurs topics pour un même `(eq_id, cmd_id)` lorsque le contrat le requiert.
- **Q6 — retenu.** L'implémentation étend l'outil de parité : souscription lecture seule à `jeedom2ha/#`, filtrée sur `state|brightness|position`, et comparaison de `state_topics` dans le diff.
- **Q7 — retenu.** Les retained invalides sont purgés à la republication et au rescan, avec garde-fou strict sur le préfixe `jeedom2ha/…` uniquement.

## 8. Hors périmètre (rappel)

`climate`, `alarm_control_panel`, `button`, couleur RGB (`LIGHT_COLOR`), état `opening`/`closing`, inversion de position, A1/A2/A3, 22.2 et tout changement de `core/` PHP. Cadrage documentaire uniquement : aucune implémentation dans cette PR.
