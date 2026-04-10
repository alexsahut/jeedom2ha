**Document de cadrage**

Plugin Jeedom de publication automatique vers Home Assistant

Projet cible : plugin Jeedom avec démon, appuyé sur MQTT Discovery pour
exposer automatiquement équipements, commandes utiles et scénarios dans
Home Assistant.

  ------------------------------------------------------------------
  **Décision de cadrage\**
  Construire une V1 80/20 qui couvre très bien les équipements
  standards déjà correctement typés dans Jeedom, plutôt que chercher
  une compatibilité totale dès le départ. Les types génériques
  constituent le principal accélérateur, mais ils ne remplacent ni
  le moteur de mapping, ni la gestion du round-trip état/commande,
  ni la découverte/suppression MQTT côté Home Assistant.
  ------------------------------------------------------------------

  ------------------------------------------------------------------

  ------------------------------------------------------------------
  Objectif V1      Retrouver automatiquement dans Home Assistant les
                   principaux équipements Jeedom pilotables au
                   quotidien, avec état fiable et commande retour.
  ---------------- -------------------------------------------------
  Ce qui est       Lumières, prises/switchs, volets, capteurs
  inclus           simples, thermostats simples, scénarios basiques,
                   filtres d'exposition, rescan, renommage,
                   suppression propre.

  Ce qui est       Import massif d'historique, graphes Jeedom natifs
  reporté          dans HA, plugins exotiques, caméras avancées,
                   compatibilité exhaustive de toutes les commandes.
  ------------------------------------------------------------------

# 1. Contexte et opportunité

**Constat.** L'utilisateur souhaite profiter des avantages de Home
Assistant (Assist, langage naturel, écosystème, MCP côté HA, tableaux de
bord) sans migrer sa logique domotique hors de Jeedom. L'idée produit
consiste donc à publier automatiquement la maison Jeedom vers Home
Assistant, afin que HA devienne une façade de consommation et
d'interaction, tandis que Jeedom reste le moteur d'exécution.

**Hypothèse structurante.** Les types génériques Jeedom sont déjà
largement exploités par le core et par des plugins comme Homebridge,
Google Smarthome ou Alexa. Ils permettent donc d'accélérer fortement le
mapping V1, car une grande partie de la sémantique de haut niveau est
déjà présente dans l'installation cible.

  ------------------------------------------------------------------
  **Important - ce que les types génériques accélèrent, et ce qu'ils
  ne résolvent pas\**
  Ils accélèrent : la qualification de l'équipement, le choix du
  type d'entité HA, et la couverture des cas standards. Ils ne
  résolvent pas : la publication MQTT Discovery, la gestion des
  renommages/suppressions, les états de scénarios, les exclusions
  utilisateur, les commandes atypiques, ni le round-trip fiable
  état/commande.
  ------------------------------------------------------------------

  ------------------------------------------------------------------

# 2. Vision produit

- Jeedom conserve la logique métier, les scénarios, les plugins
  matériels, les automatismes et les historiques natifs.

- Home Assistant récupère automatiquement les équipements utiles sous
  forme d'entités natives, prêtes pour le pilotage, les dashboards,
  Assist et le MCP Server de HA.

- L'utilisateur n'a pas à recoder un nouvel équipement : il doit
  seulement l'intégrer correctement dans Jeedom et, idéalement, lui
  affecter les bons types génériques.

- Le produit doit être simple à comprendre : "je publie Jeedom vers HA
  sans migration".

# 3. Objectifs de la V1

- Publier automatiquement dans Home Assistant les équipements Jeedom du
  quotidien déjà bien typés.

- Permettre la commande retour HA -\> Jeedom avec latence faible et état
  cohérent.

- Rendre le plugin utilisable sans configuration lourde : un assistant
  minimal, quelques filtres, puis synchronisation.

- Fournir de la visibilité sur le mapping : pourquoi un équipement est
  exposé, ou non.

- Conserver un périmètre volontairement restreint pour sortir vite une
  V1 robuste.

# 4. Non-objectifs de la V1

- Couvrir 100 % des plugins Jeedom et de leurs commandes exotiques.

- Importer l'historique complet Jeedom dans la base historique de HA.

- Reproduire tous les widgets graphiques Jeedom ou leurs graphes dans
  Home Assistant.

- Créer un serveur MCP Jeedom natif dans cette première phase.

- Supporter en profondeur les caméras, interphones, multimédia avancé,
  alarmes complexes et équipements non standardisés.

# 5. Périmètre fonctionnel V1 recommandé

  ------------------------------------------------------------------
  Famille         Décision V1 Règle de mapping    Commentaires
  --------------- ----------- ------------------- ------------------
  Lumières        Inclus      light si commandes  Priorité haute ;
                              ON/OFF + état ;     excellent cas
                              dimmer si niveau    d'usage Assist /
                              disponible          Apple Maison /
                                                  dashboards

  Prises / relais Inclus      switch              Très simple à
                                                  supporter, forte
                                                  valeur immédiate

  Volets          Inclus      cover avec          Tester les cas
                              open/close/stop ;   sans retour de
                              position si         position
                              disponible          

  Capteurs        Inclus      sensor /            Température,
  simples                     binary_sensor       humidité,
                                                  puissance,
                                                  présence,
                                                  ouverture, fuite,
                                                  etc.

  Thermostats     Inclus avec climate si le       Ne pas forcer un
  simples         prudence    modèle est clair ;  faux climate si la
                              sinon sensor +      structure Jeedom
                              switch/number       n'est pas
                                                  suffisante

  Scénarios       Inclus      button run + switch Valeur forte pour
                  basique     enable/disable +    les "modes maison"
                              état si exposable   

  Caméras         Hors V1     ---                 À traiter plus
                                                  tard

  Historique      Hors V1     ---                 HA construit son
  Jeedom                                          historique à
                                                  partir du
                                                  démarrage de la
                                                  synchro
  ------------------------------------------------------------------

# 6. Hypothèses de mapping

- 1 eqLogic Jeedom = 1 device Home Assistant.

- Les commandes Info deviennent des entités de lecture (sensor /
  binary_sensor) quand leur nature est déterminable.

- Les commandes Action deviennent des entités pilotables (light, switch,
  cover, button, number, select) selon les types génériques et, en
  secours, le type/sous-type.

- Les identifiants techniques reposent sur les IDs Jeedom, pas sur les
  noms, pour survivre aux renommages.

- Les objets Jeedom servent de base à l'area / au nom d'affichage dans
  Home Assistant.

# 7. Architecture cible V1

  ------------------------------------------------------------------
  **Plugin Jeedom  Configuration, filtres d'exposition, gestion du
  (PHP)**          démon, pages de diagnostic, actions de rescan et
                   de republishing.
  ---------------- -------------------------------------------------
  **Démon**        Processus actif responsable du bootstrap, du
                   cache local, du mapping, des publications MQTT
                   Discovery, des abonnements de commande et de la
                   réconciliation.

  **Accès Jeedom** Lecture du modèle Jeedom depuis le plugin/core ;
                   usage des concepts du core et compatibilité avec
                   les APIs documentées côté Jeedom.

  **Transport      Appui sur MQTT Manager comme prérequis V1 pour
  MQTT**           éviter de réinventer le socle MQTT et bénéficier
                   d'un environnement déjà Jeedom-compatible.

  **Home           Consommateur MQTT Discovery, création des devices
  Assistant**      et entités, Assist, dashboards, automations, MCP
                   Server officiel HA.

  **Stockage local Table de correspondance Jeedom ID -\> objet HA,
  du plugin**      empreinte de config, statut de publication,
                   version du mapping, exclusions utilisateur.
  ------------------------------------------------------------------

# 8. Flux principaux

1.  Bootstrap : scan initial des objets, équipements, commandes et
    scénarios ; calcul du mapping ; publication Discovery + états
    initiaux.

2.  Commande : Home Assistant publie sur command_topic ; le démon
    reçoit, résout la cible Jeedom, exécute la commande puis republie
    l'état réel dès qu'il est connu.

3.  Mise à jour : sur changement d'état Jeedom, publication immédiate
    sur les state topics concernés.

4.  Réconciliation : rescan périodique pour détecter nouvel équipement,
    suppression, renommage ou évolution de typage.

5.  Redémarrage HA : réémission de la discovery sur le birth message
    homeassistant/status = online.

# 9. Backlog produit V1

  --------------------------------------------------------------------
  Lot   Epic              Livrables                      Priorité
  ----- ----------------- ------------------------------ -------------
  L1    Socle plugin      Squelette plugin, info.json,   P0
                          configuration, gestion démon,  
                          logs, prérequis MQTT Manager   

  L2    Inventaire Jeedom Lecture                        P0
                          objets/eqLogic/cmd/scénarios ; 
                          cache local ; identifiants     
                          stables                        

  L3    Moteur de mapping Règles via types génériques ;  P0
                          fallback type/sous-type ;      
                          exclusions ; compatibilité V1  

  L4    Publication HA    MQTT Discovery device-based,   P0
                          state topics, command topics,  
                          availability                   

  L5    Commande retour   Exécution fiable des commandes P0
                          HA -\> Jeedom et confirmation  
                          d'état                         

  L6    Scénarios         Run / enable / disable +       P1
                          statut si disponible           

  L7    Réconciliation    Rescan, renommage, suppression P1
                          propre, nettoyage d'orphelins  

  L8    UX & diagnostic   Vue "pourquoi exposé / non     P1
                          exposé", tests, documentation  
                          d'installation                 
  --------------------------------------------------------------------

# 10. Critères d'acceptation V1

- Après activation, le plugin détecte et publie automatiquement au moins
  les lumières, prises, volets et capteurs simples correctement typés.

- Un renommage d'équipement dans Jeedom ne crée pas de doublon HA et
  conserve l'identité technique.

- Une suppression dans Jeedom entraîne la suppression propre de
  l'entité/device découverte dans HA.

- Une commande "allumer/éteindre" émise depuis HA agit correctement sur
  Jeedom et l'état visible dans HA reste cohérent.

- Le plugin fournit un journal exploitable et une vue de diagnostic
  minimale.

- L'utilisateur peut exclure un équipement ou une famille sans modifier
  le code.

# 11. Risques et décisions de conception

  ----------------------------------------------------------------
  Risque           Effet                       Décision V1
  ---------------- --------------------------- -------------------
  Types génériques Mapping insuffisant ou faux Assumer une
  incomplets       type HA                     dégradation
                                               élégante :
                                               sensor/button
                                               plutôt qu'un type
                                               "riche" incorrect ;
                                               exposer un
                                               diagnostic clair.

  Commandes        Support partiel de certains Limiter la V1 aux
  atypiques selon  équipements                 familles standards
  plugin                                       ; documenter les
                                               exclusions.

  État Jeedom non  Écart momentané entre       Préférer l'état
  immédiatement    action et état              réel ; éviter le
  relisible                                    mode optimiste
                                               quand c'est
                                               possible.

  Volume important Charge MQTT/HA au           Réémettre
  de discovery     redémarrage                 intelligemment sur
                                               le birth message et
                                               maîtriser la
                                               volumétrie.

  Temps partiel du Risque de dispersion        Protéger le
  projet                                       périmètre V1 et
                                               refuser les
                                               demandes hors
                                               scope.
  ----------------------------------------------------------------

# 12. Planning indicatif à 5 h/semaine

- Semaines 1 à 3 : squelette plugin, démon, lecture inventaire Jeedom,
  premiers tests locaux.

- Semaines 4 à 6 : mapping V1, publication MQTT Discovery, premiers
  équipements visibles dans HA.

- Semaines 7 à 9 : commandes retour HA -\> Jeedom, états cohérents,
  disponibilité, logs.

- Semaines 10 à 12 : scénarios, rescan, renommage, suppression,
  exclusions.

- Semaines 13 à 16 : UX de configuration, diagnostic, documentation,
  bêta privée.

- Au-delà : fiabilisation, edge cases, préparation Market, bêta publique
  puis stable.

# 13. Brief de lancement pour les agents BMAD

Mission : concevoir et livrer une V1 de plugin Jeedom qui publie
automatiquement vers Home Assistant les équipements Jeedom standards
déjà correctement typés, avec un haut niveau de fiabilité et un
périmètre strictement limité. Le projet ne doit pas viser la couverture
exhaustive de Jeedom en V1.

  ----------------------------------------------------------------------------
  Agent          Responsabilité                      Sortie attendue
  -------------- ----------------------------------- -------------------------
  PO / Product   Verrouiller le scope V1, rédiger    Backlog priorisé + user
                 user stories, définir DoD et        stories + non-objectifs
                 arbitrages                          explicites

  Architecte     Définir modèle de données, mapping, ADR d'architecture +
                 topics MQTT, stratégie de           conventions + schémas
                 réconciliation                      

  Dev Plugin     Créer plugin PHP, config, gestion   Plugin installable +
                 démon, pages diagnostic             écran de config + logs

  Dev Démon      Implémenter bootstrap, cache,       Démon fonctionnel + tests
                 mapping, discovery, exécution des   d'intégration locaux
                 commandes                           

  QA             Définir matrice de tests, tests de  Plan de test + rapport de
                 renommage/suppression/redémarrage   non-régression

  Doc            Rédiger doc d'installation, limites Documentation utilisateur
                 V1, FAQ de dépannage                et développeur
  ----------------------------------------------------------------------------

# 14. Première liste de user stories

- En tant qu'utilisateur Jeedom, je veux retrouver automatiquement mes
  lumières, prises, volets et capteurs simples dans Home Assistant sans
  reconfigurer chaque équipement.

- En tant qu'utilisateur Home Assistant, je veux pouvoir commander une
  entité publiée et voir son état réel remonter correctement.

- En tant qu'utilisateur avancé, je veux exclure certains équipements ou
  familles pour garder un espace HA propre.

- En tant que bêta-testeur, je veux comprendre pourquoi un équipement
  n'est pas exposé pour pouvoir corriger mes types génériques ou mon
  paramétrage.

- En tant que mainteneur du plugin, je veux des identifiants stables et
  des logs exploitables afin de diagnostiquer les incidents sans
  manipulations lourdes.

# 15. Réponse à la question clé : "avec mes types génériques déjà bien en place, cela devrait aller très vite, non ?"

  ------------------------------------------------------------------
  **Réponse courte : oui pour la V1, non pour l'ensemble du
  produit.\**
  Oui, parce que les types génériques t'évitent une grande partie du
  travail de classification et rendent réaliste une V1 utile
  couvrant vite les cas standards. Non, parce qu'un plugin publiable
  doit encore résoudre la création des entités HA, la stratégie MQTT
  Discovery, la commande retour, la cohérence d'état, la suppression
  propre, la réconciliation et l'expérience utilisateur.
  ------------------------------------------------------------------

  ------------------------------------------------------------------

- Gain réel attendu : le coeur de la sémantique de tes équipements du
  quotidien est déjà largement présent ; la V1 devient donc crédible
  avec un faible paramétrage complémentaire.

- Ce qui restera chronophage : robustesse, cas limites, UX de config,
  documentation, packaging Market et tests réels.

- Décision de cadrage : exploiter à fond les types génériques comme
  premier moteur de mapping, et refuser en V1 les cas que ces types ne
  permettent pas de classifier proprement.

# 16. Références officielles à utiliser par l'équipe

- Jeedom - Types génériques :
  https://doc.jeedom.com/fr_FR/core/4.4/types

- Jeedom - Plugin Google SmartHome (exemple d'usage des types
  génériques) :
  https://doc.jeedom.com/fr_FR/plugins/communication/gsh/beta/

- Jeedom - Plugin Alexa SmartHome (exemple d'usage des types génériques)
  : https://doc.jeedom.com/fr_FR/plugins/communication/ash/

- Jeedom - Démons et dépendances :
  https://doc.jeedom.com/fr_FR/dev/daemon_plugin

- Jeedom - Publication Market :
  https://doc.jeedom.com/fr_FR/dev/publication_plugin

- Home Assistant - MQTT Discovery :
  https://www.home-assistant.io/integrations/mqtt/
