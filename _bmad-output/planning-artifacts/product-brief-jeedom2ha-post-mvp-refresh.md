---
document_type: product_brief_refresh
project: jeedom2ha
phase: post_mvp_phase_1
version_label: v1_1_pilotable
date: 2026-03-22
author: Mary (Business Analyst)
status: draft_ready_for_pm_challenge
source_documents:
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-03-12.md
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/project-context.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/brainstorming/brainstorming-session-2026-03-12-001.md
  - _bmad-output/planning-artifacts/research/domain-jeedom-homeassistant-research-2026-03-12.md
  - _bmad-output/planning-artifacts/research/technical-jeedom-plugin-development-research-2026-03-12.md
---

# Product Brief Refresh - jeedom2ha (Post-MVP Phase 1 - V1.1 Pilotable)

## 1. Executive Summary

Le MVP de `jeedom2ha` est terminé et validé dans son périmètre initial. Il a démontré qu'un utilisateur Jeedom peut retrouver rapidement une maison utile dans Home Assistant sans migration lourde.

Le cap **Post-MVP Phase 1 - V1.1 Pilotable** n'est pas d'élargir immédiatement les domaines publiés. Le cap prioritaire est de transformer le plugin en **couche de coexistence pilotable, explicable et commercialisable** :
- pilotage fin du périmètre publié,
- opérations de maintenance claires,
- expérience prévisible côté Home Assistant,
- coût de support soutenable.

La prochaine version doit donc faire passer le produit de "bridge MVP utile" à "outil d'exploitation de coexistence Jeedom↔HA", puis seulement ensuite étendre progressivement le scope fonctionnel.

## 2. Ce que le MVP a validé

- La proposition centrale est réelle : profiter rapidement de Home Assistant sans casser l'existant Jeedom.
- Le périmètre MVP est utile au quotidien : lumières, switches/prises, covers, capteurs simples.
- La stratégie conservative et explicable est pertinente : mieux vaut ne pas publier que publier faux.
- Le plugin peut rester aligné avec un modèle "Jeedom backend / HA projection-interaction".
- La base technique et UX de diagnostic est suffisante pour une phase d'industrialisation produit.

## 3. Ce qui reste vrai dans la vision d'origine

- La vision fondatrice reste valide : éviter la migration brutale et préserver l'investissement Jeedom.
- Jeedom reste la source de vérité métier (états, logique, scénarios backend).
- Home Assistant reste la couche moderne de restitution, d'interaction et d'interface.
- La promesse clé reste le time-to-value rapide avec un comportement fiable, non magique.
- Le produit doit continuer à privilégier la prévisibilité, la lisibilité et la maîtrise.

## 4. Ce qui change dans la phase post-MVP

Le changement principal n'est pas "plus d'entités", mais "plus de contrôle produit".

Priorité phase post-MVP immédiate :
- évolution de la page diagnostic vers une console de configuration et d'opérations HA,
- vue du parc classée par pièce,
- sélection/désélection d'une pièce entière,
- exceptions par équipement dans la pièce,
- actions maintenance discovery au niveau global, pièce, équipement,
- distinction explicite entre :
  - republier la configuration,
  - supprimer puis recréer dans Home Assistant,
- explicabilité renforcée des raisons de publication, exclusion, ambiguïté.

## 5. Problèmes utilisateur prioritaires de la phase suivante

- "Je ne maîtrise pas précisément ce qui est publié dans HA."
- "Je ne comprends pas pourquoi un équipement est publié, exclu ou ambigu."
- "Je n'ai pas d'opérations simples pour maintenir un parc propre (global/pièce/équipement)."
- "Je confonds republier et supprimer/recréer, et je crains de casser mon HA."
- "Quand ma maison Jeedom évolue, je ne veux ni pollution HA ni dette de maintenance."

## 6. Proposition de valeur post-MVP

`jeedom2ha` devient une **couche de coexistence pilotable** :
- l'utilisateur contrôle le périmètre projeté à la bonne granularité,
- chaque décision système est expliquée,
- les opérations sont explicites et sûres,
- l'expérience reste conservative et prévisible.

Valeur clé de la phase :
"Je garde Jeedom comme moteur, j'exploite HA comme interface moderne, et je pilote proprement le pont sans surprise."

## 7. Personas / cibles principales de cette nouvelle phase

### Persona A - Pilote de coexistence (prioritaire)
Utilisateur Jeedom avancé, déjà actif sur le MVP, qui veut un HA propre, stable et maîtrisé sur la durée.

### Persona B - Adopteur pragmatique (prioritaire)
Utilisateur Jeedom intermédiaire qui a validé l'intérêt du bridge mais a besoin d'une UX d'exploitation claire pour continuer.

### Persona C - Intégrateur/Installateur (secondaire stratégique)
Profil pro cherchant une solution vendable, reproductible, avec risque support maîtrisable.

### Persona D - Mainteneur produit/support (interne)
Doit absorber la montée d'usage sans explosion du temps de traitement des tickets.

## 8. Positionnement produit mis à jour

Positionnement recommandé :
**"Le pont de coexistence Jeedom↔Home Assistant pilotable et explicable."**

Conséquences de positionnement :
- pas un outil de migration big-bang,
- pas un moteur d'automatisation concurrent de Jeedom,
- pas un alignement Homebridge-first,
- oui à une couche produit de projection/interaction moderne, maîtrisée et commercialisable.

### Principes non négociables

- **Jeedom source de vérité métier** : la logique métier reste côté Jeedom.
- **Prédictibilité avant couverture** : mieux vaut publier moins, mais correctement.
- **Explicabilité obligatoire** : chaque décision de publication/exclusion doit être lisible.
- **Coexistence progressive, pas migration big bang** : le produit accompagne, il ne force pas.
- **Soutenabilité support** : toute évolution doit réduire ou contenir la dette de support.

## 9. Objectifs produit post-MVP

### Objectifs court terme (phase 1 post-MVP)
- Installer une console d'exploitation complète orientée périmètre publié.
- Rendre les opérations maintenance compréhensibles et différenciées.
- Réduire les tickets d'incompréhension liés au périmètre/diagnostic.
- Atteindre une qualité perçue compatible avec une commercialisation Market.
- Intégrer une vue santé minimale du pont (daemon, broker, dernière synchro).

### Objectifs moyen terme (phase 2)
- Étendre le scope fonctionnel de manière strictement ordonnée :
  - scénarios en button,
  - number,
  - select,
  - climate minimal et strict.

### Objectifs de maturité (phase 3+)
- Prévisualisation de publication,
- remédiation guidée,
- vue santé avancée du pont,
- support renforcé et outillé.

## 10. Non-objectifs / hors périmètre à court terme

- Ne pas élargir immédiatement le scope fonctionnel avant la maîtrise UX/ops.
- Ne pas viser la couverture exhaustive de tous types Jeedom.
- Ne pas introduire de logique "magique" opaque pour augmenter artificiellement la couverture.
- Ne pas faire des alignements Homebridge-like le cœur de la roadmap.
- Ne pas transformer le plugin en plateforme de migration complète dès cette phase.

## 11. Ordre recommandé des grands chantiers d'évolution

1. **Chantier 1 - Pilotage du périmètre publié (priorité absolue)**  
Console pièce/équipement + inclusion/exclusion par pièce + exceptions par équipement + opérations de maintenance explicites + explicabilité renforcée + santé minimale du pont.

**Definition of Done (Chantier 1, strictement indispensable)**
- L'utilisateur peut inclure/exclure une pièce entière et poser des exceptions équipement.
- L'utilisateur comprend clairement la différence entre `republication` et `suppression/recréation`.
- Chaque équipement a un statut lisible avec raison explicite.
- Les opérations globales/pièce sont opérationnelles ; le niveau équipement reste limité aux actions essentielles.
- Le pont expose un état minimal : daemon, broker, dernière synchronisation.

2. **Chantier 2 - Extension fonctionnelle progressive**  
Scénarios `button` puis `number`, `select`, `climate` minimal et strict.

3. **Chantier 3 - Maturité produit & exploitation**  
Preview publication, remédiation guidée, vue santé avancée, support outillé.

4. **Chantier 4 - Alignements optionnels tardifs**  
Convergences externes non critiques (ex. patterns Homebridge) sans inversion de priorité.

## 12. Valeur business / market / adoption

- Rend la proposition Market plus claire : un produit exploitable, pas seulement technique.
- Augmente la conversion installation -> usage actif via une UX de contrôle concrète.
- Renforce la fidélisation des utilisateurs MVP en réduisant la friction post-installation.
- Limite la dette support par une meilleure explicabilité et des opérations standardisées.
- Crée un différenciateur net sur la niche Jeedom↔HA : coexistence pilotable plutôt que migration forcée.

## 13. Risques produit et arbitrages

### Risque 1 - Vouloir élargir le scope trop tôt
Impact : dégradation de qualité perçue, support en hausse, roadmap instable.  
Arbitrage : verrouiller l'ordre "maîtrise UX/ops avant extension".

### Risque 2 - UX ops insuffisamment explicite
Impact : mauvaises manipulations, pollution HA, perte de confiance.  
Arbitrage : priorité à la clarté des opérations et des raisons de décision.

### Risque 3 - Dette support mainteneur
Impact : ralentissement produit, frustration utilisateur, risque d'abandon.  
Arbitrage : concevoir chaque évolution avec objectif explicite de réduction de tickets.

### Risque 4 - Positionnement flou (bridge vs migration vs clone)
Impact : attentes irréalistes, messages contradictoires Market.  
Arbitrage : assumer un positionnement de coexistence pilotable, pas de migration totale.

### Risque 5 - Complexité "options avancées" trop précoce
Impact : produit moins accessible, adoption ralentie.  
Arbitrage : progression en couches, d'abord opérations essentielles, puis maturité avancée.

## 14. Success metrics mises à jour

### KPIs de pilotage (phase 1)

### Adoption et usage
- Taux d'installations actives à J+30 avec usage d'au moins une action console : **> 50%**.
- Conversion installation Market -> usage actif J+30 : **objectif de pilotage 30-40%**.

### Maîtrise du périmètre
- Part des équipements avec statut explicable (raison lisible) : **> 95%**.
- Temps médian de diagnostic d'un "non publié" depuis la console : **< 3 min**.

### Qualité opérationnelle
- Taux de réussite des opérations maintenance (global/pièce/équipement) : **cible initiale >= 95%**.
- Réduction des tickets "incompréhension de publication" : **-20% par trimestre**.

### Business / support
- Note Market moyenne : **>= 4/5**.
- Charge support mainteneur en régime nominal : **objectif de pilotage <= 3h/semaine**.

## 15. Recommandation finale : brief prêt ou non pour passage au PM

### Recommandation
**Prêt pour passage au PM, avec challenge ciblé.**

### Pourquoi "prêt"
- Le MVP est clairement acté comme validé.
- La phase post-MVP est recentrée sur une priorité stratégique cohérente : pilotabilité avant extension.
- L'ordre des chantiers est explicite et arbitrable.
- Les non-objectifs sont clairs, ce qui réduit le risque de scope creep.
- Les métriques sont orientées décision et exploitation.

### Points à challenger en revue PM (avant update PRD)
- Seuils KPI finaux (en particulier conversion et charge support) à calibrer selon capacité réelle.
- Niveau exact de granularité ops en v1 post-MVP (ce qui est strictement indispensable).
- Plan de message Market pour aligner promesse produit et périmètre réel.
