# AGENTS_upscale.md — Standalone Real-ESRGAN Image Upscaler

## Project purpose
Batch-upscales images from an input directory to a target resolution using
Real-ESRGAN x4plus. Designed to run independently — no dependency on `generate.py`.
Primary use case: bring AI-generated previews or any source images up to
DIN A4 @ 300 DPI (2480×3508 px) for print.

## Files
| File | Role |
|---|---|
| `upscale.py` | Main entry point — batch upscale pipeline |
| `config_upscale.json` | Runtime defaults (input/output dirs, target dims, upscaler) |
| `requirements.txt` | Python dependencies (torch cu124, Pillow, Real-ESRGAN) |

## Environment setup
```powershell
# Install dependencies (no HuggingFace auth needed — no gated models)
uv pip install -r requirements.txt
# or: pip install -r requirements.txt
```

Real-ESRGAN model weights (~67 MB) are downloaded automatically on first run
from GitHub releases and cached locally by the `realesrgan` library.

**Windows prerequisite for `basicsr`:**
Microsoft Visual C++ Build Tools must be installed:
https://visualstudio.microsoft.com/visual-cpp-build-tools/

## Running
```powershell
# Process all images in ./input → ./output_upscaled at 2480×3508 (DIN A4 @ 300 DPI)
python upscale.py

# Custom input/output paths (absolute or relative)
python upscale.py --input D:\raw_renders --output D:\print_ready

# Different target resolution (A4 @ 600 DPI)
python upscale.py --width 4960 --height 7016

# Re-process files already present in output dir
python upscale.py --overwrite

# Skip Real-ESRGAN, use PIL Lanczos only (no GPU needed, lower quality)
python upscale.py --lanczos

# Use a config file at a different path
python upscale.py --config /path/to/config_upscale.json
```

## config_upscale.json reference
```json
{
  "input_directory":  "./input",           // source images folder
  "output_directory": "./output_upscaled", // upscaled images folder (auto-created)
  "output_width":     2480,                // target width  (px) — DIN A4 @ 300 DPI
  "output_height":    3508,                // target height (px) — DIN A4 @ 300 DPI
  "output_format":    "PNG",               // PNG | JPEG
  "skip_existing":    true,                // skip files already in output dir
  "supported_formats": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"],
  "upscaler": {
    "model_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    "scale":     4,     // upscale factor applied by Real-ESRGAN before final resize
    "tile":      512,   // tile size for tiled inference (reduces VRAM usage)
    "tile_pad":  32     // tile overlap to avoid seam artifacts
  }
}
```

## CLI argument reference
| Argument | Type | Description |
|---|---|---|
| `--config PATH` | str | Config file path (default: `config_upscale.json`) |
| `--input PATH` | str | Input directory (overrides config) |
| `--output PATH` | str | Output directory (overrides config) |
| `--width N` | int | Output width in pixels (overrides config) |
| `--height N` | int | Output height in pixels (overrides config) |
| `--overwrite` | flag | Re-process files already present in output dir |
| `--lanczos` | flag | Force PIL Lanczos upscale (skip Real-ESRGAN) |

## Processing pipeline per image
1. Open source image with Pillow (any supported format)
2. Convert to RGB numpy array
3. Real-ESRGAN 4x upscale → intermediate at ~4× source dimensions
4. PIL LANCZOS resize to exact `output_width × output_height`
5. Save as PNG (or JPEG with quality 95) to output directory

Output filenames: `{original_stem}_upscaled.png` — originals are never modified.

## Resolution guide
| Use case | Width | Height |
|---|---|---|
| DIN A4 @ 72 DPI (screen) | 595 | 842 |
| DIN A4 @ 150 DPI | 1240 | 1754 |
| **DIN A4 @ 300 DPI (print, default)** | **2480** | **3508** |
| DIN A4 @ 600 DPI (high-end print) | 4960 | 7016 |
| A3 @ 300 DPI | 3508 | 4961 |

## Hardware notes (RTX 3090 / 24 GB VRAM)
- Real-ESRGAN runs with `half=True` (fp16) on GPU — fast and VRAM-efficient.
- Tiled inference (`tile=512`, `tile_pad=32`) keeps VRAM usage bounded regardless
  of source image size; safe for very large inputs.
- Typical throughput: ~10–30 s per image depending on source size.
- `--lanczos` mode uses CPU only (no GPU required) but produces lower quality results.

## Known issues / gotchas
- **`functional_tensor` error**: patched automatically at runtime via a torchvision
  shim. `basicsr` references a module removed in torchvision 0.16+; the shim injects
  it before the import resolves. No manual fix needed.
- **JPEG output**: saved at quality 95. For print workflows, prefer PNG to avoid
  compression artifacts.
- **Alpha channels**: source images with transparency (RGBA) are converted to RGB
  before upscaling. The alpha channel is discarded.
- **`skip_existing: true`**: files are matched by output filename (`stem_upscaled.ext`).
  If you change `output_width`/`output_height`, set `--overwrite` to re-process.
