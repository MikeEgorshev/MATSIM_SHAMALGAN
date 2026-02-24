# GTFS input for Shamalgan PT

Put GTFS zip files here, for example:

- `shamalgan-gtfs.zip`

Expected GTFS core files inside the zip:

- `stops.txt`
- `routes.txt`
- `trips.txt`
- `stop_times.txt`
- `calendar.txt` and/or `calendar_dates.txt`

Then run conversion from project root:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromGtfs" "-Dexec.args=original-input-data/shamalgan/gtfs/shamalgan-gtfs.zip scenarios/shamalgan/network.xml scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 2026-02-01 mergeStopsAtSameCoord false"
```
