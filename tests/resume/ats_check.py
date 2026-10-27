"""ATS checks for every résumé variant (PDF, DOCX, HTML) against resume/resume-data.json.
Run from the repo root: python3 tests/resume/ats_check.py   (needs pypdf and pandoc)"""
import json, re, subprocess, zipfile, html, os, sys
from pypdf import PdfReader
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P=lambda *a: os.path.join(ROOT,*a)
D=json.load(open(P('resume','resume-data.json'))); M=json.load(open(P('resume','manifest.json')))
norm=lambda s: re.sub(r'\s+',' ',s.replace('­','').replace('ﬁ','fi').replace('ﬂ','fl')).replace('- ','-').strip()
fails=[]; checks=0
def chk(cond,msg):
    global checks; checks+=1
    if not cond: fails.append(msg); print('  FAIL',msg)
chk(len(M)==9, f'expected 9 variants, manifest has {len(M)}')
for m in M:
    role=[r for r in D['roles'] if r['id']==m['id']][0]; print(m['id'])
    # filenames
    for k in ('pdf','docx'):
        chk(re.fullmatch(r'resume/Alvin-Diaz-Merasol-Resume(-[A-Za-z-]+)?\.'+k, m[k]) is not None, f'{m["id"]}: filename {m[k]}')
        chk(os.path.getsize(P(m[k]))>5000, f'{m["id"]}: {k} too small')
    pdf_r=PdfReader(P(m['pdf'])); pdf=norm(' '.join(p.extract_text() for p in pdf_r.pages))
    dx=norm(subprocess.run(['pandoc','-t','plain','--wrap=none',P(m['docx'])],capture_output=True,text=True).stdout)
    raw=open(P(m['html']),encoding='utf-8').read(); ht=norm(html.unescape(re.sub(r'<[^>]+>',' ',re.sub(r'<(script|style)[\s\S]*?</\1>','',raw))))
    for name,txt in [('pdf',pdf),('docx',dx),('html',ht)]:
        must=[D['name'],D['email'],role['headline'],role['summary'],'1385342','Filamer Christian University','Capiz State University','2017 – Present']
        must+=[b for e in D['experience'] for b in e['bullets']]+[e['title'] for e in D['experience']]+[D['skills'][k]['text'] for k in role['skills']]
        for s in must: chk(norm(s) in txt, f'{m["id"]} {name}: missing "{s[:60]}"')
        pos=[txt.find(D['skills'][k]['label']+':') for k in role['skills']]
        chk(all(p>=0 for p in pos) and pos==sorted(pos), f'{m["id"]} {name}: skill order')
        # reading order: name -> summary -> experience (in data order) -> education
        order=[txt.find(norm(D['name'])),txt.find(norm(role['summary'][:50]))]+[txt.find(norm(e['title'])) for e in D['experience']]+[txt.find('Filamer Christian University')]
        chk(all(o>=0 for o in order) and order==sorted(order), f'{m["id"]} {name}: reading order {order}')
        chk('�' not in txt, f'{m["id"]} {name}: replacement glyphs')
        for bad in ['Power BI','Articulate','Captivate','PMP','Certified','Python developer']:
            chk(bad not in txt, f'{m["id"]} {name}: unsupported claim "{bad}"')
    # PDF structure
    chk(len(pdf_r.pages)<=2, f'{m["id"]}: pdf pages {len(pdf_r.pages)}')
    chk(sum(len(p.images) for p in pdf_r.pages)==0, f'{m["id"]}: pdf has images')
    meta=pdf_r.metadata or {}
    chk(D['name'] in str(meta.get('/Author','')) or D['name'] in str(meta.get('/Title','')), f'{m["id"]}: pdf metadata lacks name {dict(meta)}')
    # single column: on page 1 no two text runs share a line while being far apart horizontally in the body
    xs=[]
    def v(t,cm,tm,fd,fs):
        if t.strip(): xs.append(round(tm[4]))
    pdf_r.pages[0].extract_text(visitor_text=v)
    left=min(xs) if xs else 0
    chk(len([x for x in xs if x>left+250])/max(len(xs),1)<0.15, f'{m["id"]}: pdf may be multi-column')
    # DOCX structure
    z=zipfile.ZipFile(P(m['docx'])); doc=z.read('word/document.xml').decode()
    chk('<w:tbl>' not in doc and '<w:txbxContent' not in doc and '<w:drawing' not in doc, f'{m["id"]}: docx table/textbox/image')
    chk('<w:numPr>' in doc or 'ListParagraph' in doc, f'{m["id"]}: docx bullets not real lists')
    chk(doc.count('w:val="Heading1"')==1 and doc.count('w:val="Heading2"')>=3, f'{m["id"]}: docx heading hierarchy')
    chk('<w:cols w:num="2"' not in doc, f'{m["id"]}: docx two columns')
    hdr=[n for n in z.namelist() if re.match(r'word/(header|footer)\d*\.xml',n)]
    chk(all(D['email'] not in z.read(n).decode() for n in hdr), f'{m["id"]}: contact details only in header/footer')
    # HTML structure
    chk(re.search(r'<html[^>]*lang="en"',raw) is not None, f'{m["id"]}: html lang')
    chk(len(re.findall(r'<h1[\s>]',raw))==1, f'{m["id"]}: html h1 count')
    chk(re.search(r'<h3[\s>]',raw) is None or re.search(r'<h2[\s>]',raw) is not None, f'{m["id"]}: heading levels skip')
# chronology: dated roles first, newest first
yrs=[int(re.match(r'(\d{4})',e['dates']).group(1)) for e in D['experience'] if re.match(r'\d{4}',e['dates'])]
chk(yrs==sorted(yrs), f'dated roles are not in a consistent order: {yrs}')
undated=[(e['title'],e['dates']) for e in D['experience'] if not re.match(r'\d{4}',e['dates'])]
print('\nNOTE roles without a year (ATS parsers may not read these as dates):', undated)
print(f'\n{checks-len(fails)}/{checks} checks passed')
sys.exit(1 if fails else 0)
