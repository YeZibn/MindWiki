"""PDF loading and minimal parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(slots=True)
class PdfTitleCandidate:
    value: str
    source: str
    confidence: float


@dataclass(slots=True)
class PdfSection:
    level: int
    title: str | None
    content: str
    page_number: int


@dataclass(slots=True)
class ParsedPdfDocument:
    raw_text: str
    standardized_text: str
    title_candidates: tuple[PdfTitleCandidate, ...]
    sections: tuple[PdfSection, ...]
    page_count: int


class PdfReadError(Exception):
    """Raised when the PDF file cannot be opened or parsed."""


class PdfTextExtractionError(Exception):
    """Raised when the PDF file does not yield usable text."""


def parse_pdf(path: Path) -> ParsedPdfDocument:
    """Parse a text-based PDF into a minimal standardized structure."""

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pragma: no cover - library exception surface
        raise PdfReadError(str(exc)) from exc

    sections: list[PdfSection] = []
    page_texts: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            extracted_text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - library exception surface
            raise PdfReadError(str(exc)) from exc

        normalized_text = normalize_pdf_text(extracted_text)
        if not normalized_text.strip():
            continue

        page_texts.append(normalized_text)
        sections.append(
            PdfSection(
                level=0,
                title=f"Page {page_number}",
                content=normalized_text,
                page_number=page_number,
            )
        )

    if not page_texts:
        raise PdfTextExtractionError("No usable text extracted from PDF.")

    raw_text = "\n\n".join(page_texts)
    title_candidates = (
        PdfTitleCandidate(
            value=path.stem,
            source="filename",
            confidence=0.5,
        ),
    )

    return ParsedPdfDocument(
        raw_text=raw_text,
        standardized_text=raw_text,
        title_candidates=title_candidates,
        sections=tuple(sections),
        page_count=len(reader.pages),
    )


def normalize_pdf_text(text: str) -> str:
    """Normalize extracted PDF text into a stable newline form."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in normalized.split("\n")]
    compacted_lines = [line for line in lines if line]
    return "\n".join(compacted_lines).strip()
