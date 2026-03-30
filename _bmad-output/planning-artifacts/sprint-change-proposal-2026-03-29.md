---
type: sprint-change-proposal
project: jeedom2ha
phase: post_mvp_phase_1
version_label: v1.1_pilotable
date: 2026-03-29
status: approved
approved_by: Alexandre
scope_classification: moderate
trigger: epic-4-retro-2026-03-29
impacts:
  - active-cycle-manifest.md
  - epics-post-mvp-v1-1-pilotable.md
  - test-strategy-post-mvp-v1-1-pilotable.md
  - sprint-status.yaml
  - future-ux-artifact-home-vs-diagnostic
---

# Sprint Change Proposal — Correctif prioritaire Epic 4 avant tout demarrage Epic 5

## 1. Resume du probleme

### Declencheur

Post-retrospective Epic 4 cloturee le 2026-03-29, avec Epic 4 `done` au niveau tracking mais objectif produit UX/UI non atteint en usage reel.

### Probleme fondamental

Epic 4 est **reussi sur le fond mais non encore atterri sur la forme**.

Le socle 4D, les compteurs canoniques, la sortie du vocabulaire legacy et le backend source de verite sont valides et **ne doivent pas etre rouverts**.

Le delta restant porte uniquement sur l'atterrissage produit UX/UI :
- la home ne joue pas encore assez clairement son role de console de synthese et de pilotage ;
- la surface diagnostic n'est pas encore assez recadree comme espace dedie d'explicabilite detaillee, recentre sur le perimetre ;
- la separation percue entre les surfaces reste insuffisante.

### Preuves concretes

| Constat | Impact |
|---|---|
| Home pas encore percue comme surface de synthese/pilotage dominante | La valeur produit de pilotage reste partiellement sous-delivree |
| Diagnostic encore trop proche de la home dans la perception utilisateur | Frontiere entre surfaces insuffisamment lisible |
| Validation structurelle suffisante mais preuve terrain UX insuffisamment bloquante | Risque de valider une conformite sans atterrissage reel |
| Absence d'artefact visuel prescriptif et testable | Review et terrain laissent trop de place a l'interpretation |

### Categorie

Failed approach requiring different solution, sans remise en cause du fond technique : le plan doit etre reroute vers un **correctif prioritaire Epic 4** borne, distinct d'Epic 5, demarrant par un artefact visuel prescriptif et testable.

---

## 2. Analyse d'impact

### 2.1 Impact epics

| Epic | Statut | Impact du reroutage |
|---|---|---|
| **Epic 4** | done au tracking, non atterri produit | Ouvre un chantier correctif prioritaire borne, sans rouvrir le socle 4D ni recreer tout l'epic |
| **Epic 5** | backlog | **Gele explicitement** jusqu'a validation terrain du correctif prioritaire Epic 4 |

### 2.2 Impact artefacts

| Artefact | Niveau d'impact | Changement attendu |
|---|---|---|
| `epics-post-mvp-v1-1-pilotable.md` | Significatif | Formaliser le chantier correctif prioritaire Epic 4, geler Epic 5, mettre a jour le chemin critique et la prochaine etape |
| `test-strategy-post-mvp-v1-1-pilotable.md` | Modere | Ajouter le gate terrain bloquant et la nouvelle regle de methode pour les stories de surface principale |
| `sprint-status.yaml` | Modere | Rendre visible le gel d'Epic 5 et le prerequis correctif Epic 4 sans creer de stories de dev |
| `active-cycle-manifest.md` | Faible | Pas de changement de source de verite active requis a ce stade |
| PRD / UX delta / Architecture delta | Faible | Les fondamentaux restent valides ; pas de reouverture du fond demandee par ce correct-course |

### 2.3 Impact technique

Pas de reouverture technique de fond :
1. le modele 4D reste la base canonique ;
2. les compteurs backend restent la source de verite ;
3. la sortie du vocabulaire legacy reste acquise ;
4. le backend reste la source unique de verite ;
5. le correctif porte sur la responsabilite perceptive des surfaces, pas sur le socle technique.

---

## 3. Approche recommandee

### Chemin retenu : Direct Adjustment borne avec gate de methode

Le reroutage retenu est un **ajustement direct de plan**, pas un rollback et pas une revue du MVP.

Justification :
1. le probleme est reel mais borne a l'atterrissage UX/UI ;
2. le socle Epic 4 doit etre preserve, pas remixe ;
3. Epic 5 n'est pas invalide sur le fond, mais son demarrage maintenant creerait un faux sentiment d'avancement ;
4. le bon premier livrable n'est pas une story de dev mais un **artefact visuel prescriptif et testable** ;
5. la suite doit rester strictement separee : artefact visuel -> stories correctives bornees -> implementation -> gate terrain -> reevaluation Epic 5.

### Alternatives ecartees

| Alternative | Raison d'ecart |
|---|---|
| Demarrer Epic 5 maintenant | Non viable tant que la cible produit Epic 4 n'est pas restauree |
| Rouvrir le fond technique Epic 4 | Hors scope ; le socle 4D et backend ne sont pas en cause |
| Creer immediatement des stories correctives | Trop tot sans artefact visuel prescriptif validant la repartition home vs diagnostic |
| Lancer une extension fonctionnelle ou un chantier mixte | Interdit ; ce correctif doit rester distinct de toute extension |

---

## 4. Chantier correctif prioritaire Epic 4

### Formulation precise

**Nom recommande :** Correctif prioritaire Epic 4 — restauration de la cible UX/UI home vs diagnostic

**Objectif :** restaurer la cible UX/UI attendue.

**Cible produit :**
- **home = console de synthese et de pilotage**
- **diagnostic = surface dediee d'explicabilite detaillee, recentree sur le perimetre**

**Hors scope :**
- ne pas rouvrir le modele 4D ;
- ne pas rouvrir les compteurs backend ;
- ne pas rouvrir la sortie du vocabulaire legacy ;
- ne pas lancer Epic 5.

**Premier livrable bloquant :**
- un **artefact visuel prescriptif et testable** ;
- definissant :
  - le message dominant de la home ;
  - le message dominant du diagnostic ;
  - ce qui est absent par design ;
  - ce qui est non duplicable entre les surfaces.

### Action items integres

| Action item | Integration dans le plan |
|---|---|
| **AI-1** | Le premier livrable obligatoire devient l'artefact visuel prescriptif et testable home vs diagnostic |
| **AI-2** | Le paquet de stories correctives Epic 4 ne pourra etre derive qu'apres validation de cet artefact |
| **AI-3** | Le correctif Epic 4 portera un gate terrain bloquant avant `done` |
| **AI-4** | La methode future impose artefact visuel + review orientee responsabilite des surfaces + validation terrain pour toute story touchant une surface principale |

---

## 5. Propositions de changement par artefact

### 5.1 Epics (`epics-post-mvp-v1-1-pilotable.md`)

**OLD**
- Epic 5 est le prochain chantier backlog apres Epic 4.
- Prochaine etape recommandee : `sprint-planning`, puis `create-story` pour 4.1 a 4.4.

**NEW**
- Epic 5 reste backlog **et gele**.
- Le prochain chantier n'est pas Epic 5 mais un **correctif prioritaire Epic 4**.
- Le premier livrable de ce chantier est un **artefact visuel prescriptif et testable home vs diagnostic**.
- Aucune story corrective de dev n'est ouverte avant validation de cet artefact.
- Prochaine etape recommandee : `bmad-create-ux-design`.

**Rationale**
- Le reroutage est de nature epic-level / plan-level, pas story-level.

### 5.2 Test strategy (`test-strategy-post-mvp-v1-1-pilotable.md`)

**OLD**
- Les stories Epic 4 et Epic 5 sont adressees selon le plan precedent.

**NEW**
- Toute story corrective Epic 4 est bloquee tant que l'artefact visuel prescriptif home vs diagnostic n'est pas valide.
- Toute correction touchant une surface principale porte un **gate terrain bloquant avant `done`**.
- La methode future exige, pour toute story de surface principale ou de redistribution de responsabilite entre surfaces :
  - artefact visuel prescriptif,
  - review orientee responsabilite des surfaces,
  - validation terrain adaptee.

**Rationale**
- Transformer l'apprentissage de la retro en garde-fou durable.

### 5.3 Sprint status (`sprint-status.yaml`)

**OLD**
- Epic 5 est backlog, sans gel explicite au niveau commentaire de plan.

**NEW**
- Epic 5 reste backlog **et gele** jusqu'au correctif prioritaire Epic 4 valide en terrain.
- Le statut actif rappelle explicitement :
  - livrable 0 = artefact visuel prescriptif home vs diagnostic ;
  - aucune story corrective avant validation de cet artefact ;
  - gate terrain bloquant avant `done`.

**Rationale**
- Officialiser le reroutage sans creer artificiellement de nouvelles stories ni modifier le fond technique.

---

## 6. Chemin critique mis a jour

1. Geler explicitement Epic 5.
2. Lancer `bmad-create-ux-design` pour produire l'artefact visuel prescriptif home vs diagnostic.
3. Valider cet artefact comme reference de responsabilite des surfaces.
4. Deriver ensuite un paquet de stories correctives Epic 4 strictement borne.
5. Implementer le correctif avec review orientee responsabilite des surfaces.
6. Passer un gate terrain bloquant avant `done`.
7. Reevaluer seulement ensuite le demarrage d'Epic 5.

---

## 7. Handoff et prochaine etape

### Classification

**Modere**

Le changement demande une reorganisation de plan et de methode, mais pas de refonte technique de fond.

### Handoff

| Responsabilite | Role / workflow |
|---|---|
| Officialiser le reroutage | Scrum Master / correct-course |
| Produire l'artefact visuel prescriptif | UX / workflow `bmad-create-ux-design` |
| Deriver ensuite le paquet correctif borne | PO + SM |
| Verifier le gate terrain | QA + SM |
| Appliquer la nouvelle regle de methode | SM / validate-story / create-story futurs |

### Prochaine etape recommandee

**`bmad-create-ux-design`** pour produire l'artefact visuel prescriptif home vs diagnostic.

---

## 8. Decision finale

Decision approuvee :
- Epic 5 reste **gele** ;
- un **chantier correctif prioritaire Epic 4** est ouvert, clairement separe d'Epic 5 ;
- son premier livrable obligatoire est un **artefact visuel prescriptif et testable** ;
- aucune story corrective de dev n'est ouverte avant validation de cet artefact ;
- le correctif portera un **gate terrain bloquant avant `done`** ;
- la methode future est renforcee pour les stories touchant une surface principale ou redistribuant la responsabilite entre surfaces.
