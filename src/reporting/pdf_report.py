"""PDF report generation with reportlab (optional dependency)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

from src.utils.io import ensure_dir
from src.utils.logging import get_logger

logger = get_logger(__name__)


def create_pdf_report(
    title: str,
    sections: Mapping[str, str],
    figures: Mapping[str, Sequence[Path | str]] | None = None,
    tables: Mapping[str, pd.DataFrame] | None = None,
    output_path: Path | str = "output/reports/report.pdf",
    subtitle: str | None = None,
) -> Path:
    """Generate a PDF report.

    Args:
        title: Report title.
        sections: Mapping of section heading to body text.
        figures: Optional mapping of section heading to figure paths.
        tables: Optional mapping of section heading to a DataFrame.
        output_path: Destination ``.pdf`` path.
        subtitle: Optional subtitle.

    Returns:
        The destination path.

    Raises:
        ImportError: If reportlab is not installed.
        FileNotFoundError: If a referenced figure does not exist.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as error:  # pragma: no cover
        raise ImportError("reportlab is required to generate PDF reports") from error

    destination = Path(output_path)
    ensure_dir(destination.parent)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=12,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading1"],
        fontSize=15,
        spaceBefore=14,
        spaceAfter=8,
    )

    story: list[object] = [Paragraph(escape(title), title_style)]
    if subtitle:
        story.append(Paragraph(escape(subtitle), styles["Italic"]))
    story.extend([Spacer(1, 0.3 * inch), PageBreak()])

    for section_name, content in sections.items():
        story.append(Paragraph(escape(section_name), heading_style))
        for paragraph_text in str(content).split("\n\n"):
            if paragraph_text.strip():
                story.append(Paragraph(escape(paragraph_text.strip()), body_style))

        for figure in (figures or {}).get(section_name, []) or []:
            figure_path = Path(figure)
            if not figure_path.exists():
                raise FileNotFoundError(f"Figure not found: {figure_path}")
            story.append(Image(str(figure_path), width=6.0 * inch, height=3.4 * inch))
            story.append(Spacer(1, 0.15 * inch))

        frame = (tables or {}).get(section_name)
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            preview = frame.head(30).copy()
            for column in preview.columns:
                if pd.api.types.is_float_dtype(preview[column]):
                    preview[column] = preview[column].map(
                        lambda value: f"{value:.4g}" if pd.notna(value) else ""
                    )
            data = [list(preview.columns)] + preview.astype(str).values.tolist()
            table = Table(data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.2 * inch))

    document = SimpleDocTemplate(
        str(destination),
        pagesize=A4,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
        title=title,
    )
    document.build(story)
    logger.info("PDF report written to {}", destination)
    return destination
