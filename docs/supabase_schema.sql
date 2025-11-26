-- Core tables (subset to bootstrap)
create table if not exists users (
  id uuid primary key,
  email text unique not null,
  full_name text,
  role text check (role in ('admin','child','parent','standard')) not null,
  relationship text,
  image_limit_weekly integer default 0,
  created_at timestamp default now(),
  last_active timestamp
);

create table if not exists conversations (
  id uuid primary key,
  user_id uuid references users(id) on delete cascade,
  title text,
  knowledge_base_id uuid,
  created_at timestamp default now(),
  updated_at timestamp default now()
);

create table if not exists messages (
  id uuid primary key,
  conversation_id uuid references conversations(id) on delete cascade,
  user_id uuid references users(id) on delete cascade,
  role text check (role in ('user','assistant')) not null,
  content text not null,
  emotion text,
  attachments jsonb,
  tool_calls jsonb,
  created_at timestamp default now()
);

create table if not exists memory_entries (
  id uuid primary key,
  user_id uuid references users(id) on delete cascade,
  memory_type text check (memory_type in ('fact','preference','pattern','relationship','goal','correction')) not null,
  content text not null,
  context text,
  confidence_score numeric,
  importance_score numeric,
  access_count integer default 0,
  last_accessed timestamp,
  created_at timestamp default now(),
  archived_at timestamp
);

-- Enable RLS
alter table users enable row level security;
alter table conversations enable row level security;
alter table messages enable row level security;
alter table memory_entries enable row level security;

-- Policies (example)
create policy if not exists users_own_users on users
  for select using (auth.uid() = id);

create policy if not exists users_own_conversations on conversations
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy if not exists users_own_messages on messages
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy if not exists users_own_memory on memory_entries
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
