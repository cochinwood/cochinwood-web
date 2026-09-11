"""Check preserved production exports, photographs and required root files."""
import json, subprocess, sys, re, html
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import build as B
data=json.loads(Path('content/export/published-patches.json').read_text(encoding='utf8'))
count=0
def visible(value):
    return ' '.join(html.unescape(re.sub('<[^>]+>',' ',value)).split())
for path,patches in data['patches'].items():
    rendered=Path('dist',path+'.html').read_text(encoding='utf8')
    for patch in patches:
        assert visible(patch['after']) in visible(rendered), path
        count+=1
B.LIVE_REF=data['source']
checked=0
for prefix in ['files',*B.CARRIED_ROOT_FILES,B.CARRIED_WORKFLOW]:
    for path,expected in B._live_tree(prefix).items():
        actual=Path('dist',path).read_bytes()
        assert actual == expected, 'Production asset changed: '+path
        checked+=1
print(f'PASS: {count} published export fragments preserve visible copy; {checked} production assets/root files match byte-for-byte')
