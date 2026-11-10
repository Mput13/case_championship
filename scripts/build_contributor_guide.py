#!/usr/bin/env python3
"""Embed the contributor guide and cited source texts in final_explain.html.

Requires markdown-it-py. Source snapshots are pinned Git objects; no network reads.
The source library is optional reading; the contributor chapter stays expanded.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import posixpath
import re
import subprocess
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'context/14_synthesis'
TARGET = ROOT / 'final_explain.html'
PUBLISHED = 'ad9010212a2158cdb86fc3d18539006531b0c711'
KIRUHA = 'bd807a44cab86a149519471b11f54f6d814d8d70'
REPO = 'https://github.com/Mput13/case_championship'
SOURCE_PATHS = [
    'context/07_verification/terra_data/samples/favt_regional_subsidy_2026.csv',
    'context/09_additional_research/report.md',
    'context/14_synthesis/analysis.md',
    *[f'context/14_synthesis/contributions/{name}/report.md' for name in (
        'city_screening', 'existing_context', 'kiruha', 'network_economics', 'user_network_report')],
    *[f'context/14_synthesis/inputs/{name}' for name in (
        'comparison_cost_thresholds.csv', 'inputs.json', 'manifest.json',
        'network_comparison.csv', 'operational_stress.csv')],
    'context/14_synthesis/inventory.json',
    'context/14_synthesis/knowledge.json',
    *[f'context/09_additional_research/{folder}/{name}' for folder in (
        'terra_similar_studies', 'terra_practical_tools', 'terra_network_cases')
        for name in ('report.md', 'sources.csv')],
]


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def git_source(ref: str, path: str) -> str:
    # Preserve CRLF in source hashes even though CSV rendering ignores line endings.
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT).decode('utf-8')


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def table(headers: list[str], rows: list[list[str]]) -> str:
    return '<div class="table-wrap"><table><thead><tr>' + ''.join(
        f'<th>{e(x)}</th>' for x in headers) + '</tr></thead><tbody>' + ''.join(
        '<tr>' + ''.join(f'<td>{x}</td>' for x in row) + '</tr>' for row in rows
    ) + '</tbody></table></div>'


def strip_generated(text: str, label: str) -> str:
    return re.sub(r'\n*<!-- BEGIN ' + label + r' -->.*?<!-- END ' + label + r' -->\n*', '\n', text, flags=re.S)


def block(label: str, content: str) -> str:
    return f'\n<!-- BEGIN {label} -->\n{content}\n<!-- END {label} -->\n'


def main() -> None:
    knowledge = json.loads((PACK / 'knowledge.json').read_text())
    audit = json.loads((PACK / 'contributions/kiruha/findings.json').read_text())
    sources: dict[tuple[str, str], dict] = {}
    for path in SOURCE_PATHS:
        sources[('local', path)] = {'text': git_source(PUBLISHED, path), 'ref': PUBLISHED}
    for doc in audit['documents']:
        path = doc['path']
        sources[('kiruha', path)] = {'text': git_source(KIRUHA, path), 'ref': KIRUHA}
    for (bundle, path), item in sources.items():
        item['id'] = 'source-' + hashlib.sha256(f'{bundle}/{path}'.encode()).hexdigest()[:12]
        item['url'] = f'{REPO}/blob/{item["ref"]}/{quote(path)}'
    tracked = {ref: set(git('ls-tree', '-r', '--name-only', ref).splitlines()) for ref in (PUBLISHED, KIRUHA)}

    def resolve(url: str, bundle: str = 'local', context: str = 'final_explain.html') -> str:
        url = html.unescape(url)
        if url.startswith('#'):
            return url
        parsed = urlsplit(url)
        if parsed.scheme == 'source':
            key = (parsed.netloc, unquote(parsed.path.lstrip('/')))
            return '#' + sources[key]['id']
        if url.startswith(REPO + '/blob/'):
            rest = url[len(REPO + '/blob/'):]
            ref, _, path = rest.partition('/')
            for key, item in sources.items():
                if item['ref'] == ref and key[1] == unquote(path.split('#')[0]):
                    return '#' + item['id']
            return url
        if parsed.scheme or parsed.netloc:
            return url
        path = posixpath.normpath(posixpath.join(posixpath.dirname(context), unquote(parsed.path)))
        key = (bundle, path)
        if key not in sources and ('local', path) in sources:
            key = ('local', path)
        if key in sources:
            return '#' + sources[key]['id']
        ref = KIRUHA if bundle == 'kiruha' else PUBLISHED
        if path in tracked[ref]:
            return f'{REPO}/blob/{ref}/{quote(path)}' + ('#' + parsed.fragment if parsed.fragment else '')
        # Some reports cite a file in the audited branch rather than this checkout.
        inventory = inventory_by_path.get(path)
        if inventory:
            return inventory['url']
        # An unresolved relative reference is text, never a dead navigation link.
        return ''

    inventory_by_path = {item['path']: item for item in json.loads((PACK / 'inventory.json').read_text())['entries']}

    def relink(markup: str, bundle: str = 'local', context: str = 'final_explain.html', preserve_original: bool = False) -> str:
        def replace(match: re.Match) -> str:
            before, url, after, label = match.groups()
            if preserve_original and 'data-original-source=' in before + after:
                return match.group(0)
            resolved = resolve(url, bundle, context)
            if not resolved:
                return label + f' <code class="source-path">{e(html.unescape(url))}</code>'
            return f'<a{before}href="{e(resolved)}"{after}>{label}</a>'
        return re.sub(r'<a([^>]*?)href="([^"]+)"([^>]*)>(.*?)</a>', replace, markup, flags=re.S)

    md = MarkdownIt('commonmark', {'html': False}).enable('table')

    # Author-authored narrative plus small generated tables grounded in registries.
    guide = md.render((PACK / 'contributor_guide.md').read_text())
    # Comments are escaped with html=False. They are controlled insertion markers.
    for marker in ('KIRUHA_ARTIFACTS', 'COMMON_HYPOTHESES', 'SCREENING_HYPOTHESES'):
        guide = guide.replace(f'<p>&lt;!-- {marker} --&gt;</p>', '<!-- ' + marker + ' -->')
    artifact_rows = []
    for doc in audit['documents']:
        path = doc['path']
        artifact_rows.append([
            f'<a href="source://kiruha/{e(path)}"><code>{e(path)}</code></a>', e(doc['summary'])])
    guide = guide.replace('<!-- KIRUHA_ARTIFACTS -->', table(['Артефакт — полный текст внутри документа', 'Содержание и роль'], artifact_rows))
    guide = guide.replace('<!-- COMMON_HYPOTHESES -->', table(
        ['Карточка', 'Механизм и проверка', 'Что может опровергнуть'], [
            [e(x['Гипотеза']), e(x['Механизм и нужный вход']), e(x['Что может опровергнуть'])]
            for x in knowledge['existing_hypothesis_cards']]))
    guide = guide.replace('<!-- SCREENING_HYPOTHESES -->', table(
        ['Гипотеза', 'Механизм', 'Условие подтверждения / следующий вход'], [
            [e(x['id'] + ': ' + x['hypothesis']), e(x['mechanism']),
             e(x['confirmation_test']) + '<br><br>' + e(x['next_action'])]
            for x in knowledge['screening_hypotheses']]))
    guide = guide.replace('<h1>Вклад участников: материалы, гипотезы и расчёты</h1>',
        '<div class="chapter-header"><span class="chapter-num">Глава 14 · Участники</span>'
        '<h2>Вклад участников: материалы, гипотезы и расчёты</h2></div>')
    for title, anchor in (
        ('kiruha355: варианты стратегии и широкая карта факторов', 'author-kiruha'),
        ('mput / Mput13: общий контекст, города и расчёт сети', 'author-mput'),
        ('Константин Тарасенко: методы, инструменты и аналоги', 'author-konstantin'),
        ('Как соединяются три вклада', 'team-next-experiments'),
    ):
        guide = guide.replace(f'<h2>{title}</h2>', f'<h2 id="{anchor}" class="author-heading">{title}</h2>')
    guide = '<section class="chapter contributor-guide" id="ch14">' + relink(guide, context='context/14_synthesis/contributor_guide.md') + '</section>'

    library = ['<div id="embedded-sources"><h3>Полные тексты и таблицы</h3>',
        '<p>Ссылки на материалы открывают встроенную копию. '
        'В исходных исследованиях сохранены и проверенные сведения, и авторские допущения: '
        'встроенный оригинал не получает статус подтверждённого факта только из-за публикации. '
        'Рядом доступна закреплённая версия в GitHub.</p>']
    source_manifest = []
    for (bundle, path), item in sources.items():
        source_manifest.append({'bundle': bundle, 'path': path, 'ref': item['ref'],
            'anchor': item['id'], 'sha256': hashlib.sha256(item['text'].encode()).hexdigest()})
        library.append(f'<details class="embedded-source" id="{item["id"]}"><summary>{e(path)}'
            + (' · kiruha355' if bundle == 'kiruha' else '') + '</summary>'
            + f'<p><a href="{e(item["url"])}" data-original-source="true" target="_blank" rel="noopener">'
            + f'Оригинал в GitHub · {item["ref"][:8]}</a></p>')
        if path.endswith('.md'):
            source_html = md.render(item['text'])
            # Prefix source headings to prevent collisions with the document navigation.
            headings: dict[str, str] = {}
            count = 0
            def heading(match: re.Match) -> str:
                nonlocal count
                count += 1
                level, label = match.groups()
                plain = html.unescape(re.sub('<[^>]+>', '', label))
                slug = re.sub(r'[^\w\- ]', '', plain.lower()).replace(' ', '-')
                hid = item['id'] + '-h' + str(count)
                headings[slug] = hid
                return f'<h{min(6, int(level) + 2)} id="{hid}">{label}</h{min(6, int(level) + 2)}>'
            source_html = re.sub(r'<h([1-6])>(.*?)</h\1>', heading, source_html, flags=re.S)
            source_html = relink(source_html, bundle, path)
            def source_fragment(match: re.Match) -> str:
                anchor = html.unescape(match[1])
                if anchor.startswith('source-'):
                    return match[0]
                return 'href="#' + headings.get(unquote(anchor), item['id']) + '"'
            source_html = re.sub(r'href="#([^\"]+)"', source_fragment, source_html)
            source_html = source_html.replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
            library.append('<div class="source-content">' + source_html + '</div>')
        elif path.endswith('.csv'):
            rows = list(csv.reader(io.StringIO(item['text'])))
            library.append(table(rows[0], [[e(v) for v in row] for row in rows[1:]]))
        else:
            library.append('<pre class="source-raw" tabindex="0" aria-label="Полное содержимое ' + e(path)
                + '"><code>' + e(item['text']) + '</code></pre>')
        library.append('</details>')
    library.append('</div>')

    text = TARGET.read_text()
    for name in ('CONTRIBUTOR_GUIDE', 'SOURCE_LIBRARY', 'SOURCE_BEHAVIOR', 'CONTRIBUTOR_STYLE'):
        text = strip_generated(text, name)
    old_intro = '<p>При расхождении источников приоритет у <a href="context/14_synthesis/analysis.md">проверенного анализа</a>, затем у последнего датированного исправленного расчёта. Подробные реестры сохраняют происхождение и степень уверенности. Исследование, присланное пользователем, рассматривается как набор аргументов и гипотез, а не независимое доказательство.</p>'
    text = text.replace(old_intro,
        '<p>В общей части идеи были сгруппированы по темам; это не полный авторский перечень. '
        '<a href="#ch14">Вклад каждого участника и все исходные группы гипотез</a> разобраны в следующей главе. '
        'При расхождении сверяем конкретное утверждение, дату, единицу и первоисточник; '
        'замечание к числу не отменяет саму идею. Ниже сохранены полные материалы и результаты проверки.</p>')
    text = text.replace('все проверенные наработки команды:', 'наработки команды с разделением фактов, допущений и предложений:')
    text = text.replace('Отобранные карточки K052–K075', 'Карточки гипотез из диапазона K052–K075; исходный список G/Н — в главе 14')
    text = text.replace('Оглавление документа (13 глав)', 'Оглавление документа (14 глав)')
    toc = '<li><a href="#ch14">14. Вклад трёх участников</a></li>\n'
    toc += '<li class="author-toc"><a href="#author-kiruha">kiruha355 · стратегии и гипотезы</a></li>\n'
    toc += '<li class="author-toc"><a href="#author-mput">mput · данные и расчёты</a></li>\n'
    toc += '<li class="author-toc"><a href="#author-konstantin">Константин · методы</a></li>'
    if '14. Вклад трёх участников' not in text:
        text = text.replace('<li><a href="#ch13">13. Приложение: полный каталог</a></li>',
            '<li><a href="#ch13">13. Приложение: полный каталог</a></li>\n' + toc)
    # Keep the original chapters; add the source library at the end of chapter 13.
    end13 = text.rfind('</section>', 0, text.index('  </main>'))
    text = text[:end13] + block('SOURCE_LIBRARY', '\n'.join(library)) + text[end13:]
    text = text.replace('  </main>', block('CONTRIBUTOR_GUIDE', guide) + '  </main>')
    text = relink(text, preserve_original=True)
    style = '''<style>
      .author-heading { margin-top: 3.5rem; padding-top: 1.5rem; border-top: 2px solid var(--border-col); scroll-margin-top: 4rem; }
      .contributor-guide h3 { margin-top: 2rem; }
      .contributor-guide table { min-width: 0; }
      .contributor-guide td { vertical-align: top; }
      .author-toc { font-size: .82rem; padding-left: .7rem; }
      .embedded-source { margin: 1rem 0; scroll-margin-top: 4rem; }
      .embedded-source > summary { overflow-wrap: anywhere; font-family: var(--doc-font-mono); font-size: .83rem; }
      .embedded-source:target { outline: 2px solid var(--accent-col); outline-offset: 5px; }
      .source-content { border-left: 2px solid var(--border-col); padding-left: 1rem; }
      .source-content pre, .source-raw { white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }
      .source-raw { max-height: 28rem; overflow: auto; }
      .source-path { overflow-wrap: anywhere; }
      .source-content a { overflow-wrap: anywhere; }
      @media (max-width: 640px) {
        .contributor-guide table, .contributor-guide thead, .contributor-guide tbody, .contributor-guide tr, .contributor-guide td { display: block; }
        .contributor-guide thead { display: none; }
        .contributor-guide tr { border-bottom: 1px solid var(--border-col); padding: .7rem 0; }
        .contributor-guide td { border: 0; padding: .4rem .35rem; }
        .contributor-guide td:first-child { font-weight: 650; }
        .contributor-guide td[data-column]::before { content: attr(data-column) ": "; display: block; font-size: .78rem; color: var(--muted-fg); font-weight: 500; }
      }
    </style>'''
    script = '''<script>
    (() => {
      function revealSource() {
        let id;
        try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
        const target = document.getElementById(id);
        if (!target) return;
        for (let node = target; node; node = node.parentElement) {
          if (node.tagName === 'DETAILS') node.open = true;
        }
        const menu = document.querySelector('.mobile-toc');
        if (menu && !menu.contains(target)) menu.open = false;
        requestAnimationFrame(() => target.scrollIntoView({block: 'start'}));
      }
      document.querySelectorAll('.contributor-guide table').forEach(table => {
        const labels = Array.from(table.querySelectorAll('thead th'), th => th.textContent);
        table.querySelectorAll('tbody tr').forEach(row => {
          Array.from(row.cells).forEach((cell, i) => { if (i > 0 && labels[i]) cell.dataset.column = labels[i]; });
        });
      });
      addEventListener('hashchange', revealSource);
      document.addEventListener('click', event => {
        const link = event.target.closest('a[href^="#"]');
        if (link && link.getAttribute('href') === location.hash) revealSource();
      });
      revealSource();
    })();
    </script>'''
    text = text.replace('</head>', block('CONTRIBUTOR_STYLE', style) + '</head>')
    text = text.replace('</body>', block('SOURCE_BEHAVIOR', script) + '</body>')
    TARGET.write_text(text)
    manifest = {
        'date': '2026-11-09',
        'attribution': [
            {'git_author': 'kiruha355', 'commits': ['89663d4', KIRUHA]},
            {'git_author': 'mput / Mput13', 'commits': ['66bd7c6', 'cdefb6b', 'f4b8e32', '26e0b85', '91fdbe1', PUBLISHED]},
            {'git_author': 'Konstantin Tarasenko', 'commits': ['d3593c3', 'ec01770']},
        ],
        'attribution_limit': 'Git authorship identifies the contributor of the package, not exclusive intellectual authorship; inherited ideas remain marked.',
        'coverage': {'kiruha_strategies': [f'G{i}' for i in range(1, 7)],
                     'kiruha_hypotheses': [f'Н{i}' for i in range(1, 14)],
                     'screening': [f'H{i}' for i in range(1, 7)],
                     'common_context': [f'H{i:02d}' for i in range(1, 12)],
                     'supplementary': [f'KON{i:02d}' for i in range(1, 9)],
                     'kiruha_documents': len(audit['documents'])},
        'embedded_sources': source_manifest,
        'html_sha256': hashlib.sha256(text.encode()).hexdigest(),
    }
    (PACK / 'contributor_coverage.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'Built chapter 14 and {len(sources)} embedded sources; {len(text.encode()):,} bytes')


if __name__ == '__main__':
    main()
