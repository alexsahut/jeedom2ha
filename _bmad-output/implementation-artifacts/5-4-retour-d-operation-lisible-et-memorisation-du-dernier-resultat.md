# Story 5.4 : Retour d'opération lisible et mémorisation du dernier résultat

Status: done

Epic: Epic 5 — Opérations HA explicites, contextuelles et sûres

## Story

En tant qu'utilisateur de la console,
je veux un retour d'opération court, lisible et mémorisé visible dans le bandeau de santé,
afin de savoir sans inspecter les logs ce qui a été lancé, sur quel périmètre et avec quel résultat — même après un rafraîchissement de page.

## Contexte / Objectif produit

Cette story est la **dernière story de l'Epic 5**. Elle complète la couche de lisibilité opérationnelle initiée par Story 2.1 (contrat de santé minimale) en enrichissant le champ `derniere_operation_resultat` déjà exposé par `/system/status`.

**Situation actuelle :**
- `app["derniere_operation_resultat"]` est un **simple string** (`"aucun"` / `"succes"` / `"partiel"` / `"echec"`).
- `/system/status` le sérialise tel quel.
- Le bandeau (`span#span_healthOp`) affiche un badge coloré (Succès / Partiel / Échec / Aucune) — sans aucun contexte sur *quoi*, *où*, *combien*.
- Le retour détaillé de l'opération (message, périmètre, volume) est visible uniquement dans l'alerte transiente `div_alert` — perdu au prochain rafraîchissement de page.

**Ce que Story 5.4 ajoute :**
- Le champ `derniere_operation_resultat` passe de **string → objet enrichi** : `{resultat, intention, portee, message, volume, timestamp}`.
- Le bandeau affiche le badge (inchangé) + le **message court** persistant (nouveau span adjacent).
- La mémorisation est **en mémoire daemon** (in-process, sans persistance disque) : survit aux rafraîchissements UI, remise à zéro uniquement si le daemon redémarre.

**Frontière Story 5.4 :**
- Ne modifie PAS le payload de retour des actions (`scope_reel`, `perimetre_impacte`, `message` dans l'action response) — ces champs restent inchangés.
- Ne crée PAS de nouveau endpoint ni de nouvelle mécanique d'opérations.
- N'introduit PAS de persistance disque.
- N'ouvre PAS les stories déjà soldées (5.1, 5.2, 5.3, 5.5, 5.6, 5.7).

## Dépendances autorisées

- **Story 2.1** — `done` : contrat backend de santé minimale ; `app["derniere_operation_resultat"]` initialisé ici (ligne 2400 de `http_server.py`).
- **Story 5.1** — `done` : façade backend, `_handle_action_execute`, `/system/status` déjà exposé.
- **Story 5.2** — `done` : branche `publier` dans `_handle_action_execute` ; `_build_publier_message` existant (ligne 307) ; `equipements_publies_ou_crees` disponible.
- **Story 5.3** — `done` : branche `supprimer` dans `_handle_action_execute` ; `_build_supprimer_message` existant (ligne 325) ; `equipements_supprimes` disponible.

## Scope

### In scope

**Backend (`resources/daemon/transport/http_server.py`) :**
1. Nouvelle fonction pure `_build_operation_snapshot(*, resultat, intention, portee, message, volume)` → `dict` — construit l'objet enrichi.
2. Mise à jour de l'initialisation dans `create_app` : `app["derniere_operation_resultat"]` = objet (plus string).
3. Mise à jour des **4 points d'affectation** existants :
   - `_handle_action_sync` exception handler (ligne ~875) : `intention="sync"`, message d'échec.
   - `_do_handle_action_sync` (lignes ~1410-1413) : `intention="sync"`, message par résultat.
   - Branche `supprimer` dans `_handle_action_execute` (ligne ~2169) : `intention="supprimer"`, portée, message, volume.
   - Branche `publier` dans `_handle_action_execute` (ligne ~2353) : `intention="publier"`, portée, message, volume.
4. Réutilisation des fonctions existantes `_build_publier_message` / `_build_supprimer_message` comme source du champ `message` du snapshot. Les stocker dans une variable locale et réutiliser dans le `payload` (éviter le double appel).

**Frontend JS (`desktop/js/jeedom2ha_scope_summary.js`) :**
5. Nouvelle fonction pure exportée `readOperationSnapshot(raw)` — normalise `derniere_operation_resultat` (string legacy OU objet enrichi) vers un objet canonique `{resultat, intention, portee, message, volume, timestamp}`.

**Frontend JS (`desktop/js/jeedom2ha.js`) :**
6. Mise à jour de `getBridgeStatus` > bloc "4. Dernière opération" (lignes 84–103) :
   - Déclarer `$opMsg = $('#span_healthOpMsg')` en tête du bloc (avec les autres `$var`).
   - Lire `r.derniere_operation_resultat` via `readOperationSnapshot()`.
   - Badge : comportement inchangé (basé sur `opObj.resultat`).
   - Nouveau : `$opMsg.text(opObj.message || '')`.
   - Cas bridge down (ligne ~47) : ajouter `$opMsg.text('')` pour effacer le message.

**Frontend PHP (`desktop/php/jeedom2ha.php`) :**
7. Ajouter `<span id="span_healthOpMsg">` immédiatement après `span_healthOp` (ligne ~33).

**Tests backend :**
8. `resources/daemon/tests/unit/test_story_5_4_operation_snapshot.py` — tests pytest dédiés.

**Tests frontend JS :**
9. `tests/unit/test_story_5_4_bandeau.node.test.js` — tests node:test pour `readOperationSnapshot` et couverture comportementale du rendu bandeau (badge + message).

### Out of scope

| Élément | Responsable |
|---|---|
| Persistance disque du dernier résultat | Hors V1.1 |
| Timeline des opérations (historique) | Hors V1.1 |
| Panneau secondaire de détail opération | Hors V1.1 |
| Réouverture du payload de retour d'action (`scope_reel`, `perimetre_impacte`) | Déjà fourni par 5.2/5.3 |
| Nouvelles opérations HA | Hors scope |
| Modification du gating, des confirmations fortes, des modales | 5.2/5.3 déjà soldées |
| Toute logique métier côté frontend | Invariant architectural |

## Acceptance Criteria

### AC 1 — Snapshot enrichi après une opération HA

**Given** une opération `publier` ou `supprimer` terminée (succès, partiel ou échec)
**When** le backend finalise le traitement
**Then** `app["derniere_operation_resultat"]` est un dict contenant :
- `resultat` : `"succes"` / `"partiel"` / `"echec"` (normalisé — `"succes_partiel"` → `"partiel"`)
- `intention` : `"publier"` ou `"supprimer"`
- `portee` : `"global"` / `"piece"` / `"equipement"`
- `message` : texte lisible identique à celui du payload de retour de l'action
- `volume` : nombre entier d'équipements traités avec succès (≥ 0)
- `timestamp` : horodatage ISO UTC

### AC 2 — Snapshot enrichi après synchronisation

**Given** une synchronisation (`/action/sync`) terminée
**When** le backend finalise le traitement
**Then** `app["derniere_operation_resultat"]` est un dict avec `intention = "sync"`, `portee = null`, `volume = null`, `message` adapté au résultat

### AC 3 — `/system/status` expose l'objet enrichi

**Given** une opération ou synchronisation terminée
**When** le bandeau appelle `/system/status`
**Then** `payload.derniere_operation_resultat` est un **objet JSON** (non une string) contenant les 6 champs définis en AC 1
**And** les champs existants de `/system/status` (`demon`, `broker`, `derniere_synchro_terminee`, etc.) sont inchangés

### AC 4 — État initial cohérent

**Given** aucune opération n'a encore été exécutée depuis le démarrage du daemon
**When** `/system/status` est appelé
**Then** `payload.derniere_operation_resultat.resultat` vaut `"aucun"`
**And** les champs `intention`, `portee`, `message`, `volume` valent `null`
**And** le champ n'est jamais omis du contrat

> **Note terrain (gate 2026-04-09) :** L'état initial `Aucune` n'est pas directement observable sur la box réelle car Jeedom déclenche automatiquement une synchronisation au démarrage du daemon. En pratique, le bandeau affiche immédiatement le résultat de cette sync (`intention="sync"`). Ce comportement est conforme au contrat : AC4 reste valide (l'init est correcte), l'auto-sync de Jeedom est un comportement plateforme hors périmètre story. Validé structurellement via les tests pytest (`test_snapshot_initial_resultat_aucun`).

### AC 5 — Bandeau affiche badge + message court persistant

**Given** une opération terminée (succès, partiel ou échec)
**When** le bandeau de santé est rafraîchi (y compris via rechargement de page)
**Then** `span#span_healthOp` affiche le badge coloré correspondant (Succès / Partiel / Échec)
**And** `span#span_healthOpMsg` affiche le message court lisible de l'opération
**And** ce message persiste au rechargement de page (tant que le daemon tourne)

### AC 6 — Normalisation robuste côté frontend

**Given** que `derniere_operation_resultat` peut être un objet enrichi (nouveauté) ou un string legacy (compatibilité défensive)
**When** `readOperationSnapshot(raw)` traite la valeur
**Then** il retourne toujours un objet canonique `{resultat, intention, portee, message, volume, timestamp}`
**And** si `raw` est une string, `resultat = raw`, les autres champs sont `null`
**And** si `raw` est `null` ou invalide, `resultat = "aucun"`, les autres champs sont `null`

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification cycle complet republication + validation bandeau enrichi : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.`

- [x] Task 1 — Backend : helper `_build_operation_snapshot` et mise à jour des 4 points d'affectation (AC: 1, 2, 3, 4)
  - [x] Définir `_build_operation_snapshot(*, resultat, intention=None, portee=None, message=None, volume=None) -> dict` après `_build_supprimer_message` (ligne ~342 de `http_server.py`) — inclure `"timestamp": datetime.now(timezone.utc).isoformat()` dedans
  - [x] Mettre à jour `create_app` (ligne ~2400) : `app["derniere_operation_resultat"] = _build_operation_snapshot(resultat="aucun")`
  - [x] Mettre à jour `_handle_action_sync` exception handler (ligne ~875) : remplacer `"echec"` par appel `_build_operation_snapshot(resultat="echec", intention="sync", message="Synchronisation échouée — erreur inattendue.")`
  - [x] Mettre à jour `_do_handle_action_sync` (lignes ~1410-1413) : calculer `_snap_res` + `_snap_msg` (table résultat → message sync) puis appel `_build_operation_snapshot(...)`
  - [x] Mettre à jour branche `supprimer` (ligne ~2169) : stocker `_build_supprimer_message(...)` dans `_supprimer_msg`, passer à `_build_operation_snapshot(resultat=..., intention="supprimer", portee=portee, message=_supprimer_msg, volume=equipements_supprimes)`, réutiliser `_supprimer_msg` dans `payload["message"]`
  - [x] Mettre à jour branche `publier` (ligne ~2353) : stocker `_build_publier_message(...)` dans `_publier_msg`, passer à `_build_operation_snapshot(resultat=..., intention="publier", portee=portee, message=_publier_msg, volume=equipements_publies_ou_crees)`, réutiliser `_publier_msg` dans `payload["message"]`

- [x] Task 2 — Frontend JS : `readOperationSnapshot` + affichage message court (AC: 5, 6)
  - [x] Dans `jeedom2ha_scope_summary.js` : définir `readOperationSnapshot(raw)` — normalise string/objet/null vers `{resultat, intention, portee, message, volume, timestamp}` canonique ; `VALID_RESULTATS = {succes, partiel, echec, aucun}`
  - [x] Exporter `readOperationSnapshot` dans le `return { ... }` final de `jeedom2ha_scope_summary.js`
  - [x] Dans `jeedom2ha.js` ligne ~38 : ajouter `var $opMsg = $('#span_healthOpMsg');`
  - [x] Dans `jeedom2ha.js` ligne ~47 (cas bridge down `!r.daemon`) : ajouter `$opMsg.text('');`
  - [x] Dans `jeedom2ha.js` lignes ~84-103 : remplacer `var op = r.derniere_operation_resultat || 'aucun';` par `var _opObj = readOperationSnapshot(r.derniere_operation_resultat);` (fonction importée via `jeedom2ha_scope_summary.js`) ; remplacer `switch(op)` par `switch(_opObj.resultat)` ; après le switch du badge, ajouter `$opMsg.text(_opObj.message || '');`
  - [x] Dans `desktop/php/jeedom2ha.php` ligne ~33 : ajouter `<span id="span_healthOpMsg" style="margin-left:8px; color:#666; font-size:0.9em;"></span>` immédiatement après `span_healthOp`

- [x] Task 3 — Tests backend (AC: 1, 2, 3, 4)
  - [x] `resources/daemon/tests/unit/test_story_5_4_operation_snapshot.py` :
    - Test `_build_operation_snapshot` retourne un dict avec les 6 champs
    - Test que `_build_operation_snapshot(resultat="partiel", ...)` retourne `{"resultat": "partiel", ...}` — la normalisation `"succes_partiel"` → `"partiel"` est appliquée avant l'appel (dans la branche `publier`), le helper ne normalise pas lui-même
    - Test `/system/status` : `derniere_operation_resultat` est un objet (non une string)
    - Test init : `resultat = "aucun"`, champs null
    - Test après `publier` mock : `intention = "publier"`, `portee` correct, `message` non null, `volume` ≥ 0
    - Test après `supprimer` mock : `intention = "supprimer"`, `volume = equipements_supprimes`
    - Test après `sync` : `intention = "sync"`, `portee = null`, `volume = null`
    - Test non-régression `/system/status` : champs `demon`, `broker`, `derniere_synchro_terminee` toujours présents

- [x] Task 4 — Tests frontend JS (AC: 5, 6)
  - [x] `tests/unit/test_story_5_4_bandeau.node.test.js` :
    - **Normalisation `readOperationSnapshot` (AC 6) :**
    - `readOperationSnapshot(null)` → `{resultat: "aucun", intention: null, message: null, ...}`
    - `readOperationSnapshot(undefined)` → idem
    - `readOperationSnapshot("succes")` → `{resultat: "succes", intention: null, message: null, ...}`
    - `readOperationSnapshot({resultat: "partiel", intention: "publier", portee: "piece", message: "5 équipements mis à jour...", volume: 5, timestamp: "..."})` → champs corrects
    - `readOperationSnapshot({resultat: "invalide", ...})` → `{resultat: "aucun", ...}`
    - `readOperationSnapshot({resultat: "succes", message: ""})` → `message: null` (string vide normalisé en null)
    - Vérifier que `readOperationSnapshot` est bien exporté (pas null)
    - **Couverture rendu badge — données qui pilotent `switch(_opObj.resultat)` dans `jeedom2ha.js` (AC 5) :**
    - `readOperationSnapshot({resultat: "succes", message: "12 équipements mis à jour."}).resultat === "succes"` → badge `label-success`
    - `readOperationSnapshot({resultat: "partiel", message: "3 mis à jour, 2 non traités."}).resultat === "partiel"` → badge `label-warning` orange
    - `readOperationSnapshot({resultat: "echec", message: "Synchronisation échouée."}).resultat === "echec"` → badge `label-warning` orange
    - `readOperationSnapshot({resultat: "aucun"}).resultat === "aucun"` → badge `label-default`
    - **Couverture rendu message — données qui pilotent `$opMsg.text(_opObj.message || '')` (AC 5) :**
    - `readOperationSnapshot({resultat: "succes", message: "12 équipements mis à jour."}).message === "12 équipements mis à jour."` → `$opMsg.text(...)` reçoit le message
    - `readOperationSnapshot({resultat: "succes", message: null}).message === null` → `$opMsg.text('')`
    - `readOperationSnapshot({resultat: "succes", message: ""}).message === null` → `$opMsg.text('')`
    - **Cas bridge down :** comportement de l'effacement (`$opMsg.text('')` sur `!r.daemon`) est une exigence de Task 2 — validé par le gate terrain scénario 1

- [x] Task 5 — Validation non-régression
  - [x] `python3 -m pytest resources/daemon/tests/ -q` → 279 PASS (270 + 9 nouveaux), 0 régression
  - [x] `node --test tests/unit/*.node.test.js` → 170 PASS (153 + 17 nouveaux), 0 régression
  - [x] `python3 -m pytest tests/ -q` → 541 PASS, 0 régression

## Dev Notes

### Contrat `/system/status` — Décision de breaking change (locked)

**Décision 1 — Backend exclusivement objet :** Après Story 5.4, `app["derniere_operation_resultat"]` est **exclusivement** un `dict` Python. Le type `str` est supprimé sans transition : daemon et frontend sont toujours déployés ensemble, aucun consommateur n'est laissé sur l'ancien format.

**Décision 2 — Compatibilité frontend défensive uniquement :** `readOperationSnapshot(raw)` accepte une string en entrée comme garde-fou défensif (déploiement partiel, cache stale). Ce chemin n'est pas un contrat maintenu — il n'est pas testé comme cas nominal.

**Décision 3 — Aucun autre consommateur du vieux format :** Cette story ne supporte aucun autre consommateur externe du format string. Aucun appel direct à `/system/status` dans un outil tiers ou intégration externe n'entre dans le périmètre de 5.4.

**Impact sur le contrat `/system/status` :** Le seul champ modifié est `derniere_operation_resultat` : `"succes"` (string) → `{"resultat": "succes", "message": "...", ...}` (objet). Tous les autres champs (`daemon`, `broker`, `derniere_synchro_terminee`, etc.) sont inchangés.

### Où vit la mémorisation du dernier résultat

La mémorisation vit **dans `app["derniere_operation_resultat"]`** (state in-process d'aiohttp). Elle :
- Survit aux rafraîchissements de l'UI (le daemon tourne en continu).
- Est remise à zéro (`resultat: "aucun"`) uniquement si le daemon redémarre.
- N'est **pas** persistée sur disque — par conception (cohérent avec `derniere_synchro_terminee`).
- Est écrasée à chaque nouvelle opération (1 seul dernier résultat mémorisé, pas d'historique).

### Différence nette entre résultat technique et résultat court

| | Résultat technique détaillé | Résultat court utilisateur |
|---|---|---|
| **Contenu** | `scope_reel` (equipements_publies_ou_crees, publish_errors, skips, etc.) | `{resultat, message, intention, portee, volume, timestamp}` |
| **Vie** | Payload de retour de l'action → alerte transiente (`div_alert`) | Mémorisé dans `app["derniere_operation_resultat"]` → bandeau persistant |
| **Visible** | Immédiatement post-action, disparaît au rechargement | Persistant dans le bandeau entre rafraîchissements |
| **Audience** | Debug / support | Utilisateur (bandeau lisible) |

Story 5.4 n'ajoute **pas** `scope_reel` dans `/system/status`. Elle mémorise uniquement le résumé condensé.

### Affichage partiel sans ambiguïté

Le résultat `"partiel"` doit toujours s'accompagner d'un `message` explicite :
- `publier` partiel : `"X équipements mis à jour, Y n'ont pas pu être traités."` (déjà produit par `_build_publier_message`)
- `supprimer` partiel : `"X supprimé(s), Y n'ont pas pu être traité(s)."` (déjà produit par `_build_supprimer_message`)

Le badge orange + le message côte à côte dans le bandeau éliminent l'ambiguïté support sans champ technique supplémentaire.

### Message de portée — comportement locked

**Décision — message générique :** `_build_publier_message` et `_build_supprimer_message` produisent des messages **sans nom de pièce ni d'équipement inline** (ex. `"12 équipements mis à jour dans Home Assistant."` — non `"Salon — 12 équipements mis à jour."`). Story 5.4 **ne modifie pas** ce comportement. Le champ `portee` du snapshot (`"piece"` / `"equipement"` / `"global"`) communique le type de périmètre ; `message` reste générique. Aucun nouveau champ `nom_portee` n'est introduit.

### Éviter la duplication bandeau / résultat / état des actions

Le bandeau a 4 zones distinctes répondant à des questions différentes :
- **Bridge** → l'infrastructure est-elle opérationnelle ?
- **MQTT** → le transport MQTT est-il connecté ?
- **Dernière synchro** → quand a eu lieu la dernière synchronisation ?
- **Dernière opération** → quel est le résultat de la dernière action utilisateur ?

Story 5.4 enrichit uniquement la 4ème zone. Pas de nouvelle zone, pas de duplication avec l'état des actions (géré par `applyHAGating` indépendamment).

### Comportement UX exact du bandeau `Dernière opération` (locked)

| Situation | Badge `span_healthOp` | Message `span_healthOpMsg` |
|---|---|---|
| Aucune opération depuis démarrage daemon | `label-default` — `Aucune` | vide (aucun texte affiché) |
| Opération succès | `label-success` — `Succès` | message texte de l'opération |
| Opération partielle | `label-warning` orange — `Partiel` | message texte explicatif |
| Opération échec | `label-warning` orange — `Échec` | message texte d'erreur |
| Bridge down (`!r.daemon`) | `label-default` — `Inconnue` | vide — effacement explicite via `$opMsg.text('')` |
| `message` null ou string vide | badge inchangé | vide — `$opMsg.text('')` |

**Règles de sobriété visuelle :**
- `span_healthOpMsg` est le seul ajout visible dans le bandeau. Aucune nouvelle zone, aucun panneau secondaire, aucune alerte persistante hors du bandeau.
- Le texte du message est affiché tel quel : pas de troncature, pas de formatage HTML côté frontend.
- La cohérence avec les micro-stories 5.5 / 5.6 / 5.7 est garantie par l'absence de toute modification dans `renderActionButtons`, `applyHAGating` et les badges d'équipement.

### Structure du helper `_build_operation_snapshot`

```python
# À placer après _build_supprimer_message (~ligne 342)
def _build_operation_snapshot(
    *,
    resultat: str,
    intention: Optional[str] = None,
    portee: Optional[str] = None,
    message: Optional[str] = None,
    volume: Optional[int] = None,
) -> dict:
    return {
        "resultat": resultat,
        "intention": intention,
        "portee": portee,
        "message": message,
        "volume": volume,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

Import `Optional` déjà disponible dans `http_server.py` (`from typing import ...`).

### Messages de la branche sync

```python
_SYNC_MESSAGES = {
    "succes": "Synchronisation terminée.",
    "partiel": "Synchronisation terminée avec avertissements.",
    "echec": "Synchronisation échouée.",
}
```

### Normalisation `"succes_partiel"` → `"partiel"`

La normalisation est appliquée **avant** l'appel à `_build_operation_snapshot` (identique à la logique actuelle) :

```python
snapshot_resultat = "partiel" if resultat == "succes_partiel" else resultat
request.app["derniere_operation_resultat"] = _build_operation_snapshot(
    resultat=snapshot_resultat,
    intention="publier",
    portee=portee,
    message=_publier_msg,     # construit avec resultat brut ("succes_partiel") pour bon libellé
    volume=equipements_publies_ou_crees,
)
```

`_build_publier_message` reçoit le `resultat` brut (avec `"succes_partiel"`) pour formater correctement le message. Le snapshot stocke `"partiel"` (normalisé).

### Structure `readOperationSnapshot` (JS)

```js
function readOperationSnapshot(raw) {
  var VALID_RESULTATS = { succes: true, partiel: true, echec: true, aucun: true };
  var empty = { resultat: 'aucun', intention: null, portee: null, message: null, volume: null, timestamp: null };
  if (raw === null || raw === undefined) return empty;
  if (typeof raw === 'string') {
    return Object.assign({}, empty, { resultat: VALID_RESULTATS[raw] ? raw : 'aucun' });
  }
  if (typeof raw !== 'object') return empty;
  var resultat = (typeof raw.resultat === 'string' && VALID_RESULTATS[raw.resultat]) ? raw.resultat : 'aucun';
  return {
    resultat: resultat,
    intention: typeof raw.intention === 'string' ? raw.intention : null,
    portee: typeof raw.portee === 'string' ? raw.portee : null,
    message: (typeof raw.message === 'string' && raw.message !== '') ? raw.message : null,
    volume: (typeof raw.volume === 'number' && Number.isFinite(raw.volume)) ? raw.volume : null,
    timestamp: typeof raw.timestamp === 'string' ? raw.timestamp : null,
  };
}
```

### Cohérence avec 5.5 / 5.6 / 5.7

Ces stories livrent des modifications au rendu de `jeedom2ha_scope_summary.js` (libellés courts, disabled boutons, badge Suppr. pièce). Story 5.4 :
- N'ajoute rien à `renderActionButtons`, `renderPieceActionButtons`, `renderPiecePublishButton`.
- N'ajoute rien aux balises `[data-ha-action]` ni au gating `applyHAGating`.
- N'ajoute rien aux badges de statut d'équipement.
- Ne touche pas aux tests existants de 5.5/5.6/5.7.

Le seul ajout dans `jeedom2ha_scope_summary.js` est la fonction `readOperationSnapshot` et son export.

### Dev Agent Guardrails

#### Guardrail — Ne pas rouvrir les stories soldées

- **5.1** : Ne pas modifier `actions_ha`, `est_publie_ha`, la façade backend, le signal de disponibilité.
- **5.2** : Ne pas modifier la branche `publier` au-delà de la ligne `derniere_operation_resultat` et du stockage du message.
- **5.3** : Ne pas modifier la branche `supprimer` au-delà de la ligne `derniere_operation_resultat` et du stockage du message.
- **5.5** : Ne pas modifier `shortLabel()`, `renderActionButtons()`, `pieceColumns`.
- **5.6** : Ne pas modifier la logique de rendu `disabled` des boutons HA.
- **5.7** : Ne pas modifier le badge `Suppr.` pièce/équipement.

#### Guardrail — Backend source unique

- Le champ `message` du snapshot est construit par `_build_publier_message` / `_build_supprimer_message` (backend).
- Le frontend ne calcule pas le message, ne le reformate pas, ne le tronque pas.
- `$opMsg.text(opObj.message || '')` — lecture stricte, aucune transformation.

#### Guardrail — Pas de persistance disque

- Ne pas appeler `save_publications_cache` ou équivalent pour persister `derniere_operation_resultat`.
- Ne pas créer de fichier JSON de snapshot dans `_DATA_DIR`.
- La mémorisation est in-process uniquement.

#### Guardrail — Payload de retour d'action inchangé

- La structure `payload` dans les branches `publier` et `supprimer` reste identique à ce que livraient 5.2 et 5.3.
- Seule différence : le `message` est stocké dans une variable locale (`_publier_msg`, `_supprimer_msg`) avant d'être utilisé dans les deux endroits (snapshot + payload). Aucun nouveau champ dans le payload de retour.

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Points de vigilance non-régression

| Story | Point de vigilance |
|---|---|
| **5.1** | `app["derniere_operation_resultat"]` initialisé à `_build_operation_snapshot(resultat="aucun")` — pas de rupture contrat `/system/status` pour les autres champs |
| **5.2** | Branche `publier` : `_build_publier_message` toujours appelé avec le même `resultat` brut qu'avant (formatage message inchangé) |
| **5.3** | Branche `supprimer` : idem pour `_build_supprimer_message` |
| **5.6** | `applyHAGating` consomme `r.broker.state` — non impacté par Story 5.4 |
| **5.7** | Badges `Suppr.` consomment `actions_ha.supprimer` — non impacté |
| **2.2** | Bandeau : le `switch` sur le badge de `span_healthOp` reste identique ; seul `span_healthOpMsg` est ajouté |

### Fichiers candidats à la modification

| Couche | Fichier | Modification attendue |
|---|---|---|
| Backend Python | `resources/daemon/transport/http_server.py` | Lignes ~342 (helper), ~875 (exception), ~1410-1413 (sync), ~2169 (supprimer), ~2353 (publier), ~2400 (init) |
| Frontend JS | `desktop/js/jeedom2ha_scope_summary.js` | `readOperationSnapshot` + export |
| Frontend JS | `desktop/js/jeedom2ha.js` | Lignes ~38 (décl. $opMsg), ~47 (bridge down), ~84-103 (lecture objet + affichage message) |
| Frontend PHP | `desktop/php/jeedom2ha.php` | Ligne ~33 : ajout `span#span_healthOpMsg` |
| Tests Python | `resources/daemon/tests/unit/test_story_5_4_operation_snapshot.py` | Nouveaux tests dédiés |
| Tests JS | `tests/unit/test_story_5_4_bandeau.node.test.js` | Tests `readOperationSnapshot` (normalisation) + couverture comportementale badge/message bandeau |

### Baseline non-régression

- **pytest** : 270 PASS (post-Story 5.7) → objectif ≥ 278 après Story 5.4 (8+ nouveaux tests)
- **JS node:test** : 153 PASS (post-Story 5.7) → objectif ≥ 160 après Story 5.4 (7+ nouveaux tests)

### Gate terrain — Scénario de validation

Après déploiement sur la box réelle (`--cleanup-discovery --restart-daemon`) :

1. Ouvrir la console plugin — bandeau affiche `Dernière opération : Aucune` (badge gris, pas de message).
2. Appuyer sur "Republier dans Home Assistant" (global) → attendre le retour.
3. **Sans recharger la page** : vérifier que `span_healthOp` affiche badge vert "Succès" ET `span_healthOpMsg` affiche le message (ex. "12 équipements mis à jour dans Home Assistant.").
4. **Recharger la page** : vérifier que le badge et le message sont toujours visibles (mémorisation daemon).
5. Vérifier via `curl -H "X-Local-Secret: ..." http://localhost:PORT/system/status | python3 -m json.tool` : `derniere_operation_resultat` est un objet avec `resultat`, `message`, `intention`, `portee`, `volume`, `timestamp`.
6. Effectuer un "Supprimer puis recréer" sur un équipement → valider badge "Succès" + message "1 équipement supprimé..." dans le bandeau.
7. Recharger → message toujours présent.

### References

- [Story 5.1](5-1-facade-backend-unique-et-contrat-de-disponibilite-des-actions.md) — façade backend, contrat `actions_ha`, `/system/status`
- [Story 5.2](5-2-flux-positif-contextuel-creer-republier-multi-portee.md) — `_build_publier_message`, branche `publier`, `equipements_publies_ou_crees`
- [Story 5.3](5-3-flux-supprimer-standalone-avec-confirmations-fortes.md) — `_build_supprimer_message`, branche `supprimer`, `equipements_supprimes`
- [Story 2.1 / 2.2 Epic epics](../planning-artifacts/epics-post-mvp-v1-1-pilotable.md#Epic-2) — contrat de santé minimale, bandeau
- [UX delta §9.2-9.3](../planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md) — `Dernière opération`, libellés visibles
- [Source: http_server.py — `_handle_system_status`] — ligne 593, bandeau backend
- [Source: http_server.py — `create_app`] — ligne 2395-2406, initialisation `app[]`
- [Source: jeedom2ha.js] — lignes 25-113, `getBridgeStatus`, `updateBridgeStatus`
- [Source: jeedom2ha.php] — lignes 17-35, bandeau HTML

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

Aucun blocage majeur. Deux corrections de tests au passage :
- `test_snapshot_apres_publier_global` : ajout de `"selection": ["all"]` manquant (portée global requiert ce champ).
- `test_snapshot_apres_sync_intention_et_portee_null` : ajout de `json={}` pour fournir un body JSON vide (l'endpoint lit `request.json()`).
- 4 tests `TestHealthCheckContract` dans `tests/unit/test_http_server.py` (Story 2.1) : assertions mises à jour pour vérifier le nouveau format dict (`["resultat"]`) au lieu de la string legacy.

### Completion Notes List

- `_build_operation_snapshot` défini après `_build_supprimer_message` — 6 champs : `resultat`, `intention`, `portee`, `message`, `volume`, `timestamp` UTC.
- `create_app` : initialisation avec objet `{resultat: "aucun", ...}`.
- `_handle_action_sync` exception handler : snapshot avec `intention="sync"`, message fixe.
- `_do_handle_action_sync` : table `_SYNC_MESSAGES` + calcul `_snap_res` → snapshot enrichi.
- Branche `supprimer` : variable locale `_supprimer_msg` — réutilisée dans snapshot et payload, 0 double appel.
- Branche `publier` : variable locale `_publier_msg` — idem.
- `readOperationSnapshot(raw)` : normalise string/objet/null → objet canonique, string vide → null, résultat invalide → "aucun".
- `jeedom2ha.js` : `$opMsg` déclaré, effacement bridge down, switch sur `_opObj.resultat`, `$opMsg.text(_opObj.message || '')`.
- `jeedom2ha.php` : `span#span_healthOpMsg` ajouté après `span_healthOp`.
- Tests : 9 pytest nouveaux (279 total), 17 JS nouveaux (170 total), 541 PASS dans `tests/`, 0 régression.

### File List

- `resources/daemon/transport/http_server.py`
- `desktop/js/jeedom2ha_scope_summary.js`
- `desktop/js/jeedom2ha.js`
- `desktop/php/jeedom2ha.php`
- `resources/daemon/tests/unit/test_story_5_4_operation_snapshot.py` (nouveau)
- `tests/unit/test_story_5_4_bandeau.node.test.js` (nouveau)
- `tests/unit/test_http_server.py` (assertions Story 2.1 mises à jour)
- `_bmad-output/implementation-artifacts/5-4-retour-d-operation-lisible-et-memorisation-du-dernier-resultat.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Closeout Record

### Code Review

- **Décision :** APPROVE
- **Findings :** 0 finding bloquant

### Gate Terrain

- **Date :** 2026-04-09
- **Environnement :** Box Jeedom réelle (`--cleanup-discovery --restart-daemon`)
- **Résultat global :** PASS

| Scénario | Résultat |
|---|---|
| 1. Bandeau initial — badge `Aucune` (gris), `span_healthOpMsg` vide | PASS (non observable directement — auto-sync Jeedom au démarrage ; voir note AC4) |
| 2. Republier global → badge `Succès` (vert) + message visible sans rechargement | PASS |
| 3. Rechargement de page → badge + message toujours présents (mémorisation daemon) | PASS |
| 4. `curl /system/status` → `derniere_operation_resultat` est un objet JSON avec les 6 champs | PASS |
| 5. Supprimer un équipement → badge `Succès` + message `"1 équipement supprimé..."` | PASS |
| 6. Rechargement post-suppression → message toujours présent | PASS |

**AC4 — note :** L'état initial `Aucune` n'est pas observable sur box réelle (auto-sync Jeedom au démarrage du daemon). Validé structurellement via tests pytest. Comportement plateforme hors périmètre story, non comptabilisé comme échec.

### SM Closeout

- **Story passée en `done` :** 2026-04-09
- **Epic 5 :** toutes les stories soldées — epic-5 passé en `done`
- **Note :** Story 5.4 est la dernière story fonctionnelle de l'Epic 5. Clôture de l'épic effective.

## Change Log

- 2026-04-09 — Story 5.4 implémentée : `_build_operation_snapshot` backend, `readOperationSnapshot` frontend JS, `span_healthOpMsg` PHP, tests 9+17, 0 régression.
