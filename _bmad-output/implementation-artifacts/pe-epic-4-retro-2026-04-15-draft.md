# Rétrospective pe-epic-4 — Décision de publication explicite + contrat de non-régression

**Date :** 2026-04-15  
**Cycle :** Moteur de Projection Explicable  
**Epic :** `pe-epic-4`  
**Statut epic (sprint-status) :** `done`  
**Statut rétrospective :** clôturée

---

## Contexte et hypothèse d’exécution

Cette rétrospective cible `pe-epic-4`, car :
- `sprint-status.yaml` indique `last_updated: 2026-04-15` avec la note de clôture `pe-epic-4`.
- `pe-epic-4` est `done`.
- `pe-epic-4-retrospective` était encore `optional`.

Note : le même fichier contient aussi des epics historiques (`epic-1` à `epic-5`) déjà rétrospectivés. Pour éviter le mélange de cycles, cette rétro se limite au cycle Projection Engine.

---

## Participants

- Alexandre (Project Lead)
- Bob (Scrum Master)
- Alice (Product Owner)
- Winston (Architect)
- Charlie (Senior Dev)
- Dana (QA Engineer)

---

## Résumé de livraison

### Stories clôturées

| Story | Statut | Preuve de qualité / livraison |
|---|---|---|
| 4.1 — `decide_publication()` | done | 19/19 tests story, 384/384 non-régression, code review APPROVE |
| 4.2 — distinction diagnostic politique vs gouvernance | done (tracker) | gate terrain exécuté, 175 tests JS + 928 tests Python + tests PHP PASS |
| 4.3 — migration additive reason codes AR8 | done | 31/31 tests story, 940/940 non-régression, code review APPROVE |
| 4.4 — suite invariants pipeline | done | 10 tests invariants + 76 tests pipeline ciblés PASS, aucun changement de prod |

### Métriques consolidées (preuves disponibles)

- Epic `pe-epic-4` : 4/4 stories `done`.
- PR de clôture epic : `#90` mergée (trace sprint-status).
- Non-régression conservée sur toutes les stories de l’epic.
- Contrat pipeline renforcé : invariants I1–I7 explicitement testés.

---

## Ce qui a bien marché

### 1) Frontières techniques nettes par story

Chaque story est restée dans un périmètre précis (4.1 décision, 4.2 surface diagnostic, 4.3 catalogue reason codes, 4.4 invariants transverses). Résultat : ajout progressif sans régression structurelle.

### 2) Qualité de test élevée et cumulative

Le pattern "story-level + non-régression globale" a tenu sur tout l’epic. La preuve de robustesse est visible dans les suites cumulées (384, 928, 940), sans baisse de garde.

### 3) Distinction métier utile rendue visible

La séparation `low_confidence` (politique produit) vs `ha_component_not_in_product_scope` (gouvernance) est devenue lisible côté diagnostic utilisateur, pas seulement correcte côté backend.

### 4) Continuité architecture → implémentation

Les décisions de `architecture-projection-engine.md` et `pipeline-contract.md` ont été appliquées concrètement, notamment AR9 (étape 4 ne revalide pas HA) et la causalité canonique ordonnée.

### 5) Gouvernance des changements sensible au risque

La migration additive de reason codes (4.3) a été traitée avec snapshot de baseline et tests anti-contrat, ce qui réduit fortement le risque de casse silencieuse.

---

## Ce qui a été difficile

### 1) Cohérence documentaire de statut

Le tracker sprint indique 4.2 `done`, mais le fichier story 4.2 est encore marqué `Status: review`. La livraison est effective, mais la traçabilité documentaire reste ambiguë.

### 2) Story 4.4 reconstruite a posteriori

La story 4.4 documente une implémentation déjà réalisée. Cela n’impacte pas la qualité technique, mais réduit la lisibilité process et l’auditabilité du flux de décision.

### 3) Dette de typage M2 toujours vivante

La dette `capabilities: object` vs `MappingCapabilities` (identifiée en pe-epic-3) reste explicitement documentée, sans signal clair de clôture dans les artefacts 4.x.

---

## Continuité avec la rétro pe-epic-3

| Action item pe-epic-3 | Attendu | Statut dans pe-epic-4 | Preuve |
|---|---|---|---|
| AI-1 — Artefact pipeline partagé | prérequis absolu avant pe-epic-4 | ✅ Complété | `pipeline-contract.md` (2026-04-14) + architecture PE |
| AI-2 — Checkpoint contrat `cause_mapping` | avant story 4.3 | ✅ Complété | story 4.3 Task 0 + snapshot + anti-contrats |
| AI-3 — Qualifier story 4.2 | backend-only vs surface critique | ✅ Complété | story 4.2 traitée en surface critique, artefact + gate |
| AI-4 — Documenter M2 dette vivante | borne claire + non-aggravation | ⏳ En cours | dette rappelée, clôture non explicitée dans 4.x |
| AI-5 — Spécifier les bords du contrat dans 4.x | cas limites + anti-contrats | ✅ Complété | story 4.1 et 4.4 (invariants, anti-contrats) |

---

## Insights clés

1. Le cycle PE gagne en fiabilité quand chaque étape du pipeline est testée comme contrat autonome.
2. La qualité perçue utilisateur dépend autant de la traduction diagnostic que de la justesse moteur.
3. Le dispositif de non-régression a atteint un niveau mature (tests d’invariants + snapshots + suites globales).
4. Les principaux risques restants sont surtout de gouvernance documentaire et de dette explicitement assumée, pas de stabilité fonctionnelle immédiate.

---

## Préparation de pe-epic-5

## Preview du prochain epic

**Epic suivant :** `pe-epic-5` (backlog)  
**Objectif :** publication orchestrée des projections autorisées + résultat technique traçable (`FR26` à `FR30`).

### Dépendances déjà sécurisées par pe-epic-4

- Étape 4 contractualisée (`decide_publication`) avec causalité explicite.
- Distinction diagnostique politique/gouvernance disponible.
- Catalogue reason codes classe 2/3 aligné et stable.
- Corpus de tests invariants pipeline établi.

### Préparation recommandée avant démarrage effectif

- Valider un checklist de démarrage Epic 5 basé sur les invariants 4.4.
- Encadrer explicitement la séparation "cause décisionnelle" vs "résultat technique publication" pour éviter toute confusion dans l’orchestration runtime.
- Réconcilier les statuts documentaires restants (notamment story 4.2) avant d’empiler de nouvelles couches.

---

## Action items issus de la rétro

### Process / Gouvernance

1. **Aligner le statut documentaire de la story 4.2**  
   **Owner :** Bob (Scrum Master)  
   **Succès :** fichier story 4.2 cohérent avec `sprint-status` (`done`) et références de preuve inchangées.

2. **Normaliser la traçabilité des stories reconstruites a posteriori**  
   **Owner :** Bob (Scrum Master) + Alexandre (Project Lead)  
   **Succès :** convention écrite appliquée (section "implémentation préalable" + preuve exécution + décision explicite).

### Technique / Qualité

3. **Fermer explicitement AI-4 (dette M2) ou formaliser sa condition de fermeture**  
   **Owner :** Winston (Architect) + Charlie (Senior Dev)  
   **Succès :** note de décision unique indiquant périmètre, non-aggravation, et critère de réalignement.

4. **Ajouter une gate d’intégration Epic 5 orientée FR27/FR30**  
   **Owner :** Dana (QA Engineer) + Charlie (Senior Dev)  
   **Succès :** cas validé où un incident de publication n’écrase jamais la cause décisionnelle canonique.

5. **Préparer une fixture terrain ciblée pour les cas de refus étape 4**  
   **Owner :** Dana (QA Engineer)  
   **Succès :** jeu de validation reproductible couvrant au minimum `low_confidence` et `ha_component_not_in_product_scope` sur la surface diagnostic.

---

## Chemin critique vers pe-epic-5

1. Cohérence documentaire pe-epic-4 finalisée (`story 4.2` + métadonnées de clôture).
2. Clarification officielle de la dette M2 (fermée ou strictement bornée).
3. Plan de test d’intégration Epic 5 validé (décision vs publication technique).
4. Démarrage story 5.1 avec garde-fous invariants déjà actifs (4.4).

---

## Détection de changements significatifs

**Conclusion : pas de changement de fond imposant une réécriture d’Epic 5.**

Le plan Epic 5 reste valide tel que défini. Les ajustements nécessaires sont de préparation et de gouvernance d’exécution, pas de redéfinition de contenu.

---

## Readiness finale pe-epic-4

| Dimension | Statut | Commentaire |
|---|---|---|
| Complétude stories | ✅ | 4/4 stories done dans le tracker |
| Qualité tests | ✅ | suites story + non-régression globales PASS |
| Stabilité contrat pipeline | ✅ | invariants I1–I7 couverts |
| Diagnostic utilisateur | ✅ | distinction politique/gouvernance livrée |
| Cohérence documentaire | 🟡 | divergence de statut story 4.2 à corriger |
| Dette technique héritée (M2) | 🟡 | documentée, fermeture non explicitée |
| Préparation pe-epic-5 | ✅ conditionnelle | prête après clôture des points process/AI-4 |

**Décision de readiness :** `pe-epic-4` est clôturable et `pe-epic-5` peut démarrer dès que les points conditionnels ci-dessus sont fermés.

---

## Clôture

Bob (Scrum Master): "La base technique est solide et l’epic est livré proprement. Notre levier d’amélioration principal est maintenant la rigueur de clôture documentaire et la discipline de passage vers l’orchestration Epic 5."  
Alice (Product Owner): "La valeur utilisateur progresse clairement : le diagnostic est plus explicable, et le risque de confusion diminue."  
Charlie (Senior Dev): "On garde le cap : contrats stables, anti-contrats testés, et intégration Epic 5 sans court-circuit."  
Alexandre (Project Lead): "Rétro clôturée. Passage vers pe-epic-5 validé sous conditions explicites."
