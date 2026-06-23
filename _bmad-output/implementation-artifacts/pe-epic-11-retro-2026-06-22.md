# Retrospective pe-epic-11 - Energie et routage solaire

Date: 2026-06-22
Projet: jeedom2ha
Cycle actif: Moteur de projection explicable

## Synthese

`pe-epic-11` est livre. La vague a rendu lisibles dans Home Assistant les equipements de routage solaire cibles sans ouvrir de nouveau domaine HA : MSunPV eq553, chauffe-eau eq554, IQ EV eq583 et pilotage de priorisation eq628. Le moteur est passe d'une projection principalement mono-entite a des projections multi-domaines et multi-switch structurelles, tout en conservant la gouvernance registry-driven.

## Valeur livree

- Story 11.1 : 65 capteurs eq553 publies, eligibilite sans `generic_type`.
- Story 11.1.bis : depublication exhaustive des capteurs secondaires, sans ghosts HA.
- Story 11.2 : eq554 publie sous un device commun avec 1 `switch`, 12 `sensor` et 1 `binary_sensor`.
- Story 11.3 : eq583 et eq628 couverts par le support generique `SWITCH_*` et le multi-switch structurel.

## Preuves

- PR #123 : stories 11.1, 11.1.bis et streaming 12.1.
- PR #127, commit `5e3d39b` : story 11.2; 916 tests verts.
- PR #128, commit `3546f22` : story 11.3; CI GitHub verte.
- Gate terrain 11.1 : 65 capteurs eq553 publies sur la box.
- Gate terrain 11.1.bis : passage 65 vers 0 topics lors de la suppression, puis restauration a 65.
- Gate terrain 11.2 : 14 entites eq554, switch non `unknown`.
- Gate terrain 11.3 : eq583 et eq628 publies avec etats actionnables non `unknown`.

## Risques residuels

- Le corpus energie reste dependant des generics et topologies exposes par les plugins Jeedom reels.
- Le support multi-domaine doit rester structurel et borne; aucune allowlist d'identifiants ne doit devenir une politique produit implicite.
- L'issue GitHub #124 suit encore le nettoyage d'un topic discovery eq-level legacy lors des migrations mono vers node-scoped.

## Lecons

- Separer discovery et restitution d'etat a permis d'identifier clairement la responsabilite de pe-epic-12.
- Les gates terrain de depublication sont indispensables pour les projections multi-entites.
- Un support generique fonde sur la structure des commandes resiste mieux que des exceptions par equipement.
- Le tracking documentaire doit etre ferme dans la meme sequence que le code et la preuve terrain.

## Conclusion

La promesse de `pe-epic-11` est tenue : les equipements energie prioritaires sont projetes avec une topologie HA utile, des etats exploitables et une depublication maitrisee. Aucun travail produit restant ne bloque la cloture de l'epic.
