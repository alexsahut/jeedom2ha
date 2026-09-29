# Fixtures — garde-fou publisher (story 19.4)

Traces de référence figées sur le code ACTUEL (avant tout correctif de
`apply_publication_decision()`), utilisées par
`tests/unit/test_story_19_4_guard_publisher_calls.py`. Chaque scénario a une
trace sémantique `<nom>.json` (publish/unpublish via `RecordingPublisher`) et,
depuis l'unité #2, une trace MQTT brute `<nom>_mqtt.json` (topic/payload
JSON/retain via le vrai `DiscoveryPublisher` posé sur `MqttRecordingBridge`).

## Scénarios

- **S1** — 1 sync du corpus doré sur état vide.
- **S2** — 2 syncs successifs du même corpus : le 2e ne produit aucun unpublish.
- **S3** — S1 puis un clic « Publier » sur la portée globale.
- **S4** — candidat I11 façon eq 579/585 (principal `ambiguous_skipped`,
  secondaires acceptés) : 2 syncs + 1 clic « Publier » (désormais aussi sous
  patch `evaluate_equipment`), sans unpublish.
- **S5** — 1er sync en `sure_probable`, 2e sync en `sure_only`
  (`sync_config.confidence_policy`) : les candidats `probable` perdent leur
  droit de publication.
- **S6** — candidat I11 (eq628) : sync1 principal + tous les secondaires
  `sure` acceptés, sync2 principal toujours accepté mais un secondaire
  (cmd 5980) refusé.

## Écarts réalisés à l'unité 3b-2 (C1, dépublication par candidat)

Seules les fixtures S5 et S6 ont été régénérées (`JEEDOM2HA_GUARD_REGEN=1`).

- **S5** : 583 ne dépublie plus que ses 3 switchs refusés (principal, 6009,
  6010) et garde ses 5 secondaires `sure` ; 457 ne dépublie plus que sa
  lumière et garde ses 2 capteurs. Effacements MQTT : 30 ⇒ 23. Disponibilité :
  plus d'effacement pour 583 et 457 (48 ⇒ 46 messages). Toujours 18 appels
  `unpublish`, un par équipement.
- **S6** : un `unpublish` de `jeedom2ha_628_5980` seul ; un effacement MQTT de
  plus ; disponibilité inchangée (`online`).
- S1 à S4 : identiques.

## Écarts réalisés à l'unité 4 (« Publier » en mini-sync)

Seules les fixtures « Publier » de S3 et S4 ont été régénérées (`JEEDOM2HA_GUARD_REGEN=1`).

- **S3** : 81 ⇒ 80 appels ; l'eq 6000 (`ha_missing_command_topic`), que le
  sync refuse, n'est plus publié par « Publier ». MQTT : 81 ⇒ 80 ;
  disponibilité : 47 ⇒ 46 (plus de `jeedom2ha/6000/availability`).
- **S4** : le clic « Publier » publie les 3 secondaires acceptés du candidat
  I11 et sa disponibilité `online` (0 ⇒ 3 appels, 0 ⇒ 1 message de
  disponibilité) ; toujours aucun `unpublish`.
- Syncs de S3 et S4, S1, S2, S5, S6 : identiques.
