# Story 24.9 : Serrure : `lock`

Status: ready-for-dev

> **Brouillon de cadrage (2026-10-12), `draft` jusqu'à son `create-story`, après la baseline.** Rédigé par une session cloud déléguée, documentaire. **Change la production, ouvre un composant** (`lock`, FR40/NFR10) et touche à la sécurité. Décisions attendues d'Alexandre : **Q9** et **Q10** de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
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
- **Q9 A** et **Q10 A** (tranchées).

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q9 A** (version ajustée R1) : l'epic 24 absorbe 18-2 (`lock`).
- **Q10 A** : remplacement du `binary_sensor` `lock` existant, une seule voie ; inventaire des références avant/après.
- **Q1** : « exclu par plugin » conservé (pas de `voie_native`).

## Établi par ClaudeBox le 12/10 (mesure du 10/10)

- **Une serrure** porte `LOCK_OPEN`, `LOCK_CLOSE`, `LOCK_STATE` : état + deux ordres, donc l'AC3 est satisfaite sur le cas réel.
- Reste à établir (Task 0) : la polarité de `LOCK_STATE` ; le plugin d'origine (si c'est un plugin de la liste `excludedPlugins`, l'équipement est « exclu par plugin » et sort de cette story).

## Task 0 faite par ClaudeBox le 2026-11-12 (export de production + sources Homebridge, lecture seule)

**Équipements portant `LOCK_*`** (export de décision de production, 11/11) :

| eq | plugin | Commandes | Décision actuelle |
|---|---|---|---|
| 508 | virtual | 4626 `LOCK_CLOSE`, 4627 `LOCK_OPEN`, 4628 `LOCK_STATE` | `published` (`sure`), `homekit_exposed_effective: true` |
| 421 | myBMW | 3494 `LOCK_STATE`, 3518 `LOCK_CLOSE`, 3519 `LOCK_OPEN` | `not_published`, `excluded_plugin` (plugin exclu) → **hors story** |

**Polarité de `LOCK_STATE` (source : plugin Homebridge installé, `homebridge-jeedom/index.js`, caractéristique `LockCurrentState`)** :
- cas général : valeur vraie (`1`, `true`, `on`) = **verrouillé** (`SECURED`), valeur fausse = **déverrouillé** (`UNSECURED`) ;
- équipements `nuki` (et `jeelink` relayant un `nuki`) : `0` = verrouillé, `1` = déverrouillé, `2` = bloqué (`JAMMED`), autre = inconnu.
- Aucune déduction depuis un nom (garde-fou) : un équipement dont la polarité ne relève d'aucun de ces deux cas n'est pas publié en `lock`.

## Décisions techniques ClaudeBox (2026-11-12)

- **D1 — Polarité** : celle de Homebridge ci-dessus, pour garder la parité HomeKit ; `nuki` traité à part ; `JAMMED` publié comme état `jammed` ; valeur non reconnue → aucun état publié.
- **D2 — Publication** : `lock` seulement si `LOCK_STATE` + au moins une des deux actions (AC3). `payload_lock`/`payload_unlock` → actions `LOCK_CLOSE`/`LOCK_OPEN` ; `state_locked: LOCKED`, `state_unlocked: UNLOCKED`, `state_jammed: JAMMED` ; `optimistic: false` ; pas de `code`.
- **D3 — Remplacement (Q10 A)** : le `binary_sensor` `lock` et les boutons portant les commandes `LOCK_*` du même équipement sont remplacés explicitement par la `lock` (mécanisme de 24-8 : aucune réutilisation silencieuse d'un `unique_id`).
- **D4 — Sécurité (AC7)** : le plugin ne touche jamais l'exposition à Assist ; la documentation dit que déverrouiller par la voix est un choix de l'utilisateur dans HA.

## Décisions qui restent à Alexandre (avant le déploiement, pas avant le développement)

- **Q-L1** : l'équipement 508 (serrure virtuelle) actionne-t-il une serrure réelle (scénario, autre plugin) ? Le publier en `lock` dans HA : oui / non.
- **Q-L2** : preuve terrain : lecture seule (état, entité) recommandée ; essai réel de verrouillage/déverrouillage seulement en sa présence.

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

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q9 A (absorbe 18-2), Q10 A ; Q1 « exclu par plugin » conservé.
- 2026-11-12 — Task 0 (ClaudeBox : eq 508 seul concerné, 421 exclu par plugin ; polarité Homebridge) ; D1-D4 ClaudeBox ; `ready-for-dev` pour le développement, déploiement soumis à Q-L1/Q-L2.
