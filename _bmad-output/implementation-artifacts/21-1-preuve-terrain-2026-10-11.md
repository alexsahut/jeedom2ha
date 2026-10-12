# Story 21-1 — preuve de terrain (2026-10-11)

> **Statut de ce document.** Rédigé par ClaudeBox le 11/10/2026 à 23:05, complété le 12/10 vers 03:45 (verdict du gate réancré, appareils des boutons de scénario), versé au dépôt avec la clôture de la story 21-1. Il ne cite que des identifiants : aucun nom d’équipement, de pièce ni de scénario (règle CC-48). Toutes les vérifications ont été faites en lecture seule : registre des entités de HA, journal du démon, `VERSION` de la box, page du plugin dans Chrome. Seul le déploiement a écrit, et il a été fait par clawcode.

## Ce qui est déployé

| Élément | Valeur |
|---|---|
| SHA déployé | `30e6c80fe42b33026230291a76c32d5d935aceaf` (`main` après #237 `d293a65` et #238 `30e6c80`) |
| Commande | `./scripts/deploy-to-box.sh --sha 30e6c80… --restart-daemon` (déploiement standard, sans option de nettoyage) |
| `VERSION` de la box | `sha=30e6c80…`, `deployed_at=2026-10-11T20:39:46Z`, `git_status=clean` |
| Démon | redémarré à 22:39:47 (heure de Paris), 0 ligne `ERROR` dans son journal |
| Sync après redémarrage | `total_eq=292 eligible=96 published=263` |

Remarques sur le déroulé :
- Un premier passage, sans `--restart-daemon` (22:23), a copié les fichiers sans redémarrer le démon : l’ancien code tournait encore. Le second passage a fait foi.
- Un passage intermédiaire a été refusé à tort par le garde-fou CI. La cause : un run annulé d’une autre branche créée sur le même SHA (CC-59). Ce run a été relancé avant le déploiement.

## Bloc A — CC-44 (boutons de scénario)

**Avant** (registre des entités de HA, 11/10 vers 20:30) : 355 entités jeedom2ha, dont 92 boutons de scénario. Le démon en publiait 85 ; 7 boutons fantômes : 2, 32, 33, 39, 40, 72, 129.

**Journal du démon après le redémarrage :**
- `[SCENARIO] Retained button topics collected: 98 (92 scenario button(s))`
- `[SCENARIO] Unpublished 36 scenario button(s) (36 inactive, 0 from broker): ids=[2, 31, 32, 33, 35, 39, 40, 47, 48, 52, 58, 60, 70, 72, 80, 88, 90, 100, 101, 102, 124, 129, 130, 133, 134, 141, 143, 145, 146, 147, 148, 151, 155, 156, 157, 166]`

Les 36 scénarios inactifs de Jeedom reçoivent chacun une configuration vide. La plupart n’avaient pas de bouton, et l’opération est alors sans effet. Les 7 fantômes sont tous des scénarios **désactivés**, aucun n’est supprimé : la purge « le broker fait foi » n’a donc rien eu à retirer de plus (0 retiré d’après le broker).

**Diff de l’inventaire MQTT (outil de déploiement) :** 355 → 347 topics, aucun ajouté, 8 retirés :
`homeassistant/button/jeedom2ha_scenario_{2,32,33,39,40,72,129,147}/config`.

**Après** (registre des entités de HA) : 347 entités jeedom2ha, dont 84 boutons de scénario. Aucun des 8 boutons ne reste. Les 8 figurent dans `deleted_entities` avec leur `entity_id` (non orphelins). Aucun n’avait de réglage personnalisé dans HA : nom, pièce et icône sont vides (relevé du 12/10).

**Scénario 147.** Il était actif au premier passage (publié à 22:23:52) et inactif au second, retiré à 22:39:50. Son journal montre une exécution par minute jusqu’à 22:36, puis plus rien. Aucun journal de scénario ne trace sa désactivation entre 22:35 et 22:39 : c’est donc une action manuelle. Le retrait de son bouton est le comportement décidé par Alexandre (Q2 A). Son bouton reviendra au premier rescan après sa réactivation.

**Disponibilité et appareil des boutons de scénario (AC 6 bis).** La disponibilité « pont seul » est couverte par les tests de #237. Sur le terrain, le registre des appareils de HA (relevé du 12/10 vers 03:20, lecture seule) montre l’effet attendu sur la charge utile :
- 15 des 84 boutons de scénario ont le même identifiant qu’un équipement Jeedom (comparaison avec les 292 équipements de la page du plugin) : 15, 18, 21, 81, 82, 83, 85, 109, 110, 112, 113, 120, 160, 179 et 180.
- Ce sont exactement les 15 appareils de bouton de scénario modifiés par HA à 20:39:51Z, au premier sync après le redémarrage. Ils portent maintenant les valeurs neutres (`manufacturer` « Jeedom », `model` « Unknown ») et ne reprennent plus le fabricant ni le modèle de l’équipement homonyme (par exemple, pour 109, 110 et 113, les appareils d’équipement sont de type `virtual` ou `camera`).
- Les 69 autres appareils de bouton de scénario n’ont pas été modifiés (dernière modification au plus tard le 27/09) : leur charge utile est inchangée, comme le veut l’AC 6 bis.
- Les 15 boutons gardent leur `unique_id`, leur `entity_id` et leur appareil propre (`jeedom2ha_scenario_<id>`, rattaché au pont).

Le contenu retenu de la disponibilité n’a pas été relu sur le broker : aucun outil du dépôt ne lit les charges utiles, et une lecture ad hoc sur la box de production n’apporterait rien de plus que les tests.

**Réactivation (AC 2 et AC 13 a) : pas encore observée sur le terrain.** L’AC 13 a demande qu’un humain désactive puis réactive un scénario de test, et que l’on vérifie que son bouton revient dans HA avec ses réglages (nom, identifiant d’entité, pièce, icône). Ce passage n’a pas été fait : il demande une action sur Jeedom, réservée à Alexandre. **Décision d’Alexandre (12/10 vers 05:50) : clôture de 21-1 avec une réserve sur ce point** ; la vérification se fera à la prochaine réactivation naturelle d’un scénario (suivi CC-61). La réactivation est couverte par les tests unitaires de #237 (même `unique_id`, même `command_topic`). Côté HA, les 8 boutons retirés figurent dans `deleted_entities`, qui garde l’`entity_id`, le nom, la pièce, l’icône et les alias d’une entité supprimée pour les lui rendre si elle revient avec le même `unique_id`. Comme aucun de ces 8 boutons n’avait de réglage personnalisé, l’essai n’aura de valeur que sur un bouton à qui l’on a d’abord donné une pièce ou une icône dans HA.

## Bloc B — CC-47 (affichage de la commande 5369)

Équipement 579, page du plugin, vérification dans Chrome :

| | Avant (déploiement `f10c4478`) | Après (`30e6c80`) |
|---|---|---|
| Ligne de 5369 | « Ne sera pas publié — état sans ordre On/Off » | « Sera publié : binary_sensor » |
| Synthèse de 579 | « Partiellement publié : 4 prête(s), 1 bloquante(s). » | « Sera publié dans Home Assistant : 5 commande(s) prête(s). » |
| Compteurs de la pièce | 93 prêtes, 3 bloquantes, 2 équipements à corriger | 94 prêtes, 2 bloquantes, 1 équipement à corriger |

Les autres lignes de 579 sont inchangées (5368 « commande sans type Home Assistant applicable » ; 5689, 5494, 5695 et 5493 « Sera publié : sensor »). Dans HA, 579 garde ses 5 entités (`jeedom2ha_eq_579_cmd_{5689,5494,5695,5493,5369}`) : rien de ce qui est publié n’a changé (AC 9).

**Validation UX** : donnée par ClaudeBox au nom d’Alexandre, sur sa délégation du 11/10 vers 22:50.

## Gate 20-0

**Premier passage** (11/10, sur `30e6c80`) : FAIL à l’étape `ancre-bloquante`, pour la référence comme pour le contrôle négatif. Le parcours de référence s’ancrait sur la première commande bloquante de 579, qui n’existe plus : c’est l’effet voulu du bloc B. Aucune écriture n’a été transmise : l’intercepteur n’a aucun échec, et les compteurs d’override et d’action du démon sont à 0.

**Réancrage** : PR #245 (fusionnée, `ab3a854`). La référence et le contrôle négatif visent maintenant l’équipement 380 (pièce 4), dont la seule commande bloquante est 2971. Les noms de pièce et de marque ont disparu des fichiers et des étapes du gate : `reference-bascule-eq-380.mjs`, `decouverte-piece-25-eq-579.mjs`. La relecture R1 a corrigé la pièce du parcours de découverte (25, et non 3).

**Second passage** (12/10, 03:35 → 03:41, tête de #245 `b3a06d2`, box toujours sur `30e6c80`) :

| Parcours | Verdict | Constats |
|---|---|---|
| Découverte (pièce 25, eq 579) | **PASS** | 5369 « prête », 5368 « non couverte », les 4 autres « prêtes » ; synthèse « Sera publié dans Home Assistant : 5 commande(s) prête(s). » ; pièce 25 : 94 commandes prêtes, 2 bloquantes, 1 équipement à corriger ; 0 erreur console, démon ou plugin |
| Référence (eq 380, commande 2971) | **PASS** | aperçu réel `sensor` toujours bloquant, sans écriture ; bascule simulée vers `binary_sensor` « prête » (synthèse « 1 commande(s) prête(s) ») ; retour automatique « bloquante », synthèse revenue à l’initiale |
| Contrôle négatif | **FAIL attendu** | une seule requête `saveMappingOverride` non déclarée, bloquée par l’intercepteur (`block-fail`) ; la console ne relève que l’échec de cette requête bloquée ; aucune erreur du démon ni du plugin |

Pour les trois parcours, les compteurs du démon (override sauvegardé, retour auto, sync, action, discovery) sont à 0. Aucune écriture n’a été transmise à la box.

À noter : l’aperçu réel de 2971 est refusé pour `sensor` comme pour `binary_sensor` (`ha_missing_state_topic`). La bascule de la référence est donc simulée, comme elle l’était pour 579.

## Hors périmètre, relevé pendant la preuve

- CC-59 : le garde-fou CI du déploiement lisait aussi les runs d’autres branches qui ont le même SHA. Corrigé par #244 (`f6acf0f`) : seuls comptent les runs de la branche déployée, `main` par défaut.
- CC-60 : sur l’équipement 380, la liste « Override HA » de 2971 propose notamment `sensor` et `binary_sensor`, mais l’aperçu réel refuse les deux (`ha_missing_state_topic`, `ambiguous_skipped`). La voie normale reste celle qu’indique l’écran : préciser dans Jeedom les types génériques des commandes 2968 à 2970. Reste à établir si ces types peuvent aboutir avec un forçage, ou s’ils ne devraient pas être proposés. Renvoyé à la story des compteurs (CC-51), qui revoit la sémantique des lignes.
