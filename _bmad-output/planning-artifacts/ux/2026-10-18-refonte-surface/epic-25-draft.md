# Epic 25 — Refonte de la surface de configuration (A+B+C)

**Statut :** `backlog` — brouillon préparé par clawcode le 2026-10-18 à la demande de ClaudeBox (relais des décisions d'Alexandre du 18/10), versé dans `epics-projection-engine.md` et `sprint-status.yaml` le 2026-10-18 après les décisions Q1-Q4 ci-dessous. Toutes les stories restent `backlog` : relecture ClaudeBox obligatoire sur chaque story avant tout `ready-for-dev` ; ce cadrage n'autorise aucun développement ni fusion.

**Numéro :** 25 (prochain libre ; epics 23 — Market — et 24 — parité HomeKit — déjà occupés dans `sprint-status.yaml`).

**Origine :** `CADRAGE.md` dans ce même dossier (`_bmad-output/planning-artifacts/ux/2026-10-18-refonte-surface/`), rédigé par ClaudeBox le 18/10/2026 à partir du diagnostic UX indépendant (`diagnostic-ux.md`, 15 problèmes) et des maquettes (`maquettes.html`, directions A/B/C). Fait suite au refus de validation UX de la story 22-2 par Alexandre (18/10 17:58 : « pas clair, brouillon, pas très joli »). 22-2 reste `ready-for-UX-validation` et sera close par cet epic (superseded), sans réouverture de `PRODUCT_SCOPE`.

**Valeur :** une surface de configuration par pièce cohérente (une seule grammaire visuelle, un seul vocabulaire), lisible au premier coup d'œil (page principale avec vue d'ensemble) et exploitable pour un travail fin (vue maître-détail), sur les deux thèmes Jeedom et sans régression de performance.

**Décision d'Alexandre (18/10 18:15) :** les trois directions A + B + C, assemblées dans l'ordre A → route agrégée + B → C, après validation de faisabilité Jeedom par ClaudeBox (cf. § 5 du diagnostic et la section « Contraintes Jeedom » du cadrage).

**Objectif :**
1. remplacer les trois sources de vérité contradictoires (badge plan, compteurs, tableau) par une fonction d'état unique (plan + réalité → état) ;
2. imposer le glossaire unique (équipement : Publié / À appliquer / Bloqué / Exclu / Désactivé / Rien à publier ; commande : Publiée / Bloquée / Ignorée / Exclue ; réglage : Automatique / Toujours / Jamais) sur tout l'écran, sans « override » ni franglais résiduel ;
3. porter la palette sémantique sur les variables de thème Jeedom (clair/sombre), sans couleur en dur ;
4. donner une vue d'ensemble actionnable sur la page principale (barre de santé, jauge maison filtrante, cartes de pièce) ;
5. remplacer la modale par une vue maître-détail pleine hauteur (arbre pièces → équipements, détail à droite), repliable sous un seuil de largeur ;
6. servir B et C par une route agrégée côté démon (états par pièce et par équipement en un appel), sans explosion du nombre de requêtes à l'ouverture.

**Périmètre :** `desktop/js` et `desktop/php` de la surface de configuration par pièce (fenêtre de pièce, page principale, nouvelle vue maître-détail) ; une route agrégée côté démon (lecture seule, pas de nouveau champ de décision) ; variables CSS `--j2ha-*` sous les deux thèmes ; libellés i18n et leurs tests Node ; `index.md`/`compteurs.md` à réécrire pour refléter le nouveau vocabulaire.

**Hors périmètre :** toute modification du contrat de décision (`evaluate_equipment()`, `CommandDecision`), des artefacts figés (`models/taxonomy.py`, `models/cause_mapping.py`, `models/ui_contract_4d.py`) ou des tables de mapping ; toute donnée ou capture provenant de la maison réelle (CC-48, démo VM 122 et box pour la preuve terrain, identifiants seuls) ; les epics 23 (Market) et 24 (parité HomeKit), sauf dépendance de planning sur 22-2.

**Contraintes à tenir (détail : `CADRAGE.md`, section « Contraintes Jeedom », vérifiées sur la box Jeedom 4.6.1 le 18/10) :** thème via `<body data-theme>` et variables du core (`--bg-color`, `--al-success-color`, etc.) ; jQuery 3.6 / Bootstrap 3 / bootbox / jeeDialog / jeedomUtils / Font Awesome 5 local uniquement, aucune bibliothèque externe ; CSS préfixé `.j2ha-…` ; tester clair/sombre + bascule auto et Jeedom 4.4 ; libellés via `{{…}}`/`__()` avec tests Node de libellés alignés (modèle 20-3, 22-2).

**Garde-fous :** CC-48 ; VM et snapshots par ClawBox, Chrome par ClaudeBox ; aucune donnée ou accès maison dans Git ; une story = une PR ; après approbation d'Alexandre et relecture ClaudeBox, workflow BMAD complet `create-story → dev-story → code-review` ; toute story qui touche l'écran passe par `ready-for-UX-validation` et le gate 20-0 avant `done` ; aucun nom réel d'équipement, de pièce, de scénario ou de personne dans le dépôt.

## Stories proposées

- **25.1 — Socle A : état unique, glossaire, palette de thème.** Fonction d'état unique (remplace `publicationSummaryState`) ; glossaire imposé partout (équipement, commande, réglage de publication/type) ; palette sémantique à 4 teintes sur les variables `--j2ha-*` des deux thèmes ; réorganisation de la fenêtre de pièce (contrôle segmenté Automatique/Toujours/Jamais, « Appliquer » conditionnel, menu « ⋯ » pour Republier/Supprimer, tableau des commandes regroupé par entité avec colonnes `Commande | Dans Home Assistant | Type Jeedom | Type HA`, cause dite une fois, commandes ignorées repliées, un seul équipement déplié, en-tête collant) sans changer la structure grille + modale. Doc et tests de libellés réalignés (`index.md`, `compteurs.md`). Clôt 22-2 à `done` (superseded) à la preuve terrain ; sa validation UX est transférée à 25.5 (Q1).
- **25.2 — Route agrégée côté démon.** Un appel qui rend les états par pièce et par équipement (lecture seule, dérivé de la fonction d'état de 25.1), avec mise en cache et invalidation à la synchro ; prérequis de performance pour 25.3 et 25.4.
- **25.3 — Page principale B.** Barre de santé compacte (actions + menu « ⋯ » : diagnostic, suppression globale) ; jauge maison « N publiés sur M » dont chaque segment filtre globalement (toutes pièces), recalculée à l'ouverture de la page, après chaque action, à chaque fin de synchro, plus un bouton « Actualiser » (pas de temps réel poussé pour ce premier incrément, Q2) ; cartes de pièce avec jauge segmentée et repères « N bloqués / N à appliquer » ; suppression du bandeau bleu. Dépend de 25.1 (glossaire/état) et 25.2 (route agrégée).
- **25.4 — Vue maître-détail C.** Remplace la modale (retrait de l'ancienne modale inclus dans cette story, pas de story séparée, Q4) par une vue pleine hauteur dans la page du plugin : arbre pièces → équipements filtrable/recherchable à gauche, détail de la pièce (« À traiter dans cette pièce ») ou de l'équipement à droite, retour à la page principale, panneau gauche repliable sous un seuil de largeur à mesurer pendant la story (valeur par défaut 1024 px, preuve incluant l'iPad mural en mode desktop, Q3), état d'URL. Dépend de 25.1 à 25.3 (ouverte depuis une carte ou un filtre de la page principale).
- **25.5 — Recette UX finale et preuve terrain.** Validation UX finale par Alexandre sur l'ensemble A+B+C, reprenant la validation UX transférée de 22-2 (Q1) ; captures pour 23-2 (promotion) sur la démo VM 122 ; preuve terrain CC-48 (box, identifiants seuls). Clôture l'epic.

**Ordre retenu :** 25.1 → 25.2 → 25.3 → 25.4 → 25.5.

**Décisions de cadrage (ClaudeBox, 2026-10-18 18:22, dans le cadre validé par Alexandre) :**
1. **Q1 (clôture de 22-2) :** 22-2 passe à `done` (superseded par 25.1) au moment de la preuve terrain de 25.1 ; sa validation UX est transférée à 25.5.
2. **Q2 (fraîcheur des jauges B) :** premier incrément sans temps réel poussé — jauges calculées à l'ouverture de la page, après chaque action, à chaque fin de synchro, plus un bouton « Actualiser ».
3. **Q3 (seuil de repli du panneau C) :** à mesurer pendant 25.4, valeur par défaut 1024 px ; la preuve inclut l'iPad mural en mode desktop.
4. **Q4 (retrait de l'ancienne modale) :** inclus dans 25.4, pas de story séparée.
