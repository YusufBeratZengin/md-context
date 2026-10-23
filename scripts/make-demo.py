#!/usr/bin/env python3
"""Generate docs/demo.svg showing a real CLI command and its real output."""

import html
import io
import re
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from md_context.cli import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "vault"
OUTPUT = ROOT / "docs" / "demo.svg"


def run_command() -> tuple[str, list[str]]:
    command_str = 'md-context query "valve" --root tests/fixtures/vault --budget 4000'
    with tempfile.TemporaryDirectory() as td:
        cache_dir = Path(td) / "cache"
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            main(
                [
                    "query",
                    "valve",
                    "--root",
                    str(FIXTURE),
                    "--cache-dir",
                    str(cache_dir),
                    "--budget",
                    "4000",
                ]
            )
        raw_output = out.getvalue().strip()

    # Trim to ~20 lines showing the first few matching sections
    all_lines = raw_output.splitlines()
    trimmed: list[str] = []
    # Stop after the maintenance section to keep line count ~18-20 lines
    for line in all_lines:
        trimmed.append(line)
        if "Inspect each filter weekly" in line:
            break

    return command_str, trimmed


def colorize_line(line: str) -> str:
    escaped = html.escape(line)
    if not line:
        return ""
    if line.startswith("# "):
        return f'<tspan fill="#58a6ff" font-weight="600">{escaped}</tspan>'
    if line.startswith("## "):
        return f'<tspan fill="#79c0ff" font-weight="600">{escaped}</tspan>'
    if line.startswith("Source:"):
        source_html = re.sub(
            r"`([^`]+)`",
            r'<tspan fill="#e3b341">`\1`</tspan>',
            escaped,
        )
        return f'<tspan fill="#8b949e">{source_html}</tspan>'
    if line.startswith("Query:"):
        return f'<tspan fill="#8b949e">Query: </tspan><tspan fill="#a5d6ff">{escaped[7:]}</tspan>'

    colored = re.sub(
        r"(\[\[[^\]]+\]\])",
        r"__WIKI_START__\1__SPAN_END__",
        escaped,
    )
    colored = re.sub(
        r"(?:^|(?<=\s))(#[a-zA-Z0-9_-]+)",
        r"__TAG_START__\1__SPAN_END__",
        colored,
    )
    colored = (
        colored.replace("__WIKI_START__", '<tspan fill="#d2a8ff">')
        .replace("__TAG_START__", '<tspan fill="#f0883e">')
        .replace("__SPAN_END__", "</tspan>")
    )
    return f'<tspan fill="#c9d1d9">{colored}</tspan>'


def generate_svg() -> None:
    command_str, output_lines = run_command()

    char_height = 20
    top_margin = 56
    bottom_margin = 20
    left_margin = 24
    content_lines = [f"$ {command_str}"] + output_lines
    total_lines = len(content_lines)

    width = 780
    height = top_margin + (total_lines * char_height) + bottom_margin

    lines_svg: list[str] = []
    for idx, line in enumerate(content_lines):
        y_pos = top_margin + (idx * char_height)
        if idx == 0:
            cmd_escaped = html.escape(command_str)
            span = (
                f'<tspan fill="#7ee787" font-weight="bold">$ </tspan>'
                f'<tspan fill="#f0f6fc" font-weight="bold">{cmd_escaped}</tspan>'
            )
        else:
            span = colorize_line(line)
        lines_svg.append(f'    <text x="{left_margin}" y="{y_pos}">{span}</text>')

    body_content = "\n".join(lines_svg)
    font_stack = '"JetBrains Mono", "SF Mono", "Fira Code", Menlo, Monaco, Consolas, monospace'
    sans_stack = '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
    title_bar_path = (
        f"M1,11 A10,10 0 0,1 11,1 L{width - 11},1 A10,10 0 0,1 {width - 1},11 "
        f"L{width - 1},36 L1,36 Z"
    )

    svg_content = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">\n'
        f"  <style>\n"
        f"    .window {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}\n"
        f"    .title-bar {{ fill: #161b22; }}\n"
        f"    .title-text {{ fill: #8b949e; font-family: {sans_stack}; "
        f"font-size: 12px; font-weight: 500; }}\n"
        f"    text {{ font-family: {font_stack}; font-size: 13px; }}\n"
        f"  </style>\n\n"
        f"  <!-- Window frame -->\n"
        f'  <rect class="window" x="1" y="1" width="{width - 2}" '
        f'height="{height - 2}" rx="10" />\n\n'
        f"  <!-- Title bar -->\n"
        f'  <path class="title-bar" d="{title_bar_path}" />\n'
        f'  <line x1="1" y1="36" x2="{width - 1}" y2="36" stroke="#30363d" stroke-width="1" />\n\n'
        f"  <!-- Window controls -->\n"
        f'  <circle cx="20" cy="18" r="6" fill="#ff5f56" />\n'
        f'  <circle cx="40" cy="18" r="6" fill="#ffbd2e" />\n'
        f'  <circle cx="60" cy="18" r="6" fill="#27c93f" />\n\n'
        f"  <!-- Window title -->\n"
        f'  <text class="title-text" x="{width // 2}" y="22" '
        f'text-anchor="middle">md-context — terminal</text>\n\n'
        f"  <!-- Content -->\n"
        f"{body_content}\n"
        f"</svg>\n"
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg_content, encoding="utf-8")
    print(f"Generated {OUTPUT} ({total_lines} lines, {width}x{height})")


if __name__ == "__main__":
    generate_svg()
