# Rétrospective pe-epic-20 — Étape 4 : l'interface (surface unique pièce → équipement → commande)

Date : 2026-10-11
Projet : jeedom2ha
Cycle actif : Moteur de projection explicable — étape 4 du plan d'action (ClaudeBox et clawcode, validé par Alex le 2026-09-26)
Rédaction : ClaudeBox (superviseur), appliquée par clawcode.

## Synthèse

L'epic 20 a remplacé la navigation par pièce de la story 16.8 par une surface unique pièce → équipement → commande, sans jargon Jeedom ni gabarit, avec la possibilité de poser ou retirer un override de publication directement depuis cette surface, et une documentation utilisateur réécrite sur l'interface livrée.

Les 6 stories sont `done`, de 20-0 à 20-5. Toutes les stories d'interface (20.1 à 20.4) sont passées par `ready-for-UX-validation` puis une validation UX nommée d'Alexandre ou de ClaudeBox par délégation ; 20.5 est une story documentaire, sans gate 20-0 ni déploiement, close par une relecture ClaudeBox et une relecture indépendante.

Durée : du 2026-10-01 au 2026-10-11.

## Valeur livrée

- **20-0** : gate de preuve UX outillé (Playwright, interception des écritures, aucune écriture transmise à la box pendant les parcours). Préalable à toute story d'interface suivante.
- **20-1** : surface unique pièce → équipement → commande ; ferme CC-25 (équipements désactivés inclus, état neutre).
- **20-2** : exclusion et forçage depuis la surface, purge par clic réel ; ferme CC-26. Réserve sur la commande 5369 (état sans ordre On/Off), forçage de l'eq 463 gardé par décision d'Alex.
- **20-3** : suppression de la synthèse « Parc global » et de la modale diagnostic, libellés français d'usage ; ferme le volet UI de CC-04. Deux rondes de correctifs post-fusion (R1, R2 — PR #228) après relecture a posteriori.
- **20-4** : rescan sur la page principale ; ferme CC-40 et CC-41. Réserve AC6 (un scénario désactivé garde son bouton dans HA, défaut antérieur).
- **20-5** : documentation utilisateur réécrite sous `docs/fr_FR/`, table de traçabilité affirmation → code ; ferme CC-07 d. Une ronde de correctifs (R1 — PR #232) après relecture.

**Points fermés** : CC-25, CC-26, CC-04 (volet UI, fermeture complète), CC-07 d, CC-40, CC-41.

## Gates epic-level (`epics-projection-engine.md`)

- **La surface unique consomme exclusivement `evaluate_equipment()`** ; aucun recalcul de décision propre à l'UI. ✔
- **CC-25 et CC-26 fermés et prouvés par clic réel**, y compris la purge d'un override de publication (20-1, 20-2). ✔
- **CC-04 (volet UI) fermé** : aucun jargon Jeedom résiduel dans l'interface livrée (20-3). ✔
- **Story 16.8 `done` avant la bascule effective sur la surface unique** (clôturée avant le démarrage de 20-1). ✔
- **Gate 20.0 vert avant chaque `done` d'interface de cet epic** ; aucune écriture transmise à Jeedom ni au démon pendant les parcours du gate ; les preuves terrain qui écrivent réellement ont suivi la règle de la revue Codex du 2026-10-01 (20-1 à 20-4, chacune avec son artefact de preuve terrain et gate 20-0 PASS). ✔
- **Documentation utilisateur réécrite et alignée sur l'interface livrée** (20-5, PR #232, relue en deux rondes). ✔

## Preuves

- **Une preuve terrain par story d'interface déployée** : `20-1-preuve-validation-ux-2026-10-05.md`, `20-2` (preuve terrain du 08/10 et complément du 06/10), `20-3-preuve-validation-ux-2026-10-11.md` (deux déploiements, 09/10 et 11/10), `20-4-preuve-validation-ux-2026-10-06.md`.
- **Gate 20-0 PASS avant chaque déploiement d'interface**, contrôle négatif (`block-fail` attendu) systématique.
- **Validations UX nommées** : 20-1 (ClaudeBox, délégation Alex 08:54), 20-2 (Alex, 2026-10-08), 20-3 (Alex, 09/10 20:25, puis contrôle ClaudeBox des correctifs le 11/10), 20-4 (ClaudeBox, go Alex 06/10 08:01).
- **Relecture a posteriori de 20-3** (PR #225) par ClaudeBox et une relecture indépendante, deux rondes de correctifs (R1 PR #228, R2) avant clôture.
- **Relecture de 20-5** (PR #232) par ClaudeBox et une relecture indépendante : environ 150 affirmations vérifiées dans le code, une ronde de correctifs (R1), contrôle des noms réels par empreintes.

## Risques résiduels

- **CC-51 / story « compteurs »** : la sémantique actuelle des compteurs (« publiés », « en attente d'application », « non pris en charge ») doit être revue ; prévue avec CC-36 et CC-51, après CC-44 et CC-47 (ordre décidé par Alex le 2026-10-11 à 15:48). Le bloc `compteurs` de la documentation de 20.5 est isolé et porte un bandeau d'obsolescence en attendant cette story.
- **Réserve 20-2 (commande 5369)** : état sans ordre On/Off, ni un type seul ni le forçage ne la publient dans l'état actuel ; à traiter par une story dédiée (suivi CC-47).
- **Réserve 20-4 (AC6)** : un scénario désactivé garde son bouton dans Home Assistant (CC-44, défaut antérieur à cet epic).
- **Écarts relevés par la relecture de 20-5, non corrigés dans cette story** (à traiter avec la story compteurs ou une story dédiée) : le libellé « Supprimer puis recréer » ne fait que dépublier (la recréation suppose un « Republier » ou un rescan ensuite) ; le cloisonnement des compteurs (AC6) laisse passer deux libellés proches des compteurs hors de la modale.
- **CC-54 (journal du démon tronqué par Jeedom)** : la maintenance des journaux de Jeedom peut rendre un parcours du gate 20-0 non concluant (observé pendant la preuve terrain de 20-3, relancé sans conséquence).
- **CC-48 (noms réels dans le dépôt public)** : un nom d'équipement Jeedom a dû être retiré d'un artefact de 20-2 après coup (mise en cohérence PR #226) ; le contrôle par empreintes est désormais systématique en relecture de documentation.

## Leçons

- **La relecture a posteriori trouve des écarts qu'aucun test ne voit.** Sur 20-3, la relecture post-fusion (R1/R2) a trouvé une régression fonctionnelle (republication ciblée par équipement disparue dès qu'il n'y avait plus d'override en attente) et une erreur de gating (lecture de la dernière décision du principal au lieu de la présence réelle dans Home Assistant) — aucun test ne les couvrait avant la relecture. **Règle retenue** : une relecture a posteriori après fusion reste nécessaire même quand les tests sont verts et la CI passe, en particulier sur les chemins de gating et d'état affiché.
- **Délégation aux sessions cloud, tours plafonnés à 300 s.** Le pattern retenu sur cet epic (worktree dédié, branche poussée sur GitHub *avant* `claude --cloud` pour que la session continue sur la branche choisie plutôt que sur une branche `claude/...` dérivée, brief détaillé avec périmètre et critères de clôture explicites, suivi par `claude -p --cloud <session_id>` pour les rondes de correctifs) a permis d'enchaîner create-story, dev-story et plusieurs rondes de revue sans accès box. **Point de méthode découvert pendant 20.5** : une branche locale non poussée avant le lancement fait démarrer la session cloud sur sa propre branche dérivée, pas sur celle préparée localement — toujours pousser la branche avant `claude --cloud` si la suite doit continuer exactement sur elle.
- **Un garde-fou de déploiement peut être trompé par la CI elle-même.** CC-50 : `deploy-to-box.sh` lisait tous les check-runs d'un SHA sans distinguer leur déclencheur, alors que le même workflow sert le push/PR et un cron dominical ; corrigé en filtrant par événement déclencheur (`push`/`pull_request`/`workflow_dispatch`), en ignorant les runs `schedule`.
- **Le journal du démon peut être tronqué par la maintenance de Jeedom pendant un parcours du gate** (CC-54), rendant un contrôle non concluant sans rapport avec le code testé ; la relance du seul parcours concerné suffit, mais le constat doit être consigné plutôt que réinterprété comme un échec du contrôle.
- **Les noms réels s'infiltrent facilement dans un dépôt public.** Un nom d'équipement Jeedom a dû être retiré après coup d'un artefact de preuve (20-2, CC-48) ; la relecture de documentation (20.5) a depuis systématisé un contrôle par empreintes, qui ne recopie jamais les noms réels même pour les vérifier.

## Conclusion

L'epic 20 est clos : ses gates epic-level sont tenus, les points visés sont fermés et prouvés (terrain pour 20.1 à 20.4, relecture en deux rondes pour 20.5).

Ordre décidé par Alex pour la suite (2026-10-11, 15:48) : 20-5 (fait) → CC-44 + CC-47 → CC-36 avec CC-51 et une story « compteurs » (nouvelle sémantique : « publiés » = présents dans HA, « en attente d'application », « non pris en charge ») → l'epic de parité HomeKit CC-33. Une version candidate est prévue sur `beta` après 20-5.
