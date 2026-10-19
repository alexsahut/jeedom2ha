# Story 25.6 : Vue C filtrée sur la pièce d'entrée

Status: ready-for-UX-validation

> **Statut : `ready-for-dev` (2026-10-19 17:40, relecture et décisions ClaudeBox ; Alexandre présent, peut revenir sur une décision).** Précédemment : **`backlog` (2026-10-19).** Story rédigée par une session cloud déléguée (`create-story`, documentaire : aucun code, aucun test, aucune fixture, aucun accès box / VM / Home Assistant / SSH / secret, CC-48), à partir du sprint change `sprint-change-proposal-2026-10-19-revue-ux-25.md` (statut **decided**, décision **D2**). **`ready-for-dev` n'est pas accordé** : relecture de la story par ClaudeBox, puis décisions sur Q1 à Q7 (§ Questions ouvertes, chacune avec une recommandation argumentée ; la session n'en tranche aucune). **Statut cible après implémentation et preuve terrain : `ready-for-UX-validation`** (et non `done`) ; la validation UX finale est portée par **25.5**. Les points de § Décisions déjà arbitrées sont **fermés**. Pointeurs de code pris sur `main` à `731be8d` (après 25.4 : #301 `0a71a05`, #302 `90d4177`, #303 `5789c04`, preuve terrain #304, sprint change #305) ; **à re-vérifier au SHA courant** avant le `dev-story`. Aucun nom réel d'équipement, de pièce, d'objet, de scénario ou de personne : identifiants et données fictifs seulement (CC-48).

## Story

En tant que propriétaire qui ouvre une pièce depuis sa carte sur la page principale,
je veux que la vue de travail (C) n'affiche **que cette pièce** dans son arbre, avec un bouton « Toutes les pièces » pour élargir,
afin de voir tout de suite la pièce que je viens de choisir, sans qu'elle reste hors écran au milieu des autres pièces.

**Parcours : interface (`desktop/js/`, `desktop/css/`), docs, tests Node, gate 20-0.** Aucune modification du démon, du relais ajax ni de `core/class/` (AC12). Aucune requête réseau ajoutée (AC6).

**Dépendances :** 25.4 (`ready-for-UX-validation`, déployée `90d4177`) — la vue C, son état d'URL et sa pile d'historique sont le socle modifié ici. **Première story de l'extension** décidée le 19/10 : 25.6 → 25.7 → 25.8 → 25.9 → 25.5. 25.7 et 25.8 modifient les mêmes fichiers (`jeedom2ha_workview.js`) : elles partent de la branche fusionnée de 25.6.

## Décisions déjà arbitrées

Ces points sont **fermés** ; la story les applique sans les rediscuter. Source entre parenthèses.

1. **D2 — Filtrer sur la pièce.** Depuis une carte, l'arbre de la vue C n'affiche que cette pièce ; un bouton « Toutes les pièces » élargit à toute la maison. (Sprint change 19/10, D2, décision d'Alexandre 13:50.)
2. **L'état est porté par le fragment d'URL** `#j2ha-vue=…`, déjà en place (25.4 AC18, Q1 A). Les entrées d'historique de la vue portent **toujours un état `null`** : le cœur Jeedom recharge la page sur tout `popstate` dont l'état n'est pas `null` (`desktop/common/js/utils.js`, défaut trouvé par le gate et corrigé en #302). La profondeur reste tenue par la vue (`st.hist`, `st.pushed`). (25.4 Change Log 12:20, `25-4-preuve-terrain-2026-10-19.md`.)
3. **Zéro requête supplémentaire** : ouvrir, filtrer sur la pièce, élargir, revenir ne lisent ni `getEquipmentStates` ni `getMappingOverrides`. (Sprint change, découpage ; 25.4 D2, AC5, AC10.)
4. **Gate 20-0 adapté sans affaiblissement**, avec le **registre d'assertions de 25.4** (`tests/fixtures/story_25_4_gate_assertions.json`) comme plancher : aucune entrée ne disparaît, ajouter est permis. `lib/policy.mjs` inchangé. (Sprint change ; 25.4 AC27.)
5. **Source de vérité unique de l'état** : `resolveEquipmentState`, `summarizeRoom`, `summarizeHouse` ; aucune règle d'état réécrite. (25.1 D1, 25.4 AC4.)
6. **Vocabulaire, palette, thème** : glossaire de 25.1, variables `--j2ha-*`, aucune couleur en dur ; CSS nouveau sous `.j2ha-wv` / `.j2ha-wv-*`, aucun sélecteur nu sur une classe partagée (leçon #296). (25.1 D4, D5 ; 25.4 AC23 à AC25.)
7. **Statut cible : `ready-for-UX-validation`**, validation UX finale en 25.5. (Epic 25.)

## Sources lues

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-19-revue-ux-25.md` (déclencheur point 2, D2, découpage) ; `…/ux/2026-10-18-refonte-surface/epic-25-draft.md` ; `_bmad-output/planning-artifacts/epics-projection-engine.md` § Epic 25 ; `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- `25-4-vue-maitre-detail-c.md` (D1 à D4, AC5, AC7, AC10, AC11, AC13, AC17, AC18, AC27 à AC29, Q1, Q7, Q13, Q14, Change Log) et `25-4-preuve-terrain-2026-10-19.md` (défaut « Précédent » / `popstate` du cœur, #302 ; parcours `vue-maitre-detail-c` 9/9) ; `25-3-page-principale-b.md` (D3, filtres) ; `25-1-…` (glossaire).
- Code (lecture seule, `main` `731be8d`) : `desktop/js/jeedom2ha_workview.js` (fragment `parseFragment` `:41`, `formatFragment` `:63`, `resolveFragment` `:73` ; `buildTreeModel` `:119` ; coquille `build` `:297`, bouton `.j2ha-wv-back` libellé « Toutes les pièces » `:305-306` ; `syncUrl` `:440`, `goBack` `:460`, `onPop` `:469` ; `selectRoom` `:497`, `selectEquipment` `:515`, `open` `:598`, `reconcile` `:630`, `renderChips` `:652`, `renderTree` `:742` ; `onPageRender` `:995` (`syncUrl('replace')` au changement de filtre) ; `window.j2haOpenRoom` `:1020`) ; `desktop/js/jeedom2ha_overview.js` (`computeOverview` `:79`, `chipsFor` `:66`, `openRoom` `:637`, ligne de liste filtrée `openEquipmentView` `:436`) ; `tests/e2e/gate/parcours/vue-maitre-detail-c.mjs` (étapes 1 à 9, `checkTree` `:72`), `decouverte-piece-25-eq-579.mjs`, `page-principale-b.mjs` (étape 7), `exclusion-publication-non-publiee.mjs` ; `tests/unit/test_story_25_4_etat_url.node.test.js`, `…_navigation…`, `…_glossaire…`, `…_documentation…`.

## Contexte et périmètre

### Ce qui existe aujourd'hui (relevé sur `731be8d`, à re-vérifier au SHA courant)

- Un clic sur une carte appelle `j2haOpenRoom(id)` → `open({ room: id })` : la vue C s'ouvre **sur toute la maison**, la pièce est sélectionnée et dépliée, mais l'arbre garde toutes les pièces dans l'ordre de la grille ; dans une maison de plus de 20 pièces, la pièce choisie peut être hors de la zone visible de l'arbre (constat d'Alexandre, 19/10 13:33).
- Le bouton d'en-tête `.j2ha-wv-back` porte déjà le libellé **« Toutes les pièces »** et **revient à la page principale** (`goBack`). Le libellé décidé par D2 pour élargir l'arbre est le même : il faut le libérer (Q1).
- Fragment : `#j2ha-vue=piece:P;eq:E;f:F` ; toute clé inconnue invalide le fragment entier (`parseFragment`) ; une sélection pousse une entrée (`syncUrl('push')`), un changement de filtre remplace l'entrée courante (`syncUrl('replace')`).
- Puces de l'arbre : celles de la page B, mêmes effectifs maison (`chipsFor(overview.counts)`), filtre partagé B ↔ C (25.4 Q7 A).

### Dans le périmètre

- notion de **portée** de la vue C (« cette pièce seule » / « toutes les pièces ») et ses règles d'entrée (AC1 à AC3) ;
- bouton « Toutes les pièces » pour élargir, et nouveau libellé du bouton de retour (AC4, Q1) ;
- portée dans le fragment d'URL, historique, lien profond (AC5) ;
- zéro requête (AC6) ; recherche, filtres et KPI dans la portée (AC7) ; disposition étroite (AC8) ; relectures et disparition de pièce (AC9) ;
- accessibilité, glossaire, CSS (AC10) ; gate 20-0 (AC11) ; non-régression, documentation, conventions, statut (AC12 à AC15).

### Hors périmètre (ne pas faire ici)

- toute modification de `resources/daemon/`, `core/ajax/`, `core/class/`, `tests/e2e/gate/lib/policy.mjs`, des artefacts figés et de la liste blanche de `getEquipmentStates` ;
- la cause d'exclusion (25.7), l'exclusion de pièce (25.8), la page de configuration (25.9) ;
- un mode « plusieurs pièces » ou un sélecteur de pièces dans l'arbre ; un changement du filtre partagé B ↔ C (25.4 Q7) ;
- toute mesure sur la box, la VM, Home Assistant ou l'iPad réels (CC-48) ; la validation UX finale (25.5).

## Définitions normatives

### D1 — Portée de la vue C

La vue C a une **portée** : `piece` (« cette pièce seule » : l'arbre ne contient que la pièce d'entrée) ou `toutes` (comportement de 25.4 : toutes les pièces de `j2haRoomsTree`). La portée `piece` désigne toujours **une** pièce existante, celle de la sélection courante.

| Entrée | Portée initiale | Sélection initiale |
|---|---|---|
| clic sur une carte de pièce, ou Entrée / Espace sur la carte (`j2haOpenRoom(id)`) | `piece` (cette pièce) | la pièce |
| clic sur une puce ou un segment de la jauge maison | `toutes` | aucune |
| clic sur une ligne de la liste filtrée de la page B | `toutes` (Q2) | l'équipement |
| lien profond `#j2ha-vue=piece:P;seule:1…` | `piece` | celle du fragment |
| lien profond sans `seule` (y compris les liens produits par 25.4) | `toutes` | celle du fragment |
| « Précédent » / « Suivant » du navigateur | celle de l'entrée restaurée | celle de l'entrée restaurée |

| Événement en portée `piece` | Effet | Lectures réseau |
|---|---|---|
| sélection d'un équipement de la pièce | détail d'équipement, portée inchangée | `getMappingOverrides` × 1 (25.4 D3) |
| sélection de la ligne de la pièce | détail de pièce, portée inchangée | aucune |
| recherche, puce, KPI de pièce | filtre l'arbre **dans la pièce** | aucune |
| « Toutes les pièces » | portée `toutes`, sélection conservée, ligne sélectionnée amenée dans la zone visible | aucune |
| bouton de retour (Q1) | page principale (25.4 AC17) | aucune |

### D2 — Portée dans le fragment

- Clé ajoutée : `seule:1` (Q3). Elle n'est valide **qu'avec** `piece:P` ; toute autre valeur, ou `seule` sans `piece`, invalide le fragment entier (comportement actuel de `parseFragment` pour une entrée hostile).
- Ordre d'écriture déterministe : `piece`, `eq`, `f`, `seule` (un même état donne toujours le même fragment, ce qui conserve l'égalité stricte de `syncUrl` et de la pile `st.hist`).
- Élargir remplace l'entrée courante (`replaceState`, état `null`), comme un changement de filtre (Q4) : « Précédent » garde la profondeur de 25.4 (équipement → pièce → page principale).

## Acceptance Criteria

Convention : chaque AC est vérifiable par un test nommé (Node, parcours du gate 20-0) ou par une commande dont le résultat est écrit dans l'AC. Données et identifiants fictifs (CC-48).

### A. Portée à l'ouverture

**AC1 — Depuis une carte : cette pièce seule**
**Given** la page principale chargée avec une fixture de ≥ 5 pièces fictives (dont « Sans pièce », `object_id = 0`)
**When** l'utilisateur clique sur la carte de la pièce `P` (ou l'active au clavier)
**Then** la vue C s'ouvre avec `data-j2ha-scope="piece"` sur sa racine (attribut observable, sans effet visuel propre) et l'arbre contient **exactement une** ligne de pièce, `.j2ha-wv-room[data-object_id="P"]`, dépliée et sélectionnée ; aucun sous-titre de groupe d'une autre pièce n'est rendu (test `test_story_25_6_portee_piece.node.test.js`)
**And** la ligne de la pièce garde ses repères (« n / t », « N bloqués », « N à appliquer ») identiques à ceux de la carte (même calcul qu'en 25.4 AC4) ; « Sans pièce » s'ouvre de la même façon.

**AC2 — Depuis un filtre ou une ligne de liste : toutes les pièces**
**Given** la page principale
**When** l'utilisateur clique sur une puce, un segment de la jauge ou une ligne de la liste filtrée
**Then** la vue s'ouvre en portée `toutes` (`data-j2ha-scope="toutes"`), exactement comme en 25.4 (AC1, AC13 de 25.4 inchangés) ; une ligne de liste ouvre l'équipement dans sa pièce, l'arbre complet étant filtré par le filtre actif (Q2).

**AC3 — La pièce choisie est visible**
**Given** l'ouverture depuis une carte (AC1), en disposition large ou étroite
**When** la vue est rendue
**Then** la ligne de la pièce est dans la zone visible de l'arbre (`getBoundingClientRect` contenu dans celui de `.j2ha-wv-tree`, vérifié en vrai Chromium par `test_story_25_6_navigateur_reel.node.test.js`, fixture de 40 pièces fictives, carte de la 35ᵉ pièce)
**And** le détail de pièce est affiché à droite (25.4 AC14), le focus est sur son titre (25.4 AC19).

### B. Élargir, URL, historique

**AC4 — Bouton « Toutes les pièces »**
**Given** la vue C en portée `piece`
**When** elle est rendue
**Then** un bouton `.j2ha-wv-widen` libellé « Toutes les pièces » est présent dans la zone d'outils de l'arbre (au-dessus de la recherche) ; il est **absent** du DOM en portée `toutes`
**And** l'activer (clic, Entrée, Espace) passe en portée `toutes` : l'arbre redevient celui de 25.4 (toutes les pièces, ordre et groupes de la grille), **la sélection est conservée** (pièce ou équipement), la pièce reste dépliée, et la ligne sélectionnée est amenée dans la zone visible (`scrollIntoView({ block: 'nearest' })` ou équivalent) ; le focus passe sur la ligne sélectionnée de l'arbre ; un message `role="status"` annonce « Toutes les pièces »
**And** le bouton de retour à la page principale (`.j2ha-wv-back`, classe et comportement inchangés : `goBack`, 25.4 AC17) **change de libellé** selon Q1 (par défaut « Page principale ») ; plus aucun bouton visible ne porte « Toutes les pièces » avec l'effet « retour à la page principale ».

**AC5 — Fragment d'URL et historique**
**Given** D2
**When** on ouvre depuis une carte, on sélectionne un équipement, on élargit, on utilise « Précédent » et « Suivant », on recharge la page sur chaque fragment produit
**Then** (test table-driven `test_story_25_6_etat_url.node.test.js`, successeur de `test_story_25_4_etat_url`) :
- ouvrir depuis la carte `P` pousse `#j2ha-vue=piece:P;seule:1` ; sélectionner l'équipement `E` pousse `#j2ha-vue=piece:P;eq:E;seule:1` ; élargir **remplace** l'entrée par le même fragment sans `seule` ;
- toutes les entrées poussées ou remplacées par la vue ont un état d'historique **`null`** (assertion sur `history.state` après chaque opération) ; le test de cohabitation avec l'écouteur `popstate` du cœur (25.4, #302) est étendu à ces nouvelles entrées et reste vert ;
- « Précédent » depuis l'équipement revient à la pièce **dans la portée de l'entrée restaurée**, puis à la page principale ; « Suivant » rejoue l'inverse ; aucun rechargement de page (aucun appel au faux `jeedomUtils.loadPage`) ;
- recharger la page sur `…;seule:1` rouvre la vue en portée `piece` avec la même sélection et les lectures de 25.4 AC7 (un `getEquipmentStates` ; un `getMappingOverrides` si un équipement est désigné) ; un fragment de 25.4 (sans `seule`) rouvre en portée `toutes` ;
- entrées hostiles fictives : `seule:0`, `seule:oui`, `seule:1` sans `piece`, `seule` en double, `piece:P;seule:1` avec `P` inconnu → fragment ignoré, page principale, aucune erreur.

**AC6 — Zéro requête**
**Given** une lecture d'états valide en mémoire
**When** on ouvre depuis une carte, on élargit, on recherche, on filtre, on revient, on rouvre une autre carte, on utilise « Précédent » / « Suivant »
**Then** l'espion ajax compte **zéro** `getEquipmentStates` et **zéro** `getMappingOverrides` pour toute cette navigation (hors sélection explicite d'un équipement, une lecture par sélection comme en 25.4 D3) (test `test_story_25_6_aucune_requete.node.test.js`) ; `grep -n "getEquipmentStates\|getMappingOverrides" desktop/js/*.js` : mêmes sites d'appel qu'en `731be8d`.

### C. Comportement dans la portée

**AC7 — Recherche, puces et KPI en portée `piece`**
**Given** la portée `piece` sur la pièce `P`
**When** l'utilisateur recherche, active une puce ou clique un KPI du détail de pièce
**Then** le filtrage s'applique **aux équipements de `P` seulement** (la recherche ne fait jamais apparaître une autre pièce) ; « Aucun résultat » est annoncé quand rien ne correspond dans `P`
**And** les effectifs affichés sur les puces de l'arbre sont, en portée `piece`, **ceux de la pièce `P`** (`overview.rooms[P].counts`, déjà calculés par `computeOverview` ; aucun second calcul) et, en portée `toutes`, ceux de la maison (Q5) ; l'invariant de 25.4 AC13 « nombre de lignes de l'arbre pour une puce = effectif de la puce » est vrai **dans les deux portées** (test d'invariant sur 20 fixtures seedées)
**And** le filtre reste partagé avec la page B (25.4 Q7 A) : une puce activée en portée `piece` est le filtre actif au retour en page B ; les puces de la page B gardent les effectifs maison.

**AC8 — Disposition étroite**
**Given** une largeur inférieure au seuil de 25.4 (980 px)
**When** la vue s'ouvre depuis une carte
**Then** le tiroir « Pièces » contient la seule pièce `P` et le bouton « Toutes les pièces » ; l'élargissement ne referme pas le tiroir s'il est ouvert ; changer de disposition conserve la portée (25.4 AC22) ; cibles tactiles ≥ 44 × 44 px pour le nouveau bouton.

**AC9 — Relectures et pièce disparue**
**Given** la portée `piece` sur `P`
**When** une relecture des états arrive (fin d'action, retour d'onglet, « Actualiser »), ou `reconcile` reçoit une topologie sans `P`
**Then** une relecture garde la portée, la sélection et la position de défilement (25.4 AC5) ; si `P` a disparu, la vue passe en portée `toutes` sans sélection, sans erreur de console, et remplace l'entrée d'historique (aucune entrée poussée) ; si l'équipement sélectionné a disparu, retour à la sélection de `P` en portée `piece`.

### D. Accessibilité, CSS, gate

**AC10 — Accessibilité, glossaire, CSS**
**Given** les libellés nouveaux ou modifiés (« Toutes les pièces » sur `.j2ha-wv-widen`, libellé de retour retenu en Q1, annonce « Toutes les pièces », `aria-label` éventuels)
**When** les tests de glossaire, de palette et d'anti-collision s'exécutent
**Then** tous passent par `{{…}}`, sans terme interdit de 25.1 AC23 ; `test_story_25_4_glossaire` et `test_story_25_4_documentation` sont **étendus** (le libellé « Toutes les pièces » existe toujours verbatim, désormais sur le bouton d'élargissement) ; le CSS ajouté est sous `.j2ha-wv` / `.j2ha-wv-*` ; `test_story_25_4_css_collision` (portée, non-modification, collision) passe sur le CSS final avec la référence de 25.4 **mise à jour par ajout seulement** ; aucune couleur littérale (`test_story_25_4_palette_theme` vert)
**And** l'arbre en portée `piece` reste un `role="tree"` valide (un `treeitem` de niveau 1) ; le bouton d'élargissement a un nom accessible ; la portée est annoncée à l'ouverture (« Pièce » + nom, comme en 25.4).

**AC11 — Gate 20-0 adapté, sans affaiblissement**
**Given** le registre d'assertions `tests/fixtures/story_25_4_gate_assertions.json` (plancher) et les parcours `vue-maitre-detail-c`, `page-principale-b`, `decouverte-piece-25-eq-579`, `exclusion-publication-non-publiee`, `reference-bascule-eq-380`, `controle-ecriture-non-declaree`, `rescan-page-principale`
**When** ils sont adaptés à 25.6
**Then** `test_story_25_4_gate.node.test.js` reste vert sans modification du registre (aucune étiquette, clé `record`, étape ni écriture déclarée ne disparaît) ; `git diff main...HEAD -- tests/e2e/gate/lib/policy.mjs` est **vide**
**And** `vue-maitre-detail-c` est complété ainsi : étape 1 (ouverture depuis une carte, 0 lecture) inchangée ; **étape 2** vérifie d'abord, avec une étiquette nouvelle `portee-piece-seule`, que l'arbre ne contient que la pièce de la carte cliquée, que ses repères égalent ceux de la carte et que l'URL porte `seule:1`, puis active « Toutes les pièces » (0 requête du plugin, étiquette nouvelle `requete-pendant-elargissement`) et exécute **sans changement** les assertions existantes `arbre-pieces-differentes-de-la-page` et `reperes-arbre-differents-de-la-page` ; étapes 3 à 9 inchangées dans leurs exigences ; nouveaux `record` : `portee_ouverture`, `pieces_arbre_portee_piece`
**And** les autres parcours qui ouvrent la vue par une carte (`decouverte-piece-25-eq-579`, `exclusion-publication-non-publiee`, `reference-bascule-eq-380`, `controle-ecriture-non-declaree`, `page-principale-b` étape 7) passent sans relâchement : s'ils lisent la ligne d'une pièce, c'est celle de la carte ouverte ; s'ils ont besoin d'une autre pièce, ils l'ouvrent par sa carte ou élargissent explicitement ; les clics sur `.j2ha-wv-back` restent des retours à la page principale
**And** les suites simulées `test_story_20_0_gate_*`, `test_story_20_3_gate_parcours`, `test_story_25_3_gate`, `test_story_25_4_gate` passent ; le gate contre la box est lancé par ClaudeBox (Task 6), jamais par la session cloud.

### E. Non-régression, documentation, conventions, statut

**AC12 — Aucune modification hors interface**
**Given** la branche de la story
**When** on exécute `git diff --stat main...HEAD -- resources/daemon/ core/ plugin_info/ desktop/php/ tests/e2e/gate/lib/policy.mjs scripts/`
**Then** la sortie est **vide** ; `git diff main...HEAD -- desktop/js/jeedom2ha_mapping_override.js desktop/js/jeedom2ha_mapping_surface.js` est vide ; le payload de découverte HA est inchangé.

**AC13 — Non-régression de 25.4**
**Given** les suites `test_story_25_4_*`, `test_story_25_3_*`, `test_story_20_3_*` concernées
**When** elles s'exécutent
**Then** elles passent ; celles qui supposent qu'une carte ouvre l'arbre complet (au minimum `test_story_25_4_navigation`, `…_recherche_filtres`, `…_etat_url`, `…_navigateur_reel`, `…_aucune_lecture_etats`) sont **adaptées** — élargissement explicite ou ouverture par un filtre — sans retirer d'assertion, et la liste des tests modifiés est consignée au Dev Agent Record.

**AC14 — Documentation**
**Given** `docs/fr_FR/index.md` (§ « La vue de travail »), `docs/fr_FR/changelog_beta.md` et le test de documentation de 25.4
**When** la story est livrée
**Then** `index.md` décrit l'ouverture depuis une carte sur la pièce seule, le bouton « Toutes les pièces », le nouveau libellé du retour, l'ouverture depuis un filtre ou une ligne en portée « toutes », le fragment `seule:1` et le comportement de « Précédent » ; `changelog_beta.md` reçoit une entrée ; `test_story_25_6_documentation.node.test.js` vérifie que chaque libellé cité existe verbatim dans `desktop/`.

**AC15 — Conventions et statut**
**Given** CLAUDE.md et `_bmad-output/project-context.md`
**When** la PR de dev est ouverte
**Then** une branche / une PR = ce sujet ; titre Conventional Commits ; `make test`, `node --test tests/unit/*.node.test.js`, tests PHP, `flake8` et `scripts/ci-local.sh` verts ; aucun nom réel, IP ni secret (CC-48) ; les Tasks 0 et 6 sont sautées par une session cloud et la PR le dit
**And** après la preuve terrain de ClaudeBox (Task 6), le statut passe à **`ready-for-UX-validation`**, pas `done` ; le statut courant reste `backlog` jusqu'à `ready-for-dev`.

## Statut cible et validation UX

- **Statut actuel :** `backlog` ; `ready-for-dev` non accordé.
- **Chemin :** `backlog` → `ready-for-dev` (relecture ClaudeBox + décisions Q1 à Q7) → `review` (dev-story) → `ready-for-UX-validation` (preuve terrain ClaudeBox) → `done` à la clôture de 25.5.
- La validation UX (l'arbre à une pièce suffit-il ? le bouton est-il trouvé ?) est faite par Alexandre en **25.5**.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) **[réservée à ClaudeBox ; SAUTÉE par cette session cloud (CC-48 : aucun accès box, SSH ni Home Assistant)]**
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Mode : story d'interface seule, aucune publication attendue → `./scripts/deploy-to-box.sh --sha <complet> --restart-daemon` depuis un worktree neuf (garde-fous CC-56, CC-50) ; vérifier `Deploy complete.`
- [x] Task 1 — Tests d'abord (AC: 1, 2, 3, 5, 6, 7, 9)
  - [x] 1.1 `test_story_25_6_portee_piece`, `…_etat_url` (table D1/D2 + entrées hostiles + cohabitation `popstate` du cœur), `…_aucune_requete`, `…_navigateur_reel` (zone visible, 40 pièces fictives).
  - [x] 1.2 Invariant puces / lignes dans les deux portées (20 fixtures seedées, dérivées du corpus fictif de 25.2).
- [x] Task 2 — Portée et fragment (AC: 1, 2, 5, 9)
  - [x] 2.1 `st.scope` dans `createWorkview` ; `open(target)` reçoit `scope` (`j2haOpenRoom` → `piece` ; puces, segments, lignes → `toutes`) ; `parseFragment` / `formatFragment` / `resolveFragment` gèrent `seule:1` (D2).
  - [x] 2.2 `buildTreeModel` reçoit la portée et ne rend que la pièce en portée `piece` (aucun second algorithme de regroupement) ; `reconcile` (AC9).
- [x] Task 3 — Élargir et libellés (AC: 3, 4, 7, 8, 10)
  - [x] 3.1 Bouton `.j2ha-wv-widen`, `replaceState` (Q4), sélection conservée et ramenée dans la zone visible, focus, annonce.
  - [x] 3.2 Libellé du bouton de retour (Q1) ; effectifs des puces par portée (Q5) ; CSS sous `.j2ha-wv`.
- [x] Task 4 — Gate 20-0 (AC: 11)
  - [x] 4.1 Adapter `vue-maitre-detail-c` (étape 2) et vérifier les autres parcours ; registre 25.4 vert, `policy.mjs` intact ; suites simulées.
- [x] Task 5 — Non-régression, documentation, conventions (AC: 12, 13, 14, 15)
  - [x] 5.1 `git diff --stat` de l'AC12 vide ; tests 25.4 adaptés listés ; `index.md`, `changelog_beta.md`, test de documentation.
  - [x] 5.2 `make test`, `node --test tests/unit/*.node.test.js`, tests PHP, `flake8`, `scripts/ci-local.sh`.
- [ ] Task 6 — Preuve terrain (après fusion) **[réservée à ClaudeBox ; SAUTÉE par cette session cloud (CC-48)]**
  - [ ] 6.1 Gate 20-0 contre la box, tous parcours (dont `vue-maitre-detail-c` adapté) ; contrôle négatif en échec attendu ; résultat dans `25-6-preuve-terrain-<date>.md` (identifiants seuls).
  - [ ] 6.2 Ouverture depuis la carte d'une pièce placée en fin de grille : pièce seule visible, élargissement, « Précédent » sans rechargement par le cœur ; 0 ligne `ERROR` dans le démon ; taille de la réponse inchangée.
  - [ ] 6.3 Passage du statut à `ready-for-UX-validation`.

## Dev Notes

### Dev Agent Guardrails

- **Ne jamais** modifier `resources/daemon/`, `core/`, `plugin_info/`, `desktop/php/`, `tests/e2e/gate/lib/policy.mjs` (AC12).
- **Toujours** un état d'historique `null` (`pushState(null, …)` / `replaceState(null, …)`) : un état non `null` fait recharger la page par le cœur Jeedom (#302).
- **Aucune requête ajoutée** ; la portée est un filtre d'affichage sur des données déjà en mémoire.
- **Aucun recalcul d'état ou d'effectif** hors `computeOverview` / `summarizeRoom` / `resolveEquipmentState`.
- **Gate** : registre de 25.4 = plancher ; une assertion dont le sélecteur change garde son étiquette ; aucune politique relâchée.
- **CSS** : `.j2ha-wv` / `.j2ha-wv-*` seulement ; jamais de règle sur une classe partagée nue (leçon #296).
- Libellés via `{{…}}` ; jamais d'`innerHTML` sur un nom venu de Jeedom ; aucun nom réel (CC-48).
- Une session cloud saute les Tasks 0 et 6 et le dit dans la PR.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle ; jamais de rsync ou de copie SSH ad hoc.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md` ; cycle canonique `main → beta → stable → Jeedom Market`.

### Précédents réutilisables

- Pile d'historique et cohabitation avec le `popstate` du cœur : `syncUrl`, `onPop`, test de cohabitation de #302.
- Filtre partagé et effectifs : `computeOverview` (`overview.rooms[].counts` existe déjà par pièce), `chipsFor`.
- Vrai Chromium, vrai CSS : `test_story_25_4_navigateur_reel`.

### Fichiers probablement touchés (pour le `dev-story`)

`desktop/js/jeedom2ha_workview.js` (portée, fragment, bouton, libellé de retour) ; `desktop/js/jeedom2ha_overview.js` (seulement si l'entrée « ligne de liste » doit transmettre sa portée explicitement) ; `desktop/css/jeedom2ha.css` (bloc `.j2ha-wv`) ; `docs/fr_FR/index.md`, `changelog_beta.md` ; `tests/unit/test_story_25_6_*.node.test.js` et tests 25.4 adaptés ; `tests/e2e/gate/parcours/vue-maitre-detail-c.mjs` (et les autres parcours seulement si nécessaire).

### Definition of done

AC1 à AC15 tenus ; suites locales vertes ; PR relue par ClaudeBox ; preuve terrain (Task 6) ; statut `ready-for-UX-validation`.

### References

- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-19-revue-ux-25.md`#Décisions D2, #Découpage]
- [Source: `_bmad-output/implementation-artifacts/25-4-vue-maitre-detail-c.md`#D2, #AC5, #AC7, #AC13, #AC17, #AC18, #AC27-AC29, #Change Log 12:20]
- [Source: `_bmad-output/implementation-artifacts/25-4-preuve-terrain-2026-10-19.md`#Défaut trouvé par le gate]
- [Source: `CLAUDE.md`, `docs/delegation-claude-cloud.md`, `_bmad-output/project-context.md`]

## UI Impact

- **UI Impact:** Oui — arbre de la vue C limité à la pièce d'entrée, bouton « Toutes les pièces », libellé du retour. Gate 20-0 obligatoire (AC11) ; statut cible `ready-for-UX-validation`, validation UX finale en 25.5.

## Dev Agent Record

### Agent Model Used

Claude (session cloud déléguée, branche `claude/stories-25-6-25-7-aebjpn`, 2026-10-19).

### Debug Log References

- Rouge → vert : les 33 tests de `test_story_25_6_*` ont été écrits et commités rouges (28 en échec) avant le code (commit « task 1 »), puis verts après les commits « task 2 et 3.1 » et « task 3.2 ».
- Le test réel `test_story_25_6_navigateur_reel` (cible tactile) a révélé qu'une règle CSS manquait pour `.j2ha-wv-widen` (118 × 21 px) : ajoutée (`min-height: 44px` hors disposition large).
- `scripts/ci-local.sh` : flake8, pytest 3.9 et 3.12, node (975 tests), `bash -n`, `php -l`, tests PHP verts. Un test pytest de la matrice 3.11 a échoué une fois (code du démon, que cette story ne touche pas) puis a passé à la relance isolée en 3.11 (2413 passed) : échec non reproductible : la relance finale de `scripts/ci-local.sh` (après 25.6 et 25.7) est entièrement verte (3.9 / 3.11 / 3.12 : 2404 passed, 2 skipped ; node : 1022 tests).

### Completion Notes List

- **Portée** (`st.scope` : `piece` | `toutes`) : `j2haOpenRoom` ouvre en `piece` ; puces, segments, lignes de liste (`openView`), liens de 25.4 et `ui.openRoom` sans portée ouvrent en `toutes` (Q2). `open()` ne retient `piece` que si une pièce est désignée.
- **Fragment** : clé `seule:1`, valide seulement avec `piece:P` ; ordre d'écriture `piece`, `eq`, `f`, `seule` ; `parseFragment`/`resolveFragment` ne posent `seule: true` que lorsqu'elle est présente (les objets de 25.4 restent identiques). Toutes les entrées d'historique gardent l'état `null` (#302) ; élargir REMPLACE l'entrée (Q4) ; « Précédent » restaure la portée de l'entrée.
- **Arbre** : `buildTreeModel` reçoit `scope` et ne rend que la pièce sélectionnée, sans titre de groupe (aucun second algorithme de regroupement). **Puces** : effectifs de `overview.rooms[P].counts` en portée pièce (Q5), invariant lignes = effectif vérifié sur 20 scènes seedées dans les deux portées.
- **Bouton `.j2ha-wv-widen`** (Q6) : en tête de la zone d'outils, dans le DOM seulement en portée pièce ; élargir conserve la sélection, l'amène dans la zone visible (`scrollIntoView({block:'nearest'})`), donne le focus à la ligne et annonce « Toutes les pièces ». **Retour** (`.j2ha-wv-back`) : libellé « Page principale » (Q1), classe et comportement inchangés.
- **Pièce disparue** (`reconcile`) : portée `toutes`, sans sélection, entrée remplacée (aucune entrée poussée) ; équipement disparu : retour à la sélection de la pièce, portée conservée.
- **Gate 20-0** : `vue-maitre-detail-c` étape 2 : `portee-piece-seule` (une pièce, repères = carte, `seule:1`), puis « Toutes les pièces » (`requete-pendant-elargissement`), puis les assertions existantes inchangées ; nouveaux `record` : `portee_ouverture`, `pieces_arbre_portee_piece` (+ `requetes_pendant_elargissement`). Registre 25.4 intact (`test_story_25_4_gate` vert), `policy.mjs` et lanceur inchangés. Les autres parcours (`decouverte-piece-25-eq-579`, `exclusion-publication-non-publiee`, `reference-bascule-eq-380`, `controle-ecriture-non-declaree`, `page-principale-b`) lisent la pièce de la carte ouverte : aucune modification nécessaire.
- **Aucun changement hors interface** : `git diff --stat origin/main...HEAD -- resources/daemon core plugin_info desktop/php tests/e2e/gate/lib/policy.mjs scripts desktop/js/jeedom2ha_mapping_override.js desktop/js/jeedom2ha_mapping_surface.js` est vide. `desktop/js/jeedom2ha_overview.js` non modifié (la portée par défaut de `openView` est `toutes`).
- **Tests de 25.4 adaptés (AC13)** — élargissement explicite, aucune assertion retirée : aide `openCardWide` ajoutée à `tests/unit/helpers/workview_harness.js` ; `test_story_25_4_aucune_lecture_etats`, `…_etat_url`, `…_lecture_tardive`, `…_navigation`, `…_recherche_filtres` (`openCard` → `openCardWide`) ; `…_seuil_repli` (un `ui.click('.j2ha-wv-widen')` après `ui.openRoom`) ; `…_glossaire` étendu par ajout (« Page principale », `.j2ha-wv-widen`). Non modifiés : `…_navigateur_reel` (passe via le parcours adapté), `…_gate`, `…_documentation`, `…_css_collision`, `…_palette_theme`, `…_accessibilite`.
- **Tâches sautées** : Task 0 (pre-flight terrain) et Task 6 (preuve terrain, passage à `ready-for-UX-validation`) sont réservées à ClaudeBox (CC-48) : aucun accès box/VM/Home Assistant/SSH, aucune donnée réelle. Le statut reste donc `review` ; `ready-for-UX-validation` est posé par ClaudeBox après la preuve terrain.
- **Commits** : un commit par Task (Task 2 et la partie JS de Task 3.1 sont dans le même commit, le bouton et la portée étant indissociables dans `createWorkview`).

### File List

- `desktop/js/jeedom2ha_workview.js` (modifié)
- `desktop/css/jeedom2ha.css` (modifié)
- `docs/fr_FR/index.md` (modifié)
- `docs/fr_FR/changelog_beta.md` (modifié)
- `tests/e2e/gate/parcours/vue-maitre-detail-c.mjs` (modifié)
- `tests/unit/helpers/workview_harness.js` (modifié)
- `tests/unit/test_story_25_4_aucune_lecture_etats.node.test.js`, `…_etat_url…`, `…_lecture_tardive…`, `…_navigation…`, `…_recherche_filtres…`, `…_seuil_repli…`, `…_glossaire…` (modifiés)
- `tests/unit/test_story_25_6_portee_piece.node.test.js`, `…_etat_url…`, `…_aucune_requete…`, `…_navigateur_reel…`, `…_gate…`, `…_documentation…` (nouveaux)
- `_bmad-output/implementation-artifacts/25-6-vue-c-filtree-sur-la-piece.md`, `sprint-status.yaml` (statuts, Dev Agent Record)

## Décisions (ClaudeBox, 2026-10-19 17:40)

Story relue. Les recommandations sont retenues pour Q1 à Q7 :
- **Q1** : le bouton de retour devient « Page principale ». Le libellé « Toutes les pièces » est réservé à l'élargissement (D2).
- **Q2** : depuis une ligne de la liste filtrée, la vue s'ouvre sur toutes les pièces, pour garder le contexte du filtre.
- **Q3** : la clé de fragment est `seule:1`, absente en vue complète. Les liens de 25.4 restent valides.
- **Q4** : l'élargissement remplace l'entrée d'historique, avec un état `null` (#302).
- **Q5** : les puces affichent les effectifs de la pièce. L'invariant « lignes = effectif » est conservé.
- **Q6** : le bouton est en tête de la colonne de l'arbre, visible seulement en portée pièce.
- **Q7** : la sélection est conservée après élargissement, ramenée dans la zone visible, avec le focus.

**Statut : `ready-for-dev`.**

## Questions ouvertes pour ClaudeBox / Alexandre

Chaque question porte une **recommandation argumentée** ; **aucune n'est tranchée par la session**. Les AC écrits « par défaut » suivent la recommandation, pour qu'une réponse « je valide les recommandations » rende la story prête sans réécriture.

**Q1 — Libellé du bouton de retour à la page principale (aujourd'hui « Toutes les pièces »).**
- A. **« Page principale »** (icône flèche gauche, classe `.j2ha-wv-back` inchangée). *(recommandé : c'est le nom que la documentation donne déjà à cet écran ; il libère « Toutes les pièces » pour l'élargissement décidé en D2 ; les tests et parcours ciblent la classe, pas le texte.)*
- B. « Retour » : court, mais ne dit pas où l'on va.
- C. Garder « Toutes les pièces » pour le retour et nommer l'élargissement autrement (« Afficher toutes les pièces ») : contredit le libellé fixé par D2 et laisse deux boutons presque homonymes.

**Q2 — Portée à l'ouverture depuis une ligne de la liste filtrée de la page B.**
- A. **`toutes`** : la ligne est un résultat du filtre maison ; l'arbre complet filtré montre les autres équipements du même filtre. *(recommandé : D2 ne vise que la carte ; l'utilisateur qui parcourt « 18 bloqués » veut passer de l'un à l'autre sans revenir à la page B.)*
- B. `piece` : cohérent avec la carte, mais coupe l'utilisateur des autres résultats du filtre.

**Q3 — Forme de la portée dans le fragment.**
- A. **Clé `seule:1`**, absente en portée `toutes`. *(recommandé : rétrocompatible avec les liens de 25.4, qui rouvrent tels quels en portée `toutes` ; une seule valeur valide, facile à valider.)*
- B. Clé `portee:piece|toutes` toujours écrite : plus explicite, mais change tous les fragments produits par 25.4 et les assertions de format du parcours (`/^#j2ha-vue=piece:\d+;eq:\d+/` reste vrai, mais d'autres tests comparent des fragments exacts).

**Q4 — Élargir : nouvelle entrée d'historique ou remplacement.**
- A. **Remplacement** (`replaceState`, état `null`), comme un changement de filtre. *(recommandé : « Précédent » garde exactement la profondeur prouvée par le gate en 25.4 — équipement → pièce → page principale — et l'étape 8 du parcours reste inchangée.)*
- B. Nouvelle entrée : « Précédent » revient à la pièce seule ; un niveau de plus à prouver et un comportement de plus à expliquer.

**Q5 — Effectifs des puces de l'arbre en portée `piece`.**
- A. **Effectifs de la pièce** (`overview.rooms[P].counts`), effectifs maison en portée `toutes` ; les puces de la page B restent maison. *(recommandé : garde vrai l'invariant « lignes = effectif de la puce » de 25.4 AC13, que le gate vérifie à l'étape 3 ; aucun calcul nouveau, la donnée existe.)*
- B. Effectifs maison partout : une puce « 18 bloqués » ne montrerait que 2 lignes ; l'invariant tomberait.
- C. Masquer les puces en portée `piece` (les KPI du détail de pièce suffisent) : retire un geste prouvé en 25.4.

**Q6 — Où placer le bouton « Toutes les pièces ».**
- A. **En tête de la colonne de l'arbre**, au-dessus de la recherche, visible seulement en portée `piece`. *(recommandé : il agit sur l'arbre et se trouve là où l'œil cherche la liste ; en disposition étroite il est dans le tiroir « Pièces ».)*
- B. Dans la barre d'en-tête de la vue, à côté du retour : plus visible, mais mélange navigation entre écrans et portée de l'arbre.

**Q7 — Sélection après élargissement.**
- A. **Conservée** (pièce ou équipement), ligne amenée dans la zone visible, focus sur elle. *(recommandé : élargir ne doit rien faire perdre ; c'est aussi la correction du défaut constaté — la pièce hors écran.)*
- B. Sélection vidée (vue « maison » sans sélection) : plus simple, mais l'utilisateur perd son contexte.

## Change Log

- 2026-10-19 — Création (`create-story`, session cloud déléguée) depuis le sprint change du 19/10 (D2) : statut `backlog`, 15 AC, 7 décisions déjà arbitrées, 7 questions ouvertes avec recommandation ; `ready-for-dev` non accordé ; statut cible après implémentation `ready-for-UX-validation` (validation UX finale en 25.5).
- 2026-10-19 17:40 — Relecture ClaudeBox : recommandations retenues (§ Décisions) ; `ready-for-dev`.
- 2026-10-19 — dev-story (session cloud déléguée) : Tasks 1 à 5 faites, Tasks 0 et 6 sautées (CC-48) ; statut `review` ; preuve terrain et `ready-for-UX-validation` à ClaudeBox.
