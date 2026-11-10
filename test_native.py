import json,sys,time,tempfile,shutil,types,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from urllib.parse import quote
from poetry_app.app import run
from poetry_app.core import Library
from poetry_app.voice import Speaker
from poetry_app.learning import assess,review_record
from test_support import fake_ui
ROOT=Path(__file__).resolve().parent
class VoiceTests(unittest.TestCase):
    def test_supported_locale_and_keyword_arguments(self):
        speech=types.SimpleNamespace(get_synthesis_languages=lambda:['en_US','zh_CN'],say=Mock(),stop=Mock(),is_speaking=lambda:True)
        with patch.dict(sys.modules,{'speech':speech}):
            speaker=Speaker();speaker.speak('山居秋暝')
            speech.say.assert_called_once_with('山居秋暝',language='zh_CN',rate=0.43)
            self.assertTrue(speaker.is_speaking());speaker.stop();speech.stop.assert_called()
    def test_older_speech_without_rate(self):
        speech=types.SimpleNamespace(get_synthesis_languages=lambda:['zh-CN'],say=Mock(side_effect=[TypeError('rate unsupported'),None]),stop=Mock())
        with patch.dict(sys.modules,{'speech':speech}):
            speaker=Speaker();speaker.speak('春晓')
            self.assertEqual(speech.say.call_args.kwargs,{'language':'zh-CN'})
    def test_retry_uses_another_installed_chinese_locale(self):
        speech=types.SimpleNamespace(get_synthesis_languages=lambda:['zh_CN','zh_TW'],say=Mock(),stop=Mock())
        with patch.dict(sys.modules,{'speech':speech}):
            speaker=Speaker();speaker.speak('春晓');speaker.retry('春晓')
            self.assertEqual(speech.say.call_args.kwargs['language'],'zh_TW')
    def test_chinese_voice_priority(self):
        self.assertEqual(Speaker.choose_language(['en_US','zh_TW','zh_CN']),'zh_CN')
        self.assertIsNone(Speaker.choose_language(['en-US']))
class LearningTests(unittest.TestCase):
    def test_punctuation_and_mistakes(self):
        self.assertTrue(assess('空山新雨後，天氣晚來秋。','空山新雨後\n天氣晚來秋')['exact'])
        self.assertLess(assess('空山新雨後','空山雨後')['score'],100)
        self.assertEqual(assess('空山新雨後','')['score'],0)
    def test_review_progress(self):
        first=review_record({},True,100);second=review_record(first,True,100)
        self.assertEqual(second['attempts'],2);self.assertGreater(second['due'],first['due'])
        self.assertEqual(review_record(second,False,60)['status'],'learning')
class NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'data',self.root/'data')
        self.patch=patch.dict(sys.modules,{'ui':fake_ui()});self.patch.start();self.shell=run(str(self.root))
    def tearDown(self):self.shell.close();self.patch.stop();self.temp.cleanup()
    def send(self,action,data=None):
        web=self.shell.web;count=len([s for s in web.scripts if s.startswith('bridgeDone(')])
        web.delegate.webview_should_start_load(web,'poetry:'+quote(json.dumps({'action':action,'data':data or {}})),0)
        if action=='exit':return
        for _ in range(300):
            if len([s for s in web.scripts if s.startswith('bridgeDone(')])>count:return
            time.sleep(.005)
        self.fail('Bridge did not acknowledge '+action)
    def test_standard_webview_and_retained_reader(self):
        import gc
        from poetry_app.app import _ACTIVE_READERS
        self.assertEqual(self.shell.web.presented,'fullscreen')
        self.assertEqual(self.shell.web.right_button_items[0].title,'退出')
        gc.collect();self.assertIn(self.shell,_ACTIVE_READERS)
        payload=json.loads(self.shell.web.html.split('window.BOOT=',1)[1].split(';\nconst themes=',1)[0])
        self.assertFalse(payload['native_shell'])
        self.send('navigate',{'tab':'learn'});self.assertEqual(self.shell.active_tab,'learn')
    def test_startup_breadcrumbs_do_not_include_profile(self):
        state=json.loads((self.root/'user_data/startup_state.json').read_text())
        self.assertEqual(state['phase'],'starting')
        self.assertNotIn('notes',state);self.assertNotIn('favorites',state)
        self.shell.close()
        self.assertEqual(json.loads((self.root/'user_data/startup_state.json').read_text())['phase'],'closed')
    def test_saves_are_serialized_and_exit_keeps_draft(self):
        ident=Library(str(self.root)).poems[0]['id']
        self.send('favorite',{'id':ident});self.send('save',{'font_size':31})
        self.shell.web.draft={'id':ident,'note':'退出前没有手动保存的手记'}
        self.send('exit')
        user=Library(str(self.root)).user
        self.assertIn(ident,user['favorites']);self.assertEqual(user['font_size'],31)
        self.assertEqual(user['notes'][ident],'退出前没有手动保存的手记')
        self.assertTrue(self.shell.was_closed)
    def test_external_links_keep_reader_content(self):
        web=self.shell.web
        with patch('webbrowser.open') as browser:
            self.assertFalse(web.delegate.webview_should_start_load(web,'https://github.com/chinese-poetry/chinese-poetry',0))
            browser.assert_called_once()
        self.assertFalse(self.shell.was_closed)
    def test_speech_uses_poem_id(self):
        ident=Library(str(self.root)).poems[-1]['id']
        with patch('poetry_app.app.Speaker.speak',return_value='Chinese voice') as speak:
            self.send('speak',{'id':ident});self.assertIn('遊子吟',speak.call_args.args[0])
if __name__=='__main__':unittest.main()
