# Shamalgan Real PT Integration Plan

This plan starts from the currently working car + mode-labeled-pt baseline and upgrades to real MATSim transit operations.

## Phase 0: Baseline verification (completed 2026-02-24)

- `mvnw -DskipTests compile` passes.
- `RunShamalgan --simwrapper` runs end-to-end.
- Current run still has no transit schedule/vehicles in config.

## Phase 1: GTFS conversion pipeline (implemented)

- Added `org.matsim.project.PrepareShamalganTransitFromGtfs`.
- Inputs:
  - GTFS zip (`WGS84`)
  - existing Shamalgan road network
  - service date (`yyyy-mm-dd`)
- Outputs:
  - `scenarios/shamalgan/network-with-pt.xml`
  - `scenarios/shamalgan/transitSchedule.xml`
  - `scenarios/shamalgan/transitVehicles.xml`
- Added starter PT config:
  - `scenarios/shamalgan/config-pt.xml`

## Phase 2: First real-PT run (next action)

1. Place GTFS at `original-input-data/shamalgan/gtfs/shamalgan-gtfs.zip`.
2. Run converter command from `scenarios/shamalgan/README.md`.
3. Run:
   - `RunShamalgan scenarios/shamalgan/config-pt.xml --simwrapper`
4. Validate:
   - transit schedule + vehicles loaded in logs
   - non-zero PT boardings/trips in output analysis

## Phase 3: Behavioral realism improvements

1. Add mode-choice replanning (currently fixed mode assignment in population generation).
2. Tune PT scoring and transfer penalties for realistic mode split.
3. Add access/egress handling improvements if needed.

## Phase 4: Calibration and reporting

1. Compare simulated PT ridership vs observed benchmarks.
2. Compare travel times by corridor.
3. Build dedicated Shamalgan SimWrapper PT dashboards.
