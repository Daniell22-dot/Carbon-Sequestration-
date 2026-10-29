"""Excel workbook export with per-table sheets and metadata."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from src.utils.io import ensure_dir, utc_now_iso
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _autosize_columns(writer: pd.ExcelWriter) -> None:
    for worksheet in writer.sheets.values():
        for column_cells in worksheet.columns:
            values = [str(cell.value) if cell.value is not None else "" for cell in column_cells]
            width = max((len(value) for value in values), default=8) + 2
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(width, 60)


def export_workbook(
    sheets: Mapping[str, pd.DataFrame],
    output_path: Path | str = "output/data_exports/analysis.xlsx",
    metadata: Mapping[str, object] | None = None,
) -> Path:
    """Write DataFrames to a multi-sheet Excel workbook.

    Args:
        sheets: Mapping of sheet name to DataFrame.
        output_path: Destination ``.xlsx`` path.
        metadata: Optional provenance fields written to a ``Metadata`` sheet.

    Returns:
        The destination path.

    Raises:
        ValueError: If ``sheets`` is empty or a sheet name is invalid.
    """
    if not sheets:
        raise ValueError("At least one sheet is required")

    destination = Path(output_path)
    ensure_dir(destination.parent)

    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            resolved_name = str(sheet_name)[:31]
            if not resolved_name:
                raise ValueError("Sheet names must be non-empty")
            frame.to_excel(writer, sheet_name=resolved_name, index=False)

        if metadata:
            meta_frame = pd.DataFrame(
                {
                    "key": ["generated_at", *metadata.keys()],
                    "value": [utc_now_iso(), *metadata.values()],
                }
            )
            meta_frame.to_excel(writer, sheet_name="Metadata", index=False)

        _autosize_columns(writer)

    logger.info("Excel workbook written to {}", destination)
    return destination
