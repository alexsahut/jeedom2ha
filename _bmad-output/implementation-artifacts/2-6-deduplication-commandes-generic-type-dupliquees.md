# Story 2.6: Déduplication des commandes à generic_type dupliqué

Status: review

## Story

As a utilisateur Jeedom,
I want que le moteur de mapping gère intelligemment les équipements ayant plusieurs commandes avec le même generic_type,
so that mes équipements correctement typés ne soient pas faussement classés comme ambigus.

## Contexte de découverte

Ce bug a été identifié lors de la validation terrain de la Story 4.2bis (diagnostic explicabilité) sur une box Jeedom réelle (192.168.1.21).

Le diagnostic 4.2bis expose correctement la décision du moteur de mapping — le problème est en amont, dans la logique de mapping elle-même. La Story 4.2bis n'est pas concernée par ce fix.

### Symptôme observé

Un équipement lumière correctement typé avec un jeu complet de commandes `LIGHT_*` (LIGHT_ON, LIGHT_OFF, LIGHT_STATE, LIGHT_SLIDER, LIGHT_BRIGHTNESS) est classé `ambiguous_skipped` et n'est pas publié vers Home Assistant.

### Cas terrain principal

- **Équipement** : "buanderie plafonnier et plan de travail" (eq_id=510)
- **Log démon** : `[MAPPING] eq_id=510 name='...': duplicate command for generic_type 'LIGHT_STATE' (cmd1=4655, cmd2=4658) → ambiguous`
- **Autres cas potentiels** : eq_id=511 (Entrée et spot salon), eq_id=446 (Fibaro Volets — domaine cover)

### Comportement actuel

Dans `mapping/light.py:102-122` et `mapping/cover.py:91-107`, dès qu'un second `cmd` porte le même `generic_type` qu'un `cmd` déjà collecté, le mapper retourne immédiatement un `MappingResult` avec `confidence="ambiguous"` et `reason_code="duplicate_generic_types"`, sans tenter aucune stratégie de sélection.

### Comportement attendu

Le moteur de mapping devrait tenter un arbitrage déterministe lorsqu'un doublon de generic_type est détecté sur un eqLogic, et ne classer l'équipement comme ambigu que si aucun critère de départage sûr n'est applicable.

### Hypothèse technique

Côté Jeedom, un même eqLogic peut légitimement avoir deux commandes avec le même generic_type (ex : deux `LIGHT_STATE`, une `sub_type=binary` pour l'état on/off, une `sub_type=numeric` pour le retour brightness). La cause est une configuration Jeedom typique sur certains modules multi-canal.

**Champs disponibles pour le départage** (modèle `JeedomCmd` dans `models/topology.py:73-83`) :
- `sub_type` : `binary`, `numeric`, `string`, `slider`, `color`, `other`
- `type` : `info`, `action`
- `cmd.id` : entier immutable attribué par Jeedom (ordre de création)

> **`cmd.order` n'existe pas** sur `JeedomCmd`. Ne pas l'utiliser. Seul `cmd.id` est disponible comme critère d'ancienneté.

### Impact utilisateur

Des équipements fonctionnels et correctement typés sont invisibles dans HA sans raison compréhensible pour l'utilisateur. La remédiation proposée par le diagnostic ("vérifier les types génériques") est trompeuse car les types sont corrects.

## Algorithme de déduplication (Spec)

Quand un doublon de `generic_type` est détecté dans la boucle de collecte des commandes, au lieu de retourner immédiatement `ambiguous`, appliquer l'algorithme suivant **dans cet ordre strict** :

```
ENTRÉE : cmd_existing (déjà dans le dict), cmd_new (doublon détecté)
         generic_type dupliqué (ex: "LIGHT_STATE")

ÉTAPE 1 — Discrimination par sub_type
  Si cmd_existing.sub_type ≠ cmd_new.sub_type :
    Choisir le candidat dont le sub_type correspond au rôle attendu.
    Règle domaine light :
      - LIGHT_STATE attendu comme info d'état → préférer "binary" pour on/off
      - LIGHT_BRIGHTNESS attendu comme info numérique → préférer "numeric"
    Règle domaine cover :
      - FLAP_STATE → préférer "binary"
      (FLAP_SLIDER : pas de déduplication implémentée — scope final limité à FLAP_STATE)
    → Gagnant sélectionné, confiance plafonnée à "probable".
    → SORTIE : stocker le gagnant dans le dict, continuer la collecte.
    La commande perdante est ignorée (pas réexploitée, cf. Limites).

ÉTAPE 2 — Même sub_type
  Si cmd_existing.sub_type == cmd_new.sub_type :
    → SORTIE : retourner MappingResult(confidence="ambiguous", reason_code="duplicate_generic_types").
    Politique conservative : pas d'arbitrage possible.

PAS D'ÉTAPE 3 — Pas de fallback implicite.
```

> **Décision architecturale** : quand les deux commandes ont le même `sub_type`, on ne départage pas par `cmd.id`. Le `cmd.id` reflète l'ordre de création dans Jeedom, pas une sémantique fonctionnelle. Départager sur cette base serait un choix arbitraire incompatible avec la politique conservative.

## Contrat de données

**`MappingResult.commands`** reste `Dict[str, JeedomCmd]` — le gagnant de la déduplication prend le slot. Pas de nouveau champ, pas de mapping par rôle logique. La commande perdante n'est pas stockée dans le résultat.

**Cas LIGHT_STATE binary + LIGHT_STATE numeric** : l'étape 1 sélectionne `binary` pour le slot `LIGHT_STATE` (car le rôle attendu est un état on/off). La commande `numeric` perdante est **supprimée du résultat**. Elle n'est pas réexploitée comme source alternative de brightness — le mapper calcule les capacités brightness uniquement sur `LIGHT_BRIGHTNESS` et `LIGHT_SLIDER`, comme avant. **C'est une limite assumée** : un équipement dont le seul indicateur de brightness est un `LIGHT_STATE numeric` dupliqué perdra cette information après déduplication. La correction ne dégrade pas le cas nominal (brightness via `LIGHT_BRIGHTNESS`/`LIGHT_SLIDER` reste inchangée).

## Acceptance Criteria

1. **Given** un eqLogic lumière avec 2× `LIGHT_STATE` de `sub_type` différents (binary + numeric) **When** le mapper light traite cet équipement **Then** le mapper sélectionne `sub_type=binary` pour le slot `LIGHT_STATE`, poursuit le calcul des capacités sur le dict dédupliqué, et produit un `MappingResult` avec `confidence` plafonnée à `"probable"` et un `reason_code` standard (`light_on_off_brightness`, `light_on_off_only`, etc. — selon les capacités détectées, pas un code spécifique à la déduplication)

2. **Given** un eqLogic lumière avec 2× `LIGHT_STATE` de même `sub_type` **When** le mapper light traite cet équipement **Then** le mapper retourne `MappingResult(confidence="ambiguous", reason_code="duplicate_generic_types")` comme aujourd'hui (pas de régression)

3. **Given** un eqLogic cover avec doublons `FLAP_STATE` de `sub_type` différents (binary + numeric) **When** le mapper cover traite cet équipement **Then** le mapper sélectionne `sub_type=binary` pour le slot `FLAP_STATE` et poursuit le calcul des capacités cover avec confiance plafonnée à `"probable"`

4. **And** la logique de déduplication est cohérente dans `light.py` et `cover.py` (fonction partagée ou logique dupliquée identique). Chaque mapper définit sa propre table de préférence sub_type par generic_type

5. **And** la traçabilité de la déduplication repose exclusivement sur :
   - `MappingResult.reason_details` enrichi avec `{"deduplicated": true, "duplicate_type": "<generic_type>", "kept_cmd_id": <id>, "discarded_cmd_id": <id>, "criterion": "sub_type"}`
   - Log `[MAPPING]` niveau `info` indiquant la résolution (remplace le `warning` actuel)
   - **Pas de nouveau `reason_code`** : le mapper produit le reason_code standard des capacités détectées. La couche publication (`decide_publication`) et la couche diagnostic (`_CLOSED_REASON_MAP`) ne nécessitent aucune modification — un MappingResult `probable` suit le chemin de publication existant

6. **And** les tests unitaires dans `tests/unit/` couvrent :
   - doublon `LIGHT_STATE` (binary + numeric) → `confidence="probable"`, `reason_details["deduplicated"]=True`
   - doublon `LIGHT_STATE` (numeric + numeric) → `confidence="ambiguous"`, `reason_code="duplicate_generic_types"`
   - doublon `FLAP_STATE` (binary + numeric) → `confidence="probable"`, `reason_details["deduplicated"]=True`
   - cas nominal light sans doublon → `confidence="sure"` (pas de régression)
   - cas nominal cover sans doublon → pas de régression

## Hors scope

- **Story 4.2bis** : aucune modification — le diagnostic expose correctement la décision actuelle du moteur
- **docs/forensics/** : aucune modification
- **Politique de confiance** : pas de changement de politique d'exposition ; la déduplication produit au mieux `probable`, soumis à la politique existante
- **Détection root-cause Jeedom** : on ne corrige pas la source des doublons côté Jeedom, on les gère côté mapping
- **`switch.py`** : explicitement exclu. Le switch mapper (`mapping/switch.py:95-98`) n'a pas de guard de duplication — il écrase silencieusement (`energy_cmds[cmd.generic_type] = cmd`). C'est un comportement différent (pas un bug de rejet), et le risque de faux positif switch est faible. Aligner switch.py est un sujet séparé si nécessaire.
- **Exploitation de la commande perdante** : la commande non retenue (ex: `LIGHT_STATE numeric` quand `binary` gagne) est ignorée. Elle n'est pas réutilisée comme source alternative de brightness ni stockée nulle part dans le résultat. **Limite assumée** : si le seul indicateur brightness d'un équipement est un `LIGHT_STATE numeric` dupliqué, cette information est perdue après déduplication.
- **Taxonomie AC2 / `_CLOSED_REASON_MAP`** : aucune modification nécessaire. Le mapper dédupliqué produit un reason_code standard (`light_on_off_brightness`, etc.) qui est déjà géré par la chaîne de publication et de diagnostic existante.

## Tasks / Subtasks

- [x] Task 1 — Implémenter la déduplication dans LightMapper (AC: #1, #2, #5)
  - [x] 1.1 Dans `mapping/light.py`, remplacer le `return MappingResult(confidence="ambiguous")` immédiat (L110-122) par la logique de déduplication spécifiée
  - [x] 1.2 Comparer `cmd_existing.sub_type` vs `cmd_new.sub_type`. Si différents → sélectionner selon la table de préférence domaine light (`LIGHT_STATE` → `binary`, `LIGHT_BRIGHTNESS` → `numeric`). Si identiques → conserver le retour `ambiguous` actuel
  - [x] 1.3 En cas de résolution : stocker le gagnant dans `light_cmds[generic_type]`, logger au niveau `info`, accumuler les métadonnées dedup pour injection dans `reason_details` du MappingResult final
  - [x] 1.4 Plafonner la confiance globale à `"probable"` si au moins une déduplication a eu lieu (injecter `"probable"` dans `_min_confidence`)
- [x] Task 2 — Appliquer la même logique dans CoverMapper (AC: #3, #4)
  - [x] 2.1 Dans `mapping/cover.py`, même remplacement du retour immédiat (L96-108)
  - [x] 2.2 Table de préférence domaine cover : `FLAP_STATE` → préférer `binary`
- [x] Task 3 — Tests unitaires dans `tests/unit/` (AC: #6)
  - [x] 3.1 `tests/unit/test_light_mapper.py` : doublon LIGHT_STATE (binary+numeric) → `confidence="probable"`, `reason_details["deduplicated"]=True`
  - [x] 3.2 `tests/unit/test_light_mapper.py` : doublon LIGHT_STATE (numeric+numeric) → `confidence="ambiguous"`, `reason_code="duplicate_generic_types"`
  - [x] 3.3 `tests/unit/test_cover_mapper.py` : doublon FLAP_STATE (binary+numeric) → `confidence="probable"`, `reason_details["deduplicated"]=True`
  - [x] 3.4 `tests/unit/test_light_mapper.py` : cas nominal sans doublon → `confidence="sure"` (pas de régression)
  - [x] 3.5 `tests/unit/test_cover_mapper.py` : cas nominal sans doublon → pas de régression
- [ ] Task 4 — Validation terrain minimale (manuelle, post-déploiement box réelle)
  - [ ] 4.1 eq_id=510 (buanderie plafonnier) : vérifié publié dans HA avec confidence=probable
  - [ ] 4.2 Un cas avec doublon même sub_type (si observable) : reste non publié (ambiguous via couche publication)
  - [ ] 4.3 Modale diagnostic : les 5 sections restent cohérentes pour un équipement dédupliqué (pas de JSON brut, pas de reason_code inconnu)

## Dev Notes

### Fichiers à modifier

| Fichier | Modification | Lignes actuelles |
|---------|-------------|-----------------|
| `resources/daemon/mapping/light.py` | Remplacer retour immédiat ambiguous par logique de déduplication | L102-122 |
| `resources/daemon/mapping/cover.py` | Même remplacement | L88-108 |
| `tests/unit/test_light_mapper.py` | 2 nouveaux tests (résolu + non résolu) + 1 non-régression | existant |
| `tests/unit/test_cover_mapper.py` | 1 nouveau test (résolu) + 1 non-régression | existant |

**Fichiers non touchés** : `switch.py` (exclu), `models/mapping.py` (pas de nouveau champ), `models/topology.py` (pas de nouveau champ), `transport/http_server.py` (pas de modification `_CLOSED_REASON_MAP` — le reason_code standard du mapper est déjà géré).

### Modèle de données — rappel

```python
# models/topology.py:73-83
@dataclass
class JeedomCmd:
    id: int
    name: str
    generic_type: Optional[str] = None
    type: str = "info"           # "info" | "action"
    sub_type: str = "string"     # "binary" | "numeric" | "string" | "slider" | "color" | "other"
    # ... (current_value, unit, is_visible, is_historized)
    # PAS DE CHAMP 'order'

# models/mapping.py:56-85
@dataclass
class MappingResult:
    commands: Dict[str, JeedomCmd]  # generic_type → JeedomCmd (une seule cmd par slot)
    reason_details: Optional[Dict[str, object]] = None  # enrichi avec métadonnées dedup
    # ... (ha_entity_type, confidence, reason_code, capabilities, etc.)
```

### Comportement de déduplication — résumé visuel

```
Boucle collecte commandes :
  cmd.generic_type déjà dans dict ?
    NON → stocker normalement
    OUI → DEDUP :
      sub_type différents ? → sélectionner selon règle domaine, continuer
      sub_type identiques ? → return ambiguous (comportement actuel)
```

### Intégration dans le flux mapper

La déduplication s'insère **dans la boucle de collecte** (avant les phases de détection de capacités). Le gagnant remplace le perdant dans `light_cmds[generic_type]`. Les phases capability (on/off, brightness, etc.) s'exécutent ensuite normalement sur le dict dédupliqué.

La confiance globale du MappingResult final est plafonnée à `probable` si au moins une déduplication a eu lieu. Mécanisme : injecter `"probable"` dans le calcul `_min_confidence()` existant.

### Traçabilité — décisions figées

**Pas de nouveau `reason_code`.** Le mapper dédupliqué produit un reason_code standard (ex: `light_on_off_brightness`). La couche publication (`decide_publication`) et la couche diagnostic (`_CLOSED_REASON_MAP`) ne nécessitent aucune modification.

| Couche | Contenu dedup | Détail |
|--------|--------------|--------|
| `MappingResult.reason_details` | `{"deduplicated": true, "duplicate_type": "LIGHT_STATE", "kept_cmd_id": 4655, "discarded_cmd_id": 4658, "criterion": "sub_type"}` | Seul vecteur de traçabilité dans le résultat structuré |
| Log daemon `[MAPPING]` | niveau `info` : "eq_id=510: deduplicated LIGHT_STATE (kept cmd 4655 sub_type=binary, discarded cmd 4658 sub_type=numeric)" | Remplace le `warning` actuel pour les cas résolus |
| `MappingResult.reason_code` | Inchangé : code standard des capacités (`light_on_off_brightness`, etc.) | Pas de code spécifique dedup |
| `MappingResult.confidence` | Plafonnée à `"probable"` | Via injection dans `_min_confidence` |
| `_CLOSED_REASON_MAP` | **Pas de modification** | Le reason_code standard est déjà normalisé |
| UI diagnostic | **Pas de modification JS** | `reason_details` visible dans section "Logique de décision" si non vide |

### References

- [Source: resources/daemon/mapping/light.py#L100-L122] — boucle collecte + retour ambiguous actuel
- [Source: resources/daemon/mapping/light.py#L238-L280] — phases capability + reason_code standard + `_min_confidence`
- [Source: resources/daemon/mapping/light.py#L282-L303] — `decide_publication` : `ambiguous` → `ambiguous_skipped` (couche publication, pas mapper)
- [Source: resources/daemon/mapping/cover.py#L86-L108] — même pattern dedup
- [Source: resources/daemon/mapping/switch.py#L95-L98] — silent overwrite (pas de guard, exclu du scope)
- [Source: resources/daemon/models/topology.py#L73-L83] — JeedomCmd (pas de champ order)
- [Source: resources/daemon/models/mapping.py#L56-L85] — MappingResult.commands Dict[str, JeedomCmd]
- [Source: tests/unit/test_light_mapper.py] — tests mapper light existants
- [Source: tests/unit/test_cover_mapper.py] — tests mapper cover existants

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Completion Notes List

- Task 1 (light.py) : ajout de `_LIGHT_DEDUP_PREFERENCE` + logique de déduplication dans la boucle de collecte. Cas résolu : log info, métadonnées accumulées dans `_dedup_events`. Cas non résolu (même sub_type ou pas de règle) : retour ambiguous conservatif inchangé. Floor de confiance `"probable"` via `_min_confidence` si `_dedup_events` non vide. Injection dans `reason_details` via `reason_details.update(_dedup_events[-1])`.
- Task 2 (cover.py) : même pattern. `_COVER_DEDUP_PREFERENCE` = `{"FLAP_STATE": "binary"}`. Logique identique.
- Task 3 (tests) : 7 tests ajoutés (4 dans `test_light_mapper.py`, 3 dans `test_cover_mapper.py`) + assertions `reason_code` standard renforcées. Tous passent (58/58 ciblés, 296/296 suite complète, 0 régression).
- Task 4 : validation terrain (manuelle, post-déploiement) hors scope des tests automatisés — reste à faire sur box réelle.

### File List

- resources/daemon/mapping/light.py
- resources/daemon/mapping/cover.py
- tests/unit/test_light_mapper.py
- tests/unit/test_cover_mapper.py
- _bmad-output/implementation-artifacts/2-6-deduplication-commandes-generic-type-dupliquees.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

### Change Log

- 2026-03-18 : implémentation Story 2.6 — déduplication des commandes à generic_type dupliqué dans LightMapper et CoverMapper. Tables de préférence par domaine, floor de confiance `"probable"`, traçabilité via `reason_details` et logs `[MAPPING]` niveau info.
- 2026-03-18 : correctif condition de résolution — ajout du guard `(existing.sub_type == preferred or cmd.sub_type == preferred)` pour ne résoudre que si exactement un candidat correspond au rôle attendu. Les cas où aucun sub_type ne correspond retournent désormais `ambiguous` conservatif. 2 tests supplémentaires ajoutés (un par domaine).
