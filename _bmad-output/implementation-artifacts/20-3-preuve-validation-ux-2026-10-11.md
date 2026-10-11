# Story 20-3 — preuve terrain et validation UX (09/10 et 11/10/2026)

Preuve terrain de la story 20-3 : PR #225 (fusion `0226b87`), puis correctifs de revue R1 et R2 et retrait de « Ajouter » (PR #228, fusion `f10c447`). Validation UX d'Alex le 09/10 sur `0226b87` ; contrôle des correctifs par ClaudeBox le 11/10 sur `f10c447`.

Cadre :
- règle 2 d'Alex (28/09) et règle d'autonomie du 30/09 : plugin et HA seulement, déploiement standard, relevés avant et après ;
- décision d'Alex du 11/10 : le clic réel des actions déplacées (AC10) est fait, et c'est ClaudeBox qui clique ;
- règle de la revue Codex du 01/10 pour toute action réelle : équipement non publié, témoin `getBridgeStatus` relevé avant et après, sync correctif si le témoin a bougé, aucune écriture sur un équipement publié ;
- décision d'Alex du 11/10 vers 13:00 : retrait du bouton « Ajouter » (Q4 complétée).

Exécution par clawcode (déploiements, gates, relevés de parité) et par des sessions cloud déléguées (développement) ; relectures, passages Chrome et clics réels par ClaudeBox. Heures en heure locale (Paris), sauf mention `Z`. Équipements et pièces désignés par leur id.

## 1. Code de la PR #225 (`0226b87`)

### Déploiement (09/10)

| Élément | Valeur |
|---|---|
| SHA déployé | `0226b87` : fusion de la PR #225 (session cloud déléguée) |
| Déploiement | standard, `VERSION` = `0226b87`, déployé le 2026-10-09 à 08:15:43Z |
| Parité avant / après (10:15 / 10:16) | 355 topics avant et après, aucun topic ni écouteur ajouté ou retiré ; une décision changée, l'eq 408 (`disabled_eqlogic` → `no_supported_generic_type`, non publié avant et après) : équipement activé côté Jeedom entre les deux relevés, sans effet HA |

### Gate 20-0 (09/10)

| Fin | Parcours | Verdict | Constat |
|---|---|---|---|
| 10:20 | découverte étendue | PASS | 5 critères PASS ; synthèse et action « Diagnostic » absentes, export support présent ; 0 lecture de `getPublishedScopeForConsole` / `getDiagnostics` au chargement ; 0 chaîne interdite sur la page et dans la pièce ouverte ; « Sans pièce » présente (20 équipements), sans action de pièce ; compteurs relevés. |
| 11:20 | référence (bascule de la cmd 5369) | PASS | Écritures simulées seulement. |
| 11:22 | exclusion de 20-2 | PASS | Écritures simulées. |
| 11:24 | contrôle négatif | FAIL attendu | `saveMappingOverride` non déclaré bloqué (`block-fail`) ; box sans différence. |

### Passage Chrome de ClaudeBox (11/10 matin, lecture seule)

Page principale, pièce 25 (pièce de référence du gate), équipement désactivé de la pièce 25 (eq 514), « Sans pièce » :
- aucun `#div_scopeSummary`, aucune action « Diagnostic », aucun script `jeedom2ha_scope_summary.js` ni `jeedom2ha_diagnostic_helpers.js` ;
- aucune des chaînes interdites du gate (« mapping », « Template », « Mes templates », « Paramètre n°1 », « Paramètres spécifiques », « Écart », « Confiance », `eq_id`, `reason_code`, « Parc global », « Synthèse du périmètre », « Diagnostic de Couverture », « Parité FAN », `generic_type`) dans le texte de la page, de la pièce 25 et de « Sans pièce » ;
- eq 514 : « Désactivé dans Jeedom », toutes ses commandes à l'état désactivé, jamais comptées bloquantes.

### Compteurs comparés à un recomptage indépendant (11/10)

Recomptage par ClaudeBox des arbres lus en lecture seule (`getMappingOverrides`, équipement par équipement), comparé aux compteurs affichés ; mêmes valeurs que le gate du 09/10.

| Pièce | Équipements : publiés / exclus / désactivés / à corriger | Commandes : prêtes / bloquantes / non couvertes | Écart |
|---|---|---|---|
| pièce 25 | 9 / 7 / 1 / 2 | 93 / 3 / 101 | aucun |
| « Sans pièce » | 1 / 13 / 2 / 3 | 1 / 39 / 15 | aucun |

Lecture des écarts apparents :
- pièce 25 : les commandes des équipements exclus ou désactivés ne sont pas comptées « non couvertes ».
- « Sans pièce » : les eq 607, 609 et 611 (`no_generic_type_configured`) sont comptés « à corriger » et leurs commandes « bloquantes », comme le dit le libellé de leur ligne ; l'eq 586 (`no_commands`) n'entre dans aucun compteur d'équipement. La sémantique des compteurs sera revue dans une story dédiée (décision d'Alex du 11/10 : « publiés » = présents dans HA, « en attente d'application », « non pris en charge »).

### Actions déplacées au clic réel (11/10 matin, ClaudeBox)

Cibles non publiées seulement : l'eq 287 (sans topic) et la pièce 18 (6 équipements, tous exclus par plugin).

| Heure | Geste | Journal du démon |
|---|---|---|
| 12:00:02 | eq 287, « Supprimer puis recréer », confirmation | `supprimer`, portée `equipement`, volume 0 |
| 12:00:41 | pièce 18, « Republier la pièce », confirmation | `publier`, portée `piece`, volume 0 ; écouteurs réalignés (227) |
| 12:01:03 | pièce 18, « Supprimer puis recréer la pièce », confirmation | `supprimer`, portée `piece`, volume 0 |

Témoin et relevés : `getBridgeStatus` avant = sync du 09/10 à 12:47:22Z, puis bougé par les actions, d'où un rescan correctif au clic à 12:01:49 (96 éligibles, 196 non éligibles). Parité avant (09:58:40Z) et après le rescan (10:02:18Z) : diff vide, 355 topics. `ha_overrides.json` inchangé (seul override : le forçage gardé de l'eq 463). Démon inchangé (même PID), 0 nouvelle ligne `ERROR` (plugin 3016, démon 0), aucun nouveau « Listener non trouvé ». Home Assistant, en lecture seule : 355 entités jeedom2ha au registre, inchangé.

### Validation UX

- 09/10 vers 14:46, retour d'Alex sur l'eq 287 : « aucun compteur et des boutons me semblent redondants ». Conforme au contrat (les compteurs sont dans l'en-tête de la pièce) ; dette UX CC-51, à traiter avec la story des compteurs.
- 09/10 à 20:25 : validation UX d'Alex.

## 2. Relecture a posteriori et correctifs (PR #228, `f10c447`)

Relecture a posteriori de la PR #225 par ClaudeBox et par une relecture indépendante : aucun P1. Écarts corrigés par la PR #228 (session cloud déléguée, deux rondes) :
- R1 : republication par équipement toujours proposée (« Republier », ou « Appliquer » si un override est en attente) ; gating d'état des actions déplacées, par lecture de l'arbre ; bouton en cours non réactivé par le gating global, réservé pendant la confirmation ; retour d'une action de pièce lié à sa pièce, sinon dans la zone d'alerte ; compteurs en erreur si aucune lecture n'aboutit ; boutons destructifs en rouge ; tests sur le vrai code ; chaînes interdites du gate limitées aux libellés statiques ; `object_name` échappé dans la page ; « Ajouter » retiré (décision d'Alex).
- R2 : le gating de « Supprimer puis recréer » lisait la décision du seul principal comme « publié dans HA » (bouton grisé à tort pour un équipement dont seuls les secondaires sont publiés, ou en dépublication différée). Le démon expose désormais `sync_status.published_in_ha`, lu avec la même fonction que les actions (`_is_currently_published_in_ha`), en lecture seule. Corrigés aussi : message hors modale échappé, arbres en erreur non comptés comme lus, résultat d'échec de « Republier » affiché, zone exclue du gate resserrée.

Relectures de la PR #228 (ClaudeBox et relectures indépendantes, deux rondes) : fusionnable après R2. Tests : Node 413/413, démon 1446 réussis (1441 sur `main` avant, + 5 nouveaux), PHP 29/29, `flake8` 0 ; mutations du calcul de `published_in_ha` et du gating détectées. CI verte. Restent des P3 reportés à la story des compteurs : bandeau non rafraîchi après un échec de « Republier » ; une assertion liée au faux DOM des tests.

### Déploiement (11/10)

| Élément | Valeur |
|---|---|
| SHA déployé | `f10c4478b561f4ac74aa0c33e1d2cabaf58560c6` : fusion de la PR #228 (après #227, garde-fou CC-50, et #219, documentation) |
| Garde-fou CI | premier passage du garde-fou corrigé (CC-50) : il a refusé le déploiement tant que la CI de push tournait, puis l'a accepté une fois verte |
| Déploiement | standard (`--restart-daemon`), le 2026-10-11 à 14:20:30Z ; tag `deploy-f10c4478b561f4ac74aa0c33e1d2cabaf58560c6-20261011T142039Z` ; archive de retour arrière `jeedom2ha-20261011T142029Z-ggcRun.tar.gz` (non utilisée) |
| Sync du déploiement | 292 équipements, 96 éligibles, 263 publiés ; inventaire MQTT 355 → 355 |
| Parité avant / après | diff vide (292 décisions identiques, 355 topics, aucun écouteur ajouté ou retiré) |
| Box | démon PID 1147052 remplacé par 2701487 (16:20:31) ; 0 nouvelle ligne `ERROR` ; `ha_overrides.json` inchangé (`d80a54f5…`) |

### Gate 20-0 sur `f10c447` (11/10)

| Fin | Parcours | Verdict | Constat |
|---|---|---|---|
| 16:24 | découverte étendue | PASS | 5 critères PASS ; mêmes compteurs que le 09/10 (pièce 25 : 9/7/1/2 et 93/3/101, « Sans pièce » 1/13/2/3 et 1/39/15) ; 0 chaîne interdite ; « Sans pièce » sans action de pièce. |
| 16:26 | référence | PASS | Écritures simulées seulement. |
| 16:28 | exclusion de 20-2 | PASS | Écritures simulées seulement. |
| 16:30 | contrôle négatif | non concluant | Le journal du démon a été tronqué par la maintenance des journaux de Jeedom pendant le parcours (`bornes-journal-invalides`) ; relancé. |
| 16:34 | contrôle négatif, relance | FAIL attendu | `saveMappingOverride` non déclaré bloqué (`block-fail`) ; box et journaux sans différence. |

### Contrôle de ClaudeBox dans Chrome (11/10, 16:35-16:40, après la fin du gate)

Lecture :
- page principale : « Ajouter » absent ; « Configuration » et `eqLogicThumbnailContainer` présents ; 24 cartes de pièce, le nom libre marqué sur les 23 vraies pièces, pas sur « Sans pièce » ; aucun script de synthèse ni de diagnostic ; aucune chaîne interdite ;
- pièce 25 : compteurs inchangés ; « Republier la pièce » et « Supprimer puis recréer la pièce » (rouge) actifs (la pièce a des publiés) ;
- eq 199 (publié) : « Republier » et « Supprimer puis recréer » actifs ; eq 579 (partiellement publié) : les deux actifs ;
- eq 287 (non publié, bloqué) : « Republier » actif, « Supprimer puis recréer » grisé (« Équipement non publié dans Home Assistant : rien à supprimer. ») ;
- eq 514 (désactivé) : les deux grisés (« Équipement désactivé dans Jeedom : rien à republier. ») ;
- pièce 18 (6 exclus) : compteurs 0 / 6 / 0 / 0 et 0 / 0 / 0 ; les deux actions de pièce grisées (« Aucun équipement à publier dans cette pièce. », « Aucun équipement publié dans cette pièce. ») ;
- « Sans pièce » : titre sans nom libre, aucune action de pièce, message d'indisponibilité ; compteurs inchangés.

Clic réel (cible non publiée) :

| Heure | Geste | Résultat |
|---|---|---|
| 16:37:00 | eq 287, « Republier » (pas de confirmation, comme « Appliquer ») | démon : `publier`, portée `equipement`, volume 0, succès ; message « … — Configuration déjà à jour dans Home Assistant. » dans la pièce |
| 16:38:30 | rescan correctif au clic (« Rescanner la topologie Jeedom », confirmation) | sync terminé, 96 éligibles ; bandeau « Succès », dernière synchro 16:38:30 |

Témoin `getBridgeStatus` : avant = sync du déploiement (14:20:37Z) ; bougé par le clic (`publier`, 14:37:00Z) ; après le rescan = sync 14:38:30Z.

Relevés après les clics :
- parité comparée à celle d'après le déploiement : diff vide (292 décisions, 355 topics, aucun écouteur ajouté ou retiré) ;
- box : même démon (PID 2701487), 0 ligne `ERROR` (plugin 3016, démon 0), aucun nouveau « Listener non trouvé », `ha_overrides.json` inchangé ;
- Home Assistant, en lecture seule : 355 entités jeedom2ha au registre ; dernière modification le 10/10, dernière création le 27/09 : le déploiement et les clics n'y ont rien changé.

## 3. Constats reportés

- **Sémantique des compteurs et surface d'un équipement à une seule entité** (CC-51) : story dédiée, décision d'Alex du 11/10.
- **P3 de la relecture de la PR #228** : bandeau non rafraîchi après un échec de « Republier » ; une assertion de test liée au faux DOM.
- **Journal du démon tronqué par la maintenance de Jeedom** : il peut rendre un parcours du gate non concluant ; le journal du démon est verbeux (accès HTTP locaux en `INFO`).
- **`published_scope`** (export de diagnostic) calcule « publié » sans les secondaires : peut diverger de `published_in_ha` pour un équipement dont seuls les secondaires sont publiés.

## Verdict

**20-3 est prouvée et passe `done`.** AC1 à AC10 tenus : gate vert sur `main` (`0226b87`, puis `f10c447`), compteurs égaux au recomptage, actions déplacées prouvées au clic réel sans effet, déploiements sans écart, passage Chrome consigné, validation UX d'Alex (09/10) puis contrôle des correctifs par ClaudeBox (11/10). Le volet UI de CC-04 est fermé : plus de synthèse « Parc global », plus de modale de diagnostic, plus de gabarit Jeedom ni de jargon d'infrastructure à l'écran.
