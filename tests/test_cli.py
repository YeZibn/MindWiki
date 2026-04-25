from __future__ import annotations

from pathlib import Path

from mindwiki.application.import_service import (
    ImportFileRequest,
    ImportService,
)
from mindwiki.cli.main import build_parser
from mindwiki.cli.main import main


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
    assert "tags=work" in captured.out
    assert "source_note=study" in captured.out
