#!/usr/bin/env python3
"""Freeze campaign provenance and the claim--evidence matrix for revision 17--25."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable


THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parents[1]
WORKSPACE = ROOT.parents[1]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_head() -> str:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True, capture_output=True, check=False
    )
    return process.stdout.strip() if process.returncode == 0 else "unavailable"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def freeze_source(source: Path, destination: Path) -> dict[str, Any]:
    payload = json.loads(source.read_text(encoding="utf-8"))
    write_json(destination, payload)
    return {
        "path": str(destination.relative_to(ROOT)),
        "sha256": sha256_file(destination),
        "source_snapshot": str(source.relative_to(WORKSPACE)),
        "source_sha256": sha256_file(source),
    }


def manifest(
    campaign: str,
    label_prefix: str,
    profile: str,
    config: dict[str, Any],
    dataset: dict[str, Any],
    freeze_commit: str,
) -> dict[str, Any]:
    digest = sha256_bytes(canonical_bytes(config))
    return {
        "schema": "ucc.campaign-manifest.v1",
        "campaign": campaign,
        "reader_label_prefix": label_prefix,
        "inherits": profile,
        "immutable_config_sha256": digest,
        "freeze_commit": freeze_commit,
        "dataset": dataset,
        "config": config,
    }


def campaign_outputs(output_dir: Path) -> list[Path]:
    freeze_commit = git_head()
    output_dir.mkdir(parents=True, exist_ok=True)
    real_data = freeze_source(
        WORKSPACE / "research" / "real_instance_results.json",
        output_dir / "frozen_real_panel_rows.json",
    )
    hardware_data = freeze_source(
        WORKSPACE / "research" / "hardware_aware_results.json",
        output_dir / "frozen_hardware_aware_rows.json",
    )
    registry_path = ROOT / "research" / "experiment_registry" / "frozen_hardware_rows.json"
    registry_data = {
        "path": str(registry_path.relative_to(ROOT)),
        "sha256": sha256_file(registry_path),
    }
    matched_path = ROOT / "research" / "matched_representation" / "campaign_manifest.json"
    natural_path = ROOT / "research" / "natural_factorial" / "campaign_manifest.json"
    profiles = {
        "logical_all_to_all_v1": {
            "backend_topology": "all-to-all logical, routing disabled",
            "native_gate_set": ["cx", "rx", "ry", "rz", "h"],
            "bridge_sequence": "Qiskit circuit -> declared compiler -> target-basis Qiskit circuit",
        },
        "line20_v1": {
            "backend_topology": "20-qubit bidirectional nearest-neighbor line",
            "native_gate_set": ["u", "sx", "p", "cx", "measure", "id"],
            "backend_source": "research/hardware_aware_backend.py",
            "backend_source_sha256": sha256_file(WORKSPACE / "research" / "hardware_aware_backend.py"),
        },
    }
    campaigns = {
        "RP23": manifest(
            "RP23-reorder-probe-202607",
            "RP23",
            "line20_v1",
            {
                "seed": 12345,
                "timeout_s": 600,
                "memory_cap_bytes": "not_enforced_historical",
                "tool_versions": {"qiskit": "2.3.1", "ucc": "0.4.12"},
                "artifact_commit": "legacy snapshot; generation commit unavailable",
                "bridge_sequence": "UCCDefaults variants -> line20 target basis",
                "certificate": "no independent equivalence certificate in historical rows; diagnostic only",
                "purpose": "pass-order probe; never merged with HW24",
            },
            registry_data,
            freeze_commit,
        ),
        "HW24": manifest(
            "HW24-canonical-hardware-aware-202607",
            "HW24",
            "line20_v1",
            {
                "seed": 12345,
                "timeout_policy_s": {"qpeexact": 120, "qaoa": 120, "grover": 240},
                "memory_cap_bytes": "not_enforced_historical",
                "tool_versions": {"qiskit": "2.3.1", "ucc": "0.4.12"},
                "artifact_commit": "legacy snapshot; generation commit unavailable",
                "bridge_sequence": "MQT Bench -> Qiskit/UCC -> line20 target basis",
                "certificate": "no independent equivalence certificate in historical rows; diagnostic only",
                "runner": "research/compare_hardware_aware.py",
                "runner_sha256": sha256_file(WORKSPACE / "research" / "compare_hardware_aware.py"),
            },
            hardware_data,
            freeze_commit,
        ),
        "REAL24": manifest(
            "REAL24-official-real-panel-202607",
            "REAL24",
            "logical_all_to_all_v1",
            {
                "seed": "none_in_historical_runner",
                "timeout_policy_s": {
                    "qiskit_opt3_phase_estimation": 300,
                    "qiskit_opt3_other": 180,
                    "baseline_or_semantic_ucc": 240,
                    "other": 120,
                },
                "memory_cap_bytes": "not_enforced_historical",
                "tool_versions": {"qiskit": "2.3.1", "ucc": "0.4.12"},
                "artifact_commit": "legacy snapshot; generation commit unavailable",
                "bridge_sequence": "structured real instance -> configured method -> {cx,rx,ry,rz,h}",
                "certificate": "no independent equivalence certificate in historical rows; anti-regression diagnostic only",
                "runner": "research/compare_real_instances.py",
                "runner_sha256": sha256_file(WORKSPACE / "research" / "compare_real_instances.py"),
            },
            real_data,
            freeze_commit,
        ),
        "MR25": {
            "schema": "ucc.campaign-link.v1",
            "campaign": "MR25-matched-representation-20260801",
            "reader_label_prefix": "MR25",
            "inherits": "logical_all_to_all_v1",
            "manifest_path": str(matched_path.relative_to(ROOT)),
            "manifest_sha256": sha256_file(matched_path),
        },
        "NF25": {
            "schema": "ucc.campaign-link.v1",
            "campaign": "NF25-natural-factorial-20260801",
            "reader_label_prefix": "NF25",
            "inherits": "logical_all_to_all_v1",
            "manifest_path": str(natural_path.relative_to(ROOT)),
            "manifest_sha256": sha256_file(natural_path),
        },
    }
    written = []
    for key, value in campaigns.items():
        path = output_dir / f"{key}.json"
        write_json(path, value)
        written.append(path)
    index = {
        "schema": "ucc.campaign-index.v1",
        "freeze_commit": freeze_commit,
        "base_profiles": profiles,
        "campaigns": {
            key: {
                "manifest": f"{key}.json",
                "sha256": sha256_file(output_dir / f"{key}.json"),
                "reader_label_prefix": value["reader_label_prefix"],
            }
            for key, value in campaigns.items()
        },
        "invariants": [
            "reader_label_prefix is unique across campaigns",
            "a row may inherit only from its named base profile",
            "historical missing caps/certificates are explicit strings, never silently imputed",
            "identical source instance names in distinct campaigns retain distinct prefixes",
        ],
    }
    write_json(output_dir / "campaign_index.json", index)
    written.append(output_dir / "campaign_index.json")
    return written


def claim_rows() -> list[dict[str, str]]:
    return [
        {"id":"C01","location":"abstract/introduction","claim":"The charged compiler model has one executable five-field bit cut budget.","primary_evidence":r"\cref{def:compiler,eq:info-budget}","evidence_kind":"definition","scope":"formal model only"},
        {"id":"C02","location":"abstract/conclusion","claim":"Randomized approximate output descriptions require Omega(m log(1/epsilon)) bits.","primary_evidence":r"\cref{thm:output-counting}","evidence_kind":"theorem","scope":"declared family-relative and self-contained codes"},
        {"id":"C03","location":"abstract/conclusion","claim":"Masked-share flat recovery obeys a commitment plus cut-state lower bound.","primary_evidence":r"\cref{thm:main-tradeoff}","evidence_kind":"theorem","scope":"two-round masked-share stream"},
        {"id":"C04","location":"introduction/discussion","claim":"Memory-capped hybrids attain the deterministic family-relative envelope to leading order.","primary_evidence":r"\cref{prop:hybrid-upper}","evidence_kind":"proposition","scope":"ordered-share family-relative codec"},
        {"id":"C05","location":"validation","claim":"Nine matched representations are crossed with all five configured compilers.","primary_evidence":r"\cref{fig:matched-interaction}","evidence_kind":"figure","scope":"1,080 frozen cells; 24 cells per representation--compiler pair"},
        {"id":"C06","location":"validation","claim":"The traced reference compilers directly measure commitment, crossing-state, and IR coordinates.","primary_evidence":r"\cref{fig:measured-tradeoff}","evidence_kind":"trace-derived figure","scope":"592 formal-model reference-compiler runs"},
        {"id":"C07","location":"validation/workloads","claim":"The natural-workload campaign reports all structured, null-factor, and negative-control outcomes.","primary_evidence":r"\cref{tab:natural-factorial,fig:natural-factorial}","evidence_kind":"table and figure","scope":"9 families; $2^6$ factors; 3 scales and 3 seeds"},
        {"id":"C08","location":"resource consequences","claim":"Fixed-total-error synthesis changes logical and model-specific physical resources.","primary_evidence":r"\cref{tab:resource-consequence}","evidence_kind":"table","scope":"one disclosed surface-code model"},
        {"id":"C09","location":"compiler","claim":"The exact CNOT-RZ checker is sound up to global phase.","primary_evidence":r"\cref{prop:symbolic-soundness}","evidence_kind":"proposition","scope":"declared symbolic domain only"},
        {"id":"C10","location":"validation","claim":"TKET PauliSimp and PyZX full-reduce are semantic-capable configured baselines.","primary_evidence":r"\cref{fig:matched-interaction,sec:external-baselines}","evidence_kind":"figure and frozen external campaign","scope":"native and unified configurations; bridge loss reported separately"},
        {"id":"C11","location":"application workloads","claim":"The historical real panel demonstrates anti-regression rather than independent semantic advantage.","primary_evidence":r"\cref{tab:real-instances}","evidence_kind":"table","scope":"REAL24 campaign"},
        {"id":"C12","location":"conclusion","claim":"External growth curves are configured-pipeline behavior, not empirical proofs of the lower bound.","primary_evidence":r"\cref{tab:evidence-classes}","evidence_kind":"instrumentation table","scope":"evidence-class separation"},
        {"id":"C13","location":"abstract/conclusion","claim":"K-ary dispersed updates obey an explicit randomized p-pass state/output frontier.","primary_evidence":r"\cref{thm:w1-unified-frontier}","evidence_kind":"theorem","scope":"round-major forward scans; all 2p-1 crossings charged"},
        {"id":"C14","location":"abstract/discussion","claim":"The p-block compiler reaches the multipass state frontier within the stated constant factor.","primary_evidence":r"\cref{prop:w1-block-hybrid}","evidence_kind":"proposition","scope":"family-relative p-block codec; compact-output corner for every r; full curve for r=2"},
    ]


def claim_outputs(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = claim_rows()
    payload = {
        "schema": "ucc.claim-evidence-matrix.v1",
        "rule": "Every headline claim has one primary evidence pointer and an explicit scope; unsupported generality is prohibited.",
        "claims": rows,
    }
    json_path = output_dir / "claim_evidence.json"
    write_json(json_path, payload)
    lines = []
    for row in rows:
        escaped = {key: value.replace("_", r"\_").replace("%", r"\%") for key, value in row.items()}
        lines.append(
            f"{escaped['id']} & {escaped['location']} & {escaped['primary_evidence']} & {escaped['scope']} " + r"\\"
        )
    if lines and lines[-1].endswith(r" \\"):
        lines[-1] = lines[-1][:-3]
    tex_path = output_dir / "claim_evidence_rows.tex"
    tex_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [json_path, tex_path]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-dir", type=Path, default=ROOT / "research" / "campaign_manifests")
    parser.add_argument("--claim-dir", type=Path, default=ROOT / "research" / "claim_evidence")
    args = parser.parse_args(argv)
    outputs = campaign_outputs(args.campaign_dir) + claim_outputs(args.claim_dir)
    print(json.dumps({"outputs": [str(path.relative_to(ROOT)) for path in outputs]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
