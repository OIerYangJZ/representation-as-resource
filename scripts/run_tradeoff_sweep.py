#!/usr/bin/env python3
"""Expand and execute the frozen W3 reference-compiler sweep.

The default manifest fails closed on unapproved hostnames.  ``--plan-only``
never runs a compiler and is safe for local inspection.  Existing complete
runs are verified and reused with ``--resume``; incomplete directories are
reported as failures and never deleted automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.reference_streaming.model import RunConfig
from compiler.reference_streaming.runner import run_reference_compiler
from instrumentation.event_trace import verify_trace_run


SOURCE_FILES = (
    "encoding/codec.py",
    "instrumentation/resource_accounting.py",
    "instrumentation/event_trace.py",
    "instrumentation/event_schema.json",
    "compiler/reference_streaming/model.py",
    "compiler/reference_streaming/compilers.py",
    "compiler/reference_streaming/runner.py",
    "scripts/run_tradeoff_sweep.py",
    "scripts/analyze_tradeoff.py",
    "data/frozen/tradeoff_manifest.yaml",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_plan(path: Path | str) -> dict[str, Any]:
    # JSON is a strict subset of YAML 1.2; using it keeps the remote runner
    # stdlib-only while satisfying the requested .yaml artifact contract.
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    if plan.get("schema") != "ucc.tradeoff-sweep-plan.v1":
        raise ValueError("unsupported tradeoff sweep plan")
    return plan


def expand_plan(plan: Mapping[str, Any]) -> list[RunConfig]:
    compiler_fractions = {item["name"]: float(item["memory_fraction"]) for item in plan["compilers"]}
    defaults = plan["defaults"]
    unique: dict[str, RunConfig] = {}
    dimensions = ("m", "r", "K", "epsilon_factor", "passes", "schedule", "seed")
    for segment in plan["segments"]:
        matrix = segment["matrix"]
        values = [matrix.get(name, defaults.get(name if name != "seed" else "seeds")) for name in dimensions]
        if any(value is None for value in values):
            raise ValueError(f"segment {segment['name']} lacks a dimension")
        for compiler, combination in itertools.product(segment["compiler_names"], itertools.product(*values)):
            row = dict(zip(dimensions, combination))
            config = RunConfig(
                compiler=compiler,
                memory_fraction=compiler_fractions[compiler],
                delta=float(defaults.get("delta", 0.0)),
                campaign=str(plan["campaign"]),
                **row,
            )
            unique.setdefault(config.run_id(), config)
    return sorted(unique.values(), key=lambda item: item.run_id())


def _git_revision() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _append_status(path: Path, row: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n")


def run_sweep(
    plan_path: Path,
    output_root: Path,
    *,
    resume: bool,
    max_runs: int | None,
    allow_local_smoke: bool,
) -> Path:
    plan = load_plan(plan_path)
    configs = expand_plan(plan)
    hostname = socket.gethostname()
    allowed = set(plan["execution_policy"]["allowed_remote_hostnames"])
    if plan["execution_policy"]["formal_runs_must_be_remote"] and hostname not in allowed and not allow_local_smoke:
        raise RuntimeError(
            f"formal sweep refused on hostname {hostname!r}; approved hostnames are {sorted(allowed)}"
        )
    if allow_local_smoke and (max_runs is None or max_runs > 3):
        raise ValueError("local smoke override requires --max-runs <= 3")
    selected = configs if max_runs is None else configs[:max_runs]
    campaign_root = output_root.resolve() / str(plan["campaign"])
    campaign_root.mkdir(parents=True, exist_ok=True)
    status_path = campaign_root / "sweep_status.jsonl"
    campaign_manifest_path = campaign_root / "campaign_manifest.json"
    if campaign_manifest_path.exists() and not resume:
        raise FileExistsError("campaign manifest already exists; use --resume after inspection")
    source_hashes = {
        relative: _sha256(ROOT / relative) for relative in SOURCE_FILES if (ROOT / relative).is_file()
    }
    campaign_manifest = {
        "schema": "ucc.tradeoff-campaign.v1",
        "plan_path": str(plan_path.resolve()),
        "plan_sha256": _sha256(plan_path),
        "campaign": plan["campaign"],
        "planned_unique_runs": len(configs),
        "selected_runs": len(selected),
        "hostname": hostname,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "git_revision": _git_revision(),
        "source_sha256": source_hashes,
        "started_unix": time.time(),
        "configs": [config.to_dict() for config in selected],
    }
    campaign_manifest_path.write_text(
        json.dumps(campaign_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for index, config in enumerate(selected):
        row: dict[str, Any] = {
            "run_index": index,
            "run_id": config.run_id(),
            "compiler": config.compiler,
            "started_unix": time.time(),
        }
        run_dir = campaign_root / config.run_id()
        try:
            manifest_path = run_dir / "run_manifest.json"
            if run_dir.exists():
                if not resume or not manifest_path.is_file():
                    raise FileExistsError("existing run directory is incomplete or resume was not requested")
                verify_trace_run(manifest_path, verify_slices=True)
                row.update(status="reused_verified", manifest_path=str(manifest_path))
            else:
                result = run_reference_compiler(config, campaign_root)
                row.update(status="completed", manifest_path=str(result))
        except Exception as exc:  # campaign policy requires failed cells to survive.
            row.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        row["finished_unix"] = time.time()
        _append_status(status_path, row)
        print(json.dumps(row, sort_keys=True), flush=True)
    campaign_manifest["finished_unix"] = time.time()
    campaign_manifest["status_file"] = str(status_path)
    campaign_manifest_path.write_text(
        json.dumps(campaign_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return campaign_manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data/frozen/tradeoff_manifest.yaml"))
    parser.add_argument("--output-root", default=str(ROOT / "data/runs"))
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-runs", type=int)
    parser.add_argument("--allow-local-smoke", action="store_true", help="bounded implementation smoke only; never frozen")
    args = parser.parse_args()
    plan = load_plan(Path(args.manifest))
    configs = expand_plan(plan)
    if args.plan_only:
        print(json.dumps({"campaign": plan["campaign"], "unique_runs": len(configs)}, sort_keys=True))
        return
    result = run_sweep(
        Path(args.manifest),
        Path(args.output_root),
        resume=args.resume,
        max_runs=args.max_runs,
        allow_local_smoke=args.allow_local_smoke,
    )
    print(result)


if __name__ == "__main__":
    main()
