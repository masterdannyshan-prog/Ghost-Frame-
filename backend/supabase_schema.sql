-- ═══════════════════════════════════════════════════════
--  Ghost Frame — Supabase Schema
--  Run this entire file in: Supabase Dashboard → SQL Editor
-- ═══════════════════════════════════════════════════════

-- ── Profiles ────────────────────────────────────────────
create table if not exists public.profiles (
  id            uuid references auth.users(id) on delete cascade primary key,
  username      text unique,
  display_name  text,
  avatar_url    text,
  bio           text,
  created_at    timestamptz default now()
);

-- Auto-create profile on new signup
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email,'@',1)));
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();


-- ── Projects ─────────────────────────────────────────────
create table if not exists public.projects (
  id            uuid default gen_random_uuid() primary key,
  user_id       uuid references auth.users(id) on delete cascade not null,
  title         text not null default 'Untitled',
  effect_used   text,
  original_url  text,
  result_url    text not null,
  thumbnail_url text,
  is_public     boolean default false,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

create index if not exists idx_projects_user_id on public.projects(user_id);

-- Auto-update updated_at
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

drop trigger if exists projects_updated_at on public.projects;
create trigger projects_updated_at
  before update on public.projects
  for each row execute function public.set_updated_at();


-- ── Discover Posts ───────────────────────────────────────
create table if not exists public.discover_posts (
  id            uuid default gen_random_uuid() primary key,
  user_id       uuid references auth.users(id) on delete cascade not null,
  project_id    uuid references public.projects(id) on delete set null,
  title         text not null,
  description   text,
  tags          text[] default '{}',
  image_url     text not null,
  effect_used   text,
  likes_count   integer default 0,
  created_at    timestamptz default now()
);

create index if not exists idx_discover_user_id  on public.discover_posts(user_id);
create index if not exists idx_discover_tags     on public.discover_posts using gin(tags);
create index if not exists idx_discover_effect   on public.discover_posts(effect_used);


-- ── Discover Likes ───────────────────────────────────────
create table if not exists public.discover_likes (
  id        uuid default gen_random_uuid() primary key,
  user_id   uuid references auth.users(id) on delete cascade not null,
  post_id   uuid references public.discover_posts(id) on delete cascade not null,
  created_at timestamptz default now(),
  unique(user_id, post_id)
);


-- ── Processing Jobs ──────────────────────────────────────
create table if not exists public.processing_jobs (
  id            uuid default gen_random_uuid() primary key,
  user_id       uuid references auth.users(id) on delete set null,
  status        text default 'pending'
                  check (status in ('pending','processing','done','failed')),
  effect        text not null,
  input_path    text,
  output_path   text,
  error_message text,
  metadata      jsonb default '{}',
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

drop trigger if exists jobs_updated_at on public.processing_jobs;
create trigger jobs_updated_at
  before update on public.processing_jobs
  for each row execute function public.set_updated_at();


-- ── Helper RPCs for likes counter ────────────────────────
create or replace function public.increment_likes(post_id uuid)
returns void language sql security definer as $$
  update public.discover_posts
  set likes_count = likes_count + 1
  where id = post_id;
$$;

create or replace function public.decrement_likes(post_id uuid)
returns void language sql security definer as $$
  update public.discover_posts
  set likes_count = greatest(0, likes_count - 1)
  where id = post_id;
$$;


-- ═══════════════════════════════════════════════════════
--  Row Level Security
-- ═══════════════════════════════════════════════════════

alter table public.profiles          enable row level security;
alter table public.projects          enable row level security;
alter table public.discover_posts    enable row level security;
alter table public.discover_likes    enable row level security;
alter table public.processing_jobs   enable row level security;

-- Profiles
create policy "Profiles public read"   on public.profiles for select using (true);
create policy "Users update own"       on public.profiles for update using (auth.uid() = id);
create policy "Users insert own"       on public.profiles for insert with check (auth.uid() = id);

-- Projects (private by default)
create policy "Own projects"           on public.projects for select using (auth.uid() = user_id);
create policy "Create own project"     on public.projects for insert with check (auth.uid() = user_id);
create policy "Update own project"     on public.projects for update using (auth.uid() = user_id);
create policy "Delete own project"     on public.projects for delete using (auth.uid() = user_id);

-- Discover (public read)
create policy "Public discover read"   on public.discover_posts for select using (true);
create policy "Create own post"        on public.discover_posts for insert with check (auth.uid() = user_id);
create policy "Update own post"        on public.discover_posts for update using (auth.uid() = user_id);
create policy "Delete own post"        on public.discover_posts for delete using (auth.uid() = user_id);

-- Likes
create policy "Public likes read"      on public.discover_likes for select using (true);
create policy "Own likes"              on public.discover_likes for all using (auth.uid() = user_id);

-- Jobs (service role writes; users read own)
create policy "Read own jobs"          on public.processing_jobs for select using (auth.uid() = user_id or user_id is null);
create policy "Anyone create job"      on public.processing_jobs for insert with check (true);


-- ═══════════════════════════════════════════════════════
--  Storage Buckets
--  Create these in: Supabase Dashboard → Storage
--  OR uncomment and run if using service role
-- ═══════════════════════════════════════════════════════

-- insert into storage.buckets (id, name, public) values ('originals', 'originals', false) on conflict do nothing;
-- insert into storage.buckets (id, name, public) values ('results',   'results',   true)  on conflict do nothing;


-- ═══════════════════════════════════════════════════════
--  Storage RLS Policies (REQUIRED for frontend uploads)
--  Run this in Supabase Dashboard → SQL Editor
-- ═══════════════════════════════════════════════════════

-- Allow authenticated users to upload to their own folder in results bucket
create policy "Users upload own results"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'results'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- Allow public read of results (since bucket is public)
create policy "Public read results"
  on storage.objects for select
  using (bucket_id = 'results');

-- Allow users to delete their own results
create policy "Users delete own results"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'results'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );
