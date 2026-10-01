# Story 20.0: Gate de preuve UX outillé

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un mainteneur,
I want un gate de preuve UX outillé (Playwright, compte Jeedom dédié, écritures interceptées) exécutable avant tout `done` d'interface,
so that les stories 20.1 et suivantes puissent prouver leurs parcours réels par clic sans risque d'écrire dans la maison, et sans dépendre à chaque fois d'un clic manuel long (le constat de la rétrospective pe-epic-19 sur 19-3/19-5/19-6/16-8).

**Parcours : complet.** Story bloquante, sans valeur utilisateur directe : aucune interface n'est modifiée par cette story.

## Acceptance Criteria

**AC1 — Playwright exécute un parcours contre l'UI Jeedom réelle, sans écriture non maîtrisée**

**Given** une page du plugin `jeedom2ha` ouverte via Playwright sur la VM openclaw, authentifiée avec le compte Jeedom dédié
**When** un parcours de lecture (navigation par pièce, ouverture d'un équipement, consultation du diagnostic) est exécuté
**Then** aucune requête AJAX d'écriture réelle vers Jeedom (`executeHaAction`, ou toute action qui modifierait l'état d'un équipement/scénario Jeedom) n'aboutit
**And** la liste des requêtes interceptées et leur verdict (bloquée / laissée passer) sont journalisées par le gate.

**AC2 — Liste blanche explicite pour les parcours d'override, avec restauration vérifiée**

**Given** un parcours de preuve qui pose ou purge un override de publication (`saveMappingOverride`, `revertMappingOverride`)
**When** le gate autorise ce parcours via sa liste blanche explicite
**Then** `data/ha_overrides.json` est lu avant le parcours (état de référence), le parcours s'exécute, puis `data/ha_overrides.json` est relu après restauration (purge de l'override posé) et comparé octet à octet à l'état de référence
**And** le gate échoue si l'état final diffère de l'état de référence.

**AC3 — Vérifications minimales avant tout `done` d'interface**

**Given** une story d'interface de l'epic 20 (20.1 et suivantes) arrivée à `ready-for-UX-validation`
**When** le gate 20.0 est exécuté sur cette story
**Then** il vérifie au minimum : zéro requête d'écriture non maîtrisée pendant tout le parcours (AC1), restauration vérifiée de `data/ha_overrides.json` pour les parcours d'override (AC2), absence d'erreur JavaScript console pendant le parcours, absence d'entrée `ERROR` dans les journaux du démon pendant la fenêtre du parcours
**And** le gate produit un rapport exploitable (liste des vérifications, verdict pass/fail par vérification) consommé par la story testée.

**AC4 — Lecture des identifiants hors dépôt, jamais journalisée**

**Given** un fichier d'identifiants du compte Jeedom dédié, déposé par Alexandre hors du dépôt, en permissions `600`
**When** le gate démarre un parcours Playwright
**Then** il lit ce fichier à l'exécution (jamais copié dans le dépôt, jamais écrit dans un journal ou une sortie de test)
**And** un test dédié vérifie qu'aucune valeur lue depuis ce fichier n'apparaît dans les journaux produits par le gate.

**AC5 — Gate bloquant, pas de `done` d'interface sans lui**

**Given** une story d'interface de l'epic 20
**When** sa Definition of Done est évaluée
**Then** le passage du gate 20.0 (AC1-AC4 verts) est une condition explicite de son `done`
**And** aucune story d'interface de l'epic 20 ne peut passer `ready-for-UX-validation` → `done` sans un rapport de gate vert joint.

## UI Impact

- **UI Impact :** Non — aucune interface livrée par cette story. Le gate observe et instrumente l'UI existante (16.8), il ne la modifie pas.

## Impact sur la production et retour arrière

Aucun impact sur la production : cette story ajoute un outillage de test (Playwright + scripts de gate), exécuté contre un compte Jeedom dédié non lié aux équipements réels de la maison, avec interception d'écriture. Aucun code de production (`desktop/`, `resources/daemon/`, `core/`) n'est modifié. Retour arrière : suppression de l'outillage de test ajouté, sans migration de données, sans impact sur `data/ha_overrides.json` ni sur l'état MQTT publié.

## Preuve terrain

Aucune preuve terrain au sens "déploiement sur la box" : cette story outille la preuve des stories suivantes, elle ne modifie rien de déployé. Sa propre preuve est l'exécution réussie du gate lui-même (AC1-AC5) sur un parcours de référence contre l'UI réelle via le compte dédié, journalisée dans un artefact de cette story.

## Task 0 — Pré-flight (bloquant, avant tout développement)

- [ ] **Compte Jeedom dédié disponible.** Alexandre crée et fournit un compte Jeedom dédié aux parcours de preuve (annoncé pour le 2026-10-01). Bloquant : aucune Task de cette story ne démarre sans ce compte.
- [ ] **Installation de Playwright et Chromium sur la VM openclaw actée.** Qui installe (Alexandre en pré-requis manuel, ou procédure documentée exécutée une fois par Alexandre) et où (chemin, utilisateur) : question ouverte posée à Alexandre dans `sprint-change-proposal-2026-10-01-etape-4-interface.md` (question 6). Bloquant : cette story ne peut pas installer de paquet elle-même (hors périmètre documentation), l'installation doit être actée et réalisée avant le dev de cette story.
- [ ] **Emplacement du fichier d'identifiants confirmé.** Chemin hors dépôt, permissions `600`, nom exact attendu par le gate : question ouverte posée à Alexandre (question 7 de la SCP). Bloquant pour AC4.
- [ ] **Vérifier l'existence du compte et du fichier d'identifiants avant de démarrer Task 1** (`ls -l` sur le chemin convenu, test de connexion), et consigner l'écart si l'un des deux manque encore.

## Vérifications minimales du gate (AC3)

1. Zéro requête AJAX d'écriture non maîtrisée vers Jeedom pendant tout le parcours (`executeHaAction` et toute action modifiant un équipement/scénario Jeedom, bloquées par défaut).
2. Pour un parcours d'override en liste blanche (`saveMappingOverride`, `revertMappingOverride`) : état de `data/ha_overrides.json` restauré à l'identique après le parcours (comparaison avant/après).
3. Absence d'erreur JavaScript dans la console du navigateur pendant le parcours.
4. Absence d'entrée `ERROR` dans les journaux du démon pendant la fenêtre temporelle du parcours.
5. Rapport du gate généré et lisible (verdict par vérification), joint à la story testée.

## Mécanisme d'interception des écritures

Le plugin `jeedom2ha` expose ses actions via `core/ajax/jeedom2ha.ajax.php`, dispatché par paramètre `action` (`scanTopology`, `getDiagnostics`, `executeHaAction`, `getMappingOverrides`, `previewMappingOverride`, `saveMappingOverride`, `revertMappingOverride`, entre autres). Le gate utilise l'interception réseau de Playwright (route-level) sur ces requêtes AJAX côté navigateur :
- toute requête `action=executeHaAction` (ou toute action identifiée comme modifiant un équipement/scénario Jeedom réel) est bloquée par défaut (AC1) ;
- les requêtes `action=saveMappingOverride` / `revertMappingOverride` sont laissées passer uniquement dans les parcours explicitement inscrits en liste blanche par le test (AC2), avec vérification avant/après de `data/ha_overrides.json` ;
- les requêtes de lecture (`scanTopology`, `getDiagnostics`, `getMappingOverrides`, `getPublishedScopeForConsole`) sont laissées passer sans restriction.
Le détail exact de la liste des actions à bloquer par défaut est à confirmer en Task 1, par lecture complète de `core/ajax/jeedom2ha.ajax.php` (dispatch des actions), avant tout premier parcours exécuté contre le compte dédié.

## Lecture des identifiants

Le fichier d'identifiants du compte Jeedom dédié est déposé par Alexandre hors du dépôt (chemin à confirmer, question 7 de la SCP), en permissions `600`. Le gate le lit à l'exécution via une variable d'environnement pointant vers ce chemin (jamais le contenu en dur dans un script versionné), ne l'écrit jamais dans un journal, une sortie de test ou un rapport, et échoue explicitement si le fichier est absent ou mal protégé (permissions différentes de `600`).

## Invariants concernés

Aucun invariant I1-I11 du pipeline n'est concerné : cette story est un outillage de test, sans branchement dans le pipeline de décision.

## Points fermés

Aucun CC-xx fermé par cette story : elle est le préalable outillé des stories qui ferment CC-25 (20.1) et CC-26 (20.2).

## Tasks / Subtasks

- [ ] Task 0 — Pré-flight (voir section dédiée ci-dessus) — bloquant
- [ ] Task 1 — Lire `core/ajax/jeedom2ha.ajax.php` en entier et lister exhaustivement les actions d'écriture réelle vers Jeedom à bloquer par défaut, vs. les actions de liste blanche override, vs. les actions de lecture (AC1, AC2)
- [ ] Task 2 — Mettre en place Playwright contre une page du plugin, authentification avec le compte dédié, lecture des identifiants depuis le chemin confirmé en Task 0 (AC4)
- [ ] Task 3 — Implémenter l'interception réseau (blocage par défaut des écritures, liste blanche explicite override) et le mécanisme de vérification avant/après de `data/ha_overrides.json` (AC1, AC2)
- [ ] Task 4 — Implémenter les vérifications minimales (console JS, journaux démon `ERROR`) et le rapport de gate (AC3)
- [ ] Task 5 — Exécuter un parcours de référence de bout en bout (navigation, ouverture équipement, pose puis purge d'un override) et consigner son résultat dans un artefact de cette story (preuve de la story elle-même)
- [ ] Task 6 — Documenter dans cette story comment une story suivante invoque le gate et où elle doit joindre son rapport avant `done` (AC5)

## Dev Notes

- Source : demande explicite d'Alexandre et constat de la rétrospective pe-epic-19 (`pe-epic-19-retro-2026-10-01.md`) sur le coût et la fragilité du clic réel manuel pour les stories UI (19-3, 19-5, 19-6, 16-8).
- Le choix exact des identifiants/chemins et de la procédure d'installation Playwright/Chromium reste bloqué sur une décision d'Alexandre (questions 6 et 7 de la SCP) — Task 0 ne peut pas avancer tant que ces points ne sont pas actés.
- Cette story n'ouvre aucun `PRODUCT_SCOPE`, n'ajoute aucun FR/NFR : c'est un outillage de test interne au dépôt.
