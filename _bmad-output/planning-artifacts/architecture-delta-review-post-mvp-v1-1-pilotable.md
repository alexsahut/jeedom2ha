---
document_type: architecture_delta_review
project: jeedom2ha
phase: post_mvp_phase_1
version_label: v1_1_pilotable
date: 2026-03-27
status: ready_for_epic_planning_with_recadrage_ux
source_documents:
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-post-mvp-refresh.md
  - _bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-26.md
  - _bmad-output/project-context.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/prd.md
revision_history:
  - date: 2026-03-27
    changes: "Recadrage UX — intégration du modèle Périmètre/Statut/Écart/Cause, contrat dual reason_code/cause_code, définition technique de l'écart, compteurs pièce/global, filtrage diagnostic in-scope, traitement Partiellement publié."
  - date: 2026-03-22
    changes: "Revue delta initiale — addendum structurel sur 4 sujets."
---

# Revue d'architecture delta - Post-MVP V1.1 Pilotable

## 1. Executive summary

Le socle actuel de `jeedom2ha` est **compatible avec la V1.1 Pilotable sans refonte complète**.

Le point fort du socle est clair: la logique critique est deja largement centralisee autour d'un pipeline unique `topologie -> eligibilite -> mapping -> decision de publication -> publication MQTT -> diagnostic`. Cette base est saine pour proteger la predictibilite, l'explicabilite, la stabilite des identifiants et la maintenabilite.

La V1.1 ne demande donc pas une nouvelle architecture. Elle demande un **addendum structurel cible** sur cinq sujets:

1. **Un modele canonique du perimetre publie** qui rende explicite la hierarchie `global -> piece -> equipement`.
2. **Un contrat d'operations explicites** qui distingue clairement `Republier` et `Supprimer/Recreer` a toutes les portees.
3. **Un moteur de statuts / raisons lisibles unifie cote backend**, pour ne pas disperser la logique entre daemon, PHP et JS.
4. **Un contrat minimal de sante du pont** incluant la derniere synchronisation, sans introduire une couche d'observabilite lourde.
5. **Un modele utilisateur a 4 dimensions (Perimetre / Statut / Ecart / Cause)** avec un contrat dual `reason_code` (backend stable) / `cause_code` + `cause_label` (contrat UI), des compteurs backend pre-calcules, un diagnostic filtre in-scope cote backend, et l'absorption du cas historique "Partiellement publie".

Verdict de synthese:
- **Oui, l'architecture est suffisamment cadree pour lancer l'epic planning.**
- **Les cinq sujets ci-dessus sont desormais figes et documentes dans cette revue (§6 a §10).**

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

**Resolution (recadrage 2026-03-27):** le modele Perimetre/Statut/Ecart/Cause est desormais integralement calcule par le backend. Le frontend recoit les 4 dimensions pre-resolues et les compteurs pre-calcules. Il ne fait aucune interpretation, aucun mapping local, aucun calcul de compteur. Voir §8 pour le contrat detaille.

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

### 6.6 Expression technique des sources d'exclusion

Le resolver canonique continue d'operer avec `inherit / include / exclude` et la precedence `equipement > piece > global`. La couche de presentation traduit la decision effective en source d'exclusion lisible pour l'API et le frontend.

| Resolution interne | Sortie `perimetre` pour l'API | Libelle UI |
|---|---|---|
| include (effectif, quelle que soit l'origine) | `inclus` | Inclus |
| exclude, source = regle objet/piece | `exclu_par_piece` | Exclu par la piece |
| exclude, source = filtre plugin | `exclu_par_plugin` | Exclu par le plugin |
| exclude, source = override equipement | `exclu_sur_equipement` | Exclu sur cet equipement |

Decisions:
- `inherit` n'apparait jamais dans la reponse API. Il est toujours resolu avant serialisation.
- La source d'exclusion est tracee par le resolver (il sait deja d'ou vient la decision via `exclusion_source`).
- Le frontend ne voit que les quatre valeurs `inclus`, `exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement`.
- Cette traduction est un mapping deterministe, pas une heuristique. Elle est testable en isolation.

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

## 8. Recommandations sur le moteur de statuts et la couche d'explicabilite

### 8.1 Modele utilisateur cible : Perimetre → Statut → Ecart → Cause

Le systeme expose quatre dimensions au niveau equipement:

| Dimension | Question couverte | Valeurs |
|---|---|---|
| Perimetre | cet element fait-il partie du scope voulu ? | `inclus`, `exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement` |
| Statut | est-il actuellement projete dans HA ? | `publie`, `non_publie` |
| Ecart | y a-t-il un desalignement decision ↔ etat ? | `true`, `false` |
| Cause | pourquoi cet etat ou cet ecart ? | `cause_code` + `cause_label` + optionnellement `cause_action` |

Ce modele remplace le decoupage precedent (Perimetre / Projection / Raison principale / Infrastructure).

Decisions:
- Le statut binaire `publie` / `non_publie` n'existe qu'au niveau equipement.
- Les niveaux piece et global sont lus par compteurs uniquement (voir §8.5).
- L'ancien statut `Ambigu` devient: Perimetre=inclus, Statut=non_publie, Ecart=true, Cause=mapping ambigu.
- L'ancien statut `Non supporte` devient: Perimetre=inclus, Statut=non_publie, Ecart=true, Cause=type non supporte.
- L'ancien statut `Exclu` devient: Perimetre=exclu_par_[source], Statut=non_publie, Ecart=false.
- L'ancien `Incident infrastructure` reste un motif d'ecart: Ecart=true, Cause=infra_unavailable.
- Voir §8.7 pour le traitement du cas `Partiellement publie`.

### 8.2 Definition technique de l'ecart

L'ecart est un booleen calcule par le backend. Il signale un desalignement entre la decision effective du resolver et l'etat de publication reel dans Home Assistant.

**Formule exacte:**

```
ecart = (decision_effective == "inclus" AND NOT est_publie_ha)
     OR (decision_effective != "inclus" AND est_publie_ha)
```

**Bidirectionnalite:**

| Decision effective | Etat projete HA | Ecart | Direction |
|---|---|---|---|
| inclus | publie | false | aligne |
| inclus | non_publie | **true** | inclus mais non publie |
| exclu_* | non_publie | false | aligne |
| exclu_* | publie | **true** | exclu mais encore publie |

**Relation avec l'etat projete et l'etat actif:**
- `decision_effective` = sortie du resolver canonique (`inherit/include/exclude` resolu en `inclus` ou `exclu_par_*`).
- `est_publie_ha` = presence effective d'une configuration discovery MQTT retained pour cet equipement. Cet etat est porte par le cache runtime du daemon.
- L'ecart est calcule *apres* le resolver et *apres* la verification de l'etat de publication.

**Lieu de calcul:**
- Le calcul de l'ecart se fait dans le backend, au moment de la construction de la reponse API.
- Le frontend recoit `ecart: true/false` pre-calcule et ne fait aucune deduction.

### 8.3 Contrat dual reason_code / cause_code

Le systeme maintient deux couches de codes:

| Couche | Audience | Stabilite | Cycle de vie |
|---|---|---|---|
| `reason_code` | Backend, diagnostic technique, export support | Stable — herite d'Epic 3, jamais renomme | Produit par le pipeline de decision |
| `cause_code` / `cause_label` / `cause_action` | Contrat UI canonique | Stable pour le contrat frontend | Derive du `reason_code` par une couche de traduction |

**Ou la traduction est faite:**
- Dans la couche de serialisation de la reponse API, apres que le pipeline a produit ses resultats avec `reason_code`.
- La traduction est une **fonction pure**: `reason_code → (cause_code, cause_label, cause_action)`.
- Elle est implementee comme une table de correspondance dans le backend Python.

**A quel niveau du pipeline:**

```
Topologie → Eligibilite → Mapping → Decision → reason_code
                                                      ↓
                                              Traduction (table)
                                                      ↓
                                       cause_code / cause_label / cause_action
                                                      ↓
                                              Reponse API
```

Le pipeline central ne change pas. La couche de traduction est ajoutee *en sortie* du pipeline, pas *dans* le pipeline.

**Stabilite et testabilite:**
- Les `reason_code` sont les codes techniques stables du pipeline. Ils ne sont pas exposes en UI.
- La table de traduction `reason_code → cause_code` est une fonction pure, testable en isolation par tests unitaires.
- L'ajout d'un nouveau `reason_code` (futur) requiert l'ajout d'une entree dans la table de traduction.
- Le contrat UI est testable par assertions sur les reponses API.

**Table de traduction cible (direction 1 — inclus mais non publie):**

| `reason_code` (backend) | `cause_code` (UI) | `cause_label` |
|---|---|---|
| `no_mapping` | `no_mapping` | Aucun mapping compatible |
| `ambiguous_mapping` | `ambiguous_skipped` | Mapping ambigu — plusieurs types possibles |
| `unsupported_generic_type` | `no_supported_generic_type` | Type non supporte en V1 |
| `no_generic_type` | `no_generic_type_configured` | Types generiques non configures sur les commandes |
| `disabled` | `disabled_eqlogic` | Equipement desactive dans Jeedom |
| `no_commands` | `no_commands` | Equipement sans commandes exploitables |
| `publish_failed` | `discovery_publish_failed` | Publication MQTT echouee |
| `infra_unavailable` | `infra_unavailable` | Bridge indisponible |

**Table de traduction cible (direction 2 — exclu mais encore publie):**

| `reason_code` (backend) | `cause_code` (UI) | `cause_label` |
|---|---|---|
| *(genere par detection d'ecart)* | `pending_unpublish` | Changement en attente d'application |

Note: certains `cause_code` sont identiques au `reason_code` quand la correspondance est directe. La table reste la source de verite, meme si le mapping est trivial. Le `cause_code` `pending_unpublish` est un cas special: il n'est pas derive d'un `reason_code` pipeline mais de la detection d'ecart direction 2.

### 8.4 Compteurs piece et global

Les niveaux piece et global ne portent pas de statut binaire. Leur lecture principale repose sur quatre compteurs pre-calcules par le backend.

**Compteurs:**

| Compteur | Definition | Source |
|---|---|---|
| Total | nombre total d'equipements dans la piece / dans le parc | agregation backend |
| Inclus | equipements ou `perimetre = inclus` | agregation backend |
| Exclus | equipements ou `perimetre` commence par `exclu_` | agregation backend |
| Ecarts | equipements ou `ecart = true` | agregation backend |

**Invariant arithmetique:**

```
Total = Inclus + Exclus
Ecarts ⊆ (Inclus ∪ Exclus)   // un ecart peut exister dans les deux populations
```

Un ecart de direction 1 (inclus mais non publie) est dans la population Inclus. Un ecart de direction 2 (exclu mais encore publie) est dans la population Exclus. Les deux comptent dans le compteur Ecarts.

**Source de verite:**
- Les compteurs sont calcules par le backend par agregation des etats equipement resolus.
- Les compteurs sont exposes dans la reponse API aux niveaux piece et global.
- Le frontend ne fait aucun calcul de compteur localement.

**Indicateur synthetique piece/global:**
- Si un indicateur visuel synthetique est conserve au niveau piece ou global (ex: badge d'alerte quand `ecarts > 0`), il doit etre defini comme un indicateur derive des compteurs, pas comme une extension du statut equipement, et nomme differemment (ex: `Ecarts a traiter`).

### 8.5 Filtrage du diagnostic principal in-scope

Le diagnostic principal utilisateur ne porte que sur les equipements dont `perimetre = inclus`. Le filtrage est fait **cote backend**, dans la construction de la reponse API.

**Trois surfaces, trois populations:**

| Surface | Population | Filtrage |
|---|---|---|
| Console principale (synthese perimetre) | Tous les equipements | Aucun — compteurs + perimetre par source pour les exclus |
| Diagnostic principal utilisateur | `perimetre = inclus` uniquement | Backend filtre avant envoi |
| Export support complet | Tous les equipements | Aucun — vue technique exhaustive |

Le filtrage est un simple `WHERE perimetre = 'inclus'` sur la collection d'equipements resolus. Il ne modifie ni le pipeline ni le resolver.

**Contenu du diagnostic utilisateur (equipements in-scope):**
- Statut, ecart, cause (comme en console).
- Details supplementaires: commandes observees, typage Jeedom, confiance (`Sur`/`Probable`/`Ambigu`).
- La confiance n'est visible qu'en diagnostic, jamais en console principale.

**Export support complet:**
- Contient tous les equipements, in-scope et exclus.
- Inclut les `reason_code` techniques (pas seulement les `cause_code`).
- Inclut la confiance, les commandes, le typage, les metadata pipeline.
- N'est pas filtre par le perimetre.

### 8.6 Traitement du cas historique "Partiellement publie"

"Partiellement publie" est **absorbe comme statut principal** de la console, mais **conserve comme indicateur de diagnostic detaille** pour la couverture commandes.

#### 8.6.1 Statut principal : absorption

| Ancien statut | Nouveau modele (console) |
|---|---|
| `Partiellement publie` | Perimetre=inclus, Statut=publie, Ecart=false |

Un equipement "partiellement publie" est un equipement pour lequel une configuration discovery a ete envoyee a HA. L'entite existe cote HA. Du point de vue du modele principal Perimetre/Statut/Ecart/Cause, cet equipement est **publie**.

Le fait que certaines commandes ne soient pas mappees (ex: lumiere avec ON/OFF mais sans dimmer) est un **detail de couverture**, pas un statut fondamental. Ce detail ne doit pas remonter comme statut principal ni comme ecart dans la console.

#### 8.6.2 Diagnostic : conservation comme indicateur de couverture

L'information de couverture partielle reste disponible dans le **diagnostic detaille** et l'**export support**. Elle permet de distinguer, pour un equipement publie, les commandes/capacites correctement projetees de celles qui ne le sont pas.

**Ou vit cette information:**
- Dans le diagnostic detaille par equipement (accessible depuis la console pour les equipements in-scope).
- Dans l'export support complet.
- Elle est portee par la granularite commande deja existante dans le pipeline (commandes observees vs commandes mappees).

**Comment elle reste disponible:**
- Le pipeline produit deja le detail commande par equipement (commandes Jeedom detectees, commandes effectivement mappees, commandes ignorees).
- Ce detail est inclus dans la reponse diagnostic et dans l'export support.
- Un equipement publie avec couverture partielle est identifiable dans le diagnostic par la presence de commandes non mappees parmi les commandes observees.

**Ce qui n'est pas fait:**
- "Partiellement publie" ne reapparait jamais comme statut principal de la console.
- "Partiellement publie" ne genere pas d'ecart (`ecart` reste `false` — l'equipement est bien publie comme voulu).
- "Partiellement publie" n'est pas un `cause_code` du contrat UI principal.

#### 8.6.3 Champ technique complementaire

Aucun nouveau champ obligatoire n'est introduit dans le contrat principal pour la V1.1. Le diagnostic detaille existant (granularite commande) suffit a porter l'information de couverture partielle.

Si un indicateur synthetique de couverture s'avere utile en diagnostic (ex: `commandes_mappees: 5/8`), il peut etre ajoute au niveau story comme enrichissement du contrat diagnostic, sans modifier le contrat principal de la console.

### 8.7 Gouvernance : le frontend n'interprete jamais

Decision inchangee et renforcee par le nouveau modele:
- Le backend calcule les 4 dimensions (perimetre, statut, ecart, cause).
- Le backend calcule les compteurs par piece et globaux.
- Le frontend affiche les valeurs recues.
- Le frontend peut filtrer, trier, masquer.
- Le frontend ne doit pas:
  - deriver un statut a partir d'autres champs,
  - recomposer une cause a partir de `cause_code`,
  - calculer un compteur localement,
  - inventer un libelle non fourni par le backend.

### 8.8 Incident d'infrastructure

Decision maintenue et alignee avec le nouveau modele:
- Un incident infrastructure (bridge/broker indisponible) reste un motif d'ecart explicite.
- Au niveau equipement: Ecart=true, Cause=`infra_unavailable` / `Bridge indisponible`.
- Il ne doit pas etre confondu avec un probleme de mapping ou de perimetre.
- Le bandeau de sante (§9) reste la surface principale pour les incidents d'infrastructure.
- Le rouge reste reserve a l'infrastructure — aucun probleme de mapping ou de perimetre ne doit etre affiche en rouge.

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
   `global -> piece -> equipement`, avec `inherit/include/exclude` en representation interne et precedence explicite.

2. **Expression des sources d'exclusion**
   L'API expose `inclus`, `exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement`. Le frontend ne voit jamais `inherit`. Voir §6.6.

3. **Modele utilisateur a 4 dimensions**
   Perimetre → Statut → Ecart → Cause. Le statut binaire `publie`/`non_publie` n'existe qu'au niveau equipement. Voir §8.1.

4. **Definition technique de l'ecart**
   Booleen bidirectionnel calcule par le backend. Formule, lieu de calcul et relation avec l'etat projete figes en §8.2.

5. **Contrat dual reason_code / cause_code**
   `reason_code` stable (backend, pipeline, Epic 3). `cause_code`/`cause_label`/`cause_action` derive par traduction (table pure). Le frontend ne voit que le contrat UI. Voir §8.3.

6. **Compteurs piece et global**
   Total, Inclus, Exclus, Ecarts. Pre-calcules par le backend. Invariant `Total = Inclus + Exclus`. Pas de calcul frontend. Voir §8.4.

7. **Filtrage du diagnostic principal in-scope**
   Le diagnostic utilisateur ne porte que sur `perimetre = inclus`. Filtre cote backend. Export support complet non filtre. Voir §8.5.

8. **Traitement de "Partiellement publie"**
   Absorbe comme statut principal (Perimetre=inclus, Statut=publie, Ecart=false). Conserve comme indicateur de couverture en diagnostic detaille. Pas de champ obligatoire dans le contrat principal. Voir §8.6.

9. **Contrat d'operations V1.1**
   `Republier` et `Supprimer/Recreer` doivent etre figes comme deux intentions distinctes, reutilisables aux trois portees.

10. **Separation entre decision locale et application a HA**
    Un changement de perimetre ne doit pas etre semantiquement confondu avec une action destructive ou une republication.

11. **Contrat minimal de sante du pont**
    Demon, broker, derniere synchro terminee, resultat court obligatoire de la derniere operation.

12. **Invariants d'impact HA**
    - `unique_id` stable tant que l'ID Jeedom reste stable,
    - `Republier` non destructif par intention,
    - `Supprimer/Recreer` seul flux destructif explicite,
    - recalcul du scope deterministe a partir d'un snapshot et d'une configuration donnes.

13. **Gouvernance frontend**
    Le frontend ne fait aucune interpretation, aucun mapping local, aucun calcul de compteur, aucune invention de libelle. Voir §8.7.

Sans ces treize points, les epics risquent de se decouper par ecrans ou par actions UI au lieu de se decouper autour d'un coeur de contrat stable.

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

**Architecture suffisamment cadree pour lancer l'epic planning, avec le recadrage UX du 2026-03-27 integre.**

### Formulation decisionnelle

- **Pas de refonte complete necessaire.**
- **Le socle actuel est reutilisable et pertinent.**
- **Le pipeline central, le resolver canonique et les `reason_code` restent stables.**
- **Le point critique est le contrat backend → UI, desormais fige autour de 4 dimensions et d'un contrat dual reason_code / cause_code.**

### Ce que le recadrage a tranche

Les six points demandes sont resolus:

1. **Definition technique de l'ecart** — formule exacte, bidirectionnalite, relation avec l'etat projete/actif (§8.2).
2. **Contrat dual reason_code / cause_code** — lieu de traduction, niveau pipeline, stabilite et testabilite (§8.3).
3. **Filtrage du diagnostic in-scope** — cote backend, export support non filtre (§8.5).
4. **Compteurs piece/global** — source backend, ecart bidirectionnel inclus, pas de calcul frontend (§8.4).
5. **Sources d'exclusion** — `exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement` (§6.6).
6. **Traitement de "Partiellement publie"** — absorbe comme statut principal, conserve comme indicateur de diagnostic de couverture (§8.6).

### Ambiguites residuelles

Aucune ambiguite bloquante pour l'epic planning. Les points suivants restent a affiner au niveau story:
- Le nom exact des `reason_code` existants dans le code doit etre verifie pour confirmer la table de traduction §8.3.
- Le `cause_code` `pending_unpublish` (direction 2) est un cas special non derive d'un `reason_code` pipeline — sa generation est un calcul dedie a documenter en story.
- Un indicateur synthetique de couverture commandes en diagnostic (ex: `commandes_mappees: 5/8`) peut etre ajoute au niveau story si le detail commande brut s'avere insuffisamment lisible, sans modifier le contrat principal.

### Conclusion finale

Le socle actuel supporte proprement la V1.1 Pilotable. Le recadrage UX ne modifie pas le pipeline central. Il ajoute:
- une couche de traduction `reason_code → cause_code` en sortie de pipeline,
- un calcul d'ecart bidirectionnel backend,
- des compteurs pre-calcules pour piece/global,
- un filtrage in-scope du diagnostic cote backend,
- une expression des exclusions par source pour l'API.

Dans ce cadre, la V1.1 reste:
- previsible,
- explicable,
- sure a l'usage,
- testable,
- et soutenable cote support.

### Handoff

Prochaine etape : mise a jour des epics (`epics-post-mvp-v1-1-pilotable.md`) pour inserer le nouvel Epic 4 (recadrage UX) et renumeroter l'actuel Epic 4 en Epic 5, en s'appuyant sur les 13 points figes en §10 et les contrats techniques definis en §8.
