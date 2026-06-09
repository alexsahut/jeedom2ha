# Homebridge Field Inventory Request - 2026-06-07

status: superseded
date: 2026-06-07
requested_agent: clawbox
request_channel: OpenClaw agent session
blocking_error: "agent not found: clawbox"
scope: homebridge-published-field-inventory
superseded_by: homebridge-homekit-vs-ha-delta-2026-06-07.md

## Purpose

Persist the field-inventory request for the Homebridge surface currently published on the target box, so PE Epic 10 scope can be grounded in real terrain data instead of inferred scope.

## Attempt Recorded

On 2026-06-07, `clawcode` attempted to contact agent `clawbox` through OpenClaw session routing with this intent:

- retrieve the list of active Homebridge plugins/platforms;
- retrieve the accessory/service types actually exposed on the box;
- capture obvious Jeedom generic type correspondences when available;
- list exclusions, disabled areas, and uncertainty zones;
- return a repo-ready summary.

The runtime returned:

```text
agent not found: clawbox
```

## Expected Inventory Shape

When `clawbox` becomes reachable, the returned inventory should be recorded here or superseded by a dated sibling artifact containing at minimum:

1. active Homebridge plugins/platforms;
2. effective accessory/service inventory exposed to HomeKit;
3. optional mapping hints toward Jeedom generic families;
4. exclusions, disabled integrations, and ambiguous cases;
5. provenance notes describing how the inventory was collected.

## Impact On Planning

- `sprint-change-proposal-2026-06-07.md` remains valid on its core point: PE Epic 10 needs a field-inventory prefix step before scope freeze.
- This blocked request is now superseded by a dated sibling artifact containing the audit summary transmitted by `ClawBox`.
- Immediate PE Epic 10 sequencing can now rely on that transmitted summary, while keeping prudence on ambiguous families and non-live cardinalities.

## Next Viable Moves

1. Use the superseding artifact as the current planning input for `pe-epic-10`.
2. Materialize the chosen wave in active BMAD artifacts once Alexandre validates the sequencing.
3. If needed later, replace the summary-level inventory with a stricter equipment-by-equipment snapshot.
