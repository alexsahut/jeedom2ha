# Matrice Lifecycle — Epic 5 : Fiabilité & Cycle de Vie

**Date :** 2026-03-20
**Auteurs :** Alexandre (Project Lead) + Charlie (Senior Dev)
**Statut :** Draft — À valider avant création des stories Epic 5
**Action item source :** Rétrospective Epic 4, item #2

---

## Objectif du document

Réduire les ambiguïtés de conception sur le cycle de vie avant la création des stories Epic 5.
Ce document est un artefact de cadrage/hardening, pas une spécification d'implémentation.

**Exploitable directement par Bob dans `/bmad-create-story` sans réinterprétation majeure.**

---

## Rappel du périmètre technique actuel (post-Epic 4)

### Topics MQTT en production

| Fonction | Pattern | Retain | QoS |
|----------|---------|--------|-----|
| Discovery config | `homeassistant/{entity_type}/jeedom2ha_{eq_id}/config` | oui | 0 |
| État principal | `jeedom2ha/{eq_id}/state` | non | 0 |
| État brightness | `jeedom2ha/{eq_id}/brightness` | non | 0 |
| État position | `jeedom2ha/{eq_id}/position` | non | 0 |
| Commande principale | `jeedom2ha/{eq_id}/set` | non | 0 |
| Commande brightness | `jeedom2ha/{eq_id}/brightness/set` | non | 0 |
| Commande position | `jeedom2ha/{eq_id}/position/set` | non | 0 |
| Disponibilité bridge | `jeedom2ha/bridge/status` | oui | 1 |
| Disponibilité locale | `jeedom2ha/{eq_id}/availability` | oui | 0 |
| Birth message HA | `homeassistant/status` | **non implémenté** | — |

> **Note :** Le discovery utilise actuellement le mode single-component (`homeassistant/{entity_type}/...`), et non le device discovery (`homeassistant/device/...`) recommandé en architecture. Ce choix n'impacte pas le cycle de vie Epic 5 mais conditionne le pattern de topic pour le cleanup 5.3.

### Identifiants techniques — état du code

| Identifiant | Format actuel vérifié | Encode le type d'entité ? |
|-------------|----------------------|--------------------------|
| `ha_unique_id` | `jeedom2ha_eq_{eq_id}` | **Non** — basé uniquement sur l'ID numérique Jeedom |
| Topic discovery | `homeassistant/{entity_type}/jeedom2ha_{eq_id}/config` | **Oui** — contient `{entity_type}` |
| `object_id` HA | `jeedom2ha_{eq_id}` | **Non** |
| Device identifier | `jeedom2ha_{eq_id}` | **Non** |

> **Conséquence pour le retypage :** un changement de `entity_type` (ex: `light` → `switch`) change le **topic** discovery mais PAS le `unique_id`. Deux topics coexistent temporairement sur le broker tant que l'ancien n'est pas nettoyé.

### Mécanismes existants post-Epic 4

- **Unpublish** : `publisher.unpublish_by_eq_id(eq_id, entity_type)` → payload vide retained sur le topic discovery
- **Deferred unpublish** : file d'attente `pending_discovery_unpublish` pour rejouer les unpublish si broker indisponible
- **Détection suppression** : `eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids` dans `/action/sync`
- **LWT** : `jeedom2ha/bridge/status` = `"offline"` configuré comme will message
- **Birth plugin** : `jeedom2ha/bridge/status` = `"online"` publié à la connexion MQTT
- **Disponibilité locale** : `jeedom2ha/{eq_id}/availability` publié selon l'état Jeedom
- **Souscription HA birth** : **non implémentée** (scope Epic 5)
- **Republication post-reboot** : **non implémentée** (scope Epic 5)

### Éligibilité — ordre de priorité actuel dans le code

```
1. Exclu (is_excluded) → reason_code: excluded_{source}  → NON publié
2. Désactivé (is_enable=false) → reason_code: disabled_eqlogic → NON publié
3. Sans commandes → reason_code: no_commands → NON publié
4. Sans type générique → reason_code: no_supported_generic_type → NON publié
5. Éligible → passe au mapping
```

> **Règle vérifiée :** `is_enable=false` rend l'équipement **non éligible**. Il n'est PAS publié, PAS mappé, et PAS soumis au moteur de confiance. L'effet MQTT est le même que l'exclusion : unpublish si était publié. La différence est le `reason_code` et le diagnostic affiché.

### Source de vérité — Rappel architectural

| Donnée | Source de vérité | Rôle du cache local |
|--------|-----------------|---------------------|
| Topologie (quels équipements existent) | Jeedom DB | Accélérateur, non autoritatif |
| État courant des commandes | Jeedom (`event::changes`) | Jamais autoritatif |
| Politique d'exclusion | Jeedom config (`configuration` JSON) | Jamais autoritatif |
| Politique de confiance | Jeedom config | Jamais autoritatif |
| Identité des entités HA | IDs numériques Jeedom | Dérivé, jamais inventé |

---

## Matrice lifecycle — Cas par cas

### Cas 1 : Reboot daemon

| Dimension | Valeur |
|-----------|--------|
| **Événement déclencheur** | Arrêt/redémarrage du processus Python daemon (manuel, cron Jeedom, crash) |
| **État Jeedom avant/après** | Inchangé — Jeedom DB et config sont persistants et non impactés |
| **État cache plugin avant** | Fichier cache disque contient le dernier inventaire connu |
| **État cache plugin après** | Rechargé depuis disque, puis revalidé contre Jeedom (source de vérité) |
| **État retained broker avant** | Discovery configs retained, availability bridge = `"offline"` (LWT tire) |
| **État retained broker après** | Discovery republié, availability bridge = `"online"`, états courants republié |
| **État HA attendu** | Entités passent `unavailable` (LWT), puis reviennent `online` avec état courant correct |
| **Source de vérité retenue** | Jeedom (topologie + états) — le cache n'est qu'un accélérateur |
| **Comportement plugin attendu** | 1. LWT tire → bridge `offline` 2. Daemon démarre 3. Charge cache disque 4. Connecte MQTT 5. Publie birth (`online`) 6. Reçoit topologie Jeedom (`getFullTopology`) 7. Réconcilie cache vs Jeedom 8. Republie discovery pour toutes les entités éligibles 9. Publie états courants |
| **Topics MQTT impactés** | `jeedom2ha/bridge/status`, tous les `homeassistant/{type}/jeedom2ha_*/config`, tous les `jeedom2ha/*/state`, `jeedom2ha/*/availability` |
| **Action discovery attendue** | Republish complet de toutes les entités éligibles |
| **Risque principal / ghost risk** | Si des équipements ont été supprimés dans Jeedom pendant le downtime daemon, le cache disque contient des entrées obsolètes → risque de ghost si le cache est utilisé sans réconciliation |
| **Invariant à préserver** | Après reboot, l'ensemble publié dans HA = exactement l'ensemble éligible dans Jeedom au moment du rescan |
| **Preuve terrain attendue** | Restart daemon → entités HA redeviennent disponibles, aucun doublon, aucun ghost, état courant correct |
| **Décision tranchée** | Le cache disque accélère le boot mais n'est JAMAIS la source de vérité. Toute divergence cache/Jeedom est résolue en faveur de Jeedom. Le rescan Jeedom est obligatoire avant toute republication. |

---

### Cas 2 : Reboot Jeedom

| Dimension | Valeur |
|-----------|--------|
| **Événement déclencheur** | Redémarrage du service Jeedom (reboot box, `systemctl restart`, mise à jour core) |
| **État Jeedom avant/après** | Inchangé structurellement — DB MySQL est persistante. Le daemon est arrêté puis relancé par le core Jeedom |
| **État cache plugin avant** | Fichier cache disque contient le dernier inventaire connu |
| **État cache plugin après** | Identique au cas 1 — le daemon est relancé par Jeedom → même séquence de boot |
| **État retained broker avant** | Discovery configs retained, availability bridge = `"offline"` (LWT tire quand le daemon s'arrête) |
| **État retained broker après** | Identique au cas 1 après redémarrage daemon |
| **État HA attendu** | Identique au cas 1 — passage par `unavailable` puis retour nominal |
| **Source de vérité retenue** | Jeedom |
| **Comportement plugin attendu** | Séquence identique au cas 1 une fois le daemon relancé par le core Jeedom. Le core gère le lifecycle start/stop via `deamon_start()` / `deamon_stop()`. |
| **Topics MQTT impactés** | Identique au cas 1 |
| **Action discovery attendue** | Republish complet |
| **Risque principal / ghost risk** | Race condition si le daemon démarre avant que MySQL soit pleinement disponible → `getFullTopology()` échoue ou retourne des données incomplètes |
| **Invariant à préserver** | Le daemon ne doit PAS republier avant d'avoir obtenu une topologie complète et valide depuis Jeedom |
| **Preuve terrain attendue** | Reboot complet box → daemon redémarre automatiquement → entités HA reviennent sans intervention manuelle |
| **Décision tranchée** | Si `getFullTopology()` échoue au boot, le daemon doit retenter périodiquement (backoff) sans publier quoi que ce soit. Publication = 0 tant que Jeedom n'a pas répondu avec succès. Pas de publication depuis le cache seul. |

---

### Cas 3 : Reboot broker MQTT

| Dimension | Valeur |
|-----------|--------|
| **Événement déclencheur** | Redémarrage du broker MQTT (Mosquitto ou autre) |
| **État Jeedom avant/après** | Inchangé |
| **État cache plugin avant/après** | Inchangé — le daemon tourne toujours |
| **État retained broker avant** | Tous les retained messages (discovery, availability) |
| **État retained broker après** | **Dépend de la persistence broker** : si Mosquitto a la persistence activée → retained conservés ; sinon → TOUS les retained sont perdus |
| **État HA attendu** | Temporairement, HA perd la connectivité MQTT. Après reconnexion : si retained perdus → HA perd toutes les entités discovery jusqu'à republication |
| **Source de vérité retenue** | Jeedom — le broker n'est JAMAIS source de vérité |
| **Comportement plugin attendu** | 1. `paho-mqtt` détecte la déconnexion 2. Reconnexion automatique (loop_start/reconnect) 3. On reconnect : republier birth (`online`), republier toute la discovery depuis le cache courant du daemon, republier états courants 4. Rejouer les `pending_discovery_unpublish` en attente |
| **Topics MQTT impactés** | Tous — la reconnexion nécessite un republish complet |
| **Action discovery attendue** | Republish complet obligatoire |
| **Risque principal / ghost risk** | Si le broker a perdu la persistence et que le daemon ne republie pas → HA n'a plus aucune entité. Risque inverse : si le broker a de la persistence ET que des entités ont été supprimées pendant le downtime broker mais que les unpublish n'ont pas été reçus → ghosts |
| **Invariant à préserver** | Après reconnexion broker, l'état discovery complet est re-établi. Source opérationnelle de republication : cache courant du daemon (synchronisé en continu avec Jeedom, source de vérité métier). |
| **Preuve terrain attendue** | `systemctl restart mosquitto` → entités HA reviennent automatiquement (avec ou sans persistence broker) |
| **Décision tranchée** | Le plugin ne fait AUCUNE hypothèse sur la persistence du broker. À chaque reconnexion MQTT, republication complète discovery + états + disponibilité depuis le cache daemon courant. C'est le seul comportement sûr. Pas de rescan Jeedom à la reconnexion broker — le cache daemon est tenu à jour en continu. |

---

### Cas 4 : Restart Home Assistant

| Dimension | Valeur |
|-----------|--------|
| **Événement déclencheur** | Redémarrage du service Home Assistant |
| **État Jeedom avant/après** | Inchangé |
| **État cache plugin avant/après** | Inchangé |
| **État retained broker avant/après** | Inchangé — le broker est indépendant de HA |
| **État HA attendu** | HA se réinitialise et publie `homeassistant/status` = `online` (birth message HA). Les entités MQTT sont redécouvertes via les retained messages existants ET via une republication du plugin. |
| **Source de vérité retenue** | Jeedom (source de vérité métier). Source opérationnelle de republication : cache courant du daemon (synchronisé en continu avec Jeedom via `event::changes` et rescans). |
| **Comportement plugin attendu** | 1. Le daemon souscrit à `homeassistant/status` (QoS 1) 2. À la réception de `online` : republication complète discovery depuis le cache courant du daemon 3. Les états courants sont republié pour que HA ait les valeurs à jour |
| **Topics MQTT impactés** | Tous les `homeassistant/{type}/jeedom2ha_*/config`, tous les `jeedom2ha/*/state` |
| **Action discovery attendue** | Republish complet depuis le cache daemon courant, déclenché par le birth message HA |
| **Risque principal / ghost risk** | Si le daemon ne souscrit pas au birth message HA → les retained broker peuvent suffire pour la redécouverte mais les états seront stales. Risque de ghost si des unpublish retained sont en attente pendant le restart HA. |
| **Invariant à préserver** | Après restart HA, l'ensemble des entités HA = l'ensemble éligible dans Jeedom (source de vérité métier), republié via le cache courant du daemon (source opérationnelle, aligné avec Jeedom en continu). |
| **Preuve terrain attendue** | Restart HA (Docker restart ou service) → toutes les entités jeedom2ha réapparaissent dans HA avec les bons états |
| **Décision tranchée** | La souscription au birth message HA (`homeassistant/status`) est OBLIGATOIRE en 5.1. La republication au birth message HA utilise le **cache courant du daemon**, PAS un rescan Jeedom. Justification : HA birth signifie "HA a redémarré et a besoin de la discovery", pas "Jeedom a changé". Le cache daemon est valide car synchronisé en continu via `event::changes` et rescans utilisateur. Un rescan Jeedom à chaque restart HA serait coûteux, lent et inutile. |

---

### Cas 5 : Renommage d'équipement

| Dimension | Valeur |
|-----------|--------|
| **Événement déclencheur** | L'utilisateur renomme un équipement dans l'interface Jeedom |
| **État Jeedom avant** | `eqLogic.name = "Lampe Salon"` ; `eqLogic.id = 123` (inchangé) |
| **État Jeedom après** | `eqLogic.name = "Lampe Bureau"` ; `eqLogic.id = 123` (inchangé) |
| **État cache plugin avant** | `name = "Lampe Salon"` pour `eq_id = 123` |
| **État cache plugin après** | Mis à jour au prochain rescan : `name = "Lampe Bureau"` pour `eq_id = 123` |
| **État retained broker avant** | Discovery avec `"name": "Lampe Salon"`, `"unique_id": "jeedom2ha_eq_123"` |
| **État retained broker après** | Discovery mis à jour avec `"name": "Lampe Bureau"`, même `unique_id`, même topic |
| **État HA attendu** | Le nom d'affichage de l'entité change. Le `unique_id` HA est inchangé. Aucun doublon. Les automations et dashboards qui référencent l'`entity_id` restent fonctionnels. |
| **Source de vérité retenue** | Jeedom (nouveau nom) |
| **Comportement plugin attendu** | 1. Au prochain rescan : détection du delta nom via comparaison topologie 2. Republication discovery sur le MÊME topic (`homeassistant/{type}/jeedom2ha_123/config`) avec le nouveau nom 3. Puisque le topic et le `unique_id` sont identiques → HA met à jour, pas de doublon |
| **Topics MQTT impactés** | `homeassistant/{type}/jeedom2ha_{eq_id}/config` (mis à jour, pas de nouveau topic) |
| **Action discovery attendue** | Republish du discovery config avec le nouveau nom sur le topic existant |
| **Risque principal / ghost risk** | AUCUN ghost risk car le topic discovery est basé sur `eq_id` (numérique, stable), pas sur le nom. Si le topic était basé sur le nom → ghost garanti (ancien topic retained non nettoyé). |
| **Invariant à préserver** | Le `unique_id` HA et le topic discovery sont basés exclusivement sur les IDs numériques Jeedom, JAMAIS sur les noms |
| **Preuve terrain attendue** | Renommer dans Jeedom → rescan → entité HA a le nouveau nom, même `entity_id`, aucun doublon dans l'UI HA |
| **Décision tranchée** | Le renommage est un cas nominal sans risque SI et SEULEMENT SI les identifiants sont basés sur les IDs numériques. C'est déjà le cas. Aucun cleanup topic n'est nécessaire. |

---

### Cas 6 : Suppression réelle d'équipement

| Dimension | Valeur |
|-----------|--------|
| **Événement déclencheur** | L'utilisateur supprime un équipement dans Jeedom (suppression DB) |
| **État Jeedom avant** | `eqLogic.id = 123` existe dans la DB |
| **État Jeedom après** | `eqLogic.id = 123` n'existe plus dans la DB |
| **État cache plugin avant** | Entrée pour `eq_id = 123` avec décision de publication |
| **État cache plugin après** | Au prochain rescan : entrée retirée du cache (réconciliation) |
| **État retained broker avant** | Discovery retained pour `homeassistant/{type}/jeedom2ha_123/config` |
| **État retained broker après** | Payload vide retained publié → HA supprime l'entité. Availability locale nettoyée. |
| **État HA attendu** | L'entité disparaît de HA. Les automations référençant cette entité signaleront une entité manquante. |
| **Source de vérité retenue** | Jeedom (absence dans la topologie = suppression) |
| **Comportement plugin attendu** | 1. Rescan : `eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids` (mécanisme existant) 2. Pour chaque `eq_id` supprimé : `unpublish_by_eq_id(eq_id, entity_type)` → payload vide retained 3. Nettoyage de l'availability locale : payload vide retained sur `jeedom2ha/{eq_id}/availability` 4. Retrait de l'entrée du cache local 5. Log `[MAPPING] eq_id=123 est devenu inéligible ou supprimé → MQTT unpublish effectif` |
| **Topics MQTT impactés** | `homeassistant/{type}/jeedom2ha_{eq_id}/config` (vidé), `jeedom2ha/{eq_id}/availability` (vidé) |
| **Action discovery attendue** | Payload vide retained sur le topic discovery — commande de suppression pour HA |
| **Risque principal / ghost risk** | Si le rescan n'a pas lieu (daemon non actif au moment de la suppression) → le retained discovery reste sur le broker → ghost dans HA jusqu'au prochain rescan. Si le broker est indisponible au moment du unpublish → deferred unpublish. |
| **Invariant à préserver** | Tout équipement absent de la topologie Jeedom lors d'un rescan DOIT être unpublié. Pas de seuil, pas de délai de grâce. Absent = supprimé. |
| **Preuve terrain attendue** | Supprimer un équipement dans Jeedom → rescan → entité disparaît de HA → topic discovery vérifié vide via `mosquitto_sub` |
| **Décision tranchée** | La suppression est détectée par différence d'ensembles (`anciens - nouveaux`). L'absence dans la topologie Jeedom est interprétée comme suppression, pas comme indisponibilité temporaire. Voir Décision 3 pour la distinction supprimé vs désactivé vs indisponible. |

---

### Cas 7 : Exclusion manuelle d'équipement

| Dimension | Valeur |
|-----------|--------|
| **Événement déclencheur** | L'utilisateur ajoute un équipement (ou son plugin source, ou son objet Jeedom) aux critères d'exclusion |
| **État Jeedom avant** | Équipement éligible et publié |
| **État Jeedom après** | Équipement toujours dans la DB, mais configuré comme exclu |
| **État cache plugin avant** | Entrée avec décision `published` |
| **État cache plugin après** | Au prochain rescan : entrée avec décision `excluded` |
| **État retained broker avant** | Discovery retained pour l'équipement |
| **État retained broker après** | Payload vide retained publié → HA supprime l'entité |
| **État HA attendu** | L'entité disparaît de HA. L'équipement reste visible dans le diagnostic avec raison "Exclu". |
| **Source de vérité retenue** | Jeedom config (critères d'exclusion) |
| **Comportement plugin attendu** | 1. Au prochain rescan : le filtre d'exclusion s'applique AVANT le mapping 2. Si l'équipement était publié → `unpublish_by_eq_id()` 3. Si broker indisponible → `_defer_discovery_unpublish()` 4. L'entrée diagnostic reflète le statut "Exclu" avec la raison applicable |
| **Topics MQTT impactés** | `homeassistant/{type}/jeedom2ha_{eq_id}/config` (vidé), `jeedom2ha/{eq_id}/availability` (vidé) |
| **Action discovery attendue** | Payload vide retained |
| **Risque principal / ghost risk** | Si le unpublish est déféré ET que le daemon redémarre avant replay → le ghost persiste. Le mécanisme `pending_discovery_unpublish` est en RAM, pas persisté sur disque. |
| **Invariant à préserver** | Un équipement exclu ne doit JAMAIS être publié. L'exclusion prime sur le mapping. |
| **Preuve terrain attendue** | Exclure un équipement → rescan → disparition HA → vérifier que le diagnostic le montre comme "Exclu" |
| **Décision tranchée** | L'exclusion et la suppression produisent le MÊME effet sur le broker (unpublish). La différence est uniquement dans le diagnostic : "Exclu" vs "Supprimé". L'équipement exclu reste visible dans le diagnostic, l'équipement supprimé en sort. |

---

### Cas 8 : Changement de politique de confiance

| Dimension | Valeur |
|-----------|--------|
| **Événement déclencheur** | L'utilisateur change la politique de confiance (ex: `sure_probable` → `sure_only` ou inverse) |
| **État Jeedom avant** | Politique `sure_probable`, certaines entités publiées avec confiance `probable` |
| **État Jeedom après** | Politique `sure_only` |
| **État cache plugin avant** | Entités `probable` ont `decision = published` |
| **État cache plugin après** | Au prochain rescan : entités `probable` ont `decision = not_published` (confiance insuffisante) |
| **État retained broker avant** | Discovery retained pour les entités `probable` |
| **État retained broker après** | Payload vide retained pour les entités `probable` → HA les supprime |
| **État HA attendu** | Les entités `probable` disparaissent. Les entités `sure` restent. |
| **Source de vérité retenue** | Jeedom config (politique de confiance) |
| **Comportement plugin attendu** | (Mécanisme déjà implémenté en 4.3) 1. Rescan : chaque mapping est évalué contre la nouvelle politique 2. Les entités `probable` précédemment publiées sous `sure_probable` → unpublish 3. Le mécanisme `_needs_discovery_unpublish()` détecte le changement 4. Deferred unpublish si broker indisponible |
| **Topics MQTT impactés** | `homeassistant/{type}/jeedom2ha_{eq_id}/config` pour chaque entité `probable` nouvellement exclue |
| **Action discovery attendue** | Payload vide retained pour chaque entité restreinte par la nouvelle politique |
| **Risque principal / ghost risk** | Identique au cas 7 : si unpublish déféré + redémarrage daemon → ghost. Risque UX : l'utilisateur ne comprend pas pourquoi des entités disparaissent → le diagnostic doit expliquer. |
| **Invariant à préserver** | L'ensemble publié = exactement l'ensemble autorisé par la politique courante. Pas de "grandfathering" d'entités publiées sous une ancienne politique. |
| **Preuve terrain attendue** | Passer de `sure_probable` à `sure_only` → rescan → les entités `probable` disparaissent de HA → le diagnostic les montre avec raison "Confiance insuffisante pour la politique active" |
| **Décision tranchée** | Le changement de politique a déjà un mécanisme fonctionnel (4.3). Pour Epic 5, il faut s'assurer que la republication post-reboot (5.1) respecte la politique courante, et que le cleanup (5.3) ne nettoie pas des entités légitimes sous la politique courante. |

---

## Décisions explicites

### Décision 1 : Ordre de vérité au redémarrage

**Arbitrage :** La séquence au redémarrage du daemon est strictement ordonnée :

```
1. Charger le cache disque (warm start — accélérateur, pas de publication)
2. Connecter le broker MQTT
3. Publier le birth message (bridge = online)
4. Interroger Jeedom (getFullTopology via bootstrapRuntimeAfterDaemonStart)
5. Réconcilier cache vs topologie Jeedom :
   a. Nouveaux équipements → publier discovery
   b. Équipements inchangés → republier discovery (refresh retained)
   c. Équipements modifiés → republier discovery mis à jour
   d. Équipements disparus → unpublish (payload vide retained)
   e. Équipements exclus → unpublish si étaient publiés
   f. Équipements désactivés (is_enable=false) → unpublish si étaient publiés
6. Publier les états courants pour toutes les entités publiées
7. Publier la disponibilité locale pour toutes les entités
```

**Justification :**
- L'étape 1 avant l'étape 4 permet un boot rapide : le cache sert à identifier les deltas et les unpublish nécessaires.
- L'étape 3 (birth) AVANT l'étape 4 est un choix : HA sait que le bridge est en ligne même si le rescan prend du temps. Alternative : publier le birth APRÈS le rescan complet. Le choix retenu est "bridge online signifie que le daemon est actif et connecté au broker, pas que le rescan est terminé". La disponibilité des entités individuelles est gérée par les availability topics par entité, pas par le bridge status.
- L'étape 4 est bloquante : AUCUNE publication discovery ne se fait avant d'avoir reçu une réponse valide de Jeedom. Si Jeedom est indisponible → le daemon attend (backoff exponentiel) sans rien publier.
- L'étape 5b (republish des inchangés) est nécessaire car le broker a pu perdre ses retained messages (redémarrage sans persistence).

**Règle de sécurité :** Si `getFullTopology()` échoue, le daemon ne publie RIEN. Pas de fallback sur le cache seul. Le cache accélère, il n'autorise pas.

---

### Décision 2 : Frontière exacte du cleanup 5.3

**Arbitrage :** Le cleanup 5.3 ne nettoie un topic discovery que si les **deux conditions de périmètre** sont vérifiées ET qu'**au moins une condition de cleanup** est remplie :

**Conditions de périmètre (toutes requises) :**
1. Le topic est dans le namespace plugin : `homeassistant/{entity_type}/jeedom2ha_*/config`
2. L'`eq_id` extrait du topic est un équipement connu du plugin (présent dans le cache du scan précédent ou du scan courant)

**Conditions de cleanup (au moins une requise) :**
3. L'`eq_id` est absent de la topologie Jeedom actuelle (suppression)
4. L'`eq_id` est désormais non éligible : exclu, désactivé (`is_enable=false`), sans commandes, sans type générique
5. La confiance de l'`eq_id` ne satisfait plus la politique courante (ex: `probable` sous politique `sure_only`)
6. L'`entity_type` du topic ne correspond plus au type produit par le mapping actuel (retypage — l'ancien topic est nettoyé, le nouveau est publié)

**Formule :** `cleanup(topic) = périmètre(1 ET 2) ET (3 OU 4 OU 5 OU 6)`

**Ce que le cleanup 5.3 ne fait PAS :**

- Ne nettoie JAMAIS un topic hors du namespace `jeedom2ha_*`
- Ne fait JAMAIS de wildcard subscribe + purge sur `homeassistant/#`
- Ne nettoie PAS les topics d'état (`jeedom2ha/*/state`) — ils ne sont pas retained, ils expirent naturellement
- Ne nettoie PAS les topics de commande (`jeedom2ha/*/set`) — ce sont des souscriptions, pas des retained
- Ne nettoie PAS les retained d'autres plugins ou intégrations HA

**Cleanup des topics d'availability locale :**

- `jeedom2ha/{eq_id}/availability` est retained → doit être nettoyé (payload vide retained) quand l'équipement est supprimé, exclu ou désactivé
- `jeedom2ha/bridge/status` n'est JAMAIS nettoyé par le cleanup 5.3 — il est géré par le LWT

**Justification :** Le cleanup est chirurgical et basé sur la comparaison d'ensembles (anciens vs nouveaux), pas sur une exploration du broker. Cela évite tout effet de bord sur les topics d'autres intégrations.

---

### Décision 3 : Distinction supprimé vs exclu vs désactivé vs indisponible vs renommé vs retypé

| État | Réalité Jeedom | Comment détecté | Action discovery | Action availability | Visible dans diagnostic | Réversible |
|------|---------------|-----------------|-----------------|--------------------|-----------------------|-----------|
| **Supprimé** | `eq_id` absent de la topologie | Diff d'ensembles au rescan | Payload vide retained (suppression HA) | Payload vide retained | Non — l'entrée sort du diagnostic | Non (suppression DB) |
| **Exclu** | `eq_id` présent, `is_excluded=true` | Filtre d'exclusion avant mapping | Payload vide retained (suppression HA) | Payload vide retained | Oui — reason "Exclu (par équipement / par plugin / par objet)" | Oui (retirer l'exclusion → rescan) |
| **Désactivé** | `eq_id` présent, `is_enable=false` | Check éligibilité (`assess_eligibility`) | Payload vide retained (suppression HA) | Payload vide retained | Oui — reason "Désactivé dans Jeedom" | Oui (réactiver dans Jeedom → rescan) |
| **Indisponible** | `eq_id` présent, `is_enable=true`, publié, mais module physique injoignable | Détection par Jeedom (ex: `no_signal`, timeout) relayée par le plugin | **Aucune** — discovery inchangé | `availability` → `"offline"` | Oui — statut "Publié" + availability dégradée | Oui (module revient → availability `"online"`) |
| **Renommé** | `eq_id` présent, `name` différent du cache | Comparaison `name` cache vs topologie | Republish discovery avec nouveau nom, même topic | Aucun changement | Oui — statut "Publié" (nom mis à jour) | Oui (re-renommer) |
| **Retypé** | `eq_id` présent, `generic_type` changé → `entity_type` HA change | Comparaison du résultat de mapping vs cache | Unpublish ancien topic + publish nouveau topic | Republish sur le nouveau topic | Oui — rupture notée dans le diagnostic | Oui (re-modifier generic_type) |

**Règle critique — Désactivé (`is_enable=false`) :**
Un équipement désactivé dans Jeedom est traité comme **non éligible** par le daemon. L'effet MQTT est identique à l'exclusion : unpublish si était publié. La différence avec l'exclusion est :
- Le `reason_code` est `disabled_eqlogic` (pas `excluded_*`)
- Le diagnostic affiche "Cet équipement est désactivé dans Jeedom" avec remédiation "Activez l'équipement dans sa page de configuration Jeedom"
- L'ordre d'évaluation est : Exclu > **Désactivé** > Sans commandes > Sans type générique

**Règle critique — Indisponible vs Désactivé :**
Ces deux états sont **fondamentalement différents** :
- **Désactivé** = choix utilisateur dans Jeedom → non publié, discovery supprimé
- **Indisponible** = situation physique (module Z-Wave mort, réseau coupé) → publié mais availability `"offline"`

L'indisponibilité physique ne provoque PAS un unpublish. L'entité reste dans HA, marquée `unavailable`. L'utilisateur comprend que l'équipement existe mais ne répond plus.

**Règle critique — Retypé :**
Le retypage est le cas le plus complexe. État vérifié dans le code :
- Le `ha_unique_id` (`jeedom2ha_eq_{id}`) n'encode PAS le type d'entité → il reste stable lors d'un retypage
- Le topic discovery (`homeassistant/{entity_type}/jeedom2ha_{eq_id}/config`) encode le type → il CHANGE lors d'un retypage
- Conséquence : l'ancien topic retained reste sur le broker avec l'ancien type, le nouveau topic est publié avec le nouveau type. Sans cleanup explicite de l'ancien topic, les deux coexistent → **ghost garanti**.

**Décision V1 sur le retypage :** Le retypage est une **rupture connue et acceptée**, pas un cas nominal de la promesse de stabilité Epic 5. Comportement V1 :
1. Unpublish de l'ancien topic (payload vide retained sur `homeassistant/{ancien_type}/jeedom2ha_{eq_id}/config`)
2. Publish du nouveau topic (discovery normal sur `homeassistant/{nouveau_type}/jeedom2ha_{eq_id}/config`)
3. Le `unique_id` HA ne change pas (`jeedom2ha_eq_{id}`)
4. L'`entity_id` HA peut changer (HA dérive l'entity_id du component type + object_id) → **rupture potentielle d'automations HA**
5. Le diagnostic signale explicitement la rupture

**Pré-requis pour le cleanup de retypage :** le cache doit persister le `entity_type` précédent pour chaque `eq_id`, afin de pouvoir unpublish le bon ancien topic.

---

### Décision 4 : Retained existant mais entité encore valide vs retained obsolète à nettoyer

| Situation | Définition | Action |
|-----------|-----------|--------|
| **Retained valide** | Le topic discovery retained correspond à un `eq_id` présent dans la topologie Jeedom ET éligible (enabled, non exclu, type générique présent) ET autorisé par la politique courante | **Republish** — écraser le retained avec la version fraîche (noms à jour, availability, etc.) |
| **Retained obsolète — suppression** | Le topic discovery retained correspond à un `eq_id` absent de la topologie Jeedom | **Cleanup** — payload vide retained pour supprimer l'entité HA |
| **Retained obsolète — exclusion** | Le topic discovery retained correspond à un `eq_id` présent mais exclu | **Cleanup** — payload vide retained |
| **Retained obsolète — désactivé** | Le topic discovery retained correspond à un `eq_id` présent mais `is_enable=false` | **Cleanup** — payload vide retained |
| **Retained obsolète — politique** | Le topic discovery retained correspond à un `eq_id` présent mais dont la confiance ne satisfait plus la politique | **Cleanup** — payload vide retained |
| **Retained obsolète — retypage** | Le topic discovery retained correspond à un ancien `entity_type` pour un `eq_id` dont le type a changé | **Cleanup** — payload vide retained sur l'ancien topic ; publish sur le nouveau topic |
| **Retained orphelin** | Le topic retained est dans le namespace `jeedom2ha_*` mais l'`eq_id` n'est connu ni du cache ni de la topologie Jeedom (ex: équipement publié par une version précédente du plugin puis supprimé hors scan) | **Pas de cleanup proactif en V1.** Le plugin ne peut pas deviner quels topics orphelins existent sur le broker sans wildcard subscribe. Voir question ouverte Q2. |

**Justification :** La distinction se fait par comparaison d'ensembles entre le registre connu du plugin (cache + topologie) et la source de vérité Jeedom. Les retained orphelins (publiés par une version antérieure du plugin et dont le plugin a perdu la trace) sont un cas limite hors scope V1 — un cleanup manuel via `deploy-to-box.sh --stop-daemon-cleanup` ou un outil dédié peut les adresser.

---

### Décision 5 : Comportement si HA, broker et Jeedom sont temporairement désalignés

**Scénarios de désalignement :**

| Scénario | Jeedom | Broker | HA | Comportement daemon |
|----------|--------|--------|----|-------------------|
| **A — Nominal** | UP | UP | UP | Fonctionnement normal |
| **B — Broker down** | UP | DOWN | UP (stale) | Daemon tourne, accumule les changements d'état, retente la connexion MQTT. Deferred unpublish s'accumulent. HA voit les entités comme `unavailable` (LWT retenu). |
| **C — HA down** | UP | UP | DOWN | Daemon et broker fonctionnent normalement. Les publications continuent (retained). Quand HA revient → birth message → republication discovery depuis le cache courant du daemon. |
| **D — Jeedom API down** | API DOWN | UP | UP | Daemon tourne mais ne peut pas rescanner. Pas de publication ni de modification. L'état HA est figé sur la dernière version connue. Le daemon retente périodiquement `getFullTopology`. |
| **E — Daemon seul** | DOWN | UP | UP | LWT tire → bridge `offline` → HA marque toutes les entités `unavailable`. Retained discovery reste. |
| **F — Tout down sauf Jeedom** | UP | DOWN | DOWN | Daemon peut tourner en mode dégradé (collecte `event::changes`). Aucune publication possible. À la remontée du broker → reconnexion + republish complet depuis le cache daemon. |
| **G — Triple panne puis reprise** | UP (après restart) | UP (après restart) | UP (après restart) | Le DERNIER à redémarrer déclenche la réconciliation. Si le daemon est le dernier → cas 1 (reboot daemon). Si HA est le dernier → birth message + republish depuis cache. |

**Règle de résilience :**
- Le daemon ne panique jamais. Il retente les opérations échouées avec backoff.
- Les publications sont idempotentes — republier un discovery identique est un no-op pour HA.
- Les unpublish non réalisés sont déférés en RAM (mécanisme existant `pending_discovery_unpublish`).
- En cas de désalignement persistant, l'utilisateur peut toujours déclencher un rescan manuel (mécanisme existant depuis Epic 4).

**Décision critique :** L'état du broker n'est JAMAIS lu pour déterminer la vérité. Le daemon ne souscrit PAS à ses propres topics discovery pour vérifier ce que le broker retient. La vérité est Jeedom → le daemon publie. Le broker transporte. HA consomme.

---

### Décision 6 : Republication sur birth message HA — cache courant, pas rescan

**Arbitrage :** Quand le daemon reçoit `homeassistant/status` = `online`, il republie la discovery complète depuis le **cache courant en RAM**, sans rescanner Jeedom.

**Justification :**
- Le birth message HA signifie "HA a redémarré et a besoin de la discovery", pas "Jeedom a changé".
- Le cache daemon est valide car synchronisé en continu via `event::changes` (états) et les rescans utilisateur (topologie).
- Rescanner Jeedom à chaque restart HA serait coûteux (appel PHP + parsing topologie) et inutile.

**La même règle s'applique à la reconnexion broker** (Cas 3) : le daemon republie depuis le cache courant, pas via un rescan Jeedom. La raison est identique — si le daemon tourne, son cache est à jour.

**Seul le boot du daemon (Cas 1, 2) nécessite un rescan Jeedom**, car le cache disque peut être périmé (équipements ajoutés/supprimés pendant le downtime).

---

### Décision 7 : Backoff Jeedom au bootstrap daemon

**Arbitrage :** Si Jeedom est indisponible au boot du daemon :

- Le daemon reste actif et retente `getFullTopology` avec **backoff exponentiel** : 1s, 2s, 4s, 8s, plafond 60s.
- **Pas d'abandon.** Le daemon ne s'arrête jamais de lui-même à cause d'une indisponibilité Jeedom.
- Le bridge status reste `"online"` (le daemon est bien actif et connecté au broker) mais **aucune entité n'est publiée** tant que Jeedom n'a pas répondu.
- Un log `WARNING [BOOTSTRAP] Jeedom API indisponible — retry dans Ns` est émis à chaque tentative échouée.

**Justification :**
- Arrêter le daemon forcerait Jeedom à le relancer (cron), créant un cycle start/stop coûteux.
- Le daemon actif sans entités publiées est un état explicable et inoffensif — HA voit le bridge online mais aucune entité, ce qui est cohérent avec "le système démarre".

---

### Décision 8 : Lissage de la republication post-redémarrage

**Arbitrage :** La republication post-reboot est étalée dans le temps via un **délai fixe entre chaque publication discovery** :

```
delay = max(0.1, 10.0 / nb_entites)
```

Pour chaque entité publiée : `await asyncio.sleep(delay)` entre chaque `publish`.

**Garantie :** Le lot complet prend au minimum 10 secondes pour les parcs > 100 entités. Pour les petits parcs (< 100 entités), le délai minimum de 0.1s par entité s'applique.

**Justification :**
- NFR3 exige un lissage > 10s pour la republication post-redémarrage.
- Le délai dynamique adapte automatiquement la cadence à la taille du parc.
- `asyncio.sleep` est non-bloquant pour le daemon — les autres tâches (écoute commandes, `event::changes`) continuent pendant le lissage.

**S'applique à :** boot daemon (Cas 1, 2), reconnexion broker (Cas 3), birth message HA (Cas 4).

---

## Invariants lifecycle Epic 5

Les invariants suivants doivent être vrais à tout moment, vérifiables par test, et jamais violés par une story :

1. **INV-1 — Jeedom est la source de vérité.** Le cache local et le broker ne sont jamais autoritatifs. Toute divergence est résolue en faveur de Jeedom.

2. **INV-2 — Pas de publication sans réponse Jeedom.** Le daemon ne publie AUCUN discovery tant qu'il n'a pas reçu une topologie valide depuis Jeedom. Pas de publication depuis le cache seul. S'applique uniquement au boot — pas aux republications sur birth HA ou reconnexion broker (Décision 6).

3. **INV-3 — Pas de ghost durable.** Tout équipement absent de la topologie Jeedom lors d'un rescan est unpublié. L'absence = suppression, pas indisponibilité temporaire.

4. **INV-4 — IDs stables basés sur Jeedom.** Le `unique_id` HA (`jeedom2ha_eq_{id}`) et le topic discovery sont dérivés des IDs numériques Jeedom. Un renommage ne change jamais le `unique_id` ni le topic.

5. **INV-5 — Republication complète à chaque reconnexion.** Après reconnexion broker ou birth message HA, le plugin republie l'intégralité du discovery depuis le cache courant — pas un sous-ensemble.

6. **INV-6 — Exclusion prime sur tout.** Un équipement exclu n'est jamais publié, quelle que soit sa confiance ou son historique de publication.

7. **INV-7 — Politique de confiance appliquée uniformément.** La politique courante s'applique à chaque rescan. Pas de "grandfathering" d'entités publiées sous une politique précédente.

8. **INV-8 — Unpublish déféré en cas d'indisponibilité broker.** Si un unpublish ne peut pas être exécuté (broker down), il est mis en file d'attente et rejoué dès que possible.

9. **INV-9 — Lissage de charge.** La republication post-reboot est étalée dans le temps (Décision 8) pour ne pas saturer la box Jeedom.

10. **INV-10 — Aucun fallback silencieux.** Toute erreur de lifecycle (échec Jeedom API, échec unpublish, broker indisponible) est loguée explicitement avec un `reason_code`. Jamais de fail silencieux.

11. **INV-11 — Désactivé = non publié.** Un équipement avec `is_enable=false` est traité comme non éligible et non publié. Jamais comme "indisponible".

---

## Questions encore ouvertes avant create-story

### Q1 — Persistence du `pending_discovery_unpublish`

Le mécanisme `pending_discovery_unpublish` est en RAM. Si le daemon redémarre avant replay, les unpublish déférés sont perdus. Au prochain boot, le rescan détectera-t-il automatiquement les équipements à unpublier ?

**Analyse :** Oui, si le rescan Jeedom au boot compare la topologie courante au cache disque (qui contient les entrées publiées avant la panne). La condition est que le cache disque persiste l'état "publié" et le `entity_type` pour chaque `eq_id`. Si c'est le cas, `eq_ids_supprimes = anciens_eq_ids (cache) - nouveaux_eq_ids (Jeedom)` couvrira les suppressions, et la comparaison d'`entity_type` couvrira les retypages.

**Action requise :** Vérifier dans la story 5.1 que la réconciliation au boot couvre ce cas. Si le cache disque ne persiste pas la décision "publié" + `entity_type`, il faut l'ajouter.

### Q2 — Nettoyage des retained orphelins

Si un équipement a été publié par une version antérieure du plugin (topic discovery retained sur le broker), puis le plugin a été réinstallé ou le cache purgé, le plugin n'a plus trace de cette publication. Comment nettoyer ?

**Options :**
- (A) Ignore en V1 — nettoyage manuel via `--stop-daemon-cleanup`
- (B) Wildcard subscribe `homeassistant/+/jeedom2ha_*/config` au boot pour inventorier les retained, puis unpublish de ceux hors topologie
- (C) Outil admin dédié dans l'UI (bouton "Nettoyer les orphelins")

**Action requise :** Trancher avant story 5.3. Recommandation : option (A) pour V1.

### Q3 — Retypage d'équipement et multi-entity

Actuellement, un `eq_id` = un topic discovery (un seul `entity_type`). Si un équipement Jeedom a des commandes qui pourraient produire à la fois un `light` et des `sensor`, le cleanup doit-il gérer le cas multi-topic par `eq_id` ?

**Action requise :** Documenter la limitation V1 (un `eq_id` = une entité HA) dans la story 5.3.

---

## Impacts directs sur la spec 5.1

**Story 5.1 : Persistance et Republication Post-Reboot**

1. **Séquence de boot** : implémenter l'ordre de vérité de la Décision 1. Le bootstrap existant (`bootstrapRuntimeAfterDaemonStart`) est le point d'entrée mais doit être enrichi.

2. **Souscription au birth message HA** : ajouter la souscription à `homeassistant/status` (QoS 1). À la réception de `online` → republication complète discovery depuis le cache courant du daemon (Décision 6 — pas de rescan Jeedom).

3. **Reconnexion broker** : sur `on_connect` MQTT (reconnexion) → republication complète discovery + états + availability depuis le cache courant du daemon (Décision 6).

4. **Réconciliation boot** : au boot, comparer cache disque vs topologie Jeedom :
   - Nouveaux → publier
   - Supprimés → unpublish
   - Modifiés (nom, area, type) → republier avec les mises à jour (+ unpublish ancien topic si retypage)
   - Inchangés → republier (refresh retained)
   - Désactivés (`is_enable=false`) → unpublish si étaient publiés (INV-11)

5. **Lissage** : implémenter le throttling de republication (Décision 8) — délai dynamique `max(0.1, 10.0/nb_entites)` entre chaque publish.

6. **Backoff Jeedom** : si Jeedom est indisponible au boot → Décision 7 (backoff exponentiel, aucune publication, log WARNING).

7. **Invariants à tester** : INV-1, INV-2, INV-3, INV-5, INV-8, INV-9, INV-10, INV-11.

8. **Hypothèses de plateforme** (action item retro #1) :
   - Le cache disque est rechargé par `json.load` depuis `data/`
   - Le bootstrap PHP (`bootstrapRuntimeAfterDaemonStart`) fournit la topologie Jeedom complète
   - L'état retained broker peut être absent (broker sans persistence)
   - `paho-mqtt` `on_connect` est appelé à chaque reconnexion (pas seulement la première)
   - Le cache disque doit persister `entity_type` + décision "publié" par `eq_id` pour permettre la réconciliation boot (Q1)

9. **Runbook terrain minimal** :
   - Restart daemon → vérifier entités HA reviennent
   - Restart broker (Mosquitto) → vérifier entités HA reviennent
   - Restart HA → vérifier entités HA reviennent
   - Restart complet box → vérifier récupération automatique

---

## Impacts directs sur la spec 5.2

**Story 5.2 : Stabilité des Identifiants et Renommages**

1. **Détection de renommage** : comparer `name` dans le cache vs `name` dans la topologie Jeedom. Si différent ET `eq_id` identique → renommage.

2. **Republication de discovery** : republier le discovery config sur le MÊME topic avec le nouveau `name`. Le `unique_id` (`jeedom2ha_eq_{id}`) et le topic ne changent pas.

3. **Pas de cleanup nécessaire** : le renommage n'implique aucun unpublish car le topic est basé sur l'ID, pas le nom. C'est un update in-place.

4. **Cas du renommage d'objet Jeedom** (pièce/area) : le `suggested_area` change. Republier le discovery avec le nouveau `suggested_area`. HA peut ou non mettre à jour l'area automatiquement — c'est un comportement HA, pas un engagement plugin.

5. **Cas du retypage** (Décision 3) : si le renommage s'accompagne d'un changement de `generic_type` → traiter comme suppression + recréation. Topic change → unpublish ancien + publish nouveau. C'est une rupture acceptée en V1, pas un cas de renommage.

6. **Invariants à tester** : INV-4.

7. **Hypothèses de plateforme** :
   - Le `name` Jeedom est mutable, l'`id` Jeedom est immuable
   - Le topic discovery est dérivé de l'`eq_id`, pas du `name`
   - HA met à jour le `friendly_name` quand le discovery config est republié avec un nouveau `name` et le même `unique_id`

8. **Test terrain early** (action item retro — parallèle) :
   - Renommer un équipement réel dans Jeedom → rescan → vérifier dans HA : nom mis à jour, pas de doublon, automations intactes
   - Exécuter dès Day-1 de 5.2

---

## Impacts directs sur la spec 5.3

**Story 5.3 : Nettoyage Automatique et Gestion des Écarts**

1. **Périmètre de cleanup** (Décision 2) : uniquement `homeassistant/{type}/jeedom2ha_*/config` ET `jeedom2ha/{eq_id}/availability` pour les `eq_id` supprimés, désactivés ou exclus.

2. **Mécanisme de détection** : `eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids` (mécanisme existant depuis 4.3, à enrichir pour 5.3).

3. **Distinction supprimé vs désactivé vs indisponible** (Décision 3) :
   - Absent de la topologie Jeedom = **supprimé** → unpublish discovery
   - Présent mais `is_enable=false` = **désactivé** → unpublish discovery (INV-11)
   - Présent, `is_enable=true`, publié, module physique injoignable = **indisponible** → availability `"offline"`, discovery **inchangé**
   - La spec 5.3 doit documenter cette distinction explicitement

4. **Retypage** (Décision 3) :
   - Si le `entity_type` a changé entre deux rescans → unpublish ancien topic + publish nouveau topic
   - Le cache doit persister le `entity_type` précédent pour pouvoir unpublish le bon topic
   - Le `unique_id` ne change PAS (`jeedom2ha_eq_{id}`) mais l'`entity_id` HA peut changer → rupture acceptée V1
   - Le diagnostic signale la rupture

5. **Retained orphelins** (Q2) : hors scope V1. Documenter la limitation et le workaround (`--stop-daemon-cleanup`).

6. **Nettoyage availability locale** : quand un équipement est supprimé, désactivé ou exclu → publier payload vide retained sur `jeedom2ha/{eq_id}/availability` en plus du topic discovery.

7. **Diagnostic** : la suppression d'un équipement doit apparaître dans le diagnostic uniquement pendant le rescan courant (log), puis l'entrée sort du diagnostic (l'équipement n'existe plus). Les équipements désactivés restent dans le diagnostic avec reason "Désactivé".

8. **Invariants à tester** : INV-3, INV-6, INV-7, INV-8, INV-11.

9. **Hypothèses de plateforme** :
   - Le payload vide retained (`""`) sur un topic discovery fait disparaître l'entité dans HA (spec MQTT Discovery)
   - Le broker supporte le publish d'un payload vide avec retain=True
   - Un topic discovery nettoyé (payload vide) ne persiste pas dans le broker après le nettoyage (le broker supprime le retained)

10. **Preuve terrain obligatoire** :
    - Supprimer un équipement réel dans Jeedom → rescan → vérifier dans HA : entité supprimée → vérifier sur le broker : topic discovery vide
    - Désactiver un équipement (`is_enable=false`) → rescan → vérifier : entité supprimée de HA, diagnostic montre "Désactivé"
    - Réactiver l'équipement → rescan → vérifier : entité republiée dans HA
    - Vérifier qu'un équipement indisponible (module physique HS) reste publié dans HA avec availability `"offline"`

---

## Runbooks terrain minimaux à exiger dans les futures stories

Chaque story Epic 5 touchant le lifecycle ou la persistence DOIT inclure un runbook terrain avec les preuves suivantes :

### Runbook type — Story 5.1 (Republication post-reboot)

```
PRE-CONDITIONS :
- Box Jeedom de test avec daemon actif et entités publiées dans HA
- deploy-to-box.sh --cleanup-discovery --restart-daemon exécuté avec succès

TEST 1 — Restart daemon
1. Arrêter le daemon (Jeedom UI ou CLI)
2. Vérifier : HA → toutes les entités jeedom2ha passent "unavailable"
3. Redémarrer le daemon
4. Vérifier : HA → toutes les entités reviennent "available" avec état correct
5. Preuve : capture log daemon montrant la séquence bootstrap complète

TEST 2 — Restart broker
1. systemctl restart mosquitto
2. Vérifier : daemon reconnecte automatiquement
3. Vérifier : HA → entités reviennent disponibles
4. Preuve : log daemon montrant reconnexion + republish depuis cache courant

TEST 3 — Restart HA
1. Restart Home Assistant (Docker ou service)
2. Vérifier : HA publie homeassistant/status = online (mosquitto_sub)
3. Vérifier : daemon republie discovery depuis cache courant (log)
4. Vérifier : HA → entités redécouvertes avec état correct
5. Preuve : log daemon montrant la détection du birth message + republish

TEST 4 — Reboot complet box
1. Reboot la box Jeedom
2. Attendre le démarrage complet (Jeedom + daemon)
3. Vérifier : HA → entités disponibles, état correct, aucun ghost
4. Preuve : capture log daemon post-reboot
```

### Runbook type — Story 5.2 (Renommages)

```
PRE-CONDITIONS :
- Au moins un équipement publié dans HA avec nom connu

TEST 1 — Renommage simple
1. Renommer l'équipement dans Jeedom UI
2. Déclencher un rescan
3. Vérifier dans HA : nom mis à jour, unique_id inchangé, pas de doublon
4. Preuve : mosquitto_sub sur le topic discovery → payload avec nouveau nom

TEST 2 — Renommage d'objet Jeedom (pièce)
1. Renommer l'objet Jeedom contenant l'équipement
2. Rescan
3. Vérifier : suggested_area mis à jour dans le discovery
4. Preuve : payload discovery contient le nouveau suggested_area
```

### Runbook type — Story 5.3 (Cleanup)

```
PRE-CONDITIONS :
- Au moins un équipement publié dans HA

TEST 1 — Suppression
1. Supprimer l'équipement dans Jeedom UI
2. Rescan
3. Vérifier dans HA : entité supprimée
4. Vérifier sur broker : mosquitto_sub -t "homeassistant/+/jeedom2ha_{eq_id}/config" -C 1 → vide
5. Vérifier availability : jeedom2ha/{eq_id}/availability → vide
6. Preuve : log daemon avec reason_code de suppression

TEST 2 — Suppression pendant daemon arrêté
1. Arrêter le daemon
2. Supprimer un équipement dans Jeedom
3. Redémarrer le daemon
4. Vérifier : l'équipement est détecté comme supprimé et unpublié au boot
5. Preuve : log daemon montrant la réconciliation boot → unpublish

TEST 3 — Désactivation (is_enable=false)
1. Désactiver un équipement dans Jeedom UI
2. Rescan
3. Vérifier dans HA : entité supprimée (PAS juste "unavailable")
4. Vérifier le diagnostic : montre "Désactivé dans Jeedom"
5. Réactiver l'équipement → rescan → entité republiée dans HA

TEST 4 — Distinction indisponible vs désactivé
1. Identifier un équipement dont le module physique peut être déconnecté
2. Déconnecter le module → vérifier : entité HA passe "unavailable" MAIS reste présente
3. Désactiver le même équipement (is_enable=false) → rescan → entité disparaît de HA
4. Preuve : le comportement discovery est différent entre indisponible et désactivé
```

---

## Annexe — Diagramme de flux simplifié (boot daemon)

```
[Daemon start]
     │
     ▼
[Charger cache disque]
     │
     ▼
[Connecter broker MQTT] ──(échec)──► [Retry avec backoff]
     │ (succès)                              │
     ▼                                       │
[Publier birth: bridge=online]               │
     │                                       │
     ▼                                       │
[Souscrire homeassistant/status]             │
[Souscrire jeedom2ha/+/set]                  │
[Souscrire jeedom2ha/+/brightness/set]       │
[Souscrire jeedom2ha/+/position/set]         │
     │                                       │
     ▼                                       │
[Interroger Jeedom: getFullTopology] ──(échec)──► [Retry backoff (Décision 7), aucune publication]
     │ (succès)
     ▼
[Réconcilier cache vs topologie]
     │
     ├─ Nouveaux eq_ids ──► Publish discovery
     ├─ Supprimés eq_ids ──► Unpublish discovery
     ├─ Modifiés eq_ids ──► Republish discovery (+ unpublish ancien topic si retypage)
     ├─ Désactivés eq_ids ──► Unpublish discovery (INV-11)
     └─ Inchangés eq_ids ──► Republish discovery (refresh retained)
     │
     ▼
[Publier états courants (lissé — Décision 8)]
     │
     ▼
[Publier availability locale]
     │
     ▼
[Mode nominal: event::changes + écoute commandes]


--- Événements en mode nominal ---

[homeassistant/status = online] ──► [Republish discovery depuis cache RAM (Décision 6)]
[MQTT reconnect]                ──► [Republish discovery depuis cache RAM (Décision 6)]
[Rescan utilisateur]            ──► [getFullTopology + réconciliation complète]
```
