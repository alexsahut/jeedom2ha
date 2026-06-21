# Story 10.1 — Classification terrain des 5 scenarios HomeKit (2026-06-09)

## Contexte de preuve

- Source cible canonique: `_bmad-output/planning-artifacts/pe-epic-10-perimetre-prefixe-2026-06-08.md`
- Gate terrain execute via:
  - `./scripts/deploy-to-box.sh --dry-run`
  - `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
- Captures runtime (box reelle):
  - `_bmad-output/implementation-artifacts/10-1-system-diagnostics-2026-06-09.json`
  - `_bmad-output/implementation-artifacts/10-1-system-published-scope-2026-06-09.json`

## Regle de classification appliquee

- `deja correctement couvert via button`: scenario retrouve dans diagnostics (`/system/diagnostics`) avec `ha_type=button` et statut actionnable.
- `partiellement couvert`: scenario retrouve, mais non publie ou incomplet (reason_code stable de blocage).
- `non couvert`: scenario introuvable dans la topologie/diagnostics runtime apres cycle sync complet.
- `hors-scope-sync-eqlogic`: scenario Jeedom existant confirme, mais non charge par le pipeline runtime car la sync ne couvre que `eqLogic::all()` (pas `scenario::all()`).

## Resultat de classification (AC1)

| Scenario cible (audit Homebridge) | Statut 10.1 | Preuve runtime | Raison stable |
|---|---|---|---|
| `Tout eteindre` | hors-scope-sync-eqlogic | absent de `payload.equipments[].name` + verification Jeedom: scenario existe sous `Tout éteindre` (id=20) | `scenario_objet_jeedom_hors_sync_eqlogic` |
| `ambiance cinema` | hors-scope-sync-eqlogic | absent de `payload.equipments[].name` + verification Jeedom: scenario id=38 | `scenario_objet_jeedom_hors_sync_eqlogic` |
| `ambiance coucher` | hors-scope-sync-eqlogic | absent de `payload.equipments[].name` + verification Jeedom: scenario id=50 | `scenario_objet_jeedom_hors_sync_eqlogic` |
| `Ambiance lumineuse` | hors-scope-sync-eqlogic | absent de `payload.equipments[].name` + verification Jeedom: scenario id=57 | `scenario_objet_jeedom_hors_sync_eqlogic` |
| `Lumieres terrasse` | hors-scope-sync-eqlogic | absent de `payload.equipments[].name` + verification Jeedom: scenario existe sous `Lumières terrasse` (id=150) | `scenario_objet_jeedom_hors_sync_eqlogic` |

## Mapping ancien nom -> nom actuel (verification Jeedom)

- `Tout eteindre` -> `Tout éteindre` (scenario id 20)
- `Lumieres terrasse` -> `Lumières terrasse` (scenario id 150)
- `ambiance cinema` -> inchangé (scenario id 38)
- `ambiance coucher` -> inchangé (scenario id 50)
- `Ambiance lumineuse` -> inchangé (scenario id 57)

## Lecture produit (AC3)

- Les 5 scenarios historiques HomeKit existent cote Jeedom (verification terrain complementaire) mais restent absents du runtime 10.1 car ils sont des objets `scenario` hors pipeline `eqLogic` actuel.
- La raison stable de gate devient `scenario_objet_jeedom_hors_sync_eqlogic` (et non plus une absence metier/suppression).
- La story 10.1 reste bornee au chemin `button` et a la tracabilite: aucun nouveau type HA n'est ouvert.

## Notes complementaires

- Le runtime publie bien des `button` (topics `homeassistant/button/jeedom2ha_*/config`) mais aucun des 5 scenarios n'apparait dans diagnostics/topologie courante car la sync s'appuie sur `eqLogic::all()`.
- Verification Jeedom complementaire (ClawBox): ces 5 elements sont des scenarios natifs (`scenario::byId`) et ne passent pas par la collecte `eqLogic` actuelle (`getFullTopology()`), d'ou l'ecart observe.
