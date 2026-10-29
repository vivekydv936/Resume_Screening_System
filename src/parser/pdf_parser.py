"""Safe, temporary PDF text extraction for resume screening."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO

from pdfminer.high_level import extract_text
from pdfminer.pdfdocument import PDFPasswordIncorrect


@dataclass(frozen=True)
class ParseResult:
    """Consistent result returned for every PDF parse attempt."""

    candidate_id: str
    text: str
    status: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation."""
        return asdict(self) | {"warnings": list(self.warnings)}


def _normalize_text(text: str) -> str:
    """Normalize Unicode whitespace without changing technical terms."""
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def parse_pdf(resume_file: str | Path | BinaryIO, candidate_id: str | None = None) -> ParseResult:
    """Extract text from one PDF and report errors without exposing raw content."""
    identifier = candidate_id or (
        Path(resume_file).stem if isinstance(resume_file, (str, Path)) else "unknown"
    )
    if isinstance(resume_file, (str, Path)):
        path = Path(resume_file)
        if path.suffix.lower() != ".pdf":
            return ParseResult(identifier, "", "unsupported_file_type", ("Only PDF files are supported.",))
        if not path.is_file():
            return ParseResult(identifier, "", "unreadable", ("PDF file does not exist.",))
        source: str | Path | BinaryIO = path
    else:
        source = resume_file
    try:
        text = _normalize_text(extract_text(source))
    except PDFPasswordIncorrect:
        return ParseResult(identifier, "", "encrypted", ("The PDF requires a password.",))
    except Exception as exc:
        return ParseResult(identifier, "", "unreadable", (f"PDF extraction failed: {type(exc).__name__}.",))
    if not text:
        return ParseResult(identifier, "", "empty", ("The PDF contains no extractable text.",))
    return ParseResult(identifier, text, "success")
