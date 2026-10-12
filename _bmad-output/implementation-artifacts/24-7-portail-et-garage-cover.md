# Story 24.7 : Portail et garage : `cover`

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft` jusqu'à son `create-story`, après la baseline.** Rédigé par une session cloud déléguée, documentaire. **Change la production** (des entités `button` ou `binary_sensor` deviennent un `cover`). Ne rouvre pas `PRODUCT_SCOPE` (`cover` y est déjà). Décision attendue d'Alexandre : **Q10** (remplacement d'entités existantes, option C pour un `cover` optimiste) de `sprint-change-proposal-2026-10-12-parite-homekit.md`. Relecture de ClaudeBox obligatoire. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
>
> **R1 (ClaudeBox, 12/10) intégrée** : types génériques des deux équipements concernés établis (section suivante) ; le cas du garage est la vérification de l'AC2.

## Story

En tant qu'utilisateur dont un portail et un garage sont exposés à HomeKit,
je veux les retrouver dans Home Assistant comme des ouvrants (ouvrir, fermer, état), et non comme de simples boutons,
afin de les consulter et de les piloter par Assist.

**Parcours : démon (mapper, commande, état).**

## Dépendances et décisions

- Dépend de **24.4**. Une seule story de type en cours à la fois.
- **Dépend de 23.3 pour l'état d'un `cover`** : cette story ajoute `BARRIER_STATE` / `GARAGE_STATE` comme clé de relecture du `cover` ; elle ne réimplémente pas le streaming et ne touche pas aux lignes `light`/`cover` de `sync/state.py`. Q10 C (livrer un `cover` optimiste pour ne pas attendre) est **écartée** par Alexandre : la story démarre après la fusion de 23.3 (règle de 23.3 : `optimistic: false` seulement avec un état réel).
- **Q10 A** (tranchée) : remplacement, inventaire des références.

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q10 A** : remplacement, une seule voie par équipement ; inventaire des références avant/après. **L'option C (`cover` optimiste pour ne pas attendre 23.3) est écartée** : cette story **attend 23.3** pour l'état d'un `cover`.
- **Q9 A** : sans effet ici (le portail et le garage ne sont pas dans l'epic 18).

## Établi par ClaudeBox le 12/10 (mesure du 10/10, types génériques par équipement)

- **Portail** : `GB_OPEN`, `GB_CLOSE`, `GB_TOGGLE`, `BARRIER_STATE`. Ouvrir et fermer existent : branche directe de l'AC1, bascule inutile.
- **Garage** : `GB_TOGGLE`, `GARAGE_STATE`. **Bascule seule + état** : c'est exactement le cas que l'AC2 doit trancher (un `cover` n'est publié que si la bascule est pilotée par un état binaire fiable). Ni `GB_OPEN` ni `GB_CLOSE`.
- Reste à établir (ClaudeBox, Task 0) : la polarité de `BARRIER_STATE` et `GARAGE_STATE`, et le chemin actuel de chacun (`binary_sensor` ou `button`).

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | `CoverMapper` ne reconnaît que les types `FLAP_*`. Aucun `GB_*` n'apparaît dans le code du démon. | `mapping/cover.py:30-34` |
| F2 | Les types du core pour ce cas : `GB_OPEN`, `GB_CLOSE`, `GB_TOGGLE` (actions), `BARRIER_STATE`, `GARAGE_STATE` (infos binaires). | `ha-projection-reference.md:532-540` |
| F3 | `BARRIER_STATE` et `GARAGE_STATE` donnent aujourd'hui un `binary_sensor` de classe `garage_door` ; une action `other` typée donne un `button`. Le chemin réel de chaque équipement mesuré dépend de ses commandes (D5). | `mapping/binary_sensor.py:41-42` ; `mapping/button.py:12-35` |
| F4 | Ordre de la chaîne : `CoverMapper` passe avant `BinarySensorMapper` et `ButtonMapper` : un `cover` reconnu consommerait les commandes sans doublon. | `mapping/registry.py:24-35` |
| F5 | `_NON_COVER_KEYWORDS` et `_NON_SWITCH_KEYWORDS` filtrent par mots du nom d'équipement (dont « portail » et « garage » côté switch) : heuristique fragile à ne pas étendre. | `mapping/cover.py:56-62` ; `mapping/switch.py:67-73` |
| F6 | Le `cover` actuel traduit `OPEN`/`CLOSE`/`STOP` vers `FLAP_UP`/`FLAP_DOWN`/`FLAP_STOP` ; `GB_*` n'y est pas. | `sync/command.py:283-330` |
| F7 | Le `cover` est optimiste aujourd'hui ; son état réel relève de 23.3. | `sync/state.py:33-48` ; `sync/command.py:403-430` |

## Critères d'acceptation proposés (figés sur Q10 A)

- **AC1.** Un équipement qui porte `GB_OPEN` et `GB_CLOSE` (ou `GB_TOGGLE`) est projeté en `cover` de classe portail ou garage (valeurs exactes lues dans la documentation de HA, D4), avec ses commandes d'ouverture et de fermeture traduites par `sync/command.py`.
- **AC1 bis.** Cas de référence : le portail (`GB_OPEN`, `GB_CLOSE`, `GB_TOGGLE`, `BARRIER_STATE`) donne un `cover` avec ordres d'ouverture et de fermeture directs, `GB_TOGGLE` non utilisé pour l'ouverture ; le garage (`GB_TOGGLE`, `GARAGE_STATE`) donne un `cover` dont l'ordre d'ouverture envoie la bascule **seulement si** l'état dit fermé, et inversement, jamais en aveugle.
- **AC2.** **Aucun état menteur.** Un `cover` n'est publié que s'il a soit `GB_OPEN` et `GB_CLOSE`, soit `GB_TOGGLE` **et** une information d'état binaire fiable (`BARRIER_STATE` / `GARAGE_STATE`) permettant de ne basculer que dans le bon sens. Sinon, l'équipement garde son comportement actuel avec une raison canonique explicite (impossibilité technique), jamais un `cover` à deux sens inventés.
- **AC3.** `BARRIER_STATE` / `GARAGE_STATE` consommés par le `cover` ne sont plus publiés en `binary_sensor` doublon ; les autres commandes de l'équipement gardent leur mapping.
- **AC4.** Le payload porte `default_entity_id = cover.<object_id>` (22-1) ; `unique_id` et `object_id` suivent les conventions.
- **AC5.** État : relecture par la mécanique de 23.3 (une entrée de relecture) ; la limite est écrite dans « Limites » (puce propre).
- **AC6.** Cycle de vie (Q10 A) : le passage `button`/`binary_sensor` → `cover` dépublie les anciennes entités et publie la nouvelle ; inventaire avant/après des identifiants concernés, `entity_id` anciens et nouveaux, références relevées par ClaudeBox.
- **AC7.** Aucun `FLAP_*` existant ne change : volets et stores strictement non régressés (golden, tests du `CoverMapper`, essai de mouvement sur un volet).
- **AC8.** Un override pe-epic-16 peut rediriger le portail vers `button` et inversement.
- **AC9.** `PRODUCT_SCOPE` inchangé ; golden et contrat 4D verts ; aucun nom réel dans le dépôt (CC-48) ; preuve terrain par ClaudeBox (export avant/après, ouverture et fermeture d'un équipement de test, jamais d'un vrai portail sans présence).

## Tâches proposées

- [ ] **Task 0 — Gel du référentiel** : matrice `GB_*` / `BARRIER_STATE` / `GARAGE_STATE` → `cover` (classes de HA 2026.9.4, charge utile d'ordre, topic d'état) ; liste, par ClaudeBox, des équipements concernés, de leurs commandes réelles et de leur chemin actuel (`binary_sensor` ou `button`).
- [ ] **Task 1 — Mapper** : étendre `CoverMapper` ou créer un mapper de portail partageant `CoverCapabilities` (choix au `create-story`).
- [ ] **Task 2 — Commande** : traduction des ordres, logique de bascule fondée sur l'état (AC2).
- [ ] **Task 3 — Publication** : classe d'appareil, `default_entity_id`.
- [ ] **Task 4 — État** : après 23.3 (une entrée).
- [ ] **Task 5 — Tests** : portail avec ouvrir/fermer, avec bascule + état, avec bascule seule (refus), non-régression des volets.
- [ ] **Task 6 — Gate, déploiement, preuve terrain (humain)** ; **Task 7 — documentation**.

## Garde-fous

- Un portail est un organe de sécurité : aucun essai sur un vrai portail sans présence de l'humain ; la preuve terrain se fait sur un équipement de test.
- Pas de nouvelle heuristique sur les noms d'équipement.
- Ne pas modifier le streaming des `light`/`cover` (23.3).
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Le chemin actuel de chaque équipement mesuré (D5) ; les classes d'appareil acceptées par HA 2026.9.4 ; la polarité de `BARRIER_STATE` / `GARAGE_STATE` (1 = ouvert ou fermé) ; la proportion d'équipements à bascule seule.

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q10 A (remplacement) ; option C écartée : la story attend 23.3.
