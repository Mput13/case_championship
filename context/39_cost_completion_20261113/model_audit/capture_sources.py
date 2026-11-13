#!/usr/bin/env python3
"""One-time exact git object capture. Writes only beside this script."""
from pathlib import Path
import csv,hashlib,io,json,subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OWNER='c11eb8c15d32add540d89d086f62487a5b2d424e'
P38='56400c5f111222d7c660d4345d3d43b92d4716d5'
manifest=[]
def capture(rev,path,select=None):
 data=subprocess.check_output(['git','show',f'{rev}:{path}'],cwd=ROOT)
 dest=HERE/'snapshot'/rev[:8]/path
 item=dict(commit=rev,path=path,source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),selection='FULL')
 if select:
  lines=data.decode().splitlines(keepends=True)
  rows=list(csv.DictReader(io.StringIO(data.decode())))
  indexes=[i+2 for i,r in enumerate(rows) if select(r)]
  assert len(lines)==len(rows)+1,'multiline CSV requires different line mapping'
  data=(lines[0]+''.join(lines[i-1] for i in indexes)).encode()
  item.update(selection='EXACT_HEADER_AND_SELECTED_SOURCE_LINES',source_line_numbers=[1]+indexes)
  dest=dest.with_name(dest.stem+'.selected.csv')
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 item.update(snapshot_path=str(dest.relative_to(HERE)),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
 manifest.append(item)
for p in ['src/network_model.py','src/demand_model.py','src/rules.py','src/airports_meta.py']+[f'data/assumptions/{p}.csv' for p in ['network','subsidy_hub_airports','siberia_fareast_regions','subsidy_cap_84_103','subsidy_special_fare','resort_airports','demand','range','south_west_regions','bases','longlist_params']]+[f'data/processed/{p}' for p in ['catchments.csv','od_pairs.csv','od_fit.json','demand_estimates.csv','demand_pairs.csv','network_routes.csv','network_summary.csv']]+['data/manual/closed_airports.csv','data/manual/airport_names.csv','data/manual/rw_routes_now.csv','data/raw/favt_subsidy_2026.csv']:
 capture(OWNER,p)
for p in ['economics/core.py','economics/calculate.py','economics/finalist_months.py','contract/month_adapter.py','contract/common_contract.json','contract/resource_contract.json','economics/README.md','economics/config.json','review/findings.csv','economics/three_finalists_ledger.csv','economics/three_finalists_monthly.csv','economics/three_finalists_weekly.csv']:
 capture(P38,'context/38_direct_strategy_20261113/'+p)
finalists={'C0121723','W7324a9b711d148bebb00/V0','Wa17798465f19ba7addfb/V0'}
for p in ['annual_results.csv','programmes_monthly.csv']:
 capture(P38,'context/38_direct_strategy_20261113/economics/'+p,lambda r:r['candidate'] in finalists)
for p in ['context/31_direct_growth_research_20261112/route_economics/calculate.py','context/31_direct_growth_research_20261112/audit/inputs/audit_model/620a0ac4/context/35_full_programme_execution_20261112/P04/cost_ranges.csv','context/31_direct_growth_research_20261112/audit/inputs/audit_model/a63a047b/context/35_full_programme_execution_20261112/P05/model.py','context/30_defense_research_20261111/review_costs/review.md','context/30_defense_research_20261111/review_costs/accepted_cost_inputs.csv','context/30_defense_research_20261111/economics/README.md','context/30_defense_research_20261111/economics/baseline_ledger.csv']:
 capture(P38,p)
for p in ['README.md','material_findings.csv','replay/cost_coverage.csv','replay/inputs/README.md']:
 capture('5905f8e8655cfdf2cd3ab5326dfec1df8bb98961','context/27_oms388_independent_audit_20261110/'+p)
# Public raw is absent from owner git; exact archived package has owner manifest's uncompressed SHA.
capture('5905f8e8655cfdf2cd3ab5326dfec1df8bb98961','context/27_oms388_independent_audit_20261110/replay/inputs/tochno_intercity.csv.gz')
for obsolete in ['snapshot/56400c5f/context/38_direct_strategy_20261113/economics/input_manifest.json','snapshot/56400c5f/context/38_direct_strategy_20261113/economics/annual_results.csv']:
 (HERE/obsolete).unlink(missing_ok=True)
(HERE/'snapshot_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(files=len(manifest),bytes=sum(x['bytes'] for x in manifest))))
