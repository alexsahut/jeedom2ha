# Story 4.1 : Contrat backend du modèle Périmètre / Statut / Écart / Cause

Status: done

## Story

En tant qu'utilisateur de la console V1.1,
je veux que le backend expose un contrat UI canonique à 4 dimensions (périmètre, statut, écart, cause),
afin que chaque équipement soit lisible selon un modèle mental naturel, sans concepts techniques internes.

## Dépendances autorisées

- **Story 1.1** (done) : resolver canonique `inherit/include/exclude`, source d'exclusion, `published_scope` et champ `has_pending_home_assistant_changes`.
- **Story 3.1** (done — PR #44) : `taxonomy.py` figé, reason_codes stables, `REASON_CODE_TO_PRIMARY_STATUS`.
- **Story 3.2** (done — PR #46) : `_DIAGNOSTIC_MESSAGES`, reason_codes enrichis, `detail`, `remediation`, `v1_limitation`.
- **Story 3.3** (done — PR #48) : `aggregation.py` figé, `build_summary()` déjà présent dans `http_server.py`. Les `compteurs` 4D sont ajoutés à côté du `summary` existant — non-régression de `build_summary` obligatoire.

Aucune dépendance en avant.

## Acceptance Criteria

### AC 1 — Champs 4D présents dans le contrat API équipement

**Given** un équipement évalué par le pipeline backend
**When** le contrat API `/system/diagnostics` est construit
**Then** chaque équipement dans `payload.equipments` contient les champs `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`
**And** `statut` est strictement binaire : uniquement `publie` ou `non_publie`
**And** `ecart` est un booléen pré-calculé par le backend (jamais dérivé côté UI)

### AC 2 — Direction 1 : inclus mais non publié

**Given** un équipement inclus dans le périmètre mais non publié (ex : mapping ambigu)
**When** le contrat API est construit
**Then** `perimetre` = `inclus`, `statut` = `non_publie`, `ecart` = `true`
**And** `cause_code` = `ambiguous_skipped`, `cause_label` = `Mapping ambigu — plusieurs types possibles`
**And** `cause_action` contient une action utilisateur recommandée non vide

### AC 3 — Direction 2 : exclu mais encore publié dans HA

**Given** un équipement dont `perimetre` commence par `exclu_` ET dont la présence HA réelle est confirmée par `publications[eq_id].active_or_alive == True` OU `eq_id in pending_discovery_unpublish` (l'équipement est encore physiquement présent dans HA)
**When** le contrat API est construit
**Then** `statut` = `publie`, `ecart` = `true`
**And** `cause_code` = `pending_unpublish`, `cause_label` = `Changement en attente d'application`
**And** `cause_action` = `Republier pour appliquer le changement`

> **NOTE TERRAIN 2026-03-27** : `has_pending_home_assistant_changes` ne peut PAS servir de signal direction 2. C'est un XOR (`desired != actual`) qui est aussi `True` pour les inclus-non-publiés (direction 1). Le terrain a montré 69 faux positifs causés par cette confusion.

### AC 4 — Couche de traduction reason_code → cause_code (fonction pure)

**Given** les `reason_code` stables d'Epic 3 (`taxonomy.py`, figé)
**When** la couche de traduction est exécutée
**Then** chaque `reason_code` actif est traduit en `(cause_code, cause_label, cause_action)` par une fonction pure (table de correspondance statique — voir Dev Notes)
**And** les `reason_code` restent présents dans la réponse `/system/diagnostics` en tant que couche technique/support (backward compat, export support) — ils ne sont jamais supprimés ni renommés
**And** `reason_code` n'appartient pas au contrat UI canonique : le frontend V1.1 (Story 4.4) consommera `cause_code`/`cause_label`, pas `reason_code`
**And** la table de traduction est testable en isolation totale (aucune dépendance sur `http_server` ou l'état du daemon)

### AC 5 — Compteurs 4D pré-calculés par pièce et global

**Given** le payload `/system/diagnostics`
**When** le backend calcule les agrégations
**Then** la clé `compteurs` est présente dans `payload.summary` avec les champs `total`, `inclus`, `exclus`, `ecarts`
**And** la clé `compteurs` est présente dans chaque entrée de `payload.rooms` avec les mêmes champs
**And** l'invariant arithmétique `total = inclus + exclus` est respecté pour chaque niveau (pièce et global)
**And** `ecarts` compte les équipements des DEUX directions (direction 1 ET direction 2)

### AC 6 — Valeurs autorisées du champ perimetre

**Given** n'importe quel équipement dans la réponse
**When** le champ `perimetre` est inspectionné
**Then** sa valeur est strictement l'une des quatre valeurs autorisées : `inclus`, `exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement`
**And** la valeur `inherit` n'apparaît jamais dans la réponse API (résolue avant sérialisation)

### AC 7 — Équipement aligné (pas d'écart) : champs cause null

**Given** un équipement inclus ET publié (aligné)
**When** le contrat API est construit
**Then** `ecart` = `false`, `cause_code` = `null`, `cause_label` = `null`, `cause_action` = `null`

**Given** un équipement exclu ET non présent dans HA (`publications[eq_id]` absent ou `active_or_alive == False`, et `eq_id` absent de `pending_discovery_unpublish`)
**When** le contrat API est construit
**Then** `ecart` = `false`, `cause_code` = `null`, `cause_label` = `null`, `cause_action` = `null`

### AC 8 — Non-régression des tests existants

**Given** l'ajout des champs 4D dans la réponse diagnostics
**When** la suite de tests complète est exécutée
**Then** les tests existants des stories 3.1, 3.2, 3.3, 3.4 restent verts (128/128 pytest)
**And** les tests JS existants restent verts (73/73)
**And** les champs de la couche technique (`status_code`, `reason_code`, `detail`, `remediation`, `v1_limitation`, `status`, `confidence`, etc.) restent présents dans la réponse — ils ne sont jamais supprimés

## Tasks / Subtasks

- [x] Task 1 — Créer `resources/daemon/models/cause_mapping.py` (AC 4)
  - [x] 1.1 Implémenter la table de traduction complète `reason_code → (cause_code, cause_label, cause_action)` (voir Dev Notes — Table de traduction complète)
  - [x] 1.2 Implémenter `reason_code_to_cause(reason_code: str) -> tuple[str | None, str | None, str | None]` — retourne `(None, None, None)` si le reason_code ne produit pas d'écart direction 1 (cas published ou inconnu)
  - [x] 1.3 Implémenter `build_cause_for_pending_unpublish() -> tuple[str, str, str]` — retourne `("pending_unpublish", "Changement en attente d'application", "Republier pour appliquer le changement")`
  - [x] 1.4 Vérifier que le module n'a aucune dépendance sur `http_server`, `aggregation`, `taxonomy` (pur, standalone)

- [x] Task 2 — Créer `resources/daemon/models/ui_contract_4d.py` (AC 1, AC 2, AC 3, AC 5, AC 6, AC 7)
  - [x] 2.1 Implémenter `reason_code_to_perimetre(reason_code: str) -> str` — mapping deterministe (voir table dans Dev Notes)
  - [x] 2.2 Implémenter `compute_ecart(perimetre: str, statut: str) -> bool` — formule exacte : `(perimetre == "inclus" AND statut == "non_publie") OR (perimetre.startswith("exclu_") AND statut == "publie")` — `has_pending` supprimé (XOR ambigü, invalidé terrain 2026-03-27)
  - [x] 2.3 Implémenter `build_ui_counters(equipments_4d: list[dict]) -> dict` — calcule `total`, `inclus`, `exclus`, `ecarts` par agrégation des champs `perimetre` et `ecart` déjà résolus dans la liste passée en paramètre
  - [x] 2.4 S'assurer que `build_ui_counters` respecte l'invariant `total = inclus + exclus` (assertion ou retour cohérent documenté)

- [x] Task 3 — Modifier `resources/daemon/transport/http_server.py` (AC 1–7)
  - [x] 3.1 Dans `_handle_system_diagnostics`, récupérer `pending_discovery_unpublish` depuis `request.app` (soft-fail : si absent, dict vide). `publications` est déjà accessible via `request.app.get("publications", {})`
  - [x] 3.2 Pour chaque `eq_dict` construit dans la boucle équipement, calculer et ajouter les champs dans cet ordre :
    - `is_published_in_ha` : `bool(publications.get(eq_id) and pub.active_or_alive) or eq_id in pending_discovery_unpublish` — reflète la présence HA réelle
    - `perimetre` : via `reason_code_to_perimetre(reason_code)`
    - `statut` : `"publie"` si `is_published_in_ha`, sinon `"non_publie"` (FIX terrain 2026-03-27 — l'ancienne formule avec `has_pending` était fausse)
    - `ecart` : via `compute_ecart(perimetre, statut)` — fonction pure, sans `has_pending`
    - `cause_code, cause_label, cause_action` : si `ecart` ET direction 1 (`perimetre == "inclus"`) → `reason_code_to_cause(reason_code)` ; si `ecart` ET direction 2 (`perimetre.startswith("exclu_")`) → `build_cause_for_pending_unpublish()` ; sinon → `(None, None, None)`
    - `ha_type` : `map_result.ha_entity_type if map_result else None`
  - [x] 3.3 Ajouter `"compteurs": build_ui_counters(equipments)` dans `summary` global (après `summary = build_summary(equipments)` — additive, ne pas modifier `build_summary`)
  - [x] 3.4 Ajouter `"compteurs": build_ui_counters(room_eqs)` dans chaque entrée de `rooms` (additive, aux côtés du `"summary"` existant)
  - [x] 3.5 Ne jamais supprimer les champs existants (`status_code`, `reason_code`, `detail`, `remediation`, `v1_limitation`, `status`, `confidence`, etc.) — la réponse est strictement additive
  - [x] 3.6 Ajouter les imports nécessaires pour `cause_mapping` et `ui_contract_4d`

- [x] Task 4 — Tests unitaires `test_cause_mapping.py` (AC 4)
  - [x] 4.1 Tester les 12 entrées actives de la table direction 1 (voir tableau Dev Notes — une assertion par ligne reason_code) : `ambiguous_skipped`, `probable_skipped`, `no_mapping`, `no_supported_generic_type`, `no_generic_type_configured`, `disabled_eqlogic`, `disabled`, `no_commands`, `discovery_publish_failed`, `local_availability_publish_failed`, `low_confidence`, `eligible`
  - [x] 4.2 Tester les 3 reason_codes published (`sure`, `probable`, `sure_mapping`) → chacun retourne `(None, None, None)` (pas d'écart direction 1 pour ces codes)
  - [x] 4.3 Tester le fallback : reason_code inconnu (`"unknown_xyz"`) → `(None, None, None)` (sécuritaire)
  - [x] 4.4 Tester `build_cause_for_pending_unpublish()` → valeurs exactes figées `("pending_unpublish", "Changement en attente d'application", "Republier pour appliquer le changement")`

- [x] Task 5 — Tests unitaires `test_ui_contract_4d.py` (AC 1–7)
  - [x] 5.1 Tester `reason_code_to_perimetre` : 3 cas d'exclusion (`excluded_eqlogic` → `exclu_sur_equipement`, `excluded_plugin` → `exclu_par_plugin`, `excluded_object` → `exclu_par_piece`) + fallback reason_code non-exclusion → `inclus`
  - [x] 5.2 Tester `compute_ecart` : 4 cas de la matrice obligatoire (voir Dev Notes)
  - [x] 5.3 Tester `build_ui_counters` : liste mixte (inclus/exclus/avec écarts) → compteurs corrects + invariant `total = inclus + exclus` vérifié
  - [x] 5.4 Tester `build_ui_counters` avec liste vide → `total=0, inclus=0, exclus=0, ecarts=0`
  - [x] 5.5 Tester que `ecarts` compte les deux directions : direction 1 (perimetre=inclus, ecart=true) ET direction 2 (perimetre=exclu_*, ecart=true) dans la même liste

- [x] Task 6 — Mettre à jour `test_diagnostic_endpoint.py` (AC 8)
  - [x] 6.1 Vérifier la présence des champs UI canoniques dans la réponse d'un équipement publié : `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`, `ha_type`
  - [x] 6.2 Vérifier la présence de `compteurs` dans `payload.summary` et dans chaque entrée `payload.rooms`
  - [x] 6.3 Vérifier que les champs techniques (`status_code`, `reason_code`, `detail`, etc.) restent présents (non-régression couche support)
  - [x] 6.4 Tester le cas direction 2 : simuler un équipement exclu encore présent dans HA via `publications[eq_id].active_or_alive = True` ou via `pending_discovery_unpublish` → vérifier `statut = "publie"`, `ecart = true`, `cause_code = "pending_unpublish"`

- [x] Task 7 — Exécuter la suite de tests complète (AC 8)
  - [x] 7.1 `pytest resources/daemon/tests/` → 169/169 PASS (128 existants + 41 nouveaux)
  - [x] 7.2 Tests JS `tests/unit/*.node.test.js` → 73/73 PASS (aucun JS modifié par cette story)

## Dev Notes

### Périmètre strict de Story 4.1

Cette story est **exclusivement backend Python**. Elle ne touche à aucun fichier JS, PHP, ni template Jinja.

| Frontière | Story 4.1 | Responsable |
|---|---|---|
| Consommation frontend du contrat 4D | **Hors scope** | Story 4.4 |
| Vocabulaire UI visible (exception → source d'exclusion) | **Hors scope** | Story 4.2 |
| Filtrage diagnostic in-scope côté backend | **Hors scope** | Story 4.3 |
| `taxonomy.py` (reason_codes, PRIMARY_STATUSES) | **Lecture seule — figé story 3.1** | — |
| `aggregation.py` (build_summary, compute_primary_aggregated_status) | **Lecture seule — figé story 3.3** | — |
| `_DIAGNOSTIC_MESSAGES` dans `http_server.py` | **Lecture seule — figé story 3.2** | — |
| `published_scope.py` | **Lecture seule — figé story 1.1** | — |

### Deux couches dans la réponse `/system/diagnostics`

`/system/diagnostics` sert deux usages qui coexistent dans le même payload JSON. Story 4.1 ajoute la couche UI canonique sans toucher à la couche technique.

| Couche | Champs | Usage |
|---|---|---|
| **Contrat UI canonique** (NOUVEAU — Epic 4) | `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`, `ha_type` | Consommés par le frontend en Story 4.4 — source de vérité pour la console |
| **Couche technique / support** (EXISTANT — Epics 1-3) | `status_code`, `reason_code`, `detail`, `remediation`, `v1_limitation`, `confidence`, `traceability`, `matched_commands`, `unmatched_commands` | Export support, export JSON, backward compat, tests existants |

`reason_code` reste dans la réponse JSON. Sa présence n'est pas une violation du modèle 4D — c'est la couche support backward-compatible. Ce qui change en V1.1 : le frontend (Story 4.4) consommera `cause_code`/`cause_label` et n'affichera plus `reason_code` dans la console principale.

### Contrat JSON cible par équipement

Référence : Sprint Change Proposal §V3 (approuvé 2026-03-26). Les 4 cas nominaux — les champs UI canoniques sont en tête, les champs techniques suivent dans le même objet.

**Cas 1 — Inclus et publié (aligné)**
```json
{
  "eq_id": 123,
  "name": "Lampe salon",
  "object_id": 5,
  "object_name": "Salon",
  "perimetre": "inclus",
  "statut": "publie",
  "ecart": false,
  "cause_code": null,
  "cause_label": null,
  "cause_action": null,
  "ha_type": "light",
  "status_code": "published",
  "reason_code": "sure",
  "detail": "...",
  "remediation": "..."
}
```

**Cas 2 — Inclus mais non publié (direction 1)**
```json
{
  "eq_id": 789,
  "name": "Capteur exotique",
  "object_id": 5,
  "object_name": "Salon",
  "perimetre": "inclus",
  "statut": "non_publie",
  "ecart": true,
  "cause_code": "ambiguous_skipped",
  "cause_label": "Mapping ambigu — plusieurs types possibles",
  "cause_action": "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
  "ha_type": null,
  "status_code": "ambiguous",
  "reason_code": "ambiguous_skipped",
  "detail": "Plusieurs types d'entités Home Assistant sont possibles...",
  "remediation": "Précisez les types génériques..."
}
```

**Cas 3 — Exclu et non présent dans HA (aligné)**
```json
{
  "eq_id": 456,
  "name": "Thermostat chambre",
  "object_id": 3,
  "object_name": "Chambre",
  "perimetre": "exclu_sur_equipement",
  "statut": "non_publie",
  "ecart": false,
  "cause_code": null,
  "cause_label": null,
  "cause_action": null,
  "ha_type": null,
  "status_code": "excluded",
  "reason_code": "excluded_eqlogic",
  "detail": "...",
  "remediation": "..."
}
```

**Cas 4 — Exclu mais encore présent dans HA (direction 2)**
```json
{
  "eq_id": 101,
  "name": "Lampe entrée",
  "object_id": 2,
  "object_name": "Entrée",
  "perimetre": "exclu_sur_equipement",
  "statut": "publie",
  "ecart": true,
  "cause_code": "pending_unpublish",
  "cause_label": "Changement en attente d'application",
  "cause_action": "Republier pour appliquer le changement",
  "ha_type": "light",
  "status_code": "excluded",
  "reason_code": "excluded_eqlogic",
  "detail": "...",
  "remediation": "..."
}
```

Note sur le Cas 4 : `status_code = "excluded"` (décision pipeline), mais `statut = "publie"` (état HA réel — retained MQTT encore présent). Ce n'est pas une incohérence : les deux champs appartiennent à des couches différentes et coexistent normalement.

### Compteurs cibles par pièce et global

**Ajout dans `payload.summary`** (additive — aux côtés de `primary_aggregated_status`, `total_equipments`, `counts_by_status`, `counts_by_reason`) :
```json
"compteurs": {
  "total": 278,
  "inclus": 99,
  "exclus": 179,
  "ecarts": 5
}
```

**Ajout dans chaque entrée de `payload.rooms`** (additive) :
```json
{
  "object_id": 5,
  "object_name": "Salon",
  "summary": { "primary_aggregated_status": "...", "..." : "..." },
  "compteurs": {
    "total": 12,
    "inclus": 8,
    "exclus": 4,
    "ecarts": 2
  }
}
```

Invariant obligatoire : `total = inclus + exclus`. Les `ecarts` couvrent les deux directions — un équipement exclu-mais-encore-publié compte dans `exclus` ET dans `ecarts`.

### Table de traduction reason_code → cause_code (direction 1 — inclus mais non publié)

À implémenter dans `resources/daemon/models/cause_mapping.py`. Table figée — 12 entrées actives, 3 codes published, 1 fallback.

**12 entrées actives (reason_code → (cause_code, cause_label, cause_action)) :**

| reason_code | cause_code | cause_label | cause_action |
|---|---|---|---|
| `ambiguous_skipped` | `ambiguous_skipped` | `Mapping ambigu — plusieurs types possibles` | `Préciser les types génériques sur les commandes pour lever l'ambiguïté` |
| `probable_skipped` | `ambiguous_skipped` | `Mapping ambigu — plusieurs types possibles` | `Préciser les types génériques sur les commandes pour lever l'ambiguïté` |
| `no_mapping` | `no_mapping` | `Aucun mapping compatible` | `Vérifier les types génériques des commandes dans Jeedom` |
| `no_supported_generic_type` | `no_supported_generic_type` | `Type non supporté en V1` | `None` |
| `no_generic_type_configured` | `no_generic_type_configured` | `Types génériques non configurés sur les commandes` | `Configurer les types génériques via le plugin Jeedom concerné, puis relancer un rescan` |
| `disabled_eqlogic` | `disabled_eqlogic` | `Équipement désactivé dans Jeedom` | `Activer l'équipement dans sa page de configuration Jeedom` |
| `disabled` | `disabled_eqlogic` | `Équipement désactivé dans Jeedom` | `Activer l'équipement dans sa page de configuration Jeedom` |
| `no_commands` | `no_commands` | `Équipement sans commandes exploitables` | `Vérifier que l'équipement possède des commandes actives dans Jeedom` |
| `discovery_publish_failed` | `discovery_publish_failed` | `Publication MQTT échouée` | `Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution` |
| `local_availability_publish_failed` | `discovery_publish_failed` | `Publication MQTT échouée` | `Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution` |
| `low_confidence` | `no_mapping` | `Aucun mapping compatible` | `Vérifier les types génériques des commandes dans Jeedom` |
| `eligible` | `no_mapping` | `Aucun mapping compatible` | `Relancer un sync complet depuis l'interface du plugin` |

**3 codes published → `(None, None, None)` (pas d'écart direction 1) :** `sure`, `probable`, `sure_mapping`

**Fallback (reason_code inconnu) → `(None, None, None)` (sécuritaire)**

**Table direction 2 — exclu mais encore publié (implémentée dans `build_cause_for_pending_unpublish`) :**

| Signal | cause_code | cause_label | cause_action |
|---|---|---|---|
| `is_published_in_ha == True` sur équipement `perimetre = exclu_*` | `pending_unpublish` | `Changement en attente d'application` | `Republier pour appliquer le changement` |

> `is_published_in_ha` = `publications[eq_id].active_or_alive` OR `eq_id in pending_discovery_unpublish`. Pas `has_pending`.

### Dérivation du champ `perimetre`

À implémenter dans `ui_contract_4d.py`, fonction `reason_code_to_perimetre`. Mapping déterministe :

| reason_code | perimetre |
|---|---|
| `excluded_eqlogic` | `exclu_sur_equipement` |
| `excluded_plugin` | `exclu_par_plugin` |
| `excluded_object` | `exclu_par_piece` |
| tout autre reason_code | `inclus` |

Rationale : l'exclusion d'un équipement passe toujours par l'un de ces 3 reason_codes. Tous les autres cas (published, ambiguous, not_supported, infra) concernent des équipements inclus dans le périmètre mais non publiés pour une raison métier ou technique.

### Dérivation canonique de `statut`

`statut` reflète l'état HA réel (est-ce que l'équipement est physiquement présent dans HA ?), pas la décision du pipeline ni le flag `has_pending`.

**Formule unique — source de vérité exclusive (corrigée terrain 2026-03-27) :**

```python
_pub = publications.get(eq_id)
is_published_in_ha = bool(_pub and _pub.active_or_alive) or eq_id in pending_discovery_unpublish
statut = "publie" if is_published_in_ha else "non_publie"
```

- `_pub.active_or_alive == True` : le daemon a une publication active et vivante pour cet équipement dans HA.
- `eq_id in pending_discovery_unpublish` : un unpublish a été reporté (deferred) → l'équipement est encore retained dans le broker MQTT.

**HYPOTHÈSE INVALIDÉE (terrain 2026-03-27)** : L'ancienne formule `statut = "publie" if (status_code == "published" or has_pending) else "non_publie"` était fausse. `has_pending_home_assistant_changes` est un XOR (`desired_state != actual_state`) qui vaut `True` aussi bien pour un inclus-non-publié que pour un exclu-encore-publié. Sur 69 équipements inclus non publiés, `has_pending=True` provoquait `statut="publie"` — un faux positif massif.

### Formule exacte de l'écart (corrigée terrain 2026-03-27)

```python
def compute_ecart(perimetre: str, statut: str) -> bool:
    direction_1 = (perimetre == "inclus") and (statut == "non_publie")
    direction_2 = perimetre.startswith("exclu_") and (statut == "publie")
    return direction_1 or direction_2
```

`compute_ecart` est une fonction pure de `(perimetre, statut)` uniquement. Le paramètre `has_pending` a été supprimé — c'est un XOR ambigü qui ne peut pas discriminer les directions.

**Matrice des 4 cas (tous testés obligatoirement) :**

| perimetre | is_published_in_ha | statut | ecart | direction |
|---|---|---|---|---|
| `inclus` | True | `publie` | `false` | aligné |
| `inclus` | False | `non_publie` | `true` | direction 1 |
| `exclu_*` | False | `non_publie` | `false` | aligné |
| `exclu_*` | True | `publie` | `true` | direction 2 |

### Comment déterminer la présence HA réelle dans le diagnostics handler

**FIX terrain 2026-03-27** : l'ancienne section utilisait `has_pending_home_assistant_changes` via `published_scope`. Ce signal est un XOR (`desired != actual`) et ne peut PAS servir de proxy de présence HA.

Dans `_handle_system_diagnostics`, AVANT la boucle équipement :

```python
# Vrais signaux de présence HA réelle (pas has_pending — XOR ambigü)
pending_discovery_unpublish = request.app.get("pending_discovery_unpublish") or {}
# publications est déjà accessible : publications = request.app.get("publications", {})
```

Puis dans la boucle, pour chaque `eq` :
```python
_pub = publications.get(eq_id)
is_published_in_ha = bool(_pub and _pub.active_or_alive) or eq_id in pending_discovery_unpublish
statut = "publie" if is_published_in_ha else "non_publie"
```

Soft-fail : si `publications` est vide (pas encore de sync), aucun équipement n'est marqué publié. Si `pending_discovery_unpublish` est vide, aucun deferred unpublish. Aucune exception.

### Fichiers à créer / modifier

| Fichier | Action |
|---|---|
| `resources/daemon/models/cause_mapping.py` | **CRÉER** — table de traduction pure, standalone |
| `resources/daemon/models/ui_contract_4d.py` | **CRÉER** — fonctions perimetre, statut, ecart, compteurs |
| `resources/daemon/transport/http_server.py` | **MODIFIER** — ajouter champs 4D + compteurs dans `_handle_system_diagnostics` |
| `resources/daemon/tests/unit/test_cause_mapping.py` | **CRÉER** — 16 tests (12 actifs + 3 published + 1 fallback + direction 2) |
| `resources/daemon/tests/unit/test_ui_contract_4d.py` | **CRÉER** — tests unitaires 4D |
| `resources/daemon/tests/unit/test_diagnostic_endpoint.py` | **MODIFIER** — assertions sur nouveaux champs |

**Fichiers à ne PAS toucher :**
- `resources/daemon/models/taxonomy.py` (figé story 3.1)
- `resources/daemon/models/aggregation.py` (figé story 3.3)
- `resources/daemon/models/published_scope.py` (figé story 1.1)
- Tout fichier `desktop/js/` ou `desktop/php/` ou `core/` (scope story 4.4)

### Dev Agent Guardrails

1. **Ne jamais renommer les `reason_code`** — stables Epic 3, restent dans la couche technique de la réponse.
2. **Ne jamais supprimer les champs techniques** (`status_code`, `reason_code`, `detail`, `remediation`, `v1_limitation`, etc.) — la réponse est strictement additive.
3. **Ne jamais exposer `inherit`** dans `perimetre` — la valeur est toujours résolue avant sérialisation.
4. **Une seule formule pour `statut`** : `"publie" if is_published_in_ha else "non_publie"` où `is_published_in_ha = bool(pub and pub.active_or_alive) or eq_id in pending_discovery_unpublish`. NE JAMAIS utiliser `has_pending_home_assistant_changes` comme proxy de présence HA (XOR ambigü — invalidé terrain 2026-03-27).
5. **Ne jamais calculer `ecart` côté UI** (JS ou PHP) — ce booléen est calculé uniquement en Python backend.
6. **`cause_mapping.py` est une table statique** — pas de logique conditionnelle, pas d'appel externe, pas de dépendance sur d'autres modules.
7. **`aggregation.py` est figé** — `build_summary` n'est pas modifié. `compteurs` est ajouté à côté du résultat de `build_summary`, jamais à l'intérieur.
8. **`taxonomy.py` est figé** — `PRIMARY_STATUSES`, `REASON_CODE_TO_PRIMARY_STATUS`, `get_primary_status` sont lus en lecture seule.
9. **Soft-fail obligatoire** sur `request.app.get("published_scope")` — si `None`, dict vide, pas d'exception.
10. **La traduction est en SORTIE du pipeline** — ne pas modifier le pipeline central (topologie → eligibilité → mapping → décision → reason_code). La traduction `reason_code → cause_code` se fait uniquement à la sérialisation de la réponse API.

### Contexte de précédents (Story 3.4)

Story 3.4 a livré l'intégration UI du contrat métier Epic 3. Patterns établis à respecter :
- **Option B** relay PHP : `jeedom2ha.ajax.php` enrichit la réponse avant envoi au JS — pas de second appel HTTP depuis le JS.
- **Audit de non-recomposition** : le frontend ne reconstruit pas de statut à partir de champs bruts. Les tests JS (73/73) le vérifient.
- **128/128 pytest** existants — tous doivent rester verts.
- `status_code` reste la source de la couche pipeline (`build_summary`, badges existants). Il coexiste avec `statut` dans le même objet équipement.

### Structure de tests attendue

```
resources/daemon/tests/unit/
├── test_cause_mapping.py         (NOUVEAU — 16+ tests : 12 actifs + 3 published + 1 fallback + direction 2)
├── test_ui_contract_4d.py        (NOUVEAU — ~15 tests : perimetre, statut, ecart, compteurs)
├── test_diagnostic_endpoint.py   (MODIFIER — ajouter ~6 assertions sur champs 4D + compteurs)
└── ...                           (inchangés)
```

Harness de test existant : `pytest resources/daemon/tests/` depuis la racine du projet.

### Project Structure Notes

- `cause_mapping.py` et `ui_contract_4d.py` suivent le pattern des modules `resources/daemon/models/` : commentaire `# ARTEFACT FIGÉ — Story 4.1.` en tête, imports minimaux, fonctions pures sans side effects.
- Convention Python : snake_case, docstring de module, fonctions pures.
- Pattern de test : `tests/unit/`, isolation totale sans daemon en cours d'exécution.
- Commit message convention : `feat(story-4.1): <description courte>` (cf. historique git).

### References

- [Source: Sprint Change Proposal §V3] — Contrat JSON cible complet, valeurs autorisées, les 4 cas nominaux
- [Source: Sprint Change Proposal §V5] — Table cause_code / cause_label bidirectionnelle (direction 1 + direction 2)
- [Source: Architecture delta review §8.1] — Modèle 4D, définition des 4 dimensions
- [Source: Architecture delta review §8.2] — Formule exacte de l'écart (bidirectionnel), définition de `est_publie_ha`
- [Source: Architecture delta review §8.3] — Contrat dual reason_code/cause_code : `reason_code` = couche backend stable, `cause_code/cause_label` = contrat UI canonique
- [Source: Architecture delta review §8.4] — Compteurs pièce/global, invariant `total = inclus + exclus`
- [Source: Architecture delta review §8.7] — Gouvernance : le frontend n'interprète jamais
- [Source: Epics §Epic 4 Story 4.1] — User story, AC BDD, dépendances autorisées (1.1, 3.1, 3.2)
- [Source: Test Strategy §invariants 10-17] — Invariants contractuels à couvrir pour l'Epic 4
- [Source: resources/daemon/models/taxonomy.py] — reason_codes stables (figés story 3.1)
- [Source: resources/daemon/transport/http_server.py:1228] — `_DIAGNOSTIC_MESSAGES` (figé story 3.2)
- [Source: resources/daemon/models/aggregation.py] — `build_summary` (figé story 3.3)
- [Source: resources/daemon/transport/http_server.py:146] — `_apply_pending_scope_flags`, champ `has_pending_home_assistant_changes`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (implémentation initiale), claude-opus-4-6 (correction terrain 2026-03-27)

### Debug Log References

Implémentation initiale : ajustement syntaxe Python 3.9 résolu immédiatement.
Correction terrain 2026-03-27 : `has_pending_home_assistant_changes` utilisé comme proxy de présence HA → 69 faux positifs sur terrain réel (inclus non publiés marqués `statut="publie"`). Cause racine : `has_pending` est un XOR (`desired != actual`), pas un indicateur de présence.

### Completion Notes List

- **Implémentation initiale** :
  - `cause_mapping.py` créé : table figée 12 entrées actives + 3 published + 1 fallback + direction 2. Module pur, standalone.
  - `ui_contract_4d.py` créé : `reason_code_to_perimetre`, `compute_ecart`, `build_ui_counters`.
  - `http_server.py` modifié additivement : champs 4D insérés dans chaque `eq_dict`, `compteurs` ajoutés.
- **Correction terrain 2026-03-27 (4.1-fix)** :
  - `ui_contract_4d.py` corrigé : `compute_ecart(perimetre, statut)` — paramètre `has_pending` supprimé. Direction 2 utilise `statut == "publie"` au lieu de `has_pending`.
  - `http_server.py` corrigé : formule `statut` remplacée par `is_published_in_ha` basé sur `publications[eq_id].active_or_alive` + `pending_discovery_unpublish`. Suppression du lookup `_pending_by_eq_id` (plus nécessaire).
  - Guardrail levé : ancien guardrail 4 (formule `has_pending`) remplacé par la formule correcte.
  - Guardrail ajouté : test de signature `compute_ecart` empêche la ré-introduction de `has_pending` comme paramètre.
- Suite complète : 173/173 pytest PASS, 73/73 JS PASS.
- Guardrails respectés : `taxonomy.py`, `aggregation.py`, `published_scope.py` non modifiés. `cause_mapping.py` non modifié. Séparation `reason_code` / `cause_code` préservée. Réponse additive. Compteurs intacts. Frontend non touché.

### File List

- `resources/daemon/models/cause_mapping.py` — CRÉÉ
- `resources/daemon/models/ui_contract_4d.py` — CRÉÉ
- `resources/daemon/transport/http_server.py` — MODIFIÉ
- `resources/daemon/tests/unit/test_cause_mapping.py` — CRÉÉ
- `resources/daemon/tests/unit/test_ui_contract_4d.py` — CRÉÉ
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py` — MODIFIÉ
- `_bmad-output/implementation-artifacts/4-1-contrat-backend-du-modele-perimetre-statut-ecart-cause.md` — MODIFIÉ
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — MODIFIÉ

## Change Log

- **2026-03-27 (implémentation initiale)** : Story 4.1 livrée — 7 tasks, 41 nouveaux tests, 169/169 pytest, 73/73 JS. Contrat 4D additif dans `_handle_system_diagnostics`.
- **2026-03-27 (correction terrain 4.1-fix)** : Terrain FAIL — 69 inclus non publiés avaient `statut="publie"` à cause de `has_pending` (XOR ambigü). Correction : `statut` dérivé de `publications[eq_id].active_or_alive || pending_discovery_unpublish`, `compute_ecart` simplifié à `(perimetre, statut)`. 4 nouveaux tests garde-fou. 173/173 pytest, 73/73 JS.
