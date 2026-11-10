-- items.created label (dashboard shows it; old JSON field "created")
alter table public.items add column if not exists created_label text;
