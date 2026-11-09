#!/usr/bin/env python3
"""Offline report checks: anchors, immutable link targets, units and QA fragments."""
import hashlib
import json
import re
import subprocess
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'context/19_report_update_20261110/qa'
QA.mkdir(parents=True, exist_ok=True)
page = (ROOT / 'research-report.html').read_text()


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.texts = [], [], []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'): self.ids.append(a['id'])
        if tag == 'a': self.links.append(a.get('href', ''))
    def handle_data(self, data):
        self.texts.append(data)


parsed = Inspect()
parsed.feed(page)
assert not [key for key, count in Counter(parsed.ids).items() if count > 1]
assert all(link[1:] in parsed.ids for link in parsed.links if link.startswith('#'))
assert all(link.startswith(('#', 'https://')) for link in parsed.links)
git_targets = set()
for link in parsed.links:
    if link.startswith('https://github.com/'):
        match = re.fullmatch(r'https://github.com/Mput13/case_championship/(blob|tree)/([a-f0-9]{40})(?:/(.*))?', link)
        assert match, link
        kind, sha, path = match.groups()
        git_targets.add(sha + (':' + path if path else ''))
for target in sorted(git_targets):
    subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '-e', target])
assert '&gt<br' not in page
assert len(re.findall(r'<tr data-program ', page)) == 35
assert len(re.findall(r'<tr data-program data-queue="true"', page)) == 9
assert len(re.findall(r'data-tested="true"', page)) == 3
assert len(re.findall(r'<section id=', page)) == 16
script = re.search(r'<script>(.*?)</script>', page, re.S).group(1)
(QA / 'report.js').write_text(script)
subprocess.run(['node', '--check', str(QA / 'report.js')], check=True)
style = re.search(r'<style>(.*?)</style>', page, re.S).group(1)
for name, start, end in [('c14', 'c14', 'c01'), ('c01-c07', 'c01', 'issues'),
                         ('programs', 'programs', 'c14'), ('change', 'change', 'next'),
                         ('method', 'method', 'programs'), ('team-context', 'team-context', 'inputs'),
                         ('issues-kover', 'issues', 'change'), ('people', 'people', 'sources')]:
    fragment = page[page.index('<section id="' + start + '"'):page.index('<section id="' + end + '"')]
    body = f'<main class="article">{fragment}</main>'
    (QA / f'{name}.html').write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>' + style + '</style><body><div class="layout">' + body + '</div></body></html>')
# The deep-section copies keep source content/order, but use the full article column.
for fragment in QA.glob('*.html'):
    content = fragment.read_text().replace('</style>', '.layout{display:block;max-width:910px}.article{max-width:910px}</style>')
    fragment.write_text(content)
result = {'unique_ids':len(parsed.ids),'anchor_links':sum(x.startswith('#') for x in parsed.links),
          'https_links':sum(x.startswith('https://') for x in parsed.links),'immutable_git_targets_checked':len(git_targets),
          'sections':16,'program_rows':35,'queue_rows':9,'experiment_rows':3,'javascript_syntax':'PASS',
          'report_sha256':hashlib.sha256(page.encode()).hexdigest(),
          'qa_fragments':'Copies only; main report order unchanged; no browser/server used'}
(ROOT / 'context/19_report_update_20261110/static_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
# Deep excerpts and a full-page layout probe use the same current CSS and content.
assert all(link.startswith(('#', 'https://github.com/Mput13/case_championship/')) for link in parsed.links)
assert len(re.findall(r'class="ranking-case"', page)) == 10
assert len(re.findall(r'class="person-card"', page)) == 4
assert '<table class="compact weights-table">' in page
metrics = """<script>console.log('LAYOUT_QA '+JSON.stringify({viewport:innerWidth,pageWidth:document.documentElement.scrollWidth,mainLeft:Math.round(document.querySelector('.article').getBoundingClientRect().left),mainRightGap:Math.round(innerWidth-document.querySelector('.article').getBoundingClientRect().right),sectionCount:document.querySelectorAll('section').length,programRows:document.querySelectorAll('[data-program]').length,rankCases:document.querySelectorAll('.ranking-case').length,clippedRanks:[...document.querySelectorAll('.rank-bar,.ranking-case')].filter(e=>e.scrollWidth>e.clientWidth+1).length,tocPosition:document.querySelector('.toc')?getComputedStyle(document.querySelector('.toc')).position:null}));</script>"""
(QA/'layout.html').write_text(page.replace('</body>',metrics+'</body>'))
def section(section_id):
    return re.search(r'<section id="'+section_id+r'">.*?</section>',page,re.S).group()
fragments={name:section(name) for name in ['issues','kover','next','access','sources']}
fragments['people-sources']=section('people')+section('sources')
t=section('team-context')
fragments['ranking']=t[t.index('<h3>Основной условный'):t.index('<h3>Веса и смысл')]
fragments['weights']=t[t.index('<h3>Веса и смысл'):t.index('<h3>500 км')]
fragments['weights-open']=fragments['weights'].replace('<details>','<details open>')
fragments['assumptions']=t[t.index('<h3>500 км'):]
t=section('change');fragments['economics']=t[t.index('<h3>Цири:'):]
for name,frag in fragments.items():
    doc='<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+style+'.layout{display:block;max-width:910px}.article{max-width:910px}</style><body><div class="layout"><main class="article">'+frag+'</main></div>'+metrics+'</body></html>'
    (QA/(name+'.html')).write_text(doc)
print('Current excerpts: '+', '.join(fragments))
