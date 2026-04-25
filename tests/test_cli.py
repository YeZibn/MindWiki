from __future__ import annotations

from mindwiki.cli.main import build_parser


def test_parser_accepts_import_file_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["import", "file", "notes.md"])

    assert args.command == "import"
    assert args.import_command == "file"
    assert str(args.path) == "notes.md"


def test_parser_accepts_import_dir_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["import", "dir", "docs"])

    assert args.command == "import"
    assert args.import_command == "dir"
    assert str(args.path) == "docs"
