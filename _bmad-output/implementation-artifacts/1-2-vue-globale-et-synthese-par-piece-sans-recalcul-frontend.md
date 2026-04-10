# Story 1.2: Vue globale et synthèse par pièce sans recalcul frontend

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur de la console,  
je veux voir un résumé global et des synthèses par pièce fiables,  
afin de comprendre rapidement le périmètre voulu sans ambiguïté de calcul.

## Story Context

- Cycle actif obligatoire: **Post-MVP Phase 1 - V1.1 Pilotable**
- Dépendances autorisées: Story 1.1 uniquement
- Story productrice backend de référence: `1-1-resolver-canonique-du-perimetre-publie`
- Statut de dépendance: blocage terrain levé le 2026-03-22 après reprise backend Story 1.1 et revalidation terrain finale PASS
- Réduction de dette support: évite les écarts de lecture entre compteurs UI et état backend réel
- Rappel de workflow: aucun agent ne doit deviner la source de vérité; la stratégie de test V1.1 fait partie des sources actives

## Acceptance Criteria

1. **AC1 - Résumé global et synthèse par pièce issus uniquement du backend**  
   **Given** un périmètre calculé par le resolver backend  
   **When** l'UI charge la console V1.1  
   **Then** elle affiche un résumé global et une synthèse par pièce issus uniquement du payload backend

2. **AC2 - Cohérence stricte des compteurs de synthèse**  
   **Given** une pièce contenant inclusions, exclusions et exceptions  
   **When** la synthèse est affichée  
   **Then** les compteurs reflètent exactement les décisions effectives retournées par le backend

3. **AC3 - Aucun recalcul métier lors du rafraîchissement UI**  
   **Given** une modification locale de périmètre  
   **When** l'UI rafraîchit les synthèses  
   **Then** elle ne recalcule aucune logique métier côté frontend  
   **And** elle réaffiche uniquement les données recalculées par le backend

## Tasks / Subtasks

- [x] Task 1 - Brancher un flux de lecture UI strictement aligné sur le contrat backend existant (AC: 1, 3)
  - [x] 1.1 Réutiliser le contrat `published_scope` déjà livré par Story 1.1 comme unique source de données pour la vue globale et les synthèses par pièce
  - [x] 1.2 Ajouter uniquement le chaînage technique minimal nécessaire pour exposer ce contrat à l'UI Jeedom si l'entrée existante ne suffit pas encore, sans créer de second contrat ni déplacer de logique métier hors backend
  - [x] 1.3 En cas d'absence de contrat disponible avant premier sync, afficher un état vide explicite ou un message de prérequis, sans fabriquer de compteurs ni fallback produit implicite

- [x] Task 2 - Afficher le résumé global à partir de `global.counts` backend (AC: 1, 3)
  - [x] 2.1 Ajouter dans la console un bloc de synthèse globale distinct de la vue par pièce
  - [x] 2.2 Alimenter ce bloc exclusivement depuis `published_scope.global.counts`
  - [x] 2.3 Garder toute transformation frontend purement présentationnelle: aucun recomptage, aucune déduction d'état effectif, aucun croisement avec d'autres payloads

- [x] Task 3 - Afficher les synthèses par pièce à partir de `pieces[]` backend (AC: 1, 2, 3)
  - [x] 3.1 Construire la liste ou grille des pièces depuis `published_scope.pieces[]`, avec lecture des champs `object_id`, `object_name` et `counts`
  - [x] 3.2 Afficher les agrégats exactement tels que fournis par le backend pour une pièce contenant inclusions, exclusions et exceptions
  - [x] 3.3 Ne pas introduire ici le détail équipement, la source de décision lisible ou la visibilité continue des exclus: ces sujets appartiennent à Story 1.3

- [x] Task 4 - Rafraîchir la synthèse sans delta local ni confusion avec Home Assistant (AC: 1, 3)
  - [x] 4.1 Lors d'un rechargement ou d'un refresh après modification locale, remplacer la synthèse affichée par les données du backend recalculé, sans incrémentation/décrémentation optimiste côté JS
  - [x] 4.2 Ne pas interpréter la synthèse comme un effet déjà appliqué dans Home Assistant; la séparation entre décision locale et application effective doit rester visible conceptuellement
  - [x] 4.3 Ne pas empiéter sur Story 1.4: aucun nouveau parcours "changements à appliquer à Home Assistant" ne doit être introduit dans cette story

- [x] Task 5 - Protéger le contrat V1.1 et la non-régression des synthèses (AC: 1, 2, 3)
  - [x] 5.1 Ajouter ou étendre les tests backend / contrat nécessaires pour verrouiller que les champs `global.counts` et `pieces[].counts` consommés par l'UI restent stables
  - [x] 5.2 Si un relais PHP/AJAX est ajouté, le tester comme un simple passage du contrat backend sans recalcul, sans regroupement et sans fallback de compteurs
  - [x] 5.3 Ajouter une vérification ciblée du rendu de synthèse sur un cas mixte `include / exclude / exception`, plus un scénario de rafraîchissement prouvant que l'UI remplace les données depuis le backend au lieu de recalculer localement

## Dev Notes

### Contexte actif et contraintes de cadrage

- Le cycle actif de référence est **Post-MVP Phase 1 - V1.1 Pilotable**
- Les sources actives de vérité pour cette story sont:
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Contexte secondaire autorisé et utilisé:
  - `_bmad-output/implementation-artifacts/1-1-resolver-canonique-du-perimetre-publie.md`
- Aucun agent ne doit deviner la source de vérité
- La stratégie de test V1.1 est une source active, pas un contexte secondaire
- Ne pas rouvrir le cadrage produit, ne pas modifier les epics, ne pas réinterpréter les invariants déjà figés dans le breakdown validé

### Invariants non renégociables à reprendre tels quels

- Le modèle canonique du périmètre publié reste `global -> pièce -> équipement`
- Les états supportés restent `inherit / include / exclude`
- La résolution suit explicitement `équipement > pièce > global`
- Le backend reste l'unique source de calcul de la décision effective et des agrégats affichés
- La décision locale de périmètre et l'application effective à Home Assistant restent deux concepts distincts
- Aucun calcul de décision effective, d'agrégat ou de compteur ne doit être introduit dans `desktop/js/jeedom2ha.js`
- Les frontières hors scope V1.1 restent gelées: pas d'extension fonctionnelle, pas de preview complète, pas de remédiation guidée avancée, pas de santé avancée, pas d'alignement Homebridge

### Dev Agent Guardrails

- Cette story est strictement bornée à la lecture UI du contrat backend déjà produit par Story 1.1
- Cette story ne crée pas un nouveau moteur métier: elle consomme le contrat backend existant
- Le frontend lit les champs backend déjà préparés pour la suite; il ne reconstruit ni la décision effective ni les agrégats
- La vue globale et la synthèse par pièce s'appuient sur `global.counts` et `pieces[].counts` déjà fournis par le backend
- Ne pas confondre affichage console du périmètre publié avec opérations effectives Home Assistant
- Ne pas empiéter sur Story 1.3:
  - pas de détail équipement orienté explicabilité utilisateur
  - pas de libellés UI de source de décision du type `Hérite de la pièce` ou `Exception locale`
  - pas de promesse de visibilité continue complète des exclus au niveau détail
- Ne pas empiéter sur Story 1.4:
  - pas de nouveau statut utilisateur "changements à appliquer à Home Assistant"
  - pas de lecture métier nouvelle autour de `has_pending_home_assistant_changes`
  - pas d'ambiguïté entre périmètre voulu et effet appliqué côté HA
- Ne pas dériver vers une vue par pièce comme unique source de vérité: le niveau global doit rester visible comme synthèse distincte

### Contrat backend à consommer pour Story 1.2

Story 1.1 a déjà préparé un mini contrat backend consommable par les stories suivantes. Pour Story 1.2, le besoin est volontairement borné à la lecture de la synthèse globale et des synthèses par pièce, sans recalcul frontend.

- Niveau `global`
  - `counts`: agrégats déterministes issus du resolver backend pour la synthèse globale
  - `has_pending_home_assistant_changes`: présent dans le contrat, mais sa sémantique utilisateur ne doit pas être développée dans cette story
- Niveau `piece`
  - `object_id`: identifiant stable de la pièce / objet Jeedom
  - `object_name`: libellé de la pièce / objet Jeedom
  - `counts`: agrégats déterministes de la pièce issus du resolver backend
  - `has_pending_home_assistant_changes`: présent dans le contrat, mais hors portée de Story 1.2 côté UX
- Niveau `equipement`
  - existe déjà dans le contrat Story 1.1 pour les stories suivantes, mais ne doit pas devenir le centre de la Story 1.2

Notes de contrat:

- Story 1.2 lit la synthèse `counts` globale et par pièce, pas un schéma UI réinventé
- Si un relais PHP/AJAX est nécessaire pour la console, il doit transmettre ce contrat en lecture seule
- Le contrat hérité de Story 1.1 fige déjà la présence de `global.counts` et `pieces[].counts`; si des clés détaillées y sont déjà définies, Story 1.2 les consomme telles quelles, sans les redéfinir ni en dériver d'autres côté frontend

### Previous Story Intelligence

- Story 1.1 a livré le resolver canonique backend et le contrat `published_scope`
- Story 1.1 a rendu ce contrat persistant et relisible par les stories suivantes après synchronisation backend
- Story 1.1 a explicitement verrouillé que les stories 1.2, 1.3 et 1.4 doivent consommer ce contrat au lieu d'en recréer un
- La relecture Story 1.1 a déjà fermé un risque de drift legacy; Story 1.2 ne doit surtout pas court-circuiter `published_scope` pour relire directement des exclusions historiques ou des structures parallèles
- `desktop/js/jeedom2ha.js` n'a pas reçu de logique métier V1.1 en Story 1.1; Story 1.2 ne doit pas y introduire un moteur de synthèse

### Implementation hints (non-authoritative)

- Les points ci-dessous sont des indices techniques issus de l'état actuel du plugin. Ils n'ont pas autorité et ne remplacent pas les sources documentaires actives du cycle V1.1 Pilotable.
- La chaîne backend livrée par Story 1.1 expose déjà un contrat canonique de périmètre publié réutilisable par l'UI; Story 1.2 doit se brancher sur cette chaîne au lieu d'en créer une autre.
- Le plugin dispose déjà d'une chaîne console côté template, relais backend/UI et script frontend; si Story 1.2 s'y raccorde, ce raccordement doit rester un transport et un rendu du contrat backend, pas une recomposition métier.
- Des tests de contrat et de non-régression existent déjà autour de Story 1.1; ils constituent la base naturelle à étendre pour couvrir la synthèse globale et par pièce.
- Si des points d'ancrage code sont utiles au développement, ils doivent être traités comme de simples aides de navigation dans l'état courant du dépôt, jamais comme source de vérité produit ou architecture.

### Dependencies and Sequencing

- Dépendances autorisées: Story 1.1 uniquement
- Dépendances en avant: interdites
- Cette story prépare explicitement:
  - Story 1.3, qui exploitera le niveau équipement et la source de décision lisible
  - Story 1.4, qui exploitera la distinction locale vs appliquée à HA
- Cette story doit rester autonome sans attendre Epic 2, 3 ou 4

### Risks / Points de vigilance

- Recalculer des compteurs côté JS à partir des équipements ou des pièces
- Introduire un second contrat UI différent de `published_scope`
- Dériver une lecture produit depuis des exclusions techniques historiques au lieu du resolver canonique
- Laisser croire qu'une synthèse de périmètre vaut confirmation d'application côté Home Assistant
- Faire glisser la story vers le détail équipement explicatif de Story 1.3
- Commencer à exposer les changements en attente de Story 1.4 sous couvert de "résumé"
- Produire un état vide silencieux ou trompeur au lieu d'un message clair quand aucun sync n'a encore fourni le contrat

### Testing Requirements

- Invariants V1.1 explicitement touchés par cette story:
  - modèle canonique `global -> pièce -> équipement`
  - backend source unique des agrégats affichés
  - séparation scope local vs application effective HA
  - absence de recalcul métier frontend
- Contrats MVP explicitement à préserver comme socle de non-régression pour cette story:
  - la chaîne de mapping / extraction de topologie qui alimente le modèle canonique `global -> pièce -> équipement`
  - les comportements MVP déjà couverts autour du diagnostic, des exclusions, du rescan et de la stabilité des identifiants
  - les contrats existants de publication MQTT Discovery et de cycle de vie, qui ne doivent pas régresser du seul fait de l’exposition UI des synthèses
  - la règle produit conservée: mieux vaut ne pas publier que publier faux
- Tests unitaires obligatoires:
  - uniquement si un helper de rendu ou de normalisation purement présentationnel est ajouté côté JS/PHP
  - dans ce cas, il doit prouver qu'aucun compteur n'est recomposé à partir d'un détail équipement
- Tests d'intégration backend / relais obligatoires:
  - maintenir ou étendre la couverture du contrat `published_scope` utilisé par la console
  - si un relais PHP/AJAX est ajouté, prouver qu'il restitue `global.counts` et `pieces[].counts` sans transformation métier
  - couvrir le comportement "contrat indisponible avant sync" sans fallback de synthèse inventé
- Tests de contrat / non-régression obligatoires:
  - stabilité des champs `global.counts`, `pieces[].object_id`, `pieces[].object_name`, `pieces[].counts`
  - non-régression des tests Story 1.1 sur `published_scope`
  - preuve qu'aucun calcul de compteur n'est déplacé du backend vers le frontend
- Tests UI cibles:
  - requis, car la story modifie un contrat visible critique
  - vérifier un cas mixte avec inclusions, exclusions et exceptions
  - vérifier qu'un refresh après changement local remplace les synthèses par les nouvelles données backend, sans delta local optimiste
  - vérifier que l'UI n'affiche pas ces synthèses comme une opération HA déjà effectuée

## Validation Note

- Validation terrain finale du 2026-03-22: PASS.
- Etat nominal backend + UI coherent.
- Le scenario critique anciennement FAIL est desormais PASS: changement de perimetre reversible, `/system/published_scope` reflete le changement, et le refresh UI remplace completement le rendu depuis le backend sans recalcul local.
- Le rollback backend + UI est valide.
- Aucune derive observee vers Story 1.3 ni Story 1.4.
- Limitation de protocole a conserver: le scenario `contrat backend indisponible avant premier sync` n'est pas rejouable proprement avec le runbook canonique actuel a cause du bootstrap startup; ce point est documente comme limitation de protocole et non comme echec story.
- Story 1.2 peut etre cloturee en `done`.

### References

- Sources actives de vérité:
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Contexte secondaire autorisé:
  - `_bmad-output/implementation-artifacts/1-1-resolver-canonique-du-perimetre-publie.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story context generated from active V1.1 artifacts plus authorized Story 1.1 context
- `node --test tests/unit/test_scope_summary_presenter.node.test.js` (échec rouge initial: module de présentation absent)
- `node --test tests/unit/test_scope_summary_presenter.node.test.js` (vert: 2 tests passés)
- `python3 -m pytest tests/unit/test_published_scope_http.py -q` (5 passed)
- `python3 -m pytest tests/unit/test_published_scope.py tests/unit/test_published_scope_http.py -q` (39 passed)
- `command -v php` (binaire PHP absent dans cet environnement)

### Completion Notes List

- Revalidation terrain finale PASS du 2026-03-22 apres reprise backend Story 1.1; AC3 est valide sur le scenario de changement de perimetre reversible avec remplacement complet du rendu UI depuis le backend.
- Rollback backend + UI valide sans derive vers Story 1.3 / Story 1.4.
- Limitation de protocole documentee en non-bloquant: le cas `contrat backend indisponible avant premier sync` n'est pas rejouable proprement avec le runbook canonique actuel a cause du bootstrap startup.
- Story implémentée en lecture stricte du contrat backend `published_scope` via un relai PHP/AJAX minimal, sans second contrat ni moteur métier parallèle.
- Ajout d'un bloc console dédié à la synthèse globale (`global.counts`) et à la synthèse par pièce (`pieces[].counts`) avec remplacement complet du rendu à chaque refresh backend.
- En cas d'absence de contrat avant sync, l'UI affiche un état explicite de prérequis sans fabriquer de compteurs de fallback.
- Message conceptuel explicite conservant la séparation entre périmètre local calculé et application effective Home Assistant (sans introduire le parcours Story 1.4).
- Couverture de tests étendue: contrat backend stable pour l'UI, scénario de remplacement après second sync, tests Node ciblés de rendu mixte et refresh sans delta local.

### File List

- `_bmad-output/implementation-artifacts/1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `core/ajax/jeedom2ha.ajax.php`
- `core/class/jeedom2ha.class.php`
- `desktop/js/jeedom2ha.js`
- `desktop/js/jeedom2ha_scope_summary.js`
- `desktop/php/jeedom2ha.php`
- `tests/test_php_published_scope_relay.php`
- `tests/unit/test_published_scope_http.py`
- `tests/unit/test_scope_summary_presenter.node.test.js`

### Change Log

- 2026-03-22: Revalidation terrain finale PASS apres reprise backend Story 1.1; blocage AC3 leve, Story 1.2 cloturable en `done`, limitation de protocole pre-sync conservee comme note non bloquante.
- 2026-03-22: Implémentation Story 1.2 — relai PHP/AJAX `published_scope`, bloc UI synthèse globale + par pièce sans recalcul frontend, état explicite pré-sync, tests backend/contrat et tests UI ciblés (Node).
