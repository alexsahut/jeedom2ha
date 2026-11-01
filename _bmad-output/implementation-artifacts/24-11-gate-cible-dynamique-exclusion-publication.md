# Story 24.11 : gate 20-0, cible choisie à l'exécution pour `exclusion-publication-non-publiee`

Status: done

> Créée par ClaudeBox le 2026-11-01. Décision d'Alexandre (01/11 à 09:55) : option **b**, le parcours choisit lui-même son équipement. Rattachée à l'epic 24 parce qu'elle conditionne les preuves de gate de ses stories (24.4 et suivantes). Taille : S/M. Elle touche le cadre de sûreté du gate : relecture ClaudeBox obligatoire.

## Constat

Le parcours `tests/e2e/gate/parcours/exclusion-publication-non-publiee.mjs` est codé sur l'**eq 287**. Il exige un équipement **non publié**, **sans réglage de publication enregistré**, à **une seule entité** et avec **au moins une commande**.

Depuis le 19/10, l'eq 287 porte un réglage de publication sur la box (consigne d'Alexandre : ne pas y toucher). `run-gate.mjs` refuse donc d'exécuter le parcours dès sa précondition (`assertNoOverrideOn` → `override-declare: equipement:287`), sans rien toucher : comportement voulu. Résultat : ce scénario n'est plus vérifié, alors que le gate était vert aux preuves 24.4 du 31/10.

## Story

En tant que mainteneur,
je veux que ce parcours choisisse à l'exécution un équipement qui remplit ses conditions,
afin que le gate reste vérifiable quel que soit l'état réel de la box, sans jamais viser un équipement réglé à la main.

## Conception retenue (à respecter)

1. **Déclaration à l'exécution, bornée.** `run-gate.mjs` fournit au parcours un helper `helpers.declareTarget(eqId)`, utilisable **une seule fois** et **avant** toute écriture interceptée. Ce helper :
   - refuse un `eqId` non numérique ;
   - refuse un `eqId` portant un réglage dans le témoin « avant » (`assertNoOverrideOn(before, [eqId])`) ;
   - ajoute alors `eqId` à `ctx.declaredEquipments` et à `ctx.declaredPublicationOverrides`, avec `{ commands: [] }` comme aujourd'hui ;
   - écrit la cible dans le rapport (`record('cible', eqId)`).

   La politique d'interception (`lib/policy.mjs`) est **inchangée** : seules les écritures d'un équipement déclaré peuvent être simulées, et aucune n'est jamais transmise à la box.
2. **Parcours.** `declaredEquipments` et `declaredPublicationOverrides` deviennent `{}` et le parcours exporte `dynamicTarget = true`. `isValidParcours` accepte `{}` seulement si `dynamicTarget === true`. Le parcours parcourt les cartes de pièce et l'arbre, en lecture seule, jusqu'au premier équipement qui remplit **toutes** ces conditions :
   - ligne non publiée ;
   - position « Automatique » cochée, donc aucun réglage ;
   - aucun en-tête de groupe, donc une seule entité ;
   - au moins une `tr.mapping-override-cmd`.

   Il appelle alors `declareTarget`, puis déroule exactement les étapes actuelles. S'il ne trouve aucun équipement, il échoue explicitement : `aucune-cible-eligible`.
3. **Exclusion permanente.** Le parcours ne retient **jamais** l'eq 287 (liste `EXCLUDED_TARGETS = ['287']`), même sans réglage.
4. **Registre d'assertions.** `tests/fixtures/story_25_4_gate_assertions.json` est mis à jour **explicitement** : les étiquettes et clés `record` propres à 287 sont renommées en version générique (`eq-cible-plusieurs-entites`, `compteurs-eq-cible-illisibles`, `eq_cible_compteur_N`). Aucune assertion n'est retirée et aucune étape ne disparaît.

## Critères d'acceptation

1. **AC1.** Sur la box de production, le parcours choisit une cible ≠ 287, sans réglage, et passe : interception active, 0 écriture transmise, rapport `PASS`.
2. **AC2.** Tests Node du cadre :
   - `declareTarget` refuse un id portant un réglage, un deuxième appel, un appel après une écriture, et un id non numérique ;
   - `isValidParcours` refuse `{}` sans `dynamicTarget` ;
   - la cible apparaît dans le rapport.
3. **AC3.** Tests du parcours sur pages simulées (`test_story_20_3_gate_parcours`) :
   - choix de la première cible éligible ;
   - eq 287 jamais choisi ;
   - échec `aucune-cible-eligible` quand rien n'est éligible.
4. **AC4.** Les autres parcours ne changent pas : registre 25.4 vert, mis à jour uniquement pour les renommages de AC4 de la conception.
5. **AC5.** Preuve : gate 20-0 complet relancé en production par clawcode. Les deux contrôles négatifs restent en échec attendu, tout le reste est vert.

## Garde-fous

- Aucune écriture réelle : la politique et l'intercepteur ne changent pas.
- Aucun nom d'équipement dans le dépôt ni dans le rapport : seulement des ids (CC-48).
- L'eq 287 n'est jamais touché.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée), 2026-11-01.

### Implémentation

- **Lanceur (`run-gate.mjs`), modifié uniquement par ajout** (le test 25.4 interdit toute ligne retirée ou modifiée) :
  - `createDeclareTarget({ before, ctx, journal, record })` fabrique `helpers.declareTarget(eqId)`. Ordre des refus : deuxième appel (`cible-deja-declaree` ; un premier appel refusé consomme aussi le droit), écriture déjà interceptée ou journal en échec (`cible-apres-ecriture`), id non numérique (`cible-id-invalide`, motif `^[1-9][0-9]{0,9}$`, un entier sûr est accepté sous forme décimale), réglage dans le témoin « avant » (`assertNoOverrideOn(before, [eqId])` → `override-declare: …`). Ensuite seulement : `record('cible', eqId)`, puis ajout de l'id à `ctx.declaredEquipments` et `ctx.declaredPublicationOverrides` avec `{ commands: [] }`. Rien d'autre n'est touché (exclusions de pièce, rescan, bascules).
  - « Écriture interceptée » = une entrée de journal au verdict `simulee`, ou portant une action d'écriture ou d'effet de bord de `policy.mjs` (quel que soit le verdict, donc aussi une écriture refusée), ou un journal déjà en échec (`hasInterceptedWrite`, exportée).
  - Un parcours `dynamicTarget === true` part de déclarations neuves et vides propres à l'exécution (`ctx.declaredEquipments = {}` et `ctx.declaredPublicationOverrides = {}` avant l'installation de l'intercepteur) et reçoit seul `declareTarget`. Les autres parcours gardent l'appel d'origine, inchangé (branche `else`).
  - `isValidDynamicTargetDeclaration` : `dynamicTarget` absent, ou exactement `true` avec `declaredEquipments` et `declaredPublicationOverrides` objets simples vides. `isValidParcours` l'appelle en tête.
- **Politique (`lib/policy.mjs`) et intercepteur : inchangés.** Test ajouté : avant déclaration, `savePublicationOverride` sur la cible est `block-fail` ; après, seule la cible est simulée (une autre, et 287, restent `block-fail`).
- **Parcours** : `dynamicTarget = true`, déclarations `{}`, `EXCLUDED_TARGETS = ['287']`. Recherche en lecture seule : pièce connue (objet 25, étapes 1 et 2 conservées) puis toutes les cartes (étapes `3_i` et `4_i`), lignes déjà vues ignorées. Une ligne est candidate si son mot d'état est `blocked` ou `nothing_to_publish` et si elle n'est pas désactivée dans Jeedom ; elle est alors sélectionnée (vrai clic, relecture `getMappingOverrides` autorisée) et retenue si « Automatique » est coché, sans `.j2ha-group-head`, avec au moins une `tr.mapping-override-cmd`. Puis `declareTarget`, puis les étapes 5 à 12 d'origine, sur l'id retenu. Les contrôles d'origine (`eq-introuvable`, `eq-sans-entite`, plusieurs entités, compteurs, modale de confirmation) sont gardés. Aucune cible : `aucune-cible-eligible`.
- **Registre 25.4** : renommages explicites `eq-287-plusieurs-entites` → `eq-cible-plusieurs-entites`, `compteurs-eq-287-illisibles` → `compteurs-eq-cible-illisibles`, `eq_287_compteur_${index + 1}` → `eq_cible_compteur_${index + 1}` ; déclarations passées à `{}` (conception, point 2) ; ajouts : `aucune-cible-eligible` et la déclaration `dynamicTarget: "true"` (le relevé `registryOf` lit maintenant `dynamicTarget`). Aucune étiquette, clé ni étape retirée ; les quatre autres parcours sont inchangés.

### Points à trancher en relecture

1. **AC2, « `isValidParcours` refuse `{}` sans `dynamicTarget` ».** Pris à la lettre, ce refus invaliderait les six parcours en lecture seule qui déclarent légitimement `declaredEquipments = {}` (`decouverte-piece-25-eq-579`, `page-principale-b`, `vue-maitre-detail-c`, `rescan-page-principale`, `exclusion-piece-simulee`, `controle-exclusion-piece-non-declaree`) et casserait les tests 25.3, 25.4 et 25.8, ce que AC4 interdit. Choix retenu, plus strict que l'existant sans rien casser : `{}` reste valide sans `dynamicTarget`, mais un tel parcours ne reçoit jamais `declareTarget` et ne peut donc rien écrire ; à l'inverse, `dynamicTarget` doit valoir exactement `true` et n'est accepté qu'avec des déclarations vides (test : `{}` accompagné de `dynamicTarget` `false`, `'true'`, `1`, `null` ou `{}` est refusé). À confirmer par ClaudeBox ; si le refus littéral est voulu, il faut d'abord décider du sort des parcours en lecture seule.
2. **« Ligne non publiée ».** Interprétée comme mot d'état `Bloqué` ou `Rien à publier` (ligne non désactivée). `À appliquer` est écarté (une exclusion y demande confirmation), comme `Exclu` et `Désactivé` (réglage neutralisé ailleurs ou indisponible). Plus étroit que « tout sauf Publié » : à élargir si la box n'offre aucun candidat.
3. **Pièce connue (objet 25).** Gardée en premier pour ne retirer aucune étape (1 et 2) ; « première cible éligible » s'entend donc : d'abord la pièce 25, puis les cartes dans l'ordre de la page.
4. **`run-gate.mjs` modifié par ajout seulement** : l'appel du parcours dynamique est une branche `if … else` placée devant l'appel d'origine, laissé intact.

### Non démontré ici (hors périmètre cloud)

- AC1 et AC5 : exécution sur la box de production (cible ≠ 287 choisie, interception active, 0 écriture transmise, rapport `PASS`, gate 20-0 complet). À faire par clawcode.
- Le DOM réel de la vue C n'a été simulé que dans `test_story_20_3_gate_parcours` (mots d'état `j2ha-state-*`, classe `j2ha-wv-eq-disabled`, contrôle segmenté) ; l'ordre réel de l'arbre et le temps de rendu du détail (attente bornée à 10 s par candidat, dans le budget de 180 s du parcours) restent à constater sur la box.

### Tests lancés

- `node --test tests/unit/*.node.test.js` : 1211 tests, 1211 verts (deux exécutions complètes). Une première exécution complète a montré 1 échec non reproduit (sortie non conservée) ; les fichiers 20.3 et 24.11, relancés trois fois en parallèle, sont verts.
- `make test-unit` : 792 verts.
- `flake8` : aucun constat.

### Relecture ClaudeBox (2026-11-01)

- Points 1 à 4 ci-dessus : choix de la session acceptés tels quels.
- Revue Codex P2 (#359) : un candidat portant un réglage de commande (type HA forcé) paraissait « Automatique » ; corrigé par `helpers.canDeclareTarget` / `isDeclarableTarget` (lecture seule, témoin « avant »).
- Gate de production : l'eq 598, non éligible, avait son segment « Jamais » désactivé et le clic d'exclusion a expiré ; corrigé par #360 (`b087609`), la recherche exige « Jamais » utilisable.

### Preuve terrain (2026-11-01, clawcode, box de production en `689c5fe`)

- **AC5** — gate 20-0 complet (run `22-4-prod-20261101-r2`, outillage `689c5fe`) : `decouverte-piece-25-eq-579`, `exclusion-piece-simulee`, `page-principale-b`, `rescan-page-principale`, `vue-maitre-detail-c` PASS ; `controle-ecriture-non-declaree` et `controle-exclusion-piece-non-declaree` en échec attendu (`block-fail`) ; `exclusion-publication-non-publiee` en échec (eq 598, voir ci-dessus) ; `reference-bascule-eq-380` en échec sur le témoin seul (troncature du journal du démon, piège connu), toutes ses étapes passées.
- **AC1** — relance r3 sans redéploiement, outillage `b087609` : `exclusion-publication-non-publiee` **PASS**, cible retenue **460** (≠ 287), interception active, aucun refus, aucune écriture transmise, 5/5 contrôles ; `reference-bascule-eq-380` **PASS**.

### File List

- `tests/e2e/gate/run-gate.mjs` (modifié, ajouts uniquement)
- `tests/e2e/gate/parcours/exclusion-publication-non-publiee.mjs` (modifié)
- `tests/fixtures/story_25_4_gate_assertions.json` (modifié : renommages et déclarations)
- `tests/unit/helpers/capture_story_25_4_references.js` (modifié : relevé de `dynamicTarget`)
- `tests/unit/test_story_20_3_gate_parcours.node.test.js` (modifié : AC3)
- `tests/unit/test_story_24_11_gate_cible_dynamique.node.test.js` (nouveau : AC2)
- `_bmad-output/implementation-artifacts/24-11-gate-cible-dynamique-exclusion-publication.md` (statut, Dev Agent Record)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (24-11 → review)
