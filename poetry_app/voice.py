"""Retained Chinese TTS controller. Call on the iOS UI thread."""
class Speaker:
    def __init__(self):
        self.module=None;self.synth=None;self.backend='';self.language='';self.generation=0
    @staticmethod
    def choose_language(languages):
        languages=list(languages)
        for preferred in ('zh-cn','zh-hans','zh-tw','zh-hk'):
            for lang in languages:
                if str(lang).replace('_','-').lower()==preferred:return str(lang)
        return next((str(x) for x in languages if str(x).replace('_','-').lower().startswith('zh')),None)
    def _audio_session(self):
        # Playback category also permits speech while the silent switch is on.
        try:
            from objc_util import ObjCClass
            session=ObjCClass('AVAudioSession').sharedInstance()
            session.setCategory_error_('AVAudioSessionCategoryPlayback',None)
            session.setActive_error_(True,None)
        except Exception:pass
    def speak(self,text):
        if not str(text).strip():raise ValueError('没有可朗读的内容')
        self.stop();self._audio_session()
        try:
            import speech
            lang=self.choose_language(speech.get_synthesis_languages())
            if not lang:raise ValueError('没有中文声音')
            # Pythonista versions differ in positional argument acceptance.
            speech.say(text,language=lang,rate=0.43)
            self.module=speech;self.backend='Pythonista';self.language=lang
        except Exception:
            self.speak_native(text)
        return self.backend+' · '+self.language
    def speak_native(self,text):
        if self.module:
            try:self.module.stop()
            except Exception:pass
        from objc_util import ObjCClass
        self._audio_session()
        Voice=ObjCClass('AVSpeechSynthesisVoice')
        lang=self.choose_language(str(v.language()) for v in Voice.speechVoices())
        if not lang:raise RuntimeError('未找到中文声音，请在 iPhone 设置中下载中文语音后重试')
        if self.synth is None:self.synth=ObjCClass('AVSpeechSynthesizer').alloc().init()
        self.synth.stopSpeakingAtBoundary_(0)
        utterance=ObjCClass('AVSpeechUtterance').speechUtteranceWithString_(text)
        utterance.setVoice_(Voice.voiceWithLanguage_(lang));utterance.setRate_(0.43)
        self.synth.speakUtterance_(utterance)
        self.backend='iOS 系统';self.language=lang
        return self.backend+' · '+lang
    def is_speaking(self):
        if self.backend=='Pythonista' and self.module:return bool(self.module.is_speaking())
        return bool(self.synth and self.synth.isSpeaking())
    def stop(self):
        self.generation+=1
        if self.module:
            try:self.module.stop()
            except Exception:pass
        if self.synth:
            try:self.synth.stopSpeakingAtBoundary_(0)
            except Exception:pass
        self.backend=''
