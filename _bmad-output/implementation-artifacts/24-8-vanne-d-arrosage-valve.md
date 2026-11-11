# Story 24.8 : Vanne d'arrosage : `valve`

Status: ready-for-dev

> **Brouillon de cadrage (2026-10-12), `draft` jusqu'à son `create-story`, après la baseline.** Rédigé par une session cloud déléguée, documentaire. **Change la production et ouvre un composant** (`valve`, FR40/NFR10). Décisions attendues d'Alexandre : **Q9** (relation avec l'epic 18) et **Q10** (remplacement d'entités existantes) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
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
- **Q9 A** et **Q10 A** (tranchées).

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q9 A** (version ajustée R1) : l'epic 24 absorbe 18-4 (`valve`).
- **Q10 A** : remplacement, une seule voie par équipement ; inventaire des références avant/après.
- **Q1** : « exclu par plugin » conservé (pas de `voie_native`).

## Établi par ClaudeBox le 12/10 (mesure du 10/10)

- **Deux vannes** portent `IRRIG_ON`, `IRRIG_OFF`, `IRRIG_STATE` (trio complet : ordres + état), dont **une appartient à un plugin Z-Wave**.
- **Point à trancher avant le `create-story`** : si ce plugin Z-Wave figure dans la liste `excludedPlugins` (plugins natifs : « exclu par plugin », décision Q1), cette vanne **n'est pas publiée par jeedom2ha** et sort de cette story (sa voie est l'intégration native de HA) ; seule l'autre vanne la concerne. À confirmer par ClaudeBox à partir de l'export (champ `plugin` et `reason: excluded_plugin`).
- `IRRIG_*` n'est pas un type du core (famille Homebridge) : le gel du référentiel (Task 0) reste nécessaire.

## Task 0 faite par ClaudeBox le 2026-11-11 (export de production, lecture seule)

Source : `/system/decision_export` et `/system/state_listeners` du démon de production, relevés par la sonde CC-48 v2 (11/11, 19:44). Catalogue des types gelé par clawcode à partir des sources du plugin Homebridge installé ; aucune occurrence côté core.

**Types génériques de vanne (Homebridge, gelés)** : `IRRIG_STATE/ON/OFF`, `FAUCET_STATE/ON/OFF`, `VALVE_STATE/ON/OFF` (+ `VALVE_SET_DURATION`, `VALVE_REMAINING_DURATION`, hors périmètre par AC7). Aucun type de position : `reports_position: false`.

**Équipements concernés (3, tous `published`, `homekit_exposed_effective: true`, pièce 11)** :

| eq | plugin | Trios de vanne (STATE / ON / OFF) | Publication actuelle |
|---|---|---|---|
| 461 | zwavejs | 4144 / 4145 / 4146 | `sensor` sur 4147 (sans type générique) ; commandes IRRIG en `command_not_covered` |
| 462 | zwavejs | zone 1 : 4156 / 4157 / 4158 ; zone 2 : 4159 / 4160 / 4161 | publié, commandes IRRIG en `command_not_covered` |
| 527 | virtual | 4849 / 4845 / 4848 | publié, commandes IRRIG en `command_not_covered` |

- `zwavejs` **n'est pas** dans `excludedPlugins` : les deux vannes Z-Wave sont dans le périmètre (le point « voie native » de R1 est levé). Côté HA, les entités Z-Wave natives sont toutes `unavailable` le 11/11.
- Aucune commande de vanne n'a d'entité HA aujourd'hui : la story est **additive** pour ces commandes (pas de remplacement d'entité vanne existante) ; Q10 A s'applique aux autres entités des mêmes équipements seulement si le mapping les modifie (inventaire avant/après exigé, AC5).

## Décisions d'Alexandre (2026-11-11, ~20:00)

- **D1 — Vannes Z-Wave portées par jeedom2ha** : 461, 462 et 527 sont projetées en `valve` par le plugin.
- **D2 — Une vanne par zone** : un équipement qui porte plusieurs trios `*_STATE/ON/OFF` produit une entité `valve` par trio (agrégation multi-entité structurelle, comme le multi-switch de 11.3) ; appariement des trios par l'info liée des actions (`value` de l'action = id de la commande STATE), à défaut par ordre d'id ; un trio incomplet n'est pas publié en `valve` (pas d'ordre deviné).
- **D3 — Preuve terrain sur le virtuel 527 seulement** : ouverture/fermeture réelles uniquement sur 527 ; pour 461 et 462, vérification en lecture seule (entités, topics, `optimistic: false`, état retenu = état Jeedom), **aucun ordre envoyé**.

## Décisions techniques ClaudeBox (2026-11-11)

- **D4** — `valve` sans position : `payload_open`/`payload_close` traduits par `sync/command.py` vers les actions ON/OFF ; `state_topic` + `state_open: open` / `state_closed: closed` ; état binaire 0/1 traduit avec `invertBinary` comme pour `switch` ; `optimistic: false` quand STATE existe, sinon le trio est incomplet (D2) et rien n'est publié en `valve`.
- **D5** — `device_class: water` pour `IRRIG_*` et `FAUCET_*`, aucune `device_class` pour `VALVE_*`.
- **D6** — Ordre des mappers : la vanne est reconnue avant `switch` et le repli, sans changer la projection des équipements qui n'ont aucun type de vanne (golden inchangés).

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

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q9 A (absorbe 18-4), Q10 A ; Q1 « exclu par plugin » conservé.
- 2026-11-11 — Task 0 (ClaudeBox, export de production) ; décisions D1-D3 d'Alexandre, D4-D6 ClaudeBox ; `ready-for-dev` accordé par ClaudeBox.
