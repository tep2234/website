#!/bin/bash
# Behavioural + security tests for supabase/visitor-counter.sql on local PostgreSQL 17.5
# Usage: PSQL="psql -h <host> -p <port> -U postgres -d <scratch db>" ./sql_tests.sh  (NEVER a production database)
P="${PSQL:-psql -h /tmp -p 55432 -U postgres -d vc} -Atq"
pass=0; fail=0
t(){ # name expected actual
  if [ "$2" == "$3" ]; then pass=$((pass+1)); echo "PASS  $1"; else fail=$((fail+1)); echo "FAIL  $1  expected=[$2] got=[$3]"; fi; }
reset(){ $P -c "truncate portfolio_analytics.page_views, portfolio_analytics.visitors; update portfolio_analytics.totals set page_views=0, unique_visitors=0, since=null"; }
anon(){ $P -c "set role anon; $1" 2>&1 | head -1; }
A=11111111-1111-4111-8111-111111111111; B=22222222-2222-4222-8222-222222222222

reset
t "empty stats readable by anon" '{"page_views" : 0, "unique_visitors" : 0, "since" : null}' "$(anon "select public.visit_stats()")"
r=$(anon "select public.record_visit('$A','/website/')::json->>'page_views'"); t "first visit counted (views=1)" 1 "$r"
t "first visit counted (uniques=1)" 1 "$(anon "select public.visit_stats()->>'unique_visitors'")"
t "since set on first record" t "$(anon "select (public.visit_stats()->>'since') is not null")"
for i in 1 2 3 4 5; do anon "select public.record_visit('$A','/website/')" >/dev/null; done
t "5 refreshes within 30 min ignored" 1 "$(anon "select public.visit_stats()->>'page_views'")"
anon "select public.record_visit('$A','/website/other')" >/dev/null
t "same browser, other page counts a view" 2 "$(anon "select public.visit_stats()->>'page_views'")"
t "...but not a new unique visitor" 1 "$(anon "select public.visit_stats()->>'unique_visitors'")"
anon "select public.record_visit('$B','/website/')" >/dev/null
t "second browser: views=3" 3 "$(anon "select public.visit_stats()->>'page_views'")"
t "second browser: uniques=2" 2 "$(anon "select public.visit_stats()->>'unique_visitors'")"
# age A's row beyond 30 min
$P -c "update portfolio_analytics.page_views set viewed_at=now()-interval '31 minutes' where visitor_id='$A' and path='/website/'"
anon "select public.record_visit('$A','/website/')" >/dev/null
t "return after 31 min counts again" 4 "$(anon "select public.visit_stats()->>'page_views'")"
t "...still same unique count" 2 "$(anon "select public.visit_stats()->>'unique_visitors'")"
$P -c "update portfolio_analytics.page_views set viewed_at=now()-interval '29 minutes' where visitor_id='$B'"
anon "select public.record_visit('$B','/website/')" >/dev/null
t "return after 29 min is ignored" 4 "$(anon "select public.visit_stats()->>'page_views'")"

echo "--- input validation"
t "null visitor = read only" 4 "$(anon "select public.record_visit(null,'/website/')->>'page_views'")"
t "invalid uuid rejected by type" "ERROR:  invalid input syntax for type uuid: \"not-a-uuid\"" "$(anon "select public.record_visit('not-a-uuid','/x')")"
C=33333333-3333-4333-8333-333333333333
anon "select public.record_visit('$C','/website/?utm=1#top')" >/dev/null
t "query/fragment stripped" "/website/" "$($P -c "select path from portfolio_analytics.page_views where visitor_id='$C'")"
D=44444444-4444-4444-8444-444444444444
anon "select public.record_visit('$D','<script>alert(1)</script>')" >/dev/null
t "hostile path folded to /" "/" "$($P -c "select path from portfolio_analytics.page_views where visitor_id='$D'")"
E=55555555-5555-4555-8555-555555555555
anon "select public.record_visit('$E', repeat('/a',5000))" >/dev/null
t "oversized path folded to /" "/" "$($P -c "select path from portfolio_analytics.page_views where visitor_id='$E'")"
F=66666666-6666-4666-8666-666666666666
anon "select public.record_visit('$F', null)" >/dev/null
t "null path stored as /" "/" "$($P -c "select path from portfolio_analytics.page_views where visitor_id='$F'")"
t "direct insert of bad path blocked by CHECK" "ERROR" "$($P -c "insert into portfolio_analytics.page_views(visitor_id,path) values ('$A','nope')" 2>&1 | head -1 | cut -c1-5)"

echo "--- permissions"
for q in "select * from portfolio_analytics.page_views" "select * from portfolio_analytics.visitors" "select * from portfolio_analytics.totals" \
         "insert into portfolio_analytics.page_views(visitor_id,path) values ('$A','/')" "update portfolio_analytics.totals set page_views=999999" \
         "delete from portfolio_analytics.page_views"; do
  t "anon denied: ${q:0:45}" "denied" "$(anon "$q" | grep -o 'permission denied' | head -1 | sed 's/permission denied/denied/')"
done
for q in "select public.visit_stats()" "select public.record_visit('$A','/')" "select * from portfolio_analytics.totals"; do
  t "authenticated denied: ${q:0:40}" "denied" "$($P -c "set role authenticated; $q" 2>&1 | grep -o 'permission denied' | head -1 | sed 's/permission denied/denied/')"
done
t "PUBLIC has no execute on record_visit" f "$($P -c "select has_function_privilege('public','public.record_visit(uuid,text)','execute')" 2>/dev/null || $P -c "select bool_or(grantee=0) from pg_proc p, aclexplode(p.proacl) where proname='record_visit'")"
t "functions are SECURITY DEFINER with empty search_path" "2" "$($P -c "select count(*) from pg_proc where proname in ('record_visit','visit_stats') and prosecdef and proconfig @> array['search_path=\"\"']")"
t "statement_timeout pinned on both functions" "2" "$($P -c "select count(*) from pg_proc where proname in ('record_visit','visit_stats') and proconfig @> array['statement_timeout=2s']")"
t "RLS enabled on all 3 tables" "3" "$($P -c "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where nspname='portfolio_analytics' and relkind='r' and relrowsecurity")"
t "schema usage denied to anon" f "$($P -c "select has_schema_privilege('anon','portfolio_analytics','usage')")"
t "search_path hijack: anon cannot create in public" "denied" "$(anon "create table public.site_visits_evil(x int)" | grep -o 'permission denied' | sed 's/permission denied/denied/')"

echo "--- abuse caps"
reset
$P -c "set role anon; select count(public.record_visit(gen_random_uuid(),'/website/')) from generate_series(1,200)" >/dev/null
t "new-browser cap: 200 random ids in 1 min -> 30 uniques" 30 "$(anon "select public.visit_stats()->>'unique_visitors'")"
reset
$P -c "insert into portfolio_analytics.visitors(visitor_id,first_seen) values ('$A', now()-interval '2 minutes')"
$P -c "set role anon; select count(public.record_visit('$A','/p'||g)) from generate_series(1,200) g" >/dev/null
# one known browser hitting 200 distinct pages: capped at 120/min site-wide (paths must be valid)
t "site-wide cap: 200 page hits in 1 min -> 120 views" 120 "$(anon "select public.visit_stats()->>'page_views'")"

echo "--- totals match raw rows (no drift)"
t "totals.page_views == count(page_views)" t "$($P -c "select (select page_views from portfolio_analytics.totals)=(select count(*) from portfolio_analytics.page_views)")"
echo "RESULT pass=$pass fail=$fail"
