# Story 19.3: Surface pièce / aperçu branchés sur le contrat de décision (CC-03, CC-19)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un utilisateur,
I want que la surface de navigation par pièce (`_build_mapping_override_tree`, Story 16.8) et l'aperçu à blanc (`_handle_overrides_preview`) affichent le vrai statut de publication d'un équipement, et que "revenir au mode automatique" efface aussi l'override de publication/exclusion,
so that je ne vois plus "sera publié" pour un équipement en réalité exclu (CC-03), et que revenir au mode automatique me rende bien un état totalement automatique, sans override de publication résiduel invisible (CC-19).

## Acceptance Criteria

**AC1 — CC-03 : la surface par pièce respecte l'éligibilité réelle**

**Given** un équipement exclu (par éligibilité amont ou par override de publication/exclusion)
**When** la surface de navigation par pièce (`_build_mapping_override_tree`) affiche son statut
**Then** elle consomme `evaluate_equipment()` (Story 19.0/19.1) au lieu de recalculer sa propre logique d'affichage
**And** elle affiche le statut réel "exclu" au lieu de "sera publié"
**And** un test explicite reproduit le cas CC-03 (équipement exclu par éligibilité amont) et vérifie que la surface affiche désormais le statut correct.

**AC2 — CC-03 : l'aperçu à blanc reflète la même vérité**

**Given** le même équipement, consulté via l'aperçu à blanc (`_handle_overrides_preview`)
**When** l'aperçu calcule le résultat "avec override"
**Then** il consomme également `evaluate_equipment()` avec les overrides proposés (mode preview de Story 19.0, AC3)
**And** le résultat affiché par l'aperçu est cohérent avec celui affiché par la surface par pièce pour le même équipement/override (même contrat, même réponse).

**AC3 — CC-19 : "revenir au mode automatique" efface aussi l'override de publication**

**Given** un équipement avec un override de TYPE et un override de publication/exclusion actifs simultanément
**When** l'utilisateur clique sur "revenir au mode automatique"
**Then** l'override de TYPE est effacé (comportement déjà existant)
**And** l'override de publication/exclusion est **également** effacé (correction CC-19)
**And** un test explicite vérifie que les deux overrides sont bien supprimés en un seul clic, et qu'aucun des deux ne subsiste après l'action.

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

## UI Impact

- **UI Impact:** Oui — modifie l'affichage de la surface de navigation par pièce et de l'aperçu (desktop/js, statut affiché par équipement), et le comportement du bouton "revenir au mode automatique". Cette story passe par le statut `ready-for-UX-validation` avant `done` (cf. `docs/bmad-parcours-rapide-complet.md`, commit `2b2c49b`).

## Impact sur la production et retour arrière

Changement de comportement visible et volontaire côté UI : des équipements aujourd'hui affichés à tort "sera publié" (CC-03) afficheront désormais leur vrai statut "exclu" ; le bouton "revenir au mode automatique" effacera désormais aussi l'override de publication (CC-19), alors qu'il ne le faisait pas avant. C'est une correction de bug, assumée. Retour arrière : revert de la story/PR — la surface par pièce et l'aperçu reviennent à leur logique de calcul propre (avec les bugs CC-03/CC-19 réintroduits), sans migration de données ; aucun override existant n'est perdu par le revert (le revert change uniquement la logique d'affichage/d'effacement, pas le schéma de persistance `data/ha_overrides.json`).

## Preuve terrain

Preuve par un **vrai clic** dans l'UI Jeedom (pas seulement un test automatisé) : scénario exact décrit en AC5 — équipement précédemment affiché à tort "sera publié" doit afficher son vrai statut "exclu" ; le bouton "revenir au mode automatique" doit effacer aussi l'override de publication/exclusion. Cette story passe par `ready-for-UX-validation` avant `done` (convention du repo).

## Invariants concernés

I2, I4, I6 (cohérence de la décision affichée avec celle réellement appliquée par le pipeline). Aucune nouvelle logique de décision n'est introduite ici — cette story ne fait que **consommer** `evaluate_equipment()` côté affichage.

## Points fermés

- **CC-03** — fermé par cette story (AC1, AC2, AC5) : la surface par pièce et l'aperçu n'affichent plus "sera publié" pour un équipement exclu.
- **CC-19** — fermé par cette story (AC3, AC5) : "revenir au mode automatique" efface aussi l'override de publication/exclusion.
- **CC-04**, **CC-14** (P1) — non couverts par le contexte technique fourni pour cette story (aucune information reliant explicitement CC-04/CC-14 à la surface pièce/aperçu/mode automatique) : **restent ouverts**. À rattacher explicitement à une story de cet epic ou à un incrément séparé lors d'un futur `correct-course`, une fois leur contenu précisé.

## Tasks / Subtasks

- [ ] Task 1 — Brancher `_build_mapping_override_tree` sur `evaluate_equipment()` (AC1)
  - [ ] Remplacer la logique de calcul de statut propre à la surface par pièce par un appel à `evaluate_equipment()` (Story 19.0/19.1)
  - [ ] Vérifier que le statut affiché correspond exactement à la décision réelle (y compris pour les équipements exclus par éligibilité amont)

- [ ] Task 2 — Brancher `_handle_overrides_preview` sur `evaluate_equipment()` en mode preview (AC2)
  - [ ] Utiliser le paramètre "overrides proposés" de `evaluate_equipment()` (Story 19.0, AC3) pour le calcul "avec override" de l'aperçu
  - [ ] Vérifier la cohérence stricte entre le résultat de l'aperçu et celui de la surface par pièce pour un même override

- [ ] Task 3 — Corriger "revenir au mode automatique" pour effacer aussi l'override de publication (AC3)
  - [ ] Identifier le point d'effacement actuel de l'override de TYPE et y ajouter l'effacement symétrique de l'override de publication/exclusion (persistance `data/ha_overrides.json`, cf. Story 16.3 `remove_override`/`remove_equipment_override`)

- [ ] Task 4 — Étendre `REASON_LABELS` (AC4)
  - [ ] Ajouter dans `desktop/js/jeedom2ha_mapping_override.js` (l.199-211) un libellé français pour chaque nouvelle raison exposée par le branchement sur `evaluate_equipment()`

- [ ] Task 5 — Preuve par clic réel (AC5)
  - [ ] Exécuter le scénario de clic décrit en AC5 sur la box réelle, documenter le résultat
  - [ ] Statut `ready-for-UX-validation` jusqu'à documentation de la preuve, puis passage à `done`

- [ ] Task 6 — Tests (AC1-AC4)
  - [ ] `test_story_19_3_surface_piece_apercu_contrat.py` (préfixe `test_story_19_3_*`) côté backend
  - [ ] Tests front (node) pour `REASON_LABELS` étendu et le comportement "revenir au mode automatique"
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
