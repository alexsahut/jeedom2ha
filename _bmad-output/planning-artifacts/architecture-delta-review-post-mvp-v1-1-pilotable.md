---
document_type: architecture_delta_review
project: jeedom2ha
phase: post_mvp_phase_1
version_label: v1_1_pilotable
date: 2026-03-22
status: ready_for_epic_planning_with_delta_guardrails
source_documents:
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-post-mvp-refresh.md
  - _bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/project-context.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/prd.md
---

# Revue d'architecture delta - Post-MVP V1.1 Pilotable

## 1. Executive summary

Le socle actuel de `jeedom2ha` est **compatible avec la V1.1 Pilotable sans refonte complète**.

Le point fort du socle est clair: la logique critique est deja largement centralisee autour d'un pipeline unique `topologie -> eligibilite -> mapping -> decision de publication -> publication MQTT -> diagnostic`. Cette base est saine pour proteger la predictibilite, l'explicabilite, la stabilite des identifiants et la maintenabilite.

La V1.1 ne demande donc pas une nouvelle architecture. Elle demande un **addendum structurel cible** sur quatre sujets seulement:

1. **Un modele canonique du perimetre publie** qui rende explicite la hierarchie `global -> piece -> equipement`.
2. **Un contrat d'operations explicites** qui distingue clairement `Republier` et `Supprimer/Recreer` a toutes les portees.
3. **Un moteur de statuts / raisons lisibles unifie cote backend**, pour ne pas disperser la logique entre daemon, PHP et JS.
4. **Un contrat minimal de sante du pont** incluant la derniere synchronisation, sans introduire une couche d'observabilite lourde.

Verdict de synthese:
- **Oui, l'architecture est suffisamment cadree pour lancer l'epic planning.**
- **Non, elle n'est pas prete a etre decoupee proprement si ces quatre decisions restent implicites.**

## 2. Ce qui reste valide dans l'architecture actuelle

Les fondations de l'architecture initiale restent bonnes et doivent etre conservees.

### 2.1 Jeedom reste correctement la source de verite

Le socle continue de reposer sur une extraction de topologie depuis Jeedom, sans base metier parallele ni table SQL custom. Cela reste parfaitement aligne avec les principes produit:
- Jeedom conserve la verite metier.
- Le daemon ne porte qu'un cache technique, non autoritatif.
- Le fallback radical `purge cache + rescan complet` reste sain pour la V1.1.

### 2.2 Le coeur de decision est deja centralise

L'architecture actuelle dispose deja d'un point de convergence solide:
- normalisation de la topologie,
- evaluation d'eligibilite,
- mapping centralise par domaine,
- decision de publication,
- publication / depublication,
- diagnostic.

Cette centralisation est un atout majeur pour la V1.1, car elle permet d'ajouter du pilotage sans dupliquer la logique metier dans plusieurs couches.

### 2.3 Les invariants de cycle de vie sont deja utiles pour la V1.1

Les briques suivantes sont deja en place et reutilisables:
- identifiants techniques stables bases sur les IDs Jeedom,
- gestion des renommages sans casser le `unique_id`,
- nettoyage des entites supprimees,
- prise en compte des retypages,
- republication apres reconnect broker ou birth HA,
- gestion de `pending unpublish` en cas d'indisponibilite temporaire du broker.

Ce socle est suffisant pour soutenir la promesse de predictibilite de la V1.1.

### 2.4 Le diagnostic actuel constitue un bon noyau d'explicabilite

Le backend produit deja:
- un `reason_code`,
- un detail lisible,
- une remediation,
- une traceabilite minimale,
- un export support.

Il existe donc deja un embryon de moteur de statuts explicables. Il faut l'etendre et le clarifier, pas le remplacer.

### 2.5 La separation transport interne / transport MQTT reste la bonne decision

Le choix `HTTP local pour PHP <-> daemon` et `MQTT pour HA` reste pleinement valide.

Pour la V1.1, c'est meme un avantage:
- les operations de controle ne dependent pas du broker pour exister,
- l'etat du pont peut rester lisible meme en incident MQTT,
- on evite un couplage excessif entre pilotage et transport MQTT.

### 2.6 Le socle est deja testable

Le code actuel montre deja une testabilite correcte sur le coeur Python:
- exclusions,
- diagnostic,
- cleanup,
- bootstrap,
- synchronisation de commandes.

Cela confirme qu'une evolution V1.1 bien cadree peut rester testable sans refonte.

## 3. Ce que V1.1 change du point de vue architecture

La V1.1 change moins la profondeur technique du produit que sa forme d'exploitation.

### 3.1 Passage d'un bridge publieur a un bridge pilotable

Le MVP etait surtout un moteur de projection et de diagnostic.  
La V1.1 devient un produit de **maitrise du perimetre publie**.

Architecturalement, cela impose:
- un modele canonique du perimetre,
- des portees d'action explicites,
- une logique de statut plus structuree,
- une sante minimale exposee comme contrat, pas seulement comme effet secondaire.

### 3.2 Passage d'une exclusion plate a une hierarchie de decision

Le socle actuel sait deja marquer un equipement comme exclu, avec une source d'exclusion.  
La V1.1 doit aller plus loin et rendre explicite:
- la regle globale,
- la regle de piece,
- l'exception equipement,
- la source de la decision effective.

### 3.3 Passage d'un sync global a des operations a portee lisible

Le socle actuel expose surtout une synchronisation globale.  
La V1.1 doit faire exister des operations coherentes:
- au niveau global,
- au niveau piece,
- au niveau equipement.

Ce n'est pas un probleme de transport. C'est un probleme de **modele d'orchestration**.

### 3.4 Passage d'un diagnostic principal a une console de pilotage

Aujourd'hui, le diagnostic regroupe deja des informations par piece.  
Mais la V1.1 a besoin d'un cran supplementaire:
- le diagnostic ne suffit plus,
- il faut un modele d'etat pilotable,
- il faut distinguer decision locale, effet applique a HA et incident d'infrastructure.

## 4. Points de tension ou risques d'architecture a anticiper

### R1. Modele de perimetre actuellement trop aplati

Le socle transporte aujourd'hui surtout un resultat effectif d'exclusion (`is_excluded` + `exclusion_source`).

Cela suffit pour:
- exclusion equipement,
- exclusion plugin,
- exclusion objet/piece.

Cela ne suffit pas proprement pour:
- exprimer l'heritage `global -> piece -> equipement`,
- distinguer `heritage` et `exception locale`,
- rendre lisible une inclusion locale dans une piece exclue,
- tester de facon deterministe les cas limites de precedence.

**Risque reel:** des regles implicites difficiles a expliquer et encore plus difficiles a tester.

### R2. Contrat d'operations manuelles encore incomplet

Le socle actuel possede des primitives techniques utiles:
- sync global,
- publish discovery par equipement,
- unpublish discovery par equipement,
- cleanup automatique.

En revanche, il n'existe pas encore de contrat produit explicite pour:
- `Republier` au niveau piece et equipement,
- `Supprimer/Recreer` au niveau global, piece, equipement,
- la distinction entre changement local de perimetre et application a Home Assistant.

**Risque reel:** introduire des endpoints ad hoc ou des comportements implicites differents selon la portee.

### R3. Explicabilite partiellement partagee entre backend et frontend

Le daemon porte deja l'essentiel des raisons lisibles, mais le frontend conserve encore une part de reinterpretation locale des statuts et raisons.

**Risque reel:** avec la V1.1, la logique de statut deviendrait vite incoherente si elle continue a vivre a la fois:
- dans le daemon,
- dans le PHP,
- dans le JS.

### R4. Sante du pont encore insuffisamment contractuelle

L'etat demon / broker existe deja partiellement.  
En revanche, la **derniere synchronisation terminee** n'est pas aujourd'hui un element expose comme contrat stable.

**Risque reel:** confusion support entre:
- incident infra,
- absence de sync recente,
- probleme de perimetre,
- equipement non publie pour raison metier.

### R5. Ecart entre architecture initiale et API effectivement exposee

L'architecture initiale projetait des primitives du type `/action/publish` et `/action/remove`.  
Le socle implemente aujourd'hui surtout `/action/sync`, `/system/status` et `/system/diagnostics`.

Cet ecart n'est pas bloquant pour le MVP, mais il devient sensible pour la V1.1.

**Risque reel:** ajouter les operations V1.1 directement dans l'UI ou le PHP sans facade d'orchestration unique cote daemon.

### R6. Risque d'effets HA peu lisibles lors des changements de perimetre

Le socle sait deja depublier des entites quand elles sortent du perimetre effectif.  
Mais la V1.1 exige que l'utilisateur comprenne mieux:
- quand il ne fait qu'une mise a jour,
- quand il force une reconstruction,
- quand une consequence vient de Home Assistant,
- quand un changement est encore seulement local.

**Risque reel:** comportement techniquement correct mais difficile a expliquer.

## 5. Recommandations d'architecture structurantes

### 5.1 Conserver le socle actuel et ajouter une couche delta, pas une refonte

Decision:
- **Conserver l'architecture daemon + pipeline central + cache technique + diagnostic.**
- **Ajouter une couche de modelisation et d'orchestration V1.1 au-dessus de ce socle.**

Pourquoi:
- le coeur technique est deja le bon,
- les risques V1.1 sont des risques de modele et de contrat,
- une refonte detruirait de la valeur sans reduire les vrais risques.

### 5.2 Introduire un modele canonique du perimetre publie

Decision:
- Ajouter un **modele explicite du perimetre publie** avant l'epic planning.
- Ce modele doit etre la seule source de verite pour l'evaluation `global -> piece -> equipement`.

Pourquoi:
- la V1.1 repose sur l'heritage et l'exception,
- la logique ne doit pas etre reconstruite differemment dans chaque epic,
- c'est la cle pour garder un comportement deterministe et testable.

### 5.3 Introduire une facade d'operations unique

Decision:
- Toute operation V1.1 doit passer par une **meme couche d'orchestration** cote backend.
- La portee et l'intention doivent etre des parametres de cette couche, pas des variantes dispersées.

Pourquoi:
- on evite trois implementations differentes de la meme operation,
- on garde les invariants HA au meme endroit,
- on garde un socle testable.

### 5.4 Faire du backend la source unique des statuts et raisons lisibles

Decision:
- La logique qui decide `statut + raison principale + action recommandee` doit vivre cote backend.
- Le frontend ne doit plus faire grossir sa propre logique semantique.

Pourquoi:
- la V1.1 ajoute des nuances que le JS ne doit pas recalculer,
- c'est la seule facon de garantir l'explicabilite et la soutenabilite support.

### 5.5 Etendre la sante du pont de facon minimale et contractuelle

Decision:
- Exposer un contrat de sante minimal a trois dimensions:
  - demon,
  - broker,
  - derniere synchronisation terminee.

Pourquoi:
- c'est explicitement requis par la V1.1,
- c'est suffisant pour le support courant,
- cela ne demande pas une couche d'observabilite avancee.

## 6. Recommandations sur le modele de perimetre publie

### 6.1 Decision de structure

Le modele de perimetre publie doit etre fige autour de trois niveaux:

| Niveau | Role architectural |
|---|---|
| Global | regle racine et portee d'operations globales |
| Piece | niveau principal de pilotage |
| Equipement | niveau d'exception locale |

### 6.2 Decision de representation

Le modele recommande n'est pas un booleen `exclu / non exclu`.  
Le modele recommande est un **etat a heritage explicite**.

Decision:
- Chaque noeud `piece` et `equipement` doit pouvoir etre:
  - `inherit`
  - `include`
  - `exclude`

Resolution recommandee:
- precedence `equipement > piece > global`.

Pourquoi:
- `inherit` est indispensable pour exprimer proprement l'exception,
- `include/exclude` sont necessaires pour rendre la decision lisible,
- un simple booleen ne suffit pas a representer l'intention utilisateur.

### 6.3 Decision de compatibilite avec le socle actuel

Le socle actuel peut etre reutilise comme point de depart:
- exclusion equipement existante,
- exclusion piece existante,
- source d'exclusion existante,
- evaluation avant mapping deja en place.

Mais il faut faire evoluer le modele pour transporter aussi:
- la source de decision effective,
- l'etat d'heritage,
- le cas d'inclusion par exception.

### 6.4 Decision sur les filtres techniques existants

Les exclusions par plugin source peuvent rester supportees, mais elles ne doivent pas devenir le coeur du modele V1.1.

Decision:
- les exclusions plugin restent un **filtre technique global avance**,
- elles ne remplacent pas le modele `global -> piece -> equipement`,
- leur raison doit rester lisible comme filtre technique, pas comme comportement principal de la console.

### 6.5 Decision de responsabilite

Le calcul de la decision effective doit etre centralise dans un **resolver unique de perimetre**.

Ce resolver doit fournir au minimum:
- la decision effective,
- la source de cette decision,
- un code stable pour le diagnostic,
- les informations necessaires aux compteurs globaux et par piece.

## 7. Recommandations sur la granularite des operations global / piece / equipement

### 7.1 Decision de principe

Les operations V1.1 doivent etre definies par:
- une **intention**,
- une **portee**,
- une **selection cible**.

L'intention doit etre limitee en V1.1 a deux operations HA:
- `Republier`
- `Supprimer/Recreer`

### 7.2 Decision sur la semantique de `Republier`

`Republier` doit signifier:
- recalculer le perimetre cible,
- republier la representation attendue,
- ne pas introduire volontairement de rupture destructive,
- n'effacer que ce qui doit l'etre du fait du perimetre effectif ou du cycle de vie.

Conclusion:
- `Republier` n'est pas une suppression suivie d'une recreation cachee.

### 7.3 Decision sur la semantique de `Supprimer/Recreer`

`Supprimer/Recreer` doit signifier:
- operation explicite,
- destructive cote Home Assistant,
- reservee aux cas de reconstruction voulue,
- seule operation utilisateur ayant pour intention de casser puis reconstruire la representation HA.

Conclusion:
- c'est une operation differente par nature, pas seulement par intensite.

### 7.4 Decision d'orchestration

La meme couche backend doit accepter une portee:
- `global`,
- `piece`,
- `equipement`.

Et produire:
- la liste cible,
- le resultat d'execution,
- les impacts techniques eventuels,
- le resume d'etat apres operation.

Cela permet de reemployer les primitives existantes:
- publication par equipement,
- depublication par equipement,
- cache runtime,
- detection de cycle de vie,
- synchronisation du diagnostic.

### 7.5 Decision de separation entre decision locale et effet HA

Les modifications de perimetre ne doivent pas etre confondues avec les operations HA.

Decision:
- la decision locale de scope et l'operation appliquee a HA doivent rester deux concepts distincts.

Pourquoi:
- c'est indispensable pour la predictibilite,
- c'est aligne avec la revue UX,
- cela borne clairement les effets cote Home Assistant.

## 8. Recommandations sur le moteur de statuts / raisons lisibles

### 8.1 Decision de separation semantique

Le systeme doit separer au moins quatre dimensions:

| Dimension | Question couverte |
|---|---|
| Perimetre | cet element est-il dans le scope voulu ? |
| Projection | est-il actuellement publie dans HA ? |
| Raison principale | pourquoi cet etat ? |
| Infrastructure | le pont peut-il executer l'action ? |

Cette separation est necessaire pour eviter qu'un seul badge tente de tout dire.

### 8.2 Decision sur les statuts principaux d'equipement

Pour la V1.1, le niveau equipement doit converger vers un jeu de statuts principaux restreint:
- `Publie`
- `Exclu`
- `Ambigu`
- `Non supporte`
- `Incident infrastructure`

Recommendation complementaire:
- `Partiellement publie` peut rester utile comme statut agrege ou comme detail secondaire,
- il ne doit pas devenir le statut semantique principal du moteur de decision V1.1 au niveau equipement.

### 8.3 Decision sur la raison principale

La raison principale doit vivre cote backend sous la forme:
- d'un `reason_code` stable,
- d'un message lisible,
- d'une action recommandee optionnelle,
- d'une mention explicite quand la limite vient de Home Assistant.

Le socle actuel de messages de diagnostic est reutilisable.  
La bonne decision est de l'etendre, pas de la repliquer.

### 8.4 Decision de gouvernance de la logique

Le frontend ne doit plus porter la responsabilite de reconstruire les statuts metier.

Decision:
- le backend calcule,
- le frontend affiche,
- le frontend peut filtrer et presenter,
- le frontend ne doit pas inventer de nouvelles raisons ni de nouvelles regles d'etat.

### 8.5 Decision sur l'incident d'infrastructure

Un incident infrastructure doit etre distingue d'un probleme de mapping ou de scope.

Decision:
- l'incident bridge doit etre un motif de statut explicite,
- pas une simple variante de `Non publie`.

Pourquoi:
- c'est critique pour le support,
- c'est critique pour la comprehension utilisateur,
- cela evite d'attribuer au perimetre un probleme qui releve du demon ou du broker.

## 9. Recommandations sur la sante minimale du pont

### 9.1 Ce qui est deja utilisable

Le socle expose deja une partie utile:
- etat du demon,
- etat de la connexion MQTT,
- identification du broker.

Cette base suffit pour ne pas introduire une couche de monitoring avancee.

### 9.2 Ce qui manque vraiment pour la V1.1

Le manque principal est:
- la **derniere synchronisation terminee**,
- le **resultat court obligatoire de la derniere operation** en `succes / partiel / echec`.

### 9.3 Decision recommande

Etendre le contrat de sante du pont avec un objet minimal du type:
- demon,
- broker,
- derniere synchro terminee,
- resultat court obligatoire de la derniere operation.

Le tout doit rester:
- sans historique detaille,
- sans timeline,
- sans metriques avancees,
- sans couche d'observabilite dediee.

### 9.4 Lieu de vie recommande

La sante minimale du pont doit etre produite par le daemon comme etat runtime contractuel, puis exposee au PHP/UI.

Pourquoi:
- le daemon est deja le point de verite sur la connexion broker et les synchronisations,
- on evite de reconstituer cet etat dans l'UI,
- on garde un seul contrat backend.

Decision complementaire:
- ne pas introduire de bus d'evenements ni de couche push specifique pour la V1.1;
- etendre le contrat de statut existant et le polling UI suffit pour cette phase.

## 10. Ce qu'il faut figer avant epic planning

Les decisions suivantes doivent etre figees avant de decouper les epics:

1. **Modele canonique du perimetre publie**
   `global -> piece -> equipement`, avec `inherit/include/exclude` et precedence explicite.

2. **Statut du niveau global dans le modele**
   Le niveau global existe comme racine de resolution et comme portee d'operations, meme si l'UI V1.1 ne lui donne pas encore un jeu de regles complexe.

3. **Statut des filtres techniques existants**
   Les exclusions plugin restent compatibles mais secondaires par rapport au modele principal de perimetre.

4. **Contrat d'operations V1.1**
   `Republier` et `Supprimer/Recreer` doivent etre figes comme deux intentions distinctes, reutilisables aux trois portees.

5. **Separation entre decision locale et application a HA**
   Un changement de perimetre ne doit pas etre semantiquement confondu avec une action destructive ou une republication.

6. **Source unique des statuts et raisons lisibles**
   Le backend porte la logique, le frontend ne fait que l'afficher.

7. **Contrat minimal de sante du pont**
   Demon, broker, derniere synchro terminee, resultat court obligatoire de la derniere operation.

8. **Invariants d'impact HA**
   - `unique_id` stable tant que l'ID Jeedom reste stable,
   - `Republier` non destructif par intention,
   - `Supprimer/Recreer` seul flux destructif explicite,
   - recalcul du scope deterministe a partir d'un snapshot et d'une configuration donnes.

Sans ces huit points, les epics risquent de se decouper par ecrans ou par actions UI au lieu de se decouper autour d'un coeur de contrat stable.

## 11. Ce qui peut rester ouvert jusqu'aux stories

Peut rester ouvert jusqu'au niveau story, sans bloquer l'epic planning:

- le nom exact des endpoints ou de la facade d'operation;
- le detail de persistance entre configuration plugin et configuration equipement, tant que le principe "pas de table SQL custom" est conserve;
- le choix exact entre appel synchrone, job court ou orchestration legerement asynchrone pour certaines operations;
- le wording final de certaines raisons utilisateur;
- la forme exacte de retour d'operation pour l'UI;
- la forme exacte du champ `derniere operation` et de son payload associe;
- la forme de presentation UI des compteurs et details.

Ces sujets relevent du design de stories et non d'un arbitrage d'architecture structurant.

## 12. Verification de non-empiètement sur les phases suivantes

### 12.1 Preview complete

Cette revue n'impose pas de moteur de preview avant action.  
Elle exige seulement un modele de scope et des operations explicites.

### 12.2 Remediation guidee avancee

Cette revue n'impose pas de parcours assiste multi-etapes.  
Elle demande seulement une raison principale et, si utile, une action recommandee simple.

### 12.3 Sante avancee du pont

Cette revue n'impose ni timeline, ni metriques, ni observabilite experte.  
Elle limite la sante a l'essentiel requis par la V1.1.

### 12.4 Support outille avance

Cette revue n'impose pas de nouveaux outils lourds de support.  
Le socle de diagnostic et d'export existant est suffisant pour la V1.1.

### 12.5 Extension fonctionnelle future

Cette revue n'impose aucune nouvelle famille d'entites.  
Elle se borne a rendre pilotable le perimetre deja couvert.

### 12.6 Alignement Homebridge

Cette revue n'introduit aucune contrainte Homebridge-like.  
Elle reste strictement alignee avec la priorite produit V1.1 Pilotable.

## 13. Verdict final

### Verdict

**Architecture suffisamment cadree pour lancer l'epic planning, sous reserve de figer l'addendum delta decrit dans cette revue.**

### Formulation decisionnelle

- **Pas de refonte complete necessaire.**
- **Le socle actuel est reutilisable et pertinent.**
- **Les ajustements necessaires sont limites mais structurants.**
- **Le point critique n'est pas la technique bas niveau, mais le contrat de pilotage.**

### Conclusion finale

Le socle actuel supporte proprement la V1.1 Pilotable **a condition de ne pas bricoler la phase comme une simple extension d'ecran ou une addition d'actions AJAX**.

La bonne trajectoire est:
- conserver le pipeline actuel,
- figer un modele canonique de perimetre publie,
- figer un contrat d'operations explicites,
- figer un moteur de statuts lisibles cote backend,
- et ajouter une sante minimale du pont contractuelle.

Dans ce cadre, la V1.1 reste:
- previsible,
- explicable,
- sure a l'usage,
- testable,
- et soutenable cote support.
