#!/usr/bin/env python3
"""Create visual QA excerpts from the exact generated document."""
import hashlib
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
s = (BASE / 'plan.html').read_text()
css = re.search(r'<style>(.*?)</style>', s, re.S)[1]
sections = {m[1]:m[0] for m in re.finditer(r'<section id="([^"]+)">.*?</section>', s, re.S)}
dst = BASE / 'qa'
dst.mkdir(exist_ok=True)
groups = {'start':['scope','ui'],'deep':['methods','model','checks'],'international':['international'],'agents':['agents'],'end':['acceptance','decisions','sources'],'decisions':['decisions','sources'],'assumptions':['assumptions'],'reuse':['reuse-policy'],'feedback':['feedback'],'presentation':['presentation']}
groups['variants']=['variants']
probe = "<script>console.log(JSON.stringify({viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,sections:document.querySelectorAll('section').length}));</script>"
for name, keys in groups.items():
    nav = ''.join(f'<a href="#{k}">{re.search(r"<h2>(.*?)</h2>", sections[k])[1]}</a>' for k in keys)
    body = '<div class="layout"><nav id="toc">'+nav+'</nav><main><details class="mobile-nav"><summary>Содержание</summary><nav>'+nav+'</nav></details>'+''.join(sections[k] for k in keys)+'</main></div>'
    (dst / f'{name}.html').write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style>'+body+probe+'</html>')
(dst / 'full.html').write_text(s.replace('</body>',probe+'</body>'))
(dst / 'source.json').write_text(json.dumps({'plan_sha256':hashlib.sha256(s.encode()).hexdigest(),'excerpts':groups,'scope':'Same document CSS and section markup; visual excerpts do not replace full-document structural checks.'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'source_sections':len(sections),'excerpts':len(groups),'source_hash':hashlib.sha256(s.encode()).hexdigest()}))
