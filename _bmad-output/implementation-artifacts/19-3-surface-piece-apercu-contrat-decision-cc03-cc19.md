# Story 19.3: Surface pièce / aperçu branchés sur le contrat de décision (CC-03, CC-19)

Status: backlog

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
**And** il utilise la politique applicative `app["confidence_policy"]` (sans `sure_probable` codé en dur aux lignes `http_server.py:2434/2460` ni issu du payload `:2281`) et fusionne les overrides persistés/proposés (`:2337-2358`).

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

**AC6 — Deux temporalités explicites**

**Given** les données de l'application
**When** la surface est construite
**Then** elle distingue la dernière décision synchronisée (`app["publications"]`) des overrides courants ; un badge indique qu'un override n'est pas encore appliqué, et un test couvre cet écart.

**AC7 — Aucun silence dans le diagnostic**

**Given** chaque commande de l'équipement
**When** la surface ou l'aperçu expose son diagnostic
**Then** chaque commande a une `CommandDecision`, une raison et un libellé français, y compris `publication_excluded_eqlogic`, `publication_excluded_command`, `publication_forced`, `sure_mapping`, `ha_component_not_in_product_scope`, `no_mapping`, `skipped_no_mapping_candidate` et la commande non couverte
**And** le diagnostic ne vaut plus `None` (`http_server.py:2496`) ni « — » côté JS (`jeedom2ha_mapping_surface.js:249`) ; golden 59 contient zéro commande sans raison.

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

- [ ] Task 1 — Brancher `_build_mapping_override_tree` sur `evaluate_equipment()` (AC1)
  - [ ] Remplacer la logique de calcul de statut propre à la surface par pièce par un appel à `evaluate_equipment()` (Story 19.0/19.1)
  - [ ] Vérifier que le statut affiché correspond exactement à la décision réelle (y compris pour les équipements exclus par éligibilité amont)

- [ ] Task 2 — Brancher `_handle_overrides_preview` sur `evaluate_equipment()` en mode preview (AC2)
  - [ ] Utiliser le paramètre "overrides proposés" de `evaluate_equipment()` (Story 19.0, AC3) pour le calcul "avec override" de l'aperçu
  - [ ] Vérifier la cohérence stricte entre le résultat de l'aperçu et celui de la surface par pièce pour un même override

- [ ] Task 3 — Corriger "revenir au mode automatique" pour effacer aussi l'override de publication (AC3)
  - [ ] Effacer `remove_override` pour chaque clé `eq_id:cmd_id`, puis `remove_equipment_override` (persistance `data/ha_overrides.json`, cf. Story 16.3).

- [ ] Task 4 — Étendre `REASON_LABELS` (AC4)
  - [ ] Ajouter dans `desktop/js/jeedom2ha_mapping_override.js` (l.199-211) un libellé français pour chaque nouvelle raison exposée par le branchement sur `evaluate_equipment()`.
  - [ ] Citer le bouton/handler réellement concernés : `desktop/js/jeedom2ha_mapping_surface.js:190-200,264-278` et `_handle_mapping_override_revert` (`http_server.py:2642-2648`).

- [ ] Task 5 — Preuve par clic réel (AC5)
  - [ ] Exécuter le scénario de clic décrit en AC5 sur la box réelle, documenter le résultat
  - [ ] Statut `ready-for-UX-validation` jusqu'à documentation de la preuve, puis passage à `done`

- [ ] Task 6 — Tests (AC1-AC4, AC6-AC7)
  - [ ] `test_story_19_3_surface_piece_apercu_contrat.py` (préfixe `test_story_19_3_*`) côté backend
  - [ ] Tests front (node) pour `REASON_LABELS` étendu et le comportement "revenir au mode automatique"
  - [ ] Golden 59 et tests backend/front : 0 commande sans raison, jamais diagnostic `None`/« — ».
  - [ ] Suite complète backend + front : 0 régression

## Dev Notes

### Contexte pipeline

- Cette story dépend de Story 19.1 (sync migré) pour disposer d'un `evaluate_equipment()` déjà validé en parité stricte avant de le brancher sur des surfaces supplémentaires.
- CC-03 et CC-19 sont deux bugs distincts corrigés dans la même story car ils touchent la même surface (navigation par pièce / overrides) et partagent le même point de branchement (`evaluate_equipment()` + effacement d'overrides).

### Dev Agent Guardrails

- Ne jamais dupliquer la logique de décision côté surface pièce/aperçu — tout doit passer par `evaluate_equipment()`.
- L'effacement de l'override de publication lors du retour au mode automatique doit réutiliser les fonctions CRUD existantes (`remove_override`/`remove_equipment_override`, Story 16.1/16.3), jamais une réécriture manuelle du fichier JSON.
- `REASON_LABELS` : chaque nouvelle raison ajoutée doit avoir un libellé français explicite, cohérent avec le style des libellés existants (l.199-211).

### Project Structure Notes

- Fichiers à toucher (probable) : `resources/daemon/transport/http_server.py` [MODIFIÉ — `_build_mapping_override_tree`, `_handle_overrides_preview`], `desktop/js/jeedom2ha_mapping_override.js` [MODIFIÉ — `REASON_LABELS`, logique "revenir au mode automatique"], tests backend + front associés [NOUVEAU/MODIFIÉ].

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

### File List
