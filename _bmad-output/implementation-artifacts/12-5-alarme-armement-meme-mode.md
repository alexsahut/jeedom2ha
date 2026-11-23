# Story 12.5 : Alarme — armer quand le mode demandé est déjà le mode courant, et ne plus afficher l'ancien mode à l'armement (correctif FR49)

Status: review

> Story de correction créée le 2026-11-23 par une session cloud déléguée (workflow `bmad-create-story`, non interactif), après l'essai de la story 12.4 sur la démo. Base : `origin/main` `ea1b4a2` (PR #419). Dépôt en gel : on ne corrige que les deux défauts ci-dessous, rien d'autre ne bouge. Aucun accès à la box ni à Home Assistant ; aucun nom réel, aucune IP, aucun code d'alarme (identifiants d'exemple seulement).

## Story

En tant qu'utilisateur qui arme son alarme depuis Home Assistant,
je veux que « armer présent / absent / nuit » arme réellement l'alarme même quand ce mode est déjà le mode courant de l'alarme désarmée, et que HA n'affiche pas un instant l'ancien mode,
afin que l'armement depuis HA soit aussi fiable que depuis HomeKit.

**Parcours : démon seul.** Aucun changement PHP, JS, discovery, configuration ou type générique.

## Contexte

Rattachement : **pe-epic-12** (FR49), suite directe de la story 12.4 (`12-4-alarme-etat-et-armement-par-mode.md`, statut `review`).

### Écart 1 (bloquant) — armement ignoré dans le mode courant

- 12.4 : `ARM_HOME` / `ARM_AWAY` / `ARM_NIGHT` exécutent la commande de mode désignée par `SetModePresent` / `SetModeAbsent` / `SetModeNuit` (action `ALARM_SET_MODE`).
- Constat sur la démo (deux fois) : si ce mode est déjà le mode courant de l'alarme **désarmée**, rien ne se passe, sans erreur : l'alarme reste désarmée.
- Cause probable (lecture du cœur Jeedom 4.6, `cmd.class.php`, `alreadyInState`, actif par défaut) : la commande de mode est liée à l'info Mode ; l'info étant déjà à la valeur visée, le cœur n'appelle pas le plugin. Le plugin alarm lui-même armerait.
- En production, l'alarme est désarmée sur un mode qui est aussi celui d'une clé Homebridge : l'armement correspondant depuis HA serait ignoré.
- Contrainte : ne jamais modifier les types génériques ni la configuration Jeedom (pas de désactivation de `alreadyInState`).

### Écart 2 (mineur) — ancien mode affiché ~40 ms

- À chaque armement, l'info Actif passe à 1 avant que l'info Mode soit mise à jour ; chaque événement publie un état calculé : HA voit `armed_away` (ancien mode) puis `armed_home`.
- Les événements arrivent par `/action/state_update` (listener PHP `stateListener` → `callDaemon`, réponse non lue par le PHP), un appel par info.

### Faits établis dans le code (`ea1b4a2`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | La traduction d'un armement est synchrone et choisit la cible dans `alarm_arm_targets(commands)` (modes d'abord, sinon `ALARM_ENABLE` / `ALARM_ARMED`). | `sync/command.py::_translate_alarm_command`, `mapping/alarm_control_panel.py` |
| F2 | La commande d'activation (`ALARM_ARMED` plugin alarm, `ALARM_ENABLE` virtuel) reste dans `mapping.commands` sous la clé de son generic type même quand des modes sont retenus. | `AlarmControlPanelMapper.map` |
| F3 | Une lecture fraîche d'une info Jeedom existe déjà : `CommandSynchronizer._read_info_value` (`cmd::execCmd` sur l'info, sans effet), utilisée par le garde de portail 24.7 juste avant l'envoi. | `sync/command.py` |
| F4 | Les libellés de mode des clés Homebridge sont dans `reason_details["alarm_mode_labels"]` (`alarm_mode_labels(mapping)`), comparés avec `normalize_alarm_mode_label` ; l'info Actif se lit avec `_alarm_flag`. | `mapping/alarm_control_panel.py`, `sync/readback.py` |
| F5 | Chaque événement d'info d'alarme alimente le magasin unique `_alarm_reads` puis publie aussitôt l'état calculé (pairs lus dans le magasin). | `sync/state.py::handle_state_message`, `_translate_alarm_value` |
| F6 | #419 : un échec de publication d'état d'alarme n'est jamais silencieux (WARNING `mqtt_publish_failed` sur le chemin des événements ; comptage aux republications). | `sync/state.py` |

## Critères d'acceptation

1. **AC1 — Même mode, alarme désarmée** : pour un armement dont la cible est une commande de mode, le démon relit à l'instant de l'ordre (lecture fraîche, F3) les infos Mode et Actif. Si le Mode lu, le libellé de la clé SetMode* et le nom de la commande de mode visée sont égaux une fois normalisés (revue I1) et qu'Actif vaut 0, il exécute la **commande d'activation** de l'équipement (`ALARM_ARMED`, sinon `ALARM_ENABLE` ; action de ce generic type, commande de l'équipement) au lieu de la commande de mode.
2. **AC2 — Même mode, déjà armée** : Mode = mode demandé et Actif = 1 → aucune commande Jeedom, ordre accepté, INFO `alarm_already_armed_in_mode` ; HA garde l'état déjà publié.
3. **AC3 — Autres cas, comportement inchangé** (la commande de mode est envoyée comme en 12.4) : autre mode courant ; configuration Homebridge incohérente (libellé de la clé différent du nom de la commande de mode visée, revue I1) ; Mode illisible, null, vide ou inconnu ; Actif illisible ou null ; lecture fraîche en échec ; mode demandé sans libellé ; armement sans configuration de mode (la cible est déjà la commande d'activation) ; désarmement.
4. **AC4 — Alarme sans commande d'activation** : même mode et alarme désarmée mais aucune commande d'activation valable → la commande de mode est envoyée (inchangé, au cas où le cœur ne l'ignore pas) avec un WARNING `alarm_same_mode_without_enable_command` qui dit que l'ordre peut être ignoré par Jeedom.
5. **AC5 — Lecture fiable** : jamais de décision sur une valeur mémorisée (magasin, topologie) : une valeur ancienne pourrait faire activer l'alarme dans un autre mode que celui demandé. Aucun libellé de mode ni valeur lue n'est journalisé.
6. **AC6 — Regroupement des changements de l'alarme (écart 2)** : un événement d'une info d'alarme ne publie plus immédiatement ; il alimente le magasin et programme, si aucune n'est en attente pour ce topic, une publication unique après une courte fenêtre fixe (`ALARM_STATE_COALESCE_S`, 0,25 s) ; la publication calcule l'état depuis le magasin (dernières valeurs des quatre infos) et le publie en retained. Délai borné (fenêtre fixe depuis le premier événement, pas de report glissant).
7. **AC7 — Non-régression du regroupement** : seuls les topics d'alarme sont regroupés, les autres types publient immédiatement comme avant ; un échec de publication reste un WARNING `mqtt_publish_failed` ; broker indisponible au moment de la publication → INFO `mqtt_unavailable` ; l'équipement dépublié entre-temps → rien publié ; le retour à `unknown` (payload `None`) suit la même règle qu'en 12.4 ; arrêt du démon : les publications en attente sont **publiées tout de suite** (vidage, `flush_pending_states`, avant l'arrêt du broker), puis un drapeau d'arrêt fait partir tout nouvel état d'alarme sans minuteur (revue M1, M2) ; `published: true` est rendu par anticipation pour un événement regroupé (docstring, revue M3) ; fenêtre à 0 = comportement immédiat d'avant.
8. **AC8 — Tests** rouges puis verts : même mode désarmé, même mode armé, autre mode, mode inconnu / null, Actif illisible, lecture en échec, sans commande d'activation, sans configuration de mode ; regroupement (deux événements → une seule publication, état final ; autres types immédiats ; échec de publication journalisé). Suites pytest, flake8, PHP, Node (garde 25.4, lignes remplacées déclarées si besoin) vertes.
9. **AC9 — Preuve terrain (hors session cloud, ClaudeBox / porteur du projet)** : sur la démo, alarme désarmée sur le mode X, armer X depuis HA → armée en X ; armer X une seconde fois → rien ; HA n'affiche plus l'ancien mode à l'armement.
10. **AC10 — Pas d'armement d'une alarme déclenchée ou en délai d'entrée (décision du porteur du projet, 2026-11-23)** : avant tout armement (`ARM_HOME` / `ARM_AWAY` / `ARM_NIGHT`, par mode ou générique, plugin alarm ou virtuel), le démon relit Statut (`ALARM_STATE`) puis Immédiat (`immediatState`) par lecture fraîche. Statut = 1 → refus `alarm_arm_refused_triggered` ; Immédiat = 1 → refus `alarm_arm_refused_pending` ; lecture en échec, null ou illisible → refus `alarm_arm_refused_state_unreadable` ; valeur vide → refus `alarm_arm_refused_state_empty` (revue I-a) ; plugin alarm sans Statut identifiable (generic type ou logicalId `state`) → refus `alarm_arm_refused_no_status_info` (revue m1) ; lectures en parallèle, résultat identique à une lecture séquentielle (revue m3). Refus = WARNING avec le code de raison, sans valeur ni libellé ; aucune commande envoyée ; le dernier état publié pendant le run est republié (retained) pour que HA garde ou retrouve l'état réel (rien de recalculé ni d'inventé ; rien publié pendant le run → rien). Une info absente de l'équipement (virtuel sans Statut, alarme sans Immédiat) n'est pas lue : ce n'est pas un échec. Le désarmement n'est pas concerné.
    - **Pourquoi refuser quand la lecture échoue** : le plugin alarm remet le déclenchement à zéro à un changement de mode ; armer une alarme dont on ne sait pas si elle est déclenchée pourrait donc annuler un déclenchement sans code. Le refus ne coûte qu'un nouvel essai ; l'erreur inverse coûte la sécurité.

## UI Impact

- **UI Impact:** Non — aucun changement d'interface Jeedom ; côté HA, l'armement fonctionne et l'état ne clignote plus.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — **hors session cloud** (CLAUDE.md : jamais `deploy-to-box.sh` ni accès box/HA) ; à ClaudeBox / porteur du projet
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
- [x] Task 1 — Tests rouges (AC8)
- [x] Task 2 — Écart 1 (AC1 à AC5)
  - [x] 2.1 `mapping/alarm_control_panel.py` : `alarm_enable_command(commands)` (miroir de `alarm_disarm_command`) et rôle du mode visé
  - [x] 2.2 `CommandTranslation` : champ facultatif `alarm_target_state` posé seulement pour une cible de mode
  - [x] 2.3 `CommandSynchronizer._resolve_alarm_same_mode` (async, lecture fraîche Mode puis Actif) appelé dans `handle_command_message` avant l'exécution
- [x] Task 3 — Écart 2 (AC6, AC7) : `StateSynchronizer` — regroupement par topic d'alarme, publication différée, annulation à l'arrêt
- [x] Task 4 — Tests verts, flake8, PHP, Node (garde 25.4)
- [x] Task 5 — Documentation (`docs/fr_FR/index.md`, paragraphe alarme), sprint-status
- [x] Task 7 — Corrections de la relecture indépendante de #420 et décision AC10 (voir « Review Findings »)
- [ ] Task 6 — Preuve terrain AC9 (hors session cloud)
  - [ ] relever la version de PHP de la box, la casse exacte du nom des commandes de mode et du libellé des clés Homebridge, et la valeur de `cmd::allowCheckState` (option `alreadyInState`) pour les commandes de mode (revue M4)
  - [ ] armer X dans le mode X désarmé, réarmer X, vérifier l'absence d'ancien mode à l'armement
  - [ ] pour reproduire le défaut d'avant (écart 1), utiliser aussi un nom de mode tout en minuscules (revue m6)
  - [ ] AC10 : alarme déclenchée ou en délai d'entrée sur la démo, « Armer » depuis HA → refusé, HA garde l'état ; désarmer avec le code

## Dev Notes

- **Ordre de lecture** : Mode d'abord ; s'il ne correspond pas, on n'a pas besoin d'Actif (une seule lecture dans le cas courant « autre mode »).
- **Pas de verrou ni d'état supposé** : l'ordre reste confirmé par l'état diffusé (`real_state_confirmation`).
- **Activer arme dans le mode courant** : le plugin alarm active l'alarme dans son mode courant, qui est ici le mode demandé (vérifié par la lecture fraîche).
- **Fenêtre de regroupement** : 0,25 s couvre l'écart observé (~40 ms) avec marge, sans retard perceptible ; l'état `triggered` est retardé d'au plus 0,25 s (acceptable : la sirène et les notifications sont côté Jeedom). La programmation est non bloquante : la réponse HTTP à PHP part tout de suite (les deux événements peuvent arriver l'un après l'autre).
- **Fenêtre inévitable (revue m2)** : entre la relecture de Statut / Immédiat et l'envoi de l'ordre, un déclenchement peut survenir sans être vu ; elle dure au plus le temps des lectures et de l'envoi (lectures en parallèle : un délai de requête, 2 s par défaut, au pire). Aucun verrou côté Jeedom ne permet de la fermer depuis le démon ; le désarmement exige toujours le code.
- **Tests 12.4** : ils vérifient le calcul de l'état, pas le délai ; ils tournent avec la fenêtre à 0 (fixture du fichier de test), les tests 12.5 couvrent la fenêtre.

### Dev Agent Guardrails

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`
- Session cloud : aucun déploiement, aucun accès box / HA (CLAUDE.md).

### Project Structure Notes

- Démon seulement : `mapping/alarm_control_panel.py`, `sync/command.py`, `sync/state.py`, `main.py` ou `transport/http_server.py` si l'arrêt doit annuler les publications en attente.
- Tests : `resources/daemon/tests/unit/test_story_12_5_alarme_armement_meme_mode.py` (nouveau) ; fixture de fenêtre à 0 dans `test_story_12_4_alarme_etat_mode.py`.

### References

- [Source: _bmad-output/implementation-artifacts/12-4-alarme-etat-et-armement-par-mode.md] (AC1, AC4, AC9, Dev Notes)
- [Source: _bmad-output/implementation-artifacts/24-7-*.md] (lecture fraîche juste avant l'envoi, I3)
- [Source: _bmad-output/project-context.md] (préférer l'état réel relu ; ne jamais mentir sur l'état)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée, 2026-11-23).

### Debug Log References

- Branche `fix/alarm-arm-same-mode` depuis `origin/main` `ea1b4a2`.
- Cycle rouge vérifié : avec `sync/command.py`, `sync/state.py` et `main.py` de `main`, 15 tests de 12.5 échouent (même mode désarmé, déjà armée, autre mode, sans commande d'activation, échec d'activation, regroupement, arrêt) ; tous verts après correction.

### Implementation Plan

- **Écart 1** : `_translate_alarm_command` pose `alarm_target_state` quand la cible est une commande de mode (`is_mode_command`). Dans `handle_command_message`, avant l'envoi, `_resolve_alarm_same_mode` relit Mode (`_read_info_value`, `cmd::execCmd` sur l'info, sans effet) ; s'il égale le libellé du mode visé (normalisé), relit Actif : 0 → commande d'activation (`alarm_enable_command` : `ALARM_ARMED`, sinon `ALARM_ENABLE`, action de l'équipement) ; 1 → rien envoyé, ordre accepté (INFO `alarm_already_armed_in_mode`) ; sinon (et pour tout échec, null, illisible, libellé ou info absents) → commande de mode inchangée. Sans commande d'activation : commande de mode + WARNING `alarm_same_mode_without_enable_command`.
- **Écart 2** : `StateSynchronizer._schedule_alarm_publication` — par topic d'alarme, un minuteur `loop.call_later(ALARM_STATE_COALESCE_S = 0,25 s)` posé au premier événement (fenêtre fixe, non glissante) ; les événements suivants mettent seulement le magasin à jour. `_flush_alarm_publication` relit la cible dans le registre, calcule l'état depuis le magasin et publie (retained) avec les mêmes journaux qu'avant (`mqtt_publish_failed` en WARNING, `mqtt_unavailable`, `state_target_not_found`, retour à `unknown`). `flush_pending_states()` publie l'attente à l'arrêt du démon (`main.on_stop`, avant l'arrêt du broker). Fenêtre à 0 = publication immédiate.

### Completion Notes List

- AC1 à AC8 faits et testés ; AC9 (preuve terrain) et Task 0 restent à ClaudeBox / porteur du projet.
- Points tranchés :
  1. **Lecture fraîche seulement** : jamais de décision sur le magasin ni la topologie (une valeur ancienne pourrait activer l'alarme dans un autre mode que celui demandé) ; lecture en échec → comportement de 12.4.
  2. **Alarme sans commande d'activation** : la commande de mode part quand même (si `alreadyInState` est désactivé sur la commande, elle marche) avec un WARNING qui dit que l'ordre peut être ignoré.
  3. **Déjà armée dans le mode** : l'ordre est accepté (retour vrai) sans commande ; HA garde l'état retenu, déjà juste.
  4. **Réponse à `/action/state_update`** : un événement d'alarme regroupé compte comme publié (`published: true`) ; le PHP ne lit pas cette réponse ; l'échec éventuel est journalisé en WARNING à la publication, comme avant.
  5. **Nom générique** `flush_pending_states` dans `main.py` : le test 12.4 « le code n'est jamais en ligne de commande » interdit le mot « alarm » dans `main.py`.
  6. **Tests 12.4** : fixture `_immediate_alarm_state` (fenêtre à 0) et lecture fraîche simulée en échec dans `_cmd_sync` (pas d'appel réseau) ; aucun test 12.4 retiré ni changé de sens.
- Suites après la passe de relecture : pytest 3795 passés, 37 ignorés, 1 échec intermittent sans lien (`tests/unit/test_deploy_safety_rollback.py`, vert 3 fois sur 3 isolé, script de déploiement non touché) ; flake8 vert ; PHP 23 verts, `php -l` vert ; Node 1649 / 1652, les 3 échecs `25.4 AC8` préexistants (garde-fou périmé, PR séparée).
- Suites après la deuxième relecture : pytest 3809 passés, 37 ignorés ; flake8 vert ; PHP 23 verts, `php -l` vert ; Node 1649 / 1652 (3 échecs `25.4 AC8` préexistants, PR séparée) ; tests de 12.5 : 77 (10 rouges sur `c6624ba`).
- **Passe de relecture (#420) et AC10** : I1 (concordance libellé de clé / nom de la commande de mode visée), AC10 (refus d'armer une alarme déclenchée, en délai d'entrée ou illisible ; dernier état republié), M1 à M5. Les tests de 12.4 simulent maintenant Statut et Immédiat relus à 0 (sinon tout armement serait refusé, AC10) ; 29 tests de 12.5 rouges sur le commit précédent, 64 verts.
- Latence ajoutée : armement par mode = une à deux lectures JSON-RPC (délai de requête du démon, 2 s par défaut, au pire) ; état d'alarme publié au plus 0,25 s après le premier changement.
- Suites (premier passage) : pytest 3767 passés, 37 ignorés ; `flake8 resources/daemon tests` vert ; PHP : `php -l` vert sur tous les fichiers, 23 tests autonomes verts (3 exigent un vrai cœur Jeedom, ignorés comme en CI) ; Node 1652 tests, 1649 passés, 3 échecs préexistants (`test_story_25_4_ecritures_deplacees.node.test.js`, AC8 : rouge aussi sur `main` non modifié) ; garde 25.4 (AC31) : une ligne remplacée déclarée (`REPLACED_BY_12_5`).

### File List

- `_bmad-output/implementation-artifacts/12-5-alarme-armement-meme-mode.md` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/fr_FR/index.md`
- `resources/daemon/main.py`
- `resources/daemon/mapping/alarm_control_panel.py`
- `resources/daemon/sync/command.py`
- `resources/daemon/sync/state.py`
- `resources/daemon/tests/unit/test_story_12_4_alarme_etat_mode.py`
- `resources/daemon/tests/unit/test_story_12_5_alarme_armement_meme_mode.py` (nouveau)
- `tests/unit/test_story_25_4_non_regression.node.test.js`

## Senior Developer Review (AI)

Revue adverse `bmad-code-review` du 2026-11-23 (même session que le développement : pas de contexte neuf, écart à la recommandation du workflow), sur le diff `main...fix/alarm-arm-same-mode`.

- AC1 à AC8 : implémentés, preuves dans `test_story_12_5_alarme_armement_meme_mode.py` (35 tests à cette revue ; 64 après la passe de relecture et AC10). AC9 terrain : hors session cloud.
- File List conforme au diff git.

### Constats retenus (corrigés)

- [x] [AI-Review][Medium] La publication regroupée est appelée par la boucle (minuteur) : une exception y finissait dans le gestionnaire d'exceptions d'asyncio, hors du format `[SYNC-STATE]`. Elle est attrapée et journalisée en WARNING `mqtt_publish_failed` (test ajouté) [sync/state.py].
- [x] [AI-Review][Low] Cas « pas d'info Mode sur l'équipement » non testé : test ajouté (aucune lecture, commande de mode inchangée).

### Constats écartés (avec raison)

- [Low] L'identifiant JSON-RPC de `_read_info_value` reste `jeedom2ha-barrier-read` pour la lecture de l'alarme : cosmétique, la fonction est partagée et inchangée (dépôt en gel).
- [Low] Une republication (naissance HA, sync, « Publier ») pendant la fenêtre publie depuis le même magasin, puis la publication regroupée republie la même valeur : doublon sans effet.
- [Low] Le cœur Jeedom pourrait aussi ignorer « Activer » si Actif valait déjà 1 : ce cas est exclu (Actif relu à 0 juste avant).

## Review Findings (relecture indépendante de #420, 2026-11-23, verdict OK)

- [x] [Review][Important] **I1** `sync/command.py` — la substitution par « Activer » ne vérifiait que le libellé de la clé SetMode* : une configuration Homebridge incohérente (clé Présent pointant vers la commande d'un autre mode) aurait armé dans le mauvais mode. Corrigé : la valeur relue de Mode, le libellé de la clé et le nom de la commande de mode visée doivent concorder (normalisés), sinon comportement de 12.4 ; incohérence détectée avant toute lecture du mode. Test `test_inconsistent_homebridge_configuration_keeps_the_12_4_behaviour`.
- [x] [Review][Décision] **AC10** (porteur du projet) — refus de tout armement d'une alarme déclenchée ou en délai d'entrée, et quand Statut / Immédiat ne se relisent pas (choix sûr) ; WARNING sans valeur ; dernier état publié republié. `_alarm_arm_refusal`, `StateSynchronizer.republish_last_alarm_state`, 25 tests, `docs/fr_FR/index.md`.
- [x] [Review][Minor] **M1** — texte d'AC7 aligné sur le code (vidage à l'arrêt, pas annulation).
- [x] [Review][Minor] **M2** — drapeau d'arrêt posé par `flush_pending_states` : ensuite, publication immédiate (test).
- [x] [Review][Minor] **M3** — docstring de `handle_state_message` : `published: true` anticipé pour un événement regroupé.
- [x] [Review][Minor] **M4** — Task 6 (preuve terrain) : relever la version de PHP, la casse des noms de mode et `cmd::allowCheckState`.
- [x] [Review][Minor] **M5** — marges des tests de fenêtre élargies (fenêtre de test 0,2 s ; test de fenêtre fixe à 0,3 s avec 75 ms de marge de chaque côté).
- Hors périmètre (consigne du coordinateur) : les 3 échecs Node `25.4 AC8`, garde-fou périmé sur `main`, traités dans une PR séparée.

### Deuxième relecture indépendante de `c6624ba` (2026-11-23, OK pour fusion ; Codex : rien)

- [x] [Review][Important] **I-a** — Statut ou Immédiat vide (`""`, info jamais écrite) donnait un refus « illisible, réessayez » qui se répète sans fin : refus gardé avec un code distinct `alarm_arm_refused_state_empty` ; doc : « si le refus se répète, vérifiez que Statut et Immédiat ont une valeur (0) dans Jeedom ». Tests : vide sur chaque info, virtuel jamais écrit.
- [x] [Review][Minor] **m1** — plugin alarm : Statut retrouvé aussi par son logicalId `state` (topologie), comme Immédiat ; plugin alarm sans Statut identifiable → refus `alarm_arm_refused_no_status_info` (AC10 non contournable par un generic type retiré). Plugin alarm reconnu par la topologie (`eq_type_name`) ou, sans topologie, par l'info Immédiat retenue. Mapper inchangé (dépôt en gel : la publication de l'état n'est pas touchée). Tests : Statut par logicalId, sans Statut (avec et sans topologie), virtuel sans Statut non bloqué.
- [x] [Review][Minor] **m2** — fenêtre inévitable entre la lecture de Statut et l'envoi : documentée (Dev Notes, doc utilisateur, docstring).
- [x] [Review][Minor] **m3** — Statut et Immédiat lus en parallèle (`asyncio.gather`), résultats évalués dans l'ordre Statut puis Immédiat : même résultat qu'en séquentiel (priorité `triggered`, Statut en échec l'emporte sur Immédiat à 1) ; délai maximal ramené à un délai de requête (2 s par défaut) au lieu de deux. Tests : parallélisme, équivalence séquentielle.
- [x] [Review][Minor] **m4** — INFO `alarm_same_mode_config_mismatch` (sans libellé) quand le repli I1 s'applique. Tests.
- [x] [Review][Minor] **m5** — doc : « si la relecture de Mode ou d'Actif échoue ».
- [x] [Review][Minor] **m6** — Task 6 : nom de mode tout en minuscules pour reproduire le défaut d'avant.
- Hors périmètre (consigne du coordinateur) : garde 25.4 AC8 périmé et faux `jq` de `test_deploy_safety_rollback.py`, PR séparée.

## Change Log

- 2026-11-23 : création (create-story), développement (dev-story), revue (code-review) — session cloud déléguée.
- 2026-11-23 : corrections de la relecture indépendante de #420 (I1, M1 à M5) et AC10 (décision du porteur du projet : pas d'armement d'une alarme déclenchée ou en délai d'entrée).
- 2026-11-23 : corrections de la deuxième relecture de `c6624ba` (I-a, m1 à m6).
