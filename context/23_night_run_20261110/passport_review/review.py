#!/usr/bin/env python3
"""Bounded independent review. Repository inputs are read only by exact git show.

No owner code is imported/executed. Only stdlib; all writes stay next to this file.
Use --capture-official once for the expressly allowed public text HTTP receipt.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import math
import re
from pathlib import Path
import subprocess
import urllib.request
from html.parser import HTMLParser

OUT = Path(__file__).resolve().parent
N = 'context/23_night_run_20261110/'
SUBJECT = '46fd52db073cffc46a598f44489d0761c6853410'
BASE = 'b20d4346b6aede514dbed59112bcf878232819c8'
P = N + 'passport_bridge/'
SCREEN = '82dffa795146ccc575db1bb45ba9391af44def00'
COMMON = 'abb1c76254d2d4e3cf9edd5c345b9cdb224f6abe'
PRIMARY = '17b4f348f15ea8695688d9435933cb4965568408'
STRATEGY = '0cc043484147cb9f3a23a3d3d2aea9b4a6ce9ed9'
PINS = {
    'MR10': ('4604059a675b0be410ff46685ec77fa1dc20933a', 'correction_review'),
    'MR11': ('ea2a9626aef75c121f2da7d778b47edce0d571b7', 'methods_integration_review'),
    'FRONTIER_REVIEW': ('58a02028e062b1abd803d99e19f630b75ec80657', 'hypothesis_frontier_review'),
}
CACHE, SOURCES, CHECKS = {}, {}, []


def save(name, obj):
    (OUT/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def table(name, rows):
    assert rows, name
    with (OUT/name).open('w', newline='') as f:
        w = csv.DictWriter(f, list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


def blob(sha, path, grain='document; scope is specified by the consuming check'):
    assert len(sha) == 40 and all(c in '0123456789abcdef' for c in sha)
    key = sha+':'+path
    if key not in CACHE:
        b = subprocess.check_output(['git', 'show', key])
        CACHE[key] = b
        SOURCES[key] = dict(commit=sha, path=path, exact_ref=key,
                            git_blob=subprocess.check_output(['git','rev-parse',key],text=True).strip(),
                            bytes=len(b), sha256=hashlib.sha256(b).hexdigest(),
                            lines=len(b.splitlines()), grain=grain,
                            method='git show exactSHA:path')
    return CACHE[key]


def text(sha, path, grain='document'):
    return blob(sha,path,grain).decode('utf-8-sig')


def js(sha, path, grain='JSON object'):
    return json.loads(text(sha,path,grain))


def rows(sha, path, grain='CSV record; see header'):
    return list(csv.DictReader(io.StringIO(text(sha,path,grain))))


def check(name, ok, **evidence):
    CHECKS.append(dict(check_id=name, status='PASS' if ok else 'FAIL', **evidence))
    return ok


def near(name, a, b, tol=1e-6):
    return check(name, abs(float(a)-float(b)) <= tol, actual=a, expected=b, tolerance=tol)


def official(capture):
    receipt = OUT/'official_receipt.json'
    if capture:
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        u = 'https://mai-way.ru/tasks/red-wings/'
        req = urllib.request.Request(u, headers={'User-Agent':'bounded-passport-review/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            b = r.read(500001)
            assert len(b) <= 500000
            status, url, content_type = r.status, r.url, r.headers.get('Content-Type')
        class Extract(HTMLParser):
            def __init__(self): super().__init__(); self.parts=[]; self.skip=0
            def handle_starttag(self,t,a):
                if t in ('script','style'): self.skip+=1
            def handle_endtag(self,t):
                if t in ('script','style'): self.skip-=1
            def handle_data(self,t):
                if not self.skip and t.strip(): self.parts.append(t.strip())
        e=Extract(); e.feed(b.decode('utf-8'))
        plain=' '.join(e.parts)
        wording = {
            'two_hypotheses': 'Две гипотезы' in plain and 'обе гипотезы' in plain,
            'two_scenarios': 'базовом и' in plain and 'осторожном сценарии' in plain,
            'final_8_12_direct': '8–12' in plain and 'связаны напрямую' in plain,
            'passport_1_2': '1–2 страницы' in plain,
            'nov10_2359': '10 ноября, 23:59' in plain,
            'nov13_5_8_5min': all(x in plain for x in ['13 ноября','5–8 слайдов','5 минут']),
            'roadmap_2028': '2028' in plain and 'Дорожная карта' in plain,
            'synthetic_allowed': 'синтетические' in plain and 'метод' in plain,
            'h2_2027_case_limit': 'второй половины 2027' in plain,
            'no_500km_literal': re.search(r'(?<!\d)500\s*(?:км|километр)',plain,re.I) is None,
        }
        save('official_receipt.json',dict(url=u, requested_at_utc=started, method='urllib.request text GET; no browser/auth/cookies',
             native_error='URL https://mai-way.ru/tasks/red-wings/ is not accessible via this tool.',
             status=status, final_url=url, content_type=content_type, bytes=len(b),
             sha256=hashlib.sha256(b).hexdigest(), text_sha256=hashlib.sha256(plain.encode()).hexdigest(),
             wording_checks=wording, raw_published=False, full_text_published=False,
             scope='Organiser wording only; company/industry background is not independently verified.'))
    a=json.loads(receipt.read_text())
    check('official_wording_receipt',a['status']==200 and all(a['wording_checks'].values()),receipt='official_receipt.json')
    old=js(SUBJECT,P+'official_case_receipt.json')
    check('official_body_matches_subject_capture',a['sha256']==old['sha256'],actual=a['sha256'],expected=old['sha256'])


def package():
    text(BASE,N+'contract.md'); text(BASE,N+'briefs/passport_review.md')
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',SUBJECT,P],text=True).splitlines()
    for p in paths: blob(SUBJECT,p,'subject package file')
    out=js(SUBJECT,P+'output_manifest.json')
    checks=[]
    for r in out['files']:
        b=blob(SUBJECT,P+r['path'])
        checks.append(dict(path=r['path'],bytes_match=len(b)==r['bytes'],sha256_match=hashlib.sha256(b).hexdigest()==r['sha256']))
    check('subject_manifest',all(r['bytes_match'] and r['sha256_match'] for r in checks),files=len(checks))
    save('subject_manifest_verification.json',checks)
    upstream=[]
    for r in js(SUBJECT,P+'source_manifest.json')['sources']:
        b=blob(r['commit'],r['path'],r.get('grain','upstream input'))
        upstream.append(dict(exact_ref=r['commit']+':'+r['path'],sha256_match=hashlib.sha256(b).hexdigest()==r['sha256'],bytes_match=len(b)==r['bytes']))
    check('subject_source_manifest',all(r['sha256_match'] and r['bytes_match'] for r in upstream),files=len(upstream))
    save('upstream_manifest_verification.json',upstream)
    for e in rows(SUBJECT,P+'evidence_index.csv'):
        if e['source_commit']: blob(e['source_commit'],e['source_path'],e['grain'])
    for sha,folder in PINS.values():
        for f in ['report.md','findings.json','handoff.json']:
            blob(sha,N+folder+'/'+f,'later scoped upstream review; NOT rerun here')


def screening():
    w=rows(SUBJECT,P+'author_weights.csv')
    weight_checks=[]; scores=[]
    for name,folder in [('nastya','nastya'),('tsiri_stage22','tsiri_stage22')]:
        root=N+'screening/inputs/'+folder+'/'
        a=js(SCREEN,root+'data/processed/criteria.json','city × criterion × raw/utility')
        ll=rows(SCREEN,root+'data/processed/longlist.csv','city × distances')
        cities={r['iata']:r for r in ll}
        crit=a['criteria']; sw=sum(c['weight'] for c in crit)
        expected_weights={c['key']:c for c in crit}
        for r in [r for r in w if r['model']==name]:
            c=expected_weights[r['criterion']]
            ok=(float(r['raw_weight'])==c['weight'] and abs(float(r['normalized_weight'])-c['weight']/sw)<1e-12 and r['direction']==c['dir'] and r['label']==c['label'])
            weight_checks.append(dict(model=name,criterion=r['criterion'],raw_weight=c['weight'],sum_weights=sw,pass_exact_transfer=ok))
        for radius in ([0,500] if name=='nastya' else [0,300,500,800]):
            eligible=[i for i in cities if min(float(cities[i]['dist_msk_km']),float(cities[i]['dist_ekb_km']))>=radius]
            results={}
            for i in eligible:
                score=0
                for c in crit:
                    x=a['values'][i][c['key']]
                    if name=='tsiri_stage22': u=x['u']
                    else:
                        k=c['key']; vals=[a['values'][j][k]['v'] for j in eligible]
                        vals=[c.get('fill') if v is None else v for v in vals]
                        good=[v for v in vals if v is not None]
                        lo=c.get('lo') if c.get('lo') is not None else min(good)
                        hi=c.get('hi') if c.get('hi') is not None else max(good)
                        v=x['v'] if x['v'] is not None else c.get('fill')
                        if v is None: u=.5
                        else:
                            u=(v-lo)/(hi-lo) if hi>lo else 0
                            if c['dir']=='-':u=1-u
                    score+=c['weight']*u/sw
                results[i]=score
            ordered=sorted(results,key=lambda i:-results[i])
            for rank,i in enumerate(ordered,1):scores.append(dict(model=name,radius_km=radius,iata=i,rank=rank,score=results[i],calculation='raw minmax' if name=='nastya' else 'independent weighted sum of frozen declared utilities'))
            targets={('nastya',0):['PEE','UFA','CEK'],('nastya',500):['OMS','REN','KUF'],('tsiri_stage22',0):['CEK','UFA','OMS'],('tsiri_stage22',300):['UFA','OMS','PEE'],('tsiri_stage22',500):['OMS','REN','BAX'],('tsiri_stage22',800):['OMS','BAX','KJA']}
            check('top_'+name+'_'+str(radius),ordered[:3]==targets[name,radius],actual=ordered[:3],eligible=len(eligible))
        if name=='tsiri_stage22':
            gap=[]
            for c in crit:
                bu=a['values']['BAX'][c['key']]['u']; ku=a['values']['KUF'][c['key']]['u']
                gap.append(dict(criterion=c['key'],weight=c['weight'],BAX_u=bu,KUF_u=ku,delta=c['weight']*(bu-ku)/sw))
            g=sum(r['delta'] for r in gap)
            near('BAX_KUF_gap',g,.000721148,tol=1e-9)
            c=next(c for c in crit if c['key']=='last365_days')
            effect=-c['weight']/sw/(c['hi']-c['lo'])
            check('one_publication_day_counterexample',g+effect<0,baseline_gap=g,one_added_BAX_day_effect=effect,new_gap=g+effect,scope='synthetic perturbation; not evidence of a missing message')
            table('independent_bax_kuf.csv',gap)
    check('author_weights_exact',len(weight_checks)==36 and all(r['pass_exact_transfer'] for r in weight_checks),rows=len(weight_checks))
    h=N+'screening/inputs/tsiri_historical/context/11_practical_screening/'
    ranks=rows(SCREEN,h+'ranking.csv'); params=js(SCREEN,h+'inputs.json')
    for scope,expected in [('all',['GOJ','KUF','KZN']),('new_node',['GOJ','UFA','GSV'])]:
        rr=[r for r in ranks if r['weights']=='base' and r['scope']==scope]
        if not rr and scope=='new_node':rr=[r for r in ranks if r['weights']=='base' and r['scope']=='new']
        check('stage11_scope_'+scope,len(rr)==(10 if scope=='all' else 8),rows=len(rr))
        for r in rr:
            q=sum(float(r[k])*v for k,v in params['weights']['base'].items())
            near('stage11_'+scope+'_'+r['iata'],q,float(r['score']),tol=.00006)
        ordered=sorted(rr,key=lambda r:-sum(float(r[k])*v for k,v in params['weights']['base'].items()))
        check('stage11_top_'+scope,[r['iata'] for r in ordered[:3]]==expected,actual=[r['iata'] for r in ordered[:3]])
    table('independent_weights.csv',weight_checks);table('independent_screening.csv',scores)


def economics():
    root=N+'methods/'; src=root+'inputs/set001/tsiri_93fa/context/'
    sales=rows(COMMON,src+'17_aircraft_route_review/model/sales.csv')
    caps=rows(COMMON,src+'17_aircraft_route_review/model/capacity.csv')
    flights=rows(COMMON,src+'17_aircraft_route_review/model/flights.csv')
    programs=rows(COMMON,src+'21_team_proposals/comparison.csv')
    config=js(COMMON,src+'15_team_update/model/configuration.json')
    mapping=rows(COMMON,root+'runs/common_demand_v1/demand_mapping.csv')
    nd={(r['network'],r['scenario'],tuple(r['pair'].split('-'))):float(r['N_annual_proxy'])/104 for r in mapping}
    check('annual_div104_not_winter_OD',all(abs(float(r['N_week_direction_stress'])-float(r['N_annual_proxy'])/104)<1e-8 and r['status']=='SOURCE_RECIPE_SCALE_NOT_OBSERVED_ENDPOINT_OD' for r in mapping),rows=len(mapping))
    def simulate(network,scenario,alpha=0,multiplier=1):
        pr=next(r for r in programs if r['network']==network and r['scenario']==scenario)
        ss=[s for s in sales if (s['profile'],s['network'],s['scenario'])==(pr['source_profile'],pr['source_network'],scenario)]
        cc=[c for c in caps if (c['profile'],c['network'],c['scenario'])==(pr['source_profile'],pr['source_network'],scenario)]
        p=config['scenarios'][scenario]; pair=lambda a,b:tuple(sorted([a,b]))
        freq=collections.Counter((s['origin'],s['destination']) for s in ss)
        known={pair(s['origin'],s['destination']) for s in ss if s['known_direct_RW_capacity'] and float(s['known_direct_RW_capacity'])>0}
        offers=[]
        for s in ss:
            tr=s['transfer']=='True'; fare=float(s['fare_once']); legs=s['flight_ids'].split(';'); k=(s['origin'],s['destination'])
            can=(.6 if scenario=='base' else .8) if pair(*k) in known else (.05 if scenario=='base' else .1)
            oldfare=fare/(p['transfer_fare_factor'] if tr else 1)*p['old_RW_fare_ratio']
            coefficient=(.45 if scenario=='base' else .30)*(-math.expm1(-freq[k]/3))*(.65 if tr else 1)/freq[k]
            D=(1-alpha)*float(s['D'])+alpha*nd[(network,scenario,pair(*k))]
            priority=(tr,-(fare-can*oldfare-len(legs)*p['pax_cost'])/len(legs),*k,int(s['day']),tuple(legs))
            offers.append((priority,s,legs,k,can,oldfare,coefficient,D*multiplier))
        remaining={c['flight_id']:float(c['capacity_scenario']) for c in cc};old={};tot=collections.Counter();market=collections.Counter()
        for _,s,legs,k,can,oldfare,coeff,D in sorted(offers):
            if k not in old:old[k]=float(s['known_direct_RW_capacity'] or 0)
            q=min([D*coeff]+[remaining[f] for f in legs])
            for f in legs:remaining[f]-=q
            direct=min(q*can,old[k]);old[k]-=direct;unknown=q*can-direct
            tot.update(sold_journeys=q,segment_pax=q*len(legs),gross_revenue=q*float(s['fare_once']),foregone_RW_revenue=q*can*oldfare,
                       new_pax_variable=q*len(legs)*p['pax_cost'],saved_old_pax_variable=(direct+2*unknown)*p['pax_cost'])
            market[k]+=q
            assert market[k]<=D+1e-6
        flight_cost=sum(float(c['flight_variable_cost']) for c in cc)
        value=tot['gross_revenue']-tot['foregone_RW_revenue']-tot['new_pax_variable']+tot['saved_old_pax_variable']-flight_cost
        return dict(network=network,scenario=scenario,alpha=alpha,multiplier=multiplier,contribution=value,flight_cost=flight_cost,**tot)
    numeric=[]
    expected=rows(COMMON,root+'runs/common_demand_v1/summary.csv')
    for network in ['D_SVX8','H_UFA_4','H_UFA_8']:
        for sc in ['base','cautious']:
            for alpha,recipe in [(0,'C'),(1,'N')]:
                q=simulate(network,sc,alpha);numeric.append(q)
                e=next(r for r in expected if r['network']==network and r['scenario']==sc and r['recipe']==recipe and float(r['multiplier'])==1)
                near('common_'+network+'_'+sc+'_'+recipe,q['contribution'],e['contribution_before_base_fleet_opportunity'])
    def delta(a):return simulate('D_SVX8','base',a)['contribution']-simulate('H_UFA_4','base',a)['contribution']
    lo,hi=0.,1.
    for _ in range(55):
        m=(lo+hi)/2
        if delta(m)>0:hi=m
        else:lo=m
    alpha=(lo+hi)/2; aa=simulate('D_SVX8','base',alpha); bb=simulate('H_UFA_4','base',alpha)
    near('S01_alpha',alpha,.6835090019901081,tol=1e-10)
    near('S01_equal_contribution',aa['contribution'],bb['contribution'])
    check('S01_both_negative',aa['contribution']<0 and bb['contribution']<0,contribution=aa['contribution'])
    roots={}
    for network,expected_root in [('H_UFA_4',2.4617708804),('H_UFA_8',2.9194370052)]:
        lo,hi=1.,4.
        for _ in range(55):
            m=(lo+hi)/2
            if simulate(network,'base',0,m)['contribution']>=0:hi=m
            else:lo=m
        roots[network]=(lo+hi)/2
        near('S03_zero_'+network,roots[network],expected_root,tol=1e-9)
    saturated=simulate('D_SVX8','base',0,100)
    near('S03_saturation',saturated['contribution'],-449822.7,tol=1e-6)
    gap=simulate('H_UFA_4','base')['contribution']-simulate('D_SVX8','base')['contribution']
    near('S04_FplusB_threshold_rounded_kopeck',round(gap,2),2703326.68,tol=1e-8)
    bounds=[]
    for pr in programs:
        sc=pr['scenario'];p=config['scenarios'][sc]
        ss=[s for s in sales if (s['profile'],s['network'],s['scenario'])==(pr['source_profile'],pr['source_network'],sc)]
        cc=[c for c in caps if (c['profile'],c['network'],c['scenario'])==(pr['source_profile'],pr['source_network'],sc)]
        local={s['flight_ids']:float(s['fare_once'])-p['pax_cost'] for s in ss if s['transfer']=='False'}
        local_dominates=all(float(s['fare_once'])-len(s['flight_ids'].split(';'))*p['pax_cost']<=sum(local[f] for f in s['flight_ids'].split(';'))+1e-8 for s in ss)
        bound=sum(float(c['capacity_scenario'])*local[c['flight_id']]-float(c['flight_variable_cost']) for c in cc)
        bounds.append(dict(network=pr['network'],scenario=sc,optimistic_bound=bound,transfer_dominated_by_local=local_dominates,scope='fixed products; no migration; all local seats sold; before unknown fixed costs'))
    check('S02_all_four_cautious_bounds_negative',sum(r['scenario']=='cautious' for r in bounds)==4 and all(r['optimistic_bound']<0 and r['transfer_dominated_by_local'] for r in bounds if r['scenario']=='cautious'),bounds=[r for r in bounds if r['scenario']=='cautious'])
    resources=rows(STRATEGY,N+'strategy_accounting_review/independent_resources.csv')
    necessary=4*6*10
    check('S05_resource_envelope',necessary==240 and 9*7*10==630,common=necessary,author=9*7*10)
    real=next(r for r in resources if r['model']=='anastasia' and r['candidate']=='REN' and r['scenario']=='base')
    h=float(real['weekly_block_hours'])
    check('resource_real_REN_counterexample',math.ceil(h/60)==5 and math.ceil(h/70)==4,weekly_hours=h,common_necessary_gate=h<=240,scope='necessary hours; not actual tails/crew/calendar')
    # Rebuild concurrent flight intervals from exact original primitives, shift only day1.
    pr=next(r for r in programs if r['network']=='H_UFA_8' and r['scenario']=='base')
    ff=[f for f in flights if (f['profile'],f['network'])==(pr['source_profile'],pr['source_network'])]
    intervals=[]
    for f in ff:
        shift=1440 if int(f['day'])==1 else 0
        intervals.append(dict(flight_id=f['id'],start=float(f['departure_utc_minute'])+shift,end=float(f['arrival_utc_minute'])+shift,planning_label=f['aircraft']))
    events=sorted({r[k] for r in intervals for k in ['start','end']});slices=[]
    for start,end in zip(events,events[1:]):
        ids=sorted(r['flight_id'] for r in intervals if r['start']<=start<r['end'])
        if ids:slices.append(dict(start=start,end=end,in_flight=len(ids),flight_ids=';'.join(ids)))
    peak=max(r['in_flight'] for r in slices)
    check('S07_concurrent_peak',peak==8,peak_in_flight=peak,working_plus_reserve=5,scope='necessary flying concurrency; crew/tail/slots UNKNOWN')
    table('independent_shifted_flight_intervals.csv',intervals);table('independent_concurrency.csv',slices)
    cash=rows(COMMON,root+'runs/budget_v1/cash_fixture.csv')
    cumulative=0;peak=0;out=[]
    for r in cash:
        net=float(r['operating_receipts'])+float(r['deposit_return'])-float(r['operating_payments'])-float(r['launch_payments'])-float(r['deposit_payment'])
        cumulative+=net;peak=max(peak,-cumulative)
        near('cash_net_'+r['period'],net,r['net_cash']);near('cash_cumulative_'+r['period'],cumulative,r['cumulative_cash_before_financing'])
        out.append(dict(period=r['period'],net_cash=net,cumulative=cumulative,funding_peak_so_far=peak))
    check('cash_counterexample',cumulative==400000 and peak==1000000,terminal_cash=cumulative,peak_funding=peak,scope='illustrative timing only; company full cash UNKNOWN')
    near('S08_journey_cost_clients',math.ceil(1000000/(2*(8000-500))),67,tol=0)
    near('S08_segment_cost_clients',math.ceil(1000000/(2*(8000-2*500))),72,tol=0)
    portfolio=rows('c24bbd36356f46763eed5a1654573b6de31adc6b',root+'runs/portfolio_v1/summary.csv')
    pairrow=next(r for r in portfolio if r['portfolio']=='D_SVX8+D_previous_best8' and r['scenario']=='base' and r['capture_law']=='COUNT_DISTINCT_DEPARTURE_TIMES')
    pooled=sum(float(pairrow[k])*sign for k,sign in [('gross_revenue',1),('foregone_RW_revenue',-1),('new_pax_variable',-1),('saved_old_pax_variable',1),('flight_variable_cost',-1)])
    singles=[r for r in portfolio if r['portfolio'] in ['D_SVX8','D_previous_best8'] and r['scenario']=='base' and r['capture_law']=='COUNT_DISTINCT_DEPARTURE_TIMES']
    additive=sum(float(r['contribution_before_base_fleet_opportunity']) for r in singles)
    near('S06_ledger_delta_rounded',round(pooled-additive,2),-446063.89,tol=1e-8)
    pools=collections.defaultdict(lambda:dict(sold=0,D=set(),programs=set()))
    for pr in programs:
        for s in sales:
            if (s['profile'],s['network'],s['scenario'])!=(pr['source_profile'],pr['source_network'],pr['scenario']):continue
            k=(pr['scenario'],s['origin'],s['destination']);pools[k]['sold']+=float(s['sold_journeys']);pools[k]['D'].add(float(s['D']));pools[k]['programs'].add(pr['network'])
    check('original_all_four_programs_D_bound',all(len(v['D'])==1 and v['sold']<=next(iter(v['D']))+1e-6 for v in pools.values()),directed_scenario_pools=len(pools),scope='actual frozen standalone claims pooled once per program; Q(F) remains a proposed tighter law')
    table('independent_original_D_pools.csv',[dict(scenario=k[0],origin=k[1],destination=k[2],sold=v['sold'],D=next(iter(v['D'])),programs=';'.join(sorted(v['programs']))) for k,v in sorted(pools.items())])
    # Recount frozen author's selected triangle legs; MOW remains a model node.
    routes=rows('27740ffea0821aa404ecd1013d1bb141613261f3',N+'model_repair/author/data/processed/network_routes.csv')
    routecounts=[]
    for sc,target in [('base',20),('cautious',18)]:
        rr=[r for r in routes if r['scenario']==sc and r['variant'].startswith('Прямые ')]
        programs_n=len({r['variant'] for r in rr});pairs={tuple(sorted((r['from'],r['to']))) for r in rr}
        check('C04_route_count_'+sc,programs_n==8 and len(pairs)==target and any('MOW' in k for k in pairs),programs=programs_n,model_endpoint_pairs=len(pairs),scope='unordered city-node pairs; MOW is not an airport assignment')
        for a,b in sorted(pairs):routecounts.append(dict(scenario=sc,origin_node=a,destination_node=b,MOW_aggregated='MOW' in [a,b],physical_airport_assignment='UNKNOWN'))
    table('independent_route_pairs.csv',routecounts)
    table('independent_common_cases.csv',numeric);table('independent_upper_bounds.csv',bounds);table('independent_cash.csv',out)
    save('independent_boundaries.json',dict(alpha=alpha,contribution_at_rank_boundary=aa['contribution'],H4_zero=roots['H_UFA_4'],H8_zero=roots['H_UFA_8'],DSVX_saturated=saturated['contribution'],F_plus_B_threshold=gap,actual_cash_unknown=True))


def competitors():
    ex=rows(SUBJECT,P+'competitor_and_svx_gaps.csv');cards=rows(PRIMARY,N+'primary_evidence/route_product_cards.csv')
    by_id={r['card_id']:r for r in cards}; dated=rows(PRIMARY,N+'primary_evidence/dated_evidence.csv')
    regs=rows(PRIMARY,N+'primary_evidence/source_registry.csv');reg={r['source_id']:r for r in regs}
    checks=[];matches=[]
    for n,r in enumerate(ex,2):
        if r['kind']!='ROUTE_OFFER':continue
        c=by_id[r['source_card_ids']]
        same=all(r[a]==c[b] for a,b in [('carrier','carrier'),('flight','flight'),('published_count','one_way_departures'),('departure_dates','departure_dates'),('source_ids','source_ids'),('raw_sha256','raw_sha256'),('source_rows','source_rows'),('source_urls','source_urls'),('clock_status','clock_consensus_status')])
        period=r['reference_period']==c['period_start']+'/'+c['period_end']
        ds=[d for d in dated if (d['origin'],d['destination'],d['flight'],d['source_id'],d['html_sha256'])==(c['origin'],c['destination'],c['flight'],c['source_ids'],c['raw_sha256'])]
        expected_dates=c['departure_dates'].split(';')
        dates=sorted(d['date'] for d in ds)
        check('card_'+r['example_id'],same and period and dates==expected_dates and len(ds)==int(r['published_count']),card=c['card_id'],actual_dates=dates)
        checks.append(dict(example_id=r['example_id'],subject_csv_line=n,kind=r['kind'],source_card_id=c['card_id'],source_commit=PRIMARY,
                           source_locator=N+'primary_evidence/route_product_cards.csv:'+str(cards.index(c)+2),
                           identity_count_dates='PASS' if same and period and dates==expected_dates else 'FAIL',
                           independently_recounted=len(ds),departure_dates=';'.join(dates),qualification=r['acceptance_scope'],
                           personal_check='exact card fields + dated rows; raw body not reread',remaining_unknown='operation; legal seats; bookable fare; observed OD; complete competition'))
        for d in ds:matches.append(dict(example_id=r['example_id'],card=c['card_id'],date=d['date'],origin=d['origin'],destination=d['destination'],source_row=d['source_row'],source_id=d['source_id'],raw_sha256=d['html_sha256']))
    # Re-expand source-specific UFA and KUF rules without owner parser or calendar code.
    ufa=rows(PRIMARY,N+'primary_evidence/ufa_schedule_rules.csv');end=rows(PRIMARY,N+'primary_evidence/endpoint_schedule_rules.csv')
    days=['пн','вт','ср','чт','пт','сб','вс'];week=[dt.date(2026,12,7)+dt.timedelta(days=k) for k in range(7)];rulechecks=[]
    for r in ex:
        if r['kind']!='ROUTE_OFFER':continue
        c=by_id[r['source_card_ids']]; allrules=ufa if c['source_ids'].startswith('ufa_') else end
        rr=[x for x in allrules if (x['source_id'],x['origin'],x['destination'],x['flight'])==(c['source_ids'],c['origin'],c['destination'],c['flight'])]
        if not rr:continue
        expanded=[]
        for x in rr:
            lo=x.get('period_start') or x['assigned_period_start'];hi=x.get('period_end') or x['assigned_period_end'];active=x.get('active_days') or x.get('weekdays','')
            for d in week:
                if lo<=d.isoformat()<=hi and days[d.weekday()] in active.lower():expanded.append(d.isoformat())
        actual=sorted(set(expanded));expected=c['departure_dates'].split(';')
        check('rule_expand_'+r['example_id'],actual==expected,actual=actual,expected=expected)
        rulechecks.append(dict(example_id=r['example_id'],rules=len(rr),rule_dates=';'.join(actual),calendar_matches=actual==expected,year_scope='explicit source year for UFA; assigned winter2026/27 for KUF, conditional'))
    svx=rows(PRIMARY,N+'primary_evidence/svx_observations.csv')
    for r in ex:
        if r['kind']=='ROUTE_OFFER':continue
        e=r['example_id']; personal='semantic source comparison; inherited upstream verdict, not raw re-audit'
        if e in ['V01','V02','V03','V04','V05']:
            mm=[x for x in svx if x['source_id']==r['source_ids'] and x['value']==r['published_count']]
            ok=len(mm)==1 and mm[0]['raw_sha256']==r['raw_sha256'] and mm[0]['reference_period']==r['reference_period']
            check('svx_'+e,ok,metric=mm[0]['metric'] if mm else None)
            locator=N+'primary_evidence/svx_observations.csv:'+str(svx.index(mm[0])+2) if mm else ''
        else:ok=True; locator='See semantic note and evidence IDs '+r['exact_evidence_ids']
        checks.append(dict(example_id=e,subject_csv_line=ex.index(r)+2,kind=r['kind'],source_card_id='',source_commit=PRIMARY if e.startswith('V') else '',source_locator=locator,
                           identity_count_dates='PASS_SCOPED' if ok else 'FAIL',independently_recounted='',departure_dates='',qualification=r['acceptance_scope'],personal_check=personal,
                           remaining_unknown=r['gap']))
    # Verify the three inherited OMS outbound examples against their own frozen calendar.
    core='505e24663e5952bae9b9540bb9a5a622663bfc2a'
    oms=rows(core,'context/16_agent_research/core/branches/operating_evidence/normalized/omsk_outbound_week_20261207.csv')
    for r in ex:
        if r['example_id'] not in ['K030','K031','K033']:continue
        c=by_id[r['source_card_ids']]
        oo=[x for x in oms if (x['origin_airport_iata'],x['destination_airport_iata'],x['outbound_flight_numeric'])==(c['origin'],c['destination'],c['flight'])]
        actual=sorted(x['departure_date_local'] for x in oo)
        check('OMS_frozen_calendar_'+r['example_id'],actual==c['departure_dates'].split(';'),actual=actual,scope='inherited normalized timetable, not raw or operation reacceptance')
    # Recompute the two denominators independently; they describe different sets.
    cov=rows(PRIMARY,N+'primary_evidence/coverage.csv')
    transfercoverage=[]
    for network,total,positive in [('H_UFA_8',56,10),('H_UFA_4',12,2)]:
        cr=[r for r in cov if network in r['candidate_ids'].split(';') and 'ENDPOINT_OD_VIA_UFA' in r['market_roles'].split(';')]
        actual=sum(int(r['positive_source_cards'])>0 for r in cr)
        check('G01_'+network,len(cr)==total and actual==positive,denominator=len(cr),positive=actual)
        transfercoverage.append(dict(kind='ALL_LEAF_COMBINATIONS',network=network,denominator=len(cr),positive=actual,missing_status='UNKNOWN'))
    pub=rows('7a868d1282b9c4de012e39e9fc1104d2d7f675e4',N+'common_comparison_review/independent_publication_join.csv')
    for network,total,positive in [('H_UFA_8',24,3),('H_UFA_4',8,1)]:
        cr={(r['origin'],r['destination']):r for r in pub if r['candidate_id']==network and r['role']=='TRANSFER_ENDPOINT' and r['scenario_id']=='base'}
        actual=sum(r['has_publication']=='True' for r in cr.values())
        check('G02_'+network,len(cr)==total and actual==positive,denominator=len(cr),positive=actual,scope='independent regroup of upstream incidence, no raw source uplift')
        transfercoverage.append(dict(kind='EXPORTED_TRANSFER_OD',network=network,denominator=len(cr),positive=actual,missing_status='UNKNOWN'))
    table('independent_coverage.csv',transfercoverage)
    profiles=js('77343ca9dccc14d60c51d4559485646219ecd1cd','context/13_competitors/competitors.json')
    statuses={r['id']:r['status'] for r in profiles['sources']}
    check('profiles_inherited_statuses_retained',statuses['S7']=='PRIMARY_READ' and statuses['A4']=='PRIMARY_READ' and statuses['A4M']=='PRIMARY_READ' and statuses['U6']=='PRIMARY_SEARCH_INDEX' and statuses['U6B']=='SECONDARY_SEARCH_INDEX',scope='upstream profile source classifications, not new raw verification')
    receipts=js(PRIMARY,N+'primary_evidence/http_receipts.json')
    sample=[]
    for sid in ['ufa_mrv','ufa_mrv_to','ufa_goj_fixed','ufa_goj_to','svx_results_2025','nordstar_rw_2024']:
        found=[r for r in receipts if r['source_id']==sid]
        if found:
            a=found[-1];r=reg[sid]
            ok=a.get('sha256')==r['raw_sha256'] and str(a.get('http_status'))==r['http_status']
            check('receipt_'+sid,ok,raw_sha256=r['raw_sha256'])
            sample.append(dict(source_id=sid,url=r['url'],http_status=a.get('http_status'),sha256=a.get('sha256'),capture=a.get('captured_at_utc'),receipt_registry_match=ok,
                               raw_body_availability='ignored local only; not in pinned Git input; NOT_READ'))
    check('all_28_competitor_examples_covered',len(checks)==28,rows=len(checks),route_cards=sum(r['kind']=='ROUTE_OFFER' for r in checks))
    table('competitor_checks.csv',checks);table('independent_card_dates.csv',matches);table('independent_rule_calendars.csv',rulechecks);save('receipt_sample.json',sample)


def synthesis_structure():
    requirements=rows(SUBJECT,P+'requirements_evidence.csv');claims=rows(SUBJECT,P+'claims.csv');ex=rows(SUBJECT,P+'competitor_and_svx_gaps.csv');decisions=rows(SUBJECT,P+'decision_options.csv')
    check('required_counts',len(requirements)==26 and len(claims)==33 and len(ex)==28 and len(decisions)==11,requirements=len(requirements),claims=len(claims),competitor_examples=len(ex),decisions=len(decisions))
    eid={r['evidence_id'] for r in rows(SUBJECT,P+'evidence_index.csv')};rid={r['requirement_id'] for r in requirements};cid={r['claim_id'] for r in claims}
    check('claim_foreign_keys',all(set(r['evidence_ids'].split(';'))<=eid and set(r['requirement_ids'].split(';'))<=rid for r in claims))
    check('requirement_foreign_keys',all(set(r['allowed_claim_ids'].split(';'))<=cid for r in requirements))
    prose=text(SUBJECT,P+'passport_claims.md')
    check('all_claim_wording_and_qualifications_in_prose',all(r['ready_russian_wording'] in prose and r['acceptance_scope'] in prose and r['use_condition'] in prose and r['prohibited_extension'] in prose for r in claims))
    check('all_11_decisions_open',all(r['status']=='OPEN_DECISION' for r in decisions))
    launches=js('77343ca9dccc14d60c51d4559485646219ecd1cd',N+'sol_launch_receipts.json')
    check('AI_static_roles_match',len(launches)==4 and {r['role'] for r in launches}=={'model_repair','data_bridge','primary_evidence','screening_review'} and all(r['model']=='gpt-6.1-sol' and r['providerInstanceId']=='codex' and {x['id']:x['value'] for x in r['options']}['reasoningEffort']=='xhigh' for r in launches),scope='recorded launches, no live occupancy/performance audit')
    second=js('77343ca9dccc14d60c51d4559485646219ecd1cd',N+'launch_registry_seed.json')
    check('AI_second_Astra_record',second['methods']['model']=='gpt-6-astra',scope='recorded role only')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--capture-official',action='store_true');a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    package();official(a.capture_official);screening();economics();competitors();synthesis_structure()
    save('source_manifest.json',dict(subject=SUBJECT,prepared_base=BASE,method='git show exactSHA:path only',sources=list(SOURCES.values()),
                                    reading_boundary='Obtained/hash verified does not mean every source raw body or every model pipeline was re-audited. Own computations are identified in checks and report.'))
    save('checks.json',dict(status='PASS' if all(c['status']=='PASS' for c in CHECKS) else 'FAIL',checks=CHECKS,
                            acceptance='BOUNDED_SYNTHESIS_REVIEW; not full economic replay/source/operational acceptance'))
    print(json.dumps(dict(checks=len(CHECKS),failed=[c for c in CHECKS if c['status']=='FAIL'],sources=len(SOURCES)),ensure_ascii=False))
    if any(c['status']=='FAIL' for c in CHECKS):raise SystemExit(1)


if __name__=='__main__':main()
