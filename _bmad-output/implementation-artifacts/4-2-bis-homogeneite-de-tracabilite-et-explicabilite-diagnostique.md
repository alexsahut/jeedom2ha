# Story 4.2bis: Homogénéité de Traçabilité et Explicabilité Diagnostique

Status: ready-for-dev

## Story

As an **utilisateur Jeedom**,
I want **une traçabilité homogène et complète de la chaîne de décision pour chaque équipement**,
so that **je comprenne exactement pourquoi un équipement est publié (ou non) et quelles commandes ont été utilisées.**

## Contexte

Story 4.2 a livré l'accordéon de diagnostic avec cause et remédiation. Cependant, l'expérience utilisateur reste perfectible car la traçabilité interne du plugin n'est pas exposée de manière exhaustive. Cette story "bis" verrouille le contrat technique pour garantir un diagnostic déterministe et une UI premium.

**Ce que Story 4.2bis ajoute** :
- **Backend** : Un objet `traceability` complet exposant les étapes de décision (observation -> typage -> décision -> publication).
- **Frontend** : Standardisation de l'accordéon en 5 sections fixes pour tous les équipements.
- **Gouvernance** : Alignement de la taxonomie des `reason_code`.

## Acceptance Criteria

### AC1 — Contrat Backend Structuré (Traceability)
**Given** un diagnostic est demandé
**Then** chaque équipement contient un objet `traceability` non nul respectant cette structure :
```json
"traceability": {
  "observed_commands": [{"id": 123, "name": "On", "generic_type": "LIGHT_ON"}],
  "typing_trace": [{"logical_role": "brightness", "command_id": 456, "configured_type": "LIGHT_SLIDER", "used_type": "LIGHT_SLIDER"}],
  "decision_trace": {"ha_entity_type": "light", "confidence": "sure", "reason_code": "published"},
  "publication_trace": {
    "last_discovery_publish_result": "success | failed | not_attempted",
    "last_publish_timestamp": "2026-03-18T09:00:00Z"
  }
}
```
- `observed_commands` : Tableau obligatoire d'objets `{id, name, generic_type}` de toutes les commandes vues par le démon.
- `typing_trace` : Tableau `{logical_role, command_id, configured_type, used_type}` montrant l'origine du type utilisé pour chaque rôle. `used_type` est le type final (configuré ou déduit).
- `decision_trace` : Objet `{ha_entity_type, confidence, reason_code}` détaillant le choix final du moteur. `confidence` utilise la taxonomie architecture : `sure`, `probable`, `ambiguous`, `ignore`.
- `publication_trace` : Objet `{last_discovery_publish_result, last_publish_timestamp}`.
- `last_discovery_publish_result` normé : `success`, `failed`, `not_attempted` (résultat de la tentative locale du plugin, pas d'une confirmation HA).

> [!IMPORTANT]
> **Politique de présence** : Champs obligatoires. Les tableaux peuvent être vides `[]`, les objets ne sont pas omis (utilisent des valeurs neutres ou `null` si non applicable).

### AC2 — Taxonomie Normative des Reason Codes
**Then** le système utilise exclusivement la liste fermée suivante pour `reason_code` :
- `published` : Équipement totalement exposé.
- `excluded` : Exclu explicitement par l'utilisateur.
- `disabled_eqlogic` : Équipement désactivé dans Jeedom.
- `no_commands` : Aucune commande trouvée.
- `ambiguous_skipped` : Plusieurs types possibles sans arbitrage.
- `no_generic_type_configured` : Commandes présentes mais sans type générique.
- `no_supported_generic_type` : Types génériques configurés mais hors périmètre V1.
- `discovery_publish_failed` : Échec technique de publication MQTT.

### AC3 — UI Homogène en 5 Sections
**Given** la modale de diagnostic est ouverte
**Then** l'accordéon est disponible pour **TOUS** les équipements (y compris "Publié") et respecte cette structure fixe :
1. **Commandes observées** : Liste des commandes brutes vues par le démon.
2. **Typage Jeedom** : Détail configured vs used.
3. **Logique de décision** : Pourquoi ce mapping a été choisi (ou pourquoi il a échoué).
4. **Résultat de publication** : Statut du dernier envoi MQTT.
5. **Action recommandée** :
        - Si publié/OK : "Aucune action requise. L'équipement est correctement exposé." (Wording neutre).
        - Si actionnable : Bouton/Lien contextualisé.

### AC4 — Liens Jeedom Contextuels
**Given** une cause liée au typage (`no_generic_type_configured`, `ambiguous_skipped`)
**Then** le lien "Configurer dans Jeedom" pointe directement vers l'onglet des commandes : `index.php?v=d&m={plugin}&id={id}#commandtab`.
**Otherwise** il pointe vers la page générale de l'équipement.

### AC5 — Correction v1_compatibility (Binary Sensor)
**Then** le flag `v1_compatibility` (booléen) est `True` si l'équipement appartient à : `light`, `cover`, `switch`, `sensor`, `binary_sensor`.

## Guardrails (Non-régression)

- **UI 4.1** : Ne pas modifier les badges de statut (couleurs/labels) de Story 4.1.
- **Remédiation 4.2** : Conserver l'efficacité des messages de remédiation textuels de Story 4.2.
- **Doctrine Epic 4** : Rester sur du diagnostic métier. Ne pas afficher de logs bruts ou de JSON technique dans l'UI finale.
- **Performance** : La traçabilité est calculée à la volée ou stockée en RAM, aucune persistance DB n'est requise.

## Verification Plan (Proofs)

### Automated Tests (Backend)
- [ ] Test unitaire vérifiant que l'endpoint `/system/diagnostics` respecte le schéma JSON enrichi (objet `traceability` complet).
- [ ] Test de non-régression sur le calcul de `v1_compatibility` incluant les `binary_sensor`.

### Manual Verification (Frontend)
- [ ] Smoke test documenté validant l'affichage des 5 sections pour les 4 cas types :
    - [ ] **Publié** : "Aucune action requise".
    - [ ] **Partial** : Liste des commandes manquantes sous "Logique de décision".
    - [ ] **Non publié** : Remédiation actionnable.
    - [ ] **Exclu** : Explication de l'exclusion.

## Tasks

### Task 1 — Backend
- [ ] Mettre à jour les modèles Python pour porter l'objet `traceability`.
- [ ] Enrichir le handler `/system/diagnostics` pour remplir les traces pour tous les cas.
- [ ] Normaliser les `reason_code` selon la taxonomie AC2.
- [ ] Intégrer `binary_sensor` dans le calcul de compatibilité.

### Task 2 — Frontend
- [ ] Refondre `renderTable` pour utiliser le template de sections fixes.
- [ ] Gérer l'affichage des états neutres ("Aucun", "N/A").
- [ ] Implémenter le lien contextuel `#commandtab`.

### Task 3 — Proofs
- [ ] **Backend** : Test unitaire validant le schéma JSON du payload enrichi.
- [ ] **Frontend** : Smoke test documenté sur 4 cas clés (Publié, Partiel, Non publié, Exclu).

## Dev Notes

- **CSS** : Utiliser `background: ... !important` sur les lignes de détail pour éviter les conflits au hover Jeedom.
- **Wording** : Préférer "Typage détecté" à "Heuristique de mapping".
