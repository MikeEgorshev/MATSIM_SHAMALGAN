# Shamalgan Population Assignment Algorithm

This file explains exactly how `population.xml` is generated for Shamalgan.

Main code:
- `src/main/java/org/matsim/project/PrepareShamalganPopulationFromZones.java`

Input data:
- `scenarios/shamalgan/network.xml`
- `original-input-data/shamalgan/zones-derived.csv`

Output data:
- `scenarios/shamalgan/population.xml`

## 1) What is in `zones-derived.csv`

Each row is one zone (small area), with:
- `home_x`, `home_y`, `home_weight`: where people live and how many
- `work_x`, `work_y`, `work_weight`: where jobs/activities are and how many
- `sigma_m`: random spread around the zone center in meters

Example row:

```csv
zone_id,home_x,home_y,home_weight,work_x,work_y,work_weight,sigma_m
z44,632256.211,4803348.856,1146.867,632256.211,4803348.856,1089.524,300
```

Interpretation:
- Zone `z44` has a strong home weight (`1146.867`), so it is picked often as a home zone.
- People are not placed at exactly one point; they are spread around it with `sigma_m=300`.

## 2) How many agents are created

If you do not pass `agentCount` as the 4th argument, code uses:
- `agentCount = round(sum(home_weight))`
- then clamps to `[500, 100000]`

In your current Shamalgan data this became about `30481` agents.

You can override manually:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganPopulationFromZones" "-Dexec.args=scenarios/shamalgan/network.xml original-input-data/shamalgan/zones-derived.csv scenarios/shamalgan/population.xml 20000"
```

## 3) For each person, what happens

For each synthetic person:
1. Pick one home zone with weighted random by `home_weight`.
2. Pick one work/other zone with weighted random by `work_weight`.
3. Decide if employed:
   - probability = `EMPLOYED_SHARE` (currently `0.65`)
4. Draw fixed mode for the plan:
   - `car` with `CAR_MODE_SHARE` (currently `0.55`)
   - `pt` with `PT_MODE_SHARE` (currently `0.25`)
   - otherwise `walk`
5. Add random coordinate jitter around selected zone center:
   - approximately Gaussian with standard spread from `sigma_m`
6. Snap coordinates to nearest network links in `network.xml`.
7. Build plan:
   - employed: `home -> work -> home`
   - not employed: `home -> other -> home`
8. Add person to MATSim population.

## 4) Time generation logic

Times are randomized to avoid all agents moving at one second.

Employed agents:
- home end: `07:00` to `08:59`
- work end: `16:00` to `18:59`

Non-employed agents:
- home end: `10:00` to `14:59`
- other end: `12:00` to `19:59`

## 5) Why mode share may stay constant across iterations

In this setup, each person gets one mode when plans are generated.  
If replanning strategy does not include mode-change modules, mode split stays almost fixed.

That is why you saw stable shares like:
- car ~55%
- pt ~25%
- walk ~20%

## 6) Where to tune parameters

Edit in:
- `src/main/java/org/matsim/project/PrepareShamalganPopulationFromZones.java`

User parameters:
- `EMPLOYED_SHARE`
- `CAR_MODE_SHARE`
- `PT_MODE_SHARE`
- `RANDOM_SEED`

Zone derivation parameters (upstream):
- `tools/derive_shamalgan_zones.py`
  - `ZONE_COLS`, `ZONE_ROWS`
  - `WORK_SHARE`
  - raster/map paths

## 7) Recommended workflow

1. Re-derive zones from raster + OSM:

```powershell
python tools\derive_shamalgan_zones.py
```

2. Rebuild network (if OSM changed):

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganNetwork" "-Dexec.args=original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643"
```

3. Regenerate population:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganPopulationFromZones" "-Dexec.args=scenarios/shamalgan/network.xml original-input-data/shamalgan/zones-derived.csv scenarios/shamalgan/population.xml"
```

4. Run scenario:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan"
```
