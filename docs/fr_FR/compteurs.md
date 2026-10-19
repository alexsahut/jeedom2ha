<!--
COMPTEURS:DEBUT — BLOC ISOLÉ, À RÉÉCRIRE SEUL SI LA SÉMANTIQUE DES ÉTATS OU DES COMPTEURS CHANGE

En-tête de maintenance (invisible pour l'utilisateur) :
- Réécrit par la story 25.1 : un équipement n'a plus qu'UN état (six états : Publié, À appliquer, Bloqué, Exclu,
  Désactivé, Rien à publier), lu par le badge, la ligne de l'équipement déplié et les compteurs de la pièce.
  Les trois chiffres de la story 22.2 (publiés / en attente / non pris en charge) sont remplacés.
- Règles d'état R1 à R8 : resolveEquipmentState (desktop/js/jeedom2ha_mapping_override.js), tests dans
  tests/unit/test_story_25_1_etat_unique.node.test.js. Catégories de commande : classifyCommandCategory,
  partition des codes de cause COMMAND_CAUSE_CATEGORIES (même fichier).
- Libellés d'interface décrits ici : ceux produits par buildRoomCounterLabels et buildEquipmentCounterLabels
  (même fichier), alimentés par summarizeRoom et summarizeEquipmentCounters, affichés par renderRoomCounters et
  renderEquipmentCounters (desktop/js/jeedom2ha_mapping_surface.js).
- Champs du démon lus : sync_status.published_in_ha, sync_status.current_should_publish,
  sync_status.synced_should_publish, sync_status.override_pending, entities[].override_pending,
  commands[].published_in_ha, equipment_decision (GET /system/mapping_overrides/{eq_id}).
- Story 25.3 : la page principale lit les états de tous les équipements en UN appel (action ajax getEquipmentStates,
  route GET /system/equipment_states) et en dérive la jauge de la maison et les repères des cartes avec les MÊMES
  fonctions (resolveEquipmentState, summarizeRoom, puis summarizeHouse, desktop/js/jeedom2ha_mapping_override.js ;
  desktop/js/jeedom2ha_overview.js). Un équipement de Jeedom absent de la réponse est « non lu » (hors des six états).
  Tests : test_story_25_3_etats_lecture, test_story_25_3_page_b.
- Tests Node correspondants : test_story_25_1_etat_unique, test_story_25_1_compteurs, test_story_25_1_surface,
  test_story_20_3_compteurs_piece, test_story_22_2_compteurs_portees.
- Règle de cloisonnement : aucun libellé de compteur (ligne des états de la pièce, ligne des commandes d'un équipement,
  « non lu », messages de chargement/indisponibilité) ne doit apparaître ailleurs que dans ce fichier. index.md renvoie
  ici par un simple lien. Les mots des états (badge) restent décrits dans index.md.
- Quand la sémantique change de nouveau, remplacer tout ce fichier ; rien d'autre dans la documentation n'est à modifier.
-->

# Les états et les compteurs de la vue de travail

Retour à la [documentation](index.md#la-vue-de-travail).

Chaque équipement porte **un seul état**. Le même mot, avec la même teinte, se lit dans l'arbre de la vue de travail, dans le badge à droite du nom de l'équipement affiché, dans la ligne de ce détail et dans les compteurs sous le titre de la pièce. Il n'y a plus de chiffres à rapprocher : si le badge dit « Publié », l'équipement est compté « publié » dans la pièce.
<!-- CAPTURE-A-PRENDRE: compteurs du détail de pièce -->

## Comment lire un état

| État (teinte) | Ce que cela veut dire | Que faire |
|---|---|---|
| **Publié** (vert) | L'équipement est **présent dans Home Assistant**, d'après l'état réel du démon. | Rien. Si des commandes sont bloquées, une mention orange l'indique (« 2 bloquées »). |
| **À appliquer** (bleu) | Le plan courant et ce qui est dans Home Assistant **ne concordent pas encore** : un réglage a été posé mais pas appliqué, ou l'équipement doit être publié et ne l'est pas encore. | Cliquer sur « Appliquer » (ou lancer « Relire Jeedom »). |
| **Bloqué** (orange) | Rien n'est dans Home Assistant et au moins une commande est **bloquée** par une cause que vous pouvez corriger. | Lire l'encart de cause du panneau. |
| **Exclu** (gris) | L'équipement est volontairement écarté : réglage « Jamais », configuration du plugin (plugins, pièces) ou réglage propre à l'équipement dans Jeedom. | Rien, c'est un choix. |
| **Désactivé** (gris, en italique) | L'équipement est désactivé dans Jeedom. | Réactivez-le dans Jeedom si vous le souhaitez. |
| **Rien à publier** (gris) | Aucune commande n'est publiable ni bloquée : les commandes sont toutes ignorées, ou l'équipement n'a pas de commande. | Rien. |

Le mot est toujours écrit, avec une icône : la couleur ne remplace jamais le texte.

### Les priorités entre les états

Les règles s'appliquent dans cet ordre, la première qui convient l'emporte (« P » = l'équipement est présent dans Home Assistant) :

| Ordre | Condition | État |
|---|---|---|
| R1 | Un réglage est en attente (sauf pour un équipement jamais synchronisé : le démon marque alors tout en attente faute de décision appliquée) | À appliquer |
| R2 | P | Publié |
| R3 | L'équipement est désactivé dans Jeedom | Désactivé |
| R4 | L'équipement est exclu (décision d'équipement, ou toutes ses commandes exclues) | Exclu |
| R5 | Pas de P, au moins une commande publiable et le plan courant demande la publication | À appliquer |
| R6 | Présence inconnue (démon plus ancien), au moins une commande publiable, le plan ne refuse pas la publication | À appliquer (jamais « Publié ») |
| R7 | Au moins une commande bloquée | Bloqué |
| R8 | Sinon | Rien à publier |

Conséquences à retenir :

- **« Désactivé » l'emporte sur « Exclu »** : un équipement à la fois désactivé et exclu s'affiche « Désactivé », et il est compté « désactivé », jamais « exclu ».
- **La cause d'exclusion n'est pas un état de plus.** « Par le plugin X », « par la pièce » et « individuelle » sont des mentions à côté du mot « Exclu » ; les six états et leurs effectifs ne changent pas. La ventilation des exclus d'une pièce (ligne « Exclus : » du détail de pièce, repère « N exclus » de la carte) ne compte que les équipements dont la cause est connue : sa somme peut être inférieure au compte « exclu », l'écart étant dit « autre ». Un équipement « Désactivé » n'a jamais de cause d'exclusion.
- **Il n'existe pas d'état « partiel »** : un équipement dont une partie des commandes est dans Home Assistant est « Publié », avec la mention orange du nombre de commandes bloquées.
- Un équipement hors du périmètre de publication (le plan ne demande pas sa publication) n'est jamais « À appliquer » : « Appliquer » ne pourrait pas le publier.

## Les quatre catégories de commande

| Catégorie | Définition | Compte comme défaut ? |
|---|---|---|
| **Publiée** (vert) | La commande est portée par **au moins une entité présente** dans Home Assistant. | Non |
| **Bloquée** (orange) | Absente de Home Assistant, avec une cause **que vous pouvez corriger**. | **Oui** |
| **Ignorée** (gris) | Absente de Home Assistant et **sans équivalent** dans Home Assistant : rien à faire. | Non |
| **Exclue** (gris) | Écartée par un réglage. | Non |

Les commandes **ignorées** ne sont jamais comptées comme un défaut et ne sont pas des lignes du tableau : elles sont repliées sous le tableau. Une cause inconnue du plugin (démon plus récent) classe la commande « Bloquée » : elle n'est jamais masquée. Voir [Les causes de blocage](index.md#les-causes-de-blocage).

## La jauge de la maison

Sur la page principale, le bloc de la maison reprend les mêmes états, **équipement par équipement**, pour toutes les pièces : « N publiés sur M » où M est le nombre d'équipements Jeedom de toutes les cartes (la carte « Sans pièce » comprise) et N ceux à l'état **Publié**. La jauge est découpée, dans cet ordre, en **publiés** (vert), **à appliquer** (bleu), **bloqués** (orange), **exclus et autres** (gris : exclus, désactivés et rien à publier) et **non lus** (hachuré). La somme des segments est toujours M, et celle des cartes de pièce est toujours celle de la maison.

- **Non lu** n'est pas un septième état : c'est un équipement de Jeedom dont les chiffres n'ont pas pu être lus (le démon ne le connaît pas encore, ou sa lecture a échoué). Il n'est jamais compté publié, bloqué, exclu ni désactivé, et la jauge ne devient jamais « pleine de non lus » quand la lecture n'a pas eu lieu : elle reste neutre avec un message.
- **Ce qui n'est pas un état** : la mention « N bloquées » d'un équipement publié n'est pas un équipement bloqué ; elle apparaît sur la ligne de la liste filtrée, dans l'arbre de la vue de travail et dans le détail de l'équipement, jamais dans la jauge. Une maison à zéro bloqué peut donc contenir des commandes bloquées dans des équipements publiés.
- Les chiffres sont relus à l'ouverture de la page, après chaque action, au retour sur l'onglet après plus d'une minute et par « Actualiser ». « Chiffres relus à HH:MM » est l'heure de la dernière lecture par la page.

## Les repères d'une carte de pièce

La carte d'une pièce affiche « n / t publiés » (t = équipements de la pièce), une jauge fine construite comme celle de la maison, puis, **seulement s'ils sont non nuls**, les repères **« N bloqués »** (orange), **« N à appliquer »** (bleu) et **« N non lus »** (gris). Un liseré orange signale une pièce qui contient au moins un équipement bloqué. Ces chiffres sont **les mêmes** que ceux de l'arbre de la vue de travail (repères d'une pièce) et des compteurs du détail de pièce : tous sont calculés à partir de la même lecture, sans rien relire.

## La ligne des états (sous le titre de la pièce)

Elle comporte un chiffre et un mot court pour chaque état **non nul**, toujours dans cet ordre : **publié**, **à appliquer**, **bloqué**, **exclu**, **désactivé**, **rien à publier**. Un état à zéro n'est pas affiché. Le mot est au singulier pour 1, au pluriel au-delà (« 1 publié », « 9 publiés », « 2 à appliquer »). La somme des chiffres est le nombre d'équipements lus : chaque équipement est compté une fois, dans son seul état. Chaque compteur est un filtre de l'arbre (un clic le pose, un second le retire), le même que celui de la page principale.

Il n'y a **pas de compteur de commandes au niveau de la pièce** : l'unité de décision est l'équipement.

Ces chiffres viennent de la lecture des états de la page principale : ils ne demandent aucune lecture de plus et sont présents dès l'ouverture de la vue. Tant que cette lecture n'a pas eu lieu ou a échoué, les compteurs ne sont pas affichés et la mention de la page principale (« Aucune synchronisation n'a encore eu lieu », « Mise à jour en cours… » ou « Chiffres indisponibles ») s'affiche aussi dans la vue ; jamais de « NaN » ni de faux « non lus ».

Quand certains équipements de la pièce ne sont pas lus — le démon ne les connaît pas encore, ou leur lecture a échoué — la ligne se termine par « 1 équipement non lu » ou « 2 équipements non lus » : ils ne sont pas comptés. Si le démon est une version plus ancienne qui n'indique pas la présence dans Home Assistant, la ligne le dit (« … dont la présence dans Home Assistant est inconnue (démon plus ancien) ») et ces équipements ne sont jamais comptés « publiés ».

## La liste « À traiter dans cette pièce »

Sous les compteurs, la vue liste les équipements **bloqués** et **à appliquer** de la pièce, et seulement eux : état, nom, nombre de commandes concernées et cause dite une seule fois. Elle est produite avec les mêmes règles d'état et de cause que le détail d'un équipement, à partir de la même lecture que les compteurs : elle ne demande aucune lecture de la configuration des équipements.

## La ligne d'un équipement affiché

Quand vous choisissez un équipement, une ligne s'affiche au début de son détail : **son état** (le même mot que le badge), puis le détail de **ses commandes**, par exemple :

> Publié · 3 publiées · 1 bloquée · 5 ignorées

Les zéros sont masqués, les pluriels accordés (« 1 publiée », « 3 publiées »). Les catégories apparaissent dans cet ordre : publiées, à appliquer (publiables mais pas encore dans Home Assistant), bloquées, ignorées, exclues. Seules les commandes **bloquées** comptent comme défaut : dans l'exemple, le défaut de l'équipement vaut 1, et les 5 commandes ignorées n'y comptent pas.
<!-- CAPTURE-A-PRENDRE: ligne de compteurs d'un équipement déplié -->

<!-- COMPTEURS:FIN -->
