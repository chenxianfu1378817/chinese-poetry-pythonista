import json, os, hashlib, random, datetime, tempfile
VERSION = '1.0.3'
DEFAULT_UPDATE_URL = 'https://raw.githubusercontent.com/chenxianfu1378817/chinese-poetry-pythonista/updates/update_channel/manifest.json'

def atomic_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.save-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

class Library:
    def __init__(self, root):
        self.root = root
        self.path = os.path.join(root, 'user_data', 'profile.json')
        self.user = {'favorites': [], 'notes': {}, 'theme': '活力橙', 'mode': 'system', 'update_url': DEFAULT_UPDATE_URL}
        if os.path.exists(self.path):
            with open(self.path, encoding='utf-8') as f: self.user.update(json.load(f))
        if not self.user.get('update_url') or self.user.get('update_url') == 'https://github.com/chenxianfu1378817/chinese-poetry-pythonista/releases/latest/download/manifest.json':
            self.user['update_url'] = DEFAULT_UPDATE_URL
        with open(os.path.join(root, 'data', 'poems.json'), encoding='utf-8') as f: self.poems = json.load(f)
    def save(self): atomic_json(self.path, self.user)
    def search(self, query='', category='', favorites=False):
        q = query.casefold().strip()
        return [p for p in self.poems if (not category or p['category'] == category) and
                (not favorites or p['id'] in self.user['favorites']) and
                (not q or q in (p['title'] + p['author'] + ''.join(p['paragraphs'])).casefold())]
    def today(self):
        seed = datetime.date.today().isoformat()
        return random.Random(seed).choice(self.poems)
    def favorite(self, ident):
        if ident not in {p['id'] for p in self.poems}: raise ValueError('未知诗词')
        f = self.user['favorites']
        if ident in f: f.remove(ident)
        else: f.append(ident)
        self.save()
