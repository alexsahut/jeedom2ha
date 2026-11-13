# Story 26.0 : Audit fonctionnel et UX « premier arrivant », sur la démo

Status: ready-for-dev

> Ouvre l'epic 26 : « Revue fonctionnelle et UX du plugin avant le Market ». Décision d'Alexandre du 2026-11-13 à 22:46 : avant toute publication, une personne qui installe le plugin sans rien connaître du projet doit comprendre l'interface et pouvoir tout faire. Go le même jour à 23:03 (« go 26-0 sur vm de démo »). Story d'audit, **sans aucune modification de code** : elle produit des constats classés, puis les stories de correction.

## Story

En tant que personne qui installe jeedom2ha pour la première fois, sans connaître le projet,
je veux comprendre ce que le plugin publie vers Home Assistant, pourquoi, et comment le changer,
afin de l'utiliser seul, sans aide ni lecture du code.

## Environnement

- **VM de démonstration 122 seulement** : Jeedom de démonstration et HA de démonstration, règle « Zone labo » de clawbox. La production n'est **jamais** touchée.
- Le plugin de la démo est mis au niveau de `main` (après la remise au propre, PR #385) **avant** l'audit, pour auditer l'interface réellement livrée.
- La démo peut être modifiée (inclure, exclure, corriger un mapping) : elle est restaurable par son instantané `demo`. Tout changement est noté et défait à la fin, ou l'instantané est restauré si Alexandre le décide.

## Deux regards

1. **Regard neuf** : un agent sans aucun contexte du projet. Il ne reçoit que l'interface (pages, captures, textes) et la documentation publique destinée aux utilisateurs (`docs/fr_FR/`). Il dit ce qu'il comprend, ce qu'il cherche sans le trouver et ce qui le trompe. Il ne lit ni le code, ni les stories, ni `_bmad-output/`.
2. **Regard expert (ClaudeBox)** : il vérifie chaque critère par l'action réelle sur la démo, relève l'écart entre ce que l'interface promet et ce que HA reçoit, et donne pour chaque constat la preuve (capture, export de décision, topic MQTT).
3. **clawcode** relie chaque constat confirmé à son code (fichier, fonction) et estime la correction.

## Grille d'audit (critères d'Alexandre, 13/11 22:46)

| # | Critère | Ce qui est vérifié |
|---|---|---|
| G1 | **Tout voir** | Tout ce qui est publié vers HA est visible dans le plugin. Pour ce qui ne l'est pas, la raison est donnée et compréhensible. |
| G2 | **Inclure / exclure** | Par plugin, par pièce et par équipement, dans les deux sens. L'effet est visible dans le plugin et constaté dans HA (entités ajoutées ou retirées). |
| G3 | **Agir sur tout** | Chaque commande publiée est pilotable depuis HA. Ce qui ne l'est pas est expliqué (famille sensible, absence d'état fiable…). |
| G4 | **Corriger un mapping** | Quand le type générique d'une commande est absent ou faux, l'utilisateur peut corriger la projection depuis le plugin (override) et voir le résultat dans HA. Tous les types publiés sont proposés : en particulier `valve` et `lock`, connus comme absents de l'outil. |
| G5 | **Diagnostic** | L'écran de diagnostic permet à un non-initié de comprendre pourquoi un équipement ou une commande n'est pas publié, et quoi faire. Limite connue : seule l'entité principale est lue (24-15). |
| G6 | **Vocabulaire et aide** | Les termes affichés (« projeté », « publié », « gardé », « exclu »…) sont compréhensibles et cohérents entre les écrans. Une aide est présente dans l'interface et la documentation y renvoie. |
| G7 | **Premier parcours** | De l'installation au premier équipement visible dans HA : configuration MQTT, démarrage du démon, premier « Publier », messages d'erreur utiles en cas de mauvaise configuration du broker. |
| G8 | **Restes connus à confirmer** | Noms des boutons (P2), familles sensibles publiées en bouton, boutons de repli non exécutables, bouton secondaire ambigu, polarité du `binary_sensor` de serrure, ex-24-10 (écarts résiduels). |

## Critères d'acceptation

1. **AC1** — La démo exécute le plugin de `main` (SHA relevé), avec un relevé avant et après l'audit.
2. **AC2** — Chaque critère G1 à G8 a au moins un parcours exécuté et documenté : action, attendu, constaté, preuve.
3. **AC3** — Le regard neuf est produit sans contexte du projet : sa consigne et ses entrées exactes sont jointes au rapport.
4. **AC4** — Chaque constat est classé **bloquant** (empêche l'usage ou trompe l'utilisateur), **gênant** ou **cosmétique**, et rattaché par clawcode à son code.
5. **AC5** — Le rapport propose le découpage en stories de l'epic 26, avec un ordre et un critère de sortie de l'epic : un parcours premier arrivant réussi sans aide, rejoué après correction.
6. **AC6** — Aucun nom réel, aucune IP et aucune donnée de la maison dans le dépôt (CC-48). La démo ne contient que des données fictives.
7. **AC7** — Les changements faits sur la démo sont listés et défaits, ou l'instantané `demo` est restauré si Alexandre le décide.

## Tâches

- [ ] T1 — Mettre la démo au niveau de `main` (clawbox, Zone labo, sur consigne ClaudeBox), relevé AC1.
- [ ] T2 — Regard neuf : captures et textes de chaque écran du plugin, plus la documentation utilisateur, transmis à un agent sans contexte ; son compte rendu brut est joint.
- [ ] T3 — Regard expert : parcours G1 à G8 sur la démo, avec preuves.
- [ ] T4 — Rattachement au code et estimation (clawcode).
- [ ] T5 — Rapport `26-0-rapport-audit.md`, découpage de l'epic 26, revue avec Alexandre.
- [ ] T6 — Remise en état de la démo (AC7).

## Garde-fous

- Démo seulement. Aucun accès à la production ni à son broker.
- Pas de correction pendant l'audit : un constat devient une story.
- Pas de mot de passe dans les sorties, les captures ni le dépôt ; masquage de l'hôte MQTT sur les captures (constat de 23-2).

## Journal

- 2026-11-13 — Story créée par ClaudeBox (décision d'Alexandre de 22:46, go de 23:03 sur la VM de démonstration).
