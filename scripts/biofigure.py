#!/usr/bin/env python3
"""Portable CLI for manifest-driven dual-state biomedical SVG projects."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from biofigure_lib.errors import BiofigureError, DependencyError, ManifestError, QAError


JsonObject = dict[str, Any]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biofigure",
        description="Build and edit Affinity-compatible, dual-state biomedical SVG figures.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _command(subparsers, "doctor", "check portable runtime dependencies")

    init = _command(subparsers, "init", "initialize a project")
    init.add_argument("project", type=Path)
    init.add_argument("--name", required=True)
    init.add_argument("--source", type=Path)
    init.add_argument("--width", type=int)
    init.add_argument("--height", type=int)
    init.add_argument("--background", default="#ffffff")

    suggest = _command(subparsers, "suggest", "apply candidate semantic groups")
    suggest.add_argument("project", type=Path)
    suggest.add_argument("--candidates", type=Path, required=True)

    split = _command(subparsers, "split", "split one group into two or more groups")
    split.add_argument("project", type=Path)
    split.add_argument("source_id")
    split.add_argument("--replacements", type=Path, required=True)

    merge = _command(subparsers, "merge", "merge two or more groups")
    merge.add_argument("project", type=Path)
    merge.add_argument("source_ids", nargs="+")
    merge.add_argument("--replacement", type=Path, required=True)

    rename = _command(subparsers, "rename", "rename a stable semantic group")
    rename.add_argument("project", type=Path)
    rename.add_argument("old_id")
    rename.add_argument("new_id")

    approve = _command(subparsers, "approve", "approve the current manifest revision")
    approve.add_argument("project", type=Path)

    extract = _command(subparsers, "extract", "extract exact and transparent group assets")
    extract.add_argument("project", type=Path)
    extract.add_argument("--draft", action="store_true")

    for name, help_text in (
        ("generate", "register a generated replacement for one group"),
        ("replace", "replace one group with a prepared PNG asset"),
    ):
        replacement = _command(subparsers, name, help_text)
        replacement.add_argument("project", type=Path)
        replacement.add_argument("group_id")
        replacement.add_argument("asset", type=Path)
        replacement.add_argument("--prompt")

    compile_parser = _command(subparsers, "compile", "compile the nine-layer Affinity SVG")
    compile_parser.add_argument("project", type=Path)
    compile_parser.add_argument("--draft", action="store_true")

    render = _command(subparsers, "render", "render the compiled SVG in Chrome, Chromium, or Edge")
    render.add_argument("project", type=Path)
    render.add_argument("--browser", type=Path)

    qa = _command(subparsers, "qa", "run structure, fidelity, and Affinity release gates")
    qa.add_argument("project", type=Path)
    qa.add_argument("--require-affinity", action="store_true")

    inspect = _command(subparsers, "inspect", "inspect project or group metadata")
    inspect.add_argument("project", type=Path)
    inspect.add_argument("--group")
    return parser


def _command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    help_text: str,
) -> argparse.ArgumentParser:
    return subparsers.add_parser(name, help=help_text, description=help_text)


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers: dict[str, Callable[[argparse.Namespace], JsonObject]] = {
        "doctor": _doctor,
        "init": _init,
        "suggest": _suggest,
        "split": _split,
        "merge": _merge,
        "rename": _rename,
        "approve": _approve,
        "extract": _extract,
        "generate": _replace,
        "replace": _replace,
        "compile": _compile,
        "render": _render,
        "qa": _qa,
        "inspect": _inspect,
    }
    try:
        result = handlers[args.command](args)
    except ModuleNotFoundError as exc:
        _emit_error(DependencyError(f"missing Python package: {exc.name}; install requirements.txt"), args.json)
        return 3
    except DependencyError as exc:
        _emit_error(exc, args.json)
        return 3
    except QAError as exc:
        _emit_error(exc, args.json)
        return 4
    except (ManifestError, BiofigureError, OSError, ValueError, json.JSONDecodeError) as exc:
        _emit_error(exc, args.json)
        return 2
    _emit(result, args.json)
    return 0


def _doctor(_args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.render import detect_browser

    browser: Optional[str]
    try:
        browser = str(detect_browser())
    except DependencyError:
        browser = None
    packages: dict[str, Optional[str]] = {}
    for name in ("Pillow", "PyYAML"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "ok": all(packages.values()),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": packages,
        "browser": browser,
        "render_ready": browser is not None,
        "notes": "Chrome, Chromium, or Edge is required only for render and fidelity QA.",
    }


def _init(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.project import init_project

    manifest = init_project(
        args.project,
        args.name,
        args.source,
        args.width,
        args.height,
        args.background,
    )
    return {"status": "initialized", "manifest": str(manifest.resolve())}


def _suggest(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.review import apply_suggestions

    candidates = _read_json(args.candidates)
    if isinstance(candidates, dict):
        candidates = candidates.get("groups") or candidates.get("candidates")
    if not isinstance(candidates, list):
        raise ManifestError("candidate JSON must be a list or contain groups/candidates")
    added = apply_suggestions(args.project, candidates)
    return {
        "status": "draft",
        "added": added,
        "review": str((args.project / "review/numbered.png").resolve()),
    }


def _split(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.review import split_group

    replacements = _read_json(args.replacements)
    if not isinstance(replacements, list):
        raise ManifestError("replacement JSON must be a list")
    split_group(args.project, args.source_id, replacements)
    return {"status": "draft", "removed": [args.source_id], "added": [item.get("id") for item in replacements]}


def _merge(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.review import merge_groups

    replacement = _read_json(args.replacement)
    if not isinstance(replacement, dict):
        raise ManifestError("replacement JSON must be an object")
    merge_groups(args.project, args.source_ids, replacement)
    return {"status": "draft", "removed": args.source_ids, "added": [replacement.get("id")]}


def _rename(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.review import rename_group

    rename_group(args.project, args.old_id, args.new_id)
    return {"status": "draft", "renamed": {"from": args.old_id, "to": args.new_id}}


def _approve(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.manifest import load_manifest
    from biofigure_lib.review import approve_review

    approve_review(args.project)
    data = load_manifest(args.project / "project.yaml")
    return {
        "status": "approved",
        "revision": data["review"]["revision"],
        "manifest_sha256": data["review"]["approved_manifest_sha256"],
    }


def _extract(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.assets import extract_project

    rebuilt = extract_project(args.project, draft=args.draft)
    return {"status": "extracted", "rebuilt": rebuilt}


def _replace(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.assets import replace_group_asset

    rebuilt = replace_group_asset(args.project, args.group_id, args.asset, args.prompt)
    return {"status": "draft", "group": args.group_id, "rebuilt": rebuilt}


def _compile(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.svg import compile_affinity_svg

    output = compile_affinity_svg(args.project, draft=args.draft)
    return {"status": "compiled", "svg": str(output.resolve())}


def _render(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.render import render_svg

    output = render_svg(args.project, args.browser)
    return {"status": "rendered", "preview": str(output.resolve())}


def _qa(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.qa import run_qa

    report = run_qa(args.project, require_affinity=args.require_affinity)
    return {"status": "passed", **report}


def _inspect(args: argparse.Namespace) -> JsonObject:
    from biofigure_lib.manifest import load_manifest

    data = load_manifest(args.project / "project.yaml")
    if args.group:
        group = next((item for item in data["groups"] if item["id"] == args.group), None)
        if group is None:
            raise ManifestError(f"group not found: {args.group}")
        return {"project": data["project"]["name"], "group": group}
    return {
        "project": data["project"]["name"],
        "canvas": data["canvas"],
        "review": data["review"],
        "group_count": len(data["groups"]),
        "groups": [group["id"] for group in data["groups"]],
        "text_count": len(data["texts"]),
        "connector_count": len(data["connectors"]),
    }


def _read_json(path: Path) -> Any:
    path = Path(path)
    if not path.is_file():
        raise ManifestError(f"JSON file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _emit(payload: JsonObject, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    status = payload.get("status", "ok")
    details = ", ".join(f"{key}={value}" for key, value in payload.items() if key != "status")
    print(f"{status}: {details}" if details else str(status))


def _emit_error(exc: BaseException, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
    else:
        print(f"error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
