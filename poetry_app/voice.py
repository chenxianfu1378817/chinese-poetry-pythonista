"""Chinese TTS using only Pythonista's documented speech API."""
class Speaker:
    def __init__(self):
        self.module=None;self.backend='';self.language='';self.generation=0;self.languages=[]
    @staticmethod
    def choose_language(languages):
        languages=list(languages)
        for preferred in ('zh-cn','zh-hans','zh-tw','zh-hk'):
            for lang in languages:
                if str(lang).replace('_','-').lower()==preferred:return str(lang)
        return next((str(x) for x in languages if str(x).replace('_','-').lower().startswith('zh')),None)
    def _say(self,text,language):
        try:self.module.say(text,language=language,rate=0.43)
        except TypeError:
            # Older builds may not accept rate; still use their installed locale.
            self.module.say(text,language=language)
        self.backend='Pythonista';self.language=language
        return self.backend+' · '+language
    def speak(self,text):
        if not str(text).strip():raise ValueError('没有可朗读的内容')
        self.stop()
        import speech
        self.module=speech
        self.languages=[str(x) for x in speech.get_synthesis_languages() if str(x).replace('_','-').lower().startswith('zh')]
        lang=self.choose_language(self.languages)
        if not lang:raise RuntimeError('未找到中文声音，请在 iPhone 设置中下载中文语音后重试')
        return self._say(text,lang)
    def retry(self,text):
        if not self.module:raise RuntimeError('系统语音尚未准备好')
        self.module.stop()
        lang=next((x for x in self.languages if x!=self.language),self.language)
        return self._say(text,lang)
    def is_speaking(self):return bool(self.module and self.module.is_speaking())
    def stop(self):
        self.generation+=1
        if self.module:
            try:self.module.stop()
            except Exception:pass
        self.backend=''
