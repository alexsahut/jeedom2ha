# Story 20.5 — Annexe : table de traçabilité « affirmation → fichier:ligne »

Annexe de `20-5-documentation-utilisateur-reecrite-cc07d.md` (AC1, Task 4.1). Elle couvre les affirmations factuelles sur le comportement de l'interface de `docs/fr_FR/index.md` et `docs/fr_FR/compteurs.md`.

- **Référence de vérité :** code de `main` au SHA `8a1d01b` (le code de l'interface est identique à celui du SHA `3b120d3` : `git diff 3b120d3 8a1d01b` ne touche que des fichiers de story et `sprint-status.yaml`).
- **Aucune affirmation n'est tirée d'un fichier de story.** Chaque ligne cite le code.
- Abréviations : `PHP` = `desktop/php/jeedom2ha.php` ; `PAGE` = `desktop/js/jeedom2ha.js` ; `SURF` = `desktop/js/jeedom2ha_mapping_surface.js` ; `OVR` = `desktop/js/jeedom2ha_mapping_override.js` ; `CONF` = `plugin_info/configuration.php` ; `HTTP` = `resources/daemon/transport/http_server.py` ; `AJAX` = `core/ajax/jeedom2ha.ajax.php` ; `BUDGET` = `core/php/jeedom2ha_action_budget.php`.

## 1. Page principale

| Affirmation de la documentation | Source |
|---|---|
| Bloc « Gestion » : une seule vignette « Configuration » | PHP:62-65 |
| Bandeau : quatre indicateurs Bridge, MQTT, Dernière synchro, Dernière opération | PHP:67-87 |
| Le bandeau est lu à l'ouverture de la page (pas de rafraîchissement automatique) et relu après les actions | PAGE:430-432 (« no auto-refresh »), PAGE:370, 395, 414 ; SURF:668, 505 |
| Bridge : « Actif » (vert) | PAGE:53 |
| Bridge : « Arrêté » (rouge), MQTT « Inconnu », synchro « Inconnue », opération « Inconnue » si le démon est arrêté | PAGE:42-51 |
| Bridge : « Erreur Jeedom » (rouge) | PAGE:25-31 |
| Bridge : « Erreur de communication » (rouge) | PAGE:109-114 |
| MQTT : « Connecté » (vert) | PAGE:59-61 |
| MQTT : « Reconnexion... » et « Connexion... » (orange) | PAGE:62-67 |
| MQTT : « Déconnecté » (rouge) | PAGE:68-71 |
| MQTT : « Non configuré » (autres états) | PAGE:72-74 |
| L'adresse du broker s'affiche à côté de MQTT | PAGE:75 ; PHP:76 |
| Dernière synchro : date jour/mois heures:minutes:secondes ; « Jamais » | PAGE:77-84 |
| Dernière opération : « Succès » (vert) | PAGE:89-91 |
| Dernière opération : « Partiel » et « Échec » (orange, problème de configuration) | PAGE:92-99 |
| Dernière opération : « Aucune » ; message affiché à côté | PAGE:100-102, 106 ; OVR:1039-1056 |
| Zone « Actions Home Assistant » avec trois boutons : « Republier dans Home Assistant », « Rescanner la topologie Jeedom », « Supprimer puis recréer dans Home Assistant » | PHP:92-121 (libellés :99, 107, 114) |
| Les boutons sont grisés tant que le démon ne tourne pas ou que MQTT n'est pas connecté | PAGE:125-129, 136-162 |
| Motifs affichés : « Daemon arrêté — actions Home Assistant bloquées. » / « MQTT déconnecté — actions Home Assistant bloquées. » / « Bridge ou MQTT indisponible — actions Home Assistant bloquées. » | PAGE:154-159 ; conteneur PHP:117-120 |
| Les boutons sont grisés pendant un rescan | PAGE:141-144, 350 |
| Les boutons d'action des fenêtres de pièce suivent la même règle | SURF:589-593, 957-959, 1114-1118 |
| Confirmation du rescan : « Un sync complet peut publier ou retirer des entités Home Assistant et applique les overrides persistés. Confirmer ? », bouton « Rescanner » | PAGE:164-172 |
| Rescan : libellé « Confirmation en cours… » puis « Rescan en cours… » | PAGE:437, 349 |
| Rescan : messages « Synchronisation terminée. » (vert), « Synchronisation échouée. » (rouge), « Synchronisation terminée avec avertissements. » (orange), remplacés par le message du démon s'il existe | PAGE:360-369 |
| Rescan : « Une opération est déjà en cours ou le rescan a échoué. » | PAGE:357, 373 |
| Rescan : « Erreur de communication : relire Dernière synchro avant de relancer. » | PAGE:379 |
| Rescan : le bandeau est relu ensuite | PAGE:370, 375 |
| « Republier dans Home Assistant » (parc) : confirmation « Republier tous les équipements inclus ? », bouton « Republier » | PAGE:450-469 (texte :460, bouton :461) |
| « Supprimer puis recréer » (parc) : « Supprimer puis recréer tout le parc publié ? », avertissement « Attention : l'historique, les dashboards, les automatisations et l'entity_id liés à ces entités peuvent être impactés. », bouton « Supprimer », confirmation rouge | PAGE:472-491 (:480-483), PAGE:425-428 |
| Libellés pendant une action : « Confirmation en cours… », « En cours... », « Suppression... » | PAGE:437, 457, 478 ; PAGE:388, 407 |
| Message de résultat précédé du nom de la portée ; vert (succès), orange (succès partiel), rouge sinon | PAGE:174-193 ; nom de portée « Parc global » / nom de la pièce / nom de l'équipement : HTTP:597-624 |
| Messages d'erreur « Le démon ne répond pas. » | SURF:239, 295, 310, 511 |
| « Erreur de communication avec le backend Home Assistant. » ; « Réponse backend incomplète pour l'action Home Assistant. » | PAGE:325, 334 |
| Export : case « Pseudonymiser les noms d'équipements » et bouton « Télécharger le diagnostic support » | PHP:124-135 (:128, 131) |
| Export : messages « Export en cours... », « Diagnostic téléchargé », « Erreur export », « Erreur de communication » | PAGE:498, 524, 512, 528 |
| Fichier `jeedom2ha-diagnostic-AAAA-MM-JJ.json` | PAGE:518-521 |
| Pseudonymisation : « Équipement_N », « Pièce_M », « Cmd_<id> » | AJAX:217-246 |
| Pseudonymisation : adresse du broker masquée | AJAX:738-743 |
| Message « Démon indisponible ou timeout — relancez le démon et réessayez. » | AJAX:728 |
| Section « Configuration Home Assistant par pièce » et son texte d'information | PHP:139-143 |
| Carte par pièce : nom + nombre d'équipements entre parenthèses ; « Aucune pièce avec équipement trouvée. » | PHP:145-158 (:146, 153-154) |
| Pièce sans équipement : pas de carte | PHP:25-27 ; OVR:754-759 |
| Carte « Sans pièce » regroupant les équipements sans pièce | PHP:35-55 (:51) |
| Équipements désactivés comptés et listés | PHP:13-23, 38-46 (`byObjectId(..., false)`, champ `enabled`) |
| Équipements du plugin jeedom2ha écartés | PHP:16-18, 39-41 |

## 2. Fenêtre de pièce, panneau d'équipement, entités

| Affirmation de la documentation | Source |
|---|---|
| Un clic sur la carte ouvre la fenêtre portant le nom de la pièce | PHP:150 ; SURF:1086-1111, 1145-1150 |
| Lecture limitée aux équipements de la pièce, déclenchée à l'ouverture | SURF:1131-1140 |
| « Chargement… » dans chaque panneau pendant la lecture | SURF:992 |
| Contenu de la fenêtre : compteurs, actions de pièce, zone de résultat, accordéon d'équipements | SURF:1034-1084 |
| « Republier la pièce » et « Supprimer puis recréer la pièce » | SURF:718-719, 739-740 |
| « Sans pièce » : message « Republication et suppression de pièce indisponibles pour les équipements sans pièce : utilisez les actions de chaque équipement. » | SURF:713-717 |
| « Republier la pièce » : « <nom> — republier les équipements inclus de cette pièce. Confirmer ? », bouton « Republier » | SURF:725-728 |
| « Supprimer puis recréer la pièce » : confirmation rouge, « Supprimer "<nom>" de Home Assistant : tous les équipements publiés de cette pièce. », bouton « Supprimer la pièce » | SURF:746-749 ; confirmation rouge : PAGE:425-428 |
| Zone de résultat (vert / orange / rouge) | SURF:618-625 ; PAGE:174-193 |
| Panneau d'équipement : nom, « (désactivé dans Jeedom) », badge de synthèse | SURF:1049-1066 |
| Erreurs de lecture : « Impossible de lire la configuration de cet équipement. », « Impossible de charger la configuration HA (daemon indisponible). » ; aucune action proposée | SURF:894-909, 915-917, 1009, 1019 |
| « Aucune commande à configurer pour cet équipement. » | SURF:961-964 |
| Badge « Override en attente — pas encore republié vers Home Assistant » | SURF:822-830 ; OVR:392-394 |
| Lien « Voir la première commande bloquante », défile jusqu'à la commande et la met en évidence | SURF:799-816 |
| Boutons de l'équipement : « Exclure », « Forcer », « Revenir au mode automatique », puis « Appliquer »/« Republier », puis « Supprimer puis recréer » | SURF:940-956 ; SURF:837-859 |
| Entités Home Assistant : type ou « Entité HA », « Commandes : … » ou « Aucune commande regroupée », badge « pas encore appliqué », boutons propres | SURF:872-890, 863-870 ; OVR:399-401 |
| Tableau des commandes : colonnes « Commande », « Type Jeedom », « Override HA », « Diagnostic » | SURF:968-975 |
| « Type Jeedom » en lecture seule | SURF:104-106 |
| Liste « Override HA » : « — mode automatique — » + les huit types | SURF:41-53 ; OVR:18-27 |
| Vérification après une courte attente (400 ms) | SURF:18, 142-144 |
| Le choix valide est enregistré automatiquement (« Sera publié : <type> ») ; sinon rien n'est enregistré | SURF:170-205 (:193-198) ; OVR:514-533 |
| Choisir « — mode automatique — » annule le choix de type | SURF:138-141 |
| Icône « Revenir au type automatique » (type seulement) | SURF:120-122, 148-165 |
| Un type enregistré n'est pas publié tout de suite (badge d'attente, « Appliquer ») | SURF:822-830, 943-954 ; OVR:58-72 |
| Liste grisée avec infobulles : « Commande exclue de Jeedom2HA : son type HA ne peut pas être réglé ici. » / « Équipement désactivé dans Jeedom : son type HA ne peut pas être réglé ici. » / « Aucun type Home Assistant ne couvre cette commande : son type HA ne peut pas être réglé ici. » | OVR:695-707 ; SURF:111-115 |
| Commande non couverte : icône d'interdiction + « Ne sera pas publié — commande sans type Home Assistant applicable » | SURF:63-67 ; OVR:480-498 |
| Une commande non couverte n'est ni prête ni bloquante | OVR:765-775, 787-790 |
| Bandeau « Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha. » affiché une fois par ouverture de pièce quand une vérification fait apparaître une commande bloquante | SURF:1036-1037, 90-95, 195 ; OVR:709-726 ; réinitialisation à l'ouverture : SURF:1091-1092 |

## 3. Actions de publication

| Affirmation de la documentation | Source |
|---|---|
| Les boutons « Exclure », « Forcer », « Revenir au mode automatique » existent à la portée équipement et à celle de chaque entité | SURF:837-859, 887, 940-941 |
| « Exclure » : confirmation seulement si une entité publiée quitte Home Assistant | SURF:425-441 ; OVR:257-274 |
| Confirmation d'exclusion d'équipement : « Exclure cet équipement de Home Assistant ? » + « Entités qui quitteront Home Assistant : … » ; d'entité : « Exclure cette entité de Home Assistant ? » | SURF:406-419, 437-440 |
| Boutons de confirmation « Annuler » / « Confirmer » | SURF:342-345 |
| « Forcer » : aperçu du démon avant toute écriture, sans écrire | SURF:443-481 |
| Aperçu : « Type HA : … », « Projection valide/invalide pour ce type. », « Commandes qui recevront les ordres : … », « Cette entité sera publiée dans Home Assistant. » | SURF:362-377 |
| Aperçu d'équipement : « Entités concernées par ce forçage : … », « Au moins une entité sera publiée dans Home Assistant. » | SURF:387-404 |
| « Le forçage serait refusé : <raison> » ; « Confirmer » grisé | SURF:370-376, 401, 474-476, 347-349 |
| « Aperçu indisponible — le démon ne répond pas. » | SURF:480 |
| « Revenir au mode automatique » (équipement) retire types et publication ; (entité) retire la publication de l'entité ; pas de confirmation | SURF:854, 935-941 ; HTTP:3338-3348 ; OVR:231-255 |
| « Appliquer » (orange) si réglage en attente, « Republier » sinon ; sans confirmation | SURF:945-950, 487-512 |
| « Appliquer » reste actif avec un réglage en attente (y compris une exclusion) | SURF:951-953 |
| « Supprimer puis recréer » (équipement) : « Supprimer "<nom>" de Home Assistant. » + avertissement, bouton « Supprimer 1 équipement », confirmation rouge | SURF:679-694 |
| « Supprimer puis recréer » supprime seulement, sans republier | HTTP:3993-4098 (aucune publication dans la branche `supprimer`) ; drapeau `aucun_flux_supprimer_recree` HTTP:3909, 3937, 4477 |
| « Republier » publie en tenant compte des overrides enregistrés | HTTP:4252-4262 (`persisted_overrides=overrides_cache`) |
| Résultats : « N équipements mis à jour dans Home Assistant. », « Configuration déjà à jour dans Home Assistant. », « N équipement(s) supprimé(s) de Home Assistant. » | HTTP:627-657 |
| Motifs de boutons grisés (Exclure) : « Entité déjà exclue de Home Assistant. », « Aucune commande clé propre à cette entité. », « Équipement non éligible : l'action serait sans effet. » | OVR:158-165, 173-182, 190 |
| Motifs (Forcer) : « Publication déjà forcée sur cette entité. », « Déjà publiée : forcer n'a pas d'effet. », « Aucun type Home Assistant identifié pour cette entité. », « Type HA hors périmètre de ce plugin. », « Projection invalide pour ce type HA. », « Exclusion posée sur l'équipement : la retirer depuis l'équipement. » | OVR:188-209 |
| Motifs (Revenir) : « Aucun override de publication à retirer. » | OVR:176, 211-212 |
| Motif par défaut « Cette action est sans effet dans l'état courant. » | SURF:846 |
| Motifs Republier/Appliquer (équipement) : « Équipement désactivé dans Jeedom : rien à republier. », « Équipement exclu : rien à republier. » | OVR:976-998 |
| Motif Supprimer puis recréer (équipement) : « Équipement non publié dans Home Assistant : rien à supprimer. » | OVR:976-1006 |
| Motifs de pièce : « Aucun équipement à publier dans cette pièce. », « Aucun équipement publié dans cette pièce. » ; actifs tant que les lectures ne sont pas toutes abouties | OVR:981-982, 1009-1034 ; SURF:595-606 |
| Infobulle propre à chaque bouton grisé | SURF:581-587, 844-846 |
| Messages de délai : « L'action Home Assistant dure plus longtemps que prévu (plus de 60 s). Elle peut se poursuivre côté démon : actualisez la page dans un instant pour voir le résultat. » | BUDGET:63-67 |
| « Le démon ne répond pas (timeout API) — vérifiez qu'il est bien démarré » | BUDGET:69-72 |
| « Le démon a renvoyé une erreur pendant l'action Home Assistant — consultez les logs du plugin » | BUDGET:79-81 |
| « Une action Home Assistant est déjà en cours. » | HTTP:3974 ; BUDGET:167-170 |

## 4. Ce que le plugin publie et pourquoi

| Affirmation de la documentation | Source |
|---|---|
| Huit types publiés : `light`, `cover`, `switch`, `sensor`, `binary_sensor`, `button`, `climate`, `alarm_control_panel` | `resources/daemon/validation/ha_component_registry.py:70` ; `resources/daemon/mapping/registry.py:23-34` |
| `light` : on/off et luminosité ; couleur seule non prise en charge | `resources/daemon/mapping/light.py:1-6, 213-217` |
| `cover` : ouverture/fermeture, arrêt, position | `resources/daemon/mapping/cover.py:1-6` |
| `switch` : prises/interrupteurs ; présence actionnable | `resources/daemon/mapping/switch.py:1-7` ; `resources/daemon/mapping/presence_switch.py:1-6` |
| `sensor`, `binary_sensor` | `resources/daemon/mapping/sensor.py:1-7` ; `resources/daemon/mapping/binary_sensor.py:1-9` |
| `button` : action ponctuelle ; scénarios Jeedom actifs publiés comme boutons | `resources/daemon/mapping/button.py:19-20, 44-47` ; HTTP:2079-2095 ; `core/class/jeedom2ha.class.php:798-812` |
| `climate`, `alarm_control_panel` | `resources/daemon/mapping/climate.py:1-6` ; `resources/daemon/mapping/alarm_control_panel.py:1-7` |
| Badges de synthèse (six libellés) | OVR:836-858 ; états OVR:861-883 ; dénombrement OVR:776-833 |
| « Prête » = diagnostic valide et publiable ; « bloquante » = sinon ; « non couverte » à part | OVR:513-520, 765-775, 799-809 |
| Cellule Diagnostic : « Sera publié : <type> » / « Ne sera pas publié — <cause> » | OVR:661-672 |
| Causes affichées (liste complète des libellés des familles 1 à 8) | OVR:587-618 |
| Exclusions volontaires = cinq causes | OVR:622-628, 679-682 |
| Désactivé : « Ne sera pas publié — équipement désactivé dans Jeedom » | OVR:686-693 |
| Texte technique possible en dernier recours (codes bruts, « <champ> manquant ») | OVR:649-656 |
| Politique de publication : deux valeurs | CONF:136-143 |

## 5. Configuration

| Affirmation de la documentation | Source |
|---|---|
| Vignette « Configuration » ouvre la page de configuration | PHP:64 (`data-action="gotoPluginConf"`) |
| Bandeaux « MQTT Manager détecté — configuration pré-remplie », « Configuration manuelle », « Aucun broker MQTT détecté. Installez MQTT Manager ou saisissez les paramètres manuellement ci-dessous. » | CONF:192-209 |
| Boutons/lien « Récupérer depuis MQTT Manager », « Réinitialiser le formulaire » (vide l'écran sans enregistrer) | CONF:31-36, 274-284 |
| Message « Configuration importée depuis MQTT Manager » | CONF:257 |
| Champs Hôte MQTT, Port MQTT (1883 / 8883), Utilisateur MQTT, Mot de passe MQTT (« Laisser vide pour conserver l'actuel », « Mot de passe déjà configuré »), Activer TLS, Vérifier le certificat (« Décocher pour les certificats auto-signés »), bouton « Tester la connexion » | CONF:45-101 |
| Plugins exclus (virgules, exemple `virtual,zwave,rfxcom`), Pièces exclues (identifiants numériques, exemple `1,5,12`) | CONF:114-131 |
| Bouton « Appliquer les filtres et rescanner » ; messages « Sauvegarde en cours... », « Rescan en cours... », « Appliqué & Rescan terminé » + nombre | CONF:149-152 ; CONF:292-344 (« Sauvegarde en cours... » puis « Rescan en cours... » puis « Appliqué & Rescan terminé » + nombre) |
| Les exclusions de la configuration sont distinctes de « Exclure » | OVR:614-616 (causes « exclu de Jeedom2HA (…) ») vs OVR:607-608 (causes « exclu manuellement (…) ») |
| Prérequis : Jeedom 4.4, Debian 11 et 12 | `plugin_info/info.json` (`require`, `os.min`, `os.max`) |
| Python 3 géré par Jeedom ; message « Python3 introuvable pour le plugin » | `core/class/jeedom2ha.class.php:145-148` |
| Dépendances et démon propres au plugin | `plugin_info/info.json` (`hasDependency`, `hasOwnDeamon`) |

## 6. Annexes

| Affirmation de la documentation | Source |
|---|---|
| Pièce Jeedom transmise comme `suggested_area` | `resources/daemon/discovery/publisher.py:378-379` |
| Changement de pièce détecté et journalisé | HTTP:1032-1076 |
| Mots-clés par type (light / switch / cover) : listes identiques à la documentation | `resources/daemon/mapping/light.py:67-79` ; `resources/daemon/mapping/switch.py:67-72` ; `resources/daemon/mapping/cover.py:56-61` |
| Le mot doit apparaître en entier (expression `\b…\b`) | `resources/daemon/mapping/light.py:202` ; `switch.py:168` ; `cover.py:183` |
| Mot trouvé → cause « un mot du nom de l'équipement écarte ce type » | `light.py:293-295` ; `switch.py:254` ; `cover.py:262` ; OVR:589 |
| Durée des actions : délai fixe de 60 s côté relais | BUDGET:63-67 ; `desktop/js/jeedom2ha_action_budget.js:12` (R = 60) |

## 7. Compteurs (`docs/fr_FR/compteurs.md`)

| Affirmation de la documentation | Source |
|---|---|
| Deux lignes sous le titre de la pièce | SURF:539-569, 1039 |
| « Chargement des compteurs… » ; « Compteurs indisponibles : la configuration des équipements de cette pièce n'a pas pu être lue. » | SURF:547-554 |
| Quatre compteurs d'équipements, dans l'ordre publié / exclu / désactivé / à corriger ; singulier pour 0 et 1 | OVR:942-956 |
| Trois compteurs de commandes : prêtes / bloquantes / non couvertes | OVR:957-961 |
| « N équipement(s) non lu(s) » | OVR:962-964 ; SURF:567 |
| « Publié » = badge « Sera publié… » ou « Partiellement publié… » | OVR:922-931 |
| « À corriger » = au moins une commande bloquante ; un équipement partiellement publié compte dans les deux | OVR:925-934 |
| Les commandes exclues ou d'un équipement désactivé ne sont comptées dans aucun des trois compteurs de commandes | OVR:787-798, 935-937 |
| Les compteurs se recalculent à chaque équipement lu ou rechargé | SURF:896-924 |
