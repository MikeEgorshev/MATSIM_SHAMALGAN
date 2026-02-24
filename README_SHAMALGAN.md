# Shamalgan Migration (from matsim-example-project)

This repository now contains your Shamalgan scenario migrated into the MATSim scenario-template codebase.

## Migrated paths

- `scenarios/shamalgan/*`
- `original-input-data/shamalgan/*`
- `src/main/java/org/matsim/project/*`
- `tools/derive_shamalgan_zones.py`
- `analysis-artifacts/zone-derivation/*`

## Run commands

From this repository root:

```powershell
.\mvnw.cmd -q -DskipTests compile
```

Create network from OSM:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganNetwork" "-Dexec.args=original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643"
```

Create population from derived zones:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganPopulationFromZones" "-Dexec.args=scenarios/shamalgan/network.xml original-input-data/shamalgan/zones-derived.csv scenarios/shamalgan/population.xml"
```

Run scenario:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan"
```

Run with SimWrapper dashboards:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=--simwrapper"
```

Prepare real PT inputs from GTFS (schedule + vehicles + PT-augmented network):

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromGtfs" "-Dexec.args=original-input-data/shamalgan/gtfs/shamalgan-gtfs.zip scenarios/shamalgan/network.xml scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 2026-02-01 mergeStopsAtSameCoord false"
```

Build assumed PT inputs from mapped OSM bus stops (when GTFS is unavailable):

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromAssumptions" "-Dexec.args=scenarios/shamalgan/network.xml analysis-artifacts/pt-data/osm_bus_stops.csv scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 30 60 360 06:00:00 23:00:00"
```

Run PT-enabled scenario:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=scenarios/shamalgan/config-pt.xml --simwrapper"
```

Extract bus stop candidates from OSM map:

```powershell
python tools\extract_shamalgan_bus_stops.py
```

Archive old run outputs (keeps newest output folder by default):

```powershell
powershell -ExecutionPolicy Bypass -File tools\archive_outputs.ps1 -KeepLatest 1
```

## Notes

- Default `main.class` in `pom.xml` is now `org.matsim.project.RunShamalgan`.
- This template repository also still contains Gunma code. Your Shamalgan run path is separate and does not depend on Gunma classes.
- `config-pt.xml` is a starter config for real transit once GTFS is converted.
- PT bootstrap defaults are documented in `scenarios/shamalgan/PT_BOOTSTRAP_SETTINGS.md`.
- Example-derived PT assumption baselines are documented in `analysis-artifacts/pt-data/MATSIM_EXAMPLE_PT_BASELINES.md`.
