"""Small startup breadcrumbs; no profile data or credentials are recorded."""
import os,datetime
from .core import VERSION,atomic_json

def mark(root,phase,stage=''):
    try:
        atomic_json(os.path.join(root,'user_data','startup_state.json'),{
            'version':VERSION,'phase':phase,'stage':stage,
            'at':datetime.datetime.now().isoformat(timespec='seconds')})
    except OSError:pass
