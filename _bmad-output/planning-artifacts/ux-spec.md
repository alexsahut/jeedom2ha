---
document_type: ux_spec
project: jeedom2ha
cycle: post_mvp_phase_1_v1_1_pilotable
date: 2026-03-30
version: v3_interview_driven_contractual
status: ready_as_acceptance_reference
scope: correctif_prioritaire_epic_4_home_vs_diagnostic
elicitation_mode: guided_interactive_interview
authority:
  - _bmad-output/planning-artifacts/active-cycle-manifest.md
  - _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-29.md
  - _bmad-output/implementation-artifacts/epic-4-retro-2026-03-29.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
supersedes:
  - ux-spec.md v2_contractual_wireframe created 2026-03-29
guardrails:
  - Ne pas creer de story corrective dans ce document.
  - Ne pas faire de dev dans ce workflow.
  - Ne pas rouvrir le modele 4D.
  - Ne pas rouvrir les compteurs backend historiques.
  - Ne pas rouvrir la sortie du vocabulaire legacy.
  - Ne pas deriver vers Epic 5.
  - Ne retoucher que la cible UX/UI home vs diagnostic.
---

# UX Spec V3 - Cible contractuelle issue de l'interview guidee

## 1. Statut et mandat

Ce document remplace la version precedente du `ux-spec.md`.

Il ne formalise pas une deduction theorique a partir des artefacts existants.  
Il formalise la vision d'ecran explicitement validee pendant l'interview guidee du 2026-03-30.

But du document :
- figer une cible UX/UI quasi binaire conforme / non conforme ;
- servir de reference d'acceptation avant toute future story corrective Epic 4 ;
- verrouiller la separation percue entre home et diagnostic ;
- preserver la base existante du diagnostic quand elle est deja bonne.

## 2. Phrase de verite

- `home = synthese et pilotage du parc`
- `diagnostic = explicabilite detaillee des cas du perimetre inclus`
- la home oriente vers le diagnostic
- le diagnostic n'essaie jamais de redevenir une home

Si une implementation brouille cette phrase, elle est non conforme.

## 3. Cadrage immuable

### 3.1 Hors scope

- aucune story corrective ;
- aucune refonte globale du plugin ;
- aucun travail Epic 5 ;
- aucune reouverture du modele 4D ;
- aucune redefinition des compteurs backend historiques ;
- aucune reouverture du vocabulaire legacy.

### 3.2 Ancrages produit a preserver

- La home reste la page plugin avec son shell actuel.
- Le diagnostic reste une surface separee, ouverte depuis le bouton `Diagnostic`.
- La base de la grande modal diagnostic existante est preservee.
- La logique `liste d'abord, detail ensuite` est preservee.
- Le detail commandes existant du diagnostic est preserve tel quel.

### 3.3 Shell home preserve

Les zones suivantes restent inchangees dans leur role et leur presence :
- bandeau `Sante` du pont ;
- actions globales `Home Assistant` ;
- export `diagnostic support` ;
- menu plugin :
  - `Ajouter`
  - `Configuration`
  - `Diagnostic`

La seule zone retravaillee par ce contrat est la zone centrale de lecture du parc.

## 4. Contrat transverse de separation

### 4.1 Exclusif home

Doit vivre uniquement dans la home :
- le bandeau `Sante` du pont ;
- les actions `Home Assistant` globales ;
- l'export diagnostic support ;
- le menu plugin ;
- la lecture synthetique du parc ;
- le tableau hierarchique unique :
  - `Parc global`
  - `pieces`
  - `equipements`
- les colonnes home :
  - `Nom`
  - `Perimetre`
  - `Statut`
  - `Ecart`
  - `Total`
  - `Exclus`
  - `Inclus`
  - `Publies`
  - `Ecarts`
- l'infobulle courte sur le badge `Ecart` au niveau equipement ;
- la logique de pilotage / synthese du parc.

### 4.2 Exclusif diagnostic

Doit vivre uniquement dans le diagnostic :
- la surface diagnostic separee ;
- la grande modal diagnostic existante ;
- la liste filtrable des equipements inclus uniquement ;
- les colonnes diagnostic :
  - `Piece`
  - `Nom`
  - `Ecart`
  - `Statut`
  - `Confiance`
  - `Raison`
- la recherche et les filtres ;
- `Confiance` ;
- `Raison` selon la logique diagnostic actuelle ;
- le detail commandes existant ;
- la logique d'explicabilite detaillee ;
- l'ouverture ciblee depuis la home sur un cas en ecart.

### 4.3 Partage sous forme differente

| Element | Home | Diagnostic |
| --- | --- | --- |
| `Ecart` | Badge synthetique + infobulle courte + clic vers diagnostic | Colonne explicite + raison + detail depliable |
| `Statut` | Lecture synthetique dans le tableau hierarchique | Colonne selon la logique diagnostic actuelle |
| `Cause / raison` | Jamais visible en permanence ; infobulle courte seulement sur badge `Ecart` equipement | Visible dans `Raison`, puis detaillee via le depliage existant |
| `Equipement` | Element de pilotage | Cas d'analyse detaillee |
| Point d'entree d'un cas | Clic sur le badge `Ecart` | Cas deja cible dans le modal |

### 4.4 Signaux d'echec perceptif immediats

La home ressemble trop a un diagnostic si :
- on peut comprendre un cas en detail sans quitter la home ;
- la home affiche `Confiance`, `Raison` detaillee ou tout detail technique ;
- la home reconstruit une fiche ou un panneau diagnostic inline.

Le diagnostic ressemble trop a une seconde home si :
- il affiche la sante globale, les compteurs du parc ou une synthese de pilotage ;
- il remet les exclus, les vues globales ou la synthese du parc au premier plan ;
- il perd sa logique `liste filtrable des inclus + detail a la demande`.

## 5. Contrat de navigation

### 5.1 Point d'entree general

Clic sur `Diagnostic` dans le plugin :
- ouvre la vue generale du diagnostic ;
- montre uniquement les equipements inclus dans le perimetre ;
- affiche la liste filtrable ;
- laisse toutes les lignes repliees par defaut.

### 5.2 Point d'entree cible depuis la home

Le clic sur le badge `Ecart` d'un equipement dans la home est obligatoire et contractuel.

Ce clic doit :
- ouvrir le meme modal diagnostic ;
- cibler l'equipement concerne ;
- scroller automatiquement jusqu'a lui si necessaire ;
- deplier automatiquement la ligne ;
- appliquer une mise en evidence visuelle temporaire de la ligne ciblee.

Cette regle est obligatoire.  
Une implementation qui ouvre seulement le diagnostic sans focus visible est non conforme.

### 5.3 Invariant in-scope-only

Le diagnostic standard affiche uniquement les equipements inclus dans le perimetre.

Les equipements exclus :
- sont absents par design de la vue diagnostic standard ;
- restent visibles dans la home ;
- relevent de l'export support si une vue exhaustive du parc est necessaire.

## 6. Ecrans contractuels

### 6.1 Home - vue normale

**Nom de l'ecran**  
`Home - vue normale`

**Objectif principal**  
Donner une lecture immediate de l'etat du parc sans exposer de detail diagnostic.

**Message dominant percu**  
`Je vois ou j'en suis globalement et ou aller ensuite.`

**Audience**  
Utilisateur plugin en lecture de synthese et pilotage.

**Actions possibles**
- consulter le bandeau `Sante` existant ;
- lire la ligne `Parc global` ;
- ouvrir la decomposition du parc en cliquant sur `Parc global` ;
- utiliser les actions `Home Assistant` existantes ;
- lancer l'export support existant ;
- ouvrir le diagnostic general via le menu plugin.

**Actions interdites**
- comprendre un cas en detail depuis cette vue ;
- ouvrir un detail technique inline ;
- voir `Confiance` ;
- voir `Raison` detaillee ;
- voir le detail commandes.

**Informations autorisees**
- shell existant du plugin ;
- une unique ligne `Parc global` dans le tableau central ;
- les 5 indicateurs chiffres dans l'ordre :
  - `Total`
  - `Exclus`
  - `Inclus`
  - `Publies`
  - `Ecarts`

**Informations interdites**
- equipements visibles ;
- pieces visibles tant que `Parc global` n'est pas ouvert ;
- detail diagnostic inline ;
- `Confiance` ;
- details techniques ;
- `reason_code` ;
- vocabulaire interne ;
- badge orange `changement a appliquer`.

**Structure verticale exacte**
1. `Bandeau Sante` inchange
2. `Tableau hierarchique du parc` avec une seule ligne visible : `Parc global`
3. `Actions Home Assistant` inchangees
4. `Export diagnostic support` inchange
5. `Menu plugin` inchange

**Maquette contractuelle**

```text
[BANDEAU SANTE - INCHANGE]

+----------------------------------------------------------------------------------------------------------------------+
| Nom                 | Perimetre | Statut | Ecart | Total | Exclus | Inclus | Publies | Ecarts                    |
|----------------------------------------------------------------------------------------------------------------------|
| > Parc global       |           |        |       |  128  |   25   |  103   |   97    |   6                       |
+----------------------------------------------------------------------------------------------------------------------+

[ACTIONS HOME ASSISTANT - INCHANGEES]
[EXPORT DIAGNOSTIC SUPPORT - INCHANGE]
[MENU PLUGIN - INCHANGE]
```

**CTA presents**
- clic sur `Parc global`
- clic sur `Diagnostic` dans le menu plugin
- CTA shell existants inchanges

**CTA absents**
- aucun equipement cliquable
- aucun detail inline
- aucun CTA diagnostic dans la zone centrale hors clic futur sur badge `Ecart`

**Niveau de detail attendu**  
Strictement `synthese`.

### 6.2 Home - parc global ouvert

**Nom de l'ecran**  
`Home - parc global ouvert`

**Objectif principal**  
Transformer la lecture globale en lecture par piece, sans montrer encore les equipements.

**Message dominant percu**  
`Je decompose le parc par piece sans entrer dans les cas.`

**Audience**  
Utilisateur qui cherche dans quelle piece regarder ensuite.

**Actions possibles**
- deplier `Parc global`
- lire les lignes pieces
- deplier une piece

**Actions interdites**
- lire une cause ;
- lire un detail technique ;
- voir `Confiance` ;
- voir les equipements avant d'avoir deplie une piece.

**Informations autorisees**
- lignes pieces dans le meme tableau ;
- 3 colonnes badges fixes :
  - `Perimetre`
  - `Statut`
  - `Ecart`
- 5 colonnes chiffrees dans l'ordre fixe :
  - `Total`
  - `Exclus`
  - `Inclus`
  - `Publies`
  - `Ecarts`

**Informations interdites**
- cause au niveau piece ;
- detail diagnostic inline ;
- equipements visibles tant qu'une piece n'est pas ouverte.

**Structure verticale exacte**
1. `Bandeau Sante` inchange
2. `Tableau hierarchique du parc`
3. `Actions Home Assistant` inchangees
4. `Export diagnostic support` inchange
5. `Menu plugin` inchange

**Maquette contractuelle**

```text
[BANDEAU SANTE - INCHANGE]

+------------------------------------------------------------------------------------------------------------------------------------------------+
| Nom                          | Perimetre | Statut                  | Ecart       | Total | Exclus | Inclus | Publies | Ecarts |
|------------------------------------------------------------------------------------------------------------------------------------------------|
| v Parc global                |           |                         |             |  128  |   25   |  103   |   97    |   6    |
|   > Salon                    | [Incluse] | [Partiellement publiee] | [En ecart]  |   12  |    2   |   10   |    7    |   3    |
|   > Cuisine                  | [Incluse] | [Publiee]               | [Alignee]   |   18  |    0   |   18   |   18    |   0    |
|   > Exterieur                | [Incluse] | [Partiellement publiee] | [En ecart]  |    9  |    4   |    5   |    3    |   2    |
|   > Garage                   | [Exclue]  | [Non publiee]           | [Alignee]   |    6  |    6   |    0   |    0    |   0    |
+------------------------------------------------------------------------------------------------------------------------------------------------+

[ACTIONS HOME ASSISTANT - INCHANGEES]
[EXPORT DIAGNOSTIC SUPPORT - INCHANGE]
[MENU PLUGIN - INCHANGE]
```

**CTA presents**
- clic sur une ligne piece pour la deplier
- clic sur `Diagnostic` dans le menu plugin

**CTA absents**
- aucun clic diagnostic direct au niveau piece
- aucun detail equipement visible avant ouverture de piece

**Niveau de detail attendu**  
`Synthese par piece`, sans cause.

**Regle contractuelle sur le badge `Statut` niveau piece**
- Le badge `Statut` au niveau piece (`Publiee`, `Partiellement publiee`, `Non publiee`) est un indicateur synthetique de piece.
- Il ne constitue pas une extension du statut 4D canonique au niveau equipement.
- Il ne doit pas autoriser de recalcul metier libre cote frontend.
- Sa production releve d'un contrat/story dedie ou d'une donnee backend validee, pas d'une interpretation locale implicite dans le JS.

### 6.3 Home - piece ouverte

**Nom de l'ecran**  
`Home - piece ouverte`

**Objectif principal**  
Permettre une lecture de pilotage jusqu'au niveau equipement sans quitter la logique de synthese.

**Message dominant percu**  
`Je vois quels equipements de cette piece sont inclus, publies, exclus ou en ecart, sans entrer dans le diagnostic.`

**Audience**  
Utilisateur qui identifie quel equipement merite d'ouvrir le diagnostic.

**Actions possibles**
- deplier une piece ;
- lire les lignes equipements dans le meme tableau ;
- survoler / focusser un badge `Ecart` pour obtenir une cause courte ;
- cliquer le badge `Ecart` pour ouvrir le diagnostic cible.

**Actions interdites**
- voir un detail technique inline ;
- voir `Confiance` ;
- voir `Raison` en permanence ;
- ouvrir un detail commandes dans la home.

**Informations autorisees**
- lignes equipements dans les memes 9 colonnes ;
- 3 badges par equipement :
  - `Perimetre`
  - `Statut`
  - `Ecart`
- colonnes chiffrees avec lecture de decomposition visuelle ;
- infobulle courte sur badge `Ecart` si et seulement si la ligne est en ecart.

**Informations interdites**
- colonne `Cause` ;
- `Confiance` ;
- `reason_code` ;
- couverture commandes ;
- typage ;
- detail technique ;
- panneau diagnostic inline.

**Structure verticale exacte**
1. `Bandeau Sante` inchange
2. `Tableau hierarchique du parc`
3. `Actions Home Assistant` inchangees
4. `Export diagnostic support` inchange
5. `Menu plugin` inchange

**Maquette contractuelle**

```text
[BANDEAU SANTE - INCHANGE]

+------------------------------------------------------------------------------------------------------------------------------------------------+
| Nom                          | Perimetre | Statut                  | Ecart       | Total | Exclus | Inclus | Publies | Ecarts |
|------------------------------------------------------------------------------------------------------------------------------------------------|
| v Parc global                |           |                         |             |  128  |   25   |  103   |   97    |   6    |
|   v Salon                    | [Incluse] | [Partiellement publiee] | [En ecart]  |   12  |    2   |   10   |    7    |   3    |
|     Lampe TV                 | [Inclus]  | [Publie]                | [Aligne]    |    1  |    0   |    1   |    1    |   0    |
|     Volet baie               | [Inclus]  | [Non publie]            | [Ecart] *   |    1  |    0   |    1   |    0    |   1    |
|     Radiateur decoratif      | [Exclu]   | [Non publie]            | [Aligne]    |    1  |    1   |    0   |    0    |   0    |
|   > Cuisine                  | [Incluse] | [Publiee]               | [Alignee]   |   18  |    0   |   18   |   18    |   0    |
+------------------------------------------------------------------------------------------------------------------------------------------------+

* Infobulle sur badge [Ecart] equipement uniquement :

+--------------------------------------------------------------+
| Cause : Aucun mapping compatible                             |
| Voir le diagnostic pour le detail                            |
+--------------------------------------------------------------+
```

**CTA presents**
- clic sur une piece
- survol / focus du badge `Ecart`
- clic du badge `Ecart` vers le diagnostic

**CTA absents**
- aucun depliage technique dans la home
- aucun lien vers le diagnostic hors badge `Ecart`

**Niveau de detail attendu**  
`Synthese equipement`, jamais `explicabilite detaillee`.

### 6.4 Diagnostic - vue d'entree generale

**Nom de l'ecran**  
`Diagnostic - vue d'entree generale`

**Objectif principal**  
Fournir une liste filtrable d'equipements inclus, prete a l'analyse detaillee cas par cas.

**Message dominant percu**  
`J'entre dans une surface d'explicabilite detaillee des cas inclus, pas dans une seconde home.`

**Audience**  
Utilisateur qui veut comprendre un cas ou filtrer les cas a analyser.

**Actions possibles**
- rechercher ;
- filtrer ;
- deplier une ligne ;
- fermer le modal ;
- arriver via le bouton `Diagnostic` ou via un badge `Ecart` de la home.

**Actions interdites**
- retrouver une synthese globale du parc ;
- voir les equipements exclus ;
- retrouver le bandeau `Sante` ;
- retrouver les compteurs home.

**Informations autorisees**
- titre de surface ;
- recherche ;
- filtres ;
- tableau principal ;
- equipements inclus uniquement ;
- detail commandes existant au depliage.

**Informations interdites**
- sante globale ;
- compteurs du parc ;
- synthese par piece de type home ;
- equipements exclus dans la vue standard ;
- redesign du detail commandes existant.

**Structure verticale exacte**
1. Entete modal `Diagnostic de Couverture`
2. Zone `Recherche / filtres`
3. `Tableau principal`
4. Detail commandes existant seulement sous la ligne deployee

**Maquette contractuelle**

```text
+====================================================================================================================+
| DIAGNOSTIC DE COUVERTURE                                                                                 [Fermer] |
+====================================================================================================================+

+--------------------------------------------------------------------------------------------------------------------+
| RECHERCHE / FILTRES                                                                                                |
| [Recherche texte ________________________________________________ ]                                                |
| Piece [Tous v] | Ecart [Tous v] | Statut [Tous v] | Confiance [Tous v] | Raison [____________________]            |
+--------------------------------------------------------------------------------------------------------------------+

+--------------------------------------------------------------------------------------------------------------------+
| Piece            | Nom                          | Ecart      | Statut              | Confiance | Raison            |
|--------------------------------------------------------------------------------------------------------------------|
| Salon            | > Lampe TV                   | [Aligne]   | [Statut existant]   | [Sur]     | -                 |
| Salon            | > Volet baie                 | [Ecart]    | [Statut existant]   | [Ambigu]  | Aucun mapping...  |
| Exterieur        | > Sonde terrasse             | [Aligne]   | [Statut existant]   | [Probable]| -                 |
+--------------------------------------------------------------------------------------------------------------------+
```

**CTA presents**
- recherche texte
- filtres
- clic sur une ligne pour la deplier
- fermeture du modal

**CTA absents**
- aucun compteur global
- aucune synthese parc
- aucune vue exhaustive avec exclus

**Niveau de detail attendu**  
`Liste d'entree detaillee`, avec detail a la demande.

**Regle contractuelle sur la colonne `Statut` du diagnostic**
- La colonne `Statut` du diagnostic est ancree sur la logique de la page diagnostic existante.
- Elle conserve la semantique du diagnostic actuel.
- Elle ne doit pas etre remappee artificiellement vers la logique synthetique de la home.
- Cette colonne et le detail commandes existant forment un ensemble coherent a preserver.

### 6.5 Diagnostic - cas aligne

**Nom de l'ecran**  
`Diagnostic - cas aligne`

**Objectif principal**  
Permettre de confirmer rapidement qu'un cas est OK, puis d'acceder directement au detail commandes existant si necessaire.

**Message dominant percu**  
`Ce cas est aligne ; je peux verifier son niveau de confiance sans surcouche inutile.`

**Audience**  
Utilisateur qui verifie un cas deja considere comme OK.

**Actions possibles**
- lire la ligne du tableau ;
- deplier la ligne ;
- consulter le detail commandes existant.

**Actions interdites**
- afficher un resume ajoute au-dessus du detail ;
- dupliquer l'information de la ligne dans un bloc intermediaire.

**Informations autorisees**
- `Ecart = Aligne`
- `Statut` selon la logique diagnostic actuelle
- `Confiance`
- `Raison = -` ou vide si redondante

**Informations interdites**
- bloc `cas aligne` ajoute ;
- resume `aucune action requise` ;
- remap force du `Statut` diagnostic vers la logique home.

**Structure verticale exacte**
1. Entete modal
2. Recherche / filtres
3. Tableau principal
4. Detail commandes existant directement sous la ligne si elle est ouverte

**Maquette contractuelle**

```text
| Piece | Nom              | Ecart    | Statut              | Confiance | Raison |
|-------|------------------|----------|---------------------|-----------|--------|
| Salon | > Lampe TV       | [Aligne] | [Publie]            | [Sur]     | -      |
| Salon | > Sonde fenetre  | [Aligne] | [Partiellement publie] | [Probable] | -   |

Apres depliage :

| Salon | v Lampe TV       | [Aligne] | [Publie] | [Sur] | - |
|------------------------------------------------------------------------|
| [DETAIL COMMANDES EXISTANT CONSERVE TEL QUEL]                          |
```

**CTA presents**
- deplier la ligne

**CTA absents**
- aucun bloc resume au-dessus du detail

**Niveau de detail attendu**  
Lecture rapide `OK / statut / confiance`, puis detail existant si voulu.

### 6.6 Diagnostic - cas avec ecart

**Nom de l'ecran**  
`Diagnostic - cas avec ecart`

**Objectif principal**  
Rendre lisible un cas problematique sans changer la logique existante du diagnostic.

**Message dominant percu**  
`Je vois qu'il y a un ecart, pourquoi il merite mon attention, et je peux ouvrir directement le detail commandes existant.`

**Audience**  
Utilisateur qui analyse un cas a probleme.

**Actions possibles**
- lire la ligne d'ecart ;
- deplier la ligne ;
- arriver directement sur cette ligne depuis la home ;
- consulter le detail commandes existant.

**Actions interdites**
- injecter un resume artificiel au-dessus du detail ;
- remapper brutalement le `Statut` sur la logique home ;
- reconstruire une fiche theorique differente du diagnostic existant.

**Informations autorisees**
- `Ecart`
- `Statut` selon la logique diagnostic actuelle
- `Confiance`
- `Raison` si la logique actuelle la rend utile

**Informations interdites**
- bloc `resume d'ecart` ajoute ;
- surcouche avant le detail commandes ;
- detail home reconstitue dans le diagnostic.

**Structure verticale exacte**
1. Entete modal
2. Recherche / filtres
3. Tableau principal
4. Detail commandes existant directement sous la ligne si elle est ouverte

**Maquette contractuelle**

```text
| Piece   | Nom                   | Ecart   | Statut              | Confiance | Raison                   |
|---------|-----------------------|---------|---------------------|-----------|--------------------------|
| Salon   | > Volet baie          | [Ecart] | [Statut existant]   | [Ambigu]  | Aucun mapping compatible |
| Cuisine | > Prise plan travail  | [Ecart] | [Statut existant]   | [Sur]     | Changement en attente    |

Arrivee ciblee depuis la home :

| Salon   | v Volet baie          | [Ecart] | [Statut existant]   | [Ambigu]  | Aucun mapping compatible | <- focus temporaire
|---------------------------------------------------------------------------------------------------------------|
| [DETAIL COMMANDES EXISTANT CONSERVE TEL QUEL]                                                                |
```

**CTA presents**
- deplier la ligne
- arriver via le badge `Ecart` de la home avec focus obligatoire

**CTA absents**
- aucun bloc supplementaire au-dessus du detail

**Niveau de detail attendu**  
Lecture du probleme dans la ligne, explication approfondie via le detail existant.

## 7. Invariants visuels et perceptifs

- Si la home permet de comprendre un cas detaille sans quitter la page, l'implementation est fausse.
- Si la home affiche `Confiance` ailleurs que dans le diagnostic, l'implementation est fausse.
- Si la home affiche `Raison` en permanence, l'implementation est fausse.
- Si la home ajoute une colonne `Cause`, l'implementation est fausse.
- Si la home redevient une succession de blocs `synthese + details par piece` au lieu d'un tableau hierarchique unique, l'implementation est fausse.
- Si l'ordre des colonnes chiffrees home n'est pas `Total / Exclus / Inclus / Publies / Ecarts`, l'implementation est fausse.
- Si les 3 badges `Perimetre / Statut / Ecart` ne sont pas alignees dans 3 colonnes fixes au niveau piece, l'implementation est fausse.
- Si le badge `Ecart` home n'ouvre pas le meme diagnostic avec scroll, depliage et focus temporaire, l'implementation est fausse.
- Si le diagnostic standard montre des equipements exclus, l'implementation est fausse.
- Si le diagnostic affiche la sante globale ou une synthese du parc en message dominant, l'implementation est fausse.
- Si le diagnostic perd sa logique `liste filtrable d'equipements inclus + detail a la demande`, l'implementation est fausse.
- Si le detail commandes existant est remplace par une nouvelle structure theorique, l'implementation est fausse.

## 8. Elements non duplicables

| Exclusif home | Exclusif diagnostic | Partage mais sous forme differente |
| --- | --- | --- |
| Bandeau `Sante` | Grande modal diagnostic separee | `Ecart` |
| Actions `Home Assistant` | Recherche et filtres | `Statut` |
| Export diagnostic support | `Confiance` | `Cause / raison` |
| Menu plugin | `Raison` | `Equipement` |
| Tableau hierarchique unique du parc | Detail commandes existant | Point d'entree d'un cas |
| Colonnes `Nom / Perimetre / Statut / Ecart / Total / Exclus / Inclus / Publies / Ecarts` | Colonnes `Piece / Nom / Ecart / Statut / Confiance / Raison` |  |
| Infobulle courte sur badge `Ecart` | Vue standard in-scope-only |  |

## 9. Cas concrets de rendu

### 9.1 Cas 1 - Equipement inclus, publie, sans ecart

**Dans la home - piece ouverte**

```text
| Lampe TV | [Inclus] | [Publie] | [Aligne] | 1 | 0 | 1 | 1 | 0 |
```

Lecture attendue :
- l'equipement est dans le perimetre ;
- il est publie ;
- il n'est pas en ecart ;
- aucune cause n'est visible ;
- aucun diagnostic inline n'apparait.

**Dans le diagnostic**

```text
| Salon | > Lampe TV | [Aligne] | [Publie] | [Sur] | - |
```

### 9.2 Cas 2 - Equipement inclus, non publie, avec ecart et cause

**Dans la home - piece ouverte**

```text
| Volet baie | [Inclus] | [Non publie] | [Ecart] | 1 | 0 | 1 | 0 | 1 |
```

**Infobulle home**

```text
Cause : Aucun mapping compatible
Voir le diagnostic pour le detail
```

**Navigation obligatoire**
- clic sur le badge `Ecart`
- ouverture du meme modal diagnostic
- scroll automatique si necessaire
- depliage automatique
- focus temporaire visible

**Dans le diagnostic**

```text
| Salon | v Volet baie | [Ecart] | [Statut existant] | [Ambigu] | Aucun mapping compatible |
|-----------------------------------------------------------------------------------------------|
| [DETAIL COMMANDES EXISTANT CONSERVE TEL QUEL]                                                 |
```

### 9.3 Cas 3 - Equipement exclu visible en home mais absent du diagnostic standard

**Dans la home - piece ouverte**

```text
| Radiateur decoratif | [Exclu] | [Non publie] | [Aligne] | 1 | 1 | 0 | 0 | 0 |
```

Lecture attendue :
- l'equipement reste visible dans la home ;
- il participe a la lecture du parc ;
- il n'ouvre pas un diagnostic standard de cas inclus.

**Dans le diagnostic standard**
- ligne absente par design ;
- l'analyse exhaustive releve de l'export support, pas du diagnostic standard.

## 10. Checklist d'acceptation visuelle et terrain

### 10.1 Checklist de review implementation

- [ ] Le shell home est conserve : bandeau `Sante`, actions `Home Assistant`, export support, menu plugin.
- [ ] La zone centrale home est un tableau hierarchique unique, pas deux blocs separes.
- [ ] La vue home par defaut montre uniquement la ligne `Parc global`.
- [ ] Les colonnes home sont exactement `Nom / Perimetre / Statut / Ecart / Total / Exclus / Inclus / Publies / Ecarts`.
- [ ] Les lignes piece portent 3 colonnes badges fixes : `Perimetre / Statut / Ecart`.
- [ ] Aucune cause n'apparait au niveau piece.
- [ ] Les lignes equipement home n'affichent jamais `Confiance`.
- [ ] La cause en home n'apparait qu'en infobulle courte sur badge `Ecart`.
- [ ] Le badge `Ecart` home est cliquable.
- [ ] Le clic sur badge `Ecart` ouvre le meme diagnostic avec scroll, depliage et focus temporaire obligatoires.
- [ ] Le diagnostic standard n'affiche que les equipements inclus.
- [ ] Les equipements exclus sont absents du diagnostic standard par design.
- [ ] Le diagnostic ne montre ni bandeau `Sante`, ni compteurs globaux, ni synthese de parc.
- [ ] Les colonnes diagnostic sont exactement `Piece / Nom / Ecart / Statut / Confiance / Raison`.
- [ ] La colonne `Statut` du diagnostic conserve sa logique actuelle ; elle n'est pas remappee artificiellement a la logique home.
- [ ] Toutes les lignes du diagnostic sont repliees par defaut a l'entree generale.
- [ ] Le detail commandes existant est conserve tel quel au depliage.
- [ ] Aucune surcouche resume n'est ajoutee au-dessus du detail commandes, ni pour un cas aligne ni pour un cas en ecart.

### 10.2 Criteres terrain pour Bob / Dana

- [ ] En moins de 3 secondes, un utilisateur comprend que la home sert a piloter et synthetiser le parc.
- [ ] En moins de 3 secondes, un utilisateur repere ou sont les ecarts et quelle piece ouvrir.
- [ ] Un utilisateur ne confond pas la home avec une surface diagnostic.
- [ ] Un utilisateur comprend que le diagnostic est une surface separee d'analyse detaillee.
- [ ] Un utilisateur retrouve immediatement le cas cible quand il vient de la home via un badge `Ecart`.
- [ ] Un utilisateur ne percoit pas de duplication confuse entre home et diagnostic.
- [ ] Un utilisateur percoit que les exclus restent visibles en home mais ne polluent pas le diagnostic standard.
- [ ] Un utilisateur comprend que `Confiance` appartient au diagnostic, pas a la home.

## 11. Points ouverts minimaux

- La formule backend exacte de `Publies` n'est pas figee ici ; en revanche, son emplacement visuel et son rang de lecture sont figes.
- L'emplacement UX de `Publies` est fige par la presente spec, mais aucune future story corrective ne peut supposer un recalcul frontend local de `Publies`.
- Toute story corrective sur `Publies` devra d'abord verifier si la donnee existe deja cote backend ou si une extension bornee du contrat est necessaire.
- Si une extension backend est necessaire, elle devra etre traitee explicitement, pas implicitement dans le JS.
- Le style exact de la mise en evidence temporaire dans le diagnostic n'est pas fige ; en revanche, son existence, sa perception immediate et son declenchement automatique sont obligatoires.

## 12. Conclusion operative

Le contrat final est le suivant :
- la home est une console de synthese et de pilotage du parc ;
- le diagnostic est une surface d'explicabilite detaillee des cas du perimetre inclus ;
- le passage de la home vers le diagnostic est direct, cible et visible ;
- aucune des deux surfaces ne doit absorber le role de l'autre.

Cette spec est suffisamment concrete pour servir de reference de conformite avant creation des futures stories correctives Epic 4.
