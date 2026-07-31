"""Page loading, preprocessing, and OCR primitives."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image

PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def load_pages(path: Path) -> list[np.ndarray]:
    """Load a scanned document as a list of BGR page images (OpenCV format)."""
    suffix = path.suffix.lower()
    if suffix in PDF_SUFFIXES:
        from pdf2image import convert_from_path

        pil_pages = convert_from_path(str(path), dpi=300)
        return [cv2.cvtColor(np.array(p), cv2.COLOR_RGB2BGR) for p in pil_pages]
    if suffix in IMAGE_SUFFIXES:
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"Could not read image file: {path}")
        return [img]
    raise ValueError(f"Unsupported input type: {suffix} ({path})")


def to_gray(page: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)


def preprocess_for_ocr(gray: np.ndarray) -> np.ndarray:
    """Upscale and binarize for higher OCR accuracy on small printed text."""
    scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    return cv2.adaptiveThreshold(
        scaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def ocr_full_page_text(gray: np.ndarray) -> str:
    """Whole-page OCR dump, kept for provenance / manual review, not for
    structured extraction (table columns are handled cell-by-cell instead).
    """
    processed = preprocess_for_ocr(gray)
    return pytesseract.image_to_string(processed, config="--psm 6")


def ocr_cell(
    gray: np.ndarray,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
    psm: int = 6,
    whitelist: str | None = None,
    scale: int = 3,
) -> str:
    """OCR a single table cell, cropped from the full-resolution grayscale page.

    A char whitelist (e.g. digits only) substantially improves accuracy on
    quantity columns by ruling out letter/digit confusions.
    """
    pad = 2
    y0p, y1p = max(y0 + pad, 0), max(y1 - pad, y0 + 1)
    x0p, x1p = max(x0 + pad, 0), max(x1 - pad, x0 + 1)
    cell = gray[y0p:y1p, x0p:x1p]
    if cell.size == 0:
        return ""
    cell = cv2.resize(cell, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    config = f"--psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"
    text = pytesseract.image_to_string(cell, config=config)
    return " ".join(text.split())


def save_debug_image(image: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else image).save(path)
