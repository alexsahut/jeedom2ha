# Story 24-2 — preuve de terrain et baseline « avant » (2026-10-20)

> **Statut de ce document.** Rédigé par ClaudeBox le 20/10/2026 vers 04:20 (Task 5, AC11, AC11 bis).
> - Identifiants seulement (CC-48).
> - Déploiement et parcours du gate : clawcode (`reports/24-2-2026-10-20/run-ff2f/` sur la VM). Lecture de l'export : ClaudeBox, par l'action AJAX `getDecisionExport` appelée depuis la page du plugin (lecture seule, sans téléchargement). Cache de Homebridge : clawcode, compte en lecture seule.
> - Seul le déploiement a écrit sur la box. **Aucune manipulation du secret local.**

## Ce qui est déployé

| Élément | Valeur |
|---|---|
| SHA | **`ff2fe0dedbea123de66ab7f9f5ab709a1e6e5097`** (`main` après #320), déployé le 20/10 vers 04:00 par `./scripts/deploy-to-box.sh --sha <complet> --restart-daemon`, CI de `main` attendue |
| Démon | **0 ligne `ERROR`** après redémarrage |

## Gate 20-0

| Parcours | Verdict |
|---|---|
| `page-principale-b` (menu « ⋯ » à 3 entrées, dont l'export) | **PASS** |
| `controle-ecriture-non-declaree` | **FAIL attendu** (`ecriture-override-non-declaree`) |
| `vue-maitre-detail-c` | **PASS** |

## Publication inchangée (AC11)

Inventaire MQTT `parity-snapshot` avant le déploiement et après les parcours : **348 topics des deux côtés, diff vide**. L'export ne change rien à ce qui est publié.

## Baseline « avant » (lecture du 20/10, 04:11 UTC+2)

| Mesure | Valeur |
|---|---|
| `schema_version` | 1 |
| Temps de réponse de l'action AJAX (navigateur) | 225 ms |
| Taille du document (JSON compact) | 1 032 464 octets |
| `totals` | 292 équipements, 3 422 commandes, 120 scénarios — cohérent avec le sync (292 équipements lus par la page) |
| Décisions équipements | 90 `published`, 2 `partial`, 200 `not_published` (étapes : 196 en 1, 6 en 2, 90 en 4) |
| Décisions scénarios | 84 `published`, 36 `not_published` |
| `config` | 6 plugins exclus, 8 pièces exclues (identiques à la configuration) |
| Noms dans le document | aucun champ `name` (CC-48) |

**Équipements exposés à HomeKit (`homekit_exposed=true`) : 119** (97 réglés sur l'équipement, 22 par le défaut de Homebridge), et 5 scénarios.
- Publiés dans HA : 69 ; partiel : 1 ; non publiés : 49.
- Causes des 49 non publiés : 41 plugin exclu (dont 20 deconz et 18 xiaomihome, que HA atteint par ses propres intégrations, décision du 01/10), 5 pièce exclue, 3 exclusion individuelle, 1 ambigu.

C'est le point de départ chiffré de la parité HomeKit pour 24.3 à 24.5.

## AC11 bis — comparaison au cache de Homebridge

Cache `cachedAccessories` figé depuis le 20/09 (Homebridge non relancé depuis) : 118 équipements et 5 scénarios.

| Écart | Identifiants | Lecture ClaudeBox (export) |
|---|---|---|
| Scénarios | aucun | parité totale (20, 38, 50, 57, 150) |
| Dans le cache, absents de l'export | 349 | `homekit_exposed=false`, source `piece` : la pièce n'est plus exposée ; cache antérieur au changement |
| | 9994624156, 9994624159 | identifiants synthétiques de sous-nœuds Z-Wave du cache, pas des `eq_id` Jeedom |
| Dans l'export, absents du cache | 462, 639 | équipements actifs, exposés depuis le 20/09 (cache périmé) |
| | **165, 550** | **équipements désactivés dans Jeedom** que l'export marque `homekit_exposed=true` |

**Constat pour la suite (24.3/24.4)** : `homekit_exposed` reflète le réglage d'exposition, pas l'exposition effective. Homebridge n'expose pas un équipement désactivé. La comparaison de parité devra soit croiser `homekit_exposed` avec `enabled`, soit l'export ajouter un champ d'exposition effective. Le défaut n'empêche pas la baseline : les deux équipements sont non publiés des deux côtés.

## Bilan

Le bouton, la route et le fichier d'export sont en service sur la box ; la publication est inchangée ; la baseline « avant » est capturée et l'écart avec le cache de Homebridge est expliqué. 24-2 passe à `ready-for-UX-validation` (une entrée ajoutée au menu « ⋯ », validation avec la recette 25.5).
