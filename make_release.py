"""Build full install ZIP + app update ZIP + manifest; never uploads."""
import argparse, ast, hashlib, json, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXCLUDED={'.git','__pycache__','user_data','releases','release_build','.github'}

def build(base_url, tag=None):
    if not base_url.startswith('https://'): raise ValueError('HTTPS required')
    tree=ast.parse((ROOT/'poetry_app/core.py').read_text(encoding='utf-8'))
    version=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets))
    if tag and tag!='v'+version: raise ValueError('Tag must match core.VERSION: v'+version)
    out=ROOT/'release_build';out.mkdir(exist_ok=True)
    name='poetry-'+version+'.zip';target=out/name
    with zipfile.ZipFile(str(target),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted((ROOT/'poetry_app').iterdir()):
            if p.suffix in ('.py','.html'): z.write(str(p),'poetry_app/'+p.name)
    manifest={'version':version,'url':base_url.rstrip('/')+'/'+name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    full=out/('ChinesePoetry-'+version+'.zip')
    with zipfile.ZipFile(str(full),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob('*')):
            relative=p.relative_to(ROOT)
            if p.is_file() and not (set(relative.parts)&EXCLUDED) and p.suffix not in ('.pyc','.pyo') and p.name not in ('.DS_Store','.gitignore'):
                z.write(str(p),'ChinesePoetry/'+relative.as_posix())
    (out/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in (full,target,out/'manifest.json'))+'\n',encoding='utf-8')
    print('Built release '+version+' in '+str(out)+'; not uploaded.')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',required=True);parser.add_argument('--tag');args=parser.parse_args()
    build(args.base_url,args.tag)
