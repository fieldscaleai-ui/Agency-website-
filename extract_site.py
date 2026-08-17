from playwright.sync_api import sync_playwright
import json, os, re, hashlib, urllib.request, urllib.error
from urllib.parse import urlparse

TARGET_URL='https://field-scale-flow.base44.app/#pricing'
OUT='clone-data'
os.makedirs(f'{OUT}/screenshots', exist_ok=True)
os.makedirs(f'{OUT}/components', exist_ok=True)
os.makedirs(f'{OUT}/assets', exist_ok=True)


def sanitize(s):
    return re.sub(r'[^a-z0-9._-]+','-',s.lower()).strip('-')[:60] or 'asset'

def file_ext(url, content_type=''):
    path=urlparse(url).path.lower()
    ext=os.path.splitext(path)[1]
    if ext in {'.png','.jpg','.jpeg','.webp','.gif','.svg','.avif','.ico','.woff','.woff2','.ttf','.otf','.mp4','.webm','.mov'}: return ext
    if 'svg' in content_type: return '.svg'
    if 'png' in content_type: return '.png'
    if 'jpeg' in content_type: return '.jpg'
    if 'webp' in content_type: return '.webp'
    if 'woff2' in content_type: return '.woff2'
    if 'woff' in content_type: return '.woff'
    if 'mp4' in content_type: return '.mp4'
    return '.bin'

def download(url, filepath):
    try:
        req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Accept':'*/*'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data=r.read()
            if len(data)<50: return False
            open(filepath,'wb').write(data)
            return True
    except Exception as e:
        print('DOWNLOAD_FAIL', url, str(e)[:120])
        return False

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, args=['--no-sandbox','--disable-setuid-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':900}, device_scale_factor=1)
    page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=60000)
    page.wait_for_timeout(5000)
    for _ in range(20):
        page.evaluate('window.scrollBy(0,500)')
        page.wait_for_timeout(350)
    page.evaluate('window.scrollTo(0,0)')
    page.wait_for_timeout(1500)
    raw=page.content()
    open(f'{OUT}/raw.html','w',encoding='utf-8').write(raw)
    page.screenshot(path=f'{OUT}/screenshots/desktop-full.png', full_page=True)
    page.screenshot(path=f'{OUT}/screenshots/header.png', clip={'x':0,'y':0,'width':1440,'height':180})
    for width,height,name in [(768,1024,'tablet'),(390,844,'mobile')]:
        page.set_viewport_size({'width':width,'height':height})
        page.wait_for_timeout(1000)
        page.screenshot(path=f'{OUT}/screenshots/{name}-full.png', full_page=True)
    page.set_viewport_size({'width':1440,'height':900})
    page.wait_for_timeout(500)

    inventory=page.evaluate('''() => {
      const main=document.querySelector('main')||document.body; const out=[];
      const header=document.querySelector('header');
      if(header) out.push({index:0,type:'header',selector:'header',tag:'header',classes:String(header.className||''),headings:[],buttons:[...header.querySelectorAll('button,a')].map(x=>x.innerText.trim()).filter(Boolean).slice(0,20),imageCount:header.querySelectorAll('img').length,textPreview:header.innerText.trim().slice(0,500),height:Math.round(header.getBoundingClientRect().height)});
      const children=[...main.children].filter(c=>!['HEADER','FOOTER','NAV','SCRIPT','STYLE','NOSCRIPT'].includes(c.tagName));
      children.forEach((child,idx)=>{const r=child.getBoundingClientRect(),cs=getComputedStyle(child); if(r.height<10||cs.display==='none')return; const headings=[...child.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(x=>x.innerText.trim()).filter(Boolean); const buttons=[...child.querySelectorAll('button,[role=button],a')].map(x=>x.innerText.trim()).filter(Boolean).slice(0,30); const imgs=[...child.querySelectorAll('img')]; out.push({index:idx+1,type:'section',selector:child.id?'#'+child.id:child.tagName.toLowerCase()+'.'+String(child.className||'').split(' ')[0],tag:child.tagName.toLowerCase(),classes:String(child.className||''),headings,buttons,imageCount:imgs.length,textPreview:child.innerText.trim().slice(0,1000),layout:cs.display,height:Math.round(r.height)});});
      const footer=document.querySelector('footer'); if(footer) out.push({index:999,type:'footer',selector:'footer',tag:'footer',classes:String(footer.className||''),headings:[...footer.querySelectorAll('h1,h2,h3,h4,strong')].map(x=>x.innerText.trim()).filter(Boolean),buttons:[],imageCount:footer.querySelectorAll('img').length,textPreview:footer.innerText.trim().slice(0,1000),height:Math.round(footer.getBoundingClientRect().height)}); return out;
    }''')
    json.dump(inventory,open(f'{OUT}/inventory.json','w'),indent=2)

    tokens=page.evaluate('''() => {
      const styles=e=>{if(!e)return null; const s=getComputedStyle(e); return {fontSize:s.fontSize,fontWeight:s.fontWeight,fontFamily:s.fontFamily,lineHeight:s.lineHeight,letterSpacing:s.letterSpacing,color:s.color,textTransform:s.textTransform,textAlign:s.textAlign,backgroundColor:s.backgroundColor,padding:s.padding,borderRadius:s.borderRadius,border:s.border,boxShadow:s.boxShadow};};
      const cssVars=[]; for(const sheet of document.styleSheets){try{for(const rule of sheet.cssRules){if(rule.selectorText&&rule.selectorText.includes(':root')) for(const prop of rule.style) if(prop.startsWith('--')) cssVars.push([prop,rule.style.getPropertyValue(prop).trim()]);}}catch(e){}}
      const allFonts=[]; for(const sheet of document.styleSheets){try{for(const rule of sheet.cssRules){if(rule instanceof CSSFontFaceRule) allFonts.push({family:rule.style.fontFamily,src:rule.style.src,weight:rule.style.fontWeight||'400',style:rule.style.fontStyle||'normal'});}}catch(e){}}
      const body=document.body; return {title:document.title,lang:document.documentElement.lang,body:styles(body),h1:styles(document.querySelector('h1')),h2:styles(document.querySelector('h2')),h3:styles(document.querySelector('h3')),button:styles(document.querySelector('button,a')),cssVars,fonts:[...document.querySelectorAll('link[href]')].map(x=>x.href).filter(x=>/font|woff|typekit/i.test(x)),fontFaces:allFonts,links:[...document.querySelectorAll('link[rel*=icon]')].map(x=>x.href)};
    }''')
    json.dump(tokens,open(f'{OUT}/tokens.json','w'),indent=2)

    header=page.evaluate('''() => { const h=document.querySelector('header'); if(!h)return null; const r=h.getBoundingClientRect(); const logo=h.querySelector('svg,[class*=logo] img,[class*=logo]'); const lr=logo?.getBoundingClientRect(); return {text:h.innerText.trim(),classes:String(h.className||''),rect:{x:r.x,y:r.y,w:r.width,h:r.height},logo:logo?{tag:logo.tagName,html:logo.outerHTML.slice(0,6000),rect:lr&&{x:lr.x,y:lr.y,w:lr.width,h:lr.height}}:null,links:[...h.querySelectorAll('a')].map(a=>({text:a.innerText.trim(),href:a.href})).filter(x=>x.text),buttons:[...h.querySelectorAll('button')].map(b=>b.innerText.trim()).filter(Boolean)}; }''')
    json.dump(header,open(f'{OUT}/header.json','w'),indent=2)

    footer=page.evaluate('''() => {const f=document.querySelector('footer'); return f?{text:f.innerText.trim(),bg:getComputedStyle(f).backgroundColor,links:[...f.querySelectorAll('a')].map(a=>({text:a.innerText.trim(),href:a.href})).filter(x=>x.text)}:null}''')
    json.dump(footer,open(f'{OUT}/footer.json','w'),indent=2)

    assets=page.evaluate('''() => ({
      images:[...document.querySelectorAll('img')].filter(i=>i.src).map(i=>({src:i.src,srcset:i.srcset,alt:i.alt,w:i.naturalWidth,h:i.naturalHeight,displayW:i.offsetWidth,displayH:i.offsetHeight})),
      videos:[...document.querySelectorAll('video')].map(v=>({src:v.currentSrc||v.src,poster:v.poster})).filter(x=>x.src||x.poster),
      backgrounds:[...document.querySelectorAll('*')].map(e=>({url:getComputedStyle(e).backgroundImage,tag:e.tagName,cls:String(e.className||'').slice(0,100)})).filter(x=>x.url&&x.url!=='none'&&x.url.includes('url(')),
      svgs:[...document.querySelectorAll('svg')].map((s,i)=>({i,viewBox:s.getAttribute('viewBox'),html:s.outerHTML.length<10000?s.outerHTML:'[TOO_LARGE]',parentText:s.parentElement?.innerText?.trim().slice(0,80)})),
      sources:[...document.querySelectorAll('source')].map(s=>s.src).filter(Boolean)
    })''')
    json.dump(assets,open(f'{OUT}/assets.json','w'),indent=2)

    # Capture selected component styles, raw outerHTML, and section screenshots
    els=page.locator('main > *, body > *')
    for i in range(min(40,els.count())):
        el=els.nth(i)
        try:
            if el.bounding_box() and el.bounding_box()['height']>20:
                el.scroll_into_view_if_needed(); page.wait_for_timeout(200)
                el.screenshot(path=f'{OUT}/screenshots/section-{i:02d}.png')
        except Exception: pass
    page.evaluate('window.scrollTo(0,0)')

    # Download page assets to clone-data/assets
    urls=[]
    for im in assets['images']:
        if im['src'] and not im['src'].startswith('data:'): urls.append(('image',im['src'],im.get('alt','img')))
        if im.get('srcset'):
            for part in im['srcset'].split(','):
                u=part.strip().split(' ')[0]
                if u and not u.startswith('data:'): urls.append(('image',u,im.get('alt','img')))
    for v in assets['videos']:
        if v.get('src'): urls.append(('video',v['src'],'video'))
        if v.get('poster'): urls.append(('image',v['poster'],'poster'))
    for b in assets['backgrounds']:
        for u in re.findall(r"""url\(["']?(.*?)["']?\)""", b['url']): urls.append(('image', u, 'background'))
    for s in assets['sources']: urls.append(('video',s,'source'))
    seen=set(); downloaded=[]
    for typ,url,label in urls:
        if not url or url in seen: continue
        seen.add(url)
        if url.startswith('//'): url='https:'+url
        if url.startswith('/'): url='https://field-scale-flow.base44.app'+url
        name=f"{sanitize(label)}-{hashlib.md5(url.encode()).hexdigest()[:10]}{file_ext(url)}"
        path=f'{OUT}/assets/{name}'
        if os.path.exists(path) or download(url,path):
            downloaded.append({'url':url,'path':path,'type':typ,'label':label})
    json.dump(downloaded,open(f'{OUT}/downloaded-assets.json','w'),indent=2)
    print(json.dumps({'rawChars':len(raw),'sections':len(inventory),'images':len(assets['images']),'videos':len(assets['videos']),'backgrounds':len(assets['backgrounds']),'svgs':len(assets['svgs']),'downloaded':len(downloaded),'title':tokens['title'],'lang':tokens['lang']},indent=2))
    browser.close()
