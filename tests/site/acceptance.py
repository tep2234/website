"""Portfolio acceptance tests (Chromium via Playwright). Run from the repo root:
    python3 tests/site/acceptance.py            (optional: AXE=/path/to/axe.min.js)
The page-view API is simulated (one shared count) so results never depend on, or change, the real counter."""
import asyncio, sys, os, subprocess, time, json, re, pathlib
from playwright.async_api import async_playwright
ROOT=str(pathlib.Path(__file__).resolve().parents[2]); PORT=8820; BASE=f'http://localhost:{PORT}/'
API='https://abacus.jasoncameron.dev'
AXE=os.environ.get('AXE','/home/claude/pdfwork/node_modules/axe-core/axe.min.js')
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
res=[]; count={'v':0}
def ok(group,name,cond,info=""):
    res.append((group,name,bool(cond),info)); print(("PASS " if cond else "FAIL ")+f'[{group}] {name}', "" if cond else info)
async def api(route):
    u=route.request.url
    if '/hit/' in u: count['v']+=1
    await route.fulfill(status=200,content_type='application/json',body=json.dumps({'value':count['v']}),headers={'access-control-allow-origin':'*'})
async def newpage(b,w=1440,h=850,scheme='light',mob=None,motion='no-preference'):
    mob=(w<768) if mob is None else mob
    # bypass_csp: the page's CSP (correctly) blocks the injected axe script; extras() tests the page WITH its CSP enforced
    ctx=await b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob,color_scheme=scheme,reduced_motion=motion,user_agent=UA,bypass_csp=True)
    pg=await ctx.new_page(); pg.errs=[]; pg.reqs=[]
    pg.on('pageerror',lambda e: pg.errs.append(str(e)))
    pg.on('console',lambda m: pg.errs.append(m.text) if m.type=='error' and not m.text.startswith('Failed to load resource') else None)
    pg.on('request',lambda r: pg.reqs.append(r.url))
    await pg.route(API+'/**',api)
    await pg.goto(BASE+'index.html'); await pg.wait_for_timeout(900)
    return ctx,pg

async def functional(b):
    G='function'
    ctx,pg=await newpage(b)
    # counter
    ok('counter','footer shows the service value',(await pg.is_visible('#stats')) and re.search(r'\d+ page views?',await pg.inner_text('#stats')),await pg.inner_text('#stats'))
    ok('counter','footer label is SITE TRAFFIC',(await pg.evaluate("getComputedStyle(document.querySelector('#stats .lbl')).textTransform"))=='uppercase' and (await pg.inner_text('#stats .lbl')).lower()=='site traffic')
    ok('counter','never says visitors', 'visitor' not in (await pg.inner_text('#stats')).lower())
    # icons: every <use href="#..."> points at a symbol
    miss=await pg.evaluate('[...document.querySelectorAll("use")].map(u=>u.getAttribute("href")).filter(h=>h&&h[0]==="#"&&!document.getElementById(h.slice(1)))')
    ok(G,'all SVG icon references resolve',not miss,sorted(set(miss)))
    # navigation
    tabs=await pg.eval_on_selector_all('#tabs a','e=>e.map(a=>a.getAttribute("href"))')
    ok(G,'section tabs point at real sections',tabs and await pg.evaluate('h=>h.every(x=>document.querySelector(x))',tabs),tabs)
    await pg.click('#tabs a[href="#contact"]')
    try: await pg.wait_for_function('Math.abs(document.querySelector("#contact").getBoundingClientRect().top)<300',timeout=4000); arrived=True
    except Exception: arrived=False
    ok(G,'tab click scrolls to section',arrived,await pg.evaluate('[scrollY,document.querySelector("#contact").getBoundingClientRect().top]'))
    await pg.keyboard.press('Control+k'); await pg.wait_for_timeout(200)
    ok(G,'Ctrl+K opens search',not await pg.evaluate('document.getElementById("pal").hidden'))
    await pg.fill('#pq','<img src=x onerror="window.__x1=1">sf9'); await pg.wait_for_timeout(300)
    ok('security','search box does not execute pasted HTML',not await pg.evaluate('window.__x1') and await pg.locator('#plist img').count()==0)
    await pg.fill('#pq','sf9'); await pg.wait_for_timeout(200)
    ok(G,'search finds SF9',await pg.locator('#plist li').count()>0 and 'SF9' in await pg.inner_text('#plist'))
    await pg.keyboard.press('Escape')
    # pathways
    await pg.click('#pathTabs [data-path="2"]'); t=await pg.inner_text('#pathBody h3'); ok(G,'pathway: hiring','recruiter' in t.lower(),t)
    await pg.click('#pathBody a[href="#contact"]'); await pg.wait_for_timeout(300)
    ok(G,'pathway CTA presets client type',await pg.input_value('#iClient')=='A recruiter or employer')
    # projects
    await pg.click('#pfilter [data-pc="business"]'); n=await pg.locator('#pgrid .pcard').count(); ok(G,'project filter: business',n==2,n)
    await pg.click('#pfilter [data-pc="education"]'); n2=await pg.locator('#pgrid .pcard').count(); ok(G,'project filter: education',n2==5,n2)
    await pg.click('#pfilter [data-pc="all"]'); n=await pg.locator('#pgrid .pcard').count(); ok(G,'project filter: all',n==7,n)
    for vid in ['daliguro-app','item-analysis','smart-attendance','sf9-master']:
        await pg.click(f'#pgrid [data-play="{vid}"] >> nth=0'); await pg.wait_for_timeout(500)
        src=await pg.evaluate('document.getElementById("vid").currentSrc')
        ok(G,f'project card plays {vid} recording',src.endswith(vid+'.mp4'),src)
    await pg.click('#pgrid [data-open="partsflow"]'); await pg.wait_for_timeout(350)
    ok(G,'project opens case file',await pg.inner_text('#dTitle')=='PartsFlow Pro')
    for _ in range(12): await pg.keyboard.press('Tab')
    ok('a11y','focus stays inside open case file',await pg.evaluate('document.getElementById("drawer").contains(document.activeElement)'))
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(250)
    ok('a11y','Esc closes case file',not await pg.evaluate('document.getElementById("drawer").classList.contains("on")'))
    # résumé hub: all 9 variants
    roles=await pg.locator('#cvRoles [data-cv]').count(); ok('resume','résumé hub lists 9 versions',roles==9,roles)
    bad=[]
    for i in range(roles):
        await pg.click(f'#cvRoles [data-cv="{i}"]'); await pg.wait_for_timeout(120)
        for sel,ct in [('#cvCard a[href$=".pdf"]','application/pdf'),('#cvCard a[href$=".docx"]','application/vnd.openxmlformats'),('#cvCard a[href$=".html"]','text/html')]:
            if await pg.locator(sel).count()==0: bad.append((i,sel,'missing')); continue
            href=await pg.get_attribute(sel+' >> nth=0','href'); r=await pg.request.get(BASE+href)
            if r.status!=200 or not r.headers.get('content-type','').startswith(ct): bad.append((i,href,r.status,r.headers.get('content-type')))
    ok('resume','every PDF, DOCX and HTML download link resolves (9 × 3)',not bad,bad[:4])
    # job matcher
    await pg.click('#jdSample'); await pg.wait_for_timeout(200); out=await pg.inner_text('#jdOut')
    ok('matcher','flags Power BI as not verified','BI tools' in out and 'no evidence' in out)
    ok('matcher','matches Excel and VBA','Excel and VBA' in out)
    ok('matcher','suggests a résumé version','version leads with' in out)
    ok('matcher','says it is not an ATS score','Not an ATS score' in out)
    samples={'instructional':"Instructional Designer\nRequirements:\n- Design e-learning modules and storyboards\n- Write assessments aligned to learning objectives\n- Experience with LMS platforms\n- Articulate Storyline or Rise 360\n- Strong written communication",
             'business':"Business Analyst\nRequirements:\n- Map business processes and workflows\n- Build Excel models and dashboards\n- Gather requirements from stakeholders\n- SQL for reporting\n- Tableau certification"}
    for k,jd in samples.items():
        await pg.fill('#jdText',jd); await pg.click('#jdCheck') if await pg.locator('#jdCheck').count() else await pg.click('#jdRun'); await pg.wait_for_timeout(250)
        o=await pg.inner_text('#jdOut')
        ok('matcher',f'{k} sample produces a result with unmatched items listed', re.search(r'\d+/\d+',o) and ('no evidence' in o or 'Not verified' in o), o[:160])
    await pg.fill('#jdText','<img src=x onerror="window.__x2=1"> needs Excel VBA automation and dashboards for school data, plus more lines here\n- Excel\n- <b>VBA</b>')
    await pg.click('#jdCheck') if await pg.locator('#jdCheck').count() else await pg.click('#jdRun'); await pg.wait_for_timeout(250)
    ok('security','matcher does not execute pasted HTML',not await pg.evaluate('window.__x2') and await pg.locator('#jdOut img').count()==0)
    # contact
    await pg.fill('#iName',''); await pg.click('#inq button[type=submit]'); m=await pg.inner_text('#inqOut')
    ok('contact','validation asks for missing fields','Please add' in m,m)
    ok('contact','never claims an inquiry was sent','sent' not in m.lower().replace("isn't sent",""),m)
    ok('contact','budget defaults to PHP',await pg.input_value('#iCur')=='PHP')
    o=await pg.eval_on_selector_all('#iBudget option','e=>e.map(x=>x.textContent)'); ok('contact','PHP ranges use ₱',len(o)==5 and all('₱' in x for x in o[1:]),o)
    await pg.select_option('#iCur','USD'); o2=await pg.eval_on_selector_all('#iBudget option','e=>e.map(x=>x.textContent)'); ok('contact','optional USD switches to US$',all('US$' in x for x in o2[1:]),o2)
    await pg.select_option('#iCur','PHP'); await pg.select_option('#iBudget',index=2)
    opts=lambda s: pg.eval_on_selector_all(s+' option','e=>e.map(x=>x.value||x.textContent)')
    ok('contact','client, service and timeline choices exist',len(await opts('#iClient'))>=3 and len(await opts('#iSvc') if await pg.locator('#iSvc').count() else await opts('#iService'))>=3 and len(await opts('#iTime') if await pg.locator('#iTime').count() else await opts('#iTimeline'))>=3)
    await pg.fill('#iName','QA Tester'); await pg.fill('#iMail','qa@example.com'); await pg.fill('#iMsg','Test inquiry body')
    await ctx.grant_permissions(['clipboard-read','clipboard-write'],origin=BASE[:-1])
    await pg.click('#inqCopy'); await pg.wait_for_timeout(200); clip=await pg.evaluate('navigator.clipboard.readText()')
    ok('contact','copy puts the full inquiry on the clipboard','QA Tester' in clip and 'Budget: ₱25,000 – ₱100,000 (PHP)' in clip, clip[:200])
    await pg.evaluate('''(()=>{window.__mail=null;const d=Object.getOwnPropertyDescriptor(Location.prototype,'href');})()''')
    mail=[]; pg.on('request',lambda r: mail.append(r.url) if r.url.startswith('mailto:') else None)
    await pg.route('mailto:*',lambda r: r.abort())
    pg.once('framenavigated',lambda f: mail.append(f.url))
    try:
        async with pg.expect_navigation(timeout=1500) as nav: await pg.click('#inq button[type=submit]')
    except Exception: pass
    msg=await pg.inner_text('#inqOut')
    ok('contact','submit opens the email app and says so (no "sent" claim)',('email' in msg.lower()) and 'sent' not in msg.lower().replace("isn't sent",""),msg)
    # theme
    before=await pg.evaluate('getComputedStyle(document.body).backgroundColor'); await pg.click('#themeBtn'); after=await pg.evaluate('getComputedStyle(document.body).backgroundColor')
    ok(G,'theme toggle switches palette',before!=after,f'{before} -> {after}')
    await pg.click('#themeBtn')
    # links
    missing=await pg.evaluate('[...document.querySelectorAll("a[href^=\'#\']")].map(a=>a.getAttribute("href")).filter(h=>h.length>1&&!document.getElementById(h.slice(1)))')
    ok(G,'in-page links resolve',not missing,missing[:5])
    locs=await pg.evaluate('[...new Set([...document.querySelectorAll("a[href],img[src],video[src],source[src],link[href]")].map(e=>e.getAttribute("href")||e.getAttribute("src")).filter(u=>u&&!/^(https?:|mailto:|#|data:)/.test(u)))]')
    bad=[u for u in locs if (await pg.request.get(BASE+u.split('#')[0])).status!=200]
    ok(G,f'local files resolve ({len(locs)})',not bad,bad[:5])
    ext=await pg.evaluate('[...document.querySelectorAll("a[href^=\'http\']")].filter(a=>!a.href.startsWith(location.origin)).map(a=>[a.href,a.target,a.rel])')
    ok('security','external links that open new tabs use rel=noopener',all(('noopener' in r or 'noreferrer' in r) for h,t,r in ext if t=='_blank'),[e for e in ext if e[1]=='_blank' and 'noopener' not in e[2]][:3])
    ok('security','all external links are https',all(h.startswith('https://') for h,t,r in ext),[h for h,t,r in ext if not h.startswith('https://')])
    third=sorted({re.sub(r'^(https?://[^/]+).*',r'\1',u) for u in pg.reqs if not u.startswith(BASE) and not u.startswith(('data:','mailto:'))})
    ok('network','third-party requests: only the counter API',third==[API],third)
    ok(G,'no JavaScript errors',not pg.errs,pg.errs[:3])
    # keyboard focus indicator
    await pg.goto(BASE+'index.html'); await pg.wait_for_timeout(500); seen=0; noring=[]
    for _ in range(15):
        await pg.keyboard.press('Tab')
        r=await pg.evaluate('(()=>{const e=document.activeElement;if(!e||e===document.body)return null;const s=getComputedStyle(e);return [e.tagName+(e.id?"#"+e.id:"")+"."+(e.className||""),s.outlineStyle!=="none"&&parseFloat(s.outlineWidth)>0||s.boxShadow!=="none"]})()')
        if r: seen+=1; (None if r[1] else noring.append(r[0]))
    ok('a11y','first 15 Tab stops show a visible focus indicator',seen>=10 and not noring,noring[:4])
    await ctx.close()

async def layout(b):
    axe=pathlib.Path(AXE).read_text() if pathlib.Path(AXE).exists() else None
    for w in [320,375,390,430,768,1024,1440,1920]:
        for scheme in (['light','dark'] if w in (320,390,1440) else ['light']):
            ctx,pg=await newpage(b,w=w,scheme=scheme,motion='reduce' if w in (390,1440) else 'no-preference')
            r=await pg.evaluate('''(()=>{
              const W=document.documentElement.clientWidth, over=document.documentElement.scrollWidth>W+1;
              const vis=e=>{const s=getComputedStyle(e);const r=e.getBoundingClientRect();return s.display!=="none"&&s.visibility!=="hidden"&&r.width>0&&r.height>0&&!e.closest("[hidden],dialog:not([open]),.pal[hidden]")};
              const inScroller=e=>{for(let p=e.parentElement;p&&p!==document.body;p=p.parentElement){const s=getComputedStyle(p);if(s.overflowX!=="visible"||s.position==="fixed")return true}return false};
              const wide=[...document.querySelectorAll("body *")].filter(e=>vis(e)&&!e.closest("svg")&&getComputedStyle(e).position!=="fixed").filter(e=>{const r=e.getBoundingClientRect();return r.right>W+1&&!inScroller(e)}).slice(0,4).map(e=>e.tagName+"."+e.className);
              const clip=[...document.querySelectorAll("h1,h2,h3")].filter(vis).filter(h=>h.scrollWidth>h.clientWidth+2&&getComputedStyle(h).overflow!=="visible").map(h=>h.textContent.slice(0,30));
              const small=[...document.querySelectorAll("p,li,dd,td")].filter(vis).filter(e=>parseFloat(getComputedStyle(e).fontSize)<12).length;
              const imgs=[...document.querySelectorAll("img")].filter(vis).filter(i=>i.naturalWidth&&Math.abs(i.getBoundingClientRect().width/i.getBoundingClientRect().height-i.naturalWidth/i.naturalHeight)>0.04&&getComputedStyle(i).objectFit==="fill").map(i=>i.src.split("/").pop());
              const tb=[...document.querySelectorAll("a,button,input,select,textarea,[role=tab]")].filter(vis).filter(e=>{const r=e.getBoundingClientRect();return r.width<24||r.height<24}).filter(e=>!e.closest("p,li")||e.tagName!=="A").map(e=>(e.id||e.textContent.trim().slice(0,18)||e.tagName)).slice(0,5);
              return {over,wide,clip,small,imgs,tb}})()''')
            tag=f'{w}px {scheme}'
            ok('layout',f'{tag}: no horizontal page overflow',not r['over'] and not r['wide'],r['wide'])
            ok('layout',f'{tag}: no clipped headings',not r['clip'],r['clip'])
            ok('layout',f'{tag}: body text ≥12px',r['small']==0,r['small'])
            ok('layout',f'{tag}: images keep proportions',not r['imgs'],r['imgs'])
            ok('a11y',f'{tag}: controls at least 24×24 px (WCAG 2.5.8)',not r['tb'],r['tb'])
            await pg.evaluate("document.querySelector('#stats').scrollIntoView()"); await pg.wait_for_timeout(250)
            box=await pg.evaluate('(()=>{const r=document.querySelector("#stats").getBoundingClientRect();return [r.left,r.right,innerWidth]})()')
            ok('counter',f'{tag}: footer counter visible and inside the viewport',await pg.is_visible('#stats') and box[0]>=0 and box[1]<=box[2],box)
            if w in (320,390,1440):
                await pg.screenshot(path=f'/tmp/qa-shot-{w}-{scheme}.png')
            if w<768:
                mn=await pg.evaluate('!!document.querySelector("#mnav")&&getComputedStyle(document.querySelector("#mnav")).display!=="none"')
                ok('layout',f'{tag}: mobile navigation present',mn)
            if axe:
                await pg.add_script_tag(content=axe)
                v=await pg.evaluate("axe.run(document,{runOnly:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}).then(r=>r.violations.map(v=>v.id+':'+v.nodes.length))")
                ok('a11y',f'{tag}: axe WCAG 2.2 AA, 0 violations',not v,v)
            await ctx.close()

async def perf(b):
    for w,label in [(1440,'desktop'),(390,'mobile')]:
        ctx=await b.new_context(viewport={'width':w,'height':850},is_mobile=w<768,user_agent=UA,bypass_csp=True); pg=await ctx.new_page(); await pg.route(API+'/**',api)
        cdp=await ctx.new_cdp_session(pg)
        if w<768:
            await cdp.send('Network.enable'); await cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':150,'downloadThroughput':1.6e6/8,'uploadThroughput':750e3/8})
            await cdp.send('Emulation.setCPUThrottlingRate',{'rate':4})
        await pg.add_init_script('''window.__cls=0;window.__lcp=0;new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.__cls+=e.value}).observe({type:"layout-shift",buffered:true});new PerformanceObserver(l=>{const e=l.getEntries();window.__lcp=e[e.length-1].startTime}).observe({type:"largest-contentful-paint",buffered:true});''')
        await pg.goto(BASE+'index.html',wait_until='load'); await pg.wait_for_timeout(2500)
        m=await pg.evaluate('''(()=>{const n=performance.getEntriesByType("navigation")[0];const rs=performance.getEntriesByType("resource");
          const by=t=>rs.filter(r=>r.initiatorType===t).reduce((a,r)=>a+(r.transferSize||0),0);
          const fcp=(performance.getEntriesByName("first-contentful-paint")[0]||{}).startTime;
          return {html_kb:Math.round(n.transferSize/1024),dcl_ms:Math.round(n.domContentLoadedEventEnd),load_ms:Math.round(n.loadEventEnd),fcp_ms:Math.round(fcp||0),lcp_ms:Math.round(window.__lcp),cls:+window.__cls.toFixed(3),
            requests:rs.length,img_kb:Math.round(by("img")/1024),video_kb:Math.round((by("video")+rs.filter(r=>/\\.mp4/.test(r.name)).reduce((a,r)=>a+(r.transferSize||0),0))/1024),font_kb:Math.round(rs.filter(r=>/\\.(woff2?|ttf)/.test(r.name)).reduce((a,r)=>a+(r.transferSize||0),0)/1024),
            total_kb:Math.round((n.transferSize+rs.reduce((a,r)=>a+(r.transferSize||0),0))/1024),
            videos_preload:[...document.querySelectorAll("video")].map(v=>v.preload+":"+(v.getAttribute("src")?"src":"nosrc")),
            lazy_imgs:[...document.querySelectorAll("img")].filter(i=>i.loading==="lazy").length,imgs:document.images.length,
            font_display:[...document.styleSheets].flatMap(s=>{try{return [...s.cssRules]}catch(e){return []}}).filter(r=>r.constructor.name==="CSSFontFaceRule"&&/url\\(/.test(r.style.src)).map(r=>r.style.fontDisplay)}})()''')
        tl=await cdp.send('Performance.getMetrics') if False else None
        print(f'PERF {label}{" (4x CPU, 1.6 Mbps, 150 ms)" if w<768 else " (no throttling)"}: '+json.dumps(m))
        ok('perf',f'{label}: CLS < 0.1',m['cls']<0.1,m['cls'])
        ok('perf',f'{label}: LCP < 2.5 s',m['lcp_ms']<2500,m['lcp_ms'])
        ok('perf',f'{label}: no video bytes before playback is requested',m['video_kb']<300,m['video_kb'])
        ok('perf',f'{label}: fonts use font-display swap/optional',all(f in('swap','optional','fallback') for f in m['font_display']),m['font_display'])
        await ctx.close()

async def extras(b):
    """Checks added with the Front-End Checklist fixes (CSP, fonts, images, video control, hint placement, 404)."""
    G='checklist'
    # 1. CSP enforced (no bypass): the page script still runs and nothing is blocked
    ctx=await b.new_context(viewport={'width':1440,'height':850},user_agent=UA); pg=await ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e: errs.append(str(e)))
    await pg.add_init_script('window.__csp=[];document.addEventListener("securitypolicyviolation",e=>window.__csp.push(e.violatedDirective+" "+e.blockedURI))')
    await pg.route(API+'/**',api); await pg.goto(BASE+'index.html'); await pg.wait_for_timeout(1200)
    ok('security','CSP meta tag present',await pg.evaluate('!!document.querySelector(\'meta[http-equiv="Content-Security-Policy"]\')'))
    ok('security','page script runs under the CSP',await pg.locator('#rig .folder').count()==6 and await pg.locator('#pgrid .pcard').count()>0)
    v=await pg.evaluate('window.__csp'); ok('security','no CSP violations on load',not v,v)
    ok('security','CSP script hash is current (tools/update-csp.py --check)',subprocess.run([sys.executable,os.path.join(ROOT,'tools','update-csp.py'),'--check'],capture_output=True).returncode==0)
    # 2. images: every <img> has width/height; large ones offer smaller copies that actually exist
    im=await pg.evaluate('[...document.images].map(i=>({s:i.getAttribute("src")||"",w:i.getAttribute("width"),h:i.getAttribute("height"),ss:i.getAttribute("srcset")||"",nw:i.naturalWidth}))')
    ok(G,'every <img> has width and height',all(i['w'] and i['h'] for i in im),[i['s'] for i in im if not(i['w'] and i['h'])])
    big=[i for i in im if i['s'].endswith('.webp') and ('/img/' in i['s'] or '-poster' in i['s']) and 'favicon' not in i['s']]
    ok(G,'content images have srcset',all(i['ss'] for i in big),[i['s'] for i in big if not i['ss']])
    files=sorted({u.split(' ')[0] for i in big for u in i['ss'].split(', ') if u})
    missing=[f for f in files if not os.path.exists(os.path.join(ROOT,f))]
    ok(G,'every srcset file exists',not missing,missing)
    # 3. fallback fonts are declared and used first in each stack
    fam=await pg.evaluate('["--body","--mono","--display"].map(v=>getComputedStyle(document.documentElement).getPropertyValue(v))')
    ok(G,'font stacks include metric-matched fallbacks',all('Fallback' in f.split(',')[1] for f in fam),fam)
    # 4. the inline recording has a working pause control
    await pg.locator('#ivid').scroll_into_view_if_needed(); await pg.wait_for_timeout(600)
    vis=await pg.is_visible('#ivBtn'); ok(G,'inline video has a visible pause/play control',vis)
    if vis:
        await pg.evaluate('document.getElementById("ivid").play().catch(()=>{})'); await pg.wait_for_timeout(300)
        await pg.click('#ivBtn'); await pg.wait_for_timeout(300)
        ok(G,'pause control pauses the inline video',await pg.evaluate('document.getElementById("ivid").paused'))
        ok(G,'pause control label reflects state',(await pg.get_attribute('#ivBtn','aria-label'))=='Play the recording')
    await ctx.close()
    # 5. "Pick a folder" hint sits clear of the ID card on narrow screens
    for w in [320,375,430,760,1024]:
        ctx,pg=await newpage(b,w=w)
        r=await pg.evaluate('(()=>{const h=document.querySelector(".cab-hint").getBoundingClientRect(),c=document.querySelector(".personnel").getBoundingClientRect();return [Math.round(h.bottom),Math.round(c.top)]})()')
        ok(G,f'{w}px: cabinet hint is above the ID card',r[0]<=r[1],r)
        await ctx.close()
    # 6. custom 404 page
    p404=pathlib.Path(ROOT,'404.html')
    t=p404.read_text() if p404.exists() else ''
    ok(G,'404.html exists and links home','href="/website/"' in t and '<h1>' in t)

async def main():
    srv=subprocess.Popen([sys.executable,'-m','http.server',str(PORT),'-d',ROOT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch()
            print('Browser:',b.version)
            await functional(b); await extras(b); await layout(b); await perf(b)
            await b.close()
    finally: srv.terminate()
    f=[r for r in res if not r[2]]
    print(f'\nTOTAL {len(res)-len(f)}/{len(res)} passed')
    for g,n,c,i in f: print('FAILED',g,n,i)
asyncio.run(main())
