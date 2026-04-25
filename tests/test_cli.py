from __future__ import annotations

from pathlib import Path

from mindwiki.application.import_service import (
    ImportFileRequest,
    ImportService,
)
from mindwiki.cli.main import build_parser
from mindwiki.cli.main import main
from mindwiki.ingestion.markdown import parse_markdown


def test_parser_accepts_import_file_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "import",
            "file",
            "notes.md",
            "--tag",
            "work",
            "--tag",
            "contract",
            "--source-note",
            "study",
        ]
    )

    assert args.command == "import"
    assert args.import_command == "file"
    assert str(args.path) == "notes.md"
    assert args.tag == ["work", "contract"]
    assert args.source_note == "study"


def test_parser_accepts_import_dir_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["import", "dir", "docs", "--recursive", "--tag", "work"])

    assert args.command == "import"
    assert args.import_command == "dir"
    assert str(args.path) == "docs"
    assert args.recursive is True
    assert args.tag == ["work"]


def test_import_file_returns_error_for_missing_path() -> None:
    service = ImportService()

    result = service.import_file(ImportFileRequest(path=Path("/tmp/not-found.md")))

    assert result.exit_code == 1
    assert "File not found" in result.message


def test_import_file_returns_error_for_unsupported_type(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello", encoding="utf-8")
    service = ImportService()

    result = service.import_file(ImportFileRequest(path=file_path))

    assert result.exit_code == 1
    assert "Unsupported file type" in result.message


def test_main_accepts_single_markdown_file(tmp_path: Path, capsys) -> None:
    file_path = tmp_path / "notes.md"
    file_path.write_text("# Notes", encoding="utf-8")

    exit_code = main(
        [
            "import",
            "file",
            str(file_path),
            "--tag",
            "work",
            "--source-note",
            "study",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Single-file import request accepted." in captured.out
    assert "title=Notes" in captured.out
    assert "sections=1" in captured.out
    assert "tags=work" in captured.out
    assert "source_note=study" in captured.out


def test_parse_markdown_extracts_frontmatter_and_sections(tmp_path: Path) -> None:
    file_path = tmp_path / "rag-notes.md"
    file_path.write_text(
        (
            "---\n"
            "title: RAG Notes\n"
            "tags:\n"
            "  - rag\n"
            "  - retrieval\n"
            "---\n\n"
            "# Overview\n\n"
            "RAG combines retrieval and generation.\n\n"
            "## Retrieval\n\n"
            "Retrieval finds evidence.\n"
        ),
        encoding="utf-8",
    )

    parsed = parse_markdown(file_path)

    assert parsed.frontmatter["title"] == "RAG Notes"
    assert parsed.frontmatter["tags"] == ["rag", "retrieval"]
    assert parsed.title_candidates[0].value == "RAG Notes"
    assert len(parsed.sections) == 2
    assert parsed.sections[0].title == "Overview"
    assert parsed.sections[1].title == "Retrieval"


def test_parse_markdown_keeps_anonymous_intro_section(tmp_path: Path) -> None:
    file_path = tmp_path / "journal.md"
    file_path.write_text(
        "Intro paragraph.\n\n# Topic\n\nDetails here.\n",
        encoding="utf-8",
    )

    parsed = parse_markdown(file_path)

    assert len(parsed.sections) == 2
    assert parsed.sections[0].title is None
    assert parsed.sections[0].content == "Intro paragraph."
    assert parsed.sections[1].title == "Topic"
