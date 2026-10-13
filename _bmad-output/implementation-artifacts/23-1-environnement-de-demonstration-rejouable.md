# Story 23.1 : Environnement de démonstration rejouable

Status: done

> Preuve terrain complétée le 2026-10-13 sur l'environnement de démonstration synthétique (CC-48 respecté).

## Story

En tant que mainteneur, je veux une démo synthétique, rejouable et isolée, afin de produire des preuves Market sans données de la maison.

## Critères d'acceptation proposés

1. Après le snapshot **vierge** pris par clawbox sur VM 122 (Debian 12, unité A66), un script API Jeedom idempotent crée Salon, Cuisine, Chambre, Bureau, Garage et environ quinze Virtuel anonymes.
2. Le jeu couvre lumière on/off, lumière variable, volet positionnable, prise avec W, température/humidité, ouverture, présence, compteur kWh cumulatif et trois scénarios; types génériques posés.
3. Mosquitto est local; HA de test avec MQTT est installé à l'emplacement proposé et validé par ClaudeBox; aucune dépendance à la maison.
4. Rejouer le script ne crée aucun doublon et produit un inventaire anonymisé.
5. clawbox prend le snapshot **demo**; ClaudeBox dispose de Chrome pour les captures.
6. CC-48: aucun secret, IP privée, nom réel ou donnée maison dans Git.
7. Le jeu comprend au moins un équipement sans type générique et un équipement exclu, afin de rendre « Ne sera pas publié — et pourquoi » et « Exclu » dans l'écran par pièce.

## Tâches proposées

- [x] **Prérequis — snapshot `vierge` :** l'unité ClawBox `a66-reprise-diagnostic` a achevé le snapshot de la VM 122 avant la création de la démo.
- [x] Topologie confirmée : Mosquitto local et HA de test Docker ; aucune dépendance à la maison.
- [x] Script API, contrôle idempotence et inventaire implémentés puis prouvés sur VM.
- [x] Virtuel/commandes/types génériques synthétiques créés.
- [x] HA configuré dans Docker et intégration MQTT validée.
- [x] Accès de déploiement VM fourni à clawcode hors dépôt.
- [x] Chaîne Jeedom → MQTT → HA vérifiée ; snapshot `demo` pris par clawbox.

## Garde-fous

- VM et snapshots: clawbox; Chrome: ClaudeBox. Les URL de démonstration et les comptes restent hors dépôt; aucun secret dans Git.
- Aucun accès dans Git, arguments de commande ou journaux.

## Dev Agent Record — preuve terrain (2026-10-13)

- **Environnement :** VM 122 démarrée depuis le snapshot `vierge`; Docker CE 29.9.0 installé depuis le dépôt officiel, car les couches zstd de l'image Home Assistant 2026.9.4 ne sont pas lisibles par Docker.io 20.10. Le plugin Virtuel utilise sa branche `master` (aucune branche `stable`).
- **Installation :** première installation via le paquet Market construit à `e94b01d` : 77 fichiers, manifeste respecté, `pluginVersion` 1.2.0. `deploy-to-box.sh` est réservé aux mises à jour d'une installation déjà présente.
- **Jeu de démo :** `populate_demo.py`, après les correctifs #268 et #269, a produit 69 `would_create` au dry-run puis `created: 69` au peuplement réel (5 pièces, 16 équipements, 45 commandes, 3 scénarios).
- **Validation applicative :** plugin activé, Mosquitto local sur loopback, bridge en ligne ; HA onboardé par Alex et intégration MQTT réalisée par ClaudeBox. 17 découvertes LAN ont été ignorées ; HA a exposé 19 entités MQTT (17 appareils et le broker).
- **Clôture environnement :** snapshot `demo` pris à 08:47 ; VM laissée allumée.
- **Idempotence (fil P2 #270) :** cause = champ Jeedom `unite` ignoré sous la clé `unit` (correctif #271) ; après #271, 1er passage `exists: 58, updated: 11` (pose des unités manquantes), 2e passage `exists: 69`, aucune création.

### Notes de suivi (hors correction dans cette story)

- Un équipement à deux capteurs (Climat) ne produit qu'une entité : nouvelle story à cadrer pour le multi-capteur hors MSunPV.
- Les scénarios sans pièce ne sont pas placés dans une zone HA.
- Les états initiaux restent inconnus lorsque les infos Virtuel n'ont pas de valeur ; suivre l'idée d'initialiser des valeurs synthétiques via `cmd::event` dans le peuplement.
