"""Capture only reviewed post-cutover export changes as strict source render patches.

The source branch predates four production export PRs. Patches retain their exact
published content without overwriting subsequent source work or generated chrome.
Each expected fragment must match once when rendering; drift fails the build.
"""
import json, re, subprocess
from pathlib import Path

BASE = 'ebc11445'
LIVE = '0581611a1bf6c1bc9278c93223c9d677b16708bd'
def read(ref, path):
    return subprocess.check_output(['git','show',f'{ref}:{path}']).decode('utf8')

paths = subprocess.check_output(['git','diff','--name-only',BASE,LIVE]).decode().splitlines()
patches = {}
for path in paths:
    if not (path == 'export.html' or path.startswith('export/') and path.endswith('.html')):
        continue
    old, new = read(BASE,path), read(LIVE,path)
    changes = []
    # Rows and prose paragraphs cover all tax, customs, conformity and transit changes.
    for pattern in [r'<tr>.*?</tr>', r'<p\b[^>]*>.*?</p>', r'<section class="cwg__related">.*?</section>']:
        if path == 'export.html' and not pattern.startswith('<section'): continue
        before, after = re.findall(pattern,old,re.S), re.findall(pattern,new,re.S)
        assert len(before) == len(after), (path,pattern)
        for a,b in zip(before,after):
            if a != b:
                # Rows already contain their paragraphs if any.
                if not any(a in c['before'] for c in changes):
                    changes.append({'before':a,'after':b})
    if path == 'export.html':
        # The hub adds the whole remaining-market section inside its article.
        pattern = r'<article class="cwg__body">.*?</article>'
        a,b = re.search(pattern,old,re.S)[0],re.search(pattern,new,re.S)[0]
        changes = [c for c in changes if c['before'] not in a]
        if a != b: changes.insert(0,{'before':a,'after':b})
    patches[path.removesuffix('.html')] = changes
Path('content/export/published-patches.json').write_text(json.dumps({'source':LIVE,'baseline':BASE,'patches':patches},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Captured',sum(map(len,patches.values())),'published export fragments')
