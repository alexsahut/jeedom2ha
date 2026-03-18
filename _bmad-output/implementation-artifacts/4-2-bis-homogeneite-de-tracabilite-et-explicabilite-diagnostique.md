# Story 4.2bis: Homogénéité de Traçabilité et Explicabilité Diagnostique

Status: ready-for-dev

## Story

As a utilisateur Jeedom,
I want une expérience de diagnostic homogène et une traçabilité claire du moteur de mapping,
so that je comprenne exactement pourquoi un équipement est "Partiellement publié" ou "Non publié" sans ambiguïté technique.

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
  "observed_commands": ["list of strings"],
  "typing_trace": ["Detected types in Jeedom"],
  "decision_trace": "Explanation of the mapping choice",
  "publication_trace": {
    "last_discovery_publish_result": "success | failed | not_attempted"
  }
}
```
> [!IMPORTANT]
> Politique de présence : Tous les champs sont obligatoires. Les tableaux vides sont autorisés, mais les objets ne doivent pas être omis.

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
2. **Typage Jeedom** : Types génériques détectés.
3. **Logique de décision** : Pourquoi ce mapping a été choisi (ou pourquoi il a échoué).
4. **Résultat de publication** : Statut du dernier envoi MQTT.
5. **Action recommandée** : Texte de remédiation (ou "Aucune action requise. L'équipement est correctement exposé.").

### AC4 — Liens Jeedom Contextuels
**Given** une cause liée au typage (`no_generic_type_configured`, `ambiguous_skipped`)
**Then** le lien "Configurer dans Jeedom" pointe directement vers l'onglet des commandes : `index.php?v=d&m={plugin}&id={id}#commandtab`.
**Otherwise** il pointe vers la page générale de l'équipement.

### AC5 — Correction v1_compatibility (Binary Sensor)
**Then** le flag `v1_compatibility` (booléen) est `True` si l'équipement appartient à : `light`, `cover`, `switch`, `sensor`, `binary_sensor`.

## Guardrails (Non-régression)

- **UI 4.1/4.2** : Ne pas modifier le calcul des badges de couleur ou des statuts globaux livrés précédemment.
- **Pureté métier** : L'interface utilisateur finale ne doit jamais afficher de JSON brut ou de stacktrace Python. Tout doit être traduit en langage métier.
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
- [ ] Enrichir `_handle_system_diagnostics` avec l'objet `traceability`.
- [ ] Normaliser les `reason_code` selon la taxonomie AC2.
- [ ] Intégrer `binary_sensor` dans le calcul de compatibilité.

### Task 2 — Frontend
- [ ] Refondre `renderTable` pour la structure à 5 sections.
- [ ] Implémenter le lien contextuel `#commandtab`.

### Task 3 — Proofs
- [ ] Produire un rapport de test unitaire.
- [ ] Produire une capture d'écran de l'accordéon "Publié" (nouveauté).
