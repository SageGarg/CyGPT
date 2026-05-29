-- CyGPT — migrate the original username-keyed tables to the storage-optimized
-- integer-FK design (see db/schema.sql). Safe to run on a live project; it
-- preserves existing user rows. Run once in the Supabase SQL Editor.
--
-- conversations was keyed by text username; we rebuild it to reference the new
-- integer users.id. Existing conversations are NOT migrated (the old FK held a
-- username, not an id) — run this before users have real saved chats.

begin;

-- 1. Drop the old conversations table (it referenced users.username).
drop table if exists public.conversations;

-- 2. Add the compact surrogate key to users and promote it to primary key,
--    keeping username as a unique constraint.
alter table public.users add column if not exists id bigint generated always as identity;
alter table public.users drop constraint if exists users_pkey;
alter table public.users add primary key (id);
alter table public.users add constraint users_username_key unique (username);

-- 3. Recreate conversations linked to users.id.
create table public.conversations (
    id          uuid primary key default gen_random_uuid(),
    user_id     bigint not null references public.users(id) on delete cascade,
    title       text not null default 'New chat',
    messages    jsonb not null default '[]'::jsonb,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index if not exists conversations_user_id_updated_idx
    on public.conversations (user_id, updated_at desc);

alter table public.conversations enable row level security;

commit;
