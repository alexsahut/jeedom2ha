---
type: sprint-change-proposal
project: jeedom2ha
phase: post_mvp_phase_1
version_label: v1.1_pilotable
date: 2026-03-26
status: approved
approved_by: Alexandre
scope_classification: moderate
trigger: post-epic-3-ux-review
impacts:
  - prd-post-mvp-v1-1-pilotable.md
  - ux-delta-review-post-mvp-v1-1-pilotable.md
  - architecture-delta-review-post-mvp-v1-1-pilotable.md
  - epics-post-mvp-v1-1-pilotable.md
  - sprint-status.yaml
---

# Sprint Change Proposal — Recadrage UX V1.1 Pilotable

## 1. Résumé du problème

### Déclencheur

Post-Epic 3 (done), avant démarrage d'Epic 4 (backlog). Revue critique de l'interface combinée à un export réel de la box (278 équipements, 99 inclus, 179 exclus).

### Problème fondamental

L'interface de la console V1.1 expose directement le modèle d'implémentation interne à l'utilisateur. La taxonomie backend à 6 statuts (`Publié`, `Partiellement publié`, `Ambigu`, `Exclu`, `Non supporté`, `Incident infrastructure`), les concepts `Hérite de la pièce` / `Exception locale`, la confiance tripartite (`Sûr`/`Probable`/`Ambigu`) et le compteur séparé `Exceptions` sont projetés tels quels dans l'UI au lieu d'être traduits en modèle mental utilisateur.

### Preuves concrètes

| Constat | Impact |
|---|---|
| 278 équipements, diagnostic sur l'ensemble | Diagnostic illisible — l'utilisateur ne distingue pas les 99 in-scope des 179 exclus |
| Compteur "Exceptions" en console | Masque des exclusions plugin — le terme ne correspond pas au vécu utilisateur |
| "Hérite de la pièce" / "Exception locale" | Vocabulaire d'implémentation, pas de modèle mental naturel |
| Confiance (Sûr/Probable/Ambigu) visible en console | Information technique qui ne parle pas à l'utilisateur moyen |
| "Ambigu" et "Non supporté" comme statuts principaux | Mélange un état de publication avec une cause de non-publication |
| "Partiellement publié" | Statut fourre-tout anxiogène, sans explication claire |

### Catégorie

Désalignement entre modèle d'implémentation et modèle utilisateur, découvert après livraison des Epics 1-3. Le backend est sain — le problème est purement dans la couche de présentation et le contrat UI.

---

## 2. Analyse d'impact

### 2.1 Impact epics

| Epic | Statut | Impact du recadrage |
|---|---|---|
| **Epic 1** (done) | Resolver canonique, console 3 niveaux | **Faible.** Le resolver `inherit/include/exclude` reste valide en interne. Seule la couche UI cesse d'exposer "Hérite de la pièce", "Exception locale" et le compteur "Exceptions". |
| **Epic 2** (done) | Santé minimale du pont | **Aucun.** Le bandeau santé et le contrat (démon, broker, synchro, opération) restent inchangés. |
| **Epic 3** (done) | Moteur de statuts et explicabilité | **Significatif.** La taxonomie à 6 statuts est remplacée par le modèle Périmètre/Statut/Écart/Cause. Les `reason_code` backend restent stables, seule leur exposition UI change via un nouveau contrat `cause_code`/`cause_label`. |
| **Epic 4** (backlog) | Opérations HA | **Modéré.** L'epic reste pertinent mais est renuméroté Epic 5. Ses stories doivent utiliser le nouveau vocabulaire. |

### 2.2 Impact artefacts

| Artefact | Niveau d'impact | Sections touchées |
|---|---|---|
| PRD V1.1 | Modéré | §6, §8.1, §8.3, §9 — vocabulaire et modèle de statuts |
| UX delta review | Significatif | §5.3, §6.1, §6.2 — remplacement du modèle 4 dimensions + nouvelles sections |
| Architecture delta review | Modéré | §6.2, §8.2, §8.3 — ajout concept Écart, alignement contrat |
| Epics | Significatif | Nouvel Epic 4, renumérotation Epic 5, alignement stories Epic 5 |
| sprint-status.yaml | Modéré | Ajout epic-4 (recadrage), renumérotation epic-5 |
| Code frontend (JS) | Significatif | Refactoring vocabulaire, scope diagnostic, placement confiance |
| Code backend (Python) | Modéré | Ajout dimension Écart dans le contrat JSON, couche cause_code/cause_label |
| Tests | Modéré | Assertions sur labels et vocabulaire |

### 2.3 Impact technique

Le backend (daemon Python) est solide et non remis en cause. Les changements sont :

1. Ajout de la dimension "Écart" dans le contrat JSON backend → frontend (booléen bidirectionnel)
2. Ajout d'une couche de traduction `reason_code` → `cause_code`/`cause_label` pour le contrat UI
3. Simplification de la taxonomie de statuts exposée (6 valeurs → 2 : Publié / Non publié)
4. Refactoring du vocabulaire de périmètre (inherit → source d'exclusion explicite)
5. Filtrage du diagnostic utilisateur aux équipements in-scope uniquement
6. Déplacement de la confiance vers la page diagnostic technique uniquement

Le resolver canonique (Epic 1), le contrat de santé (Epic 2), et les `reason_code` (Epic 3) restent valides comme infrastructure backend. Seule la couche de présentation vers l'utilisateur change.

---

## 3. Décisions de recadrage verrouillées

### D1 — Modèle utilisateur à 4 dimensions : Périmètre → Statut → Écart → Cause

| Dimension | Question utilisateur | Valeurs |
|---|---|---|
| **Périmètre** | "Cet équipement fait-il partie de mon scope ?" | `Inclus` · `Exclu par la pièce` · `Exclu par le plugin` · `Exclu sur cet équipement` |
| **Statut** | "Est-il projeté dans Home Assistant ?" | `Publié` · `Non publié` |
| **Écart** | "Y a-t-il un désalignement ?" | Oui / Non (bidirectionnel) |
| **Cause** | "Pourquoi ce statut ou cet écart ?" | Libellés métier explicites |

### D2 — Disparition du concept "exception"

Le terme "exception" disparaît de l'interface utilisateur. Les exclusions sont toujours exprimées par leur source.

| Ancien vocabulaire | Nouveau vocabulaire |
|---|---|
| "Exception locale" | "Exclu sur cet équipement" |
| "Hérite de la pièce" | Concept supprimé — si inclus, c'est "Inclus" ; si exclu via la pièce, c'est "Exclu par la pièce" |
| Compteur "Exceptions" | Supprimé — les exclusions sont comptées par source en niveau secondaire |

### D3 — Confiance visible uniquement en diagnostic

Les badges `Sûr` / `Probable` / `Ambigu` ne sont plus visibles dans la console principale. Ils restent disponibles dans la page diagnostic technique détaillée.

### D4 — Diagnostic utilisateur centré sur les équipements in-scope

Le diagnostic principal (console) ne porte que sur les équipements inclus dans le périmètre publié. Les exclus restent visibles dans la synthèse du périmètre avec leur source d'exclusion. L'export support complet (tout le parc) reste disponible.

### D5 — Écart bidirectionnel

L'écart est un booléen calculé par le backend : il y a écart quand la décision locale et l'état projeté ne sont pas alignés, dans les deux sens :

| Décision locale | État projeté | Écart | Cause type |
|---|---|---|---|
| Inclus | Publié | Non | — |
| Inclus | Non publié | **Oui** | Mapping ambigu, Type non supporté, Bridge indisponible… |
| Exclu | Non publié | Non | — |
| Exclu | Publié | **Oui** | Changement en attente d'application |

### D6 — Cause explicite et métier

La cause est exprimée via un `cause_code` et un `cause_label` dans le contrat UI. Ces champs sont **dérivés** des `reason_code` backend stables d'Epic 3, pas un remplacement. Le backend produit les deux niveaux :

- `reason_code` : stable, technique, hérité d'Epic 3 — non exposé en UI
- `cause_code` / `cause_label` : contrat UI canonique, dérivé du `reason_code`, exprimant la cause métier pour l'interface

### D7 — Console et diagnostic partagent la même taxonomie de base

La console et le diagnostic utilisent le même modèle Périmètre/Statut/Écart/Cause. Le diagnostic ajoute un niveau de détail supplémentaire (confiance, commandes observées, typage Jeedom).

### D8 — Aucun concept interne dans le frontend

Les termes suivants ne doivent plus apparaître dans l'interface utilisateur :
`inherit`, `decision_source`, `exception locale`, `is_exception`, `exclude`/`include` en anglais, `Partiellement publié` comme statut principal.

### D9 — Mapping complet ancien → nouveau modèle

| Ancien statut (Epic 3) | Nouveau modèle |
|---|---|
| `Publié` | Périmètre=Inclus, Statut=Publié, Écart=Non |
| `Partiellement publié` | Périmètre=Inclus, Statut=Publié, Écart=Non *(le détail vit en diagnostic)* |
| `Exclu` | Périmètre=Exclu par [source], Statut=Non publié, Écart=Non |
| `Ambigu` | Périmètre=Inclus, Statut=Non publié, Écart=Oui, Cause=Mapping ambigu |
| `Non supporté` | Périmètre=Inclus, Statut=Non publié, Écart=Oui, Cause=Type non supporté |
| `Incident infrastructure` | Statut=Non publié, Écart=Oui, Cause=Bridge indisponible *(+ bandeau santé)* |

---

## 4. Verrouillages explicites

### V1 — Statut binaire : portée exacte

Le statut binaire `Publié` / `Non publié` s'applique **exclusivement au niveau équipement**.

Au niveau pièce et global, la lecture principale repose sur les **compteurs**. Il n'y a pas de statut agrégé pièce/global qui réutiliserait le champ `statut` du niveau équipement.

Si un indicateur visuel synthétique est conservé au niveau pièce ou global (par exemple un badge d'alerte quand `écarts > 0`), il doit être :
- défini comme un indicateur dérivé des compteurs, pas comme une extension du statut équipement ;
- nommé différemment (ex: "Écarts à traiter" au lieu de "Non publié") ;
- documenté séparément dans le contrat backend.

| Niveau | Lecture principale | Statut binaire Publié/Non publié |
|---|---|---|
| Équipement | Périmètre + Statut + Écart + Cause | **Oui** — seul niveau où il existe |
| Pièce | Compteurs (Total, Inclus, Exclus, Écarts) | **Non** — indicateur dérivé des compteurs seulement |
| Global | Compteurs (Total, Inclus, Exclus, Écarts) + Bandeau santé | **Non** — indicateur dérivé des compteurs seulement |

### V2 — Compteurs cibles figés

Les compteurs de la console, aux niveaux pièce et global, sont exactement :

| Compteur | Définition |
|---|---|
| **Total** | Nombre total d'équipements dans la pièce / dans le parc |
| **Inclus** | Équipements où `perimetre = inclus` |
| **Exclus** | Équipements où `perimetre` commence par `exclu_` |
| **Écarts** | Équipements où `ecart = true` |

Le compteur `Exceptions` disparaît complètement. Les détails par source d'exclusion sont disponibles en niveau secondaire.

Invariant arithmétique :
```
Total = Inclus + Exclus
Écarts ⊆ (Inclus ∪ Exclus)   // un écart peut exister dans les deux populations
```

### V3 — Contrat backend → UI explicite

Le backend fournit directement les 4 dimensions résolues. Le frontend ne fait aucune interprétation, aucune recomposition, aucun mapping local.

Distinction structurante entre les deux couches :
- `reason_code` : stable, technique, hérité d'Epic 3 — reste dans le backend, non exposé en UI
- `cause_code` / `cause_label` / `cause_action` : contrat UI canonique, dérivé par le backend à partir du `reason_code`

#### Forme cible du contrat par équipement

```json
{
  "jeedom_eq_id": 123,
  "name": "Lampe salon",
  "object_id": 5,
  "object_name": "Salon",

  "perimetre": "inclus",
  "statut": "publie",
  "ecart": false,

  "cause_code": null,
  "cause_label": null,
  "cause_action": null,

  "ha_type": "light"
}
```

Exemple — équipement exclu par la pièce :
```json
{
  "jeedom_eq_id": 456,
  "name": "Thermostat chambre",
  "object_id": 3,
  "object_name": "Chambre",

  "perimetre": "exclu_par_piece",
  "statut": "non_publie",
  "ecart": false,

  "cause_code": null,
  "cause_label": null,
  "cause_action": null,

  "ha_type": null
}
```

Exemple — inclus mais non publié (écart) :
```json
{
  "jeedom_eq_id": 789,
  "name": "Capteur exotique",
  "object_id": 5,
  "object_name": "Salon",

  "perimetre": "inclus",
  "statut": "non_publie",
  "ecart": true,

  "cause_code": "no_mapping",
  "cause_label": "Aucun mapping compatible",
  "cause_action": "Vérifier les types génériques des commandes dans Jeedom",

  "ha_type": null
}
```

Exemple — exclu mais encore publié (écart) :
```json
{
  "jeedom_eq_id": 101,
  "name": "Lampe entrée",
  "object_id": 2,
  "object_name": "Entrée",

  "perimetre": "exclu_sur_equipement",
  "statut": "publie",
  "ecart": true,

  "cause_code": "pending_unpublish",
  "cause_label": "Changement en attente d'application",
  "cause_action": "Republier pour appliquer le changement",

  "ha_type": "light"
}
```

#### Valeurs autorisées du champ `perimetre`

| Valeur backend | Libellé UI |
|---|---|
| `inclus` | Inclus |
| `exclu_par_piece` | Exclu par la pièce |
| `exclu_par_plugin` | Exclu par le plugin |
| `exclu_sur_equipement` | Exclu sur cet équipement |

#### Valeurs autorisées du champ `statut`

| Valeur backend | Libellé UI |
|---|---|
| `publie` | Publié |
| `non_publie` | Non publié |

#### Forme cible des compteurs par pièce

```json
{
  "object_id": 5,
  "object_name": "Salon",
  "compteurs": {
    "total": 12,
    "inclus": 8,
    "exclus": 4,
    "ecarts": 2
  },
  "equipements": []
}
```

#### Forme cible des compteurs globaux

```json
{
  "compteurs": {
    "total": 278,
    "inclus": 99,
    "exclus": 179,
    "ecarts": 5
  },
  "pieces": []
}
```

#### Règle absolue

Le frontend affiche ces champs tels quels. Il peut filtrer, trier, masquer. Il ne doit jamais :
- dériver un statut à partir d'autres champs ;
- recomposer une cause à partir de `cause_code` ;
- calculer un compteur localement ;
- inventer un libellé non fourni par le backend.

### V4 — Portée exacte du diagnostic

| Surface | Population | Contenu |
|---|---|---|
| **Console principale** (synthèse périmètre) | Tous les équipements | Compteurs + périmètre par source d'exclusion pour les exclus |
| **Diagnostic principal utilisateur** | Équipements in-scope uniquement (`perimetre = inclus`) | Statut, Écart, Cause, + détails commandes / typage / confiance |
| **Export support complet** | Tous les équipements (in-scope + exclus) | Vue technique exhaustive, incluant confiance, commandes, typage, reason_code |

Règles :
1. Le diagnostic principal utilisateur ne liste que les équipements dont `perimetre = inclus`.
2. Les détails commandes / typage / confiance ne concernent que ces équipements in-scope.
3. Les équipements exclus restent visibles dans la synthèse de périmètre avec leur source d'exclusion, mais ne produisent pas d'entrée diagnostic détaillée.
4. L'export support complet conserve la vue exhaustive — il n'est pas filtré par le périmètre.

### V5 — Cause d'écart : bidirectionnalité et libellés

L'écart est bidirectionnel. La cause distingue les deux directions.

#### Direction 1 : Inclus mais non publié

| `cause_code` | `cause_label` |
|---|---|
| `no_mapping` | Aucun mapping compatible |
| `ambiguous_skipped` | Mapping ambigu — plusieurs types possibles |
| `no_supported_generic_type` | Type non supporté en V1 |
| `no_generic_type_configured` | Types génériques non configurés sur les commandes |
| `disabled_eqlogic` | Équipement désactivé dans Jeedom |
| `no_commands` | Équipement sans commandes exploitables |
| `discovery_publish_failed` | Publication MQTT échouée |
| `infra_unavailable` | Bridge indisponible |

#### Direction 2 : Exclu mais encore publié

| `cause_code` | `cause_label` |
|---|---|
| `pending_unpublish` | Changement en attente d'application |

Le champ `cause_code` suffit à identifier la direction et la nature de l'écart. Le frontend ne détermine pas la direction par lui-même — le `cause_label` métier est autosuffisant.

---

## 5. Approche recommandée

### Chemin retenu : Nouvel Epic 4 + renumérotation de l'actuel Epic 4 en Epic 5

Le recadrage nécessite les deux : un nouvel epic dédié ET une modification de l'actuel Epic 4.

Justification :
1. Le recadrage touche le code déjà livré par Epics 1-3 → ce n'est pas le scope de l'actuel Epic 4 (opérations HA)
2. Le recadrage doit être terminé AVANT les opérations, car celles-ci utiliseront le nouveau vocabulaire
3. Les deux scopes sont distincts : refactoring du modèle de présentation ≠ ajout de flux d'opérations HA
4. Un rollback n'est pas nécessaire — le backend est sain
5. Le PRD V1.1 ne change pas de scope — la promesse produit est identique, mieux exprimée

### Alternatives écartées

| Alternative | Raison d'écart |
|---|---|
| Modifier uniquement l'actuel Epic 4 | Insuffisant : le recadrage touche le code Epics 1-3, pas le scope des opérations HA |
| Reporter le recadrage après les opérations | Dangereux : Epic 5 construirait les opérations sur un vocabulaire confus |
| Intégrer le recadrage dans l'actuel Epic 4 | Confusion de scope : mélanger refactoring UX et nouvelles opérations |
| Rollback partiel | Inutile : le backend est valide |

### Nouvel Epic 4 — Recadrage UX : modèle utilisateur Périmètre / Statut / Écart / Cause

**Objectif :** Aligner la console et le diagnostic sur le modèle mental utilisateur à 4 dimensions, en éliminant les concepts techniques internes de l'interface et en centrant le diagnostic sur les équipements in-scope.

**Valeur utilisateur :** L'utilisateur comprend immédiatement si un équipement est dans son périmètre, s'il est publié, s'il y a un écart et pourquoi — sans vocabulaire technique ni concepts d'implémentation.

**Périmètre in :**
- Refonte du contrat backend → UI : ajout dimension Écart, couche cause_code/cause_label, simplification taxonomie de statuts
- Vocabulaire d'exclusion par source, disparition du concept exception
- Déplacement de la confiance vers la page diagnostic
- Diagnostic centré sur les équipements in-scope
- Alignement console/diagnostic sur la même taxonomie de base

**Périmètre out :**
- Modification du resolver canonique (Epic 1 — ne change pas)
- Modification du contrat de santé (Epic 2 — ne change pas)
- Renommage des `reason_code` stables (Epic 3 — restent stables, seule la couche cause_code/cause_label est ajoutée)
- Opérations HA (Epic 5)
- Extension fonctionnelle (button, number, select, climate)

**Stories préliminaires identifiées :**

| Story | Scope |
|---|---|
| 4.1 | Contrat backend du modèle Périmètre/Statut/Écart/Cause |
| 4.2 | Vocabulaire d'exclusion par source — disparition du concept exception |
| 4.3 | Diagnostic centré in-scope et confiance en diagnostic uniquement |
| 4.4 | Intégration UI du nouveau modèle (console + scope summary) |

### Epic 5 — Opérations HA explicites, graduées et sûres (ex-Epic 4)

L'actuel Epic 4 est renuméroté Epic 5. Ses stories (5.1→5.4) restent pertinentes mais doivent être mises à jour pour utiliser le vocabulaire du nouveau modèle. Aucun changement de fond — uniquement un alignement terminologique.

---

## 6. Propositions de changement par artefact

### 6.1 PRD V1.1 (`prd-post-mvp-v1-1-pilotable.md`)

**Section 8.1** — Console de pilotage
- OLD : "Exceptions au niveau équipement dans chaque pièce."
- NEW : "Inclusion ou exclusion au niveau équipement, exprimée par sa source (pièce, plugin, équipement)."

**Section 8.3** — Explicabilité par équipement
- OLD : "Statut lisible : Publié, Exclu, Ambigu, Non supporté (et variantes opérationnelles)"
- NEW : "Modèle à 4 dimensions : Périmètre (Inclus / Exclu par [source]), Statut (Publié / Non publié), Écart (oui/non bidirectionnel), Cause (libellé métier explicite)."
- OLD : "Raison principale obligatoire"
- NEW : "Cause métier obligatoire"

**Section 6** — Objectifs
- Ajouter : "Centrer le diagnostic utilisateur sur les équipements in-scope."

**Section 9** — Definition of Done
- Point 2 : "exceptions" → "décisions d'inclusion/exclusion par équipement"
- Point 3 : "Les statuts par équipement" → "Le modèle Périmètre/Statut/Écart/Cause est lisible et cohérent"
- Point 4 : "raison lisible" → "cause métier lisible"

### 6.2 UX delta review (`ux-delta-review-post-mvp-v1-1-pilotable.md`)

**Section 5.3** — Rendre visible l'héritage de décision
- OLD : "Hérite de la pièce" / "Exception locale"
- NEW : L'héritage n'est plus un concept utilisateur. L'utilisateur voit directement le périmètre résolu par source.

**Section 6.1** — Dimensions
- OLD : Périmètre / État de projection / Raison principale / Impact en attente
- NEW : Périmètre / Statut / Écart / Cause

**Section 6.2** — Vocabulaire
- Supprimer : "Exception locale", "Hérite de la pièce", "Partiel" comme catégorie
- Ajouter : "Exclu par la pièce", "Exclu par le plugin", "Exclu sur cet équipement", "Écart"

**Nouvelles sections à ajouter :**
- Diagnostic centré in-scope (scope + justification + lien avec export support complet)
- Placement de la confiance (diagnostic technique uniquement)
- Table de mapping ancien → nouveau modèle (D9)

### 6.3 Architecture delta review (`architecture-delta-review-post-mvp-v1-1-pilotable.md`)

**Section 6.2** — Modèle de périmètre
- Clarifier : `inherit/include/exclude` reste la représentation interne du resolver. La couche de présentation traduit en labels source-based. Le frontend ne voit jamais `inherit`.

**Section 8.2** — Statuts principaux
- OLD : Publié, Exclu, Ambigu, Non supporté, Incident infrastructure
- NEW : Publié / Non publié (statut binaire) + Écart (booléen bidirectionnel) + Cause (libellé métier)

**Nouvelle section** — Définition architecturale de "Écart"
- Calcul : comparaison entre décision effective du resolver et état de projection réel
- Bidirectionnel : couvre inclus-non-publié ET exclu-encore-publié
- Produit par le backend dans le contrat JSON, affiché par le frontend en lecture seule

**Nouvelle section** — Contrat dual reason_code / cause_code
- `reason_code` : stable, technique, hérité d'Epic 3 — non exposé en UI
- `cause_code` / `cause_label` : contrat UI canonique, dérivé du `reason_code`, pour l'interface

**Section 8.4** — Renforcer : le frontend n'interprète jamais. Il reçoit les 4 dimensions déjà calculées.

### 6.4 Epics (`epics-post-mvp-v1-1-pilotable.md`)

- Insérer la description du nouvel Epic 4 (Recadrage UX) avec stories 4.1-4.4
- Renuméroter l'actuel Epic 4 → Epic 5 (stories 5.1-5.4)
- Aligner le vocabulaire des stories Epic 5 avec le nouveau modèle
- Mettre à jour la matrice des dépendances story-level
- Mettre à jour la section 7 (ordre d'exécution) et la section 9 (plan de correction)

### 6.5 sprint-status.yaml

- Ajouter les entrées `epic-4` (recadrage) avec stories 4.1-4.4 au statut `backlog`
- Renuméroter les entrées `epic-4` existantes → `epic-5` (stories 5.1-5.4)

---

## 7. Ordre recommandé de mise à jour des artefacts

| Étape | Artefact | Action | Justification |
|---|---|---|---|
| 1 | PRD V1.1 | Figer le nouveau modèle au niveau produit | Toute la cascade en dépend |
| 2 | UX delta review | Addendum : nouveau vocabulaire, placement confiance, scope diagnostic | Le cadrage UX doit précéder l'architecture |
| 3 | Architecture delta review | Addendum : définition Écart, contrat dual reason_code/cause_code | Le contrat technique suit les décisions UX |
| 4 | Epics | Insertion Epic 4, renumérotation Epic 5, alignement stories | Le backlog reflète les artefacts amont |
| 5 | sprint-status.yaml | Mise à jour de la structure | Dernière mise à jour, reflet fidèle du plan |

---

## 8. Guardrails à respecter

1. **Le resolver canonique (Epic 1) n'est pas modifié** — `inherit/include/exclude` reste la représentation interne
2. **Le contrat de santé (Epic 2) n'est pas modifié** — démon, broker, synchro, opération
3. **Les `reason_code` stables (Epic 3) ne sont pas renommés** — une couche `cause_code`/`cause_label` est ajoutée par-dessus pour le contrat UI
4. **Aucune extension de scope fonctionnel** — pas de nouveau type HA, pas de preview, pas de remédiation avancée
5. **L'export support complet reste disponible** — seul le diagnostic utilisateur est filtré in-scope
6. **Le frontend reste en lecture seule du contrat backend** — aucune logique métier dans le JS
7. **La V1.1 reste dans la frontière "pilotage du bridge"** — le recadrage améliore la lisibilité, pas le scope
8. **Pas de refonte backend profonde** — le pipeline central est conservé, seule la couche de présentation du contrat évolue
9. **Les invariants HA sont préservés** — `unique_id` stable, `Republier` non destructif, `Supprimer/Recréer` seul flux destructif

---

## 9. Classification et handoff

### Classification : Modéré

Le recadrage nécessite :
- Réorganisation du backlog (nouvel epic, renumérotation)
- Mise à jour documentaire (PRD, UX, architecture, epics)
- Pas de refonte technique profonde (le backend est sain)

### Handoff

| Responsabilité | Rôle / workflow |
|---|---|
| Validation du Sprint Change Proposal | Alexandre (PO) — **validé 2026-03-26** |
| Mise à jour PRD | PM (workflow `edit-prd`) |
| Mise à jour UX delta | UX Designer (addendum) |
| Mise à jour Architecture delta | Architect (addendum) |
| Mise à jour Epics + sprint-status | SM (création stories + sprint planning) |
| Implémentation Epic 4 (recadrage) | Dev (workflow `dev-story`) |
| Implémentation Epic 5 (opérations) | Dev (après Epic 4 terminé) |

### Critères de succès

1. Le concept "exception" a disparu de toute l'interface utilisateur
2. Chaque équipement est lisible selon le modèle Périmètre/Statut/Écart/Cause
3. La confiance n'apparaît que dans la page diagnostic technique
4. Le diagnostic principal ne montre que les équipements in-scope
5. Aucun terme technique interne n'est visible en frontend
6. Les compteurs pièce/global sont Total/Inclus/Exclus/Écarts
7. Le statut binaire Publié/Non publié n'existe qu'au niveau équipement
8. Le contrat backend → UI suit la forme JSON cible verrouillée
9. La distinction reason_code (backend stable) / cause_code (contrat UI) est respectée
10. L'export support complet reste fonctionnel et exhaustif

### Prochaine étape

Mise à jour du PRD V1.1 (`prd-post-mvp-v1-1-pilotable.md`) selon les propositions de la section 6.1.
