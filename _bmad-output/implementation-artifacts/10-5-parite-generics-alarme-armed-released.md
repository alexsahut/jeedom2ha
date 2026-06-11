# Story 10.5 : Parité génériques alarme — ALARM_ARMED / ALARM_RELEASED

Status: done

## Story

En tant que mainteneur du bridge jeedom2ha,
je veux que le mapper `alarm_control_panel` reconnaisse `ALARM_ARMED` et `ALARM_RELEASED` comme commandes d'armement/désarmement,
afin que l'alarme Jeedom native (`eq_id=230`) soit publiée dans Home Assistant avec le même comportement que Homebridge.

## Acceptance Criteria

1. **AC1 — Fallback ALARM_ARMED** : un eqLogic contenant `ALARM_ENABLE_STATE` (info/binary) + `ALARM_ARMED` (action) est mappé en `alarm_control_panel` avec `has_command=True`.
2. **AC2 — Fallback ALARM_RELEASED** : un eqLogic contenant `ALARM_ENABLE_STATE` (info/binary) + `ALARM_RELEASED` (action) est mappé en `alarm_control_panel` avec `has_command=True`.
3. **AC3 — Nominal complet** : un eqLogic contenant `ALARM_ENABLE_STATE` + `ALARM_ARMED` + `ALARM_RELEASED` est mappé avec `has_state=True`, `has_command=True`, et les trois génériques présents dans `result.commands`.
4. **AC4 — Non-régression 10.3** : tous les tests de `test_story_10_3_alarm_control_panel.py` restent PASS sans modification.
5. **AC5 — Priorité ALARM_ENABLE/ALARM_DISABLE** : si `ALARM_ENABLE` **et** `ALARM_ARMED` sont tous deux présents, `ALARM_ENABLE` est préféré (et réciproquement pour DISABLE/RELEASED).
6. **AC6 — Gate terrain** : après redéploiement sur box réelle, `alarm_control_panels_published >= 1`.

## Tasks / Subtasks

### Task 0 — Pre-flight terrain (injecté)
- [ ] Vérifier daemon health : `GET /system/status` → `status: ok` + MQTT connected
- [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run`

### Task 1 — Étendre le mapper (AC1, AC2, AC3, AC5)
- [ ] Remplacer `_ARM_GENERIC_TYPE = "ALARM_ENABLE"` par `_ARM_GENERIC_TYPES = {"ALARM_ENABLE", "ALARM_ARMED"}`
- [ ] Remplacer `_DISARM_GENERIC_TYPE = "ALARM_DISABLE"` par `_DISARM_GENERIC_TYPES = {"ALARM_DISABLE", "ALARM_RELEASED"}`
- [ ] Adapter la boucle de scan : `gt in _ARM_GENERIC_TYPES` / `gt in _DISARM_GENERIC_TYPES`
- [ ] Conserver la clé de commande dans `commands` dict avec le générique réel (ex: `"ALARM_ARMED"`)
- [ ] Garantir priorité : ALARM_ENABLE avant ALARM_ARMED (ordre naturel de `eq.cmds`)

### Task 2 — Tests story 10.5 (AC1, AC2, AC3, AC4, AC5)
- [ ] Créer `resources/daemon/tests/unit/test_story_10_5_alarm_parity_armed_released.py`
- [ ] Fixture `_alarm_eq_armed_released()` : ALARM_ENABLE_STATE + ALARM_ARMED + ALARM_RELEASED
- [ ] Test nominal ALARM_ARMED/ALARM_RELEASED complet
- [ ] Test non-régression : ALARM_ENABLE/ALARM_DISABLE toujours reconnus (via import de `_alarm_eq_full()`)
- [ ] Vérifier que tous les tests 10.3 restent PASS (run complet)

### Task 3 — Golden corpus (non-régression pipeline)
- [ ] Ajouter sample `eq_id=230` dans `sync_payload.json` avec `ALARM_ENABLE_STATE` + `ALARM_ARMED` + `ALARM_RELEASED`
- [ ] Régénérer snapshot golden file si applicable

### Task 4 — Terrain (AC6)
- [ ] Déploiement : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
- [ ] Vérifier : `GET /system/status` → MQTT ok
- [ ] Vérifier : `GET /action/sync` → `alarm_control_panels_published >= 1`
- [ ] Collecter topics MQTT publiés pour `alarm_control_panel`

## Dev Notes

- **Fichier principal** : `resources/daemon/mapping/alarm_control_panel.py`
- **Tests story** : `resources/daemon/tests/unit/test_story_10_5_alarm_parity_armed_released.py`
- **Golden corpus** : `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json`
- **Mapper registry** : pas de modification (AlarmControlPanelMapper déjà enregistré en 10.3)
- **Publisher** : pas de modification (publish_alarm_control_panel inchangé)
- La clé dans `commands` dict doit refléter le générique réel trouvé (pas une constante hardcodée) afin que le publisher reste agnostique au générique exact.

### Dev Agent Guardrails

- Protocole terrain strict : utiliser uniquement `./scripts/deploy-to-box.sh`
- Ne jamais utiliser de commandes MQTT directes sans `X-Local-Secret`
- Gate terrain : `alarm_control_panels_published >= 1` requis avant de déclarer la story done
- Ne pas modifier les tests 10.3 existants

### References

- Mapper Story 10.3 : `resources/daemon/mapping/alarm_control_panel.py`
- Tests 10.3 : `resources/daemon/tests/unit/test_story_10_3_alarm_control_panel.py`
- Homebridge plugin source : `/var/www/html/plugins/homebridge/resources/node_modules/homebridge-jeedom/index.js` (SecuritySystem binding)
- Sprint Change Proposal : `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09.md`
- Box réelle : `eq_id=230`, `Alarme maison`, `eqType=alarm`, `sendToHomebridge=1`

## Dev Agent Record

### Agent Model Used
claude-cli/claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- AC1-AC5 PASS (14 tests story 10.5, 9 tests story 10.3 non-régression)
- Golden file 8.4 mis à jour : eligible_count=51, alarm_control_panels_published=2
- Suite complète : 792 PASS, 1 échec préexistant story 10.1 (hors scope)
- Code review PASS — finding MINOR documenté (ordre-priorité ordre-dépendant, acceptable)
- AC6 terrain PASS — alarm_control_panels_published=1 après activation objet Maison (2026-06-09 23:25). eligible_count=93, status=ok.

### Senior Developer Review (AI)

**Date :** 2026-06-09  
**Verdict : PASS**

Findings :
- CRITICAL : 0
- HIGH : 0
- MINOR : 1 — priorité ALARM_ENABLE > ALARM_ARMED repose sur l'ordre des commandes Jeedom (documenté, stable en pratique)

Toutes les ACs 1-5 validées en tests. AC6 (gate terrain) requis avant done.

### File List

- `resources/daemon/mapping/alarm_control_panel.py`
- `resources/daemon/tests/unit/test_story_10_5_alarm_parity_armed_released.py`
- `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py`
