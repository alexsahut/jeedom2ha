# Story 11.1.bis: Multi-sensor lifecycle — dépublication exhaustive des sensors secondaires (anti-ghosts HA)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur familial de Home Assistant,
je veux que la suppression / désactivation / exclusion / retype d'un équipement multi-sensor (ex. MSunPV/RouteurSolaire eq553) retire **toutes** ses entités `sensor` de Home Assistant,
afin de ne pas laisser d'entités fantômes (ghosts) qui polluent le dashboard solaire et faussent l'état réel du périmètre publié.

## Acceptance Criteria

1. **Stockage des secondaires.** Les mappings et résultats de publication des sensors secondaires d'un eqLogic multi-sensor sont traçables par `eq_id` (pas seulement le primaire), afin de permettre une dépublication exhaustive ultérieure sans dépendre du re-parsing de la topologie.
2. **Dépublication exhaustive.** `unpublish_by_eq_id` (ou son remplaçant) efface **tous** les topics discovery d'un eqLogic multi-sensor : le primaire `homeassistant/sensor/jeedom2ha_<eq>/config` **et** chaque secondaire `homeassistant/sensor/jeedom2ha_<eq>_<cmd>/config`. Aucun topic retained ne subsiste après dépublication.
3. **Déclencheurs couverts.** La dépublication exhaustive s'applique à tous les chemins de cycle de vie existants : suppression explicite (`/action/execute` supprimer), exclusion, désactivation, retype (changement de `ha_entity_type`), et nettoyage bootstrap d'un eq_id précédent.
4. **Pas de régression mono-entité.** Les eqLogics mono-entité (`light`, `cover`, `switch`, `climate`, `sensor` historique, etc.) conservent strictement leur comportement de dépublication actuel (un seul topic effacé). Aucune sur-suppression.
5. **Honnêteté diagnostique.** Si la dépublication d'un secondaire échoue, le résultat global ne déclare pas un faux succès ; le diagnostic / les traces restent honnêtes (cohérent avec le pattern `multi_sensor_partial_publish_failed` de la Story 11.1).
6. **Gate terrain de dépublication.** Sur box réelle DEV/TEST, après publication d'eq553 puis suppression/exclusion, le broker MQTT ne contient **plus aucun** topic `homeassistant/sensor/jeedom2ha_553_<cmd>/config` retained (vérifié via `mosquitto_sub`). Zéro ghost résiduel dans HA.
7. **Non-régression.** La suite pytest complète reste verte et le golden corpus intègre un cas de dépublication multi-sensor.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [ ] Task 1 — Tracer les secondaires multi-sensor par eq_id (AC: 1)
  - [ ] Stocker les mappings/publications secondaires aux côtés du primaire (structure indexée par `eq_id`) lors de `_publish_additional_sensors`.
  - [ ] Conserver assez d'information (au minimum `node_id`/`object_id` ou `cmd_id`) pour reconstruire les topics secondaires sans re-parser la topologie.
  - [ ] Ajouter un test rouge décrivant qu'après sync, eq553 expose la liste de ses secondaires.

- [ ] Task 2 — Dépublication exhaustive (AC: 2, 4, 5)
  - [ ] Étendre `unpublish_by_eq_id` (ou ajouter une voie multi-sensor) pour effacer le primaire **et** tous les secondaires connus de l'eq_id.
  - [ ] Réutiliser `_build_topic(eq_id, entity_type, node_id=...)` pour chaque secondaire (le paramètre `node_id` existe déjà).
  - [ ] Garde-fou mono-entité : un eqLogic sans secondaires efface exactement un topic (comportement inchangé).
  - [ ] Honnêteté : agréger les échecs de dépublication, ne pas masquer un secondaire non effacé.

- [ ] Task 3 — Couvrir tous les déclencheurs de cycle de vie (AC: 3)
  - [ ] Vérifier/adapter chaque appel à `unpublish_by_eq_id` : supprimer, exclure, désactiver, retype, cleanup bootstrap.
  - [ ] S'assurer que les chemins retype (ancien `eq_id`/type) nettoient aussi les secondaires de l'ancien état.

- [ ] Task 4 — Tests + golden + gate terrain (AC: 6, 7)
  - [ ] Tests unitaires : dépublication multi-sensor efface N+1 topics ; mono-entité efface 1 topic ; échec partiel honnête.
  - [ ] Ajouter au golden corpus un cas de dépublication multi-sensor (delta borné de `expected_sync_snapshot.json` si nécessaire).
  - [ ] Lancer la suite pytest complète.
  - [ ] Gate terrain : publier eq553, puis supprimer/exclure, et vérifier via `mosquitto_sub` qu'aucun `jeedom2ha_553_<cmd>/config` retained ne subsiste.

## Dev Notes

### Contexte et origine

- Dette identifiée en review de la Story 11.1 (Follow-up MEDIUM) puis **aggravée et confirmée** au gate terrain du 2026-06-17 : le vrai eq553 publie **65** sensors (et non 8). À la dépublication, 64 secondaires resteraient orphelins.
- Élevée en story dédiée via Sprint Change Proposal 2026-06-17 (`_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-17.md`).
- Scope strictement borné : robustesse du cycle de vie multi-sensor. N'ouvre aucun nouveau type HA, ne modifie pas `PRODUCT_SCOPE`, ne touche pas au mapping/publication nominal de 11.1 (qui est PASS terrain).

### Analyse du défaut (code actuel)

- `resources/daemon/discovery/publisher.py:299` — `unpublish_by_eq_id(eq_id, entity_type)` construit **un seul** topic via `_build_topic(eq_id, entity_type)` avec `node_id=None` → n'efface que `jeedom2ha_<eq>/config`.
- `resources/daemon/discovery/publisher.py:313` — `_build_topic(eq_id, entity_type, node_id=None)` : `path_part = node_id if node_id else f"jeedom2ha_{eq_id}"`. Le paramètre `node_id` **existe déjà** : la publication des secondaires l'utilise (`jeedom2ha_<eq>_<cmd>`), mais la dépublication ne le passe jamais.
- `resources/daemon/transport/http_server.py:184` — `_publish_additional_sensors(...)` publie les secondaires (appel ligne ~1252) mais ne les stocke pas sous `publications[eq_id]` → ils sont invisibles à la dépublication.
- Appels `unpublish_by_eq_id` à couvrir : `http_server.py:635, 668, 698, 1298, 1351, 1386, 2319, 2520` (supprimer / exclure / désactiver / retype / cleanup bootstrap).

### Code à inspecter / modifier

- `resources/daemon/transport/http_server.py` — orchestration sync (stockage secondaires), chemins unpublish.
- `resources/daemon/discovery/publisher.py` — `unpublish_by_eq_id`, `_build_topic`.
- `resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py` — baseline multi-sensor (réutiliser fixture eq553 fidèle terrain : toutes commandes `generic_type=None`).
- `resources/daemon/tests/unit/test_story_5_3_execute_supprimer.py` — baseline dépublication.
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py` + `resources/daemon/tests/fixtures/golden_corpus/` — golden corpus.

### Dev Agent Guardrails

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`
- Le mode `--stop-daemon-cleanup` est idéal pour vérifier la disparition des entités sans republier (preuve « HA propre »).

#### Garde-fous implementation

- Ne pas modifier le comportement de publication nominal de la Story 11.1 (gate terrain PASS).
- Ne pas sur-supprimer : un eqLogic mono-entité doit toujours effacer exactement un topic.
- Ne pas masquer un échec de dépublication d'un secondaire.
- Ne pas re-parser la topologie pour deviner les secondaires : s'appuyer sur l'état publié stocké par eq_id.
- Identité des secondaires dérivée des IDs `cmd` Jeedom (jamais des noms), cohérent avec 11.1.

### Project Structure Notes

- Story branch/worktree dédié suggéré : `story/pe-11.1-bis-multi-sensor-lifecycle`.
- `sprint-status.yaml` : `pe-epic-11: in-progress` (déjà), `11-1-bis-...: ready-for-dev` à la création.
- Numérotation : `11.1.bis` (follow-up couplé à 11.1) volontairement choisie pour **laisser le slot 11.2 au chauffe-eau eq554** (backlog-icebox §3.2, P2 Alex).
- Ne pas modifier les `_bmad-output/planning-artifacts/*` sauf correction documentaire explicitement liée.

### References

- `_bmad-output/implementation-artifacts/11-1-msunpv-routeursolaire-sensors-lecture-seule.md` — Review Follow-up MEDIUM + Completion Notes gate terrain (origine de la dette).
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-17.md` — élévation de la story.
- `_bmad-output/planning-artifacts/backlog-icebox.md` §3.1 — inventaire MSunPV eq553.
- `resources/daemon/discovery/publisher.py#unpublish_by_eq_id` — défaut de dépublication mono-topic.
- `resources/daemon/transport/http_server.py#_publish_additional_sensors` — publication secondaires non stockée.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (create-story via correct-course handoff)

### Debug Log References

### Completion Notes List

- Create-story : story 11.1.bis matérialisée à partir du Follow-up MEDIUM de 11.1, élevé via Sprint Change Proposal 2026-06-17. Numéro `11.1.bis` (et non 11.2) pour préserver le slot 11.2 = chauffe-eau eq554. Scope = robustesse cycle de vie multi-sensor (dépublication exhaustive anti-ghosts). Task 0 terrain injectée (story daemon/MQTT/discovery).

### File List
