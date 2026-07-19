#!/usr/bin/env python3
"""Dependency-light repository and skill package validation."""

from __future__ import annotations

import compileall
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "requirements.txt",
    "scripts/biofigure.py",
    "references/affinity-contract.md",
    "references/generation-workflows.md",
    "references/manifest-schema.md",
    "references/qa.md",
)
REQUIRED_COMMANDS = (
    "doctor", "init", "suggest", "split", "merge", "rename", "approve",
    "extract", "generate", "replace", "compile", "render", "qa", "inspect",
)


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\n"):
        errors.append("SKILL.md must start with YAML front matter")
    front_matter = skill.split("---", 2)[1] if skill.count("---") >= 2 else ""
    if not re.search(r"(?m)^name:\s*biofigure-affinity-svg\s*$", front_matter):
        errors.append("SKILL.md name does not match repository skill name")
    if not re.search(r"(?m)^description:\s*\S", front_matter):
        errors.append("SKILL.md description is missing")

    cli = (ROOT / "scripts/biofigure.py").read_text(encoding="utf-8")
    for command in REQUIRED_COMMANDS:
        if f'"{command}"' not in cli:
            errors.append(f"CLI command not declared: {command}")
    if "shell=True" in cli or any(
        "shell=True" in path.read_text(encoding="utf-8")
        for path in (ROOT / "scripts/biofigure_lib").glob("*.py")
    ):
        errors.append("portable runtime must not use shell=True")

    if not compileall.compile_dir(ROOT / "scripts", quiet=1):
        errors.append("Python source compilation failed")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("Repository and skill package validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

