# Story 4.5 : Atterrissage home — tableau hiérarchique unique, statut synthétique de pièce et point d'entrée vers diagnostic

Status: done

Epic: Epic 4 — Recadrage UX : modèle utilisateur Périmètre / Statut / Écart / Cause (correctif prioritaire post-rétro)

## Story

En tant qu'utilisateur de la home V1.1,  
je veux que la zone centrale soit un tableau hiérarchique unique de synthèse et de pilotage où chaque ligne pièce porte un statut synthétique de pièce contractuel, affiché dans le domaine fermé `Publiee / Partiellement publiee / Non publiee`, distinct du diagnostic,  
afin de comprendre immédiatement l'état du parc sans que le frontend invente sa propre logique métier locale.

## Contexte / Objectif produit

Cette story ouvre le paquet correctif prioritaire post-rétro Epic 4 en restaurant **la responsabilité de la home uniquement**.

Constat verrouillé au démarrage :

1. Le fond technique Epic 4 est validé et **n'est pas à rouvrir** :
   - modèle 4D conservé ;
   - backend source de vérité conservé ;
   - sortie du vocabulaire legacy conservée ;
   - Epic 5 gelé ;
   - aucun mélange avec les opérations HA Epic 5.
2. Le défaut restant est d'atterrissage UX/UI :
   - la home ne joue pas encore assez clairement son rôle de synthèse/pilotage ;
   - la zone centrale actuelle expose encore une explicabilité inline qui brouille la frontière avec le diagnostic ;
   - `ux-spec.md` V3 fixe désormais une cible contractuelle non négociable ;
   - `ux-spec.md` clarifie explicitement que le badge / la colonne `Statut` au niveau pièce est un **indicateur synthétique de pièce**, distinct du statut 4D équipement, non recalculable implicitement côté JS, et attendu dans le domaine contractuel `Publiee / Partiellement publiee / Non publiee`.

Cette story doit donc :

- conserver le shell home actuel ;
- retravailler **uniquement** la zone centrale ;
- produire un tableau hiérarchique unique `Parc global -> pièces -> équipements` ;
- rendre la ligne pièce lisible par un signal synthétique `Statut` de pièce propre à la home, limité au domaine contractuel `Publiee / Partiellement publiee / Non publiee` ;
- rendre les badges `Écart` exploitables comme point d'entrée vers le diagnostic, sans afficher de diagnostic inline ;
- absorber **dans ce même périmètre** le delta de contrat minimal strictement nécessaire à la home si `Publies` et/ou le signal synthétique `Statut` pièce ne sont pas déjà fournis par la réponse console ;
- interdire toute recomposition locale du `Statut` pièce à partir des lignes équipement, des compteurs ou du diagnostic.

## Objectif produit

Faire percevoir en moins de 3 secondes que :

- `home = synthèse et pilotage du parc` ;
- la ligne pièce porte un **statut synthétique de pièce** propre à la home, dans le domaine `Publiee / Partiellement publiee / Non publiee` ;
- les écarts se repèrent dans la home ;
- l'explication détaillée d'un cas vit ailleurs, dans le diagnostic.

## Scope

### In scope

1. Conservation du shell home existant : bandeau `Sante`, actions `Home Assistant`, export support, menu plugin.
2. Remplacement de la zone centrale par un **tableau hiérarchique unique**.
3. Vue par défaut limitée à une seule ligne visible : `Parc global`.
4. Dépliage hiérarchique `Parc global -> pièces -> équipements` dans le même tableau.
5. Colonnes home exactes et ordonnées : `Nom / Perimetre / Statut / Ecart / Total / Exclus / Inclus / Publies / Ecarts`.
6. Lignes pièce avec 3 colonnes badges fixes (`Perimetre / Statut / Ecart`) et 5 colonnes chiffrées.
7. `Statut` pièce traité comme **signal synthétique de pièce home-only**, jamais comme extension libre du statut 4D équipement, avec domaine d'affichage contractuel exact `Publiee / Partiellement publiee / Non publiee`.
8. Consommation directe du contrat existant pour `Publies` et pour le signal synthétique `Statut` pièce si ces données sont déjà disponibles et validées, sans remapping local des valeurs.
9. Si nécessaire, absorption d'un **delta minimal borné** pour fournir uniquement :
   - `Publies`
   - le signal synthétique `Statut` pièce
10. Lignes équipement avec lecture de synthèse uniquement, sans surface diagnostic inline.
11. Infobulle courte sur badge `Ecart` équipement, si et seulement si `ecart=true`.
12. Badge `Ecart` équipement rendu comme **unique point d'entrée** vers le diagnostic depuis la zone centrale home.

### Out of scope

| Élément hors scope | Responsable / remarque |
|---|---|
| Refonte de la grande modal diagnostic | Story 4.6 |
| Scroll, dépliage automatique et focus temporaire dans le diagnostic | Story 4.6 |
| Refonte du détail commandes diagnostic existant | Interdit |
| Refonte du modèle 4D, des compteurs backend historiques, du vocabulaire legacy | Hors scope, acquis Epic 4 |
| Toute logique Epic 5 (`Republier`, `Supprimer/Recréer`, confirmations HA) | Epic 5 gelé |
| Recalcul frontend implicite de `Publies`, du `Statut` pièce, de `Statut`, `Ecart` ou `Cause` | Interdit |
| Construction d'un pseudo-`Statut` pièce à partir des lignes équipement, des compteurs ou de la modal diagnostic | Interdit |
| Tout delta de contrat au-delà de `Publies` et du signal synthétique `Statut` pièce | Interdit |
| Nouvelle surface diagnostic théorique dans la home | Interdit |

## Dépendances autorisées

- Story 4.1 — `done` : contrat backend 4D stabilisé.
- Story 4.2 — `done` : vocabulaire d'exclusion par source et compteurs canoniques stabilisés.
- Story 4.3 — `done` : diagnostic in-scope, confiance limitée au diagnostic, export complet préservé.
- Story 4.4 — `done` : lecture UI 4D native désormais disponible côté UI, mais à reposer sur la bonne responsabilité de surface.
- Les artefacts amont qui figent la clarification `Statut` pièce :
  - `ux-delta-review-post-mvp-v1-1-pilotable.md` — statut équipement uniquement au niveau équipement, pièce lue par synthèse ;
  - `ux-spec.md` V3 — badge `Statut` pièce = indicateur synthétique de pièce, non déductible librement côté JS.
- `ux-spec.md` V3 — référence d'acceptation principale pour ce correctif.

Aucune dépendance Epic 5.  
Aucune dépendance en avant autre que la consommation ultérieure du point d'entrée badge `Ecart` par la Story 4.6.  
Le signal synthétique `Statut` pièce reste de responsabilité **home-only** et n'introduit aucune dépendance supplémentaire côté diagnostic.

## Acceptance Criteria

### AC 1 — Shell home conservé, zone centrale remplacée uniquement

**Given** la page home du plugin  
**When** la story est livrée  
**Then** le shell existant est conservé :
- bandeau `Sante`
- actions `Home Assistant`
- export support
- menu plugin

**And** seule la zone centrale est restructurée  
**And** la vue initiale n'affiche qu'une seule ligne visible : `Parc global`

### AC 2 — Tableau hiérarchique unique conforme au contrat visuel

**Given** la zone centrale home  
**When** l'utilisateur ouvre `Parc global`, puis une pièce  
**Then** le rendu reste dans un **même tableau hiérarchique unique**  
**And** les colonnes sont exactement :
- `Nom`
- `Perimetre`
- `Statut`
- `Ecart`
- `Total`
- `Exclus`
- `Inclus`
- `Publies`
- `Ecarts`

**And** l'ordre des colonnes chiffrées reste exactement `Total / Exclus / Inclus / Publies / Ecarts`

### AC 3 — Lecture home bornée par niveau

**Given** la home dépliée au niveau pièce  
**When** une ligne pièce est rendue  
**Then** elle affiche uniquement :
- 3 badges fixes `Perimetre / Statut / Ecart`
- 5 colonnes chiffrées

**And** aucune cause n'apparaît au niveau pièce

**Given** une ligne équipement home  
**When** elle est rendue  
**Then** elle reste une lecture de synthèse :
- `Perimetre`
- `Statut`
- `Ecart`
- colonnes chiffrées

**And** elle n'affiche aucun panneau, bloc ou sous-surface diagnostic inline

### AC 4 — `Statut` pièce = signal synthétique home-only, domaine fermé, non recomposé

**Given** une ligne pièce home  
**When** la colonne / le badge `Statut` est affiché  
**Then** elle affiche un **signal synthétique de pièce** propre à la home  
**And** ce signal ne constitue pas une extension libre du statut 4D équipement  
**And** il reste distinct de la colonne `Statut` du diagnostic
**And** son domaine de valeurs attendu est exactement :
- `Publiee`
- `Partiellement publiee`
- `Non publiee`

**And** le frontend n'invente aucune autre valeur locale pour le `Statut` pièce

**Given** un fixture de test où :
- le contrat consommé par la home fournit un `Statut` pièce explicite
- les lignes équipement permettraient une agrégation naïve différente

**When** la home est rendue  
**Then** le frontend affiche **le signal explicite du contrat/relay**  
**And** il ne le remplace pas par une recomposition locale à partir des équipements

**Given** un fixture où la source contractuelle validée fournit successivement :
- `Publiee`
- `Partiellement publiee`
- `Non publiee`

**When** la home est rendue  
**Then** chaque valeur est affichée telle quelle  
**And** elle n'est ni remappée ni normalisée vers un autre libellé local

### AC 5 — `Publies` et `Statut` pièce issus d'une source backend / relay validée

**Given** la colonne `Publies` et le signal synthétique `Statut` pièce requis par `ux-spec.md`  
**When** la home les affiche  
**Then** ils proviennent :
- soit du contrat déjà consommé par la home s'il est suffisant ;
- soit d'un delta minimal backend / relay ajouté explicitement pour ces deux signaux uniquement

**And** le JS ne recalcule pas localement `Publies`
**And** le JS ne recompose pas librement le `Statut` pièce
**And** le JS ne remappe pas librement `Publiee`, `Partiellement publiee` ou `Non publiee`
**And** le JS ne dérive pas un pseudo-contrat local depuis les équipements ou depuis la modal diagnostic

### AC 6 — Dégradation contrôlée si un signal contractuel manque

**Given** un rendu home où `Publies` ou le `Statut` pièce n'est pas présent dans la donnée consommée  
**When** le frontend affiche la ligne concernée  
**Then** il rend un état neutre / vide explicite  
**And** il ne déclenche aucun fallback de recalcul métier local  
**And** il n'introduit aucune valeur de `Statut` pièce hors du domaine contractuel attendu

### AC 7 — Signaux interdits absents de la home

**Given** n'importe quel état de la home  
**When** l'utilisateur lit la zone centrale  
**Then** il ne voit jamais dans la home :
- `Confiance`
- `Raison` détaillée
- `reason_code`
- détail commandes
- typage
- résumé diagnostic inline
- nouvelle fiche théorique de diagnostic

**And** le badge orange `Changements à appliquer` ne réapparaît pas dans la zone centrale home

### AC 8 — Badge `Ecart` sobre et infobulle courte uniquement au niveau équipement

**Given** une ligne équipement avec `ecart=true`  
**When** la home est affichée  
**Then** le badge `Ecart` est visible et identifiable  
**And** une infobulle courte expose uniquement :
- la cause courte
- l'invitation à voir le diagnostic pour le détail

**Given** une ligne équipement avec `ecart=false`  
**When** la home est affichée  
**Then** aucune infobulle de cause n'est exposée

### AC 9 — Point d'entrée diagnostic unique depuis la home

**Given** une ligne équipement home avec `ecart=true`  
**When** l'utilisateur clique le badge `Ecart`  
**Then** la home ne s'ouvre jamais en diagnostic inline  
**And** le clic porte un identifiant cible stable (`eq_id`) vers l'ouvreur partagé du diagnostic  
**And** aucun autre CTA diagnostic n'apparaît dans la zone centrale home au niveau pièce ou équipement

### AC 10 — Invariant exclus visibles en home

**Given** un équipement exclu  
**When** la home est affichée  
**Then** il reste visible dans le tableau home  
**And** il participe aux compteurs home  
**And** cette story ne réintroduit aucun diagnostic standard pour les exclus

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — N/A micro-correctif UX local (accord utilisateur)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story (N/A) :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.` (N/A)

- [x] Task 1 — Borne contractuelle home minimale si nécessaire (AC: 2, 5)
  - [x] Auditer les données déjà disponibles dans `published_scope`, `diagnostic_summary`, `diagnostic_rooms` et `diagnostic_equipments` pour `Publies` et pour le `Statut` synthétique de pièce, y compris le **domaine de valeurs réellement servi** pour ce `Statut` pièce.
  - [x] Confirmer si la home peut **consommer directement** un signal déjà valide pour `Publies` et pour le `Statut` pièce, avec les valeurs contractuelles exactes `Publiee / Partiellement publiee / Non publiee`.
  - [x] Si le contrat existant est suffisant, consommer ces valeurs telles quelles sans surcouche JS.
  - [x] Si le contrat existant ne suffit pas, ajouter un **delta minimal borné** dans la couche la plus proche de la console (`core/ajax/jeedom2ha.ajax.php` en priorité, daemon uniquement si indispensable), limité à :
    - `Publies`
    - le signal synthétique `Statut` pièce servi exactement dans le domaine `Publiee / Partiellement publiee / Non publiee`
  - [x] Interdire explicitement tout recalcul JS local de `Publies` et du `Statut` pièce.
  - [x] Interdire explicitement tout remapping JS local du domaine de valeurs `Publiee / Partiellement publiee / Non publiee`.
  - [x] Ajouter ou mettre à jour les tests de contrat/relay correspondants.

- [x] Task 2 — Remodeler le modèle home et le rendu hiérarchique (AC: 1, 2, 3, 4, 10)
  - [x] Remplacer dans `desktop/js/jeedom2ha_scope_summary.js` le rendu actuel par un tableau hiérarchique unique conforme à `ux-spec.md` V3.
  - [x] Afficher uniquement `Parc global` au chargement initial.
  - [x] Gérer le dépliage `Parc global -> pièces -> équipements` sans créer de seconde surface dans la zone centrale.
  - [x] Brancher la ligne pièce sur un signal synthétique `Statut` consommé depuis le contrat/relay, sans agrégation locale des statuts équipement et sans remapping local du domaine `Publiee / Partiellement publiee / Non publiee`.
  - [x] Conserver le mécanisme de restauration d'état de navigation déjà présent dans `desktop/js/jeedom2ha.js`.

- [x] Task 3 — Supprimer toute explicabilité inline de la home (AC: 3, 6, 7)
  - [x] Retirer les blocs `Console principale`, `Diagnostic utilisateur` et `Diagnostic technique détaillé` actuellement injectés inline dans la home.
  - [x] Réinjecter les informations 4D de la home dans des cellules et badges du tableau, pas dans des sous-surfaces.
  - [x] Vérifier qu'aucun détail diagnostic, `Confiance`, `Raison` détaillée ou couverture commandes ne subsiste dans la home.
  - [x] Si `Publies` ou le `Statut` pièce manque temporairement dans la donnée consommée, rendre un état neutre sans pseudo-contrat frontend.

- [x] Task 4 — Rendre le badge `Ecart` home exploitable comme point d'entrée (AC: 8, 9)
  - [x] Rendre le badge `Ecart` équipement cliquable uniquement quand `ecart=true`.
  - [x] Ajouter l'infobulle courte contractuelle sur ce badge uniquement.
  - [x] Porter dans le DOM l'identifiant cible stable attendu par le diagnostic (`eq_id`) sans ouvrir de contenu inline.
  - [x] Vérifier qu'aucun autre CTA diagnostic n'existe dans la zone centrale home.

- [x] Task 4.5 — Micro-correctif UX terrain résiduel (P1.3, P1.6)
  - [x] Ajouter un curseur main + hover discret sur le badge `Ecart` sans soulignement.
  - [x] Stabiliser l'alignement des colonnes au dépliage des pièces.

- [x] Task 5 — Tests story-level et gate terrain (AC: 1 à 10)
  - [x] Créer `tests/unit/test_story_4_5_home_landing.node.test.js` pour couvrir le tableau hiérarchique, les colonnes exactes, l'absence de diagnostic inline, le badge `Ecart`, l'invariant exclus visibles et l'absence de recalcul frontend implicite.
  - [x] Ajouter un test story-level qui échoue si la cellule `Perimetre` pièce retombe à `—`, si le badge `Perimetre` pièce disparaît, ou si les 3 badges fixes pièce ne sont plus présents.
  - [x] Ajouter un cas de test pour chacun des trois libellés contractuels `Publiee`, `Partiellement publiee` et `Non publiee`, afin de prouver qu'ils sont affichés tels quels.
  - [x] Ajouter un cas de test où le `Statut` pièce explicite contredit une agrégation naïve des lignes équipement, pour prouver que le frontend suit la source contractuelle.
  - [x] Ajouter un cas de test où la source fournit l'un des trois libellés contractuels et où un remapping frontend hypothétique vers une autre valeur ferait échouer le test.
  - [x] Ajouter un cas de test où `Publies` explicite contredit un comptage naïf des lignes équipement, pour prouver l'absence de recalcul JS.
  - [x] Ajouter un cas de test où un signal manque et produit un état neutre plutôt qu'une recomposition locale.
  - [x] Ajouter un cas de test où une valeur non contractuelle ne doit jamais être introduite par l'UI locale.
  - [x] Mettre à jour les suites existantes impactées (`tests/unit/test_scope_summary_presenter.node.test.js`, `tests/unit/test_story_4_4_integration_ui_4d.node.test.js`) sans casser les acquis 4.2/4.3/4.4.
  - [x] Si Task 1 touche la couche relay/backend, ajouter le test PHP ou Python minimal correspondant.
  - [x] Ajouter un test relay/backend qui prouve le passthrough d'un champ dédié de `Statut` pièce, l'absence de recomposition depuis `diagnostic_equipments`, et le fallback neutre si ce champ dédié manque.
  - [x] Exécuter la checklist terrain `ux-spec.md` section 10.2 sur home vs diagnostic avant passage à `done`.

## Dev Notes

### Contraintes `ux-spec.md` à intégrer explicitement

1. `home = synthese et pilotage du parc`.
2. Le shell home est conservé ; seule la zone centrale change.
3. La home par défaut ne montre que `Parc global`.
4. Le tableau central est unique, hiérarchique, sans blocs parallèles.
5. Les colonnes home sont figées et ordonnées.
6. La ligne pièce porte un `Statut` **synthétique de pièce**, distinct du statut 4D équipement et distinct du `Statut` de la modal diagnostic, avec domaine contractuel exact `Publiee / Partiellement publiee / Non publiee`.
7. Le `Statut` pièce ne peut pas être inféré librement côté JS à partir des équipements, des compteurs ou du diagnostic, ni remappé vers un autre domaine de valeurs local.
8. `Confiance`, `Raison` détaillée, `reason_code`, typage et détails commandes sont interdits en home.
9. Le badge `Ecart` équipement est le seul point d'entrée diagnostic dans la zone centrale.
10. Les exclus restent visibles en home.
11. `Publies` ne peut jamais être recalculé implicitement côté frontend.
12. Si un delta de contrat est nécessaire, il est strictement borné à `Publies` et au signal synthétique `Statut` pièce.

### Notes d'architecture / design

1. Le fichier principal de rendu home à corriger reste `desktop/js/jeedom2ha_scope_summary.js`.
2. `desktop/js/jeedom2ha.js` conserve déjà :
   - le refresh périodique ;
   - la capture/restauration de l'état de navigation ;
   - le point d'intégration vers la grande modal diagnostic existante.
3. Le diagnostic actuel vit déjà dans une grande modal distincte de `desktop/js/jeedom2ha.js` ; cette story ne doit pas en dupliquer les contenus ni réutiliser sa logique de `Statut`.
4. Le `Statut` pièce home doit être consommé comme **signal contractuel dédié**, servi dans le domaine fermé `Publiee / Partiellement publiee / Non publiee` ; il ne doit pas être recomposé ni remappé depuis :
   - les statuts équipement ;
   - les compteurs ;
   - `diagnostic_rooms.summary.primary_aggregated_status` ou toute autre donnée non explicitement validée pour la home.
5. Si un delta de contrat est requis, préférer une extension bornée de la réponse console/relay plutôt qu'une refonte du daemon.
6. Cette extension bornée ne peut couvrir que :
   - `Publies`
   - le signal synthétique `Statut` pièce
7. La story doit **défaire le rendu inline introduit par 4.4** sans casser la lecture stricte backend des champs 4D.

### Previous Story Intelligence

1. Story 4.4 a correctement fait passer l'UI en lecture 4D native, mais sous une forme désormais non conforme à `ux-spec.md` V3 car trop proche d'une explicabilité inline.
2. Les champs backend 4D (`perimetre`, `statut`, `ecart`, `cause_label`, `cause_action`) sont déjà présents et doivent être réutilisés sans nouveau mapping local.
3. Le commit récent `e2c59a8` a posé le rendu 3 surfaces inline ; cette story doit le transformer, pas réouvrir le contrat 4D.
4. La clarification la plus récente sur le `Statut` pièce ne doit plus laisser au développeur la liberté d'inventer une agrégation JS implicite.

### Git Intelligence Summary

- `e2c59a8 feat(story-4.4): integrer l'UI du nouveau modele console et diagnostic`
- `8c57808 feat(story-4.3): freeze tested terrain candidate`

Lecture utile :
- 4.4 a surtout déplacé le sens métier dans le frontend de présentation ;
- le correctif demandé ici concerne la responsabilité de surface, pas la sémantique backend ;
- le delta doit rester concentré sur la home et son contrat minimal de rendu ;
- la nouvelle ambiguïté à lever est strictement limitée à `Publies` et au `Statut` synthétique de pièce.

## Impacts backend vs frontend

| Couche | Impact attendu | Fichiers candidats |
|---|---|---|
| Frontend JS | Refactor majeur du rendu home hiérarchique, consommation stricte de `Publies` et du `Statut` synthétique de pièce, suppression des surfaces inline, badge `Ecart` cliquable | `desktop/js/jeedom2ha_scope_summary.js`, `desktop/js/jeedom2ha.js` |
| PHP relay | Extension minimale si `Publies` et/ou le signal synthétique `Statut` pièce manquent dans la réponse console ; aucun autre enrichissement autorisé | `core/ajax/jeedom2ha.ajax.php` |
| Backend Python | Aucun changement par défaut ; autorisé uniquement si le relay ne peut pas servir proprement `Publies` et/ou le signal synthétique `Statut` pièce | `resources/daemon/transport/http_server.py` |
| Tests JS | Nouveaux tests home + ajustement non-régression des suites existantes | `tests/unit/` |
| Tests PHP/Python | Seulement si la Task 1 modifie le contrat relay/backend | `tests/`, `resources/daemon/tests/unit/` |

## Stratégie de test story-level

### Invariants à couvrir

- I10 — contrat backend → UI 4D lu sans interprétation locale.
- I12 — lecture piece/global par compteurs backend, sans recalcul frontend.
- I14 — exclus visibles en home, hors diagnostic standard.
- I15 — confiance absente de la home.
- I17 — frontend en lecture seule.
- Le `Statut` pièce est un signal synthétique home-only distinct du `Statut` diagnostic.
- Le domaine de valeurs du `Statut` pièce affiché en home est limité à `Publiee / Partiellement publiee / Non publiee`.
- Invariants visuels `ux-spec.md` section 7 sur la séparation home/diagnostic.

### Tests unitaires obligatoires

- La vue initiale home n'affiche que `Parc global`.
- Le tableau hiérarchique porte exactement les 9 colonnes attendues.
- L'ordre des colonnes chiffrées est `Total / Exclus / Inclus / Publies / Ecarts`.
- Les lignes pièce affichent 3 badges fixes et aucune cause.
- Le `Statut` pièce affiché provient du contrat/relay et non d'une agrégation locale des lignes équipement.
- Le `Statut` pièce peut afficher `Publiee`, `Partiellement publiee` et `Non publiee`.
- Si la source contractuelle fournit `Publiee`, `Partiellement publiee` ou `Non publiee`, le frontend les affiche telles quelles.
- Aucune valeur non contractuelle de `Statut` pièce n'est introduite par l'UI locale.
- Les lignes équipement n'affichent aucun bloc diagnostic inline.
- `Confiance`, `reason_code`, couverture commandes et détails techniques sont absents du rendu home.
- Le badge `Ecart` est cliquable uniquement pour `ecart=true`.
- Les exclus restent visibles dans la home.
- Si `Publies` ou le `Statut` pièce manque, le rendu reste neutre plutôt que de recomposer un signal local.

### Tests de contrat / non-régression obligatoires

- Si `Publies` est ajouté/relayé, preuve qu'il vient d'une donnée backend/relay et non d'un recalcul JS.
- Si le `Statut` pièce est ajouté/relayé, preuve qu'il vient d'une donnée backend/relay dédiée et non d'une agrégation JS des équipements.
- Si le `Statut` pièce est fourni comme `Publiee`, `Partiellement publiee` ou `Non publiee`, preuve qu'il traverse le frontend sans remapping.
- Si un delta minimal est introduit, preuve qu'il ne couvre rien d'autre que `Publies` et le signal synthétique `Statut` pièce.
- Non-régression des acquis 4.2/4.3/4.4 : contrat 4D toujours lu en passthrough.
- Non-régression du refresh/rendu home quand le daemon est indisponible.

### Gate terrain obligatoire avant `done`

- Vérifier la checklist `ux-spec.md` section 10.2 pour la home.
- Vérifier en terrain qu'un utilisateur identifie en moins de 3 secondes :
  - que la home synthétise/pilote ;
  - où se trouvent les écarts ;
  - qu'il doit passer par le diagnostic pour le détail.

## Guardrails anti-dérive

1. Pas de dérive vers Epic 5.
2. Pas de réouverture du modèle 4D.
3. Pas de réouverture des compteurs backend historiques.
4. Pas de réintroduction du vocabulaire legacy.
5. Pas de recalcul métier implicite dans le frontend.
6. Pas de pseudo-contrat local home construit à partir des équipements ou du diagnostic.
7. Pas de recomposition JS du `Statut` pièce.
8. Pas de recalcul JS de `Publies`.
9. Pas d'invention locale de nouvelles valeurs de `Statut` pièce.
10. Pas de remapping frontend libre du domaine de valeurs `Publiee / Partiellement publiee / Non publiee`.
11. Pas de seconde surface diagnostic dans la home.
12. Pas de duplication confuse home / diagnostic.
13. Pas de badge ou panneau home donnant accès au détail commandes.
14. Pas de mini-refonte daemon si un relay borné suffit.
15. Pas de delta de contrat au-delà de `Publies` et du signal synthétique `Statut` pièce.

## Définition de done

- [x] AC 1 à AC 10 validés.
- [x] La home par défaut ne montre que `Parc global`.
- [x] Le tableau hiérarchique unique remplace les surfaces inline.
- [x] Les colonnes home sont exactes et ordonnées.
- [x] Le `Statut` pièce est servi et affiché comme signal synthétique contractuel home-only, dans le domaine exact `Publiee / Partiellement publiee / Non publiee`.
- [x] `Publies` est servi proprement sans recalcul frontend implicite.
- [x] Le frontend ne recompose ni le `Statut` pièce ni `Publies`, et ne remappe pas le domaine de valeurs du `Statut` pièce.
- [x] Le badge `Ecart` est le seul point d'entrée diagnostic depuis la zone centrale home.
- [x] Les exclus restent visibles en home.
- [x] La checklist terrain `ux-spec.md` section 10.2 est positive avant `done`.

## References

- `_bmad-output/planning-artifacts/active-cycle-manifest.md` — sections 4, 6, 8.
- `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md` — sections 6, 8.1, 8.3, 9, 12.
- `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md` — sections 5.2, 5.6, 6.2, 8.1, 8.2, 8.3.
- `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md` — sections 8.1, 8.4, 8.5, 8.7.
- `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md` — sections 4, 6, 7, 9.
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-29.md` — sections 4, 5.3, 6.
- `_bmad-output/implementation-artifacts/epic-4-retro-2026-03-29.md` — sections `Verdict`, `Action items validés / AI-2`, `AI-3`, `Chemin critique validé`.
- `_bmad-output/implementation-artifacts/4-4-integration-ui-du-nouveau-modele-console-et-diagnostic.md` — sections `Points de vigilance challengés et décisions retenues`, `Impact backend vs frontend`, `Guardrails anti-dérive`.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — bloc Epic 4 post-rétro.
- `_bmad-output/planning-artifacts/ux-spec.md` — sections 2, 3.2, 4.1, 4.3, 4.4, 5.2, 5.3, 6.1, 6.2, 6.3, 7, 8, 9.2, 9.3, 10, 11, 12.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex (CLI)

### Debug Log References

- `./scripts/deploy-to-box.sh --dry-run` (PASS — SSH/sudo OK, simulation rsync OK, aucun transfert effectif)
- `node --check desktop/js/jeedom2ha_scope_summary.js`
- `node --check desktop/js/jeedom2ha.js`
- `php -l core/ajax/jeedom2ha.ajax.php`
- `node --test tests/unit/test_scope_summary_presenter.node.test.js tests/unit/test_story_4_4_integration_ui_4d.node.test.js tests/unit/test_story_4_5_home_landing.node.test.js tests/unit/test_story_4_2_vocab_exclusion.node.test.js tests/unit/test_story_4_3_diagnostic_in_scope.node.test.js tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js` (PASS — 37/37)
- `php tests/test_php_export_diagnostic_coherence.php` (PASS)
- `php tests/test_php_story_4_5_home_signals.php` (PASS)
- `python3 -m pytest resources/daemon/tests/unit/test_ui_contract_4d.py resources/daemon/tests/unit/test_diagnostic_endpoint.py tests/unit/test_published_scope_http.py` (PASS — 76/76, warnings)
- `php tests/test_php_published_scope_relay.php` (FAIL — core/php/core.inc.php introuvable en local)
- `node --test tests/unit/test_story_4_5_home_landing.node.test.js` (PASS — 10/10)
- `node --test tests/unit/test_story_4_5_home_landing.node.test.js` (PASS — 15/15)
- `node --test tests/unit/test_story_4_5_home_landing.node.test.js` (PASS — 16/16)
- `node --test tests/unit/test_scope_summary_presenter.node.test.js tests/unit/test_story_4_4_integration_ui_4d.node.test.js tests/unit/test_story_4_5_home_landing.node.test.js tests/unit/test_story_4_2_vocab_exclusion.node.test.js tests/unit/test_story_4_3_diagnostic_in_scope.node.test.js tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js` (PASS — 43/43)
- `node --test tests/unit/test_story_4_5_home_landing.node.test.js tests/unit/test_scope_summary_presenter.node.test.js` (PASS — 22/22)

### Terrain Feedback Log

- 2026-03-30 — test box réelle, extraction du payload servi à la home via `getPublishedScopeForConsole` + `/system/diagnostics`.
- Constat terrain confirmé : le `Perimetre` pièce actuellement exposé en home est dérivé dans le relay à partir de `published_scope.pieces[].counts.include/exclude`, puis relayé dans `home_signals.pieces[].perimetre`.
- Retour produit explicite : cette provenance est jugée insuffisante pour distinguer proprement :
  - une pièce explicitement exclue ;
  - une pièce incluse dont tous les équipements sont exclus individuellement.
- Attente produit exprimée : le `Perimetre` pièce devrait venir d'une décision de configuration / résolution propre à la pièce, pas d'une simple déduction "tous les équipements sont exclus".
- Constat terrain confirmé : le `Statut` pièce dédié `home_statut` n'est pas servi sur la box testée (`diagnostic_summary.home_statut = null` et `diagnostic_rooms[].home_statut = null`), ce qui provoque correctement un rendu neutre côté home.
- Attente produit exprimée pour le `Statut` pièce : règle backend / relay explicite calculée sur les équipements `inclus` uniquement :
  - tous les inclus sont publiés => `Publiee`
  - au moins un inclus publié et au moins un inclus non publié => `Partiellement publiee`
  - sinon => `Non publiee`
- Amélioration UX demandée pour les lignes équipement : éviter l'affichage binaire brut `0/1` dans les colonnes chiffrées quand la ligne représente un seul équipement ; préférence exprimée pour un rendu plus lisible de type `case vide` pour `0` et `coche` pour `1`, potentiellement sur toutes les colonnes binaires au niveau équipement.
- Qualification terrain au 2026-03-30 :
  - `Publies` : provenance relay/backend apparente confirmée ; pas de recalcul JS observé.
  - `Perimetre` pièce : rendu exploitable mais sémantique produit/contrat jugée non suffisamment fondée tant que la source reste une déduction par compteurs.
  - `Statut` pièce : contrat nominal non démontrable sur la box testée tant que le signal dédié reste absent.
- Conséquence méthodologique : la checklist terrain visuelle peut continuer pour qualifier le rendu home 4.5, mais toute conclusion finale doit rester `sous réserve produit/contrat` tant que cet écart n'est pas arbitré ou corrigé.
- 2026-03-30 — test terrain express final Story 4.5 (home) :
  - OK : home = synthèse/pilotage ; vue initiale `Parc global` ; tableau hiérarchique unique ; badges `Perimetre / Statut / Ecart` présents ; couleurs/contrastes badges OK ; badge/texte `Contrat backend` absent ; rendu binaire équipement lisible (`vide / coche`) ; clic `Ecart` ouvre bien le diagnostic dédié (pas d'inline).
  - KO : auto-refresh toujours présent.
  - Réserve mineure : badge `Ecart` cliquable mais soulignement jugé peu cohérent (préférence hover main).
  - Verdict terrain : `OK 4.5 avec réserve mineure`.
- 2026-03-30 — re-test terrain post-correctif (UX résiduel) :
  - OK : auto-refresh supprimé ; soulignement du badge `Ecart` supprimé.
  - KO : badge `Ecart` sans curseur main au survol.
  - KO : dépliage d'une pièce décale encore les colonnes.
- 2026-03-30 — re-test terrain final post-micro-correctifs UX :
  - OK : badge `Ecart` avec curseur main + hover discret.
  - OK : alignement des colonnes stable au dépliage.
  - OK : gate terrain `ux-spec.md` 10.2 validée.
  - Verdict final : test terrain OK.

### Plan De Correction Priorisé Post-Test Terrain

- `P0 — Réserves contrat bloquantes avant done`
  - `P0.1` `Perimetre` pièce : ne plus le dériver seulement depuis `include/exclude` ; le faire venir d'une décision pièce explicite côté backend/relay, afin de distinguer :
    - une pièce explicitement exclue ;
    - une pièce incluse dont tous les équipements finissent exclus.
  - `P0.2` `Statut` pièce : servir un `home_statut` dédié côté backend/relay.
  - `P0.3` Règle produit exprimée pour `home_statut` : calcul sur les seuls équipements `inclus` :
    - tous les inclus sont publiés => `Publiee`
    - au moins un inclus publié et au moins un inclus non publié => `Partiellement publiee`
    - sinon => `Non publiee`
  - `P0.4` Refaire après correction la preuve terrain payload + home sur `Perimetre` pièce et `Statut` pièce.
- `P1 — Écarts UX à corriger`
  - `P1.1` Retirer le badge `Contrat backend` et la phrase d'aide résiduelle sous le tableau.
  - `P1.2` Supprimer l'auto-refresh périodique et conserver le bouton `Rafraîchir` comme point d'action explicite.
  - `P1.3` Rendre le badge `Ecart` visiblement cliquable.
  - `P1.4` Corriger la sémantique/couleur des badges : `Exclue` gris ; `Aligné/Alignée` vert.
  - `P1.5` Harmoniser le contraste des badges gris.
  - `P1.6` Réduire le décalage horizontal inutile lors du dépliage.
- `P2 — Améliorations UX non bloquantes`
  - `P2.1` Remplacer les `0/1` des lignes équipement par un rendu plus lisible, par exemple `vide / coche`.
  - `P2.2` Harmoniser plus finement la lecture visuelle des colonnes binaires au niveau équipement.
- Lecture de priorisation :
  - `P0` bloque un verdict `conforme terrain`.
  - `P1` bloque une bonne qualité d'atterrissage UX 4.5.
  - `P2` améliore la lisibilité, sans être bloquant à lui seul.

### Micro-Plan P0 Affiné

- `P0.A — Cible contrat`
  - Le `Perimetre` pièce home ne doit plus être déduit des seuls compteurs.
  - Le `Statut` pièce home doit être servi explicitement par le backend/relay.
  - La home doit rester en lecture stricte de ces deux signaux.
- `P0.B — Modifications backend recommandées`
  - Fichier cible : `resources/daemon/models/published_scope.py`
  - Objectif : exposer dans chaque entrée `pieces[]` un signal décisionnel pièce exploitable par la home.
  - Proposition : ajouter un champ explicite `home_perimetre`.
  - Domaine cible : `Incluse | Exclue`.
  - Règle proposée :
    - si la décision pièce résolue est `exclude`, alors `Exclue`
    - sinon `Incluse`
  - Point d'attention : utiliser la décision de pièce résolue du resolver, pas l'agrégat des équipements.
- `P0.C — Modifications diagnostics recommandées`
  - Fichier cible : `resources/daemon/models/ui_contract_4d.py`
  - Objectif : ajouter un helper pur pour le `Statut` pièce/global home.
  - Proposition : ajouter une fonction `compute_home_statut(equipments_4d)`.
  - Entrée : liste d'équipements 4D.
  - Règle produit à implémenter sur les seuls équipements `perimetre == "inclus"` :
    - tous les inclus publiés => `Publiee`
    - au moins un inclus publié et au moins un inclus non publié => `Partiellement publiee`
    - sinon => `Non publiee`
  - Garde-fou explicite : `0` équipement inclus => `Non publiee`.
  - Fichier cible : `resources/daemon/transport/http_server.py`
  - Objectif : servir ce signal dans `/system/diagnostics`.
  - Proposition :
    - enrichir `summary` avec `home_statut`
    - enrichir chaque entrée de `rooms[]` avec `home_statut`
    - calculer ce champ après constitution de `equipments` et `rooms_equips`
  - Guardrail : ne pas toucher au `Statut` diagnostic équipement, ni au contrat 4D équipement existant.
- `P0.D — Modifications relay PHP recommandées`
  - Fichier cible : `core/ajax/jeedom2ha.ajax.php`
  - Objectif : arrêter la redérivation locale.
  - Proposition :
    - remplacer `_jeedom2ha_build_home_piece_perimetre()` par une lecture stricte d'un champ pièce explicite backend, idéalement `published_scope.pieces[].home_perimetre`
    - conserver `Publies` agrégé relay tant qu'il n'existe pas déjà comme signal backend dédié
    - conserver `Statut` pièce en passthrough strict depuis `diagnostic_rooms[].home_statut` et `diagnostic_summary.home_statut`
  - Résultat attendu : le relay ne décide plus la sémantique pièce ; il relaie.
- `P0.E — Tests à ajouter ou ajuster`
  - Fichier cible : `resources/daemon/tests/unit/test_ui_contract_4d.py`
  - Ajouter :
    - helper `compute_home_statut` : cas `Publiee`
    - cas `Partiellement publiee`
    - cas `Non publiee`
    - cas `0 inclus => Non publiee`
  - Fichier cible : `tests/unit/test_published_scope_http.py`
  - Ajouter :
    - le contrat `published_scope.pieces[]` expose bien `home_perimetre`
    - cas pièce explicitement exclue
    - cas pièce `inherit/include` avec équipements tous exclus individuellement mais `home_perimetre` non forcé à `Exclue`
  - Fichier cible : `resources/daemon/tests/unit/test_diagnostic_endpoint.py`
  - Ajouter :
    - `summary.home_statut` présent
    - `rooms[].home_statut` présent
    - règle sur inclus uniquement
    - contradiction volontaire entre agrégat naïf et vraie lecture sur inclus uniquement
  - Fichier cible : `tests/test_php_story_4_5_home_signals.php`
  - Adapter :
    - `Perimetre` pièce vient d'un champ explicite backend/relay
    - ne plus prouver ce point par simple `include/exclude`
    - garder les preuves sur `Publies` et `Statut` pièce
    - garder le fallback neutre pour `home_statut`
  - Fichier cible : `tests/test_php_published_scope_relay.php`
  - Ajouter :
    - le relay forwarde le nouveau champ pièce sans recompute
  - Fichier cible : `tests/unit/test_story_4_5_home_landing.node.test.js`
  - Ajouter :
    - cas de contradiction : la pièce doit afficher `Incluse` même si ses compteurs visibles pourraient suggérer autre chose
    - garder le test `pas de recomposition frontend`
- `P0.F — Ordre d'exécution recommandé`
  - 1. Ajouter le helper pur `compute_home_statut`
  - 2. Enrichir `/system/diagnostics` avec `home_statut`
  - 3. Enrichir `published_scope.pieces[]` avec `home_perimetre`
  - 4. Simplifier le relay PHP en passthrough strict
  - 5. Mettre à jour les tests backend
  - 6. Mettre à jour les tests relay
  - 7. Refaire le contrôle terrain court : payload réel, home, puis verdict
- `P0.G — Arbitrage produit à figer`
  - Si une pièce est `inherit` mais entièrement exclue par équipements individuels, la recommandation issue du terrain est qu'elle reste affichée `Incluse`, car la pièce n'est pas exclue en tant que pièce.

### Clôture Session Terrain

- Session de test terrain 4.5 clôturée le 2026-03-30.
- Verdict de session : `OK 4.5 avec réserve mineure`.
- Réserves bloquantes avant `done` :
  - `Perimetre` pièce : source sémantique produit/contrat à corriger.
  - `Statut` pièce : signal dédié `home_statut` absent sur la box testée.
- Constat express final :
  - KO : auto-refresh toujours présent.
  - Réserve mineure : badge `Ecart` cliquable mais soulignement jugé peu cohérent (préférence hover main).
- Décision de suite : passer à l'implémentation du paquet `P0` avant toute reprise du gate terrain final.
- Le plan `P1/P2` est volontairement différé à une session ultérieure.

### Completion Notes List

- Ajout du helper pur `compute_home_statut` et exposition de `home_statut` dans `summary` + `rooms[]` du diagnostic.
- Ajout d'un signal explicite `home_perimetre` dans `published_scope.pieces[]`, issu de la décision pièce (pas des compteurs).
- Relay PHP simplifié : passthrough strict de `home_perimetre` et `home_statut` sans redérivation locale.
- Tests backend/PHP/JS mis à jour pour couvrir `home_statut`, `home_perimetre` et la contradiction compteurs vs décision pièce.
- Refactor complet de la zone centrale home vers un tableau hiérarchique unique `Parc global -> pièces -> équipements`.
- Vue initiale limitée à la ligne `Parc global` ; dépliage hiérarchique géré côté home avec restauration d'état de navigation conservée.
- Suppression des surfaces inline non conformes (`Console principale`, `Diagnostic utilisateur`, `Diagnostic technique détaillé`) et des signaux interdits en home.
- Implémentation d'un delta relay minimal borné côté `core/ajax/jeedom2ha.ajax.php` pour exposer uniquement :
  - `Publies` (global/pièce/équipement),
  - `Perimetre` pièce contractuel (`Incluse` / `Exclue`),
  - `Statut` pièce lu sur champ dédié relay/backend (domaine fermé `Publiee / Partiellement publiee / Non publiee`).
- Le frontend consomme strictement ces signaux contractuels ; aucun recalcul JS local de `Publies`, aucun fallback de recomposition du `Statut` pièce depuis les équipements.
- Le relay ne reconstruit plus le `Statut` pièce depuis `diagnostic_equipments` ; si le champ dédié est absent, le rendu passe en état neutre.
- Badge `Ecart` équipement rendu cliquable uniquement si `ecart=true`, avec infobulle courte et transport d'un `eq_id` stable vers l'ouvreur diagnostic partagé (sans inline).
- Ajout de la couverture tests Story 4.5 + test PHP minimal de contrat relay.
- Réalignement complet des suites héritées impactées 4.2/4.3/3.4 sur le contrat home 4.5, sans réintroduction de diagnostic inline et sans logique métier frontend implicite.
- Gate terrain `ux-spec.md` section 10.2 exécuté et validé (test terrain final OK).
- Code review PASS ; PR #60 squash-merge dans `main` (closeout post-merge).
- Suppression du badge `Contrat backend` et du texte d'aide sous le tableau ; auto-refresh périodique retiré (bouton `Rafraîchir` conservé).
- Badge `Ecart` rendu visiblement cliquable ; `Aligné/Alignée` passent en vert ; badges gris harmonisés (`Exclue`, `Non publiee`, états neutres).
- Décalage horizontal réduit au dépliage ; rendu binaire équipement basculé en `vide / coche` avec centrage des colonnes.
- Micro-correctif post-terrain express : suppression du refresh périodique résiduel (bridge status) ; badge `Ecart` sans soulignement avec hover/curseur main via CSS dédié ; bouton `Rafraîchir` conservé comme seul point d'action.
- Micro-correctif UX résiduel : curseur main + hover discret sur le badge `Ecart` et layout fixe pour garder les colonnes alignées au dépliage.
- Task 0 préflight terrain déclarée N/A pour ce micro-correctif local (accord utilisateur).
- Validation terrain finale : micro-correctifs UX confirmés (curseur main + alignement colonnes) ; verdict OK.

### Change Log

- 2026-03-30 — Micro-correctif UX résiduel : curseur main + hover discret sur le badge `Ecart` ; alignement des colonnes figé au dépliage ; tests JS story 4.5 + scope summary.
- 2026-03-30 — Closeout post-merge : status `done` après merge PR #60.

### File List

- `resources/daemon/models/ui_contract_4d.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/models/published_scope.py`
- `resources/daemon/tests/unit/test_ui_contract_4d.py`
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py`
- `tests/unit/test_published_scope_http.py`
- `core/ajax/jeedom2ha.ajax.php`
- `desktop/css/jeedom2ha.css`
- `desktop/php/jeedom2ha.php`
- `desktop/js/jeedom2ha.js`
- `desktop/js/jeedom2ha_scope_summary.js`
- `tests/unit/test_scope_summary_presenter.node.test.js`
- `tests/unit/test_story_4_4_integration_ui_4d.node.test.js`
- `tests/unit/test_story_4_5_home_landing.node.test.js`
- `tests/unit/test_story_4_2_vocab_exclusion.node.test.js`
- `tests/unit/test_story_4_3_diagnostic_in_scope.node.test.js`
- `tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js`
- `tests/test_php_story_4_5_home_signals.php`
- `tests/test_php_published_scope_relay.php`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-5-atterrissage-home-tableau-hierarchique-et-point-d-entree-diagnostic.md`
