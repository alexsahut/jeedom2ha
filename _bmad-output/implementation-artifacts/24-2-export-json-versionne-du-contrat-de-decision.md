# Story 24.2 : Export JSON versionné du contrat de décision

Status: ready-for-dev

> **Statut : `ready-for-dev` (2026-10-12), accordé par ClaudeBox au nom des décisions d'Alexandre du 12/10 à 13:22** (Q5 A et Q6 A tranchées). Brouillon de cadrage initial rédigé par une session cloud déléguée, documentaire ; décisions : `sprint-change-proposal-2026-10-12-parite-homekit.md`. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48) : identifiants seulement.
>
> **R1 (ClaudeBox, 12/10) intégrée** : les scénarios portent `homekit_exposed` (règle de Homebridge établie, voir 24-1) ; l'outil de parité de ClaudeBox ne lit pas les boutons de scénario, l'export les rend donc visibles ; `logicalId` est vide pour 65 accessoires sur 123 (*établi par ClaudeBox le 12/10*) : il ne sert jamais de clé unique.

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q5 A** : identifiants seulement (aucun nom), tous les équipements et tous les scénarios.
- **Q6 A** : action AJAX d'administrateur `getDecisionExport` + bouton de téléchargement ; la route du démon reste interne.
- **Q1** : « exclu par plugin » conservé, **pas de raison `voie_native`** : l'export porte `reason: excluded_plugin`, `exclusion_source: plugin` et les `logicalId`, ce qui suffit à l'alignement hors plugin.
- **Q11** : les 5 boutons de scénario sont exposés à Assist (ClaudeBox, 13:30) ; ils sont dans l'export.
- `ready-for-dev` accordé par ClaudeBox au nom de ces décisions.

## Story

En tant que mainteneur de la parité,
je veux un export JSON versionné de ce que le plugin a décidé pour chaque équipement, chaque commande et chaque scénario,
afin que ClaudeBox mesure la parité avec Apple Maison et Assist sans SSH, avant et après chaque changement de comportement.

**Parcours : démon + PHP (relais d'administrateur) + un bouton de téléchargement dans la page du plugin.** Gate 20-0 et `ready-for-UX-validation` pour le bouton. Preuve terrain par ClaudeBox.

## Dépendances et décisions

- Dépend de **24.1** (`homekit_exposed`, `logicalId`).
- Démarre après **22.2 `done`** (mêmes fichiers `http_server.py` et `desktop/`).
- **Q5 A** et **Q6 A** (tranchées, voir plus haut).
- Son déploiement suivi d'une **capture « avant » (baseline)** par ClaudeBox, conservée hors du dépôt, conditionne 24.4 (et 24.3 si elle est maintenue) et 24.5.

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Le cache disque est indexé par `eq_id`, ne contient que les équipements présents dans `publications` (pas d'inéligibles, de commandes ni de scénarios) et s'écrit sans écriture atomique. L'export va donc dans un **second fichier**. | `cache/disk_cache.py:29,107-152` |
| F2 | Un motif d'écriture atomique existe (fichier temporaire, `fsync`, `os.replace`). | `mapping/overrides.py:64-85` |
| F3 | Les décisions par commande (`CommandDecision`) sont produites par `evaluate_equipment()` ; le sync ne les conserve pas, les arbres et l'aperçu les recalculent. | `models/evaluate_equipment.py:113,309` ; sync `transport/http_server.py:1929` |
| F4 | `select_covering_decision` est le résolveur unique d'une commande portée par plusieurs entités (CC-47). | `evaluate_equipment.py:295` |
| F5 | Les scénarios sont publiés par une boucle propre, sans décision, sans périmètre ni override, et n'apparaissent dans aucun diagnostic. Leurs identifiants recoupent ceux d'équipements (15 cas, preuve 21-1). | `http_server.py:2129-2190`, `:4716` |
| F6 | L'`entity_id` attendu d'une entité nouvelle ou recréée vaut `<domaine>.<object_id>` (`default_entity_id`, 22-1). Les entités existantes gardent leur `entity_id` : la jointure avec le registre de HA se fait sur `unique_id`. | `discovery/publisher.py:405-412` |
| F7 | `published_in_ha` signifie « publié par le plugin et non en attente de dépublication », pas « présent dans le registre de HA ». | `http_server.py:470-482` |
| F8 | Le streaming effectif est lisible par `StateSynchronizer.list_state_targets()`, déjà utilisé par le diagnostic. | `http_server.py:3563-3571`, `sync/state.py` |
| F9 | Les routes du démon sont protégées par secret et limitées à `127.0.0.1` ; les relais PHP suivent un budget fixe (A1). | `http_server.py:4735-4753` ; `core/ajax/jeedom2ha.ajax.php:27`, `:744-760` (`exportDiagnostic`) |
| F10 | Les points d'écriture du cache après décision : sync complet et « Publier ». L'export s'écrit aux mêmes endroits. | `http_server.py:2202`, `:4293`, `:4598` |

## Forme proposée du document (`schema_version: 1`)

Le schéma exact est figé au `create-story` avec ClaudeBox ; la forme ci-dessous fixe l'intention. Tous les tableaux sont triés (`eq_id`, `cmd_id`, `scenario_id`) pour que deux exports se comparent par `diff`.

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-12T10:00:00Z",
  "sync_at": "2026-10-12T09:58:11Z",
  "producer": { "plugin_version": "x.y.z", "confidence_policy": "sure_probable" },
  "config": { "excluded_plugins": ["<plugin>"], "excluded_piece_ids": [12] },
  "totals": { "equipments": 0, "commands": 0, "scenarios": 0 },
  "equipments": [{
    "kind": "equipment", "key": "eq:67", "eq_id": 67, "logical_id": "<id|null>",
    "plugin": "<eq_type>", "piece_id": 12, "enabled": true, "generic_type": null,
    "homekit_exposed": true, "homekit_exposed_source": "<provenance|null>",
    "decision": "published", "reason": "<code canonique>", "step": "4",
    "exclusion_source": null,
    "overrides": { "publication": null, "types": {} },
    "pending_changes": false,
    "entities": [{ "unique_id": "<…>", "ha_type": "switch", "role": "primary",
                   "entity_id_expected": "switch.jeedom2ha_67",
                   "discovery_published": true, "state_source": "streamed" }],
    "commands": [{ "cmd_id": 1, "logical_id": "<id|null>", "generic_type": "<…|null>",
                   "type": "action", "sub_type": "other", "covered": true,
                   "decision": "published", "reason": "<code canonique>", "step": "4",
                   "entity_unique_id": "<…|null>", "ha_type": "switch", "override": null }]
  }],
  "scenarios": [{ "kind": "scenario", "key": "scenario:20", "scenario_id": 20, "active": true,
                  "homekit_exposed": true, "homekit_exposed_source": "scenario_configuration",
                  "decision": "published", "reason": "scenario_button",
                  "entity": { "unique_id": "jeedom2ha_scenario_20", "ha_type": "button",
                              "entity_id_expected": "button.jeedom2ha_scenario_20",
                              "discovery_published": true, "state_source": "none" } }]
}
```

Choix de conception à confirmer :
- `decision` / `reason` / `step` sont ceux **du dernier sync** (ce que le plugin a appliqué), avec `pending_changes` quand un override posé depuis n'a pas été appliqué (deux temporalités de 19-3). Les décisions par commande sont donc **mémorisées au sync** (et au « Publier »), non recalculées à chaque export.
- `entity_id_expected` = valeur attendue **à la création** (22-1) ; ce n'est pas l'`entity_id` du registre.
- `state_source` ∈ `streamed` / `optimistic` / `none`, lu sur le streaming effectif : la couverture de 23.3 devient mesurable sans code de plus.
- Horodatage : `generated_at` et `sync_at` en tête, pas par ligne (redondant). Si ClaudeBox le veut par ligne, c'est un champ additif (pas de changement de version).
- `reason` est le code canonique tel que produit (`excluded_plugin`, `excluded_eqlogic`, `command_not_covered`…), sans traduction. Un champ `native_test_mode` serait un champ additif si le mode « plugins en test » de 24.3 est maintenu : pas de changement de version.
- Politique de version : un champ ajouté ne change pas `schema_version` ; un champ renommé, retiré ou de sens changé le porte à 2.

## Critères d'acceptation proposés

- **AC1.** Le démon écrit `data/jeedom2ha_decision_export.json` après chaque sync complet et chaque « Publier » (mêmes points que le cache), **atomiquement** (fichier temporaire + `os.replace`), mode 600 ; `jeedom2ha_cache.json` est inchangé (format et écriture).
- **AC2.** `GET /system/decision_export` (secret requis, comme les autres routes) renvoie le même document, construit depuis la mémoire ; sans sync préalable, il répond une erreur explicite (même motif que `/system/diagnostics`).
- **AC3.** Une action AJAX d'administrateur (`getDecisionExport`) relaie la route avec un budget fixe (motif A1) et renvoie le JSON ; un bouton « Télécharger l'export de décision » est ajouté à la page du plugin (Q6 A). Aucun libellé ne parle de « présent dans HA ».
- **AC4.** Le document couvre **tous** les équipements du snapshot (éligibles ou non), **chaque commande** de chacun (y compris les non couvertes : `reason` non vide) et **tous les scénarios** (actifs et inactifs, avec `homekit_exposed` issu de 24.1), avec `kind` et `key` uniques (aucune collision entre équipement et scénario de même numéro). Un `logical_id` vide est écrit `null` ; la jointure du référentiel se fait sur `eq_id`/`cmd_id`/`scenario_id` et `unique_id`, jamais sur `logical_id` seul.
- **AC5.** Confidentialité (Q5 A) : **aucun nom** d'équipement, de pièce, de commande ni de scénario ; **aucun secret** (clé API, secret local, identifiants MQTT, jeton) ; test sur des fixtures dont les noms sont des sentinelles reconnaissables, absentes du document.
- **AC6.** `entities[].unique_id` est exactement celui du payload de découverte ; `entity_id_expected` est exactement `<domaine>.<object_id>` du même payload (`default_entity_id`).
- **AC7.** Les décisions de l'export égalent celles du diagnostic et de l'aperçu pour les mêmes entrées (un seul résolveur : `evaluate_equipment()` et `select_covering_decision`), prouvé par un test de parité sur le corpus golden existant.
- **AC8.** Le document est déterministe : deux exports du même état sont identiques à `generated_at` près.
- **AC9.** Le fichier d'export est absent du paquet Market (test de composition du paquet complété) et du dépôt ; `PRODUCT_SCOPE`, contrat 4D, golden et comportement de publication **inchangés**.
- **AC10.** Le schéma est documenté (`docs/`, développeur) avec sa politique de version.
- **AC11.** Gate 20-0 vert (bouton) ; preuve terrain par ClaudeBox : baseline « avant » capturée sans SSH, comptes cohérents avec le sync (`total_eq`, éligibles, publiés), 0 erreur, inventaire MQTT et registres de HA inchangés.
- **AC12.** Aucun nom réel dans le code de test, les fixtures, la story, la PR (CC-48).

## Tâches proposées

- [ ] **Task 0 — Figer le schéma** avec ClaudeBox (champs, noms, tri) avant tout code ; confirmer Q5 et Q6.
- [ ] **Task 1 — Mémoriser** les décisions par commande au sync et au « Publier » (RAM), sans changer ce qui est publié.
- [ ] **Task 2 — Module d'export** (nouveau, propre, motif atomique repris sans modifier `overrides.py` ni `disk_cache.py`) et appels aux points d'écriture.
- [ ] **Task 3 — Route du démon** et relais PHP ; bouton de téléchargement.
- [ ] **Task 4 — Tests** : schéma, parité avec le diagnostic, confidentialité, déterminisme, collision équipement/scénario, paquet Market.
- [ ] **Task 5 — Gate 20-0 + déploiement standard (humain) + baseline « avant »** ; mesure des écarts de la section 3 de la proposition.
- [ ] **Task 6 — Documentation** du schéma.

## Garde-fous

- Aucune écriture dans `jeedom2ha_cache.json` ni dans `ha_overrides.json` par cette story.
- Aucun champ « Assist » ni « présent dans HA » : le démon n'a pas de client HA.
- Les `logicalId` sont bruts (nécessaires à l'alignement) : fichier réservé à l'administrateur, jamais versé au dépôt ni écrit au journal.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Taille réelle du document sur 292 équipements ; coût de mémorisation des décisions par commande ; contenu exact de la baseline (nombre d'équipements exposés écartés par la pièce, par plugin, par absence de type).

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, midi — R1 (ClaudeBox) : règle d'exposition de Homebridge, scénarios dans l'export, `logicalId` vide pour 65 accessoires sur 123.
- 2026-10-12, 13:22 — Décisions d'Alexandre (relayées par ClaudeBox) : Q5 A, Q6 A, Q1 « exclu par plugin » conservé (pas de `voie_native`), Q11 oui. `ready-for-dev` accordé par ClaudeBox ; démarrage après 22.2 `done` conservé, ClaudeBox peut le lever.
