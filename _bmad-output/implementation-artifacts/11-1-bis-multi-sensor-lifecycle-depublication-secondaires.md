# Story 11.1.bis: Multi-sensor lifecycle — dépublication exhaustive des sensors secondaires (anti-ghosts HA)

Status: review

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

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — NON EXÉCUTÉ (pas d'accès box dans cet environnement)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Tracer les secondaires multi-sensor par eq_id (AC: 1)
  - [x] Stocker les mappings/publications secondaires aux côtés du primaire (structure indexée par `eq_id`) lors de `_publish_additional_sensors`. → Les secondaires sont déjà portés par `mapping_result.additional_mappings` dans `app["publications"][eq_id]` ; pas de structure parallèle nécessaire.
  - [x] Conserver assez d'information (`node_id` dérivé de `cmd_id`) pour reconstruire les topics secondaires sans re-parser la topologie. → Helper `_collect_unpublish_node_ids` + persistance `node_ids` dans le cache disque (`_extract_node_ids`).
  - [x] Ajouter un test rouge décrivant qu'après sync, eq553 expose la liste de ses secondaires. → `test_collect_node_ids_multi_sensor_returns_all_per_command_topics`, `test_disk_cache_persists_and_reloads_secondary_node_ids`.

- [x] Task 2 — Dépublication exhaustive (AC: 2, 4, 5)
  - [x] Étendre `unpublish_by_eq_id` pour effacer le primaire **et** tous les secondaires connus de l'eq_id (param `node_ids`).
  - [x] Réutiliser `_build_topic(eq_id, entity_type, node_id=...)` pour chaque secondaire.
  - [x] Garde-fou mono-entité : `node_ids=[]` → exactement un topic effacé (comportement inchangé).
  - [x] Honnêteté : agrégation `all_ok` (pas d'arrêt au premier échec), un secondaire non effacé renvoie `False`.

- [x] Task 3 — Couvrir tous les déclencheurs de cycle de vie (AC: 3)
  - [x] Chaque appel à `unpublish_by_eq_id` calcule `node_ids` (runtime via `_collect_unpublish_node_ids`, boot via `cache["node_ids"]`) : retype runtime/boot, changement de politique, purge boot/standard, action supprimer, action publier-exclus.
  - [x] Chemins retype : nettoient aussi les secondaires de l'ancien état. Replay différé (`pending_discovery_unpublish`) transporte désormais `{entity_type, node_ids}`.

- [x] Task 4 — Tests + golden + gate terrain (AC: 6, 7)
  - [x] Tests unitaires : dépublication multi-sensor efface N topics ; mono-entité efface 1 topic ; échec partiel honnête. → `test_story_11_1_bis_multi_sensor_unpublish.py`.
  - [x] Cas de dépublication multi-sensor : couvert par le test end-to-end `test_action_supprimer_erases_all_multi_sensor_topics` (le golden `expected_sync_snapshot.json` est un snapshot de **sync**, pas de dépublication → un test dédié est plus fidèle qu'un delta de snapshot).
  - [x] Suite pytest complète verte : **835 passed**.
  - [ ] Gate terrain (AC 6) : `mosquitto_sub` sur box réelle — NON EXÉCUTÉ (pas d'accès box dans cet environnement). À valider avant release Market.

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
- Dev-story (Opus 4.8) :
  - **Constat aggravant** : le primaire multi-sensor est lui aussi node-scoped (`jeedom2ha_<eq>_<cmd>`), donc l'ancienne dépublication mono-topic `jeedom2ha_<eq>/config` n'effaçait **aucun** des topics réels → 65 ghosts pour eq553, pas 64. La collecte des `node_ids` inclut donc le primaire ET les secondaires.
  - `publisher.unpublish_by_eq_id` accepte `node_ids: Optional[list]=None`. Si fourni : un topic effacé par node_id (primaire + secondaires) ; sinon : topic eq-level historique (mono-entité). Agrégation `all_ok` sans court-circuit → AC 5 (honnêteté échec partiel). Signature rétro-compatible (AC 4).
  - `cache/disk_cache.py` : helper `_extract_node_ids`, champ `node_ids` persisté + relecture rétro-compatible (caches 5.1/5.2 sans `node_ids` → `[]`).
  - `transport/http_server.py` : helper `_collect_unpublish_node_ids(mapping_result)` (primaire + `additional_mappings`, `[]` si mono). Les 7 sites d'appel `unpublish_by_eq_id` calculent et passent `node_ids` (runtime via le helper, boot via `cache["node_ids"]`). Le replay différé `pending_discovery_unpublish` stocke désormais `{entity_type, node_ids}` (helpers `_defer_discovery_unpublish` / `_pending_unpublish_parts`) au lieu d'une string.
  - **Régressions corrigées** : le passage de `unpublish_by_eq_id(...)` avec `node_ids=[]` (mono) + le changement de format de `pending_discovery_unpublish` ont cassé 19 tests existants (assertions de signature exacte + format de la valeur différée + un mock side_effect à signature figée). Tous mis à jour vers la nouvelle signature (`node_ids=[]` pour mono) ; le comportement de production mono-entité est **strictement inchangé** (un seul topic).
  - **Non vérifiable ici** : Task 0 (deploy-to-box) et AC 6 (gate terrain `mosquitto_sub`) nécessitent la box Jeedom physique — à exécuter avant release Market.

### File List

**Production :**
- `resources/daemon/discovery/publisher.py` — `unpublish_by_eq_id` étendu (param `node_ids`, dépublication exhaustive, agrégation honnête).
- `resources/daemon/cache/disk_cache.py` — `_extract_node_ids` + persistance/relecture rétro-compatible du champ `node_ids`.
- `resources/daemon/transport/http_server.py` — `_collect_unpublish_node_ids`, format dict `pending_discovery_unpublish` (`_defer_discovery_unpublish` / `_pending_unpublish_parts` / replay), 7 sites unpublish câblés.

**Tests :**
- `resources/daemon/tests/unit/test_story_11_1_bis_multi_sensor_unpublish.py` — NOUVEAU (collecte node_ids, dépublication exhaustive, échec partiel, BC, cache, end-to-end supprimer).
- `resources/daemon/tests/unit/test_story_5_3_execute_supprimer.py` — mock + assertion signature `node_ids`.
- `resources/daemon/tests/unit/test_cleanup.py` — assertions signature `node_ids` + format dict `pending_discovery_unpublish`.
- `resources/daemon/tests/unit/test_exclusion_filtering.py` — assertion signature `node_ids`.
- `resources/daemon/tests/unit/test_story_5_2_execute_publier.py` — assertion signature `node_ids`.
- `resources/daemon/tests/unit/test_story_5_2_integration.py` — assertion signature `node_ids`.
- `resources/daemon/tests/integration/test_boot_reconciliation.py` — assertions signature `node_ids` (×3).

### Change Log

| Date | Version | Description | Auteur |
|------|---------|-------------|--------|
| 2026-06-17 | 0.1 | Création story (correct-course handoff) | Opus 4.8 |
| 2026-06-17 | 1.0 | Implémentation dev-story : dépublication exhaustive multi-sensor (node_ids), persistance cache, 7 sites de cycle de vie câblés, replay différé en dict, 19 régressions corrigées. Suite verte 835 passed. Status → review. | Opus 4.8 |
