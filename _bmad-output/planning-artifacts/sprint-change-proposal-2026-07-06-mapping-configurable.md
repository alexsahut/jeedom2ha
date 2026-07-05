---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-07-06
status: approved
scope_classification: moderate
trigger: cadrage-pe-epic-16-mapping-configurable-commande-par-commande
mode: batch
communication_language: french
proposed_by: clawcode
impacts_if_approved:
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/planning-artifacts/active-cycle-manifest.md
  - _bmad-output/planning-artifacts/backlog-icebox.md
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/ux-spec.md
references:
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-12.md (cadrage historique pe-epic-12, renumeroté ici)
  - _bmad-output/planning-artifacts/active-cycle-manifest.md (§9, interdiction d'exécuter le cadrage historique tel quel)
  - _bmad-output/planning-artifacts/backlog-icebox.md (§1, drill-down commande par commande)
  - _bmad-output/planning-artifacts/ha-projection-reference.md / .xlsx / .yaml
  - _bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md
  - _bmad-output/planning-artifacts/homebridge-field-inventory-request-2026-06-07.md
  - _bmad-output/planning-artifacts/epics-projection-engine.md (Epic 15, clos 2026-07-06)
---

# Sprint Change Proposal 2026-07-06 - Cadrage pe-epic-16 : mapping configurable commande par commande

## 1. Issue Summary

### Trigger

Après clôture complète de `pe-epic-15` (visibilité console Energy/streaming/FAN parity, gate terrain de clôture PASS le 2026-07-05), Alexandre a demandé de reprendre le sujet **mapping configurable**, dans l'esprit du plugin Homebridge de Jeedom, avec des exigences précisées par rapport au cadrage de 2026-06-12 :

1. reprendre le classement des équipements par pièce (comme Homebridge) ;
2. pour chaque commande, afficher le `generic_type` actuellement configuré **et** ce que Home Assistant attend pour que l'entité fonctionne correctement — lacune identifiée dans Homebridge lui-même ;
3. pour les commandes sans `generic_type`, proposer automatiquement une configuration à partir du moteur de mapping existant ;
4. permettre une **surcharge locale HA** qui ne modifie pas le `generic_type` Jeedom natif (pour ne pas casser une configuration Homebridge qui fonctionne), mais qui affecte un type d'entité HA différent nécessitant potentiellement un `generic_type` équivalent différent côté HA.

### Constat de cadrage historique

Un cadrage complet existe déjà : `sprint-change-proposal-2026-06-12.md`, approuvé le 2026-06-12, matérialisait `pe-epic-12` avec 8 stories (12.0 à 12.7), un découpage 12a backend / 12b UI, et des garde-fous produits (mode auto par défaut, aucun override ne contourne `validate_projection()`, traçabilité `override_*`, retour à l'auto toujours possible).

Ce cadrage n'a **jamais été exécuté** : le numéro `pe-epic-12` a depuis été recyclé par l'epic runtime state-streaming (aujourd'hui `done`). `active-cycle-manifest.md` §9 l'interdit explicitement en l'état : *"le cadrage historique [...] ne doit pas être exécuté tel quel [...] nouveau correct-course [...] nouvelle numérotation"*.

Le contenu de fond (points d'injection, invariants, découpage 12a/12b) reste valide et est repris à ~90% dans ce document. Ce qui change : la numérotation (`pe-epic-16`), l'intégration du point "drill-down commande par commande" du backlog icebox (§1), et l'enrichissement UX explicite demandé par Alexandre (affichage de l'attendu HA par commande, proposition automatique, surcharge à double granularité Jeedom/HA).

### Problem statement

Le moteur actuel est explicable, gouverné et extensible, mais reste **automatique**. Trois cas produits restent sans surface de résolution :

1. l'utilisateur expert sait que son équipement peut être représenté correctement dans HA, mais le mapping automatique reste trop prudent ou incomplet niveau commande ;
2. l'utilisateur ne sait pas **ce que HA attend** pour qu'un type d'entité fonctionne — lacune identique à celle observée dans Homebridge lui-même, qu'Alexandre veut explicitement combler ;
3. l'utilisateur veut parfois représenter un même équipement Jeedom différemment côté HA sans casser sa configuration Homebridge existante (qui dépend du `generic_type` natif) — la surcharge doit donc pouvoir vivre **au niveau HA uniquement**, sans toucher au `generic_type` Jeedom source.

Le risque produit reste identique à 2026-06-12 : si les overrides deviennent un contournement libre du pipeline, ils détruisent la promesse fondatrice du cycle. Un override ne doit jamais publier une projection invalide ni masquer la décision native du moteur.

### Evidence

| Evidence | Constat | Lecture |
|---|---|---|
| `sprint-change-proposal-2026-06-12.md` | Cadrage complet déjà validé une fois par Alexandre, jamais exécuté | Base réutilisable à 90%, seule la numérotation et le scope UX changent |
| `active-cycle-manifest.md` §9 | Interdiction explicite de rejouer `pe-epic-12` tel quel | Renumérotation `pe-epic-16` obligatoire |
| `backlog-icebox.md` §1 | Drill-down commande par commande qualifié "futur epic dédié", introduit la hiérarchie niveau 4 (`pièce -> équipement -> commande`) | Même hiérarchie que le mapping configurable ; à absorber dans le même epic plutôt que dupliquer un cadrage niveau 4 |
| `architecture-projection-engine.md` D6/D11 | Point d'extension override différé, jamais détaillé | Toujours vrai, Story 16.0 doit préciser injection + schéma |
| `homebridge-homekit-vs-ha-delta-2026-06-07.md` | Delta déjà documenté entre scope HomeKit et scope HA actuel | Source utile pour la table "ce que HA attend" par famille |
| Demande Alexandre 2026-07-06 | Attente HA doit être visible par commande, proposition auto pour commandes sans `generic_type`, surcharge HA sans toucher au `generic_type` Jeedom | Nouveau AC explicite non couvert par le cadrage 2026-06-12 initial |

### Category

**Roadmap adjustment / re-cadrage d'un sujet déjà validé, avec extension de scope UX explicite.**

Le correct-course ne rouvre pas le PRD. Il renumérote un cadrage déjà approuvé, absorbe un item icebox adjacent, et ajoute des AC precis demandés par Alexandre sur la visibilité de l'attendu HA et la double granularité de surcharge (Jeedom vs HA).

## 2. Impact Analysis

### 2.1 Checklist correct-course

| Item | Statut | Notes |
|---|---|---|
| 1.1 Trigger story | [N/A] | Pas de bug story-level ; trigger roadmap post-closeout `pe-epic-15`. |
| 1.2 Core problem | [x] | Couche d'override explicite + visibilité de l'attendu HA par commande + proposition auto. |
| 1.3 Evidence | [x] | SCP historique 2026-06-12, manifeste §9, icebox §1, delta Homebridge. |
| 2.1 Current epic | [x] | `pe-epic-15` reste clos ; aucun rollback. |
| 2.2 Epic-level changes | [x] | Ajouter `pe-epic-16` en backlog, deux vagues 16a/16b, absorbant icebox §1. |
| 2.3 Future epics | [x] | Aucun epic en cours conflictuel ; 1-15 tous `done`. |
| 2.4 New epic needed | [x] | Oui, conteneur explicite requis, numéro 16 libre confirmé (grep sprint-status.yaml). |
| 2.5 Priority/order | [x] | Aucun autre epic en attente ; `pe-epic-16` devient le prochain epic exécuté. |
| 3.1 PRD conflict | [x] | Aucun conflit ; FR23/FR25 couvrent déjà l'intention overrides. |
| 3.2 Architecture conflict | [!] | Design 16a devra préciser injection, schéma double-niveau (Jeedom/HA) et diagnostic. |
| 3.3 UI/UX conflict | [!] | UI 16b doit être cadrée séparément (Story 16.5), inspirée Homebridge mais avec l'attendu HA visible — pas de front riche sans stratégie de test minimale. |
| 3.4 Other artifacts | [!] | Epics, sprint-status, manifeste et backlog-icebox à mettre à jour seulement après approbation. |
| 4.1 Direct adjustment | [x] Viable | Ajouter un epic backlog sans toucher aux epics clos, absorber icebox §1. |
| 4.2 Rollback | [x] Not viable | Aucun travail récent à revertir. |
| 4.3 MVP review | [x] Not needed | Le MVP du cycle reste atteint. |
| 4.4 Recommended path | [x] | Direct Adjustment : cadrage maintenant, exécution immédiate possible (aucun epic concurrent). |
| 5.x Proposal components | [x] | Ce SCP porte issue, impact, changements proposés, handoff. |
| 6.3 Approval | [!] | Approbation utilisateur requise avant modification des artefacts actifs. |
| 6.4 Sprint status | [!] | À faire uniquement si ce SCP est approuvé. |

### 2.2 Ce qui ne change pas

- Le cycle actif reste **Moteur de projection explicable**.
- La validation HA en étape 3 (`validate_projection()`) reste obligatoire, aucun override ne la contourne.
- `ha-projection-reference.md` reste la source-of-truth des contraintes HA et des `generic_type` attendus par composant.
- La cause principale canonique et le contrat 4D restent stables, enrichis uniquement de façon additive.
- Les epics 1 à 15 restent clos, aucune réouverture de mapping/publication/diagnostic existants hors du périmètre override explicite de ce nouvel epic.

### 2.3 Ce qui change si approuvé

- `pe-epic-16` est matérialisé comme prochain epic à exécuter (aucun epic concurrent en attente).
- Le sujet "mapping configurable" reste décopé en deux vagues :
  - **16a** : moteur d'override backend + configuration JSON versionnée + table "attendu HA par commande", testable sans UI riche ;
  - **16b** : UI Jeedom de configuration inspirée Homebridge (arbo pièce/équipement/commande), avec l'attendu HA visible et proposition auto.
- Le point icebox "drill-down commande par commande" (`backlog-icebox.md` §1) est **absorbé** dans Story 16.4 (diagnostic override-aware), qui introduit de toute façon la hiérarchie niveau 4 (`pièce -> équipement -> commande`) en lecture seule avant d'y ajouter la capacité d'édition.
- Les overrides sont explicitement à **double granularité** :
  - **Jeedom** : le `generic_type` natif Jeedom n'est jamais modifié par un override HA (pour ne pas casser une config Homebridge fonctionnelle) ;
  - **HA** : une surcharge locale au pipeline jeedom2ha peut mapper une commande vers un type d'entité HA différent de celui déduit du `generic_type` natif, sans jamais réécrire ce `generic_type` dans Jeedom.
- Nouvel AC explicite : pour toute commande, l'UI affiche (a) le `generic_type` Jeedom actuel, (b) ce que HA attend pour le composant visé (source `ha-projection-reference.md`), (c) une proposition automatique si aucun `generic_type` n'est configuré.

### 2.4 Impact technique

| Zone | Impact |
|---|---|
| Backend Python | Loader d'overrides versionnés + couche d'application entre mapping candidat et validation/décision ; nouvelle fonction de résolution "attendu HA par commande" basée sur `ha-projection-reference.yaml`. |
| Modèle de données | Schéma JSON versionné, IDs Jeedom stables (`eqLogic`/`cmd`), champ explicite distinguant override "HA local" (n'écrit jamais le `generic_type` Jeedom) d'un futur override "Jeedom" (hors scope de ce cadrage, non demandé). |
| Diagnostic | Champs additifs `override_*`, plus un champ `ha_expected_generic_type` par commande (lecture seule, dérivé de la référence HA). |
| Tests | Golden corpus, cas nominaux, cas invalides, non-régression 4D, tests de migration schéma, cas "proposition auto" sur commande sans `generic_type`. |
| PHP/Jeedom | 16a se limite à persistance/import/export ; 16b ajoute l'UI native Jeedom (arbo pièce/équipement/commande, inspirée Homebridge). |
| UX | Surface de configuration dédiée, distincte de la home et du diagnostic standard ; affichage combiné "configuré vs attendu" par commande. |

## 3. Path Forward Evaluation

### Option 1 - Direct Adjustment : ajouter `pe-epic-16` maintenant, exécution immédiate

**Statut : recommandée.**

Aucun epic n'est en attente d'exécution (1 à 15 tous `done`), contrairement au cadrage 2026-06-12 où `pe-epic-11` devait passer avant. Le mapping configurable devient donc directement le prochain epic exécutable après approbation.

Effort estimé : moyen à élevé. Risque : moyen si 16a reste backend-first ; élevé si l'UI est lancée trop tôt.

### Option 2 - Réutiliser telle quelle la branche `chore/bmad-scp-epic-12`

**Statut : non recommandée.**

Explicitement interdit par `active-cycle-manifest.md` §9 : le numéro 12 est consommé par un autre epic clos, et le scope ne couvre pas les nouvelles exigences UX (attendu HA visible, proposition auto, double granularité Jeedom/HA).

### Option 3 - Lancer directement une UI complète de mapping configurable

**Statut : non recommandée.**

Le projet n'a pas de CI PHP/front robuste pour une UI riche sans contrat backend stabilisé. Risque support et régression disproportionné, identique au constat de 2026-06-12.

### Option 4 - Traiter le drill-down commande (icebox §1) comme epic séparé du mapping configurable

**Statut : non recommandée.**

Les deux sujets introduisent la même hiérarchie niveau 4 (`pièce -> équipement -> commande`). Les traiter séparément dupliquerait le travail d'architecture frontend. Absorption dans Story 16.4 retenue.

### Selected approach

**Option 1 : Direct Adjustment, exécution immédiate après approbation.**

## 4. Detailed Change Proposals

### 4.1 `epics-projection-engine.md` - Ajouter `pe-epic-16`

**Section :** après le bloc Epic 15 (dernier epic clos du document).

**NEW :**

```md
---

### Epic 16 — Le mapping configurable donne la main à l'utilisateur expert sans casser le pipeline explicable ni la config Homebridge existante

**Valeur utilisateur :** L'utilisateur expert peut corriger ou affiner la projection HA d'une commande Jeedom lorsque le moteur automatique est trop prudent ou incomplet, voir explicitement ce que Home Assistant attend pour que l'entité fonctionne, et appliquer une surcharge HA locale sans jamais modifier le `generic_type` Jeedom natif (pour préserver une configuration Homebridge fonctionnelle en parallèle).

**Résultat observable :** Une couche d'overrides optionnelle, versionnée et réversible s'ajoute au-dessus du pipeline automatique, avec une hiérarchie de configuration pièce -> équipement -> commande inspirée de Homebridge. Pour chaque commande, l'utilisateur voit le `generic_type` Jeedom actuel, l'attendu Home Assistant pour le composant visé, et une proposition automatique si aucun `generic_type` n'est configuré. Aucun override ne publie une projection HA structurellement invalide, et aucun override HA ne réécrit le `generic_type` Jeedom natif.

**FRs couverts :** FR23, FR24, FR25, FR31, FR40, FR44, FR45

**ARs clés :** AR3, AR6, AR11, AR13, D6/D11 à préciser

**NFRs directement adressés :** NFR4, NFR10, NFR11, NFR12

**Absorbe :** `backlog-icebox.md` §1 (drill-down commande par commande) — même hiérarchie niveau 4, traité en lecture seule dans Story 16.4 avant capacité d'édition.

**Invariants à porter en stories :**
- un override ne contourne jamais la validation HA obligatoire ;
- un override HA ne réécrit jamais le `generic_type` Jeedom natif — la surcharge vit au niveau du pipeline jeedom2ha uniquement ;
- la décision native du moteur reste visible dans le diagnostic, avec l'attendu HA affiché par commande ;
- tout override est réversible et traçable (`override_*`) ;
- le schéma d'override est versionné dès la première story ;
- 16a livre un backend testable sans UI riche ;
- 16b ne démarre qu'après stabilisation du contrat backend, et absorbe le drill-down commande en lecture seule avant l'édition.

### Story 16.0 : Préfixe d'architecture — contrat d'override double granularité, points d'injection et limites

En tant que mainteneur,
je veux formaliser les types d'overrides autorisés (dont la distinction override Jeedom vs override HA local), leurs points d'injection dans le pipeline et leurs limites,
afin de garantir que la configuration utilisateur ne casse ni la validation HA, ni le diagnostic, ni une configuration Homebridge existante.

**Acceptance Criteria :**

**Given** le pipeline canonique à 5 étapes
**When** la story est exécutée
**Then** les types d'overrides autorisés sont listés et bornés (éligibilité, candidat mapping, décision, métadata)
**And** un override HA local est explicitement distingué d'une modification du `generic_type` Jeedom natif — cette dernière reste hors scope et interdite
**And** l'interdiction de publier une projection invalide est documentée comme invariant bloquant

**Given** un override de mapping ou de décision
**When** son point d'injection est décrit
**Then** le document d'architecture précise l'ordre d'application par rapport au mapping automatique, à `validate_projection()` et à `decide_publication()`
**And** le format du schéma JSON v1 est tranché ou renvoyé vers une décision explicite de Story 16.1

**Dev notes :**
- story préfixe obligatoire avant toute implémentation 16a
- cite `sprint-change-proposal-2026-07-06-mapping-configurable.md`

---

### Story 16.1 : Persistance backend du schéma d'overrides v1

En tant qu'utilisateur expert,
je veux que mes overrides soient persistants, exportables et associés à des IDs Jeedom stables,
afin de conserver mes choix lors des resyncs, upgrades et renommages.

**Acceptance Criteria :**

**Given** un override valide
**When** il est sauvegardé
**Then** il est stocké selon un schéma JSON v1 documenté, référencé par `eqLogic.id`/`cmd.id`
**And** le schéma ne modifie jamais le `generic_type` Jeedom natif — l'override HA vit dans une structure séparée
**And** le stockage ne crée pas de table SQL custom

**Given** un import ou une migration de schéma
**When** le schéma est invalide ou trop récent
**Then** le backend refuse l'application de l'override avec un diagnostic explicite
**And** aucun publish MQTT n'est déclenché par l'import seul

**Dev notes :**
- 16a backend-first ; l'édition manuelle JSON peut suffire au premier incrément si documentée
- export/import minimal requis avant UI riche

---

### Story 16.2 : Table "attendu Home Assistant par commande" et application backend des overrides de mapping candidat

En tant qu'utilisateur expert,
je veux voir ce que Home Assistant attend pour chaque commande et pouvoir forcer un candidat HA ou mapper explicitement certaines commandes,
afin de résoudre un cas que le moteur automatique ne peut pas inférer correctement, et de comprendre pourquoi.

**Acceptance Criteria :**

**Given** une commande Jeedom, mappée ou non
**When** le backend résout son "attendu HA"
**Then** il expose, en lecture, le(s) composant(s) HA et `generic_type` compatibles pour cette commande, dérivés de `ha-projection-reference.yaml`
**And** si la commande n'a aucun `generic_type` configuré, une proposition automatique est calculée à partir du moteur de mapping existant

**Given** un équipement éligible avec override de mapping
**When** le pipeline exécute l'étape de mapping
**Then** le moteur conserve le candidat natif
**And** applique le candidat surchargé avant validation HA
**And** trace la source `override_*` dans le résultat de diagnostic, sans jamais réécrire le `generic_type` Jeedom natif

**Given** un override qui produit un candidat HA invalide
**When** `validate_projection()` s'exécute
**Then** la validation HA échoue explicitement
**And** la publication reste interdite
**And** la cause indique que l'override est invalide sans masquer la décision native

**Dev notes :**
- golden corpus obligatoire : cas nominal, cas invalide, cas "proposition auto", non-régression sans override
- aucun bypass de `validate_projection()`
- source de vérité pour l'attendu HA = `ha-projection-reference.md`/`.yaml`, jamais une table dupliquée en dur

---

### Story 16.3 : Overrides de publication et exclusion explicite

En tant qu'utilisateur expert,
je veux exclure un équipement ou une commande, ou autoriser une publication dont la projection est valide mais bloquée par une politique produit,
afin de reprendre la main sans confondre ce choix avec une réussite automatique.

**Acceptance Criteria :**

**Given** un équipement ou une commande exclu par override utilisateur
**When** le pipeline évalue l'éligibilité ou la décision
**Then** l'exclusion est prioritaire, lisible et réversible
**And** le diagnostic signale l'origine utilisateur de l'exclusion

**Given** un équipement dont la projection HA est valide mais dont la confiance est faible ou la politique produit bloque la publication
**When** un override autorise la publication
**Then** `projection_validity.is_valid == true` reste une condition obligatoire
**And** la décision finale indique explicitement qu'elle vient d'un override

**Dev notes :**
- "forcer publication" signifie "forcer la décision après validation HA réussie", jamais publier un payload invalide

---

### Story 16.4 : Diagnostic override-aware avec drill-down commande par commande (absorbe backlog-icebox §1)

En tant qu'utilisateur,
je veux déplier un équipement pour voir, commande par commande, le `generic_type` Jeedom actuel, l'attendu Home Assistant, la décision native et l'éventuelle surcharge,
afin de comprendre et maintenir mes choix avec la granularité fine demandée par `backlog-icebox.md` §1.

**Acceptance Criteria :**

**Given** un équipement publié
**When** l'utilisateur déplie le drill-down commande
**Then** il voit, pour chaque commande retenue ou rejetée : le `generic_type` Jeedom, l'attendu HA, et la décision de mapping — en lecture seule pour les commandes non surchargées
**And** ce niveau 4 (`pièce -> équipement -> commande`) ne pollue pas l'Epic 2 (santé du pont) ni ne modifie les statuts Epic 3 (niveau équipement), conformément aux garde-fous `backlog-icebox.md` §1

**Given** un équipement avec override appliqué
**When** l'utilisateur consulte le diagnostic
**Then** il voit la décision native et la décision surchargée
**And** le diagnostic conserve une cause principale canonique
**And** les champs ajoutés sont additifs et compatibles avec le contrat 4D

**Given** un override sans remédiation utilisateur directe
**When** la traduction `cause_label` / `cause_action` est construite
**Then** la règle Epic 6 "no faux CTA" reste appliquée

**Dev notes :**
- centraliser les traductions dans `cause_mapping.py`
- le drill-down reste lecture seule tant que 16b (édition) n'est pas livré
- garde-fous `backlog-icebox.md` §1 à reporter explicitement dans cette story lors de `create-story`

---

### Story 16.5 : UI Jeedom de configuration par équipement, inspirée Homebridge

En tant qu'utilisateur expert,
je veux configurer un override depuis une surface Jeedom dédiée organisée par pièce comme Homebridge, avec l'attendu HA visible par commande,
afin de ne pas modifier le JSON à la main et de savoir quel `generic_type` choisir pour que l'entité fonctionne — ce que Homebridge lui-même ne montre pas.

**Acceptance Criteria :**

**Given** la surface de configuration avancée
**When** l'utilisateur l'ouvre
**Then** elle utilise l'UI native Jeedom sans framework front externe
**And** elle présente une arborescence pièce -> équipement -> commande (reprenant le classement par pièce de Homebridge)
**And** pour chaque commande, elle affiche côte à côte le `generic_type` Jeedom actuel et l'attendu Home Assistant pour le composant visé
**And** pour une commande sans `generic_type`, elle affiche la proposition automatique calculée en Story 16.2
**And** elle permet de revenir au mode automatique par équipement ou par commande

**Given** une modification d'override HA local depuis l'UI
**When** l'utilisateur sauvegarde
**Then** le backend valide le schéma et la projection avant toute application effective
**And** le `generic_type` Jeedom natif n'est jamais modifié par cette action
**And** les erreurs de validation HA sont visibles

**Dev notes :**
- 16b ne démarre qu'après stabilisation du contrat backend 16a
- définir une stratégie de test front minimale avant implémentation
- inspiration Homebridge pour le classement par pièce uniquement — corriger explicitement son défaut identifié (absence de visibilité sur l'attendu HomeKit/HA)

---

### Story 16.6 : Preview / dry-run avant application

En tant qu'utilisateur expert,
je veux prévisualiser l'effet d'un override avant de l'appliquer,
afin d'éviter de polluer Home Assistant avec une configuration approximative.

**Acceptance Criteria :**

**Given** un override en cours d'édition
**When** l'utilisateur demande une preview
**Then** le backend retourne le résultat "auto" et le résultat "avec override"
**And** aucune publication MQTT n'est déclenchée pendant le dry-run
**And** les erreurs de validation HA sont visibles avant sauvegarde

**Given** un export support
**When** un override est impliqué
**Then** l'export inclut les raisons de refus et la trace de preview utile au support

---

### Story 16.7 : Gate terrain et profils partageables

En tant que mainteneur,
je veux valider les overrides sur un corpus terrain et préparer l'export/import de profils,
afin de transformer la configurabilité en avantage marketplace durable, en cohérence avec le classement par pièce hérité de Homebridge.

**Acceptance Criteria :**

**Given** la vague 16a/16b implémentée
**When** le gate terrain est exécuté
**Then** au moins trois familles d'équipements réelles sont validées avec overrides HA locaux, retour auto et diagnostic drill-down commande
**And** le corpus inclut au moins un cas d'override invalide correctement refusé
**And** au moins un cas démontre qu'un override HA n'a pas modifié le `generic_type` Jeedom natif (non-régression Homebridge)

**Given** un profil exporté
**When** il est partagé ou importé
**Then** il est anonymisable et ne contient pas de secret
**And** son format reste compatible avec le schéma versionné

**Dev notes :**
- les profils partageables sont un objectif de croissance ; ne pas bloquer 16a si le partage communautaire est trop large
- documentation utilisateur FR requise avant closeout epic

---

### Gates epic-level pe-epic-16

- Story 16.0 est obligatoire avant toute implémentation d'override.
- Aucun override ne contourne `validate_projection()`.
- Aucun override HA ne modifie le `generic_type` Jeedom natif (non-régression Homebridge garantie).
- Le schéma d'override est versionné dès le premier incrément.
- Le diagnostic conserve la décision native, trace l'override de façon additive, et affiche l'attendu HA par commande.
- 16a backend testable précède 16b UI Jeedom.
- Le mode automatique reste le comportement par défaut.
- Le drill-down commande par commande (`backlog-icebox.md` §1) est livré en lecture seule dans Story 16.4 avant toute capacité d'édition en 16b.
```

**Rationale :** Réutilise le cadrage déjà validé le 2026-06-12 (contenu, invariants, découpage 12a/12b devenu 16a/16b), renuméroté conformément à `active-cycle-manifest.md` §9, et enrichi des AC explicites demandés par Alexandre le 2026-07-06 (attendu HA visible par commande, proposition automatique, double granularité Jeedom/HA, absorption du drill-down icebox).

### 4.2 `sprint-status.yaml` - Proposition d'ajout après approbation

**NEW (section commentaire + development_status) :**

```yaml
#          pe-epic-16 = mapping configurable commande par commande (renumerotation de pe-epic-12,
#                       cadre par sprint-change-proposal-2026-07-06-mapping-configurable.md),
#                       absorbe backlog-icebox.md §1 (drill-down commande), backlog, prochain epic execute
```

```yaml
  pe-epic-16: backlog  # mapping configurable / overrides utilisateur, double granularite Jeedom/HA ; cadre par SCP 2026-07-06 ; absorbe backlog-icebox §1 ; prochain epic execute (1-15 tous done)
```

**Rationale :** Aucun epic concurrent en attente ; `pe-epic-16` devient directement le prochain epic à exécuter, contrairement au cadrage 2026-06-12 qui devait attendre `pe-epic-11`.

### 4.3 `active-cycle-manifest.md` - Proposition d'actualisation

**Section 9 — Prochaine étape BMAD attendue :**

**NEW (paragraphe ajouté) :**

```md
Correct-course du `2026-07-06` : renumérotation du cadrage historique de mapping configurable (`chore/bmad-scp-epic-12`, jamais exécuté) en `pe-epic-16`, avec absorption de `backlog-icebox.md` §1 (drill-down commande par commande) et extension du scope UX (attendu HA visible par commande, proposition automatique, double granularité Jeedom/HA sans modification du `generic_type` natif). Voir `sprint-change-proposal-2026-07-06-mapping-configurable.md`. `pe-epic-16` est le prochain epic exécuté ; aucun epic concurrent n'est en attente (1 à 15 tous `done`).
```

**Section 10 — Résumé ultra court :**

**OLD :**

```md
Les epics `pe-epic-10`, `pe-epic-11` et `pe-epic-12` sont livrés. Aucun prochain epic n'est engagé; le mapping configurable historique doit être renuméroté et recadré depuis `main` avant usage.
```

**NEW :**

```md
Les epics `pe-epic-1` à `pe-epic-15` sont livrés. `pe-epic-16` (mapping configurable commande par commande, renumérotation du cadrage historique `pe-epic-12`) est cadré par le SCP du 2026-07-06 et devient le prochain epic exécuté.
```

**Rationale :** Le manifeste doit refléter que le sujet est désormais cadré sous un numéro valide et prêt pour `create-story`.

### 4.4 `backlog-icebox.md` - Marquage de l'item absorbé

**Section 1 — Drill-down commande par commande :**

**NEW (ligne ajoutée sous le titre) :**

```md
**Statut :** Absorbé par `pe-epic-16` (Story 16.4) depuis le correct-course du 2026-07-06 — voir `sprint-change-proposal-2026-07-06-mapping-configurable.md`. Cet item n'est plus icebox, il est cadré et planifié.
```

**Rationale :** Éviter la confusion entre un item icebox non engagé et un item désormais absorbé dans un epic actif planifié.

## 5. Marketplace Product Adjustments

Repris et complété du cadrage 2026-06-12 :

### 5.1 Ce qui doit être valorisé

- **Onboarding court** : la configurabilité aide à résoudre un cas bloqué, elle ne devient pas une étape obligatoire du premier démarrage.
- **Diagnostic comme argument principal, avec l'attendu HA visible** : expliquer "pourquoi cet équipement n'apparaît pas" et "ce que HA attend pour cette commande" est une force différenciante par rapport à Homebridge, qui ne montre pas l'attendu HomeKit.
- **Preview avant publication** : la confiance vient du dry-run.
- **Retour à l'automatique** : chaque override a un chemin simple de reset, par équipement ou par commande.
- **Non-régression Homebridge garantie** : un override HA ne modifie jamais le `generic_type` Jeedom natif, donc une configuration Homebridge fonctionnelle continue de fonctionner en parallèle.
- **Profils exportables** : effet communautaire possible à terme.

### 5.2 Garde-fous produit

- L'UI ne doit pas transformer le plugin en tableur de commandes incompréhensible.
- Le mode automatique reste le comportement par défaut.
- Les overrides doivent être visibles, réversibles et exportables.
- Le support doit pouvoir demander un export diagnostic incluant les overrides sans fuite de secrets.
- Les profils partageables sont un objectif de croissance, pas une dépendance de 16a.

## 6. Recommendation

Approuver un correct-course **modéré** :

- oui à la matérialisation de `pe-epic-16` (renumérotation du cadrage 2026-06-12) ;
- oui au découpage `16a backend testable` puis `16b UI Jeedom` ;
- oui à l'absorption de `backlog-icebox.md` §1 dans Story 16.4 ;
- oui aux nouveaux AC explicites : attendu HA visible par commande, proposition automatique, double granularité Jeedom/HA ;
- non à toute modification du `generic_type` Jeedom natif par un override HA ;
- non à une UI riche avant schéma backend, validation et diagnostic override-aware ;
- non à tout override qui contourne la validation HA.

## 7. Implementation Handoff

### Scope classification

**Moderate.**

Le changement ne demande pas de rollback ni de redéfinition du MVP, mais il réorganise le backlog futur, absorbe un item icebox, et introduit une capacité sensible touchant backend, diagnostic, persistance PHP et UI.

### Recipients

| Role | Responsabilité |
|---|---|
| Scrum Master | Ajouter l'epic au backlog comme prochain epic exécuté. |
| Product Owner / PM | Valider la promesse utilisateur, les limites marketplace, et l'absorption du drill-down icebox. |
| Architect | Produire Story 16.0 avec points d'injection, schéma v1 double granularité et frontières de validation. |
| Dev | Exécuter 16a backend avec tests et golden corpus avant tout front riche. |
| QA | Définir tests migration, non-régression 4D, non-régression Homebridge, dry-run et gates terrain. |
| UX | Cadrer 16b en UI native Jeedom inspirée Homebridge (classement pièce), en corrigeant explicitement le défaut Homebridge (absence d'attendu HomeKit visible). |

### Success criteria

- `pe-epic-16` apparaît en backlog actif comme prochain epic exécuté.
- Les stories 16a/16b sont séparées et testables.
- Le schéma d'override v1 est versionné avant la première implémentation.
- Aucun override ne publie une projection invalide, aucun override HA ne modifie le `generic_type` Jeedom natif.
- Le diagnostic montre la décision native, la surcharge, et l'attendu HA par commande.
- Le drill-down commande par commande est livré en lecture seule avant toute édition.
- Le mode automatique reste le comportement par défaut.

## 8. Decision Requested

Décision demandée à Alexandre :

- **yes** -> appliquer ce correct-course : mettre à jour `epics-projection-engine.md`, `sprint-status.yaml`, `active-cycle-manifest.md` et `backlog-icebox.md` ;
- **revise** -> garder le principe mais ajuster le découpage, les stories ou le scope UX ;
- **no** -> ne pas matérialiser `pe-epic-16` maintenant.

## 9. Decision

Approved — Alexandre a répondu `GO pour correct-course` le `2026-07-06`.

Actions d'application attendues :

- matérialiser `pe-epic-16` dans `epics-projection-engine.md` ;
- ajouter `pe-epic-16: backlog` dans `sprint-status.yaml` ;
- actualiser `active-cycle-manifest.md` (§9 et §10) pour pointer vers `pe-epic-16` comme prochaine exécution et vers ce SCP comme dernier correct-course ;
- marquer `backlog-icebox.md` §1 comme absorbé par `pe-epic-16`.
