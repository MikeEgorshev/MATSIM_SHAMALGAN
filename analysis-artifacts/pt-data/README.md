# Shamalgan PT Data Staging

This folder stores transit-related datasets extracted from current sources.

## OSM bus stops

Generated from:
- `original-input-data/shamalgan/map`

Generator script:
- `tools/extract_shamalgan_bus_stops.py`

Outputs:
- `osm_bus_stops.csv`
- `osm_bus_stops.geojson`
- `osm_filtered_train_like_stops.csv`
- `osm_bus_stops_map.png`
- `osm_pt_stop_screening_summary.csv`
- `assumed_pt_network_map.png`

Run from project root:

```powershell
python tools\extract_shamalgan_bus_stops.py
```

## Notes

- Included stops are selected from OSM tags (`highway=bus_stop`, `public_transport=*`, `amenity=bus_station`, `bus=yes`).
- Train-like stops are filtered out unless clearly bus-tagged.
- This is a geometry inventory only; no route topology, timetable, or headway is inferred.

## Assumed PT visualization

Generate PT network infographic from produced schedule/network:

```powershell
python tools\plot_assumed_pt_network.py
```
