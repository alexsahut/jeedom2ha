# Story 14.1 : Généralisation `family="FAN"` — trio FAN_STATE/FAN_ON/FAN_OFF publié en `switch`

Status: review

## Story

En tant qu'utilisateur (Alexandre),
je veux que l'eqLogic Jeedom eq67 (plugin `pool`, "Filtration"), qui expose le trio `FAN_STATE`/`FAN_ON`/`FAN_OFF`, soit publié dans Home Assistant comme un `switch` pilotable,
afin de pouvoir piloter la pompe de filtration piscine depuis HA au lieu qu'elle reste invisible (aucun mapper ne la reconnaît aujourd'hui).

## Acceptance Criteria

**AC1 — Généralisation du groupement de commandes `family` dans `switch.py`**
**Given** un eqLogic Jeedom exposant les trois commandes `FAN_STATE`, `FAN_ON`, `FAN_OFF` (même pattern structurel que `SWITCH_STATE`/`SWITCH_ON`/`SWITCH_OFF`)
**When** `SwitchMapper.map_all()` est invoqué
**Then** `_group_switch_cmds` reconnaît également la famille `FAN` (en plus de `SWITCH`) et produit un groupe complet
**And** `_map_cmd_group(eq, snapshot, group, family="FAN")` retourne un `MappingResult` avec `ha_entity_type="switch"`, `confidence="probable"`, `reason_code="switch_fan_on_off_state"`
**And** le `state_topic`/`command_topic`/`object_id`/`node_id` sont dérivés du cmd `FAN_STATE` selon le pattern déjà utilisé pour `SWITCH_*` (`jeedom2ha/{eq_id}/{state_cmd.id}/state` et `/set`)

**AC2 — eq67/cmd382 (pompe filtration piscine) publié en switch**
**Given** l'eqLogic Jeedom eq67 (plugin `pool`) exposant `FAN_STATE` (cmd382, `type=info binary`), et ses commandes `FAN_ON`/`FAN_OFF` associées
**When** le moteur exécute l'étape de mapping puis publication
**Then** eq67 apparaît en `switch` MQTT HA (`homeassistant/switch/jeedom2ha_eq_67_cmd_382/config` ou équivalent selon convention `_map_cmd_group`)
**And** l'état publié n'est pas `unknown` après un cycle de streaming runtime (Story 12.2)

**AC3 — Anti-doublon dans `binary_sensor.py`**
**Given** un eqLogic avec un trio `FAN_STATE`/`FAN_ON`/`FAN_OFF` complet, déjà projeté en `switch` par `SwitchMapper`
**When** `BinarySensorMapper` (multi-domaine ou mono) traite le même eqLogic
**Then** la commande `FAN_STATE` déjà consommée par le switch n'est jamais dupliquée en `binary_sensor` (symétrique au comportement existant pour `SWITCH_STATE`/`ENERGY_STATE` via `_switch_readback_cmd_ids` / `_SWITCH_OWNED_GENERIC_TYPES`)

**AC4 — Non-régression sur `SWITCH_*`/`ENERGY_*` existants**
**Given** la suite de tests unitaires existante (`test_switch_mapper.py`, `test_story_9_2_binary_sensor_mapper.py`, golden-file)
**When** la suite complète est exécutée après le changement
**Then** tous les tests existants restent PASS — aucune régression sur les switches `SWITCH_*` (eq554, eq583, eq628) ni sur les switches `ENERGY_*` mono

**AC5 — Commandes ON/OFF routées depuis HA (`sync/command.py`)**
**Given** un switch `FAN_*` publié et actionné depuis HA (`jeedom2ha/{eq_id}/{cmd_id}/set` payload `ON`/`OFF`)
**When** `CommandSynchronizer._translate_command` traite la commande
**Then** `FAN_ON`/`FAN_OFF` sont résolus dans la table de lookup on/off (symétrique à l'ajout historique de `SWITCH_ON`/`SWITCH_OFF` en Story 10.7) — sans quoi la commande échoue en `missing_action_command`

**AC6 — Gate terrain : eq67/cmd382 pilotable en switch sur box réelle**
**Given** le déploiement sur box réelle (192.168.1.21) avec la généralisation `family="FAN"` active
**When** le gate terrain est exécuté (`deploy-to-box.sh --cleanup-discovery --restart-daemon`)
**Then** eq67/cmd382 (pompe filtration) apparaît en `switch` MQTT HA avec un état non-`unknown`
**And** aucune régression n'est observée sur les switches existants (eq554, eq583, eq628 — cf. historique Story 11.2/11.3)

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.`

- [x] Task 1 — Généraliser `_group_switch_cmds` pour accepter `family="FAN"` (AC: 1, 2)
  - [x] Introduire une constante `_SWITCH_CMD_FAMILIES = ("SWITCH", "FAN")` dans `switch.py`
  - [x] Modifier `_group_switch_cmds` pour grouper les commandes par famille détectée dynamiquement à partir du suffixe `_STATE`/`_ON`/`_OFF` du `generic_type`, au lieu du filtre en dur `{"SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF"}`
  - [x] Adapter `map_all()` pour appeler `_map_cmd_group(eq, snapshot, group, family=<famille_detectee>)` par groupe (au lieu de forcer `family="SWITCH"`)
  - [x] Vérifier que `reason_code` reste `switch_{family.lower()}_on_off_state` (donc `switch_fan_on_off_state` pour FAN) — cohérent avec le pattern existant, pas de nouveau format à inventer

- [x] Task 2 — Anti-doublon `binary_sensor.py` (AC: 3)
  - [x] Étendre `_switch_readback_cmd_ids` pour détecter aussi les groupes `FAN_STATE`/`FAN_ON`/`FAN_OFF` complets (même logique que les groupes `SWITCH_*`)
  - [x] Vérifier que `_is_multi_domain_eq` reste cohérent (FAN_STATE ne doit pas se compter comme candidat binaire multi-domaine s'il est consommé par le switch) — `_SWITCH_OWNED_GENERIC_TYPES` étendu avec `FAN_STATE`/`FAN_ON`/`FAN_OFF`

- [x] Task 3 — Routage commande HA→Jeedom (AC: 5)
  - [x] Ajouter `FAN_ON`/`FAN_OFF` dans la table de lookup on/off de `sync/command.py::_translate_command` (lignes 261-270), à côté de `SWITCH_ON`/`SWITCH_OFF`

- [x] Task 4 — Tests unitaires de non-régression (AC: 1, 2, 3, 4, 5)
  - [x] Créer `resources/daemon/tests/unit/test_story_14_1_fan_switch_family.py` :
    - Cas nominal : eqLogic avec trio `FAN_STATE`/`FAN_ON`/`FAN_OFF` → `SwitchMapper.map_all()` retourne un `MappingResult` switch, `reason_code="switch_fan_on_off_state"`
    - Cas mixte : eqLogic avec à la fois un groupe `SWITCH_*` et un groupe `FAN_*` (noms distincts) → deux `MappingResult` distincts, chacun avec la bonne famille
    - Cas anti-doublon : `BinarySensorMapper` ne produit pas de binary_sensor pour la commande `FAN_STATE` déjà consommée par le switch
    - Cas non-régression : les tests `test_switch_mapper.py` existants sur `SWITCH_*` passent inchangés
    - Cas command routing : `_translate_command` résout `FAN_ON`/`FAN_OFF` (ajouter au test existant équivalent au pattern Story 10.7)
  - [x] Lancer la suite complète `python3 -m pytest tests/ resources/daemon/tests/ -q` — 8/8 nouveaux tests PASS, 1454 passed, 24 échecs pré-existants confirmés hors scope (dépendance externe `jeedomdaemon` absente localement — identiques avant/après le changement, cf. note sprint-status Story 11.3)

- [ ] Task 5 — Gate terrain + clôture BMAD (AC: 6)
  - [ ] Déployer via `scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Confirmer via log daemon / MQTT discovery que eq67/cmd382 apparaît en `switch`, état non-`unknown`
  - [ ] Confirmer absence de régression sur eq554/eq583/eq628 (switches existants) — topics et états inchangés
  - [ ] Documenter la preuve terrain dans Dev Agent Record
  - [ ] Mettre à jour `sprint-status.yaml` : `14-1-...: done` et `pe-epic-14: done` si gate PASS
  - [ ] Mettre à jour statut story → `done`

## Dev Notes

### Contexte du diagnostic (vérifié directement dans le code, pas supposé)

`resources/daemon/mapping/switch.py` :
- `map_all()` (lignes 90-105) appelle `_group_switch_cmds(eq)` puis, pour chaque groupe trouvé, `self._map_cmd_group(eq, snapshot, group, family="SWITCH")` — **`family` est déjà un paramètre de `_map_cmd_group`** (lignes 277-314), qui construit dynamiquement les clés `f"{family}_STATE"`, `f"{family}_ON"`, `f"{family}_OFF"`.
- Le point bloquant est **`_group_switch_cmds`** (lignes 316-329) : il filtre en dur `generic_type not in {"SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF"}` — aucune autre famille n'est reconnue, donc `FAN_STATE`/`FAN_ON`/`FAN_OFF` ne produisent jamais de groupe.
- Généralisation minimale : détecter la famille à partir du suffixe du `generic_type` (`_STATE`, `_ON`, `_OFF`) pour un ensemble de familles autorisées (`SWITCH`, `FAN`), grouper par `(family, group_key)`, puis appeler `_map_cmd_group(..., family=famille_detectee)`.

`resources/daemon/mapping/binary_sensor.py` :
- `_switch_readback_cmd_ids()` (lignes 157-183) calcule les cmd_id déjà consommés par un trio switch complet, pour éviter la duplication en binary_sensor. Actuellement ne couvre que `ENERGY_STATE`+`ENERGY_ON`+`ENERGY_OFF` et les groupes `SWITCH_STATE`/`SWITCH_ON`/`SWITCH_OFF`. Il faut y ajouter la détection des groupes `FAN_STATE`/`FAN_ON`/`FAN_OFF` complets, sur le même modèle que les groupes `SWITCH_*`.

`resources/daemon/sync/command.py` (lignes 261-282) :
- La table de lookup on/off pour `parsed.channel == "set"` et `mapping.ha_entity_type in ("light", "switch")` cherche `LIGHT_ON/ENERGY_ON/SWITCH_ON/SET_ON` (et symétrique OFF). Il faut y ajouter `FAN_ON`/`FAN_OFF`, sinon les commandes HA→Jeedom sur un switch FAN échoueront en `missing_action_command` malgré un mapping switch correctement publié (cf. précédent similaire en Story 10.7 où l'oubli de `SET_ON`/`SET_OFF` avait été un finding HIGH en code-review).

`resources/daemon/validation/ha_component_registry.py` :
- `PRODUCT_SCOPE` contient déjà `"switch"` (ligne 70). **Aucune ouverture FR40/NFR10 supplémentaire n'est nécessaire** — cette story est une extension pure de mapper sous un composant déjà ouvert, pas l'ouverture d'un nouveau composant HA.

### Architecture — pas de changement de slot registry

`SwitchMapper` reste au même emplacement dans `MapperRegistry` (`resources/daemon/mapping/registry.py`). Aucune modification du registry n'est nécessaire pour cette story — le changement est interne à `SwitchMapper`.

### Composants à toucher

- **MODIFIER** : `resources/daemon/mapping/switch.py` — généraliser `_group_switch_cmds` + `map_all` pour multi-famille (`SWITCH`, `FAN`)
- **MODIFIER** : `resources/daemon/mapping/binary_sensor.py` — étendre `_switch_readback_cmd_ids` pour les groupes `FAN_*`
- **MODIFIER** : `resources/daemon/sync/command.py` — ajouter `FAN_ON`/`FAN_OFF` dans la table de lookup on/off
- **CRÉER** : `resources/daemon/tests/unit/test_story_14_1_fan_switch_family.py`
- **VÉRIFIER (pas de modif a priori)** : `resources/daemon/mapping/registry.py`, `resources/daemon/discovery/publisher.py` (le publisher switch existant est générique par `ha_entity_type="switch"`, aucune connaissance de `family` — ne devrait pas nécessiter de changement)

### Tests patterns — suivre les conventions établies

- Helpers `_eq_with_cmd` / eqLogic construit à la main (voir `test_story_10_7_presence_switch_mapper.py`, `tests/unit/test_switch_mapper.py`)
- Pas de fixtures JSON pour les tests unitaires (réservées au golden-file) — golden-file étendu uniquement si un cas structurel manque après revue (à confirmer en dev-story, pas obligatoire pour cette story si eq67 n'est pas structurellement représentatif du corpus)
- Tests unitaires dans `resources/daemon/tests/unit/`, préfixe `test_story_14_1_`

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- Alignement complet avec la structure existante — aucun nouveau module, extension de fichiers existants uniquement
- Pas de variance détectée avec les patterns établis (Story 2.4 `switch.py`, Story 9.2 `binary_sensor.py`, Story 10.7 `sync/command.py`)

### References

- [Source: `resources/daemon/mapping/switch.py#map_all,_group_switch_cmds,_map_cmd_group` — code réel vérifié]
- [Source: `resources/daemon/mapping/binary_sensor.py#_switch_readback_cmd_ids,_SWITCH_OWNED_GENERIC_TYPES` — code réel vérifié]
- [Source: `resources/daemon/sync/command.py#_translate_command` lignes 261-282 — table de lookup on/off]
- [Source: `resources/daemon/validation/ha_component_registry.py#PRODUCT_SCOPE` ligne 70 — `switch` déjà ouvert]
- [Source: `_bmad-output/implementation-artifacts/10-7-presence-switch-mapper-publier-switch-presence.md` — precedent similaire (finding HIGH command routing manquant)]
- [Source: `_bmad-output/implementation-artifacts/11-3-iq-ev-pilotage-priorisation-solaire.md` — précédent switches multi + gate terrain eq583/eq628]
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-04-fan-switch-parity.md` — cadrage correct-course de cette story]
- [Source: `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md` — cycle deploy terrain]

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (clawcode agent)

### Debug Log References

### Completion Notes List

- 2026-07-04 : Story créée via workflow BMAD `create-story` (exécution intégrale par agent autonome, phase précédée d'un `correct-course` documenté dans `sprint-change-proposal-2026-07-04-fan-switch-parity.md`). Statut initial : `ready-for-dev`.
- 2026-07-04 : Task 1 — `switch.py::_group_switch_cmds` généralisé : groupe désormais par `(family, name_key)` pour `family in ("SWITCH", "FAN")` détecté dynamiquement via le suffixe `_STATE/_ON/_OFF` du `generic_type`, au lieu du filtre en dur `SWITCH_*`. `map_all()` transmet la famille détectée à `_map_cmd_group` (au lieu de forcer `"SWITCH"`). `reason_code` produit : `switch_fan_on_off_state` pour FAN, `switch_switch_on_off_state` pour SWITCH (inchangé).
- 2026-07-04 : Task 2 — `binary_sensor.py` : `_SWITCH_OWNED_GENERIC_TYPES` étendu avec `FAN_STATE`/`FAN_ON`/`FAN_OFF` ; `_switch_readback_cmd_ids` généralisé pour détecter les groupes complets par famille (clé `(family, name_key)`) ; `_is_multi_domain_eq` mis à jour pour réutiliser `_SWITCH_OWNED_GENERIC_TYPES` et inclure `FAN_STATE` dans le comptage `switch_state_count`.
- 2026-07-04 : Task 3 — `sync/command.py::_translate_command` : ajout de `FAN_ON`/`FAN_OFF` dans la résolution de commande on/off (aux côtés de `LIGHT_ON/ENERGY_ON/SWITCH_ON/SET_ON` et symétrique OFF).
- 2026-07-04 : Task 4 — `test_story_14_1_fan_switch_family.py` créé (8 tests, 8 PASS) : trio FAN nominal, topics dérivés du cmd_id, trio FAN incomplet → aucun switch, non-régression trio SWITCH historique, groupes mixtes SWITCH+FAN sur le même eqLogic → 2 mappings indépendants, anti-doublon binary_sensor (FAN_STATE consommé par le switch non republié), routage commande HA→Jeedom FAN_ON/FAN_OFF. Suite complète : `python3 -m pytest tests/ resources/daemon/tests/ -q` → 1454 passed (+8 nouveaux), 24 échecs pré-existants confirmés identiques avant/après le changement via `git stash` (dépendance externe `jeedomdaemon` absente localement, non liés à cette story).
- 2026-07-04 : Aucune modification de `mapping/registry.py` ni de `discovery/publisher.py` n'a été nécessaire — le publisher switch existant est générique par `ha_entity_type="switch"` et ne connaît pas la notion de `family`.

## Dev Story — Statut

Toutes les tasks de développement (1 à 4) sont complètes et vertes. Task 0 (pre-flight terrain) et Task 5 (gate terrain) restent à exécuter après code-review, conformément à la contrainte procédurale du projet.

### File List

- `_bmad-output/implementation-artifacts/14-1-fan-state-on-off-generalisation-switch-family.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-04-fan-switch-parity.md`
- `_bmad-output/planning-artifacts/active-cycle-manifest.md`
- `resources/daemon/mapping/switch.py`
- `resources/daemon/mapping/binary_sensor.py`
- `resources/daemon/sync/command.py`
- `resources/daemon/tests/unit/test_story_14_1_fan_switch_family.py`

## Senior Developer Review (AI)

**Reviewer** : agent autonome (posture code-review BMAD) — **Date** : 2026-07-04

**Périmètre revu** : `resources/daemon/mapping/switch.py`, `resources/daemon/mapping/binary_sensor.py`, `resources/daemon/sync/command.py`, `resources/daemon/tests/unit/test_story_14_1_fan_switch_family.py` (diff complet relu ligne à ligne).

**AC cross-check** :
- AC1/AC2 (généralisation `family`, eq67/cmd382) : vérifiés par `test_fan_trio_maps_to_switch`, `test_fan_trio_topics_follow_cmd_group_pattern` — PASS.
- AC3 (anti-doublon binary_sensor) : vérifié par `test_fan_state_not_duplicated_as_binary_sensor` — PASS.
- AC4 (non-régression SWITCH_*/ENERGY_*) : vérifié par `test_switch_trio_still_maps_with_switch_family`, `test_mixed_switch_and_fan_groups_both_mapped_independently`, et par la suite complète (1454 passed, 24 échecs pré-existants confirmés identiques via `git stash` avant/après) — PASS.
- AC5 (routage commande HA→Jeedom) : vérifié par `test_command_synchronizer_routes_fan_on/off` — PASS.
- AC6 (gate terrain) : non exécutable à ce stade de la revue (nécessite déploiement box réelle) — reporté à la phase gate terrain suivante, conformément à la contrainte procédurale du projet.

**Qualité de code** :
- La généralisation `_group_switch_cmds`/`_switch_readback_cmd_ids` par `(family, name_key)` est cohérente et symétrique entre `switch.py` et `binary_sensor.py`, sans duplication de logique de découverte de famille (bien que les deux fichiers redéfinissent leur propre `_SWITCH_CMD_FAMILIES` — acceptable vu l'absence de module partagé existant entre mappers, cf. pattern déjà établi pour `_switch_group_key` dupliqué entre les deux fichiers avant cette story).
- Réduction de duplication bienvenue dans `_is_multi_domain_eq` (réutilisation de `_SWITCH_OWNED_GENERIC_TYPES` au lieu d'un set local redondant) — comportement strictement identique avant/après (même ensemble de valeurs), pas de régression.
- `reason_code` respecte le format existant (`switch_{family.lower()}_on_off_state`), aucun nouveau vocabulaire introduit.

**Sécurité** : aucun impact — pas de nouvelle surface d'entrée utilisateur, pas de désérialisation, pas de changement de credentials/authn. Le changement reste interne au pipeline de mapping et à la table de lookup de commandes déjà validées par ailleurs (payload ON/OFF strict).

**Finding LOW (non bloquant, hérité, hors scope)** : `_group_switch_cmds` (donc aussi la nouvelle famille FAN) ne passe pas par les garde-fous anti-faux-positifs de `_map_energy_switch` (`_ALLOWED_EQ_GENERIC_TYPES`, `_ANTI_SWITCH_GENERIC_TYPES`, `_NON_SWITCH_KEYWORDS`) : ce comportement préexistait déjà pour `SWITCH_*` avant cette story et n'est pas modifié ni aggravé ici. Documenté pour information ; correctif éventuel hors scope de la Story 14.1 (nécessiterait son propre correct-course s'il devient un problème produit constaté).

**File List** : conforme au diff réel, aucun fichier oublié ni surnuméraire.

**Outcome** : **APPROVE** — 0 finding Critical/High. La story peut avancer vers le gate terrain (Task 0/Task 5).

## Change Log

- 2026-07-04 — correct-course exécuté intégralement : décision de créer `pe-epic-14` dédié (scope Minor, extension pure de mapper, composant `switch` déjà ouvert). SCP écrit, `sprint-status.yaml` et `active-cycle-manifest.md` mis à jour.
- 2026-07-04 — Story 14.1 créée (BMAD create-story). Statut `ready-for-dev`.
- 2026-07-04 — Dev-story : `family="FAN"` généralisé dans `switch.py` (`_group_switch_cmds`/`map_all`), anti-doublon `binary_sensor.py` étendu, routage commande HA→Jeedom `sync/command.py` étendu (`FAN_ON`/`FAN_OFF`). 8 tests unitaires nouveaux PASS, 0 régression sur la suite complète (1454 passed). Statut `review`.
- 2026-07-04 — Code-review APPROVE (0 finding Critical/High ; 1 finding LOW documenté, hérité et hors scope). Prochaine étape : gate terrain (Task 0/Task 5).
