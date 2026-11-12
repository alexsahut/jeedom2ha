# Story 24.9 : Serrure : `lock`

Status: review

> **Brouillon de cadrage (2026-10-12), `draft` jusqu'à son `create-story`, après la baseline.** Rédigé par une session cloud déléguée, documentaire. **Change la production, ouvre un composant** (`lock`, FR40/NFR10) et touche à la sécurité. Décisions attendues d'Alexandre : **Q9** et **Q10** de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
>
> **R1 (ClaudeBox, 12/10) intégrée** : types génériques de la serrure établis (section suivante).

## Story

En tant qu'utilisateur dont une serrure est exposée à HomeKit,
je veux la retrouver dans Home Assistant comme une serrure (verrouillée ou non, verrouiller, déverrouiller),
afin de la consulter et, si je l'ai voulu, de la piloter par Assist.

**Parcours : démon.** Recoupe la story 18.2 du backlog (Q9 A : absorbée par celle-ci).

## Dépendances et décisions

- Dépend de **24.4**. Une seule story de type en cours à la fois.
- **23.3** : même règle que 24.6 pour l'état.
- **Q9 A** et **Q10 A** (tranchées).

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q9 A** (version ajustée R1) : l'epic 24 absorbe 18-2 (`lock`).
- **Q10 A** : remplacement du `binary_sensor` `lock` existant, une seule voie ; inventaire des références avant/après.
- **Q1** : « exclu par plugin » conservé (pas de `voie_native`).

## Établi par ClaudeBox le 12/10 (mesure du 10/10)

- **Une serrure** porte `LOCK_OPEN`, `LOCK_CLOSE`, `LOCK_STATE` : état + deux ordres, donc l'AC3 est satisfaite sur le cas réel.
- Reste à établir (Task 0) : la polarité de `LOCK_STATE` ; le plugin d'origine (si c'est un plugin de la liste `excludedPlugins`, l'équipement est « exclu par plugin » et sort de cette story).

## Task 0 faite par ClaudeBox le 2026-11-12 (export de production + sources Homebridge, lecture seule)

**Équipements portant `LOCK_*`** (export de décision de production, 11/11) :

| eq | plugin | Commandes | Décision actuelle |
|---|---|---|---|
| 508 | virtual | 4626 `LOCK_CLOSE`, 4627 `LOCK_OPEN`, 4628 `LOCK_STATE` | `published` (`sure`), `homekit_exposed_effective: true` |
| 421 | plugin de véhicule | 3494 `LOCK_STATE`, 3518 `LOCK_CLOSE`, 3519 `LOCK_OPEN` | `not_published`, `excluded_plugin` (plugin exclu) → **hors story** |

**Polarité de `LOCK_STATE` (source : plugin Homebridge installé, `homebridge-jeedom/index.js`, caractéristique `LockCurrentState`)** :
- cas général : valeur vraie (`1`, `true`, `on`) = **verrouillé** (`SECURED`), valeur fausse = **déverrouillé** (`UNSECURED`) ;
- équipements `nuki` (et `jeelink` relayant un `nuki`) : `0` = verrouillé, `1` = déverrouillé, `2` = bloqué (`JAMMED`), autre = inconnu.
- Aucune déduction depuis un nom (garde-fou) : un équipement dont la polarité ne relève d'aucun de ces deux cas n'est pas publié en `lock`.

## Décisions techniques ClaudeBox (2026-11-12)

- **D1 — Polarité** : celle de Homebridge ci-dessus, pour garder la parité HomeKit ; `nuki` traité à part ; `JAMMED` publié comme état `jammed` ; valeur non reconnue → aucun état publié.
- **D2 — Publication** : `lock` seulement si `LOCK_STATE` + au moins une des deux actions (AC3). `payload_lock`/`payload_unlock` → actions `LOCK_CLOSE`/`LOCK_OPEN` ; `state_locked: LOCKED`, `state_unlocked: UNLOCKED`, `state_jammed: JAMMED` ; `optimistic: false` ; pas de `code`.
- **D3 — Remplacement (Q10 A)** : le `binary_sensor` `lock` et les boutons portant les commandes `LOCK_*` du même équipement sont remplacés explicitement par la `lock` (mécanisme de 24-8 : aucune réutilisation silencieuse d'un `unique_id`).
- **D4 — Sécurité (AC7)** : le plugin ne touche jamais l'exposition à Assist ; la documentation dit que déverrouiller par la voix est un choix de l'utilisateur dans HA.

## Décisions d'Alexandre (2026-11-12 à 07:51)

- **Q-L1 : OUI**, l'équipement 508 est publié en `lock` dans HA. Règle de projection : ce qui est dans l'app Maison (HomeKit) doit être dans HA.
- **Q-L2** : preuve terrain **réelle** (verrouiller puis déverrouiller) autorisée, **en présence d'Alexandre**.

## Fait établi (2026-11-12, relayé par ClaudeBox)

- L'équipement 508 est un **virtuel** dont les actions `LOCK_OPEN` / `LOCK_CLOSE` exécutent les commandes d'un autre plugin (un véhicule, piloté via un service en ligne). Son `LOCK_STATE` est un **calcul** qui vaut `1` quand l'état source vaut « sécurisé » (`SECURED`) : polarité du **cas général** (1 = verrouillé), aucun traitement particulier.

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | `LOCK_STATE`, `LOCK_OPEN`, `LOCK_CLOSE` sont des types du core ; `LOCK_STATE` est une info binaire. | `ha-projection-reference.md:531,536-537` |
| F2 | Aujourd'hui `LOCK_STATE` donne un `binary_sensor` de classe `lock` (lecture seule) ; `LOCK_*` sert de liste « anti » dans les mappers `switch`, `cover`, `light`. | `mapping/binary_sensor.py:40` ; `mapping/switch.py:52-54` ; `mapping/cover.py:43` ; `mapping/light.py:56` |
| F3 | `lock.mqtt` est documenté ; `lock` n'est ni dans le registre ni dans `PRODUCT_SCOPE`. | `ha-projection-reference.md` (composants) ; `validation/ha_component_registry.py:26-70` |
| F4 | Les commandes `LOCK_OPEN` / `LOCK_CLOSE` seraient aujourd'hui des `button` si rien ne les capte avant. | `mapping/button.py:12-35` |

## Critères d'acceptation proposés (à figer selon Q9 et Q10)

- **AC1.** Ouverture gouvernée de `lock` dans le même incrément : entrée de registre ; cas nominal et cas d'échec de `validate_projection()` ; `PRODUCT_SCOPE` mis à jour ; contrat 4D non régressé ; retrait de `LOCK_*` des listes « anti » seulement pour le nouveau mapper.
- **AC2.** **Polarité vérifiée, jamais supposée.** La correspondance valeur de `LOCK_STATE` ↔ verrouillé / déverrouillé est écrite, testée dans les deux sens, et lue dans la documentation des types Jeedom (Task 0) ; si la polarité n'est pas établie pour un équipement, il n'est **pas** publié en `lock` (raison canonique explicite).
- **AC3.** Une serrure n'est publiée en `lock` que si elle a un état fiable (`LOCK_STATE`) et au moins une commande d'action (`LOCK_OPEN` ou `LOCK_CLOSE`) ; sinon elle garde son comportement actuel (`binary_sensor` en lecture seule).
- **AC4.** Les ordres HA → Jeedom sont traduits par `sync/command.py` ; aucun ordre de déverrouillage n'est envoyé sans commande Jeedom `LOCK_OPEN` correspondante ; aucun état n'est affiché sans retour réel.
- **AC5.** Payload avec `default_entity_id = lock.<object_id>` (22-1) ; `unique_id`/`object_id` selon les conventions.
- **AC6.** Cycle de vie (Q10 A) : le `binary_sensor` `lock` existant est remplacé par le `lock` (dépublication, publication) ; inventaire des identifiants et des références avant/après.
- **AC7.** **Sécurité** : la story ne configure pas l'exposition à Assist (exigence 5) et le dit dans la documentation ; elle documente que commander le déverrouillage par la voix est un choix de l'utilisateur dans HA ; aucune valeur par défaut n'expose le déverrouillage.
- **AC8.** Golden et contrat 4D verts ; aucun nom réel (CC-48) ; preuve terrain par ClaudeBox sur une serrure de test ou, à défaut, en lecture seule de l'état.

## Tâches proposées

- [x] **Task 0 — Gel du référentiel pour `lock`** (ClaudeBox, 2026-11-12) : polarité de `LOCK_STATE`, sens de `LOCK_OPEN` / `LOCK_CLOSE`, champs de `lock.mqtt` (documentation officielle HA 2026.9.4, D4) ; liste, par ClaudeBox, des équipements concernés et de leurs commandes réelles.
- [x] **Task 1 à 7 (développement)** : registre, mapper, publication, commande, état (après 23.3), override, tests (dont polarité), **documentation** — session cloud déléguée, voir Dev Agent Record.
- [ ] **Gate, déploiement, preuve terrain (humain)** : ClaudeBox et Alexandre (Q-L2 : essai réel en sa présence).

## Garde-fous

- Une serrure est un organe de sécurité : aucun essai de déverrouillage sur une vraie porte sans l'humain.
- Pas de déduction de polarité depuis un nom.
- Le plugin ne modifie jamais l'exposition à Assist.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

La polarité réelle de `LOCK_STATE` sur les équipements mesurés ; les champs de `lock` dans HA 2026.9.4 ; la présence de commandes `LOCK_OPEN` / `LOCK_CLOSE` sur les équipements concernés.

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q9 A (absorbe 18-2), Q10 A ; Q1 « exclu par plugin » conservé.
- 2026-11-12 — Task 0 (ClaudeBox : eq 508 seul concerné, 421 exclu par plugin ; polarité Homebridge) ; D1-D4 ClaudeBox ; `ready-for-dev` pour le développement, déploiement soumis à Q-L1/Q-L2.
- 2026-11-12, 07:51 — **Décisions d'Alexandre** : Q-L1 oui (508 publié en `lock`, règle « ce qui est dans l'app Maison doit être dans HA ») ; Q-L2 preuve terrain réelle (verrouiller/déverrouiller) en sa présence. Fait établi : 508 est un virtuel relayant un autre plugin, `LOCK_STATE` calculé à 1 quand la source est sécurisée → polarité du cas général.
- 2026-11-12 — Développement (session cloud déléguée) : Tasks 1 à 7 hors terrain ; story en `review`.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée, sans accès à la box).

### Implementation Notes

- **Mapper** (`mapping/lock.py`, nouveau) : une serrure par équipement = **un** `LOCK_STATE` de type `info` et au moins une action `LOCK_CLOSE` (verrouiller) ou `LOCK_OPEN` (déverrouiller) de type `action` / sous-type `other` (un ordre de serrure ne porte pas de valeur). Refus (WARNING, projection d'avant gardée) : aucun état ou plusieurs états, plusieurs actions de même sens, action liée (« Valeur », `linked_value` de 24.8) à une autre commande que l'état, polarité non établie. État seul : rien ne change (AC3). Entité : `ha_unique_id` `jeedom2ha_eq_<eq>_cmd_<LOCK_STATE>`, `object_id`/`node_id` `jeedom2ha_<eq>_<LOCK_STATE>`, topics `jeedom2ha/<eq>/<LOCK_STATE>/state|set` (convention de 24.8), confiance `sure`, `reason_code` `lock_state_open_close`, `reason_details.lock_polarity`.
- **Polarité (D1, AC2)** : lue du **plugin** seulement (`lock_polarity`), jamais d'un nom : `nuki` → `0` verrouillé / `1` déverrouillé / `2` bloqué ; `jeelink` → **non établie** (Homebridge lit un `jeelink` selon l'équipement relayé, information que le plugin ne reçoit pas) → pas de `lock` ; tout autre plugin (dont `virtual`, cas de 508) → cas général : `1`/`true`/`on` (ou `1.0`) verrouillé, `0`/`false`/`off` (ou `0.0`) déverrouillé. `sync.readback.lock_state` : toute autre valeur → `None`, aucun état publié.
- **Ordre et remplacement (D3, Q10 A)** (`mapping/registry.py`, `_with_locks`) : la serrure passe par la même passe dédiée que la vanne, **avant** tous les mappers (donc avant le `binary_sensor` de classe `lock` et avant le bouton, dont l'appui sur `LOCK_*` est refusé par 24.12). La projection d'avant est calculée sur l'équipement complet ; ses entités qui utilisent une commande de la serrure (ou d'une vanne du même équipement) sont retirées (WARNING « remplacée par la serrure »), jamais re-projetées ; les autres sont gardées à l'identique. Le `unique_id` de la serrure est nouveau (`…_cmd_<LOCK_STATE>`, domaine `lock`) : aucun `unique_id` existant n'est réutilisé, testé sur les trois formes (binary_sensor, bouton, switch + serrure). `_with_valves` de 24.8 n'est pas modifié (ajouts seuls).
- **Registre (AR13, AC1)** : `lock` connu (`state_topic`, `command_topic`, `platform`, `availability` ; `has_state`, `has_command`) et ouvert dans `PRODUCT_SCOPE` ; `LockCapabilities` (`has_state`, `has_command`, `has_lock`, `has_unlock`) ; preuve `test_governance_fr40_proof_lock` ; `PublisherRegistry` (`publish_lock`). `LOCK_*` restent dans les listes « anti » de `switch`, `cover`, `light` (inchangées).
- **Payload (D2, AC5)** : `payload_lock: LOCK`, `payload_unlock: UNLOCK`, `state_locked: LOCKED`, `state_unlocked: UNLOCKED`, `state_jammed: JAMMED`, `optimistic: false` (fixe : une serrure a toujours son état), `default_entity_id = lock.<object_id>`, ni `code_format`, ni `payload_open`. Topic `homeassistant/lock/jeedom2ha_<eq>_<LOCK_STATE>/config`.
- **Ordres (AC4)** (`sync/command.py`) : topic de la serrure dans `_expected_command_topics` ; `LOCK` → `LOCK_CLOSE`, `UNLOCK` → `LOCK_OPEN` de la serrure, payload **exact** (sensible à la casse ; `OPEN`, `lock`, `ON`… refusés) ; la commande doit être une `action` portant le type attendu, sinon `missing_action_command` : **sans `LOCK_OPEN`, aucun déverrouillage n'est envoyé**. Confirmation `real_state_confirmation` si l'état est streamé, sinon `stateless` : aucun état optimiste. Les messages retenus restent ignorés (garde 24.7, générique).
- **État** (`sync/readback.py`, `sync/state.py`) : `STATE_KEYS["lock"]` = `mapping.lock.LOCK_STATE_KEYS` ; `lock` streamé ; traduction par `lock_state(valeur, reason_details.lock_polarity)`.
- **Override pe-epic-16** : des capacités de serrure forcées vers tout autre actionneur (switch, light, cover, button, valve, …) sont refusées ; `sensor` / `binary_sensor` (lecture) restent valides ; une autre famille forcée en `lock` est refusée. `lock` ajouté aux types autorisés d'un profil. `desktop/js/jeedom2ha_mapping_override.js` non modifié (garde 24.2).
- **Export de décision** : `lock` dans `_ACTUATOR_TYPES` ; `entity_id_expected` lu dans le payload réel. `_resolve_state_topic` rend le topic de la serrure.
- **Cycle de vie (AC6)** : pour 508, le principal change de type (`binary_sensor` → `lock`) : le topic d'équipement du `binary_sensor` est vidé par le retypage existant de `_detect_lifecycle_changes`, à chaud comme au premier sync après redémarrage (report si échec) ; un secondaire remplacé sous un principal gardé suit les chemins de 24.8 (`_unpublish_refused_candidates` à chaud, `_unpublish_boot_removed_topics` au boot). Prouvé par tests ; aucun code de cycle de vie ajouté.
- **Sécurité (D4, AC7)** : aucun code ne touche l'exposition à Assist (rien de tel n'existe dans la discovery MQTT) ; la documentation utilisateur le dit et renvoie le choix à l'utilisateur dans HA.
- **Golden 8.4** : seuls les compteurs `locks_*` à 0 apparaissent (ajouts seuls) ; le corpus ne contient qu'un `LOCK_STATE` sans action, qui garde son `binary_sensor` (AC3). Contrat 4D inchangé.
- **Garde 25.4** : lignes remplacées (listes figées qui gagnent `lock`, leurs assertions, `len(PRODUCT_SCOPE)`, test 24.8 « valve en dernier ») déclarées dans `REPLACED_BY_24_9` (`fichier::ligne`).
- Champs `lock.mqtt` non revérifiés dans le source de HA 2026.9.4 par cette session (pas d'accès) : à confirmer à la preuve terrain (entité créée, états `LOCKED` / `UNLOCKED`, aucun code demandé).

### Tests

- `resources/daemon/tests/unit/test_story_24_9_serrure_lock.py` (identifiants synthétiques 9001-9003) : registre et preuves `validate_projection` ; serrure nominale ; un seul ordre suffit ; absence de serrure (état seul, ordres seuls, deux états, deux ordres de même sens, mauvais genres, ordre à valeur, lien ailleurs) avec projection d'avant inchangée ; liens acceptés ; polarité par plugin, jamais par nom ; `jeelink` refusé ; tables cas général et `nuki` ; valeurs et polarités non reconnues → aucun état ; remplacement du `binary_sensor` et du bouton ; aucun `unique_id` réutilisé ; serrure ajoutée à côté d'un `switch` ; vanne et serrure sur le même équipement ; payload (pas de code, pas d'ouverture, rien sur Assist) ; topics ; ordres (LOCK/UNLOCK, payloads refusés, pas de déverrouillage sans `LOCK_OPEN`, commande étrangère refusée, topic d'équipement refusé, secondaire routé) ; confirmation ; refus 24.12 conservé ; état streamé et initial ; overrides croisés ; attendu HA ; export de décision ; cycle de vie (retypage à chaud et au boot, secondaire au boot) ; non-régression.
- Mis à jour : listes figées de `PRODUCT_SCOPE` / `known_types` (7.2, 7.3, 7.4, 8.2, 9.1, 9.2, 9.3, 24.7, 24.8, registre), preuve FR40, faux publisher de 19.4, golden 8.4, garde 25.4.
- `python -m pytest` : 3 032 passés, 9 désélectionnés (marqueur `load`), 0 échec. `flake8 resources/daemon tests` : 0. `node --test tests/unit/*.node.test.js` : 1 214 / 1 214 (dont la garde 25.4).

### File List

- `resources/daemon/mapping/lock.py` (nouveau)
- `resources/daemon/mapping/registry.py`, `resources/daemon/mapping/overrides.py`
- `resources/daemon/models/mapping.py`
- `resources/daemon/validation/ha_component_registry.py`
- `resources/daemon/discovery/publisher.py`, `resources/daemon/discovery/registry.py`
- `resources/daemon/sync/readback.py`, `resources/daemon/sync/command.py`, `resources/daemon/sync/state.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/export/decision_export.py`
- `resources/daemon/tests/unit/test_story_24_9_serrure_lock.py` (nouveau)
- `resources/daemon/tests/unit/test_step3_governance_fr40.py`, `test_story_19_4_guard_publisher_calls.py`, `test_ha_component_registry.py`, `test_story_7_2_wave_registry.py`, `test_story_7_3_projection_validation_wave.py`, `test_story_7_4_governance_product_scope.py`, `test_story_8_2_publisher_registry.py`, `test_story_9_1_sensor_mapper.py`, `test_story_9_2_binary_sensor_mapper.py`, `test_story_9_3_button_mapper.py`, `test_story_24_7_portail_garage_cover.py`, `test_story_24_8_vanne_arrosage_valve.py`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`
- `tests/unit/test_story_25_4_non_regression.node.test.js`
- `docs/fr_FR/index.md`, `docs/fr_FR/changelog_beta.md`, `README.md`
- `_bmad-output/implementation-artifacts/24-9-serrure-lock.md`, `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Points ouverts

1. **Preuve terrain (Q-L2)** : sur 508, inventaire avant/après (le `binary_sensor` `jeedom2ha_eq_508` disparaît, `lock.jeedom2ha_508_4628` apparaît), état lu, puis verrouiller/déverrouiller **en présence d'Alexandre**. L'ordre passe par un service en ligne : délai possible avant le retour d'état (aucun état n'est affiché entre-temps).
2. **`jeelink`** : refusé faute de savoir quel équipement il relaie ; une évolution exigerait d'exporter cette information (hors périmètre).
3. **`invertBinary`** : non appliqué à la serrure (D1 = parité Homebridge) ; à revoir si un équipement réel l'utilise.
4. **Interface** : `lock` absent du sélecteur d'override et sans libellé français (fichier JS sous garde 24.2), comme `valve`.
5. **Polarité du `binary_sensor` de classe `lock` existant** (hors story) : pour HA, `ON` signifie « déverrouillé » ; le cas général publie `1` → `ON`, soit l'inverse de Homebridge. Ne concerne plus que les serrures restées en lecture seule (sans action) ; à trancher séparément.
