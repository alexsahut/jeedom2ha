# Signal d'exposition HomeKit et identifiants physiques (story 24.1)

Documentation de développement (interne, aucune visibilité utilisateur). Le plugin **lit** ce que Homebridge expose ; il n'écrit jamais la configuration de Homebridge, les types génériques Jeedom ni l'exposition à Assist.

## Contrat des champs (`getFullTopology()` → démon)

| Niveau | Champ | Valeurs |
|---|---|---|
| Équipement | `homekit_exposed` | `true`, `false` ou `null` (inconnu ; jamais `false` par défaut) |
| Équipement | `homekit_exposed_source` | `plugin_excluded`, `piece`, `equipement`, `defaut_homebridge`, `homebridge_absent`, `illisible` |
| Équipement, commande | `logical_id` | chaîne non vide ou `null` (un `logicalId` vide est normal : ne sert jamais de clé unique, l'export porte aussi `eq_id` et `cmd_id`) |
| Scénario | `homekit_exposed`, `homekit_exposed_source` | `true`/`false`/`null` ; provenance `scenario_configuration` (ou `illisible`) |

Côté démon, `JeedomEqLogic`, `JeedomCmd` et `JeedomScenario` portent ces champs en optionnels additifs (`None` par défaut) ; `_to_tristate` ne transforme jamais `None` en `False`. Le signal ne modifie aucune éligibilité, décision, publication, priorité d'exclusion (« exclu par plugin » conservé, pas de raison `voie_native`) ni le contrat 4D.

## Règle de Homebridge reproduite (lecture seule)

Source : plugin Homebridge, `core/class/homebridge.class.php:2680-2710` (`discovery_cmd_eqlogics`), `core/api/homebridge.api.php:44`, `homebridge.class.php:3119-3122` — code hors de ce dépôt, lu le 2026-10-12 par ClaudeBox. Implémentation : `core/php/jeedom2ha_homekit_exposure.php`. Un écart futur de Homebridge se corrige **là**.

Dans l'ordre, pour un équipement :

1. Plugin Homebridge absent ou inactif → `null`, `homebridge_absent`.
2. Plugin de l'équipement inactif (liste `plugin::listPlugin(true, false, true, true)`), ou `mobile` ou `homebridge` → `false`, `plugin_excluded`.
3. Pièce : identifiant non nul, différent de -1, pièce existante, et `sendToHomebridge` = 1 lu avec la valeur par défaut 0. **Équipement sans pièce** ou **pièce sans clé** (= 0) → `false`, `piece` (et non `null`) — établi par ClaudeBox le 2026-10-12 (Task 0 bis).
4. `configuration.sendToHomebridge` de l'équipement = 1 → `true`/`false`, `equipement` ; clé absente → `sendToHomebridgeDefault` du plugin `homebridge` (`config::byKey`, défaut 1), `defaut_homebridge`.

Aucun drapeau par commande : les commandes héritent de l'équipement. Scénario : exposé si `configuration.sendToHomebridge` est différent de « 0 » (absent = exposé). Toute valeur illisible donne `null` avec la provenance `illisible`.

## Garde-fous

- Lecture seule : `getLogicalId()`, `getConfiguration()`, `config::byKey()`, `plugin::byId()`, `plugin::listPlugin()`, `jeedom2ha_homekit_*` ; aucun `setConfiguration`, `save()` ni `config::save` dans le code ajouté (test `test_php_additions_are_read_only`).
- Les `logicalId` ne sont écrits dans aucun journal de niveau `info` ou supérieur, ni dans le diagnostic ni dans son export (`exportDiagnostic` est une allowlist, inchangée) ; ils sont exclus du `repr` des dataclasses.
- Tests : `tests/unit/test_story_24_1_php_homekit_exposure.php` (règle, Task 0 bis, scénarios), `tests/unit/test_story_24_1_homekit_signal.py` (normalisation à trois états, payload ancien).
