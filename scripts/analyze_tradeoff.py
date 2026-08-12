#!/usr/bin/env python3
"""Verify W3 traces, aggregate measured budgets, and plot the real frontier."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import statistics
import sys
import tarfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from instrumentation.event_trace import verify_trace_run
from instrumentation.resource_accounting import sha256_file


COMPILER_ORDER = (
    "echo",
    "full_aggregation",
    "hybrid_25",
    "hybrid_50",
    "hybrid_75",
    "ir_materializing",
)
COLORS = {
    "echo": "#4477AA",
    "full_aggregation": "#CC6677",
    "hybrid_25": "#228833",
    "hybrid_50": "#AA3377",
    "hybrid_75": "#EE7733",
    "ir_materializing": "#66CCEE",
}
MARKERS = {
    "echo": "o",
    "full_aggregation": "s",
    "hybrid_25": "^",
    "hybrid_50": "D",
    "hybrid_75": "v",
    "ir_materializing": "P",
}


def _read_events(run_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()]


def _validate_auxiliary_artifacts(manifest: Mapping[str, Any], run_dir: Path) -> None:
    extra = manifest["extra"]
    log = extra["run_log"]
    log_path = run_dir / log["path"]
    if log_path.stat().st_size != log["bytes"] or sha256_file(log_path) != log["sha256"]:
        raise ValueError("run.log differs from its manifest record")
    for record in extra["input_artifacts"].values():
        artifact = run_dir / record["artifact_path"]
        if artifact.stat().st_size != record["artifact_bytes"] or sha256_file(artifact) != record["artifact_sha256"]:
            raise ValueError("input artifact differs from its manifest record")
        sidecar = run_dir / record["artifact_manifest_path"]
        if (
            not sidecar.is_file()
            or sidecar.stat().st_size != record["artifact_manifest_bytes"]
            or sha256_file(sidecar) != record["artifact_manifest_sha256"]
        ):
            raise ValueError("input artifact sidecar differs from its manifest record")


def summarize_run(manifest_path: Path, *, verify_slices: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = verify_trace_run(manifest_path, verify_slices=verify_slices)
    run_dir = manifest_path.parent
    _validate_auxiliary_artifacts(manifest, run_dir)
    events = _read_events(run_dir)
    config = manifest["config"]
    crossings = [row for row in events if row["crossing"] is not None]
    expected_crossings = 2 * int(config["passes"]) - 1
    a_p = sum(int(row["committed_delta_bits"]) for row in events if row["side"] == "A")
    sigma = sum(int(row["B_cross_bits"]) for row in crossings)
    s_named = max((int(row["B_cross_bits"]) for row in crossings), default=0)
    s_global = max(int(row["B_cross_bits"]) for row in events)
    peak_crossing = max(crossings, key=lambda row: row["B_cross_bits"]) if crossings else None
    L = float(config["L_delta_bits"])
    exact_residual = a_p + sigma - L
    cap_residual = a_p + expected_crossings * s_named - L
    final_output = int(events[-1]["B_com_bits"])
    output_residual = final_output - L
    epsilon_valid = float(config["epsilon"]) < math.sin(math.pi / (2.0 * int(config["Q"])))
    certificate = manifest["extra"]["output_certificate"]
    anomalies: list[str] = []
    if len(crossings) != expected_crossings:
        anomalies.append("crossing_count_mismatch")
    if exact_residual < -1e-9:
        anomalies.append("negative_exact_transcript_residual")
    if cap_residual < -1e-9:
        anomalies.append("negative_cap_envelope_residual")
    if output_residual < -1e-9:
        anomalies.append("negative_output_residual")
    if not epsilon_valid:
        anomalies.append("epsilon_outside_theorem_regime")
    if certificate.get("status") != "pass" or certificate.get("projective_error") != 0.0:
        anomalies.append("semantic_certificate_failure")
    row: dict[str, Any] = {
        "run_id": manifest["extra"]["run_id"],
        "compiler": config["compiler"],
        "m": int(config["m"]),
        "r": int(config["r"]),
        "K": int(config["K"]),
        "Q": int(config["Q"]),
        "epsilon": float(config["epsilon"]),
        "epsilon_factor": float(config["epsilon_factor"]),
        "delta": float(config["delta"]),
        "passes": int(config["passes"]),
        "memory_fraction": float(config["effective_memory_fraction"]),
        "cap_coordinates": int(manifest["extra"]["execution"]["cap_coordinates_per_pass"]),
        "requested_payload_cap_bits": int(config["requested_payload_cap_bits"]),
        "schedule": config["schedule"],
        "seed": int(config["seed"]),
        "event_count": len(events),
        "crossing_count": len(crossings),
        "L_delta_bits": L,
        "A_p_bits": a_p,
        "Sigma_p_bits": sigma,
        "S_cross_bits": s_named,
        "S_global_bits": s_global,
        "B_output_bits": final_output,
        "max_control_bits": max(row["B_control_bits"] for row in events),
        "max_store_bits": max(row["B_store_bits"] for row in events),
        "max_window_bits": max(row["B_window_bits"] for row in events),
        "max_parameter_bits": max(row["B_parameter_bits"] for row in events),
        "max_IR_bits": max(row["B_IR_bits"] for row in events),
        "cross_control_bits": 0 if peak_crossing is None else peak_crossing["B_control_bits"],
        "cross_store_bits": 0 if peak_crossing is None else peak_crossing["B_store_bits"],
        "cross_window_bits": 0 if peak_crossing is None else peak_crossing["B_window_bits"],
        "cross_parameter_bits": 0 if peak_crossing is None else peak_crossing["B_parameter_bits"],
        "cross_IR_bits": 0 if peak_crossing is None else peak_crossing["B_IR_bits"],
        "rss_peak_bytes": max(row["rss_bytes"] for row in events),
        "wall_time_ns": max(row["wall_time_ns"] for row in events),
        "exact_transcript_residual_bits": exact_residual,
        "cap_envelope_residual_bits": cap_residual,
        "output_residual_bits": output_residual,
        "normalized_x": (expected_crossings * s_named / L) if L > 0 else math.nan,
        "normalized_y": (a_p / L) if L > 0 else math.nan,
        "normalized_exact_residual": (exact_residual / L) if L > 0 else math.nan,
        "normalized_cap_residual": (cap_residual / L) if L > 0 else math.nan,
        "semantic_status": certificate.get("status"),
        "projective_error": certificate.get("projective_error"),
        "epsilon_valid": epsilon_valid,
        "theorem_diagnostic_status": "pass" if not anomalies else "theorem_model_mismatch",
        "anomalies": ";".join(anomalies),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }
    augmented = []
    for event in events:
        event_row = dict(event)
        event_row.update(
            run_id=row["run_id"], compiler=row["compiler"], m=row["m"], r=row["r"], K=row["K"],
            epsilon=row["epsilon"], passes=row["passes"], memory_fraction=row["memory_fraction"],
            schedule=row["schedule"], seed=row["seed"],
        )
        augmented.append(event_row)
    return row, augmented


def _pareto_flags(rows: list[dict[str, Any]]) -> None:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    keys = ("m", "r", "K", "epsilon_factor", "passes", "schedule", "seed")
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    for group in groups.values():
        for row in group:
            objectives = (row["A_p_bits"], row["S_cross_bits"], row["cross_IR_bits"])
            row["pareto"] = not any(
                other is not row
                and all(a <= b for a, b in zip((other["A_p_bits"], other["S_cross_bits"], other["cross_IR_bits"]), objectives))
                and any(a < b for a, b in zip((other["A_p_bits"], other["S_cross_bits"], other["cross_IR_bits"]), objectives))
                for other in group
            )


def _write_csv(path: Path, rows: list[Mapping[str, Any]], fields: Iterable[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(fields) if fields is not None else sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _create_trace_archive(campaign_root: Path, output: Path) -> None:
    """Create a deterministic archive containing every file-backed event slice."""

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="tradeoff_trace_artifacts.tar", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in sorted(campaign_root.rglob("*")):
                    if not path.is_file():
                        continue
                    arcname = Path("tradeoff_runs") / path.relative_to(campaign_root)
                    info = archive.gettarinfo(str(path), arcname=str(arcname))
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    with path.open("rb") as stream:
                        archive.addfile(info, stream)


def _linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    if len(xs) < 2 or len(set(xs)) < 2:
        return math.nan, math.nan, math.nan
    xbar, ybar = statistics.mean(xs), statistics.mean(ys)
    denom = sum((x - xbar) ** 2 for x in xs)
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / denom
    intercept = ybar - slope * xbar
    fitted = [intercept + slope * x for x in xs]
    total = sum((y - ybar) ** 2 for y in ys)
    residual = sum((y - fit) ** 2 for y, fit in zip(ys, fitted))
    r2 = 1.0 - residual / total if total else 1.0
    return slope, intercept, r2


def scaling_fits(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    canonical = [
        row for row in rows
        if row["r"] == 2 and row["K"] == 8 and row["epsilon_factor"] == 0.5
        and row["passes"] == 1 and row["schedule"] == "round_major" and row["seed"] == 20260801
    ]
    result: list[dict[str, Any]] = []
    for compiler in COMPILER_ORDER:
        subset = sorted((row for row in canonical if row["compiler"] == compiler), key=lambda row: row["m"])
        for metric in ("A_p_bits", "S_cross_bits", "B_output_bits", "max_IR_bits", "wall_time_ns"):
            points = [(row["m"], row[metric]) for row in subset if row[metric] > 0]
            slope, intercept, r2 = _linear_fit(
                [math.log2(x) for x, _ in points], [math.log2(y) for _, y in points]
            )
            result.append(
                {
                    "compiler": compiler,
                    "metric": metric,
                    "slice": "r=2,K=8,epsilon_factor=0.5,p=1,round_major,seed=20260801",
                    "points": len(points),
                    "log2_slope": slope,
                    "log2_intercept": intercept,
                    "r_squared": r2,
                }
            )
    return result


def _plot_pdf(rows: list[dict[str, Any]], fits: list[dict[str, Any]], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output, metadata={"Title": "Measured commitment-memory-IR frontier", "Author": "W3 trace analysis"}) as pdf:
        fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6), constrained_layout=True)
        ax = axes[0]
        xs = [10 ** (-2 + 5 * index / 199) for index in range(200)]
        ax.plot(xs, [max(0.0, 1.0 - x) for x in xs], color="black", lw=1.8, label="theory lower envelope")
        for compiler in COMPILER_ORDER:
            subset = [row for row in rows if row["compiler"] == compiler]
            if not subset:
                continue
            ax.scatter(
                [row["normalized_x"] for row in subset],
                [max(row["normalized_y"], 1e-3) for row in subset],
                s=[34 if row["pareto"] else 15 for row in subset],
                alpha=0.72 if compiler != "ir_materializing" else 0.9,
                marker=MARKERS[compiler], color=COLORS[compiler], label=compiler.replace("_", " "),
                edgecolors=["black" if row["pareto"] else "none" for row in subset], linewidths=0.5,
            )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"normalized crossing term $(2p-1)S/L_\delta$")
        ax.set_ylabel(r"normalized Alice-side commitment $A_p/L_\delta$")
        ax.set_title("(a) Trace-derived frontier (black edge = Pareto)")
        ax.grid(True, which="both", alpha=0.22)
        ax.legend(fontsize=7, ncol=2)

        ax = axes[1]
        canonical = [
            row for row in rows if row["m"] == 64 and row["r"] == 2 and row["K"] == 8
            and row["epsilon_factor"] == 0.5 and row["passes"] == 4
            and row["schedule"] == "round_major" and row["seed"] == 20260801
        ]
        annotation_specs = {
            "echo": ("echo", (5, 4)),
            "full_aggregation": ("full", (9, 25)),
            "hybrid_25": ("h25", (-21, -21)),
            "hybrid_50": ("h50", (9, -12)),
            "hybrid_75": ("h75", (9, 8)),
        }
        for row in canonical:
            ir_fraction = row["cross_IR_bits"] / row["S_cross_bits"] if row["S_cross_bits"] else 0.0
            ax.scatter(
                row["S_cross_bits"], max(row["A_p_bits"], 1), s=55 + 160 * ir_fraction,
                color=COLORS[row["compiler"]], marker=MARKERS[row["compiler"]],
                edgecolor="black" if row["pareto"] else "none", linewidth=0.7,
            )
            label, offset = annotation_specs[row["compiler"]]
            ax.annotate(
                label,
                (row["S_cross_bits"], max(row["A_p_bits"], 1)),
                xytext=offset,
                textcoords="offset points",
                fontsize=7,
                annotation_clip=False,
                arrowprops={"arrowstyle": "-", "color": "#666666", "linewidth": 0.45},
            )
        if canonical:
            L = canonical[0]["L_delta_bits"]
            p = canonical[0]["passes"]
            envelope_x = [0, L / (2 * p - 1)]
            ax.plot(envelope_x, [L, 0], color="black", lw=1.4, label="raw lower envelope")
        ax.set_xscale("symlog", linthresh=1)
        ax.set_yscale("symlog", linthresh=1)
        ax.set_xlabel("measured named-crossing cap S (bits)")
        ax.set_ylabel("measured Alice-side committed output A_p (bits)")
        ax.set_title("(b) Raw canonical slice; marker area reflects IR share")
        if canonical:
            ax.set_xlim(right=max(row["S_cross_bits"] for row in canonical) * 1.70)
            ax.set_ylim(top=max(row["A_p_bits"] for row in canonical) * 1.90)
        ax.grid(True, which="both", alpha=0.22)
        pdf.savefig(fig)
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6), constrained_layout=True)
        canonical_components = [
            row for row in rows if row["m"] == 64 and row["r"] == 2 and row["K"] == 8
            and row["epsilon_factor"] == 0.5 and row["passes"] == 1
            and row["schedule"] == "round_major" and row["seed"] == 20260801
        ]
        labels = [row["compiler"].replace("_", "\n") for row in canonical_components]
        bottom = [0.0] * len(canonical_components)
        components = (
            ("cross_control_bits", "control", "#999999"),
            ("cross_store_bits", "store", "#BBBB55"),
            ("cross_window_bits", "window", "#77AADD"),
            ("cross_parameter_bits", "parameter", "#EE8866"),
            ("cross_IR_bits", "IR", "#AA4499"),
        )
        for key, label, color in components:
            values = [row[key] for row in canonical_components]
            axes[0].bar(range(len(values)), values, bottom=bottom, label=label, color=color)
            bottom = [a + b for a, b in zip(bottom, values)]
        axes[0].set_xticks(range(len(labels)), labels, fontsize=7)
        axes[0].set_ylabel("bits at largest named crossing")
        axes[0].set_title("(c) Measured five-field restart-state decomposition")
        axes[0].legend(fontsize=7, ncol=3)
        axes[0].grid(True, axis="y", alpha=0.22)

        for compiler in COMPILER_ORDER:
            subset = sorted(
                (row for row in rows if row["compiler"] == compiler and row["r"] == 2 and row["K"] == 8
                 and row["epsilon_factor"] == 0.5 and row["passes"] == 1
                 and row["schedule"] == "round_major" and row["seed"] == 20260801),
                key=lambda row: row["m"],
            )
            if subset:
                axes[1].plot(
                    [row["m"] for row in subset], [row["normalized_cap_residual"] for row in subset],
                    color=COLORS[compiler], marker=MARKERS[compiler], label=compiler.replace("_", " "),
                )
        axes[1].axhline(0.0, color="black", lw=1, ls="--")
        axes[1].set_xscale("log", base=2)
        axes[1].set_yscale("symlog", linthresh=0.1)
        axes[1].set_xlabel("m")
        axes[1].set_ylabel(r"normalized cap residual $[A_p+(2p-1)S-L_\delta]/L_\delta$")
        axes[1].set_title("(d) Lower-envelope residual (negative points retained)", fontsize=10.5)
        axes[1].grid(True, which="both", alpha=0.22)
        axes[1].legend(fontsize=7, ncol=2)
        pdf.savefig(fig)
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6), constrained_layout=True)
        for compiler in COMPILER_ORDER:
            subset = sorted(
                (row for row in rows if row["compiler"] == compiler and row["r"] == 2 and row["K"] == 8
                 and row["epsilon_factor"] == 0.5 and row["passes"] == 1
                 and row["schedule"] == "round_major" and row["seed"] == 20260801),
                key=lambda row: row["m"],
            )
            if subset:
                axes[0].plot([row["m"] for row in subset], [row["S_cross_bits"] for row in subset],
                             color=COLORS[compiler], marker=MARKERS[compiler], label=compiler.replace("_", " "))
                axes[1].plot([row["m"] for row in subset], [row["B_output_bits"] for row in subset],
                             color=COLORS[compiler], marker=MARKERS[compiler], label=compiler.replace("_", " "))
        for ax, ylabel, title in (
            (axes[0], "named-crossing cap S (bits)", "(e) State scaling from serialized trace frames"),
            (axes[1], "final committed output (bits)", "(f) Output scaling from append-only streams"),
        ):
            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            ax.set_xlabel("m")
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.grid(True, which="both", alpha=0.22)
        axes[0].legend(fontsize=7, ncol=2)
        pdf.savefig(fig)
        plt.close(fig)


def analyze(campaign_root: Path, frozen_dir: Path, figure_path: Path, *, verify_slices: bool) -> dict[str, Any]:
    manifest_paths = sorted(campaign_root.glob("*/run_manifest.json"))
    if not manifest_paths:
        raise FileNotFoundError(f"no run manifests below {campaign_root}")
    frozen_dir.mkdir(parents=True, exist_ok=True)
    events_path = frozen_dir / "tradeoff_events.jsonl.gz"
    summaries: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    with events_path.open("wb") as raw:
        with gzip.GzipFile(filename="tradeoff_events.jsonl", mode="wb", fileobj=raw, mtime=0) as compressed:
            for manifest_path in manifest_paths:
                try:
                    summary, events = summarize_run(manifest_path, verify_slices=verify_slices)
                    summaries.append(summary)
                    for event in events:
                        compressed.write(
                            (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                        )
                    if summary["anomalies"]:
                        anomalies.append({"run_id": summary["run_id"], "status": summary["theorem_diagnostic_status"], "details": summary["anomalies"]})
                except Exception as exc:
                    anomalies.append(
                        {"run_id": manifest_path.parent.name, "status": "verification_failure", "details": f"{type(exc).__name__}: {exc}"}
                    )
    if not summaries:
        raise RuntimeError("all run manifests failed verification")
    status_file = campaign_root / "sweep_status.jsonl"
    last_status: dict[str, dict[str, Any]] = {}
    if status_file.is_file():
        for line in status_file.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            last_status[row["run_id"]] = row
        for row in last_status.values():
            if row.get("status") == "failed":
                anomalies.append({"run_id": row["run_id"], "status": "run_failure", "details": row.get("error", "")})
    _pareto_flags(summaries)
    summary_path = frozen_dir / "tradeoff_summary.csv"
    anomaly_path = frozen_dir / "tradeoff_anomalies.csv"
    fits_path = frozen_dir / "tradeoff_scaling_fits.csv"
    trace_archive_path = frozen_dir / "tradeoff_trace_artifacts.tar.gz"
    _write_csv(summary_path, summaries)
    _write_csv(anomaly_path, anomalies, ("run_id", "status", "details"))
    fits = scaling_fits(summaries)
    _write_csv(fits_path, fits)
    _create_trace_archive(campaign_root, trace_archive_path)
    _plot_pdf(summaries, fits, figure_path)
    output_paths = (summary_path, anomaly_path, fits_path, events_path, trace_archive_path, figure_path)
    campaign_manifest_path = campaign_root / "campaign_manifest.json"
    campaign_manifest = (
        json.loads(campaign_manifest_path.read_text(encoding="utf-8")) if campaign_manifest_path.is_file() else {}
    )
    selected_runs = int(campaign_manifest.get("selected_runs", len(last_status) or len(summaries)))
    freeze_manifest = {
        "schema": "ucc.tradeoff-freeze.v1",
        "analysis_source": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "campaign_root": str(campaign_root.resolve()),
        "verified_runs": len(summaries),
        "verification_failures": sum(item["status"] == "verification_failure" for item in anomalies),
        "run_failures": sum(item["status"] == "run_failure" for item in anomalies),
        "theorem_model_mismatches": sum(item["status"] == "theorem_model_mismatch" for item in anomalies),
        "campaign_complete": len(summaries) == selected_runs and not any(
            item["status"] in {"verification_failure", "run_failure"} for item in anomalies
        ),
        "all_verified_points_in_allowed_region": all(
            row["theorem_diagnostic_status"] == "pass" for row in summaries
        ),
        "run_manifests": [
            {"run_id": row["run_id"], "sha256": row["manifest_sha256"]} for row in summaries
        ],
        "outputs": {
            path.name: {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in output_paths
        },
        "notes": [
            "The theorem is a worst-input expected statement; per-seed residuals are retained as diagnostics, not substituted for a proof.",
            "A_p sums actual append-only output deltas on Alice-side events; Sigma_p sums all named crossings.",
            "S_cross_bits is the largest of the 2p-1 named restart-state serializations, not RSS.",
        ],
    }
    freeze_path = frozen_dir / "tradeoff_freeze_manifest.json"
    freeze_path.write_text(json.dumps(freeze_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return freeze_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", required=True)
    parser.add_argument("--frozen-dir", default=str(ROOT / "data/frozen"))
    parser.add_argument("--figure", default=str(ROOT / "figures/measured_tradeoff_frontier.pdf"))
    parser.add_argument("--skip-slice-verification", action="store_true")
    args = parser.parse_args()
    result = analyze(
        Path(args.campaign_root),
        Path(args.frozen_dir),
        Path(args.figure),
        verify_slices=not args.skip_slice_verification,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
