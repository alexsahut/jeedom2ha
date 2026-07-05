# Story 15.3: Visibilité parité FAN_* -> switch en console

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a mainteneur jeedom2ha effectuant un diagnostic terrain,
I want voir directement dans la console (panneau de diagnostic équipement + vue globale) quand un équipement a été rattaché à la famille `switch` via le fallback générique FAN (`FAN_STATE`/`FAN_ON`/`FAN_OFF`, Story 14.1) plutôt que via la famille `SWITCH` standard,
so that je peux repérer immédiatement, sans consulter les logs daemon ni interroger la base Jeedom, un cas similaire à eq67 (pompe filtration piscine, plugin `pool`) découvert uniquement en gate terrain lors de l'epic 14.

## Acceptance Criteria

1. Pour chaque équipement mappé `switch` dont le trio de commandes provient de la famille `FAN` (`FAN_STATE`/`FAN_ON`/`FAN_OFF`, `MappingResult.reason_code == "switch_fan_on_off_state"`, `resources/daemon/mapping/switch.py` — que le groupement soit obtenu par nom partagé ou par le fallback single-trio-per-family de la Story 14.1), la console affiche un badge "Parité FAN → switch" au niveau de l'équipement (même pattern visuel que les badges Energy/Streaming des Stories 15.1/15.2).
2. Aucun badge n'est affiché pour un équipement mappé `switch` via la famille `SWITCH` standard (`reason_code == "switch_switch_on_off_state"`) ni pour tout autre type d'équipement (sensor, binary_sensor, light, etc.) — pas de valeur inventée, badge strictement conditionné à la détection FAN.
3. **Piège technique identifié (à ne pas reproduire)** : le champ `reason_code` déjà exposé au niveau équipement dans `/system/diagnostics` (`_handle_system_diagnostics`) est **écrasé** par `pub_decision.reason` (valeur de confiance, ex. `"probable"`/`"sure"`) dès que l'équipement est `active_or_alive` (`http_server.py` ~L2074-2076) — c'est le cas normal pour un switch FAN correctement publié (ex. eq67 en fonctionnement). Le marqueur de famille FAN n'est donc **jamais fiable** en lisant `eq.reason_code` une fois l'équipement publié : un **nouveau champ dédié** doit être ajouté, capturé depuis `map_result.reason_code` (disponible avant l'écrasement, ~L2065), et exposé de façon additive (absent si non applicable, jamais de `false` explicite — même discipline que le badge Energy/Streaming).
4. Aucune régression sur l'affichage existant (badges Energy 15.1, Streaming 15.2, typage Jeedom, commandes observées/non-mappées, contrat 4D, résumé global) : le nouvel affichage est strictement additif.
5. Aucune modification de comportement de mapping, validation ou publication : `resources/daemon/mapping/switch.py` (`SwitchMapper._group_switch_cmds`, logique FAN/SWITCH de la Story 14.1) ne change pas de logique métier — lecture seule de `MappingResult.reason_code` déjà calculé.
6. Tests unitaires daemon (présence du nouveau champ quand `reason_code` mapping vaut `switch_fan_on_off_state`, absence pour `switch_switch_on_off_state` et pour les autres types d'équipement, non-régression du contrat existant) et JS (badge affiché/absent selon le champ, non-régression Section 2 Typage Jeedom + badges Energy/Streaming + vue "Parc global").
7. Gate terrain sur box réelle (192.168.1.21) : l'équipement eq67/cmd382 (pompe filtration piscine, plugin `pool`, cf. Story 14.1) apparaît dans la console avec le badge "Parité FAN → switch", et un équipement `switch` de la famille standard (ex. eq583/eq628, cf. Story 14.1) n'affiche pas ce badge.

## Tasks / Subtasks

<!-- Story terrain (daemon / MQTT / discovery HA / runtime / bootstrap / restart daemon /
     X-Local-Secret / /system/status / /action/sync / box réelle / test terrain) :
     la Task 0 Pre-flight terrain est injectée automatiquement par create-story en tête de cette section.
     Supprimer ce commentaire si non applicable. -->

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.`

- [x] Task 1 — Étendre le payload `/system/diagnostics` au niveau équipement (AC: #1, #2, #3, #5)
  - [x] Dans `resources/daemon/transport/http_server.py`, `_handle_system_diagnostics`, dans la branche où `map_result` est disponible (~L2064-2065, juste après `reason_code = map_result.reason_code`, **avant** l'écrasement conditionnel par `pub_decision.reason` ~L2074-2076), capturer `family_reason_code = map_result.reason_code` dans une variable locale distincte de `reason_code` (qui continue de servir sa fonction actuelle inchangée).
  - [x] Dans la construction de `eq_dict` (~L2220-2246), ajouter `eq_dict["fan_switch_parity"] = True` uniquement si `family_reason_code == "switch_fan_on_off_state"` — ne pas ajouter la clé du tout sinon (pas de `false` explicite, même pattern additif que `matched_commands[].streaming` de la Story 15.2).
  - [x] Ne toucher à aucune autre logique de `_handle_system_diagnostics`, ni à `resources/daemon/mapping/switch.py` (lecture seule de `MappingResult.reason_code` déjà calculé par `SwitchMapper._group_switch_cmds`/`decide_publication`).

- [x] Task 2 — Étendre le pont PHP `getPublishedScopeForConsole` (AC: #1, #4)
  - [x] Dans `core/ajax/jeedom2ha.ajax.php`, action `getPublishedScopeForConsole` (~L462-480), le bloc qui construit `$eqDiag[$eqId]` whiteliste explicitement chaque champ équipement (`statut`, `reason_code`, `status_code`, etc.) — ajouter `'fan_switch_parity' => array_key_exists('fan_switch_parity', $eq) ? (bool)$eq['fan_switch_parity'] : null` (ou pattern équivalent additif : absent/`null` côté PHP si absent côté daemon, jamais `false` inventé).
  - [x] L'action `getDiagnostics` (~L445-451) est un relais brut (`ajax::success($result)` direct sur la réponse daemon, sans allowlist) — **aucun changement PHP requis pour ce chemin**, le nouveau champ y sera déjà présent nativement dès Task 1. Documenter cette distinction dans les Completion Notes pour éviter de refaire l'archéologie de la Story 15.2.

- [x] Task 3 — Étendre le modèle console "Parc global" (`jeedom2ha_scope_summary.js`) (AC: #1, #4)
  - [x] Dans `desktop/js/jeedom2ha_scope_summary.js`, le builder du modèle équipement (bloc qui lit `diag.reason_code`/`diag.status_code`/etc., ~L230-250) ajouter `fan_switch_parity: readBoolean(diag.fan_switch_parity, false)` (réutilise le helper `readBoolean` existant, même pattern que `streaming_actif` de la Story 15.2).
  - [x] Dans `render()`, pour les lignes de niveau `equipement`, passer un badge additif via le paramètre `extraBadgeHtml` de `renderNameCell()` (déjà ajouté en Story 15.2, actuellement utilisé uniquement pour la ligne globale) — créer un helper `renderFanParityBadge(fanSwitchParity)` sur le même modèle que `renderGlobalStreamingBadge()`, retournant `''` si `fanSwitchParity !== true`.
  - [x] Vérifier qu'aucun autre appelant de `renderNameCell()` (pièce, global) n'est impacté — le badge FAN ne doit apparaître que sur les lignes équipement.

- [x] Task 4 — Rendu console détaillée (`jeedom2ha.js`, `buildDetailRow`) (AC: #1, #4)
  - [x] Dans `desktop/js/jeedom2ha.js`, section où `eq.name`/`reasonDescription` sont affichés pour chaque ligne équipement (~L1149-1158, table `getDiagnostics`), ajouter un badge inline "Parité FAN → switch" (même style visuel monospace que les badges Energy/Streaming, couleur distincte) affiché uniquement quand `eq.fan_switch_parity === true` — lecture directe de `eq.fan_switch_parity` (disponible nativement, `getDiagnostics` étant un relais brut non filtré, cf. Task 2).
  - [x] Aucun placeholder affiché quand `fan_switch_parity` est absent ou faux (badge conditionnel strict, cohérent avec les Stories 15.1/15.2).

- [x] Task 5 — Tests (AC: #6)
  - [x] Daemon : nouveau fichier `resources/daemon/tests/unit/test_story_15_3_diagnostic_fan_switch_parity.py` — cas équipement switch famille FAN (badge/champ présent), cas équipement switch famille SWITCH standard (absent), cas équipement non-switch (sensor, absent), cas équipement FAN mais `active_or_alive=False` (non publié — vérifier que le nouveau champ reste correct indépendamment de l'écrasement de `reason_code`), non-régression des champs `state_class`/`streaming` (Stories 15.1/15.2) sur le même payload.
  - [x] JS : étendre `tests/unit/test_scope_summary_presenter.node.test.js` (passthrough `fan_switch_parity` présent/absent) + nouveau `tests/unit/test_story_15_3_fan_parity_badge_console.node.test.js` (badge conditionnel dans `jeedom2ha.js`, rendu badge équipement dans `render()` de `jeedom2ha_scope_summary.js`, non-régression Section 2/Energy/Streaming).
  - [x] Suite complète daemon (`pytest`) et suite JS complète (`node --test tests/unit/*.node.test.js`) : 0 régression. Golden-file `expected_sync_snapshot.json` régénéré (`GOLDEN_REGEN=1`) si le nouveau champ apparaît dans le corpus (vérifier si un eqLogic du golden corpus a une famille FAN — sinon diff golden-file attendu vide).

- [x] Task 6 — Gate terrain (AC: #7)
  - [x] Après `--cleanup-discovery --restart-daemon` sur la box réelle (192.168.1.21), interroger `GET /system/diagnostics` (`X-Local-Secret`) : confirmer que l'équipement eq67 (cmd382, "Filtration") porte `"fan_switch_parity": true`, et qu'un équipement switch de la famille standard (ex. eq583/eq628, cf. Story 14.1 Change Log) ne porte pas cette clé.
  - [x] Vérification additionnelle via exécution directe du pont PHP (`getPublishedScopeForConsole()` in situ sur la box, même méthode que la Story 15.2) : confirmer que `fan_switch_parity` atteint bien le JSON retourné par ce chemin également (valide le correctif allowlist Task 2).
  - [x] Non-régression confirmée sur les badges Energy (15.1) et Streaming (15.2) pour les mêmes équipements sur la box.

## Dev Notes

- Cette story est un exercice de **lecture seule / exposition**, dans l'esprit des Stories 15.1/15.2 et des gates epic-level de l'epic 15 (`epics-projection-engine.md`) : ne jamais réouvrir le mapping/validation/publication des epics 12/13/14. `resources/daemon/mapping/switch.py` n'est lu que via `MappingResult.reason_code` déjà calculé, jamais modifié.
- **Piège déjà identifié (voir AC#3)** — contrairement aux Stories 15.1/15.2 où le principal risque architectural était le pont PHP, ici le risque principal est **backend** : le champ `eq_dict["reason_code"]` existant est réutilisé pour deux sémantiques différentes selon l'état de publication (`map_result.reason_code` si non publié, `pub_decision.reason` — une simple confiance — si publié, `http_server.py` ~L2060-2076). Un équipement FAN publié avec succès (le cas nominal, ex. eq67 en fonctionnement) aura donc `eq.reason_code == "probable"` ou `"sure"`, PAS `"switch_fan_on_off_state"` — lire directement `eq.reason_code` côté console donnerait un résultat **faux la plupart du temps**. D'où la nécessité du nouveau champ dédié capturé avant l'écrasement.
- **Bonne nouvelle découverte en amont (gain de temps vs. Story 15.2)** : contrairement au champ `matched_commands[].streaming`, l'action `getDiagnostics` (relais brut, `core/ajax/jeedom2ha.ajax.php` ~L445-451) ne filtre **aucun** champ équipement — `ajax::success($result)` retourne le JSON daemon tel quel. Seule l'action `getPublishedScopeForConsole` (utilisée par la vue "Parc global") passe par un allowlist explicite (`$eqDiag[$eqId] = [...]`, ~L462-480) qui whiteliste déjà `reason_code`/`statut`/`status_code`/etc. champ par champ — il faudra y ajouter `fan_switch_parity` explicitement (Task 2), mais ce n'est pas une découverte de bug caché comme en 15.2 : c'est un ajout de champ prévu dès la conception de cette story (conforme au gate epic-level pe-epic-15 : "si une story nécessite d'ajouter un champ au payload diagnostic daemon... cadré explicitement lors de create-story").
- `SwitchMapper._group_switch_cmds` (`switch.py` ~L322-364) construit le `reason_code` de la forme `f"switch_{family.lower()}_on_off_state"` où `family` vaut `"SWITCH"` ou `"FAN"` (`_SWITCH_CMD_FAMILIES`, ~L61) — donc `"switch_fan_on_off_state"` (famille FAN) vs `"switch_switch_on_off_state"` (famille SWITCH standard). Ce marqueur est identique que le groupement soit résolu par nom partagé ou par le fallback single-trio-per-family ajouté en gate terrain de la Story 14.1 (`switch.py` ~L340-361) — les deux chemins produisent le même `reason_code`, donc le nouveau champ couvre les deux cas sans distinction supplémentaire nécessaire.
- Rendu console existant pour les badges : `desktop/js/jeedom2ha.js` ~L906-976 (badges inline monospace, Energy ~L952-957, Streaming ~L964-966) — réutiliser ce pattern visuel. Pour la vue "Parc global" (`jeedom2ha_scope_summary.js`), le paramètre `extraBadgeHtml` de `renderNameCell()` (ajouté en Story 15.2, ~L397/415-418) est déjà générique et rétrocompatible — il suffit de l'utiliser aussi pour les lignes équipement, pas seulement la ligne globale.
- eq67 (plugin `pool`, cmd382 "Filtration", noms hétérogènes ON="Actif"/OFF="Auto") est le cas terrain de référence documenté en Story 14.1 (`_bmad-output/implementation-artifacts/14-1-fan-state-on-off-generalisation-switch-family.md`, section "Gate terrain — résultat") — toujours présent et fonctionnel sur la box réelle au 2026-07-05 (confirmé actif dans les gates terrain des Stories 15.1/15.2, aucune raison de penser qu'il aurait disparu).

### Dev Agent Guardrails

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- Backend : `resources/daemon/transport/http_server.py` (`_handle_system_diagnostics`), lit `MappingResult.reason_code` (déjà calculé par `resources/daemon/mapping/switch.py::SwitchMapper`) comme source de vérité, sans y toucher.
- Pont PHP : `core/ajax/jeedom2ha.ajax.php` — deux actions distinctes consomment `/system/diagnostics` : `getDiagnostics` (relais brut, aucun filtre) et `getPublishedScopeForConsole` (allowlist explicite par champ, à étendre en Task 2). Ne pas confondre les deux chemins (piège rencontré en Story 15.2).
- Frontend : `desktop/js/jeedom2ha_scope_summary.js` (modèle "Parc global") et `desktop/js/jeedom2ha.js` (rendu détaillé `buildDetailRow`, table `getDiagnostics`). `desktop/php/jeedom2ha.php` ne fait que relayer, aucun changement PHP attendu là.
- Aucun changement attendu dans `resources/daemon/mapping/switch.py` ni `resources/daemon/mapping/binary_sensor.py` (lus uniquement comme source de vérité via `MappingResult.reason_code`).

### References

- [Source: resources/daemon/mapping/switch.py#_SWITCH_CMD_FAMILIES (~L61), #_group_switch_cmds (~L322-364), #decide_publication (~L388-413)]
- [Source: resources/daemon/transport/http_server.py#_handle_system_diagnostics (~L2004+, écrasement reason_code ~L2060-2076, construction eq_dict ~L2220-2246)]
- [Source: core/ajax/jeedom2ha.ajax.php#getDiagnostics (~L445-451, relais brut), #getPublishedScopeForConsole (~L453-480, allowlist équipement)]
- [Source: desktop/js/jeedom2ha_scope_summary.js#createModel (modèle équipement ~L230-250), #renderNameCell (~L397, extraBadgeHtml ajouté Story 15.2)]
- [Source: desktop/js/jeedom2ha.js#buildDetailRow (~L869-976, table getDiagnostics ~L1149-1167)]
- [Source: resources/daemon/tests/unit/test_story_14_1_*.py — assertions `reason_code == "switch_fan_on_off_state"`]
- [Source: _bmad-output/implementation-artifacts/14-1-fan-state-on-off-generalisation-switch-family.md — cas terrain eq67, fallback single-trio-per-family]
- [Source: _bmad-output/implementation-artifacts/15-2-visibilite-statut-streaming-runtime.md — story précédente de l'epic, même discipline lecture seule, pattern extraBadgeHtml/readBoolean]
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic 15 — Story 15.3 et gates epic-level]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-cli/claude-sonnet-5)

### Debug Log References

### Completion Notes List

- **dev-story exécuté le 2026-07-05** — implémentation complète, statut résultant : `review`.
- Task 1 : capture de `family_reason_code = map_result.reason_code` juste après l'assignation initiale de `reason_code` (avant l'écrasement conditionnel par `pub_decision.reason`), variable initialisée à `None` en tête de boucle pour rester correcte même hors branche `map_result`. `eq_dict["fan_switch_parity"] = True` ajouté de façon strictement additive (clé absente sinon), aucune autre logique touchée.
- Task 2 : confirmé en amont (create-story) — `getDiagnostics` est un relais brut, aucun changement PHP requis pour ce chemin. Seul `getPublishedScopeForConsole` (`$eqDiag[$eqId]`) nécessitait l'ajout de l'allowlist `fan_switch_parity` (pattern additif : `null` si absent côté daemon, jamais `false` inventé).
- Task 3/4 : badge "Parité FAN → switch" ajouté en réutilisant les patterns existants — `renderFanParityBadge()` (calqué sur `renderGlobalStreamingBadge()`) branché via le paramètre `extraBadgeHtml` de `renderNameCell()` pour la vue "Parc global" (ligne équipement uniquement), et badge inline dans `jeedom2ha.js` à côté de `eq.name` pour la console détaillée (`getDiagnostics`, relais brut).
- Task 5 : 5 nouveaux tests daemon (dont le cas `active_or_alive=False` qui a révélé que `reason_code` est aussi réécrit — par `canonical_dec.reason` — dans la branche non publiée ; le test a été ajusté pour vérifier que `fan_switch_parity` reste correct indépendamment de cette seconde réécriture, renforçant la validité de l'AC#3). 2 tests ajoutés à `test_scope_summary_presenter.node.test.js` + 4 nouveaux tests dans `test_story_15_3_fan_parity_badge_console.node.test.js`. Suite complète : **968 tests daemon** (pytest) et **224 tests JS** (node --test) tous verts, 0 régression. Golden-file `expected_sync_snapshot.json` non impacté (le builder de ce test ne passe pas par `_handle_system_diagnostics`) — aucune régénération nécessaire.
- Task 6 : gate terrain box réelle (192.168.1.21) après `--cleanup-discovery --restart-daemon` : `GET /system/diagnostics` confirme `eq67` (cmd382 "Filtration") avec `fan_switch_parity: true` et `reason_code: "probable"` (confirmation en production du piège AC#3 — la clé de confiance a bien écrasé le marqueur de famille, le nouveau champ dédié est donc indispensable) ; `eq583`/`eq628` (switch famille standard) sans la clé (`has("fan_switch_parity") == false`), 8 équipements au total exposent le badge sur le corpus réel. Vérification additionnelle via exécution directe de `getPublishedScopeForConsole()` in situ (réplique du merge PHP de `jeedom2ha.ajax.php`) : `fan_switch_parity: true` pour eq67, absent pour eq583/eq628 — valide le correctif allowlist Task 2. Non-régression confirmée : `streaming_actif: true` / `streaming_cibles_count: 196`, cmd382 porte `streaming: true`, et 6 équipements du corpus réel portent toujours `state_class` (badge Energy 15.1 intact).

### File List

- `resources/daemon/transport/http_server.py`
- `core/ajax/jeedom2ha.ajax.php`
- `desktop/js/jeedom2ha_scope_summary.js`
- `desktop/js/jeedom2ha.js`
- `resources/daemon/tests/unit/test_story_15_3_diagnostic_fan_switch_parity.py` (nouveau)
- `tests/unit/test_scope_summary_presenter.node.test.js`
- `tests/unit/test_story_15_3_fan_parity_badge_console.node.test.js` (nouveau)

### Change Log

- 2026-07-05 : Implémentation Story 15.3 — exposition additive de `fan_switch_parity` (backend, pont PHP, console détaillée, vue "Parc global"), 9 nouveaux tests unitaires (5 daemon + 4 JS) + 2 tests étendus, gate terrain box réelle validé (eq67 vs eq583/eq628, non-régression Energy/Streaming).
- 2026-07-05 : Code review (AI) — Approve. Statut passé à `done`.

## Senior Developer Review (AI)

### Reviewer

Claude Sonnet 5 (claude-cli/claude-sonnet-5), 2026-07-05

### Outcome

**Approve** — aucun finding HIGH ou MEDIUM. Story conforme aux 7 AC, tests réels et suffisants, aucune régression, discipline lecture seule respectée.

### Git vs Story File List

`git status --porcelain` / `git diff --name-only` recoupés avec la section File List : **correspondance exacte**, 0 écart.
- Modifiés (trackés) : `resources/daemon/transport/http_server.py`, `core/ajax/jeedom2ha.ajax.php`, `desktop/js/jeedom2ha_scope_summary.js`, `desktop/js/jeedom2ha.js`, `tests/unit/test_scope_summary_presenter.node.test.js`, `_bmad-output/implementation-artifacts/sprint-status.yaml` (artefact de tracking, hors File List — normal).
- Nouveaux (untracked) : `resources/daemon/tests/unit/test_story_15_3_diagnostic_fan_switch_parity.py`, `tests/unit/test_story_15_3_fan_parity_badge_console.node.test.js`.
- Aucun fichier `_bmad-output`/`.claude` inclus dans le périmètre de revue de code (exclus conformément aux règles du workflow).

### AC-by-AC

1. **IMPLEMENTED** — `http_server.py` capture `family_reason_code = map_result.reason_code` juste après l'assignation initiale de `reason_code` (avant toute réécriture), puis ajoute `eq_dict["fan_switch_parity"] = True` uniquement quand `family_reason_code == "switch_fan_on_off_state"` (diff L2050-2253). Badge rendu côté `jeedom2ha_scope_summary.js` (`renderFanParityBadge`, branché via `extraBadgeHtml` sur la ligne équipement) et `jeedom2ha.js` (badge inline conditionné à `eq.fan_switch_parity === true`). Couvert par `test_fan_family_switch_gets_parity_badge_when_published` et les tests JS de rendu.
2. **IMPLEMENTED** — clé absente (pas de `false`) pour `switch_switch_on_off_state` et pour tout équipement non-switch, vérifié par `test_standard_family_switch_has_no_parity_badge`, `test_non_switch_equipment_has_no_parity_badge`, et côté JS `doesNotMatch(html, /Parité FAN/)`.
3. **IMPLEMENTED** — le piège documenté est réellement au rendez-vous : `test_fan_family_switch_gets_parity_badge_even_when_not_published` prouve que `reason_code` est réécrit (`"ambiguous"`, cas non publié) alors que `fan_switch_parity` reste correct car capturé dans une variable dédiée, non affectée par les deux chemins de réécriture (`pub_decision.reason` et `canonical_dec.reason`). Confirmé aussi en gate terrain réel (`eq.reason_code == "probable"` sur eq67 publié, `fan_switch_parity: true` correct malgré tout).
4. **IMPLEMENTED** — non-régression validée par `test_fan_parity_non_regression_alongside_energy_and_streaming` (state_class/streaming intacts sur le même payload) + suite complète 968 tests daemon / 224 tests JS tous verts, aucune régression sur Section 2 Typage Jeedom, badges Energy/Streaming, contrat 4D.
5. **IMPLEMENTED** — `git diff --stat resources/daemon/mapping/switch.py resources/daemon/mapping/binary_sensor.py` renvoie vide : zéro changement sur la logique de mapping, lecture seule confirmée.
6. **IMPLEMENTED** — 5 tests daemon (cas FAN publié, SWITCH standard, non-switch, FAN non publié révélant le second écrasement de `reason_code`, non-régression Energy/Streaming) + 2 tests étendus + 4 nouveaux tests JS ; tests réels avec assertions précises (pas de placeholders), vérifiés par exécution directe (voir ci-dessous).
7. **IMPLEMENTED (déclaratif, gate terrain de la phase dev-story)** — Completion Notes documentent des valeurs terrain précises et cohérentes avec le code (eq67 `fan_switch_parity: true` + `reason_code: "probable"`, eq583/eq628 sans la clé, non-régression Energy/Streaming confirmée sur le corpus réel). Non ré-exécuté pendant cette revue (hors périmètre code-review), mais aucune incohérence détectée entre le récit terrain et l'implémentation relue.

### Task Audit

Les 7 tâches (Task 0 à Task 6) marquées `[x]` sont toutes corroborées par des preuves concrètes (diff de code, fichiers de test, sorties de suite de tests, notes terrain détaillées) — aucun écart entre le déclaratif et le code trouvé.

### Vérification indépendante (re-exécutée pendant cette revue)

- `python3 -m pytest -q` (daemon complet) : **968 passed** — conforme à la Completion Note.
- `node --test tests/unit/*.node.test.js` (suite JS complète) : **224 tests, pass 224, fail 0** — conforme à la Completion Note.
- `git diff` relu intégralement sur les 4 fichiers source modifiés + les 2 nouveaux fichiers de test : contenu cohérent avec la description des tâches, aucune modification hors périmètre.

### Code Quality / Security

- Changements strictement additifs (nouvelle clé optionnelle, jamais de valeur par défaut inventée) — cohérent avec le pattern des Stories 15.1/15.2.
- Pont PHP : cast explicite `(bool)` + `array_key_exists` avant lecture, pas d'injection possible (pas d'entrée utilisateur, valeur interne daemon).
- JS : concaténation de chaînes HTML mais le badge est conditionné par un booléen strict (`=== true`), aucune donnée utilisateur interpolée dans le HTML généré pour ce badge — pas de risque XSS additionnel par rapport au code existant.
- Aucun problème de performance : ajout borné O(1) par équipement dans une boucle déjà existante.

### Test Quality

Tests réels avec assertions ciblées (pas de bullshit) : le test `test_fan_family_switch_gets_parity_badge_even_when_not_published` est particulièrement solide car il a été ajusté suite à une découverte réelle en exécutant les tests (second écrasement de `reason_code`), renforçant la validité de l'AC#3 plutôt que de la contourner.

### Action Items

Aucun — aucune issue HIGH ou MEDIUM identifiée après revue adversariale complète (AC, tâches, qualité de code, sécurité, tests, non-régression).
