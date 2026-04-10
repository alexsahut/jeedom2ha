# Sprint Change Proposal — Exclusion Multicritères & Politique de Confiance

**Date :** 2026-03-14
**Sprint :** Epic 4 — Maîtrise du Périmètre & Diagnostic
**Auteur :** Alexandre
**Scope :** Minor — enrichissement d'artefacts existants, pas de nouvel epic ni de réordonnancement

---

## Section 1 : Résumé du changement

### Insight déclenché

Lors du développement d'Epic 2 (mapping), constat que beaucoup de plugins Jeedom (zwavejs, deconz, xiaomihome) sont déjà intégrés nativement dans HA. Publier leurs équipements via jeedom2ha crée des doublons inutiles. Le plan actuel ne prévoit qu'une exclusion individuelle (Story 4.3 originale) — l'utilisateur devrait exclure des dizaines d'équipements un par un.

### Besoin identifié

Ajouter des filtres de publication plus larges :
1. **Par plugin / eqType_name** — exclure tout zwavejs, deconz, etc.
2. **Par pièce / objet Jeedom** — exclure les zones "Tests", "Technique"
3. **Par équipement individuel** — déjà partiellement prévu (FR18 original)
4. **Par politique de confiance configurable** — publier seulement les "sûrs" ou "sûrs + probables"
5. **Détection de doublons** — confirmé hors MVP / post-V1

---

## Section 2 : Analyse d'impact

### Impact Epics

| Epic | Impact | Description |
|------|--------|-------------|
| Epic 2 | Aucun | Le sprint en cours n'est pas modifié |
| Epic 4 | Enrichi | Story 4.3 enrichie — pas de nouvel epic |
| Autres | Aucun | Epic 1, 3, 5 non impactés |

### Conflits artefacts résolus

| Artefact | Changement |
|----------|-----------|
| PRD — FR18 | Reformulé : exclusion multicritères (individuel + plugin + pièce) |
| PRD — FR37 | **Nouveau FR** : politique de confiance configurable |
| Epics — Requirements Inventory | FR18 mis à jour, FR37 ajouté |
| Epics — FR Coverage Map | FR18 élargi, FR37 → Epic 4 |
| Epics — Epic 4 header | FR37 ajouté dans FRs covered |
| Epics — Story 4.3 | Entièrement refaite en 4 parties structurées |

---

## Section 3 : Artefacts modifiés

### FR18 (PRD + Epics) — Reformulation

**AVANT :** L'utilisateur peut exclure un équipement spécifique de la publication.

**APRÈS :** L'utilisateur peut exclure des équipements de la publication selon plusieurs critères : par équipement individuel, par plugin source (eqType_name) et par pièce / objet Jeedom. Les exclusions sont cumulatives : tout équipement correspondant à au moins un critère d'exclusion n'est pas publié. La configuration est persistée et réappliquée à chaque synchronisation / rescan.

### FR37 (nouveau)

L'utilisateur peut configurer la politique de confiance de publication : publier uniquement les équipements mappés avec une confiance « sûre », ou publier les équipements « sûrs » et « probables ». Le réglage par défaut est « sûr + probable ». Ce paramètre est global et s'applique à tous les domaines de mapping.

### Story 4.3 — Restructuration en 4 parties

- **Partie A** : Moteur de filtrage daemon (multicritères, cumulatif, avant le mapping, diagnostic)
- **Partie B** : Politique de confiance configurable (sûr only / sûr+probable)
- **Partie C** : Configuration UI (champs dans page config plugin, libellés métier)
- **Partie D** : Rescan et application (unpublish des exclus, confirmation UI)

---

## Section 4 : Référence wording UI (pour create-story)

### Critère 1 — Plugins exclus
- **Label :** Plugins exclus
- **Description :** Les équipements issus de ces plugins ne seront pas publiés vers Home Assistant.
- **Type de champ :** Liste de tags / multi-select
- **Placeholder :** Ex : zwavejs, deconz, xiaomihome
- **Données source :** Valeurs distinctes de `eqType_name` dans la topologie Jeedom

### Critère 2 — Pièces / objets Jeedom exclus
- **Label :** Pièces / objets Jeedom exclus
- **Description :** Les équipements rattachés à ces pièces / objets Jeedom ne seront pas publiés vers Home Assistant.
- **Type de champ :** Liste de tags / multi-select
- **Placeholder :** Ex : Tests, Technique, Garage
- **Données source :** Objets Jeedom (arbre jeeObject)

### Critère 3 — Exclusion par équipement individuel
- **Mécanisme :** Bouton "Exclure" par ligne dans la vue diagnostic (Story 4.1–4.2)
- **Persistance :** Flag `is_excluded` sur l'eqLogic (déjà dans le modèle `topology.py`)

### Critère 4 — Politique de publication
- **Label :** Politique de publication
- **Description :** Détermine quels équipements sont publiés selon le niveau de confiance du mapping automatique.
- **Type de champ :** Select
- **Options UI :** "Publier uniquement les mappings sûrs" / "Publier les mappings sûrs et probables (recommandé)"
- **Défaut :** sûr + probable
- **Note UI :** Les mappings ambigus ne sont jamais publiés, quelle que soit la politique choisie.

---

## Section 5 : Ce qui reste hors scope

- **Détection automatique de doublons** : confirmé post-MVP / post-V1 (PRD Growth)
- **Epic 2 en cours** : aucune modification — le mapping actuel reste inchangé
- **Nouveaux epics** : aucun — tout rentre dans Epic 4

---

*Généré par le workflow Correct Course — 2026-03-14 (session récupérée)*
