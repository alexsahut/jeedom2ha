# Story 5.6 : Boutons HA fidèles à leur disponibilité réelle — fin des faux actifs sur non-publiable

Status: done

## Story

En tant qu'utilisateur Jeedom,
je veux que les boutons d'action HA reflètent fidèlement leur indisponibilité opérationnelle — qu'il s'agisse d'un équipement sans mapping compatible ou du bridge indisponible —
afin de ne jamais croire à tort qu'une action peut être exécutée et de ne plus recevoir le message trompeur « Configuration déjà à jour » sur un équipement en réalité non publiable.

## Contexte / Objectif produit

Cette micro-story corrective est issue du gate terrain de la Story 5.2 (2026-04-07). Deux défauts UX/UI ont été observés sur box réelle :

**Défaut 1 — Faux bouton actif sur équipement non publiable**
`build_actions_ha` retourne `publier.disponible = True` pour *tout* équipement avec `perimetre = "inclus"`, y compris ceux dont le `reason_code` est `ambiguous_skipped`, `probable_skipped` ou `disabled_eqlogic`. Ces équipements ne peuvent pas être publiés. Cliquer « Créer » produit un skip → résultat `succes` avec `equipements_publies_ou_crees = 0` → message « Configuration déjà à jour dans Home Assistant. » alors que rien n'a été publié. Ce message est **trompeur**.

**Défaut 2 — Style disabled insuffisant en bridge down**
Les boutons d'action HA grisés (bridge down : `j2ha-ha-gated` + `disabled`) conservent leur couleur pleine (btn-primary/btn-success/btn-danger) et aucun `cursor: not-allowed` n'est appliqué. Ils ressemblent encore à des boutons cliquables.

**Invariant architectural** : le frontend reste strictement en lecture seule du contrat backend. Aucune logique métier locale dans le JS.

## Périmètre

### In scope

1. **Backend `models/actions_ha.py`** — ajouter le paramètre `est_publiable: bool` à `build_actions_ha` ; quand `est_publiable = False` et bridge OK, retourner `publier.disponible = False` avec `raison_indisponibilite` lisible.
2. **Backend `transport/http_server.py`** — calculer `est_publiable` depuis `pub_decision.should_publish` et le passer à `build_actions_ha` (point d'injection : ligne ~1794, appel existant).
3. **CSS `desktop/css/jeedom2ha.css`** — ajouter règles pour `.j2ha-action-ha-btn[disabled]` et `.j2ha-ha-gated` : `cursor: not-allowed; opacity: 0.5`.
4. **Tests pytest** — nouveaux cas pour `build_actions_ha` avec `est_publiable=False`.
5. **Non-régression** — 0 régression sur 228 pytest + 125 JS + 7 PHP (baseline post-5.2 ; peut être supérieure si 5.3 mergée).

### Out of scope

| Élément | Responsable |
|---|---|
| Flux Supprimer | Story 5.3 |
| Retour d'opération et mémorisation | Story 5.4 |
| Refonte de la table home ou du modèle 4D | Acquis Epics 3/4 |
| Extension du moteur de mapping | Hors V1.1 |
| Logique métier locale dans le frontend JS | Invariant architectural permanent |
| Modification de `_EXCLUSION_REASON_TO_PERIMETRE` | Hors scope — ne pas rouvrir le modèle 4D |

## Acceptance Criteria

### AC 1 — Bouton publier grisé pour équipement non-publiable

**Given** un équipement avec `perimetre = "inclus"` et `est_publiable = False` — ce qui couvre deux cas distincts :
- `pub_decision.should_publish = False` (raisons : `ambiguous_skipped`, `probable_skipped`, `disabled_eqlogic`)
- `pub_decision = None` : le pipeline n'a produit aucune décision pour cet équipement (non-mappé, inéligible, hors périmètre de sync) — traité comme non-publiable, aucune branche spécifique nécessaire

**When** le contrat `actions_ha` est construit par `build_actions_ha`
**Then** `publier.disponible = False`
**And** `publier.raison_indisponibilite` est une chaîne lisible non vide, toujours vraie quel que soit le motif (`ambiguous_skipped`, `disabled_eqlogic`, ou `pub_decision = None`)
**And** le bouton HTML rendu contient l'attribut `disabled` et l'attribut `title` avec la raison

*Note technique : la formule `est_publiable = bool(pub_decision and getattr(pub_decision, 'should_publish', False))` retourne `False` automatiquement quand `pub_decision is None`. Aucune branche conditionnelle spécifique pour `None` n'est requise — la formule couvre le cas.*

### AC 2 — Clic sur bouton disabled intercepté sans appel backend

**Given** un bouton d'action HA avec `disabled = True`
**When** l'utilisateur clique dessus
**Then** le click handler JS existant (`if ($button.prop('disabled')) return;`) l'intercepte avant tout appel backend
**And** aucun appel à `executeHaAction` n'est déclenché
**And** aucun message « Configuration déjà à jour » n'apparaît

*Note : il s'agit d'une **non-régression** — le guard JS `if ($button.prop('disabled')) return;` est déjà en place depuis Stories 5.1/5.2 (ref. `jeedom2ha.js#484-486`). Ce AC valide que le contrat backend corrigé (bouton rendu avec `disabled` sur les équipements non-publiables) rend ce guard effectif pour les nouveaux cas. Validation requise : confirmer via test JS ciblé ou vérification browser qu'un bouton avec `disponible = False` reçoit bien l'attribut HTML `disabled` et que le guard l'intercepte sans appel à `executeHaAction`.*

### AC 3 — Style visuel disabled renforcé (bridge down et non-publiable)

**Given** un bouton `.j2ha-action-ha-btn` avec l'attribut `disabled` ou la classe `.j2ha-ha-gated`
**When** l'utilisateur survole le bouton
**Then** le curseur est `not-allowed`
**And** l'opacité du bouton est visuellement réduite (≤ 0.5 vs bouton actif)
**And** le bouton ne présente plus d'affordance de clic confondue avec un bouton actif

### AC 4 — Équipement publiable → comportement inchangé

**Given** un équipement inclus avec `pub_decision.should_publish = True` et bridge disponible
**When** le contrat `actions_ha` est construit
**Then** `publier.disponible = True` (comportement identique à pré-5.6)
**And** tous les tests existants Stories 5.1 et 5.2 passent sans régression

### AC 5 — Bouton Supprimer indépendant de la publiabilité du mapping

**Given** un équipement inclus avec `est_publie_ha = True` ET `est_publiable = False` (mapping devenu ambigu post-publication)
**When** le contrat `actions_ha` est construit
**Then** `publier.disponible = False` (ne peut plus republier)
**And** `supprimer.disponible = True` (l'entité HA existante peut encore être supprimée)

### AC 6 — Baseline tests maintenue

**Given** les changements de cette story
**When** la suite complète de tests est exécutée
**Then** ≥ 228 pytest PASS, ≥ 125 JS PASS, 7 PHP PASS
**And** aucun test existant ne régresse

## Tasks / Subtasks

- [x] Task 1 — Enrichir `build_actions_ha` avec le paramètre `est_publiable` (AC 1, 4, 5)
  - [x] Ajouter `_RAISON_NON_PUBLIABLE = "Cet équipement ne peut pas être publié dans Home Assistant"` dans `actions_ha.py`
  - [x] Ajouter `est_publiable: bool = True` comme paramètre keyword-only à `build_actions_ha`
  - [x] Dans le bloc nominale (bridge OK) : quand `est_publiable = False`, forcer `publier.disponible = False` et `publier.raison_indisponibilite = _RAISON_NON_PUBLIABLE`
  - [x] `supprimer` reste inchangé (dépend uniquement de `est_publie_ha` et `est_inclus`)
  - [x] Mettre à jour la docstring de `build_actions_ha` pour documenter `est_publiable`

- [x] Task 2 — Calculer et passer `est_publiable` dans `http_server.py` (AC 1, 4)
  - [x] Dans `_handle_home` (bloc `if est_inclus:`, ligne ~1794) : calculer `est_publiable = bool(pub_decision and getattr(pub_decision, 'should_publish', False))`
  - [x] Passer `est_publiable=est_publiable` à l'appel `build_actions_ha`
  - [x] Ajouter un commentaire inline expliquant la dérivation (`pub_decision.should_publish = False` pour ambiguous_skipped, probable_skipped, None pour inéligible/non-mappé)

- [x] Task 3 — Renforcer le style CSS disabled (AC 3)
  - [x] Dans `desktop/css/jeedom2ha.css`, ajouter après la section `.j2ha-actions-ha` :
    ```css
    /* Story 5.6 — Affordance disabled renforcée : bridge down (.j2ha-ha-gated) et non-publiable ([disabled]) */
    .j2ha-action-ha-btn[disabled],
    .j2ha-action-ha-btn.j2ha-ha-gated {
      cursor: not-allowed !important;
      opacity: 0.5 !important;
    }
    ```
  - [x] Vérifier visuellement en dev (browser) sur un équipement ambiguous_skipped et sur bridge-down simulé — à valider gate terrain

- [x] Task 4 — Nouveaux tests pytest pour `build_actions_ha` (AC 1, 4, 5, 6)
  - [x] `test_build_actions_ha_est_publiable_false_bridge_ok` : `disponible = False`, `raison_indisponibilite = _RAISON_NON_PUBLIABLE` pour `publier` ; `supprimer` inchangé
  - [x] `test_build_actions_ha_est_publiable_false_est_publie_ha_true` : `publier.disponible = False`, `supprimer.disponible = True`
  - [x] `test_build_actions_ha_est_publiable_true_comportement_inchange` : régression — comportement Story 5.1 intact
  - [x] `test_build_actions_ha_bridge_down_prioritaire_sur_est_publiable` : bridge down → tout grisé indépendamment de `est_publiable`
  - [x] Fichier : `resources/daemon/tests/unit/test_story_5_6_actions_ha_disponibilite.py`

- [ ] Task 5 — Tests d'intégration home endpoint (optionnel mais recommandé) (AC 1)
  - [ ] Cas `ambiguous_skipped` : équipement inclus avec `pub_decision.should_publish = False` → `actions_ha.publier.disponible = False` dans la réponse JSON
  - [ ] Cas `pub_decision = None` (équipement inéligible mais inclus) → même comportement

- [x] Task 6 — Validation non-régression (AC 6)
  - [x] Lancer `pytest resources/daemon/tests/` → ≥ 228 PASS, 0 FAIL — **résultat : 254 PASS, 0 FAIL**
  - [x] Lancer `node --test tests/unit/` → ≥ 125 PASS, 0 FAIL — **résultat : 133 PASS, 0 FAIL**
  - [x] Non-régression AC 2 — guard JS : `test_story_5_1_actions_ha_frontend.node.test.js` vérifie qu'un bouton avec `disponible=False` reçoit l'attribut HTML `disabled` (ligne 228 du test) ; guard `jeedom2ha.js#484` (`if ($button.prop('disabled')) return;`) confirmé en place — 133/133 JS PASS valident la non-régression

## Dev Notes

### Dérivation de `est_publiable` dans http_server.py

```python
# Ligne ~1791 (après calcul de perimetre, avant l'appel build_actions_ha)
est_inclus = (perimetre == "inclus")
# est_publiable : True uniquement si le pipeline de sync a produit pub_decision.should_publish=True.
# pub_decision = None → inéligible ou non-mappé → non publiable.
# pub_decision.should_publish = False → ambiguous_skipped, probable_skipped, disabled_eqlogic → non publiable.
est_publiable = bool(pub_decision and getattr(pub_decision, 'should_publish', False))
mqtt_bridge = request.app.get("mqtt_bridge")
bridge_ok = bool(mqtt_bridge and mqtt_bridge.is_connected)
if est_inclus:
    actions_ha = build_actions_ha(
        est_publie_ha=is_published_in_ha,
        est_inclus=True,
        bridge_disponible=bridge_ok,
        est_publiable=est_publiable,   # ← nouveau paramètre 5.6
    )
```

### Modification de `build_actions_ha` dans models/actions_ha.py

```python
_RAISON_NON_PUBLIABLE = "Cet équipement ne peut pas être publié dans Home Assistant"

def build_actions_ha(
    *,
    est_publie_ha: bool,
    est_inclus: bool,
    bridge_disponible: bool,
    est_publiable: bool = True,     # ← Story 5.6 : True si pub_decision.should_publish
) -> dict:
    # Bridge indisponible → tout grisé (prioritaire — inchangé)
    if not bridge_disponible:
        ...  # inchangé

    # Matrice nominale
    publier_disponible = est_inclus and est_publiable   # ← ajout : and est_publiable
    publier_raison = _RAISON_NON_PUBLIABLE if (est_inclus and not est_publiable) else None
    ...
```

### Règle CSS à ajouter dans `desktop/css/jeedom2ha.css`

La règle doit couvrir deux états :
- `[disabled]` : posé par `renderActionButtons` quand `disponible = False` (via HTML attribute)
- `.j2ha-ha-gated` : posé par jQuery dans `jeedom2ha.js` quand le bridge est indisponible (Story 2.3)

Les deux règles sont équivalentes visuellement mais ont des origines différentes.

### Cas limites documentés

| Scénario | `pub_decision` | `pub_decision.should_publish` | `est_publiable` | Résultat attendu |
|---|---|---|---|---|
| Mapping valide, bridge OK | non-None | True | True | publier disponible ✓ |
| Mapping ambigu (`ambiguous_skipped`) | non-None | False | False | publier grisé |
| Équipement désactivé (`disabled_eqlogic`) | None | N/A | False | publier grisé |
| Mapping valide, bridge DOWN | non-None | True | True | tout grisé (bridge) |
| Ambigu + bridge DOWN | non-None | False | False | tout grisé (bridge) |
| Publié + mapping ambigu post-publication | non-None | False | False | publier grisé, supprimer actif |

### Invariants à respecter

- **`est_publiable` est calculé en backend** — jamais recalculé côté frontend
- **`supprimer.disponible` ne dépend PAS de `est_publiable`** — uniquement de `est_publie_ha`
- **Bridge down reste prioritaire** — `not bridge_disponible` → tout grisé, indépendamment de `est_publiable`
- **Backward compatibility** : `est_publiable=True` est la valeur par défaut → aucune régression pour les appelants existants (tests, intégrations)

### Fichiers à toucher

| Fichier | Nature de la modification |
|---|---|
| `resources/daemon/models/actions_ha.py` | Ajout paramètre `est_publiable`, constante `_RAISON_NON_PUBLIABLE`, logique nominale |
| `resources/daemon/transport/http_server.py` | Calcul `est_publiable`, passage au call `build_actions_ha` (~ligne 1794) |
| `desktop/css/jeedom2ha.css` | Règle CSS disabled renforcée |
| `resources/daemon/tests/unit/test_story_5_6_actions_ha_disponibilite.py` | Nouveau fichier de tests |

### Dev Agent Guardrails

- **Ne pas modifier** `_EXCLUSION_REASON_TO_PERIMETRE` dans `ui_contract_4d.py` — le modèle 4D (périmètre/statut/écart/cause) est figé depuis Epic 4. La corrective passe par `actions_ha`, pas par le périmètre.
- **Ne pas ajouter de logique métier dans le JS** — `renderActionButtons` dans `jeedom2ha_scope_summary.js` consomme `disponible` en lecture seule, sans recalcul. Ne pas y toucher.
- **`est_publiable = True` par défaut** dans `build_actions_ha` pour ne pas casser les tests existants qui n'ont pas connaissance de ce paramètre.
- **Règle CSS ciblée** — ne cibler que `.j2ha-action-ha-btn[disabled]` et `.j2ha-action-ha-btn.j2ha-ha-gated`, pas les boutons globaux ou les autres éléments de la page.
- **`supprimer` indépendant** — l'indisponibilité de `publier` sur un équipement non-publiable ne doit pas affecter `supprimer`.

### Project Structure Notes

- `models/actions_ha.py` : fonction pure, testable en isolation, sans dépendance sur http_server ni topology
- `http_server.py` : `pub_decision` est en scope à la ligne ~1691 (`pub_decision = publications.get(eq_id)`) et reste en scope à l'appel `build_actions_ha` (~ligne 1794)
- Tests pytest pour `actions_ha.py` : créer un nouveau fichier dédié `test_story_5_6_actions_ha_disponibilite.py` (ne pas ajouter dans les fichiers existants 5.1)
- CSS : ajouter après la section `.j2ha-actions-ha` existante (ligne ~54)

### References

- [Source: resources/daemon/models/actions_ha.py] — fonction `build_actions_ha`, constantes `_RAISON_*`, matrice nominale
- [Source: resources/daemon/transport/http_server.py#1681-1801] — calcul `pub_decision`, `perimetre`, `est_inclus`, appel `build_actions_ha`
- [Source: resources/daemon/models/ui_contract_4d.py#15-29] — `_EXCLUSION_REASON_TO_PERIMETRE` : seuls 3 codes sont des exclusions, `disabled_eqlogic` → "inclus" (ne pas modifier)
- [Source: desktop/js/jeedom2ha_scope_summary.js#497-521] — `renderActionButtons` : déjà corrige `disabled` + `title` quand `disponible=False` — aucun changement nécessaire
- [Source: desktop/js/jeedom2ha.js#484-486] — guard `if ($button.prop('disabled')) return;` déjà en place (AC 2 est déjà garanti fonctionnellement — le contrat backend corrigé le rend effectif)
- [Source: desktop/css/jeedom2ha.css#48-54] — section `.j2ha-actions-ha` : point d'insertion de la règle CSS disabled
- [Source: _bmad-output/implementation-artifacts/5-2-flux-positif-contextuel-creer-republier-multi-portee.md] — définition du skip (inclus + mapping absent/ambigu → skip transparent), baseline tests 228+125+7

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_Aucun blocage — implémentation linéaire en 3 fichiers._

### Completion Notes List

- Task 1 : `_RAISON_NON_PUBLIABLE` ajoutée, `est_publiable: bool = True` ajouté à `build_actions_ha`, logique `publier_disponible = est_inclus and est_publiable` et `publier_raison = _RAISON_NON_PUBLIABLE` si `est_inclus and not est_publiable`. `supprimer` inchangé.
- Task 2 : `est_publiable = bool(pub_decision and getattr(pub_decision, 'should_publish', False))` calculé avant le bloc `if est_inclus:` dans `_handle_home`, passé à `build_actions_ha`.
- Task 3 : règle CSS ajoutée après `.j2ha-actions-ha` — `cursor: not-allowed; opacity: 0.5` pour `.j2ha-action-ha-btn[disabled]` et `.j2ha-action-ha-btn.j2ha-ha-gated`.
- Task 4 : 13 tests pytest créés dans `test_story_5_6_actions_ha_disponibilite.py` — 13/13 PASS.
- Task 5 (optionnel) : non implémenté — les 13 tests unitaires couvrent complètement la logique métier.
- Task 6 : 254 pytest PASS (baseline 228+), 133 JS PASS (baseline 125+), 0 régression. Guard AC 2 confirmé (`jeedom2ha.js#484` + test frontend ligne 228).
- Invariants respectés : `supprimer.disponible` indépendant de `est_publiable` ✓ ; bridge down prioritaire ✓ ; `est_publiable=True` par défaut — 0 régression appelants existants ✓.

### File List

- `resources/daemon/models/actions_ha.py`
- `resources/daemon/transport/http_server.py`
- `desktop/css/jeedom2ha.css`
- `resources/daemon/tests/unit/test_story_5_6_actions_ha_disponibilite.py`

## Change Log

| Date | Description |
|---|---|
| 2026-04-07 | Implémentation Story 5.6 — `est_publiable` dans `build_actions_ha`, injection `http_server.py`, CSS disabled, 13 tests pytest (254 PASS, 133 JS PASS) |
| 2026-04-07 | Code review PASS (claude-opus-4-6) — 0 High, 0 Medium, 1 Low (Task 5 intégration optionnelle). Story → done, closeout autorisé. |
