---
workflowType: 'epic_planning'
workflow: 'create-epics-and-stories'
project: 'jeedom2ha'
phase: 'post_mvp_phase_1'
version_label: 'v1.1_pilotable'
date: '2026-03-22'
status: 'story_breakdown_ready_for_validation'
planningScope: 'epics_with_story_breakdown'
inputDocuments:
  - _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-post-mvp-refresh.md
  - _bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-03-22.md
  - _bmad-output/project-context.md
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
lastEdited: '2026-03-22'
---

# Plan d'epics Post-MVP V1.1 Pilotable

## 1. Executive summary

Le plan recommandé pour **Post-MVP Phase 1 - V1.1 Pilotable** retient **4 epics distincts**, sans fusion des axes prioritaires du PRD.

Ce choix est volontaire:
- fusionner la console et les opérations ferait perdre la frontière entre **décision locale de périmètre** et **effet appliqué à Home Assistant**;
- fusionner statuts, santé et opérations ferait retomber au niveau story des contrats qui doivent rester visibles au niveau epic;
- fusionner santé et explicabilité brouillerait la distinction structurante entre **incident d'infrastructure**, **choix de configuration**, **limitation de couverture** et **impact HA**.

Le découpage est centré sur un **coeur de contrat stable**, pas sur des écrans isolés:
1. modèle canonique du périmètre publié;
2. contrat minimal de santé du pont;
3. source backend unique des statuts et raisons lisibles;
4. façade unique d'opérations explicites.

Le plan est cohérent avec le cadrage validé:
- priorité absolue au **pilotage du bridge** et à la **maîtrise du périmètre publié**;
- aucune anticipation d'extension fonctionnelle `button -> number -> select -> climate`;
- aucune dérive vers preview complète, remédiation guidée avancée, santé avancée, support outillé avancé ou alignements Homebridge.

Conclusion de synthèse:
- **4 epics recommandés**
- **ordre d'exécution recommandé: 1 -> 2 -> 3 -> 4**
- **prêt pour validation story-level avant `create-story`**: le blocage initial du readiness report est levé par la section 9, qui fournit le lot de correction documentaire et la décomposition story-level nécessaires sans réouvrir le cadrage produit.

## 2. Rappel du périmètre V1.1 Pilotable

**Périmètre in**
- Console de pilotage pensée sur trois niveaux explicites: `global -> pièce -> équipement`.
- Vue par pièce comme point d'entrée principal, sans devenir l'unique modèle de lecture.
- Inclusion/exclusion par pièce avec exceptions par équipement.
- Opérations discovery explicites et distinctes:
  - `Republier dans Home Assistant`
  - `Supprimer puis recréer dans Home Assistant`
- Statuts lisibles par équipement avec raison principale et action recommandée simple quand elle existe.
- Santé minimale du pont visible: démon, broker MQTT, dernière synchronisation terminée, résultat court obligatoire de la dernière opération.
- Retour opérationnel lisible pour les actions à impact côté Home Assistant.

**Périmètre out**
- Extension fonctionnelle future: `button`, `number`, `select`, `climate` minimal/strict.
- Preview complète avant/après publication.
- Remédiation guidée avancée multi-étapes.
- Santé avancée du pont, observabilité experte, timeline ou métriques détaillées.
- Support outillé avancé au-delà du socle déjà existant.
- Alignements tardifs type Homebridge.

**Principe de phase**
- Jeedom reste la source de vérité métier.
- La prédictibilité prime sur la couverture fonctionnelle.
- Chaque décision de publication doit être explicable.
- La coexistence progressive prime sur la migration big bang.
- La soutenabilité support est une contrainte produit.

## 3. Guardrails obligatoires hérités du PRD, de la revue UX et de la revue architecture

### Guardrails PRD

- La phase cible est strictement **Post-MVP Phase 1 - V1.1 Pilotable**.
- Le chantier V1.1 porte d'abord sur la **maîtrise du périmètre publié**, pas sur l'élargissement du scope.
- Toute décision doit privilégier **publier moins, expliquer mieux**.
- Les impacts forts côté HA doivent être explicités avant action.
- Chaque epic doit intégrer au moins un critère explicite de **réduction de dette support**.

### Guardrails UX

- La console doit rester pensée sur trois niveaux explicites:
  - `Global`
  - `Pièce`
  - `Équipement`
- La pièce est le bon niveau de pilotage, mais pas l'unique niveau d'analyse.
- Il faut séparer explicitement:
  - périmètre / configuration locale;
  - état de projection vers HA;
  - raison principale;
  - santé du bridge.
- Le vocabulaire d'action primaire est figé:
  - `Republier dans Home Assistant`
  - `Supprimer puis recréer dans Home Assistant`
- Les confirmations sont graduées selon l'action, la portée et l'impact potentiel côté HA.
- La santé minimale du pont doit vivre dans un bandeau ou niveau global distinct.
- Les epics V1.1 ne doivent pas supposer:
  - preview complète;
  - remédiation guidée avancée;
  - santé avancée;
  - extension de scope.

### Guardrails architecture

- Pas de refonte complète: conserver le socle **daemon + pipeline central + cache technique + diagnostic**.
- Figer un modèle canonique du périmètre publié:
  - hiérarchie `global -> pièce -> équipement`;
  - états `inherit / include / exclude`;
  - précédence explicite `équipement > pièce > global`.
- Toute opération V1.1 passe par une **façade backend unique**.
- La portée (`global / pièce / équipement`) et l'intention (`Republier / Supprimer-Recréer`) sont des paramètres de cette façade, pas des implémentations dispersées.
- Le backend est la source unique de:
  - statut;
  - raison principale;
  - action recommandée.
- La santé minimale du pont reste légère et contractuelle:
  - démon;
  - broker;
  - dernière synchronisation terminée;
  - résultat court obligatoire de la dernière opération.
- Les invariants HA doivent être protégés:
  - `unique_id` stable tant que l'ID Jeedom est stable;
  - `Republier` = intention non destructive;
  - `Supprimer/Recréer` = seul flux destructif explicite;
  - recalcul du scope déterministe pour une configuration et un snapshot donnés.

## 4. Règles de découpage retenues pour les epics

- Les epics sont organisés par **résultat utilisateur opérationnel**, pas par couche technique ni par écran.
- Les guardrails UX et architecture sont portés **au niveau epic**, pas reportés dans des stories ultérieures.
- La séparation entre **décision locale**, **projection effective vers HA** et **impact visible pour l'utilisateur** doit rester intacte dans chaque epic.
- Les epics V1.1 ne doivent jamais devenir un cheval de Troie pour l'extension fonctionnelle future.
- Le séquencement recommandé privilégie d'abord le **coeur de contrat stable**, puis les actions à impact fort.
- Le découpage conserve le socle MVP et ajoute uniquement les deltas nécessaires à une version pilotable.
- Les quatre axes prioritaires du PRD sont couverts explicitement, sans fusion, pour éviter de noyer:
  - le contrat d'opérations;
  - le moteur de statuts;
  - la santé du pont.

| Axe prioritaire validé | Epic retenu | Pourquoi ce découpage |
|---|---|---|
| Console de pilotage par pièce + exceptions équipement | Epic 1 | Nécessite un contrat de périmètre stable et visible avant toute opération sensible |
| Santé minimale du pont et retour opérationnel visible | Epic 2 | Doit exister comme contrat distinct pour ne pas être absorbée dans les statuts ou l'UI |
| Moteur de statuts / raisons lisibles / explicabilité | Epic 3 | Doit rester un moteur backend unifié et autonome, pas un détail de rendu |
| Opérations discovery explicites et sécurité d'usage | Epic 4 | Porte les invariants HA les plus sensibles et mérite un epic dédié |

## 5. Liste des epics recommandés pour V1.1 Pilotable

### Epic 1 - Coeur de périmètre pilotable et console 3 niveaux

**Objectif**

Installer le contrat de périmètre pilotable V1.1 et la console `global -> pièce -> équipement`, avec la pièce comme point d'entrée principal, sans perdre la lecture globale ni la compréhension des exceptions locales.

**Valeur utilisateur**

L'utilisateur peut enfin décider, comprendre et relire ce qui doit faire partie du périmètre publié dans HA, à la bonne granularité, sans disparition silencieuse des exclus ni logique implicite d'héritage.

**Problème utilisateur traité**

L'utilisateur ne maîtrise pas précisément ce qui est publié dans Home Assistant et ne comprend pas toujours si un équipement suit la règle de sa pièce ou une exception locale.

**Périmètre in**
- Modèle canonique de périmètre publié `global -> pièce -> équipement`.
- États de décision `inherit / include / exclude` avec précédence `équipement > pièce > global`.
- Vue globale de synthèse distincte de la vue par pièce.
- Pilotage par pièce avec exceptions équipement.
- Visibilité continue des équipements exclus et de la source de décision:
  - `Hérite de la pièce`
  - `Exception locale`
- Compteurs globaux et par pièce cohérents avec le modèle canonique.
- Signal explicite quand une décision locale modifie le périmètre voulu sans présumer de son effet immédiat côté HA.

**Périmètre out**
- Preview complète du résultat HA avant application.
- Opérations destructives côté HA.
- Parcours de remédiation avancé.
- Extension du scope fonctionnel au-delà du périmètre MVP déjà couvert.
- Filtres techniques plugin comme modèle principal de lecture.

**Dépendances**
- Réutilise le socle MVP existant: topologie, diagnostic, exclusions déjà présentes.
- Ne dépend d'aucun epic futur pour résoudre la décision effective de périmètre.
- Fournit le contrat de base consommé ensuite par les epics 2, 3 et 4.

**Risques / points de vigilance**
- Transformer la vue par pièce en unique vue de vérité.
- Confondre un toggle local de périmètre avec un effet immédiat sur HA.
- Recalculer l'héritage dans le frontend au lieu d'utiliser un resolver unique.
- Faire disparaître les exclus de la console, ce qui recréerait de l'opacité support.

**Critères de succès epic-level**
- Le périmètre voulu est lisible et modifiable aux trois niveaux `global / pièce / équipement`.
- Chaque équipement expose explicitement la source de sa décision effective.
- Un changement local de périmètre est visible comme tel, sans laisser croire à une suppression immédiate dans HA.
- Les compteurs globaux et par pièce sont déterministes pour une configuration et un snapshot donnés.
- Réduction de dette support: en régime nominal, le support peut reconstruire le périmètre effectif et la source de décision sans lecture de logs bruts.

**Guardrails UX à respecter**
- La console doit afficher trois niveaux explicites, même si la pièce reste le point d'entrée principal.
- La vue par pièce ne doit pas masquer la lecture globale.
- La densité doit rester maîtrisée: synthèse au niveau global, compteurs au niveau pièce, détail explicatif au niveau équipement.
- L'héritage doit être visible sans jargon technique inutile.
- La séparation `périmètre local` vs `projection effective vers HA` doit être perceptible dès cet epic.

**Guardrails architecture à respecter**
- Le modèle canonique du périmètre publié doit devenir la référence unique.
- Le calcul de décision effective doit être centralisé dans un resolver backend unique.
- Aucun écran ne doit reconstruire sa propre logique d'héritage.
- Le socle daemon + pipeline + cache technique + diagnostic est conservé.
- Le recalcul du périmètre doit rester déterministe et testable.

### Epic 2 - Santé minimale du pont et lisibilité opérationnelle globale

**Objectif**

Rendre visible, en permanence et au bon niveau, l'état minimal du pont afin que l'utilisateur distingue immédiatement un problème d'infrastructure d'un problème de périmètre ou de couverture.

**Valeur utilisateur**

L'utilisateur sait d'un coup d'oeil si le bridge, MQTT et la dernière synchronisation sont en état compatible avec les actions attendues, sans devoir ouvrir un écran technique ni interpréter des logs.

**Problème utilisateur traité**

La santé minimale du pont n'est pas suffisamment visible, ce qui entretient la confusion entre panne de bridge, problème de configuration locale et limite de publication.

**Périmètre in**
- Contrat minimal de santé produit par le backend:
  - démon;
  - broker MQTT;
  - dernière synchronisation terminée;
  - résultat court obligatoire de la dernière opération.
- Bandeau global distinct des compteurs de publication.
- Visibilité explicite des raisons de blocage d'actions HA quand l'infrastructure n'est pas disponible.
- Distinction produit visible entre incident d'infrastructure et problème de périmètre.

**Périmètre out**
- Timeline détaillée des synchronisations.
- Observabilité experte, métriques, journal d'événements avancé.
- Bus d'événements ou couche push spécifique V1.1.
- Console support avancée.

**Dépendances**
- Réutilise les signaux runtime déjà présents côté daemon.
- N'a pas besoin d'attendre un futur epic pour fournir une vérité infrastructurelle minimale.
- Devient ensuite une dépendance explicite pour l'epic 3 et pour le gating de l'epic 4.

**Risques / points de vigilance**
- Mélanger visuellement la santé du pont avec les statuts de publication.
- Faire porter au frontend la responsabilité de reconstituer l'état du pont.
- Introduire trop de détails techniques et basculer vers une santé avancée hors scope.
- Utiliser le rouge pour autre chose qu'un incident d'infrastructure.

**Critères de succès epic-level**
- Les trois indicateurs minimums sont visibles sans navigation technique supplémentaire.
- L'utilisateur peut distinguer en moins de quelques secondes un incident bridge d'un problème de configuration ou de couverture.
- Une action HA indisponible affiche une raison de blocage lisible liée à l'état du pont.
- Le contrat de santé reste léger, stable et compréhensible.
- Réduction de dette support: la première qualification d'un ticket "rien ne se passe dans HA" peut se faire depuis le bandeau global sans inspection immédiate des logs daemon.

**Guardrails UX à respecter**
- La santé minimale vit dans un bandeau global distinct et toujours visible.
- Rouge réservé aux incidents d'infrastructure.
- Le bandeau reste compact et non envahissant.
- La santé ne doit pas devenir un tableau technique expert.
- La santé doit expliquer la disponibilité des actions sans se substituer aux statuts métier.

**Guardrails architecture à respecter**
- Le daemon reste la source de vérité de la santé du pont.
- Le contrat minimal est étendu sans refonte ni couche d'observabilité lourde.
- L'exposition au PHP/UI passe par un contrat backend stable, pas par des recalculs côté frontend.
- Le polling existant est suffisant pour la V1.1.
- Aucun invariant HA de cycle de vie ne doit être affaibli par cet epic.

### Epic 3 - Moteur de statuts, raisons lisibles et explicabilité backend

**Objectif**

Unifier côté backend la production des statuts, raisons principales et actions recommandées pour que chaque équipement, chaque pièce et le niveau global racontent une histoire cohérente, lisible et explicable.

**Valeur utilisateur**

L'utilisateur comprend rapidement pourquoi un équipement est publié, exclu, ambigu, non supporté ou bloqué par l'infrastructure, et sait quelle action simple est pertinente quand elle existe.

**Problème utilisateur traité**

Le produit risque sinon de retomber dans un modèle où un seul badge tente de tout dire, où `Partiel` devient un fourre-tout, et où la logique de statut se disperse entre backend et frontend.

**Périmètre in**
- Modèle sémantique séparant au minimum:
  - périmètre;
  - projection;
  - raison principale;
  - infrastructure.
- Jeu de statuts principaux convergent au niveau équipement:
  - `Publié`
  - `Exclu`
  - `Ambigu`
  - `Non supporté`
  - `Incident infrastructure`
- `reason_code` stable, raison lisible, action recommandée simple optionnelle.
- Mention explicite quand une conséquence ou limite vient de Home Assistant.
- Cohérence des agrégations pièce/global avec la lecture équipement.
- Distinction claire entre exclusion volontaire, couverture limitée, mapping ambigu, configuration incomplète et incident bridge.

**Périmètre out**
- Remédiation guidée multi-étapes.
- Correction automatique ou heuristiques opaques.
- Preview complète.
- Outils support enrichis au-delà du socle de diagnostic existant.

**Dépendances**
- S'appuie sur l'epic 1 pour la décision effective de périmètre.
- S'appuie sur l'epic 2 pour distinguer proprement l'incident d'infrastructure.
- Fournit le contrat sémantique indispensable à l'epic 4.

**Risques / points de vigilance**
- Réintroduire un badge unique "Partiel" comme lecture principale au niveau équipement.
- Laisser le frontend inventer ou recomposer des raisons métier.
- Produire trop de statuts différents et dégrader la lisibilité.
- Masquer les limites Home Assistant dans des messages trop techniques ou trop vagues.

**Critères de succès epic-level**
- Plus de 95% des équipements visibles en console exposent un statut principal lisible et une raison principale compréhensible.
- Le temps médian pour comprendre un "non publié" standard reste compatible avec la cible produit `< 3 minutes`.
- `Partiel` reste un état agrégé ou secondaire, pas le statut principal de lecture équipement.
- Les raisons principales sont cohérentes entre backend, UI et support.
- Réduction de dette support: la réponse standard à "pourquoi cet équipement n'est pas publié ?" est obtenable depuis le payload de statut, sans interprétation ad hoc des logs dans les cas nominaux.

**Guardrails UX à respecter**
- Séparer visuellement état de projection, raison principale et santé du pont.
- Conserver une structure standard de message:
  - état court;
  - raison principale;
  - action recommandée;
  - impact HA si pertinent.
- Dire explicitement quand la limite vient de Home Assistant.
- Ne pas transformer la vue par pièce en cache-misère qui masque les équipements problématiques transverses.
- Ne pas faire porter tout le sens produit par un seul badge.

**Guardrails architecture à respecter**
- Le backend est la source unique de `statut + raison principale + action recommandée`.
- Les `reason_code` doivent rester stables et gouvernés côté backend.
- L'incident infrastructure doit être un motif explicite, distinct d'un simple `Non publié`.
- La logique existante de diagnostic est étendue, pas dupliquée.
- Aucun écran ne doit recalculer ses propres règles métier.

### Epic 4 - Opérations HA explicites, graduées et sûres

**Objectif**

Rendre les opérations `Republier` et `Supprimer puis recréer` explicites, cohérentes et sûres aux portées `global / pièce / équipement`, en protégeant les invariants d'impact Home Assistant.

**Valeur utilisateur**

L'utilisateur peut lancer la bonne opération, à la bonne portée, avec le bon niveau de confirmation, sans confondre mise à jour non destructive et reconstruction destructrice côté HA.

**Problème utilisateur traité**

Les opérations de maintenance discovery sont aujourd'hui trop confondues, anxiogènes ou insuffisamment explicites sur leurs conséquences côté Home Assistant.

**Périmètre in**
- Façade backend unique d'opérations V1.1.
- Paramètres explicites de la façade:
  - intention: `Republier` ou `Supprimer/Recréer`;
  - portée: `global`, `pièce`, `équipement`;
  - sélection cible.
- Sémantique figée:
  - `Republier` = intention non destructive;
  - `Supprimer/Recréer` = seul flux destructif explicite.
- Confirmation graduée selon action, portée et impact.
- Présentation explicite de la portée réelle et du nombre d'équipements touchés.
- Rappel visible des conséquences potentielles côté HA:
  - historique;
  - dashboards;
  - automatisations;
  - `entity_id` éventuellement modifié selon les règles HA.
- Résultat d'opération lisible et court après exécution.
- Gating des actions HA selon l'état minimal du pont.
- Séparation maintenue entre:
  - décision locale de périmètre;
  - application à Home Assistant;
  - impact visible pour l'utilisateur.

**Périmètre out**
- Preview complète avant/après.
- Assistant de remédiation guidée.
- Outils massifs de batch management avancé.
- Alignements Homebridge-like.
- Extension du périmètre fonctionnel.

**Dépendances**
- S'appuie sur l'epic 1 pour le scope canonique et la portée.
- S'appuie sur l'epic 2 pour le gating et la lisibilité infrastructurelle.
- S'appuie sur l'epic 3 pour la lisibilité des raisons, impacts et résultats.

**Risques / points de vigilance**
- Cacher un comportement destructif derrière `Republier`.
- Multiplier des endpoints ou implémentations par portée.
- Utiliser une confirmation générique sans rappeler l'action réelle.
- Lancer des actions HA alors que le démon ou MQTT est indisponible.
- Faire croire que les conséquences HA dépendent uniquement du plugin alors que certaines relèvent du cycle de vie Home Assistant.

**Critères de succès epic-level**
- 100% des flux destructifs utilisateurs passent par `Supprimer puis recréer dans Home Assistant`.
- `Republier` reste non destructif par intention et par contrat.
- Chaque opération affiche sa portée réelle, le volume touché et un résultat court lisible.
- Les confirmations fortes rappellent systématiquement les conséquences possibles côté HA.
- Réduction de dette support: pour une opération sensible, le support peut identifier depuis le retour opérationnel quelle action a été lancée, sur quel périmètre et avec quel résultat court, sans devoir reconstituer le scénario à partir d'indices dispersés.

**Guardrails UX à respecter**
- Les libellés d'action restent strictement:
  - `Republier dans Home Assistant`
  - `Supprimer puis recréer dans Home Assistant`
- `Supprimer puis recréer` vit dans une zone de maintenance secondaire ou avancée, pas dans le flux normal.
- La confirmation reprend l'action et la portée réelles, jamais un simple `Confirmer`.
- Les confirmations sont graduées selon l'impact et la portée.
- La console doit rappeler ce qui relève d'une limitation Home Assistant et non du plugin.

**Guardrails architecture à respecter**
- Toute opération passe par une façade backend unique.
- Portée et intention sont des paramètres, pas des branches d'implémentation dispersées.
- Le recalcul du scope avant exécution reste déterministe.
- `unique_id` reste stable tant que l'ID Jeedom reste stable.
- Aucun orchestrateur local côté UI ne doit contourner la logique centrale.

## 6. Vérification explicite de non-empiètement

| Zone à ne pas empiéter | Vérification |
|---|---|
| Extension fonctionnelle future | Aucun epic V1.1 n'introduit `button`, `number`, `select`, `climate` ou une nouvelle famille de couverture |
| Preview complète | Le plan admet seulement des compteurs, un état `changements à appliquer` et des conséquences résumées, jamais une simulation complète avant/après |
| Remédiation guidée avancée | Le plan autorise seulement une action recommandée simple, pas d'assistant multi-étapes ni d'automatisation corrective |
| Santé avancée du pont | La santé reste limitée à `démon`, `broker`, `dernière synchro terminée`, résultat court obligatoire de dernière opération |
| Support outillé avancé | Le plan améliore la lisibilité support, mais n'ajoute pas d'outillage lourd ou de console support avancée |
| Options tardives type Homebridge | Aucun epic ne dépend d'un pattern Homebridge ni ne le prend comme cible de convergence |

Conclusion: **les epics V1.1 restent strictement dans la frontière "pilotage du bridge / maîtrise du périmètre publié".**

## 7. Ordre recommandé d'exécution des epics

1. **Epic 1 - Coeur de périmètre pilotable et console 3 niveaux**  
   Premier car il fixe le contrat racine `global -> pièce -> équipement` et la séparation entre décision locale et projection effective.

2. **Epic 2 - Santé minimale du pont et lisibilité opérationnelle globale**  
   Deuxième car les actions et les statuts doivent pouvoir s'appuyer sur une vérité infrastructurelle minimale clairement visible.

3. **Epic 3 - Moteur de statuts, raisons lisibles et explicabilité backend**  
   Troisième car il consolide la lecture produit sur le périmètre et la santé déjà stabilisés.

4. **Epic 4 - Opérations HA explicites, graduées et sûres**  
   Dernier car il porte les impacts HA les plus sensibles et doit s'appuyer sur un scope canonique, une santé minimale fiable et une explicabilité déjà en place.

Cet ordre ne remet pas en cause la priorité produit du PRD. Il sécurise la mise en oeuvre autour d'un contrat stable avant d'ouvrir les flux à impact fort.

## 8. Vérification finale

**Le découpage est-il bien centré sur un coeur de contrat stable, et non sur des écrans isolés ?**

**Oui.**

Le plan est centré sur quatre contrats stables:
- **Epic 1** porte le contrat de périmètre et de précédence.
- **Epic 2** porte le contrat minimal de santé du pont.
- **Epic 3** porte le contrat sémantique `statut / raison / action recommandée`.
- **Epic 4** porte le contrat d'opérations explicites et de sécurité d'usage.

Ce que le plan **ne fait pas**:
- il ne découpe pas par écran `global`, `pièce`, `équipement`;
- il ne découpe pas par bouton `Republier` ou `Supprimer/Recréer`;
- il ne renvoie pas les décisions structurantes UX/architecture au niveau story.

Signal faible à surveiller au passage vers `create-story`:
- si les stories futures se mettent à découper "la vue globale", "la ligne pièce", "le bouton republier", sans rappeler le contrat backend unique qu'elles servent, alors le découpage dérive hors du cadrage validé.

## 9. Plan de correction readiness avant `create-story`

Le readiness report du **2026-03-22** a initialement invalidé un passage direct à `create-story`.

Le problème n'est pas le cadrage epic-level: il est jugé bon.  
Le problème était l'absence d'un package story-level prêt à implémenter, testable et auditable.  
La présente section 9 apporte précisément ce package de correction et lève ce blocage.

### 9.1 Blocages à lever

- Absence de stories prêtes à implémenter.
- Absence de critères d'acceptation en format `Given / When / Then`.
- Dépendances story-level non auditables.
- Ambiguïté documentaire sur le caractère obligatoire du **résultat de dernière opération**.

### 9.2 Correction documentaire obligatoire

Avant toute écriture de stories détaillées, les règles suivantes doivent être figées comme non négociables:

1. Le champ **résultat de dernière opération** est obligatoire dans le contrat V1.1.
2. Aucune story ne peut réintroduire une logique métier calculée dans le frontend.
3. Aucune story ne peut masquer la séparation entre décision locale de périmètre et application à Home Assistant.
4. Aucune story ne peut dépendre d'une story future pour fonctionner nominalement.
5. Chaque story doit porter explicitement une réduction de dette support, pas seulement une livraison technique.

### 9.3 Décomposition story-level complète

#### Epic 1 - Coeur de périmètre pilotable et console 3 niveaux

##### Story 1.1 - Resolver canonique du périmètre publié

**User story**  
En tant qu'utilisateur Jeedom avancé,  
je veux que le périmètre publié soit calculé par un resolver backend unique,  
afin que les décisions `global -> pièce -> équipement` soient prédictibles et explicables.

**Dépendances autorisées:** aucune  
**Réduction de dette support:** supprime les relectures manuelles de règles d'héritage contradictoires entre backend et UI.

**Acceptance Criteria**

**Given** une configuration de périmètre contenant des règles `global`, `pièce` et `équipement`  
**When** le backend calcule la décision effective d'un équipement  
**Then** il applique strictement les états `inherit`, `include`, `exclude` avec précédence `équipement > pièce > global`

**Given** un équipement explicitement inclus dans une pièce exclue  
**When** la décision effective est calculée  
**Then** la décision retournée est `include`  
**And** la source de décision retournée est `exception_equipement`

**Given** une même configuration rejouée sur un même snapshot  
**When** le resolver est exécuté plusieurs fois  
**Then** il produit exactement les mêmes décisions et compteurs

##### Story 1.2 - Vue globale et synthèse par pièce sans recalcul frontend

**User story**  
En tant qu'utilisateur de la console,  
je veux voir un résumé global et des synthèses par pièce fiables,  
afin de comprendre rapidement le périmètre voulu sans ambiguïté de calcul.

**Dépendances autorisées:** Story 1.1  
**Réduction de dette support:** évite les écarts de lecture entre compteurs UI et état backend réel.

**Acceptance Criteria**

**Given** un périmètre calculé par le resolver backend  
**When** l'UI charge la console V1.1  
**Then** elle affiche un résumé global et une synthèse par pièce issus uniquement du payload backend

**Given** une pièce contenant inclusions, exclusions et exceptions  
**When** la synthèse est affichée  
**Then** les compteurs reflètent exactement les décisions effectives retournées par le backend

**Given** une modification locale de périmètre  
**When** l'UI rafraîchit les synthèses  
**Then** elle ne recalcule aucune logique métier côté frontend  
**And** elle réaffiche uniquement les données recalculées par le backend

##### Story 1.3 - Exceptions équipement et visibilité continue des exclus

**User story**  
En tant qu'utilisateur Jeedom,  
je veux voir les exceptions locales et les équipements exclus sans disparition silencieuse,  
afin de relire précisément pourquoi un équipement est ou n'est pas dans mon scope.

**Dépendances autorisées:** Story 1.1, Story 1.2  
**Réduction de dette support:** permet de reconstruire la source de décision sans inspection de logs bruts.

**Acceptance Criteria**

**Given** un équipement exclu volontairement  
**When** l'utilisateur consulte la pièce correspondante  
**Then** l'équipement reste visible dans la console  
**And** son état de décision est affiché explicitement

**Given** un équipement qui hérite de la règle de sa pièce  
**When** l'utilisateur consulte son détail  
**Then** la source de décision affichée est `Hérite de la pièce`

**Given** un équipement qui déroge à la règle de sa pièce  
**When** l'utilisateur consulte son détail  
**Then** la source de décision affichée est `Exception locale`

##### Story 1.4 - Changements locaux en attente d'application Home Assistant

**User story**  
En tant qu'utilisateur Jeedom,  
je veux distinguer une décision locale de périmètre d'une action effectivement appliquée à Home Assistant,  
afin de ne pas croire qu'un toggle modifie instantanément HA.

**Dépendances autorisées:** Story 1.1, Story 1.2, Story 1.3  
**Réduction de dette support:** réduit les tickets issus de la confusion "j'ai exclu mais HA n'a pas encore changé".

**Acceptance Criteria**

**Given** une modification locale d'inclusion ou d'exclusion  
**When** l'utilisateur revient sur la console  
**Then** un état `changements à appliquer à Home Assistant` est visible au niveau pertinent

**Given** des changements locaux non encore appliqués  
**When** l'utilisateur consulte la synthèse globale ou la pièce  
**Then** l'UI n'affiche pas ces changements comme déjà effectifs côté Home Assistant

**Given** des changements locaux en attente et aucune opération Home Assistant encore confirmée  
**When** l'utilisateur recharge la console ou navigue entre les niveaux `global`, `pièce` et `équipement`  
**Then** l'état `changements à appliquer` reste visible de manière cohérente  
**And** il dépend uniquement du payload backend de périmètre en attente, sans recalcul métier frontend

##### Story 1.7 - Lisibilité métier des équipements (Backlog issu Rétro)

**User story**  
En tant qu'utilisateur Jeedom,  
je veux voir un libellé compréhensible pour mes équipements dans la vue par pièce au lieu d'un ID brut,  
afin de repérer facilement l'équipement concerné sans devoir déchiffrer des identifiants techniques.

**Dépendances autorisées:** Epic 1  
**Owner:** PM (priorisation) → Architect (vérification contrat backend)  
**Réduction de dette support:** évite à l'utilisateur de devoir chercher l'ID de l'équipement dans Jeedom pour faire la correspondance.

**Acceptance Criteria**

**Given** la console V1.1 affiche un équipement dans une pièce  
**When** l'utilisateur lit la ligne de cet équipement  
**Then** un libellé métier compréhensible est affiché à la place ou en complément de l'ID brut  
**And** si le contrat backend actuel `published_scope` ne transporte pas ce libellé, alors le resolver doit être étendu pour le fournir de manière prédictible

**Guardrails spécifiques**
- **Architecture:** Si le changement nécessite une mise à jour du contrat backend (`published_scope`), cela doit être traité intégralement dans la story, y compris l'évolution du resolver.
- **Produit:** La modification ne doit pas altérer la logique de calcul de l'héritage ni masquer un fonctionnement existant.
- **Séquencement:** C'est une story backlog distincte, pas un patch UX implicite de la console. Ne bloque pas le démarrage de l'Epic 2.

#### Epic 2 - Santé minimale du pont et lisibilité opérationnelle globale

##### Story 2.1 - Contrat backend de santé minimale

**User story**  
En tant qu'utilisateur de la console,  
je veux un contrat backend unique de santé du pont,  
afin de savoir si les actions Home Assistant sont réellement exécutables.

**Dépendances autorisées:** aucune  
**Réduction de dette support:** évite les diagnostics "bridge down" reconstitués à la main depuis plusieurs sources.

**Acceptance Criteria**

**Given** le daemon est actif  
**When** le backend expose l'état du pont  
**Then** il retourne les champs `demon`, `broker`, `derniere_synchro_terminee`, `derniere_operation_resultat`

**Given** qu'aucune opération n'a encore été exécutée depuis le démarrage  
**When** l'état du pont est demandé  
**Then** `derniere_operation_resultat` est présent avec une valeur explicite cohérente avec cet état initial  
**And** il n'est jamais omis du contrat

**Given** une erreur pendant une opération de maintenance  
**When** le contrat de santé est rafraîchi  
**Then** le résultat de dernière opération reflète explicitement `echec` ou `partiel`

##### Story 2.2 - Bandeau global de santé toujours visible

**User story**  
En tant qu'utilisateur Jeedom,  
je veux voir en permanence la santé minimale du pont dans un bandeau global compact,  
afin de distinguer en un coup d'oeil un problème d'infrastructure d'un problème de configuration.

**Dépendances autorisées:** Story 2.1  
**Réduction de dette support:** permet la qualification initiale des tickets sans navigation technique.

**Acceptance Criteria**

**Given** la console V1.1 est ouverte  
**When** les données de santé sont chargées  
**Then** un bandeau global distinct affiche `Bridge`, `MQTT`, `Dernière synchro`, `Dernière opération`

**Given** un incident d'infrastructure  
**When** il est visible dans le bandeau  
**Then** le rouge est utilisé uniquement pour cet incident  
**And** les problèmes de périmètre ou de configuration n'emploient pas ce code visuel

**Given** un petit écran ou une forte densité de contenu  
**When** l'utilisateur navigue dans la console  
**Then** le bandeau reste visible sans devenir envahissant

##### Story 2.3 - Gating des actions Home Assistant selon la santé du pont

**User story**  
En tant qu'utilisateur de la console,  
je veux que les actions Home Assistant soient bloquées proprement quand le pont n'est pas opérationnel,  
afin d'éviter des actions promises mais inexécutables.

**Dépendances autorisées:** Story 2.1, Story 2.2  
**Réduction de dette support:** évite les tickets "j'ai cliqué mais rien ne s'est passé" sans explication visible.

**Acceptance Criteria**

**Given** le daemon ou le broker MQTT est indisponible  
**When** l'utilisateur tente d'accéder à une action `Republier` ou `Supprimer puis recréer`  
**Then** l'action est désactivée ou bloquée  
**And** une raison lisible de blocage est affichée

**Given** une décision locale de périmètre  
**When** le pont est indisponible  
**Then** la modification locale reste possible  
**And** seule l'application à Home Assistant est bloquée

**Given** le pont redevient sain  
**When** l'état du bandeau est rafraîchi  
**Then** les actions Home Assistant redeviennent disponibles sans rechargement logique contradictoire

##### Story 2.4 - Distinction stable entre infrastructure et configuration

**User story**  
En tant qu'utilisateur Jeedom,  
je veux voir clairement si un problème relève de l'infrastructure ou de ma configuration,  
afin de corriger la bonne cause sans interprétation hasardeuse.

**Dépendances autorisées:** Story 2.1, Story 2.2, Story 2.3  
**Réduction de dette support:** réduit les escalades inutiles où un incident bridge est traité comme un problème de mapping.

**Acceptance Criteria**

**Given** un équipement non publié et un broker indisponible  
**When** la console affiche l'état global et les détails d'équipement  
**Then** l'incident d'infrastructure est présenté séparément d'une éventuelle raison métier de non-publication

**Given** un problème de configuration sans panne d'infrastructure  
**When** l'utilisateur lit la console  
**Then** aucun libellé ou code visuel de panne système n'est utilisé

**Given** le support consulte la console avec l'utilisateur  
**When** il qualifie la situation  
**Then** il peut identifier en première lecture si le blocage est `infrastructure`, `configuration`, `couverture`, ou `scope`

#### Epic 3 - Moteur de statuts, raisons lisibles et explicabilité backend

##### Story 3.1 - Taxonomie principale de statuts d'équipement

**User story**  
En tant qu'utilisateur de la console,  
je veux un nombre limité de statuts principaux stables,  
afin de comprendre rapidement l'état de chaque équipement.

**Dépendances autorisées:** Story 1.1, Story 2.1  
**Réduction de dette support:** supprime les badges ambigus et réduit les interprétations divergentes du statut `Partiel`.

**Acceptance Criteria**

**Given** un équipement évalué par le backend  
**When** son statut principal est calculé  
**Then** il appartient uniquement à l'ensemble `Publié`, `Exclu`, `Ambigu`, `Non supporté`, `Incident infrastructure`

**Given** un cas historiquement affiché en `Partiel`  
**When** il est réévalué au niveau équipement  
**Then** il reçoit un statut principal explicite  
**And** `Partiel` n'est utilisé qu'en agrégation ou en détail secondaire

**Given** un même équipement relu par l'UI et par un export support  
**When** le statut est affiché  
**Then** la même taxonomie principale est utilisée

##### Story 3.2 - reason_code stables, raison lisible et action recommandée

**User story**  
En tant qu'utilisateur Jeedom,  
je veux une raison principale compréhensible et une action simple quand elle existe,  
afin de corriger un non-publié sans expertise MQTT.

**Dépendances autorisées:** Story 3.1  
**Réduction de dette support:** fournit une réponse standard à "pourquoi cet équipement n'est pas publié ?".

**Acceptance Criteria**

**Given** un équipement non publié ou ambigu  
**When** le backend produit son diagnostic  
**Then** il retourne un `reason_code` stable, une raison lisible et une action recommandée optionnelle

**Given** une limite relevant de Home Assistant  
**When** la raison est affichée  
**Then** le message dit explicitement qu'il s'agit d'une limitation Home Assistant

**Given** deux exécutions du même diagnostic sur le même cas  
**When** les résultats sont comparés  
**Then** le `reason_code` est identique

##### Story 3.3 - Agrégations pièce et global cohérentes

**User story**  
En tant qu'utilisateur de la console,  
je veux des agrégations pièce/global cohérentes avec les statuts individuels,  
afin de pouvoir passer du parc à l'équipement sans contradiction.

**Dépendances autorisées:** Story 3.1, Story 3.2  
**Réduction de dette support:** évite les écarts entre lecture macro et micro qui alimentent les tickets de confiance.

**Acceptance Criteria**

**Given** une pièce contenant plusieurs équipements de statuts différents  
**When** le backend calcule son résumé  
**Then** les agrégations reflètent strictement les statuts individuels sous-jacents

**Given** un équipement basculant d'un état à un autre  
**When** la pièce et le global sont recalculés  
**Then** les compteurs et états agrégés sont mis à jour sans badge fourre-tout trompeur

**Given** un état agrégé `Partiel`  
**When** l'utilisateur ouvre la pièce concernée  
**Then** il peut retrouver les causes réelles sur les équipements concernés

##### Story 3.4 - Intégration UI en lecture seule du contrat métier backend

**User story**  
En tant qu'utilisateur Jeedom,  
je veux que l'interface affiche fidèlement le contrat métier calculé par le backend,  
afin de ne pas subir une seconde interprétation locale des statuts.

**Dépendances autorisées:** Story 3.1, Story 3.2, Story 3.3  
**Réduction de dette support:** supprime la divergence backend/UI dans la lecture des statuts et raisons.

**Acceptance Criteria**

**Given** un payload backend contenant statut, raison, action recommandée et indicateurs d'impact  
**When** l'UI affiche un équipement  
**Then** elle se contente de présenter ces données  
**And** elle n'invente ni nouvelle raison ni nouvelle règle métier

**Given** un changement de wording métier backend  
**When** le payload est mis à jour  
**Then** l'UI reflète ce wording sans recalcul parallèle

**Given** un cas de non-publication complexe  
**When** le support compare backend et UI  
**Then** les deux surfaces racontent la même histoire

#### Epic 4 - Opérations HA explicites, graduées et sûres

##### Story 4.1 - Façade backend unique des opérations V1.1

**User story**  
En tant qu'utilisateur Jeedom,  
je veux que toutes les actions Home Assistant passent par une façade backend unique,  
afin que la portée et l'intention soient gérées de manière cohérente.

**Dépendances autorisées:** Story 1.1, Story 2.1, Story 3.2  
**Réduction de dette support:** évite les comportements divergents entre opérations globales, pièce et équipement.

**Acceptance Criteria**

**Given** une action Home Assistant demandée  
**When** le backend reçoit la requête  
**Then** il la traite via une façade unique paramétrée par `intention`, `portée` et `sélection`

**Given** une même intention exécutée à des portées différentes  
**When** la façade est appelée  
**Then** le contrat de réponse reste homogène

**Given** une tentative d'orchestration locale côté UI  
**When** elle contournerait la façade  
**Then** elle est interdite par conception

##### Story 4.2 - Flux Republier non destructif multi-portée

**User story**  
En tant qu'utilisateur Jeedom,  
je veux pouvoir republier globalement ou localement sans lancer une reconstruction destructive,  
afin d'appliquer proprement mon périmètre sans crainte excessive.

**Dépendances autorisées:** Story 4.1, Story 1.4, Story 2.3  
**Réduction de dette support:** clarifie le flux nominal et réduit les tickets liés à la peur de casser Home Assistant.

**Acceptance Criteria**

**Given** une intention `Republier`  
**When** l'utilisateur choisit une portée `global`, `pièce` ou `équipement`  
**Then** le backend applique un flux explicitement non destructif par contrat  
**And** il n'emprunte aucun chemin de suppression suivie de recréation destiné à reconstruire les entités Home Assistant

**Given** un équipement déjà publié avec un `unique_id` stable  
**When** une opération `Republier` réussit sur sa portée  
**Then** le backend conserve la sémantique de continuité de l'entité existante  
**And** aucun indicateur d'intention destructive n'est exposé dans le résultat d'opération

**Given** une demande `Republier` multi-portée  
**When** le backend retourne le résultat d'exécution  
**Then** le payload de retour identifie explicitement l'intention `Republier`  
**And** il permet d'auditer qu'aucun flux `Supprimer/Recréer` n'a été substitué implicitement

**Given** une confirmation affichée pour `Republier`  
**When** l'utilisateur la lit  
**Then** l'action réelle et la portée réelle sont rappelées sans vocabulaire ambigu

**Given** des changements de périmètre en attente  
**When** `Republier` se termine avec succès  
**Then** l'état `changements à appliquer` correspondant disparaît  
**And** la console n'affiche pas ce succès comme une reconstruction destructive

##### Story 4.3 - Flux Supprimer puis recréer avec confirmations fortes

**User story**  
En tant qu'utilisateur Jeedom avancé,  
je veux lancer explicitement une reconstruction destructive avec une confirmation forte,  
afin de savoir exactement quand j'accepte un impact potentiel côté Home Assistant.

**Dépendances autorisées:** Story 4.1, Story 2.3, Story 3.2  
**Réduction de dette support:** évite les scénarios où une opération destructive est confondue avec un simple refresh.

**Acceptance Criteria**

**Given** une intention `Supprimer puis recréer`  
**When** l'utilisateur déclenche l'action  
**Then** une confirmation forte rappelle la portée réelle, le volume touché et les conséquences possibles sur historique, dashboards, automatisations et `entity_id`

**Given** l'action destructive est affichée dans l'UI  
**When** l'utilisateur parcourt le flux normal  
**Then** cette action vit dans une zone secondaire ou avancée

**Given** le bridge ou MQTT est indisponible  
**When** l'utilisateur tente `Supprimer puis recréer`  
**Then** l'action est bloquée avec une raison lisible

##### Story 4.4 - Retour d'opération lisible et mémorisation du dernier résultat

**User story**  
En tant qu'utilisateur de la console,  
je veux un retour d'opération court, lisible et mémorisé,  
afin de savoir ce qui a été lancé, sur quel périmètre, avec quel résultat.

**Dépendances autorisées:** Story 2.1, Story 4.1, Story 4.2, Story 4.3  
**Réduction de dette support:** permet de reconstituer un scénario d'opération sans croiser plusieurs journaux.

**Acceptance Criteria**

**Given** une opération Home Assistant terminée  
**When** le backend retourne son résultat  
**Then** il inclut l'intention, la portée réelle, le volume touché et un résultat court lisible

**Given** une opération réussie, partielle ou en échec  
**When** le bandeau de santé est rafraîchi  
**Then** le champ obligatoire `dernière opération` reflète ce résultat

**Given** un utilisateur ou le support revient sur la console après une action récente  
**When** il consulte l'état global  
**Then** il peut identifier l'opération la plus récente sans inspection immédiate des logs

### 9.4 Matrice simple des dépendances story-level

| Story | Dépendances autorisées | Dépendance en avant |
|---|---|---|
| 1.1 | Aucune | Non |
| 1.2 | 1.1 | Non |
| 1.3 | 1.1, 1.2 | Non |
| 1.4 | 1.1, 1.2, 1.3 | Non |
| 2.1 | Aucune | Non |
| 2.2 | 2.1 | Non |
| 2.3 | 2.1, 2.2 | Non |
| 2.4 | 2.1, 2.2, 2.3 | Non |
| 3.1 | 1.1, 2.1 | Non |
| 3.2 | 3.1 | Non |
| 3.3 | 3.1, 3.2 | Non |
| 3.4 | 3.1, 3.2, 3.3 | Non |
| 4.1 | 1.1, 2.1, 3.2 | Non |
| 4.2 | 4.1, 1.4, 2.3 | Non |
| 4.3 | 4.1, 2.3, 3.2 | Non |
| 4.4 | 2.1, 4.1, 4.2, 4.3 | Non |

### 9.5 Gate de sortie de correction

Le gate de sortie est désormais **couvert par ce document**, sous réserve d'une validation finale produit/technique:

1. Les 4 epics sont décomposés en stories implémentables.
2. 100% des stories ci-dessus ont des AC `Given / When / Then`.
3. Le caractère obligatoire du **résultat de dernière opération** est repris dans Epic 2 et Epic 4.
4. Une matrice simple des dépendances story-level existe et ne contient aucune dépendance en avant.
5. Chaque story mentionne explicitement son apport en réduction de dette support ou en prédictibilité produit.

## 10. Recommandation finale

**Recommandation: le plan de correction est prêt pour validation story-level, puis génération des fichiers story individuels.**

Le plan d'epics reste robuste, cohérent et borné, et la section 9 fournit maintenant un package story-level complet pour sortir du blocage identifié par le readiness report.

**Points à figer avant `create-story`**

Ces points ne sont pas des sujets à réouvrir; ils doivent être traités comme **invariants non renégociables** dans les stories:

1. Le modèle canonique du périmètre publié reste `global -> pièce -> équipement` avec `inherit / include / exclude` et précédence `équipement > pièce > global`.
2. Le backend reste la source unique de `statut + raison principale + action recommandée + santé minimale`.
3. Toute opération V1.1 passe par une façade backend unique paramétrée par `intention` et `portée`.
4. `Republier` reste non destructif par intention; `Supprimer/Recréer` reste le seul flux destructif explicite.
5. Le résultat de dernière opération fait partie du contrat minimal visible V1.1.
6. Les frontières hors scope restent gelées:
   - pas d'extension fonctionnelle;
   - pas de preview complète;
   - pas de remédiation guidée avancée;
   - pas de santé avancée;
   - pas de support outillé avancé;
   - pas d'alignement Homebridge.

Si ces invariants sont repris tels quels, ce document peut désormais servir de source unique pour créer les fichiers story individuels sans reprise de cadrage epic-level.
