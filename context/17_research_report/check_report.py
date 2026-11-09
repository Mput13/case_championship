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
QA = Path(__file__).resolve().parent / 'qa'
QA.mkdir(exist_ok=True)
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
assert len(re.findall(r'<section id=', page)) == 14
script = re.search(r'<script>(.*?)</script>', page, re.S).group(1)
(QA / 'report.js').write_text(script)
subprocess.run(['node', '--check', str(QA / 'report.js')], check=True)
style = re.search(r'<style>(.*?)</style>', page, re.S).group(1)
for name, start, end in [('c14', 'c14', 'c01'), ('c01-c07', 'c01', 'issues'),
                         ('programs', 'programs', 'c14'), ('change', 'change', 'next'),
                         ('method', 'method', 'programs')]:
    fragment = page[page.index('<section id="' + start + '"'):page.index('<section id="' + end + '"')]
    body = f'<main class="article">{fragment}</main>'
    (QA / f'{name}.html').write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>' + style + '</style><body><div class="layout">' + body + '</div></body></html>')
# The deep-section copies keep source content/order, but use the full article column.
for fragment in QA.glob('*.html'):
    content = fragment.read_text().replace('</style>', '.layout{display:block;max-width:910px}.article{max-width:910px}</style>')
    fragment.write_text(content)
result = {'unique_ids':len(parsed.ids),'anchor_links':sum(x.startswith('#') for x in parsed.links),
          'https_links':sum(x.startswith('https://') for x in parsed.links),'immutable_git_targets_checked':len(git_targets),
          'sections':14,'program_rows':35,'queue_rows':9,'experiment_rows':3,'javascript_syntax':'PASS',
          'report_sha256':hashlib.sha256(page.encode()).hexdigest(),
          'qa_fragments':'Copies only; main report order unchanged; no browser/server used'}
(Path(__file__).resolve().parent / 'static_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
