-- Drop and recreate with uuid primary key
drop function if exists match_documents;
drop table if exists documents;

create extension if not exists "uuid-ossp";

create table documents (
    id uuid primary key default uuid_generate_v4(),
    content text,
    metadata jsonb,
    embedding vector(3072)
);

create or replace function match_documents (
    query_embedding vector(3072),
    match_count int default 4,
    filter jsonb default '{}'
)
returns table (
    id uuid,
    content text,
    metadata jsonb,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) as similarity
    from documents
    where documents.metadata @> filter
    order by documents.embedding <=> query_embedding
    limit match_count;
end;
$$;