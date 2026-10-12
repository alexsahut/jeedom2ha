# Gate A4 — Jeedom vierge (2026-10-12)

## Contexte

- Exécuté par clawbox (agent infra) sous le go d'Alex (Telegram, msg-id 11558), supervisé par ClaudeBox.
- Objet : valider le paquet de distribution Market (A2) et la conformité d'activation sur Jeedom vierge (A3).

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

Ce gate ferme en `done` : A2 (paquet distribuable) et A3 (conformité Market). Voir `sprint-status.yaml` et les fichiers de story correspondants.

## AC5 d'A1

AC5 amendé par décision Alex 2026-10-12 15:17 (D8 = a) : la charge réelle sur Jeedom vierge n'a pas été testée par ce gate, mais la charge réelle est prouvée sur la box (292 équipements réels, box en `69a4b47`, `[RELAY-BUDGET] relais=TOPOLOGY R=60 duration_s=1.811`) et en CI par `test_story_a1_parc_300_load.py` (300 équipements, vrai serveur HTTP). Le présent gate A4 sur Jeedom vierge couvre l'installation, les dépendances et le démon. A1 est `done` — voir `sprint-status.yaml` et la story correspondante.
