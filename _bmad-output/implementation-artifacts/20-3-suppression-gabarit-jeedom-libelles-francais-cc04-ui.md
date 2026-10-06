# Story 20.3 : Suppression du gabarit Jeedom et libellés français d'usage (CC-04 volet UI)

Status: backlog

> **Statut : `create-story` terminé, `ready-for-dev` NON accordé (2026-10-06).** Les arbitrages produit sont actés par Alexandre : **Q1=A, Q2=A, Q2b=A, Q3=A, Q4=A**. Le seul blocage restant est **20.2 non `done`** (`review` : preuve post-fusion et validation UX restantes). Aucun développement avant 20.2 `done`.

## Story

En tant qu'utilisateur du plugin (persona « Sébastien », modèle Homebridge),
je veux une page principale sans synthèse « Parc global », sans modale de diagnostic séparée et sans vocabulaire de gabarit Jeedom, où la surface pièce → équipement → commande dit elle-même ce qui est publié, exclu ou à corriger,
afin de comprendre l'état de mon installation avec des mots d'usage, au même endroit que celui où je la règle.

**Parcours : complet.** Story d'interface : gate 20-0, déploiement standard, preuve terrain, puis `ready-for-UX-validation` avant `done`.

## Contexte et périmètre

- Décision d'Alex du 2026-10-01 (SCP, décision 1) : la synthèse « Parc global » et la modale diagnostic sont **supprimées** au profit de la surface unique. Décision d'Alex du 2026-10-05 (Q3 de 20.1) : les compteurs ne sont pas ajoutés en 20.1 ; **20.3 décide puis livre** leur remplacement.
- 20.1 (`done`) a rendu la surface unique complète ; 20.2 (`review`) y ajoute exclusion, forçage, retour au mode automatique, badge « pas encore appliqué » et « Appliquer ». 20.4 (`done`) a posé le rescan sur la page principale.
- **Dans le périmètre :**
  - retrait de la synthèse « Parc global » (`#div_scopeSummary`) et de la modale Diagnostic ;
  - compteurs de remplacement dans la surface unique **[Q1]** ;
  - reprise ou retrait explicite des capacités que portaient ces deux éléments **[Q2, Q3]** ;
  - remplacement du jargon résiduel : « Mes templates », « Paramètre n°1 » et tout libellé du même ordre **[Q4]**.
- **Hors périmètre :** documentation utilisateur (20.5) ; exclusions par plugin ou par pièce (configuration) ; logique de décision (`evaluate_equipment()` ne change pas) ; suppression de routes du démon ; export « Télécharger le diagnostic support » (distinct de la modale, conservé, voir F4).
- **Contrainte structurante : `evaluate_equipment()` est la seule source de l'interface.** Tout compteur, libellé d'état ou cause affiché vient de l'arbre du démon (`GET /system/mapping_overrides/{eq_id}`, déjà alimenté par `evaluate_equipment()`) ; l'interface classe et dénombre, elle ne recalcule aucune décision (gate epic-level pe-epic-20).

## Faits relevés le 2026-10-06 (lecture seule, `main` `df6bb51`)

- **F1 — La synthèse « Parc global » est un tableau hiérarchique global → pièce → équipement.** Bloc `#div_scopeSummary` (`desktop/php/jeedom2ha.php:92-106`), rendu par `desktop/js/jeedom2ha_scope_summary.js` (727 lignes, ligne « Parc global » : `:372`), alimenté par `refreshPublishedScopeSummary` → action `getPublishedScopeForConsole` (`desktop/js/jeedom2ha.js:549-580`, `core/ajax/jeedom2ha.ajax.php:653`, `core/class/jeedom2ha.class.php:578`), qui lit aussi le diagnostic de tout le parc (`/system/diagnostics`, `ajax.php:658`). Ses compteurs (contrat 4D : total, exclus, inclus, publiés, écarts) comptent des **équipements**, pas des commandes, et ne comptent pas les exclusions manuelles comme « exclus » (faits repris de 20.1, Q3).
- **F2 — La synthèse porte des capacités qui ne sont pas des compteurs :**
  - boutons **Republier** et **Supprimer puis recréer** par pièce et par équipement, avec confirmation forte (`jeedom2ha.js:631-715`) ;
  - badge **Écart** cliquable qui ouvre la modale Diagnostic sur l'équipement (`jeedom2ha.js:605-629`) ;
  - badge **streaming** global (story 15.2) et badge **parité FAN → switch** (story 15.3) ;
  - les valeurs `data-scope-count` et `data-scope-publies` lues par les confirmations des boutons globaux « Republier dans Home Assistant » et « Supprimer puis recréer dans Home Assistant » (`jeedom2ha.js:537-546`, `:723-738`) : sans synthèse, ces deux confirmations n'ont plus de nombre à afficher.
- **F3 — La modale Diagnostic est une vue d'ensemble séparée** : action `diagnostic` du bloc « Gestion » (`jeedom2ha.php:67`, `jeedom2ha.js:872-1354`), lit `getDiagnostics`, n'affiche que les équipements inclus, tableau « Pièce / Nom / Écart / Statut / Confiance / Raison » et accordéon en cinq sections (éligibilité, mapping, validation HA, décision, publication : trace du pipeline, cause canonique, **résultat technique d'un échec de publication MQTT**, action recommandée). Helpers : `desktop/js/jeedom2ha_diagnostic_helpers.js`. La surface unique, elle, affiche la cause **par commande** (arbre) ; elle n'affiche pas l'échec technique d'étape 5.
- **F4 — « Télécharger le diagnostic support »** (`jeedom2ha.php:143-154`, `jeedom2ha.js:760`, action `exportDiagnostic`) est un bouton distinct de la modale ; il garde sa route `/system/diagnostics` côté démon (`ajax.php:725`). Il est hors du périmètre de suppression (« modale diagnostic » seulement), sous réserve de confirmation en Q3.
- **F5 — Le jargon de gabarit est dans une page Jeedom standard, pas dans la surface :**
  - titre de section « Mes templates » et message « Aucun équipement Template trouvé, cliquer sur "Ajouter" pour commencer » (`jeedom2ha.php:180-183`) : section qui liste les équipements de type `jeedom2ha` (aucun sur la box d'après 16.8) ;
  - page d'édition d'équipement du gabarit (`jeedom2ha.php:211-359`) : « Nom du paramètre n°1 » / « Renseignez le paramètre n°1… » / placeholder « Paramètre n°1 » (`:283-287`), « Paramètres spécifiques », « Mot de passe », « Auto-actualisation » avec assistant cron, « Description » ;
  - la classe `jeedom2ha` conserve des crochets de gabarit (`preInsert`, `preSave`, `postSave`, chiffrement d'un `password` d'équipement, `core/class/jeedom2ha.class.php:826-870`), et rien ne lit `param1` ni `autorefresh`.
  - Autres mots d'infrastructure visibles à inventorier (Task 1.2) : « Écart », « Confiance », « Parité FAN → switch », « Synthèse du périmètre publié », « mapping », « Ajouter » (crée un équipement `jeedom2ha`).
- **F6 — Le gate 20-0 et les tests dépendent de ces éléments.** `getDiagnostics` et `getPublishedScopeForConsole` figurent dans les lectures autorisées de la politique du gate (`tests/e2e/gate/lib/policy.mjs:51-52`) et de l'inventaire de chargement (`tests/e2e/gate/page-load-request-inventory.mjs:186-187`). 22 fichiers de tests ou du gate référencent la synthèse, la modale ou leurs helpers (recherche reproductible : `grep -rlE "jeedom2ha_diagnostic_helpers|Jeedom2haDiagnosticHelpers|modal-diagnostic|Diagnostic de Couverture|jeedom2ha_scope_summary|Jeedom2haScopeSummary|getPublishedScopeForConsole|data-action=diagnostic|j2ha-ecart|div_scopeSummary|table_diagnostic" tests`) :
  - Node : `test_scope_summary_presenter`, `test_story_3_4_ai5_frontend_passthrough`, `4_2_diagnostic_decision`, `4_2_vocab_exclusion`, `4_3_diagnostic_in_scope`, `4_4_integration_ui_4d`, `4_5_home_landing`, `4_6_diagnostic_modal`, `5_1_actions_ha_frontend`, `5_2_frontend`, `5_3_frontend`, `5_4_bandeau`, `5_7_badge_suppr_harmonie`, `6_1_pipeline_step`, `6_2_frontend_backend_first`, `6_3_honest_cause_mapping`, `15_2_streaming_badge_console`, `15_3_fan_parity_badge_console` ;
  - PHP : `tests/test_php_published_scope_relay.php`, `tests/unit/test_story_5_1_php_relay.php` ;
  - gate : `tests/e2e/gate/lib/policy.mjs`, `tests/e2e/gate/page-load-request-inventory.mjs`.
  Les tests des stories 4.6 et 6.1 à 6.3 importent `jeedom2ha_diagnostic_helpers.js` ou exigent le rendu de la modale : ils échoueront au retrait. Chacun est à retirer (fonction supprimée) ou à réaffecter (fonction conservée), jamais laissé rouge ni supprimé en silence.
- **F7 — Tension à trancher en Q1 :** 20.1 (AC5, inchangé) interdit de charger les arbres de tout le parc ; des compteurs **par carte de pièce** en exigeraient la lecture, ou un nouveau point d'entrée du démon.

## Décisions produit actées par Alexandre — 2026-10-06

Alexandre a validé le paquet **`1A 2A 2bA 3A 4A`**. Les AC **[Qx]** sont donc figés sur ces choix.

- **Q1 — Que deviennent les compteurs de « Parc global » ?**
  - **Décision : A.**
  - **A (recommandé) — compteurs dans la modale de la pièce ouverte, rien sur les cartes.** Entête de la pièce, lus dans l'arbre déjà chargé à l'ouverture : équipements publiés / exclus / désactivés / à corriger, et commandes prêtes / bloquantes / non couvertes. Unité dite dans le libellé (équipement ou commande), exclusions manuelles comptées comme exclues (elles viennent de la décision). Aucun nouveau point d'entrée, AC5 de 20.1 préservé. Contrepartie : plus de total du parc d'un coup d'œil.
  - **B — compteurs sur les cartes de pièces**, via un nouveau point d'entrée agrégé du démon appuyé sur `evaluate_equipment()`. Plus fidèle à l'ancienne synthèse, mais hors de la règle « aucun nouveau point d'entrée » de l'epic et du chargement borné de 20.1.
  - **C — un total unique** (« N équipements publiés ») sur la page, sans détail par pièce ; source à choisir (nouveau point d'entrée ou témoin existant).
- **Q2 — Que deviennent Republier et Supprimer puis recréer par pièce et par équipement (F2) ?**
  - **Décision : A.**
  - **A (recommandé) — conservés, déplacés dans la surface** : « Appliquer » (20.2) couvre déjà « Publier » par équipement ; ajouter « Republier la pièce » dans la modale de pièce, et « Supprimer puis recréer » par équipement et par pièce avec la confirmation forte actuelle, sur les gestionnaires existants (`executeHaAction`). Les boutons globaux restent sur la page, leurs confirmations dérivent leurs nombres du parc sans la synthèse (à préciser au cadrage : relevé simple ou point d'entrée existant, voir Q2b : par défaut sans nombre, jamais un recalcul).
  - **B — retirés** : seuls les boutons globaux subsistent ; l'utilisateur perd la republication et la suppression ciblées. À assumer explicitement.
- **Q2b — D'où viennent les nombres des confirmations des boutons globaux (« N équipements inclus », « N publiés ») ?** Aujourd'hui : `published_scope` via la synthèse ; `getBridgeStatus` ne fournit aucun décompte, et la surface ne charge que les pièces ouvertes.
  - **Décision : A.**
  - **A (recommandé) — retirer les nombres** : « Republier tous les équipements inclus ? » / « Supprimer puis recréer tout le parc publié ? », avec la mise en garde forte actuelle. Aucune source nouvelle, AC7 tenu tel quel.
  - **B — nommer une source globale autorisée** : lecture limitée de `published_scope` par ces seules confirmations (AC7 amendé pour cette exception unique).
  - **C — nouveau point d'entrée agrégé** appuyé sur `evaluate_equipment()`.
- **Q3 — Que reprend-on de la modale Diagnostic (F3, F4) ?**
  - **Décision : A**, y compris le retrait des badges streaming et parité FAN de l'interface ; l'export de diagnostic support est conservé.
  - **A (recommandé) — rien d'autre que ce que l'arbre porte déjà** (cause par commande et par entité, 20.2) ; l'échec technique de publication (étape 5), la trace du pipeline et le badge « Écart » disparaissent de l'interface ; « Télécharger le diagnostic support » reste l'outil de support. Liste des pertes écrite dans la story et confirmée.
  - **B — reprendre en plus un signal d'échec de publication par équipement** dans la surface (nécessite que l'arbre le porte : nouveau champ additif du démon).
  - Dans les deux cas : le badge streaming global (15.2) et la parité FAN (15.3) sont-ils retirés (recommandé : oui, aucun ne figure dans la surface) ou repris ?
- **Q4 — Que devient la page « gabarit » (F5) ?**
  - **Décision : A.**
  - **A (recommandé) — retrait de la section « Mes templates » et des champs sans usage** (paramètre n°1, mot de passe, auto-actualisation, assistant cron) ; le squelette de page requis par le cœur Jeedom (conteneurs `eqLogic`, `eqLogicThumbnailDisplay`, onglets Équipement / Commandes) est conservé, ses libellés réécrits en français d'usage ; « Ajouter » conservé tant que le cœur l'exige (Task 1.3 le vérifie).
  - **B — retirer aussi la création d'équipement `jeedom2ha`** (« Ajouter », page d'édition) : plus net, mais touche le contrat de page du cœur Jeedom et les crochets de la classe ; à n'envisager qu'avec la preuve de la Task 1.3.

## Acceptance Criteria

**AC1 — « Parc global » supprimé**

**Given** la page principale du plugin
**When** elle s'affiche
**Then** ni `#div_scopeSummary`, ni `#bt_refreshScopeSummary`, ni la chaîne « Parc global », ni « Synthèse du périmètre publié » n'apparaissent dans le DOM rendu
**And** `jeedom2ha_scope_summary.js` n'est plus inclus et ses gestionnaires (`.j2ha-row-toggle`, `.j2ha-ecart-clickable`, boutons de synthèse) n'existent plus
**And** aucune requête `getPublishedScopeForConsole` n'est émise au chargement (inventaire du gate), donc plus de diagnostic de tout le parc chargé à l'affichage de la page.

**AC2 — Modale Diagnostic supprimée**

**Given** le bloc « Gestion »
**When** il s'affiche
**Then** l'action « Diagnostic » (`data-action="diagnostic"`) et la modale « Diagnostic de Couverture » n'existent plus, et aucune requête `getDiagnostics` n'est émise
**And** « Ajouter » et « Configuration » gardent la classe `eqLogicThumbnailContainer` et les attributs `eqLogicAction` / `data-action` dont dépend le cœur Jeedom
**And** « Télécharger le diagnostic support » (`exportDiagnostic`) est conservé et inchangé **[Q3]**.

**AC3 — Compteurs de remplacement [Q1]**

**Given** une pièce ouverte (recommandation A)
**When** son arbre est lu
**Then** l'entête de la pièce affiche les compteurs décidés (équipements publiés, exclus, désactivés, à corriger ; commandes prêtes, bloquantes, non couvertes), chacun avec son unité dite en français
**And** chaque nombre est un dénombrement des champs de l'arbre du démon (`equipment_decision`, décision par commande, `covered`) : aucune décision n'est recalculée par l'interface
**And** une exclusion posée par l'utilisateur est comptée « exclue », une commande non couverte n'est jamais comptée bloquante, un équipement désactivé n'est jamais compté bloquant (règles de 16.8 et 20.1 conservées)
**And** aucun arbre de pièce non ouverte n'est lu (AC5 de 20.1 inchangé) ; sous B ou C, le seul nouveau point d'entrée est celui que la décision d'Alex nomme.

**AC4 — Capacités de la synthèse conservées ou retirées explicitement [Q2]**

**Given** les actions que portait la synthèse (F2)
**When** la story est livrée
**Then** chacune est soit disponible dans la surface (recommandation A : « Republier la pièce », « Supprimer puis recréer » par pièce et par équipement, mêmes confirmations fortes, mêmes routes), soit retirée et listée dans « Pertes assumées »
**And** les boutons globaux « Republier » et « Supprimer puis recréer » fonctionnent sans la synthèse : leurs confirmations suivent Q2b : sans nombre (recommandation A) ou avec le nombre d'une source globale nommée par Alex (B ou C), jamais d'un recalcul de l'interface
**And** le gating des boutons globaux (`applyHAGating`) ne dépend plus d'un rendu de synthèse.

**AC5 — Contenu diagnostic [Q3]**

**Given** la modale supprimée
**Then** le contenu repris dans la surface est exactement celui que la décision d'Alex désigne ; tout le reste (trace du pipeline, cause canonique, résultat technique d'étape 5, badge « Écart », badges streaming et parité FAN en recommandation A) est listé dans « Pertes assumées » avec la voie de remplacement (export support)
**And** les helpers `jeedom2ha_diagnostic_helpers.js` sans consommateur restant sont retirés, ceux qui servent encore sont conservés.

**AC6 — Libellés français d'usage [Q4]**

**Given** la page principale, la modale d'une pièce ouverte et la page d'édition d'équipement
**When** le texte rendu est relevé
**Then** il ne contient plus aucune des chaînes interdites : « Mes templates », « Template », « Paramètre n°1 », « Paramètres spécifiques », et celles de la table de remplacement validée en Task 1.2 (jargon d'infrastructure : « Écart », « Confiance », « mapping », « eq_id », « reason_code », noms de routes ou de types internes)
**And** chaque libellé de remplacement figure dans la table de la story (ancien → nouveau → emplacement) et passe par `{{ }}` / `__()` pour la traduction
**And** les champs sans usage retirés (recommandation A de Q4) ne laissent aucun `eqLogicAttr` orphelin dans la page.

**AC7 — `evaluate_equipment()` comme source de l'interface**

**Given** le code livré
**Then** aucune fonction de la surface ni aucun compteur ne lit `published_scope`, `diagnostic_equipments` ou `home_signals` ; un test Node échoue si la surface les référence
**And** aucune règle de décision (confiance, éligibilité, exclusion, forçage) n'est réécrite côté interface
**And** les routes du démon (`/system/diagnostics`, `published_scope`) ne sont pas supprimées par cette story (leur consommateur d'export subsiste, F4).

**AC8 — Non-régression de la surface**

**Given** la surface livrée par 20.1, 20.2 et 20.4
**Then** l'édition du type HA, l'exclusion, le forçage, le retour au mode automatique, « Appliquer », la pièce « Sans pièce », les états grisés et le rescan de la page principale fonctionnent comme avant (suites Node et Python existantes vertes)
**And** aucun `generic_type` de Jeedom n'est modifié (D10).

**AC9 — Limites de périmètre (vérifiées à la revue)**

**Given** la story livrée
**Then** aucune exclusion de pièce, aucun changement de décision, aucune route du démon supprimée, aucun point d'entrée du démon créé hors Q1 B/C ou Q3 B décidés par Alex.

**AC10 — Preuve UX et terrain**

**Given** le code fusionné sur `main` et déployé par la procédure standard
**When** le `done` est évalué
**Then** le gate 20-0 passe sur `main` : découverte étendue (absence de `#div_scopeSummary`, de « Parc global » et de l'action « Diagnostic » dans le DOM ; absence de `getPublishedScopeForConsole` et de `getDiagnostics` au chargement ; chaînes interdites absentes du texte de la page et d'une pièce ouverte ; compteurs de la pièce relevés), référence et parcours d'exclusion de 20.2 toujours PASS ; la politique du gate et l'inventaire de chargement sont mis à jour en conséquence
**And** les compteurs d'une ou plusieurs pièces réelles (dont le Garage et « Sans pièce ») sont comparés à un relevé indépendant en lecture seule de l'arbre (`getMappingOverrides`) : aucun écart inexpliqué
**And** si Q2 = A, chaque action déplacée (Republier, Supprimer puis recréer) est prouvée au clic réel suivant la règle de la revue Codex du 2026-10-01 : équipement non publié, témoin `getBridgeStatus` relevé avant et après, sync correctif si le témoin a bougé, jamais d'écriture sur un équipement publié sans GO d'Alex ; le gate 20-0 ne transmet aucune écriture
**And** un déploiement standard du SHA exact, avec relevés avant et après (box et HA), est consigné
**And** un passage dans Chrome par ClaudeBox, en lecture seule, parcourt la page, une pièce, l'équipement désactivé du Garage et « Sans pièce », et consigne la liste des chaînes vérifiées
**And** la story passe par `ready-for-UX-validation` avant `done`.

## Tasks / Subtasks

- [ ] **Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)** *(exécuté par l'humain ou ClaudeBox ; jamais par une session cloud déléguée)*
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
    - **Pour cette story : déploiement standard seulement** (voir « Interdits ») ; aucun mode de nettoyage.
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
- [ ] **Task 1 — Relevés préalables, lecture seule (AC: 1-6)**
  - [ ] 1.1 Relire F1 à F7 au SHA courant (20.2 `done` entre-temps modifie le code touché).
  - [ ] 1.2 Inventaire exhaustif des libellés visibles (PHP, `desktop/js/*.js`, CSS `content:`), classés : gabarit Jeedom / jargon d'infrastructure / libellé d'usage correct ; table « ancien → nouveau → emplacement » soumise à Alex.
  - [ ] 1.3 Lire ce que le cœur Jeedom exige de la page de plugin (`plugin.template`, `eqLogicAction`, conteneurs) pour trancher Q4 A/B sans casser « Ajouter », « Configuration » et la page d'équipement.
  - [ ] 1.4 Relever, par pièce réelle (Garage, bureau, extérieur, « Sans pièce »), les compteurs de l'arbre et de l'ancienne synthèse, pour la comparaison d'AC10 ; relever aussi qui d'autre consomme `getPublishedScopeForConsole`, `getDiagnostics`, `jeedom2ha_diagnostic_helpers.js` (AC5, AC7).
  - [ ] 1.5 Rejouer la recherche de F6 au SHA courant et classer **chaque** fichier trouvé (pas seulement la liste de F6, état au 2026-10-06) : retirer / réaffecter / conserver, avec justification.
- [ ] **Task 2 — Retrait de la synthèse et de la modale (AC: 1, 2, 5, 7)**
  - [ ] 2.1 `jeedom2ha.php` : retirer `#div_scopeSummary` et l'action « Diagnostic » ; garder classes et attributs du bloc « Gestion » ; ne plus inclure `jeedom2ha_scope_summary.js`.
  - [ ] 2.2 `jeedom2ha.js` : retirer `refreshPublishedScopeSummary`, les gestionnaires de synthèse, le gestionnaire `diagnostic` et la modale ; découpler `applyHAGating` et les confirmations globales de la synthèse (AC4).
  - [ ] 2.3 Helpers de diagnostic sans consommateur retirés ; `exportDiagnostic` inchangé.
- [ ] **Task 3 — Compteurs et capacités de remplacement (AC: 3, 4, 7) — selon Q1, Q2, Q3**
  - [ ] 3.1 Module pur de dénombrement à partir de l'arbre (équipements et commandes), testé sans DOM ; aucun recalcul de décision.
  - [ ] 3.2 Rendu de l'entête de pièce ; libellés d'unité.
  - [ ] 3.3 Selon Q2 : actions déplacées sur les gestionnaires existants, confirmations conservées ; sinon, « Pertes assumées » renseignées.
  - [ ] 3.4 Confirmations globales selon Q2b (AC4).
- [ ] **Task 4 — Libellés d'usage (AC: 6) — selon Q4**
  - [ ] 4.1 Retrait de « Mes templates » et des champs sans usage ; réécriture des libellés restants selon la table validée.
  - [ ] 4.2 Test Node qui parcourt les chaînes rendues et échoue sur toute chaîne interdite.
- [ ] **Task 5 — Tests (AC: 1-9)** : Node (module de dénombrement, absence de références à `published_scope` et co., chaînes interdites, non-régression 16.8 / 20.1 / 20.2 / 20.4), PHP (page sans synthèse, relais conservés), tests retirés ou réaffectés selon la Task 1.5 ; `flake8` si du Python est touché.
- [ ] **Task 6 — Gate et preuve (AC: 10)**
  - [ ] 6.1 Gate : parcours de découverte étendu, politique et inventaire de chargement mis à jour, auto-test local.
  - [ ] 6.2 Après fusion : déploiement standard, relevés avant et après, gate sur `main`, comparaison des compteurs, clic réel des actions déplacées si Q2 = A, passage Chrome ClaudeBox, `ready-for-UX-validation`, validation UX.

## Dev Notes

### Dépendance à 20.2 (explicite)

- **Aucun développement avant 20.2 `done`.** 20.3 touche les fichiers que 20.2 vient de modifier (`jeedom2ha_mapping_surface.js`, `jeedom2ha_mapping_override.js`, `core/ajax/jeedom2ha.ajax.php`, parcours et politique du gate) ; démarrer avant sa clôture ferait diverger les deux livraisons.
- 20.3 **réutilise** de 20.2 : le bouton « Appliquer » (publication ciblée d'un équipement, base de Q2 A), `equipment_decision` et `entities[]` de l'arbre (base des compteurs de Q1 A), les harnais Node `node:vm` (confirmations, état des boutons) et les parcours gate simulant les écritures.
- État au 2026-10-06 : code de 20.2 fusionné sur `main` ; restent la preuve post-fusion (5.2), la preuve terrain au clic réel et la validation UX (5.3). Le comportement affiché pour un équipement exclu sans commande (« Exclu », AC8 de 20.2) doit être livré et prouvé avant que les compteurs de 20.3 en dépendent.

### Contrats réutilisés (SHA `df6bb51`)

- Page : `desktop/php/jeedom2ha.php:60-209` (page d'accueil, synthèse `:92-106`, surface `:156-178`, « Mes templates » `:180-208`), `:211-359` (page d'équipement).
- Synthèse : `desktop/js/jeedom2ha_scope_summary.js`, `desktop/js/jeedom2ha.js:136-250` (gating, navigation), `:529-580`, `:600-738`.
- Modale : `desktop/js/jeedom2ha.js:872-1354`, `desktop/js/jeedom2ha_diagnostic_helpers.js`.
- Relais PHP : `core/ajax/jeedom2ha.ajax.php:646-725`, `core/class/jeedom2ha.class.php:578`.
- Arbre : `resources/daemon/transport/http_server.py:2860-3130` (inchangé par cette story).
- Gate : `tests/e2e/gate/lib/policy.mjs:51-52`, `tests/e2e/gate/page-load-request-inventory.mjs:186-187`, `tests/e2e/gate/parcours/decouverte-garage-enphase.mjs`.

### Interdits

- Aucun recalcul de décision côté interface ; jamais d'écriture du `generic_type` de Jeedom (D10) ; aucune route du démon supprimée ; aucun nouveau point d'entrée hors décision d'Alex (Q1 B/C, Q3 B).
- Ne pas charger les arbres de tout le parc au chargement de la page (AC5 de 20.1).
- Ne pas laisser un test rouge ni en retirer un sans le justifier (Task 1.5).
- Jamais `git add -A`, jamais `--admin`, aucun force-push. Déploiement standard seulement, jamais `--cleanup-discovery` ni `--stop-daemon-cleanup`.
- Preuve terrain qui écrit : aucun équipement publié touché sans GO d'Alex.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle, par l'humain ou ClaudeBox ; jamais depuis une session cloud déléguée.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

### Fichiers probablement touchés

`desktop/php/jeedom2ha.php`, `desktop/js/jeedom2ha.js`, `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/js/jeedom2ha_mapping_override.js`, `desktop/js/jeedom2ha_scope_summary.js` (supprimé), `desktop/js/jeedom2ha_diagnostic_helpers.js` (supprimé ou réduit), `desktop/css/jeedom2ha.css`, `core/ajax/jeedom2ha.ajax.php` et `core/class/jeedom2ha.class.php` (relais ou crochets de gabarit, selon Q2 et Q4), tests Node/PHP issus de la recherche de F6 (Task 1.5), `tests/e2e/gate/lib/policy.mjs`, `tests/e2e/gate/page-load-request-inventory.mjs`, `tests/e2e/gate/parcours/decouverte-garage-enphase.mjs`.

### Pertes assumées (décisions Q2=A et Q3=A)

Tableau global du parc et ses compteurs d'équipements ; badge « Écart » et navigation vers la modale ; trace du pipeline, cause canonique et résultat technique d'un échec de publication ; badges streaming global et parité FAN ; (si Q2 = B) republication et suppression ciblées par pièce et par équipement. Voie de remplacement : surface unique (cause par commande), « Télécharger le diagnostic support », boutons globaux.

## Conditions de passage à `ready-for-dev`

1. 20.2 est `done` (preuve post-fusion, preuve terrain au clic réel, validation UX).
2. Task 1.1 est refaite au SHA de ce moment si le code de 20.2 a bougé ; la table de libellés de la Task 1.2 est validée.

## Définition de done

- 20-0 et 20.1 sont `done` (tenu) ; 20.2 `done` (à tenir avant le développement).
- Tous les AC sont couverts par des tests nommés ou par le gate ; la File List est complète.
- CI verte ; revue Codex sans problème majeur (ou relecture indépendante si Codex est indisponible) ; relecture ClaudeBox.
- **Gate 20-0 vert sur le code de `main`** (découverte étendue, référence, parcours d'exclusion) avant tout passage à `done`, aucune écriture transmise à la box pendant le gate.
- Déploiement standard du SHA exact relu, relevés avant et après sans écart inexpliqué (box et HA) ; comparaison des compteurs consignée ; clic réel des actions déplacées (Q2 = A).
- Passage Chrome de ClaudeBox consigné, puis `ready-for-UX-validation`, puis validation UX d'Alex.
- Au `done` : SHA, CI, commandes de tests, preuves et validation UX consignés (rétrospective pe-epic-19). CC-04 (volet UI) fermé : plus aucun jargon Jeedom résiduel dans l'interface livrée.

## Journal des décisions

- 2026-10-01 — Décision d'Alex (SCP, décision 1) : synthèse « Parc global » et modale diagnostic supprimées au profit de la surface unique.
- 2026-10-05, 10:43 — Décision d'Alex (« 1A 2A 3C 4A » sur 20.1) : pas de compteurs en 20.1 ; le remplacement des compteurs est décidé et livré par 20.3. Faits à reprendre : la lecture de « Parc global » charge le diagnostic de tout le parc ; ses compteurs comptent des équipements et ignorent les exclusions manuelles.
- 2026-10-06 — `create-story` de 20.3 (session cloud déléguée, lecture seule, aucun accès box/HA) : faits F1 à F7 relevés dans le code de `main` `df6bb51` ; constat que la synthèse et la modale portent des capacités autres que des compteurs (actions ciblées, nombres des confirmations globales, échec technique de publication) ; questions Q1 à Q4 posées avec recommandation A. **`ready-for-dev` non accordé.**
- 2026-10-06 — Alexandre valide les arbitrages **Q1=A, Q2=A, Q2b=A, Q3=A, Q4=A**. Les AC et tâches conditionnelles sont figés sur ces choix ; 20.2 reste l'unique dépendance de statut avant le développement.

## References

- `_bmad-output/planning-artifacts/epics-projection-engine.md`, Epic 20, Story 20.3 et gates epic-level pe-epic-20.
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-01-etape-4-interface.md`, décision 1 et « Risques et suivi ».
- `_bmad-output/implementation-artifacts/20-1-surface-unique-piece-equipement-commande.md` (Q3, AC5, faits sur les compteurs) et `20-1-preuve-validation-ux-2026-10-05.md`.
- `_bmad-output/implementation-artifacts/20-2-exclusion-forcage-depuis-surface-cc26.md` (dépendance) ; `20-4-rescan-page-principale-cc04-ui.md`.
- `_bmad-output/implementation-artifacts/20-0-gate-preuve-ux-outille.md`, « Invocation du gate par une story suivante ».
- Stories d'origine de la synthèse et de la modale : 4.4 à 4.6, 5.1 à 5.3, 15.2, 15.3.

## Dev Agent Record

### Agent Model Used

À renseigner au `dev-story`.

### Completion Notes List

- 2026-10-06 — `create-story` seulement : aucun code, test, script ni configuration modifié ; statut `backlog` conservé (voir l'encadré d'en-tête).

### File List

- `_bmad-output/implementation-artifacts/20-3-suppression-gabarit-jeedom-libelles-francais-cc04-ui.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/operations/delegations.md` (ligne de journal de délégation, commit `914110c` déjà présent sur la branche)

### Change Log

- 2026-10-06 — Création de la story (brouillon complet, `ready-for-dev` bloqué par Q1 à Q4 et par 20.2 non `done`).
