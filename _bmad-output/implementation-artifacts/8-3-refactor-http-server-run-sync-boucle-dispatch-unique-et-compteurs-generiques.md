# Story 8.3 : Refactor `http_server._run_sync` — boucle dispatch unique et compteurs generiques

Status: done

## Story

En tant que mainteneur,
je veux une boucle de dispatch unique dans `_run_sync` qui delegue mapping et publication aux deux registries,
afin que l'ajout d'un nouveau type HA ne necessite plus de modifier `http_server.py`.

## Acceptance Criteria

**AC1 — Mapping via `MapperRegistry`**
Given la fonction `_run_sync` apres refactor,
When son code est inspecte,
Then la cascade `LightMapper -> CoverMapper -> SwitchMapper` est remplacee par une iteration via `MapperRegistry`
And l'ordre effectif reste strictement `LightMapper`, `CoverMapper`, `SwitchMapper`, `FallbackMapper` terminal no-op
And aucun nouveau mapper n'est cree ou modifie dans cette story.

**AC2 — Publication via `PublisherRegistry`**
Given un `mapping.ha_entity_type` resolu,
When la publication Discovery doit etre tentee,
Then les trois branches `elif mapping.ha_entity_type == "light" / "cover" / "switch"` sont remplacees par une seule branche generique
And cette branche appelle `PublisherRegistry.publish(mapping, snapshot)` pour resoudre la methode `publish_*`
And elle preserve l'echec explicite `publisher_not_registered` si le registry l'a deja renseigne dans `mapping.publication_result`.

**AC3 — Compteurs dynamiques**
Given la structure `mapping_counters`,
When elle est initialisee et mise a jour,
Then elle est generee depuis les types connus du registry de publication (`PublisherRegistry.publishers.keys()`) et non depuis une liste hardcodee `lights_*`, `covers_*`, `switches_*`
And les compteurs par type couvrent `sure`, `probable`, `ambiguous`, `published`, `skipped`
And les logs et `summary["mapping_summary"]` lisent cette structure dynamiquement sans referencer les anciennes cles hardcodees.

**AC4 — Bookkeeping pre-publication unique**
Given un equipement mappe et une `PublicationDecision`,
When `_run_sync` prepare la publication,
Then le bookkeeping commun (`state_topic`, `active_or_alive`, `_apply_availability_metadata`, `publications[eq_id]`, `nouveaux_eq_ids.add(eq_id)`) vit dans une fonction unique partagee
And ce bloc n'est plus duplique par type HA.

**AC5 — Parite comportementale stricte**
Given les inputs actuellement couverts par `light`, `cover` et `switch`,
When une sync est executee avant et apres refactor,
Then chaque equipement conserve strictement les memes `mapping`, `decision`, `publication_result`, `cause_label`, `cause_action`, `reason_code`
And les valeurs semantiques des compteurs restent identiques par type, confiance, publication et skip
And le pipeline conserve l'ordre canonique : eligibilite -> mapping -> validation HA -> decision publication -> publication MQTT/diagnostic.

**AC6 — Cadre de garantie pe-epic-8**
Given le diff de la story,
When il est relu,
Then aucun nouveau type n'est publie
And `PRODUCT_SCOPE`, `HA_COMPONENT_REGISTRY`, `validate_projection`, `decide_publication`, `cause_mapping.py`, les mappers existants et les publishers existants restent inchanges
And `sensor`, `binary_sensor` et `button` ne sont pas ajoutes au `PublisherRegistry` dans cette story.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : verifier sans transferer : `./scripts/deploy-to-box.sh --dry-run` — tente le 2026-05-03, bloque localement car `JEEDOM_BOX_HOST` n'est pas defini
  - [x] Selectionner le mode selon l'objectif de la story : mode cible retenu pour smoke terrain post-tests = `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
    - Verification disparition entites HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Verifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup termine.` — non executable dans cet environnement sans `JEEDOM_BOX_HOST`; a valider terrain avant passage `done`

- [x] Task 1 — Preflight code et scope (AC: 5, 6)
  - [x] Confirmer que `main` contient la Story 8.1 PR #107 et la Story 8.2 PR #108
  - [x] Relire `resources/daemon/transport/http_server.py:997-1224` avant edition
  - [x] Verifier que les seuls fichiers de production modifies sont limites a `resources/daemon/transport/http_server.py`
  - [x] Ne pas refactorer opportunistement `_republish_all_from_cache()` : la cible Story 8.3 est `_run_sync`

- [x] Task 2 — Brancher `MapperRegistry` dans `_run_sync` (AC: 1, 5)
  - [x] Remplacer l'instanciation directe `LightMapper()`, `CoverMapper()`, `SwitchMapper()` par `MapperRegistry()`
  - [x] Remplacer la cascade `mapping = light_mapper.map(...)` puis cover/switch par `mapper_registry.map(eq, snapshot)`
  - [x] Conserver le comportement `mapping is None -> continue` puisque `FallbackMapper` est no-op dans pe-epic-8
  - [x] Supprimer les imports de mappers devenus inutilises dans `http_server.py` si plus aucun code du fichier ne les utilise

- [x] Task 3 — Construire les compteurs generiques depuis le registry (AC: 3, 5)
  - [x] Initialiser `mapping_counters` depuis les cles exposees par `PublisherRegistry.publishers.keys()` via un helper d'inspection, sans liste parallele `light/cover/switch`
  - [x] Conserver le cas bridge absent : les compteurs doivent quand meme exister, mais aucun objet d'inspection ne doit etre passe a un chemin qui pourrait publier sans `mqtt_bridge` connecte
  - [x] Centraliser l'incrementation confidence : `mapping.confidence in {"sure", "probable", "ambiguous"}` -> compteur `<type>_<confidence>`
  - [x] Centraliser l'incrementation `published` uniquement quand `decision.active_or_alive` devient `True`, comme aujourd'hui
  - [x] Centraliser l'incrementation `skipped` quand `decision.active_or_alive` reste `False`, comme aujourd'hui
  - [x] Mettre a jour le log `[MAPPING] Summary` pour iterer sur `mapping_counters` sans cles hardcodees
  - [x] Verifier par `rg` qu'aucun consommateur frontend ou test ne depend des anciennes cles `lights_*`, `covers_*`, `switches_*` — `plugin_info/configuration.php` les lit encore, donc les cles legacy sont preservees mais generees dynamiquement depuis le registry

- [x] Task 4 — Extraire le bookkeeping pre-publication commun (AC: 2, 4, 5)
  - [x] Creer un helper unique dans `http_server.py` pour renseigner `decision.state_topic = _resolve_state_topic(mapping)`
  - [x] Dans ce helper, initialiser `decision.active_or_alive = False`
  - [x] Dans ce helper, appeler `_apply_availability_metadata(decision, mapping, snapshot)`
  - [x] Dans ce helper, renseigner `publications[eq_id] = decision`
  - [x] Dans ce helper, ajouter `eq_id` a `nouveaux_eq_ids`
  - [x] Appeler ce helper une seule fois par equipement mappe, avant tentative de publication

- [x] Task 5 — Fusionner les trois branches de publication en une branche generique (AC: 2, 5, 6)
  - [x] Instancier le `PublisherRegistry` runtime avec le `publisher` reel uniquement quand `publisher` existe
  - [x] Si `decision.should_publish` est false, conserver `mapping.publication_result = _make_publication_result("not_attempted")`
  - [x] Si `decision.should_publish` est true et que le bridge/publisher est indisponible, conserver le warning existant et `discovery_publish_failed`
  - [x] Si `decision.should_publish` est true et que le bridge/publisher est disponible, appeler `await publisher_registry.publish(mapping, snapshot)`
  - [x] Si `PublisherRegistry.publish()` a deja renseigne `mapping.publication_result` avec `publisher_not_registered`, ne pas l'ecraser par `discovery_publish_failed`
  - [x] Preserver la logique `_needs_discovery_unpublish(previous_decision)` quand la publication Discovery echoue
  - [x] Preserver la publication de disponibilite locale, `decision.discovery_published`, `decision.active_or_alive` et `mapping.pipeline_step_reached = 5`

- [x] Task 6 — Tests de non-regression cibles (AC: 1, 2, 3, 4, 5, 6)
  - [x] Ajouter `resources/daemon/tests/unit/test_story_8_3_http_server_dispatch.py`
  - [x] Tester que `MapperRegistry.map()` est utilise par `_run_sync` et conserve light/cover/switch/sans mapper
  - [x] Tester que `PublisherRegistry.publish()` est appele pour `light`, `cover`, `switch`
  - [x] Tester qu'un type sans publisher conserve `technical_reason_code="publisher_not_registered"` sans `continue` silencieux
  - [x] Tester que le helper pre-publication renseigne `state_topic`, disponibilite, `publications` et `nouveaux_eq_ids` une seule fois
  - [x] Tester que `mapping_counters` est genere dynamiquement et ne contient aucune cle creee par une liste `lights_*` / `covers_*` / `switches_*` hardcodee
  - [x] Executer les tests 8.1 + 8.2 + 8.3 ensemble
  - [x] Executer les tests d'orchestration/publication existants : `test_pe_epic5_story_5_1_orchestration.py`, `test_pe_epic5_story_5_2_publication_result.py`, `test_cleanup.py`
  - [x] Executer `python3 -m pytest` depuis `resources/daemon/` si le temps de cycle reste acceptable

## Dev Notes

### Contexte actif

Cycle actif : **Moteur de projection explicable**. Les sources de verite actives sont celles du manifeste : `epics-projection-engine.md`, `architecture-projection-engine.md`, `ha-projection-reference.md`, `sprint-change-proposal-2026-04-30.md` et `sprint-status.yaml`. Les artefacts V1.1 Pilotable sont contexte secondaire uniquement.

Story 8.3 depend directement de :
- Story 8.1 PR #107 : `MapperRegistry` + `FallbackMapper` terminal no-op
- Story 8.2 PR #108 : `PublisherRegistry` + `UnknownPublisherError` + `technical_reason_code="publisher_not_registered"`

### Zone de code critique

Le bloc vise dans `resources/daemon/transport/http_server.py` est `_run_sync`, principalement autour des lignes actuelles 997-1224 :
- lignes 997-999 : instanciation `LightMapper`, `CoverMapper`, `SwitchMapper`
- lignes 1003-1019 : `mapping_counters` hardcode
- lignes 1039-1047 : cascade hardcodee
- lignes 1072 / 1124 / 1175 : trois branches hardcodees de publication
- lignes 1418-1446 : lecture/log des compteurs a rendre dynamique si les cles changent

Modifications adjacentes autorisees dans le meme fichier : imports necessaires, helper prive/local pour le bookkeeping commun, adaptation du log summary et de `summary["mapping_summary"]`. Ne pas toucher aux autres modules de production.

### Algorithme cible recommande

Pseudo-flux attendu dans `_run_sync` :

```python
mapper_registry = MapperRegistry()
publisher = DiscoveryPublisher(mqtt_bridge) if mqtt_bridge else None
publisher_registry = PublisherRegistry(publisher) if publisher else None
mapping_counters = _build_mapping_counters_from_publisher_registry()

for eq_id, result in eligibility.items():
    if not result.is_eligible:
        continue
    eq = snapshot.eq_logics.get(eq_id)
    if not eq:
        continue

    mapping = mapper_registry.map(eq, snapshot)
    if mapping is None:
        continue

    mappings[eq_id] = mapping
    previous_decision = request.app["publications"].get(eq_id)
    await _detect_lifecycle_changes(...)

    projection_validity = validate_projection(mapping.ha_entity_type, mapping.capabilities)
    mapping.projection_validity = projection_validity
    mapping.pipeline_step_reached = 3
    decision = decide_publication(mapping, confidence_policy=confidence_policy)
    decision.mapping_result = mapping
    mapping.publication_decision_ref = decision
    mapping.pipeline_step_reached = 4

    _increment_mapping_confidence(mapping_counters, mapping)
    _prepare_publication_bookkeeping(eq_id, mapping, decision, snapshot, publications, nouveaux_eq_ids)

    if decision.should_publish:
        if publisher_registry and mqtt_bridge and mqtt_bridge.is_connected:
            config_published = await publisher_registry.publish(mapping, snapshot)
        else:
            config_published = False
            _LOGGER.warning(...)

        if not config_published:
            if _needs_discovery_unpublish(previous_decision):
                decision.discovery_published = True
            if mapping.publication_result is None:
                mapping.publication_result = _make_publication_result("failed", "discovery_publish_failed")
        else:
            decision.discovery_published = True
            local_ok = True
            if decision.local_availability_supported:
                local_ok = _publish_local_availability_state(mqtt_bridge, eq_id, decision)
            if local_ok:
                decision.active_or_alive = True
                mapping.publication_result = _make_publication_result("success")
                _increment_mapping_published(mapping_counters, mapping)
            else:
                mapping.publication_result = _make_publication_result("failed", "local_availability_publish_failed")
    else:
        mapping.publication_result = _make_publication_result("not_attempted")

    mapping.pipeline_step_reached = 5
    if not decision.active_or_alive:
        _increment_mapping_skipped(mapping_counters, mapping)
```

Le nom exact des helpers est libre, mais leur responsabilite doit rester etroite. Ne pas introduire de classe d'orchestration ou de pipeline objet dans cette story.

### Compteurs : precision anti-ambiguite

Le besoin produit est de supprimer les compteurs hardcodes par famille (`lights_*`, `covers_*`, `switches_*`) afin que Story 9 puisse ajouter des publishers sans retoucher `_run_sync`. Pour Story 8.3, la source dynamique doit etre le `PublisherRegistry`, qui contient exactement les types operationnels actuels : `light`, `cover`, `switch`.

Le helper de construction des compteurs doit pouvoir lire les cles du registry meme quand le bridge MQTT est absent. Il peut instancier un publisher d'inspection non utilise pour publier, ou toute autre approche locale equivalente, tant qu'il ne recode pas une deuxieme table de types dans `_run_sync` et ne modifie pas la table fonctionnelle de `PublisherRegistry`.

Les valeurs doivent rester equivalentes aux valeurs actuelles :
- `sure`, `probable`, `ambiguous` sont incrementes une fois par mapping de ce type
- `published` est incremente uniquement apres publication Discovery reussie et disponibilite locale OK
- `skipped` est incremente quand `decision.active_or_alive` reste false

Avant de changer la forme de `mapping_summary`, verifier par `rg` qu'aucun consommateur hors `http_server.py` ne depend des anciennes cles. Au moment de preparation, `rg` ne trouve ces cles que dans `http_server.py`.

### Type inconnu / publisher absent

Story 8.2 a defini le contrat :
- `PublisherRegistry.resolve("sensor")` leve `UnknownPublisherError`
- `PublisherRegistry.publish(mapping_sensor, snapshot)` retourne `False`
- `mapping.publication_result.status == "failed"`
- `mapping.publication_result.technical_reason_code == "publisher_not_registered"`

Story 8.3 doit brancher ce contrat sans le transformer en `continue` silencieux et sans l'ecraser par `discovery_publish_failed`. Cette situation ne doit pas apparaitre pour les mappers actuels (`light`, `cover`, `switch`, `FallbackMapper` no-op), mais elle protege la suite pe-epic-9.

### Ce que Story 8.3 ne touche PAS

| Surface | Regle |
|---|---|
| `resources/daemon/mapping/light.py` | Ne pas modifier |
| `resources/daemon/mapping/cover.py` | Ne pas modifier |
| `resources/daemon/mapping/switch.py` | Ne pas modifier |
| `resources/daemon/mapping/fallback.py` | Ne pas ajouter de logique ; reste no-op |
| `resources/daemon/discovery/publisher.py` | Ne pas modifier les methodes `publish_light`, `publish_cover`, `publish_switch` |
| `resources/daemon/discovery/registry.py` | Ne pas ajouter `sensor`, `binary_sensor`, `button` |
| `resources/daemon/validation/ha_component_registry.py` | Ne pas modifier `HA_COMPONENT_REGISTRY` ni `PRODUCT_SCOPE` |
| `resources/daemon/models/decide_publication.py` | Ne pas modifier |
| `resources/daemon/models/cause_mapping.py` | Ne pas modifier |
| `_republish_all_from_cache()` | Hors scope du refactor 8.3 sauf contrainte technique strictement necessaire |

### Dev Agent Guardrails

#### Guardrail — Deploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom reelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procedure parallele
- Reference complete modes + cycle valide terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplace par le script) : `main -> beta -> stable -> Jeedom Market`

#### Guardrail — Cadre de garantie pe-epic-8

- Refactor pur : aucune amelioration comportementale opportuniste
- Zero nouveau type publie cote HA
- Zero nouveau mapper reel
- Zero nouveau publisher
- Zero changement dans `PRODUCT_SCOPE` ou `HA_COMPONENT_REGISTRY`
- Zero changement dans `cause_label`, `cause_action`, `reason_code` et la hierarchie des causes
- Zero changement dans `validate_projection()` et `decide_publication()`
- Si une non-regression echoue, restaurer la parite ; ne pas justifier le drift comme une correction

#### Guardrail — Architecture

- AR3 : `mapping/`, `validation/`, `discovery/`, `transport/` gardent des responsabilites separees
- FR15 : le refactor ne modifie pas l'ordre canonique des cinq etapes
- `http_server.py` orchestre ; il ne doit pas connaitre les contraintes HA, ni serialiser un payload Discovery
- `PublisherRegistry` resout la methode `publish_*`; `DiscoveryPublisher` continue de serialiser/publier
- `MapperRegistry` resout le premier mapper gagnant ; il ne decide pas la publication

### Previous Story Intelligence

Story 8.1 a etabli :
- `resources/daemon/mapping/registry.py` avec ordre non configurable `LightMapper`, `CoverMapper`, `SwitchMapper`, `FallbackMapper`
- `resources/daemon/mapping/fallback.py` avec `map()` retournant toujours `None`
- tests unitaires de parite cascade vs registry sur light, cover, switch et sans mapper
- aucun branchement dans `http_server.py`

Story 8.2 a etabli :
- `resources/daemon/discovery/registry.py`
- table fixe `{"light": publish_light, "cover": publish_cover, "switch": publish_switch}`
- echec explicite `publisher_not_registered` pour type inconnu
- aucun branchement dans `http_server.py`

Story 8.3 est le premier moment ou `http_server.py` est autorise a consommer ces deux registries.

### Git Intelligence Summary

Derniers commits pertinents sur `main` :
- `24b794d feat(pe-8.2): PublisherRegistry + dispatch table ha_entity_type (#108)`
- `b291cf5 feat(pe-8.1): MapperRegistry deterministe + slot FallbackMapper terminal (#107)`
- `7aa472d chore(bmad): correct-course 2026-04-30` — ouvre pe-epic-8/9 et fixe le sequencing

Aucune dependance externe nouvelle n'est requise. Aucune recherche web n'est necessaire pour implementer cette story : le refactor consomme exclusivement les registries locaux et la reference HA locale active.

### Project Structure Notes

Fichiers attendus :
- `resources/daemon/transport/http_server.py` — refactor `_run_sync`
- `resources/daemon/tests/unit/test_story_8_3_http_server_dispatch.py` — tests Story 8.3
- `_bmad-output/implementation-artifacts/8-3-refactor-http-server-run-sync-boucle-dispatch-unique-et-compteurs-generiques.md` — statut BMAD
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — statut BMAD

Fichiers a lire mais ne pas modifier :
- `resources/daemon/mapping/registry.py`
- `resources/daemon/discovery/registry.py`
- `resources/daemon/mapping/light.py`
- `resources/daemon/mapping/cover.py`
- `resources/daemon/mapping/switch.py`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/validation/ha_component_registry.py`

### References

- [Source: _bmad-output/planning-artifacts/active-cycle-manifest.md §7] — regles agents, source HA, golden-file 8.4
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md §5.2] — pe-epic-8 refactor pur, zero nouveau comportement
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story-83--Refactor-http_server_run_sync] — story, AC, dev notes
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Gates-epic-level-pe-epic-8] — gates zero regression
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story-84--Gate-golden-file] — baseline 30 equipements qui suit
- [Source: _bmad-output/planning-artifacts/architecture-projection-engine.md#Pipeline-cible-du-moteur-de-projection] — ordre canonique des 5 etapes
- [Source: _bmad-output/planning-artifacts/architecture-projection-engine.md#D2--Module-validation-separe] — separation mapping / validation / discovery
- [Source: _bmad-output/planning-artifacts/architecture-projection-engine.md#D7--Insertion-dans-le-sync-handler] — orchestration dans `http_server.py`
- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md#Statut-BMAD-et-regles-devolution] — artefacts code derives de la reference HA
- [Source: resources/daemon/transport/http_server.py:997] — bloc hardcode cible
- [Source: resources/daemon/transport/http_server.py:1418] — log summary hardcode a rendre dynamique
- [Source: resources/daemon/mapping/registry.py] — `MapperRegistry`
- [Source: resources/daemon/discovery/registry.py] — `PublisherRegistry`
- [Source: resources/daemon/discovery/publisher.py] — publishers existants a reutiliser
- [Source: _bmad-output/project-context.md] — stack Python/pytest, regles de deploiement terrain et anti-patterns

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-03 — `./scripts/deploy-to-box.sh --dry-run` tente depuis le worktree story ; bloque avant transfert avec `ERROR: JEEDOM_BOX_HOST is not set.`. Smoke terrain non executable localement, non bloquant pour preparation code review.
- 2026-05-03 — RED Story 8.3 confirme : 6 tests echouent avant refactor (imports registry/helper absents), puis passent apres branchement.
- 2026-05-03 — `rg` a revele un consommateur reel des cles legacy `mapping_summary` dans `plugin_info/configuration.php`; les cles `lights_*`, `covers_*`, `switches_*` restent donc exposees, mais leur generation est dynamique depuis les types du `PublisherRegistry`.

### Completion Notes List

Story creee le 2026-05-03 par le workflow `bmad-create-story`.

Analyse chargee :
- workflow BMAD create-story complet + checklist
- manifeste du cycle actif section 7
- correct-course 2026-04-30
- `ha-projection-reference.md`
- Epic 8 complet, Story 8.3, Story 8.4 et gates pe-epic-8
- architecture AR3 / D2 / D7 / FR15
- code `_run_sync` lignes 997-1224 et log summary lignes 1418-1446
- `MapperRegistry` Story 8.1 et `PublisherRegistry` Story 8.2
- mappers/publishers existants et registre HA

Terrain story : true — la story touche le daemon, la discovery MQTT et `/action/sync`; Task 0 et guardrail terrain injectes.

Completion note : Ultimate context engine analysis completed - comprehensive developer guide created.

Implementation complete :
- `_run_sync` consomme `MapperRegistry.map(eq, snapshot)` pour le mapping light/cover/switch avec `FallbackMapper` no-op terminal.
- La publication Discovery de `_run_sync` passe par une branche generique `PublisherRegistry.publish(mapping, snapshot)` et preserve `publisher_not_registered`.
- Les compteurs sont construits depuis `PublisherRegistry.publishers.keys()` et incrementes via helpers generiques, tout en conservant les cles publiques legacy lues par le frontend PHP.
- Le bookkeeping pre-publication commun est centralise dans `_prepare_publication_bookkeeping()`.
- Aucune modification des mappers, publishers, registry discovery, registry HA, `decide_publication()`, `cause_mapping.py` ou `_republish_all_from_cache()`.
- Tests valides : Story 8.3 (6/6), suites 8.1+8.2+8.3 (20/20), non-regression Epic 5 ciblee (25/25), cible combinee (45/45), corpus daemon complet `671 passed`, flake8 cible OK.

### File List

- `_bmad-output/implementation-artifacts/8-3-refactor-http-server-run-sync-boucle-dispatch-unique-et-compteurs-generiques.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_story_8_3_http_server_dispatch.py`

### Change Log

- 2026-05-03 — Creation Story 8.3 ready-for-dev : contexte complet, garde-fous pe-epic-8, Task 0 terrain, tests cibles et consignes de refactor `_run_sync`.
- 2026-05-03 — Implementation Story 8.3 : `_run_sync` branche `MapperRegistry` + `PublisherRegistry`, compteurs dynamiques legacy-compatibles, bookkeeping unique, tests Story 8.3 et non-regression daemon complete ; statut passe a `review`.
