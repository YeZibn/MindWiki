"""Command line entrypoint for MindWiki."""

from __future__ import annotations

import argparse
from pathlib import Path

from mindwiki.application.import_service import ImportService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mindwiki")
    subparsers = parser.add_subparsers(dest="command")

    import_parser = subparsers.add_parser("import", help="Import knowledge sources.")
    import_subparsers = import_parser.add_subparsers(dest="import_command")

    file_parser = import_subparsers.add_parser("file", help="Import a single file.")
    file_parser.add_argument("path", type=Path, help="Path to the input file.")

    dir_parser = import_subparsers.add_parser("dir", help="Import a directory.")
    dir_parser.add_argument("path", type=Path, help="Path to the input directory.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command != "import" or not args.import_command:
        parser.print_help()
        return 1

    service = ImportService()

    if args.import_command == "file":
        result = service.import_file(args.path)
    else:
        result = service.import_directory(args.path)

    print(result.message)
    return result.exit_code
