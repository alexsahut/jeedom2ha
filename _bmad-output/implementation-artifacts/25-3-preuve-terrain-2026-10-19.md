# Story 25-3 — preuve de terrain (2026-10-19)

> **Statut de ce document.** Rédigé par ClaudeBox le 19/10/2026 entre 06:15 et 06:40 (Task 8), pendant l'autonomie de nuit déléguée par Alexandre.
> - Il ne cite que des identifiants (CC-48).
> - Vérifications en lecture seule : gate 20-0, journal du démon, registre de HA.
> - Seuls les déploiements ont écrit sur la box ; c'est clawcode qui les a faits.
> - **Aucune manipulation du secret local.**

## Ce qui est déployé

| Élément | Valeur |
|---|---|
| Premier déploiement | `ebec48b` (#293, dev 25.3), le 19/10 à 05:18. Démon redémarré, 0 ligne `ERROR`, topics MQTT 348 → 348. |
| **Déploiement final** | **`030d6e8e9fbd74ba1f9f171cdba1378c80eb4cc8`** (`main` après #296 et #297), le 19/10 à 06:09 (heure de Paris). Commande : `./scripts/deploy-to-box.sh --sha <complet> --restart-daemon`, depuis un worktree neuf en HEAD détaché. Garde-fous CC-56 (SHA = HEAD) et CC-50 (CI verte, le script a attendu la fin de la CI de `main`) passés. |
| Démon | **0 ligne `ERROR`** après le redémarrage. |
| Jeedom | 4.6.1 |

## Régression trouvée par le gate, puis corrigée (#296)

Le premier passage du gate sur `ebec48b` a révélé **une vraie régression d'interface** :
- **Symptôme.** Dans la fenêtre de pièce, le contrôle segmenté « Automatique | Toujours | Jamais » de 25.1 était réduit à 2 px.
- **Cause.** Les règles CSS des segments de jauge de 25.3 visaient `.j2ha-seg` (`flex-basis: 0; min-width: 2px`) sans passer par `.j2ha-gauge`. Or `.j2ha-seg` est aussi la classe du conteneur `role=radiogroup` de ce contrôle.
- **Effet.** Le contrôle était invisible et inutilisable pour l'utilisateur. Le parcours `exclusion-publication-non-publiee` a échoué sur un clic expiré.

**Correctif (#296, `aed7e70`) :**
- toutes les règles de segment de jauge passent sous `.j2ha-gauge .j2ha-seg` ;
- nouveau test de non-régression `test_story_25_3_css_seg_collision`. Il échoue sur l'ancien `main` et passe avec le correctif.

**Le gate a joué son rôle** : les suites locales et le navigateur réel simulé ne couvraient pas la fenêtre de pièce stylée avec la jauge.

Deux autres échecs du premier passage venaient **des parcours, pas du produit** :
- **#294** : `page-principale-b` comptait les requêtes du cœur Jeedom (`event.ajax.php`, `changes`) comme des requêtes du plugin pendant les filtres. Le comptage se limite désormais au relais du plugin. Le harnais local a été aligné en #295.
- **#297** : `page-principale-b` fermait la boîte « Télécharger le diagnostic » par Échap. Sous Bootstrap, Échap dépend du focus posé en fin d'animation, d'où l'expiration après 30 s à l'étape 6. La story n'exige pas Échap. La fermeture passe désormais par le bouton « Fermer », et les raisons d'échec sont distinctes.

Aucune assertion n'a été retirée et aucune politique n'a été relâchée (AC17). `test_story_20_0_gate_policy` et les suites 25.3 sont verts en CI.

## Gate 20-0 sur la box (AC17, Task 8.1)

Les résultats retenus sont ceux du dernier passage de chaque parcours sur le SHA qui le concerne. Les rapports sont sur la VM, dans `jeedom2ha-gate/reports/25-3-2026-10-19/`.

| Parcours | SHA | Verdict | Points relevés |
|---|---|---|---|
| `controle-ecriture-non-declaree` | `ebec48b` | **FAIL attendu** (contrôle négatif) | L'écriture non déclarée est bien bloquée. |
| `decouverte-piece-25-eq-579` | `ebec48b` | **PASS** | Compteurs de pièce et d'équipement cohérents ; 0 chaîne interdite ; pseudo-pièce « Sans pièce » présente. |
| `rescan-page-principale` | `ebec48b` | **PASS** | Confirmation ouverte depuis la barre de santé ; rescan simulé ; retour par toast. |
| `reference-bascule-eq-380` | `85d2fbb` | **PASS** | Au premier passage, le journal du démon avait été tronqué en place (« bornes-journal-invalides »). Le relancer a suffi. |
| `exclusion-publication-non-publiee` | **`030d6e8`** | **PASS** | Il échouait sur `ebec48b` à cause de la régression CSS. Le parcours complet, de l'exclusion au retour en automatique, passe désormais sur le correctif. |
| `page-principale-b` | **`030d6e8`** | **PASS** | Voir le détail ci-dessous. |

Contrôles communs à tous les PASS :
- `ac3_1` à `ac3_5` verts (interception, état de la box, console, journaux, rapport) ;
- aucune écriture transmise ;
- 0 `ERROR` du démon ou du plugin pendant la fenêtre ;
- console vide.

**Parcours `page-principale-b` sur `030d6e8` (assertions (1) à (7) de l'AC17) :**

| Étape | Mesure |
|---|---|
| (1) chargement | **1** `getEquipmentStates` sans `refresh`, **0** `getMappingOverrides` |
| (2) bandeau bleu | absent |
| (3) jauges | maison = **292** équipements, **24** cartes dont chacune somme à son total |
| (4) filtres | **3** puces non vides cliquées, **0** requête du plugin pendant les filtres |
| (5) Actualiser | **1** `getEquipmentStates` avec `refresh=1`, seul de la session |
| (6) menu « ⋯ » | deux entrées dans l'ordre ; boîte diagnostic ouverte puis fermée ; « Supprimer tout… » actif, confirmation ouverte puis annulée ; **0 écriture** |
| (7) fenêtre de pièce | ouverte depuis une carte, **6** équipements affichés |

## Taille et temps (AC7, Task 8.2)

D'après le journal du démon, chaque lecture d'état sur `ebec48b` puis sur `030d6e8` a reconstruit une réponse de la même taille :

| Date (heure de Paris) | Origine | `build_ms` | `bytes` | Équipements | `unread` |
|---|---|---|---|---|---|
| 05:19:33 | première lecture après le déploiement de `ebec48b` | 167,4 | 1 342 346 | 292 | 0 |
| 05:25:42 | pendant le gate | 164,4 | 1 342 346 | 292 | 0 |
| 05:43:05 / 05:43:06 | pendant le gate page-B (chargement, puis Actualiser avec `refresh=1`) | 161,1 / 157,6 | 1 342 346 | 292 | 0 |
| 06:09:34 | première lecture après le déploiement de `030d6e8` | 150,4 | 1 342 346 | 292 | 0 |
| 06:11:28 | pendant le gate page-B | 158,0 | 1 342 346 | 292 | 0 |

**Comparaison avec 25.2 et les budgets de Q10 :**
- **Taille côté démon.** 1 342 346 octets, **identique** à la mesure de 25.2, soit 89 % du budget de 1 500 000. Le seuil de vigilance Q8 de 1 350 000 octets n'est pas atteint. 25.3 ne modifie ni la liste blanche ni les budgets (AC7).
- **Construction côté démon.** 150 à 167 ms, contre 172 à 185 ms en 25.2. Le budget est tenu.
- **Bout en bout depuis la page B.** Le gate prouve que le chargement ne fait qu'**un** appel et que la page B s'affiche avant que chaque étape soit évaluée. Il ne chronomètre pas cet appel. La mesure chronométrée passe par le parcours `mesure-equipment-states` de 25.2, qui suit le même chemin (navigateur → relais PHP → démon) : voir § Mesure chronométrée.

### Mesure chronométrée

**Non refaite cette nuit.** La relance du parcours `mesure-equipment-states` a été demandée deux fois à clawcode, à 06:16 et à 06:23, mais ses tours n'ont pas abouti. Il n'y a donc pas de nouveau chronométrage bout en bout.

Ce qui permet de reporter les chiffres de 25.2 :
- la route, le relais et la liste blanche sont inchangés (AC16 : aucun fichier de `resources/daemon/` ni de `core/ajax/` modifié) ;
- la taille servie est identique, à l'octet près ;
- la construction côté démon est plus rapide (150 à 167 ms, contre 172 à 185 ms).

Les chiffres de 25.2 sont : froid 314 ms, chaud 136 à 322 ms, pour des budgets de 6 s et 500 ms. **Aucun budget n'est dépassé.** Le chronométrage depuis la page B reste une **réserve**, à relever avec 25.4 ou pendant la validation UX.

## Ce qui n'est pas prouvé par cette note (Tasks 8.3 et 8.4)

Le gate interdit toute écriture, et ClaudeBox ne manipule pas la box en écriture hors déploiement. Restent donc à vérifier à la main, pendant la validation UX d'Alexandre portée par **25.5** :
- **8.3, relecture après écriture et après synchro.** Vérifier que les chiffres de la page B changent sans `refresh=1` après l'enregistrement d'un réglage dans la fenêtre de pièce, puis après « Relire Jeedom ». Cette mesure avait été laissée par 25.2. Pour l'instant, elle n'est prouvée que par les tests de #288 (invalidation du cache côté démon) et de #293 (relecture côté page après chaque événement terminé, coalescence).
- **8.4, rendu visuel.** Thème sombre de Jeedom 4.6.1, icônes et couleurs réelles des objets. Le gate a ouvert la page sans erreur de console. Le contrôle visuel revient à Alexandre.

## Bilan

La page principale B est en place sur la box :
- **tous les parcours du gate sont verts** sur le SHA final ;
- le contrôle négatif échoue comme attendu ;
- le démon ne remonte aucune erreur ;
- la taille de la réponse ne bouge pas.

Le gate a trouvé une régression réelle du contrôle segmenté, corrigée et déployée avant cette note.

**25-3 passe à `ready-for-UX-validation`**. La validation UX finale d'Alexandre sur A + B + C est portée par 25.5 (AC18). Les réserves sont listées ci-dessus : 8.3 et 8.4 à vérifier à la main, chronométrage bout en bout à refaire depuis la page B.
