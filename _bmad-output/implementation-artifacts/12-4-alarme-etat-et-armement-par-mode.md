# Story 12.4 : Alarme — diffuser l'état vers HA et armer par mode (FR49, CC-64)

Status: review

> Story créée le 2026-11-23 par une session cloud déléguée (workflow `bmad-create-story`), à partir des règles 1 à 7 validées par le porteur du projet le 23/11 et relayées par le coordinateur (point CC-64). Base : `origin/main` `9f56005`. Aucun accès à la box ni à Home Assistant. Aucun nom réel, aucune IP, aucun secret (CC-48) : identifiants d'exemple seulement. Dépôt en gel : ce correctif est autorisé, rien d'autre ne doit bouger.

## Story

En tant qu'utilisateur qui pilote son alarme depuis Home Assistant,
je veux voir l'état réel de l'alarme (désarmée, armée selon le mode, délai d'entrée, déclenchée) et l'armer dans le mode voulu,
afin que HA se comporte comme HomeKit (parité Homebridge) au lieu d'afficher `unknown` et de ne rien exécuter.

**Parcours : démon (+ configuration du plugin pour le code).** Comportement générique : tout utilisateur du plugin Jeedom « alarm » ou d'un virtuel d'alarme (aucun identifiant ni libellé de la maison dans le code ou les tests, hors valeurs d'exemple).

## Contexte

Rattachement : **pe-epic-12 « Restitution d'état runtime Jeedom → Home Assistant »**, l'epic qui porte FR49 (FRs couverts : FR46 à FR50) ; FR49 prévoit que les domaines actionnables au-delà de la vague 1 « sont ajoutés par vagues ultérieures gouvernées ». Cette story est la vague `alarm_control_panel` (après 12.1 sensor / binary_sensor, 12.2 switch, puis light / cover en 23.3, valve / lock / climate en 24.x). L'epic était `done` (clos par 12.3) : il est rouvert en `in-progress` pour cette story (option « repasser l'epic en in-progress » du workflow create-story). La parité HomeKit de l'alarme relève aussi de l'esprit de pe-epic-24 (clos), qui n'est pas modifié.

### Faits de production (relevé en lecture seule par le coordinateur, ids d'exemple, un équipement du plugin `alarm`)

| Id | Commande | Type | generic_type | logicalId | Sens |
|---|---|---|---|---|---|
| 1872 | Actif | info/binary | `ALARM_ENABLE_STATE` | `enable` | 1 = armée |
| 1876 | Statut | info/binary | `ALARM_STATE` | `state` | 1 = déclenchée |
| 1877 | Immédiat | info/binary | **aucun** | `immediatState` | 1 = délai d'entrée en cours |
| 1878 | Mode | info/string | `ALARM_MODE` | `mode` | quatre libellés de mode (`<mode 1>` … `<mode 4>`) |
| 1879 / 1880 | Activer / Désactiver | action | `ALARM_ARMED` / `ALARM_RELEASED` | | |
| 1881, 1882, 2330, 2331 | modes | action | `ALARM_SET_MODE` | | lancer un mode ARME l'alarme |

Configuration posée par Homebridge sur l'eqLogic : `SetModePresent = "2330|<mode 3>"`, `SetModeAbsent = "1881|<mode 1>"`, `SetModeNuit = "1882|<mode 2>"` (format « id|libellé »).

### Faits établis dans le code (`origin/main` `9f56005`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Le mapper crée l'entité (`state_topic` `jeedom2ha/<eq>/alarm/state`, `command_topic` `…/alarm/set`) avec un `value_template` `1 → armed_away`, sinon `disarmed`. | `mapping/alarm_control_panel.py`, `discovery/publisher.py::_build_alarm_control_panel_payload` |
| F2 | Aucun état n'est diffusé : « alarm_control_panel is not streamed yet (FR49) ». L'entité reste `unknown`. | `sync/state.py` (docstring, `_STREAMED_TYPES`) |
| F3 | Le topic `jeedom2ha/<eq>/alarm/set` n'est reconnu par aucune regex de `CommandSynchronizer._parse_topic` : tout ordre HA est rejeté (`invalid_command_topic`). Il est pourtant couvert par l'abonnement `jeedom2ha/+/+/set`. | `sync/command.py` |
| F4 | Le démon reçoit déjà un réglage secret par le corps HTTP local protégé par `X-Local-Secret` : le mot de passe du broker, dans `/action/mqtt_connect` (envoyé par `deamon_start`, jamais journalisé). C'est le canal réutilisé pour le code. | `core/class/jeedom2ha.class.php::deamon_start`, `transport/http_server.py::_handle_mqtt_connect` |
| F5 | Birth HA / reconnexion broker : `_republish_all_from_cache_body` republie la discovery seule (états retenus supposés présents au broker). | `transport/http_server.py` |
| F6 | Modèles à suivre : climate (une valeur dépend d'une autre info, lue par `peer`), lock / valve (pas d'état optimiste, `stateless` / `real_state_confirmation`), select (commande retenue seulement si c'est une commande de l'équipement). | `sync/readback.py`, `sync/state.py`, `sync/command.py` |

## Critères d'acceptation

1. **AC1 — Fonction d'état pure (`sync/readback.alarm_state`)**, ordre fixe :
   1. `ALARM_STATE` = 1 → `triggered` ;
   2. `ALARM_ENABLE_STATE` = 0 → `disarmed` ;
   3. info de logicalId `immediatState` (plugin `alarm`) = 1 → `pending` ; les generic types Jeedom ne sont jamais modifiés (ils alimentent Homebridge) ;
   4. sinon, libellé `ALARM_MODE` (casse et espaces normalisés) comparé aux libellés des clés `SetModePresent` → `armed_home`, `SetModeAbsent` → `armed_away`, `SetModeNuit` → `armed_night` ;
   5. mode inconnu ou configuration absente → `armed_away` (comme Homebridge / HomeKit) ;
   6. Actif jamais lu (ou illisible) → rien d'inventé, l'entité reste `unknown` ;
   7. délai de sortie sans signal : `arming` n'est jamais publié.
2. **AC2 — Diffusion** : tout changement de l'une des 4 infos recalcule l'état (avec la dernière valeur connue des 3 autres) et le publie en retained sur le `state_topic` déjà déclaré. L'état est aussi publié au sync et à la publication initiale (« Publier » compris).
3. **AC3 — CC-08** : l'état de l'alarme est republié à la naissance de HA (`homeassistant/status = online`) et à la reconnexion au broker, après la discovery ; aucun autre type n'est concerné.
4. **AC4 — Commandes par mode** :
   - `ARM_HOME` → commande désignée par `SetModePresent`, `ARM_AWAY` → `SetModeAbsent`, `ARM_NIGHT` → `SetModeNuit`, `DISARM` → `ALARM_RELEASED` (ou `ALARM_DISABLE` pour un virtuel) ;
   - une commande de mode n'est retenue que si son id existe sur l'équipement et qu'elle est une action `ALARM_SET_MODE` ;
   - `supported_features` n'annonce que les armements disponibles ;
   - sans configuration de mode : armer = `ALARM_ARMED` / `ALARM_ENABLE` (comportement actuel) ;
   - jamais d'état optimiste : HA attend le retour d'état.
5. **AC5 — Topologie** : le PHP exporte en lecture seule les 3 clés de configuration de l'eqLogic (`getConfiguration`), au minimum pour les équipements alarme ; le modèle Python `models/topology.py` les porte. Aucune écriture côté Jeedom.
6. **AC6 — Code de désarmement** (désarmer avec code, armement libre) :
   - nouvelle clé de configuration du plugin, champ mot de passe dans la page de configuration ;
   - code configuré : la discovery publie `code: REMOTE_CODE`, `code_disarm_required: true`, `code_arm_required: false` et un `command_template` qui transmet l'action et le code ;
   - le démon compare en temps constant (`hmac.compare_digest`) ; code faux ou absent → refus + WARNING sans le code ;
   - le code ne passe jamais en ligne de commande ; il n'apparaît dans aucun journal, topic retained, discovery, ni dans Git ;
   - canal : corps HTTP local protégé par le secret local (F4) ;
   - sans code configuré : comportement sans code.
7. **AC7 — Non-régression** : le virtuel générique (`ALARM_ENABLE` / `ALARM_DISABLE` avec `ALARM_STATE` / `ALARM_ENABLE_STATE`) continue de marcher, test à l'appui ; suites Python, Node, PHP et `flake8` vertes ; garde 25.4 tenue (lignes remplacées déclarées).
8. **AC8 — Preuve terrain (ClaudeBox / porteur du projet, hors session cloud)** : après déploiement, l'entité alarme sort de `unknown` ; armer en présent / absent / nuit et désarmer (avec et sans code) depuis HA ; état suivi ; journal sans code.

## UI Impact

- **UI Impact:** Oui — page de configuration du plugin : bloc « Alarme » (champ « Code de désarmement », case « Retirer le code »). Côté HA : l'entité alarme affiche son état et ses armements.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — **hors session cloud** (CLAUDE.md : jamais `deploy-to-box.sh` ni accès box/HA) ; à ClaudeBox / porteur du projet
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
- [x] Task 1 — Topologie (AC5)
  - [x] 1.1 PHP pur `core/php/jeedom2ha_alarm.php::jeedom2ha_alarm_mode_config` ; appel dans `getFullTopology` (clé `alarm_mode_config`, ajoutée seulement si présente)
  - [x] 1.2 `models/topology.py` : `JeedomEqLogic.alarm_mode_config`, normalisation (clés connues, texte non vide)
- [x] Task 2 — Mapper (AC4, AC5)
  - [x] 2.1 lire Statut, Actif, Mode, Immédiat (logicalId `immediatState`, plugin `alarm`) ; parser « id|libellé » ; retenir une commande de mode seulement si action `ALARM_SET_MODE` de l'équipement
  - [x] 2.2 helpers partagés : `alarm_arm_targets`, `alarm_disarm_command`, `alarm_supported_features`
- [x] Task 3 — État (AC1, AC2)
  - [x] 3.1 `sync/readback.alarm_state` + `alarm_readback_commands`
  - [x] 3.2 `sync/state.py` : type streamé, 4 infos → même topic, recalcul avec les valeurs « pairs »
- [x] Task 4 — CC-08 (AC3) : `StateSynchronizer.republish_alarm_states` appelé par `_republish_all_from_cache_body`
- [x] Task 5 — Commandes (AC4, AC6) : topic `…/alarm/set`, traduction, politique `real_state_confirmation` / `stateless`
- [x] Task 6 — Code (AC6)
  - [x] 6.1 `sync/alarm_code.py` (en mémoire, `compare_digest`, `repr` sans code)
  - [x] 6.2 `/action/mqtt_connect` : retirer `alarm_disarm_code` du corps avant le pont MQTT
  - [x] 6.3 PHP : `preConfig_alarmDisarmCode` (chiffré), `preConfig_alarmDisarmCodeClear`, envoi dans `deamon_start` (corps seulement)
  - [x] 6.4 page de configuration : bloc « Alarme » (champ mot de passe, statut, case « Retirer le code ») + JS en ligne
  - [x] 6.5 discovery : `REMOTE_CODE`, `code_disarm_required`, `code_arm_required`, `command_template`
- [x] Task 7 — Tests (voir ci-dessous), baselines et garde 25.4
- [x] Task 8 — Documentation utilisateur (`docs/fr_FR/index.md`), epics, sprint-status
- [ ] Task 9 — Preuve terrain AC8 (ClaudeBox / porteur du projet, hors session cloud)

## Tests attendus (identifiants synthétiques)

- `resources/daemon/tests/unit/test_story_12_4_alarme_etat_mode.py` :
  - table de vérité de `alarm_state` (ordre des règles, normalisation, valeurs illisibles, Actif jamais lu, `arming` jamais publié) ;
  - mapper : modes retenus / refusés (id absent, mauvais type, mauvais generic type, format invalide) ; `supported_features` ; Immédiat seulement pour le plugin `alarm` ;
  - diffusion : chacune des 4 infos republie l'état recalculé ; état initial au sync et à « Publier » ;
  - CC-08 : birth HA et reconnexion broker republient l'état de l'alarme, et seulement elle ;
  - commandes par mode, désarmement, armement non disponible refusé, jamais d'état publié par l'ordre ;
  - code : bon, faux, absent, non configuré ; WARNING sans le code ; `compare_digest` ;
  - discovery : sans code (aucun champ de code) et avec code (`REMOTE_CODE`, jamais la valeur) ;
  - non-régression du virtuel générique.
- `tests/test_php_alarm.php` : fonctions pures, vrai `getFullTopology` sur un faux cœur (export lecture seule, aucune écriture), hooks `preConfig_`, code absent de la ligne de commande et des journaux.
- `tests/unit/test_story_12_4_configuration_alarme.node.test.js` : bloc « Alarme » de la configuration et fonction JS `j2haAlarmCodeIsSaved`.

## Dev Notes

- **Une seule source** pour les armements (`alarm_arm_targets`) : discovery (`supported_features`) et commandes la partagent, comme `sync.readback` pour l'état.
- **Pas d'état optimiste** : `alarm_control_panel` n'a pas d'option `optimistic` côté HA ; la politique est `real_state_confirmation` si l'état est streamé, sinon `stateless`.
- **Le code ne quitte jamais le démon** : stocké dans un objet dont le `repr` ne le contient pas ; aucune trace dans `_log_cmd` (qui ne journalise jamais le payload).
- **Baselines** : la discovery de l'alarme change (plus de `value_template`, `payload_arm_night`, `supported_features`) et le mapper déclare plus de commandes ; les baselines de projection sont mises à jour **pour les seules entrées d'alarme**, le reste doit rester identique.
- `alarm_control_panel` a été ouvert en 10.3 sous FR40/NFR10 : pas de nouvelle ouverture de `PRODUCT_SCOPE`.

### Dev Agent Guardrails

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`
- Session cloud : aucun déploiement, aucun accès box / HA (CLAUDE.md).

### Project Structure Notes

- Démon : `mapping/alarm_control_panel.py`, `sync/readback.py`, `sync/state.py`, `sync/command.py`, `sync/alarm_code.py` (nouveau), `discovery/publisher.py`, `transport/http_server.py`, `models/topology.py`.
- PHP : `core/php/jeedom2ha_alarm.php` (nouveau, fonctions pures), `core/class/jeedom2ha.class.php`, `plugin_info/configuration.php`.

### References

- [Source: _bmad-output/planning-artifacts/prd.md#FR49]
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-12] (FR46-FR50, gates epic-level pe-epic-12)
- [Source: _bmad-output/implementation-artifacts/24-9-serrure-lock.md] (pas d'état supposé, parité Homebridge)
- [Source: _bmad-output/implementation-artifacts/24-15-thermostat-climate-complet.md] (valeur dépendant d'une autre info, `peer`)
- [Source: _bmad-output/project-context.md] (sécurité : localhost, secret local, pas de secret en argv)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée, 2026-11-23).

### Debug Log References

- Branche `story/alarm-state` depuis `origin/main` `9f56005`.
- **Écart de méthode** : le code (Tasks 1 à 6) a été écrit avant la création de ce fichier de story (consigne BMAD reçue en cours de session). Il a été gardé et mis en conformité : la story reprend exactement les règles 1 à 7, puis les tests ont été écrits ; le cycle rouge a été vérifié a posteriori (les tests de 12.4 échouent à la collecte sur le code de `main`, faute de `alarm_state`, `alarm_code`, des helpers du mapper).
- Cause de F3 confirmée par test : avant 12.4, un ordre sur `jeedom2ha/<eq>/alarm/set` était rejeté `invalid_command_topic`.

### Implementation Plan

- **État** : `sync/readback.alarm_state` (pure) + `alarm_readback_commands` (les 4 infos → canal `state` du même topic). `StateSynchronizer` traite l'alarme comme le `climate` : la valeur de l'événement remplace celle de sa commande, les 3 autres sont lues par `peer` (dernier événement, sinon valeur de topologie ; au « Publier », valeurs fraîches du clic).
- **CC-08** : `StateSynchronizer.republish_alarm_states(decision)` (boucle de l'état initial restreinte à `alarm_control_panel`, valeurs « dernière connue »), appelée par `_republish_all_from_cache_body` après la discovery de chaque équipement (birth HA et reconnexion broker passent par cette fonction).
- **Commandes** : regex `jeedom2ha/<eq>/alarm/set`, topic attendu lu dans `reason_details`, traduction `_translate_alarm_command` sur les helpers `alarm_arm_targets` / `alarm_disarm_command` partagés avec la discovery (`supported_features`), contrôle « commande de l'équipement », politique `real_state_confirmation` / `stateless`.
- **Code** : `sync/alarm_code.py` (coffre en mémoire, `hmac.compare_digest`, `repr` sans code), alimenté par le corps de `/action/mqtt_connect` (clé `alarm_disarm_code` retirée avant le pont MQTT). Côté PHP : `preConfig_alarmDisarmCode` (chiffré par `utils::encrypt`, saisie vide = code gardé), `preConfig_alarmDisarmCodeClear`, envoi dans `deamon_start` seulement si un code existe.

### Completion Notes List

- AC1 à AC7 implémentés et testés ; AC8 (preuve terrain) et Task 0 restent à ClaudeBox / porteur du projet (aucun accès box/HA en session cloud).
- Points tranchés (non couverts explicitement par les règles) :
  1. **Virtuel à `ALARM_STATE` seul (sans `ALARM_ENABLE_STATE`)** : règles appliquées telles quelles — `triggered` si Statut = 1, sinon Actif jamais lu → rien publié (`unknown`). L'ancien `value_template` lisait `ALARM_STATE` comme « armée » ; il n'était de toute façon jamais alimenté.
  2. **Sans configuration de mode** : seul `arm_away` est annoncé (ARM_AWAY → `ALARM_ARMED` / `ALARM_ENABLE`), cohérent avec l'état `armed_away` que l'on publie ; `ARM_HOME` n'est plus annoncé.
  3. **Configuration partielle** : dès qu'un mode valable existe, seuls les modes valables sont annoncés (pas de repli de `ARM_AWAY` sur l'armement générique).
  4. **Libellés pour l'état** : un libellé de clé Homebridge bien formé sert à l'état même si sa commande n'est pas retenue (lecture seule).
  5. **Canal du code** : corps de `/action/mqtt_connect` (même canal que le mot de passe du broker) ; conséquence : le code n'est lu qu'au démarrage du démon (documenté dans l'info-bulle et la doc). Si aucun broker n'est configuré, le démon ne reçoit pas de code (il ne publie rien non plus).
  6. **Code configuré + payload nu `DISARM`** : refusé (`alarm_code_missing`) ; un armement reste accepté nu ou en JSON.
  7. **Effacement du code** : case « Retirer le code » (clé `alarmDisarmCodeClear`, hook `preConfig_`) ; le champ du code n'est `configKey` que s'il est saisi (comme le mot de passe MQTT).
  8. **Épic** : rangée sous `pe-epic-12` (l'epic qui porte FR49), rouvert en `in-progress` ; `last_updated` de `sprint-status.yaml` laissé tel quel (consigne du coordinateur, PR #418 concurrente).
- Baselines : seules les entrées des alarmes de corpus (eq 230 et 12000) changent (payload de discovery, commandes du mapping, `supported_features`) ; vérifié par diff. Garde 25.4 : `REPLACED_BY_12_4` (73 lignes, alarme et baselines seulement).
- Suites : pytest 3666 passés, 37 ignorés (au dernier passage ; un échec intermittent sous charge vu deux fois sur `test_deploy_safety_rollback.py::test_daemon_is_restarted_when_version_write_fails_after_a_good_promotion`, sans lien : vert 3 fois sur 3 isolé, script de déploiement non touché) ; `flake8 resources/daemon tests` vert ; Node 1641 passés, 1 échec préexistant (`25.4 / AC8`, rouge aussi sur `main` non modifié : compare au SHA figé 4ff80cd, ignoré dans un clone superficiel) ; PHP : `test_php_alarm.php` 34/34 et les autres tests autonomes verts (3 exigent un vrai cœur Jeedom, ignorés en CI) ; `php -l` vert.

### File List

- `_bmad-output/implementation-artifacts/12-4-alarme-etat-et-armement-par-mode.md` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `core/class/jeedom2ha.class.php`
- `core/php/jeedom2ha_alarm.php` (nouveau)
- `docs/fr_FR/index.md`
- `plugin_info/configuration.php`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/mapping/alarm_control_panel.py`
- `resources/daemon/models/topology.py`
- `resources/daemon/sync/alarm_code.py` (nouveau)
- `resources/daemon/sync/command.py`
- `resources/daemon/sync/readback.py`
- `resources/daemon/sync/state.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_story_12_4_alarme_etat_mode.py` (nouveau)
- `resources/daemon/tests/fixtures/barrier_state_sensor/projection_baseline.json`
- `resources/daemon/tests/fixtures/fix_switch_appariement/projection_baseline.json`
- `resources/daemon/tests/fixtures/front_v2_lot3/discovery_baseline.json`
- `resources/daemon/tests/fixtures/front_v3_lot4a/scenarios_upgrade_baseline.json`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`
- `resources/daemon/tests/fixtures/select_mode/projection_baseline.json`
- `resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore.json`, `s1_sync_corpus_dore_mqtt.json`, `s2_second_sync_calls.json`, `s2_second_sync_calls_mqtt.json`, `s3_publier_global_after_sync.json`, `s3_publier_global_after_sync_mqtt.json`, `s5_policy_transition_sure_only.json`, `s5_policy_transition_sure_only_mqtt.json`
- `resources/daemon/tests/fixtures/system_health/projection_baseline.json`
- `tests/test_php_alarm.php` (nouveau)
- `tests/unit/test_story_12_4_configuration_alarme.node.test.js` (nouveau)
- `tests/unit/test_story_25_4_non_regression.node.test.js`
- `tests/unit/test_story_25_9_configuration.node.test.js`

## Senior Developer Review (AI)

Revue adverse `bmad-code-review` du 2026-11-23 (même session que le développement : pas de contexte neuf ni d'autre modèle, écart à la recommandation du workflow), sur le diff `main...story/alarm-state`.

- **AC1 à AC7** : implémentés, preuves dans `test_story_12_4_alarme_etat_mode.py` (95 tests), `test_php_alarm.php` (34), `test_story_12_4_configuration_alarme.node.test.js` (4). **AC8** (terrain) non faisable en session cloud : Task 0 et Task 9 restent ouvertes, à ClaudeBox.
- File List conforme au diff git (aucun fichier changé non déclaré).
- Vérification externe : le cœur Jeedom (`core/class/config.class.php`, `config::save`) appelle bien `preConfig_<clé>` du plugin avant l'écriture et enregistre la valeur rendue.

### Constats retenus (corrigés)

- [x] [AI-Review][Medium] Après « Tester, enregistrer et redémarrer le démon », le code saisi restait dans le champ de la page (classe `configKey` comprise), contrairement au mot de passe MQTT : il est maintenant vidé et le statut « Code déjà configuré » affiché [plugin_info/configuration.php, `j2haRunGuidedConnection`].
- [x] [AI-Review][Medium] Le champ du code ne réagissait qu'à `keyup` / `change` : un collage à la souris (événement `input`) n'était pas enregistré. Écoute de `input` ajoutée ; trouvé par le test Chromium [plugin_info/configuration.php].
- [x] [AI-Review][Low] Le test « jamais en ligne de commande » ne vérifiait presque rien : il lit maintenant les options réelles du parseur du démon (`Jeedom2haConfig`) et le source de `main.py` [test_story_12_4_alarme_etat_mode.py].
- [x] [AI-Review][Low] Ligne `params = data.get(...)` de `_handle_mqtt_connect` réécrite inutilement : remise telle quelle, copie faite à part (garde 25.4 : une ligne retirée de moins) [transport/http_server.py].

### Constats écartés (avec raison)

- [Low] L'état de l'alarme est republié au birth / à la reconnexion même si la republication de sa discovery a échoué : l'état est retenu (`retain=True`), HA le relit quand l'entité apparaît ; pas d'effet nuisible, et suivre le résultat de la discovery demanderait de toucher la boucle commune de republication (hors périmètre, dépôt en gel).
- [Low] `payload_arm_home` / `payload_arm_night` restent dans la discovery même quand l'armement n'est pas annoncé : HA ne propose que `supported_features` ; payloads constants, inoffensifs, et identiques pour toutes les alarmes.
- [Low] La clé `alarmDisarmCodeClear` reste en base à `0` après usage : valeur neutre, nécessaire au mécanisme `configKey` du cœur.
- [Info] Les libellés de mode (`alarm_mode_labels`) figurent dans `reason_details`, donc dans le diagnostic : ce sont des noms de mode choisis par l'utilisateur, pas des secrets.
- [Info] Le code n'est lu qu'au démarrage du démon : conséquence du canal imposé (corps de `/action/mqtt_connect`), documentée (info-bulle, doc utilisateur).

**Issue :** aucun constat High ; Medium corrigés. Statut laissé à `review` et non `ready-for-UX-validation` / `done` : AC8 (preuve terrain) n'est pas faite, et la définition de `done` du `sprint-status.yaml` exige la preuve terrain pour un changement de publication HA ; l'UI touchée (bloc « Alarme ») passera ensuite par `ready-for-UX-validation`.

## Change Log

- 2026-11-23 — Story créée (`bmad-create-story`, session cloud déléguée) à partir des règles 1 à 7 du porteur du projet (23/11) ; `ready-for-dev`. Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-11-23 — Dev-story (session cloud déléguée) : Tasks 1 à 8 faites (état diffusé, CC-08, armement par mode, code de désarmement, topologie, doc, tests, baselines, garde 25.4) ; `review`. Restent Task 0 et Task 9 (terrain).
- 2026-11-23 — Story renumérotée 24.18 → 12.4 et rangée sous `pe-epic-12` (epic qui porte FR49), sur consigne du coordinateur.
- 2026-11-23 — Code review (`bmad-code-review`) : 4 constats corrigés, 5 écartés (voir ci-dessus) ; statut `review` en attente de la preuve terrain.
