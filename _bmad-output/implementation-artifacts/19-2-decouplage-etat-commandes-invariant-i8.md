# Story 19.2: Découplage I11 — état streamé et commandes routées par décision de candidat

Status: in-progress

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
  - Non exécutée ce tour : aucun déploiement/dry-run réel effectué (voir Completion Notes — reporté au tour terrain).

- [x] Task 1 — Découpler le state streaming (AC1)
  - [x] Modifier `resources/daemon/sync/state.py` aux **deux** points de filtrage identifiés — `list_state_targets` (l.154) et `_resolve_state_target` (l.263-264) — pour filtrer sur la décision du candidat concerné (`CommandDecision`/décision par candidat issue de `evaluate_equipment()`, Story 19.0/19.1) au lieu de `decision.should_publish` du principal
  - [x] Vérifier qu'aucun autre filtre implicite ne réintroduit une dépendance au principal

- [x] Task 2 — Découpler le routage de commandes (AC2)
  - [x] Modifier `resources/daemon/sync/command.py::_resolve_runtime_target` aux **deux** filtres identifiés (l.201 `should_publish`, l.204 `active_or_alive`) selon le même principe — décision prise sur le `candidate_decision` (l.209) du candidat effectivement ciblé par le topic, jamais sur celle du principal

- [x] Task 3 — Garde-fou anti-couplage-forcé (AC4)
  - [x] Test explicite garantissant qu'un secondaire refusé reste refusé (pas de "tout publier" accidentel)

- [x] Task 4 — Non-régression (AC3)
  - [x] Exécuter `test_story_13_3_metering_plug_secondary_sensors.py` et la suite complète

- [~] Task 5 — Preuve terrain (voir section dédiée)
  - [~] Chercher un cas réel sur la box (via rapport Story 19.1) ; si trouvé, vérifier l'état/routage effectif après correction — 2 candidats I11 déjà identifiés (`19-1-field-proof-2026-09-28.md`, eq 579/585), mais pas encore vérifiés en conditions réelles ce tour (aucun déploiement effectué)
  - [x] Outillage de préparation : `tools/parity_snapshot.py`/`scripts/parity-snapshot.sh` étendus en lecture seule pour relever les topics d'état retenus (`jeedom2ha/+/+/state`) et les corréler aux candidats I11 — code + tests unitaires seulement, jamais exécuté contre la box réelle (voir Completion Notes)
  - [x] **Revue ClaudeBox (commit `3a408db`), P2 — protocole de preuve corrigé.** `state_topics`/`publish_initial_states` (mécanisme ci-dessus) ne distinguent PAS l'avant de l'après un déploiement : sur `main`, l'état des secondaires I11 est déjà publié en retained à chaque sync complète, sans filtre sur le principal — cette mesure seule ne peut donc jamais servir de preuve terrain. `GET /system/state_listeners` (source exacte utilisée par le plugin PHP pour enregistrer ses écouteurs Jeedom, `StateSynchronizer.list_state_targets`) est la seule preuve qui distingue réellement les deux états. `tools/parity_snapshot.py` relève désormais ce champ systématiquement (`state_listeners`, jamais optionnel, même mécanisme que `/system/diagnostics`) et le diff expose `listeners_added`/`listeners_removed` sans jamais influencer `is_empty_diff` (qui reste la parité Story 19.1) — code + 8 tests unitaires (`test_story_19_2_parity_state_listeners.py`), toujours jamais exécuté contre la box réelle.
  - [ ] Si aucun cas réel trouvé, écrire le test d'intégration de repli et le documenter explicitement comme tel — sans objet : le test d'intégration de repli existe déjà (`test_story_19_2_decouplage_state_command_i11.py`)

- [x] Task 6 — Tests (AC1-AC4)
  - [x] `test_story_19_2_decouplage_state_command_i11.py` (préfixe `test_story_19_2_*`)
  - [x] Suite complète — voir Completion Notes pour la commande exacte utilisée (`pytest tests/unit -q` ne couvre pas l'arbre `resources/daemon/tests/unit`) : `pytest -q` depuis la racine → 1882 passed, 0 régression

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

- clawcode (autonome), 2026-09-28

### Debug Log References

### Completion Notes List

- **create-story** — 2026-09-27 — statut résultant : `ready-for-dev`. Story documentaire créée directement (skill officielle non exposée cette session).
- **dev-story (autonome)** — 2026-09-28 — statut résultant : `in-progress` (pas `done` : gate d'inventaire terrain obligatoire non satisfait ce tour, voir ci-dessous). Branche `story/19-2-decouplage-i11`, worktree dédié.

  **Task 0 (pre-flight terrain) — non exécutée ce tour, volontairement.** Cette story a été traitée en mode autonome sans accès interactif à la box réelle dans cette fenêtre de travail ; aucun `./scripts/deploy-to-box.sh --dry-run` ni déploiement n'a été lancé. Conformément à l'exigence explicite de la story ("Gate d'inventaire obligatoire… cette story… ne peut donc passer à `done` qu'après le gate obligatoire d'inventaire"), le statut reste `in-progress` et non `done`. Le gate terrain (dry-run, déploiement, inventaire avant/après 0 erreur) reste à faire dans un tour ultérieur avec accès box.

  **AC1/AC2 — correction I11 (Task 1/Task 2).** `resources/daemon/sync/state.py` : les deux points de filtrage identifiés (`list_state_targets` l.154, `_resolve_state_target` l.263-264) filtraient sur `decision.should_publish` du **principal** avant même de localiser le candidat concerné. Corrigé en déplaçant le filtre `should_publish` **après** résolution de `cand_decision` (décision propre du candidat/secondaire, via `candidate.publication_decision_ref`, avec repli sur `decision` — le principal — uniquement si le candidat n'a pas de décision propre, cas structurellement impossible pour un secondaire mappé). `resources/daemon/sync/command.py::_resolve_runtime_target` : même principe pour les deux filtres identifiés (`should_publish` l.201, `active_or_alive` l.204). Différence de conception notable avec `state.py` : ces deux filtres constituaient aussi la source des codes `reason` de diagnostic pré-existants (`entity_not_published`/`entity_not_alive`, variables `found_publishable`/`found_alive`) lorsqu'aucun candidat ne correspond au topic. Plutôt que de supprimer ce diagnostic, les variables sont désormais dérivées de la décision du **principal** en lecture seule (`if decision.should_publish: found_publishable = True; ...`) sans jamais `continue`/interrompre la boucle — la boucle sur les candidats n'est plus jamais court-circuitée par le principal. Le vrai filtrage de routage (gate binaire qui autorise ou non l'exécution de la commande) est déplacé **dans** la boucle candidats, sur `candidate_decision` du candidat effectivement ciblé par le topic (ligne où `topic not in expected_topics.values()` a déjà réduit à UN candidat). Ceci préserve 100% de la sémantique des codes `reason` pré-existants pour le cas "aucun candidat ne matche" tout en corrigeant le cas "un candidat matche mais c'était le principal qui bloquait".

  **AC4 — garde-fou anti-couplage-forcé (Task 3).** Le découplage n'introduit aucun "tout publier" : chaque candidat garde son propre gate `should_publish`/`active_or_alive`, y compris quand le principal EST publié. Vérifié par 3 tests dédiés (`test_ac4_*`) : un secondaire refusé (`refused_cmd_ids`) sous un principal publié n'est ni streamé (`list_state_targets` ET `handle_state_message`) ni routé (`handle_command_message`), tandis que le principal et les autres secondaires publiés restent fonctionnels (pas d'effet de bord "tout ou rien").

  **Preuve par mutation (méthodologie, avant PR).** `git stash push -- resources/daemon/sync/state.py resources/daemon/sync/command.py` (fichier de test neuf non suivi, donc non stashé) puis exécution de `test_story_19_2_decouplage_state_command_i11.py` sur le code PRÉ-correction : **4 des 6 tests échouent** (`test_ac1_secondary_listed_as_state_target_despite_refused_principal`, `test_ac1_secondary_state_streamed_despite_refused_principal`, `test_ac2_secondary_command_routed_despite_refused_principal`, `test_ac4_refused_secondary_never_routed_command`). Les 2 tests restants (`test_ac4_refused_secondary_never_streamed_state*`) passent déjà sur l'ancien code — explication : `state.py` pré-correction avait déjà un filtre par-candidat sur `discovery_published` (mais pas sur `should_publish`), qui suffisait par coïncidence à couvrir CE cas précis (secondaire refusé avec `discovery_published=False` implicite dans le test) ; `command.py` pré-correction n'avait AUCUN filtre par-candidat équivalent — `test_ac4_refused_secondary_never_routed_command` révèle donc un vrai bug de sur-permissivité du routage jusqu'ici non détecté (un secondaire refusé pouvait être routé si le principal était publié). `git stash pop` puis re-exécution : **6/6 passent** sur le code corrigé. Ce bug (routage AC4 sans le correctif) est documenté ici car il constitue une preuve indépendante que Task 2/AC2 corrige un problème réel, pas seulement théorique.

  **Découverte — deux arbres de tests, une seule commande couvre les deux.** Le repo a deux arbres `tests/unit` : racine (`tests/unit`, 58 fichiers, général/infra) et `resources/daemon/tests/unit` (85 fichiers dont ce nouveau, sync/mapping/command). La commande littéralement citée par la story (`pytest tests/unit -q`) exécutée depuis la racine ne couvre QUE l'arbre racine — elle ne joue jamais les tests touchant `sync/state.py`/`sync/command.py`. Vérification de non-régression réelle : `python3 -m pytest -q` (sans argument de chemin, laissant `testpaths` s'appliquer aux deux arbres) depuis la racine → **1882 passed, 0 failed** (1870 avant cette story + 12 nouveaux tests story 19.2 dont 6 sur I11 et 6 sur l'extension outil de parité). `test_story_13_3_metering_plug_secondary_sensors.py` (AC3, non-régression pattern "metering plug") inclus et vert sans modification de son intention.

  **Task 5 — préparation de la preuve terrain, extension lecture seule de `tools/parity_snapshot.py`.** L'outil (Story 19.1) détectait déjà des "candidats I11" par heuristique (corrélation topics discovery retained / décision refusée du principal), mais n'inventoriait pas les topics d'ÉTAT retenus (`jeedom2ha/<eq_id>/<cmd_id>/state`) — donc ne pouvait pas vérifier la preuve terrain demandée par la story ("discovery state_topic == topics d'état retenus non vides"). Ajout strictement opt-in et lecture seule :
    - `tools/parity_snapshot.py` : nouvelle fonction `_detect_i11_state_coverage()` qui corrèle, pour chaque candidat I11 déjà détecté, son/ses `cmd_id` (extraits du node_id discovery `jeedom2ha_<eq_id>_<cmd_id>`) avec un second inventaire MQTT (topics d'état retenus). Nouveau champ `ParitySnapshot.state_topics` et nouveau paramètre optionnel `capture_snapshot(mqtt_state_inventory_file=...)` : sans lui, format et comportement restent STRICTEMENT identiques à Story 19.1 (vérifié par test dédié `test_capture_snapshot_without_state_file_keeps_story_19_1_shape`). Nouveau flag CLI `--mqtt-state-inventory-file`, optionnel.
    - `scripts/parity-snapshot.sh` : ajout d'une deuxième souscription `mosquitto_sub -t 'jeedom2ha/+/+/state'` sur la box (même mécanisme d'authentification CC-20/trap EXIT que la première), écrite dans un second fichier temporaire transmis au tool via `--mqtt-state-inventory-file`. Jamais `mosquitto_pub`, jamais exécuté contre la box réelle dans ce tour (code + tests unitaires seulement, conformément à la consigne).
    - Régression de test existant corrigée : `tests/unit/test_parity_snapshot_wrapper.py` asserait exactement 1 appel `mosquitto_sub` par capture — mis à jour pour attendre 2 appels en cas de succès (0 si la première souscription échoue, le script s'arrêtant avant la seconde grâce à `pipefail`).
    - Portée des candidats I11 réels connus (mesure seule, `19-1-field-proof-2026-09-28.md`) : eq 579 (cmd_ids 5369/5493/5494/5689/5695), eq 585 (cmd_ids 5497/5504/5505/5536/5537/5546/5631) — 2 candidats, cohérent avec la mesure `i11_candidates: 2` déjà relevée sur la box lors de la Story 19.1. Ces identifiants n'ont pas été revérifiés contre la box dans ce tour (aucune connexion établie) ; ils sont repris tels quels depuis l'artefact de preuve terrain 19.1 pour cadrer un futur relevé `--mqtt-state-inventory-file`.

  **Écart documenté — Task 5 non close.** Le gate d'inventaire obligatoire (préambule de la story) et la preuve terrain proprement dite (vérification RÉELLE sur la box que les 2 candidats I11 connus ont désormais leurs topics d'état) restent à faire. Ce tour livre : la correction, sa preuve unitaire + mutation, et l'outillage prêt à l'emploi pour cette vérification terrain — mais pas la vérification elle-même. Statut de la story laissé à `in-progress` pour cette raison, jamais forcé à `done`.

- **code-review (ClaudeBox) + corrections (autonome)** — 2026-09-28 — commit de revue `3a408db` (PR #174). Trois points bloquants/majeurs corrigés (P1/P2/P3 ci-dessous), plus le protocole de preuve terrain Task 5 revu (voir checklist Task 5 ci-dessus) ; statut résultant : `in-progress` (inchangé — le gate d'inventaire terrain reste le seul écart bloquant `done`).

  **P1 (bloquant) — `publication_decision_ref` incohérent avec `app["publications"][eq_id]`.** Avant ce correctif, chaque branche de `_handle_action_execute` ("supprimer", "publier" en échec discovery/local-availability, "publier" dans `ecarts_resolus") ne remplaçait QUE `publications[eq_id]` par la nouvelle décision (refusée/échouée) — `mapping.publication_decision_ref` (principal ET secondaires), consulté directement par les lecteurs I11-découplés (`sync/state.py`, `sync/command.py`, `_secondary_publishable`), continuait de pointer sur l'ANCIENNE décision jusqu'à la prochaine synchro complète. Conséquence réelle : un équipement supprimé/exclu par "publier"/"supprimer" continuait de streamer son état MQTT et de router ses commandes (le vrai bug), et à l'inverse une republication réussie après un échec précédent restait bloquée jusqu'à resynchro. Corrigé par deux helpers nouveaux dans `http_server.py` : `_sync_publication_decision_refs(mapping, decision, *, reason_for_secondaries, preserve_secondary_discovery_published=False)`, appelé aux 6 sites de remplacement de décision (2× "supprimer", 2× "publier" échecs, 2× `ecarts_resolus`), qui repointe `mapping.publication_decision_ref` vers la nouvelle décision ET refuse chaque secondaire via `_refuse_secondary_decision` (construit une décision refusée FRAÎCHE par secondaire — ne mute jamais l'ancienne, d'autres lecteurs pouvant encore la référencer) ; et l'ajout de `mapping.publication_decision_ref = decision` dans le chemin de succès "publier" (le principal republié n'était, lui non plus, jamais resynchronisé). `_publish_mapping_for_action` bascule aussi `discovery_published`/`active_or_alive` à `True` sur le SECONDAIRE effectivement republié — sans ce point, un secondaire republié restait routé comme s'il l'était toujours pas.

  **P2 (majeur) — `active_or_alive` jamais remis à `False` pour un secondaire avant tentative.** `PublicationDecision.active_or_alive` vaut `True` par défaut (`models/mapping.py`) ; le principal le remettait déjà à `False` avant chaque tentative de publication (`_prepare_publication_bookkeeping`), mais `_publish_additional_sensors` (secondaires) ne le faisait jamais — un secondaire dont la publication discovery échouait restait donc `active_or_alive=True` et continuait d'être routé par `sync/command.py` (qui gate sur `should_publish` ET `active_or_alive`, contrairement à `sync/state.py` qui ne gate que sur `should_publish`/`discovery_published` — vérifié en lisant les deux modules en entier). Corrigé par une ligne `sec_decision.active_or_alive = False` avant la tentative, même modèle que le principal.

  **P3 (mineur) — reason codes de diagnostic non fiables dans `_resolve_runtime_target`.** `found_publishable`/`found_alive` (variables produisant `entity_not_published`/`entity_not_alive` quand aucun candidat ne matche le topic) étaient dérivées AVANT la boucle candidats, uniquement de la décision du PRINCIPAL — un principal refusé avec un secondaire ciblé publié-mais-non-alive rapportait donc `entity_not_published` (hérité à tort du principal) au lieu de `entity_not_alive` (l'état réel du secondaire visé). Le routage effectif (gate binaire) était déjà correct (par-candidat, architecture I11 déjà en place) ; seul le diagnostic était trompeur. Corrigé en dérivant `found_publishable`/`found_alive` du `candidate_decision` du candidat qui matche réellement le topic (`matched_topic`), avec repli sur la décision du principal uniquement si AUCUN candidat ne matche (cas `unknown`/topic totalement étranger). Correction additionnelle mineure : reformulation d'un commentaire ambigu dans le docstring de module de `tools/parity_snapshot.py` (« format strictement identique » remplacé par une description précise de ce qui reste inchangé — le contenu de `state_topics`/`i11_candidates` sans `--mqtt-state-inventory-file` — vs. ce qui change structurellement — la clé `state_topics` elle-même, désormais toujours présente dans `to_dict()`).

  **Tests nouveaux et preuve par mutation.** 5 tests daemon nouveaux, chacun avec preuve par mutation (`git stash push --keep-index -- <fichier de production>`, ré-exécution, `git stash pop`) :
  - `test_story_19_2_p1_publication_decision_ref_coherence.py` (4 tests, P1+P2) : (1) `test_e2e_supprimer_stops_state_streaming_and_command_routing` — bout en bout via `/action/sync` puis `/action/execute` "supprimer" (eq553 multi-sensor + eq628 multi-switch réels) ; (2) `test_publier_out_of_scope_ecart_stops_state_streaming_and_command_routing` — branche `ecarts_resolus` de "publier" ; (3) `test_publier_success_after_prior_failure_restores_principal_command_routing` — republication réussie après un échec précédent, vérifie que `mapping.publication_decision_ref` redevient la décision courante ET que le routage de commande est restauré ; (4) `test_p2_secondary_discovery_publish_failure_blocks_command_routing` — appel direct à `_publish_additional_sensors`, un secondaire échoue sa discovery, son routage de commande doit être bloqué tandis qu'un secondaire frère publié avec succès reste routable. Reverting `http_server.py` (stash) → les 4 échouent avec des messages d'assertion cohérents avec le bug décrit (ex. `active_or_alive is True` au lieu de `False` attendu). Restore → 4/4 passent.
  - `test_story_19_2_p3_command_reason_code_candidate.py` (1 test, P3) : **découverte pendant la mutation testing** — les 4 tests P1/P2 ainsi que la suite complète (1894 tests) passaient déjà TOUS avec le fix P3 reverté seul (aucun test existant n'exerçait ce chemin précis). Un test dédié a donc été écrit spécifiquement : principal refusé + secondaire ciblé publié-mais-non-alive → attend `reason_code=entity_not_alive`. Sans le fix : `reason_code=entity_not_published` (bug reproduit exactement), avec `assert "reason_code=entity_not_alive" in caplog.text` qui échoue. Avec le fix restauré : passe.
  - `test_story_19_2_parity_state_listeners.py` (8 tests, tooling P2) : `fetch_state_listeners` (mécanisme d'en-tête identique à `fetch_diagnostics`), capture avec/sans écouteurs, diff `listeners_added`/`listeners_removed`, rétrocompatibilité d'un relevé pré-P2 sans le champ, non-influence sur `is_empty_diff`, clé `state_listeners` dans `to_dict()`. Reverting `tools/parity_snapshot.py` → les 8 échouent (`KeyError`/`TypeError`/`AttributeError` selon le test — fonctions/champs absents). Restore → 8/8 passent.
  - 2 fichiers de tests existants mis à jour (non-régression, pas de nouveau comportement testé) : `test_story_19_1_parity_tool_readonly.py`, `test_story_19_2_parity_state_topics.py` — ajout d'un `monkeypatch.setattr(pt, "fetch_state_listeners", ...)` partout où `capture_snapshot` est exercé, `fetch_state_listeners` étant désormais appelée systématiquement (non optionnelle, contrairement à `fetch_published_scope`/state topics).

  **Suite complète et non-régression.** `python3 -m pytest -q` depuis la racine du worktree → **1895 passed, 0 failed** (1882 avant ce tour + 5 tests P1/P2/P3 + 8 tests state_listeners, moins les 2 fichiers de tests existants modifiés en place sans ajout net de cas). `test_story_19_2_decouplage_state_command_i11.py` (6 tests I11 déjà existants) et `test_story_13_3_metering_plug_secondary_sensors.py` (non-régression pattern "metering plug", AC3) exécutés explicitement en isolation en plus de la suite complète — verts sans modification.

### File List

- `resources/daemon/sync/state.py` [MODIFIÉ] — AC1, découplage I11 (`list_state_targets`, `_resolve_state_target`)
- `resources/daemon/sync/command.py` [MODIFIÉ] — AC2, découplage I11 (`_resolve_runtime_target`) ; revue ClaudeBox P3 — reason codes dérivés du candidat effectivement ciblé, plus du principal
- `resources/daemon/tests/unit/test_story_19_2_decouplage_state_command_i11.py` [NOUVEAU] — AC1-AC4, 6 tests
- `resources/daemon/tools/parity_snapshot.py` [MODIFIÉ] — Task 5, extension lecture seule opt-in (topics d'état retenus, corrélation I11) ; revue ClaudeBox P2 — `fetch_state_listeners`/champ `state_listeners`/diff `listeners_added`+`listeners_removed`, relevé systématique via `/system/state_listeners` ; P3 — reformulation docstring module
- `resources/daemon/tests/unit/test_story_19_2_parity_state_topics.py` [MODIFIÉ] — Task 5, 12 tests (extension outil de parité) ; revue ClaudeBox — mock `fetch_state_listeners` ajouté (appel désormais systématique)
- `scripts/parity-snapshot.sh` [MODIFIÉ] — Task 5, seconde souscription MQTT (topics d'état) en lecture seule
- `tests/unit/test_parity_snapshot_wrapper.py` [MODIFIÉ] — mise à jour du test wrapper existant (2 souscriptions MQTT au lieu d'1)
- `resources/daemon/transport/http_server.py` [MODIFIÉ] — revue ClaudeBox P1/P2 — helpers `_sync_publication_decision_refs`/`_refuse_secondary_decision`, câblage aux 6 sites de remplacement de décision ("supprimer" ×2, "publier" échecs ×2, `ecarts_resolus` ×2), resynchro du principal au succès "publier", reset `active_or_alive=False` avant tentative secondaire (`_publish_additional_sensors`), bascule `discovery_published`/`active_or_alive` du secondaire effectivement republié
- `resources/daemon/tests/unit/test_story_19_2_p1_publication_decision_ref_coherence.py` [NOUVEAU] — revue ClaudeBox P1/P2, 4 tests (preuve par mutation)
- `resources/daemon/tests/unit/test_story_19_2_p3_command_reason_code_candidate.py` [NOUVEAU] — revue ClaudeBox P3, 1 test (gap détecté pendant la mutation testing — aucun test existant n'exerçait ce chemin ; preuve par mutation)
- `resources/daemon/tests/unit/test_story_19_2_parity_state_listeners.py` [NOUVEAU] — revue ClaudeBox P2 (tooling), 8 tests (preuve par mutation)
- `resources/daemon/tests/unit/test_story_19_1_parity_tool_readonly.py` [MODIFIÉ] — revue ClaudeBox — mock `fetch_state_listeners` ajouté (appel désormais systématique)
- `_bmad-output/implementation-artifacts/19-2-decouplage-etat-commandes-invariant-i8.md` [MODIFIÉ] — statut, tasks, Completion Notes, File List
- `_bmad-output/implementation-artifacts/sprint-status.yaml` [MODIFIÉ] — statut `19-2-decouplage-etat-commandes-invariant-i8: in-progress`
