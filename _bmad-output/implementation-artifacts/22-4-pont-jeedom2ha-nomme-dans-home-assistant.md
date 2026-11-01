# Story 22.4 : le pont jeedom2ha apparaît sous son nom dans Home Assistant

Status: ready-for-dev

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

- [ ] Task 1 : publication de la découverte du pont (AC1, AC2)
- [ ] Task 2 : exclusions (AC3) et tests (AC4)
- [ ] Task 3 : documentation (AC6)
- [ ] Task 4 : preuve terrain sur la démo, puis en production (AC5), par ClaudeBox et clawcode
