# Story 24.3 : `voie_native` : plugins natifs non publiés et mode « test du plugin »

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **Change la production** (relibellé de tous les équipements « exclus par plugin », mode test). Décisions attendues d'Alexandre : **Q1** (la liste et son vocabulaire) et **Q2** (le mode test) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).

## Story

En tant qu'utilisateur dont Home Assistant intègre déjà nativement certains plugins Jeedom,
je veux que jeedom2ha ne publie pas ces équipements et dise pourquoi (« voie native »), avec un mode de test explicite et désactivé par défaut,
afin d'avoir une seule voie par équipement, sans doublon d'entités ni de noms devant Assist.

**Parcours : PHP (configuration) + démon + écran (libellés) + documentation.** C'est la **story dédiée qui lève le gel** de `models/taxonomy.py`, `models/cause_mapping.py` et `models/ui_contract_4d.py`, de façon strictement additive. Gate 20-0 et `ready-for-UX-validation` avant `done`.

## Dépendances et décisions

- Dépend de **24.2 déployée et de la baseline « avant »** : le nombre d'équipements relibellés et la liste des plugins sont lus dans l'export.
- **Q1** : A recommandée (réutiliser `excludedPlugins`, relue « plugins gérés nativement ») ; B (clé séparée) ; C (liste par défaut). **Q2** : B recommandée (liste « plugins en test », vide par défaut).
- 24.4 vient après (même `assess_eligibility`, mêmes tables).

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | La liste actuelle est une saisie libre, enregistrée par `saveFilteringConfig`, comparée à `getEqType_name()` avec la priorité équipement > plugin > pièce. | `plugin_info/configuration.php:112-124` ; `core/ajax/jeedom2ha.ajax.php:812-826` ; `core/class/jeedom2ha.class.php:701,775-784` |
| F2 | La source `plugin` devient le code `excluded_plugin` à l'éligibilité (étape 1, inéligible, `confidence="sure"`). | `models/topology.py:220-223,301-310` |
| F3 | `excluded_plugin` est connu de : la taxonomie figée (`:16`), la table de causes figée (`:28-32`), le contrat 4D figé (`:17`, périmètre `exclu_par_plugin`), `_DIAGNOSTIC_MESSAGES` (`http_server.py:2280-2284`), `_CLOSED_REASON_MAP` (`:2413`), les libellés de l'écran. | `models/taxonomy.py:16` ; `models/cause_mapping.py:28` ; `models/ui_contract_4d.py:17` ; `desktop/js/jeedom2ha_mapping_override.js:640,649` |
| F4 | **Un code absent de `_EXCLUSION_REASON_TO_PERIMETRE` devient « inclus »** (`reason_code_to_perimetre`) ; un équipement inclus et non publié compte comme **écart de direction 1**. Un code absent de la taxonomie s'affiche « Non supporté ». | `ui_contract_4d.py:15-30,32-44` ; `taxonomy.py:34-40` |
| F5 | Un `force_publish` ne lève pas une inéligibilité d'étape 1 (I1) : le mode test ne peut pas passer par l'override. | `models/evaluate_equipment.py:362-390` |
| F6 | Le journal de nettoyage distingue `startswith("excluded_")` ; `voie_native` n'a pas ce préfixe (message trompeur, sans effet fonctionnel). | `http_server.py:2025` |
| F7 | La documentation décrit « Plugins exclus » et son libellé de cause. | `docs/fr_FR/index.md:96,431,434` |

## Critères d'acceptation proposés (à figer selon Q1 et Q2)

- **AC1.** Un équipement dont le plugin est dans la liste des plugins natifs, et pas dans la liste « en test », reçoit à l'éligibilité la raison canonique **`voie_native`** (inéligible, étape 1, `confidence="sure"`), `decision = not_published`, aucune entité publiée. La priorité des exclusions est inchangée : l'exclusion explicite de l'équipement l'emporte (`excluded_eqlogic`), `voie_native` l'emporte sur la pièce (`excluded_object`).
- **AC2.** Le mode test est une liste de plugins, **vide par défaut** (Q2 B). Un équipement d'un plugin en test est évalué et publié comme tout autre ; l'export le marque `native_test_mode: true`. Aucun plugin n'est en test après installation ni après mise à jour.
- **AC3.** Ajout **strictement additif** des entrées `voie_native` dans la taxonomie (statut principal « Exclu »), la table de causes (libellé fixé avec ClaudeBox, par exemple « Pris en charge nativement par Home Assistant ») et le contrat 4D (périmètre `exclu_par_plugin`). **Aucune entrée existante n'est modifiée** : test qui compare les tables avant/après, sans l'entrée nouvelle.
- **AC4.** Aucun faux écart : un équipement `voie_native` ne compte ni dans « inclus mais non publié » ni dans « non pris en charge » ; il est « exclu » dans les compteurs de 22-2 ; invariant `total = inclus + exclus` vérifié.
- **AC5.** `_DIAGNOSTIC_MESSAGES`, `_CLOSED_REASON_MAP`, les libellés de l'écran et le journal de nettoyage connaissent `voie_native` ; le libellé dit ce qui se passe et ce que fait l'utilisateur (la liste « en test » existe vraiment dans la configuration : pas de faux bouton). L'ancien `excluded_plugin` reste accepté en lecture pour d'anciens diagnostics.
- **AC6.** Un équipement déjà publié dont le plugin est ajouté à la liste est dépublié par le chemin de nettoyage existant, sans entité orpheline (inventaire MQTT et registres de HA avant/après).
- **AC7.** La configuration du plugin et `docs/fr_FR/index.md` (lignes citées en F7) décrivent la liste, le mode test et l'avertissement de doublon ; le texte « Plugins exclus » est remplacé selon Q1.
- **AC8.** L'export (24.2) porte `reason: voie_native`, le `logicalId` d'équipement et de commande, et `native_test_mode`.
- **AC9.** `PRODUCT_SCOPE`, mapping, publication des autres équipements, golden et contrat 4D inchangés, sauf les entrées additives justifiées ; gate 20-0 vert ; aucun nom réel dans le dépôt (CC-48).
- **AC10.** Preuve terrain par ClaudeBox : liste des équipements relibellés rapprochée de la baseline ; aucun `entity_id` ni `unique_id` d'une entité encore publiée ne change ; un plugin de test en mode test publie, puis revient en `voie_native`, sans doublon résiduel.

## Tâches proposées

- [ ] **Task 0 — Lever le gel, dans cette story seulement** : confirmer par `git blame`/revue que les trois artefacts n'acceptent ici que des ajouts ; écrire le test de non-modification des entrées existantes avant de coder.
- [ ] **Task 1 — PHP** : lecture de la liste « en test », prise en compte dans le calcul de `is_excluded`/`exclusion_source` (`class.php:775-784`), champ additif `native_test_mode`.
- [ ] **Task 2 — Démon** : `_EXCLUSION_SOURCE_TO_REASON["plugin"] = "voie_native"` ; entrées additives des trois artefacts figés ; tables de diagnostic.
- [ ] **Task 3 — Écran et configuration** : libellés (Q1), champ « en test », texte d'avertissement.
- [ ] **Task 4 — Tests** : éligibilité, priorité, mode test, tables figées inchangées, compteurs, contrat 4D, export.
- [ ] **Task 5 — Gate 20-0 + déploiement + preuve terrain (humain)**.
- [ ] **Task 6 — Documentation** (`docs/fr_FR`).

## Garde-fous

- Pas d'ouverture de composant, pas de changement de mapping.
- Aucune liste de plugins livrée par défaut sans décision de Q1 C.
- Le mode test n'est jamais activé par le plugin, par une mise à jour ni par un forçage.
- Aucune écriture dans la configuration Jeedom des équipements.

## Vérifications non faites par cette session

La liste réelle des plugins aujourd'hui saisie et des équipements concernés (baseline) ; le comportement de HA en cas de doublon d'entités pendant un test ; l'effet exact des libellés sur la modale et le parcours du gate 20-0.
