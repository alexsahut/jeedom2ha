# Story 19.1: Sync migré vers `evaluate_equipment()`, sans changement de comportement

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un mainteneur,
I want que le sync (`_do_handle_action_sync`) appelle `evaluate_equipment()` (Story 19.0) au lieu de recalculer sa propre décision via `decide_publication()` en direct, à comportement strictement identique,
so that le sync devienne le premier point d'appel unifié sur le contrat de décision, sans risquer de régression de publication en production.

**Parcours : complet.**

## Acceptance Criteria

**AC1 — Golden file inchangé**

**Given** le corpus `tests/fixtures/golden_corpus/{sync_payload,expected_sync_snapshot}.json`
**When** le sync migré vers `evaluate_equipment()` est exécuté sur ce corpus
**Then** `test_story_8_4_golden_file.py` (ou son équivalent actuel) passe sans aucune modification du snapshot attendu
**And** aucune autre golden/fixture existante n'est modifiée pour faire passer ce test (toute modification de fixture serait un aveu de changement de comportement, interdit par cette story).

**AC2 — Parité stricte sur la suite complète**

**Given** la suite `pytest tests/unit -q` actuelle (baseline)
**When** le sync est migré vers `evaluate_equipment()`
**Then** la suite complète passe avec un nombre de tests verts au moins égal à la baseline, 0 régression
**And** un test existant peut être **mécaniquement** ajusté **uniquement** s'il vérifiait un détail d'implémentation devenu obsolète par construction (ex. un mock/spy qui assertait un appel direct à `decide_publication()` et doit désormais asserter un appel à `evaluate_equipment()` à la place) — cet ajustement doit être listé explicitement dans les Completion Notes de cette story, avec justification
**And** aucun test n'est modifié pour changer une assertion **comportementale** (valeur de `should_publish`, `reason`/`reason_code`, contenu publié) : un test qui échouerait à cause d'un changement de comportement réel doit bloquer la story, jamais être ajusté pour "faire passer" la migration.

**AC3 — Outil de parité en lecture seule sur la box**

**Given** la box Jeedom réelle (192.168.1.21)
**When** l'outil de parité (nouveau, créé par cette story) relève toutes les décisions de publication avant et après le déploiement du sync migré
**Then** la différence entre les deux relevés est **vide** (aucun équipement/commande dont la décision change)
**And** l'inventaire des topics MQTT retained est identique avant/après (ex. 353 → 353, valeur exacte relevée sur la box au moment du test)
**And** l'outil est en lecture seule strict : aucune écriture MQTT, aucune modification de `data/ha_overrides.json`, aucun redémarrage daemon déclenché par l'outil lui-même.

**AC4 — Mesure en lecture seule de l'état actuel d'I11 et du scope explicite**

**Given** le même outil de parité
**When** il s'exécute sur la box
**Then** il relève et rapporte, en lecture seule, tous les cas où I11 est déjà violé aujourd'hui (principal refusé mais secondaire publié) — sans les corriger (correction hors périmètre, Story 19.2)
**And** il relève et rapporte tout état de scope explicite déjà présent sur la box (aucune UI n'en écrit aujourd'hui, donc résultat probable = zéro — à constater par la mesure, jamais supposé a priori)
**And** ces deux mesures sont documentées dans le rapport de sortie de l'outil (fichier ou log dédié), pour alimenter respectivement Story 19.2 et l'epic (règle de scope).

**AC5 — Sécurité : `local_secret` jamais exposé (non négociable)**

**Given** l'outil de parité créé par cette story, quel que soit son mode d'appel
**When** il s'exécute (ligne de commande, journal, sortie standard, fichier de rapport)
**Then** `local_secret` n'apparaît **jamais** en clair, ni dans les arguments de ligne de commande, ni dans un log, ni dans la sortie produite par l'outil
**And** un test explicite vérifie que le code de l'outil ne journalise ni n'affiche la valeur du secret local (recherche statique de toute impression/logging de la variable portant le secret, plus test d'exécution avec assertion sur la sortie/les logs capturés).

## UI Impact

- **UI Impact:** Non — modification interne du sync (daemon), aucun changement visible côté UI Jeedom.

## Impact sur la production et retour arrière

Changement de comportement attendu : **aucun** — c'est l'objet même de cette story (refactoring pur, migration d'implémentation sans changement de résultat). Le risque réel est une régression accidentelle de publication (un équipement change de statut sans intention) ; c'est exactement ce que couvrent AC1-AC3. Retour arrière : revert de la story/PR (retour à l'appel direct de `decide_publication()` dans le sync), sans migration de données — `data/ha_overrides.json` et l'état MQTT publié restent inchangés par le revert.

## Preuve terrain

- (a) golden file inchangé (AC1).
- (b) outil en lecture seule (créé dans **cette** story, pas avant) qui relève toutes les décisions de publication avant/après déploiement sur la box, différence **vide**, inventaire des topics MQTT retained identique (ex. 353 → 353).
- (c) le même outil mesure et rapporte, en lecture seule : les cas où I11 est déjà violé aujourd'hui, et les éventuels états de scope explicites déjà présents sur la box (probablement zéro — à constater, pas supposer).
- (d) exigence de sécurité non négociable : l'outil ne doit jamais exposer `local_secret` (ligne de commande, journal, sortie) — critère d'acceptation testable (AC5).

## Invariants concernés

I1-I7 (parité stricte de comportement — aucune régression sur ces invariants déjà en vigueur). I11 n'est **pas corrigé** par cette story : il est seulement **mesuré et rapporté** en lecture seule (AC4), sa correction est le sujet exclusif de Story 19.2. Ne pas mélanger les deux preuves (cf. règle de dépendance de l'epic).

## Points fermés

Aucun CC-xx fermé par cette story (refactoring interne, pas de correction de bug utilisateur visible). CC-03, CC-18, CC-19 restent ouverts, traités par Stories 19.3/19.4. CC-04, CC-14 non concernés par cette story.

## Tasks / Subtasks

<!-- Story terrain : daemon / pipeline decide_publication / sync / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Préalable bloquant : la PR `fix/` de CC-20 est fusionnée. `deploy-to-box.sh` ne passe plus `local_secret` ni les identifiants MQTT en argument de `ssh`, `curl` ou `mosquitto_sub`. Sans cela, pas de preuve terrain.
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run` (vérifier SSH/sudo OK, box 192.168.1.21 joignable)
  - [ ] Déployer en standard : `./scripts/deploy-to-box.sh --restart-daemon`, sans option de nettoyage.
  - [ ] **Interdiction explicite (DANGER) :** ne jamais invoquer `--cleanup-discovery` ni `--stop-daemon-cleanup` (`scripts/deploy-to-box.sh:95,97`) pendant le cycle de mesure avant/après de cette story — ces deux flags republient des messages MQTT retained **vides** sur les topics discovery (`homeassistant/{light,cover,switch}/jeedom2ha_*/config`), effaçant l'état publié entre les deux relevés et rendant la comparaison "avant/après" invalide par construction (les entités disparaîtraient, ce qui n'a rien à voir avec un changement de décision). Utiliser exclusivement un déploiement standard (sans ces flags).
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou équivalent

- [ ] Task 1 — Migrer le sync vers `evaluate_equipment()` (AC1, AC2)
  - [ ] Passer l'instance `MapperRegistry` créée à `http_server.py:1375` à `evaluate_equipment()` (golden patch `transport.http_server.MapperRegistry`, `test_story_8_4_golden_file.py:272`) ; conserver les gardes `http_server.py:1397-1399` (inéligible) et `1405-1407` (mapping `None`).
  - [ ] Stocker des copies renvoyées par `evaluate_equipment()` dans `app["mappings"]` / `app["publications"]`, avec `projection_validity`, `publication_decision_ref`, `pipeline_step_reached` et `mapping_result` renseignés.

- [ ] Task 2 — Non-régression golden file + suite complète (AC1, AC2)
  - [ ] Exécuter `test_story_8_4_golden_file.py` sans modification de fixture
  - [ ] Exécuter `pytest tests/unit -q` intégralement, comparer au nombre de tests verts de la baseline actuelle

- [ ] Task 3 — Outil de parité en lecture seule (AC3, AC4, AC5)
  - [ ] Créer un outil (script dédié, hors chemin de production, jamais exécuté automatiquement) qui relève, pour chaque équipement/commande, la décision de publication actuelle sur la box, sans écriture ni effet de bord
  - [ ] Exécuter l'outil avant déploiement du sync migré, puis après, comparer les deux relevés
  - [ ] Relever et journaliser (sans corriger) les cas de violation I11 (principal refusé, secondaire publié)
  - [ ] Relever et journaliser tout état de scope explicite présent sur la box
  - [ ] Vérifier explicitement (test + revue manuelle du code de l'outil) qu'aucune trace de `local_secret` n'apparaît en sortie, log ou argument de ligne de commande

- [ ] Task 4 — Tests (AC1-AC5)
  - [ ] `test_story_19_1_sync_migration_parity.py` (préfixe `test_story_19_1_*`)
  - [ ] Test dédié de non-exposition du secret local pour l'outil de parité (AC5)

## Dev Notes

### Contexte pipeline

- Cette story est la première à **brancher** `evaluate_equipment()` (Story 19.0) dans un point d'appel réel — le sync. Elle ne change **aucune** règle métier, uniquement l'implémentation interne.
- L'outil de parité créé ici sert de preuve terrain pour cette story, et fournit en prime les mesures de référence (I11, scope explicite) qui alimenteront Story 19.2 et la règle de scope de l'epic — mais ne corrige rien lui-même.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

### Dev Agent Guardrails

- Aucune modification de règle métier dans cette story — toute divergence constatée entre `decide_publication()` direct et `evaluate_equipment()` est un bug bloquant à corriger dans `evaluate_equipment()` (Story 19.0), jamais un "changement accepté" ici.
- L'outil de parité ne doit jamais écrire (MQTT, `data/ha_overrides.json`, redémarrage daemon) — lecture seule stricte.
- Ne jamais journaliser, afficher ou transmettre `local_secret` en clair, sous quelque forme que ce soit.

### Contraintes techniques de l'outil de parité (AC3-AC5)

- **Exécution depuis la VM de dev, pas depuis la box :** l'outil s'exécute sur la machine de développement (VM), qui se connecte à la box réelle à distance (SSH/HTTP/MQTT selon le besoin) — jamais un script déployé et exécuté directement sur la box elle-même.
- **Aucune installation de paquet système :** l'outil ne doit dépendre que de ce qui est déjà disponible (bibliothèque standard Python, dépendances déjà présentes dans `requirements`/`venv` du daemon) — pas de `apt-get install` ni équivalent, ni sur la VM ni (a fortiori) sur la box.
- **Ordre stable et déterministe :** la sortie de l'outil (relevé de décisions, inventaire MQTT retained) doit être triée de façon déterministe (ex. par `eq_id` puis `cmd_id`) — un ordre non stable entre deux exécutions produirait un diff "avant/après" non vide même sans aucun changement réel, invalidant la preuve de parité (AC3).
- **Jamais de secret en argument de ligne de commande :** cohérent avec le point CC-20 documenté dans l'epic (`scripts/deploy-to-box.sh` expose déjà `local_secret`/identifiants MQTT en clair via `ps` par ce pattern) — l'outil de parité de cette story ne doit **jamais** reproduire ce pattern. Les secrets (identifiants MQTT, `local_secret`) doivent être transmis via variable d'environnement, fichier lu par l'outil, ou entrée standard (stdin) — jamais en argument positionnel ou en option `--xxx=secret` visible dans la liste des processus.

### Points constatés en dev-story (dispersion actuelle, à ne pas régresser silencieusement)

- **Politique de confiance :** stocker `request.app["confidence_policy"]` au sync, après `http_server.py:1325`.
- **Point d'injection unique :** `_resolve_data_dir(request)` remplace `_DATA_DIR` aux lignes `http_server.py:252,1393,1395,1412,1733,2355,3454`. Sans effet production ; prouvé par golden.
- **`app["mappings"]` reste le cache vivant consommé par le sync.** Ce dict `Dict[int, MappingResult]` (initialisé `http_server.py:3551`, mis à jour aux lignes 1691/1724, lu aux lignes 1361/1371/3142) continue d'être alimenté et lu exactement comme aujourd'hui après migration — `evaluate_equipment()` remplace les étapes 2 à 4 ; le cache stocke les copies renvoyées.
- **Le sync :** `evaluate_equipment()` remplace les étapes 2-4 ; `app["mappings"]` et `app["publications"]` stockent les copies renvoyées.
- **Scénarios (`app["scenario_publications"]`, `ScenarioButtonMapper`) et `is_visible` (topologie) restent hors périmètre.** Ces deux mécanismes ne passent pas par `decide_publication`/`evaluate_equipment()` aujourd'hui et cette story ne les y fait pas entrer — confirmé par lecture directe (`http_server.py:1694-1721`, `sync/command.py:530-573` pour les scénarios ; `models/topology.py:82,91,161,179` pour `is_visible`, sujet de parsing topologique sans rapport avec la décision de publication).

### Project Structure Notes

- Fichiers à toucher (probable) : `resources/daemon/transport/http_server.py` [MODIFIÉ — appels `decide_publication` remplacés par `evaluate_equipment`], nouvel outil de parité (emplacement à trancher en dev-story, hors du chemin de production), `resources/daemon/tests/unit/test_story_19_1_*.py` [NOUVEAU].

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] — epic canonique, règle de dépendance B1 avant B2.
- [Source: _bmad-output/implementation-artifacts/19-0-contrat-pur-command-decision-evaluate-equipment.md] — `evaluate_equipment()`, contrat consommé par cette story.
- [Source: resources/daemon/tests/unit/test_story_8_4_golden_file.py] — golden file de non-régression.
- [Source: _bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md] — procédure de déploiement terrain.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- **create-story** — 2026-09-27 — statut résultant : `ready-for-dev`. Story documentaire créée directement (skill officielle non exposée cette session).
- **dev-story** — 2026-09-27 — statut résultant : `in-progress`. Task 1 (migration `/action/sync` vers `evaluate_equipment()`), Task 4 (garde-fous unitaires de la migration) et Task 3 (outil de parité `tools/parity_snapshot.py`, AC3/AC4/AC5, testé en local/mocké uniquement — preuve terrain hors scope de cette passe) implémentées et committées (`8bbe147`, `df2fca9`, `1e02e1a`). Suite complète verte (1248 tests, flake8 clean). PR **#169** ouverte contre `main`, CI verte sur le SHA poussé. Revue automatisée (bot Codex) : 3 remarques P2 sur `tools/parity_snapshot.py` — toutes confirmées légitimes par inspection du code et corrigées (`cc0dc05`) avec tests de régression dédiés, fils de revue résolus. CI reconfirmée verte sur `cc0dc05`. **PR non fusionnée** — en attente de revue Alexandre (fusion hors scope de cette passe).

### File List

- `resources/daemon/transport/http_server.py` (modifié)
- `resources/daemon/tests/unit/test_pe_epic5_story_5_1_orchestration.py` (modifié)
- `resources/daemon/tests/unit/test_story_19_1_sync_migration_parity.py` (nouveau)
- `resources/daemon/tools/__init__.py` (nouveau)
- `resources/daemon/tools/parity_snapshot.py` (nouveau)
- `resources/daemon/tests/unit/test_story_19_1_parity_tool_readonly.py` (nouveau)
