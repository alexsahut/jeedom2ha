# Story 4.2: Diagnostic Détaillé et Suggestions de Remédiation

Status: review

## Story

As a utilisateur Jeedom,
I want accéder au détail technique d'un équipement problématique et savoir comment le corriger,
so that je puisse rendre ma maison HA plus complète en autonomie.

## Contexte

Story 4.1 a livré la liste de couverture avec statuts (Publié / Partiellement publié / Non publié / Exclu) et niveaux de confiance. Le backend `/system/diagnostics` retourne déjà `reason_code` par équipement. Les badges et le tableau filtrable existent dans `desktop/js/jeedom2ha.js`.

**Ce que Story 4.2 ajoute** :
- Le backend enrichit le payload avec `detail` (cause lisible) et `remediation` (action concrète), ainsi que `unmatched_commands` pour le cas "Partiellement publié".
- Le frontend ajoute le pattern accordéon sur chaque ligne de la modale de diagnostic, révélant cause + remédiation + commandes non couvertes.

**Ce que Story 4.2 ne fait PAS** :
- Elle ne touche pas à l'UI des exclusions (Story 4.3).
- Elle n'exporte rien (Story 4.4).
- Elle ne refactorise pas la logique de mapping.
- Elle n'ajoute aucune nouvelle dépendance Python ou framework JS.

## Acceptance Criteria

**AC1 — Accordéon à la demande**
**Given** la modale de diagnostic est ouverte et affiche un équipement "Non publié" ou "Partiellement publié"
**When** l'utilisateur clique sur la ligne (ou un chevron/bouton dédié)
**Then** un panneau de détail se déploie sous la ligne sans recharger la modale

**AC2 — Remédiation actionnable et non intimidante**
**Given** l'accordéon est ouvert
**Then** il affiche :
- La **cause** de non-publication en langage métier (pas de code technique brut)
- La **remédiation** spécifique à la cause détectée (ex : "Configurez le type générique sur la commande 'Etat'")
- Pour "Partiellement publié" : la liste des commandes non couvertes **avec leur `generic_type`** (commandes ayant un `generic_type` reconnu mais non couvert par le mapping V1)

**AC3 — Distinction des 4 familles de cause**
**Given** un équipement est non publié ou partiellement publié
**Then** le système distingue sans ambiguïté :
1. **Action requise côté Jeedom** (`reason_code` : `no_commands`, `ambiguous_skipped`, ou generic_type absent/mal configuré) — l'utilisateur peut corriger dans Jeedom
2. **Hors périmètre V1** (`reason_code` : `no_mapping` ou `no_supported_generic_type`) — le type d'équipement n'est pas encore supporté, aucune action Jeedom possible
3. **Exclusion volontaire** (`reason_code` : `excluded_eqlogic`) — état neutre, l'utilisateur a explicitement exclu cet équipement
4. **Panne infra** (`reason_code` : `discovery_publish_failed`, `local_availability_publish_failed`) — problème de broker MQTT, signalé en rouge

**Doctrine des causes (invariante, ne pas dériver)** :
- `no_mapping` = aucun mapper V1 ne reconnaît ce type d'équipement → **hors périmètre V1**
- `no_supported_generic_type` = des commandes ont un `generic_type` configuré, mais ce type n'est pas dans le périmètre V1 → **hors périmètre V1**
- `no_commands` = l'équipement n'a aucune commande → **action requise** (vérifier la configuration Jeedom)
- absence de `generic_type` sur les commandes (commandes existantes sans type générique) → **action requise** (configurer les types génériques dans Jeedom)
- `ambiguous_skipped` = plusieurs types HA possibles, ambiguïté non résoluble → **action requise** (préciser les types génériques)
- `excluded_eqlogic` = exclusion manuelle → **neutre** (ni panne ni action requise)
- `discovery_publish_failed`, `local_availability_publish_failed` = échec MQTT → **panne infra**

**AC4 — Wording conforme à l'UX spec**
**Then** :
- Aucun wording ne contient de terme technique MQTT, Python ou JSON brut
- Le rouge est absent des causes de configuration (réservé aux pannes infra)
- Une erreur de configuration est présentée comme une "action requise", pas comme une panne
- Le texte est concis, professionnel, rassurant

**AC5 — Lien Jeedom direct**
**Given** la cause est de type "action requise côté Jeedom" (`no_commands`, `ambiguous_skipped`, generic_type absent/mal configuré, ou "Partiellement publié")
**Then** un lien "Configurer dans Jeedom" ouvre la page de configuration de l'équipement à l'URL canonique : `index.php?v=d&m=jeedom2ha&id={eq_id}`

**AC6 — Indicateur V1**
**Given** la cause est `no_mapping` ou `no_supported_generic_type`
**Then** un indicateur visible "Hors périmètre V1" est présent, avec un message rassurant ("Ce type d'équipement n'est pas encore supporté dans cette version du plugin. Il le sera peut-être dans une version future.")

**AC7 — Cohérence ligne / accordéon**
**Then** le statut affiché sur la ligne correspond au détail de l'accordéon (pas de contradiction entre badge et texte)

**AC8 — Tests unitaires verts**
**Then** `pytest` passe sur `test_diagnostic_endpoint.py` incluant les nouveaux cas (payload enrichi, unmatched_commands, reason_code → detail/remediation)

## Tasks / Subtasks

### Task 0 — Pre-flight Git (OBLIGATOIRE, non négociable)
- [x] 0.1 S'assurer que le clone principal local est sur `main`, propre et aligné sur `origin/main`
  ```bash
  git checkout main && git pull origin main
  git status  # doit être clean
  ```
- [x] 0.2 Créer la branche dédiée et le worktree depuis `main` via le script canonique :
  ```bash
  scripts/start-story-worktree.sh story/4.2-diagnostic-detail-remediation
  ```
- [x] 0.3 Depuis le worktree dédié, exécuter le préflight bloquant :
  ```bash
  scripts/git-preflight.sh --expect-branch story/4.2-diagnostic-detail-remediation
  ```
  **S'arrêter immédiatement si le préflight échoue.**
- [x] 0.4 Relire `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md` (variables d'authentification, box de test, protocole rsync)

> **Rappel gouvernance (non négociable)** :
> - Ne jamais développer dans le clone principal local
> - Ne jamais committer directement sur `main`, `beta` ou `stable`
> - PR de développement uniquement vers `main`
> - Conventional Commits obligatoires (ex: `feat(diagnostic): add detail and remediation to coverage endpoint`)
> - Squash merge canonique vers `main`

---

### Task 1 — Backend : Enrichir `/system/diagnostics` (AC: #2, #3, #6, #7)

- [x] 1.1 Dans `resources/daemon/transport/http_server.py`, enrichir la fonction `_handle_system_diagnostics` pour ajouter par équipement :
  - `detail` : cause lisible en français (voir table de mapping ci-dessous)
  - `remediation` : action concrète en français (voir table ci-dessous)
  - `v1_limitation` : `true` si `reason_code` in (`no_mapping`, `no_supported_generic_type`)
  - `unmatched_commands` : liste des commandes non couvertes pour "Partiellement publié" (voir spec structure ci-dessous)

- [x] 1.2 Implémenter la table de mapping `reason_code → {detail, remediation}` dans `_handle_system_diagnostics` :

  | `reason_code` | `detail` | `remediation` |
  |---|---|---|
  | `no_commands` | "Cet équipement n'a aucune commande configurée dans Jeedom." | "Vérifiez que l'équipement possède des commandes actives dans Jeedom." |
  | `no_supported_generic_type` | "Les commandes de cet équipement ont un type générique configuré, mais ce type n'est pas dans le périmètre supporté par la V1 du plugin." | "Ce type d'équipement n'est pas encore supporté dans cette version. Aucune action Jeedom ne permettra de le publier en V1." |
  | `disabled` / `disabled_eqlogic` | "Cet équipement est désactivé dans Jeedom." | "Activez l'équipement dans sa page de configuration Jeedom pour qu'il devienne éligible." |
  | `excluded_eqlogic` | "Cet équipement est exclu manuellement de la publication vers Home Assistant." | "Pour le publier, retirez-le de la liste d'exclusions dans la configuration du plugin." |
  | `ambiguous_skipped` | "Plusieurs types d'entités Home Assistant sont possibles pour cet équipement. Le plugin ne publie pas en cas d'ambiguïté." | "Précisez les types génériques sur les commandes pour lever l'ambiguïté et permettre une publication fiable." |
  | `no_mapping` | "Aucun type d'équipement Home Assistant ne correspond à cet équipement dans la V1 du plugin." | "Ce type d'équipement n'est pas encore supporté. Consultez la documentation du plugin pour connaître le périmètre V1 supporté." |
  | `discovery_publish_failed` | "La publication MQTT de cet équipement a échoué lors du dernier sync." | "Vérifiez la connexion au broker MQTT et relancez un diagnostic après résolution." |
  | `local_availability_publish_failed` | "La publication de la disponibilité locale de cet équipement a échoué." | "Vérifiez la connexion au broker MQTT et relancez un sync." |
  | `sure_mapping` (si Partiellement publié) | "Cet équipement est publié mais certaines commandes ne sont pas couvertes par le mapping V1." | "Configurez les types génériques manquants sur les commandes listées ci-dessous pour une couverture complète." |
  | `eligible` (fallback) | "Cet équipement est éligible mais n'a pas été publié lors du dernier sync." | "Relancez un sync complet depuis l'interface du plugin." |
  | Default / inconnu | "Cause inconnue." | "Relancez un sync. Si le problème persiste, consultez les logs du démon." |

- [x] 1.3 Pour les équipements "Partiellement publié", renseigner `unmatched_commands` :
  ```json
  "unmatched_commands": [
    {
      "cmd_id": 3002,
      "cmd_name": "Couleur",
      "generic_type": "LIGHT_COLOR"
    }
  ]
  ```
  Structure : liste de dicts `{cmd_id, cmd_name, generic_type}` pour chaque commande qui a un `generic_type` mais n'est pas dans `map_result.commands.values()`. Liste vide `[]` si aucune commande non couverte.

- [x] 1.4 Vérifier que les champs `detail`, `remediation`, `v1_limitation`, `unmatched_commands` sont présents pour **tous** les équipements (pas uniquement les non publiés), avec des valeurs appropriées pour les équipements "Publié" (`detail=""`, `remediation=""`, `v1_limitation=false`, `unmatched_commands=[]`).

**Contrat de payload enrichi (exemple) :**
```json
{
  "action": "system.diagnostics",
  "status": "ok",
  "payload": {
    "equipments": [
      {
        "eq_id": 100,
        "object_name": "Salon",
        "name": "Lumière Salon",
        "status": "Publié",
        "confidence": "Sûr",
        "reason_code": "sure_mapping",
        "detail": "",
        "remediation": "",
        "v1_limitation": false,
        "unmatched_commands": []
      },
      {
        "eq_id": 200,
        "object_name": "Cuisine",
        "name": "Thermostat",
        "status": "Non publié",
        "confidence": "Ignoré",
        "reason_code": "no_mapping",
        "detail": "Aucun type d'équipement Home Assistant ne correspond à cet équipement dans la V1 du plugin.",
        "remediation": "Ce type d'équipement n'est pas encore supporté. Consultez la documentation du plugin pour connaître le périmètre V1 supporté.",
        "v1_limitation": true,
        "unmatched_commands": []
      },
      {
        "eq_id": 300,
        "object_name": "Salon",
        "name": "Lumière Partielle",
        "status": "Partiellement publié",
        "confidence": "Sûr",
        "reason_code": "sure_mapping",
        "detail": "Cet équipement est publié mais certaines commandes ne sont pas couvertes par le mapping V1.",
        "remediation": "Configurez les types génériques manquants sur les commandes listées ci-dessous pour une couverture complète.",
        "v1_limitation": false,
        "unmatched_commands": [
          {"cmd_id": 3002, "cmd_name": "Couleur", "generic_type": "LIGHT_COLOR"}
        ]
      }
    ]
  }
}
```

---

### Task 2 — Frontend : Accordéon de détail (AC: #1, #2, #3, #4, #5, #6, #7)

- [x] 2.1 Dans `desktop/js/jeedom2ha.js`, modifier la fonction `renderTable` (dans le handler `getDiagnostics`) pour :
  - Ajouter un chevron/bouton "Détail" sur chaque ligne dont `status` != "Publié"
  - Stocker les données enrichies (`detail`, `remediation`, `v1_limitation`, `unmatched_commands`) sur la ligne via `data-*` ou dans un objet JS indexé par `eq_id`

- [x] 2.2 Implémenter le comportement d'accordéon :
  - Clic sur la ligne ou le chevron → toggle d'une ligne de détail `<tr class="diagnostic-detail-row">` insérée juste en dessous
  - **Un seul accordéon ouvert à la fois** : fermer le précédent ouvert avant d'en ouvrir un nouveau
  - L'accordéon se referme au second clic sur la même ligne

- [x] 2.3 Contenu du panneau de détail (`diagnostic-detail-row`) :

  ```html
  <tr class="diagnostic-detail-row">
    <td colspan="5" style="background:#f9f9f9; padding:12px 20px;">
      <!-- Cause -->
      <div class="detail-cause">
        <strong>Cause :</strong>
        <span>{detail}</span>
      </div>
      <!-- Remédiation -->
      <div class="detail-remediation" style="margin-top:6px;">
        <strong>Action :</strong>
        <span>{remediation}</span>
      </div>
      <!-- Indicateur V1 si applicable -->
      <!-- SI v1_limitation === true -->
      <div class="detail-v1" style="margin-top:6px;">
        <span class="label label-default">Hors périmètre V1</span>
        <small style="margin-left:6px;color:#888;">Ce type d'équipement n'est pas encore supporté dans cette version.</small>
      </div>
      <!-- Commandes non couvertes si présentes -->
      <!-- SI unmatched_commands.length > 0 -->
      <div class="detail-unmatched" style="margin-top:8px;">
        <strong>Commandes non couvertes :</strong>
        <ul style="margin:4px 0 0 16px;">
          <!-- Pour chaque unmatched_commands[i] -->
          <li><code>{cmd_name}</code> — type générique : <code>{generic_type}</code></li>
        </ul>
      </div>
      <!-- Lien Jeedom : affiché uniquement pour les causes "action requise" (no_commands, ambiguous_skipped, generic_type absent, partiellement publié) -->
      <!-- PAS affiché pour no_mapping, no_supported_generic_type (hors périmètre V1 — aucune action possible) -->
      <!-- PAS affiché pour excluded_eqlogic (neutre) -->
      <!-- SI reason_code in [no_commands, ambiguous_skipped] OU status == "Partiellement publié" -->
      <div style="margin-top:8px;">
        <a href="index.php?v=d&m=jeedom2ha&id={eq_id}" target="_blank" class="btn btn-xs btn-default">
          <i class="fas fa-external-link-alt"></i> Configurer dans Jeedom
        </a>
      </div>
    </td>
  </tr>
  ```

- [x] 2.4 Règles de couleur du panneau de détail (conforme UX spec, alignées sur la doctrine des causes) :
  - `no_mapping`, `no_supported_generic_type` → fond gris neutre (`#f5f5f5`), label `label-default` "Hors périmètre V1" — **jamais de rouge ni de jaune**
  - `excluded_eqlogic` → fond gris neutre (`#f5f5f5`), label `label-default` "Exclu" — **neutre**
  - `no_commands`, `ambiguous_skipped`, generic_type absent/mal configuré, `disabled_eqlogic`, `disabled` → fond jaune léger (`#fffbee`), label `label-warning` "Action requise"
  - Partiellement publié (`sure_mapping` + commandes non couvertes) → fond jaune léger (`#fffbee`), label `label-warning` "Action requise"
  - `discovery_publish_failed`, `local_availability_publish_failed` → fond rouge léger (`#fdf2f2`), label `label-danger` "Erreur infra" — **rouge réservé exclusivement aux pannes broker/infra**

- [x] 2.5 Ajouter un curseur pointer sur les lignes dépliables (CSS inline ou classe) pour signaler l'interactivité

---

### Task 3 — Tests unitaires (AC: #8)

- [x] 3.1 Dans `resources/daemon/tests/unit/test_diagnostic_endpoint.py`, ajouter les tests :
  - `test_diagnostics_detail_and_remediation_no_commands` : vérifier que `detail`, `remediation` sont non vides et `v1_limitation=False` pour `reason_code=no_commands`
  - `test_diagnostics_detail_and_remediation_no_mapping` : vérifier `v1_limitation=True` pour `reason_code=no_mapping`
  - `test_diagnostics_detail_and_remediation_ambiguous` : vérifier que le `detail` mentionne l'ambiguïté
  - `test_diagnostics_detail_and_remediation_excluded` : vérifier que `detail` mentionne l'exclusion manuelle
  - `test_diagnostics_unmatched_commands_present` : pour un équipement "Partiellement publié" avec des commandes non couvertes, vérifier que `unmatched_commands` contient les bonnes entrées (`cmd_id`, `cmd_name`, `generic_type`)
  - `test_diagnostics_published_fields_empty` : pour un équipement "Publié", vérifier `detail=""`, `remediation=""`, `v1_limitation=False`, `unmatched_commands=[]`

- [x] 3.2 Vérifier que tous les tests existants continuent de passer (non-régression)

---

### Task 4 — Validation Terrain Opérateur (Quality Gate)

- [ ] 4.1 Déployer sur la box de test via rsync — **EN ATTENTE : box inaccessible au moment du dev** (voir procédure dans `jeedom2ha-test-context-jeedom-reel.md`)
- [ ] 4.2 Exécuter les smoke tests terrain — **EN ATTENTE : box inaccessible** (section Tests Minimum ci-dessous)
- [ ] 4.3 Fournir les preuves de passage au SM avant clôture — **EN ATTENTE : validation terrain**

---

## Dev Notes

### Composants à modifier

| Fichier | Nature de la modification |
|---|---|
| `resources/daemon/transport/http_server.py` | Enrichir `_handle_system_diagnostics` : `detail`, `remediation`, `v1_limitation`, `unmatched_commands` |
| `desktop/js/jeedom2ha.js` | Ajouter accordéon dans la fonction `renderTable` et dans le handler de clic |
| `resources/daemon/tests/unit/test_diagnostic_endpoint.py` | Nouveaux cas de test pour le payload enrichi |

**Aucune modification de** :
- `core/ajax/jeedom2ha.ajax.php` (action `getDiagnostics` déjà câblée)
- `desktop/php/jeedom2ha.php` (bouton déjà existant)
- `core/class/jeedom2ha.class.php`
- Tout autre mapper Python

### Architecture : Données disponibles dans `_handle_system_diagnostics`

Le handler a accès à :
- `request.app["topology"]` → `TopologySnapshot` (tous les équipements, leurs commandes avec `generic_type`)
- `request.app["eligibility"]` → `Dict[int, EligibilityResult]` (is_eligible, reason_code)
- `request.app["mappings"]` → `Dict[int, MappingResult]` (ha_entity_type, confidence, reason_code, **commands** = Dict des commandes mappées)
- `request.app["publications"]` → `Dict[int, PublicationDecision]` (should_publish, active_or_alive, reason)

Pour calculer `unmatched_commands` :
```python
# Commandes avec generic_type dans la topologie pour cet équipement
coverable_cmds = [c for c in eq.cmds if c.generic_type]
# IDs des commandes mappées (présentes dans map_result.commands)
mapped_cmd_ids = {c.id for c in map_result.commands.values()}
# Non couvertes = coverable mais absent du mapping
unmatched = [c for c in coverable_cmds if c.id not in mapped_cmd_ids]
unmatched_commands = [
    {"cmd_id": c.id, "cmd_name": c.name, "generic_type": c.generic_type}
    for c in unmatched
]
```

### Stack Frontend

- **jQuery** uniquement — pas de framework JS externe
- **Bootstrap 3** — classes `label-*`, `btn-xs`, `panel`, `table-*`
- Pattern accordéon : `$(row).next('.diagnostic-detail-row').toggle()` ou équivalent jQuery simple
- **Pas de `fetch()`** — utiliser `$.ajax()` (déjà en place)
- Pas de CSS externe ajouté — styles inline ou classes Bootstrap existantes suffisent

### Doctrine des causes — référence invariante pour l'implémentation

| `reason_code` | Famille | Traitement UX | Lien Jeedom |
|---|---|---|---|
| `no_mapping` | Hors périmètre V1 | Fond gris, label-default "Hors périmètre V1" | **Non** |
| `no_supported_generic_type` | Hors périmètre V1 | Fond gris, label-default "Hors périmètre V1" | **Non** |
| `no_commands` | Action requise | Fond jaune, label-warning "Action requise" | **Oui** |
| `ambiguous_skipped` | Action requise | Fond jaune, label-warning "Action requise" | **Oui** |
| `disabled`, `disabled_eqlogic` | Action requise | Fond jaune, label-warning "Action requise" | **Oui** |
| Partiellement publié (commandes non couvertes) | Action requise | Fond jaune, label-warning "Action requise" | **Oui** |
| `excluded_eqlogic` | Neutre | Fond gris, label-default "Exclu" | **Non** |
| `discovery_publish_failed` | Panne infra | Fond rouge, label-danger "Erreur infra" | **Non** |
| `local_availability_publish_failed` | Panne infra | Fond rouge, label-danger "Erreur infra" | **Non** |

**Distinction critique `no_supported_generic_type` vs absence de `generic_type`** :
- `no_supported_generic_type` : les commandes ont un `generic_type` configuré, mais ce type n'est PAS dans le périmètre V1 → hors périmètre V1, l'utilisateur ne peut rien faire dans Jeedom
- Absence de `generic_type` sur les commandes : les commandes existent mais n'ont pas de type générique → action requise. En pratique, ce cas est souvent couvert par `no_supported_generic_type` dans l'eligibility engine car aucun generic_type valide n'est trouvé. Si le backend expose ce sous-cas avec son propre `reason_code`, appliquer le traitement "action requise". Si non, traiter `no_supported_generic_type` en priorité comme "hors périmètre V1" (generic_type configuré mais non supporté).

### Faux positifs generic_type — leçon rétro Epic 2/3

Le `generic_type` Jeedom est renseigné par l'utilisateur ou le plugin source. Il peut contenir des valeurs non reconnues par le projet (ex: `ENERGY_STATE` pour un plugin exotique). Le backend doit traiter le cas où `generic_type` existe mais n'est pas reconnu par les mappers V1 (`no_supported_generic_type`) sans jamais inventer de mapping.

La remédiation pour ce cas doit rester informative et non culpabilisante : "Ce type générique n'est pas encore supporté dans la V1 du plugin" (pas "Votre configuration est incorrecte").

### Contrat interface PHP → daemon

Aucun changement de contrat. L'action AJAX `getDiagnostics` retourne déjà la réponse du daemon via `jeedom2ha::callDaemon('/system/diagnostics', null, 'GET', 15)`. Les champs enrichis seront automatiquement transmis au JS.

### Cycle de vie des données de diagnostic

Les données viennent de la RAM du démon et sont **volatiles** : elles sont perdues au redémarrage du démon jusqu'au prochain `/action/sync`. L'accordéon doit fonctionner sur les données de la dernière réponse AJAX (les stocker dans le JS au moment du rendu), pas en refaisant un appel AJAX par ligne dépliée.

## Guardrails

### Git (NON NÉGOCIABLE)
- Développement sur `story/4.2-diagnostic-detail-remediation` uniquement, jamais dans le clone principal local
- Aucun commit sur `main`, `beta` ou `stable`
- PR uniquement vers `main`, Conventional Commits, squash merge canonique
- Hooks `.githooks/pre-commit` et `.githooks/pre-push` activés : `git config core.hooksPath .githooks`

### Architecture
- **Zéro nouvelle dépendance Python** — utiliser uniquement la stack déjà en place (`aiohttp`, `asyncio`)
- **Zéro framework JS** — jQuery + Bootstrap 3 natif Jeedom uniquement
- **Pas de tables DB custom** — les données restent en RAM démon uniquement
- **Pas de refacto du mapping engine** — enrichir uniquement le handler `/system/diagnostics`
- **Périmètre V1 strict** : ne pas ajouter de logique de mapping pour de nouveaux types d'équipements

### UX
- Rouge réservé exclusivement aux pannes d'infrastructure (broker, démon)
- Wording métier uniquement — aucun terme MQTT, Python, JSON, payload dans l'UI utilisateur
- Accordéon = détail à la demande, la vue tableau principale reste lisible

### Tests
- `pytest` doit passer complètement avant ouverture de PR
- `scripts/ci-local.sh` pour simuler la CI localement
- Les tests existants de `test_diagnostic_endpoint.py` ne doivent pas régresser

## Previous Story Intelligence

### Leçons de Story 4.1

- **Pollution AJAX** : la réponse AJAX doit rester un JSON pur, commençant par `{`. Aucun espace, warning PHP ou balise HTML avant le JSON. Valider avec l'onglet Network du navigateur (preuve terrain critique).
- **RAM vide** : le démon fraîchement redémarré n'a pas de topologie en mémoire. La réponse `{"status": "error", "message": "Diagnostic indisponible..."}` est déjà gérée — le JS doit continuer de gérer ce cas proprement (déjà implémenté en 4.1, ne pas le casser).
- **jeedom2ha::callDaemon** côté PHP gère déjà le timeout et les erreurs réseau — ne pas réinventer de couche HTTP.
- **Données volatiles** : après restart démon, `app["topology"] = None`. Toujours vérifier que le JS gère le cas `equipments.length === 0` (déjà en place).

### Leçons des Épics 2 et 3

- **Faux positifs `generic_type`** : certains plugins Jeedom renseignent des `generic_type` non reconnus par les mappers V1. La cause `no_supported_generic_type` est distincte de `no_commands` (le type est configuré mais pas supporté). La remédiation doit le préciser.
- **Tests unitaires seuls insuffisants** : la validation terrain sur box réelle est obligatoire. Les tests unitaires mockés ne remplacent pas la validation AJAX/UI sur box.
- **Bootstrap 3 uniquement** : ne jamais introduire de classes CSS Bootstrap 4/5 ni de framework externe. Utiliser exclusivement `label-success`, `label-warning`, `label-danger`, `label-default`, `btn-xs`, `btn-default`.
- **Lecture de `jeedom2ha-test-context-jeedom-reel.md`** avant tout test terrain : variables d'environnement, procédure rsync, protocole de vérification démon.

## Tests Minimum (réels + traçabilité homogène)

> **Règle absolue** : tous les tests terrain utilisent les **variables shell documentées** dans `jeedom2ha-test-context-jeedom-reel.md`. Aucun secret (`X-Local-Secret`, `apikey`) n'est saisi en dur dans les commandes. Le chemin canonique sur la box est `/var/www/html`.

### 0. Variables et pré-requis

Depuis la box Jeedom de test (en SSH) :

```sh
export JEEDOM_ROOT=/var/www/html
export DAEMON_API=http://127.0.0.1:55080
export EQ_ID_TEST=391  # Adapter si nécessaire

export LOCAL_SECRET="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; echo config::byKey("localSecret", "jeedom2ha");')"
```

### 1. Déploiement sur la box de test

Sur la machine locale (Mac) :
```sh
export REPO="/Users/alexandre/Dev/jeedom/plugins/jeedom2ha"
export DEST="asahut@192.168.1.21:/home/asahut/jeedom2ha/"
rsync -az --delete --delete-after --prune-empty-dirs \
  --filter="merge ${REPO}/.rsync-plugin-deploy.filter" \
  "${REPO}/" "${DEST}"
```

Sur la box (root) :
```sh
rsync -a --delete --exclude 'data/' \
  /home/asahut/jeedom2ha/ /var/www/html/plugins/jeedom2ha/ && \
chown -R www-data:www-data /var/www/html/plugins/jeedom2ha && \
find /var/www/html/plugins/jeedom2ha -type d -exec chmod 755 {} \; && \
find /var/www/html/plugins/jeedom2ha -type f -exec chmod 644 {} \; && \
chmod +x /var/www/html/plugins/jeedom2ha/resources/daemon/main.py
```

### 2. Pre-flight démon et sync

```sh
# Redémarrer le démon
curl -sS -H "X-Local-Secret: $LOCAL_SECRET" "$DAEMON_API/system/status" | jq

# Déclencher un sync pour hydrater la RAM
php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php"; echo json_encode(array("payload" => jeedom2ha::getFullTopology()), JSON_UNESCAPED_SLASHES);' > /tmp/jeedom2ha-topology.json
curl -sS -X POST -H "X-Local-Secret: $LOCAL_SECRET" -H 'Content-Type: application/json' \
  "$DAEMON_API/action/sync" --data-binary @/tmp/jeedom2ha-topology.json | jq
```

### 3. Vérifier le payload enrichi du backend

```sh
curl -sS -H "X-Local-Secret: $LOCAL_SECRET" "$DAEMON_API/system/diagnostics" | jq '.payload.equipments[0]'
```

**Préconditions** : démon actif, `/action/sync` exécuté
**Action** : requête directe à l'endpoint
**Observation** : chaque équipement doit contenir `detail`, `remediation`, `v1_limitation`, `unmatched_commands`
**Verdict attendu** : PASS si les 4 champs sont présents sur chaque entrée, avec `detail` non vide pour les équipements non publiés

### 4. Test 4.2-A : Accordéon sur équipement "Non publié" — typage Jeedom

**Préconditions** : au moins un équipement "Non publié" avec `reason_code=no_supported_generic_type` ou `no_commands` dans le diagnostic

**Action** : Dans Jeedom (F12 ouvert sur onglet Network) → ouvrir la modale de diagnostic → cliquer sur une ligne "Non publié"

**Observation UI** :
- Un panneau de détail apparaît sous la ligne sans recharger la modale
- Le texte "Cause" est lisible, non technique (ex: "Aucun type générique reconnu sur les commandes")
- Le texte "Action" est actionnable (ex: "Configurez le type générique...")
- Le wording ne contient aucun terme technique MQTT/Python/JSON
- Le badge de statut du panneau est jaune (label-warning) ou gris, jamais rouge

**Observation logs** :
```sh
grep "\[DIAG\]" /var/www/html/log/jeedom2ha_daemon | tail -n 20
```
(Aucune erreur attendue)

**Verdict** : PASS / FAIL

---

### 5. Test 4.2-B : Accordéon sur équipement "Non publié" — hors périmètre V1

**Préconditions** : au moins un équipement avec `reason_code=no_mapping` dans le diagnostic

**Action** : cliquer sur la ligne correspondante dans la modale

**Observation UI** :
- L'indicateur "Hors périmètre V1" est visible (`label-default`)
- Le message est rassurant, non culpabilisant
- Aucun rouge dans le panneau

**Verdict** : PASS / FAIL

---

### 6. Test 4.2-C : Accordéon sur équipement "Partiellement publié"

**Préconditions** : au moins un équipement "Partiellement publié" dans le diagnostic (équipement mappé mais avec des commandes non couvertes)

**Action** : cliquer sur la ligne correspondante

**Observation UI** :
- La section "Commandes non couvertes" est présente
- Chaque commande non couverte est listée avec son nom et son `generic_type`
- Le lien "Configurer dans Jeedom" est présent et pointe vers la page de configuration de l'équipement

**Verdict** : PASS / FAIL

---

### 7. Test 4.2-D : Accordéon sur équipement "Exclu"

**Préconditions** : au moins un équipement avec `reason_code=excluded_eqlogic`

**Action** : cliquer sur la ligne

**Observation UI** :
- Le texte explique clairement que l'équipement est exclu manuellement (pas une panne)
- Aucun rouge
- Fond gris neutre

**Verdict** : PASS / FAIL

---

### 8. Test 4.2-E : Anti-pollution AJAX

**Préconditions** : F12 ouvert, onglet Network

**Action** : cliquer sur "Diagnostic de Couverture", observer la réponse AJAX

**Observation** : la réponse brute commence par `{`, aucun espace, aucun warning PHP, aucune balise HTML

**Verdict** : PASS / FAIL (critique — même exigence que Story 4.1)

---

### 9. Test 4.2-F : Cohérence ligne / accordéon

**Action** : Pour 3 équipements de statuts différents (Publié, Non publié, Partiellement publié), ouvrir l'accordéon et vérifier la cohérence

**Observation** : le statut dans le badge de la ligne correspond à ce qui est expliqué dans le panneau de détail

**Verdict** : PASS / FAIL

---

### Preuves obligatoires avant clôture

- Capture du Network tab (propreté AJAX — test 4.2-E)
- Capture du panneau de détail pour chaque famille de cause (tests 4.2-A, B, C, D)
- Résultat `pytest` vert (tests unitaires)
- Bilan PASS/FAIL soumis à l'agent SM

## Références

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Strategy — Actionable Accordion Row]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Error Semantics]
- [Source: _bmad-output/planning-artifacts/architecture.md#3. File, Module & Log Structure]
- [Source: resources/daemon/transport/http_server.py#_handle_system_diagnostics]
- [Source: desktop/js/jeedom2ha.js#renderTable]
- [Source: _bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md#Déploiement Local vers Box de Test]
- [Source: _bmad-output/implementation-artifacts/4-1-interface-de-diagnostic-de-couverture.md]
- [Source: docs/git-strategy.md]
- [Source: docs/local-git-guardrails.md]
- [Source: docs/agent-start-checklist.md]

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6 (create-story workflow, 2026-03-17)
claude-opus-4-6 (dev-story implementation, 2026-03-17)

### Debug Log References

### Completion Notes List

**Correctifs post-validation-terrain (2026-03-17) :**

- **Lien "Configurer dans Jeedom" corrigé** : le backend expose désormais `eq_type_name` (plugin source : zwave, philipshue, virtual…) ; le frontend construit l'URL `index.php?v=d&m={eq_type_name}&id={eq_id}` au lieu de `m=jeedom2ha` (cassé en terrain). Fallback sur `jeedom2ha` si le champ est absent.
- **Actionnabilité `no_supported_generic_type` et `ambiguous_skipped`** : le backend collecte les `generic_type` des commandes et les expose dans `detected_generic_types[]` pour ces deux cas. Le frontend les affiche en ligne dans le panneau de détail sous "Types génériques détectés".
- **Badge "Exclu" corrigé** : `label-danger` (rouge) → `label-default` (gris) — conforme à la doctrine "Exclu = neutre".
- **Fond jaune/gris/rouge stabilisé** : ajout de `!important` sur `background` du TR et TD du panneau de détail pour résister aux overrides CSS Jeedom/Bootstrap au hover.
- **Couleur neutre sur commandes non couvertes** : `color:#333` sur les `<li>` de `unmatched_commands` — aucun rouge parasite.
- **Tests** : 4 nouveaux tests ajoutés (31/31 passent), lint flake8 propre.
- **Gap terrain** : box Jeedom (192.168.1.21) toujours inaccessible — Task 4 (déploiement rsync + smoke tests UI) reste à exécuter.

**Correctif post-code-review rowspan (2026-03-17) :**

- **Bug corrigé** (`desktop/js/jeedom2ha.js`) : suppression du `rowspan` sur la colonne "Objet/Pièce" dans `renderTable`. La cellule avec `rowspan="N"` ne tenait pas compte des `diag-detail-row` intercalées, ce qui cassait l'alignement du tableau dès qu'un accordéon était ouvert dans un groupe multi-équipements. Le nom de l'objet/pièce est maintenant répété sur chaque ligne d'équipement — solution la plus simple et la plus robuste.
- **Tests** : 274/274 passent (aucune régression), dont 12/12 pour `test_diagnostic_endpoint.py`.
- **Aucune modification backend** — correctif purement frontend, une seule ligne supprimée.

**Implémentation complète (2026-03-17) :**

- **Backend** (`http_server.py`) : `_DIAGNOSTIC_MESSAGES` dict + helper `_get_diagnostic_enrichment()` + enrichissement du handler `_handle_system_diagnostics` avec `detail`, `remediation`, `v1_limitation`, `unmatched_commands` selon la doctrine des causes (v1_limitation=True pour no_mapping/no_supported_generic_type, fields vides pour "Publié").
- **Frontend** (`jeedom2ha.js`) : accordéon jQuery sur lignes non-publiées — un seul ouvert à la fois, chevron animé, couleurs conformes (gris=V1/exclu, jaune=action requise, rouge=panne infra), lien "Configurer dans Jeedom" uniquement pour les cas actionnables, re-bind après filtre de recherche.
- **Tests** (`test_diagnostic_endpoint.py`) : 7 nouveaux tests (no_commands, no_mapping, no_supported_generic_type, ambiguous, excluded, unmatched_commands, published_empty) — 27/27 passent, lint flake8 propre.
- **Gap terrain** : box Jeedom inaccessible (192.168.1.21 hors réseau) — Task 4 (déploiement rsync + smoke tests UI) reste à exécuter. La logique backend est couverte par tests unitaires.

### File List
- `_bmad-output/implementation-artifacts/4-2-diagnostic-detaille-et-suggestions-de-remediation.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py`
- `desktop/js/jeedom2ha.js`

## Change Log

| Date | Description |
|------|-------------|
| 2026-03-17 | Implémentation complète : backend enrichi (detail/remediation/v1_limitation/unmatched_commands), accordéon frontend, 7 nouveaux tests unitaires |
| 2026-03-17 | Correctifs post-validation-terrain : lien Jeedom corrigé (eq_type_name), detected_generic_types exposés, badge Exclu grisé, background !important, 4 tests ajoutés (31/31) |
| 2026-03-17 | Correctif post-code-review : suppression du `rowspan` sur la colonne Objet/Pièce — répétition du nom sur chaque ligne d'équipement (274/274 tests verts) |
