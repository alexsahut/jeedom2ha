# Sprint change proposal — revue UX de l'epic 25 (2026-10-19)

> Statut : **decided** (décisions d'Alexandre du 19/10 à 13:33 et 13:50, consignées par ClaudeBox).
> Avis de clawcode recueilli le 19/10 : favorable au découpage et au choix A1.
> Rédigé par ClaudeBox, avec identifiants fictifs ou techniques seulement (CC-48).

## Déclencheur

Le 19/10 à 13:33, Alexandre a fait sa revue UX/UI des stories 25.1, 25.3 et 25.4, déployées sur sa box (`90d4177`). Il demande cinq évolutions :

1. Une pièce exclue doit se voir directement sur sa carte de la page principale, au lieu de « 0/X publiés ».
2. Quand on entre dans une pièce depuis sa carte, la vue C doit être **filtrée sur cette pièce**. Aujourd'hui, la pièce est dépliée et sélectionnée, mais elle peut rester hors écran.
3. La cause d'une exclusion doit être lisible : par le plugin, par la pièce, ou individuelle.
4. Les exclusions se règlent dans les écrans. La page de configuration ne garde que l'exclusion **par plugin**.
5. On peut exclure une pièce depuis sa carte et depuis le détail de pièce, et un équipement depuis son détail (c'est déjà possible avec « Jamais »).

## Analyse (ClaudeBox, avec une relecture d'architecture et une relecture du backlog)

Le plugin a trois mécanismes d'exclusion :

| Mécanisme | Stockage | Écrit par | Effet |
|---|---|---|---|
| **A1** | `excludedPlugins`, `excludedObjects`, `jeedom2ha_excluded` | la page de configuration (texte libre), sauf `jeedom2ha_excluded` qui n'a aucun écrivain | Non-éligibilité. La cause est transmise jusqu'à la route 25.2 dans `equipment_decision.publication_reason` (`excluded_plugin`, `excluded_object`, `excluded_eqlogic`). Une seule cause par équipement, avec la priorité équipement > plugin > pièce. |
| **A2** | « Jamais » / « Toujours », dans `ha_overrides.json` | la surface (25.1) | `publication_excluded_eqlogic` ou `publication_excluded_command` |
| **A3** | `publishedScope*` | aucun écrivain | Aucune cause visible. **Non retenu.** |

Conséquences :
- La cause est **déjà** dans les données servies à l'interface : afficher la cause d'exclusion ne touche que l'interface.
- L'exclusion d'un équipement existe déjà (« Jamais »).
- L'exclusion d'une pièce passe par A1, avec `excludedObjects` (avis de clawcode). C'est sans migration, et les deux pièces exclues sur la box sont reprises telles quelles.

## Décisions (Alexandre, 19/10 13:50)

| # | Question | Décision |
|---|---|---|
| D1 | Un équipement réglé sur « Toujours » dans une pièce exclue | **La pièce prime.** L'équipement n'est pas publié et « Toujours » reste grisé : c'est le comportement actuel, l'éligibilité passe avant. Aucun changement du démon. |
| D2 | Comment rendre la pièce évidente en vue C | **Filtrer sur la pièce.** Depuis une carte, la vue C n'affiche que cette pièce, avec un bouton pour revenir à « Toutes les pièces ». L'état est porté par le fragment d'URL. |
| D3 | Effet d'une exclusion de pièce | **Immédiat.** Une confirmation chiffrée annonce « N entités seront retirées de Home Assistant », puis viennent la relecture et la synchro. Pas d'état « À appliquer ». |
| D4 | Saisie de l'exclusion par plugin | **Liste à cocher** des plugins présents, au lieu du texte libre. Même clé `excludedPlugins`, même format. |

Point repris de clawcode : **pas de purge implicite**. Toute exclusion de pièce passe par une confirmation chiffrée, et l'enregistrement puis la relecture sont explicites. Le gate 20-0 couvre l'héritage pièce → équipement par une écriture simulée déclarée dans `policy.mjs`. L'idempotence de la relecture et de la synchro après modification d'`excludedObjects` est vérifiée.

## Découpage : extension de l'epic 25, avant 25.5

| Ordre | Story | Contenu | Taille |
|---|---|---|---|
| 1 | **25.6** — Vue C filtrée sur la pièce d'entrée (D2) | Mode « cette pièce seule » à l'ouverture depuis une carte, bouton « Toutes les pièces », fragment d'URL et historique, zéro requête, gate 20-0 | S |
| 2 | **25.7** — Cause d'exclusion affichée | Mention « par le plugin X », « par la pièce » ou « individuelle » (« Jamais ») sur la ligne de l'arbre, dans le détail et sur la carte. Libellés alignés sur le glossaire 25.1. Pas de 7ᵉ état. « Désactivé » prime toujours. Interface seule. | S |
| 3 | **25.8** — Exclusion de pièce depuis la surface (D1, D3) | Nouvelle route PHP dédiée qui ne lit, modifie puis écrit qu'`excludedObjects`, suivie d'une relecture. Contrôle sur la carte B (qui n'ouvre pas la pièce) et dans le détail de pièce C. Confirmation chiffrée. La carte affiche « Pièce exclue ». Donnée `excluded` ajoutée à `j2haRoomsTree`. Route déclarée dans `policy.mjs` comme écriture simulée. Inventaire HA avant et après fait par ClaudeBox lors de la preuve terrain. « Sans pièce » n'est pas excluable. | M |
| 4 | **25.9** — Page de configuration : plugins seuls (D4) | Retrait du champ « Pièces exclues », renvoyé vers la surface. Liste à cocher pour les plugins. `saveFilteringConfig` n'écrit plus `excludedObjects`. Documentation mise à jour. | S |
| 5 | **25.5** — Recette UX finale | Inchangée, élargie aux stories 25.6 à 25.9 | — |

Hors périmètre : le mécanisme A3 (`publishedScope*`), les causes cumulées, et toute modification du contrat de décision ou des artefacts figés.

Les captures 23-2 et la bêta Market viennent après 25.5. L'epic 24 n'est pas changé. Pour 24-4 (HomeKit), voir D1 : une pièce exclue prime aussi sur l'exposition HomeKit, sauf nouvelle décision au moment de 24-4.
