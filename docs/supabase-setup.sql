-- ============================================================
-- JobFinder — Supabase schema
-- Run this once in: Supabase Dashboard → SQL Editor → New query
-- ============================================================

-- 1. User profiles ------------------------------------------------
create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  username text unique not null,
  full_name text,
  github_username text,
  roles jsonb not null default '[]',
  location text,
  profile_summary text,
  role text not null default 'user', -- 'user' | 'admin'
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Helper: is the current user an admin? (security definer avoids RLS recursion)
create or replace function public.is_admin()
returns boolean
language sql security definer stable
set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where user_id = auth.uid() and role = 'admin'
  );
$$;

alter table public.profiles enable row level security;

drop policy if exists "read own or admin" on public.profiles;
create policy "read own or admin" on public.profiles
  for select using (auth.uid() = user_id or public.is_admin());

drop policy if exists "update own" on public.profiles;
create policy "update own" on public.profiles
  for update using (auth.uid() = user_id);

drop policy if exists "insert own" on public.profiles;
create policy "insert own" on public.profiles
  for insert with check (auth.uid() = user_id);

-- Auto-create a profile row on signup (username comes from metadata)
create or replace function public.handle_new_user()
returns trigger
language plpgsql security definer
set search_path = public
as $$
begin
  insert into public.profiles (user_id, username)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'username', split_part(new.email, '@', 1))
  )
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 2. Usage analytics ----------------------------------------------
create table if not exists public.events (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) on delete set null,
  event text not null,
  meta jsonb not null default '{}',
  created_at timestamptz not null default now()
);

alter table public.events enable row level security;

drop policy if exists "anyone can log" on public.events;
create policy "anyone can log" on public.events
  for insert to anon, authenticated with check (true);

drop policy if exists "admin reads events" on public.events;
create policy "admin reads events" on public.events
  for select using (public.is_admin());

-- 3. Editable site content ----------------------------------------
create table if not exists public.site_content (
  key text primary key,           -- e.g. 'en:hero.title', 'he:hero.sub'
  value text not null,
  updated_at timestamptz not null default now()
);

alter table public.site_content enable row level security;

drop policy if exists "public read content" on public.site_content;
create policy "public read content" on public.site_content
  for select to anon, authenticated using (true);

drop policy if exists "admin writes content" on public.site_content;
create policy "admin writes content" on public.site_content
  for insert to authenticated with check (public.is_admin());

drop policy if exists "admin updates content" on public.site_content;
create policy "admin updates content" on public.site_content
  for update to authenticated using (public.is_admin());

drop policy if exists "admin deletes content" on public.site_content;
create policy "admin deletes content" on public.site_content
  for delete to authenticated using (public.is_admin());

-- ============================================================
-- AFTER RUNNING THIS FILE:
-- 1. Authentication → Sign In / Up → disable "Confirm email"
--    (signup uses username@users.jobfinder.local synthetic emails)
-- 2. Sign up once through the site, then make yourself admin:
--    update public.profiles set role = 'admin' where username = 'YOUR_USERNAME';
-- ============================================================
