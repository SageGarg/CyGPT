-- CyGPT — Supabase user-accounts table.
-- Run this once in your Supabase project (SQL Editor → New query → Run).
-- Mirrors the original local SQLite schema in src/auth.py.

create table if not exists public.users (
    username      text primary key,
    display_name  text not null,
    password_hash text not null,
    salt          text not null,
    created_at    timestamptz not null default now()
);

-- The app talks to this table with the service_role key (server-side only),
-- so we keep Row Level Security ON and add NO public policies. This means the
-- anon/public key cannot read password hashes — only the trusted backend can.
alter table public.users enable row level security;


-- ── Per-user chat history ───────────────────────────────────────────────────
-- One row per conversation. The full message list (including rendered sources
-- and follow-up suggestions) is stored as a JSONB blob so a whole conversation
-- loads/saves atomically. Deleting a user cascades to their conversations.
create table if not exists public.conversations (
    id          uuid primary key default gen_random_uuid(),
    username    text not null references public.users(username) on delete cascade,
    title       text not null default 'New chat',
    messages    jsonb not null default '[]'::jsonb,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Fast lookup of a user's conversations, most-recently-updated first.
create index if not exists conversations_username_updated_idx
    on public.conversations (username, updated_at desc);

-- Same RLS posture as users: server-side service_role only, no public policies.
alter table public.conversations enable row level security;
