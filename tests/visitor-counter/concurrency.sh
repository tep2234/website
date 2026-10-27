#!/bin/bash
# Usage: PSQL="psql -h <host> -p <port> -U postgres -d <scratch db>" ./concurrency.sh  (NEVER a production database)
P="${PSQL:-psql -h /tmp -p 55432 -U postgres -d vc} -Atq"
$P -c "truncate portfolio_analytics.page_views, portfolio_analytics.visitors; update portfolio_analytics.totals set page_views=0, unique_visitors=0, since=null"
A=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa
# 50 simultaneous refreshes from ONE browser on ONE page
for i in $(seq 50); do $P -c "set role anon; select public.record_visit('$A','/website/')" >/dev/null 2>>/tmp/conc.err & done; wait
r1=$($P -c "select page_views||'/'||unique_visitors from portfolio_analytics.totals")
# 25 simultaneous distinct browsers
for i in $(seq 25); do $P -c "set role anon; select public.record_visit(gen_random_uuid(),'/website/')" >/dev/null 2>>/tmp/conc.err & done; wait
r2=$($P -c "select page_views||'/'||unique_visitors||'/'||(select count(*) from portfolio_analytics.page_views)||'/'||(select count(*) from portfolio_analytics.visitors) from portfolio_analytics.totals")
echo "50 parallel same-browser refreshes -> views/uniques = $r1 (expect 1/1)"
echo "then 25 parallel new browsers -> views/uniques/rawViews/rawVisitors = $r2 (expect 26/26/26/26)"
echo "errors: $(wc -l < /tmp/conc.err)"
