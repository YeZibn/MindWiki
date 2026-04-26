from __future__ import annotations

from pathlib import Path
from uuid import UUID

from mindwiki.application.import_models import ImportFileRequest
from mindwiki.application.import_service import (
    ImportService,
)
from mindwiki.cli.main import build_parser
from mindwiki.cli.main import main
from mindwiki.ingestion.markdown import parse_markdown
from mindwiki.infrastructure.import_repository import PersistedImportResult
from mindwiki.infrastructure import settings as settings_module


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


def test_main_accepts_single_markdown_file(tmp_path: Path, capsys, monkeypatch) -> None:
    file_path = tmp_path / "notes.md"
    file_path.write_text("# Notes", encoding="utf-8")
    monkeypatch.delenv("MINDWIKI_DATABASE_URL", raising=False)
    monkeypatch.setattr(settings_module, "DOTENV_PATH", tmp_path / ".env")
    settings_module.clear_settings_cache()

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
    assert "persistence=" in captured.out
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


def test_import_file_persists_markdown_when_repository_is_available(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.md"
    file_path.write_text("# Notes\n\nHello.\n", encoding="utf-8")
    repository = RecordingImportRepository()
    service = ImportService(repository=repository)

    result = service.import_file(
        ImportFileRequest(
            path=file_path,
            tags=("work",),
            source_note="study",
        )
    )

    assert result.exit_code == 0
    assert "persistence=stored" in result.message
    assert "import_job_id=00000000-0000-0000-0000-000000000001" in result.message
    assert "document_id=00000000-0000-0000-0000-000000000003" in result.message
    assert repository.last_request is not None
    assert repository.last_request.path == file_path
    assert repository.last_parsed is not None
    assert repository.last_parsed.title_candidates[0].value == "Notes"
    assert repository.created_job_type == ".md"
    assert repository.status_updates == [
        ("00000000-0000-0000-0000-000000000001", "running", None),
        ("00000000-0000-0000-0000-000000000001", "success", None),
    ]


def test_import_file_marks_job_failed_on_parse_error(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "notes.md"
    file_path.write_text("# Notes\n", encoding="utf-8")
    repository = RecordingImportRepository()
    service = ImportService(repository=repository)

    def boom(_: Path):
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad input")

    monkeypatch.setattr("mindwiki.application.import_service.parse_markdown", boom)

    result = service.import_file(ImportFileRequest(path=file_path))

    assert result.exit_code == 1
    assert "reason=parse_error:UnicodeDecodeError" in result.message
    assert repository.status_updates[-1][1] == "failed"
    assert "UnicodeDecodeError" in (repository.status_updates[-1][2] or "")


class RecordingImportRepository:
    def __init__(self) -> None:
        self.last_request: ImportFileRequest | None = None
        self.last_parsed = None
        self.created_job_type: str | None = None
        self.status_updates: list[tuple[str, str, str | None]] = []

    def create_import_job(
        self,
        request: ImportFileRequest,
        detected_file_type: str | None,
    ) -> UUID:
        self.last_request = request
        self.created_job_type = detected_file_type
        return UUID("00000000-0000-0000-0000-000000000001")

    def update_import_job_status(
        self,
        import_job_id: UUID,
        status: str,
        *,
        error_message: str | None = None,
    ) -> None:
        self.status_updates.append((str(import_job_id), status, error_message))

    def persist_markdown_import(
        self,
        import_job_id: UUID,
        request: ImportFileRequest,
        parsed,
    ) -> PersistedImportResult:
        self.last_request = request
        self.last_parsed = parsed
        return PersistedImportResult(
            import_job_id=import_job_id,
            source_id=UUID("00000000-0000-0000-0000-000000000002"),
            document_id=UUID("00000000-0000-0000-0000-000000000003"),
            section_count=len(parsed.sections),
            chunk_count=len([section for section in parsed.sections if section.content]),
        )


def test_settings_load_database_url_from_dotenv(tmp_path: Path, monkeypatch) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "MINDWIKI_DATABASE_URL=postgresql://tester:secret@localhost:5432/mindwiki\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("MINDWIKI_DATABASE_URL", raising=False)
    monkeypatch.setattr(settings_module, "DOTENV_PATH", dotenv_path)
    settings_module.clear_settings_cache()

    settings = settings_module.get_settings()

    assert settings.database_url == "postgresql://tester:secret@localhost:5432/mindwiki"

    settings_module.clear_settings_cache()
