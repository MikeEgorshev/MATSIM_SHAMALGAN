#!/usr/bin/env python3
"""
Plot the generated assumed PT network (routes + stops) for quick visual QA.

Inputs:
- scenarios/shamalgan/network-with-pt.xml
- scenarios/shamalgan/transitSchedule.xml

Output:
- analysis-artifacts/pt-data/assumed_pt_network_map.png
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "scenarios" / "shamalgan" / "network-with-pt.xml"
SCHEDULE = ROOT / "scenarios" / "shamalgan" / "transitSchedule.xml"
OUT = ROOT / "analysis-artifacts" / "pt-data" / "assumed_pt_network_map.png"


def read_network_links(path: Path):
    tree = ET.parse(path)
    root = tree.getroot()
    nodes = {}
    for n in root.findall(".//node"):
        nodes[n.attrib["id"]] = (float(n.attrib["x"]), float(n.attrib["y"]))
    links = []
    for l in root.findall(".//link"):
        fr = nodes.get(l.attrib["from"])
        to = nodes.get(l.attrib["to"])
        if fr and to:
            links.append((l.attrib["id"], fr, to))
    return links


def read_schedule(path: Path):
    tree = ET.parse(path)
    root = tree.getroot()
    facilities = {}
    for s in root.findall("./transitStops/stopFacility"):
        facilities[s.attrib["id"]] = (float(s.attrib["x"]), float(s.attrib["y"]), s.attrib.get("name", ""))

    routes = []
    for line in root.findall("./transitLine"):
        line_id = line.attrib["id"]
        for route in line.findall("./transitRoute"):
            route_id = route.attrib["id"]
            stop_refs = [st.attrib["refId"] for st in route.findall("./routeProfile/stop")]
            coords = [facilities[r][:2] for r in stop_refs if r in facilities]
            routes.append((line_id, route_id, stop_refs, coords))
    return facilities, routes


def main() -> None:
    links = read_network_links(NETWORK)
    facilities, routes = read_schedule(SCHEDULE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 8))

    # Background road+pt links in light gray.
    for _, fr, to in links:
        plt.plot([fr[0], to[0]], [fr[1], to[1]], color="#c8c8c8", linewidth=0.45, alpha=0.35)

    colors = ["#00695c", "#c62828", "#1565c0", "#6a1b9a"]
    for idx, (line_id, route_id, _, coords) in enumerate(routes):
        if len(coords) < 2:
            continue
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        color = colors[idx % len(colors)]
        plt.plot(xs, ys, color=color, linewidth=2.2, alpha=0.95, label=f"{line_id}:{route_id}")
        plt.scatter(xs, ys, s=22, color=color, edgecolors="white", linewidths=0.4, zorder=4)

    plt.title("Shamalgan Assumed PT Network (Generated)")
    plt.xlabel("X (EPSG:32643)")
    plt.ylabel("Y (EPSG:32643)")
    plt.grid(True, alpha=0.15)
    if routes:
        plt.legend(loc="best", fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT, dpi=180)
    plt.close()

    print(f"Saved: {OUT}")
    print(f"Route count: {len(routes)}")
    print(f"Stop facility count: {len(facilities)}")


if __name__ == "__main__":
    main()
