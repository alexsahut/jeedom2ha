# Story 20-2 — preuve terrain et validation UX du 06/10/2026 (complément)

> **Statut de ce document.** Rédigé par ClaudeBox le 06/10/2026 et versé au dépôt le 11/10/2026. La clôture formelle de 20-2 est celle du 08/10 (`20-2-preuve-terrain-2026-10-08.md` : redéploiement de `79127a5`, parcours réel sur l'eq 287, dérogation d'Alex sur le témoin `getBridgeStatus`, validation UX). Ce complément consigne ce qui n'y figure pas : les deux déploiements du 06/10, les échecs puis le PASS du parcours de gate d'exclusion (PR #214, #216, #217), le forçage réel de l'eq 463 (GO d'Alex du 06/10 à 11:59, gardé par sa décision du 06/10 vers 15:09) et la réserve sur la commande 5369 (CC-47).

Preuve terrain de la story 20-2 (PR #210, fusion `d2bf697`) et de ses correctifs de validation UX (PR #215, fusion `d3cf8f6`), puis validation UX, faites le 06/10/2026.

Cadre :
- go d'Alex du 06/10 à 09:48 (« go déploiement 20-2 »), donné pour le déploiement, le gate, la preuve au clic réel et la validation UX ;
- go d'Alex du 06/10 à 11:59 (« go redéploiement 20-2 » et « oui tu peux forcer eq 463 »), donné après l'aperçu du forçage de l'eq 463 ;
- règle 2 d'Alex (28/09) et règle d'autonomie du 30/09 : plugin et HA seulement, déploiement standard, relevés avant et après.

Exécution par clawcode, relecture de chaque étape par ClaudeBox ; clics réels et passage Chrome par ClaudeBox. Heures en heure locale (Paris), sauf mention `Z`.

## Déploiements

| Élément | Premier déploiement | Second déploiement |
|---|---|---|
| SHA déployé | `d2bf697754d7a1ed331ee0d7487e45f05343914b` : fusion de la PR #210 | `d3cf8f648778891b66e01d52773d49b7372666b9` : fusion des PR #213 (documentation de 20-4) et #214 (parcours du gate, `tests/` seulement), puis de la PR #215 (correctifs de la validation UX) |
| CI de `main` sur ce SHA | verte : 10 succès, 1 `skipped` | verte : tous les check-runs en succès, `Burn-In` en `skipped` |
| SHA précédent sur la box | `80f7a05` (déployé le 06/10 à 06:06:12Z) | `d2bf697` |
| Fichiers livrés qui changent | `core/ajax/jeedom2ha.ajax.php`, `desktop/js/jeedom2ha_mapping_override.js`, `desktop/js/jeedom2ha_mapping_surface.js`, `resources/daemon/mapping/{cover,light,overrides,switch}.py`, `resources/daemon/models/{decide_publication,evaluate_equipment}.py`, `resources/daemon/transport/http_server.py` | `desktop/js/jeedom2ha_mapping_override.js`, `desktop/js/jeedom2ha_mapping_surface.js`, `resources/daemon/transport/http_server.py` |
| Déploiement | standard (`--restart-daemon`), worktree neuf détaché, à 09:19:22Z ; dry-run préalable sans erreur | standard (`--restart-daemon`), worktree neuf détaché, à 11:45:39Z ; dry-run préalable sans erreur |
| Archive de retour arrière | `jeedom2ha-20261006T091921Z-QTdJl6.tar.gz` (non utilisée) | `jeedom2ha-20261006T114539Z-RWb5TK.tar.gz` (non utilisée) |
| Tag | `deploy-d2bf697754d7a1ed331ee0d7487e45f05343914b-20261006T091931Z` | `deploy-d3cf8f648778891b66e01d52773d49b7372666b9-20261006T114549Z` |

## Relevés avant et après chaque déploiement

Les deux déploiements donnent les mêmes constats :
- VERSION après : le SHA déployé, `git_status=clean`.
- Healthcheck : MQTT connecté. Sync du déploiement : 292 équipements, 96 éligibles, 262 publiés.
- Inventaire MQTT : 353 entités avant et après, aucun topic ajouté ni retiré. Les topics des scénarios 72 et 2 (CC-44) n'apparaissent pas dans ces diffs.
- Relevé de parité : diff vide (`is_empty_diff: true`, aucune décision changée, 353 topics avant et après, aucun écouteur ajouté ni retiré). C'est l'effet attendu de 20-2 sans override (AC4).
- Box, `ps -eo pid,user,lstart,comm` : seul le démon jeedom2ha change (PID 444052 remplacé par 817341, lancé à 11:19:23 ; puis 817341 remplacé par 1105126, lancé à 13:45:40). Les autres écarts sont transitoires : threads noyau, sessions SSH, cron, processus web du script.
- Journal du plugin : 0 nouvelle ligne `ERROR` (le total reste à 3016) ; `[STATE-LISTENER] 227 listener(s)` après chaque redémarrage.
- Journal du démon : 0 `ERROR`.
- Les fichiers servis ont le sha256 du worktree (10, puis 3).
- `ha_overrides.json` : sha256 inchangé (`083ab5bf88ace22f18376d2c259e66dc87940d8c1b930c1dbd87b9d29621488d`) aux deux déploiements.
- Home Assistant : registre inchangé après le premier déploiement.

Le relevé de parité pris juste avant le second déploiement (11:44:46Z) est identique à celui d'après le premier (09:19:46Z), à l'horodatage près : la preuve au clic réel de l'exclusion (ci-dessous) n'a rien laissé sur la box.

## Gate 20-0

| Fin | Parcours | Code | Verdict | Constat |
|---|---|---|---|---|
| 11:24:19 | découverte, lecture seule | `d2bf697` | PASS | 5 critères PASS, témoin et sonde sans différence, console 0. |
| 11:26:34 | référence (bascule) | `d2bf697` | PASS | Écritures simulées seulement (`saveMappingOverride`, `revertMappingOverride`, verdict `simulee`) ; témoin et sonde sans différence. |
| 11:29:07 | exclusion d'un équipement non publié | `d2bf697` | FAIL non concluant | Défaut du parcours : la modale de pièce était fermée par Échap avant d'avoir le focus (reproduit dans Chrome), d'où un `waitFor` en échec ; critères box et journaux en FAIL : l'exécution chevauchait la troncature horaire du journal du démon (xx:27-28). Aucune écriture d'override, simulée ou transmise. Correctif : PR #214. |
| 11:31:22 | rescan de la page principale | `d2bf697` | PASS | `scanTopology` simulé (`rescan-declare`), jamais transmis. |
| 11:33:30 | contrôle négatif | `d2bf697` | FAIL attendu | `saveMappingOverride` non déclaré bloqué (`block-fail`) ; témoin et sonde sans différence. |
| 13:52:22 | exclusion d'un équipement non publié | `d3cf8f6` | FAIL non concluant | Défaut du parcours : `locator.click` en échec, sans clic « Exclure » abouti ; cause alors attribuée à la fermeture des modales (bouton de fermeture hors de la zone visible, constaté dans Chrome), puis localisée par les étapes nommées (voir 14:24:16). 5 critères PASS, aucune écriture d'override, simulée ou transmise. Correctif : PR #216 (pièce de l'eq 287 ouverte directement, fermeture sans clic par coordonnées, étapes nommées). |
| vers 13:56 | découverte, lecture seule | `d3cf8f6` | PASS | 5 critères PASS, témoin et sonde sans différence, console 0. |
| vers 13:58 | référence (bascule) | `d3cf8f6` | PASS | Écritures simulées seulement ; témoin et sonde sans différence. |
| 14:24:16 | exclusion d'un équipement non publié | `bd26c31` | FAIL non concluant | Défaut du parcours, désormais localisé par les étapes nommées : pièce ouverte et équipement déplié, puis `click` en échec à l'étape `exclure`. La modale Bootbox de Jeedom (Bootbox 5.5.2, Bootstrap 3.4.1) reste `aria-hidden="true"` une fois ouverte, ce que ClaudeBox a constaté dans Chrome ; or `getByRole` de Playwright ignore par défaut ce qui s'y trouve. 5 critères PASS, aucune écriture d'override, simulée ou transmise. Correctif : PR #217. L'échec de 13:52 (même message, sans étapes nommées) a vraisemblablement la même cause. |
| 14:46:51 | exclusion d'un équipement non publié | `63e24e6` | PASS | Après la PR #217 : étapes nommées 1 et 5 à 12 (ouverture de la pièce, dépliage, « Exclure », écriture puis relecture au journal, état des boutons, « Revenir au mode automatique », retrait au journal, état final) ; `savePublicationOverride` puis `revertPublicationOverride` simulées (`ecriture-override-declaree`, 12:45:17Z), jamais transmises ; aucune confirmation (équipement non publié) ; fenêtre du démon vide, 0 erreur ; témoin et sonde sans différence ; console 0. |

Entre `d3cf8f6` et `63e24e6`, seul le parcours `exclusion-publication-non-publiee.mjs` change (PR #216 et #217) : le code servi est celui de la box. Aucune exécution n'a transmis d'écriture à la box (`failures` vide, hors le contrôle négatif, où l'écriture est bloquée). La recherche générique de secrets ne trouve rien dans les journaux et les rapports des exécutions.

## Preuve au clic réel : exclusion puis retrait (ClaudeBox, Chrome, 11:43-11:47, box en `d2bf697`)

Sur l'eq 287, non publié, choisi en Task 0.4 :
- 11:43:27 : « Exclure » ; le démon enregistre l'exclusion d'équipement (`POST /action/publication_override` 200, « Override équipement sauvegardé : 287 ») ; la surface affiche le badge « pas encore appliqué dans Home Assistant » et le bouton « Appliquer ».
- 11:44:47 : « Appliquer » ; « Publier » pour le seul équipement (`intention=publier portee=equipement`, 0,006 s), écouteurs réalignés (227).
- 11:45:19 : « Revenir au mode automatique » ; le démon retire l'override (`Retour mode auto via UI eq_id=287 scope=equipment removed=True removed_commands=[]`).
- 11:45:42 : « Appliquer » (0,008 s), écouteurs réalignés (227).
- 11:46:58 : rescan correctif, parce que le témoin du bandeau (« Dernière opération ») avait changé : « Scan complet : 23 objets, 292 eqLogics, 120 scénarios », sync complet (96 éligibles, 196 non éligibles), 227 écouteurs.

Après : `ha_overrides.json` revenu au sha256 d'origine (`083ab5bf…`), aucune entité créée dans HA, journaux sans erreur, relevé de parité identique à celui d'après le déploiement (voir plus haut). Pose et retrait sont faits avant le second déploiement (F7).

## Forçage réel d'une entité ambiguë (ClaudeBox, Chrome, 14:02-14:03, box en `d3cf8f6`)

- Avant le GO, l'aperçu du forçage de l'eq 463 a été montré à Alex : type `light`, projection valide, commandes qui recevront les ordres (un état, un On, un Off) ; rien n'a été enregistré.
- GO d'Alex à 11:59 sur cette entité seulement.
- 14:02:22 : aperçu (`POST /system/overrides/preview` 200). 14:02:45 : « Forcer » ; le démon enregistre `463:4172` (`force_publish`). 14:03:07 : « Appliquer » ; « Publier » pour l'équipement : `[DISCOVERY] Publishing light config: topic=homeassistant/light/jeedom2ha_463/config eq_id=463 … confidence=ambiguous`, disponibilité `online` publiée, 227 écouteurs.
- `ha_overrides.json` ne contient que ce forçage. **Décision d'Alex du 06/10 vers 15:09 : le forçage est gardé** ; la lumière reste dans HA, pilotée par jeedom2ha.
- Relevé de parité de 12:48:31Z comparé à celui d'après le second déploiement (11:46:12Z) : seul l'eq 463 change (`non_publie`, `ambiguous_skipped` → `publie`, `publication_forced`, confiance d'origine `ambiguous` conservée ; commandes 4170, 4171 et 4172 retenues pour la `light` ; une entrée de périmètre explicite pour l'eq 463) ; un seul topic ajouté, `homeassistant/light/jeedom2ha_463/config` (353 → 354) ; écouteurs et topics d'état inchangés.
- Page principale : « Parc global » passe de 88 à 89 publiés et de 29 à 28 écarts ; « Dernière opération : Succès, 1 équipements mis à jour dans Home Assistant. ».

État dans Home Assistant (lecture seule, ClaudeBox) :
- registre : 355 entités jeedom2ha (354 au relevé de 20-4) ; `light.jeedom2ha_463` de retour au registre (entrée d'origine créée le 13/03, modifiée le 06/10 à 14:03:07), ni désactivée ni masquée ;
- `core.restore_state` de 14:15:11 : 342 entités jeedom2ha, 7 indisponibles, 114 `unknown` (341, 7 et 113 au relevé de 20-4) : seule la nouvelle lumière s'ajoute ;
- `light.jeedom2ha_463` : disponible, état `unknown` depuis 14:03:07. C'est l'état attendu d'une lumière : depuis la story 19-5 (CC-29), « Publier » n'envoie l'état initial que pour `sensor`, `binary_sensor` et `switch`, les seuls types dont l'état est synchronisé ; les lumières en sont hors. 12 des 17 lumières jeedom2ha sont dans le même état.

## Validation UX (Chrome)

Gestes faits : les clics réels décrits plus haut (exclusion puis retrait sur l'eq 287, forçage de l'eq 463 avec son GO), puis la lecture de la surface par pièce. Gestes exclus : aucune exclusion d'un équipement publié, aucun forçage hors de l'eq 463.

**Conforme :**
- AC1 : « Exclure », « Forcer » et « Revenir au mode automatique » sont dans l'en-tête de l'équipement et sur la première ligne de chaque entité, dont le libellé dit les commandes regroupées (eq 463 : « light — Commandes : » suivi de ses trois commandes). L'exclusion de l'eq 287 est enregistrée sur l'équipement, puis l'équipement est relu. La confirmation avant d'exclure une entité publiée n'a pas été provoquée sur la box : elle est couverte par les tests Node (harnais `node:vm`).
- AC2 : couvert par les tests Python (ordre de I4 amendé) ; sur la box, la parité ne change aucune décision aux deux déploiements.
- AC3 : aperçu du forçage de l'eq 463 montré avant le GO (type, validité, commandes qui recevront les ordres), puis forçage au clic réel et entité `light` publiée dans HA. Après coup, « Forcer » est grisé avec une info-bulle : « Déjà publiée : forcer n’a pas d’effet. » sur l'équipement, « Publication déjà forcée sur cette entité. » sur l'entité.
- AC4 : parité identique aux deux déploiements, sans override.
- AC5 : couvert par les tests Python (fusion champ par champ des deux overrides).
- AC6 : retrait au clic réel sur l'eq 287 (portée équipement, `removed=True`), puis équipement relu en mode automatique ; sur l'eq 463 forcé, « Revenir au mode automatique » est actif sur l'équipement et sur l'entité.
- AC7 : badge « pas encore appliqué dans Home Assistant » après la pose sur l'eq 287 ; « Appliquer » lance « Publier » pour ce seul équipement (`portee=equipement`), sur l'eq 287 comme sur l'eq 463 ; plus de badge sur l'eq 463 une fois appliqué.
- AC8 : non tenu à la première validation sur `d2bf697` (eq 588 à 591, exclus par le plugin et sans commande, affichés « Aucune commande projetable »), corrigé par la PR #215. Sur `d3cf8f6`, les eq 588 à 591 affichent « Exclu : ne sera pas publié dans Home Assistant. » ; sur l'eq 588, « Exclure » et « Forcer » sont grisés (« Équipement non éligible : l’action serait sans effet. ») et « Revenir au mode automatique » aussi (« Aucun override de publication à retirer. »).
- AC9 : une commande `name_heuristic_rejection` dit qu'« un mot du nom de l'équipement écarte ce type », sans demander de type générique ; la commande 5369 dit « Ne sera pas publié — état sans ordre On/Off ».
- AC10 : couvert par les tests Python et PHP ; sur la box, les routes de pose, de retrait et d'aperçu ont répondu 200 aux clics réels.
- AC11 : gate PASS sur `main` (découverte et référence sur `d3cf8f6`, exclusion sur `63e24e6`) ; preuve au clic réel sur l'eq 287 (pose, application, retrait, application), témoin du bandeau de santé lu à l'écran avant et après (« Dernière opération » ; aucune valeur `getBridgeStatus` consignée, d'où la dérogation accordée par Alex le 08/10), rescan correctif parce qu'il avait bougé, le tout avant le second déploiement ; forçage de l'eq 463 après aperçu et GO ; aucun équipement publié exclu ; story passée par `ready-for-UX-validation` avant `done`.

**Constats non bloquants, reportés :**
- **Commande 5369 non débloquée (CC-47, réserve décidée par Alex).** Voir le verdict : ni un type seul ni le forçage, dans l'état actuel, ne la publient ; elle reste en mode automatique, avec sa cause affichée.
- **Écouteur non trouvé (CC-45, antérieur à 20-2).** À l'« Appliquer » de 14:03:07, le journal `plugin` de Jeedom porte cinq erreurs « Listener non trouvé », dans la seconde du réalignement des écouteurs : des événements visaient vraisemblablement des écouteurs que le plugin venait de supprimer pour les recréer. La même erreur figure déjà le 02/07, le 29/09 et le 05/10. Sans effet sur la publication (227 écouteurs après le réalignement).
- **Avertissement répété dans le journal du démon.** Chaque lecture de l'eq 463 écrit `[OVERRIDES] Override 463:4172 sans 'ha_entity_type' exploitable — ignoré` : la lecture des overrides de type voit l'entrée de publication seule et l'écarte. Sans effet ; bruit à retirer.
- **Statut de diagnostic d'un équipement forcé (CC-46, antérieur à 20-2).** Le diagnostic du démon donne `status_code: not_supported` (« Non supporté ») à l'eq 463, pourtant publié. La table figée de la story 3.1 (`resources/daemon/models/taxonomy.py`) ne connaît pas `publication_forced` ni les raisons `publication_excluded_*` et retombe sur « Non supporté ». La surface par pièce n'est pas touchée (elle lit l'arbre) ; « Parc global » compte bien l'équipement comme publié. Seuls le diagnostic et ses consommateurs sont concernés : à traiter avec 20-3, qui retire la modale de diagnostic et redéfinit les compteurs.
- **Retours de l'interface (P3, pour 20-3).** Après « Appliquer », aucun message de succès, et le bandeau de santé n'est rafraîchi qu'au rechargement. L'aperçu du forçage s'ouvre sans titre. Un équipement forcé ne le dit que par l'info-bulle de « Forcer » grisé ; un équipement publié reste résumé « Sera publié dans Home Assistant ». Sur `d2bf697`, « Forcer » restait actif sur un équipement exclu par l'utilisateur, ce qui remplacerait l'exclusion par un forçage ; non revu depuis `d3cf8f6`.

## Verdict

**20-2 est prouvée et validée UX, et passe `done`, avec une réserve sur la commande 5369 (CC-47).** CC-26 est fermé : exclusion, forçage et retour au mode automatique se font depuis la surface, et le retrait d'une exclusion est prouvé au clic réel. CC-35 est fermé pour 16 des 17 commandes ambiguës : le forçage lève l'ambiguïté sous validation, prouvé sur la box pour l'eq 463 sur le GO d'Alex ; les autres équipements ambigus restent en mode automatique tant qu'Alex ne demande pas de les forcer. La commande 5369 (état sans ordre On/Off) n'est pas débloquée : aucun type valide n'a été relevé en Task 0.1, un type seul ne lève pas l'ambiguïté (F3 ; le parcours de référence n'en montre qu'une bascule simulée, le gate forçant la validité), et son forçage est grisé dans la surface (« Projection invalide pour ce type HA. » sur l'équipement, « Aucune commande clé propre à cette entité. » sur ses deux entités). **Décision d'Alex du 06/10 vers 15:09 : clore avec cette réserve** ; 5369 reste en mode automatique et sera traitée dans une story dédiée. Le forçage de l'eq 463 est gardé (même décision). Autres constats reportés : CC-45, CC-46 et les P3 d'interface ci-dessus.
