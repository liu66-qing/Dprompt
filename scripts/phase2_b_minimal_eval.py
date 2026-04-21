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
class MethodSpec:
    name: str
    title: str
    description: str
    local_adapter_blocks: tuple[int, ...]
    hsf_blocks: tuple[int, ...]
    sam_checkpoint: str | None
    downstream_anchor: bool


def parse_args() -> argparse.Namespace:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Evaluate B0/B1/B2/B3 minimal enhancement runs.")
    parser.add_argument(
        "--paths-cfg",
        default=str(project_root / "configs" / "paths.local.yaml"),
        help="Local path configuration.",
    )
    parser.add_argument(
        "--methods-cfg",
        default=str(project_root / "configs" / "phase2_b_methods.yaml"),
        help="B-line method configuration.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(project_root / "results" / "phase2_b_minimal"),
        help="Directory for JSON/CSV/Markdown outputs.",
    )
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--only-method", default=None, help="Optional method filter, e.g. B3.")
    parser.add_argument("--max-cases", type=int, default=None, help="Optional case limit for sanity runs.")
    parser.add_argument("--seed", type=int, default=None, help="Optional override for evaluation seed.")
    parser.add_argument("--skip-freeze-check", action="store_true", help="Skip B0 vs historical A2 verification.")
    parser.add_argument("--quiet", action="store_true", help="Disable tqdm progress bars.")
    return parser.parse_args()


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


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


def mean_curve(curves: list[list[float]]) -> list[float]:
    if not curves:
        return []
    return [float(value) for value in np.mean(np.asarray(curves, dtype=np.float64), axis=0)]


def curve_value_at_step(curve: list[float], step: int) -> float:
    if not curve:
        raise ValueError("curve is empty")
    return float(curve[min(step, len(curve)) - 1])


def first_reach_step(curve: list[float], threshold: float) -> int:
    for idx, value in enumerate(curve, start=1):
        if value >= threshold:
            return idx
    return len(curve) + 1


def resolve_project_path(project_root: pathlib.Path, path_value: str) -> pathlib.Path:
    path = pathlib.Path(path_value)
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def collect_methods(methods_cfg: dict, only_method: str | None) -> list[MethodSpec]:
    methods: list[MethodSpec] = []
    for method_name, spec in methods_cfg["method_defs"].items():
        if only_method and method_name != only_method:
            continue
        methods.append(
            MethodSpec(
                name=method_name,
                title=spec["title"],
                description=spec["description"],
                local_adapter_blocks=tuple(int(v) for v in spec.get("local_adapter_blocks", [])),
                hsf_blocks=tuple(int(v) for v in spec.get("hsf_blocks", [])),
                sam_checkpoint=spec.get("sam_checkpoint"),
                downstream_anchor=bool(spec.get("downstream_anchor", False)),
            )
        )
    return methods


def resolve_checkpoint_path(project_root: pathlib.Path, paths_cfg: dict, method: MethodSpec) -> str:
    if method.sam_checkpoint is None:
        return paths_cfg["paths"]["imis_checkpoint"]
    checkpoint_path = pathlib.Path(method.sam_checkpoint)
    if checkpoint_path.is_absolute():
        return str(checkpoint_path)
    return str((project_root / checkpoint_path).resolve())


def build_eval_args(
    project_root: pathlib.Path,
    paths_cfg: dict,
    methods_cfg: dict,
    device: torch.device,
    method: MethodSpec,
) -> SimpleNamespace:
    global_cfg = methods_cfg["global"]
    return SimpleNamespace(
        data_dir=paths_cfg["paths"]["imis_btcv_root"],
        image_size=global_cfg["image_size"],
        test_mode=True,
        batch_size=global_cfg["batch_size"],
        num_workers=global_cfg["num_workers"],
        dist=False,
        multi_gpu=False,
        model_type=global_cfg["model_type"],
        sam_checkpoint=resolve_checkpoint_path(project_root, paths_cfg, method),
        device=device,
        mask_num=None,
        prompt_mode=global_cfg["prompt_mode"],
        inter_num=global_cfg["max_interactions"],
        local_adapter_blocks=list(method.local_adapter_blocks) if method.local_adapter_blocks else None,
        hsf_blocks=list(method.hsf_blocks) if method.hsf_blocks else None,
    )


def maybe_load_full_model_checkpoint(model, checkpoint_path: str | None, device: torch.device) -> None:
    if checkpoint_path is None:
        return

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    state_dict = checkpoint.get("model_state_dict") if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint else checkpoint
    if not isinstance(state_dict, dict):
        return
    load_result = model.load_state_dict(state_dict, strict=False)
    if load_result.missing_keys:
        print(f"******Model missing keys: {load_result.missing_keys}")
    if load_result.unexpected_keys:
        print(f"******Model unexpected keys: {load_result.unexpected_keys}")


def evaluate_method(
    project_root: pathlib.Path,
    paths_cfg: dict,
    methods_cfg: dict,
    method: MethodSpec,
    device: torch.device,
    quiet: bool,
    max_cases: int | None,
    run_seed: int,
) -> dict:
    global_cfg = methods_cfg["global"]
    set_seed(int(run_seed))
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

    imis_root = pathlib.Path(paths_cfg["paths"]["imis_bench_root"]).resolve()
    if str(imis_root) not in sys.path:
        sys.path.insert(0, str(imis_root))

    from data_loader import get_loader  # noqa: PLC0415
    from model import IMISNet  # noqa: PLC0415
    from segment_anything import sam_model_registry  # noqa: PLC0415

    args = build_eval_args(project_root, paths_cfg, methods_cfg, device, method)
    data_loader = get_loader(args)
    sam = sam_model_registry[args.model_type](args).to(device)
    model = IMISNet(
        sam,
        test_mode=True,
        category_weights=str(imis_root / "dataloaders" / "categories_weight.pkl"),
    ).to(device)
    maybe_load_full_model_checkpoint(model, args.sam_checkpoint if method.sam_checkpoint is not None else None, device)
    model.eval()
    set_seed(int(run_seed))

    if device.type == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)

    sample_rows: list[dict] = []
    iterator = data_loader if quiet else tqdm(data_loader, desc=method.name)
    max_interactions = int(global_cfg["max_interactions"])
    prompt_mode = global_cfg["prompt_mode"]

    for case_idx, batch_input in enumerate(iterator):
        if max_cases is not None and case_idx >= max_cases:
            break

        sample_start = time.perf_counter()
        images = batch_input["image"].to(device)
        labels = batch_input["label"].to(device).type(torch.long)
        ori_labels = batch_input["ori_label"].to(device).type(torch.long)
        target_list = batch_input["target_list"]
        gt_prompt = batch_input["gt_prompt"]
        image_root = batch_input["image_root"][0]

        with torch.no_grad():
            image_embedding = model.image_forward(images)

        detached_embedding = model.detach_image_embedding(image_embedding)
        target_rows: list[dict] = []

        for cls_idx, target_name in enumerate(target_list):
            labels_cls = labels[cls_idx : cls_idx + 1]
            ori_labels_cls = ori_labels[cls_idx : cls_idx + 1]
            prompts = {
                "point_coords": gt_prompt["point_coords"][cls_idx : cls_idx + 1].to(device),
                "point_labels": gt_prompt["point_labels"][cls_idx : cls_idx + 1].to(device),
            }

            dice_curve: list[float] = []
            iou_curve: list[float] = []
            step_latencies: list[float] = []

            with torch.no_grad():
                step_start = time.perf_counter()
                outputs = model.forward_decoder(image_embedding, prompts)
                step_latencies.append(time.perf_counter() - step_start)

            mask_preds = outputs["masks"]
            low_masks = outputs["low_res_masks"]
            ori_preds = postprocess_mask(mask_preds, ori_labels.shape[-2:])
            iou, dice = get_iou_and_dice(ori_preds, ori_labels_cls)
            iou_curve.append(float(iou))
            dice_curve.append(float(dice))

            for _ in range(2, max_interactions + 1):
                prompts = model.supervised_prompts(None, labels_cls, mask_preds, low_masks, prompt_mode)
                with torch.no_grad():
                    step_start = time.perf_counter()
                    outputs = model.forward_decoder(detached_embedding, prompts)
                    step_latencies.append(time.perf_counter() - step_start)
                mask_preds = outputs["masks"]
                low_masks = outputs["low_res_masks"]
                ori_preds = postprocess_mask(mask_preds, ori_labels.shape[-2:])
                iou, dice = get_iou_and_dice(ori_preds, ori_labels_cls)
                iou_curve.append(float(iou))
                dice_curve.append(float(dice))

            target_rows.append(
                {
                    "target_name": str(target_name),
                    "dice_curve": dice_curve,
                    "iou_curve": iou_curve,
                    "step_latencies_s": [float(v) for v in step_latencies],
                    "final_dice": float(dice_curve[-1]),
                    "final_iou": float(iou_curve[-1]),
                }
            )

        sample_latency = time.perf_counter() - sample_start
        image_dice_curve = mean_curve([row["dice_curve"] for row in target_rows])
        image_iou_curve = mean_curve([row["iou_curve"] for row in target_rows])

        sample_rows.append(
            {
                "image_root": image_root,
                "num_targets": len(target_rows),
                "dice_curve": image_dice_curve,
                "iou_curve": image_iou_curve,
                "final_dice": float(image_dice_curve[-1]),
                "final_iou": float(image_iou_curve[-1]),
                "sample_latency_s": float(sample_latency),
                "avg_interaction_latency_s": float(sample_latency / max_interactions),
                "targets": target_rows,
            }
        )

    peak_memory_mb = 0.0
    if device.type == "cuda":
        peak_memory_mb = torch.cuda.max_memory_allocated(device) / (1024 ** 2)

    per_case_noc = [first_reach_step(row["dice_curve"], float(global_cfg["noc_threshold"])) for row in sample_rows]
    report_steps = [int(value) for value in global_cfg["report_interactions"]]
    dice_at = {
        str(step): float(np.mean([curve_value_at_step(row["dice_curve"], step) for row in sample_rows]))
        for step in report_steps
    }
    iou_at = {
        str(step): float(np.mean([curve_value_at_step(row["iou_curve"], step) for row in sample_rows]))
        for step in report_steps
    }

    result = {
        "method": method.name,
        "title": method.title,
        "description": method.description,
        "local_adapter_blocks": list(method.local_adapter_blocks),
        "hsf_blocks": list(method.hsf_blocks),
        "sam_checkpoint": args.sam_checkpoint,
        "downstream_anchor": method.downstream_anchor,
        "prompt_mode": prompt_mode,
        "max_interactions": max_interactions,
        "num_cases": len(sample_rows),
        "num_targets": int(sum(row["num_targets"] for row in sample_rows)),
        "avg_dice": float(np.mean([row["final_dice"] for row in sample_rows])),
        "avg_iou": float(np.mean([row["final_iou"] for row in sample_rows])),
        "dice_at": dice_at,
        "iou_at": iou_at,
        "noc_threshold": float(global_cfg["noc_threshold"]),
        "noc_at_threshold": float(np.mean(per_case_noc)) if per_case_noc else 0.0,
        "avg_sample_latency_s": float(np.mean([row["sample_latency_s"] for row in sample_rows])) if sample_rows else 0.0,
        "avg_interaction_latency_s": float(np.mean([row["avg_interaction_latency_s"] for row in sample_rows])) if sample_rows else 0.0,
        "peak_memory_mb": float(peak_memory_mb),
        "per_case": sample_rows,
    }

    del model
    del sam
    if device.type == "cuda":
        torch.cuda.empty_cache()

    return result


def attach_delta_vs_anchor(method_results: dict[str, dict], report_steps: list[int], anchor_name: str) -> None:
    if anchor_name not in method_results:
        return

    anchor = method_results[anchor_name]
    for method_name, result in method_results.items():
        result["delta_vs_anchor"] = {
            "anchor": anchor_name,
            "avg_dice": float(result["avg_dice"] - anchor["avg_dice"]),
            "avg_iou": float(result["avg_iou"] - anchor["avg_iou"]),
            "noc_at_threshold": float(result["noc_at_threshold"] - anchor["noc_at_threshold"]),
            "avg_interaction_latency_s": float(result["avg_interaction_latency_s"] - anchor["avg_interaction_latency_s"]),
            "peak_memory_mb": float(result["peak_memory_mb"] - anchor["peak_memory_mb"]),
            "latency_ratio": (
                float(result["avg_interaction_latency_s"] / anchor["avg_interaction_latency_s"])
                if anchor["avg_interaction_latency_s"] > 0
                else None
            ),
            "memory_ratio": (
                float(result["peak_memory_mb"] / anchor["peak_memory_mb"])
                if anchor["peak_memory_mb"] > 0
                else None
            ),
        }
        for step in report_steps:
            key = str(step)
            result["delta_vs_anchor"][f"dice_at_{key}"] = float(result["dice_at"][key] - anchor["dice_at"][key])
            result["delta_vs_anchor"][f"iou_at_{key}"] = float(result["iou_at"][key] - anchor["iou_at"][key])


def load_historical_reference(project_root: pathlib.Path, methods_cfg: dict) -> dict:
    global_cfg = methods_cfg["global"]
    history_path = resolve_project_path(project_root, global_cfg["historical_baseline_json"])
    with open(history_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    reference_cfg = global_cfg["freeze_reference"]
    for row in payload["rows"]:
        if (
            row["baseline"] == reference_cfg["baseline"]
            and row["prompt_mode"] == reference_cfg["prompt_mode"]
            and int(row["inter_num"]) == int(reference_cfg["inter_num"])
        ):
            return {
                "history_path": str(history_path),
                "baseline": row["baseline"],
                "prompt_mode": row["prompt_mode"],
                "inter_num": int(row["inter_num"]),
                "avg_dice": float(row["avg_dice"]),
                "avg_iou": float(row["avg_iou"]),
                "avg_interaction_latency_s": float(row["avg_interaction_latency_s"]),
                "peak_memory_mb": float(row["peak_memory_mb"]),
                "run_id": row["run_id"],
            }
    raise KeyError(f"Historical baseline reference not found in {history_path}")


def build_freeze_check(current_b0: dict | None, methods_cfg: dict, project_root: pathlib.Path) -> dict:
    historical = load_historical_reference(project_root, methods_cfg)
    if current_b0 is None:
        return {
            "status": "skipped",
            "reason": "B0 was not part of this invocation.",
            "historical_reference": historical,
        }

    tolerance_cfg = methods_cfg["global"]["freeze_tolerance"]
    avg_dice_delta = float(current_b0["avg_dice"] - historical["avg_dice"])
    avg_iou_delta = float(current_b0["avg_iou"] - historical["avg_iou"])
    freeze_pass = (
        abs(avg_dice_delta) <= float(tolerance_cfg["avg_dice_abs"])
        and abs(avg_iou_delta) <= float(tolerance_cfg["avg_iou_abs"])
    )

    return {
        "status": "pass" if freeze_pass else "fail",
        "historical_reference": historical,
        "current_b0": {
            "avg_dice": float(current_b0["avg_dice"]),
            "avg_iou": float(current_b0["avg_iou"]),
            "avg_interaction_latency_s": float(current_b0["avg_interaction_latency_s"]),
            "peak_memory_mb": float(current_b0["peak_memory_mb"]),
        },
        "delta": {
            "avg_dice": avg_dice_delta,
            "avg_iou": avg_iou_delta,
            "avg_interaction_latency_s": float(current_b0["avg_interaction_latency_s"] - historical["avg_interaction_latency_s"]),
            "peak_memory_mb": float(current_b0["peak_memory_mb"] - historical["peak_memory_mb"]),
        },
        "tolerance": {
            "avg_dice_abs": float(tolerance_cfg["avg_dice_abs"]),
            "avg_iou_abs": float(tolerance_cfg["avg_iou_abs"]),
        },
    }


def render_markdown(
    output_dir: pathlib.Path,
    methods_cfg: dict,
    method_results: dict[str, dict],
    method_order: list[str],
    freeze_check: dict,
    anchor_name: str,
) -> str:
    report_steps = [int(value) for value in methods_cfg["global"]["report_interactions"]]
    threshold = float(methods_cfg["global"]["noc_threshold"])

    lines = [
        "# Phase 2 B-Line Minimal Results",
        "",
        f"- Output dir: `{output_dir}`",
        f"- Prompt mode: `{methods_cfg['global']['prompt_mode']}`",
        f"- Max interactions: `{methods_cfg['global']['max_interactions']}`",
        "",
        "## Summary Table",
        "",
        f"| Method | Dice@3 | Dice@5 | Dice@8 | NoC@90 | Avg Interaction Latency (s) | Peak Memory (MB) | Delta Dice@5 vs {anchor_name} |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for method_name in method_order:
        result = method_results[method_name]
        dice_values = {step: result["dice_at"].get(str(step), float("nan")) for step in report_steps}
        lines.append(
            "| {method} | {dice3:.4f} | {dice5:.4f} | {dice8:.4f} | {noc:.3f} | {lat:.4f} | {mem:.1f} | {delta:.4f} |".format(
                method=method_name,
                dice3=dice_values.get(3, float("nan")),
                dice5=dice_values.get(5, float("nan")),
                dice8=dice_values.get(8, float("nan")),
                noc=result["noc_at_threshold"],
                lat=result["avg_interaction_latency_s"],
                mem=result["peak_memory_mb"],
                delta=result.get("delta_vs_anchor", {}).get("dice_at_5", 0.0),
            )
        )

    lines.extend(
        [
            "",
            "## B0 Freeze Check",
            "",
            f"- Threshold: `NoC@{int(threshold * 100)}`",
            f"- Status: `{freeze_check['status']}`",
        ]
    )

    historical = freeze_check.get("historical_reference")
    if historical:
        lines.append(
            "- Historical reference: `{baseline}` / `{prompt}` / `K={k}` from `{run_id}`".format(
                baseline=historical["baseline"],
                prompt=historical["prompt_mode"],
                k=historical["inter_num"],
                run_id=historical["run_id"],
            )
        )
        lines.append(f"- Historical avg_dice: `{historical['avg_dice']:.6f}`")
        lines.append(f"- Historical avg_iou: `{historical['avg_iou']:.6f}`")

    if freeze_check["status"] == "skipped":
        lines.append(f"- Reason: {freeze_check['reason']}")
    else:
        current = freeze_check["current_b0"]
        delta = freeze_check["delta"]
        lines.append(f"- Current B0 avg_dice: `{current['avg_dice']:.6f}`")
        lines.append(f"- Current B0 avg_iou: `{current['avg_iou']:.6f}`")
        lines.append(f"- Delta avg_dice: `{delta['avg_dice']:+.6f}`")
        lines.append(f"- Delta avg_iou: `{delta['avg_iou']:+.6f}`")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    project_root = pathlib.Path(__file__).resolve().parents[1]
    paths_cfg = load_yaml(args.paths_cfg)
    methods_cfg = load_yaml(args.methods_cfg)
    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    run_seed = int(args.seed) if args.seed is not None else int(methods_cfg["global"]["seed"])
    methods = collect_methods(methods_cfg, args.only_method)
    method_results: dict[str, dict] = {}
    method_order = [method.name for method in methods]

    if not methods:
        raise ValueError("No methods selected for evaluation.")

    for method in methods:
        print(f"[run] {method.name}")
        method_results[method.name] = evaluate_method(
            project_root=project_root,
            paths_cfg=paths_cfg,
            methods_cfg=methods_cfg,
            method=method,
            device=device,
            quiet=args.quiet,
            max_cases=args.max_cases,
            run_seed=run_seed,
        )

    report_steps = [int(value) for value in methods_cfg["global"]["report_interactions"]]
    anchor_name = methods_cfg["global"].get("comparison_anchor", "B0")
    attach_delta_vs_anchor(method_results, report_steps, anchor_name)

    if args.skip_freeze_check:
        freeze_check = {"status": "skipped", "reason": "--skip-freeze-check was set."}
    else:
        freeze_check = build_freeze_check(method_results.get("B0"), methods_cfg, project_root)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"{stamp}_phase2_b_minimal.json"
    csv_path = output_dir / f"{stamp}_phase2_b_minimal.csv"
    md_path = output_dir / f"{stamp}_phase2_b_minimal.md"
    latest_json = output_dir / "LATEST_phase2_b_minimal.json"
    latest_csv = output_dir / "LATEST_phase2_b_minimal.csv"
    latest_md = output_dir / "LATEST_phase2_b_minimal.md"

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "device": str(device),
        "seed": run_seed,
        "paths_cfg": args.paths_cfg,
        "methods_cfg": args.methods_cfg,
        "method_order": method_order,
        "comparison_anchor": anchor_name,
        "freeze_check": freeze_check,
        "method_results": method_results,
    }
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    fieldnames = [
        "method",
        "title",
        "avg_dice",
        "avg_iou",
        "dice_at_3",
        "dice_at_5",
        "dice_at_8",
        "noc_at_threshold",
        "avg_interaction_latency_s",
        "peak_memory_mb",
        "delta_dice_at_5_vs_anchor",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for method_name in method_order:
            result = method_results[method_name]
            writer.writerow(
                {
                    "method": method_name,
                    "title": result["title"],
                    "avg_dice": f"{result['avg_dice']:.6f}",
                    "avg_iou": f"{result['avg_iou']:.6f}",
                    "dice_at_3": f"{result['dice_at'].get('3', float('nan')):.6f}",
                    "dice_at_5": f"{result['dice_at'].get('5', float('nan')):.6f}",
                    "dice_at_8": f"{result['dice_at'].get('8', float('nan')):.6f}",
                    "noc_at_threshold": f"{result['noc_at_threshold']:.6f}",
                    "avg_interaction_latency_s": f"{result['avg_interaction_latency_s']:.6f}",
                    "peak_memory_mb": f"{result['peak_memory_mb']:.2f}",
                    "delta_dice_at_5_vs_anchor": f"{result.get('delta_vs_anchor', {}).get('dice_at_5', 0.0):.6f}",
                }
            )

    markdown = render_markdown(output_dir, methods_cfg, method_results, method_order, freeze_check, anchor_name)
    md_path.write_text(markdown + "\n", encoding="utf-8")
    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_csv.write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"[done] json={json_path}")
    print(f"[done] csv={csv_path}")
    print(f"[done] md={md_path}")
    print(f"[freeze] status={freeze_check['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
