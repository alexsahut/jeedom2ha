# Preuve terrain 23.3 — 2026-10-13

## Périmètre et garde-fou

Preuve réalisée sur le jeu synthétique 23.1. Elle ne contient que des identifiants numériques, conformément à CC-48. Le relevé des topics MQTT est séparé : `parity-snapshot.sh` n'a pas été utilisé.

## Discovery

| Topic de discovery | Constat |
| --- | --- |
| `homeassistant/light/jeedom2ha_1/config` | `optimistic: false`; `state_topic`: `jeedom2ha/1/state` |
| `homeassistant/light/jeedom2ha_2/config` | `optimistic: false`; `state_topic`: `jeedom2ha/2/state`; `brightness_state_topic`: `jeedom2ha/2/brightness`; `brightness_scale`: 100 |

## Actions et retours

| Action HA | Retour Jeedom | Topic MQTT retained | Valeur |
| --- | --- | --- | --- |
| Équipement 1 allumé | Etat = 1 | `jeedom2ha/1/state` | `ON` |
| Équipement 2 à 60 % | Etat = 1 ; Luminosite = 60 | `jeedom2ha/2/state` ; `jeedom2ha/2/brightness` | `ON` ; `60` |
| Équipement 3 à 75 % | Position = 75 | `jeedom2ha/3/state` ; `jeedom2ha/3/position` | `open` ; `75` |

## Verdict

AC4 est satisfait : état, luminosité et position transitent par les remontées réelles, avec des discoveries non optimistes.
