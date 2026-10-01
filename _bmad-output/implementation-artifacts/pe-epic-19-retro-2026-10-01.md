# Rétrospective pe-epic-19 — Contrat de décision unifié (`CommandDecision` / `evaluate_equipment`)

Date : 2026-10-01
Projet : jeedom2ha
Cycle actif : Moteur de projection explicable — étape 3 du plan d'action (ClaudeBox et clawcode, validé par Alex le 2026-09-26)
Rédaction : ClaudeBox (superviseur), appliquée par clawcode.

## Synthèse

L'epic 19 a remplacé les 4 calculs divergents de la décision de publication (sync, surface par pièce, aperçu à blanc, bouton « Publier ») par une seule fonction pure, `evaluate_equipment()`. Il a aussi fermé les défauts de publication relevés en route.

Les 7 stories sont `done`, de 19-0 à 19-6. Toutes, sauf 19-0 (fonction pure, sans branchement), ont été déployées sur la box et prouvées sur le terrain. Les 4 stories qui touchent l'interface (19-3 à 19-6) sont passées par `ready-for-UX-validation`.

19-3 est close avec une dérogation sur AC5, décidée par Alex le 29/09 à 08:13 (option A). Aucune interface ne permet encore de poser un override de publication (CC-26) : la purge de cet override par « Revenir au mode automatique » est prouvée par test (AC3), et son clic réel est un critère obligatoire de l'étape 4.

Durée : du 2026-09-27 au 2026-09-30.

## Valeur livrée

- **19-0** : contrat pur `CommandDecision` / `evaluate_equipment()`, sans branchement. PR #167.
- **19-1** : le sync consomme le contrat, sans changement de comportement.
  - PR #169, puis correctif CC-22 (PR #172).
  - Parité stricte avant et après : 292 décisions, 353 topics retenus, diff vide.
  - Préalable : CC-20 corrigé par une PR `fix/` dédiée.
- **19-2** : découplage I11 entre états et commandes (`sync/state.py`, `sync/command.py`). PR #174.
  - Les 12 écouteurs d'état attendus (eq 579 et 585) sont republiés.
  - Correctif post-fusion 19-2b (PR #178, preuve PR #179) : leurs entités restaient indisponibles dans HA, faute de disponibilité publiée pour les secondaires ; elles reprennent une valeur (CC-28).
- **19-3** : surface par pièce et aperçu branchés sur le contrat. PR #176.
  - Ferme CC-03 et CC-19.
  - « Revenir au mode automatique » efface tous les overrides de l'équipement.
- **19-4** : « Publier » en mini-sync, avec un filtre de portée unique. PR #180.
  - Correctif post-fusion 19-4b (PR #181) pour CC-30 et CC-31, relevés par Codex après la fusion.
  - Ferme CC-18 et CC-14 P1.
- **19-5** : « Publier » publie l'état initial avec la valeur lue au clic. PR #185. Ferme CC-29.
- **19-6** : durée des actions HA bornée pour les grands parcs.
  - Budget fixe du relais et du client, échéance transmise au démon, pauses de lissage plafonnées, action protégée et sérialisée.
  - PR #188 (story), #189 (code), #190 (preuve et clôture). Ferme CC-32.

**Points fermés** : CC-03, CC-14 P1, CC-18, CC-19, CC-22, CC-28, CC-29, CC-30, CC-31, CC-32. CC-04 est partiellement fermé : son volet contrat est fait, son volet interface revient à l'étape 4.

## Gates epic-level (`epics-projection-engine.md`)

- **Une seule fonction fait foi** : sync (19-1), surface par pièce et aperçu (19-3), « Publier » (19-4). ✔
- **Parité avant tout changement de comportement** : prouvée en 19-1 (diff vide), avant le découplage I11 de 19-2. ✔
- **I11 corrigé par découplage**, sans couplage forcé du secondaire sur le principal. ✔
- **CC-03, CC-18, CC-19 et CC-14 P1 fermés et prouvés**, par parité, clic réel et preuves terrain. CC-04 est partiel, comme prévu. Pour CC-19, la purge de l'override de publication est prouvée par test ; son clic réel est reporté à l'étape 4 (dérogation d'AC5 de 19-3). ✔
- **`local_secret` jamais exposé** par l'outil de parité : AC5 de 19-1, vérifié par un test et une revue. ✔

## Preuves

- **Une preuve terrain par story déployée** :
  - `19-1-field-proof-2026-09-28.md`, `19-2-field-proof-2026-09-28.md`, `19-2b-field-proof-2026-09-29.md` ;
  - `19-3-field-proof-2026-09-29.md` et `19-3-ac5-validation-2026-09-29.md` ;
  - `19-4-field-proof-2026-09-29.md`, `19-5-field-proof-2026-09-30.md`, `19-6-field-proof-2026-09-30.md`.
- **Gate d'inventaire à chaque déploiement** : relevés avant et après identiques, hors écarts expliqués ; 0 ERROR ; démons des autres plugins inchangés.
- **Validations UX nommées d'Alex** : 19-4 (29/09 à 23:30), 19-5 (30/09 à 09:57), 19-6 (30/09 à 21:33). Pour 19-3 AC5, la validation par clic a été confiée à ClaudeBox par décision d'Alex (29/09).

## Risques résiduels

- **CC-26** : aucune interface ne permet encore de poser un override de publication. Le clic réel sur sa purge est un critère obligatoire de l'étape 4 (décision d'Alex du 29/09 à 08:13).
- **CC-25** : les équipements désactivés sont absents de la surface par pièce, et l'état « non couverte » n'est pas rendu dans l'arbre. À traiter à l'étape 4.
- **Résiduels déclarés de 19-6** :
  - appels PHP à Jeedom non interruptibles ;
  - travail local de réalignement des écouteurs non borné (0,6 s mesuré, 14 s de marge) ;
  - concurrence avec la synchronisation périodique ;
  - déconnexion du client simulée par une annulation.
- **Écouteurs d'état non réalignés après « Suppr. »** : ils restent actifs jusqu'au « Publier » suivant. Les évènements reçus sont rejetés (`state_target_not_found`), sans effet. Risque faible selon clawbox (challenge croisé du 30/09) ; piste à trier.
- **Capacité documentée** (environ 250 équipements typiques) : très prudente face au coût mesuré sur la box (environ 2,5 ms par équipement). À recalibrer seulement sur décision.

## Leçons

- **La preuve terrain discriminante reste indispensable.** Les relevés avant et après, côté box et côté HA, ont rendu visible ce que les tests ne voyaient pas :
  - le bouton du scénario 2 republié en 19-5 (écart expliqué, sans lien avec la story) ;
  - les secondaires des eq 579 et 585 indisponibles dans HA (CC-28, relevé dans `core.restore_state`).
- **Déployer exactement le SHA relu.** En 19-4, un `main` local périmé a été déployé une vingtaine de secondes, puis retiré par retour arrière. Depuis, chaque déploiement part d'un worktree neuf, vérifié par `git rev-parse` avant tout envoi.
- **La revue Codex paie, mais coûte en tours.**
  - Elle a trouvé de vrais défauts, y compris après une fusion (CC-30 et CC-31).
  - Mais 19-6 a demandé 19 tours sur la story, 8 sur le code et 4 sur la PR de clôture.
  - Les 3 tours évitables de la PR #190 venaient de la documentation de clôture : File List non synchronisée, définition de `done` absente, lignes de journal abrégées.
  - **Règle retenue** : un passage en `done` porte toujours le bloc « Définition de `done` » de `docs/bmad-parcours-rapide-complet.md` (SHA, CI, tests ciblés nommés, commandes exactes, validation UX avec son SHA et son environnement). Il porte aussi une File List à jour et des journaux cités en entier.
- **Les unités détachées doivent rester petites, et leurs rapports factuels.**
  - Le développement de 19-6 a dû être découpé en 12 unités (A à L).
  - Une unité a écrit un résultat qu'elle n'avait pas observé ; une autre a affirmé à tort qu'une ligne de journal « n'existe pas dans le code ».
  - **Règle retenue** : n'écrire que ce qu'une commande vient de montrer, et borner explicitement la portée de toute recherche négative (« non trouvé dans … »).
- **Autonomie (règle d'Alex du 30/09)** : déployer, prouver et fusionner sans nouveau go a nettement accéléré le cycle. Deux défauts restent :
  - une unité morte faute de modèle disponible (authentification OpenAI indisponible, quota Anthropic épuisé) n'écrit plus de rapport : il faut aussi lire son journal ;
  - une relecture planifiée par ClaudeBox a été manquée, et c'est Alex qui a relancé.

## Conclusion

L'epic 19 est clos : ses gates epic-level sont tenus, et les points visés sont fermés et prouvés sur la box.

Suite : l'étape 4 du plan d'action, l'interface. Elle comprend :
- le gate de preuve UX outillé ;
- la surface unique pièce → équipement → commande ;
- CC-04 (volet interface), CC-25 et CC-26.

La story 16-8, dont cette surface est la base, reste `in-progress`. Son parcours navigateur réel du 2026-10-01 est partiel (`16-8-ac14-validation-2026-10-01.md`) : le chargement par équipement (AC5) et la bascule vue au clic (AC14) sont à reprendre ; la synthèse (AC9-AC10) est corrigée dans le code, à déployer. Tout cela précède sa validation UX.
