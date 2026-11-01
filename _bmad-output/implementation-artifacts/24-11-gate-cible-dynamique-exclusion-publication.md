# Story 24.11 : gate 20-0, cible choisie à l'exécution pour `exclusion-publication-non-publiee`

Status: ready-for-dev

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
