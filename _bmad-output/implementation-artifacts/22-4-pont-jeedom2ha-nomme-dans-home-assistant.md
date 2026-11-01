# Story 22.4 : le pont jeedom2ha apparaît sous son nom dans Home Assistant

Status: review

> Créée par ClaudeBox le 2026-11-01 après la relecture des médias de 23.2. `ready-for-dev` accordé par Alexandre (« ok pour la petite story de correction », 01/11 à 09:55). Petite story corrective (S) de l'epic 22, consacré aux noms dans Home Assistant.

## Constat

Dans Home Assistant, chaque appareil publié par jeedom2ha affiche « Connecté via 127.0.0.1 ». Sur la démo, la liste des appareils montre en plus un appareil nommé « 127.0.0.1 », fabricant et modèle « inconnu ».

- **Cause.** `discovery/publisher.py` déclare `"via_device": "jeedom2ha_bridge"` pour chaque appareil, mais aucun message de découverte ne publie l'appareil `jeedom2ha_bridge`. Home Assistant crée alors un appareil vide pour cet identifiant et lui donne le titre de l'intégration MQTT, c'est-à-dire l'adresse du broker.
- **Effet chez l'utilisateur.** On voit l'IP ou le nom d'hôte de son broker, sans rapport avec Jeedom, et un appareil « inconnu » dans la liste.

## Story

En tant qu'utilisateur de jeedom2ha,
je veux que mes appareils Jeedom soient « Connectés via Jeedom (jeedom2ha) » dans Home Assistant,
afin de comprendre d'où ils viennent et de voir d'un coup d'œil si le pont est en ligne.

## Critères d'acceptation

1. **AC1. Appareil du pont publié.** Au démarrage, quand MQTT est connecté, le démon publie (retenu) la découverte d'une entité `binary_sensor`, `device_class: connectivity`, nommée « État du pont », avec :
   - `unique_id` `jeedom2ha_bridge_status` ;
   - `state_topic` `jeedom2ha/bridge/status`, avec `payload_on` `online` et `payload_off` `offline` (le topic de disponibilité déjà publié par le démon) ;
   - un appareil avec `identifiers: ["jeedom2ha_bridge"]`, `name: "Jeedom (jeedom2ha)"`, `manufacturer: "jeedom2ha"`, `model: "Pont Jeedom → Home Assistant"` et `sw_version` égal à la version du plugin.
2. **AC2. Rien d'autre ne change.** Les appareils et entités existants gardent leurs `unique_id`, `identifiers` et `via_device`. Aucune entité n'est retirée et aucune décision ne change. Seule la découverte du pont s'ajoute.
3. **AC3. Hors des équipements.** Le pont n'est pas un équipement Jeedom :
   - il n'entre pas dans les compteurs, l'export de décision ou la jauge ;
   - « Supprimer de Home Assistant » d'un équipement ou d'une pièce ne le retire pas ;
   - la suppression globale du plugin, si elle existe, le retire comme le reste.
4. **AC4. Tests.** Tests unitaires de la charge de découverte (topic, champs, retenu) et de la non-régression des `via_device`. Tests de l'exclusion des compteurs et de l'export. `flake8` propre.
5. **AC5. Preuve terrain**, d'abord sur la démo (VM 122), puis en production :
   - dans HA, un appareil « Jeedom (jeedom2ha) » existe ;
   - un appareil publié affiche « Connecté via Jeedom (jeedom2ha) » ;
   - l'état du pont passe à « Déconnecté » quand on arrête le démon, puis revient ;
   - l'ancien appareil « 127.0.0.1 » est renommé ou disparaît. Sinon, consigner la manipulation à faire dans HA.
6. **AC6. Documentation.** `docs/fr_FR/index.md` dit en une phrase ce qu'est l'appareil « Jeedom (jeedom2ha) » dans Home Assistant.

## Notes

- **Point à vérifier en AC5.** Home Assistant a déjà créé l'appareil vide `jeedom2ha_bridge` : la découverte devrait le compléter, nom compris, sauf s'il a été renommé à la main.
- Ne pas mettre de `availability_topic` sur cette entité, pour qu'elle reste lisible quand le pont est hors ligne.
- Budget de `getEquipmentStates` sans effet : le pont n'est pas un équipement.
- CC-48 : aucune valeur de broker dans la charge (ni hôte, ni port).

## Tâches

- [x] Task 1 : publication de la découverte du pont (AC1, AC2)
- [x] Task 2 : exclusions (AC3) et tests (AC4)
- [x] Task 3 : documentation (AC6)
- [ ] Task 4 : preuve terrain sur la démo, puis en production (AC5), par ClaudeBox et clawcode

## Dev Agent Record

### Implementation Plan / notes

- **Charge.** `DiscoveryPublisher.build_bridge_payload(plugin_version)` (fonction pure) et `publish_bridge(plugin_version)` dans `discovery/publisher.py`. Topic `homeassistant/binary_sensor/jeedom2ha_bridge/config`, QoS 1, retenu. Entité « État du pont », `unique_id` `jeedom2ha_bridge_status`, `device_class: connectivity`, `state_topic` = `BRIDGE_AVAILABILITY_TOPIC` (`jeedom2ha/bridge/status`), `payload_on`/`payload_off` = `AVAILABILITY_ONLINE`/`AVAILABILITY_OFFLINE`, c'est-à-dire `online`/`offline` : valeurs vérifiées dans `transport/mqtt_client.py` (birth sur `_on_connect`, LWT `will_set`, `stop()`). Pas d'`availability_topic`. Appareil `identifiers: ["jeedom2ha_bridge"]`, `name: "Jeedom (jeedom2ha)"`, `manufacturer: "jeedom2ha"`, `model: "Pont Jeedom → Home Assistant"`, sans `via_device` (pas d'autoréférence). Bloc `origin` comme les autres charges ; `object_id` et `default_entity_id` (`binary_sensor.jeedom2ha_bridge_status`) suivent la convention de 22.1.
- **`sw_version`.** Version du plugin lue par le démon dans `plugin_info/info.json` (`main._read_plugin_version`, déjà rangée dans `app["plugin_version"]` par 24.2). Omise si la version est illisible (`"inconnu"`) ou vide.
- **Moment de publication.** `transport/http_server._publish_bridge_discovery(app)` est appelée en tête des deux rappels injectés par `/action/mqtt_connect` : `_reconnect_cb` (déclenché par `MqttBridge._on_connect` à **chaque** connexion, la première au démarrage comprise, juste après le birth `online`) et `_ha_birth_cb` (redémarrage de HA). Elle précède donc la republication des équipements, et une erreur de publication du pont est journalisée sans bloquer celle-ci. Broker non connecté : rien n'est publié. La sync elle-même ne republie pas le pont.
- **Hors des équipements (AC3).** Par construction : rien n'est écrit dans `publications`, `topology`, `published_scope`, les compteurs, l'export ou les états agrégés. Les dépublications passent par l'id d'équipement (`jeedom2ha_<id>`) ou un `node_id` d'équipement/scénario ; `unpublish("jeedom2ha_bridge_status")` refuse (id non numérique) sans rien publier. Suppression globale du plugin : `jeedom2ha_remove()` (`plugin_info/install.php`) est vide, aucune purge globale n'existe côté plugin ; le mode `--stop-daemon-cleanup` / `--cleanup-discovery` du script de déploiement (dev seulement) vide les topics `homeassistant/+/+/config` contenant `/jeedom2ha_`, donc aussi celui du pont.
- **Diff du démon purement additif** (garde 25.4 / AC31) : le littéral `"via_device": "jeedom2ha_bridge"` et les docstrings des rappels sont inchangés.

### Vérifications locales

- `python -m pytest` (suite de la CI : `tests` + `resources/daemon/tests`) : 2536 passed, 1 skipped, 9 deselected (tests `load` exclus par défaut).
- `resources/daemon/tests/unit/test_story_22_4_pont_nomme.py` : 17 passed.
- `flake8 resources/daemon tests` : propre.
- `node --test tests/unit/*.node.test.js` : 1198 tests, 1195 pass, 0 fail, 3 skipped.
- `scripts/deploy-to-box.sh`, SSH, box et Home Assistant non utilisés (session cloud). Task 4 / AC5 non faits.

### Change Log

- 2026-11-01 : dev-story (session cloud déléguée) ; Tasks 1 à 3 ; statut `review`. Task 4 (preuve terrain) à ClaudeBox et clawcode.

### File List

- `resources/daemon/discovery/publisher.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_story_22_4_pont_nomme.py` (nouveau)
- `docs/fr_FR/index.md`
- `docs/fr_FR/changelog_beta.md`
- `_bmad-output/implementation-artifacts/22-4-pont-jeedom2ha-nomme-dans-home-assistant.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
