import json, os, random, datetime, tempfile
from .featured import EXTRA_POEMS
from .learning import review_record
from .corpus import load,MAJOR_AUTHORS,CHAR_MAP
import collections
VERSION = '1.5.1'
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
        with open(os.path.join(root,'data','poems.json'),encoding='utf-8') as f:legacy=json.load(f)
        legacy.extend(EXTRA_POEMS)
        self.poems=load()
        self.by_id={p['id']:p for p in legacy}
        self.by_id.update({p['id']:p for p in self.poems})
        self.translation=str.maketrans(CHAR_MAP)
        self.index={p['id']:(p['title']+p['author']+''.join(p['paragraphs'])).translate(self.translation).casefold() for p in self.poems}
        self.authors=dict(collections.Counter(p['author_key'] for p in self.poems))
        self.groups={}
        for p in self.poems:self.groups.setdefault(p['author_key'],[]).append(p)
        self.featured=[p for p in self.poems if p.get('featured')]
        self.random_groups={a:self.groups[a] for a in MAJOR_AUTHORS if a in self.groups}
        self.featured_groups={}
        for p in self.featured:self.featured_groups.setdefault(p['author_key'],[]).append(p)
    def personal_ids(self):
        return set(self.user['favorites'])|set(self.user['notes'])|set(self.user['learning'])|set(self.user['ai_cache'])
    def catalog_pool(self):
        # Keep saved legacy entries discoverable without reintroducing shard order.
        return self.poems+[self.by_id[i] for i in sorted(self.personal_ids()) if i in self.by_id and i not in self.index]
    def matches(self,p,query):
        if not query:return True
        text=self.index.get(p['id'])
        if text is None:text=(p['title']+p['author']+''.join(p['paragraphs'])).translate(self.translation).casefold()
        return query in text
    def public(self,p):
        return {k:v for k,v in p.items() if not k.startswith('_')}
    def initial(self):
        ids=[p['id'] for p in self.featured[:80]]+[self.today()['id']]+self.user['favorites']+list(self.user['learning'])
        return [self.public(self.by_id[i]) for i in dict.fromkeys(ids) if i in self.by_id]
    def stats(self):
        return {'total':len(self.poems),'authors':self.authors,'categories':dict(collections.Counter(p['category'] for p in self.poems)),
                'collections':dict(collections.Counter(c for p in self.poems for c in p.get('collections',[]))),
                'major_authors':MAJOR_AUTHORS,'scope':'唐宋选本、主要诗人扩充、其他作者选篇；旧版非主库作品保留在个人收藏。'}
    def catalog(self,data):
        query=str(data.get('query','')).translate(self.translation).casefold().strip();category=data.get('category','');author=data.get('author','');collection=data.get('collection','')
        pool=[self.by_id[i] for i in self.user['favorites'] if i in self.by_id] if data.get('favorites') else self.catalog_pool()
        result=[]
        for p in pool:
            if category and p['category']!=category:continue
            if author and p.get('author_key',p['author'])!=author:continue
            if collection and collection not in p.get('collections',[]):continue
            if not self.matches(p,query):continue
            result.append(p)
        offset=max(0,int(data.get('offset',0)));limit=max(1,min(80,int(data.get('limit',40))))
        return {'poems':[self.public(p) for p in result[offset:offset+limit]],'total':len(result),'offset':offset,'more':offset+limit<len(result)}
    def random_poem(self,rng=None,featured=False):
        rng=rng or random
        groups=self.featured_groups if featured else self.random_groups
        return rng.choice(groups[rng.choice(sorted(groups))])
    def save(self): atomic_json(self.path,self.user)
    def poem(self,ident):
        if ident not in self.by_id:raise ValueError('未找到诗词')
        return self.by_id[ident]
    def search(self,query='',category='',favorites=False):
        # Developer helper returns complete matches; UI uses bounded catalog pages.
        pool=[self.by_id[i] for i in self.user['favorites'] if i in self.by_id] if favorites else self.catalog_pool()
        q=query.translate(self.translation).casefold().strip()
        return [p for p in pool if (not category or p['category']==category) and self.matches(p,q)]
    def today(self):return self.random_poem(random.Random(datetime.date.today().isoformat()),True)
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
