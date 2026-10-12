# Story 24.6 : Ventilateurs (et aspirateurs) : `fan`

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **Change la production et ouvre un composant** (`fan`, FR40/NFR10). Décisions attendues d'Alexandre : **Q7** (changer de domaine ?), **Q9** (relation avec l'epic 18), **Q10** (remplacement d'entités existantes) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).

## Story

En tant qu'utilisateur dont des ventilateurs et des aspirateurs sont exposés à HomeKit,
je veux les retrouver dans Home Assistant avec le type qui porte leurs fonctions (marche/arrêt et, quand elle existe, la vitesse),
afin de les piloter par Assist comme je le fais dans Apple Maison.

**Parcours : démon (mapper, publication, commande, état).** Recoupe la story 18.1 du backlog (Q9 A : absorbée par celle-ci).

## Dépendances et décisions

- Dépend de **24.4** (le signal HomeKit décide de ce qui est projeté). Une seule story de type en cours à la fois (mêmes fichiers).
- **23.3** : ne modifie pas les lignes `light`/`cover` du streaming ; ajoute une entrée `fan` seulement après la fusion de 23.3 (sinon `fan` optimiste, documenté ; règle `optimistic: false` seulement avec un état réel).
- **Q7** : A recommandée (`fan` seulement quand un ordre de vitesse existe ; marche/arrêt seul reste `switch`) ; B (tout `FAN_*` en `fan`, comportement prévu par 18.1) ; C (ne rien changer).
- **Q9** : A recommandée (absorption de 18.1). **Q10** : A recommandée (remplacement, inventaire des références).

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | `FAN_STATE/ON/OFF` est groupé comme un trio de `switch` depuis 14-1 ; la pompe correspondante est publiée en `switch` avec son état. | `mapping/switch.py:62-64,321` ; `mapping/binary_sensor.py:21-26` |
| F2 | `FAN_SPEED_STATE` est aujourd'hui un `sensor` (tr/min) ; un `fan` qui porterait la vitesse doit éviter ce doublon. | `mapping/sensor.py:51` |
| F3 | `fan.mqtt` est documenté dans le référentiel (champs obligatoires : topic de commande, `platform`, disponibilité) ; `fan` n'est ni dans `HA_COMPONENT_REGISTRY` ni dans `PRODUCT_SCOPE`. | `ha-projection-reference.md` (composants) ; `validation/ha_component_registry.py:26-70` |
| F4 | Types génériques de vitesse du core : `FAN_SPEED` (action, slider), `FAN_SPEED_STATE`, `ROTATION`, `ROTATION_STATE`. | `ha-projection-reference.md:598-601` |
| F5 | La famille « Robot » (`DOCK_STATE`, `DOCK`) n'est mappée par aucun mapper ; les aspirateurs ne sont donc distinguables des ventilateurs que par leurs types génériques réels (D6). | `ha-projection-reference.md:551-556` ; `mapping/binary_sensor.py:45` |
| F6 | Un override de type entre familles de commandes incompatibles est refusé par une vérification dédiée (16.7) : elle devra connaître `fan`. | `validation/ha_component_registry.py` (`_cross_family_action_mismatch`) |
| F7 | Le streaming ne couvre que `sensor`, `binary_sensor`, `switch`. | `sync/state.py:33-36,44-48` |

## Critères d'acceptation proposés (à figer selon Q7, Q9, Q10)

- **AC1.** Ouverture gouvernée de `fan` dans le même incrément : entrée `HA_COMPONENT_REGISTRY` avec champs requis et capacités ; un cas nominal et un cas d'échec de `validate_projection()` ; `PRODUCT_SCOPE` mis à jour ; contrat 4D non régressé ; `SWITCH_*`/`ENERGY_*` non régressés.
- **AC2.** Q7 A : un équipement `FAN_*` **avec** ordre de vitesse est projeté en `fan` (marche/arrêt, pourcentage) ; un `FAN_*` marche/arrêt seul reste `switch` (aucun `entity_id` ne change pour lui). Le `sensor` de vitesse n'est plus publié en doublon pour un `fan` qui la porte.
- **AC3.** Le payload porte `default_entity_id = fan.<object_id>` (règle de 22-1) ; `unique_id` et `object_id` suivent les conventions existantes.
- **AC4.** Les commandes HA → Jeedom sont traduites par `sync/command.py` (marche, arrêt, vitesse) avec le même motif de confirmation que les autres domaines ; aucun ordre n'est envoyé sans commande Jeedom correspondante.
- **AC5.** État : `optimistic: false` seulement si un état réel est remonté (après 23.3) ; sinon `fan` optimiste, documenté dans « Limites » (une puce propre).
- **AC6.** Cycle de vie (Q10 A) : le passage `switch` → `fan` dépublie l'ancienne entité et publie la nouvelle (chemin de requalification de la story 5.2) ; l'inventaire avant/après liste les équipements concernés (identifiants), les `entity_id` anciens et nouveaux, et ClaudeBox relève les références (automatisations, scripts, cartes).
- **AC7.** Un override de type pe-epic-16 peut rediriger un `fan` vers `switch` et inversement ; la vérification de compatibilité des familles de commandes connaît `fan`.
- **AC8.** Aspirateurs : si leurs types génériques sont `FAN_*`, ils suivent la règle de Q7 ; sinon ils sont signalés hors périmètre dans la story (pas de `vacuum` ici).
- **AC9.** Gate : golden et contrat 4D verts ; aucun nom réel dans le dépôt (CC-48) ; preuve terrain par ClaudeBox (export avant/après, registres de HA, un essai de marche/arrêt/vitesse sur un équipement de test).

## Tâches proposées

- [ ] **Task 0 — Gel du référentiel pour `fan`** (mini-18.0) : matrice types génériques (core ∪ Homebridge) → champs de `fan.mqtt`, lue dans la documentation officielle de HA 2026.9.4 (D4) ; liste, par ClaudeBox, des équipements concernés et de leurs types réels (vitesse, aspirateurs).
- [ ] **Task 1 — Registre et validation**, **Task 2 — mapper**, **Task 3 — publication**, **Task 4 — commande**, **Task 5 — état (après 23.3)**, **Task 6 — override**, **Task 7 — tests**, **Task 8 — gate 20-0 si l'écran change, déploiement, preuve terrain (humain)**, **Task 9 — documentation (« Limites »)**.

## Garde-fous

- Pas de `vacuum`, pas de `media_player` ici.
- Pas de remplacement sans l'inventaire de la Q10.
- Ne pas toucher aux lignes `light`/`cover` du streaming (23.3).
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Le nombre de ventilateurs avec vitesse parmi les cas mesurés ; les types génériques réels des aspirateurs ; les champs exacts de découverte de `fan` dans HA 2026.9.4.
