---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-04-22
status: approved
scope_classification: moderate
approved_by: Alexandre
approved_on: 2026-04-22
trigger: rehome-story-6-2-to-pe-epic-7
impacts:
  - _bmad-output/implementation-artifacts/6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger.md
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/planning-artifacts/active-cycle-manifest.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - future-pe-epic-7-story-files
---

# Sprint Change Proposal - Re-homing de la Story 6.2 vers pe-epic-7

## 1. Issue Summary

### Trigger

La rétrospective partielle `pe-epic-6` clôturée le **2026-04-22** confirme que l'epic 6 est sain sur ses fondations mais explicitement incomplet, car `6.2` a porté trop tôt une promesse de diagnostic actionnable sans capacité produit correspondante.

### Problem statement

Le problème identifié n'est :

- ni un bug du moteur de projection ;
- ni un défaut du PRD ;
- ni un manque de robustesse de l'architecture ;
- ni un simple sujet de wording UX.

Le problème est un **défaut de sequencing et de responsabilité story-level** :

1. l'intention planifiée de `6.2` dans `epics-projection-engine.md` était l'ajout additif de `projection_validity` au contrat 4D ;
2. la story `6.2` effectivement exécutée a dérivé vers une amélioration UX de `cause_label` / `cause_action` ;
3. le terrain a évalué cette story sur le critère d'actionnabilité réelle, ce qui a révélé une absence de capacité produit — pas un manque de polish ;
4. la story `6.3` a correctement réparé la sémantique honnête et supprimé les faux CTA, sans pour autant construire la capacité produit manquante ;
5. les artefacts BMAD actifs sont désormais désalignés :
   - `sprint-status.yaml` suit le cycle `Moteur de projection explicable` ;
   - `active-cycle-manifest.md` pointe encore vers les artefacts `V1.1 Pilotable`.

### Evidence

| Evidence | Constat | Lecture |
|---|---|---|
| `_bmad-output/implementation-artifacts/pe-epic-6-retro-2026-04-22.md` | "L'actionnabilité n'est pas une couche UX. C'est une capacité produit." | La capacité manquante doit être traitée dans un epic produit dédié |
| `_bmad-output/implementation-artifacts/6-2-...md` | Story exécutée comme enrichissement UX pur | La responsabilité story-level ne correspond plus à l'intention structurelle initiale |
| `_bmad-output/implementation-artifacts/6-3-...md` | `6.3` rétablit la règle `no faux CTA` et laisse `6.2` ouverte | La sémantique honnête est corrigée, la capacité produit ne l'est pas |
| `resources/daemon/tests/unit/test_story_6_3_honest_cause_mapping.py` | `cause_action = None` si aucune remédiation réelle | Le contrat honnête existe déjà et ne doit pas être rouvert |
| `resources/daemon/tests/unit/test_step3_governance_fr40.py` | FR40 / NFR10 déjà verrouillés en CI | Le futur epic doit s'appuyer sur ces gates au lieu de les réinventer |
| `_bmad-output/planning-artifacts/active-cycle-manifest.md` | Sources actives encore positionnées sur `V1.1 Pilotable` | Les sources de vérité BMAD sont à réaligner |

### Category

**Failed approach requiring different sequencing**, avec conflit d'artefacts actifs.  
Le bon traitement n'est pas de "finir 6.2", mais de **re-homer la capacité non construite vers un nouvel epic produit**.

---

## 2. Impact Analysis

### 2.1 Impact on Epic 6

`pe-epic-6` reste **valide sur le fond** :

- `6.1` a livré l'explicabilité par étape ;
- `6.3` a livré la sémantique honnête et la règle `no faux CTA` ;
- les invariants moteur, I4 / I7, et la séparation décision / technique sont restés sains.

Ce qui ne peut **pas** être maintenu :

- l'idée que `6.2` puisse encore être clôturée honnêtement dans `pe-epic-6` par une reprise locale ;
- l'idée que l'actionnabilité réelle soit atteignable dans Epic 6 sans ouverture produit supplémentaire.

**Conclusion :** `pe-epic-6` peut être clôturé proprement **uniquement si** `6.2` est retirée du périmètre exécutable de l'epic et re-homée vers `pe-epic-7`.

### 2.2 Required epic-level changes

Les changements epic-level requis sont :

1. **Clore proprement Epic 6** sur sa valeur réellement livrée : explicabilité + sémantique honnête.
2. **Ajouter un nouvel Epic 7** dédié à la capacité produit, pas à l'UX.
3. **Transformer l'intention non livrée de 6.2** en première capacité d'Epic 7.
4. **Rendre explicite dans le plan d'epics** que l'exposition d'une action utilisateur dépend :
   - d'une surface produit réelle ;
   - d'une ouverture gouvernée du périmètre HA ;
   - des preuves FR40 / NFR10 dans le même incrément.

### 2.3 Remaining epic review

Le cycle `Moteur de projection explicable` ne contient actuellement **aucun epic au-delà de 6** dans `epics-projection-engine.md`.

Impact sur les artefacts futurs :

- aucun epic existant n'est invalidé ;
- un **nouvel epic** est nécessaire pour absorber la capacité non construite ;
- le cycle actif doit être réaligné officiellement sur les artefacts du moteur de projection, et non plus sur ceux de `V1.1 Pilotable`.

### 2.4 New epic requirement

**Oui, un nouvel epic est requis.**

Sans `pe-epic-7` :

- `6.2` reste une story pendante sans destination ;
- le tracker reflète une incomplétude mais le plan d'epics ne fournit aucun conteneur pour la résoudre ;
- le prochain changement risque de repartir depuis un storytelling UX au lieu d'un contrat produit.

### 2.5 Order / priority changes

L'ordre recommandé devient :

1. realigner les sources de vérité BMAD sur le cycle `Moteur de projection explicable` ;
2. retirer `6.2` du périmètre exécutable de `pe-epic-6` ;
3. ajouter `pe-epic-7` comme **prochain epic requis** ;
4. préparer `7.1` avant tout nouveau dev.

Le point `M3` de la story `6.3` reste un follow-up rétro Epic 6, **mais n'est pas un prérequis bloquant** pour lancer `pe-epic-7`.

---

## 3. Artifact Conflict and Impact Analysis

### 3.1 PRD

**Aucun conflit de fond PRD.**

Le PRD du cycle moteur de projection explicable couvre déjà :

- l'action proposée uniquement lorsqu'une remédiation utilisateur existe (FR32) ;
- l'explicitation des cas non actionnables (FR33) ;
- l'ouverture gouvernée des composants HA (FR39, FR40) ;
- NFR10 comme invariant d'ouverture dans le même incrément.

**Décision :** pas de modification PRD requise.

### 3.2 Architecture

**Aucun conflit d'architecture.**

`architecture-projection-engine.md` porte déjà le modèle nécessaire :

- registre HA séparé ;
- états `connu -> validable -> ouvert` ;
- `PRODUCT_SCOPE` gouverné ;
- AR13 / FR40 comme verrou d'ouverture ;
- conservation du contrat 4D.

**Décision :** pas de modification d'architecture requise.

### 3.3 UI / UX

**Pas de nouvelle correction UX structurante requise au niveau cycle.**

La règle UX utile est déjà tranchée :

- pas de faux CTA ;
- pas de promesse d'action sans surface réelle ;
- gate terrain obligatoire si une surface critique `cause_label` / `cause_action` bouge.

**Décision :** pas de nouvelle révision UX de cadrage ; la contrainte reste portée story-level dans Epic 7.

### 3.4 Other artifacts impacted

| Artefact | Impact | Changement requis |
|---|---|---|
| `_bmad-output/planning-artifacts/active-cycle-manifest.md` | Critique | réaligner les sources de vérité sur le cycle `Moteur de projection explicable` |
| `_bmad-output/planning-artifacts/epics-projection-engine.md` | Critique | clore proprement Epic 6 et ajouter Epic 7 |
| `_bmad-output/implementation-artifacts/6-2-...md` | Significatif | transformer la story en artefact historique re-homé, non exécutable |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Critique après approbation | retirer `6.2` du périmètre actif d'Epic 6, ajouter `pe-epic-7` |
| futurs story files `7.x` | Requis après approbation | créer les nouvelles stories d'Epic 7 dans le bon ordre |

---

## 4. Path Forward Evaluation

### Option 1 - Direct Adjustment

**Statut : Not viable**

Pourquoi :

- modifier `6.2` dans son epic actuel ne suffit pas ;
- le problème dépasse une story isolée et touche la structure epic-level ;
- il faut ajouter un nouveau conteneur de capacité produit.

**Effort :** Medium  
**Risk :** High si tenté seul

### Option 2 - Potential Rollback

**Statut : Not viable**

Pourquoi :

- rollback de `6.3` réintroduirait les faux CTA et détruirait une correction valide ;
- aucune simplification durable n'en résulterait ;
- la dette n'est pas dans le code livré de `6.3`, mais dans le sequencing produit.

**Effort :** High  
**Risk :** High

### Option 3 - PRD MVP Review

**Statut : Not viable**

Pourquoi :

- le PRD du cycle moteur est déjà correct ;
- l'objectif produit ne doit pas être réduit ;
- aucune redéfinition de MVP n'est nécessaire.

**Effort :** High  
**Risk :** Medium

### Selected path

**Approche retenue : Hybrid**

Description :

- réalignement des artefacts actifs ;
- clôture propre d'Epic 6 par retrait du faux résidu exécutable `6.2` ;
- création d'un nouvel Epic 7 centré sur la capacité produit ;
- aucun rollback ;
- aucune réécriture PRD / architecture.

### Rationale

Cette approche :

- préserve la valeur déjà livrée par Epic 6 ;
- évite de retransformer la dette en chantier UX ;
- garde l'équipe dans une logique BMAD de stories pilotables et testables ;
- s'appuie sur les gates déjà implémentés (`FR40`, `NFR10`, `no faux CTA`) ;
- crée un chemin propre vers une actionnabilité réelle, pas simulée.

---

## 5. Detailed Change Proposals

### 5.1 Story 6.2 - la transformer en artefact historique re-homé

**Artifact:** `_bmad-output/implementation-artifacts/6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger.md`

**Section:** header / contexte d'exécution

**OLD**

```md
Status: in-progress

Epic: `pe-epic-6` - Le diagnostic est explicable et actionnable
```

**NEW**

```md
Status: historical-artifact-rehomed

Epic d'origine: `pe-epic-6` - Le diagnostic est explicable et actionnable
Disposition BMAD: story re-homee vers `pe-epic-7`

## Correct-course 2026-04-22 - Disposition opposable

- Cette story n'est plus un item executable du backlog actif.
- Le NO-GO terrain du 2026-04-21 a montre que sa promesse story-level ne pouvait pas etre tenue honnetement dans `pe-epic-6`.
- Aucun developpement supplementaire ne doit repartir depuis ce fichier.
- La capacite non construite est re-homee vers `pe-epic-7`, a commencer par une story additive portant `projection_validity` et les preconditions d'actionnabilite reelle.
- Ce fichier reste conserve comme artefact historique d'un sequencing invalide, pas comme source de travail.
```

**Rationale**

Préserver la trace historique sans laisser croire que `6.2` reste une story exécutable.

### 5.2 Epic 6 - expliciter la clôture propre et le re-homing

**Artifact:** `_bmad-output/planning-artifacts/epics-projection-engine.md`

**Section:** `Story 6.2` / fin de `Epic 6`

**OLD**

```md
- Execution note (correct-course 2026-04-21) : si un gate terrain revele avant 6.3 un echec de semantique honnete `cause_label` / `cause_action`, ne pas transformer 6.2 en gros chantier de rattrapage `projection_validity`. Re-aligner d'abord la promesse story-level, garder 6.2 ouverte, puis faire de 6.3 la prochaine story requise.
```

**NEW**

```md
- Execution note (correct-course 2026-04-21) : si un gate terrain revele avant 6.3 un echec de semantique honnete `cause_label` / `cause_action`, ne pas transformer 6.2 en gros chantier de rattrapage `projection_validity`. Re-aligner d'abord la promesse story-level, garder 6.2 ouverte, puis faire de 6.3 la prochaine story requise.
- Disposition post-retro 2026-04-22 : l'intention structurelle non livree de 6.2 n'est plus executee dans Epic 6. Elle est re-homee vers `pe-epic-7`. Epic 6 se clot sur l'explicabilite par etape et la semantique honnete ; aucune reprise de developpement ne repart de 6.2.
```

**Rationale**

Empêcher tout faux retour en arrière sur Epic 6 et documenter la fermeture propre.

### 5.3 Epic 7 - ajouter un conteneur produit explicite

**Artifact:** `_bmad-output/planning-artifacts/epics-projection-engine.md`

**Section:** nouvelle section après `Epic 6`

**OLD**

```md
## Epic 6 — Le diagnostic est explicable et actionnable pour chaque équipement
...
### Story 6.3 ...
```

**NEW**

```md
## Epic 7 — L'actionnabilite devient une capacite produit reelle par ouverture gouvernee du perimetre HA

L'utilisateur ne voit une action que lorsqu'elle repose sur une surface produit reellement ouverte, supportee et testee. Le mainteneur ouvre progressivement le perimetre HA selon FR40 / NFR10, expose `projection_validity` de facon additive, puis n'autorise des CTA utilisateur que pour les remediations effectivement disponibles.

### Story 7.1 : Enrichissement additif du contrat 4D — `projection_validity` est expose de bout en bout sans regression sur le schema canonique

Intention : reprendre l'intention structurelle non livree de la 6.2 planifiee.
Rend possible : distinguer proprement invalidite HA, blocage de gouvernance et action future potentielle.
Ne doit pas promettre : aucune action utilisateur nouvelle.

### Story 7.2 : Vague cible HA - les types candidats sont modelises dans le registre comme `connus`, avec contraintes explicites et perimetre borne

Intention : choisir et borner une premiere vague d'ouverture produit.
Rend possible : un backlog d'ouverture concret et auditable.
Ne doit pas promettre : ouverture produit immediate.

### Story 7.3 : Validation de projection de la vague cible — cas nominaux et cas d'echec representatifs rendent les types `validables`

Intention : prouver la validite structurelle avant toute ouverture.
Rend possible : satisfaction de la condition 2 de FR40.
Ne doit pas promettre : publication automatique ni CTA utilisateur.

### Story 7.4 : Gouvernance d'ouverture de la vague cible — `PRODUCT_SCOPE` n'evolue que sous FR40 / NFR10 dans le meme increment

Intention : ouvrir reellement la capacite produit.
Rend possible : une decision de publication honnete sur les types nouvellement supportes.
Ne doit pas promettre : que tous les blocages deviennent actionnables.

### Story 7.5 : Exposition d'actions utilisateur uniquement sur les surfaces reelles et supportees

Intention : reconnecter `cause_action` a des remediations produit effectivement disponibles.
Rend possible : des CTA honnetes sur les cas couverts par la vague ouverte.
Ne doit pas promettre : de remediations generiques hors surface existante.

Gates epic-level :
- aucune story ne modifie `PRODUCT_SCOPE` sans preuves FR40 dans le meme increment ;
- toute story modifiant `cause_action` repasse par le gate terrain `no faux CTA` ;
- toute action exposee doit etre traçable jusqu'a une surface produit reelle et testee.
```

**Rationale**

Créer un epic produit borné, séquencé, testable, sans retomber dans un epic UX opportuniste.

### 5.4 Active Cycle Manifest - réaligner les sources de vérité BMAD

**Artifact:** `_bmad-output/planning-artifacts/active-cycle-manifest.md`

**Section:** titre du cycle actif et sources de vérité actives

**OLD**

```md
Cycle actif = **Post-MVP Phase 1 - V1.1 Pilotable**
Sources de verite actives = `product-brief-jeedom2ha-post-mvp-refresh.md`, `prd-post-mvp-v1-1-pilotable.md`, `ux-delta-review-post-mvp-v1-1-pilotable.md`, `architecture-delta-review-post-mvp-v1-1-pilotable.md`, `epics-post-mvp-v1-1-pilotable.md`, `test-strategy-post-mvp-v1-1-pilotable.md`, `implementation-readiness-report-2026-03-27.md`, `sprint-status.yaml`, `backlog-icebox.md`.
```

**NEW**

```md
Cycle actif = **Moteur de projection explicable**

Sources de verite actives :
- Product Brief : `_bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md`
- PRD : `_bmad-output/planning-artifacts/prd.md`
- Architecture : `_bmad-output/planning-artifacts/architecture-projection-engine.md`
- Reconciliation PRD <-> Architecture : `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md`
- Epics / story breakdown : `_bmad-output/planning-artifacts/epics-projection-engine.md`
- Readiness report : `_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-10.md`
- Sprint status : `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Backlog futur : `_bmad-output/planning-artifacts/backlog-icebox.md`

Note :
- les artefacts `V1.1 Pilotable` deviennent du contexte secondaire verrouille ;
- aucun agent ne doit a nouveau utiliser `epics-post-mvp-v1-1-pilotable.md` pour planifier `pe-epic-7`.
```

**Rationale**

Le cycle réellement exécuté par le tracker et les stories `pe-*` n'est plus `V1.1 Pilotable`. Le manifeste doit cesser de pointer vers une source de vérité obsolète pour les décisions actuelles.

### 5.5 Sprint Status - refléter la nouvelle structure après approbation

**Artifact:** `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Section:** cycle `Moteur de Projection Explicable`

**OLD**

```yaml
pe-epic-6: in-progress
6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger: in-progress
6-3-traduction-cause-canonique-cause-label-cause-action-stables-action-proposee-uniquement-si-une-remediation-utilisateur-existe: done
pe-epic-6-retrospective: done
```

**NEW**

```yaml
pe-epic-6: done  # cloture propre apres re-homing de 6.2 vers pe-epic-7 ; valeur livree = 6.1 + 6.3
# story historique re-homee :
# 6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger -> pe-epic-7 (non executable ici)
6-3-traduction-cause-canonique-cause-label-cause-action-stables-action-proposee-uniquement-si-une-remediation-utilisateur-existe: done
pe-epic-6-retrospective: done

pe-epic-7: backlog
7-1-enrichissement-additif-du-contrat-4d-projection-validity-est-expose-de-bout-en-bout-sans-regression-sur-le-schema-canonique: backlog
7-2-vague-cible-ha-les-types-candidats-sont-modelises-dans-le-registre-comme-connus-avec-contraintes-explicites-et-perimetre-borne: backlog
7-3-validation-de-projection-de-la-vague-cible-cas-nominaux-et-cas-d-echec-rendent-les-types-validables: backlog
7-4-gouvernance-d-ouverture-de-la-vague-cible-product-scope-n-evolue-que-sous-fr40-nfr10-dans-le-meme-increment: backlog
7-5-exposition-d-actions-utilisateur-uniquement-sur-les-surfaces-reelles-et-supportees: backlog
```

**Rationale**

Le tracker doit représenter un epic 6 clôturable et un epic 7 exécutable. Garder `6.2` active dans Epic 6 empêche les deux.

### 5.6 No-change decisions

**Artifacts:** `prd.md`, `architecture-projection-engine.md`, `product-brief-jeedom2ha-2026-04-09.md`

**Decision**

```md
Aucune modification requise a ce stade.
```

**Rationale**

Le problème est dans le sequencing et dans les artefacts d'exécution, pas dans le cadrage produit ou l'architecture.

---

## 6. Recommended Approach and High-Level Action Plan

### MVP impact

**Aucun impact négatif sur le MVP / le cycle moteur de projection explicable.**

La proposition :

- ne réduit pas le scope produit ;
- ne remet pas en cause les objectifs du cycle ;
- remet simplement les capacités manquantes dans le bon conteneur.

### High-level action plan

1. Mettre à jour `active-cycle-manifest.md` pour pointer vers le cycle `Moteur de projection explicable`.
2. Mettre à jour `epics-projection-engine.md` :
   - note de clôture propre d'Epic 6 ;
   - ajout de `pe-epic-7`.
3. Transformer le fichier story `6.2` en artefact historique re-homé.
4. Mettre à jour `sprint-status.yaml` après approbation :
   - `pe-epic-6 -> done`
   - `pe-epic-7 -> backlog`
   - stories `7.1 -> 7.5 -> backlog`
5. Lancer ensuite `bmad-create-story` sur `7.1` uniquement.

### Dependencies and sequencing

- **Précondition absolue :** approbation explicite de cette proposition.
- **Précondition d'exécution :** réalignement du manifeste avant toute préparation de `7.1`.
- **Gate de reprise dev :** aucune implémentation avant création de la story `7.1`.

---

## 7. Implementation Handoff

### Scope classification

**Moderate**

Pourquoi :

- il n'y a ni rollback ni replan PRD ;
- mais il y a réorganisation du backlog, ajout d'epic, réalignement de manifeste et mise à jour du tracker.

### Handoff recipients

| Responsabilité | Rôle / workflow |
|---|---|
| Réaligner le manifeste actif | Scrum Master / Product Owner |
| Mettre à jour le plan d'epics du cycle moteur | Product Owner |
| Vérifier la cohérence de séquencement `7.1 -> 7.5` | Architect |
| Mettre à jour `sprint-status.yaml` après approbation | Scrum Master |
| Préparer la première story exécutable | Scrum Master via `bmad-create-story` |
| Implémenter ensuite `7.1` | Dev team, après validation story-level |

### Success criteria

1. `active-cycle-manifest.md` pointe vers les artefacts du cycle moteur de projection explicable.
2. `pe-epic-6` est clôturable sans faux `done`.
3. `6.2` n'est plus un item de backlog actif ; elle devient un artefact historique re-homé.
4. `pe-epic-7` existe explicitement dans le plan et dans le tracker.
5. La première story de reprise est `7.1`, pas une nouvelle dérive UX.
6. Toute future action utilisateur reste liée à une surface produit réelle et testée.

---

## 8. Checklist Summary

| Item | Status | Note |
|---|---|---|
| 1.1 Trigger story identified | [x] Done | Story `6.2` |
| 1.2 Core problem defined | [x] Done | Défaut de sequencing / responsabilité story-level |
| 1.3 Evidence gathered | [x] Done | Rétro Epic 6, story 6.2, story 6.3, FR40, manifest |
| 2.1 Current epic assessed | [x] Done | Epic 6 sain mais non clôturable tel quel |
| 2.2 Epic-level changes determined | [x] Done | Clôture propre Epic 6 + ajout Epic 7 |
| 2.3 Future epics reviewed | [x] Done | Aucun epic > 6 dans le plan actuel |
| 2.4 New epic needed | [x] Done | `pe-epic-7` requis |
| 2.5 Order / priority change | [x] Done | `pe-epic-7` devient le prochain epic requis |
| 3.1 PRD conflict check | [x] Done | Aucun conflit PRD |
| 3.2 Architecture conflict check | [x] Done | Aucun conflit architecture |
| 3.3 UX conflict check | [x] Done | Pas de nouveau recadrage UX ; gates story-level seulement |
| 3.4 Other artifacts impact | [x] Done | manifeste, epics, story 6.2, sprint-status |
| 4.1 Option 1 direct adjustment | [ ] Not viable | Trop étroit |
| 4.2 Option 2 rollback | [ ] Not viable | Régression certaine |
| 4.3 Option 3 PRD MVP review | [ ] Not viable | Non justifié |
| 4.4 Recommended path selected | [x] Done | Hybrid |
| 5.1 Issue summary created | [x] Done | Section 1 |
| 5.2 Impact documented | [x] Done | Sections 2 et 3 |
| 5.3 Recommended path documented | [x] Done | Section 4 |
| 5.4 High-level action plan defined | [x] Done | Section 6 |
| 5.5 Agent handoff established | [x] Done | Section 7 |
| 6.1 Checklist reviewed | [x] Done | Complet |
| 6.2 Proposal accuracy reviewed | [x] Done | Cohérente avec les artefacts actifs du cycle moteur |
| 6.3 User approval | [x] Done | Approbation explicite recue le 2026-04-22 (`yes`) |
| 6.4 sprint-status update | [x] Done | Tracker mis a jour apres approbation |
| 6.5 Next steps confirmed | [x] Done | prochaine etape confirmee : preparation de la story `7.1` |

---

## 9. Approval Request

Cette proposition recommande de :

- **re-home `6.2` vers `pe-epic-7`** ;
- **clore proprement `pe-epic-6`** sur sa valeur réellement livrée ;
- **réaligner les sources de vérité BMAD** sur le cycle `Moteur de projection explicable` ;
- **préparer `7.1` comme première story exécutable** du prochain epic.

**Décision recueillie :** `yes` — proposition approuvee le `2026-04-22`.
