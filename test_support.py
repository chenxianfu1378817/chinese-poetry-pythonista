"""Desktop test doubles, never imported by the iPhone application."""
import types
class View:
    def __init__(self,**kwargs):
        self.subviews=[];self.width=390;self.height=760;self.name='';self.was_closed=False
        for k,v in kwargs.items():setattr(self,k,v)
    def add_subview(self,child):self.subviews.append(child)
    @property
    def frame(self):return getattr(self,'_frame',(0,0,self.width,self.height))
    @frame.setter
    def frame(self,value):self._frame=value;self.width=value[2];self.height=value[3]
    def present(self,style,**kwargs):
        self.presented=style;self.presentation_options=kwargs
        if hasattr(self,'layout'):self.layout()
    def close(self):
        if not self.was_closed:
            if hasattr(self,'will_close'):self.will_close()
            self.was_closed=True
class Web(View):
    loaded=[]
    def __init__(self,**kwargs):super().__init__(**kwargs);self.scripts=[];self.draft={}
    def load_html(self,html):
        self.html=html;Web.loaded.append(self)
        if hasattr(self,'delegate'):self.delegate.webview_did_finish_load(self)
    def load_url(self,url):
        import urllib.request
        self.load_html(urllib.request.urlopen(url).read().decode('utf-8'))
    def evaluate_javascript(self,script):
        self.scripts.append(script)
        if script=='JSON.stringify(draftSnapshot())':
            import json
            return json.dumps(self.draft)
        return None
class Button(View):pass
class ButtonItem:
    def __init__(self,**kwargs):self.__dict__.update(kwargs)
def fake_ui():
    import queue,threading
    tasks=queue.Queue()
    def consume():
        while True:
            item=tasks.get()
            if item is None:return
            fn,args,kwargs=item
            fn(*args,**kwargs)
    interpreter=threading.Thread(target=consume,name='FakePythonistaInterpreter',daemon=True)
    interpreter.start()
    def in_background(fn):
        def wrapped(*args,**kwargs):tasks.put((fn,args,kwargs))
        return wrapped
    def shutdown():tasks.put(None);interpreter.join(timeout=2)
    return types.SimpleNamespace(View=View,WebView=Web,Button=Button,ButtonItem=ButtonItem,
        delay=lambda fn,seconds:fn() if not seconds else None,
        in_background=in_background,shutdown=shutdown)
