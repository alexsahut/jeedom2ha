<!--
COMPTEURS:DEBUT — BLOC ISOLÉ, À RÉÉCRIRE SEUL PAR LA STORY « COMPTEURS »

En-tête de maintenance (invisible pour l'utilisateur) :
- Bandeau d'obsolescence : « Cette section décrit la sémantique des compteurs avant la story compteurs. »
- Libellés d'interface décrits ici : ceux produits par buildRoomCounterLabels (desktop/js/jeedom2ha_mapping_override.js),
  alimentés par summarizeRoom (même fichier), affichés par renderRoomCounters (desktop/js/jeedom2ha_mapping_surface.js).
- Tests Node correspondants : tests/unit/test_story_20_3_compteurs_piece.node.test.js (10 tests, tous passés avec `node --test` au moment de la rédaction).
- Règle de cloisonnement : aucun libellé de compteur (ligne équipements, ligne commandes, « non lu »,
  messages de chargement/indisponibilité) ne doit apparaître ailleurs que dans ce fichier. index.md renvoie
  ici par un simple lien. Vérification : le motif de grep retenu est consigné dans la section « R1 » du Dev Agent Record de la story 20.5 (AC6). Les libellés de badge d'équipement « N commande(s) prête(s) / bloquante(s) » restent acceptés dans index.md (ce sont des libellés de badge, pas de compteur).
- Quand la sémantique change (« publiés » = présents dans Home Assistant, « en attente d'application »,
  « non pris en charge »), remplacer tout ce fichier ; rien d'autre dans la documentation n'est à modifier.
-->

# Les compteurs de la fenêtre d'une pièce

> **À savoir.** Cette page décrit les compteurs **tels qu'ils fonctionnent aujourd'hui**. Leur définition doit évoluer dans une prochaine version du plugin ; cette page sera alors remplacée.

Retour à la [documentation](index.md#la-fenêtre-dune-pièce).

Quand vous ouvrez une pièce, deux lignes de compteurs s'affichent sous son titre.
<!-- CAPTURE-A-PRENDRE: compteurs de la fenêtre d'une pièce -->

## D'où viennent les chiffres

Les compteurs sont calculés à partir de ce que la fenêtre vient de lire pour **les équipements de cette pièce** : ils reprennent le diagnostic affiché sur chaque équipement et chaque commande, sans rien recalculer de plus. Ils se mettent à jour à mesure que les équipements sont lus, et de nouveau après une action qui recharge un équipement.

Pendant la lecture, la ligne affiche « Chargement des compteurs… ». Si aucun équipement de la pièce n'a pu être lu, elle affiche « Compteurs indisponibles : la configuration des équipements de cette pièce n’a pas pu être lue. »

## La ligne des équipements

Elle comporte quatre compteurs, toujours dans cet ordre. Le libellé est au singulier pour 0 ou 1, au pluriel au-delà (« 0 équipement publié », « 3 équipements publiés »).

| Compteur affiché | Ce qu'il compte |
|---|---|
| **équipement(s) publié(s)** | Les équipements qui ont **au moins une commande prête** : ceux dont le badge indique « Sera publié… » ou « Partiellement publié… ». |
| **équipement(s) exclu(s)** | Les équipements dont le badge indique « Exclu… ». |
| **équipement(s) désactivé(s) dans Jeedom** | Les équipements dont le badge indique « Désactivé dans Jeedom… ». |
| **équipement(s) à corriger** | Les équipements qui ont **au moins une commande bloquante**. |

Tant que certains équipements de la pièce ne sont pas lus — pendant le chargement, ou parce que leur lecture a échoué — la ligne se termine par « N équipement(s) non lu(s) » : leurs chiffres ne sont pas comptés, et s'ajoutent à mesure que les lectures aboutissent.

**Deux précisions importantes :**

- **« Publié » veut dire « sera publié selon le diagnostic », pas « présent dans Home Assistant ».** Un équipement peut être compté « publié » alors que son réglage attend encore d'être appliqué.
- **Un équipement partiellement publié est compté deux fois** : « publié » (il a au moins une commande prête) et « à corriger » (il a aussi au moins une commande bloquante).

## La ligne des commandes

Elle comporte trois compteurs :

| Compteur affiché | Ce qu'il compte |
|---|---|
| **commande(s) prête(s)** | Les commandes dont la colonne « Diagnostic » indique « Sera publié : … ». |
| **commande(s) bloquante(s)** | Les commandes dont la colonne « Diagnostic » indique « Ne sera pas publié — … », hors commandes exclues, désactivées ou non couvertes. Ce compteur réunit des causes que vous pouvez corriger et d'autres que vous ne pouvez pas corriger vous-même. |
| **commande(s) non couverte(s)** | Les commandes qu'aucun type Home Assistant ne prend en charge. Elles ne sont jamais comptées comme bloquantes. |

Les commandes exclues, ou celles d'un équipement désactivé, ne figurent dans aucun de ces trois compteurs.

<!-- COMPTEURS:FIN -->
