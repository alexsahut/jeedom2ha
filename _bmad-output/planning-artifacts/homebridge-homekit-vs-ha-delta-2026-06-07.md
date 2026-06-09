# Homebridge HomeKit vs HA Delta - 2026-06-07

status: captured
date: 2026-06-07
source_agent: main
source_alias: ClawBox
source_channel: OpenClaw inter-session handoff
scope: homebridge-published-field-inventory-vs-current-ha-scope
ha_scope_current:
  - light
  - cover
  - switch
  - sensor
  - binary_sensor
  - button
provenance:
  - synthese-audit--homebridge-exposition-homekit.md (2026-05-18)
  - synthese-audit--homebridge-configuration-complete.md (2026-05-29/30)
  - synthese-audit--comparaison-homebridge-homekit-vs-jeedom2ha.md (2026-06-06)
note: Summary transmitted from existing audited documentation. No new field scan was requested for this artifact.

# Homebridge HomeKit vs HA Delta - 2026-06-07

## Purpose

Archive the useful summary already audited by `ClawBox`, so `pe-epic-10` can be sequenced from real Homebridge/HomeKit families and a concrete delta against the HA scope already opened in `jeedom2ha`.

## Provenance And Reading Constraints

- The transmitted base is documentary, not a new live scan.
- The useful perimeter excludes annex platforms such as `camera`, `samsung`, `alexa`, and `gsh`.
- The reading below is intentionally framed in usage families and representative examples, not as an exhaustive live proof equipment-by-equipment.

## Observed Homebridge Baseline

- After cleanup, Homebridge published **119 OK accessories** on the HomeKit side, excluding annex platforms.
- The core useful perimeter remains Jeedom equipment exposed through `sendToHomebridge=1`.
- The HomeKit surface also includes **5 scenarios** exposed as HomeKit switches.

## Current HA Scope In Repo

Current `jeedom2ha` published scope used for delta evaluation:

- `light`
- `cover`
- `switch`
- `sensor`
- `binary_sensor`
- `button`

## Families Already Largely Covered By Current HA Scope

### 1. `light`

- Coverage reading: already strongly aligned.
- Representative examples: `buffet ikea`, `lampadaire ikea`, `Chevet Arthur`, `lampe bureau`, `Spots salon`, `Spots cuisine`, `Neons`, `Halogene`, `spots haie`, `Leds`, `veilleuse`.
- Confidence: high.

### 2. `cover`

- Coverage reading: strongly aligned for shutters, awnings, pergola-like motorized protections.
- Representative examples: `Volets`, `Volet piscine`, `store banne`, `store pergola`, `lambrequin`, `pergola`.
- Special note: `Portail` may also belong here depending on the HA modeling authority eventually retained.
- Confidence: high for shutters/stores, medium for `Portail`.

### 3. `switch`

- Coverage reading: strongly aligned for simple on/off devices and several virtual multi-switch surfaces.
- Representative examples: `prise bureau`, `prise imac salon`, `prise AMI`, `garage`, `sèche-serviettes`.
- Composite examples already fitting `switch` logic:
  - `SPA` with `Power`, `Filtration`, `Jets`, `Bulles`, `Electroliseur`
  - `pilotage priorisation solaire` with `Filtration piscine`, `Chauffage piscine`, `Chauffage SPA`, `Charge voiture`
- Confidence: high on simple on/off, medium to high on virtual composites.

### 4. `sensor`

- Coverage reading: strongly aligned for analog measurements and informational telemetry.
- Representative examples: `Température RDC`, `Température Etage`, `Température exterieur`, `Température terrasse`, `Analyse eau de piscine`, `Rosée et givre`, `Température piece de vie`.
- Confidence: high.

### 5. `binary_sensor`

- Coverage reading: strongly aligned for openings and binary states.
- Representative examples: `Fenêtre Arthur`, `Fenêtre Margaux`, `baie gauche/droite cuisine`, `baie gauche/droite salon`, `Porte bureau`, `porte cuisine`, `Porte entrée`, `Porte vers garage`, `Alerte vent`.
- Confidence: high.

## Families Still Outside Scope Or Not Yet Equivalent

### 1. Thermostats / heating

- Observed Homebridge family: several thermostats are already published.
- Representative examples: `Thermostat chambre Arthur`, `Thermostat chambre Margaux`, `Thermostat chambre parent`, `Thermostat Galerie`, `Thermostat RDC`, `Thermostat SDB`, `Thermostat SPA`.
- Delta reading: outside current repo scope if the scope remains limited to `light`, `cover`, `switch`, `sensor`, `binary_sensor`, `button`.
- Best probable HA target: `climate`.
- Confidence: high.

### 2. House alarm

- Observed Homebridge family: `Alarme maison`.
- Delta reading: outside current repo scope.
- Best probable HA target: `alarm_control_panel`.
- Confidence: high.

### 3. HomeKit scenarios historically exposed as switches

- Observed Homebridge family: `Tout eteindre`, `ambiance cinema`, `ambiance coucher`, `Ambiance lumineuse`, `Lumieres terrasse`.
- Delta reading: functionally this is the clearest useful gap if the product goal is to recover visible Maison/Siri shortcuts inside HA.
- Best probable HA target: `button` rather than `switch`, even if the historical HomeKit shape used a switch metaphor.
- Confidence: high.

### 4. Composite domain accessories without a clear 1:1 equivalence

- `IQ EV`: observed on Homebridge after refactor as a single accessory mixing state and direct charger actions.
- `SPA`: observed on Homebridge as a composite accessory with multi-switch behavior, while `Thermostat SPA` exists separately.
- Delta reading: not necessarily missing HA entities, but not yet a clear business/UX equivalence inside the current scope.
- Best probable HA target: mix of `switch` + `sensor` / `binary_sensor`, with possible `climate` for SPA thermostat and possible `number` / `select` only when a real setpoint or mode distinction matters.
- Confidence: medium.

## Explicit Exclusions

- Annex Homebridge platforms outside `jeedom2ha` scope:
  - `Camera-ffmpeg` / RTSP cameras
  - `SamsungTizen`
  - `homebridge-alexa`
  - `homebridge-gsh`
- Apple-side surfaces derived from those platforms must not be counted as a `jeedom2ha` backlog gap.
- Also deprioritized for `pe-epic-10` first-wave purposes even if historically visible in Homebridge:
  - `airport`
  - `Internet`
  - `ampli`
  - `imprimante`
  - other low-value network / household monitoring surfaces

## Ambiguous Or Sensitive Zones

- `Portail`: likely `cover`, but the right HA projection depends on modeling authority between business virtuals and source devices.
- `Présence`, `Présence Alex`, `Présence Arthur`, `Présence Margaux`, `Présence Melanie`: technically close to `binary_sensor`, but sensitive enough that they should not be opened cosmetically without product intent.
- `Passerelle Enphase / Solaire disponible` and `Chauffe-eau / Routage reel`: Homebridge apparently publishes these in a form that can resemble read-only outlets; on the HA side the natural landing may be `sensor` or `switch` depending on product intent.
- Several historical Homebridge virtuals changed during the late-May cleanup, so family-level language is safer than hard equipment cardinalities for planning artifacts.

## Short Delta Reading

- Already well covered by current HA scope:
  - lighting
  - shutters / awnings / covers
  - simple plugs and switches
  - measurement sensors
  - openings and binary states
- Still outside scope or not yet truly equivalent:
  - thermostats -> `climate`
  - house alarm -> `alarm_control_panel`
  - HomeKit scenarios -> probable `button`
  - composite business accessories such as `IQ EV` and `SPA`

## Planning Readout For `pe-epic-10`

### Recommended sequencing from this transmitted audit summary

1. Priority wave 1:
   - consolidate the representative inventory already covered by `light`, `cover`, `switch`, `sensor`, `binary_sensor`
   - explicitly verify and, if needed, complete the HomeKit scenario path through `button`
2. Priority wave 2:
   - open `climate`
3. Priority wave 3:
   - evaluate `alarm_control_panel`
   - evaluate composite business UX equivalence for `IQ EV` and `SPA`

### Practical product reading

The most useful near-term gap is not necessarily broad new type opening first; it is the visible recovery of the **5 HomeKit scenarios** because they map closely to Home/Siri daily usage and appear to land cleanly in `button` without forcing immediate expansion into all thermostat or alarm cases.
