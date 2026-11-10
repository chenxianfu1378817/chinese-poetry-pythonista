"""Rebuild the pinned offline corpus on a development computer (Python 3 + Node).
No extra packages or API keys; the iPhone never needs to run this script.
"""
import argparse, base64, collections, hashlib, json, subprocess, sys, tempfile, zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from poetry_app.featured import EXTRA_POEMS

def rebuild(cache,output):
    report=json.loads((ROOT/'data/CORPUS_REPORT.json').read_text())
    def fetch(item):
        path=cache/item['path'];path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            url='https://raw.githubusercontent.com/chinese-poetry/chinese-poetry/'+report['source_commit']+'/'+quote(item['path'])
            for attempt in range(3):
                try:
                    with urlopen(url,timeout=30) as response:raw=response.read()
                    if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Source checksum mismatch: '+item['path'])
                    path.write_bytes(raw);break
                except Exception:
                    if attempt==2:raise
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Cached source checksum mismatch: '+item['path'])
        return item,json.loads(raw)
    items=json.loads(json.dumps(EXTRA_POEMS))
    with ThreadPoolExecutor(max_workers=8) as pool:
        for source,rows in pool.map(fetch,report['source_files']):
            category='唐诗' if source['path'].startswith('全唐诗/') else '宋词'
            for row in rows:
                paras=row.get('paragraphs');title=row.get('title') or row.get('rhythmic')
                if not title or not isinstance(paras,list) or not paras or not all(isinstance(s,str) for s in paras):continue
                author=row.get('author') or '佚名'
                ident=hashlib.sha256((category+title+author+''.join(paras)).encode()).hexdigest()[:20]
                items.append(dict(id=ident,title=title,author=author,paragraphs=paras,category=category,collections=[category+'三百首'] if '三百首' in source['path'] else []))
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)/'input.json';target=Path(temp)/'normalized.json'
        source.write_text(json.dumps(items,ensure_ascii=False))
        script=r'''
        const fs=require('fs'),vm=require('vm'),c={};vm.createContext(c);
        vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);
        const cv=c.OpenCC.Converter({from:'t',to:'cn'}),rows=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),chars=new Set(),map={};
        for(const p of rows){for(const ch of p.title+p.author+p.paragraphs.join(''))chars.add(ch);p.author_key=cv(p.author);p._dedup=p.category+'|'+p.author_key+'|'+cv(p.paragraphs.join('')).replace(/[\s，。！？；、：,.!?;:“”‘’「」『』（）()《》]/g,'')}
        for(const ch of chars){let s=cv(ch);if(s!==ch)map[ch]=s}
        fs.writeFileSync(process.argv[3],JSON.stringify({rows,map}));
        '''
        subprocess.run(['node','-e',script,str(ROOT/'poetry_app/converter.html'),str(source),str(target)],check=True)
        normalized=json.loads(target.read_text())
    unique={}
    for poem in sorted(normalized['rows'],key=lambda p:0 if p.get('featured') else 1 if p.get('collections') else 2):
        poem.setdefault('collections',[]);key=poem['_dedup']
        if key not in unique:unique[key]=poem
        else:unique[key]['collections']=sorted(set(unique[key]['collections']+poem['collections']))
    others=collections.Counter();selected=[]
    for poem in unique.values():
        important=poem.get('featured') or poem['collections'] or poem['author_key'] in report['major_authors']
        if important or others[poem['author_key']]<2:
            if not important:others[poem['author_key']]+=1
            poem.pop('_dedup');poem['featured']=bool(poem.get('featured') or poem['collections']);selected.append(poem)
    for poem in json.loads((ROOT/'data/poems.json').read_text()):
        if poem['category']=='诗经':
            poem.update(author_key='佚名',collections=['诗经'],featured=False);selected.append(poem)
    assert len(selected)==report['count']
    assert dict(collections.Counter(p['author_key'] for p in selected))==report['authors']
    raw=json.dumps(selected,ensure_ascii=False,separators=(',',':')).encode()
    packed=base64.b85encode(zlib.compress(raw,9)).decode()
    code='"""Offline curated corpus. Source and hashes: data/CORPUS_REPORT.json. MIT data."""\nimport base64,zlib,json,functools\n_DATA = '+repr(packed)+'\n@functools.lru_cache(maxsize=1)\ndef load():\n    return json.loads(zlib.decompress(base64.b85decode(_DATA)).decode("utf-8"))\nMAJOR_AUTHORS = '+repr(report['major_authors'])+'\nCHAR_MAP = '+repr(normalized['map'])+'\n'
    output.write_text(code,encoding='utf-8');print('Rebuilt',len(selected),'records:',output)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache',type=Path);parser.add_argument('--output',type=Path,default=ROOT/'poetry_app/corpus.py');args=parser.parse_args()
    if args.cache:rebuild(args.cache,args.output)
    else:
        with tempfile.TemporaryDirectory() as temp:rebuild(Path(temp),args.output)
