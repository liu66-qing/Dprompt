#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from types import SimpleNamespace

import torch
import yaml


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a 1-batch IMIS-Bench smoke check.")
    project_root = pathlib.Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--imis-root",
        default=None,
        help="IMIS-Bench root. Defaults to <project>/external/IMIS-Bench.",
    )
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
    parser.add_argument("--method", default="B0", help="Method key from phase2_b_methods.yaml.")
    parser.add_argument("--image-size", type=int, default=1024)
    parser.add_argument("--model-type", default="vit_b")
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    cli_args = build_args()
    project_root = pathlib.Path(__file__).resolve().parents[1]
    paths_cfg = load_yaml(cli_args.paths_cfg)
    methods_cfg = load_yaml(cli_args.methods_cfg)
    method_cfg = methods_cfg["method_defs"][cli_args.method]
    imis_root = (
        pathlib.Path(cli_args.imis_root).resolve()
        if cli_args.imis_root
        else pathlib.Path(paths_cfg["paths"]["imis_bench_root"]).resolve()
    )

    if not imis_root.exists():
        raise FileNotFoundError(f"IMIS-Bench root not found: {imis_root}")

    os.chdir(imis_root)
    sys.path.insert(0, str(imis_root))

    from data_loader import get_loader  # noqa: PLC0415
    from model import IMISNet  # noqa: PLC0415
    from segment_anything import sam_model_registry  # noqa: PLC0415

    device = torch.device(cli_args.device if torch.cuda.is_available() else "cpu")
    args = SimpleNamespace(
        data_dir=paths_cfg["paths"]["imis_btcv_root"],
        image_size=cli_args.image_size,
        test_mode=True,
        batch_size=1,
        num_workers=1,
        dist=False,
        multi_gpu=False,
        model_type=cli_args.model_type,
        sam_checkpoint=paths_cfg["paths"]["imis_checkpoint"],
        device=device,
        mask_num=None,
        prompt_mode=methods_cfg["global"]["prompt_mode"],
        inter_num=methods_cfg["global"]["max_interactions"],
        local_adapter_blocks=method_cfg.get("local_adapter_blocks"),
        hsf_blocks=method_cfg.get("hsf_blocks"),
    )

    print(f"device: {device}")
    print(f"method: {cli_args.method}")
    print(f"local_adapter_blocks: {args.local_adapter_blocks}")
    print(f"hsf_blocks: {args.hsf_blocks}")
    loader = get_loader(args)
    batch = next(iter(loader))
    print(f"loaded batch keys: {sorted(batch.keys())}")
    print(f"image shape: {tuple(batch['image'].shape)}")
    print(f"num targets in sample: {len(batch['target_list'])}")

    sam = sam_model_registry[args.model_type](args).to(device)
    imis = IMISNet(sam, test_mode=True, category_weights="dataloaders/categories_weight.pkl").to(device)
    imis.eval()

    images = batch["image"].to(device)
    gt_prompt = batch["gt_prompt"]
    prompts = {
        "point_coords": gt_prompt["point_coords"][0:1].to(device),
        "point_labels": gt_prompt["point_labels"][0:1].to(device),
    }

    with torch.no_grad():
        image_embedding = imis.image_forward(images)
        outputs = imis.forward_decoder(image_embedding, prompts)

    if isinstance(image_embedding, dict):
        print(f"image embedding shape: {tuple(image_embedding['image_embedding'].shape)}")
        print(
            "hierarchical embedding shapes: "
            + ", ".join(str(tuple(t.shape)) for t in image_embedding.get("hierarchical_embeddings", []))
        )
    else:
        print(f"image embedding shape: {tuple(image_embedding.shape)}")
    print(f"mask output shape: {tuple(outputs['masks'].shape)}")
    print(f"low-res mask shape: {tuple(outputs['low_res_masks'].shape)}")
    print(f"iou pred shape: {tuple(outputs['iou_pred'].shape)}")
    print("smoke_status: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
