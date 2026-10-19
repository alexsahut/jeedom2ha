# Story 22-3 — preuve de terrain (2026-10-20)

> **Statut de ce document.** Rédigé par ClaudeBox le 20/10/2026 vers 01:20 (Task 6, part ClaudeBox).
> - Il ne cite que des identifiants (CC-48).
> - Toutes les mesures sont **en lecture seule** : aucune publication MQTT, aucun redémarrage, aucune écriture Jeedom ni Home Assistant.
> - Relevé des payloads de découverte retenus : clawcode (outillage du gate 20-0, sur la VM). Recomptage indépendant : ClaudeBox, sur le fichier brut. Entités exposées à Assist : ClaudeBox, par le contexte en direct de Home Assistant.

## Ce qui est déployé

| Élément | Valeur |
|---|---|
| SHA | **`ae84d6e18cef853dbf71e0637bb8e1d870781097`** (`main` après #315). Le correctif 22-3 (#267, `2b7a058`) est en service depuis le déploiement du 18/10 22:10 (`a704dd0`). |
| Fichier brut | VM : `jeedom2ha-gate/reports/22-3-2026-10-20/discovery-configs-retained.raw` (payloads retenus `homeassistant/+/+/config`) |

## Mesures

| Mesure | Valeur | Lecture |
|---|---|---|
| Topics de découverte jeedom2ha | **348** | recompté par ClaudeBox (348) |
| Payloads `"name": null` (l'entité prend le nom de son appareil) | **168** | recompté par ClaudeBox (168) ; exemples `jeedom2ha_eq_391`, `392`, `457`, `459`, `603` |
| Payloads dont `name` est égal au nom de l'appareil | **0** | aucun doublon certain (AC1) |
| Payloads dont `name` commence par le nom de l'appareil suivi d'une espace | **0** | aucun doublon partiel |
| Noms doublés « X X » parmi les entités exposées à Assist | **0** | contexte en direct de HA, 19/10 au soir ; chaque bouton de scénario n'a qu'un nom |

Mise en regard avec le constat du 18/10 (`25-1-preuve-terrain-2026-10-18.md`) : 349 entités, dont 169 à `original_name = null` et 180 inchangées, aucun `entity_id` changé. L'écart de 1 (349 → 348, 169 → 168) correspond à un bouton de scénario retiré parce que son scénario est désactivé dans Jeedom par l'automatisme de la maison (comportement 21-1, constaté plusieurs fois le 19/10 sur les scénarios 39, 40 et 129). Ce n'est pas un effet de 22-3.

## Correspondance avec la preuve attendue

1. **Nom affiché = nom de l'appareil** : fait. 168 entités publient `name: null`, aucune ne publie un nom égal ou préfixé par celui de son appareil. Le chiffre de 131 du 12/10 a évolué avec le parc (voir 18/10).
2. **Aucun `entity_id`, appareil ou entité créé, supprimé ou renommé dans son identifiant** : constaté le 18/10 sur les registres de HA, lors de la mise en service ; les déploiements suivants ne touchent pas `publisher.py`.
3. **Inventaire MQTT identique en nombre** : 348 topics, conforme aux relevés de la soirée du 19/10 compte tenu des boutons de scénario qui suivent l'état de leur scénario.
4. **Essai vocal du scénario 38** : **reste à faire par Alexandre** (`HassTurnOn` avec le nom du scénario ; le 12/10 il donnait `MatchFailedError`).

## Bilan

Le volet démon de 22-3 est prouvé sur la box. Seul l'essai vocal d'Alexandre reste. 22-3 reste en `review` (story démon sans écran : `ready-for-UX-validation` ne s'applique pas, `docs/bmad-parcours-rapide-complet.md`) et passera à `done` si l'essai est concluant.
