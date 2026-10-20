# Story 24.3 : Mode « plugins en test » (à justifier) ; plugins natifs restent « exclus par plugin »

Status: draft

> **create-story du 2026-10-20 (session cloud déléguée, documentaire).** Verdict ci-dessous : **aucune garantie supplémentaire démontrable ; recommandation d'ABANDONNER la story.** Le statut reste `draft` : l'abandon n'est pas décidé ici, il revient à Alexandre / ClaudeBox. `ready-for-dev` n'est **pas** accordé. Chiffres tirés de `24-2-preuve-terrain-2026-10-20.md` (baseline du 20/10, `ff2fe0d`).

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **Story réduite par la décision d'Alexandre du 12/10 (Q1) : la raison `voie_native` n'est pas créée.** Le nom du fichier est conservé pour la traçabilité (`sprint-status.yaml`, epic). **Elle n'est maintenue que si, au `create-story`, le mode « plugins en test » (Q2 B) se justifie ; sinon la story est abandonnée.** Relecture de ClaudeBox obligatoire avant tout `ready-for-dev`. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q1 : la sémantique « exclu par plugin » est conservée.** Pas de raison `voie_native`, pas de relibellé : la liste `excludedPlugins`, le code `excluded_plugin` et le périmètre `exclu_par_plugin` restent tels quels. Les options A, B et C de Q1 sont **écartées**. L'export (24.2) porte toujours les `logicalId`.
- **Q2 B** : une liste « plugins en test » (vide par défaut), **sous réserve** de la justification demandée ci-dessous.
- **Conséquences pour cette story** : elle perd la raison `voie_native` et, avec elle, la modification des artefacts figés (`models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`) et des tables de libellés (`_DIAGNOSTIC_MESSAGES`, `_CLOSED_REASON_MAP`, libellés de l'écran). **Aucun de ces fichiers n'est touché.**

## Verdict du create-story (2026-10-20) : le mode « plugins en test » n'apporte pas de garantie démontrable

**Recommandation à ClaudeBox / Alexandre : ABANDONNER 24.3.** La partie « mode test » de l'exigence 2 est couverte par le retrait du plugin de `excludedPlugins` (un rescan, puis le remettre dans la liste pour revenir en arrière). Statut laissé `draft` ; la décision finale n'est pas prise par cette session.

### Ce que dit la baseline (chiffres du 20/10)

| Mesure | Valeur | Lecture pour le mode test |
|---|---|---|
| Équipements `homekit_exposed=true` | 119 | périmètre de la parité |
| Dont non publiés pour cause « plugin exclu » | **41** (34 % des 119 ; 41 sur 49 non publiés) | seuls équipements que le mode test concerne |
| Dont deconz | 20 | atteints nativement par HA, **décision d'Alexandre du 01/10 de ne pas les publier** : jamais candidats au test |
| Dont xiaomihome | 18 | idem |
| Reste : autres plugins exclus | **3** (41 − 20 − 18) | **seuls candidats réels à un test**, soit 2,5 % des 119 |
| Plugins exclus dans la configuration (export `config`) | 6 | au plus 4 d'entre eux ne sont ni deconz ni xiaomihome |

Le mode test ne servirait donc, en pratique, qu'à **3 équipements** (au plus 4 plugins), pour une comparaison ponctuelle. La part restante des 41 (38 équipements) est écartée par décision, pas par prudence.

### Argumentaire pour / contre

| Garantie invoquée par le brouillon | Apport réel du mode test | Démontrable ? |
|---|---|---|
| **Retour arrière sans ressaisir la liste** | Retirer puis remettre une entrée de `excludedPlugins` est un geste d'une ligne dans les deux sens ; le mode test a le même nombre de gestes (ajouter / retirer de la liste « en test »). | **Non** : équivalent |
| **Ne pas oublier un plugin retiré de l'exclusion** | Avec le retrait simple, l'oubli est déjà visible : l'export (24.2, `schema_version: 1`) porte `config.excluded_plugins`, et chaque équipement porte `plugin`, `decision`, `reason` ; un plugin sorti de la liste apparaît publié, un plugin ajouté apparaît `excluded_plugin`. Le mode test ajouterait un marqueur `native_test_mode`, mais **la Task 0 de 24.2 (20/10) a explicitement écarté ce champ** : il faudrait rouvrir l'export (champ additif, donc sans changement de version, mais un changement de plus). Un marquage d'oubli peut aussi se faire hors plugin, en comparant deux exports. | **Non** : visibilité déjà acquise sans le mode |
| **Mode jamais activé par le plugin / une mise à jour** | Vrai aussi du retrait simple : le plugin n'écrit jamais `excludedPlugins`. | **Non** : équivalent |
| **Test borné et réversible** (Q2 B) | Le retrait simple est borné par construction (un plugin à la fois, sa propre ligne). Le désabonnement des entités au retour arrière passe par le même mécanisme de dépublication différée (`pending_discovery_unpublish`) dans les deux cas. | **Non** : même mécanisme |

**Contre le maintien (coûts et risques propres au mode) :**
- une clé de configuration de plus et un état de plus : un plugin à la fois dans `excludedPlugins` **et** dans « en test » (priorité à définir, écran de configuration contradictoire : « Plugins exclus » affiche un plugin pourtant publié) ;
- trois couches touchées pour 3 équipements : `class.php:775-784`, ajax `saveFilteringConfig`, `configuration.php`, plus `docs/fr_FR/index.md` et un nouveau champ dans l'export déjà déployé ;
- il modifie `assess_eligibility` / la configuration du filtrage, que **24.4 modifie aussi** : 24.3 doit passer avant 24.4 et retarde la parité (la seule story qui change la production) ;
- sa preuve terrain (AC7 : inventaires MQTT et registres de HA avant/après, absence d'entité orpheline) serait identique pour le geste simple : c'est la procédure qui compte, pas la fonctionnalité.

**Pour le maintien (faibles) :** un libellé « en test » affiché à l'écran pourrait rassurer ; un garde-fou contre l'oubli plus visible qu'une comparaison d'exports ; Alexandre a retenu Q2 B le 12/10, **sous réserve** de cette justification, qui n'est pas apportée.

**Conclusion.** Aucune des garanties listées ne résiste à la comparaison avec le retrait simple de `excludedPlugins`, et le public concerné est de 3 équipements. Si Alexandre veut malgré tout un garde-fou contre l'oubli, l'option la moins chère est **sans code** : une procédure documentée (« retirer le plugin, rescan, relever les identifiants publiés dans l'export, remettre le plugin ») dans `docs/fr_FR/index.md`, portée par la PR qui clôt 24.4 ou par une courte PR documentaire, sans nouvelle clé.

### Conséquences si l'abandon est décidé (rien n'est modifié ici)
- 24.4 suit directement la baseline (déjà le cas dans `sprint-status.yaml` : « si abandonnée, 24-4 suit directement la baseline »).
- L'exigence 2 reste couverte : plugins natifs « exclus par plugin » (Q1), `logicalId` dans l'export, test par retrait de la liste.
- Le champ `native_test_mode` (déjà non livré par 24.2) disparaît des gates epic-level (`epics-projection-engine.md`).
- Le fichier est conservé pour la traçabilité, avec le statut final choisi par Alexandre / ClaudeBox (par exemple `abandonnée`).

## Questions ouvertes restantes (avec recommandation)

| # | Question | Recommandation |
|---|---|---|
| **Q3-1** | Maintenir ou abandonner 24.3 ? | **Abandonner** (verdict ci-dessus). Décision à Alexandre / ClaudeBox. |
| **Q3-2** | Si abandon : où consigner la procédure de test par retrait de `excludedPlugins` ? | `docs/fr_FR/index.md`, dans la PR de 24.4 (même zone « Plugins exclus / Pièces exclues », AC7 de 24.4) ; pas de story dédiée. |
| **Q3-3** | Si abandon : faut-il quand même un essai terrain d'un retrait propre (publication puis retour « exclu par plugin », sans entité orpheline) ? | **Oui, une fois, par ClaudeBox**, sur l'un des 3 équipements d'un plugin exclu hors deconz / xiaomihome, avec inventaires MQTT et registres de HA avant/après ; à adosser à la preuve de 24.4 (AC10), pas à une story. |
| **Q3-4** | Si maintien malgré tout : un plugin à la fois dans `excludedPlugins` et dans « en test » ? | Priorité « en test » (le plugin est publié), avertissement dans la configuration ; mais c'est un argument de plus pour l'abandon. |
| **Q3-5** | Si maintien : le champ `native_test_mode` dans l'export ? | Champ additif sans changement de `schema_version` (politique de 24.2), livré par 24.3 seulement ; 24.2 n'est pas rouvert. |
| **Q3-6** | Statut final et nom de fichier ? | Garder le nom (traçabilité) ; si abandon, statut `abandonnée` posé par ClaudeBox / Alexandre, pas par cette session. |

## Doutes et vérifications non faites
- Les 3 équipements « autres plugins exclus » sont déduits (41 − 20 − 18) ; leurs identifiants et plugins ne sont pas dans la baseline écrite. À relever dans l'export par ClaudeBox si Q3-3 est retenue.
- Le comportement de la dépublication lors d'un retour arrière a été lu dans le code (`pending_discovery_unpublish`, `http_server.py`) mais **n'a pas été exécuté** ; seul l'essai de Q3-3 le prouve.
- La baseline porte une somme à vérifier (voir 24.4, § Baseline) ; elle ne change pas ce verdict.

## Story (si elle est maintenue)

En tant qu'utilisateur dont Home Assistant intègre déjà nativement certains plugins Jeedom,
je veux pouvoir tester un de ces plugins avec jeedom2ha sans modifier durablement la liste « Plugins exclus »,
afin de comparer les deux voies un plugin à la fois, puis revenir en arrière en un geste.

**Parcours : PHP (configuration) + démon (champ additif) + documentation.** Ni artefact figé, ni raison nouvelle.

## À justifier au `create-story`

Puisque « exclu par plugin » est conservé, **retirer un plugin de la liste `excludedPlugins` suffit déjà à le tester** (un rescan, puis le remettre dans la liste pour revenir en arrière). Le mode « plugins en test » n'est maintenu que s'il apporte une garantie que ce geste n'apporte pas, par exemple :
- une liste « en test » séparée qui évite d'oublier un plugin retiré de l'exclusion (le marquage `native_test_mode` dans l'export le rend visible) ;
- un retour arrière sans ressaisir la liste.

**Ce brouillon ne décide pas.** Si aucune garantie supplémentaire n'est démontrée, la story est **abandonnée** (statut à noter dans `sprint-status.yaml` et dans le journal ci-dessous) et la partie « mode test » de l'exigence 2 est considérée comme couverte par le retrait de la liste. *Au create-story du 20/10 : aucune garantie démontrée, voir le verdict en tête ; la décision reste à Alexandre / ClaudeBox.*

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

- [x] **Task 0 — Justifier ou abandonner** : justification faite au create-story du 20/10 (verdict en tête : recommandation d'abandon) ; **décision finale en attente** (Q3-1). Les Tasks 1 à 4 ci-dessous ne sont à engager que si la story est maintenue.
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
- 2026-10-20 — **create-story** (session cloud déléguée, documentaire) : à la lumière de la baseline du 20/10 (41 équipements exposés non publiés pour cause de plugin exclu, dont 38 deconz et xiaomihome écartés par la décision du 01/10 ; 3 seuls candidats réels), aucune garantie supplémentaire démontrable par rapport au retrait de `excludedPlugins` ; **recommandation : abandonner**. Story laissée `draft` : décision à Alexandre / ClaudeBox. Questions Q3-1 à Q3-6 consignées avec recommandation.
