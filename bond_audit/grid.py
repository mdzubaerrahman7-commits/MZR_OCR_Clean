"""Detect the ruled table grid (row/column border lines) in a scanned report image.

Bond consumption reports are printed as bordered tables. Rather than OCR-ing the
whole page as free text (which loses column alignment), we locate the horizontal
and vertical border lines with morphological image processing and use them to
crop individual cells for OCR. This is far more reliable for numeric columns
than plain text OCR + regex splitting.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract


@dataclass
class Grid:
    row_lines: list[int]  # y-coordinates of horizontal border lines, top to bottom
    col_lines: list[int]  # x-coordinates of vertical border lines, left to right

    @property
    def n_rows(self) -> int:
        return len(self.row_lines) - 1

    @property
    def n_cols(self) -> int:
        return len(self.col_lines) - 1


def _cluster(values: np.ndarray, gap: int = 5) -> list[int]:
    """Collapse a sorted array of pixel coordinates into cluster centers."""
    values = sorted(int(v) for v in values)
    if not values:
        return []
    groups: list[list[int]] = [[values[0]]]
    for v in values[1:]:
        if v - groups[-1][-1] <= gap:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [int(np.mean(g)) for g in groups]


def _binarize(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        ~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2
    )


def detect_grid(gray: np.ndarray, line_fraction: float = 0.25) -> Grid | None:
    """Find ruled table border lines in a grayscale page image.

    Returns None if no plausible grid (fewer than 2 rows or 2 columns) is found,
    e.g. because the page has no bordered table.
    """
    bw = _binarize(gray)
    h, w = bw.shape

    horiz_size = max(w // 30, 10)
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horiz_size, 1))
    horiz = cv2.dilate(cv2.erode(bw, horiz_kernel), horiz_kernel)

    vert_size = max(h // 30, 10)
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vert_size))
    vert = cv2.dilate(cv2.erode(bw, vert_kernel), vert_kernel)

    row_sum = horiz.sum(axis=1)
    row_lines = _cluster(np.where(row_sum > w * line_fraction * 255)[0])

    col_sum = vert.sum(axis=0)
    col_lines = _cluster(np.where(col_sum > h * line_fraction * 255)[0])

    if len(row_lines) < 2 or len(col_lines) < 2:
        return None

    col_lines = _merge_blank_columns(gray, row_lines, col_lines)
    return Grid(row_lines=row_lines, col_lines=col_lines)


def _column_has_content(gray: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> bool:
    """OCR a candidate column strip (over the data rows, not the header) to see
    if it holds any real text. Used to detect spurious extra grid lines that
    split one logical column into a blank sliver + the real column.
    """
    if x1 <= x0 or y1 <= y0:
        return False
    strip = gray[y0:y1, x0:x1]
    strip = cv2.resize(strip, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    text = pytesseract.image_to_string(strip, config="--psm 6").strip()
    return len(text) > 0


def _merge_blank_columns(
    gray: np.ndarray, row_lines: list[int], col_lines: list[int]
) -> list[int]:
    """Drop internal vertical lines that split a column into a blank strip plus
    the real column, by checking each candidate column for any OCR-able content
    across the data-row height (i.e. excluding the header row band).
    """
    if len(row_lines) < 3:
        return col_lines  # no data rows below the header to check against

    y0, y1 = row_lines[1], row_lines[-1]
    merged = [col_lines[0]]
    for x in col_lines[1:-1]:
        if _column_has_content(gray, y0, y1, merged[-1], x):
            merged.append(x)
        # else: blank strip, drop this boundary (merge into the growing column)

    last = col_lines[-1]
    if merged[-1] != last:
        if _column_has_content(gray, y0, y1, merged[-1], last):
            merged.append(last)
        else:
            merged[-1] = last  # extend final column out to the true table border
    return merged
