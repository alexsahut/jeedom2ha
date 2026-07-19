---
type: sprint-change-proposal
date: 2026-07-19
project: jeedom2ha
author: clawcode (Scrum Master — correct-course)
trigger_story: pe-epic-16 / 16.8 (walkthrough surface navigation) — eq 457 "chambre parents"
status: approved
approved_by: Alexandre SAHUT
approved_date: 2026-07-19
placement: pe-epic-11 / Story 11.4
mode: batch
---

# Sprint Change Proposal — Lumière + mesure de consommation → projection multi-entité

## Section 1 — Résumé du problème

**Déclencheur.** Pendant le walkthrough de la story 16.8 (surface de navigation pièce/équipement),
la lumière **actionnable** « chambre parents » (eq 457, box 192.168.1.21) remonte
`Ne sera pas publié` dans la colonne diagnostic. L'équipement porte simultanément des
commandes `LIGHT_ON/OFF/SLIDER/STATE` **et** `POWER/CONSUMPTION` sur le même eqLogic.

**Nature.** Limitation technique découverte en implémentation (faux positif du moteur), pas
un nouveau besoin ni un pivot. Le light mapper (`resources/daemon/mapping/light.py:47`) range
`POWER`, `CONSUMPTION`, `ENERGY_POWER` (et `ENERGY_STATE`) dans `_ANTI_LIGHT_GENERIC_TYPES`,
au même niveau que les vrais conflits (chauffage, volet, fumée). Conséquence : présence d'une
commande de mesure → `MappingResult(confidence="ambiguous", reason_code="conflicting_generic_types")`
(light.py:176-193) → **tout l'eqLogic est skippé**, y compris la lumière pilotable.

**Preuve.** Vérifié sur la box (eq 457) : classé `ambiguous_skipped` ; `command_topic manquant`
n'était que le symptôme aval (rien n'est projeté → pas de topic de commande). Le libellé
diagnostic a déjà été corrigé côté 16.8 (message #810) pour afficher la cause amont ; le présent
SCP traite la **cause moteur**.

**Attendu.** Un tel équipement doit publier **plusieurs entités HA sous un device commun** :
- 1 `light` (depuis les commandes `LIGHT_*`),
- 1..n `sensor` `power` (W) / `energy` (kWh) (depuis `POWER`/`CONSUMPTION`).

C'est le pattern canonique HA (**1 device → N entities**) : le schéma MQTT `light`/`switch` n'a
volontairement pas de champ conso ; les modules physiques (Shelly, Fibaro, Qubino, Zigbee2MQTT)
exposent la mesure comme entités `sensor` séparées, regroupées via `identifiers` (device commun).

## Section 2 — Analyse d'impact

### Impact Epic
- **Epic 2 (mapping candidat / lumières, Story 2.2)** — foyer du faux positif anti-light.
- **Epic 11 (multi-entité / multi-domaine, Stories 11.1/11.2/11.3)** — **livré/clos**. Le moteur
  sait déjà agréger `switch` (primaire) + `sensor power/energy` (secondaire) via
  `registry.py:_map_structural_multi_entity`, mais **uniquement quand le primaire est un switch**.
  Le cas « primaire = light » n'est pas couvert.
- **Aucun epic rendu obsolète, aucune re-séquencement.** Pas de nouvelle ouverture `PRODUCT_SCOPE`
  (le domaine `light` est déjà connu/validable). Ce n'est donc **pas** un incrément FR40/NFR10
  au sens pe-epic-18 (couverture de domaines manquants) : `light` et `sensor` existent déjà.

### Impact artefacts
- **PRD** — aucun conflit. Publier honnêtement plus d'entités réelles sert les objectifs
  (projection explicable, pas de skip silencieux). `[N/A]`
- **Architecture** (`architecture-projection-engine.md`) — `_map_structural_multi_entity` est
  documenté « switch(es), puis sensors, puis binary_sensors » ; à étendre pour mentionner le
  **primaire `light`**. Édition documentaire mineure. `[Action-needed]`
- **Epics** (`epics-projection-engine.md`) — ajouter la story corrective (famille multi-entité
  Epic 11) ; noter, sur Story 2.2, que les compagnons de mesure ne sont plus des conflits. `[Action-needed]`
- **UI/UX** — **effet de bord positif** : la cellule diagnostic 16.8 passera de
  « mapping ambigu » à « Sera publié : light » (+ capteurs). Aucune modif UI requise ; le fix
  d'affichage #810 reste comme filet pour les vrais ambigus. `[N/A]`
- **Tests** `[Action-needed]` :
  - `tests/unit/test_light_mapper.py` — nouveaux cas light+POWER/CONSUMPTION (non-ambigu).
  - `test_step2_mapping_failure.py` — vérifier que `conflicting_generic_types` reste émis pour
    les vrais conflits (chauffage/volet/…) et **plus** pour les compagnons de mesure.
  - `registry` multi-entité — cas primaire `light` + secondaires sensor ; non-régression switch.
  - **Golden corpus** (`expected_sync_snapshot.json`) — réalignement des eqLogic light+conso
    (dont eq 457) : de skippé → light + sensor(s).
  - Gate terrain box 192.168.1.21 (eq 457) : light + sensors W/kWh sous device commun.

### Impact technique
1. `light.py` — scinder `_ANTI_LIGHT_GENERIC_TYPES` : retirer `POWER`, `CONSUMPTION`,
   `ENERGY_POWER` (compagnons de mesure → ignorés par le light mapper, laissés au SensorMapper).
   **Conserver** `ENERGY_STATE/ON/OFF` en conflit dur (relais de prise, pas une lumière — décision
   Alexandre 2026-07-19). Les garde-fous restants (name-heuristics `prise/plug`, eq.generic_type,
   dédup) restent inchangés.
2. `registry.py` — généraliser `_map_structural_multi_entity` pour accepter le **primaire `light`**
   à l'identique du `switch` (sortie `[light, sensor_power, sensor_energy, ...]`), device commun
   via `jeedom_eq_id`.
3. Réalignement golden + gate terrain.

## Section 3 — Chemin recommandé

**Option 1 — Direct Adjustment (retenue).** Une **story corrective dédiée** dans la lignée
multi-entité (Epic 11), traitée comme un fix moteur + petite extension d'agrégation. Gouvernance
identique au pattern maison : non-régression `registry`/switch, golden réaligné, gate terrain réel.
- Effort : **Moyen**. Risque : **Moyen** (golden + non-régression multi-entité switch + garde-fous
  faux positifs light). Pas d'impact périmètre MVP.

**Option 2 — Rollback.** `[Non viable]` — rien à annuler ; le comportement actuel est un défaut
de couverture, pas une régression d'une story livrée.

**Option 3 — Revue MVP.** `[Non viable]` — MVP inchangé ; on rend le pipeline plus honnête sans
toucher aux objectifs.

**Décision ouverte (placement epic)** — à trancher avec Alexandre :
- (a) **Réactiver la famille Epic 11** avec une story de suivi (ex. `11.4 — Lumière + mesure de
  consommation : projection multi-entité`), cohérent car c'est la même mécanique multi-entité ; **ou**
- (b) créer un **petit epic correctif dédié** (pe-epic-19) si tu préfères un conteneur propre pour
  les correctifs moteur post-16.

## Section 4 — Propositions d'édition détaillées

### Stories (nouvelle)
```
Story: [pe-epic-11 / 11.4]  (ou pe-epic-19 / 19.1 selon décision placement)
Titre: Lumière + mesure de consommation → projection multi-entité (light + sensor power/energy)

Acceptance Criteria (brouillon) :
- AC1: un eqLogic avec LIGHT_* actionnable + POWER/CONSUMPTION publie 1 light + 1..n sensor
       (device_class power/energy) sous un device HA commun (identifiers = eq_id).
- AC2: POWER/CONSUMPTION/ENERGY_POWER ne déclenchent plus conflicting_generic_types sur une lumière.
- AC3: ENERGY_STATE/ON/OFF + LIGHT_* reste ambiguous (prise), comportement inchangé.
- AC4: non-régression multi-entité switch (Epic 11) et garde-fous faux positifs light
       (name-heuristics, eq.generic_type, color-only, orphan-state, dédup).
- AC5: dépublication domain-aware — nettoie tous les topics secondaires (hérité 11.1.bis/11.2).
- AC6: golden corpus réaligné ; gate terrain box 192.168.1.21 (eq 457) : light + W + kWh visibles.

Rationale: corrige un faux positif qui skippe des lumières pilotables réelles et aligne le
comportement light sur le multi-entité switch déjà livré.
```

### Architecture (`architecture-projection-engine.md`)
```
Section: agrégation multi-entité / _map_structural_multi_entity
OLD (esprit): « primaire = switch(es), puis sensors, puis binary_sensors »
NEW (esprit): « primaire = switch OU light, puis sensors (power/energy), puis binary_sensors ;
               device commun via eq_id »
Rationale: documenter l'extension du primaire light.
```

### Epics (`epics-projection-engine.md`)
```
- Story 2.2 (lumières) : note — POWER/CONSUMPTION/ENERGY_POWER sont des compagnons de mesure,
  pas des conflits ; seuls les vrais domaines antagonistes (heating/flap/smoke/…) et
  ENERGY_STATE/ON/OFF (prise) restent anti-light.
- Ajout de la story 11.4 (ou 19.1) décrite en Section 4.
```

### PRD / UI-UX
`[N/A]` — aucun changement (effet de bord UI positif documenté en Section 2).

## Section 5 — Handoff

**Classification : Moderate** (réorganisation backlog légère : ajout d'1 story + décision de
placement epic ; puis implémentation standard).

- **PO/SM (clawcode)** : entériner placement (11.4 vs pe-epic-19), enregistrer la story dans
  `sprint-status.yaml`, mettre à jour architecture/epics.
- **Dev (clawcode, BMAD)** : `create-story → dev-story → code-review` sur la story corrective.
- **Gate terrain** : rejouer sur box 192.168.1.21 (eq 457) avec preuves consignées.

**Critères de succès** : eq 457 publie `light` + `sensor` W + `sensor` kWh sous device commun ;
non-régression switch multi-entité ; golden réaligné ; 0 régression suite unitaire ; diagnostic
16.8 passe au vert pour ce cas.
