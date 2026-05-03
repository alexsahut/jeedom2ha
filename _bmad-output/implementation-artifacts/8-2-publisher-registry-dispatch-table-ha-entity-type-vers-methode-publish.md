# Story 8.2 : PublisherRegistry — dispatch table `ha_entity_type` vers methode publish

Status: review

## Story

En tant que mainteneur,
je veux un `PublisherRegistry` qui mappe un `ha_entity_type` vers la methode `publish_*` correspondante du `DiscoveryPublisher`,
afin de remplacer les trois `elif` hardcodes de `_run_sync` par une dispatch table extensible sans introduire de nouveau comportement.

## Acceptance Criteria

**AC1 — Registre des publishers existants**
Given le registre des publishers,
When il est inspecte au demarrage du daemon,
Then il contient exactement les entrees operationnelles actuelles : `light -> publish_light`, `cover -> publish_cover`, `switch -> publish_switch`.

**AC2 — Resolution identique aux branches actuelles**
Given un `mapping.ha_entity_type` connu (`light`, `cover`, `switch`),
When la methode publish correspondante est resolue via le registre,
Then elle est strictement la meme methode liee que celle invoquee aujourd'hui par les branches `elif` de `_run_sync`.

**AC3 — Type inconnu : echec explicite**
Given un `mapping.ha_entity_type` absent du registre,
When la resolution ou la publication est tentee,
Then l'echec est explicite, logue comme defaut de couverture publisher, et produit un `publication_result` non-`success` avec un `technical_reason_code` dedie.

**AC4 — Zero comportement nouveau**
Given la Story 8.2,
When le diff est inspecte,
Then aucun nouveau publisher n'est cree, `sensor` / `binary_sensor` / `button` ne sont pas enregistres, `http_server.py` n'est pas modifie, et `PRODUCT_SCOPE`, `HA_COMPONENT_REGISTRY`, `cause_label`, `cause_action`, `reason_code` restent inchanges.

## Tasks / Subtasks

- [x] Task 1 — Creer `PublisherRegistry` dans `resources/daemon/discovery/registry.py` (AC: 1, 2, 3, 4)
  - [x] 1.1 — Creer `resources/daemon/discovery/registry.py` sur le pattern de `resources/daemon/mapping/registry.py`
  - [x] 1.2 — Implementer `UnknownPublisherError` avec `ha_entity_type` et `technical_reason_code = "publisher_not_registered"`
  - [x] 1.3 — Implementer `PublisherRegistry.__init__(self, publisher: DiscoveryPublisher)` avec une table non configurable et exactement ces cles : `light`, `cover`, `switch`
  - [x] 1.4 — Mapper les cles vers les methodes liees existantes : `publisher.publish_light`, `publisher.publish_cover`, `publisher.publish_switch`
  - [x] 1.5 — Exposer une propriete `publishers` retournant une copie de la table pour inspection AC1
  - [x] 1.6 — Implementer `resolve(self, ha_entity_type: str) -> PublishMethod` : retourne la methode liee pour un type connu ; logue une erreur claire et leve `UnknownPublisherError` pour un type inconnu
  - [x] 1.7 — Implementer `publish(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool` : delegue au publisher resolu ; pour un type inconnu, renseigne `mapping.publication_result = PublicationResult(status="failed", technical_reason_code="publisher_not_registered", attempted_at=<UTC ISO>)` et retourne `False`
  - [x] 1.8 — Ne pas importer depuis `transport/`, ne pas appeler `_make_publication_result()` (fonction privee de `http_server.py`), ne pas modifier `DiscoveryPublisher`

- [x] Task 2 — Tests unitaires `resources/daemon/tests/unit/test_story_8_2_publisher_registry.py` (AC: 1, 2, 3, 4)
  - [x] 2.1 — Test AC1 : `PublisherRegistry(DiscoveryPublisher(...)).publishers.keys()` vaut exactement `{"light", "cover", "switch"}`
  - [x] 2.2 — Test AC1/AC4 : verifier explicitement l'absence de `sensor`, `binary_sensor` et `button`
  - [x] 2.3 — Test AC2 light : `registry.resolve("light")` est liee au meme objet publisher et a `DiscoveryPublisher.publish_light`
  - [x] 2.4 — Test AC2 cover : idem pour `publish_cover`
  - [x] 2.5 — Test AC2 switch : idem pour `publish_switch`
  - [x] 2.6 — Test AC3 resolution inconnue : `registry.resolve("sensor")` leve `UnknownPublisherError`, ne retourne ni `None` ni `False`, et logue le type inconnu
  - [x] 2.7 — Test AC3 publication inconnue : `await registry.publish(mapping_ha_entity_type_inconnu, snapshot)` retourne `False` et renseigne `mapping.publication_result.status == "failed"` avec `technical_reason_code == "publisher_not_registered"`
  - [x] 2.8 — Test delegation connue : avec une methode `publish_light` mockee en `AsyncMock(return_value=True)`, `await registry.publish(mapping_light, snapshot)` attend exactement cette methode avec `(mapping, snapshot)`

- [x] Task 3 — Non-regression et limites de scope (AC: 4)
  - [x] 3.1 — Executer `python3 -m pytest resources/daemon/tests/unit/test_story_8_2_publisher_registry.py`
  - [x] 3.2 — Executer `python3 -m pytest resources/daemon/tests/unit/test_story_8_1_mapper_registry.py resources/daemon/tests/unit/test_story_8_2_publisher_registry.py`
  - [x] 3.3 — Executer un lint cible si disponible sur `resources/daemon/discovery/registry.py` et le test Story 8.2
  - [x] 3.4 — Verifier le diff : aucun changement dans `resources/daemon/transport/http_server.py`

## Dev Notes

### Contrat d'interface attendu

`PublisherRegistry` vit dans `resources/daemon/discovery/registry.py`, par symetrie avec `MapperRegistry` dans `resources/daemon/mapping/registry.py`.

Interface recommandee :

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict

from discovery.publisher import DiscoveryPublisher
from models.mapping import MappingResult, PublicationResult
from models.topology import TopologySnapshot

PublishMethod = Callable[[MappingResult, TopologySnapshot], Awaitable[bool]]

_LOGGER = logging.getLogger(__name__)


class UnknownPublisherError(KeyError):
    technical_reason_code = "publisher_not_registered"

    def __init__(self, ha_entity_type: str) -> None:
        self.ha_entity_type = ha_entity_type
        super().__init__(ha_entity_type)


class PublisherRegistry:
    def __init__(self, publisher: DiscoveryPublisher) -> None:
        self._publishers: Dict[str, PublishMethod] = {
            "light": publisher.publish_light,
            "cover": publisher.publish_cover,
            "switch": publisher.publish_switch,
        }

    @property
    def publishers(self) -> Dict[str, PublishMethod]:
        return dict(self._publishers)

    def resolve(self, ha_entity_type: str) -> PublishMethod:
        try:
            return self._publishers[ha_entity_type]
        except KeyError:
            _LOGGER.error(
                "[DISCOVERY] No publisher registered for ha_entity_type=%s",
                ha_entity_type,
            )
            raise UnknownPublisherError(ha_entity_type) from None

    async def publish(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        try:
            publish_method = self.resolve(mapping.ha_entity_type)
        except UnknownPublisherError as exc:
            mapping.publication_result = PublicationResult(
                status="failed",
                technical_reason_code=exc.technical_reason_code,
                attempted_at=datetime.now(timezone.utc).isoformat(),
            )
            return False
        return await publish_method(mapping, snapshot)
```

Ce contrat prepare Story 8.3 sans brancher encore la boucle `_run_sync`.

### Code existant a reutiliser

- `resources/daemon/discovery/publisher.py` expose deja `DiscoveryPublisher.publish_light()`, `publish_cover()` et `publish_switch()`, tous async et retournant `bool`
- `resources/daemon/transport/http_server.py:1072-1224` contient les trois branches hardcodees actuelles ; elles restent intactes dans cette story
- `resources/daemon/mapping/registry.py` est le pattern local : table ordonnee, propriete d'inspection, resolution deterministe, tests isoles
- `resources/daemon/models/mapping.py` porte `PublicationResult`; son `technical_reason_code` est le bon emplacement pour `publisher_not_registered`

### Dev Agent Guardrails

**Cadre de garantie pe-epic-8 — non negociable :**
- Aucun nouveau type publie cote Home Assistant
- Aucun nouveau publisher cree dans Story 8.2
- `sensor`, `binary_sensor` et `button` ne sont pas ajoutes au `PublisherRegistry` dans cette story
- `PRODUCT_SCOPE` reste inchange, meme si `sensor` et `binary_sensor` y existent deja depuis Story 7.4
- `HA_COMPONENT_REGISTRY` reste inchange
- `cause_label`, `cause_action`, `reason_code` et `cause_mapping.py` restent inchanges
- `http_server.py` reste inchange ; le refactor de la boucle est strictement Story 8.3

**Type inconnu :**
- Ne jamais retourner `None` comme signal de resolution absente
- Ne jamais faire un `continue` silencieux
- Ne pas ajouter un reason code canonique diagnostic pour cette story
- Utiliser un `technical_reason_code` de `publication_result` : `publisher_not_registered`
- La decision produit et le diagnostic 4D ne doivent pas etre modifies par cet echec technique isole

**Frontieres d'architecture :**
- `discovery/registry.py` peut importer `discovery.publisher`, `models.mapping`, `models.topology`
- `discovery/registry.py` ne doit pas importer `transport.http_server`
- Le publisher serialise et envoie ; il ne valide pas les contraintes HA et ne modifie pas `PRODUCT_SCOPE`
- La validation HA reste dans `validation/ha_component_registry.py`

### Previous Story Intelligence

Story 8.1 est mergee sur `main` via PR #107 le 2026-05-03 (`b291cf5 feat(pe-8.1): MapperRegistry deterministe + slot FallbackMapper terminal`). Elle a etabli :
- `resources/daemon/mapping/registry.py` avec registre non configurable et inspection par propriete
- `resources/daemon/mapping/fallback.py` avec slot terminal no-op
- tests unitaires isoles dans `resources/daemon/tests/unit/test_story_8_1_mapper_registry.py`
- aucune modification de `http_server.py`

Reprendre le style de 8.1 : changement minimal, tests directs, pas d'anticipation de Story 8.3 ou pe-epic-9.

### Git Intelligence Summary

Derniers commits pertinents :
- `b291cf5` — Story 8.1 : ajoute `MapperRegistry`, `FallbackMapper`, test Story 8.1, statut BMAD
- `e2ad5dd` / `7aa472d` — closeout correct-course 2026-04-30 : ouvre pe-epic-8 et pe-epic-9
- `bf46596` — Story 7.4 : gouvernance `PRODUCT_SCOPE` post 7.4, sans publishers reels pour `sensor` / `binary_sensor`

Aucune dependance externe nouvelle n'est requise.

### Project Structure Notes

Alignement avec AR3 :
- `mapping/` interprete Jeedom (`MapperRegistry`)
- `validation/` verifie les contraintes HA (`HA_COMPONENT_REGISTRY`, `PRODUCT_SCOPE`)
- `discovery/` serialise, publie et, avec Story 8.2, resout le publisher a appeler (`PublisherRegistry`)
- `transport/http_server.py` orchestre mais ne doit pas etre modifie avant Story 8.3

Story terrain : false. Cette story est un refactor preparatoire teste en unitaire ; aucun deploiement box reelle ni validation MQTT terrain n'est requis pour la creation du registre.

### References

- [Source: _bmad-output/planning-artifacts/active-cycle-manifest.md §7] — cycle actif, fichiers actifs, `ha-projection-reference.md`, golden-file 8.4
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md §5.2] — cadre pe-epic-8, zero nouveau comportement, Story 8.2
- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md#Statut-BMAD-et-regles-devolution] — publishers derives de la reference HA, pas l'inverse
- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md#Sequencing-douverture-documente] — `sensor` / `binary_sensor` ouverts dans `PRODUCT_SCOPE` mais publication reelle repoussee a pe-epic-9
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story-82--PublisherRegistry] — story, AC et dev notes de reference
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Gates-epic-level-pe-epic-8] — gates zero regression
- [Source: _bmad-output/planning-artifacts/architecture-projection-engine.md#D2--Module-validation-separe] — separation mapping / validation / publisher
- [Source: _bmad-output/planning-artifacts/architecture-projection-engine.md#P4--Acces-au-registre-HA] — publisher = serialization, validation en amont
- [Source: resources/daemon/discovery/publisher.py] — methodes existantes `publish_light`, `publish_cover`, `publish_switch`
- [Source: resources/daemon/transport/http_server.py:1072] — branches `elif` hardcodees actuelles a ne pas modifier dans Story 8.2
- [Source: resources/daemon/mapping/registry.py] — pattern local de registre Story 8.1
- [Source: resources/daemon/models/mapping.py] — `PublicationResult` et `MappingResult.publication_result`
- [Source: _bmad-output/project-context.md] — stack Python/pytest, frontieres daemon, regles anti-pattern et absence de deploiement terrain improvise

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `python3 -m pytest resources/daemon/tests/unit/test_story_8_2_publisher_registry.py` (8 passed)
- `python3 -m pytest resources/daemon/tests/unit/test_story_8_1_mapper_registry.py resources/daemon/tests/unit/test_story_8_2_publisher_registry.py` (14 passed)
- `python3 -m flake8 resources/daemon/discovery/registry.py resources/daemon/tests/unit/test_story_8_2_publisher_registry.py` (OK)
- `python3 -m pytest` depuis `resources/daemon/` (665 passed, 0 fail)
- `git diff --name-only -- resources/daemon/transport/http_server.py resources/daemon/mapping/light.py resources/daemon/mapping/cover.py resources/daemon/mapping/switch.py resources/daemon/validation/ha_component_registry.py resources/daemon/discovery/publisher.py` (vide)

### Completion Notes List

Story creee le 2026-05-03. Analyse des sources :
- cycle actif `Moteur de projection explicable`
- correct-course 2026-04-30
- reference HA officielle du cycle
- Epic 8 / Story 8.2 / gates pe-epic-8
- architecture AR3 et frontieres mapping / validation / discovery / transport
- code existant `DiscoveryPublisher`, branches hardcodees `_run_sync`, `MapperRegistry` Story 8.1

Decisions de preparation :
- `PublisherRegistry` localise dans `resources/daemon/discovery/registry.py`
- table limitee a `light`, `cover`, `switch`
- `sensor`, `binary_sensor`, `button` explicitement hors scope Story 8.2
- echec inconnu trace par `PublicationResult(status="failed", technical_reason_code="publisher_not_registered")`
- aucune modification de `http_server.py` avant Story 8.3
- terrain story : false

Execution dev 2026-05-03 :
- implementation de `UnknownPublisherError` et `PublisherRegistry` dans `resources/daemon/discovery/registry.py` avec table fixe `{light, cover, switch}`
- `resolve()` leve explicitement `UnknownPublisherError` et logue l'absence de publisher pour un `ha_entity_type` inconnu
- `publish()` renseigne `mapping.publication_result` avec `technical_reason_code="publisher_not_registered"` pour un type inconnu puis retourne `False`
- ajout de 8 tests unitaires Story 8.2 couvrant AC1 a AC4 et la delegation vers `publish_light`
- verification non-regression complete du corpus daemon: `665 passed`

### File List

- `_bmad-output/implementation-artifacts/8-2-publisher-registry-dispatch-table-ha-entity-type-vers-methode-publish.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/discovery/registry.py`
- `resources/daemon/tests/unit/test_story_8_2_publisher_registry.py`

## Change Log

- 2026-05-03 — Creation de la Story 8.2 ready-for-dev : PublisherRegistry preparatoire, garde-fous pe-epic-8, tests unitaires cibles, zero modification code produit.
- 2026-05-03 — Story 8.2 implementee: ajout de `PublisherRegistry` + `UnknownPublisherError`, 8 tests unitaires Story 8.2, non-regression daemon 665/665, statut passe a `review`.
