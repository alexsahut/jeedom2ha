# Premiers pas avec jeedom2ha

**jeedom2ha publie vos équipements Jeedom dans Home Assistant.** Jeedom reste la source : rien n'y est modifié.

Cette page suffit pour démarrer. La [documentation complète](index.md) détaille chaque écran.

---

## Ce qu'il vous faut

- Jeedom 4.5 ou plus récent, sur Debian 12, avec le plugin installé et ses dépendances (page du plugin, bloc « Dépendances »).
- Le **broker MQTT** que Home Assistant utilise déjà : le serveur de messages que Home Assistant écoute aussi (par exemple celui du plugin MQTT Manager de Jeedom, ou Mosquitto).
- Dans Home Assistant, l'intégration **MQTT**, avec la découverte activée (c'est son réglage par défaut).

## Avant de commencer : trois règles à connaître

> **1. Un seul broker MQTT, partagé avec Home Assistant, et une seule installation jeedom2ha par broker.** jeedom2ha et Home Assistant doivent utiliser le même broker. Si une deuxième installation jeedom2ha (une box de test, une sauvegarde restaurée sur une autre machine) se branche sur ce même broker, chacune retire les boutons de scénario de l'autre. Branchez une box de test sur un autre broker.
>
> **2. Certains mots du nom d'un équipement écartent un type.** Le plugin lit aussi le nom de l'équipement. Si le nom contient l'un de ces mots, en entier (majuscules ou non), le type correspondant est écarté et l'équipement est **Bloqué** :
>
> - pour une **lumière** : chauffage, radiateur, thermostat, heater, chaudiere, chaudière, poele, poêle, chauffe-eau, eau, water, cumulus, ballon, piscine, pool, filtration, filtre, pompe, prise, plug, socket, fumée, smoke, incendie, feu, fire, alarme, sirene, sirène, volet, store, cover, blind, shutter, garage, portail ;
> - pour une **prise ou un interrupteur** : lumière, lumiere, light, lampe, ampoule, volet, store, cover, blind, shutter, portail, garage, chauffage, radiateur, thermostat, heater, fumée, smoke, alarme, sirene ;
> - pour un **volet** : lumière, lumiere, light, lampe, ampoule, chauffage, radiateur, thermostat, heater, prise, plug, socket, fumée, smoke, alarme, sirene.
>
> « Lumière garage », « Lampe salle d'eau » ou « Éclairage piscine » ne sont donc pas publiés comme lumières ; « Lampe tableau » l'est (« eau » n'y est pas un mot entier). Que faire : sa fiche propose **« Publier quand même »** (la publication de l'équipement passe sur **« Toujours »**, puis **« Appliquer »** l'envoie), ou **« Renommer l'équipement dans Jeedom, puis Relire Jeedom »** (retirez ce mot du nom, puis cliquez sur « Relire Jeedom »). Corriger le type ne suffit pas dans ce cas : le nom continue d'écarter le type.
>
> **3. La pièce dans Home Assistant est fixée à la création.** Home Assistant range chaque appareil dans la zone de sa pièce Jeedom **une seule fois**, quand il le découvre. Déplacer ensuite l'équipement dans une autre pièce de Jeedom ne le déplace pas dans Home Assistant : changez sa zone dans Home Assistant (la [documentation complète](index.md#annexe--pièces-dans-home-assistant-zone-suggérée) donne les deux façons de faire).

## Le guide de démarrage, en quatre étapes

Ouvrez la page du plugin (**Plugins › Communication › jeedom2ha**). Tant que rien n'est publié, elle affiche **« Bienvenue dans jeedom2ha »** et quatre étapes. Chaque étape se coche seule quand elle est faite ; une étape pas encore atteinte affiche « Terminez l'étape N d'abord. ».

1. **« Connecter le broker MQTT »** — Cliquez sur **« Ouvrir la configuration MQTT »**. Dans la configuration du plugin, saisissez l'adresse du broker (« Hôte MQTT »), son port (1883 en général, 8883 avec TLS), l'utilisateur et le mot de passe, puis cliquez sur **« Tester, enregistrer et redémarrer le démon »**. Trois coches s'allument l'une après l'autre : « Connexion testée », « Réglages enregistrés », « Démon redémarré ». Si le test échoue, rien n'est enregistré et le message dit quoi vérifier. Revenez ensuite par **« Retour à la page du plugin »**.
2. **« Vérifier que Home Assistant écoute »** — Dans Home Assistant, ouvrez **Paramètres › Appareils et services › MQTT**. L'appareil « Jeedom (jeedom2ha) » doit y apparaître, avec l'entité « État du pont ». Cliquez sur **« Je l'ai vu »**. Sinon, **« Je ne le vois pas »** affiche les trois causes habituelles : l'intégration MQTT n'est pas installée, Home Assistant utilise un autre broker, ou la découverte MQTT est désactivée.
3. **« Choisir ce qui est publié »** — Par défaut, tout ce que le plugin reconnaît est publié. Cliquez sur **« Tout publier (recommandé) »**, ou sur **« Choisir… »** pour retirer d'emblée un plugin, une pièce ou un équipement. Vous pourrez changer d'avis à tout moment.
4. **« Publier dans Home Assistant »** — Le plugin lit Jeedom et publie ce qu'il reconnaît. Un écran de fin dit combien d'équipements sont dans Home Assistant, donne quelques exemples nommés et propose **« Voir ma maison »** ; si des équipements ne peuvent pas être publiés, un second bouton les liste.

Le guide se ferme par **« Fermer »**. **« Ne plus afficher ce guide »** l'empêche de revenir seul ; il reste disponible dans le menu **« ⋯ » (« Autres actions ») › « Guide de démarrage »**.

## Où trouver vos équipements dans Home Assistant

Dans Home Assistant, ouvrez **Paramètres › Appareils et services › MQTT** : c'est le même chemin qu'à l'étape 2 du guide. Chaque équipement Jeedom publié y est un appareil, sous **son nom Jeedom**, rangé dans la zone qui porte le nom de sa pièce Jeedom (« zone » dans Home Assistant, « objet » dans Jeedom). Tous sont « connectés via » l'appareil « Jeedom (jeedom2ha) ».

![Les appareils publiés par jeedom2ha dans Home Assistant, avec leur pièce](images/home-assistant-appareils.png)

Dans la page du plugin, la fiche d'un équipement rappelle ce chemin (**« Où le trouver dans Home Assistant ? »**) et donne l'identifiant de chaque entité, par exemple `light.jeedom2ha_142` (**« copier »** le met dans le presse-papiers). Cet identifiant est technique et stable : il ne change pas si vous renommez l'équipement. Une **entité** est une ligne pilotable ou lisible dans Home Assistant : un équipement Jeedom peut en donner plusieurs (une prise et sa consommation, par exemple).

## Trois questions, pour chaque équipement

La page du plugin répond toujours aux mêmes trois questions, pour toute la maison, pour une pièce et pour un équipement.

**1. Qu'est-ce qui est publié ?** Chaque équipement porte un seul mot : **Publié**, **À appliquer**, **Bloqué**, **Exclu**, **Désactivé** ou **Rien à publier**. Le lien « Que veulent dire ces mots ? », sous les chiffres de la maison, les explique en une ligne chacun. Dans la fiche d'un équipement, les deux côtés sont face à face : **« Dans Jeedom »** (nom, plugin, pièce, commandes) et **« Dans Home Assistant »** (les entités, leur type en français, par exemple « Lumière (light) », et **Pilotable** ou **Lecture seule**).

**2. Pourquoi pas ?** Un équipement non publié dit pourquoi, en clair, dans sa fiche : ce qui se passe, pourquoi, et comment faire, avec le bouton qui corrige (souvent **« Ouvrir les types génériques »** ou **« Corriger le type… »**). Un équipement publié mais qui pourrait faire mieux (en lecture seule alors que Jeedom a des ordres, par exemple) porte un **Conseil**, construit de la même façon. Le bloc **« À faire »** de la page du plugin rassemble ce qui a besoin de vous.

**3. Comment changer ?** Chaque fiche propose l'action qui convient :

- **« Ouvrir les types génériques »** : la voie durable. Dans Jeedom, chaque commande peut porter un « type générique » qui dit son rôle (par exemple « Lumière État », « Lumière Bouton On ») ; sans lui, le plugin ne peut rien en déduire. Corrigez-le dans Jeedom, puis cliquez sur **« Relire Jeedom »**.
- **« Ouvrir l'équipement dans Jeedom »** : pour compléter ses commandes dans Jeedom, puis **« Relire Jeedom »**.
- **« Corriger le type… »** : pour régler ici ce que voit Home Assistant, sans toucher à Jeedom (voir plus bas).
- **« Ouvrir la configuration du plugin »** : quand la cause est un réglage du plugin (un plugin exclu, par exemple).
- **« Publier quand même »** : quand le plugin hésite, ou quand le nom contredit les types. L'équipement passe sur « Toujours », puis « Appliquer » le publie.
- **« Renommer l'équipement dans Jeedom, puis Relire Jeedom »** : quand un mot du nom écarte le type voulu.
- **« Republier »** : quand l'envoi à Home Assistant a échoué.
- Le réglage **« Automatique | Toujours | Jamais »** de l'équipement : laisser le plugin décider, publier même si le plugin hésite, ou ne jamais le publier. Ce réglage est enregistré, puis attend : l'équipement passe « À appliquer », et le bouton **« Appliquer »** de sa fiche l'envoie à Home Assistant.

## Relire Jeedom ou Republier tout ?

Les deux boutons de la barre d'état, en haut de la page du plugin :

- **« Relire Jeedom »** : *j'ai changé quelque chose dans Jeedom* (un équipement, un type générique, un nom, une pièce). Le plugin relit Jeedom, puis met Home Assistant à jour, et applique au passage les réglages en attente.
- **« Republier tout »** : *Home Assistant a perdu ses appareils* (après un redémarrage du broker, par exemple). Le plugin renvoie à Home Assistant ce qui est déjà publié, sans relire Jeedom.

Une modification faite dans Jeedom, même sur un seul équipement, demande toujours « Relire Jeedom » : les gestes « Republier » ne relisent pas Jeedom. Pour renvoyer seulement un équipement ou une pièce, leur menu « ⋯ » propose **« Republier »** et **« Republier la pièce »**.

## Corriger un type

Quand le plugin hésite (une lampe branchée sur une prise, par exemple) ou se trompe de type :

1. Ouvrez l'équipement (cliquez sur sa pièce, puis sur son nom), et cliquez sur **« Corriger le type… »** dans sa fiche, ou sur le lien de la colonne **« Type HA »** de la commande (il affiche « Automatique » tant que le plugin choisit seul).
2. Le panneau « Type dans Home Assistant de « Nom » » dit à quelles commandes le choix s'applique (« Ce choix vaut pour les commandes : … ») : le type choisi vaut pour toute l'entité. Il rappelle que le plus durable est de corriger les types génériques dans Jeedom, puis propose les types possibles en français (« Automatique », « Lumière (light) », « Interrupteur (switch) »…). Les types qui ne peuvent pas convenir sont repliés sous « Types impossibles pour cet équipement (N) ».
3. Choisissez un type : un aperçu **« Avant » / « Après »** montre ce que deviendra l'équipement dans Home Assistant, et prévient si l'identifiant change (les automatisations qui utilisent l'ancien seront à reprendre). Rien n'est enregistré à ce stade.
4. Cliquez sur **« Enregistrer et publier »**. Un bandeau confirme le changement et propose **« Annuler »** pendant quelques secondes. Si le plugin hésite sur cet équipement, changer le type ne suffit pas : l'aperçu le dit et propose **« Publier quand même »**, qui garde le type choisi et ajoute « Toujours » ; le bouton devient alors **« Enregistrer et publier quand même »**.

La colonne « Type HA » affiche alors « Personnalisé : Lumière (light) ». Pour revenir au choix du plugin, rouvrez le panneau et choisissez « Automatique ».

## Choisir ce qui est publié

Tout ce que le plugin reconnaît est publié par défaut. Pour retirer de Home Assistant un plugin, une pièce ou un équipement, au même endroit, cliquez sur **« Choisir ce qui est publié… »** (à droite du titre de la maison, ou dans le menu « ⋯ ») :

1. Choisissez **« Par pièce »** ou **« Par plugin »**, puis décochez ce que vous ne voulez pas voir dans Home Assistant. Chaque ligne dit ce qui arrivera.
2. Le pied compte en direct les équipements et les entités qui seront retirés de Home Assistant, et ceux qui y reviendront.
3. Cliquez sur le bouton d'application, qui dit ce qu'il fera (par exemple « Appliquer — retirer N entités », en rouge). Le plugin relit Jeedom une seule fois, et un bandeau propose **« Annuler »** pendant quelques secondes.

Un équipement est publié s'il n'est exclu ni lui-même, ni par sa pièce, ni par son plugin. **« Non exclu » ne veut pas dire « publié »** : un équipement non exclu peut rester hors de Home Assistant parce qu'il est désactivé dans Jeedom, bloqué ou sans rien à publier ; son badge sur la page du plugin dit lequel. Pour un seul équipement, le réglage **« Jamais »** de sa fiche, suivi de **« Appliquer »**, fait la même chose ; pour une pièce, son menu « ⋯ » propose aussi **« Exclure la pièce… »**.

## Quelque chose ne va pas ? « Vérifier l'installation… »

Dans le menu **« ⋯ » (« Autres actions »)** de la barre d'état, **« Vérifier l'installation… »** passe les contrôles dans l'ordre : le démon tourne, le broker MQTT répond, Home Assistant s'est signalé sur le broker, la dernière relecture a réussi, les équipements bloqués. Chaque contrôle dit « OK », « À corriger », « À vérifier » ou « En attente ». Seul un point « À corriger » arrête la liste (les suivants restent « En attente ») ; un point « À vérifier » vous demande un contrôle, sans arrêter la liste. Chaque point à reprendre propose le bouton qui le corrige.

Pour demander de l'aide, la partie **« Pour le support »** de la même boîte télécharge un fichier qui décrit votre installation (**« Télécharger le diagnostic support »**), à joindre à votre message sur le forum ; la case **« Pseudonymiser les noms d'équipements »** remplace vos noms par des alias.

Pour aller plus loin : la [documentation complète](index.md).
