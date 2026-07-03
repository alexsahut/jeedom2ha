# Story 13.4: Documentation, versions et handoff terrain HA Energy

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur et mainteneur jeedom2ha,
je veux que la documentation, les surfaces de version et le handoff terrain refletent le comportement HA Energy livre,
afin de finaliser l'epic 13 sans laisser de consigne obsolete ni d'ambiguite sur la configuration Home Assistant.

## Acceptance Criteria

1. **README sans mention obsolete.** Given le README public du plugin, When la story est livree, Then il ne contient plus l'affirmation obsolete selon laquelle les capteurs numeriques `POWER` / `sensor` sont prevus mais non implementes.
2. **README HA Energy explicite.** Given un utilisateur Home Assistant consulte le README, When il lit le perimetre supporte, Then il comprend que les sensors power/energy, `binary_sensor`, le state streaming et les metadata HA Energy (`device_class`, `unit_of_measurement`, `state_class`) sont supportes sur le perimetre livre.
3. **Pas de conversion dans jeedom2ha.** Given une mesure de puissance instantanee en `W`, When la documentation explique l'objectif energie, Then elle indique clairement que jeedom2ha conserve la valeur et l'unite Jeedom brutes et ne convertit pas `W` en `kWh`.
4. **Riemann cote Home Assistant.** Given un utilisateur veut obtenir des `kWh` depuis une puissance `W`, When il lit le README ou le handoff terrain, Then l'integration temporelle est decrite comme une configuration Home Assistant, notamment via l'integration Riemann ou le dashboard Energy HA, pas comme une fonction du daemon.
5. **Versions alignees.** Given les surfaces `plugin_info/info.json`, `resources/daemon/discovery/publisher.py` et `resources/daemon/main.py`, When la story est livree, Then `pluginVersion`, `_SW_VERSION` et `_VERSION` annoncent la meme version release cible ou une convention documentee justifie explicitement une difference.
6. **Handoff terrain HA Energy.** Given un dev agent ou un operateur prepare la validation finale, When il consulte la story, Then il trouve une checklist terrain HA Energy couvrant MQTT Discovery, Home Assistant, Riemann/Energy, non-regression des entites primaires et absence de conversion.
7. **Aucune modification Jeedom/scenarios.** Given cette story est documentaire et release hygiene, When elle est implementee puis validee, Then elle ne modifie aucun equipement Jeedom, aucun scenario Jeedom, aucune commande Jeedom et aucun mapping runtime hors surfaces README/version/handoff explicitement listees.
8. **Cloture epic compatible BMAD.** Given les stories 13.1, 13.2 et 13.3 sont `done`, When la story 13.4 atteint `done` apres `dev-story` puis `code-review`, Then `pe-epic-13` peut etre cloture uniquement si le sprint status et les notes de handoff sont alignes.

## Tasks / Subtasks

- [x] Task 0 - Pre-flight terrain (DEV/TEST ONLY - pas la release Market)
  - [x] Dry-run : verifier sans transferer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Selectionner le mode selon l'objectif de la story :
    - Verification disparition entites HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Verifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup termine.`

- [x] Task 1 - Mettre a jour le README public (AC: 1, 2, 3, 4, 7)
  - [x] Supprimer la mention obsolete indiquant que les capteurs numeriques `TEMPERATURE`, `HUMIDITY`, `POWER` vers `sensor` sont prevus mais non implementes.
  - [x] Documenter le perimetre reel livre : `sensor`, `binary_sensor`, state streaming, prises/switches, mesures power/energy et metadata HA Energy.
  - [x] Ajouter une explication concise de `state_class`: `measurement` pour puissance instantanee, `total_increasing` pour energie cumulative fiable.
  - [x] Expliquer que `W` reste une puissance instantanee et que l'obtention de `kWh` depuis `W` se configure cote Home Assistant via Riemann ou Energy.
  - [x] Ajouter la note de prudence : jeedom2ha ne modifie pas Jeedom, ne convertit pas les valeurs et ne cree pas d'historique retroactif.

- [x] Task 2 - Aligner les surfaces de version (AC: 5)
  - [x] Choisir la version release cible en respectant la convention existante du plugin.
  - [x] Recaler `plugin_info/info.json` (`pluginVersion`).
  - [x] Recaler `resources/daemon/discovery/publisher.py` (`_SW_VERSION`).
  - [x] Recaler `resources/daemon/main.py` (`_VERSION`).
  - [x] Documenter dans les notes de completion si une surface garde volontairement une convention differente.

- [x] Task 3 - Ajouter le handoff terrain HA Energy (AC: 4, 6, 7, 8)
  - [x] Ajouter dans la story, le README ou un artefact de handoff existant une checklist terrain HA Energy lisible.
  - [x] Inclure verification MQTT Discovery : au moins un payload `sensor` power avec `device_class=power`, `unit_of_measurement=W`, `state_class=measurement`.
  - [x] Inclure verification MQTT Discovery energy : au moins un payload energy `Wh` ou `kWh` avec `state_class=total_increasing`, si present dans le jeu terrain.
  - [x] Inclure verification Home Assistant : entites MQTT actives, non desactivees, utilisables par statistiques long-terme ou comme source Riemann.
  - [x] Inclure verification Riemann/Energy : l'integration est configuree cote HA pour transformer une puissance en energie, sans calcul dans jeedom2ha.
  - [x] Inclure non-regression : switchs et entites primaires historiques conservent leurs identifiants et restent non-`unknown`.
  - [x] Inclure garde-fou : aucune modification Jeedom/scenario/commande pendant cette validation.

- [x] Task 4 - Verifier les artefacts BMAD de cloture (AC: 8)
  - [x] Mettre a jour cette story avec les preuves de dev-story puis code-review uniquement pendant les workflows correspondants.
  - [x] Mettre a jour `sprint-status.yaml` au fil du workflow : `in-progress`, `review`, puis `done` apres code-review.
  - [x] Ne pas passer `pe-epic-13` a `done` avant validation finale de Story 13.4.

## Dev Notes

### Source de verite produit

- `pe-epic-13` vient du Sprint Change Proposal `sprint-change-proposal-2026-06-30-energy-dashboard-ha.md`, approuve le 2026-06-30.
- Story 13.1 a livre les metadata HA Energy pour sensors power/energy : `state_class=measurement` pour puissance instantanee et `state_class=total_increasing` pour energie cumulative fiable.
- Story 13.2 a etendu l'auto-detection W/Wh/kWh sans `generic_type`, avec garde-fou cumulatif pour l'energie.
- Story 13.3 a ajoute les mesures secondaires des prises mesureuses commandables sans changer le switch primaire historique.
- Story 13.4 est une story de documentation, versions et handoff : elle ne doit pas introduire de nouveau comportement runtime.

### Etat actuel utile au dev agent

- `README.md` contient encore une section "Ce que le plugin ne fait pas encore" qui annonce les capteurs numeriques `POWER` / `sensor` comme prevus mais non implementes.
- `plugin_info/info.json` annonce `pluginVersion = "0.1"`.
- `resources/daemon/discovery/publisher.py` annonce `_SW_VERSION = "0.2.0"` dans les payloads MQTT Discovery.
- `resources/daemon/main.py` annonce `_VERSION = "0.1.0"` dans les logs de demarrage daemon.
- `resources/daemon/transport/http_server.py` annonce aussi `_VERSION = "0.2.0"` pour l'API daemon ; il n'est pas dans le contenu minimal demande, mais le dev agent doit verifier si la convention de version choisie impose de l'aligner ou de documenter son statut.

### Checklist terrain HA Energy a integrer au handoff

- MQTT Discovery power : verifier un topic `homeassistant/sensor/.../config` contenant `device_class=power`, `unit_of_measurement=W`, `state_class=measurement`.
- MQTT Discovery energy : verifier un topic `homeassistant/sensor/.../config` contenant `device_class=energy`, `unit_of_measurement=Wh` ou `kWh`, `state_class=total_increasing`, quand une mesure cumulative fiable est presente.
- Home Assistant : verifier que les entites MQTT ciblees sont actives, non desactivees, non masquees, et exposees avec leurs attributs `device_class`, `unit_of_measurement` et `state_class`.
- HA Energy / Riemann : configurer et verifier cote Home Assistant l'integration Riemann pour convertir une puissance `W` en energie, ou l'utilisation directe d'un capteur energy cumulatif dans le dashboard Energy.
- Non-conversion : comparer une valeur Jeedom ou MQTT `W` brute avec la valeur HA correspondante ; jeedom2ha ne doit pas publier de `kWh` derive depuis cette puissance.
- Non-regression : verifier que les entites primaires historiques, notamment switches de prises/energie et devices deja livres par 13.1-13.3, conservent leurs identifiants et ne deviennent pas `unknown`.
- Garde-fou terrain : ne modifier aucun scenario Jeedom, aucune commande Jeedom, aucun equipement Jeedom ; la validation ne doit porter que sur publication, documentation, versions et configuration HA.

### Dev Agent Guardrails

- Ne pas coder de nouvelle logique de mapping, de publisher, de state streaming ou d'integration energie dans le daemon.
- Ne pas modifier `PRODUCT_SCOPE`, les reason codes, les predicates d'eligibilite ou les identifiants HA.
- Ne pas changer les `unique_id`, `object_id`, `node_id`, `state_topic` ou `command_topic` existants.
- Ne pas creer de conversion W -> kWh, d'historique retroactif, ni de source de verite concurrente a Jeedom.
- Ne pas modifier Jeedom ni les scenarios pendant cette story ; les actions terrain doivent rester de la verification/deploiement selon le protocole officiel si elles sont executees en dev-story.
- Ne pas improviser de documentation contradictoire : README et handoff doivent dire que Riemann/Energy est cote Home Assistant.

### Guardrail - Deploiement terrain (DEV/TEST ONLY)

- Utiliser exclusivement `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom reelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procedure parallele.
- Reference complete modes + cycle valide terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplace par le script) : `main -> beta -> stable -> Jeedom Market`.

### Project Structure Notes

- Fichiers cibles explicitement bornes : `README.md`, `plugin_info/info.json`, `resources/daemon/discovery/publisher.py`, `resources/daemon/main.py`, et eventuellement un artefact de handoff/documentation existant si le dev agent choisit de ne pas tout porter dans le README.
- `resources/daemon/transport/http_server.py` doit etre inspecte pour coherence de version, mais ne doit etre modifie que si la convention release retenue l'exige.
- Aucun test unitaire n'est attendu pour une modification purement documentaire/version, sauf si un test existant verifie explicitement les versions.
- Un grep final doit confirmer l'absence des mentions obsoletes `POWER` / `sensor` non implementes dans `README.md`.

### References

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-30-energy-dashboard-ha.md` - Story 13.4, versions, README et handoff terrain.
- `_bmad-output/planning-artifacts/epics-projection-engine.md` - Epic 13 / Story 13.4 et gates epic-level.
- `_bmad-output/planning-artifacts/architecture.md` - MQTT Discovery, suppression propre, principe "publier moins mais correctement".
- `_bmad-output/planning-artifacts/architecture-projection-engine.md` - Jeedom source de verite, registre HA versionne, scope produit.
- `_bmad-output/planning-artifacts/ha-projection-reference.md` - `sensor.mqtt`, champs MQTT Discovery et statut `sensor` ouvert.
- `_bmad-output/project-context.md` - IDs Jeedom stables, origin `sw_version`, workflow git, deploiement terrain officiel.
- `_bmad-output/implementation-artifacts/13-1-ha-energy-metadata-pour-sensors-power-energy.md` - metadata `state_class` et preuves HA Energy.
- `_bmad-output/implementation-artifacts/13-2-auto-detection-des-commandes-w-wh-kwh-sans-generic-type.md` - detection par unite W/Wh/kWh.
- `_bmad-output/implementation-artifacts/13-3-publier-les-mesures-secondaires-des-prises-mesureuses-commandables.md` - capteurs secondaires de prises mesureuses.
- `README.md`
- `plugin_info/info.json`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/main.py`

## Code Review

**Reviewer :** GPT-5 Codex (`code-review`)

**Date :** 2026-07-03

**Decision :** APPROVE - 0 finding bloquant.

**Findings :** Aucun.

### Points verifies

- README public coherent avec le comportement livre : `sensor`, `binary_sensor`, state streaming, mesures power/energy et metadata HA Energy documentes.
- Aucune mention obsolete `POWER` / `sensor` prevus non implementes dans `README.md`.
- Conversion energie correctement bornee : jeedom2ha conserve valeurs/unites Jeedom brutes ; conversion `W` -> `kWh` documentee cote Home Assistant via Riemann/Energy.
- Versions alignees sur `0.2.0` : `pluginVersion`, daemon `_VERSION`, discovery `_SW_VERSION` et `http_server.py::_VERSION`.
- Scope 13.4 respecte : les diffs propres a 13.4 sont bornes au README, aux surfaces de version et aux artefacts BMAD ; les changements runtime presents dans le worktree correspondent aux stories 13.2/13.3 deja marquees `done`.

### Validations executees

- `grep` README des mentions obsoletes : PASS, aucune occurrence.
- `python3 -m json.tool plugin_info/info.json`
- `python3 -m py_compile resources/daemon/main.py resources/daemon/discovery/publisher.py`
- Verification script des versions : `pluginVersion`, `main._VERSION`, `publisher._SW_VERSION`, `http_server._VERSION` = `0.2.0`.
- `python3 -m pytest tests/unit/test_discovery_publisher.py resources/daemon/tests/unit/test_diagnostic_export.py -q` : PASS, 47 passed, 4 warnings existants.
- `git diff --check` : PASS.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex (`create-story`, puis `dev-story`)

### Debug Log References

- Aucun test, script terrain, commande de validation d'implementation, ni modification de code execute pendant `create-story`, conformement aux contraintes utilisateur et au workflow BMAD.
- `./scripts/deploy-to-box.sh --dry-run` - PASS ; SSH/sudo OK, simulation rsync terminee, aucun fichier transfere et aucune operation sudo.
- `python3 -m json.tool plugin_info/info.json >/dev/null && python3 -m py_compile resources/daemon/main.py resources/daemon/discovery/publisher.py` - PASS.
- Verification versions par script Python - PASS : `pluginVersion`, `_VERSION`, `_SW_VERSION` = `0.2.0`.
- Grep README des mentions obsoletes `POWER` / `sensor` prevus non implementes - PASS, aucune occurrence.
- `python3 -m pytest tests/unit/test_discovery_publisher.py resources/daemon/tests/unit/test_diagnostic_export.py -q` - PASS : 47 passed, 4 warnings.
- `python3 -m pytest -q` - ECHEC environnement : 1446 passed, 24 failed, 1048 warnings ; tous les echecs reportes sont des imports `ModuleNotFoundError: No module named 'jeedomdaemon'` dans `tests/test_runtime_imports.py` et `tests/unit/test_daemon_startup.py`. Tentative de verification dependency : `python3 -m pip show jeedomdaemon` impossible car le Python local n'a pas `pip`.

### Completion Notes List

- 2026-07-02 - workflow lance : `create-story`. Story 13.4 materialisee depuis l'Epic 13 et le Sprint Change Proposal Energy HA approuve. Statut resultant : `ready-for-dev`.
- 2026-07-02 - sprint-status mis a jour : entree `13-4-documentation-versions-et-handoff-terrain-ha-energy` ajoutee en `ready-for-dev`.
- 2026-07-02 - Dev Agent Record renseigne ; aucune tache dev cochee et aucune preuve de run dev ajoutee.
- 2026-07-03 - workflow lance : `dev-story`. Statut story et sprint-status passes a `in-progress` avant implementation.
- 2026-07-03 - README public realigne : suppression des mentions obsoletes `POWER`/`sensor` non implementes, ajout du perimetre livre `sensor`/`binary_sensor`/state streaming/HA Energy, et clarification absence de conversion W -> kWh dans jeedom2ha.
- 2026-07-03 - Versions alignees sur la release cible `0.2.0` : `pluginVersion=0.2.0`, `_VERSION=0.2.0`, `_SW_VERSION=0.2.0`. `_SW_VERSION` et `resources/daemon/transport/http_server.py::_VERSION` etaient deja a `0.2.0`; aucune convention divergente retenue.
- 2026-07-03 - Handoff terrain HA Energy conserve dans la checklist de story : MQTT Discovery power/energy, verification HA, Riemann/Energy cote HA, non-conversion, non-regression entites primaires et garde-fou aucune modification Jeedom/scenario/commande.
- 2026-07-03 - Dry-run terrain execute avec succes : simulation rsync uniquement, aucun transfert et aucune operation sudo.
- 2026-07-03 - Validations locales ciblees PASS : JSON, py_compile, grep README, alignement versions, 47 tests discovery/status. Regression complete tentee mais bloquee par dependance locale absente `jeedomdaemon`; les changements de story restent bornes a documentation/version/BMAD.
- 2026-07-03 - workflow `dev-story` termine ; statut resultant : `review`.
- 2026-07-03 - workflow lance : `code-review`. Review finale APPROVE, 0 finding bloquant ; README, versions et scope documentaire/version valides. Statut resultant : `done`.

### File List

- `_bmad-output/implementation-artifacts/13-4-documentation-versions-et-handoff-terrain-ha-energy.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `README.md`
- `plugin_info/info.json`
- `resources/daemon/main.py`

### Change Log

- 2026-07-02 - Story creee via workflow `create-story`; statut initial `ready-for-dev`.
- 2026-07-03 - Story implementee via workflow `dev-story`; README, versions et handoff terrain alignes ; statut `review`.
- 2026-07-03 - Code review finale APPROVE ; story et sprint-status passes a `done`.
