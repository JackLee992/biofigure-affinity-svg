from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_build_state(project_dir: Path) -> dict[str, Any]:
    path = Path(project_dir) / "build/state.json"
    if not path.is_file():
        return {"manifest_sha256": None, "source_sha256": None, "groups": {}, "last_command": None}
    return json.loads(path.read_text(encoding="utf-8"))


def save_build_state(project_dir: Path, data: dict[str, Any]) -> None:
    path = Path(project_dir) / "build/state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
