-- Pega todo este archivo en Supabase → SQL Editor → New query y pulsa "Run".
-- Crea la tabla de tutoriales y la carpeta (bucket) donde se guardan los archivos.

create table if not exists public.videos (
  id          uuid primary key,
  titulo      text not null,
  descripcion text not null default '',
  categoria   text not null default 'General',
  archivo     text,
  url         text,
  miniatura   text,
  fecha       timestamptz not null default now()
);

-- Solo la app (con la clave secreta) puede leer y escribir la tabla.
alter table public.videos enable row level security;

-- Carpeta pública para videos y miniaturas (50 MB por archivo, máximo del plan gratuito).
insert into storage.buckets (id, name, public, file_size_limit)
values ('videoteca', 'videoteca', true, 52428800)
on conflict (id) do nothing;
