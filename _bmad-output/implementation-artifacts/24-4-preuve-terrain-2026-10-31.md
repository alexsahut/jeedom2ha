# Story 24.4 : preuve terrain du 2026-10-31

> Box de production, déploiement autorisé par Alexandre le 31/10 (17:37), exécuté par clawcode et relu par ClaudeBox.
> Identifiants seulement (CC-48). Rapports bruts sur la VM openclaw, hors dépôt :
> `~/.openclaw/tools/jeedom2ha-gate/reports/24-4-20261031/`.

## Déploiement

- Plugin déployé sur `main` `b72af70` (#335, avec R1) le 31/10 à 19:08 (heure locale). Démon prêt, MQTT connecté.
- Export de décision : avant (`before-decision-export.json`) et après (`after-decision-export.json`).

## AC10 : équipements effectivement exposés et écartés par leur pièce

Liste préalable tirée de l'export (Task 0) : 502, 503, 516. Équipements désactivés en pièce exclue : 165, 550.

| eq | avant | après |
|---|---|---|
| 502 | `not_published` / `excluded_object` (étape 1) | `published` / `sure` (étape 4) |
| 503 | `not_published` / `excluded_object` (étape 1) | `published` / `sure` (étape 4) |
| 516 | `not_published` / `excluded_object` (étape 1) | `published` / `probable` (étape 4) |
| 165, 550 | `excluded_object` | inchangés (désactivés : exposition non effective) |

- 3 changements de décision, tous liés à HomeKit ; **aucun changement sans lien** ; `homekit_exposed_effective` présent pour tous les équipements et scénarios de l'export ; aucun retour arrière nécessaire.
- Inventaire MQTT : `homeassistant/` passe de 348 à 349 sujets, `jeedom2ha/` de 245 à 249. **Non concluant** : le relevé par `mosquitto_sub` sous-compte les messages retenus (limite constatée aussi en 23-4). Le décompte d'entités de HA reste à relever.
- **Non fait cette nuit** : le retour arrière sur un équipement de test (« Supprimer de Home Assistant » puis exclusion explicite) et les registres HA avant/après. Il faut écrire dans la production : à faire avec Alexandre.

## Gate 20-0 (lecture seule, écritures simulées)

Relance `gate-r3`, sur `main` `c631692` :

| parcours | verdict |
|---|---|
| page-principale-b | PASS |
| decouverte-piece-25-eq-579 | PASS |
| reference-bascule-eq-380 | PASS |
| rescan-page-principale | PASS |
| vue-maitre-detail-c | PASS (en échec au 1er passage : le parcours comparait « · N gardés (HomeKit) » de la carte à l'arbre, corrigé par #338, sans changement du produit) |
| exclusion-piece-simulee | PASS |
| controle-ecriture-non-declaree | FAIL attendu (contrôle négatif) |
| controle-exclusion-piece-non-declaree | FAIL attendu (contrôle négatif) |
| exclusion-publication-non-publiee | **non exécutable** : la précondition `override-declare: equipement:287` est refusée, car l'eq 287 porte déjà un réglage de publication sur la box. Le refus est voulu (le parcours ne s'exécute pas sur un équipement déjà réglé) et sans lien avec 24.4 (il échouait déjà au 1er passage). Le parcours devra viser un autre équipement non publié, à choisir avec Alexandre (consigne : ne pas toucher à l'eq 287). |

## Mesures du démon

- `getEquipmentStates` : **1 377 812 octets**, comme prévu (environ 1,38 Mo, soit environ 100 octets par équipement ajoutés par 24.4). Au-dessus du seuil de vigilance (1 350 000), sous le budget (1 500 000).
- Journal jeedom2ha : **0 ERROR** depuis le déploiement (19:08).

## Statut

`review`. Restent l'AC10 (retour arrière et registres HA, avec Alexandre) et la décision sur le parcours de l'eq 287.
