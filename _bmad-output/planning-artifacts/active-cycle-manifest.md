# Manifeste du cycle actif

## 1. Titre du cycle actif

**Moteur de projection explicable**

## 2. Statut du cycle actif

**Cycle actif de reference pour les workflows BMAD et les prompts agents.**

## 3. Objectif de ce manifeste

Eviter tout melange entre les artefacts historiques `V1.1 Pilotable` et les artefacts actifs du cycle `Moteur de projection explicable`. Ce document fixe la source de verite process a utiliser sans interpretation.

## 4. Sources de verite actives par categorie

| Categorie | Fichier actif |
| --- | --- |
| Product Brief | `_bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md` |
| PRD | `_bmad-output/planning-artifacts/prd.md` |
| Architecture | `_bmad-output/planning-artifacts/architecture-projection-engine.md` |
| Reconciliation PRD / Architecture | `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md` |
| Epics / story breakdown | `_bmad-output/planning-artifacts/epics-projection-engine.md` |
| UX / gates de surface critique | Portees par `epics-projection-engine.md` et les gates terrain story-level |
| Sprint status | `_bmad-output/implementation-artifacts/sprint-status.yaml` |
| Readiness report | `_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-10.md` |
| Backlog futur (Icebox) | `_bmad-output/planning-artifacts/backlog-icebox.md` |
| Reference projection HA (types Jeedom + composants HA + champs requis) | `_bmad-output/planning-artifacts/ha-projection-reference.md` (extrait de `docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx`) |
| Sprint Change Proposal le plus recent | `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md` |

**Note source projection HA** : `ha-projection-reference.md` documente 31 composants HA officiels MQTT, 163 types generiques Jeedom Core 4.2, et 77 champs structurellement requis. Toute extension du perimetre publie (ouverture de nouveau type dans `PRODUCT_SCOPE`, ajout de mapper, ajout de publisher, ajout de contrainte au registre HA) **doit** etre derivee de cette reference. Les artefacts code (`ha_component_registry.py`, mappers/, discovery/) sont derives, pas l'inverse. Cette reference est le contrat operationnel pour `validate_projection()` et le sequencing des vagues d'ouverture (`pe-epic-9`, `pe-epic-10+`).

## 5. Artefacts historiques conserves a titre de contexte secondaire

Ces artefacts ne sont pas des sources de verite pour le cycle actif. Ils servent uniquement de contexte historique :

- `_bmad-output/planning-artifacts/product-brief-jeedom2ha-post-mvp-refresh.md`
- `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md`
- `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md`
- `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md`
- `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
- `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
- `_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-27.md`
- `_bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-03-12.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status-pre-v1-1-pilotable-2026-03-22.yaml`

Par defaut, tout artefact non liste en section 4 est considere comme secondaire tant que ce manifeste n'est pas mis a jour.

## 6. Regles d'usage pour les prochains workflows BMAD

- Toujours considerer **Moteur de projection explicable** comme cycle actif tant que ce manifeste n'est pas remplace.
- Utiliser uniquement les fichiers de la section 4 pour planifier, verifier la readiness, suivre le sprint et preparer l'execution.
- Ne pas reutiliser les artefacts `V1.1 Pilotable` pour redefinir le scope, les priorites ou le sequencing des epics `pe-*`.
- Toute story future touchant `PRODUCT_SCOPE` doit etre relue contre `epics-projection-engine.md`, FR40 et NFR10.
- Toute story future touchant `cause_action` doit repasser par la regle `no faux CTA` et le gate terrain correspondant.
- Ne jamais deduire la source de verite a partir du nom le plus ancien ou le plus generique d'un fichier.

## 7. Regles d'usage pour les prochains prompts agents

- Nommer explicitement le cycle actif : **Moteur de projection explicable**.
- Citer explicitement les fichiers actifs utilises.
- Mentionner explicitement que `_bmad-output/implementation-artifacts/sprint-status.yaml` est le fichier de suivi actif.
- Si un prompt reference un artefact `V1.1 Pilotable`, le traiter comme contexte secondaire uniquement.
- Aucun agent ne doit deviner la source de verite. En cas d'ambiguite, il doit se referer a ce manifeste.
- Pour toute story touchant `HA_COMPONENT_REGISTRY`, `PRODUCT_SCOPE`, un mapper, un publisher ou la validation projection : citer explicitement `_bmad-output/planning-artifacts/ha-projection-reference.md` comme source-of-truth des contraintes HA et des types Jeedom. Les contraintes story-level doivent etre tracables jusqu'a une ligne de cette reference.
- Pour toute story touchant le dispatch, le `MapperRegistry` ou le `PublisherRegistry` introduits par `pe-epic-8` : citer le golden-file de Story 8.4 comme baseline de regression-control.
- Pour toute story exposant un `cause_action` : appliquer la regle Epic 6 « no faux CTA » (Story 6.3) et centraliser le `cause_code -> cause_label / cause_action` dans `cause_mapping.py` selon la convention Epic 4 V1.1.

## 8. Convention de decision en cas de conflit entre artefacts

- Les artefacts du cycle actif **Moteur de projection explicable** priment.
- Les artefacts `V1.1 Pilotable` servent uniquement de contexte.
- Le `sprint-status` actif prime pour l'execution et l'etat d'avancement.
- Si un conflit persiste, ce manifeste fait foi pour identifier quel artefact a autorite.

## 9. Prochaine etape BMAD attendue

Utiliser ce manifeste comme point d'entree avant tout workflow BMAD d'execution, puis s'appuyer sur `epics-projection-engine.md` et `sprint-status.yaml` pour la suite.  
Apres le correct-course du `2026-04-30` (`sprint-change-proposal-2026-04-30.md`), la prochaine etape attendue est la preparation de `pe-epic-8`, en commencant par la story `8.1` (`MapperRegistry`). `pe-epic-9` reste bloque tant que le golden-file de Story 8.4 n'est pas vert.

## 10. Resume ultra court a copier dans les prompts

Cycle actif = **Moteur de projection explicable**. Sources de verite actives = `product-brief-jeedom2ha-2026-04-09.md`, `prd.md`, `architecture-projection-engine.md`, `architecture-delta-review-prd-final.md`, `epics-projection-engine.md`, `implementation-readiness-report-2026-04-10.md`, `sprint-status.yaml`, `backlog-icebox.md`, `ha-projection-reference.md` (extrait de `docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx` — source-of-truth pour les contraintes HA et les types Jeedom), `sprint-change-proposal-2026-04-30.md` (dernier correct-course : cloture pe-epic-7, ajout pe-epic-8 refactor dispatch + pe-epic-9 vague 1 reelle). Les artefacts `V1.1 Pilotable` sont du contexte secondaire uniquement. Aucun agent ne doit deviner la source de verite.
