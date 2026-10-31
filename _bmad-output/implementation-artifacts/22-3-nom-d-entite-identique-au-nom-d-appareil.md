# Story 22.3 : Nom d'entité identique au nom d'appareil

Status: review

> Rattachée à l'epic 22 (noms Home Assistant = noms Jeedom, suite de 22-1). `pe-epic-22` reste `in-progress`. Story créée et développée par une session cloud déléguée (sans accès box, HA ni secret). Aucun nom réel d'équipement, de pièce, de scénario ou de personne (CC-48) : identifiants seulement.

## Story

En tant qu'utilisateur qui pilote sa maison par la voix (Assist),
je veux qu'une entité dont le nom est celui de son appareil s'affiche sous ce seul nom,
afin qu'Assist la retrouve sous le nom Jeedom que je connais.

**Parcours : démon uniquement** (discovery MQTT). Aucun écran ne change.

## Constat (ClaudeBox, 2026-10-12 vers 19:25, lecture seule des registres de HA)

- **131 entités** publiées par le plugin ont un nom d'entité identique au nom de leur appareil : HA affiche un nom doublé « X X ».
- Il s'agit de **85 boutons de scénario** et de **46 entités d'équipement** (équipements 240, 603, 242, 457, 219, 98, 496, 527 ; commandes 4807 et 4786, entre autres).
- Conséquence : Assist ne trouve pas l'entité sous son nom. Essai du 12/10 : `HassTurnOn` avec le nom du scénario 38 donne `MatchFailedError`, alors que son bouton est exposé à Assist.

## Cause

`resources/daemon/discovery/publisher.py` : depuis 22-1 (Q1 A), `_build_device_block` nomme l'appareil avec le nom Jeedom de l'équipement (ou `mapping.ha_name` pour un scénario). Chaque constructeur de payload publie aussi `"name": mapping.ha_name`. Quand les deux sont égaux, HA les concatène. Cela inclut l'entité principale d'un équipement à plusieurs entités (précision Q2 A de 22-1 : elle garde le nom de l'équipement).

## Critères d'acceptation

- **AC1.** Quand le nom d'entité est égal au nom de l'appareil (comparaison après normalisation des espaces et de la casse), le payload publie `"name": null` (convention HA : l'entité prend seulement le nom de l'appareil).
- **AC2.** Un seul helper (`DiscoveryPublisher._entity_name_for_payload`) est utilisé par tous les constructeurs de payload : lumière, volet, interrupteur, capteur, capteur binaire, climat, alarme, bouton.
- **AC3.** Si les noms diffèrent, rien ne change (équipement à plusieurs entités : les entités secondaires gardent le nom de leur commande).
- **AC4.** Aucun changement d'`unique_id`, d'`object_id`, de `default_entity_id`, de topics, d'identifiants d'appareil, d'éligibilité ni de décision ; les `entity_id` restent ceux du registre de HA. Le contrat 4D est inchangé.
- **AC5.** Le golden (traces MQTT figées de 19-4) ne change que sur le champ `name` des entités concernées ; le diff est montré dans la PR.
- **AC6.** `transport/http_server.py` et `desktop/` ne sont pas touchés (22-2 attend la validation UX d'Alexandre).
- **AC7.** Aucun nom réel dans le code, les tests, la story, la PR (CC-48).

## Tâches

- [x] **Task 1 — Helper** `_normalize_name` + `_entity_name_for_payload` dans `publisher.py` et remplacement de `"name": mapping.ha_name` dans les 8 constructeurs (AC1-AC3).
- [x] **Task 2 — Tests** : `tests/unit/test_story_22_3_nom_entite_identique_appareil.py` (helper : noms égaux, casse, espaces, noms différents, nom vide ; bouton de scénario ; équipement à une entité ; équipement à plusieurs entités) ; tests existants réalignés (22-1, 21-1 référence figée du bouton, 9-1, 9-2).
- [x] **Task 3 — Golden** : traces `*_mqtt.json` de `story_19_4_guard` régénérées (`JEEDOM2HA_GUARD_REGEN=1`) ; diff vérifié champ par champ contre les anciennes (AC5).
- [x] **Task 4 — Suites complètes** comme la CI (pytest `tests` + `resources/daemon/tests`, tests `load`, `flake8`, `node --test`, tests PHP autonomes).
- [x] **Task 5 — Documentation** : entrée dans `docs/fr_FR/changelog_beta.md`.
- [ ] **Task 6 — Preuve terrain (ClaudeBox puis Alexandre, après fusion et déploiement)** : voir ci-dessous.
  - [x] Part ClaudeBox (2026-10-20, `ae84d6e`, lecture seule) : `22-3-preuve-terrain-2026-10-20.md`.
  - [ ] Essai vocal du scénario 38 par Alexandre.

## Preuve attendue (ClaudeBox, après déploiement)

1. Les 131 entités ont pour nom affiché celui de leur appareil.
2. Aucun `entity_id`, appareil ni entité créé, supprimé ou renommé dans son identifiant.
3. Inventaire MQTT identique en nombre.
4. Essai vocal du scénario 38 par Alexandre.

## Dev Agent Record

### Implementation Plan / notes

- `_entity_name_for_payload(mapping, device)` compare `mapping.ha_name` au `device["name"]` effectivement publié (donc le nom d'équipement, ou le nom du scénario pour un bouton), après `" ".join(str.split()).casefold()`. Égalité → `None`, sinon `ha_name` inchangé. Le bloc `device` est calculé une fois par payload, le helper n'appelle rien d'autre.
- Choix : un nom d'entité vide face à un nom d'appareil non vide reste tel quel (comportement antérieur).
- Équipement à plusieurs entités : seule l'entité principale (nom d'équipement) devient `null` ; les mesures gardent le nom de leur commande.

### Golden — diff limité au champ `name`

Les 4 traces modifiées (`s1`, `s2`, `s3`, `s5`) comportent **164** différences champ par champ contre les anciennes, **toutes** de la forme `payload.name : "<nom>" → null` ; aucune autre différence (les traces `s4` et `s6` sont identiques). La référence figée du bouton de scénario (test 21-1) change aussi uniquement sur `name`.

### Vérifications locales

- `python -m pytest` (suite de la CI : `tests` + `resources/daemon/tests`) : 2257 passed, 2 skipped, 8 deselected ; tests `load` : 8 passed.
- `flake8 resources/daemon tests` : propre. `node --test tests/unit/*.node.test.js` : 476 pass, 0 fail. Tests PHP autonomes : tous OK (les 3 qui exigent un cœur Jeedom sont ignorés comme dans la CI).
- `scripts/deploy-to-box.sh` et le gate 20-0 non lancés (session cloud).

### Change Log

- 2026-10-12 : create-story et dev-story ; statut `review`.

### File List

- `_bmad-output/implementation-artifacts/22-3-nom-d-entite-identique-au-nom-d-appareil.md` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/operations/delegations.md`
- `docs/fr_FR/changelog_beta.md`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/tests/fixtures/story_19_4_guard/{s1,s2,s3,s5}_*_mqtt.json`
- `resources/daemon/tests/unit/test_story_9_1_sensor_mapper.py`, `test_story_9_2_binary_sensor_mapper.py`
- `tests/unit/test_story_22_1_noms_jeedom.py`, `test_story_21_1_cc44_scenario_lifecycle.py`
- `tests/unit/test_story_22_3_nom_entite_identique_appareil.py` (nouveau)
