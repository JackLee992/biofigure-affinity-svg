from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping, Optional

from .errors import DependencyError, QAError
from .manifest import load_manifest


def browser_candidates(
    platform_name: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> list[str]:
    platform_name = platform_name or sys.platform
    env = dict(os.environ if env is None else env)
    candidates: list[str] = []
    for executable in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge"):
        resolved = shutil.which(executable)
        if resolved:
            candidates.append(resolved)
    if platform_name == "darwin":
        candidates.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ])
    elif platform_name.startswith("win"):
        program_files = env.get("PROGRAMFILES", r"C:\Program Files")
        program_files_x86 = env.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        local = env.get("LOCALAPPDATA", "")
        candidates.extend([
            f"{program_files}\\Google\\Chrome\\Application\\chrome.exe",
            f"{program_files_x86}\\Google\\Chrome\\Application\\chrome.exe",
            f"{local}\\Google\\Chrome\\Application\\chrome.exe",
            f"{program_files}\\Microsoft\\Edge\\Application\\msedge.exe",
            f"{program_files_x86}\\Microsoft\\Edge\\Application\\msedge.exe",
        ])
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def detect_browser(explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            raise DependencyError(f"browser executable not found: {path}")
        return path
    for candidate in browser_candidates():
        path = Path(candidate)
        if path.is_file():
            return path
    raise DependencyError("Chrome, Chromium, or Edge is required for SVG rendering")


def render_svg(project_dir: Path, browser: Optional[Path] = None, timeout_seconds: int = 20) -> Path:
    project_dir = Path(project_dir)
    data = load_manifest(project_dir / "project.yaml")
    svg = project_dir / "exports/affinity.svg"
    if not svg.is_file():
        raise QAError("compiled SVG is missing")
    executable = detect_browser(browser)
    output = project_dir / "exports/preview.png"
    temporary = project_dir / "build/render-preview.png"
    profile = project_dir / "build/browser-profile"
    profile.mkdir(parents=True, exist_ok=True)
    temporary.parent.mkdir(parents=True, exist_ok=True)
    if temporary.exists():
        temporary.unlink()
    log_path = project_dir / "build/browser-render.log"
    command = [
        str(executable),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--user-data-dir={profile}",
        f"--window-size={data['canvas']['width']},{data['canvas']['height']}",
        f"--screenshot={temporary}",
        svg.resolve().as_uri(),
    ]
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, shell=False)
        deadline = time.monotonic() + timeout_seconds
        try:
            while time.monotonic() < deadline:
                if temporary.is_file() and temporary.stat().st_size > 0:
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.1)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
    if not temporary.is_file() or temporary.stat().st_size == 0:
        raise QAError(f"browser failed to render SVG; see {log_path}")
    temporary.replace(output)
    return output
