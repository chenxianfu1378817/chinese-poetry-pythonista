"""Put beside your existing main.py and run once in Pythonista. Never launches UI."""
import os,json,re,io,zipfile,hashlib,tempfile,shutil,datetime
from urllib.request import urlopen,Request
from urllib.parse import urlparse
URL='https://raw.githubusercontent.com/chenxianfu1378817/chinese-poetry-pythonista/updates/update_channel/manifest.json'
LIMIT=8*1024*1024
LAUNCHER = '"""Pythonista launcher with startup recovery. Keep beside data/ and poetry_app/."""\nimport sys,os,json,re,tempfile,traceback,datetime\nROOT=os.path.dirname(os.path.abspath(__file__))\nUSER=os.path.join(ROOT,\'user_data\')\n\ndef read_json(path):\n    try:\n        with open(path,encoding=\'utf-8\') as f:return json.load(f)\n    except (OSError,ValueError):return {}\n\ndef write_json(path,value):\n    os.makedirs(os.path.dirname(path),exist_ok=True)\n    fd,tmp=tempfile.mkstemp(dir=os.path.dirname(path),prefix=\'.launch-\')\n    try:\n        with os.fdopen(fd,\'w\',encoding=\'utf-8\') as f:json.dump(value,f,ensure_ascii=False)\n        os.replace(tmp,path)\n    finally:\n        if os.path.exists(tmp):os.unlink(tmp)\n\ndef valid_version(value):return isinstance(value,str) and re.fullmatch(r\'\\d+\\.\\d+\\.\\d+\',value) is not None\n\ndef activate_fallback(active):\n    pointer=os.path.join(USER,\'active.json\')\n    previous=active.get(\'previous_version\')\n    write_json(os.path.join(USER,\'failed_active.json\'),active)\n    if valid_version(previous) and previous not in (active.get(\'version\'),\'1.1.0\') and os.path.isfile(os.path.join(ROOT,\'releases\',previous,\'poetry_app\',\'app.py\')):\n        write_json(pointer,{\'version\':previous})\n        return previous\n    if os.path.exists(pointer):os.unlink(pointer)\n    return None\n\ndef load(code):\n    for name in list(sys.modules):\n        if name==\'poetry_app\' or name.startswith(\'poetry_app.\'):del sys.modules[name]\n    sys.path.insert(0,code)\n    from poetry_app.app import run\n    return run(ROOT)\n\ndef main():\n    active=read_json(os.path.join(USER,\'active.json\'))\n    if not isinstance(active,dict):active={}\n    state=read_json(os.path.join(USER,\'startup_state.json\'))\n    version=active.get(\'version\')\n    if version==\'1.1.0\':\n        print(\'检测到有启动问题的 1.1.0，已停用该版本。\')\n        version=activate_fallback(active)\n    if isinstance(state,dict) and state.get(\'phase\')==\'starting\' and state.get(\'version\')==version:\n        print(\'上次启动未完成，已回退；收藏和手记保持原样。\')\n        version=activate_fallback(active)\n    code=ROOT\n    if valid_version(version):\n        candidate=os.path.join(ROOT,\'releases\',version)\n        if os.path.isfile(os.path.join(candidate,\'poetry_app\',\'app.py\')):code=candidate\n    if code==ROOT:\n        try:\n            with open(os.path.join(ROOT,\'poetry_app\',\'core.py\'),encoding=\'utf-8\') as f:base=f.read()\n            match=re.search(r"VERSION\\s*=\\s*[\'\\"]([0-9.]+)",base)\n            if match and match.group(1)==\'1.1.0\':\n                print(\'随包版本也是 1.1.0。请把 repair_start.py 放在本文件旁并运行，保留 user_data。\')\n                return None\n        except OSError:pass\n    write_json(os.path.join(USER,\'startup_state.json\'),{\'version\':version or \'base\',\'phase\':\'starting\',\'stage\':\'launcher\',\'at\':datetime.datetime.now().isoformat(timespec=\'seconds\')})\n    try:\n        result=load(code)\n        try:\n            import ui\n            def legacy_ready():\n                state=read_json(os.path.join(USER,\'startup_state.json\'))\n                if isinstance(state,dict) and state.get(\'phase\')==\'starting\' and state.get(\'stage\')==\'launcher\' and getattr(result,\'on_screen\',True):\n                    write_json(os.path.join(USER,\'startup_state.json\'),{\'version\':version or \'base\',\'phase\':\'ready\',\'stage\':\'legacy-view-presented\'})\n            ui.delay(legacy_ready,3.0)\n        except ImportError:pass\n        return result\n    except Exception:\n        os.makedirs(USER,exist_ok=True)\n        with open(os.path.join(USER,\'startup_error.txt\'),\'w\',encoding=\'utf-8\') as f:f.write(traceback.format_exc())\n        print(\'启动未完成。报错已保存至 user_data/startup_error.txt。\')\n        write_json(os.path.join(USER,\'startup_state.json\'),{\'version\':version or \'base\',\'phase\':\'failed\',\'stage\':\'python-exception\'})\n        if code!=ROOT:\n            activate_fallback(active)\n            print(\'更新版本已停用，请再次运行 main.py 回到旧版，再检查更新。\')\n        return None\n\nif __name__==\'__main__\':\n    APP=main()  # Retain the UI controller for the entire script session.\n'

def atomic(path,value,binary=False):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=os.path.dirname(path),prefix='.repair-')
    try:
        with os.fdopen(fd,'wb' if binary else 'w',**({} if binary else {'encoding':'utf-8'})) as f:
            f.write(value);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def fetch(url):
    if urlparse(url).scheme!='https':raise ValueError('Only HTTPS updates are accepted')
    with urlopen(Request(url,headers={'User-Agent':'ChinesePoetry-Repair/1.1.1'}),timeout=20) as r:
        if urlparse(r.geturl()).scheme!='https':raise ValueError('Insecure redirect rejected')
        data=r.read(LIMIT+1)
    if len(data)>LIMIT:raise ValueError('Update is too large')
    return data

def repair(root,manifest=None,payload=None):
    root=os.path.abspath(root)
    if not os.path.isfile(os.path.join(root,'main.py')) or not os.path.isfile(os.path.join(root,'data','poems.json')):
        raise ValueError('请先将 repair_start.py 移到原中华诗词文件夹，与原 main.py 放在同一级，再运行。')
    m=manifest if manifest is not None else json.loads(fetch(URL).decode('utf-8'))
    version=m.get('version','')
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('版本格式错误')
    if tuple(map(int,version.split('.'))) < (1,1,1):raise ValueError('修复版本尚未就绪，请稍后再试')
    raw=payload if payload is not None else fetch(m['url'])
    if hashlib.sha256(raw).hexdigest()!=m.get('sha256'):raise ValueError('更新校验失败，未修改程序')
    releases=os.path.join(root,'releases');os.makedirs(releases,exist_ok=True)
    stage=tempfile.mkdtemp(prefix='.repair-',dir=releases)
    try:
        names=set();size=0
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for entry in z.infolist():
                if entry.is_dir():continue
                name=entry.filename
                if not re.fullmatch(r'poetry_app/[A-Za-z_][A-Za-z_0-9]*\.(py|html)',name) or name in names:
                    raise ValueError('更新包含未允许或重复的路径')
                names.add(name);size+=entry.file_size
                if size>LIMIT:raise ValueError('更新解压内容过大')
                content=z.read(entry)
                if name.endswith('.py'):compile(content,name,'exec')
                target=os.path.join(stage,name);os.makedirs(os.path.dirname(target),exist_ok=True)
                with open(target,'wb') as f:f.write(content)
        required={'poetry_app/'+n for n in ('__init__.py','app.py','core.py','index.html','updater.py','startup.py','voice.py','learning.py','ai.py','featured.py')}
        if not required.issubset(names):raise ValueError('更新内容不完整')
        user=os.path.join(root,'user_data');os.makedirs(user,exist_ok=True)
        pointer=os.path.join(user,'active.json');previous=None
        try:
            with open(pointer,encoding='utf-8') as f:previous=json.load(f).get('version')
        except (OSError,ValueError,AttributeError):pass
        # Preserve the original launcher and active pointer. Never touch profile.json.
        backup=tempfile.mkdtemp(prefix='startup_backup_',dir=user)
        shutil.copy2(os.path.join(root,'main.py'),os.path.join(backup,'main.py'))
        if os.path.exists(pointer):shutil.copy2(pointer,os.path.join(backup,'active.json'))
        target=os.path.join(releases,version)
        if os.path.exists(target):
            displaced=tempfile.mkdtemp(prefix='previous-program-',dir=releases)
            os.rmdir(displaced);os.replace(target,displaced)
        os.replace(stage,target)
        atomic(os.path.join(root,'main.py'),LAUNCHER)
        atomic(pointer,json.dumps({'version':version,'previous_version':previous},ensure_ascii=False))
        atomic(os.path.join(user,'startup_state.json'),json.dumps({'version':version,'phase':'repaired','stage':'standalone-repair'}))
        return version
    finally:
        if os.path.exists(stage):shutil.rmtree(stage)

def main():
    root=os.path.dirname(os.path.abspath(__file__))
    print('开始修复中华诗词启动。不会启动阅读界面，也不会改写收藏、手记或密钥。',flush=True)
    for attempt in range(3):
        try:
            version=repair(root)
            print('修复完成：'+version+'。现在打开同文件夹的 main.py 并运行。')
            return
        except (ValueError,KeyError,zipfile.BadZipFile) as e:
            print('未完成：'+str(e));return
        except Exception as e:
            print('网络或文件操作未完成，第 %s/3 次：%s'%(attempt+1,type(e).__name__),flush=True)
    print('未能连接更新服务。保留原文件，稍后换网络重试；个人资料未清空。')

if __name__=='__main__':main()
