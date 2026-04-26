# Scripts

This directory stores local development scripts.

Current scope:

- `init_local_db.sql`: initialize the local PostgreSQL schema for the ingestion MVP
- `reset_local_db.sql`: drop the local PostgreSQL schema objects for rebuilding
- `verify_local_import.py`: run a minimal end-to-end Markdown import verification against the local PostgreSQL database
