# Story 25.1 : Socle A — état unique, glossaire, palette et thème

Status: backlog

> **Statut : `backlog` (2026-10-18).** Story rédigée par une session cloud déléguée (`create-story`, documentaire : aucun code, aucun accès box / VM / Home Assistant / secret, CC-48). **`ready-for-dev` n'est PAS accordé** : relecture ClaudeBox obligatoire, puis réponses d'Alexandre aux questions de la section « Questions ouvertes pour Alexandre » (en fin de fichier), avant tout passage à `ready-for-dev`. Pointeurs de code pris sur `main` à `d417f08`. Aucun nom réel d'équipement, de pièce, de scénario ou de personne : identifiants et données fictives seulement (CC-48).

## Story

En tant qu'utilisateur du plugin qui ouvre la fenêtre d'une pièce puis un équipement,
je veux que chaque équipement porte **un seul état**, dit avec les mêmes mots et la même couleur dans le badge, les compteurs et le tableau, dans les thèmes clair et sombre de Jeedom, avec un réglage de publication lisible (Automatique / Toujours / Jamais),
afin de savoir d'un coup d'œil ce qui est dans Home Assistant, ce qui attend d'être appliqué et ce qui demande une action de ma part, sans avoir à rapprocher trois chiffres contradictoires.

**Parcours : interface seule** (`desktop/js/`, `desktop/php/`, `desktop/css/`, docs `docs/fr_FR/`, tests Node/PHP, parcours du gate 20-0). **Aucune modification du démon** (voir AC22). Gate 20-0 et `ready-for-UX-validation` avant `done` ; la validation UX d'Alexandre est transférée à 25.5 (Q1 du cadrage).

**Clôture de 22-2.** 22-2 (`ready-for-UX-validation`, validation UX refusée le 18/10 17:58) passe à `done` (superseded) **à la preuve terrain de 25.1** (Q1 du cadrage). Cette story-ci ne modifie pas le statut de 22-2 ; la bascule se fait au moment de la preuve terrain, par ClaudeBox.

## Contexte et périmètre

**Sources de vérité** (toutes sous `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/`) : `CADRAGE.md` (glossaire imposé, contraintes Jeedom), `epic-25-draft.md` (périmètre de 25.1), `diagnostic-ux.md` (§ 1 constats P1-P15, § 3 glossaire, § 4-5 contraintes Jeedom vérifiées, § 6 décision), `maquettes.html` (onglet A, données fictives).

**Dans le périmètre (structure grille + modale inchangée) :**
- une fonction d'état pure qui remplace `publicationSummaryState` ;
- le glossaire sur tout l'écran (page principale incluse pour les libellés, pas pour la structure) et dans `index.md` / `compteurs.md` ;
- la palette sémantique à 4 teintes sur les variables du thème Jeedom + `--j2ha-*`, clair et sombre ;
- la réorganisation de la fenêtre de pièce : contrôle segmenté, « Appliquer » conditionnel, menu « ⋯ », tableau regroupé par entité, cause dite une fois, commandes ignorées repliées, un seul équipement déplié, en-tête collant, fin du défilement imbriqué.

**Hors périmètre (ne pas faire ici) :**
- page principale B (barre de santé, jauge maison, cartes avec jauge, bandeau bleu supprimé) → 25.3 ; route agrégée → 25.2 ; vue maître-détail et retrait de la modale → 25.4 ; recette UX finale → 25.5 ;
- tout changement du démon, du contrat de décision (`evaluate_equipment()`, `CommandDecision`), des artefacts figés (`models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`) et des tables de mapping ;
- toute nouvelle requête au chargement (pas de route agrégée ici, pas de lecture supplémentaire).

**Faits relevés dans le code (`main` `d417f08`)** — pointeurs pour le `dev-story`, à re-vérifier au SHA courant :
- `desktop/js/jeedom2ha_mapping_override.js` : `buildPublicationSummaryLabel` (`:886`), `publicationSummaryState` (`:911`, retourne `excluded|disabled|empty|publish|partial|blocked`), `summarizePublication` (`:832`), `classifyCommandRow` (`:825`, déjà `uncovered` pour `command_not_covered`), `summarizeEquipmentCounters` (`:979`, mêle présence réelle et état de plan), `summarizeRoom` (`:1025`), `buildRoomCounterLabels` (`:1061`), `buildEquipmentCounterLabels` (`:1089`), `REASON_LABELS` (`:612+`, contient « Override HA »).
- `desktop/js/jeedom2ha_mapping_surface.js` : `renderSummary` (`:792+`, classes `j2ha-publish-*`), boutons Exclure/Forcer/Revenir (`:875-884`), Appliquer/Republier (`:987-993`), Republier/Supprimer la pièce (`:743`, `:764`), `max-height:calc(100vh - 320px)` en ligne (`:1122`), largeur de modale en ligne (`:1157`), accordéon `aria-multiselectable` (`:1087`).
- `desktop/js/jeedom2ha.js` : « Bridge » (`:70-71` côté PHP, `:155`), « Un sync complet … applique les overrides persistés » (`:168`).
- `desktop/php/jeedom2ha.php` : 35 attributs `style=` en ligne ; libellé « Bridge » (`:70`).
- `desktop/css/jeedom2ha.css` (147 lignes) : couleurs en dur (`#dff0d8`, `#fcf8e3`, `#f2dede`, `#eee`, `#fff9c4`, `#3c763d`, `#8a6d3b`, `#555`, `#337ab7`, `#5b9bd5`, `#f0ad4e`, …).
- `docs/fr_FR/index.md` (« Override », « Bridge », « prêt / bloquant », « Override en attente », « Override HA », « Rescanner la topologie Jeedom ») ; `docs/fr_FR/compteurs.md` (bloc isolé `COMPTEURS:DEBUT/FIN`, à réécrire seul).
- Tests Node existants à faire évoluer : `tests/unit/test_story_16_8_mapping_surface.node.test.js`, `test_story_16_8_cc38_excluded.node.test.js`, `test_story_20_2_ac8_exclu_sans_commande.node.test.js`, `test_story_20_3_*.node.test.js`, `test_story_22_2_compteurs_portees.node.test.js`, `test_story_22_2_documentation.node.test.js`, `test_story_19_3_ac4_ac6_reason_labels_sync_badge.node.test.js`, helpers `tests/unit/helpers/fake_dom.js` et `ui_harness.js`. Parcours du gate 20-0 : `tests/e2e/gate/parcours/*.mjs` (5 fichiers).

## Définitions normatives

Ces définitions font foi pour les AC. Toute ambiguïté résiduelle est listée dans « Questions ouvertes pour Alexandre ».

### D1 — Fonction d'état d'équipement

`resolveEquipmentState(tree)` — **pure** (aucun DOM, aucune E/S, aucun état global, ne mute pas son entrée), déterministe, exportée par `jeedom2ha_mapping_override.js` à côté de `summarizePublication`. Elle prend l'arbre déjà lu (`GET /system/mapping_overrides/{eq_id}`) et ne recalcule **aucune décision** : elle lit `sync_status.published_in_ha` (présence réelle, `true|false|null`), `sync_status.override_pending` / `entities[].override_pending` (divergence plan ↔ réalité, déjà calculée par le démon), `sync_status.synced_should_publish` (`null` = jamais synchronisé : l'`override_pending` du démon n'est alors pas un réglage posé, comme en 22-2), le résumé des commandes de `summarizePublication`, et `equipment_decision`.

Elle retourne `{ state, blocked_mention }` où `state ∈ { 'published', 'to_apply', 'blocked', 'excluded', 'disabled', 'nothing_to_publish' }` (affichés Publié / À appliquer / Bloqué / Exclu / Désactivé / Rien à publier) et `blocked_mention` = nombre de commandes bloquées (entier ≥ 0) affiché en mention orange « N bloquée(s) » quand `state ∈ { published, to_apply }`. **Il n'existe pas d'état « partiel ».**

Règles, **évaluées dans cet ordre, la première qui s'applique l'emporte** (P = `published_in_ha`, r = commandes prêtes au sens du plan, b = commandes bloquées au sens de D2) :

| # | Condition | `state` |
|---|---|---|
| R1 | réglage en attente (`override_pending`, hors cas « jamais synchronisé ») | `to_apply` |
| R2 | P = `true` | `published` |
| R3 | équipement désactivé dans Jeedom | `disabled` |
| R4 | équipement exclu (décision d'équipement ou toutes les commandes exclues) | `excluded` |
| R5 | P = `false` **et** r > 0 (la publication est due mais n'a pas eu lieu) | `to_apply` |
| R6 | P = `null` **et** r > 0 (démon plus ancien, présence inconnue) | `to_apply` (jamais `published`, comme en 22-2) |
| R7 | b > 0 | `blocked` |
| R8 | sinon (aucune commande publiable, rien de bloqué : commandes toutes ignorées, ou sans commande) | `nothing_to_publish` |

« Désactivé » l'emporte sur « Exclu » quand les deux s'appliquent (R3 avant R4). Les règles R1/R5/R6 sont à confirmer (Q1, Q2).

### D2 — Catégories de commande

| Catégorie (affichage) | Définition | Compte comme défaut ? |
|---|---|---|
| **Publiée** (vert) | `commands[].published_in_ha === true` | non |
| **Bloquée** (orange) | absente de HA, diagnostic **corrigeable par l'utilisateur** (codes de cause : voir D3) | **oui** |
| **Ignorée** (gris, repliée) | absente de HA, **aucun équivalent HA**, rien à faire (D3) | **non** |
| **Exclue** (gris) | exclue par l'utilisateur | non |

### D3 — Partition des codes de cause (proposition à confirmer, Q3)

Source : `REASON_LABELS` (`jeedom2ha_mapping_override.js:612+`), lue sans modifier `models/cause_mapping.py`.
- **Ignorée** : `command_not_covered`, `no_supported_generic_type`.
- **Bloquée** : `ambiguous_skipped`, `name_heuristic_rejection`, `duplicate_generic_types`, `conflicting_generic_types`, `switch_state_orphan`, `probable_skipped`, `low_confidence`, `no_generic_type_configured`, `no_mapping`, `skipped_no_mapping_candidate`, `ha_missing_command_topic`, `ha_missing_state_topic`, `discovery_publish_failed`, `ha_component_not_in_product_scope`, `no_projection_possible`.
- Codes d'état (ni bloquée ni ignorée) : `disabled_eqlogic`, `excluded_eqlogic`, `excluded_plugin`, `publication_excluded_eqlogic`, `publication_excluded_command`, `publication_forced`, `sure_mapping`.
- Tout code inconnu (démon plus récent) : catégorie **Bloquée** (jamais masqué), avec le code brut en infobulle.

### D4 — Glossaire (un mot = une notion)

| Notion | Terme affiché | Remplace (interdit après la story) |
|---|---|---|
| État d'équipement | Publié / À appliquer / Bloqué / Exclu / Désactivé / Rien à publier | « Sera publié… », « prête(s) », « Partiellement publié », « Ne sera pas publié », « Aucune commande projetable », « non pris en charge », « Override en attente », « pas encore appliqué / republié » |
| État de commande | Publiée / Bloquée / Ignorée / Exclue | « bloquante(s) », « non couverte », « commande sans type Home Assistant applicable » (comme étiquette d'état) |
| Réglage de publication | Automatique / Toujours / Jamais | « Revenir au mode automatique », « Forcer », « Exclure » |
| Réglage de type | « Type HA : auto (Lumière)» / « Type HA : sensor (imposé) » | « Override HA », « — mode automatique — » |
| Actions | Appliquer · Republier · Supprimer de Home Assistant… · Relire Jeedom | « Rescanner la topologie Jeedom », « Rescanner », « Supprimer la pièce de Home Assistant » |
| Démon | Démon | « Bridge » |
| Domaine HA | nom traduit + terme technique en petit (« Lumière *light* ») | terme technique brut seul dans une phrase |

Règles de forme : pluriels accordés par le code (pas de « commande(s) »), pas de point final dans les étiquettes (badges, boutons, en-têtes), « Désactivé » en italique, texte toujours présent (la couleur ne remplace jamais le mot). **Exceptions autorisées** : identifiants de code (`override_pending`, `mapping_overrides`, `getBridgeStatus`, classes CSS, champs JSON du démon, noms de fichiers de tests), historique des versions (`changelog*.md`), le mot « Homebridge » (le message « Aucun impact Homebridge … » est conservé) et les noms de types HA dans les listes techniques (`switch`, `sensor`…).

### D5 — Palette (4 teintes sémantiques)

vert = Publié / Publiée · bleu = À appliquer · orange = Bloqué / Bloquée / mention « N bloquée(s) » · gris = Exclu / Désactivé / Rien à publier / Ignorée / Exclue. Le rouge est réservé aux boutons destructifs **dans leur confirmation et dans le menu « ⋯ »**.

## Acceptance Criteria

Convention : chaque AC est vérifiable par un test nommé (Node, PHP ou parcours du gate 20-0) ou par une recherche de texte dont la commande figure dans l'AC. « Vert/bleu/orange/gris » désignent les rôles de D5, jamais une valeur de couleur littérale.

### A. État unique

**AC1 — Une seule fonction d'état remplace `publicationSummaryState`**
**Given** le code de `desktop/js/`
**When** on cherche `publicationSummaryState` et `buildPublicationSummaryLabel`
**Then** ces deux symboles n'existent plus (ni définition, ni appel, ni export) : `grep -rn "publicationSummaryState\|buildPublicationSummaryLabel" desktop/` ne renvoie rien
**And** `resolveEquipmentState(tree)` (D1) est exportée et appelée **par les trois affichages** : le badge d'équipement, les compteurs de la pièce et de l'équipement, et le tableau/l'en-tête d'équipement
**And** `summarizeEquipmentCounters` et `summarizeRoom` obtiennent l'état d'un équipement **uniquement** via `resolveEquipmentState` (aucun test `ready_count`/`blocking_count` ne subsiste dans les compteurs pour décider d'un état).

**AC2 — Table de vérité testée, pureté vérifiée**
**Given** un test Node `test_story_25_1_etat_unique.node.test.js`
**When** il exécute les règles R1 à R8 de D1
**Then** chaque règle est couverte par au moins un cas, **plus** les croisements suivants, avec l'état attendu écrit en dur dans le test : désactivé+exclu → `disabled` ; désactivé+exclu+P `false` → `disabled` ; P `true`+b>0 → `published` avec `blocked_mention`=b ; P `true`+réglage en attente → `to_apply` ; P `false`+r>0 sans attente → `to_apply` ; P `null`+r>0 → `to_apply` et jamais `published` ; jamais synchronisé (`synced_should_publish` `null`) avec `override_pending` `true` du démon → pas de `to_apply` par R1 ; seul un capteur secondaire publié (principal refusé, P `true`) → `published` ; équipement sans commande exclu → `excluded` ; sans commande désactivé → `disabled` ; commandes toutes ignorées → `nothing_to_publish`
**And** la fonction ne mute pas l'arbre passé (test par `Object.freeze` profond) et, appelée deux fois sur la même entrée, rend des résultats `deepEqual`
**And** aucun état hors de `{published, to_apply, blocked, excluded, disabled, nothing_to_publish}` n'est jamais retourné (test sur un jeu d'entrées généré couvrant le produit cartésien des booléens et de P ∈ {true,false,null}).

**AC3 — Badge, compteurs et tableau cohérents sur un même équipement**
**Given** un équipement fictif de chacun des 6 états de D1 (jeu de fixtures partagé)
**When** la fenêtre de pièce est rendue (harnais `ui_harness.js`)
**Then** pour chaque équipement, le mot du badge, la classe d'état de la ligne, la catégorie dans laquelle il est compté dans la ligne de compteurs de la pièce, et le mot de l'en-tête d'équipement déplié sont **identiques** (un test unique compare les quatre et échoue si l'un diverge)
**And** la somme des compteurs d'équipement par état de la pièce égale le nombre d'équipements lus, sans reste ni double compte (test d'invariant sur au moins 3 pièces fictives).

**AC4 — « Désactivé » prime sur « Exclu » (visible)**
**Given** un équipement fictif à la fois désactivé dans Jeedom et exclu (cas P2 de la capture 02)
**When** la pièce est rendue
**Then** le badge affiche « Désactivé » (italique), la ligne n'affiche **pas** « Exclu », le compteur « désactivé » de la pièce vaut 1 et le compteur « exclu » vaut 0 pour cet équipement.

**AC5 — Commandes ignorées séparées des bloquées et hors défauts**
**Given** D2 et D3
**When** un équipement fictif porte 3 commandes publiées, 1 bloquée (`no_generic_type_configured`) et 5 ignorées (`command_not_covered`)
**Then** sa ligne de compteurs de commandes affiche « 3 publiées · 1 bloquée · 5 ignorées » (zéros masqués, pluriels accordés) et le **compteur de défauts** de l'équipement vaut 1 (les ignorées n'y comptent pas)
**And** pour un équipement dont toutes les commandes sont ignorées, l'état est « Rien à publier » et le compteur de défauts de la pièce n'augmente pas
**And** un test table-driven parcourt **chaque code de `REASON_LABELS`** et exige qu'il appartienne à exactement une catégorie de D3 (échoue si un code est ajouté sans catégorie) ; un code inconnu est classé Bloquée.

**AC6 — Compteurs de la pièce par état d'équipement, zéros masqués**
**Given** une pièce fictive de 14 équipements
**When** l'en-tête de la pièce est rendu
**Then** il affiche, dans l'ordre Publié, À appliquer, Bloqué, Exclu, Désactivé, Rien à publier, un chiffre et un mot court par état **non nul** (aucun « 0 … » affiché), sans compteur de commandes au niveau de la pièce (Q4)
**And** le message « N équipement(s) non lu(s) » et le message de présence inconnue (démon plus ancien) de 22-2 sont conservés, reformulés selon le glossaire.

### B. Glossaire

**AC7 — Plus aucun terme interdit dans les libellés d'interface**
**Given** les fichiers `desktop/js/*.js`, `desktop/php/*.php`, `desktop/css/*.css`
**When** on exécute le test Node `test_story_25_1_glossaire.node.test.js`, qui extrait toutes les chaînes `{{…}}` et `__()` ainsi que les libellés construits en JS
**Then** aucune ne contient, en insensible à la casse et en mot entier, `override`, `bridge`, `prête`, `prêtes`, `prêt`, `prêts`, `bloquante`, `bloquantes`, `rescanner`, `commande(s)`, `(s)` en suffixe de pluriel ; `Homebridge` n'est pas concerné (mot entier)
**And** la même recherche sur les chaînes **construites** (concaténations, tableaux de libellés, `REASON_LABELS`) passe, y compris le texte d'infobulle et de `title`
**And** la liste des exceptions du test est exactement celle de D4 (identifiants de code, `changelog*.md`, « Homebridge »), codée en dur et commentée.

**AC8 — Libellés exacts du glossaire**
**Given** D4
**When** le test de glossaire inspecte le rendu
**Then** les libellés suivants sont présents tels quels : Publié, À appliquer, Bloqué, Exclu, Désactivé, Rien à publier ; Publiée, Bloquée, Ignorée, Exclue ; Automatique, Toujours, Jamais ; Appliquer, Republier, « Supprimer de Home Assistant… », « Relire Jeedom » ; l'indicateur de santé s'intitule « Démon »
**And** aucune étiquette de badge, bouton ou en-tête ne se termine par un point (test sur le texte rendu)
**And** le domaine HA est rendu traduit avec le terme technique en petit (« Lumière » + `light`) pour au moins `light`, `switch`, `sensor`, `binary_sensor`, `cover`, `climate`, `button`, `alarm_control_panel` (table de traduction testée).

**AC9 — Toutes les causes passent par le glossaire, sans « Override HA »**
**Given** `REASON_LABELS`
**When** une cause citait « Override HA » ou « Forcer » (ex. `switch_state_orphan`)
**Then** elle est reformulée avec « Type HA » et « Toujours » (le sens reste identique)
**And** les tests existants qui citent les anciens textes (`test_story_19_3_ac4_ac6_reason_labels_sync_badge`, `test_story_16_8_*`, `test_story_20_*`, `test_story_22_2_*`) sont mis à jour **sans affaiblir** une assertion (même nombre d'assertions ou plus ; chaque ancien texte cité est remplacé, pas supprimé).

### C. Réorganisation de la fenêtre de pièce

**AC10 — Réglage de publication à 3 états**
**Given** un équipement et chacune de ses entités
**When** la fenêtre est rendue
**Then** le réglage « Publication dans Home Assistant » est un **contrôle segmenté** `Automatique | Toujours | Jamais` (rôle `radiogroup`, trois `radio`), qui montre la position courante (jamais déduite de boutons grisés)
**And** le segment actif d'un équipement exclu est « Jamais », d'un équipement forcé « Toujours », sinon « Automatique » ; la sélection d'un segment appelle **les mêmes routes d'écriture qu'avant** (exclure / forcer / revenir), sans nouvelle route ni nouveau champ
**And** les trois boutons « Exclure », « Forcer », « Revenir au mode automatique » (équipement et entité) n'existent plus : `grep -rn "Revenir au mode automatique\|Forcer l\|Exclure l\|Exclure cette\|Forcer cette" desktop/` ne renvoie rien
**And** les segments désactivés portent leur cause en infobulle **visible dans les deux thèmes** (texte lisible, AC17) ; navigation clavier flèches/Tab/Espace fonctionnelle (test sur le harnais).

**AC11 — « Appliquer » seulement quand un réglage attend**
**Given** un équipement dont l'état D1 n'est pas `to_apply`
**When** la fenêtre est rendue
**Then** le bouton « Appliquer » n'est **ni visible ni dans l'ordre de tabulation** (absent du DOM ou `hidden` + `aria-hidden`)
**And** quand l'état est `to_apply`, « Appliquer » est visible, activé, et un clic appelle la route d'application existante (`executeHaAction publier/equipement`), puis recharge l'équipement
**And** un test vérifie les trois transitions : `published` → `to_apply` (après changement de segment) → bouton visible ; clic réussi → `published`, bouton absent ; clic en échec → bouton visible avec le message d'erreur existant.

**AC12 — Menu d'actions secondaires « ⋯ »**
**Given** l'en-tête d'équipement et l'en-tête de pièce
**When** ils sont rendus
**Then** « Republier » et « Supprimer de Home Assistant… » ne sont plus des boutons de premier niveau : ils sont dans un menu « ⋯ » (bouton `aria-haspopup="menu"`, `aria-expanded`, fermeture Échap et clic extérieur), « Supprimer de Home Assistant… » en dernier, séparé par un trait, en rouge **dans le menu seulement**
**And** pour la pièce, « Republier la pièce » et « Supprimer la pièce de Home Assistant » deviennent « Republier » et « Supprimer de Home Assistant… » dans le menu de l'en-tête de pièce (la portée est donnée par l'endroit)
**And** les entrées grisées gardent leur cause en infobulle et leurs conditions de grisé actuelles (gating `updateRoomActionsGating`) ; les confirmations existantes de suppression (texte d'impact sur l'historique, dashboards, automatisations ; « rien n'est recréé ») sont **conservées mot pour mot au glossaire près**
**And** aucun bouton rouge plein n'est visible avant la confirmation (le rouge n'apparaît que dans le menu ouvert et dans la boîte de confirmation).

**AC13 — Tableau des commandes regroupé par entité**
**Given** un équipement à plusieurs entités (fixture fictive : une entité `switch` de 3 commandes et une entité `sensor` de 4 commandes, plus 5 commandes ignorées)
**When** il est déplié
**Then** le tableau a les colonnes, dans cet ordre, `Commande | Dans Home Assistant | Type Jeedom | Type HA`, en-têtes en casse normale (pas de majuscules forcées)
**And** chaque entité forme un **groupe** : une ligne d'en-tête de groupe (domaine traduit + terme technique en petit, effectif, contrôle segmenté compact de l'AC10) suivie de ses commandes ; la liste séparée « switch — Commandes : Etat, On, Off » disparaît ; avec **une seule entité**, l'en-tête de groupe n'est pas rendu
**And** « Dans Home Assistant » affiche, selon D2 : « Publiée → Lumière (light) », « Bloquée → cause courte », ou « — » pour une ignorée ; aucune ligne ne répète « Sera publié » ou « dans Home Assistant » dans sa cellule d'état
**And** « Type HA » affiche « auto » ou « imposé (sensor) » sous forme de lien discret ouvrant le sélecteur, surligné quand un type est imposé ; le sélecteur n'est **pas** rendu en permanence sur chaque ligne et n'est jamais proposé pour une commande ignorée
**And** « Type Jeedom » est rendu en texte normal (pas de monospace majuscule), couleur lisible (AC17).

**AC14 — La cause est dite une fois, avec un lien**
**Given** un équipement dont 11 commandes sont bloquées pour la même cause (`no_generic_type_configured`)
**When** il est déplié
**Then** un **encart unique** en tête de l'équipement énonce « 11 commandes bloquées : types génériques non configurés dans Jeedom » et contient le bouton **« Ouvrir les types génériques »**
**And** les 11 lignes n'affichent plus la phrase de cause (seulement une icône ⚠ et le mot « Bloquée ») : le texte « types génériques non configurés dans Jeedom » apparaît **exactement 1 fois** dans le DOM de l'équipement (assertion sur le nombre d'occurrences)
**And** si des commandes bloquées ont des causes différentes, un encart par cause distincte, jamais un encart par commande ; chaque encart nomme le nombre de commandes concernées
**And** le lien « Voir la première commande bloquante » est supprimé quand toutes les commandes de l'équipement sont bloquées, conservé sinon
**And** la cible du bouton « Ouvrir les types génériques » est vérifiée sur les versions cibles (Q5) ; elle ne modifie jamais un type générique (D10 : les types Jeedom natifs ne sont jamais écrits).

**AC15 — Commandes ignorées repliées**
**Given** un équipement avec 5 commandes ignorées
**When** il est déplié
**Then** les ignorées ne sont **pas** des lignes du tableau mais une ligne repliée « 5 commandes ignorées, sans équivalent dans Home Assistant : Pinguer nœud, Soigner nœud… ▸ » (liste tronquée au-delà de 3 noms avec « … »), dépliable au clic et au clavier (`aria-expanded`)
**And** les ignorées n'apparaissent dans aucun compteur de défauts (AC5).

**AC16 — Un seul équipement déplié, en-tête collant, plus de défilement imbriqué**
**Given** une pièce de 20 équipements
**When** l'utilisateur déplie l'équipement B alors que l'équipement A est déplié
**Then** A se replie (un seul équipement déplié à la fois ; `aria-multiselectable` retiré de l'accordéon d'équipements)
**And** l'en-tête de l'équipement déplié est `position: sticky` en haut de la zone qui défile (la modale) et reste visible quand on fait défiler le tableau
**And** le `max-height: calc(100vh - 320px)` en ligne et son `overflow-y:auto` sur `.j2ha-eq-cmdlist` sont supprimés : `grep -n "max-height" desktop/js/*.js desktop/php/*.php` ne renvoie rien de lié à cette liste ; il n'existe qu'**une** barre de défilement verticale dans la fenêtre (assertion sur le style calculé du harnais navigateur du gate ou, à défaut, sur l'absence de `overflow` sur les descendants)
**And** le corps de l'équipement déplié est visuellement distinct (retrait, fond un cran plus clair via variable, filet vert à gauche) sans couleur en dur.

### D. Palette et thème

**AC17 — Aucune couleur en dur ; clair ET sombre**
**Given** `desktop/css/jeedom2ha.css`, `desktop/js/*.js`, `desktop/php/*.php`
**When** le test Node `test_story_25_1_palette_theme.node.test.js` analyse ces fichiers
**Then** il n'existe **aucun** littéral de couleur (`#rgb`, `#rrggbb`, `#rrggbbaa`, `rgb(`, `rgba(`, `hsl(`, nom de couleur CSS autre que `transparent`/`inherit`/`currentColor`) hors des **blocs de définition** des variables `--j2ha-*`, qui sont de la forme `body[data-theme*="Dark"] { --j2ha-… }` et `body[data-theme*="Light"] { --j2ha-… }` (et leur repli `@supports not (color: color-mix(…))`)
**And** il n'existe aucun attribut `style="…"` ou `.css({…})` portant une couleur, un fond ou une bordure colorée dans le PHP et le JS (les 35 `style=` du PHP sont déplacés dans le CSS du plugin ou ne portent que des dimensions)
**And** chaque règle d'état utilise `var(--j2ha-…)` ou une variable du core (`--al-success-color`, `--al-warning-color`, `--al-danger-color`, `--al-info-color`, `--txt-color`, `--bg-modal-color`, `--link-color`, `--logo-primary-color`), et **toute variable du core est suivie d'une valeur de repli `--j2ha-*`** (`var(--al-warning-color, var(--j2ha-warn))`) pour tolérer l'absence de la variable sur Jeedom 4.4 (AC25).

**AC18 — Quatre teintes sémantiques, fonds translucides, repli**
**Given** D5
**When** on lit les définitions `--j2ha-*`
**Then** il existe exactement les 4 teintes `--j2ha-ok` (vert), `--j2ha-todo` (bleu), `--j2ha-warn` (orange), `--j2ha-neutral` (gris), chacune définie **pour les deux thèmes**, plus les teintes de texte/fond dérivées nécessaires ; le rouge n'est défini que pour la zone destructive
**And** les fonds d'état sont translucides par `color-mix(in srgb, var(--j2ha-…) 14%, transparent)` avec un repli `rgba()` sous `@supports not (…)` (aucun fond opaque pastel)
**And** « Bloqué » est l'état le plus visible de la ligne (contraste texte et bordure supérieurs à ceux de « Publié ») ; « Publié » est discret (point ou pastille courte, texte normal).

**AC19 — Contrastes mesurés dans les deux thèmes**
**Given** les valeurs `--j2ha-*` de chaque thème et les fonds de référence (sombre : `--bg-color` `25,25,25` relevé sur Jeedom 4.6.1 ; clair : valeur relevée à la Task 0, consignée dans le test)
**When** `test_story_25_1_palette_theme.node.test.js` calcule le rapport de contraste WCAG
**Then** tout texte d'état/compteur/en-tête de tableau sur son fond a un rapport **≥ 4,5:1** et toute bordure/icône porteuse de sens ≥ **3:1**, dans le thème clair **et** dans le thème sombre (les couleurs `#555`, `#666`, `#888`, `#999` sur fond sombre, signalées < 3:1 par le diagnostic, n'existent plus)
**And** la surbrillance de la ligne ciblée (`#fff9c4` aujourd'hui) devient une variable translucide lisible en sombre.

**AC20 — Ne jamais restyler le core ; arrondi du thème**
**Given** le CSS du plugin
**When** il est analysé
**Then** tous les sélecteurs sont préfixés `.j2ha-` ou limités sous `.modal-j2ha-room` / `#j2ha_roomCards` ; aucune règle ne cible seule `.label`, `.btn`, `.panel`, `.modal`, `.objectDisplayCard`
**And** les rayons de bordure utilisent `var(--border-radius, 0)` (le thème sombre est à angles droits)
**And** la largeur de la fenêtre se règle par une classe CSS sur `.modal-j2ha-room .modal-dialog` ; l'appel `.css('width', '90%')` en ligne (`jeedom2ha_mapping_surface.js:1157`) est supprimé
**And** aucune police ni bibliothèque externe n'est ajoutée ; chiffres en `font-variant-numeric: tabular-nums` ; icônes Font Awesome 5 local / `jeedom-*` uniquement.

**AC21 — Thème : bascule et état initial**
**Given** `<body data-theme="core2019_Dark|core2019_Light">`
**When** le thème change (changement manuel ou bascule automatique jour/nuit du core) pendant que la fenêtre est ouverte
**Then** les couleurs suivent sans rechargement (aucune couleur calculée en JS et figée ; uniquement des variables CSS)
**And** si l'attribut `data-theme` est absent ou d'une valeur inconnue, le jeu **clair** s'applique (test sur le CSS : un jeu de repli sans sélecteur de thème existe) (Q6).

### E. Documentation et libellés

**AC22 — Aucun changement côté démon, d'inventaire MQTT ni de registre HA**
**Given** la branche de la story
**When** on exécute `git diff --stat main...HEAD -- resources/daemon/ scripts/deploy-to-box.sh scripts/parity-snapshot.sh scripts/deploy-inventory-diff.sh`
**Then** la sortie est **vide** ; en particulier `models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`, les tables de mapping et les fichiers *golden* sont inchangés
**And** `pytest resources/daemon/tests/unit/test_story_8_4_golden_file.py resources/daemon/tests/unit/test_story_19_0_parity_golden_corpus.py` passe sans modification de ces fichiers
**And** le payload de découverte HA, les topics, les `unique_id` et le contenu publié sont inchangés (la story ne touche que la présentation) ; aucune écriture n'est envoyée au démon qui ne l'était pas avant (même ensemble de routes et de corps de requête, vérifié par l'inventaire de requêtes du gate, AC24).

**AC23 — `index.md` et `compteurs.md` réalignés**
**Given** `docs/fr_FR/index.md` et `docs/fr_FR/compteurs.md`
**When** le test Node `test_story_25_1_documentation.node.test.js` (successeur de `test_story_22_2_documentation`) les analyse
**Then** aucune occurrence insensible à la casse et en mot entier de `override`, `bridge`, `prête(s)`, `prêt`, `bloquante(s)`, `Rescanner`, `Override HA`, `mode automatique` (au sens de l'ancien réglage), hors le titre/lien d'historique des versions et le mot « Homebridge »
**And** chaque libellé de l'AC8 cité dans la doc existe verbatim dans le code (test de traçabilité « libellé cité → présent dans `desktop/`/`core/`)
**And** `compteurs.md` décrit : les 6 états d'équipement et leurs priorités (R1-R8, dont « Désactivé » prime sur « Exclu »), les 4 catégories de commande, « Ignorée » non comptée comme défaut, la ligne de compteurs par état au niveau de la pièce (zéros masqués), la ligne de commandes d'un équipement (publiées · bloquées · ignorées), et **supprime** la section « Vérifier un chiffre » qui expliquait comment rapprocher des chiffres contradictoires (remplacée par « Comment lire un état ») ; la règle de cloisonnement du bloc `COMPTEURS:DEBUT/FIN` est respectée (aucun libellé de compteur ailleurs que dans ce fichier)
**And** `index.md` : « Override » du glossaire devient « Réglage » (ou entrée supprimée) ; les sections « Les badges de synthèse », « Les causes affichées dans la colonne Diagnostic », « Réglages en attente et Appliquer », « Les actions de publication » et « Quand un bouton est grisé » décrivent le contrôle segmenté, le menu « ⋯ » et l'encart de cause ; les emplacements `<!-- CAPTURE-A-PRENDRE -->` sont conservés (pas de captures, décision 20-5 Q3) ; une entrée est ajoutée à `docs/fr_FR/changelog_beta.md` ; aucun nom réel.

**AC24 — Gate 20-0 vert, parcours adaptés sans affaiblissement**
**Given** les 5 parcours `tests/e2e/gate/parcours/*.mjs`, `run-gate.mjs` et `page-load-request-inventory.mjs`
**When** les libellés changent
**Then** chaque assertion de libellé est mise à jour vers le nouveau glossaire **sans retirer** d'assertion ni relâcher une politique (`test_story_20_0_gate_policy`) ; les suites `test_story_20_0_gate_*.node.test.js` et `test_story_20_3_gate_parcours.node.test.js` passent en mode simulé
**And** l'inventaire des requêtes au chargement (`page-load-request-inventory.mjs`) n'augmente pas : **aucune lecture supplémentaire** à l'ouverture de la page ni d'une pièce (pas de requête par équipement ajoutée)
**And** le gate 20-0 contre la box réelle est **lancé par ClaudeBox** (pas par cette session, CC-48) et son résultat vert est consigné dans la preuve terrain ; la story ne passe pas à `done` sans lui.

**AC25 — Compatibilité Jeedom 4.4 préservée**
**Given** `plugin_info/info.json` (`"require": "4.4"`)
**When** la story est livrée
**Then** le code n'utilise que jQuery 3.6, Bootstrap 3, bootbox, jeeDialog (`jeeDialog` n'est employé que si déjà employé aujourd'hui), jeedomUtils et Font Awesome 5 local, comme avant ; aucune API ni variable CSS propre à 4.6 n'est requise : chaque variable du core a un repli `--j2ha-*` (AC17) et un test CSS le vérifie
**And** la preuve consigne, **sur une VM Jeedom 4.4** (démo ou VM vierge, par ClaudeBox ; pas par cette session) : les noms de variables du core effectivement présents, le rendu clair et sombre de la fenêtre d'une pièce, le menu « ⋯ », le contrôle segmenté et le sticky ; tout écart (variable absente) est couvert par le repli
**And** `color-mix()` absent (vieux Safari / iPad mural) → le repli `rgba()` s'applique : test CSS `@supports not`.

**AC26 — Accessibilité minimale**
**Given** les nouveaux composants
**When** le harnais les teste
**Then** l'état n'est jamais porté par la seule couleur (mot présent + icône) ; le menu « ⋯ », le contrôle segmenté, le repli des ignorées et l'encart de cause sont opérables au clavier avec les rôles/états ARIA indiqués aux AC10, AC12, AC15 ; les boutons-icônes ont un `aria-label` (au glossaire).

**AC27 — Conventions de la story**
**Given** CLAUDE.md et `_bmad-output/project-context.md`
**When** la PR de dev est ouverte
**Then** une branche / une PR = ce sujet ; titre en Conventional Commits ; `make test`, `node --test tests/unit/*.node.test.js`, `flake8` et les tests PHP passent ; `scripts/ci-local.sh` est vert avant push
**And** les captures et fixtures ne contiennent aucun nom réel d'équipement, de pièce, de scénario ou de personne, ni IP privée ni secret (CC-48) ; l'état final de 22-2 n'est pas modifié par cette PR.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) **[réservé à l'humain / ClaudeBox ; une session cloud NE LA FAIT PAS (CC-48 : aucun accès box, SSH ni Home Assistant)]**
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
  - [ ] Relever sur VM Jeedom 4.4 et 4.6.1 : valeur de `--bg-color` clair et sombre, présence de chaque variable du core utilisée, attribut `data-theme` (alimente AC19, AC21, AC25).
- [ ] Task 1 — Fonction d'état unique (AC: 1, 2, 3, 4)
  - [ ] 1.1 Écrire `test_story_25_1_etat_unique.node.test.js` (table de vérité D1) **avant** le code.
  - [ ] 1.2 Implémenter `resolveEquipmentState` ; supprimer `publicationSummaryState` et `buildPublicationSummaryLabel` ; migrer `renderSummary`, `summarizeEquipmentCounters`, `summarizeRoom`.
  - [ ] 1.3 Test d'invariant badge = compteur = tableau (AC3).
- [ ] Task 2 — Catégories de commande (AC: 5, 6, 15)
  - [ ] 2.1 Partition D3 table-driven sur `REASON_LABELS` ; Ignorée hors défauts.
  - [ ] 2.2 Réécrire `buildRoomCounterLabels` / `buildEquipmentCounterLabels` (zéros masqués, pluriels accordés).
  - [ ] 2.3 Ligne repliée des ignorées.
- [ ] Task 3 — Glossaire (AC: 7, 8, 9)
  - [ ] 3.1 Appliquer D4 dans `desktop/js/*.js`, `desktop/php/jeedom2ha.php` (« Bridge » → « Démon », « Rescanner la topologie Jeedom » → « Relire Jeedom »), `REASON_LABELS`.
  - [ ] 3.2 `test_story_25_1_glossaire.node.test.js` ; mise à jour des tests existants sans affaiblissement.
- [ ] Task 4 — Réorganisation de la fenêtre (AC: 10 à 16, 26)
  - [ ] 4.1 Contrôle segmenté + « Appliquer » conditionnel.
  - [ ] 4.2 Menu « ⋯ » (équipement et pièce).
  - [ ] 4.3 Tableau regroupé par entité, colonnes de l'AC13.
  - [ ] 4.4 Encart de cause unique + bouton « Ouvrir les types génériques » (après réponse à Q5).
  - [ ] 4.5 Un seul équipement déplié, en-tête collant, suppression du défilement imbriqué.
- [ ] Task 5 — Palette et thème (AC: 17 à 21, 25)
  - [ ] 5.1 Définir `--j2ha-*` sous `body[data-theme*="Dark"|"Light"]` + repli sans thème.
  - [ ] 5.2 Remplacer toutes les couleurs en dur (CSS) et les `style=` colorés (PHP/JS) ; classe de largeur de modale.
  - [ ] 5.3 `test_story_25_1_palette_theme.node.test.js` (littéraux, replis, contrastes, préfixes).
- [ ] Task 6 — Documentation (AC: 23)
  - [ ] 6.1 Réécrire le bloc `compteurs.md` seul ; réaligner `index.md` ; entrée `changelog_beta.md`.
  - [ ] 6.2 `test_story_25_1_documentation.node.test.js` (successeur de 22-2).
- [ ] Task 7 — Gate 20-0 et non-régression (AC: 22, 24, 25, 27)
  - [ ] 7.1 Adapter les 5 parcours aux nouveaux libellés sans retirer d'assertion ; lancer les suites simulées.
  - [ ] 7.2 `git diff --stat main...HEAD -- resources/daemon …` vide ; tests golden verts.
  - [ ] 7.3 `make test`, `node --test tests/unit/*.node.test.js`, `flake8`, tests PHP, `scripts/ci-local.sh`.
- [ ] Task 8 — Preuve terrain (humain / ClaudeBox, après fusion ; CC-48)
  - [ ] 8.1 Gate 20-0 contre la box ; rendu clair + sombre ; Jeedom 4.4 et 4.6.1 ; consigner dans `25-1-preuve-terrain-<date>.md`.
  - [ ] 8.2 Bascule de 22-2 à `done` (superseded) par ClaudeBox ; story à `ready-for-UX-validation`, validation finale transférée à 25.5.

## Dev Notes

### Dev Agent Guardrails

- **Ne jamais** modifier `resources/daemon/` (AC22) ni `models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`.
- **Aucune décision recalculée côté front** : lire `published_in_ha`, `override_pending`, `synced_should_publish`, `equipment_decision` et les diagnostics déjà portés (diagnostic-ux § 4.8).
- Écritures : **mêmes routes** qu'avant (exclure / forcer / revenir / publier / supprimer / republier) ; le contrôle segmenté n'en crée aucune.
- D10 : le `generic_type` natif Jeedom n'est jamais écrit ; le bouton « Ouvrir les types génériques » ne fait qu'ouvrir l'écran Jeedom.
- Libellés via `{{…}}` / `__()` ; **aucun fichier `core/i18n` n'existe dans le dépôt** (relevé le 18/10) : ne pas en créer sans décision.
- CSS préfixé `.j2ha-…`, jamais de restylage de `.label/.btn/.panel/.modal/.objectDisplayCard`.
- Aucun nom réel dans les fixtures, tests, docs, commits, PR (CC-48).
- Une session cloud n'utilise jamais `scripts/deploy-to-box.sh` ni SSH ; elle saute la Task 0 et la Task 8 et le dit dans la PR.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Contraintes Jeedom (CADRAGE § « Contraintes Jeedom », diagnostic § 4-5, relevées sur 4.6.1 le 18/10)

- Page du plugin = HTML libre dans la zone de contenu ; grille + modale = convention.
- Thème : `<body data-theme="core2019_Dark|core2019_Light">` ; variables du core `--bg-color` (triplet sans `rgb()`), `--bg-modal-color`, `--txt-color`, `--link-color`, `--logo-primary-color`, `--al-success-color`, `--al-warning-color`, `--al-danger-color`, `--al-info-color`, `--eqTitle-color`, `--btn-default-color`, `--border-radius` (= `0rem` en sombre). Noms **à recontrôler sur 4.4**.
- Bibliothèques disponibles : jQuery 3.6, Bootstrap 3, bootbox, jeeDialog, jeedomUtils, Font Awesome 5 local, icônes `jeedom-*`. Aucune police ni bibliothèque externe.
- `position: sticky` fonctionne dans `.modal-body` si c'est elle qui défile (diagnostic § 4.5) : retirer le `max-height` interne.
- Performance : aucune requête ajoutée (la route agrégée est 25.2).

### Tests existants à surveiller

`test_story_16_8_mapping_surface`, `test_story_16_8_cc38_excluded`, `test_story_19_3_ac4_ac6_reason_labels_sync_badge`, `test_story_20_2_ac8_exclu_sans_commande`, `test_story_20_2_p1_p2_comportement_surface`, `test_story_20_3_*`, `test_story_21_1_cc47_command_published_by_secondary`, `test_story_22_2_*`, `test_story_20_0_gate_*`, et `resources/daemon/tests/unit/test_story_19_0_parity_golden_corpus.py` / `test_story_8_4_golden_file.py` (doivent rester verts **sans** modification).

### Fichiers probablement touchés (pour le `dev-story`)

`desktop/js/jeedom2ha_mapping_override.js`, `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/js/jeedom2ha.js`, `desktop/php/jeedom2ha.php`, `desktop/css/jeedom2ha.css`, `docs/fr_FR/index.md`, `docs/fr_FR/compteurs.md`, `docs/fr_FR/changelog_beta.md`, tests Node listés ci-dessus (modifiés), nouveaux `tests/unit/test_story_25_1_*.node.test.js`, `tests/unit/helpers/*`, `tests/e2e/gate/parcours/*.mjs`.

### Mise en œuvre — rappels de décision

- Le « Bloqué » d'un équipement **publié** (au moins une commande dans HA) n'est jamais un état : c'est la mention orange « N bloquées » à côté de « Publié ».
- Le sens de « À appliquer » est unique : plan ≠ réalité (réglage en attente **ou** publication due non faite). Le futur n'apparaît nulle part ailleurs.
- Sources de l'ordre des colonnes et du regroupement : diagnostic P10, P11, P12 ; maquette A (onglet A, données fictives).

### Définition de done

AC1 à AC27 tenus ; suites locales vertes ; PR revue par ClaudeBox ; preuve terrain (Task 8) ; statut `ready-for-UX-validation` (la validation UX finale est portée par 25.5, Q1 du cadrage) ; 22-2 passé à `done` (superseded) par ClaudeBox.

### References

- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/CADRAGE.md`] — glossaire imposé, direction A, contraintes Jeedom.
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/epic-25-draft.md`#Stories proposées, 25.1] — périmètre et clôture de 22-2 (Q1).
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/diagnostic-ux.md`] — P2 (trois vérités), P3 (ignorées), P4-P6 (palette, hiérarchie), P7-P13 (compteurs, tableau, cause, vocabulaire), P15 ; § 3 glossaire ; § 4-5 contraintes ; § 6 décision.
- [Source: `_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/maquettes.html`, onglet A] — fenêtre d'une pièce, équipement à plusieurs entités (données fictives).
- [Source: `_bmad-output/implementation-artifacts/22-2-compteurs-et-lisibilite-de-la-surface-cc51-cc55-cc58-cc60.md`] — sémantique « publié = présent dans HA », cas « jamais synchronisé », capteur secondaire.
- [Source: `_bmad-output/implementation-artifacts/sprint-status.yaml`] — entrées `pe-epic-25` et `25-1-socle-etat-unique-glossaire-palette-theme` (statut `backlog`).
- [Source: `CLAUDE.md`, `docs/delegation-claude-cloud.md`] — règles des sessions cloud (pas de box, pas de SSH).

## Dev Agent Record

### Agent Model Used

_(à renseigner par le dev-story)_

### Debug Log References

### Completion Notes List

- Rédaction `create-story` (session cloud déléguée, 2026-10-18) : documentaire seulement ; aucun fichier de code, de test ou de doc utilisateur modifié ; `sprint-status.yaml` non modifié (statut `backlog` conservé, `ready-for-dev` non accordé).

### File List

_(à renseigner par le dev-story)_

## Questions ouvertes pour Alexandre

Adressées à **Alexandre** (relayées par ClaudeBox). Aucune n'est tranchée par cette rédaction ; chaque question donne une recommandation, qui sert de valeur par défaut au `dev-story` **seulement si Alexandre l'accepte**. `ready-for-dev` reste bloqué tant que Q1 à Q7 ne sont pas répondues.

**Q1 — Un équipement jamais synchronisé, publiable mais absent de Home Assistant, est-il « À appliquer » ?** (règle R5)
- A. Oui, « À appliquer » (le bouton « Appliquer »/la synchro est le geste qui le règle). *(recommandé : cohérent avec « plan ≠ réalité → À appliquer »)*
- B. Non, un état distinct ou « Rien à publier » tant qu'aucune synchro n'a eu lieu (22-2 ne le comptait pas comme « en attente »).
Impact : sur une installation neuve, A affiche beaucoup de bleu avant la première synchro.

**Q2 — Démon plus ancien (présence inconnue, `published_in_ha` = `null`) : quel état ?** (règle R6)
- A. « À appliquer », jamais « Publié ». *(recommandé)*
- B. Aucun état, mention « présence inconnue » en gris.

**Q3 — Partition « Ignorée » / « Bloquée » (D3).** Je propose `command_not_covered` et `no_supported_generic_type` en « Ignorée », tout le reste corrigeable en « Bloquée ». Confirmes-tu cette liste, notamment `ha_component_not_in_product_scope` et `no_projection_possible` (classés « Bloquée » par prudence) ? Un code que tu juges non corrigeable doit passer en « Ignorée ».

**Q4 — Compteurs de commandes au niveau de la pièce.** Le diagnostic (P7) propose de ne plus compter les commandes au niveau de la pièce (l'unité de décision est l'équipement). A. Les retirer de l'en-tête de la pièce, ne garder qu'une ligne « publiées · bloquées · ignorées » dans chaque équipement déplié. *(recommandé)* B. Garder une ligne de commandes dans l'en-tête de la pièce (publiées · bloquées · ignorées).

**Q5 — Cible du bouton « Ouvrir les types génériques ».** Aucun écran Jeedom n'est référencé dans le dépôt pour cet usage et je n'ai pas pu le vérifier (CC-48 : pas d'accès à une instance). Quelle URL / quel écran Jeedom (4.4 **et** 4.6.1) faut-il ouvrir : l'écran de configuration des types génériques du core, la page de l'équipement concerné, ou un autre ? ClaudeBox doit le relever sur la VM avant la Task 4.4 ; à défaut, le bouton ouvre la page de l'équipement Jeedom concerné.

**Q6 — Thème inconnu.** Si `body[data-theme]` est absent ou inconnu (Jeedom 4.4 non vérifié), quel jeu appliquer ? A. Clair. *(recommandé : le repli le moins surprenant)* B. Sombre.

**Q7 — Portée du « glossaire partout ».** Les libellés de la **page principale** (« Bridge » → « Démon », « Rescanner la topologie Jeedom » → « Relire Jeedom », « Supprimer de Home Assistant… ») sont renommés dans cette story, mais la **structure** de la page principale reste celle d'aujourd'hui (bandeau bleu, boutons) jusqu'à 25.3. A. Oui, libellés seulement ici. *(recommandé : évite deux passes de rédaction de la doc)* B. Reporter ces libellés à 25.3.

**Q8 (hors périmètre par défaut, à confirmer) — Icône/couleur Jeedom des objets et regroupement des cartes par objet parent.** Cité dans `CADRAGE.md` (« A — socle ») mais absent de la liste de 25.1 dans `epic-25-draft.md`, et les cartes sont refaites par 25.3. J'ai **exclu** ce point de 25.1 ; recommandation : le traiter en 25.3. Dis-moi si tu le veux dans 25.1.

**Q9 — Libellé de la demande.** La demande d'origine parle de « contrôle de republication à 3 états ». J'ai compris le *réglage de publication* Automatique / Toujours / Jamais (qui remplace Exclure / Forcer / Revenir), pas une nouvelle option de « Republier ». Merci de confirmer.

**Q10 — Gate 20-0 et VM 4.4.** La preuve de compatibilité 4.4 (AC25) suppose une VM Jeedom 4.4 disponible pour ClaudeBox (la démo VM 122 est-elle en 4.4 ou 4.6 ?). Sinon, la compatibilité 4.4 ne sera démontrée que par les replis CSS testés, pas par un rendu réel.

## Change Log

- 2026-10-18 — Création (`create-story`, session cloud déléguée) : story rédigée, statut `backlog`, 27 AC, 10 questions ouvertes pour Alexandre.
