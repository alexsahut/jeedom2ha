# Rétrospective pe-epic-4 — Décision explicite et diagnostic exploitable

**Date :** 2026-04-15  
**Cycle :** Moteur de Projection Explicable  
**Epic :** `pe-epic-4`  
**Statut epic :** `done`  
**Statut rétrospective :** clôturée

---

## Participants (atelier interactif)

- Alexandre (Project Lead)
- Bob (Scrum Master)
- Alice (Product Owner)
- Winston (Architect)
- Charlie (Senior Dev)
- Dana (QA Engineer)

---

## Résumé factuel de l’epic

- 4 stories livrées (`4.1` à `4.4`) et marquées `done` dans `sprint-status.yaml`.
- Consolidation des invariants pipeline et non-régression confirmée sur les suites de tests.
- Distinction diagnostic politique produit vs gouvernance d’ouverture effectivement livrée.

---

## Points de satisfaction (Alexandre)

### 1) Socle backend propre, explicable, stable

- Séparation claire des étapes : mapping / validation / décision / publication.
- Cause principale canonique respectée.
- Invariants pipeline solides et testés.

**Impact exprimé :** on peut expliquer un non-publié sans lire le code et sans ambiguïté.

### 2) Décision de publication devenue un objet produit clair

- La publication n’est plus un effet de bord du mapping.
- La décision est isolée, avec ses règles et sa traçabilité.

**Exemple exprimé :** équipement mappé + valide HA, mais bloqué explicitement par policy/scope.

### 3) Diagnostic structuré et exploitable

- Distinction claire entre `reason_code` backend et lecture utilisateur.
- Migration additive sans casse.
- Base de diagnostic actionnable pour support et industrialisation.

**Synthèse exprimée :** epic très solide, opacité historique largement éliminée.

---

## Axe d’amélioration principal (Alexandre)

### Risque systémique identifié

Risque de désalignement entre :
- intention produit,
- architecture,
- backlog d’exécution.

Le moteur peut être cohérent techniquement, mais la trajectoire produit peut rester ambiguë si les artefacts intermédiaires ne portent pas la même intention.

### Pré-requis avant pe-epic-5

Pré-requis principal = pilotage (pas code) :
- clarifier noir sur blanc l’intention dominante du cycle,
- vérifier cohérence PRD / architecture / epics,
- ne démarrer la suite qu’après preuve d’alignement.

---

## Décision directrice actée en séance

**Intention dominante du cycle (validée) :**

> Ouvrir tout composant HA proprement mappable, structurellement validable et non bloqué par une exception de gouvernance explicitement décidée, justifiée et tracée.

### Règle d’arbitrage associée

- Par défaut : on ouvre.
- Si on n’ouvre pas : la dérogation doit être explicitement motivée, localisée dans les artefacts, et traçable.

---

## Actions de clôture validées

1. Ajouter l’intention dominante dans les artefacts de pilotage du cycle (pas uniquement dans l’implémentation).
2. Créer/maintenir un registre explicite des exceptions de gouvernance (motif, décision, source, traçabilité).
3. Exécuter un check d’alignement PRD / architecture / epics avant pe-epic-5.
4. Poser une règle backlog : toute non-ouverture doit référencer une exception de gouvernance tracée.

---

## Précisions opératoires validées

1. **Preuve d’alignement explicite et partageable**
   - artefact court accepté,
   - doit couvrir : intention produit, exceptions actives, cohérence PRD/architecture/epics, absence de scope caché non tracé.

2. **Registre d’exceptions vivant et contrôlable**
   - consultable en review et en préparation de story,
   - pas une note statique hors du flux.

---

## Gate de démarrage pe-epic-5 (décision)

**Décision validée :**

- `pe-epic-5` est **bloqué** tant que la preuve d’alignement n’est pas produite et validée.
- Tant que ce gate n’est pas passé, `pe-epic-5` n’est pas considéré prêt au démarrage.

---

## Readiness finale

- `pe-epic-4` : clôturé.
- `pe-epic-5` : prêt **conditionnellement** au passage du gate d’alignement ci-dessus.

---

Bob (Scrum Master): "Rétro clôturée. Les décisions de pilotage sont explicites et traçables."  
Alexandre (Project Lead): "Validation confirmée : pas de démarrage pe-epic-5 sans preuve d’alignement."  
