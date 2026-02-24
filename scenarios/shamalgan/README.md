# Shamalgan Scenario

This scenario is prepared for Shamalgan (Almaty region).

## 1) Put OSM file

Copy your OpenStreetMap extract here, for example:

- `original-input-data/shamalgan/Shamalgan.osm`
- `original-input-data/shamalgan/map` (your newer, larger extract)

## 2) Convert OSM to MATSim network

Run from project root:

```powershell
.\mvnw.cmd -q -DskipTests compile
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganNetwork" "-Dexec.args=original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643"
```

Alternative in IntelliJ:

- Run main class `org.matsim.project.PrepareShamalganNetwork`
- Program arguments:
  - `original-input-data/shamalgan/Shamalgan.osm scenarios/shamalgan/network.xml EPSG:32643`
  - (recommended now) `original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643`

## 3) Create population (plans)

Option A: quick synthetic population (no zones)

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganPopulation" "-Dexec.args=scenarios/shamalgan/network.xml scenarios/shamalgan/population.xml"
```

Edit variables in:

- `src/main/java/org/matsim/project/PrepareShamalganPopulation.java`

Option B: zone-weighted population (TAZ-like)

1. Prepare zone CSV based on:
   - `original-input-data/shamalgan/zones-template.csv`
2. Run:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganPopulationFromZones" "-Dexec.args=scenarios/shamalgan/network.xml original-input-data/shamalgan/zones-derived.csv scenarios/shamalgan/population.xml"
```

Edit variables in:

- `src/main/java/org/matsim/project/PrepareShamalganPopulationFromZones.java`
- optional 4th argument `agentCount` overrides auto-inferred population size
- detailed algorithm explanation:
  - `scenarios/shamalgan/POPULATION_ALGORITHM.md`

## 4) Run MATSim

From project root:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan"
```

or run the main class `org.matsim.project.RunShamalgan` in IntelliJ.

Optional flags:

- add `--otfvis` to show live OTFVis window
- add `--simwrapper` to create SimWrapper outputs

Example:

```powershell
.\mvnw.cmd exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=--otfvis --simwrapper"
```

## 5) Add real PT from GTFS (new)

1. Place your GTFS zip at:
   - `original-input-data/shamalgan/gtfs/shamalgan-gtfs.zip`
2. Convert GTFS to MATSim transit files and create a PT-augmented network:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromGtfs" "-Dexec.args=original-input-data/shamalgan/gtfs/shamalgan-gtfs.zip scenarios/shamalgan/network.xml scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 2026-02-01 mergeStopsAtSameCoord false"
```

3. Run with PT-enabled config:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=scenarios/shamalgan/config-pt.xml --simwrapper"
```

## 6) Build assumed PT supply from mapped bus stops (no GTFS)

Use this when GTFS is unavailable. It creates:
- `scenarios/shamalgan/network-with-pt.xml`
- `scenarios/shamalgan/transitSchedule.xml`
- `scenarios/shamalgan/transitVehicles.xml`

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromAssumptions" "-Dexec.args=scenarios/shamalgan/network.xml analysis-artifacts/pt-data/osm_bus_stops.csv scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 30 60 360 06:00:00 23:00:00"
```

Assumption provenance and baseline stats:
- `analysis-artifacts/pt-data/MATSIM_EXAMPLE_PT_BASELINES.md`

## 7) Extract OSM bus stops (current trusted PT geometry source)

Run from project root:

```powershell
python tools\extract_shamalgan_bus_stops.py
```

Outputs:
- `analysis-artifacts/pt-data/osm_bus_stops.csv`
- `analysis-artifacts/pt-data/osm_bus_stops.geojson`

Reference PT bootstrap defaults:
- `scenarios/shamalgan/PT_BOOTSTRAP_SETTINGS.md`

Important for PT usage checks:
- `scenarios/shamalgan/config-pt.xml` includes `SubtourModeChoice` and transfer penalty (`additionalTransferTime=120`) so PT share can adapt during iterations.

## 8) Export/share final scenario

Minimum files to share for a car-only starter scenario:

- `scenarios/shamalgan/config.xml`
- `scenarios/shamalgan/network.xml`
- `scenarios/shamalgan/population.xml`

If you add facilities/transit/vehicles/counts modules later, include those files too and reference them in `config.xml`.
