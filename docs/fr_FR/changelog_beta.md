# Changelog — jeedom2ha (beta)

>**NOTE**
>
>S'il n'y a pas d'information sur la mise à jour, c'est que celle-ci concerne uniquement de la documentation, une traduction ou des corrections mineures.

---

# 2026-10-12 — Noms Jeedom dans Home Assistant et entity_id stable

- Chaque appareil prend le nom de l'équipement Jeedom, identique pour toutes ses entités (avant, un appareil pouvait porter le nom d'une de ses commandes). Un équipement à une seule entité affiche le nom de l'équipement ; un équipement à plusieurs entités affiche le nom de chaque commande à la suite du nom de l'appareil
- Un renommage dans Jeedom atteint Home Assistant au prochain rescan, redémarrage du démon ou « Republier »
- Les entités nouvelles ou recréées reçoivent un `entity_id` technique stable (`<domaine>.jeedom2ha_…`) : une entité supprimée puis recréée reprend son `entity_id` technique, et les automatisations, scripts et cartes qui le citent survivent à la recréation
- Les `entity_id`, noms et pièces déjà présents dans Home Assistant, y compris ceux que vous avez choisis à la main, ne sont pas modifiés

---

# 2026-10-11 — Affichage d'une commande publiée par une entité secondaire

- Une commande d'état portée à la fois par une entité principale refusée et par une entité secondaire déjà publiée (par exemple un capteur binaire) s'affiche désormais « Sera publié : binary_sensor » et est comptée « prête » dans la synthèse de l'équipement et les compteurs de la pièce (auparavant « Ne sera pas publié » et « bloquante » à tort). Correction d'affichage uniquement : rien de ce qui est publié dans Home Assistant ne change
- Cause « état sans ordre On/Off » reformulée pour un équipement dont l'état est la seule commande : rien à piloter ; choisir le type `binary_sensor` puis « Forcer »

---

# 2026-10-11 — Scénario désactivé : son bouton disparaît de Home Assistant

- Un scénario Jeedom désactivé n'a plus de bouton dans Home Assistant : il est retiré au prochain rescan ou redémarrage du démon, et revient avec le même identifiant à la réactivation
- Les boutons de scénarios déjà orphelins (désactivés ou supprimés avant cette version) sont retirés au premier rescan
- Le bouton d'un scénario ne reprend plus la disponibilité ni le type d'un équipement qui porterait le même numéro : il suit uniquement l'état du pont

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
