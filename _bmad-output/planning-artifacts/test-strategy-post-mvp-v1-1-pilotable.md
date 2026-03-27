---
document_type: test_strategy_addendum
project: jeedom2ha
phase: post_mvp_phase_1
version_label: v1_1_pilotable
date: 2026-03-27
status: realigned_with_recadrage_ux
base_strategy:
  - _bmad-output/test-artifacts/test-design-architecture.md
  - _bmad-output/test-artifacts/test-design-qa.md
active_inputs:
  - _bmad-output/planning-artifacts/active-cycle-manifest.md
  - _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-03-22.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-26.md
revision_history:
  - date: 2026-03-27
    changes: "Recadrage UX — realignement sur le modele utilisateur 4D (Perimetre/Statut/Ecart/Cause), structure a 5 epics, contrat dual reason_code/cause_code, obligations de couverture compteurs et ecart bidirectionnel."
  - date: 2026-03-22
    changes: "Creation initiale — addendum delta V1.1 sur la strategie de test MVP."
notes:
  - Addendum delta: la strategie MVP reste le socle de non-regression.
  - Le fichier /mnt/data/test-design-architecture.md n'etait pas present; la base MVP locale equivalente a ete utilisee.
  - Le readiness report actif reste le 2026-03-22 conformement au manifeste du cycle actif.
---

# Strategie de test addendum - Post-MVP V1.1 Pilotable

## 1. Executive summary

La V1.1 Pilotable ne remplace pas la strategie de test MVP. Elle la **rebranche explicitement** comme socle de non-regression, puis ajoute les obligations de couverture liees au nouveau contrat produit.

Le Sprint Change Proposal du 2026-03-26 (approuve) a recadre le modele utilisateur V1.1 autour de **4 dimensions: Perimetre → Statut → Ecart → Cause**. Ce recadrage a entraine la mise a jour du PRD, de l'UX delta review, de l'architecture delta review et des epics. Le cycle actif comporte desormais **5 epics**: Epics 1-3 (livres — resolver, sante, reason_code), Epic 4 (backlog — recadrage UX, modele 4D, contrat dual reason_code/cause_code), Epic 5 (backlog — operations HA explicites).

La strategie de test s'aligne sur ce recadrage en ajoutant les obligations de couverture sur: **le contrat backend 4D, le contrat dual reason_code/cause_code, les compteurs backend pre-calcules, l'ecart bidirectionnel, le filtrage diagnostic in-scope, l'absence de logique metier dans le frontend, et la disparition du concept d'exception**.

La regle directrice reste: on conserve l'approche MVP **backend-first, majoritairement unitaire et integration backend**, et on ajoute en delta des tests contractuels sur les invariants V1.1 recadres. Les tests UI restent cibles et ne deviennent obligatoires que lorsqu'une story modifie un contrat visible critique. Le frontend est en **lecture seule** du contrat backend — il ne calcule pas, ne derive pas, ne recompose pas.

## 2. Base conservee depuis la strategie de test MVP

Les points suivants restent valides et doivent continuer a tourner comme base de non-regression:

- Le coeur de protection reste `unit + integration backend`, pas des E2E lourds avec un vrai HA.
- Les suites MVP existantes sur mapping, publication MQTT Discovery, cycle de vie, diagnostic, exclusions, rescan et stabilite des identifiants restent obligatoires.
- La logique critique continue d'etre testee avec mocks HTTP/MQTT et assertions deterministes sur les payloads et decisions.
- La politique produit conservee reste: **mieux vaut ne pas publier que publier faux**.
- Les harness existants dans `tests/` et `resources/daemon/tests/` sont la base a etendre; on n'ouvre pas une pile de tests parallele pour V1.1.
- Les checks manuels sur box / vrai HA restent du sanity check de release, pas la preuve principale sur PR.

## 3. Delta V1.1 : risques a couvrir

Les risques prioritaires du cycle actif ne portent pas sur "plus de domaines", mais sur des contrats nouveaux et le recadrage du modele utilisateur.

### Risques conserves (mis a jour)

- **Risque de scope implicite**: la hierarchie `global -> piece -> equipement` devient produit. Elle doit etre testee comme un resolver deterministe, pas comme un effet de l'UI. Les compteurs backend pre-calcules (Total, Inclus, Exclus, Ecarts) doivent etre valides comme consequence directe de la resolution.
- **Risque de precedence incoherente**: `equipement > piece > global` doit etre prouve sur les cas limites, notamment les exclusions par source (exclu par la piece, exclu par le plugin, exclu sur cet equipement).
- **Risque de derive semantique**: le frontend ne doit pas reinventer les 4 dimensions du modele utilisateur (`perimetre`, `statut`, `ecart`, `cause_code`/`cause_label`). Le contrat dual `reason_code` (backend stable) / `cause_code`+`cause_label` (contrat UI canonique) doit rester etanche.
- **Risque destructif HA**: `Republier` ne doit jamais glisser vers un flux destructif cache; `Supprimer/Recreer` doit rester le seul flux destructif explicite.
- **Risque de confusion operatoire**: une decision locale de perimetre ne doit pas etre confondue avec son application effective a Home Assistant. L'ecart bidirectionnel est le signal du desalignement entre les deux.
- **Risque support**: `Derniere operation` et la sante minimale doivent etre suffisamment stables pour qualifier un incident sans lire les logs bruts.
- **Risque d'invariants HA casses**: `unique_id`, comportement deterministe du scope et effets de cycle de vie ne doivent pas etre affaiblis par V1.1.

### Risques ajoutes par le recadrage UX

- **Risque de fuite logique metier dans le frontend**: le frontend calcule localement un compteur, derive un statut a partir d'autres champs, ou recompose une cause a partir de `cause_code`. Le contrat V1.1 exige que le backend fournisse les 4 dimensions et les compteurs pre-calcules; le frontend affiche sans interpreter.
- **Risque de confusion reason_code / cause_code**: un changement de `cause_code` impacte un `reason_code` stable, ou un `reason_code` est expose directement en UI. Les deux couches doivent rester distinctes et testables en isolation.
- **Risque de reintroduction du concept exception**: vocabulaire d'implementation (`inherit`, `exception locale`, `decision_source`, `is_exception`) qui revient dans l'interface utilisateur. L'UI ne doit exposer que les exclusions par source.
- **Risque d'ecart unidirectionnel**: ne couvrir que la direction 1 (inclus mais non publie) et oublier la direction 2 (exclu mais encore publie). Les deux directions doivent etre prouvees dans les tests d'integration backend.
- **Risque de Partiellement publie comme statut principal**: reintroduction de `Partiellement publie` dans la console comme statut de lecture au lieu de le cantonner a un indicateur de diagnostic detaille de couverture.

## 4. Invariants contractuels a tester

Les invariants suivants deviennent **systematiques** pour les stories V1.1 qui touchent le perimetre, les statuts, la sante ou les operations.

### Invariants conserves (mis a jour)

1. Le modele canonique est bien `global -> piece -> equipement`.
2. La resolution suit explicitement `equipement > piece > global`.
3. Les etats internes supportes pour `piece` et `equipement` sont `inherit / include / exclude`.
4. Le backend est la source unique des 4 dimensions du contrat UI (`perimetre`, `statut`, `ecart`, `cause_code`/`cause_label`/`cause_action`) ainsi que des compteurs pre-calcules et de la sante minimale.
5. `Republier` est non destructif par contrat.
6. `Supprimer/Recreer` est le seul flux destructif explicite.
7. La decision locale de perimetre et l'application effective a HA restent deux concepts distincts. L'ecart bidirectionnel est le signal du desalignement entre les deux.
8. `Derniere operation` est obligatoire dans le contrat visible V1.1.
9. Les invariants HA sensibles restent proteges: `unique_id` stable tant que l'ID Jeedom est stable, recalcul du scope deterministe pour un snapshot et une configuration donnes, effets MQTT/Discovery non regressifs.

### Invariants ajoutes par le recadrage UX

10. Le contrat backend → UI est le modele a 4 dimensions: `perimetre`, `statut`, `ecart`, `cause_code`/`cause_label`/`cause_action`. C'est le seul modele de lecture de la console.
11. Le statut binaire `Publie` / `Non publie` n'existe qu'au niveau equipement. Les niveaux piece et global ne portent pas de statut agrege reutilisant ce champ.
12. Les niveaux piece et global sont lus via des compteurs backend pre-calcules: Total, Inclus, Exclus, Ecarts. Invariant arithmetique obligatoire: `Total = Inclus + Exclus`. Le compteur `Ecarts` couvre les deux directions (inclus mais non publie ET exclu mais encore publie).
13. L'ecart est un booleen bidirectionnel pre-calcule par le backend (comparaison decision effective ↔ etat projete HA). Les 4 cas de la matrice doivent etre prouves: inclus/publie=non, inclus/non-publie=oui, exclu/non-publie=non, exclu/publie=oui.
14. Le diagnostic utilisateur est filtre in-scope (`perimetre = inclus`) cote backend. Les exclus restent visibles dans la synthese de perimetre mais ne produisent pas d'entree diagnostic detaillee.
15. La confiance (`Sur`/`Probable`/`Ambigu`) n'apparait pas en console principale — diagnostic technique uniquement.
16. `reason_code` (backend stable, non expose en UI) ≠ `cause_code`/`cause_label` (contrat UI canonique, derive par table de correspondance — fonction pure). Les deux couches sont distinctes et testables en isolation.
17. Le frontend ne fait aucune interpretation: pas de calcul de compteurs, pas de derivation de statut, pas de mapping local, pas de recomposition de cause. Il affiche les 4 dimensions telles quelles.
18. Le concept d'exception a disparu de l'UI. Les exclusions sont exprimees par leur source uniquement: `exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement`. `inherit` n'apparait jamais dans la reponse API.

## 5. Niveaux de tests recommandes

### Unitaires

A exiger des tests unitaires des que la story touche:

- le resolver de perimetre `global / piece / equipement`;
- la matrice `inherit / include / exclude`;
- la precedence `equipement > piece > global`;
- la classification `Republier` vs `Supprimer/Recreer`;
- la production du resume `Derniere operation`;
- la table de traduction `reason_code` → `cause_code`/`cause_label` (fonction pure, testable en isolation);
- le calcul du booleen `ecart` (comparaison decision effective ↔ etat projete);
- la traduction de la resolution interne en source d'exclusion lisible (`inclus`, `exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement`).

### Integration backend

A exiger quand la story touche un endpoint, une facade backend, le daemon, le polling UI-backed ou le cycle de vie HA:

- mutation de perimetre et recalcul effectif;
- exposition de la sante minimale;
- retour d'operation global / piece / equipement;
- gating d'action HA si bridge ou MQTT indisponible;
- publication, depublication, cleanup, reapplication apres changement de scope;
- **ecart bidirectionnel**: prouver les 4 cas de la matrice decision×etat (inclus/publie=non, inclus/non-publie=oui, exclu/non-publie=non, exclu/publie=oui);
- **agregation compteurs**: prouver que les compteurs backend par piece et globaux respectent `Total = Inclus + Exclus` et que `Ecarts` couvre les deux directions d'ecart;
- **filtrage diagnostic in-scope**: prouver que le diagnostic utilisateur ne contient que les equipements avec `perimetre = inclus`;
- **contrat 4D complet**: prouver que le payload backend par equipement contient les 4 dimensions (`perimetre`, `statut`, `ecart`, `cause_code`/`cause_label`/`cause_action`) et les compteurs par piece/global.

### Tests de contrat / non-regression

Ils sont obligatoires sur les zones V1.1 sensibles:

- schema et champs stables des payloads backend servant la console, conformes au modele 4D verrouille;
- presence de `Derniere operation`;
- stabilite des `reason_code` quand une story touche la semantique des statuts ou ajoute/modifie un `cause_code`;
- non-regression des invariants MVP deja couverts: mapping conservateur, retained delete, lifecycle, `unique_id`, exclusions existantes;
- preuve que `Republier` n'emprunte pas le chemin destructif reserve a `Supprimer/Recreer`;
- preuve que `inherit` n'apparait jamais dans la reponse API (toujours resolu avant serialisation);
- preuve que le contrat dual `reason_code`/`cause_code` reste etanche: aucun `reason_code` expose en UI, aucun `cause_code` qui modifie un `reason_code` stable.

### Tests UI cibles si necessaire

Seulement si la story modifie un contrat visible critique:

- affichage du perimetre par source d'exclusion (`Inclus`, `Exclu par la piece`, `Exclu par le plugin`, `Exclu sur cet equipement`);
- lecture seule du contrat backend 4D: le frontend ne calcule pas, ne derive pas, ne recompose pas;
- absence de termes interdits en UI (`inherit`, `exception locale`, `decision_source`, `is_exception`, `Partiellement publie` comme statut principal, `Ambigu` comme statut, `Non supporte` comme statut, compteur `Exceptions`);
- distinction visible `Republier` vs `Supprimer puis recreer`;
- contenu minimum des confirmations destructives;
- visibilite du bandeau de sante minimale et de `Derniere operation`;
- blocage visible des actions HA quand l'infrastructure ne le permet pas;
- confiance absente de la console principale (visible uniquement en diagnostic technique).

Pas de campagne E2E exhaustive par defaut pour V1.1.

## 6. Regles de non-regression

### Regles conservees

- Une story V1.1 ne passe pas si elle casse une suite MVP existante sur mapping, lifecycle, exclusions, diagnostic ou publication MQTT.
- Toute modification d'un contrat backend visible doit ajouter un test de contrat ou mettre a jour explicitement le contrat attendu.
- Toute story touchant le scope doit prouver le determinisme du recalcul pour un meme snapshot et une meme configuration.
- Toute story touchant les operations HA doit prouver que `Republier` reste non destructif et que `Supprimer/Recreer` reste l'unique flux destructif utilisateur.
- Toute story touchant la semantique des statuts doit prouver que la logique reste cote backend et ne migre pas dans le frontend.

### Regles ajoutees par le recadrage UX

- Toute story V1.1 ne passe pas si le frontend calcule un compteur, derive un statut, ou recompose une cause a partir de champs backend.
- Toute story touchant le vocabulaire UI doit prouver l'absence de termes interdits: `inherit`, `exception locale`, `decision_source`, `is_exception`, `Partiellement publie` comme statut principal, `Ambigu` comme statut, `Non supporte` comme statut, compteur `Exceptions`.
- Toute story ajoutant ou modifiant un `cause_code`/`cause_label` doit prouver que le `reason_code` source reste stable et non expose en UI.
- Toute story touchant les compteurs piece/global doit prouver l'invariant arithmetique `Total = Inclus + Exclus` et que le compteur `Ecarts` couvre les deux directions (inclus mais non publie ET exclu mais encore publie).

## 7. Ce qui doit etre exige dans les futures stories

Chaque story V1.1 doit expliciter, dans ses Dev Notes et ses AC:

- quels invariants V1.1 elle touche (parmi les invariants 1-18);
- quels tests unitaires sont obligatoires;
- quels tests d'integration backend sont obligatoires;
- quels tests de contrat / non-regression sont obligatoires;
- si un test UI cible est requis ou explicitement non requis;
- quels contrats MVP doivent rester intacts.

### Exigences specifiques par epic

**Stories Epic 4 (recadrage UX)** — doivent en plus:
- prouver la traduction `reason_code` → `cause_code`/`cause_label` (invariant 16);
- prouver la forme 4D du contrat JSON backend → UI (invariant 10);
- prouver les compteurs pre-calcules par piece et global (invariant 12);
- prouver le filtrage in-scope du diagnostic (invariant 14);
- prouver l'absence de vocabulaire interdit en UI (invariant 18);
- prouver que `Partiellement publie` n'apparait pas comme statut principal de console.

**Stories Epic 5 (operations HA)** — doivent en plus:
- consommer le modele 4D stabilise par Epic 4 dans les reponses d'operation;
- prouver les invariants HA (Republier non destructif, Supprimer/Recreer seul flux destructif);
- prouver le gating des actions par l'etat du pont;
- prouver que les confirmations graduees rappellent la portee, le volume et les consequences HA.

### Critere de readiness

Une story n'est pas "ready-for-dev" si elle parle d'UI, d'operations ou de statuts sans nommer le backend comme source de verite, le contrat 4D comme modele de lecture, le contrat dual reason_code/cause_code comme regle d'etancheite, et la preuve de non-regression attendue.

## 8. Ce qui peut rester hors scope test a ce stade

Peut rester hors scope V1.1, sauf story qui le demande explicitement:

- plan de test exhaustif story par story;
- E2E complet avec vrai Jeedom + vrai Home Assistant sur chaque PR;
- couverture de preview complete, remediations guidees avancees ou sante avancee;
- matrice navigateur/mobile etendue;
- extension fonctionnelle `button / number / select / climate`, hors non-regression du comportement actuel de non-support.

## 9. Recommandation d'usage dans les prochains workflows BMAD

### Pour Epic 4 (recadrage UX)

- **`create-story`**: citer cet addendum plus la base MVP, puis injecter dans chaque story les invariants touches (parmi I10-I18 prioritairement) et le minimum de tests par niveau. Exiger la preuve de la traduction reason→cause, de la forme 4D du contrat, des compteurs, du filtrage in-scope et de l'absence de termes interdits. Ne pas produire de story Epic 4 "neutre" sur les tests.
- **`validate-story`**: refuser une story Epic 4 si elle n'identifie pas clairement le contrat backend 4D, les invariants recadrage touches, le contrat dual reason_code/cause_code, et le minimum de non-regression attendu.

### Pour Epic 5 (operations HA)

- **`create-story`**: citer cet addendum plus la base MVP, puis injecter les invariants HA (I5-I9) et l'obligation que les reponses d'operation consomment le contrat 4D stabilise par Epic 4. Ne pas produire de story Epic 5 "neutre" sur les tests.
- **`validate-story`**: refuser une story Epic 5 si elle n'identifie pas clairement la facade backend unique, l'intention et la portee, les invariants HA, la non-destruction de `Republier` quand pertinent, les confirmations graduees, et le minimum de non-regression attendu.

### Pour tous les epics

- **`dev-story`**: implementer les tests dans le meme changement que la fonctionnalite, en etendant d'abord les suites `pytest` / PHP existantes. Les tests UI ne viennent qu'en complement sur les contrats visibles critiques.

## 10. Ambiguite residuelle

**Partiellement publie en diagnostic detaille**: les artefacts amont verrouillent que `Partiellement publie` n'est pas un statut principal de console et qu'il reste un "indicateur de diagnostic detaille de couverture" (Sprint Change Proposal D9, UX §6.2). En revanche, aucun artefact ne specifie encore le mecanisme technique exact qui le porte (quel champ, quel `cause_code`, quel seuil de couverture commandes). Ce point releve de la specification story-level Epic 4. La strategie de test le marque comme **obligation de testabilite a specifier lors du `create-story`** sans bloquer le realignement.

## 11. Resume ultra court reutilisable dans les prompts

V1.1 Pilotable = **addendum** a la strategie MVP, pas remplacement. 5 epics (1-3 livres, 4 recadrage UX, 5 operations HA). Garder la base MVP de non-regression (`unit + integration backend`, mapping/lifecycle/diagnostic/exclusions/`unique_id`) et ajouter les preuves V1.1 recadrees sur: modele 4D **Perimetre/Statut/Ecart/Cause** comme contrat unique backend → UI, contrat dual `reason_code` (backend stable, non expose UI) / `cause_code`+`cause_label` (contrat UI canonique), compteurs backend pre-calcules (Total/Inclus/Exclus/Ecarts, `Total = Inclus + Exclus`), ecart bidirectionnel (inclus-non-publie ET exclu-encore-publie), statut binaire Publie/Non publie au niveau equipement uniquement, diagnostic filtre in-scope cote backend, confiance hors console principale, frontend en lecture seule (pas de calcul, pas de derivation, pas de mapping local), disparition du concept exception (exclusions par source uniquement), `Republier` non destructif, `Supprimer/Recreer` seul flux destructif, separation scope local vs application HA, `Derniere operation` obligatoire, invariants HA deterministes. UI tests seulement cibles si la story modifie un contrat visible critique.
