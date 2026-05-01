"""Command line entrypoint for MindWiki."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import sys
from typing import Sequence

if __package__ in {None, ""}:
    # Support direct execution via `python src/mindwiki/cli/main.py`.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mindwiki.application.import_models import ImportDirectoryRequest, ImportFileRequest
from mindwiki.application.import_service import (
    ImportService,
    normalize_tags,
)
from mindwiki.application.qa_orchestration_service import build_qa_orchestration_service
from mindwiki.application.retrieval_models import QARequest


INTRO_TEXT = """欢迎使用 MindWiki 交互式命令行

输入 `help` 查看命令说明，输入 `examples` 查看常用示例，输入 `quit` 退出。
这里支持和单次命令模式相同的能力，包括 `import` 和 `ask`。
"""

INTERACTIVE_HELP_TEXT = """可用命令：
  help                      查看帮助说明。
  examples                  查看常用命令示例。
  import file <path>        导入单个 Markdown 或 PDF 文件。
  import dir <path>         导入目录中的受支持文件。
  ask <question>            基于知识库发起提问。
  quit                      退出交互式命令行。
  exit                      退出交互式命令行。

说明：
  - 参数名保持英文，例如 `--tag`、`--source-note`、`--top-k`
  - 如果路径或问题里有空格，请使用引号包起来
  - `--tag` 可以重复传入，例如：import file notes.md --tag work --tag rag
  - 仍然支持单次命令模式：`mindwiki import file ...` 或 `mindwiki ask ...`
"""

EXAMPLES_TEXT = """常用示例：
  import file ./notes/example.md
  import file ./notes/example.md --tag work --tag rag --source-note "learning notes"
  import dir ./notes --recursive --tag work
  ask "Step 10 的职责是什么？"
  ask "总结 Step 8 和 Step 9 的职责" --top-k 3
"""


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

    ask_parser = subparsers.add_parser("ask", help="Run the first-stage QA flow.")
    ask_parser.add_argument("question", help="The question to ask against the knowledge base.")
    ask_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-k candidates retrieved inside each sub-query boundary.",
    )

    return parser


def _run_ask_command(args: argparse.Namespace) -> int:
    if args.command == "ask":
        service = build_qa_orchestration_service()
        result = service.ask(
            QARequest(
                question=args.question,
                top_k=args.top_k,
            )
        )
        print(
            json.dumps(
                {
                    "question": result.question,
                    "decomposition_mode": result.decomposition.decomposition_mode,
                    "sub_queries": list(result.decomposition.sub_queries),
                    "answer": result.answer_result.answer,
                    "confidence": result.answer_result.confidence,
                    "sources": [
                        {
                            "citation_id": source.citation_id,
                            "document_title": source.document_title,
                            "section_title": source.section_title,
                            "snippet": source.snippet,
                            "evidence_role": source.evidence_role,
                        }
                        for source in result.answer_result.sources
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    return 1


def _run_import_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
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


def run_command(argv: Sequence[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ask":
        return _run_ask_command(args)

    return _run_import_command(args, parser)


def run_interactive_shell(read_input=input) -> int:
    print(INTRO_TEXT)

    while True:
        try:
            raw_command = read_input("mindwiki> ").strip()
        except EOFError:
            print()
            print("已退出 MindWiki。")
            return 0
        except KeyboardInterrupt:
            print()
            print("输入 `quit` 或 `exit` 可以退出。")
            continue

        if not raw_command:
            continue

        lowered = raw_command.lower()
        if lowered in {"quit", "exit", "退出"}:
            print("已退出 MindWiki。")
            return 0
        if lowered in {"help", "帮助"}:
            print(INTERACTIVE_HELP_TEXT)
            continue
        if lowered in {"examples", "example", "示例", "例子"}:
            print(EXAMPLES_TEXT)
            continue

        try:
            argv = shlex.split(raw_command)
        except ValueError as exc:
            print(f"命令解析失败：{exc}")
            continue

        try:
            run_command(argv)
        except SystemExit as exc:
            if exc.code not in {0, None}:
                print(f"命令执行失败，退出码：{exc.code}")
        except KeyboardInterrupt:
            print()
            print("命令已中断。")
        except Exception as exc:
            print(f"命令执行失败：{exc.__class__.__name__}: {exc}")


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        return run_interactive_shell()

    return run_command(argv)


if __name__ == "__main__":
    raise SystemExit(main())
