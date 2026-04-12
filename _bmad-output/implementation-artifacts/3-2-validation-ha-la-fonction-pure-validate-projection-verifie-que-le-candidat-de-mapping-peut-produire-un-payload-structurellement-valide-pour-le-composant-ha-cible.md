# Story 3.2 : Validation HA — la fonction pure `validate_projection()` vérifie que le candidat de mapping peut produire un payload structurellement valide pour le composant HA cible

Status: done

> **Code review 2026-04-12** — APPROVE WITH MINOR FIXES (fixes soldés).
> M1 (fallback reason_code) corrigé, R1 (test intégrité registre) ajouté, M2 (déviation type annotation) documenté.
> 357/357 tests PASS, 0 régression. Gate terrain : **N/A** (backend pur).

## Story

En tant qu'utilisateur,
je veux que le système vérifie, avant toute publication, que le candidat de mapping d'un équipement satisfait les contraintes structurelles du composant HA cible,
afin de voir clairement quand un équipement a été compris par le moteur mais ne peut pas être projeté parce que la projection HA serait structurellement invalide — et non parce que le mapping a échoué.

## Acceptance Criteria

1. **Given** un équipement mappé comme `light` avec `has_command: true` (commandes ON/OFF présentes)
   **When** `validate_projection("light", capabilities)` est appelée
   **Then** elle retourne `ProjectionValidity(is_valid=True)`
   **And** le sous-bloc `projection_validity` dans le `MappingResult` est rempli avec `is_valid: True`

2. **Given** un équipement mappé comme `light` sans commande action (`has_command: false`)
   **When** `validate_projection("light", capabilities)` est appelée
   **Then** elle retourne `ProjectionValidity(is_valid=False, reason_code="ha_missing_command_topic", missing_capabilities=["has_command"])`
   **And** aucune publication ne peut suivre (NFR2)

3. **Given** un équipement mappé comme `cover` sans commande action (cover read-only valide côté HA per architecture)
   **When** `validate_projection("cover", capabilities)` est appelée
   **Then** elle retourne `ProjectionValidity(is_valid=True)` — le cover en lecture seule est structurellement valide

4. **Given** un équipement mappé vers un type de composant absent de `HA_COMPONENT_REGISTRY`
   **When** `validate_projection(type_inconnu, capabilities)` est appelée
   **Then** elle retourne `ProjectionValidity(is_valid=False, reason_code="ha_component_unknown")`

5. **Given** la suite de tests de l'étape 3
   **When** les tests s'exécutent en isolation (sans runtime HTTP, sans broker, sans box Jeedom)
   **Then** il existe au moins un cas nominal (projection valide) et un cas d'échec (projection invalide avec reason_code spécifique) pour chaque type de composant ouvert (NFR9)

## Tasks / Subtasks

- [x] Task 1 — Compléter `resources/daemon/validation/ha_component_registry.py` avec la fonction pure `validate_projection()` (AC: #1, #2, #3, #4)
  - [x] Ajouter uniquement les imports nécessaires depuis `models.mapping` (`MappingCapabilities`, `ProjectionValidity`) ; ne rien importer depuis `mapping/`, `discovery/`, `transport/`
  - [x] Implémenter `validate_projection(ha_entity_type: str, capabilities: MappingCapabilities) -> ProjectionValidity` dans **le même fichier** que le registre créé en Story 3.1
  - [x] Ajouter un helper privé déterministe qui résout les capabilities abstraites du registre (`has_command`, `has_state`, `has_options`) vers les champs concrets disponibles sur les objets de capabilities actuels
  - [x] Renvoyer `ProjectionValidity(is_valid=False, reason_code="ha_component_unknown", missing_fields=[], missing_capabilities=[])` si `ha_entity_type` n'existe pas dans `HA_COMPONENT_REGISTRY`
  - [x] Renseigner `missing_capabilities` et `missing_fields` dans un ordre stable, sans utiliser d'ensemble non ordonné
  - [x] Ne jamais retourner `is_valid=None` depuis `validate_projection()` : `None` reste réservé au statut `skipped` injecté plus tard par l'orchestrateur quand l'étape 3 n'est pas exécutée
  - [x] Ne pas consulter `PRODUCT_SCOPE` ici : la gouvernance d'ouverture reste une responsabilité distincte (Story 3.3 / étape 4)

- [x] Task 2 — Créer les tests unitaires dédiés à l'étape 3 dans `resources/daemon/tests/unit/test_step3_validate_projection.py` (AC: #1, #2, #3, #4, #5)
  - [x] **2.1 — Helpers locaux, sans `conftest.py`**
    - [x] Construire de petits helpers pour instancier `LightCapabilities`, `CoverCapabilities`, `SwitchCapabilities` et, si nécessaire, un double minimal pour une capability future (`has_options`)
  - [x] **2.2 — Cas nominal light** (AC #1)
    - [x] `test_validate_projection_light_with_command_is_valid`
    - [x] `LightCapabilities(has_on_off=True)` -> `is_valid is True`, `reason_code is None`, listes vides
    - [x] Affecter explicitement le résultat à `MappingResult.projection_validity` pour démontrer que le sous-bloc étape 3 se remplit sans modifier le sous-bloc mapping
  - [x] **2.3 — Cas d'échec light sans commande** (AC #2)
    - [x] `test_validate_projection_light_without_command_is_invalid`
    - [x] `LightCapabilities(has_on_off=False)` -> `reason_code == "ha_missing_command_topic"`, `missing_capabilities == ["has_command"]`, `missing_fields == ["command_topic"]`
  - [x] **2.4 — Cas nominal cover read-only** (AC #3)
    - [x] `test_validate_projection_cover_without_command_is_valid`
    - [x] `CoverCapabilities()` ou équivalent sans commande action -> `is_valid is True`
    - [x] Documenter dans le test que `cover` n'exige pas `command_topic` au stade validation
  - [x] **2.5 — Cas nominal switch** (AC #5)
    - [x] `test_validate_projection_switch_with_on_off_is_valid`
    - [x] `SwitchCapabilities(has_on_off=True)` -> `is_valid is True`
  - [x] **2.6 — Cas d'échec switch sans commande** (AC #5)
    - [x] `test_validate_projection_switch_without_command_is_invalid`
    - [x] `SwitchCapabilities(has_on_off=False, has_state=True)` -> `reason_code == "ha_missing_command_topic"`
  - [x] **2.7 — Cas d'échec type inconnu** (AC #4)
    - [x] `test_validate_projection_unknown_component_is_invalid`
    - [x] `validate_projection("unknown_component", LightCapabilities(...))` -> `is_valid is False`, `reason_code == "ha_component_unknown"`
  - [x] **2.8 — Préparer les codes classe 2 futurs sans ouvrir prématurément le scope** (AR8)
    - [x] Ajouter un test `sensor`/`binary_sensor` qui exerce `ha_missing_state_topic` via une capability `has_state=False`
    - [x] Ajouter un test `select` qui exerce `ha_missing_required_option` via un double minimal `has_options=False`
    - [x] Documenter dans les tests que ces composants sont **connus mais non ouverts** dans `PRODUCT_SCOPE` et que la validation structurelle est distincte de la gouvernance d'ouverture
  - [x] **2.9 — Test de pureté minimale** (AR7)
    - [x] Vérifier que l'objet `capabilities` passé à `validate_projection()` n'est pas muté par la fonction

- [x] Task 3 — Vérifier la non-régression locale du module validation (AC: #5)
  - [x] Depuis `resources/daemon/`, exécuter `python3 -m pytest tests/unit/test_ha_component_registry.py tests/unit/test_step3_validate_projection.py`
  - [x] Puis exécuter `python3 -m pytest tests/`
  - [x] Confirmer `0 failure`, `0 error`, et noter le total obtenu dans `Debug Log References`

## Dev Notes

### Contexte dans le pipeline

Story 3.2 est la **première story de code de production** de `pe-epic-3`. Elle s'appuie directement sur la fondation posée par Story 3.1 :

- Story 3.1 a créé `resources/daemon/validation/ha_component_registry.py` avec le registre statique et `PRODUCT_SCOPE`
- Story 3.2 ajoute la logique pure `validate_projection()` dans ce même module
- Story 3.3 utilisera ensuite cette fonction pour démontrer l'ouverture gouvernée de nouveaux composants
- Story 4.1 consommera plus tard `projection_validity.is_valid` comme fait établi dans la décision de publication
- Story 5.1 branchera l'étape 3 dans l'orchestration complète du pipeline

### Frontière de scope a respecter

Cette story **ne doit pas** anticiper les stories suivantes :

- **Ne pas modifier** `transport/http_server.py` : l'insertion runtime de `validate_projection()` dans le flux complet appartient à Story 5.1
- **Ne pas modifier** `models/cause_mapping.py` : la traduction 4D des nouveaux `reason_code` est portée par l'épic 4 / 6
- **Ne pas modifier** les mappers (`mapping/light.py`, `mapping/cover.py`, `mapping/switch.py`) : l'étape 2 produit déjà le candidat, l'étape 3 le valide
- **Ne pas ouvrir** de nouveau composant dans `PRODUCT_SCOPE` : l'ouverture gouvernée est Story 3.3

Le livrable attendu ici est donc : **fonction pure + tests d'isolation**.

### Contrat canonique de `validate_projection()`

Le contrat vient de l'architecture du moteur de projection :

```python
def validate_projection(
    ha_entity_type: str,
    capabilities: MappingCapabilities,
) -> ProjectionValidity:
    """
    Vérifie que le mapping candidat peut produire un payload
    HA structurellement valide pour le composant cible.
    Fonction pure - aucun effet de bord.
    """
```

Contraintes importantes :

- `validate_projection()` ne sérialise aucun payload
- `validate_projection()` ne log pas et ne dépend d'aucun état global
- `validate_projection()` ne décide pas `should_publish`
- `validate_projection()` ne remplit pas le diagnostic 4D
- `validate_projection()` retourne toujours un `ProjectionValidity` complet

### Interpretation correcte du registre HA

Le registre contient deux niveaux d'information :

- `required_capabilities` : contraintes que l'etape 3 peut verifier directement a partir des `MappingCapabilities`
- `required_fields` : trace des champs Home Assistant attendus pour la projection finale

**Point critique pour éviter un faux design :** l'étape 3 ne valide pas un payload JSON complet. Elle valide uniquement que les capabilities détectées permettent **de produire** les champs requis plus tard. En pratique :

- `platform` et `availability` sont fournis par la couche de publication et **ne doivent pas** faire échouer `validate_projection()`
- `command_topic`, `state_topic`, `options` peuvent être représentés comme conséquences de capabilities manquantes (`has_command`, `has_state`, `has_options`)
- `cover` read-only reste valide, car son entrée de registre n'exige aucune capability de commande

### Table de correspondance recommandee

La story 3.1 a laissé une note explicite : les capabilities abstraites du registre **ne correspondent pas 1:1** aux attributs concrets des dataclasses actuelles.

| Capability abstraite | Resolution concrete recommandee |
| --- | --- |
| `has_command` | `LightCapabilities.has_on_off` / `CoverCapabilities.has_open_close` / `SwitchCapabilities.has_on_off` |
| `has_state` | attribut `has_state` si present |
| `has_options` | attribut `has_options` si present ; sinon `False` |

Recommendation implementation :

- utiliser `isinstance(...)` pour les dataclasses actuelles afin d'éviter les collisions sémantiques
- garder un fallback `getattr(capabilities, "...", False)` pour preparer les composants connus non encore mappes
- conserver un ordre de priorite stable pour le `reason_code` retourne si plusieurs capabilities sont manquantes

Priorite recommandee pour le `reason_code` :

1. `ha_missing_required_option`
2. `ha_missing_state_topic`
3. `ha_missing_command_topic`

Cette priorite evite de masquer un besoin specifique (`options`) derriere un manque plus generique.

### Couverture de tests attendue

La suite de tests de cette story doit couvrir :

- le cas nominal `light`
- le cas d'échec `light` sans commande
- le cas nominal `cover` read-only
- le cas nominal `switch`
- le cas d'échec `switch` sans commande
- le type inconnu
- au moins un cas exercant `ha_missing_state_topic`
- au moins un cas exercant `ha_missing_required_option`

Important :

- **Ne pas inventer de faux cas d'échec pour `cover`** juste pour "cocher NFR9"
- la preuve architecturale et documentaire est au contraire que `cover` read-only est valide
- l'échec requis pour l'étape 3 est bien couvert par les cas `light`, `switch`, `sensor/select` et `unknown_component`

### Intelligence de la story precedente (3.1)

Apports utiles de Story 3.1 a reprendre sans les reouvrir :

- le package `validation/` existe deja ; ne pas creer un second module parallele
- le registre statique et `PRODUCT_SCOPE` sont deja corrects et testes
- le test AST `test_module_no_forbidden_imports` protege la separation physique ; l'implementation 3.2 doit continuer a le faire passer
- la note "cover = valide avec `required_capabilities: []`" est deja documentee : il faut la respecter, pas la contourner
- `models/cause_mapping.py` a ete explicitement laisse hors scope pour l'epic 3 amont

### Git intelligence recente

Les commits les plus proches montrent un pattern stable a reproduire :

- `a90a730 feat(pe-3.1): add static HA component registry (#81)` : la story precedente a touche uniquement le module `validation/`, son test unitaire dedie, l'artefact de story et `sprint-status.yaml`
- `598b8ca test(pe-epic-2): story 2.2 — echec et ambiguite de mapping (#80)` : une story pipeline isolee cree un **fichier de test dedie par etape**
- `cb6b6dd test(pe-epic-2): story 2.1 — candidat mapping HA annote avec niveau de confiance (#79)` : helpers locaux, pas de `conftest.py`, et assertions de contrat tres explicites

Conclusion pratique :

- privilegier **un seul nouveau fichier de test dedie a l'etape 3**
- garder des helpers locaux
- eviter les changements transverses disperses

### Informations techniques recentes a garder en tete

Verification web effectuee le 2026-04-12 sur la documentation officielle Home Assistant :

- `light` : `command_topic` est toujours requis ; `state_topic` reste optionnel
- `switch` : `command_topic` est toujours requis ; `state_topic` reste optionnel
- `cover` : `command_topic` est documente comme optionnel, et le composant peut fonctionner en mode optimiste si `state_topic` / `position_topic` ne sont pas definis

Cela confirme que la regle architecturale "cover read-only valide" est toujours alignee avec la doc officielle actuelle.

### Dev Agent Guardrails

- Implementer `validate_projection()` **dans** `resources/daemon/validation/ha_component_registry.py`, pas dans un nouveau module
- N'importer que depuis `models.mapping` si un import est necessaire
- Ne pas coder en dur un mini-registre parallele dans les tests ou dans la fonction
- Ne pas utiliser `PRODUCT_SCOPE` pour refuser un composant ici
- Ne pas toucher `transport/http_server.py`
- Ne pas toucher `models/cause_mapping.py`
- Ne pas ajouter de loggers, de side effects, ni de dependance IO dans `validate_projection()`
- Ne pas convertir la fonction en validation de payload JSON complet : l'etape 3 travaille sur les capabilities, pas sur la serialisation finale
- `ProjectionValidity.is_valid=None` reste un statut d'orchestration amont/aval, pas un resultat de validation executee
- Garder les listes `missing_fields` / `missing_capabilities` stables et deterministes

### Project Structure Notes

**Fichiers a modifier ou creer pour cette story :**

- `resources/daemon/validation/ha_component_registry.py` — ajout de `validate_projection()`
- `resources/daemon/tests/unit/test_step3_validate_projection.py` — nouveau corpus unitaire de l'etape 3
- `_bmad-output/implementation-artifacts/3-2-validation-ha-la-fonction-pure-validate-projection-verifie-que-le-candidat-de-mapping-peut-produire-un-payload-structurellement-valide-pour-le-composant-ha-cible.md`

**Fichiers explicitement hors scope :**

- `resources/daemon/models/cause_mapping.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/mapping/light.py`
- `resources/daemon/mapping/cover.py`
- `resources/daemon/mapping/switch.py`
- `resources/daemon/discovery/publisher.py`

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 3.2] — user story, AC, AR7, AR8, FR16-FR20
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §D2, §D3, §D4] — module `validation/`, registre statique, signature et contrat de `validate_projection()`
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §P2, §P3, §P4, §P6] — isolation des sous-blocs, nommage des `reason_code`, accès centralisé au registre, distinction entre champs HA et abstractions internes
- [Source: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-10.md` §Point 4 et §5.3] — pas de nouvel artefact UX requis ; l'étape 3 reste backend/diagnostic additif
- [Source: `_bmad-output/project-context.md` §Règles Python, §Règles de Test] — fonction pure Python, tests pytest isolés, pas de dépendance runtime
- [Source: `_bmad-output/implementation-artifacts/3-1-registre-ha-le-module-validation-definit-les-composants-connus-avec-leurs-contraintes-en-3-etats-distincts.md` §Abstraction des capabilities, §Dev Agent Guardrails] — correspondance capabilities abstraites -> champs concrets, scope laissé volontairement à Story 3.2
- [Source: `resources/daemon/models/mapping.py`] — `MappingCapabilities`, `ProjectionValidity`, `MappingResult`
- [Source: `resources/daemon/tests/unit/test_pipeline_contract.py`] — contrat structurel déjà couvert, à ne pas dupliquer inutilement
- [Source: `resources/daemon/tests/unit/test_step2_mapping_candidat.py`] — pattern de test par étape, helpers locaux, isolation
- [Home Assistant MQTT Light](https://www.home-assistant.io/integrations/light.mqtt) — `command_topic` requis pour `light`, `state_topic` optionnel
- [Home Assistant MQTT Switch](https://www.home-assistant.io/integrations/switch.mqtt/) — `command_topic` requis pour `switch`, `state_topic` optionnel
- [Home Assistant MQTT Cover](https://www.home-assistant.io/integrations/cover.mqtt/) — `command_topic` optionnel pour `cover`, cohérent avec le mode read-only/optimistic

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Task 1 : `validate_projection()` + `_resolve_capability()` + `_CAPABILITY_TO_REASON` + `_REASON_PRIORITY` implémentés dans `validation/ha_component_registry.py`. Import `from models.mapping import LightCapabilities, CoverCapabilities, SwitchCapabilities, ProjectionValidity` — root `models` non interdit par AR3. Test AST `test_module_no_forbidden_imports` PASS.
- Task 2 : 11 tests créés dans `test_step3_validate_projection.py` — helpers locaux (`_light`, `_cover`, `_switch`, `_SensorLikeCapabilities`, `_SelectLikeCapabilities`), isolation totale, pas de conftest. 11/11 PASS.
- Task 3 : `pytest tests/unit/test_ha_component_registry.py tests/unit/test_step3_validate_projection.py` → 19/19 PASS. Suite complète `pytest tests/` → 356/356 PASS, 0 échec, 0 erreur.
- Code review fix M1 : fallback `reason_code` remplacé — retourne désormais un vrai code métier via `_CAPABILITY_TO_REASON` au lieu du nom de capability brut. Test d'intégrité `test_all_registry_capabilities_have_reason_mapping` ajouté dans `test_ha_component_registry.py`.

### Completion Notes List

- `validate_projection()` implémentée dans `validation/ha_component_registry.py` en tant que fonction pure sans effet de bord.
- Helper privé `_resolve_capability()` résout `has_command` via `isinstance()` sur les 3 dataclasses connues, avec fallback `getattr()` pour les types futurs.
- Priorité déterministe du `reason_code` : `ha_missing_required_option` > `ha_missing_state_topic` > `ha_missing_command_topic`.
- `cover` read-only validé structurellement conforme (`required_capabilities: []` dans registre 3.1).
- `sensor`/`select` (connus non ouverts) exercés via doubles minimaux — validation structurelle distincte de la gouvernance d'ouverture (Story 3.3).
- 0 modification hors scope (transport, mappers, cause_mapping, PRODUCT_SCOPE).
- 345 tests précédents + 11 nouveaux = 356 tests — 0 régression.
- **M2 — déviation documentée** : `capabilities: object` au lieu de `MappingCapabilities` (D4). Choix pragmatique : `MappingCapabilities = Union[Light, Cover, Switch]` n'accepte pas les doubles de test pour sensor/select (connus non ouverts). Architecture §Points ouverts #1 reconnaît le type comme à définir. Pas de refacto ici — le typage sera aligné quand les dataclasses sensor/select seront formalisées.

### File List

- `resources/daemon/validation/ha_component_registry.py` (modifié)
- `resources/daemon/tests/unit/test_step3_validate_projection.py` (créé)
- `resources/daemon/tests/unit/test_ha_component_registry.py` (modifié — ajout test d'intégrité review)
- `_bmad-output/implementation-artifacts/3-2-validation-ha-la-fonction-pure-validate-projection-verifie-que-le-candidat-de-mapping-peut-produire-un-payload-structurellement-valide-pour-le-composant-ha-cible.md` (modifié)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié)
