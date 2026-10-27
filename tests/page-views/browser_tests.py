# Browser tests for the footer page-view counter (Abacus). The Abacus API is simulated with Playwright routing,
# with one shared in-memory count so persistence across browsers can be checked. Run: python3 browser_tests.py <site dir>
import asyncio, sys, subprocess, time, json, pathlib
from playwright.async_api import async_playwright
SITE=sys.argv[1] if len(sys.argv)>1 else str(pathlib.Path(__file__).resolve().parents[2])
API='https://abacus.jasoncameron.dev'; PATH='/tep2234-website/pageviews'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
AXE=pathlib.Path('/home/claude/pdfwork/node_modules/axe-core/axe.min.js')
CORS={'access-control-allow-origin':'*'}
state={'value':0,'log':[]}
res=[]
def ok(n,c,i=""): res.append(bool(c)); print(("PASS " if c else "FAIL ")+n, i if not c else "")
async def service(route):
    u=route.request.url; state['log'].append(u)
    if u==API+'/hit'+PATH: state['value']+=1; return await route.fulfill(status=200,content_type='application/json',body=json.dumps({'value':state['value']}),headers=CORS)
    if u==API+'/get'+PATH:
        return await route.fulfill(status=200,content_type='application/json',body=json.dumps({'value':state['value']}),headers=CORS)
    await route.fulfill(status=404,body='{}',headers=CORS)
async def open_page(b,handler=service,init='',storage=None,wait=900,**kw):
    kw.setdefault('user_agent',UA)
    ctx=await b.new_context(storage_state=storage,**kw); pg=await ctx.new_page(); reqs=[]; errs=[]
    await pg.add_init_script('Object.defineProperty(navigator,"webdriver",{get:()=>false});'+init)
    pg.on('request',lambda r: reqs.append(r.url)); pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.on('console',lambda m: errs.append(m.text) if m.type=='error' and not m.text.startswith('Failed to load resource') else None)  # the browser's own network log line is not a page error
    await pg.route(API+'/**',handler); await pg.goto('http://localhost:8810/index.html'); await pg.wait_for_timeout(wait)
    return ctx,pg,reqs,errs
async def text(pg): return (await pg.inner_text('#stats')) if await pg.is_visible('#stats') else None
def api(reqs): return [u.replace(API,'') for u in reqs if u.startswith(API)]
async def main():
    srv=subprocess.Popen([sys.executable,'-m','http.server','8810','-d',SITE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # 0 counter exists at zero, read-only browser: genuine zero is shown
        ctx,pg,reqs,errs=await open_page(b,init='Object.defineProperty(navigator,"doNotTrack",{get:()=>"1"})'); t=await text(pg)
        ok('0. confirmed zero from the service is shown as "0 page views"', api(reqs)==['/get'+PATH] and t and '0 page views' in t, (api(reqs),t)); await ctx.close()
        # 1 real visit recording + display
        ctx,pg,reqs,errs=await open_page(b); t=await text(pg)
        ok('1. first visit sends one /hit', api(reqs)==['/hit'+PATH], api(reqs))
        ok('1. footer shows the service value', t and '1 page view' in t and 'visitor' not in t.lower().replace('site traffic',''), t)
        ok('1. no JS errors', not errs, errs)
        st=await ctx.storage_state()
        # 2 refresh behaviour
        for _ in range(5): await pg.reload(); await pg.wait_for_timeout(400)
        ok('2. 5 refreshes inside 30 min: no extra hits (value still 1)', state['value']==1 and api(reqs).count('/hit'+PATH)==1, (state['value'],api(reqs)))
        ok('2. refresh still shows the real total', '1 page view' in (await text(pg) or ''))
        await ctx.close()
        ctx,pg,reqs,errs=await open_page(b,storage=st,init='try{for(const k of Object.keys(localStorage))if(k.startsWith("adm-pv:"))localStorage.setItem(k,String(Date.now()-31*60000))}catch(e){}')
        ok('2. same browser after 31 min counts again (2)', api(reqs)==['/hit'+PATH] and state['value']==2, (api(reqs),state['value'])); await ctx.close()
        # 3 multiple browsers + 4 persistence
        for _ in range(3):
            ctx,pg,reqs,errs=await open_page(b); await ctx.close()
        ok('3. three new browsers add three views (5)', state['value']==5, state['value'])
        ctx,pg,reqs,errs=await open_page(b,storage=st)
        ok('4. returning browser reads the persisted shared total (5 page views)', api(reqs)==['/get'+PATH] and '5 page views' in (await text(pg) or ''), (api(reqs),await text(pg))); await ctx.close()
        # privacy / automation / storage: read only
        before=state['value']
        for name,init,kw in [('Do Not Track','Object.defineProperty(navigator,"doNotTrack",{get:()=>"1"})',{}),
                             ('Global Privacy Control','Object.defineProperty(navigator,"globalPrivacyControl",{get:()=>true})',{}),
                             ('storage blocked','Object.defineProperty(window,"localStorage",{get(){throw new DOMException("x","SecurityError")}})',{}),
                             ('headless user agent','',{'user_agent':'Mozilla/5.0 HeadlessChrome/130.0'})]:
            ctx,pg,reqs,errs=await open_page(b,init=init,**kw)
            ok(f'read-only for {name}: /get only, total shown, nothing added', api(reqs)==['/get'+PATH] and state['value']==before and await text(pg) and not errs, (api(reqs),errs)); await ctx.close()
        ctx=await b.new_context(); pg=await ctx.new_page(); rq=[]; pg.on('request',lambda r: rq.append(r.url))
        await pg.route(API+'/**',service); await pg.goto('http://localhost:8810/index.html'); await pg.wait_for_timeout(900)
        ok('read-only for navigator.webdriver automation', api(rq)==['/get'+PATH] and state['value']==before, api(rq)); await ctx.close()
        # hidden tab
        ctx,pg,reqs,errs=await open_page(b,init='Object.defineProperty(document,"visibilityState",{configurable:true,get:()=>window.__v||"hidden"})')
        ok('background tab: nothing sent while hidden', api(reqs)==[], api(reqs))
        await pg.evaluate('window.__v="visible";document.dispatchEvent(new Event("visibilitychange"))'); await pg.wait_for_timeout(700)
        ok('background tab: counted once when shown', api(reqs)==['/hit'+PATH] and state['value']==before+1, api(reqs)); await ctx.close()
        # 5 failure handling
        def fixed(status,body):
            async def f(r): await r.fulfill(status=status,content_type='application/json',body=body,headers=CORS)
            return f
        async def refused(r): await r.abort('connectionrefused')
        async def hang(r): await asyncio.sleep(8)
        cases=[('HTTP 500',fixed(500,'{"error":"x"}'),900),('HTTP 429 rate limit',fixed(429,'{"error":"x"}'),900),('404 key missing',fixed(404,'{"error":"Key not found"}'),900),
               ('network refused',refused,900),('no reply within 6 s',hang,7200),('non-JSON',fixed(200,'<html>'),900),('value as string',fixed(200,'{"value":"12"}'),900),
               ('negative value',fixed(200,'{"value":-4}'),900),('fractional value',fixed(200,'{"value":3.5}'),900),
               ('null body',fixed(200,'null'),900),('missing value',fixed(200,'{}'),900)]
        for name,h,w in cases:
            ctx,pg,reqs,errs=await open_page(b,handler=h,wait=w)
            ok(f'5. {name}: footer line hidden, no JS error', await text(pg) is None and not errs, (await text(pg),errs)); await ctx.close()
        # 8 network requests (unconfigured third parties none) + 9 performance
        ctx,pg,reqs,errs=await open_page(b)
        third=[u for u in reqs if not u.startswith('http://localhost') and not u.startswith('data:')]
        ok('8. only third-party request is the counter API', all(u.startswith(API+'/') for u in third) and len(third)==1, third)
        timing=await pg.evaluate('''(()=>{const n=performance.getEntriesByType("navigation")[0];const r=performance.getEntriesByType("resource").find(e=>e.name.includes("abacus"));return {htmlDone:Math.round(n.responseEnd),dcl:Math.round(n.domContentLoadedEventEnd),load:Math.round(n.loadEventEnd),start:r?Math.round(r.startTime):null}})()''')
        ok('9. counter request starts after the HTML arrived (one small GET, async)', timing['start'] is not None and timing['start']>=timing['htmlDone'], timing)
        await ctx.close()
        ctx,pg,reqs,errs=await open_page(b,handler=hang,wait=1500)
        t2=await pg.evaluate('(()=>{const n=performance.getEntriesByType("navigation")[0];return {dcl:Math.round(n.domContentLoadedEventEnd),load:Math.round(n.loadEventEnd)}})()')
        ok('9. a hung counter API does not delay page load (DOMContentLoaded within 100 ms of normal)', t2['dcl']<=timing['dcl']+100 and t2['load']>0, (timing,t2))
        await ctx.close()
        # 6 mobile + 7 accessibility, both themes, reduced motion
        for w,mob,scheme in [(390,True,'light'),(390,True,'dark'),(1440,False,'dark'),(1440,False,'light')]:
            ctx,pg,reqs,errs=await open_page(b,viewport={'width':w,'height':850},is_mobile=mob,has_touch=mob,color_scheme=scheme,reduced_motion='reduce')
            await pg.evaluate("document.querySelector('#stats').scrollIntoView()"); await pg.wait_for_timeout(300)
            over=await pg.evaluate('document.documentElement.scrollWidth>innerWidth')
            v=[]
            if AXE.exists():
                await pg.add_script_tag(content=AXE.read_text()); v=await pg.evaluate("axe.run('footer').then(r=>r.violations.map(x=>x.id))")
            ok(f'6/7. {w}px {scheme} reduced-motion: visible, no sideways scroll, axe clean', await text(pg) and not over and not v, (over,v))
            if w==390 and scheme=='dark': await pg.locator('footer').screenshot(path='/home/claude/qa/pv_footer_390_dark.png')
            await ctx.close()
        await b.close()
    srv.terminate(); print(f"RESULT {sum(res)}/{len(res)} passed")
asyncio.run(main())
