# Retrospective pe-epic-14 - Parite generique FAN_* -> switch

Date: 2026-07-05
Projet: jeedom2ha
Cycle actif: Moteur de projection explicable

## Synthese

`pe-epic-14` est marque `done` dans `sprint-status.yaml` (story unique 14-1 `done`, gate terrain PASS) mais n'a jamais ete formalise comme epic dans `epics-projection-engine.md`, et n'a aucune retrospective. Il a ete traite integralement en Minor/Direct Adjustment via SCP (`sprint-change-proposal-2026-07-04-fan-switch-parity.md`), sans jamais repasser par la structure epic standard. Cette retro cloture cet ecart de gouvernance et en tire un enseignement explicite demande par Alexandre : le respect strict de la methode BMAD avait ete demande explicitement, et ne pas formaliser l'epic constitue un manquement direct a cette consigne.

## Valeur livree

- Story 14.1 : generalisation de `_group_switch_cmds` (switch.py) et `_switch_readback_cmd_ids` (binary_sensor.py) pour supporter la famille `FAN` (`FAN_STATE`/`FAN_ON`/`FAN_OFF`) en plus de `SWITCH`, sans nouveau composant HA (switch deja ouvert dans `PRODUCT_SCOPE`).
- Ajout de `FAN_ON`/`FAN_OFF` dans la table de routage commande HA -> Jeedom (`sync/command.py`).
- Correctif de robustesse decouvert en gate terrain : fallback "single-trio-per-family" quand le groupement par nom ne trouve pas de trio complet (noms heterogenes "Filtration"/"Actif"/"Auto" sur eq67, sans prefixe commun).

## Preuves

- Gate terrain (2026-07-04, box 192.168.1.21, 2e passage apres correctif) : `homeassistant/switch/jeedom2ha_67_382/config` publie, etat `ON`, zero regression sur les groupes SWITCH_* existants (eq583, eq628).
- 10/10 tests story PASS, 1456 passed sur la suite complete (24 echecs pre-existants inchanges, lies a une dependance locale absente hors scope).
- Code review APPROVE, 0 finding Critical/High ; 1 finding LOW herite documente (garde-fous anti-faux-positif de `_map_energy_switch` non appliques a `_group_switch_cmds`, deja vrai avant cette story, non aggrave).

## Risques residuels

- Le finding LOW herite (garde-fous anti-faux-positif absents de `_group_switch_cmds`, y compris pour la nouvelle famille FAN) reste documente mais non traite ; a reprendre via son propre correct-course si un probleme produit est constate.
- Console jeedom2ha muette sur la parite FAN_STATE, comme deja identifie dans la retro pe-epic-13 : meme angle mort UI/daemon.

## Lecons

- **Manquement direct a une consigne explicite** : Alexandre avait explicitement demande de suivre la methode BMAD ; or epic 14 n'a jamais ete cree dans `epics-projection-engine.md` ni suivi du cycle standard `create-epic -> create-story -> dev-story -> code-review -> retrospective`. Le traitement via SCP Minor/Direct Adjustment etait justifie sur le fond (extension de mapper sous un composant HA deja ouvert, pas de nouvelle gouvernance FR40/NFR10 a rejouer), mais cela n'excusait pas l'absence de formalisation epic-level et de retrospective. **Action a retenir** : meme un changement scope Minor/Direct Adjustment via SCP doit systematiquement etre rattache a une entree epic (meme minimale) dans le document d'epics, avec une retrospective de cloture - pas de bypass de la structure de gouvernance, quel que soit le niveau de scope.
- **Le gate terrain a revele ce que les tests unitaires ne pouvaient pas voir** : la topologie reelle de eq67 (noms de commandes heterogenes sans prefixe commun) n'etait couverte par aucun test unitaire initial, car tous les cas de test reproduisaient des noms partageant un prefixe. Seule l'inspection directe de la base Jeedom reelle a revele le probleme. Confirme un principe deja recurrent dans les epics precedents (10.7) : le gate terrain sur box reelle n'est pas une formalite, il trouve des cas structurels absents des tests.
- **Angle mort UI/daemon confirme une seconde fois** : comme pour l'epic 13, aucune visibilite console sur la nouvelle parite FAN_STATE. Renforce la necessite d'un principe permanent : toujours reevaluer l'alignement UI/daemon a chaque extension de capacite, meme hors AC explicite.

## Conclusion

L'epic 14 est fonctionnellement solide (0 finding bloquant, gate terrain PASS apres correctif iteratif) mais sa gouvernance etait en dehors des clous malgre une consigne explicite de suivre BMAD. Le `correct-course` qui suit cette retro doit formaliser epic 14 a minima dans `epics-projection-engine.md` (traçabilite retroactive) et graver comme regle permanente : aucun changement, meme Minor/Direct Adjustment, ne doit sauter l'etape de formalisation epic + retrospective.
