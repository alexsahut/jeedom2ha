# Story 5.1 : Façade backend unique et contrat de disponibilité des actions

Status: done

> **Merge closeout 2026-04-05** — PR #65 squash-merged dans `main` (commit `1e0a0abc376c`).
> Code review final : PASS. Gate terrain : **PASS 2026-04-05** — exécuté sur `main` (commit `1e0a0ab`).
> Story soldée. Epic 5 prêt à enchaîner sur Story 5.2.

Epic: Epic 5 — Opérations HA explicites, contextuelles et sûres

## Story

En tant qu'utilisateur Jeedom,
je veux que toutes les actions Home Assistant passent par une façade backend unique paramétrée par intention et portée, et que le backend fournisse par équipement un contrat de disponibilité des actions (`actions_ha`) incluant le label contextuel, la disponibilité, la raison d'indisponibilité et le niveau de confirmation,
afin que le frontend n'ait aucune logique locale sur les actions HA et que le socle contractuel soit posé pour les stories 5.2, 5.3 et 5.4.

## Contexte / Objectif produit

Cette story ouvre l'Epic 5 et pose le **socle contractuel et backend** des opérations HA V1.1 Pilotable.

Elle ne livre pas les flux complets de publication ni de suppression (stories 5.2 et 5.3). Elle livre la **façade backend unique**, le **signal `actions_ha` par équipement** et la **matrice de disponibilité minimale** qui seront consommés par toutes les stories suivantes.

Trois principes structurants hérités du correct-course V3 (2026-04-04) sont figés :

1. **Façade unique** — toute opération HA passe par un même point d'entrée backend, paramétrée par `intention` (`publier` / `supprimer`), `portée` (`global` / `piece` / `equipement`) et `selection`.
2. **Signal `actions_ha`** — le backend fournit par équipement un objet décrivant chaque action disponible avec son label, sa disponibilité, sa raison d'indisponibilité (si grisé) et son niveau de confirmation. Le frontend consomme ce signal en lecture seule.
3. **Label contextuel** — au niveau équipement, le bouton positif porte un label piloté par `est_publie_ha` :
   - `est_publie_ha = false` → « Créer dans Home Assistant »
   - `est_publie_ha = true` → « Republier dans Home Assistant »

Le frontend **ne calcule pas le label, ne calcule pas la disponibilité, ne reconstitue pas `est_publie_ha`, ne fait aucune logique métier locale** sur les actions HA. `est_publie_ha` est porté par le cache runtime du daemon (présence effective d'une configuration MQTT Discovery retained).

## Scope

### In scope

1. **Façade backend unique** d'opérations HA, acceptant comme paramètres :
   - `intention` : `publier` ou `supprimer`
   - `portée` : `global`, `piece`, `equipement`
   - `selection` : identifiant(s) cible(s)
2. **Validation** de la requête : intention reconnue, portée reconnue, sélection non vide.
3. **Signal `actions_ha`** exposé par équipement dans le contrat API, contenant au minimum pour chaque action :
   - `label` : libellé contextuel
   - `disponible` : booléen
   - `raison_indisponibilite` : texte lisible si `disponible = false`
   - `niveau_confirmation` : indicateur du niveau de confirmation attendu
4. **Label contextuel du bouton positif** au niveau équipement :
   - `est_publie_ha = false` → `Créer dans Home Assistant`
   - `est_publie_ha = true` → `Republier dans Home Assistant`
5. **Matrice de disponibilité minimale** :
   - `est_publie_ha = false` et équipement inclus → bouton positif actif, Supprimer grisé
   - `est_publie_ha = true` et équipement inclus → bouton positif actif, Supprimer actif
   - infrastructure indisponible → toutes les actions HA grisées avec raison lisible
6. **Contrat de réponse homogène** quelle que soit la portée, utilisant le modèle 4 dimensions (périmètre, statut, écart, cause).
7. **Cohérence** entre le signal `actions_ha` et l'état issu du contrat 4D existant (story 4.1).
8. **Tests** unitaires et d'intégration backend couvrant la façade, le signal `actions_ha`, le label contextuel et la matrice de disponibilité.

### Out of scope

| Élément hors scope | Responsable / remarque |
|---|---|
| Exécution réelle du flux `publier` (publication MQTT Discovery) | Story 5.2 |
| Exécution réelle du flux `supprimer` (dépublication MQTT Discovery) | Story 5.3 |
| Scope enforcement (suppression des exclus encore publiés lors de l'action positive) | Story 5.2 |
| Confirmations UI (modales, rappels d'impact HA) | Story 5.2 / 5.3 |
| Retour d'opération lisible et mémorisation du dernier résultat | Story 5.4 |
| Label du bouton positif à portée pièce/global (wording exact story-level) | Story 5.2 |
| Preview complète avant/après publication | Hors V1.1 |
| Extension fonctionnelle (button, number, select, climate) | Hors V1.1 |
| Alignements Homebridge | Hors V1.1 |

## Dépendances autorisées

- **Story 1.1** — `done` : resolver canonique du périmètre publié (`global → pièce → équipement`).
- **Story 2.1** — `done` : contrat backend de santé minimale (état démon, broker, dernière synchro — nécessaire pour le gating infrastructure).
- **Story 3.2** — `done` : `reason_code` stables, raison lisible, action recommandée.
- **Story 4.1** — `done` : contrat backend 4D (périmètre, statut, écart, cause_code/cause_label).

Aucune dépendance en avant. Cette story fournit le socle consommé par 5.2, 5.3 et 5.4.

## Acceptance Criteria

### AC 1 — Façade backend unique paramétrée par intention × portée

**Given** une action Home Assistant demandée
**When** le backend reçoit la requête
**Then** il la traite via une façade unique
**And** la requête contient les paramètres `intention` (`publier` ou `supprimer`), `portée` (`global`, `piece`, `equipement`) et `selection`

**Given** une requête avec une intention inconnue ou une portée non reconnue
**When** la façade la reçoit
**Then** elle la rejette avec une erreur explicite

**Given** une même intention exécutée à des portées différentes
**When** la façade est appelée
**Then** le contrat de réponse reste homogène
**And** la réponse utilise le modèle 4 dimensions (périmètre, statut, écart, cause)

### AC 2 — Signal `actions_ha` par équipement

**Given** le contrat API d'un équipement
**When** il est construit par le backend
**Then** il contient un objet `actions_ha` avec pour chaque action :
- `label` : libellé textuel
- `disponible` : booléen
- `raison_indisponibilite` : texte si indisponible, `null` sinon
- `niveau_confirmation` : indicateur du niveau de confirmation attendu

**And** le frontend consomme cet objet en lecture seule sans recalculer le label ni la disponibilité

### AC 3 — Label contextuel Créer / Republier selon `est_publie_ha`

**Given** un équipement inclus avec `est_publie_ha = false`
**When** le contrat `actions_ha` est construit
**Then** le bouton positif a le label « Créer dans Home Assistant »

**Given** un équipement inclus avec `est_publie_ha = true`
**When** le contrat `actions_ha` est construit
**Then** le bouton positif a le label « Republier dans Home Assistant »

**Given** un changement de `est_publie_ha` d'un équipement (de `false` vers `true` ou inversement)
**When** le contrat `actions_ha` est reconstruit
**Then** le label du bouton positif bascule immédiatement de manière cohérente

### AC 4 — Matrice de disponibilité minimale

**Given** un équipement inclus avec `est_publie_ha = false`
**When** le contrat `actions_ha` est construit
**Then** le bouton positif est `disponible = true`
**And** le bouton supprimer est `disponible = false` avec `raison_indisponibilite` = texte lisible (aucune entité publiée)

**Given** un équipement inclus avec `est_publie_ha = true`
**When** le contrat `actions_ha` est construit
**Then** le bouton positif est `disponible = true`
**And** le bouton supprimer est `disponible = true`

**Given** un équipement quelconque et l'infrastructure indisponible (démon ou broker hors service)
**When** le contrat `actions_ha` est construit
**Then** tous les boutons d'action HA sont `disponible = false`
**And** chaque bouton porte une `raison_indisponibilite` lisible mentionnant l'indisponibilité du pont

### AC 5 — Grisement par indisponibilité du pont

**Given** le démon ou le broker MQTT indisponible
**When** le contrat `actions_ha` est construit pour n'importe quel équipement
**Then** toutes les actions HA sont grisées
**And** la raison d'indisponibilité est lisible et distincte des raisons de configuration ou de périmètre

**Given** le pont redevenu sain
**When** le contrat `actions_ha` est reconstruit
**Then** les actions HA redeviennent disponibles selon la matrice de disponibilité nominale

### AC 6 — Interdiction de logique frontend locale sur les actions HA

**Given** le contrat `actions_ha` fourni par le backend
**When** le frontend traite ce signal
**Then** il ne calcule pas le label du bouton positif
**And** il ne calcule pas la disponibilité des boutons
**And** il ne reconstitue pas `est_publie_ha` depuis d'autres champs
**And** il ne fait aucune logique métier locale sur les actions HA
**And** il affiche strictement les valeurs fournies par `actions_ha`

### AC 7 — Cohérence du contrat `actions_ha` avec le modèle 4D

**Given** un équipement dont le contrat 4D indique `perimetre = inclus`, `statut = non_publie`
**When** le contrat `actions_ha` est construit
**Then** `est_publie_ha` est cohérent avec `statut` (non publié ⟹ `est_publie_ha = false` dans le cas nominal sans écart d'infrastructure)

**Given** un équipement dont le contrat 4D indique `perimetre = exclu_*`, `statut = publie`, `ecart = true`
**When** le contrat `actions_ha` est construit
**Then** le signal tient compte de l'état réel de publication pour le label et la disponibilité

**Given** une réponse de la façade
**When** elle est sérialisée
**Then** les champs `actions_ha` sont cohérents avec les champs du modèle 4D de l'équipement

### AC 8 — Tests de non-régression

**Given** le socle de test MVP existant (mapping, lifecycle, diagnostic, exclusions, `unique_id`)
**When** la façade et le signal `actions_ha` sont ajoutés
**Then** aucune suite de test existante ne régresse

**Given** les acquis Epic 4 (contrat 4D, compteurs, vocabulaire exclusion par source)
**When** le contrat `actions_ha` est ajouté aux réponses API
**Then** les champs 4D existants restent intacts et non modifiés

## Tasks / Subtasks

- [x] Task 0 — Pre-flight Git et état du socle
  - [x] Vérifier que la branche courante n'est pas protégée (main/beta/stable).
  - [x] Vérifier que le working tree est propre.
  - [x] Vérifier que les suites tests existantes passent : `pytest` backend + `node --test` JS.

- [x] Task 1 — Conception et implémentation de la façade backend unique (AC: 1)
  - [x] Définir le point d'entrée de la façade dans le daemon (ex: `/action/execute` ou équivalent).
  - [x] Implémenter le dispatcher de la façade acceptant `intention` × `portée` × `selection`.
  - [x] Valider les paramètres : intention reconnue, portée reconnue, sélection non vide.
  - [x] Retourner une erreur explicite pour les combinaisons invalides.
  - [x] Garantir un contrat de réponse homogène quelle que soit la portée, conforme au modèle 4D.

- [x] Task 2 — Implémentation du signal `actions_ha` par équipement (AC: 2, 3, 4, 5, 7)
  - [x] Ajouter un constructeur du signal `actions_ha` qui prend en entrée l'état 4D de l'équipement, `est_publie_ha` et l'état du pont.
  - [x] Implémenter la logique de label contextuel :
    - `est_publie_ha = false` → `Créer dans Home Assistant`
    - `est_publie_ha = true` → `Republier dans Home Assistant`
  - [x] Implémenter le label du bouton supprimer : `Supprimer de Home Assistant`.
  - [x] Implémenter la matrice de disponibilité :
    - `est_publie_ha = false` et inclus → positif actif, supprimer grisé (`Aucune entité publiée dans Home Assistant` ou équivalent)
    - `est_publie_ha = true` et inclus → positif actif, supprimer actif
    - infrastructure indisponible → tout grisé avec raison infrastructure
  - [x] Implémenter le `niveau_confirmation` pour chaque action selon les règles UX (story-level).
  - [x] Exposer `actions_ha` dans le contrat API par équipement (diagnostic et/ou console).
  - [x] Veiller à la cohérence `actions_ha` ↔ champs 4D.

- [x] Task 3 — Intégration du relay PHP et exposition au frontend (AC: 2, 6)
  - [x] Relayer le signal `actions_ha` depuis le daemon vers le frontend via `core/ajax/jeedom2ha.ajax.php`.
  - [x] S'assurer que le relay est un passthrough strict : pas de calcul de label, pas de calcul de disponibilité côté PHP.
  - [x] Relayer le point d'entrée de la façade si nécessaire (appel daemon depuis l'AJAX PHP).

- [x] Task 4 — Consommation frontend en lecture seule (AC: 6)
  - [x] Brancher le frontend sur le signal `actions_ha` fourni par le backend.
  - [x] Afficher le label et la disponibilité des boutons strictement depuis `actions_ha`.
  - [x] S'assurer qu'aucune logique locale JS ne recalcule le label, la disponibilité ou `est_publie_ha`.
  - [x] Griser visuellement les boutons indisponibles avec le texte de `raison_indisponibilite`.

- [x] Task 5 — Tests story-level (AC: 1 à 8)
  - [x] Tests unitaires Python — constructeur `actions_ha` :
    - cas `est_publie_ha = false`, équipement inclus → label `Créer`, positif actif, supprimer grisé
    - cas `est_publie_ha = true`, équipement inclus → label `Republier`, positif actif, supprimer actif
    - cas infrastructure indisponible → tout grisé avec raison infrastructure
    - cas basculement `est_publie_ha` → label bascule
    - cohérence `actions_ha` ↔ champs 4D
  - [x] Tests unitaires Python — façade :
    - intention inconnue → rejet
    - portée inconnue → rejet
    - sélection vide → rejet
    - réponse homogène quelle que soit la portée
  - [x] Tests d'intégration backend :
    - signal `actions_ha` présent dans le contrat API par équipement
    - gating par état du pont : actions grisées quand démon/broker indisponible
    - label contextuel correct selon `est_publie_ha` dans le contrat API réel
    - matrice de disponibilité complète dans le contrat API réel
  - [x] Tests de contrat / non-régression :
    - contrat 4D existant non modifié par l'ajout de `actions_ha`
    - suites MVP existantes (mapping, lifecycle, diagnostic, exclusions, `unique_id`) toujours vertes
    - acquis Epic 4 (compteurs, vocabulaire exclusion par source) intacts
    - `reason_code` stables non impactés
    - `inherit` n'apparaît toujours pas dans les réponses API
  - [x] Tests JS ciblés :
    - le frontend affiche les labels et la disponibilité depuis `actions_ha` sans recalcul
    - si `actions_ha` est absent, le rendu reste neutre (pas de pseudo-contrat local)
  - [x] Tests relay PHP :
    - passthrough strict du signal `actions_ha` sans enrichissement local

- [x] Task 6 — Déploiement terrain DEV/TEST
  - [x] Dry-run : `./scripts/deploy-to-box.sh --dry-run` — bloqué (`JEEDOM_BOX_HOST` non configuré, box indisponible)
  - [x] Vérification terrain du signal `actions_ha` dans le payload réel — **PASS 2026-04-05** : signal présent sur 99/99 équipements inclus
  - [x] Vérification terrain du label contextuel et de la disponibilité des boutons — **PASS 2026-04-05** : label Créer/Republier correct, matrice de disponibilité conforme

## Dev Notes

### Contraintes architecturales à intégrer

1. La façade backend doit être le **seul point d'entrée** pour toute opération HA V1.1. Pas d'endpoints ad hoc par portée.
2. Le signal `actions_ha` est un **contrat backend → UI**. Le frontend le consomme en lecture seule.
3. `est_publie_ha` = présence effective d'une configuration MQTT Discovery retained pour cet équipement. Cette information est portée par le **cache runtime du daemon** (cf. architecture-delta §8.2).
4. Le `niveau_confirmation` doit suivre la matrice UX graduée (ux-delta-review §7.2) :
   - action positive équipement : pas de modale obligatoire si scope explicite ;
   - action positive pièce : confirmation légère ;
   - action positive global : confirmation explicite ;
   - supprimer équipement : modale forte ;
   - supprimer pièce/global : modale forte avec rappel impacts HA.
5. Le contrat de réponse de la façade doit inclure les champs nécessaires pour le retour d'opération (story 5.4) mais cette story ne les implémente pas encore complètement.

### Points de conception ouverts (à trancher pendant l'implémentation)

1. Nom exact du endpoint de la façade (ex: `/action/execute`, `/action/ha`, ou extension d'un endpoint existant).
2. Forme exacte du champ `niveau_confirmation` (enum, entier, objet).
3. Emplacement exact du signal `actions_ha` dans la réponse API : enrichissement du contrat diagnostic existant, ou endpoint dédié.
4. Stratégie de stub pour les intentions `publier` et `supprimer` qui ne seront réellement implémentées qu'en 5.2 / 5.3 : la façade doit accepter les appels mais peut retourner un placeholder (ou une erreur contrôlée "pas encore implémenté") si l'exécution réelle n'est pas prête.

### Source de vérité pour `est_publie_ha`

`est_publie_ha` doit venir du backend / cache runtime daemon. Il ne doit **jamais** être reconstitué par le frontend à partir d'autres champs du contrat 4D. Même si `statut = publie` implique logiquement `est_publie_ha = true` dans le cas nominal, le frontend ne doit pas faire cette déduction.

### Previous Story Intelligence

1. Stories 4.1-4.6 ont posé le contrat 4D complet — cette story enrichit le contrat sans le modifier.
2. Story 2.3 a posé le gating des actions HA selon la santé du pont — cette story réutilise l'état de santé pour la matrice de disponibilité.
3. Story 3.2 a posé les `reason_code` stables — cette story ne les modifie pas.
4. Le relay PHP (`core/ajax/jeedom2ha.ajax.php`) a été simplifié en passthrough strict lors de la story 4.5 — cette story étend le passthrough au signal `actions_ha`.

### Git Intelligence Summary

Branches / commits récents pertinents :
- `832b5c1 feat(story-4.6): diagnostic modal in-scope et ouverture ciblée depuis la home`
- `be97bd0 Story 4.5: atterrissage home — tableau hiérarchique`
- Les stories 4.5 et 4.6 ont stabilisé la séparation home / diagnostic.

Fichiers principaux candidats à la modification :
- `resources/daemon/transport/http_server.py` — ajout du endpoint façade + enrichissement du contrat avec `actions_ha`
- `resources/daemon/models/` — module pour le constructeur du signal `actions_ha`
- `core/ajax/jeedom2ha.ajax.php` — relay du signal et du point d'entrée façade
- `desktop/js/jeedom2ha_scope_summary.js` ou `desktop/js/jeedom2ha.js` — consommation frontend du signal
- `resources/daemon/tests/unit/` — tests unitaires du constructeur et de la façade
- `tests/unit/` — tests d'intégration et tests JS

## Impacts backend vs frontend

| Couche | Impact attendu | Fichiers candidats |
|---|---|---|
| Backend Python (daemon) | Création de la façade d'opérations + constructeur `actions_ha` + enrichissement du contrat API | `resources/daemon/transport/http_server.py`, `resources/daemon/models/` (nouveau module) |
| PHP relay | Passthrough du signal `actions_ha` + relay du point d'entrée façade | `core/ajax/jeedom2ha.ajax.php` |
| Frontend JS | Consommation en lecture seule du signal `actions_ha` pour afficher les boutons | `desktop/js/jeedom2ha_scope_summary.js`, `desktop/js/jeedom2ha.js` |
| Tests Python | Tests unitaires constructeur + façade + signal + matrice + non-régression | `resources/daemon/tests/unit/` |
| Tests JS | Tests de consommation lecture seule du signal `actions_ha` | `tests/unit/` |
| Tests PHP | Tests relay passthrough | `tests/` |

## Stratégie de test story-level

### Invariants à couvrir

- **I4** — Backend source unique des 4 dimensions et du contrat de disponibilité `actions_ha`.
- **I5** — Action positive (`publier`) non destructive par contrat.
- **I6** — `Supprimer` seul flux destructif standalone, sans recréation automatique.
- **I7** — Séparation scope local vs application HA.
- **I8** — `Dernière opération` obligatoire (vérifié en non-régression, implémenté en 5.4).
- **I9** — Invariants HA (`unique_id` stable, recalcul scope déterministe).
- **I10** — Contrat backend → UI 4D lu sans interprétation locale.
- **I13** — Écart bidirectionnel pré-calculé backend (non-régression).
- **I16** — Contrat dual `reason_code` / `cause_code` étanche (non-régression).
- **I17** — Frontend en lecture seule.
- **I18** — Disparition du concept exception (non-régression).
- Signal `actions_ha` — label contextuel Créer/Republier selon `est_publie_ha`, disponibilité, niveau de confirmation.
- Gating par état du pont.

### Tests unitaires obligatoires

- Constructeur `actions_ha` :
  - `est_publie_ha = false`, inclus → label `Créer dans Home Assistant`, positif actif, supprimer grisé.
  - `est_publie_ha = true`, inclus → label `Republier dans Home Assistant`, positif actif, supprimer actif.
  - infrastructure indisponible → tout grisé avec raison `Bridge indisponible` ou équivalent.
  - basculement `est_publie_ha` → label bascule.
- Façade backend :
  - intention `publier` reconnue.
  - intention `supprimer` reconnue.
  - intention inconnue → rejet.
  - portée inconnue → rejet.
  - sélection vide → rejet.
- Table de traduction label :
  - correspondance `est_publie_ha` ↔ label est une fonction pure, testable en isolation.

### Tests d'intégration backend obligatoires

- Signal `actions_ha` présent dans le contrat API par équipement.
- Gating par état du pont : actions grisées quand démon/broker indisponible.
- Label contextuel correct selon `est_publie_ha` dans le contrat API réel.
- Matrice de disponibilité complète dans le contrat API réel.
- Contrat de réponse homogène quelle que soit la portée.

### Tests de contrat / non-régression obligatoires

- Contrat 4D non altéré par l'ajout de `actions_ha`.
- Suites MVP (mapping, lifecycle, diagnostic, exclusions, `unique_id`) vertes.
- Acquis Epic 4 (compteurs, vocabulaire exclusion par source) intacts.
- `reason_code` stables non impactés.
- `inherit` absent des réponses API.
- Action positive ≠ chemin destructif (preuve contractuelle).
- Signal `actions_ha` fournit le label correct (Créer vs Republier) selon `est_publie_ha`.

### Tests UI ciblés

- Le frontend affiche les labels et la disponibilité strictement depuis `actions_ha`.
- Si `actions_ha` absent, comportement neutre (pas de pseudo-contrat local).
- Aucun recalcul JS de `est_publie_ha`, du label ou de la disponibilité.

### Tests relay PHP

- Passthrough strict de `actions_ha` sans calcul local.

## Guardrails anti-dérive

1. **Pas d'implémentation du flux de publication MQTT** — c'est Story 5.2.
2. **Pas d'implémentation du flux de suppression MQTT** — c'est Story 5.3.
3. **Pas de scope enforcement** (résolution automatique des écarts direction 2) — c'est Story 5.2.
4. **Pas de modales de confirmation UI** — ce sont les stories 5.2 et 5.3.
5. **Pas de retour d'opération complet** — c'est Story 5.4.
6. **Pas de label pièce/global du bouton positif** — c'est Story 5.2 (wording story-level).
7. **Pas de réouverture du modèle 4D** — acquis Epic 4.
8. **Pas de réouverture des compteurs backend** — acquis Epic 4.
9. **Pas de réouverture du vocabulaire legacy** — acquis Epic 4.
10. **Pas de logique métier frontend locale** sur les actions HA.
11. **Pas de reconstitution frontend de `est_publie_ha`**.
12. **Pas de modification des `reason_code` stables** — acquis Epic 3.
13. **Pas d'extension fonctionnelle** (button, number, select, climate).
14. **Pas de preview complète, pas de remédiation guidée avancée, pas de santé avancée**.
15. **Pas de flux atomique « Supprimer puis recréer »** — ce wording est abandonné depuis le correct-course V3.

## Définition de done

- [x] AC 1 à AC 8 validés.
- [x] La façade backend unique accepte `intention` × `portée` × `selection` et rejette les appels invalides.
- [x] Le signal `actions_ha` est exposé par équipement avec label, disponibilité, raison d'indisponibilité, niveau de confirmation.
- [x] Le label contextuel bascule entre `Créer` et `Republier` selon `est_publie_ha`, piloté par le backend.
- [x] La matrice de disponibilité minimale est respectée et testée.
- [x] Le grisement par indisponibilité du pont fonctionne et expose une raison lisible.
- [x] Le frontend consomme `actions_ha` en lecture seule sans logique locale.
- [x] Le contrat 4D existant n'est pas altéré.
- [x] Les suites de tests MVP et Epic 4 ne régressent pas.
- [x] Le code est prêt pour la review (`bmad-code-review`).
- [x] **Gate terrain** : validation terrain du signal `actions_ha` et du label contextuel — **PASS 2026-04-05** (voir section Gate Terrain ci-dessous).

## Gate Terrain — PASS — 2026-04-05

Validation terrain exécutée sur box réelle (`main`, commit `1e0a0ab`).

| Critère | Résultat |
|---|---|
| Signal `actions_ha` présent | PASS — 99/99 équipements inclus |
| Label contextuel Créer/Republier | PASS — correct selon `est_publie_ha` |
| Matrice de disponibilité minimale | PASS — non publié → supprimer grisé ; publié → supprimer actif |
| Gating bridge (MQTT down) | PASS — toutes actions grisées avec raison lisible, rétablissement nominal |
| UI lecture seule | PASS — labels et disabled states depuis `actions_ha`, aucune logique locale |

**Observation mineure non bloquante** : curseur `hand` sur bouton `disabled` (artefact Bootstrap CSS).
Pas d'impact fonctionnel — click = no-op confirmé. Non bloquant, conservé pour traçabilité.

Gate terrain soldé.

## Closeout Final — 2026-04-05

Story 5.1 **DONE**. Toutes les acceptance criteria AC 1 à AC 8 sont validées, gate terrain passé sur box réelle.

- Façade backend unique `POST /action/execute` opérationnelle.
- Signal `actions_ha` exposé par équipement dans le contrat API.
- Label contextuel Créer/Republier piloté par le backend, consommé en lecture seule par le frontend.
- Matrice de disponibilité et gating bridge validés terrain.
- 228 pytest + 120 JS + 7 PHP = 355 tests PASS, 0 régression.
- Epic 5 prêt à enchaîner sur Story 5.2.

## References

- `_bmad-output/planning-artifacts/active-cycle-manifest.md` — sections 4, 6, 8.
- `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md` — sections 6, 8.2, 9, 12, 13.
- `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md` — sections 4.4, 6.1, 6.2, 7.1, 7.2, 7.5.
- `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md` — sections 5.3, 7.1, 7.2, 7.3, 7.4, 8.2, 10 (point 9).
- `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md` — Epic 5, Story 5.1.
- `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md` — sections 4, 5, 6, 7, 9.
- `_bmad-output/project-context.md` — règles d'implémentation et anti-patterns.

## Dev Agent Record

### Implementation Plan

1. Endpoint façade : `POST /action/execute` — paramétrée par `intention` × `portée` × `selection`.
2. Constructeur `actions_ha` : module pur `models/actions_ha.py`, fonction `build_actions_ha()`.
3. Signal exposé dans `/system/diagnostics` par équipement (null si non inclus).
4. Stub exécution : la façade accepte les appels valides mais retourne `resultat: "non_implemente"` (5.2/5.3).
5. `niveau_confirmation` : `"aucune"` pour publier (équipement), `"forte"` pour supprimer.
6. Relay PHP : passthrough strict dans `getPublishedScopeForConsole` + nouvel action `executeHaAction`.
7. Frontend : `readActionsHa()` + `renderActionButtons()` sans aucun recalcul, colonne "Actions" dans le tableau home.

### Completion Notes

- 228 pytest PASS, 120 JS PASS, 7 PHP PASS — 0 failure, 0 régression.
- Façade backend opérationnelle avec validation complète des paramètres.
- Signal `actions_ha` exposé dans le contrat API diagnostic par équipement.
- Label contextuel Créer/Republier piloté par `est_publie_ha` (= `active_or_alive`).
- Matrice de disponibilité minimale implémentée et testée.
- Gating bridge : toutes actions grisées si `MqttBridge.is_connected == False`.
- Frontend en lecture seule stricte : `readActionsHa()` normalise, `renderActionButtons()` rend.
- Relay PHP passthrough strict : aucun calcul de label ni de disponibilité.
- Task 6 (terrain) : dry-run exécuté mais bloqué par absence de `JEEDOM_BOX_HOST` (box indisponible). Vérification terrain du signal `actions_ha` et du label contextuel différée — **non bloquant pour code review**, à valider avant `done`.
- **Fix post-review M1 (2026-04-05)** : assertion tautologique corrigée dans `test_story_5_1_actions_ha_frontend.node.test.js:67` — remplacement de `!A || !B` (always-true) par regex ciblé sur l'élément `data-ha-action="publier"`. 11/11 tests PASS, suite complète 120/120 PASS, 0 régression.

### Debug Log

Aucun incident bloquant.
- 4 tests d'intégration corrigés : le `MqttBridge()` par défaut n'est pas connecté → ajout de `_set_bridge_connected(app)` dans les tests nominaux.
- Test `inherit` : renommage de l'équipement de test ("Inherit check" → "Non-reg check") car le nom contenait le mot recherché.

## File List

### Fichiers créés

- `resources/daemon/models/actions_ha.py` — Constructeur du signal `actions_ha` (fonctions pures)
- `resources/daemon/tests/unit/test_story_5_1_actions_ha.py` — Tests unitaires du constructeur (18 tests)
- `resources/daemon/tests/unit/test_story_5_1_facade.py` — Tests unitaires de la façade /action/execute (12 tests)
- `resources/daemon/tests/unit/test_story_5_1_integration.py` — Tests d'intégration backend (11 tests)
- `tests/unit/test_story_5_1_actions_ha_frontend.node.test.js` — Tests JS frontend (11 tests)
- `tests/unit/test_story_5_1_php_relay.php` — Tests relay PHP (7 tests)

### Fichiers modifiés

- `resources/daemon/transport/http_server.py` — Ajout handler `_handle_action_execute`, enrichissement diagnostics avec `actions_ha`, import `build_actions_ha`, route `/action/execute`
- `core/ajax/jeedom2ha.ajax.php` — Passthrough `actions_ha` dans allowlist diagnostic_equipments, nouvel action `executeHaAction`
- `desktop/js/jeedom2ha_scope_summary.js` — `readActionsHa()`, `renderActionButtons()`, colonne "Actions" dans le tableau, export des fonctions, `actions_ha` dans le modèle équipement

### Fichiers BMAD modifiés

- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Story 5.1 : ready-for-dev → in-progress → review → done
- `_bmad-output/implementation-artifacts/5-1-facade-backend-unique-et-contrat-de-disponibilite-des-actions.md` — Checkboxes, Dev Agent Record, File List, Change Log, Status

## Change Log

- **2026-04-04** — Story 5.1 implémentée : façade backend unique (`POST /action/execute`), signal `actions_ha` par équipement, relay PHP passthrough, consommation frontend en lecture seule. 228 pytest + 120 JS + 7 PHP = 355 tests PASS, 0 régression.
- **2026-04-05** — Reprise ciblée BMAD : réalignement artefacts (Task 6 terrain décochée car box indisponible, gate terrain ajoutée en DoD, sprint-status last_updated corrigé). Vérification de scope confirmée — aucune dérive 5.2/5.3/5.4. Tests re-validés : 228 pytest + 120 JS + 7 PHP = 355 PASS, 0 régression.
- **2026-04-05** — Fix post-review M1 : assertion JS tautologique corrigée dans `test_story_5_1_actions_ha_frontend.node.test.js:67` (ligne `!A || !B` always-true → regex `data-ha-action="publier"[^>]*>` + vérification absence `disabled`). 120/120 JS PASS, 0 régression.
- **2026-04-05** — Gate terrain PASS sur box réelle (`main`, commit `1e0a0ab`) : 99/99 équipements inclus avec `actions_ha`, label contextuel conforme, matrice de disponibilité conforme, gating bridge opérationnel. Observation CSS mineure (curseur hand sur disabled) — non bloquant. Story 5.1 passée à `done`. Epic 5 prêt pour Story 5.2.
