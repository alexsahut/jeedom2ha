# Story 25.9 : Page de configuration — exclusion par plugin seulement

Status: ready-for-dev

> **Statut : `ready-for-dev` (2026-10-19 17:40, relecture et décisions ClaudeBox ; Alexandre présent, peut revenir sur une décision).** Précédemment : **`backlog` (2026-10-19).** Story rédigée par une session cloud déléguée (`create-story`, documentaire : aucun code, aucun test, aucune fixture, aucun accès box / VM / Home Assistant / SSH / secret, CC-48), à partir du sprint change `sprint-change-proposal-2026-10-19-revue-ux-25.md` (statut **decided**, décision **D4**, point 4 du déclencheur). **`ready-for-dev` n'est pas accordé** : relecture de la story par ClaudeBox, puis décisions sur Q1 à Q6 (§ Questions ouvertes, chacune avec une recommandation argumentée ; la session n'en tranche aucune). **Statut cible après implémentation et preuve terrain : `ready-for-UX-validation`** ; validation UX finale en **25.5**. Les points de § Décisions déjà arbitrées sont **fermés**. Pointeurs de code pris sur `main` à `731be8d` ; **à re-vérifier au SHA courant** (après 25.8) avant le `dev-story`. Aucun nom réel d'équipement, de pièce, d'objet, de plugin installé chez Alexandre, de scénario ou de personne : identifiants et données fictifs seulement (CC-48).

## Story

En tant que propriétaire qui configure le plugin,
je veux que la page de configuration ne garde que l'exclusion **par plugin**, sous forme d'une **liste à cocher des plugins présents**, et qu'elle me renvoie vers la page du plugin pour exclure une pièce,
afin de ne plus saisir de noms techniques ni d'identifiants à la main, et de régler chaque exclusion là où elle se voit.

**Parcours : page de configuration (`plugin_info/configuration.php`, PHP + JS en ligne), relais ajax (`saveFilteringConfig`), docs, tests PHP et Node.** Aucune modification du démon, de la logique d'éligibilité (`core/class/`) ni du format des clés (AC9).

**Dépendances :** **25.8** (le contrôle d'exclusion de pièce sur la surface doit exister avant que le champ « Pièces exclues » disparaisse) ; 25.7 (table des noms de plugin, si Q1 de 25.7 = A). Ordre décidé : 25.6 → 25.7 → 25.8 → **25.9** → 25.5. Voir Q9 de 25.8 : déployer 25.9 au plus près de 25.8 ferme la fenêtre où « Appliquer et rescanner » peut réécrire `excludedObjects` avec une valeur périmée.

## Décisions déjà arbitrées

1. **D4 — Liste à cocher des plugins présents** au lieu du texte libre ; **même clé `excludedPlugins`, même format** (CSV d'identifiants techniques `eq_type_name`, séparés par des virgules). (Décision d'Alexandre, 19/10 13:50.)
2. **Retrait du champ « Pièces exclues »** de la page de configuration, avec un **renvoi vers la surface** (carte et détail de pièce, 25.8). (Sprint change, découpage 25.9.)
3. **`saveFilteringConfig` n'écrit plus `excludedObjects`** — et **ne l'efface pas** : la valeur existante est conservée telle quelle (les pièces déjà exclues restent exclues). (Sprint change ; reprise sans perte de 25.8.)
4. **Documentation `docs/fr_FR/index.md` mise à jour.** (Sprint change.)
5. **Mécanisme A1 inchangé** : le plugin lit toujours `excludedPlugins` et `excludedObjects` de la même façon (`core/class/jeedom2ha.class.php:764-766`), même priorité équipement > plugin > pièce. (Sprint change, § Analyse.)
6. **Hors périmètre** : A3 (`publishedScope*`), causes cumulées, contrat de décision, artefacts figés. (Sprint change.)
7. **Vocabulaire de 25.1**, libellés via `{{…}}`, aucun terme interdit ; compatibilité Jeedom 4.4 préservée. (25.1.)
8. **Statut cible : `ready-for-UX-validation`**, validation UX finale en 25.5.

## Sources lues

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-19-revue-ux-25.md` ; `epics-projection-engine.md` § Epic 25 ; `sprint-status.yaml` ; `25-7-cause-exclusion-affichee.md` (Q1 : table des noms de plugin) ; `25-8-exclusion-piece-depuis-la-surface.md` (route `saveRoomExclusion`, Q9).
- Code (lecture seule, `main` `731be8d`) : `plugin_info/configuration.php` (fieldset « Filtrage & Publication » `:110-157` : `excludedPlugins` `:115-124`, `excludedObjects` `:126-133`, `confidencePolicy` `:135-146`, bouton `#bt_applyAndRescan` `:150` ; JS en ligne : `saveFilteringConfig` puis `scanTopology` `:289-330`, mention « NE PAS déplacer dans desktop/js ») ; `core/ajax/jeedom2ha.ajax.php` (`saveFilteringConfig` `:813-828`) ; `core/class/jeedom2ha.class.php` (`:764-766`, `:841-851`) ; `tests/unit/test_story_20_4_rescan_ui.node.test.js`, `test_story_a1_client_timeout.node.test.js`, `test_story_9_0_mapping_summary_total.node.test.js` (tests qui lisent `configuration.php`) ; `tests/test_php_topology_extraction.php` ; `docs/fr_FR/index.md` (`:95-107`, `:115`, `:485-495`).

## Contexte et périmètre

### Ce qui existe aujourd'hui (relevé sur `731be8d`)

- Fieldset « Filtrage & Publication » : « Plugins exclus » (texte libre, `configKey` `excludedPlugins`, exemple `virtual,zwave,rfxcom`), « Pièces exclues » (texte libre, `configKey` `excludedObjects`, identifiants numériques), « Politique de publication » (liste), puis le bouton « Appliquer et rescanner » (`#bt_applyAndRescan`) qui envoie les **trois** valeurs à `saveFilteringConfig` puis lance `scanTopology`.
- Les champs portent la classe `configKey` : le bouton « Sauvegarder » du cœur Jeedom les enregistre **aussi**. Un champ `excludedObjects` laissé dans la page, même masqué, serait réécrit par « Sauvegarder ».
- `saveFilteringConfig` écrit les trois clés sans condition (`init('excludedObjects', '')` : un appel sans le paramètre **effacerait** la clé) et journalise les trois valeurs.

### Dans le périmètre

- liste à cocher des plugins présents, écrivant `excludedPlugins` au même format (AC1 à AC4) ;
- retrait du champ « Pièces exclues » et renvoi vers la surface (AC5) ;
- `saveFilteringConfig` sans écriture ni effacement d'`excludedObjects` (AC6, AC7) ;
- documentation (AC8) ; non-régression, conventions, preuve terrain, statut (AC9 à AC12).

### Hors périmètre (ne pas faire ici)

- toute modification de `resources/daemon/`, de `core/class/` (lecture des clés), du format des clés ; toute migration ou normalisation des valeurs existantes ;
- la route `saveRoomExclusion` et les contrôles de la surface (25.8) ; la cause d'exclusion (25.7) ;
- la politique de publication, la connexion MQTT, les autres sections de la page ;
- le gate 20-0 (la page de configuration n'est pas un parcours du gate ; `saveFilteringConfig` reste un effet de bord bloqué par `policy.mjs`, inchangé).

## Définitions normatives

### D1 — Plugins présents

Liste calculée par la page (PHP, au rendu) : les **identifiants techniques** des plugins qui ont **au moins un équipement** dans Jeedom, hors `jeedom2ha` (Q1), chacun avec son **nom affiché** (repli : l'identifiant) ; triés par nom affiché, sans tenir compte de la casse ni des accents. S'y ajoutent, **cochés**, les identifiants présents dans `excludedPlugins` mais **absents** de Jeedom, avec la mention « (absent de Jeedom) » (Q2) : rien n'est perdu à l'enregistrement.

### D2 — Valeur écrite

- Cocher / décocher ne change que la présence de l'identifiant dans `excludedPlugins`.
- Les identifiants déjà présents gardent **leur ordre** ; un identifiant nouvellement coché est ajouté **en fin** ; un identifiant décoché est retiré (toutes ses occurrences).
- Format de sortie : identifiants joints par `,` sans espace ; liste vide → chaîne vide. Le jeu d'identifiants lu par `core/class/jeedom2ha.class.php:764` (`trim`, `array_unique`, `array_filter`) est **identique** à celui que la page affiche coché (test d'équivalence).
- Un champ porteur `configKey` `excludedPlugins` (masqué) reste la valeur de référence pour « Sauvegarder » du cœur et pour `#bt_applyAndRescan` ; les cases à cocher le tiennent à jour (Q3).

## Acceptance Criteria

### A. Liste à cocher des plugins

**AC1 — Rendu**
**Given** une configuration fictive avec des équipements de trois plugins fictifs (`plugin_alpha`, `plugin_beta`, `plugin_gamma`) et `excludedPlugins = "plugin_beta,plugin_gone"`
**When** la page de configuration est rendue
**Then** le groupe « Plugins exclus » affiche une case par plugin de D1 : `plugin_alpha` (non cochée), `plugin_beta` (cochée), `plugin_gamma` (non cochée), et `plugin_gone` (cochée, « (absent de Jeedom) ») ; chaque case a pour libellé le nom affiché suivi de l'identifiant technique en texte secondaire ; `jeedom2ha` n'apparaît pas (test PHP `tests/test_php_story_25_9_configuration.php` sur la fonction pure de construction de la liste)
**And** les noms viennent de Jeedom et sont échappés (aucune injection HTML possible par un nom de plugin, test avec un nom fictif contenant `<img onerror>`)
**And** sans aucun plugin présent ni exclu, la page affiche « Aucun plugin avec des équipements. » à la place de la liste.

**AC2 — Valeur écrite (D2)**
**Given** l'état de l'AC1
**When** l'utilisateur coche `plugin_alpha`, décoche `plugin_beta`, puis clique « Appliquer et rescanner » (ou « Sauvegarder » du cœur)
**Then** la valeur envoyée pour `excludedPlugins` est exactement `"plugin_gone,plugin_alpha"` (ordre conservé, ajout en fin, retrait) ; aucune autre transformation (test Node du JS en ligne, sur le modèle de `test_story_20_4_rescan_ui`)
**And** décocher `plugin_gone` le retire ; ne rien toucher renvoie la valeur **identique** à la valeur chargée (y compris des espaces d'origine normalisés seulement si Q4 le décide).

**AC3 — Équivalence avec l'extraction**
**Given** une table de valeurs `excludedPlugins` fictives (vide, une valeur, doublons, espaces, identifiant absent)
**When** on compare l'ensemble coché par la page et l'ensemble lu par `core/class/jeedom2ha.class.php:764`
**Then** ils sont égaux pour chaque entrée (test PHP) : ce que la page montre exclu est ce que le plugin exclut.

**AC4 — Accessibilité et libellés**
**Given** la liste à cocher
**When** elle est rendue
**Then** c'est un groupe `fieldset` / `legend` (ou `role="group"` avec `aria-labelledby`) intitulé « Plugins exclus », avec une aide « Les équipements des plugins cochés ne sont pas publiés dans Home Assistant. » ; chaque case est une vraie `input type="checkbox"` avec `label` associé ; navigation clavier native ; si la liste dépasse Q5, elle défile dans une zone de hauteur bornée sans défilement horizontal ; libellés via `{{…}}`, sans terme interdit de 25.1 AC23 (« eq_type_name » ne figure plus dans un libellé visible).

### B. Pièces exclues

**AC5 — Retrait du champ, renvoi vers la surface**
**Given** la page de configuration
**When** elle est rendue
**Then** il n'existe plus aucun élément `.configKey[data-l1key=excludedObjects]` ni champ de saisie des pièces (`grep -n "excludedObjects" plugin_info/configuration.php` ne renvoie rien) ; à la place, un texte « Pièces exclues : elles se règlent depuis la page du plugin (menu « ⋯ » d'une carte de pièce, ou détail de la pièce). » avec un lien vers la page du plugin, et, si au moins une pièce est exclue, le nombre « N pièces exclues » calculé depuis la clé par la fonction de lecture de 25.8 (Q6)
**And** « Sauvegarder » du cœur n'écrit plus `excludedObjects` (la clé n'est plus portée par aucun `configKey`) ; un test le vérifie sur le HTML rendu.

### C. Relais `saveFilteringConfig`

**AC6 — `excludedObjects` ni écrit ni effacé**
**Given** `excludedObjects` fictif `"5,12"` en configuration
**When** `saveFilteringConfig` est appelé **avec** un paramètre `excludedObjects` (ancienne page restée ouverte, valeur `""` ou `"7"`) puis **sans** ce paramètre
**Then** `excludedObjects` vaut toujours `"5,12"` après chaque appel ; un espion sur `config::save` prouve que seules `excludedPlugins` et `confidencePolicy` sont écrites (test PHP)
**And** la ligne de journal ne mentionne plus `excludedObjects` ; la réponse reste `{ saved: true }` (le JS de la page n'a pas à changer de lecture).

**AC7 — Bouton « Appliquer et rescanner »**
**Given** le JS en ligne de `configuration.php`
**When** le bouton est cliqué
**Then** la requête `saveFilteringConfig` contient exactement `action`, `excludedPlugins`, `confidencePolicy` (plus de `excludedObjects`) ; l'enchaînement avec `scanTopology`, les budgets (`timeout: 90000`, story A1) et les messages sont inchangés ; `test_story_20_4_rescan_ui`, `test_story_a1_client_timeout`, `test_story_9_0_mapping_summary_total` passent (adaptés par ajout seulement s'ils lisaient `excludedObjects`).

### D. Documentation, non-régression, conventions

**AC8 — Documentation**
**Given** `docs/fr_FR/index.md`, `changelog_beta.md`
**When** la story est livrée
**Then** § « Filtrage et publication » décrit la liste à cocher (plugins présents, plugins absents encore exclus, ordre sans importance), retire la ligne « Pièces exclues » du tableau et la remplace par le renvoi vers la page du plugin ; § « Première synchronisation » (`:115`) et famille 7 « Exclusions volontaires » (« Champ « Pièces exclues » ») sont réalignés ; `changelog_beta.md` reçoit une entrée ; un test de documentation vérifie l'absence de « Pièces exclues » comme champ de configuration et la présence verbatim des libellés cités.

**AC9 — Aucune modification hors page de configuration et relais**
**Given** la branche de la story
**When** on exécute `git diff --stat main...HEAD -- resources/daemon/ core/class/ desktop/ tests/e2e/gate/`
**Then** la sortie est **vide** (hors un éventuel helper PHP partagé avec 25.7 sous `desktop/php/` si Q1 de 25.7 = A — alors réutilisé sans modification) ; `git diff main...HEAD -- core/ajax/jeedom2ha.ajax.php` ne touche que la branche `saveFilteringConfig` ; `test_php_topology_extraction.php` passe sans modification (lecture des clés inchangée).

**AC10 — Non-régression**
**Given** les suites PHP et Node, dont celles de 25.8
**When** elles s'exécutent
**Then** elles passent ; la route `saveRoomExclusion` (25.8) reste le seul écrivain d'`excludedObjects` dans le plugin (`grep -rn "config::save('excludedObjects'" core/` → une seule occurrence, dans la route de 25.8).

**AC11 — Preuve terrain (ClaudeBox)**
**Given** la story fusionnée et déployée
**When** ClaudeBox exécute la Task 5
**Then** la preuve consigne (identifiants seuls) : `excludedPlugins` et `excludedObjects` avant ; la liste à cocher reflète exactement `excludedPlugins` ; « Appliquer et rescanner » sans rien changer → `excludedPlugins` **identique**, `excludedObjects` **identique** (les deux pièces déjà exclues restent exclues), inventaire HA inchangé, 0 ligne `ERROR` ; la page n'a plus de champ « Pièces exclues » et son renvoi mène à la page du plugin.

**AC12 — Conventions et statut**
**Given** CLAUDE.md
**When** la PR de dev est ouverte
**Then** une PR = ce sujet ; titre Conventional Commits ; `make test`, `node --test tests/unit/*.node.test.js`, tests PHP, `flake8`, `scripts/ci-local.sh` verts ; plugins fictifs dans les fixtures, aucun nom réel, IP ni secret (CC-48) ; Tasks 0 et 5 sautées par une session cloud et la PR le dit
**And** après la preuve terrain le statut passe à **`ready-for-UX-validation`** ; il reste `backlog` jusqu'à `ready-for-dev`.

## Statut cible et validation UX

- **Statut actuel :** `backlog` ; `ready-for-dev` non accordé.
- **Chemin :** `backlog` → `ready-for-dev` (relecture ClaudeBox + Q1 à Q6, après 25.8 au moins `ready-for-dev`) → `review` → `ready-for-UX-validation` (preuve terrain ClaudeBox) → `done` à la clôture de 25.5.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY) **[réservée à ClaudeBox ; sautée par une session cloud (CC-48)]**
  - [ ] Dry-run `./scripts/deploy-to-box.sh --dry-run` ; déploiement `--sha <complet> --restart-daemon` depuis un worktree neuf (de préférence avec 25.8, Q9 de 25.8) ; `Deploy complete.`
  - [ ] Relever `excludedPlugins` et `excludedObjects` (identifiants seuls).
- [ ] Task 1 — Tests d'abord (AC: 1, 2, 3, 5, 6, 7)
  - [ ] 1.1 `tests/test_php_story_25_9_configuration.php` (liste D1, équivalence D2, `saveFilteringConfig` sans `excludedObjects`, HTML sans `configKey` `excludedObjects`).
  - [ ] 1.2 Test Node du JS en ligne (valeur écrite, corps de la requête).
- [ ] Task 2 — Liste à cocher (AC: 1 à 4)
  - [ ] 2.1 Fonction pure de construction de la liste (réutilise la table des noms de 25.7 si disponible) ; rendu ; champ porteur `configKey` tenu à jour (Q3).
- [ ] Task 3 — Pièces et relais (AC: 5 à 7)
  - [ ] 3.1 Retrait du champ, renvoi et nombre de pièces exclues ; `saveFilteringConfig` et son journal ; JS du bouton.
- [ ] Task 4 — Documentation et non-régression (AC: 8 à 10, 12)
  - [ ] 4.1 `index.md`, `changelog_beta.md`, test de documentation ; `git diff --stat` de l'AC9 ; suites complètes, `flake8`, `scripts/ci-local.sh`.
- [ ] Task 5 — Preuve terrain (après fusion) **[réservée à ClaudeBox ; sautée par une session cloud (CC-48)]**
  - [ ] 5.1 AC11 ; `25-9-preuve-terrain-<date>.md` (identifiants seuls) ; statut `ready-for-UX-validation`.

## Dev Notes

### Dev Agent Guardrails

- **Ne jamais effacer `excludedObjects`** : ni par `saveFilteringConfig` (paramètre présent ou absent), ni par « Sauvegarder » du cœur (aucun `configKey` restant), ni par une migration.
- **Même clé, même format** pour `excludedPlugins` ; aucune normalisation non décidée (Q4) ; un plugin absent mais exclu n'est jamais retiré en silence.
- Le JS de la page reste **en ligne** dans `configuration.php` (commentaire existant « NE PAS déplacer dans desktop/js »).
- **Ne pas modifier** `core/class/` (lecture des clés), le démon, `policy.mjs`.
- Vérifier au `dev-story`, sur le cœur Jeedom simulé, à quel moment le cœur remplit les `configKey` (chargement asynchrone de la configuration du plugin) et synchroniser les cases **après** ce remplissage (Q3) ; consigner.
- Libellés via `{{…}}` ; noms de plugin échappés ; plugins fictifs dans les tests (CC-48).
- Une session cloud saute les Tasks 0 et 5 et le dit dans la PR.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` ; jamais de procédure parallèle. Référence : `jeedom2ha-test-context-jeedom-reel.md`. Cycle canonique `main → beta → stable → Jeedom Market`.

### Précédents réutilisables

- Tests du JS en ligne de `configuration.php` : `test_story_20_4_rescan_ui`, `test_story_a1_client_timeout`.
- Lecture et écriture de `excludedObjects` : fonction pure de 25.8 (pour le nombre de pièces exclues).
- Table des noms de plugin : 25.7 Q1 A.

### Fichiers probablement touchés (pour le `dev-story`)

`plugin_info/configuration.php` (fieldset « Filtrage & Publication », JS en ligne) ; `core/ajax/jeedom2ha.ajax.php` (branche `saveFilteringConfig` seulement) ; éventuellement un helper PHP pur partagé (liste des plugins présents) ; `docs/fr_FR/index.md`, `changelog_beta.md` ; `tests/test_php_story_25_9_*.php`, `tests/unit/test_story_25_9_*.node.test.js` et tests existants adaptés par ajout.

### Definition of done

AC1 à AC12 tenus ; suites vertes ; PR relue par ClaudeBox ; preuve terrain (Task 5) ; statut `ready-for-UX-validation`.

### References

- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-19-revue-ux-25.md`#Décisions D4, #Découpage]
- [Source: `plugin_info/configuration.php`:110-157, :289-330]
- [Source: `core/ajax/jeedom2ha.ajax.php`:813-828 ; `core/class/jeedom2ha.class.php`:764-766]
- [Source: `_bmad-output/implementation-artifacts/25-8-exclusion-piece-depuis-la-surface.md`#Q9]

## UI Impact

- **UI Impact:** Oui — page de configuration du plugin : liste à cocher des plugins, retrait du champ « Pièces exclues » au profit d'un renvoi. Pas de parcours du gate 20-0 sur cette page ; preuve terrain par ClaudeBox ; statut cible `ready-for-UX-validation`.

## Dev Agent Record

### Agent Model Used

_(à remplir au `dev-story`)_

### Debug Log References

### Completion Notes List

### File List

## Décisions (ClaudeBox, 2026-10-19 17:40)

Story relue. Les recommandations sont retenues pour Q1 à Q6 :
- **Q1** : la liste propose les plugins qui ont au moins un équipement, hors `jeedom2ha`.
- **Q2** : un plugin exclu mais absent de Jeedom est affiché coché, avec « (absent de Jeedom) », et reste décochable.
- **Q3** : un champ masqué `configKey` `excludedPlugins` est tenu à jour par les cases. « Sauvegarder » et « Appliquer et rescanner » fonctionnent toujours.
- **Q4** : pas de normalisation. La valeur est réécrite identique si rien ne change.
- **Q5** : liste de hauteur bornée, sans champ de recherche.
- **Q6** : le renvoi affiche un texte, un lien vers la page du plugin et le nombre de pièces exclues, sans leurs noms.

Point d'ordonnancement : **déploiement en même temps que 25.8** (25.8 Q9).

**Statut : `ready-for-dev`.**

## Questions ouvertes pour ClaudeBox / Alexandre

Chaque question porte une **recommandation argumentée** ; **aucune n'est tranchée par la session**.

**Q1 — Quels plugins proposer ?**
- A. **Les plugins qui ont au moins un équipement** (hors `jeedom2ha`), lus au rendu. *(recommandé : c'est le sens de « plugins présents » ; un plugin sans équipement n'a rien à exclure ; la liste reste courte.)*
- B. Tous les plugins installés et actifs : liste plus longue (plugins sans équipement, plugins système), sans effet pour la plupart.

**Q2 — Identifiant exclu mais absent de Jeedom (plugin désinstallé, faute de frappe héritée du texte libre).**
- A. **Afficher coché, avec « (absent de Jeedom) »**, décochable. *(recommandé : reprise sans perte ; l'utilisateur voit et nettoie lui-même ; rien n'est retiré en silence.)*
- B. Le masquer et le conserver : invisible, donc impossible à retirer sans revenir au texte libre.
- C. Le supprimer à l'enregistrement : nettoie, mais modifie une exclusion sans geste de l'utilisateur.

**Q3 — Mécanique d'enregistrement.**
- A. **Garder un champ masqué `configKey` `excludedPlugins`** tenu à jour par les cases, lu par « Sauvegarder » du cœur et par « Appliquer et rescanner » ; cases rendues cochées côté serveur, puis resynchronisées après le remplissage des `configKey` par le cœur. *(recommandé : les deux boutons existants continuent d'écrire la même clé au même format, sans toucher au mécanisme de sauvegarde du cœur.)*
- B. Retirer `configKey` et n'écrire que par `saveFilteringConfig` : « Sauvegarder » du cœur n'enregistrerait plus les plugins exclus, ce qui surprendrait.

**Q4 — Normalisation de la valeur existante (espaces, doublons) quand rien n'a été coché ni décoché.**
- A. **Aucune** : la valeur est réécrite identique. *(recommandé : « même format » ; aucune écriture de contenu sans geste ; le plugin tolère déjà espaces et doublons à la lecture.)*
- B. Normaliser à la première sauvegarde : valeur plus propre, mais diff de configuration inattendu.

**Q5 — Longueur de la liste.**
- A. **Hauteur bornée** (environ 12 lignes visibles) avec défilement vertical, sans recherche. *(recommandé : le nombre de plugins avec équipements reste de l'ordre de la dizaine à la vingtaine ; une recherche serait du poids pour rien.)*
- B. Ajouter un champ de recherche : utile au-delà de 30 plugins, rare.

**Q6 — Contenu du renvoi « Pièces exclues ».**
- A. **Texte + lien vers la page du plugin + nombre de pièces exclues** (« 2 pièces exclues »), sans liste de noms. *(recommandé : l'utilisateur sait qu'il en existe et où les gérer ; aucun nom de pièce à rendre dans cette page.)*
- B. Lister les pièces exclues par leur nom : plus informatif, mais duplique la surface et ajoute des noms libres à échapper dans une page de plus.
- C. Texte seul : plus simple, mais cache qu'il existe encore des exclusions de pièce.

## Change Log

- 2026-10-19 — Création (`create-story`, session cloud déléguée) depuis le sprint change du 19/10 (D4) : statut `backlog`, 12 AC, 8 décisions déjà arbitrées, 6 questions ouvertes avec recommandation ; dépend de 25.8 ; `ready-for-dev` non accordé ; statut cible `ready-for-UX-validation` (validation UX finale en 25.5).
- 2026-10-19 17:40 — Relecture ClaudeBox : recommandations retenues (§ Décisions) ; `ready-for-dev`.
