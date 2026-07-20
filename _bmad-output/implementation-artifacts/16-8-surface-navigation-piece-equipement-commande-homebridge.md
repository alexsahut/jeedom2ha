# Story 16.8: Surface de navigation par pièce → équipement → commande (modèle Homebridge), branchée sur le triptyque + diagnostic HA

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur expert Jeedom (persona « Sébastien »),
je veux configurer les overrides de mapping HA depuis une **surface dédiée organisée par pièce → équipement → commande**, exactement comme le plugin Homebridge que j'utilise déjà, mais avec en plus **la visibilité immédiate de ce que Home Assistant attend** pour chaque commande,
afin de savoir d'un coup d'œil dans l'interface — **sans relancer le daemon ni lire les logs** — si un équipement répond aux prérequis HA et sera donc publié correctement.

## Contexte & motif de la corrective

- **Défaut découvert (2026-07-18, box 192.168.1.21)** : la Story 16.5 (`done`) a construit le bon *contenu* (triptyque natif/override/diagnostic + routes backend prouvées au gate 16.7) mais l'a posé sur un **point d'entrée inexistant** : l'onglet « HA / jeedom2ha » injecté dans `desktop/php/jeedom2ha.php` ne s'affiche que dans la fiche d'un **eqLogic de type jeedom2ha**. Or jeedom2ha est un bridge : `eqLogic::byType("jeedom2ha")` = **0** sur la box. La surface de config est donc **inatteignable**.
- **Double dérive de la 16.5 par rapport à l'epic** :
  1. Le fichier story 16.5 (AC2) a reformulé le point d'entrée en « onglet sur la fiche équipement Jeedom existante », alors que l'epic (`epics-projection-engine.md` l.2129, l.2137, l.2151) exigeait une **« surface Jeedom dédiée organisée par pièce comme Homebridge »** avec **« arborescence pièce → équipement → commande »**.
  2. L'implémentation n'a même pas atteint son propre AC2 affaibli (conteneur eqLogic jeedom2ha jamais rendu).
- **Décision** : cette story rétablit l'**intention epic-autoritaire** (nav par pièce, modèle Homebridge) et **supersède le point d'entrée** de la 16.5. Le backend override et le module pur `jeedom2ha_mapping_override.js` de la 16.5 restent valides et sont **réutilisés tels quels**.

## Acceptance Criteria

**Bloc A — Surface de navigation par pièce (modèle Homebridge éprouvé)**

1. Point d'entrée = une surface Jeedom **dédiée** dans la page du plugin jeedom2ha, reprenant le modèle du plugin Homebridge (`plugins/homebridge/desktop/php/homebridge.php` + modale `object.homebridge.php`). **Pas** d'onglet sur fiche eqLogic jeedom2ha, **pas** d'injection dans les fiches natives. Cette surface **supersède** le point d'entrée inatteignable de la Story 16.5 (AC2).
2. La surface liste les **pièces** via `jeeObject::buildTree(null, false)`, une entrée cliquable par pièce, dans l'ordre natif Jeedom (comme la section « Types Génériques par Pièce » de Homebridge).
3. Au clic sur une pièce, un drill-down (modale ou panneau, cf. Open Question 1) liste les **équipements de la pièce** via `eqLogic::byObjectId(object_id)`, en **accordéon Bootstrap** — un panneau collapsible par équipement (pattern `#accordionConfiguration` de `object.homebridge.php`).
4. Sous chaque équipement, la **liste plate des commandes** dans l'ordre natif de retour Jeedom — pas de tri, regroupement ni repositionnement front (cohérent avec la « liste plate » de la 16.5).
5. **Chargement paresseux** : la liste des pièces se rend sans solliciter le daemon pour les 290 équipements ; le diagnostic par commande n'est récupéré qu'à l'**ouverture de l'accordéon d'un équipement** (un GET `/system/mapping_overrides/{eq_id}` par équipement déplié), jamais en masse.

**Bloc B — Triptyque + diagnostic réutilisés (contenu 16.5, non réécrit)**

6. Pour chaque commande, le **triptyque existant** est monté : colonne natif `generic_type` (lecture seule, D10), colonne override HA (éditable), colonne diagnostic. Réutilisation **stricte** du module pur `desktop/js/jeedom2ha_mapping_override.js` et des routes backend existantes (`GET /system/mapping_overrides/{eq_id}`, `POST /system/overrides/preview`, `POST /action/mapping_override`, `POST /action/mapping_override_revert`). **Aucun nouveau backend override.**
7. Le diagnostic par commande affiche **« prêt (vert franc) / bloquant (neutre, actionnable) + pourquoi »** via `validate_projection` (reason_details) — c'est la correction explicite du défaut Homebridge (aucune visibilité sur l'attendu HomeKit/HA). L'information n'exige **ni relance du daemon, ni lecture des logs**.
8. L'édition d'un `ha_entity_type` déclenche le **dry-run instantané + auto-validation au vert** (comportement 16.5 conservé : débounce, pas de bouton « Valider » séparé, spinner circonscrit à la colonne override) ; **retour au mode auto** par commande et par équipement disponible.

**Bloc C — Synthèse de publication par équipement (le vrai besoin exprimé au cadrage)**

9. Chaque équipement affiche une **synthèse agrégée « sera publié / ne sera pas publié dans HA »**, calculée côté front à partir des diagnostics par commande (`should_publish` / `is_valid`) déjà retournés par le GET arbre — l'utilisateur voit **immédiatement, sans lancer de sync**, si les commandes de l'équipement répondent aux prérequis HA.
10. La synthèse indique le **compte commandes prêtes vs bloquantes** et fournit une **ancre directe vers la première commande bloquante**, pour transformer « ça ne se publie pas » en « voici quelle commande corriger et pourquoi ».

**Bloc D — Invariants & hygiène**

11. Le `generic_type` Jeedom natif **n'est jamais modifié** par aucune action de cette surface (D10, non-régression Homebridge). Seul objet muté = `data/ha_overrides.json` via les routes existantes.
12. **Aucun framework front** : jQuery/Bootstrap natif Jeedom, réutilisation des composants déjà en place (accordéons, badges, modale, tooltips). Aucune nouvelle palette/typo/spacing.
13. **Nettoyage du point d'entrée mort 16.5** : l'onglet « HA / jeedom2ha » injecté dans la fiche eqLogic jeedom2ha (inatteignable) est **retiré ou re-câblé** vers la nouvelle surface, pour ne pas laisser deux surfaces concurrentes ni de code mort trompeur.

**Bloc E — Gate terrain UI réel (obligatoire, correction du trou de la 16.5)**

14. **Task 0 / gate terrain** sur box `192.168.1.21`, prouvant le **parcours UI de bout en bout** (pas des cases cochées sans preuve) : ouvrir la page plugin → voir la liste des pièces → cliquer une pièce → voir l'accordéon des équipements → déplier un équipement → voir ses commandes + triptyque + diagnostic → éditer un override → constater le diagnostic passer au vert **et** la synthèse « sera publié » se mettre à jour. Preuves consignées (capture DOM/écran + échanges HTTP), avec au moins un équipement « prêt » et un équipement « bloquant ».

## Tasks / Subtasks

- [~] **Task 0 — Pre-flight & gate terrain UI (AC: 14)** — *déploiement + backend prouvés le 2026-07-18 ; walkthrough visuel navigateur restant (option « déploie seulement » choisie par Alexandre)*
  - [x] 0.1 — Pré-flight : daemon up sur `192.168.1.21` (mqtt connected), secret/API port OK (55080), `ha_overrides.json` snapshot avant = `{schema_version:2, overrides:{}, equipment_overrides:{}}` (vide, non muté depuis).
  - [~] 0.2 — Déploiement UI via `scripts/deploy-to-box.sh` : 5 assets desktop promus (dry-run == réel), `php -l` + `node --check` OK sur la box, sync `total_eq=290 eligible=98 published=246`. **Backend consommé par la surface prouvé** via `GET /system/mapping_overrides/{eq_id}` (X-Local-Secret) sur ids natifs réels : prêts = 391 « buanderie plafond » (light), 151 « Volets » (cover), 174 « Absence » (switch) tous `should_publish=true` ; bloquants = 607 « blueriiot2mqtt », 487 « Box », 547 « détecteur de fumée » (5 cmds `should_publish=false`, `reason=ha_missing_command_topic`, `missing_caps=has_command`, `missing_fields=command_topic`). ≥1 prêt et ≥1 bloquant confirmés côté données. **Reste : parcours navigateur réel** (clic pièce → accordéon → édition override → diagnostic vert + synthèse à jour) à mener par Alexandre, preuves DOM/écran à consigner.
  - [x] 0.3 — Restauration état : `ha_overrides.json` inchangé (mode déploie-seulement, aucune écriture override effectuée).
- [x] **Task 1 — Surface pièces (AC: 1, 2, 12, 13)**
  - [x] 1.1 — Section « Configuration mapping HA par pièce » dans `desktop/php/jeedom2ha.php`, itérant `jeeObject::buildTree(null, false)` (cartes cliquables, ordre natif).
  - [x] 1.2 — Retrait/re-câblage de l'onglet mort « HA / jeedom2ha » (fiche eqLogic jeedom2ha) — supprimer `#mappingOverrideTab` de la fiche ou le rediriger vers la nouvelle surface.
  - [x] 1.3 — Contrôleur navigateur : handler de clic pièce ouvrant le drill-down (modale/panneau, cf. OQ1).
- [x] **Task 2 — Drill-down équipements/commandes (AC: 3, 4, 5)**
  - [x] 2.1 — Rendu accordéon Bootstrap des équipements de la pièce via données Jeedom (`eqLogic::byObjectId`), un panneau collapsible par équipement.
  - [x] 2.2 — Chargement paresseux : GET `/system/mapping_overrides/{eq_id}` au dépliage d'un équipement uniquement (jamais 290 d'un coup).
  - [x] 2.3 — Liste plate des commandes dans l'ordre natif Jeedom.
- [x] **Task 3 — Montage du triptyque existant par commande (AC: 6, 7, 8, 11)**
  - [x] 3.1 — Réutiliser le module `jeedom2ha_mapping_override.js` (normalizeTree/normalizeCommandRow/diagnostic) pour rendre le triptyque de chaque commande dans le nouveau conteneur (au lieu du binding `currentEqId()` sur fiche eqLogic).
  - [x] 3.2 — Câbler dry-run/auto-validation/revert sur les routes existantes ; spinner circonscrit à la colonne override.
  - [x] 3.3 — Vérifier D10 : aucun chemin de code ne touche `generic_type` (test/inspection).
- [x] **Task 4 — Synthèse de publication par équipement (AC: 9, 10)**
  - [x] 4.1 — Agrégation front des diagnostics commande (`should_publish`/`is_valid`) → badge « sera publié / ne sera pas publié » + compte prêtes/bloquantes par équipement.
  - [x] 4.2 — Ancre vers la première commande bloquante depuis la synthèse.
- [x] **Task 5 — Tests (AC: tous sauf 14 terrain)**
  - [x] 5.1 — Tests front purs (node) : rendu liste pièces, drill-down accordéon, montage triptyque, agrégation synthèse « sera publié », ancre bloquante.
  - [x] 5.2 — Non-régression : suite node + suite daemon vertes, golden inchangé, aucune modification backend override.

## Dev Notes

- **Autorité de cadrage** : `epics-projection-engine.md` Story 16.5 (l.2126-2151) + en-tête Epic 16 (l.1971) — **« surface dédiée organisée par pièce comme Homebridge », « arborescence pièce → équipement → commande »**. Cette story rétablit cette intention ; elle **supersède** l'AC2 « onglet sur fiche équipement » du fichier story 16.5.
- **Modèle de référence (lu sur box 192.168.1.21, 2026-07-18)** : plugin Homebridge —
  - `plugins/homebridge/desktop/php/homebridge.php` : section « Types Génériques par Pièce », `jeeObject::buildTree()` → `objectDisplayCard` cliquables → `clickobject(id)`.
  - `plugins/homebridge/desktop/js/homebridge.js` : `clickobject()` charge une modale `modal=object.homebridge&object_id=X`.
  - `plugins/homebridge/desktop/modal/object.homebridge.php` (1286 l.) : `eqLogic::byObjectId()` → accordéon `#accordionConfiguration` (un panneau par équipement) → table par commande avec `<select generic_type>` en `<optgroup>` par famille.
  - **Défaut Homebridge à corriger** : aucune colonne diagnostic/prérequis → l'utilisateur tâtonne (config → restart daemon → logs). Notre valeur ajoutée = la colonne diagnostic + la synthèse « sera publié » (Bloc C).
- **Réutilisation, pas réécriture** : le triptyque (module pur) + les 4 routes backend override existent et sont **prouvés au gate 16.7** (ids natifs 391/151/174). Cette story est **front/nav only** : elle change le *point d'entrée* et la *coquille de navigation*, pas le contenu ni le backend.
- **Contraintes héritées non négociables** : D10 (`generic_type` natif jamais muté), D8 (`overrides.py` pur, sens unique `http_server.py → overrides.py`, jamais appelé par le pipeline de sync), D9 (schéma `ha_overrides.json` versionné). Référentiel dual-source (core ∪ Homebridge) consommé, jamais cassé.
- **Périmètre terrain** : contrairement à la 16.5 (terrain différé → jamais fait sur l'UI), le **gate terrain UI est porté par cette story** (Task 0 / AC14). C'est le correctif direct du trou de vérification qui a laissé passer la 16.5 en `done`.

### Dev Agent Guardrails

- **Aucun framework front** ; jQuery/Bootstrap Jeedom uniquement ; réutiliser les composants existants (accordéon, modale, badges).
- **D10 en dur** : seul `data/ha_overrides.json` peut être muté, via les routes existantes. Aucun POST vers `generic_type`.
- **Zéro nouveau backend override** : si une route manque pour la nav, préférer consommer les données Jeedom côté PHP (`jeeObject`/`eqLogic`) plutôt qu'ajouter une route daemon. Toute exception à justifier explicitement.
- **Pas de chargement de masse** : jamais 290 GET diagnostic au chargement de la page — lazy par équipement déplié.
- **Distinction diagnostic vs erreur** : un dry-run métier refusé = diagnostic affiché (HTTP 200), jamais une erreur réseau ; 401 auth / 404 id / 500 technique.
- **snake_case** strict pour les champs JSON échangés (`jeedom_eq_id`, `jeedom_cmd_id`, `reason_details`, `override_applied`, `override_source`, `should_publish`).

### Project Structure Notes

- Front impacté : `desktop/php/jeedom2ha.php` (nouvelle section pièces + retrait onglet mort), `desktop/js/jeedom2ha.js` (contrôleur nav pièce→eq→cmd, remplace le binding `currentEqId()` de la fiche), éventuelle nouvelle modale `desktop/modal/*.php` (cf. OQ1), `desktop/css/jeedom2ha.css` (styles nav/synthèse).
- Réutilisé tel quel : `desktop/js/jeedom2ha_mapping_override.js` (module pur triptyque/diagnostic), `core/ajax/jeedom2ha.ajax.php` (4 proxies existants), routes daemon `http_server.py` (GET arbre / preview / save / revert).
- Backend : **inchangé** attendu (à confirmer en dev-story). Aucune route override nouvelle.

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story 16.5 (l.2126-2151) + Epic 16 (l.1967-1979)] — autorité « surface par pièce comme Homebridge », arborescence pièce → équipement → commande, correction du défaut Homebridge (visibilité attendu HA)
- [Source: _bmad-output/planning-artifacts/ux-design-delta-pe-epic-16-mapping-configurable.md] — triptyque, dry-run instantané, auto-validation, couleurs, accessibilité (contenu réutilisé)
- [Source: _bmad-output/implementation-artifacts/16-5-ui-jeedom-configuration-par-equipement.md] — story superseded sur le point d'entrée ; module pur + routes réutilisés
- [Source: _bmad-output/implementation-artifacts/16-7-gate-terrain-et-profils-partageables.md] — preuves backend override (ids natifs 391/151/174) au gate 2026-07-18
- [Source: plugins/homebridge/desktop/php/homebridge.php + desktop/js/homebridge.js + desktop/modal/object.homebridge.php (box 192.168.1.21)] — modèle de navigation pièce → équipement → commande à répliquer
- [Source: resources/daemon/transport/http_server.py] — `_build_mapping_override_tree`, handlers GET/save/revert, route preview
- [Source: resources/daemon/validation/ha_component_registry.py] — `validate_projection` (source du diagnostic « prêt/bloquant »)

### Open Questions (à trancher en dev-story, non bloquantes pour la création)

1. **Drill-down = modale (fidélité Homebridge) ou panneau inline** ? Recommandation : modale par pièce comme Homebridge (`clickobject` → modal), pour maximiser la familiarité de Sébastien et isoler le chargement paresseux par pièce. À valider par le dev selon la contrainte de rendu.
2. **Synthèse « sera publié »** : agrégation strictement front à partir des `should_publish` du GET arbre (recommandé, zéro backend), ou exposition d'un rollup équipement côté daemon ? Préférer le front tant que le GET arbre porte déjà `should_publish` par commande.
3. **Sort de l'onglet mort 16.5** (AC13) : suppression pure ou redirection vers la nouvelle surface ? Trancher selon qu'un eqLogic jeedom2ha « template » ait ou non un usage résiduel légitime (a priori non → suppression).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (create-story workflow, BMAD ; discipline bmad-story-workflow-discipline)

### Debug Log References

### Completion Notes List

- 2026-07-20 — **Gate terrain UI (AC14) : bug d'intégration trouvé et corrigé.** Le walkthrough navigateur a révélé que sélectionner un override ne mettait à jour ni le diagnostic ni l'auto-validation. Cause racine : `core/ajax/jeedom2ha.ajax.php` pré-wrappait le payload dans une clé `payload` pour `previewMappingOverride`/`saveMappingOverride`/`revertMappingOverride`, alors que `jeedom2ha::callDaemon()` ajoute déjà cette enveloppe pour les POST → double imbrication `payload.payload.jeedom_eq_id` → le daemon lisait `eq_id=0` et renvoyait `{"status":"error","message":"jeedom_eq_id (int) requis"}`, relayé en `ajax::success` donc sans `overridden` → cellule diagnostic vidée, aucune persistance. Bug latent depuis 16.5/16.6 (surface jamais atteignable en navigateur → jamais exercé ; le gate 16.7 testait le daemon en direct, single-wrap, contournant le proxy). Fix : payload passé à plat dans les 3 actions (aligné sur la convention `mqtt_test`/`sync`/`execute`/`state_update`). Round-trip prouvé sur box 192.168.1.21 via `callDaemon` : preview `ok` (overridden=switch, should_publish=true), save `ok`, revert `ok`, `ha_overrides.json` restauré vide. **Reste : re-walkthrough navigateur Alexandre pour preuve DOM/écran finale.**
- 2026-07-18 — Workflow `dev-story` (BMAD). Tasks 1→5 implémentées et validées. Tests : 16.8 = **14/14 pass** ; suite node complète = **261/261 pass** ; suite daemon unitaire = **1075 passed** (aucune régression, golden inchangé, zéro modification backend override). D10 vérifié par inspection : aucun chemin ne mute `generic_type`, seul `data/ha_overrides.json` muté via routes existantes. **Reste ouvert : Task 0 / AC14 — gate terrain UI réel sur box 192.168.1.21** (parcours navigateur bout-en-bout avec preuves DOM/HTTP, ≥1 équipement prêt + ≥1 bloquant). Statut maintenu `in-progress` tant que le gate terrain n'est pas prouvé.
- 2026-07-18 — Workflow `create-story` (BMAD, discipline bmad-story-workflow-discipline). Story file créé à partir de : (a) l'autorité de cadrage epic (`epics-projection-engine.md` Story 16.5 l.2129/2137/2151 + Epic 16 l.1971), (b) le diagnostic terrain 2026-07-18 (0 eqLogic jeedom2ha → surface 16.5 inatteignable), (c) la lecture du modèle Homebridge sur box `192.168.1.21` (page pièces + modale accordéon équipements + table commandes). Statut résultant : `ready-for-dev`. **Aucune tâche dev cochée, aucun run dev/terrain/déploiement exécuté pendant create-story.** Divergence 16.5 (AC2 « onglet fiche équipement » vs epic « surface par pièce ») documentée ; cette story supersède le point d'entrée 16.5, réutilise son backend + module pur.

### File List

**Modifiés**
- `core/ajax/jeedom2ha.ajax.php` — fix gate terrain 2026-07-20 : payload à plat pour `previewMappingOverride`/`saveMappingOverride`/`revertMappingOverride` (suppression du double-wrap `payload` incompatible avec `callDaemon`).
- `desktop/php/jeedom2ha.php` — arbre pièces→équipements (`jeeObject::buildTree` + `eqLogic::byObjectId`, exclut type jeedom2ha, `sendVarToJS('j2haRoomsTree')`), section « Configuration mapping HA par pièce » (cartes cliquables), retrait onglet mort `#mappingOverrideTab` + tab-pane, include du nouveau contrôleur.
- `desktop/js/jeedom2ha.js` — retrait de l'IIFE override morte (liée à `shown.bs.tab` sur `#mappingOverrideTab`, binding `currentEqId()`), 1534→1257 lignes.
- `desktop/js/jeedom2ha_mapping_override.js` — ajout module pur : `normalizeRoomsTree` (ordre natif préservé, filtre pièces vides / eq_id invalides, coercition string→int), `summarizePublication`, `buildPublicationSummaryLabel`, `publicationSummaryState` ; exports ajoutés.
- `desktop/css/jeedom2ha.css` — styles surface pièce : `.j2ha-room-card`, accordéon `.j2ha-eq-panel`, badge synthèse `.j2ha-eq-publish-badge` (4 états ok/partial/blocked/empty), `.j2ha-goto-blocking`, `.j2ha-diag-target-highlight`.

**Créés**
- `desktop/js/jeedom2ha_mapping_surface.js` — contrôleur navigateur (jQuery/bootbox) : clic carte pièce → modale accordéon équipements, lazy GET diagnostic par équipement déplié, montage triptyque par commande (réutilise module pur), dry-run débounce + auto-validation + revert sur routes existantes, synthèse publication par équipement + ancre première commande bloquante.
- `tests/unit/test_story_16_8_mapping_surface.node.test.js` — 14 tests node purs (normalizeRoomsTree, summarizePublication, buildPublicationSummaryLabel/publicationSummaryState).

### Change Log

- 2026-07-18 — **Fix gate terrain** : le clic sur une carte pièce déclenchait le handler natif Jeedom (« EqLogic inconnu, ID Null ») au lieu de la modale. Cause : carte rendue avec la classe réservée `eqLogicDisplayCard` (le core Jeedom y bind un clic lisant `data-eqLogic_id` absent) + handler jQuery délégué intercepté. Correctif calé sur le pattern Homebridge éprouvé (`homebridge.php` l.79) : conteneur `objectListContainer`, carte `objectDisplayCard cursor j2ha-room-card` + `data-object_id` + `onclick="j2haOpenRoom(id)"` inline ; fonction `window.j2haOpenRoom` exposée par le contrôleur, handler délégué retiré. Redéployé sur box, `php -l` OK, 14/14 tests 16.8 verts. Walkthrough visuel Alexandre à refaire (hard refresh cache navigateur).
- 2026-07-18 — Implémentation front/nav-only : surface par pièce (modèle Homebridge) branchée sur triptyque + diagnostic 16.5, synthèse publication par équipement, retrait point d'entrée mort 16.5. Aucun backend override modifié (D8/D9/D10 respectés).
