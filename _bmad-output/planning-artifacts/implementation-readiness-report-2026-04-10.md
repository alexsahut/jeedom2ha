---
type: implementation-readiness-gate
cycle: moteur-de-projection-explicable
date: '2026-04-10'
author: Alexandre
verdict: READY
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/architecture-delta-review-prd-final.md
  - _bmad-output/implementation-artifacts/epic-5-retro-2026-04-09.md
  - _bmad-output/project-context.md
previousReportsExcluded: true
note: >
  Ce gate est ciblé sur le nouveau cycle "moteur de projection explicable".
  Les readiness reports V1.1 de mars (2026-03-12, 2026-03-13, 2026-03-22, 2026-03-27)
  ne sont pas réutilisés — ils couvrent un périmètre différent.
---

# Readiness Gate — Cycle Moteur de Projection Explicable

**Date :** 2026-04-10
**Projet :** jeedom2ha
**Cycle :** Moteur de projection explicable (post-V1.1)
**Objectif du gate :** Vérifier si les artefacts sont suffisamment alignés et fermes pour lancer `/bmad-create-epics` sans relancer un workflow UX.

---

## Inventaire documentaire analysé

| Artefact | Date | Statut déclaré | Rôle dans le gate |
|---|---|---|---|
| `product-brief-jeedom2ha-2026-04-09.md` | 2026-04-09 | `complete` | Vision, problem statement, success metrics, user journeys |
| `prd.md` | 2026-04-09, édité 2026-04-10 | `complete` | 45 FR (F0–F8) + 12 NFR auditables |
| `architecture-projection-engine.md` | 2026-04-09 | `complete` | 8 décisions (D1–D8) + 8 patterns (P1–P8) |
| `architecture-delta-review-prd-final.md` | 2026-04-10 | `delta-mineur, blocksEpics: false` | Réconciliation PRD final → Architecture |
| `epic-5-retro-2026-04-09.md` | 2026-04-09 | clôturée | Origine des action items AI-1/AI-2/AI-3, baseline V1.1 |
| `project-context.md` | 2026-03-15 | `complete` | Stack, patterns, règles d'implémentation |

**Note sur AI-3 :** la rétrospective Epic 5 posait comme "condition bloquante" qu'aucune story du prochain cycle ne peut être créée avant que le modèle canonique du moteur de projection soit validé. Ce prérequis est **satisfait** — `architecture-projection-engine.md` constitue exactement cet artefact.

---

## Point 1 — Cohérence Product Brief → PRD → Architecture

### Chaîne de dérivation

La chaîne n'est pas strictement linéaire mais elle est cohérente et traçable :

1. `epic-5-retro` → produit `architecture-projection-engine.md` (AI-3)
2. `architecture-projection-engine.md` + `epic-5-retro` → alimentent `product-brief-jeedom2ha-2026-04-09.md`
3. `product-brief-2026-04-09` + `architecture-projection-engine.md` → alimentent `prd.md`
4. `prd.md` (édition 2026-04-10) → réconcilié par `architecture-delta-review-prd-final.md`

L'architecture a précédé le Product Brief final et le PRD — c'est un ordering atypique mais valide. L'architecture a été produite directement depuis la rétrospective Epic 5 et les artefacts V1.1 existants. Le PRD a ensuite explicitement inclus l'architecture comme input document (`inputDocuments` dans le frontmatter).

### Cohérence substantielle

| Concept structurant | Product Brief | PRD | Architecture | Aligné ? |
|---|---|---|---|---|
| Pipeline 5 étapes canoniques | ✅ Positionné | ✅ F0 (FR1–5) + features 1–5 | ✅ Diagramme + D1/D7 | ✓ |
| Paradigme shift "closed-scope → coverage-by-validity" | ✅ Core Vision | ✅ Executive Summary + FR38/FR39 | ✅ § Changement de paradigme | ✓ |
| Registre HA séparé du mapping | ✅ Mentionné | ✅ F7 (FR36–40) | ✅ D2/D3 + PRODUCT_SCOPE | ✓ |
| Validation HA obligatoire étape 3 | ✅ Key Differentiator | ✅ F3 (FR16–20) + contraintes | ✅ D4 + P1 invariant | ✓ |
| Diagnostic explicable actionnable | ✅ Situation 2 + KPIs | ✅ F6 (FR31–35) + NFR3/4 | ✅ D8 + reason_code classes | ✓ |
| Contrat 4D V1.1 préservé | ✅ Acquis verrouillés | ✅ FR34 + NFR7 | ✅ § Fondations acquises | ✓ |
| Rétrocompatibilité reason_code | ✅ Implicite | ✅ FR43/44 + NFR8 | ✅ D5 + migration additive | ✓ |
| Overrides avancés post-MVP | ✅ Phase 2 | ✅ FR25 = post-MVP | ✅ D6 différé | ✓ |
| Stack inchangé | — | ✅ Contraintes techniques | ✅ "Stack inchangé" explicite | ✓ |
| AI-1/AI-2 différés | — | ✅ Capacités post-MVP | ✅ Items 12/13 ouverts | ✓ |

**Cohérence : FORTE. Aucun concept du Product Brief n'est absent du PRD ni de l'architecture. Aucune contradiction entre les trois artefacts.**

### Seule tension relevée

La tension n'est pas une incohérence mais un positionnement complémentaire : l'architecture décrivait initialement le `PRODUCT_SCOPE` comme une liste fixe `["light", "cover", "switch"]`, tandis que le PRD (FR38/FR39/FR40) le repositionne comme une frontière gouvernée-ouverte. Cette tension est explicitement résolue par la `architecture-delta-review-prd-final.md` (Point 2 ci-dessous).

---

## Point 2 — Statut du delta PRD → Architecture : non bloquant

### Verdict de la revue delta

Le document `architecture-delta-review-prd-final.md` (frontmatter : `verdict: delta-mineur`, `blocksEpics: false`) identifie **4 deltas**, tous de nature contractuelle ou de gouvernance, aucun de nature architecturale.

| Delta | Nature | Résolution |
|---|---|---|
| **D1** — Registre HA : 3 états (connu/validable/ouvert) vs 2 états dans l'architecture | Précision contractuelle | Modèle 3 états verrouillé dans la revue — devient le contrat de référence pour les stories |
| **D2** — Étape 4 : hiérarchie formelle (validité HA = étape 3 exclusive ; étape 4 = arbitrage publication uniquement) | Clarification de périmètre | Contrat formel court rédigé — two distinct reasons for `should_publish=False` nommées |
| **D3** — NFR auditables : NFR10 seul invariant nouveau | Invariant de processus de cycle | Couvert par FR39/FR40 — pas de nouveau code |
| **D4** — PRODUCT_SCOPE : frontière governed-open, valeur de départ non plafond | Précision de gouvernance | Règle de mutation via FR40 — pas de refonte D3 |

**Les décisions D1–D8 et les patterns P1–P8 de l'architecture restent inchangés.**

L'item 14 de l'architecture ("Extension du registre scope produit — quels composants ouvrir, dans quel ordre, avec quelles conditions") était la seule décision ouverte susceptible de bloquer le découpage. Elle est **explicitement fermée** par FR39/FR40 dans la revue delta. La conclusion de la revue est sans ambiguïté : *"Le cycle peut avancer vers `bmad-create-epics` sans condition préalable."*

**Statut : DELTA MINEUR, NON BLOQUANT. Confirmé par la revue delta formelle.**

---

## Point 3 — Suffisance des FR/NFR pour le découpage en epics/stories testables

### Couverture fonctionnelle

Le PRD contient **45 exigences fonctionnelles** organisées en **9 Features** (F0–F8) et **12 exigences non fonctionnelles** (NFR1–12).

**Structure des Features et testabilité intrinsèque :**

| Feature | FRs | Testabilité | Observation |
|---|---|---|---|
| F0 — Contrat global pipeline | FR1–5 | Fondation de toutes les autres | Ordre canonique testable par exécution du corpus de non-régression |
| F1 — Éligibilité (étape 1) | FR6–10 | Complète | FR10 auditable : étape 1 comme point de blocage + motif + action scope |
| F2 — Mapping candidat (étape 2) | FR11–15 | Complète | FR12 (niveau de confiance), FR13 (échec de mapping) = cas nominaux distincts |
| F3 — Validation HA (étape 3) | FR16–20 | Complète | FR19 = gate dur, testable par assertion `should_publish == False` sur cas invalides |
| F4 — Décision publication (étape 4) | FR21–25 | Complète | FR24 = critère de distinguabilité testable (deux reason_codes distincts dans diagnostic) |
| F5 — Publication MQTT (étape 5) | FR26–30 | Complète | FR28 = distinction échec infra / refus moteur testable |
| F6 — Diagnostic explicable | FR31–35 | Complète | FR31 auditable (4 champs minimum), FR32 auditable (cause_label toujours renseigné) |
| F7 — Registre HA et gouvernance | FR36–40 | Complète | FR39/40 = critères d'ouverture testables en isolation |
| F8 — Validation, testabilité, rétrocompat. | FR41–45 | Transverse | FR44 auditable (schéma stable), NFR9 (cas nominal + cas d'échec par étape) |

**Carte de dépendances (explicite dans le PRD) :**
- F0 → fondation de tout
- F1 → conditionne F2
- F2 → conditionne F3
- F7 → alimente F3 et F4
- F3 → conditionne F4
- F4 → conditionne F5
- F6 → dépend de F0–F5
- F8 → transverse sur F1–F7

Cette carte est directement exploitable pour l'ordering des épics.

### Couverture non fonctionnelle

Les 12 NFRs ont été rendues auditables le 2026-04-10 avec des critères "vérifié par..." explicites :

- **NFR1** (déterminisme 100%) → exécution répétée du corpus de non-régression
- **NFR2** (0% publications avec validation HA négative) → tests couvrant cas positifs et négatifs
- **NFR3** (100% équipements avec résultat explicite) → Pattern P1 trace complète
- **NFR4** (cause principale unique) → invariant d'évaluation ordonnée
- **NFR5** (composants ouverts satisfont les contraintes structurelles) → validation payloads de référence
- **NFR6** (0 source de vérité concurrente) → revue artefacts + tests depuis données Jeedom uniquement
- **NFR7** (4D rétrocompatible 100%) → comparaison schéma + comportement V1.1
- **NFR8** (0 reason_code renommé/supprimé) → diff catalogue codes + tests non-régression
- **NFR9** (5 étapes × cas nominal + cas d'échec) → vérification coverage à chaque livraison
- **NFR10** (ouverture composant = tests dans le même incrément) → invariant de processus
- **NFR11** (0 régression corpus non-régression avant acceptation) → gate CI
- **NFR12** (schéma diagnostic stable) → contrôles de schéma automatisés

**Chaque NFR est vérifiable. Aucune NFR n'est vague ou sans critère d'acceptation.**

### Capacité à produire des stories testables

Les FRs suivent systématiquement le format "Le système **peut** ..." / "L'utilisateur **peut** ..." / "Le mainteneur **peut** ...", ce qui ancre chaque FR dans un comportement observable. Couplé aux décisions architecturales D1–D8 qui précisent pour chaque décision un "Testable par :", le niveau de précision est suffisant pour rédiger des stories avec acceptance criteria concrets sans nécessiter de clarification a priori.

**Suffisance : CONFIRMÉE. 45 FR + 12 NFR auditables + carte de dépendances + guidance architecturale par décision = structure suffisante pour un découpage en epics/stories testables.**

---

## Point 4 — Aucun artefact UX supplémentaire requis avant epics

### Analyse

Le cycle "moteur de projection explicable" est fondamentalement un cycle de **couche backend et diagnostic** — il ne crée pas de nouvelles surfaces d'interface ni n'en restructure d'existantes.

Les éléments qui auraient pu justifier un workflow UX dédié :

| Question | Réponse |
|---|---|
| Nouvelles pages ou nouveaux écrans ? | Non — le cycle enrichit le diagnostic existant de façon additive |
| Nouveau paradigme d'interaction utilisateur ? | Non — l'utilisateur interagit toujours avec la même vue diagnostic 4D |
| Restructuration de l'UI existante ? | Non — l'architecture dit explicitement "Stack inchangé", D8 est un ajout de champ dans `_build_traceability()` |
| Décisions de présentation non résolues ? | Non — le contrat "le backend calcule, le frontend affiche sans interpréter" est hérité de V1.1 et maintenu (FR34, NFR7) |
| FRs d'affichage ambiguës ? | Partiellement — FR10, FR18, FR24, FR31, FR32 décrivent des exigences d'affichage, mais elles sont suffisamment précises et ancrées dans le contrat 4D pour être portées comme acceptance criteria de story sans UX préalable |

**Les FRs d'affichage (FR10, FR18, FR24, FR31, FR32) sont réalisables dans les stories Feature 6 en s'appuyant sur les patterns existants V1.1.** Elles ne demandent pas de décisions de conception UX nouvelles — elles explicitent comment étendre le diagnostic existant.

Le document UX de référence V1.1 (`ux-spec.md` + `ux-design-specification.md`) sert de baseline pour les composants UI existants. Les stories Feature 6 devront y référer pour les patterns de rendu du tableau diagnostic, mais cela n'exige pas de produire un nouvel artefact UX.

**Verdict : AUCUN artefact UX supplémentaire requis avant le découpage en epics.** Les stories Feature 6 porteront elles-mêmes les précisions d'affichage nécessaires dans leurs acceptance criteria et dev notes.

---

## Point 5 — Points à porter comme acceptance criteria dans les stories

Ces points ne modifient pas l'architecture. Ils doivent figurer explicitement dans les stories correspondantes. Ils sont classés par feature cible.

### 5.1 — Feature 7 : Registre HA et gouvernance (stories "ouverture composant")

**AC obligatoire pour toute story qui ajoute un composant dans `PRODUCT_SCOPE` :**

> Condition d'ouverture = FR40 (les trois conditions doivent être satisfaites **simultanément dans le même incrément**) :
> 1. Contraintes du composant définies dans `HA_COMPONENT_REGISTRY` (état `connu`)
> 2. `validate_projection()` aboutit positivement sur des cas nominaux représentatifs (état `validable`)
> 3. Tests de non-régression sur le contrat 4D passent sans régression (état `ouvert` autorisé)
>
> Un composant ne peut pas être marqué `ouvert` en dette de tests — les tests sont requis dans la même PR.

**AC sur les invariants de test des 3 états :**
> Les états `connu` / `validable` / `ouvert` doivent être distinguables en isolation :
> - un composant est `connu` si une entrée existe dans `HA_COMPONENT_REGISTRY` ;
> - un composant est `validable` si `validate_projection()` retourne `is_valid=True` sur le cas nominal défini ;
> - un composant est `ouvert` si et seulement si les 3 conditions ci-dessus sont satisfaites et qu'il figure dans `PRODUCT_SCOPE`.

**Sur `PRODUCT_SCOPE` :**
> La valeur de départ est `["light", "cover", "switch"]` (héritage V1.1). Ce n'est pas un plafond — tout composant `validable` du registre satisfaisant FR40 dans ce cycle peut y être ajouté. L'item 14 de l'architecture est clos : les conditions d'ouverture sont FR40, elles s'appliquent immédiatement.

### 5.2 — Feature 4 : Étape 4 — Décision de publication

**AC sur l'invariant d'ordre (issu de D7) :**
> Toute assertion sur `publication_decision.should_publish` en étape 4 doit partir d'un cas où `projection_validity.is_valid` est déjà calculé (positif ou négatif). L'étape 4 ne revalide pas la projection HA — cette question a une réponse définitive à l'issue de l'étape 3.

**AC sur la distinguabilité des deux raisons de refus (FR24) :**
> Le diagnostic doit permettre à l'utilisateur de distinguer :
> - `low_confidence` → politique produit (confiance du mapping insuffisante pour publier) — `cause_label` : variante de "Mapping trop incertain pour publier"
> - `ha_component_not_in_product_scope` → gouvernance d'ouverture (composant `validable` mais pas encore `ouvert` dans ce cycle) — `cause_label` : "Type d'entité non supporté dans cette version"
>
> Ces deux `cause_label` doivent être différents et stables. Cas de test obligatoire pour chacun.

**AC sur les overrides avancés (FR25) :**
> Les overrides avancés (forcer un type HA, publier malgré confiance insuffisante) sont **post-MVP**. Aucun code relatif aux overrides inter-étapes ne doit être produit dans ce cycle. La story ne doit pas laisser d'API ni de hook implicite pour ce futur.

### 5.3 — Feature 0 + Feature 3 : Pipeline et validation HA — invariant de trace complète

**AC sur le pattern P1 (trace complète sans court-circuit) :**
> Pour tout équipement qui passe le pipeline, le `MappingResult` doit toujours contenir :
> - `mapping` (sous-bloc étape 2 — présent même si mapping échoué, avec `reason_code`)
> - `projection_validity` (sous-bloc étape 3 — présent même si mapping échoué, avec `is_valid=None` et `reason_code="skipped_no_mapping_candidate"`)
> - `publication_decision` (sous-bloc étape 4 — présent toujours, avec `should_publish=False` si une étape précédente a échoué)
>
> Le test suivant doit passer pour tout équipement soumis au pipeline, y compris en cas d'échec d'étape :
> `assert mapping_result.projection_validity is not None`
> `assert mapping_result.publication_decision is not None`

### 5.4 — Feature 6 : Diagnostic explicable — stabilité du contrat

**AC sur la stabilité du contrat diagnostic (FR44 + NFR12) :**
> Les champs canoniques du diagnostic par équipement (`reason_code`, `cause_code`, `cause_label`, `cause_action`, étape de pipeline, statut de projection) doivent rester stables entre les tests de non-régression V1.1 et cette livraison, sauf ajouts additifs documentés. Un diff de schéma automatisé sur le corpus V1.1 doit passer sans régression destructive.

**AC sur la complétude de `cause_label` / `cause_action` (FR32) :**
> - `cause_label` doit être renseigné pour **100%** des équipements traités par le pipeline (y compris les inéligibles et les cas d'échec infrastructure).
> - `cause_action` doit être renseigné **uniquement** lorsqu'une remédiation utilisateur existe, et être `null` / absent sinon.
> - `cause_action` absent ne doit pas produire d'erreur côté UI.

### 5.5 — Feature 8 + transverse : Testabilité par étape et gate terrain

**AC sur les cas de test minimaux par étape (NFR9) :**
> Chacune des 5 étapes doit disposer, dans la suite pytest de référence, d'au moins :
> - 1 cas nominal (étape passe avec le résultat attendu) ;
> - 1 cas d'échec (étape bloque avec le reason_code attendu).
>
> Ces tests doivent être exécutables **en isolation** (sans daemon, sans MQTT, sans Jeedom connecté).

**AC sur les comportements plateforme Jeedom (AI-2 — transverse) :**
> Pour toute story avec gate terrain, les comportements Jeedom susceptibles d'interférer avec la validation terrain (auto-sync daemon au démarrage, délais `event::changes`, ordre d'initialisation) doivent figurer dans les **dev notes** ou les **conditions préalables du gate terrain** de la story, et non être découverts pendant le gate.

---

## Synthèse des cinq points

| Point | Analyse | Statut |
|---|---|---|
| 1 — Cohérence Product Brief → PRD → Architecture | Chaîne traçable, alignement substantiel fort sur tous les concepts structurants. Aucune contradiction. | ✅ Solide |
| 2 — Delta PRD → Architecture non bloquant | Revue delta explicite. 4 deltas mineurs — contractuels/gouvernance, aucun architectural. D1–D8 inchangés. Item 14 clos. Verdict de la revue : "peut avancer vers epics sans condition préalable". | ✅ Confirmé |
| 3 — Suffisance FR/NFR | 45 FR auditables + 12 NFR avec critères "vérifié par..." + carte de dépendances + guidance architecturale par décision. Structure suffisante pour stories testables. | ✅ Suffisant |
| 4 — Pas d'artefact UX supplémentaire | Cycle couche backend + diagnostic additif. Contrat 4D préservé. Pas de nouvelle surface UI. FRs d'affichage portables comme acceptance criteria de story. | ✅ Confirmé |
| 5 — Points à porter en AC | 5 blocs d'acceptance criteria identifiés, ciblés par feature, directement exploitables pour `/bmad-create-epics`. | ✅ Rédigés |

---

## Conclusion

### VERDICT : ✅ READY

**Les artefacts sont suffisamment alignés et fermes pour lancer `/bmad-create-epics` immédiatement.**

Les conditions nécessaires sont remplies :
- La vision (Product Brief) est ferme et cohérente avec le PRD et l'architecture.
- L'architecture est techniquement stable (D1–D8, P1–P8 inchangés), avec toutes les décisions critiques actées.
- Le PRD couvre le périmètre fonctionnel et non fonctionnel avec une précision suffisante pour des stories testables.
- Le delta entre PRD et architecture est mineur et non bloquant — les 4 précisions nécessaires sont rédigées et exploitables directement comme acceptance criteria.
- Aucun workflow UX intermédiaire n'est requis.
- L'obligation AI-3 de la rétrospective Epic 5 (modèle canonique du moteur de projection comme prérequis absolu) est satisfaite par `architecture-projection-engine.md`.

**Prochaine action : `/bmad-create-epics`**

Le découpage doit s'appuyer sur :
- Les Features F0–F8 comme frontières naturelles d'épics (F0 = fondation transverse à livrer en premier).
- La carte de dépendances du PRD pour l'ordering.
- Les 5 blocs d'acceptance criteria du Point 5 de ce gate pour les stories correspondantes.
- La valeur de départ `PRODUCT_SCOPE = ["light", "cover", "switch"]` comme baseline, avec la règle FR40 comme mécanisme d'extension gouverné.

**Ce qui est hors scope de ce cycle (ne pas intégrer dans les epics) :**
- Overrides avancés inter-étapes (FR25 = post-MVP).
- Flux système opérationnel externalisé AI-1 (post-MVP).
- Drill-down niveau commande (Backlog Icebox).
- Preview complète de publication (Frontière C).
- Alignement Homebridge (Frontière D).
