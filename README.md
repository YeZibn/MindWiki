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
- `import dir` checks whether the path exists and whether it is a directory
- `--tag` can be repeated
- `--source-note` is optional
- `--recursive` is only used for `import dir`

Current limitation:

- `.pdf` files are currently accepted by the CLI, but PDF parsing is not implemented yet
- the CLI does not yet write parsed content to PostgreSQL
- real persistence and import job creation will be added in the next development tasks

Local PostgreSQL schema initialization:

```bash
psql "$MINDWIKI_DATABASE_URL" -f scripts/init_local_db.sql
```

Reset local PostgreSQL schema:

```bash
psql "$MINDWIKI_DATABASE_URL" -f scripts/reset_local_db.sql
```

Current status conventions:

- `import_jobs.status`: `pending`, `running`, `success`, `failed`, `skipped`, `cancelled`
- `documents.status`: `active`, `failed`, `deleted`
