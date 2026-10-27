-- Visitor counter for tep2234.github.io/website
-- Run once in the SQL editor of a Supabase project that is NOT the DALIguro database.
-- Anonymous visitors can only call the two functions below; they cannot read or write the table directly.

create table if not exists public.site_visits (
  id          bigint generated always as identity primary key,
  visitor_id  uuid        not null,                 -- random id kept in the visitor's browser, no personal data
  path        text        not null check (char_length(path) <= 200),
  visited_at  timestamptz not null default now()
);
create index if not exists site_visits_visitor_path_time on public.site_visits (visitor_id, path, visited_at desc);
create index if not exists site_visits_time on public.site_visits (visited_at desc);

alter table public.site_visits enable row level security;   -- no policies: direct table access is denied
revoke all on public.site_visits from anon, authenticated;

-- Totals only. Page views = recorded visits; unique visitors = distinct browser ids.
create or replace function public.visit_stats()
returns json
language sql
stable
security definer
set search_path = public
as $$
  select json_build_object(
    'page_views',      count(*),
    'unique_visitors', count(distinct visitor_id),
    'since',           min(visited_at)
  ) from public.site_visits;
$$;

-- Records one page view, then returns the totals.
-- A refresh within 30 minutes by the same browser on the same page is not counted again,
-- and the whole site accepts at most 120 new rows per minute to limit abuse.
create or replace function public.record_visit(p_visitor uuid, p_path text)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_path text := left(coalesce(nullif(trim(p_path), ''), '/'), 200);
begin
  if p_visitor is null then
    return public.visit_stats();
  end if;
  if not exists (
        select 1 from public.site_visits
        where visitor_id = p_visitor and path = v_path and visited_at > now() - interval '30 minutes')
     and (select count(*) from public.site_visits where visited_at > now() - interval '1 minute') < 120
  then
    insert into public.site_visits (visitor_id, path) values (p_visitor, v_path);
  end if;
  return public.visit_stats();
end;
$$;

revoke all on function public.visit_stats() from public;
revoke all on function public.record_visit(uuid, text) from public;
grant execute on function public.visit_stats() to anon;
grant execute on function public.record_visit(uuid, text) to anon;
