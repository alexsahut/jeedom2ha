---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-06-17
status: approved
scope_classification: moderate
trigger: gate-terrain-11.1-revele-fix-eligibilite-et-dette-cycle-de-vie-multi-sensor
mode: batch
communication_language: french
proposed_by: clawcode
impacts_if_approved:
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/implementation-artifacts/11-1-bis-multi-sensor-lifecycle-depublication-secondaires.md (nouveau, via create-story)
  - resources/daemon/models/topology.py (Fix A — déjà appliqué sous Story 11.1)
  - resources/daemon/mapping/sensor.py (Fix A — déjà appliqué sous Story 11.1)
  - resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py (fixture terrain + tests éligibilité)
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/ha-projection-reference.md
references:
  - _bmad-output/implementation-artifacts/11-1-msunpv-routeursolaire-sensors-lecture-seule.md
  - _bmad-output/planning-artifacts/backlog-icebox.md §3.1
  - session transcript 2026-06-17 (gate terrain box réelle 192.168.1.21)
---

# Sprint Change Proposal 2026-06-17 — Gate terrain Story 11.1 : Fix A éligibilité + élévation dette cycle de vie multi-sensor (Story 11.1.bis)

## 1. Issue Summary

### Trigger

Le 2026-06-17, le gate terrain de la Story 11.1 (déclaré « waived — matériel MSunPV indisponible »
dans le record dev-story) a été **réellement exécuté** sur la box Jeedom DEV/TEST `192.168.1.21`.
Le matériel MSunPV/RouteurSolaire eq553 est en fait **live et accessible** (SSH + API daemon + script
`deploy-to-box.sh`). Le waiver était donc factuellement faux.

Le gate a révélé deux faits non couverts par la Story 11.1 telle que close en review :

1. **Régression d'éligibilité (bloquant terrain)** — Le vrai eq553 ne porte **aucun** `generic_type`
   sur ses commandes. La fonction `assess_eligibility()` rejetait donc l'eqLogic
   (`no_supported_generic_type`) **avant** d'atteindre le multi-sensor mapper → **0 sensor publié**
   sur la box. Les tests unitaires masquaient le défaut en injectant `generic_type="POWER"` sur
   2 commandes de la fixture, ce qui n'existe pas sur le terrain.

2. **Dette de cycle de vie multi-sensor (Follow-up MEDIUM préexistant)** — La dépublication
   (`unpublish_by_eq_id`) ne nettoie que le topic primaire `homeassistant/sensor/jeedom2ha_553/config`.
   Les N topics secondaires `jeedom2ha_553_<cmd>/config` resteraient orphelins (ghosts HA) si eq553
   est supprimé, désactivé, exclu ou sort du périmètre msunpv. Sur le terrain réel, ce ne sont pas
   « 7 secondaires » mais **64 secondaires** (voir Evidence) — la dette est bien plus lourde
   qu'estimée en review.

### Evidence

Gate terrain 2026-06-17 (après `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`,
sync `succes`) :

- `/system/diagnostics` : eq553 `perimetre=inclus`, `statut=publie`, `ha_type=sensor`.
- Broker MQTT (127.0.0.1:1883, creds `mqtt2`) : **65 topics** discovery retained
  `homeassistant/sensor/jeedom2ha_553_<cmd>/config` (et non 8 — le « 8 » de l'AC#2 était un
  sous-ensemble curé du backlog-icebox ; le vrai eq553 expose 65 commandes info numériques).
- Device commun `identifiers:["jeedom2ha_553"]`, `unique_id=jeedom2ha_eq_553_cmd_<cmd>`,
  `state_topic=jeedom2ha/553/<cmd>/state`, `device_class` inféré par unité (ex. `#5138` → power/W),
  availability `online`.

## 2. Impact Analysis

### Epic Impact

- `pe-epic-11` (Énergie / Routage solaire) — affecté. Story 11.1 reste la story d'ouverture ;
  une nouvelle story de robustesse (cycle de vie multi-sensor) est ajoutée à l'epic.

### Story Impact

| Story | État avant | État après ce correct-course |
|---|---|---|
| 11.1 — MSunPV sensors lecture seule | review, gate « waived » | review, **gate PASS** ; Fix A intégré ; record corrigé |
| **11.1.bis — Multi-sensor lifecycle (dépublication secondaires)** | n'existe pas | **NOUVELLE** — matérialisée via create-story |

### Artifact Conflicts

- `11-1-...md` : waiver supprimé, gate PASS + Fix A documentés, Follow-up MEDIUM marqué « élevé en 11.1.bis ».
  (déjà appliqué)
- `sprint-status.yaml` : ligne 11.1 à corriger (gate PASS, 65 sensors, pytest 825) + ajout ligne 11.1.bis.
- PRD / architecture / ha-projection-reference : **aucun changement** — le multi-sensor borné msunpv
  et son cycle de vie restent dans le contrat existant (sensor déjà dans PRODUCT_SCOPE).

### Technical Impact

- **Fix A (déjà appliqué sous Story 11.1)** : `MULTI_SENSOR_EQ_TYPES` + `_has_numeric_info_command()`
  dans `models/topology.py` ; `assess_eligibility()` rend éligibles les eqTypes multi-sensor sans
  `generic_type` dès ≥1 commande info numérique. Garde-fou AC#4 préservé (aucun autre eqType).
  `sensor.py` réutilise la constante partagée (source unique, pas d'import circulaire). Fixture de
  test rendue fidèle au terrain + 2 tests d'éligibilité. **Suite pytest : 825 passed.**
- **Story 11.1.bis (à venir)** : stockage des mappings/publications secondaires par `eq_id` et nettoyage
  exhaustif des topics `jeedom2ha_<eq>_<cmd>/config` à la dépublication. Code pressenti :
  `transport/http_server.py` (`_publish_additional_sensors`, paths unpublish), `discovery/publisher.py`
  (`unpublish_by_eq_id`, `_build_topic`).

## 3. Recommended Approach

**Direct Adjustment** — pas de rollback, pas de réduction de MVP.

1. Story 11.1 : conserver le travail (multi-sensor fonctionnel + Fix A). Le gate étant PASS, la story
   peut suivre son cours review → done. **Le Fix A est intégré à 11.1** car il est indissociable de
   son AC#8 (sans lui, 0 sensor terrain) — ce n'est pas du scope nouveau mais la correction d'un défaut
   masqué qui rendait 11.1 non démontrable.
2. Story 11.1.bis : nouvelle story dédiée à la robustesse du cycle de vie multi-sensor (dépublication
   exhaustive des secondaires). C'est un scope distinct (suppression/retype/exclusion), explicitement
   hors-scope de 11.1, et désormais prioritaire car la dette réelle = 64 topics orphelins potentiels.

- **Effort estimé** : Fix A = fait. Story 11.1.bis = S/M (stockage secondaires + nettoyage + tests + gate terrain de dépublication).
- **Risque** : faible. Fix A borné msunpv et couvert par tests + gate. Story 11.1.bis isolable.
- **Timeline** : aucune dérive ; 11.1.bis s'insère dans pe-epic-11 sans bloquer 11.1.

## 4. Detailed Change Proposals

### 4.1 — Story 11.1 (record) — DÉJÀ APPLIQUÉ

Voir `11-1-...md` : Task 0 et Task 5 (gate) passés de WAIVED à exécuté/PASS ; Completion Notes
réécrites (gate PASS 65 sensors + Fix A) ; Review Follow-ups : LOW gate = done, MEDIUM = élevé en 11.1.bis,
nouvel item HIGH (Fix A) = done ; Change Log + File List (ajout `models/topology.py`) à jour.

### 4.2 — sprint-status.yaml

```
OLD:
  11-1-msunpv-routeursolaire-sensors-lecture-seule: review  # dev-story 2026-06-17 — multi-sensor eq553 (8 sensors), pytest 823 vert, gate terrain waived

NEW:
  11-1-msunpv-routeursolaire-sensors-lecture-seule: review  # dev-story 2026-06-17 — multi-sensor eq553 ; gate terrain PASS box 192.168.1.21 (65 sensors publiés) ; Fix A éligibilité sans generic_type ; pytest 825 vert
  11-1-bis-multi-sensor-lifecycle-depublication-secondaires: backlog  # correct-course 2026-06-17 — dépublication exhaustive des sensors secondaires (anti-ghosts HA), Follow-up MEDIUM élevé depuis 11.1
```

Rationale : refléter le gate PASS réel et matérialiser la Story 11.1.bis dans le backlog de l'epic.

### 4.3 — Nouvelle Story 11.1.bis (via workflow create-story)

Titre : « Multi-sensor lifecycle — dépublication exhaustive des sensors secondaires (anti-ghosts HA) ».
Brief de scope : à la suppression / désactivation / exclusion / retype d'un eqLogic multi-sensor,
nettoyer **tous** les topics discovery secondaires `jeedom2ha_<eq>_<cmd>/config` (pas seulement le
primaire), avec gate terrain de dépublication (vérifier 0 ghost résiduel sur la box). Stocker les
mappings/publications secondaires par `eq_id` pour permettre ce nettoyage.

## 5. Implementation Handoff

- **Scope classification : Moderate** — réorganisation backlog (ajout 11.1.bis) + correction record 11.1.
- **Handoff** :
  - Story 11.1 → review owner : peut clore vers `done` (gate PASS, pytest 825).
  - Story 11.1.bis → create-story (SM) puis dev-story.
- **Success criteria 11.1.bis** : dépublication d'un eqLogic msunpv ne laisse aucun topic
  `jeedom2ha_<eq>_<cmd>/config` retained sur le broker ; gate terrain de dépublication PASS ;
  non-régression mono-entité.
