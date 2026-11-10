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
    def test_native_fallback(self):
        speech=types.SimpleNamespace(get_synthesis_languages=lambda:['zh-CN'],say=Mock(side_effect=RuntimeError('unavailable')),stop=Mock())
        with patch.dict(sys.modules,{'speech':speech}):
            speaker=Speaker()
            with patch.object(speaker,'speak_native') as fallback:
                speaker.speak('春晓');fallback.assert_called_once_with('春晓')
    def test_native_synthesizer_is_retained(self):
        synth=Mock();voice=Mock();voice.language.return_value='zh-CN'
        voice_class=Mock();voice_class.speechVoices.return_value=[voice]
        voice_class.voiceWithLanguage_.return_value=voice
        synth_class=Mock();synth_class.alloc.return_value.init.return_value=synth
        utterance=Mock();utterance_class=Mock();utterance_class.speechUtteranceWithString_.return_value=utterance
        session_class=Mock()
        classes={'AVSpeechSynthesisVoice':voice_class,'AVSpeechSynthesizer':synth_class,'AVSpeechUtterance':utterance_class,'AVAudioSession':session_class}
        with patch.dict(sys.modules,{'objc_util':types.SimpleNamespace(ObjCClass=lambda name:classes[name])}):
            speaker=Speaker();speaker.speak_native('山居秋暝')
            self.assertIs(speaker.synth,synth)
            utterance.setVoice_.assert_called_once_with(voice)
            synth.speakUtterance_.assert_called_once_with(utterance)
            speaker.stop();synth.stopSpeakingAtBoundary_.assert_called_with(0)
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
    def test_native_bar_independent_from_webview(self):
        self.assertEqual(len(self.shell.buttons),5)
        self.shell.width=320;self.shell.height=568;self.shell.layout()
        self.assertEqual(self.shell.web.frame[1]+self.shell.web.frame[3],self.shell.bar.frame[1])
        self.assertEqual(self.shell.right_button_items[0].title,'退出')
        self.send('navigate',{'tab':'learn'});self.assertEqual(self.shell.active_tab,'learn')
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
