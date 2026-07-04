# Sprint Change Proposal — 2026-07-04 — Parité générique FAN_* → switch

Cycle actif de référence : **Moteur de projection explicable** (voir `active-cycle-manifest.md`).
Sources de vérité utilisées : `sprint-status.yaml` (suivi actif), `ha-projection-reference.md` (contraintes HA/types Jeedom), `resources/daemon/mapping/switch.py` et `resources/daemon/mapping/binary_sensor.py` (code réel, vérifié directement).

## 1. Résumé du problème

ClawBox (agent domotique) a signalé que l'eqLogic Jeedom **eq67** (plugin `pool`, "Filtration"), commande **cmd382** `type=info binary`, `generic_type=FAN_STATE`, n'est jamais exportée vers Home Assistant :

- `switch.py` groupe et publie uniquement les familles `SWITCH_*` (via `_group_switch_cmds`) et `ENERGY_*` (mono, via `_map_energy_switch`) — aucune reconnaissance de `FAN_*`.
- `binary_sensor.py` a une table `_BINARY_SENSOR_GENERIC_TYPE_MAP` figée qui ne contient aucune entrée `FAN_STATE`.
- `sensor.py` a `FAN_SPEED_STATE` (vitesse) mais rien pour `FAN_STATE` (marche/arrêt).

Alexandre (propriétaire produit) souhaite le trio complet `FAN_STATE` + `FAN_ON` + `FAN_OFF` publié comme `switch` HA pilotable (symétrique au trio `SWITCH_STATE`/`SWITCH_ON`/`SWITCH_OFF` déjà géré), pas un binary_sensor en lecture seule — la pompe de filtration piscine doit pouvoir être pilotée depuis HA.

Vérification directe du code (`resources/daemon/mapping/switch.py` lignes 90-105, 277-337) : `_map_cmd_group(eq, snapshot, group, family="SWITCH")` et `_group_switch_cmds` sont **déjà paramétrés par `family`** — la fonction interne accepte n'importe quelle famille de type `{family}_STATE/{family}_ON/{family}_OFF`, seul `_group_switch_cmds` filtre en dur sur `{"SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF"}`. Le diagnostic initial (~5 lignes de généralisation) est confirmé exact après lecture du code réel.

Vérification `ha_component_registry.py` : `PRODUCT_SCOPE` contient déjà `"switch"` (ouvert). Le registre HA gate par `ha_entity_type`, pas par `generic_type` Jeedom — aucune ouverture FR40/NFR10 supplémentaire n'est nécessaire, il s'agit d'une extension de mapper pur, pas d'un nouveau composant HA.

## 2. Analyse d'impact (checklist correct-course, sections 1-4)

- **1.1/1.2/1.3** : trigger = signalement ClawBox + demande explicite Alex. Catégorie = lacune de couverture mapper découverte en usage terrain (pas de bug de régression). Preuve : eq67/cmd382 absent des topics MQTT publiés malgré generic_type structurellement reconnu (`FAN_STATE`).
- **2.1** : `pe-epic-13` (in-progress, mais 13.1→13.4 tous `done`, scope = énergie/statistiques HA, prises mesureuses) ne couvre pas ce sujet — aucune modification de son périmètre n'est nécessaire ni souhaitable.
- **2.2** : nécessite un **nouvel epic dédié** (pas de scope existant pertinent).
- **2.3/2.4/2.5** : aucun epic futur planifié n'est invalidé ; aucune dépendance affectée ; pas de resequencing nécessaire (epic indépendant, isolé au mapper switch/binary_sensor).
- **3.1 PRD** : pas de conflit — le FR40/NFR10 gouverne l'ouverture de nouveaux *composants* HA, pas l'ajout de types Jeedom sous un composant déjà ouvert (`switch`). Aucune modification PRD requise.
- **3.2 Architecture** : impact mineur et localisé — généralisation de `_group_switch_cmds` pour accepter `family="FAN"` en plus de `"SWITCH"`, et exclusion anti-doublon correspondante dans `binary_sensor.py` (pattern déjà existant pour `SWITCH_*`/`ENERGY_*` via `_SWITCH_OWNED_GENERIC_TYPES`/`_switch_readback_cmd_ids`).
- **3.3 UX** : aucun impact (pas de nouvelle UI console — c'est un mapper daemon → MQTT discovery).
- **3.4 Autres artefacts** : `scripts/deploy-to-box.sh` et gate terrain existant restent utilisables sans modification ; tests unitaires à étendre (non-régression `SWITCH_*`/`ENERGY_*`).

## 3. Chemin retenu

**Option 1 — Direct Adjustment**, effort **Low**, risque **Low**. Généralisation additive et bornée du dispatch `family` déjà présent dans `switch.py`, symétrique à l'exclusion anti-doublon déjà présente dans `binary_sensor.py` pour `SWITCH_*`/`ENERGY_*`. Aucun rollback, aucune révision de MVP nécessaire.

## 4. Changements d'artefacts

- **Nouvel epic** `pe-epic-14` — "Parité générique FAN_* → switch (pompe filtration piscine)" — ajouté à `sprint-status.yaml`, statut `in-progress`.
- **Nouvelle story** `14-1-fan-state-on-off-generalisation-switch-family` — créée via workflow `create-story` (phase suivante).
- **Code** : `resources/daemon/mapping/switch.py` (généralisation `family`), `resources/daemon/mapping/binary_sensor.py` (exclusion anti-doublon `FAN_*`), tests unitaires associés.
- **active-cycle-manifest.md** : pas de changement de cycle actif — ce correct-course reste sous **Moteur de projection explicable** ; ajout d'une ligne de traçabilité en section 9 (note sur pe-epic-14).

## 5. Handoff

- **Scope de changement : Minor** — implémentation directe par l'équipe de développement (dev-story), pas de réorganisation de backlog PO/SM, pas de replan PM/Architecte.
- Prochaine étape : `create-story` pour matérialiser `14-1-...` en statut `ready-for-dev`.

## Approbation

Décision SM autonome documentée le 2026-07-04 dans le cadre de la contrainte procédurale du projet (workflow correct-course exécuté intégralement, section par section). Approuvée pour exécution — scope Minor, aucun conflit PRD/Architecture/UX détecté.
