import os, json, threading
from urllib.parse import unquote
from .core import Library, VERSION
from . import updater

def run(root):
    import ui
    lib = Library(root)
    lock = threading.Lock()
    class Delegate:
        def webview_should_start_load(self, web, url, nav_type):
            if not url.startswith('poetry:'): return True
            try: message = json.loads(unquote(url.split(':',1)[1]))
            except Exception: return False
            def perform():
                try:
                    action = message['action']; data = message.get('data', {})
                    if action == 'favorite': lib.favorite(data['id'])
                    elif action == 'save':
                        for k in ('theme','mode','update_url'):
                            if k in data: lib.user[k] = data[k]
                        if 'note' in data: lib.user['notes'][data['id']] = data['note']
                        lib.save()
                    elif action == 'speak':
                        import speech
                        speech.stop(); speech.say(data['text'], 'zh-CN', 0.43)
                    elif action == 'stop':
                        import speech
                        speech.stop()
                    elif action == 'update':
                        m = updater.check(lib.user['update_url'])
                        if m:
                            import dialogs
                            if dialogs.alert('发现版本 ' + m['version'], '更新来源：' + lib.user['update_url'] + '\n下载校验并安装，下次重新运行生效。', '安装') == 1:
                                updater.install(root, m); notify('已安装，请停止脚本后重新运行')
                        else: notify('当前已是最新版本')
                    elif action == 'rollback':
                        p = os.path.join(root,'user_data','active.json')
                        if os.path.exists(p): os.unlink(p)
                        notify('已切回随包版本，请停止脚本后重新运行')
                    ui.delay(lambda: web.evaluate_javascript('receiveUser(' + json.dumps(lib.user,ensure_ascii=True) + ')'), 0)
                except Exception as e: notify('操作未完成：' + str(e))
            def work():
                with lock: perform()
            threading.Thread(target=work, daemon=True).start()
            return False
    def notify(text):
        ui.delay(lambda: web.evaluate_javascript('notice(' + json.dumps(text) + ')'), 0)
    web = ui.WebView(name='中华诗词 · ' + VERSION)
    delegate = Delegate(); web.delegate = delegate
    payload = {'poems': lib.poems, 'user':lib.user, 'today':lib.today()['id'], 'version':VERSION}
    html = open(os.path.join(os.path.dirname(__file__),'index.html'),encoding='utf-8').read()
    html = html.replace('/*BOOTSTRAP*/', 'window.BOOT=' + json.dumps(payload, ensure_ascii=True).replace('<','\\u003c') + ';')
    web.load_html(html)
    web.present('fullscreen')
    return web
