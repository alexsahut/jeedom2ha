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

## AC10 : retour arrière sur un équipement de test (2026-11-01, avec Alexandre)

Équipement de test : **502** (capteur de température virtuel, exposé à HomeKit, une entité, publié par 24.4). Les écritures ont été faites au clic par Alexandre dans la surface ; ClaudeBox a vérifié chaque étape dans la surface et sur le broker (sonde en lecture seule `24-4-ac10-20261101/probe-502.sh`, VM openclaw, hors dépôt : présence de la découverte retenue de l'eq 502 et nombre de découvertes `homeassistant/+/+/config` de jeedom2ha).

| étape (heure UTC) | surface | broker |
|---|---|---|
| avant (≈ 18:55) | `Publié`, réglage « Automatique » | — ; registre HA : l'entité de l'eq 502 est présente (951 entités au total) |
| « Supprimer de Home Assistant » confirmé (19:11) | `À appliquer` | découverte de l'eq 502 **absente**, 349 découvertes |
| « Jamais » puis « Relire Jeedom » (19:13) | `Exclu` (« Exclusion individuelle : réglage « Jamais » ») | toujours **absente** après la relecture, 349 |
| « Automatique » (19:13) | `À appliquer` (rien ne se recrée seul après une suppression, comme l'annonce la confirmation) | toujours absente, 349 |
| « Appliquer » (19:14) | `Publié` | découverte **présente** (678 octets), **350** |

- Le retour arrière fonctionne sur un équipement relevé par l'exposition HomeKit : la suppression le retire, l'exclusion explicite le garde hors de HA malgré l'exposition, le retour en automatique puis « Appliquer » le republie.
- Registres HA : relevé « avant » dans l'interface de HA ; les relevés suivants sont faits sur le broker (source de la découverte MQTT), l'interface HA se déconnectant à chaque rechargement dans le navigateur de ClaudeBox. L'historique HA de l'entité de l'eq 502 (depuis le 31/10) est perdu, comme l'annonce la confirmation.

## Gate : parcours de l'eq 287

Résolu par la story 24.11 (option b d'Alexandre) : le parcours choisit sa cible à l'exécution ; gate de production vert le 01/11 (cible 460).

## Statut

`done` : AC10 faite le 01/11 avec Alexandre.
