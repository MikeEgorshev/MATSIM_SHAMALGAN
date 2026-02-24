# Network QC Report: network-with-pt.xml

## Core Counts
- Nodes: 1,137
- Links: 3,009

## Connectivity
- Weakly connected components: 2
- Largest component nodes: 1,128 (99.21%)
- Links outside largest component: 18
- Dead-end nodes (total degree = 1): 0
- Isolated nodes (in=0,out=0): 0

## Link Attribute Statistics
- Length [m]: min=2.01, p50=104.82, p95=434.92, max=5107.27
- Free speed [m/s]: min=2.78, p50=4.17, p95=8.33, max=22.22
- Capacity [veh/h]: min=300.00, p50=600.00, p95=1000.00, max=10000.00
- Lanes: min=1.00, p50=1.00, p95=1.00, max=2.00

## Allowed Modes (link counts)
- car: 2,991
- pt: 18

## Flagged Issues (counts)
- long_link_gt_5000m: 2

## Output Files
- Issues CSV: `shamalgan-network-with-pt-issues.csv`
- Links outside largest component CSV: `shamalgan-network-with-pt-links_outside_lcc.csv`
- Dead-end nodes CSV: `shamalgan-network-with-pt-dead_end_nodes.csv`
- Isolated nodes CSV: `shamalgan-network-with-pt-isolated_nodes.csv`
