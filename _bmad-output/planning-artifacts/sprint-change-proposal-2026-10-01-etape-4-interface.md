# Sprint Change Proposal — 2026-10-01 — Étape 4 : l'interface (epic 20)

## Déclencheur

Clôture de pe-epic-19 (étape 3, contrat de décision unifié `evaluate_equipment()`) le 2026-10-01, confirmée par `pe-epic-19-retro-2026-10-01.md` (7/7 stories `done`, gates epic-level tenus). Le plan d'action d'Alex du 2026-09-26 prévoit ensuite l'étape 4 — l'interface. Résidus actés par la rétrospective, non repris par aucune story existante : CC-25, CC-26 et le volet UI de CC-04. Décision d'Alex du 2026-09-29 08:13 : le clic réel sur la purge d'un override de publication est un critère obligatoire de cette étape.

## Impact

- **CC-25** : les équipements désactivés sont absents de la surface par pièce (le JS sait les rendre ; ils manquent probablement dès `eqLogic::byObjectId($object->getId())` dans `desktop/php/jeedom2ha.php`, qui ne renverrait par défaut que les équipements actifs : à vérifier en 20-1) ; l'état « non couverte » (commande sans mapping) n'est pas rendu dans l'arbre — `normalizeCommandRow` ne transmet pas `covered`. Un correctif distinct (PR #192, `fix/16-8-synthese-non-couverte`) a déjà fermé la part « commande non couverte comptée bloquante dans la synthèse » (AC9-AC10 de 16-8) ; le volet rendu de l'arbre reste ouvert.
- **CC-26** : aucune action UI ni route HTTP ne permet de poser un override de publication (exclusion, forçage). Seule la purge (« Revenir au mode automatique ») existe, prouvée par test, jamais par clic réel.
- **CC-04 (volet UI)** : jargon Jeedom encore visible (« Mes templates », « Paramètre n°1 »…), synthèse « Parc global » et modale diagnostic distinctes de la navigation par pièce — pas de surface unique pièce → équipement → commande.
- **16-8 se termine sans nouveau code, avant 20-1.** Son parcours navigateur réel du 2026-10-01 (`16-8-ac14-validation-2026-10-01.md`) était partiel. Depuis :
  - AC5 est amendé dans la story 16-8 par décision d'Alex (2026-10-01, 16:22) : le diagnostic est chargé à l'ouverture de la pièce, ce que fait déjà le code ;
  - AC9-AC10 est corrigé par la PR #192 (`7a819df`), à déployer ;
  - reste la preuve au clic d'AC14 (bascule d'une commande bloquante en prête), après ce déploiement, puis la validation UX d'Alex.
  Ces écarts restent portés par 16-8, pas par l'epic 20. La fin de 16-8 conditionne seulement le démarrage de 20-1 : une seule implémentation de navigation par pièce existe quand 20-1 la remplace.

## Options considérées

1. **Reprendre 16-8 et fermer ses écarts avant d'ouvrir l'epic 20.** Retenu en partie : il ne reste à 16-8 aucun code à écrire (AC5 amendé, AC9-AC10 corrigé). Sa fin (déploiement, preuve AC14, validation UX) se fait en parallèle de 20-0 et ne bloque que le démarrage de 20-1.
2. **Ouvrir directement la surface unique sans gate de preuve UX outillé.** Rejeté : le plan d'action d'Alex du 2026-09-26 place le gate de preuve UX outillé en tête de l'étape 4 ; le clic réel manuel de l'étape 3 (19-3, 19-6, 16-8) s'est fait sans interception d'écriture.
3. **Gate de preuve UX outillé d'abord (story 20-0), puis la surface unique.** Retenu : une interception par défaut où aucune écriture n'est transmise à la box (toute écriture reçoit une réponse simulée vérifiée ; lectures et aperçus restent réels, sauf simulation déclarée par le parcours) permet des parcours réels répétables, sans risque sur la maison, avant de livrer une interface qui remplace l'existant. Le compte Jeedom dédié n'isole rien (voir « Point à confirmer » ci-dessous) ; l'écriture réelle est prouvée par la preuve terrain de chaque story.

## Recommandation

Ouvrir l'epic 20 avec la story 20-0 (gate de preuve UX outillé) comme préalable bloquant de toute story d'interface suivante. Les stories d'interface ne commencent qu'après 20-0 `done` et 16-8 `done`.

## Découpage proposé en stories

- **20-0 — Gate de preuve UX outillé.** Playwright sur la VM openclaw, compte Jeedom dédié (fourni par Alex), interception par défaut sans aucune écriture transmise à la box (toute écriture, override compris, reçoit une réponse simulée après vérification de sa charge utile ; `data/ha_overrides.json` et le témoin d'activité du démon relevés inchangés avant/après), vérifications minimales avant tout `done` d'interface. Bloquante pour toutes les stories suivantes.
- **20-1 — Surface unique pièce → équipement → commande.** Remplace la navigation par pièce de 16-8 et la synthèse « Parc global » pour l'affichage. Reprend sans régression l'édition du type HA par commande de 16-8 (aperçu, enregistrement automatique, retour au mode automatique) ; l'exclusion et le forçage viennent en 20-2. Selon les décisions d'Alex du 2026-10-01 :
  - diagnostic chargé à l'ouverture de la pièce ;
  - équipements sans pièce regroupés sous une pseudo-pièce « Sans pièce », en fin de liste ;
  - commandes non couvertes visibles, grisées, jamais comptées bloquantes ;
  - équipements désactivés inclus (CC-25).
  Dépend de 20-0 `done` et de 16-8 `done`.
- **20-2 — Exclusion et forçage depuis la surface (CC-26).** Ajoute l'action de poser un override de publication (exclusion, forçage) depuis la surface unique, sur l'équipement et sur la commande (décision d'Alex du 2026-10-01), avec sa purge prouvée par clic réel lors de la preuve terrain de la story (le gate 20-0 ne transmet aucune écriture). Dépend de 20-1.
- **20-3 — Suppression du gabarit Jeedom et libellés français d'usage (CC-04 volet UI).** Supprime la synthèse « Parc global » et la modale diagnostic (décision d'Alex du 2026-10-01), remplace le jargon (« Mes templates », « Paramètre n°1 »…). Dépend de 20-1 et 20-2.
- **20-4 — Rescan sur la page principale (CC-04 volet UI, fin).** Dépend de 20-1.
- **20-5 — Documentation utilisateur réécrite (CC-07 d).** Dépend de 20-1 à 20-4 (décrit l'interface finale, pas une interface intermédiaire).

Ordre de dépendance obligatoire : `20-0` → `20-1` → (`20-2`, `20-4` en parallèle possible) → `20-3` → `20-5`.

## Critères de fin de l'epic

- Une seule surface pièce → équipement → commande fait foi ; la synthèse « Parc global » et la modale diagnostic distinctes n'existent plus.
- CC-25 et CC-26 fermés et prouvés par clic réel (y compris la purge d'un override de publication, décision d'Alex du 2026-09-29).
- CC-04 (volet UI) fermé : aucun jargon Jeedom résiduel, exclusion/forçage/rescan accessibles depuis la surface unique.
- 16-8 `done` avant 20-1 : AC5 amendé par décision d'Alex, AC9-AC10 corrigé, AC14 prouvé au clic, validation UX d'Alex.
- Documentation utilisateur réécrite et alignée sur l'interface livrée.
- Gate 20-0 exécuté et vert avant chaque `done` d'interface de l'epic.

## Décisions d'Alex (2026-10-01, 16:22 et 17:58)

1. **Synthèse « Parc global » et modale diagnostic** : supprimées au profit de la surface unique (story 20-3).
2. **Exclusion et forçage** : sur l'équipement et sur la commande (story 20-2). La pièce reste gérée par la liste d'exclusions de la configuration.
3. **Équipements sans pièce** : regroupés sous une pseudo-pièce « Sans pièce », en fin de liste (story 20-1).
4. **Commandes non couvertes** : visibles, grisées, jamais comptées bloquantes, sans bascule d'affichage (story 20-1).
5. **Chargement du diagnostic** : à l'ouverture de la pièce. AC5 de 16-8 est amendé en ce sens ; 20-1 garde ce comportement.
6. **Playwright et Chromium** : GO d'Alex. Installés par clawcode sous l'utilisateur `asahut` de la VM openclaw, dans `/home/asahut/.openclaw/tools/jeedom2ha-gate` (navigateurs dans `~/.cache/ms-playwright`), sans `sudo` ni dépendance système.
7. **Identifiants du compte dédié `clawcode`** (créé par Alex le 2026-10-01) : fichier `/home/asahut/.config/jeedom2ha-gate/jeedom.env` sur la VM openclaw (dossier en 700, fichier en 600, clés `JEEDOM_USER` et `JEEDOM_PASSWORD`), déposé par Alex lui-même. Le pré-flight ne vérifie que sa présence et ses droits ; le gate le lit à l'exécution sans jamais en afficher le contenu (AC4 de 20-0).

Point à confirmer par Alex : les actions du plugin exigent un compte administrateur (`isConnect('admin')` dans `core/ajax/jeedom2ha.ajax.php` et `desktop/php/jeedom2ha.php`). Le compte `clawcode` doit donc être administrateur. Il n'isole alors rien : la protection repose entièrement sur l'interception de la story 20-0.

## Risques et suivi

- Revue Codex du 2026-10-01 (P1) : le gate ne transmet plus aucune écriture ; les preuves terrain qui écrivent (AC14 de 16-8, purge de 20-2) suivent la règle : équipement non publié, témoin `getBridgeStatus` relevé avant/après, sync correctif (après le retrait de l'override) si le témoin a bougé, jamais d'exclusion d'un équipement publié sans GO d'Alex.
- Défaut latent hors PR : écritures non atomiques de `data/ha_overrides.json` (`resources/daemon/mapping/overrides.py:266/310/430/462`, ouverture en écriture qui tronque le fichier avant de le réécrire ; un sync qui le lit à cet instant calcule sans aucun override) → story/PR séparée.
- AC14 de 16-8 : constat du 2026-10-01 au soir (`16-8-ac14-validation-2026-10-01.md`, « Suite ») : aucune bascule « bloquante → prête » par override TYPE n'est démontrable sur les données réelles (17 commandes couvertes et bloquantes du périmètre inclus, toutes `ambiguous_skipped`). La voie de preuve de la bascule exigée par AC14 (amendement d'AC14, ou preuve par le gate 20-0 en écriture simulée) est à trancher par Alex.

## Notes

- Aucune ouverture `PRODUCT_SCOPE`, aucun nouveau FR/NFR : ce cadrage est documentaire, dans la continuité de pe-epic-19.
- Aucun code, test, script, déploiement ni fusion n'a été modifié par cette unité : documentation seulement.
