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

## 2. Conception cible

### 2.1 Principe

« Publier » devient un mini-sync sur son périmètre (`_resolve_eq_ids_for_portee`,
déjà en place, l.391-422), qui traite chaque `eq_id` par **la même fonction de
post-traitement que le sync** — aucune implémentation parallèle de la décision,
du publish ou de la dépublication.

### 2.2 Fonction extraite : `apply_publication_decision()`

Nouvelle fonction (nom proposé, à ajuster en dev-story), extraite du corps
actuel du sync, appelée **une fois par `eq_id`** par le sync ET par « Publier » :

```python
async def apply_publication_decision(
    *,
    eq_id: int,
    mapping: MappingResult,                       # evaluation.mapping (frais)
    decision: PublicationDecision,                 # evaluation.equipment_decision (frais)
    secondary_decisions: List[PublicationDecision],# evaluation.secondary_decisions (frais)
    snapshot: TopologySnapshot,
    previous_decision: Optional[PublicationDecision],  # publications.get(eq_id) AVANT cet appel
    publications: Dict[int, PublicationDecision],  # muté : publications[eq_id] = ...
    publisher_registry: Optional[PublisherRegistry],
    mqtt_bridge: Optional[MqttBridge],
    publisher: Optional[DiscoveryPublisher],
    pending_discovery_unpublish: Dict[int, object],
    pending_local_cleanup: Dict[int, str],
    mapping_counters: Optional[dict] = None,       # optionnel : "Publier" peut l'omettre
) -> PublicationOutcome                            # nouveau petit dataclass (published/unpublished/skipped/failed + compteur)
```

Corps (assemblé à partir de code déjà existant, sans nouvelle logique de
décision) :

1. **Bookkeeping** — identique à `_prepare_publication_bookkeeping` (l.375-388) : `decision.state_topic = _resolve_state_topic(mapping)`, `decision.active_or_alive = False`, `_apply_availability_metadata(...)`, puis `publications[eq_id] = decision`.
2. **Si `decision.should_publish`** — tente le publish MQTT du principal (`publisher_registry.publish(mapping, snapshot)`) puis des secondaires, **gatés par `secondary_decisions` frais** (plus par `_secondary_publishable`/`publication_decision_ref` figé) : reprend le corps utile du bloc sync l.1573-1619 (gestion `discovery_published`/`active_or_alive`/`publication_result`/compteurs/local availability) — ce bloc remplace à la fois le bloc sync existant ET `_publish_mapping_for_action` (Publier). Le couplage principal/secondaires (l.623-625, `_publish_mapping_for_action`) est supprimé : un échec du principal n'empêche plus de tenter chaque secondaire.
3. **Sinon, ou si transition publié → refusé** — si `previous_decision` était publié (`_needs_discovery_unpublish(previous_decision)`) : dépublication explicite, réutilisant tel quel le corps du bloc sync l.1648-1690 (`_collect_unpublish_node_ids` + `publisher.unpublish_by_eq_id` + `_defer_discovery_unpublish` si échec + nettoyage local availability). C'est le MÊME code que le bloc `else` déjà présent côté « Publier » (l.3666-3736) pour l'exclusion de scope — les deux se fusionnent en un seul appel (voir section 4).
4. **Mise à jour des refs secondaires** — pour chaque secondaire, repointer `secondary.publication_decision_ref` vers sa `secondary_decision` fraîche (ou la fusionner avec l'état d'exécution via `_reset_secondary_runtime_state`, arbitrage détaillé section 3.3) : garantit que `sync/state.py`/`sync/command.py` (lecteurs I11) restent corrects sans aucune modification de ces fichiers (pattern déjà vérifié : lecture directe pour le principal, `publication_decision_ref` pour chaque secondaire).

### 2.3 Ce qui est déplacé/fusionné

| Élément actuel | Devenir |
|---|---|
| `_prepare_publication_bookkeeping` (l.375-388) | Absorbée telle quelle, étape 1 du nouveau helper |
| Bloc publish MQTT du sync (l.1570-1607) | Généralisé, étape 2 |
| `_publish_additional_sensors` (sync, secondaires) | Fusionnée avec `_publish_mapping_for_action` (Publier) en une seule logique de publication secondaires, gatée par `secondary_decisions` frais |
| `_publish_mapping_for_action` (l.612-659) | Supprimée en tant que fonction séparée ; son corps utile (dispatch `publisher_registry.publish`) migre dans le nouveau helper |
| `_secondary_publishable` (l.500-514) | Supprimée — plus aucun lecteur (remplacée par lecture directe de `secondary_decisions`) |
| Bloc « policy change → dépublication » (l.1648-1690) | Absorbé étape 3, appelé **inline** par eq_id (plus de seconde boucle sur `nouveaux_eq_ids` après la boucle principale : `previous_decision` est déjà disponible au même point que `decision`, cf. l.1545 déjà lu avant bookkeeping — la boucle séparée existante est redondante avec ce qui est disponible inline, elle date d'un ajout ultérieur, Story 4.3/Task 2.7) |
| Bloc `else` scope-exclu de « Publier » (l.3666-3736) | Fusionné avec l'étape 3 (même mécanisme de dépublication) — le déclenchement (scope exclu vs décision refusée) devient une seule condition (section 4/5) |

### 2.4 Ce qui NE bouge PAS

- **Bloc « purge des disparus »** (`eq_ids_supprimes`, l.1692-1733+) reste propre au sync : concept différent (eq_id plus du tout dans `nouveaux_eq_ids`, càd absent de la nouvelle topologie ou devenu inéligible) — « Publier » n'a pas cette notion, son périmètre vient de la topologie déjà connue (`app["topology"]`), pas d'un nouveau payload Jeedom.
- **`_detect_lifecycle_changes`** (retypage/renommage) reste appelé uniquement par le sync — aucun AC de cette story ne demande son branchement sur « Publier » (question ouverte, section 9, si un retypage entre deux syncs doit aussi être traité par un clic « Publier »).
- **Branche « supprimer »** de `_handle_action_execute` (l.3409-3544) : inchangée, déjà conforme au principe 19-2 (n'écrit jamais le verdict canonique `evaluate_equipment()`, seulement un motif d'action `reason="excluded"`).

### 2.5 Boucle appelante côté sync et côté « Publier »

- **Sync** : pour chaque `eq_id` éligible (l.1519+), après `evaluate_equipment(...)` (l.1531-1539) et `_detect_lifecycle_changes` (l.1549), appelle `apply_publication_decision(eq_id=..., mapping=evaluation.mapping, decision=evaluation.equipment_decision, secondary_decisions=evaluation.secondary_decisions, ..., previous_decision=request.app["publications"].get(eq_id), ...)`. Le bloc « policy change » (l.1648-1690) est supprimé (absorbé, cf. 2.3). Le bloc « purge des disparus » reste séparé, après la boucle principale.
- **« Publier »** (mini-sync) : relit `overrides_cache = list_overrides(data_dir)` / `equipment_overrides_cache = list_equipment_overrides(data_dir)` **une fois par clic** (comme le sync le fait une fois par cycle, l.1515-1517 — jamais par équipement). Pour chaque `eq_id` de `_resolve_eq_ids_for_portee(...)` : `result = eligibility.get(eq_id)` (depuis `app["eligibility"]`, calculé au dernier sync — pas de nouvelle éligibilité), `eq = snapshot.eq_logics.get(eq_id)` (depuis `app["topology"]`), puis `evaluate_equipment(eq, snapshot, result, mapper_registry=mapper_registry, confidence_policy=app["confidence_policy"], persisted_overrides=overrides_cache, persisted_equipment_overrides=equipment_overrides_cache)`, puis `apply_publication_decision(...)` avec `previous_decision = publications.get(eq_id)` (déjà lu, l.3564). `_should_attempt_publish` et `_scope_entry_is_included`-comme-gate-de-publication disparaissent de ce chemin (le filtre de scope pur reste appliqué séparément, section 5, mais pour le flag d'affichage, pas pour décider de publier — sauf arbitrage contraire, section 5/9).

## 3. Principe 19-2 mis à jour, à écrire noir sur blanc

### 3.1 Énoncé

Le verdict canonique (`should_publish`/`reason` d'une `PublicationDecision`, principal ou secondaire)
n'est **jamais** écrit ailleurs que par `evaluate_equipment()`, appelé via le post-traitement
partagé `apply_publication_decision()` (section 2) — que ce soit depuis le sync complet ou depuis
le mini-sync « Publier ». Aucune autre voie ne doit produire ou modifier ce verdict.

- **« Supprimer »** (l.3409-3544) n'écrit jamais ce verdict : il écrit une `PublicationDecision(should_publish=False, reason="excluded")`
  **directement**, sans passer par `evaluate_equipment()` — c'est un acte utilisateur explicite
  (exclusion manuelle), pas une ré-évaluation de politique. Ce comportement existant reste inchangé ;
  Task 2 ne doit pas le faire passer par le nouveau helper (il resterait cohérent avec 19-2, mais le
  déplacement n'apporte rien et gonflerait le diff).
- **L'état d'exécution** (`discovery_published`, `active_or_alive`, `publication_result`, timestamps
  de dernière tentative) reste une notion séparée du verdict, déjà distinguée par
  `_reset_secondary_runtime_state` (l.517-560, `dataclasses.replace` qui préserve `should_publish`/`reason`
  et ne touche qu'aux champs d'exécution). Cette séparation est un invariant à **conserver**
  tel quel dans `apply_publication_decision()` : l'étape 1 (bookkeeping) et l'étape 2/3 (publication
  MQTT réelle) ne réécrivent jamais `should_publish`/`reason`, seulement les champs d'exécution.

### 3.2 Devenir de `_sync_publication_decision_refs` et `_reset_secondary_runtime_state`

- **`_reset_secondary_runtime_state`** (l.517-560) : **conservée**, réutilisée telle quelle par
  `apply_publication_decision()` à l'étape 4 (mise à jour des refs secondaires) — c'est exactement
  le mécanisme qui permet de fusionner un verdict frais (`secondary_decision` d'`evaluate_equipment()`)
  avec l'état d'exécution courant sans perdre l'un ou l'autre.
- **`_sync_publication_decision_refs`** (l.563-609) : **supprimée** en tant que fonction séparée.
  Aujourd'hui elle ne fait que boucler sur les secondaires et appeler `_reset_secondary_runtime_state`
  pour chacun (jamais le principal — docstring l.563-570 explicite : « ne repointe jamais le ref du
  principal, seul un sync complet le fait »). Une fois que **chaque appelant** (sync ET Publier) passe
  par `apply_publication_decision()`, qui fait cette boucle en interne (étape 4, section 2.2), cette
  fonction wrapper devient un pur pass-through sans appelant restant — à retirer pour éviter le code mort.
  Point de vigilance Task 2 : vérifier qu'aucun autre appelant (hors les deux chemins étudiés ici)
  n'utilise `_sync_publication_decision_refs` avant suppression (`grep -rn _sync_publication_decision_refs`).

### 3.3 Arbitrage : repointer ou fusionner le ref secondaire ?

Deux options pour l'étape 4 (mise à jour de `secondary.publication_decision_ref`) :

- **(a) Repointer directement** vers `secondary_decision` (le verdict frais retourné par
  `evaluate_equipment()`) — perd l'état d'exécution courant du secondaire (`discovery_published` etc.)
  s'il n'est pas réappliqué séparément.
- **(b) Fusionner** via `_reset_secondary_runtime_state(secondary, new_verdict=secondary_decision)`
  (signature à vérifier/adapter, l.517-560) — préserve l'état d'exécution, ne change que
  `should_publish`/`reason` si le verdict frais diffère du figé.

**Recommandation : (b)**, par cohérence stricte avec le principe déjà appliqué au sync
(`_reset_secondary_runtime_state` existe précisément pour ce cas). Reprendre (a) romprait la séparation
verdict/exécution que 19-2 a justement introduite. Ce point est mécanique, pas un choix de design ouvert —
à confirmer en Task 2 par simple lecture du corps actuel de `_reset_secondary_runtime_state`.

### 3.4 Vérification des lecteurs de diagnostic

- **`_compute_pipeline_step_visible`** (l.2211+, grep confirmé) : lit l'état des étapes du pipeline
  (éligibilité → mapping → décision → publication) à partir des mêmes structures
  (`eligibility`, `mappings`/`evaluation.mapping`, `publications[eq_id]`, état d'exécution) —
  aucune de ces structures ne change de forme, seule leur **fraîcheur** change (verdict recalculé à
  chaque « Publier » au lieu d'être lu depuis un cache figé). Le diagnostic reste correct sans
  modification ; il devient même plus fiable puisqu'il reflète le verdict réellement appliqué,
  plus une valeur périmée.
- **`traceability.decision_trace`** : à vérifier en Task 2 s'il capture le verdict au moment de
  `evaluate_equipment()` (cas correct, rien à changer) ou s'il capture un état antérieur
  supposé provenir uniquement du sync (à vérifier par lecture ciblée du module `traceability`,
  non lu dans cette note faute de temps — **question ouverte**, section 9, si le trace suppose
  implicitement « un seul appelant = le sync »).

## 4. Dépublication (AC4, AC5, AC6, I11)

### 4.1 Mécanisme réutilisé, sans rien inventer

La dépublication passe déjà, aujourd'hui, par la même chaîne dans les deux endroits qui en ont besoin
(sync « policy change » l.1648-1690, et « Publier » branche scope-exclue l.3666-3736) :
`_needs_discovery_unpublish(previous_decision)` (garde : était-il effectivement publié ?) →
`_collect_unpublish_node_ids(mapping)` (l.796, résout la liste de node_ids MQTT, gère le multi-domaine) →
`publisher.unpublish_by_eq_id(eq_id, entity_type, node_ids)` → en cas d'échec réseau/broker,
`_defer_discovery_unpublish(...)` (l.893-928) qui mémorise l'eq_id dans
`pending_discovery_unpublish` pour rejouer plus tard (`_replay_deferred_discovery_unpublish`)
→ nettoyage de l'availability locale. **Task 2 n'invente aucune nouvelle mécanique de dépublication** :
le nouveau helper `apply_publication_decision()` (étape 3, section 2.2) appelle ce même enchaînement,
factorisant les deux copies actuelles en une seule.

### 4.2 Cas du sync : équipement disparu ou refusé

Le sync distingue déjà deux cas différents, qui **restent distincts** après Task 2 :

- **« policy change »** (l.1648-1690) : l'eq_id est toujours dans `nouveaux_eq_ids` (topologie actuelle),
  mais `evaluate_equipment()` retourne cette fois `should_publish=False` alors qu'il était publié —
  absorbé dans `apply_publication_decision()` (section 2/3).
- **« purge des disparus »** (l.1692-1733+, `eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids`) :
  l'eq_id a complètement disparu de la topologie ou est devenu inéligible — cas hors du périmètre
  de « Publier » (qui n'a pas de nouvelle topologie, section 2.4), reste géré uniquement par le sync,
  inchangé.

### 4.3 Secondaire refusé, principal publié (dépublication par candidat)

`evaluate_equipment()` retourne un verdict **par candidat** (`equipment_decision` pour le principal,
un élément de `secondary_decisions` par secondaire, section « evaluate_equipment.py » du rapport) —
il n'y a donc, structurellement, aucune raison que la dépublication soit groupée : le nouveau helper
doit appliquer l'étape 3 (dépublication) **indépendamment pour chaque candidat** (principal et chaque
secondaire), en comparant son verdict frais à son propre état précédent via son propre
`publication_decision_ref`/`previous_decision`. C'est déjà le sens de
`_reset_secondary_runtime_state`, appelé par secondaire, jamais en bloc pour tout l'équipement.
Concrètement : un secondaire qui passe `should_publish=True→False` doit être dépublié (son propre
`unpublish_by_eq_id` avec ses propres node_ids) **même si le principal reste publié** — aucun code
actuel ne l'empêche puisque `_publish_mapping_for_action` traite déjà les secondaires dans une boucle
séparée (l.612-659) ; il suffit que la boucle de dépublication (étape 3) soit elle aussi par-candidat,
symétrique à la boucle de publication.

### 4.4 Principal refusé (le cas déjà couvert)

C'est le cas déjà géré par le mécanisme existant (4.1/4.2) : `previous_decision` du principal était
publié, le nouveau `equipment_decision.should_publish` est `False` → dépublication du principal.
Point à trancher en Task 2 (pas un blocage design, une question d'ordre d'opérations) : si le principal
est dépublié, que deviennent ses secondaires actuellement publiés (dont le topic MQTT dépend souvent du
device HA créé par le principal) ? Le code actuel de `_publish_mapping_for_action`/dépublication scope-exclue
ne semble pas traiter explicitement la dépublication en cascade des secondaires quand seul le principal
change de verdict — à vérifier par un test dédié (section 6) plutôt que supposé ici.

### 4.5 Idempotence (AC5) — vérifié dans le code actuel

**Constat vérifié (l.3546-3610, lu ce tour) : le chemin « Publier » actuel n'a PAS de garde
d'idempotence.** `_should_attempt_publish(mapping, previous_decision)` (l.482-497) ne teste que :
(1) `mapping.confidence in ("sure", "probable")` (bug CC-18 : omet `sure_mapping`), et (2) que le
`reason` de la décision **précédente** n'est pas dans une liste figée de 4 motifs de skip. **Elle ne
teste jamais si l'équipement est déjà publié avec un verdict inchangé.** Dès que ces deux conditions
passent, le code appelle inconditionnellement `_publish_mapping_for_action` (l.3575), qui refait un
vrai envoi MQTT (discovery + state), **même si rien n'a changé depuis la dernière publication réussie**.
Donc : **oui, le chemin actuel republie à chaque clic** un équipement déjà publié et toujours valide,
tant que son mapping garde une confiance suffisante.

**Condition à ajouter pour AC5** (dans `apply_publication_decision()`, avant l'étape 2) :
ne (re)publier réellement (appel MQTT) que si `previous_decision is None`, ou
`previous_decision.should_publish != decision.should_publish`, ou
`not _needs_discovery_unpublish` combiné à `previous_decision.discovery_published is not True`
(cas où le verdict était déjà `True` mais la publication précédente avait échoué — auquel cas il FAUT
retenter, ce n'est pas un cas d'idempotence). Autrement dit la garde est : « déjà publié
(`discovery_published=True`) ET verdict inchangé (`should_publish=True` avant et après) » ⇒ ne pas
rappeler `publisher.publish(...)`, seulement rafraîchir le bookkeeping (étape 1). C'est un changement
de comportement réel par rapport à l'existant (qui republie toujours) — à couvrir par un test dédié
(section 6) qui échoue sur `main` aujourd'hui.

### 4.6 I11 — rien à changer côté lecteurs

Comme établi en section 3.2/3.3 : tant que chaque candidat (principal et secondaires) a son verdict et
son état d'exécution mis à jour par le helper unique, `sync/state.py`/`sync/command.py` restent corrects
sans modification (lecture directe du `decision` pour le principal, `publication_decision_ref` pour
les secondaires — pattern déjà homogène dans les deux fichiers, vérifié ligne 150-230/214-220).
