# Story 24.7 : Portail et garage : `cover`

Status: review

> **Brouillon de cadrage (2026-10-12), `draft` jusqu'à son `create-story`, après la baseline.** Rédigé par une session cloud déléguée, documentaire. **Change la production** (des entités `button` ou `binary_sensor` deviennent un `cover`). Ne rouvre pas `PRODUCT_SCOPE` (`cover` y est déjà). Décision attendue d'Alexandre : **Q10** (remplacement d'entités existantes, option C pour un `cover` optimiste) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
>
> **R1 (ClaudeBox, 12/10) intégrée** : types génériques des deux équipements concernés établis (section suivante) ; le cas du garage est la vérification de l'AC2.

## Story

En tant qu'utilisateur dont un portail et un garage sont exposés à HomeKit,
je veux les retrouver dans Home Assistant comme des ouvrants (ouvrir, fermer, état), et non comme de simples boutons,
afin de les consulter et de les piloter par Assist.

**Parcours : démon (mapper, commande, état).**

## Dépendances et décisions

- Dépend de **24.4**. Une seule story de type en cours à la fois.
- **Dépend de 23.3 pour l'état d'un `cover`** : cette story ajoute `BARRIER_STATE` / `GARAGE_STATE` comme clé de relecture du `cover` ; elle ne réimplémente pas le streaming et ne touche pas aux lignes `light`/`cover` de `sync/state.py`. Q10 C (livrer un `cover` optimiste pour ne pas attendre) est **écartée** par Alexandre : la story démarre après la fusion de 23.3 (règle de 23.3 : `optimistic: false` seulement avec un état réel).
- **Q10 A** (tranchée) : remplacement, inventaire des références.

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q10 A** : remplacement, une seule voie par équipement ; inventaire des références avant/après. **L'option C (`cover` optimiste pour ne pas attendre 23.3) est écartée** : cette story **attend 23.3** pour l'état d'un `cover`.
- **Q9 A** : sans effet ici (le portail et le garage ne sont pas dans l'epic 18).

## Établi par ClaudeBox le 12/10 (mesure du 10/10, types génériques par équipement)

- **Portail** : `GB_OPEN`, `GB_CLOSE`, `GB_TOGGLE`, `BARRIER_STATE`. Ouvrir et fermer existent : branche directe de l'AC1, bascule inutile.
- **Garage** : `GB_TOGGLE`, `GARAGE_STATE`. **Bascule seule + état** : c'est exactement le cas que l'AC2 doit trancher (un `cover` n'est publié que si la bascule est pilotée par un état binaire fiable). Ni `GB_OPEN` ni `GB_CLOSE`.
- Reste à établir (ClaudeBox, Task 0) : la polarité de `BARRIER_STATE` et `GARAGE_STATE`, et le chemin actuel de chacun (`binary_sensor` ou `button`).

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | `CoverMapper` ne reconnaît que les types `FLAP_*`. Aucun `GB_*` n'apparaît dans le code du démon. | `mapping/cover.py:30-34` |
| F2 | Les types du core pour ce cas : `GB_OPEN`, `GB_CLOSE`, `GB_TOGGLE` (actions), `BARRIER_STATE`, `GARAGE_STATE` (infos binaires). | `ha-projection-reference.md:532-540` |
| F3 | `BARRIER_STATE` et `GARAGE_STATE` donnent aujourd'hui un `binary_sensor` de classe `garage_door` ; une action `other` typée donne un `button`. Le chemin réel de chaque équipement mesuré dépend de ses commandes (D5). | `mapping/binary_sensor.py:41-42` ; `mapping/button.py:12-35` |
| F4 | Ordre de la chaîne : `CoverMapper` passe avant `BinarySensorMapper` et `ButtonMapper` : un `cover` reconnu consommerait les commandes sans doublon. | `mapping/registry.py:24-35` |
| F5 | `_NON_COVER_KEYWORDS` et `_NON_SWITCH_KEYWORDS` filtrent par mots du nom d'équipement (dont « portail » et « garage » côté switch) : heuristique fragile à ne pas étendre. | `mapping/cover.py:56-62` ; `mapping/switch.py:67-73` |
| F6 | Le `cover` actuel traduit `OPEN`/`CLOSE`/`STOP` vers `FLAP_UP`/`FLAP_DOWN`/`FLAP_STOP` ; `GB_*` n'y est pas. | `sync/command.py:283-330` |
| F7 | Le `cover` est optimiste aujourd'hui ; son état réel relève de 23.3. | `sync/state.py:33-48` ; `sync/command.py:403-430` |

## Task 0 faite par ClaudeBox le 2026-11-01 (export de production `57f961b` + lecture des commandes dans Jeedom)

| eq | plugin | exposé (effectif) | aujourd'hui dans HA | commandes typées |
|---|---|---|---|---|
| **496** (portail) | `virtual` | oui | `button` `jeedom2ha_eq_496` (GB_TOGGLE) | `GB_OPEN` 4545, `GB_CLOSE` 4546, `GB_TOGGLE` 4542, `BARRIER_STATE` 4543 (**info numérique**) |
| **199** (garage) | `virtual` | oui | `button` `jeedom2ha_eq_199` (GB_TOGGLE) | `GB_TOGGLE` 1624, `GARAGE_STATE` 1626 (**info numérique**) |
| 455 | `zwavejs` | non | rien (pièce exclue) | `BARRIER_STATE` binaire, 2× `GB_TOGGLE` : **hors périmètre** (équipement physique, non exposé ; règle d'Alexandre du 01/10 : pas de publication jeedom2ha de ce que HA atteint par sa propre intégration) |

- **Les états ne sont pas binaires** : `BARRIER_STATE` et `GARAGE_STATE` sont des infos **numériques** à la convention « barrière » de Z-Wave (celle du plugin Homebridge de Jeedom) : `0` fermé, `252` en fermeture, `253` arrêté, `254` en ouverture, `255` ouvert. Relevés : portail `255` (HA montre aussi un capteur d'ouverture « portail » à `on`), garage `0`. `GB_OPEN` / `GB_CLOSE` du portail écrivent respectivement `254` / `252` dans son état (`updateCmdId`).
- `GB_TOGGLE` de chaque virtuel écrit `1` dans une info `SCENARIO` : l'ordre réel est porté par un scénario Jeedom. jeedom2ha appelle la commande Jeedom, comme HomeKit, sans connaître le scénario.
- Aujourd'hui, les états numériques ne sont **pas publiés** (le `binary_sensor` `garage_door` de `mapping/binary_sensor.py:41-42` ne vaut que pour une info binaire) ; seul le `GB_TOGGLE` sort, en `button`.

## Décisions de ClaudeBox pour le `ready-for-dev` (2026-11-01, go d'Alexandre 22:11)

- **D1. État** : une info `BARRIER_STATE` / `GARAGE_STATE` **numérique** se traduit en état de `cover` par la table `0→closed`, `252→closing`, `253→stopped`, `254→opening`, `255→open` ; toute autre valeur → aucun état publié (jamais d'invention). Une info **binaire** reste traitée comme aujourd'hui (`binary_sensor` `garage_door`), hors de cette story.
- **D2. Classe d'appareil** : `gate` pour un équipement dont l'état est `BARRIER_STATE` (ou, sans état, porteur de `GB_OPEN`/`GB_CLOSE`), `garage` pour `GARAGE_STATE`. Vérifier que HA 2026.9.4 accepte ces deux valeurs de `device_class` pour `cover`.
- **D3. Ordres** : avec `GB_OPEN` **et** `GB_CLOSE`, `open`/`close` les appellent directement, `GB_TOGGLE` n'est pas utilisé, pas de `stop` (aucun `GB_STOP` sur la box). Avec `GB_TOGGLE` seul : `open` n'envoie la bascule que si le dernier état connu vaut `0` (fermé) ou `253` (arrêté) ; `close` seulement s'il vaut `255` (ouvert) ou `253` ; état inconnu ou mouvement en cours (`252`, `254`) : **aucun ordre**, refus journalisé. Jamais de bascule à l'aveugle (AC2).
- **D4. Éligibilité** (AC2) : `cover` seulement si (`GB_OPEN` et `GB_CLOSE`) ou (`GB_TOGGLE` et un état numérique D1). Sinon comportement actuel inchangé.
- **D5. `optimistic: false`** quand un état D1 existe (règle de 23.3) ; pas de `cover` optimiste.
- **D6. Remplacement** (Q10 A) : la découverte `button` de `jeedom2ha_eq_496` et `jeedom2ha_eq_199` est vidée (retenu vide) quand le `cover` est publié ; l'inventaire des références HA est relevé avec Alexandre avant le déploiement.
- **D7. Preuve terrain** : ouverture puis fermeture **réelles** du portail et du garage **en présence d'Alexandre** (organe de sécurité) ; pas d'équipement de test équivalent sur la box.

## Critères d'acceptation (figés sur Q10 A)

- **AC1.** Un équipement qui porte `GB_OPEN` et `GB_CLOSE` (ou `GB_TOGGLE`) est projeté en `cover` de classe portail ou garage (valeurs exactes lues dans la documentation de HA, D4), avec ses commandes d'ouverture et de fermeture traduites par `sync/command.py`.
- **AC1 bis.** Cas de référence : le portail (`GB_OPEN`, `GB_CLOSE`, `GB_TOGGLE`, `BARRIER_STATE`) donne un `cover` avec ordres d'ouverture et de fermeture directs, `GB_TOGGLE` non utilisé pour l'ouverture ; le garage (`GB_TOGGLE`, `GARAGE_STATE`) donne un `cover` dont l'ordre d'ouverture envoie la bascule **seulement si** l'état dit fermé, et inversement, jamais en aveugle.
- **AC2.** **Aucun état menteur.** Un `cover` n'est publié que s'il a soit `GB_OPEN` et `GB_CLOSE`, soit `GB_TOGGLE` **et** une information d'état binaire fiable (`BARRIER_STATE` / `GARAGE_STATE`) permettant de ne basculer que dans le bon sens. Sinon, l'équipement garde son comportement actuel avec une raison canonique explicite (impossibilité technique), jamais un `cover` à deux sens inventés.
- **AC3.** `BARRIER_STATE` / `GARAGE_STATE` consommés par le `cover` ne sont plus publiés en `binary_sensor` doublon ; les autres commandes de l'équipement gardent leur mapping.
- **AC4.** Le payload porte `default_entity_id = cover.<object_id>` (22-1) ; `unique_id` et `object_id` suivent les conventions.
- **AC5.** État : relecture par la mécanique de 23.3 (une entrée de relecture) ; la limite est écrite dans « Limites » (puce propre).
- **AC6.** Cycle de vie (Q10 A) : le passage `button`/`binary_sensor` → `cover` dépublie les anciennes entités et publie la nouvelle ; inventaire avant/après des identifiants concernés, `entity_id` anciens et nouveaux, références relevées par ClaudeBox.
- **AC7.** Aucun `FLAP_*` existant ne change : volets et stores strictement non régressés (golden, tests du `CoverMapper`, essai de mouvement sur un volet).
- **AC8.** Un override pe-epic-16 peut rediriger le portail vers `button` et inversement.
- **AC9.** `PRODUCT_SCOPE` inchangé ; golden et contrat 4D verts ; aucun nom réel dans le dépôt (CC-48) ; preuve terrain par ClaudeBox (export avant/après, ouverture et fermeture d'un équipement de test, jamais d'un vrai portail sans présence).

## Tâches proposées

- [x] **Task 0 — Gel du référentiel** (ClaudeBox, 01/11 : voir « Task 0 » et D1-D7) : matrice `GB_*` / `BARRIER_STATE` / `GARAGE_STATE` → `cover` (classes de HA 2026.9.4, charge utile d'ordre, topic d'état) ; liste, par ClaudeBox, des équipements concernés, de leurs commandes réelles et de leur chemin actuel (`binary_sensor` ou `button`).
- [x] **Task 1 — Mapper** : `CoverMapper` étendu (`_map_barrier`), partage `CoverCapabilities`.
- [x] **Task 2 — Commande** : traduction des ordres, logique de bascule fondée sur l'état (AC2).
- [x] **Task 3 — Publication** : classe d'appareil, `default_entity_id`.
- [x] **Task 4 — État** : après 23.3 (une entrée).
- [x] **Task 5 — Tests** : portail avec ouvrir/fermer, avec bascule + état, avec bascule seule (refus), non-régression des volets.
- [ ] **Task 6 — Gate, déploiement, preuve terrain (humain)** : à ClaudeBox et Alexandre (D7), non faite par la session cloud.
- [x] **Task 7 — documentation**.

## Garde-fous

- Un portail est un organe de sécurité : aucun essai sur un vrai portail sans présence de l'humain ; la preuve terrain se fait sur un équipement de test.
- Pas de nouvelle heuristique sur les noms d'équipement.
- Ne pas modifier le streaming des `light`/`cover` (23.3).
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Le chemin actuel de chaque équipement mesuré (D5) ; les classes d'appareil acceptées par HA 2026.9.4 ; la polarité de `BARRIER_STATE` / `GARAGE_STATE` (1 = ouvert ou fermé) ; la proportion d'équipements à bascule seule.

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q10 A (remplacement) ; option C écartée : la story attend 23.3.
- 2026-11-01 — Task 0 (ClaudeBox) : états numériques à la convention barrière ; décisions D1-D7 ; 23.3 `done` ; `ready-for-dev` (go d'Alexandre 22:11).
- 2026-11-01 — dev-story (session cloud déléguée) : Tasks 1 à 5 et 7 ; `review`. Task 6 (terrain) reste à ClaudeBox / Alexandre.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée).

### Implementation Notes

- **Mapper** (`mapping/cover.py`, `_map_barrier`) : appelé seulement si l'équipement n'a **aucun** `FLAP_*` ni type « anti-cover » ; le chemin `FLAP_*` est intact. Commandes lues : actions `GB_OPEN` / `GB_CLOSE` / `GB_TOGGLE`, infos `BARRIER_STATE` / `GARAGE_STATE`. Éligibilité D4 : (`GB_OPEN` et `GB_CLOSE`) ou (`GB_TOGGLE` et état **numérique**). Sinon `None` : la chaîne continue, comportement actuel inchangé (`button`, ou `binary_sensor` `garage_door` pour un état binaire), raison journalisée (`barrier_not_eligible`, état non numérique, doublon). Toutes les commandes `GB_*` et l'état sont consommés par le `cover` (pas de `button` ni de `binary_sensor` en double, AC3). `reason_code` : `cover_barrier_open_close` / `cover_barrier_toggle_state` ; `reason_details` : `barrier_mode` (`direct` / `toggle_on_state`), `cover_device_class` (`gate` / `garage`), `barrier_state`. Confiance `sure` avec état, `probable` sans état (ouvrir/fermer directs). Aucune heuristique sur les noms.
- **Classe d'appareil (D2)** : `garage` si l'état est `GARAGE_STATE`, `gate` pour `BARRIER_STATE` ou sans état. **Vérifié dans le code source de HA 2026.9.4** (tag `2026.9.4`, `homeassistant/components/cover/const.py` : `CoverDeviceClass.GARAGE = "garage"`, `GATE = "gate"`).
- **Publication** (`discovery/publisher.py`) : pour un `cover` barrière seulement, `device_class` gate/garage, `state_opening` / `state_closing` / `state_stopped` explicites, `payload_stop: null` (sans `GB_STOP` ; dans HA 2026.9.4 `mqtt/cover.py` accepte `None` et retire alors la fonction STOP, sinon le défaut est `"STOP"`). `default_entity_id = cover.jeedom2ha_<id>`, `unique_id` `jeedom2ha_eq_<id>`, `object_id` `jeedom2ha_<id>` (conventions inchangées). `optimistic: false` dès qu'un état numérique existe (D5, `has_reliable_channel`).
- **État (D1)** (`sync/readback.py`, `sync/state.py`) : une entrée ajoutée, sans toucher aux lignes light/cover de 23.3 : quand un `cover` n'a pas d'état `FLAP_*`, `readback_commands` prend une info `BARRIER_STATE` / `GARAGE_STATE` **numérique** ; `_translate_value` la traduit par la table `0→closed`, `252→closing`, `253→stopped`, `254→opening`, `255→open` (`barrier_state`) ; toute autre valeur (y compris décimale, hors table, vide) ne publie rien. L'écouteur PHP est inscrit automatiquement (`list_state_targets`).
- **Ordres (D3)** (`sync/command.py`, `_translate_barrier_command`) : avec `GB_OPEN` et `GB_CLOSE`, appel direct, `GB_TOGGLE` jamais utilisé. Avec `GB_TOGGLE` seul : `OPEN` seulement depuis `closed`/`stopped` (0/253), `CLOSE` seulement depuis `open`/`stopped` (255/253) ; sinon aucun ordre, refus journalisé en WARNING (`action=refuse_barrier_toggle`, `reason_code` `barrier_state_unknown` / `barrier_in_motion` / `barrier_already_open` / `barrier_already_closed`, avec l'état et la valeur brute), puis le rejet habituel `reject_command`. `STOP` refusé (`missing_action_command`). **Dernier état connu** : la dernière valeur reçue de Jeedom par `StateSynchronizer` (nouvel accesseur en lecture `last_event_value`, alimenté par chaque événement, publié ou non), à défaut la valeur de la topologie de la dernière synchronisation. Un refus n'est **jamais mis en attente** : un changement d'état ultérieur ne déclenche rien, HA doit redonner l'ordre. Politique de confirmation : `real_state_confirmation` (aucun état optimiste publié) quand l'état existe.
- **Cycle de vie (D6)** : aucun code nouveau. Le retypage `button` → `cover` est déjà traité par `_detect_lifecycle_changes` (`transport/http_server.py`), à chaud et au démarrage (cache disque) : la découverte `homeassistant/button/jeedom2ha_<id>/config` est vidée (retenu vide) avant la publication du `cover`, avec report en cas d'échec. Testé.
- **Override (AC8)** : un override « Type HA » `button` sur une commande de l'équipement redonne le `button` (projection valide, payload `button.jeedom2ha_<id>`) ; le retrait de l'override redonne le `cover`.
- **Garde 25.4 (AC31)** : diff de `resources/daemon/` en ajouts seuls (le `return None  # Not a cover` et l'import de `sync/command.py` sont conservés).
- `PRODUCT_SCOPE` inchangé ; golden inchangé (aucun `GB_*` dans le corpus).

### Points tranchés

1. **`GB_OPEN` + `GB_CLOSE` avec un état binaire** : pas de `cover` (D1 prime : une info binaire reste traitée comme aujourd'hui, hors story). Le `cover` ne consommerait pas l'état et la chaîne s'arrêtant au premier mapper, le `binary_sensor` existant disparaîtrait.
2. **`GB_OPEN` + `GB_CLOSE` sans état** : `cover` `gate` publié (D4), confiance `probable`, optimiste comme un volet sans état (règle de 23.3). Aucun équipement de la box dans ce cas (Task 0).
3. **Doublons** (ex. deux `GB_TOGGLE`, `BARRIER_STATE` et `GARAGE_STATE` ensemble) : pas de `cover`, comportement actuel.
4. **Course d'état** : si l'état change entre la lecture du dernier état connu et l'exécution de la bascule (actionnement par un autre moyen pas encore signalé par Jeedom), la bascule peut partir dans le mauvais sens : limite inhérente à toute bascule, documentée.
5. **253 « arrêté »** : HA 2026.9.4 affiche `stopped` comme « ouvert » (ou « fermé » si l'état précédent était fermé/en fermeture) ; les deux sens restent permis par la bascule (D3).
6. Constat hors périmètre : la commande d'un `button` d'équipement (`jeedom2ha/<id>/cmd`) n'est routée par `sync/command.py` que pour les scénarios ; un override vers `button` reproduit donc exactement le comportement actuel du bouton, sans plus.

### Tests

- `resources/daemon/tests/unit/test_story_24_7_portail_garage_cover.py` (83 cas, identifiants synthétiques 7001/7002) : portail `GB_OPEN`+`GB_CLOSE`+`GB_TOGGLE`+`BARRIER_STATE` numérique ; garage `GB_TOGGLE`+`GARAGE_STATE` numérique ; bascule seule sans état (reste `button`) ; état binaire (comportement inchangé, `binary_sensor` `garage_door`) ; formes ambiguës ; pas d'heuristique de nom ; `FLAP_*` + `GB_*` garde le chemin volet ; payloads de découverte (gate, garage, sans état, volet inchangé) ; table d'état et valeurs hors table ; écouteur et publication d'état, état initial ; ordres directs quel que soit l'état ; matrice complète de la bascule (0/252/253/254/255/inconnu/hors table) et refus journalisés ; dernier événement prioritaire sur la topologie ; refus non rejoué ; cohérence commande/état ; retypage `button` → `cover` à chaud et au démarrage ; override vers `button` et retour.
- `python -m pytest` : voir le rapport de PR. `flake8 resources/daemon tests` : 0. `node --test tests/unit/*.node.test.js` : voir le rapport de PR.

### File List

- `resources/daemon/mapping/cover.py` (modifié, ajouts seuls)
- `resources/daemon/discovery/publisher.py` (modifié, ajouts seuls)
- `resources/daemon/sync/readback.py` (modifié, ajouts seuls)
- `resources/daemon/sync/state.py` (modifié, ajouts seuls)
- `resources/daemon/sync/command.py` (modifié, ajouts seuls)
- `resources/daemon/tests/unit/test_story_24_7_portail_garage_cover.py` (nouveau)
- `docs/fr_FR/index.md` (modifié)
- `docs/fr_FR/changelog_beta.md` (modifié)
- `README.md` (modifié)
- `_bmad-output/implementation-artifacts/24-7-portail-et-garage-cover.md` (modifié)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié)
