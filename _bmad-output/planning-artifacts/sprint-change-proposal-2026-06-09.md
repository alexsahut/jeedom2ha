# Sprint Change Proposal — 2026-06-09
# Parité génériques alarme : ALARM_ARMED / ALARM_RELEASED

**Déclenché par :** constat terrain post-Story 10.3 (alarm_control_panels_published=0 sur box réelle)  
**Date :** 2026-06-09  
**Workflow :** correct-course  

---

## Section 1 : Résumé du problème

### Constat
Après déploiement Story 10.3 (`AlarmControlPanelMapper`), l'entité `alarm_control_panel` n'est pas publiée sur la box réelle :

```
alarm_control_panels_published=0
No exposed entities found in domain(s): alarm_control_panel
```

### Cause racine
L'alarme Jeedom réelle (`eq_id=230`, `Alarme maison`, `eqType=alarm`) expose les génériques suivants :

| Générique | Type | Rôle |
|---|---|---|
| `ALARM_ENABLE_STATE` | info/binary | état armé (✓ déjà supporté) |
| `ALARM_STATE` | info/binary | état alarme active |
| **`ALARM_ARMED`** | action | **commande armer** |
| **`ALARM_RELEASED`** | action | **commande désarmer** |
| `ALARM_SET_MODE` | action | sélecteur mode |
| `ALARM_MODE` | info | mode courant |

Le mapper Story 10.3 attend `ALARM_ENABLE` (armer) et `ALARM_DISABLE` (désarmer), qui sont les génériques de la plugin Jeedom générique virtuelle mais **pas** ceux du plugin alarme natif Jeedom utilisé sur la box.

Source terrain : `/var/www/html/plugins/homebridge/resources/node_modules/homebridge-jeedom/index.js`  
(SecuritySystem binding sur `ALARM_ARMED`/`ALARM_RELEASED`/`ALARM_ENABLE_STATE`)

### Écart de parité Homebridge → HA
Homebridge-Jeedom expose ce SecuritySystem vers HomeKit en utilisant exactement `ALARM_ARMED` et `ALARM_RELEASED`. La Story 10.3 était censée rétablir cette parité dans HA — elle est incomplète sur ce point.

---

## Section 2 : Analyse d'impact

### Impact Épic
- **pe-epic-10** : impact direct sur l'objectif "parité minimale utile Homebridge → HA" (Story 10.3)

### Impact Stories
- **Story 10.3** : déclarée `done` mais gate terrain non atteinte (alarm_control_panels_published=0)  
  → La story reste `done` (critères d'acceptance en test d'isolation PASS) mais le gate terrain réel est bloqué  
  → Correction apportée par nouvelle story corrective 10-5

### Impact artefacts
- `resources/daemon/mapping/alarm_control_panel.py` : constantes `_ARM_GENERIC_TYPE`/`_DISARM_GENERIC_TYPE` → étendre aux fallbacks
- `resources/daemon/tests/unit/test_story_10_3_alarm_control_panel.py` : à conserver sans modification (tests 10.3 restent verts)
- Nouveau fichier de test story 10.5 à créer

### Impact technique
- Pas de changement MQTT ni de changement de publisher — seul le mapper est concerné
- Le payload HA reste identique (state_topic / command_topic / DISARM / ARM_AWAY / ARM_HOME)
- Golden corpus : ajout d'un sample `eq_id=230` avec `ALARM_ARMED`/`ALARM_RELEASED`

---

## Section 3 : Approche recommandée

**Ajustement direct** — extension minimale du mapper, pas de rollback Story 10.3.

- Étendre `_ARM_GENERIC_TYPE` en `_ARM_GENERIC_TYPES = {"ALARM_ENABLE", "ALARM_ARMED"}`
- Étendre `_DISARM_GENERIC_TYPE` en `_DISARM_GENERIC_TYPES = {"ALARM_DISABLE", "ALARM_RELEASED"}`
- Préserver la priorité existante (ALARM_ENABLE avant ALARM_ARMED, ALARM_DISABLE avant ALARM_RELEASED)

**Effort :** S (< 2h)  
**Risque :** faible — changement additif, tests 10.3 restent verts  
**Impact timing :** aucun — mini-story corrective dans le sprint courant pe-epic-10

---

## Section 4 : Propositions de changement détaillées

### Changement 1 — Mapper `alarm_control_panel.py`

```
Fichier : resources/daemon/mapping/alarm_control_panel.py

AVANT :
_ARM_GENERIC_TYPE = "ALARM_ENABLE"
_DISARM_GENERIC_TYPE = "ALARM_DISABLE"

APRÈS :
_ARM_GENERIC_TYPES = {"ALARM_ENABLE", "ALARM_ARMED"}
_DISARM_GENERIC_TYPES = {"ALARM_DISABLE", "ALARM_RELEASED"}
```

Adapation de la boucle `for cmd in eq.cmds` pour tester `gt in _ARM_GENERIC_TYPES` / `gt in _DISARM_GENERIC_TYPES`.

Rationale : `ALARM_ARMED`/`ALARM_RELEASED` sont les génériques natifs du plugin alarme Jeedom, exposés tel quel par Homebridge vers HomeKit.

### Changement 2 — Tests story 10.5

Nouveau fichier `test_story_10_5_alarm_parity_armed_released.py` avec :
- fixture `_alarm_eq_armed_released()` : `ALARM_ENABLE_STATE` + `ALARM_ARMED` + `ALARM_RELEASED`
- tests : mapping nominal, has_command=True, commandes détectées
- test de non-régression : ALARM_ENABLE/ALARM_DISABLE toujours reconnus

### Changement 3 — Golden corpus

Ajout d'un sample `eq_id=230` (`Alarme maison`, `ALARM_ENABLE_STATE` + `ALARM_ARMED` + `ALARM_RELEASED`) dans le corpus de référence.

---

## Section 5 : Handoff implémentation

**Scope : Minor** — directement exécutable par le dev agent.

**Critères de succès :**
1. Tests 10.3 toujours PASS (non-régression)
2. Tests 10.5 PASS (nouveau comportement ALARM_ARMED/ALARM_RELEASED)
3. Gate terrain : `alarm_control_panels_published >= 1` après redéploiement

**Story créée :** `10-5-parite-generics-alarme-armed-released`  
**Responsible :** dev-story workflow

---

*Correct Course workflow complet, Alexandre. Change Proposal approuvé — scope Minor, routé dev-story.*
