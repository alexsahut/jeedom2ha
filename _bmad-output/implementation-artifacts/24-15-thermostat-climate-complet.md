# Story 24.15 : Thermostat : `climate` complet (état, consigne, mode)

Status: ready-for-dev

> **Story rédigée par une session cloud déléguée (2026-11-12), documentaire**, en lecture seule du code (`origin/main` `ecedde5`), sans accès à la box ni à Home Assistant. Aucun nom réel, aucune IP, aucune marque (CC-48). **Draft** : cinq décisions reviennent à Alexandre (D1 à D5, recommandations ci-dessous). **Change la production** : les 7 entités `climate` existantes changent de payload, de topics et deviennent pilotables. Une autre story (24-14) est en développement sur une autre branche : recouvrements listés en fin de Dev Notes.

## Story

En tant qu'utilisateur dont un thermostat Jeedom est publié en `climate`,
je veux voir dans Home Assistant la température mesurée, la consigne, le mode et si le chauffage est en cours, et pouvoir régler la consigne et le mode,
afin que la carte thermostat de HA soit utilisable comme celle de l'app Maison.

**Parcours : démon + export PHP (ajout).** Comportement standard attendu chez tout utilisateur du plugin Jeedom « thermostat » ; un thermostat d'un autre plugin portant les mêmes types génériques suit les mêmes règles, avec repli explicite quand une information manque.

## Constat de production (2026-11-12, ClaudeBox)

Les 7 thermostats publiés en `climate` sont inutilisables : HA les montre `off`, sans température mesurée ni consigne ; la carte n'a rien à afficher ni à régler. La story 10-2 avait été validée sur la seule structure de la discovery (« commandabilité minimale utile validée structurellement via payload discovery »), sans essai de lecture ni d'ordre.

## Dépendances et décisions

- Reprend et complète **10-2** (ouverture gouvernée de `climate`) : aucune réouverture de `PRODUCT_SCOPE`, mais l'entrée de registre `climate` gagne des champs et capacités (AC1).
- Suit le modèle de **24-8** (vanne) et **24-9** (serrure) : état streamé, ordres exacts, `optimistic: false`, remplacement explicite, tests de cycle de vie.
- **24-14** en cours (autre branche) : recouvrements dans `transport/http_server.py`, `sprint-status.yaml`, `core/class/jeedom2ha.class.php`, `discovery/publisher.py`, docs (voir « Recouvrements avec 24-14 »).
- Décisions **D1 à D5** à trancher par Alexandre avant `ready-for-dev`.

## Task 0 faite par ClaudeBox le 2026-11-12 (données de production, lecture seule)

Les 7 thermostats publiés en `climate` (eq 128, 193, 217, 219, 240, 242, 595) viennent tous du plugin Jeedom « thermostat » et portent les mêmes commandes typées :

| Type générique | Type / sous-type | Rôle |
|---|---|---|
| `THERMOSTAT_SETPOINT` | info / numeric | consigne courante |
| `THERMOSTAT_SET_SETPOINT` | action / slider | régler la consigne |
| `THERMOSTAT_TEMPERATURE` | info / numeric | température mesurée |
| `THERMOSTAT_TEMPERATURE_OUTDOOR` | info / numeric | température extérieure |
| `THERMOSTAT_MODE` | info / string | mode courant (nom du mode) |
| `THERMOSTAT_SET_MODE` (×4) | action / other | un ordre par mode nommé (les noms viennent de la configuration du thermostat ; dont l'arrêt « Off ») |
| `THERMOSTAT_STATE` | info / binary | chauffe en cours |
| `THERMOSTAT_STATE_NAME` | info / string | statut lisible |
| `THERMOSTAT_LOCK` | info / binary | verrouillage |
| `THERMOSTAT_SET_LOCK`, `THERMOSTAT_SET_UNLOCK` | action / other | verrouiller / déverrouiller |
| (sans type générique) | divers | ignorées |

**Point clé** : un thermostat simplement à l'arrêt (mode de nuit, consigne atteinte) n'est **pas** éteint ; seul le mode d'arrêt du thermostat donne `hvac_mode: off`.

## Faits relevés dans le code (`origin/main` `ecedde5`, lecture seule)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Le mapper ne capte que `THERMOSTAT_SET_SETPOINT` (action, sous-type `slider` ou vide) et `THERMOSTAT_TEMPERATURE` (info) ; toutes les autres commandes du thermostat (consigne courante, mode, ordres de mode, état, verrou, extérieur) sont ignorées, sans entité secondaire. | `mapping/climate.py:16-31`, `:41-45`, `:51-53` |
| F2 | Topics déclarés par le mapper : `jeedom2ha/<eq>/temperature/set`, `jeedom2ha/<eq>/temperature/state`, `jeedom2ha/<eq>/current_temperature`. | `mapping/climate.py:55-60` |
| F3 | Discovery : `temperature_command_topic`, `temperature_state_topic`, `current_temperature_topic` (si température), `modes: ["heat", "off"]` en dur ; **aucun** `mode_state_topic`, `mode_command_topic`, `action_topic`, `preset_mode_*`, `min_temp`, `max_temp`, `temp_step`, `optimistic`. Sans `mode_state_topic`, HA est en mode optimiste pour le mode et l'affiche `off`. | `discovery/publisher.py:917-952` (modes `:937`) |
| F4 | `climate` n'est pas streamé : la docstring le dit, `_ACTIONABLE_STREAMED` / `_STREAMED_TYPES` ne le contiennent pas, `_READBACK_KEYS` non plus ; `_iter_streamed_candidates` saute donc le `climate`, et `publish_initial_states` ne publie **rien**, même au démarrage. | `sync/state.py:26-27`, `:61-73`, `:83-89`, `:632-641` ; appel `transport/http_server.py:2163-2167` |
| F5 | `sync.readback.STATE_KEYS` n'a pas d'entrée `climate` ; `readback_commands` rend une liste vide pour un type inconnu. | `sync/readback.py:32-41`, `:69-81` |
| F6 | Registre des topics retenus et de leur purge limité à `jeedom2ha/<eq>/(state|brightness|position)`. | `sync/state.py:92`, `:101-104` |
| F7 | `_resolve_state_topic` rend `jeedom2ha/<eq>/state` pour un `climate` (topic que la discovery ne déclare pas). | `transport/http_server.py:124-140` |
| F8 | Ordres : le démon est abonné à `jeedom2ha/+/+/set`, donc reçoit `jeedom2ha/<eq>/temperature/set`, mais `_NODE_SET_TOPIC_RE` exige un identifiant de commande numérique : le message est rejeté `invalid_command_topic`. `_expected_command_topics` et `_translate_command` n'ont aucune branche `climate`. | `transport/mqtt_client.py:27-33` ; `sync/command.py:22-28`, `:286-315`, `:399-438`, `:440-547` |
| F9 | `_normalize_slider_payload` n'accepte qu'un entier 0-100 : inutilisable pour une consigne en degrés décimaux. | `sync/command.py:899-908` |
| F10 | L'export PHP de topologie ne transmet pas la configuration des commandes (`minValue`, `maxValue`) ; `JeedomCmd` n'a pas ces champs. `logical_id` est déjà transmis (24-1). | `core/class/jeedom2ha.class.php:823-840` ; `models/topology.py:143-160` |
| F11 | Registre de validation : `climate` exige seulement `availability` et `has_setpoint`. `ClimateCapabilities` : `has_setpoint`, `has_current_temperature`. | `validation/ha_component_registry.py:62-65` ; `models/mapping.py:66-75` |
| F12 | Ordre des mappers : `ClimateMapper` après `SwitchMapper`, avant `BinarySensorMapper` (sinon `THERMOSTAT_STATE` serait capté en `binary_sensor`). | `mapping/registry.py:29-40` |
| F13 | Référentiel HA : `climate.mqtt` n'a qu'un champ requis (`availability > keys > topic`) ; types génériques `THERMOSTAT_*` du core listés. | `ha-projection-reference.md:164-168`, `:579-591` |
| F14 | Golden 8.4 : 3 thermostats synthétiques (11000-11002) dans le corpus ; leur payload changera. | `tests/fixtures/golden_corpus/` ; 10-2 Completion Notes |

## Comportement du plugin Jeedom « thermostat » (source publique `jeedom/plugin-thermostat`, `core/class/thermostat.class.php`, branche `master`)

- Ordre d'arrêt : `logicalId = off`, type générique `THERMOSTAT_SET_MODE`, nom par défaut traduit « Off » ; à l'exécution, l'info de mode reçoit la valeur traduite « Off » et le statut « Arrêté ».
- Ordres de mode : `logicalId = modeAction`, nom = nom du mode configuré ; à l'exécution, l'info de mode reçoit **le nom de la commande**.
- Ordre de consigne (`logicalId = thermostat`, `THERMOSTAT_SET_SETPOINT`, slider) : `configuration.minValue` / `maxValue` = bornes du thermostat (`order_min` / `order_max`) ; l'option `slider` est écrite telle quelle dans l'info de consigne ; **l'info de mode passe à « Aucun »** (consigne manuelle hors mode).
- `THERMOSTAT_STATE` = commande `actif` (binaire, chauffe en cours) ; `THERMOSTAT_STATE_NAME` = `status` (texte : « Chauffage », « Arrêté », « Suspendu »…).
- **Verrou** : quand `lock_state` vaut 1, **tous** les ordres (consigne, modes, arrêt) sont ignorés sans erreur.

## Parité Homebridge (source publique `homebridge-jeedom`, `index.js`, branche `master`, version 1.9.0)

Le code du plugin Homebridge installé sur la box n'est pas dans ce dépôt ; la lecture porte sur la source publique (version courante), à faire confirmer par ClaudeBox sur la version installée (Task 0 bis).

- **Service** : `Thermostat` créé seulement si l'équipement a `THERMOSTAT_SETPOINT` ; caractéristiques `CurrentTemperature`, `TargetTemperature`, `CurrentHeatingCoolingState`, `TargetHeatingCoolingState`, `TemperatureDisplayUnits` (Celsius).
- **Modes** : HomeKit ne connaît que Arrêt / Chauffer / Refroidir / Auto. La correspondance avec les ordres `THERMOSTAT_SET_MODE` est **une configuration de l'utilisateur dans le plugin Homebridge** (`thermoModes` : Chauf, Clim, Off, Auto = « id|nom »). Sans ordre « Off » configuré, « Éteint » dans Maison n'envoie rien (journal « rien n'est envoyé »). Auto non configuré : renvoie la consigne courante à `THERMOSTAT_SET_SETPOINT`. Les autres modes nommés (Eco, Nuit…) ne sont **pas** atteignables depuis HomeKit.
- **Mode affiché** (`TargetHeatingCoolingState`) : depuis l'info `THERMOSTAT_MODE` ; valeur = nom du mode configuré Off / Clim / Chauf / Auto, sinon une liste de noms d'arrêt usuels (`off`, `arret`, `eteint`…) → Arrêt ; tout autre mode → Auto ; valeur vide (virtuel en transition) → mode affiché inchangé.
- **État courant** (`CurrentHeatingCoolingState`) : d'abord `THERMOSTAT_STATE_NAME` comparé à des listes de noms (chauffage → HEAT, sinon OFF) ; à défaut `THERMOSTAT_STATE` binaire + mode : éteint si état faux **ou** mode arrêt, sinon chauffe.
- **Consigne** : lue sur `THERMOSTAT_SETPOINT` ; bornes `minValue` / `maxValue` de la configuration de `THERMOSTAT_SET_SETPOINT` (`parseInt`), appliquées seulement si les deux existent ; tout réglage est **arrondi au pas de 0,5** et ignoré s'il diffère de moins de 0,5 de la valeur courante.
- **Verrou** : `THERMOSTAT_LOCK` donne la caractéristique `LockPhysicalControls` **sur le même service** (verrouillage enfant), pilotée par `THERMOSTAT_SET_LOCK` / `THERMOSTAT_SET_UNLOCK`.
- **Température extérieure** : `THERMOSTAT_TEMPERATURE_OUTDOOR` n'est lue nulle part : ignorée.

## Décisions (2026-11-12 22:13)

- **D1 A** (Alexandre) : HA expose `heat`/`off`. Le mode d'arrêt Jeedom, reconnu par son identifiant logique et jamais par son nom, donne `off`. Les autres modes nommés deviennent des `preset_modes`. D1-c suit la recommandation : sans info de mode, aucun `mode_state_topic`.
- **D2** (ClaudeBox, parité Homebridge) : `hvac_action` vaut `heating` ou `idle` d'après `THERMOSTAT_STATE` ; il vaut `off` quand le mode est l'arrêt.
- **D3** (ClaudeBox, parité Homebridge) : les bornes sont lues sur la commande de consigne et ne s'appliquent que si les deux sont valides ; le pas est de 0,5 ; une valeur hors bornes est refusée, sans écrêtage.
- **D4 A** (Alexandre) : le verrou est publié comme un `switch` « Verrouillage » séparé, de catégorie configuration, jamais comme un `lock`.
- **D5** (Alexandre) : la température extérieure est ignorée.
- Task 0 bis (ClaudeBox) : la version de `homebridge-jeedom` installée sur la box est bien la 1.9.0, celle qui a été lue.
- Ordre de développement : après la fusion de 24-14, qui touche `transport/http_server.py`. Rebaser la branche sur main avant de commencer.

## Décisions proposées (historique)

### D1 — Correspondance des modes

- **Option A (recommandée)** : `modes: ["heat", "off"]` ; les modes Jeedom autres que l'arrêt deviennent des `preset_modes` (noms tels quels, lus des commandes, aucun codé en dur).
  - **État `hvac_mode`** : `off` si et seulement si l'info `THERMOSTAT_MODE` vaut le nom de l'ordre d'arrêt (commande `THERMOSTAT_SET_MODE` dont le `logical_id` est `off`, reconnu par le plugin `thermostat`) ; toute autre valeur non vide → `heat` (« Aucun », un mode nommé, un mode inconnu : le thermostat régule) ; valeur vide ou absente → rien publié.
  - **État `preset_mode`** : la valeur de `THERMOSTAT_MODE` si elle est l'un des presets ; sinon `none` (consigne manuelle « Aucun », arrêt).
  - **Ordre `hvac_mode`** : `off` → ordre d'arrêt ; `heat` depuis l'arrêt → renvoi de la consigne courante à `THERMOSTAT_SET_SETPOINT` (le plugin repasse en consigne manuelle ; parité de l'« Auto non configuré » de Homebridge) ; `heat` alors que l'état publié est déjà `heat` → aucun ordre (sinon le mode nommé courant serait écrasé par « Aucun »).
  - **Ordre `preset_mode`** : nom exact (sensible à la casse) → la commande `THERMOSTAT_SET_MODE` de ce nom ; `none` ou nom inconnu → refusé, aucun ordre.
  - **Sans ordre d'arrêt identifié** (thermostat d'un autre plugin) : `modes: ["heat"]`, aucun ordre `off` possible (parité : « Éteint » sans ordre configuré n'envoie rien). **Sans info `THERMOSTAT_MODE`** : ni `mode_state_topic` ni presets ; `modes: ["heat"]` seul (point D1-c ci-dessous).
- **Option B** : tous les modes, arrêt compris, en `preset_modes` ; `modes: ["heat"]` fixe. Plus simple, mais l'arrêt n'est plus un arrêt pour HA (carte, Assist « éteins le chauffage », automatisations `hvac_mode: off`).
- **Justification (parité Homebridge)** : HomeKit expose un mode Arrêt distinct et un mode Chauffer ; A reproduit cette séparation. Les modes nommés, inaccessibles dans HomeKit, deviennent accessibles dans HA par les presets : c'est un **plus** sans contradiction. Contrairement à Homebridge, A n'exige aucune configuration de l'utilisateur et ne reconnaît l'arrêt par **aucun nom** (identifiant logique de la commande, pas de liste de noms d'arrêt).
- **D1-c (sous-point)** : sans info de mode, publier une fois `heat` sur le topic de mode (seul mode possible), ou ne pas déclarer de `mode_state_topic` (HA restera optimiste sur le mode). Recommandation : ne pas déclarer de `mode_state_topic` et ne proposer que `heat` ; aucun état inventé.

### D2 — `hvac_action`

- **Recommandation** : `action_topic` alimenté par `THERMOSTAT_STATE` : vrai (`1`, `true`, `on`) → `heating`, faux (`0`, `false`, `off`) → `idle` ; si l'état `hvac_mode` publié est `off` → `off` (prime sur la valeur binaire) ; valeur non reconnue → rien publié. `THERMOSTAT_STATE_NAME` n'est pas lu.
- **Justification (parité Homebridge)** : c'est la seconde branche de Homebridge (binaire + mode, arrêt prioritaire). La première (texte du statut comparé à des listes de noms) n'est pas reprise : lecture par nom proscrite (même garde-fou que 24-9), et l'info binaire est présente sur les 7 thermostats. HomeKit n'a pas d'état « au repos » (Homebridge affiche OFF quand la chauffe est coupée) ; HA en a un, `idle`, plus juste pour « mode Nuit, consigne atteinte ».
- Sans `THERMOSTAT_STATE` : pas d'`action_topic`.

### D3 — Consigne

- **Recommandation** :
  - `temperature_state_topic` alimenté par l'info `THERMOSTAT_SETPOINT` (valeur numérique telle quelle) ; `current_temperature_topic` par `THERMOSTAT_TEMPERATURE`.
  - Bornes : `min_temp` / `max_temp` lus dans `configuration.minValue` / `maxValue` de `THERMOSTAT_SET_SETPOINT` (export PHP **ajouté**, une ligne, comme `linked_value` en 24-8), publiés seulement si les deux sont des nombres finis et `min < max` ; sinon non publiés (bornes par défaut de HA) et le démon ne vérifie que le caractère numérique et fini.
  - `temp_step: 0.5`, `precision: 0.1` ; `temperature_unit` publié seulement si l'unité de la commande est `°C` ou `°F`.
  - Ordre : payload numérique fini (`.` ou `,` décimal) **arrondi au pas de 0,5**, **refusé hors bornes** (`setpoint_out_of_range`, aucun ordre, aucun écrêtage), envoyé en option `slider` à `THERMOSTAT_SET_SETPOINT`. Pas de seuil « moins de 0,5 d'écart = ignoré » (HA n'envoie un ordre que sur action de l'utilisateur).
- **Justification (parité Homebridge)** : mêmes bornes (configuration du slider, appliquées seulement si les deux existent), même pas de 0,5. Refus plutôt qu'écrêtage : un ordre hors bornes vient d'un appel MQTT direct ou d'une automatisation, pas de la carte (bornée) ; l'écrêter enverrait une consigne que l'utilisateur n'a pas demandée.

### D4 — Verrou (`THERMOSTAT_LOCK`)

- **Option A** : hors périmètre ; les trois commandes restent ignorées.
- **Option B (recommandée)** : entité secondaire `switch` « Verrouillage » sur le même appareil (`entity_category: config`), état `THERMOSTAT_LOCK` (1 = verrouillé = `ON`), `ON` → `THERMOSTAT_SET_LOCK`, `OFF` → `THERMOSTAT_SET_UNLOCK`, `optimistic: false`. **Pas** de `lock` (réservé aux organes de sécurité, sujet Assist de 24-9).
- **Justification (parité Homebridge)** : Homebridge expose le verrou (`LockPhysicalControls`) sur le thermostat ; B est la parité. Argument fonctionnel : verrouillé, le plugin ignore silencieusement **tous** les ordres ; sans le verrou visible dans HA, un ordre de consigne « sans effet » serait inexplicable. Si A est retenu, la documentation doit le dire.

### D5 — Température extérieure

- **Recommandation** : ignorée (aucune entité).
- **Justification (parité Homebridge)** : Homebridge ne la lit pas. Elle recopie en général une sonde extérieure déjà publiée par son propre équipement : une seconde entité serait un doublon (principe de moindre nuisance). Option alternative : `sensor` secondaire de classe `temperature`, désactivé par défaut.

## Critères d'acceptation

- **AC1 — Registre.** L'entrée `climate` de `HA_COMPONENT_REGISTRY` gagne ce que la story publie (topics d'état et d'ordre de consigne au minimum) ; `ClimateCapabilities` gagne `has_setpoint_state`, `has_mode`, `has_off`, `has_presets`, `has_action` (noms indicatifs) ; preuve FR40 `climate` mise à jour (nominal + échec) ; `PRODUCT_SCOPE` inchangé ; contrat 4D non régressé.
- **AC2 — Mapper.** Un équipement portant `THERMOSTAT_SET_SETPOINT` (action, sous-type `slider` ou vide) reste projeté en `climate` ; le mapper capte en plus `THERMOSTAT_SETPOINT`, `THERMOSTAT_MODE`, chaque `THERMOSTAT_SET_MODE` et `THERMOSTAT_STATE` (et, selon D4, le verrou). Un équipement sans `THERMOSTAT_SET_SETPOINT` garde sa projection actuelle. Les noms de modes viennent des commandes ; **aucun nom de mode n'est codé en dur** ; l'ordre d'arrêt est reconnu par son `logical_id`, jamais par son nom.
- **AC3 — Aucun état inventé.** Payload `optimistic: false`. Un topic d'état n'est déclaré que si une info réelle l'alimente ; une valeur vide, absente ou non reconnue ne publie rien. Un thermostat à l'arrêt de régulation (mode nommé, chauffe coupée) est `heat` / `idle`, **jamais** `off` ; seul le mode d'arrêt donne `off`.
- **AC4 — État initial.** Après la publication de la discovery d'un `climate` (démarrage du démon, « Relire Jeedom », synchro de service), consigne, température mesurée, mode, preset et action sont publiés (retenus) depuis les valeurs courantes connues de Jeedom, quand elles existent.
- **AC5 — Streaming.** Un changement de `THERMOSTAT_SETPOINT`, `THERMOSTAT_TEMPERATURE`, `THERMOSTAT_MODE` ou `THERMOSTAT_STATE` est publié sur le topic correspondant ; un changement de mode republie `hvac_mode`, `preset_mode` et `hvac_action` (l'arrêt prime sur l'action). Ces commandes figurent dans `/system/state_listeners` (listeners Jeedom).
- **AC6 — Ordres exacts.** Consigne : D3 (arrondi au pas, refus hors bornes, option `slider`). Mode : D1 (`off` → ordre d'arrêt seulement s'il existe ; `heat` selon D1 ; tout autre payload refusé). Preset : nom exact → la commande `THERMOSTAT_SET_MODE` de ce nom ; `none`, nom inconnu ou commande d'un autre équipement → refusé. Aucun ordre sans sa commande Jeedom (`missing_action_command`) ; aucun état optimiste publié après un ordre (confirmation par l'état streamé, sinon `stateless`). Les messages retenus restent ignorés (garde 24-7).
- **AC7 — Payload.** `default_entity_id = climate.jeedom2ha_<eq>` (22-1), `unique_id` **inchangé** (`jeedom2ha_eq_<eq>`, aucun nouvel `entity_id`) ; topics sous `jeedom2ha/<eq>/…`, tous déclarés dans la discovery et seuls utilisés par l'état et les ordres (état ⊆ discovery).
- **AC8 — Cycle de vie.** Mise à jour en place des 7 `climate` (même `unique_id`, même domaine) ; les anciens topics d'état (`jeedom2ha/<eq>/temperature/state`, `jeedom2ha/<eq>/current_temperature`) ne sont plus déclarés ; un topic retenu de canal `climate` qui perd sa source est vidé ; selon D4, l'entité secondaire du verrou suit les chemins de 24-8 (à chaud et au boot). Inventaire des entités avant / après.
- **AC9 — Override et export.** L'override pe-epic-16 connaît les capacités de thermostat (forçage d'un thermostat vers un autre actionneur refusé, comme 24-8) ; l'export de décision rend les topics réels du `climate`.
- **AC10 — Non-régression.** Golden 8.4 régénéré (seuls les 3 thermostats synthétiques changent) ; aucune autre projection modifiée ; suites Python, Node et `flake8` vertes ; garde 25.4 tenue (lignes remplacées déclarées).
- **AC11 — Documentation.** `docs/fr_FR/index.md` (ce que montre et pilote un thermostat, presets, verrou selon D4, ordres ignorés quand le thermostat est verrouillé) et `changelog_beta.md`.
- **AC12 — Preuve terrain (humain / ClaudeBox).** Sur un thermostat réel : carte HA avec température, consigne et mode corrects ; un réglage de consigne de +0,5 puis retour ; un preset puis retour au mode d'origine ; arrêt puis reprise **seulement avec l'accord d'Alexandre** (chauffage réel).

## Tâches proposées

- [x] **Task 0 — Données de production** (ClaudeBox, 2026-11-12) : 7 thermostats, commandes typées (tableau ci-dessus).
- [ ] **Task 0 bis — Vérifications avant `ready-for-dev`** (ClaudeBox, lecture seule) :
  - `logical_id` de l'ordre d'arrêt = `off` et nom de cette commande = valeur prise par l'info de mode à l'arrêt, sur les 7 (si un nom a été modifié, la règle D1 ne reconnaît plus l'arrêt) ;
  - `configuration.minValue` / `maxValue` présents sur les 7 ordres de consigne ;
  - valeurs observées de `THERMOSTAT_MODE` (dont « Aucun » après un réglage manuel) et de `THERMOSTAT_STATE` ;
  - version de `homebridge-jeedom` installée et passages thermostat identiques à la source publique lue ici ; présence ou non d'une configuration `thermoModes` sur ces équipements.
- [ ] **Task 1 — Export PHP (ajout)** : `min_value` / `max_value` des actions `slider` (configuration du cœur), lus dans `JeedomCmd` (D3).
- [ ] **Task 2 — Mapper** (`mapping/climate.py`) : commandes captées, presets, ordre d'arrêt par `logical_id`, topics par canal, capacités (D1, D2, D4, D5).
- [ ] **Task 3 — Discovery** (`_build_climate_payload`) : `mode_*`, `preset_mode_*`, `action_topic`, `min_temp` / `max_temp` / `temp_step` / `precision` / `temperature_unit`, `optimistic: false`.
- [ ] **Task 4 — État** (`sync/readback.py`, `sync/state.py`) : `climate` streamé, canaux (consigne, température, mode, preset, action), traduction (D1, D2), état initial, regex et purge des canaux retenus étendues.
- [ ] **Task 5 — Ordres** (`sync/command.py`, `transport/mqtt_client.py` si besoin) : topics de consigne / mode / preset, `_expected_command_topics`, traduction (D1, D3), politique de confirmation.
- [ ] **Task 6 — Verrou** (selon D4) : secondaire `switch`, remplacement et cycle de vie.
- [ ] **Task 7 — Override, export, registre** (AC1, AC9).
- [ ] **Task 8 — Tests et documentation** (AC10, AC11).
- [ ] **Gate, déploiement, preuve terrain** (ClaudeBox et Alexandre, AC12).

## Tests attendus (`resources/daemon/tests/unit/test_story_24_15_thermostat_climate_complet.py`, identifiants synthétiques)

- Mapper : thermostat complet (4 ordres de mode dont l'arrêt) ; sans ordre d'arrêt ; sans info de mode ; sans `THERMOSTAT_STATE` ; sans `THERMOSTAT_SETPOINT` ; noms de modes arbitraires (accents, espaces, casse) ; ordre d'arrêt renommé (reconnu par `logical_id`) ; aucun nom en dur (un mode nommé « Off » sans `logical_id` `off` n'est pas l'arrêt).
- Payload : clés présentes / absentes selon les capacités ; `optimistic: false` ; bornes publiées seulement si valides (absentes, non numériques, `min ≥ max`) ; `unique_id` et `default_entity_id` inchangés.
- État : table `hvac_mode` (arrêt → `off`, mode nommé → `heat`, « Aucun » → `heat`, inconnu → `heat`, vide → rien) ; table `preset_mode` (preset, « Aucun » → `none`, arrêt → `none`) ; table `hvac_action` (1 → `heating`, 0 → `idle`, arrêt → `off` quelle que soit la valeur binaire, valeur illisible → rien) ; un changement de mode republie action et preset ; état initial au boot ; listeners exposés.
- Ordres : consigne décimale (`20.5`, `20,5`), arrondi (`20.3` → `20.5`), hors bornes refusé, non numérique / infini refusé ; `off` sans ordre d'arrêt refusé ; `heat` déjà en `heat` → aucun ordre ; `heat` depuis l'arrêt → consigne courante renvoyée ; preset exact, casse différente refusée, `none` refusé ; commande d'un autre équipement refusée ; message retenu ignoré ; confirmation `real_state_confirmation`.
- Verrou (si D4 B) : secondaire `switch`, état, ordres, `entity_category`, aucun `lock`.
- Cycle de vie : mise à jour en place (pas de retypage), anciens topics non redéclarés, canal retenu sans source vidé, au boot et à chaud.
- Non-régression : un équipement sans `THERMOSTAT_SET_SETPOINT` inchangé ; golden 8.4 ; 10-2 (tests mis à jour, déclarés à la garde 25.4).

## Garde-fous

- Un thermostat pilote un chauffage réel : aucun ordre d'arrêt ni de mode sur la box sans Alexandre.
- Aucun nom de mode codé en dur ; aucune déduction depuis un nom (mode, statut, équipement).
- Aucun état optimiste ni inventé ; refus plutôt qu'écrêtage.
- `unique_id` des 7 `climate` inchangés (pas de doublon d'entité, historique HA conservé).
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Dev Notes

- **Topics proposés** (à figer au développement, dérivés de l'état `jeedom2ha/<eq>/state` par `channel_topic`) : état `jeedom2ha/<eq>/setpoint`, `…/current_temperature`, `…/mode`, `…/preset`, `…/action` ; ordres `jeedom2ha/<eq>/temperature/set`, `…/mode/set`, `…/preset/set`. `jeedom2ha/+/+/set` couvre déjà ces ordres côté abonnement ; il faut une regex dédiée avant `_NODE_SET_TOPIC_RE` (qui exige un id numérique) et `_CHANNEL_TOPIC_RE` étendue aux nouveaux canaux.
- **Champs MQTT climate** utilisés (`mode_state_topic`, `mode_command_topic`, `modes`, `preset_mode_state_topic`, `preset_mode_command_topic`, `preset_modes`, `action_topic`, `temperature_*`, `current_temperature_topic`, `min_temp`, `max_temp`, `temp_step`, `precision`, `temperature_unit`, `optimistic`) : non revérifiés dans la source de HA 2026.9.4 par cette session ; `preset_modes` ne doit pas contenir `none` (valeur réservée) ; valeurs d'`action` admises : `off`, `heating`, `idle`… À confirmer à la preuve terrain.
- **Effet de bord du plugin** : un réglage de consigne passe le mode à « Aucun » (preset `none`, `hvac_mode` `heat`) : c'est le comportement Jeedom, à documenter, pas à corriger.
- **Verrou** : verrouillé, le plugin ignore les ordres sans erreur ; la confirmation par l'état streamé ne viendra pas ; le journal du démon ne peut pas le distinguer d'un ordre lent.
- **Ordre des mappers** : inchangé ; le `climate` reste avant `binary_sensor`.
- **Golden** : 3 thermostats synthétiques à enrichir des nouvelles commandes typées (identifiants synthétiques).

### Recouvrements avec 24-14 (branche `story/analyse-reevaluation-au-demarrage`, en `review`)

| Fichier | 24-14 | 24-15 | Risque |
|---|---|---|---|
| `transport/http_server.py` | `_do_handle_action_sync_body` : `app["topology"]`, éligibilité, `mappings`, `publications`, `scenario_publications` remplacés **en fin** de synchro ; origine de synchro (`sync_origin`) ; scénarios toujours publiés | `_resolve_state_topic` (`:124-140`) et, selon l'implémentation, le cycle de vie (`_detect_lifecycle_changes`) ; état initial appelé `:2163-2167` | **Moyen** : même fonction de synchro ; `publish_initial_states` lit `app["publications"]` remplacé plus tard par 24-14 → vérifier, après fusion, que l'état initial du `climate` part bien avec la nouvelle publication. Rebaser 24-15 sur 24-14 si celle-ci est fusionnée d'abord. |
| `sync/command.py` | refus `scenario_inactive` (bloc scénario, ~`:1112`) | regex, `_parse_topic`, `_expected_command_topics`, `_translate_command` | Faible (zones distinctes). |
| `discovery/publisher.py` | imports de disponibilité, `_build_availability_fields` (branche scénario), disponibilité retenue des scénarios | `_build_climate_payload` (`:917-952`) | Faible ; le `climate` utilise `_build_availability_fields` (branche non-scénario inchangée). |
| `core/class/jeedom2ha.class.php` | `cron5`, empreinte (`eqLogic` + `scenario`), en-tête de mode de synchro | une ligne dans l'export des commandes (`:823-840`) | Faible en texte. Fonctionnel : l'empreinte de 24-14 lit la configuration de l'**équipement**, pas celle des commandes ; pour le plugin thermostat, bornes et liste des modes sont dans la configuration de l'équipement, donc un changement est bien capté. |
| `export/decision_export.py`, `docs/fr_FR/index.md`, `docs/fr_FR/changelog_beta.md`, garde 25.4 (`tests/unit/test_story_25_4_non_regression.node.test.js`) | modifiés | à modifier | Conflits de texte probables, triviaux. |
| `sprint-status.yaml` | ligne `24-14` ajoutée après `24-13` | ligne `24-15` ajoutée au même endroit | Conflit de texte certain, trivial. |

La synchro de service de 24-14 (sur changement d'empreinte) republie la discovery puis l'état initial : avec 24-15, un ajout ou un retrait de mode dans un thermostat sera repris sans redémarrage.

## Vérifications non faites par cette session

Les valeurs réelles des commandes sur la box ; le `logical_id` et le nom des ordres d'arrêt ; la configuration du slider ; la version installée de `homebridge-jeedom` et sa configuration des modes ; les champs de `climate.mqtt` dans HA 2026.9.4.

## Journal des décisions

- 2026-06-09 — Story 10-2 : `climate` ouvert, validé sur la structure de la discovery seulement.
- 2026-11-12 — Constat de production et Task 0 (ClaudeBox) : 7 thermostats inutilisables, commandes typées relevées.
- 2026-11-12 — Story rédigée (session cloud déléguée, documentaire) : faits du code, lecture des sources publiques du plugin thermostat et de `homebridge-jeedom`, D1 à D5 avec recommandations ; `draft` en attente des décisions d'Alexandre.
- 2026-11-12 22:13 — Décisions d'Alexandre : D1 A, D4 A, D5 ignorée (« ok recos ») ; D2 et D3 tranchées par ClaudeBox selon la parité Homebridge ; Task 0 bis faite (homebridge-jeedom 1.9.0) ; story `ready-for-dev`, développement après 24-14.
