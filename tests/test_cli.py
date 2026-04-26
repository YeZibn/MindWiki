from __future__ import annotations

from pathlib import Path
from uuid import UUID

from mindwiki.application.import_models import ImportDirectoryRequest, ImportFileRequest
from mindwiki.application.import_service import (
    ImportService,
    scan_directory_files,
)
from mindwiki.cli.main import build_parser
from mindwiki.cli.main import main
from mindwiki.ingestion.markdown import parse_markdown
from mindwiki.infrastructure.import_repository import PersistedImportResult
from mindwiki.infrastructure.import_repository import DirectoryImportJobSummary
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


def test_scan_directory_files_filters_supported_types(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("# Notes", encoding="utf-8")
    (tmp_path / "paper.pdf").write_text("pdf", encoding="utf-8")
    (tmp_path / "image.png").write_text("png", encoding="utf-8")
    (tmp_path / "empty.md").write_text("", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "deep.md").write_text("# Deep", encoding="utf-8")

    result = scan_directory_files(tmp_path, recursive=False)

    assert [path.name for path in result.scanned_files] == ["empty.md", "image.png", "notes.md", "paper.pdf"]
    assert [path.name for path in result.supported_files] == ["notes.md", "paper.pdf"]
    assert [path.name for path in result.unsupported_files] == ["image.png"]
    assert [path.name for path in result.empty_files] == ["empty.md"]


def test_scan_directory_files_includes_nested_files_when_recursive(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("# Notes", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "deep.md").write_text("# Deep", encoding="utf-8")
    (tmp_path / "nested" / "image.png").write_text("png", encoding="utf-8")

    result = scan_directory_files(tmp_path, recursive=True)

    assert [path.relative_to(tmp_path).as_posix() for path in result.scanned_files] == [
        "nested/deep.md",
        "nested/image.png",
        "notes.md",
    ]
    assert [path.relative_to(tmp_path).as_posix() for path in result.supported_files] == [
        "nested/deep.md",
        "notes.md",
    ]
    assert [path.relative_to(tmp_path).as_posix() for path in result.unsupported_files] == [
        "nested/image.png",
    ]


def test_import_directory_returns_scan_summary(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("pdf", encoding="utf-8")
    (tmp_path / "c.txt").write_text("txt", encoding="utf-8")
    (tmp_path / "d.md").write_text("", encoding="utf-8")
    monkeypatch.delenv("MINDWIKI_DATABASE_URL", raising=False)
    monkeypatch.setattr(settings_module, "DOTENV_PATH", tmp_path / ".env")
    settings_module.clear_settings_cache()
    request = ImportDirectoryRequest(path=tmp_path, recursive=False)
    service = ImportService()

    result = service.import_directory(request)

    assert result.exit_code == 0
    assert "scanned_files=4" in result.message
    assert "supported_files=2" in result.message
    assert "unsupported_files=1" in result.message
    assert "empty_files=1" in result.message
    assert "pending_jobs=2" in result.message
    assert "skipped_jobs=2" in result.message
    assert "skipped_unsupported=1" in result.message
    assert "skipped_empty=1" in result.message
    assert "skipped_unchanged=0" in result.message
    assert "supported_names=a.md,b.pdf" in result.message
    assert "unsupported_names=c.txt" in result.message
    assert "empty_names=d.md" in result.message


def test_import_directory_respects_recursive_flag(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "b.md").write_text("# B", encoding="utf-8")
    monkeypatch.delenv("MINDWIKI_DATABASE_URL", raising=False)
    monkeypatch.setattr(settings_module, "DOTENV_PATH", tmp_path / ".env")
    settings_module.clear_settings_cache()
    service = ImportService()

    non_recursive = service.import_directory(
        ImportDirectoryRequest(path=tmp_path, recursive=False)
    )
    recursive = service.import_directory(
        ImportDirectoryRequest(path=tmp_path, recursive=True)
    )

    assert "scanned_files=1" in non_recursive.message
    assert "supported_names=a.md" in non_recursive.message
    assert "scanned_files=2" in recursive.message
    assert "supported_names=a.md,b.md" in recursive.message


def test_import_directory_persists_batch_and_child_jobs(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("pdf", encoding="utf-8")
    (tmp_path / "c.txt").write_text("txt", encoding="utf-8")
    (tmp_path / "d.md").write_text("", encoding="utf-8")
    repository = RecordingImportRepository()
    service = ImportService(repository=repository)

    result = service.import_directory(
        ImportDirectoryRequest(path=tmp_path, recursive=False, tags=("work",), source_note="batch"),
    )

    assert result.exit_code == 0
    assert "job_persistence=stored" in result.message
    assert "batch_job_id=00000000-0000-0000-0000-000000000010" in result.message
    assert "child_jobs=4" in result.message
    assert "pending_jobs=2" in result.message
    assert "skipped_jobs=2" in result.message
    assert "skipped_unsupported=1" in result.message
    assert "skipped_empty=1" in result.message
    assert "skipped_unchanged=0" in result.message
    assert repository.last_directory_request is not None
    assert repository.last_directory_request.path == tmp_path
    assert [path.name for path in repository.last_supported_files] == ["a.md", "b.pdf"]
    assert [path.name for path in repository.last_unsupported_files] == ["c.txt"]
    assert [path.name for path in repository.last_empty_files] == ["d.md"]


def test_import_directory_keeps_changed_files_pending_and_skips_unchanged(tmp_path: Path) -> None:
    (tmp_path / "same.md").write_text("# Same", encoding="utf-8")
    (tmp_path / "new.pdf").write_text("pdf", encoding="utf-8")
    repository = RecordingImportRepository()
    repository.unchanged_files = {tmp_path / "same.md"}
    service = ImportService(repository=repository)

    result = service.import_directory(
        ImportDirectoryRequest(path=tmp_path, recursive=False),
    )

    assert result.exit_code == 0
    assert "child_jobs=2" in result.message
    assert "pending_jobs=1" in result.message
    assert "skipped_jobs=1" in result.message
    assert "skipped_unsupported=0" in result.message
    assert "skipped_empty=0" in result.message
    assert "skipped_unchanged=1" in result.message
    assert repository.last_supported_files == (tmp_path / "new.pdf", tmp_path / "same.md")
    assert repository.unchanged_files == {tmp_path / "same.md"}


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
        self.last_directory_request: ImportDirectoryRequest | None = None
        self.last_supported_files: tuple[Path, ...] = ()
        self.last_unsupported_files: tuple[Path, ...] = ()
        self.last_empty_files: tuple[Path, ...] = ()
        self.unchanged_files: set[Path] = set()
        self.last_parsed = None
        self.created_job_type: str | None = None
        self.status_updates: list[tuple[str, str, str | None]] = []

    def create_directory_import_jobs(
        self,
        request: ImportDirectoryRequest,
        supported_files: tuple[Path, ...],
        unsupported_files: tuple[Path, ...],
        empty_files: tuple[Path, ...],
    ) -> tuple[UUID, tuple[UUID, ...], DirectoryImportJobSummary]:
        self.last_directory_request = request
        self.last_supported_files = supported_files
        self.last_unsupported_files = unsupported_files
        self.last_empty_files = empty_files
        child_ids: list[UUID] = []
        pending_jobs = 0
        skipped_unchanged = 0
        next_id = 11
        for path in supported_files:
            child_ids.append(UUID(f"00000000-0000-0000-0000-0000000000{next_id}"))
            if path in self.unchanged_files:
                skipped_unchanged += 1
            else:
                pending_jobs += 1
            next_id += 1
        for _ in unsupported_files:
            child_ids.append(UUID(f"00000000-0000-0000-0000-0000000000{next_id}"))
            next_id += 1
        for _ in empty_files:
            child_ids.append(UUID(f"00000000-0000-0000-0000-0000000000{next_id}"))
            next_id += 1
        return (
            UUID("00000000-0000-0000-0000-000000000010"),
            tuple(child_ids),
            DirectoryImportJobSummary(
                pending_jobs=pending_jobs,
                skipped_jobs=len(unsupported_files) + len(empty_files) + skipped_unchanged,
                skipped_unsupported=len(unsupported_files),
                skipped_empty=len(empty_files),
                skipped_unchanged=skipped_unchanged,
            ),
        )

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
