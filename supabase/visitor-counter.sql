-- Portfolio visitor counter for tep2234.github.io/website
-- ---------------------------------------------------------------------------
-- Run once, as the database owner (Supabase SQL editor), in a project that is
-- NOT a DALIguro database. Safe to re-run: every statement is idempotent.
--
-- What the public (anon) key can do after this script:
--   * call public.record_visit(uuid, text)  -> records one page view, returns totals
--   * call public.visit_stats()             -> returns totals only
-- Nothing else: the data lives in a private schema the API does not expose,
-- and the tables are unreadable and unwritable for anon/authenticated.
--
-- Counting rules
--   * page view: one per browser per page per 30 minutes (refreshes inside the
--     window are ignored)
--   * unique visitor: first time a random browser id is seen (an estimate:
--     one person on two devices, or with cleared storage, counts twice)
--   * at most 120 new page views per minute site-wide, and at most 30 new
--     browser ids per minute, to blunt scripted inflation
-- ---------------------------------------------------------------------------

create schema if not exists portfolio_analytics;
revoke all on schema portfolio_analytics from public, anon, authenticated;

-- One row per counted page view (no IP, no user agent, no personal data)
create table if not exists portfolio_analytics.page_views (
  id         bigint generated always as identity primary key,
  visitor_id uuid        not null,
  path       text        not null check (path ~ '^/[A-Za-z0-9/_.~-]{0,199}$'),
  viewed_at  timestamptz not null default now()
);
create index if not exists page_views_visitor_path_time on portfolio_analytics.page_views (visitor_id, path, viewed_at desc);
create index if not exists page_views_time on portfolio_analytics.page_views (viewed_at desc);

-- One row per browser id ever seen
create table if not exists portfolio_analytics.visitors (
  visitor_id uuid primary key,
  first_seen timestamptz not null default now()
);
create index if not exists visitors_first_seen on portfolio_analytics.visitors (first_seen desc);

-- Single-row running totals, so reading the counter is O(1)
create table if not exists portfolio_analytics.totals (
  id              smallint primary key default 1 check (id = 1),
  page_views      bigint      not null default 0 check (page_views >= 0),
  unique_visitors bigint      not null default 0 check (unique_visitors >= 0),
  since           timestamptz
);
insert into portfolio_analytics.totals (id) values (1) on conflict (id) do nothing;

alter table portfolio_analytics.page_views enable row level security;
alter table portfolio_analytics.visitors   enable row level security;
alter table portfolio_analytics.totals     enable row level security;
revoke all on all tables    in schema portfolio_analytics from public, anon, authenticated;
revoke all on all sequences in schema portfolio_analytics from public, anon, authenticated;

-- Read totals --------------------------------------------------------------
create or replace function public.visit_stats()
returns json
language sql
stable
security definer
set search_path = ''
set statement_timeout = '2s'
as $$
  select json_build_object(
    'page_views',      t.page_views,
    'unique_visitors', t.unique_visitors,
    'since',           t.since)
  from portfolio_analytics.totals t
  where t.id = 1;
$$;

-- Record one page view, then return totals ----------------------------------
create or replace function public.record_visit(p_visitor uuid, p_path text)
returns json
language plpgsql
volatile
security definer
set search_path = ''
set statement_timeout = '2s'
as $$
declare
  v_path text;
  v_new_visitor boolean := false;
begin
  -- Input validation: no id -> read only. Paths are normalised (query string
  -- and fragment removed) and anything unexpected is folded into '/'.
  if p_visitor is null then
    return public.visit_stats();
  end if;
  v_path := split_part(split_part(coalesce(p_path, '/'), '?', 1), '#', 1);
  if v_path !~ '^/[A-Za-z0-9/_.~-]{0,199}$' then
    v_path := '/';
  end if;

  -- Concurrency: serialise writers on the totals row. This makes the
  -- 30-minute check, the rate caps and the totals update one atomic step,
  -- so simultaneous requests can never double-count.
  perform 1 from portfolio_analytics.totals where id = 1 for update;

  -- Refresh guard: same browser + same page within 30 minutes is ignored
  if exists (
      select 1 from portfolio_analytics.page_views
      where visitor_id = p_visitor and path = v_path
        and viewed_at > now() - interval '30 minutes') then
    return public.visit_stats();
  end if;

  -- Abuse caps: site-wide page views per minute
  if (select count(*) from portfolio_analytics.page_views
      where viewed_at > now() - interval '1 minute') >= 120 then
    return public.visit_stats();
  end if;

  -- New browser id? (capped separately so random-id floods stay small)
  if not exists (select 1 from portfolio_analytics.visitors where visitor_id = p_visitor) then
    if (select count(*) from portfolio_analytics.visitors
        where first_seen > now() - interval '1 minute') >= 30 then
      return public.visit_stats();
    end if;
    insert into portfolio_analytics.visitors (visitor_id) values (p_visitor)
      on conflict (visitor_id) do nothing;
    v_new_visitor := found;
  end if;

  insert into portfolio_analytics.page_views (visitor_id, path) values (p_visitor, v_path);

  update portfolio_analytics.totals
     set page_views      = page_views + 1,
         unique_visitors = unique_visitors + case when v_new_visitor then 1 else 0 end,
         since           = coalesce(since, now())
   where id = 1;

  return public.visit_stats();
end;
$$;

-- Permissions: Supabase grants EXECUTE on new functions to anon and
-- authenticated by default; reset and grant only what the page needs.
revoke all on function public.visit_stats()              from public, anon, authenticated;
revoke all on function public.record_visit(uuid, text)   from public, anon, authenticated;
grant execute on function public.visit_stats()            to anon;
grant execute on function public.record_visit(uuid, text) to anon;

-- Optional housekeeping (run by hand, or schedule with pg_cron):
-- delete from portfolio_analytics.page_views where viewed_at < now() - interval '90 days';
-- Totals are kept in portfolio_analytics.totals, so pruning old rows does not change the counter.
