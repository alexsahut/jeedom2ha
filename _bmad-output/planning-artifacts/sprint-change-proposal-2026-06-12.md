---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-06-12
status: approved
scope_classification: moderate
trigger: cadrage-pe-epic-12-plugin-mapping-configurable
mode: batch
communication_language: french
proposed_by: clawcode
impacts_if_approved:
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/planning-artifacts/active-cycle-manifest.md
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/ux-spec.md
references:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/planning-artifacts/backlog-icebox.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/implementation-artifacts/pe-epic-10-retro-2026-06-12.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-10.md
---

# Sprint Change Proposal 2026-06-12 - Cadrage pe-epic-12 : plugin de mapping configurable

## 1. Issue Summary

### Trigger

Apres cloture de `pe-epic-10` le `2026-06-12`, Alexandre a demande un cadrage de `pe-epic-12` autour d'un **plugin de mapping configurable**, inspire du modele Homebridge de Jeedom : permettre a l'utilisateur avance de reprendre la main sur certains choix de projection sans casser le moteur automatique.

Au moment de ce correct-course :

- `pe-epic-10` est `done` avec retrospective complete ;
- `pe-epic-11` est qualifie en backlog pour l'energie / routage solaire (`MSunPV` eq553 puis chauffe-eau eq554) ;
- aucun `pe-epic-12` n'existe encore dans les artefacts actifs ;
- le PRD contient deja l'intention produit des overrides (`FR23`, `FR25`) mais les classe comme croissance/post-MVP et non comme epic materialise.

Alexandre a confirme les arbitrages suivants avant redaction :

1. mode `batch` pour presenter le SCP complet ;
2. decoupage `12a / 12b` accepte ;
3. ordre d'execution confirme : `pe-epic-11` reste execute avant `pe-epic-12`.

### Problem statement

Le moteur actuel est devenu explicable, gouverne et extensible, mais il reste essentiellement **automatique**. Cette promesse est forte pour la qualite, mais elle laisse trois cas produit sans vraie surface de resolution :

1. l'utilisateur expert sait que son equipement Jeedom peut etre represente correctement dans HA, mais le mapping automatique reste trop prudent ;
2. certains plugins Jeedom exposent des commandes atypiques ou mal generisees, pour lesquelles une configuration manuelle serait plus rapide qu'une nouvelle regle globale ;
3. le support a besoin de distinguer clairement "le moteur a decide seul" de "l'utilisateur a volontairement surcharge la decision".

Le risque inverse est important : si les overrides deviennent un contournement libre du pipeline, ils peuvent detruire la promesse fondatrice du cycle. Un override ne doit jamais publier une projection invalide ni masquer la decision native du moteur.

### Evidence

| Evidence | Constat | Lecture |
|---|---|---|
| `prd.md` Scope post-MVP | Les overrides avances sont in-scope croissance, apres noyau | Le sujet est legitime mais devait attendre la stabilisation du pipeline |
| `prd.md` FR23 / FR25 | Le systeme peut appliquer des overrides autorises sans effacer la decision native | Le contrat produit existe deja au niveau exigences |
| `architecture-projection-engine.md` D6 / D11 | Les overrides d'eligibilite existent ; les overrides type/publication sont un point d'extension differe | L'architecture a prevu le point, mais pas encore le design detaille |
| `pe-epic-10-retro-2026-06-12.md` | Prochaine execution recommandee = `create-story` 11.1 `MSunPV / RouteurSolaire` | `pe-epic-12` doit etre cadre maintenant, pas execute avant l'energie |
| `backlog-icebox.md` §1 | Drill-down commande par commande est un futur epic dedie | `pe-epic-12` doit integrer ce besoin avec prudence, sans polluer la home/diagnostic existants |

### Category

**Roadmap adjustment / backlog materialization.**

Le correct-course ne reouvre pas le PRD et ne change pas l'objectif du cycle. Il materialise une capacite deja anticipee dans le produit, en la placant apres les epics de couverture utile et en posant les garde-fous necessaires.

## 2. Impact Analysis

### 2.1 Checklist correct-course

| Item | Statut | Notes |
|---|---|---|
| 1.1 Trigger story | [N/A] | Aucun bug story-level ne declenche ce changement ; le trigger est roadmap post-closeout `pe-epic-10`. |
| 1.2 Core problem | [x] | Besoin d'une couche d'override explicite, testable et gouvernee. |
| 1.3 Evidence | [x] | PRD FR23/FR25, architecture D6/D11, retro epic 10, backlog icebox. |
| 2.1 Current epic | [x] | `pe-epic-10` reste clos ; aucun rollback. |
| 2.2 Epic-level changes | [x] | Ajouter `pe-epic-12` en backlog futur, avec deux vagues 12a/12b. |
| 2.3 Future epics | [x] | `pe-epic-11` reste prochain epic execute ; `pe-epic-12` vient apres. |
| 2.4 New epic needed | [x] | Oui, car les overrides avancés meritaient un conteneur explicite. |
| 2.5 Priority/order | [x] | Pas de resequencing : energie avant mapping configurable. |
| 3.1 PRD conflict | [x] | Aucun conflit ; le PRD anticipe deja les overrides. |
| 3.2 Architecture conflict | [!] | Architecture a un point d'extension differe ; design 12a devra preciser injection, schema et diagnostic. |
| 3.3 UI/UX conflict | [!] | UI 12b doit etre cadree separement ; pas de front riche sans strategie de test minimale. |
| 3.4 Other artifacts | [!] | Epics, sprint-status et manifeste a mettre a jour seulement apres approbation. |
| 4.1 Direct adjustment | [x] Viable | Ajouter un epic backlog sans toucher aux epics clos. |
| 4.2 Rollback | [x] Not viable | Aucun travail recent n'a besoin d'etre reverti. |
| 4.3 MVP review | [x] Not needed | Le MVP du cycle reste atteint par le pipeline explicable. |
| 4.4 Recommended path | [x] | Hybrid prudent : cadrage maintenant, execution apres `pe-epic-11`. |
| 5.x Proposal components | [x] | Le present SCP porte issue, impact, changements proposes, handoff. |
| 6.3 Approval | [!] | Approbation utilisateur requise avant modification des artefacts actifs. |
| 6.4 Sprint status | [!] | A faire uniquement si ce SCP est approuve. |

### 2.2 Ce qui ne change pas

- Le cycle actif reste **Moteur de projection explicable**.
- La validation HA en etape 3 reste obligatoire.
- `ha-projection-reference.md` reste la source-of-truth des contraintes HA.
- La cause principale canonique et le contrat 4D restent stables et enrichis uniquement de facon additive.
- `pe-epic-11` reste le prochain epic execute : `MSunPV / RouteurSolaire` puis chauffe-eau.
- Les overrides ne deviennent pas une excuse pour ouvrir des composants HA sans FR40 / NFR10.

### 2.3 Ce qui change si approuve

- `pe-epic-12` est materialise comme epic backlog futur.
- Le sujet "mapping configurable" est decoupe en deux vagues :
  - **12a** : moteur d'override backend + configuration JSON versionnee, testable sans UI riche ;
  - **12b** : UI Jeedom de configuration, apres validation du contrat backend.
- Les overrides sont explicitement limites a des points d'injection compatibles avec le pipeline :
  - forcer ou exclure un equipement avant publication ;
  - forcer le candidat HA ou la selection de commandes avant validation ;
  - surcharger metadata non structurelle (nom affiche, area suggeree) ;
  - tracer toute surcharge dans le diagnostic.
- Le "forcer publication" est renomme produitement : **forcer la decision apres validation**, jamais publier une projection HA invalide.

### 2.4 Impact technique

| Zone | Impact |
|---|---|
| Backend Python | Ajouter un loader d'overrides versionnes et une couche d'application entre mapping candidat et validation/decision. |
| Modele de donnees | Definir schema JSON versionne, migrations, export/import, identifiants stables par eq/cmd ID Jeedom. |
| Diagnostic | Ajouter des `reason_code` / champs traces `override_*` de facon additive, sans effacer la decision native. |
| Tests | Golden corpus, cas nominaux, cas invalides, non-regression 4D, et tests de migration schema. |
| PHP/Jeedom | 12a peut se limiter a persistance/import/export ; 12b ajoute l'UI native Jeedom. |
| UX | Une surface de configuration dediee est requise ; ne pas injecter le parametrage avance dans la home ou le diagnostic standard. |

## 3. Path Forward Evaluation

### Option 1 - Direct Adjustment : ajouter `pe-epic-12` maintenant, execution apres `pe-epic-11`

**Statut : recommandee.**

Cette option materialise l'intention produit sans perturber l'execution immediate. Elle donne une place claire aux overrides dans la roadmap, tout en conservant le prochain pas terrain : energie / routage solaire.

Effort estime : moyen a eleve. Risque : moyen si 12a reste backend-first ; eleve si l'UI est lancee trop tot.

### Option 2 - Passer `pe-epic-12a` avant `pe-epic-11`

**Statut : non recommande.**

L'energie/routage est qualifie, utile, et ne demande normalement pas de nouveau type HA. Le traiter d'abord fournit un cas terrain supplementaire pour comprendre les limites reelles du mapping automatique avant d'introduire les overrides.

Effort estime : eleve. Risque : dispersion et perte de momentum terrain.

### Option 3 - Lancer directement une UI complete de mapping configurable

**Statut : non recommande.**

Le projet n'a pas encore de CI PHP/front robuste. Une UI riche sans contrat backend stabilise creerait une zone non testee sur une capacite sensible. Le risque support et regression serait disproportionne.

Effort estime : eleve. Risque : eleve.

### Option 4 - Ne pas cadrer maintenant

**Statut : insuffisant.**

Laisser `pe-epic-12` dans les conversations maintient une dette de roadmap. Le cadrage maintenant permet de clarifier les garde-fous sans demarrer l'implementation.

### Selected approach

**Option 1 : Direct Adjustment prudent.**

Ajouter `pe-epic-12` comme backlog futur cadre, avec execution apres `pe-epic-11`, et en imposant une separation stricte 12a/12b.

## 4. Detailed Change Proposals

### 4.1 `epics-projection-engine.md` - Ajouter `pe-epic-12`

**Section :** apres le bloc `pe-epic-11` a materialiser ou a la suite du cycle courant.

**OLD :**

```md
pe-epic-11: backlog
```

**NEW :**

```md
### Epic 12 - Le mapping configurable donne la main a l'utilisateur expert sans casser le pipeline explicable

**Valeur utilisateur :** L'utilisateur expert peut corriger ou affiner la projection d'un equipement Jeedom lorsque le moteur automatique est trop prudent ou incomplet, tout en gardant la decision native, la validation HA et le diagnostic explicables.

**Resultat observable :** Une couche d'overrides optionnelle, versionnee et reversible s'ajoute au-dessus du pipeline automatique. Elle permet de forcer un candidat HA, d'exclure un equipement, de mapper des commandes, ou de surcharger certaines metadonnees, sans jamais publier une projection HA structurellement invalide.

**FRs couverts :** FR23, FR24, FR25, FR31, FR40, FR44, FR45

**ARs cles :** AR3, AR6, AR11, AR13, D6/D11 a preciser

**NFRs directement adresses :** NFR4, NFR10, NFR11, NFR12

**Invariants a porter en stories :**
- un override ne contourne jamais la validation HA obligatoire ;
- la decision native du moteur reste visible dans le diagnostic ;
- tout override est reversible et tracable (`override_*`) ;
- le schema d'override est versionne des la premiere story ;
- 12a livre un backend testable sans UI riche ;
- 12b ne demarre qu'apres stabilisation du contrat backend.
```

**Rationale :** Le PRD couvre deja le besoin, mais aucun conteneur d'execution n'existe. L'ajout clarifie la roadmap sans changer l'ordre d'execution.

### 4.2 Stories recommandees pour `pe-epic-12`

#### Story 12.0 - Prefixe d'architecture : contrat d'override, points d'injection et limites

En tant que mainteneur,
je veux formaliser les types d'overrides autorises, leurs points d'injection dans le pipeline et leurs limites,
afin de garantir que la configuration utilisateur ne casse ni la validation HA ni le diagnostic.

Acceptance criteria :

- types d'overrides autorises listes et bornes ;
- distinction claire entre override d'eligibilite, override de candidat mapping, override de decision et override de metadata ;
- interdiction explicite de publier une projection invalide ;
- diagramme ou note d'architecture sur l'ordre d'application ;
- decision sur le format du schema JSON v1.

#### Story 12.1 - Persistance backend du schema d'overrides v1

En tant qu'utilisateur expert,
je veux que mes overrides soient persistants, exportables et associes a des IDs Jeedom stables,
afin de conserver mes choix lors des resyncs, upgrades et renommages.

Acceptance criteria :

- schema JSON v1 documente ;
- stockage sans table SQL custom, compatible configuration Jeedom ou fichier data dedie selon decision architecture ;
- migration forward prevue ;
- export/import minimal ;
- validation stricte du schema avant application.

#### Story 12.2 - Application backend des overrides de mapping candidat

En tant qu'utilisateur expert,
je veux forcer un candidat HA ou mapper explicitement certaines commandes,
afin de resoudre un cas que le moteur automatique ne peut pas inferer correctement.

Acceptance criteria :

- application apres mapping automatique et avant validation HA ;
- conservation de la decision native dans la trace ;
- validation HA executee sur le candidat surcharge ;
- cas d'echec explicite si l'override produit une projection invalide ;
- golden corpus avec cas nominal et cas invalide.

#### Story 12.3 - Overrides de publication et exclusion explicite

En tant qu'utilisateur expert,
je veux exclure un equipement ou autoriser une publication dont la projection est valide mais bloquee par une politique produit,
afin de reprendre la main sans confondre ce choix avec une reussite automatique.

Acceptance criteria :

- exclusion utilisateur reste prioritaire et lisible ;
- "forcer publication" signifie uniquement "forcer la decision apres validation HA reussie" ;
- une confiance faible peut etre assumee si la projection est valide ;
- diagnostic `override_publication_allowed` ou equivalent additif ;
- aucune publication si `projection_validity.is_valid == false`.

#### Story 12.4 - Diagnostic override-aware

En tant qu'utilisateur,
je veux voir ce que le moteur aurait fait sans override et ce qui a ete surcharge,
afin de comprendre et maintenir mes choix.

Acceptance criteria :

- champs diagnostic additifs pour decision native, decision surchargee et source override ;
- `cause_label` / `cause_action` coherents avec la regle no faux CTA ;
- badge ou indicateur "modifie manuellement" dans les surfaces existantes si necessaire ;
- non-regression du contrat 4D.

#### Story 12.5 - UI Jeedom minimale de configuration par equipement

En tant qu'utilisateur expert,
je veux configurer un override depuis une surface Jeedom dediee,
afin de ne pas modifier le JSON a la main pour les cas courants.

Acceptance criteria :

- UI native Jeedom, pas de framework front externe ;
- arborescence piece / equipement ;
- modal ou panneau par equipement ;
- controles pour type HA, commandes retenues, exclusion, retour a l'auto ;
- aucune decision non validee par le backend ;
- strategie de test front minimale definie avant implementation.

#### Story 12.6 - Preview / dry-run avant application

En tant qu'utilisateur expert,
je veux previsualiser l'effet d'un override avant de l'appliquer,
afin d'eviter de polluer Home Assistant avec une configuration approximative.

Acceptance criteria :

- resultat "auto" vs "avec override" visible ;
- erreurs de validation HA visibles avant sauvegarde ;
- aucun publish MQTT pendant le dry-run ;
- export support inclut la preview et les raisons de refus.

#### Story 12.7 - Gate terrain et profils partageables

En tant que mainteneur,
je veux valider les overrides sur un corpus terrain et preparer l'export/import de profils,
afin de transformer la configurabilite en avantage marketplace durable.

Acceptance criteria :

- gate terrain sur au moins trois familles d'equipements reelles ;
- export/import d'un profil JSON anonymisable ;
- documentation utilisateur FR ;
- decision explicite sur un futur partage communautaire de profils, hors execution immediate si trop large.

### 4.3 `sprint-status.yaml` - Proposition d'ajout apres approbation

**OLD :**

```yaml
  pe-epic-11: backlog
```

**NEW :**

```yaml
  pe-epic-11: backlog  # prochain epic execute : energie / routage solaire, P1 MSunPV eq553 puis P2 chauffe-eau eq554
  pe-epic-12: backlog  # mapping configurable / overrides utilisateur ; cadre par SCP 2026-06-12 ; execution apres pe-epic-11
```

**Rationale :** Le tracker doit distinguer clairement l'ordre d'execution : cadrage 12 maintenant, execution 11 d'abord.

### 4.4 `active-cycle-manifest.md` - Proposition d'actualisation

**OLD :**

```md
Apres le correct-course du `2026-06-07` (...) la prochaine etape attendue est l'execution de `pe-epic-10`
```

**NEW :**

```md
Apres cloture de `pe-epic-10` le `2026-06-12`, la prochaine etape d'execution est `create-story` 11.1 sur `MSunPV / RouteurSolaire`. Le correct-course du `2026-06-12` cadre `pe-epic-12` comme epic futur de mapping configurable, mais ne modifie pas l'ordre d'execution : `pe-epic-11` reste prioritaire.
```

**Rationale :** Le manifeste est obsolete depuis la cloture de `pe-epic-10` et doit pointer vers le prochain workflow BMAD reel.

## 5. Marketplace Product Adjustments

Pour que `pe-epic-12` contribue a un plugin plebiscite sur la marketplace Jeedom, le cadrage doit depasser le simple "champ de configuration avance".

### 5.1 Ce qui doit etre valorise

- **Onboarding court** : la configurabilite doit aider a resoudre un cas bloque, pas devenir une etape obligatoire du premier demarrage.
- **Diagnostic comme argument principal** : expliquer "pourquoi cet equipement n'apparait pas" et "quel override existe" est une force differenciante.
- **Preview avant publication** : la confiance vient du dry-run, pas d'un bouton de force brute.
- **Retour a l'automatique** : chaque override doit avoir un chemin simple de reset.
- **Profils exportables** : a terme, des profils par plugin Jeedom ou marque peuvent creer un effet communautaire.

### 5.2 Garde-fous produit

- L'UI ne doit pas transformer le plugin en tableur de commandes incomprehensible.
- Le mode automatique reste le comportement par defaut.
- Les overrides doivent etre visibles, reversibles et exportables.
- Le support doit pouvoir demander un export diagnostic qui inclut les overrides sans fuite de secrets.
- Les profils partageables sont un objectif de croissance, pas une dependance de 12a.

## 6. Recommendation

Approuver un correct-course **modere** :

- oui a la materialisation de `pe-epic-12` ;
- oui au decoupage `12a backend testable` puis `12b UI Jeedom` ;
- oui au cadrage produit marketplace (preview, retour auto, diagnostic, profils) ;
- non a l'execution de `pe-epic-12` avant `pe-epic-11` ;
- non a une UI riche avant schema backend, validation et diagnostic override-aware ;
- non a tout override qui contourne la validation HA.

## 7. Implementation Handoff

### Scope classification

**Moderate.**

Le changement ne demande pas de rollback ni de redefinition du MVP, mais il reorganise le backlog futur et introduit une capacite sensible qui touchera backend, diagnostic, persistance PHP et UI.

### Recipients

| Role | Responsabilite |
|---|---|
| Scrum Master | Ajouter l'epic au backlog et garder `pe-epic-11` comme prochain epic execute. |
| Product Owner / PM | Valider la promesse utilisateur et les limites marketplace. |
| Architect | Produire Story 12.0 avec points d'injection, schema v1 et frontieres de validation. |
| Dev | Executer 12a backend avec tests et golden corpus avant tout front riche. |
| QA | Definir tests migration, non-regression 4D, dry-run et gates terrain. |
| UX | Cadrer 12b en UI native Jeedom, sans melanger home, diagnostic standard et configuration avancee. |

### Success criteria

- `pe-epic-12` apparait en backlog actif, apres `pe-epic-11`.
- Les stories 12a/12b sont separees et testables.
- Le schema d'override v1 est versionne avant la premiere implementation.
- Aucun override ne publie une projection invalide.
- Le diagnostic montre la decision native et la surcharge.
- Le mode automatique reste le comportement par defaut.

## 8. Decision Requested

Decision demandee a Alexandre :

- **yes** -> appliquer ce correct-course : mettre a jour `epics-projection-engine.md`, `sprint-status.yaml` et `active-cycle-manifest.md` ;
- **revise** -> garder le principe mais ajuster le decoupage, les stories ou l'ordre ;
- **no** -> ne pas materialiser `pe-epic-12` maintenant et revenir a `create-story` 11.1 uniquement.

## 9. Decision

Approved — Alexandre a repondu `yes` le `2026-06-12`.

Actions d'application attendues :

- materialiser `pe-epic-12` dans `epics-projection-engine.md` ;
- ajouter `pe-epic-12: backlog` dans `sprint-status.yaml` ;
- actualiser `active-cycle-manifest.md` pour pointer vers `pe-epic-11` comme prochaine execution et vers ce SCP comme dernier correct-course.
