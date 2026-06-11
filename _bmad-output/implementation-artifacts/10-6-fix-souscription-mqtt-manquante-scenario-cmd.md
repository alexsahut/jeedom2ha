# Story 10.6 : Fix — souscription MQTT manquante pour les commandes de scénario

Status: done

## Story

En tant qu'utilisateur,
je veux que le clic sur un bouton de scénario dans Home Assistant déclenche réellement le scénario Jeedom,
afin que mes raccourcis d'ambiance (cinema, coucher, etc.) soient actionnables depuis HA.

## Acceptance Criteria

**AC1 — Le daemon souscrit au topic de commande des scénarios**
**Given** le daemon démarré avec connexion MQTT établie
**When** le bootstrap MQTT s'exécute
**Then** le client paho est souscrit au topic `jeedom2ha/+/cmd` (QoS 1), couvrant les scénarios `scenario_<id>`

**AC2 — Le clic sur le bouton HA déclenche le scénario Jeedom**
**Given** le daemon déployé avec le fix et les 5 scénarios publiés
**When** l'utilisateur appuie sur un bouton de scénario dans HA (ex : `ambiance cinema`)
**Then** le daemon reçoit le message MQTT sur `jeedom2ha/scenario_38/cmd`
**And** `_handle_scenario_command` est appelé et renvoie `True`
**And** le log daemon affiche `reason_code=scenario_started action=execute_scenario_command`

**AC3 — Gate terrain : preuve d'exécution observable**
**Given** le déploiement sur box réelle avec le fix
**When** l'utilisateur clique sur `ambiance cinema` dans HA
**Then** le log Jeedom ou le log daemon attestent de l'exécution du scénario id=38

**AC4 — Non-régression : les entités existantes (light, switch, cover, climate) ne sont pas affectées**
**Given** le fix appliqué
**When** les tests unitaires existants tournent
**Then** tous passent sans modification

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Cause racine identifiée : `COMMAND_SUBSCRIPTION_TOPICS` absent de `jeedom2ha/+/cmd` (donc aucun `scenario_<id>/cmd`)
  - [x] Gate terrain box réelle exécuté (voir Task 3)

- [x] Task 1 — Corriger la souscription MQTT (AC: 1, 2)
  - [x] Ajouter `"jeedom2ha/+/cmd"` à `COMMAND_SUBSCRIPTION_TOPICS` dans `transport/mqtt_client.py`

- [x] Task 2 — Tests unitaires (AC: 1, 4)
  - [x] `test_story_10_6_fix_scenario_subscription.py` : vérification que le topic est dans la liste
  - [x] Non-régression : tests existants inchangés

- [x] Task 3 — Validation terrain et traçabilité de sortie (AC: 2, 3)
  - [x] Deploy via `scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Déclenchement commande scénario `jeedom2ha/scenario_38/cmd` (équivalent clic bouton HA)
  - [x] Vérifier log daemon : `reason_code=scenario_started action=execute_scenario_command eq_id=scenario_38`
  - [x] Vérifier log Jeedom : scénario id=38 exécuté (`scenarioLog/scenario38.log`, trigger API)

- [x] Task 4 — Clôture BMAD story-level (AC: 1, 2, 3, 4)
  - [x] Statut story → `done`
  - [x] Synchroniser `sprint-status.yaml`
  - [x] Passer en `done` après gate terrain

## Dev Notes

### Cause racine

`COMMAND_SUBSCRIPTION_TOPICS` dans `transport/mqtt_client.py` (lignes 27-31) ne contenait
que les topics `/set`, `/brightness/set`, `/position/set`. Le topic de commande `/cmd`
(`jeedom2ha/+/cmd`, couvrant `scenario_<id>/cmd`) était absent. Le daemon n'était donc
jamais souscrit à ces topics MQTT, donc les messages envoyés par HA à la pression d'un
bouton de scénario n'arrivaient jamais au `CommandSynchronizer`.

### Composants touchés

- `resources/daemon/transport/mqtt_client.py` — `COMMAND_SUBSCRIPTION_TOPICS` (ajout d'une ligne)

### Composants non touchés (déjà corrects)

- `resources/daemon/sync/command.py` — `_SCENARIO_CMD_TOPIC_RE` + `_handle_scenario_command` + `_execute_scenario_start` : logique correcte, simplement jamais atteinte
- `resources/daemon/mapping/button.py` — `ScenarioButtonMapper` : `command_topic` correct
- `resources/daemon/discovery/publisher.py` — `_build_button_payload` : payload discovery correct

### Dev Agent Guardrails

- Ne toucher que `COMMAND_SUBSCRIPTION_TOPICS` — aucune autre modification dans `mqtt_client.py`.
- Ne pas étendre le scope à `jeedom2ha/+/cmd` (eqLogic buttons) sauf si une carte de travail dédiée existe.
- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Référence cycle terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.

### References

- [Source: `resources/daemon/transport/mqtt_client.py#COMMAND_SUBSCRIPTION_TOPICS`]
- [Source: `resources/daemon/sync/command.py#_SCENARIO_CMD_TOPIC_RE`]
- [Source: `_bmad-output/implementation-artifacts/10-1-verification-et-completion-du-chemin-button-pour-les-5-scenarios-homekit-visibles.md`]

## Dev Agent Record

### Agent Model Used

claude-cli/claude-sonnet-4-6

### Debug Log References

- Cause racine identifiée par lecture directe de `mqtt_client.py` lignes 27-31 vs `command.py` ligne 21
- Gate terrain 2026-06-10 :
  - daemon `/var/www/html/log/jeedom2ha_daemon`
    - `[SYNC-CMD] eq_id=scenario_38 topic=jeedom2ha/scenario_38/cmd reason_code=scenario_started action=execute_scenario_command` (00:52:01)
    - `[SYNC-CMD] eq_id=scenario_38 topic=jeedom2ha/scenario_38/cmd reason_code=scenario_started action=execute_scenario_command` (00:52:45)
  - Jeedom `/var/www/html/log/scenarioLog/scenario38.log`
    - `-- Début : ... "#trigger#":"api" ... "Scénario exécuté sur appel API"` (00:52:01 et 00:52:45)
    - `Fin correcte du scénario`

### Completion Notes List

- 2026-06-10 : Story 10.6 créée via workflow BMAD create-story (bug report workboard card).
  Cause racine : `COMMAND_SUBSCRIPTION_TOPICS` absent de `jeedom2ha/+/cmd`.
  Fix : ajout d'une ligne dans `COMMAND_SUBSCRIPTION_TOPICS`.
- 2026-06-10 : Gate terrain exécuté (deploy + preuve logs daemon + preuve log Jeedom scénario 38). AC1→AC4 validés.

### File List

- `_bmad-output/implementation-artifacts/10-6-fix-souscription-mqtt-manquante-scenario-cmd.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/transport/mqtt_client.py`
- `resources/daemon/tests/unit/test_story_10_6_fix_scenario_subscription.py`

## Change Log

- 2026-06-10 — Story 10.6 créée. Bug remonté par utilisateur (workboard card) : clic ambiance cinema → rien.
  Cause racine identifiée.
- 2026-06-10 — Fix déployé sur box de test + gate terrain PASS.
  Preuves: log daemon `[SYNC-CMD] ... scenario_started` et `scenarioLog/scenario38.log` (trigger API + fin correcte). Statut : done.
