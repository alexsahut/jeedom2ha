# Story 16-8 — validation UX du 05/10/2026

Validation UX confiée par Alex à ClaudeBox le 05/10 à 08:54 : « fais la validation UX avec chrome, si OK, enchaîne sur la story 20.1 ».

Elle a été faite dans Chrome, en lecture seule. Gestes faits : ouverture de pièces, dépliage d'équipements, clic sur l'ancre « première commande bloquante ». Gestes exclus : aucun changement de type, aucun « Publier », aucun « Suppr. ».

Il y a eu deux passages : sur la box en `b17b7c3`, puis en `957aef4`. Les heures sont en heure locale (Paris), sauf mention `Z`.

## Premier passage (08:56 à 09:03, box en `b17b7c3`)

**Conforme :**
- AC1 à AC5 : section dédiée sur la page du plugin, cartes des pièces dans l'ordre Jeedom, modale par pièce, accordéon des équipements, synthèse visible sans déplier, diagnostic chargé à l'ouverture de la pièce.
- AC6 et AC7 : triptyque type natif / override / diagnostic, avec le « pourquoi » de chaque refus.
- AC9 et AC10 : synthèse par équipement, comptes, ancre vers la première commande bloquante.
- CC-37 : « Rafraichir » (5368) est rendue « non couverte ».
- Console de la page : aucune erreur. Seule une extension du navigateur en produit.
- **Les badges disent vrai.** Dans la pièce Garage, les équipements « Sera publié » ou « Partiellement publié » (131, 199, 277, 326, 553, 554, 579, 592, 639) sont exactement ceux qui ont des entités jeedom2ha au registre de Home Assistant.

**Défaut bloquant pour la validation, CC-38.** Un équipement exclu volontairement s'affichait comme bloquant : badge rouge « Ne sera pas publié… : N commande(s) bloquante(s) », cellules ⚠ et ancre. C'est le cas d'un plugin source, d'un équipement ou d'une pièce dans la liste d'exclusions, ou d'une exclusion manuelle de publication. Ces exclusions noyaient les vrais blocages :
- Garage : 6 des 7 badges rouges, dont Passerelle Enphase (eq 559, « 54 bloquantes ») ;
- pièce de vie : 10 des 12 badges rouges.

Le produit a pourtant un statut « Exclu » distinct (`resources/daemon/models/taxonomy.py`).

**Retouches, CC-39 :**
- le titre de la section s'affichait « onfiguration mapping… ». L'icône `fa-house-signal` n'existe pas dans Font Awesome 5 Free, la version de Jeedom ;
- en thème sombre, la ligne surlignée par l'ancre était illisible : texte clair sur fond jaune pâle.

**Constats non bloquants, reportés aux stories qui refont cet affichage :**
- les en-têtes de colonnes « GENERIC_TYPE » et « OVERRIDE HA » sont du jargon (20-3, libellés français d'usage) ;
- la surface coupe en deux le bloc « Gestion » du plugin : « Ajouter », « Configuration » et « Diagnostic » apparaissent sous la surface, loin de leur titre (20-1) ;
- le sélecteur de type reste actif sur une commande exclue ou non couverte, où il n'a aucun effet (20-1) ;
- « mapping ambigu — précisez les types génériques dans Jeedom » s'affiche aussi quand le type générique est renseigné (« Surplus Solaire », `ENERGY_STATE`). Le sort des commandes ambiguës est tranché en 20-2 (CC-35).

## Correctif

PR #201, fusionnée en `957aef4`. Codex n'a trouvé aucun problème majeur, la relecture indépendante est intégrée et la CI est verte.

**CC-38.** Une commande dont `publication_reason` vaut `excluded_eqlogic`, `excluded_plugin`, `excluded_object`, `publication_excluded_eqlogic` ou `publication_excluded_command` :
- prend un état « exclu », gris, avec l'icône `fa-eye-slash` ;
- n'est jamais comptée prête ni bloquante ;
- ne reçoit jamais l'ancre.

Un équipement sans commande prête ni bloquante, avec au moins une exclusion, affiche « Exclu : ne sera pas publié dans Home Assistant. ». Le flux d'édition ne change pas.

**CC-39.** L'icône `fa-home` remplace `fa-house-signal`, dans le titre de la section et dans celui de la modale. Le texte de la ligne surlignée passe en sombre.

Les parcours du gate 20.0 connaissent l'état « exclu ». Le parcours de découverte relève en plus l'état du badge de chaque équipement du Garage.

## Déploiement et preuve (09:36 à 09:52, box en `957aef4`)

Le déploiement standard (`--restart-daemon`) a eu lieu à 07:36:38Z. Seuls les 4 fichiers de l'interface changent. Le premier essai de dry-run avait été refusé par le garde-fou CI du script : la CI de `main` n'était pas encore terminée.

Relevés avant et après :
- parité : aucune décision ni écouteur modifié ;
- inventaire MQTT de 352 à 353 topics. L'ajout est le bouton du scénario 39, republié au sync de démarrage. Son entité Home Assistant existe depuis le 18/06, et le registre des entités n'a pas été modifié ;
- démons des autres plugins et cœur inchangés ;
- aucune nouvelle erreur ; 227 écouteurs ;
- `ha_overrides.json` inchangé ;
- fichiers servis identiques au worktree.

Home Assistant, en lecture seule : 354 entités jeedom2ha et registres non modifiés. Le relevé `core.restore_state` de 09:45:11 a les mêmes décomptes, plus un bouton `unknown`, celui du scénario 39.

**Second passage dans Chrome (09:41 à 09:43) :**
- Garage :
  - les 6 équipements exclus (183, 228, 338, 341, 329, 559) ont un badge gris « Exclu » et des cellules « exclu de Jeedom2HA (plugin source dans la liste d'exclusions) », sans ancre ;
  - les ancres ne restent que sur Enphase (579, partiel) et CHACON (287, 2 commandes ambiguës) ;
- pièce de vie : 10 exclus, 2 vrais blocages (45 commandes « types génériques non configurés dans Jeedom »), 9 publiés ;
- le titre s'affiche correctement, et la ligne surlignée est lisible.

**Gate 20.0, code de `main` :**

| Fin (UTC) | Parcours | Verdict | Constat |
|---|---|---|---|
| 07:44:55Z | découverte Garage puis Enphase, lecture seule | PASS | 5368 `non-couverte`, 5369 `bloquante`. Badges : 183, 228, 338, 341, 329 et 559 `exclu` ; 579 `partiel` ; 287 `bloque` ; les 8 autres `publie`. Console 0, aucune écriture. |
| 07:51:32Z | référence (bascule) | PASS | Cible 5369 : bloquante, puis prête (« Sera publié dans Home Assistant : 5 commande(s) prête(s). »), puis bloquante ; synthèse restaurée. Écritures simulées seulement. |

L'outil d'exécution de clawcode, avec le modèle OpenAI, a rendu la main avant la fin de la première exécution. Le processus a continué et a écrit son rapport à 07:44:55Z. clawcode l'a constaté et n'a pas relancé. La seconde exécution est passée par l'autre modèle.

## Verdict

**16-8 est validée UX et passe `done`.** Les constats non bloquants ci-dessus sont repris par 20-1, 20-2 et 20-3.
