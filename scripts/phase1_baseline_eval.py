#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import random
import sys
import time
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import torch
import yaml
from torch.nn import functional as F
from tqdm import tqdm


@dataclass(frozen=True)
class RunSpec:
    image_size: int
    prompt_mode: str
    inter_num: int

    @property
    def run_id(self) -> str:
        return f"img{self.image_size}_{self.prompt_mode}_k{self.inter_num}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 1 IMIS-Bench baseline legalization.")
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--paths-cfg",
        default=str(project_root / "configs" / "paths.local.yaml"),
        help="Local path configuration.",
    )
    parser.add_argument(
        "--baseline-cfg",
        default=str(project_root / "configs" / "phase1_baselines.yaml"),
        help="Baseline legalization configuration.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(project_root / "results" / "phase1_baselines"),
        help="Directory for JSON/CSV/Markdown outputs.",
    )
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--only-baseline", default=None, help="Optional baseline name filter, e.g. A2.")
    parser.add_argument("--quiet", action="store_true", help="Disable tqdm progress bars.")
    return parser.parse_args()


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def get_iou_and_dice(pred: torch.Tensor, label: torch.Tensor) -> tuple[float, float]:
    pred = torch.sigmoid(pred) > 0.5
    label = label > 0
    intersection = torch.logical_and(pred, label).sum(dim=(1, 2, 3))
    union = torch.logical_or(pred, label).sum(dim=(1, 2, 3))
    iou = intersection.float() / (union.float() + 1e-8)
    dice = (2 * intersection.float()) / (pred.sum(dim=(1, 2, 3)) + label.sum(dim=(1, 2, 3)) + 1e-8)
    return iou.mean().item(), dice.mean().item()


def postprocess_mask(pred_masks: torch.Tensor, ori_size: tuple[int, int]) -> torch.Tensor:
    return F.interpolate(pred_masks, ori_size, mode="bilinear")


def interaction(
    model,
    image_embedding: torch.Tensor,
    low_masks: torch.Tensor,
    mask_preds: torch.Tensor,
    labels: torch.Tensor,
    inter_num: int,
    loss_fn,
):
    with torch.no_grad():
        outputs = None
        for _ in range(inter_num - 1):
            prompts = model.supervised_prompts(None, labels, mask_preds, low_masks, "points")
            outputs = model.forward_decoder(image_embedding, prompts)
            mask_preds, low_masks = outputs["masks"], outputs["low_res_masks"]
        if outputs is None:
            raise RuntimeError("interaction() called with inter_num <= 1")
        loss = loss_fn(mask_preds, labels.float(), outputs["iou_pred"])
    return loss, mask_preds


def collect_run_specs(baseline_cfg: dict, only_baseline: str | None) -> tuple[dict[RunSpec, list[dict]], list[str]]:
    unique_runs: dict[RunSpec, list[dict]] = {}
    baseline_order: list[str] = []
    for baseline_name, spec in baseline_cfg["baseline_defs"].items():
        if only_baseline and baseline_name != only_baseline:
            continue
        baseline_order.append(baseline_name)
        for prompt_mode in spec["prompt_modes"]:
            for inter_num in spec["inter_nums"]:
                run_spec = RunSpec(
                    image_size=baseline_cfg["global"]["image_size"],
                    prompt_mode=prompt_mode,
                    inter_num=inter_num,
                )
                unique_runs.setdefault(run_spec, []).append(
                    {
                        "baseline": baseline_name,
                        "title": spec["title"],
                        "description": spec["description"],
                        "role": spec["role"],
                        "downstream_anchor": bool(spec.get("downstream_anchor", False)),
                    }
                )
    return unique_runs, baseline_order


def evaluate_run(
    run_spec: RunSpec,
    paths_cfg: dict,
    baseline_cfg: dict,
    device: torch.device,
    quiet: bool,
) -> dict:
    imis_root = pathlib.Path(paths_cfg["paths"]["imis_bench_root"]).resolve()
    if str(imis_root) not in sys.path:
        sys.path.insert(0, str(imis_root))

    from data_loader import get_loader  # noqa: PLC0415
    from model import IMISNet  # noqa: PLC0415
    from segment_anything import sam_model_registry  # noqa: PLC0415
    from utils import FocalDice_MSELoss  # noqa: PLC0415

    set_seed(baseline_cfg["global"]["seed"])
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

    args = SimpleNamespace(
        data_dir=paths_cfg["paths"]["imis_btcv_root"],
        image_size=run_spec.image_size,
        test_mode=True,
        batch_size=baseline_cfg["global"]["batch_size"],
        num_workers=baseline_cfg["global"]["num_workers"],
        dist=False,
        multi_gpu=False,
        model_type=baseline_cfg["global"]["model_type"],
        sam_checkpoint=paths_cfg["paths"]["imis_checkpoint"],
        device=device,
        mask_num=None,
        prompt_mode=run_spec.prompt_mode,
        inter_num=run_spec.inter_num,
    )

    data_loader = get_loader(args)
    sam = sam_model_registry[args.model_type](args).to(device)
    model = IMISNet(
        sam,
        test_mode=True,
        category_weights=str(imis_root / "dataloaders" / "categories_weight.pkl"),
    ).to(device)
    model.eval()
    loss_fn = FocalDice_MSELoss()

    if device.type == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)

    sample_latencies: list[float] = []
    sample_rows: list[dict] = []
    avg_dice: list[float] = []
    avg_iou: list[float] = []
    avg_loss: list[float] = []

    iterator = data_loader if quiet else tqdm(data_loader, desc=run_spec.run_id)
    for batch_input in iterator:
        sample_start = time.perf_counter()
        images = batch_input["image"].to(device)
        labels = batch_input["label"].to(device).type(torch.long)
        ori_labels = batch_input["ori_label"].to(device).type(torch.long)
        target_list = batch_input["target_list"]
        gt_prompt = batch_input["gt_prompt"]
        image_root = batch_input["image_root"][0]

        image_embedding = model.image_forward(images)

        image_level_losses = []
        image_level_ious = []
        image_level_dices = []

        for cls_idx in range(len(target_list)):
            labels_cls = labels[cls_idx : cls_idx + 1]
            ori_labels_cls = ori_labels[cls_idx : cls_idx + 1]

            if run_spec.prompt_mode == "bboxes":
                prompts = {"bboxes": gt_prompt["bboxes"][cls_idx : cls_idx + 1].to(device)}
            else:
                prompts = {
                    "point_coords": gt_prompt["point_coords"][cls_idx : cls_idx + 1].to(device),
                    "point_labels": gt_prompt["point_labels"][cls_idx : cls_idx + 1].to(device),
                }

            with torch.no_grad():
                outputs = model.forward_decoder(image_embedding, prompts)
                mask_preds, low_masks = outputs["masks"], outputs["low_res_masks"]
                loss = loss_fn(mask_preds, labels_cls.float(), outputs["iou_pred"])

            if run_spec.inter_num > 1:
                image_embedding = model.detach_image_embedding(image_embedding)
                loss, mask_preds = interaction(
                    model,
                    image_embedding,
                    low_masks,
                    mask_preds,
                    labels_cls,
                    run_spec.inter_num,
                    loss_fn,
                )

            ori_preds = postprocess_mask(mask_preds, ori_labels.shape[-2:])
            iou, dice = get_iou_and_dice(ori_preds, ori_labels_cls)

            image_level_losses.append(loss.item())
            image_level_ious.append(iou)
            image_level_dices.append(dice)

        elapsed = time.perf_counter() - sample_start
        mean_loss = float(np.mean(image_level_losses))
        mean_iou = float(np.mean(image_level_ious))
        mean_dice = float(np.mean(image_level_dices))

        sample_latencies.append(elapsed)
        avg_loss.append(mean_loss)
        avg_iou.append(mean_iou)
        avg_dice.append(mean_dice)
        sample_rows.append(
            {
                "image_root": image_root,
                "loss": mean_loss,
                "iou": mean_iou,
                "dice": mean_dice,
                "sample_latency_s": elapsed,
            }
        )

    peak_memory_mb = 0.0
    if device.type == "cuda":
        peak_memory_mb = torch.cuda.max_memory_allocated(device) / (1024 ** 2)

    return {
        "run_id": run_spec.run_id,
        "image_size": run_spec.image_size,
        "prompt_mode": run_spec.prompt_mode,
        "inter_num": run_spec.inter_num,
        "num_cases": len(sample_rows),
        "avg_loss": float(np.mean(avg_loss)),
        "avg_iou": float(np.mean(avg_iou)),
        "avg_dice": float(np.mean(avg_dice)),
        "avg_sample_latency_s": float(np.mean(sample_latencies)),
        "avg_interaction_latency_s": float(np.mean(sample_latencies) / max(run_spec.inter_num, 1)),
        "peak_memory_mb": peak_memory_mb,
        "per_case": sample_rows,
    }


def render_markdown(
    baseline_cfg: dict,
    baseline_rows: list[dict],
    run_results: dict[str, dict],
    output_dir: pathlib.Path,
) -> str:
    lines = [
        "# Phase 1 Baseline Legalization Results",
        "",
        f"- Output dir: `{output_dir}`",
        f"- Primary anchor: `{baseline_cfg['freeze_statement']['primary_anchor']}`",
        "",
        "## Table",
        "",
        "| Baseline | Prompt | K | Avg Dice | Avg IoU | Avg Sample Latency (s) | Avg Interaction Latency (s) | Peak Memory (MB) | Role |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in baseline_rows:
        result = run_results[row["run_id"]]
        lines.append(
            "| {baseline} | {prompt_mode} | {inter_num} | {avg_dice:.4f} | {avg_iou:.4f} | "
            "{avg_sample_latency_s:.4f} | {avg_interaction_latency_s:.4f} | {peak_memory_mb:.1f} | {role} |".format(
                baseline=row["baseline"],
                prompt_mode=result["prompt_mode"],
                inter_num=result["inter_num"],
                avg_dice=result["avg_dice"],
                avg_iou=result["avg_iou"],
                avg_sample_latency_s=result["avg_sample_latency_s"],
                avg_interaction_latency_s=result["avg_interaction_latency_s"],
                peak_memory_mb=result["peak_memory_mb"],
                role=row["role"],
            )
        )

    lines.extend(
        [
            "",
            "## Freeze Statement",
            "",
            f"- Primary downstream anchor: `{baseline_cfg['freeze_statement']['primary_anchor']}`",
        ]
    )
    for item in baseline_cfg["freeze_statement"]["rationale"]:
        lines.append(f"- {item}")
    for item in baseline_cfg["freeze_statement"]["local_scope_note"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    paths_cfg = load_yaml(args.paths_cfg)
    baseline_cfg = load_yaml(args.baseline_cfg)
    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    unique_runs, baseline_order = collect_run_specs(baseline_cfg, args.only_baseline)

    run_results: dict[str, dict] = {}
    baseline_rows: list[dict] = []

    for run_spec, mappings in unique_runs.items():
        print(f"[run] {run_spec.run_id}")
        result = evaluate_run(run_spec, paths_cfg, baseline_cfg, device, args.quiet)
        run_results[result["run_id"]] = result
        for mapping in mappings:
            baseline_rows.append(
                {
                    "baseline": mapping["baseline"],
                    "title": mapping["title"],
                    "description": mapping["description"],
                    "role": mapping["role"],
                    "downstream_anchor": mapping["downstream_anchor"],
                    "run_id": result["run_id"],
                }
            )

    baseline_rows.sort(
        key=lambda row: (
            baseline_order.index(row["baseline"]),
            run_results[row["run_id"]]["prompt_mode"],
            run_results[row["run_id"]]["inter_num"],
        )
    )

    stamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"{stamp}_phase1_baselines.json"
    csv_path = output_dir / f"{stamp}_phase1_baselines.csv"
    md_path = output_dir / f"{stamp}_phase1_baselines.md"
    latest_json = output_dir / "LATEST_phase1_baselines.json"
    latest_csv = output_dir / "LATEST_phase1_baselines.csv"
    latest_md = output_dir / "LATEST_phase1_baselines.md"

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "device": str(device),
        "paths_cfg": args.paths_cfg,
        "baseline_cfg": args.baseline_cfg,
        "rows": [
            {
                **row,
                **{
                    key: value
                    for key, value in run_results[row["run_id"]].items()
                    if key != "per_case"
                },
            }
            for row in baseline_rows
        ],
        "run_results": run_results,
    }
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    fieldnames = [
        "baseline",
        "title",
        "role",
        "run_id",
        "prompt_mode",
        "inter_num",
        "avg_dice",
        "avg_iou",
        "avg_loss",
        "avg_sample_latency_s",
        "avg_interaction_latency_s",
        "peak_memory_mb",
        "num_cases",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in baseline_rows:
            result = run_results[row["run_id"]]
            writer.writerow(
                {
                    "baseline": row["baseline"],
                    "title": row["title"],
                    "role": row["role"],
                    "run_id": row["run_id"],
                    "prompt_mode": result["prompt_mode"],
                    "inter_num": result["inter_num"],
                    "avg_dice": f"{result['avg_dice']:.6f}",
                    "avg_iou": f"{result['avg_iou']:.6f}",
                    "avg_loss": f"{result['avg_loss']:.6f}",
                    "avg_sample_latency_s": f"{result['avg_sample_latency_s']:.6f}",
                    "avg_interaction_latency_s": f"{result['avg_interaction_latency_s']:.6f}",
                    "peak_memory_mb": f"{result['peak_memory_mb']:.2f}",
                    "num_cases": result["num_cases"],
                }
            )

    markdown = render_markdown(baseline_cfg, baseline_rows, run_results, output_dir)
    md_path.write_text(markdown + "\n", encoding="utf-8")

    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_csv.write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"[done] json={json_path}")
    print(f"[done] csv={csv_path}")
    print(f"[done] md={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
