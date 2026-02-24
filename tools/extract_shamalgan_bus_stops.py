#!/usr/bin/env python3
"""
Extract bus stop candidates from OSM XML map for Shamalgan.

This script explicitly filters out train-like stops unless they are
also clearly tagged as bus stops.

Inputs:
- original-input-data/shamalgan/map

Outputs:
- analysis-artifacts/pt-data/osm_bus_stops.csv
- analysis-artifacts/pt-data/osm_bus_stops.geojson
- analysis-artifacts/pt-data/osm_filtered_train_like_stops.csv
- analysis-artifacts/pt-data/osm_bus_stops_map.png
- analysis-artifacts/pt-data/osm_pt_stop_screening_summary.csv
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OSM_PATH = ROOT / "original-input-data" / "shamalgan" / "map"
OUT_DIR = ROOT / "analysis-artifacts" / "pt-data"
CSV_OUT = OUT_DIR / "osm_bus_stops.csv"
GEOJSON_OUT = OUT_DIR / "osm_bus_stops.geojson"
FILTERED_OUT_CSV = OUT_DIR / "osm_filtered_train_like_stops.csv"
MAP_OUT = OUT_DIR / "osm_bus_stops_map.png"
SUMMARY_CSV = OUT_DIR / "osm_pt_stop_screening_summary.csv"


def parse_tags(elem: ET.Element) -> dict[str, str]:
    tags: dict[str, str] = {}
    for t in elem.findall("tag"):
        k = t.attrib.get("k")
        v = t.attrib.get("v")
        if k and v:
            tags[k] = v
    return tags


def is_train_like(tags: dict[str, str]) -> bool:
    railway = tags.get("railway", "")
    if railway in {"station", "halt", "tram_stop", "stop"}:
        return True
    if tags.get("train") == "yes":
        return True
    if tags.get("station") in {"train", "subway", "light_rail"}:
        return True
    if tags.get("public_transport") == "station" and tags.get("bus") != "yes":
        return True
    return False


def is_bus_stop(tags: dict[str, str]) -> bool:
    if tags.get("highway") == "bus_stop":
        return True
    if tags.get("amenity") == "bus_station":
        return True
    if tags.get("bus") == "yes":
        return True
    if tags.get("public_transport") in {"platform", "stop_position"} and not is_train_like(tags):
        return True
    return False


def centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    lon = sum(p[0] for p in points) / len(points)
    lat = sum(p[1] for p in points) / len(points)
    return lon, lat


def collect_highway_lines(root: ET.Element, nodes: dict[str, tuple[float, float]]) -> list[list[tuple[float, float]]]:
    lines: list[list[tuple[float, float]]] = []
    for w in root.findall("way"):
        tags = parse_tags(w)
        if "highway" not in tags:
            continue
        refs = [nd.attrib.get("ref", "") for nd in w.findall("nd")]
        pts = [nodes[r] for r in refs if r in nodes]
        if len(pts) >= 2:
            lines.append(pts)
    return lines


def write_screening_summary(included_count: int, excluded_count: int) -> None:
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["included_bus_stops", "filtered_train_like_stops"])
        w.writerow([included_count, excluded_count])


def plot_map(
    roads: list[list[tuple[float, float]]],
    included: list[dict[str, str | float]],
    excluded: list[dict[str, str | float]],
) -> None:
    plt.figure(figsize=(12, 8))
    for line in roads:
        xs = [p[0] for p in line]
        ys = [p[1] for p in line]
        plt.plot(xs, ys, color="#b0b0b0", linewidth=0.7, alpha=0.55)

    if included:
        plt.scatter(
            [r["lon"] for r in included],
            [r["lat"] for r in included],
            s=38,
            c="#00897b",
            marker="o",
            edgecolors="white",
            linewidths=0.4,
            label=f"Included bus stops ({len(included)})",
            zorder=3,
        )
    if excluded:
        plt.scatter(
            [r["lon"] for r in excluded],
            [r["lat"] for r in excluded],
            s=42,
            c="#ef6c00",
            marker="x",
            linewidths=1.2,
            label=f"Filtered train-like stops ({len(excluded)})",
            zorder=4,
        )

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Shamalgan PT Stops Screening from OSM Map")
    plt.legend(loc="best")
    plt.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(MAP_OUT, dpi=180)
    plt.close()


def main() -> None:
    tree = ET.parse(OSM_PATH)
    root = tree.getroot()

    nodes: dict[str, tuple[float, float]] = {}
    for n in root.findall("node"):
        nid = n.attrib.get("id")
        if nid is None:
            continue
        nodes[nid] = (float(n.attrib["lon"]), float(n.attrib["lat"]))

    records: list[dict[str, str | float]] = []
    filtered_out: list[dict[str, str | float]] = []
    roads = collect_highway_lines(root, nodes)

    for n in root.findall("node"):
        tags = parse_tags(n)
        if not is_bus_stop(tags):
            if is_train_like(tags):
                filtered_out.append(
                    {
                        "osm_type": "node",
                        "osm_id": n.attrib.get("id", ""),
                        "name": tags.get("name", ""),
                        "lon": float(n.attrib["lon"]),
                        "lat": float(n.attrib["lat"]),
                        "highway": tags.get("highway", ""),
                        "public_transport": tags.get("public_transport", ""),
                        "amenity": tags.get("amenity", ""),
                        "railway": tags.get("railway", ""),
                        "bus": tags.get("bus", ""),
                        "filter_reason": "train_like_not_bus",
                    }
                )
            continue
        rec = {
            "osm_type": "node",
            "osm_id": n.attrib.get("id", ""),
            "name": tags.get("name", ""),
            "lon": float(n.attrib["lon"]),
            "lat": float(n.attrib["lat"]),
            "highway": tags.get("highway", ""),
            "public_transport": tags.get("public_transport", ""),
            "amenity": tags.get("amenity", ""),
            "railway": tags.get("railway", ""),
            "bus": tags.get("bus", ""),
        }
        records.append(rec)

    for w in root.findall("way"):
        tags = parse_tags(w)
        if not is_bus_stop(tags):
            if is_train_like(tags):
                refs = [nd.attrib.get("ref", "") for nd in w.findall("nd")]
                pts = [nodes[r] for r in refs if r in nodes]
                if pts:
                    lon, lat = centroid(pts)
                    filtered_out.append(
                        {
                            "osm_type": "way",
                            "osm_id": w.attrib.get("id", ""),
                            "name": tags.get("name", ""),
                            "lon": lon,
                            "lat": lat,
                            "highway": tags.get("highway", ""),
                            "public_transport": tags.get("public_transport", ""),
                            "amenity": tags.get("amenity", ""),
                            "railway": tags.get("railway", ""),
                            "bus": tags.get("bus", ""),
                            "filter_reason": "train_like_not_bus",
                        }
                    )
            continue
        refs = [nd.attrib.get("ref", "") for nd in w.findall("nd")]
        pts = [nodes[r] for r in refs if r in nodes]
        if not pts:
            continue
        lon, lat = centroid(pts)
        rec = {
            "osm_type": "way",
            "osm_id": w.attrib.get("id", ""),
            "name": tags.get("name", ""),
            "lon": lon,
            "lat": lat,
            "highway": tags.get("highway", ""),
            "public_transport": tags.get("public_transport", ""),
            "amenity": tags.get("amenity", ""),
            "railway": tags.get("railway", ""),
            "bus": tags.get("bus", ""),
        }
        records.append(rec)

    seen: set[tuple[str, str]] = set()
    dedup: list[dict[str, str | float]] = []
    for r in records:
        key = (str(r["osm_type"]), str(r["osm_id"]))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    filtered_out.sort(key=lambda x: (str(x["name"]), str(x["osm_type"]), str(x["osm_id"])))
    dedup.sort(key=lambda x: (str(x["name"]), str(x["osm_type"]), str(x["osm_id"])))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fields = [
        "osm_type",
        "osm_id",
        "name",
        "lon",
        "lat",
        "highway",
        "public_transport",
        "amenity",
        "railway",
        "bus",
    ]
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in dedup:
            w.writerow(row)

    filtered_fields = fields + ["filter_reason"]
    with FILTERED_OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=filtered_fields)
        w.writeheader()
        for row in filtered_out:
            w.writerow(row)

    features = []
    for r in dedup:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [r["lon"], r["lat"]],
                },
                "properties": {
                    "osm_type": r["osm_type"],
                    "osm_id": r["osm_id"],
                    "name": r["name"],
                    "highway": r["highway"],
                    "public_transport": r["public_transport"],
                    "amenity": r["amenity"],
                    "bus": r["bus"],
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}
    GEOJSON_OUT.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")

    write_screening_summary(len(dedup), len(filtered_out))
    plot_map(roads, dedup, filtered_out)

    print(f"Included bus stop candidates: {len(dedup)}")
    print(f"Filtered train-like stops: {len(filtered_out)}")
    print(f"CSV: {CSV_OUT}")
    print(f"GeoJSON: {GEOJSON_OUT}")
    print(f"Filtered-out CSV: {FILTERED_OUT_CSV}")
    print(f"Screening map: {MAP_OUT}")
    print(f"Summary: {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
