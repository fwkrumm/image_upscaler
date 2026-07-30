# Real-ESRGAN Batch Upscaler (AI GENERATED)

A standalone Python tool that upscales images in bulk using **Real-ESRGAN x4plus** and then resizes them to an exact target resolution (for example, print-ready A4 dimensions).

This project is built for a simple workflow: drop files into an input folder, run one command, get consistently sized high-quality outputs in an output folder.

## Why This Exists

AI previews, web exports, and low-resolution source renders are often too small for print or production use. This tool exists to:

- improve perceptual quality with Real-ESRGAN super-resolution,
- enforce a precise final size (width x height),
- process many files in one run,
- work independently (no dependency on other project scripts).

## What It Does

For each supported image in the input directory, the pipeline is:

1. load image with Pillow,
2. run Real-ESRGAN x4 upscaling (or optional Lanczos-only mode),
3. resize to exact target dimensions with Lanczos,
4. save to output directory as `PNG` or `JPEG`.

Output files are written as:

- `{original_name}_upscaled.png` (or `.jpg` for JPEG mode)

Original files are never modified.

## Key Features

- Batch processing of all supported images in one folder
- Real-ESRGAN x4plus enhancement with automatic model download
- Exact output dimensions for print or standardized delivery
- Optional `--lanczos` fallback mode (CPU-only, no Real-ESRGAN)
- Skip-existing behavior for resumable runs
- CLI overrides for input/output paths and output dimensions
- Automatic runtime shim for known `basicsr` / `torchvision` compatibility issue

## Requirements

- Python 3.10+ recommended
- Windows, Linux, or macOS (Windows is primary-tested in this workspace)
- Optional NVIDIA GPU for faster Real-ESRGAN processing

### Windows Prerequisite (for `basicsr`)

Install **Microsoft Visual C++ Build Tools**:

- https://visualstudio.microsoft.com/visual-cpp-build-tools/

## Installation

From the project root:

```powershell
# Option 1: uv
uv pip install -r requirements.txt

# Option 2: pip
pip install -r requirements.txt
```

The Real-ESRGAN model weights are downloaded automatically on first use and cached by the library.

## Quick Start

```powershell
python upscale.py
```

By default, this reads values from `config_upscale.json`.

## Running Tests

Run the local smoke test suite used by CI:

```powershell
# Install test-only dependencies
uv pip install -r requirements_test.txt

# Run unittest smoke checks
python -m unittest discover -s tests -v
```

Run the generation smoke command directly (same inputs as pipeline):

```powershell
python upscale.py --input input_tests --output ci_output --width 512 --height 512 --overwrite --lanczos
```

## Usage

### Common Commands

```powershell
# Use defaults from config_upscale.json
python upscale.py

# Use a different config file
python upscale.py --config path/to/config_upscale.json

# Override input/output directories
python upscale.py --input ./input --output ./output_upscaled

# Override target dimensions
python upscale.py --width 2480 --height 3508

# Re-process files already present in output directory
python upscale.py --overwrite

# Skip Real-ESRGAN and use PIL Lanczos only
python upscale.py --lanczos
```

### CLI Arguments

| Argument | Type | Description |
|---|---|---|
| `--config` | `str` | Config path (default: `config_upscale.json`) |
| `--input` | `str` | Input directory (overrides config) |
| `--output` | `str` | Output directory (overrides config) |
| `--width` | `int` | Output width in pixels (overrides config) |
| `--height` | `int` | Output height in pixels (overrides config) |
| `--overwrite` | flag | Process files even when output already exists |
| `--lanczos` | flag | Use PIL Lanczos only (disable Real-ESRGAN) |

## Configuration

Main config file: `config_upscale.json`

Example:

```json
{
  "input_directory": "./input",
  "output_directory": "./output_upscaled",
  "output_width": 6400,
  "output_height": 4800,
  "output_format": "PNG",
  "skip_existing": true,
  "supported_formats": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"],
  "upscaler": {
    "model_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    "scale": 4,
    "tile": 512,
    "tile_pad": 32
  }
}
```

### Config Notes

- `skip_existing: true` skips files where output filename already exists.
- `output_format` supports `PNG` and `JPEG`.
- `tile` and `tile_pad` help control VRAM use for large images.
- CLI flags always take priority over config values.

## Supported Input Formats

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`
- `.bmp`
- `.tiff`

## Resolution Guide

| Use Case | Width | Height |
|---|---:|---:|
| A4 @ 72 DPI (screen) | 595 | 842 |
| A4 @ 150 DPI | 1240 | 1754 |
| A4 @ 300 DPI (print) | 2480 | 3508 |
| A4 @ 600 DPI | 4960 | 7016 |
| A3 @ 300 DPI | 3508 | 4961 |

## Folder Structure

```text
.
├─ upscale.py
├─ config_upscale.json
├─ requirements.txt
├─ input/
├─ input2/
├─ output_upscaled/
└─ output_upscaled2/
```

## Performance Notes

- Real-ESRGAN path uses GPU fp16 (`half=True`) when available.
- Tiled inference keeps memory usage more stable on large inputs.
- `--lanczos` mode works without GPU but gives lower quality than Real-ESRGAN.

## Troubleshooting

- **`functional_tensor` import error**: handled automatically at runtime by a shim in `upscale.py`.
- **No files processed**: verify input directory path and supported extensions.
- **Need fresh outputs**: use `--overwrite` if `skip_existing` is true.
- **JPEG artifacts**: prefer PNG for print workflows.

## Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make focused changes with clear commit messages.
4. Open a pull request with a short summary and test notes.

If you add new CLI options or config keys, update this README in the same PR.
