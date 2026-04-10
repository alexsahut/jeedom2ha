---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments: 
  - '_bmad-output/test-artifacts/test-design-architecture.md'
  - '_bmad-output/test-artifacts/test-design-qa.md'
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-03-12T22:25:30.000Z'
projectName: 'jeedom2ha'
---

# TEA → BMAD Integration Handoff

## Purpose

This document bridges TEA's test design outputs with BMAD's epic/story decomposition workflow (`create-epics-and-stories`). It provides structured integration guidance so that quality requirements, risk assessments, and test strategies flow into implementation planning.

## TEA Artifacts Inventory

| Artifact | Path | BMAD Integration Point |
|---|---|---|
| Test Design Architecture | `_bmad-output/test-artifacts/test-design-architecture.md` | Epic quality requirements |
| Test Design QA | `_bmad-output/test-artifacts/test-design-qa.md` | Story acceptance criteria |
| Risk Assessment | (embedded in Architecture) | Epic risk classification |
| Coverage Strategy | (embedded in QA) | Story test requirements |

## Epic-Level Integration Guidance

### Risk References

- **RSK-01 (Moteur de mapping générant des faux-positifs)**: L'Epic développant le mapping (Moteur) DOIT inclure une validation rigoureuse des cas ambigus ("ne pas publier plutôt que faux").
- **RSK-02 (Cycle de vie des entités fantômes)**: L'Epic gérant la synchronisation MQTT DOIT s'assurer que l'usage de payloads vides retained sur le topic de config est implémenté et validé lors de la suppression.
- **RSK-03 (Saturation I/O)**: L'Epic lié au Bootstrap doit intégrer une notion de Throttling/Lissage de l'event loop locale.

### Quality Gates

- Les Pull Requests DOIVENT inclure des `pytest` unitaires/intégration.
- Le Coverage de Code DOIT impérativement couvrir à 85%+ la logique de "Translation Jeedom -> Home Assistant".

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Story Acceptance Criteria

- **P0-001 / P0-002**: Chaque story intégrant un nouveau Set de Génériques (ex. "Support des Lights", "Support des Covers") DOI inclure la création de ses tests de mapping respectifs.
- **P0-003 / P1-001**: La story de communication HTTP DOIT formaliser et valider les contrats d'interaction entre PHP et Python (API locale et callbacks), sans imposer le test de la chaîne complète E2E.
- **P1-003**: La story de création de l'interface de diagnostic DOIT s'appuyer sur une structure standard retournée par le mapping engine.

### Data-TestId Requirements

*(N/A for typical API/MQTT backend logic since there is no DOM rendering inside the Python daemon. UI PHP may require standard Jeedom identifiers).*

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic | Test Level |
|---|---|---|---|---|
| **RSK-01** | BUS/DATA | 9 | Core/Mapping Engine Epic | Unit |
| **RSK-02** | TECH/OPS | 6 | MQTT Transport / Sync Epic | Integration |
| **RSK-03** | PERF | 6 | Bootstrap & Cache Engine | Integration |
| **RSK-04** | OPS | 6 | Diagnostic Engine | Unit |

## Phase Transition Quality Gates

| From Phase | To Phase | Gate Criteria |
|---|---|---|
| Test Design | Epic/Story Creation | All P0 risks have mitigation strategy |
| Epic/Story Creation | ATDD | Stories have acceptance criteria from test design |
| ATDD | Implementation | Failing acceptance tests exist for all P0/P1 scenarios |
| Implementation | Test Automation | All acceptance tests pass |
| Test Automation | Release | Trace matrix shows respect des tests initiaux |
