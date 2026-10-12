# Story A3 : Conformité `info.json` au Market Jeedom (E3, E5)

Status: ready-for-dev

Epic: (Chantier Market 2026-10)

Story Key (sprint-status): `a3-conformite-market`

## Story

En tant que mainteneur,  
je veux corriger `plugin_info/info.json` pour respecter les champs obligatoires du Market Jeedom et verrouiller cette conformité par un test CI,  
afin que la première publication soit acceptée et que les mises à jour futures restent conformes.

## Description

Référence officielle : `doc.jeedom.com/fr_FR/dev/structure_info_json`. Champs obligatoires : `id`, `name`, `description` (≥ 80 caractères par langue), `licence`, `author`, `require`, `category`, `changelog`, `documentation`, `changelog_beta`, `documentation_beta`.

### État actuel de `plugin_info/info.json` (vérifié, main @7dd0120)

```json
{
  "pluginVersion": "0.3.0",
  "description": { "fr_FR": "...60 car...", "en_US": "..." },
  "changelog": ".../blob/main/docs/fr_FR/changelog.md",
  "documentation": ".../blob/main/docs/fr_FR/index.md",
  "link": { "forum": "" },
  "language": ["fr_FR", "en_US"],
  "compatibility": ["smart", "luna", "atlas", "rpi", "docker", "diy"]
}
```

### Corrections exactes à appliquer

1. **`description.fr_FR`** : réécrire à ≥ 80 caractères, **sans nom d'équipement ni de pièce de la maison** (règle CC-48 — fuite de noms réels dans le dépôt public).
2. **`description.en_US`** : à retirer ou laisser cohérent avec `language` — voir point 6.
3. **`changelog_beta`**, **`documentation_beta`** : à ajouter, pointant vers `blob/beta/docs/fr_FR/...` (cohérent avec le paquet épuré de A2 qui inclut `docs/fr_FR/`).
4. **`changelog`**, **`documentation`** : passer de `blob/main/...` à `blob/stable/docs/fr_FR/...` (le lien `stable` doit rester valide après chaque promotion, contrairement à `main` qui évolue en continu).
5. **`link.forum`** : remplir si une URL de forum existe, sinon documenter explicitement l'absence et laisser vide en connaissance de cause (pas un oubli).
6. **`language`** : `["fr_FR"]` seul (doc française uniquement, décision story 20-5) — retirer `en_US` du tableau et de `description` par cohérence, ou garder `description.en_US` seulement si `language` contient `en_US` (à trancher en dev selon l'état réel de la doc anglaise, mais la décision 20-5 pointe vers `fr_FR` seul).
7. **`compatibility`** : retirer `luna` et `atlas` (jamais testées) — ne pas les tester dans le cadre de cette story, simplement ne pas les déclarer.
8. **`plugin_info/template_icon.png`** : supprimer purement et simplement. L'icône officielle `plugin_info/jeedom2ha_icon.png` (+ `.svg`) existe déjà et est utilisée — aucun remplacement à produire, juste une suppression de fichier parasite.
9. **`issue`** : ajouter le lien vers les issues GitHub du projet.
10. **`pluginVersion`** : passer à `1.2.0` (D6), cohérent avec le prochain tag Git `v1.2.0`.

### Parcours retenu

**Parcours rapide + test CI** (règle CC-10 — la méthode a déjà tranché, pas de choix laissé à l'implémentation ; pas de refonte lourde nécessaire, les corrections sont ponctuelles et le risque se couvre par un test de non-régression) :
1. Appliquer les 10 corrections ci-dessus directement dans `plugin_info/info.json`
2. Supprimer `template_icon.png`
3. Ajouter un test CI de conformité (pas de valeur codée en dur type `pluginVersion contient "1.2.0"` — voir AC7)
4. Créer un README utilisateur minimal

## Acceptance Criteria

1. **Given** `plugin_info/info.json`  
   **When** il est parsé  
   **Then** `description.fr_FR` fait ≥ 80 caractères et ne contient aucun nom d'équipement ni de pièce réelle (CC-48).

2. **Given** les champs `changelog_beta` et `documentation_beta`  
   **When** `info.json` est vérifié  
   **Then** ils existent et pointent vers `blob/beta/docs/fr_FR/...`.

3. **Given** les champs `changelog` et `documentation`  
   **When** `info.json` est vérifié  
   **Then** ils pointent vers `blob/stable/docs/fr_FR/...`, jamais vers `blob/main/...`.

4. **Given** le champ `language`  
   **When** `info.json` est vérifié  
   **Then** il reflète exactement la documentation réellement disponible (décision 20-5 : `fr_FR` seul, sauf si une doc anglaise réelle existe — à confirmer en dev).

5. **Given** le champ `compatibility`  
   **When** `info.json` est vérifié  
   **Then** `luna` et `atlas` n'y figurent pas (non testées, non déclarées).

6. **Given** `plugin_info/template_icon.png`  
   **When** le dépôt est audité après la story  
   **Then** ce fichier n'existe plus, et `jeedom2ha_icon.png`/`jeedom2ha_icon.svg` restent inchangés et référencés.

7. **Given** le test CI de conformité  
   **When** il s'exécute sur une PR modifiant `info.json`  
   **Then** il valide les règles structurelles Jeedom (présence des champs obligatoires, longueur de description) **et** la cohérence `pluginVersion` / dernier tag Git `v*` / présence d'une entrée correspondante dans le changelog — sans valeur de version codée en dur dans le test.

8. **Given** `pluginVersion`  
   **When** `info.json` est vérifié  
   **Then** sa valeur est `1.2.0` et correspond au tag Git `v1.2.0` au moment de la release (D6).

9. **Given** un README utilisateur  
   **When** un nouvel utilisateur consulte le dépôt  
   **Then** il trouve une vue d'ensemble claire, les prérequis, et un lien vers la documentation détaillée (`docs/fr_FR/index.md`).

## Tasks / Subtasks

- [ ] T1 — Corriger `plugin_info/info.json`
  - [ ] Réécrire `description.fr_FR` ≥ 80 caractères, sans nom d'équipement/pièce réelle (CC-48)
  - [ ] Trancher `description.en_US`/`language` selon l'état réel de la doc anglaise (décision 20-5 : français seul par défaut)
  - [ ] Ajouter `changelog_beta`, `documentation_beta` (`blob/beta/docs/fr_FR/...`)
  - [ ] Corriger `changelog`, `documentation` (`blob/stable/docs/fr_FR/...`)
  - [ ] Retirer `luna`, `atlas` de `compatibility`
  - [ ] Ajouter `issue` (lien GitHub issues)
  - [ ] Passer `pluginVersion` à `1.2.0`
  - [ ] Documenter `link.forum` (vide assumé ou rempli)

- [ ] T2 — Supprimer l'icône parasite
  - [ ] Supprimer `plugin_info/template_icon.png`
  - [ ] Vérifier qu'aucune référence au fichier supprimé ne subsiste dans le code/doc

- [ ] T3 — Test CI de conformité
  - [ ] Créer un test qui valide la structure `info.json` contre les champs obligatoires Jeedom (`doc.jeedom.com/fr_FR/dev/structure_info_json`)
  - [ ] Valider la cohérence dynamique `pluginVersion` / dernier tag `v*` / entrée changelog correspondante (pas de valeur en dur)
  - [ ] Valider `description` ≥ 80 caractères par langue déclarée dans `language`

- [ ] T4 — README utilisateur
  - [ ] Créer/compléter un README minimal : vue d'ensemble, prérequis, lien vers `docs/fr_FR/index.md`

## Impact Produit

- **Si non fait** : rejet probable de la première soumission Market (description trop courte, changelogs beta manquants), ou alerte de mise à jour trompeuse pour les utilisateurs (`compatibility` non vérifiée, version incohérente).
- **Si fait** : `info.json` conforme, test CI empêchant toute régression future (E3/E5), publication fiable.

## Rollback / Plan de Retour Arrière

- Revert du commit modifiant `plugin_info/info.json` et supprimant `template_icon.png`.
- Revert du job CI de conformité si besoin (conformité redevient manuelle).

## Notes

- Aucun parcours alternatif : **parcours rapide + test CI uniquement** (CC-10 — déjà tranché).
- Dépendance : A2 (construction du paquet) a besoin de cette story terminée pour fixer les liens `blob/beta|stable/docs/fr_FR/...` dans le manifeste et dans `info.json` de façon cohérente.
- Ordre proposé : **A1 et A3 en parallèle, puis A2**.
- Référence officielle à utiliser en dev : `doc.jeedom.com/fr_FR/dev/structure_info_json` (pas la page `/plugins/market/` citée par erreur dans la version précédente de cette fiche).

## Dev Agent Record (session cloud 11/10)

- `pluginVersion` 1.2.0 (dernier tag `v1.1.0`) ; le test exige `pluginVersion >= dernier tag v*` (`=` si HEAD est taggé) et une entrée de changelog dont l'en-tête cite la version ; en-tête `v1.2.0` ajouté à l'entrée du 2026-10-11 de `docs/fr_FR/changelog.md`.
- Liens `blob/stable/...` : 404 attendu tant que `stable` n'a pas reçu sa première release Market.
- `link.forum` laissé vide en connaissance de cause (aucun forum dédié).
- README utilisateur (AC9) : réécrit par la session cloud le 2026-10-12 (commit `95bec8d`, consigne envoyée après revue ClaudeBox ayant constaté l'absence du livrable) — remplace l'ancien README orienté développeur par une version vue d'ensemble/prérequis (Jeedom 4.4+, Debian 11-12, broker MQTT, HA + intégration MQTT)/lien `docs/fr_FR/index.md`, sans nom d'équipement/pièce réel. Relu et approuvé par ClaudeBox le 2026-10-12 07:45, avec la précision qu'au passage en stable `os.min` sera fixé à `12` seul (décision Alex 07:19), pas avant.
- Test : `tests/unit/test_info_json_market_conformity.py` (sous-test de tags ignoré si le clone n'a pas de tags).
