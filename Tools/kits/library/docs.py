"""Generate docs/preset-library.md from the presets themselves (names, metadata, pattern grids, locks): the catalogue can not drift from the library."""
import os
from library.core import *

DOC = os.path.join(ROOT, 'docs', 'preset-library.md')
LEVELS = {1: 'Level 1 - immediate', 2: 'Level 2 - production', 3: 'Level 3 - educational'}
CATS = ['Techno', 'House', 'Drum & Bass', 'Electro & Broken', 'Experimental', 'Technique']


def preset_section(p):
    m = p.meta; out = []
    out.append('### %s' % p.name)
    out.append('')
    out.append('| | |')
    out.append('|---|---|')
    for label, key in (('Genre', 'category'), ('Level', 'level'), ('Character', 'character'), ('Primary technique', 'technique')):
        v = m[key]; out.append('| %s | %s |' % (label, LEVELS[v] if key == 'level' else v))
    out.append('| Secondary techniques | %s |' % '; '.join(m.get('secondary', [])))
    out.append('| Voices used | %s |' % m['voices'])
    out.append('| Key | %s |' % m['key'])
    out.append('| BPM | %d (suggested; the plugin follows the host tempo) |' % m['bpm'])
    out.append('| Pattern length | %s |' % (m.get('length') or length_text(p.patterns)))
    out.append('| Swing | %s |' % (m.get('swing') or ', '.join(sorted({'%d%%' % round(swing_of(q.shuffle)) for q in p.patterns}))))
    out.append('| **What this demonstrates** | %s |' % m['demonstrates'])
    out.append('')
    for i, (q, desc) in enumerate(zip(p.patterns, m['patterns'])):
        out.append('**Pattern %d** - %s' % (i + 1, desc.split(': ', 1)[1] if ': ' in desc[:3] else desc))
        out.append('')
        grid, extras = q.grid()
        out.append('```text')
        out += grid
        out.append('```')
        if extras:
            out.append('')
            out += ['- ' + e for e in extras]
        out.append('')
    if p.song: out.append('Song (switch on SONG in the pattern bar): ' + ' '.join('%d' % (e + 1) if e < 64 else ('LOOP' if e == LOOP else 'END') for e in p.song) + '.')
    out.append('')
    return out


def overview_table(presets):
    out = ['| Preset | Genre | Level | BPM | Primary technique |', '|---|---|---|---|---|']
    for p in presets:
        out.append('| %s | %s | %d | %d | %s |' % (p.name, p.meta['category'], p.meta['level'], p.meta['bpm'], p.meta['technique']))
    return out


def write_doc(presets, header_md, path=DOC):
    out = [header_md.rstrip(), '', '## Catalogue', '']
    out += overview_table(presets); out.append('')
    for cat in CATS:
        group = [p for p in presets if p.meta['category'] == cat]
        if not group: continue
        out += ['## %s' % cat, '']
        for p in group: out += preset_section(p)
    open(path, 'w').write('\n'.join(out) + '\n')
    return path
