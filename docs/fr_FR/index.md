# Jeedom2HA — Documentation

**Plugin de pont Jeedom → Home Assistant via MQTT Discovery**

Ce plugin affiche vos équipements Jeedom dans Home Assistant comme des appareils natifs, sans les reconfigurer à la main. Jeedom reste le moteur : c'est lui qui exécute les ordres et qui garde la configuration d'origine.

Cette documentation décrit l'écran du plugin tel que vous le voyez, avec les mots que l'écran emploie.

---

## Table des matières

- [Présentation](#présentation)
- [Prérequis et installation](#prérequis-et-installation)
- [Configuration](#configuration)
- [Première synchronisation](#première-synchronisation)
- [La page principale](#la-page-principale)
- [La configuration par pièce](#la-configuration-par-pièce)
- [Ce que le plugin publie, ce qu'il ne publie pas, et pourquoi](#ce-que-le-plugin-publie-ce-quil-ne-publie-pas-et-pourquoi)
- [Les compteurs de la fenêtre d'une pièce](compteurs.md)
- [Dépannage](#dépannage)
- [Annexes](#annexes)
- [Changelog](changelog.md)

---

## Présentation

jeedom2ha fonctionne comme un pont local. Un petit programme tournant en arrière-plan (le **démon**) lit votre installation Jeedom, décide quels équipements peuvent exister dans Home Assistant, puis les y publie par l'intermédiaire d'un **broker MQTT** (le « facteur » par lequel passent les messages entre Jeedom et Home Assistant). Home Assistant les découvre alors automatiquement : c'est le principe du *MQTT Discovery*.

Quelques repères de vocabulaire, utilisés partout dans cette documentation :

| Mot | Ce que cela désigne |
|---|---|
| **Pièce** | Un objet de votre arborescence Jeedom. Les équipements qui n'ont pas de pièce sont regroupés sous « Sans pièce ». |
| **Équipement** | Un équipement Jeedom (lampe, prise, volet, capteur…). |
| **Commande** | Une commande ou une information d'un équipement Jeedom (allumer, état, température…). |
| **Type Jeedom** | Le type générique que Jeedom attribue à une commande (colonne « Type Jeedom »). C'est lui qui permet au plugin de comprendre à quoi sert la commande. |
| **Entité Home Assistant** | Ce qui apparaît dans Home Assistant. Un équipement Jeedom peut donner une ou plusieurs entités (par exemple une prise et la mesure de sa consommation). |
| **Publier** | Rendre une entité visible et utilisable dans Home Assistant. |
| **Override** | Un réglage manuel que vous posez et que le plugin conserve : le type Home Assistant choisi pour une commande, l'exclusion ou le forçage d'une entité ou d'un équipement. Il remplace le choix automatique du plugin. |

Le plugin ne modifie jamais vos équipements, vos commandes ni vos types Jeedom. Si vous utilisez aussi le plugin Homebridge, rien ne change pour lui : l'écran du plugin le rappelle par le message « Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha. »

---

## Prérequis et installation

**Prérequis**

- Jeedom en version 4.4 ou supérieure.
- Un système Debian 11 ou 12.
- Python 3, que Jeedom gère pour le plugin (si Python 3 est introuvable, Jeedom affiche le message « Python3 introuvable pour le plugin »).
- Un broker MQTT : le plugin **MQTT Manager** (recommandé) ou un broker externe (Mosquitto, par exemple).
- Home Assistant avec l'intégration MQTT en service et la découverte automatique (*discovery*) activée.

**Installation**

1. Installez le plugin depuis le Market Jeedom.
2. Sur la page du plugin, lancez l'installation des dépendances et attendez la fin de l'opération (suivie dans le journal `jeedom2ha`).
3. Saisissez et sauvegardez la connexion au broker (voir [Configuration](#configuration)), puis démarrez le démon ou, s'il a déjà démarré, redémarrez-le : le démon ne lit les réglages MQTT qu'à son démarrage, et il peut démarrer dès la fin de l'installation, avant que vous ayez saisi le broker.

---

## Configuration

Depuis la page du plugin, cliquez sur la vignette **« Configuration »** (bloc « Gestion »).
<!-- CAPTURE-A-PRENDRE: page de configuration -->

### Connexion au broker MQTT

Si MQTT Manager est installé, le plugin le détecte et pré-remplit les champs encore vides : le bandeau affiche alors « MQTT Manager détecté — configuration pré-remplie ». Sans MQTT Manager, le bandeau affiche « Configuration manuelle » quand un hôte est déjà enregistré, et « Aucun broker MQTT détecté. Installez MQTT Manager ou saisissez les paramètres manuellement ci-dessous. » quand rien n'est enregistré.

| Champ | Rôle |
|---|---|
| **Hôte MQTT** | Adresse IP ou nom d'hôte du broker. |
| **Port MQTT** | 1883 par défaut, 8883 pour une connexion chiffrée (TLS). |
| **Utilisateur MQTT** | Identifiant du broker, si une authentification est requise. |
| **Mot de passe MQTT** | Laisser vide pour conserver le mot de passe actuel. Le message « Mot de passe déjà configuré » indique qu'un mot de passe est enregistré. |
| **Activer TLS** | Active le chiffrement de la connexion au broker. |
| **Vérifier le certificat** | Contrôle le certificat du broker. À décocher pour un certificat auto-signé. |

Trois boutons complètent la section :

- **« Tester la connexion »** essaie la connexion avec les valeurs saisies à l'écran, même non sauvegardées. Le démon doit être démarré.
- **« Récupérer depuis MQTT Manager »** réimporte les paramètres de MQTT Manager **et les enregistre aussitôt**, sans attendre « Sauvegarder » (message de réussite : « Configuration importée depuis MQTT Manager »).
- **« Réinitialiser le formulaire »** (lien) vide les champs de connexion à l'écran, sans rien enregistrer.

**Pour que ces réglages soient pris en compte :** cliquez sur le bouton **« Sauvegarder »** de Jeedom (en bas de la fenêtre de configuration), puis **démarrez ou redémarrez le démon** : il ne lit les réglages MQTT qu'à son démarrage. Le bouton « Appliquer les filtres et rescanner » ci-dessous n'enregistre pas la connexion au broker, seulement les trois réglages de filtrage.

### Filtrage et publication

| Champ | Rôle |
|---|---|
| **Plugins exclus** | Noms de plugins séparés par des virgules (exemple affiché : `virtual,zwave,rfxcom`). Les équipements de ces plugins ne sont pas publiés. Vide = aucune exclusion. |
| **Pièces exclues** | **Identifiants numériques** des pièces Jeedom, séparés par des virgules (exemple affiché : `1,5,12`). Seule la pièce indiquée est exclue, pas ses sous-pièces : indiquez aussi leurs identifiants. Pour connaître l'identifiant d'une pièce, ouvrez-la dans Jeedom (Outils → Objets) : le numéro figure dans l'adresse de la page (`id=`). Vide = aucune exclusion. |
| **Politique de publication** | « Publier les équipements sûrs et probables (recommandé) » ou « Publier uniquement les équipements sûrs ». |

« Sûr » veut dire que le type Home Assistant se déduit des types Jeedom sans doute ; « probable », qu'il s'en déduit avec un léger doute. La politique « Publier uniquement les équipements sûrs » ne met de côté que les équipements « probables ».

Le bouton **« Appliquer les filtres et rescanner »** enregistre ces trois réglages puis relance une lecture complète de Jeedom. Il affiche « Sauvegarde en cours... », puis « Rescan en cours... », puis « Appliqué & Rescan terminé » suivi du nombre d'équipements publiés.

Les exclusions de cette page sont **distinctes** de celles que vous posez avec le bouton « Exclure » de la configuration par pièce : voir [Ce que le plugin publie…](#ce-que-le-plugin-publie-ce-quil-ne-publie-pas-et-pourquoi), famille « Exclusions volontaires ».

---

## Première synchronisation

1. Configurez le broker MQTT, cliquez sur « Sauvegarder », puis démarrez ou redémarrez le démon. Vérifiez que le bandeau indique MQTT « Connecté » (vous pouvez aussi utiliser « Tester la connexion »).
2. Ajustez les filtres si nécessaire.
3. Cliquez sur **« Appliquer les filtres et rescanner »** (page de configuration) ou, depuis la page principale du plugin, sur **« Rescanner la topologie Jeedom »**. Les deux lancent une lecture complète de Jeedom ; voir [Rescanner](#rescanner-la-topologie-jeedom).
4. Dans Home Assistant, ouvrez **Paramètres → Appareils et services → MQTT** : vos équipements apparaissent.
5. Si un équipement manque, ouvrez sa pièce dans la page du plugin : l'écran vous dit s'il sera publié et, sinon, pourquoi.

Si, après un redémarrage du broker MQTT, Home Assistant ne retrouve pas ses entités, utilisez **« Republier dans Home Assistant »** sur la page principale.

---

## La page principale

La page du plugin contient, de haut en bas : le bloc « Gestion » (vignette « Configuration »), le bandeau de santé, la zone « Actions Home Assistant », l'export de diagnostic, puis la configuration par pièce.
<!-- CAPTURE-A-PRENDRE: page principale du plugin -->

### Le bandeau de santé

Le bandeau est lu **à l'ouverture de la page**, puis relu après « Republier », « Appliquer » et « Supprimer puis recréer » (à toutes les portées) et après un rescan. Il n'est pas relu après « Exclure », « Forcer » ni « Revenir au mode automatique », et il ne se rafraîchit pas tout seul : rechargez la page pour l'actualiser. Il comporte quatre indicateurs.

| Indicateur | Valeurs possibles |
|---|---|
| **Bridge** (le démon) | « Actif » (vert) ; « Arrêté » (rouge : le démon ne répond pas) ; « Erreur Jeedom » ou « Erreur de communication » (rouge). |
| **MQTT** (la liaison avec le broker) | « Connecté » (vert) ; « Reconnexion... » ou « Connexion... » (orange) ; « Déconnecté » (rouge) ; « Non configuré » ; « Inconnu » (démon arrêté ou erreur). L'adresse du broker s'affiche à côté. |
| **Dernière synchro** | La date et l'heure (jour/mois et heures:minutes:secondes) de la dernière lecture complète, « Jamais » si aucune n'a eu lieu, « Inconnue » si le démon est arrêté. |
| **Dernière opération** | « Succès » (vert) ; « Partiel » ou « Échec » (orange : c'est un problème de configuration, pas une panne d'infrastructure) ; « Aucune » ; « Inconnue » si le démon est arrêté. Le message de l'opération s'affiche à côté. |

### La zone « Actions Home Assistant »

Trois boutons agissent sur **l'ensemble du parc** :

| Bouton | Ce qu'il fait |
|---|---|
| **« Republier dans Home Assistant »** | Après confirmation (« Republier tous les équipements inclus ? »), republie dans Home Assistant les équipements inclus et applique leurs réglages en attente. Les équipements « inclus » sont ceux que le plugin ne met pas d'office de côté (par exemple par une exclusion de la configuration ou parce qu'ils sont désactivés). « Republier » travaille sur ce que le dernier rescan a lu : il ne relit pas Jeedom. |
| **« Rescanner la topologie Jeedom »** | Relit tout Jeedom. Voir [Rescanner](#rescanner-la-topologie-jeedom). |
| **« Supprimer puis recréer dans Home Assistant »** | Retire de Home Assistant tout le parc publié, après une confirmation forte. Voir [Les actions de publication](#les-actions-de-publication). |

**Quand certains boutons sont grisés.** Les trois boutons ci-dessus, ainsi que « Republier la pièce », « Supprimer puis recréer la pièce » et, pour chaque équipement, « Appliquer » / « Republier » et « Supprimer puis recréer », ne sont utilisables que si le démon tourne **et** que MQTT est connecté. Sinon, ils sont grisés et une ligne d'explication s'affiche :

- « Daemon arrêté — actions Home Assistant bloquées. » (le démon est arrêté ; le mot « Daemon » est celui de l'écran) ;
- « MQTT déconnecté — actions Home Assistant bloquées. » ;
- « Bridge ou MQTT indisponible — actions Home Assistant bloquées. » (état impossible à lire).

Pendant un rescan, ces mêmes boutons sont aussi grisés. Les boutons « Exclure », « Forcer » et « Revenir au mode automatique » et la liste « Override HA » ne sont **pas** concernés : ils restent actifs, mais si le démon ne répond pas, leur action échoue avec un message d'erreur.

### Rescanner la topologie Jeedom

« Rescanner la topologie Jeedom » ouvre d'abord une confirmation : « Un sync complet peut publier ou retirer des entités Home Assistant et applique les overrides persistés. Confirmer ? » (bouton « Rescanner » ; « overrides persistés » désigne vos réglages manuels enregistrés).

- **Ce qu'il fait** : relit tous les équipements de Jeedom, publie ou retire des entités Home Assistant en conséquence, et **applique d'un coup tous les réglages en attente** (les « overrides » : types Home Assistant choisis, exclusions, forçages) de tous les équipements.
- **Ce qu'il ne fait pas** : il ne modifie rien dans Jeedom.
- **Pendant l'opération** : le bouton affiche « Rescan en cours… » et les autres boutons d'action sont grisés.
- **Résultat** : un message « Synchronisation terminée. » (vert), « Synchronisation terminée avec avertissements. » (orange) ou « Synchronisation échouée. » (rouge) — remplacé par le message précis du démon quand il en fournit un. « Une opération est déjà en cours ou le rescan a échoué. » n'est qu'un message de repli : le démon renvoie le plus souvent son propre message, affiché à la place ; « Erreur de communication : relire Dernière synchro avant de relancer. » indique que la réponse n'est pas arrivée. Le bandeau de santé est ensuite relu.

### Télécharger le diagnostic support

Sous la zone d'actions, le bouton **« Télécharger le diagnostic support »** produit un fichier `jeedom2ha-diagnostic-AAAA-MM-JJ.json` à joindre à une demande d'aide.

- La case **« Pseudonymiser les noms d'équipements »** remplace les noms d'équipements par « Équipement_N », les noms de pièces par « Pièce_M » et les noms de commandes par « Cmd_ » suivi de leur numéro, et masque l'adresse du broker.
- Messages : « Export en cours... », puis « Diagnostic téléchargé » ; en cas de problème, « Erreur export » ou « Erreur de communication », ou le message du démon (par exemple « Démon indisponible ou timeout — relancez le démon et réessayez. »).

Ce fichier est un outil d'assistance. Pour comprendre l'état d'un équipement, utilisez la configuration par pièce.

---

## La configuration par pièce

Sous l'export de diagnostic, la section **« Configuration Home Assistant par pièce »** rappelle : « Choisissez une pièce pour voir ses équipements et, pour chaque commande, si elle répond aux prérequis Home Assistant (prêt / bloquant + pourquoi). Le type natif Jeedom (partagé Homebridge) n'est jamais modifié. »

### Les cartes de pièce

Chaque pièce qui contient au moins un équipement a une carte portant son nom et, entre parenthèses, son nombre d'équipements. La carte **« Sans pièce »** rassemble les équipements qui n'ont pas de pièce. Les équipements **désactivés dans Jeedom sont comptés et listés**. Les équipements du plugin jeedom2ha lui-même sont écartés. S'il n'y a aucune pièce avec équipement, la page affiche « Aucune pièce avec équipement trouvée. »
<!-- CAPTURE-A-PRENDRE: cartes de pièce -->

### La fenêtre d'une pièce

Cliquer sur une carte ouvre une fenêtre qui porte le nom de la pièce. Elle contient :

1. **Les compteurs** de la pièce : voir [Les compteurs](compteurs.md).
2. **Les actions de la pièce** : « Republier la pièce » et « Supprimer puis recréer la pièce ». Pour « Sans pièce », elles n'existent pas : la fenêtre indique « Republication et suppression de pièce indisponibles pour les équipements sans pièce : utilisez les actions de chaque équipement. »
3. **Une zone de résultat**, où s'affiche le message de la dernière action (vert : succès ; orange : succès partiel ; rouge : échec).
4. **La liste des équipements de la pièce**, un panneau par équipement. Chaque panneau montre le nom de l'équipement, la mention « (désactivé dans Jeedom) » le cas échéant, et un **badge de synthèse** qui dit si l'équipement sera publié (voir [Les badges de synthèse](#les-badges-de-synthèse)).

À l'ouverture, le plugin lit **uniquement les équipements de cette pièce**, ce qui prend quelques instants (« Chargement… » s'affiche dans chaque panneau). Si la lecture d'un équipement échoue, son panneau indique « Impossible de lire la configuration de cet équipement. » ou « Impossible de charger la configuration HA (daemon indisponible). » et n'offre aucune action.
<!-- CAPTURE-A-PRENDRE: fenêtre d'une pièce -->

### Le panneau d'un équipement

Dépliez un équipement pour voir, de haut en bas :

- **Le badge « Override en attente — pas encore republié vers Home Assistant »**, quand la décision de publier ou non l'équipement a changé depuis la dernière publication (voir [Réglages en attente](#réglages-en-attente-et-appliquer)).
- **Le lien « Voir la première commande bloquante »**, s'il y a une commande bloquante : il fait défiler la liste jusqu'à elle et la met en évidence quelques secondes.
- **Les boutons de l'équipement** : « Exclure », « Forcer », « Revenir au mode automatique », puis « Appliquer » ou « Republier », puis « Supprimer puis recréer ».
- **Les entités Home Assistant** de l'équipement : une ligne par entité, avec son type (« light », « switch »…, ou « Entité HA » si le type est inconnu), la mention « Commandes : … » (ou « Aucune commande regroupée »), éventuellement le badge **« pas encore appliqué »**, et ses propres boutons « Exclure », « Forcer » et « Revenir au mode automatique ».
- **Le tableau des commandes**.

Un équipement sans commande affiche « Aucune commande à configurer pour cet équipement. »

### Le tableau des commandes

Le tableau a **quatre colonnes**, une ligne par commande, dans l'ordre de Jeedom :

| Colonne | Contenu |
|---|---|
| **Commande** | Le nom de la commande. |
| **Type Jeedom** | Le type générique de la commande dans Jeedom. Lecture seule : il n'est jamais modifié. |
| **Override HA** | Une liste pour choisir le type Home Assistant de cette commande : « — mode automatique — », `alarm_control_panel`, `binary_sensor`, `button`, `climate`, `cover`, `light`, `sensor`, `switch`. |
| **Diagnostic** | Ce qui sera publié (« Sera publié : <type> ») ou non (« Ne sera pas publié — <cause> »). Voir [les causes](#les-causes-affichées-dans-la-colonne-diagnostic). |

Les commandes **non couvertes** (qu'aucun type Home Assistant ne prend en charge) restent visibles, sans jamais être comptées comme bloquantes : leur cellule affiche une icône d'interdiction et la mention « Ne sera pas publié — commande sans type Home Assistant applicable ».
<!-- CAPTURE-A-PRENDRE: tableau des commandes -->

### Choisir le type Home Assistant d'une commande

Par défaut le plugin choisit seul le type Home Assistant d'une commande (« — mode automatique — »). Vous pouvez en imposer un autre dans la colonne « Override HA » :

1. Choisissez un type dans la liste. Après une courte attente (environ 0,4 seconde), le plugin **vérifie** le choix et affiche le résultat dans la colonne « Diagnostic ».
2. Si le choix est valide (« Sera publié : <type> »), il est **enregistré automatiquement** : il n'y a pas de bouton « Enregistrer ».
3. Sinon, il est **refusé** et la colonne « Diagnostic » en donne la raison ; rien n'est enregistré. Rouvrez la pièce pour retrouver l'état réellement enregistré.
4. Un choix enregistré **n'est pas publié tout de suite**. Le signe fiable est le badge « pas encore appliqué » sur l'entité concernée, et le bouton « Republier » de l'équipement qui devient « Appliquer ». Cliquez sur « Appliquer » ou lancez un rescan.
5. Pour annuler le choix d'une commande, sélectionnez « — mode automatique — » dans la liste, ou cliquez sur l'icône « Revenir au type automatique » à côté de la liste. Cette icône ne retire que le choix de **type** de cette commande.

La liste est **grisée avec une infobulle** quand elle n'a pas de sens :

- « Commande exclue de Jeedom2HA : son type HA ne peut pas être réglé ici. »
- « Équipement désactivé dans Jeedom : son type HA ne peut pas être réglé ici. »
- « Aucun type Home Assistant ne couvre cette commande : son type HA ne peut pas être réglé ici. »

Quand une vérification fait apparaître une commande bloquante, un bandeau d'avertissement rappelle, une fois par ouverture de pièce : « Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha. »

### Deux familles de réglages : type et publication

Le plugin distingue deux sortes de réglages manuels :

| | Réglage de **type** | Réglage de **publication** |
|---|---|---|
| **Ce que c'est** | Le type Home Assistant d'une commande (liste « Override HA »). | « Exclure » ou « Forcer » une entité ou un équipement. |
| **Où** | Tableau des commandes. | Boutons de l'équipement et de chaque entité. |
| **Enregistrement** | Automatique si le choix est valide. | Au clic (avec confirmation dans certains cas). |
| **Annulation** | « — mode automatique — » ou l'icône « Revenir au type automatique » (cette commande seulement). | « Revenir au mode automatique » (voir plus bas ce qu'il retire selon la portée). |

Dans les deux cas, le réglage n'est visible dans Home Assistant qu'après avoir été appliqué.

### Réglages en attente et Appliquer

Un réglage enregistré n'est pas publié immédiatement. Tant qu'il attend, l'écran le signale :

- sur l'entité concernée : le badge **« pas encore appliqué »** (c'est le signe le plus fiable) ;
- sur l'équipement : le bouton « Republier » devient **« Appliquer »** (orange) ;
- sur l'équipement : le badge **« Override en attente — pas encore republié vers Home Assistant »**, seulement quand le réglage change la décision de publier ou non l'équipement.

Pour l'appliquer à **un équipement**, cliquez sur son bouton **« Appliquer »**. « Republier la pièce » et « Republier dans Home Assistant » appliquent aussi les réglages en attente des équipements concernés. Un [rescan](#rescanner-la-topologie-jeedom) applique d'un coup ceux de **tous** les équipements. « Appliquer » ne demande pas de confirmation ; son résultat s'affiche dans la zone de résultat de la pièce.

### Les actions de publication

Chaque bouton ci-dessous existe à la portée de l'**équipement** et, pour les trois premiers, de chaque **entité** Home Assistant.

**Exclure**

- *Ce que ça fait* : l'équipement n'est plus publié dans Home Assistant, ou l'entité n'y est plus publiée.
- *Confirmation* : seulement si l'exclusion fait **quitter Home Assistant** une entité publiée selon le diagnostic. La fenêtre demande « Exclure cet équipement de Home Assistant ? » (avec la liste « Entités qui quitteront Home Assistant : … ») ou « Exclure cette entité de Home Assistant ? ». Boutons « Annuler » et « Confirmer ». Sinon l'exclusion est enregistrée directement.
- *Ensuite* : comme tout réglage, l'exclusion attend d'être appliquée (« Appliquer », « Republier » ou rescan).

**Forcer**

- *Ce que ça fait* : demande au plugin de publier une entité qu'il aurait refusé de publier.
- *Confirmation* : toujours précédée d'un **aperçu** calculé par le démon, avant toute écriture. Il indique « Type HA : … », « Projection valide pour ce type. » ou « Projection invalide pour ce type. » (la « projection » est la transformation de l'équipement Jeedom en entité Home Assistant de ce type), « Commandes qui recevront les ordres : … » et « Cette entité sera publiée dans Home Assistant. ». À la portée équipement, l'aperçu liste « Entités concernées par ce forçage : … » et conclut « Au moins une entité sera publiée dans Home Assistant. ».
- *Si le forçage serait refusé* : l'aperçu affiche « Le forçage serait refusé : <raison> » et le bouton « Confirmer » est grisé. Si le démon ne répond pas : « Aperçu indisponible — le démon ne répond pas. »

**Revenir au mode automatique**

- *Équipement* : retire **les deux sortes** de réglages de l'équipement (types choisis pour ses commandes, exclusion ou forçage).
- *Entité* : retire l'exclusion ou le forçage de l'entité **et** les types Home Assistant choisis pour ses commandes.
- Pas de confirmation.

**Republier / Appliquer**

- *Équipement* : un seul bouton. Il s'appelle « Appliquer » (orange) s'il y a un réglage en attente, « Republier » sinon. Sans confirmation.
- *Pièce* : « Republier la pièce » demande « <nom de la pièce> — republier les équipements inclus de cette pièce. Confirmer ? » (bouton « Republier »). Elle applique aussi les réglages en attente de la pièce.
- *Dans tous les cas*, « Republier » ne relit pas Jeedom : il travaille sur ce que le dernier rescan a lu.
- *Parc* : voir [la page principale](#la-zone--actions-home-assistant-).

**Supprimer puis recréer**

- *Ce que ça fait* : retire de Home Assistant les entités **publiées** de l'équipement, de la pièce ou du parc.
- *Ce que ça ne fait pas* : cette action **supprime seulement** ; elle ne republie pas. Pour recréer les entités, utilisez ensuite « Republier » à la même portée, ou lancez un rescan.
- *Confirmation forte* (bouton rouge), intitulée « Supprimer puis recréer dans Home Assistant ». Son texte annonce ce qui sera supprimé : « Supprimer "<nom>" de Home Assistant. » (équipement), « … de Home Assistant : tous les équipements publiés de cette pièce. » (pièce) ou « Supprimer puis recréer tout le parc publié ? » (parc).
- *Mise en garde* : **« Attention : l'historique, les dashboards, les automatisations et l'entity_id liés à ces entités peuvent être impactés. »** (l'`entity_id` est l'identifiant de l'entité dans Home Assistant).
- *Boutons* : « Supprimer 1 équipement », « Supprimer la pièce » ou « Supprimer ».
- *Résultat* : un message tel que « N équipement(s) supprimé(s) de Home Assistant. » ou « Configuration déjà à jour dans Home Assistant. ».

**Pendant une action**, le bouton affiche « Confirmation en cours… », puis « En cours... » (publication) ou « Suppression... ». Le message de résultat est précédé du nom de la portée (par exemple « Parc global — … »). Messages d'erreur possibles : « Le démon ne répond pas. », « Erreur de communication avec le backend Home Assistant. », « Réponse backend incomplète pour l'action Home Assistant. ». Les délais d'attente sont décrits en [annexe](#annexe--durée-des-actions).

#### Quand un bouton est grisé

Un bouton grisé affiche **son propre motif** dans une infobulle (survolez-le). Les motifs possibles :

| Bouton | Motifs affichés |
|---|---|
| Republier, Appliquer, Supprimer puis recréer (toutes portées) et Rescanner | Voir [la zone « Actions Home Assistant »](#la-zone--actions-home-assistant-) (démon arrêté, MQTT déconnecté, rescan en cours). « Exclure », « Forcer » et « Revenir au mode automatique » ne sont pas concernés. |
| Exclure | « Entité déjà exclue de Home Assistant. » ; « Aucune commande clé propre à cette entité. » ; « Équipement non éligible : l’action serait sans effet. » |
| Forcer | « Publication déjà forcée sur cette entité. » ; « Déjà publiée : forcer n’a pas d’effet. » ; « Aucun type Home Assistant identifié pour cette entité. » ; « Type HA hors périmètre de ce plugin. » ; « Projection invalide pour ce type HA. » ; « Exclusion posée sur l’équipement : la retirer depuis l’équipement. » ; « Aucune commande clé propre à cette entité. » ; « Équipement non éligible : l’action serait sans effet. » |
| Revenir au mode automatique | « Aucun override de publication à retirer. » ; « Exclusion posée sur l’équipement : la retirer depuis l’équipement. » ; « Aucune commande clé propre à cette entité. » |
| Republier / Appliquer (équipement) | « Équipement désactivé dans Jeedom : rien à republier. » ; « Équipement exclu : rien à republier. » (sauf si un réglage est en attente) |
| Supprimer puis recréer (équipement) | « Équipement non publié dans Home Assistant : rien à supprimer. » Ce grisé reflète la présence **réelle** dans Home Assistant, pas le badge de synthèse : un équipement peut afficher « Sera publié… » et avoir ce bouton grisé tant qu'il n'a pas été publié. |
| Republier la pièce | « Aucun équipement à publier dans cette pièce. » |
| Supprimer puis recréer la pièce | « Aucun équipement publié dans cette pièce. » (même logique : présence réelle dans Home Assistant) |

Un bouton grisé sans motif particulier affiche « Cette action est sans effet dans l’état courant. »

Deux expressions de ces motifs méritent une explication. Une **« commande clé »** est une commande qui n'appartient qu'à une seule entité et qui sert à la désigner ; si toutes les commandes d'une entité sont partagées avec une autre entité, « Exclure », « Forcer » et « Revenir au mode automatique » sont grisés pour elle. La **projection** est la transformation de l'équipement en entité Home Assistant d'un type donné ; elle est « invalide » quand il manque ce dont ce type a besoin.

---

## Ce que le plugin publie, ce qu'il ne publie pas, et pourquoi

### Ce que le plugin sait publier

Le plugin publie huit types d'entités Home Assistant. Le type est choisi à partir des types Jeedom des commandes de l'équipement.

| Type Home Assistant | Ce que le plugin en fait |
|---|---|
| `light` | Lumières : allumer/éteindre et variation de luminosité. La couleur n'est pas reprise, et une lumière qui n'a que des commandes de couleur n'est pas prise en charge. |
| `cover` | Volets et stores : ouverture/fermeture, arrêt et position quand ils existent. |
| `switch` | Prises et interrupteurs (commandes d'énergie On/Off, familles « interrupteur » et « ventilateur » de Jeedom), ainsi que les équipements de présence actionnables (information de présence + actions pour l'activer et la désactiver). |
| `sensor` | Informations numériques. |
| `binary_sensor` | Informations binaires. |
| `button` | Actions ponctuelles sans valeur, et **scénarios Jeedom actifs** (un bouton par scénario actif). |
| `climate` | Thermostats, pour la consigne et la température. |
| `alarm_control_panel` | Alarmes : état armé/désarmé et commandes pour armer et désarmer. |

Le plugin ne publie pas les équipements sans type Jeedom reconnu : il l'indique alors dans la colonne « Diagnostic ».

### Les badges de synthèse

Le badge à droite du nom de chaque équipement résume sa situation :

| Situation | Libellé affiché |
|---|---|
| Toutes les commandes utiles sont prêtes | « Sera publié dans Home Assistant : N commande(s) prête(s). » |
| Certaines prêtes, d'autres bloquantes | « Partiellement publié : N prête(s), M bloquante(s). » |
| Aucune prête, au moins une bloquante | « Ne sera pas publié dans Home Assistant : M commande(s) bloquante(s). » |
| Équipement exclu | « Exclu : ne sera pas publié dans Home Assistant. » |
| Équipement désactivé dans Jeedom | « Désactivé dans Jeedom : ne sera pas publié dans Home Assistant. » |
| Aucune commande utilisable | « Aucune commande projetable en Home Assistant pour cet équipement. » (« projetable » : qui peut être transformée en entité Home Assistant) |

Vocabulaire :

- Une commande **prête** peut être publiée : « Sera publié : <type> ».
- Une commande **bloquante** devrait pouvoir être publiée mais ne le sera pas. Certaines causes se corrigent (voir les familles ci-dessous), d'autres non.
- Une commande **non couverte** n'est prise en charge par aucun type Home Assistant : elle n'est ni prête ni bloquante, et il n'y a aucune correction à faire.
- Une **entité Home Assistant** est ce qui apparaît dans Home Assistant ; un équipement peut en produire plusieurs.
- Un équipement **exclu** est volontairement écarté : par vous (« Exclure »), par la configuration du plugin (plugins, pièces) ou par un réglage d'exclusion propre à l'équipement dans Jeedom.

Un badge « Sera publié… » ou « Partiellement publié… » dit ce que le plugin **va** publier d'après son diagnostic ; ce n'est pas la présence réelle dans Home Assistant, qui dépend de l'application des réglages (voir [Réglages en attente](#réglages-en-attente-et-appliquer)).

### Les causes affichées dans la colonne Diagnostic

Quand une commande ne sera pas publiée, la cellule affiche « Ne sera pas publié — » suivi de la cause. Les causes sont regroupées ici par ce que vous pouvez en faire.

**1. Corrections possibles côté Jeedom (types génériques ou nom de l'équipement)**

| Cause affichée | Pour agir |
|---|---|
| type Home Assistant ambigu — précisez les types génériques dans Jeedom | Précisez les types génériques des commandes dans Jeedom. |
| types génériques en conflit — précisez-les dans Jeedom | Idem. |
| types génériques en double | Deux commandes portent le même type : retirez le doublon. |
| un mot du nom de l’équipement écarte ce type | Renommez l'équipement (voir [Nommage des équipements](#annexe--nommage-des-équipements)). |
| état sans ordre On/Off — rien à piloter ; choisissez le type binary_sensor dans « Override HA », puis « Forcer » | L'équipement n'a qu'une commande d'état, sans commandes On/Off : il n'y a rien à piloter. Dans la liste « Override HA » de cette commande, choisissez `binary_sensor`, puis cliquez sur « Forcer ». |

**2. Rien à publier, tel que l'équipement est configuré**

| Cause affichée | Signification |
|---|---|
| types génériques non configurés dans Jeedom | Aucune commande n'a de type Jeedom. |
| type non couvert par la V1 du plugin | Aucun des types Jeedom de l'équipement n'est reconnu par le plugin (« V1 » désigne la version actuelle du plugin ; la liste des types pris en charge est donnée plus haut). |
| aucune commande Info/Action exploitable | L'équipement n'a pas de commande utilisable. |
| aucune commande configurée dans Jeedom | L'équipement n'a aucune commande. |

**3. Publication impossible : il manque une capacité**

| Cause affichée | Signification |
|---|---|
| commande non pilotable (pas d’ordre On/Off) | Home Assistant ne pourrait pas envoyer d'ordre. |
| pas de retour d’état exploitable | Home Assistant ne pourrait pas lire l'état. |

**4. Réglage de la politique de publication**

| Cause affichée | Pour agir |
|---|---|
| confiance « probable » exclue par la politique « sûr uniquement » | Passez la politique à « Publier les équipements sûrs et probables (recommandé) » dans la configuration. |
| confiance insuffisante pour la politique active | Idem. |

**5. Type non publiable**

Ces causes s'affichent avec un triangle d'avertissement, comptent comme **bloquantes** et sont la cible du lien « Voir la première commande bloquante ».

| Cause affichée | Pour agir |
|---|---|
| aucun type Home Assistant identifié pour cette commande | Choisissez un autre type dans la colonne « Override HA », ou revenez au mode automatique. |
| aucun type Home Assistant candidat à valider | Idem. |
| type HA non ouvert par ce plugin | Idem : le type demandé n'est pas pris en charge par le plugin. |

**6. Commande non couverte**

| Cause affichée | Signification |
|---|---|
| commande sans type Home Assistant applicable | Aucun type Home Assistant ne prend cette commande en charge : rien à faire. Elle s'affiche avec une icône d'interdiction et n'est jamais comptée comme bloquante. |

**7. Exclusions volontaires** (jamais comptées comme des problèmes)

| Cause affichée | Origine |
|---|---|
| exclu manuellement (équipement) | Bouton « Exclure » de l'équipement. |
| exclu manuellement (commande) | Bouton « Exclure » d'une entité. |
| exclu de Jeedom2HA (équipement dans la liste d’exclusions) | Réglage d'exclusion propre à l'équipement dans Jeedom (la clé `jeedom2ha_excluded` de sa configuration). Aucun bouton du plugin ne le pose. |
| exclu de Jeedom2HA (plugin source dans la liste d’exclusions) | Champ « Plugins exclus ». |
| exclu de Jeedom2HA (pièce dans la liste d’exclusions) | Champ « Pièces exclues ». |

Pour reprendre un équipement exclu manuellement, utilisez « Revenir au mode automatique ». Pour une exclusion venant de la configuration du plugin (champs « Plugins exclus » et « Pièces exclues »), modifiez la configuration puis cliquez sur « Appliquer les filtres et rescanner ». Pour le réglage propre à l'équipement, retirez-le sur l'équipement dans Jeedom, puis lancez « Rescanner la topologie Jeedom ».

**8. État neutre**

| Cause affichée | Signification |
|---|---|
| équipement désactivé dans Jeedom | Réactivez l'équipement dans Jeedom si vous le souhaitez. |

**9. Incident à relire dans les journaux**

| Cause affichée | Signification |
|---|---|
| échec de publication MQTT au dernier sync | La publication vers le broker a échoué lors de la dernière synchronisation. Relancez une republication ; si le message persiste, consultez les journaux. |

Si une cellule affiche un texte technique ou une liste de codes à la place d'une de ces phrases, téléchargez le diagnostic support et joignez-le à votre demande d'aide.

---

## Dépannage

| Symptôme | Où regarder | Action |
|---|---|---|
| Le démon ne démarre pas | Bandeau, indicateur « Bridge » : « Arrêté » | Relancez l'installation des dépendances, puis démarrez le démon. Consultez le journal `jeedom2ha`. |
| Le broker n'est pas joignable | Indicateur « MQTT » : « Déconnecté » | Vérifiez les paramètres et utilisez « Tester la connexion » dans la configuration. |
| Les boutons d'action sont grisés | Ligne d'explication sous la zone « Actions Home Assistant » | Corrigez le démon ou MQTT : voir [la page principale](#la-zone--actions-home-assistant-). |
| Un équipement manque dans Home Assistant | Ouvrez sa pièce : badge de l'équipement et colonne « Diagnostic » | Appliquez la correction de la [famille de causes](#les-causes-affichées-dans-la-colonne-diagnostic) correspondante. |
| Un réglage n'a pas d'effet dans Home Assistant | Badge « pas encore appliqué » sur l'entité, ou bouton « Appliquer » à la place de « Republier » | Cliquez sur « Appliquer », ou lancez « Rescanner la topologie Jeedom ». |
| Les états ne se mettent pas à jour | Bandeau de santé | Vérifiez le démon et MQTT, puis le journal `jeedom2ha`. |
| Le bandeau semble figé | Il n'est lu qu'à l'ouverture de la page | Rechargez la page. |

Journaux : **Jeedom → Analyse → Logs → `jeedom2ha`**. Pour signaler un problème : [github.com/alexsahut/jeedom2ha/issues](https://github.com/alexsahut/jeedom2ha/issues).

---

## Annexes

### Annexe : pièces dans Home Assistant (zone suggérée)

Le plugin transmet à Home Assistant la **pièce Jeedom** de chaque équipement, comme « zone suggérée » (`suggested_area`). Si vous renommez la pièce dans Jeedom, le plugin met à jour cette information au prochain rescan.

Home Assistant n'utilise cette zone suggérée **qu'à la création** de l'appareil. Si vous déplacez ensuite un équipement d'une pièce à l'autre dans Jeedom, l'appareil reste dans son ancienne zone dans Home Assistant.

Pour le déplacer :

- **Option 1 — Supprimer puis recréer.** Utilisez « Supprimer puis recréer » sur l'équipement, la pièce ou le parc, puis « Rescanner la topologie Jeedom » : le rescan relit la pièce actuelle et recrée les entités. (« Republier » seul ne suffit pas : il travaille sur ce que le dernier rescan a lu et ne relit pas Jeedom ; si vous venez de déplacer l'équipement, rescannez d'abord.) Les personnalisations faites dans Home Assistant (icônes, alias, historique, automatisations) peuvent être perdues : lisez l'avertissement de la confirmation.
- **Option 2 — Déplacement manuel.** Dans Home Assistant : **Paramètres → Appareils et services**, trouvez l'appareil et modifiez sa zone.

### Annexe : nommage des équipements

Pour les **lumières**, les **volets** et les **prises/interrupteurs**, le plugin lit aussi le **nom de l'équipement**. Si le nom contient l'un des mots ci-dessous, l'équipement est écarté pour ce type, avec la cause « un mot du nom de l’équipement écarte ce type ».

Le mot doit apparaître **en entier** dans le nom (la casse n'a pas d'importance) : « Lampe tableau » n'est pas écarté à cause du « eau » de « tableau », mais « Lampe prise 2 » l'est à cause de « prise ».

| Pour le type | Mots qui l'écartent |
|---|---|
| **Lumière** (`light`) | chauffage, radiateur, thermostat, heater, chaudiere, chaudière, poele, poêle ; chauffe-eau, eau, water, cumulus, ballon ; piscine, pool, filtration, filtre, pompe ; prise, plug, socket ; fumée, smoke, incendie, feu, fire, alarme, sirene, sirène ; volet, store, cover, blind, shutter, garage, portail |
| **Prise / interrupteur** (`switch`) | lumière, lumiere, light, lampe, ampoule ; volet, store, cover, blind, shutter, portail, garage ; chauffage, radiateur, thermostat, heater ; fumée, smoke, alarme, sirene |
| **Volet** (`cover`) | lumière, lumiere, light, lampe, ampoule ; chauffage, radiateur, thermostat, heater ; prise, plug, socket ; fumée, smoke, alarme, sirene |

Que faire : renommez l'équipement dans Jeedom puis lancez un rescan, ou essayez le bouton « Forcer » (voir ses conditions plus haut).

### Annexe : durée des actions

Les actions « Republier » et « Supprimer puis recréer » peuvent demander du temps sur un grand parc. Le démon ne s'arrête jamais en cours de route : c'est l'écran qui cesse d'attendre.

- Si l'action dépasse environ 60 secondes, le message suivant s'affiche : « L'action Home Assistant dure plus longtemps que prévu (plus de 60 s). Elle peut se poursuivre côté démon : actualisez la page dans un instant pour voir le résultat. » Attendez quelques secondes, rechargez la page : le bandeau et la pièce reflètent alors le résultat réel.
- Si le démon répond par une erreur immédiate : « Le démon a renvoyé une erreur pendant l'action Home Assistant — consultez les logs du plugin ». Consultez alors le journal `jeedom2ha`.
- Si le démon ne répond pas du tout : « Le démon ne répond pas (timeout API) — vérifiez qu'il est bien démarré ».
- Si une autre action est déjà en cours : « Une action Home Assistant est déjà en cours. » Attendez qu'elle se termine, rechargez la page, puis relancez.

### Annexe : historique des versions

Voir le [changelog](changelog.md).
