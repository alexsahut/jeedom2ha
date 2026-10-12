# Story 23.1 : Environnement de démonstration rejouable

Status: draft

> Brouillon du 2026-10-12. Relecture ClaudeBox obligatoire avant `ready-for-dev`; aucun développement ou accès VM n'est autorisé.

## Story

En tant que mainteneur, je veux une démo synthétique, rejouable et isolée, afin de produire des preuves Market sans données de la maison.

## Critères d'acceptation proposés

1. Après le snapshot **vierge** pris par ClaudeBox sur VM 122 (Debian 12, unité A66), un script API Jeedom idempotent crée Salon, Cuisine, Chambre, Bureau, Garage et environ quinze Virtuel anonymes.
2. Le jeu couvre lumière on/off, lumière variable, volet positionnable, prise avec W, température/humidité, ouverture, présence, compteur kWh cumulatif et trois scénarios; types génériques posés.
3. Mosquitto est local; HA de test avec MQTT est installé à l'emplacement proposé et validé par ClaudeBox; aucune dépendance à la maison.
4. Rejouer le script ne crée aucun doublon et produit un inventaire anonymisé.
5. ClaudeBox prend le snapshot **demo** et dispose de Chrome pour les captures.
6. CC-48: aucun secret, IP privée, nom réel ou donnée maison dans Git.

## Tâches proposées

- [ ] **Prérequis — snapshot `vierge` :** l'unité ClawBox `a66-reprise-diagnostic` doit avoir achevé le snapshot de la VM 122; ne pas créer la démo avant cette confirmation.
- [ ] ClaudeBox confirme topologie VM et méthode snapshot; Mosquitto local est le composant prévu par A66.
- [ ] Écrire script API, contrôle idempotence et inventaire.
- [ ] Créer Virtuel/commandes/types génériques synthétiques.
- [ ] Configurer HA dans le conteneur Docker `ghcr.io/home-assistant/home-assistant` sur VM 122; si 2 Go ne suffisent pas, proposer le passage à 3 Go à ClawBox/Alex avant action.
- [ ] Vérifier Jeedom → MQTT → HA, créer les comptes de démo hors dépôt, puis snapshot demo.

## Garde-fous

- VM, snapshots et Chrome: ClaudeBox uniquement. Les URL de démonstration et les comptes restent hors dépôt; aucun secret dans Git.
- Aucun accès dans Git, arguments de commande ou journaux.
