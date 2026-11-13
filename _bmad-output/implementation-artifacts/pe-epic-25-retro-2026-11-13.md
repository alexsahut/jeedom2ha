# Rétrospective pe-epic-25 — Refonte de la surface de configuration (A+B+C)

Date : 2026-11-13
Projet : jeedom2ha
Cycle actif : Moteur de projection explicable
Rédaction : session cloud déléguée (remise au propre BMAD du 2026-11-13, décision d'Alexandre de 22:46), à partir des fichiers de story et des preuves terrain 25-1 à 25-9. Documentaire seul, aucun nom réel (CC-48).

## Synthèse

L'epic 25 est né du refus de validation UX de 22-2 (2026-10-18 17:58) et d'un diagnostic UX/UI indépendant. Décision d'Alexandre le même soir : les trois directions A (socle), B (page principale) et C (vue maître-détail). Neuf stories en quatre jours : cadrage le 18/10, revue UX intermédiaire et extension 25-6 à 25-9 le 19/10, validation UX d'Alexandre le 20/10 à 22:46 (box sur `68560b7`), clôture le 21/10 à 08:36. 9/9 stories `done`.

## Valeur livrée

- **25-1 — Socle A** : fonction d'état unique, glossaire imposé, palette `--j2ha-*` sur les deux thèmes ; clôt 22-2 (superseded) à sa preuve terrain du 18/10 (`c940ac3`).
- **25-2 — Route agrégée côté démon** : états par pièce et par équipement en un appel (#288, `2b451dd`) ; 292 équipements rendus, froid 314 ms, chaud 136 à 322 ms.
- **25-3 — Page principale B** (`030d6e8`) et **25-4 — Vue maître-détail C**, retrait de l'ancienne modale (`90d4177`).
- **25-6 à 25-9** (revue UX du 19/10, décisions D1 à D4) : vue C filtrée sur la pièce, cause d'exclusion affichée (`12e8484`), exclusion de pièce depuis la surface et page de configuration réduite aux plugins (`b3e6a13`).
- **25-5 — Recette finale** : validation UX d'Alexandre sur la liste RECETTE-25-5 (PR #324) ; clôture par la PR #330 (Jeedom 4.5 minimum). Pas de fichier de story : la traçabilité est dans `sprint-status.yaml`.

## Ce qui a coincé

- **Le gate 20-0 sur la box a trouvé un vrai défaut produit à presque chaque story**, invisible en local : contraste quasi nul du segment « Jamais » en sombre et « Exclu » au lieu de « Désactivé » (#282), collision CSS (#296), rechargement de page par l'écouteur `popstate` du cœur (#302, plus un cas dérivé trouvé par la relecture Codex), accolades de traduction coupées par une fin de ligne (#308), bouton destructif affiché vert par une règle du cœur (#314).
- **Des parcours du gate se sont trompés eux-mêmes** : requêtes du cœur comptées comme celles du plugin (#294), fermeture par Échap dépendante du focus (#297), course entre arbre et lecture des états (#303), première carte déjà exclue (#312), équipement témoin modifié par un réglage utilisateur (résolu plus tard par 24-11, cible choisie à l'exécution).
- **CI de `main` rouge après fusion (#309)** : une garde de non-régression supposait un diff non vide ; le déploiement a été refusé à juste titre (CC-50), corrigé par #311.
- **Le gate « couleurs correctes sur Jeedom 4.4 »** n'avait aucune instance pour être prouvé : changement de périmètre décidé par Alexandre le 21/10 (Jeedom 4.5 minimum, `getCmdPython3` absent avant 4.4.7).
- **Fusionné n'est pas déployé** : le premier déploiement de 25-1 a aussi mis en production 22-3, fusionnée le 12/10 et jamais déployée (169 entités modifiées).

## Leçons

1. **La preuve sur une vraie box Jeedom reste indispensable pour l'interface** : le cœur (infobulles, `popstate`, CSS déprécié, traducteur) change le comportement du plugin d'une façon qu'aucun test local ne reproduit.
2. **Un parcours de gate ancré sur l'état du terrain casse quand le terrain bouge** : choisir la cible à l'exécution (24-11) plutôt que figer un équipement.
3. **Une revue UX intermédiaire tôt** (19/10) a coûté une journée et évité un second refus : quatre stories ajoutées avant la recette finale, validées du premier coup.
4. **Un gate sans environnement pour le prouver doit être tranché tout de suite** (prouver ou changer le périmètre), pas laissé ouvert.
5. **Vérifier ce qui est réellement déployé** avant d'attribuer un écart terrain à la story du jour.

## Réserves et points de suivi

- **25-2** : comportement après écriture et après synchro prouvé par les tests seulement, pas mesuré sur la box.
- **25-6 / 25-7** : taille de la réponse agrégée non relevée (journal du démon tronqué par la maintenance Jeedom).

## Actions

| # | Action | Porteur |
|---|---|---|
| 1 | Garder le gate 20-0 sur la box obligatoire avant tout `done` touchant l'écran (déjà la règle ; confirmée par cet epic). | toutes les stories UI |
| 2 | Relever la taille de la réponse agrégée et le temps après écriture lors de la prochaine preuve terrain touchant la surface. | ClaudeBox |
| 3 | Créer un fichier de story pour toute story de recette, même courte, afin d'éviter une traçabilité seulement dans `sprint-status.yaml` (cas de 25-5). | SM / ClaudeBox |

## Conclusion

L'epic 25 est clos : la surface A+B+C est en production, validée par Alexandre, servie par la route agrégée, sur les deux thèmes, avec Jeedom 4.5 comme version minimale. Les défauts trouvés en route l'ont été par le gate sur la box, ce qui confirme son rôle.
