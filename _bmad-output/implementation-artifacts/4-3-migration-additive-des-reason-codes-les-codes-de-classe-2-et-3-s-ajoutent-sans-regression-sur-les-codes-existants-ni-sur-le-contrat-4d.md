# Story 4.3 : Migration additive des reason_codes — les codes de classe 2 et 3 s'ajoutent sans régression sur les codes existants ni sur le contrat 4D

Status: done

## Appartenance de cycle

**Cycle :** Moteur de Projection Explicable — `pe-epic-4`
**Entrée sprint-status :** `4-3-migration-additive-des-reason-codes-*` (cycle courant)

> Cette story 4.3 appartient exclusivement au cycle `pe-epic-4`. Elle est indépendante de toute story portant un identifiant "4.3" dans le cycle V1.1 Pilotable (terminé). Les deux cycles utilisent des numérotations locales sans lien entre elles. Aucune confusion de tracking ne doit être faite entre les deux.

## Story

En tant que mainteneur,
je veux que les reason_codes définis par AR8 (`ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown`, `ha_component_not_in_product_scope`) soient tous présents dans le catalogue `cause_mapping.py` avec un mapping complet et cohérent, sans renommer, supprimer ni inverser aucun code existant, et que le contrat 4D reste rétrocompatible à 100 %,
afin que les consommateurs du contrat de diagnostic (tests V1.1, systèmes en aval) ne soient pas cassés par le cycle courant.

## Frontière de responsabilité

### A — Contrat pipeline (INTANGIBLE — hors scope)

Le pipeline canonique et ses invariants sont définis dans `pipeline-contract.md` V2. Cette story ne touche à aucun aspect du pipeline.

`cause_mapping.py` NE DOIT PAS :
- modifier la logique d'une étape du pipeline
- requalifier un reason_code (ex : mapper un code de classe 3 vers un cause_code de classe 2)
- rediriger silencieusement un reason_code inconnu vers le triplet d'un code existant — le seul retour autorisé pour un code absent de la table est `(None, None, None)`, qui signifie "absence de cause mappable", non un alias d'un autre code
- ajouter de logique conditionnelle dans `reason_code_to_cause()` — seule la table change

### B — Traduction cause_mapping (SCOPE de la story)

`cause_mapping.py` implémente une **fonction pure** : `reason_code → (cause_code, cause_label, cause_action)`.

L'unique modification autorisée dans cette story est l'ajout d'entrées dans le dict `_REASON_CODE_TO_CAUSE`. Rien d'autre.

## Scope

### In-scope (les seuls fichiers modifiables)

| Fichier | Changement autorisé |
|---|---|
| `resources/daemon/models/cause_mapping.py` | Ajout d'entrées dans `_REASON_CODE_TO_CAUSE` uniquement |
| `resources/daemon/tests/unit/test_cause_mapping.py` | Ajout de tests uniquement |

### Hors scope (interdits de modification)

| Fichier | Raison |
|---|---|
| `resources/daemon/models/decide_publication.py` | Étape 4 figée — Story 4.1 |
| `resources/daemon/validation/ha_component_registry.py` | Registre figé — hors cycle |
| `resources/daemon/transport/http_server.py` | Orchestration — Epic 5 |
| `desktop/js/jeedom2ha.js` | Surface diagnostic — Story 4.2 |
| `desktop/js/jeedom2ha_diagnostic_helpers.js` | Idem |
| `resources/daemon/tests/unit/test_step4_decide_publication.py` | Non modifié |
| `resources/daemon/tests/unit/test_diagnostic_endpoint.py` | Non modifié |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` (entrées V1.1) | Les entrées epic-1 à epic-5 ne doivent pas être touchées — voir §Tracking |

## Acceptance Criteria

1. **Given** le catalogue complet de reason_codes existants, tel que capturé par le snapshot Phase 0
   **When** les nouveaux codes AR8 sont ajoutés
   **Then** tout reason_code existant conserve son nom exact, sa signification et son mapping (cause_code, cause_label, cause_action) inchangés (NFR8)
   **And** le snapshot de non-régression Phase 0 passe sans modification (comparaison stricte)

2. **Given** chaque reason_code de classe 2 absent au moment du checkpoint Phase 0 (`ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown`)
   **When** il traverse `reason_code_to_cause()`
   **Then** il produit un `cause_code` non-null distinct de `no_mapping` et `ambiguous_skipped`
   **And** un `cause_label` non-null et non vide
   **And** une `cause_action` qui est soit une chaîne valide, soit explicitement `None` (FR32)

3. **Given** le reason_code de classe 3 (`ha_component_not_in_product_scope`), que Phase 0 a trouvé présent ou absent
   **When** il traverse `reason_code_to_cause()`
   **Then** il produit `cause_code = "not_in_product_scope"`, `cause_label` non-null, et une `cause_action` non actionnable côté Jeedom
   **And** son mapping exact est identique à celui capturé dans le snapshot Phase 0 s'il était déjà présent, ou conforme au mapping prescriptif s'il a été ajouté par cette story

4. **Given** un reason_code quelconque absent de `_REASON_CODE_TO_CAUSE`
   **When** il traverse `reason_code_to_cause()`
   **Then** la fonction retourne `(None, None, None)` — ce retour est le comportement contractuel explicite du module, signifiant "absence de cause mappable" ; ce n'est pas un alias ou une redirection vers le triplet d'un autre code
   **And** aucune exception n'est levée
   **And** le reason_code inconnu n'est pas redirigé silencieusement vers le triplet d'un code existant

5. **Given** la table `_REASON_CODE_TO_CAUSE` après implémentation
   **When** chaque entrée est inspectée structurellement
   **Then** chaque entrée est un tuple à 3 éléments
   **And** si `cause_code` est non-null, alors `cause_label` est non-null (mapping complet ou triplet null/null/null — pas de mapping partiel)
   **And** si `cause_action` est renseignée, elle est une chaîne non vide

6. **Given** la suite de tests `test_cause_mapping.py` après cette story
   **When** elle est exécutée
   **Then** chaque entrée de `_REASON_CODE_TO_CAUSE` a au moins un test explicite
   **And** 0 failure, 0 error sur `test_cause_mapping.py`
   **And** 0 failure, 0 error sur la suite complète `tests/ resources/daemon/tests/`

## Tasks / Subtasks

---

### 🔒 Task 0 — GATE BLOQUANT : Checkpoint contrat `cause_mapping.py`

> **Critère bloquant :** Toutes les sous-tâches 0.1–0.7 doivent être complétées et leurs résultats documentés dans `Dev Agent Record / Completion Notes` AVANT de démarrer Task 1.
> **Aucune modification de fichier source n'est autorisée tant que Task 0 n'est pas soldée.**

- [x] 0.1 — Lire `resources/daemon/models/cause_mapping.py` dans son intégralité
- [x] 0.2 — Dresser l'inventaire exhaustif de `_REASON_CODE_TO_CAUSE` : lister chaque `reason_code` avec son triplet exact `(cause_code, cause_label, cause_action)` — voir Dev Notes §Inventaire de référence pour la baseline attendue
- [x] 0.3 — Pour chacun des 5 codes AR8, noter s'il est **présent** ou **absent** dans la table :
  - `ha_missing_command_topic` → **absent**
  - `ha_missing_state_topic` → **absent**
  - `ha_missing_required_option` → **absent**
  - `ha_component_unknown` → **absent**
  - `ha_component_not_in_product_scope` → **présent** (ajouté par Story 4.2)
- [x] 0.4 — Lire `resources/daemon/tests/unit/test_cause_mapping.py` et identifier les reason_codes qui ont un test et ceux qui n'en ont pas — voir Dev Notes §Gap de test de référence
- [x] 0.5 — Lire `resources/daemon/validation/ha_component_registry.py` : `_REASON_PRIORITY`, `_CAPABILITY_TO_REASON`, `validate_projection()` — comprendre dans quel contexte chaque code classe 2 est produit
- [x] 0.6 — **Vérifier le snapshot de référence** : comparer l'inventaire établi en 0.2 avec le `_BASELINE_SNAPSHOT` fourni dans Dev Notes §Snapshot de non-régression — ce snapshot est l'oracle contractuel, il n'est pas à reconstruire ; si une divergence est constatée (clé manquante, valeur différente, clé supplémentaire) : **STOP** — noter l'écart dans `Completion Notes` et ne pas démarrer Task 1 tant que l'écart n'est pas expliqué et résolu
- [x] 0.7 — **Valider les règles contractuelles** : confirmer explicitement dans `Completion Notes` que aucun code existant ne sera modifié dans ce qui suit

---

### Task 1 — Ajouter les codes AR8 manquants dans `_REASON_CODE_TO_CAUSE` (AC: #2, #3)

> **Prérequis :** Task 0 soldée.
> N'ajouter que les codes trouvés **absents** à l'étape 0.3. Ne pas toucher aux codes trouvés présents.

- [x] 1.1 — Pour chaque code trouvé absent par Phase 0, ajouter l'entrée selon le mapping prescriptif de Dev Notes §Mapping prescriptif AR8
- [x] 1.2 — Vérifier que les clés et les valeurs des entrées préexistantes n'ont pas été modifiées (l'ordre des entrées dans le dict n'est pas contractuel — seules les clés et leurs triplets le sont)
- [x] 1.3 — Vérifier que la logique de `reason_code_to_cause()` et `build_cause_for_pending_unpublish()` n'a pas été modifiée
- [x] 1.4 — Mettre à jour le commentaire d'en-tête du fichier pour refléter le nouveau total d'entrées actives

---

### Task 2 — Tests de non-régression snapshot (AC: #1)

> Combler le gap de non-régression identifié en 0.4 et verrouiller la baseline complète.

- [x] 2.1 — Ajouter dans `test_cause_mapping.py` la fonction `test_non_regression_snapshot()` — voir Dev Notes §Snapshot de non-régression pour le code exact
- [x] 2.2 — Ajouter les tests individuels des codes trouvés sans test par Phase 0 (baseline attendue : `excluded_eqlogic`, `excluded_plugin`, `excluded_object`) — voir Dev Notes §Tests de non-régression individuels

---

### Task 3 — Tests des nouveaux codes (AC: #2, #3)

> Un test par code trouvé absent à l'étape 0.3 et ajouté par Task 1.

- [x] 3.1 — `test_ha_missing_command_topic()` — vérification du triplet exact conforme au mapping prescriptif
- [x] 3.2 — `test_ha_missing_state_topic()` — idem
- [x] 3.3 — `test_ha_missing_required_option()` — idem
- [x] 3.4 — `test_ha_component_unknown()` — triplet exact, `cause_action is None` explicitement vérifié
- [x] 3.5 — `ha_component_not_in_product_scope` était **présent** (ajouté par Story 4.2) → test additive non requis ; déjà couvert par `test_ha_component_not_in_product_scope` et `test_ha_component_not_in_product_scope_maps_to_not_in_product_scope` (Task 4.4)

---

### Task 4 — Tests anti-contrat (AC: #4, #5)

- [x] 4.1 — `test_unknown_code_contractual_return()` — un code inexistant retourne `(None, None, None)` sans exception et sans redirection vers un autre triplet (voir Dev Notes §Tests anti-contrat)
- [x] 4.2 — `test_no_partial_mapping_in_table()` — boucle sur `_REASON_CODE_TO_CAUSE`, vérification structurelle : `cause_code` non-null implique `cause_label` non-null, pas de mapping partiel (voir Dev Notes §Tests anti-contrat)
- [x] 4.3 — `test_classe2_codes_distinct_from_mapping_failures()` — **à exécuter après Task 1** : pour chaque code classe 2 présent dans `_REASON_CODE_TO_CAUSE`, vérifier que `cause_code` n'est pas `"no_mapping"` ni `"ambiguous_skipped"` — le test commence par asserter la présence du code dans la table pour éviter un faux négatif si Task 1 n'a pas été exécutée (voir Dev Notes §Tests anti-contrat)
- [x] 4.4 — `test_ha_component_not_in_product_scope_maps_to_not_in_product_scope()` — vérifier que `cause_code = "not_in_product_scope"` (non-régression / conformité AR8, que le code ait été ajouté par 4.2 ou par cette story)

---

### Task 5 — Non-régression globale (AC: #6)

- [x] 5.1 — `python3 -m pytest resources/daemon/tests/unit/test_cause_mapping.py -v` → **31 passed**, 0 failure ✅ (≥ 28)
- [x] 5.2 — `python3 -m pytest tests/ resources/daemon/tests/ -q` → **940 passed**, 0 failure, 0 error ✅

---

### Task 6 — Tracker (cycle courant uniquement)

- [ ] 6.1 — `_bmad-output/implementation-artifacts/sprint-status.yaml` : mettre à jour **uniquement** l'entrée `4-3-migration-additive-des-reason-codes-*` → `done` après code review APPROVE
- [ ] 6.2 — Ne pas toucher aux entrées `epic-1` à `epic-5` (cycle V1.1 — terminé) ni à aucune autre entrée du fichier

---

## Dev Notes

### Inventaire de référence (baseline Phase 0)

Le dev agent DOIT vérifier ces valeurs en lisant le fichier réel. Les valeurs ci-dessous constituent la baseline établie lors de la création de cette story — elles servent de référence pour le snapshot de non-régression.

**`resources/daemon/models/cause_mapping.py` — `_REASON_CODE_TO_CAUSE`**

Entrées actives direction 1 — inclus mais non publié :

```python
"excluded_eqlogic": (
    "excluded_eqlogic",
    "Équipement exclu du scope de synchronisation",
    "Retirer l'équipement de la liste d'exclusion dans les réglages jeedom2ha",
),
"excluded_plugin": (
    "excluded_plugin",
    "Plugin exclu du scope de synchronisation",
    "Retirer le plugin de la liste d'exclusion dans les réglages jeedom2ha",
),
"excluded_object": (
    "excluded_object",
    "Objet Jeedom exclu du scope de synchronisation",
    "Retirer l'objet de la liste d'exclusion dans les réglages jeedom2ha",
),
"ambiguous_skipped": (
    "ambiguous_skipped",
    "Mapping ambigu — plusieurs types possibles",
    "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
),
"probable_skipped": (
    "ambiguous_skipped",
    "Mapping ambigu — plusieurs types possibles",
    "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
),
"no_mapping": (
    "no_mapping",
    "Aucun mapping compatible",
    "Vérifier les types génériques des commandes dans Jeedom",
),
"no_supported_generic_type": (
    "no_supported_generic_type",
    "Type non supporté en V1",
    None,
),
"no_generic_type_configured": (
    "no_generic_type_configured",
    "Types génériques non configurés sur les commandes",
    "Configurer les types génériques via le plugin Jeedom concerné, puis relancer un rescan",
),
"disabled_eqlogic": (
    "disabled_eqlogic",
    "Équipement désactivé dans Jeedom",
    "Activer l'équipement dans sa page de configuration Jeedom",
),
"disabled": (
    "disabled_eqlogic",
    "Équipement désactivé dans Jeedom",
    "Activer l'équipement dans sa page de configuration Jeedom",
),
"no_commands": (
    "no_commands",
    "Équipement sans commandes exploitables",
    "Vérifier que l'équipement possède des commandes actives dans Jeedom",
),
"discovery_publish_failed": (
    "discovery_publish_failed",
    "Publication MQTT échouée",
    "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
),
"local_availability_publish_failed": (
    "discovery_publish_failed",
    "Publication MQTT échouée",
    "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
),
"low_confidence": (
    "low_confidence",
    "Confiance insuffisante pour la politique active",
    "Assouplir la politique de confiance si vous souhaitez autoriser un mapping moins fiable.",
),
"ha_component_not_in_product_scope": (
    "not_in_product_scope",
    "Composant Home Assistant non ouvert dans ce cycle",
    "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant.",
),
"eligible": (
    "no_mapping",
    "Aucun mapping compatible",
    "Relancer un sync complet depuis l'interface du plugin",
),
```

Entrées published — pas d'écart direction 1 :

```python
"sure":         (None, None, None),
"probable":     (None, None, None),
"sure_mapping": (None, None, None),
```

Total attendu : **19 entrées**. Si le fichier réel diffère de cette baseline, arrêter et signaler l'écart avant toute implémentation.

---

### Gap de test de référence (baseline Phase 0)

`resources/daemon/tests/unit/test_cause_mapping.py` — 18 tests existants.

Codes sans test dans la baseline (à couvrir par Task 2) :
- `excluded_eqlogic`
- `excluded_plugin`
- `excluded_object`

Si Phase 0 révèle un état différent, adapter les tâches de Task 2 en conséquence.

---

### Mapping prescriptif AR8 — codes à ajouter

Ces valeurs définissent le mapping attendu pour les codes AR8 trouvés absents par Phase 0.

```python
# Classe 2 — Validation HA (étape 3) — 4 codes
"ha_missing_command_topic": (
    "ha_missing_command_topic",
    "Projection HA invalide — commande d'action manquante",
    "Vérifier que les commandes de l'équipement incluent une commande d'action compatible dans Jeedom",
),
"ha_missing_state_topic": (
    "ha_missing_state_topic",
    "Projection HA invalide — commande d'état manquante",
    "Vérifier que les commandes de l'équipement incluent une commande d'état compatible dans Jeedom",
),
"ha_missing_required_option": (
    "ha_missing_required_option",
    "Projection HA invalide — option requise par le composant Home Assistant manquante",
    "Vérifier que les commandes de l'équipement couvrent les options requises par le composant Home Assistant cible",
),
"ha_component_unknown": (
    "ha_component_unknown",
    "Composant Home Assistant non reconnu par le moteur",
    None,  # FR33 — aucune remédiation utilisateur directe
),
# Classe 3 — Scope produit (étape 4) — 1 code
# N'ajouter que si absent à Phase 0. Si déjà présent, ne pas modifier.
"ha_component_not_in_product_scope": (
    "not_in_product_scope",
    "Composant Home Assistant non ouvert dans ce cycle",
    "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant.",
),
```

**Justifications :**
- `cause_code = reason_code` pour les 4 codes classe 2 : symétrie intentionnelle, pas d'alias
- `cause_action = None` pour `ha_component_unknown` : le composant n'est pas dans `HA_COMPONENT_REGISTRY` — aucune action utilisateur (FR33)
- Préfixe "Projection HA invalide —" dans les labels classe 2 : distingue visuellement étape 3 des étapes 1–2

---

### Contexte de production des codes classe 2

Source : `resources/daemon/validation/ha_component_registry.py`

| reason_code | Déclencheur dans `validate_projection()` | Composants |
|---|---|---|
| `ha_missing_command_topic` | `has_command` non satisfait | light, switch (+ futurs hors scope) |
| `ha_missing_state_topic` | `has_state` non satisfait | sensor, binary_sensor (connus, hors PRODUCT_SCOPE) |
| `ha_missing_required_option` | `has_options` non satisfait | select (connu, hors PRODUCT_SCOPE) |
| `ha_component_unknown` | `ha_entity_type not in HA_COMPONENT_REGISTRY` | tout type inconnu |

---

### Snapshot de non-régression

> Ce snapshot est l'**oracle contractuel** fourni par cette story. Il n'est pas à reconstruire : Task 0.6 demande de le vérifier contre le code réel. Le test `test_non_regression_snapshot()` utilise ce dict directement.

**Test à ajouter dans `test_cause_mapping.py` (Task 2.1) :**

```python
# Oracle de non-régression — Story 4.3.
# Établi lors de la création de la story. Vérifié (pas reconstruit) en Phase 0.
# Contient UNIQUEMENT les codes existants avant implémentation (19 entrées).
# NE PAS modifier ce snapshot — toute divergence après implémentation est une régression.
_BASELINE_SNAPSHOT = {
    "excluded_eqlogic": (
        "excluded_eqlogic",
        "Équipement exclu du scope de synchronisation",
        "Retirer l'équipement de la liste d'exclusion dans les réglages jeedom2ha",
    ),
    "excluded_plugin": (
        "excluded_plugin",
        "Plugin exclu du scope de synchronisation",
        "Retirer le plugin de la liste d'exclusion dans les réglages jeedom2ha",
    ),
    "excluded_object": (
        "excluded_object",
        "Objet Jeedom exclu du scope de synchronisation",
        "Retirer l'objet de la liste d'exclusion dans les réglages jeedom2ha",
    ),
    "ambiguous_skipped": (
        "ambiguous_skipped",
        "Mapping ambigu — plusieurs types possibles",
        "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
    ),
    "probable_skipped": (
        "ambiguous_skipped",
        "Mapping ambigu — plusieurs types possibles",
        "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
    ),
    "no_mapping": (
        "no_mapping",
        "Aucun mapping compatible",
        "Vérifier les types génériques des commandes dans Jeedom",
    ),
    "no_supported_generic_type": ("no_supported_generic_type", "Type non supporté en V1", None),
    "no_generic_type_configured": (
        "no_generic_type_configured",
        "Types génériques non configurés sur les commandes",
        "Configurer les types génériques via le plugin Jeedom concerné, puis relancer un rescan",
    ),
    "disabled_eqlogic": (
        "disabled_eqlogic",
        "Équipement désactivé dans Jeedom",
        "Activer l'équipement dans sa page de configuration Jeedom",
    ),
    "disabled": (
        "disabled_eqlogic",
        "Équipement désactivé dans Jeedom",
        "Activer l'équipement dans sa page de configuration Jeedom",
    ),
    "no_commands": (
        "no_commands",
        "Équipement sans commandes exploitables",
        "Vérifier que l'équipement possède des commandes actives dans Jeedom",
    ),
    "discovery_publish_failed": (
        "discovery_publish_failed",
        "Publication MQTT échouée",
        "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
    ),
    "local_availability_publish_failed": (
        "discovery_publish_failed",
        "Publication MQTT échouée",
        "Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution",
    ),
    "low_confidence": (
        "low_confidence",
        "Confiance insuffisante pour la politique active",
        "Assouplir la politique de confiance si vous souhaitez autoriser un mapping moins fiable.",
    ),
    "ha_component_not_in_product_scope": (
        "not_in_product_scope",
        "Composant Home Assistant non ouvert dans ce cycle",
        "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant.",
    ),
    "eligible": (
        "no_mapping",
        "Aucun mapping compatible",
        "Relancer un sync complet depuis l'interface du plugin",
    ),
    "sure":         (None, None, None),
    "probable":     (None, None, None),
    "sure_mapping": (None, None, None),
}


def test_non_regression_snapshot():
    """SNAPSHOT — baseline figée au checkpoint Phase 0 de Story 4.3.

    Si ce test échoue après un changement de code : régression détectée sur un code existant.
    Ce snapshot NE DOIT PAS être modifié — sauf si une story dédiée l'autorise explicitement.
    """
    for reason_code, expected in _BASELINE_SNAPSHOT.items():
        actual = reason_code_to_cause(reason_code)
        assert actual == expected, (
            f"RÉGRESSION sur {reason_code!r}:\n"
            f"  attendu : {expected!r}\n"
            f"  obtenu  : {actual!r}"
        )
```

---

### Tests de non-régression individuels

**À ajouter dans `test_cause_mapping.py` (Task 2.2) — codes sans test dans la baseline :**

```python
def test_excluded_eqlogic():
    assert reason_code_to_cause("excluded_eqlogic") == (
        "excluded_eqlogic",
        "Équipement exclu du scope de synchronisation",
        "Retirer l'équipement de la liste d'exclusion dans les réglages jeedom2ha",
    )

def test_excluded_plugin():
    assert reason_code_to_cause("excluded_plugin") == (
        "excluded_plugin",
        "Plugin exclu du scope de synchronisation",
        "Retirer le plugin de la liste d'exclusion dans les réglages jeedom2ha",
    )

def test_excluded_object():
    assert reason_code_to_cause("excluded_object") == (
        "excluded_object",
        "Objet Jeedom exclu du scope de synchronisation",
        "Retirer l'objet de la liste d'exclusion dans les réglages jeedom2ha",
    )
```

---

### Tests anti-contrat

**À ajouter dans `test_cause_mapping.py` (Task 4) :**

```python
def test_unknown_code_contractual_return():
    """Contrat explicite : un reason_code absent de _REASON_CODE_TO_CAUSE retourne (None, None, None).

    Ce retour signifie "absence de cause mappable". Ce n'est pas un alias ni une redirection
    vers le triplet d'un code existant. C'est le comportement contractuel documenté du module.
    """
    assert reason_code_to_cause("__unknown_xyz__") == (None, None, None)
    assert reason_code_to_cause("") == (None, None, None)
    # Vérification supplémentaire : le retour ne correspond au triplet d'aucun code connu
    from models.cause_mapping import _REASON_CODE_TO_CAUSE
    known_triplets = set(_REASON_CODE_TO_CAUSE.values())
    assert (None, None, None) in known_triplets  # (None, None, None) est un triplet contractuel connu (codes published)
    # Le fait qu'il soit partagé avec les codes published est documenté — ce n'est pas un remapping


def test_no_partial_mapping_in_table():
    """Aucune entrée de la table ne doit avoir un mapping partiel.

    Règle : si cause_code est non-null, cause_label doit être non-null.
    Un triplet (cause_code, None, ...) est interdit — ce serait un mapping incomplet.
    Seul le triplet (None, None, None) est accepté comme "pas d'écart direction 1".
    """
    from models.cause_mapping import _REASON_CODE_TO_CAUSE
    for code, triple in _REASON_CODE_TO_CAUSE.items():
        assert isinstance(triple, tuple) and len(triple) == 3, (
            f"{code!r}: entrée malformée — attendu un tuple à 3 éléments, obtenu {triple!r}"
        )
        cause_code, cause_label, cause_action = triple
        if cause_code is not None:
            assert isinstance(cause_code, str) and cause_code, (
                f"{code!r}: cause_code non-null doit être une chaîne non vide"
            )
            assert isinstance(cause_label, str) and cause_label, (
                f"{code!r}: cause_code={cause_code!r} présent mais cause_label={cause_label!r} — mapping partiel interdit"
            )
        if cause_action is not None:
            assert isinstance(cause_action, str) and cause_action, (
                f"{code!r}: cause_action renseignée doit être une chaîne non vide"
            )


def test_classe2_codes_distinct_from_mapping_failures():
    """Après Task 1 : chaque code classe 2 présent dans la table a un cause_code distinct des classes mapping.

    Ce test s'applique aux codes effectivement présents dans _REASON_CODE_TO_CAUSE.
    Il commence par asserter la présence de chaque code pour éviter un faux négatif
    si Task 1 n'a pas été exécutée — dans ce cas, le test échoue explicitement sur l'absence.
    """
    from models.cause_mapping import _REASON_CODE_TO_CAUSE
    classe2_codes = [
        "ha_missing_command_topic",
        "ha_missing_state_topic",
        "ha_missing_required_option",
        "ha_component_unknown",
    ]
    for code in classe2_codes:
        assert code in _REASON_CODE_TO_CAUSE, (
            f"{code!r} absent de _REASON_CODE_TO_CAUSE — ce test doit s'exécuter après Task 1"
        )
        cause_code, _, _ = reason_code_to_cause(code)
        assert cause_code not in (None, "no_mapping", "ambiguous_skipped"), (
            f"{code!r}: cause_code={cause_code!r} — confond validation HA avec un échec de mapping"
        )


def test_ha_component_not_in_product_scope_maps_to_not_in_product_scope():
    """cause_code = 'not_in_product_scope' — invariant AR8 / classe 3."""
    cause_code, cause_label, _ = reason_code_to_cause("ha_component_not_in_product_scope")
    assert cause_code == "not_in_product_scope"
    assert cause_label is not None and len(cause_label) > 0
```

---

### Règles contractuelles — non-négociables

| Comportement | Statut |
|---|---|
| Renommer un reason_code existant | ❌ INTERDIT |
| Modifier cause_code, cause_label ou cause_action d'une entrée existante | ❌ INTERDIT |
| Supprimer une entrée | ❌ INTERDIT |
| Inverser le sens d'un mapping | ❌ INTERDIT |
| Modifier `reason_code_to_cause()` (logique) | ❌ INTERDIT |
| Modifier `build_cause_for_pending_unpublish()` | ❌ INTERDIT |
| Ajouter une logique conditionnelle dans `reason_code_to_cause()` | ❌ INTERDIT |
| Mapper un code classe 2 vers `cause_code = "no_mapping"` | ❌ INTERDIT |

**Compatibilité descendante (NFR7) :** même input → même output sur toute entrée existante, avant et après la story. Le snapshot de non-régression est la vérification automatique de cette propriété.

---

### Tracking du cycle courant

Le fichier `_bmad-output/implementation-artifacts/sprint-status.yaml` couvre **deux cycles** :
- Cycle V1.1 Pilotable — clôturé (entrées `epic-1` à `epic-5`) → **ne pas toucher**
- Cycle Moteur de Projection Explicable — courant (entrées `pe-epic-1` à `pe-epic-6` + stories)

Cette story ne modifie que l'entrée :
```
4-3-migration-additive-des-reason-codes-*: done
```
Après code review APPROVE uniquement.

### Dev Agent Guardrails

- **CONFIRMER** en 0.2 que le total de `_REASON_CODE_TO_CAUSE` est 19 avant implémentation ; sinon signaler l'écart
- **NE PAS** démarrer Task 1 si Task 0 n'est pas complète et documentée dans `Completion Notes`
- **NE PAS** modifier une valeur existante dans `_REASON_CODE_TO_CAUSE` — toute modification d'une entrée existante est une violation de NFR8
- **NE PAS** omettre `None` explicite pour `cause_action` de `ha_component_unknown` — le dict attend une valeur, pas l'absence de clé
- **NE PAS** aliaser les codes classe 2 entre eux — chaque code a son propre cause_code
- **CONFIRMER** que `test_non_regression_snapshot()` passe avant de déclarer Task 2 terminée
- **CONFIRMER** total de tests ≥ 28 après la story (18 baseline + 10 minimum)

### References

- [Source: `resources/daemon/models/cause_mapping.py`] — table `_REASON_CODE_TO_CAUSE` et `reason_code_to_cause()`
- [Source: `resources/daemon/tests/unit/test_cause_mapping.py`] — 18 tests baseline
- [Source: `resources/daemon/validation/ha_component_registry.py`] — `_REASON_PRIORITY`, `_CAPABILITY_TO_REASON`, `validate_projection()`
- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` §Règles globales règle 6] — migration additive uniquement
- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` §Étape 3] — reason_codes classe 2 contractuels
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 4.3] — user story, ACs, AR8 / NFR7 / NFR8 / FR43-FR45
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §AR8] — 5 codes additifs définis contractuellement
- [Source: `_bmad-output/implementation-artifacts/4-2-*`] — story 4.2 a ajouté `low_confidence` et `ha_component_not_in_product_scope` — leur état réel est vérifié en Phase 0, pas assumé
- [Source: `_bmad-output/implementation-artifacts/pe-epic-3-retro-2026-04-13.md` §AI-2] — checkpoint contrat cause_mapping.py comme prérequis de cette story

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

**Task 0 — GATE Phase 0 (2026-04-15)**

- `_REASON_CODE_TO_CAUSE` : 19 entrées — conforme au `_BASELINE_SNAPSHOT`. Zéro divergence.
- Codes AR8 absents (à ajouter par Task 1) : `ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown`.
- `ha_component_not_in_product_scope` **présent** (ajouté par Story 4.2) → ne pas modifier.
- Tests baseline : 19 tests réels (le docstring interne dit 16, la story dit 18 — écart documenté : story 4.1 n'a pas mis à jour le docstring après ajouts 4.2). Gap : `excluded_eqlogic`, `excluded_plugin`, `excluded_object` sans test individuel — conforme à la baseline story.
- Règles contractuelles confirmées : seules les 4 entrées absentes seront ajoutées, aucune entrée existante modifiée.
- Note : le commentaire inline `# --- 15 entrées actives` dans cause_mapping.py est déjà obsolète (16 actives avant story 4.3) — sera corrigé à 20 par Task 1.4.

### File List

- `resources/daemon/models/cause_mapping.py` — ajout de 4 entrées AR8 dans `_REASON_CODE_TO_CAUSE` ; commentaires d'en-tête mis à jour (20 actives + 3 published)
- `resources/daemon/tests/unit/test_cause_mapping.py` — ajout de 12 tests (snapshot, non-régression individuels, nouveaux codes, anti-contrat) ; total 31 tests ; docstring corrigé (code review)

### Change Log

- **2026-04-15** — Story 4.3 : ajout additif de 4 codes AR8 classe 2 (`ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown`) dans `_REASON_CODE_TO_CAUSE` ; 12 nouveaux tests ; 940/940 non-régression PASS
- **2026-04-15** — Code review APPROVE (claude-opus-4-6) : 0 finding HIGH/MEDIUM, 1 LOW (docstring test file obsolète — fixé) ; 31/31 + 940/940 confirmés
