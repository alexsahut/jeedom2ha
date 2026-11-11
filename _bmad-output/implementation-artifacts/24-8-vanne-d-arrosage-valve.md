# Story 24.8 : Vanne d'arrosage : `valve`

Status: review

> **Brouillon de cadrage (2026-10-12), `draft` jusqu'à son `create-story`, après la baseline.** Rédigé par une session cloud déléguée, documentaire. **Change la production et ouvre un composant** (`valve`, FR40/NFR10). Décisions attendues d'Alexandre : **Q9** (relation avec l'epic 18) et **Q10** (remplacement d'entités existantes) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
>
> **R1 (ClaudeBox, 12/10) intégrée** : deux vannes concernées, types génériques établis ; **l'une relève d'un plugin Z-Wave** : voir ci-dessous.

## Story

En tant qu'utilisateur dont une vanne d'arrosage est exposée à HomeKit,
je veux la retrouver dans Home Assistant comme une vanne (ouvrir, fermer, état),
afin de la piloter par Assist.

**Parcours : démon.** Recoupe la story 18.4 du backlog (Q9 A : absorbée par celle-ci).

## Dépendances et décisions

- Dépend de **24.4**. Une seule story de type en cours à la fois.
- **23.3** : même règle que 24.6 (une entrée de streaming après sa fusion, sinon optimiste documenté).
- **Q9 A** et **Q10 A** (tranchées).

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q9 A** (version ajustée R1) : l'epic 24 absorbe 18-4 (`valve`).
- **Q10 A** : remplacement, une seule voie par équipement ; inventaire des références avant/après.
- **Q1** : « exclu par plugin » conservé (pas de `voie_native`).

## Établi par ClaudeBox le 12/10 (mesure du 10/10)

- **Deux vannes** portent `IRRIG_ON`, `IRRIG_OFF`, `IRRIG_STATE` (trio complet : ordres + état), dont **une appartient à un plugin Z-Wave**.
- **Point à trancher avant le `create-story`** : si ce plugin Z-Wave figure dans la liste `excludedPlugins` (plugins natifs : « exclu par plugin », décision Q1), cette vanne **n'est pas publiée par jeedom2ha** et sort de cette story (sa voie est l'intégration native de HA) ; seule l'autre vanne la concerne. À confirmer par ClaudeBox à partir de l'export (champ `plugin` et `reason: excluded_plugin`).
- `IRRIG_*` n'est pas un type du core (famille Homebridge) : le gel du référentiel (Task 0) reste nécessaire.

## Task 0 faite par ClaudeBox le 2026-11-11 (export de production, lecture seule)

Source : `/system/decision_export` et `/system/state_listeners` du démon de production, relevés par la sonde CC-48 v2 (11/11, 19:44). Catalogue des types gelé par clawcode à partir des sources du plugin Homebridge installé ; aucune occurrence côté core.

**Types génériques de vanne (Homebridge, gelés)** : `IRRIG_STATE/ON/OFF`, `FAUCET_STATE/ON/OFF`, `VALVE_STATE/ON/OFF` (+ `VALVE_SET_DURATION`, `VALVE_REMAINING_DURATION`, hors périmètre par AC7). Aucun type de position : `reports_position: false`.

**Équipements concernés (3, tous `published`, `homekit_exposed_effective: true`, pièce 11)** :

| eq | plugin | Trios de vanne (STATE / ON / OFF) | Publication actuelle |
|---|---|---|---|
| 461 | zwavejs | 4144 / 4145 / 4146 | `sensor` sur 4147 (sans type générique) ; commandes IRRIG en `command_not_covered` |
| 462 | zwavejs | zone 1 : 4156 / 4157 / 4158 ; zone 2 : 4159 / 4160 / 4161 | publié, commandes IRRIG en `command_not_covered` |
| 527 | virtual | 4849 / 4845 / 4848 | publié, commandes IRRIG en `command_not_covered` |

- `zwavejs` **n'est pas** dans `excludedPlugins` : les deux vannes Z-Wave sont dans le périmètre (le point « voie native » de R1 est levé). Côté HA, les entités Z-Wave natives sont toutes `unavailable` le 11/11.
- Aucune commande de vanne n'a d'entité HA aujourd'hui : la story est **additive** pour ces commandes (pas de remplacement d'entité vanne existante) ; Q10 A s'applique aux autres entités des mêmes équipements seulement si le mapping les modifie (inventaire avant/après exigé, AC5).

## Décisions d'Alexandre (2026-11-11, ~20:00)

- **D1 — Vannes Z-Wave portées par jeedom2ha** : 461, 462 et 527 sont projetées en `valve` par le plugin.
- **D2 — Une vanne par zone** : un équipement qui porte plusieurs trios `*_STATE/ON/OFF` produit une entité `valve` par trio (agrégation multi-entité structurelle, comme le multi-switch de 11.3) ; appariement des trios par l'info liée des actions (`value` de l'action = id de la commande STATE), à défaut par ordre d'id ; un trio incomplet n'est pas publié en `valve` (pas d'ordre deviné).
- **D3 — Preuve terrain sur le virtuel 527 seulement** : ouverture/fermeture réelles uniquement sur 527 ; pour 461 et 462, vérification en lecture seule (entités, topics, `optimistic: false`, état retenu = état Jeedom), **aucun ordre envoyé**.

## Décisions techniques ClaudeBox (2026-11-11)

- **D4** — `valve` sans position : `payload_open`/`payload_close` traduits par `sync/command.py` vers les actions ON/OFF ; `state_topic` + `state_open: open` / `state_closed: closed` ; état binaire 0/1 traduit avec `invertBinary` comme pour `switch` ; `optimistic: false` quand STATE existe, sinon le trio est incomplet (D2) et rien n'est publié en `valve`.
- **D5** — `device_class: water` pour `IRRIG_*` et `FAUCET_*`, aucune `device_class` pour `VALVE_*`.
- **D6** — Ordre des mappers : la vanne est reconnue avant `switch` et le repli, sans changer la projection des équipements qui n'ont aucun type de vanne (golden inchangés).

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Aucune occurrence de `VALVE_*`, `FAUCET_*` ni `IRRIG_*` dans le code du démon ; ces familles viennent du plugin Homebridge, pas du core. | recherche dans `resources/daemon/` |
| F2 | Le référentiel dual-source (core ∪ Homebridge) devait être gelé par la story 18.0, jamais faite. | `epics-projection-engine.md` (Epic 18) ; `sprint-change-proposal-2026-07-17-couverture-domaines-ha.md` |
| F3 | `valve.mqtt` est documenté dans le référentiel ; `valve` n'est ni dans le registre ni dans `PRODUCT_SCOPE`. | `ha-projection-reference.md:125,345-351` ; `validation/ha_component_registry.py:26-70` |
| F4 | Sans mapper dédié, un équipement à commandes typées inconnues tombe sur les mappers génériques ou le repli (`sensor`/`button` ambigus). | `mapping/registry.py:24-35` ; `mapping/fallback.py` |

## Critères d'acceptation proposés (à figer selon Q9 et Q10)

- **AC1.** Ouverture gouvernée de `valve` dans le même incrément : entrée de registre avec champs requis et capacités ; cas nominal et cas d'échec de `validate_projection()` ; `PRODUCT_SCOPE` mis à jour ; contrat 4D non régressé ; `SWITCH_*`/`ENERGY_*` non régressés.
- **AC2.** Un équipement qui porte les types génériques de vanne gelés en Task 0 est projeté en `valve` (ouvrir, fermer, état) ; position seulement si une commande de position existe.
- **AC3.** **Aucun état menteur** : sans état fiable, la vanne est optimiste et documentée ; avec un état réel, `optimistic: false` (règle de 23.3).
- **AC4.** Payload avec `default_entity_id = valve.<object_id>` (22-1) ; commandes traduites par `sync/command.py` ; aucun ordre sans commande Jeedom correspondante.
- **AC5.** Cycle de vie (Q10 A) : dépublication de l'ancienne entité, publication de la nouvelle, inventaire des identifiants et des références avant/après.
- **AC6.** Override pe-epic-16 compatible (la vérification de familles de commandes connaît `valve`).
- **AC7.** Aucune minuterie, aucun programme d'arrosage, aucun débit : hors périmètre.
- **AC8.** Golden et contrat 4D verts ; aucun nom réel (CC-48) ; preuve terrain par ClaudeBox sur une vanne de test.

## Tâches proposées

- [x] **Task 0 — Gel du référentiel pour `valve`** (mini-18.0) : types génériques de vanne (core ∪ Homebridge) → champs de `valve.mqtt` (documentation officielle HA 2026.9.4, D4) ; liste, par ClaudeBox, des équipements concernés et de leurs commandes réelles. *(ClaudeBox, 2026-11-11.)*
- [x] **Task 1 — Registre** : `valve` dans `HA_COMPONENT_REGISTRY` et `PRODUCT_SCOPE`, `ValveCapabilities`, preuve FR40 (nominal + échecs), publisher enregistré (AR13).
- [x] **Task 2 — Mapper** : `mapping/valve.py`, trios IRRIG_/FAUCET_/VALVE_, une vanne par trio (D2), trio incomplet ou ambigu sans vanne, passe dédiée avant tous les mappers et vanne ajoutée aux entités existantes (D6).
- [x] **Task 3 — Publication** : `publish_valve` / `_build_valve_payload` (D4, D5, 22-1).
- [x] **Task 4 — Commande** : OPEN/CLOSE → actions ON/OFF du trio (`sync/command.py`).
- [x] **Task 5 — État** : STATE 0/1 → `open`/`closed`, `invertBinary` lu, streaming (`sync/readback.py`, `sync/state.py`), `optimistic: false`.
- [x] **Task 6 — Override et export** : familles de commandes (pe-epic-16), profil, `_ACTUATOR_TYPES` de l'export de décision.
- [x] **Task 7 — Tests et documentation** : `test_story_24_8_vanne_arrosage_valve.py`, `docs/fr_FR/index.md`, `changelog_beta.md`.
- [ ] **Gate, déploiement, preuve terrain (humain / ClaudeBox)** : D3 — ouverture/fermeture réelles sur le virtuel 527 seulement ; 461 et 462 en lecture seule ; inventaire avant/après (AC5).

## Garde-fous

- Une vanne peut inonder : aucun essai sur une vanne réelle sans l'humain.
- Pas de mapper deviné : si le référentiel de types n'est pas gelé, la story ne démarre pas.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Les types génériques exacts de vanne présents dans l'installation ; les champs de `valve` dans HA 2026.9.4 ; la présence d'un état fiable sur les équipements concernés.

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q9 A (absorbe 18-4), Q10 A ; Q1 « exclu par plugin » conservé.
- 2026-11-11 — Task 0 (ClaudeBox, export de production) ; décisions D1-D3 d'Alexandre, D4-D6 ClaudeBox ; `ready-for-dev` accordé par ClaudeBox.
- 2026-11-11 — dev-story (session cloud déléguée) : Tasks 1 à 7, story en `review` ; preuve terrain à ClaudeBox (D3).
- 2026-11-11 — relecture indépendante de la PR #370 : P2-2 (appariement par l'info liée exportée, le repli « par ordre d'id » de D2 est **retiré** pour plusieurs trios : jamais de zone devinée), P2-1 (remplacement explicite Q10 A des entités qui utilisaient une commande du trio), P3 (source unique des clés d'état, état numérique, garde 25.4 par fichier).

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée, sans accès à la box).

### Implementation Notes

- **Mapper** (`mapping/valve.py`) : familles `IRRIG`, `FAUCET`, `VALVE` ; un trio = STATE de type `info` + ON et OFF de type `action` de la même famille. Une entité `valve` par trio (`ha_unique_id` `jeedom2ha_eq_<eq>_cmd_<state>`, `object_id`/`node_id` `jeedom2ha_<eq>_<state>`, topics `jeedom2ha/<eq>/<state>/state|set`, comme le multi-switch de 11.3), confiance `sure`, `reason_code` `valve_<famille>_open_close_state`, `reason_details.valve_family` et `valve_pairing` (`linked` / `single_trio`).
- **Appariement des trios (D2, relecture P2-2)** : par **l'info liée** de chaque action. L'export PHP de topologie (`core/class/jeedom2ha.class.php`, ligne ajoutée) transmet `linked_value` = `$cmd->getValue()` pour les actions ; le démon le porte dans `JeedomCmd.linked_value` (formes `4144`, `"4144"`, `"#4144#"` ; toute autre forme -> `None`, `normalize_linked_cmd_id`). Règles par famille : nombres de STATE / ON / OFF différents -> aucune vanne ; **un seul trio** -> vanne même sans lien, mais refus si un lien existe et désigne une autre commande ; **plusieurs trios** -> chaque ON et chaque OFF doit être lié à une STATE de la famille, une ON et une OFF par STATE, sinon **aucune vanne pour la famille** (WARNING avec eq, ids des commandes et liens). Plus aucun appariement par ordre d'id.
- **Ordre des mappers (D6) et remplacement (Q10 A, relecture P2-1)** (`mapping/registry.py`, `_with_valves`) : `MapperRegistry.map_all` lance d'abord le `ValveMapper` (hors de la liste ordonnée, inchangée). Sans trio, chemin historique strictement identique. Avec des vannes : la projection d'avant est calculée sur l'équipement **complet** ; ses entités qui n'utilisent aucune commande d'un trio publié sont gardées à l'identique ; celles qui en utilisent une (ex. le `button` « sure » que `ButtonMapper` faisait sur `IRRIG_ON`, ou le repli sur la STATE) sont **retirées** avec un WARNING et jamais re-projetées : aucune entité ne réapparaît sous un `unique_id` existant avec une autre commande. Les vannes s'ajoutent ensuite ; sans entité gardée, elles suivent la règle du nom (une vanne : nom de l'équipement ; plusieurs : nom de la commande d'état).
- **Registre (AR13)** : `valve` connu (`state_topic`, `command_topic`, `platform`, `availability` ; `has_state`, `has_command`) et ouvert dans `PRODUCT_SCOPE` ; preuve `test_governance_fr40_proof_valve` ; `PublisherRegistry` (`publish_valve`).
- **Payload** : `payload_open: OPEN`, `payload_close: CLOSE`, `state_open: open`, `state_closed: closed`, `reports_position: false`, `optimistic: false` (dérivé de `has_reliable_channel`, toujours faux car le trio a son STATE), `device_class: water` pour IRRIG/FAUCET, absent pour VALVE, `default_entity_id = valve.<object_id>`, pas de `payload_stop`. Topic `homeassistant/valve/jeedom2ha_<eq>_<state>/config`.
- **Ordres** (`sync/command.py`) : topic de commande de la vanne déclaré dans `_expected_command_topics` ; `OPEN` → `<FAMILLE>_ON`, `CLOSE` → `<FAMILLE>_OFF` du trio de la vanne (jamais une autre zone) ; tout autre payload refusé ; aucune action sans sa commande Jeedom (`missing_action_command`). Confirmation `real_state_confirmation` quand l'état est streamé, sinon `stateless` : aucun état optimiste publié.
- **État** (`sync/readback.py`, `sync/state.py`) : `STATE_KEYS["valve"]` = `mapping.valve.VALVE_STATE_KEYS` (source unique) ; `valve` streamé (`_ACTIONABLE_STREAMED`) ; `valve_state()` : `1/true/on/open` ou tout nombre > 0 → `open`, `0/false/off/closed` ou 0 → `closed`, inversé si `invert_binary` (appliqué au résultat) ; négatif ou non fini → rien ; toute autre valeur ne publie rien.
- **`invertBinary`** : **constat** — ni le démon ni l'export PHP ne lisaient cette option avant la story ; le `switch` ne l'applique pas (contrairement à ce que dit D4 « comme pour `switch` »). Pour tenir D4 sur la vanne : `JeedomCmd.invert_binary` (défaut `False`), lu dans le payload de topologie, et **une ligne ajoutée** à l'export PHP (`core/class/jeedom2ha.class.php` : `'invert_binary' => (bool)$cmd->getDisplay('invertBinary', 0)`). Seule la vanne l'utilise ; `switch` et `binary_sensor` inchangés (point ouvert).
- **Override pe-epic-16** (`validation/ha_component_registry.py`, `_cross_family_action_mismatch`) : des capacités de vanne forcées vers tout type actionnable autre que `valve` (light, switch, cover, button, alarm_control_panel, climate, number, select) sont refusées ; seules les lectures `sensor` / `binary_sensor` restent valides ; des capacités d'une autre famille forcées en `valve` sont refusées. `valve` ajouté aux types autorisés d'un profil d'overrides. Le sélecteur de l'interface (`desktop/js/jeedom2ha_mapping_override.js`) n'est **pas** modifié (garde « aucune ligne modifiée » de 24.2) : `valve` n'y est pas proposé et son libellé français n'existe pas (point ouvert).
- **Export de décision** : `valve` dans `_ACTUATOR_TYPES` ; `entity_id_expected` lu dans le payload réel (`valve.jeedom2ha_<eq>_<state>`). État d'exécution : `_resolve_state_topic` rend le topic de la vanne.
- **Cycle de vie (AC5)** : aucune entité vanne n'existe aujourd'hui (Task 0). Entité retirée = **principal** : retypage (ex. `button` -> `valve`), topic vidé par `_detect_lifecycle_changes` (inchangé). Entité retirée = **secondaire** sous un principal gardé : **à chaud**, déjà couvert par le chemin existant du sync `_unpublish_refused_candidates` (19.4 C1 : un secondaire publié dont la clé `(cmd_id, node_id, domaine)` a disparu est dépublié, report fusionné en cas d'échec) — vérifié par tests, aucun code ajouté (un second mécanisme dépublierait deux fois : `test_t8` de 19.4 l'a montré) ; **au premier sync après un redémarrage** (le cas d'un déploiement), il n'y avait aucune décision en RAM et seul le type du principal était comparé au cache disque : ajout de `_unpublish_boot_removed_topics` (`transport/http_server.py`, branche boot de `_detect_lifecycle_changes`, hors retypage), qui vide chaque topic `(type, node_id)` du cache disque absent de la nouvelle projection (INFO `[LIFECYCLE]`, report fusionné dans `pending_discovery_unpublish` en cas d'échec ou sans publisher).
- **Golden 8.4** : le seul écart est l'apparition des compteurs `valves_ambiguous|probable|published|skipped|sure` à 0 dans le résumé de sync (compteurs générés depuis le registre des publishers) ; régénéré avec `GOLDEN_REGEN=1`, aucune projection ne change. Contrat 4D inchangé.
- **Garde 25.4** : le démon est en ajouts seuls, sauf les listes figées qui gagnent `valve` (`PRODUCT_SCOPE`, `_known_types`, `_ACTUATOR_TYPES`, leurs assertions de test, `len(PRODUCT_SCOPE)`) et la virgule du golden ; ces lignes sont déclarées dans `REPLACED_BY_24_8` sous la forme `fichier::ligne` (admises dans leur fichier seulement ; la garde lit le fichier dans l'en-tête `diff --git`).
- Champs `valve.mqtt` utilisés non revérifiés dans le source de HA 2026.9.4 par cette session (pas d'accès) : à confirmer à la preuve terrain (entité créée, `reports_position`, `device_class: water`).

### Tests

- `resources/daemon/tests/unit/test_story_24_8_vanne_arrosage_valve.py` (identifiants synthétiques 8001-8003) : registre et preuves `validate_projection` ; mono-vanne ; deux zones liées ; ids entrelacés (STATE1 10, STATE2 11, ON2 12, OFF2 13, ON1 14, OFF1 15) avec liens -> bon appariement, sans lien / lien manquant / deux OFF sur une zone / lien hors famille / lien vers une action -> aucune vanne ; deux zones sans lien -> aucune vanne ; un trio sans lien ou partiellement lié -> vanne, lié ailleurs -> refus ; lecture de `linked_value` (formes acceptées et refusées) ; familles et classe ; trios incomplets (projection d'avant) ; durées hors périmètre ; mesure existante gardée à l'identique (projection d'avant du même équipement) ; bouton sur `IRRIG_ON` retiré et remplacé, aucun rebranchement d'`unique_id` ; autres commandes non re-projetées ; payload ; topics ; dépublication multi-domaine ; ordres, routage par zone, aucun ordre sans commande ; table d'état (numérique, `invertBinary`) ; overrides croisés ; attendu HA ; export de décision ; non-régression switch / cover.
- Mis à jour : listes figées de `PRODUCT_SCOPE` / `known_types` (7.2, 7.3, 7.4, 8.2, 9.1, 9.2, 9.3, 24.7, registre), preuve FR40 (`test_step3_governance_fr40.py`), faux publisher de 19.4 (`valve` ajouté), golden 8.4 (compteurs).
- Ajout relecture 2 (AC5) : à chaud, secondaire remplacé par la vanne -> dépublication du seul secondaire, rien de retiré -> aucune, échec ou broker absent -> différé (chemin 19.4 C1) ; au boot, secondaire du cache absent -> dépublié, rien de retiré -> aucun, entrées homogènes au type du cache, échec ou sans publisher -> différé, entrée non publiée ignorée ; retypage du principal inchangé.
- `python -m pytest` (après relecture 2) : 2 834 passés, 9 désélectionnés (marqueur `load`), 0 échec. `flake8 resources/daemon tests` : 0. `node --test tests/unit/*.node.test.js` : 1 214 / 1 214. Tests PHP nécessitant le cœur Jeedom non exécutables ici ; `php -l` de la classe : OK.

### File List

- `resources/daemon/mapping/valve.py` (nouveau)
- `resources/daemon/mapping/registry.py`
- `resources/daemon/mapping/overrides.py`
- `resources/daemon/models/mapping.py`
- `resources/daemon/models/topology.py`
- `resources/daemon/validation/ha_component_registry.py`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/discovery/registry.py`
- `resources/daemon/sync/readback.py`
- `resources/daemon/sync/command.py`
- `resources/daemon/sync/state.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/export/decision_export.py`
- `core/class/jeedom2ha.class.php`
- `resources/daemon/tests/unit/test_story_24_8_vanne_arrosage_valve.py` (nouveau)
- `resources/daemon/tests/unit/test_step3_governance_fr40.py`, `test_story_19_4_guard_publisher_calls.py`, `test_ha_component_registry.py`, `test_story_7_2_wave_registry.py`, `test_story_7_3_projection_validation_wave.py`, `test_story_7_4_governance_product_scope.py`, `test_story_8_2_publisher_registry.py`, `test_story_9_1_sensor_mapper.py`, `test_story_9_2_binary_sensor_mapper.py`, `test_story_9_3_button_mapper.py`, `test_story_24_7_portail_garage_cover.py`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`
- `tests/unit/test_story_25_4_non_regression.node.test.js`
- `docs/fr_FR/index.md`, `docs/fr_FR/changelog_beta.md`
- `_bmad-output/implementation-artifacts/24-8-vanne-d-arrosage-valve.md`, `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Points ouverts

1. **Secondaire retiré** : traité (à chaud par 19.4 C1, au boot par `_unpublish_boot_removed_topics`) ; à confirmer dans l'inventaire avant/après de la preuve terrain.
1. **`invertBinary`** : D4 suppose que `switch` l'applique ; ce n'est pas le cas. Appliqué à la seule vanne (export PHP d'une option d'affichage, ajout) ; l'étendre à `switch` / `binary_sensor` est une décision distincte.
2. **Info liée sur la box** : l'appariement de 462 (deux zones) exige que ses quatre actions aient leur « Valeur » renseignée vers la STATE de leur zone ; sinon 462 n'aura **aucune** vanne. À vérifier dans l'export (`linked_value`) avant la preuve terrain.
3. **Interface** : `valve` absent du sélecteur d'override et sans libellé français (« Vanne ») — le fichier JS est sous garde « aucune ligne modifiée » (24.2).
4. **Preuve terrain (D3)** : 527 seul pour les ordres réels ; 461/462 en lecture seule ; vérifier aussi l'état inversé si l'option est cochée sur une des vannes.
