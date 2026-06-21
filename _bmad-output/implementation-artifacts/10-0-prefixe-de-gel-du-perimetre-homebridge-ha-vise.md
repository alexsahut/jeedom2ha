# Story 10.0 : Prefixe de gel du perimetre Homebridge -> HA vise

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant que mainteneur,
je veux figer dans un artefact executable la matrice `usage Homebridge -> generic types Jeedom -> composant HA cible -> statut actuel du moteur`,
so that `pe-epic-10` parte d'un delta reel partage, borne et exploitable plutot que d'une hypothese arbitraire de type HA a ouvrir.

## Acceptance Criteria

**AC1 - Matrice de perimetre minimale lisible**
Given l'audit archive dans `_bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md`,
When la story est executee,
Then un artefact de prefixe documente au minimum :
And les familles deja bien couvertes (`light`, `cover`, `switch`, `sensor`, `binary_sensor`) ;
And les familles encore hors scope ou non equivalentes (`scenarios HomeKit`, `climate`, `alarm_control_panel`, composites `IQ EV` / `SPA`) ;
And les exclusions explicites et zones ambigues utiles au sequencing.

**AC2 - Format de ligne canonique**
Given une famille Homebridge candidate,
When elle est integree dans la matrice,
Then chaque ligne documente explicitement :
And un exemple representatif ;
And le generic type Jeedom ou la famille source quand elle est connue ;
And le composant HA cible probable ;
And le statut courant du moteur (`deja couvert`, `ouvert mais a verifier`, `hors scope`, `ambigu`) ;
And la source de preuve utilisee.

**AC3 - Exclusions verrouillees**
Given une plateforme annexe ou un usage explicitement hors perimetre (`camera`, `samsung`, `alexa`, `gsh`, monitoring faible valeur),
When la matrice est finalisee,
Then ces cas sont classes hors `pe-epic-10`
And ils ne peuvent pas etre utilises pour justifier une ouverture de type dans cet epic.

**AC4 - Sequencing derive du delta reel**
Given la matrice finalisee,
When la conclusion de la story est redigee,
Then elle propose un sequencing explicite de vague conforme au delta Homebridge -> HA archive
And elle distingue clairement :
And ce qui est deja couvert ;
And ce qui doit etre verifie sur `button` ;
And ce qui releve d'une ouverture de type nouvelle (`climate`, `alarm_control_panel`) ;
And ce qui reste du cadrage composite ou d'un epic ulterieur.

**AC5 - Zero changement produit/technique premature**
Given le diff de la story,
When il est relu,
Then aucun code de production n'est modifie
And aucun `PRODUCT_SCOPE` n'est change
And la story ne requalifie pas Homebridge comme source de verite technique a la place de `ha-projection-reference.md`.

## Tasks / Subtasks

- [x] Task 1 - Charger et croiser les sources de preuve (AC: 1, 2, 3, 4, 5)
  - [x] Relire `_bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md`
  - [x] Relire `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md`
  - [x] Relire `_bmad-output/planning-artifacts/ha-projection-reference.md` uniquement sur les types utiles au delta
  - [x] Relire le bloc `Epic 10` de `_bmad-output/planning-artifacts/epics-projection-engine.md`

- [x] Task 2 - Produire la matrice canonique Homebridge -> Jeedom -> HA -> statut moteur (AC: 1, 2)
  - [x] Choisir un artefact cible date dans `_bmad-output/planning-artifacts/`
  - [x] Ecrire une ligne par famille / usage utile plutot qu'un dump equipement-par-equipement
  - [x] Marquer explicitement les cas `deja couvert`, `ouvert mais a verifier`, `hors scope`, `ambigu`
  - [x] Ajouter des exemples representatifs suffisants pour guider les stories suivantes

- [x] Task 3 - Verrouiller les exclusions et zones sensibles (AC: 3)
  - [x] Isoler les plateformes annexes hors scope
  - [x] Isoler les zones ambigues ou sensibles (`presence`, `Portail`, energie/routage, etc.)
  - [x] Formuler clairement ce qui ne doit pas entrer dans `pe-epic-10`

- [x] Task 4 - Deriver le sequencing d'epic depuis la matrice (AC: 4)
  - [x] Confirmer si `10.1` est pure verification ou completion reelle du chemin `button`
  - [x] Confirmer le besoin d'ouverture `climate` comme vague suivante
  - [x] Confirmer si `alarm_control_panel` est ouvrable ou releve d'un recadrage
  - [x] Classer `IQ EV` / `SPA` en cadrage composite plutot qu'en ouverture automatique

- [x] Task 5 - Validation documentaire et mise a jour BMAD (AC: 5)
  - [x] Verifier qu'aucun changement de code ou de `PRODUCT_SCOPE` n'apparait dans le diff
  - [x] Verifier que la story 10.0 cite correctement les sources de verite
  - [x] Mettre a jour le `sprint-status.yaml` uniquement via le statut BMAD de la story

## Dev Notes

### Contexte actif

Cycle actif : **Moteur de projection explicable**. `pe-epic-9` est clos et a livre la premiere vague reelle (`sensor`, `binary_sensor`, `button`). `pe-epic-10` demarre depuis un correct-course documente et depuis une synthese d'audit Homebridge transmise par `ClawBox`, sans nouveau scan terrain.

La finalite de cette story n'est pas d'ouvrir un type HA. Elle sert a figer la base de preuve qui permettra ensuite d'executer proprement `10.1`, `10.2`, `10.3` et `10.4` sans melanger priorisation Homebridge et contrat technique HA.

### Zone de travail cible

Artefacts de travail attendus :
- `_bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md` comme source de priorisation Homebridge -> HA
- `_bmad-output/planning-artifacts/ha-projection-reference.md` comme source-of-truth des contraintes HA
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md` comme cadrage de sequencing
- nouvel artefact prefixe a creer dans `_bmad-output/planning-artifacts/` pour la matrice canonique exploitable par `pe-epic-10`

Cette story est documentaire et de cadrage. Elle ne doit pas modifier le code de production ni les tests de production.

### Dev Agent Guardrails

- Ne pas toucher `resources/daemon/**`, `plugin_info/**`, `desktop/**`, `scripts/**`, ni aucun fichier de code applicatif.
- Ne pas modifier `PRODUCT_SCOPE`, `HA_COMPONENT_REGISTRY`, `validate_projection()`, mappers, publishers, `cause_mapping.py`.
- Ne pas transformer Homebridge en source de verite technique : `ha-projection-reference.md` garde cette autorite.
- Ne pas produire un dump exhaustif fragile ; preferer une matrice par familles / usages avec exemples representatifs et statuts moteurs.
- Ne pas reintroduire dans `pe-epic-10` les plateformes explicitement exclues par l'audit (`camera`, `SamsungTizen`, `homebridge-alexa`, `homebridge-gsh`).

### Project Structure Notes

Fichiers autorises a la modification pour cette story :
- `_bmad-output/planning-artifacts/*.md` lies au prefixe `pe-epic-10`
- `_bmad-output/implementation-artifacts/sprint-status.yaml` uniquement pour le statut BMAD de la story

Fichiers a lire mais ne pas modifier :
- `_bmad-output/planning-artifacts/ha-projection-reference.md`
- `_bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`

### Previous Story Intelligence

`pe-epic-9` a clos la vague 1 avec preuve terrain et sans laisser de dette CTA ouverte sur les surfaces reellement ouvertes. La suite ne doit donc pas re-questionner `sensor` / `binary_sensor` / `button` comme types deja ouverts, mais s'appuyer sur eux pour distinguer :
- ce qui est deja couvert par la vague 1 ;
- ce qui demande seulement verification ou completion sur `button` ;
- ce qui requiert une vraie ouverture de type nouvelle (`climate`, `alarm_control_panel`) ;
- ce qui releve d'un cadrage composite.

### Git Intelligence Summary

Commits recents pertinents :
- `851be60` `chore(bmad): move story 9.5 to review`
- `305a2f4` `feat(pe-9.5): expose actionable fallback remediation in diagnostics`
- `281646e` `chore(bmad): close Story 9.4 — gate terrain PASS`
- `d6afa6d` `feat(pe-9.4): FallbackMapper §11 + cause_mapping 3 codes + golden-file 48 eq (#117)`
- `9571104` `chore(bmad): close Story 9.3 — gate terrain PASS`

Lecture utile pour cette story : la vague 1 a bien cree la base technique qui permet maintenant une analyse de delta Homebridge -> HA sans chantier de refactor supplementaire.

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-10--Vague-Homebridge---HA-minimale-utile] - cadre epic-level et stories 10.0 a 10.4
- [Source: _bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md#Short-Delta-Reading] - delta utile deja audite
- [Source: _bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md#Planning-Readout-For-pe-epic-10] - sequencing recommande depuis l'audit
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md#42-Prefixe-obligatoire-de-pe-epic-10] - prefixe obligatoire et matrice attendue
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md#44-Acceptance-criteria-epic-level-recommandes] - gates epic-level recommandes
- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md] - source-of-truth des contraintes HA
- [Source: _bmad-output/project-context.md#MVP-Scope-Guardrails] - rester strict sur le scope et les exclusions

## Dev Agent Record

### Code Review

- 2026-06-08 — REVIEW (workflow BMAD `code-review`) — constats initiaux: incoherence critique `Status: done` avec tasks cochees a `[ ]`; correction automatique appliquee: toutes tasks/subtasks alignees en `[x]` selon preuves presentes dans l'artefact de prefixe `pe-epic-10-perimetre-prefixe-2026-06-08.md` et les references source citees.
- Verification complementaire AC1-AC5: PASS (story documentaire uniquement, aucun changement code produit, aucun changement `PRODUCT_SCOPE`).

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `sed -n '1564,1755p' _bmad-output/planning-artifacts/epics-projection-engine.md`
- `sed -n '1,260p' _bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md`
- `sed -n '1,240p' _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md`
- `sed -n '1,260p' _bmad-output/project-context.md`

### Completion Notes List

Story creee le 2026-06-07 par le workflow `bmad-create-story`.

Analyse chargee :
- workflow BMAD `create-story` complet + template + `discover-inputs.md`
- `_bmad/bmm/config.yaml`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `_bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md`
- `_bmad-output/planning-artifacts/ha-projection-reference.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/10-0-prefixe-de-gel-du-perimetre-homebridge-ha-vise.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-06-08 — Fix auto post code-review BMAD: alignement des Tasks/Subtasks (toutes cochees `[x]`) avec le statut `done`; ajout du compte-rendu de review dans `Dev Agent Record`.
