# Story 22-1 — preuve de terrain (2026-10-12)

> **Statut de ce document.** Rédigé par ClaudeBox le 12/10/2026 vers 07:35, à verser au dépôt avec la clôture de la story 22-1. Il ne cite que des identifiants : aucun nom d’équipement, de pièce, de scénario ni de personne (règle CC-48). Toutes les vérifications ont été faites en lecture seule : registres des appareils et des entités de HA, journal du démon, page du plugin dans Chrome. Seul le déploiement a écrit, et il a été fait par clawcode.

## Ce qui est déployé

| Élément | Valeur |
|---|---|
| SHA déployé | `6a74e58596953925751e70559f8536153b7ed506` (`main` après #249) |
| Commande | `./scripts/deploy-to-box.sh --sha 6a74e58… --restart-daemon`, depuis un worktree neuf (déploiement standard, sans option de nettoyage) |
| `VERSION` de la box | `sha=6a74e58…`, `deployed_at=2026-10-12T05:18:58Z`, `git_status=clean` |
| Démon | redémarré à 07:19:00 (heure de Paris), 0 ligne `ERROR` ; 6 `WARNING` préexistants (un override sans type, deux équipements à commandes en double) |
| Sync | `total_eq=292 eligible=96 published=263` |
| Garde-fou CI | accepté du premier coup : seuls les runs de `main` ont été jugés (CC-59, #244) |

Remarque : un premier lancement depuis un worktree neuf a échoué avant toute action (`JEEDOM_BOX_HOST is not set`). Le script lit sa configuration dans le `.env` du dépôt, absent d’un worktree neuf. Le `.env` a été lié au worktree, sans afficher son contenu, puis le déploiement a été relancé.

## Inventaire MQTT

347 → 348 topics, aucun retiré, un ajouté : `homeassistant/button/jeedom2ha_scenario_147/config`. Le scénario 147 a été réactivé dans Jeedom entre le 11/10 vers 22:39 et ce déploiement, en dehors du plugin. Son bouton est revenu au premier sync, comme prévu par 21-1.

## Appareils (registre des appareils de HA)

| | Avant (12/10 vers 06:15) | Après (07:21) |
|---|---|---|
| Appareils jeedom2ha d’équipement | 91 | 91 |
| Au nom exact de l’équipement Jeedom | 62 | **91** |
| Au nom d’une de leurs commandes | 29 | 0 |
| Appareils modifiés par ce déploiement | — | **exactement les 29 attendus**, à 05:19Z |
| Pièces modifiées | — | 0 |
| Nom choisi à la main (appareil 594) | présent | **conservé** |

La comparaison avec les noms Jeedom a été faite sur la page du plugin. Les 29 appareils : 67, 174, 206, 207, 234, 235, 312, 456, 457, 459, 468, 475, 506, 519, 520, 521, 522, 523, 553, 579, 580, 583, 585, 594, 603, 628, 631, 632, 633.

## Entités (registre des entités de HA)

Comparaison des 347 entités présentes avant le déploiement :

| Contrôle | Résultat |
|---|---|
| `entity_id` modifiés | **0** |
| Noms choisis à la main modifiés (37 entités) | **0** |
| Pièces choisies à la main modifiées (23 entités) | **0** |
| Entités changées d’appareil | 0 |
| Noms de découverte (`original_name`) modifiés | **16**, exactement les entités uniques des 16 appareils à une seule entité parmi les 29 (nom de commande → nom de l’équipement) |

L’entité principale des équipements à plusieurs entités garde le nom de l’équipement, selon la décision d’Alexandre du 12/10 vers 06:50 : 12 entités, 7 interrupteurs et 5 lumières. Les autres entités gardent le nom de leur commande.

## `entity_id` stable (Q7 B) et Task 0

Le bouton du scénario 147 est la première entité recréée depuis le déploiement :
- HA a restauré son entrée de registre depuis `deleted_entities` : date de création du 09/06 conservée, et l’entrée supprimée a disparu ;
- son `entity_id` est désormais `button.jeedom2ha_scenario_147`, la valeur de `default_entity_id`. Son ancien `entity_id` était tiré de son nom, comme pour toutes les entités créées depuis le 06/05.

Conclusion : HA 2026.9.4 applique bien `default_entity_id`, et il remplace l’`entity_id` précédent quand une entité revient après une suppression. C’est conforme à la documentation de HA et à la décision Q7 B (« une entité recréée passe une fois à la forme technique »). Aucune automatisation, aucun script ni aucune scène de HA ne cite un bouton (recherche dans `automations.yaml`, `scripts.yaml` et `scenes.yaml`) : ce changement n’a aucun effet aujourd’hui.

## Réserve CC-61 (AC 13 a de 21-1)

Ce retour du bouton 147 est la réactivation naturelle attendue. L’entrée de registre est restaurée. Le nom, la pièce et l’icône étaient vides avant comme après, donc il n’y avait rien d’autre à restaurer. Seul l’`entity_id` passe à la forme technique, par l’effet voulu de Q7 B.

## Gate 20-0

Passage du 12/10, de 07:25 à 07:31, sur `6a74e58` déployé :

| Parcours | Verdict | Constats |
|---|---|---|
| Découverte (pièce 25, eq 579) | **PASS** | 5369 « prête » ; synthèse « Sera publié dans Home Assistant : 5 commande(s) prête(s). » ; pièce 25 : 94 prêtes, 2 bloquantes ; 0 erreur |
| Référence (eq 380, commande 2971) | **PASS** | bascule simulée « prête », puis retour automatique « bloquante » ; 0 erreur |
| Contrôle négatif | **FAIL attendu** | une seule requête `saveMappingOverride` non déclarée, bloquée (`block-fail`) |

Pour les trois parcours, les compteurs du démon sont à 0 (override, retour auto, sync, action, discovery). Aucune écriture n’a été transmise. L’écran du plugin n’est pas touché par 22-1 : ce passage confirme qu’il n’y a pas de régression.
