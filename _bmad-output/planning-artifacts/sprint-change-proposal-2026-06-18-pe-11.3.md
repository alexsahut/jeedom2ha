---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-06-18
status: approved
scope_classification: moderate
trigger: story-11.3-planifiee-au-tableau-de-travail-mais-jamais-formalisee-et-dependance-vague-2-streaming
mode: batch
communication_language: french
proposed_by: clawcode
workflow: bmad correct-course (4-implementation)
impacts_if_approved:
  - _bmad-output/planning-artifacts/epics-projection-engine.md (Epic 11 : ajout Story 11.3 + note dépendance vague 2 ; Epic 12 : ajout Story 12.2 réservée)
  - _bmad-output/implementation-artifacts/sprint-status.yaml (ajout 11-3-* backlog + 12-2-* réservé + last_updated)
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md (FR49 couvre déjà l'extension par vagues gouvernées ; aucune FR nouvelle requise)
  - _bmad-output/planning-artifacts/architecture-projection-engine.md (la vague 2 reste un additif au chemin de valeur de pe-epic-12, pas une modification du contrat des 5 étapes)
  - resources/daemon/* (aucun code modifié — implémentation = stories à venir)
references:
  - _bmad-output/planning-artifacts/backlog-icebox.md §4 (inventaire IQ EV Charger eq583 + Pilotage priorisation solaire eq628)
  - _bmad-output/implementation-artifacts/pe-epic-10-retro-2026-06-12.md (Partie 2 : triage pe-epic-11 ; « IQ EV / priorisation solaire » reporté après pe-epic-11)
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-18.md (pe-epic-12 + formalisation pe-epic-11 — proposal parent approuvé)
  - workboard SQLite (carte « Story 11.3 », id 9039c60c-f221-468f-83cd-6c99f82f6ea4, board default, statut backlog, créée 2026-06-12 00:08:58)
---

# Sprint Change Proposal 2026-06-18 (pe-11.3) — Inscription de Story 11.3 (IQ EV / pilotage priorisation solaire) et de sa dépendance à la vague 2 de streaming

> Suite du correct-course `sprint-change-proposal-2026-06-18.md` (pe-epic-12 + formalisation pe-epic-11). Ce proposal complète la réconciliation epic-11 ↔ tableau de travail.

## 1. Issue Summary

### Trigger

Lors de la réconciliation du backlog pe-epic-11 avec le tableau de travail (workboard), une **3ᵉ story planifiée mais jamais formalisée** a été identifiée.

- **Carte « Story 11.3 »** présente dans le workboard (`board default`, statut `backlog`, id `9039c60c-…`), **créée le 2026-06-12 à 00:08:58** — dans la foulée de la rétrospective pe-epic-10 (12 juin), à la suite des cartes 11.1 (00:07:51) et 11.2 (00:08:32).
- La carte n'a **aucun scope documenté** : note boilerplate générique, aucun commentaire, aucun event hors `created`. Le sujet n'apparaît dans **aucun transcript de session** de travail (les seules mentions « Story 11.3 » proviennent de la session d'investigation du 2026-06-18 elle-même).
- Le scope a été **reconstitué par recoupement** retro + icebox + chronologie de création des cartes, puis **confirmé par l'utilisateur** : Story 11.3 = **IQ EV Charger (eq Jeedom 583) + Pilotage priorisation solaire (eq Jeedom 628)** — le 3ᵉ et dernier sujet énergie du backlog (`backlog-icebox.md §4`).

### Core problem (catégorie : misunderstanding of original requirements / suivi incomplet)

Un sujet énergie réel, planifié au tableau de travail le 12 juin, n'a **jamais été inscrit dans le contrat de planification** (`epics-projection-engine.md`) ni dans `sprint-status.yaml`. Il manque donc une définition d'epic-level pour Story 11.3, et — point clé révélé par l'analyse — une **dépendance inter-epic** explicite vers une vague 2 de streaming qui n'existe pas encore.

### Evidence

- **Inventaire icebox §4 (fourni par ClawBox 2026-06-09).** IQ EV (eq583) mélange des types : `binary_sensor` (#5986 Branché, #5987 Charge, #6009 Charge solaire état, #6010 Charge manuelle état) + `sensor` (#5991 Puissance W, #5992 Énergie session Wh, #5993 Énergie jour Wh) + `switch`/`button` On/Off dissociés (#5999/#6001/#6000/#6021). Pilotage priorisation (eq628) est **100% `switch` triple-commande** (info+on+off) pour 4 charges (#5977→#6006).
- **Retro pe-epic-10 (Partie 2, ligne 103).** « IQ EV / priorisation solaire et autres composites » est explicitement classé **« Reporté après pe-epic-11 »**. La carte 11.3 a donc été posée comme placeholder du sujet différé.
- **Dépendance technique.** Story 12.1 (proposal parent) ne couvre que `sensor` + `binary_sensor` (vague 1). Les parties `switch`/`button` d'IQ EV et **toute** la story eq628 ne peuvent sortir de l'état `unknown` qu'avec une **vague 2 de streaming (switch/button)**, non encore planifiée.

## 2. Impact Analysis

### Epic Impact

- **pe-epic-11 (Énergie / Routage solaire)** — scope **étendu** d'une story déjà planifiée (11.3). Aucune remise en cause du travail livré (11.1 / 11.1.bis). pe-epic-11 reste un epic de **restitution discovery lecture seule** ; la valeur runtime de 11.3 relève de pe-epic-12, comme pour 11.1 et 11.2.
- **pe-epic-12 (Restitution d'état runtime)** — gagne un jalon : une **Story 12.2 (réservée)** « vague 2 = streaming valeur switch/button », dont **11.3 (parties actionnables) et le `switch.554` de 11.2 dépendent**. La vague 1 (12.1) reste inchangée et prioritaire.

### Story Impact

| Story | État avant | État après |
|---|---|---|
| 12.1 — Streaming valeur sensor/binary_sensor (vague 1) | ready-for-dev | inchangé (reste la prochaine à développer) |
| 11.2 (réservée) — Chauffe-eau eq554 | réservée (commentaire) | inchangée ; on note que sa partie `switch.554` dépend de 12.2 |
| **12.2 (réservée) — Streaming valeur switch/button (vague 2)** | n'existe pas | **NOUVELLE (réservée)** — débloque les états actionnables |
| **11.3 (backlog) — IQ EV (eq583) + Pilotage priorisation solaire (eq628)** | carte workboard non formalisée | **INSCRITE (backlog)** avec dépendance explicite : sensor/binary_sensor ⟸ 12.1 ; switch/button ⟸ 12.2 |

### Artifact Conflicts

- **`epics-projection-engine.md`** : Epic 11 (liste + section détaillée) ne mentionne pas Story 11.3 ; Epic 12 ne mentionne pas la vague 2. → ajouts ciblés.
- **`sprint-status.yaml`** : ni `11-3-*` ni `12-2-*` présents. → ajout en backlog/réservé.
- **`prd.md`** : **aucun changement requis.** FR49 prévoit déjà explicitement que « les autres domaines (`switch`, `climate`, …) sont ajoutés par vagues ultérieures gouvernées ». La vague 2 est donc déjà couverte par l'exigence existante.
- **`architecture-projection-engine.md`** : **aucun changement.** La vague 2 réutilise le chemin de valeur de pe-epic-12 (callback PHP + `sync/state.py` + `state_topic`), étendu aux plateformes `switch`/`button` ; elle ne modifie pas le contrat des 5 étapes de projection.

### Technical Impact

- Aucun code modifié par cette proposition (planification pure).
- Implémentation différée (non engagée ici) : la vague 2 (12.2) étendra `resources/daemon/sync/state.py` aux états `switch`/`button` et devra vérifier le pattern triple-commande (info+on+off) du `MapperRegistry` pour eq628 (cf. icebox §4.2). Story 11.3 consommera cette capacité.

## 3. Recommended Approach

**Direct Adjustment** — pas de rollback, pas de réduction de MVP.

**Décision de séquencement (le cœur de la demande « quand poser 11.3 ») :**

| Ordre | Story | Rôle |
|---|---|---|
| 1 | **12.1** (vague 1 sensor/binary_sensor) | déjà ready-for-dev — alimente les sensors MSunPV (corrige le `unknown` de 11.1) + parties sensor/binary d'eq554 et d'IQ EV |
| 2 | **11.2** (eq554) | parties sensor/binary OK via 12.1 ; `switch.554` flaggé « attend 12.2 » |
| 3 | **12.2** (vague 2 switch/button) | débloque les états actionnables |
| 4 | **11.3** (IQ EV + pilotage eq628) | enfin sortable de `unknown` (ses parties switch/button dépendent de 12.2) |

**Pourquoi inscrire 11.3 maintenant mais ne PAS lancer create-story tout de suite :**
- **Inscrire maintenant** (backlog + dépendance) supprime le risque de re-perdre le sujet (déjà perdu une fois entre le 12 juin et aujourd'hui) et rend la dépendance vague 2 traçable.
- **create-story différé** : écrire le fichier story 11.3 avant que 12.2 existe le ferait rancir (il serait rédigé contre une capacité de streaming switch/button inexistante). On applique la même logique que « 12.1 avant 11.2 » : on ne crée/lance une story que quand sa dépendance terrain est réelle.

- **Effort** : planification = cette proposition. 11.3 (futur) = M (types mixtes, pattern triple-commande à valider). 12.2 (futur) = M/L (extension du chemin de valeur aux plateformes actionnables).
- **Risque** : faible pour cette proposition (inscription) ; borné par la dépendance explicite.
- **Timeline** : aucune dérive ; 12.1 reste la prochaine story à développer.

## 4. Detailed Change Proposals

### 4.1 — `epics-projection-engine.md` (a) : « Liste des epics » → invariants pe-epic-11 (après la ligne 441)

```
OLD (dernier invariant Epic 11 de la liste) :
- l'inventaire cible reste borné par `backlog-icebox.md §3` ; aucune ouverture de l'intégration Enphase native HA (hors scope jeedom2ha).

NEW :
- l'inventaire cible reste borné par `backlog-icebox.md §3` et `§4` (IQ EV eq583 / pilotage priorisation eq628) ; aucune ouverture de l'intégration Enphase native HA (hors scope jeedom2ha) ;
- Story 11.3 (IQ EV + pilotage priorisation) mêle des types : ses `sensor`/`binary_sensor` sont alimentés par la vague 1 (pe-epic-12 / 12.1), ses états actionnables `switch`/`button` dépendent de la vague 2 (pe-epic-12 / 12.2) — 11.3 n'est créée/lancée qu'une fois 12.2 disponible.
```

### 4.2 — `epics-projection-engine.md` (b) : section détaillée Epic 11 → ajouter Story 11.3 (après la ligne 1840, avant `### Gates epic-level pe-epic-11`)

```
NEW :

### Story 11.3 (backlog) — IQ EV Charger (eq583) + Pilotage priorisation solaire (eq628)
Planifiée au tableau de travail le 2026-06-12 (3ᵉ sujet énergie, reporté après pe-epic-11 par la retro pe-epic-10). Inventaire `backlog-icebox.md §4`.
- **IQ EV (eq583)** : `binary_sensor` (#5986, #5987, #6009, #6010) + `sensor` (#5991, #5992, #5993) + `switch`/`button` On/Off dissociés (#5999/#6001/#6000/#6021) — pas d'ouverture cosmétique.
- **Pilotage priorisation (eq628)** : `switch` triple-commande info+on+off (#5977→#6006, 4 charges) — vérifier le support du pattern triple-commande dans le `MapperRegistry` avant ouverture.
- **Dépendance streaming** : parties `sensor`/`binary_sensor` ⟸ pe-epic-12 / 12.1 (vague 1) ; états actionnables `switch`/`button` ⟸ pe-epic-12 / 12.2 (vague 2). create-story 11.3 différé jusqu'à disponibilité de 12.2.
```

### 4.3 — `epics-projection-engine.md` (c) : section détaillée Epic 12 → ajouter Story 12.2 réservée (après la ligne 1855, avant `### Gates epic-level pe-epic-12`)

```
NEW :

### Story 12.2 (réservée) — Streaming de valeur switch / button (vague 2)
Réservée. Étend le chemin de valeur de 12.1 (`resources/daemon/sync/state.py`) aux plateformes actionnables `switch` et `button`, pour restituer l'état readback de ces entités (sortie du `unknown`). Débloque : le `switch.jeedom2ha_554` de Story 11.2, et les parties actionnables de Story 11.3 (IQ EV On/Off, pilotage priorisation eq628). Borne : vague 2 = `switch` + `button` uniquement ; `climate` et autres domaines = vagues ultérieures gouvernées (FR49).
```

### 4.4 — `epics-projection-engine.md` (d) : Gates epic-level pe-epic-12 → noter la séquence des vagues

```
OLD :
- vague 1 strictement bornée `sensor` + `binary_sensor` ; ouverture des domaines actionnables différée à des vagues ultérieures gouvernées ;

NEW :
- vagues bornées et séquencées : vague 1 (12.1) = `sensor` + `binary_sensor` ; vague 2 (12.2, réservée) = `switch` + `button` ; domaines suivants (`climate`, …) = vagues ultérieures gouvernées (FR49) ; aucune vague n'ouvre un domaine hors `PRODUCT_SCOPE` ;
```

### 4.5 — `sprint-status.yaml` (a) : bloc pe-epic-11 → ajouter 11-3 (après la ligne 237)

```
OLD :
  # 11-2-* RÉSERVÉ : chauffe-eau eq554 (backlog-icebox §3.2, P2 Alex) — pas encore créé

NEW :
  # 11-2-* RÉSERVÉ : chauffe-eau eq554 (backlog-icebox §3.2, P2 Alex) — pas encore créé ; partie switch.554 dépend de pe-epic-12 / 12.2 (vague 2)
  11-3-iq-ev-pilotage-priorisation-solaire: backlog  # inscrit par correct-course 2026-06-18 (pe-11.3) — IQ EV eq583 + pilotage priorisation eq628 (backlog-icebox §4) ; types mixtes : sensor/binary ⟸ 12.1, switch/button ⟸ 12.2 ; create-story différé jusqu'à 12.2 ; carte workboard 9039c60c préexistante
```

### 4.6 — `sprint-status.yaml` (b) : bloc pe-epic-12 → ajouter 12-2 réservé (après la ligne 249)

```
OLD :
  12-1-streaming-valeur-sensor-binary-sensor-vague-1: ready-for-dev  # create-story 2026-06-18 — StateSynchronizer (sync/state.py) miroir de CommandSynchronizer ; double state_topic mono+multi-sensor eq553 ; canal inbound Jeedom→daemon à trancher Task 1 ; gate terrain eq553 non-unknown

NEW :
  12-1-streaming-valeur-sensor-binary-sensor-vague-1: ready-for-dev  # create-story 2026-06-18 — StateSynchronizer (sync/state.py) miroir de CommandSynchronizer ; double state_topic mono+multi-sensor eq553 ; canal inbound Jeedom→daemon à trancher Task 1 ; gate terrain eq553 non-unknown
  # 12-2-* RÉSERVÉ : streaming valeur switch/button (vague 2) — étend sync/state.py aux plateformes actionnables ; débloque switch.554 (11.2) et parties actionnables d'IQ EV/pilotage (11.3) — pas encore créé
```

### 4.7 — `sprint-status.yaml` (c) : last_updated

```
OLD :
last_updated: '2026-06-18'  # correct-course 2026-06-18 : pe-epic-11 formalisé + pe-epic-12 ouvert (restitution d'état runtime) ; create-story 12.1 → ready-for-dev

NEW :
last_updated: '2026-06-18'  # correct-course 2026-06-18 (pe-11.3) : Story 11.3 inscrite (backlog, IQ EV/pilotage) + Story 12.2 réservée (vague 2 switch/button) ; dépendances inter-epic explicitées
```

## 5. Implementation Handoff

- **Scope classification : Moderate** — réorganisation de backlog (inscription d'une story planifiée + jalon de dépendance), sans replan ni rollback, sans changement de PRD.
- **Handoff** :
  - epics + sprint-status → mise à jour documentaire additive (cette proposition, après approbation).
  - **Aucune** create-story déclenchée par cette proposition. 11.3 et 12.2 restent backlog/réservé.
  - Prochaine action de dev inchangée : **dev-story 12.1** (vague 1).
- **Séquence de création future** : create-story 12.2 (quand 12.1 livrée) → create-story 11.3 (quand 12.2 livrée).
- **Success criteria** :
  - Story 11.3 inscrite en backlog dans `epics-projection-engine.md` + `sprint-status.yaml`, avec scope eq583/eq628 et dépendance vague 1/vague 2 explicite ;
  - Story 12.2 réservée comme cible de dépendance pour `switch.554` (11.2) et les parties actionnables de 11.3 ;
  - aucune dérive sur 12.1 (reste la prochaine story à développer).

---

## Annexe — Change Navigation Checklist (exécution)

**Section 1 — Trigger & contexte**
- 1.1 Story déclencheuse : réconciliation backlog pe-epic-11 ↔ workboard → carte « Story 11.3 » non formalisée — **[x] Done**
- 1.2 Problème : sujet énergie planifié (12 juin) jamais inscrit au contrat de planification + dépendance vague 2 implicite — **[x] Done**
- 1.3 Évidence : carte workboard 9039c60c (backlog), icebox §4, retro pe-epic-10 ligne 103 — **[x] Done**

**Section 2 — Epic Impact**
- 2.1 pe-epic-11 complétable en l'état + 1 story planifiée à inscrire — **[x] Done**
- 2.2 Changement epic : ajout Story 11.3 (pe-epic-11) + Story 12.2 réservée (pe-epic-12) — **[x] Done**
- 2.3 Epics futurs : pe-epic-12 impacté (jalon vague 2) — **[x] Done**
- 2.4 Aucun epic rendu obsolète ; aucun nouvel epic requis — **[x] Done**
- 2.5 Ordre/priorité : séquence 12.1 → 11.2 → 12.2 → 11.3 actée — **[x] Done**

**Section 3 — Artifact Conflict**
- 3.1 PRD : pas de conflit, FR49 couvre déjà les vagues — **[N/A]**
- 3.2 Architecture : additif au chemin de valeur pe-epic-12, pas de modif du contrat — **[N/A]**
- 3.3 UI/UX : sans objet — **[N/A]**
- 3.4 Autres artefacts : epics-projection-engine.md + sprint-status.yaml — **[x] Done**

**Section 4 — Path Forward**
- 4.1 Option 1 Direct Adjustment — **[x] Viable** (effort Low, risque Low)
- 4.2 Option 2 Rollback — **[ ] Not viable** (rien à annuler)
- 4.3 Option 3 MVP Review — **[ ] Not viable** (MVP non impacté)
- 4.4 Sélection : **Option 1 — Direct Adjustment**

**Section 5 — Composants du proposal** : Issue Summary, Impact, Recommended Approach, Detailed Changes, Handoff — **[x] Done**

**Section 6 — Final review** : en attente d'approbation utilisateur explicite (6.3) avant application des éditions (6.4).
