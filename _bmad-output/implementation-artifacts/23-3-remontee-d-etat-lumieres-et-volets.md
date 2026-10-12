# Story 23.3 : Remontée d'état des lumières et volets

Status: draft

> Brouillon. Relecture ClaudeBox obligatoire avant `ready-for-dev`.

## Story

En tant qu'utilisateur HA, je veux voir l'état réel des lumières et la position des volets, afin d'éviter les états optimistes ou absents avant la bêta Market.

## Critères d'acceptation proposés

1. La vague streaming inclut `LIGHT_STATE`/luminosité et `FLAP_STATE`/position sans régression sensor, binary_sensor, switch.
2. Les payloads MQTT publient états compatibles; action et retour convergent sans boucle ni état périmé.
3. Tests unitaires/intégration/parité: changement d'état, luminosité, position, commandes absentes et golden.
4. Preuve 23.1: lumière variable et volet positionnable, inventaire MQTT/HA avant-après.
5. README et `docs/fr_FR/index.md` « Limites » distinguent couverture et limites restantes.
6. Une lumière ou un volet sans commande d'état Jeedom reste optimiste; la discovery n'envoie `optimistic: false` que lorsqu'un état réel existe, et cette règle figure dans « Limites ».

## Tâches proposées

- [ ] **Prérequis :** 23.1 fournit lumière variable et volet positionnable synthétiques; CC-48 s'applique aux fixtures, preuves et PR.
- [ ] Revalider `_STREAMED_TYPES`, publishers et types génériques actuels.
- [ ] Définir contrat état/brightness/position et dégradations.
- [ ] Implémenter listener, routage, publication et tests/parité; prouver sur 23.1.
- [ ] Mettre à jour Limites; ne pas ouvrir climate/alarm.
