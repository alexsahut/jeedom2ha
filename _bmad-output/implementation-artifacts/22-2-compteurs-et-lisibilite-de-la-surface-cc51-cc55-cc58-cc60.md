# Story 22.2 : Compteurs et lisibilité de la surface (compteurs, CC-51, CC-55, CC-58, CC-60, P3 de 20-3)

Status: ready-for-dev

> **Statut : `ready-for-dev` (2026-10-12).** Alexandre a tranché les questions le 2026-10-12 vers 05:50, relayé par ClaudeBox : **Q1 A, Q2 A, Q3 A, Q4 B, Q5 A, Q6 C, Q7 A (sous réserve de la Task 0 a), Q8 A, QD une seule story** (voir « Décisions d'Alexandre »). `ready-for-dev` est accordé par ClaudeBox au nom de cette décision. **Ordre : après 22-1.** Brouillon de cadrage rédigé par une session cloud déléguée (documentaire, lecture seule : aucun accès box, Home Assistant ni secret). Pointeurs pris sur `main` à `ab3a854`. R1 (ClaudeBox) : C9 reformulé (cause non affirmée). Aucun nom réel (CC-48) : identifiants seuls.

## Story

En tant qu'utilisateur du plugin qui ouvre une pièce puis un équipement,
je veux voir d'un coup d'œil combien d'éléments sont réellement dans Home Assistant, lesquels attendent une application et lesquels ne sont pas pris en charge, avec des boutons dont la portée est claire et dont les libellés tiennent leur promesse,
afin de ne plus me demander si un bouton double un autre, si « recréer » recrée vraiment, ni pourquoi un type proposé est refusé.

**Parcours : démon + interface** (`desktop/js/`, `core/ajax/` si besoin). Gate 20-0 et `ready-for-UX-validation` avant `done`.

## Décisions d'Alexandre (2026-10-12, vers 05:50, relayées par ClaudeBox)

`ready-for-dev` est accordé par ClaudeBox au nom de cette décision. Cette story passe **après 22-1**.

- **Q1 A** — « publiés » : équipements d'après `published_in_ha` ; commande « publiée » = portée par au moins une entité présente dans HA.
- **Q2 A** — trois notions principales : publiés / en attente d'application / non pris en charge (bloquant ou non couvert). **Exclu** et **désactivé dans Jeedom** restent visibles à part.
- **Q3 A** — compteurs dans l'en-tête de la pièce **et** dans chaque équipement déplié.
- **Q4 B** — libellés de portée **et** masquage des actions d'entité quand l'équipement n'a qu'une entité et qu'elles doublent celles de l'équipement (sous réserve de la Task 0 b).
- **Q5 A** — libellé fidèle : « Supprimer de Home Assistant » (équipement, pièce, parc), avec rappel que « Republier » le remet. Aucune recréation enchaînée.
- **Q6 C** — sélecteur « Override HA » désactivé, avec explication, sur une commande portée par deux entités (CC-58).
- **Q7 A** — la liste « Override HA » ne propose que des types qui peuvent aboutir (CC-60). **Sous réserve de la Task 0 a** : si elle montre qu'un forçage ou une projection corrigée débloque ces types, **revenir vers ClaudeBox avant de coder**.
- **Q8 A** — P3 de 20-3 inclus (bandeau rafraîchi après un échec de « Republier », assertion de faux DOM).
- **QD** — une seule story.

## Contexte

- **Décision d'Alexandre (2026-10-11 15:48)** : petite story « compteurs », regroupée avec CC-51. « Publiés » = présents dans HA (`published_in_ha`, exposé par le démon depuis la R2 de 20-3), plus « en attente d'application » et « non pris en charge ».
- **CC-51 (retour d'Alexandre du 2026-10-09, équipement 287)** : « aucun compteur, et des boutons me semblent redondants ».
- **CC-55.** « Supprimer puis recréer » ne recrée rien (équipement, pièce, parc). Antérieur à l'epic 20 (story 5.3).
- **CC-58.** Sur une commande portée par deux entités (forme de l'équipement 579, commande 5369 : principal `switch` refusé, `binary_sensor` secondaire publié), le type choisi dans « Override HA » s'applique au principal (clé `eq:cmd` partagée), pas à l'entité qui publie. Limite consignée en 21-1.
- **CC-60 (relevé du 2026-10-12).** Équipement 380 (entité `cover` `ambiguous` `state_orphan` ; seule bloquante : commande 2971 `FLAP_STATE` ; 2968 à 2970 sans type générique) : la liste « Override HA » de 2971 propose `sensor` et `binary_sensor`, mais l'aperçu réel refuse les deux (`ha_missing_state_topic`, `ambiguous_skipped`).
- **P3 reportés par 20-3** (R2) : bandeau non rafraîchi après un échec de « Republier » ; une assertion de test liée au faux DOM ; File List.
- **Documentation 20-5** : le bloc `compteurs` (`docs/fr_FR/compteurs.md`, isolé) attend cette story ; les captures viennent après (décision d'Alexandre, 2026-10-11 17:35).
- **Hors périmètre :** noms et pièces HA (22.1), parité HomeKit (CC-33), chantier Market, tout changement de ce qui est publié (hors Q7 si option C).

## Faits relevés dans le code (lecture seule)

| # | Fait | Pointeur |
|---|---|---|
| C1 | Les compteurs sont calculés **côté interface** à partir des arbres déjà lus (un `GET` par équipement) : `summarizeRoom` compte, par équipement, `publish`/`partial` comme « publié », plus exclu, désactivé, « à corriger » ; par commande : prête, bloquante, non couverte. | `desktop/js/jeedom2ha_mapping_override.js:910-940` |
| C2 | « Publié » y est **déduit des diagnostics de commande** (`publicationSummaryState`), pas de la présence réelle dans HA. Le signal de présence `sync_status.published_in_ha` existe (lu seulement pour griser « Supprimer puis recréer »). | `override.js:776-835,861-885` ; lecture : `:70,:999` ; calcul démon : `transport/http_server.py:470-` (`_is_currently_published_in_ha`) |
| C3 | Libellés : « équipement publié / exclu / désactivé dans Jeedom / à corriger » ; « commande prête / bloquante / non couverte » ; « équipement non lu ». | `override.js:947-966` |
| C4 | Rendu : **deux lignes de pastilles dans l'en-tête de la modale de pièce** ; rien dans l'équipement déplié (là, seul le badge « Sera publié… / Partiellement publié… » de `renderSummary`). Aucune ligne de compteurs par équipement. | `desktop/js/jeedom2ha_mapping_surface.js:514-575` (compteurs), `:1039` (hôte), `:768-800` (badge équipement) |
| C5 | Actions d'équipement : « Exclure », « Forcer », « Revenir au mode automatique », puis « Republier »/« Appliquer » et « Supprimer puis recréer ». Actions **d'entité** : mêmes trois boutons (Exclure, Forcer, Revenir) **sur chaque ligne d'entité**, sans indication de portée dans le libellé. Sur un équipement à une seule entité, les deux jeux visent la même chose. | `surface.js:837-868` (`appendPublicationActions`, appelée avec `equipment=true` à `:927` et `false` à `:897`) ; `:944-960` |
| C6 | La cible « équipement » est construite par `equipmentPublicationTarget` : elle lit aussi des overrides qui passent par les entités (`exclude_eqlogic`). Les deux portées ne sont donc pas toujours équivalentes : à vérifier cas par cas (Task 0). | `override.js:231-258` |
| C7 | « Supprimer puis recréer » (équipement, pièce, parc) : confirmation, puis action démon `supprimer` qui dépublie sans republier ; la recréation n'a lieu qu'au « Republier » ou au rescan suivant. Libellés : « Supprimer puis recréer », « Supprimer puis recréer la pièce », titre « Supprimer puis recréer dans Home Assistant ». | `surface.js:680-700,740-760` ; démon : `http_server.py:4034-4075` |
| C8 | Le sélecteur « Override HA » (liste des types) est construit côté interface à partir des types connus du registre de publication, sans filtrer ceux qui seront refusés ; l'aperçu (dry-run) dit ensuite oui/non. | `surface.js:41` (`buildOptions`), `:97-140` (ligne de commande) ; `override.js:695` (`getOverrideSelectorState`) ; registre : `http_server.py:288-305` |
| C9 | Refus `ha_missing_state_topic` : le registre exige un topic d'état pour `sensor`/`binary_sensor`. 2971 est pourtant une commande info d'état (`FLAP_STATE`) : la cause n'est donc **pas** une « commande sans état lisible ». Elle vient probablement de la projection que construit l'override (aucun topic d'état repris de l'entité `cover`). **À établir en Task 0 a**, non affirmé ici. | `validation/ha_component_registry.py:82-93`, `models/cause_mapping.py:110` |
| C10 | Dans la forme 579, l'override de type est clé `eq:cmd` : il atteint l'entité principale, pas le secondaire qui publie. | `mapping/overrides.py:376` (`apply_type_override`) ; limite consignée dans la story 21-1 |

## Critères d'acceptation (figés sur les décisions)

- **AC1.** Les compteurs de la pièce montrent : **publiés** (présents dans HA, d'après `published_in_ha` ; une commande est publiée si au moins une entité présente la porte), **en attente d'application** (override posé, pas encore appliqué : `override_pending`) et **non pris en charge** (bloquant ou non couvert) ; **exclus** et **désactivés dans Jeedom** restent visibles à part. Le « publié » ne dérive plus d'un diagnostic de commande [Q1 A, Q2 A].
- **AC2.** Un équipement déplié affiche ses propres compteurs (publiés / en attente / non pris en charge), en plus de ceux de la pièce [Q3 A].
- **AC3.** Les libellés de portée distinguent « équipement entier » et « cette entité » ; sur un équipement à une seule entité, les actions d'entité qui doublent celles de l'équipement sont masquées (mêmes routes, aucune fonction perdue) ; les équipements multi-entités gardent leurs actions par entité [Q4 B].
- **AC4.** Le libellé « Supprimer puis recréer » devient « Supprimer de Home Assistant » partout (équipement, pièce, parc, confirmations, infobulles, aide, documentation) et rappelle que « Republier » remet l'équipement ; aucune recréation enchaînée, aucun changement de comportement du démon [Q5 A].
- **AC5.** CC-58 : sur une commande portée par deux entités (forme de l'équipement 579, commande 5369), le sélecteur « Override HA » est désactivé avec une explication claire ; aucun changement de publication ni de contrat d'override [Q6 C].
- **AC6.** CC-60 : la liste « Override HA » ne propose que des types qui peuvent aboutir ; sur l'équipement 380, les types refusés (`sensor`, `binary_sensor`) de la commande 2971 ne sont plus proposés, la cause « précisez les types génériques dans Jeedom » restant la voie normale [Q7 A, sous réserve de la Task 0 a].
- **AC7.** P3 : le bandeau de santé est rafraîchi après un échec de « Republier » ; l'assertion de test liée au faux DOM est corrigée [Q8 A].
- **AC8.** Les compteurs d'une pièce sont égaux au recomptage manuel de la pièce (preuve par l'humain, comme en 20-3).
- **AC9.** `docs/fr_FR/compteurs.md` entièrement réécrit (bloc isolé, bandeau d'obsolescence retiré) ; emplacements de captures conservés.
- **AC10.** Gate 20-0 vert ; tests Node/Python/PHP et `flake8` verts ; golden inchangé sauf champ additif éventuel ; **inventaire MQTT et registre HA strictement identiques avant/après** (aucune publication ne change) ; aucun nom réel (CC-48).

## Tâches

- **Task 0 — Établir (lecture seule)** : (a) pour CC-60, **la cause exacte** du refus `ha_missing_state_topic` de 2971 (projection de l'override sans topic d'état repris de l'entité `cover` ?) et si `sensor`/`binary_sensor` peuvent aboutir avec un forçage ou une projection corrigée (test sur l'équipement 380 simulé). **Si oui, s'arrêter et revenir vers ClaudeBox avant de coder (réserve de Q7 A)** ; (b) pour C6, la liste des cas où les actions d'équipement et d'entité ne sont **pas** équivalentes (condition du masquage de Q4 B) ; (c) relevé « avant » : compteurs affichés d'une pièce test.
- **Task 1 — Démon (si besoin, champ additif)** : exposer ce que Q2 exige (par exemple la présence par entité et la liste des commandes non prises en charge) sans nouveau recalcul de décision ; lecture seule.
- **Task 2 — Interface : compteurs** (`summarizeRoom`, `buildRoomCounterLabels`, `renderRoomCounters`, nouvelle ligne par équipement) selon Q1 A, Q2 A, Q3 A.
- **Task 3 — Interface : portées et doublons** (`appendPublicationActions`, `renderEntities`) selon Q4 B.
- **Task 4 — Libellé « Supprimer de Home Assistant »** (équipement, pièce, parc, confirmations) selon Q5 A.
- **Task 5 — CC-58 (sélecteur désactivé, Q6 C) et CC-60 (liste filtrée, Q7 A)**.
- **Task 6 — P3 de 20-3** selon Q8 A.
- **Task 7 — Tests** : Node (faux DOM), Python, gate 20-0 (parcours sur l'équipement 287 : une seule entité ; 579 : deux entités ; 380 : types refusés).
- **Task 8 — Documentation** : réécrire `docs/fr_FR/compteurs.md` ; ajuster `index.md` si besoin ; **captures par l'humain** après la story.
- **Task 9 — Preuve terrain (humain)** : inventaire avant/après (aucune publication ne doit changer), recomptage des compteurs sur au moins une pièce, clic réel des actions touchées.

## Garde-fous

- Gate 20-0 vert avant tout `done` ; aucune écriture transmise à la box par le gate.
- Preuve terrain avec inventaire avant/après : MQTT et registre HA strictement identiques, aucune publication ne change dans cette story.
- Le démon reste l'unique source de décision (`evaluate_equipment()`) : l'interface ne recalcule rien.
- Aucun nom réel (CC-48), aucun secret ; `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Questions pour Alexandre (tranchées le 2026-10-12 : options non retenues marquées « écartée »)

**Q1 — Sur quoi compter « publiés » ?**
- **A (retenue).** Équipements : `published_in_ha` (présence réelle dans HA, déjà décidé). Commandes : « publiée » = portée par au moins une entité présente. Conséquence : le compteur dit vrai, y compris pour la forme 579 (principal refusé + secondaire publié) ; peut différer légèrement d'aujourd'hui (« prêtes »).
- **B (écartée).** Compter aussi les entités HA (ligne supplémentaire). Conséquence : plus d'information, mais trois unités (équipement, entité, commande) qui compliquent la lecture.

**Q2 — Que devient le reste des compteurs actuels (exclu, désactivé, à corriger, bloquante, non couverte) ?**
- **A (retenue).** Trois notions principales : publiés / en attente d'application / non pris en charge (= bloquant ou non couvert). **Exclu** et **désactivé dans Jeedom** restent visibles à part (l'utilisateur les a choisis ou subis, ils ne sont pas des défauts). Conséquence : lecture simple, rien de caché.
- **B (écartée).** Seulement les trois notions décidées ; exclus et désactivés disparaissent des compteurs. Conséquence : plus court, mais un équipement exclu devient invisible dans les chiffres.

**Q3 — Où afficher les compteurs ?**
- **A (retenue).** En-tête de la pièce (déjà là) **et** une ligne dans chaque équipement déplié (répond au « aucun compteur » de CC-51 sur l'équipement 287).
- **B (écartée).** Seulement dans l'équipement déplié. Conséquence : plus de vue d'ensemble de la pièce.

**Q4 — Boutons redondants (CC-51).**
- **A (écartée).** Libellés de portée seulement (« Exclure l'équipement », « Exclure cette entité »…). Conséquence : rien ne disparaît, mais les doublons restent.
- **B (retenue).** Libellés de portée **et** masquer les actions d'entité quand l'équipement n'a qu'une entité et qu'elles doublent celles de l'équipement (sous réserve de C6/Task 0). Conséquence : interface plus courte, aucune fonction perdue (mêmes routes).
- **C (écartée).** Masquer toutes les actions d'entité. Conséquence : perte de la finesse d'exclusion par entité sur les équipements multi-entités.

**Q5 — « Supprimer puis recréer » (CC-55).**
- **A (retenue).** Libellé fidèle : « Supprimer de Home Assistant » (équipement, pièce, parc), avec rappel que « Republier » le remet. Conséquence : changement de texte et de confirmations seulement ; aucun risque pour la maison ; un bouton de moins qui promet trop.
- **B (écartée).** Recréation enchaînée : supprimer puis republier dans la même action. Conséquence : le libellé devient vrai, mais l'action est plus longue sur un parc (lissage, échéance 19.6), et **recrée réellement** les entités : historique, noms et pièces manuels perdus (37 entités, 23 pièces, 1 appareil aujourd'hui). **Un `entity_id` tiré des noms du moment** (HA 2026.9.4 n'applique plus `object_id`, constat de terrain R1) est donné aux entités recréées : il change pour toutes celles dont il dérivait d'un nom, avec les conséquences sur automatisations et tableaux de bord ; Q7 B de 22.1 (décidée) donne aux entités recréées un `entity_id` technique stable `<domaine>.<object_id actuel>` ; une des 306 entités actuelles à `entity_id` dérivé des noms le changerait une fois. Écartée : le libellé fidèle suffit.

**Q6 — Type d'override sur une commande portée par deux entités (CC-58).**
- **A (écartée).** Laisser la limite (déjà consignée en 21-1) et l'expliquer dans l'aide. Conséquence : zéro risque, mais le comportement reste surprenant.
- **B (écartée).** Appliquer le type à l'entité qui publie (clé d'override élargie à l'entité). Conséquence : comportement attendu, mais changement de contrat des overrides et migration des overrides existants.
- **C (retenue).** Désactiver le sélecteur sur ces commandes avec une explication claire. Conséquence : petite correction d'interface, aucun changement de publication.

**Q7 — Liste « Override HA » refusée à l'aperçu (CC-60).**
- **A (retenue).** Ne proposer que les types qui peuvent aboutir (liste filtrée par le démon ou par l'aperçu), si Task 0 a montre qu'aucun forçage ni correction de projection ne les débloque. Conséquence : plus de choix voué à l'échec ; la cause « précisez les types génériques dans Jeedom » reste la voie normale.
- **B (écartée).** Garder la liste et expliquer le refus avant le choix. Conséquence : moins de code, l'utilisateur voit encore des types inutiles.
- **C (écartée, sauf si la Task 0 a le montre possible : alors retour vers ClaudeBox).** Permettre au forçage (ou à une projection corrigée) de les faire aboutir. Conséquence : seulement si Task 0 a le montre possible ; risque d'entités sans état fiable dans HA.

**Q8 — P3 de 20-3 (bandeau, assertion de faux DOM).**
- **A (retenue).** Les inclure : correctifs minimes, même fichiers que cette story.
- **B (écartée).** Les reporter encore. Conséquence : un bandeau périmé après un échec de « Republier » subsiste.

**QD — Découpage (tranchée : une seule story).** Une seule story 22.2 (même écran, même gate). Si elle devient trop grosse : 22.2 (compteurs + CC-51 + P3) puis 22.3 (CC-55, CC-58, CC-60, qui sont trois sujets distincts). Ne pas fusionner 22.1 avec 22.2 (démon seul vs interface, preuves différentes).

## Ordre retenu entre 22.1 et 22.2

22.1 d'abord : elle change ce qui est publié (noms) et décide si « recréer » est le moyen d'appliquer pièce et noms (Q6 de 22.1), ce dont dépend le libellé de CC-55 ; 22.2 ne change que l'écran et gagne à décrire un parc dont les noms sont stables.

## Vérifications non faites par cette session

Équivalence exacte des actions d'équipement et d'entité (C6) ; cause du refus `ha_missing_state_topic` sur 2971 et faisabilité d'un forçage `sensor`/`binary_sensor` (C9 à établir) ; valeurs réelles des compteurs sur la box ; comportement de HA à la suppression d'une découverte (perte du registre d'entité, hypothèse à confirmer pour Q5 B).

## Journal des décisions

- 2026-10-11 15:48 — Alexandre : story « compteurs » regroupée avec CC-51 ; « publiés » = `published_in_ha`, plus « en attente d'application » et « non pris en charge ».
- 2026-10-11 17:35 — Alexandre : captures de la documentation après cette story.
- 2026-10-12 — Cadrage documentaire (cette session) : story en `draft`, décisions Q1 à Q8 attendues.
- 2026-10-12 — R1 (ClaudeBox) : C9 reformulé, conséquence de H6 ajoutée à Q5 B.
- 2026-10-12, vers 05:50 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q1 A, Q2 A, Q3 A, Q4 B, Q5 A, Q6 C, Q7 A (sous réserve de la Task 0 a : retour vers ClaudeBox si un forçage ou une projection corrigée débloque ces types), Q8 A, QD une seule story. **`ready-for-dev` accordé** par ClaudeBox au nom de cette décision ; AC figés, options écartées retirées des AC et tâches ; ordre : après 22-1.

## Dev Agent Record

(à remplir par `dev-story`)

### File List

- `_bmad-output/implementation-artifacts/22-2-compteurs-et-lisibilite-de-la-surface-cc51-cc55-cc58-cc60.md` (nouveau)
