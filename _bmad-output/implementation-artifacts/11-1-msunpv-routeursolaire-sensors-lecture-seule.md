# Story 11.1: MSunPV / RouteurSolaire — publier les valeurs de routage solaire en sensors lecture seule

Status: review

## Story

En tant qu'utilisateur familial de Home Assistant,
je veux voir dans HA les valeurs de production et de routage de l'equipement Jeedom `MSunPV / RouteurSolaire` eq553,
afin de suivre sur le dashboard solaire les panneaux, le reseau et le routage cumulus/radiateur sans ouvrir de nouveau type HA.

## Acceptance Criteria

1. **Perimetre strict eq553.** La story cible uniquement `MSunPV / RouteurSolaire` eq553 et ne traite pas le chauffe-eau eq554 ni le bug `switch.jeedom2ha_554 = unknown`.
2. **Sensors lecture seule.** Les 8 commandes inventoriees pour eq553 sont projetables comme `sensor` HA, sans nouveau type dans `PRODUCT_SCOPE` :
   - `#5138` Puissance panneaux, `W`
   - `#5137` Puissance reseau, `W`
   - `#5139` Routage cumulus, `%`
   - `#5140` Routage radiateur, `%`
   - `#5177` Etat sortie 1 (CE %), `%`
   - `#5171` Production panneaux journaliere, `Wh`
   - `#5170` Production injectee journaliere, `Wh`
   - `#5169` Consommation reseau journaliere, `Wh`
3. **Support multi-sensor borne.** L'eqLogic eq553 peut produire plusieurs entites `sensor` HA rattachees au meme device Jeedom, avec `unique_id`, `object_id`, discovery topic et `state_topic` distincts par commande.
4. **Pas de regression 1 eqLogic -> 1 entite existante.** Les mappers existants `light`, `cover`, `switch`, `climate`, `alarm_control_panel`, `presence_switch`, `binary_sensor`, `button`, fallback et le `SensorMapper` historique conservent leur comportement sur les cas non multi-sensor.
5. **Validation HA obligatoire.** Chaque sensor derive de eq553 passe par `validate_projection()` avec `SensorCapabilities(has_state=True)` et ne publie rien si la validation echoue.
6. **Diagnostic et compteurs coherents.** Le sync expose un mapping/publication lisible pour eq553 : les compteurs `sensor` et `published` refletent les sensors publies, et le diagnostic ne masque pas les refus ou echecs de publication.
7. **Golden corpus et non-regression.** Le golden corpus integre un cas MSunPV representatif et la suite de non-regression reste verte.
8. **Gate terrain.** Sur box reelle DEV/TEST, apres deploy/restart/sync, les topics discovery des 8 sensors eq553 sont publies et les valeurs sont lisibles dans HA ou via MQTT. Le gate terrain peut etre documente avec waiver explicite si l'equipement live n'est pas disponible au moment du test.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — EXECUTE le 2026-06-17 (box reelle 192.168.1.21, voir Completion Notes)
  - [x] Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Verifier que le script se termine avec `Deploy complete.`

- [x] Task 1 — Caracteriser le besoin multi-sensor eq553 (AC: 1, 2, 3)
  - [x] Ajouter un test unitaire rouge qui decrit eq553 avec les 8 commandes MSunPV et attend 8 mappings `sensor`.
  - [x] Verifier que chaque mapping conserve `jeedom_eq_id=553` mais possede un identifiant d'entite distinct par commande.
  - [x] Borner explicitement le comportement aux commandes `info` numeriques ; aucune commande action n'est creee.

- [x] Task 2 — Implementer le support multi-sensor minimal dans le pipeline (AC: 3, 4, 5, 6)
  - [x] Introduire une API de mapping additive permettant a un mapper de retourner plusieurs `MappingResult` sans casser `MapperRegistry.map()`.
  - [x] Adapter l'orchestration `/action/sync` pour traiter plusieurs mappings par eqLogic lorsque le mapper le demande.
  - [x] Conserver la compatibilite des consommateurs existants qui attendent un mapping principal par `eq_id`.
  - [x] Ne pas modifier `PRODUCT_SCOPE`.

- [x] Task 3 — Publier des topics discovery/state distincts par commande (AC: 3, 5)
  - [x] Adapter `DiscoveryPublisher.publish_sensor()` / payload sensor pour accepter un `node_id`, `object_id`, `unique_id`, `state_topic` distincts issus du mapping.
  - [x] Garder le `device` HA commun rattache a `jeedom2ha_553`.
  - [x] Ajouter des tests sur les payloads des 8 sensors MSunPV.

- [x] Task 4 — Etendre le diagnostic, les compteurs et la publication sans regression (AC: 4, 6)
  - [x] Verifier que les compteurs `sensor` et `published` comptent les entites multi-sensor publiees.
  - [x] Verifier que le diagnostic eq553 reste lisible et ne declare pas un faux succes si une publication sensor echoue.
  - [x] Verifier que les actions `publier` / `supprimer` ciblant eq553 gerent les entites multi-sensor ou documenter le comportement borne si le support action reste out-of-scope. (Documente : voir Completion Notes — publier/supprimer restent mono-entite par `eq_id`, comportement borne inchange.)

- [x] Task 5 — Golden corpus, tests complets et gate terrain (AC: 7, 8)
  - [x] Ajouter eq553 au golden corpus avec les 8 commandes representant MSunPV.
  - [x] Regenerer/ajuster `expected_sync_snapshot.json` uniquement pour les deltas attendus.
  - [x] Lancer la suite pytest complete.
  - [x] Executer le gate terrain via `scripts/deploy-to-box.sh` et documenter les preuves dans la story. — PASS le 2026-06-17 : 65 topics discovery `homeassistant/sensor/jeedom2ha_553_<cmd>/config` publies, device commun `identifiers:["jeedom2ha_553"]`, availability `online`. Voir Completion Notes.

### Review Follow-ups (AI)

- [>] [AI-Review][MEDIUM] Cycle de vie multi-sensor : seuls le mapping/decision primaires sont stockes sous `mappings[eq_id]` / `publications[eq_id]`. La dépublication (suppression/retype de eq553) via `unpublish_by_eq_id` ne nettoie que le topic primaire `homeassistant/sensor/jeedom2ha_553/config` ; les topics secondaires `jeedom2ha_553_<cmd>/config` resteraient orphelins (ghosts HA). **ELEVE en story 11.1.bis** (multi-sensor lifecycle / dépublication des secondaires) via correct-course — voir Sprint Change Proposal. [`resources/daemon/transport/http_server.py:1248`]
- [x] [AI-Review][LOW] AC8 gate terrain : rejoue le 2026-06-17 (`./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`, box 192.168.1.21). PASS — 65 sensors eq553 publies en discovery. [terrain]
- [x] [AI-Review][HIGH] Regression d'eligibilite decouverte au gate terrain : le vrai eq553 ne porte **aucun** `generic_type`, donc `assess_eligibility()` le rejetait (`no_supported_generic_type`) avant meme le multi-sensor mapper → 0 sensor publie sur la box. Le test masquait le defaut en injectant `generic_type="POWER"` sur 2 commandes. **Fix A** applique : les eqTypes multi-sensor (`msunpv`) sont eligibles sans `generic_type` des qu'ils portent ≥1 commande info numerique (`MULTI_SENSOR_EQ_TYPES` + `_has_numeric_info_command` dans `models/topology.py`). Fixture de test rendue fidele au terrain (tous `generic_type=None`) + tests d'eligibilite ajoutes. [`resources/daemon/models/topology.py:243`]

## Dev Notes

### Source produit et scope

- Source de verite fonctionnelle : `_bmad-output/planning-artifacts/backlog-icebox.md` §3.1.
- Readiness : `_bmad-output/implementation-artifacts/pe-epic-10-retro-2026-06-12.md` recommande explicitement de demarrer `pe-epic-11` par `MSunPV / RouteurSolaire` eq553.
- Limite stricte : ne pas traiter eq554 dans cette story ; le bug chauffe-eau `unknown` est un sujet distinct.
- Aucun nouveau composant HA : `sensor` est deja dans `PRODUCT_SCOPE`.

### Analyse architecture

- Le pipeline actuel mappe un `JeedomEqLogic` vers un `MappingResult` principal. Cette story introduit le premier besoin borne `1 eqLogic -> N sensors`.
- Ne pas casser l'API historique `MapperRegistry.map(eq, snapshot) -> Optional[MappingResult]`; preferer une API additive (`map_all`, `secondary_mappings`, ou equivalent) pour limiter le risque.
- Le `device` HA doit rester commun (`identifiers: ["jeedom2ha_553"]`) afin que HA groupe les sensors MSunPV sous le meme device.
- Les entites doivent etre identifiees par commande, pas par nom : utiliser les IDs `cmd` pour `unique_id`, `object_id`, topic discovery et `state_topic` quand plusieurs sensors partagent le meme eqLogic.
- Toute publication doit rester gouvernee par etapes 3/4/5 : mapping -> validation HA -> decision -> publication MQTT.

### Code a inspecter / modifier

- `resources/daemon/mapping/sensor.py` — `SensorMapper` historique, aujourd'hui mono-sensor.
- `resources/daemon/mapping/registry.py` — dispatch mapper ordonne.
- `resources/daemon/models/mapping.py` — `MappingResult`, `SensorCapabilities`.
- `resources/daemon/discovery/publisher.py` — payload sensor et topic discovery.
- `resources/daemon/discovery/registry.py` — dispatch publisher.
- `resources/daemon/transport/http_server.py` — orchestration sync, compteurs, publications, actions publier/supprimer.
- `resources/daemon/tests/unit/test_story_9_1_sensor_mapper.py` — baseline sensor.
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py` + `resources/daemon/tests/fixtures/golden_corpus/` — golden corpus.

### Dev Agent Guardrails

#### Guardrail — Deploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom reelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procedure parallele.
- Reference complete modes + cycle valide terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplace par le script) : `main -> beta -> stable -> Jeedom Market`.

#### Garde-fous implementation

- Ne pas ajouter `number` ou `select`.
- Ne pas publier les valeurs eq553 comme un seul sensor agregateur.
- Ne pas utiliser les noms des commandes comme identifiants stables.
- Ne pas casser les cas mono-entite historiques.
- Ne pas masquer une publication partielle : si un sensor echoue, le diagnostic ou les traces doivent rester honnetes.

### Project Structure Notes

- Story branch/worktree dedie : `story/pe-11.1-msunpv`.
- Les fichiers `_bmad-output/planning-artifacts/*` ne sont pas a modifier pour cette story sauf correction documentaire explicitement liee.
- `sprint-status.yaml` doit passer `pe-epic-11: in-progress` et `11-1-...: ready-for-dev` a la creation.

### References

- `_bmad-output/planning-artifacts/backlog-icebox.md` §3.1 — inventaire MSunPV eq553.
- `_bmad-output/implementation-artifacts/pe-epic-10-retro-2026-06-12.md` §Preparation pe-epic-11.
- `_bmad-output/project-context.md` — regles Python, MQTT Discovery, tests, deploiement terrain.
- `resources/daemon/mapping/sensor.py` — mapper sensor existant.
- `resources/daemon/discovery/publisher.py` — publication MQTT discovery sensor.
- `resources/daemon/transport/http_server.py` — orchestration du pipeline.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex (create-story) ; Claude Opus 4.8 (dev-story)

### Debug Log References

- `python3 -m pytest resources/daemon/tests -q` → 825 passed (823 + 2 tests d'eligibilite Fix A).
- Golden non-regression (`test_story_8_4_golden_file.py`) vert apres ajout eq553 et regeneration bornee de `expected_sync_snapshot.json`.
- Gate terrain 2026-06-17 : `/system/diagnostics` (eq553 publie) + `mosquitto_sub` (65 topics discovery retained).

### Completion Notes List

- Create-story completed: story 11.1 materialisee avec contexte multi-sensor eq553 et garde-fous terrain.
- API de mapping additive : `MappingResult.additional_mappings` + `MapperRegistry.map_all()` (avec `_invoke_mapper`), `SensorMapper.map_all()`. `MapperRegistry.map()` reste compatible (retourne le mapping principal, rattache les secondaires via `additional_mappings`). `PRODUCT_SCOPE` inchange.
- Multi-sensor borne au type d'eqLogic MSunPV (`_MULTI_SENSOR_EQ_TYPES = {"msunpv"}`) ; tout autre eqLogic conserve le comportement mono-sensor historique (AC#4 — non-regression). Seules les commandes `info`/`numeric` deviennent des sensors ; les actions sont ignorees (AC#2).
- Identite par commande derivee des IDs `cmd` Jeedom (jamais des noms) : `unique_id=jeedom2ha_eq_553_cmd_<cmd>`, `object_id/node_id=jeedom2ha_553_<cmd>`, `state_topic=jeedom2ha/553/<cmd>/state`. `device` HA commun conserve (`identifiers: ["jeedom2ha_553"]`) pour le groupement HA (AC#3, AC#5).
- `device_class` derive par `generic_type` connu sinon inference par unite (`W/kW→power`, `Wh/kWh→energy`, `V→voltage`, `A→current`) ; `None` honnete quand inconnu (pas de classe inventee).
- Diagnostic honnete (AC#6) : `_publish_additional_sensors` incremente les compteurs `sensors_*`/`published` reels ; en cas d'echec d'un secondaire, le `publication_result` du primaire passe a `failed` / `multi_sensor_partial_publish_failed` (pas de faux succes).
- Comportement borne `publier`/`supprimer` : ces actions restent mono-entite par `eq_id` (inchangees). Le support action multi-entite n'est pas ouvert par cette story ; comportement documente ici comme out-of-scope.
- Gate terrain (Task 0 + Task 5 dernier point) : **PASS le 2026-06-17** sur box reelle DEV/TEST `192.168.1.21` (`./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → `Deploy complete.`, sync `succes`). Preuves MQTT (broker 127.0.0.1:1883, creds `mqtt2`) : eq553 `perimetre=inclus`, `statut=publie`, `ha_type=sensor` ; 65 topics discovery `homeassistant/sensor/jeedom2ha_553_<cmd>/config` retained ; chaque payload porte `unique_id=jeedom2ha_eq_553_cmd_<cmd>`, `object_id=jeedom2ha_553_<cmd>`, `state_topic=jeedom2ha/553/<cmd>/state`, `device.identifiers=["jeedom2ha_553"]` commun, `device_class` infere par unite (ex. `#5138` Puissance panneaux → power/W) ; `jeedom2ha/553/availability=online`. Les valeurs d'etat par commande sont event-driven (publiees au prochain changement Jeedom), comportement attendu.
- **Terrain vs inventaire** : l'inventaire AC#2 listait 8 commandes (sous-ensemble curate du backlog-icebox §3.1). Le vrai eq553 expose **65** commandes info numeriques → 65 sensors publies. Aucune regression : le multi-sensor mapper traite toutes les commandes info/numeric de l'eqLogic msunpv.
- **Fix A — gate d'eligibilite (decouvert au gate terrain)** : le vrai eq553 ne porte aucun `generic_type`, donc `assess_eligibility()` le classait `no_supported_generic_type` et il n'atteignait jamais le multi-sensor mapper (0 sensor sur box). Les tests masquaient le defaut (fixture avec `generic_type="POWER"`). Correctif : `MULTI_SENSOR_EQ_TYPES` (source unique dans `models/topology.py`, partagee avec `SensorMapper`) + `_has_numeric_info_command()` ; `assess_eligibility()` rend eligibles les eqTypes multi-sensor sans `generic_type` des qu'ils portent ≥1 commande info numerique. Garde-fou AC#4 : aucun autre eqType ne beneficie du contournement. Fixture de test rendue fidele au terrain (tous `generic_type=None`) + 2 tests d'eligibilite ajoutes. Suite pytest complete : 825 passed.

### File List

- `_bmad-output/implementation-artifacts/11-1-msunpv-routeursolaire-sensors-lecture-seule.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/models/mapping.py`
- `resources/daemon/models/topology.py` (Fix A — eligibilite multi-sensor sans generic_type)
- `resources/daemon/mapping/sensor.py`
- `resources/daemon/mapping/registry.py`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py`
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py`
- `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`

### Change Log

- 2026-06-12 — Story 11.1 creee via workflow create-story.
- 2026-06-17 — dev-story : implementation multi-sensor MSunPV eq553 (API additive, publisher per-commande, orchestration sync, diagnostic honnete, golden corpus). Suite pytest 823 verte. Gate terrain waived (materiel indisponible). Status → review.
- 2026-06-17 — gate terrain rejoue sur box reelle 192.168.1.21 : decouverte d'une regression d'eligibilite (eq553 sans generic_type rejete). Fix A applique (`models/topology.py`), fixture rendue fidele au terrain, +2 tests. Gate PASS : 65 sensors eq553 publies. Suite pytest 825 verte. Follow-up MEDIUM (cycle de vie multi-sensor) eleve en story 11.1.bis via correct-course.

