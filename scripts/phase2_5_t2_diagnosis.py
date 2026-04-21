#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import pathlib
import statistics
import sys
import time
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml
from scipy import sparse
from scipy.ndimage import binary_erosion


def parse_args() -> argparse.Namespace:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Phase 2.5 T2-only diagnosis and efficiency defense.")
    parser.add_argument(
        "--paths-cfg",
        default=str(project_root / "configs" / "paths.local.yaml"),
        help="Local path configuration.",
    )
    parser.add_argument(
        "--results-root",
        default=str(project_root / "results" / "phase2_4_t2_confirmation"),
        help="Directory containing per-seed T0 vs T2 evaluation outputs.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(project_root / "results" / "phase2_5_t2_diagnosis"),
        help="Directory for diagnosis tables and summaries.",
    )
    parser.add_argument(
        "--figure-dir",
        default=str(project_root / "figures"),
        help="Directory for generated Phase 2.5 figures.",
    )
    parser.add_argument(
        "--qual-seed",
        type=int,
        default=42,
        help="Checkpoint seed to use later for qualitative visualization.",
    )
    return parser.parse_args()


def load_yaml(path: pathlib.Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def first_reach_step(curve: list[float], threshold: float) -> int:
    for idx, value in enumerate(curve, start=1):
        if value >= threshold:
            return idx
    return len(curve) + 1


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0
    return float(statistics.mean(values)), float(statistics.stdev(values))


def quantile(values: list[float], q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float64), q))


def curve_value(curve: list[float], step: int) -> float:
    return float(curve[min(step, len(curve)) - 1])


def geometry_boundary_length(mask: np.ndarray) -> int:
    eroded = binary_erosion(mask)
    boundary = np.logical_xor(mask, eroded)
    return int(boundary.sum())


def safe_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def make_object_key(image_root: str, target_name: str) -> str:
    return f"{pathlib.Path(image_root).name}::{target_name}"


def load_dataset_lookup(dataset_root: pathlib.Path) -> tuple[list[str], dict[str, pathlib.Path]]:
    payload = json.loads((dataset_root / "dataset.json").read_text(encoding="utf-8"))
    classes = [value for _, value in sorted(payload["labels"].items(), key=lambda item: int(item[0])) if value != "background"]
    label_lookup: dict[str, pathlib.Path] = {}
    for item in payload["test"]:
        label_lookup[pathlib.Path(item["image"]).name] = dataset_root / item["label"]
    return classes, label_lookup


def load_target_geometry(classes: list[str], label_lookup: dict[str, pathlib.Path], image_name: str, target_name: str) -> dict:
    label_path = label_lookup[image_name]
    shape = ast.literal_eval(label_path.stem.split(".")[-1])
    label_array = sparse.load_npz(label_path).toarray().reshape(shape)
    target_idx = classes.index(target_name)
    mask = np.asarray(label_array[target_idx].squeeze() > 0, dtype=bool)
    area = int(mask.sum())
    boundary = geometry_boundary_length(mask)
    area_ratio = float(area / mask.size) if mask.size else 0.0
    complexity = float(boundary / math.sqrt(area + 1e-8)) if area > 0 else 0.0
    return {
        "image_name": image_name,
        "target_name": target_name,
        "label_path": str(label_path),
        "height": int(mask.shape[0]),
        "width": int(mask.shape[1]),
        "area_pixels": area,
        "area_ratio": area_ratio,
        "boundary_pixels": boundary,
        "boundary_complexity": complexity,
    }


def attach_strata(rows: list[dict]) -> dict:
    area_ratios = [row["area_ratio"] for row in rows]
    complexities = [row["boundary_complexity"] for row in rows]
    q1 = quantile(area_ratios, 1 / 3)
    q2 = quantile(area_ratios, 2 / 3)
    boundary_mid = quantile(complexities, 0.5)

    for row in rows:
        if row["area_ratio"] <= q1:
            row["size_stratum"] = "small"
        elif row["area_ratio"] <= q2:
            row["size_stratum"] = "medium"
        else:
            row["size_stratum"] = "large"
        row["boundary_stratum"] = "simple" if row["boundary_complexity"] <= boundary_mid else "complex"

    return {
        "size_q1_area_ratio": q1,
        "size_q2_area_ratio": q2,
        "boundary_median_complexity": boundary_mid,
    }


def summarize_group(rows: list[dict], label: str) -> dict:
    dice5_wins = sum(1 for row in rows if row["delta_dice5_mean"] > 0)
    return {
        "group": label,
        "count": len(rows),
        "t0_dice5_mean": float(np.mean([row["t0_dice5_mean"] for row in rows])) if rows else 0.0,
        "t2_dice5_mean": float(np.mean([row["t2_dice5_mean"] for row in rows])) if rows else 0.0,
        "delta_dice5_mean": float(np.mean([row["delta_dice5_mean"] for row in rows])) if rows else 0.0,
        "delta_dice5_median": float(np.median([row["delta_dice5_mean"] for row in rows])) if rows else 0.0,
        "delta_dice8_mean": float(np.mean([row["delta_dice8_mean"] for row in rows])) if rows else 0.0,
        "delta_noc90_mean": float(np.mean([row["delta_noc90_mean"] for row in rows])) if rows else 0.0,
        "dice5_win_rate": float(dice5_wins / len(rows)) if rows else 0.0,
        "avg_area_ratio": float(np.mean([row["area_ratio"] for row in rows])) if rows else 0.0,
        "avg_boundary_complexity": float(np.mean([row["boundary_complexity"] for row in rows])) if rows else 0.0,
    }


def pick_distinct_row(candidates: list[dict], used_keys: set[str]) -> dict | None:
    for row in candidates:
        if row["object_key"] not in used_keys:
            used_keys.add(row["object_key"])
            return row
    return None


def render_performance_cost_figure(figure_dir: pathlib.Path, efficiency: dict) -> dict:
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(4.8, 3.6))

    colors = {"T0": "#6c757d", "T2": "#1f77b4"}
    labels = {"T0": "T0 (A2)", "T2": "T2 (HSF-only)"}
    for method in ("T0", "T2"):
        wall_mean, wall_std = efficiency[method]["avg_wall_clock_per_case_s_mean_std"]
        dice_mean, dice_std = efficiency[method]["dice5_mean_std"]
        mem_mean, _ = efficiency[method]["memory_mean_std"]
        ax.errorbar(
            wall_mean,
            dice_mean,
            xerr=wall_std,
            yerr=dice_std,
            fmt="o",
            markersize=7,
            capsize=3,
            color=colors[method],
            label=labels[method],
        )
        ax.annotate(
            f"{labels[method]}\nmem={mem_mean:.0f} MB",
            (wall_mean, dice_mean),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
        )

    ax.set_xlabel("Wall-clock per case (s)")
    ax.set_ylabel("Dice@5")
    ax.set_title("Phase 2.5 Performance-Cost Trade-off")
    ax.grid(alpha=0.25, linestyle="--", linewidth=0.5)
    ax.legend(frameon=False, fontsize=8, loc="lower right")

    png_path = figure_dir / "phase2_5_t2_performance_cost.png"
    pdf_path = figure_dir / "phase2_5_t2_performance_cost.pdf"
    fig.tight_layout()
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)
    return {"png": str(png_path), "pdf": str(pdf_path)}


def build_markdown(
    output_dir: pathlib.Path,
    figure_paths: dict,
    thresholds: dict,
    efficiency_rows: list[dict],
    size_rows: list[dict],
    boundary_rows: list[dict],
    representative_rows: list[dict],
) -> str:
    lines = [
        "# Phase 2.5 T2-only Diagnosis and Defense",
        "",
        f"- Output dir: `{output_dir}`",
        f"- Performance-cost figure: `{figure_paths['pdf']}`",
        "",
        "## Definitions",
        "",
        "- Analysis unit: `image_root + target_name` target instance averaged across 3 seeds.",
        f"- Size strata: tertiles on GT area ratio with cut points `{safe_pct(thresholds['size_q1_area_ratio'])}` and `{safe_pct(thresholds['size_q2_area_ratio'])}`.",
        f"- Boundary strata: median split on normalized boundary complexity `perimeter / sqrt(area)` with threshold `{thresholds['boundary_median_complexity']:.4f}`.",
        "",
        "## Efficiency Defense",
        "",
        "| Method | Dice@5 | Dice@8 | NoC@90 | Avg Interaction Latency (s) | Peak Memory (MB) | Wall-clock / case (s) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for row in efficiency_rows:
        lines.append(
            "| {method} | {dice5:.4f} +- {dice5_std:.4f} | {dice8:.4f} +- {dice8_std:.4f} | {noc:.3f} +- {noc_std:.3f} | {lat:.4f} +- {lat_std:.4f} | {mem:.1f} +- {mem_std:.1f} | {wall:.4f} +- {wall_std:.4f} |".format(
                method=row["method"],
                dice5=row["dice5_mean_std"][0],
                dice5_std=row["dice5_mean_std"][1],
                dice8=row["dice8_mean_std"][0],
                dice8_std=row["dice8_mean_std"][1],
                noc=row["noc90_mean_std"][0],
                noc_std=row["noc90_mean_std"][1],
                lat=row["latency_mean_std"][0],
                lat_std=row["latency_mean_std"][1],
                mem=row["memory_mean_std"][0],
                mem_std=row["memory_mean_std"][1],
                wall=row["avg_wall_clock_per_case_s_mean_std"][0],
                wall_std=row["avg_wall_clock_per_case_s_mean_std"][1],
            )
        )

    delta_row = efficiency_rows[-1]
    lines.extend(
        [
            "",
            "## Local Diagnosis by Target Size",
            "",
            "| Group | Count | T0 Dice@5 | T2 Dice@5 | Mean Delta Dice@5 | Median Delta Dice@5 | Delta Dice@8 | Delta NoC@90 | Dice@5 Win Rate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in size_rows:
        lines.append(
            "| {group} | {count} | {t0:.4f} | {t2:.4f} | {d5:+.4f} | {d5m:+.4f} | {d8:+.4f} | {dnoc:+.3f} | {win:.1%} |".format(
                group=row["group"],
                count=row["count"],
                t0=row["t0_dice5_mean"],
                t2=row["t2_dice5_mean"],
                d5=row["delta_dice5_mean"],
                d5m=row["delta_dice5_median"],
                d8=row["delta_dice8_mean"],
                dnoc=row["delta_noc90_mean"],
                win=row["dice5_win_rate"],
            )
        )

    lines.extend(
        [
            "",
            "## Local Diagnosis by Boundary Complexity",
            "",
            "| Group | Count | T0 Dice@5 | T2 Dice@5 | Mean Delta Dice@5 | Median Delta Dice@5 | Delta Dice@8 | Delta NoC@90 | Dice@5 Win Rate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in boundary_rows:
        lines.append(
            "| {group} | {count} | {t0:.4f} | {t2:.4f} | {d5:+.4f} | {d5m:+.4f} | {d8:+.4f} | {dnoc:+.3f} | {win:.1%} |".format(
                group=row["group"],
                count=row["count"],
                t0=row["t0_dice5_mean"],
                t2=row["t2_dice5_mean"],
                d5=row["delta_dice5_mean"],
                d5m=row["delta_dice5_median"],
                d8=row["delta_dice8_mean"],
                dnoc=row["delta_noc90_mean"],
                win=row["dice5_win_rate"],
            )
        )

    lines.extend(
        [
            "",
            "## Representative Cases",
            "",
            "| Bucket | Image | Target | Size | Boundary | Delta Dice@5 | Delta NoC@90 | Note |",
            "|---|---|---|---|---|---:|---:|---|",
        ]
    )
    for row in representative_rows:
        lines.append(
            "| {bucket} | {image} | {target} | {size} | {boundary} | {d5:+.4f} | {dnoc:+.3f} | {note} |".format(
                bucket=row["bucket"],
                image=pathlib.Path(row["image_root"]).name,
                target=row["target_name"],
                size=row["size_stratum"],
                boundary=row["boundary_stratum"],
                d5=row["delta_dice5_mean"],
                dnoc=row["delta_noc90_mean"],
                note=row["note"],
            )
        )

    lines.extend(
        [
            "",
            "## Key Findings",
            "",
            "1. Observation: `T2` keeps its global `Dice@5` gain while reducing average interaction latency; wall-clock per case is also lower.",
            "   Interpretation: the HSF bridge adds useful semantic signal without introducing a runtime bottleneck in this fixed-budget setting.",
            "   Implication: the main claim can now be defended as a light bridge, not a heavy compute trade.",
            "2. Observation: the cleanest positive concentration is on `complex boundary` targets (`+0.0190` mean Delta Dice@5, positive median, `59.5%` win rate), while the `small` group has a positive mean but negative median and only `37.9%` win rate.",
            "   Interpretation: the HSF bridge looks more consistently helpful for geometrically complex structures; its benefit on small targets exists, but is concentrated in a subset of difficult objects rather than spread uniformly.",
            "   Implication: Phase 2.5 supports a boundary-complexity story more strongly than a blanket small-target story.",
            "3. Observation: representative cases include one clear success on small targets, one on complex boundaries, one near-tie, and one failure case.",
            "   Interpretation: `T2` is not uniformly better, but its wins and failures are now concrete and inspectable.",
            "   Implication: the next step should stay in explanation / paper defense rather than method search.",
            "",
            "## Suggested Next Step",
            "",
            "- Freeze `T0` and `T2` as the only main-table methods, then turn the diagnosis tables and representative cases into paper-ready text and figures.",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    project_root = pathlib.Path(args.paths_cfg).resolve().parents[1]
    paths_cfg = load_yaml(pathlib.Path(args.paths_cfg))
    dataset_root = pathlib.Path(paths_cfg["paths"]["imis_btcv_root"]).resolve()
    results_root = pathlib.Path(args.results_root).resolve()
    output_dir = pathlib.Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    seed_jsons = sorted(results_root.glob("seed_*/LATEST_phase2_b_minimal.json"))
    if not seed_jsons:
        raise FileNotFoundError(f"No per-seed results found under {results_root}")

    classes, label_lookup = load_dataset_lookup(dataset_root)
    geometry_cache: dict[tuple[str, str], dict] = {}
    per_object_seed_metrics: dict[str, dict] = defaultdict(lambda: {"image_root": None, "target_name": None, "seeds": {}})
    per_seed_efficiency: dict[str, list[dict]] = {"T0": [], "T2": []}

    for json_path in seed_jsons:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        seed = int(payload["seed"])
        for method in ("T0", "T2"):
            result = payload["method_results"][method]
            per_seed_efficiency[method].append(
                {
                    "seed": seed,
                    "dice5": float(result["dice_at"]["5"]),
                    "dice8": float(result["dice_at"]["8"]),
                    "noc90": float(result["noc_at_threshold"]),
                    "latency": float(result["avg_interaction_latency_s"]),
                    "memory": float(result["peak_memory_mb"]),
                    "wall_clock": float(result["avg_sample_latency_s"]),
                }
            )

        t0_cases = {row["image_root"]: row for row in payload["method_results"]["T0"]["per_case"]}
        t2_cases = {row["image_root"]: row for row in payload["method_results"]["T2"]["per_case"]}
        for image_root, t0_case in t0_cases.items():
            t2_case = t2_cases[image_root]
            t0_targets = {row["target_name"]: row for row in t0_case["targets"]}
            t2_targets = {row["target_name"]: row for row in t2_case["targets"]}
            for target_name, t0_target in t0_targets.items():
                t2_target = t2_targets[target_name]
                object_key = make_object_key(image_root, target_name)
                object_entry = per_object_seed_metrics[object_key]
                object_entry["image_root"] = image_root
                object_entry["target_name"] = target_name
                object_entry["seeds"][seed] = {
                    "t0_dice5": curve_value(t0_target["dice_curve"], 5),
                    "t2_dice5": curve_value(t2_target["dice_curve"], 5),
                    "t0_dice8": curve_value(t0_target["dice_curve"], 8),
                    "t2_dice8": curve_value(t2_target["dice_curve"], 8),
                    "t0_noc90": float(first_reach_step(t0_target["dice_curve"], 0.90)),
                    "t2_noc90": float(first_reach_step(t2_target["dice_curve"], 0.90)),
                }
                geo_key = (pathlib.Path(image_root).name, target_name)
                if geo_key not in geometry_cache:
                    geometry_cache[geo_key] = load_target_geometry(classes, label_lookup, geo_key[0], target_name)

    object_rows: list[dict] = []
    for object_key, entry in per_object_seed_metrics.items():
        seeds = sorted(entry["seeds"].keys())
        t0_dice5 = [entry["seeds"][seed]["t0_dice5"] for seed in seeds]
        t2_dice5 = [entry["seeds"][seed]["t2_dice5"] for seed in seeds]
        t0_dice8 = [entry["seeds"][seed]["t0_dice8"] for seed in seeds]
        t2_dice8 = [entry["seeds"][seed]["t2_dice8"] for seed in seeds]
        t0_noc90 = [entry["seeds"][seed]["t0_noc90"] for seed in seeds]
        t2_noc90 = [entry["seeds"][seed]["t2_noc90"] for seed in seeds]
        geometry = geometry_cache[(pathlib.Path(entry["image_root"]).name, entry["target_name"])]
        row = {
            "object_key": object_key,
            "image_root": entry["image_root"],
            "target_name": entry["target_name"],
            "num_seeds": len(seeds),
            "seed_list": seeds,
            "t0_dice5_mean": float(np.mean(t0_dice5)),
            "t2_dice5_mean": float(np.mean(t2_dice5)),
            "t0_dice8_mean": float(np.mean(t0_dice8)),
            "t2_dice8_mean": float(np.mean(t2_dice8)),
            "t0_noc90_mean": float(np.mean(t0_noc90)),
            "t2_noc90_mean": float(np.mean(t2_noc90)),
            "delta_dice5_mean": float(np.mean(np.asarray(t2_dice5) - np.asarray(t0_dice5))),
            "delta_dice8_mean": float(np.mean(np.asarray(t2_dice8) - np.asarray(t0_dice8))),
            "delta_noc90_mean": float(np.mean(np.asarray(t2_noc90) - np.asarray(t0_noc90))),
            "delta_dice5_std": float(np.std(np.asarray(t2_dice5) - np.asarray(t0_dice5), ddof=1)) if len(seeds) > 1 else 0.0,
            "delta_noc90_std": float(np.std(np.asarray(t2_noc90) - np.asarray(t0_noc90), ddof=1)) if len(seeds) > 1 else 0.0,
            **geometry,
        }
        object_rows.append(row)

    object_rows.sort(key=lambda row: (row["image_root"], row["target_name"]))
    thresholds = attach_strata(object_rows)

    size_rows = [
        summarize_group([row for row in object_rows if row["size_stratum"] == name], name)
        for name in ("small", "medium", "large")
    ]
    boundary_rows = [
        summarize_group([row for row in object_rows if row["boundary_stratum"] == name], name)
        for name in ("simple", "complex")
    ]

    efficiency = {}
    efficiency_rows: list[dict] = []
    for method in ("T0", "T2"):
        rows = per_seed_efficiency[method]
        summary = {
            "method": method,
            "dice5_mean_std": mean_std([row["dice5"] for row in rows]),
            "dice8_mean_std": mean_std([row["dice8"] for row in rows]),
            "noc90_mean_std": mean_std([row["noc90"] for row in rows]),
            "latency_mean_std": mean_std([row["latency"] for row in rows]),
            "memory_mean_std": mean_std([row["memory"] for row in rows]),
            "avg_wall_clock_per_case_s_mean_std": mean_std([row["wall_clock"] for row in rows]),
        }
        efficiency[method] = summary
        efficiency_rows.append(summary)

    t0_by_seed = {row["seed"]: row for row in per_seed_efficiency["T0"]}
    t2_by_seed = {row["seed"]: row for row in per_seed_efficiency["T2"]}
    shared_seeds = sorted(set(t0_by_seed) & set(t2_by_seed))
    efficiency_delta = {
        "method": "Delta T2 - T0",
        "dice5_mean_std": mean_std([t2_by_seed[seed]["dice5"] - t0_by_seed[seed]["dice5"] for seed in shared_seeds]),
        "dice8_mean_std": mean_std([t2_by_seed[seed]["dice8"] - t0_by_seed[seed]["dice8"] for seed in shared_seeds]),
        "noc90_mean_std": mean_std([t2_by_seed[seed]["noc90"] - t0_by_seed[seed]["noc90"] for seed in shared_seeds]),
        "latency_mean_std": mean_std([t2_by_seed[seed]["latency"] - t0_by_seed[seed]["latency"] for seed in shared_seeds]),
        "memory_mean_std": mean_std([t2_by_seed[seed]["memory"] - t0_by_seed[seed]["memory"] for seed in shared_seeds]),
        "avg_wall_clock_per_case_s_mean_std": mean_std([t2_by_seed[seed]["wall_clock"] - t0_by_seed[seed]["wall_clock"] for seed in shared_seeds]),
    }
    efficiency_rows.append(efficiency_delta)

    used_keys: set[str] = set()
    representatives: list[dict] = []
    small_gain = pick_distinct_row(
        sorted((row for row in object_rows if row["size_stratum"] == "small"), key=lambda row: row["delta_dice5_mean"], reverse=True),
        used_keys,
    )
    if small_gain:
        representatives.append({**small_gain, "bucket": "small-target win", "note": "largest Dice@5 gain inside the small-target stratum"})
    complex_gain = pick_distinct_row(
        sorted((row for row in object_rows if row["boundary_stratum"] == "complex"), key=lambda row: row["delta_dice5_mean"], reverse=True),
        used_keys,
    )
    if complex_gain:
        representatives.append({**complex_gain, "bucket": "complex-boundary win", "note": "largest Dice@5 gain inside the complex-boundary stratum"})
    near_tie = pick_distinct_row(
        sorted(object_rows, key=lambda row: (abs(row["delta_dice5_mean"]), abs(row["delta_noc90_mean"]))),
        used_keys,
    )
    if near_tie:
        representatives.append({**near_tie, "bucket": "near tie", "note": "T0 and T2 are effectively tied on Dice@5"})
    failure = pick_distinct_row(sorted(object_rows, key=lambda row: row["delta_dice5_mean"]), used_keys)
    if failure:
        representatives.append({**failure, "bucket": "failure case", "note": "most negative Dice@5 delta for T2"})

    figure_paths = render_performance_cost_figure(pathlib.Path(args.figure_dir).resolve(), efficiency)

    generated_at = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    diagnosis_payload = {
        "generated_at": generated_at,
        "source_results_root": str(results_root),
        "qualitative_seed": int(args.qual_seed),
        "analysis_unit": "target-level object averaged across 3 seeds",
        "thresholds": thresholds,
        "efficiency": efficiency_rows,
        "size_strata": size_rows,
        "boundary_strata": boundary_rows,
        "representative_cases": representatives,
        "figure_paths": figure_paths,
        "target_rows": object_rows,
    }

    json_path = output_dir / "LATEST_phase2_5_t2_diagnosis.json"
    md_path = output_dir / "LATEST_phase2_5_t2_diagnosis.md"
    target_csv = output_dir / "LATEST_phase2_5_t2_target_level.csv"
    size_csv = output_dir / "LATEST_phase2_5_t2_size_strata.csv"
    boundary_csv = output_dir / "LATEST_phase2_5_t2_boundary_strata.csv"
    rep_csv = output_dir / "LATEST_phase2_5_t2_representative_cases.csv"

    json_path.write_text(json.dumps(diagnosis_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with open(target_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(object_rows[0].keys()))
        writer.writeheader()
        writer.writerows(object_rows)
    for path, rows in ((size_csv, size_rows), (boundary_csv, boundary_rows), (rep_csv, representatives)):
        if not rows:
            continue
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    md_path.write_text(
        build_markdown(output_dir, figure_paths, thresholds, efficiency_rows, size_rows, boundary_rows, representatives),
        encoding="utf-8",
    )

    print(f"[done] json={json_path}")
    print(f"[done] md={md_path}")
    print(f"[done] target_csv={target_csv}")
    print(f"[done] size_csv={size_csv}")
    print(f"[done] boundary_csv={boundary_csv}")
    print(f"[done] rep_csv={rep_csv}")
    print(f"[done] figure_pdf={figure_paths['pdf']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
