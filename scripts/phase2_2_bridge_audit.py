#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import sys
import time
from types import SimpleNamespace

import torch
import yaml


def parse_args() -> argparse.Namespace:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Audit trainable parameter scopes for Phase 2.2 bridge runs.")
    parser.add_argument(
        "--paths-cfg",
        default=str(project_root / "configs" / "paths.local.yaml"),
        help="Local path configuration.",
    )
    parser.add_argument(
        "--bridge-cfg",
        default=str(project_root / "configs" / "phase2_2_trainable_bridge.yaml"),
        help="Phase 2.2 bridge configuration.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(project_root / "results" / "phase2_2_bridge_audit"),
        help="Directory for JSON/CSV/Markdown outputs.",
    )
    parser.add_argument("--only-run", default=None, help="Optional run filter, e.g. T3.")
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_checkpoint(paths_cfg: dict) -> str:
    return paths_cfg["paths"]["imis_checkpoint"]


def build_args(paths_cfg: dict, bridge_cfg: dict, run_name: str, run_cfg: dict, device: torch.device) -> SimpleNamespace:
    global_cfg = bridge_cfg["global"]
    return SimpleNamespace(
        data_dir=paths_cfg["paths"]["imis_btcv_root"],
        image_size=global_cfg["image_size"],
        test_mode=False,
        batch_size=global_cfg["batch_size"],
        num_workers=global_cfg["num_workers"],
        dist=False,
        multi_gpu=False,
        model_type=global_cfg["model_type"],
        sam_checkpoint=resolve_checkpoint(paths_cfg),
        device=device,
        mask_num=global_cfg["mask_num"],
        inter_num=global_cfg["inter_num"],
        local_adapter_blocks=run_cfg.get("local_adapter_blocks"),
        hsf_blocks=run_cfg.get("hsf_blocks"),
        trainable_scope=run_cfg["trainable_scope"],
    )


def main() -> int:
    args = parse_args()
    project_root = pathlib.Path(__file__).resolve().parents[1]
    paths_cfg = load_yaml(args.paths_cfg)
    bridge_cfg = load_yaml(args.bridge_cfg)
    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    imis_root = pathlib.Path(paths_cfg["paths"]["imis_bench_root"]).resolve()
    os.chdir(imis_root)
    if str(imis_root) not in sys.path:
        sys.path.insert(0, str(imis_root))

    from model import IMISNet  # noqa: PLC0415
    from segment_anything import sam_model_registry  # noqa: PLC0415

    device = torch.device(args.device if args.device != "cpu" and torch.cuda.is_available() else "cpu")
    rows: list[dict] = []

    for run_name, run_cfg in bridge_cfg["run_defs"].items():
        if args.only_run and run_name != args.only_run:
            continue
        model_args = build_args(paths_cfg, bridge_cfg, run_name, run_cfg, device)
        sam = sam_model_registry[model_args.model_type](model_args).to(device)
        model = IMISNet(
            sam,
            test_mode=False,
            select_mask_num=model_args.mask_num,
            category_weights=str(imis_root / "dataloaders" / "categories_weight.pkl"),
        ).to(device)
        summary = model.set_trainable_scope(run_cfg["trainable_scope"])

        rows.append(
            {
                "run": run_name,
                "title": run_cfg["title"],
                "trainable_scope": run_cfg["trainable_scope"],
                "local_adapter_blocks": list(run_cfg.get("local_adapter_blocks", [])),
                "hsf_blocks": list(run_cfg.get("hsf_blocks", [])),
                "trainable_param_tensors": summary["trainable_param_tensors"],
                "trainable_param_count": summary["trainable_param_count"],
                "trainable_names": summary["trainable_names"],
            }
        )
        del model
        del sam

    stamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"{stamp}_phase2_2_bridge_audit.json"
    csv_path = output_dir / f"{stamp}_phase2_2_bridge_audit.csv"
    md_path = output_dir / f"{stamp}_phase2_2_bridge_audit.md"
    latest_json = output_dir / "LATEST_phase2_2_bridge_audit.json"
    latest_csv = output_dir / "LATEST_phase2_2_bridge_audit.csv"
    latest_md = output_dir / "LATEST_phase2_2_bridge_audit.md"

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "bridge_cfg": args.bridge_cfg,
                "rows": rows,
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )
        handle.write("\n")

    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "run",
                "title",
                "trainable_scope",
                "trainable_param_tensors",
                "trainable_param_count",
                "local_adapter_blocks",
                "hsf_blocks",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "run": row["run"],
                    "title": row["title"],
                    "trainable_scope": row["trainable_scope"],
                    "trainable_param_tensors": row["trainable_param_tensors"],
                    "trainable_param_count": row["trainable_param_count"],
                    "local_adapter_blocks": str(row["local_adapter_blocks"]),
                    "hsf_blocks": str(row["hsf_blocks"]),
                }
            )

    lines = [
        "# Phase 2.2 Bridge Audit",
        "",
        "| Run | Scope | Trainable Tensors | Trainable Params |",
        "|---|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['run']} | {row['trainable_scope']} | {row['trainable_param_tensors']} | {row['trainable_param_count']} |"
        )
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
