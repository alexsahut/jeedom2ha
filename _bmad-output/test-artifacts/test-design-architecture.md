---
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
lastSaved: '2026-03-12T22:25:30+01:00'
workflowType: 'testarch-test-design'
inputDocuments: 
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
---

# Test Design for Architecture: jeedom2ha

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by Architecture/Dev teams. Serves as a contract between QA and Engineering on what must be addressed before test development begins.

**Date:** 2026-03-12
**Author:** BMad TEA (Test Architect)
**Status:** Architecture Review Pending
**Project:** jeedom2ha
**PRD Reference:** `_bmad-output/planning-artifacts/prd.md`
**ADR Reference:** `_bmad-output/planning-artifacts/architecture.md`

---

## Executive Summary

**Scope:** Middleware d'interopérabilité (Plugin Jeedom + Daemon Python) qui projette automatiquement une installation Jeedom existante dans Home Assistant via MQTT Discovery, couvrant en MVP les lumières, prises, volets et capteurs simples.

**Business Context** (from PRD):
- **Problem:** Éviter aux utilisateurs Jeedom un choix binaire entre conserver leur investissement historique et accéder aux UI/IA modernes de Home Assistant.
- **GA Launch:** MVP ciblé sur une "Time to first useful value < 1h".

**Architecture** (from ADR):
- **Key Decision 1:** Démon Python 3 asynchrone géré par Jeedom.
- **Key Decision 2:** Transport PHP <-> Python via API HTTP locale et Callbacks Jeedom.
- **Key Decision 3:** Mapping Engine "généric-type first", source de vérité = Jeedom exclusivement.

**Risk Summary:**
- **Total risks**: 4
- **High-priority (≥6)**: 4 risks requiring immediate mitigation
- **Test effort**: ~20-32 hours for 1 Developer/QA.

---

## Quick Guide

### 🚨 BLOCKERS - Team Must Decide (Can't Proceed Without)

**Pre-Implementation Critical Path** - These MUST be completed before QA can write integration tests:

1. **TEST-01: Contrat de Mock API Jeedom** - Le mock de l'API HTTP locale Jeedom (pour simuler la source de vérité PHP) doit être stabilisé pour permettre les tests Python indépendants. (recommended owner: Dev Lead)
2. **TEST-02: Fixtures de Generic Types** - Obtenir un échantillon ("fixture set") des configurations `eqLogic`/`cmd` typiques (propres et erronées) issues de Jeedom pour nourrir le Mapping Engine. (recommended owner: Dev Lead)
3. **TEST-03: Contrat de Sécurité API Locale** - Définir et tester rigoureusement la sécurité du canal local (inaccessible hors 127.0.0.1, rejet sans clé API, payload invalide -> erreur structurée, timeouts remontés dans le diagnostic). (recommended owner: Dev Lead)

---

### ⚠️ HIGH PRIORITY - Team Should Validate

1. **[BUS/DATA] Moteur de mapping générant des faux-positifs** - S'assurer que la politique d'exposition reste "conservative" et que les exceptions sont traçables. Valider l'architecture du `mapping/engine.py` de manière isolée.
2. **[TECH/OPS] Cycle de vie et entités fantômes** - Valider l'idempotence des commandes de suppression et l'usage correct des payloads `MQTT Discovery` vides (retained=true).

---

### 📋 INFO ONLY - Solutions Provided (Review, No Decisions Needed)

1. **Test strategy**: Majoritairement unitaire et d'intégration en Python (`pytest`), mockant MQTT et HTTP.
2. **Tooling**: `pytest`, `pytest-asyncio`, `paho-mqtt` (mocké).
3. **Coverage**: Focus P0 sur le Mapping Engine et le publish MQTT Discovery.
4. **Quality gates**: 100% pass sur P0, couverture > 85% sur le Mapping Engine.

---

## For Architects and Devs - Open Topics 👷

### Risk Assessment

**Total risks identified**: 4 (4 high-priority score ≥6)

#### High-Priority Risks (Score ≥6) - IMMEDIATE ATTENTION

| Risk ID | Category | Description | Prob | Impact | Score | Mitigation | Owner | Timeline |
|---|---|---|---|---|---|---|---|---|
| **RSK-01** | **BUS/DATA** | Moteur de mapping générant des faux-positifs polluant HA | 3 | 3 | **9** | Règle conservative ("ne pas publier plutôt que faux"), diagnostic explicite. | Dev | MVP |
| **RSK-02** | **TECH/OPS** | Désynchro cycle de vie (Entités fantômes dans HA) | 2 | 3 | **6** | Suppression par payload vide retained MQTT, Rescan Manuel. | Dev | MVP |
| **RSK-03** | **PERF** | Saturation I/O au Bootstrap (Box limitées) | 3 | 2 | **6** | Lissage temporal / Throttling de la publication MQTT sur 5-10s. | Dev | MVP |
| **RSK-04** | **OPS** | Maintenabilité Solo (Dette Support) | 2 | 3 | **6** | Périmètre V1 strictement délimité, output diagnostic clair. | PM/Dev | MVP |

---

### Testability Concerns and Architectural Gaps

**🚨 ACTIONABLE CONCERNS - Architecture Team Must Address**

#### 1. Blockers to Fast Feedback

| Concern | Impact | What Architecture Must Provide | Owner | Timeline |
|---|---|---|---|---|
| **E2E Complexity** | Impossibilité de tester "rapidement" le flux complet PHP -> Python -> MQTT -> HA. | **Séparation nette (ASR1)** : `mapping/engine.py` doit être 100% isolé du transport MQTT pour validation unitaire `pytest`. | Dev | Dev-Start |
| **API Locale Sécurité** | Vulnérabilité du canal local et instabilité en cas de payload malformé. | **Sécurisation (ASR2)** : Implémenter et tester inaccessibilité hors 127.0.0.1, rejet sans clé API, payloads invalides (erreur structurée) et timeouts. | Dev | Dev-Start |

### Testability Assessment Summary

**📊 CURRENT STATE - FYI**

#### What Works Well
- ✅ **Controllability**: L'API HTTP locale (`/action/sync`) offre des points d'entrée parfaits pour le déclenchement de tests sans passer par l'UI PHP.
- ✅ **Observability**: Le sous-système de diagnostic par équipement (publié/partiel/non) rend le debug et les assertions de mapping limpides.
- ✅ **Reliability**: Pas de base de données asynchrone source d'états concurrents (uniquement Jeedom).

---

### Risk Mitigation Plans (High-Priority Risks ≥6)

#### RSK-01: Moteur de mapping générant des faux-positifs (Score: 9) - CRITICAL

**Mitigation Strategy:**
1. Implémenter un découplage total entre `mapping/engine.py` et MQTT.
2. Créer une batterie de tests unitaires injectant les fixtures typiques de `cmd` Jeedom.
3. Assert que toute entrée ambiguë retourne une action "Ignore" ou un niveau de confiance "faible" avec raison textuelle ("Pas de type générique valide").
4. **Fallback honnête** : Ajouter un test dédié aux états non mensongers en cas de valeur invalide/incomplète (null, unité absente, commande incohérente). Le système ne doit pas publier faux : conserver le dernier état valide, publier unknown/unavailable, ou ignorer selon le cas.

**Owner:** Dev Lead
**Timeline:** Sprint 1
**Status:** Planned
**Verification:** 85%+ Unit test coverage sur le module `mapping`.

#### RSK-02: Désynchro cycle de vie et entités fantômes (Score: 6) - HIGH

**Mitigation Strategy:**
1. Tester unitairement le générateur de payload Discovery pour vérifier les deletes (payload vide retained sur le topic de config).
2. Implémenter un test d'intégration simulant une action `remove` depuis l'UI PHP et vérifiant le message MQTT publié.

**Owner:** Dev Lead
**Timeline:** Sprint 1
**Status:** Planned
**Verification:** Integration Test Pass sur le flow `remove`.

---

**End of Architecture Document**
