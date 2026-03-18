# Story 2.6: Déduplication des commandes à generic_type dupliqué

Status: backlog

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

Côté Jeedom, un même eqLogic peut légitimement avoir deux commandes avec le même generic_type (ex : deux `LIGHT_STATE`, une pour l'état on/off, une pour le retour brightness). La cause est une configuration Jeedom typique sur certains modules (multi-canal, agrégation d'états).

Des critères de départage potentiels existent :
- `sub_type` de la commande (binary vs numeric)
- `type` de la commande (info vs action)
- Ordre canonique dans Jeedom (cmd.order, cmd.id)
- Cohérence avec les autres commandes du même domaine fonctionnel

### Impact utilisateur

Des équipements fonctionnels et correctement typés sont invisibles dans HA sans raison compréhensible pour l'utilisateur. La remédiation proposée par le diagnostic ("vérifier les types génériques") est trompeuse car les types sont corrects.

## Acceptance Criteria

1. **Given** un eqLogic lumière avec deux commandes portant le même generic_type (ex : 2× `LIGHT_STATE`) **When** le moteur de mapping traite cet équipement **Then** le mapper tente un arbitrage déterministe basé sur les métadonnées des commandes (sub_type, type info/action, cmd.order) avant de conclure à l'ambiguïté

2. **And** si l'arbitrage identifie un unique candidat cohérent pour chaque rôle fonctionnel, l'équipement est mappé normalement avec une confiance `probable` (pas `sure`, car la déduplication est heuristique)

3. **And** si aucun critère de départage ne permet un choix sûr, l'équipement reste classé `ambiguous_skipped` comme aujourd'hui (pas de régression sur les cas réellement ambigus)

4. **And** la logique de déduplication est factorisée ou dupliquée de manière cohérente dans tous les mappers concernés (`light.py`, `cover.py`, `switch.py` si applicable)

5. **And** le `reason_code` pour un mapping résolu par déduplication est distinct (ex : `deduplicated_probable`) pour traçabilité diagnostique

6. **And** les tests unitaires couvrent au minimum :
   - un cas avec doublon `LIGHT_STATE` (binary + numeric) → résolu par sub_type
   - un cas avec doublon `LIGHT_STATE` (même sub_type) → reste ambigu
   - un cas avec doublon `COVER_STATE` → même logique appliquée
   - un cas nominal sans doublon → pas de régression

## Hors scope

- **Story 4.2bis** : aucune modification — le diagnostic expose correctement la décision actuelle du moteur
- **docs/forensics/** : aucune modification
- **Politique de confiance** : pas de changement de politique d'exposition ; la déduplication produit au mieux `probable`, soumis à la politique existante
- **Détection root-cause Jeedom** : on ne corrige pas la source des doublons côté Jeedom, on les gère côté mapping

## Tasks / Subtasks

- [ ] Task 1 — Analyser les cas terrain de doublons generic_type (AC: #1)
  - [ ] 1.1 Identifier les critères de départage disponibles dans le modèle JeedomCmd
  - [ ] 1.2 Définir la stratégie de déduplication (matrice sub_type × type × ordre)
- [ ] Task 2 — Implémenter la déduplication dans LightMapper (AC: #1, #2, #3, #5)
  - [ ] 2.1 Extraire la logique de déduplication (fonction ou méthode réutilisable)
  - [ ] 2.2 Modifier `light.py` pour appliquer la déduplication avant le retour `ambiguous`
  - [ ] 2.3 Ajouter le reason_code `deduplicated_probable`
- [ ] Task 3 — Appliquer la même logique dans CoverMapper (AC: #4)
  - [ ] 3.1 Vérifier `cover.py` et appliquer la déduplication cohérente
  - [ ] 3.2 Vérifier `switch.py` et appliquer si applicable
- [ ] Task 4 — Tests unitaires (AC: #6)
  - [ ] 4.1 Test doublon LIGHT_STATE résolu par sub_type
  - [ ] 4.2 Test doublon LIGHT_STATE non résolvable → ambiguous
  - [ ] 4.3 Test doublon COVER_STATE résolu
  - [ ] 4.4 Test nominal sans doublon → pas de régression
- [ ] Task 5 — Validation intégration diagnostic (AC: #5)
  - [ ] 5.1 Vérifier que le diagnostic 4.2bis affiche correctement `deduplicated_probable`

## Dev Notes

### Fichiers concernés

- `resources/daemon/mapping/light.py` — logique de duplication ligne 102-122
- `resources/daemon/mapping/cover.py` — logique de duplication ligne 91-107
- `resources/daemon/mapping/switch.py` — vérifier si même pattern existe
- `resources/daemon/models/mapping.py` — potentiellement ajouter `deduplicated_probable` au vocabulaire
- `resources/daemon/transport/http_server.py` — `_CLOSED_REASON_MAP` doit mapper le nouveau reason_code
- `resources/daemon/tests/unit/` — nouveaux tests

### Patterns établis

- Le mapping utilise un dictionnaire `light_cmds: Dict[str, JeedomCmd]` indexé par generic_type
- La détection de doublon se fait inline avec un `if cmd.generic_type in light_cmds`
- Le retour immédiat `ambiguous` coupe court à toute analyse ultérieure des capacités
- La story 2.2 a établi le pattern capability-based (on_off + brightness cumulés) — la déduplication doit s'intégrer avant la phase de détection des capacités

### Taxonomie diagnostic (Story 4.2bis)

Le `_CLOSED_REASON_MAP` dans `http_server.py` normalise les reason_codes vers 8 codes fermés. Le nouveau `deduplicated_probable` devra être ajouté à cette map, probablement normalisé vers `"no_mapping"` ou un nouveau code selon la décision d'architecture.

### References

- [Source: resources/daemon/mapping/light.py#L102-L122] — logique de duplication actuelle
- [Source: resources/daemon/mapping/cover.py#L91-L107] — même pattern
- [Source: resources/daemon/transport/http_server.py#L855] — `_CLOSED_REASON_MAP`
- [Source: _bmad-output/implementation-artifacts/2-2-mapping-exposition-des-lumieres.md] — Story 2.2 (mapping lumières)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2] — Epic 2 Découverte & Mapping

## Dev Agent Record

### Agent Model Used

(à remplir lors de l'implémentation)

### Completion Notes List

### File List
