"""Compatibility placeholder for older updater package allowlists."""
class Speaker:
    def speak(self,text):raise RuntimeError('此版仅使用网页朗读，不调用 Pythonista 原生语音')
    def stop(self):pass
