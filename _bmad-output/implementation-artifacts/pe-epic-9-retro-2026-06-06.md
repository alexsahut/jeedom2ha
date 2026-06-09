# Retrospective pe-epic-9 — Vague 1 d'extension reelle (`sensor` / `binary_sensor` / `button`) + `FallbackMapper`

Date: 2026-06-06  
Projet: jeedom2ha  
Cycle actif: Moteur de projection explicable  
Facilitation: Bob (Scrum Master)  
Participant principal: Alexandre (Project Lead)

## Sources de verite analysees

- `_bmad-output/planning-artifacts/active-cycle-manifest.md`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `_bmad-output/planning-artifacts/ha-projection-reference.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/pe-epic-8-retro-2026-05-05.md`
- `_bmad-output/implementation-artifacts/9-0-decouplage-des-consommateurs-externes-de-mapping-summary-ui-jeedom-script-de-deploiement.md`
- `_bmad-output/implementation-artifacts/9-1-sensor-mapper-publish-sensor-info-numeric-et-capteurs-simples.md`
- `_bmad-output/implementation-artifacts/9-2-binary-sensor-mapper-publish-binary-sensor-info-binary-presence-ouverture-fuite.md`
- `_bmad-output/implementation-artifacts/9-3-button-mapper-publish-button-ouverture-button-dans-product-scope-sous-fr40-nfr10.md`
- `_bmad-output/implementation-artifacts/9-4-fallback-mapper-degradation-elegante-terminale-publier-sensor-button-par-defaut-plutot-que-skip-silencieux.md`
- `_bmad-output/implementation-artifacts/9-5-exposition-d-actions-utilisateur-sur-les-surfaces-reellement-ouvertes-par-la-vague-1-re-homee-depuis-7-5.md`
- `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`

## Synthese

`pe-epic-9` est clos et a tenu son contrat produit: ouvrir une premiere vague reelle de nouveaux composants Home Assistant au-dessus de l'infrastructure registry-driven livree par `pe-epic-8`, puis exposer des actions utilisateur seulement sur des surfaces reellement ouvertes par la vague 1. L'epic a ajoute `sensor`, `binary_sensor`, `button`, la degradation elegante terminale via `FallbackMapper`, puis la correction UX/metier `no faux CTA` sur les cas ambigus reellement remediables.

Le resultat epic-level tangible est net: passage d'une baseline terrain `278 eqLogics / 81 eligibles / 30 publies` documentee en retrospective `pe-epic-8` a `282 eqLogics / 82 eligibles / 71 publies / 71 topics discovery` observes au gate final Story 9.5. La valeur importante n'est pas seulement quantitative. La vague 1 a montre que le pipeline peut maintenant ouvrir des composants HA supplementaires sans retoucher la boucle centrale ni casser le corpus historique du golden-file.

Bob (Scrum Master): "Epic 9 n'a pas juste ajoute des types. Il a prouve que l'ouverture incrementale gouvernee par registre, golden-file et gate terrain tient vraiment sur une box reelle."

Winston (Architect): "La promesse de `pe-epic-8` etait structurelle. `pe-epic-9` l'a convertie en couverture produit observable sans regression du dispatch."

Dana (QA Engineer): "Le vrai signal positif, c'est qu'on a garde la discipline de non-regression tout en etendant discovery, diagnostic et UX."

## Partie 1 — Epic Review

### Etat de livraison

| Story | Resultat principal | Preuve de qualite |
| --- | --- | --- |
| 9.0 Prefixe totals dynamiques | decouplage des consommateurs externes de `mapping_summary` avant ouverture de nouveaux types | cloture `done`; prerequis `PE8-AI-01` et `PE8-AI-02` absorbes |
| 9.1 SensorMapper | ouverture `sensor` sur infos numeric et capteurs simples | gate terrain PASS; discipline golden-file explicite |
| 9.2 BinarySensorMapper | ouverture `binary_sensor` sur presence, ouverture, fuite et cas voisins | code review presente; gate terrain PASS |
| 9.3 ButtonMapper | ouverture `button` sous FR40 / NFR10 | gate terrain PASS; `PRODUCT_SCOPE` ouvert dans la story prevue |
| 9.4 FallbackMapper | degradation elegante terminale via `publish_sensor` / `publish_button` plutot que skip silencieux | gate terrain PASS; corpus golden-file etendu |
| 9.5 CTA honnetes | exposition d'actions utilisateur uniquement sur surfaces reelles de la vague 1 + fix `no_projection_possible` | 733/733 PASS; gate terrain final PASS avec `published=71`, `discovery topics=71` |

### Ce qui a bien fonctionne

- L'epic a garde une extension incrementale tres disciplinee: `9.0` pour nettoyer les consommateurs externes, puis ouverture sequentielle `sensor` -> `binary_sensor` -> `button` -> `fallback` -> CTA sur surfaces reelles.
- Les action items critiques de `pe-epic-8` ont ete reellement absorbes dans l'execution: totals dynamiques, inspection propre des types connus, extension disciplinee du golden-file, gate terrain compare a la baseline precedente.
- La culture de non-regression a tenu sur tout l'epic: les stories etendent le golden-file au lieu de regenerer opportunistement le snapshot historique, et les suites de tests restent le garde-fou normal avant terrain.
- Le gate terrain est reste une pratique d'execution, pas un rituel decoratif. Il a accompagne l'ouverture produit a chaque story et a servi de preuve de cloture epic-level sur la box reelle.
- La regle metier `no faux CTA` a ete preservee jusqu'au bout: `sensor` / `binary_sensor` / `button` sans remediation reelle gardent `cause_action = null`, tandis que les cas `ambiguous_skipped` re-homes depuis le fallback recoivent une remediaton executable dans Jeedom.

### Ce qui a moins bien fonctionne

- Le principal risque recurrent n'etait plus dans les mappers eux-memes mais dans les zones peripheriques: compteurs externes, `_resolve_state_topic`, normalisation des `reason_code`, mapping de `cause_action`, snapshots et tests de diagnostic.
- Plusieurs changements apparemment locaux ont eu des effets transverses sur publication, diagnostic et tests herites. L'epic montre que la complexite s'est deplacee de la boucle centrale vers l'orchestration et la coherence inter-couches.
- Le fallback a apporte une vraie progression produit, mais a cree une zone de vigilance UX: il faut continuer a distinguer "publier par defaut" d'un vrai cas publiable nominal et garder une justification honnete des CTA.
- Le sous-cas `no_projection_possible` n'a pas ete observe en live pendant le gate final de 9.5. Il est correctement couvert par tests, mais la preuve terrain reelle reste plus faible sur ce cas que sur les cas nominaux et ambigus.

### Lecons apprises

- Une vague "nouveau type HA" ne touche jamais seulement un mapper et un publisher. Elle impacte aussi compteurs externes, topics, taxonomie de diagnostic, golden-file, tests d'orchestration et protocole terrain.
- La centralisation par registres et conventions uniques a vraiment paye: des que la logique est sortie des listes hardcodees, l'epic a gagne en robustesse et en lisibilite.
- Le golden-file incrementiel reste le bon verrou de regression, mais il doit etre pense en tandem avec les artefacts UX/diagnostic, pas seulement avec le snapshot de sync.
- Le terrain doit continuer a verifier des cas bords representatifs, pas seulement des cas nominaux, sinon certains defauts de diagnostic restent visibles seulement en CI.

### Continuite avec la retrospective pe-epic-8

| Action item pe-epic-8 | Etat dans pe-epic-9 | Observation |
| --- | --- | --- |
| PE8-AI-01 Totaux publies UI dynamiques | ✅ Solde | absorbe par Story 9.0 |
| PE8-AI-02 Total publie script terrain dynamique | ✅ Solde | absorbe par Story 9.0 |
| PE8-AI-03 API propre `PublisherRegistry.known_types()` | ✅ Solde | absorbe par Story 9.1 |
| PE8-AI-04 Extension disciplinee du golden-file | ✅ Solde | tenue sur 9.1 a 9.5 |
| PE8-AI-05 Gate terrain avec baseline | ✅ Solde | confirme jusqu'au gate final 9.5 |
| PE8-AI-06 Garder 9.5 apres surfaces reelles | ✅ Solde | execute proprement apres ouverture reelle de la vague 1 |
| PE8-AI-07 Backlog vagues suivantes depuis reference HA | ⏳ Reporte | reste le vrai sujet de `pe-epic-10+` |

## Partie 2 — Preparation pe-epic-10+

### Readiness

Le projet est pret a ouvrir une vague ulterieure, mais il n'existe pas encore de `pe-epic-10` materialise dans le sprint actif. Les artefacts actifs convergent: les 25 composants HA restants relevent de vagues `pe-epic-10+`, toujours derivees de `ha-projection-reference.md` et toujours gouvernees story-par-story sous FR40 / NFR10.

La bonne suite n'est donc pas de creer une story de dev isolee. La bonne suite est un recadrage produit/process pour choisir la prochaine vague, puis seulement la materialiser dans le backlog executable.

### Triage avant / dans / apres pe-epic-10+

| Placement | Items | Decision |
| --- | --- | --- |
| Avant pe-epic-10 | Correct-course post-vague 1 | Definir la prochaine vague depuis `ha-projection-reference.md`, FR40 et NFR10, au lieu d'ouvrir opportunistement un type. |
| Prefixe du prochain epic | Checklist "nouveau type" | Poser des la story 0 la checklist complete: mapper, publisher, `known_types`, topics, compteurs, diagnostic UX, golden-file, tests, terrain. |
| Dans le prochain epic | Matrice d'impact transversale | Externaliser les zones qui cassent lorsqu'un type est ajoute: discovery, diagnostic, state/command topic, consumers externes, fixtures, terrain. |
| Dans le prochain epic | Cas bords terrain obligatoires | Ajouter quelques cas "ambigus", "fallback", "no_projection_possible" ou equivalents au protocole terrain, pas seulement des cas nominaux. |
| Reporte apres cadrage | Choix de la vague suivante | `number`, `select`, `climate` et les autres composants hors vague 1 restent a prioriser explicitement, pas a ouvrir par glissement de scope. |

## Action Items Priorises

| ID | Priorite | Titre | Owner | Target | Critere de sortie |
| --- | --- | --- | --- | --- | --- |
| PE9-AI-01 | P0 | Correct-course `pe-epic-10+` depuis la reference HA | Product Owner + Scrum Master + Architect | Prochain recadrage BMAD | Une prochaine vague est choisie explicitement depuis `ha-projection-reference.md`, avec guardrails FR40 / NFR10 cites dans le cadrage. |
| PE9-AI-02 | P0 | Checklist canonique "nouveau type HA" | Dev + QA + Architect | Prefixe du prochain epic | Toute ouverture de type passe par une checklist unique couvrant mapper, publisher, `known_types`, topics, compteurs, diagnostic, golden-file, tests et terrain. |
| PE9-AI-03 | P1 | Matrice d'impact transversale des ouvertures produit | Architect + Dev | Prefixe du prochain epic | Un artefact partageable liste ce qu'un ajout de type touche reellement, pour ne plus dependre de memoire projet implicite. |
| PE9-AI-04 | P1 | Pack terrain cas bords du diagnostic | QA + Alexandre | Prochain epic | Le protocole terrain integre au moins quelques cas limites de diagnostic, et pas seulement les cas nominaux de publication. |
| PE9-AI-05 | P2 | Discipline unifiee des artefacts figes | Dev + QA | Prochain epic | Les regles de modification de `cause_mapping` et du golden-file sont explicites, afin de limiter les oublis de synchronisation entre code, tests et UX. |

## Readiness Assessment

| Dimension | Statut | Notes |
| --- | --- | --- |
| Qualite / tests | Pret | 9.5 cloture avec 733/733 PASS et corpus precedent preserve. |
| Gate terrain | Pret | preuve reelle disponible jusqu'au gate epic-level final (`published=71`, `discovery topics=71`). |
| Gouvernance scope | Pret avec vigilance | `button` a bien ete ouvert dans sa story gouvernee; la suite doit garder la meme discipline FR40 / NFR10. |
| Dette bloquante | Limitee | rien ne bloque techniquement, mais la prochaine vague doit etre recadree avant execution. |
| Backlog suivant | A cadrer | `pe-epic-10+` existe en intention dans les artefacts, pas encore en backlog executable. |

## Conclusion

`pe-epic-9` a rempli sa mission: convertir l'infrastructure extensible de `pe-epic-8` en premiere vague produit reelle, sans casser le dispatch, le golden-file ni la regle metier `no faux CTA`. Le projet sort de cet epic avec une couverture nettement superieure et une preuve terrain solide.

La lecon principale pour la suite est simple: le prochain epic ne doit pas seulement choisir un nouveau composant HA, il doit aussi industrialiser la methode d'ouverture d'un type. Tant que cette checklist transverse n'est pas explicite, chaque nouvelle vague continuera a payer un cout de redecouverte inutile.

Bob (Scrum Master): "Retrospective complete. `pe-epic-9` est clos proprement. La prochaine bonne etape n'est pas une story de dev isolee, c'est un `correct-course` pour choisir et cadrer `pe-epic-10+`."
