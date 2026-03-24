# Manifeste du cycle actif

## 1. Titre du cycle actif

**Post-MVP Phase 1 - V1.1 Pilotable**

## 2. Statut du cycle actif

**Cycle actif de reference pour les workflows BMAD et les prompts agents.**

## 3. Objectif de ce manifeste

Eviter tout melange entre les artefacts historiques du MVP et les artefacts actifs du cycle V1.1 Pilotable. Ce document fixe la source de verite process a utiliser sans interpretation.

## 4. Sources de verite actives par categorie

| Categorie | Fichier actif |
| --- | --- |
| Product Brief | `_bmad-output/planning-artifacts/product-brief-jeedom2ha-post-mvp-refresh.md` |
| PRD | `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md` |
| UX | `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md` |
| Architecture | `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md` |
| Epics / story breakdown | `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md` |
| Test strategy | `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md` |
| Sprint status | `_bmad-output/implementation-artifacts/sprint-status.yaml` |
| Readiness report | `_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-22.md` |
| Backlog futur (Icebox) | `_bmad-output/planning-artifacts/backlog-icebox.md` |

## 5. Artefacts historiques conserves a titre de contexte secondaire

Ces artefacts ne sont pas des sources de verite pour le cycle actif. Ils servent uniquement de contexte historique :

- `_bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-03-12.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status-pre-v1-1-pilotable-2026-03-22.yaml`

Par defaut, tout autre artefact non liste en section 4 est considere comme secondaire tant que ce manifeste n'est pas mis a jour.

## 6. Regles d'usage pour les prochains workflows BMAD

- Toujours considerer **V1.1 Pilotable** comme cycle actif tant que ce manifeste n'est pas remplace.
- Utiliser uniquement les fichiers de la section 4 pour planifier, verifier la readiness, suivre le sprint et preparer l'execution.
- Ne pas reutiliser les artefacts MVP historiques pour redefinir le scope, les priorites ou le sequencing actif.
- Ne jamais deduire la source de verite a partir du nom le plus ancien ou le plus generique d'un fichier.

## 7. Regles d'usage pour les prochains prompts agents

- Nommer explicitement le cycle actif: **Post-MVP Phase 1 - V1.1 Pilotable**.
- Citer explicitement les fichiers actifs utilises.
- Mentionner explicitement que `_bmad-output/implementation-artifacts/sprint-status.yaml` est le fichier de suivi actif.
- Si un prompt reference un artefact historique, le traiter comme contexte secondaire uniquement.
- Aucun agent ne doit deviner la source de verite. En cas d'ambiguite, il doit se referer a ce manifeste.

## 8. Convention de decision en cas de conflit entre artefacts

- Les artefacts du cycle actif **V1.1 Pilotable** priment.
- Les artefacts MVP historiques servent uniquement de contexte.
- Le `sprint-status` actif prime pour l'execution et l'etat d'avancement.
- Si un conflit persiste, ce manifeste fait foi pour identifier quel artefact a autorite.

## 9. Prochaine etape BMAD attendue

Utiliser ce manifeste comme point d'entree avant tout workflow BMAD d'execution, puis s'appuyer sur les epics V1.1 et le `sprint-status.yaml` actif pour la suite.

## 10. Resume ultra court a copier dans les prompts

Cycle actif = **Post-MVP Phase 1 - V1.1 Pilotable**. Sources de verite actives = `product-brief-jeedom2ha-post-mvp-refresh.md`, `prd-post-mvp-v1-1-pilotable.md`, `ux-delta-review-post-mvp-v1-1-pilotable.md`, `architecture-delta-review-post-mvp-v1-1-pilotable.md`, `epics-post-mvp-v1-1-pilotable.md`, `test-strategy-post-mvp-v1-1-pilotable.md`, `implementation-readiness-report-2026-03-22.md`, `sprint-status.yaml`, `backlog-icebox.md`. Les artefacts MVP historiques sont du contexte secondaire uniquement. Aucun agent ne doit deviner la source de verite.
