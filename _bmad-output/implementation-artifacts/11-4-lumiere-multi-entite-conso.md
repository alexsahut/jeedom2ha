# Story 11.4: Lumière + mesure de consommation → projection multi-entité

Status: done

<!-- Créée par create-story 2026-07-19 suite au SCP approuvé
     `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-19-lumiere-multi-entite-conso.md`.
     Déclencheur : walkthrough story 16.8, eq 457 "chambre parents". -->

## Story

As a mainteneur jeedom2ha (et utilisateur HA),
I want qu'un eqLogic lumière **actionnable** portant aussi des commandes de mesure `POWER`/`CONSUMPTION`
soit publié comme **une entité `light` + une/des entité(s) `sensor` power/energy sous un device HA commun**,
so that les lumières pilotables qui mesurent leur consommation (Fibaro Dimmer, Shelly, Qubino…) ne soient
plus silencieusement skippées et que leur consommation remonte dans Home Assistant.

## Acceptance Criteria

1. **AC1 — Multi-entité light + conso.** Un eqLogic avec au moins une commande `LIGHT_*` actionnable
   **et** une/des commande(s) `POWER`/`CONSUMPTION` publie : 1 entité `light` (depuis les `LIGHT_*`)
   **+** 1..n entité(s) `sensor` avec `device_class` `power` (W) / `energy` (kWh, `state_class total_increasing`)
   depuis `POWER`/`CONSUMPTION`, toutes rattachées à **un device HA commun** (`identifiers` dérivé de `eq_id`).
2. **AC2 — Fin du faux positif.** Les commandes `POWER`, `CONSUMPTION`, `ENERGY_POWER` ne déclenchent
   **plus** `conflicting_generic_types` (confidence `ambiguous`) sur une lumière : le light mapper les ignore
   (compagnons de mesure laissés au `SensorMapper`) et projette la lumière normalement.
3. **AC3 — Prise inchangée.** Un eqLogic avec `LIGHT_*` **et** `ENERGY_STATE`/`ENERGY_ON`/`ENERGY_OFF`
   reste `ambiguous` (`conflicting_generic_types`) — comportement prise inchangé (décision Alexandre 2026-07-19).
4. **AC4 — Non-régression garde-fous.** Aucune régression sur : le multi-entité `switch` existant (Epic 11)
   et les garde-fous faux positifs light (name-heuristics `prise/plug/volet/…`, `eq.generic_type` non-light,
   color-only, orphan-state, dédup Story 2.6). `generic_type` natif Jeedom jamais muté (invariant D10).
   `PRODUCT_SCOPE` jamais bypassé.
5. **AC5 — Cycle de vie domain-aware.** La dépublication d'un tel eqLogic nettoie **tous** les topics
   discovery secondaires (light + sensors), sans ghost HA (hérité Story 11.1.bis / 11.2).
6. **AC6 — Golden + gate terrain.** Golden corpus (`expected_sync_snapshot.json`) réaligné pour les
   eqLogic light+conso (dont eq 457) : de skippé → `light` + `sensor(s)`. Gate terrain box 192.168.1.21
   (eq 457) : `light` + `sensor` W + `sensor` kWh visibles sous device commun ; suite unitaire 0 régression.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run` → SSH/sudo OK, cible = light.py/registry.py/sensor.py.
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` ← retenu
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.` → `Deploy complete.`

- [x] Task 1 — Light mapper : compagnons de mesure ≠ conflit (AC2, AC3, AC4)
  - [x] Dans `resources/daemon/mapping/light.py`, scinder `_ANTI_LIGHT_GENERIC_TYPES` : retirer
        `POWER`, `CONSUMPTION`, `ENERGY_POWER` (compagnons → ni light_cmds ni anti_light_cmds → ignorés
        par le light mapper, donc laissés au SensorMapper).
  - [x] **Conserver** `ENERGY_STATE`, `ENERGY_ON`, `ENERGY_OFF` dans les conflits durs (comportement prise).
  - [x] Conserver intacts les autres anti-light (HEATING/THERMOSTAT/WATER_HEATER/FLAP/SMOKE/MOTION/
        PRESENCE/OPENING/SIREN/ALARM/LOCK) et les garde-fous name-heuristics / eq.generic_type / color-only /
        orphan-state / dédup.

- [x] Task 2 — Registry : agrégation multi-entité primaire `light` (AC1, AC4, AC5)
  - [x] Dans `resources/daemon/mapping/registry.py`, généraliser `_map_structural_multi_entity` pour
        accepter un **primaire `light`** à l'identique du `switch` : primaire (light|switch) + `sensor`
        power/energy secondaires + binary_sensor éventuels, agrégés sous device commun (`jeedom_eq_id`).
  - [x] Réutiliser le gate `_has_power_or_energy_sensor` (device_class power/energy) pour déclencher
        l'agrégation même avec un seul sensor secondaire (parité switch existante).
  - [x] Vérifier l'ordre déterministe de sortie et la cohérence avec `map()` / `additional_mappings`.

- [x] Task 3 — Tests unitaires (AC1–AC5)
  - [x] `tests/unit/test_light_mapper.py` : lumière + POWER/CONSUMPTION → non-ambigu (light) ; lumière +
        ENERGY_STATE/ON/OFF → toujours ambigu ; non-régression garde-fous.
  - [x] `resources/daemon/tests/unit/test_step2_mapping_failure.py` : `conflicting_generic_types` conservé
        pour les vrais conflits, plus émis pour compagnons de mesure.
  - [x] Test registry multi-entité : primaire light + sensors power/energy ; non-régression primaire switch.
  - [x] Test dépublication domain-aware (light + sensors) — pas de ghost.

- [x] Task 4 — Golden corpus (AC6)
  - [x] Réaligner `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json` pour les
        eqLogic light+conso (dont eq 457) : skippé → light + sensor(s). Vérifier le test de non-régression golden.

- [x] Task 5 — Gate terrain (AC6)
  - [x] Rejouer sur box 192.168.1.21 via `scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → `Deploy complete.`
  - [x] Preuves : eq 457 publie `light` + `sensor` W (`state_class measurement`) + `sensor` kWh
        (`state_class total_increasing`) sous device commun `jeedom2ha_457` ; états MQTT non-unknown.

    **Discovery (retained MQTT, box 192.168.1.21) :**
    - `homeassistant/light/jeedom2ha_457/config` — `unique_id: jeedom2ha_eq_457`, dimmer (brightness),
      `device.identifiers: ["jeedom2ha_457"]`, `via_device: jeedom2ha_bridge`.
    - `homeassistant/sensor/jeedom2ha_457_4104/config` — "Puissance", `device_class: power`,
      `unit_of_measurement: W`, `state_class: measurement`, `device.identifiers: ["jeedom2ha_457"]`.
    - `homeassistant/sensor/jeedom2ha_457_4105/config` — "Consommation", `device_class: energy`,
      `unit_of_measurement: kWh`, `state_class: total_increasing`, `device.identifiers: ["jeedom2ha_457"]`.
    - `homeassistant/sensor/jeedom2ha_457_4102/config` — "Etat", `unit: %` (info numérique, sensor simple).

    **États MQTT (non-unknown) :** `jeedom2ha/457/availability=online`, `457/4104/state=0` (W, lampe off),
    `457/4105/state=27.7` (kWh), `457/4102/state=0` (%). Les cmd ids réels box (4102/4104/4105) diffèrent
    du fixture golden synthétique (45705/45706) — attendu.

## Dev Notes

- **Cause racine** : `light.py:47` range les commandes de mesure dans `_ANTI_LIGHT_GENERIC_TYPES` ; la
  détection anti-affinité (light.py:176-193) renvoie alors `ambiguous / conflicting_generic_types` et
  `decide_publication` (light.py:339-341) mappe ça en `ambiguous_skipped` → eqLogic entier skippé.
- **Mécanique déjà existante** : `registry.py:_map_structural_multi_entity` (lignes ~84-119) agrège déjà
  `switch` (primaire) + sensors/binary_sensors, et `_has_power_or_energy_sensor` déclenche le multi même
  sur un seul sensor power/energy. Il suffit d'étendre le primaire à `light`.
- **SensorMapper prêt** : `sensor.py:25-26` mappe `POWER→(power,W)` et `CONSUMPTION→(energy,kWh)` ;
  `_derive_state_class` (sensor.py:74-77) pose `measurement`/`total_increasing`. `map_all` produit déjà les
  sensors secondaires indépendamment des LIGHT_*.
- **Publisher** : device commun via `identifiers=[device_id]` (publisher.py:371) + `via_device` bridge
  (publisher.py:375), `device_id` dérivé de `jeedom_eq_id` → light + sensors partagent la même carte device HA.
- **Pattern HA** : le schéma MQTT `light`/`switch` n'a pas de champ conso ; la conso s'expose en entités
  `sensor` séparées sous le device (1 device → N entities), pattern Shelly/Tasmota/Zigbee2MQTT.

### Dev Agent Guardrails

- **PRODUCT_SCOPE** jamais bypassé ; `generic_type` natif Jeedom jamais muté (invariant D10).
- **Non-régression prioritaire** : multi-entité switch (Epic 11, notamment eq554/11.2 et eq583/eq628/11.3)
  et garde-fous faux positifs light. Ajouts strictement additifs côté comportement moteur.
- **Aucun nouveau `reason_code`** introduit ; `conflicting_generic_types` conservé pour les vrais conflits.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

### Project Structure Notes

- Fichiers touchés : `resources/daemon/mapping/light.py`, `resources/daemon/mapping/registry.py`,
  tests unitaires associés, golden corpus. `sensor.py` et `publisher.py` : réutilisés sans modification
  attendue (à confirmer en dev).
- Cohérent avec l'architecture du moteur de projection (agrégation multi-entité bornée, dépublication
  domain-aware), pas de nouvelle abstraction.

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-19-lumiere-multi-entite-conso.md]
- [Source: resources/daemon/mapping/light.py#_ANTI_LIGHT_GENERIC_TYPES (L47) + anti-affinité (L176-193)]
- [Source: resources/daemon/mapping/registry.py#_map_structural_multi_entity (L84-119)]
- [Source: resources/daemon/mapping/sensor.py#_SENSOR_GENERIC_TYPE_MAP (L25-26) + map_all (L159)]
- [Source: resources/daemon/discovery/publisher.py#device identifiers (L371-375)]
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic 11 multi-entité (Story 11.2)]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD dev-story, TDD RED→GREEN→REFACTOR)

### Debug Log References

- `python3 -m pytest resources/daemon/tests/unit -q` → 1080 passed.
- `python3 -m pytest tests/unit --ignore=tests/unit/test_daemon_startup.py -q` → 489 passed.
- 23 échecs pré-existants isolés à `tests/unit/test_daemon_startup.py` (`ModuleNotFoundError: jeedomdaemon`,
  dépendance externe absente de l'env — hors périmètre, non causés par cette story).
- Golden : `GOLDEN_REGEN=1 python3 -m pytest resources/daemon/tests/unit/test_story_8_4_golden_file.py`
  puis re-run sans regen → 1 passed (déterministe).

### Completion Notes List

- **AC2** : `light.py` — retrait de `POWER`/`CONSUMPTION`/`ENERGY_POWER` de `_ANTI_LIGHT_GENERIC_TYPES` ;
  ces compagnons tombent hors light_cmds ET anti_light_cmds → ignorés par le light mapper → laissés au
  SensorMapper. Plus de `conflicting_generic_types` sur une lumière mesureuse.
- **AC1/AC4/AC5** : `registry.py:_map_structural_multi_entity` généralisé — primaire `light` publiable
  (confidence sure/probable via `_publishable_light_primary`) accepté à l'identique du switch quand un
  sensor power/energy est présent. Le light mapper n'est invoqué que si `switch_results` vide ET
  `_has_power_or_energy_sensor(sensor_results)` → aucun appel superflu sur les lights ordinaires
  (préserve l'orchestration/spy des steps).
- **sensor.py** (modifié, non prévu initialement dans Dev Notes) : `_has_structural_multi_entity_sensor_shape`
  étendue au motif light actionnable + companion power/energy (branche `not has_switch_shape`), pour produire
  des sensors secondaires à unique_id command-scoped (`jeedom2ha_eq_{eq}_cmd_{cmd_id}`) et éviter toute
  collision d'unique_id avec le light primaire (`jeedom2ha_eq_{eq}`).
- **AC3** : light + `ENERGY_STATE`/`ENERGY_ON`/`ENERGY_OFF` reste `ambiguous`/`conflicting_generic_types`
  (comportement prise) — la branche light exige `not has_switch_shape`, les prises sont strictement inchangées.
- **AC6 (golden)** : eq 457 (Fibaro Dimmer type) ajouté au corpus (58→59 eqLogics) ; snapshot réaligné :
  eq 457 passe de skippé → `light` primaire `probable` (`is_valid: true`, pipeline step 5). Corpus shape
  bumpé 58→59 + `assert 457 in eq_ids`.
- **AC6 (gate terrain)** : ✅ PASS — box 192.168.1.21, `deploy-to-box.sh --cleanup-discovery --restart-daemon`
  → `Deploy complete.`. eq 457 (Fibaro Dimmer réel) publie `light/jeedom2ha_457` (dimmer) + `sensor` Puissance
  (`power`/`W`/`measurement`) + `sensor` Consommation (`energy`/`kWh`/`total_increasing`), tous sous device
  commun `identifiers:["jeedom2ha_457"]`. États MQTT non-unknown (availability `online`, 0 W, 27.7 kWh).
- Aucun nouveau `reason_code` ; `generic_type` natif jamais muté (D10) ; `PRODUCT_SCOPE` non bypassé.
- 0 régression fonctionnelle (1569 tests verts hors dépendance externe absente).
- **code-review (2026-07-19)** : review adversariale — 6/6 AC IMPLEMENTED, audit tâches 0-5 OK, 0 High/Medium.
  Correctif LOW-1 appliqué : `ENERGY_POWER` ajouté explicitement à `_SENSOR_GENERIC_TYPE_MAP`
  (`("power","W")`) pour ne plus dépendre du fallback unité `W→power` — robuste même si une commande
  ENERGY_POWER arrive sans unité. Test dédié `test_energy_power_maps_to_power_without_relying_on_unit`.
  Suite complète re-validée : 1081 tests daemon verts (hors `test_daemon_startup.py` = dép. externe absente).
  Statut résultant : `done`.

### File List

- `resources/daemon/mapping/light.py` (modifié)
- `resources/daemon/mapping/registry.py` (modifié)
- `resources/daemon/mapping/sensor.py` (modifié)
- `resources/daemon/tests/unit/test_story_11_4_light_multi_entite_conso.py` (créé)
- `resources/daemon/tests/unit/test_step2_mapping_failure.py` (modifié)
- `tests/unit/test_light_mapper.py` (modifié)
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py` (modifié — corpus shape 58→59)
- `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json` (modifié — eq 457 ajouté)
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json` (régénéré)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié)

### Change Log

- 2026-07-19 — Story 11.4 implémentée (dev-story, TDD). Light mesureur actionnable → multi-entité
  light + sensor(s) power/energy sous device commun. Statut `in-progress` → `review`.
- 2026-07-19 — Gate terrain AC6 exécuté et PASS sur box 192.168.1.21 (eq 457 réel : light + power W +
  energy kWh sous device commun, états MQTT non-unknown). Prêt pour `code-review`.
- 2026-07-19 — code-review PASS (0 High/Medium). Correctif LOW-1 : mapping explicite `ENERGY_POWER`
  dans `_SENSOR_GENERIC_TYPE_MAP` + test dédié. Statut `review` → `done`.
