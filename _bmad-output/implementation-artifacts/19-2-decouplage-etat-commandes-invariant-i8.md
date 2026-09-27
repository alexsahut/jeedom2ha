# Story 19.2: Découplage I11 — état streamé et commandes routées par décision de candidat

Status: backlog

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un mainteneur,
I want que `resources/daemon/sync/state.py` et `resources/daemon/sync/command.py` filtrent le state-streaming et le routage de commandes sur la décision **du candidat/secondaire lui-même**, jamais sur celle du principal,
so that un secondaire publié sous un principal refusé (ex. pattern "metering plug") reçoive bien son état MQTT et voie ses commandes routées, au lieu de devenir une entité HA fantôme sans état ni commande.

**Parcours : complet.**

## Acceptance Criteria

**AC1 — State streaming découplé (I11)**

**Given** un équipement dont le principal est refusé (`should_publish=False`) mais dont un secondaire est publié (`should_publish=True`)
**When** `resources/daemon/sync/state.py` décide de streamer l'état d'une entité — deux points de filtrage précis à corriger : `list_state_targets` (filtre sur `decision.should_publish` du principal, l.154, **avant** même d'itérer les candidats à la recherche de leur propre `cand_decision`, l.164-165) et `_resolve_state_target` (même filtre sur le principal, l.263-264, **avant** la recherche du candidat ciblé par `eq_id`/`cmd_id`)
**Then** la décision de streaming est prise sur la `CommandDecision`/décision **du candidat concerné**, jamais sur celle du principal
**And** le secondaire publié reçoit son état MQTT streamé
**And** un test explicite reproduit ce cas et vérifie que l'état du secondaire est bien streamé malgré le refus du principal.

**AC2 — Routage de commandes découplé (I11)**

**Given** le même scénario (principal refusé, secondaire publié)
**When** `resources/daemon/sync/command.py::_resolve_runtime_target` décide de router une commande entrante — filtre sur `decision.should_publish` du principal en l.201, puis sur `decision.active_or_alive` (toujours le principal) en l.204, **avant** d'itérer les candidats (`candidate_decision`, l.209) pour trouver celui qui correspond réellement au topic
**Then** la décision de routage est prise sur la décision **du candidat concerné**, jamais sur celle du principal
**And** les commandes destinées au secondaire publié sont bien routées
**And** un test explicite reproduit ce cas et vérifie le routage effectif de la commande du secondaire.

**AC3 — Non-régression du pattern "metering plug"**

**Given** le corpus de test `test_story_13_3_metering_plug_secondary_sensors.py` (secondaires indépendants du type du principal)
**When** le découplage I11 est implémenté
**Then** ce test reste vert sans modification de son intention (des ajustements de mécanique interne sont acceptables si la sémantique du test n'est pas affaiblie)
**And** aucune autre suite existante liée aux secondaires/multi-sensor n'est régressée.

**AC4 — Pas de couplage forcé (I11 correctement interprété)**

**Given** l'invariant I11 tel que formulé ("publié ⇒ état streamé ET commandes routées")
**When** l'implémentation est revue
**Then** la correction ne force **jamais** un secondaire à hériter de la décision du principal (ni dans un sens ni dans l'autre) — chaque candidat garde sa décision propre, indépendante
**And** un test explicite vérifie qu'un principal publié avec un secondaire refusé ne fait PAS streamer/router le secondaire refusé (le découplage n'est pas un "tout publier", c'est un "chacun sa décision").

## UI Impact

- **UI Impact:** Non — changement interne au daemon (`sync/state.py`, `sync/command.py`), aucun changement d'interface utilisateur.

## Impact sur la production et retour arrière

Changement de comportement réel et volontaire : des entités HA aujourd'hui "fantômes" (publiées en discovery mais sans état/commande car secondaires d'un principal refusé) recevront désormais leur état et leurs commandes. C'est une correction de bug (I11), pas une régression attendue. Retour arrière : revert de la story/PR — `state.py`/`command.py` reviennent au filtrage sur la décision du principal ; aucune migration de données requise, aucun changement de schéma de persistance.

## Preuve terrain

Preuve terrain = sur la box, pour toutes les entités : `discovery state_topic ==` topics d'état retenus non vides ; à défaut d'un cas réel, repli par test seulement pour I11, reproduisant « principal refusé / secondaire publié », et explicitement documenté dans les Completion Notes.

**Gate d'inventaire obligatoire (convention repo, `sprint-status.yaml`) :** cette story touche la publication vers Home Assistant (état MQTT streamé + routage de commandes pour des entités déjà publiées) — elle ne peut donc passer à `done` qu'après le gate obligatoire d'inventaire des entités avant/après déploiement (0 erreur), au même titre que toute story de ce type. Ce gate est distinct de l'outil de parité de Story 19.1 (qui mesure la décision de publication) : il porte spécifiquement sur l'inventaire des entités HA effectivement présentes après déploiement de cette correction.

## Invariants concernés

I11 (objet principal de cette story — correction par découplage explicite, jamais par couplage forcé). I1-I7 non modifiés, à ne pas régresser (vérifié par la suite complète).

## Points fermés

Aucun CC-xx explicitement listé dans le contexte fourni ne correspond directement à I11 (I11 est une découverte de ce chantier, pas un ticket CC-xx préexistant). Cette story ne ferme donc pas de CC-xx numéroté ; elle corrige l'invariant I11 découvert pendant l'analyse. CC-04/CC-14 non concernés par cette story spécifique.

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / state streaming / routage commande / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY)
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Identifier, via le rapport de l'outil de parité (Story 19.1, AC4), un cas réel de violation I11 sur la box si disponible
  - [ ] **Interdiction explicite (DANGER) :** ne jamais invoquer `--cleanup-discovery` ni `--stop-daemon-cleanup` (`scripts/deploy-to-box.sh:95,97`) pendant la vérification terrain de cette story — ces flags republient des messages MQTT retained **vides** sur les topics discovery, ce qui effacerait les entités déjà publiées (principal et secondaires) et rendrait impossible de constater si un secondaire reçoit bien son état/ses commandes après correction. Déploiement standard uniquement.

- [ ] Task 1 — Découpler le state streaming (AC1)
  - [ ] Modifier `resources/daemon/sync/state.py` aux **deux** points de filtrage identifiés — `list_state_targets` (l.154) et `_resolve_state_target` (l.263-264) — pour filtrer sur la décision du candidat concerné (`CommandDecision`/décision par candidat issue de `evaluate_equipment()`, Story 19.0/19.1) au lieu de `decision.should_publish` du principal
  - [ ] Vérifier qu'aucun autre filtre implicite ne réintroduit une dépendance au principal

- [ ] Task 2 — Découpler le routage de commandes (AC2)
  - [ ] Modifier `resources/daemon/sync/command.py::_resolve_runtime_target` aux **deux** filtres identifiés (l.201 `should_publish`, l.204 `active_or_alive`) selon le même principe — décision prise sur le `candidate_decision` (l.209) du candidat effectivement ciblé par le topic, jamais sur celle du principal

- [ ] Task 3 — Garde-fou anti-couplage-forcé (AC4)
  - [ ] Test explicite garantissant qu'un secondaire refusé reste refusé (pas de "tout publier" accidentel)

- [ ] Task 4 — Non-régression (AC3)
  - [ ] Exécuter `test_story_13_3_metering_plug_secondary_sensors.py` et la suite complète

- [ ] Task 5 — Preuve terrain (voir section dédiée)
  - [ ] Chercher un cas réel sur la box (via rapport Story 19.1) ; si trouvé, vérifier l'état/routage effectif après correction
  - [ ] Si aucun cas réel trouvé, écrire le test d'intégration de repli et le documenter explicitement comme tel

- [ ] Task 6 — Tests (AC1-AC4)
  - [ ] `test_story_19_2_decouplage_state_command_i11.py` (préfixe `test_story_19_2_*`)
  - [ ] Suite complète `pytest tests/unit -q` : 0 régression

## Dev Notes

### Contexte pipeline

- Cette story dépend de Story 19.1 (le sync doit déjà produire des décisions par candidat via `evaluate_equipment()`/`CommandDecision`) — ne jamais implémenter le découplage sur l'ancien mécanisme `decide_publication()` direct.
- Le pattern "metering plug" (Story 13.3) est la référence de non-régression : des secondaires indépendants du type du principal doivent continuer à fonctionner après le découplage.

### Dev Agent Guardrails

- Ne jamais coupler la décision d'un secondaire à celle du principal, dans aucun sens.
- `state.py`/`command.py` restent des consommateurs de décisions déjà calculées — aucune logique de décision (I1-I7) ne doit être dupliquée ou réimplémentée dans ces modules.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh`.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

### Project Structure Notes

- Fichiers à toucher (probable) : `resources/daemon/sync/state.py` [MODIFIÉ], `resources/daemon/sync/command.py` [MODIFIÉ], `resources/daemon/tests/unit/test_story_19_2_*.py` [NOUVEAU].

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] — invariant I11, règle de découplage actée (pas de couplage forcé).
- [Source: resources/daemon/sync/state.py#L154] — `list_state_targets`, filtrage actuel sur `decision.should_publish` du principal (à corriger).
- [Source: resources/daemon/sync/state.py#L263-L264] — `_resolve_state_target`, même filtrage sur le principal (à corriger).
- [Source: resources/daemon/sync/command.py#L201] — `_resolve_runtime_target`, filtrage sur `decision.should_publish` du principal (à corriger).
- [Source: resources/daemon/sync/command.py#L204] — `_resolve_runtime_target`, filtrage sur `decision.active_or_alive` du principal (à corriger).
- [Source: resources/daemon/tests/unit/test_story_13_3_metering_plug_secondary_sensors.py] — non-régression du pattern secondaires indépendants.
- [Source: _bmad-output/implementation-artifacts/19-1-sync-migre-contrat-decision-sans-changement-comportement.md] — outil de parité, mesure préalable des violations I11.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- **create-story** — 2026-09-27 — statut résultant : `ready-for-dev`. Story documentaire créée directement (skill officielle non exposée cette session).

### File List
