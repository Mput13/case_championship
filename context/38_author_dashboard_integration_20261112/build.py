#!/usr/bin/env python3
"""Keep the published author dashboard intact; append accepted research data/views."""
import hashlib, json, pathlib, subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUTHOR = '6cbe817320f75db9823984e7c4eeb6091fd7d996'
P15 = ROOT / 'context/35_full_programme_execution_20261112/P15'
sha = lambda b: hashlib.sha256(b).hexdigest()

def main():
    author = subprocess.check_output(['git', 'show', AUTHOR + ':outputs/redwings_panel.html'], cwd=ROOT)
    assert author == (HERE / 'author_original.html').read_bytes()
    data = json.loads((P15 / 'dashboard_data.json').read_text())
    payload = {'results': data['lazy_results'], 'products': data['products']}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    (HERE / 'canonical_data.json').write_text(encoded + '\n')
    js = (HERE / 'canonical.js').read_text()
    # Exact published CSS, markup and model code remain in the original block.
    # The added module uses author components and labels the two scopes separately.
    html = '<!doctype html><html lang="ru">\n' + author.decode() + '\n'
    html += '<script id="accepted-research-data" type="application/json">' + encoded.replace('</', '<\\/') + '</script>\n'
    html += '<script>\n' + js + '\n</script>\n</html>\n'
    (HERE / 'dashboard.html').write_text(html)
    entry = HERE / 'redwings_panel.html'
    if entry.is_symlink():
        entry.unlink()
    entry.write_text(html)
    old = subprocess.check_output(['git', 'show', AUTHOR + ':outputs/redwings_panel_v1.html'], cwd=ROOT)
    (HERE / 'redwings_panel_v1.html').write_bytes(old)
    inputs = {'author_commit': AUTHOR, 'author_path': 'outputs/redwings_panel.html',
              'author_bytes': len(author), 'author_sha256': sha(author),
              'P15_data_sha256': sha((P15 / 'dashboard_data.json').read_bytes()),
              'P09_commit': payload['results']['commit'],
              'P09_manifest_sha256': payload['results']['manifest_sha256'],
              'design_rule': 'Unchanged complete author dashboard; no P15 CSS, layout, navigation or theme overrides.',
              'model_rule': 'Original model kept as historical model. Accepted P09 remains a separate exact projection; no financial recomputation.',
              'strategy_correction': 'City alternatives are not a sequential multi-hub opening programme. Joint multi-hub economics not calculated.'}
    (HERE / 'input_manifest.json').write_text(json.dumps(inputs, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'html_bytes': len(html.encode()), 'html_sha256': sha(html.encode()), 'author_sha256': sha(author)}))

if __name__ == '__main__':
    main()
