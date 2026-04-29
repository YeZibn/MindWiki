CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50) NOT NULL,
    source_uri TEXT,
    file_path TEXT,
    import_method VARCHAR(50),
    source_note TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_job_id UUID REFERENCES import_jobs (id),
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    input_path TEXT,
    input_payload TEXT,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources (id),
    import_job_id UUID REFERENCES import_jobs (id),
    title TEXT NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    content_hash VARCHAR(128),
    source_native_key TEXT,
    file_path TEXT,
    summary TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    imported_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_tags (
    document_id UUID NOT NULL REFERENCES documents (id),
    tag_id UUID NOT NULL REFERENCES tags (id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, tag_id)
);

CREATE TABLE IF NOT EXISTS sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents (id),
    parent_section_id UUID REFERENCES sections (id),
    title TEXT,
    level INTEGER NOT NULL DEFAULT 0,
    order_index INTEGER NOT NULL,
    start_offset INTEGER,
    end_offset INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents (id),
    section_id UUID REFERENCES sections (id),
    chunk_index INTEGER NOT NULL,
    content_text TEXT NOT NULL,
    token_count INTEGER,
    start_offset INTEGER,
    end_offset INTEGER,
    page_number INTEGER,
    embedding_ref TEXT,
    embedding_provider TEXT,
    embedding_model TEXT,
    embedding_version TEXT,
    embedding_dim INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

ALTER TABLE chunks
    ADD COLUMN IF NOT EXISTS embedding_ref TEXT,
    ADD COLUMN IF NOT EXISTS embedding_provider TEXT,
    ADD COLUMN IF NOT EXISTS embedding_model TEXT,
    ADD COLUMN IF NOT EXISTS embedding_version TEXT,
    ADD COLUMN IF NOT EXISTS embedding_dim INTEGER;

CREATE INDEX IF NOT EXISTS idx_sources_source_type
    ON sources (source_type);

CREATE INDEX IF NOT EXISTS idx_import_jobs_parent_job_id
    ON import_jobs (parent_job_id);

CREATE INDEX IF NOT EXISTS idx_import_jobs_status
    ON import_jobs (status);

CREATE INDEX IF NOT EXISTS idx_documents_source_id
    ON documents (source_id);

CREATE INDEX IF NOT EXISTS idx_documents_import_job_id
    ON documents (import_job_id);

CREATE INDEX IF NOT EXISTS idx_documents_status
    ON documents (status);

CREATE INDEX IF NOT EXISTS idx_tags_tag_name
    ON tags (tag_name);

CREATE INDEX IF NOT EXISTS idx_document_tags_document_id
    ON document_tags (document_id);

CREATE INDEX IF NOT EXISTS idx_document_tags_tag_id
    ON document_tags (tag_id);

CREATE INDEX IF NOT EXISTS idx_sections_document_id
    ON sections (document_id);

CREATE INDEX IF NOT EXISTS idx_sections_parent_section_id
    ON sections (parent_section_id);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id
    ON chunks (document_id);

CREATE INDEX IF NOT EXISTS idx_chunks_section_id
    ON chunks (section_id);

CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index
    ON chunks (chunk_index);
