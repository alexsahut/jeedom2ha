---
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
lastSaved: '2026-03-12T22:25:30+01:00'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad/tea/config.yaml'
---

# Step 01: Detect Mode

- **Detected Mode**: System-Level Mode
- **Reasoning**: `sprint-status.yaml` does not exist in the implementation artifacts, whereas `prd.md` and `architecture.md` are present in the planning artifacts. According to file-based detection rules, this indicates a System-Level test design phase.

# Step 02: Load Context

- **Detected Stack**: `backend` (Jeedom PHP plugin + Python daemon via MQTT).
- **Loaded Artifacts**: System-Level artifacts `prd.md` and `architecture.md` loaded successfully.
- **Key Extractions**:
  - **Dependencies**: Jeedom 4.4.9+, Debian 12, Python 3.9+, MQTT Broker (Mosquitto).
  - **Integrations**: Jeedom core API (eqLogic/cmd/event::changes), MQTT HA Discovery standard payload format.
  - **NFRs**: Latency ≤ 2s, bootstrap non saturant, robust lifecycle, local-first.
- **Knowledge Base**: Appropriate config and paths resolved `tea_use_playwright_utils=true`, `tea_use_pactjs_utils=true`.

# Step 03: Risk & Testability Assessment

## 1. Testability Assessment Summary (System-Level)

**✅ Testability Assessment Summary**
- **Controllability**: Excellent. The Python daemon exposes a local HTTP API (`/action/sync`, `/action/publish`) allowing easy test harnesses without full Jeedom UI. The mapping engine is strictly separated from the transport layer.
- **Observability**: High. Logs are categorized explicitly (`[MQTT]`, `[MAPPING]`, etc.). A dedicated diagnostic subsystem evaluates every entity with clear reasons for non-publication.
- **Reliability**: High predictability. Stateless mapping logic, explicit re-sync on boot, and no complex external databases involved.

**🚨 Testability Concerns**
- **E2E Complexity**: End-to-end tests involving a real Jeedom core and Home Assistant instance are heavy to maintain for a solo developer.
- **PHP ↔ Python contract**: Testing the exact interaction between the Jeedom PHP core events and the Python daemon requires robust mocking of the Jeedom API.

**ASRs (Architecturally Significant Requirements)**
- **ASR1 [ACTIONABLE]**: The `mapping/engine.py` must be 100% mocked and tested independently of MQTT or the Jeedom HTTP API to prove deterministic behavior.
- **ASR2 [ACTIONABLE]**: Establish a lightweight fixture set representing typical "messy" Jeedom object structures to feed the mapping tests.

## 2. Risk Assessment Findings

1. **[BUS/DATA] Moteur de mapping générant des faux-positifs** (P:3, I:3 = 9) - L'hétérogénéité des "generic types" Jeedom peut polluer HA. *Mitigation: Politique d'exposition conservative ("ne pas publier plutôt que publier faux"), diagnostic explicite.*
2. **[TECH/OPS] Cycle de vie et entités fantômes** (P:2, I:3 = 6) - Désynchronisation entre Jeedom et HA (suppressions non reflétées). *Mitigation: Utilisation stricte de payloads vides retained pour la suppression de MQTT Discovery.*
3. **[PERF] Saturation I/O au Bootstrap** (P:3, I:2 = 6) - Publier 100+ équipements sature la box Jeedom ou le broker. *Mitigation: Throttling / lissage de la publication discovery sur 5-10 secondes.*
4. **[OPS] Maintenabilité Solo** (P:2, I:3 = 6) - La charge de support peut noyer le développeur. *Mitigation: MVP strict (lumières, volets, prises, capteurs simples), logs de support exportables par l'utilisateur.*

# Step 04: Coverage Plan & Execution Strategy

## 1. Coverage Matrix

- **[P0] Mapping Engine (Lights/Switches)**: Validation de la traduction Jeedom (generic types) -> HA Payload. *Niveau: Unit*
- **[P0] Mapping Engine (Covers & Sensors)**: Traduction des volets et capteurs simples (température, binaire). *Niveau: Unit*
- **[P0] HTTP API (PHP->Python)**: Commandes de contrôle `/action/sync` et `/action/publish`. *Niveau: Integration (mock Jeedom)*
- **[P0] MQTT Discovery Publish**: Le payload généré est publié sur le bon topic (retained). *Niveau: Integration (mock Broker)*
- **[P1] MQTT Command Return**: L'ordre HA passe via le démon Python et génère le bon callback Jeedom. *Niveau: Integration*
- **[P1] Entity Lifecycle**: Ajout, Renommage (unique_id stable), Suppression (via empty payload retained). *Niveau: Integration*
- **[P1] Diagnostic Engine**: Génère les statuts "published/partial/none + reason" correctement. *Niveau: Unit*
- **[P2] Throttling / Boot I/O**: 100 entités sont publiées lissées sur ~10s. *Niveau: Integration/Perf*

## 2. Execution Strategy

- **PR (Pull Request)**: L'ensemble des tests unitaires et d'intégration Python (exécutés via `pytest` avec mocks MQTT/HTTP) DOIT tourner sur chaque PR. Temps d'exécution cible < 2 minutes.
- **Nightly / Dev Ex**: Les tests E2E nécessitant un Jeedom Core simulé + Broker Mosquitto local sont laissés à la discrétion du développeur en dev local ou en Nightly s'ils s'avèrent fiables.

## 3. Resource Estimates

- **P0** (Core MVP Mapping & Transport): ~10–15 hours
- **P1** (Lifecycle, Retour Cmd, Diag): ~8–12 hours
- **P2** (Boot Throttling, Perf): ~2–5 hours
- **Total:** ~20–32 hours

## 4. Quality Gates

- P0 pass rate = 100%
- P1 pass rate ≥ 95%
- High-risk mitigations (Empty Retained for Deletions, Safe Mapping Fallbacks) doivent être validées unitairement avant release.
- Couverture de test unitaire (Coverage Target) ≥ **85%** stricte sur `resources/daemon/mapping/engine.py`.

# Step 05: Generate Outputs & Validate

## Completion Report

- **Mode Used:** System-Level Mode
- **Output File Paths:**
  - `_bmad-output/test-artifacts/test-design-architecture.md` (System Architecture Test Design)
  - `_bmad-output/test-artifacts/test-design-qa.md` (QA Execution Test Design)
  - `_bmad-output/test-artifacts/test-design/jeedom2ha-handoff.md` (BMAD Handoff Document)
- **Key Risks & Gates:**
  - **RSK-01:** Moteur de mapping faux-positifs.
  - **RSK-02:** Cycle de vie et entités fantômes.
  - **RSK-03:** Saturation I/O Jeedom/Broker au boot.
  - **Gates:** 100% Pass Rate sur P0. 85%+ Test Coverage sur le module Mapping.
- **Validation:** Tous les templates ont été générés avec succès. La stratégie d'E2E a été basculée vers l'intégration Python pour limiter la surcharge de l'unique mainteneur.
