# Story 11.3: IQ EV Charger + Pilotage priorisation solaire

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur familial de Home Assistant,
je veux retrouver dans HA les états, mesures et priorisations solaires de l'IQ EV Charger (eq583) et du pilotage de priorisation solaire (eq628),
afin de superviser et piloter les modes de charge solaires sans rester bloqué sur un composite unique en `unknown`.

## Acceptance Criteria

1. **IQ EV états et mesures publiés.** Les commandes info IQ EV eq583 suivantes sont publiées sans ouverture de type HA nouvelle : `binary_sensor` pour #5986 Branché, #5987 Charge, #6009 Charge solaire état, #6010 Charge manuelle état ; `sensor` pour #5991 Puissance W, #5992 Énergie session Wh, #5993 Énergie jour Wh.
2. **IQ EV actions modélisées en deux switches logiques.** Les paires On/Off dissociées eq583 produisent deux `switch` HA distincts : Charge solaire (#6009 readback, #5999 On, #6001 Off) et Charge manuelle (#6010 readback, #6000 On, #6021 Off). Les identifiants, object_id, command_topic et state_topic sont stables et distincts par commande de readback.
3. **eq628 produit quatre switches de priorisation.** Le pattern triple-commande info+on+off de eq628 produit quatre `switch` HA distincts : Filtration piscine (#5977/#5978/#5979), Chauffage piscine (#5980/#5981/#5982), Chauffage SPA (#5983/#5984/#5985), Charge voiture (#6004/#6005/#6006).
4. **Streaming runtime cohérent pour les switches multiples.** Chaque switch logique multi-switch utilise sa commande info de readback comme cible de state listener, publie son état initial et ses changements sur son propre `state_topic`, avec traduction `ON`/`OFF` conforme au payload discovery. Aucun état n'est publié sur une commande action On/Off.
5. **State ⊆ discovery et lifecycle.** Les topics state/command des multi-switches sont lus depuis les mappings/publications déclarés ; la dépublication d'un équipement multi-switch supprime tous les node_ids secondaires. Aucun topic discovery secondaire orphelin ne reste après suppression ou changement de politique.
6. **Périmètre strict.** Aucun nouveau type n'est ajouté à `PRODUCT_SCOPE`; `number`, `select`, `climate`, intégration Enphase native et UX composite dédiée restent hors scope. `button` reste command-only/stateless et ne reçoit aucun `state_topic`.
7. **Non-régression.** Les switches mono-entité historiques, presence switch 10.7, multi-sensor 11.1, streaming 12.1/12.2, discovery, commandes HA -> Jeedom et golden-file existants restent verts.
8. **Gate terrain.** Sur box réelle DEV/TEST `192.168.1.21`, après deploy/restart/sync : les entités eq583/eq628 disponibles dans l'inventaire live sont publiées avec des topics discovery distincts ; au moins un switch multi-switch prouve un état `ON`/`OFF` retenu sur MQTT et n'est plus `unknown`. Si eq583/eq628 sont absents ou désactivés sur la box, documenter le constat et valider par fixture représentative + non-régression terrain existante.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — NON EXÉCUTÉ dans cette passe (à faire avant `done`)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Couvrir par tests le pattern multi-switch borné (AC: #2, #3, #4, #5, #7)
  - [x] Ajouter une fixture eq583 avec deux trios logiques ENERGY_STATE/ENERGY_ON/ENERGY_OFF différenciés par nom/cmd_id.
  - [x] Ajouter une fixture eq628 avec quatre trios logiques info+on+off.
  - [x] Vérifier que `MapperRegistry.map_all()` retourne N switches distincts et que `map()` conserve le primaire + `additional_mappings`.
  - [x] Vérifier que discovery, state listeners et snapshots initiaux utilisent des topics par commande de readback, pas le topic unique eq-level.

- [x] Task 2 — Étendre `SwitchMapper` au multi-switch par équipement (AC: #2, #3, #6, #7)
  - [x] Conserver le comportement mono-switch historique quand un seul trio logique existe.
  - [x] Produire plusieurs `MappingResult` switch quand plusieurs commandes info de readback et plusieurs paires On/Off coexistent sur le même eqLogic.
  - [x] Utiliser des `ha_unique_id`, `object_id`, `node_id`, `state_topic`, `command_topic` et noms HA distincts par switch logique.
  - [x] Ne pas publier de faux switch si un trio n'a pas readback + On + Off utilisables.

- [x] Task 3 — Propager les topics par mapping dans discovery, publication et streaming (AC: #2, #4, #5)
  - [x] Adapter `_build_switch_payload()` pour honorer `reason_details` quand un switch fournit `object_id`, `command_topic` ou `state_topic`.
  - [x] Adapter `_resolve_state_topic()` pour honorer `reason_details["state_topic"]`.
  - [x] Vérifier que `StateSynchronizer` lit `reason_details["cmd_id"]` et publie sur le topic du switch logique.
  - [x] Vérifier que la dépublication collecte tous les node_ids des switches secondaires.

- [x] Task 4 — Valider les chemins existants et le non-scope (AC: #1, #6, #7)
  - [x] Confirmer que sensor/binary_sensor IQ EV restent couverts par mappers existants ou par fixtures représentatives sans nouvelle ouverture `PRODUCT_SCOPE`.
  - [x] Confirmer que `button` reste absent du streaming d'état.
  - [x] Exécuter les tests ciblés puis la suite daemon complète.

- [>] Task 5 — Gate terrain et clôture BMAD (AC: #8)
  - [ ] Exécuter le déploiement terrain via `scripts/deploy-to-box.sh` uniquement. — RESTANT avant `done`
  - [ ] Relever discovery/state topics eq583/eq628 si présents ; sinon documenter absence/désactivation et la preuve alternative. — RESTANT avant `done`
  - [x] Mettre à jour `Dev Agent Record`, `File List`, `Change Log`, puis passer la story en `review`.

## Dev Notes

### Source produit et scope

- Story issue de la carte workboard `Story 11.3` (id `9039c60c-f221-468f-83cd-6c99f82f6ea4`) et formalisée par le correct-course 2026-06-18.
- Scope confirmé : IQ EV Charger eq583 + Pilotage priorisation solaire eq628, source inventaire `_bmad-output/planning-artifacts/backlog-icebox.md` §4.
- Dépendance technique levée : Story 12.1 (`sensor`/`binary_sensor`) et Story 12.2 (`switch`, `button` no-op) sont `done` dans `sprint-status.yaml`.
- Aucun nouveau type HA : `sensor`, `binary_sensor`, `switch`, `button` sont déjà dans `PRODUCT_SCOPE` (`resources/daemon/validation/ha_component_registry.py`).

### Architecture et contraintes

- `MapperRegistry` supporte déjà `map_all()` et `additional_mappings` depuis Story 11.1. Réutiliser ce mécanisme plutôt qu'ajouter un nouveau registre.
- `SensorMapper` montre le pattern d'identité par commande via `reason_details`: `cmd_id`, `object_id`, `node_id`, `state_topic`.
- `SwitchMapper` actuel collecte les ENERGY_* dans un dict plat `{generic_type: JeedomCmd}` ; c'est la limite à lever de façon bornée pour les équipements virtuels multi-switch.
- `StateSynchronizer` sait déjà itérer le mapping primaire + `additional_mappings` et priorise `reason_details["cmd_id"]` / `reason_details["state_topic"]`.
- Le payload discovery switch historique utilise `jeedom2ha/{eq}/set` et `jeedom2ha/{eq}/state`; pour multi-switch, utiliser des topics distincts par readback, par exemple `jeedom2ha/{eq}/{cmd_id}/set` et `jeedom2ha/{eq}/{cmd_id}/state`.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

#### Garde-fous implémentation

- Ne pas modifier `_bmad/`.
- Ne pas ajouter de `PRODUCT_SCOPE`.
- Ne pas inventer de `number`/`select` ou de surface composite dédiée.
- Ne pas transformer `button` en entité à état.
- Garder le comportement mono-switch inchangé pour les équipements existants.
- Toute valeur runtime doit provenir d'une commande info Jeedom, jamais d'une action On/Off.

### Project Structure Notes

- Worktree : `projects/jeedom2ha-pe-12.1`.
- Modules probables : `resources/daemon/mapping/switch.py`, `resources/daemon/discovery/publisher.py`, `resources/daemon/transport/http_server.py`, `resources/daemon/sync/state.py`.
- Tests probables : nouveau `resources/daemon/tests/unit/test_story_11_3_iq_ev_priorisation.py` + ajustements ciblés aux tests 12.2 si nécessaire.

### References

- `_bmad-output/planning-artifacts/backlog-icebox.md` §4 — inventaire eq583/eq628.
- `_bmad-output/planning-artifacts/epics-projection-engine.md` — Epic 11, Story 11.3.
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-18-pe-11.3.md` — décision de séquencement et dépendance 12.2.
- `_bmad-output/implementation-artifacts/10-4-cadrage-des-composites-metier-iq-ev-spa-sans-ouverture-cosmetique.md` — handoff multi-switch.
- `_bmad-output/implementation-artifacts/12-2-streaming-valeur-switch-button-vague-2.md` — streaming switch et button no-op.
- `resources/daemon/mapping/switch.py` — mapper à étendre.
- `resources/daemon/mapping/registry.py` — `map_all()` et `additional_mappings`.
- `resources/daemon/discovery/publisher.py` — payload switch discovery.
- `resources/daemon/sync/state.py` — streaming runtime state.
- `resources/daemon/transport/http_server.py` — publication decisions, state_topic, unpublish node_ids.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `python3 -m pytest resources/daemon/tests/unit/test_story_11_3_iq_ev_priorisation.py -q` → 6 passed.
- `python3 -m pytest resources/daemon/tests -q` → 903 passed, 637 warnings (warnings aiohttp/deprecation existants).

### Completion Notes List

- 2026-06-20 — workflow lancé : `create-story` ; statut résultant : `ready-for-dev`. Story 11.3 formalisée après audit : fichier absent, sprint-status en `backlog`, dépendance 12.2 désormais `done`.
- 2026-06-20 — workflow lancé : `dev-story` ; statut résultant : `in-progress`. Implémentation multi-switch bornée en cours.
- 2026-06-21 — workflow lancé : `dev-story closeout` ; statut résultant : `review`. Implémentation locale validée par tests (6 ciblés, 903 daemon). Gate terrain eq583/eq628 restant avant `done` / release ; ne pas marquer `done` sans `code-review`.

### File List

- `_bmad-output/implementation-artifacts/11-3-iq-ev-pilotage-priorisation-solaire.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/mapping/switch.py`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/sync/command.py`
- `resources/daemon/sync/state.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/transport/mqtt_client.py`
- `resources/daemon/tests/unit/test_story_11_3_iq_ev_priorisation.py`
- `resources/daemon/tests/unit/test_story_10_6_fix_scenario_subscription.py`

### Change Log

- 2026-06-20 — BMAD create-story : story 11.3 créée en `ready-for-dev`.
- 2026-06-20 — BMAD dev-story : démarrage, statut `in-progress`.
- 2026-06-21 — BMAD dev-story closeout : tests ciblés + suite daemon verts, story passée en `review`; gate terrain et `code-review` restent bloquants avant `done`.
