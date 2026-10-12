# Story 24.3 : Mode « plugins en test » (à justifier) ; plugins natifs restent « exclus par plugin »

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **Story réduite par la décision d'Alexandre du 12/10 (Q1) : la raison `voie_native` n'est pas créée.** Le nom du fichier est conservé pour la traçabilité (`sprint-status.yaml`, epic). **Elle n'est maintenue que si, au `create-story`, le mode « plugins en test » (Q2 B) se justifie ; sinon la story est abandonnée.** Relecture de ClaudeBox obligatoire avant tout `ready-for-dev`. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q1 : la sémantique « exclu par plugin » est conservée.** Pas de raison `voie_native`, pas de relibellé : la liste `excludedPlugins`, le code `excluded_plugin` et le périmètre `exclu_par_plugin` restent tels quels. Les options A, B et C de Q1 sont **écartées**. L'export (24.2) porte toujours les `logicalId`.
- **Q2 B** : une liste « plugins en test » (vide par défaut), **sous réserve** de la justification demandée ci-dessous.
- **Conséquences pour cette story** : elle perd la raison `voie_native` et, avec elle, la modification des artefacts figés (`models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`) et des tables de libellés (`_DIAGNOSTIC_MESSAGES`, `_CLOSED_REASON_MAP`, libellés de l'écran). **Aucun de ces fichiers n'est touché.**

## Story (si elle est maintenue)

En tant qu'utilisateur dont Home Assistant intègre déjà nativement certains plugins Jeedom,
je veux pouvoir tester un de ces plugins avec jeedom2ha sans modifier durablement la liste « Plugins exclus »,
afin de comparer les deux voies un plugin à la fois, puis revenir en arrière en un geste.

**Parcours : PHP (configuration) + démon (champ additif) + documentation.** Ni artefact figé, ni raison nouvelle.

## À justifier au `create-story`

Puisque « exclu par plugin » est conservé, **retirer un plugin de la liste `excludedPlugins` suffit déjà à le tester** (un rescan, puis le remettre dans la liste pour revenir en arrière). Le mode « plugins en test » n'est maintenu que s'il apporte une garantie que ce geste n'apporte pas, par exemple :
- une liste « en test » séparée qui évite d'oublier un plugin retiré de l'exclusion (le marquage `native_test_mode` dans l'export le rend visible) ;
- un retour arrière sans ressaisir la liste.

**Ce brouillon ne décide pas.** Si aucune garantie supplémentaire n'est démontrée, la story est **abandonnée** (statut à noter dans `sprint-status.yaml` et dans le journal ci-dessous) et la partie « mode test » de l'exigence 2 est considérée comme couverte par le retrait de la liste.

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | La liste actuelle est une saisie libre, enregistrée par `saveFilteringConfig`, comparée à `getEqType_name()` avec la priorité équipement > plugin > pièce. | `plugin_info/configuration.php:112-124` ; `core/ajax/jeedom2ha.ajax.php:812-826` ; `core/class/jeedom2ha.class.php:701,775-784` |
| F2 | La source `plugin` donne `excluded_plugin` à l'éligibilité (étape 1, inéligible, `confidence="sure"`), périmètre `exclu_par_plugin` : **inchangés**. | `models/topology.py:220-223,301-310` ; `models/ui_contract_4d.py:17` |
| F3 | Un `force_publish` ne lève pas une inéligibilité d'étape 1 (I1) : le mode test ne peut pas passer par l'override. | `models/evaluate_equipment.py:362-390` |
| F4 | La documentation décrit « Plugins exclus ». | `docs/fr_FR/index.md:96,431,434` |

## Critères d'acceptation proposés (conditionnels, si la story est maintenue)

- **AC1.** Une liste « plugins en test » est ajoutée à la configuration du filtrage, **vide par défaut et après toute mise à jour** ; le plugin ne l'active jamais de lui-même.
- **AC2.** Un équipement d'un plugin en test n'est pas exclu par plugin (même chemin que s'il n'était pas dans `excludedPlugins`) ; la priorité équipement > plugin > pièce et `excluded_eqlogic` restent inchangées.
- **AC3.** Le payload porte un champ additif `native_test_mode` (équipement concerné) ; l'export (24.2) le recopie (champ additif, pas de changement de version).
- **AC4.** **Aucune raison nouvelle, aucun libellé modifié** : `taxonomy.py`, `cause_mapping.py`, `ui_contract_4d.py`, `_DIAGNOSTIC_MESSAGES`, `_CLOSED_REASON_MAP` et les libellés de l'écran sont **inchangés** (test de non-modification).
- **AC5.** Sans plugin en test, comportement strictement identique à aujourd'hui : golden et contrat 4D inchangés.
- **AC6.** La configuration du plugin et `docs/fr_FR/index.md` décrivent la liste, l'avertissement de doublon d'entités avec l'intégration native, et le retour arrière.
- **AC7.** Preuve terrain par ClaudeBox : un plugin de test publie, puis revient « exclu par plugin », sans entité orpheline (inventaire MQTT et registres de HA avant/après) ; gate 20-0 vert si l'écran change ; aucun nom réel (CC-48).

## Tâches proposées

- [ ] **Task 0 — Justifier ou abandonner** (au `create-story`, avec ClaudeBox) : voir la section « À justifier ».
- [ ] **Task 1 — PHP** : lecture de la liste « en test » dans le calcul de `is_excluded` (`class.php:775-784`), champ additif `native_test_mode`.
- [ ] **Task 2 — Configuration et documentation.**
- [ ] **Task 3 — Tests** : plugin en test / hors test / liste vide ; priorité ; artefacts figés inchangés.
- [ ] **Task 4 — Gate, déploiement, preuve terrain (humain).**

## Garde-fous

- Pas d'ouverture de composant, pas de changement de mapping, pas de raison nouvelle.
- Le mode test n'est jamais activé par le plugin, par une mise à jour ni par un forçage.
- Aucune écriture dans la configuration Jeedom des équipements.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft` avec la raison `voie_native` (Q1 A recommandée).
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q1 « exclu par plugin » conservé (A, B, C écartées) ; Q2 B. La raison `voie_native` et la modification des artefacts figés sont retirées ; le mode test est à justifier au `create-story`, sinon la story est abandonnée.
