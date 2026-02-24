# Reference PT Defaults Used for Shamalgan Bootstrap

Collected from:

1. `matsim-scenarios/matsim-lausitz`
   - commit: `b45d8f4d78c42be51e1a23a0b6441c7df49efe8c`
   - file: `input/v2024.2/lausitz-v2024.2-10pct.config.xml`
2. `matsim-scenarios/matsim-dresden`
   - commit: `81daefb5e868862e69ac416154b70cec2d920ba2`
   - file: `input/v1.0/dresden-v1.0-10pct.config.xml`

## Shared defaults in both references

- `transit.useTransit = true`
- `transit.transitScheduleFile = <set>`
- `transit.vehiclesFile = <set>`
- `transitRouter.extensionRadius = 500.0`
- `transitRouter.directWalkFactor = 1.0`
- `transitRouter.maxBeelineWalkConnectionDistance = 300.0`

These values were copied into Shamalgan PT bootstrap config and docs.
