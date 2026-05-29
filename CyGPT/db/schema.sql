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
