# Story 20.2 — preuve terrain partielle

**Date :** 2026-10-08
**SHA déployé :** `79127a5`
**Statut :** preuve terrain consignée ; story maintenue en `review`.

## Éléments validés

- Déploiement standard, sans cleanup ni rescan, terminé avec sauvegarde et rollback disponibles.
- Gate 20-0 sur `main` : découverte, référence et parcours 20.2 (exclusion/retrait simulés) PASS ; contrôle d'écriture non déclarée bloqué comme attendu.
- Cible terrain : eq287 `CHACON_porte-garage`, non publiée, sans override initial et sans topic HA/MQTT. Le périmètre autorisé par Alexandre était exclusivement l'exclusion de cette cible, sans forçage.
- Parcours réel réalisé dans Jeedom : **Exclure → Appliquer → Revenir au mode automatique**. Alexandre confirme avoir vu l'état `Exclu`, le badge `pas encore appliqué dans Home Assistant`, et confirme que le second clic `Appliquer` après le retour est bien le sien.
- État final : override eq287 absent, décision revenue à `ambiguous_skipped`, équipement non publié. La parité avant/après est strictement identique : aucune décision, aucun topic MQTT/HA et aucun écouteur ne diffèrent.

## Anomalie observée

Le premier clic `Appliquer` a affiché `Listener non trouvé : 28449`.

Le diagnostic en lecture seule établit que ce message vient du coeur Jeedom lors du réalignement global des écouteurs d'état : un rappel porteur d'un identifiant d'une génération précédente est arrivé après la suppression de cette ligne. L'identifiant ne concerne pas eq287 ; eq287 ne porte que des commandes d'action et aucun écouteur d'état. Aucun écouteur n'a été perdu, aucun effet HA/MQTT n'a été observé et le retour automatique est complet. Il s'agit d'une course préexistante à consigner comme dette séparée, pas d'une régression 20.2.

## Écart restant avant transition

L'AC11 exige un témoin `getBridgeStatus` relevé avant et après le parcours réel. Cette lecture, disponible seulement dans une session navigateur authentifiée, n'a pas été capturée autour des clics. Les autres témoins (hash d'overrides, PID, journaux, écouteurs, parité et MQTT) sont conformes mais ne remplacent pas littéralement ce témoin. La story reste donc `review` ; elle ne passe ni `ready-for-UX-validation` ni `done` sur la seule base de cette preuve.

## Références de preuve

- Relevés de parité avant/après et rapports du gate conservés hors dépôt sur l'environnement de preuve.
- Journaux Jeedom et démon lus en lecture seule par ClawBox durant le diagnostic.
