"""Loopback HTTP transport: no native JavaScript callbacks."""
import os,json,threading,secrets,hmac
from http.server import BaseHTTPRequestHandler,HTTPServer
from socketserver import ThreadingMixIn
class LocalServer(ThreadingMixIn,HTTPServer):
    daemon_threads=True
from .core import Library,VERSION
from . import ai,updater,startup
_ACTIVE_READERS=[]

class Reader:
    def __init__(self,root,ui):
        self.root=root;self.ui=ui;self.lib=Library(root);self.lock=threading.RLock()
        self.was_closed=False;self.ready=False;self.key_configured=False
        self.token=secrets.token_urlsafe(32)
        self.server=LocalServer(('127.0.0.1',0),self.handler())
        self.server.daemon_threads=True
        self.origin='http://127.0.0.1:'+str(self.server.server_port)
        self.base=self.origin+'/'+self.token+'/'
        self.web=ui.WebView(name='中华诗词 · '+VERSION)
        # All UIKit wrappers are called through the interpreter, never from a
        # WebView delegate, synchronous JS callback or custom Objective-C bridge.
        self.schedule=ui.in_background
        self.web.right_button_items=[ui.ButtonItem(title='退出',action=lambda sender:self.interpreter(self.close,wait=False))]
        self.web.flex='WH'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
    def interpreter(self,fn,wait=True):
        event=threading.Event();result={}
        def work():
            try:result['value']=fn()
            except Exception as e:result['error']=e
            finally:event.set()
        self.schedule(work)()
        if not wait:return
        if not event.wait(45):raise RuntimeError('操作超时，请重试')
        if 'error' in result:raise result['error']
        return result.get('value')
    def payload(self):
        return {'poems':self.lib.initial(),'stats':self.lib.stats(),'user':self.lib.user,'today':self.lib.today()['id'],
            'version':VERSION,'native_shell':False,'api_url':self.base+'api'}
    def html(self):
        with open(os.path.join(os.path.dirname(__file__),'index.html'),encoding='utf-8') as f:s=f.read()
        with self.lock:payload=json.dumps(self.payload(),ensure_ascii=True).replace('<','\\u003c')
        return s.replace('__CONVERTER_URL__',self.base+'converter').replace('/*BOOTSTRAP*/','window.BOOT='+payload+';')
    def action(self,action,data):
        if action=='catalog':
            with self.lock:return {'catalog':self.lib.catalog(data)}
        if action=='poem':return {'poem':self.lib.public(self.lib.poem(data['id']))}
        if action=='random':return {'poem':self.lib.public(self.lib.random_poem())}
        if action=='ai':
            with self.lock:
                poem=self.lib.poem(data['id']);endpoint=self.lib.user['ai_endpoint'];model=self.lib.user['ai_model']
            key=self.interpreter(lambda:ai.get_key(endpoint))
            if not key:raise ValueError('请先在设置中填写并保存 DeepSeek API key')
            text=ai.interpret(poem,endpoint,model,key=key)
            import datetime
            record={'text':text,'model':model,'endpoint':endpoint,'created':datetime.datetime.now().isoformat(timespec='seconds')}
            with self.lock:self.lib.user['ai_cache'][data['id']]=record;self.lib.save()
            return {'ai':{'id':data['id'],'record':record}}
        if action in ('ai_key','ai_delete_key'):
            endpoint=self.lib.user['ai_endpoint']
            if action=='ai_key':
                key=str(data.get('key','')).strip()
                if not key:raise ValueError('请填写 API key')
                self.interpreter(lambda:ai.set_key(endpoint,key));self.key_configured=True
            else:self.interpreter(lambda:ai.delete_key(endpoint));self.key_configured=False
            return {'message':'密钥已保存到手机钥匙串' if self.key_configured else '密钥已移除','key_configured':self.key_configured}
        if action=='update':
            m=updater.check(self.lib.user['update_url'])
            return {'update':m,'message':'发现版本 '+m['version'] if m else '当前已是最新版本'}
        if action=='install_update':
            m=updater.check(self.lib.user['update_url'])
            if not m:return {'message':'当前已是最新版本'}
            updater.install(self.root,m);return {'message':'已安装 '+m['version']+'，请退出后重新运行 main.py'}
        with self.lock:
            if action=='save':self.lib.settings(data)
            elif action=='favorite':self.lib.favorite(data['id'])
            elif action=='practice':self.lib.practice(data['id'],bool(data.get('mastered')),data.get('score'))
            elif action=='ai_settings':return {'key_configured':self.key_configured}
            elif action in ('speak','stop'):return {'message':'此版使用网页朗读，不调用曾导致闪退的 Pythonista speech 模块'}
            elif action=='rollback':
                p=os.path.join(self.root,'user_data','active.json')
                if os.path.exists(p):os.unlink(p)
                return {'message':'已回退，下次重新运行生效'}
            elif action=='exit':return {'exit':True}
            else:raise ValueError('未知操作')
            return {'user':self.lib.user,'message':'手记已保存' if 'note' in data else None}
    def handler(self):
        reader=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass  # Never log URLs, request bodies or keys.
            def valid(self):
                return self.headers.get('Host')==reader.origin.split('//')[1] and self.headers.get('Origin',reader.origin)==reader.origin
            def send(self,status,value,kind='application/json; charset=utf-8'):
                body=value.encode() if isinstance(value,str) else json.dumps(value,ensure_ascii=False).encode()
                self.send_response(status);self.send_header('Content-Type',kind)
                self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def do_GET(self):
                if self.valid() and hmac.compare_digest(self.path,'/'+reader.token+'/converter'):
                    with open(os.path.join(os.path.dirname(__file__),'converter.html'),encoding='utf-8') as f:script=f.read()
                    self.send(200,script,'application/javascript; charset=utf-8');return
                if not self.valid() or not hmac.compare_digest(self.path,'/'+reader.token+'/'):
                    self.send(403,{'error':'拒绝访问'});return
                self.send(200,reader.html(),'text/html; charset=utf-8')
                startup.mark(reader.root,'ready',stage='http-page-served')
            def do_POST(self):
                if not self.valid() or not hmac.compare_digest(self.path,'/'+reader.token+'/api'):
                    self.send(403,{'error':'拒绝访问'});return
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    if not 0<n<=1024*1024:raise ValueError('请求大小不合适')
                    m=json.loads(self.rfile.read(n).decode('utf-8'))
                    result=reader.action(m['action'],m.get('data',{}))
                    self.send(200,result)
                    if result.get('exit'):reader.interpreter(reader.close,wait=False)
                except Exception as e:self.send(200,{'error':str(e)})
        return Handler
    def close(self):
        if self.was_closed:return
        self.was_closed=True
        startup.mark(self.root,'closed',stage='exit')
        self.web.close()
        threading.Thread(target=self.server.shutdown,daemon=True).start()
        self.server.server_close()
        if self in _ACTIVE_READERS:_ACTIVE_READERS.remove(self)

def run(root):
    startup.mark(root,'starting',stage='http-reader')
    import ui
    reader=Reader(root,ui);_ACTIVE_READERS.append(reader)
    try:
        reader.web.load_url(reader.base)
        reader.web.present('fullscreen')
    except Exception:
        reader.close();raise
    return reader
