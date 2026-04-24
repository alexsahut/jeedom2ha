---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-04-21
status: approved
approved_by: Alexandre
scope_classification: moderate
trigger: story-6.2-terrain-no-go-2026-04-21
impacts:
  - _bmad-output/implementation-artifacts/6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger.md
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - future-story-6.3-file
---

# Sprint Change Proposal - NO-GO terrain Story 6.2

## 1. Issue Summary

### Trigger

Gate terrain reel de la Story 6.2 conclu en **NO-GO** le 2026-04-21.

### Problem statement

Le probleme revele n'est **pas** un bug du moteur de projection ni un simple manque de polish.

Le probleme est un **defaut de sequencement et d'appropriation semantique** :

1. le plan epic d'origine separait :
   - **6.2** = enrichissement additif du contrat (`projection_validity`) ;
   - **6.3** = semantique stable `cause_label` / `cause_action`, avec action uniquement si elle existe reellement ;
2. la story 6.2 effectivement creee a **anticipe** la promesse de 6.3 tout en s'interdisant explicitement de rouvrir `projection_validity` ;
3. le terrain a ensuite evalue 6.2 sur un critere d'**actionnabilite honnete** qu'elle n'avait pas, seule, le bon perimetre pour satisfaire proprement.

### Evidence

| Cas terrain | Constat | Lecture de fond |
|---|---|---|
| Step 3 | Cause non claire, action non comprise, comprehension > 60 s | Echec de semantique ET absence de support structurel suffisant pour expliquer proprement l'invalidite |
| Step 4 | Decision percue, mais action floue | Faux CTA ou action non suffisamment prouvable dans les surfaces reelles |
| Step 2 | Lecture rapide mais incoherence percue avec la promesse d'ouverture large | Le discours visible melange encore fermeture produit, absence de mapping et ouverture gouvernee |

### Category

**Failed approach requiring different sequencing**, sans remise en cause du pipeline canonique ni du cadrage PRD/architecture de fond.

---

## 2. Impact Analysis

### 2.1 Impact on Epic 6

Epic 6 reste **valide sur le fond**.

Ce que le NO-GO invalide :
- la tentative de faire porter a la story 6.2 actuelle une promesse complete de `cause_label` / `cause_action` honnêtes sur steps 2/3/4 ;
- le sequencing pratique qui a devance 6.3 sans restaurer le support structurel initialement attendu de 6.2.

Ce que le NO-GO n'invalide pas :
- le PRD du cycle moteur de projection explicable ;
- l'architecture du pipeline a 5 etapes ;
- la separation `reason_code` / `cause_code` ;
- la gouvernance d'ouverture FR39/FR40.

### 2.2 Artifact conflicts

| Artefact | Niveau d'impact | Conflit / besoin |
|---|---|---|
| Story 6.2 actuelle | Significatif | Porte des engagements de semantique/action trop proches de 6.3 tout en excluant `projection_validity` |
| `epics-projection-engine.md` | Modere | Le decoupage original 6.2 / 6.3 est plus juste que l'execution re-priorisee du 2026-04-21 |
| `sprint-status.yaml` | Modere | Le tracker doit refléter une correction de sequencement, pas un faux avancement vers `done` |
| PRD / architecture / pipeline contract | Faible | Pas de correction de fond requise ; ils servent au contraire de reference opposable |

### 2.3 Technical impact

1. Ne pas rouvrir le moteur backend 1 -> 5.
2. Ne pas traiter le NO-GO comme une preuve que "le code manque" uniquement.
3. Considerer l'implementation 6.2 actuelle comme **prototype exploratoire utile**, pas comme preuve que le bon contrat story-level a ete atteint.
4. Geler toute tentative de closeout 6.2 tant que le sequencing n'est pas reclarifie.

---

## 3. Recommended Approach

### Selected path

**Option 2 - Re-sequencer 6.2 et 6.3**

### Why this is the right option

Le NO-GO revele bien :
- un probleme de wording ;
- un probleme de faux CTA / action non reellement disponible ;
- un probleme de discours visible sur l'ouverture du scope ;

mais il **ne revele pas encore** un trou de cadrage produit fondamental dans le PRD.

Le modele attendu existe deja dans les artefacts de reference :
- le PRD demande un diagnostic explicable et actionnable, avec action seulement quand une remediation utilisateur existe reellement ;
- l'epic plan original faisait porter a 6.3 la semantique `cause_label` / `cause_action` honnete ;
- l'architecture separe bien cause canonique, invalidite HA, gouvernance d'ouverture et resultat technique.

Le trou observe est donc d'abord un **mauvais sequencing story-level**, pas un besoin de replan complet.

### Alternatives rejected

| Option | Decision | Why rejected |
|---|---|---|
| Option 1 - Continuer 6.2 par correctif cible | Non retenue | Trop reducteur : le probleme n'est pas seulement le texte, mais la place meme de la promesse `cause_action` dans le sequencing |
| Option 3 - Ouvrir une vraie correction de cadrage produit | Non retenue a ce stade | Le PRD et l'architecture decrivent deja le bon modele ; rien ne prouve encore un manque de cadrage de fond |

### Effort / risk

| Axe | Niveau | Commentaire |
|---|---|---|
| Effort | Medium | Rebaseliner 6.2, avancer 6.3, reajuster le tracker et les gates |
| Risque | Medium | Risque principal = continuer a coder sur une mauvaise decoupe et empiler les faux CTA |
| Impact planning | Faible a modere | Un tour de clarification maintenant evite une double dette produit + UX ensuite |

---

## 4. Detailed Change Proposals

### 4.1 Story 6.2 - restore the right responsibility

**Artifact:** `_bmad-output/implementation-artifacts/6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger.md`

**OLD**
- Story 6.2 presentee comme amelioration UX pure de `cause_label` / `cause_action`
- `projection_validity` explicitement hors scope
- gate terrain evalue la comprehension et l'actionnabilite honnete sur steps 2/3/4

**NEW**
- Rebaseliner 6.2 d'abord sur sa **promesse story-level** :
  - consigner explicitement que le gate terrain 2026-04-21 est **NO-GO** ;
  - conserver la story `in-progress` ;
  - retirer l'idee qu'un simple correctif de wording dans 6.2 suffira a solder la semantique honnete `cause_label` / `cause_action`
- Rappeler que la responsabilite structurelle initiale de 6.2 dans l'epic plan reste liee a `projection_validity`, **sans** rouvrir maintenant un gros chantier opportuniste dans cette story pour la "sauver"
- Limiter l'execution immediate a un realignement documentaire et de sequencing ; aucun dev additionnel n'est lance depuis 6.2 tant que 6.3 n'est pas preparee
- Transformer le NO-GO du 2026-04-21 en preuve qu'une 6.2 "UX pure cause/action" etait mal sequencee
- Conserver la story `in-progress` jusqu'a reappariement de son contrat, sans la cloturer

**Rationale**
- Le besoin immediat approuve n'est pas de relancer un gros sous-chantier `projection_validity`, mais de realigner la promesse et de remettre 6.3 a la bonne place
- Step 3 ne peut pas devenir franchement lisible si la semantique honnete est traitee comme un simple patch cosmetique

### 4.2 Story 6.3 - pull forward the semantic contract actually needed by terrain

**Artifact:** `epics-projection-engine.md` puis future story file 6.3

**OLD**
- 6.3 backlog, apres une 6.2 supposee resoudre deja la clarification terrain cause/action

**NEW**
- Faire de 6.3 la **prochaine story requise** apres rebaselining documentaire de 6.2
- Etendre explicitement 6.3 avec les apprentissages terrain du NO-GO :
  - Step 2 : le libelle ne doit pas laisser croire a une fermeture arbitraire du produit quand le probleme releve en realite du mapping
  - Step 3 : `cause_label` doit expliquer l'invalidite HA ; `cause_action` doit etre nulle ou explicitement non directe si l'utilisateur ne peut pas corriger reellement
  - Step 4 : aucun CTA du type "choisir manuellement le type d'equipement" ne doit survivre sans surface reelle et prouvee
  - Gate terrain obligatoire : comprehension step 2/3/4 + absence de faux CTA

**Rationale**
- C'est exactement le contrat de 6.3 dans l'epic plan : `cause_label` toujours renseigne, `cause_action` seulement si remediation utilisateur reelle

### 4.3 Epic plan - add an execution note to prevent the same drift

**Artifact:** `_bmad-output/planning-artifacts/epics-projection-engine.md`

**OLD**
- Le decoupage 6.2 / 6.3 existe, mais rien n'explicite assez fortement qu'on ne doit pas avancer la semantique d'action avant son support structurel et son gate d'honnetete

**NEW**
- Ajouter une note d'execution sous Epic 6 :
  - ne pas tirer `cause_action` en amont d'une story tant que la remediation utilisateur n'est pas prouvable ;
  - toute story qui modifie `cause_label` / `cause_action` sur surface critique doit etre gatee par "no faux CTA" ;
  - toute re-priorisation locale doit respecter la frontiere : **structure diagnostic avant promesse d'action**.

**Rationale**
- Transformer le NO-GO en garde-fou de methode durable

### 4.4 Sprint status - reflect the sequencing correction, not a false near-done

**Artifact:** `_bmad-output/implementation-artifacts/sprint-status.yaml`

**OLD**
- `6.2: in-progress`
- `6.3: backlog`

**NEW**
- `6.2` reste `in-progress`, avec commentaire explicite :
  - NO-GO terrain du 2026-04-21
  - correct-course approuve
  - rebaselining du contrat story-level requis avant closeout
- `6.3` reste `backlog` tant que le correct-course n'est pas approuve et que la story n'est pas regeneree
- apres approbation :
  - `6.3` devient la prochaine story a creer / preparer

**Rationale**
- Le tracker doit documenter une correction de sequencing, pas laisser croire qu'un micro-fix suffira a faire passer 6.2 en `done`

---

## 5. Implementation Handoff

### Scope classification

**Moderate**

Il faut une reorganisation story-level et tracker-level, mais pas de replan produit fondamental.

### Handoff recipients

| Responsabilite | Role / workflow |
|---|---|
| Approuver le correct-course | User / porteur |
| Rebaseliner 6.2 et consigner la decision | Scrum Master |
| Realigner l'epic plan et le tracker | Scrum Master / Product Owner |
| Creer la vraie story 6.3 pour execution | Scrum Master via `bmad-create-story` |
| N'engager le dev qu'apres validation story-level | Dev team |

### Success criteria

1. 6.2 n'est pas cloturee.
2. 6.3 n'est pas demarree sans decision explicite.
3. Le tracker explique le NO-GO et le resequencement.
4. La prochaine story executable porte explicitement la regle : **pas de faux CTA**.
5. Aucun dev supplementaire n'est lance avant alignement des artefacts.

---

## 6. Checklist Summary

| Item | Status | Note |
|---|---|---|
| 1.1 Trigger story identified | [x] Done | Story 6.2, gate terrain NO-GO |
| 1.2 Core problem defined | [x] Done | Mauvais sequencing, pas simple manque de code |
| 1.3 Evidence gathered | [x] Done | Step 2 / 3 / 4 terrain fournis |
| 2.1 Current epic assessed | [x] Done | Epic 6 valide, story split derive |
| 2.2 Epic-level changes determined | [x] Done | Note de sequencing reintroduite dans l'epic plan |
| 2.3 Future epics reviewed | [x] Done | Impact borne a Epic 6 |
| 2.4 New epic needed | [N/A] Skip | Pas de nouvel epic requis |
| 2.5 Order / priority change | [x] Done | 6.3 doit passer devant la promesse actuelle de 6.2 |
| 3.1 PRD conflict check | [x] Done | Pas de conflit de fond PRD |
| 3.2 Architecture conflict check | [x] Done | Pas de conflit de fond architecture |
| 3.3 UX conflict check | [x] Done | Conflit de traduction / gate d'honnetete |
| 3.4 Other artifacts impact | [x] Done | Tracker + epic plan + story files |
| 4.1 Option 1 direct adjustment | [ ] Not viable | Trop etroit |
| 4.2 Option 2 resequencing | [x] Viable | Recommande |
| 4.3 Option 3 PRD MVP review | [ ] Not viable | Pas justifie a ce stade |
| 4.4 Recommended path selected | [x] Done | Option 2 |
| 5.1 Issue summary created | [x] Done | Voir section 1 |
| 5.2 Impact documented | [x] Done | Voir section 2 |
| 5.3 Recommended path documented | [x] Done | Voir section 3 |
| 5.4 High-level action plan defined | [x] Done | Voir sections 4 et 5 |
| 5.5 Handoff plan established | [x] Done | Voir section 5 |
| 6.1 Checklist reviewed | [x] Done | Complet |
| 6.2 Proposal accuracy reviewed | [x] Done | Cohérent avec PRD / archi / epic plan |
| 6.3 User approval | [x] Done | Approbation explicite recue le 2026-04-21 avec nuance d'execution |
| 6.4 Sprint status update | [x] Done | Tracker et artefacts de sequencing realignes apres approbation |

---

## 7. Final Decision

Decision approuvee :
- **Option 2 retenue : re-sequencer 6.2 et 6.3**
- ne pas traiter le NO-GO comme "juste un wording"
- ne pas reouvrir le moteur
- ne pas clore 6.2
- ne pas rouvrir inutilement un gros chantier `projection_validity` dans 6.2
- ne pas lancer du dev additionnel tant que le correct-course n'est pas approuve et applique aux artefacts
