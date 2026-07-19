from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from PIL import Image

from .errors import ManifestError
from .manifest import save_manifest


PROJECT_DIRS = (
    "source/references",
    "groups/clean",
    "groups/generated",
    "review",
    "build/exact",
    "build/masks",
    "build/failed",
    "exports",
)


def init_project(
    project_dir: Path,
    name: str,
    source: Optional[Path],
    width: Optional[int],
    height: Optional[int],
    background: str,
) -> Path:
    project_dir = Path(project_dir)
    if project_dir.exists() and any(project_dir.iterdir()):
        raise ManifestError(f"project directory is not empty: {project_dir}")
    for relative in PROJECT_DIRS:
        (project_dir / relative).mkdir(parents=True, exist_ok=True)

    destination = project_dir / "source/original.png"
    if source is not None:
        source = Path(source)
        if not source.is_file():
            raise ManifestError(f"source image not found: {source}")
        with Image.open(source) as image:
            canvas_width, canvas_height = image.size
            image.convert("RGBA").save(destination)
    else:
        if width is None or height is None:
            raise ManifestError("width and height are required for an empty canvas")
        if width <= 0 or height <= 0:
            raise ManifestError("width and height must be positive")
        canvas_width, canvas_height = width, height
        Image.new("RGBA", (width, height), background).save(destination)

    manifest = {
        "schema_version": 1,
        "project": {"name": name},
        "canvas": {"width": canvas_width, "height": canvas_height, "background": background},
        "source": {"image": "source/original.png", "references": []},
        "style": {"prompt": None, "references": []},
        "review": {"status": "draft", "revision": 0, "approved_manifest_sha256": None},
        "groups": [],
        "texts": [],
        "connectors": [],
        "qa": {"require_pixel_match": source is not None, "rmse_threshold": 0.0},
    }
    manifest_path = project_dir / "project.yaml"
    save_manifest(manifest_path, manifest)
    return manifest_path
