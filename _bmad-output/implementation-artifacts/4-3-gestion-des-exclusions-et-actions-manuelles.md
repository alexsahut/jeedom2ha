# Story 4.3: Exclusion Multicritères et Gestion du Périmètre Publié

Status: done

## Story

As a **utilisateur Jeedom**,
I want **configurer finement ce qui est publié vers HA selon plusieurs critères d'exclusion et une politique de confiance, et forcer un rescan complet**,
so that **je garde mon installation Home Assistant propre, sans équipements parasites ni entités fantômes.**

---

## Story hardening decisions

### Décisions d'arbitrage V2 vs V1

**1. Titre** : inchangé — "Exclusion Multicritères et Gestion du Périmètre Publié" correspond exactement au scope. Le "Rescan" du bouton UI est une "action manuelle" au sens large mais ne mérite pas d'être dans le titre. Cohérent avec le fichier epics.md.

**2. Priorité des exclusions** : déterministe et explicite — `eqlogic > plugin > object`. Si un équipement est exclu par plusieurs critères simultanément, seule la source la plus prioritaire est reportée dans `exclusion_source`. Cela évite toute ambiguïté dans les diagnostics et les traces. Cette règle est répercutée dans les AC, Dev Notes et tests.

**3. Dépublication sur changement de politique de confiance (GAP CRITIQUE de la V1)** : La V1 affirmait à tort que `eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids` couvrait ce cas. Ce n'est pas vrai : un équipement éligible (non exclu, actif) mais bloqué par `sure_only` est toujours ajouté à `nouveaux_eq_ids` → il n'est JAMAIS dans `eq_ids_supprimes` → le message MQTT retained reste → HA conserve l'entité fantôme. Ce cas est désormais explicite en AC B.2 et Task 2.7.

**4. UX configuration CSV** : conservée en V1 — c'est le meilleur compromis sans dérive de scope. Les Dev Notes précisent maintenant : trim, dedup, ignore valeurs vides, placeholder avec exemples, aide textuelle orientée métier. Pas de validation dynamique contre les plugins Jeedom connus (scope V1).

**5. Impacts traçabilité** :
- `_CLOSED_REASON_MAP` : manquait `excluded_plugin` et `excluded_object` → ajoutés (Task 2.6, MANQUANT V1).
- `_handle_system_diagnostics` : check hardcodé `if el_result.reason_code == "excluded_eqlogic"` → doit être remplacé par `if el_result.reason_code in _EXCLUDED_REASON_CODES` (Task 2.8, MANQUANT V1).
- `_DIAGNOSTIC_MESSAGES` : inchangé dans son principe, mais les nouvelles entrées sont rendues obligatoires et testées.
- `_build_traceability()` : aucune modification nécessaire — les nouveaux codes tombent dans le bucket "exclu" via `_CLOSED_REASON_MAP`.

**6. Compatibilité code existant** :
- `scanTopology` dans `jeedom2ha.ajax.php` : EXISTE déjà → la story ne demande PAS de le créer.
- `is_excluded` dans `JeedomEqLogic` : EXISTE déjà → seul `exclusion_source` est ajouté.
- `decide_publication(mapping)` sans `confidence_policy` : DOIT rester valide (défaut `"sure_probable"`).
- `LIGHT_PUBLICATION_POLICY` / `COVER_PUBLICATION_POLICY` / `SWITCH_PUBLICATION_POLICY` : constantes module — ne pas modifier, surcharger via copie locale dans `decide_publication()`.

### Décision d'arbitrage V3 — Sauvegarde avant rescan (CORRECTION V2)

**Problème identifié dans la V2** : L'AC C.2 affirmait "la configuration est d'abord sauvegardée automatiquement par Jeedom (via `configKey` pattern)". C'est **factuellement faux**.

- `scanTopology` (ligne 126 de `jeedom2ha.ajax.php`) appelle `getFullTopology()` qui lit la config via `config::byKey()` — uniquement depuis la DB déjà persistée.
- Le pattern `configKey` est sauvegardé **uniquement** quand l'utilisateur clique le bouton "Sauvegarder" injecté par Jeedom core dans l'en-tête de la page de configuration — PAS automatiquement lors d'un clic sur un bouton custom.
- Si l'utilisateur modifie `excludedPlugins` puis clique "Appliquer et Rescanner" sans avoir cliqué "Sauvegarder" d'abord, le rescan utilise l'ANCIENNE config en base. Le bouton promet "Appliquer" mais n'applique rien.

**Arbitrage retenu : Option A — vrai bouton "Appliquer et Rescanner"**

Raisons :
- Option B (renommer en "Rescanner") = UX trompeuse : l'utilisateur venant de modifier ses exclusions attend que ses changements soient pris en compte.
- Le pattern `forceMqttManagerImport` établit exactement le précédent : un handler PHP appelle `config::save()` directement. C'est la voie propre dans Jeedom sans dépendre des internals non-documentés du core JS.
- Un handler `saveFilteringConfig` ciblé sur les 3 clés de filtrage est justifié (pas "inutile") : `scanTopology` ne peut pas recevoir ces valeurs en paramètre car `getFullTopology()` lit depuis la DB.

**Implémentation retenue** :
- Nouveau handler PHP `saveFilteringConfig` dans `jeedom2ha.ajax.php` : accepte `excludedPlugins`, `excludedObjects`, `confidencePolicy` en POST, appelle `config::save()` pour chacun, valide les valeurs, retourne succès.
- Le JS du bouton chaîne : POST `saveFilteringConfig` (succès) → POST `scanTopology`.
- Si `saveFilteringConfig` échoue → afficher erreur, ne pas lancer le scan.

**Impact UX** :
- Bouton nommé "Appliquer et Rescanner" — label conservé, sémantique désormais exacte.
- En cas d'échec de sauvegarde : message d'erreur clair avant tout rescan.
- En cas de succès : afficher le résultat du scan (nombre d'équipements publiés).

**Impact sur les AC / tâches / tests** :
- AC C.2 : corrigé — le flux explicite est : sauvegarde des 3 clés → confirmation → scan.
- Task 3.2 : ajouter la création du handler `saveFilteringConfig` en PHP.
- Task 3.3 (JS) : JS chaîne les deux appels séquentiellement.
- Test 4.9 (nouveau) : test unitaire ou d'intégration du chaînage save→scan.

---

## Acceptance Criteria

### Partie A — Moteur de filtrage multicritères (daemon)

**AC A.1 — Exclusion par critères multiples**
Given des critères d'exclusion sont configurés (plugin, objet, ou individuel)
When un sync/rescan est déclenché
Then les équipements correspondant à au moins un critère ne sont pas publiés dans HA
And les critères supportés sont : plugin source (`eq_type_name`), pièce/objet Jeedom (id), équipement individuel

**AC A.2 — Priorité d'exclusion déterministe**
Given un équipement matche plusieurs critères simultanément (ex : exclu individuellement ET son plugin est exclu)
When le payload topology est construit
Then `exclusion_source` vaut `"eqlogic"` (priorité la plus haute)
And l'ordre de priorité est : `eqlogic > plugin > object`
And un seul `reason_code` est produit par `assess_eligibility()` en fonction de cette priorité

**AC A.3 — Unpublish des équipements nouvellement exclus**
Given un équipement était publié dans HA lors du sync précédent
When il devient exclu (via un critère quelconque) au sync suivant
Then son message MQTT Discovery retained est supprimé (unpublish)
And il n'est plus visible dans HA

**AC A.4 — Visibilité dans le diagnostic**
Given un équipement est exclu par plugin, objet, ou individuellement
When l'utilisateur consulte le diagnostic
Then l'équipement apparaît avec statut "Exclu" (même UI que l'exclusion individuelle)
And la raison d'exclusion est visible dans le détail (`excluded_eqlogic`, `excluded_plugin`, ou `excluded_object`)

### Partie B — Politique de confiance configurable

**AC B.1 — Filtrage par niveau de confiance**
Given l'utilisateur a choisi `sure_only`
When le moteur de mapping produit un résultat avec confidence `probable`
Then cet équipement n'est PAS publié dans HA
And la politique `sure_probable` (défaut) publie les `sure` ET les `probable`
And la politique s'applique à tous les domaines (light, cover, switch)

**AC B.2 — Dépublication sur changement de politique (cas critique)**
Given un équipement était publié avec confidence `probable` sous la politique `sure_probable`
When l'utilisateur passe en `sure_only` et déclenche un rescan
Then cet équipement est dépublié (son message MQTT retained est supprimé)
And il n'est plus visible dans HA après le rescan
And il apparaît dans le diagnostic avec son `reason_code` mapping (ex: `ambiguous_skipped` ou le code du mapper)
Note : ce cas n'est PAS couvert par `eq_ids_supprimes` — nécessite une logique dédiée dans `_handle_action_sync`

### Partie C — Configuration et UI

**AC C.1 — Nouveaux champs de configuration**
Given l'utilisateur accède à la page de configuration du plugin
When il consulte la section "Filtrage & Publication"
Then il voit les champs : `excludedPlugins` (texte libre, CSV), `excludedObjects` (texte libre, CSV d'IDs numériques), `confidencePolicy` (select)
And chaque champ a un exemple de valeur visible (placeholder ou aide textuelle)
And la configuration est persistée via `config::byKey()` / `config::save()` (mécanisme standard Jeedom)

**AC C.2 — Bouton Appliquer et Rescanner**
Given l'utilisateur a modifié les champs de filtrage (`excludedPlugins`, `excludedObjects`, `confidencePolicy`)
When il clique sur "Appliquer et Rescanner"
Then les 3 champs de filtrage sont explicitement sauvegardés en base (via appel AJAX `saveFilteringConfig`) AVANT le rescan
And uniquement en cas de succès de la sauvegarde, l'appel AJAX `scanTopology` est déclenché
And si la sauvegarde échoue, un message d'erreur est affiché et le scan n'est PAS lancé
And le résultat du scan est affiché : succès (avec nombre d'équipements publiés), erreur partielle, ou échec
Note : le pattern `configKey` (sauvegarde Jeedom core) n'est PAS déclenché par ce bouton — la sauvegarde passe par `saveFilteringConfig`

### Partie D — Rescan et application

**AC D.1 — Application complète au rescan**
Given la configuration d'exclusion ou de politique de confiance a été modifiée
When l'utilisateur déclenche un rescan via le bouton ou via le diagnostic
Then le nouveau périmètre est appliqué intégralement
And les équipements désormais hors périmètre sont dépubliés (AC A.3 et B.2)
And les équipements nouvellement dans le périmètre sont publiés

---

## Tasks / Subtasks

- [x] Task 1 — PHP : Enrichissement `getFullTopology()` (AC: A, B)
  - [x] 1.1 Lire `excludedPlugins` (CSV `eq_type_name`) et `excludedObjects` (CSV IDs) depuis `config::byKey()`
  - [x] 1.2 Lire `confidencePolicy` depuis `config::byKey('confidencePolicy', __CLASS__, 'sure_probable')`
  - [x] 1.3 Pour chaque eqLogic, calculer `is_excluded` et `exclusion_source` selon la priorité : `eqlogic > plugin > object`
    - Si `$eq->getConfiguration('jeedom2ha_excluded', false)` → `exclusion_source = "eqlogic"`
    - Sinon si `eq_type_name` ∈ `$excludedPlugins` → `exclusion_source = "plugin"`
    - Sinon si `object_id` ∈ `$excludedObjects` → `exclusion_source = "object"`
    - Sinon → `is_excluded = false`, pas de `exclusion_source`
  - [x] 1.4 Ajouter `exclusion_source` dans chaque eqLogic du payload si `is_excluded=true`
  - [x] 1.5 Ajouter `sync_config.confidence_policy` au niveau racine du payload topology

- [x] Task 2 — Daemon Python : Modèle + éligibilité + politique + traçabilité (AC: A, B)
  - [x] 2.1 Ajouter `exclusion_source: Optional[str] = None` dans `JeedomEqLogic` (`models/topology.py`)
  - [x] 2.2 Lire `exclusion_source` dans `TopologySnapshot.from_jeedom_payload()` (lecture directe depuis `eq_raw`)
  - [x] 2.3 Modifier `assess_eligibility()` : produire `excluded_eqlogic` / `excluded_plugin` / `excluded_object` selon `eq.exclusion_source` (défaut `"eqlogic"` si absent)
  - [x] 2.4 Dans `_handle_action_sync` : extraire `sync_config.confidence_policy` du payload, valider (`"sure_only"` | `"sure_probable"`, défaut `"sure_probable"`), passer aux mappers
  - [x] 2.5 Modifier `decide_publication()` dans `light.py`, `cover.py`, `switch.py` : ajouter `confidence_policy: str = "sure_probable"` — si `"sure_only"`, copie locale de la policy avec `probable: False`
  - [x] 2.6 Ajouter `excluded_plugin` et `excluded_object` dans `_DIAGNOSTIC_MESSAGES` ET dans `_CLOSED_REASON_MAP` (`http_server.py`)
    - `_CLOSED_REASON_MAP`: `"excluded_plugin": "excluded"`, `"excluded_object": "excluded"`
    - `_DIAGNOSTIC_MESSAGES`: message + remédiation + `False` (non publiable)
  - [x] 2.7 Dans `_handle_action_sync` : détecter et dépublier les équipements éligibles mais bloqués par la policy (AC B.2)
    - Après le traitement de tous les eqLogics du sync courant, pour chaque `eq_id` dans `nouveaux_eq_ids` :
      - Si `previous_decision = publications.get(eq_id)` existe avec `should_publish=True`
      - Et `current_decision.should_publish=False`
      - → déclencher unpublish (même mécanique que `eq_ids_supprimes`)
  - [x] 2.8 Dans `_handle_system_diagnostics` : remplacer le check hardcodé `reason_code == "excluded_eqlogic"` par `reason_code in _EXCLUDED_REASON_CODES`
    - Définir constante locale : `_EXCLUDED_REASON_CODES = {"excluded_eqlogic", "excluded_plugin", "excluded_object"}`

- [x] Task 3 — PHP `configuration.php` + AJAX handler : Nouveaux champs (AC: C)
  - [x] 3.1 Ajouter un fieldset "Filtrage & Publication" avec les champs (pattern `configKey` standard Jeedom) :
    - `excludedPlugins` : `<input class="configKey form-control" data-l1key="excludedPlugins" placeholder="virtual,zwave"/>`
    - `excludedObjects` : `<input class="configKey form-control" data-l1key="excludedObjects" placeholder="1,5,12"/>`
    - `confidencePolicy` : `<select class="configKey form-control" data-l1key="confidencePolicy">` avec options `sure_probable` (défaut) et `sure_only`
    - Ajouter du texte d'aide visible sous chaque champ (exemple de valeur attendue)
  - [x] 3.2 Ajouter le handler PHP `saveFilteringConfig` dans `jeedom2ha.ajax.php` :
    - Accepte `excludedPlugins`, `excludedObjects`, `confidencePolicy` en POST
    - Valide `confidencePolicy` (doit être `"sure_only"` ou `"sure_probable"`, sinon force `"sure_probable"`)
    - Appelle `config::save()` pour chacune des 3 clés
    - Retourne `ajax::success(['saved' => true])`
    - Voir Dev Notes pour le code exact
  - [x] 3.3 Ajouter le bouton "Appliquer et Rescanner" avec JS inline chaîné : save → scan (voir Dev Notes)
  - [x] 3.4 Ne pas déplacer le JS dans `desktop/js/jeedom2ha.js` — ce fichier n'est pas chargé sur la vue configuration

- [x] Task 4 — Tests unitaires Python (AC: A, B) — fichier : `resources/daemon/tests/unit/test_exclusion_filtering.py`
  - [x] 4.1 `assess_eligibility()` : `excluded_eqlogic`, `excluded_plugin`, `excluded_object` — les 3 codes
  - [x] 4.2 `assess_eligibility()` priorité : équipement exclu avec source="eqlogic" → `reason_code == "excluded_eqlogic"`
  - [x] 4.3 `assess_eligibility()` sans `exclusion_source` → défaut `"excluded_eqlogic"` (rétro-compatibilité)
  - [x] 4.4 `decide_publication()` sur les 3 mappers : `sure_only` bloque `probable`, `sure_probable` le laisse passer
  - [x] 4.5 `decide_publication()` sans `confidence_policy` → défaut `sure_probable` → probable autorisé (non-régression)
  - [x] 4.6 Dépublication policy change (AC B.2) : équipement probable → was_published, now `sure_only` → unpublish déclenché
  - [x] 4.7 `_handle_system_diagnostics` : `excluded_plugin` et `excluded_object` → statut "Exclu" (même UI que `excluded_eqlogic`)
  - [x] 4.8 `_CLOSED_REASON_MAP` : `excluded_plugin` → `"excluded"`, `excluded_object` → `"excluded"`
  - [x] 4.9 Non-régression : exclusion individuelle `jeedom2ha_excluded` → `excluded_eqlogic` (comportement inchangé)
  - [x] 4.10 Non-régression : tous les tests existants (289+) passent toujours

- [x] Task 5 — Tests PHP / vérifications manuelles (AC: C.2) — à valider lors de la recette
  - [x] 5.1 `saveFilteringConfig` persiste les 3 clés : POST avec `excludedPlugins="virtual"`, `excludedObjects="1,2"`, `confidencePolicy="sure_only"` → `config::byKey('excludedPlugins')` retourne `"virtual"`, `config::byKey('confidencePolicy')` retourne `"sure_only"` après l'appel
  - [x] 5.2 `saveFilteringConfig` fallback sur `confidencePolicy` invalide : POST avec `confidencePolicy="bad_value"` → `config::byKey('confidencePolicy')` retourne `"sure_probable"`
  - [x] 5.3 Comportement bouton si sauvegarde échoue : simuler un échec de `saveFilteringConfig` → vérifier que `scanTopology` n'est PAS appelé et qu'un message d'erreur est affiché
  - [x] 5.4 Flux complet E2E : POST `saveFilteringConfig` (ok) → POST `scanTopology` → résultat cohérent avec les nouvelles exclusions en base

---

## Dev Notes

### Architecture des exclusions (approche PHP-first)

**Principe** : PHP calcule toutes les exclusions avant de construire le payload topologie. Le daemon reçoit des `is_excluded=true` pré-calculés avec un champ `exclusion_source` explicatif. Aucune config d'exclusion n'est passée séparément au daemon.

**Deux chemins de sauvegarde coexistent** — ne pas confondre :
- **Bouton "Sauvegarder" Jeedom (standard)** : Jeedom core collecte tous les champs `.configKey` et les sauvegarde. Ce chemin n'est PAS déclenché par le bouton "Appliquer et Rescanner".
- **Bouton "Appliquer et Rescanner" (custom)** : le JS appelle explicitement `saveFilteringConfig` pour sauvegarder les 3 clés de filtrage, PUIS `scanTopology`. Sans ce chaînage, le rescan lirait l'ancienne config en base.

**Flux complet (bouton "Appliquer et Rescanner")** :
1. JS lit les 3 champs du formulaire → POST `saveFilteringConfig` → `config::save()` pour `excludedPlugins`, `excludedObjects`, `confidencePolicy`
2. JS, uniquement si succès de l'étape 1 → POST `scanTopology` → `getFullTopology()` lit les configs persistées (les nouvelles valeurs sont maintenant en base)
3. `getFullTopology()` calcule `is_excluded` + `exclusion_source` (priorité eqlogic > plugin > object), ajoute `sync_config.confidence_policy`
4. `callDaemon('/action/sync', $topology, 'POST', 15)` → daemon reçoit le tout
5. `_handle_action_sync` extrait `sync_config.confidence_policy`, le passe à chaque `decide_publication()`
6. Équipements exclus : `assess_eligibility()` retourne `is_eligible=False` → pas ajoutés à `nouveaux_eq_ids` → unpublish via `eq_ids_supprimes` si précédemment publiés
7. Équipements éligibles mais bloqués par policy : ajoutés à `nouveaux_eq_ids` → logique dédiée Task 2.7 détecte et unpublish

### Fichiers à modifier

**PHP :**
- `core/class/jeedom2ha.class.php` — `getFullTopology()` uniquement
- `plugin_info/configuration.php` — nouveau fieldset + bouton + JS inline chaîné
- `core/ajax/jeedom2ha.ajax.php` — nouveau handler `saveFilteringConfig`

**Python (daemon) :**
- `models/topology.py` — `JeedomEqLogic` + `from_jeedom_payload()` + `assess_eligibility()`
- `mapping/light.py`, `mapping/cover.py`, `mapping/switch.py` — signature `decide_publication()`
- `transport/http_server.py` — `_handle_action_sync`, `_handle_system_diagnostics`, `_DIAGNOSTIC_MESSAGES`, `_CLOSED_REASON_MAP`

**Tests :**
- `resources/daemon/tests/unit/test_exclusion_filtering.py` (créer)
- Enrichir `test_diagnostic_endpoint.py` si les tests `_handle_system_diagnostics` y sont déjà

### Format du payload topology enrichi

```json
{
  "timestamp": "...",
  "objects": [...],
  "eq_logics": [
    {
      "id": 123,
      "name": "Prise Salon",
      "is_excluded": true,
      "exclusion_source": "plugin",
      "eq_type_name": "virtual",
      ...
    }
  ],
  "sync_config": {
    "confidence_policy": "sure_only"
  }
}
```

Si `is_excluded = false` : le champ `exclusion_source` est absent du payload (ne pas le transmettre du tout).

### Priorité d'exclusion PHP (getFullTopology)

```php
$excludedPlugins = array_filter(array_map('trim', explode(',', config::byKey('excludedPlugins', __CLASS__, ''))));
$excludedObjects = array_map('intval', array_filter(array_map('trim', explode(',', config::byKey('excludedObjects', __CLASS__, '')))));
$confidencePolicy = config::byKey('confidencePolicy', __CLASS__, 'sure_probable');
// Valider : autoriser uniquement "sure_only" ou "sure_probable"
if (!in_array($confidencePolicy, ['sure_only', 'sure_probable'])) {
    $confidencePolicy = 'sure_probable';
}

// Pour chaque eqLogic :
$isExcluded = false;
$exclusionSource = null;
if ($eq->getConfiguration('jeedom2ha_excluded', false)) {
    $isExcluded = true;
    $exclusionSource = 'eqlogic';  // Priorité 1 — individuel
} elseif (in_array($eq->getEqType_name(), $excludedPlugins)) {
    $isExcluded = true;
    $exclusionSource = 'plugin';   // Priorité 2 — plugin
} elseif (in_array((int)$eq->getObject_id(), $excludedObjects)) {
    $isExcluded = true;
    $exclusionSource = 'object';   // Priorité 3 — pièce
}

$eqData = [
    'id'          => (int)$eq->getId(),
    'is_excluded' => $isExcluded,
    // ... autres champs du payload existant ...
];
// N'ajouter exclusion_source que si is_excluded=true
// (ne pas utiliser l'opérateur spread PHP pour la compatibilité PHP < 8.1)
if ($isExcluded) {
    $eqData['exclusion_source'] = $exclusionSource;
}
```

### assess_eligibility() enrichie (topology.py)

```python
_EXCLUSION_SOURCE_TO_REASON = {
    "eqlogic": "excluded_eqlogic",
    "plugin":  "excluded_plugin",
    "object":  "excluded_object",
}

# Dans assess_eligibility() — priorité : Exclu > Désactivé > Sans cmds > Sans type
if eq.is_excluded:
    source = eq.exclusion_source or "eqlogic"  # défaut rétro-compatible
    reason_code = _EXCLUSION_SOURCE_TO_REASON.get(source, "excluded_eqlogic")
    return EligibilityResult(is_eligible=False, reason_code=reason_code, confidence="sure")
```

### decide_publication() — signature mise à jour (3 mappers)

```python
def decide_publication(self, mapping: MappingResult, confidence_policy: str = "sure_probable") -> PublicationDecision:
    policy = dict(LIGHT_PUBLICATION_POLICY)  # copie locale — ne jamais modifier la constante
    if confidence_policy == "sure_only":
        policy["probable"] = False
    should_publish = policy.get(mapping.confidence, False)
    ...
```

Même pattern pour `CoverMapper.decide_publication()` et `SwitchMapper.decide_publication()`.

Appels dans `_handle_action_sync` :
```python
decision = mapper.decide_publication(mapping, confidence_policy=confidence_policy)
```

### _handle_action_sync — extraction sync_config et dépublication policy-change

```python
# Extraction (après data = await request.json())
payload = data.get("payload", {})
sync_config = payload.get("sync_config", {})
confidence_policy = sync_config.get("confidence_policy", "sure_probable")
if confidence_policy not in ("sure_only", "sure_probable"):
    _LOGGER.warning("[SYNC] confidence_policy invalide '%s' → fallback sure_probable", confidence_policy)
    confidence_policy = "sure_probable"
```

```python
# Dépublication des équipements éligibles mais bloqués par policy (Task 2.7)
# À exécuter APRÈS la boucle principale sur les eqLogics, AVANT eq_ids_supprimes :
for eq_id in nouveaux_eq_ids:
    previous_decision = request.app["publications"].get(eq_id)
    current_decision = current_decisions.get(eq_id)  # stocker dans un dict pendant la boucle principale
    if (previous_decision is not None
            and _needs_discovery_unpublish(previous_decision)
            and current_decision is not None
            and not current_decision.should_publish):
        _LOGGER.info("[SYNC] eq_id=%d: policy change → dépublication (was=%s now=%s)",
                     eq_id, previous_decision.reason, current_decision.reason)
        # même mécanique que eq_ids_supprimes
        await publisher.unpublish_by_eq_id(eq_id, entity_type=current_decision.mapping_result.ha_entity_type)
        # Mettre à jour publications pour ne pas re-dépublier
        request.app["publications"][eq_id] = current_decision
```

Note implémentation : la boucle principale doit accumuler les `current_decisions` dans un dict `{eq_id: decision}` pour que ce bloc puisse les lire. À affiner par le dev si la structure interne diffère.

### _handle_system_diagnostics — extension du check exclu (Task 2.8)

```python
# Constante à définir près de _CLOSED_REASON_MAP :
_EXCLUDED_REASON_CODES = frozenset({"excluded_eqlogic", "excluded_plugin", "excluded_object"})

# Dans _handle_system_diagnostics, remplacer :
# if el_result.reason_code == "excluded_eqlogic":  ← HARDCODÉ
# Par :
if el_result.reason_code in _EXCLUDED_REASON_CODES:
    status = "Exclu"
    ...
```

### _CLOSED_REASON_MAP — entrées manquantes à ajouter

```python
_CLOSED_REASON_MAP = {
    # ... entrées existantes inchangées ...
    "excluded_eqlogic": "excluded",     # existant
    "excluded_plugin":  "excluded",     # NOUVEAU
    "excluded_object":  "excluded",     # NOUVEAU
    ...
}
```

### _DIAGNOSTIC_MESSAGES — entrées à ajouter

```python
"excluded_plugin": (
    "Cet équipement est exclu car son plugin source figure dans la liste d'exclusions.",
    "Pour le publier, retirez son plugin de la liste d'exclusions dans la configuration.",
    False,
),
"excluded_object": (
    "Cet équipement est exclu car sa pièce/objet figure dans la liste d'exclusions.",
    "Pour le publier, retirez sa pièce de la liste d'exclusions dans la configuration.",
    False,
),
```

### configuration.php — UX champs exclusion

Les champs utilisent le pattern `configKey` Jeedom (sauvegardés par le bouton "Sauvegarder" standard de la page de configuration). Le bouton "Appliquer et Rescanner" passe par `saveFilteringConfig` — voir section JS ci-dessous.

```html
<fieldset>
  <legend>{{Filtrage & Publication}}</legend>

  <div class="form-group">
    <label class="col-sm-3 control-label">{{Plugins exclus}}</label>
    <div class="col-sm-9">
      <input class="configKey form-control" data-l1key="excludedPlugins"
             placeholder="virtual,zwave,rfxcom"/>
      <span class="help-block">{{Noms de plugins séparés par des virgules (eq_type_name). Laisser vide = aucune exclusion.}}</span>
    </div>
  </div>

  <div class="form-group">
    <label class="col-sm-3 control-label">{{Pièces exclues}}</label>
    <div class="col-sm-9">
      <input class="configKey form-control" data-l1key="excludedObjects"
             placeholder="1,5,12"/>
      <span class="help-block">{{IDs d'objets Jeedom séparés par des virgules. Laisser vide = aucune exclusion.}}</span>
    </div>
  </div>

  <div class="form-group">
    <label class="col-sm-3 control-label">{{Politique de publication}}</label>
    <div class="col-sm-9">
      <select class="configKey form-control" data-l1key="confidencePolicy">
        <option value="sure_probable">{{Publier les équipements sûrs et probables (recommandé)}}</option>
        <option value="sure_only">{{Publier uniquement les équipements sûrs}}</option>
      </select>
    </div>
  </div>

  <div class="form-group">
    <div class="col-sm-offset-3 col-sm-9">
      <button id="bt_applyAndRescan" class="btn btn-primary">
        <i class="fas fa-sync"></i> {{Appliquer et Rescanner}}
      </button>
      <span id="span_rescanResult" style="display:none; margin-left:10px;"></span>
    </div>
  </div>
</fieldset>
```

### Handler PHP `saveFilteringConfig` à ajouter dans `jeedom2ha.ajax.php`

À insérer dans le bloc `if/else if`, AVANT le bloc `else` final (après le bloc `scanTopology`) :

```php
else if ($action == 'saveFilteringConfig') {
    $excludedPlugins  = init('excludedPlugins', '');
    $excludedObjects  = init('excludedObjects', '');
    $confidencePolicy = init('confidencePolicy', 'sure_probable');
    // Validation : valeurs autorisées uniquement
    if (!in_array($confidencePolicy, ['sure_only', 'sure_probable'])) {
        $confidencePolicy = 'sure_probable';
    }
    config::save('excludedPlugins',  $excludedPlugins,  'jeedom2ha');
    config::save('excludedObjects',  $excludedObjects,  'jeedom2ha');
    config::save('confidencePolicy', $confidencePolicy, 'jeedom2ha');
    log::add('jeedom2ha', 'info', '[CONFIG] saveFilteringConfig: excludedPlugins="'
        . $excludedPlugins . '" excludedObjects="' . $excludedObjects
        . '" confidencePolicy="' . $confidencePolicy . '"');
    ajax::success(['saved' => true]);
}
```

Note : `scanTopology` existe déjà dans `jeedom2ha.ajax.php` — aucune modification de ce handler n'est nécessaire.

### configuration.php — JS inline bouton "Appliquer et Rescanner" (flux chaîné save → scan)

**Pourquoi ce chaînage est nécessaire** : `scanTopology` appelle `getFullTopology()` qui lit depuis `config::byKey()` (DB). Le pattern `configKey` (sauvegarde Jeedom core) n'est déclenché QUE par le bouton "Sauvegarder" injecté par Jeedom dans l'en-tête — pas par un bouton custom. Sans la sauvegarde explicite préalable, le rescan utilise l'ANCIENNE config en base et ne "applique" rien.

```javascript
$('#bt_applyAndRescan').on('click', function() {
  var $btn = $(this);
  var $status = $('#span_rescanResult');
  $btn.prop('disabled', true);
  $status.removeClass('label-success label-danger label-warning')
         .addClass('label').text('{{Sauvegarde en cours...}}').show();

  // Étape 1 : sauvegarder les champs de filtrage explicitement
  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {
      action:           'saveFilteringConfig',
      excludedPlugins:  $('.configKey[data-l1key=excludedPlugins]').val(),
      excludedObjects:  $('.configKey[data-l1key=excludedObjects]').val(),
      confidencePolicy: $('.configKey[data-l1key=confidencePolicy]').val()
    },
    dataType: 'json',
    timeout: 10000,
    success: function(saveData) {
      if (saveData.state !== 'ok') {
        $btn.prop('disabled', false);
        $status.addClass('label-danger')
               .text(saveData.result || '{{Erreur lors de la sauvegarde}}');
        return;
      }
      // Étape 2 : lancer le rescan avec la config fraîchement sauvegardée
      $status.text('{{Rescan en cours...}}');
      $.ajax({
        type: 'POST',
        url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
        data: {action: 'scanTopology'},
        dataType: 'json',
        timeout: 20000,
        success: function(scanData) {
          $btn.prop('disabled', false);
          if (scanData.state !== 'ok') {
            $status.addClass('label-danger')
                   .text(scanData.result || '{{Erreur lors du rescan}}');
            return;
          }
          var r = scanData.result || {};
          var summary = (r.payload && r.payload.mapping_summary) ? r.payload.mapping_summary : {};
          var published = (summary.lights_published || 0)
                        + (summary.covers_published || 0)
                        + (summary.switches_published || 0);
          $status.addClass('label-success')
                 .text('{{Appliqué & Rescan terminé}} — ' + published + ' {{équipement(s) publié(s)}}');
        },
        error: function() {
          $btn.prop('disabled', false);
          $status.addClass('label-danger').text('{{Erreur de communication lors du rescan}}');
        }
      });
    },
    error: function() {
      $btn.prop('disabled', false);
      $status.addClass('label-danger').text('{{Erreur de communication lors de la sauvegarde}}');
    }
  });
});
```

### Guardrails (Non-régression)

- Le bouton "Appliquer et Rescanner" doit appeler `saveFilteringConfig` AVANT `scanTopology`. Ne jamais appeler `scanTopology` directement depuis le bouton sans sauvegarde préalable — le rescan lirait l'ancienne config.
- `saveFilteringConfig` ne doit sauvegarder QUE les 3 clés de filtrage (`excludedPlugins`, `excludedObjects`, `confidencePolicy`). Ne pas modifier les clés MQTT ou autres.
- La sauvegarde via le bouton "Sauvegarder" Jeedom core (pattern `configKey`) reste fonctionnelle et indépendante — les deux mécanismes coexistent sans conflit.
- Ne pas modifier le comportement de l'exclusion individuelle `jeedom2ha_excluded` — elle reste Priorité 1.
- Le champ `exclusion_source` est **optionnel** dans le payload — si absent, le daemon utilise `"eqlogic"` par défaut (rétro-compatibilité des anciens payloads).
- La signature `decide_publication(mapping)` sans `confidence_policy` DOIT rester valide (défaut `"sure_probable"`) pour ne pas casser les 289+ tests existants.
- `LIGHT_PUBLICATION_POLICY` / `COVER_PUBLICATION_POLICY` / `SWITCH_PUBLICATION_POLICY` : constantes module — ne jamais les modifier, toujours surcharger via copie locale dans `decide_publication()`.
- `_build_traceability()` : aucune modification nécessaire — les nouveaux codes tombent dans le bucket "excluded" via `_CLOSED_REASON_MAP`.
- Ne pas toucher aux badges UI de diagnostic 4.1/4.2/4.2bis.
- Ne pas déplacer le JS de `configuration.php` vers `desktop/js/jeedom2ha.js` (ce fichier n'est pas chargé sur la vue configuration).
- CSS `!important` sur les lignes de détail accordéon diagnostic — à respecter si de nouvelles lignes sont ajoutées dans la modale.

### Structure des tests

#### Tests unitaires Python — `resources/daemon/tests/unit/test_exclusion_filtering.py`

```python
# ── assess_eligibility : les 3 reason_codes ──────────────────────────────────

def test_assess_eligibility_excluded_eqlogic():
    eq = JeedomEqLogic(id=1, name="Test", is_excluded=True, exclusion_source="eqlogic", cmds=[...])
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"
    assert not result.is_eligible

def test_assess_eligibility_excluded_plugin():
    eq = JeedomEqLogic(id=2, name="Test", is_excluded=True, exclusion_source="plugin", cmds=[...])
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_plugin"
    assert not result.is_eligible

def test_assess_eligibility_excluded_object():
    eq = JeedomEqLogic(id=3, name="Test", is_excluded=True, exclusion_source="object", cmds=[...])
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_object"
    assert not result.is_eligible

def test_assess_eligibility_no_source_defaults_to_eqlogic():
    # Rétro-compatibilité : exclusion_source absent → "excluded_eqlogic"
    eq = JeedomEqLogic(id=4, name="Test", is_excluded=True, exclusion_source=None, cmds=[...])
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"

# ── Priorité d'exclusion ─────────────────────────────────────────────────────

def test_exclusion_priority_eqlogic_wins_over_plugin():
    # Si is_excluded=True avec source="eqlogic", même si le plugin serait aussi exclu
    eq = JeedomEqLogic(id=5, name="Test", is_excluded=True, exclusion_source="eqlogic", cmds=[...])
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"  # eqlogic > plugin

# ── decide_publication : politique de confiance ───────────────────────────────

def test_decide_publication_sure_only_blocks_probable():
    for MapperClass in [LightMapper, CoverMapper, SwitchMapper]:
        mapper = MapperClass()
        mapping = MappingResult(confidence="probable", ...)
        decision = mapper.decide_publication(mapping, confidence_policy="sure_only")
        assert not decision.should_publish

def test_decide_publication_sure_probable_allows_probable():
    for MapperClass in [LightMapper, CoverMapper, SwitchMapper]:
        mapper = MapperClass()
        mapping = MappingResult(confidence="probable", ...)
        decision = mapper.decide_publication(mapping, confidence_policy="sure_probable")
        assert decision.should_publish

def test_decide_publication_default_policy_allows_probable():
    # Appel sans confidence_policy → défaut sure_probable → probable autorisé
    mapper = LightMapper()
    mapping = MappingResult(confidence="probable", ...)
    decision = mapper.decide_publication(mapping)
    assert decision.should_publish

def test_decide_publication_sure_only_still_allows_sure():
    mapper = LightMapper()
    mapping = MappingResult(confidence="sure", ...)
    decision = mapper.decide_publication(mapping, confidence_policy="sure_only")
    assert decision.should_publish

# ── Dépublication sur changement de policy (AC B.2) ──────────────────────────

def test_policy_change_probable_to_sure_only_triggers_unpublish():
    # Cas : équipement était published (probable), now sure_only → doit être unpublié
    # Test via _handle_action_sync ou via la logique d'unpublish dédiée
    # Vérifier que unpublish_by_eq_id est appelé pour cet eq_id
    ...

# ── _handle_system_diagnostics : statut "Exclu" pour les 3 codes ─────────────

def test_diagnostic_excluded_plugin_shows_exclu_status():
    # Simuler un EligibilityResult avec reason_code="excluded_plugin"
    # Vérifier que la réponse diagnostic contient status="Exclu" pour cet eq
    ...

def test_diagnostic_excluded_object_shows_exclu_status():
    # Même vérification pour excluded_object
    ...

# ── _CLOSED_REASON_MAP ────────────────────────────────────────────────────────

def test_closed_reason_map_excluded_plugin():
    from transport.http_server import _CLOSED_REASON_MAP
    assert _CLOSED_REASON_MAP["excluded_plugin"] == "excluded"

def test_closed_reason_map_excluded_object():
    from transport.http_server import _CLOSED_REASON_MAP
    assert _CLOSED_REASON_MAP["excluded_object"] == "excluded"

# ── Non-régression ────────────────────────────────────────────────────────────

def test_non_regression_individual_exclusion_unchanged():
    # jeedom2ha_excluded (individuel) → excluded_eqlogic, inchangé
    eq = JeedomEqLogic(id=99, name="Test", is_excluded=True, exclusion_source="eqlogic", cmds=[...])
    result = assess_eligibility(eq)
    assert result.reason_code == "excluded_eqlogic"

```

#### Tests PHP / recette manuelle — vérifications du handler `saveFilteringConfig` (Task 5)

Ces tests ne sont pas automatisés en Python — ils couvrent le handler PHP et le chaînage JS. À valider manuellement lors de la recette ou via un framework de test PHP si disponible.

**5.1 — Persistance des 3 clés**
```
Prérequis : démon démarré, plugin configuré
Action    : POST jeedom2ha.ajax.php {action: "saveFilteringConfig", excludedPlugins: "virtual", excludedObjects: "1,2", confidencePolicy: "sure_only"}
Attendu   : réponse {state: "ok", result: {saved: true}}
           config::byKey('excludedPlugins', 'jeedom2ha') == "virtual"
           config::byKey('excludedObjects', 'jeedom2ha') == "1,2"
           config::byKey('confidencePolicy', 'jeedom2ha') == "sure_only"
```

**5.2 — Fallback sur `confidencePolicy` invalide**
```
Action    : POST {action: "saveFilteringConfig", confidencePolicy: "n_importe_quoi"}
Attendu   : config::byKey('confidencePolicy', 'jeedom2ha') == "sure_probable"  // valeur fallback
```

**5.3 — Pas de scan si sauvegarde échoue**
```
Contexte : simuler un échec HTTP (timeout ou 500) sur saveFilteringConfig
Attendu  : le bouton affiche le message d'erreur de sauvegarde
           scanTopology n'est pas appelé (vérifiable dans les logs daemon)
```

**5.4 — Flux complet E2E**
```
Action   : modifier excludedPlugins dans l'UI → cliquer "Appliquer et Rescanner"
Attendu  : 1. message "Sauvegarde en cours..." affiché
           2. message "Rescan en cours..." affiché
           3. message "Appliqué & Rescan terminé — N équipement(s) publié(s)" affiché
           4. les équipements du plugin exclu ne sont plus visibles dans le diagnostic HA
```

### Context technique rappel

- `scanTopology` dans `jeedom2ha.ajax.php` : EXISTE — appelle `getFullTopology()` + `/action/sync` → ne pas recréer
- `is_excluded` dans `JeedomEqLogic` : EXISTE — seul `exclusion_source` est nouveau
- `_handle_action_sync` : `payload = data.get("payload", {})` puis `TopologySnapshot.from_jeedom_payload(payload)` — `sync_config` est à lire AVANT de passer le payload à `from_jeedom_payload()`
- Config Jeedom : `config::byKey('key', __CLASS__, 'default')` pour la lecture ; les 3 clés de filtrage sont sauvegardées via `saveFilteringConfig` (bouton custom) ou via le bouton "Sauvegarder" Jeedom (pattern `configKey`) — les deux mécanismes sont indépendants
- Taxonomie 4.2bis : les nouveaux codes `excluded_plugin`/`excluded_object` entrent dans le bucket `"excluded"` via `_CLOSED_REASON_MAP` — `_build_traceability()` n'a pas à être modifié

### References

- `models/topology.py` : `JeedomEqLogic`, `assess_eligibility()`, `EligibilityResult`
- `transport/http_server.py` : `_handle_action_sync`, `_handle_system_diagnostics`, `_DIAGNOSTIC_MESSAGES`, `_CLOSED_REASON_MAP`
- `mapping/light.py` : `LIGHT_PUBLICATION_POLICY`, `LightMapper.decide_publication()`
- `mapping/cover.py` : `COVER_PUBLICATION_POLICY`, `CoverMapper.decide_publication()`
- `mapping/switch.py` : `SWITCH_PUBLICATION_POLICY`, `SwitchMapper.decide_publication()`
- `core/class/jeedom2ha.class.php` : `getFullTopology()`, `callDaemon()`, `config::byKey()`
- `plugin_info/configuration.php` : patterns HTML/JS existants (fieldset, configKey, ajax inline)
- `core/ajax/jeedom2ha.ajax.php` : action `scanTopology` (existante, inchangée) + nouveau handler `saveFilteringConfig`
- `_bmad-output/implementation-artifacts/4-2-bis-homogeneite-de-tracabilite-et-explicabilite-diagnostique.md` : `_CLOSED_REASON_MAP`, `_build_traceability()`, taxonomie AC2, 289 tests baseline

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- AC B.2 (policy-change unpublish) — test initial utilisait `LIGHT_ON+LIGHT_OFF+LIGHT_STATE` → confiance `"sure"`, jamais bloqué par `sure_only`. Corrigé en utilisant `LIGHT_STATE+LIGHT_ON` (sans LIGHT_OFF) → confiance `"probable"` → unpublish déclenché correctement.

### Completion Notes List

- Tous les 75 tests passent (42 baseline + 33 nouveaux dans `test_exclusion_filtering.py`).
- AC B.2 (GAP CRITIQUE) implémenté : boucle dédiée après sync principal pour dépublier les équipements éligibles mais bloqués par changement `sure_probable → sure_only`.
- `_EXCLUDED_REASON_CODES` (frozenset) remplace le check hardcodé `== "excluded_eqlogic"` dans `_handle_system_diagnostics`.
- Handler `saveFilteringConfig` PHP chaîne save → scan de façon séquentielle et sûre. JS inline dans `configuration.php` (pas dans `desktop/js/`).
- Compatibilité ascendante préservée : `decide_publication(mapping)` sans `confidence_policy` continue de fonctionner avec défaut `"sure_probable"`.
- Constantes module (`LIGHT_PUBLICATION_POLICY`, etc.) non modifiées — surcharge uniquement via copie locale dans chaque appel.
- Task 5 (recette PHP) documentée en Dev Notes — pas d'infra de test PHP automatisée disponible dans ce projet.
- [Review fix H1] Ajout `_DIAGNOSTIC_MESSAGES["probable_skipped"]` — diagnostic explicite quand `sure_only` bloque un `probable`.
- [Review fix H2] Ajout `_CLOSED_REASON_MAP["probable_skipped"] = "confidence_policy_skipped"` — nouveau code fermé de traçabilité. Arbitrage : `ambiguous_skipped` serait sémantiquement faux (l'équipement n'est pas ambigu), et aucun consumer downstream ne filtre sur `decision_trace.reason_code` → un code dédié est viable et plus fidèle.
- [Review fix L1] Suppression fixture `app_with_publications` non utilisée dans les tests.
- [Review fix L3] Ajout filtre `is_numeric` sur `$excludedObjectsRaw` dans `getFullTopology()` — évite qu'une saisie non numérique produise un `intval(0)` parasite.

### File List

- `core/class/jeedom2ha.class.php` — `getFullTopology()` : exclusions multicritères + `sync_config`
- `core/ajax/jeedom2ha.ajax.php` — nouveau handler `saveFilteringConfig`
- `plugin_info/configuration.php` — fieldset "Filtrage & Publication" + bouton + JS inline
- `resources/daemon/models/topology.py` — `JeedomEqLogic.exclusion_source`, `from_jeedom_payload()`, `assess_eligibility()`
- `resources/daemon/mapping/light.py` — `LightMapper.decide_publication()` : paramètre `confidence_policy`
- `resources/daemon/mapping/cover.py` — `CoverMapper.decide_publication()` : paramètre `confidence_policy`
- `resources/daemon/mapping/switch.py` — `SwitchMapper.decide_publication()` : paramètre `confidence_policy`
- `resources/daemon/transport/http_server.py` — `_EXCLUDED_REASON_CODES`, `_CLOSED_REASON_MAP`, `_DIAGNOSTIC_MESSAGES`, `_handle_action_sync`, `_handle_system_diagnostics`
- `resources/daemon/tests/unit/test_exclusion_filtering.py` — NOUVEAU (33 tests)

### Change Log

| Date | Change |
|------|--------|
| 2026-03-19 | Story 4.3 implémentée — exclusions multicritères, politique de confiance, bouton Appliquer & Rescanner, AC B.2 dépublication, 30 tests |
| 2026-03-19 | Review fixes (H1/H2/M1/L1/L3) — diagnostic `probable_skipped`, taxonomie `confidence_policy_skipped`, chiffres de tests corrigés, nettoyage code mort, hardening `excludedObjects` |
