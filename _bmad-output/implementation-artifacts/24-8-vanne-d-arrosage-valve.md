# Story 24.8 : Vanne d'arrosage : `valve`

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **Change la production et ouvre un composant** (`valve`, FR40/NFR10). Décisions attendues d'Alexandre : **Q9** (relation avec l'epic 18) et **Q10** (remplacement d'entités existantes) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
>
> **R1 (ClaudeBox, 12/10) intégrée** : deux vannes concernées, types génériques établis ; **l'une relève d'un plugin Z-Wave** : voir ci-dessous.

## Story

En tant qu'utilisateur dont une vanne d'arrosage est exposée à HomeKit,
je veux la retrouver dans Home Assistant comme une vanne (ouvrir, fermer, état),
afin de la piloter par Assist.

**Parcours : démon.** Recoupe la story 18.4 du backlog (Q9 A : absorbée par celle-ci).

## Dépendances et décisions

- Dépend de **24.4**. Une seule story de type en cours à la fois.
- **23.3** : même règle que 24.6 (une entrée de streaming après sa fusion, sinon optimiste documenté).
- **Q9** : A recommandée. **Q10** : A recommandée.

## Établi par ClaudeBox le 12/10 (mesure du 10/10)

- **Deux vannes** portent `IRRIG_ON`, `IRRIG_OFF`, `IRRIG_STATE` (trio complet : ordres + état), dont **une appartient à un plugin Z-Wave**.
- **Point à trancher avant le `create-story`** : si ce plugin Z-Wave figure dans la liste des plugins natifs (24.3, `voie_native`), cette vanne **n'est pas publiée par jeedom2ha** et sort de cette story (sa voie est l'intégration native de HA) ; seule l'autre vanne la concerne. À confirmer par ClaudeBox à partir de l'export (champ `plugin` et `reason`).
- `IRRIG_*` n'est pas un type du core (famille Homebridge) : le gel du référentiel (Task 0) reste nécessaire.

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Aucune occurrence de `VALVE_*`, `FAUCET_*` ni `IRRIG_*` dans le code du démon ; ces familles viennent du plugin Homebridge, pas du core. | recherche dans `resources/daemon/` |
| F2 | Le référentiel dual-source (core ∪ Homebridge) devait être gelé par la story 18.0, jamais faite. | `epics-projection-engine.md` (Epic 18) ; `sprint-change-proposal-2026-07-17-couverture-domaines-ha.md` |
| F3 | `valve.mqtt` est documenté dans le référentiel ; `valve` n'est ni dans le registre ni dans `PRODUCT_SCOPE`. | `ha-projection-reference.md:125,345-351` ; `validation/ha_component_registry.py:26-70` |
| F4 | Sans mapper dédié, un équipement à commandes typées inconnues tombe sur les mappers génériques ou le repli (`sensor`/`button` ambigus). | `mapping/registry.py:24-35` ; `mapping/fallback.py` |

## Critères d'acceptation proposés (à figer selon Q9 et Q10)

- **AC1.** Ouverture gouvernée de `valve` dans le même incrément : entrée de registre avec champs requis et capacités ; cas nominal et cas d'échec de `validate_projection()` ; `PRODUCT_SCOPE` mis à jour ; contrat 4D non régressé ; `SWITCH_*`/`ENERGY_*` non régressés.
- **AC2.** Un équipement qui porte les types génériques de vanne gelés en Task 0 est projeté en `valve` (ouvrir, fermer, état) ; position seulement si une commande de position existe.
- **AC3.** **Aucun état menteur** : sans état fiable, la vanne est optimiste et documentée ; avec un état réel, `optimistic: false` (règle de 23.3).
- **AC4.** Payload avec `default_entity_id = valve.<object_id>` (22-1) ; commandes traduites par `sync/command.py` ; aucun ordre sans commande Jeedom correspondante.
- **AC5.** Cycle de vie (Q10 A) : dépublication de l'ancienne entité, publication de la nouvelle, inventaire des identifiants et des références avant/après.
- **AC6.** Override pe-epic-16 compatible (la vérification de familles de commandes connaît `valve`).
- **AC7.** Aucune minuterie, aucun programme d'arrosage, aucun débit : hors périmètre.
- **AC8.** Golden et contrat 4D verts ; aucun nom réel (CC-48) ; preuve terrain par ClaudeBox sur une vanne de test.

## Tâches proposées

- [ ] **Task 0 — Gel du référentiel pour `valve`** (mini-18.0) : types génériques de vanne (core ∪ Homebridge) → champs de `valve.mqtt` (documentation officielle HA 2026.9.4, D4) ; liste, par ClaudeBox, des équipements concernés et de leurs commandes réelles.
- [ ] **Task 1 à 7** : registre, mapper, publication, commande, état (après 23.3), override, tests ; **gate, déploiement, preuve terrain (humain)** ; **documentation**.

## Garde-fous

- Une vanne peut inonder : aucun essai sur une vanne réelle sans l'humain.
- Pas de mapper deviné : si le référentiel de types n'est pas gelé, la story ne démarre pas.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Les types génériques exacts de vanne présents dans l'installation ; les champs de `valve` dans HA 2026.9.4 ; la présence d'un état fiable sur les équipements concernés.
