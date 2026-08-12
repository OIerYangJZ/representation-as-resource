from __future__ import annotations

import json
import math
from pathlib import Path

from reportlab.lib.colors import HexColor, black, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path(__file__).resolve().parent / "ssh_full_run_20260706_165733"

TARGETS = {
    "fourier_separation": [
        ROOT / "PaperDraft" / "figures" / "fourier_separation.pdf",
        ROOT / "Graph Materials" / "01_fourier_separation.pdf",
    ],
    "fourier_ablation": [
        ROOT / "PaperDraft" / "figures" / "fourier_ablation.pdf",
        ROOT / "Graph Materials" / "03_fourier_ablation.pdf",
    ],
    "resource_consequence": [
        ROOT / "PaperDraft" / "figures" / "resource_consequence.pdf",
        ROOT / "Graph Materials" / "02_resource_consequence.pdf",
    ],
}

SIZES = [4000, 10000, 20000, 50000, 100000]
SIZE_LABELS = ["4k", "10k", "20k", "50k", "100k"]

COLORS = {
    "semantic_ucc": "#0072B2",
    "phase_poly_reference": "#009E73",
    "qiskit_opt3": "#D55E00",
    "pyzx_full_reduce": "#7A4EA3",
    "tket_fullpeephole": "#CC79A7",
    "tket_paulisimp": "#8B0000",
    "tket_guided_paulisimp": "#E69F00",
    "no_fourier_ucc": "#666666",
}


def _read_json(name: str) -> list[dict[str, object]]:
    return json.loads((SOURCE_DIR / name).read_text(encoding="utf-8"))


def _index(rows: list[dict[str, object]]) -> dict[tuple[int, str], dict[str, object]]:
    return {(int(row["size"]), str(row["method_key"])): row for row in rows}


def _fmt_int(value: int | float) -> str:
    return f"{int(value):,}"


def _nice_log_ticks(y_min: float, y_max: float) -> list[int]:
    candidates = [10, 20, 50, 100, 200, 500]
    ticks: list[int] = []
    start = int(math.floor(math.log10(y_min))) - 1
    end = int(math.ceil(math.log10(y_max))) + 1
    for exp in range(start, end + 1):
        for mantissa in candidates:
            value = mantissa * (10**exp)
            if y_min <= value <= y_max:
                ticks.append(value)
    return ticks


class PdfPlot:
    def __init__(self, path: Path, width: float = 720, height: float = 420) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.width = width
        self.height = height
        self.c = canvas.Canvas(str(path), pagesize=(width, height))
        self.left = 70
        self.right = width - 26
        self.bottom = 84
        self.top = height - 54
        self.y_min = 1.0
        self.y_max = 10.0

    def set_ranges(self, y_min: float, y_max: float) -> None:
        self.y_min = y_min
        self.y_max = y_max

    def x(self, size: int) -> float:
        lo = math.log10(SIZES[0])
        hi = math.log10(SIZES[-1])
        return self.left + (math.log10(size) - lo) / (hi - lo) * (self.right - self.left)

    def y(self, value: float) -> float:
        lo = math.log10(self.y_min)
        hi = math.log10(self.y_max)
        return self.bottom + (math.log10(value) - lo) / (hi - lo) * (self.top - self.bottom)

    def title(self, title: str) -> None:
        self.c.setFont("Helvetica-Bold", 13)
        self.c.setFillColor(black)
        self.c.drawCentredString(self.width / 2, self.height - 28, title)

    def axes(self, y_label: str, x_label: str = "Requested input gates") -> None:
        c = self.c
        c.setStrokeColor(Color(0.82, 0.82, 0.82))
        c.setLineWidth(0.45)
        c.setFont("Helvetica", 8)
        c.setFillColor(black)
        for size, label in zip(SIZES, SIZE_LABELS):
            x = self.x(size)
            c.line(x, self.bottom, x, self.top)
            c.drawCentredString(x, self.bottom - 16, label)
        for tick in _nice_log_ticks(self.y_min, self.y_max):
            y = self.y(tick)
            c.setStrokeColor(Color(0.86, 0.86, 0.86))
            c.line(self.left, y, self.right, y)
            c.setFillColor(black)
            c.drawRightString(self.left - 8, y - 3, _fmt_int(tick))
        c.setStrokeColor(black)
        c.setLineWidth(0.9)
        c.line(self.left, self.bottom, self.left, self.top)
        c.line(self.left, self.bottom, self.right, self.bottom)
        c.setFont("Helvetica", 10)
        c.drawCentredString((self.left + self.right) / 2, 32, x_label)
        c.saveState()
        c.translate(self.left - 50, (self.bottom + self.top) / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, y_label)
        c.restoreState()

    def status_band(self, y_value: float, label: str, color: str) -> None:
        y = self.y(y_value)
        self.c.setStrokeColor(HexColor(color))
        self.c.setLineWidth(0.7)
        self.c.setDash(2, 2)
        self.c.line(self.left, y, self.right, y)
        self.c.setDash()
        self.c.setFont("Helvetica", 8)
        self.c.setFillColor(HexColor(color))
        self.c.drawString(self.left + 4, y + 4, label)

    def line_series(
        self,
        points: list[tuple[int, float]],
        color: str,
        marker: str,
        dashed: bool = False,
    ) -> None:
        if not points:
            return
        c = self.c
        c.setStrokeColor(HexColor(color))
        c.setFillColor(HexColor(color))
        c.setLineWidth(1.7)
        if dashed:
            c.setDash(4, 3)
        if len(points) > 1:
            path = c.beginPath()
            path.moveTo(self.x(points[0][0]), self.y(points[0][1]))
            for size, value in points[1:]:
                path.lineTo(self.x(size), self.y(value))
            c.drawPath(path)
        c.setDash()
        for size, value in points:
            self.marker(self.x(size), self.y(value), marker, color)

    def marker(self, x: float, y: float, marker: str, color: str, size: float = 4.5) -> None:
        c = self.c
        c.setStrokeColor(HexColor(color))
        c.setFillColor(HexColor(color))
        c.setLineWidth(1.2)
        if marker == "circle":
            c.circle(x, y, size, stroke=1, fill=1)
        elif marker == "open_square":
            outline_size = size + 1.2
            c.rect(
                x - outline_size,
                y - outline_size,
                2 * outline_size,
                2 * outline_size,
                stroke=1,
                fill=0,
            )
        elif marker == "square":
            c.rect(x - size, y - size, 2 * size, 2 * size, stroke=1, fill=1)
        elif marker == "triangle":
            p = c.beginPath()
            p.moveTo(x, y + size)
            p.lineTo(x - size, y - size)
            p.lineTo(x + size, y - size)
            p.close()
            c.drawPath(p, stroke=1, fill=1)
        elif marker == "diamond":
            p = c.beginPath()
            p.moveTo(x, y + size)
            p.lineTo(x - size, y)
            p.lineTo(x, y - size)
            p.lineTo(x + size, y)
            p.close()
            c.drawPath(p, stroke=1, fill=1)
        elif marker == "x":
            c.line(x - size, y - size, x + size, y + size)
            c.line(x - size, y + size, x + size, y - size)
        elif marker == "plus":
            c.line(x - size, y, x + size, y)
            c.line(x, y - size, x, y + size)
        else:
            c.circle(x, y, size, stroke=1, fill=1)

    def legend(self, entries: list[tuple[str, str, str]], y: float = 54) -> None:
        c = self.c
        c.setFont("Helvetica", 8)
        x = self.left
        row_height = 13
        max_width = self.right - self.left
        for label, color, marker in entries:
            entry_width = pdfmetrics.stringWidth(label, "Helvetica", 8) + 24
            if x + entry_width > self.left + max_width:
                x = self.left
                y -= row_height
            self.marker(x + 5, y + 3, marker, color, size=3.6)
            c.setFillColor(black)
            c.drawString(x + 13, y, label)
            x += entry_width + 12

    def finish(self) -> None:
        self.c.save()
        print(f"wrote {self.path}")


def _series(
    rows: dict[tuple[int, str], dict[str, object]],
    method: str,
    value_key: str,
) -> tuple[list[tuple[int, float]], list[int], list[int]]:
    completed: list[tuple[int, float]] = []
    timeouts: list[int] = []
    errors: list[int] = []
    for size in SIZES:
        row = rows.get((size, method), {})
        status = row.get("status")
        value = row.get(value_key)
        if status == "completed" and value is not None:
            completed.append((size, float(value)))
        elif status == "error":
            errors.append(size)
        else:
            timeouts.append(size)
    return completed, timeouts, errors


def _draw_status_series(
    plot: PdfPlot,
    rows: dict[tuple[int, str], dict[str, object]],
    method: str,
    value_key: str,
    marker: str,
    timeout_y: float,
    error_y: float | None = None,
    dashed: bool = False,
) -> None:
    completed, timeouts, errors = _series(rows, method, value_key)
    color = COLORS[method]
    plot.line_series(completed, color, marker, dashed=dashed)
    for size in timeouts:
        plot.marker(plot.x(size), plot.y(timeout_y), "x", color, size=5)
    if error_y is not None:
        for size in errors:
            plot.marker(plot.x(size), plot.y(error_y), "plus", color, size=5)


def _write_plot_to_targets(name: str, draw) -> None:
    for target in TARGETS[name]:
        plot = PdfPlot(target)
        draw(plot)
        plot.finish()


def generate_fourier_separation() -> None:
    rows = _index(_read_json("round3_main_external_baselines_results.json"))
    methods = [
        ("semantic_ucc", "semantic UCC (Fourier-layer IR enabled)", "circle", False),
        ("qiskit_opt3", "qiskit opt3", "triangle", False),
        ("pyzx_full_reduce", "PyZX full_reduce", "square", False),
        ("tket_fullpeephole", "TKET FullPeephole", "diamond", True),
        ("tket_paulisimp", "TKET PauliSimp", "plus", False),
        ("tket_guided_paulisimp", "TKET GuidedPauliSimp", "diamond", False),
    ]

    def draw(plot: PdfPlot) -> None:
        timeout_y = 520_000
        error_y = 700_000
        plot.set_ranges(25, 900_000)
        plot.title("Fourier-layer external baselines")
        plot.axes("Compiled output gates")
        plot.status_band(timeout_y, "timeout", "#555555")
        plot.status_band(error_y, "error", "#8B0000")
        for method, _label, marker, dashed in methods:
            _draw_status_series(plot, rows, method, "gate_count", marker, timeout_y, error_y, dashed=dashed)
        legend_entries = [(label, COLORS[method], marker) for method, label, marker, _ in methods]
        legend_entries.extend([("timeout marker", "#555555", "x"), ("error marker", "#8B0000", "plus")])
        plot.legend(legend_entries)

    _write_plot_to_targets("fourier_separation", draw)


def generate_fourier_ablation() -> None:
    rows = _index(_read_json("round3_fourier_ablation_completion_results.json"))
    methods = [
        ("semantic_ucc", "semantic UCC (Fourier-layer IR enabled)", "circle"),
        ("phase_poly_reference", "phase-polynomial reference", "square"),
        ("qiskit_opt3", "qiskit opt3", "triangle"),
        ("no_fourier_ucc", "artifact UCC (Fourier-layer IR disabled)", "diamond"),
    ]

    def draw(plot: PdfPlot) -> None:
        timeout_y = 520_000
        plot.set_ranges(25, 760_000)
        plot.title("Fourier-layer IR ablation")
        plot.axes("Compiled output gates")
        plot.status_band(timeout_y, "timeout", "#555555")
        for method, _label, marker in methods:
            _draw_status_series(plot, rows, method, "gate_count", marker, timeout_y)
        legend_entries = [(label, COLORS[method], marker) for method, label, marker in methods]
        legend_entries.append(("timeout marker", "#555555", "x"))
        plot.legend(legend_entries)

    _write_plot_to_targets("fourier_ablation", draw)


def generate_resource_consequence() -> None:
    rows = _index(_read_json("round3_resource_consequence_check_results.json"))
    methods = [
        ("semantic_ucc", "semantic UCC (Fourier-layer IR enabled)", "circle"),
        ("phase_poly_reference", "phase-polynomial reference", "open_square"),
        ("qiskit_opt3", "qiskit opt3", "triangle"),
        ("no_fourier_ucc", "artifact UCC (Fourier-layer IR disabled)", "diamond"),
    ]

    def draw(plot: PdfPlot) -> None:
        plot.set_ranges(10, 18_000_000)
        plot.title("Rotation multiplicity and Clifford+T exposure")
        # Draw two panels on one canvas by temporarily overriding coordinates.
        old = (plot.left, plot.right, plot.bottom, plot.top, plot.y_min, plot.y_max)
        panels = [
            (70, 345, "rz_rotation_count", "Exposed rotation count", 180_000, 10, 180_000),
            (415, 690, "t_proxy_1e_10", "Clifford+T proxy (1e-10)", 18_000_000, 1000, 18_000_000),
        ]
        for left, right, value_key, y_label, timeout_y, y_min, y_max in panels:
            plot.left = left
            plot.right = right
            plot.bottom = 92
            plot.top = 332
            plot.set_ranges(y_min, y_max)
            plot.axes(y_label)
            plot.status_band(timeout_y, "timeout", "#555555")
            # Draw the open phase-polynomial markers first, then place the
            # coincident filled semantic-UCC markers above them. This exposes
            # both series without changing any data coordinate.
            draw_order = [methods[1], methods[0], methods[2], methods[3]]
            for method, _label, marker in draw_order:
                _draw_status_series(plot, rows, method, value_key, marker, timeout_y)
        plot.left, plot.right, plot.bottom, plot.top, plot.y_min, plot.y_max = old
        legend_entries = [(label, COLORS[method], marker) for method, label, marker in methods]
        legend_entries.append(("timeout marker", "#555555", "x"))
        plot.legend(legend_entries, y=58)

    _write_plot_to_targets("resource_consequence", draw)


def main() -> None:
    generate_fourier_separation()
    generate_fourier_ablation()
    generate_resource_consequence()


if __name__ == "__main__":
    main()
