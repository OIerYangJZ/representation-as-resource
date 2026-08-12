#!/usr/bin/env python3
"""Actual W8/W7 clean-room subset: compile, certify, and estimate resources."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

from workloads.natural import (
    FACTORS,
    QREContext,
    circuit_metrics,
    compile_authors,
    compile_external_tket,
    dense_certificate,
    generate_instance,
    qasm_bytes,
    raw_reference,
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    instance = generate_instance("qaoa_ising", 1, 20260821, 1.0, "all_to_all")
    reference = raw_reference(instance)
    factors = {name: 1 for name in FACTORS}
    authors, authors_record = compile_authors(instance, factors)
    external, external_record = compile_external_tket(instance)
    authors_certificate = dense_certificate(reference, authors)
    external_certificate = dense_certificate(reference, external)
    if authors_certificate["status"] != "completed_valid":
        raise RuntimeError(f"authors certificate failed: {authors_certificate}")
    if external_certificate["status"] != "completed_valid":
        raise RuntimeError(f"external certificate failed: {external_certificate}")

    qre = QREContext(epsilon_total=1e-6, factories=16)
    authors_qre = qre.measure(authors)
    external_qre = qre.measure(external)
    for item in (authors_qre, external_qre):
        if item["qre_status"] != "completed_valid" or item["qre_physical_qubits"] <= 0:
            raise RuntimeError(f"QRE failed: {item}")

    receipt = {
        "schema": "ucc.clean-room-smoke.v1",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            package: importlib.metadata.version(package)
            for package in ("qiskit", "pytket", "numpy", "pandas", "pyarrow")
        },
        "instance": {
            "instance_id": instance.instance_id,
            "representation_id": instance.representation_id,
            "family": instance.family,
            "scale": instance.scale,
            "seed": instance.seed,
            "density": instance.density,
            "topology": instance.topology,
        },
        "authors": {
            "status": authors_certificate["status"],
            "certificate_sha256": authors_certificate["certificate_sha256"],
            "qasm_sha256": sha256(qasm_bytes(authors)),
            "metrics": circuit_metrics(authors),
            "selected_candidate": authors_record["selected_candidate"],
            "qre": authors_qre,
        },
        "external": {
            "status": external_certificate["status"],
            "certificate_sha256": external_certificate["certificate_sha256"],
            "qasm_sha256": sha256(qasm_bytes(external)),
            "metrics": circuit_metrics(external),
            "selected_candidate": external_record["selected_candidate"],
            "qre": external_qre,
        },
        "grid_synth_unique_pairs": len(qre.grid.records),
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
