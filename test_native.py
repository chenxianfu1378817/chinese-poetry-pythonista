"""Exercise the actual HTTP server, not native speech/WebView mocks."""
import json,sys,tempfile,shutil,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch,Mock
from poetry_app.app import run
from test_support import fake_ui
ROOT=Path(__file__).resolve().parent
class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'data',self.root/'data');self.ui=fake_ui()
        with patch.dict(sys.modules,{'ui':self.ui}):self.reader=run(str(self.root))
    def tearDown(self):self.reader.close();self.ui.shutdown();self.temp.cleanup()
    def post(self,action,data=None):
        request=urllib.request.Request(self.reader.base+'api',data=json.dumps({'action':action,'data':data or {}}).encode(),headers={'Content-Type':'application/json'})
        return json.load(urllib.request.urlopen(request))
    def test_settings_have_no_automatic_native_keychain_calls(self):
        with patch('poetry_app.ai.has_key',side_effect=AssertionError('no implicit native access')):
            for _ in range(10):
                html=urllib.request.urlopen(self.reader.base).read().decode()
                self.assertIn('DeepSeek Flash',html)
                self.assertNotIn("`;bridge('ai_settings')}",html)
        self.assertNotIn('evaluate_javascript',(ROOT/'poetry_app/app.py').read_text())
        self.assertNotIn('ui.delay',(ROOT/'poetry_app/app.py').read_text())
    def test_authenticated_transport_and_foreign_origin(self):
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(self.reader.origin+'/wrong/')
        req=urllib.request.Request(self.reader.base+'api',data=b'{"action":"exit"}',headers={'Origin':'https://evil.example'})
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(req)
        self.assertFalse(self.reader.was_closed)
    def test_mutations_round_trip(self):
        ident=self.reader.lib.poems[0]['id'];self.post('favorite',{'id':ident})
        self.post('save',{'id':ident,'note':'HTTP 保存','font_size':30})
        self.post('practice',{'id':ident,'mastered':True})
        from poetry_app.core import Library
        user=Library(str(self.root)).user
        self.assertIn(ident,user['favorites']);self.assertEqual(user['notes'][ident],'HTTP 保存')
        self.assertEqual(user['font_size'],30);self.assertEqual(user['learning'][ident]['status'],'mastered')
    def test_key_is_explicit_only_and_not_saved_in_profile(self):
        with patch('poetry_app.ai.set_key') as setter:
            r=self.post('ai_key',{'key':'TEST_NOT_A_REAL_KEY'});setter.assert_called_once()
            self.assertTrue(r['key_configured'])
        self.assertNotIn('TEST_NOT_A_REAL_KEY',str(self.reader.payload()))
    def test_disabled_native_speech_does_not_import_engine(self):
        with patch.dict(sys.modules,{'speech':None}):self.assertIn('网页朗读',self.post('speak',{})['message'])
if __name__=='__main__':unittest.main()
