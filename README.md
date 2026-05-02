# MindWiki

MindWiki is a personal knowledge base RAG project.

## Current Stage

The repository is in the early development stage.
The current implementation focus is a minimal ingestion plus LLM integration MVP.

## Local Development

Recommended toolchain:

- Python 3.11+
- `uv`

Common commands:

```bash
uv sync
uv run mindwiki --help
PYTHONPATH=src python3 -m pytest
```

## CLI Usage

Current available commands:

```bash
PYTHONPATH=src python3 -m mindwiki --help
PYTHONPATH=src python3 -m mindwiki import file --help
PYTHONPATH=src python3 -m mindwiki import dir --help
PYTHONPATH=src python3 -m mindwiki ask --help
```

Current non-CLI integration entrypoint:

- `src/mindwiki/llm/service.py` exposes the first `generate_text` service entrypoint for OpenAI-compatible LLM calls
- `src/mindwiki/llm/embedding_service.py` exposes the first embedding generation service entrypoint for OpenAI-compatible embedding calls
- `src/mindwiki/application/retrieval_service.py` exposes the first `bm25_only` retrieval service entrypoint
- `src/mindwiki/application/query_decomposition_service.py` exposes the first `Step 09.1` query decomposition service entrypoint
- `src/mindwiki/application/query_expansion_service.py` exposes the first `Step 09.2` fixed `base_query / step_back_query / hyde_query` expansion service entrypoint
- `src/mindwiki/application/subquery_retrieval_service.py` exposes the first `Step 09.3` per-sub-query four-route retrieval merge entrypoint
- `src/mindwiki/application/subquery_rerank_service.py` exposes the first `Step 09.4` per-sub-query rerank entrypoint
- `src/mindwiki/application/context_builder_service.py` exposes the first `Step 09.5` context builder entrypoint
- `src/mindwiki/application/citation_payload_service.py` exposes the first `Step 09.6` citation payload entrypoint
- `src/mindwiki/application/answer_generation_service.py` exposes the first `Step 10` QA answer generation entrypoint
- `src/mindwiki/application/qa_orchestration_service.py` exposes the first unified QA orchestration entrypoint across `Step 09 + Step 10`

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
- `.pdf` files are currently parsed with a minimal text-based PDF pipeline for copyable-text PDFs
- successful Markdown imports currently print a lightweight parsing summary such as `title=...` and `sections=...`
- successful PDF imports currently print a lightweight parsing summary such as `title=...`, `pages=...`, and `sections=...`
- if `MINDWIKI_DATABASE_URL` is configured and the local schema has been initialized, Markdown imports will also write `sources`, `import_jobs`, `documents`, `sections`, and `chunks` to PostgreSQL
- if `MINDWIKI_DATABASE_URL` is configured and the local schema has been initialized, copyable-text PDF imports will also write `sources`, `import_jobs`, `documents`, `sections`, and `chunks` to PostgreSQL
- if PostgreSQL, embedding, and `Milvus` settings are all configured, successful Markdown/PDF imports will also generate chunk embeddings and write vectors to `Milvus`
- `import dir` checks whether the path exists and whether it is a directory
- `import dir` currently creates a batch job plus file child jobs; supported files with the same `file_path` and same `content_hash` as an existing document are marked as `skipped` with `error_message=content_unchanged`
- `import dir` currently prints a lightweight summary including `pending_jobs`, `skipped_jobs`, `skipped_unsupported`, `skipped_empty`, and `skipped_unchanged`
- `import dir` now also consumes newly created `pending` child jobs in the same command: Markdown child jobs are executed immediately, and copyable-text PDF child jobs are also executed through the real PDF import path
- current execution output also includes `success_jobs`, `failed_jobs`, and `executed_skipped_jobs`
- the parent directory job currently keeps `status=success` and writes the execution aggregate back to `input_payload.execution_summary`
- `--tag` can be repeated
- `--source-note` is optional
- `--recursive` is only used for `import dir`
- `ask` now runs the first-stage unified QA flow and prints structured JSON

Current limitation:

- `.pdf` single-file parsing currently only supports copyable-text PDFs
- `.pdf` directory execution currently only supports copyable-text PDFs
- if `MINDWIKI_DATABASE_URL` is missing, persistence is skipped and the CLI will report `reason=database_url_missing`
- PDF OCR and more advanced PDF processing will be added in later development tasks
- LLM integration currently exposes only the `generate_text` capability
- embedding integration currently supports only chunk-level vector generation for import-time indexing
- structured output handling currently supports minimal local JSON parsing and lightweight schema checks
- citation validation and repair retries are not implemented yet
- retrieval currently supports `bm25_only`, `vector_only`, and `hybrid`
- Step 09 now implements the full first-stage orchestration chain:
  - query decomposition
  - fixed query expansion
  - per-sub-query four-route retrieval merge
  - per-sub-query rerank
  - context builder
  - citation payload
- Step 10 currently implements only the first QA answer generation path
- document summary, multi-document synthesis, comparison analysis, and related note recommendation are not implemented yet

## LLM Setup

The project now supports a minimal OpenAI-compatible LLM integration.

Required environment variables:

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_PATH=/Users/yezibin/Project/MindWiki/logs/mindwiki.jsonl
LLM_BASE_URL=https://kuaipao.ai/v1
LLM_API_KEY=your-api-key
LLM_MODEL_ID=gpt-5.4
LLM_MODEL_MINI_ID=gpt-5.4-mini
LLM_TIMEOUT_MS=30000
LLM_RERANK_BASE_URL=https://api.siliconflow.cn/v1
LLM_RERANK_API_KEY=your-rerank-api-key
LLM_RERANK_MODEL_ID=Qwen/Qwen3-Reranker-8B
LLM_RERANK_TIMEOUT_MS=30000
LLM_EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
LLM_EMBEDDING_API_KEY=your-embedding-api-key
LLM_EMBEDDING_MODEL_ID=Qwen/Qwen3-Embedding-8B
LLM_EMBEDDING_TIMEOUT_MS=30000
SYSTEM_MEMORY_MILVUS_URI=http://127.0.0.1:19530
SYSTEM_MEMORY_MILVUS_TOKEN=
MILVUS_COLLECTION_NAME=mindwiki_chunks
```

Current LLM behavior:

- structured application logs now default to `JSON lines` on `stdout / stderr`
- each logged QA / LLM flow now carries a generated `request_id`
- `build_llm_service()` reads LLM settings from `.env` or the shell environment
- `build_rerank_service()` reads rerank settings from `.env` or the shell environment
- `build_embedding_service()` reads embedding settings from `.env` or the shell environment
- `generate_text` builds `system + user` messages and sends them through `/chat/completions`
- rerank execution sends query + candidate documents through `/rerank`
- embedding generation sends chunk text batches through `/embeddings`
- retry is only used for retryable failures
- fallback can switch from `LLM_MODEL_ID` to `LLM_MODEL_MINI_ID`
- structured outputs can be parsed locally when `response_format.type=json_schema`
- local schema validation currently checks JSON parseability, required fields, and basic types

Current logging behavior:

- first-stage logs currently emit structured `JSON lines`
- `INFO` and lower-severity events go to `stdout`
- `ERROR` events go to `stderr`
- logs are also appended to the local file path in `LOG_FILE_PATH`
- the default local file path is `/Users/yezibin/Project/MindWiki/logs/mindwiki.jsonl`
- sensitive metadata fields such as `api_key` and `token` are redacted
- long metadata strings are truncated before output
- current structured logs now cover:
  - unified QA orchestration
  - `generate_text`
  - `rerank`
  - `embedding`
  - `import file`
  - `import dir`
- current minimal logging verification is covered by local automated tests rather than a separate network-dependent script

Current embedding behavior:

- embedding main object is `chunk`
- embedding input currently uses:
  - `document_title`
  - optional `section_title`
  - `chunk_text`
- successful import-time vector sync writes:
  - one `Milvus` record per chunk
  - `embedding_ref / embedding_provider / embedding_model / embedding_version / embedding_dim` back to PostgreSQL
- current embedding version is `v1`

Minimal `generate_text` example:

```python
from mindwiki.llm.service import GenerateTextInput, build_llm_service

service = build_llm_service()
response = service.generate_text(
    GenerateTextInput(
        system_prompt="You are a concise assistant. Reply with plain text only.",
        user_prompt="Reply with exactly: MINDWIKI_LLM_OK",
        task_type="smoke_test",
        max_tokens=32,
    )
)

print(response.status)
print(response.output_text)
```

## Retrieval Setup

The project now supports first-stage `bm25_only`, `vector_only`, and `hybrid` retrieval paths.

Current retrieval behavior:

- retrieval main object is `chunk`
- supported retrieval modes are currently:
  - `bm25_only`
  - `vector_only`
  - `hybrid`
- vector storage is now written during import when embedding and `Milvus` settings are configured
- strong filters currently support:
  - `source_types`
  - `document_scope`
  - `tags`
  - `time_range`
- first-stage `time_range` means `documents.imported_at`
- `match_sources` currently reflects:
  - `document_title`
  - `section_title`
  - `document_tags`
  - `chunk_text`
- `vector_only` currently returns:
  - `match_sources = ("vector",)`
  - `score_breakdown = {"vector_score": ...}`
- `hybrid` currently returns:
  - merged `match_sources`
  - `score = final_score`
  - `score_breakdown` including:
    - `vector_score`
    - `bm25_score`
    - `rrf_score`
    - `normalized_rrf_score`
    - `normalized_vector_score`
    - `normalized_bm25_score`
    - `dual_hit_bonus`
    - `final_score`

Minimal retrieval example:

```python
from mindwiki.application.retrieval_models import RetrievalQuery
from mindwiki.application.retrieval_service import RetrievalService

service = RetrievalService()
result = service.retrieve(
    RetrievalQuery(
        query="verification note",
        top_k=5,
    )
)

for hit in result.hits:
    print(hit.document_title, hit.score, hit.match_sources)
```

Minimal vector retrieval example:

```python
from mindwiki.application.retrieval_models import RetrievalQuery
from mindwiki.application.retrieval_service import RetrievalService

service = RetrievalService()
result = service.retrieve(
    RetrievalQuery(
        query="embedding generation and vector sync verification",
        top_k=3,
        retrieval_mode="vector_only",
    )
)

for hit in result.hits:
    print(hit.document_title, hit.score, hit.score_breakdown)
```

Minimal hybrid retrieval example:

```python
from mindwiki.application.retrieval_models import RetrievalQuery
from mindwiki.application.retrieval_service import RetrievalService

service = RetrievalService()
result = service.retrieve(
    RetrievalQuery(
        query="exact keyword recall and semantic recall fusion",
        top_k=3,
        retrieval_mode="hybrid",
    )
)

for hit in result.hits:
    print(hit.document_title, hit.score, hit.score_breakdown)
```

Minimal Step 09 front-half orchestration example:

```python
from mindwiki.application.query_decomposition_service import QueryDecompositionService
from mindwiki.application.query_expansion_service import build_query_expansion_service
from mindwiki.application.subquery_retrieval_service import SubQueryRetrievalService

decomposition = QueryDecompositionService().decompose("分别总结 Step 8 和 Step 9 的职责")
expansion_service = build_query_expansion_service()
sub_query_service = SubQueryRetrievalService()

for index, sub_query in enumerate(decomposition.sub_queries, start=1):
    expansion = expansion_service.expand(sub_query)
    result = sub_query_service.retrieve_for_sub_query(
        sub_query_id=f"sq_{index}",
        sub_query_text=sub_query,
        expansion=expansion,
        top_k=3,
    )
    print(result.sub_query_id, result.sub_query_text, len(result.candidates))
```

Local Step 09 front-half verification command:

```bash
PYTHONPATH=src /opt/miniconda3/bin/python3 scripts/verify_local_step09_orchestration.py
```

Minimal Step 09 full orchestration example:

```python
from mindwiki.application.citation_payload_service import CitationPayloadService
from mindwiki.application.context_builder_service import ContextBuilderService
from mindwiki.application.query_decomposition_service import QueryDecompositionService
from mindwiki.application.query_expansion_service import build_query_expansion_service
from mindwiki.application.subquery_rerank_service import build_subquery_rerank_service
from mindwiki.application.subquery_retrieval_service import SubQueryRetrievalService

decomposition = QueryDecompositionService().decompose("分别总结 Step 8 和 Step 9 的职责")
expansion_service = build_query_expansion_service()
retrieval_service = SubQueryRetrievalService()
rerank_service = build_subquery_rerank_service()
context_builder = ContextBuilderService()
citation_service = CitationPayloadService()

rerank_results = []
for index, sub_query in enumerate(decomposition.sub_queries, start=1):
    expansion = expansion_service.expand(sub_query)
    retrieval_result = retrieval_service.retrieve_for_sub_query(
        sub_query_id=f"sq_{index}",
        sub_query_text=sub_query,
        expansion=expansion,
        top_k=5,
    )
    rerank_results.append(rerank_service.rerank_sub_query(retrieval_result))

context_result = context_builder.build_context(tuple(rerank_results))
citation_result = citation_service.build_citations(context_result)

print(len(context_result.sections), len(citation_result.citations))
```

Local Step 09 full orchestration verification command:

```bash
PYTHONPATH=src /opt/miniconda3/bin/python3 scripts/verify_local_step09_full_orchestration.py
```

Minimal Step 10 QA answer generation example:

```python
from mindwiki.application.answer_generation_service import build_answer_generation_service
from mindwiki.application.citation_payload_service import CitationPayloadService
from mindwiki.application.context_builder_service import ContextBuilderService
from mindwiki.application.query_decomposition_service import QueryDecompositionService
from mindwiki.application.query_expansion_service import build_query_expansion_service
from mindwiki.application.subquery_rerank_service import build_subquery_rerank_service
from mindwiki.application.subquery_retrieval_service import SubQueryRetrievalService

question = "分别总结 Step 8 和 Step 9 的职责"
decomposition = QueryDecompositionService().decompose(question)
expansion_service = build_query_expansion_service()
retrieval_service = SubQueryRetrievalService()
rerank_service = build_subquery_rerank_service()
context_builder = ContextBuilderService()
citation_service = CitationPayloadService()
answer_service = build_answer_generation_service()

rerank_results = []
for index, sub_query in enumerate(decomposition.sub_queries, start=1):
    expansion = expansion_service.expand(sub_query)
    retrieval_result = retrieval_service.retrieve_for_sub_query(
        sub_query_id=f"sq_{index}",
        sub_query_text=sub_query,
        expansion=expansion,
        top_k=5,
    )
    rerank_results.append(rerank_service.rerank_sub_query(retrieval_result))

context_result = context_builder.build_context(tuple(rerank_results))
citation_result = citation_service.build_citations(context_result)
answer_result = answer_service.generate_answer(
    question=question,
    context_result=context_result,
    citation_result=citation_result,
)

print(answer_result.answer, answer_result.confidence, len(answer_result.sources))
```

Minimal unified QA orchestration example:

```python
from mindwiki.application.qa_orchestration_service import build_qa_orchestration_service
from mindwiki.application.retrieval_models import QARequest

service = build_qa_orchestration_service()
result = service.ask(
    QARequest(
        question="分别总结 Step 8 和 Step 9 的职责",
        top_k=5,
    )
)

print(result.answer_result.answer)
print(result.answer_result.confidence)
print([source.citation_id for source in result.answer_result.sources])
```

Minimal CLI QA example:

```bash
PYTHONPATH=src python3 -m mindwiki ask "分别总结 Step 8 和 Step 9 的职责"
```

Local Step 10 QA answer generation verification command:

```bash
PYTHONPATH=src /opt/miniconda3/bin/python3 scripts/verify_local_step10_answer_generation.py
```

PostgreSQL persistence setup:

```bash
cp .env.example .env
# edit .env and set your real username/password/database
export MINDWIKI_DATABASE_URL='postgresql://user:password@localhost:5432/mindwiki'
/Library/PostgreSQL/16/bin/psql 'postgresql://user:password@localhost:5432/postgres' -c 'CREATE DATABASE mindwiki;'
/Library/PostgreSQL/16/bin/psql "$MINDWIKI_DATABASE_URL" -f scripts/init_local_db.sql
PYTHONPATH=src python3 -m mindwiki import file ./notes/example.md
```

`Milvus` setup for import-time vector sync:

```bash
export LLM_EMBEDDING_BASE_URL='https://api.siliconflow.cn/v1'
export LLM_EMBEDDING_API_KEY='your-embedding-api-key'
export LLM_EMBEDDING_MODEL_ID='Qwen/Qwen3-Embedding-8B'
export SYSTEM_MEMORY_MILVUS_URI='http://127.0.0.1:19530'
export MILVUS_COLLECTION_NAME='mindwiki_chunks'
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
PYTHONPATH=src python3 scripts/verify_local_llm.py
PYTHONPATH=src python3 scripts/verify_local_retrieval.py
PYTHONPATH=src python3 scripts/verify_local_vector_retrieval.py
PYTHONPATH=src python3 scripts/verify_local_hybrid_retrieval.py
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
- verify `success_jobs`, `failed_jobs`, and `executed_skipped_jobs`
- query child jobs for the generated `batch_job_id`
- verify the parent directory job payload contains `execution_summary`
- verify that the PDF child job is executed through the real PDF import path

The LLM verification script will:

- read `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL_ID` from `.env` or the shell
- run one real `generate_text` smoke test against the configured gateway
- expect the exact response `MINDWIKI_LLM_OK`
- print a JSON summary including `status`, `model`, `usage`, and normalized `error` fields

The Step 10 answer-generation verification script will:

- import one Markdown sample covering `Step 8 / Step 9 / Step 10`
- run the real `Step 09` orchestration chain through:
  - query decomposition
  - fixed query expansion
  - per-sub-query retrieval
  - rerank
  - context builder
  - citation payload
- run one real `Step 10` structured QA answer generation call against the current local knowledge base
- accept either:
  - a grounded cited answer
  - a standardized no-answer result when the current knowledge base evidence is insufficient or conflicting
- run one isolated real `Step 10` QA generation call against an in-script evidence fixture
- verify the isolated answer returns stable structured output
- if the isolated answer is a grounded cited answer, verify citation sources are returned
- if the gateway conservatively refuses under the current prompt and schema, accept a standardized no-answer result
- verify the local empty-context fallback still returns a low-confidence no-answer result

The retrieval verification script will:

- import one tagged Markdown sample into PostgreSQL
- run one broad `bm25_only` retrieval query
- run one filtered retrieval query with `tags`, `source_types`, `document_scope`, and `time_range`
- verify that the imported document can be retrieved under both query shapes
- print a JSON summary including top hit, `match_sources`, and `score_breakdown`

The vector retrieval verification script will:

- import one tagged Markdown sample with import-time embedding generation enabled
- run one broad `vector_only` retrieval query
- run one filtered `vector_only` retrieval query with `tags`, `source_types`, `document_scope`, and `time_range`
- verify that the imported document can be retrieved under both query shapes
- verify that `match_sources = ("vector",)` and `score_breakdown` includes `vector_score`
- print a JSON summary including top hit and vector score details

The hybrid retrieval verification script will:

- import one tagged Markdown sample with import-time embedding generation enabled
- run one broad `hybrid` retrieval query
- run one filtered `hybrid` retrieval query with `tags`, `source_types`, `document_scope`, and `time_range`
- verify that the imported document can be retrieved under both query shapes
- verify that `score_breakdown` includes:
  - `vector_score`
  - `bm25_score`
  - `rrf_score`
  - `final_score`
- print a JSON summary including top hit, merged `match_sources`, and fusion score details

Current status conventions:

- `import_jobs.status`: `pending`, `running`, `success`, `failed`, `skipped`, `cancelled`
- `documents.status`: `active`, `failed`, `deleted`
