"""Self-contained HTML report generation with Jinja2."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from src.utils.io import ensure_dir, utc_now_iso
from src.utils.logging import get_logger

logger = get_logger(__name__)

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
  :root { --primary: #1f4e79; --accent: #2e8b57; --muted: #6b7280; }
  body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         margin: 0; color: #111827; background: #f9fafb; }
  header { background: var(--primary); color: white; padding: 2.5rem 1.5rem; }
  header h1 { margin: 0 0 .5rem 0; }
  header p { margin: 0; opacity: .85; }
  main { max-width: 960px; margin: 0 auto; padding: 1.5rem; }
  section { background: white; border-radius: 8px; padding: 1.25rem 1.5rem;
            margin-bottom: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  h2 { color: var(--primary); border-bottom: 2px solid #e5e7eb; padding-bottom: .4rem; }
  img { max-width: 100%; height: auto; margin: .75rem 0; border: 1px solid #e5e7eb; }
  table { border-collapse: collapse; width: 100%; font-size: .85rem; margin: .75rem 0; }
  th { background: var(--primary); color: white; text-align: left; }
  th, td { padding: .4rem .5rem; border: 1px solid #e5e7eb; }
  tr:nth-child(even) td { background: #f3f4f6; }
  footer { color: var(--muted); text-align: center; font-size: .8rem; padding: 1rem; }
  .meta { font-size: .8rem; color: var(--muted); }
</style>
</head>
<body>
<header>
  <h1>{{ title }}</h1>
  {% if subtitle %}<p>{{ subtitle }}</p>{% endif %}
  <p class="meta">Generated {{ generated_at }}</p>
</header>
<main>
{% for section in sections %}
  <section id="{{ section.anchor }}">
    <h2>{{ section.name }}</h2>
    {% for paragraph in section.paragraphs %}<p>{{ paragraph }}</p>{% endfor %}
    {% for image in section.images %}<img src="{{ image }}" alt="{{ section.name }} figure">{% endfor %}
    {% for table in section.tables %}{{ table | safe }}{% endfor %}
  </section>
{% endfor %}
</main>
<footer>Carbon Sequestration Analysis Project</footer>
</body>
</html>
"""


def _image_data_uri(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".") or "png"
    mime = "image/svg+xml" if suffix == "svg" else f"image/{suffix}"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render_html_report(
    title: str,
    sections: Mapping[str, str],
    figures: Mapping[str, Sequence[Path | str]] | None = None,
    tables: Mapping[str, pd.DataFrame] | None = None,
    output_path: Path | str = "output/reports/report.html",
    subtitle: str | None = None,
    embed_images: bool = True,
) -> Path:
    """Render a standalone HTML report.

    Args:
        title: Report title.
        sections: Mapping of section heading to body text.
        figures: Optional mapping of section heading to figure paths.
        tables: Optional mapping of section heading to DataFrames.
        output_path: Destination HTML path.
        subtitle: Optional subtitle.
        embed_images: Base64-embed images for a single-file report.

    Returns:
        The destination path.

    Raises:
        ImportError: If Jinja2 is not installed.
        FileNotFoundError: If a referenced figure does not exist.
    """
    try:
        from jinja2 import Template
    except ImportError as error:  # pragma: no cover
        raise ImportError("jinja2 is required to render HTML reports") from error

    rendered_sections = []
    for index, (name, content) in enumerate(sections.items()):
        images: list[str] = []
        for figure in (figures or {}).get(name, []) or []:
            figure_path = Path(figure)
            if not figure_path.exists():
                raise FileNotFoundError(f"Figure not found: {figure_path}")
            images.append(
                _image_data_uri(figure_path) if embed_images else figure_path.as_posix()
            )

        table_html: list[str] = []
        section_tables = (tables or {}).get(name)
        if isinstance(section_tables, pd.DataFrame):
            section_tables = [section_tables]
        for frame in section_tables or []:
            table_html.append(
                frame.to_html(index=False, border=0, classes="report-table", na_rep="")
            )

        paragraphs = [
            paragraph.strip()
            for paragraph in str(content).split("\n\n")
            if paragraph.strip()
        ]
        rendered_sections.append(
            {
                "anchor": f"section-{index + 1}",
                "name": name,
                "paragraphs": paragraphs,
                "images": images,
                "tables": table_html,
            }
        )

    template = Template(_TEMPLATE)
    html = template.render(
        title=title,
        subtitle=subtitle,
        generated_at=utc_now_iso(),
        sections=rendered_sections,
    )

    destination = Path(output_path)
    ensure_dir(destination.parent)
    destination.write_text(html, encoding="utf-8")
    logger.info("HTML report written to {}", destination)
    return destination
