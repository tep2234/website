# Browser tests for the visitor counter: real PostgreSQL 17.5 + PostgREST behind the page, plus failure modes.
import asyncio, sys, subprocess, time, json, shutil, pathlib
from playwright.async_api import async_playwright
R=pathlib.Path('/home/claude/website'); JWT=open('/home/claude/pgrest/anon.jwt').read().strip()
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
FAKE='https://abcdefghijklmnopqrst.supabase.co'
site=pathlib.Path('/home/claude/qa/vcsite')
if site.exists(): shutil.rmtree(site)
shutil.copytree(R,site,ignore=shutil.ignore_patterns('.git','media','*.mp4','*.pdf'))
s=(site/'index.html').read_text(); assert 'var COUNTER={url:"",anonKey:""};' in s
(site/'index.html').write_text(s.replace('var COUNTER={url:"",anonKey:""};',f'var COUNTER={{url:"{FAKE}",anonKey:"{JWT}"}};'))
def psql(q): return subprocess.run(['psql','-h','/tmp','-p','55432','-U','postgres','-d','vc','-Atqc',q],capture_output=True,text=True).stdout.strip()
def totals(): return psql("select page_views||'/'||unique_visitors from portfolio_analytics.totals")
def reset(): psql("truncate portfolio_analytics.page_views, portfolio_analytics.visitors; update portfolio_analytics.totals set page_views=0, unique_visitors=0, since=null")
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'POST, OPTIONS'}
res=[]
def ok(n,c,i=""): res.append(bool(c)); print(("PASS " if c else "FAIL ")+n, i)
async def proxy(route):
    req=route.request
    if req.method=='OPTIONS': return await route.fulfill(status=204,headers=CORS)
    r=await route.fetch(url=req.url.replace(FAKE+'/rest/v1','http://localhost:3300'))
    await route.fulfill(response=r,headers={**r.headers,**CORS})
async def page(b,url='http://localhost:8798/index.html',handler=proxy,init='',ctx_kw={},storage_state=None,wait=900):
    ctx=await b.new_context(storage_state=storage_state,user_agent=UA,**ctx_kw); pg=await ctx.new_page(); reqs=[]; errs=[]
    await pg.add_init_script('Object.defineProperty(navigator,"webdriver",{get:()=>false});'+init)
    pg.on('request',lambda r: reqs.append((r.url,r.method,r.post_data)) if 'supabase.co' in r.url and r.method=='POST' else None)
    pg.on('pageerror',lambda e: errs.append(str(e)))
    await pg.route(FAKE+'/**',handler); await pg.goto(url); await pg.wait_for_timeout(wait)
    return ctx,pg,reqs,errs
async def txt(pg): return (await pg.inner_text('#stats')) if await pg.is_visible('#stats') else None
async def main():
    srv=subprocess.Popen([sys.executable,'-m','http.server','8798','-d',str(site)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    srv0=subprocess.Popen([sys.executable,'-m','http.server','8799','-d',str(R)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # 0. unconfigured (the real PR build): no request, hidden
        ctx,pg,reqs,errs=await page(b,'http://localhost:8799/index.html')
        ok('unconfigured build: no counter request', not reqs, reqs); ok('unconfigured build: footer counter hidden', await txt(pg) is None)
        ok('unconfigured build: no JS errors', not errs, errs); await ctx.close()
        # 1. first real visit records 1/1 and shows it
        reset(); ctx,pg,reqs,errs=await page(b)
        t=await txt(pg); ok('first visit recorded in DB (1/1)', totals()=='1/1', totals())
        ok('footer shows DB totals', t and '1 page view' in t and '1 estimated unique visitor' in t, t)
        ok('request was record_visit with uuid + path', reqs and reqs[0][0].endswith('/rpc/record_visit') and '"p_path":"/index.html"' in reqs[0][2], reqs[:1])
        state=await ctx.storage_state()
        # 2. refresh x5 same browser -> no increase (client guard + server guard)
        for i in range(5): await pg.reload(); await pg.wait_for_timeout(500)
        ok('5 refreshes do not inflate (still 1/1)', totals()=='1/1', totals()); ok('refresh still shows totals', '1 page view' in (await txt(pg) or ''))
        await ctx.close()
        # 3. client guard bypassed (localStorage timestamp cleared) -> server 30-min guard still holds
        ctx,pg,reqs,errs=await page(b,storage_state=state,init='try{Object.keys(localStorage).forEach(k=>k.startsWith("adm-visit:")&&localStorage.removeItem(k))}catch(e){}')
        ok('server-side 30-min guard holds when client guard bypassed', reqs and 'record_visit' in reqs[0][0] and totals()=='1/1', (totals(),reqs[:1]))
        await ctx.close()
        # 4. second browser -> 2/2
        ctx,pg,reqs,errs=await page(b); ok('second browser: 2 views / 2 uniques', totals()=='2/2', totals())
        ok('footer pluralises', 'page views' in (await txt(pg) or '') and 'visitors' in (await txt(pg) or ''), await txt(pg)); await ctx.close()
        # 5. same browser after 31 minutes -> new view, same unique
        psql("update portfolio_analytics.page_views set viewed_at=viewed_at-interval '31 minutes'")
        ctx,pg,reqs,errs=await page(b,storage_state=state,init='try{Object.keys(localStorage).forEach(k=>k.startsWith("adm-visit:")&&localStorage.setItem(k,String(Date.now()-31*60000)))}catch(e){}')
        ok('return after 31 min: +1 view, uniques unchanged (3/2)', totals()=='3/2', totals()); await ctx.close()
        # 6. Do Not Track / GPC -> read only
        before=totals(); ctx,pg,reqs,errs=await page(b,init='Object.defineProperty(navigator,"globalPrivacyControl",{get:()=>true})')
        ok('Global Privacy Control: stats only, nothing recorded', reqs and 'visit_stats' in reqs[0][0] and totals()==before and await txt(pg), (reqs[:1],totals())); await ctx.close()
        ctx,pg,reqs,errs=await page(b,init='Object.defineProperty(navigator,"doNotTrack",{get:()=>"1"})')
        ok('Do Not Track: stats only, nothing recorded', reqs and 'visit_stats' in reqs[0][0] and totals()==before, reqs[:1]); await ctx.close()
        # 7. automation (navigator.webdriver + HeadlessChrome UA) -> read only
        ctx=await b.new_context(); pg=await ctx.new_page(); rq=[]; pg.on('request',lambda r: rq.append(r.url) if 'supabase.co' in r.url and r.method=='POST' else None)
        await pg.route(FAKE+'/**',proxy); await pg.goto('http://localhost:8798/index.html'); await pg.wait_for_timeout(900)
        ok('automated browser: stats only', rq and 'visit_stats' in rq[0] and totals()==before, rq[:1]); await ctx.close()
        # 8. storage blocked -> read only
        ctx,pg,reqs,errs=await page(b,init='Object.defineProperty(window,"localStorage",{get(){throw new DOMException("blocked","SecurityError")}})')
        ok('storage blocked: stats only, no JS error', reqs and 'visit_stats' in reqs[0][0] and totals()==before and not errs, (reqs[:1],errs)); await ctx.close()
        # 9. tampered stored id -> replaced with valid uuid
        ctx,pg,reqs,errs=await page(b,init='if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem("adm-visitor","<script>")}')
        sent=json.loads(reqs[0][2]) if reqs and reqs[0][2] else {}
        ok('tampered browser id replaced by a valid v4 uuid', len(sent.get('p_visitor',''))==36 and sent['p_visitor'][14]=='4', sent); await ctx.close()
        # 10. background tab: not counted until visible
        before=totals()
        ctx,pg,reqs,errs=await page(b,init='Object.defineProperty(document,"visibilityState",{configurable:true,get:()=>window.__vis||"hidden"})')
        ok('hidden tab: no record yet', not reqs and totals()==before, reqs)
        await pg.evaluate('window.__vis="visible";document.dispatchEvent(new Event("visibilitychange"))'); await pg.wait_for_timeout(800)
        ok('hidden tab becomes visible: recorded once', len(reqs)==1 and 'record_visit' in reqs[0][0] and totals()!=before, (len(reqs),totals())); await ctx.close()
        # 11. failure modes -> hidden, no errors
        async def h500(r): await r.fulfill(status=500,body='x',headers=CORS)
        async def habort(r): await r.abort('connectionrefused')
        async def hhang(r): await asyncio.sleep(9); 
        def hjson(body):
            async def f(r): await r.fulfill(status=200,content_type='application/json',body=body,headers=CORS)
            return f
        async def h401(r): await r.fulfill(status=401,content_type='application/json',body='{"message":"Invalid API key"}',headers=CORS)
        cases=[('HTTP 500',h500,900),('network refused',habort,900),('invalid key 401',h401,900),('timeout (no reply in 6 s)',hhang,7000),
               ('non-JSON body',hjson('<html>'),900),('wrong types',hjson('{"page_views":"lots","unique_visitors":2}'),900),
               ('negative numbers',hjson('{"page_views":-5,"unique_visitors":1}'),900),('fractional numbers',hjson('{"page_views":2.5,"unique_visitors":1}'),900),
               ('uniques > views',hjson('{"page_views":3,"unique_visitors":9}'),900),('null body',hjson('null'),900),
               ('HTML injection in since',hjson('{"page_views":3,"unique_visitors":2,"since":"<img src=x onerror=alert(1)>"}'),900)]
        for name,hd,wait in cases:
            ctx,pg,reqs,errs=await page(b,handler=hd,wait=wait); t=await txt(pg)
            if name.startswith('HTML'):
                ok('since injection rendered as numbers only, no <img>', t and await pg.locator('#stats img').count()==0 and 'since' not in t, t)
            else:
                ok(f'{name}: counter hidden, no JS error', t is None and not errs, (t,errs))
            await ctx.close()
        await b.close()
    srv.terminate(); srv0.terminate()
    print(f"RESULT {sum(res)}/{len(res)} passed")
asyncio.run(main())
