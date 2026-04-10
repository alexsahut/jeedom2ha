---
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
lastSaved: '2026-03-12T22:25:30+01:00'
workflowType: 'testarch-test-design'
inputDocuments: 
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
---

# Test Design for QA: jeedom2ha

**Purpose:** Test execution recipe for QA team. Defines what to test, how to test it, and what QA needs from other teams.

**Date:** 2026-03-12
**Author:** BMad TEA (Test Architect)
**Status:** Draft
**Project:** jeedom2ha

**Related:** See Architecture doc (test-design-architecture.md) for testability concerns and architectural blockers.

---

## Executive Summary

**Scope:** Middleware d'interopérabilité (Plugin Jeedom + Daemon Python) pour projeter une installation Jeedom sous Home Assistant via MQTT.

**Risk Summary:**
- Total Risks: 4 (4 high-priority score ≥6, 0 medium, 0 low)
- Critical Categories: BUS/DATA (Faux positifs de mapping), TECH/OPS (Cycle de vie des entités).

**Coverage Summary:**
- P0 tests: ~4 (Core Mapping, HTTP Control, Publish Discovery)
- P1 tests: ~5 (Lifecycle, Command Routing, Diagnostic Engine, MVP Exclusion, Rescan Manuel)
- P2 tests: ~1 (Throttling / Perf Verification)
- **Total**: ~10 Core Scenarios (~25-35 hours for 1 Dev/QA)

---

## Not in Scope

**Components or systems explicitly excluded from this test plan:**

| Item | Reasoning | Mitigation |
|---|---|---|
| **Thermostats hyper complexes (Climate)** | Hors scope MVP (Périmètre volontairement limité). | Seront exclus ou partiellement mappés en V1. Support complet décalé à V1.1. |
| **Sécurité/Authentication HA** | Hors du plugin Jeedom. | Configuré côté HA/Broker, le plugin n'a qu'à s'authentifier au broker. |
| **Tests E2E "Vrais"** | Maintenabilité trop lourde pour 1 dev solo sur un bridge complexe. | Remplacés par des tests d'intégration Python avec Broker MQTT mocké et API PHP mockée. |

---

## Dependencies & Test Blockers

**CRITICAL:** QA cannot proceed without these items from other teams.

### QA Infrastructure Setup (Pre-Implementation)

1. **Test Data Factories**
   - Mock des `eqLogic` et `cmd` Jeedom en format JSON.
2. **Environnement Pytest**
   - Setup `pytest` asynchrone avec mock global de `paho-mqtt` et du listener HTTP.

---

## Risk Assessment

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Score | QA Test Coverage |
|---|---|---|---|---|
| **RSK-01** | BUS/DATA | Faux positifs de mapping polluant MQTT | **9** | TU massifs sur `mapping/engine.py` avec variations de `Generic Types`. |
| **RSK-02** | TECH/OPS | Entités fantômes dans HA | **6** | Tests d'intégration sur les payloads de suppression (`{}`) |
| **RSK-03** | PERF | Saturation I/O Jeedom/Broker au boot | **6** | Test asynchrone mesurant le lissage temporel sur 100 entités fictives. |
| **RSK-04** | OPS | Support Insoutenable | **6** | Assertions fines sur la clarté de l'output d'erreur du Diagnostic. |

---

## Entry & Exit Criteria

**Entry Criteria:**
- [x] Architecture validée et séparation du Mapping isolée des I/O.
- [ ] Fixtures JSON `eqLogic` prêtes.

**Exit Criteria:**
- [ ] All P0 tests passing.
- [ ] All P1 tests passing.
- [ ] Couverture > 85% sur `mapping/engine.py` (cible indicative sur la logique métier, pas un totem global).

---

## Test Coverage Plan

### P0 (Critical)

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P0-001** | Mapping: Lights/Switches (Generic -> HA Payload) | Unit | RSK-01 | Vérifier l'idempotence et la conformité au standard HA Discovery. |
| **P0-002** | Mapping: Covers/Sensors (Generic -> HA Payload) | Unit | RSK-01 | Inclure cas nominaux et manquants/ambigus. |
| **P0-003** | HTTP API (PHP->Python Control) | Integration | - | Contrôle API & sécurité (127.0.0.1 seul, test sans clé API, payload invalide, timeout). |
| **P0-004** | Publish MQTT Discovery | Integration | RSK-02 | Vérifier l'appel à `client.publish` avec topic et flag `retained=True`. |

### P1 (High)

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P1-001** | MQTT Command Routing | Integration | - | HA Command in -> Correct Jeedom PHP Callback Out. |
| **P1-002** | Entity Lifecycle (Add/Rename/Delete) | Integration | RSK-02 | Renommage n'affecte pas `unique_id`. Delete emet payload vide retained sur topic config. |
| **P1-003** | Diagnostic Engine Output | Unit | RSK-04 | Renvoie les labels "Published/Partiel/Non-Publié" corrects avec la raison. |
| **P1-004** | Exclusion MVP | Integration | - | Exclusion équipement avant publication, republication propre post-exclusion, aucun impact sur les autres entités. |
| **P1-005** | Rescan Manuel | Integration | - | Correction type générique, déclenchement rescan, apparition de la nouvelle entité attendue. |

### P2 (Medium)

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P2-001** | Throttling / I/O Smoothing | Integration | RSK-03 | Publish loop ne surcharge pas l'event loop (vérification temporelle). |

---

## Execution Strategy

### Every PR: Pytest Unit/Integration (~2 min)
- **All P0, P1, P2 tests.**
- Les mocks asynchrones et l'injection de dépendances rendent l'exécution de la suite entière quasi instantanée. C'est la ligne de défense principale.

### Manual / Dev Ex: Vrais Tests E2E
- L'activation du Daemon sur un environnement Jeedom de dev connecté à un "vrai" Home Assistant sera gardée pour des "sanity checks" manuels de la V1 et des releases majeures, compte tenu de l'absence de ressources QA.

---

## QA Effort Estimate

| Priority | Count | Effort Range | Notes |
|---|---|---|---|
| P0 | ~4 | ~10-15 hours | Mise en place de l'injection (Mock MQTT + HTTP). |
| P1 | ~5 | ~10-15 hours | |
| P2 | ~1 | ~2-5 hours | |
| **Total** | **~10** | **~25-35 hours** | **1 Dev** |

---
