#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import yaml
from matplotlib.colors import to_rgb
from PIL import Image


def parse_args() -> argparse.Namespace:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Render representative T0 vs T2 qualitative cases.")
    parser.add_argument(
        "--paths-cfg",
        default=str(project_root / "configs" / "paths.local.yaml"),
        help="Local path configuration.",
    )
    parser.add_argument(
        "--diagnosis-json",
        default=str(project_root / "results" / "phase2_5_t2_diagnosis" / "LATEST_phase2_5_t2_diagnosis.json"),
        help="Diagnosis summary with representative cases.",
    )
    parser.add_argument(
        "--figure-dir",
        default=str(project_root / "figures"),
        help="Directory for generated qualitative figure.",
    )
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--step", type=int, default=5, help="Interaction step to visualize.")
    return parser.parse_args()


def load_yaml(path: pathlib.Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_eval_args(paths_cfg: dict, device: torch.device, hsf_blocks: list[int] | None) -> SimpleNamespace:
    return SimpleNamespace(
        data_dir=paths_cfg["paths"]["imis_btcv_root"],
        image_size=1024,
        test_mode=True,
        batch_size=1,
        num_workers=1,
        dist=False,
        multi_gpu=False,
        model_type="vit_b",
        sam_checkpoint=paths_cfg["paths"]["imis_checkpoint"],
        device=device,
        mask_num=None,
        prompt_mode="points",
        inter_num=8,
        local_adapter_blocks=None,
        hsf_blocks=hsf_blocks,
    )


def overlay_mask(ax, image: np.ndarray, mask: np.ndarray | None, gt_mask: np.ndarray | None, title: str, color: str) -> None:
    ax.imshow(image, cmap="gray", vmin=float(image.min()), vmax=float(image.max()))
    if mask is not None and mask.any():
        overlay = np.zeros((*mask.shape, 4), dtype=np.float32)
        overlay[..., :3] = to_rgb(color)
        overlay[..., 3] = mask.astype(np.float32) * 0.38
        ax.imshow(overlay, interpolation="nearest")
    if gt_mask is not None and gt_mask.any():
        ax.contour(gt_mask.astype(float), levels=[0.5], colors="yellow", linewidths=1.0)
    ax.set_title(title, fontsize=9)
    ax.axis("off")


def compute_crop(gt_mask: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray, pad: int = 18) -> tuple[slice, slice]:
    union = gt_mask | pred_a | pred_b
    ys, xs = np.where(union)
    if len(ys) == 0:
        return slice(0, gt_mask.shape[0]), slice(0, gt_mask.shape[1])
    y0 = max(int(ys.min()) - pad, 0)
    y1 = min(int(ys.max()) + pad + 1, gt_mask.shape[0])
    x0 = max(int(xs.min()) - pad, 0)
    x1 = min(int(xs.max()) + pad + 1, gt_mask.shape[1])
    return slice(y0, y1), slice(x0, x1)


def main() -> int:
    args = parse_args()
    diagnosis_payload = json.loads(pathlib.Path(args.diagnosis_json).read_text(encoding="utf-8"))
    representatives = diagnosis_payload.get("representative_cases", [])
    if not representatives:
        raise ValueError("No representative cases found in diagnosis json.")

    qual_seed = int(diagnosis_payload.get("qualitative_seed", 42))
    paths_cfg = load_yaml(pathlib.Path(args.paths_cfg))
    project_root = pathlib.Path(args.paths_cfg).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    imis_root = pathlib.Path(paths_cfg["paths"]["imis_bench_root"]).resolve()
    if str(imis_root) not in sys.path:
        sys.path.insert(0, str(imis_root))

    from data_loader import get_loader  # noqa: PLC0415
    from model import IMISNet  # noqa: PLC0415
    from segment_anything import sam_model_registry  # noqa: PLC0415
    from scripts.phase2_b_minimal_eval import get_iou_and_dice, maybe_load_full_model_checkpoint, postprocess_mask, set_seed  # noqa: PLC0415

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    set_seed(qual_seed)
    loader_args = build_eval_args(paths_cfg, device, hsf_blocks=None)
    dataloader = get_loader(loader_args)

    selected_images = {row["image_root"] for row in representatives}
    case_batches: dict[str, dict] = {}
    for batch in dataloader:
        image_root = batch["image_root"][0]
        if image_root in selected_images:
            case_batches[image_root] = batch
        if len(case_batches) == len(selected_images):
            break

    t0_args = build_eval_args(paths_cfg, device, hsf_blocks=None)
    t2_args = build_eval_args(paths_cfg, device, hsf_blocks=[9, 10, 11])

    t0_sam = sam_model_registry[t0_args.model_type](t0_args).to(device)
    t2_sam = sam_model_registry[t2_args.model_type](t2_args).to(device)
    t0_model = IMISNet(t0_sam, test_mode=True, category_weights=str(imis_root / "dataloaders" / "categories_weight.pkl")).to(device)
    t2_model = IMISNet(t2_sam, test_mode=True, category_weights=str(imis_root / "dataloaders" / "categories_weight.pkl")).to(device)

    t2_ckpt = (
        project_root
        / "external"
        / "IMIS-Bench"
        / "work_dir"
        / "phase2_4_t2_confirmation"
        / f"T2_hsf_only_seed{qual_seed}"
        / "IMIS_latest.pth"
    )
    maybe_load_full_model_checkpoint(t2_model, str(t2_ckpt), device)
    t0_model.eval()
    t2_model.eval()

    figure_dir = pathlib.Path(args.figure_dir).resolve()
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(representatives), 4, figsize=(11, 2.8 * len(representatives)))
    if len(representatives) == 1:
        axes = np.expand_dims(axes, axis=0)

    for row_idx, rep in enumerate(representatives):
        batch = case_batches[rep["image_root"]]
        image_root = rep["image_root"]
        target_name = rep["target_name"]
        target_index = batch["target_list"].index(target_name)
        image = batch["image"].to(device)
        labels = batch["label"].to(device).type(torch.long)
        ori_labels = batch["ori_label"].to(device).type(torch.long)
        gt_prompt = batch["gt_prompt"]
        labels_cls = labels[target_index : target_index + 1]
        ori_labels_cls = ori_labels[target_index : target_index + 1]
        prompts = {
            "point_coords": gt_prompt["point_coords"][target_index : target_index + 1].to(device),
            "point_labels": gt_prompt["point_labels"][target_index : target_index + 1].to(device),
        }

        outputs_by_method = {}
        for method_name, model in (("T0", t0_model), ("T2", t2_model)):
            with torch.no_grad():
                image_embedding = model.image_forward(image)
                detached_embedding = model.detach_image_embedding(image_embedding)
                current_prompts = prompts
                outputs = model.forward_decoder(image_embedding, current_prompts)
                mask_preds = outputs["masks"]
                low_masks = outputs["low_res_masks"]
                for _ in range(2, args.step + 1):
                    current_prompts = model.supervised_prompts(None, labels_cls, mask_preds, low_masks, "points")
                    outputs = model.forward_decoder(detached_embedding, current_prompts)
                    mask_preds = outputs["masks"]
                    low_masks = outputs["low_res_masks"]
                ori_preds = postprocess_mask(mask_preds, ori_labels_cls.shape[-2:])
                _, dice = get_iou_and_dice(ori_preds, ori_labels_cls)
                outputs_by_method[method_name] = {
                    "mask": (torch.sigmoid(ori_preds)[0, 0].detach().cpu().numpy() > 0.5),
                    "dice": float(dice),
                }

        raw_image = np.asarray(Image.open(image_root).convert("L"), dtype=np.float32)
        gt_mask = (ori_labels_cls[0, 0].detach().cpu().numpy() > 0)
        t0_mask = outputs_by_method["T0"]["mask"]
        t2_mask = outputs_by_method["T2"]["mask"]
        ys, xs = compute_crop(gt_mask, t0_mask, t2_mask)

        image_crop = raw_image[ys, xs]
        gt_crop = gt_mask[ys, xs]
        t0_crop = t0_mask[ys, xs]
        t2_crop = t2_mask[ys, xs]

        overlay_mask(axes[row_idx, 0], image_crop, None, gt_crop, "Image", "royalblue")
        overlay_mask(axes[row_idx, 1], image_crop, gt_crop, None, "GT", "orange")
        overlay_mask(
            axes[row_idx, 2],
            image_crop,
            t0_crop,
            gt_crop,
            f"T0 @ {args.step}\nDice={outputs_by_method['T0']['dice']:.3f}",
            "crimson",
        )
        overlay_mask(
            axes[row_idx, 3],
            image_crop,
            t2_crop,
            gt_crop,
            f"T2 @ {args.step}\nDice={outputs_by_method['T2']['dice']:.3f}",
            "dodgerblue",
        )

        row_label = (
            f"{rep['bucket']}\n"
            f"{pathlib.Path(image_root).name} / {target_name}\n"
            f"mean delta Dice@5={rep['delta_dice5_mean']:+.3f}"
        )
        axes[row_idx, 0].text(
            -0.36,
            0.5,
            row_label,
            transform=axes[row_idx, 0].transAxes,
            ha="right",
            va="center",
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
        )

    fig.suptitle(
        f"Phase 2.5 Representative Cases (selected by 3-seed mean, visualized with seed {qual_seed})",
        fontsize=11,
        y=0.995,
    )
    fig.tight_layout(rect=(0.08, 0, 1, 0.98))
    png_path = figure_dir / "phase2_5_t2_representative_cases.png"
    pdf_path = figure_dir / "phase2_5_t2_representative_cases.pdf"
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)

    print(f"[done] png={png_path}")
    print(f"[done] pdf={pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
