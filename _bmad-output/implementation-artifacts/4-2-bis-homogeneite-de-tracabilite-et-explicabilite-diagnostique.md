# Story 4.2bis: Homogénéité de Traçabilité et Explicabilité Diagnostique

Status: ready-for-dev

## Story

As a utilisateur Jeedom,
I want une expérience de diagnostic homogène et une traçabilité claire du moteur de mapping,
so that je comprenne exactement pourquoi un équipement est "Partiellement publié" ou "Non publié" sans ambiguïté technique.

## Contexte

Story 4.2 a livré l'accordéon de diagnostic avec cause et remédiation. Cependant, l'expérience utilisateur reste perfectible car :
1. Les données de traçabilité (quels types génériques ont été vus vs quels types sont supportés) ne sont pas toujours présentées de manière homogène.
2. Certains cas de "Non publié" (ex: `ambiguous_skipped` vs `no_supported_generic_type`) nécessitent une distinction plus fine des types détectés.
3. L'accordéon doit être systématiquement présent pour tous les équipements non-OK pour garantir la confiance.

**Ce que Story 4.2bis ajoute** :
- **Backend** : Un objet `traceability` riche dans le payload de diagnostic, exposant les types génériques configurés et ceux réellement exploités par le mapper.
- **Frontend** : Standardisation de la section "Détails techniques" dans l'accordéon pour inclure cette traçabilité.
- **Taxonomie** : Stabilisation des `reason_code` (ex: `no_generic_type_configured` vs `generic_type_not_supported`).

## Acceptance Criteria

**AC1 — Objet de traçabilité Backend**
**Given** un diagnostic est demandé
**Then** le payload contient pour chaque équipement un objet `traceability` :
```json
"traceability": {
  "detected_generic_types": ["LIGHT_ON", "LIGHT_SLIDER"],
  "used_generic_types": ["LIGHT_ON"],
  "unsupported_generic_types": ["LIGHT_SLIDER"],
  "v1_compatibility": "partial"
}
```

**AC2 — Distinction fine des types génériques**
**Given** un équipement avec `reason_code` = `no_supported_generic_type` ou `ambiguous_skipped`
**Then** l'accordéon affiche explicitement la liste des types génériques trouvés dans Jeedom pour aider l'utilisateur à corriger sa configuration.

**AC3 — Homogénéité de l'UI Accordéon**
**Then** l'accordéon utilise une structure fixe :
1. Cause (Titre + Badge)
2. Action (Remédiation)
3. Traçabilité (Détails des types détectés)
4. Lien "Configurer dans Jeedom" (si actionnable)

**AC4 — Flag v1_compatibility**
**Then** chaque équipement porte un flag `v1_compatibility` (`full`, `partial`, `none`, `excluded`) calculé par le démon pour simplifier la logique frontend.

## Tasks

### Task 1 — Backend : Enrichissement de la traçabilité
- [ ] Modifier `_handle_system_diagnostics` dans `http_server.py` pour inclure l'objet `traceability`.
- [ ] Implémenter le calcul de `v1_compatibility`.
- [ ] Ajouter les nouveaux `reason_code` granulaires.

### Task 2 — Frontend : Standardisation de l'accordéon
- [ ] Modifier `renderTable` dans `jeedom2ha.js` pour utiliser la nouvelle structure homogène.
- [ ] Afficher les types génériques détectés/utilisés.

### Task 3 — Tests & Validation
- [ ] Mettre à jour `test_diagnostic_endpoint.py`.
- [ ] Vérifier la non-régression sur le filtrage et la recherche.

## Dev Notes
- Conserver la doctrine des couleurs Bootstrap 3 (jaune=action requise, gris=V1, rouge=infra).
- Ne pas introduire de nouvelles dépendances.
