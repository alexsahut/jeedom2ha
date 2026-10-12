# Story 23.2 : Captures et vidéo de promotion rejouables

Status: draft

> Brouillon. Dépend de 23.1 et de 22.2 `done`; relecture ClaudeBox obligatoire.

## Story

En tant que mainteneur, je veux générer les visuels depuis la démo synthétique, afin que docs, forum et bêta Market montrent le produit livré.

## Critères d'acceptation proposés

1. Un parcours Playwright sur 23.1 prend une capture pour chaque `CAPTURE-A-PRENDRE` de `docs/fr_FR/index.md`.
2. Il produit une vidéo ≤2 min: installation, scan, écran par pièce, puis zones et entités HA.
3. Médias, métadonnées et commande de régénération sont versionnés sans rendre accessibles secrets ou données maison.
4. Marqueurs remplacés seulement après validation que média, version et documentation concordent.
5. CC-48: seuls contenus synthétiques de 23.1 visibles.
6. La vidéo est en mp4 ou webm, 1280×720, interface française, et exploitable comme lien « vidéo » de la fiche Market (hébergement choisi par Alexandre); les captures sont rangées dans `docs/fr_FR/images/`.

## Tâches proposées

- [ ] **Prérequis :** 23.1 validée, 22.2 `done`, comptes de démo fournis hors dépôt; ClaudeBox accède à Jeedom et HA de démonstration depuis Chrome.
- [ ] Figer storyboard avec ClaudeBox et relever les marqueurs docs.
- [ ] Écrire les scénarios Playwright/captures déterministes et enregistrer la vidéo.
- [ ] Versionner, documenter la régénération, puis valider Chrome avec ClaudeBox.
