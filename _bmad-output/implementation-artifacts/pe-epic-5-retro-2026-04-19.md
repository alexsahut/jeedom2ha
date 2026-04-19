# Rétrospective pe-epic-5 — Les projections autorisées sont publiées vers HA avec un résultat technique traçable

**Date :** 2026-04-19
**Cycle :** Moteur de Projection Explicable
**Epic :** `pe-epic-5`
**Statut epic :** `done`
**Statut rétrospective :** clôturée

---

## Participants

- Alexandre (Project Lead)
- Bob (Scrum Master)
- Alice (Product Owner)
- Winston (Architect)
- Charlie (Senior Dev)
- Dana (QA Engineer)

---

## Résumé factuel de l'epic

- 2 stories livrées (`5.1` et `5.2`) — toutes `done` dans `sprint-status.yaml`
- Story 5.1 : orchestration canonique 5 étapes dans le sync handler — 426/426 tests PASS, PR #95 mergée
- Story 5.2 : résultat de publication traçable, séparation décision produit / résultat technique — 424/424 tests PASS
- 100% des action items de la rétro pe-epic-4 complétés (première fois dans le cycle)
- Findings review story 5.2 : 1 HIGH + 3 MEDIUM — corrigés dans la même session

---

## Suivi actions pe-epic-4 (rétro 2026-04-15)

| Action | Statut | Preuve |
|--------|--------|--------|
| AI-1 Ajouter l'intention dominante dans les artefacts | ✅ | `pe-epic-5-document-precedence.md`, `pe-epic-5-alignment-gate.md` |
| AI-2 Créer/maintenir un registre d'exceptions de gouvernance | ✅ | `pe-epic-5-governance-exceptions-register.md` (vivant) |
| AI-3 Exécuter un check d'alignement PRD/architecture/epics | ✅ | `pe-epic-5-alignment-gate.md` (gate bloquant validé) |
| AI-4 Règle backlog : toute non-ouverture référence GOV-PE5-xxx | ✅ | 6 IDs utilisés dans les 2 stories sans exception |

**Observation :** Première fois dans le cycle que 100% des action items d'une rétro sont complétés. Raison identifiée : les actions étaient concrètes et vérifiables, branchées sur l'exécution réelle, et adressaient la cause racine — pas juste les symptômes.

---

## Points de satisfaction

### 1. Pilotage produit réellement contrôlé

Pour la première fois dans le cycle, le cadre de pilotage posé en rétro pe-epic-4 a réellement structuré l'exécution :
- l'intention dominante était présente dans les stories,
- la gouvernance était explicitement branchée,
- plus aucun "hors scope implicite".

**Impact exprimé (Alexandre) :** on est passé d'un pilotage "intentionnel" à un pilotage réellement contrôlé.

### 2. Gouvernance devenue réflexe d'exécution

Les 6 IDs GOV-PE5-xxx référencés dans les 2 stories sans exception. Ce n'est plus un overhead : c'est un réflexe de delivery.

### 3. Qualité technique préservée malgré le recadrage

Invariants pipeline intacts, 426+424 tests, 0 régression, corrections post-review traitées dans la logique du problème. Le review a joué son rôle comme prévu.

**Note architect (Winston) :** rare de pouvoir absorber un layer de gouvernance sans ralentir ni dégrader l'engineering.

### 4. Fondations backend solides pour pe-epic-6

- Séparation décision produit / résultat technique propre et tenue
- `_build_traceability()` enrichi avec dimensions `decision_trace` et `publication_trace`
- Cause principale canonique préservée comme source de vérité exclusive des étapes 1-4

---

## Challenges et tensions

### Challenge 1 — Invariant I7 fragile dans `_build_traceability()`

**Constat :** 3 violations AC3/I7 détectées en review story 5.2 et corrigées dans la même session.

Les 3 dérives :
1. `reason_code` dérivait de `publication_result.technical_reason_code` au lieu de `canonical_dec.reason` (étape 4)
2. `_needs_discovery_unpublish()` marquait à tort des équipements "à dépublier" après un échec initial jamais publié (fallback `should_publish=True`)
3. `_build_traceability()` fallback retournait `"discovery_publish_failed"` comme cause canonique via `CLOSED_REASON_MAP`

**Lecture systémique (Alexandre) :** l'invariant I7 est conceptuellement clair — "étapes 1-4 dominent toujours" — mais il n'est pas encore suffisamment "guidant" dans le code. Trois portes ouvertes, trois dérives.

### Challenge 2 — Aliasing `publication_decision` / `publication_decision_ref`

**Constat :** ambiguïté contractuelle portée pendant toute l'epic. Pas de bug fonctionnel, mais dette de compréhension non résolue.

**Lecture systémique (Alexandre) :** le contrat était correct mais pas assez univoque pour être appliqué sans ambiguïté par tout dev entrant dans la zone.

### Lecture commune des deux challenges

> "Deux manifestations du même problème systémique : la frontière entre concepts est encore fragile dans l'implémentation. Le système qualité fonctionne — mais il compense des faiblesses de design qu'on peut améliorer." — Alexandre

---

## Insight clé

**De "correct mais fragile" à "structurellement sûr".**

Dans les deux cas (I7 et aliasing), on dépend encore de la vigilance humaine (review, QA) pour tenir le modèle. L'objectif pour la suite : rendre certaines erreurs impossibles, pas seulement détectables.

**Règle sur les action items (synthèse Alexandre) :** les action items qui tiennent sont ceux qui sont :
1. concrets et vérifiables,
2. branchés sur l'exécution réelle,
3. adressant la cause racine, pas le symptôme.

---

## Readiness pe-epic-5

| Dimension | Statut | Note |
|-----------|--------|------|
| Qualité code / review | ✅ | Corrections faites au bon endroit, filet tenu |
| Déploiement terrain | ✅ Validé | Run terrain du 2026-04-19 soldé sur box réelle ; voir `pe-epic-5-terrain-validation.md` |
| Validation finale (Alexandre) | ✅ Validée | Décision explicite Alexandre : gate terrain levé avec niveau de preuve réaliste |
| Santé technique | ✅ avec vigilance | Zone fragile identifiée, adressée par prep sprint |
| Bloqueurs | ✅ Non | Gate terrain levé ; readiness pe-epic-6 autorisée |

---

## Action items pe-epic-5

### AI-1 — Processus
Formuler les action items futurs selon les 3 critères validés : concrets et vérifiables, branchés sur l'exécution réelle, adressant la cause racine.
- **Owner :** Bob (facilitation)
- **Critère :** appliqué dès la formulation des AI de cette rétro

---

## Prep sprint pe-epic-6 — Gate de readiness (bloquant)

> Décision Alexandre : ce prep sprint est un gate de readiness pe-epic-6, pas une pré-phase optionnelle. Aucune story 6.x ne démarre tant que tous les critères ne sont pas soldés.

### P-1/P-2 [Livrable maître] — Contrat canonique de traceabilité + aliasing résolu
- **Owner :** Winston + Charlie
- **Scope :**
  - source de vérité unique de la cause canonique
  - rôle exact `publication_result` (étape 5 = technique uniquement)
  - rôle exact `publication_decision_ref` (alias contrat)
  - frontières décision / traceabilité / rendu diagnostic
  - aliasing supprimé ou rendu définitivement non ambigu
- **Livrable :** note contractuelle courte, opposable en review, intégrée aux artefacts de préséance documentaire
- **Gate out :** tout dev entrant dans `_build_traceability()` pour 6.x navigue sans ambiguïté

### P-3 — Tests de non-masquage I7 non permissifs
- **Owner :** Dana
- **Scope :**
  - cas cassants sur les 3 chemins de dérive identifiés en story 5.2
  - assertions échouant si cause canonique remplacée par `technical_reason_code`
  - assertions sur `_needs_discovery_unpublish()` fallback
  - assertions sur `_build_traceability()` fallback `CLOSED_REASON_MAP`
- **Gate out :** les 3 violations I7 de story 5.2 réintroduites font échouer la suite

### P-4 — Artefact visuel prescriptif pe-epic-6
- **Owner :** Alice
- **Scope :**
  - `cause_label`, `cause_action`, étape de pipeline visible en UI diagnostic
  - wireframe ou spec visuelle — surface UI diagnostic
  - couvre les cas des stories 6-1 et 6-3
- **Gate out :** artefact prêt avant `create-story` 6-1 et 6-3

---

## Critical path avant démarrage pe-epic-6

```
Parallèle :
  Charlie + Winston → P-1/P-2
  Dana             → P-3
  Alice            → P-4
  Alexandre        → Déploiement terrain pe-epic-5 + validation

Gate de readiness pe-epic-6 (tous bloquants) :
  ✅ P-1/P-2 soldés
  ✅ P-3 soldé
  ✅ P-4 soldé
  ✅ Déploiement terrain pe-epic-5 + validation Alexandre soldés selon niveau de preuve réaliste
```

**Source de vérité terrain :** `pe-epic-5-terrain-validation.md`

---

## Découverte significative — Impact sur pe-epic-6

pe-epic-6 planifié suppose que `_build_traceability()` est stable pour enrichissement direct. pe-epic-5 a démontré le contraire. Le prep sprint n'est pas optionnel : il sécurise la zone fragile avant exposition UI.

**Recommandation :** ne pas mettre à jour le plan de pe-epic-6 sur le fond — les stories sont correctes. Le gate de readiness est désormais levé ; démarrage autorisé.

---

## Mot de clôture (Alexandre)

> "Cet epic marque un vrai tournant dans la façon dont on travaille. On a prouvé qu'on est capable d'aligner pilotage, architecture et exécution. C'est probablement le point le plus important du cycle jusqu'ici. On est en train de passer d'un mode 'delivery rapide' à un mode delivery maîtrisé dans la durée. On valide pe-epic-5 en terrain, on sécurise le contrat et la traceabilité, et ensuite seulement on expose la valeur en UI avec pe-epic-6."

---

Bob (Scrum Master) : "Rétro clôturée. Les décisions de préparation sont explicites et tracées."
Alexandre (Project Lead) : "Validation confirmée : gate terrain pe-epic-5 levé le 2026-04-19 avec niveau de preuve réaliste ; GO pe-epic-6."
