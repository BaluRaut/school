#!/usr/bin/env python3
"""i18n tool for The School sites.
  extract <dict.json> <html...>   -> collect unique translatable units (en -> "") merging into dict.json
  apply   <dict.json> <html...>   -> rewrite pages: Marathi default, data-en holds English, + lang dropdown
  restore -           <html...>   -> strip the Marathi layer, put English back (clean page to edit)
  dump    <dict.json> <start> <count>   -> print untranslated units with ids
  merge   <dict.json> <batch.json...>   -> merge {id: mr} batches into dict.json
"""
import sys, json, re
from bs4 import BeautifulSoup, NavigableString

INLINE = {'b','i','em','strong','code','kbd','small','br','span','a','sup','sub','u','mark','tspan','abbr','input','wbr'}
SKIP_TAGS = {'script','style','pre','noscript','defs','marker','select','option'}

def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

def is_leaf(el):
    for c in el.children:
        if isinstance(c, NavigableString):
            continue
        if c.name in INLINE:
            if not is_leaf(c): return False
            continue
        return False
    return True

def worth(txt):
    t = norm(re.sub(r'<[^>]+>', '', txt))
    if not t: return False
    if re.fullmatch(r'[\W\d_]+', t): return False
    if len(t) < 2: return False
    return True

def units(soup):
    out = []
    def walk(el):
        if el.name in SKIP_TAGS: return
        if el.name not in INLINE and el.name not in ('body','html','head') and is_leaf(el):
            inner = el.decode_contents()
            if worth(inner):
                out.append(el)
            return
        for c in list(el.children):
            if isinstance(c, NavigableString): continue
            if c.name in INLINE and c.name not in ('br','input','wbr') and is_leaf(c):
                inner = c.decode_contents()
                if worth(inner): out.append(c)
                continue
            walk(c)
    walk(soup)
    return out

def key_of(el):
    return norm(el.decode_contents())

def strip_layer(soup):
    for el in soup.select('[data-en]'):
        el.clear(); el.append(BeautifulSoup(el['data-en'], 'html.parser')); del el['data-en']
        if el.has_attr('data-mr'): del el['data-mr']
    for el in soup.select('[data-en-ph]'):
        el['placeholder'] = el['data-en-ph']; del el['data-en-ph']
    for sid in ('i18n-js','i18n-css','lang-pick'):
        t = soup.find(id=sid)
        if t: t.decompose()
    soup.html['lang'] = 'en'

def load_soup(f):
    raw = open(f, encoding='utf-8').read()
    soup = BeautifulSoup(raw, 'html.parser')
    if 'id="i18n-js"' in raw:
        strip_layer(soup)
    return soup

def extract(out_path, files):
    try: d = json.load(open(out_path))
    except Exception: d = {}
    for f in files:
        soup = load_soup(f)
        for el in units(soup):
            d.setdefault(key_of(el), "")
        for el in soup.find_all(attrs={'placeholder': True}):
            d.setdefault(norm(el['placeholder']), "")
    json.dump(d, open(out_path,'w'), ensure_ascii=False, indent=0)
    print(f'{out_path}: {len(d)} units, {sum(1 for v in d.values() if not v)} untranslated')

SWITCH_CSS = '''
<style id="i18n-css">
#lang-pick{position:fixed;top:10px;right:10px;z-index:9999;font:600 .85rem -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;background:var(--card,#fff);color:var(--ink,#0f172a);border:1px solid var(--line,#e2e8f0);border-radius:999px;padding:6px 12px;box-shadow:0 2px 10px rgba(0,0,0,.08);cursor:pointer}
html[lang="mr"] body{font-family:"Noto Sans Devanagari","Mukta","Devanagari Sangam MN","Nirmala UI",-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
html[lang="mr"] svg text{font-family:"Noto Sans Devanagari","Mukta","Devanagari Sangam MN","Nirmala UI",sans-serif}
@media print{#lang-pick{display:none}}
</style>'''

SWITCH_HTML = '''<select id="lang-pick" aria-label="Language / भाषा" onchange="schoolSetLang(this.value)">
<option value="mr">🇮🇳 मराठी</option><option value="en">🇬🇧 English</option></select>'''

SWITCH_JS = '''
<script id="i18n-js">
function schoolSetLang(l){
  try{localStorage.setItem('school-lang',l)}catch(e){}
  document.documentElement.setAttribute('lang',l);
  document.querySelectorAll('[data-en]').forEach(function(el){
    if(!el.hasAttribute('data-mr')) el.setAttribute('data-mr', el.innerHTML);
    el.innerHTML = (l==='en') ? el.getAttribute('data-en') : el.getAttribute('data-mr');
  });
  document.querySelectorAll('[data-en-ph]').forEach(function(el){
    if(!el.hasAttribute('data-mr-ph')) el.setAttribute('data-mr-ph', el.getAttribute('placeholder'));
    el.setAttribute('placeholder', (l==='en') ? el.getAttribute('data-en-ph') : el.getAttribute('data-mr-ph'));
  });
  var p=document.getElementById('lang-pick'); if(p) p.value=l;
}
(function(){ var l='mr'; try{ l=localStorage.getItem('school-lang')||'mr'; }catch(e){}
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',function(){schoolSetLang(l)}); else schoolSetLang(l); })();
</script>'''

def apply(mr_path, files):
    d = json.load(open(mr_path))
    for f in files:
        soup = load_soup(f)
        n = 0
        for el in units(soup):
            k = key_of(el)
            mr = d.get(k, '')
            if not mr or mr == k: continue
            el['data-en'] = el.decode_contents()
            el.clear(); el.append(BeautifulSoup(mr, 'html.parser')); n += 1
        for el in soup.find_all(attrs={'placeholder': True}):
            k = norm(el['placeholder']); mr = d.get(k, '')
            if mr and mr != k:
                el['data-en-ph'] = el['placeholder']; el['placeholder'] = mr
        soup.html['lang'] = 'mr'
        soup.head.append(BeautifulSoup(SWITCH_CSS, 'html.parser'))
        soup.body.insert(0, BeautifulSoup(SWITCH_HTML, 'html.parser'))
        soup.body.append(BeautifulSoup(SWITCH_JS, 'html.parser'))
        open(f, 'w', encoding='utf-8').write(str(soup))
        print(f'{f.split("/")[-1]}: {n} units translated')

def restore(_path, files):
    for f in files:
        raw = open(f, encoding='utf-8').read()
        if 'id="i18n-js"' not in raw:
            print(f.split('/')[-1], 'was not applied'); continue
        soup = BeautifulSoup(raw, 'html.parser'); strip_layer(soup)
        open(f, 'w', encoding='utf-8').write(str(soup))
        print(f.split('/')[-1], 'restored to English')

def dump(path, args):
    d = json.load(open(path)); keys = list(d.keys())
    start, count = int(args[0]), int(args[1])
    todo = [i for i,k in enumerate(keys) if not d[k]]
    for i in todo[start:start+count]:
        print(f'{i}\t{keys[i]}')
    print(f'# remaining untranslated: {len(todo)}', file=sys.stderr)

def merge(path, args):
    d = json.load(open(path)); keys = list(d.keys())
    n = 0
    for bf in args:
        b = json.load(open(bf))
        for i, mr in b.items():
            k = keys[int(i)]
            if mr and mr.strip(): d[k] = mr.strip(); n += 1
    json.dump(d, open(path,'w'), ensure_ascii=False, indent=0)
    print(f'merged {n}; untranslated left: {sum(1 for v in d.values() if not v)}')

if __name__ == '__main__':
    cmd, path, *files = sys.argv[1:]
    {'extract': extract, 'apply': apply, 'restore': restore, 'dump': dump, 'merge': merge}[cmd](path, files)
