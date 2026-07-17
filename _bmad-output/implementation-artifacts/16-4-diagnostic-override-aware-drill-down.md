# Story 16.4: Diagnostic override-aware avec drill-down commande par commande

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur,
je veux déplier un équipement pour voir, commande par commande, le `generic_type` Jeedom actuel, l'attendu Home Assistant, la décision native et l'éventuelle surcharge,
afin de comprendre et maintenir mes choix avec la granularité fine demandée par `backlog-icebox.md` §1.

## Acceptance Criteria

1. **AC1 — Drill-down lecture seule commande par commande.**
   **Given** un équipement publié
   **When** l'utilisateur déplie le drill-down commande (niveau 4 `pièce -> équipement -> commande`)
   **Then** il voit, pour chaque commande retenue (`matched_commands`) ou rejetée (`unmatched_commands`) : le `generic_type` Jeedom, l'attendu HA, et la décision de mapping — en lecture seule pour les commandes non surchargées
   **And** ce niveau 4 ne pollue pas l'Epic 2 (santé du pont) ni ne modifie les statuts Epic 3 (niveau équipement), conformément aux garde-fous `backlog-icebox.md` §1 : les champs ajoutés sont strictement additifs sur les entrées `matched_commands[]` / `unmatched_commands[]`, sans altérer les champs 4D eq-level existants (`perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`).

2. **AC2 — Décision native vs décision surchargée.**
   **Given** un équipement avec override appliqué (mapping override Story 16.2 ou publication override Story 16.3)
   **When** l'utilisateur consulte le diagnostic
   **Then** il voit la décision native et la décision surchargée (les deux, distinctement)
   **And** le diagnostic conserve une cause principale canonique eq-level inchangée (la cause 4D n'est pas recalculée depuis le niveau commande)
   **And** les champs ajoutés sont additifs et compatibles avec le contrat 4D (`models/ui_contract_4d.py`).

3. **AC3 — "No faux CTA" (Epic 6) préservée.**
   **Given** un override sans remédiation utilisateur directe
   **When** la traduction `cause_label` / `cause_action` liée à l'override est construite
   **Then** la règle Epic 6 "no faux CTA" reste appliquée (`cause_action = None` quand il n'existe pas de remédiation directe)
   **And** toute traduction est centralisée dans `models/cause_mapping.py` (aucune chaîne FR dupliquée dans `http_server.py`).

4. **AC4 — Consommation stricte des reason_codes 16.3 (SCP 2026-07-07).**
   **Given** un override de publication acté en Story 16.3
   **When** le drill-down expose l'état override d'une commande / d'un équipement
   **Then** il consomme EXACTEMENT les reason_codes 16.3 — `publication_excluded_eqlogic`, `publication_excluded_command`, `publication_forced` — et les `reason_details` associés (`publication_override_applied`, `override_source`, `underlying_confidence`)
   **And** aucun nouveau reason_code recouvrant la même sémantique n'est introduit.

5. **AC5 — Non-régression additive prouvée.**
   **Given** le corpus de tests unitaires + golden snapshot existant
   **When** la story est implémentée
   **Then** la suite unitaire complète du daemon passe sans régression
   **And** le golden snapshot du diagnostic est réaligné (les nouveaux champs apparaissent, les champs existants sont inchangés)
   **And** le mode automatique (absence d'override) reste le comportement par défaut : les nouveaux champs override sont absents/neutres quand aucun override n'existe.

## Tasks / Subtasks

- [x] Task 1 — Attendu HA + décision native par commande (AC: #1)
  - [x] Enrichir chaque entrée de `matched_commands[]` et `unmatched_commands[]` (`http_server.py`) avec l'attendu HA via `resolve_expected_ha(eq, snapshot)` → champ `attendu_ha` (= `proposed_ha_entity_type`), + `mapping_decision` + `retained`.
  - [x] Ajouter la décision de mapping par commande : `matched` → type HA effectif (`retained=True`) ; `unmatched` → rejet explicite (`mapping_decision=None`, `retained=False`).
  - [x] `resolve_expected_ha` (fresh `MapperRegistry`) n'est invoqué QUE dans le cas override (rare) pour récupérer la décision native ; sinon `attendu_ha = ha_entity_type` effectif (pas de recompute).
- [x] Task 2 — Décision native vs surchargée (AC: #2, #4)
  - [x] Mapping override (Story 16.2) : lecture `reason_details.override_applied` / `override_source` ; exposition `type_override = {source, native, effective}` (native = moteur brut, effective = type surchargé).
  - [x] Publication override (Story 16.3) : `_build_publication_override_diag` consomme `publication_override_applied` / `override_source` / `underlying_confidence` + le reason_code 16.3 déjà porté (`publication_excluded_eqlogic` / `publication_excluded_command` / `publication_forced`) — aucun nouveau reason_code.
  - [x] Cause canonique eq-level 4D intacte (aucune dérivation depuis le niveau commande).
- [x] Task 3 — Traductions centralisées + no faux CTA (AC: #3)
  - [x] Aucune nouvelle étiquette FR nécessaire au niveau commande : les champs ajoutés sont des identifiants machine (types HA, sources) — pas de chaîne FR codée en dur dans `http_server.py`. La logique de cause/`cause_action` (no faux CTA) reste inchangée dans `models/cause_mapping.py`.
- [x] Task 4 — Tests unitaires + golden (AC: #5)
  - [x] Nouveau `resources/daemon/tests/unit/test_story_16_4_diagnostic_override_aware.py` : 4 tests (attendu HA + décision par commande ; native vs surchargée ; consommation reason_codes 16.3 ; commande rejetée lecture seule + additivité 4D).
  - [x] Golden snapshot réaligné via `GOLDEN_REGEN=1` (diff strictement additif : uniquement `attendu_ha` / `mapping_decision` / `retained`).
  - [x] Suite unitaire complète du daemon : **1028 passed, 0 régression**.

## Dev Notes

Story **lecture seule** (aucune capacité d'édition — l'édition arrive en 16b). Le drill-down commande est **additif** sur le contrat diagnostic existant : on enrichit les entrées `matched_commands[]` / `unmatched_commands[]` déjà produites par `GET /system/diagnostics`, sans toucher aux champs 4D eq-level.

**Point d'entrée exact (déjà présent, à enrichir) :**
- `resources/daemon/transport/http_server.py` — endpoint `GET /system/diagnostics`. Les listes par commande sont construites à `~2160-2186` (`matched_commands` = commandes mappées ; `unmatched_commands` = commandes couvrables `c.generic_type` non mappées) et rattachées à `eq_dict` à `2316-2317`. Chaque entrée porte déjà `cmd_id`, `cmd_name`, `generic_type` (+ éventuels `state_class` / `unit_of_measurement` / `streaming`). **On ajoute ici** `attendu_ha`, la décision native, et les champs override.

**Attendu HA par commande (réutiliser, ne pas réinventer) :**
- `resources/daemon/mapping/registry.py:132-189` — `resolve_expected_ha(eq, snapshot, cmd=None, *, registry=None) -> Dict` retourne `{eq_id, cmd_id, generic_type, proposed_ha_entity_type, compatible_ha_components, secondary_ha_entity_types, ...}`. `proposed_ha_entity_type` = attendu HA candidat moteur. Passer le `registry` déjà instancié pour l'équipement.

**Overrides (source de l'état natif vs surchargé) :**
- `resources/daemon/mapping/overrides.py` — mapping override (Story 16.2) : `apply_type_override(...)` pose `override_applied` + `override_source` dans `reason_details` (via `dataclasses.replace`). Publication override (Story 16.3) : `resolve_publication_override(...)` (précédence exclude-eqlogic > exclude-command > force > None).
- `resources/daemon/models/decide_publication.py` — reason_codes 16.3 : `publication_excluded_eqlogic`, `publication_excluded_command`, `publication_forced` ; `reason_details` : `publication_override_applied`, `override_source`, `underlying_confidence`. Invariants à respecter : I2 (`is_valid=False` jamais bypassé), I3 (`should_publish=True ⇒ ha_entity_type ∈ PRODUCT_SCOPE).

**Contrat 4D (ne pas casser) :**
- `resources/daemon/models/ui_contract_4d.py` — `perimetre` / `statut` / `ecart` / `cause_*` restent eq-level. Le niveau 4 commande est un enrichissement des sous-listes, il ne remonte pas dans les compteurs 4D (`build_ui_counters`) ni dans `compute_home_statut`.
- `resources/daemon/models/cause_mapping.py` — toute traduction FR override-aware passe ici (`_REASON_CODE_TO_CAUSE`, `resolve_cause_ux`). `cause_action=None` quand pas de remédiation directe (no faux CTA, Epic 6).

**Garde-fous `backlog-icebox.md` §1 (à respecter explicitement) :**
- Le drill-down commande est le niveau 4 (`pièce -> équipement -> commande`). Il ne doit PAS polluer l'Epic 2 (santé du pont MQTT) ni modifier les statuts Epic 3 (niveau équipement).
- Reste **lecture seule** tant que 16b (édition) n'est pas livré.

**Rappel gouvernance SCP 2026-07-07 (Story 16.3) :** le diagnostic override-aware consomme EXACTEMENT les reason_codes actés en 16.3 sans en introduire de nouveaux recouvrant la même sémantique. Réf. `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07-16-3-overrides-schema.md`.

### Dev Agent Guardrails

- Ne créer aucun nouveau reason_code : réutiliser strictement ceux de 16.3.
- Aucune chaîne FR codée en dur dans `http_server.py` : centraliser dans `cause_mapping.py`.
- Additivité stricte : ne pas modifier les clés existantes de `eq_dict` ni des entrées `matched_commands` / `unmatched_commands` ; uniquement en ajouter.
- Aucun override HA ne modifie le `generic_type` Jeedom natif (non-régression Homebridge — le drill-down l'expose mais ne le mute jamais).
- Aucun bypass de `validate_projection()` : le diagnostic reflète les décisions, il ne les recalcule pas hors moteur.

**Terrain :** validation primaire par tests unitaires + golden snapshot sur fixtures synthétiques (conforme AR13/FR40/NFR10 : 4D non-régression sur fixtures, box réelle non requise pour un enrichissement diagnostic lecture seule). Un gate terrain consolidé sur box réelle est cadré séparément en Story 16.7 ; ne pas déclencher de cycle disruptif ici.

### Project Structure Notes

- Fichiers touchés (attendu) : `resources/daemon/transport/http_server.py` (enrichissement des entrées commande), éventuellement `resources/daemon/models/cause_mapping.py` (nouvelles étiquettes override-aware), nouveau test `resources/daemon/tests/unit/test_story_16_4_diagnostic_override_aware.py`, réalignement golden (`tests/fixtures/golden_corpus/` + `test_story_8_4_golden_file.py`).
- Nommage test conforme au pattern maison : `test_story_<epic>_<story>_<sujet>.py`.
- Aucune modification de `resources/daemon/mapping/*` attendue (réutilisation de `resolve_expected_ha`).

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story 16.4] — définition, AC BDD, dev notes, garde-fous backlog-icebox §1.
- [Source: resources/daemon/transport/http_server.py:2140-2200] — construction `matched_commands` / `unmatched_commands`.
- [Source: resources/daemon/transport/http_server.py:2293-2330] — assemblage `eq_dict`, rattachement des sous-listes commande.
- [Source: resources/daemon/mapping/registry.py:132-189] — `resolve_expected_ha` (attendu HA par commande).
- [Source: resources/daemon/mapping/overrides.py] — `apply_type_override`, `resolve_publication_override`, `override_source`.
- [Source: resources/daemon/models/decide_publication.py] — reason_codes 16.3 + `reason_details` (`publication_override_applied`, `override_source`, `underlying_confidence`).
- [Source: resources/daemon/models/ui_contract_4d.py] — contrat 4D eq-level (à préserver).
- [Source: resources/daemon/models/cause_mapping.py] — traductions centralisées + no faux CTA.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07-16-3-overrides-schema.md] — SCP consommation stricte reason_codes 16.3.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (claude-cli)

### Debug Log References

- `python3 -m pytest tests/unit/test_story_16_4_diagnostic_override_aware.py -q` → 4 passed.
- `python3 -m pytest tests/unit -q` (pré-golden) → 1 failed (golden 8.4) / 1027 passed — dérive attendue, strictement additive.
- `GOLDEN_REGEN=1 python3 -m pytest tests/unit/test_story_8_4_golden_file.py` → régénération ; re-run → 1 passed.
- `python3 -m pytest tests/unit -q` (post-golden) → **1028 passed, 0 régression**.

### Completion Notes List

- create-story (BMAD) — 2026-07-17 — statut résultant : ready-for-dev. Ultimate context engine analysis completed - comprehensive developer guide created.
- dev-story (BMAD) — 2026-07-17 — statut résultant : review. Implémentation lecture seule, strictement additive sur `GET /system/diagnostics`.
  - `_enrich_command_drilldown` : ajoute `attendu_ha` / `mapping_decision` / `retained` sur chaque entrée `matched_commands` & `unmatched_commands` ; `type_override {source, native, effective}` uniquement quand override de type 16.2 appliqué.
  - `_build_publication_override_diag` : expose `publication_override {reason_code, override_source, underlying_confidence}` en consommant EXACTEMENT les reason_codes/reason_details 16.3, clé absente si aucun override (pas de clé nulle).
  - Aucun champ 4D eq-level modifié ; aucun nouveau reason_code introduit ; `generic_type` Jeedom natif jamais muté (non-régression Homebridge).
  - Décision native (pré-override) obtenue via `resolve_expected_ha` (moteur brut, sans override) — appelé seulement dans le cas override.

### File List

- `resources/daemon/transport/http_server.py` (modifié) — import `resolve_expected_ha` ; helpers `_enrich_command_drilldown` / `_build_publication_override_diag` ; câblage dans `_handle_system_diagnostics` ; clé additive `publication_override` sur `eq_dict`.
- `resources/daemon/tests/unit/test_story_16_4_diagnostic_override_aware.py` (nouveau) — 4 tests couvrant AC1/AC2/AC4 + additivité 4D.
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json` (régénéré) — champs additifs `attendu_ha` / `mapping_decision` / `retained`.
- `_bmad-output/implementation-artifacts/16-4-diagnostic-override-aware-drill-down.md` (story) — tasks cochées, Dev Agent Record.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 16-4 : backlog → ready-for-dev → in-progress → review.

### Change Log

- 2026-07-17 — Story 16.4 implémentée (dev-story BMAD) : drill-down diagnostic override-aware lecture seule, additif. 1 fichier code + 1 test + golden réaligné. 1028 tests passed.
