# Story 25-4 — preuve de terrain (2026-10-19)

> **Statut de ce document.** Rédigé par ClaudeBox le 19/10/2026 vers 13:15 (Task 11).
> - Il ne cite que des identifiants (CC-48).
> - Vérifications en lecture seule : gate 20-0, journal du démon, code du cœur Jeedom sur la box.
> - Seuls les déploiements ont écrit sur la box, et c'est clawcode qui les a faits.
> - **Aucune manipulation du secret local.**

## Ce qui est déployé

| Élément | Valeur |
|---|---|
| Premier déploiement | `0a71a05` (#301, dev 25.4), le 19/10 à 11:45 (heure de Paris), CI attendue. 0 ligne `ERROR` dans le démon. Un seul topic MQTT ajouté : le bouton du scénario 147, réactivé dans Jeedom. Cet ajout vient de 21-1 (CC-44), pas de 25.4. |
| **Déploiement final** | **`90d417783c071a25181f9df9b580fa619ea3e82a`** (`main` après #302), le 19/10 à 12:35. Commande : `./scripts/deploy-to-box.sh --sha <complet> --restart-daemon`, depuis un worktree neuf en HEAD détaché. Garde-fous CC-56 et CC-50 passés. **0 ligne `ERROR`** dans le journal du démon. |
| Parcours seul | `5789c04` (#303) : correctif du parcours uniquement, **sans redéploiement**. La box reste sur `90d4177`, ce que confirme le relevé du SHA déployé dans `DONE3`. |

Les fichiers `DONE` et `DONE2` annoncent 3 et 4 lignes `ERROR`. Ce sont les refus de déployer du script de clawcode, qui attendait la fin de la CI de `main`. Le journal du démon n'en contient aucune (`grep ERROR` vide).

## Défaut trouvé par le gate, puis corrigé (#302)

- **Le gate a échoué** sur `0a71a05`, parcours `vue-maitre-detail-c`, étape 8 (« Précédent ») : `precedent-ne-remonte-pas`.
- **L'interception a bloqué** une requête non inscrite, `GET /index.php` avec les clés `v, m, p, ajax`.
- **Cause, lue dans le code du cœur sur la box** (`desktop/common/js/utils.js`, l. 290-309) : le cœur écoute `popstate`. Dès que `event.state !== null`, il recharge la page par `jeedomUtils.loadPage`. La vue poussait `{ j2ha: n }`, donc **chaque « Précédent » rechargeait la page**. C'est exactement la réserve Q1 de la story.
- **Correctif (#302, `90d4177`)** :
  - les entrées d'historique portent un état `null`. Avec un état `null`, le cœur se contente de chercher un onglet `.nav-tabs` portant ce fragment, et il n'y en a aucun ici ;
  - la profondeur est tenue par la vue elle-même (pile `st.hist`, position `st.pushed`) ;
  - un test de cohabitation simule l'écouteur du cœur : rouge avant le correctif, vert après.
- **Relecture Codex de #302** : elle a trouvé un cas dérivé, corrigé dans la même PR (`a2b8fee`) avec son test. Il s'agissait de « Précédent » jusqu'à la page principale, puis « Suivant », puis « Toutes les pièces ».

**Défaut de parcours (#303).** Après le redéploiement, l'étape 6 (« lien profond ») a échoué sur un comptage. C'était une course : au rechargement, l'arbre unitaire (environ 70 ms) était rendu avant que la lecture des états (environ 300 ms) n'arrive au journal. L'interception comptait pourtant le même total de 8 lectures. Le parcours attend désormais les deux lectures, puis exige une égalité stricte. L'exigence n'est pas relâchée.

## Gate 20-0 sur la box (AC27 à AC29)

Rapports sur la VM, dans `jeedom2ha-gate/reports/25-4-2026-10-19/`.

| Parcours | SHA déployé | Verdict | Points relevés |
|---|---|---|---|
| `controle-ecriture-non-declaree` | `0a71a05` | **FAIL attendu** | L'écriture non déclarée est bloquée (`block-fail`, `ecriture-override-non-declaree`). |
| `decouverte-piece-25-eq-579` | `0a71a05` | **PASS** | Le parcours passe par la vue C, sans modale. Aucun équipement « non lu » dans la pièce 25 ni dans « Sans pièce » (invariant de la R1, P2-3). |
| `exclusion-publication-non-publiee` | `0a71a05` | **PASS** | Sélection par l'arbre, exclusion simulée, retour au mode automatique, aucune confirmation inattendue. |
| `reference-bascule-eq-380` | `0a71a05` | **PASS** | L'étape « sélection » remplace le dépliage de l'accordéon, avec les mêmes étiquettes. |
| `rescan-page-principale` | `0a71a05` | **PASS** | |
| `page-principale-b` | **`90d4177`** | **PASS** (aussi sur `0a71a05`) | L'étape 7 ouvre la vue C depuis une carte. |
| `vue-maitre-detail-c` | **`90d4177`**, parcours `5789c04` | **PASS** | Voir le détail ci-dessous. |

Tous les PASS ont les contrôles `ac3_1` à `ac3_5` verts. Aucune écriture n'est transmise et aucune requête n'est bloquée.

**Parcours `vue-maitre-detail-c` (AC29)**

| Étape | Mesure |
|---|---|
| (1) ouverture depuis une carte | **0** `getEquipmentStates`, **0** `getMappingOverrides` |
| (2) arbre | **24** pièces ; repères qui somment aux nombres de la page B (18 « bloqués ») |
| (3) recherche et filtres | **3** puces non vides, **0** requête du plugin |
| (4) sélection d'un équipement | **1** `getMappingOverrides`, rendu en **61 à 67 ms** ; pastille de l'arbre = badge du détail |
| (5) réponse tardive ignorée | portée par le test en vrai Chromium (`test_story_25_4_*`), comme décidé (§ Décisions, précision 1) : l'interception du gate ne retarde pas une réponse à la demande |
| (6) lien profond après rechargement | **1** `getEquipmentStates` + **1** `getMappingOverrides`, même sélection rouverte |
| (7) disposition | `split` à 1 180 px, `compact` à 780 px ; aucun défilement horizontal du détail ; le tiroir « Pièces » s'ouvre et se ferme ; **0** requête |
| (8) « Précédent » | remonte **2 niveaux** : équipement → pièce → page principale, **sans rechargement par le cœur** |
| (9) menu « ⋯ » de pièce | « Supprimer de Home Assistant… » grisé sur la pièce testée ; **0** écriture |

## Taille et temps (AC32)

D'après le journal du démon (`[AGGREGATE]`), chaque lecture d'état depuis le déploiement de `0a71a05` porte sur 292 équipements :
- 0 non lu ;
- **1 342 346 octets**, identique à 25.2 et à 25.3 ;
- construction en **145 à 205 ms**.

25.4 ne modifie ni la liste blanche ni les budgets. Le seuil de vigilance Q8 de 1 350 000 octets n'est pas atteint.

Le temps de rendu d'un équipement sélectionné, de la sélection au tableau des commandes, est de **61 à 67 ms** sur le parc réel. Le parcours l'enregistre sans seuil. C'est un premier relevé de bout en bout depuis l'interface, en complément des réserves de chronométrage de 25.3.

## Ce qui n'est pas prouvé par cette note

- **iPad mural en mode bureau.** Sa largeur CSS réelle n'a pas été relevée. Le seuil retenu (980 px, mesuré par la session de dev) peut être révisé par une PR de suite, à l'occasion de la validation UX.
- **Rendu visuel.** Thème sombre et clair, icônes et couleurs réelles, contrastes : le contrôle est à faire par Alexandre en 25.5.
- **Écritures réelles depuis la vue C.** Réglages, Appliquer, Republier et Supprimer ne sont pas vérifiés sur la box. Le gate interdit toute écriture. Les corps des requêtes sont prouvés identiques à `main` par le test de contrat (15 scénarios, AC8).
- **« Relire Jeedom » avec la vue ouverte.** Pas de vérification sur la box. Le comportement attendu, sans rechargement de la page, est décrit au Dev Agent Record (Task 3.4).

## Bilan

La vue maître-détail C remplace la fenêtre de pièce sur la box.
- **Tout le gate est vert** sur le SHA final, et le contrôle négatif échoue comme attendu.
- Le démon ne remonte aucune erreur et la taille de la réponse ne bouge pas.
- Le gate a trouvé **un vrai défaut produit** : « Précédent » rechargeait la page à cause du `popstate` du cœur Jeedom. Il est corrigé et redéployé avant cette note.

**25-4 passe à `ready-for-UX-validation`.** La validation UX finale d'A + B + C, y compris l'iPad mural, est portée par **25.5** (AC34). Les réserves sont listées ci-dessus.
