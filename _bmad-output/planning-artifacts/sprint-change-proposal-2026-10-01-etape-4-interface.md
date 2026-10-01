# Sprint Change Proposal — 2026-10-01 — Étape 4 : l'interface (epic 20)

## Déclencheur

Clôture de pe-epic-19 (étape 3, contrat de décision unifié `evaluate_equipment()`) le 2026-10-01, confirmée par `pe-epic-19-retro-2026-10-01.md` (7/7 stories `done`, gates epic-level tenus). Le plan d'action d'Alex du 2026-09-26 prévoit ensuite l'étape 4 — l'interface. Résidus actés par la rétrospective, non repris par aucune story existante : CC-25, CC-26 et le volet UI de CC-04. Décision d'Alex du 2026-09-29 08:13 : le clic réel sur la purge d'un override de publication est un critère obligatoire de cette étape.

## Impact

- **CC-25** : les équipements désactivés sont absents de la surface par pièce (`desktop/js/jeedom2ha_mapping_surface.js`) ; l'état « non couverte » (commande sans mapping) n'est pas rendu dans l'arbre — `normalizeCommandRow` ne transmet pas `covered`. Un correctif distinct (PR #192, `fix/16-8-synthese-non-couverte`) a déjà fermé la part « commande non couverte comptée bloquante dans la synthèse » (AC9-AC10 de 16-8) ; le volet rendu de l'arbre reste ouvert.
- **CC-26** : aucune action UI ni route HTTP ne permet de poser un override de publication (exclusion, forçage). Seule la purge (« Revenir au mode automatique ») existe, prouvée par test, jamais par clic réel.
- **CC-04 (volet UI)** : jargon Jeedom encore visible (« Mes templates », « Paramètre n°1 »…), synthèse « Parc global » et modale diagnostic distinctes de la navigation par pièce — pas de surface unique pièce → équipement → commande.
- **16-8 reste `in-progress`** : son parcours navigateur réel du 2026-10-01 (`16-8-ac14-validation-2026-10-01.md`) est partiel — AC5 (diagnostic lu à l'ouverture de la modale au lieu de l'accordéon), AC14 (bascule de la synthèse au clic) restent à reprendre. Ces écarts restent portés par 16-8 ; ils ne sont pas repris par l'epic 20, mais la fin de 16-8 est un prérequis déclaré de la surface unique (une seule implémentation de navigation par pièce doit exister avant de la remplacer).

## Options considérées

1. **Reprendre 16-8 et fermer ses écarts avant d'ouvrir l'epic 20.** Rejeté : 16-8 construit une surface qui sera remplacée par la surface unique de l'épic 20 (synthèse + modale diagnostic supprimées) ; finir ses écarts serait un travail jeté.
2. **Ouvrir directement la surface unique sans gate de preuve UX outillé.** Rejeté : les parcours UI de l'étape 3 (19-3, 19-5, 19-6) ont montré un rendement faible et long du clic réel manuel (ClaudeBox, Claude in Chrome, sans interception d'écriture) ; la rétrospective de pe-epic-19 recommande l'outillage pour l'étape 4.
3. **Gate de preuve UX outillé d'abord (story 20-0), puis la surface unique.** Retenu : un compte Jeedom dédié et des écritures interceptées permettent des parcours réels répétables, sans risque sur la maison, avant de livrer une interface qui remplace l'existant.

## Recommandation

Ouvrir l'epic 20 avec la story 20-0 (gate de preuve UX outillé) comme préalable bloquant de toute story d'interface suivante. Les stories d'interface ne commencent qu'après 20-0 `done` et la fin déclarée de 16-8.

## Découpage proposé en stories

- **20-0 — Gate de preuve UX outillé.** Playwright sur la VM openclaw, compte Jeedom dédié (fourni par Alex), interception des écritures (sauf liste blanche override, avec restauration vérifiée de `data/ha_overrides.json`), vérifications minimales avant tout `done` d'interface. Bloquante pour toutes les stories suivantes.
- **20-1 — Surface unique pièce → équipement → commande, lecture seule.** Remplace la navigation par pièce de 16-8 et la synthèse « Parc global » pour l'affichage (pas encore l'action). Rend l'état « non couverte » dans l'arbre et inclut les équipements désactivés (CC-25). Dépend de 20-0 et de la clôture de 16-8.
- **20-2 — Exclusion et forçage depuis la surface (CC-26).** Ajoute l'action de poser un override de publication (exclusion, forçage) depuis la surface unique, avec sa purge prouvée par clic réel. Dépend de 20-1.
- **20-3 — Suppression du gabarit Jeedom et libellés français d'usage (CC-04 volet UI).** Retire la synthèse et la modale diagnostic désormais redondantes, remplace le jargon (« Mes templates », « Paramètre n°1 »…). Dépend de 20-1 et 20-2.
- **20-4 — Rescan sur la page principale (CC-04 volet UI, fin).** Dépend de 20-1.
- **20-5 — Documentation utilisateur réécrite (CC-07 d).** Dépend de 20-1 à 20-4 (décrit l'interface finale, pas une interface intermédiaire).

Ordre de dépendance obligatoire : `20-0` → `20-1` → (`20-2`, `20-4` en parallèle possible) → `20-3` → `20-5`.

## Critères de fin de l'epic

- Une seule surface pièce → équipement → commande fait foi ; la synthèse « Parc global » et la modale diagnostic distinctes n'existent plus.
- CC-25 et CC-26 fermés et prouvés par clic réel (y compris la purge d'un override de publication, décision d'Alex du 2026-09-29).
- CC-04 (volet UI) fermé : aucun jargon Jeedom résiduel, exclusion/forçage/rescan accessibles depuis la surface unique.
- 16-8 clôturé (`done`), ses écarts repris ou explicitement actés comme non applicables après remplacement par la surface unique.
- Documentation utilisateur réécrite et alignée sur l'interface livrée.
- Gate 20-0 exécuté et vert avant chaque `done` d'interface de l'epic.

## Questions ouvertes pour Alex

1. **Sort de la synthèse « Parc global » et de la modale diagnostic** : suppression complète au profit de la surface unique, ou conservation en lecture seule en complément ? Recommandation : suppression complète (c'est l'intention explicite du cadrage : « elle remplace la synthèse et la modale diagnostic »), à confirmer.
2. **Emplacement de l'exclusion et du forçage** : au niveau de la commande (le plus précis, cohérent avec `CommandDecision` par `cmd_id`), de l'équipement (comme aujourd'hui dans 16-3/16-8), ou de la pièce (groupé, mais sans précédent dans le contrat) ? Recommandation : au niveau de la commande, avec un raccourci équipement (« exclure tout l'équipement ») si Alex le souhaite — à trancher.
3. **Sort des équipements sans pièce (« Aucun »)** : regroupés sous une pseudo-pièce « Aucun » dans la surface unique, ou exclus de la navigation par pièce et seulement visibles ailleurs ? Pas de précédent déjà tranché dans le code actuel — à trancher.
4. **Affichage de l'état « non couverte »** : dans l'arbre de la surface unique, doit-elle apparaître comme une ligne normale (distincte visuellement, jamais bloquante) ou être masquée par défaut avec une bascule d'affichage ? 16-8 cessera de la compter comme bloquante une fois 20-1 livrée — à trancher.
5. **Granularité du chargement du diagnostic** : à l'ouverture de la pièce (synthèse visible sans déplier, le comportement observé en production que 16-8 corrige actuellement vers l'équipement) ou à l'ouverture de l'équipement (AC5 de 16-8 tel qu'écrit, jamais atteint par un parcours réel conforme) ? La réponse d'Alex vaut aussi pour fermer l'écart AC5 de 16-8. Recommandation : à l'ouverture de l'équipement (AC5 tel qu'écrit), pour limiter la charge réseau/diagnostic sur les grandes pièces — à confirmer.
6. **Installation de Playwright et de Chromium sur la VM openclaw** : qui l'installe (Alex en pré-requis manuel, ou une procédure documentée exécutée une fois par Alex), et où (chemin, utilisateur) ? Cette unité n'installe rien (interdit par consigne) — à clarifier avant le début effectif de 20-0.
7. **Emplacement du fichier d'identifiants du compte Jeedom dédié** : chemin hors dépôt proposé par la story 20-0 (`permissions 600`, jamais dans les journaux) — à valider par Alex avant qu'il ne le dépose, avec le nom exact attendu par le gate.

## Notes

- Aucune ouverture `PRODUCT_SCOPE`, aucun nouveau FR/NFR : ce cadrage est documentaire, dans la continuité de pe-epic-19.
- Aucun code, test, script, déploiement ni fusion n'a été modifié par cette unité : documentation seulement.
