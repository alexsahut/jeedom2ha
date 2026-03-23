# Sprint Change Proposal — Epic 1 / V1.1 — Contrat `published_scope` non mis a jour sur exclusion piece legacy

**Date :** 2026-03-22  
**Cycle actif :** Post-MVP Phase 1 - V1.1 Pilotable  
**Mode :** Batch  
**Auteur :** Bob, Scrum Master  
**Scope :** Moderate limite — reouverture d'une story backend productrice existante, blocage explicite d'une story consommatrice, sans nouvel epic, sans nouveau cadrage produit

---

## Diagnostic de workflow BMAD

### Initialisation et cadre

- [x] Trigger clarifie: la validation terrain de Story 1.2 a echoue sur AC3.
- [x] Mode fixe: **Batch** demande explicitement par l'utilisateur.
- [x] Cycle actif confirme: **Post-MVP Phase 1 - V1.1 Pilotable**.
- [x] Sources actives chargees: manifeste, epics V1.1, strategie de test V1.1, sprint-status, Story 1.1, Story 1.2.

### Checklist BMAD — synthese

| Section checklist | Statut | Conclusion |
| --- | --- | --- |
| 1. Trigger et contexte | [x] Done | Le defaut est observe sur la chaine backend `published_scope`, pas sur le rendu UI 1.2 |
| 2. Impact epic | [x] Done | Impact limite a **Epic 1** |
| 3. Impact artefacts | [x] Done | Pas de conflit PRD / UX / architecture ; delta story-level et sprint-status suffisant |
| 4. Path forward | [x] Done | **Option 1 - Direct Adjustment** retenue |
| 5. Components du proposal | [x] Done | Propositions explicites ci-dessous |
| 6. Final review / approval | [!] Action-needed | Approbation utilisateur requise avant application des mises a jour d'artefacts |

---

## Section 1 : Resume du probleme

### Story declencheuse

**Story 1.2 - Vue globale et synthese par piece sans recalcul frontend**

### Probleme constate

La Story 1.2 ne peut pas etre passee en `done` car sa validation terrain echoue sur **AC3** :

- la configuration Jeedom change bien via `excludedObjects`;
- `getFullTopology()` voit bien les equipements de la piece `bureau` comme exclus;
- mais le contrat backend `/system/published_scope` reste inchange;
- l'UI 1.2 reste coherente avec ce backend inchange;
- le defaut est donc situe **en amont de l'UI**, dans la story productrice backend.

### Hypothese technique de travail

Hypothese de travail la plus plausible au vu du code et des tests existants:

- le producteur PHP pre-remplit `published_scope.pieces[*]` avec `raw_state = inherit` et `source = default_inherit`, meme sans regle V1.1 explicite;
- le resolver backend pourrait ne pas activer le fallback legacy `excludedObjects -> piece exclude` si cet etat piece est interprete comme deja explicite;
- dans cette hypothese, le chemin reel `excludedObjects -> getFullTopology() -> /action/sync -> /system/published_scope` peut rester bloque sur `inherit`, alors meme que les eqs sont bien marques `is_excluded/object` dans la topologie.

Cette hypothese est coherente avec le symptome terrain et avec le trou de couverture constate:

- la couverture unitaire teste bien le fallback legacy `object`, mais avec `raw_scope = {}` uniquement;
- la couverture HTTP teste des cas explicites et un fallback `plugin`, pas le cas reel issu du payload PHP pre-rempli pour les pieces.

Conclusion de workflow: meme si la cause technique exacte doit encore etre validee precisement en reprise story-level, le defaut observe reste traite correctement comme un **defaut backend rattache a Story 1.1**, pas comme une derive UI de Story 1.2.

---

## Section 2 : Analyse d'impact

### Impact sur les epics

| Epic | Impact | Commentaire |
| --- | --- | --- |
| Epic 1 | Impacte | Le contrat backend racine de perimetre n'est pas encore suffisamment fiable sur le chemin legacy piece |
| Epic 2 | Aucun | Aucun delta requis |
| Epic 3 | Aucun immediat | Depend toujours d'un contrat de perimetre fiable fourni par Epic 1 |
| Epic 4 | Aucun immediat | Non concerne a ce stade |

### Impact sur les stories

| Story | Impact | Decision |
| --- | --- | --- |
| 1.1 | Invalidee partiellement | A rouvrir comme story productrice backend |
| 1.2 | Bloquee pour cloture | Reste story consommatrice correcte, mais non validable tant que 1.1 n'est pas corrigee |
| 1.3 | Aucun changement de texte requis | Ne doit pas avancer tant que 1.1 est rouverte |
| 1.4 | Aucun changement de texte requis | Ne doit pas avancer tant que 1.1 est rouverte |

### Impact sur les artefacts actifs

| Artefact | Impact | Decision |
| --- | --- | --- |
| PRD actif | Aucun conflit | Pas de mise a jour requise |
| UX active | Aucun conflit | Pas de mise a jour requise |
| Architecture active | Aucun conflit | Pas de mise a jour requise |
| Strategie de test active | Suffisante au niveau addendum | Pas de delta global requis ; le trou doit etre ferme au niveau story/test case |
| Story 1.1 | Oui | Reouverture + precision du trou d'integration a couvrir |
| Story 1.2 | Oui | Note de blocage / validation dependante de 1.1 |
| sprint-status.yaml | Oui | Reouverture explicite de 1.1, 1.2 conservee en review avec note de blocage |

### Pourquoi PRD / UX / architecture ne doivent pas etre rouverts

Les artefacts actifs disent deja la bonne chose:

- le backend est la source unique du contrat;
- le perimetre est determine cote backend;
- l'UI ne doit pas recalculer;
- l'Epic 1 depend d'un resolver backend unique et deterministe.

Le probleme n'est pas un manque de cadrage.  
Le probleme est un **ecart entre la story 1.1 declaree done et le comportement reel d'un chemin backend deja inclus dans son perimetre de compatibilite**.

---

## Section 3 : Approche recommandee

### Option retenue

**Option 1 - Direct Adjustment**

### Recommandation explicite

**Rouvrir Story 1.1** plutot que creer une nouvelle story corrective backend dans Epic 1.

### Rationale

1. Le defaut ne porte pas sur un nouveau besoin produit. Il contredit un contrat deja attribue a Story 1.1.
2. Story 1.2 consomme correctement le backend actuel; elle n'est pas la source du defaut.
3. Creer une nouvelle story corrective introduirait une dependance supplementaire artificielle entre la story productrice et la story consommatrice, alors que la dependance officielle existe deja: **1.2 depend de 1.1**.
4. La traceabilite la plus propre consiste a dire la verite du backlog:
   - la story productrice backend n'est pas finie;
   - la story consommatrice reste bloquee pour sa cloture.
5. Cette voie minimise les deltas documentaires:
   - pas de nouvel epic;
   - pas de nouvelle story a inserer;
   - pas de re-sequencement V1.1;
   - pas de PRD / UX / architecture a retoucher.

### Qualification des autres options

- **Option 2 - Potential Rollback:** non retenue. Aucun rollback produit ou UI n'est necessaire.
- **Option 3 - PRD MVP Review:** non retenue. Le MVP / V1.1 reste atteignable, aucun changement de cadrage n'est justifie.
- **Creation d'une story corrective backend Epic 1:** non recommandee dans ce cas. Elle masquerait un defect de fermeture de 1.1 au lieu de corriger la story productrice deja declaree `done`.

### Estimation

- **Effort:** faible a moyen
- **Risque:** faible
- **Impact planning:** limite a Epic 1
- **Impact produit:** aucun changement de scope

---

## Section 4 : Propositions de changement detaillees

### Artifact 1 — Story 1.1

**Story :** `1-1-resolver-canonique-du-perimetre-publie`  
**Section :** `Status`

**OLD**

```md
Status: done
```

**NEW**

```md
Status: in-progress
```

**Rationale**

La story productrice backend ne peut plus rester `done` apres un echec terrain coherent avec un trou reel de la chaine `/action/sync -> /system/published_scope` sur le chemin legacy piece.

**Section :** `Testing Requirements` / note de reouverture

**OLD**

Pas de preuve explicite requise sur le chemin reel:

```text
excludedObjects -> getFullTopology() -> /action/sync -> /system/published_scope
```

quand `published_scope.pieces[*]` est pre-rempli avec `raw_state = inherit`.

**NEW**

Ajouter une exigence explicite:

```md
- Tests d'integration backend obligatoires:
  - couvrir le chemin legacy `excludedObjects -> getFullTopology() -> /action/sync -> /system/published_scope`
  - verifier que le fallback piece legacy reste actif meme si `published_scope.pieces[*]` est present avec `raw_state = inherit` par defaut
  - prouver le remplacement du contrat backend persiste apres changement de configuration locale
```

**Rationale**

Le trou n'est pas dans l'intention produit. Il est dans la preuve d'integration de la story productrice.

### Artifact 2 — Story 1.2

**Story :** `1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend`  
**Section :** note de validation / blocage

**OLD**

Aucune note explicite ne trace l'echec terrain AC3 comme blocage amont.

**NEW**

Ajouter une note minimale, sans changer le scope de la story:

```md
## Validation Note

- Validation terrain du 2026-03-22: AC3 non validable tant que Story 1.1 ne remet pas a jour correctement le contrat backend `published_scope` sur le chemin legacy `excludedObjects`.
- L'UI 1.2 reste coherente avec le backend retourne; aucun recalcul frontend parasite n'a ete observe.
- Story 1.2 ne doit pas passer en `done` avant revalidation terrain apres correction de Story 1.1.
```

**Rationale**

On preserve une trace propre entre:

- la story **productrice backend** qui doit etre rouverte;
- la story **consommatrice UI** qui reste correcte mais bloquee pour cloture.

### Artifact 3 — sprint-status.yaml

**Section :** `development_status`

**OLD**

```yaml
development_status:
  epic-1: in-progress
  1-1-resolver-canonique-du-perimetre-publie: done
  1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend: review
```

**NEW**

```yaml
development_status:
  epic-1: in-progress
  1-1-resolver-canonique-du-perimetre-publie: in-progress
  # 1-2 validation terrain bloquee par la reouverture de 1-1 sur le contrat backend published_scope
  1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend: review
```

**Rationale**

- le modele de statut ne prevoit pas `blocked`;
- la modification minimale correcte est donc:
  - rouvrir la story productrice 1.1;
  - conserver 1.2 en `review` avec une note explicite de blocage amont.

### Artifact 4 — Aucun delta global requis

**PRD / UX / architecture / test strategy**

**Decision**

Ne pas modifier ces artefacts globaux.

**Rationale**

Ils portent deja les invariants corrects. Le delta utile se situe au niveau:

- de la story backend productrice 1.1;
- de la story consommatrice 1.2;
- du suivi sprint-status.

---

## Section 5 : Handoff recommande

### Classification de scope

**Moderate** — reorganisation de backlog legere par SM/PO, puis correction backend ciblee.

### Handoff recommande

1. **SM / PO**
   - approuver la reouverture de Story 1.1
   - appliquer la mise a jour minimale de Story 1.2 et de `sprint-status.yaml`

2. **Development**
   - travailler **uniquement** sur Story 1.1 rouverte
   - corriger la chaine backend `published_scope` sur le chemin legacy `excludedObjects`
   - etendre les tests d'integration/contrat pour fermer le trou reel observe

3. **Validation terrain / QA**
   - rejouer la validation terrain de Story 1.1
   - puis rejouer AC3 de Story 1.2 sur la meme chaine backend

### Prochain handoff recommande

**Sequence de handoff recommandee :**

1. appliquer les mises a jour documentaires minimales sur Story 1.1, Story 1.2 et `sprint-status.yaml`;
2. lancer une validation ciblee de Story 1.1 rouverte avec les exigences de tests ajoutees sur le chemin backend legacy;
3. seulement apres validation de cette reouverture documentaire et de ses exigences de preuve, lancer `dev-story` sur Story 1.1.

Note operationnelle explicite:

- tant que Story 1.1 est rouverte, Story 1.2 reste en `review` avec blocage amont;
- tant que Story 1.1 est rouverte, les stories dependantes **1.3** et **1.4** ne doivent pas avancer;
- Story 1.2 ne doit etre revalidee qu'apres fermeture du defect backend producteur.

---

## Resume executif

- **Decision recommandee:** rouvrir **1.1**, ne pas creer de nouvelle story corrective.
- **Pourquoi:** defaut de contrat backend deja attribue a 1.1 ; 1.2 est seulement la consommatrice bloquee.
- **Delta documentaire minimal:** Story 1.1, Story 1.2, `sprint-status.yaml`.
- **Aucun delta requis:** PRD, UX, architecture, test strategy globale.
- **Aucun dev lance dans ce proposal.**

---

*Genere par le workflow Correct Course en mode batch — 2026-03-22.*
