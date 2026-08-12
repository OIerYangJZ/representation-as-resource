from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = ROOT / "PaperDraft" / "figures"


COLORS = {
    "translation": "#4E79A7",
    "qiskit": "#F28E2B",
    "legacy": "#B07AA1",
    "semantic": "#59A14F",
    "qft_inverse": "#4E79A7",
    "qpe_style": "#F28E2B",
    "qaoa_ring": "#59A14F",
    "grover_mirrored": "#B07AA1",
    "grid": "#D8DEE6",
    "axis": "#23272F",
    "text": "#20242A",
}


FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Helvetica.ttf",
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]
        if bold
        else FONT_CANDIDATES
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def comma(value: float | int) -> str:
    return f"{int(round(value)):,}"


def short_k(value: float | int) -> str:
    value = int(round(value))
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return str(value)


def draw_centered(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, fnt, fill: str) -> None:
    w, h = text_size(draw, text, fnt)
    draw.text((xy[0] - w / 2, xy[1] - h / 2), text, font=fnt, fill=fill)


def legend(draw: ImageDraw.ImageDraw, items: list[tuple[str, str, str]], x: int, y: int, width: int) -> None:
    fnt = font(24)
    cursor_x = x
    cursor_y = y
    for label, color, style in items:
        label_w, _ = text_size(draw, label, fnt)
        entry_w = label_w + 60
        if cursor_x + entry_w > x + width:
            cursor_x = x
            cursor_y += 36
        if style == "line":
            draw.line((cursor_x, cursor_y + 13, cursor_x + 34, cursor_y + 13), fill=color, width=5)
        elif style == "dash":
            for dx in range(0, 34, 12):
                draw.line((cursor_x + dx, cursor_y + 13, cursor_x + min(dx + 7, 34), cursor_y + 13), fill=color, width=5)
        else:
            draw.rectangle((cursor_x, cursor_y + 2, cursor_x + 28, cursor_y + 26), fill=color)
        draw.text((cursor_x + 42, cursor_y), label, font=fnt, fill=COLORS["text"])
        cursor_x += entry_w + 28


def generate_real_instance_bars() -> None:
    data = json.loads((ROOT / "research" / "real_instance_results.json").read_text())
    methods = [
        ("translation_only", "translation only", COLORS["translation"]),
        ("qiskit_opt3", "qiskit opt3", COLORS["qiskit"]),
        ("baseline_ucc", "UCC v0.4.12 default", COLORS["legacy"]),
        ("optimized_ucc", "semantic UCC", COLORS["semantic"]),
    ]
    instances = [
        ("phase_estimation_real", "phase estimation"),
        ("grover_real", "Grover"),
        ("qaoa_real", "QAOA"),
    ]

    img = Image.new("RGB", (1600, 953), "white")
    draw = ImageDraw.Draw(img)
    title_font = font(42, bold=True)
    label_font = font(26)
    small_font = font(22)

    draw_centered(draw, (800, 45), "Official real-instance output gates", title_font, COLORS["text"])

    left, right, top, bottom = 150, 1530, 110, 765
    max_y = 500_000
    for tick in [0, 100_000, 200_000, 300_000, 400_000, 500_000]:
        y = bottom - (tick / max_y) * (bottom - top)
        draw.line((left, y, right, y), fill=COLORS["grid"], width=2)
        draw.text((52, y - 14), short_k(tick), font=small_font, fill=COLORS["text"])
    draw.line((left, top, left, bottom), fill=COLORS["axis"], width=3)
    draw.line((left, bottom, right, bottom), fill=COLORS["axis"], width=3)
    draw.text((18, 382), "gates", font=label_font, fill=COLORS["text"])

    group_w = (right - left) / len(instances)
    bar_w = 58
    gap = 12
    for i, (inst_key, inst_label) in enumerate(instances):
        center = left + group_w * (i + 0.5)
        start = center - (len(methods) * bar_w + (len(methods) - 1) * gap) / 2
        for j, (method_key, _label, color) in enumerate(methods):
            value = data[inst_key][method_key]["output"]["total_gates"]
            x0 = start + j * (bar_w + gap)
            x1 = x0 + bar_w
            y0 = bottom - (value / max_y) * (bottom - top)
            draw.rectangle((x0, y0, x1, bottom), fill=color)
            draw.text((x0 - 2, y0 - 28), short_k(value), font=small_font, fill=COLORS["text"])
        draw_centered(draw, (center, bottom + 46), inst_label, label_font, COLORS["text"])

    legend(draw, [(label, color, "bar") for _key, label, color in methods], 210, 835, 1180)
    output = FIGURE_DIR / "real_instance_grouped_bar.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, optimize=True)
    print(f"wrote {output}")


def log_y(value: float, y_min: float, y_max: float, top: int, bottom: int) -> float:
    value = max(value, y_min)
    lo = math.log10(y_min)
    hi = math.log10(y_max)
    return bottom - (math.log10(value) - lo) / (hi - lo) * (bottom - top)


def x_pos(size: int, x_min: int, x_max: int, left: int, right: int) -> float:
    lo = math.log10(x_min)
    hi = math.log10(x_max)
    return left + (math.log10(size) - lo) / (hi - lo) * (right - left)


def dashed_line(draw: ImageDraw.ImageDraw, p0: tuple[float, float], p1: tuple[float, float], color: str) -> None:
    x0, y0 = p0
    x1, y1 = p1
    steps = 24
    for i in range(0, steps, 2):
        a = i / steps
        b = min(i + 1, steps) / steps
        draw.line(
            (
                x0 + (x1 - x0) * a,
                y0 + (y1 - y0) * a,
                x0 + (x1 - x0) * b,
                y0 + (y1 - y0) * b,
            ),
            fill=color,
            width=4,
        )


def draw_series(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, float]],
    color: str,
    panel: tuple[int, int, int, int],
    y_min: float,
    y_max: float,
    dashed: bool,
) -> None:
    left, top, right, bottom = panel
    coords = [
        (
            x_pos(size, 4000, 100000, left, right),
            log_y(value, y_min, y_max, top, bottom),
        )
        for size, value in points
    ]
    for p0, p1 in zip(coords, coords[1:]):
        if dashed:
            dashed_line(draw, p0, p1, color)
        else:
            draw.line((p0, p1), fill=color, width=4)
    for x, y in coords:
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color, outline="white", width=2)


def generate_scaling_plot() -> None:
    data = json.loads((ROOT / "research" / "scaling_results.json").read_text())
    families = [
        ("qft_inverse", "QFT inverse"),
        ("qpe_style", "QPE style"),
        ("qaoa_ring", "QAOA ring"),
        ("grover_mirrored", "Grover mirrored"),
    ]
    sizes = [4000, 10000, 20000, 50000, 100000]

    img = Image.new("RGB", (1600, 780), "white")
    draw = ImageDraw.Draw(img)
    title_font = font(34, bold=True)
    label_font = font(23)
    tick_font = font(19)

    draw_centered(draw, (800, 36), "Scaling on representative structured families", title_font, COLORS["text"])
    panels = {
        "gates": (130, 112, 745, 515),
        "runtime": (890, 112, 1505, 515),
    }

    def axes(panel: tuple[int, int, int, int], y_ticks: list[float], y_min: float, y_max: float, title: str, y_label: str) -> None:
        left, top, right, bottom = panel
        draw.text((left, top - 48), title, font=label_font, fill=COLORS["text"])
        for size in sizes:
            x = x_pos(size, 4000, 100000, left, right)
            draw.line((x, top, x, bottom), fill=COLORS["grid"], width=1)
            draw_centered(draw, (x, bottom + 26), f"{size // 1000}k", tick_font, COLORS["text"])
        for tick in y_ticks:
            y = log_y(tick, y_min, y_max, top, bottom)
            draw.line((left, y, right, y), fill=COLORS["grid"], width=1)
            label = short_k(tick) if y_max > 1000 else f"{tick:g}"
            draw.text((left - 72, y - 12), label, font=tick_font, fill=COLORS["text"])
        draw.line((left, top, left, bottom), fill=COLORS["axis"], width=3)
        draw.line((left, bottom, right, bottom), fill=COLORS["axis"], width=3)
        draw.text((left + 225, bottom + 55), "input gates", font=label_font, fill=COLORS["text"])
        draw.text((left - 97, top + 165), y_label, font=label_font, fill=COLORS["text"])

    axes(panels["gates"], [1, 10, 100, 1000, 10000, 100000, 1000000, 5000000], 1, 5_000_000, "Output gates", "log scale")
    axes(panels["runtime"], [0.01, 0.1, 1, 10, 100], 0.01, 100, "Runtime (s)", "log scale")

    for family_key, _label in families:
        color = COLORS[family_key]
        default_gates = []
        semantic_gates = []
        default_runtime = []
        semantic_runtime = []
        for size in sizes:
            row = data[family_key][str(size)]
            default_gates.append((size, row["baseline"]["output"]["total_gates"]))
            semantic_gates.append((size, max(1, row["prebasis"]["output"]["total_gates"])))
            default_runtime.append((size, row["baseline"]["runtime_s"]))
            semantic_runtime.append((size, row["prebasis"]["runtime_s"]))
        draw_series(draw, default_gates, color, panels["gates"], 1, 5_000_000, dashed=True)
        draw_series(draw, semantic_gates, color, panels["gates"], 1, 5_000_000, dashed=False)
        draw_series(draw, default_runtime, color, panels["runtime"], 0.01, 100, dashed=True)
        draw_series(draw, semantic_runtime, color, panels["runtime"], 0.01, 100, dashed=False)

    legend_items = []
    for family_key, label in families:
        legend_items.append((f"{label} upstream default", COLORS[family_key], "dash"))
        legend_items.append((f"{label} semantic UCC", COLORS[family_key], "line"))
    legend(draw, legend_items, 145, 625, 1310)

    output = FIGURE_DIR / "scaling_plot.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, optimize=True)
    print(f"wrote {output}")


def main() -> None:
    generate_real_instance_bars()
    generate_scaling_plot()


if __name__ == "__main__":
    main()
