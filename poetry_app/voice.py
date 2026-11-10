"""Minimal Pythonista TTS. Every method must run on the interpreter thread."""
import importlib

class Speaker:
    def __init__(self):
        self.module=None;self.active=False;self.language='zh-CN';self.backend=''
    def speak(self,text):
        if not str(text).strip():raise ValueError('没有可朗读的内容')
        if self.active:raise ValueError('已有朗读请求，请先点击停止，再重新朗读')
        module=importlib.import_module('speech')
        # One explicit request: no pre-stop, voice enumeration, rate overrides,
        # polling or automatic retries against the native speech engine.
        module.say(str(text),language=self.language)
        self.module=module;self.active=True;self.backend='Pythonista'
        return 'Pythonista 中文朗读请求已提交；再次播放前请先停止'
    def stop(self):
        if self.module is not None and self.active:
            self.module.stop()
        self.active=False;self.backend=''
