# Story 24.1 : Signal d'exposition HomeKit et identifiants physiques

Status: review

> **Statut : `ready-for-dev` (2026-10-12), accordé par ClaudeBox au nom des décisions d'Alexandre du 12/10 à 13:22** (Task 0 faite, Q5 tranchée). Brouillon de cadrage initial (2026-10-12) : Rédigé par une session cloud déléguée, documentaire (aucun accès box, Home Assistant ni secret). **R1 (ClaudeBox, 12/10) intégrée** : la Task 0 est faite (règle d'exposition de Homebridge établie en lecture seule) ; deux cas restent à confirmer (Task 0 bis). Relecture de ClaudeBox obligatoire avant `ready-for-dev`. Contexte et décisions : `sprint-change-proposal-2026-10-12-parite-homekit.md` (T3, Q5, D1). Pointeurs `fichier:ligne` pris sur `main` à `b1acad7`, sauf mention du plugin Homebridge. Aucun nom réel d'équipement, de pièce, de scénario ou de personne (CC-48) : identifiants seulement.

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q5 A** : l'export (24.2) porte des identifiants seulement, aucun nom ; les champs de cette story sont portés tels quels.
- **Q1** : la sémantique « exclu par plugin » est conservée ; aucune raison `voie_native`. Le signal d'exposition ne change **pas** la priorité des exclusions.
- `ready-for-dev` accordé par ClaudeBox au nom de ces décisions.

## Story

En tant que mainteneur de la parité entre Apple Maison et Assist,
je veux que le démon sache quels équipements et quels scénarios Jeedom sont exposés à HomeKit et connaisse les identifiants physiques (`logicalId`) des équipements et des commandes,
afin que les stories suivantes décident, exportent et alignent sans jamais modifier la configuration Homebridge, les types génériques Jeedom ni l'exposition à Assist.

**Parcours : PHP + démon, lecture seule. Aucun changement de comportement, aucun écran.**

## Dépendances et décisions

- Ne dépend plus d'aucune vérification préalable (Task 0 faite) ; les deux cas de la Task 0 bis se confirment pendant le `create-story`.
- Peut démarrer avant le `done` de 22-2 (ne touche ni `http_server.py` ni `desktop/`).
- Q5 A (tranchée) : les champs sont portés tels quels, sans nom.

## Établi par ClaudeBox le 12/10 (lecture seule, plugin Homebridge)

Source : `plugins/homebridge/core/class/homebridge.class.php:2680-2710` (`discovery_cmd_eqlogics`), `core/api/homebridge.api.php:44`, `homebridge.class.php:3119-3122`. Ce code n'est pas dans ce dépôt.

- **Équipement exposé** si : (1) il appartient à un plugin **actif**, sauf `mobile` et `homebridge` ; (2) il est **dans une pièce dont `configuration.sendToHomebridge` vaut 1** ; (3) sa propre `configuration.sendToHomebridge` (entier) vaut 1.
- **Valeur par défaut** : si la clé est absente sur l'équipement, la valeur par défaut est celle de la configuration du plugin Homebridge (`config::byKey`, clé `sendToHomebridgeDefault`, défaut 1). L'API de Homebridge écarte `sendToHomebridge == 0`.
- **Scénario** (`discovery_scenario()`, `homebridge.class.php:3119`) : exposé si la clé `sendToHomebridge` est **présente** dans la configuration du scénario **et** que sa valeur n'est pas `== "0"` ; **clé absente = NON exposé** (corrigé par ClaudeBox le 12/10 (R1 de #261) : la R1 de #260 disait « absent = exposé », ce qui était faux ; cohérent avec le terrain : 5 scénarios exposés sur toute la box).
- **Lecture brute** (R1 de #261) : Homebridge teste `isset` sur le tableau brut de configuration (`utils::o2a`) puis `intval` ; `getConfiguration("cle", defaut)` (`utils::getJsonAttr`, `core/class/utils.class.php:252`) rendrait le défaut pour une clé absente **et** pour une chaîne vide. Le plugin lit donc le tableau complet et reproduit les tests à l'identique : équipement `intval(valeur) != 0` (`:2706-2709`, `homebridge.api.php:44`), défaut `intval(config::byKey("sendToHomebridgeDefault", "homebridge", 1, true))`, pièce `getConfiguration("sendToHomebridge", 0) == 1` (comparaison souple, `:2692-2697`). Une valeur inattendue ne donne jamais `null` : Homebridge en décide.
- **Liste des plugins actifs** : `plugin::listPlugin(true, false, true, true)` (`core/class/plugin.class.php:208-221`) rend une liste simple d'identifiants lue en base (table `config`, clé `active` à 1), exactement la source de Homebridge (`:2682-2687`, puis `eqLogic::byType` sans filtre sur l'activation de l'équipement). Un plugin absent de la liste (inactif, désinstallé) : `false`, `plugin_excluded`, sans autre lecture.
- **Aucun drapeau par commande** : les commandes héritent de l'équipement.
- **Cache Homebridge** (mesure du 12/10) : 123 accessoires, tous à 1 ; `logicalId` non vide pour **58**, **vide pour 65** : un `logicalId` vide est normal et donne `null`, il ne sert donc jamais de clé unique (l'export porte aussi `eq_id` et `cmd_id`).

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Aucune lecture de `sendToHomebridge`, de `logicalId` ni d'un attribut « HomeKit » dans le plugin (recherche exhaustive hors tests ; seule mention : le docstring de `mapping/button.py:45`). | `core/`, `desktop/`, `plugin_info/`, `resources/daemon/` |
| F2 | Le PHP lit les commandes (id, nom, type générique, type, sous-type, valeur, unité, visibilité, historisation) puis construit l'équipement (id, nom, pièce, activation, visibilité, plugin, type générique, exclusion, statut). | `core/class/jeedom2ha.class.php:759-769`, `:786-796` |
| F3 | Le démon normalise ce payload avec des `.get()` tolérants ; les dataclasses portent des valeurs par défaut, donc un champ optionnel ajouté ne casse aucun payload existant. | `resources/daemon/models/topology.py:74-100`, `:124-190` |
| F4 | `_to_bool(None, default)` renvoie `default` : il ne convient **pas** à un champ à trois états (vrai / faux / inconnu). | `models/topology.py:11-23` |
| F5 | Les scénarios sont lus à part (id, nom, actif) par `buildScenariosPayload` ; `scenarios_complete` y est déjà calculé. | `class.php:661-680`, `:832` ; `models/topology.py:103-108` |
| F6 | Priorité d'exclusion : équipement > plugin > pièce ; `exclusion_source` est déjà transmis. | `class.php:775-784` |

## Critères d'acceptation proposés

- **AC1.** `getFullTopology()` ajoute à chaque équipement `homekit_exposed` (`true`, `false` ou `null`) et `homekit_exposed_source`, et un `logical_id` (chaîne ou `null`) à chaque équipement et à chaque commande. Lecture seule : `getLogicalId()`, `getConfiguration()`, `config::byKey()`, `jeeObject` ; aucun `setConfiguration`, `save()` ni écriture sur un équipement, une pièce, une commande, un scénario ou la configuration de Homebridge.
- **AC2.** `homekit_exposed` **reproduit la règle de Homebridge établie ci-dessus**, en lecture seule et **à l'identique** (R1 de #261) : plugin de l'équipement dans la liste des plugins actifs et ni `mobile` ni `homebridge`, **et** pièce `== 1` (lue avec le défaut 0), **et** valeur d'équipement d'`intval` différent de 0 (à défaut de clé `isset`, `sendToHomebridgeDefault`, défaut 1). `homekit_exposed_source` dit **lequel des trois a décidé** (valeurs proposées : `plugin_excluded`, `piece`, `equipement`, `defaut_homebridge`) ; `null` avec la provenance `homebridge_absent` si le plugin Homebridge est absent ou inactif, ou `illisible` **seulement** si une lecture lève une exception (état de Homebridge, liste des plugins, configuration) ; une valeur inattendue ne donne pas `null`, Homebridge en décide. **Jamais `false` par défaut** pour une lecture impossible.
- **AC3.** Le démon porte ces champs en optionnels additifs (`None` par défaut) sur `JeedomEqLogic` et `JeedomCmd`. `from_jeedom_payload` normalise `0`/`1`/`"0"`/`"1"`/`true`/`false` sans transformer `None` en `False`. Un payload ancien, sans ces champs, produit exactement le même snapshot qu'avant.
- **AC4.** Aucun changement d'éligibilité, de mapping, de décision, de publication, de diagnostic, de cache ni de contrat 4D : golden et contrat 4D **identiques octet pour octet** ; `PRODUCT_SCOPE` inchangé ; `exportDiagnostic` (allowlist) inchangé.
- **AC5.** Un `logicalId` vide ou absent est transporté comme `null` (jamais comme chaîne vide) ; les `logicalId` ne sont écrits dans aucun journal de niveau `info` ou supérieur, ni dans le diagnostic existant ni dans son export (ils peuvent contenir des adresses d'appareil).
- **AC6.** **Scénarios** : `buildScenariosPayload` ajoute `homekit_exposed` (vrai si la clé `sendToHomebridge` est présente dans la configuration du scénario et que sa valeur n'est pas `== "0"` ; **clé absente = non exposé**, corrigé par ClaudeBox le 12/10 (R1 de #261)) avec la provenance `scenario_configuration` ; le démon le porte sur `JeedomScenario` de la même manière additive ; sans effet sur la publication des boutons (21-1 inchangée).
- **AC7.** Tests : extraction PHP de la topologie (équipement exposé, pièce à 0, équipement à 0, clé absente avec défaut 1 puis 0, plugin `mobile` / `homebridge`, plugin inactif, Homebridge absent, valeur illisible, scénario) ; normalisation Python (trois états, payload ancien) ; recherche dans le diff prouvant l'absence d'écriture sur la configuration Jeedom ou Homebridge.
- **AC8.** Aucun nom réel dans le code de test, les fixtures, la story, la PR (CC-48).

## Tâches proposées

- [x] **Task 0 — Établie par ClaudeBox le 12/10** (voir plus haut) : règle d'exposition, valeur par défaut, scénarios, absence de drapeau par commande, état des `logicalId`.
- [x] **Task 0 bis — Établie par ClaudeBox (lecture seule du code du plugin Homebridge sur la box)** : la règle exige un identifiant de pièce non nul, différent de -1, une pièce existante et la clé `sendToHomebridge` égale à 1 (lue avec la valeur par défaut 0) sur la pièce. Donc (a) un équipement **sans pièce** n'est pas exposé, et (b) une pièce **sans clé** `sendToHomebridge` vaut 0 : ses équipements ne sont pas exposés. Dans les deux cas : `homekit_exposed = false` avec la provenance `piece` (et non `null`). Implémenté et testé (`jeedom2ha_homekit_eq_exposure`, cas « Task 0 bis » du test PHP).
- [x] **Task 1 — PHP** : `core/php/jeedom2ha_homekit_exposure.php` (règle pure) ; `buildHomekitExposureContext` (lecture de l'installation/activation de `homebridge`, `sendToHomebridgeDefault`, `plugin::listPlugin(true, false, true, true)`) ; `getFullTopology()` ajoute `homekit_exposed`, `homekit_exposed_source`, `logical_id` (équipement et commande) ; `buildScenariosPayload` ajoute le signal des scénarios.
- [x] **Task 2 — Démon** : champs additifs `None` par défaut sur `JeedomEqLogic`, `JeedomCmd`, `JeedomScenario` ; `_to_tristate`, `_normalize_logical_id` ; éligibilité et décisions non touchées.
- [x] **Task 3 — Tests** : `tests/unit/test_story_24_1_php_homekit_exposure.php` (40 assertions), `tests/unit/test_story_24_1_homekit_signal.py` (36 tests) ; golden et contrat 4D inchangés (suite complète verte).
- [x] **Task 4 — Documentation de développement** : `docs/dev-homekit-exposure.md` (contrat des champs et règle de Homebridge, date et source).

## Garde-fous

- **Le plugin n'écrit jamais** la configuration Homebridge, les types génériques Jeedom ni l'exposition à Assist (exigence 5).
- La règle d'exposition est celle d'un autre plugin : elle est documentée avec sa date et sa source ; un écart futur de Homebridge se corrige ici, pas dans les stories suivantes.
- Aucun changement de ce qui est publié ; si le golden bouge, la story est refusée.
- Aucun accès SSH, box ou Home Assistant depuis la session cloud ; `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Les deux cas de la Task 0 bis ; la stabilité de la règle de Homebridge entre ses versions ; la lecture effective de `config::byKey('sendToHomebridgeDefault', 'homebridge')` depuis le plugin (droits, nom de classe).

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, midi — R1 (ClaudeBox) : Task 0 faite (règle d'exposition de Homebridge).
- 2026-10-12, 13:22 — Décisions d'Alexandre (relayées par ClaudeBox) : Q5 A ; Q1 : « exclu par plugin » conservé. `ready-for-dev` accordé par ClaudeBox.
- 2026-10-12 — R1 ClaudeBox intégrée (B1 scénarios absent = non exposé, B2 lecture brute à l'identique, B3 liste des plugins actifs seule).
- 2026-10-12 — Dev-story (session cloud déléguée) : Tasks 0 bis à 4 faites, statut `review`. Précision de ClaudeBox sur la Task 0 bis intégrée (sans pièce et pièce sans clé : `false`, provenance `piece`).

## Dev Agent Record

### Agent Model Used

Session cloud déléguée (dev-story), sans accès box, Home Assistant ni secret.

### Completion Notes

- Règle pure dans `core/php/jeedom2ha_homekit_exposure.php` (sans cœur Jeedom, donc testée en CI) ; la lecture du contexte (`plugin::byId('homebridge')`, `config::byKey('sendToHomebridgeDefault', 'homebridge', 1, true)`, `plugin::listPlugin(true, false, true, true)`, `jeeObject::getConfiguration`) est dans `jeedom2ha::buildHomekitExposureContext`. Le plugin Homebridge n'est jamais appelé.
- Ordre d'évaluation : Homebridge absent/inactif (`null`, `homebridge_absent`) → plugin (`false`, `plugin_excluded`) → pièce (`false`, `piece`) → équipement (`equipement`) → défaut (`defaut_homebridge`). `null`/`illisible` seulement sur exception de lecture.
- **Forme de la liste des plugins confirmée par ClaudeBox (R1 de #261)** : liste simple d'identifiants lue en base ; le repli `plugin_active_probe` est retiré, la liste fait foi. Reste à vérifier sur la box la lecture de `config::byKey(..., 'homebridge', 1, true)` (droits).
- Aucun changement de topic, d'`unique_id`, de payload de découverte, d'éligibilité, de contrat d'override ; aucune dépendance ; `transport/http_server.py` et `desktop/` non touchés ; `exportDiagnostic` inchangé.
- Absence d'écriture : recherche dans le diff (`setConfiguration|setLogicalId|->save(|config::save|config::remove`) sans résultat sur les lignes ajoutées, doublée par `test_php_additions_are_read_only`.

### File List

- `core/php/jeedom2ha_homekit_exposure.php` (nouveau)
- `core/class/jeedom2ha.class.php`
- `resources/daemon/models/topology.py`
- `tests/unit/test_story_24_1_php_homekit_exposure.php` (nouveau)
- `tests/unit/test_story_24_1_homekit_signal.py` (nouveau)
- `docs/dev-homekit-exposure.md` (nouveau)
- `docs/operations/delegations.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- cette story

### R1 ClaudeBox intégrée (PR #261, tête `9f3e21d`)

- **B1** : scénario, clé absente = **non exposé** (code, AC6, section « Établi par ClaudeBox », doc, proposition de changement) — corrigé par ClaudeBox le 12/10 (R1 de #261).
- **B2** : lecture du tableau brut de configuration (`getConfiguration()` sans argument) et tests de Homebridge reproduits à l'identique (`isset`, `intval`, comparaison souple de la pièce) ; `jeedom2ha_homekit_flag` et le `null` sur valeur inattendue retirés ; `null`/`illisible` seulement sur exception de lecture.
- **B3** : la liste `plugin::listPlugin(true, false, true, true)` fait foi ; repli `plugin_active_probe` retiré ; plugin hors liste : `false`, `plugin_excluded` ; liste illisible : `null`.
- Tests PHP ajustés (50 assertions).

### Preuve attendue (R1 ClaudeBox)

24-1 ne rend `homekit_exposed` visible nulle part (l'export arrive avec 24-2). La preuve de 24-1 est donc une **non-régression** : inventaire MQTT et registres HA inchangés, démon sain, topologie acceptée avec les mêmes effectifs. La comparaison au cache de Homebridge (123 accessoires, 5 scénarios) se fait sur le premier export de 24-2 et devient un critère de sa baseline.
