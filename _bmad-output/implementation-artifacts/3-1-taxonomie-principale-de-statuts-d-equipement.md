# Story 3.1 : Taxonomie principale de statuts d'équipement

Status: review

---

## Story

En tant qu'utilisateur de la console,
je veux que chaque équipement affiche un statut principal clair parmi un ensemble fermé et stable,
afin de comprendre immédiatement son état sans interprétation ni badge ambigu.

---

## Contexte et objectif

### Situation actuelle (à corriger dans cette story)

Le backend produit actuellement quatre valeurs pour le champ `status` dans `/system/diagnostics` :

| Valeur actuelle | Problème |
|---|---|
| `"Publié"` | ✓ conservé tel quel |
| `"Exclu"` | ✓ conservé tel quel |
| `"Partiellement publié"` | ❌ interdit comme statut principal équipement — doit devenir `"Publié"` + détail secondaire |
| `"Non publié"` | ❌ trop vague — masque `Ambigu`, `Non supporté`, `Incident infrastructure` |

L'UI JavaScript (`getStatusLabel`) mappe uniquement ces 4 valeurs. Elle ignore `Ambigu`, `Non supporté`, `Incident infrastructure`.

### Objectif de Story 3.1

Remplacer ce modèle partiel par une **taxonomie principale fermée à 5 statuts**, implémentée backend-first,
avec un remplacement atomique backend + frontend + tests dans la même PR.

Produire un **artefact sémantique figé** (`taxonomy.py`) qui servira de contrat unique pour les stories 3.2, 3.3, 3.4.

### Ce que cette story ne fait pas

Story 3.1 **n'absorbe pas le contenu métier de Story 3.2**. Elle prépare le terrain sans empiéter :

| Frontière | Story 3.1 | Story 3.2 |
|---|---|---|
| Statuts principaux | ✓ verrouillés ici | lecture seule |
| Structure du contrat backend | ✓ définie ici | lecture seule |
| Mapping reason_code → primary_status | ✓ figé ici (codes existants) | ajout de nouveaux codes si besoin |
| Texte de la raison lisible (`detail`) | ❌ inchangé, géré par `_DIAGNOSTIC_MESSAGES` existant | ✓ formalisé et complété |
| Action recommandée (`remediation`) | ❌ inchangée | ✓ formalisée |
| Nouveaux reason_codes | ❌ aucun ajout | ✓ nouveaux codes si nécessaire |
| Texte des labels de reason_code JS | ❌ inchangé | ✓ complété |

**Règle de dérive interdite :** si l'implémentation amène l'agent à écrire du texte de `detail` ou de `remediation` au-delà de ce qui existe déjà dans `_DIAGNOSTIC_MESSAGES`, il sort du scope de 3.1 — STOP.

---

## Dépendances autorisées

- **Story 1.1** — périmètre canonique (`published_scope`, `assess_eligibility()`)
- **Story 2.1** — contrat de santé (`/system/status`)
- Aucune dépendance en avant

---

## Scope

### In-scope

- Création de `resources/daemon/models/taxonomy.py` : artefact sémantique figé
- Modification de `_handle_system_diagnostics` dans `http_server.py` pour utiliser la taxonomie
- Remplacement de `status = "Partiellement publié"` et `status = "Non publié"` par les valeurs de la taxonomie
- Mise à jour de `_STATUS_CODE_MAP` en cohérence
- Mise à jour atomique de `getStatusLabel` dans `desktop/js/jeedom2ha.js`
- Rendu `(partiel)` au call site du renderer JS pour `Publié` + `unmatched_commands.length > 0` (pas dans `getStatusLabel`)
- Test de synchronisation contrat backend/frontend (AI-3)
- Tests unitaires Python et JS pour les 5 statuts

### Out-of-scope (interdit en 3.1)

- Modification de `_DIAGNOSTIC_MESSAGES` (reason_codes textes lisibles) → **Story 3.2**
- Ajout de nouveaux `reason_code` non encore émis par le backend → **Story 3.2**
- Modification du champ `detail` ou `remediation` dans le payload → **Story 3.2**
- Agrégations pièce/global → **Story 3.3**
- Rendu complet UI du contrat métier → **Story 3.4**
- Comportements dynamiques pollers / UI temps réel → **Story 3.4**
- Preview complète, remédiation guidée avancée → **Phases B/C**
- Support outillé avancé → **Phase C**

---

## Taxonomie principale — artefact figé

### Les 5 statuts principaux

| Code machine | Label français | Couleur UI | Sémantique |
|---|---|---|---|
| `published` | `Publié` | `label-success` (vert) | L'équipement est publié dans HA (complètement ou partiellement) |
| `excluded` | `Exclu` | `label-default` (gris) | Exclu volontairement par configuration utilisateur ou scope |
| `ambiguous` | `Ambigu` | `label-warning` (orange) | Mapping impossible — plusieurs interprétations ou confiance insuffisante |
| `not_supported` | `Non supporté` | `label-default` (gris sombre) | Type non couvert, commandes absentes, ou état Jeedom incompatible |
| `infra_incident` | `Incident infrastructure` | `label-danger` (rouge) | Échec d'infrastructure (MQTT/publish) — problème de bridge, pas de config |

**Règle visuelle héritée de Story 2.4 :** le rouge (`label-danger`) est réservé à l'infrastructure. `Ambigu` et `Non supporté` ne sont jamais rouges.

### Mapping reason_code → primary_status (exhaustif sur les codes existants)

Ce tableau est la source de vérité. Immuable pour 3.2–3.4.

| `reason_code` | `primary_status` | Justification |
|---|---|---|
| `sure` | `published` | Publié avec certitude |
| `probable` | `published` | Publié avec confiance probable (politique permissive) |
| `excluded_eqlogic` | `excluded` | Exclusion manuelle de l'équipement |
| `excluded_plugin` | `excluded` | Plugin source exclu |
| `excluded_object` | `excluded` | Pièce exclue |
| `disabled_eqlogic` | `not_supported` | Équipement désactivé dans Jeedom |
| `disabled` | `not_supported` | Alias retro-compatible de `disabled_eqlogic` |
| `no_commands` | `not_supported` | Aucune commande exploitable |
| `no_supported_generic_type` | `not_supported` | Aucun type générique supporté en V1.1 |
| `no_generic_type_configured` | `not_supported` | Commandes sans type générique configuré |
| `no_mapping` | `not_supported` | Aucun mapper compatible trouvé |
| `low_confidence` | `not_supported` | Confiance trop faible pour publication |
| `probable_skipped` | `ambiguous` | Confiance probable mais politique "sûr uniquement" — mapping non déterministe |
| `ambiguous_skipped` | `ambiguous` | Plusieurs types génériques possibles — ambiguïté de mapping |
| `discovery_publish_failed` | `infra_incident` | Échec publication MQTT (infra) |
| `local_availability_publish_failed` | `infra_incident` | Échec publication disponibilité locale (infra) |

**Codes non terminaux (ne doivent jamais apparaître dans le payload final) :**
- `eligible` — code intermédiaire de `assess_eligibility()`, toujours surchargé par la suite

**Cas `unknown` :** si un `reason_code` non listé apparaît → `not_supported` par défaut sécuritaire. À documenter dans la PR si cela arrive.

### Détail secondaire : Publié partiel

L'ancien `"Partiellement publié"` devient `primary_status = "published"`.
Le caractère partiel est un **détail de présentation contextuel**, non un statut principal.

Mécanisme : `unmatched_commands.length > 0` avec `status == "Publié"`, évalué **au call site du renderer d'équipement**.
- `getStatusLabel("Publié")` reste pur et retourne uniquement le badge Publié.
- Le suffixe `(partiel)` est concaténé par le caller, après `getStatusLabel`, quand `unmatched_commands.length > 0`.
- Aucun nouveau champ API n'est ajouté — `unmatched_commands` existe déjà dans le payload.

---

## Acceptance Criteria

### AC 1 — Taxonomie verrouillée côté backend

**Given** un équipement évalué par le backend
**When** `/system/diagnostics` est appelé
**Then** le champ `status` de chaque equipment appartient UNIQUEMENT à `{"Publié", "Exclu", "Ambigu", "Non supporté", "Incident infrastructure"}`
**And** `"Partiellement publié"` et `"Non publié"` n'apparaissent JAMAIS dans la réponse

### AC 2 — `Partiellement publié` éliminé comme statut principal

**Given** un équipement dont certaines commandes sont publiées et d'autres non couvertes
**When** `/system/diagnostics` est appelé
**Then** le champ `status` est `"Publié"`
**And** `unmatched_commands` contient les commandes non couvertes
**And** l'UI affiche un badge `Publié` avec indicateur secondaire `(partiel)` si `unmatched_commands.length > 0`

### AC 3 — `Non publié` remplacé par un statut précis

**Given** un équipement non publié (toute raison sauf exclusion)
**When** `/system/diagnostics` est appelé
**Then** le champ `status` est soit `"Ambigu"` soit `"Non supporté"` soit `"Incident infrastructure"`
**And** le champ `reason_code` est cohérent avec le `status` selon la table de mapping

### AC 4 — Test de synchronisation AI-3 : garde-fou de contrat à deux couches

**Given** les 5 primary_status définis dans `taxonomy.py`
**When** le test Python de synchronisation est exécuté
**Then** il extrait spécifiquement le bloc `getStatusLabel` de `jeedom2ha.js` (via regex — pas le fichier entier)
**And** il vérifie que chaque label français de `PRIMARY_STATUSES.values()` apparaît **dans ce bloc uniquement**
**And** il échoue si le bloc `getStatusLabel` est introuvable dans le fichier

**Given** les 5 primary_status définis dans `taxonomy.py`
**When** le test JS `test_story_3_1_status_labels.node.test.js` est exécuté
**Then** `getStatusLabel("Publié")`, `getStatusLabel("Exclu")`, `getStatusLabel("Ambigu")`, `getStatusLabel("Non supporté")`, `getStatusLabel("Incident infrastructure")` retournent chacun un HTML non-fallback (contenant leur label exact)
**And** `getStatusLabel("Partiellement publié")` et `getStatusLabel("Non publié")` ne retournent PAS un rendu de statut nominal (ils tombent dans le fallback ou sont absents)

**And** (garde-fou de dérive) : si un label est ajouté à `PRIMARY_STATUSES` sans mise à jour de `getStatusLabel`, le test Python AC4 devient rouge car le bloc extrait ne contiendra pas le nouveau label

### AC 5 — `taxonomy.py` expose un contrat importable et complet

**Given** `resources/daemon/models/taxonomy.py` existe
**When** `from models.taxonomy import PRIMARY_STATUSES, REASON_CODE_TO_PRIMARY_STATUS, get_primary_status` est exécuté
**Then** l'import fonctionne sans erreur
**And** `PRIMARY_STATUSES` contient exactement 5 entrées
**And** `get_primary_status("ambiguous_skipped")` retourne `"Ambigu"` sans erreur

### AC 6 — Cohérence multi-surfaces

**Given** un même équipement relu par l'UI console et via `/system/diagnostics` direct
**When** le statut est comparé
**Then** les deux surfaces racontent la même histoire avec le même wording issu de la taxonomie

---

## Tasks / Subtasks

- [x] Task 1 — Créer `resources/daemon/models/taxonomy.py` (artefact figé) (AC 1, AC 5)
  - [x] 1.1 — Créer le fichier avec `PRIMARY_STATUSES: dict[str, str]` — machine code → label français
  - [x] 1.2 — Créer `REASON_CODE_TO_PRIMARY_STATUS: dict[str, str]` — mapping exhaustif selon tableau ci-dessus
  - [x] 1.3 — Créer `PRIMARY_STATUS_LABELS: frozenset[str]` — ensemble fermé des labels français valides
  - [x] 1.4 — Créer `get_primary_status(reason_code: str) -> str` — résolution avec fallback `"not_supported"` si code inconnu
  - [x] 1.5 — Ajouter un commentaire en tête : `# ARTEFACT FIGÉ — Story 3.1. Ne pas modifier sans story dédiée. Stories 3.2, 3.3, 3.4 consomment en lecture seule.`
  - [x] 1.6 — L'artefact NE contient pas de textes lisibles ni d'actions recommandées (hors scope)

- [x] Task 2 — Modifier `_handle_system_diagnostics` dans `http_server.py` (AC 1, AC 2, AC 3)
  - [x] 2.1 — Importer `get_primary_status` depuis `models.taxonomy`
  - [x] 2.2 — Remplacer toutes les assignations `status = "Partiellement publié"` et `status = "Non publié"` par le calcul via `get_primary_status(reason_code)`
  - [x] 2.3 — Remplacer `status = "Exclu"` et `status = "Publié"` par `get_primary_status(reason_code)` pour unifier le point d'entrée
  - [x] 2.4 — Mettre à jour `_STATUS_CODE_MAP` : remplacer les 4 anciennes clés par les 5 nouvelles (`"Publié" → "published"`, `"Exclu" → "excluded"`, `"Ambigu" → "ambiguous"`, `"Non supporté" → "not_supported"`, `"Incident infrastructure" → "infra_incident"`)
  - [x] 2.5 — Suppression propre de la constante `_EXCLUDED_REASON_CODES` si elle est désormais couverte par `REASON_CODE_TO_PRIMARY_STATUS` (sinon : l'adapter pour qu'elle reste cohérente)
  - [x] 2.6 — Vérifier que `unmatched_commands` est bien peuplé pour les cas `primary_status == "published"` avec couverture partielle (comportement identique — juste `status` qui change)
  - [x] 2.7 — Aucun nouveau champ ajouté au payload au-delà de la mise à jour de `status`

- [x] Task 3 — Mise à jour atomique `desktop/js/jeedom2ha.js` (AC 1, AC 2, AI-2)
  - [x] 3.1 — Réécrire `getStatusLabel` comme fonction **pure** — un seul argument `status` (signature inchangée) — pour les 5 nouveaux statuts :
    - `"Publié"` → `label-success`
    - `"Exclu"` → `label-default`
    - `"Ambigu"` → `label-warning`
    - `"Non supporté"` → `label-default` (style visuellement distinct de `Exclu` si possible avec CSS inline)
    - `"Incident infrastructure"` → `label-danger`
  - [x] 3.2 — **`getStatusLabel` NE gère PAS le détail secondaire `(partiel)`** — la fonction reste pure et ne reçoit pas `unmatched_commands`
  - [x] 3.3 — Le suffixe `(partiel)` est ajouté **au call site du renderer** d'équipement (fonction `buildDetailRow` ou équivalent), après appel à `getStatusLabel`, selon la condition : `eq.unmatched_commands && eq.unmatched_commands.length > 0 && eq.status === "Publié"`. Rendu attendu : `[badge Publié] <span class="text-muted" style="font-size:0.85em">(partiel)</span>`
  - [x] 3.4 — Supprimer les cas `"Partiellement publié"` et `"Non publié"` de `getStatusLabel`
  - [x] 3.5 — Vérifier que `commandTabReasonCodes` reste cohérent avec la taxonomie (aucun reason_code ne pointe vers un statut invalide)
  - [x] 3.6 — Cette task doit être dans le MÊME commit que Task 2 (atomicité AI-2)

- [x] Task 4 — Test de synchronisation contrat backend/frontend — garde-fou AI-3 à deux couches (AC 4, AI-3, AI-7)
  - [x] 4.1 — Créer `tests/unit/test_story_3_1_taxonomy_sync.py` (couche Python)
  - [x] 4.2 — Ce test lit `PRIMARY_STATUSES` depuis `models.taxonomy`
  - [x] 4.3 — Ce test lit `desktop/js/jeedom2ha.js` comme string PUIS extrait spécifiquement le bloc `getStatusLabel` via regex : `re.search(r'var getStatusLabel\s*=\s*function.*?};', js_content, re.DOTALL)` — ou pattern équivalent adapté à la syntaxe du fichier
  - [x] 4.4 — Si le bloc `getStatusLabel` est introuvable → le test échoue avec message explicite : `"getStatusLabel introuvable dans jeedom2ha.js"`
  - [x] 4.5 — Pour chaque label français dans `PRIMARY_STATUSES.values()` : asserter que le label apparaît **dans le bloc extrait** (pas dans le fichier entier)
  - [x] 4.6 — Vérifier également que les anciens statuts `"Partiellement publié"` et `"Non publié"` n'apparaissent **pas comme cas nominaux** dans le bloc extrait (leur présence éventuelle ne doit être qu'en fallback ou commentaire)
  - [x] 4.7 — Commenter dans le test : `# AI-3 guard — Story 3.1. Ce test cible le bloc getStatusLabel. Ne pas affaiblir en testant le fichier entier. Permanent pour Epic 3+.`
  - [x] 4.8 — Les tests JS de rendu (Task 6) constituent la deuxième couche : ils appellent `getStatusLabel()` réellement via `node:test` et valident le comportement, pas seulement la présence textuelle

- [x] Task 5 — Tests unitaires Python de la taxonomie et du diagnostic (AC 1, AC 2, AC 3)
  - [x] 5.1 — Créer `tests/unit/test_story_3_1_taxonomy.py`
  - [x] 5.2 — Test : `get_primary_status` pour chaque reason_code du tableau de mapping → valeur attendue
  - [x] 5.3 — Test : `get_primary_status("eligible")` ne doit jamais apparaître comme valeur finale (test de documentation)
  - [x] 5.4 — Test : `get_primary_status("code_inexistant")` → `"not_supported"` (fallback sécuritaire)
  - [x] 5.5 — Test d'intégration `_handle_system_diagnostics` : équipement exclu → `status == "Exclu"`
  - [x] 5.6 — Test : équipement désactivé → `status == "Non supporté"`
  - [x] 5.7 — Test : `ambiguous_skipped` → `status == "Ambigu"`
  - [x] 5.8 — Test : `discovery_publish_failed` → `status == "Incident infrastructure"`
  - [x] 5.9 — Test : équipement publié complet → `status == "Publié"` + `unmatched_commands == []`
  - [x] 5.10 — Test : équipement publié partiel → `status == "Publié"` + `unmatched_commands.length > 0` + PAS de `status == "Partiellement publié"`
  - [x] 5.11 — Test : aucune réponse de `/system/diagnostics` ne retourne `"Non publié"` ni `"Partiellement publié"`

- [x] Task 6 — Tests JS de l'affichage (AC 1, AC 2, AC 4 couche comportement)
  - [x] 6.1 — Créer `tests/unit/test_story_3_1_status_labels.node.test.js` — utilise `node:test` natif (pattern Story 2.3)
  - [x] 6.2 — Test : `getStatusLabel("Publié")` → contient `label-success` et contient le texte `Publié`
  - [x] 6.3 — Test : `getStatusLabel("Exclu")` → contient `label-default` et contient le texte `Exclu`
  - [x] 6.4 — Test : `getStatusLabel("Ambigu")` → contient `label-warning` et contient le texte `Ambigu`
  - [x] 6.5 — Test : `getStatusLabel("Non supporté")` → contient `label-default`, ne contient PAS `label-danger`, contient le texte `Non supporté`
  - [x] 6.6 — Test : `getStatusLabel("Incident infrastructure")` → contient `label-danger` et contient le texte `Incident infrastructure`
  - [x] 6.7 — Test `getStatusLabel` n'est PAS responsable du `(partiel)` : `getStatusLabel("Publié")` ne contient PAS le texte `partiel` — vérifie la pureté de la fonction
  - [x] 6.8 — Test du call site (`buildDetailRow` ou équivalent) : pour un équipement `{status: "Publié", unmatched_commands: []}` → le rendu NE contient PAS `(partiel)`
  - [x] 6.9 — Test du call site : pour un équipement `{status: "Publié", unmatched_commands: [{cmd_id: 1}]}` → le rendu contient `(partiel)`
  - [x] 6.10 — Test négatif : `getStatusLabel("Partiellement publié")` ne produit PAS un badge `label-success`, `label-warning`, `label-danger` — tombe dans le fallback neutre
  - [x] 6.11 — Test négatif : `getStatusLabel("Non publié")` — même exigence que 6.10

---

## Dev Notes

### Stratégie de rendu du détail secondaire `(partiel)` — décision figée

**`getStatusLabel(status)` est une fonction PURE à signature inchangée.** Elle ne reçoit JAMAIS `unmatched_commands`.

Le suffixe `(partiel)` est ajouté **au call site**, dans la fonction de rendu d'équipement (actuellement `buildDetailRow` ou équivalent dans `jeedom2ha.js`), avec la condition :

```javascript
// Dans buildDetailRow ou équivalent — APRÈS appel à getStatusLabel
var partialSuffix = '';
if (eq.status === 'Publié' && eq.unmatched_commands && eq.unmatched_commands.length > 0) {
    partialSuffix = ' <span class="text-muted" style="font-size:0.85em">(partiel)</span>';
}
// Rendu final: getStatusLabel(eq.status) + partialSuffix
```

**Pourquoi ce choix :**
- `getStatusLabel` reste testable proprement avec un seul argument
- Le partial est un détail de présentation contextuel, pas un état métier — il appartient au renderer
- Cohérent avec backend-first : le backend fournit `status == "Publié"` + `unmatched_commands`, le JS compose l'affichage

**Interdit :** ajouter un paramètre `options`, `isPartial`, ou `unmatched_commands` à `getStatusLabel`.



- **Backend = source unique des statuts.** Le frontend ne recalcule jamais de règle métier.
- **`taxonomy.py` est le contrat.** Il est lu par `http_server.py` et testé contre `jeedom2ha.js`. Il ne contient ni texte de `detail`, ni `remediation`, ni wording lisible — seulement le mapping codes+labels.
- **Remplacement atomique (AI-2).** Les modifications `http_server.py` et `jeedom2ha.js` sont dans le MÊME commit. Aucune phase intermédiaire avec `"Code inconnu"` ou affichage cassé.
- **Aucune logique métier en JS.** Le JS affiche ce que le backend envoie dans `status`.

### Structure du code existant à toucher

| Fichier | Rôle | Modification attendue |
|---|---|---|
| `resources/daemon/models/topology.py` | `assess_eligibility()` | **Non modifié** — produit déjà les reason_codes corrects |
| `resources/daemon/transport/http_server.py` | `_handle_system_diagnostics()` | Remplace calcul de `status` par `get_primary_status(reason_code)` |
| `resources/daemon/transport/http_server.py` | `_STATUS_CODE_MAP` | Nouvelles clés avec les 5 statuts |
| `resources/daemon/transport/http_server.py` | `_EXCLUDED_REASON_CODES` | Vérifier cohérence / supprimer si redondant avec taxonomy |
| `desktop/js/jeedom2ha.js` | `getStatusLabel()` | Remplacer pour les 5 nouveaux statuts |
| `resources/daemon/models/taxonomy.py` | **NEW** | Créer l'artefact figé |

### Ce que `assess_eligibility()` produit déjà (NE PAS TOUCHER)

```python
# models/topology.py - assess_eligibility() - LECTURE SEULE pour Story 3.1
# Produit: excluded_eqlogic / excluded_plugin / excluded_object → EligibilityResult(is_eligible=False)
#           disabled_eqlogic → EligibilityResult(is_eligible=False)
#           no_commands → EligibilityResult(is_eligible=False)
#           no_supported_generic_type → EligibilityResult(is_eligible=False)
#           eligible → EligibilityResult(is_eligible=True)
```

### Calcul du `primary_status` dans `_handle_system_diagnostics`

Le point d'assignation de `status` final dans le code actuel :
1. Ligne init: `status = "Non publié"` → à remplacer par `status = None` (sera calculé)
2. `if el_result.reason_code in _EXCLUDED_REASON_CODES` → `status = "Exclu"` → à remplacer
3. `else` branche non éligible → `status = "Non publié"` → à remplacer
4. `if pub_decision and pub_decision.active_or_alive` + `if unmapped_cmds` → `status = "Partiellement publié"` ou `"Publié"` → à remplacer
5. Dans chaque branche, appliquer `status = get_primary_status(reason_code)` après que `reason_code` est déterminé

**Pattern recommandé post-refacto :**
```python
# À la fin de chaque branche de calcul, une fois reason_code final connu :
status = get_primary_status(reason_code)
# puis dans la réponse: "status": status
```

### Structure du `taxonomy.py` attendue

```python
# resources/daemon/models/taxonomy.py
# ARTEFACT FIGÉ — Story 3.1
# Stories 3.2, 3.3, 3.4 consomment en lecture seule.

PRIMARY_STATUSES: dict[str, str] = {
    "published":    "Publié",
    "excluded":     "Exclu",
    "ambiguous":    "Ambigu",
    "not_supported":"Non supporté",
    "infra_incident":"Incident infrastructure",
}

REASON_CODE_TO_PRIMARY_STATUS: dict[str, str] = {
    "sure":                              "published",
    "probable":                          "published",
    "excluded_eqlogic":                  "excluded",
    "excluded_plugin":                   "excluded",
    "excluded_object":                   "excluded",
    "disabled_eqlogic":                  "not_supported",
    "disabled":                          "not_supported",
    "no_commands":                       "not_supported",
    "no_supported_generic_type":         "not_supported",
    "no_generic_type_configured":        "not_supported",
    "no_mapping":                        "not_supported",
    "low_confidence":                    "not_supported",
    "probable_skipped":                  "ambiguous",
    "ambiguous_skipped":                 "ambiguous",
    "discovery_publish_failed":          "infra_incident",
    "local_availability_publish_failed": "infra_incident",
}

PRIMARY_STATUS_LABELS: frozenset[str] = frozenset(PRIMARY_STATUSES.values())


def get_primary_status(reason_code: str) -> str:
    """Résout le statut principal à partir d'un reason_code.
    Fallback sécuritaire vers 'not_supported' si code inconnu.
    """
    return PRIMARY_STATUSES.get(
        REASON_CODE_TO_PRIMARY_STATUS.get(reason_code, "not_supported"),
        "Non supporté",
    )
```

### Dev Agent Guardrails

**Interdit dans cette story :**
- Modifier `_DIAGNOSTIC_MESSAGES` dans `http_server.py` (textes de `detail`/`remediation`) → Story 3.2
- Ajouter de nouveaux `reason_code` qui n'existent pas encore dans le backend → Story 3.2
- Modifier `assess_eligibility()` dans `topology.py` → hors scope total
- Modifier les champs `detail`, `remediation`, `v1_limitation` du payload → Story 3.2
- Créer une table de wording complète avec textes utilisateur → Story 3.2
- Ajouter de la logique d'agrégation pièce/global → Story 3.3
- Modifier la structure d'ensemble du payload (champs autres que `status` et `status_code`) → hors scope
- Ajouter un champ `primary_status` parallèle à `status` → remplacer `status` directement

**Obligatoire dans cette story :**
- Le commit qui change `_handle_system_diagnostics` DOIT être le même commit que le changement de `getStatusLabel` (AI-2)
- `test_story_3_1_taxonomy_sync.py` doit être livré dans la même PR (AI-3)
- `taxonomy.py` doit avoir le commentaire figé en tête de fichier

### Guardrail AI-1 — Artefact figé, consommé en lecture seule par les stories aval

`taxonomy.py` produit par Story 3.1 est le contrat canonique pour l'Epic 3 entier.

- **Story 3.2, 3.3, 3.4 = consommatrices, pas rédactrices.** Elles importent `taxonomy.py` mais ne le modifient pas.
- Si une story aval a besoin d'un nouveau statut ou d'un nouveau reason_code → elle doit créer sa propre story de modification de taxonomie, pas modifier silencieusement `taxonomy.py`.
- **Critère de code review des stories 3.2–3.4 :** vérifier que `taxonomy.py` n'a pas été modifié dans la PR (git diff sur ce fichier doit être vide).
- La code review de Story 3.1 doit vérifier : `taxonomy.py` porte le commentaire figé en tête + les exports sont corrects.

### Guardrail AI-2 — Atomicité obligatoire

Zéro état intermédiaire toléré entre backend et frontend.

Le commit de livraison de Story 3.1 doit :
1. Modifier `http_server.py` (nouveaux statuts)
2. Modifier `jeedom2ha.js` (nouveaux labels)
3. Ajouter tous les tests

En **un seul commit atomique** (ou une PR fusionnée en un seul merge commit).

Vérification attendue en code review :
- grep `"Partiellement publié"` dans `http_server.py` → aucun résultat
- grep `"Non publié"` dans `http_server.py` → aucun résultat sauf commentaires historiques
- grep `"Partiellement publié"` dans `jeedom2ha.js` → aucun résultat sauf commentaires
- grep `"Non publié"` dans `jeedom2ha.js` → aucun résultat sauf commentaires

### Guardrail AI-3 — Test de synchronisation contraignant à deux couches

Le garde-fou AI-3 est implémenté par **deux tests complémentaires** :

**Couche 1 — Python, source contractuelle (`test_story_3_1_taxonomy_sync.py`) :**
- Lit `PRIMARY_STATUSES` depuis `taxonomy.py` (source de vérité)
- Extrait le **bloc `getStatusLabel`** via regex (pas le fichier entier) → échoue si le bloc est introuvable
- Vérifie que chaque label français est présent **dans ce bloc uniquement**
- Vérifie que les anciens statuts (`"Partiellement publié"`, `"Non publié"`) n'apparaissent pas comme cas nominaux dans le bloc
- **Résiste aux faux-positifs** : un label en commentaire ou dans `reasonLabels` ne fait pas passer ce test

**Couche 2 — JS, comportement réel (`test_story_3_1_status_labels.node.test.js`) :**
- Appelle `getStatusLabel()` réellement via `node:test` pour chaque label
- Vérifie que la valeur retournée est non-fallback et contient le bon label
- Vérifie la pureté de la fonction (pas de `(partiel)` dedans)
- Vérifie le call site du renderer pour le rendu partiel

**Ces deux tests sont permanents.** Ne pas les supprimer. Ne pas les affaiblir (ne pas revenir au test de fichier entier).

**Dérive détectée par le garde-fou :**
- Ajout d'un 6e statut dans `PRIMARY_STATUSES` sans `getStatusLabel` → couche 1 rouge
- `getStatusLabel` existe mais ne ge pas le statut correctement → couche 2 rouge
- Label présent dans un commentaire JS mais absent de la fonction → couche 1 rouge (ciblée)

### Guardrail AI-7 — Vérification intégrée à la code review

La code review de Story 3.1 doit vérifier explicitement :
1. `taxonomy.py` a le commentaire "ARTEFACT FIGÉ"
2. `test_story_3_1_taxonomy_sync.py` est présent, cible le **bloc `getStatusLabel`** (pas le fichier entier) et passe
3. `test_story_3_1_status_labels.node.test.js` est présent, appelle `getStatusLabel()` réellement et passe
4. Aucune logique `status` calculée en dehors de `get_primary_status(reason_code)` dans `_handle_system_diagnostics`
5. `jeedom2ha.js` gère les 5 statuts et ne gère plus `"Partiellement publié"` ni `"Non publié"` comme cas nominaux
6. `getStatusLabel` est pure — pas de `unmatched_commands` en argument — et le rendu `(partiel)` est au call site

---

## Stratégie de tests

### Couverture attendue

| Couche | Fichier | Rôle | Nbre tests estimé |
|---|---|---|---|
| Taxonomie Python (unitaire) | `test_story_3_1_taxonomy.py` | Résolution reason_code → primary_status, fallback, scénarios diagnostics | ~18 tests |
| Sync contrat backend/frontend (AI-3 couche 1) | `test_story_3_1_taxonomy_sync.py` | Extraction bloc `getStatusLabel`, présence des labels dans la fonction | ~6 tests |
| Labels JS + rendu partiel (AI-3 couche 2) | `test_story_3_1_status_labels.node.test.js` | Appel réel de `getStatusLabel()`, rendu call site, pureté de la fonction, absences attendues | ~12 tests |

### Distinction des responsabilités

**`test_story_3_1_taxonomy_sync.py` — garde-fou de contrat (Python) :**
Répond à : "Est-ce que chaque label de la taxonomie Python est présent dans la *fonction* `getStatusLabel` ?"
Méthode : extraction regex du bloc de la fonction dans le fichier JS. Pas d'exécution JS.
Dérive détectée : label ajouté à `taxonomy.py` sans mise à jour de `getStatusLabel`.

**`test_story_3_1_status_labels.node.test.js` — test de comportement (JS) :**
Répond à : "`getStatusLabel()` retourne-t-elle les bons résultats pour chaque statut ? Le rendu partiel au call site est-il correct ?"
Méthode : exécution réelle via `node:test`, assertions sur le HTML retourné.
Dérive détectée : `getStatusLabel` redéfinie avec une logique incorrecte, rendu partiel absent.

**Ces deux tests sont complémentaires, pas redondants.** L'un vérifie le contrat source, l'autre vérifie le comportement.

### Principe de test

- Pas de test terrain requis — les changements sont dans la couche diagnostic + JS rendu.
- Tests Python : `pytest`.
- Tests JS : `node:test` natif (pattern établi en Story 2.3).
- Le test AI-3 Python cible le bloc `getStatusLabel` (regex) — pas le fichier entier.

### Couverture minimale non négociable

1. Tous les `reason_code` du mapping ont un test de résolution correcte
2. Le fallback `"code_inexistant"` → `"Non supporté"` est testé
3. Aucun ancien statut (`"Partiellement publié"`, `"Non publié"`) ne sort du diagnostic
4. Le test AI-3 Python extrait le bloc de `getStatusLabel` et passe
5. Le test JS appelle `getStatusLabel()` pour les 5 statuts et valide les retours
6. Le rendu `(partiel)` au call site est couvert : cas complet ET cas partiel

---

## Risques et ambiguïtés résolues

### R1 — Ambiguïté : `disabled_eqlogic` → `Exclu` ou `Non supporté` ?

**Résolu : `Non supporté`.**
`disabled_eqlogic` correspond à un équipement désactivé dans Jeedom, pas à une exclusion volontaire de la publication. L'exclusion volontaire passe par `excluded_eqlogic` / `excluded_plugin` / `excluded_object`. Un équipement désactivé n'a pas été "exclu du bridge" — il est simplement inutilisable en l'état. `Non supporté` est le statut correct.

### R2 — Ambiguïté : `probable_skipped` → `Ambigu` ou `Non supporté` ?

**Résolu : `Ambigu`.**
`probable_skipped` signifie que le mapping existe avec confiance `probable`, mais la politique de publication est "sûr uniquement". Le mapping est donc non déterministe en termes de certitude → `Ambigu`. Ce n'est pas une absence de support, c'est une indétermination du mapping.

### R3 — Ambiguïté : faut-il ajouter un champ `primary_status` en parallèle de `status` ou remplacer `status` ?

**Résolu : remplacer `status` directement.**
L'ajout d'un champ parallèle crée une phase de transition où les deux coexistent avec des données possiblement contradictoires. Conformément à AI-2 (atomicité), on remplace. Le champ garde le nom `status` — seules les valeurs changent.

### R4 — Ambiguïté : la frontière entre 3.1 et 3.2 sur `_DIAGNOSTIC_MESSAGES`

**Résolu : 3.1 ne touche pas `_DIAGNOSTIC_MESSAGES`.**
Le texte de `detail` et `remediation` dans `_DIAGNOSTIC_MESSAGES` reste inchangé par 3.1. Si certains textes ne correspondent pas parfaitement à la nouvelle taxonomie, c'est acceptable : 3.2 les corrigera. La priorité de 3.1 est le contrat de statuts, pas le wording.

### R5 — Ambiguïté : `eligible` comme reason_code possible dans le payload final

**Résolu : `eligible` n'est jamais un reason_code final.**
Vérification dans le code : `reason_code = el_result.reason_code` est initialisé à `"eligible"` puis systématiquement surchargé dans chaque branche de `_handle_system_diagnostics`. La surcharge est garantie par la structure du code.

### R6 — Ambiguïté : affichage de `Non supporté` vs `Exclu` — même couleur `label-default` ?

**Résolu : même classe CSS, distinction optionnelle via style inline.**
Les deux statuts sont "neutres" (non publiés sans urgence). Leur différentiation visuelle peut se faire par un léger style inline sur `Non supporté` (ex: couleur #666 légèrement plus foncée) si l'agent le juge lisible. La priorité est la taxonomie, pas la différenciation chromatique. Si pas évident, même `label-default` pour les deux est acceptable pour 3.1.

---

## Critères de readiness pour `dev-story`

Story 3.1 est **prête pour `dev-story`** si et seulement si :

- [x] L'agent dev a lu cette story jusqu'à la fin
- [x] L'agent dev a lu `resources/daemon/transport/http_server.py:_handle_system_diagnostics` (lignes ~1448–1603)
- [x] L'agent dev a lu `desktop/js/jeedom2ha.js:getStatusLabel` et `reasonLabels`
- [x] L'agent dev a lu `resources/daemon/models/topology.py:assess_eligibility`
- [x] L'agent dev a compris la frontière 3.1 vs 3.2 (ne pas toucher `_DIAGNOSTIC_MESSAGES`)
- [x] L'agent dev a compris que Task 2 + Task 3 doivent être dans le même commit (AI-2)
- [x] L'agent dev a compris que Task 4 (test AI-3) est obligatoire avant de marquer la story done

---

## Impacts

### Backend

- `resources/daemon/models/taxonomy.py` — **NOUVEAU** (artefact figé)
- `resources/daemon/transport/http_server.py` — modifications ciblées dans `_handle_system_diagnostics` et `_STATUS_CODE_MAP`
- `resources/daemon/models/topology.py` — **NON MODIFIÉ**

### Frontend

- `desktop/js/jeedom2ha.js` — `getStatusLabel` réécrit pour 5 statuts + détail partiel

### Tests

- `tests/unit/test_story_3_1_taxonomy.py` — **NOUVEAU**
- `tests/unit/test_story_3_1_taxonomy_sync.py` — **NOUVEAU** (AI-3 guard permanent)
- `tests/unit/test_story_3_1_status_labels.node.test.js` — **NOUVEAU**

### Aucun impact sur

- `assess_eligibility()` — inchangé
- `_DIAGNOSTIC_MESSAGES` — inchangé
- Le contrat `published_scope` (Epic 1) — inchangé
- Le contrat de santé `/system/status` (Story 2.1) — inchangé
- Le gating des actions HA (Story 2.3) — inchangé

---

## Références

- [Epics V1.1 — Epic 3 et Story 3.1](_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md#epic-3)
- [Architecture Delta Review — §8](/_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md)
- [UX Delta Review — §4.3, §6.1, §6.2](_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md)
- [PRD V1.1 — §8.3](_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md)
- [Rétrospective Epic 2 — AI-1, AI-2, AI-3, AI-7](_bmad-output/implementation-artifacts/epic-2-retro-2026-03-25.md)
- [Story 2.4 — reasonLabels, getStatusLabel, analyse audit-first](_bmad-output/implementation-artifacts/2-4-distinction-stable-entre-infrastructure-et-configuration.md)

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4.6

### Debug Log References

- Correction `_build_traceability` : deux références à `published_statuses` (lignes 1399 et 1426) — supprimées et remplacées par `if status == "Publié"`.
- Chemin `_JS_FILE` dans `test_story_3_1_taxonomy_sync.py` corrigé : `parents[3]` → `parents[2]`.
- Regex `_GETSTATUS_PATTERN` corrigée : `.*?;` → `.*?};` pour capturer le bloc complet de `getStatusLabel`.
- Tests Story 2.4 mis à jour (comportements legacy post-Story 3.1) : `test_ambiguous_reason_stable_under_mqtt_state` (status `"Non publié"` → `"Ambigu"`), copie inline de `getStatusLabel` et tests css.

### Completion Notes List

- **Task 1** : `resources/daemon/models/taxonomy.py` créé avec commentaire figé, 5 `PRIMARY_STATUSES`, 16 entrées `REASON_CODE_TO_PRIMARY_STATUS`, `PRIMARY_STATUS_LABELS` (frozenset), `get_primary_status()` avec fallback `not_supported`.
- **Task 2** : `_handle_system_diagnostics` refactorisé — `get_primary_status(reason_code)` est le seul point d'assignation de `status`. `_EXCLUDED_REASON_CODES` supprimé. `_STATUS_CODE_MAP` mis à jour avec les 5 nouveaux statuts. `_build_traceability` corrigé (deux occurrences de `published_statuses`). `unmatched_commands` inchangé.
- **Task 3** : `getStatusLabel` réécrit pour 5 statuts (atomique avec Task 2). Suffixe `(partiel)` ajouté au call site dans `renderTable`. `isPublished` dans `buildDetailRow` simplifié. Suppression des cas `"Partiellement publié"` et `"Non publié"` (AI-2 : zéro occurrence résiduelle).
- **Task 4** : `test_story_3_1_taxonomy_sync.py` (AI-3 guard) — 9 tests, extraction regex du bloc `getStatusLabel` via `.*?};`, vérification de chaque label français dans le bloc, vérification absence des anciens statuts nominaux.
- **Task 5** : `test_story_3_1_taxonomy.py` — 31 tests couvrant tous les `reason_codes`, fallbacks, et 7 scénarios d'intégration endpoint `/system/diagnostics`.
- **Task 6** : `test_story_3_1_status_labels.node.test.js` (node:test) — 13 tests couvrant les 5 statuts, la pureté de `getStatusLabel`, le call site partiel, et les tests négatifs pour les anciens statuts.
- **Résultats finaux** : 425/425 pytest ✓, 61/61 node tests ✓, 0 régression.

### File List

- `resources/daemon/models/taxonomy.py` ← **NOUVEAU**
- `resources/daemon/transport/http_server.py` ← modifié (import taxonomy, `_STATUS_CODE_MAP`, `_handle_system_diagnostics`, `_build_traceability`, suppression `_EXCLUDED_REASON_CODES`)
- `desktop/js/jeedom2ha.js` ← modifié (`getStatusLabel` réécrit, `isPublished` simplifié, suffixe partiel au call site)
- `tests/unit/test_story_3_1_taxonomy.py` ← **NOUVEAU**
- `tests/unit/test_story_3_1_taxonomy_sync.py` ← **NOUVEAU** (AI-3 guard permanent)
- `tests/unit/test_story_3_1_status_labels.node.test.js` ← **NOUVEAU**
- `tests/unit/test_story_2_4_infra_separation.py` ← modifié (assertion `status == "Ambigu"` pour `ambiguous_skipped`)
- `tests/unit/test_story_2_4_visual_separation.node.test.js` ← modifié (copie `getStatusLabel` mise à jour, tests css statuts legacy)

---

**Story revision date:** 2026-03-25
**Cycle:** Post-MVP Phase 1 - V1.1 Pilotable
**Status:** review
