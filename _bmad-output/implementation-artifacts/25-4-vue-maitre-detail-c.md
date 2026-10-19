# Story 25.4 : Vue maître-détail C — remplacement de la fenêtre de pièce

Status: review

> **Statut : `review` (2026-10-19, `dev-story` terminé par une session cloud déléguée ; Tasks 0 et 11 SAUTÉES, CC-48 ; la preuve terrain, le passage à `ready-for-UX-validation` et la validation UX finale restent à ClaudeBox / 25.5).** Précédemment : `ready-for-dev` (2026-10-19 07:45, relecture et décisions ClaudeBox par délégation d'Alexandre — § Décisions : Q1 à Q14 = A, avec précisions). Précédemment : **`backlog` (2026-10-19).** Story rédigée par une session cloud déléguée (`create-story`, documentaire : aucun code, aucun test, aucune fixture, aucun accès box / VM / Home Assistant / SSH / secret, CC-48). **`ready-for-dev` n'est pas accordé** : la relecture de la story par ClaudeBox est obligatoire, puis les décisions sur les questions Q1 à Q14 (§ Questions ouvertes, chacune avec une recommandation argumentée ; la session n'en tranche aucune). **Statut cible après implémentation et preuve terrain : `ready-for-UX-validation`** (et non `done`) ; la validation UX finale de la vue C est portée par **25.5**, pas par cette story. Les points listés en § Décisions déjà arbitrées sont **fermés** (ils viennent de l'epic, du cadrage, de 25.1 à 25.3 et de la commande de cette story) et ne sont pas rouverts ici. Pointeurs de code pris sur `main` à `a5ba89b` (après 25.1 : #279 `a704dd0`, R2 #282 `c940ac3` ; 25.2 : #288 `2b451dd` ; 25.3 : #293 `ebec48b`, correctifs #294 #296 #297, preuve terrain `030d6e8` / #298) ; **à re-vérifier au SHA courant** avant le `dev-story`. Aucun nom réel d'équipement, de pièce, d'objet, de scénario ou de personne : identifiants et données fictifs seulement (CC-48).

## Story

En tant que propriétaire qui travaille la configuration Home Assistant de sa maison (jusqu'à plusieurs centaines d'équipements, parfois depuis une tablette murale),
je veux qu'un clic sur une carte de pièce ou sur un filtre de la page principale ouvre, **à la place de la fenêtre modale**, une vue pleine hauteur dans la page du plugin — l'arbre pièces → équipements, filtrable et recherchable, à gauche ; le détail de la pièce (« À traiter dans cette pièce ») ou de l'équipement choisi à droite —,
afin de parcourir et corriger la maison pièce après pièce **sans ouvrir ni fermer de fenêtre**, sans perdre le contexte, et sans que le détail soit tronqué.

**Parcours : interface (`desktop/php/`, `desktop/js/`, `desktop/css/`), docs, tests Node/PHP, gate 20-0.** Elle **consomme** les états déjà chargés par la page principale (route `getEquipmentStates`, 25.2 ; page B, 25.3) et **retire** l'ancienne modale de pièce (décision Q4 du cadrage de l'epic : pas de story séparée). **Aucune modification du démon ni du relais ajax** (AC29).

## Décisions déjà arbitrées

Ces points sont **fermés** ; la story les applique sans les rediscuter. Source entre parenthèses.

1. **La vue C remplace la modale, retrait inclus.** `openRoom` / `buildRoomModalHtml` / la bootbox `modal-j2ha-room` disparaissent dans cette story ; pas de story de retrait séparée, pas de double chemin (modale + vue) livré. (epic-25-draft, Q4 de cadrage.)
2. **Seuil de repli entre vue maître-détail et vue étroite : à mesurer pendant la story ; valeur par défaut 1024 px si la mesure n'aboutit pas.** La preuve inclut l'iPad mural en mode bureau (preuve finale hors session de rédaction, documentaire). (epic-25-draft, Q3 de cadrage.)
3. **Source de vérité unique de l'état d'un équipement : `resolveEquipmentState(entrée, enabled)`** (25.1 D1). Aucune règle d'état, aucune partition « Ignorée / Bloquée », aucune table de libellés n'est réécrite pour la vue C. (25.1, 25.2 décisions 1-3, 25.3 décision 2.)
4. **Les états viennent de `getEquipmentStates`, déjà chargée par la page B ; la vue C n'ajoute aucune lecture de cette route.** Elle lit la copie unique en mémoire de la page (25.3 D3) et ses relectures passent par le lecteur existant (coalescé). (Commande de la story ; 25.3 décisions 1, 4, 5.)
5. **Les arbres `getMappingOverrides` ne sont lus qu'à la sélection d'un équipement dans la vue détail** — pas à l'ouverture de la vue, pas à la sélection d'une pièce, pas pour remplir l'arbre. Les **écritures** (aperçu, enregistrement, retour au mode automatique, réglage de publication, Appliquer, Republier, Supprimer) gardent **exactement les mêmes routes, les mêmes paramètres et les mêmes corps de requête** qu'aujourd'hui : aucune réécriture de la logique d'écriture. (Commande de la story ; 16.8, 20-x, 22.2, 25.1.)
6. **Leçon de la story 25.3 (PR #296) — contrainte de conception.** `.j2ha-seg` était partagée entre la jauge et le contrôle segmenté « Automatique | Toujours | Jamais » ; une règle de jauge non portée a réduit ce contrôle à 2 px sur la box, et seul le gate 20-0 l'a vu. Tout nouveau composant partagé de la vue C reçoit **des classes propres** ou des règles **explicitement portées**, et un **test de non-régression anti-collision** le prouve (AC24, AC25). (`25-3-preuve-terrain-2026-10-19.md` § Régression trouvée par le gate.)
7. **Gate 20-0 : les parcours qui ouvrent aujourd'hui la modale sont adaptés, jamais affaiblis.** `decouverte-piece-25-eq-579`, `exclusion-publication-non-publiee`, `reference-bascule-eq-380`, `page-principale-b` (étape 7) — et `controle-ecriture-non-declaree`, qui ouvre aussi la modale — sont adaptés à la vue C **sans retirer aucune assertion et sans relâcher la politique** ; un **parcours propre à la vue C** est ajouté. (Commande de la story ; 25.3 AC17.)
8. **Vocabulaire, palette, thème** : glossaire de 25.1 (Publié / À appliquer / Bloqué / Exclu / Désactivé / Rien à publier ; Publiée / Bloquée / Ignorée / Exclue ; Automatique / Toujours / Jamais) ; vert / bleu / orange / gris, rouge réservé aux boutons destructifs dans leur confirmation et dans les menus « ⋯ » ; aucune couleur en dur, variables `--j2ha-*` ; compatibilité Jeedom 4.4 préservée. (25.1 D4, D5, AC25.)
9. **Contenu fonctionnel du détail inchangé** : état unique, réglage de publication segmenté, « Appliquer » conditionnel, menu « ⋯ », tableau des commandes regroupé par entité, cause dite une fois, commandes ignorées repliées, aucun défilement imbriqué. La vue C **déplace** ce contenu de 25.1 dans le panneau droit ; elle ne le redessine pas. (25.1 ; CADRAGE direction C.)
10. **Pas de temps réel poussé, pas de polling** : l'iPad mural est servi par les déclencheurs de 25.3 (après action, fin de synchro, retour sur l'onglet > 60 s, bouton « Actualiser » de la page B). (25.3 décisions 4, 5, Q10 B.)
11. **Pièce « Sans pièce » (`object_id = 0`)** : adressable dans l'arbre comme les autres ; ses actions de pièce restent indisponibles (le démon refuse la portée `piece` pour `0`), ses actions par équipement sont conservées. (20.1, 25.1.)
12. **Statut cible après implémentation : `ready-for-UX-validation`**, pas `done`. Voir § « Statut cible et validation UX ».

## Sources lues

- `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/epic-25-draft.md` §25.4 et décisions de cadrage Q1-Q4 ; `…/CADRAGE.md` (direction C, contraintes Jeedom, point 4 « Tablette / iPad mural », point 1 « pleine hauteur ») ; `…/diagnostic-ux.md` P8, P15 (« au-delà d'environ 40 équipements dans une pièce, on passe au maître-détail ») et § 4 point 6 (hauteur, mode « mobile », retour arrière) ; `…/maquettes.html`, onglet C (deux cadres : pièce sélectionnée / équipement sélectionné ; arbre à gauche 330 px, outils de recherche et puces, KPI de pièce, liste « À traiter dans cette pièce », méta de l'équipement, tableau 4 colonnes). **Les noms de classes de la maquette (`.seg`, `.chip`, `.pill`, `.dot`, `.row`, `.btn`, `.c-*`) sont génériques : ils ne sont jamais repris tels quels dans le CSS du plugin** (AC24).
- `_bmad-output/planning-artifacts/epics-projection-engine.md` § Epic 25 (statut, décisions de cadrage, gates epic-level).
- `_bmad-output/implementation-artifacts/25-1-socle-etat-unique-glossaire-palette-theme.md` (D1, D3, D4, D5, AC16, AC24, AC25, Q8) ; `25-2-route-agregee-cote-demon.md` (§ Contrat final, AC3, AC4, AC5) ; `25-3-page-principale-b.md` (D1-D3, AC1-AC7, AC11, AC12, AC17, décisions Q1-Q11, Dev Agent Record) ; `25-3-preuve-terrain-2026-10-19.md` (régression CSS `.j2ha-seg`, réserve de chronométrage depuis la page B, taille 1 342 346 octets à 89 % du budget).
- Code (lecture seule, `main` `a5ba89b`) : `desktop/js/jeedom2ha_mapping_surface.js` (`openRoom` `:1568`, `buildRoomModalHtml` `:1508`, `loadEquipment` `:1431`, `reloadEquipment` `:1473`, `togglePanel` `:1491`, `isRoomOpen` `:757`, `showActionFeedback` `:773`, `reloadRoom` `:782`, `runHaAction` `:796`, `buildMenu` `:856`, `buildRoomActions` `:955`, `renderNotices` `:1062`, `buildSegmented` `:1138`, `renderCommandTable` `:1288`, `applyEquipment` `:580`, `window.j2haOpenRoom` `:1615` ; écritures : `saveOverride` `:300`, `revertCommand` `:315`, `publicationRequest` `:376`, `requestPublication` `:514`) ; `desktop/js/jeedom2ha_overview.js` (lecteur d'états, `notifyStatesChanged`, filtres globaux, cartes) ; `desktop/js/jeedom2ha_mapping_override.js` (`resolveEquipmentState`, `summarizeRoom`, `summarizeHouse`) ; `desktop/php/jeedom2ha.php` (`j2haRoomsTree`, `j2haAncestors`, `#j2ha_roomCards`, `row-overflow` / `eqLogicThumbnailDisplay`) ; `desktop/css/jeedom2ha.css` (`.j2ha-gauge .j2ha-seg` `:193`, contrôle segmenté `.j2ha-seg` `:533`) ; `tests/e2e/gate/lib/policy.mjs` (lectures autorisées dont `getMappingOverrides` et `getEquipmentStates`) ; `tests/e2e/gate/parcours/*.mjs` (6 parcours) ; `tests/e2e/gate/page-load-request-inventory.mjs`.

## Contexte et périmètre

### Ce qui existe aujourd'hui (relevé sur `a5ba89b`, à re-vérifier au SHA courant)

- **Page principale (25.3)** : barre de santé, jauge maison filtrante, liste filtrée globale, cartes de pièce groupées par objet parent (`#j2ha_roomCards`, `objectDisplayCard`, `.j2ha-room-card`, `data-object_id`, `onclick="j2haOpenRoom(…)"`). Les états de toute la maison sont en mémoire dans le lecteur de `jeedom2ha_overview.js` (une copie, agrégats dérivés à chaque rendu).
- **Fenêtre de pièce (25.1)** : `openRoom(objectId)` ouvre une `bootbox.dialog` (`className: 'modal-j2ha-room'`, `size: 'large'`), y rend un **accordéon** (un seul équipement déplié) et, **dès l'ouverture, charge l'arbre de chaque équipement de la pièce** (`$content.find('.j2ha-eq-panel').each(… loadEquipment …)`) pour calculer badges et compteurs. C'est ce que la vue C remplace : les états viennent désormais de la copie en mémoire, et l'arbre d'un seul équipement est lu **quand il est sélectionné**.
- **Écritures** : toutes passent par `$.ajax` vers `core/ajax/jeedom2ha.ajax.php` avec les actions `previewMappingOverride`, `saveMappingOverride`, `revertMappingOverride`, `savePublicationOverride`, `revertPublicationOverride`, `executeHaAction` (`intention` `publier` / `supprimer`, `portee` `equipement` / `piece`, `selection` JSON). Ces corps sont la référence à ne pas modifier (AC8).
- **Gate 20-0** : 6 parcours ; 4 d'entre eux ouvrent la modale (`.modal-j2ha-room`, `.j2ha-eq-panel[data-eq-id]`, `.j2ha-eq-toggle`, `.panel-collapse`, `.bootbox-close-button`) et `page-principale-b` en fait un contrôle de non-régression (étape 7).
- **Mesures de référence (25.2 / 25.3)** : réponse de la route 1 342 346 octets (89 % du budget de 1 500 000), froid 314 ms, chaud 136 à 322 ms, construction 150-185 ms ; **chronométrage bout en bout depuis la page B non relevé** (réserve de 25.3). Un arbre unitaire `getMappingOverrides` est une lecture légère (un équipement).

### Dans le périmètre

- vue maître-détail : coquille, arbre pièces → équipements, recherche, filtres, détail pièce, détail équipement (AC9 à AC16) ;
- navigation : ouverture depuis carte / filtre / ligne de liste, retour à la page principale, état d'URL, clavier (AC17 à AC19) ;
- seuil de repli, vue étroite, hauteur, tablette (AC20 à AC22) ;
- retrait de la modale (AC1 à AC3) ; source de vérité unique, lecture tardive, écritures inchangées (AC4 à AC8) ;
- CSS, thème, accessibilité, test anti-collision (AC23 à AC26) ;
- extension du gate 20-0 (AC27 à AC29) ; documentation et libellés (AC30) ; non-régression et conventions (AC31 à AC34).

### Hors périmètre (ne pas faire ici)

- toute modification de `resources/daemon/` et de `core/ajax/` ; du contrat de décision, des artefacts figés (`models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`), des tables de mapping ; toute nouvelle route ou nouveau champ de la liste blanche de `getEquipmentStates` (si un besoin d'affichage manque dans l'entrée agrégée → **s'arrêter et poser la question**, Q8) ;
- la page principale B hors ce qu'impose l'ouverture de la vue (pas de refonte de la barre de santé, de la jauge, des cartes) ;
- tout temps réel poussé, tout polling ; toute mesure sur la box, la VM, Home Assistant ou l'iPad réels (CC-48) ; la **validation UX finale** et la recette A+B+C (25.5) ; les captures de promotion (25.5) ; flags beta / stable / Market ; autres plugins ; dongles.

## Définitions normatives

### D1 — Données de la vue

- **Arbre** : `j2haRoomsTree` (pièces, noms, ordre natif, `enabled`) + `j2haAncestors` (sous-titres de groupe, 25.3 Q2) — seule source des pièces et de leur appartenance. La vue C réutilise le **même regroupement par objet parent** que la grille de la page B (aucun second algorithme de regroupement).
- **États** : la copie unique en mémoire de la page (`payload.equipments`, clés `String(eq_id)`) ; état d'un équipement = `resolveEquipmentState(entrée, enabled)` avec `enabled` lu dans `j2haRoomsTree` ; équipement absent de la copie = **non lu** (hors des six états, comme 25.3 D1). Agrégats de pièce = `summarizeRoom` ; agrégat maison = `summarizeHouse` (25.3). **Rien n'est stocké comme seconde vérité** : tout est dérivé à chaque rendu (25.3 D3).
- **Détail d'équipement** : l'arbre unitaire (`getMappingOverrides`, un `eqId`), lu à la sélection (D3).

### D2 — Navigation et états de la vue

Deux « vues » dans la même page du plugin : **page principale** (B) et **vue de travail** (C). La vue de travail a trois états de sélection : **aucune** (invite « Sélectionnez une pièce ou un équipement »), **pièce** (détail « À traiter dans cette pièce »), **équipement** (détail complet). Ouvrir la vue C ne lit rien : ni `getEquipmentStates`, ni `getMappingOverrides` (AC10).

| Événement | Effet sur la vue | Lectures réseau |
|---|---|---|
| clic sur une carte de pièce | vue C, pièce sélectionnée, arbre déplié sur cette pièce | aucune |
| clic sur une puce / un segment de la jauge maison | vue C, filtre correspondant actif, aucune sélection | aucune |
| clic sur une ligne de la liste filtrée (page B) | vue C, **équipement sélectionné** dans sa pièce, filtre conservé | `getMappingOverrides` × 1 (sélection) |
| sélection d'une pièce dans l'arbre | détail de pièce | aucune |
| sélection d'un équipement dans l'arbre | détail d'équipement | `getMappingOverrides` × 1 |
| retour à la page principale | vue B, état de la page B inchangé | aucune |
| fin d'action (succès ou échec) | relecture des états par le lecteur existant (coalescée, sans `refresh`) ; si un équipement est sélectionné et que l'action le concerne : relecture de son arbre unitaire | `getEquipmentStates` × 1 (lecteur existant) ; `getMappingOverrides` × 1 si l'équipement sélectionné est concerné |

### D3 — Cycle de lecture de l'arbre unitaire

- Un arbre unitaire est lu **à chaque sélection d'équipement** (jamais préchargé, jamais lu pour remplir l'arbre, jamais lu à la sélection d'une pièce). Une lecture en vol pour le même équipement n'est pas doublée.
- Une réponse qui arrive après que la sélection a changé est **ignorée** sans erreur et sans toucher à l'affichage courant (équivalent de `roomHasEquipment` dans la modale actuelle).
- Après une écriture sur l'équipement sélectionné, son arbre est relu comme aujourd'hui (`reloadEquipment`) ; les états de la vue (badge, compteurs, repères) suivent la relecture des états par le lecteur, jamais un recalcul local.
- Échec de lecture : message d'équipement non lisible comme aujourd'hui (`markTreeError`), le reste de la vue reste utilisable.

### D4 — Seuil de repli et deux dispositions

- **Disposition large** (largeur ≥ seuil) : deux colonnes, arbre fixe à gauche, détail à droite, chacun défile seul dans la hauteur disponible.
- **Disposition étroite** (largeur < seuil) : une colonne ; le panneau de gauche est **repliable** (Q2), replié par défaut quand une sélection existe, ouvert sinon ; le détail occupe toute la largeur.
- **Valeur du seuil** : à mesurer pendant la story (protocole en AC20, Q3) ; **défaut 1024 px** si la mesure n'aboutit pas. Le seuil est une constante unique (JS) reprise à l'identique par la media query CSS ; un test garantit l'égalité (AC21).

## Acceptance Criteria

Convention : chaque AC est vérifiable par un test nommé (Node, PHP, parcours du gate 20-0) ou par une commande dont le résultat est écrit dans l'AC. « Vert / bleu / orange / gris » désignent les rôles de 25.1 D5, jamais une valeur de couleur littérale.

### A. Remplacement de la modale et retrait

**AC1 — La vue C remplace la modale à tous les points d'entrée**
**Given** la page principale (B) chargée
**When** l'utilisateur clique sur une carte de pièce, sur une puce ou un segment de la jauge maison, ou sur une ligne de la liste filtrée
**Then** la vue C s'ouvre dans la page du plugin (zone de contenu Jeedom conservée, barre Jeedom intacte) **sans aucune `bootbox` de pièce** (test Node : aucun appel à `bootbox.dialog` avec `className` contenant `modal-j2ha-room` ; test navigateur réel : aucun `.modal` visible à l'ouverture)
**And** les cartes conservent `objectDisplayCard`, `.j2ha-room-card`, `data-object_id` et l'appel `j2haOpenRoom(objectId)` (le nom de la fonction globale est conservé comme point d'entrée, sans autre contrat) ; jamais `eqLogicDisplayCard`
**And** la ligne de la liste filtrée (Q1 de 25.3) ouvre désormais la vue C sur l'équipement concerné.

**AC2 — Retrait de l'ancienne modale, sans reste mort**
**Given** la branche de la story
**When** on recherche `modal-j2ha-room`, `buildRoomModalHtml`, `openRoom`, `.j2ha-eq-accordion`, `panel-group` et les styles associés dans `desktop/`, `tests/` et `docs/`
**Then** il ne reste aucune occurrence fonctionnelle (`grep -rn "modal-j2ha-room" desktop/ tests/ docs/` ne renvoie rien, hors historique `_bmad-output/` et hors la liste de retrait du test AC2)
**And** les règles CSS propres à la modale sont supprimées (pas seulement inutilisées) ; un test statique liste les sélecteurs retirés (`tests/fixtures/story_25_4_css_baseline.json`, Task 1) et vérifie leur absence
**And** les fonctions de rendu **de l'équipement** (état, contrôle de publication, tableau des commandes, notices, commandes ignorées) ne sont **pas** retirées : elles sont déplacées dans le panneau de détail (AC15)
**And** `window.j2haOpenRoom` reste défini (AC1) et ne crée aucune modale.

**AC3 — Pas de double chemin ni de régression d'accès**
**Given** la page principale
**When** on exerce toutes les entrées de l'AC1, « Relire Jeedom », « Republier tout » et « Supprimer tout de Home Assistant… » avec la vue C ouverte
**Then** les confirmations fortes (`btn-danger`, libellés inchangés), le gating (`applyHAGating`, `div_haGatingReason`), les identifiants `span_health*` et `data-ha-action` de la barre de santé restent opérants sans modification
**And** le comportement de la page après « Relire Jeedom » avec la vue C ouverte est vérifié au `dev-story` et consigné (la topologie de `j2haRoomsTree` est rendue côté serveur : si la page se recharge, la vue C est rétablie par l'état d'URL de l'AC18 ; sinon l'arbre est cohérent avec les nouveaux états) ; aucun état incohérent (équipement sélectionné disparu) n'a pour effet une erreur : retour à la sélection de sa pièce, ou de la vue sans sélection si la pièce a disparu.

### B. Données : source unique, lecture tardive, écritures inchangées

**AC4 — Source de vérité unique de l'état (aucune réécriture)**
**Given** la vue C et la copie des états en mémoire
**When** la vue calcule l'état d'un équipement, les repères d'une ligne de l'arbre, les KPI d'une pièce ou les puces de filtre
**Then** l'état de chaque équipement est le retour de `resolveEquipmentState(entrée, enabled)` avec `enabled` lu **dans `j2haRoomsTree`** ; les agrégats de pièce passent par `summarizeRoom`, l'agrégat maison par `summarizeHouse` ; le mot d'état affiché vient de la table de libellés de 25.1 (aucune seconde table)
**And** `git diff main...HEAD -- desktop/js/jeedom2ha_mapping_override.js` ne modifie **aucune** ligne de `resolveEquipmentState`, `analyzeEquipment`, `classifyCommandCategory`, `categoryOfCause`, `summarizeEquipmentCounters`, `summarizeRoom`, `summarizeHouse` (seuls des ajouts de fonctions pures et d'exports sont admis)
**And** `grep -rn "COMMAND_CAUSE_CATEGORIES\|categoryOfCause" desktop/js/` ne trouve rien en dehors de `jeedom2ha_mapping_override.js` (la partition D3 de 25.1 n'est pas dupliquée) ; un test table-driven fait varier `enabled ∈ {true, false}` et vérifie « Désactivé » prime sur « Exclu » dans l'arbre, les KPI et le détail
**And** un test d'invariant vérifie, sur 20 fixtures aléatoires seedées, que **la somme des KPI d'une pièce dans la vue C égale les repères de la carte de la même pièce en page B**, état par état, non lus compris, et que la somme des pièces égale le bloc maison.

**AC5 — Aucune lecture supplémentaire de `getEquipmentStates`**
**Given** la page B chargée avec une lecture valide en mémoire
**When** l'utilisateur ouvre la vue C, navigue entre pièces et équipements, filtre, cherche, replie le panneau, revient à la page principale, puis rouvre la vue
**Then** l'espion ajax compte **zéro** appel `getEquipmentStates` pour toute cette navigation (test Node `test_story_25_4_aucune_lecture_etats.node.test.js`) ; aucun nouveau site d'appel n'apparaît (`grep -n "getEquipmentStates" desktop/js/*.js desktop/php/*.php` : le même site unique qu'en 25.3)
**And** les relectures **déclenchées** (fin d'action, retour d'onglet > 60 s, « Actualiser » de la page B) restent portées par le lecteur de 25.3 : une relecture = un appel sans `refresh`, coalescée ; `refresh=1` reste réservé au bouton « Actualiser » (aucun paramètre `refresh` ailleurs : `grep -n "refresh" desktop/js/*.js` inchangé)
**And** la vue C se rafraîchit à chaque relecture (arbre, repères, KPI, liste « À traiter », badge de l'équipement sélectionné) sans perdre la sélection ni la position de défilement ; si le lecteur est dans l'un des états `available:false` / `action_in_progress` / erreur de 25.3 D2, la vue C affiche **les mêmes mentions** (mêmes libellés exacts, `role="status"`) et jamais « NaN », « undefined » ni une fausse alarme de « non lus »
**And** l'ouverture de la vue C sur une page dont la lecture est indisponible reste possible : l'arbre est rendu depuis `j2haRoomsTree` sans pastilles d'état, la sélection d'un équipement lit son arbre unitaire (le détail reste utilisable comme aujourd'hui), la mention d'indisponibilité est visible.

**AC6 — Les arbres `getMappingOverrides` ne sont lus qu'à la sélection d'un équipement**
**Given** une fixture de ≥ 3 pièces et ≥ 40 équipements fictifs
**When** on ouvre la vue C, on sélectionne une pièce, on déplie des pièces, on filtre, on cherche
**Then** l'espion ajax compte **zéro** appel `getMappingOverrides` (test `test_story_25_4_lecture_tardive.node.test.js`)
**And** sélectionner un équipement émet **exactement un** appel `getMappingOverrides` avec son `eqId` ; resélectionner le même équipement émet un nouvel appel (D3, Q9) ; sélectionner A puis B rapidement émet deux appels et **seule** la réponse de B est rendue (réponse tardive de A ignorée sans erreur)
**And** le site d'appel de `getMappingOverrides` est **unique** (une fonction de lecture) et n'est atteignable depuis aucune boucle sur les pièces ou les équipements (test statique + test de comportement : 100 équipements, 0 appel tant qu'aucun n'est sélectionné)
**And** l'ancien préchargement de la pièce (une lecture par équipement à l'ouverture) n'existe plus (`grep -n "\.j2ha-eq-panel').each" desktop/js/` ne renvoie rien).

**AC7 — Lien profond : au plus une lecture d'arbre**
**Given** une URL d'état (AC18) qui désigne une pièce et un équipement
**When** la page se charge
**Then** l'inventaire des requêtes du chargement compte **un** `getEquipmentStates` (sans `refresh`) et **un** `getMappingOverrides` (celui de l'équipement désigné) ; une URL qui ne désigne qu'une pièce, ou aucune, compte **zéro** `getMappingOverrides` ; le chargement par défaut de la page (sans état d'URL) est **inchangé** par rapport à 25.3 (un `getEquipmentStates`, zéro `getMappingOverrides`)
**And** un état d'URL invalide (identifiant inconnu, non numérique, `eq_id` d'une autre pièce) est ignoré sans erreur et ouvre la page principale (test table-driven d'entrées hostiles fictives).

**AC8 — Écritures strictement inchangées**
**Given** les écritures de l'écran d'équipement : aperçu (`previewMappingOverride`), enregistrement (`saveMappingOverride`), retour (`revertMappingOverride`), réglage de publication (`savePublicationOverride`, `revertPublicationOverride`), `executeHaAction` (`publier` / `supprimer`, portée `equipement` / `piece`), Appliquer, Republier
**When** chacune est déclenchée depuis la vue C
**Then** la route, le verbe, les noms de paramètres, leurs valeurs et l'ordre des opérations (aperçu avant enregistrement ; confirmation avant écriture lorsque l'entité est déjà publiée ; réservation du bouton pendant l'appel) sont **identiques** à ceux de `main` : un **test de contrat d'écriture** compare, pour chaque écriture, le corps sérialisé (clés triées) à la référence `tests/fixtures/story_25_4_corps_ecriture.json` **capturée avant tout changement** (Task 1) ; le test échoue si un paramètre est ajouté, retiré ou renommé
**And** les fonctions d'écriture (`saveOverride`, `revertCommand`, `publicationRequest`, `revertPublication`, `requestPublication`, `applyEquipment`, `runHaAction` et leurs aides de confirmation) sont **déplacées, pas réécrites** : `git diff --color-moved` ne montre aucun changement du corps de construction des requêtes, et la revue consigne le résultat au Dev Agent Record
**And** `lib/policy.mjs` n'ajoute ni ne retire aucune action autorisée ; `test_story_20_0_gate_policy` reste vert.

### C. Interface maître-détail

**AC9 — Coquille de la vue : pleine hauteur, une seule barre de défilement par colonne**
**Given** la vue C ouverte en disposition large
**When** elle est rendue
**Then** elle occupe la hauteur disponible sous la barre Jeedom (Q12 : mesure du décalage haut à l'exécution plutôt qu'une constante), l'arbre et le détail défilent **chacun seul** ; il n'y a **aucun défilement imbriqué** dans le détail (le tableau des commandes ne porte pas de `max-height` propre, 25.1 AC16) ni de défilement de la page derrière
**And** la barre de santé de la page reste visible au-dessus de la vue (et reste opérante) ; la jauge maison, la liste filtrée et la grille de cartes sont masquées (non détruites : le retour les retrouve dans l'état laissé)
**And** la hauteur suit les changements de taille de fenêtre et d'orientation (`resize`, `orientationchange`) sans scintillement ; une hauteur minimale utile est garantie (Q12)
**And** en disposition large, l'arbre mesure ≈ 300-330 px (valeur de la maquette, ajustée par la mesure de l'AC20) et le détail prend le reste.

**AC10 — Ouvrir ou naviguer ne lit rien**
**Given** D2
**When** on exécute la table D2 événement par événement
**Then** le nombre de lectures réseau de chaque ligne est celui de la dernière colonne (test table-driven `test_story_25_4_navigation.node.test.js`) ; en particulier l'ouverture de la vue C, la sélection d'une pièce, le dépliage d'une pièce, la recherche et le filtrage émettent **0** requête.

**AC11 — Arbre pièces → équipements**
**Given** les pièces de `j2haRoomsTree`
**When** l'arbre est rendu
**Then** il reprend, dans l'ordre et avec les sous-titres de groupe de la grille de la page B, chaque pièce avec : icône et couleur Jeedom de l'objet (25.3 AC13, repli sûr identique), nom, « n / t » (publiés / équipements) et, **seulement s'ils sont non nuls**, les repères « N bloqués » (orange) et « N à appliquer » (bleu) ; la pseudo-pièce « Sans pièce » est présente comme les autres
**And** chaque pièce se déplie en lignes d'équipement : état (point + mot court ou pastille de largeur fixe **avant** le nom, diagnostic P8), nom (`eq_name` de `j2haRoomsTree`), mention orange « N bloquées » si `blocked_mention` > 0, et rendu atténué + « (désactivé dans Jeedom) » pour un équipement désactivé ; un équipement **non lu** est affiché sans état, avec la mention grise « non lu »
**And** l'ordre des équipements est l'ordre natif de Jeedom (Q10) ; seule la pièce sélectionnée est dépliée à l'ouverture, les autres pièces sont repliées ; les lignes d'une pièce repliée **ne sont pas rendues dans le DOM** tant qu'elle n'est pas dépliée, sauf si un filtre ou une recherche actif la déplie (Q5)
**And** la sélection courante est visible par plus que la couleur (marque de bordure + `aria-selected="true"`) ; l'arbre est un `role="tree"` avec `role="treeitem"`, `aria-expanded`, `aria-level` (AC26).

**AC12 — Recherche**
**Given** l'arbre de l'AC11
**When** l'utilisateur saisit dans « Rechercher une pièce ou un équipement »
**Then** la recherche porte sur les **noms de pièce et d'équipement** seulement (Q6), sans distinction de casse ni d'accents, avec un délai d'anti-rebond court ; les pièces dont un équipement correspond sont dépliées, les autres masquées ; une pièce dont le **nom** correspond affiche tous ses équipements ; « Aucun résultat » (sans point final) est annoncé en `role="status"` quand rien ne correspond
**And** **aucune requête réseau** n'est émise (AC10) ; vider le champ restaure l'état antérieur de l'arbre (dépliages et sélection compris)
**And** le texte saisi n'est jamais interprété comme du HTML ni comme une expression régulière (test avec `<img onerror>` et `(.*` fictifs) ; la sélection en cours n'est pas perdue par une recherche qui ne la contient pas (le détail reste affiché).

**AC13 — Filtres d'état de l'arbre**
**Given** les puces de filtre de la vue C
**When** l'utilisateur en active une
**Then** les puces sont celles de la page B (Tous, publiés, bloqués, à appliquer, exclus et autres, + non lus si > 0), avec les mêmes libellés, la même composition de « exclus et autres » (25.3 Q4) et les mêmes effectifs, calculés par les mêmes fonctions (aucun second calcul d'effectifs) ; une puce à zéro est désactivée
**And** le **filtre actif en page B est l'état initial** de la vue C (état partagé, une seule vérité de filtre entre B et C, Q7) ; changer le filtre dans la vue C est reflété au retour en page B
**And** combiné à la recherche (ET logique), un filtre actif n'ajoute **aucune** requête ; la sélection d'un équipement qui sort du filtre reste affichée dans le détail (elle n'est pas désélectionnée par un changement de filtre) ; le nombre de lignes de l'arbre pour un filtre est égal à l'effectif annoncé sur la puce (test d'invariant).

**AC14 — Détail de la pièce : « À traiter dans cette pièce »**
**Given** une pièce sélectionnée
**When** le détail est rendu
**Then** il montre : fil d'Ariane (« Parent › Pièce » selon le regroupement), icône + nom, bouton « Republier la pièce » et menu « ⋯ » (« Supprimer de Home Assistant… » en rouge **dans** le menu seulement), KPI de pièce (publiés, bloqués, à appliquer, exclus ou désactivés, rien à publier, et « non lus » si > 0 ; zéros masqués ou désactivés comme sur les cartes), et la liste **« À traiter dans cette pièce »** : une ligne par équipement `blocked` ou `to_apply` (état, nom, nombre de commandes concernées, **cause dite une fois**, action unique : « Ouvrir les types génériques » pour un blocage corrigeable dans Jeedom, « Appliquer » pour un équipement à appliquer) ; si rien n'est à traiter, un état vide explicite (« Rien à traiter dans cette pièce ») et la phrase « Les N équipements … n'appellent aucune action » reste factuelle (nombres issus de `summarizeRoom`)
**And** les causes et les décomptes de cette liste sont produits **par les fonctions existantes de 25.1** alimentées par l'entrée agrégée (Q8) — sans lecture `getMappingOverrides` ; si ce n'est pas possible (champ absent de la liste blanche de la route), le `dev-story` **s'arrête et pose la question** : il ne lit pas les arbres des équipements de la pièce « en douce »
**And** un clic sur une ligne sélectionne l'équipement (lecture tardive, AC6) ; le bouton « Appliquer » d'une ligne déclenche **la même écriture** qu'aujourd'hui (`executeHaAction` `publier` / `equipement`, AC8) sans lire d'arbre (Q11) ; la pièce « Sans pièce » (`object_id = 0`) n'affiche pas les actions de pièce et garde le texte explicatif actuel ; les KPI sont cliquables comme filtres locaux de l'arbre (Q7).

**AC15 — Détail de l'équipement : contenu de 25.1 déplacé, pas redessiné**
**Given** un équipement sélectionné et son arbre unitaire lu (AC6)
**When** le détail est rendu
**Then** l'en-tête collant (`position: sticky`, nom + état + « Appliquer » conditionnel + menu « ⋯ ») reste visible pendant le défilement du détail ; sous lui : le contrôle de publication segmenté (Automatique | Toujours | Jamais), les infos d'entité, l'encart de cause unique (avec « Ouvrir les types génériques ») ou l'encart « À appliquer », le tableau des commandes regroupé par entité (`Commande | Dans Home Assistant | Type Jeedom | Type HA`), les commandes ignorées repliées — **tels que livrés par 25.1** (mêmes fonctions de rendu, mêmes classes, mêmes textes)
**And** le badge, les compteurs d'équipement et les mentions viennent de `resolveEquipmentState` / `summarizeEquipmentCounters` sur l'**arbre unitaire** (comme aujourd'hui) ; l'état affiché dans l'arbre de gauche pour le même équipement vient de l'**entrée agrégée** ; un test de parité (fixtures de 25.2) vérifie que les deux mots d'état sont identiques pour chaque équipement du corpus, y compris après une relecture simulée
**And** les identifiants et classes utilisés par les tests, par le gate et par `scrollToCommand` sont **conservés** : `.j2ha-eq-panel[data-eq-id]` (désormais le conteneur du détail), `.j2ha-eq-publish-badge`, `.j2ha-eq-counter`, `.j2ha-cmd-table`, `tr.mapping-override-cmd[data-cmd-id]`, `.mo-diag-cell`, `.j2ha-goto-blocking`, `.j2ha-notice-text`, `.j2ha-type-link`, `.mo-revert-cmd`, `.j2ha-seg*` du contrôle de publication ; il n'y a plus d'accordéon : `.j2ha-eq-toggle` et `.panel-collapse` disparaissent avec lui (leur remplacement dans les parcours est documenté en AC28)
**And** « réassurance Homebridge » (`j2haSurface_reassurance`) garde son comportement (affichage conditionnel, état réinitialisé à l'entrée dans la vue) ; la mise en évidence d'une commande ciblée (`j2ha-diag-target-highlight`) fonctionne dans le détail.

**AC16 — Feedback et réservation des boutons**
**Given** une action lancée depuis la vue C (équipement, pièce ou ligne « À traiter »)
**When** elle se termine (succès, échec, ou réponse du démon `echec` / `succes_partiel`)
**Then** le résultat est affiché dans une zone `role="status"` du **détail** (équivalent de `showRoomFeedback`) tant que la pièce concernée est affichée, sinon dans la zone d'alerte de la page (`#div_alert`, message échappé) ; le bandeau de santé est relu (`refreshBridgeStatus`) et `notifyStatesChanged()` est signalé **quelle que soit l'issue** (22.2 Q8 A, 25.3 Q7 A)
**And** le bouton qui a lancé l'action est réservé pendant l'appel (pas de double envoi) ; une action lancée depuis une pièce puis une navigation vers une autre pièce ne rend jamais son résultat dans la mauvaise pièce (la pièce est **capturée au lancement**, jamais relue au retour, R1-D de 20.3).

### D. Navigation, URL, clavier

**AC17 — Retour à la page principale**
**Given** la vue C ouverte
**When** l'utilisateur clique sur « Toutes les pièces » (en-tête de la vue) ou utilise le bouton « Précédent » du navigateur
**Then** la page principale (B) est restaurée **dans l'état où elle a été quittée** (filtre global, position de défilement, mention de fraîcheur), sans rechargement de la page ni requête réseau
**And** il n'existe pas de raccourci Échap pour quitter la vue (conflit avec la fermeture des menus et des confirmations, Q13) ; Échap ferme d'abord le menu « ⋯ » ou la confirmation ouverts, puis ne fait rien d'autre
**And** quitter la vue annule les minuteries et les lectures en vol de la vue (aucune écriture dans un DOM détaché, aucune erreur de console).

**AC18 — État d'URL**
**Given** la page du plugin (adresse `index.php?v=d&m=jeedom2ha&p=jeedom2ha`)
**When** une pièce ou un équipement est sélectionné, le filtre ou le panneau change
**Then** l'état « vue C, pièce `P`, équipement `E`, filtre `F` » est reflété dans l'URL par le mécanisme retenu en Q1 (par défaut : fragment, sans rechargement) ; copier-coller l'URL dans un autre onglet rouvre la même sélection (AC7) ; le bouton « Précédent » du navigateur remonte d'un niveau (équipement → pièce → page principale) ; la recherche n'est pas mémorisée
**And** la mise à jour de l'URL ne déclenche **aucun** rechargement ni aucune requête réseau, et n'interfère pas avec la navigation du core Jeedom (vérification sur la page réelle consignée au `dev-story`, Task 3 ; si le core réécrit ou intercepte le fragment, repli décrit en Q1)
**And** les valeurs lues dans l'URL sont validées (entiers positifs, pièce existante, équipement appartenant à la pièce) avant tout usage (AC7).

**AC19 — Clavier et lecteurs d'écran**
**Given** la vue C
**When** on navigue au clavier
**Then** l'arbre suit le motif ARIA `tree` (flèches haut/bas : ligne suivante/précédente ; droite/gauche : déplier/replier ou aller au parent/enfant ; Entrée/Espace : sélectionner ; Début/Fin) avec une seule ligne dans l'ordre de tabulation (« roving tabindex ») ; Tab passe de l'arbre au détail puis aux boutons d'en-tête ; le focus est rendu à l'élément déclencheur au retour, et **déplacé vers le titre du détail** (`tabindex="-1"`) quand une sélection change le détail
**And** la sélection d'un équipement ou d'une pièce, un résultat de recherche et un changement de disposition sont annoncés par des zones `role="status"` `aria-live="polite"` ; chaque bouton-icône a un `aria-label` ; aucune information n'est portée par la seule couleur (mot + icône).

### E. Seuil de repli, hauteur et tablette

**AC20 — Seuil mesuré (ou 1024 px par défaut)**
**Given** les largeurs candidates `768, 834, 900, 980, 1024, 1112, 1180, 1280` (px de viewport CSS) et la fixture la plus lourde du corpus de 25.2 (5 entités, noms de commandes longs, 292 équipements au total)
**When** le `dev-story` exécute le protocole de mesure (navigateur réel de la session, données fictives, rendu avec le vrai CSS ; Q3) : pour chaque largeur, (a) présence ou absence de défilement horizontal dans le détail (`scrollWidth ≤ clientWidth`) pour le tableau des commandes à quatre colonnes ; (b) largeur utile du détail ; (c) lisibilité du panneau de gauche (aucune troncature du nom d'une pièce plus courte que 20 caractères hors ellipse prévue) ; (d) hauteur utile
**Then** le seuil retenu est **la plus petite largeur candidate pour laquelle la disposition large satisfait (a) et (c)** avec les critères chiffrés tranchés en Q3 ; il est consigné au Dev Agent Record avec le tableau des mesures (identifiants et données fictives, CC-48)
**And** **si la mesure n'aboutit pas** (critère non tenu à aucune largeur, navigateur indisponible, résultat instable) : le seuil est **1024 px** et le Dev Agent Record le dit en toutes lettres (décision Q3 de cadrage) ; la story ne bloque pas
**And** la valeur retenue et la méthode sont citées dans la documentation de la story et de la preuve ; **la preuve sur l'iPad mural en mode bureau est une réserve explicite** (Task 11), jamais une assertion de cette story.

**AC21 — Une constante, un seul endroit**
**Given** le seuil retenu
**When** on lit le code
**Then** il est défini **une seule fois** côté JS (constante nommée, exportée pour les tests) et la media query CSS reprend la même valeur ; un test lit les deux et échoue s'ils divergent (`test_story_25_4_seuil_repli.node.test.js`)
**And** la disposition est exposée par un attribut observable `data-j2ha-layout="split|compact"` sur la racine de la vue (utile au gate et aux tests, sans effet visuel propre) ; elle suit `matchMedia` avec **repli** `resize` quand `matchMedia` est absent ou en erreur.

**AC22 — Disposition étroite**
**Given** une largeur inférieure au seuil (tablette, iPad mural en mode bureau si sa largeur CSS est inférieure)
**When** la vue est rendue
**Then** le panneau de gauche est repliable (Q2) : un bouton « Pièces » (`aria-expanded`, `aria-controls`) l'ouvre en tiroir au-dessus du détail ; sélectionner une pièce ou un équipement le referme ; le détail occupe toute la largeur sans défilement horizontal (tableau des commandes compris) ; le bouton « Toutes les pièces » reste accessible
**And** passer d'une disposition à l'autre (rotation, redimensionnement) **conserve** la sélection, le filtre, la recherche et la position dans le détail ; aucune requête n'est émise par le changement de disposition
**And** les cibles tactiles (lignes de l'arbre, puces, boutons) ont au moins 44 × 44 px effectifs en disposition étroite ; pas de comportement qui dépende du survol (`:hover`) pour une action ou une information.

### F. CSS, thème, accessibilité, anti-collision

**AC23 — Palette, thème, replis**
**Given** les thèmes clair et sombre de Jeedom et le repli sans `data-theme` (25.1 Q6 A)
**When** la vue C est rendue
**Then** toutes les couleurs viennent de variables `--j2ha-*` (avec replis) déjà définies ou ajoutées dans le même bloc ; **aucune** couleur littérale ajoutée (test `test_story_25_4_palette_theme.node.test.js`, successeur de celui de 25.3) ; les fonds d'état translucides ont leur repli `rgba()` quand `color-mix()` est absent (iPad mural) ; `var(--border-radius)` est respecté (angles droits du thème sombre)
**And** les contrastes texte / fond des nouveaux éléments (lignes d'arbre, sélection, repères, KPI, liste « À traiter », tiroir) respectent les seuils du test de contrastes de 25.1 sur les deux thèmes ; la couleur Jeedom d'un objet reste un accent d'icône (jamais fond ni texte, 25.3 AC13)
**And** la compatibilité Jeedom 4.4 est préservée (aucune API ni variable propre à 4.6 ; replis testés) ; `dvh` et `position: sticky` ont un repli (Q12) ; le rendu réel 4.4 et le rendu réel du thème clair restent portés par 25.5.

**AC24 — Classes propres et portées explicites pour tout composant partagé (leçon de 25.3)**
**Given** la leçon de la PR #296 (une règle de jauge sur `.j2ha-seg` nue a écrasé le contrôle segmenté)
**When** la story ajoute du CSS pour la vue C
**Then** **toutes** les règles nouvelles sont soit sous la racine `.j2ha-wv` (vue maître-détail), soit sur des classes au préfixe `.j2ha-wv-` ; **aucun sélecteur nu** (`.j2ha-seg`, `.j2ha-menu`, `.j2ha-badge`, `.j2ha-state-*`, `.j2ha-gauge`, `.chip`, `.pill`, `.dot`, `.row`, `.btn`…) n'est ajouté ni modifié pour la vue C ; les noms génériques de la maquette ne sont pas repris
**And** quand la vue C **réutilise** un composant existant (contrôle segmenté, menu « ⋯ », pastille d'état, puces de filtre de la page B), elle le réutilise **sans en modifier les règles** ; une variante de présentation passe par une classe `.j2ha-wv-…` qui porte **sa propre** déclaration sous `.j2ha-wv`, jamais par une règle ajoutée sur la classe partagée
**And** un **inventaire des classes partagées** (composant → propriétaire → contextes d'usage) est écrit dans le Dev Agent Record et dans un commentaire d'en-tête du bloc CSS de la vue C ; il couvre au minimum `.j2ha-seg*` (contrôle segmenté, jauge), `.j2ha-menu-*`, `.j2ha-state-*`, `.j2ha-badge`, `.j2ha-gauge`, les puces de filtre de la page B.

**AC25 — Test de non-régression anti-collision (obligatoire)**
**Given** `tests/fixtures/story_25_4_css_baseline.json` (liste des sélecteurs et déclarations de `desktop/css/jeedom2ha.css` sur `main` **avant** la story, capturée en Task 1) et le CSS final
**When** `test_story_25_4_css_collision.node.test.js` s'exécute
**Then** il vérifie trois choses : (1) **portée** — tout sélecteur présent dans le CSS final et absent de la référence commence par `.j2ha-wv` ou contient `.j2ha-wv-` ; (2) **non-modification** — aucune déclaration d'un sélecteur de la référence n'a changé, hors la liste explicite des sélecteurs de la modale retirés (AC2) ; (3) **collision visuelle** — dans un vrai Chromium (précédent : `test_story_25_3_navigateur_reel`, vrai CSS et vrai jQuery), le contrôle segmenté de publication (`[role=radiogroup].j2ha-seg`), la jauge de la page B (`.j2ha-gauge .j2ha-seg`) et leurs voisins ont **la même taille calculée** dans la vue C, dans la page B et seuls, c'est-à-dire que la largeur calculée du contrôle segmenté n'est ni inférieure à celle de ses boutons ni réduite à 2 px, et que `flex-basis` / `min-width` / `width` d'un `.j2ha-seg` hors jauge ne sont pas ceux d'un segment de jauge
**And** ce test **échoue** sur une branche qui réintroduit la règle fautive de 25.3 (`.j2ha-seg { flex-basis: 0; min-width: 2px }` nue) — preuve par un test négatif qui injecte la règle dans un CSS temporaire ; la preuve est consignée au Dev Agent Record
**And** `test_story_25_3_css_seg_collision` reste vert sans modification.

**AC26 — Accessibilité et glossaire des nouveaux libellés**
**Given** les libellés nouveaux de la vue (au minimum : « Toutes les pièces », « Rechercher une pièce ou un équipement », « À traiter dans cette pièce », « Rien à traiter dans cette pièce », « Pièces » / « Masquer les pièces », « Aucun résultat », « Sélectionnez une pièce ou un équipement », les `aria-label` de l'arbre et des boutons-icônes)
**When** les tests de glossaire et de documentation s'exécutent
**Then** tous passent par `{{…}}` / `__()` (aucun fichier `core/i18n` n'est créé sans décision), sans point final dans les étiquettes, pluriels accordés par le code, aucun terme interdit de 25.1 AC23 (« override », « bridge », « prête(s) », « Sera publié », « Rescanner la topologie », franglais…) ; `test_story_25_1_glossaire`, `test_story_25_3_glossaire` sont **étendus** au nouveau fichier JS et aux ajouts de `desktop/php/` ; ils restent verts
**And** le mot « modale » et l'expression « fenêtre de pièce » n'apparaissent plus dans les libellés visibles ni dans la documentation utilisateur (hors historique).

### G. Gate 20-0, sans affaiblissement

**AC27 — Parcours adaptés : aucune assertion retirée, aucune politique relâchée**
**Given** les parcours `decouverte-piece-25-eq-579`, `exclusion-publication-non-publiee`, `reference-bascule-eq-380`, `controle-ecriture-non-declaree`, `page-principale-b` (étape 7), `run-gate.mjs`, `lib/policy.mjs`
**When** ils sont adaptés à la vue C
**Then** un **registre d'assertions** `tests/fixtures/story_25_4_gate_assertions.json`, **capturé avant toute modification** (Task 1), liste pour chaque parcours les étiquettes d'erreur (`throw new Error('…')`), les clés `helpers.record('…')`, les étapes `atStep`/`waitAtStep`, les écritures déclarées (`declaredEquipments`, `declaredBascules`, `declaredPublicationOverrides`) ; `test_story_25_4_gate.node.test.js` échoue si l'une de ces entrées **disparaît** du parcours adapté (le registre est un **sur-ensemble minimal** : ajouter est permis, retirer non) ; une assertion dont le **sélecteur** change garde la **même étiquette** et la même exigence
**And** `lib/policy.mjs` est **inchangé** (diff vide) ; si une exigence nouvelle de la vue (ex. « zéro `getMappingOverrides` avant sélection ») ne peut pas être portée par la politique, elle l'est par le parcours lui-même (comme l'assertion `refresh=1` de 25.3), sans élargir la liste blanche ; `test_story_20_0_gate_policy` et les suites simulées `test_story_20_0_gate_*`, `test_story_20_3_gate_parcours`, `test_story_25_3_gate` passent
**And** le contrôle négatif `controle-ecriture-non-declaree` **échoue toujours comme attendu** depuis la vue C (l'écriture non déclarée est bloquée) ; aucun parcours ne transmet d'écriture réelle à la box.

**AC28 — Table d'adaptation des sélecteurs (exigences conservées)**
**Given** la table suivante
**When** les parcours sont adaptés
**Then** chaque exigence de la colonne « Conservé » est vérifiée dans le parcours adapté :

| Parcours | Aujourd'hui (modale) | Dans la vue C | Conservé (exigences) |
|---|---|---|---|
| `decouverte-piece-25-eq-579` | `.modal-j2ha-room`, `.j2ha-eq-panel` de toute la pièce, fermeture `detached` | racine `.j2ha-wv`, lignes d'arbre `[data-eq-id]` pour les états de **toute** la pièce, détail `.j2ha-eq-panel[data-eq-id]` pour l'équipement sélectionné, retour à la page principale | présence de l'équipement attendu et de l'équipement désactivé ; mots d'état de tous les équipements de la pièce ; compteurs de pièce cohérents (invariants) ; chaînes interdites absentes **dans la vue** ; actions de pièce présentes ; pseudo-pièce « Sans pièce » ouvrable ; fermeture → retour page |
| `exclusion-publication-non-publiee` | boucle sur les cartes, ouvre/ferme la modale, cherche le panneau | boucle sur les cartes → vue C → sélection de l'équipement par l'arbre ; « fermer » = retour page | exclusion simulée puis retour au mode automatique ; état des boutons avant/après ; **aucune** confirmation `Confirmer` pour un équipement non publié (`modale-confirmation-inattendue`) ; aucune écriture réelle |
| `reference-bascule-eq-380` | ouvre, déplie (`.j2ha-eq-toggle`, `.panel-collapse`) | sélection dans l'arbre ; le détail est déjà ouvert (l'étape « dépliage » devient « sélection », même étiquette de suivi) | table des commandes, ancre bloquante, cause, bascule simulée, journal d'écritures attendu, retour réel au mode automatique |
| `controle-ecriture-non-declaree` | ouvre la pièce, panneau 380 | idem via la vue C | l'écriture non déclarée reste **bloquée** ; le parcours échoue comme attendu |
| `page-principale-b` étape 7 | carte → modale existante, nombre de panneaux > 0 | carte → vue C ; lignes d'arbre > 0 ; **aucun** `getEquipmentStates` supplémentaire ; **zéro** `getMappingOverrides` avant sélection | non-régression de l'ouverture ; assertions (1) à (6) de 25.3 inchangées |

**And** le temps de chargement d'un équipement sélectionné est enregistré par le parcours (valeur seulement, aucun seuil) pour alimenter la réserve de chronométrage de 25.3.

**AC29 — Nouveau parcours propre à la vue C, en lecture seule**
**Given** le gate et un nouveau parcours `tests/e2e/gate/parcours/vue-maitre-detail-c.mjs`
**When** il s'exécute (simulé en CI, contre la box par ClaudeBox)
**Then** il prouve, avec des assertions et des étiquettes d'erreur distinctes : (1) ouvrir la vue depuis une carte n'émet **aucun** `getEquipmentStates` ni `getMappingOverrides` ; (2) l'arbre contient toutes les pièces de la page B et ses repères somment aux nombres de la page B ; (3) la recherche et chaque puce non vide filtrent **sans requête du plugin** et leurs effectifs égalent le nombre de lignes ; (4) sélectionner un équipement émet **un** `getMappingOverrides` et rend le tableau des commandes, la pastille d'état de l'arbre égalant le badge du détail ; (5) sélectionner un second équipement émet un second appel et la réponse tardive du premier n'est pas rendue (scénario contrôlé par l'interception) ; (6) l'état d'URL : recharger la page avec l'URL de l'équipement sélectionné rouvre la même sélection avec **un** `getEquipmentStates` et **un** `getMappingOverrides` ; (7) à deux largeurs de viewport émulées (une au-dessus, une en dessous du seuil retenu) l'attribut `data-j2ha-layout` vaut `split` puis `compact`, aucun défilement horizontal dans le détail, le tiroir « Pièces » s'ouvre et se ferme, sans requête ; la valeur `window.innerWidth` est enregistrée ; (8) le bouton « Précédent » remonte équipement → pièce → page principale ; (9) ouvrir le menu « ⋯ » de pièce puis annuler la confirmation de suppression n'émet **aucune écriture**
**And** `lib/policy.mjs` n'ajoute aucune action ; `page-load-request-inventory.mjs` : le chargement par défaut est **inchangé** (un `getEquipmentStates`, zéro `getMappingOverrides`) et une variante « lien profond » est ajoutée en lecture seule (AC7) ; le diff de l'inventaire est consigné au Dev Agent Record
**And** le gate contre la **box réelle** est lancé par ClaudeBox (pas par cette session, CC-48) ; son résultat est consigné dans la preuve terrain ; la story ne passe pas à `ready-for-UX-validation` sans lui.

### H. Non-régression, documentation, conventions, statut

**AC30 — Documentation et libellés**
**Given** `docs/fr_FR/index.md`, `docs/fr_FR/compteurs.md` (bloc `COMPTEURS:DEBUT/FIN` seul), `docs/fr_FR/changelog_beta.md` et les tests de documentation de 25.1 et 25.3
**When** la story est livrée
**Then** `index.md` décrit la vue de travail (ouverture depuis une carte ou un filtre, arbre, recherche, filtres, détail de pièce « À traiter dans cette pièce », détail d'équipement, retour, comportement sur tablette) et ne parle plus de fenêtre ni de modale ; `compteurs.md` rattache chaque nombre de la vue (repères d'arbre, KPI de pièce) à la même définition que la page principale ; `changelog_beta.md` reçoit une entrée ; les emplacements `<!-- CAPTURE-A-PRENDRE -->` sont conservés (pas de captures, décision 20-5 Q3)
**And** `test_story_25_4_documentation.node.test.js` (successeur de `test_story_25_3_documentation`) vérifie l'absence des termes interdits et que chaque libellé cité dans la doc existe verbatim dans `desktop/` ou `core/`.

**AC31 — Aucune modification du démon, des routes ni des artefacts figés**
**Given** la branche de la story
**When** on exécute `git diff --stat main...HEAD -- resources/daemon/ core/ajax/ core/class/ scripts/deploy-to-box.sh scripts/parity-snapshot.sh scripts/deploy-inventory-diff.sh tests/e2e/gate/lib/policy.mjs`
**Then** la sortie est **vide** ; `models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`, les tables de mapping et les fichiers *golden* sont inchangés ; le payload de découverte HA, les topics et les `unique_id` sont inchangés
**And** `git diff main...HEAD --stat -- desktop/js/jeedom2ha_mapping_override.js` ne montre que des ajouts (AC4) ; les suites `test_story_25_1_*`, `25_2_*`, `25_3_*`, `test_story_20_*`, `test_story_22_2_*` concernées passent, avec pour seules modifications celles imposées par le retrait de la modale, **listées une à une au Dev Agent Record** (aucun test supprimé sans remplacement équivalent).

**AC32 — Performance et taille**
**Given** la mesure de 25.2 / 25.3 (1 342 346 octets, froid 314 ms, chaud 136-322 ms) et le budget de 1 500 000 octets
**When** la vue C est livrée
**Then** la story **ne modifie ni la liste blanche de la route, ni son budget de taille, ni ses budgets de temps** ; la vue n'ajoute aucune copie ni re-sérialisation des états (test : aucun `JSON.stringify` sur `payload.equipments`) ; le temps de calcul de l'arbre, des KPI et des filtres sur 292 équipements de la forme la plus lourde est mesuré en Node et consigné (sans seuil inventé) ; ouvrir la vue et filtrer restent interactifs (aucune boucle bloquante au-delà d'un cycle de rendu ; les lignes d'équipement des pièces repliées ne sont pas rendues, AC11)
**And** le chronométrage bout en bout de la lecture d'un arbre unitaire à la sélection, depuis la vue C, est une **réserve de la preuve terrain** (Task 11) et prolonge la réserve de chronométrage de 25.3.

**AC33 — Conventions de la story**
**Given** CLAUDE.md et `_bmad-output/project-context.md`
**When** la PR de dev est ouverte
**Then** une branche / une PR = ce sujet ; titre en Conventional Commits ; `make test`, `node --test tests/unit/*.node.test.js`, les tests PHP, `flake8` passent ; `scripts/ci-local.sh` est vert avant push
**And** fixtures et tests ne contiennent aucun nom réel d'équipement, de pièce, d'objet, de scénario ou de personne, ni IP privée ni secret (CC-48) ; les identifiants de fixtures sont fictifs
**And** les Tasks 0 et 11 (réservées à l'humain / ClaudeBox) sont sautées par la session cloud et la PR le dit.

**AC34 — Statut cible et validation UX**
**Given** la fin de l'implémentation
**When** ClaudeBox a consigné la preuve terrain (Task 11)
**Then** le statut de la story passe à **`ready-for-UX-validation`**, et **non à `done`** ; la validation UX finale d'Alexandre sur l'ensemble A + B + C (y compris la vue C et son usage sur l'iPad mural) est portée par **25.5**, pas par cette story
**And** cette section et le Dev Agent Record le disent explicitement ; **le statut courant reste `backlog`** jusqu'à `ready-for-dev` (relecture ClaudeBox).

## Statut cible et validation UX

- **Statut actuel :** `backlog`. Il n'est pas modifié par la création de la story ; **`ready-for-dev` n'est pas accordé**.
- **Statut cible après implémentation et preuve terrain :** `ready-for-UX-validation`.
- **La validation UX finale n'a pas lieu en 25.4.** Elle est portée par **25.5** (« Recette UX finale et preuve terrain »), qui reprend aussi la validation transférée de 22-2 (Q1 de cadrage), les preuves transférées de 25.1 (rendu réel du thème clair sur la box, rendu sur Jeedom 4.4) et les réserves de 25.3 (8.3, 8.4, chronométrage depuis la page B). 25.4 fournit à 25.5 une vue C prouvée par le gate 20-0, la mesure du seuil et la preuve terrain ; elle ne demande pas d'avis esthétique à Alexandre avant 25.5.
- **Chemin des statuts :** `backlog` → `ready-for-dev` (relecture ClaudeBox + décisions Q1-Q14) → `review` (dev-story) → `ready-for-UX-validation` (preuve terrain ClaudeBox) → `done` à la clôture de 25.5.

## Tasks / Subtasks

- [ ] Task 0 (SAUTÉE par la session cloud du `dev-story`, 2026-10-19 : réservée à l'humain / ClaudeBox ; CC-48, aucun accès à la box) — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) **[réservé à l'humain / ClaudeBox ; une session cloud NE LA FAIT PAS (CC-48 : aucun accès box, SSH ni Home Assistant)]**
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
  - [ ] Relever, avant le `dev-story`, la largeur CSS réelle de l'iPad mural en mode bureau (identifiants seuls, aucune donnée de la maison) : alimente Q3 et AC20.
- [x] Task 1 — **Capturer l'état de référence AVANT tout changement de code** (AC: 2, 8, 24, 25, 27)
  - [x] 1.1 `tests/fixtures/story_25_4_corps_ecriture.json` : corps sérialisés (clés triées) de chaque écriture de l'écran d'équipement et de pièce, relevés en exécutant les suites existantes de la modale sur `main` (jamais sur la box).
  - [x] 1.2 `tests/fixtures/story_25_4_css_baseline.json` : sélecteurs et déclarations de `desktop/css/jeedom2ha.css` sur `main`, avec la liste des sélecteurs propres à la modale (à retirer en AC2).
  - [x] 1.3 `tests/fixtures/story_25_4_gate_assertions.json` : registre d'assertions des cinq parcours qui touchent la modale (AC27), généré par script lisant les parcours de `main`.
  - [x] 1.4 Inventaire des classes partagées (AC24) : relever sur `main` qui utilise quoi (`.j2ha-seg*`, `.j2ha-menu-*`, `.j2ha-state-*`, `.j2ha-badge`, `.j2ha-gauge`, puces de la page B).
- [x] Task 2 — Tests d'abord (AC: 4, 5, 6, 7, 10, 12, 13, 17, 18, 21, 25)
  - [x] 2.1 `test_story_25_4_aucune_lecture_etats`, `test_story_25_4_lecture_tardive`, `test_story_25_4_navigation` (table D2), `test_story_25_4_recherche_filtres`, `test_story_25_4_etat_url`, `test_story_25_4_seuil_repli`, `test_story_25_4_css_collision` (+ test négatif), `test_story_25_4_contrat_ecriture`.
  - [x] 2.2 Fixtures fictives dérivées du corpus de 25.2 (`tests/fixtures/`), dont 100 équipements et 292 équipements lourds.
  - [x] 2.3 Harnais : `tests/unit/helpers/fake_dom.js`, `ui_harness.js`, `page_b_harness.js` ; test navigateur réel sur le modèle de `test_story_25_3_navigateur_reel`.
- [x] Task 3 — Coquille, navigation, URL (AC: 1, 3, 9, 10, 17, 18, 19)
  - [x] 3.1 Nouveau module `desktop/js/jeedom2ha_workview.js` (UMD : partie pure testée sous Node + démarrage navigateur) : état de la vue, routage, `j2haOpenRoom` comme point d'entrée (Q14).
  - [x] 3.2 Hauteur à l'exécution, décalage haut mesuré (Q12), `resize` / `orientationchange`.
  - [x] 3.3 Vérifier sur la page du plugin simulée (faux cœur Jeedom) que le fragment d'URL n'est pas intercepté ; consigner (Q1).
  - [x] 3.4 Vérifier le comportement après « Relire Jeedom » avec la vue ouverte (AC3) ; consigner.
- [x] Task 4 — Arbre, recherche, filtres, détail de pièce (AC: 4, 11, 12, 13, 14)
  - [x] 4.1 Arbre `role="tree"`, regroupement partagé avec la grille de B, rendu différé des lignes (Q5).
  - [x] 4.2 Recherche (Q6), filtres partagés avec la page B (Q7).
  - [x] 4.3 Détail de pièce : KPI, « À traiter dans cette pièce » depuis l'entrée agrégée (Q8, Q11), actions de pièce.
- [x] Task 5 — Détail d'équipement et retrait de la modale (AC: 2, 6, 8, 15, 16)
  - [x] 5.1 Déplacer les fonctions de rendu et d'écriture de `jeedom2ha_mapping_surface.js` dans le panneau de détail **sans les réécrire** ; `git diff --color-moved` consigné.
  - [x] 5.2 Lecture tardive de l'arbre unitaire (D3), réponses tardives ignorées.
  - [x] 5.3 Retirer `openRoom` / `buildRoomModalHtml` / accordéon / CSS de la modale ; tests de non-occurrence (AC2).
- [x] Task 6 — CSS, thème, accessibilité (AC: 22, 23, 24, 26)
  - [x] 6.1 Bloc CSS `.j2ha-wv` / `.j2ha-wv-*` + commentaire d'en-tête (inventaire des classes partagées).
  - [x] 6.2 Clavier (roving tabindex), annonces, cibles tactiles ; contrastes.
- [x] Task 7 — Mesure du seuil de repli (AC: 20, 21, 22)
  - [x] 7.1 Protocole de mesure (Q3) dans un vrai Chromium de la session, largeurs candidates, fixture la plus lourde ; tableau au Dev Agent Record.
  - [x] 7.2 Fixer la constante (ou 1024 px par défaut si la mesure n'aboutit pas) ; test d'égalité JS / CSS.
- [x] Task 8 — Documentation (AC: 26, 30)
  - [x] 8.1 `index.md`, bloc `compteurs.md`, `changelog_beta.md` ; `test_story_25_4_documentation.node.test.js`.
- [x] Task 9 — Gate 20-0 (AC: 27, 28, 29)
  - [x] 9.1 Adapter les cinq parcours selon la table de l'AC28 ; registre d'assertions vert.
  - [x] 9.2 Ajouter `vue-maitre-detail-c.mjs` ; variante « lien profond » de l'inventaire ; lancer les suites simulées.
- [x] Task 10 — Non-régression et conventions (AC: 31, 32, 33)
  - [x] 10.1 `git diff --stat main...HEAD -- resources/daemon/ core/ajax/ core/class/ … tests/e2e/gate/lib/policy.mjs` vide.
  - [x] 10.2 Mesure Node (292 équipements lourds), absence de `JSON.stringify` sur les états ; liste des tests existants modifiés.
  - [x] 10.3 `make test`, `node --test tests/unit/*.node.test.js`, tests PHP, `flake8`, `scripts/ci-local.sh`.
- [ ] Task 11 (SAUTÉE par la session cloud du `dev-story`, 2026-10-19 : réservée à l'humain / ClaudeBox ; CC-48, aucune preuve terrain possible depuis le cloud) — Preuve terrain (après fusion)
  - [ ] 11.1 Gate 20-0 contre la box, parcours adaptés et `vue-maitre-detail-c` compris ; résultat dans `25-4-preuve-terrain-<date>.md` (identifiants seuls).
  - [ ] 11.2 **Preuve sur l'iPad mural en mode bureau** : largeur CSS réelle, disposition obtenue (`data-j2ha-layout`), tiroir « Pièces », rotation, sélection d'un équipement, aucune barre de défilement horizontale ; confirmation ou révision du seuil (Q3).
  - [ ] 11.3 Chronométrage bout en bout de la sélection d'un équipement (lecture d'un arbre unitaire) et du premier affichage de la vue, depuis la page réelle (prolonge la réserve de 25.3).
  - [ ] 11.4 Rendu sombre sur Jeedom 4.6.1 ; icônes et couleurs réelles des objets dans l'arbre ; passage du statut à `ready-for-UX-validation`.

## Dev Notes

### Dev Agent Guardrails

- **Ne jamais** modifier `resources/daemon/`, `core/ajax/`, `core/class/`, `tests/e2e/gate/lib/policy.mjs`, ni `models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py` (AC31).
- **Ne jamais** recalculer un état, une catégorie de commande ni un compteur autrement que par `resolveEquipmentState` / `summarizeRoom` / `summarizeHouse` (AC4). Si une impossibilité technique apparaît (champ absent de l'entrée agrégée, cause non reconstructible sans l'arbre), **s'arrêter** et la consigner en question (Q8), ne pas lire les arbres de toute la pièce « en douce ».
- **Aucune lecture de `getEquipmentStates` ajoutée** par la vue C ; `refresh=1` reste dans le gestionnaire d'« Actualiser » de la page B (AC5).
- **`getMappingOverrides` seulement à la sélection d'un équipement** ; un seul site d'appel ; réponses tardives ignorées (AC6, D3).
- **Ne pas réécrire les écritures** : déplacer, comparer au contrat de référence (AC8). Aucun changement de route, de paramètre, d'ordre d'opérations, de confirmation.
- **CSS** : préfixe `.j2ha-wv` / `.j2ha-wv-` pour tout ce qui est nouveau ; **jamais** de sélecteur nu sur une classe partagée ; ne pas coller le CSS de la maquette (noms génériques) ; ne jamais restyler `.label`, `.btn`, `.panel`, `.modal`, `.objectDisplayCard` (AC24, AC25).
- **Gate** : ne jamais retirer une assertion ni relâcher la politique ; le registre d'assertions est un plancher (AC27).
- Libellés via `{{…}}` / `__()` ; **aucun fichier `core/i18n` n'existe dans le dépôt** : ne pas en créer sans décision.
- Jamais d'`innerHTML` / `.html()` sur une valeur issue de Jeedom (noms de pièce, d'équipement, icône) : `.text()` / échappement (les noms sont libres, 25.1 `j2ha-free-name`).
- Aucun nom réel dans les fixtures, tests, docs, commits, PR (CC-48).
- Une session cloud n'utilise jamais `scripts/deploy-to-box.sh` ni SSH ; elle saute les Tasks 0 et 11 et le dit dans la PR.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Contraintes Jeedom (CADRAGE, relevées sur 4.6.1 le 18/10)

- Page du plugin = HTML libre dans la zone de contenu (`row-overflow` / `eqLogicThumbnailDisplay`) ; la vue C reste dans cette zone, barre Jeedom conservée ; thème via `<body data-theme>` et variables du core, complétées par `--j2ha-*` (25.1) ; jQuery 3.6, Bootstrap 3, bootbox (pour les confirmations seulement), jeeDialog (seulement s'il est déjà employé), jeedomUtils, Font Awesome 5 local ; aucune bibliothèque ni police externe.
- Tester thèmes clair / sombre + bascule auto et compatibilité 4.4 (variables relevées sur 4.6.1 ; pas de VM 4.4 : replis testés, 25.1 Q10).
- Hauteur : `calc(100vh - barre)` est fragile (barre variable selon version, iOS Safari et sa barre d'adresse) → mesurer le décalage haut à l'exécution, `dvh` avec repli (Q12).

### Précédents réutilisables

- Lecteur d'états, coalescence, `notifyStatesChanged`, états de rendu `available:false` / `action_in_progress` / erreur : `desktop/js/jeedom2ha_overview.js` (25.3) — **le réutiliser**, ne pas en écrire un second.
- Regroupement par objet parent, icône et couleur sûres : `desktop/php/jeedom2ha_overview_helpers.php`, `j2haAncestors` (25.3) ; côté JS, la même logique de regroupement que la grille.
- Menu « ⋯ » : composant de 25.1 (`.j2ha-menu-*`, `buildMenu`) — réutiliser ses classes et sa logique, sans en modifier les règles (AC24).
- Contrôle segmenté de 25.1 (`buildSegmented`, `.j2ha-seg*`) : composant partagé **à risque de collision** (leçon #296).
- Tests : `test_story_25_3_navigateur_reel` (vrai Chromium, vrai CSS, faux cœur Jeedom), `test_story_25_3_css_seg_collision` (précédent de l'anti-collision), `test_story_25_3_gate` (« aucune ligne retirée » des parcours), `test_story_25_2_parite_etat` + `tests/fixtures/story_25_2_parite_etat.json` (parité agrégé / unitaire).
- Pièces à fort volume : diagnostic P15 (« au-delà d'environ 40 équipements dans une pièce, on passe au maître-détail »).

### Tests existants à surveiller

`test_story_25_1_*` (état, glossaire, palette, surface, documentation, compteurs), `test_story_25_2_parite_etat`, `test_story_25_3_*` (page B, chargement unique, refresh, glossaire, palette, css_seg_collision, gate, navigateur réel, documentation), `test_story_16_8_mapping_surface`, `test_story_20_1_*`, `test_story_20_2_*`, `test_story_20_3_*` (dont `gate_parcours`, `php_page`), `test_story_22_2_*`, `test_story_20_0_gate_*`, tests PHP du relais et de `test_story_25_3_php_hierarchie.php`. Ceux qui construisent ou lisent la modale sont à **adapter** (jamais supprimés sans équivalent) ; la liste est consignée au Dev Agent Record.

### Fichiers probablement touchés (pour le `dev-story`)

`desktop/js/jeedom2ha_workview.js` (**nouveau**, vue C : état, arbre, recherche, filtres, routage, disposition) ; `desktop/js/jeedom2ha_mapping_surface.js` (retrait de la modale, rendu et écritures de l'équipement **déplacés** vers le panneau de détail, exposés pour la vue) ; `desktop/js/jeedom2ha_overview.js` (ouverture de la vue depuis cartes / puces / lignes, état de filtre partagé, restauration de la page B) ; `desktop/js/jeedom2ha.js` (rattachement minimal) ; `desktop/js/jeedom2ha_mapping_override.js` (**ajouts** purs seulement) ; `desktop/php/jeedom2ha.php` (conteneur de la vue, `include_file` du nouveau module) ; `desktop/css/jeedom2ha.css` (bloc `.j2ha-wv`, retrait des règles de la modale) ; `docs/fr_FR/index.md`, `compteurs.md`, `changelog_beta.md` ; tests Node `tests/unit/test_story_25_4_*.node.test.js` et adaptés ; fixtures `tests/fixtures/story_25_4_*.json` ; `tests/e2e/gate/parcours/*.mjs`, `tests/e2e/gate/page-load-request-inventory.mjs`.

### Definition of done

AC1 à AC34 tenus ; suites locales vertes ; PR relue par ClaudeBox ; preuve terrain (Task 11, dont la preuve sur l'iPad mural en mode bureau) ; statut `ready-for-UX-validation` (la validation UX finale est portée par 25.5).

### References

- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/epic-25-draft.md`#Stories proposées, 25.4 ; #Décisions de cadrage Q3, Q4]
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/CADRAGE.md`#C — vue de travail ; #Contraintes Jeedom ; #Vérifié sur la box, point 4]
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/diagnostic-ux.md`#P8, #P15, #4 point 6]
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/maquettes.html`, onglet C — données fictives]
- [Source: `_bmad-output/implementation-artifacts/25-1-socle-etat-unique-glossaire-palette-theme.md`#D1, #D4, #D5, #AC16, #AC24, #AC25]
- [Source: `_bmad-output/implementation-artifacts/25-2-route-agregee-cote-demon.md`#Contrat final, #AC3, #AC4]
- [Source: `_bmad-output/implementation-artifacts/25-3-page-principale-b.md`#D1-D3, #AC1-AC7, #AC17, #Décisions, #Dev Agent Record]
- [Source: `_bmad-output/implementation-artifacts/25-3-preuve-terrain-2026-10-19.md`#Régression trouvée par le gate, #Mesure chronométrée]
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md`#Epic-25]
- [Source: `CLAUDE.md`, `docs/delegation-claude-cloud.md`, `_bmad-output/project-context.md`]

## UI Impact

- **UI Impact:** Oui — remplacement de la fenêtre de pièce par une vue maître-détail dans la page du plugin (`desktop/php/`, `desktop/js/`, `desktop/css/`), docs utilisateur. Gate 20-0 obligatoire (AC27 à AC29) ; statut cible `ready-for-UX-validation`, validation UX finale en 25.5.

## Dev Agent Record

### Agent Model Used

Session cloud déléguée Claude Code — `dev-story` (2026-10-19), sur la branche imposée par la plateforme `claude/story-25-4-implementation-ieevms` (même commit de départ que `story/25-4-dev` : `4ff80cd`, PR #300 fusionnée), comme pour 25.3. **Tasks 0 et 11 sautées** (CC-48 : aucun accès box, VM, SSH ni Home Assistant depuis le cloud). **Statut de fin : `review`** (pas `ready-for-UX-validation` : la preuve terrain et la bascule finale restent à ClaudeBox après fusion, Décisions point 5).

### Debug Log References

- `node --test tests/unit/*.node.test.js` : 925 sous-tests verts (base `main` : 773 ; ajoutés par la story : tests `test_story_25_4_*` ; adaptés : voir ci-dessous).
- `make test` / `scripts/ci-local.sh` / `flake8` / tests PHP : résultat consigné dans la PR (exécutés avant le push).
- `git diff --stat 4ff80cd -- resources/daemon/ core/ajax/ core/class/ scripts/deploy-to-box.sh scripts/parity-snapshot.sh scripts/deploy-inventory-diff.sh tests/e2e/gate/lib/policy.mjs` : **vide** (AC31). `git diff -U0 4ff80cd -- desktop/js/jeedom2ha_mapping_override.js` : **vide** (aucun ajout nécessaire non plus).
- Mesure du seuil : `node tests/unit/helpers/measure_story_25_4_threshold.js` → `tests/fixtures/story_25_4_mesure_seuil.json`.

### Completion Notes List

**Architecture livrée.** `desktop/js/jeedom2ha_workview.js` (nouveau, UMD : partie pure testée sous Node + contrôleur + démarrage navigateur) ; `jeedom2ha_mapping_surface.js` perd la modale et l'accordéon, expose `window.Jeedom2haSurface` (détail d'équipement, actions de pièce, gating) ; `jeedom2ha_overview.js` ouvre la vue (cartes, puces, segments de jauge, lignes de la liste filtrée), partage l'état de filtre (`setFilterExact`, `snapshot`, `subscribe`) et exporte `chipsFor` (un seul calcul d'effectifs pour B et C) ; `desktop/php/jeedom2ha.php` : `#j2ha_mainView` (titre, bloc maison, liste filtrée, cartes) + `#j2ha_workView` + `include_file` ; `desktop/css/jeedom2ha.css` : bloc `.j2ha-wv` / `.j2ha-wv-*` et retrait des règles de la fenêtre.

**Décisions ClaudeBox appliquées.** Q1 à Q14 = A avec les précisions : fragment `#j2ha-vue=piece:P;eq:E;f:F` (préfixe obligatoire), tiroir repliable (Q2), `jeedom2ha_workview.js` (Q4), rendu différé (Q5), recherche sur les noms (Q6), filtre unique B ↔ C et KPI cliquables (Q7), causes depuis l'entrée agrégée (Q8), relecture à chaque sélection sans cache (Q9), ordre natif (Q10), « Appliquer » direct seulement sur `to_apply` (Q11), hauteur mesurée avec `dvh`/`vh` et minimum 480 px (Q12), pas d'Échap pour quitter (Q13), `window.j2haOpenRoom` conservé (Q14).

**Q1 — vérification du fragment dans le core (consigné, AC18).** Le code du core Jeedom (4.4 à 4.6) n'est ni dans le dépôt ni accessible depuis la session cloud (CC-48) : **non vérifié**. Le fragment est retenu (Q1 = A) avec le **repli `sessionStorage` automatique** prévu par la décision : si `history.pushState` / `replaceState` lèvent (cœur qui interdit ou intercepte), la sélection est gardée en session (`{ mode: 'storage', piece, eq, filter }`), restaurée au démarrage seulement si l'adresse n'a pas de fragment, effacée à la fermeture ; pas de lien partageable dans ce mode. **À confirmer à la preuve terrain** (Task 11) : un fragment réécrit par le core ferait échouer l'assertion (6) du parcours `vue-maitre-detail-c`.

**Q8 — arrêt éventuel : non déclenché.** L'entrée agrégée porte `diagnostic` par commande et `entities[]` ; `groupBlockedCauses`, `buildCauseNoticeText` et `buildEquipmentCounterLabels` appliqués à l'entrée agrégée rendent exactement les causes et décomptes de l'arbre unitaire (test `test_story_25_4_non_regression` sur les 10 fixtures de 25.2). Aucun champ manquant, aucune lecture d'arbre pour « À traiter dans cette pièce ».

**Mesure du seuil (Task 7, AC20, Q3 = A).** Protocole : Chromium de la session, disposition large forcée à chaque largeur (media query remplacée par `min-width: 0`), contexte Jeedom imité (marges de 15 px, barre de défilement réservée), fixture la plus lourde (292 équipements, un équipement à 5 entités aux noms de commande longs). Critères (Décisions) : (a) pas de défilement horizontal dans le détail ; (b) panneau de gauche ≥ 280 px ; (c) détail ≥ 560 px.

| Largeur (px) | Détail (px) | Arbre (px) | (a) | (b) | (c) | Retenu |
|---:|---:|---:|:-:|:-:|:-:|:-:|
| 768 | 394 | 322 | oui | oui | non | non |
| 834 | 460 | 322 | oui | oui | non | non |
| 900 | 526 | 322 | oui | oui | non | non |
| **980** | 606 | 322 | oui | oui | oui | **oui (seuil)** |
| 1024 | 650 | 322 | oui | oui | oui | oui |
| 1112 | 738 | 322 | oui | oui | oui | oui |
| 1180 | 806 | 322 | oui | oui | oui | oui |
| 1280 | 906 | 322 | oui | oui | oui | oui |

**Seuil retenu : 980 px** (plus petite largeur candidate qui satisfait (a), (b) et (c) ; `LAYOUT_SPLIT_MIN_WIDTH = 980` côté JS, `@media (min-width: 980px)` côté CSS, test d'égalité). **Réserves** : le contexte Jeedom est imité, pas mesuré ; la largeur CSS réelle de l'iPad mural en mode bureau est relevée en preuve terrain (Task 11) et peut réviser le seuil par une PR de suite (la valeur par défaut de la décision de cadrage était 1024 px ; la mesure a abouti, ce défaut n'est donc pas utilisé).

**Clic sur une puce de la page B (AC1, D2).** Une puce ou un segment de la jauge ouvre la vue C avec ce filtre (décision de l'énoncé et de D2) ; un second clic sur le filtre déjà actif le retire sur la page. Sans vue disponible (`env.openView` absent ou refusé), le comportement de 25.3 (liste filtrée sur la page B) est conservé : c'est le repli et c'est ce que les tests de 25.3 qui n'embarquent pas la vue exercent. Le parcours `page-principale-b` (étape 4) est adapté : mêmes étiquettes d'erreur, mêmes clés `record`, les lignes comptées sont celles de l'arbre de la vue. Les chiffres de 25.3 qui étaient lus « dans la fenêtre » sont lus dans l'arbre / le détail de pièce.

**Task 3.4 — « Relire Jeedom » avec la vue ouverte (AC3, consigné).** La page **ne se recharge pas** après `scanTopology` : alerte, relecture du bandeau, puis `notifyStatesChanged()` → relecture des états par le lecteur de 25.3, sans `refresh`. `j2haRoomsTree` est rendu côté serveur et reste celui du chargement de la page (comportement identique à celui de la fenêtre de pièce) ; la vue suit les nouveaux états : un équipement sélectionné devenu « non lu » garde son détail, sa ligne dit « non lu », aucune erreur (test `test_story_25_4_accessibilite`) ; `reconcile(rooms)` existe et est testé en direct, mais **aucun code de production ne l'appelle** (R1) : `j2haRoomsTree` est rendu côté serveur et ne change pas sans rechargement de la page, donc rien ne produit une nouvelle liste de pièces à réconcilier ; il est conservé comme point d'entrée pour une future relecture de la topologie sans rechargement (AC3 « sélection disparue » n'a pas de producteur aujourd'hui).

**AC29 (5) — réponse tardive (précision ClaudeBox n°1).** L'interception du gate ne retarde pas une réponse à la demande et n'est pas modifiée pour cela : l'assertion (5) est portée par `test_story_25_4_navigateur_reel` (vrai Chromium, réseau factice qui retarde la réponse de A) ; le parcours `vue-maitre-detail-c` garde (1) à (4) et (6) à (9). Report consigné, pas un affaiblissement.

**Gate 20-0 (AC27 à AC29).** Registre d'assertions capturé avant la story (`tests/fixtures/story_25_4_gate_assertions.json`) ; `test_story_25_4_gate` échoue si une étiquette d'erreur, une clé `record`, une étape ou une écriture déclarée disparaît d'un parcours. Parcours adaptés avec de **vrais clics** (aucun `dispatchEvent`) : `decouverte-piece-25-eq-579` (compteurs de « Sans pièce » dans le détail de pièce, mêmes clés `record`), `exclusion-publication-non-publiee`, `reference-bascule-eq-380` (+ chronométrage de sélection, réserve de 25.3), `controle-ecriture-non-declaree`, `page-principale-b` ; nouveau `vue-maitre-detail-c` ; `lib/policy.mjs`, `run-gate.mjs`, `interceptor.mjs`, `simulate.mjs` inchangés. **Variante « lien profond »** ajoutée à `page-load-request-inventory.mjs` (additive : le chargement par défaut reste « 1 getEquipmentStates, 0 getMappingOverrides » ; la variante exige 1 + 1). Les pages simulées de `test_story_20_3_gate_parcours` reproduisent désormais le DOM de la vue. Les suites `test_story_20_0_gate_*`, `test_story_20_3_gate_parcours`, `test_story_25_3_gate` passent ; `test_story_25_3_gate` ne garde « aucune ligne retirée » que pour `rescan-page-principale` (les quatre autres sont couverts par le registre).

**Écritures (AC8).** Corps comparés à `tests/fixtures/story_25_4_corps_ecriture.json` (14 scénarios relevés sur `main` AVANT tout changement). Équivalent automatisé de `git diff --color-moved` : `test_story_25_4_ecritures_deplacees` compare, caractère pour caractère, 18 fonctions d'écriture et 31 fonctions de rendu d'équipement de la surface à leur version de `main` (`4ff80cd`) ; seules 10 fonctions de colle fenêtre → vue changent de corps (liste figée) et 12 fonctions de la fenêtre sont retirées (aucune d'écriture ni de rendu d'équipement).

**Revue interne — défaut trouvé et corrigé.** En adaptant les tests de 20.3, un fork a relevé que le détail de pièce n'appliquait ni le gating du pont ni celui de l'état des équipements avant le rendu suivant de la page B (boutons actifs démon arrêté). Corrigé (`renderPane` appelle `surface.refreshRoomGating`) avec test de non-régression dans `test_story_25_4_navigation`.

**Performance (AC32).** Aucune modification de la liste blanche ni des budgets de la route ; aucun `JSON.stringify` / copie des états (test). Calcul en Node sur 292 équipements lourds (consigné par `test_story_25_4_non_regression`, sans seuil) : états + agrégats 6,7 ms, arbre complet 0,7 ms, 5 filtres + recherche 0,9 ms, KPI + « À traiter » 2,4 ms. Le chronométrage de bout en bout d'une sélection depuis la vue C est enregistré par les parcours (`temps_chargement_eq_selectionne_ms`, valeur seule) et reste une réserve de la preuve terrain.

**Points de conception à connaître (relecture).** (1) KPI de pièce : un compteur par état (publié, à appliquer, bloqué, exclu, désactivé, rien à publier : mots du glossaire de 25.1) ; chaque compteur bascule le filtre **partagé** de la page (exclu, désactivé et rien à publier se rattachent tous au filtre « exclus et autres »). (2) Le bloc « Gestion » de la page reste affiché au-dessus de la vue (AC9 ne masque que le bloc maison, la liste filtrée et les cartes) ; la hauteur de la vue est mesurée sous lui. (3) La règle de fond/bordure du corps de l'accordéon (`panel-body`) n'a pas d'équivalent dans la vue (supprimée avec la modale). (4) `.j2ha-room-counter-unread` reste dans le CSS (le détail d'équipement l'emploie pour « présence inconnue ») : retiré de la liste de retrait. (5) Réassurance Homebridge : élément `#j2haSurface_reassurance` construit par la vue, état réinitialisé à l'entrée dans la vue.

**Inventaire des classes partagées (AC24)** : `tests/fixtures/story_25_4_shared_classes.json` et en-tête du bloc CSS de la vue — `.j2ha-seg*` (contrôle segmenté, aussi segment de jauge sous `.j2ha-gauge`), `.j2ha-gauge`, `.j2ha-menu-*`, `.j2ha-state-*`, `.j2ha-badge`, `.j2ha-chip-filter`, `.j2ha-chip` ; la vue les réutilise sans toucher leurs règles. `test_story_25_4_css_collision` : portée (tout sélecteur ajouté sous `.j2ha-wv`), non-modification (aucune déclaration de la référence changée, hors liste de retrait), collision visuelle en vrai Chromium + test négatif qui réinjecte la règle de 25.3 et échoue comme attendu.

**Tests existants modifiés (AC31 — liste une à une, aucun supprimé sans équivalent).**
- `test_story_25_1_surface` (45) : compteurs lus dans `.j2ha-wv-kpis` depuis les entrées agrégées ; un seul détail d'équipement à la fois (`show`) ; menu de pièce → bouton « Republier la pièce » + « Supprimer… » dans le menu ; « un seul panneau déplié » → « sélectionner B remplace le détail de A » ; sticky `.j2ha-wv .j2ha-eq-head` ; « une lecture par équipement à l'ouverture » → « aucune lecture à l'ouverture, une par sélection » ; assertion de fond du corps d'accordéon retirée (règle supprimée).
- `test_story_20_3_r1_ui_reelle` (56) : gating de pièce lu dans les entrées agrégées (« lecture en attente/en échec » → « équipement non lu ») ; R1-D : modale ouverte / fermée / autre pièce → détail affiché / `.j2ha-wv-back` / autre pièce, seul l'arbre de l'équipement sélectionné est relu ; R1-E compteurs réécrits (4 sous-tests) ; G : structure de la vue au lieu de la modale ; R2-6 : titre du détail.
- `test_story_22_2_compteurs_portees` (32), `test_story_20_3_compteurs_piece` (17), `test_story_20_2_p1_p2_comportement_surface` (12) : sélecteurs et un détail à la fois ; `20.3 / AC7` : « le dénombrement ne lit que l'arbre de la pièce ouverte » → « ne lit AUCUN arbre » ; découpe du source adaptée au retrait de la section « compteurs de la pièce ».
- `test_story_25_1_glossaire` (3 sous-tests : parcours des six équipements un par un), `test_story_25_1_palette_theme` (largeur par classe de la vue, fonds `--bg-color`, `matchMedia` admis pour la seule disposition), `test_story_25_3_palette_theme`, `test_story_25_3_page_b` (icônes de la vue portent l'accent), `test_story_25_3_refresh_actualiser` (vue de travail), `test_story_25_3_navigateur_reel` (la vue est chargée ; le test du focus des puces de B s'exécute sans la vue, repli de 25.3), `test_story_25_3_gate` (registre pour quatre parcours), `test_story_20_3_gate_parcours` (pages simulées = DOM de la vue), `test_story_25_1_documentation` / `test_story_22_2_documentation` (noms des emplacements de capture et des phrases du détail).
- Harnais `ui_harness.js` : charge B, C et un faux navigateur ; `ui.openRoom` ouvre la vue (aucune lecture) ; nouveaux `openRoomWith`, `show`, `showRoom`, `selectEquipment`, `loadStates`, `advance`.

### File List

- `desktop/js/jeedom2ha_workview.js` (nouveau), `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/js/jeedom2ha_overview.js`, `desktop/php/jeedom2ha.php`, `desktop/css/jeedom2ha.css`.
- `docs/fr_FR/index.md`, `docs/fr_FR/compteurs.md` (bloc isolé), `docs/fr_FR/changelog_beta.md`.
- `tests/e2e/gate/parcours/{decouverte-piece-25-eq-579,exclusion-publication-non-publiee,reference-bascule-eq-380,controle-ecriture-non-declaree,page-principale-b}.mjs`, `tests/e2e/gate/parcours/vue-maitre-detail-c.mjs` (nouveau), `tests/e2e/gate/page-load-request-inventory.mjs`.
- `tests/unit/test_story_25_4_*.node.test.js` (nouveaux : aucune_lecture_etats, lecture_tardive, navigation, recherche_filtres, etat_url, seuil_repli, css_collision, contrat_ecriture, ecritures_deplacees, navigateur_reel, gate, retrait_modale, palette_theme, glossaire, documentation, accessibilite, non_regression) ; tests adaptés listés ci-dessus.
- `tests/unit/helpers/` : `ui_harness.js` (étendu), `fake_browser.js`, `big_scene.js`, `workview_harness.js`, `workview_browser.js`, `write_scenarios.js`, `git_base.js`, `capture_story_25_4_references.js`, `measure_story_25_4_threshold.js` (nouveaux).
- `tests/fixtures/story_25_4_{corps_ecriture,css_baseline,gate_assertions,shared_classes,mesure_seuil}.json` (nouveaux).
- `_bmad-output/implementation-artifacts/25-4-vue-maitre-detail-c.md` (ce fichier), `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- **Inchangés (AC31)** : `resources/daemon/`, `core/ajax/`, `core/class/`, `tests/e2e/gate/lib/policy.mjs`, `run-gate.mjs`, `models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`, `jeedom2ha_mapping_override.js`.

### Change Log

- 2026-10-19 — `dev-story` (session cloud déléguée) : vue de travail maître-détail C livrée à la place de la fenêtre de pièce ; seuil de repli mesuré à 980 px ; gate 20-0 adapté sans affaiblissement et parcours `vue-maitre-detail-c` ajouté ; documentation ; statut `review`. Tasks 0 et 11 sautées (CC-48).
- 2026-10-19 — Reprise de la relecture R1 (PR #301) : P2-1 (`open()` pose `st.opening` autour de `setFilterExact`, le rendu de B ne réécrit plus l'entrée de la page principale ; « Précédent » depuis une puce ou un segment revient à la page principale), P2-2 (le déclencheur est mémorisé dans `enterView()` puis refocalisé au retour, sinon la carte de la pièce), P2-3 (gate `decouverte-piece-25-eq-579` : les « non lus » sont comptés, enregistrés — `equipements_non_lus_piece_25`, `piece_25_non_lus`, `sans_piece_non_lus` — et font échouer le parcours ; la somme des compteurs est de nouveau comparée à tous les équipements), P3-1 (la ligne « À traiter » dont l'écriture est en vol ou dont l'erreur n'a pas été lue est détachée puis réinsérée telle quelle : bouton réservé, un seul envoi, erreur lisible), P3-2 (scénario « Appliquer » d'une ligne comparé au corps `appliquer-equipement` de la référence), P3-3 (`window.j2haOpenRoom` défini dès le chargement du script, sans effet tant qu'il n'y a pas d'instance). Tests : `test_story_25_4_revue_r1` (9, tous en échec sans les correctifs). À consigner : `reconcile()` n'est pas appelé en production (voir Task 3.4) ; `refreshEquipmentState` réécrit le badge et les compteurs du détail à partir de l'entrée agrégée (et non de l'arbre unitaire de l'AC15) — écart acté, parité prouvée par les tests ; le comportement de `popstate` du core Jeedom et de `history.go(-n)` après rechargement reste une réserve de la preuve terrain (Task 11).

## Décisions (ClaudeBox, 2026-10-19 07:45, par délégation d'Alexandre du 2026-10-18 23:50)

Story relue en entier : 34 AC, D1 à D4, table D2, Tasks, Q1 à Q14. Elle est conforme à la commande et aux décisions de cadrage. **Les recommandations A sont retenues pour Q1 à Q14**, avec les précisions suivantes. Elles font foi en cas d'écart avec le texte des AC.

- **Q1 = A (fragment).** Avant d'écrire le routage, le `dev-story` vérifie dans le code du core (Jeedom 4.4 à 4.6) si le fragment est déjà lu ou réécrit, par exemple pour les onglets ou `jeedomUtils`. Il consigne ce qu'il trouve. Si le core intercepte le fragment, il applique le **repli `sessionStorage`** sans redemander : sélection restaurée, pas de lien partageable. L'AC18 est alors amendée dans le Dev Agent Record : « Précédent » remonte d'un niveau grâce à `history.state`. Le préfixe `j2ha-vue=` reste obligatoire, pour ne jamais lire un fragment qui ne serait pas au plugin.
- **Q2 = A (tiroir repliable).**
- **Q3 = A**, avec les critères (a), (b) ≥ 280 px et (c) ≥ 560 px. Valeur par défaut : 1024 px. La largeur réelle de l'iPad mural en mode bureau sera relevée en preuve terrain (Task 11) ; elle peut réviser le seuil par une PR de suite.
- **Q4 = A (nouveau `jeedom2ha_workview.js`).** Le rendu et les écritures de l'équipement restent dans `jeedom2ha_mapping_surface.js` et sont exposés par une fonction. L'AC8 s'applique : déplacement prouvé par `--color-moved`.
- **Q5 = A (rendu différé).**
- **Q6 = A (noms seulement).**
- **Q7 = A (une seule vérité de filtre B ↔ C, KPI cliquables).**
- **Q8 = A.** Si un champ manque à l'entrée agrégée, **arrêt et question**. Aucune lecture d'arbre de pièce, et aucune extension de la liste blanche de la route dans cette story.
- **Q9 = A (relecture à chaque sélection, sans cache).**
- **Q10 = A (ordre natif de Jeedom).**
- **Q11 = A (« Appliquer » direct depuis la ligne).** Le bouton n'est proposé que pour une ligne `to_apply`. Il reprend la même écriture, la même réservation de bouton et la même confirmation qu'aujourd'hui, avec le même contrat de corps (AC8). Un clic sur le reste de la ligne sélectionne l'équipement.
- **Q12 = A (décalage haut mesuré à l'exécution, `dvh` avec repli `vh`, hauteur minimale ≈ 480 px).**
- **Q13 = A (pas d'Échap pour quitter la vue).**
- **Q14 = A (`window.j2haOpenRoom` conservé).**

**Précisions ClaudeBox hors questions :**

1. **AC29 (5), réponse tardive dans le gate.** L'interception du gate ne retarde peut-être pas une réponse à la demande. Dans ce cas, l'assertion (5) est portée par le test en vrai Chromium (`test_story_25_4_*`, précédent : `test_story_25_3_navigateur_reel`), avec un réseau factice qui retarde la réponse. Le parcours garde les assertions (1) à (4) et (6) à (9). Ce report est **consigné** au Dev Agent Record ; ce n'est pas un affaiblissement. L'interception de `lib/policy.mjs` n'est pas modifiée pour ça.
2. **Vrai clic dans les parcours.** Depuis #299 : les parcours adaptés et le nouveau parcours utilisent des **clics Playwright réels**, avec contrôle d'actionnabilité. Ce qui est caché, recouvert ou réduit à 2 px doit faire échouer le gate. `dispatchEvent('click')` n'est admis que là où un parcours existant l'utilisait déjà, sur un bouton de fermeture de bootbox qui disparaît avec la modale. Il n'est pas reconduit dans la vue C.
3. **Retrait de la modale et « Sans pièce ».** Le parcours `decouverte-piece-25-eq-579` vérifie aujourd'hui les compteurs de « Sans pièce » dans la modale. Il les vérifie désormais dans le détail de pièce de la vue C, **avec les mêmes clés `record`** : registre de l'AC27.
4. **Taille de la story.** Elle est grande (34 AC). Pas de découpage : la vue, le retrait de la modale et l'adaptation du gate sont indissociables, c'est la décision Q4 du cadrage. En revanche, le `dev-story` livre **une seule PR**, dont les commits suivent les Tasks, pour une relecture par étapes. Si la PR dépasse ce qu'une session peut finir, la session s'arrête proprement après le premier jalon cohérent qui laisse `main` vert et le dit. Premier jalon possible : la vue C derrière la modale encore présente ne convient **pas** ; il faut au minimum le retrait et le gate adapté.
5. **Statut de la commande.** La lecture de la session est confirmée : `backlog` à la création, puis `ready-for-dev` par la présente relecture, et `ready-for-UX-validation` seulement après la preuve terrain.

**Statut : `ready-for-dev`.**

## Questions ouvertes pour ClaudeBox / Alexandre

Chaque question porte une **recommandation argumentée** ; **aucune n'est tranchée par la session**. Les AC écrits « par défaut » ci-dessus suivent la recommandation, pour qu'une réponse « je valide les recommandations » rende la story prête sans réécriture.

**Q1 — Mécanisme de l'état d'URL (epic : « état d'URL »).**
- A. **Fragment** (`#j2ha-vue=piece:P;eq:E;f:F`, valeurs validées), mis à jour par `history.pushState` / `replaceState` et lu par `popstate` / `hashchange` : aucun rechargement, aucune requête, « Précédent » fonctionne, lien partageable. *(recommandé : le plus compatible avec une page de plugin dont l'adresse porte déjà `v=d&m=jeedom2ha&p=jeedom2ha` ; à vérifier au `dev-story` que le core Jeedom n'intercepte pas le fragment.)*
- B. Paramètres de requête ajoutés à l'adresse : lien plus « propre », mais toute mise à jour peut provoquer un rechargement complet par le chargement de page du core, ce qui perd la vue et refait les lectures.
- C. Pas d'état d'URL : plus simple, mais contredit l'epic (retour arrière, lien profond) et laisse l'iPad mural perdre sa sélection à chaque rechargement (après « Relire Jeedom » si la page se recharge, AC3).
- *Repli si A est intercepté par le core :* `sessionStorage` pour la sélection (par vue, sans lien partageable), consigné et décidé par ClaudeBox.

**Q2 — Disposition étroite : forme du panneau de gauche.**
- A. **Tiroir repliable** : le panneau est masqué par défaut quand une sélection existe, un bouton « Pièces » l'ouvre au-dessus du détail, sélectionner le referme. *(recommandé : c'est la formulation de l'epic et du cadrage — « panneau gauche repliable sous une largeur seuil » — et elle garde un seul modèle mental large/étroit.)*
- B. Pile de deux écrans (liste puis détail avec bouton retour) : modèle « mobile » classique, mais deux écrans à synchroniser et une navigation de plus au doigt.
- C. Arbre en accordéon au-dessus du détail, toujours visible : consomme la hauteur utile sur tablette.

**Q3 — Protocole de mesure du seuil et critères chiffrés.**
- A. Mesurer dans le Chromium de la session (largeurs candidates de l'AC20, fixture la plus lourde, vrai CSS) ; critères **proposés** : (a) aucun défilement horizontal dans le détail ; (b) panneau de gauche ≥ 280 px ; (c) détail utile ≥ 560 px ; retenir la plus petite largeur candidate qui les satisfait ; **1024 px si la mesure n'aboutit pas** (décision de cadrage). La largeur CSS réelle de l'iPad mural en mode bureau est relevée **hors session** (Task 0 / Task 11) et peut réviser le seuil. *(recommandé : la mesure est reproductible et sans accès terrain ; les critères sont discutables mais explicites ; le défaut 1024 px est déjà décidé.)*
- B. Fixer 1024 px sans mesure : plus rapide, mais contredit « à mesurer pendant 25.4 ».
- C. Mesurer uniquement sur l'iPad réel : plus fidèle, impossible pour une session cloud (CC-48) et retarde le `dev-story`.
- *Note :* l'hypothèse selon laquelle un iPad en mode bureau expose environ 1024 px CSS n'est pas vérifiée ici ; elle ne sert à rien dans la story tant qu'elle n'est pas mesurée.

**Q4 — Où vit le code de la vue : nouveau module ou extension de `jeedom2ha_mapping_surface.js` (1 621 lignes).**
- A. **Nouveau `desktop/js/jeedom2ha_workview.js`** pour la coquille, l'arbre, la recherche, le routage et la disposition ; `jeedom2ha_mapping_surface.js` garde le rendu et les écritures de l'équipement (déplacés dans le panneau de détail, exposés par une fonction) et perd la modale. *(recommandé : suit le précédent de 25.3 — `jeedom2ha_overview.js` —, limite le diff des fonctions d'écriture, garde les parties pures testables sous Node.)*
- B. Tout dans `jeedom2ha_mapping_surface.js` : un seul fichier, mais ~2 400 lignes et un diff d'écritures plus difficile à vérifier.
- C. Réécrire la surface en modules distincts (arbre, détail, écritures) : propre, mais contredit « aucune réécriture de la logique d'écriture » et alourdit la revue.

**Q5 — Rendu de l'arbre : tout ou différé.**
- A. **Différé** : seules les lignes des pièces dépliées (ou dépliées par un filtre / une recherche) existent dans le DOM ; la pièce sélectionnée est dépliée à l'ouverture. *(recommandé : 292 équipements aujourd'hui, davantage demain ; coût de rendu et de mise à jour à chaque relecture proportionnel à ce qui est visible ; sur l'iPad mural le gain est réel.)*
- B. Tout rendre : plus simple, recherche triviale, mais DOM de plusieurs centaines de lignes réécrit à chaque relecture.
- C. Virtualisation de liste : surdimensionné pour ce volume.

**Q6 — Portée de la recherche.**
- A. **Noms de pièce et d'équipement** seulement (déjà dans `j2haRoomsTree`, aucune lecture), insensible à la casse et aux accents. *(recommandé : zéro requête, comportement prévisible ; l'étiquette « Rechercher une pièce ou un équipement » est celle de la maquette.)*
- B. Ajouter les noms de commande : exigerait de lire les arbres unitaires (contredit D3) ou d'élargir la liste blanche de la route (hors périmètre, AC31).
- C. Ajouter l'état ou la cause (« bloqué », « types génériques ») : redondant avec les filtres.

**Q7 — Filtre partagé entre la page B et la vue C, et KPI de pièce cliquables.**
- A. **Une seule vérité de filtre** : le filtre actif en B est l'état initial de C, les changements dans C se reflètent en B ; les KPI du détail de pièce sont des filtres locaux de l'arbre. *(recommandé : évite deux filtres qui divergent et reste fidèle à « un clic sur une carte ou un filtre ouvre la vue C » ; aucune requête.)*
- B. Filtres indépendants : plus simple, mais l'utilisateur voit deux listes qui ne disent pas la même chose.
- C. Pas de KPI cliquables : retire un geste de la maquette, mais réduit la surface à tester.

**Q8 — Causes et décomptes de « À traiter dans cette pièce » sans lire d'arbre unitaire.**
- A. **Les produire depuis l'entrée agrégée** avec les fonctions de 25.1 (`renderNotices`-équivalent pur, `summarizeEquipmentCounters`), la parité étant prouvée comme en 25.2 AC4 ; si un champ manque, **s'arrêter et poser la question**. *(recommandé : respecte la contrainte « arbres lus uniquement à la sélection » ; l'entrée agrégée porte déjà `diagnostic` par commande et `entities[]`.)*
- B. Lire les arbres des équipements bloqués / à appliquer de la pièce à la sélection de la pièce : simple, mais contredit la décision de lecture tardive et recrée le préchargement de la modale en plus petit.
- C. Afficher le nombre de commandes sans cause dans la liste : plus pauvre, perd la valeur du diagnostic remontée par P12.

**Q9 — Cache de l'arbre unitaire à la resélection.**
- A. **Relire à chaque sélection** (une lecture légère), sans cache entre deux sélections. *(recommandé : fraîcheur après une écriture ou une synchro sans logique d'invalidation à maintenir ; le coût est un appel par clic, dé-doublé s'il est en vol.)*
- B. Cache jusqu'à la prochaine écriture ou relecture des états : économise des appels, mais ajoute une seconde copie à invalider (le contraire de D3 de 25.3).

**Q10 — Ordre des équipements dans l'arbre.**
- A. **Ordre natif de Jeedom**, comme la grille de B et comme la modale actuelle ; les filtres servent à isoler les cas à traiter. *(recommandé : cohérence avec le reste de l'écran, aucun tri à expliquer.)*
- B. Tri par état (bloqués d'abord) : utile pour traiter, mais déplace des lignes à chaque relecture et rompt la mémoire spatiale.

**Q11 — « Appliquer » depuis la ligne « À traiter » : écriture directe ou sélection.**
- A. **Direct**, par la même écriture qu'aujourd'hui (`executeHaAction` `publier` / `equipement`, qui ne demande pas d'arbre) avec les mêmes réservations de bouton et le même feedback ; c'est le geste de la maquette. *(recommandé : un clic de moins pour le cas le plus fréquent ; aucune logique d'écriture nouvelle, l'AC8 le prouve par le contrat de corps.)*
- B. Le bouton sélectionne l'équipement et l'utilisateur applique depuis le détail : plus prudent (l'utilisateur voit l'encart « À appliquer » avant), un clic de plus.

**Q12 — Hauteur de la vue et robustesse tablette.**
- A. **Mesurer le décalage haut à l'exécution** (`getBoundingClientRect().top` du conteneur) plutôt qu'une constante de barre, hauteur = hauteur de la fenêtre moins ce décalage, `dvh` avec repli `vh`, hauteur minimale utile (≈ 480 px), recalcul sur `resize` / `orientationchange`. *(recommandé : la barre Jeedom varie entre 4.4 et 4.6 et la barre d'adresse d'iOS Safari modifie `100vh` ; une constante serait fausse quelque part.)*
- B. `calc(100vh - 80px)` constant : simple, fragile (c'est le risque nommé au diagnostic § 4 point 6).
- C. Hauteur automatique, sans pleine hauteur : perd l'intérêt de la vue (deux défilements indépendants).

**Q13 — Quitter la vue : Échap ou non.**
- A. **Pas d'Échap** : bouton « Toutes les pièces » et bouton « Précédent » du navigateur seulement ; Échap ferme d'abord un menu ou une confirmation ouverts. *(recommandé : 25.3 a déjà vu Échap dépendre du focus de Bootstrap et échouer au gate ; un Échap qui quitte la vue au lieu de fermer un menu serait une régression d'usage.)*
- B. Échap quitte la vue quand rien n'est ouvert : raccourci utile au clavier, risque de sortie involontaire.

**Q14 — Nom du point d'entrée.**
- A. **Conserver `window.j2haOpenRoom(objectId)`** comme point d'entrée (les cartes de 25.3 l'appellent par `onclick`), avec comme seul contrat « ouvrir la vue sur cette pièce ». *(recommandé : aucun changement de balisage PHP des cartes, parcours et tests inchangés sur ce point, le nom « Room » reste exact.)*
- B. Renommer en `j2haOpenWorkview` : plus parlant, mais modifie le PHP des cartes, `onclick`, les helpers de test et les parcours pour un gain nul.

## Points signalés à la relecture (hors questions)

- **Statut cible de la commande de cette session.** La commande demande un statut de fin de session « `ready-for-UX-validation` — PAS `ready-for-dev` ». Dans ce dépôt, `ready-for-UX-validation` désigne l'état d'une story **implémentée et prouvée sur le terrain** (25.1, 25.3). Lire la commande ainsi aurait fait passer une story **non implémentée** à un statut qui dit le contraire. Lecture retenue, sans trancher à la place de ClaudeBox : la story et `sprint-status.yaml` restent `backlog` (conforme à l'AC de la commande « `backlog` ou équivalent initial, pas `ready-for-dev` »), et `ready-for-UX-validation` est le **statut cible après implémentation** (AC34). À corriger par ClaudeBox si une autre lecture était voulue.
- **Branche.** Le travail de cette session est sur la branche imposée par la plateforme cloud (`claude/story-25-4-master-detail-7w4ygv`) et non sur `story/25-4-vue-maitre-detail-c`, déjà poussée à `a5ba89b`. Les deux partent du même commit. Précisé dans la PR.

## Change Log

- 2026-10-19 — Création (`create-story`, session cloud déléguée) : story rédigée, statut `backlog`, 34 AC, 12 décisions déjà arbitrées consignées, 14 questions ouvertes pour ClaudeBox / Alexandre avec recommandation ; `ready-for-dev` non accordé ; statut cible après implémentation `ready-for-UX-validation` (validation UX finale en 25.5).
- 2026-10-19 07:45 — Relecture ClaudeBox : Q1 à Q14 = A (repli `sessionStorage` pour Q1 si le core intercepte le fragment ; « Appliquer » direct seulement sur `to_apply` pour Q11), précisions sur l'AC29 (5), les vrais clics (#299), « Sans pièce », la taille de la story et le statut ; `ready-for-dev`.
- 2026-10-19 — `dev-story` (session cloud déléguée) : implémentation AC1 à AC34 sur la branche de la plateforme, Tasks 1 à 10 faites, Tasks 0 et 11 sautées (CC-48) ; statut `review` ; la preuve terrain, `ready-for-UX-validation` et la validation UX (25.5) restent à ClaudeBox.
- 2026-10-19 12:20 — Correctif ClaudeBox après le gate sur la box (parcours `vue-maitre-detail-c`, étape 8 `precedent-ne-remonte-pas` ; requête `GET /index.php?…&ajax=…` bloquée) : le cœur Jeedom (`desktop/common/js/utils.js`) recharge la page par `jeedomUtils.loadPage` sur tout `popstate` dont l'état n'est pas `null`. Les entrées de la vue portent désormais un état `null` ; la profondeur est tenue par la vue (`st.hist` / `st.pushed`). Réserve Q1 levée sur ce point ; test de cohabitation ajouté.
