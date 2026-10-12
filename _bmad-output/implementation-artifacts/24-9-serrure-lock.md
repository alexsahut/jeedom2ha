# Story 24.9 : Serrure : `lock`

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **Change la production, ouvre un composant** (`lock`, FR40/NFR10) et touche à la sécurité. Décisions attendues d'Alexandre : **Q9** et **Q10** de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
>
> **R1 (ClaudeBox, 12/10) intégrée** : types génériques de la serrure établis (section suivante).

## Story

En tant qu'utilisateur dont une serrure est exposée à HomeKit,
je veux la retrouver dans Home Assistant comme une serrure (verrouillée ou non, verrouiller, déverrouiller),
afin de la consulter et, si je l'ai voulu, de la piloter par Assist.

**Parcours : démon.** Recoupe la story 18.2 du backlog (Q9 A : absorbée par celle-ci).

## Dépendances et décisions

- Dépend de **24.4**. Une seule story de type en cours à la fois.
- **23.3** : même règle que 24.6 pour l'état.
- **Q9** : A recommandée. **Q10** : A recommandée.

## Établi par ClaudeBox le 12/10 (mesure du 10/10)

- **Une serrure** porte `LOCK_OPEN`, `LOCK_CLOSE`, `LOCK_STATE` : état + deux ordres, donc l'AC3 est satisfaite sur le cas réel.
- Reste à établir (Task 0) : la polarité de `LOCK_STATE` ; le plugin d'origine (si c'est un plugin natif de la liste de 24.3, l'équipement relève de `voie_native`, pas de cette story).

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | `LOCK_STATE`, `LOCK_OPEN`, `LOCK_CLOSE` sont des types du core ; `LOCK_STATE` est une info binaire. | `ha-projection-reference.md:531,536-537` |
| F2 | Aujourd'hui `LOCK_STATE` donne un `binary_sensor` de classe `lock` (lecture seule) ; `LOCK_*` sert de liste « anti » dans les mappers `switch`, `cover`, `light`. | `mapping/binary_sensor.py:40` ; `mapping/switch.py:52-54` ; `mapping/cover.py:43` ; `mapping/light.py:56` |
| F3 | `lock.mqtt` est documenté ; `lock` n'est ni dans le registre ni dans `PRODUCT_SCOPE`. | `ha-projection-reference.md` (composants) ; `validation/ha_component_registry.py:26-70` |
| F4 | Les commandes `LOCK_OPEN` / `LOCK_CLOSE` seraient aujourd'hui des `button` si rien ne les capte avant. | `mapping/button.py:12-35` |

## Critères d'acceptation proposés (à figer selon Q9 et Q10)

- **AC1.** Ouverture gouvernée de `lock` dans le même incrément : entrée de registre ; cas nominal et cas d'échec de `validate_projection()` ; `PRODUCT_SCOPE` mis à jour ; contrat 4D non régressé ; retrait de `LOCK_*` des listes « anti » seulement pour le nouveau mapper.
- **AC2.** **Polarité vérifiée, jamais supposée.** La correspondance valeur de `LOCK_STATE` ↔ verrouillé / déverrouillé est écrite, testée dans les deux sens, et lue dans la documentation des types Jeedom (Task 0) ; si la polarité n'est pas établie pour un équipement, il n'est **pas** publié en `lock` (raison canonique explicite).
- **AC3.** Une serrure n'est publiée en `lock` que si elle a un état fiable (`LOCK_STATE`) et au moins une commande d'action (`LOCK_OPEN` ou `LOCK_CLOSE`) ; sinon elle garde son comportement actuel (`binary_sensor` en lecture seule).
- **AC4.** Les ordres HA → Jeedom sont traduits par `sync/command.py` ; aucun ordre de déverrouillage n'est envoyé sans commande Jeedom `LOCK_OPEN` correspondante ; aucun état n'est affiché sans retour réel.
- **AC5.** Payload avec `default_entity_id = lock.<object_id>` (22-1) ; `unique_id`/`object_id` selon les conventions.
- **AC6.** Cycle de vie (Q10 A) : le `binary_sensor` `lock` existant est remplacé par le `lock` (dépublication, publication) ; inventaire des identifiants et des références avant/après.
- **AC7.** **Sécurité** : la story ne configure pas l'exposition à Assist (exigence 5) et le dit dans la documentation ; elle documente que commander le déverrouillage par la voix est un choix de l'utilisateur dans HA ; aucune valeur par défaut n'expose le déverrouillage.
- **AC8.** Golden et contrat 4D verts ; aucun nom réel (CC-48) ; preuve terrain par ClaudeBox sur une serrure de test ou, à défaut, en lecture seule de l'état.

## Tâches proposées

- [ ] **Task 0 — Gel du référentiel pour `lock`** : polarité de `LOCK_STATE`, sens de `LOCK_OPEN` / `LOCK_CLOSE`, champs de `lock.mqtt` (documentation officielle HA 2026.9.4, D4) ; liste, par ClaudeBox, des équipements concernés et de leurs commandes réelles.
- [ ] **Task 1 à 7** : registre, mapper, publication, commande, état (après 23.3), override, tests (dont polarité) ; **gate, déploiement, preuve terrain (humain)** ; **documentation**.

## Garde-fous

- Une serrure est un organe de sécurité : aucun essai de déverrouillage sur une vraie porte sans l'humain.
- Pas de déduction de polarité depuis un nom.
- Le plugin ne modifie jamais l'exposition à Assist.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

La polarité réelle de `LOCK_STATE` sur les équipements mesurés ; les champs de `lock` dans HA 2026.9.4 ; la présence de commandes `LOCK_OPEN` / `LOCK_CLOSE` sur les équipements concernés.
