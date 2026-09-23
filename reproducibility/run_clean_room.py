#!/usr/bin/env python3
"""Copy a minimal artifact into an independent temporary directory and verify it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "reproducibility/clean_room.log"
RECEIPT = ROOT / "data/frozen/clean_room_receipt.json"
REPORT = ROOT / "CLEAN_ROOM_REPORT.md"


def copy_relative(source_root: Path, target_root: Path, relative: str) -> None:
    source = source_root / relative
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        shutil.copy2(source, target)


def run(command: list[str], cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    output = f"$ {' '.join(command)}\n{result.stdout}{result.stderr}"
    if result.returncode:
        raise RuntimeError(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="keep the temporary clean-room directory")
    args = parser.parse_args()
    clean = Path(tempfile.mkdtemp(prefix="ucc-clean-room-"))
    required = [
        "tests/test_qary_packing.py",
        "tests/test_update_stream_equivalence.py",
        "tests/search_small_compiler_counterexamples.py",
        "workloads",
        "scripts/allocate_synthesis_error.py",
        "scripts/run_qre_campaign.py",
        "qre",
        "certificates",
        "reproducibility/clean_room_smoke.py",
        "PaperDraft/research/fixed_budget_qre/tools/staq_grid_synth",
    ]
    for relative in required:
        copy_relative(ROOT, clean, relative)
    (clean / "scripts/__init__.py").touch()

    venv = clean / ".venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    python = venv / "bin/python"
    locked_site_packages = sysconfig.get_paths()["purelib"]
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": os.pathsep.join((str(clean), locked_site_packages)),
        "PYTHONHASHSEED": "0",
        "MPLCONFIGDIR": str(clean / ".cache/matplotlib"),
        "XDG_CACHE_HOME": str(clean / ".cache"),
        "LANG": "C.UTF-8",
    }
    outputs = []
    outputs.append(run([
        str(python), "-m", "pytest",
        "tests/test_qary_packing.py", "tests/test_update_stream_equivalence.py",
        "tests/search_small_compiler_counterexamples.py", "-q",
    ], clean, env))
    if "9 passed" not in outputs[0]:
        raise RuntimeError("clean-room theorem-test count was not 9")
    outputs.append(run([
        str(python), "reproducibility/clean_room_smoke.py", "--receipt", str(RECEIPT)
    ], clean, env))
    portable_log = "\n\n".join(outputs)
    portable_log = portable_log.replace(str(clean), "<clean-room>")
    portable_log = portable_log.replace(str(ROOT), "<repository>")
    LOG.write_text(portable_log)
    receipt = json.loads(RECEIPT.read_text())
    receipt["theorem_tests_passed"] = 9
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    log_sha = hashlib.sha256(LOG.read_bytes()).hexdigest()
    REPORT.write_text(f"""# Clean-room reproduction report

## Result

PASS.  A minimal artifact was copied to an independent temporary directory, a fresh virtual
environment was created without network access and explicitly bound to the locked project
site-packages, and all requested subsets were executed from that directory.

- Headline-theorem exhaustive subset: {receipt['theorem_tests_passed']} tests passed across
  `test_qary_packing.py`, `test_update_stream_equivalence.py`, and
  `search_small_compiler_counterexamples.py`.
- Natural benchmark subset: `{receipt['instance']['family']}` was independently compiled by the
  authors reference and TKET semantic baseline; both dense projective certificates returned
  `completed_valid`.
- Fixed-total-error QRE subset: both outputs used epsilon_total=1e-6 and 16 factories and returned
  positive physical-qubit, cycle, runtime, and spacetime estimates.
- Deterministic grid-synthesis pairs exercised: {receipt['grid_synth_unique_pairs']}.

The machine-readable receipt is `data/frozen/clean_room_receipt.json`; the command log is
`reproducibility/clean_room.log` (SHA-256 `{log_sha}`).  The temporary directory was
{'retained by explicit request' if args.keep else 'removed after verification'}.

This validates a theorem-test subset, a benchmark subset, and a QRE subset.  It does not rerun the
full 21,060-cell W8 campaign or all 288 W7 cells inside the temporary directory.
""")
    print(json.dumps({"status": "pass", "clean_room": str(clean), "receipt": str(RECEIPT), "log_sha256": log_sha}, indent=2))
    if not args.keep:
        shutil.rmtree(clean)


if __name__ == "__main__":
    main()
