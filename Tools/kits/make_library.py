#!/usr/bin/env python3
"""Build the LynnDrum demo / production preset library.

    make_library.py                      write Presets/factory/*.lynnpreset (library presets) and docs/preset-library.md
    make_library.py --check              fail if the committed presets / docs differ from what the source generates
    make_library.py --audit [name ...]   render every pattern through the real engine + sequencer and check level, clipping and
                                         that each demonstration's technique is measurably audible (needs build-core/lxr_render_seq)
    make_library.py --balance [--write] [name ...]   find per-voice volumes (kick, d2, d3, snare, cymbal, hat) that mix well; --write stores them in library/balance.json
    make_library.py --preview [name ...] also write WAVs + spectrograms into build-previews/ (git-ignored) to listen to / look at

The factory presets written by make_factory.py (Init, Tight 4/4, Deep Backbeat, Metal Broken) are untouched.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from library.core import *
import library.techno as techno
import library.electro as electro
import library.house as house
import library.dnb as dnb
import library.experimental as experimental
import library.lessons as lessons

MODULES = [techno, house, dnb, electro, experimental, lessons]


def all_presets():
    out = []
    for m in MODULES: out += m.PRESETS
    return out


def main(argv):
    presets = all_presets()
    names = [a for a in argv if not a.startswith('--')]
    if names:
        sel = [p for p in presets if any(n.lower() in p.name.lower() for n in names)]
        if not sel: sys.exit('no preset matches %s' % names)
    else: sel = presets
    if '--balance' in argv:
        import library.audit as audit
        import json
        res = {p.name: audit.balance(p) for p in sel}
        if '--write' in argv:
            cur = dict(BALANCE); cur.update(res)
            json.dump(cur, open(BALANCE_FILE, 'w'), indent=1, sort_keys=True); open(BALANCE_FILE, 'a').write('\n'); print('wrote', os.path.relpath(BALANCE_FILE, ROOT))
        return 0
    if '--audit' in argv or '--preview' in argv:
        import library.audit as audit
        bad = []
        for p in sel:
            bad += audit.audit(p)
            if '--preview' in argv: print('  previews:', audit.preview(p))
        print('\n%d problem(s)' % len(bad)); [print(' -', b) for b in bad]
        return 1 if bad else 0
    if '--check' in argv:
        import tempfile, library.docs as docs
        hdr = os.path.join(os.path.dirname(__file__), 'library', 'doc_header.md'); bad = []
        with tempfile.TemporaryDirectory() as t:
            for f in write_presets(presets, t):
                cur = os.path.join(PRESET_DIR, os.path.basename(f))
                if not os.path.exists(cur) or open(cur).read() != open(f).read(): bad.append(os.path.relpath(cur, ROOT))
            dp = docs.write_doc(presets, open(hdr).read(), os.path.join(t, 'doc.md'))
            if not os.path.exists(docs.DOC) or open(docs.DOC).read() != open(dp).read(): bad.append(os.path.relpath(docs.DOC, ROOT))
        print('library is up to date' if not bad else 'OUT OF DATE (run make_library.py): ' + ', '.join(bad))
        return 1 if bad else 0
    files = write_presets(presets)
    for f in files: print('wrote', os.path.relpath(f, ROOT))
    import library.docs as docs
    hdr = os.path.join(os.path.dirname(__file__), 'library', 'doc_header.md')
    print('wrote', os.path.relpath(docs.write_doc(presets, open(hdr).read() if os.path.exists(hdr) else '# LynnDrum preset library'), ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
