# Story 25.3 : Page principale B — barre de santé, jauge maison filtrante, cartes de pièce

Status: ready-for-dev

> **Statut : `ready-for-dev` (2026-10-19 03:25, relecture et décisions ClaudeBox par délégation d'Alexandre du 2026-10-18 23:50 — § Décisions).** Précédemment : `backlog` (2026-10-19). Story rédigée par une session cloud déléguée (`create-story`, documentaire : aucun code, aucun test, aucun accès box / VM / Home Assistant / secret, CC-48). **`ready-for-dev` n'est pas accordé** : relecture ClaudeBox obligatoire, puis décisions sur les questions Q1 à Q11 (§ Questions ouvertes, chacune avec une recommandation). Les points listés en § Décisions déjà arbitrées sont **fermés** (ils viennent de l'epic, de 25.1 et de 25.2) et ne sont pas rouverts ici. Pointeurs de code pris sur `main` à `04edf79` (après 25.1 : #279 `a704dd0`, R2 #282 `c940ac3` ; après 25.2 : #288 `2b451dd`, preuve terrain #289). Aucun nom réel d'équipement, de pièce, de scénario ou de personne : identifiants et données fictives seulement (CC-48).

## Story

En tant que propriétaire qui ouvre la page du plugin,
je veux voir **dès le premier écran** combien d'équipements sont publiés dans Home Assistant, lesquels sont bloqués ou attendent d'être appliqués, et dans quelles pièces, avec une jauge de la maison dont chaque segment filtre la liste, des cartes de pièce qui portent leur propre état, et des actions rangées par importance,
afin de savoir **sans rien ouvrir** s'il reste un problème dans la maison, au lieu d'ouvrir les pièces une à une.

**Parcours : interface (`desktop/php/`, `desktop/js/`, `desktop/css/`), docs, tests Node/PHP, gate 20-0.** Elle **consomme** la route `getEquipmentStates` livrée par 25.2 ; **aucune modification du démon** (AC16). La fenêtre de pièce (modale) reste celle de 25.1 : son remplacement par la vue maître-détail est 25.4.

## Décisions déjà arbitrées

Ces points sont **fermés** ; la story les applique sans les rediscuter. Source entre parenthèses.

1. **Un seul appel au chargement, jamais de boucle par équipement.** La page lit les états par **un** appel de l'action ajax `getEquipmentStates` (relais PHP livré par 25.2, route démon `GET /system/equipment_states`). (CADRAGE « Performance » ; 25.2 Q9 A.)
2. **Une seule fonction d'état.** L'état affiché par équipement est `resolveEquipmentState(entrée, enabled)` de 25.1 (D1), alimentée par l'entrée de la route et par `enabled` de `j2haRoomsTree`. Aucune règle d'état, aucune partition « Ignorée / Bloquée », aucune table de libellés n'est réécrite côté page B. (25.2 décisions 1-3, Q1 A, Q2 A.)
3. **La réconciliation « non lu » est faite par le client.** Un `eq_id` de `j2haRoomsTree` absent de `payload.equipments` est « non lu » ; le démon n'émet jamais `not_in_topology`. (25.2 Q3 bis A, § Contrat.)
4. **Pas de temps réel poussé.** Jauges et états recalculés : à l'ouverture de la page, après chaque action utilisateur, à chaque fin de synchro, et par le bouton « Actualiser ». Pas de polling périodique, pas de WebSocket. (epic-25-draft, Q2 de cadrage ; 25.2 Q13.)
5. **`refresh=1` est réservé au bouton « Actualiser ».** Le démon invalide lui-même son cache à la fin de chaque synchro, après chaque écriture d'override et après chaque action Publier / Supprimer / Republier (25.2 AC11-AC13) : la page n'a donc jamais à contourner le cache. (25.2 Q8 A, Q13 oui.)
6. **`available:false` et `meta.action_in_progress:true` sont des états de rendu à part entière**, pas des erreurs. (25.2 Q7 A, Q12 A.)
7. **Le bandeau bleu disparaît** ; une ligne d'aide discrète, avec lien vers la doc, le remplace. (diagnostic P5.)
8. **Barre de santé compacte** (démon, MQTT, dernière synchro, dernière opération) avec les actions courantes à droite et un menu « ⋯ » (télécharger le diagnostic ; supprimer tout de Home Assistant, en rouge, séparé par un trait). (epic-25-draft §25.3 ; diagnostic P5.)
9. **Jauge maison** « N publiés sur M », segments cliquables = filtres **globaux** (toutes pièces) ; **cartes de pièce** avec jauge segmentée et repères « N bloqués » / « N à appliquer ». (epic-25-draft §25.3 ; diagnostic P1.)
10. **Icône et couleur Jeedom des objets, cartes regroupées par objet parent** sont traitées **ici** et pas en 25.1. (25.1 Q8, tranchée le 2026-10-18.)
11. **Vocabulaire et palette de 25.1** : Publié / À appliquer / Bloqué / Exclu / Désactivé / Rien à publier ; vert / bleu / orange / gris ; rouge réservé aux boutons destructifs dans leur confirmation et dans le menu « ⋯ ». Aucune couleur en dur ; variables `--j2ha-*`. (25.1 D4, D5.)
12. **Statut cible après implémentation : `ready-for-UX-validation`**, pas `done`. La validation UX finale d'Alexandre est portée par **25.5**. Voir § « Statut cible et validation UX ».

## Sources lues

- `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/epic-25-draft.md` §25.3 et décisions de cadrage Q1-Q4 ; `…/CADRAGE.md` (direction B, contraintes Jeedom, performance) ; `…/diagnostic-ux.md` P1, P5, P6, P9, P14 et § 5 points 4 et 9 ; `…/maquettes.html`, onglet B (barre de santé, bloc maison, légende en puces, liseré orange des pièces à traiter, liste filtrable).
- `_bmad-output/implementation-artifacts/25-1-socle-etat-unique-glossaire-palette-theme.md` : D1 (`resolveEquipmentState(tree, enabled)`), D3, D4, D5, AC24 (gate), AC25 (4.4), Q8 (icône/couleur et regroupement reportés ici), décisions du 2026-10-18 19:20.
- `_bmad-output/implementation-artifacts/25-2-route-agregee-cote-demon.md` : § Contrat final, AC5, AC7, AC8, AC11, Q3 bis, Q7, Q8, Q9, Q12, Q13, Dev Agent Record ; `25-2-preuve-terrain-2026-10-19.md` (mesures du parc réel, point d'attention sur la taille).
- Code (lecture seule, `main` `04edf79`) : `desktop/php/jeedom2ha.php` (`j2haRoomsTree` `:12-56`, bandeau de santé `:68-88`, zone d'actions `:90-122`, export diagnostic `:119-131`, bandeau `alert-info` `j2ha-surface-intro` `:137`, cartes `:147-153`) ; `desktop/js/jeedom2ha.js` (`refreshBridgeStatus` `:19`, `applyHAGating` `:137`, `triggerTopologyRescan` `:348`, `triggerPublierAction` `:389`, `triggerSupprimerAction` `:410`) ; `desktop/js/jeedom2ha_mapping_override.js` (`resolveEquipmentState` `:951`, `summarizeEquipmentCounters` `:1144`, `summarizeRoom` `:1167`, `buildRoomCounterLabels` `:1202`) ; `desktop/js/jeedom2ha_mapping_surface.js` (`window.j2haOpenRoom` `:1603`, cartes en `objectDisplayCard` + `onclick`, jamais `eqLogicDisplayCard`) ; `core/ajax/jeedom2ha.ajax.php:940` (relais `getEquipmentStates`, `refresh=1` optionnel) ; `core/class/jeedom2ha.class.php:758` (le dépôt lit déjà `father_id` des objets Jeedom) ; `tests/e2e/gate/lib/policy.mjs` (`getEquipmentStates` déjà inscrit dans les lectures autorisées) et `tests/e2e/gate/parcours/*.mjs` (5 parcours).

## Contexte et périmètre

### Ce qui existe aujourd'hui (relevé sur `04edf79`, à re-vérifier au SHA courant)

- **La page principale** empile : tuile « Configuration », bandeau de santé (`div_bridgeHealthBanner`, rempli par `refreshBridgeStatus` via `getBridgeStatus`), zone « Actions Home Assistant » (3 boutons de même poids, dont « Supprimer de Home Assistant… », `data-ha-action`, `bt_rescanTopology`, gating par `applyHAGating`), export du diagnostic (case « Pseudonymiser » + bouton), **bandeau bleu** `alert alert-info j2ha-surface-intro` (une phrase d'environ 40 mots), puis la grille de cartes `#j2ha_roomCards` : une porte `fa-door-open` identique, le nom, le nombre d'équipements entre parenthèses. **Aucune carte ne porte d'état** (diagnostic P1).
- **Aucune lecture d'état au chargement.** Les arbres ne sont lus qu'à l'ouverture d'une pièce (un `getMappingOverrides` par équipement). 25.2 a livré la route agrégée et son relais ; **aucune page ne les appelle encore** (25.2 AC18).
- **`j2haRoomsTree`** donne, par pièce, `object_id`, `object_name`, `parent_number` et les équipements `{eq_id, eq_name, enabled}` ; la pseudo-pièce `object_id = 0` rassemble les équipements sans objet. Les objets **sans équipement propre sont omis** (`continue` quand la liste est vide). `parent_number` est lu dans la configuration de l'objet : ce n'est **pas** l'identifiant du parent (→ Q2).
- **Fonctions d'état prêtes pour la page B** : `summarizeRoom(trees, totalEquipments, enabledById)` rend `equipments_total`, `equipments_read`, `by_state`, `equipments_presence_unknown`, `defects` ; `buildRoomCounterLabels` rend la ligne de mots par état. Elles ont été écrites en 25.1 pour être alimentées par des arbres ; 25.2 AC4 prouve que l'entrée agrégée donne le même résultat que l'arbre complet.
- **La route agrégée** (contrat final de 25.2) : `payload.{schema_version, available, meta.{generated_at, generation, cache.{hit, build_ms}, equipments_total, equipments_read, action_in_progress}, equipments{"<eq_id>"…}, unread[]}`, et `reason:"action_in_progress"` quand `available:false` vient du verrou d'action. Pas d'index `rooms`, pas d'`enabled`, pas d'état résolu.
- **Mesure terrain de 25.2** (parc réel, 292 équipements) : froid 314 ms, chaud 136 à 322 ms, build démon 172 à 185 ms, **réponse 1 342 346 octets côté démon, soit 89 % du budget de 1 500 000** (point d'attention reporté ici, AC7).

### Dans le périmètre

- chargement et consommation de `getEquipmentStates` par la page principale (AC1 à AC7) ;
- barre de santé compacte, actions, menu « ⋯ », suppression du bandeau bleu, ligne d'aide (AC8, AC9) ;
- jauge maison, filtres globaux et liste des équipements filtrés (AC10, AC11) ;
- cartes de pièce avec jauge et repères (AC12) ;
- icône et couleur Jeedom des objets, regroupement par objet parent (AC13), y compris l'extension additive de `j2haRoomsTree` côté PHP ;
- libellés, documentation, thème, accessibilité (AC14, AC15) ;
- extension du gate 20-0 (AC17).

### Hors périmètre (ne pas faire ici)

- toute modification de `resources/daemon/` ; de `core/ajax/` (le relais de 25.2 suffit) ; du contrat de décision, des artefacts figés (`models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`) et des tables de mapping ;
- la **fenêtre de pièce** (modale) : structure, contenu et lectures par équipement restent ceux de 25.1. Elle n'est **pas** alimentée par la route agrégée (une seule source par vue tant que 25.4 n'a pas remplacé la modale) ;
- la vue maître-détail, l'arbre filtrable, l'état d'URL, le retrait de la modale (25.4) ; la recette UX finale et les captures de promotion (25.5) ;
- tout temps réel poussé, tout polling périodique ;
- toute mesure sur la box, la VM ou Home Assistant réels (CC-48) ; flags beta / stable / Market ; autres plugins ; dongles.

## Définitions normatives

### D1 — Données de la page

- `rooms` = `j2haRoomsTree` (seule source des pièces, de leurs noms, de leur ordre, de leur appartenance et de `enabled`). `equipments` = `payload.equipments` de la route, clés `String(eq_id)`.
- Pour chaque équipement `e` de `j2haRoomsTree` : si `equipments[String(e.eq_id)]` existe, état = `resolveEquipmentState(equipments[…], e.enabled)` ; sinon **non lu** (hors des 6 états : ce n'est pas un 7ᵉ état).
- Un `eq_id` présent dans `payload.equipments` mais absent de `j2haRoomsTree` (équipement supprimé ou d'un type exclu depuis la dernière synchro) est **ignoré** par la page : `j2haRoomsTree` fait foi pour ce qui est affiché.
- **M** (dénominateur de la jauge maison) = nombre d'équipements de `j2haRoomsTree`, toutes pièces confondues, pseudo-pièce comprise. **N** = nombre d'équipements à l'état `published`. Les segments (publiés, à appliquer, bloqués, « exclus et autres » — Q4 —, non lus) **somment à M**.
- Le nombre de pièces annoncé sous le chiffre = pièces de `j2haRoomsTree` avec `object_id > 0`.

### D2 — États de rendu de la lecture

| Réponse reçue | Rendu |
|---|---|
| `available:true`, `meta.action_in_progress:false` | Rendu normal. |
| `available:true`, `meta.action_in_progress:true` | Rendu normal **et** mention discrète « Opération en cours : ces chiffres peuvent changer » (`role="status"`) ; une relecture est planifiée (Q6). |
| `available:false`, sans `reason` (avant la première synchro) | Jauge maison vide et neutre, texte « Aucune synchronisation n'a encore eu lieu » ; « Relire Jeedom » mis en évidence ; cartes **sans jauge** (nom, icône, nombre d'équipements comme aujourd'hui) ; aucune relecture automatique. |
| `available:false`, `reason:"action_in_progress"` | Si des chiffres valides sont déjà en mémoire dans la page : ils restent affichés, atténués, avec la mention ci-dessus. Sinon : jauge neutre « Mise à jour en cours… ». Une relecture est planifiée (Q6). |
| erreur ajax, délai dépassé (15 s du relais) ou `status` ≠ `ok` | Jauge neutre « Chiffres indisponibles », message sans détail technique, bouton « Actualiser » actif ; les derniers chiffres valides, s'il y en a, restent affichés atténués. |

Les libellés exacts de cette table sont ceux de l'AC4 ; ils entrent au glossaire de la story.

### D3 — Gestion de l'état en mémoire de la page

La page garde **une seule** copie de la dernière réponse valide (`payload.equipments` n'est ni cloné, ni re-sérialisé par pièce) et la date locale de lecture. Les agrégats par pièce et par maison sont **dérivés** à chaque rendu, jamais stockés comme une seconde vérité.

## Acceptance Criteria

Convention : chaque AC est vérifiable par un test nommé (Node, PHP, parcours du gate 20-0) ou par une commande dont le résultat est écrit dans l'AC. « Vert / bleu / orange / gris » désignent les rôles de 25.1 D5, jamais une valeur de couleur littérale.

### A. Données, états de rendu et fraîcheur

**AC1 — Un seul appel au chargement, jamais de boucle**
**Given** la page principale chargée avec une fixture de ≥ 3 pièces et ≥ 40 équipements fictifs
**When** la page s'initialise
**Then** l'espion ajax compte **exactement un** appel `getEquipmentStates`, **sans** paramètre `refresh`, et **zéro** `getMappingOverrides` (test `test_story_25_3_chargement_unique.node.test.js`)
**And** une recherche de texte (`grep -n "getEquipmentStates" desktop/js/*.js desktop/php/*.php`) ne trouve l'action qu'**à un seul endroit** de la couche ajax de la page (une fonction de lecture), et ce site d'appel n'est atteignable depuis aucune boucle sur les pièces ou les équipements (test statique + test de comportement : 100 équipements, toujours 1 appel)
**And** l'inventaire des requêtes du gate (`tests/e2e/gate/page-load-request-inventory.mjs`) compte, au chargement de la page, **une** occurrence de `getEquipmentStates` et **aucune** de `getMappingOverrides`.

**AC2 — Un seul calcul d'état, aucune réécriture**
**Given** les entrées de la route et `j2haRoomsTree`
**When** la page calcule l'état d'un équipement, d'une pièce et de la maison
**Then** l'état de l'équipement est le retour de `resolveEquipmentState(entrée, enabled)` avec `enabled` lu **dans `j2haRoomsTree`** (jamais dans la réponse de la route, qui n'en porte pas) ; les agrégats par pièce passent par `summarizeRoom` ; l'agrégat maison est la somme des agrégats de pièce
**And** `git diff main...HEAD -- desktop/js/jeedom2ha_mapping_override.js` ne modifie **aucune** ligne des fonctions `resolveEquipmentState`, `analyzeEquipment`, `classifyCommandCategory`, `categoryOfCause`, `summarizeEquipmentCounters`, `summarizeRoom` (seuls des ajouts de fonctions pures, p. ex. `summarizeHouse`, et leurs exports sont admis)
**And** un test table-driven fait varier `enabled ∈ {true, false}` sur un même équipement et vérifie « Désactivé » prime sur « Exclu », comme en 25.1 R3/R4, avec les valeurs venant de `j2haRoomsTree`
**And** `grep -n "COMMAND_CAUSE_CATEGORIES\|categoryOfCause" desktop/js/jeedom2ha_overview.js desktop/php/` (ou le fichier qui porte la page B) ne trouve rien : la partition D3 de 25.1 n'est pas dupliquée.

**AC3 — Réconciliation : « non lu »**
**Given** un `j2haRoomsTree` contenant un `eq_id` (p. ex. 998) absent de `payload.equipments`, avec ou sans entrée dans `payload.unread`
**When** la page calcule la pièce et la maison
**Then** l'équipement est compté **non lu** : `summarizeRoom` reçoit `totalEquipments` du `j2haRoomsTree` et les seules entrées présentes, donc `equipments_total − equipments_read` = nombre de non lus de la pièce
**And** la carte et le bloc maison affichent « N non lu(s) » en mention grise (accord du pluriel par le code, jamais « non lu(s) »), les segments somment toujours à M (segment neutre « non lus », D1), et un équipement non lu n'est **jamais** compté publié, bloqué, exclu ni désactivé
**And** les clés de `payload.equipments` (chaînes) sont rapprochées des `eq_id` entiers de `j2haRoomsTree` (test : `"101"` ↔ `101`)
**And** un `eq_id` de `payload.equipments` absent de `j2haRoomsTree` est ignoré sans erreur (D1).

**AC4 — `available:false` et `action_in_progress:true` rendus explicitement**
**Given** les cinq réponses de la table D2 (fixtures JSON)
**When** la page les reçoit
**Then** chaque cas produit le rendu de la table D2, avec les libellés exacts suivants (glossaire, sans point final dans les étiquettes) : « Aucune synchronisation n'a encore eu lieu » ; « Opération en cours : ces chiffres peuvent changer » ; « Mise à jour en cours… » ; « Chiffres indisponibles »
**And** aucun de ces cas ne lève d'exception ni n'affiche « NaN », « undefined » ou « 0 publiés sur 0 » ; un `available:false` n'affiche **jamais** une jauge pleine de « non lus » (ce serait une fausse alarme)
**And** dans les cas « avant première synchro » et « erreur », les actions de la barre de santé restent soumises au gating existant (`applyHAGating`), inchangé
**And** les mentions sont des zones `role="status"` `aria-live="polite"`, et l'état n'est jamais porté par la seule couleur.

**AC5 — `refresh=1` réservé à « Actualiser »**
**Given** la page principale
**When** on exerce : ouverture de la page, fin de synchro, action utilisateur, relecture planifiée par l'AC4 (Q6), retour sur l'onglet du navigateur
**Then** aucun appel n'est émis avec `refresh=1` ; **seul** le clic sur « Actualiser » émet **un** appel `getEquipmentStates` avec `refresh=1` (test Node sur l'espion ajax)
**And** `grep -n "refresh" desktop/js/*.js` ne montre le paramètre que dans la fonction appelée par le gestionnaire du bouton « Actualiser »
**And** pendant que le bouton « Actualiser » attend sa réponse, il est désactivé (pas de double appel) et indique l'attente.

**AC6 — Quand les chiffres sont recalculés**
**Given** la page principale
**When** l'un des événements suivants se termine (succès **ou** échec, car un échec peut avoir changé l'état, comme en 22-2 Q8 A)
**Then** les jauges et les états sont relus par **un** appel sans `refresh` : (a) ouverture de la page ; (b) fin de « Relire Jeedom » (synchro) ; (c) fin de « Republier tout » ; (d) fin de « Supprimer tout de Home Assistant… » ; (e) fin de chaque action de la fenêtre de pièce (enregistrer un réglage, Appliquer, Republier la pièce, Supprimer de Home Assistant) selon la granularité de Q7 ; (f) clic sur « Actualiser » (avec `refresh=1`, AC5)
**And** un test par événement vérifie « un événement terminé → un appel », et que **deux événements rapprochés se coalescent** en un seul appel (Q7)
**And** aucune relecture n'a lieu hors de ces événements : pas de minuterie périodique, pas d'écoute de `visibilitychange` ou de `focus` (Q10), vérifié par recherche de texte (`setInterval`, `visibilitychange`).

**AC7 — Taille de la réponse : point de vigilance, pas de réduction silencieuse**
**Given** la mesure de 25.2 sur le parc réel : **1 342 346 octets côté démon (1 242 700 reçus par le navigateur), soit 89 % du budget de 1 500 000**, froid 314 ms, chaud 136 à 322 ms ; budgets Q10 de 25.2 : taille ≤ 1 500 000 octets, bout en bout ≤ 6 s à froid et ≤ 500 ms à chaud
**When** 25.3 consomme la route
**Then** la story **ne modifie ni la liste blanche de la route, ni le budget de taille, ni les budgets de temps** ; toute évolution passe par une décision explicite (Q8)
**And** la page ne multiplie pas la charge : une seule copie de la réponse en mémoire (D3), pas de clonage ni de re-sérialisation par pièce (test : `JSON.stringify` n'est appelé sur aucune partie de `payload.equipments`)
**And** le temps de calcul des agrégats côté navigateur sur une fixture de 292 équipements de la forme la plus lourde du corpus de 25.2 est consigné dans le Dev Agent Record (mesure Node, sans seuil inventé ici) ; la page reste interactive pendant le rendu (pas de boucle bloquante au-delà d'un cycle de rendu)
**And** la preuve terrain (Task 8) relève, par ClaudeBox, la taille reçue, la taille côté démon (ligne `[AGGREGATE] … bytes=`), le temps bout en bout à froid et à chaud **depuis la page B**, et les compare à 1 342 346 octets et aux budgets ci-dessus ; **la story ne passe pas à `ready-for-UX-validation` si un budget est dépassé** (elle le consigne et rouvre Q8, elle ne le relève pas)
**And** le risque est inscrit au Dev Agent Record (« croissance du parc ») et suivi dans la preuve terrain.

### B. Interface

**AC8 — Le bandeau bleu disparaît**
**Given** la page principale
**When** elle est rendue
**Then** aucun élément `.alert.alert-info.j2ha-surface-intro` n'existe (`grep -rn "j2ha-surface-intro" desktop/` ne renvoie plus que, au plus, la classe CSS d'une **ligne d'aide** neutre) ; aucune zone bleue pleine largeur n'ouvre la section
**And** sous le titre « Configuration Home Assistant par pièce », une ligne d'aide discrète (texte normal, `text-muted`, une phrase de 20 mots ou moins, sans jargon « prêt / bloquant ») renvoie à la documentation (Q9)
**And** le texte conservé de l'ancien bandeau qui dit que le type natif Jeedom est partagé avec Homebridge est reporté en **note de l'aide**, pas en bandeau ; le mot « Homebridge » reste admis (25.1 D4)
**And** un test Node (DOM factice) vérifie l'absence du bandeau et la présence de la ligne d'aide.

**AC9 — Barre de santé compacte, actions et menu « ⋯ »**
**Given** la page principale
**When** elle est rendue
**Then** la barre de santé tient sur **une ligne** (qui se replie proprement sous 768 px) et affiche les quatre briques de `getBridgeStatus` — Démon, MQTT, Dernière synchro, Dernière opération — chacune avec un **point d'état + un libellé court** (le mot est toujours présent) ; l'adresse du broker passe en infobulle (`title`) ; les éléments conservent les identifiants `span_healthBridge`, `span_healthMqtt`, `span_healthMqttBroker`, `span_healthSync`, `span_healthOp`, `span_healthOpMsg` utilisés par `refreshBridgeStatus` et par le gate
**And** à droite de la barre : deux boutons de poids normal, « Republier tout » et « Relire Jeedom » (conservent `data-ha-action="republier"`, `data-ha-action="rescan"`, `bt_rescanTopology` et le gating existant, `div_haGatingReason` compris), puis un bouton-icône « ⋯ » (`aria-label` « Plus d'actions », `aria-haspopup="menu"`, `aria-expanded`)
**And** le menu « ⋯ » contient, dans cet ordre : « Télécharger le diagnostic… », un séparateur, « Supprimer tout de Home Assistant… » (seul élément **rouge**, `data-ha-action="supprimer-recreer"` conservé, même gating, même confirmation forte `btn-danger` qu'aujourd'hui) ; il s'ouvre au clic et au clavier, se ferme par Échap et clic extérieur, et rend le focus au bouton
**And** « Télécharger le diagnostic… » ouvre une boîte de dialogue qui porte la case « Pseudonymiser les noms d'équipements » (libellé inchangé) et le bouton de téléchargement ; **le comportement d'export est inchangé** (même action ajax, mêmes paramètres, mêmes garanties de pseudonymisation) ; la case et le bouton ne sont plus posés en pleine page
**And** aucune action destructrice n'est visible hors du menu ; « Supprimer tout » n'a plus le même style qu'un bouton courant (diagnostic P5)
**And** la tuile « Configuration » (`gotoPluginConf`) n'est pas modifiée.

**AC10 — Jauge maison « N publiés sur M »**
**Given** la lecture réussie (D2, cas normal)
**When** le bloc maison est rendu
**Then** il affiche en grand « N » avec « publiés sur M » (pluriel accordé : « 1 publié sur 1 »), la ligne « équipements Jeedom, P pièces » (D1), et une jauge segmentée dont les largeurs sont proportionnelles à M, dans l'ordre : publiés (vert), à appliquer (bleu), bloqués (orange), exclus et autres (gris, Q4), non lus (motif neutre)
**And** la jauge est un seul élément `role="img"` dont l'`aria-label` dit les mêmes nombres en toutes lettres ; les segments de largeur nulle ne sont pas rendus ; la somme des segments est égale à M (test d'invariant sur 20 fixtures aléatoires seedées)
**And** la légende est une rangée de **puces** (`<button aria-pressed>`) : « N publiés », « N bloqués », « N à appliquer », « N exclus et autres » (Q4), plus « N non lus » si > 0 ; les puces à zéro restent affichées mais **désactivées** (`disabled`) pour ne pas déplacer la mise en page
**And** le bloc maison porte le bouton « Actualiser » (AC5) et la mention « Chiffres relus à HH:MM » (heure **locale de la lecture**, Q10)
**And** ce bloc ne dit jamais « Sera publié » ni « prête(s) » (glossaire 25.1, test de glossaire étendu).

**AC11 — Filtres globaux : chaque segment filtre toutes les pièces**
**Given** le bloc maison de l'AC10
**When** l'utilisateur clique sur une puce ou sur le segment correspondant de la jauge (même gestionnaire, même `aria-pressed`)
**Then** **sans aucune requête réseau** (le test vérifie 0 appel ajax), la page affiche, entre le bloc maison et la grille, la **liste des équipements à cet état, toutes pièces confondues** : une ligne par équipement avec l'état (mot + icône + teinte), le nom (`eq_name` de `j2haRoomsTree`), la pièce, et la mention « N bloquées » (orange) lorsque `blocked_mention` > 0 ; l'ordre est celui de la grille (pièces) puis l'ordre natif des équipements
**And** le filtre est à **sélection unique** : un second clic sur la même puce, la touche Échap ou un bouton « Tout afficher » le retire ; le nombre de lignes de la liste est égal au nombre annoncé sur la puce (test d'invariant)
**And** le filtre « exclus et autres » (Q4) regroupe exclus, désactivés et rien à publier, chaque ligne gardant son propre mot d'état
**And** l'effet du filtre sur la grille de cartes et l'action du clic sur une ligne suivent Q1 (par défaut : cartes sans correspondance atténuées et non masquées ; un clic sur une ligne ouvre la fenêtre de la pièce)
**And** le filtre n'est pas mémorisé dans l'URL (l'état d'URL est livré par 25.4) et se réinitialise à chaque relecture complète de la page ; après une relecture des états (AC6), un filtre actif est **réappliqué** aux nouveaux chiffres (la liste reste cohérente avec la jauge).

**AC12 — Cartes de pièce : jauge segmentée et repères**
**Given** une lecture réussie
**When** la grille est rendue
**Then** chaque carte affiche : l'icône de l'objet (AC13, 20 à 24 px), le nom, « n / t publiés » (n = publiés de la pièce, t = équipements de la pièce), une **jauge segmentée** fine (mêmes teintes et mêmes règles que l'AC10, sommant à t, `role="img"` avec `aria-label` complet) et, **seulement s'ils sont non nuls**, les repères « N bloqués » (orange), « N à appliquer » (bleu) et « N non lus » (gris) ; les zéros sont masqués
**And** une carte avec au moins un équipement à l'état `blocked` porte un **liseré orange** (maquette B) ; aucune autre teinte de liseré n'est utilisée
**And** les compteurs d'une carte sont ceux de `summarizeRoom` pour cette pièce (test d'invariant : la somme des cartes = le bloc maison, pour chaque état, y compris les non lus)
**And** la pseudo-pièce « Sans pièce » (`object_id = 0`) est rendue comme les autres, avec l'icône de repli
**And** `objectDisplayCard`, `cursor`, `j2ha-room-card`, `data-object_id` et `onclick="j2haOpenRoom(…)"` sont conservés : le clic ouvre la fenêtre de pièce **inchangée** de 25.1 (le plugin n'utilise pas `eqLogicDisplayCard`, que le core détourne) ; la carte est opérable au clavier (`tabindex="0"`, Entrée/Espace) et son nom accessible inclut l'état résumé
**And** avant la première synchro (D2), les cartes n'ont pas de jauge (nom, icône, nombre d'équipements comme aujourd'hui).

**AC13 — Icône et couleur Jeedom des objets, regroupement par objet parent (reprise de 25.1 Q8)**
**Given** `j2haRoomsTree` étendu côté PHP (Q2, Q3) avec, pour chaque pièce, `father_id`, l'icône et la couleur de l'objet Jeedom
**When** la grille est rendue
**Then** chaque carte reprend l'**icône** choisie par l'utilisateur dans Jeedom pour l'objet (porte `fa-door-open` en repli seulement : icône absente, vide ou rejetée par la validation) et sa **couleur** selon Q3 (accent de l'icône ; jamais une teinte d'état)
**And** les cartes sont **regroupées par objet parent** : un sous-titre de groupe par parent (Q2), les cartes enfants dessous, l'ordre natif de Jeedom conservé à l'intérieur de chaque groupe ; un objet sans parent ni enfant, et la pseudo-pièce, ne portent pas de sous-titre
**And** l'extension de `j2haRoomsTree` est **additive** : les champs existants (`object_id`, `object_name`, `parent_number`, `equipments[].{eq_id, eq_name, enabled}`) ne changent ni de nom ni de type, et `sendVarToJS('j2haRoomsTree', …)` reste l'unique canal ; les consommateurs existants (`summarizeRoom`, `j2haOpenRoom`, tests 20.1/20.3) passent sans modification
**And** le HTML d'icône de Jeedom n'est **jamais injecté brut** : il est réduit côté PHP à une liste blanche de classes CSS (Q3) puis échappé ; une couleur qui n'est pas un littéral hexadécimal valide est ignorée ; test PHP sur des entrées hostiles fictives (`"><script>`, `javascript:`, classe inconnue, couleur `red;background:url(...)`) → repli sûr
**And** la couleur Jeedom n'est jamais utilisée comme fond de texte ni comme couleur de texte (contraste non maîtrisé sur les deux thèmes) ; elle teinte l'icône et un filet de la carte, avec un repli `--j2ha-*` si elle est absente
**And** aucune requête n'est ajoutée pour cela (les données sortent du même rendu PHP).

**AC14 — Glossaire, libellés, documentation**
**Given** `docs/fr_FR/index.md`, `docs/fr_FR/compteurs.md`, `docs/fr_FR/changelog_beta.md` et les tests de documentation de 25.1
**When** la story est livrée
**Then** `index.md` décrit la nouvelle page principale (barre de santé, actions, menu « ⋯ », jauge maison et filtres, cartes, « Actualiser », « non lu », regroupement par objet parent) et ne mentionne plus le bandeau ; `compteurs.md` (bloc `COMPTEURS:DEBUT/FIN` seul) décrit la jauge maison, les repères des cartes, « non lu » et ce qui n'est pas un état ; `changelog_beta.md` reçoit une entrée ; les emplacements `<!-- CAPTURE-A-PRENDRE -->` sont conservés (pas de captures, décision 20-5 Q3)
**And** `test_story_25_3_documentation.node.test.js` (successeur de `test_story_25_1_documentation`) vérifie l'absence des termes interdits de 25.1 AC23 et que chaque libellé cité dans la doc existe verbatim dans `desktop/` ou `core/`
**And** les libellés de la page B passent par `{{…}}` / `__()` (aucun fichier `core/i18n` n'existe dans le dépôt : ne pas en créer sans décision), sans point final dans les étiquettes, pluriels accordés par le code
**And** les tests de glossaire de 25.1 (`test_story_25_1_glossaire.node.test.js`) restent verts et sont étendus à `desktop/php/jeedom2ha.php` et au nouveau fichier JS.

**AC15 — Thème, palette, accessibilité**
**Given** les thèmes clair et sombre de Jeedom et le repli sans `data-theme` (25.1 Q6 A)
**When** la page B est rendue
**Then** toutes les couleurs viennent de variables `--j2ha-*` (avec replis) déjà définies en 25.1 ou ajoutées dans le même bloc, classes préfixées `.j2ha-…`, **aucune** couleur littérale ajoutée (test `test_story_25_3_palette_theme.node.test.js`, successeur de la vérification de 25.1) et aucun restylage global des classes du core
**And** les contrastes texte / fond des nouveaux éléments (puces, mentions, repères, liste filtrée) respectent les seuils vérifiés par le test de contrastes de 25.1 sur les deux thèmes ; les fonds d'état translucides ont leur repli `rgba()` quand `color-mix()` est absent (iPad mural)
**And** aucune information n'est portée par la seule couleur (mot + icône) ; puces, menu « ⋯ », cartes et boîte de dialogue sont opérables au clavier avec les rôles/états ARIA des AC9 à AC12 ; chaque bouton-icône a un `aria-label`
**And** la compatibilité Jeedom 4.4 est préservée comme en 25.1 AC25 (aucune API ni variable propre à 4.6 ; replis testés) ; le rendu réel 4.4 et le rendu réel du thème clair sur la box restent portés par 25.5.

### C. Non-régression, gate et statut

**AC16 — Aucune modification du démon ni des routes ; fenêtre de pièce inchangée**
**Given** la branche de la story
**When** on exécute `git diff --stat main...HEAD -- resources/daemon/ core/ajax/ scripts/deploy-to-box.sh scripts/parity-snapshot.sh scripts/deploy-inventory-diff.sh`
**Then** la sortie est **vide** ; `models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`, les tables de mapping et les fichiers *golden* sont inchangés ; le payload de découverte HA, les topics et les `unique_id` sont inchangés
**And** la page B n'écrit rien de nouveau : mêmes routes et mêmes corps de requête qu'avant pour toutes les écritures (publier, supprimer, republier, rescan, export) ; le gate le vérifie (AC17)
**And** la fenêtre de pièce (structure, contenu, lectures `getMappingOverrides` par équipement à l'ouverture d'une pièce) est **inchangée** : les suites `test_story_25_1_*`, `test_story_20_*`, `test_story_22_2_*` qui la concernent passent sans modification autre que celles imposées par le déplacement des boutons (AC9) et documentées dans le Dev Agent Record
**And** `resolveEquipmentState` et ses helpers ne sont pas modifiés (AC2) ; les suites `test_story_25_2_*` passent sans modification.

**AC17 — Gate 20-0 étendu aux parcours de la page B, sans affaiblissement**
**Given** les 5 parcours existants (`controle-ecriture-non-declaree`, `decouverte-piece-25-eq-579`, `exclusion-publication-non-publiee`, `reference-bascule-eq-380`, `rescan-page-principale`), `run-gate.mjs`, `lib/policy.mjs` et `page-load-request-inventory.mjs`
**When** la story est livrée
**Then** les parcours existants sont **adaptés** aux nouveaux emplacements des boutons (barre de santé, menu « ⋯ ») **sans retirer d'assertion ni relâcher une politique** (`test_story_20_0_gate_policy` vert) ; les sélecteurs conservés (`.j2ha-room-card`, `data-object_id`, `bt_rescanTopology`, `data-ha-action`, identifiants `span_health*`) évitent la réécriture là où c'est possible
**And** le scénario est **étendu** par un parcours en lecture seule (nom proposé : `page-principale-b.mjs`), avec les assertions suivantes : (1) au chargement, **un** `getEquipmentStates` sans `refresh` et **zéro** `getMappingOverrides` ; (2) le bandeau bleu est absent ; (3) la jauge maison somme à M et chaque carte somme à son total ; (4) un clic sur chaque puce non vide affiche la liste filtrée **sans requête réseau** ; (5) un clic sur « Actualiser » émet **un** `getEquipmentStates` avec `refresh=1`, et c'est le seul de la session ; (6) le menu « ⋯ » s'ouvre, contient les deux entrées attendues, et fermer la boîte de dialogue du diagnostic ou la confirmation de suppression n'émet **aucune écriture** ; (7) l'ouverture d'une carte ouvre la fenêtre de pièce existante (non-régression, ses lectures par équipement sont autorisées)
**And** `lib/policy.mjs` ne change pas d'action autorisée (`getEquipmentStates` y est déjà) ; si la politique actuelle ne distingue pas `refresh=1` dans l'URL ou le corps, l'assertion (5) est portée par le parcours lui-même, sans élargir la liste blanche (vérification au dev-story, à consigner)
**And** `page-load-request-inventory.mjs` : l'inventaire du chargement passe de « sans lecture d'état » à « une lecture d'état » ; aucune autre lecture n'est ajoutée ; le diff de l'inventaire est dans le Dev Agent Record
**And** les suites simulées `test_story_20_0_gate_*.node.test.js` et `test_story_20_3_gate_parcours.node.test.js` passent ; le gate contre la box réelle est **lancé par ClaudeBox** (pas par cette session, CC-48), son résultat est consigné dans la preuve terrain, et la story ne passe pas à `ready-for-UX-validation` sans lui.

**AC18 — Statut cible et validation UX**
**Given** la fin de l'implémentation
**When** ClaudeBox a consigné la preuve terrain (Task 8)
**Then** le statut de la story passe à **`ready-for-UX-validation`**, et **non à `done`** ; la validation UX finale d'Alexandre sur l'ensemble A + B + C est portée par **25.5** (décision Q1 du cadrage), pas par cette story
**And** cette section et le Dev Agent Record le disent explicitement ; **le statut courant reste `backlog`** jusqu'à `ready-for-dev` (relecture ClaudeBox).

**AC19 — Conventions de la story**
**Given** CLAUDE.md et `_bmad-output/project-context.md`
**When** la PR de dev est ouverte
**Then** une branche / une PR = ce sujet ; titre en Conventional Commits ; `make test`, `node --test tests/unit/*.node.test.js`, les tests PHP, `flake8` passent ; `scripts/ci-local.sh` est vert avant push
**And** fixtures et tests ne contiennent aucun nom réel d'équipement, de pièce, d'objet, de scénario ou de personne, ni IP privée ni secret (CC-48) ; les icônes et couleurs de test sont fictives
**And** les Tasks 0 et 8 (réservées à l'humain / ClaudeBox) sont sautées par la session cloud et la PR le dit.

## Statut cible et validation UX

- **Statut actuel :** `backlog`. Il n'est pas modifié par la création de la story.
- **Statut cible après implémentation et preuve terrain :** `ready-for-UX-validation`.
- **La validation UX finale n'a pas lieu en 25.3.** Elle est portée par **25.5** (« Recette UX finale et preuve terrain »), qui reprend aussi la validation UX transférée de 22-2 (Q1) et les preuves transférées de 25.1 (rendu réel du thème clair sur la box, rendu sur Jeedom 4.4). 25.3 fournit à 25.5 une page B prouvée par le gate 20-0 et par la preuve terrain ; elle ne demande pas d'avis esthétique à Alexandre avant 25.5.
- **Chemin des statuts :** `backlog` → `ready-for-dev` (relecture ClaudeBox + décisions Q1-Q11) → `review` (dev-story) → `ready-for-UX-validation` (preuve terrain ClaudeBox) → `done` à la clôture de 25.5.

## Tasks / Subtasks

- [ ] Task 0 (SAUTÉE par la session cloud : réservée à l'humain / ClaudeBox) — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) **[réservé à l'humain / ClaudeBox ; une session cloud NE LA FAIT PAS (CC-48 : aucun accès box, SSH ni Home Assistant)]**
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
  - [ ] Relever sur la box (identifiants seuls, CC-48) ce que renvoient `getDisplay('icon')` et `getDisplay('tagColor')` des objets (forme du HTML d'icône, valeurs de couleur) et la forme réelle de `father_id` (alimente AC13, Q2, Q3).
- [ ] Task 1 — Tests d'abord, données et états (AC: 1, 2, 3, 4, 5, 6)
  - [ ] 1.1 `test_story_25_3_chargement_unique.node.test.js` (AC1), `test_story_25_3_reconciliation_non_lu.node.test.js` (AC3), `test_story_25_3_etats_lecture.node.test.js` (AC4, table D2), `test_story_25_3_refresh_actualiser.node.test.js` (AC5, AC6).
  - [ ] 1.2 Fixtures JSON fictives dérivées du corpus de 25.2 (`tests/fixtures/`), plus les cinq réponses de la table D2.
  - [ ] 1.3 Ajouter les fonctions pures d'agrégat (`summarizeHouse` ou équivalent) **par ajout** dans `jeedom2ha_mapping_override.js`, sans toucher `resolveEquipmentState` ni `summarizeRoom` (AC2).
- [ ] Task 2 — Couche de lecture et état de la page (AC: 1, 4, 5, 6, 7)
  - [ ] 2.1 Une fonction de lecture unique de `getEquipmentStates` ; copie unique en mémoire (D3) ; dérivation des agrégats à chaque rendu.
  - [ ] 2.2 Relectures déclenchées par les événements de l'AC6 (rattachement aux callbacks existants de `jeedom2ha.js` et de la fenêtre de pièce), coalescence, politique de Q6.
  - [ ] 2.3 Bouton « Actualiser » (`refresh=1`) et mention « Chiffres relus à HH:MM ».
- [ ] Task 3 — Page principale (AC: 8, 9, 10, 11, 12, 14, 15)
  - [ ] 3.1 Suppression du bandeau bleu, ligne d'aide (Q9).
  - [ ] 3.2 Barre de santé compacte, actions, menu « ⋯ », boîte de dialogue du diagnostic (identifiants et `data-*` conservés).
  - [ ] 3.3 Bloc maison : jauge, puces, liste filtrée globale (Q1, Q4, Q5).
  - [ ] 3.4 Cartes de pièce : jauge, repères, liseré, conservation de `j2haOpenRoom`.
  - [ ] 3.5 CSS `.j2ha-…` et variables `--j2ha-*` ; `test_story_25_3_palette_theme.node.test.js`.
- [ ] Task 4 — Icône, couleur et regroupement par objet parent (AC: 13)
  - [ ] 4.1 Extension additive de `j2haRoomsTree` (Q2, Q3) et test PHP (entrées hostiles).
  - [ ] 4.2 Regroupement, sous-titres de groupe, repli d'icône ; `test_story_25_3_hierarchie_objets.node.test.js`.
- [ ] Task 5 — Documentation (AC: 14)
  - [ ] 5.1 `index.md`, bloc `compteurs.md`, `changelog_beta.md` ; `test_story_25_3_documentation.node.test.js`.
- [ ] Task 6 — Gate 20-0 et non-régression (AC: 16, 17, 19)
  - [ ] 6.1 Adapter les 5 parcours sans retirer d'assertion ; ajouter `page-principale-b.mjs` ; mettre à jour l'inventaire de chargement ; lancer les suites simulées.
  - [ ] 6.2 `git diff --stat main...HEAD -- resources/daemon/ core/ajax/ …` vide ; suites `test_story_25_1_*` et `25_2_*` vertes.
  - [ ] 6.3 `make test`, `node --test tests/unit/*.node.test.js`, tests PHP, `flake8`, `scripts/ci-local.sh`.
- [ ] Task 7 — Vigilance taille (AC: 7)
  - [ ] 7.1 Mesure Node du calcul d'agrégats sur 292 équipements lourds ; test « une seule copie, aucun `JSON.stringify` sur `equipments` » ; consigner dans le Dev Agent Record.
- [ ] Task 8 (SAUTÉE par la session cloud : réservée à l'humain / ClaudeBox ; CC-48) — Preuve terrain (après fusion)
  - [ ] 8.1 Gate 20-0 contre la box, parcours de l'AC17 compris ; résultat dans `25-3-preuve-terrain-<date>.md` (identifiants seuls).
  - [ ] 8.2 Mesure de la taille et des temps depuis la page B, comparaison aux budgets de 25.2 et à 1 342 346 octets (AC7).
  - [ ] 8.3 Vérification **à la main, hors gate** (le gate interdit toute écriture) que les chiffres changent sans `refresh=1` après une écriture d'override puis après une synchro : c'est la mesure que 25.2 a laissée à 25.3 (« on le revérifiera par l'usage en 25.3 »).
  - [ ] 8.4 Rendu sombre sur Jeedom 4.6.1 ; icône et couleur réelles des objets ; passage du statut à `ready-for-UX-validation`.

## Dev Notes

### Dev Agent Guardrails

- **Ne jamais** modifier `resources/daemon/` ni `core/ajax/` (AC16), ni `models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`.
- **Ne jamais** recalculer un état, une catégorie de commande ni un compteur autrement que par `resolveEquipmentState` / `summarizeRoom` (AC2). Si une impossibilité technique apparaît, **s'arrêter** et la consigner en question, ne pas contourner.
- **Un seul appel** `getEquipmentStates` par lecture ; jamais dans une boucle ; `refresh=1` seulement dans le gestionnaire d'« Actualiser » (AC1, AC5).
- Ne pas appeler `getMappingOverrides` au chargement ; la fenêtre de pièce garde ses lectures par équipement (AC16).
- Le HTML d'icône d'un objet Jeedom est **non fiable** : liste blanche de classes côté PHP, échappement, jamais d'`innerHTML`/`.html()` sur cette valeur ; la couleur est validée (AC13).
- Libellés via `{{…}}` / `__()` ; **aucun fichier `core/i18n` n'existe dans le dépôt** : ne pas en créer sans décision.
- CSS préfixé `.j2ha-…`, jamais de restylage de `.label/.btn/.panel/.modal/.objectDisplayCard` ; utiliser `objectDisplayCard` + `onclick`, jamais `eqLogicDisplayCard`.
- Conserver les identifiants et attributs utilisés par `refreshBridgeStatus`, `applyHAGating`, les tests et le gate (AC9, AC12, AC17).
- Aucun nom réel dans les fixtures, tests, docs, commits, PR (CC-48).
- Une session cloud n'utilise jamais `scripts/deploy-to-box.sh` ni SSH ; elle saute les Tasks 0 et 8 et le dit dans la PR.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Contraintes Jeedom (CADRAGE, relevées sur 4.6.1 le 18/10)

- Page du plugin = HTML libre dans la zone de contenu ; thème via `<body data-theme>` et variables du core, complétées par `--j2ha-*` (25.1) ; jQuery 3.6, Bootstrap 3, bootbox, jeeDialog (seulement s'il est déjà employé), jeedomUtils, Font Awesome 5 local ; aucune bibliothèque ni police externe.
- Tester thèmes clair / sombre + bascule auto et compatibilité 4.4 (variables relevées sur 4.6.1 ; pas de VM 4.4 : replis testés, 25.1 Q10).
- `getDisplay('icon')` / `getDisplay('tagColor')` : cités par le diagnostic P14, **non vérifiés ici** (pas d'accès à une instance) → relevé en Task 0.

### Précédents réutilisables

- Pureté et tests d'états : `test_story_25_1_etat_unique.node.test.js` ; parité agrégé / unitaire : `test_story_25_2_parite_etat.node.test.js` et `tests/fixtures/story_25_2_parite_etat.json`.
- Menu « ⋯ » : composant de 25.1 (fenêtre de pièce) à réutiliser plutôt que d'en écrire un second.
- Refresh du bandeau après échec d'une action : 22-2 Q8 A (`refreshBridgeStatus` sur succès **et** échec) — même règle pour les chiffres (AC6).
- Harnais : `tests/unit/helpers/fake_dom.js`, `ui_harness.js`.

### Tests existants à surveiller

`test_story_25_1_*` (état, glossaire, palette, documentation), `test_story_25_2_parite_etat`, `test_story_16_8_mapping_surface`, `test_story_20_1_*` (pseudo-pièce `object_id=0`), `test_story_20_2_*`, `test_story_20_3_*`, `test_story_22_2_*`, `test_story_20_0_gate_*`, `test_story_20_3_gate_parcours`, tests PHP du relais (`test_story_a1_php_relay.php`).

### Fichiers probablement touchés (pour le `dev-story`)

`desktop/php/jeedom2ha.php` (bandeau, barre de santé, actions, menu, grille, extension de `j2haRoomsTree`) ; `desktop/js/jeedom2ha.js` (rattachement des relectures aux fins d'action) ; `desktop/js/jeedom2ha_mapping_override.js` (**ajouts** de fonctions pures et exports uniquement) ; **proposition** : nouveau `desktop/js/jeedom2ha_overview.js` (lecture, rendu de la page B), à inclure à côté des autres `include_file` ; `desktop/js/jeedom2ha_mapping_surface.js` (appel de relecture après action de la fenêtre de pièce, rien d'autre) ; `desktop/css/jeedom2ha.css` ; `docs/fr_FR/index.md`, `compteurs.md`, `changelog_beta.md` ; tests Node nouveaux `tests/unit/test_story_25_3_*.node.test.js` et adaptés ; un test PHP ; fixtures ; `tests/e2e/gate/parcours/*.mjs`, `tests/e2e/gate/page-load-request-inventory.mjs`.

### Definition of done

AC1 à AC19 tenus ; suites locales vertes ; PR relue par ClaudeBox ; preuve terrain (Task 8) ; statut `ready-for-UX-validation` (la validation UX finale est portée par 25.5).

### References

- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/epic-25-draft.md`#Stories proposées, 25.3 ; #Décisions de cadrage Q2]
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/CADRAGE.md`#B — page principale ; #Contraintes Jeedom]
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/diagnostic-ux.md`#P1, #P5, #P14, #5 point 9]
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/maquettes.html`, onglet B — données fictives]
- [Source: `_bmad-output/implementation-artifacts/25-1-socle-etat-unique-glossaire-palette-theme.md`#D1, #D4, #D5, #AC24, #AC25, #Q8]
- [Source: `_bmad-output/implementation-artifacts/25-2-route-agregee-cote-demon.md`#Contrat final, #AC5, #AC7, #AC8, #AC11, #Décisions]
- [Source: `_bmad-output/implementation-artifacts/25-2-preuve-terrain-2026-10-19.md`#Comparaison aux budgets, #Point d'attention pour 25.3]
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md`#Epic-25]
- [Source: `CLAUDE.md`, `docs/delegation-claude-cloud.md`, `_bmad-output/project-context.md`]

## UI Impact

- **UI Impact:** Oui — page principale du plugin (`desktop/php/`, `desktop/js/`, `desktop/css/`), docs utilisateur. Gate 20-0 obligatoire (AC17) ; statut cible `ready-for-UX-validation`, validation UX finale en 25.5.

## Dev Agent Record

### Agent Model Used

Session cloud déléguée Claude Code — `create-story` (documentaire, 2026-10-19).

### Debug Log References

### Completion Notes List

- Rédaction `create-story` : documentaire seulement ; aucun fichier de code, de test ou de doc utilisateur modifié ; statut **`backlog` conservé** (`ready-for-dev` non accordé : relecture ClaudeBox obligatoire, Q1-Q11 à trancher). `sprint-status.yaml` : seul le commentaire de l'entrée `25-3-page-principale-b` est complété.
- Écarts et constats relevés dans les sources, à confirmer par ClaudeBox :
  1. `parent_number` (lu dans `getConfiguration('parentNumber')`) n'est pas l'identifiant du parent ; le dépôt lit déjà `father_id` (`core/class/jeedom2ha.class.php:758`). Le regroupement par parent demande donc d'étendre `j2haRoomsTree` (→ Q2).
  2. `jeedom2ha.php` omet les objets sans équipement propre : un parent qui ne porte que des sous-pièces n'a pas de carte, mais il faut son nom pour le sous-titre de groupe (→ Q2).
  3. La signature réelle est `resolveEquipmentState(tree, enabled)` ; `enabled` vient de `j2haRoomsTree`, la route n'en porte pas (25.2 Q2 A).
  4. La route ne documente `reason:"action_in_progress"` que dans le texte de 25.2 (AC11, Q7), pas dans l'exemple de son § Contrat final ; la page doit tolérer son absence (D2) — à confirmer contre `http_server.py` au dev-story.
  5. La taille de réponse mesurée en 25.2 (1,34 Mo, 89 % du budget) est inscrite comme AC de vigilance (AC7) et comme question (Q8), pas retranchée.
- Aucune mesure ni donnée terrain n'a été produite ni inventée (CC-48).

### File List

- Story : ce fichier.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (commentaire de l'entrée `25-3-page-principale-b`, statut inchangé).

## Décisions (ClaudeBox, 2026-10-19 03:25, par délégation d'Alexandre du 2026-10-18 23:50)

Relecture ClaudeBox : story approuvée, 19 AC cohérents avec 25.1 et 25.2. Les recommandations sont suivies, **sauf Q10, tranchée en B avec garde-fou**.

- **Q1 = A.** Liste sous le bloc maison. Les cartes sans équipement correspondant sont atténuées, pas masquées. Un clic sur une ligne ouvre la fenêtre de la pièce.
- **Q2 = A.** Extension additive de `j2haRoomsTree` avec `father_id`, plus une variable pour les ancêtres sans équipement propre. Groupe = parent direct, « Sans pièce » en dernier. Pas de repli de groupe en 25.3.
- **Q3 = A.** Classes d'icône filtrées par liste blanche et reconstruites côté PHP. Couleur acceptée seulement en hexadécimal validé ; elle teinte l'icône et un filet de la carte, jamais le texte ni une teinte d'état.
- **Q4 = A.** Segment gris « exclus et autres ». Les « non lus » ont un motif neutre, hors des six états.
- **Q5 = A.** Pas de repère agrégé des commandes bloquées dans des équipements publiés. La mention « N bloquées » reste sur les lignes et dans la fenêtre de pièce.
- **Q6 = A.** Au plus 3 relectures automatiques (2 s, 5 s, 10 s) sans `refresh`. Pas de relecture automatique sur erreur ajax.
- **Q7 = A.** Relecture à la fin de chaque action, coalescée sur 500 ms. Fenêtre de pièce comprise, relecture à chaque action et pas à la fermeture.
- **Q8 = A.** Rien ne change dans la route en 25.3. Seuil d'alerte à 1 350 000 octets relevé à la preuve terrain : au-dessus, ou si un budget de temps est dépassé, la story reste en `review` et une décision choisit un levier.
- **Q9 = A.** Ligne d'aide d'une phrase avec un lien « Aide ». Le diagnostic passe par `bootbox`, et la case « Pseudonymiser » reste inchangée.
- **Q10 = B, avec garde-fou.** Affichage de « Chiffres relus à HH:MM », heure de lecture par la page. **Relecture au retour sur l'onglet** (`visibilitychange` → visible), sans `refresh`, seulement si la dernière lecture date de **plus de 60 s**, et coalescée avec les autres déclencheurs de l'AC6.
  - *Motif :* l'iPad mural d'Alexandre garde la page ouverte longtemps. Sans cela, il afficherait des chiffres périmés jusqu'au prochain « Actualiser ».
  - *Coût :* une lecture servie par le cache démon (≈ 0,14 à 0,32 s mesuré).
  - Ce n'est pas un polling, pas de temps réel.
  - AC6 compte ce déclencheur en plus des quatre de l'epic, et un test Node le couvre : seuil de 60 s, coalescence, pas de `refresh`.
- **Q11 = A.** Toutes les pièces de `j2haRoomsTree` sont rendues, sans filtre implicite.

*Toutes ces décisions sont réversibles. Elles sont consignées au journal de nuit du plan ClaudeBox pour relecture par Alexandre.*

## Questions ouvertes pour ClaudeBox / Alexandre

Chaque question porte une **recommandation** ; **aucune n'est tranchée par la session**. Les AC écrits « par défaut » ci-dessus suivent la recommandation, pour qu'une réponse « je valide les recommandations » rende la story prête sans réécriture.

**Q1 — Effet d'un filtre global sur la grille, et action d'un clic sur une ligne de la liste.**
- A. Liste sous le bloc maison **et** cartes sans équipement correspondant atténuées (non masquées, pas de saut de mise en page) ; un clic sur une ligne ouvre la fenêtre de la pièce (équipement mis en évidence s'il existe déjà un mécanisme de ciblage sans nouvelle lecture ; sinon pièce seule). *(recommandé : le filtre reste lisible, aucun travail jeté quand 25.4 remplacera la modale)*
- B. Liste seule, la grille ne change pas : plus simple, mais le lien entre le filtre et les pièces concernées se perd.
- C. Grille filtrée (cartes sans correspondance masquées) et pas de liste : contredit « liste des équipements concernés » (diagnostic P1).

**Q2 — Source du parent et forme des groupes.**
- A. Étendre `j2haRoomsTree` de façon **additive** avec `father_id` (comme `core/class/jeedom2ha.class.php:758`) et ajouter une seconde variable JS pour les **ancêtres sans équipement propre** (`{object_id, name, father_id}`, nécessaires aux sous-titres). Groupe = parent direct ; titre « Parent › Enfant » si la profondeur dépasse 2 ; la carte du parent, s'il porte des équipements, ouvre son groupe ; objets sans parent ni enfant et « Sans pièce » : groupes sans sous-titre, « Sans pièce » en dernier ; pas de repli de groupe en 25.3. *(recommandé)*
- B. Réutiliser `parent_number` : déconseillé, c'est un niveau de profondeur et non un identifiant de parent (à vérifier sur la box, Task 0).
- C. Aplatir et trier : renonce au regroupement décidé en 25.1 Q8.

**Q3 — Icône et couleur Jeedom : injection sûre et usage de la couleur.**
- A. Côté PHP : extraire d'`getDisplay('icon')` uniquement les classes CSS d'une liste blanche (`fas|far|fab|icon|jeedom-*|…` + caractères `[A-Za-z0-9_ -]`), reconstruire `<i class="…">`, repli porte ; couleur : littéral hexadécimal `#RGB|#RRGGBB` validé, sinon ignorée ; la couleur teinte l'icône et un filet de la carte, jamais le texte ni une teinte d'état. *(recommandé : surface d'injection nulle, contraste maîtrisé sur les deux thèmes)* Forme réelle des valeurs à relever en Task 0.
- B. Injecter le HTML tel quel comme le core : fidèle, mais ouvre une injection par un nom d'icône ou une couleur d'objet.
- C. Ignorer la couleur, garder l'icône seule : plus sûr, perd une partie de ce que l'utilisateur a configuré (diagnostic P14).

**Q4 — Composition et libellé du segment gris, et représentation des « non lus ».**
- A. Segment gris = exclus + désactivés + rien à publier, libellé de puce **« exclus et autres »** (comme la maquette), chaque ligne de la liste gardant son propre mot d'état ; « non lus » = segment à motif neutre et mention grise, hors des six états. *(recommandé : reste dans le glossaire de 25.1, aucun 7ᵉ état)*
- B. Trois puces grises séparées (exclus, désactivés, rien à publier) : plus précis, légende trop longue sur tablette.
- C. Compter les non lus dans le gris : masque un défaut de lecture, contraire à la décision 3.

**Q5 — Équipements publiés avec des commandes bloquées : repère au niveau de la maison et des cartes ?** (le glossaire dit : « Publié » + mention orange « N bloquées », pas d'état partiel)
- A. Pas de repère agrégé en 25.3 : les segments et repères comptent des **équipements par état** ; la mention « N bloquées » n'apparaît que sur les lignes de la liste filtrée et dans la fenêtre de pièce. *(recommandé : une seule unité de compte, cohérente avec 25.1 Q4 qui a retiré les compteurs de commandes de l'en-tête de pièce)* Contrepartie : une maison à « 0 bloqué » peut contenir des commandes bloquées dans des équipements publiés.
- B. Ajouter un repère orange discret « N équipements publiés avec commandes bloquées » sur la carte et le bloc maison : plus complet, mais ajoute une seconde notion de « bloqué » à la vue d'ensemble.

**Q6 — Politique de relecture quand `action_in_progress` est vrai ou que la lecture est indisponible.**
- A. Jusqu'à **3 relectures automatiques** sans `refresh`, espacées de 2 s, 5 s puis 10 s, annulées si un autre événement de l'AC6 relit entre-temps ; ensuite le message reste et « Actualiser » reprend la main. Une indisponibilité (erreur ajax) n'est **pas** relue automatiquement. *(recommandé : suit la décision 25.2 Q7 A « 25.3 gérera la relecture » sans polling infini)*
- B. Aucune relecture automatique : l'utilisateur appuie sur « Actualiser » ; simple, mais l'affichage reste « en cours » après la fin de l'opération.
- C. Attendre la fin avec un délai long : peut bloquer l'affichage et dépasser le budget du relais (15 s).

**Q7 — Granularité du « après chaque action », notamment pour la fenêtre de pièce.**
- A. Relecture **à la fin de chaque action** (succès ou échec), coalescée sur 500 ms ; pour la fenêtre de pièce, la relecture part à la fin de chaque action et non à la fermeture, de sorte que la page derrière la modale soit juste dès que la modale se ferme. *(recommandé : suit l'invalidation côté démon, une action = un appel)*
- B. Une seule relecture à la fermeture de la modale : moins d'appels, mais la page peut rester périmée si la modale reste ouverte (iPad mural) ou si elle est fermée par erreur de navigation.

**Q8 — Taille de réponse (1,34 Mo, 89 % du budget) : seuil d'alerte et leviers.**
- A. **Ne rien changer en 25.3** (la route et ses budgets sont gelés) ; fixer un **seuil d'alerte** à 90 % du budget (1 350 000 octets) relevé dans la preuve terrain : au-dessus, ou au dépassement d'un budget de temps, la story reste en `review` et une décision choisit parmi les leviers de 25.2 — compression gzip au niveau du relais, allègement de `diagnostic` dans la liste blanche (parité AC4 de 25.2 à re-prouver), ou statu quo avec suivi du parc. *(recommandé : la mesure terrain décide, pas la supposition ; rien n'est retranché en silence)*
- B. Agir dès 25.3 sur le relais (gzip) : gain probable, mais touche `core/ajax/` (hors périmètre, AC16) et rouvre la route livrée.
- C. Alléger la liste blanche maintenant : demande de re-prouver la parité d'état (25.2 AC4) et d'amender 25.2 `done`.

**Q9 — Ligne d'aide sous le titre et boîte de dialogue du diagnostic.**
- A. Ligne d'aide d'une phrase avec lien « Aide » vers la documentation du plugin (URL obtenue par l'API du core si elle existe, sinon lien relatif déjà employé par le plugin ; à vérifier au dev-story) ; boîte de dialogue du diagnostic via `bootbox` (déjà employé), case « Pseudonymiser » **inchangée** (décochée par défaut, comme aujourd'hui). *(recommandé : aucun composant nouveau, comportement d'export intact)*
- B. Pas de lien (texte seul) : évite une dépendance à l'URL de la doc.
- C. Pseudonymisation cochée par défaut : plus prudent, mais change un comportement existant (hors périmètre).

**Q10 — Fraîcheur affichée et relecture au retour d'onglet.**
- A. Afficher « Chiffres relus à HH:MM » (heure locale de la **lecture** par la page, pas `meta.generated_at`, qui date de la construction du cache) ; **aucune** relecture automatique au retour sur l'onglet (pas de temps réel, décision 4). *(recommandé)*
- B. Relire au retour d'onglet (`visibilitychange`) : plus frais sur l'iPad mural, mais c'est un déclencheur de plus que l'epic n'a pas retenu.

**Q11 — « Pièces » techniques (supervision, tests, géolocalisation) mêlées aux vraies pièces (diagnostic P14).**
- A. Hors périmètre de 25.3 : toutes les pièces de `j2haRoomsTree` sont rendues ; le regroupement par parent suffit à les isoler si l'utilisateur les a rangées sous un parent dédié. *(recommandé : aucun filtre implicite qui cacherait des équipements publiés)*
- B. Ajouter un réglage « masquer les objets… » : nouvelle donnée de configuration, hors décision d'epic.

## Change Log

- 2026-10-19 03:25 — Relecture ClaudeBox : décisions Q1-Q11 (Q10 B avec garde-fou 60 s, sinon recommandations) ; `ready-for-dev`.

- 2026-10-19 — Création (`create-story`, session cloud déléguée) : story rédigée, statut `backlog`, 19 AC, 12 décisions déjà arbitrées consignées, 11 questions ouvertes pour ClaudeBox / Alexandre avec recommandation ; `ready-for-dev` non accordé.
