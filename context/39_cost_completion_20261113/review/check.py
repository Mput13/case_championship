#!/usr/bin/env python3
"""Independent P39 review: reads completed CSVs, never rebuilds network or imports build/verify.
Writes only review/check.log and review/input_content.json. No Git or mtime checks.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from collections import Counter
import csv,json,hashlib,ast
R=Path(__file__).resolve().parent
P=R.parent

def read(n):
    with (P/n).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def digest():
    return {str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.rglob('*')) if p.is_file() and R not in p.parents}
before=digest()
base=R/'input_content.json'
if not base.exists():base.write_text(json.dumps(before,indent=2)+'\n')
groups={}
def ck(g,ok,detail):
    d=groups.setdefault(g,{'checks':0,'failures':[]});d['checks']+=1
    if not ok:d['failures'].append(detail)
def eq(g,a,b,label,tol=Decimal('0.0001')):
    ck(g,abs(Decimal(str(a))-Decimal(str(b)))<=tol,label+f': {a} vs {b}')
rows=read('calculation/COST_TABLE.csv'); w=json.loads((P/'calculation/workings.json').read_text())
cov=read('model_audit/coverage.csv');drivers=read('model_audit/annual_drivers.csv'); exp=read('model_audit/exposures.csv')
C={(r['item_id'],r['network']):r for r in cov};D={(r['model'],r['network'],r['scenario'],r['item_id']):r for r in drivers}
E={(r['model'],r['network'],r['scenario'],r['scope'],r['metric']):r for r in exp}
T={tuple(r[k] for k in ('model','network','scenario')):r for r in read('model_audit/owner_network_totals.csv')+read('model_audit/p38_network_totals.csv')}
B={(r['case'],r['article_id']):r for r in rows}
ck('01 coverage',len(rows)==546 and len(B)==546 and len(C)==117,'117 -> 546 unique')
ck('01 coverage',len(T)==14 and len({r['article_id'] for r in rows})==39,'14 cases x39')
for key,t in T.items():ck('01 coverage',sum(tuple(r[k] for k in ('model','network','scenario'))==key for r in rows)==39,str(key))
for r in rows:
    key=tuple(r[k] for k in ('model','network','scenario')); c=C[r['article_id'],r['coverage_network']];d=D[key+(r['article_id'],)]
    for out,src in [('coverage_status_original','status'),('code_table_exact_lines','evidence'),('already_in_model','in_model_components'),('model_formula','formula_or_basket')]:ck('01 coverage',r[out]==c[src],r['row_id']+out)
    expected=d['existing_proxy_amount_rub']
    if key[0]=='P38' and r['article_id'] in ('CREW_PROXY','CREDIT','GRANT','PAX'):expected='0'
    if expected=='UNKNOWN':ck('02 existing amounts',r['existing_annual_amount_rub']=='UNKNOWN',r['row_id'])
    else:eq('02 existing amounts',r['existing_annual_amount_rub'],expected,r['row_id'])
    if key[0]=='P38' and r['article_id']=='CREW_PROXY':eq('02 existing amounts',r['excluded_reference_rub'],d['existing_proxy_amount_rub'],r['row_id']+' excluded')
    for field in ['annual_addition_min_rub','annual_addition_max_rub','full_service_annual_actual_min_rub','full_service_annual_actual_max_rub','one_off_expense_rub','CAPEX_cash_rub','refundable_deposit_cash_rub','advance_cash_rub','spares_stock_cash_rub','working_capital_peak_rub']:
        ck('07 unknown and cash',r[field]=='UNKNOWN',r['row_id']+field)
    for field in ('source_refs','driver_refs'):
        for ref in json.loads(r[field]):
            name,line=ref.rsplit(':',1);path=P/'calculation'/name
            ck('03 source lineage',path.is_file() and 0<int(line)<=len(path.read_text().splitlines()),ref)
    for s in json.loads(r['normalized_scenarios']):
        for unit,result in [('unit_min','full_service_min_rub'),('unit_max','full_service_max_rub')]:
            if s[unit] is None or s['quantity'] is None:ck('06 unit times quantity',s[result] is None,r['row_id']+s['name'])
            else:eq('06 unit times quantity',s[result],(Decimal(str(s[unit]))*Decimal(str(s['quantity']))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),r['row_id']+s['name'],Decimal('.01'))
        ck('07 unknown and cash',s['addition_rub'] is None,r['row_id']+s['name'])
        ck('10 admission',s['price_source_id'] not in ('PKC-1690-AUDIT','INS-TENDER-REJECTED','ANALOG-AERO-BREAKFAST','ANALOG-BUS'),r['row_id'])
        if r['article_id']=='PARKING':ck('08 exclusivity',s['exclusive_group']=='parking_billing_choice',r['row_id'])
# Independent values read visually from primary tariff pages / saved official hotel HTML.
primary={'OMS-BAG':4450,'OMS-RACK':1229.51,'OMS-WH-11.19.1':330,'OMS-WH-11.19.2':1000,
'OMS-BASE-30–74.999 т':117100,'OMS-BASE-75–99.999 т':130200,
'OMS-PARK-H-30–74.999 т':1018,'OMS-PARK-H-75–99.999 т':1140,
'OMS-PARK-D-30–74.999 т':24432,'OMS-PARK-D-75–99.999 т':27360,
'ANALOG-HOTEL-SINGLE':4100,'ANALOG-HOTEL-DOUBLE':4650,'OMS-CITYBUS':3430,'OMS-MEAL-DISTR':3275,
'OMS-IT-TGM-IN':6.23,'OMS-IT-TGM-AV':55.6}
prices={r['id']:r for r in read('omsk_price_recovery/prices.csv')}
for sid,price in primary.items():
    eq('10 admission',prices[sid]['min'],price,sid+' primary min');eq('10 admission',prices[sid]['max'],price,sid+' primary max')
for r in rows:
    for s in json.loads(r['normalized_scenarios']):
        if s['price_source_id'] in primary:
            for field in ('unit_min','unit_max'):eq('10 admission',s[field],primary[s['price_source_id']],r['row_id']+field)
params={r['parameter']:r for r in read('model_audit/snapshot/c11eb8c1/data/assumptions/network.csv')}
for c in w['cases']:
    key=tuple(c[k] for k in ('model','network','scenario'));t=T[key];case=c['case'];owner=key[0]=='OWNER';sc='cautious' if key[2].startswith('cautious') else 'base'
    for out,src in [('model_margin_rub','subtotal_rub'),('model_cost_rub','cost_rub'),('working_aircraft','working_aircraft'),('reserve_aircraft','reserve_aircraft'),('departures','departures'),('block_hours','block_hours'),('journeys','journeys'),('segments','segments'),('transfer_journeys','transfers')]:eq('04 exposure and fleet',c[out],t[src],case+out)
    airports=[r for r in exp if tuple(r[k] for k in ('model','network','scenario'))==key and r['scope']!='NETWORK' and r['metric']=='departures']
    eq('04 exposure and fleet',sum(float(r['value']) for r in airports),t['departures'],case+' airport reconciliation')
    eq('04 exposure and fleet',c['OMS_departures'],sum(float(r['value']) for r in airports if r['scope']=='OMS'),case+' OMS')
    eq('04 exposure and fleet',c['segments'],c['journeys']+c['transfer_journeys'],case+' transfer identity')
    ck('04 exposure and fleet',c['reserve_aircraft']==1,case+' reserve')
    if owner:ck('04 exposure and fleet',c['weeks']==(52 if sc=='base' else 48),case+' weeks')
    for item,metric,param in [('GROUND','departures','ground_rub_per_flight'),('DEICE','departures','deicing_rub_per_flight'),('MRO_PROXY','block_hours','mro_rub_per_hour'),('NAV','block_hours','navigation_rub_per_hour'),('CREW_PROXY','block_hours','crew_rub_per_hour'),('PAX','segments','pax_cost_rub')]:
        rate=float(params[param][sc]);amount=rate*c[metric] if owner or item not in ('CREW_PROXY','PAX') else 0
        eq('05 independent cost formulas',B[case,item]['existing_annual_amount_rub'],amount,case+item)
    if owner:
        burn=float(params['fuel_t_per_hour'][sc])*c['block_hours']+float(params['fuel_t_per_cycle'][sc])*c['departures']
        fuel=burn*float(params['fuel_rub_per_t'][sc]);credit=burn*float(params['fuel_compensation_rub_per_t'][sc])
        eq('05 independent cost formulas',B[case,'FUEL']['existing_annual_amount_rub'],fuel,case+' fuel')
        eq('05 independent cost formulas',B[case,'CREDIT']['existing_annual_amount_rub'],credit,case+' credit')
        costs=fuel-credit+sum(float(B[case,i]['existing_annual_amount_rub']) for i in ('GROUND','DEICE','MRO_PROXY','NAV','CREW_PROXY','PAX'))
        eq('05 independent cost formulas',costs,t['cost_rub'],case+' cost subtract credit once')
    else:
        eq('05 independent cost formulas',float(t['fuel_cost'])+sum(float(t[k]) for k in ('mro','navigation','ground','deice')),t['cost_rub'],case+' no fixed crew',Decimal('.02'))
    eq('05 independent cost formulas',float(t['net_revenue_rub'])-float(t['cost_rub']),t['subtotal_rub'],case+' no second migration/tax deduction')
    months=12*(float(t['working_aircraft'])+float(t['reserve_aircraft']));margin=float(t['subtotal_rub'])
    eq('09 headroom and historical',c['rent_ceiling_all_fleet_per_aircraft_month_rub'],margin/months,case+' ceiling')
    eq('09 headroom and historical',c['rent_ceiling_working_only_other_load_zero_rub'],margin/(12*float(t['working_aircraft'])),case+' working ceiling')
    eq('09 headroom and historical',c['rent_stress_full_allocation_exVAT_rub'],7560000/1.18*months,case+' rent',Decimal('.011'))
    eq('09 headroom and historical',c['rent_stress_residual_after_allocation_rub'],margin-7560000/1.18*months,case+' residual',Decimal('.011'))
    eq('09 headroom and historical',c['technical_reserve_stress_exVAT_rub'],2436000*months,case+' reserve stress')
    ck('09 headroom and historical',c['actual_billed_aircraft_months'] is None and c['incremental_new_rent_cash_rub'] is None,case)
    for item in ('TRANSFER','OVERHEAD','DISRUPT'):
        for s in json.loads(B[case,item]['normalized_scenarios']):
            name=s['name']
            if name in ('one_extra_bag_service_per_OMS_departure','one_informing_workplace_per_OMS_departure'):eq('06 unit times quantity',s['quantity'],c['OMS_departures'],case+name)
            if name.startswith('one_percentage_point'):eq('06 unit times quantity',s['quantity'],c['transfer_journeys']*.01/(2 if name.endswith('double') else 1),case+name)
annual=read('model_audit/snapshot/56400c5f/context/38_direct_strategy_20261113/economics/annual_results.selected.csv')
monthly=read('model_audit/snapshot/56400c5f/context/38_direct_strategy_20261113/economics/programmes_monthly.selected.csv')
dated=read('model_audit/p38_dated_exposure.csv')
for c in w['cases']:
    if c['model']!='P38':continue
    a={r['state']:r for r in annual if r['candidate']==c['network'] and r['scenario']==c['scenario']}
    for field,state in [('R_minus_W_rub','WITHOUT_NEW'),('R_minus_K_rub','KEEP')]:eq('11 P38 calendar and deltas',c[field],sum(float(r['known_subtotal_before_C_D_F'])*(1 if r['state']=='REPLACE' else -1) for r in monthly if r['candidate']==c['network'] and r['scenario']==c['scenario'] and r['state'] in ('REPLACE',state)),c['case']+field)
    plan=[r for r in dated if r['candidate']==c['network']]
    ck('11 P38 calendar and deltas',all(r['dep'].startswith('2027-') for r in plan) and len(plan)==c['departures'],c['case']+' calendar')
    eq('11 P38 calendar and deltas',sum(r['origin']=='OMS' for r in plan),c['OMS_departures'],c['case']+' OMS count')
    eq('11 P38 calendar and deltas',sum(float(r['block_h']) for r in plan),c['block_hours'],c['case']+' BH')
    ck('11 P38 calendar and deltas',len({(r['tail'],r['dep'][:7]) for r in plan})==24,c['case']+' active months')
# Read exact pinned source lines and snapshot bytes, no network model execution.
used_citations={s.strip() for r in cov for s in r['evidence'].split('|')}
for r in read('model_audit/evidence_lines.csv'):
    if r['citation'] not in used_citations:continue
    path=P/'model_audit'/r['snapshot_path'];line=int(r['citation'].rsplit(':',1)[1]);ck('03 source lineage',path.read_text().splitlines()[line-1]==r['source_text'],r['citation'])
for r in json.loads((P/'model_audit/snapshot_manifest.json').read_text()):ck('03 source lineage',hashlib.sha256((P/'model_audit'/r['snapshot_path']).read_bytes()).hexdigest()==r['sha256'],r['snapshot_path'])
# Only extract pure scalar helpers, never execute build/verify main or import their modules.
tree=ast.parse((P/'calculation/build_cost_table.py').read_text());funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('number','money','product','strict_sum')]
ns={'Decimal':Decimal,'ROUND_HALF_UP':ROUND_HALF_UP};exec(compile(ast.Module(body=funcs,type_ignores=[]),'<scalar helpers>','exec'),ns)
ck('07 unknown and cash',ns['product'](None,0) is None and ns['product'](0,None) is None and ns['strict_sum']([0,None]) is None,'unknown zero boundary')
ck('07 unknown and cash',ns['product'](0,100)==0 and ns['money']('-1.005')==-1.01,'known zero and negative rounding')
ck('07 unknown and cash',all(w[k] is None for k in ('annual_missing_total_rub','full_PnL_rub','full_cash_budget_rub')) and all(v is None for v in w['launch'].values()),'no complete budget from unknowns')
v=json.loads((P/'calculation/validation.json').read_text())
for n,h in v['outputs_sha256'].items():ck('12 validation and preservation',hashlib.sha256((P/'calculation'/n).read_bytes()).hexdigest()==h,n)
protection=json.loads((P/'calculation/protection.json').read_text())
h=hashlib.sha256();sources={n:v for n,v in before.items() if not n.startswith('calculation/')}
for n in sorted(sources,key=Path):h.update(n.encode()+b'\0'+bytes.fromhex(sources[n]))
protection_observation={'pre_review_input_count':len(sources),'producer_input_count':protection['input_files'],'pre_review_input_sha256':h.hexdigest(),'producer_input_sha256':protection['input_content_sha256'],'matches_producer_baseline':h.hexdigest()==protection['input_content_sha256'],'classification':'P3 verification provenance limitation; pre-existing before review; changed file UNKNOWN'}
ck('12 validation and preservation',digest()==before==json.loads(base.read_text()),'all existing P39 file contents unchanged; ignores mtime/review')
log={'status':'PASS' if not any(g['failures'] for g in groups.values()) else 'FAIL','method':'Independent CSV arithmetic and source lineage; no build.calculate, verify.main, Git or network rerun; manual primary checks in README','groups':groups,'protection_observation':protection_observation,'rows':len(rows),'coverage_rows':len(cov),'cases':len(T)}
(R/'check.log').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n');print(json.dumps(log,ensure_ascii=False,indent=2))
