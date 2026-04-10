# Story BUG-1: Correctif keyword matching — mots entiers uniquement (éviter faux positifs substring)

Status: done

## Story

As a utilisateur Jeedom avec des noms d'équipements courants (ex: "bureau", "lampe"),
I want que le mapper utilise un matching par mot entier (word boundary) au lieu d'un matching substring pour les keywords de nommage,
so that mes équipements ne soient pas classés "ambiguous" à cause de faux positifs sur des sous-chaînes.

## Acceptance Criteria

1. **AC-1 — Substring d'un keyword dans un nom → plus de faux positif**
   Un équipement nommé "lampe bureau" avec LIGHT_STATE/LIGHT_ON/LIGHT_OFF doit être mappé comme `light` avec confidence `sure` ou `probable`. Le keyword "eau" (présent dans `_NON_LIGHT_KEYWORDS`) ne doit PAS matcher car il n'apparaît pas comme mot entier dans "bureau".

2. **AC-2 — Mot entier keyword → toujours détecté**
   Un équipement nommé "eau chaude salon" avec LIGHT_STATE/LIGHT_ON/LIGHT_OFF → `confidence == "ambiguous"`, `reason_code == "name_heuristic_rejection"`. Le keyword "eau" matche comme mot entier. Idem pour "prise tv" → ambiguous dans le light mapper.

3. **AC-3 — Keyword composé avec tiret → ambiguous (comportement observable)**
   Un équipement nommé "chauffe-eau garage" avec LIGHT_STATE/LIGHT_ON/LIGHT_OFF → `confidence == "ambiguous"`, `reason_code == "name_heuristic_rejection"`. Ne pas asserter `matched_keyword` exact : l'itération sur un `set` est non déterministe et "chauffe-eau" comme "eau" peuvent tous deux matcher via word boundary (le tiret est un séparateur `\b`).

4. **AC-4 — Aucune régression**
   La suite complète `pytest` du repo passe sans régression.

5. **AC-5 — Couverture des trois mappers**
   Le correctif est appliqué dans `light.py`, `switch.py`, et `cover.py` — tous les endroits utilisant `kw in name_lower`.

## Tasks / Subtasks

- [x] Task 1 — Ajouter `import re` et créer helper de matching (AC: #5)
  - [x] Créer une fonction utilitaire `_keyword_matches(keyword: str, text: str) -> bool` qui encapsule `re.search(r'\b' + re.escape(keyword) + r'\b', text)` — soit dans chaque mapper (inline), soit dans un module partagé `mapping/utils.py` si pertinent
  - [x] Décision : inline dans chaque mapper (3 fichiers) est préférable pour un correctif minimal sans créer de nouveau module

- [x] Task 2 — Appliquer le correctif dans light.py (AC: #1, #2, #3, #5)
  - [x] Ajouter `import re` en tête du fichier
  - [x] Remplacer ligne ~195-196 : `matched_kw = next((kw for kw in _NON_LIGHT_KEYWORDS if kw in name_lower), None)` par `matched_kw = next((kw for kw in _NON_LIGHT_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', name_lower)), None)`
  - [x] Vérifier que le log existant `"name contains non-light keyword '%s' → ambiguous"` reste inchangé

- [x] Task 3 — Appliquer le correctif dans switch.py (AC: #5)
  - [x] Ajouter `import re` en tête du fichier
  - [x] Remplacer ligne ~135-136 : même pattern que light.py pour `_NON_SWITCH_KEYWORDS`
  - [x] **NE PAS modifier** le matching `_OUTLET_TYPE_KEYWORDS` (lignes ~301-302) qui opère sur `eq_type_name`, pas sur le nom d'équipement — hors périmètre

- [x] Task 4 — Appliquer le correctif dans cover.py (AC: #5)
  - [x] Ajouter `import re` en tête du fichier
  - [x] Remplacer ligne ~180-181 : même pattern que light.py pour `_NON_COVER_KEYWORDS`

- [x] Task 5 — Ajouter tests unitaires pour les faux positifs (AC: #1, #2, #3, #4)
  - [x] Dans `tests/unit/test_light_mapper.py` — classe `TestFalsePositivesGuardrails` :
    - [x] `test_bureau_with_light_cmds_not_ambiguous` :
      - Nom: "lampe bureau", cmds: LIGHT_STATE (info/binary) + LIGHT_ON + LIGHT_OFF
      - Attendu: `confidence in ("sure", "probable")` — "eau" ne matche pas dans "bureau"
    - [x] `test_eau_standalone_still_ambiguous` :
      - Nom: "eau chaude salon", cmds: LIGHT_STATE (info/binary) + LIGHT_ON + LIGHT_OFF
      - Attendu: `confidence == "ambiguous"`, `reason_code == "name_heuristic_rejection"`, `matched_keyword == "eau"`
    - [x] `test_chauffe_eau_still_ambiguous` :
      - Nom: "chauffe-eau garage", cmds: LIGHT_STATE (info/binary) + LIGHT_ON + LIGHT_OFF
      - Attendu: `confidence == "ambiguous"`, `reason_code == "name_heuristic_rejection"`
      - NE PAS asserter `matched_keyword` exact (set non ordonné : "chauffe-eau" ou "eau" peuvent matcher en premier)
    - [x] `test_bateau_not_ambiguous` :
      - Nom: "bateau salon", cmds: LIGHT_STATE (info/binary) + LIGHT_ON + LIGHT_OFF
      - Attendu: `confidence in ("sure", "probable")` — "eau" ne matche pas dans "bateau"
  - [x] Dans `tests/unit/test_switch_mapper.py` — classe `TestNameHeuristics` :
    - [x] `test_lampe_standalone_still_ambiguous` :
      - Nom: "Lampe salon", cmds: ENERGY_ON + ENERGY_OFF
      - Attendu: `confidence == "ambiguous"`, `reason_code == "name_heuristic_rejection"`, `matched_keyword == "lampe"`
      - Régression : confirme que le word-boundary matching préserve la détection des mots entiers
    - [x] `test_prechauffage_not_ambiguous` :
      - Nom: "Préchauffage moteur", cmds: ENERGY_ON + ENERGY_OFF
      - Attendu: `confidence in ("sure", "probable")` — "chauffage" ne matche pas dans "préchauffage" (sous-chaîne, pas mot entier)
      - Ce test ÉCHOUE avant correctif (substring "chauffage" in "préchauffage" → True) et PASSE après (word boundary → False)
  - [x] Dans `tests/unit/test_cover_mapper.py` — classe `TestFalsePositivesGuardrails` :
    - [x] `test_prise_standalone_still_ambiguous` :
      - Nom: "Prise USB bureau", cmds: FLAP_STATE (info/binary) + FLAP_UP + FLAP_DOWN
      - Attendu: `confidence == "ambiguous"`, `reason_code == "name_heuristic_rejection"`, `matched_keyword == "prise"`
      - Régression : confirme que le word-boundary matching préserve la détection des mots entiers
    - [x] `test_reprise_not_ambiguous` :
      - Nom: "Reprise ventilation", cmds: FLAP_STATE (info/binary) + FLAP_UP + FLAP_DOWN
      - Attendu: `confidence in ("sure", "probable")` — "prise" ne matche pas dans "reprise" (sous-chaîne, pas mot entier)
      - Ce test ÉCHOUE avant correctif (substring "prise" in "reprise" → True) et PASSE après (word boundary → False)

- [x] Task 6 — Exécuter la suite complète de tests (AC: #4)
  - [x] `pytest tests/ -v` : tous les tests PASS, 0 FAIL
  - [x] Vérifier qu'aucun test existant n'est cassé par le changement de matching

## Dev Notes

### Contexte du bug

Identifié lors de la validation terrain Story 5.2 (2026-03-21). Le mapper utilise `keyword in name.lower()` (matching substring) pour les keywords de nommage. Cela génère des faux positifs :
- "bureau" contient "eau" → bloque le mapping light
- "lampe bureau (ex-chevet)" → "bureau" contient "eau" → ambiguous au lieu de light
- Tout mot contenant un keyword comme sous-chaîne est affecté

**Source :** `_bmad-output/implementation-artifacts/post-5-2-documentation-needs.md` section BUG-1.

### Code actuel (identique dans les 3 mappers)

```python
name_lower = eq.name.lower()
matched_kw = next((kw for kw in _NON_*_KEYWORDS if kw in name_lower), None)
```

### Correctif

```python
import re
# ...
name_lower = eq.name.lower()
matched_kw = next((kw for kw in _NON_*_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', name_lower)), None)
```

### Comportement de `\b` avec les cas identifiés

| Nom | Keyword | Substring match | Word boundary match | Résultat attendu |
|-----|---------|----------------|--------------------|-|
| "bureau" | "eau" | ✅ (faux positif) | ❌ (pas de boundary) | Pas ambiguous |
| "eau chaude" | "eau" | ✅ | ✅ (mot entier) | Ambiguous |
| "chauffe-eau" | "chauffe-eau" | ✅ | ✅ (tiret = non-word) | Ambiguous |
| "chauffe-eau" | "eau" | ✅ (faux positif) | ✅ (tiret = boundary) | Ambiguous (OK — overlap : ne pas asserter le keyword exact, les deux sont valides) |
| "bateau" | "eau" | ✅ (faux positif) | ❌ | Pas ambiguous |
| "lampe salon" | "lampe" | ✅ | ✅ (mot entier) | Ambiguous (légitime) |
| "préchauffage" | "chauffage" | ✅ (faux positif) | ❌ (é = word char) | Pas ambiguous |
| "reprise" | "prise" | ✅ (faux positif) | ❌ (e = word char) | Pas ambiguous |

**Note Python 3 :** `re` utilise Unicode par défaut, `\b` reconnaît les caractères accentués comme caractères de mot. "lumière", "chaudière" etc. fonctionnent correctement comme mots entiers.

### Dev Agent Guardrails

- **Périmètre strict** : modifier UNIQUEMENT le pattern de matching keyword dans les 3 mappers (light.py, switch.py, cover.py)
- **NE PAS toucher** : logique generic_type, scoring de confidence, capabilities detection, deduplication, publication decision
- **NE PAS modifier** `_OUTLET_TYPE_KEYWORDS` dans switch.py (lignes ~301-302) — ce matching opère sur `eq_type_name` (type de plugin Jeedom), pas sur le nom d'équipement. Hors périmètre.
- **NE PAS créer de nouveau module** `mapping/utils.py` pour un helper aussi simple — garder le `re.search` inline dans chaque mapper
- **NE PAS modifier les keyword lists** elles-mêmes — le bug est dans le matching, pas dans le contenu des listes
- **Tests** : ajouter dans les classes existantes — `TestFalsePositivesGuardrails` pour light et cover, `TestNameHeuristics` pour switch — pas créer de nouveaux fichiers de test
- **Pattern de test** : suivre le pattern existant avec `_make_eq()` et `_cmd()` module-level factories, docstrings Given/When/Then
- **Non-déterminisme set** : ne jamais asserter `matched_keyword` exact quand plusieurs keywords du set peuvent matcher le même nom (ex: "chauffe-eau" → "chauffe-eau" ou "eau"). Asserter uniquement `confidence` et `reason_code`

### Fichiers impactés

| Fichier | Action | Lignes concernées |
|---------|--------|-------------------|
| `resources/daemon/mapping/light.py` | Ajouter `import re`, modifier matching L195-196 | ~3 lignes changées |
| `resources/daemon/mapping/switch.py` | Ajouter `import re`, modifier matching L135-136 | ~3 lignes changées |
| `resources/daemon/mapping/cover.py` | Ajouter `import re`, modifier matching L180-181 | ~3 lignes changées |
| `tests/unit/test_light_mapper.py` | Ajouter 4 tests dans `TestFalsePositivesGuardrails` | ~40 lignes ajoutées |
| `tests/unit/test_switch_mapper.py` | Ajouter 2 tests dans `TestNameHeuristics` | ~24 lignes ajoutées |
| `tests/unit/test_cover_mapper.py` | Ajouter 2 tests dans `TestFalsePositivesGuardrails` | ~24 lignes ajoutées |

### Project Structure Notes

- Aucune variance : le correctif suit les conventions existantes (inline dans chaque mapper)
- Aucun nouveau fichier créé
- Aucune nouvelle dépendance (module `re` est stdlib Python)

### References

- [Source: _bmad-output/implementation-artifacts/post-5-2-documentation-needs.md#BUG-1]
- [Source: resources/daemon/mapping/light.py#L61-74 (_NON_LIGHT_KEYWORDS), L195-196 (matching)]
- [Source: resources/daemon/mapping/switch.py#L56-61 (_NON_SWITCH_KEYWORDS), L135-136 (matching)]
- [Source: resources/daemon/mapping/cover.py#L54-59 (_NON_COVER_KEYWORDS), L180-181 (matching)]
- [Source: tests/unit/test_light_mapper.py#L230 (TestFalsePositivesGuardrails, test_name_heuristic_rejection)]
- [Source: tests/unit/test_switch_mapper.py#L350 (TestNameHeuristics)]
- [Source: tests/unit/test_cover_mapper.py#L292 (TestFalsePositivesGuardrails, test_name_heuristic_rejection)]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

Aucun blocage. Correctif appliqué tel que spécifié dans la story.

### Completion Notes List

- ✅ `import re` ajouté dans les 3 mappers (light.py, switch.py, cover.py)
- ✅ Matching keyword remplacé par `re.search(r'\b' + re.escape(kw) + r'\b', name_lower)` inline dans chaque mapper
- ✅ `_OUTLET_TYPE_KEYWORDS` dans switch.py non modifié (hors périmètre)
- ✅ 4 tests ajoutés dans `TestFalsePositivesGuardrails` (test_light_mapper.py) : faux positifs "bureau"/"bateau" corrigés, vrais positifs "eau chaude"/"chauffe-eau" préservés
- ✅ 2 tests ajoutés dans `TestNameHeuristics` (test_switch_mapper.py) : faux positif "Préchauffage moteur" corrigé, vrai positif "Lampe salon" préservé
- ✅ 2 tests ajoutés dans `TestFalsePositivesGuardrails` (test_cover_mapper.py) : faux positif "Reprise ventilation" corrigé, vrai positif "Prise USB bureau" préservé
- ✅ Suite complète : 262 tests, 0 échec

### File List

- `resources/daemon/mapping/light.py`
- `resources/daemon/mapping/switch.py`
- `resources/daemon/mapping/cover.py`
- `tests/unit/test_light_mapper.py`
- `tests/unit/test_switch_mapper.py`
- `tests/unit/test_cover_mapper.py`

## Change Log

- 2026-03-21 : BUG-1 — Remplacement du matching substring `kw in name_lower` par word boundary `re.search(r'\b' + re.escape(kw) + r'\b', name_lower)` dans les 3 mappers. Ajout de 8 tests unitaires couvrant les faux positifs corrigés et les vrais positifs préservés.
