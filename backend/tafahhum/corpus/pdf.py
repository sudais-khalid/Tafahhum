"""Extracting page images from a scanned PDF.

The page image is the primary evidence and is retained permanently. Everything
downstream — OCR text, corrections, extracted entries — is derived from it and
can be regenerated; the image cannot.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class PageImage:
    index: int          # 0-based position in the PDF
    path: Path
    width: int
    height: int
    sha256: str
    native_dpi: float   # effective DPI of the embedded scan, not the render


@dataclass(frozen=True)
class PdfSurvey:
    """What the PDF actually is, established before any processing."""

    page_count: int
    has_text_layer: bool
    text_chars_sampled: int
    median_native_dpi: float
    producer: str | None

    @property
    def needs_ocr(self) -> bool:
        return not self.has_text_layer

    @property
    def dpi_is_marginal(self) -> bool:
        """Below ~150 DPI, glyph-segmenting OCR degrades sharply on Arabic script."""
        return self.median_native_dpi < 150


def survey(pdf_path: Path, *, sample: int = 40) -> PdfSurvey:
    """Inspect a PDF before committing to a processing strategy.

    A 'scanned' PDF sometimes carries an embedded text layer, which makes OCR
    unnecessary. Checking first is cheap and skipping the check is expensive.
    """
    doc = pymupdf.open(pdf_path)
    try:
        chars = 0
        dpis: list[float] = []
        step = max(1, doc.page_count // sample)

        for i in range(0, doc.page_count, step):
            page = doc[i]
            chars += len(page.get_text().strip())
            for xref, *_ in page.get_images(full=True):
                info = doc.extract_image(xref)
                if page.rect.width:
                    dpis.append(info["width"] / (page.rect.width / 72))

        dpis.sort()
        median = dpis[len(dpis) // 2] if dpis else 0.0
        return PdfSurvey(
            page_count=doc.page_count,
            has_text_layer=chars > 0,
            text_chars_sampled=chars,
            median_native_dpi=median,
            producer=doc.metadata.get("producer") if doc.metadata else None,
        )
    finally:
        doc.close()


def extract_pages(
    pdf_path: Path,
    out_dir: Path,
    *,
    render_dpi: int = 300,
    first: int = 0,
    last: int | None = None,
) -> list[PageImage]:
    """Render pages to PNG.

    `render_dpi` is the rasterisation target, not the information content of the
    scan. Rendering a 70 DPI scan at 300 DPI adds pixels, not detail — it is done
    because OCR engines and vision models both handle a larger raster better, not
    because it recovers anything.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    pages: list[PageImage] = []

    try:
        end = doc.page_count if last is None else min(last, doc.page_count)
        for i in range(first, end):
            dest = out_dir / f"{i + 1:04d}.png"
            page = doc[i]

            native = 0.0
            for xref, *_ in page.get_images(full=True):
                info = doc.extract_image(xref)
                if page.rect.width:
                    native = max(native, info["width"] / (page.rect.width / 72))

            if not dest.exists():
                page.get_pixmap(dpi=render_dpi).save(dest)

            raw = dest.read_bytes()
            pix = pymupdf.Pixmap(dest)
            pages.append(
                PageImage(
                    index=i,
                    path=dest,
                    width=pix.width,
                    height=pix.height,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    native_dpi=native,
                )
            )
        return pages
    finally:
        doc.close()
