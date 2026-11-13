// ARTEFACT — Story 25.4 (AC4, AC15, AC31, AC32) : non-régression. Aucune modification du démon, des routes, du relais ni des
// artefacts figés ; `jeedom2ha_mapping_override.js` n'a que des ajouts ; la vue n'ajoute ni copie ni re-sérialisation des
// états ; parité d'état entre l'arbre (entrée agrégée) et le détail (arbre unitaire), y compris après une relecture ; le calcul
// de l'arbre, des KPI et des filtres sur 292 équipements est mesuré (sans seuil inventé). Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const W = require('../../desktop/js/jeedom2ha_workview.js');
const { diffAgainstBase, fileAtBase, removedLines } = require('./helpers/git_base');
const { FIXTURE, phpAvailable, SCENE, clone } = require('./helpers/page_b_harness');
const { startWorkview, openCard } = require('./helpers/workview_harness');
const { makeScene } = require('./helpers/big_scene');
const { ok } = require('./helpers/ui_harness');

const root = path.join(__dirname, '..', '..');
const maybe = phpAvailable ? it : it.skip;
const stripComments = (source) => source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

describe('25.4 / AC31 — le démon, les routes et les artefacts figés ne changent pas', () => {
  // Stories 25.8 et 25.9 (adaptation par ajout) : seules ces lignes existantes ont été remplacées — la liste blanche de la route agrégée
  // gagne `present_in_ha` (25.8, Q1 B) et `saveFilteringConfig` n'écrit plus la clé des pièces exclues (25.9, AC6). Tout autre
  // retrait dans ces fichiers fait échouer le garde.
  const REPLACED_BY_25_8_25_9 = [
    '"entities": [{"override_pending": e["override_pending"]} for e in tree["entities"]],',
    'equipment_decision, entities[{override_pending}], commands[{jeedom_cmd_id, covered,',
    'assert all(set(e) == {"override_pending"} for e in entry["entities"])', // test de la liste blanche de 25.2, mis à jour avec elle
    "$excludedPlugins  = init('excludedPlugins', '');",
    "$excludedObjects  = init('excludedObjects', '');",
    "$confidencePolicy = init('confidencePolicy', 'sure_probable');",
    '// Validation : valeurs autorisées uniquement',
    "if (!in_array($confidencePolicy, ['sure_only', 'sure_probable'])) {",
    "$confidencePolicy = 'sure_probable';",
    '}',
    "config::save('excludedPlugins',  $excludedPlugins,  'jeedom2ha');",
    "config::save('excludedObjects',  $excludedObjects,  'jeedom2ha');",
    "config::save('confidencePolicy', $confidencePolicy, 'jeedom2ha');",
    "log::add('jeedom2ha', 'info', '[CONFIG] saveFilteringConfig: excludedPlugins=\"'",
    '. $excludedPlugins . \'" excludedObjects="\' . $excludedObjects',
    '. \'" confidencePolicy="\' . $confidencePolicy . \'"\');',
  ];

  // Story 24.2 (autorisée par ClaudeBox) : l'export de décision ajoute une route du démon, une action ajax et deux clés de
  // sync_config. Seules ces deux lignes existantes sont remplacées (sync_config étendu ; condition de périmètre du sync calculée
  // une fois dans `scope_included`) ; core/class/ passe donc du « diff vide » au garde « aucune ligne retirée » ci-dessous.
  const REPLACED_BY_24_2 = [
    "$result['sync_config'] = array('confidence_policy' => $confidencePolicy);",
    'if not _scope_entry_is_included(eq_id, scope_entries.get(eq_id), eligibility):',
  ];

  // Story 24.4 (projection HomeKit) et sa relecture R1 : lignes existantes remplacées dans le démon (résolution du périmètre, lecture de
  // l'exclusion historique, import et signature/appel de la projection agrégée, qui gagne trois champs additifs).
  const REPLACED_BY_24_4 = [
    'effective_state = piece_effective',
    'decision_source = "piece" if piece_state != STATE_INHERIT else "global"',
    'if eq.is_excluded:',
    'source = eq.exclusion_source or "eqlogic"  # défaut rétro-compatible',
    'from models.published_scope import resolve_published_scope',
    'def _project_equipment_state(tree: Dict[str, Any]) -> Dict[str, Any]:',
    'equipments[str(eq_id)] = _project_equipment_state(tree)',
    // test de la route agrégée (25.2) : les trois champs additifs sont écartés de la comparaison à l'arbre unitaire
    'EQUIPMENT_KEYS = {"jeedom_eq_id", "equipment_decision", "entities", "commands", "sync_status"}',
    'assert payload["equipments"][str(eq_id)] == _project(unit)',
    'assert after["equipments"]["101"] == _project(unit)',
  ];

  // Story 24.8 (ouverture gouvernée de `valve`, AR13) : les listes figées des composants ouverts et des publishers gagnent
  // `valve` (code et tests qui les vérifient), `valve` est un actionneur de l'export de décision, et le golden 8.4 gagne les
  // compteurs `valves_*` à 0 (seule la virgule après `switches_sure` change). Le reste du démon est en ajouts seuls. Chaque
  // remplacement est admis dans SON fichier seulement (« fichier::ligne »), pas comme texte libre.
  const REPLACED_BY_24_8 = [
    'resources/daemon/validation/ha_component_registry.py::PRODUCT_SCOPE = ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"]  # climate ouvert Story 10.2 sous FR40/NFR10 # alarm_control_panel ouvert Story 10.3 sous FR40/NFR10',
    'resources/daemon/discovery/registry.py::_known_types = ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"]',
    'resources/daemon/export/decision_export.py::_ACTUATOR_TYPES = frozenset({"light", "cover", "switch", "climate", "alarm_control_panel"})',
    'resources/daemon/tests/unit/test_ha_component_registry.py::assert PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"]',
    'resources/daemon/tests/unit/test_story_7_2_wave_registry.py::assert PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"]',
    'resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py::assert PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"]',
    'resources/daemon/tests/unit/test_story_7_4_governance_product_scope.py::assert set(PRODUCT_SCOPE) == {"light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"}',
    'resources/daemon/tests/unit/test_story_7_4_governance_product_scope.py::assert len(PRODUCT_SCOPE) == 8',
    'resources/daemon/tests/unit/test_story_8_2_publisher_registry.py::assert set(registry.publishers.keys()) == {"light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"}',
    'resources/daemon/tests/unit/test_story_8_2_publisher_registry.py::assert PublisherRegistry.known_types() == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"]',
    'resources/daemon/tests/unit/test_story_9_1_sensor_mapper.py::assert PublisherRegistry.known_types() == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"]',
    'resources/daemon/tests/unit/test_story_9_2_binary_sensor_mapper.py::assert PublisherRegistry.known_types() == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"]',
    'resources/daemon/tests/unit/test_story_9_3_button_mapper.py::"light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel"',
    'resources/daemon/tests/unit/test_story_24_7_portail_garage_cover.py::"climate", "alarm_control_panel"]',
    'resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::"switches_sure": 3',
  ];

  // Story 24.9 (ouverture gouvernée de `lock`, AR13) : mêmes listes figées que 24.8, qui gagnent `lock` (code et tests qui les
  // vérifient), `lock` est un actionneur de l'export de décision ; le test 24.8 « valve en dernier » devient « valve présent ».
  // Le golden 8.4 gagne les compteurs `locks_*` à 0 en ajouts seuls. Le reste du démon est en ajouts seuls (« fichier::ligne »).
  const REPLACED_BY_24_9 = [
    'resources/daemon/validation/ha_component_registry.py::PRODUCT_SCOPE = ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"]  # climate ouvert Story 10.2 sous FR40/NFR10 # alarm_control_panel ouvert Story 10.3 sous FR40/NFR10 # valve ouvert Story 24.8 sous FR40/NFR10',
    'resources/daemon/discovery/registry.py::_known_types = ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"]',
    'resources/daemon/export/decision_export.py::_ACTUATOR_TYPES = frozenset({"light", "cover", "switch", "climate", "alarm_control_panel", "valve"})',
    'resources/daemon/tests/unit/test_ha_component_registry.py::assert PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"]',
    'resources/daemon/tests/unit/test_story_7_2_wave_registry.py::assert PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"]',
    'resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py::assert PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"]',
    'resources/daemon/tests/unit/test_story_7_4_governance_product_scope.py::assert set(PRODUCT_SCOPE) == {"light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"}',
    'resources/daemon/tests/unit/test_story_7_4_governance_product_scope.py::assert len(PRODUCT_SCOPE) == 9',
    'resources/daemon/tests/unit/test_story_8_2_publisher_registry.py::assert set(registry.publishers.keys()) == {"light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"}',
    'resources/daemon/tests/unit/test_story_8_2_publisher_registry.py::assert PublisherRegistry.known_types() == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"]',
    'resources/daemon/tests/unit/test_story_9_1_sensor_mapper.py::assert PublisherRegistry.known_types() == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"]',
    'resources/daemon/tests/unit/test_story_9_2_binary_sensor_mapper.py::assert PublisherRegistry.known_types() == ["light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"]',
    'resources/daemon/tests/unit/test_story_9_3_button_mapper.py::"light", "cover", "switch", "sensor", "binary_sensor", "button", "climate", "alarm_control_panel", "valve"',
    'resources/daemon/tests/unit/test_story_24_7_portail_garage_cover.py::"climate", "alarm_control_panel", "valve"]',
    'resources/daemon/tests/unit/test_story_24_8_vanne_arrosage_valve.py::assert PRODUCT_SCOPE[-1] == "valve"',
    'resources/daemon/tests/unit/test_story_24_8_vanne_arrosage_valve.py::assert PublisherRegistry.known_types()[-1] == "valve"',
  ];

  // Story 24.14 (décisions D1 A et D2 A d'Alexandre) : le bouton d'un scénario n'est plus retiré quand le scénario devient
  // inactif, il est grisé par une disponibilité propre (`jeedom2ha/scenario_<id>/availability`, `availability_mode: all`) ;
  // la purge « le broker fait foi » ne retire plus que les scénarios supprimés ; l'export ne donne plus `scenario_inactive`.
  // L'instantané (topologie, éligibilité, `mappings`, `publications`, `scenario_publications`) n'est remplacé qu'en fin de
  // synchro réussie (AC8). La synchro de démarrage porte l'en-tête `boot` (AC9). Seules ces lignes sont remplacées
  // (« fichier::ligne ») ; le reste du démon et de core/class/ est en ajouts seuls.
  const REPLACED_BY_24_14 = [
    "core/class/jeedom2ha.class.php::return self::callDaemon('/action/sync', $topology, 'POST', 15);",
    "resources/daemon/discovery/publisher.py::EntityAvailability,",
    "resources/daemon/discovery/publisher.py::# Story 21.1 (C8) — pont seul : jamais la disponibilité d'un eqLogic homonyme.",
    "resources/daemon/discovery/publisher.py::return build_discovery_availability_fields(EntityAvailability())",
    "resources/daemon/export/decision_export.py::REASON_SCENARIO_INACTIVE = \"scenario_inactive\"  # scénario inactif : jamais de bouton dans HA",
    "resources/daemon/export/decision_export.py::published = bool(scenario.is_active and getattr(scenario_publication, \"discovery_published\", False))",
    "resources/daemon/export/decision_export.py::\"decision\": DECISION_PUBLISHED if scenario.is_active else DECISION_NOT_PUBLISHED,",
    "resources/daemon/export/decision_export.py::\"reason\": REASON_SCENARIO_BUTTON if scenario.is_active else REASON_SCENARIO_INACTIVE,",
    "resources/daemon/transport/http_server.py::request.app[\"topology\"] = snapshot",
    "resources/daemon/transport/http_server.py::request.app[\"eligibility\"] = eligibility",
    "resources/daemon/transport/http_server.py::# Nettoyage de la RAM pour éviter les données obsolètes (fuite pour Diagnostics)",
    "resources/daemon/transport/http_server.py::request.app[\"mappings\"].pop(old_eq_id, None)",
    "resources/daemon/transport/http_server.py::request.app[\"publications\"].pop(old_eq_id, None)",
    "resources/daemon/transport/http_server.py::unpublished_scenario_ids: Set[int] = set()",
    "resources/daemon/transport/http_server.py::if not scenario.is_active:",
    "resources/daemon/transport/http_server.py::# Story 21.1 (CC-44) — un scénario inactif n'a plus de bouton dans HA.",
    "resources/daemon/transport/http_server.py::# Pas de report si le broker est injoignable : la purge « le broker fait foi »",
    "resources/daemon/transport/http_server.py::# ci-dessous reprend au sync suivant (aucun passage par pending_discovery_unpublish,",
    "resources/daemon/transport/http_server.py::# indexé par eq_id).",
    "resources/daemon/transport/http_server.py::if broker_ready and await publisher.unpublish(f\"jeedom2ha_scenario_{scenario_id}\"):",
    "resources/daemon/transport/http_server.py::unpublished_scenario_ids.add(scenario_id)",
    "resources/daemon/transport/http_server.py::continue",
    "resources/daemon/transport/http_server.py::active_or_alive=True,",
    "resources/daemon/transport/http_server.py::# Purge scenarios that disappeared or became inactive since last sync (M1 fix).",
    "resources/daemon/transport/http_server.py::for stale_id in stale_scenario_ids:",
    "resources/daemon/transport/http_server.py::request.app[\"scenario_publications\"].pop(stale_id, None)",
    "resources/daemon/transport/http_server.py::request.app[\"scenario_publications\"].update(scenario_publications)",
    "resources/daemon/transport/http_server.py::# qui ne sont pas actifs (inactifs, supprimés, fantômes déjà présents). Garde-fou : la",
    "resources/daemon/transport/http_server.py::# section `scenarios` doit être une liste, lue en entier côté démon et déclarée complète",
    "resources/daemon/transport/http_server.py::# par le producteur PHP (`scenarios_complete`), sinon le défaut « liste vide » ou un",
    "resources/daemon/transport/http_server.py::# scénario illisible ferait vider des boutons encore actifs.",
    "resources/daemon/transport/http_server.py::result = await publisher.purge_orphan_scenario_buttons(",
    "resources/daemon/transport/http_server.py::set(scenario_publications), unpublished_scenario_ids",
    "resources/daemon/transport/http_server.py::)",
    "resources/daemon/transport/http_server.py::emptied_ids = sorted(unpublished_scenario_ids | set(purged_ids))",
    "resources/daemon/transport/http_server.py::if emptied_ids:",
    "resources/daemon/transport/http_server.py::\"[SCENARIO] Unpublished %d scenario button(s) (%d inactive, %d from broker): ids=%s\",",
    "resources/daemon/transport/http_server.py::len(emptied_ids), len(unpublished_scenario_ids), len(purged_ids), emptied_ids,",
  ];

  // Story 24.15 (décisions D1 A, D4 A et D5 d'Alexandre ; D2 et D3 par parité Homebridge) : le climate d'un thermostat publie
  // consigne, température, mode, presets et chauffe, et devient pilotable. Lignes remplacées : le mapper et le payload du
  // climate (anciens topics `temperature/state`, `modes` fixes), l'entrée de registre (`required_fields`), la regex des canaux
  // retenus de sync/state.py, trois assertions des tests 10-2, et les références du golden 8.4 et des gardes 19-4 régénérées
  // (seuls les thermostats synthétiques changent). Admis dans leur fichier seulement (« fichier::ligne »).
  const REPLACED_BY_24_15 = [
    "resources/daemon/discovery/publisher.py::\"modes\": [\"heat\", \"off\"],",
    "resources/daemon/discovery/publisher.py::\"temperature_command_topic\", f\"jeedom2ha/{eq_id}/temperature/set\"",
    "resources/daemon/discovery/publisher.py::\"temperature_command_topic\": reason_details.get(",
    "resources/daemon/discovery/publisher.py::\"temperature_state_topic\", f\"jeedom2ha/{eq_id}/temperature/state\"",
    "resources/daemon/discovery/publisher.py::\"temperature_state_topic\": reason_details.get(",
    "resources/daemon/discovery/publisher.py::),",
    "resources/daemon/discovery/publisher.py::Minimal useful payload: temperature setpoint + current temperature when available.",
    "resources/daemon/discovery/publisher.py::Scope: residential thermostat, no advanced HVAC modes (Story 10.2 guardrail).",
    "resources/daemon/discovery/publisher.py::current_temperature_topic = reason_details.get(\"current_temperature_topic\")",
    "resources/daemon/discovery/publisher.py::if current_temperature_topic:",
    "resources/daemon/discovery/publisher.py::payload[\"current_temperature_topic\"] = current_temperature_topic",
    "resources/daemon/mapping/climate.py::\"temperature_command_topic\": f\"jeedom2ha/{eq_id}/temperature/set\",",
    "resources/daemon/mapping/climate.py::\"temperature_state_topic\": f\"jeedom2ha/{eq_id}/temperature/state\",",
    "resources/daemon/mapping/climate.py::commands = {\"THERMOSTAT_SET_SETPOINT\": setpoint_cmd}",
    "resources/daemon/mapping/climate.py::commands[\"THERMOSTAT_TEMPERATURE\"] = temp_cmd",
    "resources/daemon/mapping/climate.py::from models.mapping import ClimateCapabilities, MappingResult",
    "resources/daemon/mapping/climate.py::from typing import Optional",
    "resources/daemon/mapping/climate.py::reason_details[\"current_temperature_topic\"] = f\"jeedom2ha/{eq_id}/current_temperature\"",
    "resources/daemon/sync/state.py::(FR49).",
    "resources/daemon/sync/state.py::Domains not yet streamed (climate, alarm_control_panel) are governed later waves",
    "resources/daemon/sync/state.py::_CHANNEL_TOPIC_RE = re.compile(r\"jeedom2ha/\\d+/(?:state|brightness|position)\")",
    "resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::\"has_setpoint\": true",
    "resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::\"switches_published\": 14,",
    "resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::\"switches_sure\": 3,",
    "resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::\"temperature_command_topic\": \"jeedom2ha/11001/temperature/set\",",
    "resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::\"temperature_state_topic\": \"jeedom2ha/11000/temperature/state\"",
    "resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::\"temperature_state_topic\": \"jeedom2ha/11001/temperature/state\"",
    "resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::\"temperature_state_topic\": \"jeedom2ha/11002/temperature/state\"",
    "resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::\"total_cmds\": 174,",
    "resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json::\"unmatched_commands\": [],",
    "resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore.json::\"temperature_command_topic\": \"jeedom2ha/11001/temperature/set\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore.json::\"temperature_state_topic\": \"jeedom2ha/11000/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore.json::\"temperature_state_topic\": \"jeedom2ha/11001/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore.json::\"temperature_state_topic\": \"jeedom2ha/11002/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore_mqtt.json::\"heat\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore_mqtt.json::\"off\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11000/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11001/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s1_sync_corpus_dore_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11002/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s2_second_sync_calls.json::\"temperature_command_topic\": \"jeedom2ha/11001/temperature/set\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s2_second_sync_calls.json::\"temperature_state_topic\": \"jeedom2ha/11000/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s2_second_sync_calls.json::\"temperature_state_topic\": \"jeedom2ha/11001/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s2_second_sync_calls.json::\"temperature_state_topic\": \"jeedom2ha/11002/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s2_second_sync_calls_mqtt.json::\"heat\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s2_second_sync_calls_mqtt.json::\"off\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s2_second_sync_calls_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11000/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s2_second_sync_calls_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11001/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s2_second_sync_calls_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11002/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s3_publier_global_after_sync.json::\"temperature_command_topic\": \"jeedom2ha/11001/temperature/set\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s3_publier_global_after_sync.json::\"temperature_state_topic\": \"jeedom2ha/11000/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s3_publier_global_after_sync.json::\"temperature_state_topic\": \"jeedom2ha/11001/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s3_publier_global_after_sync.json::\"temperature_state_topic\": \"jeedom2ha/11002/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s3_publier_global_after_sync_mqtt.json::\"heat\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s3_publier_global_after_sync_mqtt.json::\"off\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s3_publier_global_after_sync_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11000/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s3_publier_global_after_sync_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11001/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s3_publier_global_after_sync_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11002/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s5_policy_transition_sure_only.json::\"temperature_command_topic\": \"jeedom2ha/11001/temperature/set\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s5_policy_transition_sure_only.json::\"temperature_state_topic\": \"jeedom2ha/11000/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s5_policy_transition_sure_only.json::\"temperature_state_topic\": \"jeedom2ha/11001/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s5_policy_transition_sure_only.json::\"temperature_state_topic\": \"jeedom2ha/11002/temperature/state\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s5_policy_transition_sure_only_mqtt.json::\"heat\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s5_policy_transition_sure_only_mqtt.json::\"off\"",
    "resources/daemon/tests/fixtures/story_19_4_guard/s5_policy_transition_sure_only_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11000/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s5_policy_transition_sure_only_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11001/temperature/state\",",
    "resources/daemon/tests/fixtures/story_19_4_guard/s5_policy_transition_sure_only_mqtt.json::\"temperature_state_topic\": \"jeedom2ha/11002/temperature/state\",",
    "resources/daemon/tests/unit/test_story_10_2_climate_opening.py::assert \"off\" in payload[\"modes\"]",
    "resources/daemon/tests/unit/test_story_10_2_climate_opening.py::assert mapping.reason_details[\"temperature_state_topic\"] == \"jeedom2ha/5100/temperature/state\"",
    "resources/daemon/tests/unit/test_story_10_2_climate_opening.py::assert payload[\"temperature_state_topic\"] == \"jeedom2ha/5100/temperature/state\"",
    "resources/daemon/validation/ha_component_registry.py::\"required_fields\": [\"availability\"],",
  ];

  // Correctif fix/deploy-preserve-python-venv (défaut constaté le 20/10 sur la VM de démo, Jeedom 4.6.1 / Debian 12) : l'étape 1b
  // de deploy-to-box.sh supprimait (rsync --delete) puis passait en 644 `resources/python_venv/`, le venv que le cœur Jeedom crée
  // pour les dépendances pip3 et avec lequel il lance le démon → « python_venv/bin/python3: not found ». Seules ces trois lignes
  // sont remplacées (rsync + deux find) et seules ces lignes sont ajoutées ; tout autre changement des scripts de déploiement
  // fait échouer le garde.
  const DEPLOY_VENV_FIX = {
    removed: [
      `sudo rsync -a --delete --exclude 'data/' "\${JEEDOM_STAGING_DIR}/" "\${JEEDOM_BOX_PATH}/"`,
      'sudo find "${JEEDOM_BOX_PATH}" -type d -exec chmod 755 {} \\;',
      'sudo find "${JEEDOM_BOX_PATH}" -type f -exec chmod 644 {} \\;',
    ],
    added: [
      '# resources/python_venv/ est créé par le cœur Jeedom (dépendances pip3 de packages.json) et sert à lancer le démon :',
      '# ni supprimé par --delete, ni chmod 644 (VM de démo 20/10 : démon « python_venv/bin/python3: not found »).',
      `sudo rsync -a --delete --exclude 'data/' --exclude '/resources/python_venv/' "\${JEEDOM_STAGING_DIR}/" "\${JEEDOM_BOX_PATH}/"`,
      'sudo find "${JEEDOM_BOX_PATH}" -path "${JEEDOM_BOX_PATH}/resources/python_venv" -prune -o -type d -exec chmod 755 {} \\;',
      'sudo find "${JEEDOM_BOX_PATH}" -path "${JEEDOM_BOX_PATH}/resources/python_venv" -prune -o -type f -exec chmod 644 {} \\;',
    ],
  };

  it('git diff --stat sur les scripts de déploiement : vide (hors le correctif DEPLOY_VENV_FIX de deploy-to-box.sh)', () => {
    const diff = diffAgainstBase(['--stat'], ['scripts/parity-snapshot.sh', 'scripts/deploy-inventory-diff.sh']);
    if (diff !== null) assert.equal(diff, '');
    const deploy = diffAgainstBase(['-U0'], ['scripts/deploy-to-box.sh']);
    if (deploy === null || deploy === '') return;
    const lines = deploy.split('\n').filter((l) => /^[+-]/.test(l) && !/^(\+\+\+|---) /.test(l));
    assert.deepEqual(lines.filter((l) => l.startsWith('-')).map((l) => l.slice(1)), DEPLOY_VENV_FIX.removed);
    assert.deepEqual(lines.filter((l) => l.startsWith('+')).map((l) => l.slice(1)), DEPLOY_VENV_FIX.added);
  });

  it('resources/daemon/, core/ajax/, core/class/, lib/policy.mjs : aucune ligne existante retirée, hors les remplacements de 25.8, 25.9 et 24.2', () => {
    const diff = diffAgainstBase(['-U0'], ['resources/daemon/', 'core/ajax/', 'core/class/', 'tests/e2e/gate/lib/policy.mjs']);
    if (diff === null) return;
    const allowed = [...REPLACED_BY_25_8_25_9, ...REPLACED_BY_24_2, ...REPLACED_BY_24_4];
    // Ligne retirée -> « fichier::ligne » (fichier lu dans l'en-tête `diff --git` qui la précède).
    let file = null;
    const removed = [];
    for (const l of diff.split('\n')) {
      if (l.startsWith('diff --git ')) file = l.split(' b/').pop();
      else if (removedLines(l).length) removed.push({ file, line: l.slice(1).trim() });
    }
    const unexpected = removed
      .filter(({ file: f, line }) => !allowed.includes(line) && !REPLACED_BY_24_8.includes(`${f}::${line}`)
        && !REPLACED_BY_24_9.includes(`${f}::${line}`) && !REPLACED_BY_24_14.includes(`${f}::${line}`)
        && !REPLACED_BY_24_15.includes(`${f}::${line}`))
      .map(({ line }) => line);
    assert.deepEqual(unexpected, []);
  });

  it('aucun fichier core/i18n n’est créé', () => {
    assert.equal(fs.existsSync(path.join(root, 'core', 'i18n')), false);
  });

  it('jeedom2ha_mapping_override.js : aucune ligne modifiée ni retirée (seuls des ajouts sont admis)', () => {
    const diff = diffAgainstBase(['-U0'], ['desktop/js/jeedom2ha_mapping_override.js']);
    if (diff !== null) assert.deepEqual(removedLines(diff), []);
  });

  it('la partition des causes n’est dupliquée nulle part (COMMAND_CAUSE_CATEGORIES / categoryOfCause hors du module pur)', () => {
    for (const file of fs.readdirSync(path.join(root, 'desktop/js')).filter((f) => f.endsWith('.js') && f !== 'jeedom2ha_mapping_override.js')) {
      assert.doesNotMatch(fs.readFileSync(path.join(root, 'desktop/js', file), 'utf8'), /COMMAND_CAUSE_CATEGORIES|categoryOfCause/, file);
    }
  });
});

describe('25.4 / AC32 — aucune copie ni re-sérialisation des états', () => {
  it('aucun JSON.stringify ni copie profonde des états (payload.equipments, agrégats) dans la page B et dans la vue', () => {
    for (const file of ['jeedom2ha_overview.js', 'jeedom2ha_workview.js']) {
      const code = stripComments(fs.readFileSync(path.join(root, 'desktop/js', file), 'utf8'));
      assert.doesNotMatch(code, /structuredClone/, file);
      // Le seul JSON.* de la vue est le repli de session de l'état d'URL (pièce, équipement, filtre), jamais les états.
      for (const call of code.match(/JSON\.(stringify|parse)\([^)]*\)/g) || []) {
        assert.doesNotMatch(call, /equipments|payload|entries|overview|snapshot|valid/, file + ' : ' + call);
      }
    }
  });

  it('la liste blanche et le budget de la route ne sont pas touchés (projection, durée de cache, relais ajax de la lecture)', () => {
    const slice = (text, from, to) => text.slice(text.indexOf(from), text.indexOf(to, text.indexOf(from)));
    const pyBase = fileAtBase('resources/daemon/transport/http_server.py');
    const phpBase = fileAtBase('core/ajax/jeedom2ha.ajax.php');
    // Une base disponible pour `git diff` l'est aussi pour `git show <base>:<fichier>` : sinon le garde serait muet.
    if (diffAgainstBase(['--stat'], ['core/ajax/']) !== null) assert.ok(pyBase !== null && phpBase !== null, 'fileAtBase sans contenu');
    if (pyBase === null || phpBase === null) return; // aucune base : garde sans effet
    const py = fs.readFileSync(path.join(root, 'resources/daemon/transport/http_server.py'), 'utf8');
    const php = fs.readFileSync(path.join(root, 'core/ajax/jeedom2ha.ajax.php'), 'utf8');
    const projection = ['def _project_equipment_state', 'def _build_equipment_states'];
    assert.ok(py.includes(projection[0]));
    // Story 24.4 (R1) : la signature gagne deux paramètres et la projection trois champs additifs (bloc commenté « Story 24.4 »).
    const unchanged = (text) => slice(text, ...projection)
      .replace(/def _project_equipment_state\([^)]*\) -> Dict\[str, Any\]:/, 'def _project_equipment_state')
      .replace(/ {8}# Story 24\.4 \(R1, additif\)[\s\S]*?"scope_inherit": [^\n]*\n/, '');
    assert.equal(unchanged(py), unchanged(pyBase).replace(/def _project_equipment_state[^\n]*/, 'def _project_equipment_state'), 'liste blanche (projection) modifiée');
    const constants = (text) => text.split('\n').filter((l) => /^_EQUIPMENT_STATES_/.test(l)).join('\n');
    assert.equal(constants(py), constants(pyBase), 'constantes de la route modifiées');
    const relay = ["$action == 'getEquipmentStates'", 'else if ($action =='];
    assert.ok(php.includes(relay[0]) && phpBase.includes(relay[0]), 'relais getEquipmentStates introuvable');
    assert.equal(slice(php, ...relay), slice(phpBase, ...relay), 'relais getEquipmentStates modifié');
    // Story 25.8 (Q1 B) : la projection porte `present_in_ha` (état final, base déjà porteuse de 25.8).
    assert.ok(py.includes('{"override_pending": e["override_pending"], "present_in_ha": e["present_in_ha"]}'));
  });

  it('292 équipements de la forme la plus lourde : calcul de l’arbre, des KPI et des filtres mesuré (consigné, sans seuil)', (t) => {
    const big = makeScene({ rooms: 12, equipments: 292, seed: 25, longNames: true, grouped: true, unread: 5 });
    const rooms = W.decorateRooms(big.scene.objects ? [] : []);
    void rooms;
    const raw = [];
    Object.entries(big.scene.eqlogics).forEach(([key, list]) => {
      const id = key === 'null' ? 0 : Number(key);
      const object = big.scene.objects.find((o) => o.id === id);
      raw.push({ object_id: id, object_name: object ? object.name : 'Sans pièce', equipments: list.map((e) => ({ eq_id: e.id, eq_name: e.name, enabled: e.enabled })) });
    });
    const decorated = W.decorateRooms(raw);
    const timeOf = (fn) => { const t0 = process.hrtime.bigint(); fn(); return Number(process.hrtime.bigint() - t0) / 1e6; };
    let overview;
    const computeMs = timeOf(() => { overview = O.computeOverview(raw, big.equipments); });
    const treeMs = timeOf(() => { W.buildTreeModel({ rooms: decorated, groups: null, overview, filter: null, search: '', expanded: Object.fromEntries(decorated.map((r) => [r.object_id, true])), selectedRoom: null, selectedEq: null }); });
    const filterMs = timeOf(() => { ['published', 'blocked', 'to_apply', 'other', 'unread'].forEach((f) => W.buildTreeModel({ rooms: decorated, groups: null, overview, filter: f, search: 'eq', expanded: {}, selectedRoom: null, selectedEq: null })); });
    const kpiMs = timeOf(() => { overview.rooms.forEach((r) => { M.buildRoomCounterLabels(r.summary); W.buildTreatList(r, big.equipments, decorated.find((d) => d.object_id === r.object_id)); }); });
    t.diagnostic(`292 équipements — états + agrégats : ${computeMs.toFixed(1)} ms ; arbre complet : ${treeMs.toFixed(1)} ms ; 5 filtres + recherche : ${filterMs.toFixed(1)} ms ; KPI + « À traiter » : ${kpiMs.toFixed(1)} ms`);
    for (const ms of [computeMs, treeMs, filterMs, kpiMs]) assert.ok(Number.isFinite(ms));
    assert.equal(overview.total, 292);
  });
});

describe('25.4 / AC15 — parité d’état entre l’arbre (entrée agrégée) et le détail (arbre unitaire)', () => {
  maybe('pour chaque équipement du corpus de 25.2 : le mot d’état de la ligne d’arbre égale le badge du détail, avant et après une relecture', () => {
    const ids = Object.keys(FIXTURE);
    const objects = [{ id: 10, name: 'Zone fictive', father_id: null, display: {} }];
    const eqlogics = { 10: ids.map((id) => ({ id: Number(id), name: 'Eq ' + id, enabled: FIXTURE[id].enabled !== false })) };
    const equipments = {};
    ids.forEach((id) => { equipments[id] = clone(FIXTURE[id].aggregated); });
    const ui = startWorkview({ scene: { objects, eqlogics, doc: 'https://doc.example.test/plugin' }, equipments });
    openCard(ui, 10);
    for (const id of ids) {
      ui.selectEquipment(Number(id), ok(clone(FIXTURE[id].tree)));
      const treeWord = ui.text(`.j2ha-wv-eq[data-eq-id="${id}"] .j2ha-state-word`).trim();
      const badge = ui.text(`.j2ha-eq-panel[data-eq-id="${id}"] .j2ha-eq-publish-badge`).trim();
      assert.equal(treeWord, badge, 'équipement ' + id);
      assert.equal(treeWord, M.EQUIPMENT_STATE_LABELS[M.resolveEquipmentState(equipments[id], FIXTURE[id].enabled !== false).state]);
      // Relecture simulée : un nouveau rendu de B rafraîchit le badge depuis l'entrée agrégée (mêmes fonctions).
      ui.page.render();
      assert.equal(ui.text(`.j2ha-eq-panel[data-eq-id="${id}"] .j2ha-eq-publish-badge`).trim(), treeWord, 'après relecture ' + id);
    }
  });

  maybe('« À traiter » : les causes de la liste (entrée agrégée) sont celles de l’encart du détail (arbre unitaire)', () => {
    const ids = Object.keys(FIXTURE).filter((id) => M.groupBlockedCauses(FIXTURE[id].tree).length > 0);
    assert.ok(ids.length >= 1, 'le corpus contient un équipement bloqué');
    for (const id of ids) {
      assert.deepEqual(
        M.groupBlockedCauses(FIXTURE[id].aggregated).map((g) => [g.code, g.label, g.count]),
        M.groupBlockedCauses(FIXTURE[id].tree).map((g) => [g.code, g.label, g.count]),
        'équipement ' + id,
      );
    }
  });

  it('SCENE reste exploitable par la vue (sanity)', () => {
    assert.ok(SCENE.objects.length > 0);
  });
});
