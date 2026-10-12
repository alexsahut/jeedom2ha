# Gate A4 — Jeedom vierge (2026-10-12)

## Contexte

- Exécuté par ClaudeBox sous le go d'Alex (Telegram, msg-id 11558).
- Objet : valider le paquet de distribution Market (A2) et la conformité d'activation sur Jeedom vierge (A1 T5, A3).

## Construction du paquet

- Construit avec `scripts/build-market-package.sh` depuis `main` (`b1acad7`).
- 75 fichiers, manifeste respecté.
- Premier niveau du paquet : `3rdparty`, `LICENSE`, `core`, `desktop`, `docs`, `plugin_info`, `resources`.
- `pluginVersion` : 1.2.0.

## VM jetable Debian 12 / Jeedom 4.6.1

- Activation : dépendances installées automatiquement (state ok).
- Démon : ok.
- MQTT : `jeedom2ha/bridge/status=online` sur Mosquitto local.
- Journaux : 0 ERROR.

## VM jetable Debian 11.11 / Python 3.9.2

- Dépendances : ok.
- Démon : ok.
- MQTT : non testé (pas de broker disponible sur cette VM ; décision ClaudeBox).
- Journaux : 4 « error » bénignes dans `jeedom2ha_packages` (purge du cache pip vide, avertissements gpg).

## Remarques

- Le journal du démon reste vide au niveau de log par défaut.
- Les deux VM sont revenues éteintes à l'issue du gate ; une seule a été allumée à la fois.

## Portée

Ce gate ferme en `done` : A1 (tâche T5, gate terrain), A2 (paquet distribuable) et A3 (conformité Market). Voir `sprint-status.yaml` et les fichiers de story correspondants.
