"""Command line entrypoint for MindWiki."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from mindwiki.application.import_service import (
    ImportDirectoryRequest,
    ImportFileRequest,
    ImportService,
    normalize_tags,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mindwiki")
    subparsers = parser.add_subparsers(dest="command")

    import_parser = subparsers.add_parser("import", help="Import knowledge sources.")
    import_subparsers = import_parser.add_subparsers(dest="import_command")

    file_parser = import_subparsers.add_parser("file", help="Import a single file.")
    file_parser.add_argument("path", type=Path, help="Path to the input file.")
    file_parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Tag to attach to the import. Can be repeated.",
    )
    file_parser.add_argument(
        "--source-note",
        help="Optional source note for the import request.",
    )

    dir_parser = import_subparsers.add_parser("dir", help="Import a directory.")
    dir_parser.add_argument("path", type=Path, help="Path to the input directory.")
    dir_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan subdirectories.",
    )
    dir_parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Tag to attach to imported files. Can be repeated.",
    )
    dir_parser.add_argument(
        "--source-note",
        help="Optional source note for the import request.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "import" or not args.import_command:
        parser.print_help()
        return 1

    service = ImportService()

    if args.import_command == "file":
        request = ImportFileRequest(
            path=args.path,
            tags=normalize_tags(args.tag),
            source_note=args.source_note,
        )
        result = service.import_file(request)
    else:
        request = ImportDirectoryRequest(
            path=args.path,
            recursive=args.recursive,
            tags=normalize_tags(args.tag),
            source_note=args.source_note,
        )
        result = service.import_directory(request)

    print(result.message)
    return result.exit_code
