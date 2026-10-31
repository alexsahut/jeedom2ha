# Jeedom2HA — Documentation

**Plugin de pont Jeedom → Home Assistant via MQTT Discovery**

Ce plugin affiche vos équipements Jeedom dans Home Assistant comme des appareils natifs, sans les reconfigurer à la main. Jeedom reste le moteur : c'est lui qui exécute les ordres et qui garde la configuration d'origine.

Cette documentation décrit l'écran du plugin tel que vous le voyez, avec les mots que l'écran emploie.

---

## Table des matières

- [Présentation](#présentation)
- [Prérequis et installation](#prérequis-et-installation)
- [Installer depuis GitHub (beta)](installation-github.md)
- [Configuration](#configuration)
- [Première synchronisation](#première-synchronisation)
- [La page principale](#la-page-principale)
- [La configuration par pièce](#la-configuration-par-pièce)
- [Ce que le plugin publie, ce qu'il ne publie pas, et pourquoi](#ce-que-le-plugin-publie-ce-quil-ne-publie-pas-et-pourquoi)
- [Les états et les compteurs de la vue de travail](compteurs.md)
- [Dépannage](#dépannage)
- [Annexes](#annexes)
  - [Noms et identifiants dans Home Assistant](#annexe--noms-et-identifiants-dans-home-assistant)
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
| **Réglage** | Un choix manuel que vous posez et que le plugin conserve : le « Type HA » d'une commande, ou la publication d'un équipement ou d'une entité (« Automatique », « Toujours » ou « Jamais »). Il remplace le choix automatique du plugin. |
| **État** | Ce que dit le badge d'un équipement : Publié, À appliquer, Bloqué, Exclu, Désactivé ou Rien à publier. Un équipement n'a toujours qu'un seul état (voir [Les états et les compteurs](compteurs.md)). |
| **Démon** | Le programme du plugin qui tourne en arrière-plan. Son indicateur se lit dans la barre de santé de la page principale. |

Le plugin ne modifie jamais vos équipements, vos commandes ni vos types Jeedom. Si vous utilisez aussi le plugin Homebridge, rien ne change pour lui : l'écran du plugin le rappelle par le message « Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha. »

---

## Prérequis et installation

**Prérequis**

- Jeedom en version 4.5 ou supérieure.
- Un système Debian 12.
- Python 3, que Jeedom gère pour le plugin (si Python 3 est introuvable, Jeedom affiche le message « Python3 introuvable pour le plugin »).
- Un broker MQTT : le plugin **MQTT Manager** (recommandé) ou un broker externe (Mosquitto, par exemple).
- Home Assistant avec l'intégration MQTT en service et la découverte automatique (*discovery*) activée.

**Installation**

1. Installez le plugin depuis le Market Jeedom. Pour une installation hors Market à partir d'une archive GitHub, suivez plutôt [Installer depuis GitHub (beta)](installation-github.md).
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

**Pour que ces réglages soient pris en compte :** cliquez sur le bouton **« Sauvegarder »** de Jeedom (en bas de l'écran de configuration), puis **démarrez ou redémarrez le démon** : il ne lit les réglages MQTT qu'à son démarrage. Le bouton situé sous les réglages de filtrage, plus bas, n'enregistre pas la connexion au broker, seulement ces réglages de filtrage.

### Filtrage et publication

| Champ | Rôle |
|---|---|
| **Plugins exclus** | Une **liste à cocher** des plugins qui ont au moins un équipement dans Jeedom (le plugin jeedom2ha lui-même n'y figure pas). Chaque case porte le nom du plugin affiché par Jeedom, suivi de son identifiant technique en gris. Cochez les plugins dont les équipements ne doivent pas être publiés dans Home Assistant. Un plugin exclu mais **absent de Jeedom** (désinstallé) reste affiché, coché, avec la mention « (absent de Jeedom) » : décochez-le pour le retirer. L'ordre des cases n'a pas d'importance ; la liste défile si elle est longue. Rien de coché = aucune exclusion de plugin. |
| **Politique de publication** | « Publier les équipements sûrs et probables (recommandé) » ou « Publier uniquement les équipements sûrs ». |

**Pièces exclues.** Il n'y a plus de champ de saisie des pièces dans cette page : « Pièces exclues : elles se règlent depuis la page du plugin (menu « ⋯ » d'une carte de pièce, ou détail de la pièce). » Un lien ouvre la page du plugin, et le nombre de pièces déjà exclues est rappelé (« 2 pièces exclues », sans leurs noms). Les pièces que vous aviez déjà indiquées dans l'ancien champ sont reprises telles quelles : elles apparaissent « Pièce exclue » sur leur carte. Voir [Exclure une pièce](#exclure-une-pièce). **Pièces exclues : sauf équipements exposés à HomeKit.** Un équipement actif exposé à HomeKit (réglage de Homebridge lu par le plugin) n'est pas écarté par l'exclusion de sa pièce : il reste publié, comme dans Apple Maison. L'exclusion de l'équipement lui-même, l'exclusion de son plugin et un équipement désactivé dans Jeedom restent respectés, ainsi que l'état global « exclure ».

« Sûr » veut dire que le type Home Assistant se déduit des types Jeedom sans doute ; « probable », qu'il s'en déduit avec un léger doute. La politique « Publier uniquement les équipements sûrs » ne met de côté que les équipements « probables ».

Le bouton situé sous ces réglages les enregistre puis relance une lecture complète de Jeedom, comme « Relire Jeedom » sur la page principale. Le bouton « Sauvegarder » de Jeedom enregistre aussi la liste des plugins exclus, au même format. Il affiche l'avancement (sauvegarde, puis lecture), puis le nombre d'équipements publiés.

Les exclusions de cette page sont **distinctes** de celles que vous posez avec le réglage « Jamais » de la configuration par pièce : voir [Ce que le plugin publie…](#ce-que-le-plugin-publie-ce-quil-ne-publie-pas-et-pourquoi), famille « Exclusions volontaires ».

---

## Première synchronisation

1. Configurez le broker MQTT, cliquez sur « Sauvegarder », puis démarrez ou redémarrez le démon. Vérifiez que la barre de santé de la page principale indique MQTT « Connecté » (vous pouvez aussi utiliser « Tester la connexion »).
2. Ajustez les filtres si nécessaire (plugins exclus, politique de publication ; les pièces s'excluent depuis la page du plugin).
3. Cliquez sur le bouton situé sous les filtres (page de configuration) ou, depuis la page principale du plugin, sur **« Relire Jeedom »**. Les deux lancent une lecture complète de Jeedom ; voir [Relire Jeedom](#relire-jeedom).
4. Dans Home Assistant, ouvrez **Paramètres → Appareils et services → MQTT** : vos équipements apparaissent.
5. Si un équipement manque, ouvrez sa pièce dans la page du plugin : la vue de travail vous dit son état et, s'il est bloqué, pourquoi.

Si, après un redémarrage du broker MQTT, Home Assistant ne retrouve pas ses entités, utilisez **« Republier tout »** sur la page principale.

---

## La page principale

La page du plugin contient, de haut en bas : le bloc « Gestion » (vignette « Configuration »), la barre de santé et ses actions, puis la configuration par pièce (une ligne d'aide, le bloc de la maison et les cartes de pièce). Aucun bandeau bleu n'ouvre plus la page.
<!-- CAPTURE-A-PRENDRE: page principale du plugin -->

### La barre de santé

La barre tient sur une ligne (elle se replie sur les petits écrans) : quatre indicateurs, chacun avec un point d'état et un mot, puis les actions à droite. Elle est lue **à l'ouverture de la page**, puis relue après « Republier tout », « Appliquer » et « Supprimer de Home Assistant » (à toutes les portées, **y compris quand l'action échoue**) et après « Relire Jeedom ». Il n'est pas relu après un changement du réglage de publication, et elle ne se rafraîchit pas toute seule : rechargez la page pour l'actualiser. Les quatre indicateurs :

| Indicateur | Valeurs possibles |
|---|---|
| **Démon** | « Actif » (vert) ; « Arrêté » (rouge : le démon ne répond pas) ; « Erreur Jeedom » ou « Erreur de communication » (rouge). |
| **MQTT** (la liaison avec le broker) | « Connecté » (vert) ; « Reconnexion... » ou « Connexion... » (orange) ; « Déconnecté » (rouge) ; « Non configuré » ; « Inconnu » (démon arrêté ou erreur). L'adresse du broker s'affiche à côté. |
| **Dernière synchro** | La date et l'heure (jour/mois et heures:minutes:secondes) de la dernière lecture complète, « Jamais » si aucune n'a eu lieu, « Inconnue » si le démon est arrêté. |
| **Dernière opération** | « Succès » (vert) ; « Partiel » ou « Échec » (orange : c'est un problème de configuration, pas une panne d'infrastructure) ; « Aucune » ; « Inconnue » si le démon est arrêté. Le message de l'opération s'affiche à côté. |

### Les actions de la barre de santé

Deux boutons de poids normal agissent sur **l'ensemble du parc** ; les actions moins courantes sont rangées dans le menu « ⋯ » (« Plus d'actions »), à droite :

| Action | Ce qu'elle fait |
|---|---|
| **« Republier tout »** | Après confirmation (« Republier tous les équipements inclus ? »), republie dans Home Assistant les équipements inclus et applique leurs réglages en attente. Les équipements « inclus » sont ceux que le plugin ne met pas d'office de côté (par exemple par une exclusion de la configuration ou parce qu'ils sont désactivés). « Republier tout » travaille sur ce que la dernière lecture complète a lu : il ne relit pas Jeedom. |
| **« Relire Jeedom »** | Relit tout Jeedom. Voir [Relire Jeedom](#relire-jeedom). |
| **« Télécharger le diagnostic… »** (menu « ⋯ ») | Ouvre une boîte qui propose le téléchargement du diagnostic support. Voir [Télécharger le diagnostic support](#télécharger-le-diagnostic-support). |
| **« Supprimer tout de Home Assistant… »** (menu « ⋯ », en rouge, séparé par un trait) | Retire de Home Assistant tout le parc publié, après une confirmation forte. Rien n'est recréé ensuite : « Republier » remet les équipements. Voir [Les actions de publication](#les-actions-de-publication). |

Le menu « ⋯ » s'ouvre au clic ou au clavier, se ferme par Échap ou par un clic à l'extérieur, et rend le focus à son bouton. Aucune action destructrice n'est visible hors de ce menu.

**Quand certains boutons sont grisés.** « Republier tout », « Relire Jeedom » et « Supprimer tout de Home Assistant… », ainsi que « Appliquer » et les entrées « Republier » et « Supprimer de Home Assistant… » des menus « ⋯ » (de la pièce et de chaque équipement), ne sont utilisables que si le démon tourne **et** que MQTT est connecté. Sinon, ils sont grisés et une ligne d'explication s'affiche :

- « Démon arrêté — actions Home Assistant bloquées. » (le démon est arrêté) ;
- « MQTT déconnecté — actions Home Assistant bloquées. » ;
- « Démon ou MQTT indisponible — actions Home Assistant bloquées. » (état impossible à lire).

Pendant une relecture de Jeedom, ces mêmes boutons sont aussi grisés. Le réglage de publication (« Automatique », « Toujours », « Jamais ») et le « Type HA » des commandes ne sont **pas** concernés : ils restent actifs, mais si le démon ne répond pas, leur action échoue avec un message d'erreur.

### Relire Jeedom

« Relire Jeedom » ouvre d'abord une confirmation : « Une relecture complète peut publier ou retirer des entités Home Assistant et applique les réglages enregistrés. Confirmer ? » (bouton « Relire »).

- **Ce qu'il fait** : relit tous les équipements de Jeedom, publie ou retire des entités Home Assistant en conséquence, et **applique d'un coup tous les réglages en attente** (types Home Assistant choisis, publication « Toujours » ou « Jamais ») de tous les équipements.
- **Ce qu'il ne fait pas** : il ne modifie rien dans Jeedom.
- **Scénarios** : le bouton Home Assistant d'un scénario Jeedom désactivé (ou supprimé) disparaît à la prochaine relecture ou au prochain redémarrage du démon, et revient à la réactivation. **Une seule installation jeedom2ha par broker MQTT** : le plugin considère le broker comme la référence des boutons de scénario, donc une deuxième instance (box de test, clone restauré) qui y serait connectée verrait ses boutons de scénario retirés par l'autre, et inversement.
- **Pendant l'opération** : le bouton affiche « Relecture en cours… » et les autres boutons d'action sont grisés.
- **Résultat** : un message « Synchronisation terminée. » (vert), « Synchronisation terminée avec avertissements. » (orange) ou « Synchronisation échouée. » (rouge) — remplacé par le message précis du démon quand il en fournit un. « Une opération est déjà en cours ou la relecture a échoué. » n'est qu'un message de repli : le démon renvoie le plus souvent son propre message, affiché à la place ; « Erreur de communication : relire Dernière synchro avant de relancer. » indique que la réponse n'est pas arrivée. La barre de santé est ensuite relue.

### Exclure une pièce

Une pièce entière peut être exclue de Home Assistant **depuis sa carte** (menu « ⋯ » en haut à droite de la carte, entrée **« Exclure la pièce… »**) ou **depuis le détail de la pièce** dans la vue de travail (même entrée dans le menu « ⋯ », avant « Supprimer de Home Assistant… »). Ouvrir ce menu n'ouvre pas la pièce. La carte « Sans pièce » n'a pas de menu : elle ne peut pas être exclue.

- **La confirmation est chiffrée.** « Exclure la pièce « Nom » de Home Assistant ? » annonce le nombre d'entités concernées : « 5 entités seront retirées de Home Assistant. », « 1 entité sera retirée… » ou « Aucune entité n'est publiée dans cette pièce. » Si la lecture des états n'est pas disponible, la confirmation le dit (« Nombre d'entités inconnu : la lecture des états n'est pas disponible. ») et reste possible. Si des réglages attendent d'être appliqués, elle ajoute « La relecture appliquera aussi les M réglages en attente de la maison. » Le bouton « Exclure la pièce » est rouge, car il retire des entités de Home Assistant ; « Annuler », la croix et la touche Échap ferment sans rien écrire.
- **L'effet est immédiat.** Après la confirmation, le plugin enregistre l'exclusion puis lance **une relecture complète de Jeedom** (celle de « Relire Jeedom », sans seconde confirmation), puis relit les chiffres. Pendant ce temps, « Relire Jeedom » et les entrées d'exclusion de toutes les pièces sont grisés (« Une opération est déjà en cours. »). Si l'enregistrement échoue, rien n'est relu ni changé. Si la relecture échoue, l'exclusion reste enregistrée et le message est suivi de « Relancez « Relire Jeedom » pour retirer les entités. » Exclure une pièce déjà exclue ne change rien mais relance quand même la relecture.
- **La carte** affiche **« Pièce exclue »** (icône œil barré) à la place de « n / t publiés » ; la jauge et les repères restent, et « N pas encore retirés » s'affiche tant que la relecture n'a pas retiré tous les équipements. Dans la vue de travail, la ligne de la pièce porte la même mention, et le détail de la pièce affiche « Pièce exclue : ses équipements ne sont pas publiés dans Home Assistant. » avec le bouton **« Ne plus exclure la pièce… »**.
- **« Ne plus exclure la pièce… »** demande une confirmation sans nombre (« Ses équipements seront relus et publiés s'ils sont publiables. ») ; le bouton « Ne plus exclure » n'est pas rouge, car rien n'est retiré.
- **La pièce prime sur « Toujours ».** Sauf équipements exposés à HomeKit (actifs), qui ne sont pas écartés par la pièce, un équipement réglé « Toujours » dans une pièce exclue n'est pas publié : « Toujours » reste affiché comme réglage posé, mais les positions grisées disent « Pièce exclue : elle prime sur ce réglage. »
- **Pas de cascade.** Seule la pièce choisie est exclue, pas ses sous-pièces : excluez-les aussi, une à une.

### Télécharger le diagnostic support

Le menu « ⋯ » de la barre de santé propose **« Télécharger le diagnostic… »**. Une boîte s'ouvre ; son bouton **« Télécharger le diagnostic support »** produit un fichier `jeedom2ha-diagnostic-AAAA-MM-JJ.json` à joindre à une demande d'aide. Fermer la boîte n'envoie rien.

- La case **« Pseudonymiser les noms d'équipements »** remplace les noms d'équipements par « Équipement_N », les noms de pièces par « Pièce_M » et les noms de commandes par « Cmd_ » suivi de leur numéro, et masque l'adresse du broker.
- Messages : « Export en cours... », puis « Diagnostic téléchargé » ; en cas de problème, « Erreur export » ou « Erreur de communication », ou le message du démon (par exemple « Démon indisponible ou timeout — relancez le démon et réessayez. »).

Ce fichier est un outil d'assistance. Pour comprendre l'état d'un équipement, utilisez la configuration par pièce.

---

## La configuration par pièce

Sous la barre de santé, la section **« Configuration Home Assistant par pièce »** commence par une ligne d'aide discrète, avec un lien **« Aide »** vers cette documentation. Le type natif Jeedom (partagé avec Homebridge) n'est jamais modifié par le plugin.

### Le bloc de la maison

Le bloc de la maison donne, dès le premier écran, le chiffre qui compte : un grand nombre suivi de « publiés sur » le total des équipements Jeedom, avec le nombre de pièces. Dessous, une **jauge** segmentée (publiés en vert, à appliquer en bleu, bloqués en orange, exclus et autres en gris, non lus en hachuré) et une **légende en puces**.

- **Chaque puce (et chaque segment de la jauge) est un filtre** qui s'applique à toutes les pièces : un clic ouvre la [vue de travail](#la-vue-de-travail) avec ce filtre actif (l'arbre ne montre que les équipements dans cet état). Au retour sur la page principale, le filtre est conservé : la liste des équipements dans cet état s'affiche sous le bloc, avec leur pièce, et les cartes de pièce sans équipement concerné sont atténuées (jamais masquées). Un clic sur une ligne de cette liste ouvre la vue de travail sur l'équipement. Un second clic sur la puce, la touche Échap ou « Tout afficher » retire le filtre. Un filtre ne fait aucune requête : il lit les chiffres déjà affichés.
- Les puces à zéro restent affichées mais sont grisées. La puce « exclus et autres » regroupe les équipements exclus, désactivés et sans rien à publier ; chaque ligne garde son propre mot d'état.
- **« Actualiser »** relit les chiffres en contournant la mémoire du démon, et « Chiffres relus à HH:MM » indique l'heure de la dernière lecture. Les chiffres sont relus à l'ouverture de la page, après chaque action (« Republier tout », « Relire Jeedom », « Supprimer tout de Home Assistant… », et chaque action de la vue de travail, qu'elle réussisse ou échoue) et quand vous revenez sur l'onglet du navigateur après plus d'une minute. Il n'y a pas de relecture périodique.
- Pendant une opération du plugin, une mention « Opération en cours : ces chiffres peuvent changer » s'affiche ; le plugin relit alors trois fois au plus, puis laisse la mention en place. Avant la première synchronisation, la page indique « Aucune synchronisation n'a encore eu lieu » ; si la lecture échoue, « Chiffres indisponibles » (les derniers chiffres valides restent affichés, atténués).

Le détail des chiffres est dans [Les états et les compteurs](compteurs.md#la-jauge-de-la-maison).

### Les cartes de pièce

Chaque pièce qui contient au moins un équipement a une carte portant l'icône et la couleur choisies dans Jeedom pour l'objet, son nom, « n / t publiés », une petite jauge segmentée et, seulement s'ils ne sont pas nuls, les repères « N bloqués » (orange), « N à appliquer » (bleu), « N non lus » (gris) et « N exclus » (gris, après les autres : l'infobulle et le nom accessible de la carte donnent la ventilation par cause, comme dans le détail de la pièce). Une carte qui contient au moins un équipement bloqué porte un liseré orange. Les cartes sont **regroupées par objet parent** (sous-titre du groupe, ordre de Jeedom conservé). La carte **« Sans pièce »** rassemble les équipements qui n'ont pas de pièce, en dernier. Les équipements **désactivés dans Jeedom sont comptés et listés**. Les équipements du plugin jeedom2ha lui-même sont écartés. Chaque carte (sauf « Sans pièce ») a un menu « ⋯ » pour exclure la pièce ou ne plus l'exclure (voir [Exclure une pièce](#exclure-une-pièce)) ; une pièce exclue affiche « Pièce exclue » à la place de « n / t publiés ». S'il n'y a aucune pièce avec équipement, la page affiche « Aucune pièce avec équipement trouvée. »

Les cartes sont opérables au clavier (Entrée ou Espace ouvre la vue de travail sur la pièce, seule dans l'arbre). Un équipement dont la lecture a échoué, ou que le démon ne connaît pas encore, est compté **« non lu »** : il n'est jamais compté publié, bloqué, exclu ni désactivé.
<!-- CAPTURE-A-PRENDRE: cartes de pièce -->

### La vue de travail

Cliquer sur une carte de pièce, sur une puce ou un segment de la jauge de la maison, ou sur une ligne de la liste filtrée ouvre la **vue de travail**, dans la page du plugin, **sans ouvrir de boîte de dialogue** : la barre de santé reste affichée au-dessus, le bloc de la maison, la liste filtrée et les cartes sont masqués (ils retrouvent leur état au retour). La vue occupe la hauteur de l'écran : à gauche l'arbre des pièces et de leurs équipements, à droite le détail de ce que vous avez choisi ; chaque colonne défile seule.

- **La portée.** Depuis **une carte de pièce**, l'arbre n'affiche que **cette pièce** (dépliée et choisie) : elle est tout de suite visible, même dans une maison de plus de vingt pièces. Le bouton **« Toutes les pièces »**, en tête de l'arbre (dans le tiroir « Pièces » sur tablette), élargit à toute la maison : le choix est conservé, la ligne choisie reste visible et reçoit le focus, et le bouton disparaît. Depuis une puce, un segment de la jauge ou une ligne de la liste filtrée, la vue s'ouvre directement sur **toutes les pièces**, pour garder le contexte du filtre. Dans la pièce seule, la recherche et les filtres ne portent que sur cette pièce.
- **Le retour.** « Page principale » (ou le bouton « Précédent » du navigateur) revient à la page principale telle que vous l'avez laissée (filtre, position de défilement), sans rien relire. La touche Échap ne quitte pas la vue : elle ferme d'abord un menu ou une confirmation ouverts.
- **L'adresse de la page** garde votre sélection (elle se termine par `#j2ha-vue=…`) : copiée dans un autre onglet, elle rouvre la même pièce et le même équipement. Une adresse qui se termine par `seule:1` rouvre la pièce seule ; sans `seule:1`, elle rouvre toutes les pièces. Élargir remplace l'entrée de l'historique au lieu d'en ajouter une : « Précédent » remonte d'un niveau (équipement, puis pièce, puis page principale) et rouvre chaque niveau avec la portée qu'il avait. La recherche n'est pas mémorisée.
- **L'arbre** reprend, en portée « toutes », toutes les pièces, regroupées comme les cartes (sous-titre du groupe, ordre de Jeedom conservé), « Sans pièce » comprise. Chaque pièce porte l'icône et la couleur choisies dans Jeedom, son nom, « n / t » et, seulement s'ils ne sont pas nuls, les repères « N bloqués » (orange) et « N à appliquer » (bleu). Déplier une pièce montre ses équipements : l'état avant le nom (le même mot que partout), la mention « (désactivé dans Jeedom) » le cas échéant, « N bloquées » pour un équipement publié qui en comporte, et « non lu » pour un équipement dont les chiffres n'ont pas pu être lus. La pièce choisie est dépliée ; les autres sont repliées. L'arbre se parcourt au clavier : flèches haut et bas, flèches droite et gauche pour déplier ou replier, Entrée ou Espace pour choisir, Début et Fin.
- **La cause d'exclusion** d'un équipement « Exclu » est une mention grise après son nom (« par le plugin X », « par la pièce », « individuelle »), tronquée avant le nom si la place manque. Le détail d'une pièce affiche, sous ses compteurs, la ligne « Exclus : » avec la ventilation par cause.
- **La recherche** (« Rechercher une pièce ou un équipement ») porte sur les noms de pièce et d'équipement seulement, sans tenir compte de la casse ni des accents ; « Aucun résultat » s'affiche quand rien ne correspond. Une pièce dont le nom correspond montre tous ses équipements. Elle ne fait aucune requête.
- **Les filtres** sont les mêmes puces que sur la page principale, avec les mêmes libellés ; les effectifs sont ceux de la maison, ou ceux de la pièce quand la vue est limitée à une pièce (le nombre de lignes de l'arbre est toujours égal au chiffre de la puce). Le filtre est **partagé** avec la page principale : celui que vous avez choisi y est repris, et un changement fait dans la vue se retrouve au retour. Une puce à zéro est grisée. Choisir un filtre ne fait aucune requête et ne désélectionne rien : l'équipement affiché reste affiché même s'il sort du filtre.

**Le détail d'une pièce** montre : le fil d'Ariane (parent puis pièce), le nom, le bouton **« Republier la pièce »** et le menu « ⋯ » (**« Exclure la pièce… »** ou **« Ne plus exclure la pièce… »**, puis **« Supprimer de Home Assistant… »**, en rouge, dans le menu seulement ; une pièce exclue affiche aussi l'encart « Pièce exclue : ses équipements ne sont pas publiés dans Home Assistant. »), les **compteurs de la pièce** (un chiffre et un mot court par état d'équipement : publié, à appliquer, bloqué, exclu, désactivé, rien à publier ; les états à zéro sont masqués ; un clic sur un compteur filtre l'arbre — voir [Les états et les compteurs](compteurs.md)), une zone de résultat, et la liste **« À traiter dans cette pièce »** : une ligne par équipement bloqué ou à appliquer, avec son état, son nom, le nombre de commandes concernées et la cause dite une seule fois. L'action de la ligne est unique : **« Ouvrir les types génériques »** quand le blocage se corrige dans Jeedom, **« Appliquer »** pour un équipement à appliquer (le résultat s'affiche dans la zone de résultat). Un clic sur le reste de la ligne affiche l'équipement. Quand il n'y a rien à faire, la vue dit « Rien à traiter dans cette pièce » et rappelle combien d'équipements n'appellent aucune action. Pour « Sans pièce », il n'y a ni « Republier la pièce » ni menu : la vue indique « Republication et suppression de pièce indisponibles pour les équipements sans pièce : utilisez les actions de chaque équipement. » Le résultat de la dernière action s'affiche dans la zone de résultat (vert : succès ; orange : succès partiel ; rouge : échec).

**Le détail d'un équipement** s'affiche quand vous choisissez un équipement dans l'arbre ou dans la liste « À traiter dans cette pièce ». Le plugin ne lit la configuration **que de cet équipement** et seulement à ce moment (« Chargement… » s'affiche) ; choisir de nouveau le même équipement la relit. Si la lecture échoue, le détail indique « Impossible de lire la configuration de cet équipement. » ou « Impossible de charger la configuration HA (démon indisponible). » et n'offre aucune action. Un seul équipement est affiché à la fois ; son en-tête (nom, badge, réglage de publication, « Appliquer » et menu « ⋯ ») reste collé en haut pendant que vous faites défiler le tableau, sans autre barre de défilement dans le détail. Son contenu est décrit ci-dessous.

**Sur tablette et petit écran** (en dessous de 980 pixels de large), l'arbre devient un **tiroir** : le bouton **« Pièces »** l'ouvre au-dessus du détail, un autre clic ou le choix d'une pièce ou d'un équipement le referme ; le tiroir est ouvert tant que rien n'est choisi. Le détail occupe toute la largeur, sans défilement horizontal. Tourner la tablette ne perd ni la sélection, ni le filtre, ni la recherche, ni votre position, et ne refait aucune requête. Les lignes, les puces et les boutons sont assez grands pour le doigt.
<!-- CAPTURE-A-PRENDRE: vue de travail -->

### Le détail d'un équipement

L'en-tête de l'équipement affiché, qui reste visible, comporte :

- **Le badge d'état** (« Publié », « À appliquer », « Bloqué », « Exclu », « Désactivé » ou « Rien à publier »), suivi, quand l'équipement est publié ou à appliquer, de la **mention orange** du nombre de commandes bloquées (« 2 bloquées »).
- **La cause d'exclusion**, sous le badge, quand l'état est « Exclu » (jamais pour un équipement « Désactivé ») : une phrase grise dit pourquoi et où agir — « Exclu par le plugin X (configuration du plugin, « Plugins exclus ») » avec le bouton « Ouvrir la configuration du plugin » ; « Exclu par la pièce : toute la pièce est exclue » ; « Exclusion individuelle : réglage « Jamais » », « Exclusion individuelle : « Jamais » sur ses entités » ou « Exclusion individuelle : réglage de l'équipement dans Jeedom ». Le bouton n'écrit rien : il ouvre seulement la configuration.
- **Le réglage « Publication dans Home Assistant »**, un contrôle à trois positions **« Automatique », « Toujours », « Jamais »**. La position courante est toujours montrée : « Jamais » pour un équipement exclu, « Toujours » pour un équipement forcé, « Automatique » sinon. Choisir une position enregistre le réglage (voir [Les actions de publication](#les-actions-de-publication)) ; il n'est pas publié tout de suite. Une position indisponible est grisée et son infobulle dit pourquoi. Au clavier, les flèches déplacent le choix, Espace ou Entrée le valident.
- **Le bouton « Appliquer »**, affiché **seulement quand l'état est « À appliquer »** (voir [Réglages en attente](#réglages-en-attente-et-appliquer)).
- **Le menu « ⋯ »** (touche Échap pour le fermer) : « Republier », « Tout remettre en automatique… », puis, séparée par un trait, « Supprimer de Home Assistant… » en rouge.

Dessous, de haut en bas :

- **La ligne de l'équipement** : son état, puis le détail de ses commandes par catégorie (publiées, à appliquer, bloquées, ignorées, exclues). Voir [Les états et les compteurs](compteurs.md).
- **Les encarts de cause** : la cause d'un blocage est dite **une seule fois**, avec le nombre de commandes concernées (« 11 commandes bloquées : types génériques non configurés dans Jeedom »). S'il y a plusieurs causes, il y a un encart par cause, jamais un par commande. Quand le blocage se corrige dans les types génériques de Jeedom, l'encart porte le bouton **« Ouvrir les types génériques »**, qui ouvre l'écran des types d'équipement de Jeedom (il n'écrit rien). Le lien **« Voir la première commande bloquée »** fait défiler le tableau jusqu'à elle et la met en évidence quelques secondes ; il n'est pas affiché quand toutes les commandes de l'équipement sont bloquées.
- **Le tableau des commandes**, regroupé par entité.
- **Une ligne repliée pour les commandes ignorées** : « 5 commandes ignorées, sans équivalent dans Home Assistant : … ». Elle se déplie au clic ou au clavier. Pour une commande qui n'est pas prise en charge par le plugin, la ligne ajoute « non pris en charge par le plugin ».

Un équipement sans commande affiche « Aucune commande à configurer pour cet équipement. »
<!-- CAPTURE-A-PRENDRE: détail d'un équipement -->

### Le tableau des commandes

Le tableau a **quatre colonnes**, une ligne par commande, dans l'ordre de Jeedom au sein de chaque groupe :

| Colonne | Contenu |
|---|---|
| **Commande** | Le nom de la commande. |
| **Dans Home Assistant** | Ce que devient la commande : « Publiée → Lumière (light) », « À appliquer → Capteur (sensor) » (publiable, pas encore dans Home Assistant), « Bloquée » (la cause est dans l'encart de l'équipement, pas répétée sur chaque ligne), « Exclue », ou « — ». |
| **Type Jeedom** | Le type générique de la commande dans Jeedom. Lecture seule : il n'est jamais modifié. |
| **Type HA** | « auto » (le plugin choisit seul) ou « imposé (sensor) » (surligné). Un clic sur ce lien ouvre le sélecteur. Voir [Choisir le type Home Assistant d'une commande](#choisir-le-type-home-assistant-dune-commande). |

**Regroupement par entité.** Quand l'équipement a plusieurs entités Home Assistant, chaque entité forme un groupe : une ligne d'en-tête (le domaine en français avec le terme technique en petit, par exemple « Lumière *light* », le nombre de commandes, le contrôle « Automatique | Toujours | Jamais » de **cette entité**), puis ses commandes. Les domaines sont traduits : Lumière (`light`), Interrupteur (`switch`), Capteur (`sensor`), Capteur binaire (`binary_sensor`), Volet (`cover`), Thermostat (`climate`), Bouton (`button`), Alarme (`alarm_control_panel`). Sur un équipement qui n'a qu'une seule entité, il n'y a pas d'en-tête de groupe : le réglage de l'équipement suffit. L'en-tête reste affiché si un réglage a été posé sur la commande de cette seule entité.

Les commandes **ignorées** (qu'aucun type Home Assistant ne prend en charge) n'apparaissent pas dans le tableau : elles sont repliées sous lui.
<!-- CAPTURE-A-PRENDRE: tableau des commandes -->

### Choisir le type Home Assistant d'une commande

Par défaut le plugin choisit seul le type Home Assistant d'une commande (« auto »). Vous pouvez en imposer un autre :

1. Cliquez sur le lien de la colonne « Type HA » : le sélecteur s'ouvre (Échap le referme). Choisissez un type dans la liste. Après une courte attente (environ 0,4 seconde), le plugin **vérifie** le choix et affiche le résultat dans la colonne « Dans Home Assistant ».
2. Si le choix est valide (« À appliquer → <type> »), il est **enregistré automatiquement** : il n'y a pas de bouton « Enregistrer ».
3. Sinon, il est **refusé** (« Bloquée → <cause> ») ; rien n'est enregistré. Choisissez de nouveau l'équipement pour retrouver l'état réellement enregistré.
4. Un choix enregistré **n'est pas publié tout de suite**. Le signe fiable est l'état « À appliquer » de l'équipement et le bouton « Appliquer ». Cliquez sur « Appliquer » ou lancez « Relire Jeedom ».
5. Pour annuler le choix d'une commande, sélectionnez « auto » dans la liste, ou cliquez sur l'icône « Retirer le type imposé » à côté du lien. Cette icône ne retire que le choix de **type** de cette commande.

**La liste ne propose que des types qui peuvent aboutir.** Le plugin vérifie, pour chaque type, si Home Assistant pourrait recevoir cette commande sous ce type ; un type qui échouerait toujours (par exemple `sensor` pour la commande d'état d'un volet sans commande d'ouverture) est retiré, car « Toujours » ne peut pas le faire aboutir. Un type valide mais refusé seulement parce que le choix automatique est ambigu reste proposé : c'est le cas où « Toujours » peut aider. Un type déjà choisi pour la commande reste affiché, pour que vous puissiez revenir à « auto ». Pour qu'un type de plus soit proposé, précisez les types génériques de l'équipement dans Jeedom.

Le lien est **grisé avec une infobulle** quand le réglage n'a pas de sens :

- « Commande exclue de Jeedom2HA : son type HA ne peut pas être réglé ici. »
- « Équipement désactivé dans Jeedom : son type HA ne peut pas être réglé ici. »
- « Aucun type Home Assistant ne couvre cette commande : son type HA ne peut pas être réglé ici. »
- « Cette commande est portée par plusieurs entités : le type Home Assistant choisi ne s’appliquerait qu’à l’entité principale de l’équipement. Réglage indisponible ici. » (par exemple une commande d'état publiée par un capteur secondaire alors que l'entité principale est refusée). Si un type avait déjà été choisi pour cette commande, l'icône « Retirer le type imposé » reste disponible.
- « Aucun type Home Assistant ne peut aboutir pour cette commande en l’état : précisez les types génériques dans Jeedom. » (aucun type n'est valide pour cette commande ; la voie normale est de préciser les types génériques dans Jeedom)

Quand une vérification fait apparaître une commande bloquée, un bandeau d'avertissement rappelle, une fois par ouverture de la vue de travail : « Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha. »

### Deux familles de réglages : type et publication

Le plugin distingue deux sortes de réglages manuels :

| | Réglage de **type** | Réglage de **publication** |
|---|---|---|
| **Ce que c'est** | Le « Type HA » d'une commande (« auto » ou un type imposé). | « Automatique », « Toujours » ou « Jamais » pour une entité ou un équipement. |
| **Où** | Colonne « Type HA » du tableau des commandes. | Contrôle à trois positions de l'équipement et de chaque groupe d'entité. |
| **Enregistrement** | Automatique si le choix est valide. | Au clic (avec confirmation dans certains cas). |
| **Annulation** | « auto » ou l'icône « Retirer le type imposé » (cette commande seulement). | « Automatique » (voir plus bas ce qu'il retire selon la portée). |

Dans les deux cas, le réglage n'est visible dans Home Assistant qu'après avoir été appliqué.

### Réglages en attente et Appliquer

Un réglage enregistré n'est pas publié immédiatement. Tant qu'il attend, l'écran le signale :

- sur l'équipement : le badge passe à **« À appliquer »** (bleu) et le bouton **« Appliquer »** apparaît dans son en-tête ;
- sur l'entité concernée (équipement à plusieurs entités) : la mention « À appliquer » dans son en-tête de groupe.

Un équipement est aussi « À appliquer » quand sa publication est due mais n'a pas eu lieu (jamais publié alors qu'il le devrait), ou quand le démon est une version plus ancienne qui ne dit pas s'il est présent dans Home Assistant : il n'est alors jamais affiché « Publié ». Voir [Les états et les compteurs](compteurs.md).

Pour l'appliquer à **un équipement**, cliquez sur son bouton **« Appliquer »**. « Republier la pièce » et « Republier tout » appliquent aussi les réglages en attente des équipements concernés. Un [relevé de Jeedom](#relire-jeedom) applique d'un coup ceux de **tous** les équipements. « Appliquer » ne demande pas de confirmation ; son résultat s'affiche dans la zone de résultat du détail, et en cas d'échec le bouton reste affiché avec le message d'erreur.

### Les actions de publication

**Le réglage de publication** (contrôle « Automatique | Toujours | Jamais ») existe à la portée de l'**équipement entier** (en-tête de l'équipement) et de **chaque entité** (en-tête de son groupe, quand l'équipement a plusieurs entités). Dans les paragraphes ci-dessous, « Jamais », « Toujours » et « Automatique » désignent ces positions, quelle que soit leur portée.

**Jamais**

- *Ce que ça fait* : l'équipement n'est plus publié dans Home Assistant, ou l'entité n'y est plus publiée.
- *Confirmation* : seulement si le réglage fait **quitter Home Assistant** une entité publiée selon le diagnostic. La confirmation demande « Régler cet équipement sur « Jamais » (exclu de Home Assistant) ? » (avec la liste « Entités qui quitteront Home Assistant : … ») ou « Régler cette entité sur « Jamais » (exclue de Home Assistant) ? ». Boutons « Annuler » et « Confirmer ». Sinon le réglage est enregistré directement.
- *Ensuite* : comme tout réglage, il attend d'être appliqué (« Appliquer », « Republier » ou « Relire Jeedom »).

**Toujours**

- *Ce que ça fait* : demande au plugin de publier une entité qu'il aurait refusé de publier.
- *Confirmation* : toujours précédée d'un **aperçu** calculé par le démon, avant toute écriture. Il indique « Type HA : … », « Projection valide pour ce type. » ou « Projection invalide pour ce type. » (la « projection » est la transformation de l'équipement Jeedom en entité Home Assistant de ce type), « Commandes qui recevront les ordres : … » et « Le forçage publie cette entité dans Home Assistant. ». À la portée équipement, l'aperçu liste « Entités concernées par ce forçage : … » et conclut « Le forçage publie au moins une entité dans Home Assistant. ».
- *Si le réglage serait refusé* : l'aperçu affiche « Le forçage serait refusé : <raison> » et le bouton « Confirmer » est grisé. Si le démon ne répond pas : « Aperçu indisponible — le démon ne répond pas. »

**Automatique**

- *Équipement* : choisir « Automatique » retire le réglage de publication de l'équipement. Cliquer sur la position déjà courante n'écrit rien. Pour retirer **d'un coup les deux sortes** de réglages de l'équipement (types choisis pour ses commandes, « Jamais » ou « Toujours » de l'équipement et de ses entités), utilisez « Tout remettre en automatique… » du menu « ⋯ » : une confirmation précède le retrait.
- *Entité* : retire « Jamais » ou « Toujours » de l'entité **et** les types Home Assistant choisis pour ses commandes.
- Pas de confirmation.

**Republier / Appliquer**

- *Équipement* : « Appliquer » (bouton bleu, seulement quand l'état est « À appliquer ») et « Republier » (menu « ⋯ ») utilisent la même route. Sans confirmation.
- *Pièce* : « Republier la pièce » demande « <nom de la pièce> — republier les équipements inclus de cette pièce. Confirmer ? » (bouton « Republier »). Elle applique aussi les réglages en attente de la pièce.
- *Dans tous les cas*, « Republier » ne relit pas Jeedom : il travaille sur ce que la dernière lecture complète a lue.
- *Parc* : voir [la page principale](#les-actions-de-la-barre-de-santé).

**Supprimer de Home Assistant…**

- *Ce que ça fait* : retire de Home Assistant les entités **publiées** de l'équipement, de la pièce ou du parc. L'entrée est en rouge dans le menu « ⋯ » seulement ; l'ellipse annonce une confirmation.
- *Ce que ça ne fait pas* : cette action **supprime seulement** ; elle ne republie pas. Pour recréer les entités, utilisez ensuite « Republier » à la même portée, ou lancez « Relire Jeedom ».
- *Confirmation forte* (bouton rouge), intitulée « Supprimer de Home Assistant ». Son texte annonce ce qui sera supprimé : « Supprimer "<nom>" de Home Assistant. » (équipement), « … de Home Assistant : tous les équipements publiés de cette pièce. » (pièce) ou « Supprimer de Home Assistant tout le parc publié ? » (parc).
- *Mise en garde* : **« Attention : l'historique, les dashboards, les automatisations et l'entity_id liés à ces entités peuvent être impactés. »** (l'`entity_id` est l'identifiant de l'entité dans Home Assistant). Elle rappelle aussi : **« Rien n'est recréé automatiquement : utilisez « Republier » pour remettre dans Home Assistant ce qui a été supprimé. »** (pour le parc : « … pour remettre les équipements dans Home Assistant. »)
- *Boutons* : « Supprimer 1 équipement », « Supprimer la pièce » ou « Supprimer ».
- *Résultat* : un message tel que « 2 équipements supprimés de Home Assistant. » ou « Configuration déjà à jour dans Home Assistant. ».

**Pendant une action**, l'entrée ou le bouton affiche « Confirmation en cours… », puis « En cours... » (publication) ou « Suppression... ». Le message de résultat est précédé du nom de la portée (par exemple « Parc global — … »). Messages d'erreur possibles : « Le démon ne répond pas. », « Erreur de communication avec le backend Home Assistant. », « Réponse backend incomplète pour l'action Home Assistant. ». Les délais d'attente sont décrits en [annexe](#annexe--durée-des-actions).

#### Quand un bouton est grisé

Un bouton ou une position grisés affichent **leur propre motif** dans une infobulle (survolez-les). Les motifs possibles :

| Bouton | Motifs affichés |
|---|---|
| Appliquer, Republier, Supprimer de Home Assistant… (toutes portées) et Relire Jeedom | Voir [les actions de la barre de santé](#les-actions-de-la-barre-de-santé) (démon arrêté, MQTT déconnecté, relecture en cours). Les positions « Automatique », « Toujours » et « Jamais » ne sont pas concernées. |
| Jamais | « Aucune commande clé propre à cette entité. » ; « Équipement non éligible : l’action serait sans effet. » |
| Toujours | « Déjà publiée : « Toujours » n’aurait pas d’effet. » ; « Aucun type Home Assistant identifié pour cette entité. » ; « Type HA hors périmètre de ce plugin. » ; « Projection invalide pour ce type HA. » ; « Exclusion posée sur l’équipement : la retirer depuis l’équipement. » ; « Aucune commande clé propre à cette entité. » ; « Équipement non éligible : l’action serait sans effet. » |
| Automatique | « Aucun réglage de publication à retirer. » ; « Exclusion posée sur l’équipement : la retirer depuis l’équipement. » ; « Aucune commande clé propre à cette entité. » |
| Republier (équipement) | « Équipement désactivé dans Jeedom : rien à republier. » ; « Équipement exclu : rien à republier. » (sauf si un réglage est en attente) |
| Supprimer de Home Assistant… (équipement) | « Équipement non publié dans Home Assistant : rien à supprimer. » Ce grisé reflète la présence **réelle** dans Home Assistant, pas le badge d'état : un équipement peut afficher « À appliquer » et avoir cette entrée grisée tant qu'il n'a pas été publié. |
| Republier (pièce) | « Aucun équipement à publier dans cette pièce. » |
| Supprimer de Home Assistant… (pièce) | « Aucun équipement publié dans cette pièce. » (même logique : présence réelle dans Home Assistant) |

Une position déjà choisie reste la position courante du contrôle : elle n'est pas grisée. Un bouton grisé sans motif particulier affiche « Cette action est sans effet dans l’état courant. »

Deux expressions de ces motifs méritent une explication. Une **« commande clé »** est une commande qui n'appartient qu'à une seule entité et qui sert à la désigner ; si toutes les commandes d'une entité sont partagées avec une autre entité, « Automatique », « Toujours » et « Jamais » sont grisés pour elle. La **projection** est la transformation de l'équipement en entité Home Assistant d'un type donné ; elle est « invalide » quand il manque ce dont ce type a besoin.

---

## Ce que le plugin publie, ce qu'il ne publie pas, et pourquoi

### Ce que le plugin sait publier

Le plugin publie huit types d'entités Home Assistant. Le type est choisi à partir des types Jeedom des commandes de l'équipement.

| Type Home Assistant | Ce que le plugin en fait |
|---|---|
| `light` | Lumières : allumer/éteindre et variation de luminosité, avec l'état réel quand Jeedom le fournit (voir [Limites](#limites--état-réel-des-lumières-et-des-volets)). La couleur n'est pas reprise, et une lumière qui n'a que des commandes de couleur n'est pas prise en charge. |
| `cover` | Volets et stores : ouverture/fermeture, arrêt et position quand ils existent, avec l'état et la position réels quand Jeedom les fournit. |
| `switch` | Prises et interrupteurs (commandes d'énergie On/Off, familles « interrupteur » et « ventilateur » de Jeedom), ainsi que les équipements de présence actionnables (information de présence + actions pour l'activer et la désactiver). |
| `sensor` | Informations numériques. |
| `binary_sensor` | Informations binaires. |
| `button` | Actions ponctuelles sans valeur, et **scénarios Jeedom actifs** (un bouton par scénario actif). |
| `climate` | Thermostats, pour la consigne et la température. |
| `alarm_control_panel` | Alarmes : état armé/désarmé et commandes pour armer et désarmer. |

Le plugin ne publie pas les équipements sans type Jeedom reconnu : il l'indique alors dans l'encart de cause de l'équipement.

### Limites : état réel des lumières et des volets

Le plugin remonte l'état **réel** d'une lumière ou d'un volet seulement si l'équipement Jeedom a une **commande d'information** correspondante. Sans elle, Home Assistant affiche un état **supposé** : celui de la dernière commande envoyée, qui peut différer de la réalité.

| Équipement | Commande d'information Jeedom | Ce que Home Assistant affiche |
|---|---|---|
| Lumière | état (marche/arrêt) | l'état réel allumée/éteinte |
| Lumière variable | état **et** luminosité (ou un état numérique, qui donne alors aussi la luminosité) | l'état réel et la luminosité réelle (0 à 100) |
| Lumière variable | état binaire seul, sans luminosité | l'état réel ; la luminosité reste supposée par Home Assistant |
| Lumière variable | luminosité seule, sans état | l'état allumée/éteinte reste supposé : le plugin ne le déduit jamais de la luminosité |
| Lumière sans commande d'état | aucune | état supposé |
| Volet | état d'ouverture (binaire) | ouvert ou fermé réel |
| Volet positionnable | état numérique (0 à 100) | ouvert/fermé et position réels ; une position intermédiaire s'affiche « ouvert » |
| Volet avec curseur de position | état binaire seul | ouvert/fermé réel ; la **position n'est pas remontée** (pas de valeur numérique à lire) |
| Volet sans commande d'état | aucune | état supposé |

Autres limites à connaître :

- **Aucune inversion de position.** Le plugin reprend la valeur de Jeedom telle quelle (0 = fermé, 100 = ouvert). Si un plugin Jeedom inverse cette échelle, la position affichée est inversée.
- **Pas d'état intermédiaire** « en ouverture », « en fermeture » ou « arrêté » : seuls ouvert et fermé sont remontés.
- **Valeur illisible ou hors de 0 à 100 :** rien n'est publié, Home Assistant garde la dernière valeur connue.
- **Retrait d'une commande d'information :** le plugin garde la liste des états qu'il a lui-même publiés (fichier du démon). À la synchronisation ou à la republication suivante, il efface l'état mémorisé par le broker pour ce canal, afin que Home Assistant ne le relise pas. Un état publié par une version qui ne tenait pas cette liste ne peut pas être effacé automatiquement.
- La couleur d'une lumière, les thermostats et les alarmes ne sont pas concernés par cette remontée d'état.

### Les badges de synthèse

Le badge à droite du nom de chaque équipement dit son **état**. Un équipement n'en a qu'un, toujours dit avec le même mot et la même teinte dans l'arbre, le badge du détail et les compteurs de la pièce (le détail des règles est dans [Les états et les compteurs](compteurs.md)).

| État | Teinte | Ce que cela veut dire |
|---|---|---|
| **Publié** | vert (discret) | L'équipement est présent dans Home Assistant. |
| **À appliquer** | bleu | Un réglage attend d'être appliqué, ou la publication due n'a pas encore eu lieu. |
| **Bloqué** | orange (le plus visible) | Rien n'est dans Home Assistant et au moins une commande est bloquée par une cause corrigeable. |
| **Exclu** | gris | L'équipement est volontairement écarté. La **cause** est dite à côté du mot : « par le plugin X », « par la pièce » ou « individuelle » (voir [Exclusions volontaires](#ce-que-le-plugin-publie-ce-quil-ne-publie-pas-et-pourquoi)). Ce n'est pas un état de plus. |
| **Désactivé** | gris, en italique | L'équipement est désactivé dans Jeedom. Il l'emporte sur « Exclu ». |
| **Rien à publier** | gris | Aucune commande n'est publiable ni bloquée. |

Quand l'équipement est « Publié » ou « À appliquer » et que certaines commandes sont bloquées, le badge est suivi de la **mention orange** du nombre de commandes bloquées (« 1 bloquée », « 2 bloquées ») : ce n'est pas un état, il n'existe pas d'état « partiel ».

Vocabulaire :

- Une commande **publiée** est dans Home Assistant (portée par au moins une entité présente).
- Une commande **bloquée** devrait pouvoir être publiée mais ne l'est pas ; la cause est dite dans l'encart de l'équipement. Certaines causes se corrigent (voir les familles ci-dessous), d'autres non.
- Une commande **ignorée** n'a aucun équivalent dans Home Assistant : il n'y a rien à faire, et elle n'est jamais comptée comme un défaut.
- Une commande **exclue** est écartée par un réglage.
- Une **entité Home Assistant** est ce qui apparaît dans Home Assistant ; un équipement peut en produire plusieurs.
- Un équipement **exclu** est volontairement écarté : par vous (« Jamais »), par la configuration du plugin (plugins, pièces) ou par un réglage d'exclusion propre à l'équipement dans Jeedom.

Le badge dit ce qui est dans Home Assistant **maintenant** ou ce qui reste à appliquer ; la présence réelle dépend de l'application des réglages (voir [Réglages en attente](#réglages-en-attente-et-appliquer)).

### Les causes de blocage

Quand des commandes sont bloquées, l'équipement affiche un encart par cause (« 11 commandes bloquées : types génériques non configurés dans Jeedom »). Les lignes du tableau montrent seulement « Bloquée ». Les causes sont regroupées ici par ce que vous pouvez en faire.

**1. Corrections possibles côté Jeedom (types génériques ou nom de l'équipement)**

| Cause affichée | Pour agir |
|---|---|
| type Home Assistant ambigu — précisez les types génériques dans Jeedom | Précisez les types génériques des commandes dans Jeedom (bouton « Ouvrir les types génériques »). |
| types génériques en conflit — précisez-les dans Jeedom | Idem. |
| types génériques en double | Deux commandes portent le même type : retirez le doublon. |
| un mot du nom de l’équipement écarte ce type | Renommez l'équipement (voir [Nommage des équipements](#annexe--nommage-des-équipements)). |
| état sans ordre On/Off — rien à piloter ; choisissez le type binary_sensor dans « Type HA », puis « Toujours » | L'équipement n'a qu'une commande d'état, sans commandes On/Off : il n'y a rien à piloter. Dans la colonne « Type HA » de cette commande, choisissez `binary_sensor`, puis réglez la publication sur « Toujours ». |

**2. Blocages tels que l'équipement est configuré**

| Cause affichée | Signification |
|---|---|
| types génériques non configurés dans Jeedom | Aucune commande n'a de type Jeedom (bouton « Ouvrir les types génériques »). |
| aucune commande Info/Action exploitable | L'équipement n'a pas de commande utilisable. |

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

Ces causes s'affichent avec un triangle d'avertissement, comptent comme **bloquées** et sont la cible du lien « Voir la première commande bloquée ».

| Cause affichée | Pour agir |
|---|---|
| aucun type Home Assistant identifié pour cette commande | Choisissez un autre type dans la colonne « Type HA », ou revenez à « auto ». |
| aucun type Home Assistant candidat à valider | Idem. |

**6. Commandes ignorées** (jamais comptées comme des défauts)

Ces commandes n'ont aucun équivalent dans Home Assistant ; il n'y a rien à faire. Elles sont repliées sous le tableau, pas dans des encarts.

| Cause | Signification |
|---|---|
| sans équivalent dans Home Assistant | Aucun type Home Assistant ne prend cette commande en charge. |
| type non couvert par la V1 du plugin | Aucun des types Jeedom de la commande n'est reconnu par le plugin (« V1 » désigne la version actuelle du plugin ; la liste des types pris en charge est donnée plus haut). |
| non pris en charge par le plugin | Le type Home Assistant demandé n'est pas ouvert par le plugin : la ligne repliée le précise. |

**7. Exclusions volontaires** (jamais comptées comme des problèmes)

| Cause (infobulle de la ligne « Exclue ») | Origine |
|---|---|
| exclu manuellement (équipement) | Réglage « Jamais » de l'équipement. |
| exclu manuellement (commande) | Réglage « Jamais » d'une entité. |
| exclu de Jeedom2HA (équipement dans la liste d’exclusions) | Réglage d'exclusion propre à l'équipement dans Jeedom (la clé `jeedom2ha_excluded` de sa configuration). Aucun bouton du plugin ne le pose. |
| exclu de Jeedom2HA (plugin source dans la liste d’exclusions) | Plugin coché dans la liste « Plugins exclus » de la configuration. |
| exclu de Jeedom2HA (pièce dans la liste d’exclusions) | Exclusion de la pièce, posée depuis sa carte ou son détail (voir [Exclure une pièce](#exclure-une-pièce)) ; reprend aussi les pièces de l'ancien champ « Pièces exclues » de la configuration. Sauf équipements exposés à HomeKit (actifs) : ils ne sont pas écartés par leur pièce. |

Dans la vue de travail, la **cause** d'un équipement « Exclu » est dite en clair, sans ouvrir la configuration : sur sa ligne de l'arbre (« par le plugin X », « par la pièce », « individuelle »), dans son détail (la phrase complète et l'endroit où agir) et, pour toute la pièce, dans la ligne « Exclus : » du détail de pièce (par exemple « 2 par le plugin X, 1 individuelle »). Le nom du plugin est celui affiché par Jeedom ; s'il est introuvable, c'est « par son plugin ». « par la pièce » correspond à l'exclusion de la pièce, « par le plugin » à la liste « Plugins exclus », « individuelle » au réglage « Jamais » ou au réglage propre à l'équipement dans Jeedom. Une seule cause est dite par équipement, dans l'ordre de priorité de Jeedom ; quand elle ne peut pas être déterminée (commandes exclues pour des raisons différentes), la ligne « Exclus : » compte l'équipement dans « autre ».

Pour reprendre un équipement exclu manuellement, choisissez « Automatique ». Pour une exclusion de plugin, décochez le plugin dans « Plugins exclus » puis cliquez sur le bouton situé sous les filtres ; pour une exclusion de pièce, utilisez « Ne plus exclure la pièce… ». Pour le réglage propre à l'équipement, retirez-le sur l'équipement dans Jeedom, puis lancez « Relire Jeedom ».

**8. État neutre**

| Cause | Signification |
|---|---|
| équipement désactivé dans Jeedom | Réactivez l'équipement dans Jeedom si vous le souhaitez. L'état « Désactivé » est en italique. |

**9. Incident à relire dans les journaux**

| Cause affichée | Signification |
|---|---|
| échec de publication MQTT au dernier sync | La publication vers le broker a échoué lors de la dernière synchronisation. Relancez une republication ; si le message persiste, consultez les journaux. |

Si un encart affiche un texte technique ou une liste de codes à la place d'une de ces phrases, téléchargez le diagnostic support et joignez-le à votre demande d'aide. Une cause inconnue du plugin (démon plus récent) classe la commande « Bloquée » : le code brut s'affiche en infobulle.

---

## Dépannage

| Symptôme | Où regarder | Action |
|---|---|---|
| Le démon ne démarre pas | Bandeau, indicateur « Démon » : « Arrêté » | Relancez l'installation des dépendances, puis démarrez le démon. Consultez le journal `jeedom2ha`. |
| Le broker n'est pas joignable | Indicateur « MQTT » : « Déconnecté » | Vérifiez les paramètres et utilisez « Tester la connexion » dans la configuration. |
| Les boutons d'action sont grisés | Ligne d'explication sous la barre de santé | Corrigez le démon ou MQTT : voir [la page principale](#les-actions-de-la-barre-de-santé). |
| Un équipement manque dans Home Assistant | Ouvrez sa pièce : badge de l'équipement et encart de cause | Appliquez la correction de la [famille de causes](#les-causes-de-blocage) correspondante. |
| Un réglage n'a pas d'effet dans Home Assistant | Badge « À appliquer » et bouton « Appliquer » dans l'en-tête de l'équipement | Cliquez sur « Appliquer », ou lancez « Relire Jeedom ». |
| Les états ne se mettent pas à jour | Bandeau de santé | Vérifiez le démon et MQTT, puis le journal `jeedom2ha`. |
| La barre de santé semble figée | Elle n'est lue qu'à l'ouverture de la page et après chaque action | Rechargez la page. |

Journaux : **Jeedom → Analyse → Logs → `jeedom2ha`**. Pour signaler un problème : [github.com/alexsahut/jeedom2ha/issues](https://github.com/alexsahut/jeedom2ha/issues).

---

## Annexes

### Annexe : pièces dans Home Assistant (zone suggérée)

Le plugin transmet à Home Assistant la **pièce Jeedom** de chaque équipement, comme « zone suggérée » (`suggested_area`). Si vous renommez la pièce dans Jeedom, le plugin met à jour cette information à la prochaine relecture de Jeedom.

Home Assistant n'utilise cette zone suggérée **qu'à la création** de l'appareil. Si vous déplacez ensuite un équipement d'une pièce à l'autre dans Jeedom, l'appareil reste dans son ancienne zone dans Home Assistant.

Pour le déplacer :

- **Option 1 — Supprimer de Home Assistant, puis relire Jeedom.** Utilisez « Supprimer de Home Assistant… » sur l'équipement, la pièce ou le parc, puis « Relire Jeedom » : la relecture lit la pièce actuelle et recrée les entités. (« Republier » seul ne suffit pas : il travaille sur ce que la dernière lecture complète a lu et ne relit pas Jeedom ; si vous venez de déplacer l'équipement, relisez Jeedom d'abord.) Les personnalisations faites dans Home Assistant (icônes, alias, historique, automatisations) peuvent être perdues : lisez l'avertissement de la confirmation.
- **Option 2 — Déplacement manuel.** Dans Home Assistant : **Paramètres → Appareils et services**, trouvez l'appareil et modifiez sa zone.

### Annexe : noms et identifiants dans Home Assistant

**Le nom de l'appareil est le nom de l'équipement Jeedom**, accents compris, identique pour toutes les entités de cet équipement. Le nom d'une entité suit une règle simple :

- **équipement à une seule entité** : l'entité porte le nom de l'équipement (Home Assistant l'affiche comme l'appareil) ;
- **équipement à plusieurs entités** (par exemple une prise avec des mesures de puissance et d'énergie) : l'**entité principale** (lumière, interrupteur, volet…) porte le **nom de l'équipement**, et Home Assistant l'affiche sous le nom de l'appareil ; les **autres entités** portent le nom de leur **commande**, que Home Assistant affiche à la suite du nom de l'appareil.

Un bouton de scénario porte le nom du scénario.

**Renommer dans Jeedom.** Le nouveau nom atteint Home Assistant à la **prochaine relecture de Jeedom**, au redémarrage du démon ou avec « Republier » : le plugin n'agit pas à l'enregistrement de l'équipement dans Jeedom. Pensez à lancer « Relire Jeedom » après un renommage.

**Ce que le plugin ne touche pas.** Un nom d'appareil ou d'entité, ou une pièce, que vous avez choisis vous-même dans Home Assistant font foi : le plugin ne les écrase pas. Les `entity_id` et noms des entités déjà créées ne changent pas non plus : la mise à jour ne fait évoluer que les noms affichés par défaut. Pour la pièce, voir l'annexe précédente : Home Assistant ne l'applique qu'à la création de l'appareil.

**`entity_id` des entités créées ou recréées.** Le `entity_id` est l'identifiant technique cité par les automatisations, scripts et cartes de tableau de bord. Pour toute entité **nouvelle ou recréée**, le plugin demande à Home Assistant un `entity_id` technique et stable, de la forme `<domaine>.jeedom2ha_<numéro de l'équipement>` (suivi du numéro de la commande pour les entités propres à une commande), par exemple `sensor.jeedom2ha_579_5795`. Home Assistant ne l'utilise qu'**à la création** de l'entité, et il remplace alors un `entity_id` que vous auriez personnalisé avant de supprimer l'entité.

Conséquences :

- une entité **supprimée puis recréée reprend son `entity_id` technique** : les automatisations, scripts et cartes qui le citent continuent de fonctionner, même si vous avez renommé l'équipement ;
- une entité dont l'`entity_id` actuel est issu d'un nom lisible le **change une fois** vers la forme technique si vous la recréez ;
- les cartes de tableau de bord citent l'`entity_id`, pas le nom affiché : seule la voix (Assist) s'appuie sur le nom.

### Annexe : nommage des équipements

Pour les **lumières**, les **volets** et les **prises/interrupteurs**, le plugin lit aussi le **nom de l'équipement**. Si le nom contient l'un des mots ci-dessous, l'équipement est écarté pour ce type, avec la cause « un mot du nom de l’équipement écarte ce type ».

Le mot doit apparaître **en entier** dans le nom (la casse n'a pas d'importance) : « Lampe tableau » n'est pas écarté à cause du « eau » de « tableau », mais « Lampe prise 2 » l'est à cause de « prise ».

| Pour le type | Mots qui l'écartent |
|---|---|
| **Lumière** (`light`) | chauffage, radiateur, thermostat, heater, chaudiere, chaudière, poele, poêle ; chauffe-eau, eau, water, cumulus, ballon ; piscine, pool, filtration, filtre, pompe ; prise, plug, socket ; fumée, smoke, incendie, feu, fire, alarme, sirene, sirène ; volet, store, cover, blind, shutter, garage, portail |
| **Prise / interrupteur** (`switch`) | lumière, lumiere, light, lampe, ampoule ; volet, store, cover, blind, shutter, portail, garage ; chauffage, radiateur, thermostat, heater ; fumée, smoke, alarme, sirene |
| **Volet** (`cover`) | lumière, lumiere, light, lampe, ampoule ; chauffage, radiateur, thermostat, heater ; prise, plug, socket ; fumée, smoke, alarme, sirene |

Que faire : renommez l'équipement dans Jeedom puis lancez « Relire Jeedom », ou essayez le réglage « Toujours » (voir ses conditions plus haut).

### Annexe : durée des actions

Les actions « Republier » et « Supprimer de Home Assistant » peuvent demander du temps sur un grand parc. Le démon ne s'arrête jamais en cours de route : c'est l'écran qui cesse d'attendre.

- Si l'action dépasse environ 60 secondes, le message suivant s'affiche : « L'action Home Assistant dure plus longtemps que prévu (plus de 60 s). Elle peut se poursuivre côté démon : actualisez la page dans un instant pour voir le résultat. » Attendez quelques secondes, rechargez la page : le bandeau et la pièce reflètent alors le résultat réel.
- Si le démon répond par une erreur immédiate : « Le démon a renvoyé une erreur pendant l'action Home Assistant — consultez les logs du plugin ». Consultez alors le journal `jeedom2ha`.
- Si le démon ne répond pas du tout : « Le démon ne répond pas (timeout API) — vérifiez qu'il est bien démarré ».
- Si une autre action est déjà en cours : « Une action Home Assistant est déjà en cours. » Attendez qu'elle se termine, rechargez la page, puis relancez.

### Annexe : historique des versions

Voir le [changelog](changelog.md).
