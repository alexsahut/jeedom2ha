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

## Écarts attendus à l'unité #3 (refactor de `apply_publication_decision()`)

- **S3** : 81 appels aujourd'hui ⇒ 80 attendus — l'eq 6000
  (`ha_missing_command_topic`) est publié par le clic « Publier » global bien
  que le sync le refuse (`_should_attempt_publish` ne regarde que la
  confiance) ; il ne devra plus être publié.
- **S4** : le clic « Publier » devra publier les secondaires acceptés du
  candidat I11 (aujourd'hui 0 appel côté « Publier »).
- **S5** : les eq 583 (5 secondaires `sure`) et 457 (2 capteurs) devront
  garder leurs secondaires publiés lors de la transition de politique ; seuls
  les candidats devenus refusés devront être dépubliés (aujourd'hui, tout est
  republié puis dépublié dans le même sync — 18 unpublish figés).
- **S6** : seul le secondaire refusé devra être dépublié (aujourd'hui, rien
  n'est dépublié : la garde ne détecte pas cette transition publié → refusé).
