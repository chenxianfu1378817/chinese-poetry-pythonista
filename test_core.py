import unittest, tempfile, shutil, os, io, zipfile, hashlib, json
from pathlib import Path
from unittest.mock import patch
from poetry_app.core import Library, VERSION, DEFAULT_UPDATE_URL
from poetry_app import updater
ROOT=Path(__file__).resolve().parent
_parts=list(map(int,VERSION.split('.')));_parts[-1]+=1
NEXT_VERSION='.'.join(map(str,_parts))
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'data',self.root/'data');self.lib=Library(str(self.root))
    def tearDown(self):self.tmp.cleanup()
    def package(self, extra=None):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            for p in (ROOT/'poetry_app').iterdir():
                if p.suffix in ('.py','.html'): z.writestr('poetry_app/'+p.name,p.read_bytes())
            if extra:z.writestr(extra,'bad')
        raw=b.getvalue();return raw,{'version':NEXT_VERSION,'sha256':hashlib.sha256(raw).hexdigest(),'url':'https://example.com/release.zip'}
    def test_data(self):
        self.assertEqual(len(self.lib.poems),2305)
        self.assertEqual(len({p['id'] for p in self.lib.poems}),2305)
        self.assertEqual({p['category'] for p in self.lib.poems},{'唐诗','宋词','诗经'})
    def test_search(self):
        p=self.lib.poems[0]
        self.assertIn(p,self.lib.search(p['title']))
        self.assertIn(p,self.lib.search(p['author']))
        self.assertIn(p,self.lib.search(p['paragraphs'][0][:4]))
        self.assertTrue(all(p['category']=='诗经' for p in self.lib.search(category='诗经')))
        self.assertEqual(self.lib.search('不存在的标题XYZ'),[])
    def test_user_persistence(self):
        ident=self.lib.poems[0]['id'];self.lib.favorite(ident)
        self.lib.user['notes'][ident]='学习笔记';self.lib.user['mode']='dark';self.lib.save()
        reloaded=Library(str(self.root));self.assertEqual(reloaded.user,self.lib.user)
        self.assertEqual(len(reloaded.search(favorites=True)),1)
        reloaded.favorite(ident);self.assertEqual(reloaded.search(favorites=True),[])
    def test_today(self):self.assertEqual(self.lib.today(),self.lib.today())
    def test_update_preserves_user(self):
        self.lib.favorite(self.lib.poems[0]['id']);before=(self.root/'user_data/profile.json').read_bytes()
        raw,m=self.package();updater.install(str(self.root),m,raw)
        self.assertTrue((self.root/'releases'/NEXT_VERSION/'poetry_app/app.py').exists())
        self.assertEqual(json.loads((self.root/'user_data/active.json').read_text())['version'],NEXT_VERSION)
        self.assertEqual((self.root/'user_data/profile.json').read_bytes(),before)
    def test_hash_rejection(self):
        raw,m=self.package()
        with self.assertRaises(ValueError):updater.install(str(self.root),m,raw+b'corrupt')
        self.assertFalse((self.root/'user_data/active.json').exists())
    def test_path_rejection(self):
        for path in ['../user_data/profile.json','poetry_app/../../evil.py','user_data/profile.json']:
            raw,m=self.package(path)
            with self.assertRaises(ValueError):updater.install(str(self.root),m,raw)
        self.assertFalse((self.root/'user_data/active.json').exists())
    def test_manifest(self):
        raw,m=self.package()
        with patch.object(updater,'fetch',return_value=json.dumps(m).encode()):self.assertEqual(updater.check(m['url']),m)
        m['version']=VERSION
        with patch.object(updater,'fetch',return_value=json.dumps(m).encode()):self.assertIsNone(updater.check(m['url']))
    def test_https(self):
        with self.assertRaises(ValueError):updater.fetch('http://example.com/m.json')
    def test_incomplete(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('poetry_app/app.py','x=1')
        raw=b.getvalue();m={'version':NEXT_VERSION,'sha256':hashlib.sha256(raw).hexdigest()}
        with self.assertRaises(ValueError):updater.install(str(self.root),m,raw)
    def test_default_update_url_and_migration(self):
        self.assertEqual(self.lib.user['update_url'], DEFAULT_UPDATE_URL)
        ident=self.lib.poems[0]['id'];self.lib.favorite(ident)
        self.lib.user['update_url']='';self.lib.user['notes'][ident]='保留旧版手记';self.lib.save()
        reloaded=Library(str(self.root))
        self.assertEqual(reloaded.user['update_url'], DEFAULT_UPDATE_URL)
        self.assertIn(ident,reloaded.user['favorites'])
        self.assertEqual(reloaded.user['notes'][ident],'保留旧版手记')
        reloaded.user['update_url']='https://github.com/chenxianfu1378817/chinese-poetry-pythonista/releases/latest/download/manifest.json';reloaded.save()
        self.assertEqual(Library(str(self.root)).user['update_url'], DEFAULT_UPDATE_URL)
        reloaded.user['update_url']='https://example.com/custom.json';reloaded.save()
        self.assertEqual(Library(str(self.root)).user['update_url'],'https://example.com/custom.json')
if __name__=='__main__':unittest.main()
