---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-06-22
status: approved
scope_classification: minor
trigger: realignement-documentaire-post-merge-pe-11-3
mode: batch
communication_language: french
proposed_by: clawcode
impacts_if_approved:
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/planning-artifacts/active-cycle-manifest.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/implementation-artifacts/pe-epic-11-retro-2026-06-22.md
  - _bmad-output/implementation-artifacts/pe-epic-12-retro-2026-06-22.md
approval:
  approved_by: Alexandre
  approved_on: 2026-06-22
  source: "Demande explicite: ok fait une story de réalignement documentaire, utilise bien les workflow bmad"
---

# Sprint Change Proposal 2026-06-22 — Réalignement documentaire post pe-epic-11 / pe-epic-12

## 1. Issue Summary

Après le merge de la PR #128 (`feat(pe-11.3): generic SWITCH multi-switch energy routing`), l'état réel du projet est plus avancé que plusieurs artefacts de planification :

- `sprint-status.yaml` et les story records marquent `pe-epic-10`, `pe-epic-11` et `pe-epic-12` comme livrés.
- `active-cycle-manifest.md` pointe encore le correct-course du 2026-06-07 comme dernière source et annonce `pe-epic-10` comme prochaine étape.
- `epics-projection-engine.md` décrit encore `11.2`, `11.3`, `12.1` et `12.2` comme réservées, backlog ou à créer dans ses sections détaillées.
- Les rétrospectives de clôture `pe-epic-11` et `pe-epic-12` ne sont pas présentes sur `main`.
- Une branche locale ancienne `chore/bmad-scp-epic-12` utilise le numéro `pe-epic-12` pour un futur mapping configurable ; ce numéro a depuis été consommé par l'epic runtime state streaming.

Ce correct-course ne change pas le produit livré. Il ajoute une story de maintenance documentaire pour remettre les sources BMAD actives au niveau de la réalité Git/GitHub.

## 2. Impact Analysis

**Epic impact.** `pe-epic-12` est temporairement rouvert pour une story de closeout documentaire `12.3`, puis doit revenir à `done` après `code-review`. `pe-epic-11` et le runtime streaming restent fonctionnellement clos.

**Story impact.** Nouvelle story :

- `12-3-realignement-documentaire-post-epics-11-12`

**Artifact impact.**

- `epics-projection-engine.md` : remplacer les formulations réservées/backlog par l'état livré et ajouter le statut de closeout.
- `active-cycle-manifest.md` : mettre à jour le dernier SCP, le statut du cycle, la prochaine étape BMAD et les notes de conflit.
- `sprint-status.yaml` : inscrire la story 12.3 dans la séquence BMAD, puis la clôturer après review.
- Rétrospectives : créer `pe-epic-11-retro-2026-06-22.md` et `pe-epic-12-retro-2026-06-22.md`.

**PRD / Architecture / UX.** Aucun changement requis : il s'agit d'un réalignement de suivi et de narration BMAD, sans nouveau comportement produit ni interface.

## 3. Recommended Approach

Approche retenue : **Direct Adjustment**.

Créer une story BMAD courte et bornée, exécutée dans l'ordre obligatoire :

1. `create-story`
2. `dev-story`
3. `code-review`

La story doit modifier uniquement les artefacts documentaires actifs et les rétrospectives. Aucun code produit, test terrain, déploiement box ou PR GitHub n'est requis.

## 4. Detailed Change Proposals

### `sprint-status.yaml`

- Rouvrir temporairement `pe-epic-12` en `in-progress` pour la story de maintenance.
- Ajouter `12-3-realignement-documentaire-post-epics-11-12: backlog`.
- À la fin de `code-review`, repasser `12.3` et `pe-epic-12` à `done`.

### `epics-projection-engine.md`

- Ajouter Story 12.3 dans Epic 12.
- Refléter que 11.2, 11.3, 12.1 et 12.2 sont livrées, avec leurs preuves principales.
- Conserver la séparation : pe-epic-11 = discovery énergie/routage ; pe-epic-12 = runtime state streaming.

### `active-cycle-manifest.md`

- Mettre `sprint-change-proposal-2026-06-22-doc-realignment.md` comme dernier correct-course.
- Indiquer que `pe-epic-10`, `pe-epic-11` et `pe-epic-12` sont livrés.
- Clarifier que le futur mapping configurable doit être renuméroté/rebasé avant usage, car `pe-epic-12` désigne désormais le runtime state streaming livré.

### Rétrospectives

- Créer une rétro courte pour `pe-epic-11`.
- Créer une rétro courte pour `pe-epic-12`.
- Documenter les leçons : terrain exécutable depuis clawcode, éviter les worktrees fantômes, closeout BMAD à faire immédiatement après gate/merge.

## 5. Implementation Handoff

**Scope : Mineur.** Exécution directe par clawcode via story BMAD.

**Success criteria :**

- Les artefacts actifs ne disent plus que 11.2/11.3/12.1/12.2 sont réservées ou à créer.
- Le manifeste pointe vers l'état courant et non vers `pe-epic-10`.
- Les rétrospectives 11/12 existent.
- `sprint-status.yaml` reflète la story 12.3 et clôture à nouveau `pe-epic-12` après review.

