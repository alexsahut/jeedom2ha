# Story 25.7 : Cause d'exclusion affichée

Status: ready-for-UX-validation

> **Statut : `ready-for-dev` (2026-10-19 17:40, relecture et décisions ClaudeBox ; Alexandre présent, peut revenir sur une décision).** Précédemment : **`backlog` (2026-10-19).** Story rédigée par une session cloud déléguée (`create-story`, documentaire : aucun code, aucun test, aucune fixture, aucun accès box / VM / Home Assistant / SSH / secret, CC-48), à partir du sprint change `sprint-change-proposal-2026-10-19-revue-ux-25.md` (statut **decided**, point 3 du déclencheur). **`ready-for-dev` n'est pas accordé** : relecture de la story par ClaudeBox, puis décisions sur Q1 à Q7 (§ Questions ouvertes, chacune avec une recommandation argumentée ; la session n'en tranche aucune). **Statut cible après implémentation et preuve terrain : `ready-for-UX-validation`** ; validation UX finale en **25.5**. Les points de § Décisions déjà arbitrées sont **fermés**. Pointeurs de code pris sur `main` à `731be8d` ; **à re-vérifier au SHA courant** (après 25.6) avant le `dev-story`. Aucun nom réel d'équipement, de pièce, d'objet, de plugin installé chez Alexandre, de scénario ou de personne : identifiants et données fictifs seulement (CC-48).

## Story

En tant que propriétaire qui voit un équipement « Exclu »,
je veux lire **pourquoi** il l'est — par le plugin X, par la pièce, ou individuellement (« Jamais ») — sur sa ligne dans l'arbre, dans son détail et sur la carte de sa pièce,
afin de savoir où agir pour le reprendre, sans chercher dans la page de configuration ni dans la documentation.

**Parcours : interface seule (`desktop/js/`, éventuellement `desktop/php/` pour la donnée de la Q1, `desktop/css/`), docs, tests Node, gate 20-0.** **Aucune modification du démon ni de la liste blanche de `getEquipmentStates`** (AC12).

**Dépendances :** 25.6 (même fichier `jeedom2ha_workview.js`, la branche part de 25.6 fusionnée). Ordre décidé : 25.6 → **25.7** → 25.8 → 25.9 → 25.5. 25.8 réutilise la cause « par la pièce » définie ici (carte « Pièce exclue », grisé de « Toujours »).

## Décisions déjà arbitrées

1. **La donnée existe** : la cause est dans `equipment_decision.publication_reason` de l'entrée agrégée (route 25.2, liste blanche) et de l'arbre unitaire : `excluded_plugin`, `excluded_object`, `excluded_eqlogic` (mécanisme A1, éligibilité), `publication_excluded_eqlogic`, `publication_excluded_command` (mécanisme A2, « Jamais »). Afficher la cause **ne touche que l'interface**. (Sprint change, § Analyse.)
2. **Une seule cause par équipement**, dans la priorité déjà appliquée par Jeedom et le démon : équipement > plugin > pièce pour A1 (`core/class/jeedom2ha.class.php:841-851`), et A1 avant A2 (l'éligibilité passe avant le réglage de publication). **Pas de causes cumulées** (hors périmètre du sprint change).
3. **Vocabulaire du glossaire 25.1** ; la cause est une **mention** à côté du mot d'état « Exclu », **pas un 7ᵉ état** ; les six états et leurs effectifs ne changent pas.
4. **« Désactivé » prime** : un équipement désactivé dans Jeedom s'affiche « Désactivé » et **aucune** cause d'exclusion n'est affichée pour lui (25.1 R3 avant R4).
5. **Mécanisme A3 (`publishedScope*`) hors périmètre** : aucune cause n'en est déduite.
6. **Source de vérité unique de l'état** (`resolveEquipmentState`), aucune réécriture ; ajouts purs seulement dans `jeedom2ha_mapping_override.js` (25.4 AC4).
7. **Zéro requête ajoutée** ; aucune lecture d'arbre unitaire pour afficher une cause dans l'arbre, sur une carte ou dans le détail de pièce (25.4 D3, AC6).
8. **Gate 20-0 sans affaiblissement**, registres d'assertions de 25.4 (et de 25.6) comme plancher ; `lib/policy.mjs` inchangé (aucune écriture nouvelle).
9. **CSS** sous `.j2ha-wv` / `.j2ha-wv-*` ou classes nouvelles préfixées, aucun sélecteur nu sur une classe partagée (leçon #296) ; aucune couleur en dur.
10. **Statut cible : `ready-for-UX-validation`**, validation UX finale en 25.5.

## Sources lues

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-19-revue-ux-25.md` (tableau A1 / A2 / A3, découpage 25.7) ; `epic-25-draft.md` ; `epics-projection-engine.md` § Epic 25 ; `sprint-status.yaml`.
- `25-1-socle-etat-unique-glossaire-palette-theme.md` (D1 R3/R4, D4 glossaire, AC23 termes interdits) ; `25-2-route-agregee-cote-demon.md` (§ Contrat final, liste blanche, AC3 parité) ; `25-3-page-principale-b.md` (cartes, repères) ; `25-4-vue-maitre-detail-c.md` (AC11 lignes d'arbre, AC14, AC15) ; `25-6-vue-c-filtree-sur-la-piece.md`.
- Code (lecture seule, `main` `731be8d`) : `desktop/js/jeedom2ha_mapping_override.js` (`REASON_LABELS` `:612-643`, dont `excluded_*` et `publication_excluded_*` `:632-641` ; `EXCLUDED_PUBLICATION_REASONS` `:647-653` ; `isExcludedDiagnostic` `:703`, `buildExcludedLabel` `:708` ; `analyzeEquipment` `:928-939` ; `resolveEquipmentState` `:951` ; `EQUIPMENT_STATE_LABELS` `:1133` ; `publicationActionState`, cas inéligible `:198-205`) ; `desktop/js/jeedom2ha_mapping_surface.js` (cellules « Exclue » `:87-122`, `buildSegmented` `:1076`, `renderNotices` `:1000`) ; `desktop/js/jeedom2ha_workview.js` (`buildTreeModel` `:119`, `buildEquipmentItem` `:726`, détail de pièce `:852-1000`) ; `desktop/js/jeedom2ha_overview.js` (`computeOverview` `:79`, `renderCards` `:388`) ; `desktop/php/jeedom2ha.php` (`j2haRoomsTree` `:18-75` : `eq_id`, `eq_name`, `enabled` — **pas de plugin**) ; `core/class/jeedom2ha.class.php` (`:764-766`, `:841-851` priorité eqlogic > plugin > object, `eq_type` envoyé au démon `:877`) ; `resources/daemon/transport/http_server.py` (`_project_equipment_state` `:3370`, `_decision_view` `:2717`) ; `docs/fr_FR/index.md` (§ « Les badges de synthèse », famille 7 « Exclusions volontaires » `:485-495`) ; `docs/fr_FR/compteurs.md` (R4).

## Contexte et périmètre

### Ce qui existe aujourd'hui (relevé sur `731be8d`)

- Un équipement exclu s'affiche « Exclu » (badge, ligne d'arbre, KPI « exclu »), compté dans « exclus et autres » sur la jauge. **La cause n'est visible nulle part pour un équipement exclu par A1** : un équipement inéligible n'a ni entité ni commande dans l'arbre, donc pas de cellule « Exclue → … » ; la seule trace est l'infobulle des cellules de commande pour A2 (`buildExcludedLabel` : « Exclue → exclu manuellement (commande) »), et le segment « Jamais » actif pour `publication_excluded_eqlogic`.
- Les libellés techniques existent (`REASON_LABELS`) mais sont longs et ne nomment pas le plugin : « exclu de Jeedom2HA (plugin source dans la liste d’exclusions) ».
- **Le nom du plugin n'est pas disponible côté interface** : ni l'entrée agrégée (liste blanche de 25.2 : `jeedom_eq_id`, `equipment_decision`, `entities[{override_pending}]`, `commands[…]`, `sync_status`), ni l'arbre unitaire, ni `j2haRoomsTree` (`eq_id`, `eq_name`, `enabled`) ne portent le type de l'équipement. Le démon le reçoit (`eq_type`), mais ne le renvoie pas. → **Q1**.

### Dans le périmètre

- une fonction pure de cause (D1) et son test de parité agrégé / unitaire (AC1, AC2) ;
- la mention de cause sur la ligne de l'arbre (AC3), dans le détail d'équipement (AC4), dans le détail de pièce et sur la carte (AC5) ;
- la donnée « plugin X » selon la décision de Q1 (AC6) ;
- glossaire, accessibilité, CSS (AC7, AC8) ; gate 20-0 (AC9) ; documentation (AC10) ; non-régression, conventions, statut (AC11 à AC14).

### Hors périmètre (ne pas faire ici)

- toute modification de `resources/daemon/`, `core/ajax/`, `core/class/`, de la liste blanche, du contrat de décision, des artefacts figés (`models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`), de `tests/e2e/gate/lib/policy.mjs` ;
- toute **écriture** : bouton « exclure / ne plus exclure la pièce » (25.8), page de configuration (25.9) ; un lien d'action peut **renvoyer** vers l'endroit où agir (Q4) mais n'écrit rien ;
- un filtre par cause, une puce « exclus par … », un 7ᵉ état, des causes cumulées ; le mécanisme A3 ;
- la validation UX finale (25.5).

## Définitions normatives

### D1 — Cause d'exclusion d'un équipement

Fonction pure **ajoutée** à `jeedom2ha_mapping_override.js` (nom indicatif `exclusionCauseOf(entry, enabled)`), appliquée **à l'entrée agrégée** (arbre, cartes, détail de pièce) comme **à l'arbre unitaire** (détail d'équipement) :

1. si `resolveEquipmentState(entry, enabled).state !== 'excluded'` → **aucune cause** (`null`) ; en particulier un équipement « Désactivé » n'a jamais de cause ;
2. sinon, si `equipment_decision.publication_reason` est une raison d'exclusion, elle est la cause ;
3. sinon (état « Exclu » parce que **toutes** les commandes sont exclues, R4 de `compteurs.md`), la cause est la raison d'exclusion des commandes **si elle est la même pour toutes** ; sinon `null` (jamais de cause inventée ni cumulée) ;
4. raison inconnue ou absente → `null`.

| `publication_reason` | Genre | Mention courte (ligne, carte) | Phrase du détail (Q2) | Où agir (Q4) |
|---|---|---|---|---|
| `excluded_plugin` | par le plugin | « par le plugin X » (X selon Q1) | « Exclu par le plugin X (configuration du plugin, « Plugins exclus ») » | configuration du plugin |
| `excluded_object` | par la pièce | « par la pièce » | « Exclu par la pièce : toute la pièce est exclue » | configuration du plugin (25.8 : sur la carte et dans le détail de pièce) |
| `publication_excluded_eqlogic` | individuelle | « individuelle » | « Exclusion individuelle : réglage « Jamais » » | contrôle « Automatique / Toujours / Jamais » |
| `publication_excluded_command` (toutes les commandes) | individuelle | « individuelle » | « Exclusion individuelle : « Jamais » sur ses entités » | réglage de chaque entité |
| `excluded_eqlogic` | individuelle | « individuelle » (Q3) | « Exclusion individuelle : réglage de l'équipement dans Jeedom » | l'équipement, dans Jeedom |

Le retour de la fonction est un objet `{ kind: 'plugin' | 'piece' | 'individuelle', code: <publication_reason> }` ou `null` ; le **libellé** est produit par une seconde fonction pure à partir de `kind`, `code` et du nom de plugin (Q1). Aucun libellé n'est dupliqué hors de ces deux fonctions.

### D2 — Ventilation par pièce

Pour une pièce, la **ventilation des exclus** est le décompte, par `kind` (et, pour `plugin`, par plugin), des équipements **lus** de la pièce dont la cause n'est pas `null`. La somme de la ventilation est **≤** l'effectif « exclu » de la pièce (`summarizeRoom`) ; l'écart (cause `null`) est montré comme « autre » seulement s'il est non nul (jamais inventé). Calcul à chaque rendu, depuis la copie unique en mémoire (25.3 D3) : aucune seconde vérité.

## Acceptance Criteria

### A. Fonction de cause

**AC1 — Table de vérité**
**Given** des fixtures fictives couvrant chaque ligne de D1, plus : désactivé + exclu (`enabled:false` avec `excluded_object`), exclu par toutes ses commandes « Jamais », commandes exclues par des raisons différentes, équipement non lu, `publication_reason` inconnu, `enabled ∈ {true, false, undefined}`
**When** `test_story_25_7_cause_exclusion.node.test.js` s'exécute (table-driven)
**Then** la cause rendue est exactement celle de D1 ; `null` pour tout équipement dont l'état n'est pas « Exclu », dont tout « Désactivé » ; aucune cause pour un équipement non lu
**And** `git diff main...HEAD -- desktop/js/jeedom2ha_mapping_override.js` ne montre que des **ajouts** (aucune ligne modifiée de `resolveEquipmentState`, `analyzeEquipment`, `REASON_LABELS`, `EXCLUDED_PUBLICATION_REASONS`, `summarizeRoom`, `summarizeHouse`).

**AC2 — Parité agrégé / unitaire**
**Given** les fixtures de parité de 25.2 (`tests/fixtures/story_25_2_parite_etat.json`), complétées par des cas d'exclusion fictifs
**When** on calcule la cause sur l'arbre unitaire et sur l'entrée agrégée correspondante
**Then** les deux causes sont `deepEqual` pour chaque équipement (la mention de l'arbre égale la phrase du détail au même `kind`).

### B. Affichage

**AC3 — Ligne de l'arbre (vue C)**
**Given** un équipement « Exclu » dont la cause n'est pas `null`
**When** sa ligne est rendue dans l'arbre de la vue C
**Then** après le mot d'état « Exclu » et le nom, une mention grise `.j2ha-wv-cause` donne la mention courte de D1 (« par le plugin X », « par la pièce », « individuelle ») ; elle fait partie du nom accessible de la ligne ; elle est absente pour tout autre état et pour un équipement désactivé
**And** la ligne ne change ni de hauteur cible minimale (44 px en disposition étroite) ni d'ordre ; la mention est tronquée par ellipse avant le nom si la place manque (le nom de l'équipement reste prioritaire) ; aucune requête n'est émise (espion ajax).

**AC4 — Détail de l'équipement**
**Given** un équipement « Exclu » sélectionné (arbre unitaire lu, 25.4 D3)
**When** le détail est rendu
**Then** sous le badge d'état, un encart neutre (gris, icône `fa-eye-slash`, `role="status"`) donne la **phrase** de D1 et, selon Q4, l'endroit où agir ; il n'y a **qu'un** encart de cause (25.1 « cause dite une fois ») ; un équipement désactivé n'a pas cet encart
**And** pour `publication_excluded_eqlogic`, le contrôle segmenté reste le seul moyen d'agir (« Jamais » actif, inchangé) ; pour une cause A1, « Toujours » et « Jamais » restent grisés comme aujourd'hui (`publicationActionState`, cas inéligible), **leur infobulle est inchangée dans cette story** (le grisé motivé par la pièce est porté par 25.8, D1 du sprint change).

**AC5 — Détail de pièce et carte**
**Given** une pièce dont au moins un équipement lu est « Exclu »
**When** le détail de pièce (vue C) et la carte (page B) sont rendus
**Then** le détail de pièce affiche, sous les KPI, une ligne « Exclus : » suivie de la ventilation D2 dans l'ordre plugin(s), pièce, individuelle, autre (zéros omis, pluriels accordés par le code, ex. « 2 par le plugin X, 1 individuelle ») ;
**And** la carte affiche un repère gris `.j2ha-mark-excluded` « N exclus » (N = effectif « exclu » de la pièce, même nombre que le KPI) dont le nom accessible et l'infobulle portent la même ventilation ; le repère est absent si N = 0 ; il ne change ni la jauge, ni le ratio « n / t publiés », ni l'ordre des repères existants (bloqués, à appliquer, non lus) (Q5)
**And** l'invariant « somme de la ventilation ≤ N » est vérifié sur 20 fixtures seedées (`test_story_25_7_ventilation.node.test.js`) ; aucune requête n'est émise.

**AC6 — Nom du plugin**
**Given** la décision de Q1 (par défaut : A)
**When** une cause `excluded_plugin` est affichée
**Then** X est le **nom affiché du plugin** (repli : identifiant technique du plugin s'il n'a pas de nom lisible) ; la donnée vient de la page (`desktop/php/`), jamais du démon ni de la route agrégée ; elle est échappée (`.text()`, jamais `.html()`) ; un test PHP vérifie l'ajout **additif** à `j2haRoomsTree` (aucun champ existant renommé ni retypé, `test_story_25_3_php_hierarchie.php` vert) et la table des noms (fixtures fictives)
**And** si la donnée est absente pour un équipement (plugin désinstallé, champ vide), la mention est « par son plugin » — jamais « par le plugin undefined » ni une chaîne vide.

### C. Glossaire, accessibilité, CSS

**AC7 — Glossaire**
**Given** les libellés nouveaux (mentions et phrases de D1, « Exclus : », « autre », « N exclus », « par son plugin »)
**When** `test_story_25_1_glossaire`, `test_story_25_3_glossaire`, `test_story_25_4_glossaire` (étendus) s'exécutent
**Then** tous les libellés passent par `{{…}}`, sans point final dans les mentions, sans terme interdit (25.1 AC23 : « override », « bridge », « prête », « (s) »…) ; le mot d'état reste « Exclu » (aucun « Exclu par… » comme nouvel état) ; les six libellés d'état de `EQUIPMENT_STATE_LABELS` sont inchangés.

**AC8 — Accessibilité et CSS**
**Given** les éléments nouveaux (mention de ligne, encart de cause, ligne de ventilation, repère de carte)
**When** les tests de palette, de contrastes et d'anti-collision s'exécutent
**Then** les couleurs viennent de `--j2ha-*` (rôle gris de 25.1 D5), contrastes conformes sur les deux thèmes ; le CSS nouveau est sous `.j2ha-wv` / `.j2ha-wv-*` ou sur la classe nouvelle `.j2ha-mark-excluded` déclarée sous `.j2ha-room-groups` (aucune règle modifiée sur `.j2ha-mark` nue) ; `test_story_25_4_css_collision` passe avec la référence mise à jour **par ajout seulement** ; l'information n'est jamais portée par la seule couleur.

### D. Gate, documentation, non-régression

**AC9 — Gate 20-0**
**Given** les registres d'assertions (25.4, et celui de 25.6 s'il existe) comme plancher
**When** le parcours `vue-maitre-detail-c` est complété d'une étape nouvelle `cause-exclusion` (lecture seule)
**Then** elle vérifie, sur la box : chaque ligne d'arbre au mot « Exclu » porte une mention de la forme D1 ou aucune (étiquette `cause-exclusion-hors-glossaire` sinon) ; aucune ligne « Désactivé » ne porte de mention (`cause-sur-desactive`) ; la somme des repères « N exclus » des cartes égale le nombre de lignes « Exclu » de l'arbre élargi (`exclus-carte-differents-de-l-arbre`) ; zéro requête du plugin pendant l'étape ; `record` : `exclus_par_plugin`, `exclus_par_piece`, `exclus_individuels`, `exclus_sans_cause`
**And** `lib/policy.mjs` est inchangé (diff vide) ; aucune écriture n'est déclarée ; les suites simulées passent.

**AC10 — Documentation**
**Given** `docs/fr_FR/index.md`, `compteurs.md`, `changelog_beta.md`
**When** la story est livrée
**Then** `index.md` (§ « Les badges de synthèse », § « Le détail d'un équipement », famille 7 « Exclusions volontaires ») décrit les trois mentions et où agir pour chacune ; `compteurs.md` dit que la ventilation n'ajoute pas d'état et que sa somme peut être inférieure au compte « exclu » ; `changelog_beta.md` reçoit une entrée ; `test_story_25_7_documentation.node.test.js` vérifie que chaque libellé cité existe verbatim dans `desktop/`.

**AC11 — Non-régression**
**Given** les suites `test_story_25_1_*`, `25_2_parite_etat`, `25_3_*`, `25_4_*`, `25_6_*`, `test_story_20_*`, `test_story_22_2_*`
**When** elles s'exécutent
**Then** elles passent ; un test qui comparait le texte exact d'une ligne d'arbre ou d'une carte est adapté **par ajout** de la mention attendue, jamais par retrait d'assertion ; la liste est consignée au Dev Agent Record.

**AC12 — Aucune modification hors interface**
**Given** la branche de la story
**When** on exécute `git diff --stat main...HEAD -- resources/daemon/ core/ plugin_info/ tests/e2e/gate/lib/policy.mjs scripts/`
**Then** la sortie est **vide** ; la seule modification de `desktop/php/` admise est l'ajout de la donnée de Q1 (si Q1 = A) ; la taille de la réponse `getEquipmentStates` est inchangée (aucun champ ajouté à la liste blanche).

**AC13 — Performance**
**Given** la fixture la plus lourde (292 équipements fictifs)
**When** la page B et la vue C sont rendues
**Then** le surcoût de calcul des causes et des ventilations est mesuré en Node et consigné au Dev Agent Record (sans seuil inventé) ; la cause est calculée une fois par équipement et par rendu (aucune boucle quadratique sur les pièces).

**AC14 — Conventions et statut**
**Given** CLAUDE.md
**When** la PR de dev est ouverte
**Then** une PR = ce sujet ; titre Conventional Commits ; `make test`, `node --test tests/unit/*.node.test.js`, tests PHP, `flake8`, `scripts/ci-local.sh` verts ; aucun nom réel ni nom de plugin réellement installé chez Alexandre dans les fixtures (plugins fictifs `plugin_alpha`, `plugin_beta`…), aucune IP ni secret (CC-48) ; Tasks 0 et 6 sautées par une session cloud et la PR le dit
**And** après la preuve terrain (Task 6) le statut passe à **`ready-for-UX-validation`** ; il reste `backlog` jusqu'à `ready-for-dev`.

## Statut cible et validation UX

- **Statut actuel :** `backlog` ; `ready-for-dev` non accordé.
- **Chemin :** `backlog` → `ready-for-dev` (relecture ClaudeBox + Q1 à Q7) → `review` → `ready-for-UX-validation` (preuve terrain ClaudeBox) → `done` à la clôture de 25.5.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY) **[réservée à ClaudeBox ; SAUTÉE par cette session cloud (CC-48)]**
  - [ ] Dry-run `./scripts/deploy-to-box.sh --dry-run` ; déploiement `--sha <complet> --restart-daemon` depuis un worktree neuf ; `Deploy complete.`
  - [ ] Relever (identifiants seuls) le nombre d'équipements exclus par cause sur la box, depuis le journal ou le gate, pour comparer à la Task 6.
- [x] Task 1 — Tests d'abord (AC: 1, 2, 5, 6)
  - [x] 1.1 `test_story_25_7_cause_exclusion` (table D1), parité agrégé / unitaire, `…_ventilation` (invariant), test PHP de la donnée de Q1.
- [x] Task 2 — Fonctions pures (AC: 1, 2, 7)
  - [x] 2.1 `exclusionCauseOf` et la fonction de libellé, **ajoutées** et exportées dans `jeedom2ha_mapping_override.js`.
- [x] Task 3 — Donnée « plugin X » (AC: 6) — selon Q1
  - [x] 3.1 (Q1 = A) champ additif dans `j2haRoomsTree` et table des noms, échappés.
- [x] Task 4 — Affichage (AC: 3, 4, 5, 8)
  - [x] 4.1 Ligne d'arbre (`buildTreeModel` / `buildEquipmentItem`), encart du détail d'équipement, ventilation du détail de pièce, repère de carte (`renderCards`).
  - [x] 4.2 CSS, contrastes, nom accessible.
- [x] Task 5 — Gate, documentation, non-régression (AC: 9 à 14)
  - [x] 5.1 Étape `cause-exclusion` de `vue-maitre-detail-c` ; registres verts ; `policy.mjs` intact.
  - [x] 5.2 `index.md`, `compteurs.md`, `changelog_beta.md`, test de documentation ; mesure Node ; suites complètes.
- [ ] Task 6 — Preuve terrain (après fusion) **[réservée à ClaudeBox ; SAUTÉE par cette session cloud (CC-48)]**
  - [ ] 6.1 Gate 20-0 contre la box, dont l'étape `cause-exclusion` ; contrôle négatif en échec attendu ; `25-7-preuve-terrain-<date>.md` (identifiants seuls).
  - [ ] 6.2 Vérifier sur la box que les équipements des deux pièces déjà exclues affichent « par la pièce », et qu'un équipement réglé « Jamais » affiche « individuelle » ; 0 ligne `ERROR` ; taille de la réponse inchangée ; statut `ready-for-UX-validation`.

## Dev Notes

### Dev Agent Guardrails

- **Ne jamais** modifier `resources/daemon/`, la liste blanche de la route, `core/`, `plugin_info/`, `tests/e2e/gate/lib/policy.mjs`, les artefacts figés (AC12).
- **Ne jamais** déduire une cause autrement que par D1 ; aucune cause pour un état autre que « Exclu » ; « Désactivé » prime.
- **Aucune lecture** d'arbre unitaire pour l'arbre, la carte ou le détail de pièce : l'entrée agrégée porte déjà `equipment_decision` et `commands[].diagnostic`.
- **Pas de 7ᵉ état**, pas de puce ni de filtre par cause, pas de couleur nouvelle (rôle gris existant).
- Libellés via `{{…}}` ; `.text()` pour le nom du plugin et de l'équipement ; aucun nom réel (CC-48).
- Une session cloud saute les Tasks 0 et 6 et le dit dans la PR.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` ; jamais de procédure parallèle. Référence : `jeedom2ha-test-context-jeedom-reel.md`. Cycle canonique `main → beta → stable → Jeedom Market`.

### Précédents réutilisables

- `isExcludedDiagnostic`, `EXCLUDED_PUBLICATION_REASONS`, `REASON_LABELS` (à **lire**, pas à modifier) ; `analyzeEquipment` (R4 « toutes les commandes exclues »).
- Ajout additif à `j2haRoomsTree` : précédent 25.3 AC13 (`father_id`, `icon_classes`, `color`) et `test_story_25_3_php_hierarchie.php`.
- Parité agrégé / unitaire : `test_story_25_2_parite_etat`.

### Fichiers probablement touchés (pour le `dev-story`)

`desktop/js/jeedom2ha_mapping_override.js` (ajouts purs) ; `desktop/js/jeedom2ha_workview.js` (ligne d'arbre, détail de pièce) ; `desktop/js/jeedom2ha_mapping_surface.js` (encart du détail d'équipement) ; `desktop/js/jeedom2ha_overview.js` (repère de carte) ; `desktop/php/jeedom2ha.php` et `jeedom2ha_overview_helpers.php` (donnée de Q1) ; `desktop/css/jeedom2ha.css` ; `docs/fr_FR/index.md`, `compteurs.md`, `changelog_beta.md` ; `tests/unit/test_story_25_7_*`, test PHP ; `tests/e2e/gate/parcours/vue-maitre-detail-c.mjs`.

### Definition of done

AC1 à AC14 tenus ; suites vertes ; PR relue par ClaudeBox ; preuve terrain (Task 6) ; statut `ready-for-UX-validation`.

### References

- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-19-revue-ux-25.md`#Analyse, #Découpage]
- [Source: `_bmad-output/implementation-artifacts/25-1-socle-etat-unique-glossaire-palette-theme.md`#D1, #D4, #AC23]
- [Source: `_bmad-output/implementation-artifacts/25-2-route-agregee-cote-demon.md`#Contrat final]
- [Source: `core/class/jeedom2ha.class.php`:841-851 (priorité des exclusions A1)]
- [Source: `docs/fr_FR/index.md`#Exclusions volontaires]

## UI Impact

- **UI Impact:** Oui — mention de cause sur la ligne d'arbre, encart dans le détail, ventilation dans le détail de pièce, repère « N exclus » sur la carte. Gate 20-0 obligatoire (AC9) ; statut cible `ready-for-UX-validation`.

## Dev Agent Record

### Agent Model Used

Claude (session cloud déléguée, branche `claude/stories-25-6-25-7-aebjpn`, 2026-10-19), après 25.6 (statut `review`, même branche).

### Debug Log References

- Task 1 : `test_story_25_7_cause_exclusion`, `…_ventilation` et le test PHP ont été commités rouges (32 tests Node en échec, test PHP en erreur fatale) avant le code. `test_story_25_7_detail_equipement` (AC4) a été écrit APRÈS l'affichage du détail (il est vert dès sa première exécution).
- Le premier essai de contrôle négatif du gate (patch de la bibliothèque dans la page) ne rejetait pas : l'étape 6 du parcours recharge la page, ce qui effaçait le patch. Le patch est désormais posé par `addInitScript` à l'affectation de `Jeedom2haMappingOverride`, avant chaque chargement.
- Tests de 25.x échoués après l'ajout puis adaptés PAR AJOUT (liste ci-dessous) : `test_story_25_4_ecritures_deplacees` interdit de modifier `renderSummary` (comparé à main) : l'encart est donc rendu par une fonction nouvelle `renderExclusion`, appelée par `renderEquipmentTree` (colle) et `refreshEquipmentState`.
- `scripts/ci-local.sh` (relancé en fin de story, après les deux stories) : flake8, pytest 3.9 / 3.11 / 3.12 (2404 passed, 2 skipped), node (1022 tests), `bash -n`, `php -l`, tests PHP : tout vert. `make test` (pytest direct) : 778 passed, 2 skipped.

### Completion Notes List

- **D1** : `exclusionCauseOf(tree, enabled)` (ajout pur à `jeedom2ha_mapping_override.js`, `git diff` : aucune ligne supprimée) : `null` hors état « Exclu » (donc jamais pour « Désactivé » ni « non lu ») ; sinon la raison d'exclusion de `equipment_decision`, sinon la raison commune des commandes exclues ; jamais de cause cumulée. Parité agrégé / unitaire (`deepEqual`) sur les fixtures de 25.2 et sur des cas fictifs. `exclusionCauseText(cause, nom, 'short'|'sentence')` produit les libellés `{{…}}` (repli « son plugin ») ; `exclusionBreakdown` / `exclusionBreakdownText` (D2, Q6 : « N autre »).
- **Q1 = A (page)** : `eq_type` (identifiant validé par liste blanche) ajouté à chaque équipement de `j2haRoomsTree` et table `j2haPluginNames` {identifiant: nom affiché} pour les seuls plugins présents, repli sur l'identifiant (`j2ha_plugin_id`, `j2ha_plugin_names` dans `jeedom2ha_overview_helpers.php` ; `jeedom2ha.php`). Aucun champ existant renommé ni retypé (test 25.3 étendu par ajout). Aucune modification du démon ni de la liste blanche de la route ; la table servira à 25.9.
- **Affichage** : ligne d'arbre (`.j2ha-wv-cause`, après le nom, ellipse avant le nom) ; détail d'équipement (encart neutre `.j2ha-eq-exclusion .j2ha-notice-neutral`, `role="status"`, icône `fa-eye-slash`, lien « Ouvrir la configuration du plugin » pour une cause de plugin seulement, aucune écriture — Q4 ; pour « par la pièce », le renvoi vers le contrôle de 25.8 viendra avec 25.8) ; détail de pièce (ligne « Exclus : » sous les KPI, `computeOverview` calcule la ventilation) ; carte (repère gris `.j2ha-mark-excluded` « N exclus », en dernier, infobulle + `aria-label` = ventilation, ajoutée aussi au nom accessible de la carte). Aucune requête (espion ajax).
- **CSS** : sous `.j2ha-wv` / `.j2ha-wv-*` ; la seule règle hors `.j2ha-wv` est `.j2ha-room-groups .j2ha-mark.j2ha-mark-excluded` (prévue par l'AC8) : les listes blanches de `test_story_25_4_css_collision` et `…_palette_theme` sont étendues PAR AJOUT d'exactement cette entrée. Couleurs : `--j2ha-neutral`, `--j2ha-line`, `--j2ha-surface-strong` seulement.
- **Gate 20-0** : étape 10 `cause-exclusion` ajoutée à `vue-maitre-detail-c` (lecture seule : arbre élargi filtré sur « exclus et autres », étiquettes `cause-exclusion-hors-glossaire`, `cause-sur-desactive`, `exclus-carte-differents-de-l-arbre`, `requete-pendant-cause-exclusion` ; `record` `exclus_par_plugin`, `exclus_par_piece`, `exclus_individuels`, `exclus_sans_cause`). `readCards` ignore désormais aussi le repère « N exclus » dans la comparaison des repères carte / arbre (comme « non lus » ; la somme des repères est vérifiée par la nouvelle étape). `policy.mjs`, lanceur, interception inchangés ; registre de 25.4 vert. Contrôles négatifs en vrai Chromium (mention hors glossaire, somme des repères). La branche « cause-sur-desactive » n'a pas de contrôle négatif automatisable (le code ne rend jamais de cause pour un désactivé) : elle garde la garde-fou côté box.
- **AC13 (mesure Node, fixture 40 pièces / 292 équipements fictifs dont 21 exclus)** : `computeOverview` complet 0,94 ms ; `resolveEquipmentState` seul sur les 292 : 0,25 ms ; surcoût de `exclusionCauseOf` (appelé une fois par équipement « Exclu », seulement) : 0,06 ms ; ventilation des 40 pièces : 0,01 ms. Aucun seuil inventé.
- **AC12** : `git diff --stat origin/main...HEAD -- resources/daemon core plugin_info tests/e2e/gate/lib scripts` vide ; seul `desktop/php/` modifié : ajout de la donnée de Q1 (+47 lignes, aucune suppression) ; aucun champ ajouté à la liste blanche de `getEquipmentStates`.
- **Tests existants adaptés PAR AJOUT (AC11)** : `test_story_25_3_page_b` (champs de `j2haRoomsTree` : + `eq_type`, + `j2haPluginNames`) ; `test_story_25_4_recherche_filtres` (la comparaison des repères carte / arbre ignore aussi « N exclus ») ; `test_story_25_4_css_collision`, `…_palette_theme` (une entrée autorisée en plus, voir CSS) ; `test_story_25_4_glossaire` (+ « Exclus ») ; `test_story_25_6_documentation` (retrouve son entrée de changelog par son titre) ; `tests/unit/helpers/render_page.php` (faux plugin à nom lu dans la fixture), `ui_harness.js`, `workview_harness.js`, `workview_browser.js` (`pluginNames`). Aucune assertion retirée.
- **Tâches sautées** : Task 0 (pre-flight, relevé des exclus par cause sur la box) et Task 6 (preuve terrain, vérification des « par la pièce » sur la box, passage à `ready-for-UX-validation`) sont réservées à ClaudeBox (CC-48). Statut courant `review`.

### File List

- `desktop/js/jeedom2ha_mapping_override.js` (ajouts), `desktop/js/jeedom2ha_overview.js`, `desktop/js/jeedom2ha_workview.js`, `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/css/jeedom2ha.css` (modifiés)
- `desktop/php/jeedom2ha.php`, `desktop/php/jeedom2ha_overview_helpers.php` (modifiés)
- `docs/fr_FR/index.md`, `docs/fr_FR/compteurs.md`, `docs/fr_FR/changelog_beta.md` (modifiés)
- `tests/e2e/gate/parcours/vue-maitre-detail-c.mjs` (modifié)
- `tests/unit/helpers/render_page.php`, `ui_harness.js`, `workview_harness.js`, `workview_browser.js` (modifiés)
- `tests/unit/test_story_25_3_page_b.node.test.js`, `test_story_25_4_recherche_filtres`, `…_css_collision`, `…_palette_theme`, `…_glossaire`, `test_story_25_6_documentation` (modifiés)
- `tests/unit/test_story_25_7_cause_exclusion.node.test.js`, `…_ventilation…`, `…_detail_equipement…`, `…_gate…`, `…_documentation…`, `test_story_25_7_php_plugin_names.php` (nouveaux)
- `_bmad-output/implementation-artifacts/25-7-cause-exclusion-affichee.md`, `sprint-status.yaml` (statuts, Dev Agent Record)

## Décisions (ClaudeBox, 2026-10-19 17:40)

Story relue. Les recommandations sont retenues pour Q1 à Q7 :
- **Q1** : le nom du plugin vient de la page. On ajoute un `eq_type` dans `j2haRoomsTree` et une table des noms de plugins lue dans Jeedom, côté PHP. Aucune modification du démon ni de la liste blanche. La table sert aussi à 25.9.
- **Q2** : mention courte après « Exclu » (« par le plugin X », « par la pièce », « individuelle »), phrase complète dans le détail.
- **Q3** : `excluded_eqlogic` s'affiche « individuelle », précisé « réglage de l'équipement dans Jeedom ».
- **Q4** : le détail dit où agir, en texte, avec un lien vers la configuration pour le plugin. Pour la pièce, le lien renvoie au contrôle de 25.8 une fois celui-ci livré. Aucune écriture dans cette story.
- **Q5** : repère gris « N exclus » sur la carte, avec la ventilation en infobulle et dans le nom accessible.
- **Q6** : « N autre » pour une cause indéterminable.
- **Q7** : infobulle des cellules inchangée, `REASON_LABELS` n'est pas modifié.

**Statut : `ready-for-dev`.**

## Questions ouvertes pour ClaudeBox / Alexandre

Chaque question porte une **recommandation argumentée** ; **aucune n'est tranchée par la session**.

**Q1 — D'où vient le nom du plugin X ? (vérifié : il n'est pas disponible côté interface aujourd'hui).**
Ni l'entrée agrégée, ni l'arbre unitaire, ni `j2haRoomsTree` ne portent le type de l'équipement ; le démon le reçoit (`eq_type`) mais ne le renvoie pas.
- A. **Ajout additif côté page** (`desktop/php/jeedom2ha.php`) : un champ `eq_type` (identifiant technique, `getEqType_name()`) par équipement dans `j2haRoomsTree`, et une table `j2haPluginNames` `{ identifiant: nom affiché }` construite une fois depuis l'API du cœur pour les seuls plugins présents ; repli sur l'identifiant. *(recommandé : donnée lue dans Jeedom par la page, comme `enabled` ; aucune modification du démon ni de la liste blanche, donc conforme à « interface seule » ; coût de quelques octets par équipement dans la page, rien dans la route ; la même table servira à la liste à cocher de 25.9.)*
- B. Ajouter le type à la liste blanche de la route agrégée : contredit « aucune modification du démon ni de la liste blanche » et grossit une réponse déjà à 89 % de son budget (1 342 346 octets).
- C. Pas de nom : « par son plugin » seulement. Zéro donnée nouvelle, mais l'utilisateur doit encore chercher lequel — c'est précisément ce que le point 3 d'Alexandre demande de lire.

**Q2 — Formulation : mention courte et phrase du détail.**
- A. **Mentions « par le plugin X », « par la pièce », « individuelle »** après le mot « Exclu » ; phrases complètes de D1 dans le détail. *(recommandé : reprend mot pour mot les trois formes du sprint change ; « individuelle » s'accorde avec « exclusion », sous-entendu dans la mention ; le détail lève l'ambiguïté en nommant le réglage.)*
- B. « Exclu par le plugin X » comme libellé unique : allonge chaque ligne et ressemble à un nouvel état (contre la décision « pas de 7ᵉ état »).
- C. Icône seule avec infobulle : illisible au doigt sur l'iPad mural, contraire à « jamais par la seule couleur ou la seule icône ».

**Q3 — `excluded_eqlogic` (clé `jeedom2ha_excluded` posée dans Jeedom, sans écrivain dans le plugin).**
- A. **« individuelle »**, avec la phrase « réglage de l'équipement dans Jeedom » dans le détail. *(recommandé : c'est une exclusion propre à l'équipement ; la phrase dit qu'elle ne se retire pas par « Automatique », ce que la documentation dit déjà.)*
- B. Une 4ᵉ mention (« par Jeedom ») : plus précise, mais hors des trois formes décidées.

**Q4 — Dire où agir dans le détail.**
- A. **Texte seul** (« configuration du plugin », « contrôle Automatique / Toujours / Jamais », « l'équipement, dans Jeedom »), plus un lien vers la page de configuration du plugin pour `excluded_plugin` et `excluded_object` ; aucune écriture. *(recommandé : utile tout de suite, sans écriture ; 25.8 remplacera le renvoi pour la pièce par le contrôle sur la carte et le détail de pièce, 25.9 retirera la pièce de la configuration.)*
- B. Aucune indication d'action : la cause suffit ; l'utilisateur cherche encore où agir.

**Q5 — Carte : repère « N exclus » ou rien.**
- A. **Repère gris « N exclus »** (seulement si N > 0), ventilation dans le nom accessible et l'infobulle. *(recommandé : la cause est demandée « sur la carte » ; un seul repère court garde la carte lisible ; la ventilation complète est au détail de pièce.)*
- B. Ventilation complète visible sur la carte : précis, mais surcharge une carte déjà porteuse d'une jauge, d'un ratio et de trois repères possibles.
- C. Rien sur la carte avant 25.8 : contraire au point 3 du sprint change.

**Q6 — Ventilation quand des causes manquent (équipement « Exclu » sans cause déterminable, D1 point 3).**
- A. **Afficher « N autre »** dans la ventilation quand l'écart est non nul. *(recommandé : la somme reste vraie et visible ; aucune cause n'est inventée.)*
- B. Omettre l'écart : la ventilation semble incomplète sans le dire.

**Q7 — Infobulle des cellules « Exclue » du tableau des commandes (texte technique actuel « Exclue → exclu manuellement (commande) »).**
- A. **Inchangée dans cette story** (`REASON_LABELS` n'est pas modifié, AC1). *(recommandé : périmètre minimal ; la cause d'équipement est dans l'encart, la cellule garde son diagnostic technique ; un alignement éventuel relève de la recette 25.5.)*
- B. La réaligner sur les mentions de D1 : modifie une table partagée par d'autres écrans et d'autres tests.

## Change Log

- 2026-10-19 — Création (`create-story`, session cloud déléguée) depuis le sprint change du 19/10 (point 3) : statut `backlog`, 14 AC, 10 décisions déjà arbitrées, 7 questions ouvertes avec recommandation ; constat consigné : le nom du plugin n'est pas disponible côté interface (Q1) ; `ready-for-dev` non accordé ; statut cible `ready-for-UX-validation` (validation UX finale en 25.5).
- 2026-10-19 17:40 — Relecture ClaudeBox : recommandations retenues (§ Décisions) ; `ready-for-dev`.
- 2026-10-19 — dev-story (session cloud déléguée, après 25.6) : Tasks 1 à 5 faites, Tasks 0 et 6 sautées (CC-48) ; statut `review` ; preuve terrain et `ready-for-UX-validation` à ClaudeBox.
