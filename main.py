"""Pythonista launcher with startup recovery. Keep beside data/ and poetry_app/."""
import sys,os,json,re,tempfile,traceback,datetime
ROOT=os.path.dirname(os.path.abspath(__file__))
USER=os.path.join(ROOT,'user_data')

def read_json(path):
    try:
        with open(path,encoding='utf-8') as f:return json.load(f)
    except (OSError,ValueError):return {}

def write_json(path,value):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=os.path.dirname(path),prefix='.launch-')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def valid_version(value):return isinstance(value,str) and re.fullmatch(r'\d+\.\d+\.\d+',value) is not None

def activate_fallback(active):
    pointer=os.path.join(USER,'active.json')
    previous=active.get('previous_version')
    write_json(os.path.join(USER,'failed_active.json'),active)
    if valid_version(previous) and previous not in (active.get('version'),'1.1.0') and os.path.isfile(os.path.join(ROOT,'releases',previous,'poetry_app','app.py')):
        write_json(pointer,{'version':previous})
        return previous
    if os.path.exists(pointer):os.unlink(pointer)
    return None

def load(code):
    for name in list(sys.modules):
        if name=='poetry_app' or name.startswith('poetry_app.'):del sys.modules[name]
    sys.path.insert(0,code)
    from poetry_app.app import run
    return run(ROOT)

def main():
    active=read_json(os.path.join(USER,'active.json'))
    if not isinstance(active,dict):active={}
    state=read_json(os.path.join(USER,'startup_state.json'))
    version=active.get('version')
    if version=='1.1.0':
        print('检测到有启动问题的 1.1.0，已停用该版本。')
        version=activate_fallback(active)
    if isinstance(state,dict) and state.get('phase')=='starting' and state.get('version')==version:
        print('上次启动未完成，已回退；收藏和手记保持原样。')
        version=activate_fallback(active)
    code=ROOT
    if valid_version(version):
        candidate=os.path.join(ROOT,'releases',version)
        if os.path.isfile(os.path.join(candidate,'poetry_app','app.py')):code=candidate
    if code==ROOT:
        try:
            with open(os.path.join(ROOT,'poetry_app','core.py'),encoding='utf-8') as f:base=f.read()
            match=re.search(r"VERSION\s*=\s*['\"]([0-9.]+)",base)
            if match and match.group(1)=='1.1.0':
                print('随包版本也是 1.1.0。请从 GitHub 下载最新版，保留 user_data，不覆盖个人资料。')
                return None
        except OSError:pass
    write_json(os.path.join(USER,'startup_state.json'),{'version':version or 'base','phase':'starting','stage':'launcher','at':datetime.datetime.now().isoformat(timespec='seconds')})
    try:
        result=load(code)
        try:
            import ui
            def legacy_ready():
                state=read_json(os.path.join(USER,'startup_state.json'))
                if isinstance(state,dict) and state.get('phase')=='starting' and state.get('stage')=='launcher' and getattr(result,'on_screen',True):
                    write_json(os.path.join(USER,'startup_state.json'),{'version':version or 'base','phase':'ready','stage':'legacy-view-presented'})
            ui.delay(legacy_ready,3.0)
        except ImportError:pass
        return result
    except Exception:
        os.makedirs(USER,exist_ok=True)
        with open(os.path.join(USER,'startup_error.txt'),'w',encoding='utf-8') as f:f.write(traceback.format_exc())
        print('启动未完成。报错已保存至 user_data/startup_error.txt。')
        write_json(os.path.join(USER,'startup_state.json'),{'version':version or 'base','phase':'failed','stage':'python-exception'})
        if code!=ROOT:
            activate_fallback(active)
            print('更新版本已停用，请再次运行 main.py 回到旧版，再检查更新。')
        return None

if __name__=='__main__':
    APP=main()  # Retain the UI controller for the entire script session.
