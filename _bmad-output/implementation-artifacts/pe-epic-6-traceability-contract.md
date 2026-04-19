# Contrat canonique de traçabilité — pe-epic-6

**Date :** 2026-04-19
**Statut :** canonique — prérequis pe-epic-6
**Owners :** Winston (Architect) + Charlie (Senior Dev)
**Gate out :** tout dev entrant dans `_build_traceability()` navigue sans ambiguïté

---

## 1. Source de vérité unique de la cause canonique

La cause canonique d'un équipement est **exclusivement portée par `map_result.publication_decision_ref.reason`** (champ `reason` du `PublicationDecision` produit par l'étape 4 et câblé dans `MappingResult` à la fin de cette étape).

```
MappingResult.publication_decision_ref   ← source canonique unique (étape 4)
MappingResult.publication_result         ← résultat technique exclusif (étape 5)
```

Il n'existe **pas** de seconde source de vérité pour la cause canonique.

---

## 2. Rôle de chaque bloc

### `publication_decision_ref` (étape 4 — décision produit)

- Porte la **cause canonique** : ce que le pipeline a décidé de faire, et pourquoi.
- Son champ `reason` est toujours un code décisionnel des étapes 1–4.
- Câblé sur `MappingResult` à la fin de l'étape 4 (`mapping.publication_decision_ref = decision`).
- **Jamais modifié** après l'étape 4.

### `publication_result` (étape 5 — résultat technique)

- Porte le résultat **technique** de la publication MQTT : succès, échec ou non tenté.
- Son champ `technical_reason_code` contient les codes infra (`discovery_publish_failed`, `local_availability_publish_failed`).
- **N'influence jamais** la cause canonique.
- Visible dans `publication_trace` du diagnostic, jamais dans `decision_trace`.

---

## 3. Invariant I7 — non-masquage (opposable en review)

> **Aucun code, à aucun endroit, ne peut placer un `technical_reason_code` de l'étape 5 dans `decision_trace.reason_code`.**

### Formulation négative (ce qui est interdit)

- Interdit : `decision_trace.reason_code = "discovery_publish_failed"`
- Interdit : `decision_trace.reason_code = "local_availability_publish_failed"`
- Interdit : toute logique lisant `publication_result.technical_reason_code` pour alimenter `canonical_reason` ou `closed_reason`
- Interdit : tout alias ou fallback faisant de `publication_result` une source de la cause canonique

### Formulation positive

```
decision_trace.reason_code  ← codes étapes 1–4 uniquement
publication_trace           ← codes techniques étape 5 uniquement
```

Ces deux dimensions **coexistent** dans le diagnostic sans jamais se substituer l'une à l'autre.

---

## 4. Frontières conceptuelles

| Dimension | Responsable | Porte | N'écrit jamais dans |
|-----------|-------------|-------|---------------------|
| **Décision** (étapes 1–4) | `publication_decision_ref.reason` | Cause du pipeline | `publication_trace` |
| **Traçabilité** | `_build_traceability()` | Structure du diagnostic | Aucune source de vérité |
| **Résultat technique** (étape 5) | `publication_result` | Outcome MQTT | `decision_trace` |
| **Rendu diagnostic** (UI) | `cause_mapping.py` / frontend | `cause_code`, `cause_label` | Aucune source de vérité |

Aucun mélange de responsabilité autorisé entre ces quatre couches.

---

## 5. Décision sur l'aliasing — Option A retenue

### Situation avant ce livrable

`_build_traceability()` acceptait deux sources potentielles pour la décision canonique :
1. `map_result.publication_decision_ref` (prioritaire)
2. le paramètre `pub_decision` passé séparément (fallback)

Ces deux champs désignaient toujours le même objet en production, créant une illusion de double source de vérité.

### Décision : Option A — suppression de l'alias

Le paramètre `pub_decision` a été **supprimé** de la signature de `_build_traceability()`.

```python
# Avant (ambigu)
def _build_traceability(eq, map_result, pub_decision, status, top_reason_code) -> dict:
    canonical_decision = (
        getattr(map_result, "publication_decision_ref", None) or pub_decision
    )

# Après (source unique)
def _build_traceability(eq, map_result, status, top_reason_code) -> dict:
    canonical_decision = map_result.publication_decision_ref if map_result else None
```

La fonction lit exclusivement `map_result.publication_decision_ref`. Un dev lisant le code ne voit qu'une seule source possible.

### Fallback transitoire (compatibilité legacy)

Si `map_result.publication_decision_ref` est `None` (objets antérieurs à story 5.2 sans step-4 explicite), `canonical_reason` tombe sur `top_reason_code`. Ce fallback est **transitoire** : il ne constitue pas une source canonique, et ne peut être atteint dans le pipeline courant (l'étape 4 câble toujours `publication_decision_ref`). Il est documenté comme tel dans la docstring de la fonction.

---

## 6. Codes step-5 retirés de `_CLOSED_REASON_MAP`

`"discovery_publish_failed"` et `"local_availability_publish_failed"` ont été **retirés** de `_CLOSED_REASON_MAP`.

```python
# Avant (vecteur de contamination I7)
"discovery_publish_failed": "discovery_publish_failed",
"local_availability_publish_failed": "discovery_publish_failed",

# Après : absents — ces codes n'ont pas de place dans decision_trace
```

Le commentaire du map documente explicitement l'invariant :
> Les codes techniques de l'étape 5 sont interdits ici — ils n'appartiennent qu'à `publication_trace` (invariant I7).

---

## 7. Analyse des trois dérives story 5.2

### Dérive 1 — `reason_code ← technical_reason_code` au lieu de `canonical_dec.reason`

**Chemin de dérive :** La logique calculait `reason_code` depuis `publication_result.technical_reason_code` en oubliant de lire `canonical_dec.reason` en premier.

**Comment ce livrable l'empêche :** `_build_traceability()` lit `canonical_reason` **exclusivement** depuis `canonical_decision.reason` (champ step-4). `publication_result.technical_reason_code` n'est lu que pour construire `publication_trace` (section 4 de la fonction), jamais pour `canonical_reason`. La séparation est structurelle dans le corps de la fonction.

---

### Dérive 2 — `_needs_discovery_unpublish()` fallback incorrect

**Chemin de dérive :** La fonction marquait des équipements "à dépublier" après un échec de publication initiale, en utilisant `should_publish=True` comme proxy de présence HA — à tort pour des équipements jamais publiés.

**Pourquoi ce livrable ne la couvre pas :** Cette dérive était dans `_needs_discovery_unpublish()`, une fonction distincte sans lien avec `_build_traceability()` ni avec l'aliasing `pub_decision`. Elle a été corrigée dans story 5.2 à sa source propre. Elle n'appartient pas au périmètre du contrat de traçabilité.

---

### Dérive 3 — `_CLOSED_REASON_MAP` retournait `"discovery_publish_failed"` comme cause canonique

**Chemin de dérive :** Le map contenait `"discovery_publish_failed": "discovery_publish_failed"` et `"local_availability_publish_failed": "discovery_publish_failed"`. Si `canonical_reason` portait un code step-5 (via `top_reason_code` en état legacy), il traversait le map et contaminait `decision_trace.reason_code` d'un code technique.

**Comment ce livrable l'empêche :**
1. Les deux entrées step-5 ont été **retirées** du map — elles ne peuvent plus produire de valeur dans `decision_trace`.
2. En parallèle, `_build_traceability()` lit `canonical_reason` depuis `canonical_decision.reason` (step-4), jamais depuis `top_reason_code` quand `canonical_decision` est disponible. Le `top_reason_code` ne peut donc contaminer `canonical_reason` que si `publication_decision_ref` est absent (état legacy inatteignable dans le pipeline courant).

---

## 8. Validation de robustesse

| Critère | Statut |
|---------|--------|
| Plus aucune ambiguïté sur la source de la cause canonique | ✅ Un seul champ : `publication_decision_ref.reason` |
| Plus aucun alias implicite dans `_build_traceability()` | ✅ `pub_decision` supprimé de la signature |
| `_CLOSED_REASON_MAP` sans codes step-5 | ✅ Deux entrées retirées + commentaire explicite |
| Tests I7 : dérive 1 et 3 réintroduites → FAIL | ✅ 426/426 PASS, tests réécrits pour prouver I7 |
| Dev entrant dans `_build_traceability()` comprend immédiatement le modèle | ✅ Docstring + signature épurée |

## 9. Intégration dans le cadre de gouvernance pe-epic-5 / pe-epic-6

Ce contrat est :

- référencé dans le gate de readiness pe-epic-6 comme livrable P-1/P-2
- opposable en review selon le micro-protocole GOV-PE5-xxx
- soumis à la règle de préséance documentaire définie dans pe-epic-5-document-precedence.md

Toute modification future de `_build_traceability()` ou des structures associées doit :

- référencer explicitement ce contrat
- démontrer le respect de l’invariant I7
- être validée en review contre ce document

**GO — le modèle est structurellement sûr pour pe-epic-6.**
