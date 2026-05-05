# Golden Corpus Story 8.4

Ce corpus fige 35 eqLogics deterministes pour le gate de non-regression Story 8.4
et l'extension sensor Story 9.1.

## Repartition normative

- Lights (10): `1000`-`1009`
- Covers (8): `2000`-`2007`
- Switches (5): `3000`-`3004`
- Ambigus (3): `4000`-`4002`
- Non-eligibles (2): `5000`-`5001`
- Valides bloques (2): `6000`-`6001`
- Sensors (5): `7000`-`7004`

## Roles equipement par equipement

- `1000`: light sure (on/off/state)
- `1001`: light probable (state+on)
- `1002`: light probable (state+off)
- `1003`: light probable (slider seul)
- `1004`: light probable (on + state numeric)
- `1005`: light sure (on/off/state + brightness + slider)
- `1006`: light sure (on/off/state)
- `1007`: light probable (state+on)
- `1008`: light probable (state+off)
- `1009`: light probable (slider + state numeric)

- `2000`: cover sure (up/down/state)
- `2001`: cover probable (up/down)
- `2002`: cover probable (slider implicite)
- `2003`: cover sure (up/down/state + stop)
- `2004`: cover probable (bso_up/bso_down)
- `2005`: cover sure (bso_up/bso_down/bso_state)
- `2006`: cover sure (up/down/state + slider)
- `2007`: cover probable (up/down + slider)

- `3000`: switch sure (on/off/state, type prise)
- `3001`: switch probable (on/off)
- `3002`: switch probable (on only)
- `3003`: switch probable (off only)
- `3004`: switch probable (partial on+state)

- `4000`: ambigu (light + flap en conflit)
- `4001`: ambigu (cover state orphan)
- `4002`: ambigu (switch rejete par heuristique nom)

- `5000`: non-eligible (disabled_eqlogic)
- `5001`: non-eligible (excluded_eqlogic)

- `6000`: valide bloque etape 3 (`ha_missing_command_topic`) via light `LIGHT_STATE` numeric seul
- `6001`: valide bloque etape 4 (`ha_component_not_in_product_scope`) via mapping test-double `climate`

- `7000`: sensor temperature (`TEMPERATURE`) -> `device_class=temperature`, `unit=°C`
- `7001`: sensor humidite (`HUMIDITY`) -> `device_class=humidity`, `unit=%`
- `7002`: sensor puissance (`POWER`) -> `device_class=power`, `unit=W`
- `7003`: sensor qualite air (`CO2`) -> `device_class=carbon_dioxide`, `unit=ppm`
- `7004`: sensor luminosite (`BRIGHTNESS`) -> `device_class=illuminance`, `unit=lx`

## Stabilite

- IDs stables, aucune generation aleatoire
- Structure de payload stable (`objects`, `eq_logics`, `published_scope`, `sync_config`)
- Aucune dependance environnement externe (MQTT/broker reels non utilises)
