# MATSim Example PT Baselines Used for Shamalgan Assumptions

Source dataset:
- `org.matsim:matsim-examples:2025.0`
- schedules sampled from:
  - `pt-simple/transitschedule.xml`
  - `pt-simple-lineswitch/transitschedule.xml`
  - `pt-tutorial/transitschedule.xml`
  - `siouxfalls-2014/Siouxfalls_transitSchedule.xml`
  - `ptdisturbances/schedule_wo-disturbance.xml`

Computed from those example schedules:
- headway samples: `2328`
- mean headway: `365.72 sec` (rounded to `360 sec` for Shamalgan)
- median headway: `300 sec`
- median first departure: `06:00:00`
- median last departure: `22:55:00` (rounded to `23:00:00`)

Shamalgan assumed PT defaults chosen:
- bus speed: `30 km/h` (user assumption)
- dwell at stop: `60 sec` (user assumption)
- headway: `360 sec` (example-derived mean, rounded)
- service window: `06:00:00` to `23:00:00` (example-derived medians)
