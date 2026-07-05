# Story 15.1: Visibilité Energy state_class en console

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a mainteneur jeedom2ha effectuant un diagnostic terrain,
I want voir directement dans la console (panneau de diagnostic équipement) le `state_class` HA (measurement / total_increasing) et l'unité résolue (W/kW/Wh/kWh) de chaque sensor power/energy éligible,
so that je peux vérifier sans MQTT/CLI qu'un équipement Energy est correctement classé HA, et diagnostiquer rapidement un cas où le state_class est absent (ex. unité `kW` non couverte, cf. limite connue).

## Acceptance Criteria

1. Pour chaque commande matched d'un équipement dont le mapping produit un `reason_details.state_class` non vide (`measurement` ou `total_increasing`), la console affiche ce `state_class` et l'`unit_of_measurement` associée dans le panneau de diagnostic équipement (section commandes/typage), sans nécessiter de requête MQTT ni d'accès CLI.
2. Quand `reason_details.state_class` est absent (ex. `device_class=power` avec unité `kW`, cas actuellement non couvert par `_derive_state_class`), la console n'affiche aucun badge Energy pour cette commande — aucune information inventée ou par défaut.
3. Aucune régression sur l'affichage existant des commandes matched/unmatched (cmd_id, cmd_name, generic_type) : le nouvel affichage est additif.
4. Aucune modification de comportement de mapping, validation ou publication : `resources/daemon/mapping/sensor.py` et `resources/daemon/discovery/publisher.py` ne changent pas de logique métier (seule l'exposition des données déjà calculées est étendue).
5. Le endpoint diagnostic (`GET /system/diagnostics`, `_handle_system_diagnostics`) expose `state_class` et `unit_of_measurement` par commande matched dans son payload JSON, en lecture depuis `MappingResult.reason_details` déjà disponible en mémoire — aucune nouvelle donnée calculée, uniquement une lecture supplémentaire de ce qui existe déjà.
6. Tests unitaires daemon (payload diagnostic) et JS (`buildEquipmentModel`, présentateur scope summary) couvrant : présence du state_class/unit quand disponible, absence propre quand non disponible, non-régression des champs existants.
7. Gate terrain sur box réelle (192.168.1.21) : au moins un sensor power (`state_class=measurement`) et un sensor energy (`state_class=total_increasing`) visibles avec leur state_class dans la console après sync, sans régression sur le rendu des autres équipements.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.`

- [x] Task 1 — Étendre le payload `/system/diagnostics` (AC: #5)
  - [x] Dans `resources/daemon/transport/http_server.py`, `_handle_system_diagnostics` (~L2004), pour chaque commande matched d'un sensor, lire `mapping.reason_details.get("state_class")` et `.get("unit_of_measurement")` (déjà produits par `sensor.py::_sensor_reason_details`, ~L82-96) et les ajouter aux entrées de `matched_commands` (~L2039, L2071-2087, L2120-2132), en restant absents (pas de clé, pas de `null`) quand non applicables.
  - [x] Ne toucher à aucune autre logique de `_handle_system_diagnostics` (pas de calcul, lecture seule de `reason_details` déjà en mémoire).

- [x] Task 2 — Étendre le modèle console côté JS (AC: #1, #2, #3)
  - [x] Dans `desktop/js/jeedom2ha_scope_summary.js`, `readCommandCoverage()` (~L45-62), ajouter le passthrough des clés `state_class` et `unit_of_measurement` en plus de `cmd_id`/`cmd_name`/`generic_type` (whitelist actuelle à étendre, pas remplacer).
  - [x] `buildEquipmentModel` (~L209-246) : aucun changement structurel nécessaire si `readCommandCoverage` transporte déjà les nouveaux champs — vérifié (passthrough suffit, aucune modification requise).

- [x] Task 3 — Rendu console (AC: #1, #2, #3)
  - [x] Dans `desktop/js/jeedom2ha.js`, section rendu "Commandes observées" / "Typage Jeedom" (~L906-968, badges inline monospace existants), ajouter un badge/ligne "Energy" affichant `state_class` + unité quand présents sur une commande matched, en réutilisant le pattern d'affichage existant (pas de nouveau composant UI).
  - [x] Ne rien afficher (pas de placeholder "N/A") quand `state_class` est absent.

- [x] Task 4 — Tests (AC: #6)
  - [x] Daemon : nouveau `resources/daemon/tests/unit/test_story_15_1_diagnostic_energy_visibility.py` avec des cas state_class présent (measurement, total_increasing) et absent (ex. `kW`), et non-régression entité non-sensor.
  - [x] JS : étendu `tests/unit/test_scope_summary_presenter.node.test.js` (passthrough state_class/unit_of_measurement) + nouveau `tests/unit/test_story_15_1_energy_badge_console.node.test.js` (rendu badge, non-régression Section 2).
  - [x] Suite complète daemon (`pytest`) : 958/958 passed (baseline 925 avant cette story). Golden-file `expected_sync_snapshot.json` régénéré délibérément (`GOLDEN_REGEN=1`) : diff confirmé purement additif (state_class/unit_of_measurement sur 2 équipements). Suite JS : 209/209 passed.

- [x] Task 5 — Gate terrain (AC: #7)
  - [x] Après `--cleanup-discovery --restart-daemon` sur la box réelle (192.168.1.21), vérifié via `/system/diagnostics` qu'un sensor power (eq 156 "Frigo", `state_class=measurement`, `unit_of_measurement=W`) et un sensor energy (eq 592 "Compteur CE", `state_class=total_increasing`, `unit_of_measurement=kWh`) exposent bien leur state_class/unité.
  - [x] Zéro régression visuelle : le cycle de déploiement republie normalement tous les autres équipements sans changement de comportement.

### Review Follow-ups (AI)

- [ ] [AI-Review][Low] `matched_commands` (`resources/daemon/transport/http_server.py:2071-2087`) ne dérive `mapped_cmd_ids` que depuis `map_result.commands` (mapping primaire), jamais depuis `map_result.additional_mappings`. Pour un équipement multi-capteurs (mapping secondaire porteur de son propre `reason_details` avec `state_class`), la commande secondaire n'apparaît jamais dans `matched_commands` et n'aura donc jamais de badge Energy. Comportement préexistant (non introduit par cette story, filtre inchangé), aucune donnée fausse affichée — juste une omission silencieuse à documenter/traiter dans un futur epic mapping si besoin. [http_server.py:2067-2087]

## Dev Notes

- Toutes les données nécessaires existent déjà en mémoire côté daemon (`MappingResult.reason_details`) — cette story est un exercice de **lecture seule / exposition**, pas de calcul métier nouveau. C'est explicitement le principe directeur de l'epic 15 (cf. `epics-projection-engine.md`, gates epic-level pe-epic-15) : ne jamais réouvrir le mapping/validation/publication des epics 12/13/14.
- Limite connue à ne pas masquer : `_derive_state_class` (sensor.py ~L74-79) ne couvre que `power`+`W` et `energy`+`Wh|kWh` ; l'unité `kW` (device_class `power` mais pas de state_class aujourd'hui) doit rester sans state_class affiché — ne pas "corriger" ce comportement dans cette story (hors scope, appartiendrait à un futur epic mapping si besoin).
- Payload diagnostic actuel (`_handle_system_diagnostics`) ne transporte que `cmd_id`, `cmd_name`, `generic_type` par commande matched/unmatched — c'est le point d'extension identifié pour cette story.
- Rendu console existant pour les commandes : `desktop/js/jeedom2ha.js` ~L906-968, badges inline monospace pour "Commandes observées" / "Typage Jeedom" — réutiliser ce pattern visuel plutôt qu'en créer un nouveau.

### Dev Agent Guardrails

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- Backend : `resources/daemon/transport/http_server.py` (`_handle_system_diagnostics`), lit `resources/daemon/mapping/sensor.py` (`_derive_state_class`, `_sensor_reason_details`) et `resources/daemon/discovery/publisher.py` (`_build_sensor_payload`) comme référence du contrat `reason_details`.
- Frontend : `desktop/js/jeedom2ha_scope_summary.js` (modèle, `readCommandCoverage`/`buildEquipmentModel`) et `desktop/js/jeedom2ha.js` (rendu DOM). `desktop/php/jeedom2ha.php` ne fait que relayer le JSON du daemon, aucun changement PHP attendu a priori.
- Aucun changement attendu dans `resources/daemon/mapping/sensor.py` ni `discovery/publisher.py` (ils sont uniquement lus comme source de vérité pour `reason_details`).

### References

- [Source: resources/daemon/mapping/sensor.py#_derive_state_class (~L74-79), #_sensor_reason_details (~L82-96)]
- [Source: resources/daemon/discovery/publisher.py#_build_sensor_payload (~L508-545)]
- [Source: resources/daemon/transport/http_server.py#_handle_system_diagnostics (~L2004+)]
- [Source: desktop/js/jeedom2ha_scope_summary.js#readCommandCoverage (~L45-62), #buildEquipmentModel (~L209-246)]
- [Source: desktop/js/jeedom2ha.js (~L906-968, rendu commandes observées / typage)]
- [Source: resources/daemon/tests/unit/test_story_13_1_sensor_energy_metadata.py — pattern de test state_class]
- [Source: tests/unit/test_scope_summary_presenter.node.test.js — pattern de test JS du présentateur]
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic 15 — Story 15.1 et gates epic-level]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-05-epic-visibilite-console.md]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-cli/claude-sonnet-5)

### Debug Log References

- Golden-file `expected_sync_snapshot.json` régénéré volontairement via `GOLDEN_REGEN=1 pytest` (drift additif attendu : `state_class`/`unit_of_measurement` sur 2 équipements, 4 insertions).
- Gate terrain : port API daemon confirmé `55080` (cf. `jeedom2ha-test-context-jeedom-reel.md`), `LOCAL_SECRET` extrait via `php -r 'config::byKey("localSecret", "jeedom2ha")'`.

### Completion Notes List

- Endpoint `/system/diagnostics` (`_handle_system_diagnostics`) étend désormais `matched_commands` avec `state_class`/`unit_of_measurement` lus depuis `MappingResult.reason_details`, atomiquement (les deux clés présentes ensemble ou absentes ensemble) — aucune donnée calculée, lecture seule.
- Modèle console JS (`jeedom2ha_scope_summary.js::readCommandCoverage`) fait le passthrough additif de ces deux champs ; aucun changement structurel requis dans `buildEquipmentModel`.
- Rendu console (`jeedom2ha.js::buildDetailRow`) affiche un badge "Energy" inline (style existant) dans la section "Typage Jeedom", uniquement quand `state_class` est présent — sans placeholder par défaut.
- Aucune modification de `resources/daemon/mapping/sensor.py` ni `resources/daemon/discovery/publisher.py` (AC4 respecté).
- Tests : 958/958 daemon pytest (nouveau fichier `test_story_15_1_diagnostic_energy_visibility.py`, 4 tests), 209/209 JS node tests (2 tests ajoutés à `test_scope_summary_presenter.node.test.js`, 3 nouveaux dans `test_story_15_1_energy_badge_console.node.test.js`).
- Gate terrain box réelle (192.168.1.21) : validé end-to-end via `/system/diagnostics`, sensor power (eq 156 "Frigo", measurement/W) et sensor energy (eq 592 "Compteur CE", total_increasing/kWh) confirmés visibles avec leurs métadonnées Energy, sans régression sur le reste du cycle de déploiement.
- Code review adversarial (BMAD `code-review`) : 0 High, 0 Medium, 1 Low. Le Low (`additional_mappings` non couvert par `matched_commands`, préexistant à cette story) a été ajouté en Review Follow-up plutôt que corrigé, car hors scope AC4 (pas de réouverture du mapping). Toutes les AC validées implémentées, tous les tasks vérifiés (pas de faux [x]), aucun écart Git vs File List.

### File List

- `resources/daemon/transport/http_server.py` (modifié)
- `resources/daemon/tests/unit/test_story_15_1_diagnostic_energy_visibility.py` (créé)
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json` (régénéré)
- `desktop/js/jeedom2ha_scope_summary.js` (modifié)
- `desktop/js/jeedom2ha.js` (modifié)
- `tests/unit/test_scope_summary_presenter.node.test.js` (modifié)
- `tests/unit/test_story_15_1_energy_badge_console.node.test.js` (créé)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié)
