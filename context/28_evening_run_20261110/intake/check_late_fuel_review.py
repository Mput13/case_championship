import gzip
import hashlib
import json
import math
import subprocess
from pathlib import Path

REVIEW = 'c5ec29f7a89e457ed104026877b8f8d3b6101ca9'
SCOPE = 'context/28_evening_run_20261110/late_fuel_review/'
ROOT = Path(__file__).resolve().parents[1]

def blob(commit, path):
    return subprocess.check_output(['git', 'show', f'{commit}:{path}'])

def verify(data, row):
    assert len(data) == row['bytes'], row['path']
    assert hashlib.sha256(data).hexdigest() == row['sha256'], row['path']

def close(a, b):
    assert math.isclose(a, b, abs_tol=0.0001, rel_tol=1e-10), (a, b)

outputs = json.loads(blob(REVIEW, SCOPE + 'output_manifest.json'))
for row in outputs:
    verify(blob(REVIEW, SCOPE + row['path']), row)
sources = json.loads(blob(REVIEW, SCOPE + 'source_manifest.json'))
git_count = 0
for row in sources:
    if row.get('commit'):
        data = blob(row['commit'], row['path'])
        verify(data, row)
        actual = subprocess.check_output(['git', 'rev-parse', f"{row['commit']}:{row['path']}"], text=True).strip()
        assert actual == row['git_blob']
        git_count += 1
    else:
        assert row['pin'] == 'gzip_derivative'
        gz = next(x for x in sources if x['pin'] == 'frozen_methods_raw')
        verify(gzip.decompress(blob(gz['commit'], gz['path'])), row)

d = json.loads(blob(REVIEW, SCOPE + 'calculation.json'))
close(sum(d['monthly_precise_series']) / 9, d['monthly_precise_mean'])
assert round(d['monthly_precise_mean']) == 32930
for key in ['fixed_old_network', 'fixed_new_network']:
    rows = d[key]
    assert len(rows) == 3 and [r['credit_rub_per_t'] for r in rows] == [0, 3024, 32930]
    base = rows[0]
    for r in rows:
        assert r['routes'] == base['routes']
        for field in ['flights_week', 'hours_week', 'fuel_tonnes_year', 'revenue_rub', 'annual_segments']:
            close(r[field], base[field])
        tonnes = sum(2 * leg['freq_each_way'] * 52 * (1.55 * leg['block_h'] + 0.20) for leg in r['legs'])
        close(tonnes, r['fuel_tonnes_year'])
        close(tonnes * 134896, r['fuel_gross_rub'])
        close(tonnes * r['credit_rub_per_t'], r['credit_rub'])
        close(r['fuel_gross_rub'] + r['nonfuel_cost_rub'] - r['credit_rub'], r['cost_rub'])
        close(r['revenue_rub'] - r['cost_rub'], r['contribution_rub'])
        close(base['contribution_rub'] + tonnes * r['credit_rub_per_t'], r['contribution_rub'])
        close(-base['contribution_rub'] / tonnes, r['credit_breakeven_rub_per_t'])
old0, old = d['fixed_old_network'][0], d['fixed_old_network'][2]
new = d['fixed_new_network'][2]
fuel_effect = old['contribution_rub'] - old0['contribution_rub']
selection_effect = new['contribution_rub'] - old['contribution_rub']
close(fuel_effect + selection_effect, new['contribution_rub'] - old0['contribution_rub'])
noz = next(x for x in d['route_deletion_examples'] if x['route'] == 'NOZ')
assert noz['allocated_contribution_rub'] < 0 < noz['full_minus_without_contribution_rub']
goj = next(x for x in old['legs'] if x['to'] == 'GOJ')
close((1.55 * goj['block_h'] + 0.2) * 2 * goj['freq_each_way'] * 52, goj['fuel_tonnes_year'])
result = {'review_sha': REVIEW, 'subject_sha': 'dc1eb38d4c6b7c18386b3db4b1750166bb010ffd',
          'status': 'ROOT_INTAKE_PASS_SCOPED', 'output_hashes': len(outputs), 'git_sources': git_count,
          'gzip_derivative_hashes': 1, 'fixed_network_rows': 6, 'real_example': goj,
          'fixed_old_fuel_effect_rub': fuel_effect, 'same_credit_selection_effect_rub': selection_effect,
          'NOZ_allocation_not_marginal': noz,
          'limits': ['Not full solver replay', 'Not actual RW tax eligibility/payment',
                     'Not 2027/28 forecast, physical resource/MCT or full PnL/cash',
                     'Route grant/fare CHANGES remains separate', 'Frozen prior results unchanged']}
(ROOT / 'intake/late_fuel_review_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['status', 'output_hashes', 'git_sources', 'fixed_network_rows']}))
