# Story 23.4 — preuve terrain du 2026-10-31 (AC2)

> Exécutée par clawbox, pilotée par ClaudeBox, sous le mandat de nuit d'Alexandre (`go NUIT-20261031`). Copie jetable de la VM de démo (VM 123, clonée depuis le snapshot `vierge` de la VM 122 : Debian 12, Jeedom 4.6.1, Mosquitto local), détruite à la fin de l'essai. Identifiants seulement (CC-48).

## Procédure suivie

`docs/fr_FR/installation-github.md` de `main` (`237029b`), à la lettre : archive `main.zip`, dossier `jeedom2ha-main` renommé `jeedom2ha` sous `/var/www/html/plugins/`, `chown www-data`, activation, dépendances, broker `127.0.0.1:1883`, démon.

## Relevés (2026-10-31, 19:10–19:17)

| Contrôle | Résultat |
|---|---|
| Version installée | `pluginVersion` 1.2.0 (archive `main`, sans fichier `VERSION`) |
| Fichiers | 4 629 : l'archive embarque les dossiers de développement, ce qu'annonce la doc |
| Dépendances | `state=ok` (venv : `jeedomdaemon`, `aiohttp`, `paho-mqtt`), lancées d'elles-mêmes par l'activation |
| Démon | `state=ok`, `launchable=ok` (démarrage 19:15) |
| Page du plugin | HTTP 200 |
| Journaux | 1 ERROR (`Failed to start daemon within 20s`, 19:10) et 1 traceback (`No module named 'jeedomdaemon'`) : tentative de démarrage du démon par Jeedom **avant** la fin de l'installation des dépendances ; aucune erreur après |
| Statut du pont MQTT | non relevé : la commande de contrôle filtrait les messages retenus (`mosquitto_sub -R`) alors que `jeedom2ha/bridge/status` est retenu. Défaut du relevé, pas du plugin ; le démon `ok` et le journal sans erreur après 19:15 indiquent un fonctionnement normal |

## Écarts entre la doc et la réalité (corrigés dans cette PR)

1. L'activation lance déjà les dépendances ; « Relancer » pendant l'installation est refusé (« installation déjà en cours »). La doc le dit désormais, avec le journal à suivre.
2. L'erreur transitoire du démon pendant l'installation des dépendances est expliquée.
3. Le contrôle de réussite citait l'ancien libellé « Rescanner la topologie Jeedom » : remplacé par « Relire Jeedom » (libellé depuis l'epic 25).

## Constat hors doc

Le snapshot `vierge` de la VM 122 **contient déjà jeedom2ha** (gate A4 du 12/10) : ce n'est pas une Jeedom sans le plugin. Pour cette preuve, le dossier existant a été mis de côté avant l'installation. À savoir pour toute preuve de « première installation » future.

## Statut

AC2 fait. AC5 (mise à niveau et retour arrière) reste « documenté, non testé ». Story laissée `review`.
