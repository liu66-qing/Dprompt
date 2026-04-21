#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import statistics
import time


def parse_args() -> argparse.Namespace:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Aggregate Phase 2.4 T2 confirmation results.")
    parser.add_argument(
        "--results-root",
        default=str(project_root / "results" / "phase2_4_t2_confirmation"),
        help="Directory containing per-seed eval subdirectories.",
    )
    return parser.parse_args()


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0
    return float(statistics.mean(values)), float(statistics.stdev(values))


def win_loss_tie(anchor_cases: dict[str, dict], target_cases: list[dict], step_idx: int) -> dict[str, int]:
    wins = losses = ties = 0
    for row in target_cases:
        anchor = anchor_cases[row["image_root"]]
        delta = float(row["dice_curve"][step_idx] - anchor["dice_curve"][step_idx])
        if delta > 1e-8:
            wins += 1
        elif delta < -1e-8:
            losses += 1
        else:
            ties += 1
    return {"wins": wins, "losses": losses, "ties": ties}


def main() -> int:
    args = parse_args()
    results_root = pathlib.Path(args.results_root)
    seed_jsons = sorted(results_root.glob("seed_*/LATEST_phase2_b_minimal.json"))
    if not seed_jsons:
        raise FileNotFoundError(f"No per-seed results found under {results_root}")

    per_seed_rows: list[dict] = []
    pooled_wins = {"dice5": {"wins": 0, "losses": 0, "ties": 0}, "dice8": {"wins": 0, "losses": 0, "ties": 0}}

    t0_dice5: list[float] = []
    t0_dice8: list[float] = []
    t0_noc: list[float] = []
    t0_latency: list[float] = []
    t0_memory: list[float] = []

    t2_dice5: list[float] = []
    t2_dice8: list[float] = []
    t2_noc: list[float] = []
    t2_latency: list[float] = []
    t2_memory: list[float] = []

    for json_path in seed_jsons:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        seed = int(payload.get("seed", -1))
        t0 = payload["method_results"]["T0"]
        t2 = payload["method_results"]["T2"]
        t0_cases = {row["image_root"]: row for row in t0["per_case"]}
        wins5 = win_loss_tie(t0_cases, t2["per_case"], 4)
        wins8 = win_loss_tie(t0_cases, t2["per_case"], 7)
        for key in pooled_wins["dice5"]:
            pooled_wins["dice5"][key] += wins5[key]
            pooled_wins["dice8"][key] += wins8[key]

        t0_dice5.append(float(t0["dice_at"]["5"]))
        t0_dice8.append(float(t0["dice_at"]["8"]))
        t0_noc.append(float(t0["noc_at_threshold"]))
        t0_latency.append(float(t0["avg_interaction_latency_s"]))
        t0_memory.append(float(t0["peak_memory_mb"]))

        t2_dice5.append(float(t2["dice_at"]["5"]))
        t2_dice8.append(float(t2["dice_at"]["8"]))
        t2_noc.append(float(t2["noc_at_threshold"]))
        t2_latency.append(float(t2["avg_interaction_latency_s"]))
        t2_memory.append(float(t2["peak_memory_mb"]))

        per_seed_rows.append(
            {
                "seed": seed,
                "t0_dice5": float(t0["dice_at"]["5"]),
                "t2_dice5": float(t2["dice_at"]["5"]),
                "delta_dice5": float(t2["dice_at"]["5"] - t0["dice_at"]["5"]),
                "t0_dice8": float(t0["dice_at"]["8"]),
                "t2_dice8": float(t2["dice_at"]["8"]),
                "delta_dice8": float(t2["dice_at"]["8"] - t0["dice_at"]["8"]),
                "t0_noc90": float(t0["noc_at_threshold"]),
                "t2_noc90": float(t2["noc_at_threshold"]),
                "delta_noc90": float(t2["noc_at_threshold"] - t0["noc_at_threshold"]),
                "t0_latency": float(t0["avg_interaction_latency_s"]),
                "t2_latency": float(t2["avg_interaction_latency_s"]),
                "t0_memory": float(t0["peak_memory_mb"]),
                "t2_memory": float(t2["peak_memory_mb"]),
                "wins_dice5": wins5["wins"],
                "losses_dice5": wins5["losses"],
                "wins_dice8": wins8["wins"],
                "losses_dice8": wins8["losses"],
            }
        )

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "num_seeds": len(per_seed_rows),
        "seeds": [row["seed"] for row in per_seed_rows],
        "t0": {
            "dice5_mean_std": mean_std(t0_dice5),
            "dice8_mean_std": mean_std(t0_dice8),
            "noc90_mean_std": mean_std(t0_noc),
            "latency_mean_std": mean_std(t0_latency),
            "memory_mean_std": mean_std(t0_memory),
        },
        "t2": {
            "dice5_mean_std": mean_std(t2_dice5),
            "dice8_mean_std": mean_std(t2_dice8),
            "noc90_mean_std": mean_std(t2_noc),
            "latency_mean_std": mean_std(t2_latency),
            "memory_mean_std": mean_std(t2_memory),
        },
        "delta_t2_vs_t0": {
            "dice5_mean_std": mean_std([b - a for a, b in zip(t0_dice5, t2_dice5)]),
            "dice8_mean_std": mean_std([b - a for a, b in zip(t0_dice8, t2_dice8)]),
            "noc90_mean_std": mean_std([b - a for a, b in zip(t0_noc, t2_noc)]),
        },
        "pooled_win_rate_vs_t0": pooled_wins,
        "per_seed_rows": per_seed_rows,
    }

    summary_dir = results_root / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = summary_dir / f"{stamp}_phase2_4_t2_confirmation_summary.json"
    csv_path = summary_dir / f"{stamp}_phase2_4_t2_confirmation_summary.csv"
    md_path = summary_dir / f"{stamp}_phase2_4_t2_confirmation_summary.md"
    latest_json = summary_dir / "LATEST_phase2_4_t2_confirmation_summary.json"
    latest_csv = summary_dir / "LATEST_phase2_4_t2_confirmation_summary.csv"
    latest_md = summary_dir / "LATEST_phase2_4_t2_confirmation_summary.md"

    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_seed_rows[0].keys()))
        writer.writeheader()
        writer.writerows(per_seed_rows)

    t0_d5_mean, t0_d5_std = summary["t0"]["dice5_mean_std"]
    t2_d5_mean, t2_d5_std = summary["t2"]["dice5_mean_std"]
    t0_d8_mean, t0_d8_std = summary["t0"]["dice8_mean_std"]
    t2_d8_mean, t2_d8_std = summary["t2"]["dice8_mean_std"]
    t0_noc_mean, t0_noc_std = summary["t0"]["noc90_mean_std"]
    t2_noc_mean, t2_noc_std = summary["t2"]["noc90_mean_std"]
    delta_d5_mean, delta_d5_std = summary["delta_t2_vs_t0"]["dice5_mean_std"]
    delta_d8_mean, delta_d8_std = summary["delta_t2_vs_t0"]["dice8_mean_std"]
    delta_noc_mean, delta_noc_std = summary["delta_t2_vs_t0"]["noc90_mean_std"]
    lines = [
        "# Phase 2.4 T2 Confirmation Summary",
        "",
        f"- Seeds: {summary['seeds']}",
        "",
        "| System | Dice@5 | Dice@8 | NoC@90 |",
        "|---|---:|---:|---:|",
        f"| T0 | {t0_d5_mean:.4f} +- {t0_d5_std:.4f} | {t0_d8_mean:.4f} +- {t0_d8_std:.4f} | {t0_noc_mean:.3f} +- {t0_noc_std:.3f} |",
        f"| T2 | {t2_d5_mean:.4f} +- {t2_d5_std:.4f} | {t2_d8_mean:.4f} +- {t2_d8_std:.4f} | {t2_noc_mean:.3f} +- {t2_noc_std:.3f} |",
        "",
        "| Delta T2 - T0 | Dice@5 | Dice@8 | NoC@90 |",
        "|---|---:|---:|---:|",
        f"| Mean +- Std | {delta_d5_mean:+.4f} +- {delta_d5_std:.4f} | {delta_d8_mean:+.4f} +- {delta_d8_std:.4f} | {delta_noc_mean:+.3f} +- {delta_noc_std:.3f} |",
        "",
        f"- Pooled Dice@5 win rate vs T0: {pooled_wins['dice5']['wins']} win / {pooled_wins['dice5']['losses']} loss / {pooled_wins['dice5']['ties']} tie",
        f"- Pooled Dice@8 win rate vs T0: {pooled_wins['dice8']['wins']} win / {pooled_wins['dice8']['losses']} loss / {pooled_wins['dice8']['ties']} tie",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_csv.write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"[done] json={json_path}")
    print(f"[done] csv={csv_path}")
    print(f"[done] md={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
