import json, os, random, datetime, tempfile
from .featured import EXTRA_POEMS
from .learning import review_record
VERSION = '1.4.0'
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

def font_size(value):
    try: return max(16,min(40,int(value)))
    except (TypeError, ValueError): return 23

class Library:
    def __init__(self, root):
        self.root=root
        self.path=os.path.join(root,'user_data','profile.json')
        self.user={'favorites':[],'notes':{},'theme':'活力橙','mode':'system','update_url':DEFAULT_UPDATE_URL,
                   'text_script':'simplified','speech_voice':'','speech_rate':0.9,'voice_backend':'web','font_size':23,'learning':{},'ai_cache':{},'ai_endpoint':'https://api.deepseek.com','ai_model':'deepseek-flash'}
        if os.path.exists(self.path):
            with open(self.path,encoding='utf-8') as f:self.user.update(json.load(f))
        if not self.user.get('update_url') or self.user.get('update_url')=='https://github.com/chenxianfu1378817/chinese-poetry-pythonista/releases/latest/download/manifest.json':
            self.user['update_url']=DEFAULT_UPDATE_URL
        if not self.user.get('ai_endpoint'):self.user['ai_endpoint']='https://api.deepseek.com'
        if not self.user.get('ai_model'):self.user['ai_model']='deepseek-flash'
        if self.user.get('voice_backend') in ('auto','pythonista'):self.user['voice_backend']='web'
        if self.user.get('voice_backend') not in ('auto','web','pythonista','off'):self.user['voice_backend']='auto'
        if self.user.get('text_script') not in ('original','simplified','traditional'):self.user['text_script']='simplified'
        self.user['font_size']=font_size(self.user.get('font_size'))
        with open(os.path.join(root,'data','poems.json'),encoding='utf-8') as f:self.poems=json.load(f)
        ids={p['id'] for p in self.poems}
        self.poems.extend(p for p in EXTRA_POEMS if p['id'] not in ids)
        self.by_id={p['id']:p for p in self.poems}
    def save(self): atomic_json(self.path,self.user)
    def poem(self,ident):
        if ident not in self.by_id:raise ValueError('未找到诗词')
        return self.by_id[ident]
    def search(self,query='',category='',favorites=False):
        q=query.casefold().strip()
        return [p for p in self.poems if (not category or p['category']==category) and
                (not favorites or p['id'] in self.user['favorites']) and
                (not q or q in (p['title']+p['author']+''.join(p['paragraphs'])).casefold())]
    def today(self):return random.Random(datetime.date.today().isoformat()).choice(EXTRA_POEMS)
    def favorite(self,ident):
        self.poem(ident);f=self.user['favorites']
        if ident in f:f.remove(ident)
        else:f.append(ident)
        self.save()
    def settings(self,data):
        for k in ('theme','mode','update_url','ai_endpoint','ai_model','speech_voice'):
            if k in data:self.user[k]=str(data[k])
        if 'text_script' in data:
            if data['text_script'] not in ('original','simplified','traditional'):raise ValueError('无效字形')
            self.user['text_script']=data['text_script']
        if 'voice_backend' in data:
            if data['voice_backend'] not in ('auto','web','pythonista','off'):raise ValueError('未知朗读方式')
            self.user['voice_backend']=data['voice_backend']
        if 'speech_rate' in data:
            try:self.user['speech_rate']=max(0.6,min(1.2,float(data['speech_rate'])))
            except (ValueError,TypeError):raise ValueError('无效语速')
        if 'font_size' in data:self.user['font_size']=font_size(data['font_size'])
        if 'note' in data:
            self.poem(data['id']);self.user['notes'][data['id']]=str(data['note'])
        self.save()
    def practice(self,ident,mastered=False,score=None):
        self.poem(ident)
        self.user['learning'][ident]=review_record(self.user['learning'].get(ident),mastered,score)
        self.save()
