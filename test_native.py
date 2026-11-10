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
    def test_one_minimal_request_without_enumeration_stop_or_poll(self):
        speech=types.SimpleNamespace(say=Mock(),stop=Mock(),get_synthesis_languages=Mock(side_effect=AssertionError('no enumeration')),is_speaking=Mock(side_effect=AssertionError('no polling')))
        with patch.dict(sys.modules,{'speech':speech}):
            speaker=Speaker();speaker.speak('山居秋暝')
            speech.say.assert_called_once_with('山居秋暝',language='zh-CN')
            speech.stop.assert_not_called();speech.get_synthesis_languages.assert_not_called();speech.is_speaking.assert_not_called()
            self.assertTrue(speaker.active)
    def test_rapid_repeated_requests_are_rejected_until_explicit_stop(self):
        speech=types.SimpleNamespace(say=Mock(),stop=Mock())
        with patch.dict(sys.modules,{'speech':speech}):
            speaker=Speaker();speaker.speak('春晓')
            with self.assertRaises(ValueError):speaker.speak('江雪')
            speech.say.assert_called_once();speech.stop.assert_not_called()
            speaker.stop();speaker.stop();speech.stop.assert_called_once()
            speaker.speak('江雪');self.assertEqual(speech.say.call_count,2)
    def test_native_error_is_not_retried(self):
        speech=types.SimpleNamespace(say=Mock(side_effect=RuntimeError('unavailable')),stop=Mock())
        with patch.dict(sys.modules,{'speech':speech}):
            speaker=Speaker()
            with self.assertRaises(RuntimeError):speaker.speak('春晓')
            speech.say.assert_called_once();speech.stop.assert_not_called();self.assertFalse(speaker.active)
    def test_constructing_controller_does_not_import_native_speech(self):
        with patch('poetry_app.voice.importlib.import_module') as loader:
            speaker=Speaker();speaker.stop();loader.assert_not_called()
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
        self.ui=fake_ui();self.patch=patch.dict(sys.modules,{'ui':self.ui});self.patch.start();self.shell=run(str(self.root))
    def tearDown(self):self.shell.close();self.ui.shutdown();self.patch.stop();self.temp.cleanup()
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
    def test_speech_and_stop_never_run_on_ui_callback_thread(self):
        import threading
        ui_ident=threading.get_ident();calls=[];stopped=threading.Event()
        speech=types.SimpleNamespace(say=lambda *args,**kwargs:calls.append(('say',threading.get_ident())),stop=lambda:(calls.append(('stop',threading.get_ident())),stopped.set()))
        ident=Library(str(self.root)).poems[-1]['id']
        with patch.dict(sys.modules,{'speech':speech}):
            self.send('speak',{'id':ident});self.send('stop');self.assertTrue(stopped.wait(1))
            self.shell.close();self.ui.shutdown()
        self.assertEqual([x[0] for x in calls],['say','stop'])
        self.assertTrue(all(x[1]!=ui_ident for x in calls),calls)
    def test_disabled_backend_cannot_call_native_speech(self):
        speech=types.SimpleNamespace(say=Mock(),stop=Mock())
        ident=Library(str(self.root)).poems[0]['id']
        self.send('save',{'voice_backend':'off'})
        with patch.dict(sys.modules,{'speech':speech}):
            self.send('speak',{'id':ident});speech.say.assert_not_called()
    def test_unfinished_native_request_uses_web_on_next_launch(self):
        self.shell.close();self.ui.shutdown()
        lib=Library(str(self.root));lib.settings({'voice_backend':'pythonista'})
        before=(self.root/'user_data/profile.json').read_bytes()
        (self.root/'user_data/voice_state.json').write_text('{"phase":"before-say"}')
        self.ui=fake_ui()
        with patch.dict(sys.modules,{'ui':self.ui}):self.shell=run(str(self.root))
        payload=json.loads(self.shell.web.html.split('window.BOOT=',1)[1].split(';\nconst themes=',1)[0])
        self.assertEqual(payload['user']['voice_backend'],'web')
        self.assertTrue(payload['voice_notice'])
        self.assertEqual((self.root/'user_data/profile.json').read_bytes(),before)
    def test_same_thread_dispatch_is_blocked_without_calling_native_speech(self):
        ui=types.SimpleNamespace(**self.ui.__dict__);ui.in_background=lambda fn:fn
        with patch.dict(sys.modules,{'ui':ui}):
            reader=run(str(self.root))
            speech=types.SimpleNamespace(say=Mock(),stop=Mock())
            ident=Library(str(self.root)).poems[0]['id']
            with patch.dict(sys.modules,{'speech':speech}):
                reader.web.delegate.webview_should_start_load(reader.web,'poetry:'+quote(json.dumps({'action':'speak','data':{'id':ident}})),0)
                speech.say.assert_not_called()
                self.assertFalse(reader.was_closed)
                self.assertTrue(any('speechStatus' in line for line in reader.web.scripts))
            reader.close()
if __name__=='__main__':unittest.main()
