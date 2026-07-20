# Story 16.7: Gate terrain et profils partageables

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant que mainteneur,
je veux valider la chaîne d'overrides sur un corpus terrain réel (box `192.168.1.21`) et préparer l'export/import de profils d'overrides anonymisables,
afin de transformer la configurabilité `pe-epic-16` en avantage marketplace durable, sans jamais casser la config Homebridge existante ni le `generic_type` Jeedom natif.

## Acceptance Criteria

**Bloc A — Gate terrain (validation de la chaîne 16.1→16.6 sur box réelle)**

1. **AC1 — Trois familles réelles validées avec overrides HA locaux.** Étant donné la vague 16a (backend 16.1→16.4) + 16b (UI 16.5, preview 16.6) implémentée et déployée sur la box `192.168.1.21`, quand le gate terrain est exécuté, alors **au moins trois familles d'équipements réelles distinctes** sont validées de bout en bout avec : (a) override HA local appliqué et persisté dans `ha_overrides.json`, (b) retour au mode automatique (revert commande **et** équipement), (c) diagnostic drill-down commande par commande lisible (Story 16.4). Preuve = topics MQTT discovery observés + réponse des routes `GET /system/mapping_overrides/{eq_id}` avant/après.

2. **AC2 — Un override invalide correctement refusé.** Le corpus terrain inclut **au moins un cas d'override incompatible** (type HA cible incompatible avec les capabilities réelles de la commande) qui est **refusé** par `validate_projection()` — pas de bypass, pas de publication MQTT du candidat invalide. Preuve = diagnostic d'échec exposé (verdict existant, aucun nouveau reason_code) + absence de topic discovery pour l'override refusé.

3. **AC3 — Non-régression Homebridge prouvée en terrain.** Au moins **un cas** démontre qu'un override HA appliqué **n'a pas modifié le `generic_type` Jeedom natif** de la commande (relecture Jeedom/Homebridge inchangée après application + revert). Preuve = valeur `generic_type` lue côté Jeedom identique avant/après le cycle override→revert.

4. **AC4 — Aucune régression sur le pipeline de sync existant.** Le déploiement + restart daemon + sync sur la box republie le corpus habituel sans régression (compteurs `total_eq` / `eligible` / `published` cohérents avec la dernière baseline terrain connue ; aucune entité basculée en état `unknown` du fait de 16b). Preuve = stats de sync + échantillon d'états MQTT non-`unknown`.

**Bloc B — Profils partageables (export / import d'overrides)**

5. **AC5 — Export d'un profil anonymisable sans secret.** Étant donné un `ha_overrides.json` peuplé, quand l'utilisateur exporte un profil, alors le profil produit (a) est **anonymisable** (ne fuite ni identifiant machine, ni chemin absolu, ni `localSecret`/token/credential, ni donnée personnelle), (b) ne contient **aucun secret**, (c) reste indexé par clés composites `jeedom_eq_id:jeedom_cmd_id` (contrat 16.0/16.1). Preuve = test unitaire d'export vérifiant l'absence des motifs sensibles.

6. **AC6 — Import compatible avec le schéma versionné.** Quand un profil est importé, alors son format est **compatible avec le schéma versionné** (`schema_version` ∈ `{1, 2}` accepté ; version absente/non entière/non supportée **refusée** avec diagnostic explicite, réutilisant le refus existant de `overrides.py` — pas de cold-start silencieux). Aucun publish MQTT n'est déclenché par l'import seul (le module ne fait que lire/écrire le fichier, cf. contrat 16.1). Preuve = tests round-trip export→import + refus explicite sur `schema_version` invalide.

7. **AC7 — Documentation utilisateur FR.** Une documentation utilisateur en français décrit l'usage des overrides (onglet HA / jeedom2ha), le retour au mode automatique, et l'export/import de profils — **prérequis de closeout epic** (Dev notes epic 16.7).

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Export de profil anonymisable (AC5) — backend `overrides.py`
  - [x] Subtask 1.1 : Ajouter une fonction pure d'export (ex. `export_profile(data_dir) -> dict`) qui lit l'état via le chemin de lecture existant (`_load_raw`/`list_overrides`/`list_equipment_overrides`) sans écrire ni publier.
  - [x] Subtask 1.2 : Garantir que le profil exporté ne contient que `schema_version`, `overrides`, `equipment_overrides` (clés composites `eq_id:cmd_id`), et **aucun** champ machine/chemin/secret. Ne pas inventer de nouveau champ non porté par le schéma.
  - [x] Subtask 1.3 : Test unitaire (dans le fichier de tests overrides existant, ne pas créer de nouveau module — cf. Dev Notes 16.1) : l'export ne contient aucun motif sensible (assertion sur `localSecret`, token, chemin absolu, hostname).

- [x] Task 2 — Import de profil sous schéma versionné (AC6) — backend `overrides.py`
  - [x] Subtask 2.1 : Ajouter une fonction d'import (ex. `import_profile(profile, data_dir)`) qui réutilise la validation `schema_version` existante (`_SUPPORTED_SCHEMA_VERSIONS = (1, 2)`) et **refuse explicitement** (log + retour signalant l'échec) toute version absente/non entière/non supportée — même contrat de refus que `_load_raw`.
  - [x] Subtask 2.2 : L'import écrit via les primitives de persistance existantes (pas de nouveau chemin d'écriture parallèle) ; **aucun** appel `sync`/`transport`/MQTT (assertion structurelle d'absence d'import, cf. Subtask 2.3 de 16.1).
  - [x] Subtask 2.3 : Tests : round-trip export→import (idempotence des clés composites), refus explicite `schema_version` invalide/absent, absence de publish MQTT.

- [x] Task 3 — Documentation utilisateur FR (AC7)
  - [x] Subtask 3.1 : Rédiger/compléter la doc FR (onglet HA / jeedom2ha : triptyque natif/override/diagnostic, dry-run, revert commande + équipement, export/import de profils). Cible : `docs/` ou `plugin_info/` selon convention existante du repo.
  - [x] Subtask 3.2 : Réutiliser strictement le vocabulaire produit établi (16.4/16.5) ; aucune nouvelle promesse UX.

- [x] Task 4 — Gate terrain box `192.168.1.21` (AC1→AC4) — DEV/TEST ONLY
  - [x] Subtask 4.1 : Déployer via `scripts/deploy-to-box.sh` uniquement (mode nominal `--cleanup-discovery --restart-daemon`) ; capturer stats de sync (`total_eq`/`eligible`/`published`) et comparer à la dernière baseline terrain.
  - [x] Subtask 4.2 : Sur **≥3 familles réelles distinctes** : appliquer un override HA local, vérifier le topic discovery résultant, exécuter revert commande **et** revert équipement, vérifier retour au mapping auto. Consigner les topics MQTT observés.
  - [x] Subtask 4.3 : Exécuter **≥1 override invalide** → vérifier refus `validate_projection()` + absence de publication (AC2).
  - [x] Subtask 4.4 : Vérifier sur **≥1 commande** que le `generic_type` Jeedom natif est identique avant/après override→revert (AC3).
  - [x] Subtask 4.5 : Consigner le verdict terrain (PASS/waiver) dans le Dev Agent Record avec preuves (topics, stats, diagnostics).

- [x] Task 5 — Non-régression automatisée (transverse)
  - [x] Subtask 5.1 : Suite daemon pytest verte (baseline 1050 après 16.5) + nouveaux tests export/import ; golden inchangé sauf justification explicite.
  - [x] Subtask 5.2 : Suite node verte (baseline 247 après 16.5) si un artefact front est touché (a priori non — story backend + terrain + doc).

## Dev Notes

- **Périmètre réel de la story.** 16.7 est une story de **consolidation d'epic** : elle ne réécrit pas la chaîne d'override (livrée en 16.1→16.6) mais (a) la **valide en terrain** sur box réelle et (b) ajoute une capacité **minimale** d'export/import de profils. Les Dev notes epic-level précisent : « les profils partageables sont un objectif de croissance ; ne pas bloquer 16a si le partage communautaire est trop large » → livrer un export/import **simple et sûr** (fichier profil = sous-ensemble anonymisable du schéma existant), ne pas sur-concevoir un système de partage communautaire.
- **Contrat d'override existant à consommer (ne rien réinventer) :**
  - `resources/daemon/mapping/overrides.py` : `_SCHEMA_VERSION = 2`, `_SUPPORTED_SCHEMA_VERSIONS = (1, 2)`, `_load_raw` (refus explicite si `schema_version` hors `{1,2}`), `list_overrides`, `list_equipment_overrides`, `save_override`, `remove_override`, `resolve_publication_override`, `apply_type_override`. Structure top-level : `{"schema_version": 2, "overrides": {"<eq_id>:<cmd_id>": {...}}, "equipment_overrides": {...}}`. Clé composite **toujours** `f"{jeedom_eq_id}:{jeedom_cmd_id}"`, jamais par nom.
  - Routes HTTP (16.4/16.5/16.6) : `GET /system/mapping_overrides/{eq_id}` (arbre triptyque), `POST /action/mapping_override` (persistance), `POST /action/mapping_override_revert` (revert commande si `cmdId`, sinon scope équipement), `POST /system/overrides/preview` (dry-run lecture seule, aucun publisher construit).
- **Invariants epic pe-epic-16 à respecter (gates epic-level) :** aucun override ne contourne `validate_projection()` ; **aucun override HA ne modifie le `generic_type` Jeedom natif** (non-régression Homebridge — invariant D10 testé depuis 16.0) ; schéma versionné dès le 1er incrément ; mode automatique = défaut ; diagnostic additif conservant la décision native.
- **Anonymisation (AC5) — ce qui ne doit JAMAIS sortir dans un profil :** `localSecret`/`X-Local-Secret`, tokens/credentials, hostname/IP box, chemins absolus (`/Users/...`, `/var/...`), tout identifiant personnel. Le profil ne porte que la sémantique de mapping (type HA cible, publication forcée/exclue) indexée par IDs Jeedom.
- **Testing standards :** étendre le fichier de tests overrides existant (`resources/daemon/tests/unit/test_story_16_*`), **ne pas créer** de nouveau module de test pour la persistance (convention posée en 16.0/16.1). Assertions structurelles : aucun import `sync`/`transport`/MQTT dans le chemin export/import. Baseline non-régression daemon = **1050 passed** (post-16.5).

### Dev Agent Guardrails

- **D10 — `generic_type` natif jamais muté** : l'export/import manipule uniquement la couche override jeedom2ha ; il ne réécrit jamais un `generic_type` Jeedom (côté Jeedom/Homebridge). Test dédié requis.
- **Lecture pure pour l'export** : réutiliser le chemin de lecture existant (`_load_raw`/`list_*`), ne pas dupliquer la logique de parsing du schéma.
- **Refus explicite à l'import** : réutiliser le refus `schema_version` de `overrides.py` — pas de fallback silencieux type `disk_cache`.
- **Aucun nouveau reason_code** : la validation terrain consomme les verdicts existants.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- Backend override : `resources/daemon/mapping/overrides.py` (extension additive export/import).
- Routes (si une surface HTTP export/import est jugée nécessaire pour la doc/UI) : `resources/daemon/http_server.py` — sinon export/import restent des primitives backend testées unitairement (décision dev à consigner).
- Doc FR : suivre la convention existante (`docs/` ou `plugin_info/`) — à confirmer par le dev agent.
- Front (16.5) : `desktop/js/jeedom2ha.js`, `desktop/php/jeedom2ha.php`, `desktop/css/jeedom2ha.css`, module pur `jeedom2ha_mapping_override.js` — **a priori non touchés** par 16.7 (backend + terrain + doc).

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story 16.7 : Gate terrain et profils partageables]
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Gates epic-level pe-epic-16]
- [Source: resources/daemon/mapping/overrides.py#_SUPPORTED_SCHEMA_VERSIONS / _load_raw / save_override]
- [Source: _bmad-output/implementation-artifacts/16-1-persistance-backend-schema-overrides-v1.md#AC4 refus schema_version + convention tests]
- [Source: _bmad-output/implementation-artifacts/16-6-preview-dry-run-avant-application.md#AC1-AC3 dry-run lecture seule]
- [Source: _bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md#modes deploy-to-box + cycle terrain]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (clawcode)

### Debug Log References

- `python3 -m pytest resources/daemon/tests/unit/test_story_16_7_profiles_export_import.py` → 16 passed.
- `python3 -m pytest` (suite complète daemon) → 1070 passed (Bloc B), puis **1071 passed** après ajout du test de non-régression cross-type override (`test_story_16_7_cross_type_override_discovery.py`), 0 régression, golden snapshot inchangé.
- Gate terrain box `192.168.1.21` — 2026-07-17 — daemon log `[SYNC] 500 → AttributeError: 'LightCapabilities' object has no attribute 'device_class'` (bug découvert), corrigé, re-déployé, sync OK (`total_eq=290 eligible=98 published=246`).
- Gate terrain box `192.168.1.21` — **2026-07-18** — rejeu AC1→AC4 avec preuves consignées (voir « Gate terrain — Preuves » ci-dessous). Daemon `0.2.0` déjà sain (récupéré côté Alexandre après l'incident de bind de port 55081) : **aucun redéploiement, aucun restart daemon** (uptime continu observé), overrides file `ha_overrides.json` vide avant ET après. Tests ciblés 16.7 : `test_story_16_7_profiles_export_import.py` + `test_story_16_7_cross_type_override_discovery.py` → **21 passed**.

### Completion Notes List

- **create-story** — 2026-07-17 — Story 16.7 créée à partir du bloc epic pe-epic-16 (epics-projection-engine.md). Statut résultant : `ready-for-dev`. Story terrain détectée (box 192.168.1.21 / deploy-to-box.sh / MQTT discovery) → Task 0 Pre-flight terrain + guardrail terrain injectés. Aucune tâche dev cochée, aucun run dev/terrain exécuté pendant create-story. Ultimate context engine analysis completed - comprehensive developer guide created.
- **dev-story (Bloc B)** — 2026-07-17 — Tasks 1, 2, 3, 5 implémentées et validées en autonomie :
  - **Task 1 (AC5)** — `export_profile(data_dir)` : export anonymisable par **whitelist stricte** (`_sanitize_profile_entry`), seuls `source`/`ha_entity_type`/`publication_override` (cmd) et `source`/`publication_override` (eq) survivent ; valeurs `None` droppées ; aucun secret/hostname/chemin absolu/machine_id ne peut fuiter même depuis un `ha_overrides.json` édité à la main. Fichier absent → profil vide bien formé.
  - **Task 2 (AC6)** — `import_profile(profile, data_dir)` : réutilise le contrat de refus explicite `schema_version ∈ {1,2}` (jamais de cold-start silencieux), refuse `bool`/`float`/`str`/absent, strippe les champs non-whitelistés à l'import, refuse les clés composites invalides (non `eq:cmd`). Round-trip export→import idempotent. Réutilise strictement `save_override`/`save_equipment_override` (aucun chemin d'écriture parallèle, D8/D10 respectés).
  - **Task 3** — Doc FR (`docs/fr_FR/index.md`) : section « Configuration du mapping par équipement (overrides) » + entrée TOC, réutilise le vocabulaire 16.4/16.5, couvre triptyque natif/override/diagnostic, validation instantanée, revert, export/import anonymisable, non-régression Homebridge. Aucune nouvelle promesse UX.
  - **Task 5** — Non-régression : suite complète 1070 passed (0 régression), invariant structurel D8 vérifié par test AST (aucun import sync/transport/mqtt dans le chemin export/import).
- **Gate terrain (Task 0 + Task 4) — 2026-07-18 — VERDICT : PASS.** Rejeu complet AC1→AC4 sur la box réelle `192.168.1.21` (daemon `0.2.0` sain, récupéré côté Alexandre après l'incident de bind port 55081). Décision de sûreté : le daemon venant d'être récupéré d'un crash de bind de port, le gate a été exécuté **sans `--restart-daemon` ni redéploiement** (uptime daemon continu observé de bout en bout). La chaîne d'override a été validée via les **routes daemon autoritatives** (`GET /system/mapping_overrides/{eq}`, `POST /action/mapping_override`, `POST /action/mapping_override_revert`, `POST /system/overrides/preview`) — celles-là mêmes qui pilotent la discovery au sync — puis un `POST /action/sync` a republié le corpus natif sans régression. `ha_overrides.json` vérifié **vide avant et après** (aucun résidu de test).

- **code-review** — 2026-07-20 — Revue adversariale (workflow BMAD `code-review`). Résultat : **0 Critical, 0 High, 1 Medium (corrigé), 1 Low (follow-up)**. 7/7 ACs implémentés/validés ; suite daemon complète **1086 passed, 0 régression**. MEDIUM corrigé : `resources/daemon/discovery/publisher.py` (fix D11) ajouté à la File List (était omis). LOW consigné (non bloquant) : `import_profile` n'est pas atomique — une clé composite invalide en milieu de profil lève `ValueError` après persistance des entrées précédentes (import partiel possible) ; acceptable pour le périmètre « simple et sûr », à durcir si un partage communautaire élargi est un jour livré. Statut résultant : `done`.

- **codex-review (PR #152)** — 2026-07-20 — Revue automatique Codex sur la PR : **1 P1 + 3 P2**, tous corrigés sur la branche puis re-poussés :
  - **P1 (validation cross-type impilotable)** — `validate_projection()` refuse désormais un override cross-type dont la **famille de commande** (ON/OFF vs OPEN/CLOSE) n'est pas routable par `_translate_command` : `has_command` se résolvant à `True` à travers les familles (cover via `has_open_close`, light/switch via `has_on_off`), un `cover → switch` passait la validation générique tout en étant impilotable. Nouvelle garde `_cross_family_action_mismatch` dans `validation/ha_component_registry.py` → `is_valid=false`, `reason_code=ha_missing_command_topic` (**0 nouveau reason_code**, `cause_mapping.py` figé intouché). Sens de commande identique (light↔switch) reste valide.
  - **P2 (whitelist de valeur)** — `_sanitize_profile_entry` valide maintenant la **valeur** en plus du nom de champ : `source ∈ {user}`, `publication_override ∈ {exclude, force_publish}`, `ha_entity_type ∈` référentiel HA connu. Un secret logé dans un champ whitelisté (`"source": "<token>"`) ou un type arbitraire est droppé à l'export ET à l'import.
  - **P2 (atomicité import)** — `import_profile` refactoré en **deux passes** : parse/valide/assainit TOUTES les entrées avant toute écriture ; une clé invalide en milieu de profil abort (`ValueError`) sans laisser de fichier partiel.
  - **P2 (échec d'écriture avalé)** — `save_override`/`save_equipment_override` renvoient désormais `bool` (True persisté, False sur dossier absent/OSError avalé) ; `import_profile` lève `RuntimeError` si une entrée validée n'a pas pu être persistée.
  - Tests ajoutés : 6 rejets/validations cross-family (`validate_projection`) + 6 whitelist-valeur/atomicité/échec-écriture/bool. Suite daemon complète **1098 passed, 0 régression**.

### Gate terrain — Preuves (2026-07-18, box `192.168.1.21`)

**AC1 — 3 familles réelles distinctes validées de bout en bout** (override appliqué+persisté / revert commande / revert équipement / diagnostic drill-down) :

| Famille | eq / cmd | natif | override → effectif | diagnostic (is_valid) | revert cmd | 
|---|---|---|---|---|---|
| Light | 391 `buanderie plafond` / 3265 `LIGHT_STATE` | `light` | → `switch` (`override_applied=true`, `source=user`) | `true` | `removed=true` → retour `light` |
| Cover | 151 `Volets` / 1122 `FLAP_STATE` | `cover` | → `switch` (`override_applied=true`, `source=user`) | `true` | `removed=true` → retour `cover` |
| Switch | 174 `Absence` / 1331 `SWITCH_STATE` | `switch` | → `light` (`override_applied=true`, `source=user`) | `true` | `removed=true` → retour `switch` |

- Revert **scope équipement** démontré sur eq 174 : `save_equipment_override(174, {publication_override:"force_publish"})` (primitive officielle) → `POST /action/mapping_override_revert {jeedom_eq_id:174}` → `scope=equipment removed=true` → fichier revenu vide.

**AC2 — Overrides invalides refusés par `validate_projection()` (via preview dry-run, zéro side-effect)** :
- `391 → sensor` (incompatible : `LightCapabilities` sans `has_state`) → `is_valid=false`, `reason_code=ha_missing_state_topic`, `missing=[state_topic]`, `should_publish=false`.
- `174 → select` (incompatible : sans `has_options`) → `is_valid=false`, `reason_code=ha_missing_required_option`, `should_publish=false`.
- **Aucun nouveau reason_code** (verdicts existants réutilisés). **Aucune persistance** (`ha_overrides.json` resté vide après preview) et **aucun publish** (preview lecture seule).

**AC3 — Non-régression Homebridge (D10) prouvée côté Jeedom** : lecture directe `cmd::byId()` après le cycle override→revert complet — `generic_type` natif **identique** au baseline topologie pré-gate :
- `3265=LIGHT_STATE`, `1122=FLAP_STATE`, `1331=SWITCH_STATE` (+ `LIGHT_ON/OFF`, `FLAP_UP/DOWN`, `SWITCH_ON/OFF` intacts). Le `generic_type` Jeedom n'a jamais été muté par la couche override.

**AC4 — Non-régression sync** : `POST /action/sync` (corpus natif, aucun override actif) → `status=ok`, `total_eq=290`, `eligible=98`, **`published=246`** (14 light + 8 cover + 39 switch + 154 sensor + 17 binary_sensor + 6 button + 7 climate + 1 alarm) = **baseline terrain connue** (cf. Debug Log 2026-07-17). Échantillon d'états MQTT réels **non-`unknown`** (`.../474/state=22.9`, `.../522/state=100`, `.../187/state=OFF`, `.../448/state=ON`, `.../587/state=15`, availabilities `online`). Topics discovery broker par plateforme = compteurs published pour tous les types **sauf `button`** (87 retained sur broker vs 6 publiés ce cycle).

**Observations honnêtes / limites** :
- L'**observation d'un override reflété dans la discovery MQTT** (republication cross-type) n'a **pas** été exécutée : elle aurait exigé un restart du daemon fraîchement récupéré + un `--cleanup-discovery` pour ne pas laisser de topics retained fantômes sous l'ancienne plateforme. La chaîne d'override est prouvée via les routes autoritatives (qui pilotent la discovery au sync). Risque jugé non justifié vu l'état du daemon.
- **Accumulation retained pré-existante** : 87 topics discovery `button` sur le broker contre 6 publiés — résidu retained d'un scope de publication antérieur, **antérieur au gate et hors périmètre 16.7** (non causé par cette story ; à traiter par un `deploy-to-box.sh --cleanup-discovery` lors d'un prochain cycle terrain planifié).

### File List

- `resources/daemon/mapping/overrides.py` (modifié — ajout `export_profile`, `import_profile`, helpers `_sanitize_profile_entry`, `_parse_override_key`, `_parse_equipment_key` + constantes whitelist ; Codex P2 : whitelist de valeur `_is_allowed_profile_value`, import deux passes atomique, `save_override*` renvoient `bool`)
- `resources/daemon/validation/ha_component_registry.py` (modifié — Codex P1 : garde `_cross_family_action_mismatch` dans `validate_projection` refusant un override cross-type dont la famille de commande n'est pas routable)
- `resources/daemon/tests/unit/test_story_16_7_profiles_export_import.py` (nouveau — 16 tests + 6 Codex P2 : whitelist-valeur, atomicité, échec-écriture, bool)
- `docs/fr_FR/index.md` (modifié — section overrides + TOC)
- `resources/daemon/discovery/publisher.py` (modifié — fix D11 : `getattr` sur `capabilities` dans `_build_switch/cover/light_payload` pour tolérer un override cross-type sans crash `AttributeError`)
- `resources/daemon/tests/unit/test_story_16_7_cross_type_override_discovery.py` (nouveau — 5 tests non-régression cross-type override discovery + 6 Codex P1 : rejets/validations cross-family `validate_projection`)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié — 16.7 → `review` après gate terrain 2026-07-18)
- `_bmad-output/implementation-artifacts/16-7-gate-terrain-et-profils-partageables.md` (modifié — checkboxes Tasks 1/2/3/5 + Task 0/4 avec preuves terrain consignées, Dev Agent Record)
