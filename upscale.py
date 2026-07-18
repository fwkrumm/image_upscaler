#!/usr/bin/env python3
"""Standalone Real-ESRGAN upscaler — no dependency on generate.py.

Reads all images from input_directory, upscales via Real-ESRGAN x4plus,
resizes to output_width × output_height, and saves to output_directory.

Usage:
    python upscale.py                                    # uses config_upscale.json
    python upscale.py --config /other/path/config.json
    python upscale.py --input ./raw --output ./print
    python upscale.py --width 4960 --height 7016        # A4 @ 600 DPI
    python upscale.py --overwrite                        # re-process existing outputs
    python upscale.py --lanczos                          # skip Real-ESRGAN, PIL only

Prerequisites:
    pip install -r requirements_upscale.txt
"""

import argparse
import copy
import json
import sys
import time
import traceback
import types
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image


# ─────────────────────────────── Config ──────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_config(config: dict, args: argparse.Namespace) -> dict:
    cfg = copy.deepcopy(config)

    if args.input is not None:
        cfg["input_directory"] = args.input
    if args.output is not None:
        cfg["output_directory"] = args.output
    if args.width is not None:
        cfg["output_width"] = args.width
    if args.height is not None:
        cfg["output_height"] = args.height
    if args.overwrite:
        cfg["skip_existing"] = False
    if args.lanczos:
        cfg["upscaler"]["force_lanczos"] = True

    return cfg


# ─────────────────────────────── CLI ─────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Upscale images to target resolution via Real-ESRGAN + PIL",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--config",    default="config_upscale.json", help="Config file (default: config_upscale.json)")
    p.add_argument("--input",     help="Input directory  (overrides config)")
    p.add_argument("--output",    help="Output directory (overrides config)")
    p.add_argument("--width",     type=int, help="Output width  in pixels (overrides config)")
    p.add_argument("--height",    type=int, help="Output height in pixels (overrides config)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite already-upscaled files in output dir")
    p.add_argument("--lanczos",   action="store_true", help="Skip Real-ESRGAN, use PIL Lanczos only")
    return p


# ─────────────────────────────── Upscaler ────────────────────────────────────

def _patch_basicsr_torchvision() -> None:
    """basicsr references torchvision.transforms.functional_tensor removed in 0.16+.
    Inject a shim so the import resolves without touching the installed package."""
    import sys
    if "torchvision.transforms.functional_tensor" not in sys.modules:
        import torchvision.transforms.functional as _F
        _shim = types.ModuleType("torchvision.transforms.functional_tensor")
        _shim.rgb_to_grayscale = _F.rgb_to_grayscale
        sys.modules["torchvision.transforms.functional_tensor"] = _shim


def load_upscaler(upscaler_cfg: dict, force_lanczos: bool = False) -> tuple[Any, str]:
    if force_lanczos:
        print("[upscaler] PIL Lanczos mode (--lanczos flag).")
        return None, "lanczos"

    try:
        _patch_basicsr_torchvision()
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer

        model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=upscaler_cfg["scale"],
        )
        upsampler = RealESRGANer(
            scale=upscaler_cfg["scale"],
            model_path=upscaler_cfg["model_url"],
            model=model,
            tile=upscaler_cfg.get("tile", 512),
            tile_pad=upscaler_cfg.get("tile_pad", 32),
            pre_pad=0,
            half=True,
        )
        print("[upscaler] Real-ESRGAN x4plus loaded.")
        return upsampler, "realesrgan"

    except Exception as exc:
        print("[WARNING] Real-ESRGAN failed to load — falling back to PIL Lanczos.")
        print(f"          Reason: {type(exc).__name__}: {exc}")
        print("          Full traceback:")
        traceback.print_exc()
        print()
        return None, "lanczos"


def upscale_image(
    img: Image.Image,
    upsampler: Any,
    mode: str,
    target_w: int,
    target_h: int,
) -> Image.Image:
    if mode == "realesrgan":
        import numpy as np
        img_np = np.array(img.convert("RGB"))
        output, _ = upsampler.enhance(img_np)
        upscaled = Image.fromarray(output)
    else:
        upscaled = img

    if upscaled.size != (target_w, target_h):
        upscaled = upscaled.resize((target_w, target_h), Image.LANCZOS)
    return upscaled


# ─────────────────────────────── Main ────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cfg = merge_config(load_config(args.config), args)

    input_dir    = Path(cfg["input_directory"])
    output_dir   = Path(cfg["output_directory"])
    target_w     = cfg["output_width"]
    target_h     = cfg["output_height"]
    out_format   = cfg.get("output_format", "PNG").upper()
    skip_exists  = cfg.get("skip_existing", True)
    formats      = {ext.lower() for ext in cfg.get("supported_formats", [".png", ".jpg", ".jpeg", ".webp"])}
    upscaler_cfg = cfg["upscaler"]
    force_lanczos = upscaler_cfg.get("force_lanczos", False)

    if not input_dir.exists():
        print(f"[ERROR] Input directory does not exist: {input_dir.resolve()}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect images
    candidates = [p for p in sorted(input_dir.iterdir()) if p.suffix.lower() in formats]
    if not candidates:
        print(f"[INFO] No supported images found in {input_dir.resolve()}")
        print(f"       Supported formats: {', '.join(sorted(formats))}")
        sys.exit(0)

    print(f"Found {len(candidates)} image(s) in {input_dir.resolve()}")
    print(f"Target resolution : {target_w}×{target_h}  |  format: {out_format}")
    print(f"Output directory  : {output_dir.resolve()}\n")

    upsampler, upscale_mode = load_upscaler(upscaler_cfg, force_lanczos)

    out_ext   = ".png" if out_format == "PNG" else ".jpg"
    done = skipped = failed = 0

    for idx, src_path in enumerate(candidates, 1):
        out_name = src_path.stem + "_upscaled" + out_ext
        out_path = output_dir / out_name

        if skip_exists and out_path.exists():
            print(f"[{idx}/{len(candidates)}] Skip (exists): {out_path.name}")
            skipped += 1
            continue

        t_start = time.time()
        try:
            img = Image.open(src_path)
            src_w, src_h = img.size
            print(f"[{idx}/{len(candidates)}] {src_path.name}  ({src_w}×{src_h}) → {target_w}×{target_h} ...")

            result = upscale_image(img, upsampler, upscale_mode, target_w, target_h)

            if out_format == "PNG":
                result.save(str(out_path), "PNG")
            else:
                result.convert("RGB").save(str(out_path), "JPEG", quality=95)

            elapsed = time.time() - t_start
            print(f"[{idx}/{len(candidates)}] Saved → {out_path.name}  ({elapsed:.1f}s)")
            done += 1

        except Exception as exc:
            print(f"[{idx}/{len(candidates)}] ERROR processing {src_path.name}: {exc}")
            failed += 1

    print(f"\nDone. processed={done}  skipped={skipped}  failed={failed}")
    print(f"Output: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
