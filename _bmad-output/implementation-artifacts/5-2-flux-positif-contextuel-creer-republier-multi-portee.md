# Story 5.2 : Flux positif contextuel — Créer / Republier multi-portée

Status: done

> **Merge closeout 2026-04-06** — PR #67 squash-merged dans `main` (commit `8d60a02`).
> Code review final : PASS. Gate terrain : **exécuté 2026-04-07** — 6 PASS, 1 NOT EXECUTED (waiver assumé).
> Story clôturée à `done` avec note de clôture et waiver explicites.

## Story

En tant qu'utilisateur Jeedom,
je veux pouvoir déclencher l'action "Créer" ou "Republier" depuis la console home (global / pièce / équipement) et obtenir immédiatement un retour lisible sur ce qui a été appliqué,
afin d'appliquer mon périmètre dans Home Assistant sans crainte excessive et de constater le résultat sans quitter la page.

## Contexte / Objectif produit

Cette story implémente l'exécution réelle de l'intention `publier` dans la façade backend unique posée par la Story 5.1. Elle est la suite directe de Story 5.5 qui a rendu les boutons visuellement cliquables (libellés courts, repositionnement colonne).

L'objectif produit est double :

1. **Exécution backend réelle** — remplacer le stub `non_implemente` par la republication MQTT Discovery effective, non destructive et idempotente.
2. **Boucle UX complète et contractuelle** — l'utilisateur déclenche l'action, voit un état intermédiaire, reçoit un retour lisible (succès / partiel / échec), et retrouve les compteurs et écarts mis à jour dans la table.

La promesse produit de `Publier` est :
- **non destructive** : aucune entité HA n'est supprimée pour les équipements inclus
- **idempotente** : relancer la même action donne le même résultat sans effet secondaire
- **prévisible** : l'utilisateur sait ce qui a été appliqué, sur quel périmètre, avec quel résultat

**Sémantique canonique :**
- **Label utilisateur contextuel** = `"Créer"` (bouton vert, équipement non encore publié) ou `"Republier"` (bouton bleu, équipement déjà publié). Ce label est piloté par `est_publie_ha` via le signal `actions_ha` (Story 5.1). Il est affiché en court via `shortLabel()` (Story 5.5).
- **Intention backend canonique** = `publier` dans tous les cas. La façade ne distingue pas "créer" de "republier" — ce sont deux résultats du même flux publish MQTT Discovery idempotent.
- Ces deux niveaux ne doivent jamais être confondus dans l'implémentation ni dans les tests.

L'exécution de `supprimer` (dépublication standalone) reste Story 5.3. La mémorisation durable du dernier résultat dans le bandeau de santé reste Story 5.4.

## Scope

### In scope

**Backend :**
1. Remplacement du stub `non_implemente` pour `intention = "publier"` dans `_handle_action_execute` (`http_server.py:1735`)
2. Résolution de portée : `_resolve_eq_ids_for_portee(portee, selection, topology)` → `List[int]`
   - `equipement` : `selection = [eq_id, ...]`
   - `piece` : `selection = [piece_id]` → tous les `eq_id` de la pièce depuis `topology`
   - `global` : `selection = ["all"]` → tous les `eq_id` de `topology`
3. Pour chaque `eq_id` résolu :
   - Inclus + mappé → `publisher.publish_light/cover/switch(mapping, topology)` (republication idempotente) ; incrémenter `equipements_publies_ou_crees` si succès, `publish_errors` si échec MQTT
   - Exclu + encore publié (`publications[eq_id].discovery_published = True`) → unpublish + cleanup availability (scope enforcement, résolution écart direction 2) ; incrémenter `ecarts_resolus`
   - Inclus mais mapping absent ou ambigu → **skip attendu** ; incrémenter `skips`

   **Définition du skip :** un skip est attendu quand l'équipement inclus dans la portée n'a pas de mapping valide (type ambigu, erreur de mapping pré-existante). Le skip est **transparent pour le calcul de `resultat`** : il n'entraîne jamais `succes_partiel` seul. Seuls les échecs de publish MQTT (`publish_errors > 0`) dégradent le résultat. Il n'existe pas de "skip inattendu" dans cette story — tout skip reflète un état pré-existant du mapping.

   **Définition de `equipements_publies_ou_crees` :** nombre d'équipements pour lesquels l'appel `publisher.publish_*` a retourné succès. Inclut indifféremment les premières créations (équipement non encore dans HA) et les republications (entité HA existante mise à jour). Le nom reflète cette dualité Créer / Republier — l'opération MQTT est identique dans les deux cas.
4. Lissage : `max(0.1, 10.0 / max(1, N))` entre chaque publish
5. Gate `topology is None` → HTTP 409 + message lisible
6. Payload de retour structuré (voir contrat ci-dessous)

**Frontend (JS) :**
7. Click handler équipement sur `.j2ha-action-ha-btn[data-ha-action="publier"]` :
   - Désactiver le bouton + afficher spinner pendant l'appel
   - `niveau_confirmation = "aucune"` → appel direct sans modale
   - Afficher le retour dans un feedback inline sous le bouton
   - Rafraîchir le scope summary après succès ou succès partiel
8. Click handler global sur `.j2ha-ha-action[data-ha-action="republier"]` :
   - Confirmation explicite : "Republier dans Home Assistant — X équipements inclus. Confirmer ?"
   - Appel `executeHaAction` avec `portee: "global", selection: ["all"]`
   - Feedback global + rafraîchissement
9. Bouton "Republier" par ligne pièce dans le scope summary (colonne Actions, position 5 post-Story 5.5) :
   - Confirmation légère : nom pièce + nb équipements inclus
   - Appel `executeHaAction` avec `portee: "piece", selection: [piece_id]`
   - Feedback pièce + rafraîchissement

**Contrat de retour backend (obligatoire) :**
```json
{
  "action": "action.execute",
  "status": "ok",
  "payload": {
    "intention": "publier",
    "portee": "piece",
    "resultat": "succes",
    "message": "12 équipements mis à jour dans Home Assistant.",
    "perimetre_impacte": {"nom": "Salon", "equipements_inclus": 12},
    "scope_reel": {
      "equipements_inclus": 12,
      "equipements_publies_ou_crees": 12,
      "ecarts_resolus": 2,
      "skips": 0
    },
    "aucun_flux_supprimer_recree": true,
    "request_id": "...",
    "timestamp": "..."
  }
}
```

**Règles de calcul de `resultat` (implémentation sans ambiguïté) :**

| Cas | Condition | `resultat` |
|---|---|---|
| topology None | `app["topology"] is None` | `"echec"` → HTTP 409 |
| Bridge indisponible (garde-fou) | `mqtt_bridge.is_connected is False` au moment de l'exécution | `"echec"` → HTTP 503 |
| 100% d'échecs publish | `publish_errors > 0` ET `equipements_publies_ou_crees = 0` | `"echec"` → HTTP 200 |
| Succès partiel | `publish_errors > 0` ET `equipements_publies_ou_crees > 0` | `"succes_partiel"` → HTTP 200 |
| Succès complet (incl. 0 changement) | `publish_errors = 0` (skips ignorés) | `"succes"` → HTTP 200 |

Note : le cas `equipements_publies_ou_crees = 0` et `publish_errors = 0` (tout déjà à jour, aucun skip-erreur) est un **succès idempotent valide** (`resultat = "succes"`). Ce n'est pas une erreur.

**Messages lisibles (non techniques — pas de MQTT/payload/topic) :**
- `succes`, `equipements_publies_ou_crees > 0` : `"X équipements mis à jour dans Home Assistant."`
- `succes`, `equipements_publies_ou_crees = 0` (idempotent) : `"Configuration déjà à jour dans Home Assistant."`
- `succes_partiel` : `"X équipements mis à jour, Y n'ont pas pu être traités."`
- `echec`, topology None : `"Aucune synchronisation disponible. Lancez une synchronisation d'abord."`
- `echec`, bridge ou autre : `"L'action n'a pas pu être exécutée. Vérifiez la connexion Home Assistant."`

**Non-régression :**
10. 228 pytest + 125 JS + 7 PHP = 360 tests existants → 0 régression (baseline post-Story 5.5)
11. Stub `non_implemente` conservé uniquement pour `intention = "supprimer"` (Story 5.3)

### Out of scope

| Élément hors scope | Responsable |
|---|---|
| Exécution de `supprimer` (dépublication standalone intentionnelle) | Story 5.3 |
| Confirmations fortes pour `Supprimer puis recréer` | Story 5.3 |
| Mémorisation durable du dernier résultat dans le bandeau de santé | Story 5.4 |
| Retour d'opération persisté entre sessions | Story 5.4 |
| Rescan complet topologie Jeedom dans le cadre de Publier | Hors scope — c'est `/action/sync` |
| Preview complète avant/après, extension fonctionnelle | Hors V1.1 |
| Toute logique métier côté frontend | Invariant architectural |
| Réouverture du modèle 4D ou des `reason_code` | Acquis Epic 3/4 |

## Dépendances autorisées

- **Story 5.1** — `done` : façade `POST /action/execute`, signal `actions_ha`, stub `non_implemente`, `DiscoveryPublisher`, relay PHP `executeHaAction`.
- **Story 5.5** — `review` (**PRÉCONDITION DE MISE EN ŒUVRE**) : l'implémentation de Story 5.2 suppose que Story 5.5 est mergée dans `main`. L'état attendu : `shortLabel()` présent dans `jeedom2ha_scope_summary.js`, `renderActionButtons()` avec `btn-primary` pour Republier, `pieceColumns[]` avec placeholder Actions à l'**index 4** (pas 9), baseline JS à **125 tests** (pas 120). Toute implémentation de Story 5.2 avant le merge de Story 5.5 produira des conflits sur `pieceColumns` et une baseline de tests incorrecte.
- **Story 1.4** — `done` : `has_pending_home_assistant_changes` dans le contrat de scope.
- **Story 2.3** — `done` : gating des actions HA selon la santé du pont.

## Acceptance Criteria

### AC 1 — Flux `publier` strictement non destructif pour les équipements inclus

**Given** une intention `publier` sur n'importe quelle portée
**When** l'exécution backend se termine
**Then** aucun équipement inclus n'a été supprimé de Home Assistant
**And** les entités HA des équipements inclus ont le même `unique_id` qu'avant l'action (`jeedom2ha_eq_{eq_id}`)
**And** le payload de retour contient `"aucun_flux_supprimer_recree": true`
**And** aucun log backend ne trace d'`unpublish` sur un équipement inclus

### AC 2 — Idempotence

**Given** une opération `publier` réussie sur une portée donnée
**When** la même opération est relancée immédiatement (même portée, même sélection)
**Then** le résultat est `succes` avec `equipements_publies_ou_crees` ≥ 0 et `ecarts_resolus = 0`
**And** aucune entité HA n'est supprimée ou dupliquée
**And** les compteurs de la table home restent cohérents

### AC 3 — Payload de retour auditable

**Given** une demande `publier` quelle que soit la portée
**When** le backend retourne le résultat
**Then** le payload contient `intention = "publier"`, `portee`, `resultat` (succes / succes_partiel / echec)
**And** `scope_reel` est présent avec `equipements_inclus`, `equipements_publies_ou_crees`, `ecarts_resolus`, `skips`
**And** `aucun_flux_supprimer_recree: true` est présent
**And** `message` est lisible non technique

### AC 4 — Feedback utilisateur visible et lisible

**Given** l'utilisateur clique sur un bouton d'action positive (équipement, pièce ou global)
**When** l'appel backend retourne
**Then** un message lisible s'affiche dans la console home sans rechargement de page
**And** le message indique le résultat (succès / partiel / échec) en termes métier (pas de MQTT, topic, payload)
**And** le message indique le périmètre impacté (nombre d'équipements ou nom de pièce)
**And** ce message n'est jamais implicite ou silencieux

### AC 5 — Boucle UX complète et déterministe

**Given** l'utilisateur clique sur un bouton d'action positive
**When** l'appel est en cours
**Then** le bouton est désactivé (disabled) et un indicateur visuel d'attente est affiché (spinner ou texte)
**And** les autres boutons de la même ligne restent dans leur état courant (pas de freeze global)

**When** la réponse est reçue (succès ou erreur)
**Then** le message de retour s'affiche
**And** la table home est rafraîchie (compteurs, écarts mis à jour)
**And** le bouton est ré-activé si disponible selon la nouvelle matrice `actions_ha`

**Given** un équipement venant d'être créé dans HA (`succes`, était `est_publie_ha=false`)
**When** la table home est rafraîchie
**Then** le bouton passe de `"Créer"` (vert) à `"Republier"` (bleu) sans rechargement de page complet

### AC 6 — Confirmations graduées selon la portée

**Given** l'utilisateur clique sur le bouton équipement (`niveau_confirmation = "aucune"`)
**When** le clic est détecté
**Then** l'action est déclenchée directement, sans modale intermédiaire

**Given** l'utilisateur clique sur "Republier la pièce"
**When** la confirmation s'affiche
**Then** elle rappelle le nom de la pièce et le nombre d'équipements inclus
**And** elle propose un bouton de confirmation clair (ex: "Republier 12 équipements")

**Given** l'utilisateur clique sur le bouton global "Republier dans Home Assistant"
**When** la confirmation s'affiche
**Then** elle rappelle la portée globale et le nombre total d'équipements inclus
**And** elle propose un bouton de confirmation (ex: "Republier X équipements")

### AC 7 — Écarts direction 2 résolus après Republier

**Given** des équipements exclus mais encore publiés dans HA (`has_pending_home_assistant_changes = true`)
**When** `publier` se termine avec succès sur la portée concernée
**Then** ces équipements sont dépubliés de HA (unpublish MQTT — scope enforcement)
**And** `scope_reel.ecarts_resolus` reflète le nombre d'équipements dépubliés
**And** la table home rafraîchie n'affiche plus d'écart pour ces équipements
**And** cette résolution n'est pas présentée comme destructive dans le message

### AC 8 — Gestion des cas limites

**Niveau 1 — Comportement nominal frontend (bridge down) :**

**Given** le bridge ou MQTT est indisponible
**When** l'utilisateur est sur la console home
**Then** les boutons d'action sont désactivés par `applyHAGating` (`jeedom2ha.js:126`)
**And** le click handler n'est jamais déclenché (bouton `disabled`)
**And** aucun appel `executeHaAction` n'est émis

**Niveau 2 — Garde-fou backend (appel reçu malgré gating) :**

**Given** un appel `POST /action/execute` parvient au backend avec `intention = "publier"`
**When** le backend détecte que `mqtt_bridge.is_connected is False` avant l'exécution
**Then** la façade retourne HTTP 503 avec `resultat = "echec"` et `message = "L'action n'a pas pu être exécutée. Vérifiez la connexion Home Assistant."`
**And** aucun publish n'est tenté

*Note : le Niveau 1 est le chemin nominal. Le Niveau 2 est un garde-fou défensif pour les cas de race condition ou d'appel direct à la façade.*

**Given** l'appel backend retourne une erreur 409 (topology None)
**When** le frontend reçoit l'erreur
**Then** le message affiché est : "Aucune synchronisation disponible. Lancez une synchronisation d'abord."
**And** le bouton est ré-activé

**Given** l'opération `publier` se termine sans modification (0 publié, 0 écart résolu)
**When** le résultat est affiché
**Then** `resultat = "succes"` et le message est : "Configuration déjà à jour dans Home Assistant."
**And** aucun écart n'est créé artificiellement

**Given** une opération `publier` en succès partiel (au moins 1 échec)
**When** le résultat est affiché
**Then** `resultat = "succes_partiel"` et le message précise le nombre de succès et d'échecs
**And** la table home est quand même rafraîchie pour refléter les équipements traités avec succès

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.`
  - Tentatives exécutées le `2026-04-06` : bloquées avant déploiement car `JEEDOM_BOX_HOST` n'est pas défini dans l'environnement local.

- [x] Task 1 — Backend : implémentation de l'exécution `publier` (AC: 1, 2, 3, 7)
  - [x] Extraire `_resolve_eq_ids_for_portee(portee, selection, topology)` → `List[int]`
    - `portee = "equipement"` : cast chaque élément de `selection` en `int`
    - `portee = "piece"` : résoudre les `eq_id` de la pièce depuis `topology`
    - `portee = "global"` : tous les `eq_id` de `topology`
    - `portee = "piece"` + piece_id inconnue → HTTP 400 avec message lisible
  - [x] Gate `topology is None` → HTTP 409 + message `"Aucune synchronisation disponible — appelez /action/sync d'abord."`
  - [x] Boucle d'exécution pour chaque `eq_id` résolu :
    - Inclus + mappé → `publisher.publish_light/cover/switch(mapping, topology)` ; incrémenter `equipements_publies_ou_crees`
    - Exclu + `publications[eq_id].discovery_published = True` → unpublish + cleanup availability ; incrémenter `ecarts_resolus`
    - Inclus mais mapping absent/ambigu → skip ; incrémenter `skips`
  - [x] Lissage `max(0.1, 10.0 / max(1, N))` entre chaque publish
  - [x] Calculer `resultat` : `"succes"` / `"succes_partiel"` / `"echec"` selon les compteurs
  - [x] Construire `message` lisible (non technique, voir contrat)
  - [x] Payload retour complet : `intention`, `portee`, `resultat`, `message`, `perimetre_impacte`, `scope_reel`, `aucun_flux_supprimer_recree: True`, `request_id`, `timestamp`
  - [x] Conserver stub `"non_implemente"` pour `intention = "supprimer"` (Story 5.3 inchangée)

- [x] Task 2 — Frontend : click handler équipement (AC: 5, 6)
  - [x] Handler sur `#div_scopeSummaryContent` click `.j2ha-action-ha-btn[data-ha-action="publier"]`
  - [x] `niveau_confirmation = "aucune"` → appel direct sans modale
  - [x] Désactiver le bouton + afficher spinner (ou texte "...") pendant l'appel
  - [x] Appel `executeHaAction(eqId, "equipement")`
  - [x] Afficher le `message` du payload sous le bouton (ou toast)
  - [x] En cas de succès ou succès_partiel : déclencher le rafraîchissement du scope summary
  - [x] Ré-activer le bouton à la fin (succès ou erreur)

- [x] Task 3 — Frontend : bouton pièce + confirmation légère (AC: 5, 6)
  - [x] Ajouter le bouton "Republier" dans `pieceColumns` à l'**index 4** (post-Story 5.5 — colonne Actions en position 5)
  - [x] Le bouton porte `data-ha-action` pour le gating automatique (`applyHAGating`)
  - [x] Click → confirmation légère : nom pièce + nb équipements inclus + bouton "Republier X équipements"
  - [x] Appel `executeHaAction(pieceId, "piece")`
  - [x] Afficher le `message` du retour + rafraîchissement scope summary

- [x] Task 4 — Frontend : confirmation explicite global (AC: 5, 6)
  - [x] Handler sur `.j2ha-ha-action[data-ha-action="republier"]` (bouton global dans `desktop/php/jeedom2ha.php`)
  - [x] Confirmation : "Republier dans Home Assistant — X équipements inclus" + bouton "Republier X équipements"
  - [x] Appel `executeHaAction("all", "global")`
  - [x] Afficher le `message` du retour + rafraîchissement scope summary

- [x] Task 5 — Tests story-level (AC: 1 à 8)
  - [x] `resources/daemon/tests/unit/test_story_5_2_execute_publier.py` :
    - portée `equipement`, eq inclus non publié → publish, `equipements_publies_ou_crees = 1`, `resultat = "succes"`
    - portée `equipement`, eq inclus déjà publié → republish idempotent, `resultat = "succes"`
    - portée `equipement`, eq exclu encore publié → unpublish, `ecarts_resolus = 1`, `resultat = "succes"`
    - portée `piece` → boucle sur tous les eq de la pièce
    - portée `global` → boucle sur tous les eq
    - `topology is None` → HTTP 409, message lisible
    - 0 changement (tout déjà à jour) → `resultat = "succes"`, message "déjà à jour"
    - succès partiel (1 échec, 1 succès) → `resultat = "succes_partiel"`, message précis
    - `aucun_flux_supprimer_recree: True` présent dans tous les payloads `publier`
    - `unique_id` inchangé dans le discovery republié
  - [x] `resources/daemon/tests/unit/test_story_5_2_integration.py` :
    - Signal `actions_ha` cohérent après republication (label bascule Créer → Republier)
    - Scope enforcement terrain simulé : eq exclu + publié → unpublish déclenché
    - Contrat 4D, `reason_code`, acquis Epic 4 non altérés
  - [x] `tests/unit/test_story_5_2_frontend.node.test.js` :
    - Click équipement → pas de modale si `niveau_confirmation = "aucune"`
    - Click pièce → confirmation légère avec compteur
    - Click global → confirmation explicite avec compteur
    - Bouton disabled + spinner pendant l'appel
    - Message `"succes"` → rafraîchissement déclenché
    - Message `"succes_partiel"` → rafraîchissement déclenché + message partiel affiché
    - Message `"echec"` → pas de rafraîchissement, message d'erreur affiché
    - Aucune logique locale de calcul de portée ou de scope
  - [x] Non-régression : 782 pytest + 133 JS + 3 PHP exécutables PASS ; 3 scripts PHP supplémentaires restent bloqués par l'absence du bootstrap Jeedom local.

- [x] Task 6 — Gate terrain (exécuté 2026-04-07 — voir section Gate terrain ci-dessous)
  - [x] Déploiement sur box canonique : effectué manuellement (JEEDOM_BOX_HOST non défini en local)
  - [x] Bouton "Republier dans Home Assistant" (global) → 30 équipements republiés, toast vert conforme
  - [~] Équipement inclus non publié → bouton "Créer" (vert) → clic → entité créée dans HA : **NOT EXECUTED** — waiver assumé (voir note de clôture)
  - [x] Équipement inclus déjà publié → bouton "Republier" (bleu) → clic → entité mise à jour, aucun doublon HA
  - [x] Scope enforcement : exclure pièce Buanderie → entités disparaissent de HA, 0 écarts résiduels
  - [x] Idempotence : relancer la même action → succes, 0 erreur, table inchangée
  - [x] Bridge down simulé (arrêt mosquitto) → boutons disabled, aucun appel possible
  - [x] Messages lisibles affichés côté console pour chaque cas

## Dev Notes

### Contraintes architecturales

1. **Pas de re-query Jeedom** — `publier` utilise uniquement l'état en mémoire : `app["topology"]`, `app["mappings"]`, `app["publications"]`. Jamais `getFullTopology()`. C'est ce qui le distingue de `/action/sync`.
2. **Pattern de référence : `_republish_all_from_cache`** (`http_server.py:325`) — la boucle est quasi identique mais scoped sur la sélection résolue. Factoriser si possible plutôt que dupliquer.
3. **Scope enforcement** : un équipement est "encore publié" si `publications[eq_id].discovery_published is True`. L'unpublish utilise `publisher.unpublish_by_eq_id(eq_id, entity_type=decision.mapping_result.ha_entity_type)` + nettoyage `pending_local_availability_cleanup`.
4. **`selection = ["all"]` pour `portée = "global"`** — sentinel accepté, résolu sur l'intégralité de `topology`. La validation existante (liste non vide) est compatible.
5. **`message` lisible** — construit côté backend depuis les compteurs. Jamais de termes MQTT/payload/topic/retained dans le message. Les messages sont en français.
6. **`resultat`** — calculé en priorité décroissante (voir table complète dans la section Scope) :
   - `topology is None` → `"echec"` HTTP 409 (avant toute exécution)
   - `mqtt_bridge.is_connected is False` → `"echec"` HTTP 503 (garde-fou backend)
   - `publish_errors > 0` ET `equipements_publies_ou_crees = 0` → `"echec"` HTTP 200
   - `publish_errors > 0` ET `equipements_publies_ou_crees > 0` → `"succes_partiel"` HTTP 200
   - `publish_errors = 0` (skips ignorés, `equipements_publies_ou_crees` ≥ 0) → `"succes"` HTTP 200
   - Les `skips` n'entrent jamais dans le calcul de `resultat`.
7. **Rafraîchissement post-action** — appeler la même fonction que `#bt_refreshScopeSummary`. Pas de re-architecture du polling.
8. **Gating des boutons pièce** — ils doivent porter `data-ha-action` (peut être `"piece-republier"` ou `"publier"`) pour être couverts par `applyHAGating` (`jeedom2ha.js:126`).

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Previous Story Intelligence

**Story 5.1 (`done`) :**
- Stub à remplacer : `_handle_action_execute` (`http_server.py:1735`) — `resultat: "non_implemente"` pour les deux intentions. Story 5.2 remplace uniquement `"publier"`. Le stub `"supprimer"` reste intact.
- `renderActionButtons` (`jeedom2ha_scope_summary.js:486`) — boutons déjà rendus avec `data-ha-action="publier"` et `data-eq-id`. Click handler manquant.
- `executeHaAction` relay PHP (`core/ajax/jeedom2ha.ajax.php:584`) — relay existant, aucune modification PHP attendue.
- `applyHAGating` (`jeedom2ha.js:126`) — gating automatique sur `[data-ha-action]`. Les boutons pièce doivent porter cet attribut.

**Story 5.5 (`review`) — PRÉCONDITION : l'implémentation commence après le merge de Story 5.5**
- `shortLabel()` helper dans `jeedom2ha_scope_summary.js` — labels courts affichés, `data-ha-action` inchangé à `"publier"`.
- `renderActionButtons()` : Republier = `btn-primary` (bleu).
- `pieceColumns[]` : placeholder Actions à l'**index 4** (pas 9). Le bouton pièce de Story 5.2 doit être inséré à cet index.
- Baseline JS : **125 tests** (pas 120). Toute vérification de non-régression utilise 125 comme base.
- Si Story 5.5 n'est pas mergée : arrêter, merger 5.5, puis reprendre 5.2.

**Basculement label Créer → Republier :**
- Après une première publication réussie, le backend bascule `est_publie_ha = true`. Le label bascule (Créer → Republier, vert → bleu) lors du rafraîchissement de `/system/diagnostics`. C'est le rafraîchissement scope summary post-action qui déclenche ce rechargement.

### Fichiers candidats à la modification

| Couche | Fichier | Modification attendue |
|---|---|---|
| Backend Python | `resources/daemon/transport/http_server.py` | Remplacement stub `"publier"`, fonction `_resolve_eq_ids_for_portee`, boucle publish |
| Frontend JS | `desktop/js/jeedom2ha.js` | Click handlers global + équipement |
| Frontend JS | `desktop/js/jeedom2ha_scope_summary.js` | Bouton pièce à l'index 4 (post-5.5) |
| Tests Python | `resources/daemon/tests/unit/test_story_5_2_execute_publier.py` | Tests unitaires backend |
| Tests Python | `resources/daemon/tests/unit/test_story_5_2_integration.py` | Tests d'intégration |
| Tests JS | `tests/unit/test_story_5_2_frontend.node.test.js` | Tests confirmations, handlers, feedback |

### Données terrain pour les tests

- Topic discovery : `homeassistant/{entity_type}/jeedom2ha_eq_{eq_id}/config`
- Topic availability : `jeedom2ha/{eq_id}/availability`
- `mosquitto_sub -t "homeassistant/+/jeedom2ha_eq_+/config" -v` — vérifier les payloads republied
- `mosquitto_sub -t "jeedom2ha/+/availability" -v` — vérifier l'availability après scope enforcement

### Invariants à couvrir (non-régression)

- **I4** — Backend source unique du contrat `actions_ha` et des 4 dimensions.
- **I5** — Action positive (`publier`) non destructive par contrat pour les inclus.
- **I7** — Séparation scope local vs application HA.
- **I9** — `unique_id` stable, recalcul scope déterministe.
- **I10** — Contrat backend → UI 4D consommé sans interprétation locale.
- **I17** — Frontend en lecture seule pour le calcul de portée et de scope.

### References

- [Source: `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md#Story 5.2`] — AC canoniques et dépendances
- [Source: `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md#§7.2`] — matrice de confirmation graduée
- [Source: `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md#§7.5`] — "Republier la pièce"
- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md#§7.2`] — façade unique, portée = paramètre
- [Source: `_bmad-output/implementation-artifacts/5-1-facade-backend-unique-et-contrat-de-disponibilite-des-actions.md#Guardrails anti-dérive`] — stubs à conserver pour 5.3
- [Source: `_bmad-output/implementation-artifacts/5-5-compacite-visuelle-table-home-colonne-actions.md#Coordination avec Story 5.2`] — index 4, merge order
- [Source: `resources/daemon/transport/http_server.py:325`] — `_republish_all_from_cache` (pattern de référence)
- [Source: `resources/daemon/transport/http_server.py:1735`] — `_handle_action_execute` (stub à remplacer)
- [Source: `desktop/js/jeedom2ha.js:126`] — `applyHAGating`
- [Source: `desktop/js/jeedom2ha_scope_summary.js:486`] — `renderActionButtons` (click handler manquant)

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- `python3 -m pytest tests resources/daemon/tests -q` → `782 passed`
- `node --test tests/unit/*.node.test.js` → `133 passed`
- `php tests/test_php_export_diagnostic_coherence.php` → PASS
- `php tests/test_php_story_4_5_home_signals.php` → PASS
- `php tests/unit/test_story_5_1_php_relay.php` → PASS
- `php tests/test_php_published_scope_relay.php` / `tests/test_php_topology_extraction.php` / `tests/test_runtime_bootstrap_startup.php` → bloqués par l'absence de `core/php/core.inc.php`
- `./scripts/deploy-to-box.sh --dry-run` / `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → bloqués car `JEEDOM_BOX_HOST` n'est pas défini

### Completion Notes List

- Stub `publier` remplacé dans `http_server.py` avec résolution de portée, boucle publish/unpublish, calcul de résultat, message lisible et compatibilité avec le wrapper PHP `{payload: ...}`.
- Le backend reste la source unique de vérité : aucun re-query Jeedom, `published_scope` et `publications` sont réappliqués et persistés après action.
- Le frontend exécute uniquement des handlers : action directe pour l'équipement, confirmation légère pour la pièce, confirmation explicite pour le global, spinner local, feedback lisible et refresh de la home.
- Le bouton pièce est maintenant rendu à l'index Actions attendu post-Story 5.5 et porte `data-ha-action` pour rester sous le gating existant.
- Une suite story-level dédiée a été ajoutée pour le backend unitaire, l'intégration backend et le frontend JS.
- Le gate terrain a été tenté mais reste bloqué par l'environnement local ; la story est prête pour review, pas pour `done`.

### File List

- `resources/daemon/transport/http_server.py`
- `desktop/js/jeedom2ha.js`
- `desktop/js/jeedom2ha_scope_summary.js`
- `resources/daemon/tests/unit/test_story_5_1_facade.py`
- `resources/daemon/tests/unit/test_story_5_2_execute_publier.py`
- `resources/daemon/tests/unit/test_story_5_2_integration.py`
- `tests/unit/test_story_5_2_frontend.node.test.js`
- `_bmad-output/implementation-artifacts/5-2-flux-positif-contextuel-creer-republier-multi-portee.md`

## Gate terrain 2026-04-07

| # | Étape | Observation | Verdict |
|---|---|---|---|
| 1 | Préflight — démon, MQTT, home plugin | Page accessible, démon OK, MQTT connecté, aucune erreur visible | **PASS** |
| 2 | Global — Republier | Modale conforme ("99 équipements inclus"), toast vert "Parc global — 30 équipements republiés". 69 skippés (mappings absents/ambigus — attendu). Aucune erreur. | **PASS** |
| 3 | Équipement non publié → Créer (bouton individuel) | NOT EXECUTED — Story 5.3 absente : impossible de remettre un équipement mappable *actif* en état "non publié". Deux cas observés : (a) capteur sans mapping : bouton "Créer" actif + "déjà à jour" ; (b) "buanderie plafond" désactivé dans Jeedom → affiché "Inclus / Non publié" en UI mais backend skip (hors topology) → "déjà à jour" + entité absente de HA. UX issue transverse : boutons non grisés pour équipements sans mapping ou désactivés. À traiter hors scope 5.2. Couverture indirecte via Republier global (30 publiés). | **NOT EXECUTED** |
| 4 | Équipement déjà publié → Republier individuel | Toast vert "buanderie plafond — 1 équipements mis à jour dans Home Assistant." Bouton resté "Republier" (bleu) après refresh. `est_publie_ha` maintenu. Aucun doublon signalé. | **PASS** |
| 5 | Scope enforcement — pièce Buanderie exclue | Exclusion pièce + appliquer/rescanner → 11 équipements "Alignés / Non publiés", 0 écarts. Entités confirmées absentes de HA (dont "buanderie plafond" republié en étape 4). Trigger : rescan post-exclusion (pas le bouton Republier explicitement). Résultat conforme. | **PASS** |
| 6 | Idempotence | Republier individuel lancé 2 fois de suite — même feedback aux deux clics, aucun doublon, aucune erreur. | **PASS** |
| 7 | Bridge down / gating | Broker MQTT coupé → aucune action ne part au clic. Fonctionnellement correct. Observation UX : curseur reste `pointer` au survol → boutons semblent cliquables visuellement. À améliorer : fond gris + `cursor: not-allowed` (comme badges "non publié"). Non bloquant pour ce gate. | **PASS** |

### Verdict gate terrain : PARTIAL — clôturé avec waiver

**6/7 PASS — 1 NOT EXECUTED**

**Waiver assumé sur le checkpoint 3 (Créer individuel) :**
- Raison d'inexécution : Story 5.3 (Supprimer) non encore disponible — impossible de remettre un équipement mappable actif en état "non publié" sans levier de dépublication. Le Republier global (étape 2) a consommé tous les candidats avant que le test individuel puisse être exécuté.
- Couverture indirecte disponible : les 30 équipements publiés lors du Republier global incluaient des premières créations ; les tests unitaires story-level (`test_story_5_2_execute_publier.py`) couvrent explicitement le cas "inclus non publié → publish → `equipements_publies_ou_crees = 1`".
- **Report vers Story 5.3** : le flux `Supprimer` permettra de remettre un équipement mappable actif en état "non publié" de manière contrôlée. Le test terrain "Créer" individuel sera exécuté dans le gate terrain de Story 5.3.
- Décision produit : clôture à `done` acceptée avec ce waiver documenté.

**Observations UX hors clôture fonctionnelle (à traiter en backlog) :**
1. Boutons "Créer"/"Republier" actifs pour équipements sans mapping ou désactivés dans Jeedom → feedback "déjà à jour" sémantiquement trompeur (équipement absent de HA). À corriger : griser le bouton ou afficher un tooltip explicite quand le mapping est absent.
2. Boutons grisés en mode bridge-down mais curseur `pointer` au survol → manque `cursor: not-allowed` pour rendre le disabled visuellement explicite (alignement avec le style des badges "non publié").

## Change Log

- **2026-04-06** — Story 5.2 implémentée dans le worktree dédié : backend `publier` multi-portée, handlers frontend équipement/pièce/global, feedback utilisateur, suites story-level ajoutées. Non-régression locale validée : `782 pytest` + `133 JS` + `3 PHP` exécutables PASS. Gate terrain tenté mais bloqué car `JEEDOM_BOX_HOST` n'est pas défini.
- **2026-04-07** — Gate terrain exécuté sur box réelle. 6/7 PASS, 1 NOT EXECUTED (Créer individuel — waiver assumé, report vers Story 5.3). Story passée à `done`.
