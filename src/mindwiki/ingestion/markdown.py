"""Markdown loading and minimal parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")


@dataclass(slots=True)
class MarkdownTitleCandidate:
    value: str
    source: str
    confidence: float


@dataclass(slots=True)
class MarkdownSection:
    level: int
    title: str | None
    content: str
    start_line: int
    end_line: int


@dataclass(slots=True)
class ParsedMarkdownDocument:
    raw_text: str
    standardized_text: str
    frontmatter: dict[str, object]
    title_candidates: tuple[MarkdownTitleCandidate, ...]
    sections: tuple[MarkdownSection, ...]


def load_markdown(path: Path) -> str:
    """Load a Markdown file as UTF-8 text with normalized newlines."""

    text = path.read_text(encoding="utf-8")
    return normalize_markdown_text(text)


def normalize_markdown_text(text: str) -> str:
    """Normalize line endings and remove UTF-8 BOM."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.removeprefix("\ufeff")


def parse_markdown(path: Path) -> ParsedMarkdownDocument:
    """Parse a Markdown file into a minimal standardized structure."""

    raw_text = load_markdown(path)
    frontmatter, body = extract_frontmatter(raw_text)
    sections = split_markdown_sections(body)
    title_candidates = build_title_candidates(path, frontmatter, sections)

    return ParsedMarkdownDocument(
        raw_text=raw_text,
        standardized_text=body,
        frontmatter=frontmatter,
        title_candidates=title_candidates,
        sections=sections,
    )


def extract_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Extract simple YAML frontmatter from Markdown text."""

    if not text.startswith("---\n"):
        return {}, text

    lines = text.split("\n")
    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return {}, text

    frontmatter_lines = lines[1:closing_index]
    body = "\n".join(lines[closing_index + 1 :])
    if body.startswith("\n"):
        body = body[1:]
    return parse_simple_yaml(frontmatter_lines), body


def parse_simple_yaml(lines: list[str]) -> dict[str, object]:
    """Parse a minimal subset of YAML used by current Markdown notes."""

    result: dict[str, object] = {}
    current_list_key: str | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if line.startswith((" ", "\t")) and current_list_key and stripped.startswith("- "):
            existing = result.setdefault(current_list_key, [])
            if isinstance(existing, list):
                existing.append(_strip_yaml_scalar(stripped[2:]))
            continue

        if ":" not in stripped:
            current_list_key = None
            continue

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        value = raw_value.strip()

        if not value:
            result[key] = []
            current_list_key = key
            continue

        result[key] = _strip_yaml_scalar(value)
        current_list_key = None

    return result


def _strip_yaml_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def split_markdown_sections(text: str) -> tuple[MarkdownSection, ...]:
    """Split Markdown body into heading-driven sections."""

    sections: list[MarkdownSection] = []
    current_level: int | None = None
    current_title: str | None = None
    current_start_line = 1
    current_lines: list[str] = []
    inside_code_block = False

    lines = text.split("\n")

    def flush(end_line: int) -> None:
        nonlocal current_level, current_title, current_lines, current_start_line
        content = "\n".join(current_lines).strip()
        if current_title is None and not content:
            current_lines = []
            current_start_line = end_line + 1
            return

        sections.append(
            MarkdownSection(
                level=current_level or 0,
                title=current_title,
                content=content,
                start_line=current_start_line,
                end_line=end_line,
            )
        )
        current_lines = []
        current_start_line = end_line + 1

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            inside_code_block = not inside_code_block

        heading_match = None if inside_code_block else HEADING_RE.match(line)
        if heading_match:
            flush(line_number - 1)
            current_level = len(heading_match.group(1))
            current_title = heading_match.group(2).strip()
            current_start_line = line_number
            continue

        current_lines.append(line)

    flush(len(lines))
    return tuple(sections)


def build_title_candidates(
    path: Path,
    frontmatter: dict[str, object],
    sections: tuple[MarkdownSection, ...],
) -> tuple[MarkdownTitleCandidate, ...]:
    candidates: list[MarkdownTitleCandidate] = []

    title_from_frontmatter = frontmatter.get("title")
    if isinstance(title_from_frontmatter, str) and title_from_frontmatter.strip():
        candidates.append(
            MarkdownTitleCandidate(
                value=title_from_frontmatter.strip(),
                source="frontmatter",
                confidence=0.95,
            )
        )

    first_h1 = next(
        (section.title for section in sections if section.level == 1 and section.title),
        None,
    )
    if first_h1:
        candidates.append(
            MarkdownTitleCandidate(
                value=first_h1,
                source="h1",
                confidence=0.8,
            )
        )

    candidates.append(
        MarkdownTitleCandidate(
            value=path.stem,
            source="filename",
            confidence=0.5,
        )
    )

    deduped: list[MarkdownTitleCandidate] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (candidate.value, candidate.source)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return tuple(deduped)
