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
9. **AC9 — Corrections de revue (Codex P2 + relecture indépendante, 2026-11-23)** :
   - **unknown** : quand l'état calculé devient inconnu (Actif illisible ou jamais lu, virtuel à `ALARM_STATE` seul revenu à 0) alors qu'un état avait été publié — ou que rien n'est connu de ce run (redémarrage) —, le démon publie en retained le payload `None`, que HA lit comme `unknown` (source citée en Dev Notes) ; une seule fois tant que l'état reste inconnu ;
   - **code illisible** : valeur stockée mais déchiffrement en échec → warning PHP sans la valeur, indicateur `alarm_disarm_code_unreadable` envoyé au démon ; le démon refuse tout DISARM (WARNING `alarm_code_unreadable`), la discovery exige toujours le code ;
   - **limite d'essais** : 5 codes faux pour un même équipement → verrou de 5 minutes (tout DISARM refusé, WARNING `alarm_code_locked`, jamais le code) ; remise à zéro au premier bon code ou à l'expiration ; horloge injectable ;
   - **code numérique** : 4 à 8 chiffres, espaces de début et de fin retirés, contrôlé côté PHP (`preConfig_`, exception au message clair) et côté JS (message, champ non enregistré) ; `REMOTE_CODE` gardé (pavé numérique) ;
   - **documentation** : le code n'est ni dans le topic retenu, ni dans la discovery, ni dans les journaux, mais HA l'envoie en clair, sans retain, sur le topic de commande au désarmement ; ACL du broker (seul HA publie sur `jeedom2ha/+/alarm/set`) et TLS recommandés ;
   - **redémarrage requis** : après saisie ou retrait du code, la page de configuration dit que le démon doit être redémarré et ce qui vaut d'ici là (premier code : l'alarme reste désarmable sans code) ;
   - **doublon de libellé** : deux clés Homebridge au même libellé (normalisé) → WARNING au mapping, comportement inchangé.

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
- [x] Task 10 — Corrections de revue (AC9 ; Codex P2 + relecture indépendante, aucun P1)
  - [x] 10.0 fusion de `origin/main` (bloc `hors-cycle-epic-h` de `sprint-status.yaml`, PR #418) : fusion sans conflit, les deux blocs gardés
  - [x] 10.1 `sync/state.py` : `ALARM_UNKNOWN_PAYLOAD = "None"`, suivi du dernier payload publié par topic d'alarme, retour à `unknown` sur événement et à la (re)publication
  - [x] 10.2 code illisible : `jeedom2ha_alarm_code_daemon_fields` (PHP), warning dans `deamon_start`, indicateur lu par `/action/mqtt_connect`, refus `alarm_code_unreadable` (`sync/alarm_code.py`, `sync/command.py`)
  - [x] 10.3 limite d'essais : `AlarmDisarmLockout` (5 essais, 300 s, horloge injectable), refus `alarm_code_locked`
  - [x] 10.4 code de 4 à 8 chiffres : `jeedom2ha_alarm_code_is_valid` / `_to_store` (exception), `j2haAlarmCodeIsValid` / `IsRejected` (JS), message dans la page
  - [x] 10.5 `docs/fr_FR/index.md` : phrase sur le code corrigée, ACL et TLS, blocage, code illisible, redémarrage
  - [x] 10.6 avis « redémarrage du démon requis » (`j2haAlarmCodeRestartNotice`, trois cas : premier code, changement, retrait)
  - [x] 10.7 WARNING de doublon de libellé de mode (`mapping/alarm_control_panel.py`)
  - [x] 10.8 tests Python, PHP et Node de ces cas ; revue `bmad-code-review` de la passe

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
- **Payload `unknown` (AC9)** — source : Home Assistant, `homeassistant/components/mqtt/alarm_control_panel.py`, `MqttAlarm._state_message_received` : `if payload == PAYLOAD_NONE: self._attr_alarm_state = None` ; `PAYLOAD_NONE = "None"` dans `homeassistant/components/mqtt/const.py` ; un payload vide (après rendu du template) est ignoré (« Ignoring empty payload »), il ne peut donc pas servir. Lu sur `home-assistant/core` branche `dev`, commit `5616ea891a3e4b5a7051f2a7cd754b763850df75` (23/11/2026). Même fichier : `code: REMOTE_CODE` donne `CodeFormat.NUMBER` (pavé numérique).
- **Exception de `preConfig_` (AC9, code numérique)** — cœur Jeedom (`jeedom/core`, commit `32ce257`) : `config::save` appelle `preConfig_<clé>` sans l'attraper, `config.ajax.php` (`addKey`) enregistre les clés une à une ; l'exception remonte donc en erreur AJAX affichée. Le contrôle JS empêche qu'un code refusé parte à l'enregistrement (le contrôle PHP est la défense de dernier rang).

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

- **Passe de corrections de revue (2026-11-23, AC9)** :
  - fusion de `origin/main` sans conflit (merge, pas de rebase ni de force-push) ; `sprint-status.yaml` garde `hors-cycle-epic-h` et l'entrée 12-4 ;
  - **unknown** : règle générale côté `StateSynchronizer` (pas dans la fonction pure `alarm_state`, qui garde `None` = « rien d'honnête ») ; sur événement, `None` est publié si le dernier payload publié du run sur ce topic n'est pas déjà `None` (donc aussi au premier événement après un redémarrage) ; à la (re)publication (sync, « Publier », naissance HA, reconnexion), une alarme sans état honnête publie `None` (un état retenu d'un run précédent peut être au broker). Le test `test_never_read_enable_publishes_nothing` devient `…_resets_ha_to_unknown_once` : comportement changé à dessein ;
  - **code illisible** : déchiffrement en exception, `false`, non-texte ou blanc = illisible ; l'indicateur l'emporte sur un code qui arriverait quand même ; seul `true` (booléen JSON) l'active ;
  - **limite d'essais** : seuls les codes faux comptent (code absent et armements non) ; un nouveau code (démarrage du démon) remet tout à zéro ; le bon code est refusé pendant le verrou ; état en mémoire (perdu au redémarrage du démon, qui relit aussi le code) ;
  - **avis de redémarrage** : trois messages exacts au lieu d'un seul (premier code : désarmable sans code ; changement : l'ancien code reste demandé ; retrait : le code reste demandé), pour ne pas afficher une phrase fausse ; il disparaît après « Tester, enregistrer et redémarrer le démon » (`j2haAlarmCodeAfterSave`) ;
  - garde 25.4 : aucune ligne de `main` figée retirée (fichiers propres à 12.4 seulement) ; `REPLACED_BY_12_4` inchangé.

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
- Passe de corrections de revue (AC9), fichiers modifiés : `core/class/jeedom2ha.class.php`, `core/php/jeedom2ha_alarm.php`, `docs/fr_FR/index.md`, `plugin_info/configuration.php`, `resources/daemon/mapping/alarm_control_panel.py`, `resources/daemon/sync/alarm_code.py`, `resources/daemon/sync/command.py`, `resources/daemon/sync/state.py`, `resources/daemon/transport/http_server.py`, `resources/daemon/tests/unit/test_story_12_4_alarme_etat_mode.py`, `tests/test_php_alarm.php`, `tests/unit/test_story_12_4_configuration_alarme.node.test.js`, ce fichier de story

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

## Review Findings

### Revue Codex et relecture indépendante (2026-11-23) — aucun P1, tous corrigés (AC9, Task 10)

- [x] [Codex][P2] Virtuel à `ALARM_STATE` seul : 1 → 0 donnait `None`, rien publié, HA restait sur `triggered` (retenu). Règle générale : état devenu inconnu après un état publié (ou encore inconnu après un redémarrage) → payload `None` retenu [sync/state.py]
- [x] [Relecture] Code stocké mais illisible : le démon partait sans code (désarmable sans code). Indicateur `alarm_disarm_code_unreadable`, refus de tout DISARM, discovery qui exige le code, warning PHP sans valeur [core/php/jeedom2ha_alarm.php, core/class/jeedom2ha.class.php, sync/alarm_code.py, sync/command.py, transport/http_server.py]
- [x] [Relecture] Aucune limite d'essais : verrou de 5 minutes après 5 codes faux, par équipement, horloge injectable [sync/alarm_code.py, sync/command.py]
- [x] [Relecture] Code libre : 4 à 8 chiffres, PHP et JS, `REMOTE_CODE` gardé [core/php/jeedom2ha_alarm.php, plugin_info/configuration.php]
- [x] [Relecture] Doc inexacte (« n'apparaît ni dans les messages MQTT ») : HA envoie le code en clair, sans retain, sur le topic de commande ; ACL et TLS recommandés [docs/fr_FR/index.md]
- [x] [Relecture] Redémarrage du démon requis non signalé dans la page : avis à trois cas [plugin_info/configuration.php]
- [x] [Relecture] Deux clés Homebridge au même libellé : WARNING au mapping, comportement inchangé [mapping/alarm_control_panel.py]

### Revue Codex de la tête `ddceae7` (2026-11-23)

- [x] [Codex][P2] `_last_known_value()` confondait « événement de valeur `None` » et « aucun événement » : après Actif=`None` (publié `None`, correct), un événement Mode reprenait l'ancienne `current_value` de la topologie (Actif=1) et publiait `armed_away` ; la republication (naissance HA, reconnexion) reprenait la même valeur périmée. Correctif : `_last_known_alarm_value()` lit `last_event()` et garde `None` quand un événement l'a porté ; seul « aucun événement » retombe sur la topologie. Utilisé pour les quatre infos de l'alarme (calcul des voisines et `republish_alarm_states`). Vérifié aussi pour Statut (jamais `triggered` ressuscité), Immédiat (jamais `pending` ressuscité) et Mode (mode inconnu → `armed_away`, règle 5, jamais l'ancien mode). Tests : séquence Actif=`None` puis Mode, republication après Actif=`None`, et les trois autres infos ; rouges sur `ddceae7`, verts après. `_last_known_value()` lui-même n'est pas modifié : il sert aussi au thermostat (Story 24.15), hors périmètre de cette story [sync/state.py]

### Revue Codex de la tête `b74efea` (2026-11-23) — correction à la racine

- [x] [Codex][P2] « Publier » relisait Actif à `None` : `publish_click_states()` publiait bien `None`, puis `reconcile_fresh_read()` retirait la valeur du cache et l'événement Mode suivant reprenait la `current_value` (1) de la topologie : l'alarme réapparaissait armée ; la republication aussi. Troisième constat de la même famille : correction à la racine, **pour l'alarme seulement** (les autres types gardent leur comportement).
  - **Source unique** : `StateSynchronizer._alarm_reads`, magasin « dernière lecture connue » `(eq_id, cmd_id) -> (instant de lecture, valeur)` des quatre infos (Actif, Statut, Immédiat, Mode). `None` y est une valeur. Alimenté par toutes les lectures (événement, lecture au clic, synchro complète). Aucun chemin ne retire d'entrée : une lecture plus récente la remplace, y compris la topologie d'une synchro pour les entrées plus anciennes que sa lecture (un événement reçu après la lecture de la synchro reste le plus récent, règle de la Story 24.15). Seule une commande jamais lue retombe sur la valeur du mapping.
  - **Audit des chemins du démon qui lisent ou effacent une valeur d'alarme** (`sync/state.py` sauf mention) :
    1. **Événement Jeedom** (`handle_state_message`) : écrit dans le magasin avant tout garde-fou (broker absent, cible non résolue), `None` compris ; le calcul de l'état lit les trois autres infos dans le magasin (`_translate_alarm_value` → `_last_known_alarm_value`).
    2. **Clic « Publier »** (`publish_click_states`, appelé par `http_server` pour l'équipement) : passe par `reconcile_fresh_read(…, fresh_values)` qui écrit chaque info relue (`None` compris) ; une info non relue par le clic garde sa lecture précédente ; la boucle de publication lit les infos de l'alarme dans le magasin, plus dans `fresh_values` ni dans les événements en attente.
    3. **`reconcile_fresh_read`** : pour l'alarme, n'écrit que dans le magasin (lecture fraîche, puis événement en attente plus récent que la lecture) ; son retrait d'entrée (`pop`) ne touche que le cache des autres types, que l'alarme ne lit plus.
    4. **Synchro complète** (`_do_handle_action_sync` → `reconcile_fresh_read(decision, sync_read_at)` → `publish_initial_states`) : la topologie remplace les lectures plus anciennes que la synchro (`None` compris) ; un événement reçu avant que l'alarme soit au registre mais après la lecture de la synchro est repris depuis le cache des événements ; la publication initiale lit le magasin.
    5. **Naissance de HA et reconnexion au broker** (`_republish_all_from_cache_body` → `_republish_alarm_state` → `republish_alarm_states`) : lit le magasin seulement.
    6. **Redémarrage du démon** : magasin vide (en mémoire) ; avant la première synchro, aucune alarme n'est au registre, donc rien n'est publié ni recalculé ; la première synchro remplit le magasin depuis la topologie.
    7. **Hors `state.py`** : `sync/command.py` ne lit aucune valeur d'alarme (pas d'état optimiste, `real_state_confirmation` / `stateless` seulement) ; `last_event_value` ne sert qu'aux barrières (Story 24.7) ; `_last_known_value` ne sert plus qu'au thermostat (Story 24.15) ; `_purge_invalid_retained` ne concerne pas l'alarme.
  - **Tests** (`test_story_12_4_alarme_etat_mode.py`) : pour chaque chemin, la séquence « Actif=1 dans la topologie → lecture `None` par ce chemin → événements Mode, Statut, Immédiat → toujours inconnu », puis la republication, puis le retour d'un état quand Actif est relu à 1. Chemins couverts : événement, événement rejeté broker absent, clic, clic suivi d'un clic qui ne relit pas Actif, relecture fraîche, topologie de synchro, événement plus récent qu'une synchro ; plus le redémarrage, l'événement reçu avant la mise au registre, et le bout en bout par `/action/sync` avec la naissance de HA et la reconnexion. Quatre de ces tests sont rouges sur `b74efea`.
  - Écart assumé : au clic « Publier », une info que le clic n'a pas relue prend sa dernière lecture connue au lieu de bloquer la publication (règle « source unique ») ; les autres types gardent la règle de la Story 19.5 [sync/state.py]

### `bmad-code-review` de la passe de corrections (diff `623e0bf..892433e`, 2026-11-23)

Même session que les corrections (pas de contexte neuf ni d'autre modèle : écart à la recommandation du workflow, comme à la première revue). File List conforme au diff ; Tasks 10.x vérifiées dans le code et les tests ; AC9 implémenté. Aucun constat High.

Retenus (corrigés dans cette passe) :

- [x] [AI-Review][Medium] Après « Sauvegarder » du cœur (et non le parcours guidé), le code saisi restait en clair dans le champ (classe `configKey` comprise) et l'avis de redémarrage dépendait du champ. Le cœur appelle `window.jeedom2ha_postSaveConfiguration` après un enregistrement réussi (`desktop/js/plugin.js`, `savePluginConfig`, cœur `32ce257`) : le code quitte la page, le statut est mis à jour, et l'avis « redémarrage requis » reste affiché jusqu'au parcours guidé (qui redémarre le démon) [plugin_info/configuration.php]
- [x] [AI-Review][Medium] `trim()` de JavaScript retire plus de blancs que `trim()` de PHP (espace insécable, espaces Unicode) : un code « 1234 » suivi d'une espace insécable passait le contrôle JS puis faisait échouer l'enregistrement côté PHP (et l'arrêtait en cours de boucle `addKey`). Le JS retire maintenant exactement les mêmes caractères que PHP [plugin_info/configuration.php]

Écartés (avec raison) :

- [Low] Le WARNING de doublon de libellé revient à chaque synchronisation : c'est le moment où le mapping est recalculé, comme les autres constats de mapping ; une seule ligne par alarme concernée, rien à mémoriser entre synchros.
- [Low] La publication de `None` compte dans le nombre d'états publiés (sync, « Publier ») : c'est bien une publication sur le topic d'état, et le compteur sert au diagnostic, pas à une promesse d'état connu.
- [Low] Le verrou d'essais est par équipement, sans plafond global : une installation a une ou deux alarmes ; quelqu'un qui peut publier sur le topic de commande peut aussi y lire le code (d'où la recommandation ACL/TLS), le verrou freine seulement l'essai à l'aveugle depuis HA.
- [Low] Verrou et compteur en mémoire, perdus au redémarrage du démon : le démon relit alors le code ; un redémarrage demande l'accès à Jeedom, hors de portée d'un essai depuis HA.
- [Info] Code illisible sans broker configuré : le démon ne reçoit rien (limite déjà notée : sans broker, rien n'est publié ni commandé).

## Change Log

- 2026-11-23 — Story créée (`bmad-create-story`, session cloud déléguée) à partir des règles 1 à 7 du porteur du projet (23/11) ; `ready-for-dev`. Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-11-23 — Dev-story (session cloud déléguée) : Tasks 1 à 8 faites (état diffusé, CC-08, armement par mode, code de désarmement, topologie, doc, tests, baselines, garde 25.4) ; `review`. Restent Task 0 et Task 9 (terrain).
- 2026-11-23 — Story renumérotée 24.18 → 12.4 et rangée sous `pe-epic-12` (epic qui porte FR49), sur consigne du coordinateur.
- 2026-11-23 — Code review (`bmad-code-review`) : 4 constats corrigés, 5 écartés (voir ci-dessus) ; statut `review` en attente de la preuve terrain.
- 2026-11-23 — Corrections de revue (Codex P2 + relecture indépendante, AC9) : fusion de `origin/main`, retour à `unknown` (payload `None`), code illisible refusé, limite d'essais, code de 4 à 8 chiffres, doc (code en clair sur le topic de commande, ACL, TLS), avis de redémarrage, WARNING de doublon de libellé ; statut `review`.
- 2026-11-23 — `bmad-code-review` de la passe de corrections : 2 constats Medium corrigés (code laissé dans la page après « Sauvegarder » du cœur, `trim` JS ≠ PHP), 5 écartés ; statut `review` (AC8 terrain toujours à faire).
- 2026-11-23 — Revue Codex de `ddceae7` : P2 corrigé (un événement de valeur `None` n'est plus remplacé par la valeur de topologie pour les quatre infos de l'alarme) ; statut `review`.
- 2026-11-23 — Revue Codex de `b74efea` : P2 corrigé à la racine (magasin unique des lectures des quatre infos de l'alarme, audit des chemins, un test par chemin) ; statut `review`.
