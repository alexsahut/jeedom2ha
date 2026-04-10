---
document_type: backlog_icebox
project: jeedom2ha
status: future_backlog
lastEdited: 2026-03-24
---

# Backlog Futur & Icebox

Ce document trace les sujets qualifiés par le PM qui sont explicitement HORS SCOPE du cycle actif. Ils ne doivent donner lieu à aucune story ni développement tant qu'ils n'ont pas été réévalués lors d'un futur planning d'epic.

## 1. Transparence et observabilité du mapping (Niveau Commande)

* **Intitulé :** Drill-down commande par commande
* **Résumé produit :** Permettre à l'utilisateur de déplier un équipement publié pour consulter, en lecture seule, les commandes sous-jacentes retenues et rejetées par le modèle de mapping, afin de fiabiliser le diagnostic local. Révèle la composition fine de l'équipement HA.
* **Horizon recommandé :** Post-V1.1 (Maturité produit avancée - Frontière C du PRD)
* **Conteneur recommandé :** Futur epic dédié
* **Owner logique :** Product Manager (pour cadrage futur) -> Architect
* **Garde-fous de non-empiètement :** 
  - Ne doit pas polluer l'Epic 2 (Santé du pont) avec des détails de niveau commande.
  - Ne doit pas modifier les statuts principaux de l'Epic 3, qui restent au niveau équipement.
  - Aucune opération HA partielle/unitaire de niveau commande n'est autorisée par l'Epic 4. La granularité managériale reste l'équipement.
* **Condition de réactivation future :** Nécessitera une phase d'architecture propre car cela introduit un niveau 4 structurant (`global -> pièce -> équipement -> commande`) dans la hiérarchie de la donnée et du frontend.

## 2. Alignement ciblé de la navigation sur les patterns Homebridge

* **Intitulé :** Navigation type Homebridge
* **Résumé produit :** Étudier la pertinence d'intégrer ponctuellement des patterns UX d'outils existants (comme Homebridge) pour réduire la friction d'adoption des migrants, uniquement si ces patterns n'entrent pas en conflit avec nos invariants propres à Home Assistant (ex: hiérarchie par pièce).
* **Horizon recommandé :** Icebox / Alignements optionnels tardifs (Frontière D du PRD)
* **Conteneur recommandé :** Backlog futur documenté (Icebox)
* **Owner logique :** UX Designer / Product Manager
* **Garde-fous de non-empiètement :**
  - Ne doit pas interférer avec la dette UX traitée dans l'Epic 1 (corrections de lisibilité). L'Epic 1 optimise notre UX, il ne la pivote pas.
  - Le vocabulaire et la philosophie des opérations restent centrés sur Home Assistant (Epic 3 et 4), pas de renaming des actions par mimétisme avec d'autres écosystèmes.
  - Pas de convergence implicite immédiate pour résoudre des bugs UI.
* **Condition de réactivation future :** Phase très ultérieure conditionnée par une validation stricte d'absence de conflit (conceptuel ou technique) avec le modèle core Jeedom2HA.
