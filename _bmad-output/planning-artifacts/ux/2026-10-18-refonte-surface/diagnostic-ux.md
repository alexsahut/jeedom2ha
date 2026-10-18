# jeedom2ha — diagnostic UX/UI de la surface « Configuration Home Assistant par pièce »

Regard extérieur, à partir des 6 captures du 18/10 (01 à 06) et du code de l'écran (`jeedom2ha.php`, `jeedom2ha_mapping_surface.js`, `jeedom2ha_mapping_override.js`, `jeedom2ha.css`). Les noms réels des équipements ne sont pas repris ici : on parle de « l'équipement d'éclairage » (capture 03), « l'enceinte » (capture 04), « la prise multi-capteurs » (captures 05-06).

## En une phrase

Le fond est juste, mais l'écran **n'a pas de grammaire visuelle** : chaque information (état, compteur, cause, action) est rendue avec le même outil, une pastille ou un bouton gris de même taille. Il parle **trois vocabulaires différents** pour le même fait, et l'élément le plus lumineux de chaque vue est soit inutile (bandeau bleu), soit dangereux (bouton rouge « Supprimer »). L'œil ne sait pas où se poser, et la question « qu'est-ce qui part dans HA, et pourquoi pas le reste ? » demande de **lire** au lieu de **voir**.

---

## 1. Les problèmes, du plus grave au moins grave

### P1 — La promesse produit échoue dès le premier écran : la grille des pièces ne dit rien
- **Ce qu'on voit** (01, grille) : 28 cartes identiques avec une porte bleue, un nom et un total d'équipements entre parenthèses. Aucune n'indique ce qui est publié, bloqué ou exclu.
- **Pourquoi ça gêne** : le principe du produit est de savoir *sans chercher*. Ici, pour savoir s'il reste un problème dans la maison, il faut ouvrir les 25 pièces une par une. Le seul chiffre affiché (le total) est le moins utile des chiffres disponibles. C'est l'écran que le propriétaire voit le plus, et c'est celui qui l'informe le moins.
- **Correction** : chaque carte porte son **état** : une jauge publié/total (barre fine segmentée publié / à appliquer / bloqué / exclu), le chiffre « 9 / 22 publiés » et, s'il y en a, un repère orange « 2 bloqués ». En tête de grille, un résumé de la maison en une ligne (« 142 publiés · 7 bloqués · 3 à appliquer ») dont chaque chiffre est un **filtre** qui ouvre la liste des équipements concernés, toutes pièces confondues.

### P2 — Trois vérités qui se contredisent : badge, compteurs et tableau ne comptent pas la même chose
- **Ce qu'on voit** :
  - 03 (éclairage) : le badge dit « Sera publié… : **3** commande(s) prête(s) », le compteur dit « **3** publiées, 0 en attente, **1** non prise en charge » et le tableau a **4** lignes. Le badge oublie une commande ; le compteur la classe comme un défaut.
  - 05 (prise multi-capteurs) : badge « **7** prêtes », compteur « 7 publiées + **5** non prises en charge ». Les 5 sont invisibles depuis la liste.
  - 04 (enceinte) : le même fait porte trois noms : « **11 commande(s) bloquante(s)** » (badge), « **11 commandes non prises en charge** » (compteur), « **Ne sera pas publié — types génériques non configurés** » ×11 (tableau).
  - 02 : un équipement affiche « (désactivé dans Jeedom) » à côté de son nom, mais son badge dit « **Exclu** » et le compteur de la pièce annonce « **0** équipement désactivé ». Sur la même ligne, l'écran affirme deux choses qui se contredisent.
- **Pourquoi ça gêne** : le badge parle au **futur** (le plan : « sera publié », calculé depuis le diagnostic), le compteur parle au **présent** (la réalité : « publié dans HA », lu dans `published_in_ha`), et le tableau parle encore au futur. L'utilisateur ne sait pas lequel croire. Le code le confirme : `buildPublicationSummaryLabel` compte les diagnostics `ready`, `summarizeEquipmentCounters` compte la présence réelle, et l'exclusion l'emporte sur la désactivation dans `publicationSummaryState`. La doc (`compteurs.md`, § « Vérifier un chiffre ») doit expliquer comment rapprocher les chiffres à la main : c'est le symptôme.
- **Correction** : **un seul état par équipement**, calculé une seule fois, affiché partout avec le même mot et la même couleur (voir le glossaire au § 3). La règle de fusion du plan et de la réalité est simple : si le plan et la réalité concordent, on affiche la réalité (« Publié ») ; s'ils divergent, l'état est « **À appliquer** », et c'est le seul cas où le futur apparaît. « Désactivé » prime sur « Exclu » : c'est un fait de Jeedom, pas un choix fait dans le plugin.

### P3 — « Non pris en charge » met le normal et le corrigeable dans le même sac
- **Ce qu'on voit** (02, en-tête) : « 84 commandes non prises en charge » dans une seule pièce. Les lignes concernées (03, 05) sont « Rafraîchir », « Pinguer nœud », « Soigner nœud », « Tester nœud », « Reset consommation » : des commandes techniques qui n'ont **aucune raison** d'aller dans HA.
- **Pourquoi ça gêne** : c'est une **fausse alarme permanente**. Le plus gros chiffre de l'écran décrit un état normal, et noie les 11 commandes réellement bloquées de l'enceinte. `compteurs.md` l'admet : « ce compteur réunit des causes que vous pouvez corriger et d'autres que vous ne pouvez pas corriger ». Un compteur qui ne dit pas s'il faut agir ne sert à rien.
- **Correction** : deux catégories distinctes.
  - **Bloquée** (orange) : publiable si l'utilisateur fait quelque chose, avec une cause et une action.
  - **Ignorée** (gris, discret) : pas d'équivalent dans HA, rien à faire. Les commandes ignorées ne comptent pas comme un défaut, ne sont pas reprises dans les compteurs de tête, et sont **repliées** dans le tableau (« 5 commandes ignorées : Rafraîchir, Pinguer nœud… ▸ »).

### P4 — Couleurs : la palette du thème clair est plaquée sur le thème sombre, et le bleu ne veut rien dire
- **Ce qu'on voit** :
  - 02 : 22 pastilles pastel (`#dff0d8`, `#eee`, `#f2dede`, définies en dur dans `jeedom2ha.css`) sur un fond `#1e1e1e`. Ce sont les éléments **les plus lumineux** de la fenêtre, et ils sont répétés sur chaque ligne.
  - L'état « Exclu » (gris clair) est aussi lumineux que « Publié » : l'œil ne distingue pas « rien à faire » de « tout va bien ».
  - L'état « Bloqué » est rose pâle avec un texte brun `#8a6d3b` : contraste faible, et c'est pourtant le seul état qui demande une action.
  - Le bleu est partout sans porter de sens : le bandeau d'information, les 28 portes `#5b9bd5`, les liens `#337ab7`.
  - Textes en dur `#555` / `#666` / `#888` sur fond sombre (« Dernière synchro », adresse du broker, `LIGHT_STATE`, en-têtes du tableau) : contraste insuffisant, sous 3:1.
  - La surbrillance de la ligne ciblée est un jaune `#fff9c4` sur un thème sombre.
- **Pourquoi ça gêne** : la couleur doit coder l'**état**, et rien d'autre. Ici elle code le hasard des classes Bootstrap. En plus, la couleur ne suit pas le niveau d'urgence : ce qui demande une action est le moins visible.
- **Correction** : quatre teintes sémantiques, et c'est tout : **vert** = publié, **orange** = bloqué (action requise), **bleu** = à appliquer (en transit), **gris** = exclu, désactivé ou ignoré (choix ou neutre). Le rouge est réservé aux boutons destructifs, dans leur confirmation. Les teintes sont définies par des variables, avec un fond **translucide** (`rgba` / `color-mix`) qui fonctionne sur les thèmes clair et sombre, et non avec des pastels opaques. Ce qui est sain se met en retrait (pastille ou point coloré, texte normal) ; ce qui est bloqué ressort.

### P5 — Page principale : hiérarchie inversée
- **Ce qu'on voit** (01) :
  - L'élément le plus voyant est le **bandeau bleu** pleine largeur : une phrase de 40 mots en jargon (« prêt / bloquant + pourquoi », « type natif Jeedom (partagé Homebridge) »).
  - L'état de santé, qui est la vraie information, est une ligne de texte gris (`#555`) sans relief.
  - Les actions globales sont trois boutons gris de même poids, dont « **Supprimer de Home Assistant** » collé à « Republier », dans le même style.
  - La case « Pseudonymiser » et « Télécharger le diagnostic support » sont posées entre les actions et les pièces, en retrait (le `col-sm-12` ajoute un décalage) et collées au titre de section.
- **Pourquoi ça gêne** : l'ordre visuel ne suit pas l'ordre d'importance. L'action la plus destructrice du plugin (supprimer tout le parc de HA) a le même poids que l'action la plus anodine. Et le même geste est **rouge plein dans la modale** mais gris sur la page : le danger est signalé de façon incohérente. Le diagnostic support est un outil rare, il occupe une ligne entière en plein milieu.
- **Correction** :
  - Une **barre de santé** compacte : un point d'état et un libellé court par brique. On garde « MQTT connecté » et on relègue l'adresse `127.0.0.1:1883` dans une infobulle.
  - Les actions courantes à droite de la barre (« Republier tout », « Rescanner Jeedom »). Un menu « ⋯ » contient « Télécharger le diagnostic… » (la case de pseudonymisation passe dans la boîte de dialogue de téléchargement) et, séparée par un trait, « Supprimer tout de Home Assistant… » en rouge.
  - Le bandeau bleu disparaît ; une ligne d'aide discrète sous le titre, avec un lien vers la doc, suffit.

### P6 — Dans la fenêtre d'une pièce, le bouton le plus visible est « Supprimer la pièce »
- **Ce qu'on voit** (02-05) : « Republier la pièce » (gris) et « **Supprimer la pièce de Home Assistant** » (rouge plein) en tête de fenêtre, avant la liste.
- **Pourquoi ça gêne** : c'est la première chose que voit l'œil en ouvrant une pièce, alors qu'on l'utilise une fois par an. La confirmation existe, mais l'**affordance** dit « voici l'action principale de cet écran ».
- **Correction** : les actions de pièce passent à droite de l'en-tête. « Republier la pièce » reste un bouton discret ; « Supprimer de Home Assistant » passe dans un menu « ⋯ », en rouge **dans** le menu seulement.

### P7 — Les compteurs sont un mur de pastilles grises
- **Ce qu'on voit** (02, en-tête) : 8 pastilles `label-default` à texte long, toutes de même poids. Elles se répartissent sur 3 lignes irrégulières (la 5ᵉ, « 0 équipement désactivé dans Jeedom », se retrouve seule sur sa ligne). Les zéros sont affichés (« 0 équipement en attente d'application », « 0 commande en attente… »). Dans chaque équipement déplié, 3 pastilles de plus (03, 04, 05).
- **Pourquoi ça gêne** :
  - Les pastilles ressemblent à des boutons sans en être (**fausse affordance**).
  - Le chiffre, qui est la seule chose à lire, est noyé dans la phrase.
  - Les zéros font du **bruit** : ils prennent autant de place qu'un vrai signal.
  - Deux lignes (équipements, puis commandes) obligent à comparer des unités différentes.
- **Correction** : une **barre segmentée** (publié / à appliquer / bloqué / exclu-désactivé) avec une légende chiffrée : **chiffre en gros, mot court en petit**. Les zéros sont masqués. Les commandes ne sont pas comptées au niveau de la pièce : l'unité de décision de l'utilisateur est l'équipement. Le détail par commande ne vit que dans l'équipement déplié.

### P8 — La liste des équipements ne se lit pas d'un coup d'œil
- **Ce qu'on voit** (02) :
  - Le nom est à gauche, le badge est **à l'extrême droite**, à environ 600 px du nom.
  - Les badges ont une largeur variable, ce qui fait une colonne en dents de scie.
  - Chaque badge répète « dans Home Assistant » et finit par un point : 22 répétitions sur une liste de 22.
  - Les équipements exclus, bloqués et publiés sont mélangés dans l'ordre de Jeedom. Il n'y a ni tri, ni filtre, ni recherche.
- **Pourquoi ça gêne** : la loi de proximité est violée, l'œil fait des allers-retours sur toute la largeur et ne sait plus quel badge appartient à quelle ligne (aucun séparateur, lignes de 14 px). Avec 300 équipements, trouver « ce qui est bloqué » revient à tout lire.
- **Correction** :
  - **L'état passe en premier**, dans une colonne de largeur fixe juste avant le nom (point ou pastille courte : « Publié », « Bloqué », « Exclu »).
  - À droite, une colonne chiffrée « 3 / 4 commandes » et la cause courte quand l'équipement est bloqué.
  - Des **filtres** (Tous · Publiés · Bloqués · À appliquer · Exclus) avec leurs effectifs, et une recherche.
  - Un séparateur fin entre les lignes, des lignes de 32 px environ, et l'en-tête de l'équipement déplié qui reste visible (`position: sticky`).

### P9 — Cinq boutons d'action de même poids, et l'état courant n'est pas affiché
- **Ce qu'on voit** (03, 04) : « Exclure l'équipement », « Forcer l'équipement », « Revenir au mode automatique (équipement entier) », « Republier », « Supprimer de Home Assistant ». Les cinq sont en `btn-xs` sur une ligne ; la seule différence est le rouge du dernier. On ne sait pas lesquels sont grisés : sur thème sombre, l'état désactivé se voit mal.
- **Pourquoi ça gêne** :
  - Exclure / Forcer / Revenir sont les **trois positions d'un même réglage**, présentées comme trois actions. L'utilisateur doit déduire l'état actuel (automatique, forcé ou exclu) de la combinaison de boutons grisés.
  - « Forcer » est opaque : forcer quoi ?
  - « Republier » et « Supprimer » sont des actions de maintenance mises au même niveau que le réglage principal.
- **Correction** : un **contrôle segmenté** « Publication dans HA : `Automatique` | `Toujours` | `Jamais` » qui *montre* l'état et le change en un clic (infobulle sur « Toujours » : « publier même si le plugin a un doute »). Le bouton « **Appliquer** » (vert Jeedom) n'apparaît **que** quand un réglage attend. « Republier » et « Supprimer de HA… » passent dans un menu « ⋯ ».

### P10 — Équipement à plusieurs entités : 20 boutons avant le tableau, et une information en double
- **Ce qu'on voit** (05) : 5 lignes « switch — Commandes : Etat, On, Off », « sensor — Commandes : Puissance »…, chacune avec 3 boutons (« Exclure cette entité », « Forcer cette entité », « Revenir au mode automatique (cette entité) »). Avec les 5 boutons de l'équipement, cela fait **20 boutons** avant la première ligne du tableau. Le tableau redit ensuite « Sera publié : sensor » pour les mêmes commandes.
- **Pourquoi ça gêne** : l'information est **redondante** (deux listes des mêmes commandes) et la densité d'actions est écrasante, alors qu'on modifie rarement une entité. Les noms de domaines HA bruts (`switch`, `sensor`) en minuscules anglaises au milieu de phrases françaises n'aident pas.
- **Correction** : **regrouper le tableau par entité**. Chaque entité devient une ligne d'en-tête de groupe (« Interrupteur · *switch* » + son contrôle segmenté compact), suivie de ses commandes. La liste séparée disparaît. Quand il n'y a qu'une entité, l'en-tête de groupe disparaît aussi (déjà prévu par `entityActionsDuplicateEquipment`).

### P11 — Tableau des commandes : la colonne qui compte est la dernière, et 11 sélecteurs identiques font du bruit
- **Ce qu'on voit** (03-06) :
  - Colonnes `COMMANDE | TYPE JEEDOM | OVERRIDE HA | DIAGNOSTIC`. Le diagnostic (la réponse à la question de l'utilisateur) est à droite, après un sélecteur « — mode automatique — » répété sur **chaque** ligne. Le sélecteur est présent même sur « Rafraîchir », qui ne peut rien publier.
  - Le type Jeedom est en monospace MAJUSCULES `#555`, quasi illisible, et vaut souvent « — ».
  - Les en-têtes sont en MAJUSCULES grises.
- **Pourquoi ça gêne** : l'ordre des colonnes suit le modèle de données (source → réglage → résultat) et non la question posée (résultat d'abord). Un sélecteur identique sur toutes les lignes est du **bruit pur**, et il ne montre même pas le type choisi par le mode automatique : il faut aller le lire dans la colonne Diagnostic.
- **Correction** : colonnes `Commande | Dans Home Assistant | Type Jeedom | ✎`.
  - « Dans Home Assistant » affiche le résultat : ✓ *Lumière (light)*, ⚠ *cause courte*, ou — *ignorée*.
  - Le réglage est un lien discret « auto » / « forcé : sensor » qui ouvre le sélecteur au clic. On le surligne quand un type est imposé, pour que l'exception se voie.
  - Le type Jeedom passe en texte normal, plus petit, en gris lisible.
  - Les en-têtes passent en casse normale.

### P12 — La cause est répétée sur chaque ligne au lieu d'être dite une fois, avec une action
- **Ce qu'on voit** (04) : « Ne sera pas publié — types génériques non configurés dans Jeedom » ×11, en orange. Le lien « ↓ Voir la première commande bloquante » mène à la première de 11 lignes toutes bloquées. En 05 : « Ne sera pas publié — commande sans type Home Assistant applicable » ×5.
- **Pourquoi ça gêne** : la cause est au niveau de l'**équipement** (aucun type générique n'est posé), mais elle est rendue au niveau de la **commande**. Le rapport signal/bruit s'effondre, et aucun bouton ne permet de corriger le problème.
- **Correction** : quand plusieurs commandes partagent une cause, un **encart unique** en tête de l'équipement : « 11 commandes bloquées : types génériques non configurés dans Jeedom. [Ouvrir les types génériques] ». Les lignes concernées n'affichent plus qu'un ⚠ et le mot « Bloquée ». Le lien « première commande bloquante » est supprimé quand toutes les commandes sont bloquées.

### P13 — Vocabulaire : 20 termes pour 6 notions, du franglais et du jargon de développeur
- **Inventaire relevé** :
  - États et notions : publié / prête / projetable / pris en charge / couvert / bloquante / exclu / désactivé / forcé.
  - Réglages et actions : override / mode automatique / appliquer / republier / rescanner / topologie / Bridge.
  - Modèle HA et Jeedom : entité / type générique / type Jeedom / type HA.
  - Le même fait change de temps grammatical selon l'endroit (« Sera publié », « publiées dans HA »).
  - Les pluriels sont écrits « commande(s) prête(s) » au lieu d'être accordés.
  - Les badges finissent par un point, les boutons non.
  - Le même verbe change de forme : « Supprimer de Home Assistant » (parc, équipement) et « Supprimer la pièce de Home Assistant ».
  - Libellés de développeur : « Override en attente — pas encore republié vers Home Assistant », « Override HA », `LIGHT_STATE`, `switch`.
- **Pourquoi ça gêne** : la cohérence du vocabulaire est la signalétique de l'interface. Un utilisateur avancé finit par déduire que « prête » = « sera publiée » ≈ « publiée », mais chaque synonyme lui coûte un doute, et c'est exactement le « pas clair » qu'il ne sait pas nommer.
- **Correction** : le glossaire du § 3, appliqué partout (badge, compteur, tableau, boutons, toasts, doc).
  - Les pluriels sont accordés par le code : la fonction existe déjà pour les compteurs.
  - Pas de point final dans les étiquettes.
  - Le domaine HA s'affiche traduit, avec le terme technique en petit : « Lumière *light* ».
  - « Bridge » devient « Démon ». « Override HA » devient « Type HA » (réglage) et le mot « override » disparaît de l'écran.
  - « Rescanner la topologie Jeedom » devient « Relire Jeedom ».

### P14 — Une icône de porte identique pour 28 pièces, et une hiérarchie aplatie
- **Ce qu'on voit** (01) : la même porte bleue 28 fois. Les objets parents et enfants sont mis à plat dans la même grille. Des « pièces » techniques (supervision, tests, géolocalisation) sont mêlées aux vraies pièces.
- **Pourquoi ça gêne** : l'icône n'apporte aucune information, et le motif répété crée une texture qui fatigue (28 × le même pictogramme de 48 px). L'utilisateur a **déjà choisi** une icône et une couleur pour chaque objet dans Jeedom (`getDisplay('icon')`, `tagColor`) : l'écran les ignore. La hiérarchie (`parent_number`) est transmise au JS mais pas exploitée.
- **Correction** : reprendre l'icône et la couleur Jeedom de chaque objet (avec la porte en repli seulement), regrouper les cartes par objet parent (sous-titres « Rez-de-chaussée », « Étage », « Extérieur ») et réduire l'icône à 20-24 px : c'est l'état qui doit dominer la carte, pas le pictogramme.

### P15 — Défilement imbriqué et perte de contexte quand on déplie
- **Ce qu'on voit** (05-06) :
  - Le tableau a son propre défilement (`max-height: calc(100vh - 320px)`), à l'intérieur d'une modale qui défile aussi.
  - Plusieurs équipements peuvent être dépliés en même temps (`aria-multiselectable`).
  - Une fois l'équipement déplié, on ne voit plus ni son nom ni son état : la liste reprend sous le tableau sans transition visuelle (06).
- **Pourquoi ça gêne** : deux barres de défilement se disputent la molette. L'œil perd le rattachement « ce tableau appartient à quel équipement ? ». L'équipement déplié n'est pas visuellement « enfoncé » dans la liste : même fond, aucune bordure ou une bordure faible.
- **Correction** : un seul équipement déplié à la fois. Son corps est en retrait, sur un fond un cran plus clair avec un filet vert à gauche, et son en-tête reste collé (`sticky`) en haut de la zone de défilement. Le défilement interne du tableau est supprimé. Au-delà d'environ 40 équipements dans une pièce, on passe au maître-détail (direction C).

### En complément (moins graves)
- Le bandeau jaune « Aucun impact Homebridge » apparaît dans la modale : rassurant sur le fond, mais c'est un **troisième style de bandeau** (bleu, jaune, rouge) sur la même vue. Il faut le transformer en note discrète, une seule fois, dans l'aide.
- L'unité visuelle est cassée par le mélange de 3 tailles de boutons (`btn-sm`, `btn-xs`, liens) et de styles inline dans le PHP et le JS (`style="margin-left:8px"`…). Il faut les déplacer dans le CSS du plugin.
- La modale est fixée à `90 % / 1100 px` par du JS inline : elle ne profite pas d'un écran de 1440 px et elle est trop large pour sa propre liste.

---

## 2. Ce qui marche et qu'il faut garder

- **Le modèle pièce → équipement → commande**, calqué sur Homebridge : c'est le bon modèle mental pour un Jeedomien.
- **Un diagnostic par commande qui dit *pourquoi*** (« types génériques non configurés », « commande sans type HA applicable ») : c'est la vraie valeur ajoutée face à Homebridge. Il faut le garder et le **remonter** (P12), pas le supprimer.
- **Le texte n'est jamais remplacé par la couleur** (règle a11y déjà dans le CSS) : à conserver dans toutes les directions.
- **Les confirmations explicites** des suppressions (« l'historique, les dashboards, les automatisations… peuvent être impactés ; rien n'est recréé ») : elles sont excellentes.
- **Un bouton grisé porte sa propre cause en infobulle** : c'est une très bonne pratique. Il faut seulement la rendre visible sur le thème sombre.
- **« Appliquer » remplace « Republier » quand un réglage attend** : la bonne idée est déjà là, il manque un statut visuel au-dessus.
- **La barre de santé toujours visible** (démon, MQTT, dernière synchro, dernière opération) : le contenu est juste, seule la forme change.
- **Le chargement paresseux** par équipement et le message « Compteurs indisponibles… » quand la lecture échoue : c'est un comportement honnête.
- **L'usage des classes du core** (`objectDisplayCard`, `eqLogicThumbnailContainer`, `bootbox`) : l'écran reste « chez lui » dans Jeedom, et il faut continuer.

---

## 3. Glossaire proposé (un mot = une notion, partout)

| Niveau | État affiché | Couleur | Remplace | Sens |
|---|---|---|---|---|
| Équipement | **Publié** | vert | « Sera publié… N prête(s) », « publié dans HA » | Présent dans HA, conforme au réglage |
| Équipement | **À appliquer** | bleu | « en attente d'application », « Override en attente », « pas encore appliqué » | Réglage modifié, pas encore envoyé (bouton « Appliquer ») |
| Équipement | **Bloqué** | orange | « Ne sera pas publié : N bloquante(s) », « non pris en charge » | Rien n'est publiable tant que l'utilisateur ne corrige pas ; cause affichée |
| Équipement | **Exclu** | gris | « Exclu : ne sera pas publié… » | Choix de l'utilisateur |
| Équipement | **Désactivé** | gris, italique | « (désactivé dans Jeedom) » | Désactivé dans Jeedom ; prime sur Exclu |
| Équipement | **Rien à publier** | gris | « Aucune commande projetable… » | Aucune commande n'a d'équivalent HA |
| Commande | **Publiée** → *Lumière (light)* | vert | « Sera publié : light » | — |
| Commande | **Bloquée** → cause | orange | « Ne sera pas publié — … » (cause corrigeable) | — |
| Commande | **Ignorée** | gris, repliée | « commande sans type HA applicable », « non couverte » | Pas d'équivalent HA, rien à faire |
| Commande | **Exclue** | gris | — | — |

Un équipement qui a au moins une commande publiée et d'autres bloquées est « Publié » avec une **mention orange** « 2 bloquées ». On n'invente pas un 7ᵉ état « partiel ».

Réglage de publication : **Automatique / Toujours / Jamais** (remplace Revenir au mode automatique / Forcer / Exclure).
Réglage de type : **Type HA : auto (light)** / **Type HA : sensor (imposé)** (remplace « Override HA — mode automatique — »).
Actions : **Appliquer**, **Republier**, **Supprimer de Home Assistant…** (toujours la même forme, la portée est donnée par l'endroit où se trouve le bouton), **Relire Jeedom** (remplace « Rescanner la topologie Jeedom »).

---

## 4. Contraintes d'implémentation dans Jeedom 4.4+

1. **Ne jamais restyler les classes du core globalement** (`.label`, `.btn`, `.panel`, `.modal`, `.objectDisplayCard`). Tout passe par un préfixe `.j2ha-…` et sous `.modal-j2ha-room` ou `#j2ha_roomCards`, sinon on casse les autres plugins sur la même page de session (le CSS des plugins est chargé dans l'interface commune).
2. **Clair ET sombre.**
   - Pas de couleurs opaques en dur (`#dff0d8`, `#555`…). Il faut s'appuyer sur les variables CSS du thème du core (Jeedom 4.x expose des variables `--…-color` dans `core/themes/core2019_Light|Dark` ; les noms exacts sont **à vérifier sur la box** avant de coder, par exemple `--txt-color`, `--bg-modal-color`, `--al-success-color`, `--al-warning-color`).
   - Pour les fonds d'état, utiliser des **teintes translucides** (`rgba(…, .14)` ou `color-mix(in srgb, var(--j2ha-ok) 14%, transparent)`), qui marchent sur les deux fonds.
   - Si le core ne fournit pas la teinte voulue, définir des variables `--j2ha-*` sous un sélecteur de thème (Jeedom pose le thème sur `body` ; l'attribut ou la classe exacts sont à vérifier) avec un jeu clair et un jeu sombre.
   - `color-mix` est supporté par les navigateurs récents ; prévoir un repli `rgba` pour les vieux Safari et iPad muraux.
3. **Pas de police externe** : Jeedom a déjà sa police (Roboto selon le thème). On n'en ajoute pas ; on travaille la graisse et la taille. Pour les chiffres, on utilise `font-variant-numeric: tabular-nums`.
4. **Font Awesome 5** (`fas`) est fourni par le core, et les icônes `jeedom-*` et `icon_*` aussi. L'icône d'objet Jeedom est du HTML (`$object->getDisplay('icon')`) : il faut l'injecter échappée côté PHP, comme le fait le core dans ses vues.
5. **Bootbox / modales** : la largeur se règle par une classe CSS sur `.modal-j2ha-room .modal-dialog` (au lieu du `.css()` inline). Le `sticky` fonctionne à l'intérieur de `.modal-body` si c'est elle qui défile ; dans ce cas, retirer le `max-height` interne du tableau.
6. **Direction C (maître-détail)** : elle sort du motif « grille + modale » des plugins Jeedom. La page du plugin (`row-overflow` + `eqLogicThumbnailDisplay`) le permet, mais il faut gérer la hauteur (`calc(100vh - hauteur de la barre Jeedom)`), le mode « mobile » (Jeedom desktop sur tablette) et le retour arrière.
7. **Traduction** : tous les libellés passent par `{{…}}` (et `__()` en PHP) ; un changement de vocabulaire implique de mettre à jour les fichiers `i18n`, les tests Node qui vérifient les libellés (`test_story_20_3…`, `test_story_22_2…`) et la doc (`index.md`, `compteurs.md`). Il faut prévoir ce coût, qui est souvent plus gros que le CSS.
8. **Pas de logique nouvelle côté front pour l'état unique (P2)** : le démon expose déjà `published_in_ha`, `override_pending` et les diagnostics. La fusion « plan + réalité → un état » est une fonction pure, testable, à poser dans `jeedom2ha_mapping_override.js`, à côté de `publicationSummaryState`, qu'elle remplace.
9. **État des pièces sur la page principale (P1)** : aujourd'hui les arbres ne sont lus qu'à l'ouverture d'une pièce (un GET par équipement). Les jauges demandent soit une route agrégée côté démon (la plus propre : un appel, quelques octets par pièce), soit un chargement différé et mis en cache. **Ne pas lancer 300 GET** à l'ouverture de la page.

## 5. Vérifié sur la box le 18/10/2026 (ClaudeBox, lecture seule, navigateur intégré)

Faisabilité dans un plugin Jeedom : **oui pour A, B et C**. La page d'un plugin (`desktop/php/<plugin>.php`) est du HTML libre affiché dans la zone de contenu de Jeedom ; le plugin y charge son CSS et son JS par `include_file` (déjà le cas). Aucune règle écrite de « charte graphique » imposant la grille de vignettes n'a été trouvée dans la documentation développeur (doc.jeedom.com, `dev/plugin_template`) ; la grille + modale est une **convention**, pas une obligation. Point non vérifiable : l'appréciation de la revue humaine du Market à la demande de stable.

Ce que fournit l'environnement réel (Jeedom **4.6.1**, thème `core2019_Dark`) :
- thème posé sur `<body data-theme="core2019_Dark">` (et `core2019_Light`), avec `data-uimode="desktop"`, `data-device` ;
- variables CSS du core lisibles : `--bg-color` (« 25, 25, 25 », triplet sans `rgb()`), `--bg-modal-color`, `--txt-color`, `--link-color`, `--logo-primary-color` (vert Jeedom `rgb(150,201,39)`), `--al-success-color`, `--al-warning-color`, `--al-danger-color`, `--al-info-color`, `--eqTitle-color`, `--btn-default-color`, **`--border-radius: 0rem`** (le thème sombre est à angles droits : les maquettes arrondies doivent suivre `var(--border-radius)`) ;
- jQuery 3.6.0, Bootstrap 3, `bootbox`, `jeeDialog`, `jeedomUtils`, Font Awesome 5 local (`/3rdparty/font-awesome5`), icônes `jeedom-*` ; `color-mix()` supporté par le navigateur du Mac.

Contraintes à respecter (en plus du § 4) :
1. Rester dans la zone de contenu (barre Jeedom conservée) ; C se fait en pleine hauteur `calc(100vh - barre)` dans la page du plugin, sans toucher au core.
2. Couleurs : partir des variables du core (`--al-*`, `--logo-primary-color`, `--txt-color`, `--bg-*`), compléter par des `--j2ha-*` définies sous `body[data-theme*="Dark"]` / `body[data-theme*="Light"]` ; repli `rgba()` si `color-mix` absent.
3. Tester les deux thèmes, la bascule automatique jour/nuit du core, et la compatibilité annoncée **Jeedom 4.4** (les noms de variables sont relevés sur 4.6.1 : à recontrôler sur 4.4, par exemple sur la VM 122 de démo ou une VM vierge).
4. Tablette / iPad mural en mode desktop : C doit replier le panneau gauche sous une largeur seuil.
5. Performance : jauges de B et arbre de C = **une route agrégée côté démon** (pas 300 lectures).

## 6. Décision d'Alex (18/10/2026 18:15)

« si tu valides que c'est possible alors je valide A+B+C ». ClaudeBox a validé la faisabilité (§ 5). Lecture retenue pour rendre les trois cohérentes (B et C se recouvrent) :
- **A = socle** partout : état unique par équipement (Publié / À appliquer / Bloqué / Exclu / Désactivé ; « Désactivé » prime sur « Exclu »), commandes ignorées séparées des bloquées, vocabulaire unique (glossaire § 3), palette sémantique sur les variables du thème, réglage « Automatique / Toujours / Jamais », actions rares dans un menu « ⋯ », tableau des commandes regroupé par entité, cause dite une fois avec action.
- **B = page principale** : santé + actions, jauge maison avec filtres globaux (publiés / bloqués / à appliquer / exclus, toutes pièces), cartes de pièce avec jauge et repères.
- **C = vue de travail** : un clic sur une carte (ou un filtre global) ouvre la vue maître-détail en pleine hauteur (arbre pièces → équipements filtrable à gauche, détail de la pièce ou de l'équipement à droite) **à la place de la fenêtre modale**, avec retour à la page principale ; panneau gauche repliable sur tablette.
- Ordre de livraison proposé : A (corrige les contradictions, prérequis), puis route agrégée + B, puis C.
