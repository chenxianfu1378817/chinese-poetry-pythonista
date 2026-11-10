"""Public HTTPS installation/update smoke test; no credentials or real user data."""
import argparse, hashlib, io, json, re, runpy, shutil, sys, tempfile, types, zipfile
from pathlib import Path
from poetry_app.core import Library, DEFAULT_UPDATE_URL
from poetry_app import updater
ROOT=Path(__file__).resolve().parent

def verify():
    saved_version=updater.VERSION
    try:
        # Exercise the shipped updater with an older installed version number.
        updater.VERSION='1.0.0'
        manifest=updater.check(DEFAULT_UPDATE_URL)
        assert manifest is not None, 'Expected a published version newer than 1.0.0'
        version=manifest['version'];base=manifest['url'].rsplit('/',1)[0]
        archive_name='ChinesePoetry-'+version+'.zip'
        full=updater.fetch(base+'/'+archive_name)
        sums=updater.fetch(base+'/SHA256SUMS.txt').decode('utf-8')
        assert hashlib.sha256(full).hexdigest()+'  '+archive_name in sums
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copytree(ROOT/'data',root/'data');shutil.copy(str(ROOT/'main.py'),str(root/'main.py'))
            lib=Library(str(root));ident=lib.poems[0]['id'];lib.favorite(ident)
            lib.user['notes'][ident]='线上更新验证手记';lib.user['theme']='竹叶青';lib.save()
            before=(root/'user_data/profile.json').read_bytes()
            updater.install(str(root),manifest)
            assert (root/'user_data/profile.json').read_bytes()==before
            from test_support import fake_ui, Web
            sys.modules['ui']=fake_ui()
            before_load=len(Web.loaded)
            runpy.run_path(str(root/'main.py'),run_name='__main__')
            assert len(Web.loaded)==before_load+1
            payload=json.loads(re.search(r'window.BOOT=(.*?);\nconst themes=',Web.loaded[-1].html,re.S).group(1))
            assert payload['version']==version
            assert ident in payload['user']['favorites']
            assert payload['user']['notes'][ident]=='线上更新验证手记'
            assert payload['user']['theme']=='竹叶青'
            from poetry_app import updater as latest
            assert latest.check(DEFAULT_UPDATE_URL) is None
            with zipfile.ZipFile(io.BytesIO(full)) as z:
                assert z.testzip() is None
                assert 'ChinesePoetry/main.py' in z.namelist()
                assert not any('/user_data/' in n or '/.git/' in n for n in z.namelist())
        return {'result':'PASS','version':version,'manifest_url':DEFAULT_UPDATE_URL,'sha256':manifest['sha256'],'checks':['public anonymous HTTPS manifest','public HTTPS full ZIP and SHA256SUMS','public HTTPS app update ZIP','isolated install and atomic activation','profile bytes preserved','launcher loads downloaded code','favorites, notes and theme preserved','latest version reports no update'],'scope':'Desktop smoke test with simulated older version number and ui module; not an iPhone device test'}
    finally: updater.VERSION=saved_version

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args()
    result=verify();text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:Path(args.output).write_text(text,encoding='utf-8')
    print(text)
