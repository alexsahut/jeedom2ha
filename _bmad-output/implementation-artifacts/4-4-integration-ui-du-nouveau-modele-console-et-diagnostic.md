# Story 4.4 : Intégration UI du nouveau modèle (console + diagnostic)

Status: done

## Story

En tant qu'utilisateur de la console V1.1,  
je veux que l'interface affiche fidèlement le modèle 4 dimensions et les compteurs fournis par le backend,  
afin que la lecture soit cohérente entre la console, le diagnostic et l'export support.

## Contexte / Objectif produit

Cette story clôt l'intégration UX du recadrage Epic 4 en faisant de l'UI une lecture **native 4D** :
`perimetre` → `statut` (binaire) → `ecart` → `cause_label` / `cause_action`.

Point de départ réel (verrouillé) avant ouverture de 4.4 :

- Story 4.1 : `done` (contrat backend 4D stabilisé en production de payload).
- Story 4.2 : `done` (vocabulaire d'exclusion par source et compteurs `Total/Inclus/Exclus/Écarts` stabilisés).
- Story 4.3 : `done` avec **candidat figé et traçable** (`8c57808d9fe2b1ae00db0cc7bbd9cd16ab4a9752`) et merge effectif sur `main` via PR #57.

Constats terrain à capitaliser (non renégociables) :

1. Vocabulaire d'exclusion par source validé.
2. Visibilité des exclus validée.
3. Compteurs `Total / Inclus / Exclus / Écarts` validés.
4. Confiance absente de la console principale validée.
5. Confiance visible en diagnostic technique détaillé validée.
6. `Partiellement publié` absorbé comme statut principal validé.
7. Détail de couverture partielle (commandes mappées/non mappées) validé et conservé.
8. Distinction visuelle console vs diagnostic encore perfectible : 4.4 est la story dédiée à ce réalignement UI.

Réduction de dette support portée par 4.4 :

- supprime la narration métier principale basée sur des libellés legacy frontend ;
- élimine la dérive d'interprétation locale ;
- aligne explicitement la lecture console, diagnostic utilisateur, diagnostic technique et export support.

## Scope

### In scope

1. Intégration UI complète du modèle 4D au niveau équipement dans la console.
2. Lecture pièce/global exclusivement par compteurs backend (`Total`, `Inclus`, `Exclus`, `Écarts`).
3. Suppression de la dépendance fonctionnelle principale à `getAggregatedStatusLabel` pour raconter le métier.
4. Affichage de `cause_label` / `cause_action` uniquement quand pertinent (`ecart = true`).
5. Cohérence de taxonomie entre console et diagnostic (même base 4D, détails techniques ajoutés côté diagnostic technique seulement).
6. Maintien de la visibilité des exclus en console sans diagnostic utilisateur détaillé hors-scope.
7. Passage en lecture stricte backend (pas de recalcul local `statut`, `ecart`, `cause`, `compteurs`).
8. Couverture de test story-level incluant non-régression explicite des acquis 4.2/4.3.
9. **Export support IN SCOPE en mode cohérence contractuelle uniquement** : vérification de cohérence 4D entre surfaces, sans évolution fonctionnelle du payload export.

### Out of scope

| Élément hors scope | Responsable |
|---|---|
| Extension fonctionnelle au-delà du recadrage UX Epic 4 | Epic 5+ |
| Refonte backend du contrat 4D | Story 4.1 (figée) |
| Refonte resolver `inherit/include/exclude` | Epic 1 (figé) |
| Repositionnement de la confiance en console principale | Interdit (décision produit figée) |
| Réintroduction de `Partiellement publié` comme statut principal | Interdit (décision produit figée) |
| Ajout de nouveaux champs backend obligatoires si le contrat 4D actuel suffit | Hors scope 4.4 |
| Modification fonctionnelle de l'export support (allowlist, structure, résumé) | Hors scope 4.4 (vérification uniquement) |
| Refonte des opérations HA (`Republier`, `Supprimer/Recréer`) | Epic 5 |

## Dépendances autorisées

- **Story 4.1** — `done` : contrat backend 4D et compteurs backend pré-calculés.
- **Story 4.2** — `done` : vocabulaire d'exclusion par source, disparition de `Exceptions`.
- **Story 4.3** — `review` : filtrage diagnostic in-scope, confiance limitée au diagnostic technique, absorption de `Partiellement publié`.

Aucune dépendance en avant.

## Précondition d'exécution / base de référence

Décision d'exécution : **4.4 peut démarrer sur le candidat 4.3 figé** (`8c57808d9fe2b1ae00db0cc7bbd9cd16ab4a9752`), sans attendre le merge formel de 4.3.

Règles obligatoires :

1. La baseline fonctionnelle 4.3 est réputée figée pour le développement 4.4 (filtrage in-scope, confiance en diagnostic technique uniquement, absorption de `Partiellement publié`).
2. Le dev 4.4 n'est pas autorisé à réinterpréter, corriger ou étendre fonctionnellement la story 4.3.
3. Si l'état mergé final de 4.3 diverge fonctionnellement du candidat figé, 4.4 est mise en pause pour réalignement explicite SM/PO (pas d'arbitrage implicite côté dev).

## Inputs verrouillés du gate 4.2 / 4.3

1. Le vocabulaire source d'exclusion validé ne régresse pas.
2. Les compteurs validés ne régressent pas.
3. La confiance ne fuit jamais en console principale.
4. Le détail de couverture partielle reste consultable.
5. La séparation visuelle console / diagnostic devient plus claire sans casser les acquis.
6. Le marqueur technique `(partiel)` (ou équivalent) ne redevient jamais un pseudo-statut principal.

## Contrat de surfaces UI (normatif et testable)

| Surface | Population | Champs obligatoires | Champs optionnels | Champs interdits |
|---|---|---|---|---|
| Console principale | Tous les équipements | `perimetre`, `statut` (binaire), `ecart`, compteurs `Total/Inclus/Exclus/Écarts` | `cause_label`, `cause_action` uniquement si `ecart=true` | `confidence`, `reason_code`, détail couverture partielle (`matched_commands`/`unmatched_commands`), statuts legacy dominants (`Ambigu`, `Non supporté`, `Partiellement publié`) |
| Diagnostic utilisateur | In-scope uniquement (`perimetre=inclus`) | même base 4D que console (`perimetre`, `statut`, `ecart`, cause si `ecart=true`) | `cause_action` si présente | `confidence`, `reason_code`, détails techniques de couverture partielle |
| Diagnostic technique détaillé | In-scope uniquement (`perimetre=inclus`) | base 4D + `confidence` + détails techniques (`reason_code`, couverture partielle via commandes) | détails techniques additionnels (`status_code`, `detail`, `remediation`, `v1_limitation`) | contradiction avec la lecture 4D principale |
| Export support | Tous les équipements | contrat export existant (4D + champs techniques) inchangé et cohérent avec la taxonomie 4D | champs techniques déjà existants | libellés UI legacy injectés comme statut principal, divergence sémantique avec 4D |

Règles transverses :

1. Les exclus sont visibles en console avec leur source d'exclusion.
2. Les exclus ne produisent pas de diagnostic utilisateur détaillé ni de diagnostic technique détaillé in-scope.
3. La confiance n'apparaît jamais en console principale.
4. Le détail de couverture partielle n'apparaît jamais comme statut principal ; il reste technique (diagnostic technique + export).

## Acceptance Criteria

### AC 1 — Lecture 4D native en console (équipement in-scope)

**Given** la console V1.1 au niveau équipement  
**When** un équipement in-scope est affiché  
**Then** il présente les 4 dimensions :
- périmètre
- statut binaire
- indicateur d'écart
- cause métier (si écart)

### AC 2 — Exclu visible mais hors diagnostic utilisateur détaillé

**Given** un équipement exclu  
**When** il est affiché dans la console  
**Then** il reste visible  
**And** son périmètre est exprimé par sa source d'exclusion  
**And** il n'affiche pas un diagnostic utilisateur détaillé hors-scope

### AC 3 — Compteurs strictement canoniques

**Given** les compteurs par pièce ou globaux  
**When** ils sont affichés  
**Then** le compteur `Exceptions` n'existe pas  
**And** les compteurs sont strictement :
- `Total`
- `Inclus`
- `Exclus`
- `Écarts`

### AC 4 — Frontend en lecture stricte du backend

**Given** la console et le diagnostic  
**When** le frontend affiche les données backend  
**Then** il ne recalcule ni statut, ni écart, ni cause, ni compteurs  
**And** il se contente d'afficher le contrat backend fourni

### AC 5 — Cause visible si et seulement si écart

**Given** un équipement avec `ecart = true`  
**When** il est affiché  
**Then** la cause métier associée est visible  
**And** l'interface rend lisible qu'il existe un désalignement à traiter

### AC 6 — Lecture sobre sans écart

**Given** un équipement sans écart  
**When** il est affiché  
**Then** la lecture reste sobre  
**And** la cause n'est pas artificiellement affichée

### AC 7 — Sortie des statuts legacy comme statut principal

**Given** un équipement historiquement couvert par les anciens libellés (`Ambigu`, `Non supporté`, `Partiellement publié`)  
**When** il est affiché dans la nouvelle UI 4D  
**Then** la lecture principale repose sur le modèle 4D  
**And** ces anciens libellés ne sont plus utilisés comme statuts principaux de console

### AC 8 — Cohérence console / diagnostic technique détaillé

**Given** le diagnostic technique détaillé  
**When** il est affiché pour un équipement in-scope  
**Then** il reste cohérent avec la console  
**And** il peut afficher les informations techniques autorisées (comme la confiance et les détails de couverture)  
**And** il ne contredit jamais la lecture 4D principale

### AC 9 — Wording backend reflété sans sémantique locale parallèle

**Given** un changement de wording ou de cause côté backend  
**When** le contrat API évolue dans son wording métier  
**Then** l'UI le reflète sans logique sémantique parallèle locale

### AC 10 — Export support cohérent (in scope vérification, sans évolution fonctionnelle)

**Given** l'export support existant (stabilisé avant 4.4)  
**When** la story 4.4 est livrée  
**Then** l'export conserve son contrat fonctionnel inchangé  
**And** sa lecture reste cohérente avec la taxonomie 4D affichée par la console et le diagnostic  
**And** aucun libellé legacy de statut principal n'est réintroduit via la chaîne d'export

## Tasks / Subtasks

- [x] Task 1 — Modèle UI : consommer explicitement les champs 4D (AC: 1, 4, 5, 6, 9)
  - [x] 1.1 Dans `desktop/js/jeedom2ha_scope_summary.js`, enrichir `buildEquipmentModel()` pour exposer explicitement `perimetre`, `statut`, `ecart`, `cause_label`, `cause_action` depuis `diagnostic_equipments[eq_id]` (lecture seule).
  - [x] 1.2 Ne pas dériver ces champs depuis `status_code`, `reason_code` ou `effective_state` (interdiction de mapping local).
  - [x] 1.3 Ajouter un fallback de robustesse UI non-sémantique (ex: valeur vide / inconnu) si un champ 4D manque, sans recomposition locale.

- [x] Task 2 — Console principale : rendre la lecture métier en 4D natif (AC: 1, 2, 5, 6, 7)
  - [x] 2.1 Remplacer la narration principale basée sur `getAggregatedStatusLabel(equipement.status_code)` au niveau ligne équipement par un rendu structuré 4D.
  - [x] 2.2 Rendre l'écart avec un signal visuel lisible mais sobre (`ecart=true` mis en évidence, `ecart=false` neutre).
  - [x] 2.3 Afficher `cause_label` (et `cause_action` si disponible) uniquement si `ecart=true`.
  - [x] 2.4 Conserver la visibilité des exclus avec source d'exclusion, sans diagnostic utilisateur détaillé pour les exclus.

- [x] Task 3 — Pièce / global : supprimer la lecture dominante legacy au profit des compteurs 4D (AC: 3, 4, 7)
  - [x] 3.1 Garder la lecture principale pièce/global strictement sur `Total/Inclus/Exclus/Écarts` issus de `diagnostic_summary.compteurs` et `diagnostic_rooms[*].compteurs`.
  - [x] 3.2 Retirer du niveau principal les badges/agrégations legacy qui portent `Ambigu`, `Non supporté` ou `Partiellement publié` comme statut de lecture.
  - [x] 3.3 Vérifier l'absence du libellé `Exceptions` dans le rendu final.

- [x] Task 4 — Clarifier visuellement les 3 surfaces UI (console / diagnostic utilisateur / diagnostic technique) (AC: 2, 8)
  - [x] 4.1 Dans `renderPieceEquipements()`, introduire une séparation explicite entre :
    - lecture principale console (4D),
    - diagnostic utilisateur (in-scope),
    - diagnostic technique détaillé (in-scope, détails techniques autorisés).
  - [x] 4.2 Maintenir la règle produit : `confidence` visible uniquement en diagnostic technique détaillé.
  - [x] 4.3 Garder le détail de couverture partielle accessible uniquement en diagnostic technique/export (pas comme statut principal).

- [x] Task 5 — Désengager la narration principale de `getAggregatedStatusLabel` (AC: 4, 7)
  - [x] 5.1 Vérifier que `getAggregatedStatusLabel` n'est plus utilisé pour la lecture métier principale de la console.
  - [x] 5.2 Si la fonction est conservée pour compatibilité technique, la limiter à un usage secondaire non dominant (jamais statut principal console).
  - [x] 5.3 Vérifier que `renderEquipmentState` ne redevient pas la source principale de sens métier (lecture principale = 4D backend).

- [x] Task 6 — Tests unitaires JS dédiés Story 4.4 (AC: 1 à 9)
  - [x] 6.1 Créer `tests/unit/test_story_4_4_integration_ui_4d.node.test.js` avec au minimum :
    - rendu 4D complet pour un in-scope ;
    - exclus visibles + pas de diagnostic utilisateur détaillé ;
    - compteur `Exceptions` absent, compteurs canoniques présents ;
    - `ecart=true` affiche cause, `ecart=false` masque cause ;
    - anciens libellés non dominants dans la console ;
    - cohérence console vs diagnostic technique ;
    - confiance absente console / présente diagnostic technique ;
    - passthrough d'un `cause_label` backend modifié sans reformulation locale.
  - [x] 6.2 Mettre à jour si nécessaire les tests existants impactés :
    - `tests/unit/test_scope_summary_presenter.node.test.js`
    - `tests/unit/test_story_4_2_vocab_exclusion.node.test.js`
    - `tests/unit/test_story_4_3_diagnostic_in_scope.node.test.js`
    - `tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js`

- [x] Task 7 — Vérifications contractuelles et non-régression cross-story (AC: 3, 4, 8, 9)
  - [x] 7.1 Vérifier qu'aucun nouveau champ backend obligatoire n'est requis pour livrer 4.4.
  - [x] 7.2 Exécuter les suites minimales :
    - `node --test tests/unit/*.node.test.js`
    - `python3 -m pytest resources/daemon/tests/unit/test_ui_contract_4d.py resources/daemon/tests/unit/test_story_4_3_diagnostic_in_scope.py`
  - [x] 7.3 Vérifier explicitement la non-régression des acquis terrain 4.2/4.3.

- [x] Task 8 — Export support : contrôle de cohérence contractuelle (AC: 10)
  - [x] 8.1 Ajouter un test dédié `tests/test_php_export_diagnostic_coherence.php` (ou équivalent dans la stack de tests existante) qui vérifie que l'export reste aligné sur la taxonomie 4D après intégration UI 4.4.
  - [x] 8.2 Vérifier explicitement que l'export ne réintroduit pas de statut principal legacy (`Ambigu`, `Non supporté`, `Partiellement publié`) dans la lecture métier principale.
  - [x] 8.3 Exécuter le test export dédié dans la gate 4.4 (`php tests/test_php_export_diagnostic_coherence.php`) et documenter le résultat.

## Dev Notes

### Décisions d'architecture / design à appliquer

1. Le modèle principal de lecture est **4D natif** ; l'UI ne doit plus raconter l'état métier via les codes legacy.
2. Le backend reste la source unique de `statut`, `ecart`, `cause`, `compteurs`.
3. `reason_code` reste un détail technique support/export ; il ne pilote pas la lecture principale console.
4. La confiance reste uniquement en diagnostic technique détaillé.
5. `Partiellement publié` reste absorbé comme statut principal ; la couverture partielle reste un détail technique.

### Statut de l'export support (décision tranchée)

1. L'export support est **IN SCOPE de 4.4 uniquement en vérification de cohérence**.
2. 4.4 ne modifie pas fonctionnellement le contrat export (pas de nouveau champ, pas de changement d'allowlist, pas de changement de résumé).
3. 4.4 exige une preuve testée que l'export reste aligné avec la lecture 4D de la console/diagnostic.

### Points de vigilance challengés et décisions retenues

1. **Remplacement de `getAggregatedStatusLabel` dans la lecture principale**  
Décision : oui, la lecture principale console bascule en 4D natif ; `getAggregatedStatusLabel` ne doit plus être la narration métier dominante.

2. **Affichage visuel de `ecart` sans alourdir la console**  
Décision : signal compact binaire (aligné / écart à traiter), sans multiplier les badges concurrents.

3. **Affichage de la cause uniquement quand pertinente**  
Décision : `cause_label` / `cause_action` visibles uniquement si `ecart=true`.

4. **Séparation console vs diagnostic sans dupliquer l'information**  
Décision : base 4D identique ; le diagnostic technique ajoute uniquement les détails autorisés.

5. **Couverture de non-régression 4.2/4.3**  
Décision : tests dédiés 4.4 + maintien des suites 4.2/4.3 existantes.

6. **Nouveaux champs backend nécessaires ?**  
Décision : non par défaut ; le contrat 4D actuel suffit pour 4.4.

7. **Risque de dominance des concepts legacy**  
Décision : bannir les anciens statuts comme lecture principale de console.

### Impact backend vs frontend

| Couche | Impact attendu Story 4.4 | Fichiers principaux |
|---|---|---|
| Backend Python | Aucun changement contractuel obligatoire ; contrat 4D existant consommé tel quel | `resources/daemon/transport/http_server.py` (vérification uniquement si besoin) |
| Frontend JS | Intégration UI 4D native + séparation claire des surfaces + retrait narration principale legacy | `desktop/js/jeedom2ha_scope_summary.js` |
| Export PHP | In scope vérification : cohérence 4D obligatoire sans modification fonctionnelle du contrat export | `core/ajax/jeedom2ha.ajax.php`, `tests/test_php_export_diagnostic_coherence.php` |
| Tests JS | Nouveaux tests Story 4.4 + ajustements non-régression | `tests/unit/` |
| Tests Python | Vérification contractuelle de stabilité 4D / in-scope | `resources/daemon/tests/unit/` |

### Fichiers à ne pas toucher sauf blocage avéré

- `resources/daemon/models/cause_mapping.py` (table reason→cause figée Story 4.1)
- `resources/daemon/models/taxonomy.py` (socle Epic 3 figé)
- `resources/daemon/models/aggregation.py` (socle Epic 3 figé)
- `resources/daemon/models/published_scope.py` (socle Epic 1 figé)

### Usages résiduels de la narration legacy (autorisé / interdit)

Usages résiduels autorisés :

1. `getAggregatedStatusLabel` peut subsister comme helper de compatibilité technique ou fallback dégradé, tant qu'il n'est pas la lecture métier principale.
2. Les labels legacy peuvent subsister dans des tests de non-régression historiques (Story 3.4) tant qu'ils ne pilotent pas le rendu principal 4D.

Usages résiduels interdits :

1. Utiliser `getAggregatedStatusLabel` pour le statut principal d'un équipement dans la console.
2. Utiliser des agrégations legacy comme lecture dominante pièce/global.
3. Dériver `statut`, `ecart`, `cause` depuis `status_code` ou `reason_code`.
4. Réintroduire `Ambigu`, `Non supporté` ou `Partiellement publié` comme statuts principaux de lecture console.

## Stratégie de test story-level

### Invariants V1.1 touchés

| Invariant | Référence | Couvert par |
|---|---|---|
| I10 — Contrat 4D unique backend → UI | test-strategy §4 | AC 1, 4, 9 |
| I11 — Statut binaire au niveau équipement uniquement | test-strategy §4 | AC 1, 7 |
| I12 — Compteurs pièce/global backend `Total=Inclus+Exclus` | test-strategy §4 | AC 3, 4, 10 |
| I14 — Diagnostic utilisateur filtré in-scope | test-strategy §4 | AC 2, 8 |
| I15 — Confiance hors console principale | test-strategy §4 | AC 8 |
| I16 — Étanchéité reason_code / cause_code | test-strategy §4 | AC 4, 8, 9, 10 |
| I17 — Frontend en lecture seule | test-strategy §4 | AC 4, 9 |
| I18 — Disparition des termes interdits en UI | test-strategy §4 | AC 3, 7 |

### Tests unitaires obligatoires

- Vérifier le rendu 4D natif à partir des champs backend (`perimetre`, `statut`, `ecart`, `cause_label`, `cause_action`).
- Vérifier que `cause_label`/`cause_action` n'apparaissent pas quand `ecart=false`.
- Vérifier que les équipements exclus restent visibles mais sans diagnostic utilisateur détaillé.
- Vérifier l'absence de `Exceptions` et la présence des 4 compteurs canoniques.
- Vérifier que la confiance n'apparaît pas en console principale.
- Vérifier le passthrough strict d'un wording backend modifié.

### Tests d'intégration / contrat obligatoires

- Vérifier que le frontend ne dépend pas d'un recalcul local (cas injectés où `status_code` legacy contredit volontairement le 4D : l'UI suit le 4D).
- Vérifier la cohérence de lecture console/diagnostic pour un même équipement.
- Vérifier la non-régression du filtrage in-scope fourni par Story 4.3.
- Vérifier la cohérence de l'export support avec la taxonomie 4D, sans évolution fonctionnelle du contrat export.

### Tests de séparation des surfaces (obligatoires)

1. Console principale : `confidence` absente, détails de couverture partielle absents, cause uniquement si `ecart=true`.
2. Diagnostic utilisateur : base 4D présente, `confidence` absente.
3. Diagnostic technique détaillé : `confidence` + détails techniques présents pour les in-scope.
4. Exclus : visibles en console, absents des surfaces diagnostic détaillées in-scope.
5. Export support : conserve sa population exhaustive et son contrat technique existant.

### Non-régression obligatoire

- Suites JS existantes Story 4.2 / 4.3 / 3.4 passent après intégration 4.4.
- Suites Python contractuelles 4.1/4.3 restent vertes.
- Test export dédié `php tests/test_php_export_diagnostic_coherence.php` vert.
- Aucun retour en arrière sur les validations gate 4.2/4.3.

## Guardrails anti-dérive

1. Pas de dérive vers Epic 5.
2. Pas d'extension fonctionnelle.
3. Pas de refonte backend générale.
4. Pas de remise en cause du contrat 4D.
5. Pas de recalcul frontend.
6. Pas de réouverture du débat sur la confiance en console.
7. Pas de réouverture du débat sur `Partiellement publié` statut principal.
8. Les exclus restent visibles en console mais hors diagnostic utilisateur détaillé.
9. Le récit métier principal ne dépend plus de `getAggregatedStatusLabel`.
10. Export support : cohérence obligatoire, évolution fonctionnelle interdite dans 4.4.

## Définition de done story-level

- [x] AC 1 à AC 10 validés par tests automatisés.
- [x] Lecture principale console passée en 4D natif backend.
- [x] `getAggregatedStatusLabel` non dominant pour la lecture métier principale.
- [x] Compteurs stricts `Total/Inclus/Exclus/Écarts`, sans `Exceptions`.
- [x] Confiance visible uniquement en diagnostic technique détaillé.
- [x] `Partiellement publié` non utilisé comme statut principal de console.
- [x] Export support cohérent avec la taxonomie 4D, sans modification fonctionnelle du contrat export.
- [x] Non-régression 4.2/4.3 confirmée.
- [x] Code review PASS.

## References

- `_bmad-output/planning-artifacts/active-cycle-manifest.md`
- `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md`
- `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md`
- `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md`
- `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md` (Story 4.4 + matrice dépendances)
- `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-1-contrat-backend-du-modele-perimetre-statut-ecart-cause.md`
- `_bmad-output/implementation-artifacts/4-2-vocabulaire-d-exclusion-par-source-disparition-du-concept-exception.md`
- `_bmad-output/implementation-artifacts/4-3-diagnostic-centre-in-scope-confiance-en-diagnostic-uniquement-traitement-de-partiellement-publie.md`

## Change Log

- 2026-03-29 — Implémentation Story 4.4 : lecture UI 4D native, séparation explicite console/diagnostic utilisateur/diagnostic technique, retrait des badges legacy dominants pièce/global, test JS story-level 4.4, ajustements des non-régressions 3.4/4.2/4.3, ajout du test PHP de cohérence export 4D.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `node --test tests/unit/test_story_4_4_integration_ui_4d.node.test.js` (RED puis GREEN)
- `node --test tests/unit/test_scope_summary_presenter.node.test.js tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js tests/unit/test_story_4_2_vocab_exclusion.node.test.js tests/unit/test_story_4_3_diagnostic_in_scope.node.test.js tests/unit/test_story_4_4_integration_ui_4d.node.test.js`
- `node --test tests/unit/*.node.test.js`
- `python3 -m pytest resources/daemon/tests/unit/test_ui_contract_4d.py resources/daemon/tests/unit/test_story_4_3_diagnostic_in_scope.py`
- `php tests/test_php_export_diagnostic_coherence.php`

### Completion Notes List

- `buildEquipmentModel()` consomme explicitement le contrat 4D backend (`perimetre`, `statut`, `ecart`, `cause_label`, `cause_action`) sans dérivation locale depuis `status_code`/`reason_code`/`effective_state`.
- La narration principale console est passée en lecture 4D native; les niveaux global/pièce restent pilotés par `Total/Inclus/Exclus/Écarts` backend.
- Les surfaces sont explicitement séparées dans `renderPieceEquipements()` : console principale (tous), diagnostic utilisateur (in-scope), diagnostic technique détaillé (in-scope).
- `confidence` reste visible uniquement en diagnostic technique détaillé; la console principale n’affiche ni confiance ni statuts legacy dominants.
- Le passthrough PHP `getPublishedScopeForConsole` inclut désormais les champs 4D existants côté backend, sans création de nouveau contrat obligatoire.
- Test story-level ajouté (`test_story_4_4_integration_ui_4d.node.test.js`) + adaptations des suites impactées (`scope_summary_presenter`, `story_3_4_ai5_frontend_passthrough`).
- Cohérence export validée via `tests/test_php_export_diagnostic_coherence.php` et exécution verte.

### File List

- `_bmad-output/implementation-artifacts/4-4-integration-ui-du-nouveau-modele-console-et-diagnostic.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `desktop/js/jeedom2ha_scope_summary.js`
- `core/ajax/jeedom2ha.ajax.php`
- `tests/unit/test_story_4_4_integration_ui_4d.node.test.js`
- `tests/unit/test_scope_summary_presenter.node.test.js`
- `tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js`
- `tests/test_php_export_diagnostic_coherence.php`
