# Refonte de la surface « Configuration Home Assistant par pièce » — cadrage (ClaudeBox, 18/10/2026)

## Origine
- 22-2 déployée et prouvée le 12/10 ; **validation UX refusée par Alexandre le 18/10 17:58** : « pas clair, brouillon, pas très joli ». 22-2 reste `ready-for-UX-validation` et sera close par cette refonte (superseded).
- Diagnostic par un agent UX/UI indépendant (captures réelles du 18/10, code de la surface) : `diagnostic-ux.md` ; maquettes (données fictives) : `maquettes.html` — copiés dans ce dossier par Alexandre.
- **Décision d'Alexandre (18/10 18:15) : A + B + C**, après validation de faisabilité par ClaudeBox (§ 5 du diagnostic).

## Diagnostic en 6 points (détail : diagnostic-ux.md, P1-P15)
1. Aucune grammaire visuelle : état, compteur, cause et action ont tous la forme d'une pastille ou d'un bouton gris.
2. Trois vérités contradictoires : badge « Sera publié : N prête(s) » (plan, futur) ≠ compteurs « N publiées / M non prises en charge » (présence réelle) ≠ tableau ; un désactivé affiché « Exclu » (P2).
3. « Non pris en charge » mélange commandes techniques sans équivalent HA (Rafraîchir, Pinguer…) et vrais blocages : fausse alarme permanente (P3).
4. Palette pastel du thème clair en dur sur le thème sombre ; bleu sans sens ; « Bloqué » le moins visible ; « Supprimer » rouge comme action principale (P4-P6).
5. Grille des pièces sans aucun état (P1) ; listes sans tri ni filtre (P8).
6. 20 termes pour 6 notions, franglais (« Override HA », `switch`, « Bridge ») (P13).

## Glossaire imposé (un mot = une notion, partout)
- Équipement : **Publié** (vert) / **À appliquer** (bleu) / **Bloqué** (orange, cause + action) / **Exclu** (gris) / **Désactivé** (gris italique, PRIME sur Exclu) / **Rien à publier** (gris). Publié avec des commandes bloquées = « Publié » + mention orange « N bloquées » (pas d'état « partiel »).
- Commande : **Publiée** → *Lumière (light)* / **Bloquée** → cause / **Ignorée** (pas d'équivalent HA, repliée, non comptée comme défaut) / **Exclue**.
- Réglage de publication : **Automatique / Toujours / Jamais** (remplace Revenir / Forcer / Exclure). Réglage de type : « Type HA : auto (light) » / « Type HA : sensor (imposé) » (le mot override disparaît de l'écran).
- Actions : Appliquer, Republier, Supprimer de Home Assistant… (même forme partout), Relire Jeedom (ex-« Rescanner la topologie »). « Bridge » → « Démon ». Pluriels accordés, pas de point final dans les étiquettes, domaine HA traduit avec le terme technique en petit.
- L'état d'un équipement est UNE fonction pure (plan + réalité → état), qui remplace `publicationSummaryState` ; si plan et réalité divergent → « À appliquer ».

## Les trois directions retenues et leur assemblage
- **A — socle partout** : état unique + glossaire ; palette sémantique (4 teintes) sur les variables du thème ; contrôle segmenté Automatique/Toujours/Jamais ; « Appliquer » visible seulement si un réglage attend ; Republier/Supprimer dans un menu « ⋯ » ; tableau des commandes regroupé par entité, colonnes `Commande | Dans Home Assistant | Type Jeedom | Type HA` ; cause dite une fois par équipement avec bouton « Ouvrir les types génériques » ; commandes ignorées repliées ; un seul équipement déplié, en-tête collant ; plus de défilement imbriqué ; icône et couleur Jeedom de chaque objet, cartes regroupées par objet parent.
- **B — page principale** : barre de santé compacte (+ actions, menu « ⋯ » avec diagnostic et suppression globale) ; jauge maison « N publiés sur M » dont chaque segment est un filtre global (toutes pièces) ; cartes de pièce avec jauge segmentée et repères « N bloqués / N à appliquer » ; bandeau bleu supprimé.
- **C — vue de travail** : un clic sur une carte ou un filtre ouvre, À LA PLACE de la modale, une vue maître-détail pleine hauteur dans la page du plugin : arbre pièces → équipements filtrable/recherchable à gauche, détail de la pièce (« À traiter dans cette pièce ») ou de l'équipement à droite ; retour à la page principale ; panneau gauche repliable sous une largeur seuil (tablette, iPad mural).
- Ordre : A → route agrégée + B → C.

## Contraintes Jeedom (vérifiées sur la box, Jeedom 4.6.1, 18/10)
- Page du plugin = HTML libre dans la zone de contenu ; grille + modale = convention, pas obligation (aucune règle écrite trouvée ; avis de la revue humaine Market non vérifiable).
- Thème : `<body data-theme="core2019_Dark|core2019_Light">`. Variables du core : `--bg-color` (triplet), `--bg-modal-color`, `--txt-color`, `--link-color`, `--logo-primary-color`, `--al-success-color`, `--al-warning-color`, `--al-danger-color`, `--al-info-color`, `--eqTitle-color`, `--btn-default-color`, `--border-radius` (= 0rem en sombre : angles droits). Compléter par des `--j2ha-*` sous `body[data-theme*="Dark"|"Light"]`. Fonds d'état translucides (`color-mix`, repli `rgba`). Plus aucune couleur en dur.
- Disponibles : jQuery 3.6, Bootstrap 3, bootbox, jeeDialog, jeedomUtils, Font Awesome 5 local, icônes `jeedom-*`. Aucune police ni bibliothèque externe.
- CSS préfixé `.j2ha-…`, jamais de restylage global des classes du core.
- Tester thèmes clair/sombre + bascule auto, et **Jeedom 4.4** (compatibilité annoncée ; variables relevées sur 4.6.1).
- Libellés via `{{…}}`/`__()`, i18n, tests Node de libellés (20-3, 22-2), `index.md`, `compteurs.md` à réécrire : coût à prévoir.
- Performance : jauges B et arbre C = **une route agrégée côté démon** (états par pièce et par équipement en un appel) ; jamais 300 GET à l'ouverture.
- CC-48 : captures et preuves sur la démo VM 122 (et box pour la preuve terrain, identifiants seuls).

## Stories proposées
1. Socle A : fonction d'état unique + glossaire + palette/variables thème + réorganisation de la fenêtre de pièce (sans changer la structure grille + modale) ; doc et tests de libellés réalignés ; clôt 22-2.
2. Route agrégée côté démon (états par pièce/équipement, mise en cache, invalidation à la synchro).
3. Page principale B : barre de santé, jauge maison + filtres globaux, cartes de pièce.
4. Vue maître-détail C (remplace la modale) : arbre filtrable, détail pièce/équipement, repli tablette, retour arrière, état d'URL.
5. Recette UX finale par Alexandre + captures 23-2 sur la démo.
