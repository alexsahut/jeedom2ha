# Retrospective pe-epic-10 — Vague Homebridge -> HA minimale utile

Date: 2026-06-12  
Projet: jeedom2ha  
Cycle actif: Moteur de projection explicable  
Facilitation: Bob (Scrum Master)  
Participant principal: Alexandre (Project Lead)

## Sources de verite analysees

- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `_bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md`
- `_bmad-output/planning-artifacts/pe-epic-10-perimetre-prefixe-2026-06-08.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-07.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-10.md`
- `_bmad-output/planning-artifacts/backlog-icebox.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/pe-epic-9-retro-2026-06-06.md`
- `_bmad-output/implementation-artifacts/10-0-prefixe-de-gel-du-perimetre-homebridge-ha-vise.md`
- `_bmad-output/implementation-artifacts/10-1-verification-et-completion-du-chemin-button-pour-les-5-scenarios-homekit-visibles.md`
- `_bmad-output/implementation-artifacts/10-2-ouverture-gouvernee-de-climate-pour-les-thermostats-homebridge-representatifs.md`
- `_bmad-output/implementation-artifacts/10-3-evaluation-puis-ouverture-ciblee-de-alarm-control-panel-pour-alarme-maison.md`
- `_bmad-output/implementation-artifacts/10-4-cadrage-des-composites-metier-iq-ev-spa-sans-ouverture-cosmetique.md`
- `_bmad-output/implementation-artifacts/10-5-parite-generics-alarme-armed-released.md`
- `_bmad-output/implementation-artifacts/10-6-fix-souscription-mqtt-manquante-scenario-cmd.md`
- `_bmad-output/implementation-artifacts/10-7-presence-switch-mapper-publier-switch-presence.md`

## Synthese

`pe-epic-10` est clos et a tenu sa promesse produit: recuperer dans Home Assistant la parite minimale utile observee cote Homebridge, sans transformer l'epic en vague opportuniste d'ouverture HA sans borne. L'epic a d'abord gele son perimetre reel via `10.0`, puis a enchaine des increments tres lisibles: scenarios HomeKit via `button`, thermostats via `climate`, alarme via `alarm_control_panel`, cadrage explicite des composites `IQ EV` / `SPA`, correction de parite des generics d'alarme natifs, fix terrain de souscription MQTT scenario, puis extension `presence -> switch` cloturee avec decision explicite SM faute de candidat live validable sur la box actuelle.

Le resultat important n'est pas seulement l'ajout de types ou de fixes. `pe-epic-10` a montre que le moteur registry-driven peut suivre un backlog derive d'un usage terrain reel Homebridge tout en gardant les guardrails FR40 / NFR10, le golden-file, les gates terrain et la discipline "pas d'ouverture cosmetique". La vague a aussi confirme qu'une parite utile ne se joue pas seulement dans les mappers: elle depend tout autant de la publication MQTT effective, du routage de commandes, des generics reels observes sur la box et de la qualite du cadrage produit autour des composites et des zones sensibles.

Bob (Scrum Master): "Epic 10 a fait exactement ce qu'il fallait: transformer un audit Homebridge en backlog executable sans casser la gouvernance technique qu'on a construite depuis pe-epic-8."

Winston (Architect): "Le signal fort, c'est qu'on a pu ouvrir `climate` et `alarm_control_panel`, corriger les generics natifs d'alarme, et fermer proprement le cas presence sans mentir sur la preuve terrain."

Dana (QA Engineer): "La lecon qualite est nette: sur cette vague, un type HA ouvert sans verification de transport MQTT ou sans lecture des generics live aurait donne une fausse impression de parite."

## Partie 1 — Epic Review

### Etat de livraison

| Story | Resultat principal | Preuve de qualite |
| --- | --- | --- |
| 10.0 Prefixe Homebridge | gel du perimetre Homebridge -> HA utile, exclusions et zones sensibles bornees | artefact de prefixe `done`, matrice canonique et gates epic-level poses |
| 10.1 Scenarios HomeKit | verification + completion du chemin `button` pour les 5 scenarios historiques | gate terrain PASS 5/5, topics scenario confirmes |
| 10.2 Climate | ouverture gouvernee de `climate` pour les thermostats representatifs | gate terrain PASS, `climates_published=7` |
| 10.3 Alarm control panel | ouverture ciblee de `alarm_control_panel` pour `Alarme maison` | story `done`, puis parite live completee par 10.5 |
| 10.4 Composites IQ EV / SPA | cadrage sans ouverture cosmetique des composites metier | `SPA` classe "deja couvert par composition", `IQ EV` reporte comme extension bornee |
| 10.5 Generics alarme natifs | fallback `ALARM_ARMED` / `ALARM_RELEASED` reconnu par le mapper | 792 PASS, gate terrain PASS `alarm_published=1` |
| 10.6 MQTT scenarios | fix de souscription `jeedom2ha/+/cmd` pour les scenarios | gate terrain PASS, preuve daemon + scenario38.log |
| 10.7 Presence switch | `PresenceSwitchMapper` + fallback `binary_sensor` preserve | 808/808 PASS, gate terrain execute, cloture `done` avec decision explicite SM faute de candidat live validable |

### Ce qui a bien fonctionne

- La story `10.0` a joue son vrai role de prefixe: elle a borne le sujet et a evite que l'epic derive vers "ouvrons les types HA qui nous arrangent" au lieu de suivre une valeur terrain explicite.
- Le sequencing a ete globalement excellent: verification d'abord, ouverture gouvernee ensuite, correctifs terrain ensuite, puis seulement cadrage des zones sensibles et composites.
- L'epic a reussi a mixer plusieurs natures de travail sans confusion: ouverture produit (`10.2`, `10.3`), correctif de parite live (`10.5`), bug transport MQTT (`10.6`), cadrage metier (`10.4`) et decision SM explicite (`10.7`).
- Les gates terrain ont vraiment servi de filtre produit. `10.2`, `10.5` et `10.6` ont ete confirmes sur la box reelle, et `10.7` a ete ferme honnetement parce que le blocage etait un manque de candidat terrain, pas un defaut d'implementation restant.
- Le principe "pas d'ouverture cosmetique" a ete preserve. `IQ EV` n'a pas ete force dans un composant HA flatteur mais faux, et le cas presence n'a pas ete declare PASS sur une preuve live inexistante.

### Ce qui a moins bien fonctionne

- L'epic a confirme que la parite Homebridge utile se casse souvent dans les details terrain plutot que dans la couche de mapping pure: souscription MQTT scenario absente, generics alarme reels differents du cas theorique, equipements presence reels non alignes avec l'hypothese `SET_ON` / `SET_OFF`.
- Le commentaire de `sprint-status.yaml` pour `pe-epic-10` n'a pas ete maintenu au fil de l'eau et est devenu trompeur en fin d'epic. Le tracker de haut niveau doit mieux refleter les decisions de closeout.
- La discipline de pre-flight terrain est restee inegale dans certains artefacts story-level. Le projet a bien execute les gates, mais les checklists de Task 0 n'etaient pas toujours entierement realignees avec l'etat final de la story.
- Le cas `presence` a montre une fragilite de formulation d'AC terrain: il faut distinguer plus explicitement "preuve d'implementation et de non-regression" de "preuve live sur equipement representatif disponible".

### Lecons apprises

- Une vague de parite "Homebridge -> HA" doit partir d'un inventaire usage/famille, mais doit etre refermee story par story sur les generics et equipements reels visibles sur la box.
- Une ouverture de type HA ne suffit pas a recuperer l'usage si le transport de commande n'est pas complet. `10.6` est la preuve que le backlog de parite doit couvrir le chemin end-to-end, pas seulement la projection.
- Les stories d'evaluation/cadrage (`10.0`, `10.4`) ont une vraie valeur productive: elles evitent de sur-promettre et reduisent les contournements cosmetiques plus tard.
- Les AC terrain pour zones sensibles doivent integrer un mode de sortie explicite quand aucun candidat live representatif n'est disponible. Fermer proprement avec waiver motive vaut mieux qu'un faux PASS ou qu'une story eternelle.

### Continuite avec la retrospective pe-epic-9

| Action item pe-epic-9 | Etat dans pe-epic-10 | Observation |
| --- | --- | --- |
| PE9-AI-01 Correct-course `pe-epic-10+` depuis la reference HA | ✅ Solde | materialise par le correct-course du 2026-06-07 puis Story 10.0 |
| PE9-AI-02 Checklist canonique "nouveau type HA" | ✅ Tenu de fait | appliquee dans les stories d'ouverture reelle `10.2` et `10.3`, puis dans les correctifs `10.5` / `10.6` |
| PE9-AI-03 Matrice d'impact transversale | ✅ Solde | absorbee par le prefixe 10.0 et le sequencing epic-level Homebridge -> HA |
| PE9-AI-04 Pack terrain cas bords du diagnostic | ✅ Partiellement solde | gates terrain reels executes sur scenarios, climate, alarme et presence; le cas presence a justement servi de cas bord environnemental |
| PE9-AI-05 Discipline unifiee des artefacts figes | ⏳ Progres mais non parfait | discipline globalement tenue, mais `sprint-status.yaml` et certaines checklists story-level ont demande des realignements de closeout |

## Partie 2 — Preparation pe-epic-11

### Readiness

Le projet est pret a ouvrir `pe-epic-11`, maintenant que `pe-epic-10` est clos. Le backlog qualifie est deja documente et borne: energie / routage solaire, avec priorite explicite `P1 = MSunPV / RouteurSolaire (eq553)` puis `P2 = chauffe-eau detail (eq554)`. La difference importante avec l'epic 10 est que le prochain epic ne devrait pas exiger d'ouverture de nouveau type HA: `sensor`, `binary_sensor`, `button` et `switch` sont deja dans `PRODUCT_SCOPE`.

La bonne suite n'est donc pas un nouveau correct-course majeur de gouvernance type-par-type. La bonne suite est une ouverture propre d'epic axe usage/valeur, avec un premier incrément centre sur les signaux solaires lisibles pour la famille, puis un correctif/follow-up sur l'etat `unknown` du chauffe-eau.

### Triage avant / dans / apres pe-epic-11

| Placement | Items | Decision |
| --- | --- | --- |
| Prefixe pe-epic-11 | Story 11.1 `MSunPV / RouteurSolaire` | Demarrer par des `sensor` lecture seule a forte valeur visible, sans nouveau type HA a ouvrir. |
| Prefixe / debut pe-epic-11 | Diagnostic `switch.jeedom2ha_554 = unknown` | Traiter comme sujet distinct et borne, a ne pas melanger avec l'ouverture MSunPV. |
| Dans pe-epic-11 | Inventaire energie/routage | S'appuyer sur `backlog-icebox.md` pour les commandes et entites cibles eq553 / eq554. |
| Dans pe-epic-11 | Gate terrain metier | Verifier non seulement publication MQTT mais lisibilite des valeurs de routage sur le dashboard HA cible. |
| Reporte apres pe-epic-11 | IQ EV / priorisation solaire et autres composites | Garder separes tant que la promesse produit exacte n'est pas reframee story-level. |

## Action Items Priorises

| ID | Priorite | Titre | Owner | Target | Critere de sortie |
| --- | --- | --- | --- | --- | --- |
| PE10-AI-01 | P0 | Basculer `pe-epic-10` en `done` dans le tracker | Scrum Master | Closeout immediat | `sprint-status.yaml` marque `pe-epic-10: done` et `pe-epic-10-retrospective: done`. |
| PE10-AI-02 | P0 | Lancer `create-story` 11.1 sur `MSunPV / RouteurSolaire` | Scrum Master + Product Lead | Prochaine session BMAD | Story 11.1 creee avec scope borne eq553, sans melange avec eq554. |
| PE10-AI-03 | P1 | Isoler le bug chauffe-eau `unknown` de l'ouverture energie | Architect + Dev | pe-epic-11 prefixe / story dediee | Une story ou un sous-sujet distinct documente le diagnostic `switch.jeedom2ha_554` et evite de polluer 11.1. |
| PE10-AI-04 | P1 | Renforcer la hygiene des artefacts de closeout | Scrum Master + Dev | Prochain epic | Les commentaires `sprint-status` et les checklists Task 0/Task 5 sont realignes des la cloture story-level. |
| PE10-AI-05 | P2 | Introduire un pattern de waiver terrain explicite | Scrum Master + QA | Prochain epic / prochaines zones sensibles | Les stories a gate terrain sensible prevoient une sortie formelle quand le candidat live representatif n'existe pas sur la box. |

## Readiness Assessment

| Dimension | Statut | Notes |
| --- | --- | --- |
| Qualite / tests | Pret | Stories 10.x fermees avec preuves de tests et gates terrain documentes. |
| Gate terrain | Pret avec lecons claires | L'epic a montre a la fois des PASS reels et un cas de waiver explicite sur 10.7. |
| Gouvernance scope | Pret | `pe-epic-10` a tenu FR40 / NFR10 et n'a pas ouvert cosmetiquement les zones ambigues. |
| Dette bloquante | Limitee | Rien de bloquant pour ouvrir `pe-epic-11`; le principal suivi est d'hygiene tracker et de separation des sujets energie. |
| Backlog suivant | Pret | `pe-epic-11` est qualifie avec priorites et inventaire initial deja documentes. |

## Conclusion

`pe-epic-10` a rempli sa mission: convertir un delta Homebridge reel en vague HA utile, bornee et honnete. Il a ouvert `climate`, confirme et corrige la chaine scenario, aligne l'alarme native avec la realite des generics terrain, et cadre les zones composites ou sensibles sans sur-promesse. L'epic se clot sur une lecon utile pour la suite: la parite utile se gagne autant dans les details de terrain et de transport que dans l'ouverture de nouveaux mappers.

La prochaine bonne etape n'est plus un correct-course de cadrage. C'est l'ouverture propre de `pe-epic-11`, en commencant par une story 11.1 focalisee sur `MSunPV / RouteurSolaire`, puis un traitement separe du chauffe-eau `unknown`.

Bob (Scrum Master): "Retrospective complete. `pe-epic-10` est clos proprement. Prochaine etape recommandee: `create-story` 11.1 sur `MSunPV / RouteurSolaire`."
