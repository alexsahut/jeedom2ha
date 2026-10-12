# Story 24.5 : Scénarios exposés à HomeKit

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **La portée dépend de la mesure** : la story peut se terminer en simple correction de la mesure, sans code de production. Décision attendue d'Alexandre : **Q8** (type HA des scénarios) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel de scénario (CC-48) : identifiants seulement.

## Story

En tant qu'utilisateur qui déclenche cinq scénarios par la voix dans Apple Maison,
je veux savoir pourquoi ils ne sont pas comptés comme projetés dans Home Assistant et, s'il y a un vrai manque, le combler,
afin que ces scénarios se déclenchent par Assist.

**Parcours : démon, éventuellement ouverture d'un composant.** Pas d'écran sauf si Q8 B ou C.

## Dépendances et décisions

- Dépend de **24.2** (les scénarios sont dans l'export) et de la **baseline**.
- **Q8** : A recommandée (garder `button`) ; B (`scene` pour les scénarios exposés) ; C (`scene` pour tous, en remplacement). B et C ouvrent un composant (FR40/NFR10) et ne sont décidées qu'après la mesure.

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Tout scénario **actif** reçoit un bouton `jeedom2ha_scenario_<id>` ; un scénario inactif n'en a pas, et depuis 21-1 un bouton existant est retiré. | `transport/http_server.py:2134-2158` ; `mapping/button.py:44-65` |
| F2 | Les cinq scénarios HomeKit sont les identifiants 20, 38, 50, 57 et 150 (story 10-1) ; aucun ne recoupe un identifiant d'équipement parmi les 15 cas mesurés (preuve 21-1). | `10-1-verification-et-completion-du-chemin-button-pour-les-5-scenarios-homekit-visibles.md` ; `21-1-preuve-terrain-2026-10-11.md` |
| F3 | Les scénarios sont hors du contrat de décision, du périmètre publié, du cache disque, du diagnostic et de l'outil de parité. | `http_server.py:2129-2190`, `:4716` ; `tools/parity_snapshot.py` |
| F4 | Le référentiel de HomeKit décrit ces scénarios comme des **interrupteurs HomeKit**. Un `button` HA est sans état. | `homebridge-homekit-vs-ha-delta-2026-06-07.md` ; `discovery/publisher.py:722-750` |
| F5 | `scene.mqtt` est un composant MQTT documenté, absent du registre et de `PRODUCT_SCOPE`. | `_bmad-output/planning-artifacts/ha-projection-reference.md` (tableau des composants) ; `validation/ha_component_registry.py:26-70` |

## Hypothèses à départager (proposition, section 6)

H-a artefact de mesure (rien n'est lisible dans le contrat) ; H-b un ou plusieurs scénarios inactifs ; H-c type attendu `switch`/`scene` ; H-d projetés mais non exposés à Assist (côté HA) ; H-e jointure par numéro.

## Critères d'acceptation proposés

- **AC1.** À partir de l'export « avant » (24.2) et des registres de HA relevés par ClaudeBox, l'écart des cinq scénarios est **classé** par identifiant dans l'une des causes H-a à H-e (ou une autre, nommée), avec la preuve. Le résultat est versé au dépôt (identifiants seulement).
- **AC2.** Si la cause est une erreur de mesure (H-a, H-d, H-e) : aucun code de production ; le référentiel de ClaudeBox est corrigé hors dépôt ; la story se clôt par la preuve et la documentation de la clé de jointure (`kind` + `key` de l'export).
- **AC3.** Si la cause est l'inactivité (H-b) : aucun code ; la documentation dit qu'un scénario désactivé n'a pas de bouton (comportement décidé en 21-1) ; Alexandre décide s'il active les scénarios concernés.
- **AC4.** Si la cause est le type attendu (H-c) et que Q8 est B ou C : ouverture gouvernée de `scene` dans le même incrément (entrée de registre, mapper, cas nominal et cas d'échec de `validate_projection()`, contrat 4D non régressé), `default_entity_id` sur le nouveau payload (règle de 22-1), une seule voie par scénario (remplacement du bouton, pas coexistence), inventaire avant/après et liste des références à l'ancien `entity_id`.
- **AC5.** Un scénario reste déclenchable depuis HA après la story (essai par ClaudeBox) ; la commande reste routée par `jeedom2ha/scenario_<id>/cmd` ou son successeur documenté ; `sync/command.py` n'est modifié que si le type change.
- **AC6.** Les scénarios inactifs ne reçoivent toujours pas d'entité ; la purge « le broker fait foi » de 21-1 est inchangée.
- **AC7.** Aucun nom de scénario dans le dépôt (CC-48) ; aucun changement de ce qui est publié si AC2 ou AC3.

## Tâches proposées

- [ ] **Task 0 — Mesure (ClaudeBox, lecture seule)** : pour les cinq identifiants, relever `is_active` dans Jeedom, la présence de `homeassistant/button/jeedom2ha_scenario_<id>/config` dans l'inventaire MQTT, l'entité dans le registre de HA et son exposition à Assist ; relever la règle de type attendu du référentiel ; relever comment Assist traite un `button` et une `scene` (documentation officielle, D4).
- [ ] **Task 1 — Classer l'écart** (AC1) et décider avec Alexandre (Q8).
- [ ] **Task 2 — Seulement si B ou C** : ouverture de `scene` ; sinon, clôture documentaire.
- [ ] **Task 3 — Preuve terrain** (humain) : export « après », déclenchement d'un scénario.

## Garde-fous

- Pas d'ouverture de composant avant la mesure.
- Le plugin ne modifie jamais l'exposition de ces entités à Assist.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Toutes les causes de la section « Hypothèses » : cette session n'a pas accès à la box ; le traitement d'un `button` et d'une `scene` par Assist n'est pas vérifié.
