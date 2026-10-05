# Story 20-1 — preuve terrain et validation UX du 05/10/2026

Preuve terrain de la story 20-1 (PR #204, fusion `95fde04`) et validation UX, faites le 05/10/2026.

Cadre :
- règle 2 d'Alex (28/09) et règle d'autonomie du 30/09 : déployer, prouver et fusionner sans son go, plugin et HA seulement ;
- consigne d'Alex du 05/10 à 08:54 : « fais la validation UX avec chrome, si OK, enchaîne sur la story 20.1, tu as toute la nuit ». La validation UX de 20-1 est faite par ClaudeBox sur cette délégation, comme celle de 16-8 ; Alex peut la reprendre.

Exécution par clawcode, relecture de chaque étape par ClaudeBox. Heures en heure locale (Paris), sauf mention `Z`.

## Déploiement

| Élément | Valeur |
|---|---|
| SHA déployé | `95fde04338f6d5ab6270e5111b9069c9657af466`, fusion de la PR #204 |
| CI de `main` sur ce SHA | verte : 10 succès, `Burn-In` `skipped` |
| SHA précédent sur la box | `957aef4` (CC-38, déployé à 07:36:38Z) |
| Fichiers livrés qui changent | `desktop/php/jeedom2ha.php`, `desktop/js/jeedom2ha_mapping_override.js`, `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/css/jeedom2ha.css` |
| Déploiement | standard (`--restart-daemon`), depuis un worktree neuf détaché sur `origin/main`, à 09:36:47Z ; dry-run préalable sans erreur |
| Archive de retour arrière | `jeedom2ha-20261005T093647Z-sWBCcR.tar.gz` (non utilisée) |
| Tag | `deploy-95fde04338f6d5ab6270e5111b9069c9657af466-20261005T093657Z` |

Le dry-run a été différé jusqu'à la fin de la CI de `main`, que le garde-fou du script exige. Le worktree de déploiement doit aussi recevoir le `.env` du dépôt de travail (hôte, port et compte de la box).

## Relevés avant et après

- VERSION après : `95fde04...`, `git_status=clean`.
- Healthcheck MQTT et sync OK : 292 équipements, 262 publiés. Inventaire MQTT : 353 entités avant et après, aucun topic ajouté ni retiré.
- Relevé de parité : seuls `captured_at` et `label` changent.
- Box, `ps -eo pid,user,lstart,comm` : seul le démon jeedom2ha change (PID 2041326 remplacé par 2279862, `www-data`, lancé à 11:36:49, même PID à deux relevés). Les autres écarts sont transitoires : threads noyau, workers apache et php, sessions SSH.
- Journal du plugin :
  - 0 nouvelle ligne `ERROR` : le total reste à 3016 ;
  - 0 `CLEANUP` ;
  - `[STATE-LISTENER] 227 listener(s)` à 11:36:52, comme avant.
- Journal du démon : 0 `ERROR`.
- Les 4 fichiers servis ont le sha256 du worktree, et contiennent le code de 20-1 (`isDisabledDiagnostic`, `getOverrideSelectorState`, `byObjectId(null, false)`).
- `ha_overrides.json` : sha256 inchangé (`083ab5bf88ace22f18376d2c259e66dc87940d8c1b930c1dbd87b9d29621488d`).
- Home Assistant, en lecture seule (ClaudeBox) :
  - 354 entités jeedom2ha au registre ;
  - registres d'entités et d'appareils non modifiés (derniers changements le 04/10) ;
  - le relevé `core.restore_state` de 11:45:11, après le déploiement, a les mêmes décomptes que celui de 11:15:11, avant le déploiement : 341 entités, 7 indisponibles (boutons), 113 `unknown` (button 90, light 12, sensor 10, binary_sensor 1).

## Correction du parcours de découverte (PR #205)

Le premier passage de ClaudeBox dans Chrome, juste après le déploiement, a montré une erreur dans son propre relevé de la Task 0.2 : l'équipement désactivé du Garage (objet 25) est l'eq 514. L'eq 279, retenu par erreur, est dans le bureau (objet 3). Le parcours fusionné aurait échoué au premier passage.

- PR #205, fusion `05634b8` : le parcours relève l'eq 514. La story précise aussi que l'eq 339 du Garage, désactivé et exclu, compte parmi les exclus, car l'exclusion est évaluée avant la désactivation (`resources/daemon/models/topology.py:303-312`).
- Revue : relecture indépendante « fusionnable », Codex en limite d'usage, CI verte.
- Entre `95fde04` et `05634b8`, seuls le parcours et la story changent. Le code de `main` est donc celui de la box.

## Gate 20-0 (code de `main`, `05634b8`)

| Fin (UTC) | Parcours | Verdict | Constat |
|---|---|---|---|
| 11:32:58Z | découverte, lecture seule | PASS | Actions de « Gestion » avant la surface et avant le bandeau de santé. Aucune lecture `getMappingOverrides` avant l'ouverture d'une pièce. Carte « Sans pièce » présente, 20 équipements. Enphase : 5368 `non-couverte`, 5369 `bloquante`, 4 `prete`, synthèse « Partiellement publié : 4 prête(s), 1 bloquante(s). ». Garage, 18 badges : 183, 228, 329, 338, 339, 341 et 559 `exclu` ; 514 `desactive` ; 579 `partiel` ; 287 `bloque` ; les 8 autres `publie`. Les 23 cellules de l'eq 514 sont `desactive`. Console 0, aucune écriture. |
| 11:36:08Z | référence (bascule) | PASS | Cible 5369 : bloquante, puis prête (« Sera publié dans Home Assistant : 5 commande(s) prête(s). »), puis bloquante ; synthèse restaurée. Écritures simulées seulement (`saveMappingOverride`, `revertMappingOverride`). |

Le journal du démon n'a pas été tronqué pendant ces deux exécutions, lancées vers la demie. Le contrôle générique des secrets ne trouve rien dans les rapports.

## Validation UX (Chrome, 13:36 à 13:40, box en `95fde04`)

Dans Chrome, en lecture seule. Gestes faits : ouverture de pièces, dépliage d'équipements et de la ligne « Parc global ». Gestes exclus : aucun changement de type, aucun « Publier », aucun « Suppr. ».

**Conforme :**
- AC1 : la surface par pièce est la seule surface d'édition ; la synthèse « Parc global » et l'action « Diagnostic » restent en place jusqu'à 20-3.
- AC2 : « Ajouter », « Configuration » et « Diagnostic » sont directement sous le titre « Gestion ».
- AC3 : la carte « Sans pièce » est la dernière, avec 20 équipements, et s'ouvre comme une pièce.
- AC4 :
  - dans le Garage, l'eq 514 est grisé, avec la mention « (désactivé dans Jeedom) » et le badge neutre « Désactivé dans Jeedom : ne sera pas publié dans Home Assistant. » ; l'eq 339, désactivé et exclu, affiche « Exclu » ;
  - dans « Sans pièce », 2 équipements sont désactivés, et un troisième, désactivé et exclu, affiche « Exclu ».
- AC6 : dans le Garage, chacune des 308 cellules a un seul état : 93 prêtes, 3 bloquantes, 101 non couvertes, 88 exclues et 23 désactivées.
- AC7 :
  - les 96 commandes prêtes ou bloquantes du Garage gardent un sélecteur actif ;
  - les 212 autres ont un sélecteur désactivé, avec l'info-bulle de leur état, sur le sélecteur et sur sa cellule.
- Lisibilité en thème sombre : les cellules et badges désactivés restent lisibles.
- Console de la page : aucune erreur du plugin. Seule une extension du navigateur en produit.

**Constat non bloquant, reporté :**
- **Équipement exclu sans commande.** Dans « Sans pièce », les 4 équipements 588 à 591 sont « Exclu par le plugin » dans « Parc global ». La surface affiche pourtant « Aucune commande projetable en Home Assistant pour cet équipement. ». Leur arbre ne contient aucune commande, et l'état « Exclu » se déduit des commandes. Les deux vues disent « non publié », mais pas pour la même raison. Le correctif demande que l'arbre du démon porte la décision de l'équipement, puisque l'interface ne recalcule rien. À traiter en 20-2, qui pose l'exclusion au niveau de l'équipement dans la surface ; sinon en 20-3, qui revoit les libellés.

Fait vérifié, sans défaut : les 3 équipements bloquants de « Sans pièce » ont chacun 13 commandes « types génériques non configurés dans Jeedom ». Ce sont de vrais blocages, actionnables dans Jeedom.

## Verdict

**20-1 est prouvée et validée UX, et passe `done`.** CC-25 est fermé : équipements désactivés et « Sans pièce » présents dans la surface, et état « non couverte » rendu depuis CC-37.
