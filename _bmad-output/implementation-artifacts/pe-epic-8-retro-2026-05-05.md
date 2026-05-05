# Retrospective pe-epic-8 — Refactor dispatch + registry-driven + golden-file

Date: 2026-05-05  
Projet: jeedom2ha  
Cycle actif: Moteur de projection explicable  
Facilitation: Bob (Scrum Master)  
Participant principal: Alexandre (Project Lead)

## Sources de verite analysees

- `_bmad-output/planning-artifacts/active-cycle-manifest.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `_bmad-output/planning-artifacts/architecture-projection-engine.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/ha-projection-reference.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/8-1-mapper-registry-dispatch-deterministe-et-slot-terminal-reserve.md`
- `_bmad-output/implementation-artifacts/8-2-publisher-registry-dispatch-table-ha-entity-type-vers-methode-publish.md`
- `_bmad-output/implementation-artifacts/8-3-refactor-http-server-run-sync-boucle-dispatch-unique-et-compteurs-generiques.md`
- `_bmad-output/implementation-artifacts/8-4-gate-golden-file-de-non-regression-sur-30-equipements-de-reference.md`
- Commits: `b291cf5`, `24b794d`, `d0df00f`, `9c868ab`, `a8ea3b1`, `b63c14d`
- PRs: #107, #108, #109, #110

## Synthese

`pe-epic-8` est clos et a tenu son contrat principal: transformer un dispatch hardcode en infrastructure extensible sans ouvrir de nouveau comportement Home Assistant. L'epic a livre le `MapperRegistry`, le `PublisherRegistry`, le branchement registry-driven de `_run_sync`, puis un golden-file de 30 equipements qui devient le verrou de non-regression pour les prochaines stories touchant mapping, transport, discovery ou validation.

Le resultat produit important n'est pas une nouvelle couverture HA immediate. C'est la suppression du cout structurel qui aurait force `pe-epic-9` a dupliquer environ 200 lignes dans `http_server.py` pour ajouter `sensor`, `binary_sensor` et `button`. La baseline operationnelle connue reste: box Alexandre = 278 eqLogics, 81 eligibles, 30 publies, ratio publie/eligible 37%. Cette mesure est informative et sert de point de comparaison pour `pe-epic-9`, sans devenir une assertion de golden-file.

Bob (Scrum Master): "Epic 8 a livre une infrastructure, pas une feature visible. C'est exactement le bon resultat pour un refactor pur."

Winston (Architect): "La valeur est dans la nouvelle forme du systeme: les prochains types HA se raccordent au registre et au golden-file au lieu de retoucher la boucle centrale."

Dana (QA Engineer): "Le golden-file 8.4 est maintenant le filet de regression-control. Toute future evolution doit expliquer son drift, pas le masquer."

## Partie 1 — Epic Review

### Etat de livraison

| Story | PR / commit | Resultat | Preuve qualite |
| --- | --- | --- | --- |
| 8.1 MapperRegistry | PR #107, `b291cf5` | `MapperRegistry` ordonne `LightMapper`, `CoverMapper`, `SwitchMapper`, `FallbackMapper`; fallback no-op terminal | 6 tests Story 8.1; corpus daemon 657 passed |
| 8.2 PublisherRegistry | PR #108, `24b794d` | Dispatch table `light`, `cover`, `switch`; echec explicite `publisher_not_registered` | 8 tests Story 8.2; corpus daemon 665 passed |
| 8.3 Refactor `_run_sync` | PR #109, `d0df00f`; closeout `9c868ab` | `_run_sync` consomme les deux registries; compteurs dynamiques legacy-compatibles; bookkeeping publication unique | Story 8.3 6/6; suite 8.1+8.2+8.3 20/20; corpus daemon 671 passed |
| 8.4 Golden-file gate | PR #110, merge commit `a8ea3b1`; closeout `b63c14d` | Corpus deterministe 30 equipements + snapshot + test golden-file standard CI | test 8.4 PASS; suite 8.1-8.4 21 passed; corpus daemon 1198 passed |

Note de reconciliation: `sprint-status.yaml` est la source d'execution et marque `pe-epic-8` et les 4 stories comme `done`. Les story records 8.1 et 8.2 conservent un en-tete `Status: review`, mais les PRs mergees et le sprint status font foi pour cette retrospective.

### Ce qui a bien fonctionne

- Le correct-course 2026-04-30 a pose un sequence clair: refactor pur d'abord, extension reelle ensuite. Cette separation a evite d'entremeler infrastructure et nouveau comportement.
- La progression 8.1 -> 8.2 -> 8.3 a garde des frontieres nettes: mapping dans `mapping/`, publication dans `discovery/`, orchestration dans `transport/http_server.py`.
- Story 8.3 a supprime le point de duplication le plus dangereux: les branches `light` / `cover` / `switch` dans `_run_sync`.
- Story 8.4 a transforme une promesse de parite en preuve executable, avec fixture stable, snapshot canonique et diff lisible.
- Le scope de garantie a ete respecte: aucun nouveau type publie, aucun changement `PRODUCT_SCOPE`, `HA_COMPONENT_REGISTRY`, `cause_label`, `cause_action` ou `reason_code`.

### Ce qui a moins bien fonctionne

- Le besoin de conserver les cles legacy `lights_*`, `covers_*`, `switches_*` a ete decouvert pendant 8.3 via `plugin_info/configuration.php`. Ce n'etait pas un echec d'implementation, mais un signal que les consommateurs externes de `mapping_summary` doivent etre audites avant l'extension.
- Le helper d'inspection des types connus de `PublisherRegistry` reste couple a une instance construite avec `DiscoveryPublisher(None)`. Le comportement est couvert, mais l'API exprime mal l'intention.
- La smoke terrain 8.3 a ete limitee par l'environnement local (`JEEDOM_BOX_HOST` absent). Story 8.4 a apporte la gate pytest normative, et la baseline box Alexandre reste le repere produit pour `pe-epic-9`.

### Lecons apprises

- Un refactor de dispatch doit inclure ses consommateurs de resume, pas seulement la boucle centrale. Sinon les compteurs deviennent dynamiques dans le backend mais restent partiellement hardcodes dans les surfaces de reporting.
- Le bon niveau d'abstraction pour `PublisherRegistry` est double: resolution runtime via instance de publisher, et exposition statique des types connus pour inspection.
- Le golden-file doit rester un verrou anti-drift, pas un generateur de snapshot opportuniste. Les 30 equipements initiaux doivent rester intacts quand `pe-epic-9` l'etend.
- La mesure terrain doit rester separee du golden-file: le golden-file prouve la non-regression deterministe, la box Alexandre mesure la progression reelle de couverture.

### Retrospective precedente

Aucune retrospective `pe-epic-7` n'a ete trouvee dans les artefacts. La continuite exploitable vient donc du `sprint-change-proposal-2026-04-30.md`. Follow-through constate: les epics `pe-epic-8` et `pe-epic-9` ont ete ajoutes, `pe-epic-8` a ete execute dans l'ordre, et le blocage de `pe-epic-9` par le golden-file 8.4 est leve apres PR #110.

## Partie 2 — Preparation pe-epic-9

### Readiness pe-epic-9

`pe-epic-9` peut demarrer sur le plan produit: le prerequis epic-level `pe-epic-8` est clos, le golden-file 8.4 est present, et `ha-projection-reference.md` est source-of-truth officielle pour les contraintes `sensor.mqtt`, `binary_sensor.mqtt` et `button.mqtt`.

Le plan de `pe-epic-9` reste valide. Il ne requiert pas de nouveau correct-course, mais il doit recevoir deux corrections de reporting avant Story 9.1 pour eviter une mesure terrain fausse des nouveaux publies.

### Triage avant / dans / apres pe-epic-9

| Placement | Items | Decision |
| --- | --- | --- |
| Prefixe pe-epic-9 avant 9.1 | `plugin_info/configuration.php:331-334`, `scripts/deploy-to-box.sh:509-513` | Corriger les totaux publies hardcodes avant l'ajout de `sensor_*`, `binary_sensors_*`, `buttons_*` dans `mapping_summary`. |
| Integre dans Story 9.1 | `PublisherRegistry.known_types()` | Ajouter une API statique ou classmethod au moment ou 9.1 touche `PublisherRegistry` pour enregistrer `sensor`. |
| Integre dans chaque story 9.1-9.4 | Golden-file 8.4 etendu | Chaque nouveau mapper/publisher ajoute ses cas, tout en gardant le corpus initial vert. |
| Integre dans l'epic gate pe-epic-9 | Baseline terrain Alexandre | Mesurer les nouveaux publies par type et par origine de mapper contre la baseline 278 / 81 / 30 / 37%. |
| Reporte pe-epic-10+ | Vagues hors `sensor`, `binary_sensor`, `button` | Les 25 composants HA restants restent hors-vague et doivent repartir de `ha-projection-reference.md` + FR40 / NFR10. |

## Action Items Priorises

| ID | Priorite | Titre | Owner | Target story | Placement | Critere de sortie |
| --- | --- | --- | --- | --- | --- | --- |
| PE8-AI-01 | P0 | Total publie UI Jeedom dynamique | Dev frontend/PHP | Prefixe avant 9.1 | Avant pe-epic-9 | `plugin_info/configuration.php` ne somme plus seulement `lights_published`, `covers_published`, `switches_published`; les futurs `*_published` sont inclus ou une valeur backend totale canonique est utilisee. |
| PE8-AI-02 | P0 | Total publie script terrain dynamique | Dev/Ops | Prefixe avant 9.1 | Avant pe-epic-9 | `scripts/deploy-to-box.sh` ne somme plus seulement les trois types historiques; le compteur final inclut les types ajoutes par 9.1-9.4. |
| PE8-AI-03 | P1 | API statique `PublisherRegistry.known_types()` | Dev backend | Story 9.1 | Dans 9.1 | L'inspection des types connus ne depend plus d'une instance `PublisherRegistry(DiscoveryPublisher(None))`; les tests 8.3/9.1 lisent la meme source de verite. |
| PE8-AI-04 | P1 | Extension disciplinee du golden-file | QA + Dev | Stories 9.1, 9.2, 9.3, 9.4 | Dans chaque story | Les nouveaux cas `sensor`, `binary_sensor`, `button`, `FallbackMapper` s'ajoutent au snapshot sans modifier les 30 equipements initiaux hors changement story-level explicitement justifie. |
| PE8-AI-05 | P1 | Gate terrain pe-epic-9 avec baseline publie/eligible | Alexandre + QA | Gate epic pe-epic-9 | Dans pe-epic-9 | Le resultat terrain documente nouveaux publies par type (`sensor`, `binary_sensor`, `button`) et origine (`mapper specifique`, `FallbackMapper`) en comparaison de la baseline 278 eqLogics / 81 eligibles / 30 publies. |
| PE8-AI-06 | P2 | Garder 9.5 apres surfaces reelles | Product Owner + Dev | Story 9.5 | Dans 9.5 | Aucun `cause_action` ou CTA n'est expose pour une surface qui n'est pas effectivement ouverte par 9.1-9.4; la regle "no faux CTA" reste appliquee. |
| PE8-AI-07 | P2 | Backlog des vagues suivantes depuis la reference HA | Product Owner + Architect | pe-epic-10+ | Reporte | Les composants hors vague 1 ne sont pas ajoutes opportunistement; ils seront planifies depuis `ha-projection-reference.md`, FR40 et NFR10. |

## Risques Residuals

- Si PE8-AI-01 et PE8-AI-02 ne sont pas faits avant 9.1, `mapping_summary` pourra contenir des nouveaux publies exacts mais les deux totaux externes resteront faux.
- Si PE8-AI-03 est repousse, l'ajout de `sensor` dans `PublisherRegistry` fonctionnera probablement, mais l'inspection restera fragile et moins lisible.
- Si les nouveaux cas 9.x modifient le snapshot initial au lieu de l'etendre, le golden-file perdra sa valeur de baseline de parite pe-epic-8.

## Readiness Assessment

| Dimension | Statut | Notes |
| --- | --- | --- |
| Qualite / tests | Pret | Golden-file 8.4 PASS; suite standard annoncee 1198 passed. |
| Merge / integration | Pret | PR #110 mergee le 2026-05-05; merge commit `a8ea3b1`; closeout `b63c14d` sur `main`. |
| Dette bloquante | Limitee | Deux corrections de totals externes doivent preceder 9.1. |
| Plan produit | Pret | `pe-epic-9` reste aligne avec le SCP 2026-04-30 et `ha-projection-reference.md`. |
| Gouvernance scope | Pret avec vigilance | `button` ne peut entrer dans `PRODUCT_SCOPE` que dans Story 9.3 sous FR40 / NFR10. |

## Conclusion

`pe-epic-8` a rempli son role de charniere: il ne livre pas plus d'entites, mais il rend l'ouverture de `pe-epic-9` mecaniquement soutenable. Le prochain mouvement doit rester strict: corriger les deux compteurs externes, ouvrir `sensor` via 9.1 en s'appuyant sur une API d'inspection propre, puis etendre le golden-file story par story sans degrader le corpus initial.

Bob (Scrum Master): "Retrospective complete. L'epic est clos, le plan suivant est valide, et les vrais points d'attention sont assez petits pour etre traites proprement avant qu'ils ne deviennent du bruit produit."
