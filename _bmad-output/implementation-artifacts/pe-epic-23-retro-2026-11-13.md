# Rétrospective pe-epic-23 — Prêt pour le Market et la promotion

Date : 2026-11-13
Projet : jeedom2ha
Cycle actif : Moteur de projection explicable
Rédaction : session cloud déléguée (remise au propre BMAD du 2026-11-13, décision d'Alexandre de 22:46), à partir des fichiers de story et de leurs preuves terrain. Documentaire seul, aucun nom réel (CC-48).

## Synthèse

L'epic 23 devait rendre le plugin démontrable, installable et honnêtement documenté avant la promotion et la bêta Market, sans aucune donnée de la maison. Cadré le 2026-10-12, il est clos le 2026-11-01 : ses cinq stories sont `done`, dont **23-4 avec une réserve** (AC5).

## Valeur livrée

- **23-1 — Démo rejouable** : VM de démonstration partie d'un snapshot vierge, jeu synthétique créé par un script idempotent (5 pièces, 16 équipements, 45 commandes, 3 scénarios ; `created: 69`, puis `exists: 69` au second passage), Mosquitto local et HA de test, snapshot `demo` (preuve 2026-10-13). Correctifs nés du terrain : #268, #269, #271 (idempotence des unités).
- **23-3 — État des lumières et des volets** : `light` et `cover` streamés, discoveries non optimistes, luminosité et position remontées (PR #265, preuve sur la démo le 2026-10-13).
- **23-5 — Licence** : AGPL-3.0-or-later, décision écrite d'Alexandre du 2026-10-12 19:21, alignement fusionné par #273.
- **23-4 — Installation depuis GitHub** : procédure `docs/fr_FR/installation-github.md` exécutée sur une copie jetable de la VM de démo le 2026-10-31 (3 écarts de doc corrigés), PR #337.
- **23-2 — Captures et vidéo rejouables** : outillage Playwright et storyboard (dev cloud du 2026-10-21), passage terrain r9 par clawcode le 2026-10-31, rendu validé par Alexandre le 2026-11-01 09:22, médias publiés par #353 et #357.

## Ce qui a coincé

- **Le terrain de 23-2 a demandé une douzaine de correctifs d'outillage** (#336, #339, #340, #342 à #350) : bouton de connexion du cœur 4.6.1, animations gelées qui bloquaient la connexion, bascule automatique du thème le soir, `networkidle` jamais atteint dans Jeedom, cadrage des captures, pilotage HA.
- **La preuve de 23-3 n'a pas pu utiliser l'outil de parité** : `parity-snapshot.sh` ne souscrit pas aux nouveaux topics d'état (`state`, `brightness`, `position`) ; un relevé MQTT séparé a tenu lieu de preuve (option Q6).
- **23-4 dépendait d'une branche `beta` maintenue** qui n'existait pas : la procédure nomme `main`, `beta` n'est pas présentée comme livrée.

## Leçons

1. **Une démo synthétique rejouable débloque toutes les preuves publiques** sans exposer la maison (CC-48) ; elle a ensuite servi aux epics 22, 24 et 25.
2. **Relire les médias produits fait apparaître des défauts produit** : « Connecté via <hôte du broker> » dans HA a donné la story 22-4 (pont nommé), close le même jour.
3. **Un outil de preuve doit suivre le périmètre de la story** : si l'outil ne voit pas les nouveaux topics, le dire dans la preuve et utiliser un relevé séparé, plutôt que conclure sur un diff vide.
4. **Automatiser Jeedom au navigateur demande des attentes bornées** (`settle` à 3 s) : le cœur n'est jamais au repos réseau.

## Réserves et points de suivi

- **23-4, AC5** : mise à niveau et retour arrière documentés, non testés (réserve acceptée à la clôture).
- **23-2** : sur la vidéo, la valeur « Hôte MQTT » de la démo reste visible (masquage CC-48 à corriger avant toute régénération hors démo) ; badge de message Jeedom dans la barre ; une capture de carte seule hors documentation.
- **23-1, notes de suivi** : équipement à deux capteurs qui ne produit qu'une entité ; scénarios sans pièce hors zone HA ; états initiaux inconnus des Virtuel sans valeur.

## Actions

| # | Action | Porteur |
|---|---|---|
| 1 | Tester mise à niveau et retour arrière de l'installation GitHub à la prochaine version publiée (solde de la réserve AC5 de 23-4). | ClaudeBox |
| 2 | Appliquer le masquage CC-48 du champ « Hôte MQTT » dans l'outillage de 23-2 avant toute régénération hors démo. | prochaine story touchant l'outillage de captures |
| 3 | Reprendre les trois notes de suivi de 23-1 dans le prochain epic de revue fonctionnelle/UX. | ClaudeBox (cadrage) |

## Conclusion

L'epic 23 est clos : démo, état des lumières et volets, licence, installation GitHub et médias de promotion sont livrés et prouvés sur l'environnement de démonstration, avec une réserve connue (AC5 de 23-4) et trois suites identifiées.
