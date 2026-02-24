#!/usr/bin/env python3
"""
Derive zonal home/work weights from a population-density GeoTIFF and an OSM map extent.

Outputs:
- original-input-data/shamalgan/zones-derived.csv
- analysis-artifacts/zone-derivation/04_density_roads_zones_new_map.png
- analysis-artifacts/zone-derivation/05_zone_selection_process_new_map.png
- analysis-artifacts/zone-derivation/summary_new_map.csv

Edit USER VARIABLES below if you want to tune zoning granularity or work-share assumption.
"""

from __future__ import annotations

import csv
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from pyproj import Transformer


# =========================
# USER VARIABLES (edit here)
# =========================
ROOT = Path(__file__).resolve().parents[1]
TIFF_PATH = ROOT / "original-input-data" / "shamalgan" / "kaz_pop_2025_CN_100m_R2025A_v1.tif"
OSM_PATH = ROOT / "original-input-data" / "shamalgan" / "map"
ZONES_OUT = ROOT / "original-input-data" / "shamalgan" / "zones-derived.csv"
ANALYSIS_DIR = ROOT / "analysis-artifacts" / "zone-derivation"

# Number of zone grid cells in lon/lat directions.
ZONE_COLS = 10
ZONE_ROWS = 8

# Workplaces as a simple proportion of home weight.
WORK_SHARE = 0.95

# Max visual clipping for heatmap colors.
HEAT_CLIP = 15.0

# CRS for MATSim network/population coordinates in this project.
TARGET_CRS = "EPSG:32643"


def parse_bounds_from_osm(osm_path: Path) -> tuple[float, float, float, float]:
    tree = ET.parse(osm_path)
    root = tree.getroot()
    bounds = root.find("bounds")
    if bounds is None:
        raise RuntimeError(f"No <bounds> found in OSM file: {osm_path}")
    minlat = float(bounds.attrib["minlat"])
    minlon = float(bounds.attrib["minlon"])
    maxlat = float(bounds.attrib["maxlat"])
    maxlon = float(bounds.attrib["maxlon"])
    return minlon, maxlon, minlat, maxlat


def collect_highway_lines(osm_path: Path) -> list[np.ndarray]:
    tree = ET.parse(osm_path)
    root = tree.getroot()
    nodes = {}
    for n in root.findall("node"):
        nid = n.attrib.get("id")
        if nid is None:
            continue
        nodes[nid] = (float(n.attrib["lon"]), float(n.attrib["lat"]))

    lines = []
    for w in root.findall("way"):
        has_highway = any(
            tag.attrib.get("k") == "highway" for tag in w.findall("tag")
        )
        if not has_highway:
            continue
        pts = []
        for nd in w.findall("nd"):
            ref = nd.attrib.get("ref")
            if ref in nodes:
                pts.append(nodes[ref])
        if len(pts) >= 2:
            lines.append(np.asarray(pts, dtype=float))
    return lines


def geotiff_lonlat_grid(tif_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with tifffile.TiffFile(tif_path) as tif:
        arr = tif.asarray()
        page = tif.pages[0]
        x_scale = page.tags["ModelPixelScaleTag"].value[0]
        y_scale = page.tags["ModelPixelScaleTag"].value[1]
        tie = page.tags["ModelTiepointTag"].value
        x0 = tie[3]
        y0 = tie[4]
        nodata = page.tags["GDAL_NODATA"].value
        nodata = float(nodata) if nodata is not None else -99999.0

    arr = arr.astype(np.float32, copy=False)
    arr[arr <= nodata] = np.nan
    rows, cols = arr.shape

    lons = x0 + (np.arange(cols) + 0.5) * x_scale
    lats = y0 - (np.arange(rows) + 0.5) * y_scale
    return arr, lons, lats


def clip_to_bbox(
    arr: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    minlon: float,
    maxlon: float,
    minlat: float,
    maxlat: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # Crop to bbox index ranges first (fast), then apply finite mask.
    col_idx = np.where((lons >= minlon) & (lons <= maxlon))[0]
    row_idx = np.where((lats >= minlat) & (lats <= maxlat))[0]
    if len(col_idx) == 0 or len(row_idx) == 0:
        raise RuntimeError("No raster cells intersect OSM bounds.")
    c0, c1 = int(col_idx.min()), int(col_idx.max())
    r0, r1 = int(row_idx.min()), int(row_idx.max())
    cropped = arr[r0 : r1 + 1, c0 : c1 + 1]
    lons_c = lons[c0 : c1 + 1]
    lats_c = lats[r0 : r1 + 1]
    return cropped, lons_c, lats_c


def derive_zones(
    pop: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    minlon: float,
    maxlon: float,
    minlat: float,
    maxlat: float,
) -> list[dict]:
    lon_edges = np.linspace(minlon, maxlon, ZONE_COLS + 1)
    lat_edges = np.linspace(minlat, maxlat, ZONE_ROWS + 1)
    tx = Transformer.from_crs("EPSG:4326", TARGET_CRS, always_xy=True)
    zones = []
    znum = 1

    for r in range(ZONE_ROWS):
        for c in range(ZONE_COLS):
            lo0, lo1 = lon_edges[c], lon_edges[c + 1]
            la0, la1 = lat_edges[r], lat_edges[r + 1]
            cols = (lons >= lo0) & (lons < lo1)
            rows = (lats >= la0) & (lats < la1)
            if not np.any(cols) or not np.any(rows):
                znum += 1
                continue

            sub = pop[np.ix_(rows, cols)]
            valid = np.isfinite(sub) & (sub > 0)
            if not np.any(valid):
                znum += 1
                continue
            w = np.where(valid, sub, 0.0)
            sw = float(np.sum(w))
            if sw <= 0:
                znum += 1
                continue

            lons_sel = lons[cols]
            lats_sel = lats[rows]
            lon_w = np.sum(w, axis=0)
            lat_w = np.sum(w, axis=1)
            clon = float(np.sum(lons_sel * lon_w) / sw)
            clat = float(np.sum(lats_sel * lat_w) / sw)
            x, y = tx.transform(clon, clat)

            zone_id = f"z{znum:02d}"
            home = round(sw, 3)
            work = round(sw * WORK_SHARE, 3)
            zones.append(
                {
                    "zone_id": zone_id,
                    "home_x": round(x, 3),
                    "home_y": round(y, 3),
                    "home_weight": home,
                    "work_x": round(x, 3),
                    "work_y": round(y, 3),
                    "work_weight": work,
                    "sigma_m": 300,
                    "lon": clon,
                    "lat": clat,
                }
            )
            znum += 1

    zones.sort(key=lambda z: z["home_weight"], reverse=True)
    return zones


def write_zones_csv(zones: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "zone_id",
        "home_x",
        "home_y",
        "home_weight",
        "work_x",
        "work_y",
        "work_weight",
        "sigma_m",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for z in zones:
            w.writerow({k: z[k] for k in fields})


def save_summary(
    summary_path: Path,
    osm_path: Path,
    minlon: float,
    maxlon: float,
    minlat: float,
    maxlat: float,
    clipped_pop: np.ndarray,
    zones: list[dict],
) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    pop_sum = float(np.nansum(clipped_pop))
    max_hw = max((z["home_weight"] for z in zones), default=0.0)
    mean_hw = float(np.mean([z["home_weight"] for z in zones])) if zones else 0.0
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "source_osm",
                "bbox_minlon",
                "bbox_maxlon",
                "bbox_minlat",
                "bbox_maxlat",
                "bbox_population_estimate",
                "zone_count",
                "max_zone_home_weight",
                "mean_zone_home_weight",
            ]
        )
        w.writerow(
            [
                str(osm_path).replace("\\", "/"),
                minlon,
                maxlon,
                minlat,
                maxlat,
                pop_sum,
                len(zones),
                max_hw,
                mean_hw,
            ]
        )


def plot_reference_like_overlay(
    out_path: Path,
    pop: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    roads: list[np.ndarray],
    zones: list[dict],
    minlon: float,
    maxlon: float,
    minlat: float,
    maxlat: float,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(14, 8))

    show = np.clip(pop, 0, HEAT_CLIP)
    # Downsample for faster rendering while preserving pattern.
    step = max(1, int(max(show.shape) / 1200))
    show_d = show[::step, ::step]
    lons_d = lons[::step]
    lats_d = lats[::step]
    lon_d, lat_d = np.meshgrid(lons_d, lats_d)
    plt.pcolormesh(lon_d, lat_d, show_d, shading="auto", cmap="inferno")

    for line in roads:
        plt.plot(line[:, 0], line[:, 1], color="#e7bf59", linewidth=1.2, alpha=0.95)

    for z in zones[:25]:
        plt.scatter(z["lon"], z["lat"], s=14, c="#6ee7ff", alpha=0.85, edgecolors="none")

    plt.xlim(minlon, maxlon)
    plt.ylim(minlat, maxlat)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Shamalgan Density + OSM Roads (new map extent)")
    cb = plt.colorbar()
    cb.set_label("Population per 100m cell (clipped)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_zone_process(out_path: Path, zones: list[dict], pop_sum: float) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vals = [z["home_weight"] for z in zones[:20]]
    labels = [z["zone_id"] for z in zones[:20]]
    cum = np.cumsum(vals) / pop_sum * 100.0 if pop_sum > 0 else np.zeros(len(vals))

    fig, ax1 = plt.subplots(figsize=(14, 7))
    ax1.bar(labels, vals, color="#ef4444")
    ax1.set_ylabel("Home weight")
    ax1.set_xlabel("Top zones (by home weight)")
    ax1.tick_params(axis="x", rotation=65)

    ax2 = ax1.twinx()
    ax2.plot(labels, cum, color="#0ea5e9", linewidth=2.0, marker="o", markersize=4)
    ax2.set_ylabel("Cumulative share of bbox population (%)")
    ax2.set_ylim(0, min(100, max(10, math.ceil(max(cum) / 10) * 10)))

    plt.title("Zone selection process: sorted zone weights and cumulative coverage")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_density_and_zones_basic(
    out_path: Path,
    pop: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    zones: list[dict],
    minlon: float,
    maxlon: float,
    minlat: float,
    maxlat: float,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 7))
    show = np.clip(pop, 0, HEAT_CLIP)
    step = max(1, int(max(show.shape) / 1200))
    show_d = show[::step, ::step]
    lons_d = lons[::step]
    lats_d = lats[::step]
    lon_d, lat_d = np.meshgrid(lons_d, lats_d)
    plt.pcolormesh(lon_d, lat_d, show_d, shading="auto", cmap="plasma")

    if zones:
        plt.scatter(
            [z["lon"] for z in zones],
            [z["lat"] for z in zones],
            s=35,
            c=[z["home_weight"] for z in zones],
            cmap="viridis",
            edgecolors="white",
            linewidths=0.4,
            alpha=0.9,
        )

    plt.xlim(minlon, maxlon)
    plt.ylim(minlat, maxlat)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Population density + derived zones (new map extent)")
    cb = plt.colorbar()
    cb.set_label("Population per 100m cell (clipped)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_top_zones_home_weight(out_path: Path, zones: list[dict], n: int = 20) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    top = zones[:n]
    labels = [z["zone_id"] for z in top]
    vals = [z["home_weight"] for z in top]
    plt.figure(figsize=(12, 6))
    plt.bar(labels, vals, color="#f97316")
    plt.xlabel("Zone")
    plt.ylabel("Home weight")
    plt.title(f"Top {n} zones by home weight")
    plt.xticks(rotation=65)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_process_flow(out_path: Path, pop_sum: float, zone_count: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("off")
    steps = [
        "1) Read TIFF population raster",
        "2) Clip raster to OSM bounds",
        f"3) Grid zoning ({ZONE_COLS}x{ZONE_ROWS})",
        f"4) Keep non-empty cells ({zone_count} zones)",
        "5) Weighted centroid + home/work weights",
        f"6) Write zones CSV and stats\nTotal bbox pop ~= {pop_sum:,.0f}",
    ]
    y = 0.85
    for s in steps:
        ax.text(
            0.08,
            y,
            s,
            fontsize=12,
            va="center",
            bbox=dict(boxstyle="round,pad=0.35", fc="#f3f4f6", ec="#9ca3af"),
        )
        if y > 0.2:
            ax.annotate(
                "",
                xy=(0.12, y - 0.08),
                xytext=(0.12, y - 0.02),
                arrowprops=dict(arrowstyle="->", color="#374151", lw=1.4),
            )
        y -= 0.13
    plt.title("Shamalgan population derivation pipeline", fontsize=14)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_zone_weight_map(
    out_path: Path,
    roads: list[np.ndarray],
    zones: list[dict],
    minlon: float,
    maxlon: float,
    minlat: float,
    maxlat: float,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 7))
    for line in roads:
        plt.plot(line[:, 0], line[:, 1], color="#d4a72c", linewidth=1.0, alpha=0.8)
    if zones:
        sizes = np.array([z["home_weight"] for z in zones], dtype=float)
        sizes = 20 + 220 * (sizes / max(sizes))
        plt.scatter(
            [z["lon"] for z in zones],
            [z["lat"] for z in zones],
            s=sizes,
            c=[z["home_weight"] for z in zones],
            cmap="YlOrRd",
            edgecolors="#111827",
            linewidths=0.3,
            alpha=0.85,
        )
    plt.xlim(minlon, maxlon)
    plt.ylim(minlat, maxlat)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Zone centroid map sized by home weight")
    cb = plt.colorbar()
    cb.set_label("Home weight")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_population_capture_curve(out_path: Path, zones: list[dict], pop_sum: float) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vals = np.array([z["home_weight"] for z in zones], dtype=float)
    order = np.sort(vals)[::-1]
    x = np.arange(1, len(order) + 1)
    y = np.cumsum(order) / pop_sum * 100 if pop_sum > 0 else np.zeros_like(order)
    plt.figure(figsize=(11, 6))
    plt.plot(x, y, color="#2563eb", linewidth=2.2)
    for q in [10, 20, 30]:
        if len(y) >= q:
            plt.scatter([q], [y[q - 1]], color="#ef4444", s=35)
            plt.text(q, y[q - 1] + 1.5, f"{q} zones: {y[q-1]:.1f}%", fontsize=9)
    plt.grid(True, alpha=0.25)
    plt.xlabel("Number of top zones")
    plt.ylabel("Captured population share (%)")
    plt.title("Population capture curve by ranked zones")
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def main() -> None:
    minlon, maxlon, minlat, maxlat = parse_bounds_from_osm(OSM_PATH)
    roads = collect_highway_lines(OSM_PATH)
    pop, lon, lat = geotiff_lonlat_grid(TIFF_PATH)
    clipped, lon, lat = clip_to_bbox(pop, lon, lat, minlon, maxlon, minlat, maxlat)

    zones = derive_zones(clipped, lon, lat, minlon, maxlon, minlat, maxlat)
    write_zones_csv(zones, ZONES_OUT)

    pop_sum = float(np.nansum(clipped))
    save_summary(
        ANALYSIS_DIR / "summary_new_map.csv",
        OSM_PATH,
        minlon,
        maxlon,
        minlat,
        maxlat,
        clipped,
        zones,
    )
    plot_reference_like_overlay(
        ANALYSIS_DIR / "04_density_roads_zones_new_map.png",
        clipped,
        lon,
        lat,
        roads,
        zones,
        minlon,
        maxlon,
        minlat,
        maxlat,
    )
    plot_zone_process(
        ANALYSIS_DIR / "05_zone_selection_process_new_map.png",
        zones,
        pop_sum,
    )
    plot_density_and_zones_basic(
        ANALYSIS_DIR / "01_density_and_zones.png",
        clipped,
        lon,
        lat,
        zones,
        minlon,
        maxlon,
        minlat,
        maxlat,
    )
    plot_top_zones_home_weight(
        ANALYSIS_DIR / "02_top_zones_home_weight.png",
        zones,
        n=20,
    )
    plot_process_flow(
        ANALYSIS_DIR / "03_process_flow.png",
        pop_sum,
        len(zones),
    )
    plot_zone_weight_map(
        ANALYSIS_DIR / "06_zone_weight_map.png",
        roads,
        zones,
        minlon,
        maxlon,
        minlat,
        maxlat,
    )
    plot_population_capture_curve(
        ANALYSIS_DIR / "07_population_capture_curve.png",
        zones,
        pop_sum,
    )

    print(f"Zones written: {ZONES_OUT}")
    print(f"Estimated bbox population: {pop_sum:.3f}")
    print(f"Zone count: {len(zones)}")
    print(f"Top zone weight: {zones[0]['home_weight'] if zones else 0}")


if __name__ == "__main__":
    main()
