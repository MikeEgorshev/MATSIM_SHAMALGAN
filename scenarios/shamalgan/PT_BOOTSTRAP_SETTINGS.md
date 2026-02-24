# Shamalgan PT Bootstrap Settings

This file documents PT defaults copied from established MATSim scenario repos and adapted for Shamalgan.

Reference configs inspected:
- `analysis-artifacts/reference-matsim/matsim-lausitz/input/v2024.2/lausitz-v2024.2-10pct.config.xml`
- `analysis-artifacts/reference-matsim/matsim-dresden/input/v1.0/dresden-v1.0-10pct.config.xml`

## Copied defaults (core)

- `transit.useTransit = true`
- `transit.transitModes = pt`
- `transit.routingAlgorithmType = SwissRailRaptor`
- `transitRouter.extensionRadius = 500.0`
- `transitRouter.directWalkFactor = 1.0`
- `transitRouter.maxBeelineWalkConnectionDistance = 300.0`
- `transitRouter.searchRadius = 1000.0`
- `qsim.useTransit = true`
- `transitRouter.additionalTransferTime = 120.0` (added for conservative transfer friction)

## Mode-choice activation (critical)

Without mode-choice replanning, PT shares stay mostly fixed from initial plans.

For Shamalgan PT test config (`config-pt.xml`), enable:

- `replanning.strategy = SubtourModeChoice` with non-zero weight
- `subtourModeChoice.modes = car,pt,walk`
- `subtourModeChoice.chainBasedModes = car`

## Starting coefficients used in Shamalgan PT test config

- Car:
  - `constant = 0.0`
  - `monetaryDistanceRate = -0.00025`
- PT:
  - `constant = -0.8`
  - `marginalUtilityOfTraveling_util_hr = 0.0`
- Walk:
  - `constant = -1.4`
  - `marginalUtilityOfTraveling_util_hr = 0.0`

These are conservative startup values inspired by dresden/lausitz style mode constants, then simplified for this small-data context.

## Why these values

- They are conservative defaults used in production-grade MATSim scenario repos.
- They avoid over-optimistic transfers and ensure stop search is not too narrow.
- They are suitable as a starting point until local PT observations are available.

## Limitation

These settings do not create transit service by themselves. You still need:
- `transitSchedule.xml`
- `transitVehicles.xml`
- routes/departures (typically from GTFS or manually curated data)
