# Rétrospective pe-epic-21 — Solde des réserves de l'étape 4 (CC-44, CC-47)

Date : 2026-10-12
Projet : jeedom2ha
Cycle actif : Moteur de projection explicable — étape 4 du plan d'action (ClaudeBox et clawcode, validé par Alex le 2026-09-26)
Rédaction : ClaudeBox (superviseur), consignée par une session cloud déléguée.

## Synthèse

L'epic 21 a soldé les deux réserves laissées par l'epic 20 : un scénario Jeedom désactivé ne laisse plus de bouton dans Home Assistant (CC-44), et l'écran dit vrai sur une commande d'état déjà publiée par une entité secondaire (CC-47). Il compte une seule story, 21-1, en deux blocs et deux PR.

La story est `done` avec **une réserve sur l'AC 13 a** (voir plus bas). Durée : du 2026-10-11 au 2026-10-12.

## Valeur livrée

- **CC-44 (bloc A, #237 `d293a65`)** : retrait des boutons de scénario désactivés, supprimés ou déjà fantômes (le broker fait foi). Sur la box : 7 fantômes retirés (2, 32, 33, 39, 40, 72, 129) plus le scénario 147 désactivé pendant la preuve ; 355 → 347 topics, 92 → 84 boutons de scénario.
- **CC-47 (bloc B, #238 `30e6c80`)** : la ligne de la commande 5369 de l'équipement 579 dit « Sera publié : binary_sensor », la synthèse compte 5 commandes prêtes, la pièce passe de 93/3 à 94/2 prêtes/bloquantes. Aucune publication ne change.
- **CC-57** (disponibilité et appareil des boutons de scénario homonymes, AC 6 bis) : prouvé le 12/10 ; 15 appareils de bouton passent aux valeurs neutres, 69 sont inchangés.
- **Outillage** : CC-56 (forme sûre de lancement d'une délégation et `--sha` obligatoire au déploiement) ; CC-59 (garde-fou CI par branche, #244 `f6acf0f`) ; gate 20-0 réancré sur l'équipement 380, sans nom réel (#245 `ab3a854`).

**Points fermés** : CC-44, CC-47, CC-57, CC-56, CC-59. **Renvoyés à la story 22-2** : CC-58, CC-60.

## Gates epic-level (`epics-projection-engine.md`)

- **Un scénario désactivé n'a plus de bouton dans HA après le sync suivant**, prouvé sur la box (inventaire avant/après, 0 erreur du démon). ✔
- **La ligne, la synthèse et les totaux de 5369 disent qu'elle est publiée** ; les 5 entités de 579 sont inchangées dans HA, et seuls 8 topics de boutons de scénario ont disparu de l'inventaire. ✔
- **`PRODUCT_SCOPE` inchangé** ; golden et contrat 4D verts. ✔

## Ce qui a marché

- **Les décisions d'Alexandre en une passe** : Q0 à Q4 tranchées d'un coup, toutes les recommandations retenues, sans aller-retour.
- **Deux blocs, deux PR, menés en parallèle** par deux sessions cloud, sans collision de fichiers.
- **La relecture indépendante du bloc A**, en plus de celle de ClaudeBox.
- **Le rediagnostic de CC-47 avant le développement** : le relevé de terrain a montré que 5369 était déjà publiée, donc un défaut d'affichage et non de publication. Le bloc B a été recentré avant la première ligne de code.
- **La preuve par les registres de HA** (`deleted_entities`, registre des appareils) : lecture seule, sans action sur la box, et assez précise pour distinguer les 15 appareils modifiés des 69 inchangés.

## Leçons

1. **Un prompt cité dans une commande shell peut s'exécuter.** Il faut la forme sûre de lancement (prompt dans un fichier) et une empreinte. L'empreinte a aussi détecté, pour le réancrage du gate, une recopie qui avait remplacé les apostrophes droites par des apostrophes typographiques.
2. **Un déploiement du démon sans `--restart-daemon` laisse tourner l'ancien code.** Le premier passage du 11/10 a copié les fichiers sans rien changer au comportement ; seul le second a fait foi.
3. **Le garde-fou CI ne doit juger que la branche déployée.** Un run annulé d'une autre branche créée sur le même SHA a fait refuser un déploiement à tort (CC-59).
4. **Un gate ancré sur un défaut du terrain casse quand une story corrige ce défaut**, et la maquette d'un test n'est pas le terrain : le parcours de référence s'ancrait sur une commande bloquante de 579, corrigée par le bloc B ; et la pièce du parcours de découverte était 25, non 3.
5. **Un processus lancé en arrière-plan par un agent meurt à la fin de son tour.** Lancer avec `setsid -f`.
6. **Les tours de clawcode sont plafonnés à 300 s** : messages courts et autoportants.
7. **Avant de qualifier un défaut de publication, vérifier la présence réelle dans HA** (erratum de ClaudeBox du 06/10 sur 5369, qui l'avait jugée non publiée).

## Réserve

**AC 13 a.** L'essai de réactivation d'un scénario par un humain n'a pas été fait. Il est couvert par les tests unitaires de #237, et HA garde dans `deleted_entities` les réglages des entités retirées. **Décision d'Alexandre du 2026-10-12 vers 05:50 : clôture avec cette réserve.** La vérification se fera à la prochaine réactivation naturelle d'un scénario (suivi ClaudeBox CC-61).

## Suite

- **Epic 22** : CC-36 (noms Home Assistant = noms Jeedom), compteurs, CC-51, CC-55, CC-58, CC-60, en deux stories (22-1 puis 22-2).
- Puis **la parité HomeKit** (CC-33).
- **Découverte de terrain reportée à 22-1** : HA 2026.9.4 n'applique plus `object_id` depuis le 2026-05-06.

## Conclusion

L'epic 21 est clos : ses gates epic-level sont tenus, CC-44 et CC-47 sont fermés et prouvés sur la box, avec une seule réserve connue et suivie (AC 13 a).
