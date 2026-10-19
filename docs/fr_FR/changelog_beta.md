# Changelog — jeedom2ha (beta)

>**NOTE**
>
>S'il n'y a pas d'information sur la mise à jour, c'est que celle-ci concerne uniquement de la documentation, une traduction ou des corrections mineures.

---

# 2026-10-19 — Vue de travail : une carte ouvre la pièce seule

- Un clic sur une carte de pièce ouvre la vue de travail sur **cette pièce seule** : elle est tout de suite visible, même dans une maison de plus de vingt pièces. Le bouton « Toutes les pièces », en tête de l'arbre, élargit à toute la maison en gardant votre choix.
- Depuis une puce, un segment de la jauge ou une ligne de la liste filtrée, la vue s'ouvre sur toutes les pièces, comme avant.
- Le bouton qui ramène à la page principale s'appelle désormais « Page principale ». L'adresse de la page garde la portée (`seule:1`) ; « Précédent » garde ses trois niveaux.
- Aucune modification du démon, ni de ce qui est publié dans Home Assistant. Aucune requête de plus.

---

# 2026-10-19 — Vue de travail : l'arbre des pièces et le détail, sans fenêtre

- Un clic sur une carte de pièce, sur une puce ou un segment de la jauge, ou sur une ligne de la liste filtrée ouvre une **vue de travail** dans la page du plugin, à la place de l'ancienne fenêtre de pièce : l'arbre des pièces et de leurs équipements à gauche (recherche, filtres), le détail à droite.
- Le détail d'une pièce propose « Republier la pièce », le menu « ⋯ » et la liste « À traiter dans cette pièce » (équipements bloqués ou à appliquer, cause dite une fois, « Ouvrir les types génériques » ou « Appliquer »). Le détail d'un équipement reprend l'état, le réglage de publication, le tableau des commandes et les actions déjà connus.
- La configuration d'un équipement n'est lue que lorsque vous le choisissez ; ouvrir une pièce ne lit plus que les chiffres déjà chargés par la page principale.
- « Toutes les pièces » et le bouton « Précédent » du navigateur reviennent à la page principale telle que vous l'avez laissée ; l'adresse de la page garde la sélection.
- Sur tablette, l'arbre devient un tiroir « Pièces » sous une largeur d'écran de 980 pixels ; la vue s'adapte à la rotation.
- Aucune modification du démon, ni de ce qui est publié dans Home Assistant.

---

# 2026-10-19 — Page principale : barre de santé compacte, jauge de la maison et cartes de pièce

- Le bandeau bleu disparaît : une ligne d'aide discrète avec un lien « Aide » le remplace.
- La barre de santé tient sur une ligne et porte les actions : « Republier tout », « Relire Jeedom » et un menu « ⋯ » qui range « Télécharger le diagnostic… » et, en rouge, « Supprimer tout de Home Assistant… ».
- Un bloc « publiés sur » le total donne dès le premier écran l'état de la maison, avec une jauge dont chaque segment filtre la liste des équipements, toutes pièces confondues. « Actualiser » relit les chiffres ; ils sont aussi relus après chaque action et au retour sur l'onglet.
- Les cartes de pièce montrent leur propre jauge et leurs repères (bloqués, à appliquer, non lus), l'icône et la couleur choisies dans Jeedom, et sont regroupées par objet parent.
- Aucune modification du démon, ni de ce qui est publié dans Home Assistant.

---

# 2026-10-18 — Un seul état par équipement, mots unifiés et fenêtre de pièce réorganisée

- Chaque équipement porte **un seul état**, dit avec le même mot et la même couleur dans le badge, la ligne de son panneau et les compteurs de la pièce : Publié, À appliquer, Bloqué, Exclu, Désactivé ou Rien à publier (« Désactivé » l'emporte sur « Exclu »). L'ancien état « partiel » devient la mention orange « N bloquées » à côté de « Publié ». Voir la page « Les états et les compteurs ».
- Le réglage de publication est un contrôle à trois positions : **Automatique, Toujours, Jamais** (il remplace « Exclure », « Forcer » et « Revenir au mode automatique »). « Appliquer » n'apparaît que lorsqu'un réglage attend ; « Republier » et « Supprimer de Home Assistant… » passent dans un menu « ⋯ ».
- Le tableau des commandes est regroupé par entité (colonnes : Commande, Dans Home Assistant, Type Jeedom, Type HA). La cause d'un blocage est dite une seule fois, avec un bouton « Ouvrir les types génériques ». Les commandes sans équivalent dans Home Assistant sont repliées sous le tableau et ne comptent plus comme des défauts.
- Un seul équipement est déplié à la fois, son en-tête reste visible, et la fenêtre n'a plus qu'une barre de défilement.
- Les couleurs suivent les thèmes clair et sombre de Jeedom.
- Les mots de l'interface changent : « Bridge » devient « Démon », « Rescanner la topologie Jeedom » devient « Relire Jeedom », « Override HA » devient « Type HA ». Aucune modification du démon, ni de ce qui est publié dans Home Assistant.

---

# 2026-10-18 — Debian 12 seulement

- Le plugin est désormais annoncé pour Debian 12 seulement (Debian 11 est en fin de vie).

---

# 2026-10-18 — Licence AGPL-3.0-or-later

- À partir de la version 1.2.0, le plugin est publié sous AGPL-3.0-or-later. Les versions
  antérieures restent publiées sous leur licence d'origine.

---

# 2026-10-12 — Plus de nom doublé dans Home Assistant

- Quand une entité porte exactement le nom de son appareil (boutons de scénario, équipements à une entité), Home Assistant affichait le nom deux fois (« X X »). Le nom n'est plus doublé et l'assistant vocal retrouve l'entité sous son nom. Seul le nom affiché change : aucun identifiant d'entité n'est modifié.

---

# 2026-10-12 — Compteurs fondés sur la présence dans Home Assistant et actions plus lisibles

- Les compteurs d'une pièce disent maintenant ce qui est **réellement dans Home Assistant** : équipements et commandes publiés, en attente d'application, non pris en charge (les équipements exclus ou désactivés restent comptés à part). Un équipement déplié affiche aussi ses propres compteurs. Voir la page « Les compteurs »
- Les boutons disent leur portée : « Exclure l’équipement » / « Exclure cette entité » (idem pour « Forcer » et « Revenir au mode automatique »). Sur un équipement qui n'a qu'une seule entité, les boutons d'entité qui faisaient la même chose que ceux de l'équipement ne sont plus affichés
- « Supprimer puis recréer » devient « Supprimer de Home Assistant » (équipement, pièce, parc) : l'action supprime seulement, elle ne recrée rien ; la confirmation rappelle que « Republier » remet l'équipement. Le comportement n'a pas changé
- Le sélecteur « Override HA » est désactivé, avec une explication, sur une commande portée par plusieurs entités (le type choisi ne s'appliquerait qu'à l'entité principale de l'équipement)
- La liste « Override HA » ne propose plus que les types qui peuvent aboutir pour la commande : un type que Home Assistant refuserait toujours (même avec « Forcer ») n'est plus proposé, et le sélecteur est grisé, avec une explication, quand aucun type ne reste (la voie normale est alors de préciser les types génériques dans Jeedom)
- Le bandeau de santé est relu aussi quand « Republier » (ou une action de pièce) échoue
- Rien de ce qui est publié dans Home Assistant ne change : mêmes topics, mêmes `unique_id`, mêmes payloads

---

# 2026-10-12 — Noms Jeedom dans Home Assistant et entity_id stable

- Chaque appareil prend le nom de l'équipement Jeedom, identique pour toutes ses entités (avant, un appareil pouvait porter le nom d'une de ses commandes). Un équipement à une seule entité affiche le nom de l'équipement ; pour un équipement à plusieurs entités, l'entité principale (lumière, interrupteur, volet…) porte le nom de l'équipement et s'affiche sous le nom de l'appareil, tandis que les autres entités portent le nom de leur commande, affiché à la suite du nom de l'appareil
- Un renommage dans Jeedom atteint Home Assistant au prochain rescan, redémarrage du démon ou « Republier »
- Les entités nouvelles ou recréées reçoivent un `entity_id` technique stable (`<domaine>.jeedom2ha_…`) : une entité supprimée puis recréée reprend son `entity_id` technique, et les automatisations, scripts et cartes qui le citent survivent à la recréation
- Les `entity_id` déjà présents dans Home Assistant ne changent pas. Les noms affichés des appareils et entités non personnalisés sont mis à jour au prochain rescan ; les noms et pièces que vous avez choisis à la main dans Home Assistant sont conservés

---

# 2026-10-11 — Affichage d'une commande publiée par une entité secondaire

- Une commande d'état portée à la fois par une entité principale refusée et par une entité secondaire déjà publiée (par exemple un capteur binaire) s'affiche désormais « Sera publié : binary_sensor » et est comptée « prête » dans la synthèse de l'équipement et les compteurs de la pièce (auparavant « Ne sera pas publié » et « bloquante » à tort). Correction d'affichage uniquement : rien de ce qui est publié dans Home Assistant ne change
- Cause « état sans ordre On/Off » reformulée pour un équipement dont l'état est la seule commande : rien à piloter ; choisir le type `binary_sensor` puis « Forcer »

---

# 2026-10-11 — Scénario désactivé : son bouton disparaît de Home Assistant

- Un scénario Jeedom désactivé n'a plus de bouton dans Home Assistant : il est retiré au prochain rescan ou redémarrage du démon, et revient avec le même identifiant à la réactivation
- Les boutons de scénarios déjà orphelins (désactivés ou supprimés avant cette version) sont retirés au premier rescan
- Le bouton d'un scénario ne reprend plus la disponibilité ni le type d'un équipement qui porterait le même numéro : il suit uniquement l'état du pont

---

# 2026-10-11 — Nouvelle interface par pièce et documentation réécrite

- Nouvelle page principale : un bandeau de santé (Bridge, MQTT, Dernière synchro, Dernière opération), la zone « Actions Home Assistant » et une carte par pièce (plus une carte « Sans pièce »)
- Configuration par pièce : la fenêtre d'une pièce liste ses équipements, dit pour chacun s'il sera publié dans Home Assistant et, sinon, pourquoi, avec les mots de l'écran
- Tableau des commandes à quatre colonnes (« Commande », « Type Jeedom », « Override HA », « Diagnostic ») : le type Home Assistant d'une commande se choisit directement, avec vérification instantanée
- Nouveaux boutons « Exclure », « Forcer » (avec aperçu avant écriture) et « Revenir au mode automatique », par équipement et par entité Home Assistant ; « Appliquer » pour publier un réglage en attente ; chaque bouton grisé explique pourquoi dans une infobulle
- « Republier » et « Supprimer puis recréer » disponibles pour le parc, une pièce ou un équipement, avec confirmation et mise en garde
- « Rescanner la topologie Jeedom » directement sur la page principale
- Compteurs en haut de la fenêtre d'une pièce
- Retrait de l'ancienne synthèse globale du parc, du bouton « Diagnostic » et de l'onglet de la fiche d'équipement : leur contenu vit désormais dans la configuration par pièce
- Documentation utilisateur réécrite pour décrire cet écran, avec la liste des causes de non-publication
