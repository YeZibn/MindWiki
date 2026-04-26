# MindWiki

MindWiki is a personal knowledge base RAG project.

## Current Stage

The repository is in the early development stage.
The first implementation target is a minimal ingestion MVP focused on Markdown single-file import.

## Local Development

Recommended toolchain:

- Python 3.11+
- `uv`

Common commands:

```bash
uv sync
uv run mindwiki --help
```

## CLI Usage

Current available commands:

```bash
PYTHONPATH=src python3 -m mindwiki --help
PYTHONPATH=src python3 -m mindwiki import file --help
PYTHONPATH=src python3 -m mindwiki import dir --help
```

Single-file import:

```bash
PYTHONPATH=src python3 -m mindwiki import file ./notes/example.md
PYTHONPATH=src python3 -m mindwiki import file ./notes/example.md --tag work --tag rag --source-note "learning notes"
```

Directory import:

```bash
PYTHONPATH=src python3 -m mindwiki import dir ./notes
PYTHONPATH=src python3 -m mindwiki import dir ./notes --recursive --tag work --source-note "knowledge directory"
```

Current CLI behavior:

- `import file` checks whether the path exists, whether it is a file, and whether the file type is supported
- supported file types are currently `.md` and `.pdf`
- `.md` files are currently read and parsed with a minimal Markdown pipeline
- current Markdown parsing includes UTF-8 loading, newline normalization, simple frontmatter extraction, title candidate extraction, and heading-based section splitting
- successful Markdown imports currently print a lightweight parsing summary such as `title=...` and `sections=...`
- if `MINDWIKI_DATABASE_URL` is configured and the local schema has been initialized, Markdown imports will also write `sources`, `import_jobs`, `documents`, `sections`, and `chunks` to PostgreSQL
- `import dir` checks whether the path exists and whether it is a directory
- `import dir` currently creates a batch job plus file child jobs; supported files with the same `file_path` and same `content_hash` as an existing document are marked as `skipped` with `error_message=content_unchanged`
- `import dir` currently prints a lightweight summary including `pending_jobs`, `skipped_jobs`, `skipped_unsupported`, `skipped_empty`, and `skipped_unchanged`
- `--tag` can be repeated
- `--source-note` is optional
- `--recursive` is only used for `import dir`

Current limitation:

- `.pdf` files are currently accepted by the CLI, but PDF parsing is not implemented yet
- if `MINDWIKI_DATABASE_URL` is missing, persistence is skipped and the CLI will report `reason=database_url_missing`
- real persistence and import job creation will be added in the next development tasks

PostgreSQL persistence setup:

```bash
cp .env.example .env
# edit .env and set your real username/password/database
export MINDWIKI_DATABASE_URL='postgresql://user:password@localhost:5432/mindwiki'
/Library/PostgreSQL/16/bin/psql 'postgresql://user:password@localhost:5432/postgres' -c 'CREATE DATABASE mindwiki;'
/Library/PostgreSQL/16/bin/psql "$MINDWIKI_DATABASE_URL" -f scripts/init_local_db.sql
PYTHONPATH=src python3 -m mindwiki import file ./notes/example.md
```

The application will automatically read `MINDWIKI_DATABASE_URL` from the project root `.env` file if the shell environment variable is not set.
Shell commands such as `psql` do not read `.env` automatically, so export the variable in the shell when you run schema scripts manually.

Local PostgreSQL schema initialization:

```bash
/Library/PostgreSQL/16/bin/psql "$MINDWIKI_DATABASE_URL" -f scripts/init_local_db.sql
```

Reset local PostgreSQL schema:

```bash
/Library/PostgreSQL/16/bin/psql "$MINDWIKI_DATABASE_URL" -f scripts/reset_local_db.sql
```

Minimal end-to-end verification:

```bash
PYTHONPATH=src python3 scripts/verify_local_import.py
PYTHONPATH=src python3 scripts/verify_local_directory_import.py
```

The verification script will:

- create a temporary Markdown file
- run `mindwiki import file ...`
- query `sources`, `import_jobs`, `documents`, `sections`, and `chunks`
- print a JSON summary and exit with code `0` only if the expected row deltas are observed

The directory verification script will:

- create a temporary directory with supported, unsupported, and empty files
- import one Markdown file first to create an unchanged-content baseline
- run `mindwiki import dir ...`
- verify `pending_jobs`, `skipped_jobs`, `skipped_unsupported`, `skipped_empty`, and `skipped_unchanged`
- query child jobs for the generated `batch_job_id`

Current status conventions:

- `import_jobs.status`: `pending`, `running`, `success`, `failed`, `skipped`, `cancelled`
- `documents.status`: `active`, `failed`, `deleted`
