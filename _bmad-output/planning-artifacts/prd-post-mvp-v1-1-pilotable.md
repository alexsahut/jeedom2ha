---
workflowType: 'prd'
workflow: 'edit'
project: 'jeedom2ha'
phase: 'post_mvp_phase_1'
version_label: 'v1.1_pilotable'
date: '2026-03-26'
status: 'ready_for_epic_planning'
source_prd: '_bmad-output/planning-artifacts/prd.md'
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-post-mvp-refresh.md
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/project-context.md
  - _bmad-output/planning-artifacts/prd-validation-report.md
stepsCompleted:
  - step-e-01-discovery
  - step-e-02-review
  - step-e-03-edit
lastEdited: '2026-03-26'
editHistory:
  - date: '2026-03-26'
    changes: 'Recadrage UX V1.1 — intégration du modèle utilisateur Périmètre/Statut/Écart/Cause, disparition du concept exception, confiance en diagnostic technique uniquement, diagnostic centré in-scope, distinction reason_code/cause_code.'
  - date: '2026-03-22'
    changes: 'Update structurant post-MVP: recentrage produit sur V1.1 Pilotable et priorisation pilotage/ops avant extension du scope.'
---

# PRD Update - jeedom2ha Post-MVP Phase 1 (V1.1 Pilotable)

## 1. Executive Summary

Ce document est une **mise à jour structurante** du PRD existant (`prd.md`), pas une réécriture from scratch.

Le MVP est terminé, validé et conserve sa valeur fondatrice: **Jeedom reste le moteur métier, Home Assistant reste la couche moderne de projection et d’interaction**.

La phase cible **Post-MVP Phase 1 - V1.1 Pilotable** est la première version réellement commercialisable de coexistence Jeedom↔HA.  
La priorité n°1 n’est pas d’élargir immédiatement les domaines supportés; la priorité n°1 est de **maîtriser le périmètre publié et les opérations de projection vers Home Assistant**.

Ordre stratégique imposé:
1. Pilotage du bridge (V1.1 Pilotable)
2. Extension fonctionnelle ordonnée
3. Maturité produit avancée
4. Alignements optionnels type Homebridge

## 2. Contexte et acquis du MVP

Acquis confirmés et à préserver:
- Proposition de valeur validée: accès rapide à HA sans migration brutale.
- Périmètre utile déjà livré: lumières, switches/prises, covers, capteurs simples.
- Politique conservative validée: mieux vaut non publié que mal publié.
- Diagnostic de couverture MVP fonctionnel et déjà utile au support.
- Fondations techniques et UX suffisantes pour passer à une phase de produit pilotable.

Invariants MVP conservés:
- Jeedom source de vérité métier.
- Identifiants stables côté projection.
- Comportement explicable et prévisible.
- Local-first et soutenabilité support comme contraintes de conception.

## 3. Vision produit inchangée vs évolution post-MVP

Vision inchangée:
- Éviter le big bang migratoire.
- Valoriser l’existant Jeedom.
- Utiliser HA comme couche moderne d’interface et d’interaction.

Évolution post-MVP:
- Passage d’un bridge “utile” à un bridge **pilotable en exploitation**.
- Passage d’une logique “publier ce qui marche” à une logique “publier ce qui est maîtrisé, explicable et opérable”.
- Passage d’une promesse technique à une promesse commercialisable: qualité perçue, clarté opérationnelle, coût support contenu.

## 4. Nom et objectif de la phase cible : V1.1 Pilotable

**Nom de phase:** Post-MVP Phase 1 - V1.1 Pilotable

**Objectif produit unique:** donner à l’utilisateur un contrôle clair, granulaire et sûr du périmètre Jeedom projeté dans Home Assistant, avec des opérations explicites et un état minimal du pont visible.

**Résultat attendu de phase:** un pont de coexistence exploitable au quotidien, vendable sur sa lisibilité opérationnelle, pas sur la seule largeur fonctionnelle.

## 5. Problèmes utilisateur prioritaires de la phase

Problèmes P0 à résoudre:
- L’utilisateur ne maîtrise pas précisément ce qui est publié dans HA.
- L’utilisateur ne comprend pas pourquoi un équipement est publié ou non publié, ni la cause d’un éventuel écart.
- Les opérations de maintenance discovery sont confondues et risquées perçues.
- Les impacts forts côté HA (historique, dashboards, automatisations) sont mal anticipés.
- La santé minimale du pont n’est pas suffisamment visible pour diagnostiquer rapidement.

## 6. Objectifs produit

Objectifs court terme (V1.1 Pilotable):
- Installer une console de configuration et d’opérations centrée sur le périmètre publié.
- Permettre le pilotage par pièce avec décisions d’inclusion/exclusion par équipement, exprimées par leur source.
- Centrer le diagnostic utilisateur sur les équipements in-scope uniquement.
- Rendre explicite la différence entre republier et supprimer/recréer.
- Afficher une cause métier lisible par équipement pour tout écart entre décision et état projeté.
- Exposer un état minimal du pont: démon, broker, dernière synchro.
- Réduire les tickets d’incompréhension publication/diagnostic.

Objectifs ultérieurs (hors V1.1, ordonnés):
1. Extension fonctionnelle: scénarios en `button`, puis `number`, puis `select`, puis `climate` minimal et strict.
2. Maturité produit avancée: preview complète, remédiation guidée avancée, support outillé avancé.
3. Alignements optionnels tardifs (dont Homebridge) sans inversion de priorité.

## 7. Principes produit non négociables

- **Jeedom reste la source de vérité métier.**
- **La prédictibilité prime sur la couverture fonctionnelle.**
- **Chaque décision de publication doit être explicable.**
- **La coexistence progressive prime sur la migration big bang.**
- **La soutenabilité support est une contrainte produit.**

Règle de dernier recours:
- En cas de conflit entre “publier plus” et “publier correctement”, le produit choisit “publier moins, expliquer mieux”.

## 8. Périmètre fonctionnel prioritaire de V1.1 Pilotable

### 8.1 Console de pilotage du périmètre publié

Capacités minimales requises:
- Vue principale **par pièce** (objet Jeedom) avec compteurs : Total, Inclus, Exclus, Écarts.
- Inclusion/exclusion au niveau pièce.
- Inclusion ou exclusion au niveau équipement, exprimée par sa source (pièce, plugin, équipement).
- Maintien de la visibilité des exclus avec leur source d'exclusion (pas de disparition silencieuse de la console).

Modèle de lecture par niveau:
- **Équipement:** statut binaire `Publié` / `Non publié` — seul niveau où ce statut existe.
- **Pièce et global:** lecture par compteurs uniquement (Total, Inclus, Exclus, Écarts). Pas de statut agrégé réutilisant le champ statut équipement.

Le concept d'**exception** disparaît de l'interface utilisateur. Les exclusions sont toujours exprimées par leur source : exclu par la pièce, exclu par le plugin, exclu sur cet équipement.

### 8.2 Opérations discovery explicites

Deux opérations distinctes, non confondues:
- **Republier la configuration**: met à jour la projection sans intention de rupture du modèle existant.
- **Supprimer puis recréer dans Home Assistant**: opération de rupture explicite utilisée quand une reconstruction est nécessaire.

Impact utilisateur à rendre visible avant confirmation:
- Risque potentiel de rupture de références HA (dashboards, automatisations, assistants vocaux).
- Risque de perte d’historique sur les entités recréées.
- Possibles changements d’`entity_id` pilotés par les règles internes de Home Assistant (limitation HA, pas plugin).

### 8.3 Explicabilité par équipement

Pour chaque équipement in-scope, la console doit fournir un modèle à 4 dimensions:
- **Périmètre:** Inclus · Exclu par la pièce · Exclu par le plugin · Exclu sur cet équipement.
- **Statut:** Publié · Non publié (binaire, niveau équipement uniquement).
- **Écart:** indication bidirectionnelle de désalignement entre la décision locale et l’état projeté (inclus mais non publié, ou exclu mais encore publié).
- **Cause métier obligatoire:** libellé explicite et lisible pour tout écart (ex: "Aucun mapping compatible", "Changement en attente d’application").
- Indication de l’action recommandée quand une remédiation simple existe.

Le backend conserve des `reason_code` stables (hérités d’Epic 3, non exposés en UI) et expose en complément un contrat UI canonique (`cause_code`, `cause_label`, optionnellement `cause_action`). Le PRD exige cette distinction ; la spécification technique détaillée du contrat vit dans l’architecture.

La confiance (Sûr / Probable / Ambigu) ne fait pas partie de la console principale. Elle reste visible uniquement dans le diagnostic technique détaillé.

### 8.4 Santé minimale du pont

Indicateurs visibles en permanence:
- État du démon.
- État broker MQTT.
- Date/heure de dernière synchronisation terminée.

## 9. Definition of Done produit du chantier 1

Le chantier 1 “Pilotage du périmètre publié” est terminé si et seulement si:

1. L’utilisateur peut inclure/exclure une pièce complète.
2. L’utilisateur peut définir des décisions d’inclusion/exclusion par équipement, exprimées par leur source.
3. Le modèle Périmètre / Statut / Écart / Cause est lisible et cohérent avec l’état réel de publication pour chaque équipement.
4. Chaque écart dispose d’une cause métier lisible.
5. La distinction `Republier` vs `Supprimer/Recréer` est explicite dans l’UI et dans les confirmations.
6. Les opérations à impact fort HA nécessitent une confirmation explicite avec rappel des conséquences.
7. Le niveau global (parc), pièce et équipement couvre les opérations essentielles de maintenance du périmètre.
8. L’état minimal du pont (démon, broker, dernière synchro) est visible sans navigation technique.
9. Les erreurs d’infrastructure sont distinguées des problèmes de configuration.
10. Le diagnostic utilisateur est centré sur les équipements in-scope ; la confiance n’est visible qu’en diagnostic technique.
11. La distinction `reason_code` (backend stable) / `cause_code` + `cause_label` (contrat UI) est respectée dans l’architecture.
12. Le comportement observé reste aligné avec les principes de prédictibilité et d’explicabilité.

## 10. Non-objectifs / hors périmètre court terme

Hors V1.1 sauf nécessité forte justifiée:
- Preview complète de publication avant action.
- Parcours de remédiation guidé avancé multi-étapes.
- Support outillé avancé (au-delà du socle déjà existant).
- Élargissement massif du périmètre fonctionnel.
- Alignement Homebridge comme axe prioritaire.

Ne pas faire en V1.1:
- Repositionner le plugin comme outil de migration totale.
- Pousser de nouvelles familles fonctionnelles avant stabilisation du pilotage.
- Ajouter des heuristiques opaques pour “gonfler” artificiellement la couverture.

## 11. Frontière explicite entre pilotage du bridge, maturité ultérieure et élargissement du périmètre fonctionnel

### Frontière A - Pilotage du bridge (V1.1, prioritaire)

Contenu:
- Console de pilotage périmètre.
- Opérations discovery explicites et sûres.
- Explicabilité par équipement.
- Santé minimale du pont.

But:
- Fiabiliser l’exploitation du périmètre déjà publié.

### Frontière B - Élargissement du périmètre fonctionnel (phase suivante, après A)

Ordre obligatoire:
1. Scénarios Jeedom exposés en `button`
2. `number`
3. `select`
4. `climate` minimal et strict

But:
- Étendre la valeur sans casser la lisibilité ni la soutenabilité support.

### Frontière C - Maturité produit avancée (après B)

Contenu:
- Preview complète.
- Remédiation guidée avancée.
- Vue santé avancée.
- Support outillé avancé.

But:
- Améliorer l’efficacité opérationnelle à l’échelle.

### Frontière D - Alignements optionnels tardifs (après C)

Contenu:
- Convergences externes non critiques, y compris patterns Homebridge.

But:
- Optimiser l’écosystème sans détourner la roadmap cœur.

## 12. Exigences UX / explicabilité / sécurité d’usage

Exigences UX:
- Desktop-first avec lisibilité de parc et filtres rapides.
- Un vocabulaire de statuts stable et non ambigu.
- Une hiérarchie claire entre action globale, action pièce et action équipement.

Exigences d’explicabilité:
- Chaque équipement in-scope en écart doit afficher une cause métier lisible.
- Les causes techniques doivent être traduites en langage produit compréhensible via le contrat UI (`cause_label`).
- Les limites dues à Home Assistant doivent être signalées explicitement comme limites externes.
- La confiance (Sûr / Probable / Ambigu) n’est visible qu’en diagnostic technique, pas en console principale.

Exigences de sécurité d’usage:
- Confirmation obligatoire des actions à impact fort côté HA.
- Message de confirmation incluant le périmètre impacté et les conséquences possibles.
- Distinction visuelle stricte entre:
  - incident d’infrastructure (démon/broker/connexion),
  - action de configuration requise,
  - limitation de couverture fonctionnelle.

## 13. Exigences opérationnelles minimales visibles utilisateur

La V1.1 doit rendre visibles, sans outil externe:
- État du démon.
- État du broker MQTT.
- Dernière synchronisation terminée (timestamp).
- Résultat de la dernière opération de maintenance (succès/partiel/échec).
- Modèle Périmètre / Statut / Écart / Cause au niveau équipement.

Actions opérationnelles minimales:
- Republier la configuration: global, pièce, équipement.
- Supprimer / Recréer: global, pièce, équipement.
- Recalcul / réapplication des exclusions après modification de périmètre.

Dépendances et limites à expliciter:
- L’effet final de suppression/recréation dépend du cycle de vie des entités dans HA.
- La conservation des historiques/références HA n’est pas garantie lors d’une recréation.
- Le comportement de redécouverte dépend aussi de la conformité broker MQTT sur les messages retained (limitation externe possible).

## 14. KPIs / success metrics de la phase

KPIs de pilotage V1.1:
- Équipements avec statut et cause métier lisibles: **> 95%**.
- Temps médian pour comprendre un “non publié”: **< 3 minutes**.
- Taux de réussite des opérations de maintenance (global/pièce/équipement): **>= 95%**.
- Réduction des tickets “incompréhension de publication”: **-20% par trimestre**.
- Charge support mainteneur en régime nominal: **<= 3h/semaine**.
- Installations actives J+30 utilisant au moins une action console: **> 50%**.
- Note Market moyenne visée: **>= 4/5**.

Indicateur de qualité d’usage critique:
- Part des opérations à impact fort confirmées avec information de conséquence affichée: **100%**.

## 15. Hypothèses, risques et arbitrages

Hypothèses de phase:
- Le socle MVP reste stable pendant la phase V1.1.
- Les utilisateurs veulent prioritairement maîtriser leur parc publié avant d’ajouter de nouveaux domaines.
- La clarté opérationnelle réduit réellement les tickets de support.

Risques principaux:
- Scope creep vers l’extension fonctionnelle trop tôt.
- Confusion persistante entre republier et supprimer/recréer.
- Sous-estimation des impacts HA lors d’opérations destructives.
- Dette UX/ops reportée au profit de “plus de types”.

Arbitrages décidés:
- Priorité au pilotage du périmètre publié avant extension.
- Priorité à l’explicabilité avant automatisation avancée.
- Priorité à la soutenabilité support avant sophistication outillage.

## 16. Préparation au découpage futur en epics

Ce PRD est conçu pour un découpage epic-first sans produire de stories à ce stade.

Axes de découpage recommandés pour la planification:
- **Axe 1:** Console de pilotage par pièce + décisions d’inclusion/exclusion par équipement.
- **Axe 2:** Opérations discovery explicites (`Republier` vs `Supprimer/Recréer`) et sécurité d’usage.
- **Axe 3:** Modèle Périmètre / Statut / Écart / Cause et cohérence explicative.
- **Axe 4:** Recadrage UX — alignement de la console et du diagnostic sur le modèle mental utilisateur.
- **Axe 5:** Santé minimale du pont et retour opérationnel visible.
- **Axe 6:** Extension fonctionnelle ordonnée (button → number → select → climate minimal/strict).

Règles de planification:
- Les epics V1.1 ne doivent pas introduire d’extension massive de scope.
- Chaque epic doit contenir un critère explicite de réduction de dette support.
- Toute action à impact HA fort doit intégrer une exigence de confirmation et de transparence d’impact.

## 17. Recommandation finale : prêt ou non pour planification d’epics

**Recommandation: PRÊT pour la planification des epics post-MVP**, avec garde-fous obligatoires:
- Respect strict de l’ordre stratégique (pilotage → extension → maturité → options).
- Pas de dilution du chantier 1 par des demandes d’élargissement opportuniste.
- Traçabilité explicite des impacts HA sur chaque opération sensible.

Décision produit:
- Le PRD post-MVP V1.1 est suffisamment clair, priorisé et exploitable pour lancer le workflow de planification des nouveaux epics.
