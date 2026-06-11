---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-06-10
status: approved
scope_classification: minimal
trigger: correction-course-presence-switch-mapper-story-A
mode: incremental
communication_language: french
proposed_by: clawcode
impacts_if_approved:
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/ha-projection-reference.md
references:
  - _bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md
  - session transcript 2026-06-09 (audit delta HomeKit vs HA)
---

# Sprint Change Proposal 2026-06-10 - Story 10.7 : PresenceSwitchMapper (presence → switch)

## 1. Issue Summary

### Trigger

Lors de la session du 2026-06-09, un audit du delta HomeKit → HA a mis en évidence un écart structurel
sur les équipements de présence. HomeKit publie un **switch** (état ON/OFF visible + actionnable)
pour les équipements Jeedom disposant d'une info PRESENCE + des actions set-on / set-off.
`jeedom2ha` publie actuellement un `binary_sensor` (état seul) + un `button` (action seule) — deux
entités disjointes, inférieures à l'expérience HomeKit.

L'epic `pe-epic-10` avait explicitement classé `presence` comme « zone sensible, ouvrable seulement
après cadrage explicite ». Ce correct-course constitue ce cadrage.

### Clarification des stories initialement proposées

Lors de la session du 2026-06-09, trois stories avaient été proposées (A, B, C) :

| Story | Proposition | Réalité au 2026-06-10 |
|---|---|---|
| A — Présence → switch | PresenceSwitchMapper, état visible | **NOUVELLE** — ajoutée ici comme Story 10.7 |
| B — Scénarios MQTT debug | Fix topic MQTT scénario | **= Story 10-6 déjà in-progress** (créée 2026-06-10) |
| C — ClimateMapper thermostats | Mapper THERMOSTAT_* → climate | **= Story 10-2 DÉJÀ DONE** (gate terrain PASS 2026-06-09) |

Seule Story A est réellement nouvelle.

### Problem Statement

Pour les équipements Jeedom de type présence (PRESENCE + set-on / set-off), le mapping actuel
produit deux entités séparées :
- `binary_sensor` : état seul (no action possible depuis HA)
- `button` (via FallbackMapper) : action seule (pas de retour d'état)

L'équivalent HomeKit est un **switch** unique : état ON/OFF visible + commande depuis HA.
Ce double-publishing dégradé génère de la confusion dans l'UI HA et ne permet pas de voir
facilement si quelqu'un est présent.

### Evidence

| Evidence | Constat |
|---|---|
| `homebridge-homekit-vs-ha-delta-2026-06-07.md` | Présence = switch dans HomeKit, pas de binary_sensor + button |
| Conversation terrain 2026-06-09 | Présence iPhone Alex visible dans HA comme sensor seul, pas actionnable |
| `epics-projection-engine.md` §Epic 10 | Présence classée « zone sensible — ouvrable après cadrage explicite » |
| Story 9.3 (ButtonMapper) + Story 9.2 (BinarySensorMapper) | Présence actuellement mappée via les deux mappers génériques |

## 2. Impact Analysis

### 2.1 Ce qui ne change pas

- Le cycle actif reste **Moteur de projection explicable**.
- `ha-projection-reference.md` reste la source de vérité des contraintes HA.
- Les guardrails `FR40` / `NFR10` restent obligatoires : Story 10.7 devra embarquer cas nominaux, cas d'échec, golden-file, non-régression dans le même incrément.
- `pe-epic-10` reste centré sur la parité Homebridge minimale utile.

### 2.2 Ce qui change si approuvé

- `pe-epic-10` s'enrichit d'une Story 10.7 de type technique : détection de la combinaison PRESENCE + set-on/set-off → publication d'un `switch` unique.
- `switch` est **déjà dans `PRODUCT_SCOPE`** — pas de nouvelle ouverture de type HA requise.
- Fallback sur `binary_sensor` si pas d'actions (lecture seule) — préserve la rétrocompatibilité.

## 3. Detailed Change Proposal

### Story 10.7 : PresenceSwitchMapper — publier `switch` pour les équipements présence actionnables

**Contenu :**

1. Ajouter un `PresenceSwitchMapper` qui :
   - détecte la combinaison `info PRESENCE` + actions `set-on` / `set-off` dans les generics Jeedom
   - produit un `MappingResult` avec `ha_entity_type = "switch"` (déjà dans PRODUCT_SCOPE)
   - configure `state_topic` + `command_topic` correctement

2. Fallback sur `binary_sensor` si les actions set-on / set-off sont absentes (lecture seule).

3. Preuves FR40 / NFR10 dans le même incrément : cas nominaux, cas d'échec de validation,
   golden-file étendu, non-régression diagnostic.

4. Gate terrain sur box réelle : vérifier que les équipements de présence (ex : iPhone Alex)
   apparaissent en switch dans HA avec état ET commande.

### Séquençage

- Story 10.7 est ajoutée en **backlog** dans `pe-epic-10`.
- Prochaine action attendue : session séparée `create-story` pour Story 10.7.
- Story 10.6 (fix MQTT scénarios) reste in-progress et bloque le gate terrain de l'epic.

## 4. Artifact Changes

| Artefact | Changement |
|---|---|
| `epics-projection-engine.md` | Ajout Story 10.7 sous pe-epic-10 |
| `sprint-status.yaml` | Ajout `10-7-presence-switch-mapper: backlog` |

## 5. Decision

Approved — cadrage explicite confirmé par Alexandre lors de la session du 2026-06-09.
