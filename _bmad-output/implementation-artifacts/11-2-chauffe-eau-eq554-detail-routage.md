# Story 11.2: Chauffe-eau eq554 — exposer le détail de routage en multi-domaine lecture seule (sensor + binary_sensor + actionnables)

Status: ready-for-dev

## Story

En tant qu'utilisateur familial de Home Assistant,
je veux voir dans HA le détail de routage du chauffe-eau Jeedom `eq554` (routage réel, puissance, état on/off, chauffe complète, équivalent heures, kWh) en plus du `switch.jeedom2ha_554` déjà publié,
afin de suivre sur le dashboard solaire la consommation et le pilotage du cumulus, sans ouvrir de nouveau type HA.

## Acceptance Criteria

1. **Périmètre strict eq554.** La story cible uniquement le chauffe-eau `eq554` et n'altère pas le MSunPV `eq553` (Story 11.1) ni aucun autre eqLogic. Aucune ouverture de type dans `PRODUCT_SCOPE` (`sensor`, `binary_sensor`, `switch`, `button` sont déjà ouverts).
2. **Inventaire multi-domaine eq554 (source `backlog-icebox.md §3.2`).** Les commandes du chauffe-eau sont projetables, chacune dans son domaine HA, sous un device commun :
   - `sensor` : `#5530` Routage réel (`%`), `#5206` Puissance (`W`), `#5538` Équivalent H de chauffe aujourd'hui (`H`), `#5527` kWh depuis hier (`kWh`).
   - `binary_sensor` : `#5489` Etat on/off, `#5510` Chauffe complète dans la journée, `#5708` Activé.
   - actionnables `switch`/`button` : `#5490` Manu, `#5491` Auto, `#5372` Absence — **comportement existant conservé** (voir AC#4), pas d'ouverture de type.
   - **L'inventaire ci-dessus est un sous-ensemble curate.** Le vrai eq554 peut exposer davantage de commandes (précédent eq553 : 8 listées → 65 réelles). Le mapping doit traiter **toutes** les commandes éligibles de l'eqLogic, pas seulement les 10 listées (voir Task 1).
3. **Multi-domaine borné sur un eqLogic unique.** L'eqLogic `eq554` produit plusieurs entités HA de domaines différents (`sensor`, `binary_sensor`, et l'actionnable existant) rattachées au **même device HA** `identifiers: ["jeedom2ha_554"]`, chacune avec `unique_id`, `object_id`, topic discovery et `state_topic` distincts dérivés de l'ID `cmd` Jeedom (jamais du nom).
4. **Non-régression du `switch.jeedom2ha_554` existant.** Le `switch.jeedom2ha_554` publié aujourd'hui par `SwitchMapper` (commandes `ENERGY_*`) conserve son `unique_id` historique (`jeedom2ha_eq_554`), son comportement de publication et son streaming d'état (vague 2 / Story 12.2). Aucune entité dupliquée pour la capacité on/off déjà couverte par le switch.
5. **Contrainte registry « premier mapper gagnant ».** `MapperRegistry.map_all()` s'arrête au premier mapper qui reconnaît l'eqLogic (`registry.py:69-73`). eq554 est aujourd'hui capté par `SwitchMapper` (3ᵉ) → ses `sensor`/`binary_sensor` ne sont jamais atteints. La story doit lever cette limite **uniquement pour l'eqType routeur-solaire chauffe-eau**, sans changer le dispatch des autres eqLogics (mono-domaine inchangé).
6. **Pas de régression mono-entité.** Les mappers `light`, `cover`, `switch`, `climate`, `alarm_control_panel`, `presence_switch`, `binary_sensor`, `sensor` (mono + multi-sensor eq553), `button`, fallback conservent leur comportement sur tous les eqLogics non-eq554.
7. **Validation HA obligatoire.** Chaque entité dérivée de eq554 passe par `validate_projection()` avec les capabilities adaptées (`SensorCapabilities(has_state=True)` pour les sensors, capabilities binaires pour les binary_sensors) et ne publie rien si la validation échoue.
8. **Diagnostic et compteurs cohérents et honnêtes.** Le sync expose un mapping/publication lisible pour eq554 : les compteurs par domaine (`sensor`, `binary_sensor`, `published`) reflètent les entités publiées ; un échec de publication d'une entité secondaire ne produit pas un faux succès (héritage du diagnostic honnête Story 11.1).
9. **Cycle de vie multi-entité (anti-ghosts).** La dépublication de eq554 (`unpublish_by_eq_id`) nettoie **tous** les topics discovery secondaires `homeassistant/<domain>/jeedom2ha_554_<cmd>/config`, sans laisser de fantôme HA (héritage Story 11.1.bis).
10. **Golden corpus et non-régression.** Le golden corpus intègre un cas eq554 représentatif (multi-domaine) ; `expected_sync_snapshot.json` n'est régénéré que pour les deltas attendus ; la suite pytest complète reste verte.
11. **Gate terrain.** Sur box réelle DEV/TEST `192.168.1.21`, après `deploy → restart → sync`, les topics discovery des entités eq554 (sensors + binary_sensors) sont publiés sous le device `jeedom2ha_554`, le `switch.jeedom2ha_554` reste présent et non-`unknown` (état readback streamé par 12.2), et les valeurs sont lisibles dans HA/MQTT. Gate documentable avec waiver explicite si l'équipement live est indisponible au moment du test.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
  - [ ] **Capturer la topologie réelle de eq554** (`/topology` ou snapshot Jeedom) : `eq_type_name`, et pour chaque commande `type`/`sub_type`/`generic_type`/`unit`. C'est la donnée décisive : l'inventaire `backlog-icebox.md §3.2` est curate et peut diverger (précédent eq553 65 cmds + absence de `generic_type`).

- [ ] Task 1 — Caractériser le besoin multi-domaine eq554 (AC: 1, 2, 3, 5)
  - [ ] À partir de la topologie réelle capturée (Task 0), figer la liste des commandes éligibles et leur domaine cible (`sensor` info numérique, `binary_sensor` info binaire, actionnable déjà couvert par le switch).
  - [ ] Ajouter un test unitaire rouge décrivant eq554 (fixture fidèle au terrain : `eq_type_name` réel, `generic_type` réel ou `None`) et attendant N `sensor` + M `binary_sensor` + le `switch` historique, tous rattachés au device `jeedom2ha_554`.
  - [ ] Borner explicitement : chaque commande `info` numérique → `sensor` ; chaque commande `info` binaire → `binary_sensor` ; les commandes `action` `ENERGY_*` restent gérées par `SwitchMapper` (pas de doublon).

- [ ] Task 2 — Lever la contrainte « premier mapper gagnant » pour l'eqType chauffe-eau, sans régression (AC: 3, 4, 5, 6)
  - [ ] Décider de l'approche multi-domaine bornée. **Recommandé** : un mapper multi-domaine dédié (ou extension du chemin multi-entité existant) gaté sur l'`eq_type_name` réel du chauffe-eau, qui agrège `sensor` + `binary_sensor` par commande **et délègue/conserve** le `switch` `ENERGY_*` produit par `SwitchMapper` (pas de réécriture du switch, AC#4). Alternative : agrégation registry multi-mapper bornée au seul eqType chauffe-eau.
  - [ ] Étendre `MULTI_SENSOR_EQ_TYPES` / introduire un ensemble `MULTI_DOMAIN_EQ_TYPES` dans `models/topology.py` (source unique partagée), gaté sur l'eqType réel capturé. **Ne pas** élargir le contournement à d'autres eqTypes (garde-fou AC#6).
  - [ ] Préserver `MapperRegistry.map()` (mapping principal + `additional_mappings`) et tous les consommateurs mono-mapping par `eq_id`.
  - [ ] Ne pas modifier `PRODUCT_SCOPE`.

- [ ] Task 3 — Publier des topics discovery/state distincts par commande et par domaine (AC: 3, 7) 
  - [ ] Étendre la publication multi-entité (aujourd'hui sensor-only, `_publish_additional_sensors` dans `http_server.py`) pour gérer les `binary_sensor` secondaires : payload `binary_sensor` HA, `node_id`/`object_id`/`unique_id`/`state_topic` distincts par commande, device commun `jeedom2ha_554`.
  - [ ] Réutiliser `DiscoveryPublisher.publish_binary_sensor()` existant pour les payloads (ne pas réinventer).
  - [ ] Identité dérivée des IDs cmd Jeedom : `unique_id=jeedom2ha_eq_554_cmd_<cmd>`, `object_id/node_id=jeedom2ha_554_<cmd>`, `state_topic=jeedom2ha/554/<cmd>/state` (cohérent avec la convention eq553).
  - [ ] Ajouter des tests sur les payloads des sensors et binary_sensors eq554.

- [ ] Task 4 — Diagnostic, compteurs, cycle de vie et streaming sans régression (AC: 4, 8, 9)
  - [ ] Vérifier que les compteurs par domaine (`sensor`, `binary_sensor`, `published`) comptent les entités multi-domaine publiées.
  - [ ] Vérifier que le diagnostic eq554 reste honnête : un échec de publication secondaire ne déclare pas un faux succès (`multi_*_partial_publish_failed`).
  - [ ] Vérifier la dépublication exhaustive eq554 (`unpublish_by_eq_id`) : aucun topic discovery secondaire orphelin (réutiliser le mécanisme Story 11.1.bis).
  - [ ] Vérifier que le streaming d'état (Story 12.1 sensor/binary, 12.2 switch) cible bien les `state_topic` per-commande des nouvelles entités eq554 (état initial + event-driven).

- [ ] Task 5 — Golden corpus, tests complets et gate terrain (AC: 10, 11)
  - [ ] Ajouter eq554 au golden corpus (cas multi-domaine représentatif).
  - [ ] Régénérer/ajuster `expected_sync_snapshot.json` uniquement pour les deltas attendus.
  - [ ] Lancer la suite pytest complète (`python3 -m pytest resources/daemon/tests -q`).
  - [ ] Exécuter le gate terrain via `scripts/deploy-to-box.sh` et documenter les preuves (topics discovery eq554 retained, device commun, switch non-`unknown`). Waiver explicite si matériel indisponible.

## Dev Notes

### Source produit et scope

- Source de vérité fonctionnelle : `_bmad-output/planning-artifacts/backlog-icebox.md` §3.2 (inventaire chauffe-eau eq554).
- Définition epic : `_bmad-output/planning-artifacts/epics-projection-engine.md` §« Story 11.2 (réservée) — Chauffe-eau eq554 ».
- **Dépendance pe-epic-12 levée** : le bug historique `switch.jeedom2ha_554 = unknown` est **résolu** par le streaming d'état vague 2 (Story 12.2, mergée main PR #125). Le gate terrain 12.2 a observé `eq554=OFF` (état switch réel, plus `unknown`). Cette story ne refait donc PAS le diagnostic « unknown » : elle ajoute la **restitution discovery lecture seule** du détail de routage (sensors + binary_sensors) absent aujourd'hui.
- pe-epic-11 reste un epic de **restitution discovery lecture seule**. Aucune valeur runtime n'est ajoutée ici (elle relève de pe-epic-12, déjà done) : la story réutilise les `state_topic` que 12.1/12.2 alimentent.
- Aucun nouveau composant HA : `sensor`, `binary_sensor`, `switch`, `button` sont déjà dans `PRODUCT_SCOPE`.

### Analyse architecture

- **Le pipeline mappe un `JeedomEqLogic` → un mapper « gagnant » → 1..N `MappingResult`.** Story 11.1 a introduit le multi-**entité** mono-domaine (eq553 → N `sensor`) via `MappingResult.additional_mappings` + `MapperRegistry.map_all()` + `SensorMapper.map_all()`. Story 11.2 introduit le premier besoin **multi-domaine** (1 eqLogic → `sensor` + `binary_sensor` + `switch`).
- **Contrainte décisive (`registry.py:61-73`)** : `map_all` retourne les résultats du **premier** mapper qui produit ≥1 résultat, puis s'arrête. Ordre du registry : `Light, Cover, Switch, Climate, Alarm, PresenceSwitch, BinarySensor, Sensor, Button, Fallback`. eq554 possède des commandes `ENERGY_*` → `SwitchMapper` (rang 3) le capte et `map_all` s'arrête → ses commandes `sensor`/`binary_sensor` ne sont jamais mappées. **C'est pourquoi seul `switch.jeedom2ha_554` est publié aujourd'hui.**
- **Approche recommandée (bornée, sans régression)** : un chemin multi-domaine gaté sur l'`eq_type_name` réel du chauffe-eau (analogue à `MULTI_SENSOR_EQ_TYPES` mais étendu aux binaires), placé de façon à agréger les domaines pour ce seul eqType, tout en **conservant** le `switch` historique produit par `SwitchMapper` (mêmes `unique_id`/topics, AC#4). Ne pas dupliquer la capacité on/off déjà portée par le switch.
- **eqType eq554 vs eq553** : eq553 (msunpv, sans `generic_type`) est capté par `SensorMapper` multi-sensor. eq554 publie un `switch` → il porte des commandes `ENERGY_*` avec `generic_type` (sinon `SwitchMapper` ne le capterait pas). Donc eq553 et eq554 n'ont **pas** le même profil de commandes même s'ils peuvent partager un plugin. **Le gating multi-domaine doit cibler eq554 sans réabsorber eq553** (qui doit rester sensor-pur, AC#1/#6). Vérifier l'`eq_type_name` réel des deux au terrain avant de choisir la clé de gating.
- Identité par commande dérivée des IDs `cmd` Jeedom (jamais des noms) ; `device` HA commun `jeedom2ha_554` pour le groupement HA.
- Toute publication reste gouvernée par les étapes 3/4/5 : mapping → validation HA → décision → publication MQTT.

### Code à inspecter / modifier

- `resources/daemon/models/topology.py` — `MULTI_SENSOR_EQ_TYPES`, `_has_numeric_info_command`, `assess_eligibility` (éligibilité sans `generic_type`). Source unique du gating eqType.
- `resources/daemon/mapping/sensor.py` — `SensorMapper.map_all` / `_map_multi_sensor` (patron multi-entité à étendre/imiter pour le binaire).
- `resources/daemon/mapping/binary_sensor.py` — `BinarySensorMapper` (réutiliser la logique de détection binaire, ne pas réinventer).
- `resources/daemon/mapping/switch.py` — `SwitchMapper` (commandes `ENERGY_*` → switch historique eq554 ; ne pas casser).
- `resources/daemon/mapping/registry.py` — dispatch `map`/`map_all` (contrainte premier-mapper-gagnant).
- `resources/daemon/models/mapping.py` — `MappingResult.additional_mappings`, `SensorCapabilities`, capabilities binaires.
- `resources/daemon/discovery/publisher.py` — `publish_sensor` / `publish_binary_sensor` (payloads + topics per-commande).
- `resources/daemon/discovery/registry.py` — dispatch publisher.
- `resources/daemon/transport/http_server.py` — orchestration sync, `_publish_additional_sensors` (~ligne 600), compteurs, `unpublish_by_eq_id` (~ligne 1248-1315), `additional_mappings`.
- `resources/daemon/sync/state.py` — résolveur d'état runtime (12.1/12.2) gaté sur la discovery du candidat (`state.py:286`) ; les nouveaux `state_topic` eq554 doivent être alimentés.
- `resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py` — patron de test multi-entité.
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py` + `resources/daemon/tests/fixtures/golden_corpus/` — golden corpus.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

#### Garde-fous implémentation

- Ne pas ouvrir `number`, `select`, ni aucun type hors `PRODUCT_SCOPE`.
- Ne pas dupliquer le `switch.jeedom2ha_554` existant : la capacité on/off reste portée par `SwitchMapper` avec son `unique_id` historique.
- Ne pas réabsorber eq553 (msunpv sensor-pur) dans le chemin multi-domaine eq554.
- Ne pas utiliser les noms de commandes comme identifiants stables (toujours les IDs `cmd`).
- Ne pas masquer une publication partielle : un échec secondaire doit rester visible dans le diagnostic/traces.
- Ne pas étendre le gating multi-domaine au-delà de l'eqType chauffe-eau réel.
- Ne pas modifier les artefacts `_bmad-output/planning-artifacts/*` (sauf correction documentaire explicitement liée).

### Project Structure Notes

- Story branch/worktree dédié : `story/pe-11.2-eq554` (créé depuis `main`, qui porte 11.1, 11.1.bis, 12.1, 12.2).
- `sprint-status.yaml` : `pe-epic-11` reste `in-progress` ; `11-2-...` passe `backlog → ready-for-dev` à la création.
- Filename/key : `11-2-chauffe-eau-eq554-detail-routage`.

### References

- `_bmad-output/planning-artifacts/backlog-icebox.md` §3.2 — inventaire chauffe-eau eq554.
- `_bmad-output/planning-artifacts/epics-projection-engine.md` §Epic 11 / Story 11.2 + §Epic 12 / Story 12.2.
- `_bmad-output/implementation-artifacts/11-1-msunpv-routeursolaire-sensors-lecture-seule.md` — patron multi-entité (API additive, identité per-commande, diagnostic honnête, Fix A éligibilité).
- `_bmad-output/implementation-artifacts/11-1-bis-multi-sensor-lifecycle-depublication-secondaires.md` — dépublication exhaustive multi-entité (anti-ghosts).
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-18-pe-11.3.md` — séquence 12.1 → 11.2 → 12.2 → 11.3 et dépendances de streaming.
- `resources/daemon/mapping/registry.py` — contrainte premier-mapper-gagnant.
- `resources/daemon/mapping/sensor.py`, `resources/daemon/mapping/binary_sensor.py`, `resources/daemon/mapping/switch.py` — mappers concernés.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (create-story)

### Debug Log References

### Completion Notes List

- Create-story completed : story 11.2 matérialisée à partir de l'inventaire eq554 (`backlog-icebox.md §3.2`) et du patron multi-entité 11.1. Contrainte architecturale clé identifiée : `MapperRegistry.map_all` « premier mapper gagnant » qui explique pourquoi seul `switch.jeedom2ha_554` est publié aujourd'hui. Dépendance 12.2 levée (switch.554 non-`unknown`, `eq554=OFF` observé au gate terrain 12.2). Task 0 terrain injectée (story daemon/MQTT/discovery) avec capture obligatoire de la topologie réelle eq554 (l'inventaire backlog est curate ; précédent eq553 8→65 cmds + absence de `generic_type`).

### File List

- `_bmad-output/implementation-artifacts/11-2-chauffe-eau-eq554-detail-routage.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-06-19 — Story 11.2 créée via workflow create-story (multi-domaine eq554, lecture seule discovery).
