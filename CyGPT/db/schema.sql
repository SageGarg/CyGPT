-- CyGPT — Supabase schema (canonical, for a fresh project).
-- Run this once in your Supabase project (SQL Editor → New query → Run).
-- If you already created the older username-keyed tables, run
-- db/migrate_link_optimized.sql instead to upgrade in place.

-- ── Users ───────────────────────────────────────────────────────────────────
-- `id` is a compact surrogate key used for relationships (8 bytes), so child
-- rows don't repeat the variable-length username. `username` stays unique and
-- is what we look up at login.
create table if not exists public.users (
    id            bigint generated always as identity primary key,
    username      text not null unique,
    display_name  text not null,
    password_hash text not null,
    salt          text not null,
    created_at    timestamptz not null default now()
);

-- Server-side service_role only — no public policies (anon key can't read hashes).
alter table public.users enable row level security;


-- ── Per-user chat history ───────────────────────────────────────────────────
-- One row per conversation, linked to its owner by the integer user_id FK.
-- ON DELETE CASCADE removes a user's conversations when the user is deleted.
-- The full message list (rendered sources + follow-up suggestions) is stored
-- as a JSONB blob so a whole conversation loads/saves atomically; Postgres
-- TOAST-compresses large JSONB out of line automatically.
create table if not exists public.conversations (
    id          uuid primary key default gen_random_uuid(),
    user_id     bigint not null references public.users(id) on delete cascade,
    title       text not null default 'New chat',
    messages    jsonb not null default '[]'::jsonb,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Composite index: list one user's conversations, most-recently-updated first,
-- straight from the index without a separate sort.
create index if not exists conversations_user_id_updated_idx
    on public.conversations (user_id, updated_at desc);

alter table public.conversations enable row level security;
