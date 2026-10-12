# Story 22-2 — preuve de terrain (2026-10-12)

> **Statut de ce document.** Rédigé par ClaudeBox le 12/10/2026 vers 11:35, à verser au dépôt avec la clôture de la story 22-2. Il ne cite que des identifiants : aucun nom d’équipement, de pièce, de scénario ni de personne (règle CC-48). Toutes les vérifications ont été faites en lecture seule : registres des appareils et des entités de HA, journal du démon, page du plugin dans Chrome. Seul le déploiement a écrit, et il a été fait par clawcode. Le seul clic réel sur une action d’écriture (« Supprimer de Home Assistant ») a été annulé dans sa confirmation.

## Ce qui est déployé

| Élément | Valeur |
|---|---|
| SHA déployé | `09817f91195344fa9391ad12d5d438c4e641934e` (`main` après #255) |
| Commande | `./scripts/deploy-to-box.sh --sha 09817f9… --restart-daemon`, depuis un worktree neuf en HEAD détaché (déploiement standard, sans option de nettoyage) |
| Avant | la box portait `69a4b47` (A1 et A3), déployé à 07:34Z par l’autre chantier ; aucun autre déploiement en cours au lancement |
| Démon | redémarré à 11:11 (heure de Paris), MQTT connecté, 0 ligne `ERROR` ; 6 `WARNING` préexistants (un override sans type, deux équipements à commandes en double) |
| Sync | `total_eq=292 eligible=96 published=263` |
| Garde-fou CI | accepté : CI de `main` sur `09817f9` verte avant le lancement |

## Inventaire MQTT

349 → 348 topics, aucun ajouté, un retiré : `homeassistant/button/jeedom2ha_scenario_129/config`.

Ce retrait ne vient pas de 22-2. Le corps de sync envoyé par Jeedom au déploiement marque le scénario 129 `is_active: false`. Le démon retire donc son bouton, comme le prévoit 21-1 (CC-44). Le journal du démon montre que ce scénario change d’état dans Jeedom, hors du plugin : bouton retiré au déploiement de 22-1 (07:19), republié au déploiement d’A1 (09:34) et au rescan de 09:38, retiré de nouveau à 11:11. Son entrée de registre est dans `deleted_entities` de HA : elle sera restaurée à sa prochaine réactivation.

## Registres de HA (aucune publication ne change)

| Contrôle | Avant (11:02) | Après (11:13) |
|---|---|---|
| Entités jeedom2ha | 349 | 348 (le bouton du scénario 129, voir ci-dessus) |
| Entités modifiées depuis le déploiement | — | **0** |
| Appareils jeedom2ha | 178 | 177 (l’appareil du scénario 129) |
| Appareils modifiés depuis le déploiement | — | **0** |

Aucun `entity_id`, nom, pièce, icône ni appareil n’a changé pour les autres entités. Toute modification aurait mis à jour leur `modified_at`.

## Écran du plugin (lecture seule, Chrome)

**Pièce 25**, en-tête de la modale :

| Avant 22-2 (07:46) | Après 22-2 (11:14) |
|---|---|
| 9 équipements publiés | **9 équipements publiés dans Home Assistant** |
| — | 0 équipement en attente d’application |
| 1 équipement à corriger | **1 équipement non pris en charge** (287) |
| 7 équipements exclus | 7 équipements exclus |
| 1 équipement désactivé dans Jeedom | 1 équipement désactivé dans Jeedom |
| 94 commandes prêtes | **94 commandes publiées dans Home Assistant** |
| — | 0 commande en attente d’application |
| 2 bloquantes + 101 non couvertes | **103 commandes non prises en charge** |

**Recomptage de la pièce 25 (AC8)**, fait indépendamment de l’écran :
- dans les arbres du démon, 9 équipements ont `published_in_ha`, portant 90 entités présentes et 94 commandes publiées ;
- dans le registre des entités de HA, exactement les mêmes 9 équipements ont des entités, avec le même nombre d’entités par équipement (199, 131, 277, 326, 592, 639 : 1 chacun ; 579 : 5 ; 554 : 14 ; 553 : 65). Les 9 autres n’en ont aucune.

Les compteurs disent donc vrai.

**Équipement 287** (une seule entité) déplié :
- compteurs : 0 commande publiée, 0 en attente, 3 non prises en charge ;
- boutons d’équipement : « Exclure l’équipement », « Forcer l’équipement », « Revenir au mode automatique (équipement entier) », « Republier », « Supprimer de Home Assistant » ;
- ligne d’entité **sans aucun bouton**. Avant, elle répétait les trois actions de l’équipement (CC-51).

**Équipement 579** (6 entités) déplié :
- compteurs : 5 commandes publiées, 0 en attente, 1 non prise en charge ;
- chaque ligne d’entité garde ses trois actions, libellées « cette entité » ;
- le sélecteur de la commande 5369, portée par plusieurs entités, est grisé avec l’explication « Cette commande est portée par plusieurs entités : le type Home Assistant choisi ne s’appliquerait qu’à l’entité principale de l’équipement. Réglage indisponible ici. » (CC-58).

**Équipement 380** (pièce 4), commande 2971 :
- la liste « Override HA » ne propose plus que « mode automatique » et `cover`. `sensor` et `binary_sensor`, toujours refusés, ont disparu (CC-60, décision d’Alexandre du 12/10 vers 10:30) ;
- la cause reste lisible : « Ne sera pas publié — type Home Assistant ambigu — précisez les types génériques dans Jeedom » ;
- ligne d’entité sans bouton (une seule entité).

**Clic réel sur « Supprimer de Home Assistant »** (équipement 592, une entité, publié) : la confirmation s’intitule « Supprimer de Home Assistant ». Elle rappelle l’impact sur l’historique et ajoute : « Rien n’est recréé automatiquement : utilisez « Republier » pour remettre dans Home Assistant ce qui a été supprimé. » Clic sur « Annuler » : rien n’a été supprimé (registre de HA inchangé, entité de 592 intacte) et le bouton est rendu (CC-55).

## Temps de lecture d’un équipement

La liste filtrée est calculée par le démon à chaque lecture d’un équipement (`GET /system/mapping_overrides/{eq_id}`) : 8 évaluations par entité. Mesures depuis la page du plugin, en lecture seule :

| | Avant (11:00) | Après (11:13) |
|---|---|---|
| Équipement 579 (6 entités) | 63 / 40 ms | 87 / 69 ms |
| Équipements 380 et 287 (1 entité) | 36 à 40 ms | 41 à 50 ms |
| Pièce 4 (30 équipements, 49 entités), lectures en série | 1 200 ms | 1 739 ms |
| Lecture la plus longue de la pièce 4 | 68 ms | 385 ms (équipement à 24 entités) |

Pas de blocage visible. Le coût croît avec le nombre d’entités d’un équipement : à suivre (CC-62) si un équipement plus gros apparaît.

## Gate 20-0

Passage du 12/10, de 11:18 à 11:26, sur `09817f9` déployé :

| Parcours | Verdict | Constats |
|---|---|---|
| Découverte (pièce 25, eq 579) | **PASS** | 8 compteurs de pièce lus (ceux du tableau ci-dessus) ; compteurs de 579 ; 6 lignes d’entité à 3 actions « cette entité » ; 3 actions d’équipement ; sélecteur de 5369 grisé |
| Exclusion (eq 287) | **PASS** | actions d’entité masquées ; compteurs de 287 lus ; exclusion puis retour au mode automatique simulés, aucune écriture transmise |
| Référence (eq 380, commande 2971) | FAIL, puis **PASS** | premier passage : liste de 2971 = `cover` seul, puis échec `parcours-record-valeur-invalide`. Le parcours enregistrait le texte entier de la cause (environ 90 caractères), alors que le rapport en accepte 80. Correctif #258 (`9319784`, tests seulement, aucun déploiement) ; repassé à 11:53 : **PASS**. Liste = `cover` seul, cause lisible, bascule simulée « prête » puis retour automatique « bloquante », compteurs restitués, aucune écriture |
| Contrôle négatif | **FAIL attendu** | une seule requête `saveMappingOverride` non déclarée, bloquée (`block-fail`) ; box inchangée |

Pour tous les passages, la box est inchangée (`ac3_2_box`) et aucune écriture n’a été transmise.
