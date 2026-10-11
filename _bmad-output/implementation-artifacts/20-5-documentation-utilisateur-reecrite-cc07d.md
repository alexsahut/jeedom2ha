# Story 20.5 : Documentation utilisateur réécrite (CC-07 d)

Status: done

> **Avancement (2026-10-11) : Tasks 1 à 4, 6 et 6.1 faites.** Documentation livrée sous `docs/fr_FR/` ; table de traçabilité en annexe (`20-5-tracabilite-documentation.md`). Relecture ClaudeBox et relecture indépendante, deux rondes (PR #232), environ 150 affirmations vérifiées dans le code ; contrôle des noms réels par ClaudeBox.

> **Statut : `done` (2026-10-11).** Alexandre a tranché Q1=A, Q2=A, Q3=B, Q4=A (Journal des décisions) ; le plan de la Task 2.1 est retenu tel quel et les décisions de rédaction de la Task 2.4 sont prises. Documentation livrée sous `docs/fr_FR/` (PR #232), relue en deux rondes par ClaudeBox et par une relecture indépendante : environ 150 affirmations vérifiées dans le code, aucun nom réel (contrôle par empreintes), liens et ancres valides. Ferme CC-07 d. La story « compteurs » n'est pas encore livrée : le bloc `compteurs` décrit la sémantique actuelle avec son bandeau d'obsolescence.

## Story

En tant qu'utilisateur du plugin qui vient d'installer jeedom2ha (ou qui le met à jour),
je veux une documentation qui décrit l'écran tel qu'il est réellement, avec les mots que l'écran emploie, et qui dit ce que le plugin publie ou ne publie pas dans Home Assistant et pourquoi,
afin de configurer mon installation, de comprendre l'état affiché et de corriger un équipement non publié sans lire le code ni consulter les journaux.

**Parcours : documentaire.** Pas d'interface à livrer : ni gate 20-0, ni déploiement sur la box, ni `ready-for-UX-validation`. En revanche la fidélité de chaque affirmation à l'interface livrée est vérifiée en lecture du code (AC1) ; la relecture ClaudeBox est requise avant fusion.

## Contexte et périmètre

- **Source** : `_bmad-output/planning-artifacts/epics-projection-engine.md`, Epic 20, « Story 20.5 — Documentation utilisateur réécrite (CC-07 d). Décrit l'interface finale livrée par l'epic. Dépend de 20.1 à 20.4. » Le même fichier déclare « CC-07 d (documentation utilisateur) fermé par Story 20.5 » et fixe le gate epic-level « documentation utilisateur réécrite et alignée sur l'interface livrée ». `sprint-change-proposal-2026-10-01-etape-4-interface.md` (ligne 41) précise : « décrit l'interface finale, pas une interface intermédiaire ».
- **Ferme CC-07 d.**
- **Référence de vérité : le code de `main` au SHA `3b120d3`** (clôture de 20.3), pas les fichiers de story. Les stories 20.1 à 20.4 racontent l'historique du développement (ajouts, retraits, reprises de revue) ; l'état final se lit dans `desktop/php/jeedom2ha.php`, `desktop/js/jeedom2ha.js`, `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/js/jeedom2ha_mapping_override.js`, `plugin_info/configuration.php` et les routes du démon (`resources/daemon/transport/http_server.py:4574-4592`). Au moment du `dev-story`, ces faits sont à rejouer au SHA courant (Task 1).
- **Dans le périmètre :**
  - inventaire de la documentation existante et classement à jour / périmé / manquant (section « Inventaire », livrée dans cette story) ;
  - réécriture de la documentation utilisateur pour l'interface finale de l'epic 20 : page principale, bandeau de santé, cartes de pièce, modale de pièce et ses compteurs, surface pièce → équipement → commande, actions exclure / forcer / revenir au mode automatique / appliquer, republier, supprimer puis recréer, rescan, export de diagnostic, configuration ;
  - un texte « ce qui est publié, ce qui ne l'est pas, et pourquoi », dans les mots de l'interface ;
  - mise à jour des changelogs (entrée datée) ;
  - emplacement de captures d'écran prévu dans le plan, **sans les réaliser** (voir Q3).
- **Hors périmètre :**
  - tout changement de code, de test, de libellé d'interface ou de comportement ; si la rédaction révèle un libellé d'interface faux ou trompeur, il est consigné comme constat (section « Constats pour le backlog »), pas corrigé ici ;
  - la story « compteurs » prévue après celle-ci (voir « Section compteurs isolée ») ;
  - la documentation développeur (`docs/git-strategy.md`, `docs/ci.md`, `docs/dev-deploy.md`, `docs/delegation-claude-cloud.md`, `docs/operations/*`) : elle n'est pas de la documentation utilisateur ;
  - toute prise de capture d'écran, tout accès à la box Jeedom ou à Home Assistant ;
  - les décisions sur Q1 à Q4.

## Inventaire de la documentation existante (relevé au SHA `3b120d3`)

| Fichier | Rôle | Constat global |
|---|---|---|
| `docs/fr_FR/index.md` (318 lignes) | Documentation utilisateur, cible du lien « documentation » de `plugin_info/info.json` (`docs/fr_FR/index.md` sur `main`) | **Partiellement périmé** : description de l'interface (Diagnostic, onglet HA, périmètre V1) antérieure à l'epic 20 ; plusieurs sections hors sujet pour un utilisateur. |
| `docs/index.md` (16 lignes) | Index du dossier `docs/` | **Périmé sur une ligne** : décrit `fr_FR/index.md` comme « Jeedom plugin template documentation » (héritage du gabarit) ; lui-même rédigé en anglais, alors que le reste est en français. Mélange documentation de développement et documentation utilisateur. |
| `docs/fr_FR/changelog.md` (58 lignes) | Changelog des versions stables, cible du lien « changelog » de `info.json` | **Incomplet** : dernière entrée 2026-09-27 (v0.3.0). Aucune entrée pour l'interface livrée par l'epic 20 (surface par pièce, exclusion/forçage, compteurs, rescan, suppression du parc global et du gabarit). |
| `docs/fr_FR/changelog_beta.md` (26 lignes) | Changelog des versions beta | **Périmé** : intitulé « Changelog plugin template - beta », contenu entièrement hérité du gabarit (2020-2022), aucune entrée jeedom2ha. |
| `README.md` (racine) | Présentation GitHub | À relire en Task 1 : non inventorié ligne à ligne ici ; seul le recoupement des libellés (Diagnostic, onglet HA) est attendu. |
| `docs/operations/` | Délégations, parité 19.1 | Documentation d'exploitation interne, **hors périmètre** (aucun contenu à destination de l'utilisateur final). |
| `docs/cadrage_plugin_jeedom_ha_bmad.md`, `docs/release-market.md` | Cadrage produit, procédure de release | Hors périmètre ; `release-market.md` peut dicter où la doc du Market est lue (à lire en Task 1, voir Q4). |

### Détail de `docs/fr_FR/index.md` : à jour / périmé / manquant

**Périmé (à réécrire ou retirer), avec la raison :**

| # | Passage actuel | Pourquoi c'est périmé (état du code au SHA `3b120d3`) |
|---|---|---|
| P1 | Sommaire et sections « Première synchronisation », « Diagnostic » : bouton **« Diagnostic »** de la page principale, tableau Statut / Raison / Suggestion | Le bouton « Diagnostic » et la modale « Diagnostic de Couverture » ont été **supprimés par 20.3** (décision d'Alex 2026-10-01). Le bloc « Gestion » ne contient plus que « Configuration » (`jeedom2ha.php:62-65`). Le diagnostic vit désormais **dans la surface par pièce** (colonne Diagnostic par commande, badge de synthèse par équipement) et dans « Télécharger le diagnostic support ». Statut « publié / non publié / ambigu » : ces trois mots ne sont plus ceux de l'écran. |
| P2 | Section « Configuration du mapping par équipement (overrides) » : « ouvrez sa fiche dans Jeedom : un onglet **HA / jeedom2ha** y présente le mapping commande par commande » | Cet onglet a été **retiré par 16.8** (`jeedom2ha.php:271-273`, « point d'entrée inatteignable », aucun équipement jeedom2ha dans la pratique). Le point d'entrée réel est : page du plugin → carte de pièce → modale de pièce → équipement → commandes. |
| P3 | Même section : panneau dépliable par commande à **trois colonnes « Natif / Override / Diagnostic »** | Le tableau réel a **quatre colonnes : « Commande », « Type Jeedom », « Override HA », « Diagnostic »** (`jeedom2ha_mapping_surface.js:971-974`), une ligne par commande, sans panneau par commande. |
| P4 | Même section : « Un override compatible est accepté… sans bouton Enregistrer » | Exact pour l'override de **type** (vérification instantanée puis enregistrement automatique si valide), mais **incomplet et trompeur** : un override enregistré n'est **pas** publié immédiatement ; il porte le badge « Override en attente — pas encore republié vers Home Assistant » et attend « Appliquer » (équipement) ou le rescan. |
| P5 | Même section : « Revenir au mode automatique » décrit « par commande » et « par équipement » | Le bouton **« Revenir au mode automatique »** existe à deux endroits dans l'écran réel (équipement et entité Home Assistant) avec des portées et des états grisés précis (voir F6) ; le lien « Revenir au type automatique » (icône) de la ligne de commande ne retire que l'override de **type**. Le texte actuel ne distingue pas override de type et override de publication. |
| P6 | Même section : « **Export / import de profils d'overrides** » (schéma versionné, anonymisation) | Aucun point d'entrée dans l'interface ni route HTTP du démon (`http_server.py:4574-4592`, relais `core/ajax/jeedom2ha.ajax.php`) ne propose export ou import de profil ; le code existe seulement dans `resources/daemon/mapping/overrides.py` et ses tests (story 16.7). Une documentation utilisateur ne peut pas décrire une fonction inatteignable. À retirer, ou à garder avec la mention « non disponible dans l'interface » (décision de rédaction à valider, voir Task 2.4). |
| P7 | « Périmètre V1 » : tableau limité à lumières, volets, prises ; « **Hors périmètre V1 : capteurs numériques (sensor), capteurs binaires (binary_sensor), thermostats, scénarios** » ; encadré « Les capteurs figurent dans le diagnostic… mais ne sont pas publiés » | Le périmètre produit du démon couvre **huit types** : `light`, `cover`, `switch`, `sensor`, `binary_sensor`, `button`, `climate`, `alarm_control_panel` (`validation/ha_component_registry.py:70`, `mapping/registry.py:23-34`), et la liste proposée dans la colonne « Override HA » est la même (`HA_ENTITY_TYPE_OPTIONS`, `jeedom2ha_mapping_override.js:18-27`). Le tableau et l'encadré sont **faux**. La rédaction doit s'appuyer sur ce que le plugin publie réellement, à rejouer en Task 1 (et non sur ce paragraphe). |
| P8 | « Configuration → Filtrage & Publication » : bouton **« Appliquer et Rescanner »**, options en tableau | Le bouton réel s'appelle **« Appliquer les filtres et rescanner »** (`plugin_info/configuration.php:150`). Libellé du champ « Politique de publication » : les deux valeurs réelles sont « Publier les équipements sûrs et probables (recommandé) » et « Publier uniquement les équipements sûrs » (l. 141-142), pas `Sûr + Probable` / `Sûr uniquement`. Le bouton « Récupérer depuis MQTT Manager » et le lien « Réinitialiser le formulaire » (l. 32, 36) ne sont pas décrits. |
| P9 | « Première synchronisation » : étapes 3 et « Après un redémarrage du broker… relancez un rescan depuis la configuration » | Un **rescan est maintenant sur la page principale** (« Rescanner la topologie Jeedom », story 20.4). La configuration garde « Appliquer les filtres et rescanner ». Les deux chemins sont à expliquer et à distinguer. |
| P10 | « Troubleshooting » : « Diagnostic → colonne Raison », « Vérifier statut démon + logs » | « Diagnostic → colonne Raison » renvoie à une modale supprimée. À remplacer par la lecture du bandeau de santé et de la surface par pièce. |
| P11 | « Durée des actions **“Publier” / “Supprimer”** » : « Les actions groupées (Publier / Supprimer une sélection) » | Les libellés réels sont **« Republier »** et **« Supprimer puis recréer »**, sans notion de « sélection » ; les portées sont le parc, une pièce, un équipement. Les messages cités sont, eux, toujours exacts (`core/php/jeedom2ha_action_budget.php:65,80,169`) ; les volumes chiffrés (≈250, ≈155, ≈510 équipements) sont une documentation d'exploitation que l'utilisateur ne peut pas vérifier : à conserver en annexe ou à condenser (décision de rédaction, Task 2.4). |
| P12 | « Comportement des pièces (suggested_area) », option 1 : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` | Script de **développement** (`deploy-to-box.sh`, « DEV/TEST ONLY »), absent d'une installation Market et à ne jamais présenter à un utilisateur. La voie utilisateur existe maintenant dans l'interface : **« Supprimer puis recréer »** par équipement, par pièce ou pour le parc. |

**À jour (à conserver, après vérification en Task 1) :**

- « Prérequis » (Jeedom 4.4.9+, Debian, Python, broker MQTT) ; à recouper avec `plugin_info/info.json` (le changelog 2026-09-27 resserre l'OS à Debian 11 et 12 : le texte « Debian 12+ » est à vérifier).
- « Installation » (dépendances, démon) et « Configuration → Broker MQTT » (hôte, port, utilisateur, mot de passe, TLS, « Vérifier le certificat », « Tester la connexion »), sous réserve de compléter les libellés réels (`configuration.php:42-101`).
- « Comportement des pièces (suggested_area) » : l'explication du comportement de HA reste juste ; seul le remède P12 est périmé.
- « Nommage des équipements » (mots-clés bloquants, piège du matching par sous-chaîne) : cohérent avec la cause affichée « un mot du nom de l'équipement écarte ce type » ; **à revérifier mot par mot** contre le code des mappers avant de le reprendre (les listes ont pu évoluer).
- Les trois messages de la section « Durée des actions » (voir P11).

**Manquant (jamais documenté) :**

| # | À documenter | Pourquoi |
|---|---|---|
| M1 | Page principale : bandeau de santé (Bridge, MQTT, Dernière synchro, Dernière opération), zone « Actions Home Assistant », message de blocage quand le démon est arrêté ou MQTT déconnecté | Aucune ligne dans la doc actuelle. |
| M2 | Cartes de pièce, pseudo-pièce « Sans pièce », modale de pièce, accordéon d'équipements | Remplace l'ancien parcours « Diagnostic ». |
| M3 | Les **compteurs** de la modale de pièce (voir « Section compteurs isolée ») | Livrés par 20.3, absents. |
| M4 | Les actions **Exclure / Forcer / Revenir au mode automatique**, l'aperçu de forçage, la confirmation d'exclusion, le badge « pas encore appliqué », « Appliquer » | Livrés par 20.2, absents. |
| M5 | **Republier la pièce**, **Supprimer puis recréer** (pièce, équipement, parc) et leurs mises en garde | Déplacés dans la surface par 20.3, absents. |
| M6 | **Rescanner la topologie Jeedom** (page principale) et ce qu'il fait (applique les overrides persistés) | Livré par 20.4, absent. |
| M7 | « Télécharger le diagnostic support » et la case « Pseudonymiser les noms d'équipements » | Conservé par 20.3 mais jamais documenté. |
| M8 | Le tableau « ce que le plugin publie / ne publie pas et pourquoi », avec les causes **telles qu'affichées** | Demande explicite de la story ; les causes sont aujourd'hui dispersées dans le code (`REASON_LABELS`, `jeedom2ha_mapping_override.js:587-620`). |
| M9 | Les états grisés des boutons et leurs infobulles | Un bouton grisé sans explication est le premier motif de question d'un utilisateur ; chaque cause est affichée en infobulle dans l'interface. |
| M10 | Un mot sur l'**absence d'impact sur Homebridge** | L'écran l'affirme lui-même (« Aucun impact Homebridge… »). Seule la phrase de non-régression de l'ancienne doc subsiste, sous un ancien contexte. |

## Faits relevés le 2026-10-11 (lecture seule, `main` `3b120d3`)

Ces faits sont la base de la rédaction. Chaque libellé entre guillemets est celui que l'utilisateur lit à l'écran, repris tel quel du code.

### F1 — Page principale (`desktop/php/jeedom2ha.php`)

- **Bloc « Gestion »** : une seule vignette, **« Configuration »** (`:62-65`). « Diagnostic » et « Ajouter » n'existent plus (20.3).
- **Bandeau de santé** (toujours visible, `:67-87`, rempli par `refreshBridgeStatus` au chargement, sans rafraîchissement automatique) : quatre indicateurs.
  - **Bridge** : « Actif » (vert) ; « Arrêté » (rouge, démon non joignable) ; « Erreur Jeedom » ou « Erreur de communication » (rouge).
  - **MQTT** : « Connecté » (vert) ; « Reconnexion... » / « Connexion... » (orange) ; « Déconnecté » (rouge) ; « Non configuré » ; « Inconnu » si le démon est arrêté. L'adresse du broker s'affiche à côté.
  - **Dernière synchro** : date `jj/mm hh:mm:ss`, « Jamais » ou « Inconnue ».
  - **Dernière opération** : « Succès » (vert), « Partiel » ou « Échec » (orange : problème de configuration, pas incident d'infrastructure), « Aucune », avec le message de l'opération.
- **Zone « Actions Home Assistant »** (`:89-121`) : trois boutons, **« Republier dans Home Assistant »**, **« Rescanner la topologie Jeedom »**, **« Supprimer puis recréer dans Home Assistant »**. Ils sont **grisés** tant que le pont n'est pas opérationnel, avec une ligne d'explication : « Daemon arrêté — actions Home Assistant bloquées. », « MQTT déconnecté — actions Home Assistant bloquées. » ou « Bridge ou MQTT indisponible — actions Home Assistant bloquées. » (`jeedom2ha.js:153-158`). Ils sont aussi grisés pendant un rescan. (Le mot « Daemon » est celui de l'écran ; voir « Constats pour le backlog ».)
- **Export** (`:123-135`) : case **« Pseudonymiser les noms d'équipements »** et bouton **« Télécharger le diagnostic support »** ; messages « Export en cours... », « Diagnostic téléchargé », « Erreur export ». Fichier produit : `jeedom2ha-diagnostic-AAAA-MM-JJ.json` (`jeedom2ha.js:521`).
- **Section « Configuration Home Assistant par pièce »** (`:137-160`) : encadré d'information (« Choisissez une pièce pour voir ses équipements et, pour chaque commande, si elle répond aux prérequis Home Assistant (prêt / bloquant + pourquoi). Le type natif Jeedom (partagé Homebridge) n'est jamais modifié. »), puis une **carte par pièce** : nom de la pièce et nombre d'équipements entre parenthèses. Une pièce sans équipement n'a pas de carte. La carte **« Sans pièce »** rassemble les équipements sans pièce. Sans aucune pièce : « Aucune pièce avec équipement trouvée. »
- Les équipements désactivés dans Jeedom **sont** comptés et listés (relevé avec `onlyEnable=false`, `:15-16, :37-38`) ; les équipements du plugin jeedom2ha lui-même sont exclus.

### F2 — Modale de pièce (`jeedom2ha_mapping_surface.js`, `openRoom` `:1086+`)

- Un clic sur la carte ouvre une modale (titre = nom de la pièce). **Un seul diagnostic par équipement, chargé à l'ouverture** pour les équipements de la pièce seulement.
- **Compteurs** (F5, section isolée).
- **Actions de pièce** : **« Republier la pièce »** et **« Supprimer puis recréer la pièce »** (confirmation forte, bouton rouge). Pour « Sans pièce » elles n'existent pas : « Republication et suppression de pièce indisponibles pour les équipements sans pièce : utilisez les actions de chaque équipement. »
- Zone de retour des actions (succès, avertissement, échec).
- **Accordéon d'équipements** : un panneau par équipement ; nom, mention **« (désactivé dans Jeedom) »** le cas échéant, badge de synthèse (F4).

### F3 — Surface équipement → commande

Dans un équipement déplié :

- badge **« Override en attente — pas encore republié vers Home Assistant »** quand un override est enregistré mais non appliqué ;
- lien **« Voir la première commande bloquante »** (fait défiler jusqu'à la commande et la surligne) ;
- boutons d'action (F6) ;
- une ligne par **entité Home Assistant** : type (« light », « switch »…, ou « Entité HA »), « Commandes : … » ou « Aucune commande regroupée », badge **« pas encore appliqué »** et ses propres boutons ;
- le **tableau des commandes**, colonnes **« Commande »**, **« Type Jeedom »** (lecture seule, jamais modifié), **« Override HA »** (liste : « — mode automatique — », `alarm_control_panel`, `binary_sensor`, `button`, `climate`, `cover`, `light`, `sensor`, `switch`) et **« Diagnostic »**. Les commandes **non couvertes sont visibles, grisées, jamais bloquantes**. Choisir un type lance une vérification (délai 400 ms) ; si le résultat est valide, il est **enregistré automatiquement** (pas de bouton « Enregistrer ») ; sinon il est refusé avec sa raison. Une commande dont l'override de type est posé affiche une icône **« Revenir au type automatique »**.
- Le sélecteur est **grisé avec une infobulle** pour une commande exclue (« Commande exclue de Jeedom2HA : son type HA ne peut pas être réglé ici. »), un équipement désactivé (« Équipement désactivé dans Jeedom : son type HA ne peut pas être réglé ici. ») ou une commande non couverte (« Aucun type Home Assistant ne couvre cette commande : son type HA ne peut pas être réglé ici. »).
- Bandeau d'assurance **« Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha. »**, affiché **une fois par ouverture de pièce**, quand une vérification de type fait apparaître une commande bloquante.
- Un équipement sans commande : « Aucune commande à configurer pour cet équipement. » Une lecture impossible : « Impossible de lire la configuration de cet équipement. » ou « Impossible de charger la configuration HA (daemon indisponible). »

### F4 — Ce que dit l'écran de la publication (badges et causes)

**Badge de synthèse d'un équipement** (`buildPublicationSummaryLabel`, `jeedom2ha_mapping_override.js:836-858`) :

| Situation | Libellé affiché |
|---|---|
| Toutes les commandes utiles sont prêtes | « Sera publié dans Home Assistant : N commande(s) prête(s). » |
| Certaines prêtes, d'autres bloquantes | « Partiellement publié : N prête(s), M bloquante(s). » |
| Aucune prête, au moins une bloquante | « Ne sera pas publié dans Home Assistant : M commande(s) bloquante(s). » |
| Équipement exclu | « Exclu : ne sera pas publié dans Home Assistant. » |
| Équipement désactivé | « Désactivé dans Jeedom : ne sera pas publié dans Home Assistant. » |
| Aucune commande projetable | « Aucune commande projetable en Home Assistant pour cet équipement. » |

**Cellule Diagnostic d'une commande** : « Sera publié : <type> », ou « Ne sera pas publié — <cause> ». Causes affichées (`REASON_LABELS`, `jeedom2ha_mapping_override.js:587-620`, à reprendre mot pour mot) :

| Cause affichée | Famille |
|---|---|
| « type Home Assistant ambigu — précisez les types génériques dans Jeedom » ; « types génériques en conflit — précisez-les dans Jeedom » ; « types génériques en double » ; « un mot du nom de l’équipement écarte ce type » ; « état sans ordre On/Off » | À corriger côté Jeedom (types génériques, nom) |
| « types génériques non configurés dans Jeedom » ; « type non couvert par la V1 du plugin » ; « aucune commande Info/Action exploitable » ; « aucune commande configurée dans Jeedom » | Rien à publier tel que configuré |
| « commande non pilotable (pas d’ordre On/Off) » ; « pas de retour d’état exploitable » | Projection impossible (capacités manquantes) |
| « confiance « probable » exclue par la politique « sûr uniquement » » ; « confiance insuffisante pour la politique active » | Réglage de la politique de publication |
| « commande sans type Home Assistant applicable » (« non couverte ») | Commande non couverte |
| « aucun type Home Assistant identifié pour cette commande » ; « aucun type Home Assistant candidat à valider » ; « type HA non ouvert par ce plugin » | Type non publiable : affichées en **bloquantes** (triangle, comptées bloquantes, cible de « Voir la première commande bloquante »), `jeedom2ha_mapping_override.js:771-774`, `jeedom2ha_mapping_surface.js:63-67` *(corrigé en R1)* |
| « exclu manuellement (équipement) » ; « exclu manuellement (commande) » ; « exclu de Jeedom2HA (équipement dans la liste d’exclusions) » ; « … (plugin source dans la liste d’exclusions) » ; « … (pièce dans la liste d’exclusions) » | Exclusions volontaires (jamais comptées bloquantes) |
| « équipement désactivé dans Jeedom » | État neutre |
| « échec de publication MQTT au dernier sync » | Incident à relire dans les journaux |
| « publication forcée manuellement » ; « type Home Assistant identifié — publication normale » | Causes positives |

> Point d'attention de rédaction : la V1 de l'écran dit « type non couvert par la V1 du plugin » alors que le périmètre compte huit types (P7). La documentation emploie la formule de l'écran **et** explique ce qu'elle couvre réellement ; l'incohérence éventuelle de libellé est un constat pour le backlog, pas une retouche ici.

### F5 — Compteurs de la modale (voir la section isolée ci-dessous)

Deux lignes sous le titre de la pièce, lues dans les diagnostics déjà chargés (`renderRoomCounters`, `:539+` ; libellés `buildRoomCounterLabels`, `jeedom2ha_mapping_override.js:947-967`) :

- Ligne équipements : « N équipement(s) publié(s) », « … exclu(s) », « … désactivé(s) dans Jeedom », « … à corriger », suivi si besoin de « N équipement(s) non lu(s) » ;
- Ligne commandes : « N commande(s) prête(s) », « … bloquante(s) », « … non couverte(s) ».
- Messages : « Chargement des compteurs… » ; « Compteurs indisponibles : la configuration des équipements de cette pièce n’a pas pu être lue. »

### F6 — Actions de publication (exclure / forcer / revenir / appliquer / republier / supprimer puis recréer)

- **Exclure**, **Forcer**, **Revenir au mode automatique** : trois boutons, **à la portée de l'équipement et à celle de chaque entité Home Assistant**. Quand une action serait sans effet, le bouton est grisé et **sa propre infobulle donne la cause** : « Entité déjà exclue de Home Assistant. », « Publication déjà forcée sur cette entité. », « Déjà publiée : forcer n’a pas d’effet. », « Aucun type Home Assistant identifié pour cette entité. », « Type HA hors périmètre de ce plugin. », « Projection invalide pour ce type HA. », « Aucune commande clé propre à cette entité. », « Équipement non éligible : l’action serait sans effet. », « Exclusion posée sur l’équipement : la retirer depuis l’équipement. », « Aucun override de publication à retirer. », « Cette action est sans effet dans l’état courant. »
- **Exclure** : confirmation seulement si l'exclusion fait quitter Home Assistant une entité publiée (« Exclure cet équipement de Home Assistant ? » + « Entités qui quitteront Home Assistant : … » ; « Exclure cette entité de Home Assistant ? »). Boutons de la confirmation : « Annuler » / « Confirmer ».
- **Forcer** : **aperçu fourni par le démon avant toute écriture** : « Type HA : … », « Projection valide / invalide pour ce type. », « Commandes qui recevront les ordres : … », « Cette entité sera publiée dans Home Assistant. » (équipement : « Entités concernées par ce forçage : … », « Au moins une entité sera publiée dans Home Assistant. »). Si le forçage serait refusé : « Le forçage serait refusé : <raison> », bouton « Confirmer » grisé. Aperçu indisponible : « Aperçu indisponible — le démon ne répond pas. »
- **Revenir au mode automatique** (équipement) retire **les deux** catégories d'override de l'équipement (type et publication). Sur une entité, il retire l'exclusion ou le forçage de l'entité **et** les types Home Assistant choisis pour ses commandes (`jeedom2ha.ajax.php:981-991` → `http_server.py:3373-3375`, `fields=("ha_entity_type","publication_override")`, `entity_scope=True`, appliqué sur toutes les commandes de l'entité `http_server.py:3314-3337`). *(Corrigé en R1 : la version initiale disait « retire l'override de publication de cette entité » seulement.)*
- **Appliquer / Republier (équipement)** : un seul bouton. Libellé **« Appliquer »** (orange) quand un override attend d'être appliqué, **« Republier »** sinon. Grisé pour un équipement désactivé (« Équipement désactivé dans Jeedom : rien à republier. ») ou exclu (« Équipement exclu : rien à republier. ») — sauf si un override est en attente.
- **Supprimer puis recréer** (équipement, pièce, parc) : confirmation rouge « Supprimer puis recréer dans Home Assistant », texte « Supprimer "<nom>" de Home Assistant… » et mise en garde **« Attention : l'historique, les dashboards, les automatisations et l'entity_id liés à ces entités peuvent être impactés. »** Boutons « Supprimer 1 équipement » / « Supprimer la pièce » / « Supprimer ». Grisé pour un équipement non publié (« Équipement non publié dans Home Assistant : rien à supprimer. »), pour une pièce sans rien à supprimer (« Aucun équipement publié dans cette pièce. ») ; « Republier la pièce » grisé avec « Aucun équipement à publier dans cette pièce. ».
- **Republier dans Home Assistant** (parc) : « Republier tous les équipements inclus ? » (sans nombre). **Supprimer puis recréer** (parc) : « Supprimer puis recréer tout le parc publié ? » + même mise en garde.
- Pendant une action : libellés « Confirmation en cours… », « En cours... », « Suppression... ». Résultat : message du démon, vert (succès), orange (succès partiel) ou rouge. Erreurs : « Le démon ne répond pas. », « Erreur de communication avec le backend Home Assistant. », « Réponse backend incomplète pour l'action Home Assistant. ». Délai : messages de dépassement et d'action déjà en cours (P11).

### F7 — Rescan (page principale)

« Rescanner la topologie Jeedom » → confirmation « Un sync complet peut publier ou retirer des entités Home Assistant et applique les overrides persistés. Confirmer ? » (bouton « Rescanner »). Pendant l'opération : « Rescan en cours… » ; tous les boutons d'action sont grisés. Issues : « Synchronisation terminée. » (vert), « Synchronisation terminée avec avertissements. » (orange), « Synchronisation échouée. » (rouge), « Une opération est déjà en cours ou le rescan a échoué. », « Erreur de communication : relire Dernière synchro avant de relancer. » ; le bandeau est ensuite relu. Ce rescan est celui qui **applique d'un coup les overrides en attente de tous les équipements**.

### F8 — Configuration (`plugin_info/configuration.php`, ouverte par la vignette « Configuration »)

- Bandeau de détection : « MQTT Manager détecté — configuration pré-remplie », « Configuration manuelle », « Aucun broker MQTT détecté. Installez MQTT Manager ou saisissez les paramètres manuellement ci-dessous. » ; bouton « Récupérer depuis MQTT Manager », lien « Réinitialiser le formulaire ».
- **Configuration MQTT** : Hôte MQTT, Port MQTT (1883 par défaut, 8883 pour TLS), Utilisateur MQTT, Mot de passe MQTT (« Laisser vide pour conserver l'actuel », « Mot de passe déjà configuré »), Activer TLS, Vérifier le certificat (« Décocher pour les certificats auto-signés »), bouton « Tester la connexion ».
- **Filtrage & Publication** : Plugins exclus (noms de plugins séparés par des virgules), Pièces exclues (**identifiants numériques** d'objets Jeedom séparés par des virgules), Politique de publication (deux valeurs, P8), bouton **« Appliquer les filtres et rescanner »** (« Sauvegarde en cours... », « Rescan en cours... », « Appliqué & Rescan terminé — N équipement(s) publié(s) »).
- Les exclusions de cette page sont celles qui apparaissent dans la surface comme « exclu de Jeedom2HA (… dans la liste d'exclusions) » ; elles sont **distinctes** des exclusions manuelles posées par le bouton « Exclure ».

### F9 — Routes du démon concernées (référence, `http_server.py:4574-4592`)

`GET /system/status` (bandeau), `POST /action/sync` (rescan), `GET /system/mapping_overrides/{eq_id}` (arbre d'un équipement), `POST /system/overrides/preview` (aperçu type et forçage), `POST /action/mapping_override[_revert]` (override de type), `POST /action/publication_override[_revert]` (exclure / forcer / revenir), `POST /action/execute` (republier, supprimer puis recréer), `GET /system/diagnostics` (export de diagnostic), `GET /system/published_scope` (route conservée, plus appelée par la page). Aucune route de profil d'overrides (P6).

## Section compteurs isolée — conçue pour être réécrite seule

> **Contrainte (demande d'Alexandre) : une story « compteurs » est déjà prévue après celle-ci. Elle changera la sémantique des compteurs : « publiés » = présents dans Home Assistant, « en attente d'application », « non pris en charge », à la place de la sémantique actuelle. Cette section doit pouvoir être remplacée sans toucher au reste de la documentation.**

Règles de rédaction (AC6) :

1. **Un seul endroit.** Toute la description des compteurs tient dans **un fichier ou un bloc unique** nommé `compteurs` (fichier séparé inclus ou section aux ancres balisées `<!-- COMPTEURS:DEBUT -->` … `<!-- COMPTEURS:FIN -->`, selon Q4). Le reste du document renvoie à ce bloc par un lien, **sans jamais recopier** un libellé de compteur, un exemple chiffré ni une définition.
2. **Pas de définition de compteur ailleurs.** Les descriptions de la modale, du tableau de publication et des causes n'emploient pas les mots « publié », « exclu », « à corriger » pour *définir* un compteur ; elles décrivent l'état d'un équipement ou d'une commande (F4), qui reste inchangé.
3. **Contenu du bloc (sémantique actuelle, à remplacer plus tard)** :
   - ce que compte chaque nombre de la ligne équipements (F5) : « publié » = au moins une commande prête (équipement entièrement ou **partiellement** publié) ; « exclu » ; « désactivé dans Jeedom » ; « à corriger » = au moins une commande bloquante, donc **un équipement partiellement publié compte à la fois publié et à corriger** (limite connue, décrite dans le Dev Agent Record de 20.3) ;
   - ce que compte chaque nombre de la ligne commandes : prêtes, bloquantes, non couvertes ;
   - la précision que **« publié » signifie aujourd'hui « sera publié selon le diagnostic »** et **non « présent dans Home Assistant »** : c'est précisément la sémantique que la story compteurs doit changer. Le bloc le dit en toutes lettres, avec un bandeau d'obsolescence prévu (« Cette section décrit la sémantique des compteurs avant la story compteurs. »).
4. **En-tête de maintenance dans le bloc** : liste des libellés d'interface décrits, de la fonction qui les produit (`buildRoomCounterLabels`, `summarizeRoom`) et de l'état des tests Node correspondants, pour que l'auteur de la story compteurs sache quoi réconcilier.
5. **Test de cloisonnement (AC6)** : un contrôle automatisé ou, à défaut, une vérification documentée par `grep` établit que les libellés de compteur n'apparaissent **que** dans le bloc.

## Acceptance Criteria

**AC1 — Chaque affirmation est vérifiée dans le code**

**Given** la documentation réécrite
**When** un relecteur choisit n'importe quelle affirmation sur l'interface (libellé, bouton, état grisé, message, comportement)
**Then** elle correspond au code de `main` au SHA courant du `dev-story`, sans écart
**And** une table de traçabilité (« affirmation → fichier:ligne ») est jointe au Dev Agent Record, couvrant au minimum tous les libellés cités entre guillemets
**And** aucune affirmation n'est tirée d'un fichier de story : l'historique de développement n'est jamais la source.

**AC2 — Ce qui est périmé a disparu, ce qui manquait est là**

**Given** l'inventaire de cette story (P1 à P12, M1 à M10)
**When** la documentation est réécrite
**Then** chaque entrée P est soit corrigée, soit retirée (avec sa raison consignée), et chaque entrée M est couverte par au moins une section
**And** le mot « Diagnostic » ne désigne plus un bouton ou une modale de la page principale ; l'onglet « HA / jeedom2ha » n'est plus mentionné ; aucune commande `deploy-to-box.sh` n'apparaît dans la documentation utilisateur
**And** `docs/index.md` ne décrit plus `fr_FR/index.md` comme « Jeedom plugin template documentation » et `docs/fr_FR/changelog_beta.md` n'est plus intitulé « Changelog plugin template - beta ».

**AC3 — L'écran réel est décrit, du chargement de la page au dernier bouton**

**Given** le plan de la documentation
**When** on le suit dans l'ordre
**Then** il décrit : la page principale et son bandeau de santé (quatre indicateurs, leurs valeurs), la zone « Actions Home Assistant » et son blocage, les cartes de pièce et « Sans pièce », la modale de pièce, l'accordéon d'équipements, les entités Home Assistant, le tableau à quatre colonnes, l'édition du type Home Assistant d'une commande, les actions Exclure / Forcer / Revenir au mode automatique / Appliquer / Republier / Supprimer puis recréer (équipement, pièce, parc), le rescan, l'export de diagnostic, la configuration
**And** chaque action décrit : ce qu'elle fait, ce qu'elle ne fait pas, sa confirmation, ses états grisés et leurs causes, et ce que l'utilisateur voit ensuite
**And** la distinction entre **override de type** (enregistré automatiquement, en attente d'application) et **override de publication** (exclure / forcer) est explicite.

**AC4 — « Ce que le plugin publie et pourquoi » est dit avec les mots de l'écran**

**Given** un équipement dans la surface
**When** le lecteur cherche pourquoi il est ou n'est pas dans Home Assistant
**Then** la documentation donne la table des badges (F4) et des causes (F4) **avec les libellés exacts de l'interface**, regroupés par famille d'action (corriger dans Jeedom, régler le plugin, rien à faire, incident)
**And** elle explique ce que sont une commande « prête », « bloquante », « non couverte », une entité Home Assistant et un équipement exclu manuellement ou par la configuration
**And** elle ne contient aucun jargon interne : ni `evaluate_equipment`, ni `generic_type` comme concept sans glose (l'écran écrit « Type Jeedom » et « types génériques »), ni noms de routes, ni noms de fonctions, ni identifiants de stories, ni sigles `CC-`/`AC`.

**AC5 — Aucune donnée réelle**

**Given** la documentation, ses exemples et ses éventuels textes de légende de capture
**When** on les relit
**Then** aucun nom d'équipement, de pièce, de plugin, d'hôte, d'adresse IP ni d'identifiant réel de l'installation d'Alexandre ne figure ; les exemples sont génériques (« Pièce A », « Lampe 1 », « Prise 2 », identifiants fictifs)
**And** les noms de plugin cités en exemple de configuration restent ceux déjà présents dans le texte d'interface (placeholder `virtual,zwave,rfxcom`).

**AC6 — La section compteurs est isolée**

**Given** la documentation réécrite
**When** on supprime ou remplace le bloc `compteurs`
**Then** aucun autre passage ne devient faux ni orphelin : les renvois pointent vers le bloc (lien ou ancre) et aucun libellé de compteur n'est recopié ailleurs
**And** le bloc porte son en-tête de maintenance et son bandeau d'obsolescence (règles de la section isolée)
**And** une vérification (grep documenté ou test) établit que les libellés « équipement(s) publié(s) », « à corriger », « commande(s) prête(s)/bloquante(s)/non couverte(s) » n'apparaissent qu'à cet endroit.

**AC7 — Pas de captures dans cette réécriture (décision Q3=B)**

**Given** la décision d'Alexandre (Q3=B)
**When** la documentation est livrée
**Then** elle ne contient aucune image ni fichier de capture ; le texte est autoportant (chaque écran est décrit en mots)
**And** un emplacement de capture est prévu par écran sous forme d'un commentaire Markdown invisible d'une ligne (par exemple `<!-- CAPTURE-A-PRENDRE: modale de pièce -->`), pour que la story « compteurs » ou une story ultérieure puisse les ajouter ; les captures seront alors prises **après** la story « compteurs », sur données d'exemple génériques uniquement (installation de démonstration ou maquette, jamais la box d'Alexandre), sans nom réel d'équipement, de pièce ni d'adresse
**And** cette story ne produit aucune capture.

**AC8 — Emplacement, langue et public conformes aux décisions**

**Given** les décisions d'Alexandre Q1=A, Q2=A et Q4=A
**When** la documentation est livrée
**Then** elle s'adresse à l'utilisateur du Market (français courant, aucun jargon, termes Jeedom et Home Assistant glosés), est rédigée **en français seul** (aucun fichier `docs/en_US`), et se trouve sous `docs/fr_FR/` avec le bloc `compteurs` dans un **fichier séparé** (`docs/fr_FR/compteurs.md`) ; `plugin_info/info.json` (liens `documentation` et `changelog`) est vérifié et **n'est pas modifié** (l'emplacement ne change pas)
**And** le changelog stable reçoit une entrée datée décrivant ce que l'utilisateur voit de nouveau (surface par pièce, exclusion et forçage, retour au mode automatique, rescan sur la page principale, retrait de la synthèse globale et du Diagnostic), rédigée pour l'utilisateur, sans numéros de stories.

**AC9 — Aucun périmètre voisin touché**

**Given** le diff final de la story de développement
**When** on liste les fichiers modifiés
**Then** il ne contient que de la documentation (`docs/**`, éventuellement `README.md` et `plugin_info/info.json` si Q4 le justifie) et les fichiers BMAD de suivi (story, `sprint-status.yaml`)
**And** aucun fichier sous `core/`, `desktop/`, `resources/`, `tests/`, `scripts/` ni `.github/` n'est modifié, sauf un éventuel test de cloisonnement de la documentation (AC6) si Alexandre l'accepte.

## Tasks / Subtasks

- [x] **Task 0 — Prérequis (bloquants)**
  - [x] 0.1 *(fait le 2026-10-11, 17:35 : Q1=A, Q2=A, Q3=B, Q4=A, voir le Journal des décisions)* Alexandre a tranché **Q1, Q2, Q3, Q4** (section ci-dessous) ; réponses consignées dans le Journal des décisions.
  - [x] 0.2 *(vérifié le 2026-10-11 dans `sprint-status.yaml` : 20-1 à 20-4 `done` ; story « compteurs » non livrée, le bloc décrit la sémantique actuelle)* 20.1 à 20.4 `done` (tenu au 2026-10-11) ; **la story « compteurs » est connue** : si elle a déjà changé la sémantique avant ce `dev-story`, le bloc `compteurs` décrit la **nouvelle** sémantique (sinon l'ancienne, avec son bandeau d'obsolescence).
- [x] **Task 1 — Rejouer les relevés au SHA courant (lecture seule) (AC: 1)**
  - [x] 1.1 Rejouer F1 à F9 sur le `main` du moment ; consigner tout écart avec le présent relevé dans le Dev Agent Record (un écart signale qu'une story a modifié l'interface depuis le `create-story`).
  - [x] 1.2 Lire `README.md`, `docs/release-market.md` et `plugin_info/info.json` pour fixer où la documentation est lue (liens, version minimale, prérequis OS).
  - [x] 1.3 Établir la liste exacte des types Home Assistant publiés par le plugin et de leurs conditions (cf. P7), **à partir du code des mappers et de `PRODUCT_SCOPE`**, pas de l'ancien tableau.
  - [x] 1.4 Revérifier chaque ligne de la section « Nommage des équipements » contre le code (mots-clés bloquants) avant de la reprendre ou de la raccourcir.
- [x] **Task 2 — Plan et décisions de rédaction (AC: 2, 3, 8)**
  - [x] 2.1 *(plan retenu tel quel ; Alexandre relira la documentation livrée)* Plan de la documentation : Présentation ; Prérequis et installation ; Configuration ; Première synchronisation ; La page principale (bandeau, actions, export) ; La configuration par pièce (cartes, modale, tableau, actions) ; **Ce que le plugin publie et pourquoi** ; Les compteurs *(bloc isolé)* ; Dépannage ; Annexes (suggested_area, nommage, durée des actions, changelog).
  - [x] 2.2 Fixer le niveau de détail selon Q1, la langue selon Q2, les emplacements de captures selon Q3, le dossier selon Q4.
  - [x] 2.3 Pour chaque entrée P1 à P12, noter « corrigé / retiré / déplacé en annexe » et la raison.
  - [x] 2.4 *(décisions de rédaction prises par ClaudeBox le 2026-10-11)* **P6 (profils d'overrides) : retiré**, conformément à l'interdit « ne pas décrire une fonction sans point d'entrée » ; **P11 (volumes chiffrés) : condensé dans une annexe courte** (les trois messages et la marche à suivre restent, les estimations par type d'équipement sont ramenées à une phrase).
- [x] **Task 3 — Rédaction (AC: 1-6)**
  - [x] 3.1 Sections « page principale », « configuration par pièce », « ce que le plugin publie et pourquoi » (F1 à F4, F6 à F8), libellés repris du code, sans jargon.
  - [x] 3.2 Bloc `compteurs` isolé (section dédiée, F5), avec en-tête de maintenance et bandeau d'obsolescence ; renvois depuis le reste du texte par lien ou ancre uniquement.
  - [x] 3.3 Sections conservées et corrigées : prérequis, installation, configuration MQTT et filtrage (libellés réels, P8, P9), dépannage (P10), suggested_area (P12), durée des actions (P11), nommage (1.4).
  - [x] 3.4 `docs/index.md` (P index), `docs/fr_FR/changelog.md` (entrée datée), `docs/fr_FR/changelog_beta.md` (intitulé et contenu hérités du gabarit, selon la décision prise).
  - [x] 3.5 *(sans objet : Q2=A, français seul, aucune version anglaise)*
- [x] **Task 4 — Vérifications (AC: 1, 2, 4-6, 9)** *(relecture ClaudeBox et relecture indépendante, deux rondes (PR #232), environ 150 affirmations vérifiées dans le code ; contrôle des noms réels par ClaudeBox)*
  - [x] 4.1 Table de traçabilité « affirmation → fichier:ligne » dans le Dev Agent Record.
  - [x] 4.2 *(fait ; le contrôle contre les noms réels reste à faire par ClaudeBox)* Recherches négatives dans `docs/` : « Diagnostic » (bouton), « HA / jeedom2ha », « deploy-to-box », `evaluate_equipment`, `CC-`, « Mes templates », adresses IP. **Le contrôle contre les noms réels de la maison est fait par ClaudeBox à la relecture, en lecture seule, sans jamais recopier ces noms** (la session de dev ne les connaît pas et ne les cherche pas).
  - [x] 4.3 Vérification de cloisonnement des compteurs (AC6).
  - [x] 4.4 Liens internes valides (Markdown) ; `git diff --stat` limité aux fichiers documentaires.
  - [x] 4.5 Aucun test existant ne casse (certains tests peuvent lire `docs/` ; lancer `make test`, voir Dev Notes).
- [x] **Task 5 — Captures d'écran : sans objet (Q3=B) (AC: 7)** *(aucune capture dans cette réécriture ; seuls les commentaires d'emplacement invisibles sont posés en Task 3 ; captures après la story « compteurs », sur données génériques)*
- [x] **Task 6 — Relecture et clôture** *(relecture ClaudeBox et relecture indépendante, deux rondes (PR #232), environ 150 affirmations vérifiées dans le code ; contrôle des noms réels par ClaudeBox)*
  - [x] 6.1 *(fait : relecture ClaudeBox et relecture indépendante, deux rondes (PR #232), environ 150 affirmations vérifiées dans le code ; contrôle des noms réels par ClaudeBox)* Relecture ClaudeBox (fidélité au code, absence de jargon, aucune donnée réelle) avant fusion ; revue indépendante si Codex est indisponible.
  - [x] 6.2 *(fait : SHA `main` `36eb156` (fusion PR #232) ; `make test` vert ; décisions Q1 à Q4 consignées au Journal ; CC-07 d fermé par cette clôture)* Au `done` : SHA relevé, commandes de vérification, décisions Q1 à Q4 et fermeture de CC-07 d consignés.

## Dev Notes

### Questions ouvertes pour Alexandre (à trancher avant `ready-for-dev`)

Les recommandations ci-dessous sont des propositions ; aucune n'est actée par ce `create-story`.

**Q1 — Public visé : utilisateur du Market (grand public) ou Alexandre seul (usage interne) ?**

- **A. Utilisateur du Market** : français courant, aucun jargon (ni `generic_type`, ni MQTT sans glose), explication des termes Jeedom/Home Assistant, dépannage guidé. Cohérent avec le lien « documentation » de `info.json` et avec le gate epic-level « documentation utilisateur réécrite ».
- **B. Alexandre seul** : texte court de référence, vocabulaire du projet admis, pas de pédagogie ; plus rapide à écrire, mais impropre à publier sur le Market.
- **Recommandation : A.** Le plugin est destiné au Market (cycle `main → beta → stable → Jeedom Market`), la documentation est liée dans `info.json`, et l'écran a été réécrit pour parler « avec des mots d'usage » (20.3) : la documentation doit tenir le même niveau. Une doc interne peut en être dérivée plus tard à moindre coût, l'inverse non.

**Q2 — Langue : français seul, ou aussi anglais ?**

- **A. Français seul** (`docs/fr_FR`), comme aujourd'hui ; l'interface elle-même est en français et ne contient que des textes `{{…}}` traduisibles.
- **B. Français + anglais** (`docs/en_US`) : audience plus large sur le Market, mais coût double, risque de divergence à chaque évolution d'écran, et l'interface reste en français tant qu'aucune traduction (`core/i18n`) n'existe — une documentation anglaise décrirait un écran français.
- **Recommandation : A.** Rédiger en français d'abord ; l'anglais n'a de sens qu'avec une interface traduite. À rouvrir quand l'interface le sera.

**Q3 — Captures d'écran : oui ou non dans la documentation finale ?**

- **A. Oui** : 4 à 6 captures génériques (page principale avec bandeau, carte de pièce, modale avec compteurs, tableau des commandes, confirmation de « Supprimer puis recréer »), sur données d'exemple. Gain de compréhension réel pour la surface par pièce ; coût : maintenance à chaque évolution d'écran, et une story « compteurs » imminente va changer la ligne de compteurs (donc rendre une capture obsolète tout de suite).
- **B. Non** : texte autoportant, aucune dépendance visuelle, aucun risque de fuite de noms réels.
- **Recommandation : B pour cette réécriture, avec emplacements prévus dans le plan** (une ligne de commentaire par écran), puis **ajout des captures après la story « compteurs »**. Raison : les compteurs sont la zone la plus visible de la modale et vont changer ; une capture prise maintenant serait fausse au prochain jalon. Si Alexandre veut des captures malgré tout, elles seront prises sur une installation de démonstration ou une maquette, jamais sur la box réelle (AC7).

**Q4 — Emplacement : `docs/fr_FR` (celui du Market) ou un autre emplacement ?**

- **A. `docs/fr_FR/index.md`** (et `changelog.md`) : emplacement déjà référencé par `plugin_info/info.json` (`documentation` et `changelog`) et par la convention de documentation des plugins Jeedom (`docs/<langue>/`), qui est celle lue par le Market. Aucun changement de lien.
- **B. Autre emplacement** (par exemple `docs/utilisateur/` ou un wiki) : sépare la documentation utilisateur de la documentation de développement qui occupe aujourd'hui `docs/`, au prix d'un changement de liens dans `info.json` et d'un risque de casser la lecture par le Market.
- **Recommandation : A, avec un découpage en plusieurs fichiers sous `docs/fr_FR/`** (par exemple `index.md` pour le parcours et un fichier `compteurs.md` pour le bloc isolé, voir AC6). La séparation utilisateur / développeur peut se faire par `docs/index.md` (index à clarifier) sans déplacer la documentation du Market. À confirmer : le Market lit-il bien les sous-fichiers liés depuis `index.md` (Task 1.2, `release-market.md`) ; sinon, bloc balisé dans `index.md` à la place d'un fichier séparé.

### Constats pour le backlog (non traités par cette story)

À valider ou rejeter par Alexandre ; la documentation décrit l'écran tel quel et n'attend pas ces corrections.

1. Les messages « Daemon arrêté — actions Home Assistant bloquées. » (`jeedom2ha.js:156`) et « daemon indisponible » emploient « daemon » alors que le bandeau dit « Bridge » ; l'utilisateur lit trois mots (démon, daemon, bridge) pour une même chose. Hors du périmètre de 20.3 ? — à regrouper avec la story compteurs / CC-51 (décision d'ordre d'Alex du 11/10).
2. « type non couvert par la V1 du plugin » (`jeedom2ha_mapping_override.js:595`) : « V1 » est un jargon de version, et le périmètre réel compte huit types (P7) — à regrouper avec la story compteurs / CC-51 (décision d'ordre d'Alex du 11/10).
3. « Jeedom2HA » (exclusions) et « jeedom2ha » (plugin) : deux graphies dans l'écran — à regrouper avec la story compteurs / CC-51 (décision d'ordre d'Alex du 11/10).
4. La page d'édition d'équipement du gabarit (`jeedom2ha.php:163-266`) reste dans le fichier alors que rien ne l'atteint (aucune vignette d'équipement) : à confirmer par le cœur Jeedom ; non documentée.
5. La route `GET /system/published_scope` du démon n'est plus appelée par la page (conservée par décision).
6. Un équipement partiellement publié compte à la fois « publié » et « à corriger » (limite connue de 20.3) : à traiter par la story « compteurs ».

### Contrats réutilisés

- Libellés : lus dans le code, jamais déduits des stories (voir AC1).
- Plan inspiré du parcours de l'utilisateur : installer → configurer → première synchronisation → comprendre l'état → corriger → dépanner.
- Style : français, tutoiement et familiarités évités (registre du texte existant, à confirmer avec Q1), phrases courtes, un écran par section, tableau des causes avec libellés exacts.

### Interdits

- Aucune modification de code, de test, de libellé ou de comportement. Un libellé faux est un constat (voir plus haut), pas une retouche.
- Aucun nom réel d'équipement, de pièce, d'hôte, de plugin d'installation, d'adresse IP, d'identifiant d'équipement ni de secret ; aucune capture de la box réelle.
- Aucune mention de commandes de développement (`deploy-to-box.sh`, `make`, `scripts/*`) dans la documentation utilisateur.
- Aucun accès à la box Jeedom, à Home Assistant ni au déploiement.
- Ne pas décrire une fonction sans point d'entrée dans l'interface (profils d'overrides, P6).
- Ne pas dupliquer les libellés de compteur hors du bloc isolé (AC6).
- Jamais `git add -A`, jamais `--admin`, aucun force-push.

### Fichiers probablement touchés (pour le `dev-story`)

`docs/fr_FR/index.md` (réécriture), `docs/fr_FR/compteurs.md` (isolé, Q4=A), `docs/fr_FR/changelog.md`, `docs/fr_FR/changelog_beta.md`, `docs/index.md`, éventuellement `README.md` et `plugin_info/info.json` (liens, seulement si Q4 = B), aucun `docs/en_US/*` (Q2=A) ni `docs/images/*` (Q3=B). Aucun fichier de code.

### Tests existants à surveiller

Lancer `make test` avant de pousser, par prudence : un test qui lit des fichiers sous `docs/` (liens, libellés) ou le changelog doit rester vert ; aucun test n'est attendu en échec pour un changement de documentation seule.

## Conditions de passage à `ready-for-dev` (toutes remplies le 2026-10-11, 17:35)

1. [x] Alexandre a répondu à **Q1, Q2, Q3 et Q4** (Q1=A, Q2=A, Q3=B, Q4=A) ; consigné dans le Journal des décisions, AC7 et AC8 figés dessus.
2. [x] Le plan de documentation (Task 2.1) est retenu tel quel ; Alexandre relira la documentation livrée.
3. [x] L'état de la story « compteurs » est connu : **pas encore livrée**, le bloc `compteurs` décrit la sémantique actuelle avec son bandeau d'obsolescence.

## Définition de done

- Tous les AC sont couverts ; table de traçabilité « affirmation → code » jointe ; File List complète.
- Diff limité à la documentation (AC9) ; CI verte.
- Relecture ClaudeBox (fidélité, jargon, données réelles) ; revue indépendante si Codex est indisponible.
- CC-07 d fermé : documentation utilisateur alignée sur l'interface livrée, sans écart relevé en relecture.
- Décisions Q1 à Q4, SHA de référence et commandes de vérification consignés au `done`.

## Journal des décisions

- 2026-10-01 — Sprint change proposal : story 20-5 « Documentation utilisateur réécrite (CC-07 d) », dépend de 20-1 à 20-4, décrit l'interface finale.
- 2026-10-11 — `create-story` de 20.5 (session cloud déléguée, lecture seule, aucun accès box/HA) : inventaire de la documentation au SHA `3b120d3` (12 passages périmés, 10 manquants), faits F1 à F9 relevés dans le code, section compteurs isolée, questions Q1 à Q4 posées avec recommandation. **`ready-for-dev` non accordé** à ce stade ; aucune des quatre questions n'est tranchée par ce document.
- 2026-10-11, 17:35 — Décisions d'Alexandre : Q1=A (utilisateur du Market), Q2=A (français seul), Q3=B (pas de captures dans cette réécriture ; emplacements prévus ; captures après la story « compteurs »), Q4=A (docs/fr_FR, bloc compteurs séparé).
- 2026-10-11 — Décisions de rédaction (Task 2.4, ClaudeBox) : P6 retiré (fonction sans point d'entrée) ; P11 condensé en annexe courte ; plan de la Task 2.1 retenu tel quel. Conditions de passage remplies : story `ready-for-dev`.
- 2026-10-11 — Clôture : documentation livrée (PR #232), relue en deux rondes par ClaudeBox et par une relecture indépendante ; story done ; ferme CC-07 d. Alexandre relira la documentation livrée.

## References

- `_bmad-output/planning-artifacts/epics-projection-engine.md`, Epic 20, Story 20.5 et gates epic-level pe-epic-20.
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-01-etape-4-interface.md` (décisions d'interface).
- `_bmad-output/implementation-artifacts/20-1-surface-unique-piece-equipement-commande.md`, `20-2-exclusion-forcage-depuis-surface-cc26.md`, `20-3-suppression-gabarit-jeedom-libelles-francais-cc04-ui.md`, `20-4-rescan-page-principale-cc04-ui.md` (historique, non source de vérité de l'état final) et leurs artefacts de preuve.
- Code : `desktop/php/jeedom2ha.php`, `desktop/js/jeedom2ha.js`, `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/js/jeedom2ha_mapping_override.js`, `plugin_info/configuration.php`, `resources/daemon/transport/http_server.py:4574-4592`, `resources/daemon/validation/ha_component_registry.py:70`.
- Documentation actuelle : `docs/fr_FR/index.md`, `docs/index.md`, `docs/fr_FR/changelog.md`, `docs/fr_FR/changelog_beta.md`, `plugin_info/info.json` (liens `documentation` et `changelog`).
- `_bmad-output/project-context.md` (règles d'implémentation).

## Dev Agent Record

### Agent Model Used

Agent Claude Code, session cloud déléguée (sans accès box Jeedom, Home Assistant, secrets ni déploiement). Phases `create-story` puis `dev-story` (Tasks 1 à 4).

### Debug Log References

- Relevé en lecture seule du code de `main` `3b120d3` ; aucune exécution de test, aucun changement de code.
- `dev-story` (2026-10-11) : code rejoué au SHA `8a1d01b` (`git diff 3b120d3 8a1d01b` : uniquement la story et `sprint-status.yaml`, donc code d'interface inchangé). `pip install -e ".[test]"`, `make test` : 620 passed, 1 skipped ; `flake8` : sans sortie. Vérifications documentaires : liens internes Markdown valides, recherches négatives et cloisonnement des compteurs (voir ci-dessous).

### Completion Notes List

- Story créée, statut `backlog` (`ready-for-dev` non accordé : Q1 à Q4 à trancher par Alexandre).
- Aucun nom d'équipement ni de pièce réel dans cette story ; les exemples sont génériques.

**`dev-story` (Tasks 1 à 4) — livré :**

- `docs/fr_FR/index.md` réécrit (plan de la Task 2.1) ; `docs/fr_FR/compteurs.md` créé (bloc isolé, Q4=A, en-tête de maintenance et mention d'obsolescence en commentaire invisible + note visible) ; `docs/fr_FR/changelog.md` (entrée du 2026-10-11) ; `docs/fr_FR/changelog_beta.md` (intitulé et contenu hérités du gabarit remplacés) ; `docs/index.md` (ligne « template » corrigée). `plugin_info/info.json` vérifié, non modifié.
- **Table de traçabilité (AC1, Task 4.1)** : `_bmad-output/implementation-artifacts/20-5-tracabilite-documentation.md` (annexe, hors documentation du Market). Chaque citation de ligne a été revérifiée par script (ligne contenant le texte attendu).
- Captures : aucune ; commentaires invisibles `<!-- CAPTURE-A-PRENDRE: … -->` posés (Q3=B).
- Décisions P1 à P12 : P1 corrigé (plus de bouton « Diagnostic », le mot ne désigne que la colonne du tableau et l'export) ; P2 retiré (onglet) ; P3 corrigé (quatre colonnes) ; P4 corrigé (réglage enregistré mais en attente) ; P5 corrigé (type vs publication) ; P6 retiré (aucun point d'entrée) ; P7 corrigé (huit types) ; P8 corrigé (libellés réels) ; P9 corrigé (deux chemins de rescan) ; P10 corrigé (dépannage réécrit) ; P11 condensé en annexe, volumes chiffrés retirés ; P12 corrigé (voie utilisateur « Supprimer puis recréer », plus aucune commande de développement). M1 à M10 couverts : page principale/bandeau (M1), cartes et fenêtre (M2), compteurs (M3), exclure/forcer/revenir/appliquer (M4), republier/supprimer puis recréer (M5), rescan (M6), export (M7), table publié/non publié (M8), états grisés et infobulles (M9), Homebridge (M10).
- Vérifications : recherches négatives dans `docs/fr_FR/` : aucune occurrence de « HA / jeedom2ha », `deploy-to-box`, `evaluate_equipment`, « Mes templates », adresse IP, `generic_type`, identifiant de story dans `index.md`/`compteurs.md`/nouvelle entrée de changelog (les anciennes entrées du changelog, antérieures à cette story, citent encore des stories : non touchées). Cloisonnement des compteurs : `grep -nE "[0-9]+ (équipements? (publiés?|exclus?|désactivés? dans Jeedom|à corriger|non lus?)|commandes? (prêtes?|bloquantes?|non couvertes?))" docs/fr_FR/index.md docs/fr_FR/changelog.md docs/fr_FR/changelog_beta.md docs/index.md` : aucune occurrence (les libellés de compteur n'apparaissent que dans `docs/fr_FR/compteurs.md`).

**R1 — corrections de relecture ClaudeBox (PR #232), 2026-10-11**

Chaque point a été revérifié dans le code avant d'être écrit ; la table de traçabilité a une section 8 « Corrections R1 » et la ligne « Revenir au mode automatique » (entité) est corrigée.

*P1*
1. « Revenir au mode automatique » sur une entité retire aussi les types choisis pour ses commandes (`entity_scope=True`, `fields` = type + publication). Corrigé dans `index.md` (section « Revenir au mode automatique » et colonne « Annulation »), dans la table de traçabilité (ligne ex-105 scindée en équipement / entité) et dans le fait F6 de la story.
2. Les causes « aucun type Home Assistant identifié pour cette commande », « aucun type Home Assistant candidat à valider » et « type HA non ouvert par ce plugin » sont **bloquantes** (seule « commande sans type Home Assistant applicable » est non couverte). Nouvelle famille « Type non publiable » (action : choisir un autre type dans « Override HA » ou revenir au mode automatique) ; la famille « Commande non couverte » ne garde qu'une cause. F4 de la story corrigé.
3. Annexe zone suggérée : « Supprimer puis recréer, puis Rescanner la topologie Jeedom » (« Republier » ne relit pas Jeedom, `http_server.py:3889`) ; « au prochain rescan » ajouté.

*P2*
4. Boutons grisés : seuls les boutons `data-ha-action` (Republier, Appliquer, Supprimer puis recréer, Rescanner) le sont ; « Exclure », « Forcer », « Revenir au mode automatique » et la liste « Override HA » restent actifs. Nommés dans la zone « Actions » et dans le tableau des boutons grisés.
5. Badge d'attente : le signe fiable est « pas encore appliqué » (entité) et le bouton « Appliquer » ; « Override en attente… » seulement si la décision de publier change (`http_server.py:3036`).
6. Exclusion « équipement dans la liste d'exclusions » : réglage propre à l'équipement (clé `jeedom2ha_excluded`, lue seulement à `jeedom2ha.class.php:746`, aucun écran du plugin ne l'écrit). Famille et « que faire » corrigés.
7. MQTT : « Sauvegarder » (bouton de Jeedom) puis (re)démarrage du démon ; installation et première synchronisation adaptées ; « Tester la connexion » et « Récupérer depuis MQTT Manager » précisés.
8. Exemple « Lampe bureau » remplacé par « Lampe tableau » (« eau » dans « tableau », donc non écarté).
9. `changelog.md` : anciennes entrées réécrites pour l'utilisateur (identifiants de story, CC-17, `deploy-to-box.sh`, `generic_type`, rsync, `os.min`, phrase fausse sur les capteurs et légende orpheline retirés). Vérifié par grep.
10. `README.md` : bouton « Diagnostic », « Appliquer et Rescanner », « colonne Raison », « Export de diagnostic » (listé comme à venir), thermostats et scénarios (listés comme à venir alors qu'ils sont publiés), « Debian 12+ » (info.json : 11 et 12) alignés.

*P3* — tous traités : message de repli du rescan ; bandeau relu après Republier/Appliquer/Supprimer puis recréer/rescan seulement ; « Republier la pièce » et « Republier dans Home Assistant » appliquent aussi les réglages en attente ; confirmation d'exclusion « publiée selon le diagnostic » ; grisé de « Supprimer puis recréer » = présence réelle ; « override » ajouté au vocabulaire, « projection », « commande clé », « sûr / probable » et « inclus » glosés (« overrides persistés » glosé dans le rescan) ; `compteurs.md` : « bloquante » réunit des causes corrigeables et d'autres non, « non lu(s) » aussi pendant le chargement, en-tête invisible corrigé (10 tests Node passés avec `node --test`, renvoi au présent motif de grep) ; « Configuration manuelle » seulement si un hôte est enregistré ; « Pièces exclues » : pièce directe seulement, sans sous-pièces ; `switch` : familles « interrupteur » et « ventilateur » ; couleur des lumières non reprise ; rédaction (« Sous l'export de diagnostic », « n'est plus publié(e) » reformulé, « activée… active », sous-section renvoi retirée, puce « Supprimer puis recréer » découpée en trois).
- Apostrophes : contrôle automatisé de tous les libellés entre « » de `index.md` et `compteurs.md` contre le code (apostrophes typographiques ’ comprises). Un écart restant corrigé ; les écarts qui subsistent sont des phrases composées en plusieurs morceaux dans le code ou des termes de la documentation, pas des libellés d'écran.

*AC6 — motif de grep retenu.* Hors `compteurs.md`, aucune correspondance :
`grep -nE '[0-9N] (équipements? (publiés?|exclus?|désactivés?|à corriger|non lus?)|commandes? (prêtes?|bloquantes?|non couvertes?))|équipements? à corriger|équipement\(s\) (publié|exclu|désactivé|à corriger|non lu)|Chargement des compteurs|Compteurs indisponibles|à corriger' docs/fr_FR/index.md docs/fr_FR/changelog.md docs/fr_FR/changelog_beta.md docs/index.md README.md` (code retour 1) ; le même motif donne 8 lignes dans `docs/fr_FR/compteurs.md`. Les libellés de badge d'équipement « N commande(s) prête(s) / bloquante(s) » restent dans `index.md` (acceptés par la relecture ; la forme « (s) » n'est pas couverte par le motif). La phrase « il n'y a rien à corriger » a été reformulée (« aucune correction à faire »).

*Points non vérifiables dans ce dépôt (cœur Jeedom), à confirmer par ClaudeBox ou Alexandre :* le bouton « Sauvegarder » de la fenêtre de configuration et le démarrage du démon par l'installation ; le chemin « Outils → Objets » et le fait que l'identifiant de pièce figure dans l'adresse (`id=`) ; la définition de « sûr » / « probable » (formulée d'après le seul usage de la politique, `decide_publication.py:141`) ; la gloss de « inclus » (exemples tirés des motifs d'inéligibilité).

**Écarts entre la story-source et le code (à relire par ClaudeBox) :**

1. **Nommage des équipements (Task 1.4)** : les listes de mots-clés sont identiques à l'ancienne documentation, mais la correspondance se fait **sur le mot entier** (`\b…\b`, `light.py:202`, `switch.py:168`, `cover.py:183`), pas par sous-chaîne. L'ancien « piège du matching par sous-chaîne » (exemple « bureau » / « eau ») est **faux** au SHA courant ; il est retiré, remplacé par la règle du mot entier.
2. **« Supprimer puis recréer »** : la branche `supprimer` du démon ne fait que **dépublier** (`http_server.py:3993-4098`, drapeau `aucun_flux_supprimer_recree`). La recréation n'est pas faite par ce bouton ; elle suppose un « Republier » ou un rescan ensuite. La documentation le dit ainsi, au lieu de promettre une recréation automatique. Libellé d'interface potentiellement trompeur : à ajouter aux constats pour le backlog.
3. **Scénarios** : les scénarios Jeedom **actifs** sont publiés comme `button` (`http_server.py:2079-2095`, `jeedom2ha.class.php:798-812`). L'ancienne documentation (« Hors périmètre V1 : … scénarios ») et la story-source (P7) ne le disaient pas. Documenté.
4. **Causes « positives »** (F4) : « publication forcée manuellement » et « type Home Assistant identifié — publication normale » n'apparaissent dans la cellule « Diagnostic » que comme motif d'un état *bloquant* (`buildBlockingReason`, `OVR:631-657`, appelé seulement si l'état n'est pas « prêt », `OVR:661-672`). Une commande prête affiche « Sera publié : <type> ». Ces deux libellés ne sont donc **pas** documentés comme causes (pas de situation utilisateur vérifiée où ils s'affichent).
5. **Confirmation de « Republier la pièce »** : texte exact lu dans le code, « <nom> — republier les équipements inclus de cette pièce. Confirmer ? » ; la story-source ne le citait pas. Le bouton « Appliquer »/« Republier » d'un équipement n'a **pas** de confirmation (`SURF:487-512`).
6. **Prérequis** : « Python 3.9+ » et « PHP 8.x » (ancienne documentation) ne sont étayés par aucun fichier de code ou de configuration du plugin (seuls `info.json` : Jeedom 4.4, Debian 11 à 12.99, et la détection de Python 3 par Jeedom le sont) ; ils ont été retirés plutôt que reconduits. À confirmer avec Alexandre si ces versions doivent figurer.
7. **Retraits de l'ancienne documentation non étayés par le code** : « après un redémarrage du démon, les entités redeviennent pilotables automatiquement », « entités dupliquées après changement d'identifiant » (dépannage) et la logique de persistance du broker : aucun élément vérifiable dans les fichiers lus, retirés ; remplacés par la recommandation « Republier dans Home Assistant ».
8. **Cloisonnement des compteurs (AC6)** : les libellés par équipement du badge de synthèse (« … N commande(s) prête(s). », « … M bloquante(s). ») et le message du bouton « Appliquer les filtres et rescanner » de la configuration (« équipement(s) publié(s) ») utilisent des mots proches des compteurs. Ce ne sont pas des libellés de compteur de la modale (forme avec « (s) » et chiffre variable) ; le grep d'AC6 est donc défini sur la forme réellement affichée par les compteurs (chiffre + libellé). À trancher par ClaudeBox : accepter, ou demander que la story « compteurs » réconcilie aussi ces deux libellés.
9. **Branche** : la story évoquait `story/20-5-dev-story` ; la session est contrainte à la branche `claude/user-documentation-rewrite-zlq19s`, utilisée à la place (préfixe `claude/` accepté par la CI).
10. Constat déjà noté dans la story, confirmé : mots « démon » / « daemon » / « Bridge » pour une même chose ; « V1 » et « Jeedom2HA »/« jeedom2ha » dans les causes. La documentation reprend la formule de l'écran et la glose.

### File List

- `_bmad-output/implementation-artifacts/20-5-documentation-utilisateur-reecrite-cc07d.md` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (ligne 20-5 et `last_updated`)

*Ajouts du `dev-story` :*

- `docs/fr_FR/index.md` (réécrit)
- `docs/fr_FR/compteurs.md` (nouveau, bloc isolé)
- `docs/fr_FR/changelog.md` (entrée du 2026-10-11)
- `docs/fr_FR/changelog_beta.md` (réécrit)
- `docs/index.md` (index des fichiers de `fr_FR`)
- `README.md` (R1 : bouton « Diagnostic » et « Appliquer et Rescanner » remplacés par les libellés réels, passages périmés alignés)
- `_bmad-output/implementation-artifacts/20-5-tracabilite-documentation.md` (nouveau, table de traçabilité)
- `_bmad-output/implementation-artifacts/20-5-documentation-utilisateur-reecrite-cc07d.md` (cases cochées, Dev Agent Record)

*Ajouts de la clôture :*

- `_bmad-output/planning-artifacts/epics-projection-engine.md` (pe-epic-20 passé `done`)
- `_bmad-output/implementation-artifacts/pe-epic-20-retro-2026-10-11.md` (nouveau, rétrospective)

### Change Log

- 2026-10-11 — Création de la story 20.5 (`create-story`, statut `backlog`).
- 2026-10-11 — R1 (relecture ClaudeBox, PR #232) : corrections P1 (Revenir au mode automatique sur une entité, famille « type non publiable », annexe zone suggérée), P2 (boutons grisés nommés, badge d'attente, exclusion d'équipement, MQTT « Sauvegarder » + démon, exemple neutre, anciennes entrées du changelog, README) et P3 ; voir « R1 » du Dev Agent Record. Statut inchangé.
- 2026-10-11 — `dev-story` (session cloud déléguée) : Tasks 1 à 4 faites, documentation utilisateur réécrite sous `docs/fr_FR/`, table de traçabilité en annexe, écarts signalés ; Task 6.1 préparée (PR non fusionnée) ; statut inchangé (`ready-for-dev`) dans l'attente de la relecture ClaudeBox.
- 2026-10-11 — Clôture : relecture ClaudeBox et relecture indépendante (PR #232, deux rondes) ; story `done` ; ferme CC-07 d ; `pe-epic-20` passé `done`, rétrospective `pe-epic-20-retro-2026-10-11.md`.
