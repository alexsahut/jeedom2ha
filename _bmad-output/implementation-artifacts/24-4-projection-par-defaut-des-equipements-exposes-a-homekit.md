# Story 24.4 : Projection par défaut des équipements exposés à HomeKit

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft` jusqu'à son `create-story` après la baseline.** Rédigé par une session cloud déléguée, documentaire. **Change la production** : des équipements aujourd'hui exclus par leur pièce seront publiés au sync suivant. Décisions d'Alexandre (12/10 à 13:22) : **Q3 A** et **Q4 A** ; ex-décisions attendues **Q3** (la pièce n'écarte plus) et **Q4** (mapping ambigu ou probable) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
>
> **R1 (ClaudeBox, 12/10) intégrée** : *établi par ClaudeBox le 12/10*, d'après la configuration actuelle du plugin (inchangée depuis le 04/10) et le référentiel du 10/10, **3 équipements** (virtuels, dans deux pièces exclues) seraient nouvellement publiés. Le risque de publication de masse est faible ; l'option C de Q3 ne se justifie plus. Le signal d'exposition suit la règle de Homebridge (24-1) : pièce + équipement + valeur par défaut.

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q3 A** : un équipement exposé à HomeKit n'est jamais écarté par sa pièce (`excludedObjects` et état de pièce hérité) ; l'exclusion explicite de l'équipement et l'état global « exclure » restent respectés. Options B et C **écartées**.
- **Q4 A** : l'exposition HomeKit ne change pas la politique de confiance ; option B **écartée**.
- **Q1** : « exclu par plugin » conservé : `excluded_plugin` garde sa priorité (équipement > plugin > pièce) sur le signal HomeKit ; **pas de `voie_native`**.
- Cette story reste `draft` jusqu'à son `create-story`, après la baseline de 24.2.

## Story

En tant qu'utilisateur qui pilote sa maison par la voix dans Apple Maison,
je veux que tout équipement exposé à HomeKit soit projeté dans Home Assistant par défaut, sans que l'exclusion de sa pièce ne l'écarte,
afin que ce qui se pilote ou se consulte par la voix le soit aussi par Assist, sans configurer la maison deux fois.

**Parcours : démon + libellés de l'écran et de la configuration.** Gate 20-0 et `ready-for-UX-validation` avant `done`.

## Dépendances et décisions

- Dépend de **24.1** (signal) et **24.2** (mesure + baseline). Si 24.3 (mode « plugins en test ») est maintenue, elle passe avant (mêmes fonctions de configuration) ; sinon 24.4 suit directement la baseline.
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

- **AC1.** Un équipement `homekit_exposed = true` n'est jamais écarté par `excludedObjects` ni par un état de pièce « exclure » hérité. À l'éligibilité (`assess_eligibility`), la source `object` est ignorée pour lui ; dans le résolveur de périmètre, la pièce exclue ne s'applique pas à lui sauf état d'équipement explicite (même règle que le sync, « Publier », l'aperçu et le diagnostic : un seul calcul).
- **AC2.** Le périmètre publié signale ces équipements comme exceptions (`is_exception`, `decision_source` additive, par exemple `exception_homekit`) pour que les compteurs de pièce et le bandeau restent cohérents ; contrat additif, aucun champ existant modifié.
- **AC3.** L'exclusion explicite d'un équipement exposé (override `exclude_eqlogic`, état d'équipement « exclure », `jeedom2ha_excluded`) l'écarte toujours, avec sa raison.
- **AC4.** Un équipement non exposé (`false`) ou au signal inconnu (`null`) garde exactement le comportement actuel ; un équipement dont le signal est `null` n'est **jamais** traité comme exposé.
- **AC5.** **Chaque commande** d'un équipement exposé a, dans l'export, une décision, une raison canonique non vide et son étape ; aucune commande « sans raison » (test sur le corpus golden et sur les fixtures de 24.1).
- **AC6.** Q4 A : la politique de confiance et le forçage restent le levier des mappings ambigus ou probables ; aucun forçage automatique par le signal HomeKit.
- **AC7.** Libellés : la configuration « Pièces exclues » et `docs/fr_FR/index.md` disent « sauf équipements exposés à HomeKit » ; la cause `excluded_object` n'apparaît plus pour un équipement exposé ; aucune cause trompeuse à l'écran.
- **AC8.** Les équipements nouvellement publiés le sont par le chemin normal (découverte, état initial, disponibilité) ; aucun `entity_id` ni `unique_id` d'entité déjà publiée ne change.
- **AC9.** `PRODUCT_SCOPE`, mapping, golden et contrat 4D inchangés, sauf champs additifs justifiés ; gate 20-0 vert ; aucun nom réel dans le dépôt (CC-48).
- **AC10.** Preuve terrain par ClaudeBox : liste préalable (identifiants) des équipements exposés écartés par la pièce, tirée de l'export ; après déploiement, ces équipements sont publiés (ou ont une autre raison canonique) ; inventaires MQTT et registres de HA avant/après ; retour arrière vérifié sur un équipement de test (« Supprimer de Home Assistant » puis exclusion explicite) ; export « après » comparé à la baseline.

## Tâches proposées

- [ ] **Task 0 — Confirmation préalable (ClaudeBox, à partir de l'export de 24.2)** : les identifiants des équipements exposés écartés par la pièce (attendu : 3, *établi par ClaudeBox le 12/10*) ; si l'export en donne nettement plus, revenir vers Alexandre (option C de Q3) avant de coder.
- [ ] **Task 1 — Démon** : règle dans `assess_eligibility` et dans `resolve_published_scope` ; source de décision additive ; un seul point de calcul partagé par sync, « Publier », aperçu, diagnostic.
- [ ] **Task 2 — Libellés** (configuration, écran, `docs/fr_FR`).
- [ ] **Task 3 — Tests** : exposé / non exposé / inconnu × pièce exclue × exclusion explicite × état global ; parité sync / « Publier » / aperçu ; golden ; export.
- [ ] **Task 4 — Gate 20-0 + déploiement + preuve terrain (humain)**.

## Garde-fous

- Le plugin n'écrit pas l'exposition HomeKit ni la configuration Homebridge (exigence 5).
- Pas de publication de masse sans la liste préalable de la Task 0.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Combien d'équipements exposés sont écartés par leur pièce aujourd'hui ; si l'état global « exclure » est réellement utilisé ; l'effet exact de la nouvelle source de décision sur les compteurs de pièce de 22-2 et sur le gate 20-0.

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q3 A, Q4 A ; Q1 « exclu par plugin » conservé (pas de `voie_native`). Reste `draft` jusqu'au `create-story` après la baseline.
