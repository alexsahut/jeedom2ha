<!--
COMPTEURS:DEBUT — BLOC ISOLÉ, À RÉÉCRIRE SEUL SI LA SÉMANTIQUE DES COMPTEURS CHANGE

En-tête de maintenance (invisible pour l'utilisateur) :
- Réécrit par la story 22.2 : la sémantique décrite ici est celle de « publié = présent dans Home Assistant »,
  « en attente d'application » et « non pris en charge » (le bandeau d'obsolescence de l'ancienne version est retiré).
- Libellés d'interface décrits ici : ceux produits par buildRoomCounterLabels et buildEquipmentCounterLabels
  (desktop/js/jeedom2ha_mapping_override.js), alimentés par summarizeRoom et summarizeEquipmentCounters (même
  fichier), affichés par renderRoomCounters et renderEquipmentCounters (desktop/js/jeedom2ha_mapping_surface.js).
- Champs du démon lus : sync_status.published_in_ha, sync_status.override_pending, entities[].present_in_ha,
  entities[].override_pending, commands[].published_in_ha (GET /system/mapping_overrides/{eq_id}).
- Tests Node correspondants : tests/unit/test_story_20_3_compteurs_piece.node.test.js et
  tests/unit/test_story_22_2_compteurs_portees.node.test.js ; tests du démon : resources/daemon/tests/unit/test_story_22_2_presence_et_cc60.py.
- Règle de cloisonnement : aucun libellé de compteur (ligne équipements, ligne commandes, « non lu »,
  messages de chargement/indisponibilité) ne doit apparaître ailleurs que dans ce fichier. index.md renvoie
  ici par un simple lien. Les libellés de badge d'équipement « N commande(s) prête(s) / bloquante(s) » restent
  acceptés dans index.md (ce sont des libellés de badge, pas de compteur).
- Quand la sémantique change de nouveau, remplacer tout ce fichier ; rien d'autre dans la documentation n'est à modifier.
-->

# Les compteurs de la fenêtre d'une pièce

Retour à la [documentation](index.md#la-fenêtre-dune-pièce).

Les compteurs répondent à trois questions : **qu'est-ce qui est réellement dans Home Assistant ? qu'est-ce qui attend d'être appliqué ? qu'est-ce que le plugin ne prend pas en charge ?** Ils s'affichent à deux endroits : sous le titre de la pièce (deux lignes, pour toute la pièce) et dans chaque équipement déplié (une ligne, pour cet équipement).
<!-- CAPTURE-A-PRENDRE: compteurs de la fenêtre d'une pièce -->

## D'où viennent les chiffres

Les compteurs sont calculés à partir de ce que la fenêtre vient de lire pour **les équipements de cette pièce**. Le plugin ne recalcule rien lui-même : il reprend ce que le démon indique, y compris **la présence réelle dans Home Assistant** de chaque équipement et de chaque commande. Ils se mettent à jour à mesure que les équipements sont lus, et de nouveau après une action qui recharge un équipement.

Pendant la lecture, la ligne affiche « Chargement des compteurs… ». Si aucun équipement de la pièce n'a pu être lu, elle affiche « Compteurs indisponibles : la configuration des équipements de cette pièce n’a pas pu être lue. »

## Les trois notions

| Notion | Ce que cela veut dire |
|---|---|
| **Publié dans Home Assistant** | L'élément est **présent dans Home Assistant** (d'après l'état réel du démon), et non « il devrait l'être ». Une commande est publiée dès qu'**au moins une** entité présente dans Home Assistant la porte. |
| **En attente d'application** | Un réglage (type, exclusion, forçage…) a été posé mais **pas encore appliqué** : il faut cliquer sur « Appliquer » (ou lancer un rescan) pour que Home Assistant le reflète. |
| **Non pris en charge** | Le plugin ne publie pas cet élément et il n'y a rien en attente : la commande est bloquante ou n'est couverte par aucun type Home Assistant, ou l'équipement entier n'a rien dans Home Assistant. Voir [les causes](index.md#les-causes-affichées-dans-la-colonne-diagnostic). |

Ces trois notions sont **indépendantes** : un élément peut être compté dans plusieurs d'entre elles (par exemple un équipement publié dont un nouveau réglage attend d'être appliqué compte à la fois « publié » et « en attente »). Un équipement exclu ou désactivé n'est jamais « non pris en charge » : ce n'est pas un défaut.

## La ligne des équipements (sous le titre de la pièce)

Elle comporte cinq compteurs, toujours dans cet ordre. Le libellé est au singulier pour 0 ou 1, au pluriel au-delà (« 0 équipement publié dans Home Assistant », « 3 équipements publiés dans Home Assistant »).

| Compteur affiché | Ce qu'il compte |
|---|---|
| **équipement(s) publié(s) dans Home Assistant** | Les équipements **présents** dans Home Assistant. Un équipement dont seul un capteur secondaire est publié (le type principal étant refusé) est compté : il est bien dans Home Assistant. |
| **équipement(s) en attente d'application** | Les équipements dont un réglage attend d'être appliqué (le badge « Override en attente — pas encore republié vers Home Assistant » ou « pas encore appliqué » est affiché). |
| **équipement(s) non pris en charge** | Les équipements qui ne sont **pas** dans Home Assistant, n'ont rien en attente, et ne sont ni exclus ni désactivés. |
| **équipement(s) exclu(s)** | Les équipements dont le badge indique « Exclu… ». Compté à part : l'exclusion est un choix, pas un défaut. |
| **équipement(s) désactivé(s) dans Jeedom** | Les équipements dont le badge indique « Désactivé dans Jeedom… ». Compté à part. |

Tant que certains équipements de la pièce ne sont pas lus — pendant le chargement, ou parce que leur lecture a échoué — la ligne se termine par « N équipement(s) non lu(s) » : leurs chiffres ne sont pas comptés, et s'ajoutent à mesure que les lectures aboutissent. Si le démon est une version plus ancienne qui n'indique pas la présence dans Home Assistant, la ligne le dit (« … dont la présence dans Home Assistant est inconnue (démon plus ancien) ») et ces équipements ne sont comptés ni publiés ni non pris en charge.

## La ligne des commandes (sous le titre de la pièce)

Elle comporte trois compteurs, sur l'ensemble des équipements lus de la pièce :

| Compteur affiché | Ce qu'il compte |
|---|---|
| **commande(s) publiée(s) dans Home Assistant** | Les commandes portées par **au moins une entité présente** dans Home Assistant. |
| **commande(s) en attente d'application** | Les commandes portées par une entité dont un réglage attend d'être appliqué. |
| **commande(s) non prise(s) en charge** | Les commandes **absentes** de Home Assistant dont la colonne « Diagnostic » indique « Ne sera pas publié — … » (bloquante) ou qu'aucun type Home Assistant ne prend en charge (non couverte). Ce compteur réunit des causes que vous pouvez corriger et d'autres que vous ne pouvez pas corriger vous-même. |

Les commandes exclues, ou celles d'un équipement désactivé, ne figurent dans aucun de ces trois compteurs. Une commande peut être « publiée » même si l'entité principale de son équipement est refusée, dès qu'une autre entité présente la porte (c'est le cas d'une commande d'état publiée par un capteur binaire secondaire).

## La ligne d'un équipement déplié

Quand vous dépliez un équipement, une ligne de compteurs s'affiche au-dessus de ses boutons, **pour cet équipement seul**. Elle reprend les trois compteurs de commandes ci-dessus (publiées dans Home Assistant, en attente d'application, non prises en charge) et ajoute « équipement exclu » ou « équipement désactivé dans Jeedom » quand c'est le cas. Les chiffres de la pièce sont la somme de ceux des équipements lus.
<!-- CAPTURE-A-PRENDRE: ligne de compteurs d'un équipement déplié -->

## Vérifier un chiffre

Pour recompter à la main une pièce : ouvrez chaque équipement, comptez ses commandes dont la colonne « Diagnostic » est « Sera publié : … » **et** qui sont présentes dans Home Assistant, puis comparez avec le compteur de la pièce. Un écart entre « Sera publié » et « publié dans Home Assistant » est normal quand un réglage attend d'être appliqué : c'est exactement ce que le compteur « en attente d'application » signale.

<!-- COMPTEURS:FIN -->
