import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from measure import *

PARAMS = json.load(open(os.path.join(ROOT, 'Tools/params/params.json')))['params']
BY_ID = {p['id']: p for p in PARAMS}

import re as _re
_norm = lambda t: _re.sub(r'[^a-z0-9]', '', t.lower())
def voice_id(group, name):
    for p in PARAMS:
        if p['group'] == group and _norm(p['name']) == _norm(name): return p['id']
    raise KeyError((group, name))

def defaults():
    return {p['id']: p['default'] for p in PARAMS}

def par_lines(kit):
    return ['par PAR_%s %d' % (i.upper(), v) for i, v in kit.items()]

class V:
    """overrides by readable name for one voice group"""
    def __init__(self, group): self.group = group
    def __call__(self, **kw):
        out = {}
        for k, v in kw.items():
            name = k.replace('_', ' ')
            out[voice_id(self.group, name)] = v
        return out

def window_hz(x, t0, t1, n=4096):
    a = int(t0 * FS / 1000); seg = x[a:a + int((t1 - t0) * FS / 1000)]
    n = 1
    while n < max(len(seg), 1024): n <<= 1
    seg = seg + [0.0] * (n - len(seg))
    return dominant_hz(seg, 0, n)

def zc_hz(x, t0, t1):
    """mean frequency from upward zero crossings in [t0,t1] ms"""
    a, b = int(t0 * FS / 1000), int(t1 * FS / 1000)
    zs = [i for i in range(a + 1, min(b, len(x) - 1)) if x[i - 1] < 0 <= x[i]]
    if len(zs) < 2: return 0.0
    return (len(zs) - 1) * FS / (zs[-1] - zs[0])
