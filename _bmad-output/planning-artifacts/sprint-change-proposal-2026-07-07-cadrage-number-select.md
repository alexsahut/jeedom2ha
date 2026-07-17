---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-07-07
status: approved
scope_classification: minor
trigger: cadrage-ouverture-number-select-composants-ha-non-gouvernes
mode: batch
communication_language: french
proposed_by: clawcode
impacts_if_approved:
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/ux-spec.md
  - resources/daemon/validation/ha_component_registry.py
references:
  - _bmad-output/planning-artifacts/epics-projection-engine.md (Epic 10 Story 10.4, garde-fou number/select ligne Dev notes)
  - _bmad-output/planning-artifacts/ha-projection-reference.md / .yaml
  - resources/daemon/validation/ha_component_registry.py (HA_COMPONENT_REGISTRY vs PRODUCT_SCOPE)
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-06-mapping-configurable.md (précédent d'ajout d'epic par correct-course)
---

# Sprint Change Proposal 2026-07-07 - Cadrage de l'ouverture de `number` et `select`

## 1. Issue Summary

### Trigger

Le 2026-07-07, après clôture de la Story 16.3, Alexandre a demandé quels composants Home Assistant ne sont pas encore gouvernés, puis a demandé de **préparer une story pour `number` et une autre pour `select`**, en utilisant le workflow BMAD adéquat.

Audit du registre : `HA_COMPONENT_REGISTRY` (`resources/daemon/validation/ha_component_registry.py`) contient 10 composants ; `PRODUCT_SCOPE` en gouverne 8. Les deux composants **connus et validables mais non gouvernés** sont :

| Composant | required_fields | required_capabilities |
|---|---|---|
| `number` | `command_topic`, `platform`, `availability` | `has_command` |
| `select` | `command_topic`, `options`, `platform`, `availability` | `has_command`, `has_options` |

### Constat de gouvernance

Un composant ne s'ouvre pas « parce qu'il est registré ». La règle AR13/FR40/NFR10 impose que toute entrée dans `PRODUCT_SCOPE` soit livrée dans le **même incrément** avec : (1) l'entrée `HA_COMPONENT_REGISTRY` (déjà présente pour `number` et `select`), (2) au moins un cas nominal + un cas d'échec `validate_projection()`, (3) un test de non-régression du contrat 4D. De plus, le garde-fou explicite de la Story 10.4 (`epics-projection-engine.md`, Dev notes) indique : *« `number` et `select` ne doivent être introduits que si un besoin réel de consigne ou de mode distinct est prouvé »*.

Créer directement deux stories d'**ouverture** violerait ce garde-fou tant qu'aucun équipement Jeedom concret ne justifie une consigne (`number`) ou un mode distinct (`select`) non déjà couvert par les types ouverts (`climate`, `switch`, `sensor`, etc.).

### Décision Alexandre (2026-07-07)

- **Driver = (1b)** : stories de **cadrage seulement** (modèle Story 10.4), pas d'ouverture effective de `PRODUCT_SCOPE`.
- **Structure = (2A)** : nouvel epic `pe-epic-17` via correct-course, hébergeant les deux stories, puis `create-story` ×2.

### Category

**Roadmap adjustment / cadrage de gouvernance.** Aucun changement de PRD, d'architecture ou de code. Deux stories de cadrage documentaire dans un nouvel epic conteneur.

## 2. Impact Analysis

### 2.1 Checklist correct-course

| Item | Statut | Notes |
|---|---|---|
| 1.1 Trigger story | [N/A] | Pas de bug story-level ; demande roadmap post-Story 16.3. |
| 1.2 Core problem | [x] | Deux composants HA connus/validables non gouvernés ; décision d'ouverture à cadrer, pas à forcer. |
| 1.3 Evidence | [x] | `ha_component_registry.py` (registry vs scope), garde-fou Story 10.4. |
| 2.1 Current epic | [x] | `pe-epic-16` reste `in-progress` (overrides) ; aucun rollback. |
| 2.2 Epic-level changes | [x] | Ajouter `pe-epic-17` (cadrage number/select) avec 2 stories en backlog. |
| 2.3 Future epics | [x] | Aucun conflit ; une ouverture effective éventuelle sera un incrément séparé. |
| 2.4 New epic needed | [x] | Oui ; numéro 17 libre (grep sprint-status.yaml), périmètre distinct des overrides pe-epic-16. |
| 2.5 Priority/order | [x] | Cadrage documentaire ; non bloquant pour pe-epic-16. |
| 3.1 PRD conflict | [x] | Aucun ; FR40/NFR10 couvrent déjà la gouvernance d'ouverture. |
| 3.2 Architecture conflict | [N/A] | Aucun changement d'architecture ; cadrage seulement. |
| 3.3 UI/UX conflict | [N/A] | Aucune surface UI ajoutée. |
| 3.4 Other artifacts | [!] | `epics-projection-engine.md` + `sprint-status.yaml` à mettre à jour après approbation. |
| 4.1 Direct adjustment | [x] Viable | Ajouter un epic de cadrage sans toucher au code ni aux epics clos. |
| 4.2 Rollback | [x] Not viable | Aucun travail à revertir. |
| 4.3 MVP review | [x] Not needed | MVP du cycle intact. |
| 4.4 Recommended path | [x] | Direct Adjustment : cadrage maintenant, ouverture éventuelle différée sous FR40/NFR10. |
| 5.x Proposal components | [x] | Issue, impact, changements, handoff présents. |
| 6.3 Approval | [x] | Décisions (1b)+(2A) données par Alexandre le 2026-07-07. |
| 6.4 Sprint status | [!] | Mise à jour uniquement après ce SCP approuvé. |

### 2.2 Ce qui ne change pas

- Le cycle actif reste **Moteur de projection explicable**.
- `PRODUCT_SCOPE` reste inchangé (8 composants) : aucune ouverture effective de `number`/`select`.
- `HA_COMPONENT_REGISTRY` reste inchangé (les deux composants y sont déjà `connus`/`validables`).
- `pe-epic-16` (overrides) reste `in-progress`, non impacté.
- Aucun code, test, mapping, validation ou publication modifié.

### 2.3 Ce qui change si approuvé

- `pe-epic-17` est matérialisé comme epic de **cadrage** (backlog).
- Deux stories de cadrage en backlog : `17-1` (`number`/consigne) et `17-2` (`select`/mode).
- Chaque story classe les cas candidats et produit, si une ouverture est justifiée, un handoff précis (équipement cible, `generic_type`, preuves FR40/NFR10 à écrire) vers un incrément d'ouverture séparé.

### 2.4 Impact technique

| Zone | Impact |
|---|---|
| Code Python | **Aucun** dans cet epic (cadrage documentaire). |
| Registre HA | Aucun — `number`/`select` déjà présents comme `connus`/`validables`. |
| Tests | Aucun dans cet epic ; les preuves nominal/échec `validate_projection()` + 4D sont exigées uniquement dans un futur incrément d'ouverture. |
| Diagnostic / MQTT | Aucun. |

## 3. Path Forward Evaluation

### Option 1 - Direct Adjustment : ajouter `pe-epic-17` de cadrage (recommandée)

**Statut : recommandée et retenue (décision Alexandre 2A + 1b).**

Cadre proprement la question sans déroger au garde-fou 10.4 ni à AR13/FR40/NFR10. L'ouverture réelle reste conditionnée à une preuve d'équipement.

### Option 2 - Ouvrir directement `number` et `select` dans `PRODUCT_SCOPE`

**Statut : non recommandée.** Dérogerait au garde-fou explicite Story 10.4 (besoin réel non prouvé) et créerait des stories d'ouverture sans équipement cible.

### Option 3 - Rattacher à `pe-epic-16`

**Statut : écartée par Alexandre.** Mélangerait *overrides utilisateur* (16) et *ouverture de scope* (périmètres distincts).

### Selected approach

**Option 1 : Direct Adjustment, epic de cadrage `pe-epic-17`.**

## 4. Detailed Change Proposals

### 4.1 `epics-projection-engine.md` — Ajouter `pe-epic-17`

**Section :** après le bloc Epic 16 (dernier epic du document). Correction préalable : retrait d'une fence de code `` ```md `` orpheline ouverte avant le bloc Epic 16 (jamais refermée), pour que les epics 16 et 17 rendent en markdown propre.

**NEW :** bloc `### Epic 17 — Cadrage de l'ouverture gouvernée de number et select ...` avec Story 17.1, Story 17.2 et les gates epic-level (voir le fichier appliqué).

**Rationale :** conteneur explicite de cadrage, aligné sur le modèle Story 10.4, sans ouverture effective.

### 4.2 `sprint-status.yaml` — Ajout après approbation

**NEW (bloc commentaire + development_status) :**

```yaml
  pe-epic-17: backlog  # cadrage ouverture number/select (composants HA connus/validables non gouvernes) ; cadre par SCP 2026-07-07 ; stories de cadrage seulement, aucune ouverture PRODUCT_SCOPE
  17-1-cadrage-ouverture-number-consigne: backlog
  17-2-cadrage-ouverture-select-mode: backlog
```

**Rationale :** enregistre l'epic et les deux stories comme backlog, prêtes pour `create-story`.

## 5. Recommendation

Approuver un correct-course **mineur** :

- oui à la matérialisation de `pe-epic-17` (cadrage) ;
- oui aux deux stories de cadrage `17-1` (`number`) et `17-2` (`select`) ;
- non à toute ouverture effective de `PRODUCT_SCOPE` dans cet epic ;
- toute ouverture réelle reste un incrément séparé sous FR40/NFR10 (registry déjà présent + nominal/échec `validate_projection()` + non-régression 4D).

## 6. Implementation Handoff

### Scope classification

**Minor.** Cadrage documentaire, aucun code, aucun rollback, aucun MVP touché.

### Recipients

| Role | Responsabilité |
|---|---|
| Scrum Master | Ajouter `pe-epic-17` + 2 stories au backlog. |
| Dev (create-story) | Produire `17-1` et `17-2` en `ready-for-dev`. |
| Product Owner | Fournir, lors de `dev-story`, les équipements Jeedom candidats (consigne / mode) pour trancher le classement. |

### Success criteria

- `pe-epic-17` et les 2 stories apparaissent en backlog.
- Les stories `create-story` restent des cadrages (aucune modif `PRODUCT_SCOPE`).
- Le classement par cas et le handoff FR40/NFR10 sont explicites dans chaque story.

## 7. Decision

Approved — Alexandre a répondu `1b, 2.a` le 2026-07-07 (cadrage seulement + nouvel epic via correct-course).

Actions d'application :

- matérialiser `pe-epic-17` dans `epics-projection-engine.md` ✅ ;
- ajouter `pe-epic-17` + `17-1` + `17-2` en `backlog` dans `sprint-status.yaml` ;
- enchaîner `create-story` ×2 (→ `ready-for-dev`).
