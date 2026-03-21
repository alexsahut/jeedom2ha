# Post-terrain 5.2 — Besoins de documentation et correctifs identifiés

Issu de la validation terrain Story 5.2 (2026-03-21).

---

## DOC-1 — Comportement `suggested_area` dans Home Assistant

### Contexte

Le plugin publie `suggested_area` dans le payload MQTT Discovery lors de chaque sync.
Lors de TC-2, le log LIFECYCLE et le payload ont été correctement mis à jour (`bureau`),
mais l'entité est restée dans la pièce d'origine (`chambre parents`) dans HA.

### Explication technique

`suggested_area` est une **suggestion à la création** du device dans HA. Pour les devices déjà
enregistrés, HA ignore les changements de `suggested_area` dans les messages discovery suivants —
comportement documenté dans la spec HA MQTT Discovery.

### Ce que le plugin garantit (contrat)

- Log `[LIFECYCLE] area change` quand l'objet Jeedom est renommé ✅
- Champ `suggested_area` mis à jour dans le payload ✅

### Ce que HA ne fait PAS automatiquement

- HA ne déplace pas le device d'une pièce à l'autre quand `suggested_area` change

### Marche à suivre pour l'utilisateur

**Option 1 — Cleanup discovery** (réinitialise l'enregistrement HA, `suggested_area` est réappliqué) :
```bash
./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon
```
> ⚠️ Entraîne une recréation des entités HA — les customisations manuelles (icônes, alias) sont perdues.

**Option 2 — Déplacement manuel dans HA**
Dans HA → Paramètres → Appareils et services → trouver le device → modifier la zone.

### Où documenter

- [ ] `docs/fr_FR/index.md` (ou fichier documentation plugin) — section "Comportement des pièces"
- [ ] FAQ ou note dans l'interface de diagnostic (tooltip ou info-bulle sur le champ "Pièce Jeedom")

---

## DOC-2 — Règles de mapping generic_type → entity_type HA

### Contexte

Lors de TC-3, des noms d'équipements courants ont produit des ambiguïtés non anticipées :

| Nom | Problème |
|-----|----------|
| `"lampe bureau (ex-chevet)"` | "bureau" contient "eau" → non-light keyword → ambiguous |
| `"lampe (ex-chevet)"` | "lampe" → non-switch keyword → bloque le retypage switch |

L'interface de diagnostic affiche `ambiguous` sans expliquer quelle règle a été déclenchée.

### Règles actuelles (non documentées)

Le mapper utilise des listes de keywords avec un matching **substring** (`keyword in name.lower()`).
Les listes exactes sont dans `resources/daemon/mapping/light.py`, `switch.py`, `cover.py`.

### Ce qu'il faut documenter

1. **Liste des keywords par type** — lesquels bloquent quel mapping
2. **Logique de priorité** — generic_type prime sur name ; les keywords servent à lever ou bloquer l'ambiguïté
3. **Exemples de noms problématiques** — "bureau" (eau), "lampe" (switch), etc.

### Où documenter

- [ ] `docs/fr_FR/index.md` — section "Nommage des équipements"
- [ ] Interface diagnostic — afficher la règle déclenchée (ex: "name contains non-light keyword 'eau'")

---

## BUG-1 — Substring keyword matching (faux positifs)

### Sévérité

Moyenne — impact utilisateur réel, silencieux (ambiguïté non expliquée).

### Description

La logique `keyword in name.lower()` fait du matching substring, non mot entier.
Exemples de faux positifs :
- `"bureau"` contient `"eau"` → bloque light
- `"lambrequin"` contient `"lam"` → risque similaire
- Tout mot contenant un keyword comme sous-chaîne

### Correctif attendu

Remplacer le matching substring par une recherche de **mot entier** :
```python
import re
re.search(r'\b' + re.escape(keyword) + r'\b', name.lower())
```

### Périmètre

`resources/daemon/mapping/light.py`, `switch.py`, `cover.py` — fonctions de détection de keywords.

### Story à créer

- Epic cible : Epic 5 (lifecycle) ou Epic 6 (à définir)
- Titre suggéré : "Correctif keyword matching — mots entiers uniquement (éviter faux positifs substring)"
- Taille estimée : Small (correctif ciblé + tests)
- Dépendances : aucune — isolé dans les mappers

### Impact immédiat

En attendant le correctif, conseiller aux utilisateurs d'éviter dans les noms d'équipements :
- Pour les lumières : mots contenant `eau`, `prise`, `switch`, `interrupteur`
- Pour les switches : mots contenant `lampe`, `lumière`, `light`, `spot`

---

## Résumé des actions

| ID | Type | Priorité | Action |
|----|------|----------|--------|
| DOC-1 | Documentation | Moyen | Documenter comportement `suggested_area` HA dans docs plugin |
| DOC-2 | Documentation | Moyen | Documenter règles de mapping keyword dans docs plugin + diagnostic |
| BUG-1 | Correctif | Moyen | Story : remplacer substring par word-boundary matching dans mappers |
