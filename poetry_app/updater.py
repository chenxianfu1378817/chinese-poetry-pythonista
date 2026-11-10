"""HTTPS manifest + SHA256, isolated releases, atomic activation."""
import io, json, os, re, hashlib, zipfile, shutil, tempfile
from urllib.request import urlopen, Request
from urllib.parse import urlparse
from .core import VERSION, atomic_json
MAX_SIZE = 8 * 1024 * 1024

def fetch(url):
    if urlparse(url).scheme != 'https': raise ValueError('更新地址必须使用 HTTPS')
    with urlopen(Request(url, headers={'User-Agent': 'ChinesePoetry/1.0'}), timeout=20) as r:
        if urlparse(r.geturl()).scheme != 'https': raise ValueError('不安全的跳转')
        data = r.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE: raise ValueError('更新文件过大')
    return data

def check(url):
    m = json.loads(fetch(url).decode('utf-8'))
    if not re.fullmatch(r'\d+\.\d+\.\d+', m.get('version', '')): raise ValueError('版本格式错误')
    if not re.fullmatch('[0-9a-f]{64}', m.get('sha256', '')): raise ValueError('校验值错误')
    if tuple(map(int,m['version'].split('.'))) <= tuple(map(int,VERSION.split('.'))): return None
    return m

def install(root, manifest, payload=None):
    data = fetch(manifest['url']) if payload is None else payload
    if hashlib.sha256(data).hexdigest() != manifest['sha256']: raise ValueError('更新校验失败')
    version = manifest['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version): raise ValueError('版本格式错误')
    releases = os.path.join(root, 'releases'); os.makedirs(releases, exist_ok=True)
    stage = tempfile.mkdtemp(dir=releases)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            total = 0; names = set()
            for i in z.infolist():
                name = i.filename
                if i.is_dir(): continue
                if not re.fullmatch(r'poetry_app/[A-Za-z_][A-Za-z_0-9]*\.(py|html)', name): raise ValueError('更新包含未允许的路径')
                if name in names: raise ValueError('重复文件')
                names.add(name); total += i.file_size
                if total > MAX_SIZE: raise ValueError('解压文件过大')
                content = z.read(i)
                if name.endswith('.py'): compile(content, name, 'exec')
                dest = os.path.join(stage, name); os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, 'wb') as f: f.write(content)
            required = {'poetry_app/__init__.py','poetry_app/app.py','poetry_app/core.py','poetry_app/updater.py','poetry_app/index.html'}
            if not required.issubset(names): raise ValueError('更新文件不完整')
        target = os.path.join(releases, version)
        if os.path.exists(target): raise ValueError('此版本已安装；请先回退再清理对应版本目录')
        os.replace(stage, target)
        atomic_json(os.path.join(root,'user_data','active.json'), {'version': version})
    finally:
        if os.path.exists(stage): shutil.rmtree(stage)
