# Story 5.3 : Flux Supprimer standalone avec confirmations fortes

Status: done

## Story

En tant qu'utilisateur Jeedom avancé,
je veux lancer explicitement la suppression d'une entité Home Assistant avec une confirmation forte rappelant la portée et les conséquences,
afin de savoir exactement quand j'accepte un impact potentiel côté Home Assistant et de pouvoir recréer proprement une entité depuis un état vierge.

## Contexte / Objectif produit

Cette story implémente l'exécution réelle de l'intention `supprimer` dans la façade backend unique posée par la Story 5.1. Elle est la suite directe de Story 5.2 qui a implémenté le flux `publier`.

L'objectif produit est triple :

1. **Exécution backend réelle** — remplacer le stub `non_implemente` pour `intention = "supprimer"` par la dépublication MQTT Discovery effective.
2. **Confirmation forte obligatoire** — l'utilisateur doit explicitement accepter les conséquences potentielles avant toute suppression (historique HA, dashboards, automatisations, `entity_id`).
3. **Boucle terrain Supprimer → Créer** — cette story est le support de validation explicite du cas `Créer` non soldé dans le gate terrain de Story 5.2 (waiver documenté). Le gate terrain de Story 5.3 doit obligatoirement couvrir la boucle complète : Supprimer → disparition HA → Créer → recréation HA.

**Contrat sémantique :**
- **`supprimer`** = dépublication standalone. Supprime la configuration MQTT Discovery de l'entité dans Home Assistant. L'entité disparaît de HA. Ce n'est pas un "Supprimer puis recréer" atomique : le "puis recréer" est une action utilisateur ultérieure (bouton `Créer`/`Republier`, déjà implémenté par Story 5.2).
- **Intention backend** = `supprimer` dans tous les cas (même façade que Story 5.2, même portées).
- **Label UX** = `Supprimer puis recréer dans Home Assistant` (communique à l'utilisateur qu'il pourra recréer ensuite, pas que la recréation est automatique).

**Frontière de scope Story 5.3 / Story 5.2 :**
- Story 5.3 n'ajoute **aucune logique métier nouvelle au flux `Créer`**. La partie `Créer` présente dans le gate terrain sert uniquement à valider la cohérence post-suppression et à solder le waiver terrain de Story 5.2.
- La branche `publier` / `Créer` livrée par Story 5.2 **ne doit pas être modifiée**, sauf bug strictement bloquant découvert pendant l'implémentation de Story 5.3 et documenté explicitement.

## Dépendances autorisées

- **Story 5.1** — `done` : façade backend, stub `supprimer`, signal `actions_ha`, matrice disponibilité (Supprimer actif ssi `est_publie_ha = true` ET inclus)
- **Story 5.2** — `done` : implémentation `publier`, `_resolve_eq_ids_for_portee`, pattern boucle publish, `triggerPublierAction` — les patterns sont à réutiliser directement
- **Story 2.3** — `done` : gating bridge
- **Story 3.2** — `done` : `reason_code` stables

## Scope

### In scope

**Backend :**
1. Remplacement du stub `non_implemente` pour `intention = "supprimer"` dans `_handle_action_execute` (`http_server.py:1967`)
2. Réutilisation de `_resolve_eq_ids_for_portee(portee, selection, topology)` — existant Story 5.2, aucune modification
3. Pour chaque `eq_id` résolu :
   - Publié (`_is_currently_published_in_ha = True`) → `publisher.unpublish_by_eq_id(eq_id, entity_type)` ; si succès : mettre à jour `publications[eq_id]` avec `discovery_published=False` + nettoyage availability ; incrémenter `equipements_supprimes`
   - Déjà non publié → skip ; incrémenter `skips`
   - Échec unpublish → `_defer_discovery_unpublish` ; incrémenter `supprimer_errors`
4. Lissage identique à Story 5.2 : `max(0.1, 10.0 / max(1, N))` entre chaque unpublish
5. Guards identiques à Story 5.2 : `topology is None` → HTTP 409 ; `mqtt_bridge.is_connected is False` → HTTP 503
6. Payload de retour structuré (voir contrat ci-dessous)

**Frontend (JS) :**

Story 5.3 implémente un **même flux fonctionnel `supprimer`** décliné sur les portées équipement / pièce / global, sans élargissement UX au-delà des confirmations fortes et du déclenchement d'action. Les seules différences entre portées sont le contenu de la modale de confirmation (portée, compteur) et le paramètre `portee` passé à `executeHaAction`.

7. Click handler équipement sur `.j2ha-action-ha-btn[data-ha-action="supprimer"]` :
   - Modale de confirmation forte (voir §Contrat confirmation forte)
   - Appel `triggerSupprimerAction($button, "equipement", [eq_id])`
   - Feedback inline sous le bouton
   - Refresh scope summary après succès ou succès partiel
8. Click handler global sur `.j2ha-ha-action[data-ha-action="supprimer-recreer"]` :
   - Modale de confirmation forte avec portée globale + compteur publiés
   - Appel `triggerSupprimerAction($button, "global", ["all"])`
   - Feedback global + rafraîchissement
9. Bouton "Supprimer" par ligne pièce (colonne Actions, aux côtés du Republier — bouton `btn-danger`) :
   - Rendu dans `renderPiecePublishButton` ou cellule Actions dédiée
   - Modale de confirmation forte avec nom pièce + nb publiés
   - Appel `triggerSupprimerAction($button, "piece", [piece_id])`
   - Feedback pièce + rafraîchissement

**Contrat de retour backend (obligatoire) :**
```json
{
  "action": "action.execute",
  "status": "ok",
  "payload": {
    "intention": "supprimer",
    "portee": "equipement",
    "resultat": "succes",
    "message": "buanderie plafond — 1 équipement supprimé de Home Assistant.",
    "perimetre_impacte": {"nom": "buanderie plafond", "equipements_publies": 1},
    "scope_reel": {
      "equipements_supprimes": 1,
      "supprimer_errors": 0,
      "skips": 0
    },
    "request_id": "...",
    "timestamp": "..."
  }
}
```

**Règles de calcul de `resultat` :**

| Cas | Condition | `resultat` |
|---|---|---|
| Topology absente | `topology is None` | `"echec"` HTTP 409 |
| Bridge indisponible | `mqtt_bridge.is_connected is False` | `"echec"` HTTP 503 |
| Tout en échec | `supprimer_errors > 0` ET `equipements_supprimes = 0` | `"echec"` HTTP 200 |
| Partiel | `supprimer_errors > 0` ET `equipements_supprimes > 0` | `"succes_partiel"` HTTP 200 |
| Succès | `supprimer_errors = 0` (skips ignorés) | `"succes"` HTTP 200 |

**Règles de message lisible (backend construit, jamais de termes MQTT/topic/retained) :**
- `succes`, `equipements_supprimes > 0` : `"{nom} — {N} équipement(s) supprimé(s) de Home Assistant."`
- `succes`, `equipements_supprimes = 0` (tout était déjà non publié) : `"Configuration déjà à jour dans Home Assistant."`
- `succes_partiel` : `"{equipements_supprimes} supprimé(s), {supprimer_errors} n'ont pas pu être traité(s)."`
- `echec` (bridge) : `"L'action n'a pas pu être exécutée. Vérifiez la connexion Home Assistant."`

**Contrat confirmation forte (modale obligatoire, tous niveaux) :**

La confirmation doit toujours rappeler :
- la portée réelle et le nombre d'équipements concernés
- que l'action est destinée à reconstruire la représentation HA
- les conséquences potentielles côté HA : historique, dashboards, automatisations, `entity_id`
- bouton de confirmation reprenant l'action et la portée : `"Supprimer N équipements"`
- bouton Annuler toujours présent

Exemple (équipement) :
> **Supprimer puis recréer dans Home Assistant**
> Supprimer "buanderie plafond" de Home Assistant.
> Attention : l'historique, les dashboards et les automatisations liés à cette entité peuvent être impactés.
> [Annuler] [Supprimer 1 équipement]

### Out of scope

| Élément hors scope | Responsable |
|---|---|
| Mémorisation du dernier résultat dans le bandeau santé | Story 5.4 |
| Republication automatique après suppression (non atomique) | Story 5.2 déjà implémenté |
| Preview avant/après | Hors V1.1 |

## Acceptance Criteria

**AC1 — Confirmation forte (epic AC)**
**Given** l'utilisateur déclenche "Supprimer puis recréer"
**When** la modale de confirmation s'affiche
**Then** elle rappelle la portée réelle, le volume touché, et les conséquences potentielles sur historique, dashboards, automatisations et `entity_id`

**AC2 — Zone secondaire (epic AC)**
**Given** l'action destructive est affichée dans l'UI
**When** l'utilisateur parcourt le flux normal
**Then** "Supprimer puis recréer" est visuellement distinct de "Republier" (btn-danger rouge, jamais confondu)

**AC3 — Gating bridge (epic AC)**
**Given** le bridge ou MQTT est indisponible
**When** l'utilisateur tente "Supprimer puis recréer"
**Then** l'action est bloquée (bouton disabled + raison visible)

**AC4 — Suppression effective dans HA**
**Given** un équipement inclus et publié dans HA
**When** l'utilisateur clique "Supprimer" et confirme
**Then** l'entité disparaît de Home Assistant et le feedback UI affiche "supprimé" (toast vert ou message inline)

**AC5 — Boucle Supprimer → Créer (validation waiver Story 5.2)**
**Given** un équipement supprimé (AC4 validé)
**When** la home plugin est rafraîchie après la suppression
**Then** le bouton de l'équipement repasse en "Créer" (vert, `est_publie_ha = false`)
**And** un clic sur "Créer" recrée l'entité dans Home Assistant
**And** le feedback UI est lisible (toast vert, message conforme)
**And** le bouton repasse ensuite en "Republier" (bleu) après le refresh

**AC6 — Idempotence (contrat backend)**
**Given** un appel `intention = "supprimer"` sur un équipement déjà non publié
**When** le backend traite la requête
**Then** le résultat est `"succes"` avec message "déjà à jour", 0 erreur, aucun effet parasite

*Note :* l'idempotence est un contrat backend, pas un parcours UX nominal. Après une suppression réussie + refresh, le bouton "Supprimer" devient indisponible (`est_publie_ha = false` → matrice disponibilité Story 5.1), donc l'utilisateur ne peut pas naturellement relancer l'action depuis l'UI. La validation terrain de ce cas s'effectue via un appel API direct, ou dans la fenêtre pré-refresh immédiatement après une suppression.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Backend : remplacement stub `supprimer` (AC: 3, 4, 6)
  - [x] Remplacer le bloc `if intention == "supprimer": return non_implemente` à `http_server.py:1967`
  - [x] Réutiliser `_resolve_eq_ids_for_portee` (aucune modification — existant Story 5.2)
  - [x] Implémenter la boucle unpublish :
    - `_is_currently_published_in_ha` → unpublish ou skip
    - Succès : `publications[eq_id]` mis à jour `discovery_published=False` + nettoyage availability (pattern identique lignes 2173-2186 de http_server.py)
    - Échec : `_defer_discovery_unpublish`
  - [x] Lissage `max(0.1, 10.0 / max(1, N))` entre chaque unpublish
  - [x] Guards topology/bridge identiques à la branche `publier` (409/503)
  - [x] Construire le payload de retour conforme au contrat défini ci-dessus
  - [x] Messages lisibles en français, jamais de termes MQTT/topic/retained

- [x] Task 2 — Frontend équipement : click handler + confirmation forte (AC: 1, 2, 3, 4, 5)
  - [x] Handler sur `.j2ha-action-ha-btn[data-ha-action="supprimer"]`
  - [x] Afficher modale de confirmation forte (portée, conséquences HA)
  - [x] Annuler → aucun appel backend
  - [x] Confirmer → désactiver bouton + spinner → `triggerSupprimerAction($button, "equipement", [eq_id])`
  - [x] Afficher feedback inline sous le bouton
  - [x] Déclencher refresh scope summary si `resultat = "succes"` ou `"succes_partiel"`
  - [x] Ré-activer le bouton à la fin

- [x] Task 3 — Frontend pièce : bouton Supprimer + confirmation forte (AC: 1, 2, 3, 4)
  - [x] Ajouter bouton "Supprimer" `btn-danger` dans la colonne Actions des lignes pièce (aux côtés de "Republier")
  - [x] Le bouton porte `data-ha-action` pour rester sous le gating `applyHAGating`
  - [x] Click → confirmation forte : nom pièce + nb publiés + conséquences HA
  - [x] Appel `triggerSupprimerAction($button, "piece", [piece_id])`
  - [x] Feedback pièce + rafraîchissement scope summary

- [x] Task 4 — Frontend global : click handler + confirmation forte (AC: 1, 2, 3, 4)
  - [x] Handler sur `.j2ha-ha-action[data-ha-action="supprimer-recreer"]` (bouton déjà présent dans `desktop/php/jeedom2ha.php`)
  - [x] Lire le compteur publiés (depuis les données scope summary déjà chargées)
  - [x] Confirmation forte : "Supprimer puis recréer dans Home Assistant — N équipements publiés. Attention : historique, dashboards, automatisations, entity_id peuvent être impactés."
  - [x] Appel `triggerSupprimerAction($button, "global", ["all"])`
  - [x] Feedback global + rafraîchissement

- [x] Task 5 — Tests story-level (AC: 1 à 6)
  - [x] `resources/daemon/tests/unit/test_story_5_3_execute_supprimer.py` :
    - portée `equipement`, eq publié → unpublish, `equipements_supprimes=1`, `resultat="succes"`
    - portée `equipement`, eq déjà non publié → skip, `resultat="succes"`, message "déjà à jour"
    - portée `piece` → boucle sur tous les eq de la pièce
    - portée `global` → boucle sur tous les eq
    - `topology is None` → HTTP 409, message lisible
    - mqtt_bridge déconnecté → HTTP 503, message lisible
    - Échec unpublish → `supprimer_errors=1`, `resultat="echec"` si 0 supprimé, `resultat="succes_partiel"` si partiel
    - `publications[eq_id].discovery_published = False` après suppression réussie
    - Idempotence backend : eq déjà non publié → `resultat="succes"`, 0 erreur (appel API direct, pas via UI post-refresh)
  - [x] `resources/daemon/tests/unit/test_story_5_3_integration.py` :
    - Signal `actions_ha` cohérent après suppression : label bascule "Republier" → "Créer"
    - Contrat 4D, `reason_code`, acquis Epic 4 non altérés
  - [x] `tests/unit/test_story_5_3_frontend.node.test.js` :
    - Click équipement → modale confirmation forte affichée (avec conséquences HA)
    - Annuler → aucun appel backend
    - Confirmer → spinner + appel `triggerSupprimerAction`
    - Feedback `"succes"` → rafraîchissement déclenché
    - Feedback `"succes_partiel"` → rafraîchissement + message partiel
    - Feedback `"echec"` → pas de rafraîchissement, message d'erreur
    - Bouton pièce Supprimer → confirmation forte avec nom pièce
    - Bouton global Supprimer → confirmation forte avec compteur publiés
  - [x] Non-régression : `python3 -m pytest tests resources/daemon/tests -q` → 811 passed, 0 fail ; `node --test tests/unit/*.node.test.js` → 143 pass, 0 fail ; PHP lint PASS

- [x] Task 6 — Gate terrain (bloquant avant done)
  - [x] `deploy-to-box.sh --cleanup-discovery --restart-daemon` : succès
  - [x] Équipement inclus publié → bouton "Supprimer" (rouge) visible et actif
  - [x] Modale de confirmation forte affichée avec portée, conséquences HA
  - [x] Confirmer → entité disparaît de Home Assistant
  - [x] Feedback UI lisible (toast vert, message "supprimé")
  - [x] **[WAIVER 5.2]** Refresh home → bouton repasse en "Créer" (vert)
  - [x] **[WAIVER 5.2]** Clic "Créer" → entité recréée dans HA, `unique_id` conforme
  - [x] **[WAIVER 5.2]** Feedback UI lisible pour Créer (toast vert, message conforme)
  - [x] **[WAIVER 5.2]** Bouton repasse en "Republier" (bleu) après refresh
  - [x] Idempotence backend : appel API direct sur équipement déjà non publié → `resultat="succes"`, message "déjà à jour", 0 erreur (le bouton UI n'est pas accessible dans ce cas post-refresh)
  - [x] Bridge down → bouton Supprimer disabled, aucun appel possible

## Dev Notes

### Contraintes architecturales

1. **Façade unique Story 5.1** — `supprimer` passe par le même `_handle_action_execute` que `publier`. Aucun endpoint dédié.
2. **`_resolve_eq_ids_for_portee` réutilisable sans modification** — existant `http_server.py:154`. Ne pas dupliquer.
3. **Pattern de référence : scope enforcement dans `publier`** (`http_server.py:2135-2200`) — la boucle unpublish est quasi identique à la branche exclu de `publier`. La mise à jour de `publications[eq_id]` avec `discovery_published=False` suit le même pattern (lignes 2173-2186).
4. **Stub à remplacer** : `http_server.py:1967` — bloc `if intention == "supprimer":` retournant `non_implemente`. Ce bloc précède la résolution de topology ; il faut le remplacer par la logique complète (les guards topology/bridge et la résolution des eq_ids sont dans la branche `publier` immédiatement après).
5. **Pas de re-query Jeedom** — utiliser uniquement `app["topology"]`, `app["mappings"]`, `app["publications"]`.
6. **`selection = ["all"]` pour `portée = "global"`** — déjà géré par `_resolve_eq_ids_for_portee`.
7. **Mise à jour de `publications[eq_id]` après unpublish** — obligatoire pour que `est_publie_ha` bascule à `false` et que le label revienne à "Créer" au prochain refresh. Pattern exact : `PublicationDecision(should_publish=False, discovery_published=False, ...)` avec conservation des métadonnées availability (voir lignes 2173-2186 de http_server.py).
8. **Lissage** : `max(0.1, 10.0 / max(1, N))` — identique à `publier`.
9. **`triggerSupprimerAction`** — nouvelle fonction frontend calquée sur `triggerPublierAction` (`jeedom2ha.js:376`), appelle `executeHaAction('supprimer', ...)`.
10. **Bouton global** : `data-ha-action="supprimer-recreer"` (PHP déjà existant, `jeedom2ha.php:67`) — le click handler doit mapper vers `intention: "supprimer"` + `portee: "global"` + `selection: ["all"]`.
11. **Bouton pièce** : pas encore rendu pour Supprimer. À ajouter dans `jeedom2ha_scope_summary.js` dans la zone Actions des lignes pièce (colonne index 4, même cellule que Republier ou cellule adjacente). Doit porter `data-ha-action` pour rester sous `applyHAGating`.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Guardrail — Libellé "Supprimer puis recréer" ≠ opération atomique

- L'action exécutée immédiatement par Story 5.3 est une **suppression uniquement** (`intention = "supprimer"`).
- Aucun feedback de succès ne doit laisser entendre une recréation automatique : le message doit dire "supprimé de Home Assistant", jamais "supprimé et recréé".
- La recréation est une **action utilisateur ultérieure, distincte**, via le bouton `Créer` (Story 5.2). Elle n'est ni déclenchée, ni planifiée, ni implicite dans le flux `supprimer`.
- Le libellé UX "Supprimer puis recréer dans Home Assistant" est une convention de communication vers l'utilisateur (il pourra recréer ensuite) — il ne décrit pas une opération backend atomique.

### Guardrail — Stub `publier` à conserver

Le stub `if intention == "publier": return non_implemente` **n'existe plus** (remplacé par Story 5.2). Seul le stub `supprimer` est à remplacer. Ne jamais toucher à la branche `publier` existante.

### Previous Story Intelligence

**Story 5.2 (`done`) :**
- `_resolve_eq_ids_for_portee` (`http_server.py:154`) — réutiliser sans modification
- Pattern boucle publish (lignes 2068-2200) — la branche scope enforcement (lignes 2135-2200) est le modèle direct pour `supprimer`
- `_is_currently_published_in_ha` — helper existant à réutiliser pour détecter si eq est publié
- `_defer_discovery_unpublish` — helper existant pour échecs unpublish
- `_clear_local_availability_topic` + `_defer_local_availability_cleanup` — helpers existants
- `triggerPublierAction` (`jeedom2ha.js:376`) — modèle exact pour `triggerSupprimerAction`
- `executeHaAction(intention, portee, selection, handlers)` — premier paramètre est l'intention, appeler avec `'supprimer'`
- `showHaActionFeedback`, `shouldRefreshPublishedScopeAfterHaAction`, `setHaActionPendingState` — à réutiliser identiquement
- Baseline non-régression : 0 nouvelle régression sur pytest + JS + PHP exécutables existants (commandes référencées dans Task 5)

**Observation terrain Story 5.2 (UX issues à ne pas réintroduire) :**
- Boutons actifs pour équipements sans mapping ou désactivés → feedback trompeur : veiller à ce que le bouton Supprimer reste grisé quand `est_publie_ha = false` (déjà géré par matrice disponibilité Story 5.1)
- Curseur `pointer` sur boutons disabled : pas critique, mais idéalement `cursor: not-allowed` pour les boutons grisés

**Story 5.1 (`done`) :**
- Matrice de disponibilité `actions_ha.supprimer.disponible` : Supprimer actif ssi `est_publie_ha = true` ET équipement inclus ET bridge disponible. Le frontend lit cette disponibilité sans recalcul local.
- `applyHAGating` (`jeedom2ha.js:133`) — couvre automatiquement tous les éléments portant `[data-ha-action]`.
- Bouton équipement Supprimer (`btn-danger`, `data-ha-action="supprimer"`) : déjà rendu par `renderActionButtons` (`jeedom2ha_scope_summary.js:513`). Pas à re-créer.
- Bouton global Supprimer (`data-ha-action="supprimer-recreer"`) : déjà présent dans `desktop/php/jeedom2ha.php:67`. Click handler manquant.

### Fichiers candidats à la modification

| Couche | Fichier | Modification attendue |
|---|---|---|
| Backend Python | `resources/daemon/transport/http_server.py` | Remplacement stub `"supprimer"` (ligne 1967), boucle unpublish |
| Frontend JS | `desktop/js/jeedom2ha.js` | `triggerSupprimerAction` + click handler global + click handler équipement |
| Frontend JS | `desktop/js/jeedom2ha_scope_summary.js` | Bouton Supprimer ligne pièce + click handler pièce |
| Tests Python | `resources/daemon/tests/unit/test_story_5_3_execute_supprimer.py` | Tests unitaires backend |
| Tests Python | `resources/daemon/tests/unit/test_story_5_3_integration.py` | Tests d'intégration |
| Tests JS | `tests/unit/test_story_5_3_frontend.node.test.js` | Tests confirmations, handlers, feedback |

### Données terrain

- Topic discovery : `homeassistant/{entity_type}/jeedom2ha_eq_{eq_id}/config`
- Vérifier suppression : `mosquitto_sub -t "homeassistant/+/jeedom2ha_eq_+/config" -v` — le topic ne doit plus apparaître (retained cleared)
- Vérifier availability cleared : `mosquitto_sub -t "jeedom2ha/+/availability" -v`
- Vérifier recréation (boucle waiver 5.2) : même topic config → nouveau payload attendu

### Invariants à couvrir (non-régression)

- **I4** — Backend source unique du contrat `actions_ha` et des 4 dimensions.
- **I5** — Action positive (`publier`) non destructive — ne pas altérer la branche `publier` existante.
- **I7** — Séparation scope local vs application HA.
- **I9** — `unique_id` stable, recalcul scope déterministe.
- **I10** — Contrat backend → UI 4D consommé sans interprétation locale.
- **I17** — Frontend en lecture seule pour le calcul de portée et de scope.

### References

- [Source: `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md#Story 5.3`] — AC canoniques et dépendances
- [Source: `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md#§7.3`] — confirmation forte Supprimer
- [Source: `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md#§7.4`] — contenu minimum confirmation à impact fort
- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md#§7.3`] — sémantique `Supprimer/Recreer`
- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md#§7.4`] — orchestration multi-portée
- [Source: `_bmad-output/implementation-artifacts/5-2-flux-positif-contextuel-creer-republier-multi-portee.md#Gate terrain 2026-04-07`] — waiver checkpoint Créer individuel → report vers 5.3
- [Source: `resources/daemon/transport/http_server.py:154`] — `_resolve_eq_ids_for_portee` (réutiliser)
- [Source: `resources/daemon/transport/http_server.py:1967`] — stub `supprimer` (à remplacer)
- [Source: `resources/daemon/transport/http_server.py:2135`] — pattern scope enforcement / unpublish (modèle)
- [Source: `desktop/js/jeedom2ha.js:329`] — `executeHaAction` (réutiliser)
- [Source: `desktop/js/jeedom2ha.js:376`] — `triggerPublierAction` (modèle pour `triggerSupprimerAction`)
- [Source: `desktop/js/jeedom2ha_scope_summary.js:497`] — `renderActionButtons` (bouton Supprimer déjà rendu équipement)
- [Source: `desktop/php/jeedom2ha.php:67`] — bouton global `data-ha-action="supprimer-recreer"` (click handler manquant)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Test 5.2 `doesNotMatch(j2ha-piece-action-btn)` : adapté pour cibler spécifiquement `data-ha-action="publier"` après ajout bouton Supprimer pièce
- Gate terrain bug 1 : bouton Supprimer rendu disabled au lieu de masqué quand `disponible=false` → cohabitation Créer+Supprimer
- Gate terrain bug 2 : boutons pièce Republier+Supprimer passaient sur 2 lignes (pas de conteneur flex)
- Gate terrain bug 3 : duplication du nom dans le message (backend + frontend concat)

### Completion Notes List

- Task 1 : stub `supprimer` remplacé par boucle unpublish complète avec `_build_supprimer_message`, guards partagés, lissage, mise à jour publications
- Task 2 : `triggerSupprimerAction` + `confirmHaSupprimerAction` (btn-danger) + click handler équipement avec confirmation forte
- Task 3 : `renderPieceSupprimerButton` ajouté dans scope summary, click handler pièce avec confirmation forte
- Task 4 : click handler global `supprimer-recreer` → `triggerSupprimerAction('global', ['all'])`, `data-scope-publies` alimenté par `renderPublishedScopeSummary`
- Task 5 : 13 tests backend (unit), 3 tests intégration (dont round-trip Supprimer→Créer), 12 tests frontend JS. 811 pytest + 145 JS + PHP lint = 0 régression.
- Bug 1 fix : `renderActionButtons` ne rend plus le bouton Supprimer quand `disponible=false` (masqué, pas disabled)
- Bug 2 fix : `renderPieceActionButtons` wrapper flex + libellé abrégé "Suppr." pour compacité pièce
- Bug 3 fix : `_build_supprimer_message` ne contient plus le nom (évite duplication avec `buildHaActionUserMessage`)
- ✅ Résolution code review M2 (2026-04-08) : ajout `entity_id` dans les 3 textes de confirmation forte (équipement, pièce, global) + assertions JS correspondantes — 145/145 JS PASS, 798/798 pytest PASS
- Note M1 (2026-04-08) : les fichiers `resources/daemon/models/actions_ha.py`, `desktop/css/jeedom2ha.css`, `resources/daemon/tests/unit/test_story_5_6_actions_ha_disponibilite.py` et `_bmad-output/implementation-artifacts/5-6-coherence-visuelle-disabled-boutons-ha.md` présents dans le worktree appartiennent à Story 5.6 (déjà `done` en sprint). Ils sont à commiter séparément dans le contexte Story 5.6, pas dans le commit Story 5.3.

### File List

- `resources/daemon/transport/http_server.py` — branche `supprimer` + `_build_supprimer_message` (sans nom)
- `desktop/js/jeedom2ha.js` — `triggerSupprimerAction`, `confirmHaSupprimerAction`, click handlers équipement/pièce/global, `data-scope-publies`
- `desktop/js/jeedom2ha_scope_summary.js` — `renderPieceSupprimerButton` (libellé "Suppr."), `renderPieceActionButtons` (wrapper flex), bouton Supprimer masqué quand `disponible=false`
- `resources/daemon/tests/unit/test_story_5_3_execute_supprimer.py` — 13 tests unitaires backend
- `resources/daemon/tests/unit/test_story_5_3_integration.py` — 3 tests intégration (label switch, 4D contract, round-trip)
- `tests/unit/test_story_5_3_frontend.node.test.js` — 12 tests frontend JS
- `tests/unit/test_story_5_2_frontend.node.test.js` — ajustement mineur assertion `doesNotMatch`
- `tests/unit/test_story_5_1_actions_ha_frontend.node.test.js` — adaptations tests pour bouton Supprimer masqué (non disabled)
