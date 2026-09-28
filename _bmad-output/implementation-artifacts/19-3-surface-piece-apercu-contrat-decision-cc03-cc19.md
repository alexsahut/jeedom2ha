# Story 19.3: Surface pièce / aperçu branchés sur le contrat de décision (CC-03, CC-19)

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un utilisateur,
I want que la surface de navigation par pièce (`_build_mapping_override_tree`, Story 16.8) et l'aperçu à blanc (`_handle_overrides_preview`) affichent le vrai statut de publication d'un équipement, et que "revenir au mode automatique (tout l'équipement)" efface bien tous les overrides de cet équipement (TYPE par commande ET publication/exclusion),
so that je ne vois plus "sera publié" pour un équipement en réalité exclu (CC-03), et que revenir au mode automatique me rende bien un état totalement automatique, sans override résiduel invisible d'aucune sorte (CC-19).

**Parcours : complet.**

## Acceptance Criteria

**AC1 — CC-03 : la surface par pièce respecte l'éligibilité réelle**

**Given** un équipement exclu (par éligibilité amont ou par override de publication/exclusion)
**When** la surface de navigation par pièce (`_build_mapping_override_tree`) affiche son statut
**Then** elle consomme `evaluate_equipment()` (Story 19.0/19.1) au lieu de recalculer sa propre logique d'affichage
**And** elle affiche le statut réel "exclu" au lieu de "sera publié"
**And** un test explicite reproduit le cas CC-03 (équipement exclu par éligibilité amont), un override de publication (aujourd'hui `None` dans cette surface) et la politique `sure_only`, et vérifie que la surface affiche désormais le statut correct.

**AC2 — CC-03 : l'aperçu à blanc reflète la même vérité**

**Given** le même équipement, consulté via l'aperçu à blanc (`_handle_overrides_preview`)
**When** l'aperçu calcule le résultat "avec override"
**Then** il consomme également `evaluate_equipment()` avec les overrides proposés (mode preview de Story 19.0, AC3)
**And** le résultat affiché par l'aperçu est cohérent avec celui affiché par la surface par pièce pour le même équipement/override (même contrat, même réponse).
**And** il utilise la politique applicative `app["confidence_policy"]` (sans `sure_probable` codé en dur aux lignes `http_server.py:2434/2460` ni issu du payload `:2281`) et passe les propositions via `proposed_overrides` / `proposed_equipment_overrides` du contrat.

**AC3 — CC-19 : "revenir au mode automatique (tout l'équipement)" efface réellement tout l'équipement**

**Given** un équipement avec un override de TYPE sur au moins une commande (`overrides[eq_id:cmd_id]`, ce qui affiche le bouton "revenir au mode automatique (tout l'équipement)" via `hasOverride`/`override_applied`, `desktop/js/jeedom2ha_mapping_surface.js` l.264-278) et, séparément, un override de publication/exclusion au niveau équipement (`equipment_overrides[eq_id]`)
**When** l'utilisateur clique sur ce bouton — qui aujourd'hui envoie uniquement `eqId` (`revertEquipment`, l.190-200), ce qui fait que `_handle_mapping_override_revert` (`resources/daemon/transport/http_server.py` l.2606-2657) n'appelle que `remove_equipment_override` et **laisse intacts** les overrides de TYPE par commande — c'est le bug réel (constaté par lecture directe du code), à l'inverse de la formulation historique de CC-19 qui supposait que seul le TYPE était effacé
**Then** l'action doit désormais effacer tous les overrides de l'équipement : `remove_override` pour chaque clé `eq_id:cmd_id` puis `remove_equipment_override` (Story 16.1/16.3 — jamais une réécriture manuelle du fichier JSON)
**And** un test explicite vérifie qu'après un seul clic, plus aucun override (TYPE ou publication, à quelque granularité que ce soit) ne subsiste pour cet équipement.

**AC4 — Libellés français des nouvelles raisons exposées**

**Given** de nouvelles valeurs de `reason`/`reason_details` potentiellement exposées à l'UI suite au branchement sur `evaluate_equipment()` (ex. raisons pour commandes non couvertes, Story 19.0 AC1)
**When** ces raisons sont affichées côté desktop
**Then** `REASON_LABELS` dans `desktop/js/jeedom2ha_mapping_override.js` (l.199-211) est étendu avec un libellé français pour chaque nouvelle raison exposée
**And** aucune raison affichée à l'utilisateur ne reste sans libellé français (pas de code brut affiché tel quel).

**AC5 — Preuve par clic réel dans l'UI Jeedom**

**Given** l'environnement Jeedom réel (box 192.168.1.21)
**When** un testeur exécute le scénario de clic suivant : (1) ouvrir la surface de navigation par pièce ; (2) localiser un équipement précédemment affiché à tort "sera publié" alors qu'il est en réalité exclu ; (3) constater qu'il affiche désormais son vrai statut "exclu" ; (4) sur un équipement avec override TYPE + override publication actifs, cliquer sur "revenir au mode automatique" ; (5) constater que les deux overrides ont disparu de l'affichage
**Then** le scénario est documenté avec captures ou description précise du résultat observé sur la box réelle
**And** cette story reste au statut `ready-for-UX-validation` tant que ce scénario de clic réel n'a pas été exécuté et documenté.
**And** la validation est nommément identifiée : validateur, date, SHA déployé, environnement (box 192.168.1.21).

**AC6 — Deux temporalités explicites**

**Given** les données de l'application
**When** la surface est construite
**Then** elle distingue la dernière décision synchronisée (`app["publications"]`) des overrides courants ; un badge indique qu'un override n'est pas encore appliqué, et un test couvre cet écart.

**AC7 — Aucun silence dans le diagnostic**

**Given** chaque commande de l'équipement
**When** la surface ou l'aperçu expose son diagnostic
**Then** chaque commande a une `CommandDecision`, une raison et un libellé français, y compris `publication_excluded_eqlogic`, `publication_excluded_command`, `publication_forced`, `sure_mapping`, `ha_component_not_in_product_scope`, `no_mapping`, `skipped_no_mapping_candidate` et la commande non couverte
**And** le diagnostic ne vaut plus `None` (`http_server.py:2496`) ni « — » côté JS (`jeedom2ha_mapping_override.js:249`) ; golden 59 contient zéro commande sans raison.

## UI Impact

- **UI Impact:** Oui — modifie l'affichage de la surface de navigation par pièce et de l'aperçu (desktop/js, statut affiché par équipement), et le comportement du bouton "revenir au mode automatique". Cette story passe par le statut `ready-for-UX-validation` avant `done` (cf. `docs/bmad-parcours-rapide-complet.md`, commit `2b2c49b`).

## Impact sur la production et retour arrière

Changement de comportement visible et volontaire côté UI : des équipements aujourd'hui affichés à tort "sera publié" (CC-03) afficheront désormais leur vrai statut "exclu" ; le bouton "revenir au mode automatique" effacera désormais tous les overrides de l'équipement (CC-19). C'est une correction de bug, assumée. Retour arrière : revert de la story/PR — la surface par pièce et l'aperçu reviennent à leur logique de calcul propre (avec les bugs CC-03/CC-19 réintroduits), sans migration de données ; aucun override existant n'est perdu par le revert (le revert change uniquement la logique d'affichage/d'effacement, pas le schéma de persistance `data/ha_overrides.json`).

## Preuve terrain

Preuve par un **vrai clic** dans l'UI Jeedom (pas seulement un test automatisé) : scénario exact décrit en AC5 — équipement précédemment affiché à tort "sera publié" doit afficher son vrai statut "exclu" ; le bouton "revenir au mode automatique" doit effacer tous ses overrides. Cette story passe par `ready-for-UX-validation` avant `done` (convention du repo).

## Invariants concernés

I2, I4, I6 (cohérence de la décision affichée avec celle réellement appliquée par le pipeline). Aucune nouvelle logique de décision n'est introduite ici — cette story ne fait que **consommer** `evaluate_equipment()` côté affichage.

## Points fermés

- **CC-03** — fermé par cette story (AC1, AC2, AC5) : la surface par pièce et l'aperçu n'affichent plus "sera publié" pour un équipement exclu.
- **CC-19** — fermé par cette story (AC3, AC5) : "revenir au mode automatique" efface tous les overrides de l'équipement.
- **CC-04** — partiellement fermé. Volet contrat : décision canonique par commande (19-0 AC1) et deux temporalités (19-3 AC6). Volet UI (jargon, gabarit, surface unique) : étape 4.
- **CC-14 P1** (parité simulation/sync + pas de silence) — fermé par 19-0 AC1 + 19-3 AC7 + 19-4 AC7 ; P0 fait à l'étape 1 ; P2 hors périmètre.

## Tasks / Subtasks

- [x] Task 1 — Brancher `_build_mapping_override_tree` sur `evaluate_equipment()` (AC1)
  - [x] Remplacer la logique de calcul de statut propre à la surface par pièce par un appel à `evaluate_equipment()` (Story 19.0/19.1)
  - [x] Vérifier que le statut affiché correspond exactement à la décision réelle (y compris pour les équipements exclus par éligibilité amont)

- [x] Task 2 — Brancher `_handle_overrides_preview` sur `evaluate_equipment()` en mode preview (AC2)
  - [x] Utiliser le paramètre "overrides proposés" de `evaluate_equipment()` (Story 19.0, AC3) pour le calcul "avec override" de l'aperçu
  - [x] Vérifier la cohérence stricte entre le résultat de l'aperçu et celui de la surface par pièce pour un même override

- [x] Task 3 — Corriger CC-19 : « revenir au mode automatique » laisse les overrides TYPE par commande (AC3)
  - [x] Effacer `remove_override` pour chaque clé `eq_id:cmd_id`, puis `remove_equipment_override` (persistance `data/ha_overrides.json`, cf. Story 16.3).

- [x] Task 4 — Étendre `REASON_LABELS` (AC4)
  - [x] Ajouter dans `desktop/js/jeedom2ha_mapping_override.js` (l.199-211) un libellé français pour chaque nouvelle raison exposée par le branchement sur `evaluate_equipment()`.
  - [x] Citer le bouton/handler réellement concernés : `desktop/js/jeedom2ha_mapping_surface.js:190-200,264-278` et `_handle_mapping_override_revert` (`http_server.py:2642-2648`).

- [ ] Task 5 — Preuve par clic réel (AC5)
  - [ ] Exécuter le scénario de clic décrit en AC5 sur la box réelle, documenter le résultat
  - [ ] Statut `ready-for-UX-validation` jusqu'à documentation de la preuve, puis passage à `done`

- [x] Task 6 — Tests (AC1-AC4, AC6-AC7)
  - [x] `test_story_19_3_ac{1,2,3,6,7}_*.py` (préfixe `test_story_19_3_*`) côté backend, plus le garde-fou de parité JSON `test_story_19_3_guardrail_no_override_json_parity.py`
  - [x] Tests front (node) pour `REASON_LABELS` étendu et `shouldShowOverridePendingBadge` (AC4/AC6)
  - [x] Golden 59 et tests backend/front : 0 commande sans raison, jamais diagnostic `None`/« — ».
  - [x] Suite complète backend + front : 0 régression (1310 tests Python + 291 tests node, tous verts)

## Dev Notes

### Contexte pipeline

- Cette story dépend de Story 19.1 (sync migré) pour disposer d'un `evaluate_equipment()` déjà validé en parité stricte avant de le brancher sur des surfaces supplémentaires.
- CC-03 et CC-19 sont deux bugs distincts corrigés dans la même story car ils touchent la même surface (navigation par pièce / overrides) et partagent le même point de branchement (`evaluate_equipment()` + effacement d'overrides).

### Report explicite de la revue PR #169 (Story 19.1)

La Story 19.1 conserve le calcul historique de l’aperçu : proposition seule,
avec uniquement la substitution `_DATA_DIR` → `data_dir`. La fusion des overrides
persistés et proposés ainsi que la politique applicative sont différées à cette story.
Utiliser `evaluate_equipment(..., proposed_overrides=..., proposed_equipment_overrides=...)`.

Ajouter un test de conflit : un override TYPE persisté sur une **autre commande de
la même entité** est rencontré avant celui demandé par `apply_type_override` et
peut gagner malgré une fusion par clé. Vérifier que le type **demandé** est celui
réellement évalué (validation HA et décision), sans mutation des overrides persistés.
Le simple passage de `proposed_overrides` ne prouve pas cette priorité inter-commandes :
le test doit couvrir ce conflit dans le contrat puis dans l’aperçu.

### Dev Agent Guardrails

- Ne jamais dupliquer la logique de décision côté surface pièce/aperçu — tout doit passer par `evaluate_equipment()`.
- L'effacement de l'override de publication lors du retour au mode automatique doit réutiliser les fonctions CRUD existantes (`remove_override`/`remove_equipment_override`, Story 16.1/16.3), jamais une réécriture manuelle du fichier JSON.
- `REASON_LABELS` : chaque nouvelle raison ajoutée doit avoir un libellé français explicite, cohérent avec le style des libellés existants (l.199-211).

### Project Structure Notes

- Fichiers à toucher (probable) : `resources/daemon/transport/http_server.py` [MODIFIÉ — `_build_mapping_override_tree`, `_handle_overrides_preview`], `desktop/js/jeedom2ha_mapping_override.js` [MODIFIÉ — `REASON_LABELS`, CC-19 : « revenir au mode automatique » laisse les overrides TYPE par commande], tests backend + front associés [NOUVEAU/MODIFIÉ].

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] — CC-03, CC-19, contexte de l'epic.
- [Source: _bmad-output/implementation-artifacts/16-8-surface-navigation-piece-equipement-commande-homebridge.md] — surface par pièce existante (`_build_mapping_override_tree`).
- [Source: desktop/js/jeedom2ha_mapping_override.js#L199-L211] — `REASON_LABELS` à étendre.
- [Source: _bmad-output/implementation-artifacts/19-0-contrat-pur-command-decision-evaluate-equipment.md] — mode "overrides proposés" consommé par l'aperçu.
- [Source: docs/bmad-parcours-rapide-complet.md] — convention `ready-for-UX-validation` (commit `2b2c49b`).

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- **create-story** — 2026-09-27 — statut résultant : `ready-for-dev`. Story documentaire créée directement (skill officielle non exposée cette session).

- **dev-story (Reprise 1)** — 2026-09-27/28 — production (`http_server.py`, `evaluate_equipment.py`, `overrides.py`, `jeedom2ha_mapping_override.js`, `jeedom2ha_mapping_surface.js`) branchée sur `evaluate_equipment()` pour AC1/AC2/AC3/AC4, `REASON_LABELS` étendu (commit `2bc7c43`). Ce tour s'est arrêté après avoir committé un premier lot de tests (`test_story_19_3_surface_apercu.py`) qui s'est révélé **fabriqué** : il appelait des signatures de fonctions inexistantes dans le code réel (jamais exécuté avec succès), ce qui a interrompu la reprise avant la validation complète. Sauvegarde de l'état non committé en `1b9906f`.

- **dev-story (Reprise 2)** — 2026-09-28 — reprise après le rapport `/tmp/jeedom2ha-19-3-resume-report.md`. Production déjà en place revue et jugée de bonne qualité : **aucun changement de production dans cette reprise**. Travail réalisé :
  - Suppression du fichier de test fabriqué (`1ce301d`) et remplacement complet par des tests réels, calqués sur le patron `test_story_16_8_secondary_sensor_diagnostic.py` (vrai client aiohttp contre les vrais endpoints HTTP) :
    - `test_story_19_3_ac1_cc03_surface_status.py` — la surface par pièce affiche le vrai statut (exclusion amont, override de publication, politique `sure_only`).
    - `test_story_19_3_ac2_preview_surface_parity.py` — cohérence aperçu/surface, `confidence_policy` exclusivement issue de `app["confidence_policy"]` (jamais du payload, écart PR #169), conflit inter-commandes (override persisté sur une commande sœur ne doit pas l'emporter sur l'override proposé).
    - `test_story_19_3_ac3_revert_equipment.py` — CC-19 : le retour au mode automatique purge tous les overrides (TYPE par commande + publication/exclusion équipement) en un seul clic.
    - `test_story_19_3_ac6_sync_status.py` — les deux temporalités (`synced_should_publish`/`current_should_publish`/`override_pending`).
    - `test_story_19_3_ac7_no_silent_diagnostic.py` — zéro commande sans diagnostic/raison sur le corpus doré (59 équipements), libellé français systématique pour toute raison de blocage, cas explicite `command_not_covered`.
    - `test_story_19_3_ac4_ac6_reason_labels_sync_badge.node.test.js` (front, node) — libellé français concret pour les 10 nouveaux codes de blocage + `publication_forced`, comportement de `shouldShowOverridePendingBadge` (normalisation stricte d'un `sync_status` absent/malformé).
    - `test_story_19_3_guardrail_no_override_json_parity.py` — garde-fou : pour un équipement sans override, diff champ à champ de la réponse JSON complète (surface + aperçu) entre `49dc70b` et la branche via une sonde manuelle (`git worktree`, script jetable non committé) ; résultat : **un seul champ diffère**, `sync_status` (nouveau, AC6) — tout le reste est strictement identique bit à bit, ce qui valide l'invariant AR9 (aucune duplication/altération de la logique de décision existante) sur le chemin heureux.
  - **Mutation testing** : les 5 fichiers de production ont été temporairement reramenés à leur état `49dc70b` (working tree non committé, jamais poussé) et la suite des 16 tests Story 19.3 rejouée. 13/16 ont échoué comme attendu (mutation tuée). 3 sont passés sur l'ancien code — chacun justifié, aucun n'a nécessité de renforcement :
    - `test_guardrail_preview_response_identical_to_pre_story` — passage **attendu et correct par construction** : ce test encode justement le résultat confirmé de la sonde (l'aperçu, pour un équipement sans override, est déjà identique avant/après la story) ; c'est un test de parité, pas un tueur de mutation.
    - `test_ac2_preview_auto_view_matches_tree_diagnostic` — passe sur `49dc70b` car l'ancien code faisait déjà transiter la vue "auto" de l'aperçu et le diagnostic de l'arbre par le même moteur (`validate_projection`/`decide_publication` dans `_preview_mapping_view`, confirmé par lecture directe de `49dc70b:resources/daemon/transport/http_server.py:2297`) pour ce cas dégénéré sans override. Le vrai correctif AC2 (source de la `confidence_policy`) est bien capturé par le test voisin `test_ac2_confidence_policy_ignores_payload_uses_app_state`, qui échoue correctement sur `49dc70b`.
    - `test_ac2_proposed_override_wins_over_sibling_persisted_override` — passe sur `49dc70b` car l'ancien code clé déjà les overrides proposés par `f"{eq_id}:{cmd_id}"` (confirmé `49dc70b:resources/daemon/transport/http_server.py:2447`) : l'isolation entre commandes sœurs préexistait à la story. Ce test reste une garde de non-régression légitime pour cet invariant de structure de données, pas un tueur de mutation Story 19.3.
  - Les 5 fichiers de production ont été restaurés à l'état `HEAD` de la branche immédiatement après la campagne de mutation (aucune trace de la mutation dans l'historique git).
  - **Suite complète, zéro régression** : `python3 -m pytest -q` depuis `resources/daemon` → 1310 passed ; `node --test tests/unit/*.node.test.js` → 291 pass, 0 fail.
  - **Écart hors périmètre constaté (non corrigé dans cette reprise)** : sur le corpus doré, certaines commandes secondaires (eq 583 "IQ EV Charger", cmds 5999/6000/6001/6021 ; eq 628 "Pilotage priorisation solaire", cmds 5981/5982/5984/5985/6005/6006) affichent simultanément `covered=False` (champ `row["covered"]` de l'arbre, basé sur `_secondary_mapping_by_cmd`/`reason_details["cmd_id"]`) et `should_publish=True`/`ha_entity_type` renseigné dans leur diagnostic (basé sur `evaluation.command_decisions`, source de vérité). Les deux détections de couverture peuvent diverger pour certaines commandes secondaires. Aucun impact utilisateur constaté (le diagnostic affiché reste correct, seul le badge `coverable`/`covered` de l'arbre serait potentiellement trompeur) — documenté ici pour un futur ticket, volontairement non corrigé (hors périmètre AC1-AC7 de cette reprise, aurait nécessité une modification de production non demandée).
  - AC5 (preuve par clic réel sur la box 192.168.1.21) reste **non exécutée** dans cette reprise — hors périmètre (aucun accès box/déploiement autorisé pour ce tour). La story reste donc à `in-progress`, pas `ready-for-UX-validation`.

- **dev-story (Reprise 3 — relecture ClaudeBox PR #176)** — 2026-09-28 — correction de trois défauts trouvés par ClaudeBox (P1-a, P1-b bloquants ; P3 mineur), tous visibles uniquement à l'échelle du corpus doré complet (59 équipements), jamais sur un équipement synthétique isolé :
  - **P1-a (AC2/AC7)** — `POST /system/overrides/preview` était muet (`auto:None`, `overridden:None`, `covered` absent) pour un équipement inéligible (disabled/excluded) ou sans mapping — branche `auto_evaluation.mapping is None` de `_handle_overrides_preview`. Fix : nouvelle fonction `_view_for_ineligible_or_unmapped(evaluation, cmd_id)` — expose la même vue que le `diagnostic` de l'arbre pour cette commande (raison d'éligibilité, `should_publish:false`) ; `auto` et `overridden` partagent la même vue puisqu'aucun override ne peut changer une décision déjà tranchée au niveau 1/2 (I4). `covered:false` ajouté (était absent).
  - **P1-b** — les commandes d'action (On/Off) des interrupteurs secondaires (eq 583 cmds 5999/6000/6001/6021 ; eq 628 cmds 5981/5982/5984/5985/6005/6006) étaient `covered:false` avec un diagnostic incohérent (`should_publish:true`, `ha_entity_type:null`) — c'est exactement l'écart hors périmètre documenté en Reprise 2 ci-dessus, maintenant corrigé. Cause racine : `_secondary_mapping_by_cmd` n'indexait que `reason_details["cmd_id"]` (commande d'état) de chaque secondaire, jamais ses commandes d'action présentes dans `secondary.commands`. Fix : indexation via `mapping_cmd_ids(secondary)`, la même extraction que le primaire (`mapping/overrides.py`) — une seule fonction reste la source, partagée par `covered` (arbre), le diagnostic (arbre) et la cible de l'aperçu (`_target_mapping_for_cmd`).
  - **P3 (mineur)** — le littéral `"sure_probable"` était dupliqué 4 fois (`_handle_sync`, `_handle_overrides_preview`, signature par défaut et point d'appel de `_build_mapping_override_tree`). Fix : constantes module-level `_DEFAULT_CONFIDENCE_POLICY = "sure_probable"` et `_VALID_CONFIDENCE_POLICIES = ("sure_only", "sure_probable")`.
  - **3ᵉ défaut découvert par le nouveau test golden-corpus (non listé par ClaudeBox)** : dans la branche `auto_target is None` de `_handle_overrides_preview` (commande ciblée non couverte ni par le primaire ni par un secondaire), `auto` était construit via `_view_from_evaluation(auto_evaluation, None)` — `cmd_id=None` cible TOUJOURS le mapping PRIMAIRE dans `_target_mapping_for_cmd`, donc l'aperçu affichait la décision de l'ÉQUIPEMENT (ex. `alarm_control_panel`, `should_publish:true` pour eq 230) au lieu de la décision `command_not_covered` propre à la commande — 18 écarts sur eq 230/554/583 du corpus doré. Fix : réemploi de `_view_for_ineligible_or_unmapped(auto_evaluation, proposed_cmd_id)` (déjà introduite pour P1-a), qui résout déjà la décision par `cmd_id` dans `evaluation.command_decisions`, `mapping=None` — même contrat que la branche `diag_mapping=None` de l'arbre.
  - **Tests ajoutés** : `test_story_19_3_fix1_claudebox_review.py` — Test 1 (parité aperçu/arbre par commande sur les 59 équipements et leurs commandes), Test 2 (invariants golden : aucun `covered:false` publié, aucun `should_publish:true` avec type `null`, chaque raison de blocage a un libellé `REASON_LABELS`), 3 tests unitaires (eq 5000 désactivé, eq 5001 exclu, eq 628 secondaire commande On).
  - **Mutation testing** : sur `c59a87e` (avant tout fix), les 5 tests échouent. Sur `efa9d9c` (P1-a/P1-b/P3 seuls, sans le 3ᵉ fix), Test 1 échoue encore (18 écarts) tandis que Test 2 et les 3 unitaires passent déjà — preuve que le 3ᵉ défaut est réel et distinct, révélé uniquement par le test à l'échelle du corpus complet.
  - **Suite complète, zéro régression** : `python3 -m pytest -q` depuis la racine du repo → **1919 passed** ; `node --test tests/unit/*.node.test.js` → **291 pass, 0 fail**.
  - AC5 reste **non exécutée** dans cette reprise également (même hors-périmètre qu'en Reprise 2). Statut inchangé : `in-progress`.

### File List

**Production (Reprise 1, `2bc7c43` + travail antérieur en `1b9906f`) :**
- `resources/daemon/transport/http_server.py` [MODIFIÉ] — `_build_mapping_override_tree`, `_handle_overrides_preview`, `_handle_mapping_override_revert` branchés sur `evaluate_equipment()`
- `resources/daemon/models/evaluate_equipment.py` [MODIFIÉ]
- `resources/daemon/mapping/overrides.py` [MODIFIÉ]
- `desktop/js/jeedom2ha_mapping_override.js` [MODIFIÉ] — `REASON_LABELS` étendu, `shouldShowOverridePendingBadge`
- `desktop/js/jeedom2ha_mapping_surface.js` [MODIFIÉ]

**Tests (Reprise 2) :**
- `resources/daemon/tests/unit/test_story_19_3_ac1_cc03_surface_status.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_19_3_ac2_preview_surface_parity.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_19_3_ac3_revert_equipment.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_19_3_ac6_sync_status.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_19_3_ac7_no_silent_diagnostic.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_19_3_guardrail_no_override_json_parity.py` [NOUVEAU]
- `tests/unit/test_story_19_3_ac4_ac6_reason_labels_sync_badge.node.test.js` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_16_8_secondary_sensor_diagnostic.py` [MODIFIÉ — adapté aux nouvelles signatures]
- `resources/daemon/tests/unit/test_story_19_0_evaluate_equipment_contract.py` [MODIFIÉ — adapté aux nouvelles signatures]
- `resources/daemon/tests/unit/test_story_19_3_surface_apercu.py` [SUPPRIMÉ — fichier fabriqué de la Reprise 1, signatures inexistantes]

**Production + tests (Reprise 3, relecture ClaudeBox PR #176, commits `efa9d9c` + `7814de9`) :**
- `resources/daemon/transport/http_server.py` [MODIFIÉ] — `_secondary_mapping_by_cmd` (P1-b), nouvelle `_view_for_ineligible_or_unmapped` + branchement `_handle_overrides_preview` (P1-a et 3ᵉ défaut, branche `auto_target is None`), constantes `_DEFAULT_CONFIDENCE_POLICY`/`_VALID_CONFIDENCE_POLICIES` (P3)
- `resources/daemon/tests/unit/test_story_19_3_fix1_claudebox_review.py` [NOUVEAU]
