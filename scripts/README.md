# Scripts

This directory stores local development scripts.

Current scope:

- `init_local_db.sql`: initialize the local PostgreSQL schema for the ingestion MVP
  - now also prepares chunk embedding metadata columns used by import-time vector sync
- `reset_local_db.sql`: drop the local PostgreSQL schema objects for rebuilding
- `verify_local_import.py`: run a minimal end-to-end Markdown import verification against the local PostgreSQL database
- `verify_local_directory_import.py`: run a minimal end-to-end directory import verification against the local PostgreSQL database, including Markdown/PDF child job execution outcomes and parent job execution summary checks
- `verify_local_llm.py`: run a minimal end-to-end `generate_text` verification against the configured OpenAI-compatible LLM gateway
- `verify_local_retrieval.py`: run a minimal end-to-end `bm25_only` retrieval verification against the local PostgreSQL database
- `verify_local_vector_retrieval.py`: run a minimal end-to-end `vector_only` retrieval verification against the local PostgreSQL and Milvus setup
- `verify_local_hybrid_retrieval.py`: run a minimal end-to-end `hybrid` retrieval verification against the local PostgreSQL, embedding gateway, and Milvus setup
- `verify_local_step09_orchestration.py`: run a minimal end-to-end verification for `Step 09` front-half orchestration, including query decomposition, fixed query expansion, and per-sub-query four-route retrieval merge
- `verify_local_step09_full_orchestration.py`: run a minimal end-to-end verification for full `Step 09` orchestration, including query decomposition, fixed query expansion, per-sub-query retrieval, rerank, context builder, and citation payload
