---
document_type: test_strategy_addendum
project: jeedom2ha
phase: post_mvp_phase_1
version_label: v1_1_pilotable
date: 2026-03-22
status: ready_for_story_workflows
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
notes:
  - Addendum delta: la strategie MVP reste le socle de non-regression.
  - Le fichier /mnt/data/test-design-architecture.md n'etait pas present; la base MVP locale equivalente a ete utilisee.
---

# Strategie de test addendum - Post-MVP V1.1 Pilotable

## 1. Executive summary

La V1.1 Pilotable ne remplace pas la strategie de test MVP. Elle la **rebranche explicitement** comme socle de non-regression, puis ajoute les obligations de couverture liees au nouveau contrat produit: **perimetre pilotable, operations HA explicites, statuts backend unifies et sante minimale visible**.

La regle directrice est simple: on conserve l'approche MVP **backend-first, majoritairement unitaire et integration backend**, et on ajoute en delta des tests contractuels sur les invariants V1.1. Les tests UI restent cibles et ne deviennent obligatoires que lorsqu'une story modifie la lisibilite, la gradation des confirmations ou le gating des actions.

## 2. Base conservee depuis la strategie de test MVP

Les points suivants restent valides et doivent continuer a tourner comme base de non-regression:

- Le coeur de protection reste `unit + integration backend`, pas des E2E lourds avec un vrai HA.
- Les suites MVP existantes sur mapping, publication MQTT Discovery, cycle de vie, diagnostic, exclusions, rescan et stabilite des identifiants restent obligatoires.
- La logique critique continue d'etre testee avec mocks HTTP/MQTT et assertions deterministes sur les payloads et decisions.
- La politique produit conservee reste: **mieux vaut ne pas publier que publier faux**.
- Les harness existants dans `tests/` et `resources/daemon/tests/` sont la base a etendre; on n'ouvre pas une pile de tests parallele pour V1.1.
- Les checks manuels sur box / vrai HA restent du sanity check de release, pas la preuve principale sur PR.

## 3. Delta V1.1 : nouveaux risques a couvrir

Les risques prioritaires du cycle actif ne portent pas sur "plus de domaines", mais sur des contrats nouveaux:

- **Risque de scope implicite**: la hierarchie `global -> piece -> equipement` devient produit. Elle doit donc etre testee comme un resolver deterministe, pas comme un effet de l'UI.
- **Risque de precedence incoherente**: `equipement > piece > global` doit etre prouve sur les cas limites, notamment les exceptions locales.
- **Risque de derive semantique**: le frontend ne doit pas reinventer `statut`, `raison principale`, `action recommandee` ou `sante minimale`.
- **Risque destructif HA**: `Republier` ne doit jamais glisser vers un flux destructif cache; `Supprimer/Recreer` doit rester le seul flux destructif explicite.
- **Risque de confusion operatoire**: une decision locale de perimetre ne doit pas etre confondue avec son application effective a Home Assistant.
- **Risque support**: `Derniere operation` et la sante minimale doivent etre suffisamment stables pour qualifier un incident sans lire les logs bruts.
- **Risque d'invariants HA casses**: `unique_id`, comportement deterministe du scope et effets de cycle de vie ne doivent pas etre affaiblis par V1.1.

## 4. Invariants contractuels a tester

Les invariants suivants deviennent **systematiques** pour les stories V1.1 qui touchent le perimetre, les statuts, la sante ou les operations:

1. Le modele canonique est bien `global -> piece -> equipement`.
2. La resolution suit explicitement `equipement > piece > global`.
3. Les etats supportes pour `piece` et `equipement` sont `inherit / include / exclude`.
4. Le backend est la source unique de `statut`, `raison principale`, `action recommandee` et `sante minimale`.
5. `Republier` est non destructif par contrat.
6. `Supprimer/Recreer` est le seul flux destructif explicite.
7. La decision locale de perimetre et l'application effective a HA restent deux concepts distincts.
8. `Derniere operation` est obligatoire dans le contrat visible V1.1.
9. Les invariants HA sensibles restent proteges: `unique_id` stable tant que l'ID Jeedom est stable, recalcul du scope deterministe pour un snapshot et une configuration donnes, effets MQTT/Discovery non regressifs.

## 5. Niveaux de tests recommandes

### Unitaires

A exiger des tests unitaires des que la story touche:

- le resolver de perimetre `global / piece / equipement`;
- la matrice `inherit / include / exclude`;
- la precedence `equipement > piece > global`;
- la classification `Republier` vs `Supprimer/Recreer`;
- la normalisation `statut / raison principale / action recommandee`;
- la production du resume `Derniere operation`.

### Integration backend

A exiger quand la story touche un endpoint, une facade backend, le daemon, le polling UI-backed ou le cycle de vie HA:

- mutation de perimetre et recalcul effectif;
- exposition de la sante minimale;
- retour d'operation global / piece / equipement;
- gating d'action HA si bridge ou MQTT indisponible;
- publication, depublication, cleanup, reapplication apres changement de scope.

### Tests de contrat / non-regression

Ils sont obligatoires sur les zones V1.1 sensibles:

- schema et champs stables des payloads backend servant la console;
- presence de `Derniere operation`;
- stabilite des `reason_code` quand une story touche la semantique des statuts;
- non-regression des invariants MVP deja couverts: mapping conservateur, retained delete, lifecycle, `unique_id`, exclusions existantes;
- preuve que `Republier` n'emprunte pas le chemin destructif reserve a `Supprimer/Recreer`.

### Tests UI cibles si necessaire

Seulement si la story modifie un contrat visible critique:

- affichage de la source de decision (`heritage` / `exception locale`);
- distinction visible `Republier` vs `Supprimer puis recreer`;
- contenu minimum des confirmations destructives;
- visibilite du bandeau de sante minimale et de `Derniere operation`;
- blocage visible des actions HA quand l'infrastructure ne le permet pas.

Pas de campagne E2E exhaustive par defaut pour V1.1.

## 6. Regles de non-regression

- Une story V1.1 ne passe pas si elle casse une suite MVP existante sur mapping, lifecycle, exclusions, diagnostic ou publication MQTT.
- Toute modification d'un contrat backend visible doit ajouter un test de contrat ou mettre a jour explicitement le contrat attendu.
- Toute story touchant le scope doit prouver la determinisme du recalcul pour un meme snapshot et une meme configuration.
- Toute story touchant les operations HA doit prouver que `Republier` reste non destructif et que `Supprimer/Recreer` reste l'unique flux destructif utilisateur.
- Toute story touchant la semantique des statuts doit prouver que la logique reste cote backend et ne migre pas dans le frontend.

## 7. Ce qui doit etre exige dans les futures stories

Chaque story V1.1 doit expliciter, dans ses Dev Notes et ses AC:

- quels invariants V1.1 elle touche;
- quels tests unitaires sont obligatoires;
- quels tests d'integration backend sont obligatoires;
- quels tests de contrat / non-regression sont obligatoires;
- si un test UI cible est requis ou explicitement non requis;
- quels contrats MVP doivent rester intacts.

Une story n'est pas "ready-for-dev" si elle parle d'UI, d'operations ou de statuts sans nommer le backend comme source de verite ni la preuve de non-regression attendue.

## 8. Ce qui peut rester hors scope test a ce stade

Peut rester hors scope V1.1, sauf story qui le demande explicitement:

- plan de test exhaustif story par story;
- E2E complet avec vrai Jeedom + vrai Home Assistant sur chaque PR;
- couverture de preview complete, remediations guidees avancees ou sante avancee;
- matrice navigateur/mobile etendue;
- extension fonctionnelle `button / number / select / climate`, hors non-regression du comportement actuel de non-support.

## 9. Recommandation d'usage dans les prochains workflows BMAD

- **`create-story`**: citer cet addendum plus la base MVP, puis injecter dans chaque story les invariants touches et le minimum de tests par niveau. Ne pas produire de story V1.1 "neutre" sur les tests.
- **`validate-story`** ou **`validate-create-story`**: refuser une story si elle n'identifie pas clairement le contrat backend, les invariants V1.1 affectes, la non-destruction de `Republier` quand pertinent, et le minimum de non-regression attendu.
- **`dev-story`**: implementer les tests dans le meme changement que la fonctionnalite, en etendant d'abord les suites `pytest` / PHP existantes. Les tests UI ne viennent qu'en complement sur les contrats visibles critiques.

## 10. Resume ultra court reutilisable dans les prompts

V1.1 Pilotable = **addendum** a la strategie MVP, pas remplacement. Garder la base MVP de non-regression (`unit + integration backend`, mapping/lifecycle/diagnostic/exclusions/`unique_id`) et ajouter les preuves V1.1 sur: `global -> piece -> equipement`, `inherit/include/exclude`, precedence `equipement > piece > global`, backend source unique de `statut/raison/action recommandee/sante minimale`, `Republier` non destructif, `Supprimer/Recreer` seul flux destructif, separation scope local vs application HA, `Derniere operation` obligatoire, invariants HA deterministes. UI tests seulement cibles si la story modifie un contrat visible critique.
