# Story 25-2 — preuve de terrain (2026-10-19)

> **Statut de ce document.** Rédigé par ClaudeBox le 19/10/2026 vers 02:50 (Task 7, AC16), pendant l'autonomie de nuit déléguée par Alexandre. Il ne cite que des identifiants (règle CC-48). Toutes les vérifications ont été faites en lecture seule : registre des entités de HA, journal du démon, et un parcours du gate 20-0 qui appelle `getEquipmentStates`. **Aucune manipulation du secret local** : la route a été appelée par le relais PHP, depuis la page du plugin, avec la session du compte dédié au gate. Seul le déploiement a écrit sur la box, et c'est clawcode qui l'a fait.

## Ce qui est déployé

| Élément | Valeur |
|---|---|
| SHA déployé | `2b451dd5ffadefe9a1b48a69765eef7501942d81` (`main` après #288) |
| Commande | `./scripts/deploy-to-box.sh --sha <complet> --restart-daemon`, depuis un worktree neuf en HEAD détaché. Garde-fous CC-56 (SHA = HEAD) et CC-50 (CI verte) passés. |
| Démon | redémarré le 19/10 à 02:28 (heure de Paris), **0 ligne `ERROR`** à 02:50 |
| Sync | `total_eq=292 eligible=96 published=263` |
| Jeedom | 4.6.1 |

## Inventaire MQTT et registre de HA

- **Topics MQTT : 349 → 348.** Le bouton du scénario 129 est revenu, ceux des scénarios 147 et 40 ont disparu. Ces scénarios ont été réactivés ou désactivés côté Jeedom, et le démon applique 21-1 (CC-44), comme le 12/10 et le 18/10. Cela ne vient pas de 25.2, qui ne touche ni à la découverte ni à la publication (AC6).
- **Registre des entités de HA (02:47) :**
  - 348 entités jeedom2ha ;
  - aucune entité créée depuis le déploiement ;
  - une seule entité modifiée, le bouton du scénario 129, restauré depuis `deleted_entities` à 02:28:10. Aucun `entity_id` n'a changé.

## Mesure de la route sur le parc réel (AC16)

Parcours gate `mesure-equipment-states`, non versionné, lancé le 19/10 à 02:43 :
- verdict **PASS** ;
- interception, état de la box, console et journaux tous verts ;
- aucune écriture transmise, aucun marqueur d'écriture, 0 `ERROR`.

Le parcours fait 5 appels `getEquipmentStates`, de bout en bout depuis la page (navigateur → relais PHP → démon) :

| Appel | Cache | `build_ms` (démon) | Bout en bout | Réponse relais | Équipements | `unread` |
|---|---|---|---|---|---|---|
| 1 | hit (cache déjà construit à 02:41:58) | 171,8 | 290 ms | 1 242 700 o | 292 / 292 | 0 |
| 2 | hit | 171,8 | 269 ms | 1 242 700 o | 292 / 292 | 0 |
| 3 | hit | 171,8 | 322 ms | 1 242 700 o | 292 / 292 | 0 |
| 4 (`refresh=1`, reconstruction) | **miss**, génération 3 → 4 | **184,9** | **314 ms** | 1 242 701 o | 292 / 292 | 0 |
| 5 | hit | 184,9 | 136 ms | 1 242 700 o | 292 / 292 | 0 |

Journal du démon, lignes `[AGGREGATE]` (une par construction) :
- 02:41:58, `build_ms=178.0`, génération 2 ;
- 02:41:58, `build_ms=171.8`, génération 3 ;
- 02:44:04, `build_ms=184.9`, génération 4.

Chacune donne `equipments=292 unread=0 bytes=1342346`. Les deux premières constructions viennent d'une tentative précédente de lancement du parcours.

### Comparaison aux budgets de Q10

| Budget | Valeur mesurée | Verdict |
|---|---|---|
| Bout en bout à froid ≤ 6 s | **314 ms** (avec reconstruction) | tenu, avec un facteur 19 de marge |
| Bout en bout à chaud ≤ 500 ms | **136 à 322 ms** | tenu |
| Construction côté démon (synthétique : ≤ 4 000 ms projetés) | **172 à 185 ms** sur la box | tenu, bien sous la projection d'environ 1 016 ms |
| Taille de réponse ≤ 1 500 000 o | **1 342 346 o** côté démon, 1 242 700 o reçus | **tenu de justesse (89 %)** |

**Point d'attention pour 25.3 : la taille de réponse.** Le parc réel donne une réponse de 1,34 Mo, au lieu des 913 ko mesurés en synthétique. Le temps à chaud est dominé par le transfert et le décodage de cette charge, pas par le démon. Plusieurs pistes, à arbitrer en 25.3 :
- compresser la réponse (gzip au niveau du relais) ;
- alléger `diagnostic` dans la liste blanche, à condition que la parité de l'AC4 reste prouvée ;
- garder la réponse telle quelle et suivre la croissance du parc.

Le budget n'est pas relevé.

### Ce qui n'a pas été mesuré sur le terrain

L'AC16 demandait aussi un appel « après une écriture d'override » et un autre « après une synchro ». Le gate interdit toute écriture, et une synchro réelle n'a pas eu lieu pendant la fenêtre de mesure. On a seulement observé l'invalidation par synchro au déploiement : la génération repart, puis le cache est reconstruit au premier appel.

Le comportement après écriture et après synchro est prouvé par les tests de la PR #288 :
- invalidation des trois handlers d'override ;
- invalidation en fin de synchro et d'action ;
- test d'énumération des chemins d'écriture.

On le revérifiera par l'usage en 25.3, quand la page principale consommera la route.

## Bilan

La route est en place sur la box et rend les 292 équipements sans échec. Les budgets de temps sont largement tenus. Aucune publication HA n'est modifiée par 25.2. La réserve est consignée ci-dessus : mesures après écriture et après synchro non faites sur le terrain, taille de réponse à surveiller. **25-2 passe à `done`.**
