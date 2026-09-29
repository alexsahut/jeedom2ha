# Note de conception — Story 19.4 « Publier » en mini-sync (CC-18)

Statut : brouillon pour relecture ClaudeBox avant tout code. Aucune ligne de
production modifiée dans ce tour. Tous les numéros de ligne ci-dessous sont
relevés sur `origin/main@5b14243` (fichier `resources/daemon/transport/
http_server.py`, 3901 lignes) — **différents** de ceux cités dans la story
(rédigée avant 19-2/19-3, donc périmés).

## 1. État actuel, cartographié

### 1.1 Les deux chemins, pas à pas

**Chemin sync** (`_do_handle_action_sync`, l.1425-1885+) :

1. Reconstruit une topologie fraîche depuis le payload Jeedom (`TopologySnapshot.from_jeedom_payload`, l.1452) et calcule `resolve_published_scope(snapshot, raw_scope=...)` (l.1457) → stocké dans `app["published_scope"]`, mais **jamais consulté ensuite pour décider de publier** (voir 1.4).
2. `assess_all(snapshot)` (l.1460) → éligibilité par eq_id, stockée dans `app["eligibility"]`.
3. Charge les overrides **une seule fois pour tout le cycle** (l.1515-1517) : `overrides_cache = list_overrides(data_dir)`, `equipment_overrides_cache = list_equipment_overrides(data_dir)`.
4. Boucle sur `eligibility.items()` (l.1519) ; pour chaque eq_id éligible : `evaluate_equipment(eq, snapshot, result, mapper_registry=mapper_registry, confidence_policy=confidence_policy, persisted_overrides=overrides_cache, persisted_equipment_overrides=equipment_overrides_cache)` (l.1531-1539) → `evaluation.mapping` + `evaluation.equipment_decision` (+ `evaluation.secondary_decisions`, frais, un par secondaire).
5. `_detect_lifecycle_changes(...)` (l.1549) dépublie l'ancien topic si retypage, AVANT toute republication.
6. **`_prepare_publication_bookkeeping(eq_id, mapping, decision, snapshot, publications, nouveaux_eq_ids)` (l.1561, définie l.375-388) — LE point d'écriture canonique du verdict** : pose `decision.state_topic`, remet `decision.active_or_alive = False`, applique les métadonnées de disponibilité, puis `publications[eq_id] = decision` et `nouveaux_eq_ids.add(eq_id)`. Rien d'autre n'écrit le verdict `should_publish`/`reason` du principal dans ce chemin.
7. Si `decision.should_publish` (l.1572) : tente le publish MQTT réel (`publisher_registry.publish`), gère `discovery_published`/`active_or_alive`/`publication_result`, republie les secondaires via `_publish_additional_sensors(... secondary_decisions=evaluation.secondary_decisions ...)` (l.1612-1619, **decisions fraîches**, pas `_secondary_publishable`).
8. **Bloc « policy change → dépublication » (l.1648-1690)** : pour chaque `eq_id` toujours mappé (`nouveaux_eq_ids`), si `previous_decision` était publié (`_needs_discovery_unpublish`) ET que `current_decision.should_publish` est maintenant `False` → dépublication explicite (`publisher.unpublish_by_eq_id` + `_collect_unpublish_node_ids` + defer si échec + nettoyage local availability). C'est le mécanisme AC4 attend.
9. **Bloc « purge des disparus » (l.1692-1733+)** : `eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids` — équipements plus du tout mappés (supprimés Jeedom ou devenus inéligibles) → même mécanique de dépublication, raison détaillée par `reason_code`.

**Chemin « Publier »** (`_handle_action_execute`, l.3270-3901, branche `intention == "publier"` à partir de l.3546) :

1. **N'utilise PAS un nouveau payload Jeedom.** Topologie = `request.app.get("topology")` (l.3331, le snapshot du DERNIER sync). `published_scope = request.app.get("published_scope")` (l.3332, calculé au dernier sync). `eligibility`/`mappings` (l.3393-3394) = les dicts figés du dernier sync.
2. `eq_ids = _resolve_eq_ids_for_portee(portee, selection, topology)` (l.3386, définie l.391-422) — résout le périmètre demandé (équipement/pièce/global) en mémoire.
3. Boucle sur `eq_ids` (l.3561+) : `mapping = mappings.get(eq_id)` — **le mapping CACHÉ du dernier sync, jamais recalculé** ; `previous_decision = publications.get(eq_id)` ; `is_included = _scope_entry_is_included(eq_id, scope_entry, eligibility)` (l.3565, définie l.455-464).
4. Si `is_included` : `if not _should_attempt_publish(mapping, previous_decision): skip` (l.3572-3574, bug CC-18 ci-dessous), sinon `_publish_mapping_for_action(publisher_registry, mapping, topology)` (l.3576, définie l.612-659) qui publie le principal puis gate chaque secondaire via `_secondary_publishable(secondary)` (l.638, définie l.500-514, décision **figée** du dernier sync).
5. Si **non** `is_included` : dépublication explicite si actuellement publié (l.3666-3736) — mécanisme déjà correct, mais **seulement pour l'exclusion de scope**, jamais pour un refus de `evaluate_equipment()`.

### 1.2 Divergences avec le sync, localisées précisément

| Divergence | Localisation | AC qui corrige |
|---|---|---|
| Tuple de confiance codé en dur `("sure", "probable")`, omet `"sure_mapping"` | `_should_attempt_publish`, l.482-489 (`mapping.confidence not in (...)`) | AC1 |
| Vérifie le `reason` de la **décision précédente** (dernier sync/action) contre un tuple figé, jamais le verdict frais | `_should_attempt_publish`, l.490-497 | AC1 |
| Deux codes du tuple (`unknown_skipped`, `ignore_skipped`) ne sont jamais produits par `decide_publication` (code mort) | `_should_attempt_publish`, l.493/496 vs `decide_publication.py:57` (`_PUBLISHABLE_CONFIDENCES`) | AC1 (nettoyage) |
| `mapping = mappings.get(eq_id)` réutilise le mapping calculé au dernier sync **avec les overrides d'alors**, jamais recalculé avec les overrides/policy courants | `_handle_action_execute`, l.3563 | AC1, AC2, AC6 |
| Équipement `is_included=True` mais devenu refusé (override d'exclusion ajouté) : `skip`, **aucune dépublication** | `_handle_action_execute`, l.3572-3574 (contraste avec le bloc sync l.1648-1690 qui, lui, dépublie) | AC4 |
| `_secondary_publishable` lit `secondary.publication_decision_ref.should_publish` — verdict **figé** du dernier sync, jamais réévalué par une action | l.500-514 (docstring l.501-511 le documente explicitement comme voulu, contexte 19-2/P1-bis) | AC6 |
| Couplage secondaires ↔ succès du principal : si `primary_ok` est `False`, `return False` immédiatement, secondaires jamais tentés | `_publish_mapping_for_action`, l.623-625 | Task 1 (guardrail, pas un AC direct — CC-18 ne le mentionne pas explicitement mais Task 1 l'exige) |
| `_scope_entry_is_included` (l.455-464) gate réellement la publication côté « Publier », alors que le sync ne consulte JAMAIS `published_scope`/scope pour décider de publier (seulement `eligibility.is_eligible`, l.1519-1520) | `_scope_entry_is_included` vs boucle sync l.1519 | AC3 (voir section 5 — écart significatif, PAS nul en pratique, voir 19-1 terrain) |
| `reason` reconstruit manuellement au succès (`publish_reason = mapping.confidence` si l'ancien reason était un code « skipped »/« failed ») au lieu du `reason` produit par `decide_publication()` | l.3603-3617 | Conséquence de AC1/AC2 une fois `evaluate_equipment()` branché : ce raccommodage disparaît, le `reason` vient directement de la décision fraîche |

### 1.3 `_apply_pending_scope_flags` — précision utile

Contrairement à ce que son commentaire dans la story laisse penser
(« réimplémentation locale de l'inclusion de scope »), cette fonction
(l.747-777) **ne recalcule pas** l'inclusion : elle lit `eq_entry.get(
"effective_state")` déjà posé par `resolve_published_scope` et calcule
uniquement un flag d'affichage `has_pending_home_assistant_changes` (état
désiré vs `decision.active_or_alive`). Elle n'est donc pas la cible directe
d'AC3 — la vraie question AC3 porte sur `_scope_entry_is_included` (qui, lui,
gate réellement la publication côté « Publier », jamais côté sync). Voir
section 5.

### 1.4 Ce que ce bug NE fait PAS (pour cadrer la story)

Le sync ignore aujourd'hui `published_scope`/`_scope_entry_is_included` pour
décider de publier — il publie tout ce que `decision.should_publish` (verdict
`decide_publication()`) autorise, indépendamment du scope UI. `published_scope`
est une vue/contrat séparé (précédence équipement > pièce > global sur un
arbre `raw_scope` fourni par le front-end), **sans lien algorithmique** avec
les overrides `publication_excluded_*` consommés par `decide_publication()`.
Ce sont deux mécanismes d'exclusion différents. Voir section 5 pour l'impact
chiffré (102 exceptions de scope réelles mesurées sur la box, artefact 19-1).
