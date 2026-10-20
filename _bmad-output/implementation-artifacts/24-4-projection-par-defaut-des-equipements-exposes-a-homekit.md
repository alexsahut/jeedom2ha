# Story 24.4 : Projection par défaut des équipements exposés à HomeKit

Status: ready-for-dev

> **create-story du 2026-10-20 (session cloud déléguée, documentaire).** Intègre la baseline de `24-2-preuve-terrain-2026-10-20.md` (`ff2fe0d`) et la correction d'**exposition effective** (AC11 bis de 24.2). **Reste `draft` : `ready-for-dev` n'est pas accordé** (relecture ClaudeBox / décision d'Alexandre requises, questions Q4-1 à Q4-9 ci-dessous). Dépendance 24.3 : la recommandation est de l'abandonner ; 24.4 suivrait alors directement la baseline.

> **Brouillon de cadrage (2026-10-12), `draft` jusqu'à son `create-story` après la baseline.** Rédigé par une session cloud déléguée, documentaire. **Change la production** : des équipements aujourd'hui exclus par leur pièce seront publiés au sync suivant. Décisions d'Alexandre (12/10 à 13:22) : **Q3 A** et **Q4 A** ; ex-décisions attendues **Q3** (la pièce n'écarte plus) et **Q4** (mapping ambigu ou probable) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
>
> **R1 (ClaudeBox, 12/10) intégrée** : *établi par ClaudeBox le 12/10*, d'après la configuration actuelle du plugin (inchangée depuis le 04/10) et le référentiel du 10/10, **3 équipements** (virtuels, dans deux pièces exclues) seraient nouvellement publiés *(estimation provisoire, antérieure à la baseline ; remplacée par le chiffrage du 20/10 ci-dessous : 3 attendus, 5 au plus)*. Le risque de publication de masse est faible ; l'option C de Q3 ne se justifie plus. Le signal d'exposition suit la règle de Homebridge (24-1) : pièce + équipement + valeur par défaut.

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q3 A** : un équipement exposé à HomeKit n'est jamais écarté par sa pièce (`excludedObjects` et état de pièce hérité) ; l'exclusion explicite de l'équipement et l'état global « exclure » restent respectés. Options B et C **écartées**.
- **Q4 A** : l'exposition HomeKit ne change pas la politique de confiance ; option B **écartée**.
- **Q1** : « exclu par plugin » conservé : `excluded_plugin` garde sa priorité (équipement > plugin > pièce) sur le signal HomeKit ; **pas de `voie_native`**.
- Cette story reste `draft` jusqu'à son `create-story`, après la baseline de 24.2.

## Correction « exposition effective » (nouveau, 2026-10-20)

**Constat (baseline, AC11 bis de 24.2).** `homekit_exposed` reflète le **réglage** d'exposition lu dans Jeedom (pièce + équipement + valeur par défaut de Homebridge, 24.1), pas l'exposition **effective** : Homebridge n'expose pas un équipement désactivé. Les équipements 165 et 550 sont `homekit_exposed=true` et désactivés. Sans correction, 24.4 les traiterait comme « exposés » et fausserait la projection et la mesure de parité.

**Définition (une seule, partagée).** Un équipement est *effectivement exposé* à HomeKit si et seulement si `homekit_exposed = true` **ET** `enabled = true`.

| `enabled` | `homekit_exposed` | Exposition effective |
|---|---|---|
| `true` | `true` | **`true`** |
| `true` | `false` | `false` |
| `true` | `null` (inconnu) | `null` (jamais traité comme exposé) |
| `false` | n'importe lequel | **`false`** |

`enabled` illisible : le démon et le PHP retiennent déjà « actif par défaut » (`_to_bool(..., default=True)` dans `topology.py`, `class.php:875`) ; la règle suit ce défaut (Q4-3).

**(a) Dans l'export (contrat de décision de 24.2).**
- **Champ additif** `homekit_exposed_effective` (booléen ou `null`) sur chaque équipement, calculé par la règle ci-dessus ; pour les scénarios, avec `active` à la place de `enabled` (Q4-5).
- `homekit_exposed` et `homekit_exposed_source` **ne changent pas de sens** (ils restent le réglage et sa provenance) ; aucun champ renommé ni retiré.
- **`schema_version` reste 1** : la politique de 24.2 (`24-2-export-json-versionne-du-contrat-de-decision.md`, § Forme du document) veut qu'un champ ajouté ne change pas la version, et seul un champ renommé, retiré ou de sens changé la porte à 2. Remplacer le sens de `homekit_exposed` serait un changement de sens, donc une version 2 : **écarté** (Q4-1).
- **Comparabilité avec la baseline « avant »** : l'export du 20/10 n'a pas ce champ, mais il porte `enabled` et `homekit_exposed` ; l'exposition effective « avant » est dérivable (`homekit_exposed` ET `enabled`), donc **aucune nouvelle baseline** n'est nécessaire.
- 24.2 est `ready-for-UX-validation` et son fichier n'est pas rouvert : le champ est livré par 24.4 (Task 1 bis), avec test de non-régression du reste du document.

**(b) Dans la projection par défaut.**
- Un helper unique `homekit_exposed_effective` (propriété de `JeedomEqLogic`, `models/topology.py`) est la seule source pour `assess_eligibility`, `resolve_published_scope` et l'export ; **ni le PHP ni le payload ne changent** (le signal de 24.1 reste une lecture pure du réglage de Homebridge, sans lire l'état d'activation).
- La règle Q3 A (« la pièce n'écarte plus ») ne s'applique qu'aux équipements **effectivement** exposés (`true`). Un équipement désactivé n'est donc pas relevé de l'exclusion de sa pièce, **n'est pas marqué exception** (`is_exception`, `decision_source` additive) et garde sa raison actuelle : l'ordre existant de `assess_eligibility` (« Exclu > Désactivé > Sans commandes > Sans type générique ») n'est **pas modifié**.
- Un équipement désactivé qui est réactivé dans Jeedom devient effectivement exposé au sync suivant et suit la règle Q3 A.

**Ce que la correction change, et ne change pas (voir le chiffrage ci-dessous).** Sur la baseline, elle ne change le **statut de publication d'aucun équipement** (un équipement désactivé est non publié avec ou sans elle) ; elle change l'**attribution de la cause** (`excluded_object` conservé plutôt que `disabled_eqlogic`/exception trompeuse), les **compteurs d'exceptions** et le **dénominateur de la parité** (119 → au plus 117).

## Story

En tant qu'utilisateur qui pilote sa maison par la voix dans Apple Maison,
je veux que tout équipement exposé à HomeKit soit projeté dans Home Assistant par défaut, sans que l'exclusion de sa pièce ne l'écarte,
afin que ce qui se pilote ou se consulte par la voix le soit aussi par Assist, sans configurer la maison deux fois.

**Parcours : démon + libellés de l'écran et de la configuration.** Gate 20-0 et `ready-for-UX-validation` avant `done`.

## Dépendances et décisions

- Dépend de **24.1** (signal) et **24.2** (mesure + baseline, **faite le 20/10**). Si 24.3 (mode « plugins en test ») est maintenue, elle passe avant (mêmes fonctions de configuration) ; sinon 24.4 suit directement la baseline. **Recommandation du create-story de 24.3 : l'abandonner** (décision à Alexandre / ClaudeBox) ; 24.4 n'a alors plus de prédécesseur en attente.
- **Q3** : A recommandée (la pièce n'écarte plus ; exclusion explicite et état global respectés) ; C (derrière une clé de configuration, désactivée au premier déploiement) si Alexandre veut un déclenchement manuel. **Q4** : A recommandée (la politique de confiance reste).

## Raisons légitimes d'écart pour un équipement exposé (liste à valider)

Seuls ces cas écartent un équipement `homekit_exposed = true`, chacun avec sa raison canonique dans l'export et l'écran :
- exclusion explicite : `excluded_eqlogic`, `publication_excluded_eqlogic`, état d'équipement « exclure » du périmètre publié ;
- exclusion par plugin : `excluded_plugin` (plugins natifs compris, Q1), qui prime sur le signal HomeKit comme avant ;
- impossibilité technique : `disabled_eqlogic`, `no_commands`, `no_generic_type_configured` / `no_supported_generic_type`, `no_mapping`, `ambiguous_skipped` / `probable_skipped` (Q4 A), échec de validation `ha_*`, `ha_component_not_in_product_scope`.

L'état global « exclure » reste respecté (Q3 A, ce n'est pas une exclusion de pièce).

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | L'exclusion de pièce vit à deux endroits : `excludedObjects` (code `excluded_object`, étape 1) et l'état de pièce hérité du périmètre publié (règle historique `legacy_excluded_pieces`). Priorité équipement > plugin > pièce. | `core/class/jeedom2ha.class.php:702-703,783-784` ; `models/topology.py:220-223,307-310` ; `models/published_scope.py:93-122` |
| F2 | Le filtre de périmètre s'applique **après** la décision ; il lit `effective_state` : un équipement hérite de l'état « exclure » de sa pièce sauf état d'équipement explicite. | `transport/http_server.py:419-428`, `:1911`, `:1948` |
| F3 | Aucun code du dépôt n'écrit les états de périmètre (`publishedScope*States`, `jeedom2ha_excluded`, `jeedom2ha_scope_state`) ; ils sont lus. L'exclusion explicite de l'équipement que pose l'utilisateur est l'override `exclude_eqlogic` (20-2). | `class.php:710-712,775,810` ; `models/decide_publication.py:95-103` |
| F4 | Le résultat du périmètre porte `decision_source` et `is_exception` (comptage des exceptions) : l'écran « pièce » s'en sert. | `published_scope.py:126-175` ; `core/ajax/jeedom2ha.ajax.php:125-170` |
| F5 | La configuration « Pièces exclues » et sa documentation décrivent une exclusion sans exception. | `plugin_info/configuration.php:124-132` ; `docs/fr_FR/index.md:97,432` |
| F6 | `evaluate_equipment()` produit déjà une décision par commande avec une raison non vide (I6) ; une commande non couverte porte `command_not_covered`. | `models/evaluate_equipment.py:38-48,113-130` |

## Critères d'acceptation proposés (figés sur Q3 A et Q4 A)

- **AC1.** Un équipement **effectivement exposé** (`homekit_exposed = true` ET `enabled = true`) n'est jamais écarté par `excludedObjects` ni par un état de pièce « exclure » hérité. À l'éligibilité (`assess_eligibility`), la source `object` est ignorée pour lui ; dans le résolveur de périmètre, la pièce exclue ne s'applique pas à lui sauf état d'équipement explicite (même règle que le sync, « Publier », l'aperçu et le diagnostic : un seul calcul).
- **AC2.** Le périmètre publié signale ces équipements comme exceptions (`is_exception`, `decision_source` additive, par exemple `exception_homekit`) pour que les compteurs de pièce et le bandeau restent cohérents ; contrat additif, aucun champ existant modifié.
- **AC3.** L'exclusion explicite d'un équipement exposé (override `exclude_eqlogic`, état d'équipement « exclure », `jeedom2ha_excluded`) l'écarte toujours, avec sa raison.
- **AC4.** Un équipement non exposé (`false`), au signal inconnu (`null`) **ou désactivé (`enabled = false`, y compris si `homekit_exposed = true`)** garde exactement le comportement et la raison actuels ; un équipement dont le signal est `null` ou qui est désactivé n'est **jamais** traité comme exposé.
- **AC5.** **Chaque commande** d'un équipement exposé a, dans l'export, une décision, une raison canonique non vide et son étape ; aucune commande « sans raison » (test sur le corpus golden et sur les fixtures de 24.1).
- **AC6.** Q4 A : la politique de confiance et le forçage restent le levier des mappings ambigus ou probables ; aucun forçage automatique par le signal HomeKit.
- **AC7.** Libellés : la configuration « Pièces exclues » et `docs/fr_FR/index.md` disent « sauf équipements exposés à HomeKit » ; la cause `excluded_object` n'apparaît plus pour un équipement **effectivement** exposé (`homekit_exposed` ET `enabled`) ; un équipement désactivé la garde (AC12) ; aucune cause trompeuse à l'écran.
- **AC8.** Les équipements nouvellement publiés le sont par le chemin normal (découverte, état initial, disponibilité) ; aucun `entity_id` ni `unique_id` d'entité déjà publiée ne change.
- **AC9.** `PRODUCT_SCOPE`, mapping, golden et contrat 4D inchangés, sauf champs additifs justifiés ; gate 20-0 vert ; aucun nom réel dans le dépôt (CC-48).
- **AC10.** Preuve terrain par ClaudeBox : liste préalable (identifiants) des équipements **effectivement** exposés écartés par la pièce, tirée de l'export (attendu : 3, borne 5 ; voir le chiffrage) ; après déploiement, ces équipements sont publiés (ou ont une autre raison canonique) ; inventaires MQTT et registres de HA avant/après ; retour arrière vérifié sur un équipement de test (« Supprimer de Home Assistant » puis exclusion explicite) ; export « après » comparé à la baseline.
- **AC11.** Export : champ additif `homekit_exposed_effective` (équipements ; scénarios selon Q4-5) = `homekit_exposed` ET `enabled` selon la table ci-dessus ; `homekit_exposed` / `homekit_exposed_source` inchangés ; `schema_version` reste 1 ; tests : les quatre lignes de la table, les équipements 165 et 550 de la baseline représentés par des fixtures anonymes (`enabled=false`, `homekit_exposed=true` ⇒ `homekit_exposed_effective=false`), document existant inchangé hors le champ.
- **AC12.** Un équipement désactivé et `homekit_exposed = true` dans une pièce exclue garde `excluded_object` (ordre de `assess_eligibility` inchangé), n'est pas relevé de la pièce, n'est pas compté comme exception ; désactivé hors pièce exclue : `disabled_eqlogic` comme avant. Un seul calcul (helper partagé) pour sync, « Publier », aperçu, diagnostic et export (test de parité).

## Tâches proposées

- [x] **Task 0 — Confirmation préalable (ClaudeBox, à partir de l'export de 24.2)** — *chiffrage réel du create-story du 20/10, remplaçant l'estimation provisoire de ClaudeBox du 12/10 (3 équipements, antérieure à la baseline)*. Voir § « Chiffrage de l'effet attendu » : sur la baseline, **0 changement de statut sauf les équipements exposés écartés par la pièce : 3 attendus, 5 au plus** ; plugin exclu (41), exclusion individuelle (3), ambigu (1) et désactivés (2) ne changent pas de statut. À faire par ClaudeBox avant `ready-for-dev` : (1) **croiser `enabled` × `reason` × exposition effective** sur l'export pour placer 165 et 550 et lever l'écart de somme de la baseline (49 non publiés, mais 41+5+3+1 = 50) ; (2) relever les identifiants des équipements effectivement exposés dont la raison est `excluded_object` (attendu 3, borne 5) ; (3) si ce nombre dépasse nettement 5 (seuil de rappel : plus de 10), revenir vers Alexandre (option C de Q3) avant de coder.
- [ ] **Task 1 bis — Exposition effective** : helper `homekit_exposed_effective` (`models/topology.py`), champ additif de l'export (équipements ; scénarios selon Q4-5), `schema_version` inchangé ; AC11 et AC12.
- [ ] **Task 1 — Démon** : règle dans `assess_eligibility` et dans `resolve_published_scope` ; source de décision additive ; un seul point de calcul partagé par sync, « Publier », aperçu, diagnostic.
- [ ] **Task 2 — Libellés** (configuration, écran, `docs/fr_FR`).
- [ ] **Task 3 — Tests** : exposé / non exposé / inconnu / **désactivé** × pièce exclue × exclusion explicite × état global ; parité sync / « Publier » / aperçu ; golden ; export.
- [ ] **Task 4 — Gate 20-0 + déploiement + preuve terrain (humain)**.

## Baseline du 20/10 : ce qu'elle dit et ce qu'elle ne dit pas

Source : `24-2-preuve-terrain-2026-10-20.md` (292 équipements, 3 422 commandes ; 119 `homekit_exposed=true`, dont 97 réglés sur l'équipement et 22 par le défaut de Homebridge). Identifiants seulement (CC-48).

| Statut des 119 exposés (réglage) | Nombre |
|---|---|
| Publiés | 69 |
| Partiel | 1 |
| Non publiés | 49 |

Causes données pour les 49 non publiés : plugin exclu **41** (20 deconz + 18 xiaomihome + **3** autres plugins), pièce exclue **5**, exclusion individuelle **3**, ambigu **1**.

**Deux points à lever par ClaudeBox (Task 0) :**
1. **Somme** : 41 + 5 + 3 + 1 = **50**, alors que la baseline compte **49** non publiés (69 + 1 + 49 = 119). Un équipement est vraisemblablement compté deux fois ou classé à tort ; la baseline n'a pas été modifiée par cette session (hors périmètre).
2. **Place de 165 et 550** (désactivés, exposés par réglage) : `assess_eligibility` applique « Exclu > Désactivé » (`topology.py:354-366`). Un équipement désactivé **et** exclu (plugin, pièce ou individuel) porte donc la raison d'exclusion ; un désactivé seul porte `disabled_eqlogic`, cause qui **n'apparaît pas** dans la liste des 49. Les deux sont donc soit dans l'une des catégories ci-dessus (hypothèse H1 : les « 5 pièce exclue » moins les 3 attendus par ClaudeBox le 12/10 laissent précisément 2), soit une cinquième catégorie omise (H2). Non tranché : `enabled` est dans l'export, le croisement est immédiat pour ClaudeBox.

## Chiffrage de l'effet attendu de 24.4 sur la baseline

Légende : « change » = le statut de publication (`not_published` → `published`) change au sync suivant. Les 119 sont le réglage ; l'exposition effective est notée E.

| Catégorie de cause (baseline) | Équipements | Changent de statut avec 24.4 + correction | Justification |
|---|---|---|---|
| Publiés / partiel | 69 / 1 | **0** | rien à relever |
| **Pièce exclue** | 5 | **3 attendus (borne haute 5)** | seule catégorie touchée (Q3 A). Les 3 sont l'estimation de ClaudeBox du 12/10 (virtuels, deux pièces exclues). Sous H1, les 2 autres sont 165 et 550 : désactivés, donc non E, **non relevés** (AC4, AC12) et inchangés. Sous H2, jusqu'à 5 sont relevés ; chacun reste soumis au mapping (une absence de type ou un mapping ambigu le laisse non publié avec sa raison). Borne basse : 0 si aucun des 5 n'est publiable |
| **Plugin exclu** | 41 (dont 38 deconz/xiaomihome) | **0** | `excluded_plugin` prime sur le signal HomeKit (Q1) |
| **Exclusion individuelle** | 3 | **0** | l'exclusion explicite l'emporte (AC3) |
| **Ambigu** | 1 | **0** | Q4 A : la politique de confiance reste (`ambiguous_skipped`) |
| **Désactivé** (165, 550) | 2 (dans l'une des lignes ci-dessus ou en 5ᵉ catégorie, H1/H2) | **0** | non publié avec ou sans correction : un désactivé relevé de sa pièce retomberait sur `disabled_eqlogic` |
| **Total** | 119 réglés / **117 effectivement exposés** | **+3 attendus (0 à 5)** | |

**Effet de la correction « exposition effective » seule :**
- **Statut de publication : aucun changement** (0 équipement) sur cette baseline ;
- **Dénominateur de parité** : 119 → **117** (au plus ; 165 et 550 sont dans les 119, AC11 bis) ;
- **Cause** : sans correction, les 2 désactivés, s'ils sont en pièce exclue, seraient relevés (H1) puis retomberaient sur `disabled_eqlogic` en étant comptés comme exceptions HomeKit ; avec correction, leur raison reste `excluded_object` et ils ne sont pas comptés ;
- **Lecture de parité** : 70 sur 119 = **58,8 %** aujourd'hui (69 publiés + 1 partiel) ; 70 sur 117 = **59,8 %** avec la définition corrigée ; 73 sur 117 = **62,4 %** après 24.4 si les 3 attendus sont publiés. Le reste (environ 44, à 1 près selon l'écart de somme) est composé d'exclusions de plugin décidées, d'exclusions individuelles et d'un mapping ambigu, que 24.4 ne change volontairement pas.

**À retenir.** L'effet de production de 24.4 sur cette baseline est **faible** : +3 équipements publiés attendus, 5 au plus, déjà dans l'ordre de grandeur sur lequel Alexandre a décidé Q3 A le 12/10. Le risque de publication de masse est faible ; l'option C de Q3 ne se justifie pas à ce niveau (seuil de rappel : plus de 10, Task 0).

## Questions ouvertes restantes (avec recommandation)

| # | Question | Recommandation |
|---|---|---|
| **Q4-1** | Forme du champ d'exposition effective : nouveau champ additif `homekit_exposed_effective`, ou changer le sens de `homekit_exposed` ? | **Nouveau champ additif**, `schema_version` reste 1. Changer le sens de `homekit_exposed` serait une version 2. |
| **Q4-2** | Où calculer l'exposition effective : démon (helper) ou PHP (payload) ? | **Démon seul** : 24.1 inchangé, pas de nouveau champ de payload, un point de calcul pour projection et export. |
| **Q4-3** | `enabled` illisible : actif ou inconnu ? | **Actif par défaut**, comme le PHP (`class.php:875`) et le démon (`default=True`) ; l'exposition effective suit alors le réglage. |
| **Q4-4** | Raison d'un équipement désactivé, exposé, en pièce exclue : `excluded_object` ou `disabled_eqlogic` ? | **Conserver `excluded_object`** (ordre existant « Exclu > Désactivé », aucun changement de `assess_eligibility` hors la règle Q3 A). |
| **Q4-5** | Ajouter aussi `homekit_exposed_effective` aux scénarios (avec `active`) ? | **Oui**, même helper, symétrie pour les consommateurs ; sans effet sur la baseline (les 5 scénarios exposés sont en parité totale). |
| **Q4-6** | Rouvrir Q3 (option C : clé « projection HomeKit par défaut ») maintenant que le nombre est de 3 à 5 et non plus seulement 3 ? | **Non** : A est maintenue ; rappel à Alexandre seulement si la Task 0 donne plus de 10. |
| **Q4-7** | Qui lève l'écart de somme de la baseline (49 vs 50) et place 165 / 550 (H1 / H2) ? | **ClaudeBox**, par le croisement `enabled` × `reason` de la Task 0, avant `ready-for-dev`. |
| **Q4-8** | Surface de l'écran : l'epic 25 (état unique `resolveEquipmentState`, route `getEquipmentStates`) remplace les compteurs de 22.2 (clos) ; la source de décision additive `exception_homekit` doit-elle y apparaître ? | **À vérifier au dev** (lire 25-1 / 25-2 au début du dev, non relus par cette session) ; rester sur **un seul calcul**, sans second état parallèle ; gate 20-0 si l'écran change. |
| **Q4-9** | Ordre : 24.4 directement après la baseline si 24.3 est abandonnée ? | **Oui** (voir la recommandation de 24.3). |

## Garde-fous

- Le plugin n'écrit pas l'exposition HomeKit ni la configuration Homebridge (exigence 5).
- Pas de publication de masse sans la liste préalable de la Task 0.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

*Levé le 20/10 par la baseline :* le nombre d'équipements exposés écartés par leur pièce (5, dont 3 attendus relevables). *Reste :* la place exacte de 165 et 550 et l'écart de somme de la baseline (Task 0) ; si l'état global « exclure » est réellement utilisé ; l'effet exact de la nouvelle source de décision sur l'écran de l'epic 25 (état unique) et sur le gate 20-0 (Q4-8) ; les 5 équipements « pièce exclue » n'ont pas été individuellement vérifiés (mapping, commandes). Aucune exécution : lecture du code (`topology.py:354-387`, `decision_export.py:315-345`, `published_scope.py:93-122`) et des documents seulement.

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q3 A, Q4 A ; Q1 « exclu par plugin » conservé (pas de `voie_native`). Reste `draft` jusqu'au `create-story` après la baseline.
- 2026-10-20 — **create-story** (session cloud déléguée, documentaire) : intègre la baseline du 20/10 ; ajoute la correction « exposition effective » (`homekit_exposed` ET `enabled`) à l'export (champ additif `homekit_exposed_effective`, `schema_version` inchangé) et à la projection (helper unique, désactivé jamais traité comme exposé) ; chiffre l'effet (+3 attendus, 5 au plus, 0 pour les autres causes ; parité 70/119 → 70/117, 73/117 après 24.4) ; remplace l'estimation provisoire de la Task 0 ; AC1 et AC4 amendés, AC11 et AC12 ajoutés ; Q4-1 à Q4-9 avec recommandation. **Story laissée `draft`, `ready-for-dev` non accordé.**
- 2026-10-21, 00:10 — **Task 0 faite par ClaudeBox** (export 24.2 lu sur la box `ff2fe0d`+, sync du 20/10 03:05 UTC, lecture seule) : 119 exposés ; 69 publiés, 1 partiel (585, `ambiguous_skipped`), 49 non publiés = 41 `excluded_plugin` + 3 `excluded_eqlogic` + 5 `excluded_object`. **Écart de somme levé** : l'« ambigu » de la baseline est l'équipement partiel, pas un non publié. **165 et 550** sont désactivés **et** en pièce exclue (raison `excluded_object`) : exposition effective fausse, aucun changement attendu. Équipements actifs, exposés, écartés par la pièce : **3** (502, 503, 516), égal à l'attendu, sous le seuil de rappel (10) → Q3 A maintenue sans retour vers Alexandre.
- 2026-10-21, 00:10 — **Décisions ClaudeBox** (délégation d'Alexandre sur les décisions de story selon recommandations) : **Q4-1 à Q4-9 = recommandations** (champ additif `homekit_exposed_effective`, `schema_version` 1 ; calcul au démon seul ; `enabled` illisible = actif ; raison `excluded_object` conservée ; champ aussi sur les scénarios ; Q3 A maintenue ; Q4-8 vérifiée au dev, un seul calcul ; 24.4 suit directement la baseline). **`ready-for-dev` accordé.**

