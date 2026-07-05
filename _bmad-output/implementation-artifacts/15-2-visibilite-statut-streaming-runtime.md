# Story 15.2: Visibilité statut du state streaming runtime

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a mainteneur jeedom2ha effectuant un diagnostic terrain,
I want voir directement dans la console (panneau de diagnostic équipement + vue globale) si une commande matched (sensor/binary_sensor/switch) est effectivement streamée en runtime (`StateSynchronizer`, capacité livrée en epic 12) plutôt que de devoir interroger `GET /system/state_listeners` à la main,
so that je peux confirmer sans CLI/MQTT qu'un équipement Jeedom → HA reflète bien un état temps réel, et repérer immédiatement un équipement matched qui n'est PAS encore streamé (ex. discovery pas encore confirmée).

## Acceptance Criteria

1. Pour chaque commande matched d'un équipement, quand ce couple `(eq_id, cmd_id)` est présent dans `StateSynchronizer.list_state_targets()` (i.e. réellement streamé : type vague 1/2, discovery confirmée, topic déclaré), la console affiche un badge "Streaming actif" (réutilisant le pattern visuel du badge Energy de la Story 15.1), sans nécessiter de requête manuelle à `/system/state_listeners`.
2. Aucun badge "Streaming actif" n'est affiché pour une commande absente de `list_state_targets()` — aucun état intermédiaire ("en attente", "en échec") n'est inventé : `StateSynchronizer` ne persiste aujourd'hui aucun statut d'échec ou d'attente par entité (cf. Dev Notes, limite connue), donc afficher un tel état serait une donnée fabriquée. Seul un booléen "actuellement streamé oui/non" est honnête avec les données disponibles.
3. La console affiche une vue globale (au niveau du résumé/summary) : `streaming_actif` (reflet de `StateSynchronizer.is_active`) et `streaming_cibles_count` (nombre total de couples `(eq_id, cmd_id)` actuellement dans `list_state_targets()`), pour une visibilité terrain de la capacité livrée en epic 12 sans avoir à cliquer équipement par équipement.
4. Aucune régression sur l'affichage existant (badges Energy, typage Jeedom, commandes observées/non-mappées, contrat 4D) : le nouvel affichage est strictement additif.
5. Aucune modification de comportement de streaming, mapping, validation ou publication : `resources/daemon/sync/state.py` (`StateSynchronizer`) et `resources/daemon/mapping/*` ne changent pas de logique métier. Le endpoint `/system/diagnostics` (`_handle_system_diagnostics`) lit uniquement `state_sync.list_state_targets()` et `state_sync.is_active`, déjà disponibles au runtime (aucun nouveau calcul, aucune nouvelle persistance).
6. Tests unitaires daemon (payload diagnostic : présence/absence du badge selon `list_state_targets()`, présence des champs `streaming_actif`/`streaming_cibles_count` dans le summary) et JS (`buildEquipmentModel`/présentateur, rendu badge) couvrant : cas streamé, cas non streamé (matched mais absent de `list_state_targets()`), non-régression des champs existants (notamment badge Energy 15.1 qui doit continuer de s'afficher indépendamment).
7. Gate terrain sur box réelle (192.168.1.21) : au moins un équipement sensor/binary_sensor (vague 1) ou switch avec readback (vague 2, ex. `ENERGY_STATE`/`PRESENCE`) visible avec son badge "Streaming actif" dans la console après sync, et le compteur global `streaming_cibles_count` cohérent avec le nombre d'entrées retournées par `GET /system/state_listeners` sur la même box au même instant.

## Tasks / Subtasks

<!-- Story terrain (daemon / MQTT / discovery HA / runtime / bootstrap / restart daemon /
     X-Local-Secret / /system/status / /action/sync / box réelle / test terrain) :
     la Task 0 Pre-flight terrain est injectée automatiquement par create-story en tête de cette section.
     Supprimer ce commentaire si non applicable. -->

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.`

- [x] Task 1 — Étendre le payload `/system/diagnostics` par commande (AC: #1, #2, #5)
  - [x] Dans `resources/daemon/transport/http_server.py`, `_handle_system_diagnostics` (~L2004+, boucle `matched_commands` ~L2071-2087), lire `request.app.get("state_synchronizer")` une fois par requête et construire un `set` `(eq_id, cmd_id)` à partir de `state_sync.list_state_targets()` (appelé une seule fois hors boucle équipements, pas par équipement — coût O(n) une fois).
  - [x] Pour chaque entrée de `matched_commands`, ajouter `"streaming": true` uniquement si `(eq_id, c.id)` est dans ce set ; ne pas ajouter la clé du tout sinon (pas de `false` explicite — cohérence avec le pattern "absent = non applicable" de la Story 15.1).
  - [x] Ne toucher à aucune autre logique de `_handle_system_diagnostics` ni à `resources/daemon/sync/state.py` (lecture seule des méthodes publiques déjà existantes `list_state_targets()`/`is_active`).

- [x] Task 2 — Étendre le `summary` global (AC: #3, #5)
  - [x] Dans `resources/daemon/transport/http_server.py`, après construction de `summary = build_summary(equipments)` (~L2251), ajouté `summary["streaming_actif"] = bool(state_sync.is_active) if state_sync is not None else False` et `summary["streaming_cibles_count"] = len(streaming_targets)` (réutilise le set construit en Task 1, pas de second appel à `list_state_targets()`).
  - [x] `build_summary()` (fonction existante) non modifiée — l'ajout se fait après l'appel, comme déjà fait pour `summary["compteurs"]` et `summary["home_statut"]` (~L2252-2253).

- [x] Task 3 — Étendre le modèle console côté JS (AC: #1, #3, #4)
  - [x] Dans `desktop/js/jeedom2ha_scope_summary.js`, `readCommandCoverage()` (~L45-73), ajouté le passthrough additif de la clé `streaming` (booléen, présente uniquement si `true`, même pattern que `state_class`/`unit_of_measurement` de la Story 15.1).
  - [x] Ajouté le passthrough de `diagSummary.streaming_actif` / `diagSummary.streaming_cibles_count` dans `createModel()` (~L355-370), exposés sous `model.global.streaming_actif`/`model.global.streaming_cibles_count`, en réutilisant les helpers existants `readBoolean`/`readCount`.
  - [x] **Déviation découverte et corrigée (hors hypothèse initiale de la story)** : contrairement à la note "Project Structure Notes" ci-dessous qui supposait que `desktop/php/jeedom2ha.php` relaie le JSON tel quel, le vrai pont PHP est `core/ajax/jeedom2ha.ajax.php` (`getPublishedScopeForConsole`, action réellement consommée par `createModel()`), et il applique un **allowlist strict** via `_jeedom2ha_extract_commands()` qui ne transmettait ni `state_class`/`unit_of_measurement` (Story 15.1, jamais câblé côté PHP) ni `streaming`. Sans correction, le passthrough JS ci-dessus n'aurait jamais reçu de donnée réelle depuis la vraie console (uniquement testable en isolation JS). Corrigé en étendant `_jeedom2ha_extract_commands()` (`core/ajax/jeedom2ha.ajax.php` ~L18-40) pour transmettre `state_class`/`unit_of_measurement`/`streaming` de façon additive (clé absente si non fournie par le daemon, jamais de valeur inventée) — corequis nécessaire pour que AC#1/#3 soient honorés de bout en bout, pas un élargissement de scope.

- [x] Task 4 — Rendu console (AC: #1, #3, #4)
  - [x] Dans `desktop/js/jeedom2ha.js`, section "Typage Jeedom" (`buildDetailRow`, ~L923-966), à côté du badge Energy existant, ajouté un badge "Streaming actif" (même style visuel monospace, couleur verte distincte) affiché uniquement quand `mcEntry.streaming === true` pour la commande correspondante, via un index `streamingByCmdId` construit une seule fois aux côtés de `energyByCmdId` (pas de nouveau parcours de `eq.matched_commands`).
  - [x] Ajouté l'affichage de `streaming_actif`/`streaming_cibles_count` sur la ligne "Parc global" du tableau `render()` (`desktop/js/jeedom2ha_scope_summary.js`, nouveau helper `renderGlobalStreamingBadge()`, badge injecté dans la cellule Nom via un paramètre additif `extraBadgeHtml` de `renderNameCell()` — signature rétrocompatible, aucun autre appelant impacté, colonnes du contrat 4D inchangées).
  - [x] Aucun placeholder affiché quand `streaming`/`streaming_actif` est absent ou faux (badge conditionnel strict).

- [x] Task 5 — Tests (AC: #6)
  - [x] Daemon : `resources/daemon/tests/unit/test_story_15_2_diagnostic_streaming_visibility.py` — cas commande dans `list_state_targets()` (badge présent), cas commande matched mais absente (badge absent), cas `state_synchronizer` absent de `app` (pas de crash, `streaming_actif=False`), présence de `streaming_actif`/`streaming_cibles_count` dans `summary`, non-régression badge Energy (15.1) sur le même payload. 5/5 passent.
  - [x] JS : étendu `tests/unit/test_scope_summary_presenter.node.test.js` (passthrough `streaming` par commande + `streaming_actif`/`streaming_cibles_count` globaux, cas présent/absent) + nouveau `tests/unit/test_story_15_2_streaming_badge_console.node.test.js` (index `streamingByCmdId`, badge conditionnel, rendu badge global `render()`, non-régression Section 2/Energy). 12+5 tests passent.
  - [x] Suite complète daemon (`pytest`) : 963 passed. Suite JS complète (`node --test tests/unit/*.node.test.js`) : 218 passed. Golden-file `expected_sync_snapshot.json` régénéré (`GOLDEN_REGEN=1`) : diff strictement additif (`streaming_actif`, `streaming_cibles_count`).

- [x] Task 6 — Gate terrain (AC: #7)
  - [x] Après `--cleanup-discovery --restart-daemon` sur la box réelle (192.168.1.21), interrogé `GET /system/diagnostics` et `GET /system/state_listeners` (même `X-Local-Secret`) au même instant : `summary.streaming_actif = true`, `summary.streaming_cibles_count = 196`, `/system/state_listeners` renvoie exactement 196 entrées (correspondance stricte). 49 `matched_commands` portent `"streaming": true` (ex. eq_id=587, cmd_id=5515 "Batterie").
  - [x] Vérification additionnelle via exécution directe du pont PHP (`jeedom2ha::getPublishedScopeForConsole()` + `_jeedom2ha_extract_commands()` in situ sur la box) : mêmes valeurs `streaming_actif`/`streaming_cibles_count`/49 commandes streaming confirmées côté PHP (pas seulement côté daemon brut) — valide que le correctif allowlist (Task 3) fonctionne réellement dans le chemin console, pas seulement en isolation JS/pytest.
  - [x] Non-régression confirmée sur données réelles : le badge Energy (Story 15.1, `state_class`) était **silencieusement bloqué par l'allowlist PHP avant cette story** (0 commande n'en bénéficiait jamais côté console malgré 6 commandes porteuses côté daemon) — désormais transmis correctement (6 commandes avec `state_class` visibles côté PHP), confirmant que le correctif Task 3 corrige aussi une régression latente non détectée de la Story 15.1, en plus d'activer 15.2.

## Dev Notes

- Cette story est un exercice de **lecture seule / exposition**, exactement dans l'esprit de la Story 15.1 et des gates epic-level de l'epic 15 (`epics-projection-engine.md`) : ne jamais réouvrir le mapping/validation/publication des epics 12/13/14. `resources/daemon/sync/state.py` n'est lu qu'via ses méthodes publiques déjà existantes (`list_state_targets()`, `is_active`), jamais modifié.
- **Limite connue à ne pas masquer (documentée explicitement, pas de donnée inventée)** : `StateSynchronizer` (Story 12.1/12.2) ne persiste aujourd'hui **aucun** statut d'échec ou d'attente par entité — `handle_state_message()` (`sync/state.py` ~L90-135) journalise un `reason_code` (`mqtt_publish_failed`, `state_target_not_found`, etc.) via `_log()` mais ne le stocke nulle part de requêtable. Le texte de l'epic 15 mentionne "publié / en attente / en échec", mais seul l'état "publié" (présence dans `list_state_targets()`) est honnêtement dérivable des données en mémoire actuelles. Introduire un tracking d'échec/attente persistant nécessiterait de modifier `sync/state.py` (epic 12), ce qui est explicitement hors gate epic 15 (lecture seule, pas de réouverture epics 12/13/14) — à traiter dans un futur epic dédié si le besoin terrain se confirme.
- `StateSynchronizer.list_state_targets()` (`sync/state.py` ~L137-183) est déjà l'source autoritative utilisée par le endpoint existant `GET /system/state_listeners` (`http_server.py::_handle_system_state_listeners`, ~L2300-2322) — cette story ne crée aucune nouvelle logique de résolution, elle réutilise exactement la même méthode pour l'exposer aussi dans `/system/diagnostics` (évite un aller-retour manuel entre deux endpoints pour le diagnostic terrain).
- Payload diagnostic actuel (`_handle_system_diagnostics`) transporte déjà `state_class`/`unit_of_measurement` par commande (Story 15.1) — cette story étend le même point d'extension (`matched_commands` entries) avec `streaming`, en suivant rigoureusement le même pattern additif (clé absente si non applicable, jamais de `null`/`false` explicite bruyant).
- Rendu console existant pour les commandes : `desktop/js/jeedom2ha.js` ~L906-976 (badges inline monospace, badge Energy Story 15.1 ~L952-957) — réutiliser ce pattern visuel plutôt qu'en créer un nouveau.
- Types réellement streamés aujourd'hui (`sync/state.py` ~L31-35) : `sensor`, `binary_sensor` (vague 1, Story 12.1) + `switch` avec readback `ENERGY_STATE`/`SWITCH_STATE`/`PRESENCE` (vague 2, Story 12.2). `button`, `light`, `cover` ne sont jamais dans `list_state_targets()` — c'est un comportement attendu (pas un bug), à ne pas "corriger" dans cette story.

### Dev Agent Guardrails

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- Backend : `resources/daemon/transport/http_server.py` (`_handle_system_diagnostics`), lit `resources/daemon/sync/state.py` (`StateSynchronizer.list_state_targets`, `.is_active`) comme source de vérité, exactement comme `_handle_system_state_listeners` (~L2300-2322) le fait déjà pour un endpoint séparé.
- Frontend : `desktop/js/jeedom2ha_scope_summary.js` (modèle, `readCommandCoverage`/lecture du summary) et `desktop/js/jeedom2ha.js` (rendu DOM, `buildDetailRow`). `desktop/php/jeedom2ha.php` ne fait que relayer le JSON du daemon, aucun changement PHP attendu a priori.
- Aucun changement attendu dans `resources/daemon/sync/state.py` (lu uniquement comme source de vérité via ses méthodes publiques existantes).

### References

- [Source: resources/daemon/sync/state.py#StateSynchronizer.list_state_targets (~L137-183), #is_active (~L69-78), #handle_state_message (~L90-135)]
- [Source: resources/daemon/transport/http_server.py#_handle_system_diagnostics (~L2004+), #_handle_system_state_listeners (~L2300-2322)]
- [Source: desktop/js/jeedom2ha_scope_summary.js#readCommandCoverage (~L45-67)]
- [Source: desktop/js/jeedom2ha.js#buildDetailRow (~L869-976, badge Energy Story 15.1 ~L952-957)]
- [Source: resources/daemon/tests/unit/test_story_15_1_diagnostic_energy_visibility.py — pattern de test diagnostic]
- [Source: tests/unit/test_scope_summary_presenter.node.test.js — pattern de test JS du présentateur]
- [Source: _bmad-output/implementation-artifacts/15-1-visibilite-energy-state-class-console.md — story précédente de l'epic, même discipline lecture seule]
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic 15 — Story 15.2 et gates epic-level]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-05-epic-visibilite-console.md]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-cli/claude-sonnet-5)

### Debug Log References

### Completion Notes List

- Lecture seule stricte de `StateSynchronizer` respectée : aucune modification de `resources/daemon/sync/state.py`, uniquement lecture de `list_state_targets()`/`is_active` via `request.app.get("state_synchronizer")` dans `_handle_system_diagnostics`.
- Déviation majeure découverte et corrigée en cours de Task 3 : la note "Project Structure Notes" de la story supposait à tort que `desktop/php/jeedom2ha.php` relaie le JSON tel quel — le vrai pont consommé par la console (`createModel()`) est `core/ajax/jeedom2ha.ajax.php::getPublishedScopeForConsole` avec un allowlist strict `_jeedom2ha_extract_commands()`. Cet allowlist ne transmettait ni `state_class`/`unit_of_measurement` (Story 15.1, jamais câblé côté PHP malgré le passthrough JS déjà écrit) ni `streaming` (15.2). Étendu de façon additive (clé absente si non fournie, jamais de valeur inventée) : corequis nécessaire pour honorer AC#1/#3, et corrige au passage une régression latente et non détectée de la Story 15.1 (badge Energy jamais visible côté console réelle malgré tests JS/pytest verts en isolation).
- Gate terrain (box 192.168.1.21) : validé à la fois côté daemon brut (`/system/diagnostics`, `/system/state_listeners`) ET côté pont PHP réel (exécution directe de `getPublishedScopeForConsole()` + `_jeedom2ha_extract_commands()` sur la box) — `streaming_actif=true`, `streaming_cibles_count=196` == nombre d'entrées `/system/state_listeners`, 49 commandes `streaming:true`, 6 commandes `state_class` (Energy 15.1) désormais visibles côté PHP.
- Golden-file `expected_sync_snapshot.json` régénéré (`GOLDEN_REGEN=1`) : diff strictement additif (2 clés `streaming_actif`/`streaming_cibles_count`).
- Suites complètes exécutées : daemon `pytest` 963 passed ; JS `node --test tests/unit/*.node.test.js` 218 passed. PHP : pas d'interpréteur `php` disponible dans cet environnement d'exécution pour lancer `tests/unit/test_story_5_1_php_relay.php` localement — la correction PHP a été vérifiée fonctionnellement en conditions réelles sur la box (ci-dessus), ce qui couvre le comportement à l'exécution, mais le test PHP dédié n'a pas pu être rejoué ici faute de runtime PHP local.

### File List

- `resources/daemon/transport/http_server.py` (modifié — `_handle_system_diagnostics` : lecture `state_synchronizer`, champ `streaming` par commande, `streaming_actif`/`streaming_cibles_count` dans `summary`)
- `resources/daemon/tests/unit/test_story_15_2_diagnostic_streaming_visibility.py` (nouveau)
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json` (régénéré, additif)
- `core/ajax/jeedom2ha.ajax.php` (modifié — `_jeedom2ha_extract_commands()` : passthrough additif `state_class`/`unit_of_measurement`/`streaming`)
- `desktop/js/jeedom2ha_scope_summary.js` (modifié — `readCommandCoverage()` : passthrough `streaming` ; `createModel()` : `streaming_actif`/`streaming_cibles_count` globaux ; `renderNameCell()`/`render()` : badge global additif via nouveau helper `renderGlobalStreamingBadge()`)
- `desktop/js/jeedom2ha.js` (modifié — `buildDetailRow` : index `streamingByCmdId`, badge "Streaming actif" par commande)
- `tests/unit/test_scope_summary_presenter.node.test.js` (étendu — passthrough `streaming` par commande + `streaming_actif`/`streaming_cibles_count` globaux)
- `tests/unit/test_story_15_2_streaming_badge_console.node.test.js` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié — statut story)

## Senior Developer Review (AI)

### Reviewer

Alexandre (via clawcode, agent BMAD `code-review`), 2026-07-05

### Outcome

**Approve** — aucun finding HIGH/MEDIUM/LOW. Toutes les ACs implémentées et vérifiées.

### Method

- Story rechargée intégralement depuis le fichier (pas de mémoire de session).
- Découverte git fraîche : `git status --porcelain`, `git diff --name-only`, `git diff --cached --name-only` — la liste des fichiers modifiés/ajoutés correspond exactement au File List de la story (7 fichiers modifiés + 3 nouveaux, y compris la story elle-même).
- Chaque diff réel (`git diff`) lu et confronté au texte des Tasks/Completion Notes, fichier par fichier.
- Tests rejoués en direct dans cette session (pas de confiance aveugle au chiffre annoncé) :
  - JS : `node --test tests/unit/*.node.test.js` → **218 passed** (correspond exactement à la story).
  - Daemon : `python3 -m pytest -q` (racine `resources/daemon`) → **963 passed** (correspond exactement à la story).
  - Ciblé : `node --test` sur les 3 fichiers 15.1/15.2 → **20 passed** (helpers `readBoolean`/`readCount`/`isFiniteNumber` confirmés existants et utilisés correctement).

### AC-by-AC

1. **IMPLEMENTED** — badge "Streaming actif" par commande, conditionné à la présence dans `streamingByCmdId` (`jeedom2ha.js` ~L964-966), lui-même dérivé de `state_sync.list_state_targets()` côté backend (`http_server.py` ~L2030-2036, ~L2097-2098).
2. **IMPLEMENTED** — clé `streaming` absente (jamais `false` explicite) quand la commande n'est pas dans `list_state_targets()` ; confirmé par test daemon dédié (`test_matched_command_omits_streaming_when_not_in_state_targets`) et test JS (`streaming absent`).
3. **IMPLEMENTED** — `summary["streaming_actif"]`/`summary["streaming_cibles_count"]` ajoutés après `build_summary()` (`http_server.py` ~L2254-2256), passthrough JS confirmé (`createModel`), badge global confirmé (`renderGlobalStreamingBadge`).
4. **IMPLEMENTED** — non-régression vérifiée : badge Energy (15.1), Section 2 Typage Jeedom, contrat 4D colonnes toutes intactes (tests dédiés + lecture diff : `renderNameCell` garde un paramètre additif rétrocompatible, aucun autre appelant touché).
5. **IMPLEMENTED** — `resources/daemon/sync/state.py` **non modifié** (absent du `git diff --name-only`), lecture strictement via `list_state_targets()`/`is_active` déjà publics.
6. **IMPLEMENTED** — couverture daemon (5 tests dédiés, cas streamé/non-streamé/sans state_synchronizer/summary/non-régression Energy) + JS (4 tests dans le presenter + 5 tests dédiés badge console) — tous rejoués et verts dans cette session.
7. **IMPLEMENTED** — gate terrain documenté avec double vérification (endpoint brut + exécution directe du pont PHP réel sur la box), `streaming_cibles_count=196` == nombre d'entrées `/system/state_listeners`, cohérence stricte confirmée dans la story.

### Findings

Aucun finding HIGH, MEDIUM ou LOW.

### Notes complémentaires (hors gate, positif)

- La déviation Task 3 (allowlist PHP `_jeedom2ha_extract_commands()`) est un vrai bug de régression latente sur la Story 15.1, correctement identifié, corrigé de façon additive, et documenté avec transparence dans les Completion Notes plutôt que dissimulé — exactement l'esprit "toujours réévaluer l'alignement UI/daemon" du gate epic-level pe-epic-15.
- Le correctif PHP bénéficie aussi à `_jeedom2ha_build_export_equipment()` (export diagnostic), un second call-site non explicitement visé par les ACs mais couvert gratuitement par le passthrough additif dans la fonction partagée — cohérent avec le principe additif, aucun risque de régression identifié sur ce second chemin (il n'ajoute que des clés optionnelles).
- Aucun problème de sécurité : tous les champs PHP nouvellement transmis passent par un cast typé (`(string)`, `(bool)`) avant d'entrer dans le JSON de réponse, pas d'échappement HTML à faire à ce niveau (fait côté JS au rendu, `escapeHtml` déjà utilisé ailleurs dans le fichier pour les labels).
