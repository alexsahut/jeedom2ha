# Relevé de parité Story 19.1

`resources/daemon/tools/parity_snapshot.py` compare l'état de publication du
démon avant et après un changement de sync. Il est **strictement en lecture
seule** : GET `/system/diagnostics`, GET `/system/published_scope` et
`mosquitto_sub` uniquement. Il ne déclenche ni `/action/sync`, ni publication
MQTT, ni écriture dans `data/`.

## Préconditions

1. Faire exécuter le sync normal par le plugin Jeedom ; ne pas utiliser cet
   outil pour le déclencher.
2. Depuis la VM de développement, ouvrir un tunnel SSH local vers les services
   locaux de la box (adapter le port du démon) :

   ```bash
   ssh -N -L 155080:127.0.0.1:<daemon-port> -L 11883:127.0.0.1:1883 jeedom-deploy
   ```

   Le tunnel évite d'exposer le démon ou MQTT sur le LAN. Garder cette session
   ouverte uniquement le temps du relevé.
3. Fournir le secret local et, si le broker l'exige, les identifiants MQTT par
   le mécanisme d'environnement masqué de l'hôte (`JEEDOM2HA_LOCAL_SECRET` ou
   `JEEDOM2HA_LOCAL_SECRET_FILE`, `JEEDOM2HA_MQTT_USER`,
   `JEEDOM2HA_MQTT_PASS`). Ne jamais les placer dans une commande, un argument,
   un URL, un fichier versionné ou un journal.

## Procédure terrain (read-only)

Dans `resources/daemon`, capturer l'état **avant** :

```bash
python3 -m tools.parity_snapshot capture \
  --base-url http://127.0.0.1:155080 \
  --mqtt-host 127.0.0.1 --mqtt-port 11883 \
  --label before --output /tmp/jeedom2ha-parity-before.json
```

Après le changement autorisé et le sync normal du plugin, capturer **après** :

```bash
python3 -m tools.parity_snapshot capture \
  --base-url http://127.0.0.1:155080 \
  --mqtt-host 127.0.0.1 --mqtt-port 11883 \
  --label after --output /tmp/jeedom2ha-parity-after.json
```

Comparer ensuite les deux fichiers :

```bash
python3 -m tools.parity_snapshot diff \
  --before /tmp/jeedom2ha-parity-before.json \
  --after /tmp/jeedom2ha-parity-after.json
```

Le code de retour vaut `0` seulement si décisions et topics MQTT sont
identiques. Un relevé vide (décisions **ou** topics), une erreur HTTP/MQTT ou
un diff non vide est un échec explicite (`2` pour capture/donnée invalide, `1`
pour un diff) : ne pas le consigner comme une parité validée. Les champs
`i11_candidates`, `explicit_scope_entries` et `published_scope_exceptions`
restent des observations ; l'outil ne les corrige jamais.

Fermer le tunnel dès que les captures sont terminées et conserver les JSON
comme preuve de la passe, hors du dépôt si elles contiennent des données de
l'installation.
