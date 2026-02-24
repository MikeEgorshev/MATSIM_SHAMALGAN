#!/usr/bin/env python3
import argparse
import csv
import math
import os
import statistics
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque


def parse_modes(modes_text):
    if not modes_text:
        return set()
    return {m.strip() for m in modes_text.split(",") if m.strip()}


def percentile(values, p):
    if not values:
        return float("nan")
    if p <= 0:
        return min(values)
    if p >= 100:
        return max(values)
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1


def safe_float(raw, default=float("nan")):
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def safe_int(raw, default=0):
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Create network QC report for MATSim network XML.")
    parser.add_argument("network_xml", help="Path to MATSim network XML.")
    parser.add_argument("--out-dir", default="analysis-artifacts/network-qc", help="Output directory.")
    parser.add_argument("--name", default="network-qc", help="Report base name.")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    tree = ET.parse(args.network_xml)
    root = tree.getroot()
    nodes_elem = root.find("nodes")
    links_elem = root.find("links")
    if nodes_elem is None or links_elem is None:
        raise RuntimeError("Invalid MATSim network XML: missing <nodes> or <links>.")

    node_ids = set()
    for n in nodes_elem.findall("node"):
        nid = n.attrib.get("id")
        if nid:
            node_ids.add(nid)

    in_degree = Counter()
    out_degree = Counter()
    undirected_adj = defaultdict(set)

    mode_counter = Counter()
    link_lengths = []
    free_speeds = []
    capacities = []
    lanes = []

    issues = []
    links = []

    for le in links_elem.findall("link"):
        lid = le.attrib.get("id")
        from_id = le.attrib.get("from")
        to_id = le.attrib.get("to")
        length = safe_float(le.attrib.get("length"))
        freespeed = safe_float(le.attrib.get("freespeed"))
        capacity = safe_float(le.attrib.get("capacity"))
        permlanes = safe_float(le.attrib.get("permlanes"))
        modes = parse_modes(le.attrib.get("modes"))

        links.append(
            {
                "id": lid,
                "from": from_id,
                "to": to_id,
                "length": length,
                "freespeed": freespeed,
                "capacity": capacity,
                "permlanes": permlanes,
                "modes": ",".join(sorted(modes)),
            }
        )

        if from_id:
            out_degree[from_id] += 1
        if to_id:
            in_degree[to_id] += 1
        if from_id and to_id:
            undirected_adj[from_id].add(to_id)
            undirected_adj[to_id].add(from_id)

        link_lengths.append(length)
        free_speeds.append(freespeed)
        capacities.append(capacity)
        lanes.append(permlanes)

        if not modes:
            issues.append({"id": lid, "issue": "missing_modes"})
        for m in modes:
            mode_counter[m] += 1

        if not math.isfinite(length) or length <= 0:
            issues.append({"id": lid, "issue": "invalid_length", "value": length})
        if not math.isfinite(freespeed) or freespeed <= 0:
            issues.append({"id": lid, "issue": "invalid_freespeed", "value": freespeed})
        if not math.isfinite(capacity) or capacity <= 0:
            issues.append({"id": lid, "issue": "invalid_capacity", "value": capacity})
        if not math.isfinite(permlanes) or permlanes <= 0:
            issues.append({"id": lid, "issue": "invalid_permlanes", "value": permlanes})

        if math.isfinite(freespeed) and freespeed > 50:
            issues.append({"id": lid, "issue": "high_freespeed_gt_50ms", "value": freespeed})
        if math.isfinite(capacity) and capacity > 10000:
            issues.append({"id": lid, "issue": "high_capacity_gt_10000", "value": capacity})
        if math.isfinite(length) and length > 5000:
            issues.append({"id": lid, "issue": "long_link_gt_5000m", "value": length})

    # Connected components (weak, undirected)
    visited = set()
    components = []
    for nid in node_ids:
        if nid in visited:
            continue
        q = deque([nid])
        visited.add(nid)
        comp_nodes = []
        while q:
            cur = q.popleft()
            comp_nodes.append(cur)
            for nei in undirected_adj[cur]:
                if nei not in visited:
                    visited.add(nei)
                    q.append(nei)
        components.append(comp_nodes)

    components.sort(key=len, reverse=True)
    largest_comp_nodes = set(components[0]) if components else set()
    largest_comp_share = (len(largest_comp_nodes) / len(node_ids)) if node_ids else 0.0

    links_outside_lcc = []
    for link in links:
        if link["from"] not in largest_comp_nodes or link["to"] not in largest_comp_nodes:
            links_outside_lcc.append(link)

    dead_end_nodes = []
    for nid in node_ids:
        indeg = safe_int(in_degree.get(nid, 0))
        outdeg = safe_int(out_degree.get(nid, 0))
        total = indeg + outdeg
        if total == 1:
            dead_end_nodes.append({"node_id": nid, "in_degree": indeg, "out_degree": outdeg})

    isolated_nodes = []
    for nid in node_ids:
        indeg = safe_int(in_degree.get(nid, 0))
        outdeg = safe_int(out_degree.get(nid, 0))
        if indeg == 0 and outdeg == 0:
            isolated_nodes.append({"node_id": nid})

    issues_by_type = Counter(i["issue"] for i in issues)

    summary_lines = [
        f"# Network QC Report: {os.path.basename(args.network_xml)}",
        "",
        "## Core Counts",
        f"- Nodes: {len(node_ids):,}",
        f"- Links: {len(links):,}",
        "",
        "## Connectivity",
        f"- Weakly connected components: {len(components):,}",
        f"- Largest component nodes: {len(largest_comp_nodes):,} ({largest_comp_share:.2%})",
        f"- Links outside largest component: {len(links_outside_lcc):,}",
        f"- Dead-end nodes (total degree = 1): {len(dead_end_nodes):,}",
        f"- Isolated nodes (in=0,out=0): {len(isolated_nodes):,}",
        "",
        "## Link Attribute Statistics",
        (
            f"- Length [m]: min={min(link_lengths):.2f}, p50={percentile(link_lengths,50):.2f}, "
            f"p95={percentile(link_lengths,95):.2f}, max={max(link_lengths):.2f}"
        ),
        (
            f"- Free speed [m/s]: min={min(free_speeds):.2f}, p50={percentile(free_speeds,50):.2f}, "
            f"p95={percentile(free_speeds,95):.2f}, max={max(free_speeds):.2f}"
        ),
        (
            f"- Capacity [veh/h]: min={min(capacities):.2f}, p50={percentile(capacities,50):.2f}, "
            f"p95={percentile(capacities,95):.2f}, max={max(capacities):.2f}"
        ),
        (
            f"- Lanes: min={min(lanes):.2f}, p50={percentile(lanes,50):.2f}, "
            f"p95={percentile(lanes,95):.2f}, max={max(lanes):.2f}"
        ),
        "",
        "## Allowed Modes (link counts)",
    ]

    for mode, count in mode_counter.most_common():
        summary_lines.append(f"- {mode}: {count:,}")

    summary_lines.extend(["", "## Flagged Issues (counts)"])
    if issues_by_type:
        for issue, count in issues_by_type.most_common():
            summary_lines.append(f"- {issue}: {count:,}")
    else:
        summary_lines.append("- None")

    summary_lines.extend(
        [
            "",
            "## Output Files",
            f"- Issues CSV: `{args.name}-issues.csv`",
            f"- Links outside largest component CSV: `{args.name}-links_outside_lcc.csv`",
            f"- Dead-end nodes CSV: `{args.name}-dead_end_nodes.csv`",
            f"- Isolated nodes CSV: `{args.name}-isolated_nodes.csv`",
        ]
    )

    report_md = os.path.join(args.out_dir, f"{args.name}.md")
    issues_csv = os.path.join(args.out_dir, f"{args.name}-issues.csv")
    lcc_csv = os.path.join(args.out_dir, f"{args.name}-links_outside_lcc.csv")
    dead_csv = os.path.join(args.out_dir, f"{args.name}-dead_end_nodes.csv")
    iso_csv = os.path.join(args.out_dir, f"{args.name}-isolated_nodes.csv")

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
        f.write("\n")

    write_csv(issues_csv, issues, fieldnames=["id", "issue", "value"])
    write_csv(
        lcc_csv,
        links_outside_lcc,
        fieldnames=["id", "from", "to", "length", "freespeed", "capacity", "permlanes", "modes"],
    )
    write_csv(dead_csv, dead_end_nodes, fieldnames=["node_id", "in_degree", "out_degree"])
    write_csv(iso_csv, isolated_nodes, fieldnames=["node_id"])

    print(f"Wrote report: {report_md}")
    print(f"Wrote CSVs: {issues_csv}, {lcc_csv}, {dead_csv}, {iso_csv}")


if __name__ == "__main__":
    main()
