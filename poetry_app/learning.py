"""Offline recitation helpers; punctuation-insensitive self checks."""
import difflib, unicodedata, datetime

def normalize(text):
    return ''.join(c for c in text if unicodedata.category(c)[0] in ('L','N')).casefold()

def assess(expected, actual):
    want,got=normalize(expected),normalize(actual)
    matcher=difflib.SequenceMatcher(None,want,got,autojunk=False)
    edits=[]
    for op,i,j,a,b in matcher.get_opcodes():
        if op!='equal':edits.append({'kind':op,'expected':want[i:j],'actual':got[a:b]})
    return {'score':round(matcher.ratio()*100) if want else 0,'exact':bool(want) and want==got,'differences':edits[:30], 'expected_chars':len(want),'actual_chars':len(got)}

def review_record(previous, mastered=False, score=None):
    today=datetime.date.today()
    record=dict(previous or {})
    record['attempts']=int(record.get('attempts',0))+1
    record['status']='mastered' if mastered else 'learning'
    record['last_practiced']=today.isoformat()
    streak=int(record.get('streak',0))+1 if mastered else 0
    record['streak']=streak
    record['due']=(today+datetime.timedelta(days=([1,3,7,14,30][min(max(streak-1,0),4)] if mastered else 1))).isoformat()
    if score is not None:record['last_score']=max(0,min(100,int(score)))
    return record
