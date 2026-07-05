# Retrospective pe-epic-13 - Energie HA exploitable

Date: 2026-07-05
Projet: jeedom2ha
Cycle actif: Moteur de projection explicable

## Synthese

`pe-epic-13` est livre (4/4 stories `done`) mais n'avait jamais ete flippe `done` au niveau epic dans `sprint-status.yaml` (reste `in-progress` depuis le 2026-06-30) et n'avait aucune retrospective materialisee, contrairement aux epics 11 et 12. Cette retro corrige les deux manques : elle capture les enseignements de l'epic et prepare le flip epic-level qui sera execute par le `correct-course` qui suit immediatement.

## Valeur livree

- Story 13.1 : `state_class` porte dans `reason_details` pour les sensors `power`/`energy` (`measurement` / `total_increasing`) et publie par le `DiscoveryPublisher` uniquement quand le mapper l'a renseigne.
- Story 13.2 : auto-detection des commandes `W`/`Wh`/`kWh` non taguees `generic_type`, avec garde-fou anti-faux-positif corrige en code-review (unites cumulatives non fiables exclues) puis correctif post-investigation HA (normalisation accent-insensitive de "Energie session").
- Story 13.3 : publication des mesures secondaires `power`/`energy` sur les prises mesureuses commandables, sans dupliquer le readback deja consomme par le switch primaire.
- Story 13.4 : README et versions (`0.2.0`) realignes sur le perimetre reellement livre ; suppression des mentions obsoletes.

## Preuves

- Gate terrain AC7 (2026-07-0x, box 192.168.1.21) : `total_eq=284`, `eligible=95`, `published=240` ; MQTT Discovery confirme `power`/`W`/`measurement` et `energy`/`Wh|kWh`/`total_increasing` sur plusieurs eqLogic (553, 554).
- Limitation constatee sur ce meme gate : verification directe Home Assistant (UI/registry) non prouvee — `homeassistant.local:8123` a repondu mais sans token HA disponible (401), connecteur HA n'exposant pas les entites cibles. MQTT/Jeedom PASS, HA UI non confirme.
- Suite unitaire daemon complete verte a chaque story (925 -> 939 tests selon les stories), suite cible 13.1-13.4 verte.

## Risques residuels

- La verification HA UI/registry de l'AC7 reste un point ouvert non ferme par preuve directe ; a rejouer avec un token HA valide si un doute produit se presente.
- Aucune visibilite maintainer sur les nouvelles metadonnees Energy (`state_class`, eligibilite W/Wh/kWh) dans la console jeedom2ha (`desktop/php`, `desktop/js`) : angle mort produit, voir Lecons.

## Lecons

- **Gouvernance BMAD non respectee** : le flip epic-level (`pe-epic-13: in-progress` -> `done`) et la retrospective n'ont pas ete faits au moment de la cloture de la story 13.4, alors que toutes les stories etaient `done`. Action corrective : le `correct-course` qui suit cette retro doit systematiquement inclure une checklist explicite de cloture d'epic (flip + retro) avant qu'un nouvel epic ne demarre.
- **Angle mort UI/daemon, jamais scope mais reel** : aucune des epics 11 a 14 n'avait d'AC touchant `desktop/*`, ce qui etait correct au regard des criteres d'acceptation definis a l'epoque - mais cela a laisse la console jeedom2ha totalement muette sur les nouvelles capacites Energy (metadata `state_class`), le state-streaming (epic 12) et bientot la parite FAN_STATE (epic 14). Ce n'est pas une regression ni un oubli de dev : c'est un **veritable enseignement de process** a retenir pour la suite - l'UI doit toujours etre re-evaluee en meme temps que les capacites du daemon evoluent, meme quand aucun AC explicite ne le demande, pour eviter que ce type d'angle mort se reproduise silencieusement.
- **Verification terrain HA incomplete acceptee comme "partiellement validee"** : le manque de token HA n'a pas bloque la cloture de la story 13.4 documentaire. A surveiller : ne pas laisser ce type de limitation devenir une habitude qui affaiblit la preuve terrain.

## Conclusion

L'epic 13 est fonctionnellement complet et de bonne qualite (0 finding bloquant sur les 4 stories), mais sa cloture de gouvernance etait incomplete. Cette retrospective flippe le statut vers `done` via le `correct-course` associe et transforme l'angle mort UI/Energy en action de fond : un futur epic de visibilite console (Energy/state_class/streaming/FAN parity) doit etre cadre par SCP, avec pour principe directeur permanent : **toujours aligner l'UI avec les capacites du daemon**, meme hors AC explicite.
