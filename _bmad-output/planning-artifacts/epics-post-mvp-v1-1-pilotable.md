---
workflowType: 'epic_planning'
workflow: 'create-epics-and-stories'
project: 'jeedom2ha'
phase: 'post_mvp_phase_1'
version_label: 'v1.1_pilotable'
date: '2026-03-27'
status: 'realigned_with_recadrage_ux'
planningScope: 'epics_with_story_breakdown'
inputDocuments:
  - _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-post-mvp-refresh.md
  - _bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-26.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-03-27.md
secondaryContextDocuments:
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/project-context.md
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
lastEdited: '2026-03-27'
editHistory:
  - date: '2026-03-27'
    changes: 'Recadrage UX — insertion Epic 4 (modèle Périmètre/Statut/Écart/Cause, contrat dual reason_code/cause_code, diagnostic in-scope, disparition exception), renumérotation Epic 5 (ex-Epic 4 opérations HA), réalignement vocabulaire documentaire Epics 1-3.'
  - date: '2026-03-22'
    changes: 'Création initiale — 4 epics V1.1 Pilotable avec story breakdown.'
---

# Plan d'epics Post-MVP V1.1 Pilotable

## 1. Executive summary

Le plan pour **Post-MVP Phase 1 - V1.1 Pilotable** comporte **5 epics**.

Les **Epics 1, 2 et 3 sont livrés**. Ils constituent les fondations backend et UI du bridge pilotable : resolver canonique de périmètre, santé minimale du pont, moteur de statuts et `reason_code` stables.

Le **Sprint Change Proposal du 2026-03-26** (approuvé) a identifié un désalignement entre le modèle d'implémentation interne et le modèle mental utilisateur. Les artefacts amont (PRD, UX delta review, Architecture delta review) ont été mis à jour en conséquence.

Ce recadrage est porté par un **nouvel Epic 4** dédié, qui aligne la couche de présentation sur le modèle utilisateur à 4 dimensions **Périmètre → Statut → Écart → Cause**. L'ancien Epic 4 (opérations HA) est renuméroté **Epic 5**.

Le découpage reste centré sur des **contrats stables**, pas sur des écrans isolés :
1. modèle canonique du périmètre publié (Epic 1 — livré) ;
2. contrat minimal de santé du pont (Epic 2 — livré) ;
3. infrastructure backend des statuts et `reason_code` stables (Epic 3 — livré) ;
4. modèle utilisateur Périmètre / Statut / Écart / Cause et contrat UI canonique (Epic 4 — backlog) ;
5. façade unique d'opérations HA explicites (Epic 5 — backlog).

Le plan est cohérent avec le cadrage validé :
- priorité absolue au **pilotage du bridge** et à la **maîtrise du périmètre publié** ;
- aucune anticipation d'extension fonctionnelle `button → number → select → climate` ;
- aucune dérive vers preview complète, remédiation guidée avancée, santé avancée, support outillé avancé ou alignements Homebridge.

## 2. Rappel du périmètre V1.1 Pilotable

**Périmètre in**
- Console de pilotage pensée sur trois niveaux explicites : `global → pièce → équipement`.
- Vue par pièce comme point d'entrée principal, sans devenir l'unique modèle de lecture.
- Inclusion/exclusion par pièce avec décisions d'inclusion/exclusion par équipement, exprimées par leur source (pièce, plugin, équipement).
- Modèle utilisateur à 4 dimensions : Périmètre → Statut → Écart → Cause.
- Compteurs (Total, Inclus, Exclus, Écarts) comme lecture principale aux niveaux pièce et global.
- Statut binaire `Publié` / `Non publié` au niveau équipement uniquement.
- Écart bidirectionnel : inclus mais non publié, ou exclu mais encore publié.
- Cause métier lisible pour chaque écart, dérivée des `reason_code` backend via `cause_code` / `cause_label`.
- Diagnostic utilisateur centré sur les équipements in-scope ; confiance visible uniquement en diagnostic technique.
- Opérations discovery explicites et distinctes :
  - `Republier dans Home Assistant`
  - `Supprimer puis recréer dans Home Assistant`
- Santé minimale du pont visible : démon, broker MQTT, dernière synchronisation terminée, résultat court obligatoire de la dernière opération.
- Retour opérationnel lisible pour les actions à impact côté Home Assistant.

**Périmètre out**
- Extension fonctionnelle future : `button`, `number`, `select`, `climate` minimal/strict.
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
- Le modèle Périmètre / Statut / Écart / Cause est lisible et cohérent pour chaque équipement.
- Chaque écart dispose d'une cause métier lisible.
- Le diagnostic utilisateur est centré sur les équipements in-scope.
- La distinction `reason_code` (backend stable) / `cause_code` + `cause_label` (contrat UI) est respectée.

### Guardrails UX

- La console doit rester pensée sur trois niveaux explicites :
  - `Global`
  - `Pièce`
  - `Équipement`
- La pièce est le bon niveau de pilotage, mais pas l'unique niveau d'analyse.
- Le modèle utilisateur repose sur 4 dimensions : **Périmètre → Statut → Écart → Cause**.
- Le statut binaire `Publié` / `Non publié` n'existe qu'au niveau équipement.
- Les niveaux pièce et global sont lus par **compteurs** : Total, Inclus, Exclus, Écarts.
- Le concept d'**exception** a disparu. Les exclusions sont exprimées par leur source : `Exclu par la pièce`, `Exclu par le plugin`, `Exclu sur cet équipement`.
- Le diagnostic utilisateur ne porte que sur les équipements in-scope (`périmètre = Inclus`).
- La confiance (`Sûr` / `Probable` / `Ambigu`) n'est visible qu'en diagnostic technique, jamais en console.
- `Partiellement publié` n'est pas un statut principal de console ; il reste un indicateur de diagnostic détaillé de couverture.
- Le vocabulaire d'action primaire est figé :
  - `Republier dans Home Assistant`
  - `Supprimer puis recréer dans Home Assistant`
- Les confirmations sont graduées selon l'action, la portée et l'impact potentiel côté HA.
- La santé minimale du pont doit vivre dans un bandeau ou niveau global distinct.
- Le contrat backend → UI fournit les 4 dimensions pré-calculées. Le frontend ne fait aucune interprétation.
- Les termes interdits en UI incluent : `Hérite de la pièce`, `Exception locale`, `is_exception`, `decision_source`, `inherit`, `include`/`exclude` en anglais, `Partiellement publié` comme statut principal, `Ambigu` comme statut, `Non supporté` comme statut, compteur `Exceptions`.

### Guardrails architecture

- Pas de refonte complète : conserver le socle **daemon + pipeline central + cache technique + diagnostic**.
- Le modèle canonique du périmètre publié reste :
  - hiérarchie `global → pièce → équipement` ;
  - états internes `inherit / include / exclude` ;
  - précédence explicite `équipement > pièce > global`.
- La couche de présentation traduit la résolution interne en source d'exclusion lisible (`inclus`, `exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement`). Le frontend ne voit jamais `inherit`.
- Le backend expose un contrat UI canonique à 4 dimensions : `perimetre`, `statut`, `ecart`, `cause_code` / `cause_label` / `cause_action`.
- Les `reason_code` (Epic 3) restent stables et non exposés en UI. La couche `cause_code` / `cause_label` est dérivée par une table de traduction (fonction pure) ajoutée en sortie du pipeline.
- Les compteurs (Total, Inclus, Exclus, Écarts) sont pré-calculés par le backend. Le frontend ne fait aucun calcul de compteur local.
- L'écart est un booléen pré-calculé par le backend (comparaison décision effective ↔ état projeté HA).
- Le diagnostic utilisateur est filtré in-scope côté backend.
- Toute opération V1.1 passe par une **façade backend unique**.
- La portée (`global / pièce / équipement`) et l'intention (`Republier / Supprimer-Recréer`) sont des paramètres de cette façade.
- Le backend est la source unique de statut, cause, action recommandée, compteurs.
- La santé minimale du pont reste légère et contractuelle : démon, broker, dernière synchronisation terminée, résultat court obligatoire de la dernière opération.
- Les invariants HA doivent être protégés :
  - `unique_id` stable tant que l'ID Jeedom est stable ;
  - `Republier` = intention non destructive ;
  - `Supprimer/Recréer` = seul flux destructif explicite ;
  - recalcul du scope déterministe pour une configuration et un snapshot donnés.

## 4. Règles de découpage retenues pour les epics

- Les epics sont organisés par **résultat utilisateur opérationnel**, pas par couche technique ni par écran.
- Les guardrails UX et architecture sont portés **au niveau epic**, pas reportés dans des stories ultérieures.
- La séparation entre **décision locale**, **projection effective vers HA** et **impact visible pour l'utilisateur** doit rester intacte dans chaque epic.
- Les epics V1.1 ne doivent jamais devenir un cheval de Troie pour l'extension fonctionnelle future.
- Le séquencement recommandé privilégie d'abord le **coeur de contrat stable**, puis les actions à impact fort.
- Le découpage conserve le socle MVP et ajoute uniquement les deltas nécessaires à une version pilotable.
- Les cinq axes prioritaires du PRD sont couverts explicitement, sans fusion.

| Axe prioritaire validé | Epic retenu | Pourquoi ce découpage |
|---|---|---|
| Console de pilotage par pièce + décisions d'inclusion/exclusion par source | Epic 1 (livré) | Nécessite un contrat de périmètre stable et visible avant toute opération sensible |
| Santé minimale du pont et retour opérationnel visible | Epic 2 (livré) | Doit exister comme contrat distinct pour ne pas être absorbée dans les statuts ou l'UI |
| Infrastructure backend des statuts et `reason_code` stables | Epic 3 (livré) | Doit rester un moteur backend unifié et autonome, pas un détail de rendu |
| Modèle utilisateur Périmètre / Statut / Écart / Cause et contrat UI canonique | Epic 4 (backlog) | Aligne la couche de présentation sur le modèle mental utilisateur, prérequis aux opérations |
| Opérations discovery explicites et sécurité d'usage | Epic 5 (backlog) | Porte les invariants HA les plus sensibles et doit s'appuyer sur le modèle utilisateur stabilisé |

## 5. Liste des epics recommandés pour V1.1 Pilotable

### Epic 1 — Coeur de périmètre pilotable et console 3 niveaux

**Statut : livré.** Les ajustements de vocabulaire ci-dessous réalignent l'artefact documentaire avec le recadrage UX validé. Le scope et l'implémentation de cet epic ne sont pas modifiés. La transition effective du vocabulaire utilisateur est portée par l'Epic 4.

**Objectif**

Installer le contrat de périmètre pilotable V1.1 et la console `global → pièce → équipement`, avec la pièce comme point d'entrée principal, sans perdre la lecture globale ni la compréhension des décisions d'exclusion par source.

**Valeur utilisateur**

L'utilisateur peut enfin décider, comprendre et relire ce qui doit faire partie du périmètre publié dans HA, à la bonne granularité, sans disparition silencieuse des exclus ni logique implicite d'héritage.

**Problème utilisateur traité**

L'utilisateur ne maîtrise pas précisément ce qui est publié dans Home Assistant et ne comprend pas toujours pourquoi un équipement est inclus ou exclu.

**Périmètre in**
- Modèle canonique de périmètre publié `global → pièce → équipement`.
- États de décision internes `inherit / include / exclude` avec précédence `équipement > pièce > global`.
- Vue globale de synthèse distincte de la vue par pièce.
- Pilotage par pièce avec décisions d'inclusion/exclusion par équipement.
- Visibilité continue des équipements exclus et de la source de décision.
- Compteurs globaux et par pièce cohérents avec le modèle canonique.
- Signal explicite quand une décision locale modifie le périmètre voulu sans présumer de son effet immédiat côté HA.

**Périmètre out**
- Preview complète du résultat HA avant application.
- Opérations destructives côté HA.
- Parcours de remédiation avancé.
- Extension du scope fonctionnel au-delà du périmètre MVP déjà couvert.
- Filtres techniques plugin comme modèle principal de lecture.

**Dépendances**
- Réutilise le socle MVP existant : topologie, diagnostic, exclusions déjà présentes.
- Ne dépend d'aucun epic futur pour résoudre la décision effective de périmètre.
- Fournit le contrat de base consommé ensuite par les epics 2, 3, 4 et 5.

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
- Réduction de dette support : en régime nominal, le support peut reconstruire le périmètre effectif et la source de décision sans lecture de logs bruts.

**Guardrails UX à respecter**
- La console doit afficher trois niveaux explicites, même si la pièce reste le point d'entrée principal.
- La vue par pièce ne doit pas masquer la lecture globale.
- La densité doit rester maîtrisée : synthèse au niveau global, compteurs au niveau pièce, détail explicatif au niveau équipement.
- La séparation `périmètre local` vs `projection effective vers HA` doit être perceptible dès cet epic.

**Guardrails architecture à respecter**
- Le modèle canonique du périmètre publié doit devenir la référence unique.
- Le calcul de décision effective doit être centralisé dans un resolver backend unique.
- Aucun écran ne doit reconstruire sa propre logique d'héritage.
- Le socle daemon + pipeline + cache technique + diagnostic est conservé.
- Le recalcul du périmètre doit rester déterministe et testable.

### Epic 2 — Santé minimale du pont et lisibilité opérationnelle globale

**Statut : livré.** Aucun ajustement de vocabulaire nécessaire. Le scope et l'implémentation de cet epic ne sont pas modifiés.

**Objectif**

Rendre visible, en permanence et au bon niveau, l'état minimal du pont afin que l'utilisateur distingue immédiatement un problème d'infrastructure d'un problème de périmètre ou de couverture.

**Valeur utilisateur**

L'utilisateur sait d'un coup d'oeil si le bridge, MQTT et la dernière synchronisation sont en état compatible avec les actions attendues, sans devoir ouvrir un écran technique ni interpréter des logs.

**Problème utilisateur traité**

La santé minimale du pont n'est pas suffisamment visible, ce qui entretient la confusion entre panne de bridge, problème de configuration locale et limite de publication.

**Périmètre in**
- Contrat minimal de santé produit par le backend :
  - démon ;
  - broker MQTT ;
  - dernière synchronisation terminée ;
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
- Devient ensuite une dépendance explicite pour les epics 3, 4 et 5.

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
- Réduction de dette support : la première qualification d'un ticket "rien ne se passe dans HA" peut se faire depuis le bandeau global sans inspection immédiate des logs daemon.

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

### Epic 3 — Moteur de statuts, reason_code stables et explicabilité

**Statut : livré.** Les ajustements de vocabulaire ci-dessous réalignent l'artefact documentaire avec le recadrage UX validé. Le scope et l'implémentation de cet epic ne sont pas modifiés. Epic 3 a établi l'infrastructure backend (`reason_code`, raisons lisibles, actions recommandées) sur laquelle l'Epic 4 construit la couche de traduction UI (`cause_code` / `cause_label`).

**Objectif**

Unifier côté backend la production des statuts, `reason_code` stables et actions recommandées pour que chaque équipement raconte une histoire cohérente, lisible et explicable.

**Valeur utilisateur**

L'utilisateur comprend rapidement pourquoi un équipement est publié ou non publié, et sait quelle action simple est pertinente quand elle existe.

**Problème utilisateur traité**

Le produit risque sinon de retomber dans un modèle où un seul badge tente de tout dire, où la logique de statut se disperse entre backend et frontend, et où les causes de non-publication restent opaques.

**Périmètre in**
- Infrastructure backend de statuts séparant au minimum : périmètre, état de publication, `reason_code` stable, incident infrastructure.
- `reason_code` stables, raison lisible, action recommandée simple optionnelle.
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
- Fournit l'infrastructure `reason_code` indispensable à l'epic 4 (couche `cause_code` / `cause_label`).
- Fournit le contrat sémantique consommé par l'epic 5.

**Risques / points de vigilance**
- Laisser le frontend inventer ou recomposer des raisons métier.
- Produire trop de statuts différents et dégrader la lisibilité.
- Masquer les limites Home Assistant dans des messages trop techniques ou trop vagues.

**Critères de succès epic-level**
- Plus de 95% des équipements visibles en console disposent d'un `reason_code` stable côté backend, exploitable par la couche `cause_code` / `cause_label` du contrat UI.
- Les raisons principales sont cohérentes entre backend, UI et support.
- Réduction de dette support : la réponse standard à "pourquoi cet équipement n'est pas publié ?" est obtenable depuis le payload de statut, sans interprétation ad hoc des logs dans les cas nominaux.

**Guardrails UX à respecter**
- Séparer visuellement statut de publication, cause métier et santé du pont.
- Conserver une structure standard de message : statut, cause métier, action recommandée, impact HA si pertinent.
- Dire explicitement quand la limite vient de Home Assistant.
- Ne pas transformer la vue par pièce en cache-misère qui masque les équipements problématiques transverses.

**Guardrails architecture à respecter**
- Le backend est la source unique de `statut + reason_code + action recommandée`.
- Les `reason_code` doivent rester stables et gouvernés côté backend.
- L'incident infrastructure doit être un motif explicite.
- La logique existante de diagnostic est étendue, pas dupliquée.
- Aucun écran ne doit recalculer ses propres règles métier.

### Epic 4 — Recadrage UX : modèle utilisateur Périmètre / Statut / Écart / Cause

**Statut : backlog.** Nouvel epic issu du Sprint Change Proposal du 2026-03-26.

**Objectif**

Aligner la console et le diagnostic sur le modèle mental utilisateur à 4 dimensions, en éliminant les concepts techniques internes de l'interface et en centrant le diagnostic sur les équipements in-scope.

**Valeur utilisateur**

L'utilisateur comprend immédiatement si un équipement est dans son périmètre, s'il est publié, s'il y a un écart et pourquoi — sans vocabulaire technique ni concepts d'implémentation.

**Problème utilisateur traité**

L'interface de la console V1.1 expose directement le modèle d'implémentation interne à l'utilisateur : la taxonomie backend à 6 statuts, les concepts `Hérite de la pièce` / `Exception locale`, la confiance tripartite et le compteur séparé `Exceptions` sont projetés tels quels dans l'UI au lieu d'être traduits en modèle mental utilisateur.

**Périmètre in**
- Contrat backend → UI du modèle à 4 dimensions : `perimetre`, `statut` (binaire), `ecart` (booléen bidirectionnel), `cause_code` / `cause_label` / `cause_action`.
- Couche de traduction `reason_code` → `cause_code` / `cause_label` (fonction pure, table de correspondance).
- Vocabulaire d'exclusion par source (`exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement`) — disparition du concept exception.
- Compteurs backend pré-calculés (Total, Inclus, Exclus, Écarts) aux niveaux pièce et global.
- Diagnostic utilisateur filtré in-scope côté backend.
- Confiance déplacée vers le diagnostic technique uniquement.
- Absorption de `Partiellement publié` : le statut principal devient `Publié`, le détail de couverture commandes reste un indicateur de diagnostic détaillé.
- Intégration UI en lecture seule du modèle 4 dimensions (console + diagnostic).
- Alignement console/diagnostic sur la même taxonomie de base.

**Périmètre out**
- Modification du resolver canonique (Epic 1 — ne change pas).
- Modification du contrat de santé (Epic 2 — ne change pas).
- Renommage des `reason_code` stables (Epic 3 — restent stables, seule la couche `cause_code` / `cause_label` est ajoutée).
- Opérations HA (Epic 5).
- Extension fonctionnelle (button, number, select, climate).

**Dépendances**
- S'appuie sur l'epic 1 pour le resolver canonique et le périmètre `global → pièce → équipement`.
- S'appuie sur l'epic 2 pour le contrat de santé et la distinction infrastructure/configuration.
- S'appuie sur l'epic 3 pour les `reason_code` stables et le moteur de diagnostic backend.
- Fournit le modèle utilisateur stabilisé consommé ensuite par l'epic 5.

**Risques / points de vigilance**
- Réintroduire du vocabulaire d'implémentation dans le frontend (inherit, exception, decision_source).
- Laisser le frontend dériver un statut, recomposer une cause ou calculer un compteur.
- Confondre la traduction `reason_code` → `cause_code` avec un renommage des `reason_code` eux-mêmes.
- Ignorer l'écart de direction 2 (exclu mais encore publié).
- Transformer `Partiellement publié` en statut principal au lieu d'un indicateur de diagnostic.

**Critères de succès epic-level**
- Le concept "exception" a disparu de toute l'interface utilisateur.
- Chaque équipement est lisible selon le modèle Périmètre / Statut / Écart / Cause.
- La confiance n'apparaît que dans la page diagnostic technique.
- Le diagnostic principal ne montre que les équipements in-scope.
- Aucun terme technique interne n'est visible en frontend.
- Les compteurs pièce/global sont Total / Inclus / Exclus / Écarts.
- Le statut binaire Publié / Non publié n'existe qu'au niveau équipement.
- Le contrat backend → UI suit la forme JSON cible verrouillée (§V3 du Sprint Change Proposal).
- La distinction `reason_code` (backend stable) / `cause_code` (contrat UI) est respectée.
- L'export support complet reste fonctionnel et exhaustif.
- Réduction de dette support : les tickets "incompréhension de publication" diminuent grâce à un vocabulaire métier clair et un diagnostic centré sur ce qui compte.

**Guardrails UX à respecter**
- Le modèle à 4 dimensions est le seul modèle de lecture de la console.
- Le statut binaire `Publié` / `Non publié` est strictement au niveau équipement.
- Les niveaux pièce/global sont lus par compteurs uniquement.
- Aucun des termes interdits (§6.2 UX delta review) n'apparaît en interface.
- La confiance est réservée au diagnostic technique, jamais à la console.
- `Partiellement publié` n'est pas un statut principal.
- La structure standard de message par équipement en écart est : statut, cause, action recommandée, impact HA si pertinent.

**Guardrails architecture à respecter**
- Les `reason_code` (Epic 3) ne sont pas renommés ni modifiés.
- La couche `cause_code` / `cause_label` est ajoutée en sortie du pipeline par une table de correspondance.
- L'écart est un booléen pré-calculé par le backend (formule : décision ↔ état projeté).
- Les compteurs sont des agrégations backend, jamais des calculs frontend.
- Le filtrage diagnostic in-scope est un `WHERE perimetre = 'inclus'` côté backend.
- Le frontend ne fait aucune interprétation — il affiche les 4 dimensions telles quelles.
- Le resolver canonique (inherit/include/exclude) n'est pas modifié.

### Epic 5 — Opérations HA explicites, graduées et sûres

**Statut : backlog.** Renuméroté depuis l'ancien Epic 4 suite au Sprint Change Proposal du 2026-03-26. L'intention produit et le scope restent inchangés. Les ajustements sont principalement terminologiques et contractuels : les opérations utilisent désormais le vocabulaire et le modèle 4 dimensions stabilisés par l'Epic 4.

**Objectif**

Rendre les opérations `Republier` et `Supprimer puis recréer` explicites, cohérentes et sûres aux portées `global / pièce / équipement`, en protégeant les invariants d'impact Home Assistant.

**Valeur utilisateur**

L'utilisateur peut lancer la bonne opération, à la bonne portée, avec le bon niveau de confirmation, sans confondre mise à jour non destructive et reconstruction destructrice côté HA.

**Problème utilisateur traité**

Les opérations de maintenance discovery sont aujourd'hui trop confondues, anxiogènes ou insuffisamment explicites sur leurs conséquences côté Home Assistant.

**Périmètre in**
- Façade backend unique d'opérations V1.1.
- Paramètres explicites de la façade :
  - intention : `Republier` ou `Supprimer/Recréer` ;
  - portée : `global`, `pièce`, `équipement` ;
  - sélection cible.
- Sémantique figée :
  - `Republier` = intention non destructive ;
  - `Supprimer/Recréer` = seul flux destructif explicite.
- Confirmation graduée selon action, portée et impact.
- Présentation explicite de la portée réelle et du nombre d'équipements touchés.
- Rappel visible des conséquences potentielles côté HA : historique, dashboards, automatisations, `entity_id` éventuellement modifié selon les règles HA.
- Résultat d'opération lisible et court après exécution.
- Gating des actions HA selon l'état minimal du pont.
- Réponses d'opération conformes au modèle 4 dimensions (périmètre, statut, écart, cause).
- Séparation maintenue entre décision locale de périmètre, application à Home Assistant, impact visible pour l'utilisateur.

**Périmètre out**
- Preview complète avant/après.
- Assistant de remédiation guidée.
- Outils massifs de batch management avancé.
- Alignements Homebridge-like.
- Extension du périmètre fonctionnel.

**Dépendances**
- S'appuie sur l'epic 1 pour le scope canonique et la portée.
- S'appuie sur l'epic 2 pour le gating et la lisibilité infrastructurelle.
- S'appuie sur l'epic 3 pour les `reason_code`, la lisibilité des raisons, impacts et résultats.
- S'appuie sur l'epic 4 pour le modèle utilisateur 4 dimensions et le contrat UI canonique.

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
- Les réponses d'opération utilisent le vocabulaire du modèle 4 dimensions.
- Réduction de dette support : pour une opération sensible, le support peut identifier depuis le retour opérationnel quelle action a été lancée, sur quel périmètre et avec quel résultat court, sans devoir reconstituer le scénario à partir d'indices dispersés.

**Guardrails UX à respecter**
- Les libellés d'action restent strictement :
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
| Preview complète | Le plan admet seulement des compteurs, un état d'écart et des causes résumées, jamais une simulation complète avant/après |
| Remédiation guidée avancée | Le plan autorise seulement une action recommandée simple, pas d'assistant multi-étapes ni d'automatisation corrective |
| Santé avancée du pont | La santé reste limitée à `démon`, `broker`, `dernière synchro terminée`, résultat court obligatoire de dernière opération |
| Support outillé avancé | Le plan améliore la lisibilité support, mais n'ajoute pas d'outillage lourd ou de console support avancée |
| Options tardives type Homebridge | Aucun epic ne dépend d'un pattern Homebridge ni ne le prend comme cible de convergence |

Conclusion : **les epics V1.1 restent strictement dans la frontière "pilotage du bridge / maîtrise du périmètre publié".**

## 7. Ordre recommandé d'exécution des epics

1. **Epic 1 — Coeur de périmètre pilotable et console 3 niveaux** (livré)
   Premier car il fixe le contrat racine `global → pièce → équipement` et la séparation entre décision locale et projection effective.

2. **Epic 2 — Santé minimale du pont et lisibilité opérationnelle globale** (livré)
   Deuxième car les actions et les statuts doivent pouvoir s'appuyer sur une vérité infrastructurelle minimale clairement visible.

3. **Epic 3 — Moteur de statuts, reason_code stables et explicabilité** (livré)
   Troisième car il consolide l'infrastructure backend de diagnostic sur le périmètre et la santé déjà stabilisés.

4. **Epic 4 — Recadrage UX : modèle utilisateur Périmètre / Statut / Écart / Cause** (backlog — prochain)
   Quatrième car il aligne la couche de présentation sur le modèle mental utilisateur, en s'appuyant sur les fondations des Epics 1-3 et en stabilisant le vocabulaire avant les opérations HA.

5. **Epic 5 — Opérations HA explicites, graduées et sûres** (backlog)
   Dernier car il porte les impacts HA les plus sensibles et doit s'appuyer sur un scope canonique, une santé minimale fiable, une explicabilité déjà en place et un modèle utilisateur stabilisé.

Cet ordre ne remet pas en cause la priorité produit du PRD. Il sécurise la mise en oeuvre autour d'un contrat stable avant d'ouvrir les flux à impact fort.

## 8. Vérification finale

**Le découpage est-il bien centré sur un coeur de contrat stable, et non sur des écrans isolés ?**

**Oui.**

Le plan est centré sur cinq contrats stables :
- **Epic 1** porte le contrat de périmètre et de précédence.
- **Epic 2** porte le contrat minimal de santé du pont.
- **Epic 3** porte l'infrastructure backend `reason_code / raison lisible / action recommandée`.
- **Epic 4** porte le contrat UI canonique à 4 dimensions et la traduction `reason_code` → `cause_code`.
- **Epic 5** porte le contrat d'opérations explicites et de sécurité d'usage.

Ce que le plan **ne fait pas** :
- il ne découpe pas par écran `global`, `pièce`, `équipement` ;
- il ne découpe pas par bouton `Republier` ou `Supprimer/Recréer` ;
- il ne renvoie pas les décisions structurantes UX/architecture au niveau story.

Signal faible à surveiller au passage vers `create-story` :
- si les stories futures se mettent à découper "la vue globale", "la ligne pièce", "le bouton republier", sans rappeler le contrat backend unique qu'elles servent, alors le découpage dérive hors du cadrage validé.

## 9. Plan de correction readiness et décomposition story-level

### 9.1 Blocages à lever

- Le readiness report du 2026-03-22 avait identifié l'absence d'un package story-level prêt à implémenter.
- Le Sprint Change Proposal du 2026-03-26 ajoute un nouvel epic (recadrage UX) et une renumérotation.
- La présente section 9 fournit la décomposition story-level complète pour les 5 epics.

### 9.2 Correction documentaire obligatoire

Règles non négociables pour toutes les stories :

1. Le champ **résultat de dernière opération** est obligatoire dans le contrat V1.1.
2. Aucune story ne peut réintroduire une logique métier calculée dans le frontend.
3. Aucune story ne peut masquer la séparation entre décision locale de périmètre et application à Home Assistant.
4. Aucune story ne peut dépendre d'une story future pour fonctionner nominalement.
5. Chaque story doit porter explicitement une réduction de dette support ou de prédictibilité produit.
6. Aucune story ne doit réintroduire le concept d'exception ou d'héritage comme vocabulaire utilisateur.
7. Le modèle **Périmètre / Statut / Écart / Cause** est la seule taxonomie autorisée pour l'exposition UI des statuts d'équipement.
8. La **confiance** ne doit jamais apparaître en console principale.
9. La distinction `reason_code` (backend stable) / `cause_code` + `cause_label` (contrat UI canonique) est structurante.
10. `Partiellement publié` ne doit jamais apparaître comme statut principal de console.

### 9.3 Décomposition story-level complète

#### Epic 1 — Coeur de périmètre pilotable et console 3 niveaux (livré)

> Note : les stories ci-dessous sont livrées. Le vocabulaire est réaligné pour cohérence documentaire avec le recadrage UX validé. Le scope implémenté n'est pas modifié ; la transition effective du vocabulaire utilisateur est portée par l'Epic 4.

> **Note numérotation :** Les identifiants 1.5 et 1.6 sont absents de la liste ci-dessous. Ces numéros ont été retirés ou abandonnés en cours de construction du plan initial. Aucun artefact disponible ne documente leur contenu précis. La séquence 1.1 → 1.2 → 1.3 → 1.4 → 1.7 conserve intentionnellement ces identifiants vacants pour ne pas renuméroter les stories existantes.

##### Story 1.1 — Resolver canonique du périmètre publié

**User story**
En tant qu'utilisateur Jeedom avancé,
je veux que le périmètre publié soit calculé par un resolver backend unique,
afin que les décisions `global → pièce → équipement` soient prédictibles et explicables.

**Dépendances autorisées :** aucune
**Réduction de dette support :** supprime les relectures manuelles de règles d'héritage contradictoires entre backend et UI.

**Acceptance Criteria**

**Given** une configuration de périmètre contenant des règles `global`, `pièce` et `équipement`
**When** le backend calcule la décision effective d'un équipement
**Then** il applique strictement les états `inherit`, `include`, `exclude` avec précédence `équipement > pièce > global`

**Given** un équipement explicitement inclus dans une pièce exclue
**When** la décision effective est calculée
**Then** la décision retournée est `include`
**And** la source de décision retournée est l'équipement lui-même

**Given** une même configuration rejouée sur un même snapshot
**When** le resolver est exécuté plusieurs fois
**Then** il produit exactement les mêmes décisions et compteurs

##### Story 1.2 — Vue globale et synthèse par pièce sans recalcul frontend

**User story**
En tant qu'utilisateur de la console,
je veux voir un résumé global et des synthèses par pièce fiables,
afin de comprendre rapidement le périmètre voulu sans ambiguïté de calcul.

**Dépendances autorisées :** Story 1.1
**Réduction de dette support :** évite les écarts de lecture entre compteurs UI et état backend réel.

**Acceptance Criteria**

**Given** un périmètre calculé par le resolver backend
**When** l'UI charge la console V1.1
**Then** elle affiche un résumé global et une synthèse par pièce issus uniquement du payload backend

**Given** une pièce contenant des inclusions et des exclusions
**When** la synthèse est affichée
**Then** les compteurs reflètent exactement les décisions effectives retournées par le backend

**Given** une modification locale de périmètre
**When** l'UI rafraîchit les synthèses
**Then** elle ne recalcule aucune logique métier côté frontend
**And** elle réaffiche uniquement les données recalculées par le backend

##### Story 1.3 — Exclusions par source et visibilité continue des exclus

**User story**
En tant qu'utilisateur Jeedom,
je veux voir les décisions d'exclusion avec leur source et les équipements exclus sans disparition silencieuse,
afin de relire précisément pourquoi un équipement est ou n'est pas dans mon scope.

**Dépendances autorisées :** Story 1.1, Story 1.2
**Réduction de dette support :** permet de reconstruire la source de décision sans inspection de logs bruts.

**Acceptance Criteria**

**Given** un équipement exclu volontairement
**When** l'utilisateur consulte la pièce correspondante
**Then** l'équipement reste visible dans la console
**And** la source de sa décision d'exclusion est affichée explicitement

**Given** un équipement exclu parce que sa pièce est exclue
**When** l'utilisateur consulte son détail
**Then** la source d'exclusion indique que la décision provient de la pièce

**Given** un équipement explicitement exclu par l'utilisateur
**When** l'utilisateur consulte son détail
**Then** la source d'exclusion indique que la décision porte sur cet équipement spécifiquement

##### Story 1.4 — Changements locaux en attente d'application Home Assistant

**User story**
En tant qu'utilisateur Jeedom,
je veux distinguer une décision locale de périmètre d'une action effectivement appliquée à Home Assistant,
afin de ne pas croire qu'un toggle modifie instantanément HA.

**Dépendances autorisées :** Story 1.1, Story 1.2, Story 1.3
**Réduction de dette support :** réduit les tickets issus de la confusion "j'ai exclu mais HA n'a pas encore changé".

**Acceptance Criteria**

**Given** une modification locale d'inclusion ou d'exclusion
**When** l'utilisateur revient sur la console
**Then** un signal de changement en attente d'application à Home Assistant est visible au niveau pertinent

**Given** des changements locaux non encore appliqués
**When** l'utilisateur consulte la synthèse globale ou la pièce
**Then** l'UI n'affiche pas ces changements comme déjà effectifs côté Home Assistant

**Given** des changements locaux en attente et aucune opération Home Assistant encore confirmée
**When** l'utilisateur recharge la console ou navigue entre les niveaux `global`, `pièce` et `équipement`
**Then** le signal de changement en attente reste visible de manière cohérente
**And** il dépend uniquement du payload backend, sans recalcul métier frontend

##### Story 1.7 — Lisibilité métier des équipements (Backlog issu Rétro)

**User story**
En tant qu'utilisateur Jeedom,
je veux voir un libellé compréhensible pour mes équipements dans la vue par pièce au lieu d'un ID brut,
afin de repérer facilement l'équipement concerné sans devoir déchiffrer des identifiants techniques.

**Dépendances autorisées :** Epic 1
**Owner :** PM (priorisation) → Architect (vérification contrat backend)
**Réduction de dette support :** évite à l'utilisateur de devoir chercher l'ID de l'équipement dans Jeedom pour faire la correspondance.

**Acceptance Criteria**

**Given** la console V1.1 affiche un équipement dans une pièce
**When** l'utilisateur lit la ligne de cet équipement
**Then** un libellé métier compréhensible est affiché à la place ou en complément de l'ID brut
**And** si le contrat backend actuel ne transporte pas ce libellé, alors le resolver doit être étendu pour le fournir de manière prédictible

**Guardrails spécifiques**
- **Architecture :** Si le changement nécessite une mise à jour du contrat backend, cela doit être traité intégralement dans la story, y compris l'évolution du resolver.
- **Produit :** La modification ne doit pas altérer la logique de calcul de l'héritage ni masquer un fonctionnement existant.
- **Séquencement :** C'est une story backlog distincte, pas un patch UX implicite de la console. Ne bloque pas le démarrage des Epics suivants.

#### Epic 2 — Santé minimale du pont et lisibilité opérationnelle globale (livré)

> Note : les stories ci-dessous sont livrées. Aucun ajustement de vocabulaire nécessaire.

##### Story 2.1 — Contrat backend de santé minimale

**User story**
En tant qu'utilisateur de la console,
je veux un contrat backend unique de santé du pont,
afin de savoir si les actions Home Assistant sont réellement exécutables.

**Dépendances autorisées :** aucune
**Réduction de dette support :** évite les diagnostics "bridge down" reconstitués à la main depuis plusieurs sources.

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

##### Story 2.2 — Bandeau global de santé toujours visible

**User story**
En tant qu'utilisateur Jeedom,
je veux voir en permanence la santé minimale du pont dans un bandeau global compact,
afin de distinguer en un coup d'oeil un problème d'infrastructure d'un problème de configuration.

**Dépendances autorisées :** Story 2.1
**Réduction de dette support :** permet la qualification initiale des tickets sans navigation technique.

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

##### Story 2.3 — Gating des actions Home Assistant selon la santé du pont

**User story**
En tant qu'utilisateur de la console,
je veux que les actions Home Assistant soient bloquées proprement quand le pont n'est pas opérationnel,
afin d'éviter des actions promises mais inexécutables.

**Dépendances autorisées :** Story 2.1, Story 2.2
**Réduction de dette support :** évite les tickets "j'ai cliqué mais rien ne s'est passé" sans explication visible.

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

##### Story 2.4 — Distinction stable entre infrastructure et configuration

**User story**
En tant qu'utilisateur Jeedom,
je veux voir clairement si un problème relève de l'infrastructure ou de ma configuration,
afin de corriger la bonne cause sans interprétation hasardeuse.

**Dépendances autorisées :** Story 2.1, Story 2.2, Story 2.3
**Réduction de dette support :** réduit les escalades inutiles où un incident bridge est traité comme un problème de mapping.

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

#### Epic 3 — Moteur de statuts, reason_code stables et explicabilité (livré)

> Note : les stories ci-dessous sont livrées. Le vocabulaire est réaligné pour cohérence documentaire avec le recadrage UX validé. Le scope implémenté n'est pas modifié ; Epic 3 a établi l'infrastructure `reason_code` sur laquelle l'Epic 4 construit la couche `cause_code` / `cause_label`.

##### Story 3.1 — Modèle de statuts et reason_code stables par équipement

**User story**
En tant qu'utilisateur de la console,
je veux un modèle de statuts backend stable et cohérent,
afin que le diagnostic de chaque équipement repose sur des `reason_code` fiables et prédictibles.

**Dépendances autorisées :** Story 1.1, Story 2.1
**Réduction de dette support :** supprime les badges ambigus et fournit une base stable pour l'exposition UI.

**Acceptance Criteria**

**Given** un équipement évalué par le backend
**When** son statut et sa raison sont calculés
**Then** il reçoit un `reason_code` stable qui identifie sans ambiguïté la situation

**Given** un cas historiquement affiché en `Partiel`
**When** il est évalué par le moteur de statuts
**Then** le `reason_code` distingue la cause réelle (mapping partiel, couverture incomplète…)

**Given** un même équipement relu par l'UI et par un export support
**When** le `reason_code` est comparé
**Then** il est identique dans les deux contextes

##### Story 3.2 — reason_code stables, raison lisible et action recommandée

**User story**
En tant qu'utilisateur Jeedom,
je veux un `reason_code` stable côté backend, une raison lisible et une action simple quand elle existe,
afin de corriger un non-publié sans expertise MQTT.

**Dépendances autorisées :** Story 3.1
**Réduction de dette support :** fournit une réponse standard à "pourquoi cet équipement n'est pas publié ?".

**Acceptance Criteria**

**Given** un équipement non publié ou en écart
**When** le backend produit son diagnostic
**Then** il retourne un `reason_code` stable, une raison lisible et une action recommandée optionnelle

**Given** une limite relevant de Home Assistant
**When** la raison est affichée
**Then** le message dit explicitement qu'il s'agit d'une limitation Home Assistant

**Given** deux exécutions du même diagnostic sur le même cas
**When** les résultats sont comparés
**Then** le `reason_code` est identique

##### Story 3.3 — Agrégations pièce et global cohérentes

**User story**
En tant qu'utilisateur de la console,
je veux des compteurs pièce/global cohérents avec les statuts individuels,
afin de pouvoir passer du parc à l'équipement sans contradiction.

**Dépendances autorisées :** Story 3.1, Story 3.2
**Réduction de dette support :** évite les écarts entre lecture macro et micro qui alimentent les tickets de confiance.

**Acceptance Criteria**

**Given** une pièce contenant plusieurs équipements de statuts différents
**When** le backend calcule son résumé
**Then** les compteurs reflètent strictement les statuts individuels sous-jacents

**Given** un équipement basculant d'un état à un autre
**When** la pièce et le global sont recalculés
**Then** les compteurs sont mis à jour de manière cohérente

**Given** des compteurs au niveau pièce ou global
**When** l'utilisateur ouvre la pièce concernée
**Then** il peut retrouver les causes réelles sur les équipements concernés

##### Story 3.4 — Intégration UI en lecture seule du contrat métier backend

**User story**
En tant qu'utilisateur Jeedom,
je veux que l'interface affiche fidèlement le contrat métier calculé par le backend,
afin de ne pas subir une seconde interprétation locale des statuts.

**Dépendances autorisées :** Story 3.1, Story 3.2, Story 3.3
**Réduction de dette support :** supprime la divergence backend/UI dans la lecture des statuts et raisons.

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

#### Epic 4 — Recadrage UX : modèle utilisateur Périmètre / Statut / Écart / Cause (backlog)

##### Story 4.1 — Contrat backend du modèle Périmètre / Statut / Écart / Cause

**User story**
En tant qu'utilisateur de la console V1.1,
je veux que le backend expose un contrat UI canonique à 4 dimensions (périmètre, statut, écart, cause),
afin que chaque équipement soit lisible selon un modèle mental naturel, sans concepts techniques internes.

**Dépendances autorisées :** Story 1.1, Story 3.1, Story 3.2
**Réduction de dette support :** remplace la taxonomie à 6 statuts internes par un modèle métier compréhensible, réduisant les interprétations divergentes entre support et utilisateur.

**Acceptance Criteria**

**Given** un équipement évalué par le pipeline backend
**When** le contrat API est construit
**Then** il contient les champs `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`
**And** `statut` est strictement binaire (`publie` / `non_publie`)
**And** `ecart` est un booléen pré-calculé par le backend

**Given** un équipement inclus mais non publié (ex : mapping ambigu)
**When** le contrat API est construit
**Then** `perimetre` = `inclus`, `statut` = `non_publie`, `ecart` = `true`
**And** `cause_code` = `ambiguous_skipped`, `cause_label` = `Mapping ambigu — plusieurs types possibles`

**Given** un équipement exclu mais encore publié dans HA
**When** le contrat API est construit
**Then** `ecart` = `true`
**And** `cause_code` = `pending_unpublish`, `cause_label` = `Changement en attente d'application`

**Given** les `reason_code` stables d'Epic 3
**When** la couche de traduction est exécutée
**Then** chaque `reason_code` est traduit en `cause_code` / `cause_label` par une fonction pure (table de correspondance)
**And** les `reason_code` ne sont jamais exposés dans la réponse API UI
**And** la table de traduction est testable en isolation

**Given** les compteurs d'une pièce
**When** le backend les calcule
**Then** il fournit `total`, `inclus`, `exclus`, `ecarts` pré-calculés
**And** l'invariant `total = inclus + exclus` est respecté

##### Story 4.2 — Vocabulaire d'exclusion par source — disparition du concept exception

**User story**
En tant qu'utilisateur Jeedom,
je veux que les exclusions soient exprimées par leur source (pièce, plugin, équipement),
afin de comprendre immédiatement qui a exclu cet équipement, sans vocabulaire d'héritage ni d'exception.

**Dépendances autorisées :** Story 1.1, Story 1.3, Story 4.1
**Réduction de dette support :** supprime le vocabulaire confus (exception, héritage) source de tickets d'incompréhension.

**Acceptance Criteria**

**Given** un équipement exclu via la règle de sa pièce
**When** le contrat API est construit
**Then** `perimetre` = `exclu_par_piece`
**And** les termes `Hérite de la pièce`, `Exception locale`, `inherit` n'apparaissent jamais dans la réponse API ni dans l'UI

**Given** un équipement explicitement exclu par l'utilisateur
**When** le contrat API est construit
**Then** `perimetre` = `exclu_sur_equipement`

**Given** un équipement exclu par un filtre plugin
**When** le contrat API est construit
**Then** `perimetre` = `exclu_par_plugin`

**Given** l'interface utilisateur complète (console + diagnostic)
**When** l'ensemble des termes visibles est audité
**Then** aucun des termes interdits (§6.2 UX delta review) n'est présent

**Given** les compteurs par pièce ou globaux
**When** ils sont affichés
**Then** le compteur `Exceptions` n'existe pas
**And** les compteurs sont strictement `Total`, `Inclus`, `Exclus`, `Écarts`

##### Story 4.3 — Diagnostic centré in-scope, confiance en diagnostic uniquement, traitement de "Partiellement publié"

**User story**
En tant qu'utilisateur de la console V1.1,
je veux que le diagnostic principal ne porte que sur mes équipements inclus, que la confiance ne soit visible qu'en diagnostic technique, et que "Partiellement publié" ne soit plus un statut principal mais un indicateur de diagnostic détaillé,
afin de me concentrer sur ce qui compte et de ne pas être noyé par des informations techniques superflues.

**Dépendances autorisées :** Story 3.1, Story 3.2, Story 4.1
**Réduction de dette support :** réduit la surcharge d'information, les questions sur des équipements hors scope, et les confusions sur le statut "Partiellement publié".

**Acceptance Criteria**

**Given** le diagnostic principal utilisateur
**When** il est construit par le backend
**Then** il ne contient que les équipements dont `perimetre` = `inclus`
**And** les équipements exclus restent visibles dans la synthèse de périmètre avec leur source d'exclusion

**Given** un équipement in-scope affiché dans la console principale
**When** ses informations sont rendues
**Then** la confiance (`Sûr` / `Probable` / `Ambigu`) n'est pas visible

**Given** un équipement in-scope affiché dans le diagnostic technique détaillé
**When** ses informations sont rendues
**Then** la confiance est visible et exploitable

**Given** un équipement historiquement affiché en `Partiellement publié`
**When** il est réévalué par le nouveau modèle
**Then** son statut principal est `Publié`
**And** `Partiellement publié` est conservé comme indicateur de diagnostic détaillé de couverture commandes
**And** il n'est jamais utilisé comme statut principal de la console

**Given** l'export support complet
**When** il est généré
**Then** il contient tous les équipements (in-scope et exclus)
**And** il inclut la confiance, les `reason_code` techniques, les commandes et le typage

##### Story 4.4 — Intégration UI du nouveau modèle (console + diagnostic)

**User story**
En tant qu'utilisateur de la console V1.1,
je veux que l'interface affiche fidèlement le modèle 4 dimensions et les compteurs fournis par le backend,
afin que la lecture soit cohérente entre la console, le diagnostic et l'export support.

**Dépendances autorisées :** Story 4.1, Story 4.2, Story 4.3
**Réduction de dette support :** supprime toute interprétation locale des statuts par le frontend et garantit la cohérence de lecture entre toutes les surfaces.

**Acceptance Criteria**

**Given** la console V1.1 au niveau équipement
**When** un équipement in-scope est affiché
**Then** il présente les 4 dimensions : périmètre, statut binaire, indicateur d'écart, cause métier (si écart)

**Given** les compteurs au niveau pièce ou global
**When** la console les affiche
**Then** ils sont exactement `Total`, `Inclus`, `Exclus`, `Écarts`
**And** ils sont issus du payload backend pré-calculé, sans calcul local frontend

**Given** le contrat JSON complet d'un équipement
**When** le frontend le reçoit et l'affiche
**Then** il ne dérive aucun statut, ne recompose aucune cause, ne calcule aucun compteur
**And** il affiche les `cause_label` tels quels, sans reformulation locale

**Given** un changement de vocabulaire dans le contrat backend
**When** le payload est mis à jour
**Then** l'UI reflète ce changement sans logique de traduction locale

**Given** la console et le diagnostic affichant le même équipement
**When** les informations sont comparées
**Then** la taxonomie de base (périmètre, statut, écart, cause) est identique
**And** le diagnostic ajoute uniquement les détails supplémentaires (confiance, commandes, typage)

#### Epic 5 — Opérations HA explicites, graduées et sûres (backlog)

> Note : cet epic est renuméroté depuis l'ancien Epic 4. L'intention produit (opérations HA explicites, sûres et graduées) est conservée intégralement. Les ajustements sont principalement terminologiques : les opérations utilisent le vocabulaire et le modèle 4 dimensions stabilisés par l'Epic 4.

##### Story 5.1 — Façade backend unique des opérations V1.1

**User story**
En tant qu'utilisateur Jeedom,
je veux que toutes les actions Home Assistant passent par une façade backend unique,
afin que la portée et l'intention soient gérées de manière cohérente.

**Dépendances autorisées :** Story 1.1, Story 2.1, Story 3.2, Story 4.1
**Réduction de dette support :** évite les comportements divergents entre opérations globales, pièce et équipement.

**Acceptance Criteria**

**Given** une action Home Assistant demandée
**When** le backend reçoit la requête
**Then** il la traite via une façade unique paramétrée par `intention`, `portée` et `sélection`

**Given** une même intention exécutée à des portées différentes
**When** la façade est appelée
**Then** le contrat de réponse reste homogène
**And** la réponse utilise le modèle 4 dimensions (périmètre, statut, écart, cause)

**Given** une tentative d'orchestration locale côté UI
**When** elle contournerait la façade
**Then** elle est interdite par conception

##### Story 5.2 — Flux Republier non destructif multi-portée

**User story**
En tant qu'utilisateur Jeedom,
je veux pouvoir republier globalement ou localement sans lancer une reconstruction destructive,
afin d'appliquer proprement mon périmètre sans crainte excessive.

**Dépendances autorisées :** Story 5.1, Story 1.4, Story 2.3
**Réduction de dette support :** clarifie le flux nominal et réduit les tickets liés à la peur de casser Home Assistant.

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

**Given** des changements de périmètre en attente (écart de direction 2)
**When** `Republier` se termine avec succès
**Then** l'écart correspondant disparaît
**And** la console n'affiche pas ce succès comme une reconstruction destructive

##### Story 5.3 — Flux Supprimer puis recréer avec confirmations fortes

**User story**
En tant qu'utilisateur Jeedom avancé,
je veux lancer explicitement une reconstruction destructive avec une confirmation forte,
afin de savoir exactement quand j'accepte un impact potentiel côté Home Assistant.

**Dépendances autorisées :** Story 5.1, Story 2.3, Story 3.2
**Réduction de dette support :** évite les scénarios où une opération destructive est confondue avec un simple refresh.

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

##### Story 5.4 — Retour d'opération lisible et mémorisation du dernier résultat

**User story**
En tant qu'utilisateur de la console,
je veux un retour d'opération court, lisible et mémorisé,
afin de savoir ce qui a été lancé, sur quel périmètre, avec quel résultat.

**Dépendances autorisées :** Story 2.1, Story 5.1, Story 5.2, Story 5.3
**Réduction de dette support :** permet de reconstituer un scénario d'opération sans croiser plusieurs journaux.

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

### 9.4 Matrice des dépendances story-level

| Story | Dépendances autorisées | Dépendance en avant |
|---|---|---|
| 1.1 | Aucune | Non |
| 1.2 | 1.1 | Non |
| 1.3 | 1.1, 1.2 | Non |
| 1.4 | 1.1, 1.2, 1.3 | Non |
| 1.7 | Epic 1 | Non |
| 2.1 | Aucune | Non |
| 2.2 | 2.1 | Non |
| 2.3 | 2.1, 2.2 | Non |
| 2.4 | 2.1, 2.2, 2.3 | Non |
| 3.1 | 1.1, 2.1 | Non |
| 3.2 | 3.1 | Non |
| 3.3 | 3.1, 3.2 | Non |
| 3.4 | 3.1, 3.2, 3.3 | Non |
| 4.1 | 1.1, 3.1, 3.2 | Non |
| 4.2 | 1.1, 1.3, 4.1 | Non |
| 4.3 | 3.1, 3.2, 4.1 | Non |
| 4.4 | 4.1, 4.2, 4.3 | Non |
| 5.1 | 1.1, 2.1, 3.2, 4.1 | Non |
| 5.2 | 5.1, 1.4, 2.3 | Non |
| 5.3 | 5.1, 2.3, 3.2 | Non |
| 5.4 | 2.1, 5.1, 5.2, 5.3 | Non |

Aucune dépendance en avant. L'Epic 5 dépend de l'Epic 4 via la Story 4.1 (contrat 4 dimensions), ce qui reflète la décision du Sprint Change Proposal : le recadrage doit être terminé avant les opérations.

### 9.5 Gate de sortie

Le gate de sortie est couvert par ce document, sous réserve d'une validation finale produit/technique :

1. Les 5 epics sont décomposés en stories implémentables.
2. 100% des stories ont des AC `Given / When / Then`.
3. Le caractère obligatoire du **résultat de dernière opération** est repris dans Epic 2 et Epic 5.
4. Une matrice des dépendances story-level existe et ne contient aucune dépendance en avant.
5. Chaque story mentionne explicitement son apport en réduction de dette support ou en prédictibilité produit.
6. Le modèle **Périmètre / Statut / Écart / Cause** est couvert explicitement par l'Epic 4 (stories 4.1-4.4).
7. La distinction `reason_code` / `cause_code` est portée par les stories 4.1 et 4.3.
8. La disparition du concept exception est portée par la story 4.2.
9. Le traitement de `Partiellement publié` est porté par la story 4.3.

## 10. Recommandation finale

**Recommandation : le plan d'epics est réaligné avec le recadrage UX validé et prêt pour validation story-level, puis génération des fichiers story individuels.**

Le plan d'epics est robuste, cohérent et borné. Les 5 epics couvrent la totalité du scope V1.1 Pilotable :
- Epics 1-3 livrés, fondations solides ;
- Epic 4 aligne la couche de présentation sur le modèle mental utilisateur ;
- Epic 5 porte les opérations HA sur un vocabulaire stabilisé.

**Points à figer avant `create-story`**

Ces points sont des **invariants non renégociables** dans les stories :

1. Le modèle canonique du périmètre publié reste `global → pièce → équipement` avec `inherit / include / exclude` et précédence `équipement > pièce > global`.
2. Le backend reste la source unique de `statut + cause + action recommandée + santé minimale + compteurs`.
3. Le contrat UI canonique est à 4 dimensions : périmètre, statut (binaire), écart (booléen), cause (métier).
4. Les `reason_code` (Epic 3) restent stables. La couche `cause_code` / `cause_label` est dérivée par une table de traduction (fonction pure).
5. Toute opération V1.1 passe par une façade backend unique paramétrée par `intention` et `portée`.
6. `Republier` reste non destructif par intention ; `Supprimer/Recréer` reste le seul flux destructif explicite.
7. Le résultat de dernière opération fait partie du contrat minimal visible V1.1.
8. Le concept d'exception a disparu de l'interface utilisateur.
9. La confiance n'est visible qu'en diagnostic technique.
10. `Partiellement publié` n'est pas un statut principal de console.
11. Les frontières hors scope restent gelées :
    - pas d'extension fonctionnelle ;
    - pas de preview complète ;
    - pas de remédiation guidée avancée ;
    - pas de santé avancée ;
    - pas de support outillé avancé ;
    - pas d'alignement Homebridge.

Si ces invariants sont repris tels quels, ce document peut servir de source unique pour créer les fichiers story individuels sans reprise de cadrage epic-level.

**Prochaine étape recommandée :** `sprint-planning` pour intégrer l'Epic 4 et l'Epic 5 dans le sprint actif, puis `create-story` pour les stories 4.1 à 4.4.
