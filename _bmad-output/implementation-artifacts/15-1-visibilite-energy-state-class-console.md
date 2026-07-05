# Story 15.1: Visibilité Energy state_class en console

Status: ready-for-dev

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

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.`

- [ ] Task 1 — Étendre le payload `/system/diagnostics` (AC: #5)
  - [ ] Dans `resources/daemon/transport/http_server.py`, `_handle_system_diagnostics` (~L2004), pour chaque commande matched d'un sensor, lire `mapping.reason_details.get("state_class")` et `.get("unit_of_measurement")` (déjà produits par `sensor.py::_sensor_reason_details`, ~L82-96) et les ajouter aux entrées de `matched_commands` (~L2039, L2071-2087, L2120-2132), en restant absents (pas de clé, pas de `null`) quand non applicables.
  - [ ] Ne toucher à aucune autre logique de `_handle_system_diagnostics` (pas de calcul, lecture seule de `reason_details` déjà en mémoire).

- [ ] Task 2 — Étendre le modèle console côté JS (AC: #1, #2, #3)
  - [ ] Dans `desktop/js/jeedom2ha_scope_summary.js`, `readCommandCoverage()` (~L45-62), ajouter le passthrough des clés `state_class` et `unit_of_measurement` en plus de `cmd_id`/`cmd_name`/`generic_type` (whitelist actuelle à étendre, pas remplacer).
  - [ ] `buildEquipmentModel` (~L209-246) : aucun changement structurel nécessaire si `readCommandCoverage` transporte déjà les nouveaux champs — vérifier.

- [ ] Task 3 — Rendu console (AC: #1, #2, #3)
  - [ ] Dans `desktop/js/jeedom2ha.js`, section rendu "Commandes observées" / "Typage Jeedom" (~L906-968, badges inline monospace existants), ajouter un badge/ligne "Energy" affichant `state_class` + unité quand présents sur une commande matched, en réutilisant le pattern d'affichage existant (pas de nouveau composant UI).
  - [ ] Ne rien afficher (pas de placeholder "N/A") quand `state_class` est absent.

- [ ] Task 4 — Tests (AC: #6)
  - [ ] Daemon : étendre `resources/daemon/tests/unit/test_diagnostic_endpoint.py` (et/ou `test_diagnostic_export.py`) avec des cas state_class présent (measurement, total_increasing) et absent (ex. `kW`).
  - [ ] JS : étendre `tests/unit/test_scope_summary_presenter.node.test.js` pour `readCommandCoverage`/`buildEquipmentModel` avec state_class présent/absent.
  - [ ] Lancer la suite complète daemon (`pytest`) pour confirmer zéro régression sur les tests existants (baseline connue : 925 passed avant cette story, cf. story 13.1).

- [ ] Task 5 — Gate terrain (AC: #7)
  - [ ] Après `--cleanup-discovery --restart-daemon`, ouvrir la console sur la box et vérifier visuellement qu'un sensor power et un sensor energy affichent leur state_class/unité.
  - [ ] Vérifier zéro régression visuelle sur un équipement sans Energy (ex. switch simple).

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

### Debug Log References

### Completion Notes List

### File List
