---
type: ux-artifact
scope: pe-epic-6
gate: bloquant - stories 6-1 et 6-3
date: 2026-04-19
status: canonique-opposable
version: 2
stories_gated:
  - "6-1"
  - "6-3"
source_contracts:
  - pe-epic-6-traceability-contract.md
  - pipeline-contract.md
  - pe-epic-5-gov-reference-micro-protocol.md
  - pe-epic-5-governance-exceptions-register.md
  - cause_mapping.py (baseline v4.3)
---

# UX - Surface de diagnostic enrichie - pe-epic-6

**Statut :** artefact gate bloquant. Les stories 6-1 et 6-3 ne peuvent pas être marquées `done` sans conformité à ce document.

## 1. Principe fondamental

### 1.1 Source unique de la cause canonique

Cause canonique affichable = `publication_decision_ref.reason` (étape 4), exposée côté diagnostic via `traceability.decision_trace.reason_code`.

- La cause canonique ne vient jamais de `publication_trace`.
- La cause canonique ne vient jamais de `technical_reason_code`.
- La cause canonique ne vient jamais d'un mapping frontend local.

### 1.2 Séparation obligatoire décision (step 4) / résultat technique (step 5)

Deux dimensions coexistent et ne se remplacent jamais :

1. Décision pipeline (étapes 1-4) : pourquoi le moteur a décidé de publier ou non.
2. Résultat technique (étape 5) : succès/échec MQTT lors de la tentative effective.

**Invariant I7 opposable :**
`technical_reason_code` (step 5) ne doit jamais alimenter `decision_trace.reason_code`.

### 1.3 Lecture UX attendue

La UI présente simultanément :

1. Un statut global (`publie`, `non_publie`, `erreur_technique`).
2. Une étape de pipeline visible (1 -> 5).
3. Une cause canonique unique (`cause_label`) et son action (`cause_action`) dérivées uniquement de `decision_trace.reason_code`.
4. Un bloc technique séparé quand step 5 échoue.

## 2. Modèle de données UI

### 2.1 Entrées backend obligatoires

| Champ backend | Rôle UX | Source contractuelle |
|---|---|---|
| `traceability.decision_trace.reason_code` | clé canonique pour `cause_label` / `cause_action` et étape bloquante | `publication_decision_ref.reason` |
| `traceability.decision_trace.ha_entity_type` | contexte de rendu (notamment cas GOV) | step 2/4 |
| `traceability.decision_trace.confidence` | contexte d'explication (ambigu/politique de confiance) | step 2/4 |
| `traceability.publication_trace.last_discovery_publish_result` | statut technique `success|failed|not_attempted` | step 5 |
| `traceability.publication_trace.technical_reason_code` (optionnel) | détail technique d'échec MQTT | step 5 |
| `ecart` | affichage colonne Cause (uniquement si écart) | contrat 4D |

### 2.2 Champs UI dérivés autorisés (et uniquement ceux-ci)

| Champ UI dérivé | Règle |
|---|---|
| `global_status` | `erreur_technique` si `last_discovery_publish_result="failed"`; sinon `publie` si `decision_trace.reason_code="published"`; sinon `non_publie` |
| `pipeline_blocking_step` | mapping strict du tableau §2.4 |
| `cause_label` | mapping strict du tableau §2.3 à partir de `decision_trace.reason_code` |
| `cause_action` | mapping strict du tableau §2.3 à partir de `decision_trace.reason_code` |
| `technical_label` / `technical_action` | mapping du tableau technique §2.5 à partir de `technical_reason_code` |

Aucun autre calcul métier frontend n'est autorisé.

### 2.3 Mapping strict `decision_trace.reason_code -> cause_label / cause_action`

Table normative opposable pour stories 6-1 et 6-3.

| `decision_trace.reason_code` | `cause_label` obligatoire | `cause_action` obligatoire | Mode de rendu |
|---|---|---|---|
| `published` | `Publication autorisee par le pipeline` | `null` | Succès. Pas de bloc Action. |
| `excluded` | `Equipement hors scope de synchronisation` | `Retirer l'exclusion dans les reglages jeedom2ha.` | `Action` |
| `disabled_eqlogic` | `Equipement desactive dans Jeedom` | `Activer l'equipement dans Jeedom puis relancer un diagnostic.` | `Action` |
| `no_commands` | `Equipement sans commandes exploitables` | `Verifier les commandes actives de l'equipement dans Jeedom.` | `Action` |
| `no_generic_type_configured` | `Types generiques non configures` | `Configurer les types generiques puis relancer un rescan.` | `Action` |
| `no_supported_generic_type` | `Type d'equipement non supporte dans ce cycle` | `Aucune action cote Jeedom : composant non pris en charge dans ce cycle.` | `Informatif` |
| `ambiguous_skipped` | `Mapping ambigu - plusieurs types possibles` | `Precisser les types generiques pour lever l'ambiguite.` | `Action` |
| `confidence_policy_skipped` | `Confiance insuffisante pour la politique active` | `Assouplir la politique de confiance si vous souhaitez publier les cas probables.` | `Action` |
| `low_confidence` | `Confiance insuffisante pour la politique active` | `Assouplir la politique de confiance si vous souhaitez publier les cas probables.` | `Action` |
| `ha_missing_command_topic` | `Projection HA invalide - commande d'action manquante` | `null` | `FR33` |
| `ha_missing_state_topic` | `Projection HA invalide - commande d'etat manquante` | `null` | `FR33` |
| `ha_missing_required_option` | `Projection HA invalide - option requise manquante` | `null` | `FR33` |
| `ha_component_unknown` | `Composant Home Assistant non reconnu par le moteur` | `null` | `FR33` |
| `ha_component_not_in_product_scope` | `Composant Home Assistant non ouvert dans ce cycle` | `Decision de gouvernance active : voir reference GOV-PE5-xxx associee.` | `Informatif` |
| *fallback non catalogué* | `Cause non classee` | `Relancer un diagnostic et remonter les logs daemon.` | `Informatif` |

Règle FR33 obligatoire quand `cause_action = null` :

- Message standard : `Aucune action directe disponible - la contrainte depend de la structure de l'appareil.`
- Message court (`ha_component_unknown`) : `Aucune action disponible pour ce composant.`

### 2.4 Mapping strict `decision_trace.reason_code -> step bloquante`

| `decision_trace.reason_code` | Step visible |
|---|---|
| `excluded`, `disabled_eqlogic`, `no_commands`, `no_generic_type_configured` | Step 1 - Eligibilite |
| `ambiguous_skipped`, `no_supported_generic_type` | Step 2 - Mapping |
| `ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown` | Step 3 - Validation Home Assistant |
| `confidence_policy_skipped`, `low_confidence`, `ha_component_not_in_product_scope` | Step 4 - Decision de publication |
| `published` + publication `success` | Step 5 - Publie |
| `published` + publication `failed` | Step 5 - Echec technique |

### 2.5 Mapping technique (step 5 uniquement)

| `technical_reason_code` | `technical_label` | `technical_action` |
|---|---|---|
| `discovery_publish_failed` | `Echec de publication MQTT discovery` | `Verifier la connexion au broker MQTT puis relancer un diagnostic.` |
| `local_availability_publish_failed` | `Echec de publication MQTT availability` | `Verifier la connexion au broker MQTT puis relancer un diagnostic.` |
| *absent* | `Aucun incident technique` | `null` |

## 3. Règles d'affichage (DO / DON'T)

### 3.1 DO - Ce que l'UI DOIT toujours faire

1. Afficher l'indicateur pipeline 5 étapes dans l'accordéon diagnostic.
2. Calculer `cause_label` et `cause_action` uniquement depuis `decision_trace.reason_code`.
3. Afficher une cause canonique unique par équipement.
4. Afficher le statut global avec 3 valeurs possibles : `publie`, `non_publie`, `erreur_technique`.
5. Afficher les blocs `Decision pipeline` et `Resultat technique` séparément quand step 5 échoue.
6. Afficher FR33 quand `cause_action = null`.
7. Afficher `cause_label` en colonne Cause pour tout équipement avec `ecart = true`.
8. Rendre les blocages step 1-4 en orange; réserver le rouge aux échecs techniques step 5.
9. Afficher une référence `GOV-PE5-xxx` pour tout `ha_component_not_in_product_scope`.
10. Laisser une traçabilité lisible en review : une assertion visuelle doit pouvoir pointer 1 code backend -> 1 rendu UI.

### 3.2 DON'T - Ce que l'UI NE DOIT JAMAIS faire

1. Afficher `technical_reason_code` comme cause principale.
2. Utiliser `reason_code` top-level pour écraser `decision_trace.reason_code`.
3. Fusionner les blocs décisionnels et techniques dans le cas step 5 failed.
4. Afficher un code brut (`ha_missing_command_topic`, etc.) comme texte utilisateur principal.
5. Utiliser le rouge pour un blocage step 1-4.
6. Afficher un bouton/lien d'action quand le mode est `Informatif` ou `FR33`.
7. Laisser un équipement en écart sans `cause_label` visible.
8. Masquer l'étape bloquante ou l'indicateur pipeline.
9. Créer une table de mapping JS locale différente du mapping contractuel de ce document.
10. Introduire un wording ad hoc non tracé en PR review.

## 4. Cas d'usage UI (table ou scénarios)

Notation pipeline : `1 2 3 4 5` avec `V=valide`, `B=bloque`, `N=non atteint`, `T=echec technique`.

| ID | Cas obligatoire | Entrée backend minimale | Attendu UI obligatoire |
|---|---|---|---|
| CU-1 | Non publication step 1 (inéligible) | `decision_trace.reason_code=no_commands` | Pipeline `1B 2N 3N 4N 5N`; statut `non_publie`; cause/action step 1 |
| CU-2 | Non publication step 2 (ambigu) | `decision_trace.reason_code=ambiguous_skipped` | Pipeline `1V 2B 3N 4N 5N`; statut `non_publie`; cause ambiguë + action de précision |
| CU-3 | Non publication step 3 (invalidité HA) | `decision_trace.reason_code=ha_missing_command_topic` | Pipeline `1V 2V 3B 4N 5N`; statut `non_publie`; cause step 3 + FR33 |
| CU-4 | Non publication step 4 (politique) | `decision_trace.reason_code=low_confidence` | Pipeline `1V 2V 3V 4B 5N`; statut `non_publie`; action sur politique de confiance |
| CU-5 | Publication réussie | `decision_trace.reason_code=published` + `last_discovery_publish_result=success` | Pipeline `1V 2V 3V 4V 5V`; statut `publie`; aucun bloc technique |
| CU-6 | Echec technique step 5 | `decision_trace.reason_code=published` + `last_discovery_publish_result=failed` + `technical_reason_code=discovery_publish_failed` | Pipeline `1V 2V 3V 4V 5T`; statut `erreur_technique`; deux blocs séparés (Decision + Technique) |
| CU-7 | Cas ambigu / confidence_policy | `decision_trace.reason_code=confidence_policy_skipped` | Pipeline `1V 2V 3V 4B 5N`; statut `non_publie`; cause politique de confiance (pas ambiguïté générique) |
| CU-8 | Cas hors scope produit (GOV) | `decision_trace.reason_code=ha_component_not_in_product_scope` + `ha_entity_type` | Pipeline `1V 2V 3V 4B 5N`; statut `non_publie`; cause informative + référence GOV-PE5-xxx |

### 4.1 Rendu obligatoire du cas technique (CU-6)

Quand step 5 échoue, l'accordéon contient obligatoirement :

1. Bloc `Decision pipeline` : rappelle explicitement que les étapes 1-4 sont validées (`published`).
2. Bloc `Resultat technique` : détaille `technical_reason_code` et action MQTT.

Sans ces deux blocs séparés, la review est en `request changes` (violation I7).

### 4.2 Références GOV obligatoires pour CU-8

Pour `ha_component_not_in_product_scope`, afficher l'ID actif du registre :

| `ha_entity_type` | Référence |
|---|---|
| `sensor` | `GOV-PE5-001` |
| `binary_sensor` | `GOV-PE5-002` |
| `button` | `GOV-PE5-003` |
| `number` | `GOV-PE5-004` |
| `select` | `GOV-PE5-005` |
| `climate` | `GOV-PE5-006` |

Si le composant n'a pas d'ID actif, la non-ouverture est non conforme et non opposable.

## 5. Anti-patterns interdits

| Anti-pattern | Pourquoi interdit | Verdict review |
|---|---|---|
| `cause_label` dérivé de `technical_reason_code` | Confusion cause canonique / incident technique | KO immédiat |
| Colonne Cause vide alors que `ecart=true` | Perte d'explicabilité utilisateur | KO |
| Bouton d'action pour un message `Aucune action...` | Fausse promesse d'action | KO |
| Rouge sur step 2/3/4 | Faux signal d'incident infrastructure | KO |
| Un seul bloc pour le cas step 5 failed | Violation I7 | KO immédiat |
| Code brut backend affiché comme libellé principal | UX non lisible, non contractuelle | KO |
| Absence de référence GOV sur un hors-scope | Non conformité au micro-protocole GOV-PE5-xxx | KO |
| Mapping frontend différent du tableau §2.3 | Contrat non déterministe, non testable | KO |

## 6. Contrats avec le backend

### 6.1 Contrats normatifs opposables

1. **C-BE-01 (source unique)** : la cause canonique UI provient de `publication_decision_ref.reason` via `decision_trace.reason_code`.
2. **C-BE-02 (I7)** : `technical_reason_code` ne peut pas alimenter `decision_trace.reason_code`.
3. **C-BE-03 (mapping)** : `cause_label`/`cause_action` suivent strictement le tableau §2.3.
4. **C-BE-04 (étapes)** : l'étape affichée suit strictement le tableau §2.4.
5. **C-BE-05 (step 5)** : en cas d'échec technique, deux blocs séparés sont obligatoires.
6. **C-BE-06 (FR33)** : `cause_action=null` implique un message explicite "Aucune action...".
7. **C-BE-07 (GOV)** : tout `ha_component_not_in_product_scope` affiche une référence `GOV-PE5-xxx` active.
8. **C-BE-08 (non-régression additive)** : aucun champ historique n'est supprimé/renommé; enrichissement additif uniquement.

### 6.2 Clause story 6-3 (alignement `cause_mapping.py`)

Le baseline v4.3 contient encore des `cause_action` non null sur `ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`.

Pour la conformité story 6-3 avec ce contrat UX :

1. Ces trois codes doivent produire `cause_action = null`.
2. Le rendu UI doit afficher FR33 (pas d'action directe).

### 6.3 Gate de validation terrain avant `done`

**Story 6-1 - gate terrain :**

1. Vérifier CU-1 à CU-6 sur navigation réelle.
2. Vérifier que chaque équipement affiche exactement une étape bloquante.
3. Vérifier que le cas step 5 failed montre 2 blocs séparés.

**Story 6-3 - gate terrain :**

1. Vérifier le mapping strict §2.3 pour chaque code couvert.
2. Vérifier FR33 pour tous les cas `cause_action=null`.
3. Vérifier la présence des références GOV pour `ha_component_not_in_product_scope`.

Tout écart à ces checks rend la PR non conforme à cet artefact.

---

## Décision d'application

Ce document fait foi pour la préparation et la review des stories 6-1 et 6-3.
Toute implémentation qui diverge doit soit :

1. Mettre à jour ce document avant merge, avec justification explicite.
2. Ou être refusée en review (`request changes`).
