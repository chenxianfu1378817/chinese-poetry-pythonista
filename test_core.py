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
        self.assertEqual(len(self.lib.poems),25324)
        self.assertEqual(len({p['id'] for p in self.lib.poems}),25324)
        self.assertEqual({p['category'] for p in self.lib.poems},{'唐诗','宋词','诗经'})
    def test_corpus_scope_and_major_authors(self):
        report=json.loads((ROOT/'data/CORPUS_REPORT.json').read_text())
        self.assertEqual(report['count'],len(self.lib.poems))
        self.assertEqual(report['authors'],self.lib.authors)
        self.assertEqual(len(report['source_files']),82)
        self.assertEqual(sum('/poet.tang.' in x['path'] for x in report['source_files']),58)
        self.assertEqual(sum('/ci.song.' in x['path'] for x in report['source_files']),22)
        for author,count in [('李白',1173),('杜甫',1479),('白居易',2986),('王维',397),('苏轼',366),('辛弃疾',632),('李清照',53)]:
            self.assertEqual(self.lib.authors[author],count)
        self.assertEqual(self.lib.stats()['collections'],report['collections'])
        self.assertLess(len(self.lib.initial()),100)
    def test_pagination_and_cross_script_search(self):
        page=self.lib.catalog({'author':'李白','limit':40})
        second=self.lib.catalog({'author':'李白','offset':40,'limit':40})
        self.assertEqual(page['total'],1173);self.assertTrue(page['more'])
        self.assertEqual(len(page['poems']),40)
        self.assertFalse({p['id'] for p in page['poems']}&{p['id'] for p in second['poems']})
        self.assertEqual(self.lib.catalog({'query':'王维'})['total'],self.lib.catalog({'query':'王維'})['total'])
        for query in ['长恨歌','大江东去','寻寻觅觅','國破山河在','床前明月光']:
            self.assertTrue(self.lib.search(query),query)
        self.assertEqual(self.lib.catalog({'collection':'诗经'})['total'],305)
        self.assertLessEqual(len(self.lib.catalog({'limit':99999})['poems']),80)
    def test_legacy_saved_records_remain_discoverable(self):
        legacy=json.loads((ROOT/'data/poems.json').read_text())
        old=next(p for p in legacy if p['id'] not in self.lib.index)
        ident=old['id'];self.lib.favorite(ident)
        self.lib.settings({'id':ident,'note':'旧版原文手记'})
        self.lib.practice(ident,True)
        reloaded=Library(str(self.root))
        self.assertEqual(reloaded.poem(ident),old)
        self.assertEqual(reloaded.catalog({'favorites':True})['poems'][0]['id'],ident)
        self.assertIn(ident,{p['id'] for p in reloaded.initial()})
        self.assertIn(old,reloaded.search(old['title']))
        reloaded.favorite(ident)
        self.assertIn(old,reloaded.search(old['title']))  # Note/learning survives unfavoriting.
        self.assertEqual(reloaded.user['notes'][ident],'旧版原文手记')
    def test_update_fits_previous_updater_size_limit(self):
        raw,_=self.package()
        self.assertLess(len(raw),8*1024*1024)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertLess(sum(p.file_size for p in z.infolist()),8*1024*1024)
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
    def test_today(self):
        self.assertEqual(self.lib.today(),self.lib.today())
        self.assertTrue(self.lib.today()['featured'])
        import random
        rng=random.Random(137)
        samples=[self.lib.random_poem(rng) for _ in range(100)]
        self.assertGreater(len({p['author_key'] for p in samples}),30)
        self.assertTrue(all(p['author_key'] in self.lib.stats()['major_authors'] for p in samples))
    def test_voice_backend_migrates_and_persists(self):
        self.assertEqual(self.lib.user['voice_backend'],'web')
        self.lib.settings({'voice_backend':'web'})
        self.assertEqual(Library(str(self.root)).user['voice_backend'],'web')
        with self.assertRaises(ValueError):self.lib.settings({'voice_backend':'invalid'})
    def test_font_and_learning_persist(self):
        ident=self.lib.poems[-1]['id']
        self.lib.settings({'font_size':32})
        self.lib.practice(ident,True,100)
        reloaded=Library(str(self.root))
        self.assertEqual(reloaded.user['font_size'],32)
        self.assertEqual(reloaded.user['learning'][ident]['status'],'mastered')
        self.assertEqual(reloaded.user['learning'][ident]['last_score'],100)
        reloaded.settings({'font_size':100})
        self.assertEqual(reloaded.user['font_size'],40)
        reloaded.settings({'font_size':-1})
        self.assertEqual(reloaded.user['font_size'],16)
    def test_text_script_migrates_and_persists(self):
        self.assertEqual(self.lib.user['text_script'],'simplified')
        ident=self.lib.poems[0]['id'];self.lib.favorite(ident)
        self.lib.settings({'text_script':'original','id':ident,'note':'保留原字形筆記'})
        reloaded=Library(str(self.root))
        self.assertEqual(reloaded.user['text_script'],'original')
        self.assertIn(ident,reloaded.user['favorites'])
        self.assertEqual(reloaded.user['notes'][ident],'保留原字形筆記')
        with self.assertRaises(ValueError):reloaded.settings({'text_script':'invalid'})
    def test_voice_preference_persists(self):
        value='["local-voice","Chinese Enhanced","zh-CN"]'
        self.lib.settings({'speech_voice':value,'speech_rate':0.8})
        reloaded=Library(str(self.root))
        self.assertEqual(reloaded.user['speech_voice'],value)
        self.assertEqual(reloaded.user['speech_rate'],0.8)
        reloaded.settings({'speech_rate':3})
        self.assertEqual(reloaded.user['speech_rate'],1.2)
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
