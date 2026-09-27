# Story 19.1: Sync migré vers `evaluate_equipment()`, sans changement de comportement

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un mainteneur,
I want que le sync (`_do_handle_action_sync`) appelle `evaluate_equipment()` (Story 19.0) au lieu de recalculer sa propre décision via `decide_publication()` en direct, à comportement strictement identique,
so that le sync devienne le premier point d'appel unifié sur le contrat de décision, sans risquer de régression de publication en production.

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
**And** aucun test existant n'est modifié pour "faire passer" la migration (un test qui échouerait à cause d'un changement de comportement réel doit bloquer la story, pas être ajusté).

**AC3 — Outil de parité en lecture seule sur la box**

**Given** la box Jeedom réelle (192.168.1.21)
**When** l'outil de parité (nouveau, créé par cette story) relève toutes les décisions de publication avant et après le déploiement du sync migré
**Then** la différence entre les deux relevés est **vide** (aucun équipement/commande dont la décision change)
**And** l'inventaire des topics MQTT retained est identique avant/après (ex. 353 → 353, valeur exacte relevée sur la box au moment du test)
**And** l'outil est en lecture seule strict : aucune écriture MQTT, aucune modification de `data/ha_overrides.json`, aucun redémarrage daemon déclenché par l'outil lui-même.

**AC4 — Mesure en lecture seule de l'état actuel d'I8 et du scope explicite**

**Given** le même outil de parité
**When** il s'exécute sur la box
**Then** il relève et rapporte, en lecture seule, tous les cas où I8 est déjà violé aujourd'hui (principal refusé mais secondaire publié) — sans les corriger (correction hors périmètre, Story 19.2)
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
- (c) le même outil mesure et rapporte, en lecture seule : les cas où I8 est déjà violé aujourd'hui, et les éventuels états de scope explicites déjà présents sur la box (probablement zéro — à constater, pas supposer).
- (d) exigence de sécurité non négociable : l'outil ne doit jamais exposer `local_secret` (ligne de commande, journal, sortie) — critère d'acceptation testable (AC5).

## Invariants concernés

I1-I7 (parité stricte de comportement — aucune régression sur ces invariants déjà en vigueur). I8 n'est **pas corrigé** par cette story : il est seulement **mesuré et rapporté** en lecture seule (AC4), sa correction est le sujet exclusif de Story 19.2. Ne pas mélanger les deux preuves (cf. règle de dépendance de l'epic).

## Points fermés

Aucun CC-xx fermé par cette story (refactoring interne, pas de correction de bug utilisateur visible). CC-03, CC-18, CC-19 restent ouverts, traités par Stories 19.3/19.4. CC-04, CC-14 non concernés par cette story.

## Tasks / Subtasks

<!-- Story terrain : daemon / pipeline decide_publication / sync / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run` (vérifier SSH/sudo OK, box 192.168.1.21 joignable)
  - [ ] Sélectionner le mode de déploiement adapté à un cycle de mesure avant/après (à documenter en dev-story, cohérent avec le mode utilisé en Story 16.3/16.7)
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou équivalent

- [ ] Task 1 — Migrer le sync vers `evaluate_equipment()` (AC1, AC2)
  - [ ] Remplacer l'appel direct à `decide_publication()` dans `_do_handle_action_sync` (chemin primaire) et dans `_publish_additional_sensors()` (chemin secondaire) par un appel à `evaluate_equipment()` (Story 19.0), à comportement strictement identique
  - [ ] Vérifier que la résolution de l'éligibilité reste faite exactement comme aujourd'hui (une seule fois, en amont), et passée telle quelle à `evaluate_equipment()` (AC2 de Story 19.0)

- [ ] Task 2 — Non-régression golden file + suite complète (AC1, AC2)
  - [ ] Exécuter `test_story_8_4_golden_file.py` sans modification de fixture
  - [ ] Exécuter `pytest tests/unit -q` intégralement, comparer au nombre de tests verts de la baseline actuelle

- [ ] Task 3 — Outil de parité en lecture seule (AC3, AC4, AC5)
  - [ ] Créer un outil (script dédié, hors chemin de production, jamais exécuté automatiquement) qui relève, pour chaque équipement/commande, la décision de publication actuelle sur la box, sans écriture ni effet de bord
  - [ ] Exécuter l'outil avant déploiement du sync migré, puis après, comparer les deux relevés
  - [ ] Relever et journaliser (sans corriger) les cas de violation I8 (principal refusé, secondaire publié)
  - [ ] Relever et journaliser tout état de scope explicite présent sur la box
  - [ ] Vérifier explicitement (test + revue manuelle du code de l'outil) qu'aucune trace de `local_secret` n'apparaît en sortie, log ou argument de ligne de commande

- [ ] Task 4 — Tests (AC1-AC5)
  - [ ] `test_story_19_1_sync_migration_parity.py` (préfixe `test_story_19_1_*`)
  - [ ] Test dédié de non-exposition du secret local pour l'outil de parité (AC5)

## Dev Notes

### Contexte pipeline

- Cette story est la première à **brancher** `evaluate_equipment()` (Story 19.0) dans un point d'appel réel — le sync. Elle ne change **aucune** règle métier, uniquement l'implémentation interne.
- L'outil de parité créé ici sert de preuve terrain pour cette story, et fournit en prime les mesures de référence (I8, scope explicite) qui alimenteront Story 19.2 et la règle de scope de l'epic — mais ne corrige rien lui-même.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

### Dev Agent Guardrails

- Aucune modification de règle métier dans cette story — toute divergence constatée entre `decide_publication()` direct et `evaluate_equipment()` est un bug bloquant à corriger dans `evaluate_equipment()` (Story 19.0), jamais un "changement accepté" ici.
- L'outil de parité ne doit jamais écrire (MQTT, `data/ha_overrides.json`, redémarrage daemon) — lecture seule stricte.
- Ne jamais journaliser, afficher ou transmettre `local_secret` en clair, sous quelque forme que ce soit.

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

### File List
