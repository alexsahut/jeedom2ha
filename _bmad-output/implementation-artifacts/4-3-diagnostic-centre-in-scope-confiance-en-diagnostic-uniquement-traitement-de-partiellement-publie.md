# Story 4.3 : Diagnostic centré in-scope, confiance en diagnostic uniquement, traitement de "Partiellement publié"

Status: done

## Story

En tant qu'utilisateur de la console V1.1,
je veux que le diagnostic principal ne porte que sur mes équipements inclus, que la confiance ne soit visible qu'en diagnostic technique, et que "Partiellement publié" ne soit plus un statut principal mais un indicateur de diagnostic détaillé,
afin de me concentrer sur ce qui compte et de ne pas être noyé par des informations techniques superflues.

## Contexte / Objectif produit

Le modèle 4D (Périmètre / Statut / Écart / Cause) est désormais figé côté backend par Story 4.1 (done — PR #52 mergée le 2026-03-28) et le vocabulaire d'exclusion par source est stabilisé côté frontend par Story 4.2 (done — code review PASS le 2026-03-28). Toutefois, trois problèmes UX persistent :

1. **Le diagnostic principal ne filtre pas** — les équipements exclus encombrent la vue diagnostic utilisateur, ce qui noie l'information utile.
2. **La confiance technique est exposable partout** — le champ `confidence` (Sûr / Probable / Ambigu) est disponible dans la réponse backend mais ne doit apparaître qu'en diagnostic technique détaillé, jamais en console principale.
3. **"Partiellement publié" reste un statut fantôme** — `getAggregatedStatusLabel("partially_published")` produit encore "Partiellement publié" dans le frontend, alors que ce statut est absorbé dans le modèle 4D (Périmètre=inclus, Statut=publié, Écart=false).

Cette story clarifie les **quatre surfaces de lecture** et assigne à chacune sa population et son contenu :

| Surface | Population | Contenu spécifique | Confiance visible |
|---|---|---|---|
| **Console principale** (synthèse périmètre) | Tous les équipements | Compteurs, périmètre par source, statut 4D, écart, cause | **Non** |
| **Diagnostic principal utilisateur** | `perimetre = inclus` uniquement | Statut, écart, cause, détails commandes/typage | **Non** |
| **Diagnostic technique détaillé** | `perimetre = inclus` uniquement | Tout le diagnostic principal + confiance + reason_code | **Oui** |
| **Export support complet** | Tous les équipements | Vue technique exhaustive : confiance, reason_code, commandes, typage, 4D | **Oui** |

Le filtrage in-scope est une **règle de population de surface** appliquée côté backend. Il ne modifie ni le pipeline, ni le resolver canonique, ni le calcul des 4 dimensions.

## Scope

### In scope

1. **Backend** — Filtrage diagnostic in-scope côté serveur (`perimetre = inclus`).
2. **Backend** — Vérification et figeage de l'absorption de `Partiellement publié` (statut=publie, ecart=false, pas de cause_code).
3. **Frontend** — Confiance absente de la console principale (invariant à tester).
4. **Frontend** — Confiance rendue visible dans le diagnostic technique détaillé (section existante ou nouvelle).
5. **Frontend** — Neutralisation de `getAggregatedStatusLabel("partially_published")` → rendu comme "Publié" (cohérence 4D).
6. **Frontend** — Le diagnostic principal utilisateur ne montre les détails que pour les équipements in-scope.
7. **Export PHP** — Ajout des champs 4D (`perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`) dans l'allowlist d'export.
8. **Export PHP** — Mise à jour du résumé d'export pour refléter le modèle 4D (disparition de la catégorie `partially_published`).
9. **Tests** — Couverture de tous les AC : filtrage, confiance, Partiellement publié, export.

### Out of scope

| Élément hors scope | Responsable |
|---|---|
| Refonte complète de l'affichage 4D en console (badges statut/écart/cause) | Story 4.4 |
| Remplacement complet de `getAggregatedStatusLabel` par l'affichage 4D | Story 4.4 |
| Élimination de `Ambigu` / `Non supporté` dans `getAggregatedStatusLabel` | Story 4.4 |
| Élimination de `include`/`exclude` (anglais) dans `renderEquipmentState` | Story 4.4 |
| Opérations HA (Republier, Supprimer/Recréer) | Epic 5 |
| Modification du resolver canonique (inherit/include/exclude) | Epic 1 — figé |
| Modification du contrat de santé du pont | Epic 2 — figé |
| Renommage des `reason_code` stables | Epic 3 — figés |
| Modification de `cause_mapping.py` ou `ui_contract_4d.py` | Story 4.1 — figés à son merge |

## Dépendances autorisées

- **Story 3.1** (done — PR #44) — `taxonomy.py` figé, `REASON_CODE_TO_PRIMARY_STATUS`, 5 statuts primaires.
- **Story 3.2** (done — PR #46) — `_DIAGNOSTIC_MESSAGES`, `reason_code` enrichis, `detail`, `remediation`, `v1_limitation`.
- **Story 4.1** (done — PR #52 mergée le 2026-03-28) — contrat 4D backend (`perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`), compteurs 4D (`compteurs.total`, `compteurs.inclus`, `compteurs.exclus`, `compteurs.ecarts`) dans `/system/diagnostics`.

**Aucune dépendance en avant.** Story 4.4 peut s'appuyer sur le filtrage et le traitement de "Partiellement publié" stabilisés ici.

### Prérequis contractuel minimal de Story 4.1

Le prérequis de Story 4.3 sur Story 4.1 est strictement contractuel : la réponse `/system/diagnostics` doit exposer, pour chaque équipement, les 6 champs 4D (`perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`) et les compteurs 4D par pièce et global. Story 4.3 consomme ce contrat, pas le code interne de 4.1.

**État réel du prérequis** : Story 4.1 est désormais mergée dans `main`. La story 4.3 consomme le contrat 4D réellement stabilisé, sans dépendance ouverte restante sur 4.1.

### Coexistence avec Story 4.2

Story 4.3 **ne dépend pas fonctionnellement** de Story 4.2. Aucun des AC de 4.3 ne requiert que le vocabulaire d'exclusion par source soit migré pour passer.

État réel de coexistence :
- Story 4.2 est déjà `done` et 4.3 part du JS post-4.2.
- Les acquis 4.2 (badges périmètre, compteurs 4D) restent intacts dans le candidat 4.3.
- Les tests de non-régression 4.2 / 4.3 passent sur le même état figé.

## Acceptance Criteria

### AC 1 — Filtrage backend du diagnostic principal in-scope

**Given** le diagnostic principal utilisateur (surface dédiée dans la réponse `/system/diagnostics`)
**When** il est construit par le backend
**Then** il ne contient que les équipements dont `perimetre` = `inclus`
**And** les équipements exclus (`exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement`) ne sont PAS présents dans cette surface filtrée
**And** les équipements exclus restent visibles dans les sections non filtrées de la réponse (utilisées par la synthèse de périmètre et l'export) avec leur source d'exclusion

### AC 2 — Confiance absente de la console principale

**Given** un équipement in-scope affiché dans la console principale (synthèse de périmètre)
**When** ses informations sont rendues
**Then** aucun badge, libellé ou indicateur de confiance (`Sûr` / `Probable` / `Ambigu`) n'est produit par la zone de rendu de la ligne équipement dans la synthèse de périmètre
**And** la fonction ou le bloc de rendu responsable de la ligne équipement en console ne lit pas et ne projette pas le champ `confidence`

### AC 3 — Confiance visible en diagnostic technique détaillé

**Given** un équipement in-scope affiché dans le diagnostic technique détaillé
**When** ses informations sont rendues
**Then** la confiance (`Sûr` / `Probable` / `Ambigu`) est visible et exploitable
**And** la valeur affichée correspond exactement à la valeur `confidence` fournie par le backend pour cet équipement

### AC 4 — Absorption de "Partiellement publié"

**Given** un équipement historiquement affiché en `Partiellement publié` (équipement publié dans HA avec couverture commandes partielle)
**When** il est réévalué par le modèle 4D
**Then** `statut` = `publie`, `ecart` = `false`, `cause_code` = `null`
**And** il n'est jamais utilisé comme statut principal de la console

**Given** le frontend reçoit un `status_code` = `partially_published` (cas legacy/résiduel)
**When** `getAggregatedStatusLabel` le traite
**Then** le libellé rendu est `Publié` (même badge, même style que le cas `published`)
**And** la fonction `getAggregatedStatusLabel` ne produit pas le libellé `"Partiellement publié"` pour cette entrée

**Given** un équipement publié avec couverture commandes partielle
**When** il est inspecté dans le diagnostic détaillé
**Then** l'information de couverture partielle reste accessible via les champs existants (`matched_commands`, `unmatched_commands`)
**And** le libellé de statut principal affiché pour cet équipement est `"Publié"`, pas `"Partiellement publié"`

### AC 5 — Export support complet exhaustif

**Given** l'export support complet généré par `exportDiagnostic` (PHP)
**When** il est produit
**Then** il contient tous les équipements (in-scope et exclus), aucun filtrage
**And** chaque équipement inclut les champs 4D : `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`
**And** chaque équipement inclut `confidence`, `reason_code`, `matched_commands`, `unmatched_commands`, `detected_generic_types`
**And** le résumé d'export utilise les compteurs 4D (`total`, `inclus`, `exclus`, `ecarts`) au lieu de l'ancien résumé par `status_code`
**And** la catégorie `partially_published` n'apparaît plus dans le résumé d'export

### AC 6 — Non-régression des tests existants

**Given** les modifications backend et frontend
**When** la suite de tests complète est exécutée
**Then** tous les tests pytest existants passent (baseline : 128+ tests — ajustement attendu selon Story 4.2)
**And** tous les tests JS existants passent (baseline : 73+ tests — ajustement attendu selon Story 4.2)
**And** les champs techniques legacy (`status`, `status_code`, `confidence`, `reason_code`, `detail`, `remediation`, `v1_limitation`) restent présents dans la réponse `/system/diagnostics` — jamais supprimés

## Tasks / Subtasks

- [x] Task 1 — Backend : surface filtrée diagnostic in-scope dans `/system/diagnostics` (AC 1)
  - [x] 1.1 Dans `http_server.py`, à la construction de la réponse `/system/diagnostics`, ajouter une surface contenant uniquement les équipements dont `perimetre == "inclus"` — filtre en Python pur sur la collection déjà résolue, pas de modification du pipeline. Le choix du nom de clé et de la forme (section top-level, query param, etc.) est laissé au dev — voir Dev Notes pour un exemple d'implémentation acceptable.
  - [x] 1.2 La surface filtrée expose les mêmes champs par équipement que la surface complète (4D + technique) — même structure, population restreinte
  - [x] 1.3 Vérifier que les sections non filtrées (`payload.equipments`, `payload.rooms`, `payload.summary`) restent inchangées — tous les équipements (in-scope et exclus) y sont présents
  - [x] 1.4 Exposer le nombre d'équipements in-scope dans la réponse (compteur ou longueur de la collection filtrée — au choix du dev)

- [x] Task 2 — Backend : vérification de l'absorption "Partiellement publié" (AC 4)
  - [x] 2.1 Vérifier dans `taxonomy.py` qu'aucun `reason_code` ne produit un `status_code` = `partially_published` — si un tel mapping existe, le documenter dans les Dev Notes comme dette technique résiduelle mais ne PAS modifier `taxonomy.py` (figé Epic 3)
  - [x] 2.2 Vérifier dans `cause_mapping.py` que les codes `sure`, `probable`, `sure_mapping` retournent bien `(None, None, None)` — confirmant que ces équipements sont publiés avec ecart=false
  - [x] 2.3 Ajouter un test unitaire prouvant que pour un équipement publié avec couverture partielle (`matched_commands` < commandes totales), le contrat 4D donne bien `statut=publie`, `ecart=false`, `cause_code=null`

- [x] Task 3 — Frontend : neutralisation de "Partiellement publié" dans `getAggregatedStatusLabel` (AC 4)
  - [x] 3.1 Dans `jeedom2ha_scope_summary.js`, modifier `getAggregatedStatusLabel("partially_published")` pour retourner le même rendu que `"published"` — badge vert, libellé `"Publié"`
  - [x] 3.2 Ajouter un commentaire sur la ligne modifiée : `// Story 4.3 : "Partiellement publié" absorbé — statut principal = Publié`
  - [x] 3.3 Ajouter un test unitaire JS vérifiant que `getAggregatedStatusLabel("partially_published")` produit exactement le même résultat que `getAggregatedStatusLabel("published")`

- [x] Task 4 — Frontend : confiance en diagnostic technique détaillé uniquement (AC 2, AC 3)
  - [x] 4.1 Identifier dans `jeedom2ha_scope_summary.js` la section de rendu diagnostic par équipement (actuellement : `status_code`, `detail`, `remediation`, `v1_limitation`) — cette section est le "diagnostic technique détaillé"
  - [x] 4.2 Ajouter le rendu de `confidence` dans cette section diagnostic — format : badge texte avec la valeur traduite (`sure` → `Sûr`, `probable` → `Probable`, `ambiguous` → `Ambigu`) — visible uniquement quand la valeur est non-null et non-vide
  - [x] 4.3 Vérifier que la confiance N'apparaît PAS dans la section console principale (ligne d'équipement dans la synthèse de périmètre) — si la confiance est actuellement rendue quelque part dans la console, la supprimer
  - [x] 4.4 Le rendu de confiance est un affichage en lecture seule du champ `confidence` du backend — aucune dérivation, aucun calcul local

- [x] Task 5 — Frontend : consommation de la surface filtrée in-scope (AC 1)
  - [x] 5.1 Dans `createModel()` de `jeedom2ha_scope_summary.js`, extraire la surface filtrée in-scope de la réponse backend — stocker dans un index par `eq_id` pour lookup rapide
  - [x] 5.2 Dans le rendu diagnostic par équipement, conditionner l'affichage des détails diagnostic (status_code, detail, remediation, v1_limitation, confidence) à la présence de l'équipement dans la surface filtrée — si absent (exclu), pas de détails diagnostic rendus
  - [x] 5.3 Les équipements exclus restent visibles dans la liste d'équipements par pièce avec leur badge périmètre — seuls les détails diagnostic sont masqués
  - [x] 5.4 Graceful degradation : si la surface filtrée est absente de la réponse (daemon ancien, réponse incomplète), fallback sur le comportement actuel (tous les détails affichés) — pas de crash

- [x] Task 6 — Export PHP : champs 4D et résumé actualisé (AC 5)
  - [x] 6.1 Dans `core/ajax/jeedom2ha.ajax.php`, action `exportDiagnostic`, ajouter les champs suivants à l'allowlist d'extraction : `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`
  - [x] 6.2 Vérifier que `confidence`, `reason_code`, `matched_commands`, `unmatched_commands`, `detected_generic_types` sont déjà dans l'allowlist — corriger si manquant
  - [x] 6.3 Mettre à jour le calcul du résumé d'export : remplacer le comptage par `status_code` (published / partially_published / not_published / excluded) par un comptage basé sur les champs 4D : `total`, `inclus` (perimetre=inclus), `exclus` (perimetre commence par exclu_), `ecarts` (ecart=true), `publies` (statut=publie), `non_publies` (statut=non_publie)
  - [x] 6.4 Supprimer la catégorie `partially_published` du résumé d'export
  - [x] 6.5 Signaler le changement de contrat export (incrémentation de version, champ de migration, ou tout autre mécanisme au choix du dev — l'exigence est la traçabilité du changement, pas le mécanisme exact)

- [x] Task 7 — Tests backend (AC 1, AC 4, AC 6)
  - [x] 7.1 Créer `resources/daemon/tests/test_story_4_3_diagnostic_in_scope.py` :
    - Test filtrage : payload avec 5 équipements (3 inclus, 2 exclus) → la surface filtrée contient exactement 3 équipements, tous avec `perimetre=inclus`
    - Test non-filtrage des sections existantes : `payload.equipments` contient les 5 équipements
    - Test compteur in-scope cohérent avec la population filtrée
    - Test absorption "Partiellement publié" : équipement `sure_mapping` avec commandes partielles → `statut=publie`, `ecart=false`, `cause_code=null`
    - Test écart direction 2 : équipement exclu encore publié → présent dans `payload.equipments` mais absent de la surface filtrée
  - [x] 7.2 Ajouter dans `test_ui_contract_4d.py` un cas de test pour l'absorption de `partially_published` : `reason_code=sure_mapping`, `matched_commands < total_commands` → ecart=false, cause_code=null
  - [x] 7.3 Ajouter un test de non-régression vérifiant que les champs techniques (`status_code`, `confidence`, `reason_code`, `detail`, `remediation`, `v1_limitation`) restent présents dans la surface filtrée in-scope

- [x] Task 8 — Tests frontend (AC 2, AC 3, AC 4)
  - [x] 8.1 Créer `tests/unit/test_story_4_3_diagnostic_in_scope.node.test.js` :
    - Test `getAggregatedStatusLabel("partially_published")` retourne le même résultat que `getAggregatedStatusLabel("published")`
    - Test ligne équipement console : un équipement avec `confidence: "sure"` rendu via la fonction de rendu console → la sortie de cette zone ne contient pas de badge confiance
    - Test section diagnostic détaillé : un équipement in-scope rendu via la zone diagnostic → la sortie contient le libellé de confiance traduit
    - Test filtrage frontend : payload avec surface filtrée contenant 2 sur 4 équipements → seuls les 2 in-scope affichent des détails diagnostic
    - Test graceful degradation : payload sans surface filtrée → tous les détails affichés (fallback)
  - [x] 8.2 Vérifier non-régression : `tests/unit/test_scope_summary_presenter.node.test.js` — tous les tests existants passent
  - [x] 8.3 Vérifier non-régression Story 3.4 : `tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js` — passthrough lecture seule intact

- [x] Task 9 — Exécution suite complète (AC 6)
  - [x] 9.1 `pytest resources/daemon/tests/` → suite complète PASS
  - [x] 9.2 `node --test tests/unit/*.node.test.js` → tous les tests PASS
  - [x] 9.3 Vérifier manuellement que l'export généré par `exportDiagnostic` contient les champs 4D et que `partially_published` n'apparaît plus dans le résumé

## Dev Notes

### Frontière exacte entre les quatre surfaces

La distinction est fondamentale pour cette story. Chaque surface a une population et un contenu différents :

```
Console principale (synthèse périmètre)
├── Population : TOUS les équipements
├── Contenu : compteurs 4D, périmètre par source, badge statut
├── Confiance : NON visible
└── Source : payload.rooms + payload.summary + payload.equipments

Diagnostic principal utilisateur
├── Population : perimetre = inclus UNIQUEMENT
├── Contenu : statut, écart, cause, détails commandes/typage
├── Confiance : NON visible
└── Source : surface filtrée in-scope (nouveau, filtré backend)

Diagnostic technique détaillé
├── Population : perimetre = inclus UNIQUEMENT
├── Contenu : tout le diagnostic principal + confiance + reason_code
├── Confiance : OUI visible
└── Source : même surface filtrée, section UI distincte

Export support complet
├── Population : TOUS les équipements
├── Contenu : vue technique exhaustive (4D + technique + commandes + typage)
├── Confiance : OUI incluse
└── Source : collection complète (non filtrée) via PHP
```

**Règle clé** : le filtrage in-scope est une règle de population de surface. Il ne modifie ni le pipeline (`topology → eligibility → mapping → decision → publication → diagnostic`), ni le resolver canonique (`inherit/include/exclude`), ni le calcul des 4 dimensions.

### Traitement exact de "Partiellement publié" — exemples concrets

**Cas concret : Lumière avec ON/OFF mais sans dimmer**

Avant Story 4.3 (ancien modèle) :
- `status_code` = `partially_published` (ou `published` selon la version)
- Label console : "Partiellement publié" (badge bleu)

Après Story 4.3 (modèle 4D) :
- `perimetre` = `inclus`
- `statut` = `publie` (une config discovery a été envoyée à HA, l'entité existe)
- `ecart` = `false` (l'équipement est bien publié comme voulu)
- `cause_code` = `null`
- Label console : "Publié" (badge vert)
- Diagnostic détaillé : `matched_commands: ["LIGHT_ON", "LIGHT_OFF"]`, `unmatched_commands: ["LIGHT_SLIDER"]` — l'information de couverture partielle reste accessible via ces champs existants

**Cas concret : Cover avec UP/DOWN mais sans STOP ni position**

Même traitement :
- `statut` = `publie`, `ecart` = `false`
- Diagnostic détaillé : montre les commandes mappées et non mappées

**Ce qui n'est PAS fait :**
- "Partiellement publié" ne réapparaît jamais comme statut principal
- "Partiellement publié" ne génère pas d'écart (`ecart` reste `false`)
- "Partiellement publié" n'est pas un `cause_code`
- Aucun nouveau champ obligatoire dans le contrat principal

**Enrichissement optionnel (hors contrat principal) :** Si le dev juge utile d'ajouter un indicateur synthétique de couverture au diagnostic détaillé (ex: `commandes_mappees: 5/8`), il peut l'ajouter dans la surface filtrée in-scope uniquement — jamais dans le contrat principal de console. Ce point est optionnel et non requis par les AC.

### Où vit l'information de couverture partielle après Story 4.3

| Information | Surface | Champs porteurs |
|---|---|---|
| Commandes effectivement mappées | Diagnostic détaillé + Export | `matched_commands` (liste) |
| Commandes non mappées | Diagnostic détaillé + Export | `unmatched_commands` (liste) |
| Types génériques détectés | Diagnostic détaillé + Export | `detected_generic_types` (liste) |
| Ratio synthétique (optionnel) | Diagnostic détaillé uniquement | `coverage_ratio` (optionnel — ex: `"5/8"`) |

Le frontend n'a pas besoin de calculer un ratio. Les listes de commandes sont déjà fournies par le backend.

### Table de traduction confiance → libellé UI

Implémenter dans `jeedom2ha_scope_summary.js`, fonction locale pure :

```
Valeur confidence (backend)  → Libellé UI affiché
─────────────────────────────────────────────────
"sure"                       → "Sûr"
"probable"                   → "Probable"
"ambiguous"                  → "Ambigu"
null / "" / toute autre      → "" (pas de badge — confiance non déterminée)
```

Cette table est utilisée **uniquement dans la section diagnostic technique détaillé**, jamais dans la console principale.

### Contrat backend `/system/diagnostics` — ajout Story 4.3

**Exigence produit** : la réponse `/system/diagnostics` doit fournir, en plus de la vue complète existante, une surface filtrée contenant uniquement les équipements in-scope (`perimetre == "inclus"`). Le mécanisme exact (section top-level, query param, endpoint dédié) est laissé au dev. Le contenu de chaque équipement dans la surface filtrée est identique à la vue complète — même structure, même champs, population restreinte.

**Exemple d'implémentation acceptable** (non contractuel — le dev peut choisir un autre shape) :

```json
{
  "summary": { ... },
  "rooms": [ ... ],
  "equipments": [ ... ],
  "in_scope_equipments": [
    {
      "eq_id": "123",
      "perimetre": "inclus",
      "statut": "publie",
      "ecart": false,
      "cause_code": null,
      "confidence": "sure",
      "status_code": "published",
      "reason_code": "sure_mapping",
      "...": "mêmes champs que equipments[i]"
    }
  ]
}
```

### Export PHP — changements attendus

**Allowlist actuelle** (Story 3.x) : `eq_id`, `eq_type_name`, `name`, `object_name`, `status`, `status_code`, `confidence`, `reason_code`, `detail`, `remediation`, `v1_limitation`, `v1_compatibility`, `matched_commands`, `unmatched_commands`, `detected_generic_types`, `traceability`

**Allowlist après Story 4.3** — ajout des champs 4D : `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`

**Résumé d'export — avant** :
```json
"summary": { "total": 42, "published": 30, "partially_published": 5, "not_published": 3, "excluded": 4 }
```

**Résumé d'export — après** (exemple, noms de clés au choix du dev) :
```json
"summary": {
  "total": 42,
  "inclus": 38,
  "exclus": 4,
  "ecarts": 3,
  "publies": 35,
  "non_publies": 7
}
```

**Exigences sur le résumé** : le résumé reflète le modèle 4D (compteurs par `perimetre` et par `statut`). La catégorie `partially_published` n'y figure plus. Le mécanisme de signalement du changement de contrat (version, champ de migration) est au choix du dev.

Le PHP lit les champs 4D depuis la réponse daemon pour calculer ce résumé. Il ne recalcule pas les compteurs — il itère les équipements extraits et compte par valeur de champ.

### Distinction reason_code / cause_code — vérification de non-brouillage

Story 4.3 **ne modifie pas** la couche `reason_code` → `cause_code` (figée Story 4.1, `cause_mapping.py`). Le seul ajout est l'inclusion des `reason_code` dans l'export support et dans la surface filtrée in-scope.

Vérification : `reason_code` apparaît dans l'export et le diagnostic technique. `cause_code` apparaît dans le contrat 4D de la console. Les deux ne sont jamais mélangés. Le frontend ne lit pas `reason_code`.

### Impact backend vs frontend

| Couche | Modifications Story 4.3 | Fichiers touchés |
|---|---|---|
| Backend Python | Ajout d'une surface filtrée in-scope dans la réponse `/system/diagnostics` | `resources/daemon/transport/http_server.py` |
| Backend Python | Aucune modification de `cause_mapping.py`, `ui_contract_4d.py`, `taxonomy.py`, `aggregation.py` | — |
| Frontend JS | Neutralisation `partially_published` → `Publié`, rendu confiance en zone diagnostic, consommation surface filtrée | `desktop/js/jeedom2ha_scope_summary.js` |
| Export PHP | Ajout champs 4D dans allowlist, mise à jour résumé export | `core/ajax/jeedom2ha.ajax.php` |
| Tests Python | Nouveaux tests filtrage, absorption, non-régression | `resources/daemon/tests/` (nouveau fichier dédié) |
| Tests JS | Nouveaux tests confiance, Partiellement publié, filtrage | `tests/unit/` (nouveau fichier dédié) |

### Fichiers à ne PAS toucher

- `resources/daemon/models/cause_mapping.py` (figé Story 4.1)
- `resources/daemon/models/ui_contract_4d.py` (figé Story 4.1)
- `resources/daemon/models/taxonomy.py` (figé Story 3.1)
- `resources/daemon/models/aggregation.py` (figé Story 3.3)
- `resources/daemon/models/published_scope.py` (figé Story 1.1)
- `core/php/jeedom2ha.php` (pas de modification PHP stub)

### Dev Agent Guardrails

1. **Ne pas modifier le pipeline** — le filtrage in-scope est un filtre de population en sortie, pas une modification du pipeline `topology → eligibility → mapping → decision → publication → diagnostic`.
2. **Ne pas modifier le resolver canonique** — `inherit/include/exclude`, précédence `equipement > piece > global` restent intacts.
3. **Ne pas modifier `cause_mapping.py`** — la traduction `reason_code` → `cause_code` est figée Story 4.1.
4. **Ne pas modifier `taxonomy.py`** — les 5 statuts primaires et `REASON_CODE_TO_PRIMARY_STATUS` sont figés Story 3.1.
5. **Ne pas recalculer `perimetre`, `statut`, `ecart` côté frontend** — le filtrage in-scope est fait côté backend, le frontend consomme la surface filtrée telle quelle sans refiltrer.
6. **Ne pas réintroduire `Partiellement publié` comme statut principal** — le seul traitement autorisé est le mapping vers "Publié" dans `getAggregatedStatusLabel`.
7. **Ne pas créer de nouveau `cause_code` pour la couverture partielle** — "Partiellement publié" n'est pas un écart, pas une cause, pas un `cause_code`.
8. **`reason_code` reste invisible en console** — il apparaît uniquement dans le diagnostic technique détaillé et l'export.
9. **Non-régression Story 3.4 obligatoire** — les sections `status_code`, `detail`, `remediation`, `v1_limitation` ne sont pas supprimées du rendu. La confiance est AJOUTÉE, pas substituée.
10. **Coexistence Story 4.2** — si Story 4.2 est déjà mergée, ses acquis (badges périmètre, compteurs 4D) doivent rester intacts. Si Story 4.2 n'est pas encore mergée, les modifications de 4.3 ne doivent pas empêcher le merge futur de 4.2.
11. **`core/php/jeedom2ha.php` doit rester du PHP pur** — pas de dépendance Jeedom dans le stub PHP. Les modifications sont uniquement dans `core/ajax/jeedom2ha.ajax.php`.

### Project Structure Notes

- Backend daemon Python : `resources/daemon/`
- Modèles backend : `resources/daemon/models/`
- Serveur HTTP daemon : `resources/daemon/transport/http_server.py`
- Frontend JS : `desktop/js/`
- Export PHP : `core/ajax/jeedom2ha.ajax.php`
- Tests Python : `resources/daemon/tests/`
- Tests JS : `tests/unit/` — format `*.node.test.js`, runner : Node.js `--test`
- Le module `Jeedom2haScopeSummary` est exporté en UMD — ne pas casser le pattern d'export

### References

- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md#8.5`] — Filtrage du diagnostic principal in-scope (trois surfaces, trois populations)
- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md#8.6`] — Traitement du cas historique "Partiellement publié" (absorption + indicateur diagnostic)
- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md#8.3`] — Contrat dual reason_code / cause_code
- [Source: `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md#5.6`] — Rôle console vs diagnostic (table des surfaces)
- [Source: `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md#6.2`] — Vocabulaire recommandé + termes interdits
- [Source: `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md#6.5`] — Table de mapping ancien → nouveau modèle (Partiellement publié → Publié)
- [Source: `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md#Story 4.3`] — AC upstream dans le plan d'epics
- [Source: `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md#4`] — Invariants contractuels V1.1 (I10-I18)
- [Source: `_bmad-output/implementation-artifacts/4-1-contrat-backend-du-modele-perimetre-statut-ecart-cause.md`] — Contrat 4D backend figé, structure JSON, tables de traduction
- [Source: `_bmad-output/implementation-artifacts/4-2-vocabulaire-d-exclusion-par-source-disparition-du-concept-exception.md`] — État pré-Story 4.3 du JS

## Stratégie de test story-level

### Invariants V1.1 touchés par cette story

| Invariant | Référence | Couvert par |
|---|---|---|
| I10 — Contrat 4D comme unique modèle de lecture | test-strategy §4 | AC 1, AC 5 |
| I14 — Diagnostic filtré in-scope côté backend | test-strategy §4 | AC 1 |
| I15 — Confiance hors console principale | test-strategy §4 | AC 2 |
| I16 — Contrat dual reason_code / cause_code étanche | test-strategy §4 | AC 5 |
| I17 — Frontend en lecture seule | test-strategy §4 | AC 2, AC 3, AC 4 |
| I18 — Disparition du concept exception | test-strategy §4 | Non touché (Story 4.2) |

### Tests unitaires obligatoires

- Table de traduction `confidence` → libellé UI (fonction pure — 4 cas)
- `getAggregatedStatusLabel("partially_published")` → même résultat que `"published"`
- Surface filtrée in-scope : population correcte (inclus uniquement)
- Absorption "Partiellement publié" : `statut=publie`, `ecart=false`, `cause_code=null`

### Tests d'intégration backend obligatoires

- Endpoint `/system/diagnostics` avec mix inclus/exclus → la surface filtrée contient seulement les inclus
- Endpoint `/system/diagnostics` avec équipement publié à couverture partielle → `statut=publie`, `ecart=false`
- Endpoint `/system/diagnostics` avec équipement exclu encore publié (direction 2) → absent de la surface filtrée, présent dans la collection complète
- Compteur in-scope cohérent

### Tests de contrat / non-régression obligatoires

- Champs techniques (`status_code`, `confidence`, `reason_code`, `detail`, `remediation`, `v1_limitation`) présents dans la surface filtrée
- Champs 4D présents dans l'export PHP (`perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`)
- Résumé d'export sans catégorie `partially_published`
- Suite pytest complète PASS
- Suite JS complète PASS

### Tests UI ciblés obligatoires

- Zone rendu ligne équipement console : aucun badge confiance produit
- Zone rendu diagnostic technique : badge confiance présent pour les équipements in-scope
- Fonction `getAggregatedStatusLabel("partially_published")` : ne produit pas le libellé "Partiellement publié"
- Détails diagnostic conditionnés à la présence de l'équipement dans la surface filtrée

## Guardrails anti-dérive

1. **Pas de dérive vers Story 4.4** — cette story ne refond pas l'affichage 4D complet de la console. Elle ne remplace pas `getAggregatedStatusLabel` par un affichage 4D. Elle ne touche pas `renderEquipmentState`. Elle ne modifie pas l'affichage des badges statut/écart/cause.
2. **Pas de refonte globale de l'UI** — les modifications frontend sont ciblées : neutralisation d'un cas dans une table, ajout d'un libellé, conditionnement de sections.
3. **Pas de dépendance en avant** — Story 4.4 et Epic 5 ne sont pas nécessaires pour que Story 4.3 fonctionne. Story 4.4 consommera le filtrage et le traitement "Partiellement publié" sans les recalculer.
4. **Backend-first** — tout calcul métier (filtrage, absorption, compteurs) est côté backend. Le frontend affiche.
5. **Pas d'implémentation directe** — ce fichier est une story, pas un patch code.
6. **Pas de wording flou** — les quatre surfaces sont nommées et définies.

## Définition de done story-level

- [x] AC 1 à AC 6 validés par les tests automatisés
- [x] Surface filtrée in-scope présente dans la réponse `/system/diagnostics` et correctement peuplée
- [x] Confiance absente de la console principale (prouvé par test)
- [x] Confiance présente en diagnostic technique détaillé (prouvé par test)
- [x] "Partiellement publié" n'apparaît plus comme statut principal (prouvé par test)
- [x] Export support complet inclut les champs 4D, la confiance, les reason_code, les commandes et le typage
- [x] Résumé d'export utilise le modèle 4D (pas de `partially_published`)
- [x] Suite pytest complète PASS
- [x] Suite JS complète PASS
- [x] Non-régression Stories 3.4 et 4.1 confirmée ; coexistence Story 4.2 vérifiée
- [x] Code review PASS

## Risques / ambiguïtés restantes

1. **Clôture review / merge final** — réalisée par le squash merge de la PR #57 dans `main` (commit `9cf4cadcb4df08b81e163ca79aaec3d8419a422b`). La story est alignée sur l'état réel et ne porte plus d'écart documentaire.

2. **`partially_published` status_code — origine résiduelle** — Il n'est pas clair si le backend génère encore `partially_published` comme `status_code` dans des chemins legacy secondaires. La story le neutralise côté lecture et le couvre par tests, sans rouvrir `taxonomy.py`.

3. **Performance du filtrage** — La surface filtrée in-scope duplique les données des équipements inclus. Pour un parc de ~200 équipements, ce doublon est négligeable. Si le parc dépasse 1000 équipements, une optimisation future pourrait être nécessaire — hors scope V1.1.

4. **Diagnostic technique détaillé vs diagnostic principal utilisateur en UI** — La distinction entre ces deux surfaces est architecturalement claire (avec/sans confiance), mais leur rendu visuel est identique dans le code JS actuel (même section). Story 4.3 ajoute la confiance dans la section diagnostic existante, ce qui en fait de facto le "diagnostic technique détaillé". La séparation visuelle plus fine (onglets, niveaux de détail progressifs) relève de Story 4.4.

## Dev Agent Record

### Agent Model Used

Gemini 3.1 Pro (High)

### Debug Log References

### Completion Notes List

- Implémentation code, UX et tests exécutée entièrement et avec succès.
- Tests locaux confirmés sur l'état figé : 182 Pytest PASS, 95 JS PASS.
- Verdict terrain déjà obtenu : GO avec réserve. Aucune correction produit / code métier supplémentaire n'est requise avant 4.4.
- Candidat terrain figé en git sur `story/4.3-diagnostic-centre-in-scope`, commit `8c57808d9fe2b1ae00db0cc7bbd9cd16ab4a9752`, tag `story-4.3-terrain-go-avec-reserve`.
- Traçabilité documentaire réalignée par le SM ; story alignée sur le squash merge de la PR #57 dans `main` (commit `9cf4cadcb4df08b81e163ca79aaec3d8419a422b`) et clôturée en `done`.

### File List

- `desktop/js/jeedom2ha_scope_summary.js`
- `resources/daemon/transport/http_server.py`
- `core/ajax/jeedom2ha.ajax.php`
- `resources/daemon/tests/unit/test_story_4_3_diagnostic_in_scope.py`
- `tests/unit/test_story_4_3_diagnostic_in_scope.node.test.js`
- `resources/daemon/tests/unit/test_ui_contract_4d.py`
- `tests/unit/test_scope_summary_presenter.node.test.js`
- `tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js`
- `_bmad-output/implementation-artifacts/4-3-diagnostic-centre-in-scope-confiance-en-diagnostic-uniquement-traitement-de-partiellement-publie.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
