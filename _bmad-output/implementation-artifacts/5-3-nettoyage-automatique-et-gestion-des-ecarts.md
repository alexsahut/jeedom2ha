# Story 5.3: Nettoyage Automatique et Gestion des Écarts

Status: review

## Story

As a utilisateur Jeedom,
I want que les équipements supprimés dans Jeedom disparaissent de HA,
so that j'évite l'accumulation d'entités fantômes.

## Hypothèses de Plateforme

| Hypothèse | Valeur vérifiée (post-5.2) | Impact pour 5.3 |
|-----------|---------------------------|-----------------|
| H1 — Unpublish discovery existant | `publisher.unpublish_by_eq_id(eq_id, entity_type)` publie payload vide retained sur `homeassistant/{type}/jeedom2ha_{eq_id}/config` — mécanisme opérationnel depuis 4.3 | 5.3 réutilise tel quel, aucun changement |
| H2 — Set difference existant | `eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids` détecte les suppressions/inéligibilités — opérationnel depuis 4.3, étendu en 5.1 pour le boot cache | 5.3 réutilise tel quel, aucun changement |
| H3 — Deferred unpublish existant | `pending_discovery_unpublish` + `pending_local_availability_cleanup` en RAM — replay à chaque sync et reconnexion broker | 5.3 réutilise tel quel |
| H4 — Availability cleanup conditionnel | `_clear_local_availability_topic()` existe mais n'est appelée que si `local_availability_supported=True` dans la purge standard, et **jamais** dans le chemin boot cache | 5.3 doit rendre ce cleanup **inconditionnel** et l'ajouter au chemin boot cache |
| H5 — Log cleanup non-discriminant | Le message actuel (`"eq_id=%d est devenu inéligible ou supprimé"`) ne distingue pas la raison : suppression DB, désactivation, exclusion, perte de type générique | 5.3 doit classifier la raison via le dict `eligibility` |
| H6 — Eligibility accessible dans la purge | `eligibility: Dict[int, EligibilityResult]` est calculé dans `_handle_action_sync()` et reste en scope au moment de la purge (ligne 977+) | 5.3 peut checker `eligibility.get(old_eq_id)` pour distinguer supprimé (absent du dict) vs inéligible (présent avec reason_code) |
| H7 — Payload vide retained = suppression HA | Un publish de payload vide avec `retain=True` sur un topic discovery fait disparaître l'entité dans HA (spec MQTT Discovery) | Pas de changement — déjà validé terrain |
| H8 — Limitation V1 : orphelins retained | Les topics retained publiés par une ancienne version du plugin et dont le plugin a perdu la trace ne sont PAS nettoyés proactivement | 5.3 documente la limitation + workaround `--stop-daemon-cleanup` |
| H9 — Limitation V1 : un eq_id = une entité HA | Le plugin produit une seule entité HA par eq_id Jeedom. Les multi-entity par eq_id sont hors scope V1 | 5.3 documente la limitation |

## Acceptance Criteria

### Groupe 1 — Suppression d'équipement (INV-3)

1. **Given** un équipement est publié dans HA (discovery retained + availability published) **When** l'utilisateur le supprime dans Jeedom (suppression DB) et déclenche un rescan (`/action/sync`) **Then** le daemon :
   - Détecte la suppression via `eq_ids_supprimes` (set difference)
   - Publie un payload vide retained sur `homeassistant/{type}/jeedom2ha_{eq_id}/config` (suppression discovery HA)
   - Publie un payload vide retained sur `jeedom2ha/{eq_id}/availability` (nettoyage availability locale)
   - Retire l'entrée de `app["mappings"]` et `app["publications"]` (synchronisation cache RAM)
   - Logue `INFO [CLEANUP] eq_id=%d: supprimé dans Jeedom → discovery unpublish + availability cleanup`

2. **Given** le daemon est arrêté **When** un équipement publié est supprimé dans Jeedom, puis le daemon redémarre **Then** au premier sync post-boot :
   - Le boot cache contient l'entrée `{eq_id, entity_type, published=True}`
   - Le `eq_id` est absent de la topologie Jeedom courante → dans `eq_ids_supprimes`
   - Le daemon unpublish le discovery via boot cache entity_type
   - Le daemon cleanup l'availability topic `jeedom2ha/{eq_id}/availability`
   - Logue `INFO [CLEANUP] eq_id=%d: supprimé depuis downtime daemon → discovery unpublish + availability cleanup (boot_cache)`

3. **Given** un unpublish de suppression échoue (broker indisponible) **When** le broker redevient disponible au sync suivant **Then** le `pending_discovery_unpublish` est rejoué et l'unpublish aboutit (INV-8)

### Groupe 2 — Désactivation et réactivation (INV-11)

4. **Given** un équipement publié dans HA **When** l'utilisateur le désactive dans Jeedom (`is_enable=false`) et déclenche un rescan **Then** le daemon :
   - L'équipement est présent dans `eligibility` avec `reason_code="disabled_eqlogic"` et `is_eligible=False`
   - L'équipement tombe dans `eq_ids_supprimes` (plus dans `nouveaux_eq_ids`)
   - Unpublish discovery + cleanup availability
   - Logue `INFO [CLEANUP] eq_id=%d: désactivé dans Jeedom (disabled_eqlogic) → discovery unpublish + availability cleanup`
   - Le diagnostic affiche l'équipement avec statut "Non publié" et raison "Cet équipement est désactivé dans Jeedom"

5. **Given** un équipement désactivé (non publié) **When** l'utilisateur le réactive (`is_enable=true`) et déclenche un rescan **Then** l'équipement redevient éligible, est remappé et republié dans HA (discovery + availability + état courant)

### Groupe 3 — Distinction supprimé vs indisponible

6. **Given** un équipement publié dont le module physique est injoignable (ex: module Z-Wave déconnecté) **When** Jeedom signale cette indisponibilité **Then** le daemon :
   - NE supprime PAS le discovery (l'entité reste dans HA)
   - Met à jour l'availability locale : `jeedom2ha/{eq_id}/availability` → `"offline"`
   - L'entité apparaît comme `unavailable` dans HA mais reste présente

7. **Given** le même équipement indisponible (module physique) **When** l'utilisateur le **désactive** (`is_enable=false`) dans Jeedom et déclenche un rescan **Then** le daemon unpublish le discovery (l'entité disparaît de HA) — comportement différent de l'indisponibilité physique

### Groupe 4 — Cleanup availability inconditionnel

8. **Given** un équipement dans `eq_ids_supprimes` (supprimé ou devenu inéligible) **When** le cleanup est déclenché **Then** le nettoyage de `jeedom2ha/{eq_id}/availability` est effectué **inconditionnellement** (pas conditionné par `local_availability_supported`) — car l'équipement est définitivement retiré et tout retained résiduel doit être nettoyé

9. **Given** un équipement présent dans le boot cache mais absent de la topologie au premier sync post-boot **When** le discovery est unpublié depuis le boot cache **Then** l'availability locale est AUSSI nettoyée (actuellement ce chemin ne nettoie pas l'availability)

### Groupe 5 — Logging explicite avec classification des raisons

10. **Given** un équipement est dans `eq_ids_supprimes` **When** le daemon exécute le cleanup **Then** le message de log distingue la raison spécifique :
    - Si `eq_id` absent de `eligibility` → `"supprimé dans Jeedom"`
    - Si `eligibility[eq_id].reason_code == "disabled_eqlogic"` → `"désactivé dans Jeedom"`
    - Si `eligibility[eq_id].reason_code` starts with `"excluded_"` → `"exclu ({source})"`
    - Sinon → `"devenu inéligible ({reason_code})"`

### Groupe 6 — Limitations documentées V1

11. **Given** un topic discovery retained orphelin existe sur le broker (publié par une ancienne version du plugin ou après purge du cache) **When** un rescan est déclenché **Then** le plugin NE nettoie PAS proactivement ce topic — limitation V1 documentée, workaround : `deploy-to-box.sh --stop-daemon-cleanup` ou suppression manuelle via MQTT

12. **Given** un `eq_id` Jeedom **When** il est mappé **Then** un seul `entity_type` est produit par `eq_id` (une seule entité HA par équipement Jeedom) — limitation V1

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
  - [x] Avant clôture, rejouer le mini preflight terrain projet pour les flux sync/runtime daemon depuis `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md` sur la box de validation : `GET /system/status` (401 sans header, JSON `status=ok` avec `X-Local-Secret`) puis `POST /action/sync` (HTTP 200, payload de synthèse présent, aucun 401)

- [x] Task 1 — Availability cleanup hardening (AC: #1, #2, #8, #9)
  - [x] 1.1 Dans la purge `eq_ids_supprimes` standard (http_server.py ~L1033-1057) : rendre le cleanup availability **inconditionnel** — retirer la garde `if bool(getattr(old_decision, "local_availability_supported", False))`. Remplacer par un appel systématique à `_clear_local_availability_topic(mqtt_bridge, old_eq_id, build_local_availability_topic(old_eq_id))` pour tout `old_eq_id` dans `eq_ids_supprimes` qui est effectivement unpublié
  - [x] 1.2 Dans le chemin boot cache (http_server.py ~L985-1011) : ajouter le cleanup availability après l'unpublish discovery. Appeler `_clear_local_availability_topic(mqtt_bridge, old_eq_id, build_local_availability_topic(old_eq_id))` (avec defer si broker indisponible)
  - [x] 1.3 Importer `build_local_availability_topic` depuis `models.availability` si pas déjà importé dans http_server.py
  - [x] 1.4 Tests unitaires :
    - Suppression standard → `_clear_local_availability_topic` appelé même si `local_availability_supported=False`
    - Suppression boot cache → `_clear_local_availability_topic` appelé après unpublish discovery
    - Broker indisponible → defer local availability cleanup

- [x] Task 2 — Logging enrichi avec classification des raisons (AC: #10, #1, #4)
  - [x] 2.1 Dans la purge `eq_ids_supprimes` (http_server.py ~L978-1061), avant chaque unpublish (standard et boot cache), déterminer la raison de suppression :
    ```python
    elig_entry = eligibility.get(old_eq_id)
    if elig_entry is None:
        cleanup_reason = "supprimé dans Jeedom"
    elif elig_entry.reason_code == "disabled_eqlogic":
        cleanup_reason = "désactivé dans Jeedom (disabled_eqlogic)"
    elif elig_entry.reason_code.startswith("excluded_"):
        cleanup_reason = f"exclu ({elig_entry.reason_code})"
    else:
        cleanup_reason = f"devenu inéligible ({elig_entry.reason_code})"
    ```
  - [x] 2.2 Remplacer le tag `[MAPPING]` par `[CLEANUP]` dans les logs de la purge pour cohérence avec la story 5.3. Le message devient : `"[CLEANUP] eq_id=%d: %s → discovery unpublish + availability cleanup"` (ou `"→ discovery unpublish effectif"` / `"→ deferred"` selon le cas)
  - [x] 2.3 Même enrichissement pour le chemin boot cache : `"[CLEANUP] eq_id=%d: %s (boot_cache, entity_type=%s)"`
  - [x] 2.4 Tests unitaires :
    - Suppression DB → log contient `"supprimé dans Jeedom"`
    - Désactivation → log contient `"désactivé dans Jeedom"`
    - Exclusion → log contient `"exclu (excluded_eqlogic)"`
    - Perte de generic_type → log contient `"devenu inéligible (no_supported_generic_type)"`

- [x] Task 3 — Tests de cycle complet (AC: #3, #4, #5, #6, #7)
  - [x] 3.1 Test intégration : suppression → unpublish → cache vidé → equipment absent du diagnostic
  - [x] 3.2 Test intégration : désactivation → unpublish → réactivation → republish (cycle complet)
  - [x] 3.3 Test unitaire : deferred unpublish replayed au sync suivant (INV-8)
  - [x] 3.4 Test unitaire : indisponible physique → availability "offline" mais discovery inchangé (AC #6)
  - [x] 3.5 Test unitaire : désactivé → discovery supprimé (comportement différent de l'indisponibilité, AC #7)

- [x] Task 4 — Tests terrain (non négociables) (AC: Runbook)
  - [x] 4.1 TC-1 (Suppression) — PASS terrain (eq_id=355)
  - [x] 4.2 TC-2 (Suppression pendant daemon arrêté) — PASS terrain (eq_id=616, chemin boot_cache)
  - [x] 4.3 TC-3 (Désactivation is_enable=false) — PASS terrain (eq_id=617, cycle désactivation/réactivation)
  - [x] 4.4 TC-4 (Distinction indisponible vs désactivé) — DEROGATION documentée: indisponibilité physique non reproductible sur le parc de validation, bypass explicitement demandé par le porteur (2026-03-22)

## Dev Notes

### Tableau de bord du code existant — ce qui change dans 5.3

| Aspect | Comportement post-5.2 | Ce que 5.3 ajoute / modifie |
|--------|----------------------|----------------------------|
| Suppression discovery | ✅ Fonctionnel — unpublish payload vide retained | Aucun changement |
| Suppression boot cache | ✅ Fonctionnel — unpublish depuis boot_cache entity_type | Ajoute le cleanup availability (manquant) |
| Availability cleanup standard | ⚠️ Conditionnel sur `local_availability_supported` | Rendu inconditionnel pour `eq_ids_supprimes` |
| Log cleanup | ⚠️ `"inéligible ou supprimé"` — non-discriminant | Classifié par raison : supprimé / désactivé / exclu / inéligible |
| Deferred unpublish | ✅ Fonctionnel | Aucun changement |
| Diagnostic disabled | ✅ Fonctionnel — "Non publié" + "Désactivé dans Jeedom" | Aucun changement |
| Retypage | ✅ Fonctionnel (Story 5.2) | Aucun changement — retypage géré par `_detect_lifecycle_changes` |
| Set difference | ✅ Fonctionnel — `anciens_eq_ids - nouveaux_eq_ids` | Aucun changement |
| RAM cleanup | ✅ Fonctionnel — `pop` de mappings/publications | Aucun changement |
| Cache disque | ✅ Fonctionnel — `save_publications_cache()` après sync | Aucun changement |

### Architecture du cleanup — périmètre chirurgical (Décision 2 de la matrice lifecycle)

Le cleanup 5.3 ne nettoie un topic que si les **deux conditions de périmètre** ET **au moins une condition de cleanup** sont remplies :

**Périmètre (toutes requises) :**
1. Topic dans le namespace plugin : `homeassistant/{entity_type}/jeedom2ha_*/config`
2. Le `eq_id` extrait est connu du plugin (cache courant ou boot cache)

**Cleanup (au moins une) :**
3. `eq_id` absent de la topologie Jeedom (suppression DB)
4. `eq_id` devenu inéligible : exclu, désactivé, sans commandes, sans type générique
5. Confiance ne satisfait plus la politique courante (déjà géré par le bloc policy change L933-975)
6. `entity_type` changé (déjà géré par `_detect_lifecycle_changes` de 5.2)

**Ce que 5.3 ne fait PAS :**
- Ne nettoie JAMAIS un topic hors du namespace `jeedom2ha_*`
- Ne fait JAMAIS de wildcard subscribe sur `homeassistant/#`
- Ne nettoie PAS les topics d'état (`jeedom2ha/*/state`) — non retained
- Ne nettoie PAS les topics de commande — ce sont des souscriptions
- Ne nettoie PAS les retained d'autres plugins ou intégrations HA
- Ne nettoie PAS proactivement les orphelins retained (V1)

### Point d'ancrage dans `_handle_action_sync()` (http_server.py)

Les modifications de 5.3 sont localisées dans **la section purge existante** (lignes ~977-1068). Pas de nouvelle fonction à créer. Les changements sont :

**Changement 1 — Classification de la raison (avant les unpublish) :**
```python
# À ajouter au début de la boucle for old_eq_id in eq_ids_supprimes:
elig_entry = eligibility.get(old_eq_id)
if elig_entry is None:
    cleanup_reason = "supprimé dans Jeedom"
elif elig_entry.reason_code == "disabled_eqlogic":
    cleanup_reason = "désactivé dans Jeedom (disabled_eqlogic)"
elif elig_entry.reason_code.startswith("excluded_"):
    cleanup_reason = f"exclu ({elig_entry.reason_code})"
else:
    cleanup_reason = f"devenu inéligible ({elig_entry.reason_code})"
```

**Changement 2 — Messages de log avec tag [CLEANUP] et raison :**
Remplacer les `_LOGGER.info("[MAPPING] eq_id=%d est devenu inéligible ou supprimé ...")` par `_LOGGER.info("[CLEANUP] eq_id=%d: %s → discovery unpublish effectif", old_eq_id, cleanup_reason)`.

**Changement 3 — Availability cleanup inconditionnel (purge standard) :**
**IMPORTANT : ce changement reste DANS le bloc `if _needs_discovery_unpublish(old_decision):` (L1013).** On ne cleanup l'availability que si l'équipement était effectivement publié.
Remplacer le bloc conditionnel :
```python
if bool(getattr(old_decision, "local_availability_supported", False)):
    # cleanup availability...
```
Par un appel direct :
```python
# Nettoyage availability locale inconditionnel (5.3 — équipement retiré définitivement)
avail_topic = build_local_availability_topic(old_eq_id)
if mqtt_bridge and mqtt_bridge.is_connected:
    clear_ok = _clear_local_availability_topic(mqtt_bridge, old_eq_id, avail_topic)
    if clear_ok:
        pending_local_cleanup.pop(old_eq_id, None)
    else:
        _defer_local_availability_cleanup(pending_local_cleanup, old_eq_id, avail_topic)
else:
    _defer_local_availability_cleanup(pending_local_cleanup, old_eq_id, avail_topic)
```

**Changement 4 — Availability cleanup pour le chemin boot cache :**
Ajouter après le unpublish discovery boot cache (après L998 ou L1004) :
```python
# Cleanup availability locale depuis boot_cache (5.3)
avail_topic = build_local_availability_topic(old_eq_id)
if mqtt_bridge and mqtt_bridge.is_connected:
    clear_ok = _clear_local_availability_topic(mqtt_bridge, old_eq_id, avail_topic)
    if clear_ok:
        pending_local_cleanup.pop(old_eq_id, None)
    else:
        _defer_local_availability_cleanup(pending_local_cleanup, old_eq_id, avail_topic)
else:
    _defer_local_availability_cleanup(pending_local_cleanup, old_eq_id, avail_topic)
```

### Invariants à tester (matrice lifecycle)

| Invariant | Vérifié par |
|-----------|-------------|
| **INV-3** — Pas de ghost durable. Absent = unpublié. | AC #1, #2, TC-1, TC-2 |
| **INV-6** — Exclusion prime sur tout | AC #10 (log "exclu"), code existant dans eligibility chain |
| **INV-7** — Politique de confiance appliquée uniformément | Code existant (bloc policy change L933-975), pas de changement 5.3 |
| **INV-8** — Unpublish déféré si broker indisponible | AC #3, test deferred replay |
| **INV-11** — Désactivé = non publié | AC #4, #5, #7, TC-3 |

### Distinction supprimé vs désactivé vs indisponible (Décision 3)

| État | Détection dans le code 5.3 | Action discovery | Action availability |
|------|---------------------------|-----------------|-------------------|
| **Supprimé** | `old_eq_id not in eligibility` (absent de la topologie) | Payload vide retained | Payload vide retained |
| **Désactivé** | `eligibility[eq_id].reason_code == "disabled_eqlogic"` | Payload vide retained | Payload vide retained |
| **Exclu** | `eligibility[eq_id].reason_code.startswith("excluded_")` | Payload vide retained | Payload vide retained |
| **Indisponible** | Publié, `is_enable=true`, module physique injoignable | **Aucun changement** | `"offline"` (pas de suppression) |

### Note de cadrage AC #6 — indisponibilité physique

Le cas AC #6 reste dans le mécanisme runtime existant des entités encore éligibles : `models.topology._normalize_local_availability()` alimente le snapshot, `availability_from_snapshot()` puis `_apply_availability_metadata()` copient `local_availability_state` sur la `PublicationDecision`, et `_publish_local_availability_state()` publie ensuite le retained `jeedom2ha/{eq_id}/availability` pendant `/action/sync`.

Ce cas ne doit donc ajouter **aucun** cleanup discovery, **aucun** unpublish et **aucune** modification du cleanup 5.3 : on valide seulement qu'une entité encore éligible peut publier `local_availability_state="offline"` sans sortir du périmètre runtime déjà en place.

### Limitations V1 documentées

**L1 — Retained orphelins non nettoyés proactivement :**
Si un topic discovery retained existe sur le broker mais que le plugin n'a plus trace de l'eq_id (cache purgé, réinstallation plugin), le plugin ne le nettoiera pas. Workaround : `deploy-to-box.sh --stop-daemon-cleanup` ou suppression manuelle via `mosquitto_pub -t "homeassistant/{type}/jeedom2ha_{eq_id}/config" -n -r`.

**L2 — Un eq_id = une entité HA :**
Le plugin produit une seule entité HA par eq_id Jeedom. Si un équipement Jeedom a des commandes pouvant produire à la fois un `light` et des `sensor`, seul le type dominant est publié. Les entités multi-composants par eq_id sont hors scope V1.

### Dev Agent Guardrails

#### Guardrail 1 — Ne pas créer de nouvelle fonction ou fichier
Les modifications 5.3 sont localisées dans la **section purge existante** de `_handle_action_sync()` (~L977-1068). Pas de helper, pas de nouveau fichier de code. Les seuls nouveaux fichiers sont les tests sous `resources/daemon/tests/`. Réutiliser d'abord les factories `MappingResult` / `PublicationDecision`, le `MagicMock` bridge et les patterns de helpers présents dans `resources/daemon/tests/unit/test_command_sync.py`; pour les tests HTTP/aiohttp, reprendre le pattern `create_app` + `aiohttp_client` déjà en place dans `resources/daemon/tests/unit/test_diagnostic_endpoint.py`.

#### Guardrail 2 — Ne pas toucher au mécanisme set difference ni au bloc policy change
`eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids` et le bloc policy change (L933-975) fonctionnent correctement. Ne pas les modifier. Le bloc policy change fait déjà son propre cleanup availability (L964-974) — ne pas le dupliquer ni le modifier.

#### Guardrail 3 — Ne pas toucher à `_detect_lifecycle_changes` (5.2)
Le helper de détection lifecycle (rename, area, retypage) est distinct du cleanup 5.3. Ne pas le modifier.

#### Guardrail 4 — Import de `build_local_availability_topic`
Vérifier que `build_local_availability_topic` est importé depuis `models.availability`. S'il ne l'est pas déjà, l'ajouter aux imports de http_server.py.

#### Guardrail 5 — Le cleanup availability est idempotent et inoffensif
Publier un payload vide retained sur un topic availability qui n'existe pas sur le broker est un no-op inoffensif. C'est pourquoi le cleanup peut être inconditionnel sans risque d'effet de bord.

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Note d'alignement architecture — topic discovery

Cette story se cale sur le pattern de topic discovery **actuellement implémenté** : `homeassistant/{entity_type}/jeedom2ha_{eq_id}/config` (single-component discovery). La migration vers device discovery (`homeassistant/device/...`) est hors scope V1.

### Project Structure Notes

| Fichier | Modification |
|---------|-------------|
| `resources/daemon/transport/http_server.py` | Section purge (~L977-1068) : availability cleanup inconditionnel, availability cleanup boot cache, logging enrichi [CLEANUP] |
| `resources/daemon/tests/unit/test_cleanup.py` | Nouveau fichier — tests unitaires cleanup : raison classification, availability inconditionnelle, boot cache availability ; réutiliser les patterns de `resources/daemon/tests/unit/test_command_sync.py` |
| `resources/daemon/tests/integration/test_boot_reconciliation.py` | Nouveau fichier dédié si absent — scénarios sync post-boot / suppression pendant downtime avec availability cleanup ; reprendre le style d'intégration de `resources/daemon/tests/integration/test_command_sync_coexistence.py` |

Aucun conflit de structure détecté. Aucun nouveau modèle, aucun nouveau helper.

### References

- [Source: epic-5-lifecycle-matrix.md#Décision-2] — Frontière exacte du cleanup 5.3
- [Source: epic-5-lifecycle-matrix.md#Décision-3] — Distinction supprimé / désactivé / indisponible / exclu
- [Source: epic-5-lifecycle-matrix.md#Impacts-directs-sur-la-spec-5.3] — Spécification officielle story 5.3
- [Source: epic-5-lifecycle-matrix.md#Invariants] — INV-3 (pas de ghost), INV-8 (deferred), INV-11 (disabled = non publié)
- [Source: resources/daemon/transport/http_server.py#L977-1068] — Section purge existante (point d'ancrage principal)
- [Source: resources/daemon/transport/http_server.py#L985-1011] — Chemin boot cache (availability cleanup manquant)
- [Source: resources/daemon/transport/http_server.py#L1033-1057] — Availability cleanup conditionnel (à rendre inconditionnel)
- [Source: resources/daemon/transport/http_server.py#L101-113] — `_clear_local_availability_topic()` helper existant
- [Source: resources/daemon/models/availability.py#L13] — `LOCAL_AVAILABILITY_TOPIC_TEMPLATE` et `build_local_availability_topic()`
- [Source: resources/daemon/models/topology.py#L204-226] — `assess_eligibility()` chaîne d'éligibilité
- [Source: implementation-artifacts/5-2-stabilite-des-identifiants-et-renommages.md] — Contexte story précédente
- [Source: implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md] — Contrat auth terrain

## Stratégie de Tests

### Tests minimum par groupe d'AC

| Groupe AC | Type | Fichier cible | Ce qu'il vérifie |
|-----------|------|---------------|------------------|
| #1 — Suppression standard | Unitaire | `resources/daemon/tests/unit/test_cleanup.py` | eq_id supprimé → unpublish discovery + cleanup availability inconditionnel + log `[CLEANUP].*supprimé` |
| #2 — Suppression boot | Intégration | `resources/daemon/tests/integration/test_boot_reconciliation.py` | Boot cache published + absent topologie → unpublish discovery + cleanup availability |
| #3 — Deferred replay | Unitaire | `resources/daemon/tests/unit/test_cleanup.py` | Unpublish échoue → deferred → replay au sync suivant |
| #4 — Désactivation | Unitaire | `resources/daemon/tests/unit/test_cleanup.py` | is_enable=false → unpublish + log `[CLEANUP].*désactivé` |
| #5 — Réactivation | Intégration | `resources/daemon/tests/integration/test_boot_reconciliation.py` | Désactivé → réactivé → republié |
| #6 — Indisponible | Unitaire | `resources/daemon/tests/unit/test_cleanup.py` | Module HS → availability "offline" mais discovery inchangé |
| #7 — Désactivé vs indisponible | Unitaire | `resources/daemon/tests/unit/test_cleanup.py` | Même eq_id : indisponible→availability offline ; désactivé→discovery unpublish |
| #8, #9 — Availability inconditionnelle | Unitaire | `resources/daemon/tests/unit/test_cleanup.py` | Cleanup availability sans garde `local_availability_supported` ; boot cache cleanup |
| #10 — Classification raisons | Unitaire | `resources/daemon/tests/unit/test_cleanup.py` | 4 log patterns : supprimé / désactivé / exclu / inéligible |
| TC-1..4 — Terrain | Terrain | Task 4 | Voir Runbook ci-dessous |

## Runbook Terrain Obligatoire

La clôture de la story exige **deux validations distinctes** sur la box de validation : le mini preflight sync/runtime daemon du document `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md` (contrat `GET /system/status` + `POST /action/sync`) **puis** l'exécution complète du runbook TC-1 à TC-4 ci-dessous.

### Pré-conditions

```
- Box Jeedom de test avec daemon actif et entités publiées dans HA
- deploy-to-box.sh --cleanup-discovery --restart-daemon exécuté avec succès
- Accès SSH + mosquitto_sub disponible sur la box
- Au moins 3 équipements publiés dans HA (pour avoir de la marge)
```

### TC-1 — Suppression d'équipement

```
PRE: noter l'eq_id d'un équipement publié (ex: 355)
     mosquitto_sub -t "homeassistant/+/jeedom2ha_355/config" -C 1 → noter le payload
     mosquitto_sub -t "jeedom2ha/355/availability" -C 1 → noter le payload

1. Supprimer l'équipement dans Jeedom UI (via page équipement → supprimer)
2. Déclencher un rescan via le bouton "Scanner" dans l'UI diagnostic

CONTRAT PLUGIN (obligatoire) :
3. grep "[CLEANUP].*supprimé" logs daemon → message attendu avec eq_id
4. mosquitto_sub -t "homeassistant/+/jeedom2ha_355/config" -C 1 → payload vide (null)
5. mosquitto_sub -t "jeedom2ha/355/availability" -C 1 → payload vide (null)
6. Entité disparue de HA

PREUVES : captures logs + mosquitto_sub
```

### TC-2 — Suppression pendant daemon arrêté

```
PRE: noter un eq_id publié

1. Arrêter le daemon (Jeedom UI)
2. Supprimer l'équipement dans Jeedom
3. Redémarrer le daemon
4. Attendre le premier sync automatique

CONTRAT PLUGIN (obligatoire) :
5. grep "[CLEANUP].*supprimé.*boot_cache" logs daemon → message attendu
6. mosquitto_sub → discovery vide + availability vide
7. Entité disparue de HA

PREUVES : captures logs + mosquitto_sub
```

### TC-3 — Désactivation (is_enable=false)

```
PRE: noter un eq_id publié

1. Désactiver l'équipement dans Jeedom UI (décocher "Activer")
2. Rescan

CONTRAT PLUGIN (obligatoire) :
3. grep "[CLEANUP].*désactivé" logs daemon → message attendu
4. Entité disparue de HA (PAS juste "unavailable" — complètement absente)
5. Diagnostic Jeedom → équipement listé avec "Désactivé dans Jeedom"

6. Réactiver l'équipement (cocher "Activer") → rescan
7. Entité réapparaît dans HA

PREUVES : captures logs + mosquitto_sub + screenshots diagnostic
```

### TC-4 — Distinction indisponible vs désactivé

```
PRE: identifier un équipement dont le module physique peut être déconnecté
     (ex: prise connectée débranchable, ou débrancher l'antenne Z-Wave temporairement)

1. Rendre le module physique injoignable → attendre que Jeedom détecte
2. Vérifier dans HA : entité passe "unavailable" MAIS reste présente dans la liste
3. Vérifier availability topic : jeedom2ha/{eq_id}/availability → "offline"
4. Vérifier discovery topic : homeassistant/{type}/jeedom2ha_{eq_id}/config → payload JSON intact

5. Désactiver le même équipement (is_enable=false) → rescan
6. Vérifier dans HA : entité DISPARAÎT complètement (plus dans la liste)
7. Vérifier discovery topic → payload vide

PREUVES : captures comparées étape 2-4 vs étape 5-7
```

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Branche de travail : `codex/story-5-3-cleanup-lifecycle`
- Dry-run terrain : `./scripts/deploy-to-box.sh --dry-run` → `SSH OK | sudo OK`, simulation rsync OK
- Validation terrain projet : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → `Deploy complete.`, healthcheck OK, sync OK (`total_eq=287`, `eligible=82`, `published=30`)
- Mini preflight complémentaire sur box : `/system/status` sans header → `401`, avec `X-Local-Secret` → `status=ok`, `/action/sync` → HTTP `200`, `status=ok`
- Validation locale : `python3 -m pytest resources/daemon/tests` → `97 passed`
- Lint ciblé : `python3 -m flake8 resources/daemon/transport/http_server.py resources/daemon/tests/unit/test_cleanup.py resources/daemon/tests/integration/test_boot_reconciliation.py` → OK
- TC-1 terrain (eq_id=355) : suppression UI + rescan, log `[CLEANUP] eq_id=355: supprimé dans Jeedom → discovery unpublish effectif + availability cleanup`, puis `mosquitto_sub` timeout (`RC=27`) sur discovery + availability.
- TC-2 terrain (eq_id=616) : suppression pendant downtime daemon validée, log `[CLEANUP] eq_id=616: supprimé depuis downtime daemon → discovery unpublish effectif + availability cleanup (boot_cache, entity_type=light)`, puis `RC=27` discovery + availability post-redémarrage.
- TC-3 terrain (eq_id=617) : désactivation `is_enable=false` + rescan, log `[CLEANUP] eq_id=617: désactivé dans Jeedom (disabled_eqlogic) → discovery unpublish effectif + availability cleanup`, diagnostic "Cet équipement est désactivé dans Jeedom", puis réactivation + rescan avec republication discovery/availability (`online`).
- TC-4 terrain : tentative indisponibilité physique sur eq_id=617 non détectée par Jeedom (`jeedom2ha/617/availability` reste `online`), scénario de distinction non reproductible dans les contraintes du parc.

### Completion Notes List

- Durci la purge `eq_ids_supprimes` dans `http_server.py` sans toucher au set difference, au bloc policy change ni à `_detect_lifecycle_changes`.
- Rendu le cleanup du topic `jeedom2ha/{eq_id}/availability` inconditionnel pour les équipements réellement dépubliés, avec defer/replay inchangé si le broker est indisponible.
- Étendu le chemin boot cache pour nettoyer aussi l'availability locale après unpublish discovery, avec le même comportement deferred.
- Remplacé les logs génériques de purge par des logs `[CLEANUP]` classifiant explicitement `supprimé`, `désactivé`, `exclu` ou `devenu inéligible`.
- Ajouté des tests unitaires et d'intégration couvrant suppression standard, boot cache, replay différé, désactivation/réactivation, indisponibilité physique runtime et diagnostics post-cleanup.
- Validation terrain runbook exécutée et tracée: TC-1/TC-2/TC-3 PASS avec preuves logs+MQTT.
- TC-4 non reproductible sur le parc de validation (pas d'équipement pilotable permettant de provoquer une indisponibilité physique détectée).
- Dérogation explicite demandée par le porteur le 2026-03-22 pour bypass TC-4; risque résiduel conservé sur la validation terrain AC #6/#7.
- Story passée en `review` avec mention explicite de cette dérogation et des preuves manquantes associées.

### File List

- `_bmad-output/implementation-artifacts/5-3-nettoyage-automatique-et-gestion-des-ecarts.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_cleanup.py`
- `resources/daemon/tests/integration/test_boot_reconciliation.py`

## Change Log

- 2026-03-22 — Implémentation locale 5.3 terminée, tests Python + preflight box validés, story conservée `in-progress` en attente des TC-1 à TC-4 terrain.
- 2026-03-22 — Validation terrain guidée: TC-1/TC-2/TC-3 PASS (preuves logs+MQTT), TC-4 non reproductible sur le parc; bypass demandé par le porteur et dérogation documentée; statut mis à `review`.
