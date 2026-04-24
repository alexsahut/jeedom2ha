# Story 6.2 : Diagnostic - enrichissement cause et actions - l'utilisateur comprend clairement le probleme et comment le corriger

Status: historical-artifact-rehomed

Epic d'origine: `pe-epic-6` - Le diagnostic est explicable et actionnable

Disposition BMAD: story re-homee vers `pe-epic-7`

Entree sprint-status: `6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger`

## Correct-course 2026-04-22 - Disposition opposable

- Cette story n'est plus un item executable du backlog actif.
- Le NO-GO terrain du `2026-04-21` a montre que sa promesse story-level ne pouvait pas etre tenue honnetement dans `pe-epic-6`.
- Aucun developpement supplementaire ne doit repartir depuis ce fichier.
- La capacite non construite est re-homee vers `pe-epic-7`, a commencer par une story additive portant `projection_validity` et les preconditions d'actionnabilite reelle.
- Ce fichier reste conserve comme artefact historique d'un sequencing invalide, pas comme source de travail.

## Story

En tant qu'utilisateur de jeedom2ha,  
je veux que le diagnostic me donne une cause claire, contextualisee et accompagnee d'une action lisible,  
afin de comprendre immediatement pourquoi l'equipement n'est pas publie et quoi faire ensuite.

## Contexte / Objectif produit

La Story 6.1 est **done** et son gate terrain UX/UI reel est **PASS** au `2026-04-21`.

Le constat terrain le plus important a ete documente explicitement dans la story 6.1 :

- un cas `step 3` reel et un cas `step 4` reel affichent le meme libelle visible `Mapping ambigu - plusieurs types possibles` ;
- le **stepper est actuellement le seul discriminant perceptible** entre les deux ;
- le contrat canonique et l'invariant **I7** sont corrects, mais la lecture utilisateur reste cognitivement ambigue.

Cette story 6.2 a ete **initialement executee comme une amelioration UX pure**, strictement bornee a :

- clarifier la lecture visible de la cause ;
- rendre l'action suivante plus evidente ;
- distinguer sans ambiguite un probleme de projection / validation d'un arbitrage de decision de publication ;
- rester **backend-first**, additif, compatible 6.1, sans toucher au moteur de decision.

### Decision de sequencement a respecter

- `epics-projection-engine.md` porte encore le decoupage initial `6.2 = projection_validity` / `6.3 = cause_label-cause_action`.
- Le brief PO de creation de story du `2026-04-21`, base sur le gate terrain 6.1, **re-priorise explicitement** la clarification UX des causes comme prochaine story a executer.
- Cette story est donc la **reference d'execution ready-for-dev** pour la prochaine tranche backlog du tracker.
- **Ne pas profiter de cette story** pour rouvrir opportunistement l'ancien chantier documentaire `projection_validity` de la 6.2 initiale.
- **Correct-course approuve le 2026-04-21** : ne pas tenter de "sauver" cette story en rouvrant maintenant un gros chantier `projection_validity`. L'action immediate approuvee est de realigner la promesse story-level, de conserver 6.2 `in-progress`, et de faire de 6.3 la prochaine story requise pour la semantique honnete `cause_label` / `cause_action` et la regle `no faux CTA`.

## Contexte terrain 6.1 a reprendre tel quel

- Cas terrain `step 3` observe le `2026-04-21` : `Garage / CHACON_porte-garage` (cmds `#2210-2212`)
- Cas terrain `step 4` observe le `2026-04-21` : `terrasse / lames pergola (virt)` (`eq_id 380`)
- Observation 6.1 consignee : le libelle `Mapping ambigu` apparait sur les deux cas ; le stepper seul permet de les distinguer.
- Cette story existe pour eliminer cette ambiguite **sans modifier la cause canonique** ni la separation decision / technique deja validees.

## Scope

### In scope

- enrichissement UX de `cause_label` et `cause_action` ;
- contextualisation visible par etape de pipeline ;
- differenciation explicite `step 3` vs `step 4` ;
- amelioration de la lisibilite utilisateur du diagnostic existant ;
- backend minimal si necessaire pour exposer des libelles / actions contextualises ;
- propagation PHP/JS en lecture stricte du backend ;
- tests cibles et gate terrain UX reel.

### Out of scope

- toute modification du pipeline backend 1 -> 5 ;
- toute nouvelle regle de decision, de mapping ou de gouvernance ;
- toute creation, suppression, inversion de sens ou renommage de `reason_code` ;
- toute promotion d'un `technical_reason_code` en cause principale ;
- toute logique metier ou recontextualisation cote frontend ;
- toute refonte UI globale ou creation d'une surface parallele ;
- tout chantier complet d'ajout du sous-bloc `projection_validity` dans `traceability`.

## Acceptance Criteria

1. **AC1 - Cause contextualisee par etape**
   **Given** deux equipements partageant un meme `traceability.decision_trace.reason_code`
   **And** l'un est affiche en `pipeline_step_visible = 3` et l'autre en `pipeline_step_visible = 4`
   **When** l'utilisateur lit le diagnostic
   **Then** le `cause_label` visible n'est pas identique entre les deux cas
   **And** le libelle `step 3` explique un probleme de projection / validation technique
   **And** le libelle `step 4` explique un arbitrage de decision / publication
   **And** le stepper n'est plus le seul element permettant de distinguer les deux situations.

2. **AC2 - Alignement strict avec le modele canonique**
   **Given** un diagnostic enrichi
   **When** `cause_label` et `cause_action` sont calcules
   **Then** la cause canonique reste derivee exclusivement de `traceability.decision_trace.reason_code`
   **And** la contextualisation s'appuie uniquement sur des donnees backend deja canoniques, notamment `pipeline_step_visible`
   **And** aucun recalcul metier n'est realise dans `core/ajax/jeedom2ha.ajax.php` ou dans le JS.

3. **AC3 - Action utilisateur explicite et honnete**
   **Given** un equipement bloque en `step 2`, `step 3` ou `step 4`
   **When** l'utilisateur lit le diagnostic
   **Then** une action ou un prochain pas clair est visible via `cause_action`
   **And** cette action est formulee dans le langage utilisateur, sans code technique brut
   **And** si aucune remediation utilisateur directe n'existe reellement, le texte l'indique explicitement sans faux CTA
   **And** les actions restent coherentes avec les surfaces existantes de Jeedom / jeedom2ha.

4. **AC4 - Aucun impact sur I7**
   **Given** un equipement en `step 5 failed`
   **When** le diagnostic enrichi est rendu
   **Then** la cause principale contextualisee continue d'etre ancree sur `decision_trace.reason_code`
   **And** `publication_trace.technical_reason_code` reste confine au bloc technique
   **And** aucun wording enrichi n'introduit de confusion entre decision pipeline et resultat technique.

5. **AC5 - Additivite stricte**
   **Given** le catalogue actuel de `reason_code`, le contrat 4D et les consommateurs existants
   **When** la story est livree
   **Then** aucun `reason_code` existant n'est modifie, supprime ou renomme
   **And** l'enrichissement est porte par un mapping UX additif pur
   **And** le schema diagnostic historique reste stable hors enrichissements documentes
   **And** aucune logique multi-cause ou fallback implicite ne change la semantique du diagnostic.

6. **AC6 - Lisibilite UX validee**
   **Given** un gate terrain UX reel couvrant au minimum un cas `step 2`, un cas `step 3` et un cas `step 4`
   **When** un utilisateur lit le diagnostic sans consulter de log technique
   **Then** il comprend en moins de 3 secondes pourquoi ca bloque
   **And** il comprend quoi faire ensuite
   **And** il peut distinguer `step 3` et `step 4` sans s'appuyer uniquement sur le stepper.

## Tasks / Subtasks

- [ ] Task 0 - Pre-flight terrain (DEV/TEST ONLY - pas la release Market)
  - [x] Dry-run : verifier sans transferer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Selectionner le mode selon l'objectif de la story :
    - Verification disparition entites HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Verifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup termine.`

- [x] Task 1 - Designer le mapping UX contextuel (AC: #1, #2, #3, #5)
  - [x] Inventorier les cas ou le meme `decision_trace.reason_code` produit aujourd'hui une lecture utilisateur ambigue selon `pipeline_step_visible`, en priorite les cas observes en terrain 6.1.
  - [x] Definir une couche pure de contextualisation backend de forme `cause canonique + contexte etape -> cause_label / cause_action`.
  - [x] Preserver la table de base `reason_code -> cause` comme socle stable ; si un nouveau helper est ajoute, le faire sans casser les cas non concernes.
  - [x] Formaliser un wording utilisateur distinct pour `step 3` et `step 4`, coherent avec le brief PO et honnete sur les actions reellement disponibles.

- [x] Task 2 - Integrer l'enrichissement backend minimal sans rouvrir le pipeline (AC: #1, #2, #4, #5)
  - [x] Implementer la contextualisation dans `resources/daemon/models/cause_mapping.py` ou un helper voisin pur, jamais dans le frontend.
  - [x] Reutiliser `pipeline_step_visible` livre par 6.1 comme signal de contexte UX, sans recalculer les etapes.
  - [x] Appliquer le mapping enrichi au moment de construire `eq_dict` dans `resources/daemon/transport/http_server.py`.
  - [x] Conserver intacts `reason_code`, `cause_code`, `traceability`, `pipeline_step_visible` et la separation I7.

- [x] Task 3 - Propager le contrat et afficher l'action sans logique locale (AC: #2, #3, #6)
  - [x] Verifier que `core/ajax/jeedom2ha.ajax.php` reste un simple passthrough des champs enrichis.
  - [x] Mettre a jour la surface diagnostic existante (`desktop/js/jeedom2ha.js` et helpers associes) pour afficher le `cause_label` enrichi et l'action associee fournis par le backend.
  - [x] Garder la modal diagnostic existante ; aucune surface parallele, aucun mapping JS local `reason_code -> libelle/action`.
  - [x] Si une micro-retouche visuelle est necessaire pour la lisibilite, la borner au rendu existant de la modal.

- [x] Task 4 - Verrouiller les tests et la non-regression (AC: #1, #2, #4, #5)
  - [x] Ajouter une suite backend dediee type `resources/daemon/tests/unit/test_story_6_2_contextual_cause_mapping.py` ou etendre les suites 6.1 de facon lisible.
  - [x] Couvrir au minimum : meme `reason_code`, `step 3` vs `step 4`, labels differents ; action associee honnete ; non-regression I7.
  - [x] Verifier que les `reason_code` restent inchanges et que le contrat historique (`reason_code`, `cause_code`, `cause_label`, `cause_action`, `traceability`, export) reste stable.
  - [x] Ajouter des tests JS garantissant que le frontend affiche les champs backend enrichis sans les recalculer.

- [ ] Task 5 - Gate terrain UX reel (AC: #6)
  - [ ] Valider sur box Jeedom reelle au minimum un cas `step 2`, un cas `step 3`, un cas `step 4`.
  - [ ] Verifier que la cause visible distingue clairement `step 3` et `step 4`, sans s'appuyer uniquement sur le stepper.
  - [ ] Verifier que l'action visible est comprise immediatement et ne promet aucune correction inexistante.
  - [ ] Documenter dans la story la date, l'environnement, les `eq_id` / cas observes, le verdict et les limites explicites avant passage a `done`.

## Dev Notes

### Fondations opposables

- La cause canonique principale provient de `traceability.decision_trace.reason_code`.
- Le pipeline canonique reste strictement ordonne : `1 -> 2 -> 3 -> 4 -> 5`.
- La regle globale 2 du `pipeline-contract.md` reste opposable : premier echec decisionnel dans l'ordre du pipeline = cause principale retenue.
- La regle globale 9 du `pipeline-contract.md` reste opposable : la decision pipeline et le resultat technique coexistent sans se remplacer.
- L'invariant **I7** est non negociable : `technical_reason_code` n'alimente jamais la cause principale.
- `cause_mapping.py` reste l'unique endroit autorise pour traduire `reason_code -> (cause_code, cause_label, cause_action)`.

### Intelligence tiree de la Story 6.1

- Le commit `0cb3988` (`feat(pe-6.1): diagnostic par etape pipeline + separation step5 failed`) a deja etabli les zones de code a reutiliser :
  - `resources/daemon/transport/http_server.py`
  - `resources/daemon/models/cause_mapping.py`
  - `core/ajax/jeedom2ha.ajax.php`
  - `desktop/js/jeedom2ha.js`
  - `desktop/js/jeedom2ha_diagnostic_helpers.js`
  - `resources/daemon/tests/unit/test_story_6_1_pipeline_step_diagnostic.py`
  - `tests/unit/test_story_6_1_pipeline_step.node.test.js`
- Le gate terrain 6.1 a confirme que le contrat est juste, mais que le wording visible n'est pas encore assez discriminant pour l'utilisateur.
- La Story 6.2 doit donc **prolonger le pattern 6.1**, pas inventer une nouvelle architecture de diagnostic.

### Git Intelligence Summary

- Commit recent le plus pertinent : `0cb3988` - `feat(pe-6.1): diagnostic par etape pipeline + separation step5 failed (#98)`
- Commit de closeout tracker : `3f11eea` - `chore(bmad): close story 6.1 after merge and set tracker done (#99)`
- Conclusion exploitable : la story 6.2 doit repartir des memes fichiers et des memes patterns de tests, sans deplacer la logique hors des couches deja stabilisees.

### Strategie d'implementation backend-first

- Commencer par le daemon et la production de `cause_label` / `cause_action`.
- Reutiliser `pipeline_step_visible` comme signal de contexte UX deja stabilise par 6.1.
- Preferer un helper pur additionnel plutot qu'une re-ecriture de la table `_REASON_CODE_TO_CAUSE`.
- Si le meme `reason_code` doit produire deux libelles differents selon l'etape, faire porter cette distinction cote backend seulement.
- Le PHP et le JS ne doivent faire que transporter / afficher.

### Frontiere explicite a respecter

- **Ne pas rouvrir le moteur de decision** : pas de changement de `decide_publication`, de validation HA, ni de l'ordre du pipeline.
- **Ne pas rouvrir le chantier `projection_validity`** : l'ajout du sous-bloc complet dans `traceability` n'est pas le scope de cette story.
- **Ne pas promettre une action inexistante** : si l'utilisateur ne peut pas agir directement, le wording doit le dire explicitement.
- **Ne pas fusionner plusieurs causes** : une cause principale contextualisee, pas une liste de problemes.

### Fichiers / zones candidates

- Mapping cause UX :
  - `resources/daemon/models/cause_mapping.py`
- Construction du diagnostic :
  - `resources/daemon/transport/http_server.py`
- Relay PHP :
  - `core/ajax/jeedom2ha.ajax.php`
- UI diagnostic :
  - `desktop/js/jeedom2ha.js`
  - `desktop/js/jeedom2ha_diagnostic_helpers.js`
- Styles si strictement necessaire :
  - `desktop/css/jeedom2ha.css`
- Tests backend :
  - `resources/daemon/tests/unit/test_story_6_1_pipeline_step_diagnostic.py`
  - nouvelle suite story 6.2 si plus lisible
- Tests frontend :
  - `tests/unit/test_story_6_1_pipeline_step.node.test.js`
  - nouvelle suite story 6.2 si plus lisible

### Exemples de wording cibles a utiliser comme boussole

- `step 2` :
  - `cause_label` attendu type : `Mapping incomplet ou incoherent`
  - `cause_action` attendu type : `Verifier les types generiques et les commandes de l'equipement dans Jeedom`
- `step 3` :
  - `cause_label` attendu type : `Projection Home Assistant incomplete - certaines commandes requises sont manquantes`
  - `cause_action` attendu type : `Ajouter ou corriger les commandes requises (ON/OFF/STATE) dans Jeedom`
- `step 4` :
  - `cause_label` attendu type : `Plusieurs interpretations possibles - la publication n'a pas ete decidee automatiquement`
  - `cause_action` attendu type : `Preciser les types generiques pour lever l'ambiguite`  
    ou un wording explicitement non-actionnable si aucune correction directe n'existe reellement.

Ces exemples sont des **cibles UX**, pas une autorisation de modifier le moteur ni d'introduire une fonctionnalite inexistante.

### Strategie de test ciblee

- Backend :
  - prouver qu'un meme `decision_trace.reason_code` peut produire deux `cause_label` differents selon `pipeline_step_visible`
  - prouver que `decision_trace.reason_code` lui-meme ne change pas
  - prouver que `technical_reason_code` reste hors cause principale
  - prouver que les autres cas historiques restent inchanges
- Frontend :
  - prouver que la colonne / zone visible lit `cause_label` enrichi du backend
  - prouver que l'action affichee vient de `cause_action`
  - prouver l'absence de table locale JS de contextualisation metier
- Terrain :
  - reprendre un cas reel `step 3` et un cas reel `step 4` de 6.1 si toujours observables
  - consigner explicitement si un cas a disparu du dataset reel

### Latest Technical Information

- Aucune recherche web externe n'est requise pour cette story.
- Le scope est entierement borne a des contrats internes, des patterns deja livres et des surfaces existantes du repo.
- Aucun upgrade de dependance ni changement de stack n'est attendu.

### Dev Agent Guardrails

- Ne pas modifier `reason_code`.
- Ne pas modifier l'ordre du pipeline.
- Ne pas recalculer la cause en JS.
- Ne pas recalculer l'etape visible en JS.
- Ne pas introduire de multi-cause.
- Ne pas faire de fallback implicite qui change le sens metier.
- Ne pas faire de faux CTA utilisateur.
- Ne pas exposer `technical_reason_code` comme cause principale.
- Ne pas recreer une nouvelle surface UI.
- Rester compatible avec 6.1 et avec les tests 6.1 existants.

### Guardrail - Deploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom reelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procedure parallele.
- Reference complete modes + cycle valide terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique inchange : `main -> beta -> stable -> Jeedom Market`.

### Project Structure Notes

- Reutiliser la modal diagnostic existante et ses helpers ; ne pas recreer une surface parallele.
- Preserver les champs historiques du contrat diagnostic.
- Si un helper pur additionnel est introduit, le placer au plus pres du diagnostic backend existant.
- Le clone courant peut contenir d'autres changements ; ne pas reverter de modifications non liees a la story.

### Project Context Reference

- `_bmad-output/project-context.md` s'applique en entier a cette story.
- Respecter les regles projet daemon / PHP / JS / tests / deploiement terrain deja documentees.

## References

- `_bmad-output/planning-artifacts/epics-projection-engine.md`
  - Epic 6
  - FR31, FR32, FR33, FR34, FR35
  - Story 6.1
  - Story 6.3 (decoupage initial du chantier cause_label / cause_action)
- `_bmad-output/planning-artifacts/prd.md`
  - FR31 a FR35
  - FR44
- `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md`
  - section "Pour la story Diagnostic explicable (Feature 6, FR32/FR44)"
  - clarification etape 4 = arbitrage publication uniquement
- `_bmad-output/planning-artifacts/architecture-projection-engine.md`
  - contrat dual `reason_code` / `cause_code`
  - D8 diagnostic etendu
  - `reason_code -> cause_label`
- `_bmad-output/planning-artifacts/pipeline-contract.md`
  - regle globale 2
  - regle globale 9
  - invariant I7
- `_bmad-output/implementation-artifacts/6-1-diagnostic-par-etape-de-pipeline-l-utilisateur-consulte-pour-chaque-equipement-l-etape-de-blocage-et-la-cause-principale-canonique-unique-ordonnee-par-pipeline.md`
  - gate terrain 2026-04-21
  - observation UX step 3 vs step 4
  - completion notes et fichiers touches
- `_bmad-output/implementation-artifacts/5-2-resultat-de-publication-tracable-le-resultat-technique-est-enregistre-separement-de-la-decision-produit-et-ne-masque-pas-la-cause-principale-canonique.md`
  - separation decision / technique deja livree
  - correctifs I7
- `_bmad-output/implementation-artifacts/pe-epic-5-document-precedence.md`
  - regle de precedence opposable du cycle PE
- `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md`
  - principe : diagnostic actionnable, explication + action simple
- `resources/daemon/models/cause_mapping.py`
  - socle actuel de traduction `reason_code -> cause`
- `resources/daemon/transport/http_server.py`
  - construction actuelle de `cause_label`, `cause_action`, `traceability`, `pipeline_step_visible`
- `desktop/js/jeedom2ha_diagnostic_helpers.js`
  - lecture stricte backend de `cause_label`, `cause_action`, cause canonique

## Gate Terrain

Gate terrain **bloquant avant `done`** :

- valider la comprehension reelle sur box Jeedom ;
- couvrir au minimum un cas `step 2`, un cas `step 3`, un cas `step 4` ;
- verifier que `step 3` et `step 4` ne se distinguent plus uniquement par le stepper ;
- verifier que l'action visible est comprise sans lire de log technique ;
- consigner dans la story :
  - date,
  - environnement,
  - cas / `eq_id` observes,
  - verdict,
  - niveau de preuve et limites explicites.

### Verdict terrain du 2026-04-21

- Verdict global : **NO-GO**
- `step 3` : KO — cause non claire, action non comprise, comprehension > 60 s
- `step 4` : partiel / KO actionnable — la decision est percue, l'action reste floue
- `step 2` : partiel / KO actionnable — lecture rapide, mais incoherence percue entre "non supporte V1" et la promesse d'ouverture explicable
- Decision de gate : arret du gate terrain ; story conservee `in-progress` ; correct-course formel requis avant toute suite

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex CLI)

### Debug Log References

- `./scripts/deploy-to-box.sh --dry-run` : OK (`SSH OK | sudo OK`, mode `DRY-RUN`, simulation rsync terminee)
- `python3 -m pytest` : 969 passed
- `node --test tests/unit/*.node.test.js` : 193 passed
- `python3 -m pytest resources/daemon/tests/unit/test_story_6_2_contextual_cause_mapping.py resources/daemon/tests/unit/test_story_6_1_pipeline_step_diagnostic.py resources/daemon/tests/unit/test_cause_mapping.py tests/unit/test_story_3_2_reason_labels_sync.py` : 50 passed
- `node --test tests/unit/test_story_6_2_frontend_backend_first.node.test.js tests/unit/test_story_6_1_pipeline_step.node.test.js tests/unit/test_story_4_2_diagnostic_decision.node.test.js` : 23 passed

### Completion Notes List

- ✅ Mapping UX contextuel ajoute dans `cause_mapping.py` avec distinction explicite `step 3` / `step 4` pour `ambiguous(_skipped)`.
- ✅ Nouvelle fonction pure `resolve_cause_ux(reason_code, pipeline_step)` introduite avec fallback explicite non-null.
- ✅ Construction du diagnostic backend recablee pour produire `cause_label` / `cause_action` depuis `decision_trace.reason_code + pipeline_step_visible`.
- ✅ Frontend passe en lecture stricte backend pour cause/action (suppression du mapping JS local des reasons et du fallback remediation).
- ✅ Non-regression validee par la suite complete `pytest` (969 tests) et la suite complete Node (`193` tests).
- ⚠️ Gate terrain UX reel execute hors de cette session le `2026-04-21` avec verdict **NO-GO** ; story conservee `in-progress` et re-routage approuve vers un correct-course puis vers la story 6.3 pour la semantique honnete.

### File List

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/models/cause_mapping.py`
- `resources/daemon/transport/http_server.py`
- `desktop/js/jeedom2ha.js`
- `desktop/js/jeedom2ha_diagnostic_helpers.js`
- `resources/daemon/tests/unit/test_story_6_2_contextual_cause_mapping.py`
- `tests/unit/test_story_6_2_frontend_backend_first.node.test.js`
- `tests/unit/test_story_3_2_reason_labels_sync.py`
- `tests/unit/test_story_4_2_diagnostic_decision.node.test.js`
- `_bmad-output/implementation-artifacts/6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger.md`

## Change Log

- **2026-04-21** : creation de la story 6.2 en `ready-for-dev`
  - story creee depuis le brief PO post-gate terrain 6.1
  - priorite explicite donnee a la clarification UX `cause_label / cause_action`
  - tracker d'execution a realigner sur ce slug
- **2026-04-21** : implementation story 6.2 (backend-first) en `in-progress`
  - ajout du mapping UX contextuel `reason_code + pipeline_step -> cause_label/cause_action`
  - integration backend dans `http_server.py` sans modification du pipeline 1->5
  - suppression du mapping local JS des causes (lecture backend stricte)
  - ajout des suites de tests story 6.2 (backend + frontend) et execution de la regression complete
  - gate terrain UX reel (Task 5) restant a executer avant `done`
- **2026-04-21** : gate terrain reel execute -> **NO-GO**
  - `step 3` non compris en lecture reelle ; action non actionnable
  - `step 4` partiellement compris ; action jugee floue
  - `step 2` percu comme incoherent avec la promesse d'ouverture explicable
  - correct-course approuve : 6.2 reste `in-progress`, aucun dev supplementaire ne repart depuis cette story, 6.3 devient la prochaine story requise
- **2026-04-22** : correct-course approuve pour implementation
  - la story devient un artefact historique re-home vers `pe-epic-7`
  - aucun developpement supplementaire ne repart depuis ce fichier
  - `projection_validity` redevient la premiere capacite structurelle a traiter dans Epic 7
