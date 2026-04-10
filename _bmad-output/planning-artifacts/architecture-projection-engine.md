---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7]
inputDocuments:
  - _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/implementation-artifacts/epic-5-retro-2026-04-09.md
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-post-mvp-refresh.md
  - _bmad-output/project-context.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx
workflowType: 'architecture'
project_name: 'jeedom2ha'
user_name: 'Alexandre'
date: '2026-04-09'
phase: 'post_v1_1'
scope: 'projection_engine_canonical_model'
motivation: 'AI-3 rétro Epic 5 — prérequis absolu avant prochain cycle'
lastStep: 7
status: 'complete'
---

# Architecture du moteur de projection — Post-V1.1

_Ce document formalise le modèle canonique du moteur de projection jeedom2ha comme contrat d'architecture testable, explicable et exploitable pour le cycle post-V1.1. Il répond à l'action item AI-3 de la rétrospective Epic 5 (2026-04-09)._

---

## Project Context Analysis

### Fondations acquises du cycle V1.1 (non rouvertes)

Le cycle V1.1 Pilotable a stabilisé un ensemble de fondations qui ne sont pas remises en question par cette architecture. Ce sont des acquis verrouillés :

- **Jeedom source de vérité métier.** Le daemon ne porte qu'un cache technique non autoritatif. Aucune table DB custom. Le fallback radical `purge cache + rescan complet` reste sain.
- **Contrat 4D conservé.** Le modèle utilisateur Périmètre / Statut / Écart / Cause est le contrat UI canonique. Le backend calcule les 4 dimensions, les compteurs et les causes. Le frontend affiche sans interpréter.
- **Contrat dual `reason_code` / `cause_code` conservé.** Les `reason_code` sont stables, hérités d'Epic 3, non exposés en UI. La traduction `reason_code → (cause_code, cause_label, cause_action)` est une fonction pure ajoutée en sortie du pipeline.
- **Façade d'opérations existante non rouverte.** L'endpoint `/action/execute` avec `intention + portée + sélection` est le contrat stable pour les opérations HA. Le signal `actions_ha` gouverne la disponibilité UI.
- **Résolution de périmètre `global → pièce → équipement`** avec précédence stricte `équipement > pièce > global`.
- **Gate terrain systématique** comme pratique de validation absorbée.
- **Séparation transport interne (HTTP local) / transport MQTT** conservée.

### Ce que le cycle V1.1 n'a pas externalisé (dette structurante)

La rétrospective Epic 5 identifie trois absences qui motivent ce document :

1. **Pas de modèle canonique du moteur de projection** (AI-3). La logique de décision — quoi projeter, pourquoi, avec quelles contraintes — vit dans le code mais n'est pas formalisée comme contrat testable et discutable indépendamment de l'implémentation.
2. **Pas de flux système opérationnel externalisé** (AI-1). La chaîne complète `Action utilisateur → Backend → Résultat → Stockage → API → JS → UI` n'a pas de représentation partageable.
3. **Pas de contraintes plateforme Jeedom documentées** (AI-2). Des comportements Jeedom implicites (auto-sync daemon, délais `event::changes`) interfèrent avec la validation terrain sans être recensés comme préconditions de test.

### Changement de paradigme post-V1.1

V1.1 = *comment exécuter des opérations HA de manière fiable et déterministe*.
Post-V1.1 = *comment décider quoi projeter dans Home Assistant, avec quelles contraintes de validité, et de manière explicable*.

Ce n'est pas une évolution de feature. C'est un changement de couche : d'un système d'actions à un **moteur de projection** — mapping des équipements, typage, règles de décision, validation de la sortie, overrides utilisateur, explicabilité.

Le fichier de référence HA (`docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx`) révèle un trou structurel dans le pipeline actuel : **il n'existe pas d'étape de validation de la projection côté HA**. Le publisher construit un payload et l'envoie. Si le payload est structurellement invalide au sens HA, l'entité est rejetée silencieusement et l'utilisateur voit une absence sans cause explicable.

### Pipeline cible du moteur de projection — 5 étapes canoniques

```
┌─────────────────────────────────────────────────────────────┐
│  1. ÉLIGIBILITÉ                                             │
│     Entrée : TopologySnapshot (eq + cmds + scope)           │
│     Sortie : EligibilityResult par eq                       │
│     Échecs : excluded_*, disabled, no_commands,             │
│              no_generic_type                                │
│     → Filtre les équipements avant toute logique métier     │
├─────────────────────────────────────────────────────────────┤
│  2. MAPPING CANDIDAT                                        │
│     Entrée : eq éligible + ses commandes + generic_types    │
│     Sortie : MappingCandidate (type HA candidat,            │
│              capabilities détectées, confiance, reason)      │
│     Échecs : no_mapping, ambiguous, name_heuristic,         │
│              color_only_unsupported, duplicate_generic_types │
│     → Produit une INTENTION de projection, pas un payload   │
├─────────────────────────────────────────────────────────────┤
│  3. VALIDATION DE PROJECTION HA                             │
│     Entrée : MappingCandidate + registre composants HA      │
│     Sortie : ProjectionValidity (valide/invalide,           │
│              champs manquants, contraintes violées)          │
│     Échecs : ha_missing_command_topic,                      │
│              ha_missing_state_topic,                         │
│              ha_missing_required_option                      │
│     → Vérifie que le candidat PEUT produire un payload      │
│       structurellement valide au sens HA                    │
├─────────────────────────────────────────────────────────────┤
│  4. DÉCISION DE PUBLICATION                                 │
│     Entrée : MappingCandidate validé + confidence_policy    │
│              + registre scope produit                        │
│     Sortie : PublicationDecision (should_publish, reason)    │
│     Échecs : low_confidence (policy filter),                │
│              ha_component_not_in_product_scope               │
│     → Applique la politique de confiance ET le scope        │
│       produit                                               │
├─────────────────────────────────────────────────────────────┤
│  5. PUBLICATION MQTT + DIAGNOSTIC                           │
│     Entrée : PublicationDecision validée                    │
│     Sortie : payload MQTT envoyé + état enregistré          │
│     Échecs : discovery_publish_failed,                      │
│              local_availability_publish_failed               │
│     → Exécution technique, résultat stocké, diagnostic      │
│       mis à jour                                            │
└─────────────────────────────────────────────────────────────┘
```

### Définition stricte des 4 classes d'échec

#### Classe 1 — Échec de mapping

**Définition :** Le moteur interne ne parvient pas à interpréter les commandes de l'équipement Jeedom pour en dériver un type d'entité HA candidat, ou produit un résultat dont la confiance est insuffisante pour avancer dans le pipeline.

**Frontière :** L'échec relève entièrement de l'interprétation des données Jeedom. Le moteur a accès aux commandes, aux generic_types, aux heuristiques de nom — et malgré cela, il ne peut pas produire de candidat utilisable.

**Exemple canonique :** Un eqLogic porte à la fois des commandes `LIGHT_ON` / `LIGHT_OFF` et des commandes `FLAP_UP` / `FLAP_DOWN`. Le mapping détecte des generic_types conflictuels et produit `confidence=ambiguous`, `reason_code=conflicting_generic_types`. Le pipeline s'arrête à l'étape 2.

#### Classe 2 — Invalidité structurelle HA

**Définition :** Le mapping a produit un candidat (type HA + capabilities), mais ce candidat ne satisfait pas les contraintes structurelles du composant HA cible. Le payload résultant serait rejeté ou ignoré par Home Assistant.

**Frontière :** L'échec ne relève pas de l'interprétation Jeedom (le mapping a réussi) mais des exigences du composant HA de destination. C'est une contrainte externe au moteur.

**Exemple canonique :** Un eqLogic est mappé comme `light` avec `confidence=sure`, mais il ne possède que `LIGHT_STATE` (info) sans aucune commande action. Le composant `light.mqtt` requiert `command_topic`. La validation HA produit `reason_code=ha_missing_command_topic`. Le pipeline s'arrête à l'étape 3.

#### Classe 3 — Hors scope produit

**Définition :** Le mapping a produit un candidat valide dont la projection HA serait structurellement correcte, mais le type d'entité HA cible n'est pas ouvert dans la version courante du produit.

**Frontière :** L'échec ne relève ni du mapping ni de la validité HA. Le moteur sait mapper l'équipement et la projection serait techniquement valide, mais le produit n'autorise pas encore ce domaine.

**Exemple canonique :** Un eqLogic thermostat est correctement mappé vers `climate.mqtt`, la validation HA confirme que le payload serait structurellement valide, mais `climate` n'est pas dans le registre de scope produit V1.x. Le pipeline produit `reason_code=ha_component_not_in_product_scope`. Le pipeline s'arrête à l'étape 4.

#### Classe 4 — Échec d'infrastructure

**Définition :** La décision de publication a été prise positivement (le mapping, la validité HA et le scope produit sont tous satisfaits), mais la publication effective vers Home Assistant échoue pour une raison technique (broker MQTT indisponible, timeout, erreur réseau).

**Frontière :** Tout le modèle décisionnel a abouti positivement. L'échec est purement technique et transitoire.

**Exemple canonique :** Un eqLogic lumière a été mappé, validé, autorisé par le scope produit, mais le broker MQTT est déconnecté. Le publish est déféré dans `pending_discovery_unpublish` et produit `reason_code=discovery_publish_failed`. Le pipeline s'arrête à l'étape 5.

### Invariant d'évaluation ordonnée et cause principale canonique

Le moteur évalue les étapes dans un **ordre strict et stable** : Éligibilité → Mapping → Validité HA → Scope produit → Publication.

Le premier échec rencontré dans cet ordre devient la **cause principale canonique** de l'équipement dans le diagnostic. C'est un contrat de lisibilité : l'utilisateur et le support voient une seule cause explicable par équipement, celle qui a effectivement bloqué le pipeline.

Cet ordre n'est pas une négation de toute insuffisance latente secondaire. Un équipement peut simultanément avoir un mapping ambigu ET un composant HA cible hors scope produit. Mais le pipeline s'arrête au mapping ambigu (étape 2) et c'est cette cause qui est retenue dans le diagnostic. Si le mapping est corrigé ultérieurement, le pipeline avancera et l'échec de scope produit deviendra alors visible.

Ce choix est délibéré : il produit un diagnostic progressif et actionnable plutôt qu'une liste exhaustive de problèmes simultanés.

### Registre des composants HA supportables

Il existe un **registre canonique des composants HA supportables** par le moteur. Ce registre :

- est **séparé de la logique de mapping** — le mapping produit des candidats, le registre détermine ce qui est validable et publiable ;
- est **versionné** — il évolue avec les cycles produit ;
- est **testable en isolation** — chaque entrée du registre définit les champs requis et les contraintes structurelles d'un composant HA ;
- est **librement implémentable sous forme de structure statique interne** — dict Python, dataclass, ou tout autre mécanisme. Le point architectural est la séparation de responsabilité, pas la forme technique.

Le registre porte deux niveaux d'information :

| Niveau | Contenu | Exemple |
|--------|---------|---------|
| **Composants connus** | Types d'entités HA dont le moteur connaît les contraintes structurelles | `light.mqtt`, `cover.mqtt`, `switch.mqtt`, `sensor.mqtt`, `binary_sensor.mqtt`, `button.mqtt`, `number.mqtt`, `select.mqtt`, `climate.mqtt` |
| **Composants ouverts (scope produit)** | Sous-ensemble des composants connus autorisés à la publication dans la version courante | V1.x : `["light", "cover", "switch"]` |

Un composant **connu mais non ouvert** produit `reason_code=ha_component_not_in_product_scope`. Un composant **inconnu** (absent du registre) produit `reason_code=ha_component_unknown` — le moteur ne sait pas valider sa projection.

Le fichier Excel HA (`docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx`) est la **source de vérité pour alimenter ce registre et ses tests**, pas une source de règles de mapping ni un engagement produit. L'existence d'un composant dans l'Excel ne crée aucune obligation de l'ouvrir dans le scope produit.

### Reason codes proposés — nouvelles classes d'échec

**Classe 2 — Validité structurelle HA (étape 3) :**

| `reason_code` | Signification | `cause_code` (UI) | `cause_label` |
|---|---|---|---|
| `ha_missing_command_topic` | Commande action absente pour remplir le `command_topic` requis | `ha_projection_incomplete` | Projection HA incomplète — commande requise absente |
| `ha_missing_state_topic` | Commande info absente pour remplir le `state_topic` requis | `ha_projection_incomplete` | Projection HA incomplète — état requis absent |
| `ha_missing_required_option` | Champ requis spécifique au composant manquant | `ha_projection_incomplete` | Projection HA incomplète — champ obligatoire manquant |
| `ha_component_unknown` | Composant HA absent du registre — le moteur ne sait pas valider | `ha_projection_incomplete` | Type d'entité HA inconnu du moteur |

**Classe 3 — Scope produit (étape 4) :**

| `reason_code` | Signification | `cause_code` (UI) | `cause_label` |
|---|---|---|---|
| `ha_component_not_in_product_scope` | Composant HA connu mais non ouvert par le scope produit | `not_in_product_scope` | Type d'entité non supporté dans cette version |

Note : `ha_component_not_in_product_scope` **clarifie** l'actuel `unsupported_generic_type` / `no_supported_generic_type` qui mélange deux concepts distincts — l'absence de mapping (classe 1) et la fermeture du scope produit (classe 3). Les anciens codes restent valides pour la rétrocompatibilité du pipeline existant ; le nouveau code s'ajoute pour la couche de décision formalisée.

### Frontière source de vérité Jeedom ↔ projection Home Assistant

```
      SOURCE DE VÉRITÉ                    PROJECTION
  ┌──────────────────┐            ┌──────────────────────┐
  │     JEEDOM        │            │   HOME ASSISTANT      │
  │                   │            │                       │
  │  eq + cmds +      │  Moteur   │   Entités MQTT        │
  │  generic_types +  │ ───────►  │   Discovery           │
  │  scope utilisat.  │ projection│   (payload validé)    │
  │                   │            │                       │
  │  Toujours lu,     │            │   Toujours écrit,     │
  │  jamais modifié   │            │   jamais lu comme     │
  │  par le moteur    │            │   source de vérité    │
  └──────────────────┘            └──────────────────────┘
         │                                    │
         │  Entrées canoniques :              │  Sorties canoniques :
         │  - TopologySnapshot                │  - Payload Discovery JSON
         │  - Scope utilisateur               │  - Availability topics
         │  - Configuration plugin            │  - State/Command topics
         │                                    │  - Diagnostic (4D + trace)
         │  Contraintes plateforme :          │
         │  - auto-sync daemon               │  Contraintes externes :
         │  - event::changes limité           │  - Champs requis par composant
         │  - délais de synchronisation       │  - Birth message HA
         │                                    │  - Retained messages broker
```

### Décisions verrouillées vs décisions encore ouvertes

#### Verrouillé dans ce modèle

Ces décisions sont actées et ne seront pas rouvertes dans l'artefact d'architecture final :

1. **Pipeline à 5 étapes** avec ordre d'évaluation stable (Éligibilité → Mapping → Validité HA → Scope produit → Publication).
2. **4 classes d'échec disjointes** avec cause principale canonique retenue par ordre de pipeline.
3. **Registre des composants HA** séparé de la logique de mapping, versionné, avec distinction composants connus / composants ouverts.
4. **La validation HA est une fonction pure** : `validate(MappingCandidate, HAComponentSpec) → ProjectionValidity`, testable en isolation.
5. **Le fichier Excel HA est un contrat externe de validation et de test**, pas une source de règles de mapping, pas un engagement produit.
6. **Les acquis V1.1 sont conservés** : Jeedom source de vérité, contrat 4D, contrat dual reason/cause, façade d'opérations, signal actions_ha, résolution de périmètre.

#### Encore ouvert — à décider dans les prochaines étapes architecturales

7. **Forme technique du registre composants HA** (dict, dataclass, fichier de config, code généré).
8. **Granularité de la validation HA** : validation champ par champ ou validation au niveau du composant entier.
9. **Impact sur la structure `MappingResult` existante** : extension ou nouveau type `MappingCandidate`.
10. **Stratégie de migration des reason_code existants** vers le nouveau modèle à 4 classes.
11. **Modélisation des overrides utilisateur** dans le pipeline (position exacte et interaction avec les étapes).
12. **Contraintes plateforme Jeedom** (AI-2) : forme du registre de contraintes et intégration dans les dev notes stories.
13. **Flux système opérationnel externalisé** (AI-1) : forme de l'artefact (Mermaid, JSON canonique, les deux).
14. **Extension du registre scope produit** pour Frontière B : quels composants ouvrir, dans quel ordre, avec quelles conditions.

#### Explicitement hors scope du cycle suivant

15. **Drill-down niveau commande** dans l'UI (Backlog Icebox — requiert un niveau 4 structurant).
16. **Alignement Homebridge** (Frontière D — les onglets HomeKit de l'Excel ne sont pas exploités).
17. **Réconciliation sophistiquée** ou détection automatique de doublons.
18. **Heuristiques opaques** pour gonfler artificiellement la couverture.
19. **Preview complète** de publication avant action (Frontière C — maturité produit avancée).

### Risques architecturaux identifiés

| Risque | Impact | Mitigation |
|---|---|---|
| Confusion mapping ↔ validité HA dans le diagnostic | Reason codes mélangés, utilisateur ne sait pas quoi corriger | Pipeline à 5 étapes, classes d'échec disjointes, cause principale canonique |
| Élargissement scope par glissement depuis l'Excel | Composants HA publiés sans engagement produit explicite | Registre scope produit versionné, séparé du registre composants connus |
| Validation HA couplée au runtime MQTT | Non testable en isolation | Fonction pure, tests générés depuis l'Excel |
| Régression contrat 4D existant | Cassure du diagnostic V1.1 fonctionnel | Nouveaux reason_code additifs, aucun code existant renommé ou supprimé |
| Effets plateforme Jeedom non documentés (AI-2) | Surprises en gate terrain, faux échecs | Contraintes documentées comme préconditions de test avant stories |
| Complexité de migration des reason_code existants | Double-codage temporaire ou incohérence | Stratégie de migration explicite à décider en étape architecture |

## Stack technologique (confirmation)

Stack inchangé. Le moteur de projection est une formalisation architecturale du code Python existant dans `resources/daemon/`. Il ne modifie ni le stack (PHP 8.x + Python 3.9+/asyncio + jQuery + MQTT), ni les dépendances (`jeedomdaemon`, `paho-mqtt`, `pytest`, Jest), ni la structure de fichiers du plugin.

## Décisions architecturales du moteur de projection

### Priorités

| Priorité | ID | Décision | Bloque |
|---|---|---|---|
| Critique | D1 | Extension MappingResult par sous-blocs bornés | Toute implémentation |
| Critique | D2 | Module `validation/` séparé | Structure du code |
| Critique | D3 | Registre statique composants HA | Validation HA |
| Critique | D4 | Fonction pure `validate_projection` | Tests du moteur |
| Important | D5 | Migration reason_code additive | Rétrocompatibilité diagnostic |
| Important | D6 | Overrides à l'éligibilité uniquement | Simplicité pipeline |
| Important | D7 | Insertion validation dans le sync handler | Flux opérationnel |
| Important | D8 | Diagnostic étendu avec `projection_validity` | Observabilité |

### D1 — MappingResult : sous-blocs bornés par étape

**Décision :** Le `MappingResult` reste l'objet de transport principal du pipeline. Chaque étape écrit dans un sous-bloc strictement borné — elle ne modifie pas les sous-blocs des autres étapes.

**Sous-blocs définis :**

| Sous-bloc | Écrit par | Contenu |
|---|---|---|
| `mapping` (existant) | Étape 2 — Mapping candidat | `ha_entity_type`, `confidence`, `reason_code`, `capabilities`, `commands` |
| `projection_validity` | Étape 3 — Validation HA | `is_valid`, `missing_fields`, `missing_capabilities`, `reason_code` |
| `publication_decision` | Étape 4 — Décision finale | `should_publish`, `reason`, `active_or_alive`, `discovery_published` |

**Invariant :** une étape ne court-circuite jamais la suivante. Même en cas d'invalidité HA (étape 3), le pipeline produit une `PublicationDecision` explicite avec `should_publish=False` et un `reason_code` cohérent hérité de l'étape qui a bloqué. Le diagnostic reçoit toujours un objet complet.

**Rationale :** évite un objet fourre-tout. Chaque étape a une surface d'écriture délimitée, testable en isolation. Le diagnostic peut lire chaque sous-bloc indépendamment pour construire la trace complète.

**Option écartée :** nouveau type `MappingCandidate` distinct du `MappingResult`. Doublerait les structures sans gain — le `MappingResult` est déjà le bon véhicule.

**Testable par :** `assert mapping_result.projection_validity is not None` pour tout eq passé par l'étape 3 ; `assert mapping_result.publication_decision.should_publish == False` pour un eq invalide côté HA.

### D2 — Module `validation/` séparé

**Décision :** La validation HA vit dans un nouveau module `resources/daemon/validation/ha_component_registry.py`, séparé physiquement du mapping (`mapping/`) et du publisher (`discovery/`).

**Contient :**
- Le registre statique `HA_COMPONENT_REGISTRY` (composants connus + contraintes)
- La liste `PRODUCT_SCOPE` (composants ouverts dans la version courante)
- La fonction `validate_projection(ha_entity_type, capabilities) → ProjectionValidity`

**Rationale :** Trois responsabilités, trois modules. Le mapping interprète Jeedom. La validation vérifie les contraintes HA. Le publisher sérialise et envoie. Aucun ne doit connaître les détails des autres.

**Option écartée :** intégrer dans `mapping/engine.py` ou `discovery/publisher.py` — viole la séparation des responsabilités.

**Testable par :** `from validation.ha_component_registry import validate_projection, HA_COMPONENT_REGISTRY` sans dépendance MQTT, Jeedom ou daemon.

### D3 — Registre statique des composants HA

**Décision :** Le registre est un dict Python statique dans `validation/ha_component_registry.py`.

```python
HA_COMPONENT_REGISTRY = {
    "light": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "cover": {
        "required_fields": ["platform", "availability"],
        "required_capabilities": [],  # cover read-only valide côté HA
    },
    "switch": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "sensor": {
        "required_fields": ["state_topic", "platform", "availability"],
        "required_capabilities": ["has_state"],
    },
    "binary_sensor": {
        "required_fields": ["state_topic", "platform", "availability"],
        "required_capabilities": ["has_state"],
    },
    # Composants connus mais non ouverts en V1.x :
    "button": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "number": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "select": {
        "required_fields": ["command_topic", "options", "platform", "availability"],
        "required_capabilities": ["has_command", "has_options"],
    },
    "climate": {
        "required_fields": ["availability"],
        "required_capabilities": [],
    },
}

PRODUCT_SCOPE = ["light", "cover", "switch"]  # V1.x — versionné par cycle produit
```

**Deux niveaux :** composant connu (dans le registre) vs composant ouvert (dans `PRODUCT_SCOPE`). Un composant connu mais non ouvert produit `ha_component_not_in_product_scope`. Un composant inconnu produit `ha_component_unknown`.

**Rationale :** structure statique = simple, testable, lisible. Le registre change rarement (à chaque cycle produit). L'Excel HA sert de source de vérité pour les tests d'exhaustivité, pas pour le runtime.

**Option écartée :** chargement dynamique depuis JSON ou code généré depuis l'Excel — complexité non justifiée.

### D4 — Fonction pure `validate_projection`

**Décision :** Signature et contrat de la validation HA.

```python
@dataclass
class ProjectionValidity:
    is_valid: bool
    reason_code: Optional[str]       # None si valide
    missing_fields: List[str]        # champs HA requis non satisfaits
    missing_capabilities: List[str]  # capabilities moteur absentes

def validate_projection(
    ha_entity_type: str,
    capabilities: MappingCapabilities,
) -> ProjectionValidity:
    """
    Vérifie que le mapping candidat peut produire un payload
    HA structurellement valide pour le composant cible.
    Fonction pure — aucun effet de bord.
    """
```

**Granularité :** validation au niveau composant avec rapport de champs. Pas de validation champ par champ du payload JSON (trop couplé au publisher).

**Testable par :**
- `validate_projection("light", caps_sans_commande).is_valid == False`
- `validate_projection("light", caps_avec_on_off).is_valid == True`
- `validate_projection("cover", caps_sans_commande).is_valid == True` (cover read-only valide)

### D5 — Migration reason_code : addition pure

**Décision :** Les reason_code existants (`no_mapping`, `ambiguous_skipped`, `no_supported_generic_type`, etc.) restent inchangés. Les nouveaux codes s'ajoutent. La table de traduction `cause_mapping.py` est étendue.

**Nouveaux reason_code :**

| Code | Classe | Signification |
|---|---|---|
| `ha_missing_command_topic` | Validité HA | Commande action absente pour le `command_topic` requis |
| `ha_missing_state_topic` | Validité HA | Commande info absente pour le `state_topic` requis |
| `ha_missing_required_option` | Validité HA | Champ requis spécifique manquant (ex: `options` pour select) |
| `ha_component_unknown` | Validité HA | Composant HA absent du registre |
| `ha_component_not_in_product_scope` | Scope produit | Composant connu mais non ouvert par le scope produit courant |

**Rétrocompatibilité :** L'ancien `no_supported_generic_type` continue de fonctionner pour les cas existants. Le nouveau `ha_component_not_in_product_scope` est utilisé quand le pipeline à 5 étapes distingue formellement mapping et scope.

**Testable par :** tous les tests existants passent sans modification après ajout des nouveaux codes.

### D6 — Overrides utilisateur : éligibilité uniquement

**Décision :** Les overrides utilisateur (inclusion/exclusion scope) restent à l'étape 1, comme aujourd'hui. Un eq exclu ne passe jamais dans le mapping.

**Point d'extension documenté (différé) :** un override de type "forcer la publication malgré confiance insuffisante" ou "forcer un type HA" pourrait intervenir entre les étapes 2 et 4 dans un cycle futur. Non engagé pour le prochain cycle.

**Testable par :** un eq exclu ne produit ni `MappingResult.mapping` ni `MappingResult.projection_validity` dans le diagnostic.

### D7 — Insertion dans le sync handler

**Décision :** Le handler `/action/sync` (`http_server.py`) intègre l'appel `validate_projection()` entre le mapping et `decide_publication()`.

Flux actuel :
```
assess_all → [éligible] map → decide_publication → publish
```

Flux cible :
```
assess_all → [éligible] map → validate_projection → decide_publication → publish
```

**Invariant critique :** même si `validate_projection` retourne `is_valid=False`, le pipeline continue jusqu'à produire une `PublicationDecision(should_publish=False, reason=ha_missing_command_topic)`. Le pipeline ne court-circuite jamais — il produit toujours un objet complet pour le diagnostic.

**Option écartée :** réécrire le sync handler en pipeline objet — sur-engineering pour un ajout d'une étape.

**Testable par :** un test d'intégration soumettant un eq sans commande action au sync produit `reason_code=ha_missing_command_topic` dans le diagnostic ET `publication_decision.should_publish == False`.

### D8 — Diagnostic étendu

**Décision :** Ajout de `projection_validity` dans la trace de décision par équipement.

```python
# Dans _build_traceability() — ajout au dict existant
"projection_validity": {
    "is_valid": True/False,
    "missing_fields": [...],
    "missing_capabilities": [...],
    "reason_code": "ha_missing_command_topic" or None,
}
```

Le contrat 4D existant n'est pas modifié. Les nouveaux `reason_code` de classe 2 alimentent le contrat 4D via `reason_code_to_cause()` dans `cause_mapping.py`, comme les codes existants.

**Testable par :** la réponse diagnostic d'un eq invalide côté HA contient `projection_validity.is_valid == False` ET `cause_code == "ha_projection_incomplete"`.

## Patterns d'implémentation du moteur de projection

### Patterns conservés

Les patterns de l'architecture MVP (§Implementation Patterns) et du `project-context.md` restent en vigueur : naming `snake_case` Python, IDs stables sur IDs Jeedom, enveloppe JSON standard, organisation par responsabilité métier, logs catégorisés, fallback conservatif, tests pytest.

### Patterns nouveaux

#### P1 — Traversée du pipeline et trace complète

**Règle :** Un équipement éligible traverse le pipeline de décision complet. Chaque étape produit un sous-bloc explicite dans le `MappingResult`, même si ses préconditions ne sont pas réunies.

**Préconditions et sous-blocs explicites :** Si une étape ne peut pas s'exécuter parce qu'une étape précédente a échoué, elle produit un sous-bloc avec un statut explicite plutôt qu'un trou implicite.

| Situation | Sous-bloc `projection_validity` | Sous-bloc `publication_decision` |
|---|---|---|
| Mapping réussi, validation réussie | `{is_valid: True, ...}` | `{should_publish: True/False, reason: ...}` |
| Mapping réussi, validation échouée | `{is_valid: False, reason_code: "ha_missing_...", ...}` | `{should_publish: False, reason: "ha_missing_..."}` |
| Mapping échoué | `{is_valid: None, reason_code: "skipped_no_mapping_candidate"}` | `{should_publish: False, reason: "no_mapping"}` |

**Invariant principal :** le diagnostic reçoit toujours une trace complète et explicite, sans trou implicite. Chaque sous-bloc est présent, avec un statut qui dit soit le résultat réel, soit la raison pour laquelle l'étape n'a pas pu s'exécuter.

```python
# BON — trace complète même sans mapping
if mapping.confidence == "unknown":
    validity = ProjectionValidity(
        is_valid=None,
        reason_code="skipped_no_mapping_candidate",
        missing_fields=[], missing_capabilities=[],
    )
else:
    validity = validate_projection(mapping.ha_entity_type, mapping.capabilities)

decision = decide_publication(mapping, validity, policy, scope)
# decision est toujours produit — le diagnostic est toujours complet

# INTERDIT — trou implicite
if mapping.confidence == "unknown":
    return  # ← projection_validity et publication_decision absents
```

#### P2 — Isolation des sous-blocs

**Règle :** Chaque étape du pipeline écrit exclusivement dans son sous-bloc. Elle lit les sous-blocs des étapes précédentes mais ne les modifie jamais.

| Étape | Lit | Écrit |
|---|---|---|
| Mapping (2) | TopologySnapshot, EligibilityResult | `mapping` |
| Validation HA (3) | `mapping.ha_entity_type`, `mapping.capabilities` | `projection_validity` |
| Décision (4) | `mapping.confidence`, `projection_validity.is_valid` | `publication_decision` |

**Anti-pattern :** un validateur qui modifie la confiance du mapping, ou une décision qui écrase le `reason_code` du mapping.

#### P3 — Nommage des reason_code

**Règle :** Les nouveaux `reason_code` suivent un préfixe par classe d'échec.

| Classe | Préfixe | Exemples |
|---|---|---|
| Mapping (étape 2) | *(convention existante)* | `no_mapping`, `ambiguous_skipped`, `duplicate_generic_types` |
| Validité HA (étape 3) | `ha_` | `ha_missing_command_topic`, `ha_missing_state_topic`, `ha_component_unknown` |
| Scope produit (étape 4) | `ha_component_` | `ha_component_not_in_product_scope` |
| Infrastructure (étape 5) | *(convention existante)* | `discovery_publish_failed`, `infra_unavailable` |
| Pipeline skip (transverse) | `skipped_` | `skipped_no_mapping_candidate` |

**Règle de non-collision :** un nouveau `reason_code` ne doit jamais être un sous-ensemble d'un code existant. Vérifier l'unicité avant ajout.

#### P4 — Accès au registre HA

**Règle :** Le registre `HA_COMPONENT_REGISTRY` et `PRODUCT_SCOPE` sont importés depuis `validation/ha_component_registry.py`. Aucun autre module ne doit coder en dur les contraintes HA.

```python
# BON
from validation.ha_component_registry import HA_COMPONENT_REGISTRY, PRODUCT_SCOPE

# INTERDIT — contrainte HA codée en dur dans le publisher
if ha_entity_type == "light" and "command_topic" not in payload:
    ...
```

**Exception :** le publisher (`discovery/publisher.py`) construit les payloads avec les clés concrètes (`command_topic`, `state_topic`). C'est de la sérialisation, pas de la validation. La validation a déjà eu lieu en amont.

#### P5 — Décision de publication : toujours un motif explicite

**Règle :** `decide_publication()` produit toujours un `reason` explicite, y compris dans le cas positif.

```python
PublicationDecision(should_publish=True, reason="sure")
PublicationDecision(should_publish=False, reason="ha_missing_command_topic")
PublicationDecision(should_publish=False, reason="ha_component_not_in_product_scope")
# INTERDIT
PublicationDecision(should_publish=False, reason=None)
```

#### P6 — Vérification du registre HA contre la spec Excel

**Règle :** Le registre interne `HA_COMPONENT_REGISTRY` et le fichier Excel HA (`docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx`) opèrent à **deux niveaux d'abstraction différents**. La vérification de cohérence doit respecter cette distinction.

**Niveau 1 — Spec HA (Excel) :** champs MQTT Discovery requis par composant, tels que documentés par Home Assistant. C'est une liste de clés JSON (`command_topic`, `state_topic`, `options`, `platform`, `availability > keys > topic`).

**Niveau 2 — Registre interne (code) :** traduction des contraintes HA en termes de **capabilities abstraites du moteur** (`has_command`, `has_state`, `has_options`). Cette traduction est un acte de conception — un `command_topic` requis dans la spec HA signifie que le moteur doit avoir détecté au moins une commande action, mais c'est le registre qui encode cette correspondance, pas un mapping mécanique 1:1.

**Stratégie de vérification en 3 couches :**

```python
# Couche 1 — Exhaustivité documentaire
# Vérifier que chaque composant dans le registre interne correspond
# à un composant documenté dans l'Excel.
def test_registry_components_exist_in_spec():
    """Tout composant du registre doit exister dans la spec HA."""
    for component in HA_COMPONENT_REGISTRY:
        assert component in excel_components, \
            f"{component}: absent de la spec HA"

# Couche 2 — Couverture des champs requis
# Vérifier que pour chaque champ required dans la spec HA,
# le registre interne a au moins une required_capability OU
# un required_field qui le couvre.
# Note : la correspondance n'est pas un issuperset mécanique.
# Un required_field "command_topic" dans la spec HA est couvert
# par required_capability "has_command" dans le registre — c'est
# une correspondance sémantique documentée, pas syntaxique.
def test_registry_covers_ha_required_fields():
    """Chaque champ HA requis doit avoir un correspondant dans le registre."""
    for component, spec in HA_COMPONENT_REGISTRY.items():
        excel_required = get_excel_required_fields(component)
        for field in excel_required:
            assert field_is_covered(component, field, spec), \
                f"{component}.{field}: pas de couverture dans le registre"

# Couche 3 — Table de correspondance explicite
# La correspondance spec HA → capability interne est documentée
# dans une table de mapping de test, pas dans le registre lui-même.
FIELD_TO_CAPABILITY_MAP = {
    "command_topic": "has_command",
    "state_topic": "has_state",
    "options": "has_options",
    "platform": None,      # toujours fourni par le moteur — pas une capability
    "availability": None,  # toujours fourni par le moteur — pas une capability
}
```

**Ce qui est testé :** la cohérence entre l'abstraction interne et la spec externe, via une table de correspondance explicite et documentée.

**Ce qui n'est pas testé :** l'identité syntaxique — le registre n'est pas un miroir de l'Excel.

**Emplacement :** `resources/daemon/tests/unit/test_ha_component_registry.py`

#### P7 — Enrichissement du diagnostic : ajout pur

**Règle :** Le diagnostic existant (`_build_traceability()`) est enrichi par **ajout** du sous-bloc `projection_validity`. Aucun champ existant n'est supprimé, renommé ou déplacé.

```python
traceability = {
    # Existant — ne pas toucher
    "observed_commands": [...],
    "typing_trace": {...},
    "decision_trace": {...},
    "publication_trace": {...},
    # Ajout — nouveau sous-bloc
    "projection_validity": {
        "is_valid": True,  # ou False, ou None si skipped
        "missing_fields": [],
        "missing_capabilities": [],
        "reason_code": None,
    },
}
```

#### P8 — Catégorie de log `[VALIDATION]`

**Règle :** Les logs de la couche de validation utilisent la catégorie `[VALIDATION]`, distincte de `[MAPPING]` et `[DISCOVERY]`.

```python
logger.debug("[VALIDATION] light eq=%d: command_topic required, has_command=%s", eq_id, has_cmd)
logger.info("[VALIDATION] eq=%d: projection invalide — %s", eq_id, reason_code)
```

## Structure projet — delta moteur de projection

### Nouveau module

```
resources/daemon/
├── validation/                        ← NOUVEAU
│   ├── __init__.py
│   └── ha_component_registry.py       # HA_COMPONENT_REGISTRY, PRODUCT_SCOPE,
│                                      # validate_projection(), ProjectionValidity
└── tests/
    └── unit/
        └── test_ha_component_registry.py  ← NOUVEAU
```

### Mapping pipeline → code

| Étape pipeline | Module responsable | Fonction principale |
|---|---|---|
| 1. Éligibilité | `models/topology.py` | `assess_all()` |
| 2. Mapping candidat | `mapping/light.py`, `cover.py`, `switch.py` | `LightMapper.map()`, etc. |
| 3. Validation HA | `validation/ha_component_registry.py` | `validate_projection()` |
| 4. Décision publication | `models/mapping.py` | `decide_publication()` (étendu) |
| 5. Publication MQTT | `discovery/publisher.py` | `publish_light()`, etc. |
| Diagnostic | `models/cause_mapping.py`, `ui_contract_4d.py` | `reason_code_to_cause()`, `compute_ecart()` |
| Orchestration | `transport/http_server.py` | `_do_handle_action_sync()` |

### Frontières de dépendance

```
  mapping/           validation/          models/           discovery/
  ─────────          ──────────          ─────────         ──────────
  Interprète         Vérifie les         Décide si          Sérialise
  les commandes      contraintes HA      on publie          et envoie
  Jeedom             sur le candidat     ou non             le payload MQTT
       │                   │                  │                   │
       │  MappingResult    │ ProjectionValid. │ PublicationDecis. │
       ├──────────────────►├─────────────────►├──────────────────►│
```

**Règle de dépendance :** `validation/` importe depuis `models/` (types). Il n'importe pas depuis `mapping/`, `discovery/`, ou `transport/`. L'orchestration dans `http_server.py` appelle les trois dans l'ordre.

**Vigilance croissance :** Si le registre HA grandit significativement (> 15 composants, contraintes de validation complexes par type), `ha_component_registry.py` devra être scindé en `registry.py` (données) + `validator.py` (logique). Pour le prochain cycle, un fichier unique suffit.

### Fichiers ciblés par ce delta

| Fichier | Modification |
|---|---|
| `models/mapping.py` | Ajout champ `projection_validity` dans `MappingResult` |
| `models/cause_mapping.py` | Entrées pour les nouveaux `reason_code` classe 2 et 3 |
| `transport/http_server.py` | Appel `validate_projection()` dans le sync ; enrichissement `_build_traceability()` |

### Fichiers non ciblés a priori

Les fichiers suivants ne sont pas ciblés par ce delta, sauf ajustement minimal de compatibilité si nécessaire à l'implémentation : `mapping/light.py`, `cover.py`, `switch.py`, `discovery/publisher.py`, `models/topology.py`, `models/published_scope.py`, `models/actions_ha.py`, `models/ui_contract_4d.py`, `sync/command.py`.

## Validation architecturale

### Cohérence globale ✅

**Compatibilité des décisions :**

Les 8 décisions architecturales (D1-D8) forment une chaîne cohérente sans conflit :
- D1 (sous-blocs bornés) → D2 (module séparé) → D3 (registre statique) → D4 (fonction pure) : conteneur, lieu, données, interface — alignés.
- D5 (migration additive) + D1 : nouveaux sous-blocs portent les nouveaux reason_code, anciens intacts.
- D6 (overrides à l'éligibilité) + pipeline 5 étapes : l'override affecte l'étape 1, n'interfère pas avec 2-5.
- D7 (insertion sync handler) + D4 + D1 : le handler appelle `validate_projection()` et écrit dans `projection_validity`, cohérent avec l'invariant de traversée complète.
- D8 (diagnostic étendu) + D1 + P7 : le diagnostic lit les sous-blocs ajoutés par D1.

**Consistance patterns ↔ décisions :**

Chaque pattern (P1-P8) implémente au moins une décision, aucun pattern n'entre en contradiction avec une décision :
- P1 (traversée complète) → D1, D7. P2 (isolation sous-blocs) → D1. P3 (nommage) → D5. P4 (accès registre) → D2. P5 (motif explicite) → P1. P6 (vérification 3 couches) → D3. P7 (diagnostic enrichi) → D8. P8 (catégorie log) → D2.

**Alignement structure ↔ décisions :**

Le module `validation/` (D2), les fichiers modifiés (`models/mapping.py` → D1, `cause_mapping.py` → D5, `http_server.py` → D7+D8) et la règle de dépendance (`validation/` importe `models/` uniquement) sont cohérents avec le diagramme de frontières.

**Contradictions détectées : 0.**

**Tension vérifiée :** D1 "pas de court-circuit" + P1 "sous-blocs skipped avec `is_valid: None`" → cohérent. `None` signifie "non évalué, voici pourquoi" — le sous-bloc est présent, le diagnostic est complet.

### Couverture des exigences ✅

**AI-3 (prérequis absolu) — couvert intégralement :**

| Exigence AI-3 | Couverture |
|---|---|
| Modèle canonique du moteur de projection | Pipeline 5 étapes, 4 classes d'échec, cause principale canonique |
| Entrées (équipement, type, état, configuration) | Étape 1 — TopologySnapshot + scope utilisateur |
| Règles de décision (mapping, ambiguïté, should_publish) | Étapes 2, 3, 4 — responsabilité délimitée par étape |
| Overrides utilisateur (inclusion/exclusion, priorité) | D6 — éligibilité, extension documentée comme différée |
| Sortie explicable et testable | ProjectionValidity + PublicationDecision + trace diagnostic (D8) |
| Testable indépendamment du code | Fonctions pures, registre statique, tests en isolation |
| Discutable en revue de planning | Ce document = contrat, pas le code |
| Contrat de référence du prochain epic | Pipeline + décisions + patterns + structure = contrat implémentable |

**Acquis V1.1 — préservés :** contrat 4D non modifié (enrichi par ajout pur P7), dual reason_code/cause_code additive (D5), façade d'opérations non rouverte, signal actions_ha non modifié, résolution périmètre non modifiée.

**AI-1 et AI-2 :** correctement signalés comme suites distinctes dans les décisions encore ouvertes (items 12-13). Non livrés par cet artefact — attendu.

### Readiness d'implémentation ✅

| Dimension | Statut |
|---|---|
| Décisions documentées avec rationale et option écartée | ✅ 8/8 |
| Priorités établies (Critique vs Important) | ✅ |
| Patterns avec exemples de code BON/INTERDIT | ✅ 8/8 |
| Structure projet delta définie | ✅ |
| Table pipeline → code (module + fonction par étape) | ✅ |
| Frontières de dépendance avec diagramme | ✅ |
| Vigilance croissance documentée (seuil 15 composants) | ✅ |

### Points ouverts non bloquants

1. **`MappingCapabilities`** — type d'entrée référencé par D4. Type d'implémentation à définir dans la première story, pas un gap architectural.
2. **Signature étendue de `decide_publication()`** — doit accepter `ProjectionValidity` comme entrée. Montré dans P1, implicite dans D7. Clarté suffisante.
3. **`FIELD_TO_CAPABILITY_MAP`** (P6) — artefact de test, pas d'architecture. Correct en l'état.

### Conclusion

**Statut : PRÊT POUR LA SUITE DU WORKFLOW.**

**Niveau de confiance : élevé.** Le document est auto-cohérent, couvre intégralement l'exigence AI-3, préserve les acquis V1.1 sans modification, et fournit un contrat suffisamment précis pour guider l'implémentation story par story.

Le prochain workflow BMAD peut démarrer depuis ce modèle comme contrat de référence.
