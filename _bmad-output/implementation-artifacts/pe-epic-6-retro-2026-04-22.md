# Rétrospective partielle pe-epic-6 — Le diagnostic est explicable et actionnable pour chaque équipement

**Date :** 2026-04-22
**Cycle :** Moteur de Projection Explicable
**Epic :** `pe-epic-6`
**Statut epic :** `in-progress`
**Statut rétrospective :** clôturée en mode partiel
**Motif de partialité :** `6.2` reste `in-progress` après NO-GO terrain du 2026-04-21 et correct-course approuvé

---

## Participants

- Alexandre (Project Lead)
- Bob (Scrum Master)
- Alice (Product Owner)
- Winston (Architect)
- Charlie (Senior Dev)
- Dana (QA Engineer)

---

## Résumé factuel de l'epic

- 3 stories prévues dans `pe-epic-6`
- `6.1` : `done` avec gate terrain PASS le 2026-04-21
- `6.2` : `in-progress` avec gate terrain NO-GO le 2026-04-21, puis correct-course approuvé
- `6.3` : `done` le 2026-04-22 après code review PASS et gate terrain PASS
- Le moteur, les invariants I4 / I7 et la séparation décision / technique sont restés stables pendant les corrections
- Aucun `pe-epic-7` n'est défini dans les artefacts de planification actuels

---

## Suivi actions pe-epic-5

| Action | Statut | Lecture |
|---|---|---|
| Contrat canonique de traceabilité | ✅ | Tenu, le modèle n'a pas bougé malgré les corrections |
| Tests I7 non permissifs | ✅ | Protecteurs, aucune dérive décisionnel / technique |
| Artefact visuel prescriptif | ✅ | 6.1 a fourni une base UX solide |
| Discipline d'exécution | ✅ | Correct-course propre, sans contournement ni faux `done` |

**Observation :** le follow-through de la rétro `pe-epic-5` a bien tenu. Le NO-GO de `6.2` a révélé un problème de sequencing produit, pas une faiblesse systémique du moteur.

---

## Points de satisfaction

### 1. Fondations techniques saines

- pipeline `1 -> 5` resté stable
- invariants I4 / I7 tenus
- séparation décisionnelle / technique préservée
- corrections locales, sans régression structurelle

**Lecture commune :** l'architecture était saine dès le départ ; elle a permis de corriger sans tout casser.

### 2. Valeur utilisateur réellement visible après 6.3

- `6.1` a apporté la structure visible : stepper + cause canonique
- `6.3` a corrigé la sémantique utilisateur
- suppression des faux CTA = gain immédiat de confiance

**Lecture commune :** on est passé de "ça marche techniquement" à "c'est compréhensible pour un utilisateur réel".

### 3. Système qualité utile, terrain décisif

- forte couverture `pytest` + `node`
- invariants protégés pendant tout le correct-course
- aucune régression détectée en corrigeant la sémantique

**Limite clarifiée :** tests verts != produit compréhensible. Le terrain a joué le rôle de vérité produit.

### 4. Correct-course rapide et mature

- détection rapide du problème de `6.2`
- décision explicite de ne pas forcer la story
- création de `6.3` ciblée et propre
- correction sans élargir artificiellement le scope

**Lecture commune :** bon signal de maturité produit ; on a corrigé la direction, pas seulement le code.

---

## Challenges et tensions

### Challenge 1 — Sequencing `6.2` / `6.3`

Le point de friction principal a été un problème de sequencing produit et de promesse story-level.

- `6.2` a porté trop tôt une promesse de diagnostic actionnable
- le moteur savait déjà expliquer le problème, mais pas toujours recommander une action honnête
- certaines situations n'avaient pas de remédiation utilisateur réelle ni de surface produit correspondante

**Lecture systémique :** la difficulté n'était pas dans le moteur, mais dans l'écart entre explicabilité du diagnostic et actionnabilité réellement soutenable.

### Challenge 2 — Confusion entre "explicable" et "actionnable"

Le cycle a révélé que ces deux notions correspondent à deux niveaux de maturité différents.

- `explicable` : capacité déjà tenue par le moteur et par `6.1`
- `actionnable` : capacité produit plus exigeante, dépendante du périmètre HA réellement ouvert et des surfaces réellement supportées

**Lecture produit :** l'actionnabilité n'est pas une couche UX ; c'est une capacité produit.

### Point secondaire — Dette latente M3

Le point `M3` remonté en story `6.3` sur l'alignement `cause_code` / `decision_reason_code` reste une dette mineure utile à traiter, mais non explicative de la friction centrale de l'epic.

---

## Insight clé

**L'actionnabilité n'est pas une couche UX. C'est une capacité produit dépendante du périmètre réellement ouvert et supporté.**

Le moteur savait déjà :

- détecter les causes
- qualifier les états
- exposer le pipeline

Mais il ne pouvait pas toujours répondre honnêtement à : "qu'est-ce que je dois faire concrètement ?"

La bonne correction n'a donc pas été "plus d'UX", mais "moins de sur-promesse".

---

## Accord d'équipe non négociable

> **On n'expose une action que si elle est faisable et supportée par le produit. Sinon, on n'en expose pas.**

Cet accord devient la règle de référence pour toute surface diagnostic future.

---

## Readiness pe-epic-6

| Dimension | Statut | Note |
|---|---|---|
| Qualité structurelle | ✅ | pipeline stable, invariants tenus, non-régression validée |
| Déploiement / terrain | ✅ avec réserve connue | `6.1` et `6.3` validées ; `6.2` NO-GO assumé et compris |
| Santé technique | ✅ | pas de réserve critique sur stabilité ou implémentation |
| Acceptation Project Lead | ✅ avec incomplétude explicite | epic sain mais incomplet à cause de `6.2` |
| Bloqueurs critiques latents | ✅ Non | seul point ouvert majeur = capacité produit non encore construite |

**Conclusion de readiness :** `pe-epic-6` est sain sur ses fondations et ses comportements réels. Son incomplétude est volontaire, explicite et comprise ; elle correspond à une capacité produit non encore construite, pas à un défaut de qualité ou de stabilité.

---

## Action items pe-epic-6

### AI-1 — Formaliser la règle "pas d'action sans surface produit réelle"

- **Owner :** Bob + Alice
- **Action :** intégrer explicitement la règle dans les prochains briefs, gates et stories touchant `cause_action` ou une guidance utilisateur
- **Critère de succès :** toute future story de diagnostic inclut la règle, le gate `no faux CTA`, et la preuve de la surface produit réellement disponible

### AI-2 — Traiter l'actionnabilité comme une capacité produit

- **Owner :** Alice + Winston
- **Action :** exiger que toute promesse d'action utilisateur référence le périmètre HA réellement ouvert et la remédiation effectivement supportée
- **Critère de succès :** plus aucune story ne confond `explicable` et `actionnable`

### AI-3 — Conserver `6.2` comme incomplétude consciente, pas comme bug cosmétique

- **Owner :** Bob
- **Action :** maintenir `6.2` ouverte tant que son contrat n'est pas réaligné avec une capacité produit réelle, sans closeout par simple retouche de wording
- **Critère de succès :** le tracker et les futurs arbitrages traitent `6.2` comme une capacité incomplète, pas comme un simple défaut d'UX

### AI-4 — Lever la dette latente M3 sur la cohérence 4D

- **Owner :** Charlie + Winston
- **Action :** aligner `cause_code`, `cause_label` et `cause_action` sur une même source canonique dans `/system/diagnostics`
- **Critère de succès :** un test d'invariant garantit que les trois champs dérivent de la même cause canonique

---

## Impact sur la suite

- Aucun `pe-epic-7` n'étant défini, la rétro ne débouche pas sur une préparation détaillée d'epic suivant
- La principale sortie de cette rétro est une règle d'exécution produit : ne jamais promettre une action utilisateur avant d'avoir prouvé qu'elle existe réellement dans le produit
- Toute future extension de diagnostic devra distinguer explicitement :
  - compréhension du problème
  - capacité réelle à agir

---

## Mot de clôture

> "L'epic est sain sur ses fondations et ses comportements réels, et l'incomplétude est volontaire et comprise : elle correspond à une capacité produit qu'on n'a pas encore construite, pas à un problème de qualité ou de stabilité." — Alexandre

---

Bob (Scrum Master) : "Rétro partielle clôturée."
Alexandre (Project Lead) : "Validation confirmée : `pe-epic-6` est sain mais explicitement incomplet à cause de `6.2`, sans autre réserve critique à ce stade."
