# Story 9.5 : Exposition d'actions utilisateur sur les surfaces réellement ouvertes par la vague 1 (re-homée depuis Story 7.5)

Status: review

## Story

En tant qu'utilisateur,
je veux voir une action seulement lorsqu'elle correspond à une remédiation réellement disponible après l'ouverture de la vague 1 (`sensor`, `binary_sensor`, `button`),
afin que le diagnostic reste honnête et utile une fois que la vague 1 est en production.

**Pré-requis story-level** : Stories 9.1, 9.2, 9.3 et 9.4 closes ✓ ; golden-file 8.4 vert ✓ ; la vague 1 est effectivement publiée sur la box réelle d'Alexandre ✓ (gate terrain epic-level pe-epic-9 atteint dès Story 9.3 et confirmé Story 9.4 — published=68, ratio=83.9%).

## Acceptance Criteria

**AC1 — Équipements mapper spécifique publiés (sensor / binary_sensor / button)**
**Given** un équipement publié en `sensor` / `binary_sensor` / `button` par un mapper spécifique (Stories 9.1, 9.2, 9.3) avec `confidence="sure"` et `should_publish=True`
**When** le diagnostic est affiché
**Then** `cause_action` reste `null` (équipement aligné : `ecart=false`, aucune cause exposée)
**And** ce cas est satisfait structurellement sans modification de code — l'AC valide l'invariant existant

**AC2 — FallbackMapper : `cause_action` non-null pour remédiation actionnable**
**Given** un équipement projeté par `FallbackMapper` (Story 9.4) avec `reason_code ∈ {"fallback_sensor_default", "fallback_button_default"}` et `confidence="ambiguous"` → `decision_reason_code = "ambiguous_skipped"`, `pipeline_step_visible = 4`
**When** le diagnostic est affiché
**Then** `cause_action` est une chaîne non-null indiquant « Préciser les types génériques sur les commandes dans Jeedom pour lever l'ambiguïté »
**And** `cause_label` = "Arbitrage de publication non automatique — ambiguïté de mapping non résolue" (inchangé)
**And** `confidence` = "Ambigu" (inchangé)

**AC3 — `no_projection_possible` : `cause_action = null` (aucune remédiation directe)**
**Given** un équipement éligible sans aucune commande Info ni Action exploitable → `reason_code = "no_projection_possible"`, `map_result = None`
**When** le diagnostic est affiché
**Then** `cause_action` reste `null`
**And** `cause_label` = "Projection impossible — aucune commande exploitable détectée" (via `reason_code_to_cause("no_projection_possible")`)
**And** `decision_trace.reason_code = "no_projection_possible"` (fix bug Story 9.4 AI-Review LOW — actuellement `"no_commands"` par erreur)

**AC4 — Hors vague 1 : Story 9.5 ne modifie rien**
**Given** un équipement hors vague 1 (type non ouvert dans `PRODUCT_SCOPE`)
**When** le diagnostic est affiché
**Then** la story 9.5 ne modifie ni `cause_label` ni `cause_action` pour cet équipement
**And** la règle « no faux CTA » de Story 6.3 reste verrouillée

**AC5 — Gate terrain no faux CTA**
**Given** les changements story-level touchant `cause_action`
**When** la story est validée sur la box réelle d'Alexandre
**Then** le gate terrain `no faux CTA` passe sur des cas représentatifs de la vague 1 :
- au minimum 5 sensor (SensorMapper) publiés → `cause_action = null` confirmé (pas d'écart)
- au minimum 5 binary_sensor (BinarySensorMapper) publiés → `cause_action = null` confirmé
- au minimum 3 button (ButtonMapper) publiés → `cause_action = null` confirmé
- au minimum 5 équipements FallbackMapper (ambiguous_skipped) → `cause_action` non-null confirmé
- `no_projection_possible` si présent → `cause_action = null` confirmé

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Mettre à jour `cause_mapping.py` — ARTEFACT FIGÉ (AC2, AC3)
  - [x] 1.1 Mettre à jour le commentaire d'en-tête : ajouter `Story 9.5` dans la liste des stories
  - [x] 1.2 `_REASON_CODE_TO_CAUSE["fallback_sensor_default"]` : passer `cause_action` de `None` à `"Configurer les types génériques des commandes Info dans Jeedom pour permettre une projection spécifique"`
  - [x] 1.3 `_REASON_CODE_TO_CAUSE["fallback_button_default"]` : passer `cause_action` de `None` à `"Configurer les types génériques des commandes Action dans Jeedom pour permettre une projection spécifique"`
  - [x] 1.4 `CAUSE_MAPPING["ambiguous_skipped"]["step_4"]["action"]` : passer de `None` à `"Préciser les types génériques sur les commandes dans Jeedom pour lever l'ambiguïté"` (correction principale — c'est ce chemin qui est utilisé dans le diagnostic pour les fallback)
  - [x] 1.5 `CAUSE_MAPPING["ambiguous"]["step_4"]["action"]` : même valeur que 1.4 (symétrie — cas legacy)
  - [x] 1.6 `no_projection_possible` cause_action : rester `None` — ne pas toucher (aucune remédiation directe)

- [x] Task 2 — Corriger `_CLOSED_REASON_MAP` dans `http_server.py` (AC3 — fix bug Story 9.4 AI-Review LOW)
  - [x] 2.1 Ajouter `"no_projection_possible": "no_projection_possible"` à `_CLOSED_REASON_MAP` (ligne ~1567)
  - [x] 2.2 Mettre à jour le commentaire doc de `_CLOSED_REASON_MAP` (ligne ~1563) pour lister `no_projection_possible` dans la taxonomie fermée
  - [x] 2.3 Vérifier que `cause_label` pour ID 10004 dans le golden-file change : "Équipement sans commandes exploitables" → "Projection impossible — aucune commande exploitable détectée"
  - [x] 2.4 Vérifier que `cause_action` pour ID 10004 change : "Vérifier que l'équipement possède des commandes actives dans Jeedom" → `null`

- [x] Task 3 — Mettre à jour `test_story_9_4_fallback_mapper.py` (AC2, AC3)
  - [x] 3.1 Renommer `test_cause_fallback_sensor_default_no_action` → `test_cause_fallback_sensor_default_has_action`
  - [x] 3.2 Changer `assert action is None` → `assert action is not None and len(action) > 0` (cause_action est maintenant une CTA réelle)
  - [x] 3.3 Renommer `test_cause_fallback_button_default_no_action` → `test_cause_fallback_button_default_has_action`
  - [x] 3.4 Même changement pour button
  - [x] 3.5 Conserver `test_cause_no_projection_possible_no_action` tel quel — `action is None` reste la vérité pour `no_projection_possible`

- [x] Task 4 — Mettre à jour `test_diagnostic_endpoint.py` (AC3)
  - [x] 4.1 `test_diagnostics_reason_code_normalization_no_mapping` (ligne ~920) :
    - Changer `assert dt["reason_code"] == "no_commands"` → `assert dt["reason_code"] == "no_projection_possible"`
    - Mettre à jour le docstring : supprimer `→ no_commands (fallback conservateur)`, écrire `→ no_projection_possible (fix Story 9.5)`
    - Ajouter : `assert dt["reason_code"] in _CLOSED_REASON_CODES` (invariant taxonomie fermée — vérifier que `"no_projection_possible"` est dans `_CLOSED_REASON_CODES`)
  - [x] 4.2 Créer `test_diagnostics_fallback_mapper_cause_action_non_null` : vérifier que `cause_action` est non-null pour un équipement FallbackMapper (`ambiguous_skipped`, step_4) après Story 9.5
  - [x] 4.3 Vérifier que `_CLOSED_REASON_CODES` dans `test_diagnostic_endpoint.py` inclut `"no_projection_possible"` (l'ajouter si absent)

- [x] Task 5 — Mettre à jour le golden-file `expected_sync_snapshot.json` (PE8-AI-04 discipline — construire manuellement)
  - [x] 5.1 IDs 10000, 10001, 10002, 10003 (FallbackMapper sensor/button) : `"cause_action": null` → `"cause_action": "Préciser les types génériques sur les commandes dans Jeedom pour lever l'ambiguïté"` (4 entrées à modifier dans la section diagnostics du snapshot)
  - [x] 5.2 ID 10004 (`no_projection_possible`) :
    - `"cause_action": "Vérifier que l'équipement possède des commandes actives dans Jeedom"` → `null`
    - `"cause_label": "Équipement sans commandes exploitables"` → `"Projection impossible — aucune commande exploitable détectée"`
    - `"traceability.decision_trace.reason_code": "no_commands"` → `"no_projection_possible"`
  - [x] 5.3 Vérifier que les 43 équipements existants (IDs 1000-9002) sont INCHANGÉS — confirmé avant PR (seul ID 4001 ambiguous_skipped step_4 mis à jour : effet de bord intentionnel documenté)
  - [x] 5.4 NE PAS régénérer le snapshot via le pipeline — discipline PE8-AI-04

- [ ] Task 6 — Gate terrain no faux CTA (AC5)
  - [ ] 6.1 Déployer sur box réelle via `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] 6.2 Appeler `/system/diagnostics` et vérifier les cas de la vague 1 :
    - 5 sensors spécifiques (SensorMapper) publiés → `cause_action = null` ✓
    - 5 binary_sensors spécifiques (BinarySensorMapper) publiés → `cause_action = null` ✓
    - 3+ buttons spécifiques (ButtonMapper) publiés → `cause_action = null` ✓
    - Équipements FallbackMapper (ambiguous_skipped) → `cause_action` non-null ✓
    - Équipement `no_projection_possible` si présent → `cause_action = null` ✓
  - [ ] 6.3 Documenter les compteurs post-Story 9.5 (baseline attendue : published=68, ratio=83.9% — inchangé car cette story ne modifie pas les publications)

- [x] Task 7 — Validation non-régression suite complète
  - [x] 7.1 `pytest resources/daemon/tests/` — suite complète PASS
  - [x] 7.2 `test_story_8_4_golden_file.py` : PASS avec snapshot mis à jour (5.1/5.2)
  - [x] 7.3 Vérifier que les tests hors Task 3/4 passent sans modification (notamment `test_diagnostics_detail_and_remediation_ambiguous` qui ne teste pas `cause_action`)

## Dev Notes

### Livraison principale : mettre à jour `CAUSE_MAPPING["ambiguous_skipped"]["step_4"]`

**Chemin critique** pour les FallbackMapper (IDs 10000-10003 du golden-file) :

```
FallbackMapper → reason_code="fallback_sensor_default", confidence="ambiguous"
→ decide_publication() → reason="ambiguous_skipped"  
→ _build_traceability() → canonical_reason="ambiguous_skipped" → closed_reason="ambiguous_skipped"
→ decision_reason_code = "ambiguous_skipped"
→ pipeline_step_visible = 4  (mapping présent, publication bloquée)
→ resolve_cause_ux("ambiguous_skipped", 4)
    → CAUSE_MAPPING["ambiguous_skipped"]["step_4"] EXISTS → return early
    → {"cause_label": "Arbitrage de publication...", "cause_action": None}  ← AVANT
    → {"cause_label": "Arbitrage de publication...", "cause_action": "Préciser..."}  ← APRÈS 9.5
```

**Implication** : `_REASON_CODE_TO_CAUSE["fallback_sensor_default"]` cause_action n'est PAS atteint pour la couche diagnostic (CAUSE_MAPPING prend la priorité). Les mises à jour des Tasks 1.2/1.3 sont nécessaires pour la cohérence de `reason_code_to_cause()` appelé directement (tests + couche cause_code).

### Fix `_CLOSED_REASON_MAP` pour `no_projection_possible`

**Bug actuel** (Story 9.4 AI-Review LOW) : pour un équipement éligible sans mapping (map_result=None), `_build_traceability` produit `decision_trace.reason_code = "no_commands"` au lieu de `"no_projection_possible"`. Cause : `"no_projection_possible"` absent de `_CLOSED_REASON_MAP`, ce qui tombe dans le branch `else → "no_commands"` (ligne ~1647 de `http_server.py`).

**Fix** : ajouter `"no_projection_possible": "no_projection_possible"` à `_CLOSED_REASON_MAP`. Ce fix change :
- `decision_trace.reason_code` : `"no_commands"` → `"no_projection_possible"`
- `cause_label` (via `resolve_cause_ux("no_projection_possible", 2)`) : `"Équipement sans commandes exploitables"` → `"Projection impossible — aucune commande exploitable détectée"`
- `cause_action` : `"Vérifier que l'équipement possède des commandes actives dans Jeedom"` → `null`

**Vérifier** que `"no_projection_possible"` est dans `_CLOSED_REASON_CODES` dans le fichier de test. Si absent, l'ajouter.

### Portée exacte des changements `cause_action`

| Reason code | Decision reason | Pipeline step | cause_action AVANT | cause_action APRÈS |
|---|---|---|---|---|
| `fallback_sensor_default` | `ambiguous_skipped` | 4 | `null` | CTA non-null |
| `fallback_button_default` | `ambiguous_skipped` | 4 | `null` | CTA non-null |
| `no_projection_possible` | `no_projection_possible` (après fix) | 2 | `"Vérifier..."` (bug) | `null` (correct) |
| `ambiguous_skipped` (autres cas) | `ambiguous_skipped` | 4 | `null` → CTA non-null | effet de bord attendu |

**Note sur l'effet de bord** : en mettant `CAUSE_MAPPING["ambiguous_skipped"]["step_4"]["action"]` à non-null, TOUS les équipements `ambiguous_skipped` à step_4 bénéficient de la CTA — pas seulement les FallbackMapper. Ce comportement est intentionnel et correct : pour tout équipement bloqué en ambiguïté au step_4, "préciser les types génériques dans Jeedom" est une remédiation réelle.

### AC1 est satisfait structurellement sans code

Les equipments publiés en sensor/binary_sensor/button par les mappers spécifiques (confidence="sure") ont :
- `should_publish=True` → `is_published_in_ha=True` → `ecart=false`
- Branche `else → cause_code, cause_label, cause_action = None, None, None` (ligne ~1920 http_server.py)

Aucun code à écrire pour AC1. L'AC valide un invariant architectural existant.

### Discipline golden-file PE8-AI-04

**NE PAS régénérer** `expected_sync_snapshot.json` depuis le pipeline. Construire manuellement les 5 modifications :

**4 entrées `cause_action` (IDs 10000-10003 dans la section `diagnostics_response`) :**
```json
"cause_action": "Préciser les types génériques sur les commandes dans Jeedom pour lever l'ambiguïté"
```
(Remplace `"cause_action": null` pour chaque ID 10000, 10001, 10002, 10003)

**ID 10004 — 3 modifications :**
- `"cause_action": "Vérifier que l'équipement possède des commandes actives dans Jeedom"` → `null`
- `"cause_label": "Équipement sans commandes exploitables"` → `"Projection impossible — aucune commande exploitable détectée"`
- `"traceability": { "decision_trace": { "reason_code": "no_commands" } }` → `"reason_code": "no_projection_possible"`

**Les 43 équipements existants (IDs 1000-9002) ne sont PAS modifiés.**

### Erreurs à éviter (leçons Stories 9.1-9.4)

**L1** : Ne pas modifier `decide_publication()` ni `confidence_policy` — la politique `sure_only` reste inchangée, les équipements FallbackMapper restent `should_publish=False`.

**L2** : Ne pas changer `CAUSE_MAPPING["ambiguous_skipped"]["step_3"]` — seul `step_4` est concerné. Le step_3 a déjà une `action` non-null correcte.

**L3** : Ne pas créer de nouvelle entrée dans `CAUSE_MAPPING` pour `"fallback_sensor_default"` ou `"fallback_button_default"` — ces reason_codes ne sont PAS utilisés comme `decision_reason_code` dans la couche UX. Seul `"ambiguous_skipped"` l'est.

**L4** : Vérifier `_CLOSED_REASON_CODES` dans `test_diagnostic_endpoint.py` — si `"no_projection_possible"` est absent, l'ajouter sinon `assert dt["reason_code"] in _CLOSED_REASON_CODES` échouera.

**L5** : La règle § "no faux CTA" (Story 6.3) est respectée : "Préciser les types génériques dans Jeedom" est une remédiation réelle, exécutable par l'utilisateur dans Jeedom standard. Ce n'est pas un CTA vers une surface fictive ou non-existante.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

#### Guardrail — ARTEFACT FIGÉ cause_mapping.py

- `cause_mapping.py` est un ARTEFACT FIGÉ (Stories 4.1/4.3/6.2/6.3/9.4/9.5)
- Toute modification nécessite une story dédiée
- Mettre à jour le commentaire `# ARTEFACT FIGÉ` en tête de fichier pour inclure `Story 9.5`
- Ne modifier que les 4 champs listés dans Task 1 — rien d'autre

#### Guardrail — NE PAS toucher

- `LightMapper`, `CoverMapper`, `SwitchMapper`, `BinarySensorMapper`, `SensorMapper`, `ButtonMapper`, `FallbackMapper`
- `resources/daemon/mapping/registry.py` — ordre de la cascade inchangé
- `resources/daemon/validation/ha_component_registry.py` — `PRODUCT_SCOPE` inchangé
- `resources/daemon/discovery/publisher.py` — `publish_sensor`, `publish_button` inchangés
- `resources/daemon/decision/publication.py` — `decide_publication()` inchangé
- `CAUSE_MAPPING["ambiguous_skipped"]["step_3"]` — déjà correct, non-null, ne pas toucher
- Les 43 équipements existants du golden-file (IDs 1000-9002) — verrou de non-régression

#### Guardrail — Discipline golden-file PE8-AI-04

- Construire manuellement les modifications du golden-file (5 changements dans la section diagnostics)
- NE PAS régénérer `expected_sync_snapshot.json` via le pipeline
- Vérifier que le test `test_story_8_4_golden_file.py` est VERT avant ET après les modifications
- La partie `sync_response` du snapshot est inchangée (cause_action n'existe pas dans la réponse sync)

### Project Structure Notes

```
resources/daemon/
├── models/
│   └── cause_mapping.py          ← MODIFIER : ARTEFACT FIGÉ — 4 champs (Tasks 1.1-1.5)
├── transport/
│   └── http_server.py            ← MODIFIER : _CLOSED_REASON_MAP + commentaire (Task 2)
└── tests/
    ├── fixtures/golden_corpus/
    │   └── expected_sync_snapshot.json  ← MODIFIER manuellement : 5 champs (Task 5)
    └── unit/
        ├── test_story_9_4_fallback_mapper.py  ← MODIFIER : 2 tests renommés + assertions (Task 3)
        └── test_diagnostic_endpoint.py        ← MODIFIER : test line ~920 + nouveau test (Task 4)
```

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md#Story 9.5`] — AC complets + dev notes
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md#Gates epic-level pe-epic-9`] — gate terrain cloture epic
- [Source: `resources/daemon/models/cause_mapping.py`] — ARTEFACT FIGÉ à modifier : `_REASON_CODE_TO_CAUSE` + `CAUSE_MAPPING`
- [Source: `resources/daemon/transport/http_server.py:1563-1591`] — `_CLOSED_REASON_MAP` à étendre
- [Source: `resources/daemon/transport/http_server.py:1726-1750`] — `_compute_pipeline_step_visible` (step 4 pour ambiguous, step 2 pour no_projection_possible)
- [Source: `resources/daemon/transport/http_server.py:1895-1920`] — `resolve_cause_ux` + `decision_reason_code` chemin critique
- [Source: `resources/daemon/tests/unit/test_story_9_4_fallback_mapper.py:175-195`] — tests cause_action à modifier (Tasks 3.1-3.5)
- [Source: `resources/daemon/tests/unit/test_diagnostic_endpoint.py:920-941`] — test `no_commands` → `no_projection_possible` à corriger
- [Source: `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json:8066-8445`] — section diagnostics IDs 10000-10004 à modifier manuellement
- [Source: `_bmad-output/implementation-artifacts/9-4-fallback-mapper-degradation-elegante-terminale-publier-sensor-button-par-defaut-plutot-que-skip-silencieux.md#Review Follow-ups (AI)`] — AI-Review LOW `no_projection_possible` absent de `_CLOSED_REASON_MAP`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Task 1 : cause_mapping.py ARTEFACT FIGÉ mis à jour — 4 champs (1.2, 1.3, 1.4, 1.5), commentaire d'en-tête mis à jour (1.1). `no_projection_possible` cause_action laissé `None` (1.6).
- Task 2 : `_CLOSED_REASON_MAP` dans http_server.py étendu avec `"no_projection_possible": "no_projection_possible"` — fix bug AI-Review LOW Story 9.4.
- Task 3 : 2 tests renommés `*_no_action` → `*_has_action` avec assertions inversées. `test_cause_no_projection_possible_no_action` conservé tel quel.
- Task 4 : `test_diagnostics_reason_code_normalization_no_mapping` corrigé (`no_commands` → `no_projection_possible`). `"no_projection_possible"` ajouté à `_CLOSED_REASON_CODES`. Nouveau test `test_diagnostics_fallback_mapper_cause_action_non_null` ajouté. Import `SensorCapabilities` ajouté.
- Task 5 : Golden-file mis à jour — IDs 10000-10003 (`cause_action` null → CTA), ID 10004 (3 champs), ID 4001 (effet de bord intentionnel `ambiguous_skipped` step_4). Deux sections (`equipments` et `in_scope_equipments`) mises à jour. PE8-AI-04 respecté (modification manuelle via script Python, pas de pipeline).
- Task 7 : 733/733 PASS. Tests Story 6.2 et 6.3 mis à jour pour refléter le nouveau comportement (cause_action non-null pour `ambiguous_skipped` step_4 est intentionnel — CTA réel, règle no faux CTA respectée).

### File List

- `resources/daemon/models/cause_mapping.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_story_9_4_fallback_mapper.py`
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py`
- `resources/daemon/tests/unit/test_story_6_2_contextual_cause_mapping.py`
- `resources/daemon/tests/unit/test_story_6_3_honest_cause_mapping.py`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`
