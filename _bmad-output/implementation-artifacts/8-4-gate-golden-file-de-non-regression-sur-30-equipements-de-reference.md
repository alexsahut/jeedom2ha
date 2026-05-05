# Story 8.4 : Gate golden-file de non-regression sur 30 equipements de reference

Status: review

## Story

En tant que mainteneur,
je veux un test golden-file qui compare la sortie complete d'une synchronisation sur un corpus reproductible de 30 equipements,
afin que `pe-epic-8` ne puisse cloturer que si la parite comportementale post-refactor reste strictement preservee et que `pe-epic-9` demarre sur une baseline de regression-control stable.

## Acceptance Criteria

**AC1 — Corpus deterministe de 30 equipements**
Given un corpus de reference stocke sous `resources/daemon/tests/fixtures/golden_corpus/`,
When le test golden-file charge ce corpus,
Then il contient exactement 30 eqLogics deterministes : 10 lights, 8 covers, 5 switches, 3 ambigus, 2 non-eligibles, 2 valides bloques par scope ou validation HA.

**AC2 — Snapshot stable de sortie complete**
Given ce corpus de reference,
When une sync complete est executee via `/action/sync` avec MQTT et publication Discovery mockes,
Then la sortie canonique comparee au snapshot inclut au minimum : mapping, decision, `publication_result`, contrat 4D, `traceability.projection_validity`, `traceability.decision_trace`, `traceability.publication_trace`, `pipeline_step_visible` et `payload.mapping_summary`.

**AC3 — Drift bloquant**
Given un drift detecte entre la sortie courante et le snapshot golden,
When la suite de tests est executee,
Then le test echoue explicitement avec un diff lisible,
And la story reste bloquee tant que la parite n'est pas restauree,
And aucune justification de type "amelioration accidentelle" n'est acceptable dans `pe-epic-8`.

**AC4 — Baseline CI pour les prochains epics**
Given le test golden-file,
When une PR future touche `resources/daemon/mapping/`, `resources/daemon/transport/`, `resources/daemon/discovery/` ou `resources/daemon/validation/`,
Then ce test fait partie de la suite `pytest` standard executee par la CI,
And il devient la baseline de regression-control obligatoire pour toutes les stories de `pe-epic-9`.

**AC5 — Zero production change**
Given le diff de la story,
When il est relu,
Then aucun fichier de production n'est modifie,
And les seules modifications attendues sont le corpus de fixtures, le snapshot golden et le test golden-file,
And `PRODUCT_SCOPE`, `HA_COMPONENT_REGISTRY`, `MapperRegistry`, `PublisherRegistry`, `FallbackMapper`, `DiscoveryPublisher`, `validate_projection`, `decide_publication`, `cause_mapping.py` et `http_server.py` restent inchanges.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : verifier sans transferer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Selectionner le mode selon l'objectif de la story :
    - Verification disparition entites HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Verifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup termine.`

- [x] Task 1 — Creer le corpus de fixtures deterministe (AC: 1, 5)
  - [x] 1.1 — Creer `resources/daemon/tests/fixtures/golden_corpus/`
  - [x] 1.2 — Ajouter un fichier source lisible, par exemple `sync_payload.json`, contenant `objects`, `eq_logics`, `published_scope` et `sync_config`
  - [x] 1.3 — Garder des IDs stables et groupes par familles : `1000-1009` lights, `2000-2007` covers, `3000-3004` switches, `4000-4002` ambigus, `5000-5001` non-eligibles, `6000-6001` bloques par scope/validation
  - [x] 1.4 — Ne pas utiliser de generation random, de timestamps courants, de tri implicite non controle ou de donnees depandant de l'environnement
  - [x] 1.5 — Documenter dans le JSON ou dans un court `README.md` le role attendu de chaque equipement du corpus

- [x] Task 2 — Construire le snapshot golden canonique (AC: 2, 3, 5)
  - [x] 2.1 — Ajouter `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`
  - [x] 2.2 — Normaliser les champs volatils avant comparaison : `request_id`, `timestamp`, `PublicationResult.attempted_at`, `derniere_synchro_terminee` si expose, et tout champ ISO runtime equivalent
  - [x] 2.3 — Trier les dictionnaires par cle et les listes d'equipements par `eq_id` avant ecriture/comparaison
  - [x] 2.4 — Inclure le `payload.mapping_summary` complet avec les cles legacy generees dynamiquement : `lights_*`, `covers_*`, `switches_*`
  - [x] 2.5 — Inclure pour chaque equipement diagnostique le contrat 4D (`perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`, `ha_type`) et la trace complete

- [x] Task 3 — Ajouter le test golden-file (AC: 2, 3, 4, 5)
  - [x] 3.1 — Ajouter `resources/daemon/tests/unit/test_story_8_4_golden_file.py`
  - [x] 3.2 — Charger les fixtures depuis `resources/daemon/tests/fixtures/golden_corpus/` avec `pathlib.Path`, pas depuis le cwd implicite
  - [x] 3.3 — Executer `/action/sync` via `aiohttp_client(create_app(...))`, sur le pattern de `test_story_8_3_http_server_dispatch.py`
  - [x] 3.4 — Mock/stub MQTT et `DiscoveryPublisher` de facon deterministe ; ne jamais contacter un broker reel
  - [x] 3.5 — Appeler ensuite `/system/diagnostics` pour capturer le contrat 4D et `traceability` associes aux 30 equipements
  - [x] 3.6 — Construire un objet snapshot minimal et canonique contenant `sync_payload`, `diagnostics_payload`, `app["mappings"]`, `app["publications"]` et les counters utiles, puis comparer a `expected_sync_snapshot.json`
  - [x] 3.7 — En cas de divergence, produire un diff JSON lisible via la bibliotheque standard (`json.dumps(..., indent=2, sort_keys=True)`, `difflib.unified_diff`)

- [x] Task 4 — Couvrir explicitement les 6 familles du corpus (AC: 1, 2, 3)
  - [x] 4.1 — Lights : 10 cas light-family attendus comme light, couvrant `sure`, `probable`, brightness et variantes deterministes sans double-compter les 3 cas ambigus
  - [x] 4.2 — Covers : 8 cas cover-family attendus comme cover, couvrant open/close, stop, position, BSO et variantes deterministes sans double-compter les 3 cas ambigus
  - [x] 4.3 — Switches : 5 cas switch-family attendus comme switch, couvrant on/off/state, probable on/off-only ou one-shot, outlet detecte via `eq_type_name`, sans double-compter les 3 cas ambigus
  - [x] 4.4 — Ambigus : 3 cas eligibles qui doivent rester non publies avec cause canonique stable (`ambiguous_skipped` ou equivalent actuel), par exemple state-only/orphan, color-only, name heuristic ou conflit anti-affinite
  - [x] 4.5 — Non-eligibles : 2 cas etape 1 (`disabled_eqlogic`, `excluded_eqlogic` ou `no_commands`) presents dans le diagnostic mais absents de `app["mappings"]`
  - [x] 4.6 — Valides bloques : 2 cas mappes puis bloques par etape 3 ou 4, par exemple `ha_missing_command_topic` et `ha_component_not_in_product_scope`, en utilisant des doubles de test si necessaire sans modifier la production

- [x] Task 5 — Verifier la baseline CI et la non-regression (AC: 3, 4, 5)
  - [x] 5.1 — Confirmer que `.github/workflows/test.yml` execute deja `python -m pytest` sur chaque PR vers `main`, `beta`, `stable`
  - [x] 5.2 — Ne pas modifier la CI si le nouveau test est dans `resources/daemon/tests/` et donc inclus dans `pyproject.toml`
  - [x] 5.3 — Executer `python3 -m pytest resources/daemon/tests/unit/test_story_8_4_golden_file.py`
  - [x] 5.4 — Executer les suites de garde-fou 8.1 + 8.2 + 8.3 + 8.4
  - [x] 5.5 — Executer `python3 -m pytest` depuis la racine ou depuis `resources/daemon/` selon la convention locale utilisee dans les stories precedentes
  - [x] 5.6 — Verifier par `git diff --name-only` qu'aucun fichier de production n'a change

## Dev Notes

### Contexte actif

Cycle actif : **Moteur de projection explicable**. Sources de verite chargees pour cette story :
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md`
- `_bmad-output/planning-artifacts/active-cycle-manifest.md`
- `_bmad-output/planning-artifacts/ha-projection-reference.md`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `_bmad-output/planning-artifacts/architecture-projection-engine.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Story 8.1, Story 8.2, Story 8.3 et code post-PR #109

`pe-epic-8` est un refactor pur. 8.4 est la derniere story de l'epic et son gate bloque `pe-epic-9`. La mesure terrain operationnelle connue (Box Alexandre : 278 eqLogics, 81 eligibles, 30 publies, ratio publie/eligible 37 %) est informative seulement ; elle ne doit pas etre encodee comme assertion normative dans le test.

### Cadre de garantie pe-epic-8

- Zero modification de code production
- Zero nouveau type publie
- Zero changement `PRODUCT_SCOPE` ou `HA_COMPONENT_REGISTRY`
- Zero changement `cause_label`, `cause_action`, `reason_code` ou hierarchie des causes
- Zero changement `MapperRegistry`, `PublisherRegistry`, `FallbackMapper`, mappers existants ou publishers existants
- Zero "amelioration accidentelle" : un drift golden-file est une regression dans cet epic, meme si la nouvelle sortie semble meilleure

### Fixtures et snapshot

Le repertoire `resources/daemon/tests/fixtures/` n'existe pas encore dans le repo au moment de preparation de la story. Il faut donc le creer explicitement avec le sous-repertoire `golden_corpus/`.

Convention recommandee :

```text
resources/daemon/tests/fixtures/golden_corpus/
├── sync_payload.json
├── expected_sync_snapshot.json
└── README.md
```

Le snapshot doit rester lisible en review. Preferer un JSON stable, indente, avec `sort_keys=True`. Eviter toute dependance externe de snapshot testing : le `pyproject.toml` expose `pytest`, `pytest-cov`, `pytest-asyncio`, `pytest-aiohttp`, `flake8`, mais aucune lib de snapshot/approval. Utiliser uniquement la bibliotheque standard (`json`, `pathlib`, `difflib`, `copy`) et les fixtures `pytest-aiohttp` deja presentes.

### Sortie canonique a comparer

Comparer un objet reduit aux surfaces de contrat, pas un dump aveugle d'objets Python. Sur chaque run, normaliser avant comparaison :
- `request_id` de la reponse `/action/sync`
- `timestamp` de la reponse HTTP
- `PublicationResult.attempted_at`
- tout timestamp runtime derive de `datetime.now()`

Le snapshot doit au minimum contenir :
- `sync.payload.mapping_summary`
- `sync.payload.published_scope`
- diagnostics par `eq_id` depuis `/system/diagnostics`
- pour chaque diagnostic : contrat 4D, `status`, `reason_code`, `pipeline_step_visible`, `actions_ha`, `traceability`
- une projection serialisee des `MappingResult` et `PublicationDecision` stockes en memoire quand l'equipement est mappe
- pour `PublicationResult` : `status` et `technical_reason_code`, timestamp normalise

Ne pas comparer les logs. Ne pas comparer l'ordre brut des dictionnaires. Ne pas capturer d'objet non serialisable.

### Code post-Story 8.3 a connaitre

`resources/daemon/transport/http_server.py` est deja refactore :
- `MapperRegistry()` est instancie dans `_do_handle_action_sync()` et remplace la cascade hardcodee
- `PublisherRegistry(publisher)` est instancie si un `DiscoveryPublisher` existe
- `_build_mapping_counters_from_publisher_registry()` genere les compteurs depuis `PublisherRegistry.publishers.keys()`
- `_prepare_publication_bookkeeping()` centralise `state_topic`, availability, `publications[eq_id]` et `nouveaux_eq_ids`
- `PublisherRegistry.publish()` preserve `technical_reason_code="publisher_not_registered"` sans l'ecraser par `discovery_publish_failed`
- `_build_traceability()` lit `projection_validity` et `publication_result` sans recalculer

Le test 8.4 doit observer ces contrats ; il ne doit pas les refactorer.

### Composition minimale du corpus

Les familles ci-dessous sont normatives ; les exemples precis sont adaptables si un mapper existant impose un nom ou une combinaison de commandes plus stable.

| Famille | Nombre | Intention |
|---|---:|---|
| Lights | 10 | Cas light-family attendus comme light : nominal, probable, brightness, variantes deterministes |
| Covers | 8 | Cas cover-family attendus comme cover : open/close, stop, position, BSO, variantes deterministes |
| Switches | 5 | Cas switch-family attendus comme switch : on/off/state, probable, outlet, variantes deterministes |
| Ambigus | 3 | Equipements eligibles mappes mais non publies pour ambiguite |
| Non-eligibles | 2 | Etape 1 bloquee, visibles dans diagnostic, absents des mappings |
| Valides bloques | 2 | Equipements mappes mais bloques par validation HA ou scope produit |

Attention : `sensor` et `binary_sensor` sont deja dans `PRODUCT_SCOPE` depuis Story 7.4, mais aucun mapper/publisher reel n'est ouvert dans `pe-epic-8`. Ne pas les ajouter au `PublisherRegistry`. Pour les deux cas "valides bloques", utiliser les comportements existants ou des doubles de test locaux au test, sans modifier la production.

Les 6 familles ci-dessus sont des buckets de comptage exclusifs : si un equipement light-family est retenu comme cas ambigu, il compte dans le bucket "Ambigus", pas dans les 10 lights.

### Previous Story Intelligence

Story 8.1 (PR #107) a etabli :
- `resources/daemon/mapping/registry.py`
- `resources/daemon/mapping/fallback.py`
- ordre `LightMapper`, `CoverMapper`, `SwitchMapper`, `FallbackMapper`
- `FallbackMapper.map()` retourne `None` systematiquement dans `pe-epic-8`

Story 8.2 (PR #108) a etabli :
- `resources/daemon/discovery/registry.py`
- `PublisherRegistry` limite a `light`, `cover`, `switch`
- `UnknownPublisherError`
- `PublicationResult(status="failed", technical_reason_code="publisher_not_registered")` pour type sans publisher

Story 8.3 (PR #109) a etabli :
- `_run_sync` consomme `MapperRegistry` et `PublisherRegistry`
- les compteurs sont dynamiques mais legacy-compatibles (`lights_*`, `covers_*`, `switches_*`)
- `http_server.py` garde le role d'orchestration uniquement
- corpus daemon complet annonce : `671 passed`

### Git Intelligence Summary

Derniers commits pertinents sur `main` :
- `9c868ab chore(bmad): close Story 8.3 formally`
- `d0df00f feat(pe-8.3): refactor _run_sync via MapperRegistry + PublisherRegistry (#109)`
- `24b794d feat(pe-8.2): PublisherRegistry + dispatch table ha_entity_type (#108)`
- `b291cf5 feat(pe-8.1): MapperRegistry deterministe + slot FallbackMapper terminal (#107)`
- `7aa472d chore(bmad): correct-course 2026-04-30 — close pe-epic-7, open pe-epic-8/9`

Aucune dependance externe nouvelle n'est requise. Aucune recherche web n'est necessaire : la story verrouille le comportement local existant et s'appuie sur les artefacts BMAD actifs.

### Dev Agent Guardrails

#### Guardrail — Deploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom reelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procedure parallele
- Reference complete modes + cycle valide terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplace par le script) : `main -> beta -> stable -> Jeedom Market`

#### Guardrail — Golden-file

- Le test golden-file n'est pas un outil de validation de nouvelle fonctionnalite ; c'est un verrou anti-drift
- Toute modification du snapshot doit etre justifiee par une story ulterieure qui assume explicitement le changement de contrat
- Ne pas regenerer le snapshot pour "faire passer" le test
- Le diff attendu doit etre lisible en review ; si le snapshot devient opaque, reduire/normaliser la structure, pas masquer la divergence
- Garder le corpus initial de 30 equipements intact quand `pe-epic-9` etendra le golden-file avec de nouveaux types

#### Guardrail — CI

La CI actuelle (`.github/workflows/test.yml`) execute `python -m pytest --cov=resources/daemon --cov-report=xml --cov-report=term-missing` sur chaque PR vers `main`, `beta`, `stable`. Un test place sous `resources/daemon/tests/` est donc deja dans la baseline CI. Ne modifier la CI que si une preuve locale montre que le test 8.4 n'est pas execute par la suite standard.

### Project Structure Notes

Fichiers attendus :
- `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`
- `resources/daemon/tests/fixtures/golden_corpus/README.md`
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py`

Fichiers explicitement hors scope :
- `resources/daemon/transport/http_server.py`
- `resources/daemon/mapping/*.py`
- `resources/daemon/discovery/*.py`
- `resources/daemon/validation/ha_component_registry.py`
- `resources/daemon/models/decide_publication.py`
- `resources/daemon/models/cause_mapping.py`
- `.github/workflows/test.yml` sauf preuve que le test standard ne couvre pas `resources/daemon/tests/`

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story-84--Gate-golden-file] — story, AC et composition minimale du corpus
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Gates-epic-level-pe-epic-8] — gates zero regression et blocage pe-epic-9
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md §5.2] — cadre pe-epic-8, refactor pur, golden-file 30 equipements
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md §6] — Story 8.4 bloque pe-epic-9
- [Source: _bmad-output/planning-artifacts/active-cycle-manifest.md §7] — golden-file 8.4 baseline regression-control pour dispatch/registries
- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md#Statut-BMAD-et-regles-devolution] — artefacts code derives de la reference HA
- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md#Sequencing-douverture-documente] — `sensor`/`binary_sensor` ouverts en scope mais publication reelle repoussee a pe-epic-9
- [Source: _bmad-output/planning-artifacts/architecture-projection-engine.md#Pipeline-cible-du-moteur-de-projection] — ordre canonique des 5 etapes
- [Source: _bmad-output/planning-artifacts/architecture-projection-engine.md#D7--Insertion-dans-le-sync-handler] — orchestration `/action/sync`
- [Source: resources/daemon/transport/http_server.py] — `_do_handle_action_sync`, counters dynamiques, traceability
- [Source: resources/daemon/tests/unit/test_story_8_3_http_server_dispatch.py] — pattern de test aiohttp + mocks registry/publisher
- [Source: pyproject.toml] — testpaths `tests`, `resources/daemon/tests`; dependances test disponibles
- [Source: .github/workflows/test.yml] — CI pytest full-suite sur PR

## Dev Agent Record

### Agent Model Used

GPT-5.5 (Codex)

### Debug Log References

- `./scripts/deploy-to-box.sh --dry-run` -> PASS (mode dry-run, aucun transfert effectif)
- `python3 -m pytest resources/daemon/tests/unit/test_story_8_4_golden_file.py` -> PASS (1 passed)
- `python3 -m pytest resources/daemon/tests/unit/test_story_8_1_mapper_registry.py resources/daemon/tests/unit/test_story_8_2_publisher_registry.py resources/daemon/tests/unit/test_story_8_3_http_server_dispatch.py resources/daemon/tests/unit/test_story_8_4_golden_file.py` -> PASS (21 passed)
- `python3 -m pytest` -> PASS (1198 passed)

### Completion Notes List

Story creee le 2026-05-04 par le workflow `bmad-create-story`.

Analyse chargee :
- workflow BMAD create-story complet + checklist
- manifeste du cycle actif
- correct-course 2026-04-30
- `ha-projection-reference.md`
- Epic 8 complet, Story 8.4, gates pe-epic-8 et Story 9.1 pour la suite
- architecture moteur de projection
- `http_server.py` post-refactor 8.3
- tests Story 8.3
- absence actuelle de `resources/daemon/tests/fixtures/`

Terrain story : true — la story mentionne `/action/sync`, daemon, MQTT et discovery HA ; Task 0 et guardrail terrain sont presents. La gate normative reste le golden-file pytest/CI.

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

- Implementation Story 8.4 terminee sans changement production.
- Corpus deterministe 30 equipements ajoute sous `resources/daemon/tests/fixtures/golden_corpus/`.
- Snapshot golden canonique ajoute avec normalisation des champs volatils (`request_id`, `timestamp`, `attempted_at`, `derniere_synchro_terminee`).
- Test golden-file ajoute avec diff unifie bloquant (`difflib.unified_diff`) et validation explicite des 6 familles.
- Cas `ha_missing_command_topic` couvert via fixture `6000` (`LIGHT_STATE` numeric seul).
- Cas `ha_component_not_in_product_scope` couvert via double local de `MapperRegistry` (eq `6001` force en `climate`), sans modifier la production.
- AC5 verifie: aucun fichier production modifie (`mapping/`, `discovery/`, `transport/`, `validation/`, `models/` inchanges).

### File List

- resources/daemon/tests/fixtures/golden_corpus/sync_payload.json
- resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json
- resources/daemon/tests/fixtures/golden_corpus/README.md
- resources/daemon/tests/unit/test_story_8_4_golden_file.py
- _bmad-output/implementation-artifacts/8-4-gate-golden-file-de-non-regression-sur-30-equipements-de-reference.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

- 2026-05-04 — Creation Story 8.4 ready-for-dev : corpus golden-file 30 equipements, test snapshot CI, garde-fous zero production change, baseline pe-epic-9.
- 2026-05-04 — Implementation Story 8.4 : corpus golden-file 30 equipements + snapshot expected + test golden-file non-regression, validations pytest completes, statut passe a review.
