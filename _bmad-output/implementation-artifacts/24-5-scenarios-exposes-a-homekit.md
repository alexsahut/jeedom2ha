# Story 24.5 : Scénarios exposés à HomeKit

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **R1 (ClaudeBox, 12/10) intégrée : la cause de l'écart est établie, la story se réduit à documenter et à vérifier que les scénarios sont dans l'export (24.2).** Aucun changement de production. Décision d'Alexandre : **Q8 A** (garder `button`) est confirmée par les faits ; B et C ne sont plus à l'ordre du jour. Relecture de ClaudeBox obligatoire avant `ready-for-dev`. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel de scénario (CC-48) : identifiants seulement.

## Story

En tant que mainteneur de la parité,
je veux que les cinq scénarios déclenchés par la voix dans Apple Maison soient lisibles dans le contrat de décision et que la cause de leur écart soit documentée,
afin que la mesure ne les compte plus « non projetés » à tort et que l'exposition à Assist reste un geste côté Home Assistant.

**Parcours : documentation + preuve par l'export. Pas de code de production.**

## Dépendances et décisions

- Dépend de **24.2** (les scénarios sont dans l'export avec `homekit_exposed`, issu de 24.1).
- **Q8 A** : garder `button` (84 boutons existants inchangés).

## Établi par ClaudeBox le 12/10 (lecture seule)

Les cinq scénarios 20, 38, 50, 57 et 150 sont **actifs** dans Jeedom et **leurs boutons existent dans le registre de HA**, mais ils sont **non exposés à Assist** (`should_expose: false`) ; l'outil de parité de ClaudeBox **ne lit pas les boutons de scénario**. Hypothèses de la proposition (section 6) : **H-a et H-d confirmées** ; H-b (inactifs), H-c (type attendu) et H-e (jointure par numéro) écartées. L'exposition à Assist est un geste côté HA, hors plugin (exigence 5).

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Tout scénario **actif** reçoit un bouton `jeedom2ha_scenario_<id>` ; un scénario inactif n'en a pas, et depuis 21-1 un bouton existant est retiré. | `transport/http_server.py:2134-2158` ; `mapping/button.py:44-65` |
| F2 | Les scénarios sont hors du contrat de décision, du périmètre publié, du cache disque, du diagnostic et de l'outil de parité : c'est la cause (H-a). | `http_server.py:2129-2190`, `:4716` ; `tools/parity_snapshot.py` |
| F3 | Aucun des cinq identifiants ne recoupe un identifiant d'équipement parmi les 15 cas mesurés (preuve 21-1). | `21-1-preuve-terrain-2026-10-11.md` |

## Critères d'acceptation proposés

- **AC1.** L'export de 24.2 contient, pour les identifiants 20, 38, 50, 57 et 150, une ligne `kind: scenario` avec `active`, `homekit_exposed`, `decision`, `unique_id` (`jeedom2ha_scenario_<id>`) et `entity_id_expected` ; la comparaison avec le registre de HA se fait sur `unique_id`. Vérifié par ClaudeBox sur l'export « avant ».
- **AC2.** La documentation de développement dit que l'écart « scénarios non projetés » était un artefact de mesure et qu'un scénario est projeté en `button` dès qu'il est actif ; la clé de jointure est `kind` + `key` (`scenario:<id>`) ou `unique_id`.
- **AC3.** Aucun changement de ce qui est publié ; inventaire MQTT et registres de HA identiques avant/après ; aucune ouverture de composant (`scene` hors périmètre tant que Q8 reste A).
- **AC4.** Si l'export montre un des cinq scénarios inactif ou sans bouton (contre la mesure du 12/10), la story s'arrête et le signale à ClaudeBox et Alexandre avant tout code.
- **AC5.** Aucun nom de scénario dans le dépôt (CC-48).

## Tâches proposées

- [ ] **Task 0 — Vérifier sur l'export « avant »** (ClaudeBox) : les cinq lignes de AC1.
- [ ] **Task 1 — Documentation** (AC2) et clôture ; mise à jour du référentiel de parité de ClaudeBox hors dépôt (lecture des boutons de scénario).

## Garde-fous

- Le plugin ne modifie jamais l'exposition à Assist : l'exposer est un geste côté HA, par l'humain.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Le traitement par Assist d'un `button` (D4) : seulement utile si B ou C est un jour envisagée.
