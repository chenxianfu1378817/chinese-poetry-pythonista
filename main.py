"""Pythonista: open this file and tap Run."""
import sys, os, json
ROOT = os.path.dirname(os.path.abspath(__file__))
code = ROOT
try:
    version = json.load(open(os.path.join(ROOT, 'user_data', 'active.json')))['version']
    if not all(c.isdigit() or c == '.' for c in version): raise ValueError('version')
    candidate = os.path.join(ROOT, 'releases', version)
    if os.path.isfile(os.path.join(candidate, 'poetry_app', 'app.py')): code = candidate
except (OSError, ValueError, KeyError): pass
for module in list(sys.modules):
    if module == 'poetry_app' or module.startswith('poetry_app.'):
        del sys.modules[module]
sys.path.insert(0, code)
from poetry_app.app import run
run(ROOT)
