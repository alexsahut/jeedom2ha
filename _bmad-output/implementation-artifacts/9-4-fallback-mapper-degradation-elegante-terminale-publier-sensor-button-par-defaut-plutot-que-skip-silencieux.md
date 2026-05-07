# Story 9.4 : FallbackMapper §11 — dégradation élégante terminale (publier sensor/button par défaut plutôt que skip silencieux)

Status: review

## Story

En tant qu'utilisateur,
je veux que les équipements Jeedom dont le typage permet une projection structurellement valide (au moins une commande Info ou une commande Action) soient publiés par défaut en `sensor` ou `button` plutôt qu'omis silencieusement,
afin de tenir la promesse §11 du cadrage initial : « dégradation élégante : sensor/button plutôt qu'un type 'riche' incorrect ».

## Acceptance Criteria

**AC1 — Fallback vers sensor**
**Given** un eqLogic Jeedom éligible avec au moins une commande `Info` (type="info", any sub_type, generic_type quelconque) non capturée par les mappers spécifiques
**When** le `FallbackMapper` est invoqué en slot terminal
**Then** il produit un `MappingResult` :
- `ha_entity_type = "sensor"`, `confidence = "ambiguous"`
- `reason_code = "fallback_sensor_default"`
- `capabilities = SensorCapabilities(has_state=True)`
- `reason_details = {}` (device_class=None, unit_of_measurement=None — publish_sensor les gère)
- La première commande Info trouvée est sélectionnée (ordre itération eq.cmds)

**AC2 — Fallback vers button**
**Given** un eqLogic Jeedom éligible avec au moins une commande `Action` (type="action", any sub_type, generic_type quelconque) ET sans commande Info exploitable
**When** le `FallbackMapper` est invoqué
**Then** il produit un `MappingResult` :
- `ha_entity_type = "button"`, `confidence = "ambiguous"`
- `reason_code = "fallback_button_default"`
- `capabilities = SwitchCapabilities(has_on_off=True)`
- `reason_details = {"command_topic": f"jeedom2ha/{eq_id}/cmd"}`
- La première commande Action trouvée est sélectionnée

**AC3 — Retour None tracé (no_projection_possible)**
**Given** un eqLogic Jeedom éligible sans aucune commande `Info` ni `Action` exploitable
**When** le `FallbackMapper` est invoqué
**Then** il retourne `None`
**And** dans le diagnostic, `reason_code = "no_projection_possible"` est exposé (pas `"no_mapping"` — pas un skip silencieux)

**AC4 — cause_action = None strictement pour tous les cas fallback**
**Given** tout `MappingResult` produit par `FallbackMapper` (sensor ou button, confidence="ambiguous")
**When** le pipeline produit la cause UX via `resolve_cause_ux(reason_code, step)`
**Then** `cause_action = None` strictement, sans exception
**And** aucun CTA utilisateur n'est exposé — règle Epic 6 « no faux CTA » Story 6.3 maintenue

**AC5 — cause_label non-null pour dégradation élégante (FR32)**
**Given** le diagnostic d'un équipement projeté par FallbackMapper (sensor ou button)
**When** son `cause_label` est inspecté
**Then** `cause_label` indique clairement « projection en dégradation élégante »
**And** `confidence = "ambiguous"` signale à l'utilisateur que le typage Jeedom pourrait être amélioré

**AC6 — Publication réelle via publish_sensor / publish_button existants**
**Given** un mapping FallbackMapper (sensor ou button) avec `is_valid=True` et politique de confiance qui inclut "ambiguous"
**When** le pipeline exécute l'étape 5
**Then** `publish_sensor` (pour sensor) ou `publish_button` (pour button) est invoqué sans aucune modification de ces méthodes
**And** le payload MQTT Discovery est conforme aux contraintes de `ha-projection-reference.md` (sensor.mqtt / button.mqtt)

**AC7 — Trois nouveaux cause_codes dans cause_mapping.py**
**Given** les reason_codes `"fallback_sensor_default"`, `"fallback_button_default"`, `"no_projection_possible"`
**When** `reason_code_to_cause()` est appelé
**Then** chaque code retourne `(cause_code, cause_label, cause_action)` non-null/non-null/None
**And** aucun string literal de ces codes n'est dispersé hors de `cause_mapping.py`

**AC8 — Extension golden-file (PE8-AI-04 discipline)**
**Given** le golden-file Story 8.4 (43 équipements)
**When** il est étendu avec 5 équipements fallback représentatifs (IDs 10000-10004)
**Then** la non-régression du corpus initial (43 équipements) reste verte
**And** `sync_payload.json` contient les 5 nouveaux eqLogics
**And** `expected_sync_snapshot.json` contient les 5 résultats attendus

**AC9 — test_story_8_1 : FallbackMapper n'est plus no-op**
**Given** `test_ac2_fallback_mapper_always_returns_none` dans `test_story_8_1_mapper_registry.py`
**When** FallbackMapper est appelé avec un eq ayant une commande Info
**Then** le test est mis à jour pour refléter que FallbackMapper produit un mapping (sensor ambiguous) et ne retourne plus None systématiquement

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Implémenter FallbackMapper avec logique broadband (AC1, AC2, AC3)
  - [x] 1.1 Modifier `resources/daemon/mapping/fallback.py` — remplacer le no-op par la logique réelle
  - [x] 1.2 Prédicat `_has_info_command(eq) -> bool` : `any((cmd.type or "").lower() == "info" for cmd in eq.cmds)`
  - [x] 1.3 Prédicat `_has_action_command(eq) -> bool` : `any((cmd.type or "").lower() == "action" for cmd in eq.cmds)`
  - [x] 1.4 Logique de sélection : première commande Info trouvée (ordre itération eq.cmds)
  - [x] 1.5 Cas sensor : construire `MappingResult(ha_entity_type="sensor", confidence="ambiguous", reason_code="fallback_sensor_default", capabilities=SensorCapabilities(has_state=True), reason_details={}, ...)`
  - [x] 1.6 Cas button : construire `MappingResult(ha_entity_type="button", confidence="ambiguous", reason_code="fallback_button_default", capabilities=SwitchCapabilities(has_on_off=True), reason_details={"command_topic": f"jeedom2ha/{eq.id}/cmd"}, ...)`
  - [x] 1.7 Cas None : aucune commande Info ni Action → retourner `None` (no_projection_possible géré en AC3)

- [x] Task 2 — Ajout des 3 cause_codes dans cause_mapping.py (AC7)
  - [x] 2.1 Modifier `resources/daemon/models/cause_mapping.py`, section `_REASON_CODE_TO_CAUSE`
  - [x] 2.2 Ajouter `"fallback_sensor_default"` → `("fallback_sensor_default", "Projection en dégradation élégante — capteur par défaut", None)`
  - [x] 2.3 Ajouter `"fallback_button_default"` → `("fallback_button_default", "Projection en dégradation élégante — bouton par défaut", None)`
  - [x] 2.4 Ajouter `"no_projection_possible"` → `("no_projection_possible", "Projection impossible — aucune commande exploitable détectée", None)`
  - [x] 2.5 Vérifier que le commentaire d'en-tête (ARTEFACT FIGÉ) est mis à jour pour mentionner Story 9.4

- [x] Task 3 — Mise à jour http_server.py (AC3, AC5)
  - [x] 3.1 Dans `_DIAGNOSTIC_MESSAGES` (ligne ~1482), ajouter l'entrée `"no_projection_possible"`
  - [x] 3.2 Dans la boucle de rendu diagnostic (ligne ~1851), remplacer `reason_code = "no_mapping"` par `reason_code = "no_projection_possible"` dans la branche `map_result is None` pour équipement éligible
  - [x] 3.3 Vérifier que `_TYPES_WITHOUT_STATE_TOPIC = {"button"}` (ligne ~70) couvre déjà les mappings button issus de FallbackMapper — NE PAS MODIFIER (déjà correct Story 9.3) ✓

- [x] Task 4 — Extension golden-file (AC8, PE8-AI-04)
  - [x] 4.1 Ajouter dans `sync_payload.json` après les IDs 9000-9002, les 5 eqLogics fallback (IDs 10000-10004)
  - [x] 4.2 Ajouter dans `expected_sync_snapshot.json` les 5 résultats attendus
  - [x] 4.3 Mettre à jour `_assert_corpus_shape` dans `test_story_8_4_golden_file.py` : `assert len(eq_ids) == 48`
  - [x] 4.4 Les 43 équipements précédents (IDs 1000-9002) ne sont PAS modifiés — confirmé avant PR

- [x] Task 5 — Tests unitaires FallbackMapper (AC1-AC7)
  - [x] 5.1 Créer `resources/daemon/tests/unit/test_story_9_4_fallback_mapper.py`
  - [x] 5.2 Tests FallbackMapper — cas sensor : Info string, Info color, Info+Action→sensor wins
  - [x] 5.3 Tests FallbackMapper — cas button : Action slider, Action string, command_topic
  - [x] 5.4 Tests FallbackMapper — cas None : type=event, aucune commande
  - [x] 5.5 Tests cause_mapping : 3 codes → cause_action is None
  - [x] 5.6 Test non-régression : mappers spécifiques non affectés

- [x] Task 6 — Mise à jour test_story_8_1_mapper_registry.py (AC9)
  - [x] 6.1 Supprimer `test_ac2_fallback_mapper_always_returns_none` et remplacer par tests comportement réel
  - [x] 6.2 Ajouter : FallbackMapper avec eq ayant Info → sensor non-None
  - [x] 6.3 Ajouter : FallbackMapper avec eq sans Info ni Action → None
  - [x] 6.4 Vérifier que l'ordre canonique final est toujours : `[LightMapper, CoverMapper, SwitchMapper, BinarySensorMapper, SensorMapper, ButtonMapper, FallbackMapper]`

- [x] Task 7 — Validation non-régression + terrain (AC1-AC9)
  - [x] 7.1 Suite complète : 732/732 PASS — zéro régression
  - [x] 7.2 `test_story_8_4_golden_file.py` : PASS avec 48 équipements
  - [ ] 7.3 Déployer sur box Alexandre et relever la mesure terrain
  - [ ] 7.4 Documenter la mesure dans les Completion Notes (gate terrain pe-epic-9 PE8-AI-05)

### Review Follow-ups (AI)

- [ ] [AI-Review][LOW] Incohérence `cause_code`/`cause_label` pour `no_projection_possible` dans le diagnostic : `cause_code="no_projection_possible"` mais `cause_label/cause_action` proviennent de `"no_commands"` via le fallback conservateur de `_build_traceability` (ligne ~1647). Cause racine : `"no_projection_possible"` absent de `_CLOSED_REASON_MAP` → `_build_traceability` retourne `"no_commands"` au lieu de `"no_projection_possible"`. Analyser si l'ajout de `"no_projection_possible": "no_projection_possible"` dans `_CLOSED_REASON_MAP` suffit (nécessite `"no_projection_possible"` dans `_CLOSED_REASON_CODES`). [transport/http_server.py:1567-1591, :1639-1647 | fixtures/golden_corpus/expected_sync_snapshot.json:eq_id=10004]

## Dev Notes

### Architecture et patterns à suivre

**Principe de broadband** — FallbackMapper est délibérément non-sélectif sur sub_type et generic_type :
- `Info ANY_SUB_TYPE + ANY_GENERIC_TYPE` → sensor (même si sub_type="string" ou "color" ou "slider")
- `Action ANY_SUB_TYPE + ANY_GENERIC_TYPE` → button (même si sub_type="slider" ou "string", PAS seulement "other")
- `Rien d'Info ni d'Action` → None (cas extrêmement rare — type de commande non standard)

**Priorité Info > Action** : si un eq a à la fois des commandes Info et Action, le FallbackMapper produit `sensor`. Les eqLogics purement Action (ex. variateur, texte) qui n'ont PAS d'Info seront des buttons.

**Réutilisation stricte** :
- `SensorCapabilities(has_state=True)` — MÊME que SensorMapper (Story 9.1)
- `SwitchCapabilities(has_on_off=True)` — MÊME que ButtonMapper (Story 9.3)
- NE PAS créer `FallbackCapabilities` ou `AmbiguousCapabilities`
- `publish_sensor` et `publish_button` SANS MODIFICATION — ils gèrent device_class=None

**Pattern MappingResult pour sensor fallback** :
```python
MappingResult(
    ha_entity_type="sensor",
    confidence="ambiguous",
    reason_code="fallback_sensor_default",
    jeedom_eq_id=eq.id,
    ha_unique_id=f"jeedom2ha_eq_{eq.id}",
    ha_name=eq.name,
    suggested_area=snapshot.get_suggested_area(eq.id),
    commands={cmd.generic_type or "fallback": cmd},   # première commande Info
    capabilities=SensorCapabilities(has_state=True),
    reason_details={},
)
```

**Pattern MappingResult pour button fallback** :
```python
MappingResult(
    ha_entity_type="button",
    confidence="ambiguous",
    reason_code="fallback_button_default",
    jeedom_eq_id=eq.id,
    ha_unique_id=f"jeedom2ha_eq_{eq.id}",
    ha_name=eq.name,
    suggested_area=snapshot.get_suggested_area(eq.id),
    commands={cmd.generic_type or "fallback": cmd},   # première commande Action
    capabilities=SwitchCapabilities(has_on_off=True),
    reason_details={"command_topic": f"jeedom2ha/{eq.id}/cmd"},
)
```

**Cas `commands` dict avec generic_type None** : si `cmd.generic_type is None`, utiliser `"fallback"` comme clé dict pour éviter `{None: cmd}` qui casse `commands.values()`. L'éligibilité garantit `any(cmd.generic_type is not None for cmd in eq.cmds)` mais pas forcément sur la commande sélectionnée.

### cause_mapping.py — 3 entrées à ajouter

Dans `_REASON_CODE_TO_CAUSE` (ARTEFACT FIGÉ — mettre à jour le commentaire d'en-tête pour inclure Story 9.4) :

```python
# --- 3 codes dégradation élégante Story 9.4 (§11 cadrage) ---
# cause_action = None : conformité règle no faux CTA (Story 6.3)
"fallback_sensor_default": (
    "fallback_sensor_default",
    "Projection en dégradation élégante — capteur par défaut",
    None,
),
"fallback_button_default": (
    "fallback_button_default",
    "Projection en dégradation élégante — bouton par défaut",
    None,
),
"no_projection_possible": (
    "no_projection_possible",
    "Projection impossible — aucune commande exploitable détectée",
    None,
),
```

**Pourquoi cause_action = None** : règle Epic 6 / Story 6.3 « no faux CTA » — aucune surface dans jeedom2ha ne permet à l'utilisateur d'agir directement sur ces cas. La Story 9.5 (re-homée depuis 7.5) ajoutera le CTA "compléter le typage Jeedom" pour les fallback, mais PAS cette story.

### http_server.py — 2 changements minimes

**Changement 1 — `_DIAGNOSTIC_MESSAGES` (ligne ~1487, après l'entrée `"no_mapping"`)** :
```python
"no_projection_possible": (
    "Aucune commande Info ou Action exploitable — projection impossible même en dégradation.",
    "Vérifiez que l'équipement possède des commandes Info ou Action dans Jeedom.",
    False,
),
```

**Changement 2 — boucle de rendu diagnostic (ligne ~1851)** :
```python
# AVANT (à remplacer) :
else:
    reason_code = "no_mapping"
    confidence = "Ignoré"
    status = get_primary_status(reason_code)

# APRÈS :
else:
    reason_code = "no_projection_possible"
    confidence = "Ignoré"
    status = get_primary_status(reason_code)
```

**Pourquoi ce changement est sûr** : après Story 9.4, le seul cas où `map_result is None` pour un équipement éligible est celui où FallbackMapper a retourné None (rien d'exploitable). Avant Story 9.4, `no_mapping` était correct pour tous les cas "aucun mapper n'a matché". Après, FallbackMapper a essayé et échoué explicitement → `no_projection_possible` est sémantiquement correct.

**NE PAS toucher** `_build_traceability` (ligne ~1601) : le sub-bloc pipeline step 2 reste `"skipped_no_mapping_candidate"` dans la trace brute — c'est le contrat du pipeline canonique, distinct de la cause UX.

**NE PAS toucher** `_TYPES_WITHOUT_STATE_TOPIC = {"button"}` (ligne ~70) : déjà couvre les mappings button issus de FallbackMapper ✓

### Publication via publish_sensor / publish_button

FallbackMapper → sensor : `reason_details = {}` → `_build_sensor_payload` lit `device_class = reason_details.get("device_class")` → None → pas de champ `device_class` dans le payload HA. ✓ Compatible.

FallbackMapper → button : `reason_details = {"command_topic": "jeedom2ha/{eq_id}/cmd"}` → `_build_button_payload` lit `command_topic = reason_details.get("command_topic", f"jeedom2ha/{eq_id}/cmd")`. ✓ Identique à ButtonMapper.

**Décision de publication** : `confidence = "ambiguous"` → `decide_publication()` applique la `confidence_policy`. Avec politique "sure_only" (défaut), ces mappings ne seront PAS publiés (`should_publish=False`, `reason="ambiguous_skipped"`). Ils apparaissent dans le diagnostic avec cause "ambiguous_skipped" (cause existante) → NE PAS modifier decide_publication ni confidence_policy pour cette story.

**Cela signifie** : en pratique sur la box réelle avec politique "sure_only", les équipements fallback apparaissent dans le diagnostic comme "non publiés" mais avec cause_label explicite plutôt que disparaître silencieusement. Objectif §11 atteint : visibilité sans publication spéculative.

### Golden-file — 5 équipements fallback à ajouter

**Dans `sync_payload.json`** (après les IDs 9000-9002) :

```json
{
  "id": "10000",
  "name": "Capteur générique non typé",
  "object_id": "1",
  "eq_type": "virtual",
  "generic_type": null,
  "is_enable": "1",
  "is_visible": "1",
  "cmds": [
    {
      "id": "100001",
      "name": "État",
      "generic_type": "GENERIC_INFO",
      "type": "info",
      "sub_type": "string"
    }
  ]
},
{
  "id": "10001",
  "name": "Couleur ambiante",
  "object_id": "1",
  "eq_type": "virtual",
  "generic_type": null,
  "is_enable": "1",
  "is_visible": "1",
  "cmds": [
    {
      "id": "100011",
      "name": "Couleur",
      "generic_type": "COLOR",
      "type": "info",
      "sub_type": "color"
    }
  ]
},
{
  "id": "10002",
  "name": "Variateur slider",
  "object_id": "1",
  "eq_type": "virtual",
  "generic_type": null,
  "is_enable": "1",
  "is_visible": "1",
  "cmds": [
    {
      "id": "100021",
      "name": "Niveau",
      "generic_type": "VOLUME_SET",
      "type": "action",
      "sub_type": "slider"
    }
  ]
},
{
  "id": "10003",
  "name": "Saisie texte",
  "object_id": "1",
  "eq_type": "virtual",
  "generic_type": null,
  "is_enable": "1",
  "is_visible": "1",
  "cmds": [
    {
      "id": "100031",
      "name": "Texte",
      "generic_type": "SET_TEXT",
      "type": "action",
      "sub_type": "string"
    }
  ]
},
{
  "id": "10004",
  "name": "Commande interne événement",
  "object_id": "1",
  "eq_type": "virtual",
  "generic_type": null,
  "is_enable": "1",
  "is_visible": "1",
  "cmds": [
    {
      "id": "100041",
      "name": "Événement",
      "generic_type": "JEEDOM_CHANNEL",
      "type": "event",
      "sub_type": "other"
    }
  ]
}
```

**Pourquoi ces IDs** :
- 10000 : Info string, `generic_type="GENERIC_INFO"` — réel Jeedom, non dans SensorMapper (numeric only) → FallbackMapper sensor
- 10001 : Info color, `generic_type="COLOR"` — réel Jeedom, non dans SensorMapper → FallbackMapper sensor
- 10002 : Action slider — ButtonMapper ne prend que sub_type="other" → FallbackMapper button
- 10003 : Action string — ButtonMapper ne prend que sub_type="other" → FallbackMapper button
- 10004 : type="event" — ni Info ni Action → FallbackMapper → None (no_projection_possible)

**Dans `expected_sync_snapshot.json`** : ajouter les 5 résultats correspondants. Pour 10000-10003, le mapping attendu est :
- 10000/10001 : `ha_entity_type="sensor"`, `confidence="ambiguous"`, `reason_code="fallback_sensor_default"`, `should_publish=False` (confidence_policy "sure"), `reason="ambiguous_skipped"`
- 10002/10003 : `ha_entity_type="button"`, `confidence="ambiguous"`, `reason_code="fallback_button_default"`, `should_publish=False`, `reason="ambiguous_skipped"`
- 10004 : pas de mapping (`map_result=None`) — équipement éligible sans mapping → absent de `mappings` dict mais présent dans `eligibility`

**Pour 10004 dans le golden-file** : l'équipement sera dans `eligibility` (is_eligible=True) mais absent de `mappings`. Le snapshot doit refléter cet état. Vérifier comment le golden-file capture les équipements sans mapping.

**NE PAS régénérer** `expected_sync_snapshot.json` via le pipeline — construire manuellement les 5 nouvelles entrées pour respecter la discipline PE8-AI-04.

**`_assert_corpus_shape`** : passer de 43 à 48 équipements.

### Cascade order — inchangé

```
MapperRegistry._mappers = [
    LightMapper(),         # LIGHT_* → ha_entity_type="light"
    CoverMapper(),         # FLAP_* → ha_entity_type="cover"
    SwitchMapper(),        # ENERGY_* → ha_entity_type="switch"
    BinarySensorMapper(),  # Info binary types → ha_entity_type="binary_sensor"
    SensorMapper(),        # Info numeric known types → ha_entity_type="sensor"
    ButtonMapper(),        # Action "other" types → ha_entity_type="button"
    FallbackMapper(),      # Broadband terminal : sensor/button/None ← Story 9.4
]
```

**NE PAS modifier** `registry.py` — l'ordre et l'enregistrement sont corrects depuis Story 8.1/9.3.

### test_story_8_1_mapper_registry.py — mise à jour obligatoire (AC9)

Le test `test_ac2_fallback_mapper_always_returns_none` (lignes 136-141) vérifie que FallbackMapper retourne toujours None. Ce test doit être remplacé par :

```python
def test_ac2_fallback_mapper_with_info_returns_sensor():
    """FallbackMapper produit sensor pour eq avec commande Info (Story 9.4)."""
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="info", sub_type="string", generic_type="GENERIC_INFO")])
    result = fallback.map(eq, _make_snapshot())
    assert result is not None
    assert result.ha_entity_type == "sensor"
    assert result.confidence == "ambiguous"
    assert result.reason_code == "fallback_sensor_default"


def test_ac2_fallback_mapper_without_info_action_returns_none():
    """FallbackMapper retourne None si aucune commande Info ni Action (Story 9.4)."""
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="event", sub_type="other", generic_type="JEEDOM_CHANNEL")])
    assert fallback.map(eq, _make_snapshot()) is None
```

**Aussi mettre à jour `_hardcoded_cascade`** si elle liste les comportements attendus des mappers — vérifier si elle fait référence au no-op FallbackMapper.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

#### Guardrail — Golden-file discipline (PE8-AI-04)

- Les 43 équipements précédents (IDs 1000-9002) sont un verrou de non-régression
- Tout drift sur ces 43 cas bloque la PR
- Les 5 nouveaux cas (IDs 10000-10004) s'ajoutent en fin de liste, pas intercalés
- Le test `test_story_8_4_golden_file.py` doit rester vert avant ET après les ajouts
- NE PAS régénérer le snapshot depuis le code — construire manuellement les 5 nouvelles entrées
- Corpus size passe de 43 → 48

#### Guardrail — NE PAS créer de nouvelles capabilities

- Réutiliser `SensorCapabilities(has_state=True)` pour le cas sensor fallback
- Réutiliser `SwitchCapabilities(has_on_off=True)` pour le cas button fallback
- NE PAS créer `FallbackCapabilities`, `AmbiguousCapabilities`, ou toute nouvelle dataclass

#### Guardrail — NE PAS modifier publish_sensor / publish_button

- Ces méthodes gèrent déjà `device_class=None` (reason_details vide) — `_build_sensor_payload` a `device_class = reason_details.get("device_class")` qui retourne None → pas de champ dans le payload
- `_build_button_payload` lit `command_topic` depuis reason_details — déjà correct
- AUCUNE MODIFICATION de `discovery/publisher.py` pour cette story

#### Guardrail — NE PAS toucher _build_traceability

- La trace brute pipeline (step 2 sub-bloc) reste `"skipped_no_mapping_candidate"` pour map_result None
- Seul le rendu diagnostic (ligne ~1851) change `"no_mapping"` → `"no_projection_possible"`
- Ces deux couches (trace brute vs cause UX) sont intentionnellement distinctes dans le contrat 4D

#### Guardrail — cause_action = None SANS EXCEPTION

- Les 3 nouveaux cause_codes ont tous `cause_action = None`
- Story 9.5 ajoutera le CTA "compléter le typage Jeedom" — PAS Story 9.4
- Toute cause_action non-None pour ces codes serait une violation de la règle Epic 6 / Story 6.3

#### Guardrail — PRODUCT_SCOPE inchangé

- FallbackMapper n'ouvre PAS de nouveau type dans `PRODUCT_SCOPE`
- Il s'appuie uniquement sur `sensor` (Story 9.1) et `button` (Story 9.3) déjà ouverts
- NE PAS modifier `ha_component_registry.py`

#### Guardrail — NE PAS modifier

- `LightMapper`, `CoverMapper`, `SwitchMapper`, `BinarySensorMapper`, `SensorMapper`, `ButtonMapper`
- `MapperRegistry` (registry.py) — FallbackMapper est déjà en slot terminal
- `ha_component_registry.py` — PRODUCT_SCOPE inchangé
- `discovery/publisher.py` — publish_sensor et publish_button inchangés
- `discovery/registry.py` — known_types() inchangé
- Les 43 équipements existants du golden-file (IDs 1000-9002)

### Project Structure Notes

```
resources/daemon/
├── mapping/
│   ├── fallback.py           ← MODIFIER : no-op → logique réelle broadband
│   └── registry.py           (NE PAS MODIFIER — ordre inchangé depuis 8.1/9.3)
├── models/
│   └── cause_mapping.py      ← MODIFIER : +3 cause_codes
├── transport/
│   └── http_server.py        ← MODIFIER : _DIAGNOSTIC_MESSAGES + ligne ~1851
├── discovery/
│   ├── publisher.py          (NE PAS MODIFIER)
│   └── registry.py           (NE PAS MODIFIER)
├── validation/
│   └── ha_component_registry.py  (NE PAS MODIFIER — PRODUCT_SCOPE inchangé)
└── tests/
    ├── fixtures/golden_corpus/
    │   ├── sync_payload.json             ← MODIFIER : +5 eqLogics (10000-10004)
    │   └── expected_sync_snapshot.json   ← MODIFIER : +5 résultats attendus
    └── unit/
        ├── test_story_9_4_fallback_mapper.py  ← NOUVEAU
        ├── test_story_8_4_golden_file.py      ← MODIFIER : _assert_corpus_shape → 48
        └── test_story_8_1_mapper_registry.py  ← MODIFIER : test_ac2 + _hardcoded_cascade
```

### Baseline post-9.3 et mesure terrain attendue

- Baseline post-9.3 : `total_eq=278, eligible=81, published=68, ratio=83.9%`
  - lights=13, switches=10, covers=7, sensors=17, binary_sensors=11, buttons=10
- Mesure post-9.4 : `published` NE devrait PAS changer avec confidence_policy="sure" (les fallback ont `confidence="ambiguous"` → `should_publish=False`)
- L'impact terrain est visible dans le diagnostic : les équipements qui étaient "Aucun mapping compatible" deviennent "Projection en dégradation élégante" avec cause_label explicite
- Gate terrain : confirmer que aucune régression sur les 68 publiés + confirmer que les nouveaux équipements fallback apparaissent dans le diagnostic avec cause_label non-null

### Précédents Stories 9.1/9.2/9.3 — Erreurs à éviter

**L1 [LOW Story 9.2/9.3]** : `_hardcoded_cascade` dans `test_story_8_1_mapper_registry.py` — mettre à jour si elle référence le comportement no-op du FallbackMapper.

**L2 [LOW Story 9.2/9.3]** : Ne PAS régénérer `expected_sync_snapshot.json` via le pipeline — discipline golden-file PE8-AI-04. Construire manuellement les 5 nouvelles entrées.

**L3 [Story 9.4 spécifique]** : Attention à `commands={cmd.generic_type or "fallback": cmd}` dans MappingResult — si generic_type est None, le dict `{None: cmd}` peut causer des erreurs dans le pipeline. Utiliser `"fallback"` comme clé par défaut.

**L4 [Story 9.4 spécifique]** : Le cas 10004 dans le golden-file (no_projection_possible) — l'équipement est dans `eligibility` (is_eligible=True) mais ABSENT de `mappings`. Vérifier que `expected_sync_snapshot.json` gère ce cas correctement (un mapping absent n'est pas un snapshot entry).

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md#Story 9.4`] — définition complète + AC epic-level
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md#Gates epic-level pe-epic-9`] — gate terrain cloture epic
- [Source: `resources/daemon/mapping/fallback.py`] — fichier à modifier (no-op Story 8.1)
- [Source: `resources/daemon/models/cause_mapping.py`] — ARTEFACT FIGÉ — ajouter les 3 codes section `_REASON_CODE_TO_CAUSE`
- [Source: `resources/daemon/transport/http_server.py#L1431-1550`] — `_DIAGNOSTIC_MESSAGES` à étendre
- [Source: `resources/daemon/transport/http_server.py#L1850-1853`] — `reason_code = "no_mapping"` à remplacer
- [Source: `resources/daemon/mapping/sensor.py`] — pattern mapper broadband à reproduire (SensorCapabilities réutilisé)
- [Source: `resources/daemon/mapping/button.py`] — pattern command_topic dans reason_details à reproduire
- [Source: `resources/daemon/discovery/publisher.py#publish_sensor`] — gestion device_class=None déjà implémentée
- [Source: `resources/daemon/discovery/publisher.py#publish_button`] — lecture command_topic depuis reason_details
- [Source: `resources/daemon/tests/unit/test_story_8_1_mapper_registry.py#L136-141`] — test_ac2 à remplacer
- [Source: `resources/daemon/tests/unit/test_story_8_4_golden_file.py#L234-256`] — _assert_corpus_shape à mettre à jour (43→48)
- [Source: `_bmad-output/implementation-artifacts/9-3-button-mapper-publish-button-ouverture-button-dans-product-scope-sous-fr40-nfr10.md`] — Précédents L1/L2 + patterns button

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

- `_bmad-output/implementation-artifacts/9-4-fallback-mapper-degradation-elegante-terminale-publier-sensor-button-par-defaut-plutot-que-skip-silencieux.md` — story file
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 9.4 marquée ready-for-dev → review
- `resources/daemon/mapping/fallback.py` — no-op → logique broadband §11 (Info→sensor, Action→button, rien→None)
- `resources/daemon/models/cause_mapping.py` — 3 codes dégradation élégante (fallback_sensor_default, fallback_button_default, no_projection_possible), cause_action=None
- `resources/daemon/transport/http_server.py` — _DIAGNOSTIC_MESSAGES + "no_mapping" → "no_projection_possible" ligne ~1853
- `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json` — +5 eqLogics fallback (10000-10004)
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json` — +5 résultats fallback, corpus 43→48
- `resources/daemon/tests/unit/test_story_9_4_fallback_mapper.py` — NEW : 15 tests FallbackMapper + cause_mapping
- `resources/daemon/tests/unit/test_story_8_1_mapper_registry.py` — test_ac2 remplacé (no-op → comportement réel) + _hardcoded_cascade + test_ac3 unknown_eq mis à jour
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py` — _assert_corpus_shape 43→48
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py` — 2 tests mis à jour (no_mapping → no_projection_possible, v1_limitation False)
