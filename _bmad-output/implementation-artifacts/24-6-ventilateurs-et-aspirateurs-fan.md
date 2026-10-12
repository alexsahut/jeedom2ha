# Story 24.6 : Ventilateurs (et aspirateurs) : équivalents fonctionnels

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **R1 (ClaudeBox, 12/10) intégrée : story réduite.** *Établi par ClaudeBox le 12/10* : 8 équipements exposés à HomeKit portent `FAN_*` (marche, arrêt, état ; 5 aspirateurs compris), **aucun n'a de commande de vitesse**. Avec **Q7 A**, aucun ne change de type : la story devient un classement « équivalents fonctionnels » dans l'export. **`fan` n'est plus ouvert ici**, sauf apparition d'un ventilateur à vitesse. Décisions : **Q7** et **Q9** de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire avant `ready-for-dev`. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).

## Story

En tant que mainteneur de la parité,
je veux que les ventilateurs et aspirateurs exposés à HomeKit et publiés en `switch` soient reconnus comme fonctionnellement équivalents (marche, arrêt, état), et qu'un ventilateur à vitesse soit repéré s'il apparaît,
afin de ne pas changer le domaine d'entités qui fonctionnent par la voix, et d'ouvrir `fan` seulement quand il apporte une fonction.

**Parcours : export + documentation. Pas de code de production tant qu'aucun ventilateur à vitesse n'existe.**

## Dépendances et décisions

- Dépend de **24.2** (export) et **24.4**.
- **Q7 A** (recommandée) : `fan` seulement quand un ordre de vitesse existe. **Q9** : l'epic 18 garde 18-1 (`fan`) ; cette story ne l'absorbe plus.

## Établi par ClaudeBox le 12/10

8 équipements exposés portent des types `FAN_*` (marche, arrêt, état), dont 5 aspirateurs ; aucun n'a de commande de vitesse (`FAN_SPEED`, `ROTATION`). La famille « Robot » (`DOCK_STATE`, `DOCK`) n'est pas en cause.

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | `FAN_STATE/ON/OFF` est groupé comme un trio de `switch` depuis 14-1, publié avec son état. | `mapping/switch.py:62-64,321` ; `mapping/binary_sensor.py:21-26` |
| F2 | `FAN_SPEED_STATE` est aujourd'hui un `sensor` (tr/min) ; un futur `fan` qui porterait la vitesse devrait éviter ce doublon. | `mapping/sensor.py:51` |
| F3 | `fan.mqtt` est documenté ; `fan` n'est ni dans `HA_COMPONENT_REGISTRY` ni dans `PRODUCT_SCOPE`. | `ha-projection-reference.md` ; `validation/ha_component_registry.py:26-70` |
| F4 | Types de vitesse du core : `FAN_SPEED`, `FAN_SPEED_STATE`, `ROTATION`, `ROTATION_STATE`. | `ha-projection-reference.md:598-601` |

## Critères d'acceptation proposés

- **AC1.** L'export (24.2) porte, pour chacun des 8 équipements `FAN_*` exposés, `ha_type: switch`, sa décision, son `state_source` et un marqueur de classement (forme à fixer avec ClaudeBox, par exemple `parity_class: functional_equivalent`) ; aucun n'est compté « écart de type » par le référentiel.
- **AC2.** La documentation de développement énonce la règle : un `FAN_*` sans ordre de vitesse reste `switch` ; la présence de `FAN_SPEED` ou `ROTATION` sur un équipement exposé est le seul déclencheur d'une nouvelle story (ouverture gouvernée de `fan`, 18-1).
- **AC3.** Aucun changement de ce qui est publié : inventaire MQTT et registres de HA identiques avant/après, aucun `entity_id` ni `unique_id` ne change ; `PRODUCT_SCOPE` inchangé.
- **AC4.** Si un ventilateur à vitesse apparaît dans l'export (contre la mesure du 12/10), la story s'arrête : une story d'ouverture de `fan` (reprise de 18-1, Q10 pour le remplacement des entités) est rédigée à part.
- **AC5.** Les aspirateurs restent des `switch` ; `vacuum` hors périmètre.

## Tâches proposées

- [ ] **Task 0 — Vérifier sur l'export « avant »** (ClaudeBox) : les 8 équipements, leurs types génériques, l'absence de vitesse.
- [ ] **Task 1 — Marqueur de classement** dans l'export (avec 24.2) et documentation (AC2).

## Garde-fous

- Pas d'ouverture de composant dans cette story.
- Pas de changement de domaine d'entités existantes sans la décision de la Q10.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Que la mesure du 12/10 (aucune vitesse) reste vraie sur l'export ; la forme exacte du marqueur de classement.
