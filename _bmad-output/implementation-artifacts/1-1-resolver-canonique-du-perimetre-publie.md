# Story 1.1: Resolver canonique du périmètre publié

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur Jeedom avancé,  
je veux que le périmètre publié soit calculé par un resolver backend unique,  
afin que les décisions `global -> pièce -> équipement` soient prédictibles et explicables.

## Story Context

- Cycle actif obligatoire: **Post-MVP Phase 1 - V1.1 Pilotable**
- Dépendances autorisées: aucune
- Réduction de dette support: supprime les relectures manuelles de règles d'héritage contradictoires entre backend et UI
- Rappel de workflow: aucun agent ne doit deviner la source de vérité; la stratégie de test V1.1 fait partie des sources actives

## Acceptance Criteria

1. **AC1 - Résolution canonique et précédence stricte**  
   **Given** une configuration de périmètre contenant des règles `global`, `pièce` et `équipement`  
   **When** le backend calcule la décision effective d'un équipement  
   **Then** il applique strictement les états `inherit`, `include`, `exclude` avec précédence `équipement > pièce > global`

2. **AC2 - Exception équipement explicite**  
   **Given** un équipement explicitement inclus dans une pièce exclue  
   **When** la décision effective est calculée  
   **Then** la décision retournée est `include`  
   **And** la source de décision retournée est `exception_equipement`

3. **AC3 - Déterminisme du resolver et des compteurs**  
   **Given** une même configuration rejouée sur un même snapshot  
   **When** le resolver est exécuté plusieurs fois  
   **Then** il produit exactement les mêmes décisions et compteurs

## Tasks / Subtasks

- [x] Task 1 - Etendre le contrat d'entrée backend du périmètre publié sans calcul frontend (AC: 1, 2, 3)
  - [x] 1.1 Etendre `jeedom2ha::getFullTopology()` pour transporter les décisions brutes de périmètre aux trois niveaux `global / pièce / équipement`
  - [x] 1.2 Ajouter au payload backend un bloc canonique de scope permettant au moteur backend de distinguer l'état brut racine, l'état brut par pièce et l'état brut par équipement
  - [x] 1.3 Normaliser côté backend les seules valeurs autorisées `inherit / include / exclude`; toute valeur absente ou invalide doit être traitée de manière déterministe et testée
  - [x] 1.4 Garder PHP et JS en lecture seule sur cette logique: aucune décision effective, aucun compteur et aucune source de décision ne doivent être calculés côté frontend

- [x] Task 2 - Introduire un resolver backend unique, pur et déterministe (AC: 1, 2, 3)
  - [x] 2.1 Créer un module dédié sous `resources/daemon/models/` pour le modèle canonique du périmètre publié et la fonction pure de résolution
  - [x] 2.2 Calculer pour chaque équipement au minimum: `effective_state`, `decision_source`, `is_exception` et tout identifiant utile au résumé backend
  - [x] 2.3 Appliquer strictement la précédence `équipement > pièce > global` dans un seul point du backend
  - [x] 2.4 Retourner explicitement `decision_source = exception_equipement` lorsqu'un override équipement casse la règle héritée de sa pièce
  - [x] 2.5 Produire les compteurs globaux et par pièce depuis le même passage de résolution pour garantir un déterminisme strict

- [x] Task 3 - Exposer la sortie du resolver comme contrat backend réutilisable par la console V1.1 (AC: 1, 2, 3)
  - [x] 3.1 Persister en mémoire backend le résultat canonique du resolver au moment du sync, au même niveau d'autorité que `topology`, `eligibility`, `mappings` et `publications`
  - [x] 3.2 Rendre accessible côté backend, sans implémenter encore la vue UI, le minimum nécessaire pour les stories suivantes: `global.counts`, `global.has_pending_home_assistant_changes`, `piece.object_id`, `piece.object_name`, `piece.counts`, `piece.has_pending_home_assistant_changes`, `equipement.eq_id`, `equipement.effective_state`, `equipement.decision_source`, `equipement.is_exception`, `equipement.has_pending_home_assistant_changes`
  - [x] 3.3 Préparer le contrat de lecture pour Stories 1.2, 1.3 et 1.4 sans introduire de dépendance en avant: cette story doit fonctionner nominalement seule, et les stories suivantes consommeront ce contrat au lieu d'en recréer un

- [x] Task 4 - Protéger la compatibilité MVP et les invariants V1.1 déjà figés (AC: 1, 2, 3)
  - [x] 4.1 Garder la séparation entre décision locale de périmètre et application effective à Home Assistant: le resolver calcule un périmètre voulu, il ne déclenche pas ici d'opération destructive ou implicite côté HA
  - [x] 4.2 Ne pas faire des filtres techniques historiques (`excludedPlugins`, `excludedObjects`, `jeedom2ha_excluded`) la source de vérité V1.1; si une compatibilité est nécessaire, elle doit rester explicitement secondaire au modèle canonique `global -> pièce -> équipement`
  - [x] 4.3 Préserver les invariants sensibles déjà couverts par le socle existant: `unique_id` stable, recalcul déterministe, mapping/lifecycle/diagnostic/exclusions non régressifs hors périmètre explicite de la story
  - [x] 4.4 Ne supprimer aucun équipement du contrat backend simplement parce qu'il est hors périmètre voulu; la visibilité métier des exclus est une exigence d'epic et ne doit pas être rendue impossible par cette story

- [x] Task 5 - Ajouter la couverture de tests V1.1 obligatoire (AC: 1, 2, 3)
  - [x] 5.1 Ajouter des tests unitaires du resolver sur la matrice `global / pièce / équipement` x `inherit / include / exclude`
  - [x] 5.2 Ajouter des tests unitaires ciblant la précédence stricte et le cas `exception_equipement`
  - [x] 5.3 Ajouter un test de déterminisme: même snapshot + même configuration => mêmes décisions et mêmes compteurs sur plusieurs exécutions
  - [x] 5.4 Ajouter au moins un test d'intégration backend via `/action/sync` (ou le point d'entrée backend retenu) qui prouve que la résolution canonique est calculée côté backend puis réutilisable telle quelle, avec présence du mini contrat minimal `global / pièce / équipement`
  - [x] 5.5 Etendre les tests de non-régression déjà présents sur la topologie, les exclusions et le diagnostic pour vérifier que le resolver n'introduit ni duplicat de logique UI ni rupture des contrats MVP conservés

## Dev Notes

### Contexte actif et contraintes de cadrage

- Le cycle actif de référence est **Post-MVP Phase 1 - V1.1 Pilotable**
- Les seules sources de vérité de cette story sont:
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Aucun agent ne doit deviner la source de vérité
- La stratégie de test V1.1 est une source active, pas un contexte secondaire
- Ne pas rouvrir le cadrage produit, ne pas modifier les epics, ne pas réinterpréter les invariants déjà figés dans l'epic breakdown

### Invariants non renégociables a reprendre tels quels

- Le modèle canonique du périmètre publié reste `global -> pièce -> équipement`
- Les états supportés restent `inherit / include / exclude`
- La résolution suit explicitement `équipement > pièce > global`
- Le backend est l'unique source de calcul de la décision effective; aucun écran ne reconstruit sa logique d'héritage
- La décision locale de périmètre et l'application effective à Home Assistant restent deux concepts distincts
- Aucune story ne peut dépendre d'une story future pour fonctionner nominalement
- Chaque story doit porter explicitement une réduction de dette support, pas seulement une livraison technique
- Les frontières hors scope V1.1 restent gelées: pas d'extension fonctionnelle, pas de preview complète, pas de remédiation guidée avancée, pas de santé avancée, pas d'alignement Homebridge

### Dev Agent Guardrails

- Cette story crée le coeur de contrat stable de l'Epic 1; elle ne doit pas déborder sur les écrans complets de Story 1.2 ni sur les opérations HA explicites de l'Epic 4
- Le resolver doit être **pur**, **centralisé** et **testable**: pas de branche métier dupliquée entre PHP, JS, diagnostics et pipeline de sync
- Le contrat backend produit ici doit être le seul consommé plus tard par la console; les stories 1.2, 1.3 et 1.4 doivent lire ce contrat, pas le recalculer
- Le flux actuel `scanTopology -> /action/sync` constitue l'ancrage naturel de la résolution backend; si un autre point d'entrée est introduit, il doit réutiliser exactement la même fonction de résolution
- Les exclusions historiques du plugin ne doivent pas devenir le "modèle principal de lecture" de V1.1; elles peuvent servir de compatibilité transitoire mais pas de source canonique pour la console pilotable
- Ne pas introduire de fallback produit implicite en absence de configuration V1.1 explicite; si une compatibilité technique transitoire est nécessaire, elle doit être traitée comme hypothèse de dev à valider, jamais comme invariant du cycle actif
- L'implémentation doit préparer la lisibilité future des exclus et des exceptions locales; ne pas jeter les équipements hors périmètre hors du contrat backend
- Aucun calcul de décision effective, d'agrégat ou de compteurs ne doit apparaître dans `desktop/js/jeedom2ha.js`

### Mini contrat backend minimal du resolver

Sans figer ici un schéma complet de console, la sortie backend minimale attendue de Story 1.1 doit exposer un contrat lisible par Stories 1.2, 1.3 et 1.4 sans recalcul métier frontend.

- Niveau `global`
  - `counts`: agrégats déterministes issus du resolver pour la synthèse globale
  - `has_pending_home_assistant_changes`: booléen backend indiquant si des changements locaux restent en attente d'application HA
- Niveau `piece`
  - `object_id`: identifiant stable de la pièce / objet Jeedom
  - `object_name`: libellé de la pièce / objet Jeedom
  - `counts`: agrégats déterministes de la pièce issus du resolver
  - `has_pending_home_assistant_changes`: booléen backend pour la portée pièce
- Niveau `equipement`
  - `eq_id`: identifiant stable de l'équipement Jeedom
  - `effective_state`: décision effective résolue pour l'équipement
  - `decision_source`: code backend stable indiquant l'origine de la décision effective; il doit permettre au minimum de distinguer héritage depuis le global, héritage depuis la pièce, règle équipement explicite et `exception_equipement`
  - `is_exception`: booléen backend permettant à l'UI d'indiquer une exception locale sans recalcul métier
  - `has_pending_home_assistant_changes`: booléen backend pour la portée équipement

Notes de contrat:

- L'imbrication exacte du payload peut rester ouverte à ce stade (`equipements` sous `pieces` ou structure plate), mais ces champs minimaux ne doivent pas être réinventés par le frontend
- Story 1.2 consommera `counts`, Story 1.3 consommera `effective_state` et `decision_source`, Story 1.4 consommera `has_pending_home_assistant_changes`
- Ce mini contrat est un garde-fou d'implémentation pour `dev-story`; il ne remplace pas les invariants du cycle actif et n'élargit pas le scope produit

### Implementation Notes

- Le socle existant montre déjà un pipeline backend centralisé:
  - extraction Jeedom côté PHP avec `jeedom2ha::getFullTopology()`
  - normalisation backend via `TopologySnapshot.from_jeedom_payload()`
  - orchestration de sync dans `resources/daemon/transport/http_server.py`
- Recommandation d'implémentation: garder `resources/daemon/models/topology.py` focalisé sur la normalisation brute et introduire un module dédié de résolution canonique sous `resources/daemon/models/`
- Les sources actives ne justifient aucun fallback produit par défaut en absence de configuration V1.1 explicite; ne pas déduire une règle canonique depuis le comportement historique du code existant
- Si un fallback de compatibilité technique s'avère nécessaire à l'implémentation pour préserver un comportement existant, le traiter comme hypothèse à valider en dev et à couvrir par tests, sans l'ériger en invariant ni en source de vérité du cycle actif
- Les compteurs globaux et par pièce doivent venir du même calcul canonique que les décisions effectives pour éviter tout drift entre résumé et détail
- Le résultat du resolver doit être stocké dans l'état backend pour être relu tel quel par les stories suivantes; ne pas recomposer ce résultat depuis `eligibility`, `mappings` ou `publications`

### Dependencies and Sequencing

- Dépendances autorisées: aucune
- Dépendances en avant: interdites
- Cette story fournit ensuite le contrat de base consommé par:
  - Story 1.2 pour les synthèses backend lues par l'UI
  - Story 1.3 pour les exceptions équipement et la visibilité continue des exclus
  - Story 1.4 pour rendre visibles les changements locaux en attente d'application HA
  - Story 3.1 et Story 4.1 qui réutiliseront le coeur de périmètre stable au lieu de redéfinir la portée

### Project Structure Notes

- Points d'ancrage probables:
  - `core/class/jeedom2ha.class.php`
  - `core/ajax/jeedom2ha.ajax.php`
  - `resources/daemon/models/topology.py`
  - `resources/daemon/transport/http_server.py`
  - `tests/unit/test_topology.py`
  - `resources/daemon/tests/unit/test_exclusion_filtering.py`
  - `resources/daemon/tests/unit/test_diagnostic_endpoint.py`
  - `tests/test_php_topology_extraction.php`
- Fichiers probablement a creer:
  - `resources/daemon/models/published_scope.py` (ou nom équivalent clairement dédié au resolver canonique)
  - suites de tests dédiées au resolver et à son contrat backend
- Fichiers a ne pas charger de logique métier V1.1:
  - `desktop/php/jeedom2ha.php`
  - `desktop/js/jeedom2ha.js`

### Risks / Points de vigilance

- Transformer la vue par pièce en unique vue de vérité au lieu d'un point d'entrée principal
- Recalculer l'héritage dans le frontend ou dans plusieurs couches backend concurrentes
- Confondre décision locale de périmètre et effet immédiat côté Home Assistant
- Conserver les exclusions techniques historiques comme modèle principal au lieu du contrat canonique V1.1
- Produire des compteurs via un autre code path que la résolution canonique
- Rendre impossible la visibilité future des exclus en supprimant trop tôt les équipements hors périmètre du contrat backend

### Testing Requirements

- Invariants V1.1 explicitement touchés par cette story:
  - modèle canonique `global -> pièce -> équipement`
  - états `inherit / include / exclude`
  - précédence `équipement > pièce > global`
  - séparation scope local vs application effective HA
  - recalcul déterministe pour un snapshot et une configuration donnés
- Tests unitaires obligatoires:
  - matrice complète de résolution `global / pièce / équipement`
  - cas limites d'override équipement sur pièce exclue
  - décision source `global`, `pièce`, `équipement`, `exception_equipement`
  - déterminisme des décisions et des compteurs
- Tests d'intégration backend obligatoires:
  - calcul du resolver au moment du sync
  - disponibilité du contrat backend canonique après sync, avec présence des champs minimaux `global / pièce / équipement`
  - absence de recalcul parallèle côté UI/PHP template
- Tests de contrat / non-régression obligatoires:
  - stabilité du mini contrat renvoyé aux futures stories de console
  - non-régression des suites MVP conservées sur topologie, exclusions, lifecycle, diagnostic, `unique_id`
  - preuve que tout éventuel fallback de compatibilité technique reste explicitement testé et n'est pas promu en vérité produit implicite
- Tests UI:
  - non requis dans cette story tant que le travail reste sur le contrat backend et non sur la vue

### References

- Sources actives de vérité:
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Points d'ancrage codebase utilises comme contexte d'implémentation secondaire:
  - `core/class/jeedom2ha.class.php` (`getFullTopology`)
  - `resources/daemon/models/topology.py`
  - `resources/daemon/transport/http_server.py` (`_handle_action_sync`)
  - `tests/unit/test_topology.py`
  - `resources/daemon/tests/unit/test_exclusion_filtering.py`
  - `tests/test_php_topology_extraction.php`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `python3 -m pytest tests/unit/test_published_scope.py tests/unit/test_published_scope_http.py tests/unit/test_topology.py tests/unit/test_http_server.py resources/daemon/tests/unit/test_exclusion_filtering.py resources/daemon/tests/unit/test_diagnostic_endpoint.py -q` (127 passed, warnings `DeprecationWarning` aiohttp déjà connus)
- `command -v php` retourne vide (`exit 1`) dans cet environnement
- `php -l core/class/jeedom2ha.class.php` impossible dans cet environnement (`php: command not found`)
- `php tests/test_php_topology_extraction.php` impossible dans cet environnement (`php: command not found`)

### Completion Notes List

- Resolver canonique backend implémenté dans `resources/daemon/models/published_scope.py` avec précédence stricte `equipement > piece > global`, état `exception_equipement`, compteurs globaux/pièces et déterminisme.
- Contrat d'entrée étendu dans `jeedom2ha::getFullTopology()` via bloc `published_scope` brut (`global`, `pieces`, `equipements`) sans calcul métier frontend/PHP.
- Contrat backend persistant branché sur `/action/sync` (`app["published_scope"]`) et exposé via `/system/published_scope` pour consommation future sans recalcul UI.
- Compatibilité technique traitée comme hypothèse backend testée: fallback legacy `exclusion_source=eqlogic/object/plugin` appliqué uniquement si scope canonique explicite absent, pour éviter tout drift contrat `published_scope` vs pipeline d'éligibilité.
- Test de contrat PHP étendu (`tests/test_php_topology_extraction.php`) pour vérifier la présence du bloc `published_scope` et des clés racines minimales `global / pieces / equipements` sans déplacer de logique métier.
- Vérification de non-régression exécutée sur topologie, sync HTTP, exclusions et diagnostic; fichiers UI `desktop/js/jeedom2ha.js` et `desktop/php/jeedom2ha.php` non modifiés.

### File List

- `_bmad-output/implementation-artifacts/1-1-resolver-canonique-du-perimetre-publie.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `core/class/jeedom2ha.class.php`
- `resources/daemon/models/published_scope.py`
- `resources/daemon/transport/http_server.py`
- `tests/test_php_topology_extraction.php`
- `tests/unit/test_published_scope.py`
- `tests/unit/test_published_scope_http.py`

### Change Log

- 2026-03-22: Implémentation complète Story 1.1 (contrat d'entrée `published_scope`, resolver canonique backend, persistance mémoire au sync, endpoint backend dédié, tests unitaires + intégration + non-régression).
- 2026-03-22: Code review BMAD IA — verdict `changes requested`; story repassée `in-progress` tant que le fallback legacy `excludedPlugins` n'est pas reflété ou explicitement écarté du contrat canonique.
- 2026-03-22: Correction suite code review — fallback legacy plugin (`exclusion_source=plugin`) aligné et testé dans le resolver, test PHP de contrat `published_scope` ajouté, story remise en `review`.
- 2026-03-22: Code review BMAD IA — re-review après correction approuvé; P1 legacy plugin fermé, couverture PHP minimale `published_scope` confirmée, story passée `done`.

## Senior Developer Review (AI)

### Reviewer

GPT-5 Codex

### Date

2026-03-22 14:33:01 CET

### Verdict

changes requested

### Findings

- [high] Le fallback legacy du resolver ne couvre que `exclusion_source=eqlogic/object` alors que `getFullTopology()` continue de produire des exclusions historiques via `excludedPlugins`. En l'absence de scope V1.1 explicite, un équipement exclu par plugin reste `excluded_plugin` pour l'éligibilité backend mais le contrat canonique le résout encore en `effective_state=include` / `decision_source=global`, ce qui casse la promesse d'un contrat backend minimal fiable et réutilisable pour la console. Preuves: `core/class/jeedom2ha.class.php` (priorité plugin toujours active), `resources/daemon/models/published_scope.py` (fallback absent pour `plugin`), reproduction revue avec un snapshot `exclusion_source='plugin'`.

### Review Tests

- `python3 -m pytest tests/unit/test_published_scope.py tests/unit/test_published_scope_http.py tests/unit/test_topology.py tests/unit/test_http_server.py resources/daemon/tests/unit/test_exclusion_filtering.py resources/daemon/tests/unit/test_diagnostic_endpoint.py -q` (125 passed, warnings `DeprecationWarning` aiohttp déjà connus sur les mutations `request.app[...]`)
- `command -v php` -> binaire absent dans cet environnement; `php -l core/class/jeedom2ha.class.php` non vérifiable localement

### Re-review Date

2026-03-22 14:53:22 CET

### Re-review Verdict

approved

### Re-review Findings

- Aucun finding bloquant sur cette passe.
- Le P1 précédent est **fermé**: le fallback legacy `exclusion_source=plugin` est maintenant reflété par le resolver canonique uniquement comme compatibilité technique secondaire, sans promotion en vérité produit V1.1.
- La couverture de test PHP minimale est **présente**: `tests/test_php_topology_extraction.php` vérifie désormais la présence du bloc `published_scope` et des clés racines `global / pieces / equipements`.
- AC1, AC2 et AC3 sont couverts par le resolver et sa suite de tests dédiés; aucune logique métier n'a été ajoutée à l'UI.

### Re-review Tests

- `python3 -m pytest tests/unit/test_published_scope.py tests/unit/test_published_scope_http.py tests/unit/test_topology.py tests/unit/test_http_server.py resources/daemon/tests/unit/test_exclusion_filtering.py resources/daemon/tests/unit/test_diagnostic_endpoint.py -q` (127 passed, warnings `DeprecationWarning` aiohttp déjà connus sur les mutations `request.app[...]`)
- `command -v php` -> binaire absent dans cet environnement; `php -l core/class/jeedom2ha.class.php` et `php tests/test_php_topology_extraction.php` non vérifiables localement
