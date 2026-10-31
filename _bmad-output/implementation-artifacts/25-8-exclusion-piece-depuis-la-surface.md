# Story 25.8 : Exclusion de pièce depuis la surface

Status: done

> **Statut : `review` (dev-story terminé, session cloud déléguée, 2026-10-19 ; Tasks 0 et 7 sautées, CC-48 : déploiement et preuve terrain à ClaudeBox après fusion, avec la pièce de test choisie avec Alexandre).** Précédemment : **`ready-for-dev` (2026-10-19 17:40, relecture et décisions ClaudeBox ; Alexandre présent, peut revenir sur une décision).** Précédemment : **`backlog` (2026-10-19).** Story rédigée par une session cloud déléguée (`create-story`, documentaire : aucun code, aucun test, aucune fixture, aucun accès box / VM / Home Assistant / SSH / secret, CC-48), à partir du sprint change `sprint-change-proposal-2026-10-19-revue-ux-25.md` (statut **decided**, décisions **D1** et **D3**, avis de clawcode « A1 / `excludedObjects` »). **`ready-for-dev` n'est pas accordé** : relecture de la story par ClaudeBox, puis décisions sur Q1 à Q10 (§ Questions ouvertes, chacune avec une recommandation argumentée ; la session n'en tranche aucune). **Statut cible après implémentation et preuve terrain : `ready-for-UX-validation`** ; validation UX finale en **25.5**. Les points de § Décisions déjà arbitrées sont **fermés**. Pointeurs de code pris sur `main` à `731be8d` ; **à re-vérifier au SHA courant** (après 25.6 et 25.7) avant le `dev-story`. Aucun nom réel d'équipement, de pièce, d'objet, de scénario ou de personne ; identifiants fictifs dans les fixtures, identifiants techniques seuls dans la preuve terrain (CC-48).

## Story

En tant que propriétaire qui règle ce que Home Assistant voit de sa maison,
je veux exclure (ou ne plus exclure) une pièce entière **depuis sa carte** sur la page principale et **depuis le détail de la pièce** dans la vue de travail, avec une confirmation qui m'annonce combien d'entités vont quitter Home Assistant,
afin de régler mes exclusions là où je les vois, sans saisir d'identifiants dans la page de configuration.

**Parcours : interface (`desktop/`), une route ajax PHP dédiée (`core/ajax/` + fonction pure sous `core/php/`), gate 20-0 (`policy.mjs` + simulation), docs, tests Node et PHP.** Le démon n'est pas modifié pour la logique d'exclusion (D1) ; la seule exception envisagée est l'éventuel champ de liste blanche de la **Q1** (décompte exact des entités), soumise à décision.

**Dépendances :** 25.7 (cause « par la pièce », fonction `exclusionCauseOf`, repère « N exclus ») ; 25.6 (portée de la vue C) ; même fichiers JS, branche partant de 25.7 fusionnée. Ordre décidé : 25.6 → 25.7 → **25.8** → 25.9 → 25.5. **25.9 dépend de 25.8** : le champ « Pièces exclues » de la configuration n'est retiré qu'une fois ce contrôle livré (voir Q9 sur la fenêtre entre les deux).

## Décisions déjà arbitrées

1. **Mécanisme A1, clé `excludedObjects` seulement.** Pas de nouveau mécanisme, pas de migration : les pièces déjà présentes dans `excludedObjects` sont reprises telles quelles, **sans perte**. A2 (« Jamais ») et A3 (`publishedScope*`) ne sont pas utilisés pour la pièce. (Sprint change, § Analyse, avis de clawcode.)
2. **Nouvelle route ajax PHP dédiée** qui **lit, modifie puis écrit uniquement** la clé `excludedObjects` (jamais `excludedPlugins`, `confidencePolicy` ni aucune autre clé), **suivie d'une relecture explicite** (`scanTopology`). (Sprint change, découpage 25.8.)
3. **D3 — Effet immédiat** : une confirmation **chiffrée** « N entités seront retirées de Home Assistant », puis l'enregistrement et la relecture ; **pas d'état « À appliquer »** pour une exclusion de pièce. (Décision d'Alexandre, 19/10 13:50.)
4. **Aucune purge implicite** : rien n'est retiré de Home Assistant sans la confirmation chiffrée ; l'enregistrement et la relecture sont deux opérations **explicites**, dans cet ordre. (Point repris de clawcode.)
5. **D1 — Une pièce exclue prime sur « Toujours »** : un équipement réglé « Toujours » dans une pièce exclue n'est pas publié et « Toujours » reste grisé ; c'est le comportement actuel (l'éligibilité passe avant le réglage de publication) ; **aucun changement du démon** pour cela. (Décision d'Alexandre.)
6. **Contrôles** : sur la **carte B** (sans ouvrir la pièce : arrêt de propagation du clic et des touches) et dans le **détail de pièce C**. (Sprint change, point 5.)
7. **`excluded` ajouté à `j2haRoomsTree`** (champ additif par pièce) ; la carte affiche **« Pièce exclue »** au lieu de « 0 / X publiés ». (Sprint change, point 1.)
8. **« Sans pièce » (`object_id = 0`) n'est pas excluable** : aucun contrôle, et la route refuse `0`. (Sprint change.)
9. **Gate 20-0** : la route est déclarée dans `tests/e2e/gate/lib/policy.mjs` comme **écriture simulée** ; les autres actions de la politique sont **inchangées** ; aucune assertion retirée (registres de 25.4 et suivants comme plancher). (Sprint change.)
10. **Idempotence** de l'écriture, de la relecture et de la synchro après modification d'`excludedObjects` ; **inventaire Home Assistant avant / après** et preuve terrain par **ClaudeBox**. (Sprint change.)
11. **Exclusion de la pièce elle-même, sans cascade** : le plugin exclut les équipements dont **l'objet propre** est dans `excludedObjects` (`core/class/jeedom2ha.class.php:848`), pas ceux des sous-pièces ; cette sémantique ne change pas (documentée dans `index.md:100`).
12. **Vocabulaire, palette, thème** de 25.1 ; rouge réservé au bouton de confirmation d'une action qui retire de Home Assistant ; CSS préfixé, aucun sélecteur nu sur une classe partagée (leçon #296).
13. **Statut cible : `ready-for-UX-validation`**, validation UX finale en 25.5.

## Sources lues

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-19-revue-ux-25.md` (tout) ; `epic-25-draft.md` ; `epics-projection-engine.md` § Epic 25 ; `sprint-status.yaml`.
- `25-2-route-agregee-cote-demon.md` (liste blanche, budget 1 500 000 octets, vigilance Q8 1 350 000) ; `25-3-page-principale-b.md` (cartes, lecteur, `notifyStatesChanged`) ; `25-4-vue-maitre-detail-c.md` (AC8 contrat d'écriture, AC14 détail de pièce, AC27 gate) et sa preuve terrain (1 342 346 octets) ; `25-6-…`, `25-7-…`.
- Code (lecture seule, `main` `731be8d`) : `core/ajax/jeedom2ha.ajax.php` (`saveFilteringConfig` `:813-828`, `scanTopology` `:652`) ; `core/class/jeedom2ha.class.php` (lecture et filtrage `excludedObjects` `:764-766`, priorité `:841-851`) ; `core/php/` (fonctions pures : `jeedom2ha_action_budget.php`, `jeedom2ha_homekit_exposure.php`) ; `plugin_info/configuration.php` (`:115-133`, `:289-330`) ; `desktop/php/jeedom2ha.php` (`j2haRoomsTree` `:18-75`) ; `desktop/php/jeedom2ha_overview_helpers.php` (`j2ha_render_room_card` `:161`) ; `desktop/js/jeedom2ha_overview.js` (`renderCards` `:388`, clavier des cartes `:569-575`) ; `desktop/js/jeedom2ha.js` (`triggerTopologyRescan` `:355`, réservation `jeedom2haRescanInProgress` `:451-462`, confirmation `confirmTopologyRescan`) ; `desktop/js/jeedom2ha_mapping_surface.js` (`buildMenu` `:791`, `buildRoomActions` `:890`, entrées rouges dans le menu `:928`, `buildEquipmentExcludeContent` `:491`) ; `desktop/js/jeedom2ha_mapping_override.js` (`publicationActionState`, cas inéligible `:198-205`, `entitiesLeavingHomeAssistant` `:304`) ; `resources/daemon/transport/http_server.py` (purge des équipements devenus inéligibles à la synchro `:2025-2040`, `_project_equipment_state` `:3370`, `present_in_ha` par entité dans l'arbre unitaire `:3230`) ; `tests/e2e/gate/lib/policy.mjs`, `lib/interceptor.mjs` (`:289-307`, branche `else` = retour), `lib/simulate.mjs`, `run-gate.mjs` (`:430`) ; `docs/fr_FR/index.md` (`:95-107`, `:160-168`, `:485-495`).

## Contexte et périmètre

### Ce qui existe aujourd'hui (relevé sur `731be8d`)

- `excludedObjects` est une chaîne CSV d'identifiants d'objets Jeedom, saisie en texte libre dans la page de configuration et écrite par `saveFilteringConfig` (avec `excludedPlugins` et `confidencePolicy`, en une fois). Le plugin la lit à chaque extraction de topologie (`trim`, `is_numeric`, `intval`, dédoublonnage) ; un équipement dont l'objet propre y figure est envoyé au démon avec `is_excluded: true`, `exclusion_source: 'object'` (priorité 3, après équipement et plugin).
- À la synchro suivante (`scanTopology` → `/action/sync`), le démon **retire de Home Assistant** les équipements devenus inéligibles (`cleanup_reason = "exclu (excluded_object)"`) et ne les republie plus. « Relire Jeedom » **applique aussi d'un coup tous les réglages en attente** de la maison (`index.md:164`).
- Sur la box : **deux pièces** sont déjà dans `excludedObjects` (sprint change) ; elles doivent être reprises sans perte.
- La route agrégée ne porte, par entité, que `override_pending` ; la présence réelle d'une entité dans Home Assistant (`present_in_ha`) est dans l'arbre unitaire seulement. Les commandes portent `published_in_ha`. → **Q1** (décompte « N entités »).

### Dans le périmètre

- fonction pure de lecture / modification de `excludedObjects` et route ajax dédiée (AC1 à AC4) ;
- donnée `excluded` dans `j2haRoomsTree` et état en mémoire après écriture (AC5) ;
- contrôles sur la carte B et dans le détail de pièce C, confirmation chiffrée, enchaînement écriture → relecture, échecs (AC6 à AC11) ;
- carte « Pièce exclue », D1 dans le détail d'équipement (AC12, AC13) ;
- gate 20-0 : politique, simulation, parcours (AC14, AC15) ;
- idempotence, reprise sans perte, preuve terrain avec inventaire HA (AC16, AC17) ;
- documentation, non-régression, conventions, statut (AC18 à AC21).

### Hors périmètre (ne pas faire ici)

- toute modification de la logique d'éligibilité ou de décision (`core/class/` hors lecture, `resources/daemon/models/`, `mapping/`, `sync/`, artefacts figés) ; D1 ne change aucune priorité ;
- la page de configuration (retrait du champ « Pièces exclues », liste à cocher des plugins, `saveFilteringConfig`) : **25.9** ;
- une exclusion en cascade des sous-pièces ; une exclusion de plusieurs pièces à la fois ; un état « À appliquer » ; une purge sans relecture ;
- l'exclusion d'un équipement (déjà possible par « Jamais ») ; le mécanisme A3 ; la clé `jeedom2ha_excluded` ;
- la validation UX finale (25.5).

## Définitions normatives

### D1 — Lecture-modification-écriture de `excludedObjects`

Fonction pure PHP (nom indicatif `jeedom2ha_toggle_excluded_object(string $csv, int $objectId, bool $excluded): array`, fichier nouveau sous `core/php/`, sans dépendance au cœur Jeedom) :

- découpe `$csv` sur `,`, `trim` de chaque jeton, jetons vides ignorés ;
- **exclure** : si un jeton numérique égal à `$objectId` existe déjà → `changed: false`, chaîne inchangée ; sinon ajoute `(string) $objectId` **en fin** ;
- **ne plus exclure** : retire **tous** les jetons numériques égaux à `$objectId` ; aucun → `changed: false` ;
- **tous les autres jetons sont conservés, dans leur ordre**, y compris les identifiants d'objets disparus et les jetons non numériques (Q5) ;
- rend `{ csv: <nouvelle chaîne, jetons joints par ','>, changed: bool, ids: <entiers retenus par la même règle que core/class:765-766> }`.

Un test table-driven prouve que `ids` est **identique** à l'ensemble calculé par `core/class/jeedom2ha.class.php:765-766` pour tout `$csv` de la table (même interprétation que l'extraction : aucune divergence possible entre ce que la surface affiche et ce que le plugin exclut).

### D2 — Route `saveRoomExclusion` (nom indicatif, Q2)

`POST core/ajax/jeedom2ha.ajax.php`, `action=saveRoomExclusion`, `objectId=<entier>`, `excluded=1|0`. Accès administrateur comme les autres actions.
- `objectId` doit être un entier strictement positif désignant un objet Jeedom existant ; `0`, négatif, non numérique, inconnu → `ajax::error` sans écriture.
- `excluded` vaut exactement `'1'` ou `'0'` ; toute autre valeur → `ajax::error` sans écriture.
- Lit `config::byKey('excludedObjects', 'jeedom2ha', '')`, applique D1, **n'appelle `config::save` que si `changed`**, et seulement sur la clé `excludedObjects`.
- Journalise une ligne `info` (`[CONFIG] saveRoomExclusion: objectId=<id> excluded=<0|1> changed=<0|1>`), sans la chaîne complète.
- Réponse : `{ object_id, excluded, changed, excluded_objects: [ids] }`.
- **Ne déclenche pas** la relecture : le client l'enchaîne explicitement (décision 2).

### D3 — Enchaînement côté interface

1. **Contrôle** (carte ou détail de pièce) → **confirmation** (D4). Annuler n'écrit rien.
2. Confirmer → `saveRoomExclusion`. Échec → message, **aucune relecture**, aucun état changé.
3. Succès → mise à jour en mémoire du drapeau `excluded` des pièces depuis `excluded_objects` (aucun rechargement de page) → **relecture explicite** par le même chemin que « Relire Jeedom » (`scanTopology`, même réservation `jeedom2haRescanInProgress`, même budget client, mêmes messages de résultat), **sans** sa confirmation propre (la confirmation chiffrée l'a annoncée, Q6).
4. Fin de la relecture (succès ou échec) → `refreshBridgeStatus()` et `notifyStatesChanged()` (relecture des états par le lecteur de 25.3, une requête, sans `refresh`).
5. Pendant 2 à 4, les contrôles d'exclusion de toutes les pièces, « Relire Jeedom » et les boutons `data-ha-action` sont réservés (pas de double envoi).

### D4 — Confirmation chiffrée

- **Exclure** : titre « Exclure la pièce « Nom » de Home Assistant ? » ; corps « N entités seront retirées de Home Assistant. » (N selon Q1 ; « 1 entité sera retirée… », « Aucune entité n'est publiée dans cette pièce. » pour 0) ; si la maison a des réglages en attente, une phrase chiffrée « La relecture appliquera aussi les M réglages en attente de la maison. » (Q6) ; boutons « Annuler » et **« Exclure la pièce »** (rouge, `btn-danger`).
- **Ne plus exclure** : « Ne plus exclure la pièce « Nom » ? Ses équipements seront relus et publiés s'ils sont publiables. » (+ phrase des réglages en attente) ; boutons « Annuler » et « Ne plus exclure » (bouton principal, pas rouge : rien n'est retiré) (Q7).
- Si une lecture des états n'est pas disponible (25.3 D2 : `available:false`, erreur, en cours), le nombre ne peut pas être calculé : la confirmation le dit (« Nombre d'entités inconnu : la lecture des états n'est pas disponible. ») et reste possible (Q8).

## Acceptance Criteria

### A. Écriture

**AC1 — Fonction pure D1**
**Given** une table de fixtures CSV fictives (vide, `"5"`, `"5,12"`, `" 5 , 12 "`, `"5,,12"`, `"12,5,5"`, `"abc,5"`, `"7,5,999999"`, `"-3,5"`, `"5.0,5"`)
**When** `tests/test_php_story_25_8_exclusion_piece.php` applique exclure / ne plus exclure à des identifiants présents et absents
**Then** les sorties sont exactement celles de D1 (ajout en fin, retrait de toutes les occurrences, autres jetons conservés dans l'ordre, `changed` exact) ; `ids` égale l'ensemble calculé par la règle de `core/class/jeedom2ha.class.php:765-766` sur la même entrée (test d'équivalence) ; appliquer deux fois la même opération donne `changed:false` la seconde fois et la même chaîne.

**AC2 — Route : seule la clé `excludedObjects`**
**Given** une configuration fictive avec `excludedPlugins`, `excludedObjects`, `confidencePolicy` et d'autres clés du plugin
**When** la route est appelée (exclure, ne plus exclure, rejouer)
**Then** seule `excludedObjects` peut être écrite ; un espion sur `config::save` prouve qu'aucune autre clé n'est écrite et qu'**aucune** écriture n'a lieu quand `changed` est faux ; les valeurs des autres clés sont identiques avant / après (test PHP)
**And** `git diff main...HEAD -- core/ajax/jeedom2ha.ajax.php` ne montre qu'un **ajout** (branche `saveRoomExclusion`) : `saveFilteringConfig` et les autres actions sont inchangées dans cette story.

**AC3 — Route : validation et refus**
**Given** les entrées hostiles fictives `objectId ∈ {0, -1, '', 'abc', '1e3', '12;5', objet inconnu}` et `excluded ∈ {'', '2', 'true', 'oui'}`
**When** la route est appelée
**Then** chaque appel répond par une erreur, sans écriture ni ligne de journal contenant l'entrée brute ; la route ne lance jamais `scanTopology` ni aucun appel au démon.

**AC4 — Route sans relecture implicite**
**Given** la route
**When** on lit son code et son test
**Then** elle n'appelle ni le démon, ni `scanTopology`, ni aucune purge ; l'effet sur Home Assistant ne vient **que** de la relecture explicite de D3 (test : aucun appel au relais du démon pendant la route).

### B. Données et contrôles

**AC5 — `excluded` dans `j2haRoomsTree`**
**Given** `excludedObjects` fictif `"5,12"`
**When** la page est rendue
**Then** chaque pièce de `j2haRoomsTree` porte `excluded: true|false` (vrai si son `object_id` est dans `ids` de D1), `false` pour « Sans pièce » ; aucun autre champ n'est renommé ni retypé (`test_story_25_3_php_hierarchie.php` vert, test PHP nouveau pour `excluded`)
**And** après une écriture réussie, le drapeau en mémoire est mis à jour depuis `excluded_objects` de la réponse, pour **toutes** les pièces (une écriture concurrente d'un autre onglet est ainsi reflétée), sans rechargement de la page.

**AC6 — Contrôle sur la carte B, sans ouvrir la pièce**
**Given** la page principale
**When** l'utilisateur ouvre le menu « ⋯ » d'une carte (Q3) puis choisit « Exclure la pièce… » (ou « Ne plus exclure la pièce… » si elle est exclue), à la souris, au doigt ou au clavier (Entrée / Espace sur le bouton du menu)
**Then** la vue C **ne s'ouvre pas** : le clic, `keydown` et `keyup` du bouton et des entrées du menu sont arrêtés (`stopPropagation`) avant l'`onclick` de la carte et l'écouteur clavier de `jeedom2ha_overview.js` ; le fragment d'URL est inchangé ; aucun `j2haOpenRoom` n'est appelé (test `test_story_25_8_carte_menu.node.test.js`, et test en vrai Chromium)
**And** la carte de « Sans pièce » n'a **pas** de menu ; les cartes conservent `objectDisplayCard`, `.j2ha-room-card`, `data-object_id`, `onclick="j2haOpenRoom(…)"` ; le menu réutilise le composant `.j2ha-menu-*` de 25.1 **sans en modifier les règles**.

**AC7 — Contrôle dans le détail de pièce C**
**Given** une pièce sélectionnée dans la vue C (portée `piece` ou `toutes`)
**When** le détail est rendu
**Then** le menu « ⋯ » de la pièce (`buildRoomActions`) contient « Exclure la pièce… » (ou « Ne plus exclure la pièce… ») **avant** le séparateur et « Supprimer de Home Assistant… » ; une pièce exclue affiche sous son titre un encart neutre « Pièce exclue : ses équipements ne sont pas publiés dans Home Assistant. » avec le bouton « Ne plus exclure la pièce… » ; « Sans pièce » n'a ni l'entrée ni l'encart.

**AC8 — Confirmation chiffrée (D4)**
**Given** une fixture fictive où la pièce `P` a des équipements publiés, à appliquer, bloqués, exclus individuellement, désactivés et non lus
**When** l'utilisateur demande l'exclusion de `P`
**Then** la confirmation affiche N calculé **par une fonction pure unique** selon Q1 depuis la copie des états en mémoire (aucune requête : espion ajax à zéro jusqu'au clic sur « Exclure la pièce »), avec les pluriels accordés par le code ; la phrase des réglages en attente apparaît si et seulement si l'effectif maison « à appliquer » est non nul (Q6) ; le bouton de confirmation est rouge (`btn-danger`) et seul le clic sur lui écrit
**And** Annuler, la croix, Échap ferment sans écrire (0 `saveRoomExclusion`, 0 `scanTopology`) et libèrent les réservations ; le focus revient au bouton déclencheur.

**AC9 — Enchaînement écriture → relecture (D3)**
**Given** une confirmation acceptée
**When** l'enchaînement s'exécute
**Then** l'ordre des requêtes est exactement : `saveRoomExclusion` (une), puis `scanTopology` (une), puis `getEquipmentStates` (une, sans `refresh`, par le lecteur de 25.3) ; aucune autre écriture (test de séquence sur l'espion ajax `test_story_25_8_enchainement.node.test.js`)
**And** les corps de `scanTopology` et de `getEquipmentStates` sont **identiques** à ceux de « Relire Jeedom » et du lecteur (contrat de 25.4 AC8 étendu, fixture de référence capturée avant changement) ; le résultat de la relecture s'affiche avec les messages existants de « Relire Jeedom ».

**AC10 — Échecs**
**Given** chacun des cas : erreur de la route ; échec réseau de la route ; relecture refusée (« opération déjà en cours ») ; relecture en échec ; délai client dépassé
**When** l'enchaînement s'exécute
**Then** une erreur de la route n'entraîne **aucune** relecture et ne change aucun drapeau ; un échec de la relecture laisse l'exclusion **enregistrée** (drapeau à jour, carte « Pièce exclue ») et affiche le message de « Relire Jeedom » ainsi que l'invitation « Relancez « Relire Jeedom » pour retirer les entités. » ; dans tous les cas les réservations sont libérées et `notifyStatesChanged()` est appelé après la relecture tentée.

**AC11 — Réservation et disponibilité**
**Given** une relecture ou une action Home Assistant en cours, ou le gating de la barre de santé qui interdit les actions (démon arrêté, MQTT déconnecté)
**When** la page est rendue
**Then** les entrées d'exclusion sont grisées avec une infobulle (« Une opération est déjà en cours. » / la raison du gating existante), comme « Relire Jeedom » ; elles redeviennent actives à la fin.

### C. Affichage

**AC12 — Carte « Pièce exclue »**
**Given** une pièce dont `excluded` est vrai
**When** la carte est rendue
**Then** la ligne « n / t publiés » est remplacée par « Pièce exclue » (gris, icône `fa-eye-slash`, mot visible, pas seulement la couleur) ; le reste suit Q4 (par défaut : jauge et repères conservés, repère « N exclus » de 25.7 compris) ; le nom accessible de la carte commence par « Nom, pièce exclue »
**And** si des équipements de la pièce ne sont pas encore exclus dans la copie des états (relecture pas encore faite ou échouée), la carte ajoute la mention « N pas encore retirés » (Q4) ; la mention disparaît d'elle-même à la relecture suivante ; la ligne de la pièce dans l'arbre C porte la même mention « Pièce exclue » à la place du ratio.

**AC13 — D1 dans le détail d'équipement**
**Given** un équipement d'une pièce exclue, réglé « Toujours » ou « Automatique »
**When** son détail est rendu
**Then** il est « Exclu » avec la cause « par la pièce » (25.7) ; « Toujours » et « Jamais » sont grisés comme aujourd'hui ; l'infobulle du segment grisé dit « Pièce exclue : elle prime sur ce réglage. » (Q10), calculée **dans la surface** à partir de la cause, **sans modifier** `publicationActionState` ; un réglage « Toujours » déjà posé reste affiché comme position courante (aucune écriture, aucun changement du démon).

### D. Gate 20-0

**AC14 — Politique : une écriture simulée de plus, rien d'autre**
**Given** `tests/e2e/gate/lib/policy.mjs`
**When** la route est déclarée
**Then** `classifyRequest` rend `simulate` / `exclusion-piece-declaree` pour un `POST` `saveRoomExclusion` dont `objectId` et `excluded` correspondent exactement à une entrée `ctx.declaredRoomExclusions` (`{ [objectId]: { excluded: '1' | '0' } }`), et `block-fail` / `exclusion-piece-non-declaree` sinon (méthode autre que `POST`, objet non déclaré, valeur différente, paramètres dupliqués ou invalides) ; `ALLOWED_READS`, `SIDE_EFFECT_ACTIONS`, `OVERRIDE_WRITE_ACTIONS` et les verdicts existants sont **inchangés** (diff limité à l'ajout) ; `test_story_20_0_gate_policy` est **étendu** (cas positifs et négatifs) et reste vert
**And** `lib/interceptor.mjs` traite `saveRoomExclusion` par une branche **explicite** (jamais par la branche `else` actuelle, qui sert le retour d'un réglage) et `lib/simulate.mjs` fournit sa réponse simulée (forme de D2, `excluded_objects` simulés à partir de la configuration réelle lue par la page et de l'écriture déclarée) ; `run-gate.mjs` transmet `declaredRoomExclusions` (défaut `{}`) ; `interceptor-selftest.mjs` couvre la nouvelle branche.

**AC15 — Parcours `exclusion-piece-simulee`**
**Given** un parcours nouveau `tests/e2e/gate/parcours/exclusion-piece-simulee.mjs` qui déclare **une** pièce (identifiant technique choisi par ClaudeBox) et `declaredRescan = true`
**When** il s'exécute (simulé en CI, contre la box par ClaudeBox)
**Then** il prouve, avec des étiquettes d'erreur distinctes : (1) ouvrir le menu de la carte n'ouvre pas la vue C et n'émet aucune requête (`menu-carte-ouvre-la-piece`) ; (2) la confirmation affiche un nombre entier (`confirmation-sans-nombre`), enregistré par `record('entites_annoncees', N)` ; (3) Annuler n'émet aucune écriture (`ecriture-apres-annulation`) ; (4) Confirmer émet exactement `saveRoomExclusion` (simulée) puis `scanTopology` (simulée) puis une lecture `getEquipmentStates`, dans cet ordre, sans autre écriture (`sequence-exclusion-inattendue`) ; (5) la carte affiche « Pièce exclue » (`carte-non-marquee-exclue`) ; (6) le même scénario depuis le détail de pièce C (`detail-piece-exclusion-absente`) ; (7) la carte « Sans pièce », si elle existe, n'a pas de menu (`sans-piece-excluable`) ; (8) une écriture `saveRoomExclusion` sur une **autre** pièce, provoquée par le parcours, est **bloquée** par la politique (`exclusion-non-declaree-transmise`)
**And** le contrôle négatif `controle-ecriture-non-declaree` échoue toujours comme attendu ; les registres d'assertions existants restent des planchers ; **aucune écriture réelle** n'est transmise à la box par le gate.

### E. Idempotence, reprise, preuve terrain

**AC16 — Idempotence et reprise sans perte**
**Given** `excludedObjects` fictif contenant deux pièces existantes, un identifiant disparu et un jeton non numérique
**When** on exclut une troisième pièce, la ré-exclut, puis ne l'exclut plus
**Then** la chaîne finale est **identique** à la chaîne de départ (test PHP) ; les deux pièces initiales restent exclues à chaque étape ; la seconde exclusion répond `changed:false` sans `config::save`
**And** côté interface, rejouer l'enchaînement sur une pièce déjà exclue ne pose pas de nouvelle écriture (`changed:false`) mais **relance quand même** la relecture explicite (Q6 : la relecture est idempotente) ; ce comportement est consigné.

**AC17 — Preuve terrain avec inventaire HA (ClaudeBox)**
**Given** la story fusionnée et déployée (Task 0)
**When** ClaudeBox exécute la Task 7
**Then** la preuve consigne, en identifiants seuls : `excludedObjects` avant (les deux pièces déjà exclues présentes) ; inventaire Home Assistant **avant** (entités du plugin, par équipement de la pièce de test) ; nombre annoncé par la confirmation ; inventaire **après** la relecture (l'écart égale le nombre annoncé — ou, si Q1 ≠ B, l'écart est expliqué ligne à ligne) ; une **seconde relecture** sans changement (0 publication, 0 retrait : idempotence de la synchro) ; « Ne plus exclure » puis inventaire revenu à l'état initial ; `excludedObjects` final identique à l'initial ; 0 ligne `ERROR` dans le démon
**And** la pièce de test et le moment de l'écriture réelle sont choisis avec le GO d'Alexandre (Q9).

### F. Documentation, non-régression, conventions, statut

**AC18 — Documentation**
**Given** `docs/fr_FR/index.md`, `compteurs.md`, `changelog_beta.md`
**When** la story est livrée
**Then** `index.md` décrit l'exclusion de pièce depuis la carte et le détail de pièce, la confirmation chiffrée, l'enchaînement enregistrement → relecture (et le fait que la relecture applique aussi les réglages en attente), la carte « Pièce exclue », « Sans pièce » non excluable, l'absence de cascade aux sous-pièces, D1 (« la pièce prime sur « Toujours » ») ; § « Filtrage et publication » indique que le champ « Pièces exclues » de la configuration et la surface écrivent la même clé (jusqu'à 25.9) ; famille 7 « Exclusions volontaires » mise à jour ; `test_story_25_8_documentation.node.test.js` vérifie les libellés cités.

**AC19 — Aucune modification de la logique d'exclusion**
**Given** la branche de la story
**When** on exécute `git diff --stat main...HEAD -- resources/daemon/models/ resources/daemon/mapping/ resources/daemon/sync/ resources/daemon/discovery/ core/class/ plugin_info/`
**Then** la sortie est **vide** ; `git diff main...HEAD -- resources/daemon/` est vide **sauf** si Q1 = B (alors : ajout du seul champ `present_in_ha` à la projection de liste blanche, parité de 25.2 AC3 mise à jour, taille de réponse mesurée et consignée contre le seuil de vigilance de 1 350 000 octets) ; `tests/e2e/gate/lib/policy.mjs` ne change que par l'ajout de l'AC14.

**AC20 — Non-régression**
**Given** les suites `test_story_25_*`, `test_story_20_*`, `test_story_22_2_*`, `test_php_topology_extraction.php`, les tests PHP existants
**When** elles s'exécutent
**Then** elles passent ; `test_php_topology_extraction.php` prouve que l'extraction calcule toujours `exclusion_source: 'object'` pour une pièce ajoutée par la route (même clé, même lecture) ; tout test adapté l'est par ajout et est listé au Dev Agent Record.

**AC21 — Conventions et statut**
**Given** CLAUDE.md
**When** la PR de dev est ouverte
**Then** une PR = ce sujet ; titre Conventional Commits ; `make test`, `node --test tests/unit/*.node.test.js`, tests PHP, `flake8`, `scripts/ci-local.sh` verts ; identifiants fictifs, aucun nom réel, IP ni secret (CC-48) ; Tasks 0 et 7 sautées par une session cloud et la PR le dit
**And** après la preuve terrain (Task 7) le statut passe à **`ready-for-UX-validation`** ; il reste `backlog` jusqu'à `ready-for-dev`.

## Statut cible et validation UX

- **Statut actuel :** `backlog` ; `ready-for-dev` non accordé.
- **Chemin :** `backlog` → `ready-for-dev` (relecture ClaudeBox + Q1 à Q10) → `review` → `ready-for-UX-validation` (preuve terrain ClaudeBox avec inventaire HA) → `done` à la clôture de 25.5.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY) **[réservée à ClaudeBox ; SAUTÉE par cette session cloud (CC-48)]**
  - [ ] Dry-run `./scripts/deploy-to-box.sh --dry-run` ; déploiement `--sha <complet> --restart-daemon` depuis un worktree neuf ; `Deploy complete.` **(avec 25.9 dans le même déploiement : Q9)**
  - [ ] Relever `excludedObjects` (identifiants seuls) et l'inventaire HA de référence ; vérifier que les deux pièces déjà exclues s'affichent « Pièce exclue » sans aucune écriture.
- [x] Task 1 — Références avant changement (AC: 2, 9, 14)
  - [x] 1.1 Corps de référence de `scanTopology` et `getEquipmentStates` : le test d'enchaînement compare le corps de la relecture enchaînée à celui de « Relire Jeedom » dans le même harnais (url, type, corps, délai) ; registre d'assertions des parcours existants inchangé (planchers de 25.4 et suivants verts).
- [x] Task 2 — Tests d'abord (AC: 1 à 5, 8 à 10, 14, 16)
  - [x] 2.1 `tests/test_php_story_25_8_exclusion_piece.php` (D1, équivalence avec l'extraction, route, refus, idempotence, reprise sans perte) — rouge sans le module ni la branche ni `excluded`, vert après.
  - [x] 2.2 `test_story_25_8_carte_menu`, `…_confirmation` (fonction de N, pluriels, indisponibilité), `…_enchainement` (séquence, échecs), `…_affichage`, `…_gate`, `…_navigateur_reel`, `…_documentation`, extension de `test_story_20_0_gate_policy` et `…_simulate`, `resources/daemon/tests/unit/test_story_25_8_present_in_ha.py`.
- [x] Task 3 — Fonction pure et route (AC: 1 à 4)
  - [x] 3.1 `core/php/jeedom2ha_room_exclusion.php` + `require_once` DANS la branche `saveRoomExclusion` de l'ajax (le diff de l'ajax est un pur ajout).
- [x] Task 4 — Donnée et contrôles (AC: 5 à 11)
  - [x] 4.1 `excluded` dans `j2haRoomsTree` ; menu « ⋯ » de carte (arrêt de propagation) ; entrée et encart du détail de pièce.
  - [x] 4.2 Confirmation chiffrée (Q1, Q6, Q7, Q8) ; enchaînement D3 par le chemin de « Relire Jeedom » ; réservations ; échecs.
- [x] Task 5 — Affichage (AC: 12, 13)
  - [x] 5.1 Carte et ligne d'arbre « Pièce exclue », mention « N pas encore retirés » ; infobulle D1 dans la surface.
- [x] Task 6 — Gate, documentation, non-régression (AC: 14, 15, 18 à 21)
  - [x] 6.1 `policy.mjs`, `interceptor.mjs`, `simulate.mjs`, `run-gate.mjs`, `interceptor-selftest.mjs` ; parcours `exclusion-piece-simulee` (+ contrôle négatif `controle-exclusion-piece-non-declaree`) ; suites simulées en vrai Chromium.
  - [x] 6.2 Docs ; `git diff --stat` de l'AC19 ; suites complètes, `flake8`, `scripts/ci-local.sh`.
- [ ] Task 7 — Preuve terrain (après fusion) **[réservée à ClaudeBox ; SAUTÉE par cette session cloud (CC-48)]**
  - [ ] 7.1 Gate 20-0 contre la box, dont `exclusion-piece-simulee` (identifiant de la pièce de test à fixer dans `declaredRoomExclusions` et dans le parcours) ; contrôle négatif en échec attendu (`controle-ecriture-non-declaree` ET `controle-exclusion-piece-non-declaree`).
  - [ ] 7.2 Écriture réelle avec le GO d'Alexandre (Q9) : inventaire HA avant / après, seconde relecture idempotente, « Ne plus exclure », retour à l'état initial, `excludedObjects` final = initial ; **mesure de la taille de `getEquipmentStates` sur la box contre 1 350 000 / 1 500 000 octets** ; `25-8-preuve-terrain-<date>.md` (identifiants seuls).
  - [ ] 7.3 Statut `ready-for-UX-validation`.

## Dev Notes

### Dev Agent Guardrails

- **La route n'écrit que `excludedObjects`**, et seulement quand `changed` ; jamais `excludedPlugins`, `confidencePolicy`, `publishedScope*`, ni la configuration d'un équipement.
- **Jamais de relecture implicite côté serveur**, jamais de purge sans confirmation ; l'effet HA vient de la relecture explicite.
- **Ne jamais** modifier la logique d'éligibilité (`core/class/`), le démon (sauf Q1 = B, limité à la liste blanche), les artefacts figés ; ne pas modifier `saveFilteringConfig` ici (25.9).
- **Réutiliser** le chemin de relecture de « Relire Jeedom » (réservation, budget, messages) au lieu d'en écrire un second.
- **Arrêter la propagation** des événements du menu de carte ; ne jamais retirer `onclick="j2haOpenRoom(…)"` des cartes.
- **Politique du gate** : ajout seulement ; branche explicite dans l'intercepteur ; jamais transmettre une écriture réelle.
- Libellés via `{{…}}`, pluriels par le code, aucun terme interdit ; noms de pièce par `.text()` ; aucun nom réel (CC-48).
- Une session cloud saute les Tasks 0 et 7 et le dit dans la PR.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` ; jamais de rsync ou de copie SSH ad hoc. Référence : `jeedom2ha-test-context-jeedom-reel.md`. Cycle canonique `main → beta → stable → Jeedom Market`.
- L'écriture réelle de la Task 7 change ce que Home Assistant voit : elle se fait avec le GO d'Alexandre, et l'état initial est restauré et vérifié.

### Précédents réutilisables

- Fonctions pures PHP testables hors cœur : `core/php/jeedom2ha_action_budget.php`, `jeedom2ha_homekit_exposure.php` ; tests `tests/test_php_*.php`.
- Relecture : `triggerTopologyRescan` (`desktop/js/jeedom2ha.js:355`) et sa réservation.
- Menu « ⋯ » : `buildMenu` (25.1) ; entrées rouges dans le menu seulement.
- Confirmation d'exclusion chiffrée : `buildEquipmentExcludeContent` / `entitiesLeavingHomeAssistant` (« Jamais » d'équipement).
- Écriture simulée déclarée : `declaredPublicationOverrides` (20-2) et `declaredRescan` (20-4).

### Fichiers probablement touchés (pour le `dev-story`)

`core/php/jeedom2ha_room_exclusion.php` (**nouveau**, nom indicatif) ; `core/ajax/jeedom2ha.ajax.php` (ajout d'une branche) ; `desktop/php/jeedom2ha.php` (`excluded`) ; `desktop/php/jeedom2ha_overview_helpers.php` (menu de carte) ; `desktop/js/jeedom2ha_overview.js` (carte, menu, arrêt de propagation) ; `desktop/js/jeedom2ha_workview.js` (détail de pièce, ligne d'arbre) ; `desktop/js/jeedom2ha_mapping_surface.js` (`buildRoomActions`, infobulle D1) ; `desktop/js/jeedom2ha.js` (enchaînement, réutilisation de la relecture) ; `desktop/js/jeedom2ha_mapping_override.js` (ajouts purs : fonction de N) ; `desktop/css/jeedom2ha.css` ; `tests/e2e/gate/lib/{policy,interceptor,simulate}.mjs`, `run-gate.mjs`, `interceptor-selftest.mjs`, `parcours/exclusion-piece-simulee.mjs` ; `tests/test_php_story_25_8_*.php`, `tests/unit/test_story_25_8_*` ; docs. Si Q1 = B : `resources/daemon/transport/http_server.py` (`_project_equipment_state` seulement) et ses tests de 25.2.

### Definition of done

AC1 à AC21 tenus ; suites vertes ; PR relue par ClaudeBox ; preuve terrain avec inventaire HA (Task 7) ; statut `ready-for-UX-validation`.

### References

- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-19-revue-ux-25.md`#Analyse, #Décisions D1 D3, #Découpage]
- [Source: `core/class/jeedom2ha.class.php`:764-766, :841-851]
- [Source: `core/ajax/jeedom2ha.ajax.php`:813-828]
- [Source: `resources/daemon/transport/http_server.py`:2025-2040 (purge à la synchro)]
- [Source: `_bmad-output/implementation-artifacts/25-2-route-agregee-cote-demon.md`#Contrat final ; `25-4-preuve-terrain-2026-10-19.md`#Taille et temps]

## UI Impact

- **UI Impact:** Oui — menu « ⋯ » sur les cartes, entrée et encart dans le détail de pièce, confirmation chiffrée, carte « Pièce exclue ». Écriture de configuration et relecture explicites. Gate 20-0 obligatoire (AC14, AC15) ; preuve terrain avec inventaire HA ; statut cible `ready-for-UX-validation`.

## Dev Agent Record

### Agent Model Used

Claude (session cloud déléguée, branche `claude/epic-25-room-exclusion-plugins-i17h7v`, 2026-10-19), avec 25.9 dans la même PR (Q9 : déploiement conjoint) ; 25.6 et 25.7 fusionnées sur `main` au préalable.

### Debug Log References

- **Rouge avant vert** : le test PHP (`test_php_story_25_8_exclusion_piece.php`) a été écrit avant le module : sans `core/php/jeedom2ha_room_exclusion.php` il échoue à la première assertion ; sans la branche ajax ni `excluded` dans la page (`git stash` des deux fichiers) 11 assertions sont rouges. `test_story_25_2_route_agregee` / `test_story_25_8_present_in_ha` : 20 tests rouges avant l'ajout de `present_in_ha` à la liste blanche, verts après (fixture de parité régénérée). `test_story_25_8_confirmation` : 5 tests de page rouges avant le câblage (fonction pure : verte d'emblée, écrite avec elle). `…_enchainement` : 5 rouges au premier essai (objets d'un autre contexte `vm` comparés par `deepEqual`, double `refreshBridgeStatus` en fin de relecture → compteur d'appels ajouté), puis verts. `…_affichage` : 7 rouges avant le menu de détail, l'encart, la ligne d'arbre et l'infobulle D1. `test_story_20_0_gate_policy` / `…_simulate` : rouges avant `policy.mjs` / `simulate.mjs`.
- Les tests en vrai Chromium (`…_navigateur_reel`, `…_gate`) n'ont pas montré de défaut de propagation : l'arrêt de `keydown` est porté par le gestionnaire du menu (`onKey`) et celui du bouton, `keyup` et le `click` de la zone du menu par des gestionnaires ajoutés ; le faux DOM n'accepte qu'UN gestionnaire par événement et par élément (d'où `stop` intégré à `onKey` plutôt qu'un second écouteur).
- Tests de 25.x qui échouaient après l'ajout, adaptés PAR AJOUT (liste ci-dessous) ; aucune assertion retirée.
- `scripts/ci-local.sh` : voir la ligne « Résultat final » ci-dessous (relancé après les deux stories).

### Completion Notes List

- **D1 — fonction pure** : `jeedom2ha_toggle_excluded_object` / `jeedom2ha_excluded_object_ids` (`core/php/jeedom2ha_room_exclusion.php`, sans cœur Jeedom, compatibles PHP 7.4). Tous les autres jetons sont conservés dans leur ordre (identifiants disparus, jetons non numériques), les jetons vides ignorés, l'identifiant ajouté EN FIN, toutes les occurrences retirées ; `ids` est l'équivalent exact de `core/class/jeedom2ha.class.php:765-766` (test d'équivalence sur 14 chaînes, et test qui vérifie que ces deux lignes sont toujours celles de la classe).
- **D2 — route `saveRoomExclusion`** : `jeedom2ha_save_room_exclusion($objectId, $excluded, $objectExists, $readCsv, $saveCsv, $log)` (accès au cœur injecté) ; `objectId` = `^[1-9][0-9]{0,8}$` et objet Jeedom existant, `excluded` = exactement `'1'`/`'0'` ; n'écrit que si la chaîne change, et seulement la clé `excludedObjects` ; une ligne `info` sans la chaîne complète ; refus sans écriture, sans journal et sans citer l'entrée brute ; aucun appel au démon ni relecture (test de la branche ajax : ni `callDaemon`, ni `scanTopology`, ni autre clé). `require_once` placé DANS la branche : `git diff origin/main -- core/ajax/jeedom2ha.ajax.php` = un ajout (25.8) + le remplacement de `saveFilteringConfig` (25.9).
- **`excluded` dans `j2haRoomsTree`** (champ additif en fin de pièce, `false` pour « Sans pièce ») ; `normalizeRoom` le recopie ; la page principale en est la source unique et le remplace pour TOUTES les pièces depuis `excluded_objects` (`setExcludedObjects`) ; la vue de travail le recopie à chaque rendu et redessine le détail de pièce quand il change.
- **Q1 = B — `present_in_ha`** ajouté aux entités de la liste blanche de la route agrégée (`_project_equipment_state`, une ligne ; docstring de la route mise à jour ; parité de 25.2 et fixture régénérées) ; la règle de priorité (D1) n'est pas touchée. **Mesure de taille** (`pytest -m load resources/daemon/tests/unit/test_story_25_2_load.py -s`, 292 équipements fictifs, même machine, même graine) : **913 266 octets avant, 949 673 octets après (+36 407 o, +4,0 %)**, donc sous le seuil de vigilance de 1 350 000 et sous le budget de 1 500 000 sur la fixture synthétique ; le test d'AC15 de 25.2 imprime maintenant un avertissement au-delà de 1 350 000 (`VIGILANCE_BYTES`). **Projection pour la box** : la dernière mesure terrain est 1 342 346 octets (25.4, 99,4 % du seuil de vigilance) ; le surcoût est proportionnel au nombre d'entités (≈ 22 à 23 octets par entité) : **le seuil de vigilance sera très probablement dépassé sur la box** (il suffit de ~350 entités) sans approcher le budget de 1 500 000 tant que la box a moins de ~6 800 entités. Décision ClaudeBox (§ Décisions) : on garde le champ et la preuve terrain consigne le chiffre réel ; repli « N équipements (M commandes) » seulement si le budget est dépassé. À mesurer en Task 7.2.
- **D4 — confirmation chiffrée** : `Jeedom2haOverview.roomExclusionImpact` (UNE fonction pure : entités `present_in_ha === true` des équipements de la pièce depuis la copie en mémoire ; présence inconnue et équipements non lus signalés mais non comptés ; lecture indisponible, en cours ou copie périmée → « Nombre d'entités inconnu… » et l'action reste possible) et `roomExclusionDialog` (pluriels accordés par le code, phrase chiffrée des réglages en attente si et seulement si l'effectif maison « à appliquer » est non nul, bouton `btn-danger` pour « Exclure la pièce », `btn-primary` pour « Ne plus exclure » sans nombre). Aucune requête avant le clic de confirmation (espion ajax).
- **D3 — enchaînement** : `requestRoomExclusion` (`jeedom2ha.js`) : réservation immédiate (même drapeau `jeedom2haRescanInProgress`, même bouton « Relire Jeedom » en attente, `applyHAGating` grise toutes les entrées `data-ha-action`, dont l'exclusion des autres pièces, avec l'infobulle « Une opération est déjà en cours. » ou la raison du gating du pont) → confirmation → `saveRoomExclusion` (délai client 20 s) → échec : message, AUCUNE relecture, rien de changé → succès : drapeaux mis à jour, puis `triggerTopologyRescan` — le MÊME chemin que « Relire Jeedom » (corps, délai, messages identiques, vérifiés contre le bouton dans le même harnais) auquel un 4ᵉ paramètre facultatif `chain` a été ajouté sans toucher aux fragments de texte gardés par `test_story_20_4_rescan_ui`. Fin de relecture : « Relancez « Relire Jeedom » pour retirer les entités. » si elle a échoué (réseau, refus, échec du démon) ; `refreshBridgeStatus()` (une seule fois, compteur `jeedom2haBridgeRefreshes`) ; `notifyStatesChanged()` (déjà dans `complete`) → une lecture `getEquipmentStates` sans `refresh`. Le focus revient au bouton déclencheur (résolu à l'instant du besoin : le détail est redessiné après l'écriture).
- **Contrôles** : menu « ⋯ » de carte (PHP `j2ha_render_room_menu`, composant `.j2ha-menu-*` de 25.1 sans en modifier une règle ; une seule entrée `data-ha-action="exclure-piece"`) ; propagation arrêtée pour le clic, `keydown` et `keyup` du bouton, du menu et des entrées (test faux DOM ET vrai Chromium : souris, Entrée, Espace, flèches, Échap n'ouvrent jamais la pièce) ; classe d'ancrage `j2ha-room-has-menu` posée par le JS (le balisage de carte de 25.3 est inchangé) ; cible ≥ 44 × 44 px ; « Sans pièce » sans menu. Détail de pièce : entrée « Exclure la pièce… » / « Ne plus exclure la pièce… » AVANT le séparateur et « Supprimer de Home Assistant… », encart neutre « Pièce exclue : ses équipements ne sont pas publiés dans Home Assistant. » avec « Ne plus exclure la pièce… » (`surface.buildRoomExcludedNotice`).
- **Affichage (AC12/13)** : « Pièce exclue » (icône `fa-eye-slash` + mot) REMPLACE seulement le ratio de la carte (jauge et repères, dont « N exclus » de 25.7, conservés) ; « N pas encore retirés » compte les équipements ni « Exclu », ni « Désactivé », ni non lus ; la carte dit « Pièce exclue » même sans lecture des états ; nom accessible « Nom, pièce exclue, … » ; même mention dans l'arbre de la vue. D1 : `applyRoomExclusionPrecedence` pose l'infobulle « Pièce exclue : elle prime sur ce réglage. » sur les segments grisés « Toujours » / « Jamais » d'un équipement dont `exclusionCauseOf` est « par la pièce » ; `publicationActionState` n'est pas modifié ; un « Toujours » déjà posé reste la position courante.
- **Gate 20-0** : `policy.mjs` (ajout de 27 lignes, aucune retirée) : `saveRoomExclusion` → `simulate` / `exclusion-piece-declaree` si POST, exactement `action`+`objectId`+`excluded`, objectId entier strictement positif et sens identiques à `ctx.declaredRoomExclusions` ; sinon `block-fail` / `exclusion-piece-non-declaree` (les doublons de paramètres sont refusés plus tôt par `parametres-invalides`, `block-fail` aussi) ; `ALLOWED_READS`, `SIDE_EFFECT_ACTIONS`, `OVERRIDE_WRITE_ACTIONS` inchangés. `simulate.mjs` : `setRoomExclusionBase` (liste simulée amorcée avec la valeur RÉELLE de `excludedObjects`, relevée en lecture seule par la sonde existante du lanceur, mêmes règles que le plugin) et `buildRoomExclusionResponse` (forme de D2 ; la liste simulée s'accumule d'une écriture à l'autre). `interceptor.mjs` : branche EXPLICITE avant `saveMappingOverride`, la branche `else` des retours de réglage est inchangée. `run-gate.mjs` : `declaredRoomExclusions` (défaut `{}`) et amorçage de la liste. `interceptor-selftest.mjs` : déclarée simulée / autre pièce et autre sens bloqués / jamais reçue par le serveur (tourne en local, vert). Parcours `exclusion-piece-simulee` (8 étapes, étiquettes de l'AC15, `record('entites_annoncees', N)`) passé en vrai Chromium avec la VRAIE politique et la VRAIE simulation (harnais `workview_browser.js` : option `gate`), avec contrôles négatifs pour 6 étiquettes sur 8.
- **Écart consigné — AC15 (8)** : une écriture sur une AUTRE pièce « provoquée par le parcours » fait échouer le gate (le journal consigne un `block-fail`) : elle ne peut donc pas figurer dans un parcours qui doit passer. L'étape (8) de `exclusion-piece-simulee` vérifie que la seule écriture d'exclusion émise est la déclarée et simulée (toute autre aurait été bloquée et consignée) ; la provocation elle-même est portée par le contrôle négatif dédié **`controle-exclusion-piece-non-declaree`** (échoue comme attendu, au même titre que `controle-ecriture-non-declaree`), par `test_story_20_0_gate_policy` (cas négatifs) et par l'auto-test de l'intercepteur. À lancer par ClaudeBox en Task 7.1. La seule pièce déclarée par défaut est la `4` (comme `controle-ecriture-non-declaree`) : à remplacer par l'identifiant technique choisi avec Alexandre, dans `declaredRoomExclusions` ET dans la constante `ROOM` du parcours.
- **AC16** : chaîne de départ à deux pièces + un identifiant disparu + un jeton non numérique → exclure une troisième, ré-exclure (`changed:false`, aucune écriture), ne plus exclure : chaîne finale IDENTIQUE (test PHP) ; côté interface, rejouer sur une pièce déjà exclue ne pose pas d'écriture de plus côté serveur mais relance la relecture (test d'enchaînement) — comportement consigné dans `index.md`.
- **AC19** : `git diff --stat origin/main...HEAD -- resources/daemon/models resources/daemon/mapping resources/daemon/sync resources/daemon/discovery core/class` vide ; `resources/daemon/` ne change que par `transport/http_server.py` (`_project_equipment_state` + docstring) et ses tests ; `policy.mjs` ne change que par l'ajout de l'AC14. (`plugin_info/` : changé par 25.9 seulement.)
- **Non fait / hors périmètre** : le lien « Ne plus exclure la pièce… » dans l'encart de cause « Exclu par la pièce » du détail d'ÉQUIPEMENT (question Q4 de 25.7 : « le lien renvoie au contrôle de 25.8 une fois livré ») n'est pas dans les AC de 25.8 : non ajouté, à décider en revue. La validation UX finale (carte étroite, iPad mural, débordement du menu dans la carte) reste à 25.5. Tasks 0 et 7 sautées (CC-48).
- **Tests existants adaptés (AC20), liste** : `test_story_25_1_surface` (le motif interdit `Exclure l` devient `Exclure l(?!a pièce)` : « Exclure la pièce… » est désormais un libellé voulu ; les anciens boutons d'équipement restent interdits) ; `test_story_25_3_page_b` (champs de `j2haRoomsTree` : + `excluded`) ; `test_story_25_4_css_collision` et `…_palette_theme` (+ les trois familles de sélecteurs de carte de 25.8, sous `.j2ha-room-groups`) ; `test_story_25_4_non_regression` (les gardes « diff vide » du démon, de l'ajax et de la politique deviennent « aucune ligne existante retirée hors ces remplacements explicites » ; `core/class/` et scripts restent à diff vide) ; `test_story_25_7_documentation` (retrouve son entrée de changelog par son titre) ; `test_story_25_7_php_plugin_names.php` (champs de pièce : + `excluded`) ; `test_story_25_2_route_agregee.py` (+ `present_in_ha`) et la fixture `tests/fixtures/story_25_2_parite_etat.json` régénérée ; `test_story_25_2_load.py` (seuil de vigilance) ; `tests/test_php_topology_extraction.php` (+ un cas par ajout : la chaîne produite par la fonction de la route est lue par la même extraction, `exclusion_source=object`, non exécutable ici : vrai cœur Jeedom requis, comme le reste du fichier) ; aides de test `render_page.php` (faux `config`), `page_b_harness.js`, `ui_harness.js`, `workview_browser.js` (option `gate`).
- **Résultat final de `scripts/ci-local.sh`** : voir le Dev Agent Record de 25.9 (même exécution, après les deux stories).

### File List

- `core/php/jeedom2ha_room_exclusion.php` (nouveau)
- `core/ajax/jeedom2ha.ajax.php` (branche `saveRoomExclusion`)
- `desktop/php/jeedom2ha.php`, `desktop/php/jeedom2ha_overview_helpers.php`
- `desktop/js/jeedom2ha.js`, `desktop/js/jeedom2ha_overview.js`, `desktop/js/jeedom2ha_workview.js`, `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/js/jeedom2ha_mapping_override.js`, `desktop/css/jeedom2ha.css`
- `resources/daemon/transport/http_server.py`
- `tests/e2e/gate/lib/policy.mjs`, `tests/e2e/gate/lib/simulate.mjs`, `tests/e2e/gate/lib/interceptor.mjs`, `tests/e2e/gate/run-gate.mjs`, `tests/e2e/gate/interceptor-selftest.mjs`
- `tests/e2e/gate/parcours/exclusion-piece-simulee.mjs` (nouveau), `tests/e2e/gate/parcours/controle-exclusion-piece-non-declaree.mjs` (nouveau)
- Tests nouveaux : `tests/test_php_story_25_8_exclusion_piece.php`, `tests/unit/test_story_25_8_{carte_menu,confirmation,enchainement,affichage,gate,navigateur_reel,documentation}.node.test.js`, `resources/daemon/tests/unit/test_story_25_8_present_in_ha.py`
- Tests adaptés par ajout : voir la liste ci-dessus (`tests/unit/test_story_20_0_gate_{policy,simulate}`, `test_story_25_{1_surface,3_page_b,4_css_collision,4_palette_theme,4_non_regression,7_documentation}`, `test_story_25_7_php_plugin_names.php`, `resources/daemon/tests/unit/test_story_25_2_{route_agregee,load}.py`, `tests/fixtures/story_25_2_parite_etat.json`, `tests/test_php_topology_extraction.php`, `tests/unit/helpers/{render_page.php,page_b_harness.js,ui_harness.js,workview_browser.js}`)
- `docs/fr_FR/index.md`, `docs/fr_FR/compteurs.md`, `docs/fr_FR/changelog_beta.md`
- `_bmad-output/implementation-artifacts/25-8-exclusion-piece-depuis-la-surface.md`, `sprint-status.yaml` (statuts, Dev Agent Record)

## Décisions (ClaudeBox, 2026-10-19 17:40)

Story relue. Les recommandations sont retenues pour Q1 à Q10, avec ces précisions :
- **Q1 = B.** On ajoute `present_in_ha` aux entités de la liste blanche de la route agrégée. C'est un ajout de champ, autorisé : la contrainte « aucun changement du démon » du sprint-change ne porte que sur la règle de priorité (D1). Le chiffre annoncé doit être exact pour servir de preuve.
  - **Mesure obligatoire** de la taille de la réponse sur la fixture la plus lourde, puis sur la box en preuve terrain. Seuil de vigilance : 1 350 000 octets. Seuil bloquant : 1 500 000 octets.
  - Si le seuil de vigilance est dépassé sur la box, on garde quand même le champ, et la preuve consigne le chiffre. Si le budget est dépassé, on se replie sur « N équipements (M commandes) » sans le champ, et on le consigne.
- **Q2** : route `saveRoomExclusion` (`objectId`, `excluded=1|0`), déclarée dans `policy.mjs` comme écriture simulée, avec sa branche dédiée dans l'intercepteur. On n'utilise pas la branche `else` des retours de réglage.
- **Q3** : menu « ⋯ » sur la carte, avec arrêt de propagation du clic.
- **Q4** : sur la carte d'une pièce exclue, « Pièce exclue » remplace seulement le ratio. On garde la jauge et les repères, plus « N pas encore retirés » tant que la relecture n'a pas eu lieu.
- **Q5** : les jetons inconnus sont conservés tels quels, dans leur ordre.
- **Q6** : la relecture applique aussi tous les réglages en attente de la maison. On l'annonce, chiffré, dans la même confirmation. On relit même s'il n'y a aucun changement.
- **Q7** : « Ne plus exclure » demande une confirmation sans chiffre, avec un bouton principal (pas rouge).
- **Q8** : si la lecture est indisponible, l'action reste autorisée, avec « Nombre d'entités inconnu ».
- **Q9** : la preuve terrain se fait sur une pièce de test **choisie avec Alexandre au moment de la preuve**, état initial restauré. **25.8 et 25.9 sont déployées ensemble**, pour ne jamais laisser « Appliquer et rescanner » réécrire une valeur périmée d'`excludedObjects`.
- **Q10** : infobulle « Pièce exclue : elle prime sur ce réglage. », sans modifier `publicationActionState`.

**Statut : `ready-for-dev`.**

## Questions ouvertes pour ClaudeBox / Alexandre

Chaque question porte une **recommandation argumentée** ; **aucune n'est tranchée par la session**. Les AC écrits « par défaut » suivent la recommandation.

**Q1 — Comment chiffrer « N entités seront retirées de Home Assistant » ?**
La route agrégée ne dit pas, entité par entité, ce qui est présent dans Home Assistant (`entities[]` n'y porte que `override_pending`) ; l'arbre unitaire le dit (`present_in_ha`), mais 25.4 interdit de le lire hors sélection.
- A. Sans toucher au démon : compter ce que l'entrée agrégée sait exactement — les **équipements** de la pièce présents dans HA (`sync_status.published_in_ha`) et leurs **commandes** publiées (`commands[].published_in_ha`) — et formuler « N équipements (M commandes) seront retirés de Home Assistant ». Exact, mais pas en « entités » comme décidé en D3, et l'écart d'inventaire HA de la preuve ne se compare pas directement.
- B. **Ajouter `present_in_ha` à la projection `entities[]` de la liste blanche** (champ déjà calculé par le même constructeur, lecture seule, aucune décision nouvelle) et compter les entités présentes des équipements de la pièce. *(recommandé : c'est la seule façon de dire exactement « N entités » comme décidé en D3, et de rendre la preuve terrain discriminante — l'écart d'inventaire HA doit égaler N ; le coût est de l'ordre de 20 octets par entité, à mesurer contre le seuil de vigilance de 1 350 000 octets que la réponse frôle (1 342 346), le budget restant 1 500 000. Si ClaudeBox lit « aucun changement du démon » (D1) comme couvrant toute la story, retenir A et faire valider la formulation par Alexandre.)*
- C. Lire les arbres unitaires des équipements publiés de la pièce au clic sur « Exclure la pièce… » : exact, sans toucher au démon, mais rouvre le préchargement que 25.4 a supprimé (décision 5 de 25.4).

**Q2 — Nom et forme de la route.**
- A. **`saveRoomExclusion`** avec `objectId` et `excluded=1|0` (une route, deux sens). *(recommandé : suit la convention `save…` des écritures existantes ; un seul site à déclarer dans la politique ; le sens est un paramètre validé.)*
- B. Deux routes `excludeRoom` / `includeRoom` : plus lisibles, deux entrées de politique et deux branches de simulation.

**Q3 — Forme du contrôle sur la carte.**
- A. **Menu « ⋯ »** (composant de 25.1) en coin de carte, avec une seule entrée « Exclure la pièce… » / « Ne plus exclure la pièce… ». *(recommandé : le geste destructif est derrière deux clics et une confirmation ; même grammaire que le détail ; laisse la place à d'autres entrées de pièce plus tard.)*
- B. Bouton-icône direct (œil barré) : un clic de moins, mais un geste qui retire de HA à portée d'un doigt sur l'iPad mural, et une icône à interpréter.
- *Accessibilité :* la carte est un `role="button"` ; un bouton à l'intérieur est un élément interactif imbriqué. Recommandation : l'accepter (arrêt de propagation, nom accessible explicite, test clavier) plutôt que de changer le balisage des cartes fixé par 25.3 ; à revoir en 25.5 si la recette le signale.

**Q4 — Carte d'une pièce exclue : que garder sous « Pièce exclue » ?**
- A. **Remplacer seulement le ratio** par « Pièce exclue » ; garder la jauge (toute grise après relecture) et les repères (dont « N exclus » de 25.7) ; ajouter « N pas encore retirés » tant que la copie des états montre des équipements de la pièce non exclus. *(recommandé : la carte reste vraie avant et après la relecture ; aucune information n'est cachée ; un échec de relecture se voit.)*
- B. Carte réduite à « Pièce exclue » sans jauge : plus sobre, mais masque un état transitoire faux (entités encore publiées).

**Q5 — Jetons inconnus dans `excludedObjects` (identifiant d'objet supprimé, texte saisi à la main).**
- A. **Conservés tels quels, dans leur ordre** ; seuls les jetons égaux à l'objet visé sont ajoutés ou retirés. *(recommandé : « reprise sans perte » ; la route ne fait que ce qu'on lui demande ; 25.9 retire le champ texte, donc plus de nouveaux jetons à la main.)*
- B. Normaliser (supprimer les jetons non numériques et les objets disparus) : plus propre, mais une écriture de surface modifierait des réglages que l'utilisateur n'a pas touchés.

**Q6 — La relecture applique aussi tous les réglages en attente de la maison.**
- A. **Le dire dans la confirmation, chiffré** (« La relecture appliquera aussi les M réglages en attente de la maison », M = effectif maison « à appliquer ») et enchaîner sans seconde confirmation ; relancer la relecture même si `changed` est faux. *(recommandé : aucune purge ni application cachée ; le démon n'offre pas de relecture limitée à une pièce ; une seule confirmation chiffrée pour un seul geste.)*
- B. Enchaîner aussi la confirmation de « Relire Jeedom » : deux confirmations pour un geste, l'utilisateur apprend à cliquer sans lire.
- C. Refuser l'exclusion tant que des réglages sont en attente : sûr, mais bloque un geste simple pour une raison sans rapport.

**Q7 — « Ne plus exclure » : confirmation chiffrée ou non ?**
- A. **Confirmation sans nombre**, bouton principal non rouge : « Ses équipements seront relus et publiés s'ils sont publiables. » *(recommandé : un équipement exclu n'a ni entité ni commande évaluée, on ne peut donc pas annoncer combien d'entités apparaîtront sans relecture ; rien n'est retiré de HA, donc pas de rouge.)*
- B. Pas de confirmation : plus rapide, mais publie d'un clic des entités que l'utilisateur avait écartées.

**Q8 — Confirmation quand la lecture des états est indisponible.**
- A. **Autoriser**, en disant « Nombre d'entités inconnu : la lecture des états n'est pas disponible. » *(recommandé : l'écriture et la relecture ne dépendent pas de la lecture des états ; la confirmation reste honnête.)*
- B. Interdire l'exclusion tant que la lecture n'a pas abouti : jamais de nombre inconnu, mais le contrôle disparaît justement quand on cherche à corriger.

**Q9 — Preuve terrain : pièce de test, et fenêtre entre 25.8 et 25.9.**
- A. **Pièce de test choisie par Alexandre** (GO explicite, écriture réelle courte, état initial restauré et vérifié par inventaire) ; et **déployer 25.9 juste après 25.8** — idéalement dans le même déploiement — car tant que 25.9 n'est pas livrée, « Appliquer et rescanner » de la page de configuration réécrit `excludedObjects` avec la valeur du champ chargée à l'ouverture de cette page et peut défaire une exclusion posée depuis la surface. *(recommandé : sécurité de la maison d'abord ; la fenêtre de risque est nulle si les deux sont déployées ensemble.)*
- B. Prouver sur la démo VM 122 seulement : sans risque pour la maison, mais la preuve d'inventaire HA de la box (décidée) manquerait.

**Q10 — Infobulle du segment grisé dans une pièce exclue (D1).**
- A. **« Pièce exclue : elle prime sur ce réglage. »**, calculée dans la surface à partir de la cause de 25.7, sans modifier `publicationActionState`. *(recommandé : dit pourquoi « Toujours » ne fait rien, conformément à D1 ; aucune fonction de 25.1 n'est réécrite.)*
- B. Garder « Équipement non éligible : l'action serait sans effet. » : exact, mais n'explique pas que la pièce est la cause.

## Change Log

- 2026-10-19 — Création (`create-story`, session cloud déléguée) depuis le sprint change du 19/10 (D1, D3) : statut `backlog`, 21 AC, 13 décisions déjà arbitrées, 10 questions ouvertes avec recommandation ; constats consignés : la relecture applique tous les réglages en attente (Q6), le décompte exact en entités n'est pas dans la route agrégée (Q1), fenêtre de risque avant 25.9 (Q9) ; `ready-for-dev` non accordé ; statut cible `ready-for-UX-validation` (validation UX finale en 25.5).
- 2026-10-19 17:40 — Relecture ClaudeBox : recommandations retenues (§ Décisions) ; `ready-for-dev`.
- 2026-10-19 — Dev-story (session cloud déléguée) : AC1 à AC16 et AC18 à AC21 implémentés (route `saveRoomExclusion`, `excluded`, menu de carte, confirmation chiffrée, enchaînement, « Pièce exclue », D1, gate 20-0 : politique + simulation + parcours), Q1 = B (`present_in_ha`, taille mesurée) ; tests rouges puis verts ; documentation ; statut `review`. Tasks 0 et 7 (déploiement, preuve terrain, AC17) laissées à ClaudeBox.
