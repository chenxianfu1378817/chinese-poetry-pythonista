"""Standard Pythonista WebView reader with retained lifecycle and startup markers."""
import os, json, threading, queue, datetime
from urllib.parse import unquote
from .core import Library, VERSION
from .voice import Speaker
from . import updater, ai, startup

_ACTIVE_READERS=[]

def run(root):
    startup.mark(root,'starting',stage='before-ui-import')
    import ui
    lib=Library(root);speaker=Speaker();lock=threading.RLock();jobs=queue.Queue()
    closed=threading.Event()
    def on_ui(fn):
        def safe():
            if not closed.is_set():fn()
        ui.delay(safe,0)
    def javascript(function,value):
        on_ui(lambda:web.evaluate_javascript(function+'('+json.dumps(value,ensure_ascii=True)+')'))
    def notice(text):javascript('notice',text)
    def finish(message=None,with_user=False):
        result={}
        if message:result['message']=message
        if with_user:
            with lock:result['user']=dict(lib.user)
        javascript('bridgeDone',result)
    def speech_status(message):javascript('speechStatus',message)
    def stop_speech():
        speaker.stop();speech_status('朗读已停止')
    def speak_poem(ident):
        try:
            p=lib.poem(ident)
            text=p['title']+'。'+p['author']+'。'+''.join(p['paragraphs'])
            label=speaker.speak(text);generation=speaker.generation
            speech_status('已提交朗读 · '+label)
            def check_start():
                if closed.is_set() or speaker.generation!=generation:return
                try:
                    if speaker.is_speaking():speech_status('正在朗读 · '+speaker.language)
                    elif speaker.backend=='Pythonista':
                        label=speaker.retry(text)
                        speech_status('已重试系统中文声音 · '+label)
                        ui.delay(check_retry,0.7)
                    else:speech_status('未检测到朗读，请检查媒体音量、音频输出和中文声音')
                except Exception as e:speech_status('朗读未启动：'+str(e))
            def check_retry():
                if closed.is_set() or speaker.generation!=generation:return
                speech_status('正在朗读 · '+speaker.language if speaker.is_speaking() else '未检测到朗读，请检查媒体音量、音频输出和中文声音')
            ui.delay(check_start,0.7)
        except Exception as e:speech_status('朗读失败：'+str(e)+'；请检查中文声音与媒体音量')
        finally:finish()
    def key_available():
        try:return ai.has_key(lib.user['ai_endpoint'])
        except Exception:return False
    def send_ai_settings():javascript('aiSettings',{'configured':key_available()})
    def generate_ai(data):
        ident=data['id'];poem=lib.poem(ident)
        with lock:endpoint=lib.user['ai_endpoint'];model=lib.user['ai_model']
        def worker():
            try:
                text=ai.interpret(poem,endpoint,model)
                record={'text':text,'model':model,'endpoint':endpoint,'created':datetime.datetime.now().isoformat(timespec='seconds')}
                with lock:lib.user['ai_cache'][ident]=record;lib.save()
                javascript('receiveAI',{'id':ident,'record':record})
            except Exception as e:javascript('receiveAI',{'id':ident,'error':str(e)})
        threading.Thread(target=worker,daemon=True).start()
    class Shell:
        # A normal Python controller retains a standard, documented WebView.
        # No UIView subclass callbacks, Objective-C calls or struct-return bridges.
        def __init__(self):
            startup.mark(root,'starting',stage='create-webview')
            self.web=ui.WebView(name='中华诗词 · '+VERSION)
            self.ready=False;self.active_tab='home';self.was_closed=False
            try:self.web.will_close=self.cleanup
            except (AttributeError,TypeError):pass
            self.web.right_button_items=[ui.ButtonItem(title='退出',action=lambda sender:self.request_exit(),tint_color='#f47725')]
        def select_tab(self,tab,colors=None):
            if tab in ('home','library','learn','favorites','settings'):self.active_tab=tab
        def request_exit(self):
            if self.ready:
                try:self.web.evaluate_javascript('requestExit()');return
                except Exception:pass
            self.close()
        def cleanup(self):
            if self.was_closed:return
            self.was_closed=True
            try:
                if self.ready:
                    raw=self.web.evaluate_javascript('JSON.stringify(draftSnapshot())')
                    data=json.loads(raw) if isinstance(raw,str) else raw
                    if isinstance(data,dict) and data.get('id') in lib.by_id:
                        with lock:lib.settings(data)
            except Exception:pass
            closed.set();speaker.stop();jobs.put(None)
            startup.mark(root,'closed',stage='explicit-exit')
            if self in _ACTIVE_READERS:_ACTIVE_READERS.remove(self)
        def close(self):
            self.cleanup()
            self.web.close()
        def present(self):
            startup.mark(root,'starting',stage='present-webview')
            self.web.present('fullscreen')
            def watch_close():
                if closed.is_set():return
                if not getattr(self.web,'on_screen',True):
                    self.cleanup();return
                ui.delay(watch_close,1.0)
            ui.delay(watch_close,1.0)
    shell=Shell();web=shell.web
    class Delegate:
        def webview_did_finish_load(self,view):
            shell.ready=True
            def healthy():
                if not closed.is_set():startup.mark(root,'ready',stage='webview-loaded')
            ui.delay(healthy,3.0)
        def webview_should_start_load(self,view,url,nav_type):
            if not url.startswith('poetry:'):
                if url.startswith(('https://','http://')):
                    import webbrowser
                    webbrowser.open(url)
                    return False
                return url.startswith(('about:','applewebdata:'))
            try:
                message=json.loads(unquote(url.split(':',1)[1]));action=message['action'];data=message.get('data',{})
                if action=='navigate':
                    on_ui(lambda:shell.select_tab(data.get('tab')));finish();return False
                if action=='style':
                    on_ui(lambda:shell.select_tab(shell.active_tab,data));finish();return False
                if action=='speak':on_ui(lambda:speak_poem(data['id']));return False
                if action=='stop':on_ui(stop_speech);finish();return False
                if action=='exit':on_ui(shell.close);return False
                jobs.put((action,data))
            except Exception as e:finish('操作未完成：'+str(e))
            return False
    delegate=Delegate();web.delegate=delegate;shell.delegate_reference=delegate
    def worker():
        while True:
            job=jobs.get()
            if job is None:return
            if closed.is_set():continue
            action,data=job
            try:
                if action=='save':
                    with lock:lib.settings(data)
                    finish('手记已保存' if 'note' in data else None,True)
                elif action=='favorite':
                    with lock:lib.favorite(data['id'])
                    finish(with_user=True)
                elif action=='practice':
                    with lock:lib.practice(data['id'],bool(data.get('mastered')),data.get('score'))
                    finish('学习进度已保存',True)
                elif action=='ai_settings':send_ai_settings();finish()
                elif action=='ai_key':
                    import console
                    endpoint=lib.user['ai_endpoint'];ai.endpoint_url(endpoint)
                    key=console.password_alert('AI 服务密钥','密钥只保存在 iOS 钥匙串，不写入诗词文件或网页。')
                    ai.set_key(endpoint,key);send_ai_settings();finish('密钥已保存到钥匙串')
                elif action=='ai_delete_key':
                    ai.delete_key(lib.user['ai_endpoint']);send_ai_settings();finish('此服务的密钥已移除')
                elif action=='ai':generate_ai(data);finish()
                elif action=='update':
                    m=updater.check(lib.user['update_url'])
                    if m:
                        import dialogs
                        if dialogs.alert('发现版本 '+m['version'],'安装后使用退出按钮关闭阅读器，再运行 main.py。收藏和手记保留。','安装')==1:
                            updater.install(root,m);finish('更新已安装，请退出后重新运行 main.py')
                        else:finish()
                    else:finish('当前已是最新版本')
                elif action=='rollback':
                    p=os.path.join(root,'user_data','active.json')
                    if os.path.exists(p):os.unlink(p)
                    finish('已切回随包版本，请退出后重新运行')
                else:finish('暂不支持此操作')
            except KeyboardInterrupt:finish('已取消')
            except Exception as e:finish('操作未完成：'+str(e))
    threading.Thread(target=worker,daemon=True).start()
    payload={'poems':lib.poems,'user':lib.user,'today':lib.today()['id'],'version':VERSION,
             'native_shell':False,'readings':{p['id']:lib.reading(p['id']) for p in lib.poems if p.get('featured')}}
    with open(os.path.join(os.path.dirname(__file__),'index.html'),encoding='utf-8') as f:html=f.read()
    html=html.replace('/*BOOTSTRAP*/','window.BOOT='+json.dumps(payload,ensure_ascii=True).replace('<','\\u003c')+';')
    _ACTIVE_READERS.append(shell)
    startup.mark(root,'starting',stage='load-html')
    web.load_html(html)
    try:shell.present()
    except Exception:
        shell.close()
        raise
    return shell
