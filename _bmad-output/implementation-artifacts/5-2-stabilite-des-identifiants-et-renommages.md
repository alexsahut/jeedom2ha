# Story 5.2: Stabilité des Identifiants et Renommages

Status: done  # terrain validé 2026-03-21 — TC-1/TC-2/TC-3 PASS

## Story

As a utilisateur Jeedom,
I want pouvoir renommer mes équipements dans Jeedom,
so that je puisse faire évoluer mon installation sans créer de nouvelle entité ni casser les références existantes côté HA dans le cas nominal.

## Hypothèses de Plateforme

| Hypothèse | Valeur vérifiée (post-5.1) | Impact pour 5.2 |
|-----------|---------------------------|-----------------|
| H1 — Renommage déjà implicitement géré | `/action/sync` republie TOUJOURS toutes les entités éligibles avec les données fraîches de Jeedom (`ha_name = eq.name` depuis la topologie courante) | Les renames sont "déjà" propagés — 5.2 ajoute la **détection explicite + logging** |
| H2 — Retypage non géré | Si `entity_type` change, l'ancien topic discovery reste retained sur le broker → ghost HA | 5.2 doit unpublish l'ancien topic AVANT de publish le nouveau |
| H3 — Cache ne persiste pas `ha_name` | Le cache 5.1 ne stocke que `{entity_type, published}` | 5.2 étend le format pour inclure `ha_name` et `suggested_area` |
| H4 — `unique_id` immuable | `ha_unique_id = f"jeedom2ha_eq_{eq.id}"` est calculé dans le mapper, jamais modifié | Un renommage ne touche jamais le `unique_id` ni le topic — aucune logique à modifier là |
| H5 — `suggested_area` depuis objets Jeedom | `snapshot.get_suggested_area(eq_id)` retourne `objects[object_id].name` | Un renommage d'objet Jeedom change la valeur de `suggested_area` dans le payload discovery |
| H6 — `previous_decision` disponible | `request.app["publications"].get(eq_id)` retourne le `PublicationDecision` précédent (contient `mapping_result` avec `ha_entity_type`, `ha_name`, `suggested_area`) | Point de comparaison pour détecter renames et retypages au runtime |
| H7 — Boot cache disponible | `request.app["boot_cache"]` est chargé au démarrage avant le premier sync (Task 1.3 de 5.1) | Comparaison boot_cache vs topologie courante pour détecter retypage survenu pendant le downtime |

## Acceptance Criteria

### Groupe 1 — Détection et republication d'un renommage d'équipement

1. **Given** un équipement est publié dans HA avec `ha_name="Lampe Salon"` **When** l'utilisateur le renomme `"Plafonnier Salon"` dans Jeedom et déclenche un rescan (`/action/sync`) **Then** le daemon détecte le changement en comparant le nouveau `mapping.ha_name` au `previous_decision.mapping_result.ha_name`, logue `INFO [LIFECYCLE] eq_id=N: rename détecté ('Lampe Salon' → 'Plafonnier Salon')`, et publie le discovery config sur le **même topic** (topic basé sur `eq_id`, inchangé) avec le nouveau `name`

2. **Given** un renommage est détecté au runtime **When** le discovery est republié **Then** le plugin publie sur le **même topic** avec le même `unique_id` (`jeedom2ha_eq_{eq_id}`) — aucune publication dupliquée n'est émise par le plugin. *(Côté HA : mise à jour du `friendly_name` attendue selon la spec MQTT Discovery — à confirmer en terrain TC-1)*

3. **Given** le daemon redémarre avec un cache disque persistant `ha_name="Lampe Salon"` **When** la première `/action/sync` post-boot apporte `ha_name="Plafonnier Salon"` **Then** le daemon compare le champ `ha_name` du `boot_cache[eq_id]` vs le nouveau `mapping.ha_name`, logue `INFO [LIFECYCLE] eq_id=N: rename détecté depuis boot_cache ('Lampe Salon' → 'Plafonnier Salon')`, et republie le discovery avec le nouveau nom

### Groupe 2 — Renommage d'objet Jeedom (suggested_area)

4. **Given** un équipement est publié avec `suggested_area="Salon"` **When** l'utilisateur renomme l'objet Jeedom contenant cet équipement en `"Séjour"` et déclenche un rescan **Then** le daemon détecte le changement en comparant `mapping.suggested_area` vs `previous_decision.mapping_result.suggested_area`, logue `INFO [LIFECYCLE] eq_id=N: area change ('Salon' → 'Séjour')`, et publie le discovery avec le nouveau `suggested_area`

5. **Given** le `suggested_area` a changé **When** le discovery est republié **Then** le `unique_id` et le topic discovery restent inchangés — seul le champ `suggested_area` du payload est mis à jour

### Groupe 3 — Retypage (entity_type change)

6. **Given** un équipement est publié comme `light` (topic `homeassistant/light/jeedom2ha_{eq_id}/config`) **When** son `generic_type` change dans Jeedom et le mapper le catégorise maintenant comme `switch` lors du prochain rescan **Then** le daemon :
   - Logue `INFO [LIFECYCLE] eq_id=N: retypage détecté (light → switch) → unpublish ancien topic`
   - Appelle `unpublish_by_eq_id(eq_id, entity_type="light")` (payload vide retained sur l'ancien topic) **AVANT** le publish du nouveau topic
   - Publie `homeassistant/switch/jeedom2ha_{eq_id}/config` avec le nouveau payload

7. **Given** un retypage est survenu pendant le downtime daemon (eq mappé comme `light` dans le cache, puis `generic_type` changé, puis daemon redémarre) **When** la première `/action/sync` post-boot est reçue et l'équipement est mappé comme `switch` **Then** le daemon compare `boot_cache[eq_id]["entity_type"]` (`"light"`) vs le nouveau `entity_type` (`"switch"`) → différence détectée → unpublish `light` topic AVANT publish `switch` topic — même logique que le retypage runtime (AC #6)

8. **Given** un retypage est détecté (runtime ou boot) **When** l'unpublish de l'ancien topic échoue (broker indisponible) **Then** l'ancien `eq_id` + `entity_type` est inséré dans `pending_discovery_unpublish` pour replay (INV-8), et la publication du nouveau topic continue normalement

### Groupe 4 — Extension du cache disque

9. **Given** la première `/action/sync` réussit **When** `save_publications_cache()` est appelé **Then** le fichier `data/jeedom2ha_cache.json` persiste pour chaque équipement les champs `{"entity_type": str, "published": bool, "ha_name": str, "suggested_area": str | null}` — les champs `ha_name` et `suggested_area` proviennent de `decision.mapping_result.ha_name` et `decision.mapping_result.suggested_area`

10. **Given** un cache au format 5.1 (sans `ha_name` / `suggested_area`) est présent sur le disque **When** `load_publications_cache()` charge ce fichier **Then** les entrées retournées ont `ha_name=""` et `suggested_area=None` par défaut (`.get("ha_name", "")`, `.get("suggested_area", None)`) — aucune erreur, aucun log d'erreur, démarrage normal

### Groupe 5 — Stabilité des identifiants (INV-4)

11. **Given** un équipement subit un renommage, un changement d'area, ou un retypage **When** le discovery est republié dans tous ces cas **Then** le champ `unique_id` du payload MQTT Discovery est toujours `"jeedom2ha_eq_{eq_id}"` — jamais basé sur le nom ou le type

12. **Given** un équipement est renommé dans Jeedom **When** HA reçoit le discovery republié **Then** le plugin garantit : même `unique_id` dans le payload, même topic, aucune double publication. *(Côté HA : mise à jour du `friendly_name` et continuité des automations/dashboards attendues selon la spec MQTT Discovery — à confirmer en terrain TC-1)*

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Déployer et redémarrer le daemon : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
    *(mode `--stop-daemon-cleanup` non pertinent pour 5.2 — aucune vérification de disparition d'entités sans republication prévue dans cette story)*
  - [ ] Vérifier que le script se termine avec `Deploy complete.`
  - [ ] Vérifier que des entités jeedom2ha sont visibles dans HA avant de démarrer les TC (état de base valide : au moins 2 équipements publiés)

- [x] Task 1 — Extension du cache disque (AC: #9, #10)
  - [x] 1.1 Dans `save_publications_cache()` (`cache/disk_cache.py`) : ajouter `ha_name` et `suggested_area` au dict sérialisé pour chaque entrée — `ha_name = str(getattr(mapping_result, "ha_name", "") or "")` ; `suggested_area = getattr(mapping_result, "suggested_area", None)`
  - [x] 1.2 Dans `load_publications_cache()` (`cache/disk_cache.py`) : ajouter `"ha_name": str(value.get("ha_name", "") or "")` et `"suggested_area": value.get("suggested_area", None)` dans le dict résultat — backward-compatible avec caches 5.1 sans ces champs
  - [x] 1.3 Tests unitaires (`tests/unit/test_disk_cache.py`) :
    - `save_publications_cache` produit le nouveau format avec `ha_name` et `suggested_area`
    - `load_publications_cache` d'un cache 5.1 (sans `ha_name`) retourne `ha_name=""`, `suggested_area=None` sans erreur

- [x] Task 2 — Implémentation du helper `_detect_lifecycle_changes` (AC: #1, #2, #3, #4, #5, #6, #7, #8)
  - [x] 2.1 Créer la fonction `async def _detect_lifecycle_changes(...)` dans `transport/http_server.py` — signature et corps complets définis dans les Dev Notes (section "Point d'ancrage"). Cette fonction unique couvre : rename runtime, area change runtime, retypage runtime, rename boot, retypage boot.
  - [x] 2.2 Appeler `await _detect_lifecycle_changes(...)` dans la boucle de mapping de `_handle_action_sync()`, **une seule fois par eq_id**, après création du `MappingResult`, avant `publisher.publish_*()`. L'appel est **commun aux trois branches** (light / cover / switch) — ne pas dupliquer.
  - [x] 2.3 Aucune logique de publication supplémentaire — le handler publie déjà avec les données fraîches ; le helper ne publie jamais, il ne fait que log + unpublish stale topics.
  - [x] 2.4 Tests unitaires (`tests/unit/test_lifecycle.py`, nouveau fichier) :
    - Rename runtime : sync avec `ha_name` modifié → log `INFO [LIFECYCLE].*rename détecté` exact ; `unique_id` dans le payload republié inchangé
    - Area change : sync avec `suggested_area` modifié → log `INFO [LIFECYCLE].*area change` exact
    - Retypage runtime : old light publié + sync switch → `unpublish_by_eq_id(X, "light")` appelé AVANT `publish_switch()` ; si unpublish échoue → `pending_discovery_unpublish[X] == "light"`, publish switch continue
    - Rename boot : boot_cache `ha_name="Salon"`, sync `ha_name="Séjour"` → log `INFO [LIFECYCLE].*rename détecté depuis boot_cache`
    - Retypage boot : boot_cache `entity_type="light"`, sync retourne switch → `unpublish_by_eq_id(X, "light")` + publish switch continue

- [x] Task 3 — Tests d'intégration retypage au boot (AC: #7, #8)
  - [x] 3.1 Dans `tests/integration/test_boot_reconciliation.py` : ajouter le scénario retypage au boot : cache `{eq_id=X, entity_type="light", published=True, ha_name="..."}`, première sync mappe `X` comme switch → `unpublish_by_eq_id(X, "light")` déclenché, puis publish switch
  - [x] 3.2 Broker indisponible au retypage boot → `pending_discovery_unpublish[X] == "light"`, publish switch continue normalement

- [x] Task 4 — Tests terrain (non négociables) (AC: Runbook)
  - [x] 4.1 TC-1 (renommage simple) — PASS 2026-03-21. Log `[LIFECYCLE] eq_id=355: rename détecté` à 18:56:04 et 19:05:30. Topic inchangé. `unique_id=jeedom2ha_eq_355` inchangé dans le payload. Côté HA : friendly_name mis à jour confirmé via MCP.
  - [x] 4.2 TC-2 (renommage d'objet Jeedom) — PASS 2026-03-21. Log `[LIFECYCLE] eq_id=355: area change ('Chambre parents' → 'bureau')` à 18:56:04. Payload contient `suggested_area: "bureau"`. Côté HA : device reste dans l'ancienne pièce — comportement HA attendu (voir observation O1).
  - [x] 4.3 TC-3 (retypage) — PASS 2026-03-21. Séquence validée en deux temps sur eq_id=355 : (A) switch→light à 19:38:12 — log `retypage détecté (switch → light)` + `rename détecté` simultané, mosquitto : switch(null) → light(payload) ; (B) light→switch à 19:43:58 — log `retypage détecté (light → switch)` + `rename détecté` simultané, mosquitto : light(null) → switch(payload). `unique_id=jeedom2ha_eq_355` inchangé dans tous les payloads.

## Dev Notes

### Tableau de bord du code existant — ce qui change dans 5.2

| Aspect | Comportement post-5.1 | Ce que 5.2 ajoute |
|--------|-----------------------|-------------------|
| Renommage eq (runtime) | Géré implicitement — publish avec `ha_name` frais à chaque sync | Détection + log explicite (AC #1) |
| Renommage area (runtime) | Géré implicitement — publish avec `suggested_area` frais | Détection + log explicite (AC #4) |
| Renommage au boot | Géré implicitement — reconciliation republie avec données fraîches | Détection depuis `boot_cache.ha_name` + log (AC #3) |
| Retypage runtime | ❌ Non géré — ghost dans HA (ancien topic retained non nettoyé) | Détection + unpublish ancien topic (AC #6) |
| Retypage au boot | ❌ Non géré — même problème | Comparaison `boot_cache.entity_type` vs nouveau type (AC #7) |
| Cache disque format | `{entity_type, published}` | Étendu : `{entity_type, published, ha_name, suggested_area}` (AC #9) |

### Règle critique — un renommage ne touche jamais le topic ni le unique_id

Le topic discovery est `homeassistant/{entity_type}/jeedom2ha_{eq_id}/config`. Il est dérivé de `eq_id` (stable, numérique) et du `entity_type`. Un renommage Jeedom change UNIQUEMENT le champ `name` dans le **payload** MQTT Discovery. Ne jamais modifier la construction du topic en fonction du `name`. Le `unique_id` (`jeedom2ha_eq_{eq_id}`) est immuable. INV-4.

### Règle critique — retypage = unpublish avant publish

Si `entity_type` change entre deux syncs, l'ancien topic (ex: `homeassistant/light/jeedom2ha_123/config`) reste en retained sur le broker. HA maintient alors deux entités pour le même équipement. La procédure stricte est :

```
1. Détecter : old_entity_type != new_entity_type ET was_published
2. Unpublish ancien topic (payload vide retained) AVANT publish nouveau
3. Si unpublish échoue → pending_discovery_unpublish[eq_id] = old_type, continuer
4. Publish nouveau topic normalement
```

L'ordre est critique. Ne pas inverser. Le `unique_id` HA ne change pas mais l'`entity_id` HA peut changer (`light.xxx` → `switch.xxx`) — rupture acceptée V1.

### Point d'ancrage dans `_handle_action_sync()` (http_server.py)

La boucle de mapping traite chaque type séparément (light → cover → switch). Les trois branches partagent la même logique de détection lifecycle.

**Stratégie canonique imposée : extraire un helper async dédié** — ne pas dupliquer le bloc dans chaque branche type.

Nom imposé : `_detect_lifecycle_changes(eq_id, mapping, previous_decision, boot_cache, is_first_sync, publisher, pending_discovery_unpublish)` — fonction `async` dans `http_server.py`.

Appel unique dans la boucle de mapping, **après** la création du `MappingResult` et **avant** `publisher.publish_*()`, commun aux trois branches (light / cover / switch) :

```python
await _detect_lifecycle_changes(
    eq_id, mapping, previous_decision,
    boot_cache=request.app.get("boot_cache", {}),
    is_first_sync=is_first_sync,
    publisher=publisher,
    pending_discovery_unpublish=pending_discovery_unpublish,
)
```

Implémentation du helper :

```python
async def _detect_lifecycle_changes(
    eq_id: int,
    mapping: MappingResult,
    previous_decision,
    boot_cache: dict,
    is_first_sync: bool,
    publisher,
    pending_discovery_unpublish: dict,
) -> None:
    """Detect and handle rename, area change, and retyping for a single eq_id.

    Called once per eq_id in the mapping loop, before publish.
    Guardrail: never publishes — only unpublishes stale topics and logs.
    """
    # --- Runtime detection (previous_decision from app["publications"]) ---
    if previous_decision is not None and getattr(previous_decision, "mapping_result", None) is not None:
        prev_mr = previous_decision.mapping_result
        # Retypage runtime : unpublish ancien topic si entity_type a changé
        if prev_mr.ha_entity_type != mapping.ha_entity_type and _needs_discovery_unpublish(previous_decision):
            _LOGGER.info(
                "[LIFECYCLE] eq_id=%d: retypage détecté (%s → %s) → unpublish ancien topic",
                eq_id, prev_mr.ha_entity_type, mapping.ha_entity_type,
            )
            unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=prev_mr.ha_entity_type)
            if not unpublish_ok:
                _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, prev_mr.ha_entity_type)
        # Rename / area change logs (publication déjà assurée par le handler avec données fraîches)
        if prev_mr.ha_name != mapping.ha_name:
            _LOGGER.info("[LIFECYCLE] eq_id=%d: rename détecté ('%s' → '%s')", eq_id, prev_mr.ha_name, mapping.ha_name)
        if prev_mr.suggested_area != mapping.suggested_area:
            _LOGGER.info("[LIFECYCLE] eq_id=%d: area change ('%s' → '%s')", eq_id, prev_mr.suggested_area, mapping.suggested_area)

    # --- Boot detection (boot_cache chargé depuis le disque) ---
    if is_first_sync:
        boot_entry = boot_cache.get(eq_id)
        if boot_entry:
            boot_type = boot_entry.get("entity_type", "")
            boot_name = boot_entry.get("ha_name", "")
            # Retypage au boot
            if boot_type and boot_type != mapping.ha_entity_type:
                _LOGGER.info(
                    "[LIFECYCLE] eq_id=%d: retypage au boot (%s → %s) → unpublish ancien topic",
                    eq_id, boot_type, mapping.ha_entity_type,
                )
                unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=boot_type)
                if not unpublish_ok:
                    _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, boot_type)
            # Rename au boot
            if boot_name and boot_name != mapping.ha_name:
                _LOGGER.info(
                    "[LIFECYCLE] eq_id=%d: rename détecté depuis boot_cache ('%s' → '%s')",
                    eq_id, boot_name, mapping.ha_name,
                )
```

> **Note** : le retypage runtime et le retypage boot sont mutuellement exclusifs (`previous_decision` est None au premier sync, donc seul le chemin `is_first_sync` s'exécute au boot). Aucune double dépublication possible.

### Extension du cache disque — format cible

```json
{
  "123": {"entity_type": "light",  "published": true,  "ha_name": "Lampe Salon",    "suggested_area": "Salon"},
  "456": {"entity_type": "cover",  "published": true,  "ha_name": "Volet Chambre",  "suggested_area": "Chambre"},
  "789": {"entity_type": "switch", "published": false, "ha_name": "Prise Bureau",   "suggested_area": null}
}
```

Dans `save_publications_cache()` :
```python
cache[str(eq_id)] = {
    "entity_type": entity_type,
    "published": published,
    "ha_name": str(getattr(mapping_result, "ha_name", "") or ""),
    "suggested_area": getattr(mapping_result, "suggested_area", None),
}
```

Dans `load_publications_cache()`, ajout au dict résultat :
```python
result[eq_id] = {
    "entity_type": str(value.get("entity_type", "") or ""),
    "published": bool(value.get("published", False)),
    "ha_name": str(value.get("ha_name", "") or ""),        # BC: absent en 5.1
    "suggested_area": value.get("suggested_area", None),   # BC: absent en 5.1
}
```

### Dev Agent Guardrails

#### Guardrail 1 — Renommage ne touche jamais le topic ni le unique_id (INV-4)
Le topic `homeassistant/{entity_type}/jeedom2ha_{eq_id}/config` est dérivé de `eq_id` numérique. Ne jamais utiliser `ha_name` dans la construction du topic. `ha_unique_id = f"jeedom2ha_eq_{eq_id}"` est immuable quelle que soit la modification Jeedom.

#### Guardrail 2 — Unpublish AVANT publish pour le retypage (ordre critique)
Si `entity_type` a changé : unpublish ancien → publish nouveau. Ne jamais inverser. Si unpublish échoue : déférer dans `pending_discovery_unpublish` et continuer le publish du nouveau topic.

#### Guardrail 3 — Ne pas refactorer la logique de publication existante
Le handler `/action/sync` republie déjà tous les équipements éligibles avec données fraîches. 5.2 ajoute UNIQUEMENT des logs et l'unpublish de l'ancien topic en cas de retypage. Ne pas changer la logique `should_publish`, ne pas ajouter `asyncio.sleep()` dans le chemin HTTP, ne pas réécrire la boucle de mapping.

#### Guardrail 4 — Backward compatibility du cache disque
Les caches existants (format 5.1) ne contiennent pas `ha_name` ni `suggested_area`. `load_publications_cache()` doit retourner des valeurs par défaut (`""`, `None`) sans lever d'exception ni logger d'erreur pour ces champs manquants.

#### Guardrail 5 — `_needs_discovery_unpublish` comme garde-fou
Vérifier `_needs_discovery_unpublish(previous_decision)` avant tout unpublish runtime — cette fonction retourne `True` seulement si l'entité était réellement publiée. Ne pas tenter d'unpublish si l'entité n'était pas publiée (`discovery_published=False`).

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Note d'alignement d'architecture — topic discovery

Cette story se cale sur le pattern de topic discovery **actuellement implémenté** dans le code :
`homeassistant/{entity_type}/jeedom2ha_{eq_id}/config` (single-component discovery).

Ce choix est différent du target architectural documenté dans `architecture.md` (device discovery : `homeassistant/device/...`). La migration vers device discovery est hors scope V1. Les raisonnements de topic dans cette story (unpublish de l'ancien topic, détection de retypage) sont valides pour le pattern single-component en production — ils devront être réadaptés si le pattern change dans une future story.

### Project Structure Notes

| Fichier | Modification |
|---------|-------------|
| `resources/daemon/cache/disk_cache.py` | Étendu : persist/load `ha_name` + `suggested_area` — backward-compatible |
| `resources/daemon/transport/http_server.py` | `_handle_action_sync()` : rename logs + retypage handling (runtime + boot) |
| `tests/unit/test_disk_cache.py` | Adapter pour le nouveau format ; test BC ancien format (sans ha_name) |
| `tests/unit/test_lifecycle.py` | Nouveau fichier — tests rename detection + retypage runtime |
| `tests/integration/test_boot_reconciliation.py` | Extension — test retypage au boot + rename depuis boot_cache |

Aucun conflit de structure détecté. `ha_name` et `suggested_area` sont déjà dans `MappingResult` — aucun nouveau champ de modèle à créer.

### References

- [Source: epic-5-lifecycle-matrix.md#Impacts-directs-sur-la-spec-5.2] — Spécification officielle story 5.2
- [Source: epic-5-lifecycle-matrix.md#Décision-3] — Distinction supprimé / désactivé / indisponible / retypage
- [Source: epic-5-lifecycle-matrix.md#Invariants] — INV-4 (IDs stables), INV-8 (unpublish déféré)
- [Source: resources/daemon/cache/disk_cache.py] — Format cache actuel + logique save/load à étendre
- [Source: resources/daemon/transport/http_server.py#_handle_action_sync] — Point d'ancrage principal (lignes ~547–991)
- [Source: resources/daemon/models/mapping.py#MappingResult] — Champs `ha_name`, `suggested_area`, `ha_entity_type`, `ha_unique_id`
- [Source: resources/daemon/mapping/light.py] — Pattern `ha_name=eq.name, suggested_area=snapshot.get_suggested_area(eq.id)` — identique dans cover.py et switch.py
- [Source: implementation-artifacts/5-1-persistance-et-republication-post-reboot.md] — Architecture boot/cache établie, guardrails de référence
- [Source: implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md] — Contrat auth terrain obligatoire

## Stratégie de Tests

### Tests minimum par groupe d'AC

| Groupe AC | Type | Fichier cible | Ce qu'il vérifie |
|-----------|------|---------------|------------------|
| #1, #2 — Rename runtime | Unitaire | `test_lifecycle.py` | Sync avec `ha_name` modifié → log `[LIFECYCLE].*rename détecté` exact ; topic inchangé ; `unique_id` inchangé dans le payload |
| #3 — Rename boot | Unitaire | `test_lifecycle.py` | boot_cache `ha_name="Salon"`, sync `ha_name="Séjour"` → log `[LIFECYCLE].*rename détecté depuis boot_cache` |
| #4, #5 — Area change | Unitaire | `test_lifecycle.py` | Sync avec `suggested_area` modifié → log `[LIFECYCLE].*area change` exact |
| #6, #8 — Retypage runtime | Unitaire | `test_lifecycle.py` | old light publié + sync switch → `unpublish_by_eq_id(X, "light")` avant `publish_switch()` ; unpublish échoue → pending ; publish switch continue |
| #7, #8 — Retypage boot | Intégration | `test_boot_reconciliation.py` | boot_cache `entity_type="light"`, sync retourne switch → `unpublish_by_eq_id(X, "light")` + publish switch |
| #9, #10 — Cache format | Unitaire | `test_disk_cache.py` | `save()` produit le nouveau format ; `load()` d'un cache 5.1 (sans `ha_name`) → défauts BC sans erreur |
| #11, #12 — INV-4 | Unitaire | `test_lifecycle.py` | `unique_id = "jeedom2ha_eq_{id}"` inchangé dans payload rename et retypage |
| TC-1, TC-2, TC-3 — Terrain | Terrain | Task 4 | Contrat plugin : logs `[LIFECYCLE]` + mosquitto_sub. Terrain attendu côté HA : à confirmer |

## Runbook Terrain Obligatoire

### Pré-conditions

```
- Box Jeedom de test avec daemon actif et entités publiées dans HA
- deploy-to-box.sh --cleanup-discovery --restart-daemon exécuté avec succès
- Accès SSH + mosquitto_sub disponible sur la box
- Au moins 2 équipements publiés dans HA
```

### TC-1 — Renommage simple

```
PRE: noter l'eq_id et le nom actuel d'un équipement publié
     mosquitto_sub -t "homeassistant/+/jeedom2ha_+/config" -C 1 → noter le "name" et "unique_id" actuels

1. Renommer l'équipement dans Jeedom UI (ex: "Lampe" → "Plafonnier")
2. Déclencher un rescan via le bouton "Scanner" dans l'UI diagnostic

CONTRAT PLUGIN (obligatoire) :
3. grep "[LIFECYCLE].*rename" logs daemon → message rename détecté attendu
4. mosquitto_sub -t "homeassistant/+/jeedom2ha_{eq_id}/config" -C 1 → "name": "Plafonnier" + "unique_id": "jeedom2ha_eq_{id}" inchangé
5. Topic identique (même chemin) au payload précédent — aucune deuxième publication sur un autre topic

TERRAIN ATTENDU côté HA (à confirmer, non garanti par le plugin) :
6. friendly_name mis à jour dans l'UI HA, entity_id inchangé, aucun doublon
7. Automation utilisant cette entité toujours fonctionnelle
```

### TC-2 — Renommage d'objet Jeedom (pièce)

```
PRE: noter le suggested_area actuel d'un équipement (dans le payload discovery via mosquitto_sub)

1. Renommer l'objet Jeedom contenant l'équipement dans Jeedom UI
2. Déclencher un rescan

CONTRAT PLUGIN (obligatoire) :
3. grep "[LIFECYCLE].*area change" logs daemon → message attendu
4. mosquitto_sub -t "homeassistant/+/jeedom2ha_{eq_id}/config" -C 1 → "suggested_area": nouveau nom de pièce

TERRAIN ATTENDU côté HA (à confirmer) :
5. Zone de l'entité mise à jour dans la fiche HA
```

### TC-3 — Retypage (si équipement adapté disponible)

```
PRE: identifier un équipement dont le generic_type peut être modifié pour changer le type HA
     (ex: LIGHT_* → retirer pour ne garder que ENERGY_ON + ENERGY_OFF → devient switch)

1. Modifier le generic_type dans Jeedom pour changer le type HA résultant
2. Déclencher un rescan

CONTRAT PLUGIN (obligatoire) :
3. grep "[LIFECYCLE].*retypage" logs daemon → message attendu
4. Ancien topic vide : mosquitto_sub -t "homeassistant/light/jeedom2ha_{eq_id}/config" -C 1 → payload vide ou absent
5. Nouveau topic valide : mosquitto_sub -t "homeassistant/switch/jeedom2ha_{eq_id}/config" -C 1 → payload JSON valide

TERRAIN ATTENDU côté HA (à confirmer) :
6. Ancienne entité light disparue de HA, nouvelle entité switch présente
PREUVES : captures logs + mosquitto_sub
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

Néant — implémentation sans blocage ni déviation de la story.

### Completion Notes List

- **Task 1 (disk_cache.py)** : `save_publications_cache` étend chaque entrée avec `ha_name` et `suggested_area` depuis `mapping_result`. `load_publications_cache` lit ces champs avec fallback `""` / `None` pour backward compat caches 5.1. Tests AC#9/AC#10 : 17 tests disk_cache PASS.
- **Task 2 (http_server.py)** : `_detect_lifecycle_changes` créé comme fonction `async` module-level. Appelé une seule fois par `eq_id` dans `_handle_action_sync()`, après `mappings[eq_id] = mapping` et avant le if/elif de type. Couvre : rename runtime (log), area change (log), retypage runtime (unpublish + defer si échec), rename boot (log), retypage boot (unpublish + defer si échec). Jamais publie. Tests AC#1-#8,#11 : 23 tests lifecycle PASS.
- **Task 3 (test_boot_reconciliation.py)** : 4 nouveaux tests d'intégration : retypage boot ordering (unpublish avant publish), log lifecycle boot, défer si broker down, absence de retypage si type inchangé. 10 tests integration PASS.
- **Régression** : 418 tests PASS, 0 regression.
- **INV-4** : `unique_id = f"jeedom2ha_eq_{eq_id}"` inchangé dans tous les scénarios — le helper ne touche jamais `ha_unique_id`.
- **Guardrail ordre retypage** : unpublish old → publish new. Garanti par la structure séquentielle : helper appelé avant le bloc publish dans chaque branche.
- **Follow-ups code review 2026-03-21** : ✅ Résolu MEDIUM-1 — garde `published` ajoutée sur boot retypage L255 (alignement Guardrail 5 + test `test_no_retypage_boot_when_not_published`) ; ✅ Résolu LOW-1 — docstring `load_publications_cache` mis à jour avec les 4 champs ; ✅ Résolu LOW-2 — 3 tests combinés rename+retypage simultanés ajoutés (class `TestRenameAndRetypageCombined`). Suite : 422 tests PASS.

### File List

- `resources/daemon/cache/disk_cache.py` — étendu : ha_name + suggested_area dans save/load, BC 5.1 ; docstring load mis à jour (follow-up LOW-1)
- `resources/daemon/transport/http_server.py` — ajout `_detect_lifecycle_changes`, appel dans `_handle_action_sync()` ; garde `published` boot retypage (follow-up MEDIUM-1)
- `tests/unit/test_disk_cache.py` — adapté pour nouveau format + tests AC#9/AC#10
- `tests/unit/test_lifecycle.py` — nouveau fichier, 23 tests unitaires helper lifecycle + 1 test garde boot (follow-up MEDIUM-1) + 3 tests combinés rename+retypage (follow-up LOW-2)
- `tests/integration/test_boot_reconciliation.py` — 4 nouveaux tests retypage au boot (AC#7/AC#8)
- `_bmad-output/implementation-artifacts/5-2-stabilite-des-identifiants-et-renommages.md` — story mise à jour
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — statut → review

### Post-terrain Observations

**O1 — Comportement HA `suggested_area` (TC-2)**
Le champ `suggested_area` dans le payload MQTT Discovery est une suggestion à la **première création** du device dans HA. Pour les devices déjà enregistrés, HA ne réassigne pas automatiquement la pièce lors des mises à jour discovery suivantes — l'utilisateur doit déplacer le device manuellement dans HA. Ce comportement est documenté dans la spec HA MQTT Discovery. Le plugin remplit correctement sa responsabilité (log + payload mis à jour) ; la non-propagation automatique est côté HA.
→ Besoin de documentation utilisateur identifié (DOC-1) : expliquer ce comportement et la marche à suivre (cleanup-discovery ou déplacement manuel).

**O2 — Substring keyword matching dans le mapper (Bug B1)**
Lors de TC-3, des noms d'équipements courants ont déclenché des ambiguïtés inattendues :
- "bureau" contient "eau" → bloque le mapping light
- "lampe" → bloque le mapping switch

La logique actuelle fait un `in` (substring) plutôt qu'une correspondance de mots entiers, ce qui génère des faux positifs sur des mots courants du vocabulaire français. L'interface de diagnostic ne détaille pas les règles déclenchées.
→ Deux besoins identifiés (DOC-2 et BUG-1) : documentation des règles de mapping, et story correctif substring matching.

### Change Log

- 2026-03-21 : Implémentation Story 5.2 — extension cache disque (ha_name/suggested_area), helper _detect_lifecycle_changes (rename+area+retypage runtime et boot), tests unitaires et d'intégration, 418 tests PASS.
- 2026-03-21 : Follow-ups code review — garde published boot retypage (MEDIUM-1), docstring load mis à jour (LOW-1), 3 tests rename+retypage combinés (LOW-2). 422 tests PASS.
- 2026-03-21 : Validation terrain TC-1/TC-2/TC-3 PASS sur box réelle (eq_id=355, deconz ikea). Story done. Observations O1 (suggested_area HA) et O2 (keyword substring) documentées.
