# Story 25-1 — preuve de terrain (2026-10-18)

> **Statut de ce document.** Rédigé par ClaudeBox le 18/10/2026 vers 23:40, versé au dépôt avec la clôture de la story 25.1 (Task 8). Il ne cite que des identifiants : aucun nom d’équipement, de pièce, de scénario ni de personne (règle CC-48). Toutes les vérifications ont été faites en lecture seule : registres des appareils et des entités de HA, journal du démon, fichiers de version, rapports du gate 20-0. Seuls les déploiements ont écrit, et c'est clawcode qui les a faits.

## Ce qui est déployé

| Élément | Valeur |
|---|---|
| Premier déploiement | `a704dd0` (`main` après #279 : 25.1 + R1), le 18/10 à 22:10 (heure de Paris), `deploy-to-box.sh --sha <complet> --restart-daemon`, CI verte |
| Second déploiement (en place) | `c940ac3` (`main` après #282 : R2, contraste des segments et « Désactivé » prioritaire sur « Exclu »), le 18/10 à 22:31 |
| Démon | redémarré à 22:31, MQTT connecté, **0 ligne `ERROR`** dans `jeedom2ha_daemon` (relu à 22:45) |
| Sync | `total_eq=292 eligible=96 published=263` aux deux déploiements |
| Jeedom | **4.6.1** (`core/config/version` de la box) |

## Inventaire MQTT

- Déploiement de 22:10 : 347 → 350 topics. Trois boutons de scénarios (129, 147 et 40) ont été republiés, parce que ces scénarios ont été réactivés côté Jeedom. Sans lien avec 25.1.
- Déploiement de 22:31 : 350 → 349. Le bouton du scénario 129 a été retiré, car ce scénario est de nouveau désactivé dans Jeedom. C'est le comportement prévu par 21-1 (CC-44), déjà constaté le 12/10 (preuve 22-2).

25.1 ne modifie pas le démon (AC22). Aucun topic n'a été ajouté ni retiré par cette story.

## Registres de HA

Relevé du 18/10 à 22:47.

| Contrôle | Valeur |
|---|---|
| Entités jeedom2ha | 349 |
| Appareils jeedom2ha | 178 |
| Entités créées depuis 22:00 | **0** |
| Entités modifiées depuis le déploiement de 22:31 (`c940ac3`) | **0** |
| Appareils modifiés depuis le déploiement de 22:31 | **0** |
| Entités modifiées par le déploiement de 22:10 (`a704dd0`) | **169**, toutes à 22:10:19, aucun `entity_id` changé |
| Appareils modifiés par le déploiement de 22:10 | 2 |

**Les 169 entités modifiées à 22:10 relèvent de 22-3, pas de 25.1.** Le correctif 22-3 (#267, `2b7a058`, « pas de nom d'entité identique au nom de l'appareil ») a été fusionné le 12/10 mais n'avait jamais été déployé. Le déploiement de 22:10 l'a donc mis en service. Constat sur les 349 entités :
- les 169 modifiées ont toutes `original_name = null`. HA leur donne seulement le nom de l'appareil : le nom doublé « X X » a disparu, ce qui est l'effet attendu de 22-3 (AC1) ;
- les 180 autres ont toutes un `original_name` non nul et n'ont pas bougé (AC3) ;
- aucun nom posé par l'utilisateur dans HA (`name`) n'est touché, et aucun `entity_id` ne change.

La story 22-3 comptait 131 entités concernées le 12/10 ; l'écart avec 169 n'est pas analysé ici (parc et scénarios ont bougé depuis). Ce relevé tient lieu de constat terrain pour les AC1 et AC3 de 22-3. Le statut de 22-3 n'est pas modifié ici : l'essai vocal du scénario 38 reste à faire avec Alexandre.

## Écran du plugin (thème sombre, 4.6.1)

Contrôle visuel du 18/10 à 22:20 sur `a704dd0`, puis à 22:35 sur `c940ac3`.

**Deux défauts trouvés sur `a704dd0`, corrigés par la R2 (#282) :**
- le segment « Jamais », quand il est disponible, était presque invisible en sombre : texte `rgb(51,51,51)` sur fond `rgb(25,25,25)` ;
- l'équipement 164, désactivé dans Jeedom, s'affichait « Exclu ».

**Après `c940ac3`, vérifié à l'écran :**
- le segment « Jamais » s'affiche en `rgb(172,172,172)` (`--txt-color`) ; « Toujours », indisponible, est atténué ;
- l'équipement 164 s'affiche « Désactivé » ;
- compteurs de la pièce de l'équipement 164 : 9 publiés · 2 bloqués · 10 exclus · 1 désactivé.

Retour d'Alexandre sur l'écran déployé (18/10 à 22:36) : « c'est top ! ». La validation UX formelle reste portée par 25.5.

## Gate 20-0

Passage du 18/10 de 22:53 à 23:03 sur `c940ac3` déployé, depuis un worktree neuf de `main` à `c83cc86` en HEAD détaché, sous le compte dédié. Les 5 parcours ont été lancés en série, un seul essai de connexion chacun.

| Parcours | Verdict | Constats |
|---|---|---|
| Découverte (pièce 25, eq 579) | FAIL, puis **PASS** | Voir (1) ci-dessous |
| Exclusion (eq 287) | **PASS** | Compteurs de 287 : « 2 bloquées », « 1 ignorée ». Actions d'entité masquées. Exclusion (`savePublicationOverride`) puis retour automatique (`revertPublicationOverride`) simulés, relecture dérivée, aucune écriture transmise |
| Référence (eq 380, commande 2971) | FAIL, puis **PASS** | Voir (2) ci-dessous |
| Rescan (page principale) | **PASS** | Confirmation ouverte, `scanTopology` simulé, retour en toast « succès » |
| Contrôle négatif | **FAIL attendu** | Une seule requête `saveMappingOverride` non déclarée, bloquée (`block-fail`, `ecriture-override-non-declaree`), box inchangée |

Sur tous les passages, la box reste inchangée :
- `ac3_2_box` vrai ;
- aucun marqueur d'écriture dans le journal du démon pendant la fenêtre ;
- 0 `ERROR` dans `jeedom2ha_daemon` et dans `jeedom2ha`.

La console reste sans erreur, sauf la requête bloquée attendue du contrôle négatif.

**(1) Découverte, `selecteur-5369-sans-explication`.** Le lien de type de 5369 était bien désactivé (`aria-disabled=true`), mais son attribut `title` était vide au moment de la lecture. Un parcours de diagnostic en lecture seule (23:1x, PASS) relève ce `title` : « Cette commande est portée par plusieurs entités : le type Home Assistant choisi ne s’appliquerait qu’à l’entité principale de l’équipement. Réglage indisponible ici. ».

Cause : une course de lecture dans le parcours. Le cœur Jeedom 4.6.1 (`desktop/common/js/utils.js:1042`, `jeedomUtils.initTooltips`) déplace `title` vers `data-title` quand il pose ses infobulles. L'explication reste affichée en infobulle : il n'y a pas de défaut produit. Correctif côté tests seulement : #283, fusionnée `d7450ea`, qui lit `title` puis `data-title`.

Constats du passage :
- « 5 publiées », « 1 ignorée » ;
- 6 entités, chacune avec son contrôle « Automatique | Toujours | Jamais » ;
- contrôle d'équipement à 3 segments ;
- 20 équipements sans pièce ;
- 0 chaîne interdite.

**(2) Référence, `synthese-bascule-encore-bloquante`.** La cellule de 2971 passe bien de « bloquée » à « à appliquer » après la bascule simulée vers `cover` : liste filtrée réduite à `cover`, cause lisible, aucune écriture. Mais la synthèse de l'équipement affiche « Rien à publier » au lieu de « À appliquer ».

Cause : la lecture dérivée du gate (`deriveOverrideTree`, `simulate.mjs`) ne recalcule jamais `sync_status`. C'est un choix arbitré par ClaudeBox le 02/10 : le gate ne prouve pas le badge « pas encore appliqué ». Or l'état unique de 25.1 (`resolveEquipmentState`) lit `current_should_publish` et `override_pending`. Le démon réel recalcule ces deux champs après un enregistrement (tests `test_story_19_3_ac6_sync_status.py`). L'écran réel affichera donc « À appliquer ».

Correctif côté tests seulement, toujours #283 : le parcours accepte « Rien à publier » en simulation, et le commentaire porte la limite.

**Relance des deux parcours sur `main` à `d7450ea`** (worktree neuf, HEAD détaché) :

- **Découverte : PASS** (23:3x). Le sélecteur de 5369 est désactivé, avec son explication. Les 5 commandes visibles de 579 sont publiées ; synthèse « Publié ».
  - Badges de la pièce 25 : 199, 131, 277, 326, 554, 553, 579, 592 et 639 publiés ; 287 bloqué ; 183, 228, 338, 341, 329 et 559 exclus ; 339 et 514 désactivés.
  - Compteurs de la pièce 25 : 9 publiés · 1 bloqué · 6 exclus · 2 désactivés.
  - Compteurs de « sans pièce » : 1 publié · 3 bloqués · 12 exclus · 3 désactivés · 1 rien à publier.
  - Aucune chaîne interdite.
- **Référence, premier relancement : FAIL**, sur `bornes-journal-invalides`. Le journal du démon a été tronqué en place pendant la fenêtre par la maintenance des journaux de Jeedom. Le témoin était donc illisible, alors que le parcours lui-même était entièrement vert. La doc 20-0 prévoit une relance dans ce cas.
- **Référence, second relancement : PASS** (23:4x).
  - Synthèse : « Bloqué » au départ, « Rien à publier » après la bascule simulée (limite décrite plus haut), « Bloqué » de nouveau après le retour automatique.
  - Compteurs restitués.
  - Aucune écriture transmise, 0 `ERROR`, box inchangée.

Avec l'exclusion, le rescan et le contrôle négatif du premier passage, **le gate 20-0 est vert pour 25.1**. Rapports hors dépôt : `~/.openclaw/tools/jeedom2ha-gate/reports/25-1-2026-10-18/` sur la VM openclaw.

## Ce qui n'est pas prouvé ici

- **Thème clair sur la box.** La box et le compte du gate sont en thème sombre. Passer en clair demanderait d'écrire la configuration Jeedom, ce qui est exclu. Les contrastes du thème clair sont couverts par `test_story_25_1_palette_theme.node.test.js` (AC19, fonds blanc et `#f5f5f5`). Le rendu clair réel est reporté à la recette 25.5.
- **Jeedom 4.4.** Aucune instance 4.4 n'est disponible : la box est en 4.6.1, et le clone de répétition est injoignable et lui aussi issu de la box. Restent à contrôler sur 4.4 la cible `index.php?v=d&p=types` (Q5) et les replis `--j2ha-*` des variables du cœur (AC25). C'est reporté à 25.5, ou à un bêta-testeur en 4.4.

## Bilan

AC1 à AC27 sont tenus sur la box 4.6.1, en thème sombre, d'après les suites locales (640 tests Node), le gate et le contrôle visuel. Deux points restent hors de cette preuve : le rendu réel du thème clair et Jeedom 4.4 (voir ci-dessus). Le gate 20-0 est vert après le correctif de tests #283. Aucune publication HA n'est modifiée par 25.1. 25-1 passe à `ready-for-UX-validation`, et la validation finale est transférée à 25.5. 22-2 passe à `done` (superseded), comme le prévoit Q1 du cadrage de l'epic 25.
