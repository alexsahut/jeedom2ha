# Changelog — jeedom2ha

>**NOTE**
>
>S'il n'y a pas d'information sur la mise à jour, c'est que celle-ci concerne uniquement de la documentation, une traduction ou des corrections mineures.

---

# 2026-10-11 — Nouvelle interface par pièce et documentation réécrite

- Nouvelle page principale : un bandeau de santé (Bridge, MQTT, Dernière synchro, Dernière opération), la zone « Actions Home Assistant » et une carte par pièce (plus une carte « Sans pièce »)
- Configuration par pièce : la fenêtre d'une pièce liste ses équipements, dit pour chacun s'il sera publié dans Home Assistant et, sinon, pourquoi, avec les mots de l'écran
- Tableau des commandes à quatre colonnes (« Commande », « Type Jeedom », « Override HA », « Diagnostic ») : le type Home Assistant d'une commande se choisit directement, avec vérification instantanée
- Nouveaux boutons « Exclure », « Forcer » (avec aperçu avant écriture) et « Revenir au mode automatique », par équipement et par entité Home Assistant ; « Appliquer » pour publier un réglage en attente ; chaque bouton grisé explique pourquoi dans une infobulle
- « Republier » et « Supprimer puis recréer » disponibles pour le parc, une pièce ou un équipement, avec confirmation et mise en garde
- « Rescanner la topologie Jeedom » directement sur la page principale
- Compteurs en haut de la fenêtre d'une pièce
- Retrait de l'ancienne synthèse globale du parc, du bouton « Diagnostic » et de l'onglet de la fiche d'équipement : leur contenu vit désormais dans la configuration par pièce
- Documentation utilisateur réécrite pour décrire cet écran, avec la liste des causes de non-publication

# 2026-09-27 — v0.3.0

- Le plugin est désormais prévu pour Debian 11 et 12
- La version du plugin est lisible (0.3.0), et le démon l'indique dans son journal à son démarrage

# Mars 2026 — premières versions

- Lecture de vos équipements Jeedom avec leurs pièces, et publication dans Home Assistant des lumières (simples et variables), des volets et des prises
- Configuration de la connexion au broker MQTT (détection automatique de MQTT Manager ou saisie manuelle, chiffrement TLS) et affichage de l'état de la connexion
- Remontée en continu des états Jeedom vers Home Assistant, et pilotage depuis Home Assistant avec confirmation de l'état réel
- Disponibilité du pont et des équipements indiquée dans Home Assistant
- Exclusions par plugin, par pièce et par équipement, et choix de la politique de publication (équipements sûrs, ou sûrs et probables)
- Commandes en double de même type générique : gérées sans doublon
- Premier écran de diagnostic de couverture avec suggestions de correction (remplacé depuis par la configuration par pièce)
- Nouvelle icône du plugin et documentation réécrite
