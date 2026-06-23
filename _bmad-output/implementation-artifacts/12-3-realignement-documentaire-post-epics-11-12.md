# Story 12.3: Réalignement documentaire post pe-epic-11 / pe-epic-12

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant que mainteneur du cycle BMAD `Moteur de projection explicable`,
je veux que les artefacts actifs reflètent l'état réel après les merges des stories 11.2, 11.3, 12.1 et 12.2,
afin que la prochaine story parte des bonnes sources de vérité, sans reprendre une branche ou un statut obsolète.

## Acceptance Criteria

1. **Manifeste actif réaligné.** `active-cycle-manifest.md` pointe vers le correct-course du 2026-06-22, indique que `pe-epic-10`, `pe-epic-11` et `pe-epic-12` sont livrés, et ne présente plus `pe-epic-10` comme prochaine étape.
2. **Epics détaillés réalignés.** `epics-projection-engine.md` ne décrit plus `11.2`, `11.3`, `12.1` ni `12.2` comme réservées, backlog ou à créer ; les sections détaillées reflètent leur état livré et leurs preuves principales.
3. **Rétrospectives de clôture présentes.** Les fichiers `pe-epic-11-retro-2026-06-22.md` et `pe-epic-12-retro-2026-06-22.md` existent, synthétisent valeur livrée, preuves, risques restants et leçons de méthode.
4. **Futur mapping configurable clarifié.** Les artefacts actifs signalent que la branche locale ancienne `chore/bmad-scp-epic-12` ne doit pas être utilisée telle quelle : le sujet mapping configurable devra être renuméroté/rebasé avant exécution.
5. **Tracking BMAD cohérent.** `sprint-status.yaml` suit cette story selon le contrat BMAD (`ready-for-dev` → `in-progress` → `review` → `done`) et ramène `pe-epic-12` à `done` lorsque `12.3` est validée.
6. **Validation documentaire reproductible.** Une vérification textuelle ciblée prouve que les formulations obsolètes ont disparu des artefacts actifs concernés et que les nouveaux fichiers attendus sont présents.

## Tasks / Subtasks

- [ ] Task 1 — Réaligner `active-cycle-manifest.md` (AC: 1, 4)
  - [ ] Mettre à jour la table des sources de vérité, notamment le dernier Sprint Change Proposal.
  - [ ] Remplacer la section "Prochaine étape BMAD attendue" par un état post-epic-12.
  - [ ] Ajouter une note explicite sur le cadrage mapping configurable à renuméroter/rebaser.

- [ ] Task 2 — Réaligner `epics-projection-engine.md` (AC: 2, 4)
  - [ ] Mettre à jour le résumé détaillé de `pe-epic-11` : 11.1, 11.1-bis, 11.2 et 11.3 livrées.
  - [ ] Mettre à jour le résumé détaillé de `pe-epic-12` : 12.1, 12.2 livrées, 12.3 story de closeout documentaire.
  - [ ] Retirer les formulations obsolètes "réservée", "backlog" ou "à créer" pour les stories déjà livrées.

- [ ] Task 3 — Ajouter les rétrospectives pe-epic-11 et pe-epic-12 (AC: 3)
  - [ ] Créer `pe-epic-11-retro-2026-06-22.md`.
  - [ ] Créer `pe-epic-12-retro-2026-06-22.md`.
  - [ ] Inclure valeur livrée, preuves principales, risques résiduels et leçons BMAD.

- [ ] Task 4 — Synchroniser tracking et validations documentaires (AC: 5, 6)
  - [ ] Garder cette story en `in-progress` pendant l'implémentation, puis `review` à la fin du dev-story.
  - [ ] Ajouter les lignes rétrospectives au `sprint-status.yaml`.
  - [ ] Exécuter les vérifications ciblées : `git diff --check` et recherches sur les formulations obsolètes dans les artefacts actifs.

## Dev Notes

### Source de vérité immédiate

- `sprint-status.yaml` marque déjà `pe-epic-10`, `pe-epic-11` et `pe-epic-12` comme livrés avant l'ouverture temporaire de 12.3. [Source: `_bmad-output/implementation-artifacts/sprint-status.yaml`]
- Le correct-course de cette story est `sprint-change-proposal-2026-06-22-doc-realignment.md`. [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-22-doc-realignment.md`]
- Le dernier commit `main` est `3546f22 feat(pe-11.3): generic SWITCH multi-switch energy routing (#128)`, précédé de #127, #126, #125 et #123. [Source: `git log --oneline --max-count=8`]

### Contraintes de périmètre

- Aucun code produit ne doit être modifié.
- Aucun déploiement sur environnement réel n'est requis par cette story : elle ne fait que réconcilier les documents avec des preuves déjà consignées.
- Ne pas réactiver ni merger la branche locale `chore/bmad-scp-epic-12` : elle utilise un numéro d'epic devenu obsolète.
- Ne pas renuméroter le cycle entier. La correction doit être additive et localisée.

### Dev Agent Guardrails

- Modifier les artefacts BMAD actifs avec parcimonie : `active-cycle-manifest.md`, `epics-projection-engine.md`, `sprint-status.yaml`, et les deux rétrospectives.
- Préserver les commentaires utiles de `sprint-status.yaml`; ne pas réécrire le fichier en bloc.
- Pour les formulations obsolètes, corriger dans les artefacts actifs seulement. Les anciennes Sprint Change Proposals historiques peuvent conserver leur texte d'époque.
- Le futur sujet "mapping configurable façon Homebridge" reste un prochain axe potentiel, pas une story de cette exécution.

### Project Structure Notes

- Artefacts de planning : `_bmad-output/planning-artifacts/`.
- Artefacts d'implémentation / story / rétrospectives : `_bmad-output/implementation-artifacts/`.
- Story file courant : `_bmad-output/implementation-artifacts/12-3-realignement-documentaire-post-epics-11-12.md`.

### References

- `_bmad-output/planning-artifacts/active-cycle-manifest.md`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-22-doc-realignment.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/11-2-chauffe-eau-eq554-detail-routage.md`
- `_bmad-output/implementation-artifacts/11-3-iq-ev-pilotage-priorisation-solaire.md`
- `_bmad-output/implementation-artifacts/12-1-streaming-valeur-sensor-binary-sensor-vague-1.md`
- `_bmad-output/implementation-artifacts/12-2-streaming-valeur-switch-button-vague-2.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex (create-story)

### Debug Log References

- `git log --oneline --decorate --max-count=8`
- `grep -nE "FR23|FR25|overrides|pe-epic-12|Feature 9|FR46|FR47|FR48|FR49|FR50" ...`

### Completion Notes List

- 2026-06-22 — `create-story` completed : story 12.3 matérialisée après correct-course approuvé, scope borné au réalignement documentaire actif. Statut résultant : `ready-for-dev`.

### File List

- `_bmad-output/implementation-artifacts/12-3-realignement-documentaire-post-epics-11-12.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-22-doc-realignment.md`

### Change Log

- 2026-06-22 — Story créée via workflow `create-story`; statut initial `ready-for-dev`.

