# Story 24.6 : Ventilateurs (et aspirateurs) : équivalents fonctionnels

Status: done

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **R1 (ClaudeBox, 12/10) intégrée : story réduite.** *Établi par ClaudeBox le 12/10* : 8 équipements exposés à HomeKit portent `FAN_*` (marche, arrêt, état ; 5 aspirateurs compris), **aucun n'a de commande de vitesse**. Avec **Q7 A**, aucun ne change de type : la story devient un classement « équivalents fonctionnels » dans l'export. **`fan` n'est plus ouvert ici**, sauf apparition d'un ventilateur à vitesse. Décisions : **Q7** et **Q9** de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire avant `ready-for-dev`. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q7 A** : `fan` seulement quand un ordre de vitesse existe ; options B et C **écartées**.
- **Q9 A** (version ajustée par la R1) : l'epic 24 absorbe 18-2 et 18-4 ; **l'epic 18 garde 18-1 (`fan`)**.
- Cette story reste `draft` jusqu'à son `create-story`.

## Story

En tant que mainteneur de la parité,
je veux que les ventilateurs et aspirateurs exposés à HomeKit et publiés en `switch` soient reconnus comme fonctionnellement équivalents (marche, arrêt, état), et qu'un ventilateur à vitesse soit repéré s'il apparaît,
afin de ne pas changer le domaine d'entités qui fonctionnent par la voix, et d'ouvrir `fan` seulement quand il apporte une fonction.

**Parcours : export + documentation. Pas de code de production tant qu'aucun ventilateur à vitesse n'existe.**

## Dépendances et décisions

- Dépend de **24.2** (export) et **24.4**.
- **Q7 A** (tranchée) : `fan` seulement quand un ordre de vitesse existe. **Q9 A** (tranchée) : l'epic 18 garde 18-1 (`fan`) ; cette story ne l'absorbe pas.

## Établi par ClaudeBox le 12/10

8 équipements exposés portent des types `FAN_*` (marche, arrêt, état), dont 5 aspirateurs ; aucun n'a de commande de vitesse (`FAN_SPEED`, `ROTATION`). La famille « Robot » (`DOCK_STATE`, `DOCK`) n'est pas en cause.

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | `FAN_STATE/ON/OFF` est groupé comme un trio de `switch` depuis 14-1, publié avec son état. | `mapping/switch.py:62-64,321` ; `mapping/binary_sensor.py:21-26` |
| F2 | `FAN_SPEED_STATE` est aujourd'hui un `sensor` (tr/min) ; un futur `fan` qui porterait la vitesse devrait éviter ce doublon. | `mapping/sensor.py:51` |
| F3 | `fan.mqtt` est documenté ; `fan` n'est ni dans `HA_COMPONENT_REGISTRY` ni dans `PRODUCT_SCOPE`. | `ha-projection-reference.md` ; `validation/ha_component_registry.py:26-70` |
| F4 | Types de vitesse du core : `FAN_SPEED`, `FAN_SPEED_STATE`, `ROTATION`, `ROTATION_STATE`. | `ha-projection-reference.md:598-601` |

## Task 0 faite par ClaudeBox le 2026-11-01 (export de production, `689c5fe`)

9 équipements exposés à HomeKit portent des types `FAN_*` : 67 (plugin `pool`), 165, 506, 516, 519, 520, 521, 522, 523 (plugin `virtual`).
- Tous ont le trio `FAN_ON`, `FAN_OFF`, `FAN_STATE` ; **aucun** n'a `FAN_SPEED`, `FAN_SPEED_STATE`, `ROTATION` ni `ROTATION_STATE` : la mesure du 12/10 tient, AC4 ne se déclenche pas.
- 8 sont publiés (`probable`) avec un `switch` à état relu (`streamed`) ; 165 est désactivé dans une pièce exclue (`excluded_object`, exposition non effective, inchangé depuis 24.4).
- Le décompte « 8 » du 12/10 correspond aux 8 équipements à exposition effective.

## Décisions de ClaudeBox pour le `ready-for-dev` (2026-11-01)

- **D1. Forme du marqueur** : champ additif `parity_class` sur chaque entrée `equipment` de l'export (`schema_version` reste 1, comme `homekit_exposed_effective` en 24.4). Valeurs : `"functional_equivalent"` ou `null`. Calcul (fonction pure, testée) : `homekit_exposed_effective is True` ET l'équipement a au moins une entité publiée de `ha_type` `switch` portée par une commande `FAN_STATE`, `FAN_ON` ou `FAN_OFF` ET aucune commande `FAN_SPEED`, `FAN_SPEED_STATE`, `ROTATION`, `ROTATION_STATE`. Sinon `null`. Pas de champ sur les scénarios.
- **D2. Ventilateur à vitesse** : si un équipement exposé porte un type de vitesse, `parity_class` vaut `null` et l'export porte en plus `parity_alert: "fan_speed_present"` sur cet équipement (champ additif, absent sinon) : c'est le déclencheur de l'AC4, visible sans lire le code.
- **D3. Le « référentiel »** (outil de parité de ClaudeBox, hors dépôt) lit `parity_class` ; la story n'y touche pas : AC1 s'arrête à l'export et à sa documentation.

## Critères d'acceptation

- **AC1.** L'export porte `parity_class` (D1) sur toutes les entrées `equipment` ; il vaut `"functional_equivalent"` pour un équipement exposé (effectif) publié en `switch` par un trio `FAN_*` sans vitesse, `null` sinon (non exposé, exposition non effective comme 165, non publié, ou autre famille). Tests : les cas de D1 et D2 sur fixtures anonymes, dont un aspirateur avec `BATTERY`, un équipement désactivé exposé, un équipement avec `FAN_SPEED`.
- **AC2.** `docs/dev-decision-export.md` documente `parity_class` et `parity_alert` (table des champs) et la règle : un `FAN_*` sans ordre de vitesse reste `switch` ; la présence de `FAN_SPEED` ou `ROTATION` sur un équipement exposé est le seul déclencheur d'une nouvelle story (ouverture gouvernée de `fan`, 18-1).
- **AC3.** Aucun changement de ce qui est publié : inventaire MQTT et registres de HA identiques avant/après, aucun `entity_id` ni `unique_id` ne change ; `PRODUCT_SCOPE` inchangé.
- **AC4.** Un équipement exposé avec un type de vitesse porte `parity_alert: "fan_speed_present"` (D2) ; son ouverture en `fan` relève d'une story à part (reprise de 18-1, Q10). Sur la box au 01/11 : aucun.
- **AC6.** Preuve terrain (ClaudeBox, clawcode) : après déploiement, l'export de production porte `functional_equivalent` sur exactement 67, 506, 516, 519, 520, 521, 522, 523, `null` sur 165 ; 0 changement de décision ; inventaire MQTT inchangé.
- **AC5.** Les aspirateurs restent des `switch` ; `vacuum` hors périmètre.

## Tâches

- [x] **Task 0 — Vérifier sur l'export « avant »** (ClaudeBox, 01/11) : voir ci-dessus.
- [x] **Task 1 — `parity_class` / `parity_alert`** : fonction pure (près de `compute_homekit_exposed_effective` ou dans `export/`), champ additif dans `export/decision_export.py`, tests unitaires (AC1, AC4, AC5).
- [x] **Task 2 — Documentation** `docs/dev-decision-export.md` (AC2).
- [x] **Task 3 — Non-régression** (AC3) : aucun changement de mapping, de publication, de `PRODUCT_SCOPE` ; garde 25.4 si elle s'applique ; `flake8`, suite complète.
- [x] **Task 4 — Preuve terrain** (AC6) : ClaudeBox et clawcode, 2026-11-01 (voir « Preuve terrain »).

## Garde-fous

- Pas d'ouverture de composant dans cette story.
- Pas de changement de domaine d'entités existantes sans la décision de la Q10.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Que la mesure du 12/10 (aucune vitesse) reste vraie sur l'export ; la forme exacte du marqueur de classement.

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q7 A, Q9 A (ajustée R1 : l'epic 18 garde 18-1).
- 2026-11-01 — Task 0 sur l'export de production et décisions D1-D3 (ClaudeBox) ; `ready-for-dev` (go d'Alexandre 21:10 « on attaque la prochaine story »).
- 2026-11-01 — dev-story (session cloud déléguée) : Tasks 1 à 3 livrées, statut `review` ; Task 4 (AC6) à ClaudeBox et clawcode après fusion.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée).

### Implementation Notes

- **Fonction pure** `compute_parity_class(homekit_exposed_effective, commands) -> (parity_class, parity_alert)` dans `resources/daemon/export/decision_export.py`, juste avant `_equipment_row`. Elle lit les lignes `commands[]` déjà construites pour l'équipement (`generic_type`, `decision`, `ha_type`) : aucune décision n'est recalculée, rien d'autre ne l'appelle (test AST).
- **Règle exacte** : exposition effective différente de `True` ⇒ `(null, absent)`. Exposé et au moins une commande `FAN_SPEED`, `FAN_SPEED_STATE`, `ROTATION` ou `ROTATION_STATE` (publiée ou non) ⇒ `(null, "fan_speed_present")`. Exposé, sans vitesse, et au moins une commande `FAN_STATE`/`FAN_ON`/`FAN_OFF` avec `decision: "published"` et `ha_type: "switch"` ⇒ `("functional_equivalent", absent)`. Sinon `(null, absent)`.
- **Points tranchés** :
  1. « Entité publiée » (D1) est lue sur le **verdict** de la commande (`commands[].decision == "published"`), pas sur l'état d'exécution `entities[].discovery_published` : le classement reste stable si le broker est momentanément indisponible et ne demande pas de jointure `entity_unique_id` ↔ `unique_id`. Un équipement désactivé, exclu ou refusé par le périmètre a ses commandes en `not_published` : `null`.
  2. Le type de vitesse déclenche l'alerte **qu'il soit publié ou non** (le `FAN_SPEED_STATE` est aujourd'hui un `sensor`, F2), et même sans trio `FAN_*` sur l'équipement (D2 : « porte un type de vitesse »).
  3. Un trio `FAN_*` dont un override de type sort de `switch` n'est pas classé (`null`).
  4. `parity_alert` est **absent** hors alerte (D2) ; c'est la seule exception documentée à « clés toujours présentes ».
- **Garde 25.4 (AC31)** : elle refuse toute ligne existante retirée dans `resources/daemon/`. Le `return {` de `_equipment_row` est donc conservé ; `parity_alert` est ajouté par décompactage conditionnel en fin de dictionnaire (diff 100 % ajout).
- Aucun changement de mapping, de publication, de `PRODUCT_SCOPE` ni du payload MQTT ; `schema_version` reste 1.

### Tests

- `resources/daemon/tests/unit/test_story_24_6_parity_class_fan.py` (29 cas) : fonction pure (non exposé / inconnu, trio publié en `switch`, aspirateur avec `BATTERY`, une seule commande `FAN_*` suffit, chaque type de vitesse publié ou non, vitesse sans trio, trio non publié, trio sorti de `switch`, autres familles `SWITCH_*`, `LIGHT_*`, `DOCK_*`, aucune commande) ; export de bout en bout par `/action/sync` sur 10 équipements anonymes (601-610 : ventilateur, aspirateur, désactivé exposé en pièce exclue façon 165, `FAN_SPEED`, non exposé, inconnu, exclu, `SWITCH_*`, vitesse non exposée, vitesse désactivée) ; `parity_alert` seulement sur 604 ; pas de champ sur les scénarios ; `schema_version == 1` ; AC5 (restent `switch`, aucun `fan` ni `vacuum`) ; AC3 (publications MQTT identiques avec le classement neutralisé ; aucun module hors export n'appelle le classement).
- `python -m pytest` : 2 566 passés, 9 désélectionnés (marqueur `load`). `flake8 resources/daemon tests` : 0. `node --test tests/unit/*.node.test.js` : tout vert.

### File List

- `resources/daemon/export/decision_export.py` (modifié, ajouts seuls)
- `resources/daemon/tests/unit/test_story_24_6_parity_class_fan.py` (nouveau)
- `docs/dev-decision-export.md` (modifié)
- `_bmad-output/implementation-artifacts/24-6-ventilateurs-et-aspirateurs-fan.md` (modifié)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié)

## Preuve terrain (2026-11-01, clawcode, relue par ClaudeBox)

Run `24-6-prod-20261101` (VM openclaw, hors dépôt) : déploiement de `57f961b` (#366) depuis `689c5fe`, retour arrière prêt, non déclenché.
- Export de décision avant/après : **0 changement de décision** (AC3).
- Inventaire MQTT : sujets `homeassistant/` delta **0** (AC3).
- `parity_class == "functional_equivalent"` sur exactement **67, 506, 516, 519, 520, 521, 522, 523** ; `null` sur 165 et sur tous les autres équipements ; **aucune** entrée `parity_alert` (AC1, AC4, AC6).
- `getEquipmentStates` : 1 377 812 octets (inchangé) ; 0 ERROR du démon depuis le redémarrage.
- Relecture de la PR : ClaudeBox seul (Codex sans quota ce soir-là).
