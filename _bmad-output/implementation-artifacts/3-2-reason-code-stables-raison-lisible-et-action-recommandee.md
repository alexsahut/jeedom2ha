# Story 3.2 : `reason_code` stables, raison lisible et action recommandée

Status: done

---

## Story

En tant qu'utilisateur Jeedom,
je veux une raison principale compréhensible et une action simple quand elle existe,
afin de corriger un non-publié sans expertise MQTT.

---

## Contexte et objectif

### Situation actuelle (à corriger dans cette story)

Story 3.1 a livré `taxonomy.py` — la taxonomie fermée à 5 statuts avec le mapping
`reason_code → primary_status`. Ce contrat est figé et consommé en **lecture seule** par la présente story.

Cependant, la couche `_DIAGNOSTIC_MESSAGES` (textes de raison + action recommandée) présente des lacunes
identifiées. L'ampleur exacte doit être confirmée par un audit préalable avant toute modification :

**Lacunes bloquantes — scope direct des AC :**

| Problème identifié | Impact utilisateur |
|---|---|
| Certains `reason_code` du mapping (à confirmer par audit Task 1.2) sont suspectés absents de `_DIAGNOSTIC_MESSAGES` (`probable`, `low_confidence`, `no_generic_type_configured` sont des candidats mais non confirmés) | Ces codes tomberaient dans `_DIAGNOSTIC_DEFAULT` : "Cause inconnue." — réponse inacceptable pour les cas non-publiés |
| `no_supported_generic_type` a `v1_limitation=True` mais le `detail` ne mentionne pas "Home Assistant" | L'utilisateur ne sait pas si la limite vient du plugin ou de HA |
| `no_mapping` a `v1_limitation=True` — le texte mentionne HA mais peut être renforcé | Mention partielle |
| Aucun test ne vérifie que 100 % des `reason_code` du mapping ont une entrée dans `_DIAGNOSTIC_MESSAGES` | Dérive silencieuse possible sur les stories suivantes |
| Aucun test ne vérifie que 100 % des `reason_code` ont un label dans `reasonLabels` JS | Idem |

**Observations de vigilance — hors scope direct des AC :**

| Code | Observation | Action dans cette story |
|---|---|---|
| `sure` (`published`) | `detail` potentiellement inadapté pour le cas nominal publié | Audit Task 1.5 — documenter en PR uniquement, correction non obligatoire |
| `sure_mapping` | Absent de `REASON_CODE_TO_PRIMARY_STATUS` — code fantôme d'état inconnu | Audit Task 1.3 — documenter en PR, décision de suppression post-audit |
| `eligible` | Non-terminal documenté Story 3.1 — présence dans `_DIAGNOSTIC_MESSAGES` | Audit Task 1.4 — documenter en PR, présence inoffensive si non émis |

### Objectif de Story 3.2

Compléter et stabiliser le contrat "raison lisible + action recommandée" du backend pour que :

1. Chaque `reason_code` de `REASON_CODE_TO_PRIMARY_STATUS` correspondant aux cas non publiés ou ambigus retourne une raison lisible non-fallback.
2. Les limitations Home Assistant sont explicitement libellées comme telles dans le `detail`.
3. Le `reason_code` est déterministe : deux diagnostics sur le même cas produisent le même code.
4. Les deux gardes-fous AI-3 sont en place : complétude `_DIAGNOSTIC_MESSAGES` et complétude `reasonLabels` JS.

### Frontière story 3.2 vs stories adjacentes

| Frontière | Story 3.2 | Limites |
|---|---|---|
| Taxonomie des statuts principaux | **Lecture seule** — `taxonomy.py` inchangé | Story 3.1 (figé) |
| Structure du payload (noms de champs) | **Inchangée** — contenu enrichi, pas de nouveau champ | N/A |
| Badge `v1_limitation` dans l'UI | Mise à jour du libellé uniquement (mention HA) | Rendu complet → Story 3.4 |
| Rendu conditionnel selon `unmatched_commands` | **Hors scope** | Story 3.4 |
| Agrégations pièce / global | Hors scope | Story 3.3 |
| Rendu UI complet du contrat | Hors scope | Story 3.4 |
| Nouveaux `reason_code` non encore émis | Hors scope | Stories futures si besoin |
| Remédiation guidée multi-étapes | Hors scope | Epic 4+ |

---

## Dépendances autorisées

- **Story 3.1** (done — PR #44 mergée 2026-03-25) : `taxonomy.py` contrat figé, consommé en lecture seule.
  - Artefact : `resources/daemon/models/taxonomy.py`
  - Exports utilisés : `REASON_CODE_TO_PRIMARY_STATUS` (16 codes, source de vérité)
- Aucune dépendance en avant.

---

## Guardrails obligatoires

### AI-1 — Taxonomie verrouillée par 3.1

3.2 **consomme** `taxonomy.py` en lecture seule. `REASON_CODE_TO_PRIMARY_STATUS` est la source de
vérité des codes attendus. Story 3.2 n'ajoute, ne renomme, n'interprète aucun statut principal.

**Critère de code review :** `taxonomy.py` doit être **inchangé** dans la PR 3.2
(git diff sur ce fichier = vide).

### AI-2 — Atomicité obligatoire

Toute modification de `_DIAGNOSTIC_MESSAGES` (backend Python) doit être dans le **même commit** que :
- la mise à jour du badge `v1_limitation` dans `desktop/js/jeedom2ha.js`,
- tous les tests associés.

Aucun état intermédiaire toléré (zéro label "Cause inconnue." en backend + badge obsolète en JS).

### AI-3 — Garde-fou de synchronisation backend/frontend — étendu en 3.2

Story 3.1 a livré les couches 1 et 2 du garde-fou AI-3 (statuts principaux). Story 3.2 ajoute deux
couches supplémentaires qui sont **permanentes** :

**Couche 3 — Python, complétude `_DIAGNOSTIC_MESSAGES`** (`test_story_3_2_reason_completeness.py`) :
- Vérifie que chaque code de `REASON_CODE_TO_PRIMARY_STATUS` a une entrée dans `_DIAGNOSTIC_MESSAGES`.
- Vérifie que les codes avec `v1_limitation=True` contiennent "Home Assistant" dans leur `detail`.
- Échoue si un code du mapping retourne `_DIAGNOSTIC_DEFAULT` ("Cause inconnue.").

**Couche 4 — Python, complétude `reasonLabels` JS** (`test_story_3_2_reason_labels_sync.py`) :
- Extrait le bloc `reasonLabels` de `jeedom2ha.js` via regex.
- Vérifie que chaque code de `REASON_CODE_TO_PRIMARY_STATUS` a une clé dans ce bloc.
- Échoue si le bloc `reasonLabels` est introuvable dans le fichier JS.

Ces deux tests rejoignent la suite permanente de l'Epic 3. **Ne pas les affaiblir ni les supprimer.**

### AI-7 — Vérification intégrée à la code review

La code review de Story 3.2 doit vérifier explicitement :
1. `taxonomy.py` n'a pas été modifié (AI-1).
2. `test_story_3_2_reason_completeness.py` est présent et passe (AI-3 couche 3).
3. `test_story_3_2_reason_labels_sync.py` est présent et passe (AI-3 couche 4).
4. Aucun code de `REASON_CODE_TO_PRIMARY_STATUS` ne retourne `_DIAGNOSTIC_DEFAULT`.
5. Les codes avec `v1_limitation=True` mentionnent "Home Assistant" dans leur `detail`.
6. La modification JS du badge est dans le même commit que la modification Python (AI-2).

---

## Acceptance Criteria

### AC 1 — Les `reason_code` correspondant aux cas non publiés ou ambigus ont une raison lisible non-fallback

**Given** un équipement non publié ou ambigu dont le `reason_code` appartient à `REASON_CODE_TO_PRIMARY_STATUS`
**When** `/system/diagnostics` est appelé
**Then** le champ `detail` est non-vide et ne contient pas "Cause inconnue."
**And** le champ `remediation` est soit une action lisible, soit vide intentionnellement (aucune action possible)

> **Note de bornage :** les codes avec `primary_status = "published"` (`sure`, `probable`) sont hors du périmètre de cet AC — un `detail` vide ou générique est acceptable pour un équipement correctement publié. L'audit de `sure.detail` (Task 1.5) est une observation de vigilance documentée en PR, pas une obligation de correction. Le cas `sure` + `unmatched_commands > 0` (publication partielle) est borné vers Story 3.4.

### AC 2 — Les limites Home Assistant sont explicitement libellées

**Given** un équipement dont le `reason_code` a `v1_limitation = True` dans `_DIAGNOSTIC_MESSAGES`
**When** la raison est affichée dans `/system/diagnostics`
**Then** le texte du champ `detail` contient explicitement les mots "Home Assistant"

**Given** le badge `v1_limitation` est rendu dans l'UI
**When** l'utilisateur lit le badge
**Then** le badge mentionne explicitement "Home Assistant" (pas seulement "Hors périmètre V1")

### AC 3 — Le `reason_code` est déterministe

**Given** deux exécutions du diagnostic sur le même équipement dans le même état
**When** les résultats sont comparés
**Then** le champ `reason_code` est identique dans les deux réponses
**And** le champ `detail` est identique dans les deux réponses

### AC 4 — Les gardes-fous AI-3 couches 3 et 4 sont opérationnels

**Given** les 16 `reason_code` définis dans `REASON_CODE_TO_PRIMARY_STATUS`
**When** `test_story_3_2_reason_completeness.py` est exécuté
**Then** chaque code a une entrée dans `_DIAGNOSTIC_MESSAGES`
**And** les codes `v1_limitation=True` contiennent "Home Assistant" dans leur `detail`
**And** aucun code du mapping ne retourne `_DIAGNOSTIC_DEFAULT`

**Given** les 16 `reason_code` définis dans `REASON_CODE_TO_PRIMARY_STATUS`
**When** `test_story_3_2_reason_labels_sync.py` est exécuté
**Then** chaque code a une clé dans le bloc `reasonLabels` extrait de `jeedom2ha.js`
**And** le test échoue si le bloc `reasonLabels` est introuvable dans le JS

---

## Tasks / Subtasks

- [x] Task 1 — Audit préalable : cartographier l'état réel avant toute modification (base de toutes les corrections)
  - [x] 1.1 — Lire `taxonomy.py::REASON_CODE_TO_PRIMARY_STATUS` (lecture seule) et lister les 16 codes attendus
  - [x] 1.2 — Croiser avec les clés de `_DIAGNOSTIC_MESSAGES` : confirmer les codes manquants et les codes suspects (`sure_mapping`, `eligible`)
  - [x] 1.3 — Vérifier si `sure_mapping` est encore émis : `grep -rn sure_mapping resources/daemon/` — documenter le résultat
  - [x] 1.4 — Confirmer que `eligible` ne sort jamais de `_handle_system_diagnostics` (non-terminal, documenté Story 3.1) — documenter le résultat
  - [x] 1.5 — Vigilance uniquement : vérifier que `sure.detail` n'est pas un message problématique pour le cas nominal publié — résultat documenté en commentaire PR uniquement, aucune correction obligatoire (hors AC)
  - [x] 1.6 — Documenter le résultat de l'audit (2-3 lignes en commentaire PR) avant de modifier le code

- [x] Task 2 — Ajouter les entries manquantes confirmées par l'audit dans `_DIAGNOSTIC_MESSAGES` (AC 1)
  - [x] 2.1 — Ajouter les entries manquantes confirmées par l'audit (Task 1.2) — les codes concernés et leur wording sont déterminés par l'audit, pas pré-fixés
    - Chaque entry ajoutée doit avoir : `detail` non-vide et non-fallback, `remediation` pertinente ou vide intentionnellement, `v1_limitation` selon la nature du blocage
  - [x] 2.2 — Vérifier que les nouvelles entries ne retournent pas `_DIAGNOSTIC_DEFAULT` avant commit

- [x] Task 3 — Corriger les entries existantes identifiées par l'audit (AC 1, AC 2)
  - [x] 3.1 — Pour chaque code avec `v1_limitation=True` dont le `detail` ne mentionne pas "Home Assistant" : mettre à jour le `detail` pour mention HA explicite (au minimum : `no_supported_generic_type`, potentiellement `no_mapping`)
  - [x] 3.2 — `sure` (vigilance) : documenter le résultat de l'audit Task 1.5 en commentaire PR — hors AC 1, aucune correction obligatoire par cette story
    - Le cas partiel (`sure` + `unmatched_commands > 0`) reste **hors scope** → Story 3.4
  - [x] 3.3 — `sure_mapping` (vigilance) : documenter le résultat de l'audit (Task 1.3) en commentaire PR — toute décision de suppression de `_DIAGNOSTIC_MESSAGES` n'est effectuée que si l'audit confirme à la fois l'absence totale d'émission ET un risque actif de confusion ; sinon, noter uniquement
  - [x] 3.4 — `eligible` (vigilance) : documenter le résultat de l'audit (Task 1.4) en commentaire PR — `eligible` est déjà documenté Story 3.1 comme non-terminal et non émis dans le payload final ; sa présence dans `_DIAGNOSTIC_MESSAGES` est inoffensive

- [x] Task 4 — Mise à jour du badge `v1_limitation` dans `desktop/js/jeedom2ha.js` (AC 2, AI-2)
  - [x] 4.1 — Localiser le rendu du badge (ligne ~547) : texte actuel "Hors périmètre V1"
  - [x] 4.2 — Mettre à jour pour mentionner explicitement "Home Assistant"
  - [x] 4.3 — Cette modification JS est dans le **même commit** que les modifications `_DIAGNOSTIC_MESSAGES` (AI-2)
  - [x] 4.4 — Vérifier que `commandTabReasonCodes` reste cohérent (aucun nouveau code à ajouter pour 3.2)

- [x] Task 5 — Garde-fou AI-3 couche 3 : test de complétude `_DIAGNOSTIC_MESSAGES` (AC 4, AI-3, AI-7)
  - [x] 5.1 — Créer `tests/unit/test_story_3_2_reason_completeness.py`
  - [x] 5.2 — Import : `REASON_CODE_TO_PRIMARY_STATUS` depuis `models.taxonomy` ; `_DIAGNOSTIC_MESSAGES`, `_DIAGNOSTIC_DEFAULT`, `_get_diagnostic_enrichment` depuis `transport.http_server` (utiliser même pattern d'import que `test_story_3_1_taxonomy_sync.py`)
  - [x] 5.3 — Test : pour chaque code dans `REASON_CODE_TO_PRIMARY_STATUS`, il existe une clé dans `_DIAGNOSTIC_MESSAGES`
  - [x] 5.4 — Test : pour chaque code dans `REASON_CODE_TO_PRIMARY_STATUS`, `_get_diagnostic_enrichment(code)[0]` (le `detail`) ne vaut pas `_DIAGNOSTIC_DEFAULT[0]` ("Cause inconnue.")
  - [x] 5.5 — Test : pour chaque code dans `REASON_CODE_TO_PRIMARY_STATUS` dont l'entry a `v1_limitation = True` : le texte `detail` contient "Home Assistant" (comparaison case-insensitive)
  - [x] 5.6 — Commentaire en tête : `# AI-3 guard layer 3 — Story 3.2. Complétude _DIAGNOSTIC_MESSAGES. Ne pas affaiblir ni supprimer. Permanent Epic 3+.`

- [x] Task 6 — Garde-fou AI-3 couche 4 : test de complétude `reasonLabels` JS (AC 4, AI-3, AI-7)
  - [x] 6.1 — Créer `tests/unit/test_story_3_2_reason_labels_sync.py`
  - [x] 6.2 — Import : `REASON_CODE_TO_PRIMARY_STATUS` depuis `models.taxonomy`
  - [x] 6.3 — Lire `desktop/js/jeedom2ha.js` comme string ; extraire le bloc `reasonLabels` via regex :
    ```python
    import re
    # Couvrir var / let / const
    pattern = re.compile(r'(?:var|let|const)\s+reasonLabels\s*=\s*\{.*?\};', re.DOTALL)
    match = pattern.search(js_content)
    if not match:
        raise AssertionError("reasonLabels introuvable dans jeedom2ha.js")
    block = match.group(0)
    ```
    Adapter si la déclaration utilise une forme non couverte.
  - [x] 6.4 — Si bloc introuvable → échouer avec : `"reasonLabels introuvable dans jeedom2ha.js"`
  - [x] 6.5 — Pour chaque code dans `REASON_CODE_TO_PRIMARY_STATUS` : asserter que la string `"'code'"` (avec quotes) apparaît dans le bloc extrait
  - [x] 6.6 — Commentaire en tête : `# AI-3 guard layer 4 — Story 3.2. Complétude reasonLabels JS. Ne pas affaiblir ni supprimer. Permanent Epic 3+.`

- [x] Task 7 — Tests unitaires du contenu enrichi (AC 1, AC 2, AC 3)
  - [x] 7.1 — Créer `tests/unit/test_story_3_2_messages.py`
  - [x] 7.2 — Test : les codes ajoutés (Task 2) ont chacun un `detail` non-vide et non-fallback
  - [x] 7.3 — Test : les codes avec `v1_limitation=True` ont un `detail` contenant "Home Assistant"
  - [x] 7.4 — Test de stabilité (AC 3) : deux appels successifs `_get_diagnostic_enrichment("ambiguous_skipped")` → résultats strictement identiques (`==`)
  - [x] 7.5 — Test de stabilité : même test avec `_get_diagnostic_enrichment("discovery_publish_failed")`
  - [x] 7.6 — Tests des corrections identifiées par l'audit (Task 3) — assertions alignées sur les décisions prises post-audit, pas sur des valeurs pré-fixées
  - [x] 7.7 — `sure.detail` non modifié → tests Story 3.1 non impactés (vérification confirmée)

---

## Dev Notes

### Approche obligatoire : audit-first

**L'audit préalable (Task 1) précède toute modification.** Il sert à :
- Confirmer les lacunes réelles vs les lacunes supposées dans la situation actuelle
- Arbitrer les cas ambigus (`sure_mapping`, `sure`, `eligible`) sur base du code actuel, pas d'hypothèses
- Documenter "ce qui était déjà sain" en plus de "ce qui a été corrigé"
- Éviter les suppressions spéculatives

Toute décision de suppression ou de correction qui ne serait pas confirmée par l'audit doit être portée en note de PR plutôt qu'exécutée.

### Périmètre des AC vs observations audit

**Codes en scope direct des AC :**
- Tous les codes dont le `primary_status` est `not_supported`, `ambiguous`, ou `infra_incident`
- Ces codes doivent avoir un `detail` non-fallback (AC 1) et, si `v1_limitation=True`, mentionner "Home Assistant" (AC 2)

**Codes en observation de vigilance uniquement :**
- `sure`, `probable` (`published`) : hors contrainte "detail non-vide" — audit de cohérence documenté en PR, pas d'obligation de correction
- `sure_mapping`, `eligible` : hors `REASON_CODE_TO_PRIMARY_STATUS` — état documenté en PR, aucune suppression spéculative

Cette distinction est critique pour éviter que le dev agent traite les observations de vigilance comme des AC bloquants.

### Taxonomie 3.1 : lecture seule absolue

`taxonomy.py::REASON_CODE_TO_PRIMARY_STATUS` est la liste de référence des 16 codes attendus.
Ce fichier est **inchangé** dans cette story. C'est le contrat produit par Story 3.1 — il ne peut pas être réinterprété ni enrichi ici.

### Logique métier : aucune duplication côté frontend

Le frontend consomme le payload backend tel quel. Aucune règle de sélection de message, aucun recalcul de statut, aucune substitution de texte côté JS (au-delà du badge `v1_limitation`) ne doit être ajoutée dans cette story.

### Contrat backend existant (structure inchangée par 3.2)

Champs actuels dans le payload diagnostics par équipement :

| Champ | Type | Rôle |
|---|---|---|
| `status` | `str` | Statut principal (5 valeurs — taxonomy.py, figé Story 3.1) |
| `reason_code` | `str` | Code stable déterminant le statut (déterministe) |
| `detail` | `str` | Raison lisible (source : `_DIAGNOSTIC_MESSAGES`) |
| `remediation` | `str` | Action recommandée (source : `_DIAGNOSTIC_MESSAGES`), peut être vide |
| `v1_limitation` | `bool` | `True` si blocage lié à une limite de couverture vers Home Assistant |

**Story 3.2 n'ajoute pas de champ.** Elle enrichit uniquement le contenu de `_DIAGNOSTIC_MESSAGES` et corrige le badge JS.

### Fichiers à modifier

| Fichier | Modification |
|---|---|
| `resources/daemon/transport/http_server.py` | `_DIAGNOSTIC_MESSAGES` : ajouts et corrections selon audit |
| `desktop/js/jeedom2ha.js` | Badge `v1_limitation` : mention HA explicite (même commit — AI-2) |
| `resources/daemon/models/taxonomy.py` | **NON MODIFIÉ** (AI-1) |

### Fichiers à créer

| Fichier | Rôle |
|---|---|
| `tests/unit/test_story_3_2_reason_completeness.py` | Garde-fou AI-3 couche 3 — complétude `_DIAGNOSTIC_MESSAGES` |
| `tests/unit/test_story_3_2_reason_labels_sync.py` | Garde-fou AI-3 couche 4 — complétude `reasonLabels` JS |
| `tests/unit/test_story_3_2_messages.py` | Tests unitaires contenu enrichi |

### Pattern d'import dans les tests Python

```python
import sys, os
# Adapter selon la profondeur réelle depuis le fichier de test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../resources/daemon'))
from models.taxonomy import REASON_CODE_TO_PRIMARY_STATUS
from transport.http_server import _DIAGNOSTIC_MESSAGES, _DIAGNOSTIC_DEFAULT, _get_diagnostic_enrichment
```

Vérifier le chemin exact en suivant le pattern utilisé dans `test_story_3_1_taxonomy_sync.py` (même dossier de tests, même structure).

### Cas `sure` : observation de vigilance uniquement

`sure` correspond à `primary_status = "published"` et est hors du périmètre de AC 1.
L'audit (Task 1.5) documente l'état actuel de `sure.detail` en PR. Aucune correction n'est obligatoire par cette story.

**Dans tous les cas :** le cas partiel (`sure` + `unmatched_commands > 0`) est borné vers **Story 3.4**.
Story 3.2 ne doit pas implémenter de rendu conditionnel selon `unmatched_commands`.

### Tableau d'état cible après Story 3.2

Cible après audit et corrections (les "À confirmer" se résolvent pendant l'audit Task 1) :

| `reason_code` | Statut dans 3.2 |
|---|---|
| `sure` | Hors scope AC — vigilance : auditer et documenter en PR uniquement, borné 3.4 pour cas partiel |
| `probable` | À confirmer par audit + ajouter si absent |
| `excluded_eqlogic` | Vérifier — conserver si correct |
| `excluded_plugin` | Vérifier — conserver si correct |
| `excluded_object` | Vérifier — conserver si correct |
| `disabled_eqlogic` | Vérifier — conserver si correct |
| `disabled` | Vérifier — conserver si correct (alias retro-compatible) |
| `no_commands` | Vérifier — conserver si correct |
| `no_supported_generic_type` | Corriger mention HA (v1_limitation=True) |
| `no_generic_type_configured` | À confirmer par audit + ajouter si absent |
| `no_mapping` | Corriger mention HA si insuffisante (v1_limitation=True) |
| `low_confidence` | À confirmer par audit + ajouter si absent |
| `probable_skipped` | Vérifier — conserver si correct |
| `ambiguous_skipped` | Vérifier — conserver si correct |
| `discovery_publish_failed` | Vérifier — conserver si correct |
| `local_availability_publish_failed` | Vérifier — conserver si correct |
| `sure_mapping` | Vigilance : auditer présence dans le code (Task 1.3) — documenter en PR, décision de suppression post-audit uniquement |
| `eligible` | Vigilance : documenter en PR (Task 1.4) — non-terminal documenté Story 3.1, présence inoffensive |

### `_DIAGNOSTIC_DEFAULT` : ne doit jamais apparaître en cas nominal

```python
_DIAGNOSTIC_DEFAULT = (
    "Cause inconnue.",
    "Relancez un sync. Si le problème persiste, consultez les logs du démon.",
    False,
)
```

Après Story 3.2, ce fallback ne doit plus être retourné pour aucun code dans `REASON_CODE_TO_PRIMARY_STATUS`.
Le test AI-3 couche 3 l'assertera automatiquement.

### Dev Agent Guardrails

**Obligatoire dans cette story :**
- `taxonomy.py` inchangé dans la PR (git diff = vide) — AI-1
- Modifications Python + JS dans le même commit — AI-2
- `test_story_3_2_reason_completeness.py` dans la PR — AI-3 couche 3
- `test_story_3_2_reason_labels_sync.py` dans la PR — AI-3 couche 4
- Auditer `sure_mapping`, `eligible`, et `sure` AVANT de modifier `_DIAGNOSTIC_MESSAGES` (résultats en PR)
- Si et seulement si `sure.detail` est corrigé (hors obligation) : vérifier et mettre à jour les tests Story 3.1 dans le même commit

**Interdit dans cette story :**
- Modifier `taxonomy.py` (ajout, suppression, renommage) → AI-1
- Ajouter de nouveaux `reason_code` qui ne sont pas encore émis par le backend
- Modifier la structure du payload (noms de champs, types, ajout de champ)
- Renommer `v1_limitation` (champ consommé par le frontend — rupture de contrat)
- Implémenter un rendu conditionnel selon `unmatched_commands` → Story 3.4
- Toucher aux agrégations pièce/global → Story 3.3
- Toucher au rendu complet UI au-delà du badge v1_limitation → Story 3.4
- Introduire de la logique métier côté JS

### Project Structure Notes

- Tests Python : `tests/unit/`, runner `pytest`
- Pas de test terrain requis — changements dans données statiques et JS cosmétique
- Pattern JS tests (si nécessaire) : `node:test` natif (pattern établi Story 2.3) — non requis pour 3.2
- Branche de travail : créée depuis `main`, dans un worktree dédié (cf. règles Git `docs/git-strategy.md`)

### References

- [Source `_DIAGNOSTIC_MESSAGES`](resources/daemon/transport/http_server.py#L1227)
- [Source `reasonLabels` JS](desktop/js/jeedom2ha.js#L392)
- [Badge `v1_limitation` rendering](desktop/js/jeedom2ha.js#L546)
- [taxonomy.py — ARTEFACT FIGÉ Story 3.1](resources/daemon/models/taxonomy.py)
- [Epic 3 — Story 3.2](/_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md#story-32)
- [Rétrospective Epic 2 — AI-1 à AI-7](/_bmad-output/implementation-artifacts/epic-2-retro-2026-03-25.md)
- [Story 3.1 — artefact figé](/_bmad-output/implementation-artifacts/3-1-taxonomie-principale-de-statuts-d-equipement.md)

---

## Stratégie de tests

### Couverture attendue

| Couche | Fichier | Rôle | Tests estimés |
|---|---|---|---|
| Complétude `_DIAGNOSTIC_MESSAGES` + mention HA (AI-3 couche 3) | `test_story_3_2_reason_completeness.py` | 100 % des codes du mapping ont un message non-fallback ; v1_limitation contient HA | ~10 |
| Complétude `reasonLabels` JS (AI-3 couche 4) | `test_story_3_2_reason_labels_sync.py` | Extraction bloc `reasonLabels` via regex ; 100 % codes ont un label | ~5 |
| Contenu des messages enrichis (unitaire) | `test_story_3_2_messages.py` | Codes ajoutés, corrections HA, stabilité | ~10 |

### Principe de test

- Tests Python : `pytest`
- Pas de test terrain requis (modifications dans données statiques et présentation JS)
- Les gardes-fous couches 3 et 4 rejoignent la suite permanente de l'Epic 3
- Si les tests de Story 3.1 (`test_story_3_1_taxonomy.py`) sont impactés par une correction de `sure.detail` : mettre à jour dans la même PR

### Couverture minimale non négociable

1. Les codes ajoutés (confirmés par audit Task 1.2) ont un `detail` non-vide et non-fallback
2. `no_supported_generic_type.detail` et `no_mapping.detail` contiennent "Home Assistant"
3. Aucun code de `REASON_CODE_TO_PRIMARY_STATUS` ne retourne `_DIAGNOSTIC_DEFAULT` (test AI-3 couche 3)
4. Tous les codes de `REASON_CODE_TO_PRIMARY_STATUS` ont un label dans `reasonLabels` JS (test AI-3 couche 4)
5. Stabilité : deux appels `_get_diagnostic_enrichment(code)` → résultat identique

### Ce que la stratégie de tests ne fige pas

- Le wording exact des nouveaux `detail` et `remediation` (décision du dev après audit)
- La valeur exacte du `detail` pour `sure` (`published` — hors AC 1, observation de vigilance uniquement)
- Les décisions de suppression de `sure_mapping` ou `eligible` (post-audit, hors AC)
- Un rendu UI avancé ou conditionnel selon `unmatched_commands` → Story 3.4

---

## Risques et points de vigilance

### R1 — Dérive vers Story 3.4

Si l'audit amène à vouloir traiter le cas `sure` + `unmatched_commands > 0` (publication partielle),
stopper : c'est le scope de Story 3.4. Story 3.2 se limite à corriger le message pour le cas nominal,
pas à implémenter un rendu conditionnel côté JS ou backend.

### R2 — Suppression spéculative de codes legacy

Ne supprimer `sure_mapping` ou `eligible` de `_DIAGNOSTIC_MESSAGES` que si l'audit (Tasks 1.3, 1.4)
confirme explicitement leur obsolescence. Une suppression non confirmée peut faire tomber un code
existant dans `_DIAGNOSTIC_DEFAULT` silencieusement.

### R3 — Faux sentiment de couverture

La story corrige les lacunes connues au moment de sa création. Elle ne garantit pas que des codes
futurs seront couverts. C'est le rôle du test AI-3 couche 3 (permanent) de détecter les dérives
futures automatiquement — c'est précisément pour ça qu'il est permanent.

### R4 — Rupture de synchro backend/frontend

Toute modification de `_DIAGNOSTIC_MESSAGES` sans mise à jour de `reasonLabels` JS dans le même
commit (AI-2) crée un état intermédiaire incohérent. Le garde-fou AI-3 couche 4 détecte cette dérive
en CI, mais pas en temps réel : respecter l'atomicité du commit d'emblée.

### R5 — Confusion entre limite HA et erreur utilisateur

Les codes avec `v1_limitation=True` représentent une limite de couverture du plugin vers Home Assistant,
pas une erreur de configuration utilisateur. Le `detail` doit l'exprimer clairement pour éviter une
recherche d'action corrective inutile de la part de l'utilisateur ou du support.

### R6 — `sure_mapping` : code fantôme d'état inconnu

Nature inconnue avant l'audit Task 1.3. Si `sure_mapping` est encore émis par le backend, sa suppression
de `_DIAGNOSTIC_MESSAGES` fera retourner `_DIAGNOSTIC_DEFAULT` pour ce code.
Vérifier avant de supprimer. Décision d'arbitrage : si absent → supprimer ; si présent → note de PR.

### R7 — Tests Story 3.1 peuvent être impactés par une correction de `sure`

`test_story_3_1_taxonomy.py` peut contenir des assertions sur `eq.detail` pour `reason_code="sure"`.
Vérifier avant de modifier `_DIAGNOSTIC_MESSAGES["sure"]`. Mettre à jour dans la même PR si nécessaire.

### R8 — Regex `reasonLabels` fragile si format JS change

Le pattern doit couvrir `var|let|const`. Prévoir un message d'erreur explicite si le bloc est
introuvable, plutôt qu'un échec cryptique.

---

## Réduction de dette support

**Réponse standard à "pourquoi cet équipement n'est pas publié ?" :**

Après Story 3.2, pour tout `reason_code` dans le mapping taxonomy correspondant à un équipement non publié ou ambigu :
- `detail` contient une réponse compréhensible, sans expertise MQTT.
- `remediation` contient une action simple et actionnelle quand elle existe.
- Quand `v1_limitation=True` → l'utilisateur et le support savent que c'est une limite de couverture
  vers Home Assistant, pas un problème de configuration personnel.
- Plus de "Cause inconnue." pour un équipement courant.

Le support peut donner une réponse de premier niveau à "pourquoi cet équipement n'est pas publié ?"
depuis le payload du diagnostic, sans interprétation ad hoc des logs dans les cas nominaux.

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4-6) — 2026-03-26

### Debug Log References

- Audit Task 1.2 : 3 codes manquants confirmés (`probable`, `no_generic_type_configured`, `low_confidence`)
- Audit Task 1.3 : `sure_mapping` absent du code de sync réel — uniquement dans fixtures de tests. Conservé comme safety net legacy.
- Audit Task 1.4 : `eligible` non-terminal confirmé — présence inoffensive dans `_DIAGNOSTIC_MESSAGES`.
- Audit Task 1.5 : `sure.detail` trompeur pour publication complète (message partiel) — documenté, hors scope AC, non corrigé.
- `no_mapping.detail` déjà sain (contient "Home Assistant") — aucune correction requise.
- `reasonLabels` JS : tous les 16 codes déjà présents avant Story 3.2 — aucun ajout JS requis.
- Phase RED confirmée : 7 échecs attendus sur les tests garde-fous avant corrections.
- Phase GREEN : 7 → 0 échecs après corrections. 637 tests passent (0 régression Story 3.2).


### Completion Notes List

- ✅ Task 1 : Audit préalable complet. 3 codes manquants confirmés. Observations documentées.
- ✅ Task 2 : `probable`, `no_generic_type_configured`, `low_confidence` ajoutés à `_DIAGNOSTIC_MESSAGES` avec messages non-fallback.
- ✅ Task 3 : `no_supported_generic_type.detail` corrigé — mention "Home Assistant" ajoutée. `no_mapping` déjà sain.
- ✅ Task 4 : Badge `v1_limitation` mis à jour — "Hors périmètre V1 — Home Assistant". Même commit que les modifications Python (AI-2).
- ✅ Task 5 : `test_story_3_2_reason_completeness.py` créé — 48 tests (3 paramétrés × 16 codes). Tous passent.
- ✅ Task 6 : `test_story_3_2_reason_labels_sync.py` créé — 17 tests. Tous passent.
- ✅ Task 7 : `test_story_3_2_messages.py` créé — 34 tests. Tous passent.
- ✅ `taxonomy.py` inchangé (AI-1 confirmé par `git diff`).
- ✅ Aucun recalcul métier ajouté côté JS.
- ✅ Suite complète 637 tests PASS. Aucune régression détectée pour Story 3.2.

### File List

- `resources/daemon/transport/http_server.py` — `_DIAGNOSTIC_MESSAGES` : ajout de `probable`, `no_generic_type_configured`, `low_confidence` ; correction `no_supported_generic_type` (mention HA)
- `desktop/js/jeedom2ha.js` — badge `v1_limitation` : "Hors périmètre V1 — Home Assistant"
- `tests/unit/test_story_3_2_reason_completeness.py` — créé (AI-3 couche 3, 48 tests)
- `tests/unit/test_story_3_2_reason_labels_sync.py` — créé (AI-3 couche 4, 17 tests)
- `tests/unit/test_story_3_2_messages.py` — créé (contenu enrichi, 34 tests)
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py` — adaptations taxonomie 3.1 (`sure_mapping` → `sure`, statuts renommés)
- `resources/daemon/tests/unit/test_diagnostic_export.py` — adaptations taxonomie 3.1 (`_VALID_STATUS_CODES`, `sure_mapping` → `sure`)
- `resources/daemon/tests/unit/test_exclusion_filtering.py` — adaptations taxonomie 3.1 (`_EXCLUDED_REASON_CODES` → `_CLOSED_REASON_MAP`, statuts renommés)
- `resources/daemon/tests/integration/test_boot_reconciliation.py` — adaptation taxonomie 3.1 (`disabled_eqlogic` → `"Non supporté"`)

---

**Story revision date:** 2026-03-26 (correction artefact — cohérence AC/vigilance)
**Cycle:** Post-MVP Phase 1 - V1.1 Pilotable
**Status:** done
