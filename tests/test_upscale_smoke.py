import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


class UpscaleSmokeTest(unittest.TestCase):
    def test_upscale_pipeline_with_input_tests_images(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        input_dir = repo_root / "input_tests"

        self.assertTrue(input_dir.exists(), "input_tests directory missing")

        source_images = sorted(
            p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        self.assertGreater(len(source_images), 0, "No supported test images in input_tests")

        tmp_dir = Path(tempfile.mkdtemp(prefix="upscale-smoke-"))
        try:
            output_dir = tmp_dir / "output"
            test_config = {
                "input_directory": str(input_dir),
                "output_directory": str(output_dir),
                "output_width": 256,
                "output_height": 256,
                "output_format": "PNG",
                "skip_existing": True,
                "supported_formats": sorted(SUPPORTED_EXTENSIONS),
                "upscaler": {
                    "model_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
                    "scale": 4,
                    "tile": 512,
                    "tile_pad": 32,
                },
            }
            config_path = tmp_dir / "config_upscale_test.json"
            config_path.write_text(json.dumps(test_config), encoding="utf-8")

            cmd = [
                sys.executable,
                str(repo_root / "upscale.py"),
                "--config",
                str(config_path),
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--width",
                "256",
                "--height",
                "256",
                "--overwrite",
                "--lanczos",
            ]

            result = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=(
                    "upscale.py failed\n"
                    f"stdout:\n{result.stdout}\n"
                    f"stderr:\n{result.stderr}"
                ),
            )

            generated = sorted(output_dir.glob("*_upscaled.png"))
            self.assertEqual(
                len(generated),
                len(source_images),
                (
                    "Generated output count does not match input_tests image count\n"
                    f"stdout:\n{result.stdout}\n"
                    f"stderr:\n{result.stderr}"
                ),
            )

            for out_path in generated:
                with Image.open(out_path) as img:
                    self.assertEqual(
                        img.size,
                        (256, 256),
                        f"Unexpected output size for {out_path.name}: {img.size}",
                    )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
