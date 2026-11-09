#!/usr/bin/env python3
"""Offline team update; Python stdlib. Run: python3 scripts/build_team_comparison.py.

Only this script, context/15_team_update/model and calculations.md are written.
No web, no optimisation claim: finite bank/rotation/frequency enumeration plus
explicit local-first / transfer-first allocation heuristics. Inputs can be
updated through model/overrides.json without changing the calculation logic.
"""
from __future__ import annotations
import copy
import csv
import datetime as dt
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'context/15_team_update/model'
LEGACY = ROOT / 'context/12_network_economics'
SCREEN = ROOT / 'context/11_practical_screening'
AS_OF = '2026-11-09'
WEEK = '2026-12-07'
READS = set()
META = dict(as_of=AS_OF, period='2026-12-07/2026-12-13 scenario week',
            geography='Russian domestic endpoint OD; airport-level operations',
            source='frozen repository inputs + explicitly labelled analyst scenarios',
            status='CONDITIONAL_SCENARIO_NOT_FORECAST')


def read(path):
    path = Path(path)
    READS.add(path.resolve())
    return path.read_text(encoding='utf-8-sig')


def jsin(path): return json.loads(read(path))
def csvin(path): return list(csv.DictReader(read(path).splitlines()))
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csvout(name, rows):
    rows = list(rows)
    units=('screening utility 0..1; weights and rank' if 'city_' in name or 'score_' in name else
           'dimensionless multipliers; RUB/week; endpoint journeys/week' if 'sensitivity' in name or 'threshold' in name or 'maxima' in name else
           'dated flight segments; UTC minutes; block hours; seats; endpoint journeys; RUB/week; see column names')
    rows=[{**META,'unit':units,**r} for r in rows]
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, keys, lineterminator='\n')
        w.writeheader()
        w.writerows({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)


def pair(a, b): return '-'.join(sorted((a, b)))
def number(v):
    try: return float(v)
    except (ValueError, TypeError): return None


def replay_old():
    """Unmodified legacy program is run under a new ROOT before any new model."""
    sandbox = OUT / 'legacy_replay'
    inputs = [ROOT / 'scripts/build_network_economics.py']
    inputs += [SCREEN / n for n in ['inputs.json', 'coordinates.json', 'ranking.csv']]
    inputs += [LEGACY / n for n in ['inputs.json', 'schedule_rules.json', 'sources.json', 'advertised_fares.json']]
    for src in inputs:
        READS.add(src.resolve())
        dest = sandbox / src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    run = subprocess.run([sys.executable, str(sandbox / 'scripts/build_network_economics.py')],
                         cwd=sandbox, text=True, capture_output=True, check=True)
    original = csvin(LEGACY / 'network_comparison.csv')
    reproduced = csvin(sandbox / 'context/12_network_economics/network_comparison.csv')
    deltas = []
    for a, b in zip(original, reproduced):
        assert a.keys() == b.keys()
        for k in a:
            x, y = number(a[k]), number(b[k])
            if x is not None and y is not None:
                assert math.isclose(x, y, rel_tol=1e-10, abs_tol=1e-5), (k, x, y)
                deltas.append(abs(x-y))
            else: assert a[k] == b[k]
    assert len(original) == len(reproduced) == 6
    result = dict(status='PASS', rows=6, max_absolute_numeric_difference=max(deltas),
                  stdout=run.stdout.strip(), stderr=run.stderr,
                  source_inputs=[str(p.relative_to(ROOT)) for p in inputs],
                  scope='frozen JSON replay only; historic HTML parser NOT rerun; legacy quirks retained here')
    dump('legacy_reproduction.json', result)
    return result


def ranking():
    rows = csvin(ROOT / 'data/processed/longlist.csv')
    ranking_overrides = jsin(OUT/'overrides.json').get('ranking',{})
    for evidence in ['evidence/parent_verified_facts.json','evidence/parent_verified_costs.csv','evidence/cities_matrix.csv','evidence/cities_matrix_manifest.json']:
        read(OUT.parent/evidence)
    read(ROOT/'scripts/collect_team_context.py')
    # Only corrected scenarios use newly confirmed city values; team_original remains a replay.
    frozen_rows = copy.deepcopy(rows)
    weights = csvin(ROOT / 'data/assumptions/longlist_weights.csv')
    # Read the provenance and preprocessing, never run code which overwrites team outputs.
    for p in ['src/longlist_data.py', 'src/longlist_score.py', 'src/build_longlist.py',
              'docs/22_data_sources_longlist.md', 'context/14_synthesis/analysis.md',
              'data/manual/longlist_manual.csv', 'data/processed/longlist_computed.csv',
              'data/processed/longlist_scores.csv', 'data/processed/longlist_scores_min500.csv',
              'data/processed/longlist_sensitivity.csv', 'data/processed/longlist_sensitivity_min500.csv']:
        read(ROOT / p)
    w = {r['column']: float(r['weight']) for r in weights}
    negative = {r['column'] for r in weights if r['direction'] == '-'}
    known_bases = set(ranking_overrides.get('confirmed_competitor_bases', ['KJA','IKT','VVO','MRV','AER','MCX']))
    possible_bases = set(ranking_overrides.get('possible_competitor_bases',['KZN','TJM']))
    # A carrier statement is presence evidence, never a measured fortress or route share.
    competitor_status = {i: ('STATEMENT_IN_FROZEN_MANUAL' if i in {'KJA','IKT','VVO','MRV','AER','MCX'}
                             else 'PRIMARY_INDEXED_HOME_CARRIER_STATEMENT_NOT_ROUTE_SHARE') for i in known_bases}
    rank_rows = []
    crit_rows = []
    normalized = {}
    for col in w:
        vals = []
        for r in rows:
            if col == 'dist_bases_km': v = min(float(r['dist_msk_km']), float(r['dist_ekb_km']))
            elif col == 'competitor_hub': v = float(r['iata'] in {'KJA','IKT','VVO'})
            else: v = number(r.get(col))
            if v is not None: vals.append(v)
        lo, hi = min(vals), max(vals)
        normalized[col] = (0., 2.) if col == 'rostec_link' else (lo, hi)
    cases = {
        'team_original': w,
        'unknown_intervals_corrected_bases': w,
        'expanded_base_leads_stress': w,
        'information_neutral': {k:v for k,v in w.items() if k not in ['competitor_hub','transfer_zone','rostec_link','pax_2025']},
        'connectivity_resilience': dict(gap_pop=30,last365_days=35,catchment_pop=15,dist_bases_km=15,strategy_region=5),
        'market_scale': dict(gap_pop=15,last365_days=20,pax_2025=20,catchment_pop=25,dist_bases_km=10,
                             strategy_region=5,transfer_zone=5),
        'no_access_bias_no_rostec': {k:v for k,v in w.items() if k not in ['rostec_link','transfer_zone','competitor_hub']},
    }
    case_top = {}
    for case, ww in cases.items():
        rows=copy.deepcopy(frozen_rows)
        if case!='team_original':
            for r in rows:r.update(ranking_overrides.get('city_values',{}).get(r['iata'],{}))
        result = []
        for r in rows:
            lows, mids, highs = [], [], []
            for col, weight in ww.items():
                mi, ma = normalized[col]
                if col == 'dist_bases_km': value = min(float(r['dist_msk_km']),float(r['dist_ekb_km']))
                elif col == 'competitor_hub':
                    value = float(r['iata'] in {'KJA','IKT','VVO'}) if case == 'team_original' else (1. if r['iata'] in (known_bases | possible_bases if case=='expanded_base_leads_stress' else known_bases) else None)
                else: value = number(r.get(col))
                if case == 'team_original' and value is None:
                    value = .5 if col == 'transfer_zone' else 0.
                if value is None:
                    a,b=0.,1.
                else:
                    a=b=(value-mi)/(ma-mi) if ma>mi else 0.
                    if col in negative: a=b=1-a
                    # Airport lower bounds and approximate totals are not exact quantities.
                    if case != 'team_original' and col == 'pax_2025':
                        if '>' in r['pax_2025_qualifier']: b=1.
                        elif r['pax_2025_qualifier'] != '=':
                            a=max(0,(value*.95-mi)/(ma-mi));b=min(1,(value*1.05-mi)/(ma-mi))
                    # IKT international-transfer absence does not establish domestic absence.
                    if case != 'team_original' and col == 'transfer_zone' and r['iata']=='IKT': a,b=0.,1.
                lows.append(weight*a); highs.append(weight*b); mids.append(weight*(a+b)/2)
                crit_rows.append(dict(case=case,iata=r['iata'],criterion=col,weight=weight,
                    utility_low=a,utility_mid_scenario=(a+b)/2,utility_high=b,
                    source=r.get({'transfer_zone':'transfer_source','rostec_link':'rostec_source','pax_2025':'pax_source_url','competitor_hub':'base_source'}.get(col,''),'') or 'docs/22; frozen longlist; no empirical OD interpretation',
                    as_of=AS_OF,period='mixed: census 2021; airport 2025; schedule Jun-Dec2026; restrictions trailing365d',
                    unit='unitless normalized screening utility; NOT demand',geography=r['iata'],
                    competitor_evidence=competitor_status.get(r['iata'],'UNKNOWN; no claim absence of base/strength')))
            total=sum(ww.values())
            result.append(dict(case=case,iata=r['iata'],city=r['city'],score_low=sum(lows)/total,
                               score_mid_scenario=sum(mids)/total,score_high=sum(highs)/total,
                               min_distance_existing_base_km=min(float(r['dist_msk_km']),float(r['dist_ekb_km'])),
                               **META))
        result.sort(key=lambda r:(-r['score_mid_scenario'],r['iata']))
        for i,r in enumerate(result,1):
            r['rank_mid_scenario']=i
            r['possible_best_rank']=1+sum(s['score_low']>r['score_high'] for s in result if s!=r)
            r['possible_worst_rank']=1+sum(s['score_high']>=r['score_low'] for s in result if s!=r)
        case_top[case]=[r['iata'] for r in result[:3]]
        rank_rows.extend(result)
    team_file=csvin(ROOT/'data/processed/longlist_scores.csv')
    for r in rank_rows:
        if r['case']=='team_original':
            orig=next(x for x in team_file if x['iata']==r['iata'])
            assert abs(round(r['score_mid_scenario'],3)-float(orig['score']))<1e-9
    csvout('city_scores.csv',rank_rows);csvout('city_criterion_intervals.csv',crit_rows)
    distance=[]
    for c in cases:
        rr=[r for r in rank_rows if r['case']==c]
        for limit in [0,300,500,750]:
            selected=sorted([r for r in rr if r['min_distance_existing_base_km']>=limit], key=lambda r:r['rank_mid_scenario'])
            distance.append(dict(case=c,scenario_min_distance_km=limit,top3=' > '.join(r['iata'] for r in selected[:3]),
                                 excluded=';'.join(r['iata'] for r in rr if r not in selected),
                                 status='SENSITIVITY_ONLY_NOT_DISPATCH_OR_HARD_GATE'))
    csvout('city_distance_sensitivity.csv',distance)
    # Original --min-dist renormalizes after filtering: reproduce it separately.
    subset=[r for r in rank_rows if r['case']=='team_original' and r['min_distance_existing_base_km']>=500]
    prepared=[]
    for r in frozen_rows:
        if min(float(r['dist_msk_km']),float(r['dist_ekb_km']))<500:continue
        vals={col:(min(float(r['dist_msk_km']),float(r['dist_ekb_km'])) if col=='dist_bases_km' else
                   float(r['iata'] in {'KJA','IKT','VVO'}) if col=='competitor_hub' else
                   number(r.get(col)) if number(r.get(col)) is not None else .5 if col=='transfer_zone' else 0.) for col in w}
        prepared.append((r['iata'],vals))
    reproduced=[]
    for i,vals in prepared:
        score=0
        for col,weight in w.items():
            lo=min(v[col] for _,v in prepared);hi=max(v[col] for _,v in prepared)
            z=(vals[col]-lo)/(hi-lo) if hi>lo else 0
            score+=weight*(1-z if col in negative else z)
        reproduced.append(dict(iata=i,score=score/sum(w.values()),scenario='historical team --min-dist500, renormalized subset; SENSITIVITY only'))
    stored={r['iata']:float(r['score']) for r in csvin(ROOT/'data/processed/longlist_scores_min500.csv')}
    assert all(abs(round(r['score'],3)-stored[r['iata']])<1e-9 for r in reproduced)
    csvout('team_min500_reproduced.csv',sorted(reproduced,key=lambda r:-r['score']))
    old=csvin(SCREEN/'ranking.csv');old_inputs=jsin(SCREEN/'inputs.json'); technical=[]
    for name,ww in old_inputs['weights'].items():
        base=[r for r in old if r['scope']=='new_node' and r['weights']==name]
        for case in ['historical','technical_equal','omit_technical_and_basing']:
            ww2=dict(ww)
            if case=='omit_technical_and_basing':ww2['technical']=ww2['basing']=0
            calc=[]
            for r in base:
                v={k:float(r[k]) for k in ww2}
                if case=='technical_equal':v['technical']=100
                s=sum(v[k]*ww2[k] for k in ww2)/sum(ww2.values())
                # Original intervals must not be reused for new weights.
                low=sum((0 if k in ['technical','basing'] else v[k])*ww2[k] for k in ww2)/sum(ww2.values())
                high=sum((100 if k in ['technical','basing'] else v[k])*ww2[k] for k in ww2)/sum(ww2.values())
                calc.append(dict(case=case,weights=name,iata=r['iata'],score=s,
                                 unknown_technical_basing_low=low,unknown_technical_basing_high=high,
                                 source='context/11_practical_screening/ranking.csv + inputs.json',as_of=AS_OF,
                                 period='historical screen 2026-11-08; utilities, not new economics',unit='score 0..100',geography=r['iata']))
            for i,r in enumerate(sorted(calc,key=lambda r:-r['score']),1):r['rank']=i;technical.append(r)
    csvout('old_score_technical_bias.csv',technical)
    dump('ranking_notes.json',dict(top3=case_top,old_top3='GOJ/UFA/GSV in historical new_node base scope',
        unknown_intervals='bounding utility scenarios, NOT confidence intervals; midpoint is only a scenario',
        competitor_correction='MRV/AER/MCX manual statement; TJM indexed primary home-carrier statement accepted by parent; KZN lead separately tested; dominance/route share UNKNOWN',
        neutral='removes criteria where data discovery itself earns points/penalties; no airport total precise ranking',
        population='gap_pop and airport pax NEVER used to generate OD; structural screen only',
        sweep='random-weight top3 share in team CSV is frequency under arbitrary weight sampling, NOT probability of correct choice',
        count=len(rows)))
    return case_top


class Model:
    def __init__(self):
        self.old=jsin(LEGACY/'inputs.json')
        self.oldscreen=jsin(SCREEN/'inputs.json')
        self.geo={r['iata']:r for r in jsin(SCREEN/'coordinates.json')}
        self.sources=jsin(LEGACY/'sources.json')
        self.rules=jsin(LEGACY/'schedule_rules.json')
        self.competition=csvin(LEGACY/'competition.csv')
        self.blocks={(r['origin'],r['destination']):r for r in csvin(LEGACY/'block_times.csv')}
        self.published=csvin(LEGACY/'published_flight_dates.csv')
        self.longlist=csvin(ROOT/'data/processed/longlist.csv')
        self.cfg=dict(active_aircraft=4,spare_aircraft=1,seats=100,work_days=6,
            planning_cap_block_h=10,span_cap_h=16,turn_minutes=45,bank_wait_minutes=75,
            min_connection_minutes=60,max_connection_minutes=240,max_detour=1.6,
            block_time_factor=1.,spare_location_direct='SVX',reserve_mobilisation_minutes=120,
            fleet_fixed_rub_aircraft_week=None,opportunity_rub_block_hour=None,
            new_base_fixed_rub_week=None,disruption_compensation_rub_journey=5000)
        self.overrides=jsin(OUT/'overrides.json')
        self.sources.extend(self.overrides.get('source_records',[]))
        self.cfg.update(self.overrides.get('config',{}))
        self.scenarios=copy.deepcopy(self.old['scenarios'])
        for sc,p in self.overrides.get('scenarios',{}).items():self.scenarios[sc].update(p)
        self.markets={r['pair']:copy.deepcopy(r) for r in self.old['markets']}
        self.new_markets=set()
        self.rw=Counter()
        # Published legacy table has no week field: use exact dates and dedupe.
        unique={(r['origin'],r['destination'],r['date'],r['flight']):r for r in self.published
                if WEEK<=r['date']<='2026-12-13' and r['flight'].startswith('WZ-')}
        for r in unique.values():self.rw[(r['origin'],r['destination'])]+=100
        self.networks={}
        self.bank_details=[]
        self.airport_technical='UNVERIFIED slots/crew/TO/airport windows; no ready-base claim'
        self._distance_cache={}
        self._block_cache={}

    def distance(self,a,b):
        k=pair(a,b)
        if k not in self._distance_cache:
            x,y=self.geo[a],self.geo[b]
            la,lb=map(math.radians,[x['lat'],y['lat']]);dl=math.radians(y['lon']-x['lon'])
            self._distance_cache[k]=12742*math.asin(min(1,math.sqrt(math.sin((lb-la)/2)**2+math.cos(la)*math.cos(lb)*math.sin(dl/2)**2)))
        return self._distance_cache[k]

    def block(self,a,b,cfg=None):
        c=cfg or self.cfg
        key=(a,b)
        override=self.overrides.get('block_minutes',{}).get(a+'-'+b)
        v=override if override is not None else (float(self.blocks[key]['minutes']) if key in self.blocks
            else math.ceil((30+self.distance(a,b)*1.10/700*60)/5)*5)
        return int(math.ceil(v*c['block_time_factor']))

    def band_values(self,a,b):
            d=self.distance(a,b)
            # A common distance-band experiment, not GOJ city-name substitution or airport-pax regression.
            if d<600: dc,db,fc,fb,band=40,120,3500,5000,'short_under600km'
            elif d<1200:dc,db,fc,fb,band=80,200,6500,9000,'regional600_1200km'
            elif d<1800:dc,db,fc,fb,band=100,260,8000,11000,'regional1200_1800km'
            else:dc,db,fc,fb,band=120,320,10500,14000,'long_over1800km'
            south=bool(set((a,b))&{'AER','MRV'})
            mult=1.5 if south else 1.
            return dict(local_pair=True,demand_cautious=dc*mult,demand_base=db*mult,
                fare_cautious=fc,fare_base=fb,capture_group='uncertain',cannibal_base=.05,cannibal_cautious=.1,
                old_rw_segments=2,transfer_competition_factor=.65,
                evidence='UNKNOWN paid OD, competitor calendar, net fare and own connecting sales',sources=[],
                range_basis=f'ANALYST ASSUMPTION common {band}; south scenario x{mult}; no fitted demand model; scale probe only',
                demand_stress_range=f'0–{2*db*mult:g}',band=band)

    def market(self,a,b):
        key=pair(a,b)
        if key not in self.markets:
            self.markets[key]=dict(pair=key,**self.band_values(a,b))
            self.new_markets.add(key)
        self.markets[key].update(self.overrides.get('markets',{}).get(key,{}))
        return self.markets[key]

    def valid_transfer(self,a,h,b,cfg=None):
        c=cfg or self.cfg
        return (a!=b and (self.distance(a,h)+self.distance(h,b))/max(1,self.distance(a,b))<=c['max_detour'])

    def best_partition(self,h,leaves,k,cfg=None):
        """Finite partitions of a bank, not route-network global optimisation."""
        c=cfg or self.cfg
        options=[]
        for left in itertools.combinations(sorted(leaves),k):
            right=tuple(sorted(set(leaves)-set(left)))
            valid=sum(self.valid_transfer(a,h,b) for a in left for b in right)
            # Tie break by total imbalance of job block, then stable lexicographic bank.
            imbalance=abs(sum(self.block(h,a)+self.block(a,h) for a in left)-sum(self.block(h,b)+self.block(b,h) for b in right))
            job=lambda x:self.block(h,x,c)+self.block(x,h,c)
            def bad_pair(x,y):
                minutes=job(x)+job(y)
                return minutes>c['planning_cap_block_h']*60 or minutes+2*c['turn_minutes']+c['bank_wait_minutes']>c['span_cap_h']*60 or c['bank_wait_minutes']<c['turn_minutes']
            bad=min(sum(bad_pair(left[i],right[j]) for i,j in enumerate(perm)) for perm in itertools.permutations(range(k)))
            # Feasible allocation has precedence over adding theoretical connections.
            options.append((bad,-valid,imbalance,tuple(left),right))
        _,_,_,a,b=min(options)
        return a,b

    def add_leg(self,legs,n,day,tail,a,b,start,c):
        v=self.block(a,b,c)
        index=len(legs)
        legs.append(dict(network=n,day=day,date=(dt.date.fromisoformat(WEEK)+dt.timedelta(days=day-1)).isoformat(),
            aircraft=tail,origin=a,destination=b,departure_utc_minute=(day-1)*1440+start,
            arrival_utc_minute=(day-1)*1440+start+v,block_minutes=v,
            id=f'{n}-D{day}-{index:03d}',capacity=c['seats'],
            block_method='parent override' if a+'-'+b in self.overrides.get('block_minutes',{}) else
             (self.blocks[(a,b)]['method'] if (a,b) in self.blocks else 'SCENARIO 30min+distance*1.10/700kmh rounded5min'),
            source='context/12_network_economics/block_times.csv' if (a,b) in self.blocks else 'coordinates.json + analyst block method',
            physical_status=self.airport_technical))
        return start+v+c['turn_minutes']

    def hub(self,h,frequency,cfg=None):
        c=cfg or self.cfg
        n=f'H_{h}_{frequency}'
        spokes={
          'GOJ':['OMS','KUF','MMK','UFA','AER','VOG','ARH','MRV'],
          'UFA':['GOJ','KUF','OMS','NJC','VOG','MRV','ARH','GSV'],
          'CEK':['GOJ','KUF','OMS','NJC','VOG','MRV','UFA','GSV'],
          'TJM':['GOJ','KUF','OMS','NJC','VOG','PEE','UFA','GSV'],
          'PEE':['GOJ','KUF','OMS','NJC','VOG','MRV','UFA','GSV']}[h]
        dense=self.best_partition(h,spokes,4,c)
        if frequency=='dense':banks=[dense]*c['work_days']
        else:
            groups=self.best_partition(h,spokes,4,c)
            banks=[self.best_partition(h,groups[i%2],2,c) for i in range(c['work_days'])]
        legs=[]
        for day,(a,b) in enumerate(banks,1):
            # Both directions are offered on different service dates in the same week.
            if (day-1)//(1 if frequency=='dense' else 2)%2:a,b=b,a
            am=list(a);pm=list(b);k=len(am)
            best=None
            for perm in itertools.permutations(range(k)):
                bad=0;peak=0;spans=[]
                for i,j in enumerate(perm):
                    bh=(self.block(h,am[i],c)+self.block(am[i],h,c)+self.block(h,pm[j],c)+self.block(pm[j],h,c))/60
                    start=720-self.block(h,am[i],c)-c['turn_minutes']-self.block(am[i],h,c)
                    end=720+c['bank_wait_minutes']+self.block(h,pm[j],c)+c['turn_minutes']+self.block(pm[j],h,c)
                    bad+=bh>c['planning_cap_block_h'] or (end-start)/60>c['span_cap_h'] or c['bank_wait_minutes']<c['turn_minutes']
                    peak=max(peak,bh);spans.append((end-start)/60)
                option=(bad,peak,perm)
                if best is None or option<best:best=option
            bad,_,perm=best
            nexttail=k
            for i,j in enumerate(perm):
                first=f'{h}{i+1}'
                bh=(self.block(h,am[i],c)+self.block(am[i],h,c)+self.block(h,pm[j],c)+self.block(pm[j],h,c))/60
                start=720-self.block(h,am[i],c)-c['turn_minutes']-self.block(am[i],h,c)
                end=720+c['bank_wait_minutes']+self.block(h,pm[j],c)+c['turn_minutes']+self.block(pm[j],h,c)
                tail=first
                if bh>c['planning_cap_block_h'] or (end-start)/60>c['span_cap_h'] or c['bank_wait_minutes']<c['turn_minutes']:
                    nexttail+=1;tail=f'{h}{nexttail}'
                t=self.add_leg(legs,n,day,first,h,am[i],start,c)
                self.add_leg(legs,n,day,first,am[i],h,t,c)
                t=self.add_leg(legs,n,day,tail,h,pm[j],720+c['bank_wait_minutes'],c)
                self.add_leg(legs,n,day,tail,pm[j],h,t,c)
            self.bank_details.append(dict(network=n,day=day,morning=';'.join(am),afternoon=';'.join(pm),
                matching=';'.join(am[i]+'→'+pm[j] for i,j in enumerate(perm)),
                active_required=k+bad,enumeration='all bank bipartitions; all daily AM/PM job permutations; no route-set global search'))
        return dict(name=n,hub=h,kind='hub',frequency=frequency,legs=legs,cfg=c)

    def direct(self,frequency,cfg=None):
        c=cfg or self.cfg;n='B0' if frequency=='original' else 'B_sparse'
        legs=[]
        days=range(1,c['work_days']+1) if frequency=='original' else [1,2,4,5]
        for day in days:
            for i,cycle in enumerate(self.oldscreen['direct_cycles'],1):
                route=cycle if day%2 else cycle[::-1]
                t=300
                for a,b in zip(route,route[1:]):t=self.add_leg(legs,n,day,f'D{i}',a,b,t,c)
        return dict(name=n,hub=None,kind='direct',frequency=frequency,legs=legs,cfg=c)

    def audit(self,net):
        c=net['cfg'];legs=net['legs'];issues=[];days=[]
        for tail in sorted({r['aircraft'] for r in legs}):
            alllegs=sorted([r for r in legs if r['aircraft']==tail],key=lambda r:r['departure_utc_minute'])
            for a,b in zip(alllegs,alllegs[1:]):
                if a['destination']!=b['origin']:issues.append('spatial_discontinuity '+tail)
                if a['arrival_utc_minute']+c['turn_minutes']>b['departure_utc_minute']:issues.append('turn_or_overlap '+tail)
            if alllegs[0]['origin']!=alllegs[-1]['destination']:issues.append('weekly_wrap '+tail)
            for day in range(1,c['work_days']+1):
                rr=[r for r in alllegs if r['day']==day]
                if not rr:continue
                h=sum(r['block_minutes'] for r in rr)/60
                span=(rr[-1]['arrival_utc_minute']-rr[0]['departure_utc_minute'])/60
                if h>c['planning_cap_block_h']+1e-9:issues.append('block_cap '+tail+str(day))
                if span>c['span_cap_h']+1e-9:issues.append('span_cap '+tail+str(day))
                days.append(dict(network=net['name'],day=day,aircraft=tail,start_airport=rr[0]['origin'],
                    end_airport=rr[-1]['destination'],block_hours=h,span_hours=span,
                    block_cap=c['planning_cap_block_h'],span_cap=c['span_cap_h'],turn=c['turn_minutes'],
                    physical_continuity_status='PASS' if all(a['destination']==b['origin'] and a['arrival_utc_minute']+c['turn_minutes']<=b['departure_utc_minute'] for a,b in zip(rr,rr[1:])) else 'FAIL'))
        peak=max(Counter(r['day'] for r in days).values(),default=0)
        if peak>c['active_aircraft']:issues.append('active_aircraft_cap')
        budget=c['active_aircraft']*c['work_days']*c['planning_cap_block_h']
        hours=sum(r['block_minutes'] for r in legs)/60
        # A spare is not a fifth scheduled working tail.
        reserve_requirement=max(1,len({r['origin'] for r in legs if r['aircraft'].startswith('D') and r['departure_utc_minute']%1440==300})) if net['kind']=='direct' else 1
        return dict(network=net['name'],feasible=not issues,issues=';'.join(issues),active_peak=peak,
            weekly_legs=len(legs),weekly_block_hours=hours,unused_block_budget_hours=budget-hours,
            max_daily_span_hours=max((d['span_hours'] for d in days),default=0),
            max_daily_block_hours=max((d['block_hours'] for d in days),default=0),
            active_aircraft_limit=c['active_aircraft'],spares=c['spare_aircraft'],fleet_total_condition=c['active_aircraft']+c['spare_aircraft'],
            reserve_locations=net['hub'] or c['spare_location_direct'],
            uncovered_bases_if_simultaneous_AOG=max(0,reserve_requirement-c['spare_aircraft']),
            caveat='algebraic continuity only; slots, crews, TO and actual aircraft availability UNVERIFIED'),days

    def itineraries(self,net):
        out=defaultdict(list);legs=net['legs'];c=net['cfg'];h=net['hub']
        for l in legs:
            out[(l['origin'],l['destination'])].append(dict(day=l['day'],legs=[l['id']],transfer=False,wait_minutes=0))
        if h:
            for a in legs:
                if a['destination']!=h:continue
                for b in legs:
                    if b['origin']!=h or a['day']!=b['day']:continue
                    wait=b['departure_utc_minute']-a['arrival_utc_minute']
                    if c['min_connection_minutes']<=wait<=c['max_connection_minutes'] and self.valid_transfer(a['origin'],h,b['destination'],c):
                        out[(a['origin'],b['destination'])].append(dict(day=a['day'],legs=[a['id'],b['id']],transfer=True,wait_minutes=wait))
        for a,b in out:self.market(a,b)
        return out

    def make_networks(self):
        for f in ['original','sparse']:
            n=self.direct(f);n['itineraries']=self.itineraries(n);self.networks[n['name']]=n
        for h in ['GOJ','UFA','CEK','TJM','PEE']:
            for f in ['dense','compact']:
                n=self.hub(h,f);n['itineraries']=self.itineraries(n);self.networks[n['name']]=n

    def flight_cost(self,l,sc):
        p=self.scenarios[sc];h=l['block_minutes']/60
        return ((p['fuel_t_per_hour']*h+p['fuel_t_per_cycle'])*(p['fuel_rub_per_t']+p['fuel_uplift_rub_per_t'])
            +h*(p['mro_rub_per_hour']+p['crew_rub_per_hour']+p['navigation_rub_per_hour'])
            +self.old['ufa_reference_basket_rub']*p['airport_factor']+p['deicing_probability']*p['deicing_operation_rub'])

    def rw_cap(self,a,b):
        return self.markets[pair(a,b)].get('rw_direct_seats_'+a,self.rw.get((a,b)))

    def evaluate(self,net,sc,priority='local_first',fare_scale=1,cost_scale=1,demand_scale=1,
                 transfer_scale=1,market_scales=None,migration_scale=1,transfer_fare_scale=1,detail=False):
        p=self.scenarios[sc];c=net['cfg'];caps={l['id']:float(c['seats']) for l in net['legs']}
        offers=[];market_scales=market_scales or {}
        for (a,b),its in net['itineraries'].items():
            m=self.markets[pair(a,b)];f=len(its);trans=its[0]['transfer']
            D=m['demand_'+sc]*demand_scale*market_scales.get(m['pair'],1)
            q=p['capture_'+('transfer' if trans else m['capture_group'])]*(1-math.exp(-f/p['frequency_scale']))
            if trans:q=min(1,q*m.get('transfer_competition_factor',1)*transfer_scale)
            fare=m['fare_'+sc]*fare_scale*(p['transfer_fare_factor']*transfer_fare_scale if trans else 1)
            can=min(1,m['cannibal_'+sc]*migration_scale)
            oldfare=m['fare_'+sc]*p['old_RW_fare_ratio']
            for it in its:
                offers.append(dict(origin=a,destination=b,market=m['pair'],D=D,desired=D*q/f,
                    reference_market_fare=m['fare_'+sc],transfer_fare_factor=p['transfer_fare_factor']*transfer_fare_scale if trans else 1,
                    effective_fare=fare,oldfare=oldfare,can=can,**it))
        offers.sort(key=lambda o:((o['transfer'] if priority=='local_first' else not o['transfer']),
            -(o['effective_fare']-o['can']*o['oldfare']-len(o['legs'])*p['pax_cost'])/len(o['legs']),
            o['origin'],o['destination'],o['day'],tuple(o['legs'])))
        migration_left=dict(self.rw)
        for a,b in net['itineraries']:
            cap=self.rw_cap(a,b)
            if cap is not None:migration_left[(a,b)]=cap
        sales=[]
        totals=Counter();byod=Counter()
        for o in offers:
            sold=min(o['desired'],*(caps[i] for i in o['legs']))
            for i in o['legs']:caps[i]-=sold
            k=(o['origin'],o['destination']);m=self.markets[o['market']]
            observedcap=self.rw_cap(*k)
            migrated_direct=min(sold*o['can'],migration_left.get(k,0))
            migration_left[k]=migration_left.get(k,0)-migrated_direct
            migrated_unknown=(sold*o['can']-migrated_direct) if observedcap is None or m['old_rw_segments']>=2 else 0.
            migrated=migrated_direct+migrated_unknown
            oldsegments=migrated_direct+2*migrated_unknown
            values=dict(sold_journeys=sold,transfer_journeys=sold if o['transfer'] else 0,
                local_journeys=sold if not o['transfer'] else 0,segment_pax=sold*len(o['legs']),
                migrated_RW_direct=migrated_direct,migrated_RW_unverified_connecting=migrated_unknown,
                migrated_RW_total=migrated,net_new_journeys=sold-migrated,
                gross_revenue=sold*o['effective_fare'],foregone_RW_revenue=migrated*o['oldfare'],
                incremental_revenue=sold*o['effective_fare']-migrated*o['oldfare'],
                new_pax_variable=sold*len(o['legs'])*p['pax_cost']*cost_scale,
                saved_old_pax_variable=oldsegments*p['pax_cost']*cost_scale,
                old_RW_segment_pax=oldsegments)
            totals.update(values);byod[k]+=sold
            if detail:sales.append(dict(network=net['name'],scenario=sc,priority=priority,
                origin=o['origin'],destination=o['destination'],date=(dt.date.fromisoformat(WEEK)+dt.timedelta(days=o['day']-1)).isoformat(),
                flight_ids=';'.join(o['legs']),transfer=o['transfer'],wait_minutes=o['wait_minutes'],
                D_OD_week_direction=o['D'],desired_pax=o['desired'],reference_market_fare=o['reference_market_fare'],
                transfer_fare_factor=o['transfer_fare_factor'],effective_fare=o['effective_fare'],
                migration_direct_seat_cap=observedcap,unverified_connecting_capacity='UNKNOWN; fractional scenario only',**values))
        flightcost=sum(self.flight_cost(l,sc) for l in net['legs'])*cost_scale
        contrib=totals['incremental_revenue']-flightcost-totals['new_pax_variable']+totals['saved_old_pax_variable']
        hours=sum(l['block_minutes'] for l in net['legs'])/60
        result=dict(network=net['name'],scenario=sc,priority=priority,**totals,flight_variable_cost=flightcost,
            incremental_operating_cost=flightcost+totals['new_pax_variable']-totals['saved_old_pax_variable'],
            contribution_before_base_fleet_opportunity=contrib,weekly_block_hours=hours,weekly_legs=len(net['legs']),
            seats=len(net['legs'])*c['seats'],load_factor=totals['segment_pax']/max(1,len(net['legs'])*c['seats']),
            incremental_segment_pax=totals['segment_pax']-totals['old_RW_segment_pax'],
            configured_base_fixed_rub_week=c['new_base_fixed_rub_week'] if net['hub'] else 0,
            fleet_fixed_rub_week=None if c['fleet_fixed_rub_aircraft_week'] is None else (c['active_aircraft']+c['spare_aircraft'])*c['fleet_fixed_rub_aircraft_week'],
            opportunity_rub_week=None if c['opportunity_rub_block_hour'] is None else hours*c['opportunity_rub_block_hour'],**META)
        fixed=result['fleet_fixed_rub_week'];opp=result['opportunity_rub_week'];base=result['configured_base_fixed_rub_week']
        result['contribution_after_configured_fixed_costs']=None if any(x is None for x in [fixed,opp,base]) else contrib-fixed-opp-base
        assert all(-1e-7<=v<=c['seats']+1e-7 for v in caps.values())
        assert abs(sum(c['seats']-v for v in caps.values())-totals['segment_pax'])<1e-5
        assert abs(totals['sold_journeys']+totals['transfer_journeys']-totals['segment_pax'])<1e-5
        assert abs(totals['sold_journeys']-totals['net_new_journeys']-totals['migrated_RW_total'])<1e-5
        assert abs(totals['gross_revenue']-totals['foregone_RW_revenue']-totals['incremental_revenue'])<1e-5
        for (a,b),sold in byod.items():
            assert sold<=self.markets[pair(a,b)]['demand_'+sc]*demand_scale*market_scales.get(pair(a,b),1)+1e-6
        if detail:
            for s in sales:
                assert abs(s['sold_journeys']*s['effective_fare']-s['gross_revenue'])<1e-5
            for k in net['itineraries']:
                cap=self.rw_cap(*k)
                if cap is not None:assert sum(s['migrated_RW_direct'] for s in sales if (s['origin'],s['destination'])==k)<=cap+1e-6
            capacity=[dict(**l,scenario=sc,priority=priority,
                sold_segment_pax=c['seats']-caps[l['id']],remaining_seats=caps[l['id']],
                flight_variable_cost=self.flight_cost(l,sc)*cost_scale) for l in net['legs']]
        else:capacity=[]
        return result,sales,capacity


def reinforcements(model):
    rows=[];accepted=[]
    for sc in ['base','cautious']:
        initial=model.evaluate(model.networks['B0'],sc)[0]['contribution_before_base_fleet_opportunity']
        for key,index in [('AER-GSV',1),('OMS-SVX',2)]:
            for count in range(1,7):
                n=f'B_add_{key}_{count}';legs=[];c=model.cfg
                for day in range(1,7):
                    for i,cycle in enumerate(model.oldscreen['direct_cycles']):
                        route=list(cycle if day%2 else cycle[::-1])
                        if i==index and day<=count:
                            if key=='AER-GSV':
                                j=route.index('GSV');route=route[:j+1]+['AER','GSV']+route[j+1:]
                            else:route+=['OMS','SVX']
                        t=300
                        for a,b in zip(route,route[1:]):t=model.add_leg(legs,n,day,f'D{i+1}',a,b,t,c)
                net=dict(name=n,hub=None,kind='direct',frequency='marginal_enumeration',legs=legs,cfg=c)
                net['itineraries']=model.itineraries(net)
                audit,_=model.audit(net);r=model.evaluate(net,sc)[0]
                delta=r['contribution_before_base_fleet_opportunity']-initial
                good=audit['feasible'] and delta>0
                rows.append(dict(scenario=sc,network=n,pair=key,days_added=count,added_legs=len(legs)-72,
                    feasible=audit['feasible'],issues=audit['issues'],incremental_contribution_vs_B0=delta,
                    accepted_marginal=good,rule='only add when feasible AND total incremental contribution > 0; no equal-hours target'))
                if good and sc=='base':accepted.append(net)
    csvout('direct_reinforcement.csv',rows)
    # Preserve B0 even if a marginal variant is acceptable.
    for n in accepted:model.networks[n['name']]=n
    return rows


def export_registry(model):
    source_map={r['id']:r for r in model.sources}
    rows=[]
    for key,m in sorted(model.markets.items()):
        a,b=key.split('-')
        sources=m.get('sources',[])
        urls=';'.join(source_map[s]['url'] for s in sources if s in source_map)
        rows.append(dict(pair=key,observed_OD=m.get('observed_OD'),observed_net_fare=m.get('observed_net_fare'),
            scenario_OD_cautious=m['demand_cautious'],scenario_OD_base=m['demand_base'],
            empirical_OD_lower=m.get('empirical_OD_lower'),empirical_OD_upper=m.get('empirical_OD_upper'),
            scenario_stress_OD_low=0,scenario_stress_OD_high=2*m['demand_base'],
            net_fare_cautious_RUB_journey=m['fare_cautious'],net_fare_base_RUB_journey=m['fare_base'],
            straight_line_km=model.distance(a,b),capture_group=m['capture_group'],
            known_RW_direct_seats_A_to_B=model.rw_cap(a,b),known_RW_direct_seats_B_to_A=model.rw_cap(b,a),
            RW_seats_status='published dated-flight lower observed inventory; absent key UNKNOWN, not zero market',
            origin='NEW_COMMON_DISTANCE_BAND_SCENARIO' if key in model.new_markets else 'EXACT_SAME_OD_LEGACY_SCENARIO',
            source_ids=';'.join(sources),source_urls=m.get('source_urls',urls or None),
            source='context/12_network_economics/inputs.json' if key not in model.new_markets else 'analyst common distance bands + context/11_practical_screening/coordinates.json',
            evidence=m.get('evidence','UNKNOWN'),method=m['range_basis'],
            as_of=AS_OF,period='2026-12-07/13 hypothetical winter week; legacy analog KUF-MRV annual2025 segments only',
            geography=key,unit='endpoint journeys/week/direction and RUB/net one-way journey',
            unknown_reason='no comparable paid OD/month/direction panel or matched realised fares in frozen inputs'))
    csvout('od_registry.csv',rows)
    dump('od_registry.json',dict(metadata=META,markets=model.markets,
        note='One canonical pair object across every alternative; airport pax/gap_pop are not an OD conversion. Empirical bounds remain NULL; 0..2x base is a stress scenario, not a confidence interval.'))


def resource_sensitivity(model):
    rows=[]
    configs=[('default',{})]
    for cap in [8,12]:configs.append((f'block_cap_{cap}',dict(planning_cap_block_h=cap)))
    configs += [('turn60',dict(turn_minutes=60)),('turn90',dict(turn_minutes=90)),
        ('span12',dict(span_cap_h=12)),('block_plus10',dict(block_time_factor=1.1)),
        ('block_plus20',dict(block_time_factor=1.2)),('active3',dict(active_aircraft=3)),
        ('spare0',dict(spare_aircraft=0)),('spare2',dict(spare_aircraft=2)),
        ('bank120',dict(bank_wait_minutes=120))]
    banklen=len(model.bank_details)
    for label,delta in configs:
        c={**model.cfg,**delta}
        for old in list(model.networks.values()):
            if old['kind']=='direct' and old['name'] not in ['B0','B_sparse']:continue
            n=model.direct(old['frequency'],c) if old['kind']=='direct' else model.hub(old['hub'],old['frequency'],c)
            r,_=model.audit(n);r.update(test=label,config_delta=json.dumps(delta,sort_keys=True));rows.append(r)
    model.bank_details=model.bank_details[:banklen]
    csvout('resource_sensitivity.csv',rows)
    return rows


def sensitivity(model,feasible):
    rows=[];thresholds=[];maxima=[];leader_switch=[]
    grids={
        'cost_scale':[i/20 for i in range(5,36)],
        'fare_scale':[i/10 for i in range(5,31)],
        'demand_scale':[i/4 for i in range(0,41)]+[16.,32.,1000.],
        'transfer_scale':[i/10 for i in range(0,101)]+[20.,50.,1000.],
        'transfer_market_scale':[i/4 for i in range(0,41)]+[16.,32.,1000.],
        'migration_scale':[0.,.5,1.,2.,4.],
        'transfer_fare_scale':[.5,.7,.85,1.,1.15,1.3,1.5,2.],
        'new_base_cost_week':[float(i*500000) for i in range(21)]}
    transfer_keys={pair(a,b) for n in model.networks.values() for (a,b),its in n['itineraries'].items() if its[0]['transfer']}
    for sc in ['base','cautious']:
        for priority in ['local_first','transfer_first']:
            for parameter,grid in grids.items():
                cache={}
                def run(x):
                    if x not in cache:
                        kw=({} if parameter=='new_base_cost_week' else {parameter:x}) if parameter!='transfer_market_scale' else dict(market_scales={k:x for k in transfer_keys})
                        cache[x]={n:model.evaluate(model.networks[n],sc,priority,**kw)[0] for n in feasible}
                        if parameter=='new_base_cost_week':
                            for nn,rr in cache[x].items():
                                if model.networks[nn]['hub']:rr['contribution_before_base_fleet_opportunity']-=x
                    return cache[x]
                for x in grid:
                    rr=run(x)
                    bestdirect=max((r['contribution_before_base_fleet_opportunity'] for n,r in rr.items() if model.networks[n]['kind']=='direct'),default=0)
                    for n,r in rr.items():
                        rows.append(dict(scenario=sc,priority=priority,parameter=parameter,value=x,network=n,
                            contribution=r['contribution_before_base_fleet_opportunity'],transfer_journeys=r['transfer_journeys'],
                            sold_journeys=r['sold_journeys'],best_direct=bestdirect,
                            gap_vs_direct=r['contribution_before_base_fleet_opportunity']-bestdirect,
                            gap_vs_zero=r['contribution_before_base_fleet_opportunity'],
                            note='one-at-a-time; shared OD. For new_base_cost_week contribution is AFTER this scenario base cost; other rows before base. Greedy, not global optimal'))
                # Every bracket is recorded, including repeated crossings. No endpoint called max.
                for n in feasible:
                    if model.networks[n]['kind']!='hub':continue
                    for reference in ['best_direct','zero']:
                        def gap(x):
                            rr=run(x);ref=0 if reference=='zero' else max(r['contribution_before_base_fleet_opportunity'] for nn,r in rr.items() if model.networks[nn]['kind']=='direct')
                            return rr[n]['contribution_before_base_fleet_opportunity']-ref
                        roots=[]
                        for x,y in zip(grid,grid[1:]):
                            gx,gy=gap(x),gap(y)
                            if gx==0:roots.append(x)
                            elif gx*gy<0:
                                lo,hi=x,y
                                for _ in range(25):
                                    mid=(lo+hi)/2
                                    if gap(lo)*gap(mid)<=0:hi=mid
                                    else:lo=mid
                                roots.append((lo+hi)/2)
                        # Distinct CSV row for each crossing; no duplicated grid coordinates.
                        for idx,root in enumerate(sorted(set(round(r,8) for r in roots)),1):
                            thresholds.append(dict(scenario=sc,priority=priority,network=n,parameter=parameter,
                                reference=reference,crossing=idx,root=root,
                                unit='RUB/week' if parameter=='new_base_cost_week' else 'dimensionless multiplier',gap_at_boundary_RUB=gap(root),
                                transfer_journeys_at_boundary=run(root)[n]['transfer_journeys'],
                                sold_journeys_at_boundary=run(root)[n]['sold_journeys'],
                                status=('ZERO_CROSSING_IN_TESTED_BRACKET' if abs(gap(root))<100 else 'SIGN_SWITCH_BOUNDARY_MAY_BE_GREEDY_DISCONTINUITY'),
                                range_low=min(grid),range_high=max(grid)))
                        if not roots:thresholds.append(dict(scenario=sc,priority=priority,network=n,parameter=parameter,
                            reference=reference,crossing=0,root=None,unit='RUB/week' if parameter=='new_base_cost_week' else 'dimensionless multiplier',
                            status='NO_CROSSING_ON_TESTED_GRID; not proof outside range',range_low=min(grid),range_high=max(grid)))
                def winner(x):return max(feasible,key=lambda n:(run(x)[n]['contribution_before_base_fleet_opportunity'],n))
                for x,y in zip(grid,grid[1:]):
                    a,b=winner(x),winner(y)
                    if a!=b:leader_switch.append(dict(scenario=sc,priority=priority,parameter=parameter,
                        lower=x,upper=y,leader_below=a,leader_above=b,
                        interpretation='project-leader change bracket, distinct from zero crossing; intermediate switches may exist'))
                if parameter=='transfer_scale':
                    for n in feasible:
                        rr=[(x,run(x)[n]) for x in grid]
                        xp,rp=max(rr,key=lambda t:t[1]['transfer_journeys'])
                        xc,rc=max(rr,key=lambda t:t[1]['contribution_before_base_fleet_opportunity'])
                        endpoint=run(grid[-1])[n]
                        maxima.append(dict(scenario=sc,priority=priority,network=n,
                            max_transfer_journeys_on_tested_grid=rp['transfer_journeys'],capture_at_grid_max=xp,
                            max_contribution_on_tested_grid=rc['contribution_before_base_fleet_opportunity'],capture_at_contribution_max=xc,
                            transfer_journeys_at_endpoint=endpoint['transfer_journeys'],endpoint_capture=grid[-1],
                            scope='MAX over exactly the saved finite grid and fixed booking heuristic; no global optimum'))
    csvout('sensitivity.csv',rows);csvout('switch_thresholds.csv',thresholds)
    csvout('project_leader_switch_brackets.csv',leader_switch);csvout('grid_maxima.csv',maxima)
    conditions=[]
    for sc in ['base','cautious']:
        for priority in ['local_first','transfer_first']:
            for n in feasible:
                if model.networks[n]['kind']!='hub':continue
                rr=[r for r in rows if r['scenario']==sc and r['priority']==priority and r['network']==n and r['parameter']=='transfer_scale']
                b0=next(r['contribution'] for r in rows if r['scenario']==sc and r['priority']==priority and r['network']=='B0' and r['parameter']=='transfer_scale' and r['value']==0)
                for fixed_base in [0,50000000/52,150000000/52]:
                    for reference in ['B0','best_direct','zero']:
                        def diff(r):return r['contribution']-fixed_base-(b0 if reference=='B0' else r['best_direct'] if reference=='best_direct' else 0)
                        ok=[r for r in rr if diff(r)>=0]
                        hit=min(ok,key=lambda r:r['value']) if ok else None
                        conditions.append(dict(network=n,scenario=sc,priority=priority,reference=reference,
                            fixed_base_RUB_week_scenario=fixed_base,
                            first_capture_multiplier_on_saved_grid=hit['value'] if hit else None,
                            transfer_journeys_at_first_grid_condition=hit['transfer_journeys'] if hit else None,
                            contribution_after_base_at_condition=hit['contribution']-fixed_base if hit else None,
                            max_gap_RUB_on_tested_grid=max(diff(r) for r in rr),
                            status='ALREADY_ABOVE_REFERENCE_WITH_ZERO_TRANSFER' if hit and hit['value']==0 else 'FIRST_PASSING_GRID_POINT_NOT_EXACT_THRESHOLD' if hit else 'NOT_REACHED_ON_SAVED_GRID',
                            interpretation='Fixed local OD/fare; transfers use both dated seats. Fractional scenario passengers, not measured demand. Nonmonotone heuristic; not a global minimum.'))
    csvout('transfer_passenger_conditions.csv',conditions)
    return rows,thresholds,maxima


def fixed_costs(model,summary,audits):
    base=[];fixed=[]
    for r in summary:
        if r['priority']!='local_first':continue
        sc=r['scenario'];n=r['network'];a=audits[n]
        direct=max(x['contribution_before_base_fleet_opportunity'] for x in summary if x['scenario']==sc and x['priority']=='local_first' and audits[x['network']]['feasible'] and model.networks[x['network']]['kind']=='direct')
        value=r['contribution_before_base_fleet_opportunity']
        if model.networks[n]['hub']:
            base.append(dict(network=n,scenario=sc,max_new_base_RUB_week_vs_best_direct=value-direct,
                max_new_base_RUB_year_equivalent_vs_best_direct=(value-direct)*52,
                max_new_base_RUB_week_vs_no_launch=value,
                new_base_actual_cost=None,interpretation='signed tie threshold; negative means no nonnegative affordable base; NOT breakeven budget',**META))
        for reserve in [1,2]:
            for cost in [0,500000,1000000]:
                for opportunity in [0,20000,50000]:
                    fleet=(model.cfg['active_aircraft']+reserve)*cost
                    opp=r['weekly_block_hours']*opportunity
                    fixed.append(dict(network=n,scenario=sc,reserves=reserve,aircraft_total_condition=model.cfg['active_aircraft']+reserve,
                        fleet_fixed_RUB_aircraft_week_scenario=cost,total_fleet_fixed_RUB_week=fleet,
                        opportunity_RUB_used_block_hour_scenario=opportunity,total_opportunity_cost_RUB_week=opp,
                        unused_block_budget_hours=a['unused_block_budget_hours'],
                        contribution_after_fleet_opportunity_before_base=value-fleet-opp,
                        unused_hours_potential_alternative_margin_RUB=a['unused_block_budget_hours']*opportunity,
                        basis='illustrative cost scenarios, actual fixed/opportunity/base UNKNOWN; spare does not add active capacity'))
    csvout('new_base_tie_thresholds.csv',base);csvout('fleet_and_opportunity_scenarios.csv',fixed)
    csvout('replacement_boundary.csv',[dict(scenario='replacement_NOT_CALCULABLE',basis_source='context/14_synthesis NE-10',
        formula='replacement contribution = additive contribution + avoidable old-flight cost - lost old revenue + old variable passenger savings - recapture double counts',
        avoidable_old_flight_cost=None,lost_old_revenue=None,recaptured_old_sales=None,
        interpretation='UNKNOWN; no withdrawal savings credited anywhere in accepted additive comparison',**META)])
    return base


def disruption_scenarios(model,summary,sales):
    rows=[]
    for net in model.networks.values():
        if net['name'] not in {r['network'] for r in summary}:continue
        h=net['hub'];n=net['name']
        for sc in ['base','cautious']:
            base=next(r for r in summary if r['network']==n and r['scenario']==sc and r['priority']=='local_first')
            sold=[s for s in sales if s['network']==n and s['scenario']==sc and s['priority']=='local_first']
            for shock in ['node_closed_day3','correlated_GOJ_KUF_GSV_VOG_day3','AOG_day3_one_spare','AOG_day3_two_spares']:
                closed={h} if h else {'ZIA'}
                if shock.startswith('correlated'):closed={'GOJ','KUF','GSV','VOG'}
                tail=next((r['aircraft'] for r in net['legs'] if r['day']==3),None)
                # Sparse direct operates days1,2,4,5: AOG on next working day instead.
                failed_day=3 if tail else 4
                tail=next((r['aircraft'] for r in net['legs'] if r['day']==failed_day),None)
                failedbase=next((r['origin'] for r in net['legs'] if r['aircraft']==tail and r['day']==failed_day),None)
                reserves=2 if 'two_spares' in shock else model.cfg['spare_aircraft']
                locations=[h]*reserves if h else ([model.cfg['spare_location_direct']] if reserves==1 else ['ZIA','SVX'][:reserves])
                local=failedbase in locations
                reaction=None
                if shock.startswith('AOG'):
                    if local:reaction=0
                    elif locations:reaction=min(model.block(x,failedbase)+model.cfg['reserve_mobilisation_minutes'] for x in locations)
                cancelled=set();end_positions={}
                for aircraft in sorted({r['aircraft'] for r in net['legs']}):
                    rr=sorted([r for r in net['legs'] if r['aircraft']==aircraft],key=lambda r:r['departure_utc_minute'])
                    position=rr[0]['origin']
                    for l in rr:
                        disrupted=(l['day']==3 and (l['origin'] in closed or l['destination'] in closed)) if not shock.startswith('AOG') else (l['day']==failed_day and aircraft==tail and not local)
                        if disrupted or l['origin']!=position:cancelled.add(l['id'])
                        else:position=l['destination']
                    end_positions[aircraft]=position
                lost=[s for s in sold if cancelled & set(s['flight_ids'].split(';'))]
                lost_j=sum(s['sold_journeys'] for s in lost)
                margin=sum(s['incremental_revenue']-s['new_pax_variable']+s['saved_old_pax_variable'] for s in lost)
                compensation=lost_j*model.cfg['disruption_compensation_rub_journey']
                rows.append(dict(network=n,scenario=sc,shock=shock,reserves=reserves,
                    reserve_locations=';'.join(x for x in locations if x),failed_base=failedbase if shock.startswith('AOG') else None,
                    remote_response_minutes=reaction if shock.startswith('AOG') else None,
                    cancelled_legs=len(cancelled),lost_booked_OD_journeys=lost_j,
                    lost_project_gross_revenue=sum(s['gross_revenue'] for s in lost),
                    compensation_RUB_scenario=compensation,
                    contribution_no_rebooking_no_flight_cost_recovery=base['contribution_before_base_fleet_opportunity']-margin-compensation,
                    end_positions=json.dumps(end_positions,sort_keys=True),
                    source='deterministic common-shock experiment; observed restriction days in longlist only',
                    as_of=AS_OF,period='one disruption in model week',geography=';'.join(sorted(x for x in closed if x)) if not shock.startswith('AOG') else failedbase,
                    unit='legs, endpoint journeys, RUB/week',
                    limitation='NO probability inferred. No rebooking; no flight cost recovery; old migrating customer returns to baseline. Remote spare cannot save first cycle; ferry not scheduled. Crew/standby response unverified.'))
    csvout('correlated_disruption_scenarios.csv',rows)
    csvout('observed_restriction_days.csv',[dict(iata=r['iata'],h1_2026_days=r['h1_2026_days'],jan_oct_2026_days=r['jan_oct_2026_days'],trailing365_days=r['last365_days'],
        source='data/processed/longlist.csv + data/processed/kover_days.csv; Rosaviatsiya posts, observed LOWER count',
        as_of=AS_OF,period='H1 2026 / Jan-Oct2026 / trailing365days to snapshot2026-11-09',unit='calendar days with restriction announcement',
        geography=r['iata'],probability=None,duration_hours=None,
        limitation='day counts are not delay duration, flight cancellation probability or independent airport draws') for r in model.longlist])
    return rows


def horizon(model,summary):
    rows=[]
    for n in model.networks:
        for year in [2027,2028]:
            for trend in [.9,1.,1.1]:
                r=model.evaluate(model.networks[n],'base',demand_scale=trend**(year-2026))[0]
                for denominator in [80000000,100000000,120000000]:
                    rows.append(dict(network=n,year=year,annual_OD_multiplier_scenario=trend,
                        network_policy='hold same network; no additional aircraft or route opening assumed',
                        weekly_project_segments=r['segment_pax'],weekly_incremental_segments=r['incremental_segment_pax'],
                        annual_equivalent_incremental_segments=r['incremental_segment_pax']*52,
                        national_domestic_flown_segments_denominator_SCENARIO=denominator,
                        incremental_share_percentage_points_scenario=r['incremental_segment_pax']*52/denominator*100,
                        RW_baseline_segments=None,RW_total_market_share=None,
                        source='analyst 52 identical weeks run-rate and denominator scenarios; NOT observed national forecast',
                        as_of=AS_OF,period=f'{year} conditional annual equivalent',geography='Russian domestic flown segments',
                        unit='flown passenger segments; percentage points',
                        limitation='seasonality, own baseline, actual denominator, fleet growth, legal/slot/TO readiness UNKNOWN; OD journeys not divided by segment denominator'))
    csvout('2027_2028_hold_network_scenarios.csv',rows)


def validate(model,summary,audits,resources,sens,maxima,original_hashes):
    tests={}
    tests['legacy_original_B0_72_legs']=len(model.networks['B0']['legs'])==72
    b=model.evaluate(model.networks['B0'],'base')[0]
    old=next(r for r in csvin(LEGACY/'network_comparison.csv') if r['network']=='B0' and r['scenario']=='base')
    tests['B0_original_hours_preserved']=abs(b['weekly_block_hours']-float(old['weekly_block_hours']))<1e-8
    for n,net in model.networks.items():
        for sc in ['base','cautious']:
            a,ss,cc=model.evaluate(net,sc,detail=True)
            aa=model.evaluate(net,sc,detail=True)
            assert (a,ss,cc)==aa
            model.evaluate(net,sc,demand_scale=1000,detail=True)
            model.evaluate(net,sc,transfer_scale=1000,priority='transfer_first',detail=True)
    tests['deterministic_repeated_evaluation']=True
    tests['dated_capacity_fare_migration_and_OD_conservation_with_saturation']=True
    tests['bidirectional_transfer_products_in_week']=all((b,a) in net['itineraries'] and net['itineraries'][(b,a)][0]['transfer'] for net in model.networks.values() for (a,b),its in net['itineraries'].items() if its[0]['transfer'])
    tests['same_pair_same_market_object_all_alternatives']=all(model.market(a,b) is model.markets[pair(a,b)] for net in model.networks.values() for a,b in net['itineraries'])
    tests['no_forced_flight_hour_equalization']=len({round(r['weekly_block_hours'],6) for r in summary})>2
    tests['cap_changes_checks_or_allocation']=any(r['test']=='block_cap_8' and (r['feasible']!=next(x for x in resources if x['test']=='block_cap_12' and x['network']==r['network'])['feasible'] or r['active_peak']!=next(x for x in resources if x['test']=='block_cap_12' and x['network']==r['network'])['active_peak']) for r in resources)
    tests['turn_changes_hours_or_span']=any(r['test']=='turn90' and (r['active_peak']!=audits[r['network']]['active_peak'] or r['max_daily_span_hours']!=audits[r['network']]['max_daily_span_hours'] or r['feasible']!=audits[r['network']]['feasible']) for r in resources)
    tests['spare_is_not_active_capacity']=all(r['active_aircraft_limit']==model.cfg['active_aircraft'] and r['fleet_total_condition']==model.cfg['active_aircraft']+2 for r in resources if r['test']=='spare2')
    tests['spare_changes_fleet_and_coverage']=any(r['test']=='spare2' and r['uncovered_bases_if_simultaneous_AOG']<next(x for x in resources if x['test']=='spare0' and x['network']==r['network'])['uncovered_bases_if_simultaneous_AOG'] for r in resources)
    keys=[(r['scenario'],r['priority'],r['parameter'],r['value'],r['network']) for r in sens]
    tests['sensitivity_unique_coordinates']=len(keys)==len(set(keys))
    for row in maxima:
        rr=[r for r in sens if r['scenario']==row['scenario'] and r['priority']==row['priority'] and r['network']==row['network'] and r['parameter']=='transfer_scale']
        assert max(r['transfer_journeys'] for r in rr)==row['max_transfer_journeys_on_tested_grid']
    tests['grid_max_really_max']=True
    tests['all_base_case_hubs_have_eight_rays']=all(len({pair(l['origin'],l['destination']) for l in net['legs']})==8 for net in model.networks.values() if net['kind']=='hub')
    # Structural counterexample using real dated legs, capacities and one-ticket accounting.
    net=model.networks['H_GOJ_compact']
    zero_local={pair(a,b):(0 if 'GOJ' in (a,b) else 100) for a,b in net['itineraries']}
    counter=model.evaluate(net,'base',market_scales=zero_local,fare_scale=5)[0]
    tests['standalone_local_threshold_not_necessary_for_hub']=(counter['local_journeys']==0 and counter['transfer_journeys']>0 and counter['contribution_before_base_fleet_opportunity']>0)
    dump('standalone_rule_counterexample.json',dict(result=counter,local_OD_multiplier=0,transfer_OD_multiplier=100,fare_multiplier=5,
        interpretation='artificial structural counterexample ONLY, not a plausible forecast or launch case: hub can cover rays with zero local demand'))
    z=model.evaluate(model.networks['B0'],'base',demand_scale=0)[0]
    tests['zero_OD_zero_revenue_and_full_flight_cost']=z['gross_revenue']==0 and z['sold_journeys']==0 and abs(z['contribution_before_base_fleet_opportunity']+z['flight_variable_cost'])<1e-6
    tests['legacy_and_existing_Excel_unchanged']=all(digest(p)==h for p,h in original_hashes.items())
    assert all(tests.values()),tests
    # READS includes every frozen file used, plus explicit code, instructions and override configuration.
    READS.add(Path(__file__).resolve())
    manifest={str(p.relative_to(ROOT)):digest(p) for p in sorted(READS) if p.is_relative_to(ROOT) and
              (not p.is_relative_to(OUT) or p==OUT/'overrides.json')}
    dump('input_manifest.json',dict(as_of=AS_OF,sha256=manifest,
        note='All computational/provenance files read by this driver; includes old ranking.csv and both scripts. Legacy replay has copied input hashes too. Source URLs do not certify HTML replay.'))
    result=dict(status='PASS',tests=tests,as_of=AS_OF,input_sha256=manifest,
        limitations=['No empirical OD/net-fare calibration','Allocation heuristics and finite layout enumeration only',
          'Base/fleet/opportunity actual costs UNKNOWN','No slots/crew/TO/dispatch signoff',
          'Historical web parser not replayed','Unknown connecting RW migration uncapped by unavailable historical connecting capacity; separately labelled',
          'Correlated disruptions deterministic scenarios, no probabilities','2028 and denominator are transparent scenarios only'])
    dump('validation.json',result)
    return result


def report(model,replay,tops,summary,audits,base,reinforce,validation):
    lines=['# Расчёты командного обновления',
        f'Срез {AS_OF}. Из корня: `python3 scripts/build_team_comparison.py` — stdlib, offline. '
        'Входы подтверждений: `model/overrides.json`; структура и поля в `model/override_schema.json`. '
        'Чужие файлы и `outputs/longlist.xlsx` сохранены без изменения.',
        f'Старая экономика сначала воспроизведена неизменённым скриптом в `model/legacy_replay/`: {replay["status"]}, '
        f'максимум численного расхождения {replay["max_absolute_numeric_difference"]:.3g}. '
        'Это повтор frozen JSON, не historical HTML parser. Б0 остаётся отдельной исходной альтернативой: 12 пар × 3 вылета/направление, 72 плеча / 195,75 блок-ч.',
        'Все новые деньги — ₽/сценарную неделю 7–13 декабря 2026; OD — конечные поездки/неделю/направление, география — внутренние рынки России. '
        'Это условный operating contribution до новой базы, fixed fleet и opportunity cost; не прибыль/прогноз.',
        '## Города',
        '| Сценарий | Top3 условной середины |','|---|---|']
    for case,top in tops.items():lines.append('| '+case+' | '+' > '.join(top)+' |')
    lines += ['20 городов пересчитаны. Старый GOJ/UFA/GSV получен другой формулой на 10 городах. '
        'Неизвестные дают интервалы полезности, не нули; midpoint не оценка факта. Техданные уравнены/исключены отдельно в `old_score_technical_bias.csv`. '
        'Заявленные базы MRV/AER/MCX и индексированное сообщение Utair по TJM добавлены к старым; KZN — отдельный стресс лида, маршрутные доли UNKNOWN. '
        '`information_neutral` убирает признаки, где полнота сбора сама даёт преимущество. `gap_pop`/airport pax не спрос; '
        'случайная частота top3 не вероятность выбора; 500 км только чувствительность. Штатный `--min-dist500` воспроизведён отдельно с его перенормировкой.',
        '## Сети',
        'Пять условных хабов имеют по 8 лучей: dense 6 оборотов/луч, compact 3 с чередованием групп и полезными обратными стыковками на других датах. '
        'Б_sparse сохраняет треугольники Б0 в 4 дня, 2 вылета/направление. '
        'В `network_pairs`, `project_flights`, `itinerary_calendar`, `flight_capacity` — состав, UTC-даты/времена, непрерывные замкнутые цепочки и кресла каждого рейса.',
        'Общий верхний ресурс — условие 4 рабочих × 100 кресел + 1 резерв, 6 дней, 10 blockh/day, span16h, turn45; '
        'не факт наличия. Реальные настройки — `configuration.json`. Слоты/crew/ТО/местные окна/type-payload dispatch UNKNOWN. '
        'Перебраны разбиения волн и дневные перестановки оборотов; ограниченный перебор, не глобальный optimum. Превышение ресурса = infeasible.',
        '| Сеть | Ресурс | Плечи / блок-ч | Свободно ч | База Δ млн ₽ | Осторожный Δ млн ₽ |',
        '|---|---|---|---|---|---|']
    for n in model.networks:
        b=next(r for r in summary if r['network']==n and r['scenario']=='base' and r['priority']=='local_first')
        c=next(r for r in summary if r['network']==n and r['scenario']=='cautious' and r['priority']=='local_first')
        a=audits[n]
        lines.append(f'| {n} | {"условно feasible" if a["feasible"] else "INFEASIBLE"} | {b["weekly_legs"]} / {b["weekly_block_hours"]:.1f} | {a["unused_block_budget_hours"]:.1f} | {b["contribution_before_base_fleet_opportunity"]/1e6:.2f} | {c["contribution_before_base_fleet_opportunity"]/1e6:.2f} |')
    lines += ['Часы не уравнены насильно; усиления Б проходят только при положительном маржинальном вкладе и выполнимости: '
        f'принято {sum(r["accepted_marginal"] for r in reinforce)} из {len(reinforce)} проверок. '
        'NO_LAUNCH = 0 до новых затрат. Два порядка бронирований local_first/transfer_first сохранены раздельно; '
        'максимум всей сохранённой сетки и endpoint saturation различаются в `grid_maxima.csv`.',
        '## OD и учёт',
        '`od_registry`: одна каноническая OD во всех альтернативах. Точные старые OD сохраняют прежние сценарии; новые пары получают общие '
        'distance-band диапазоны, без переименования GOJ. Эмпирические OD/fare/границы NULL; 0..2×base — стресс, не confidence interval. '
        'Каждая новая пара имеет метод/источник/дату/единицу/географию/период. Новое block time — 30 мин + 1,10×great-circle/700 км/ч, округление5мин; не dispatch.',
        'Билет один раз: effective transfer fare = reference × 0,90/0,85, два датированных плеча. Gross, incremental, journey/segment и миграция разделены. '
        'Прямой миграционный компонент ограничен подтверждёнными прежними прямыми креслами RW; неизвестные прежние connecting продажи — отдельный долевой сценарий без подтверждённой ёмкости. '
        'Кредит снятия старых рейсов отсутствует; replacement требует lost revenue и avoidable cost, сейчас NULL. '
        'Standalone local threshold не необходим лучу хаба: явный структурный контрпример сохранён отдельно.',
        '## Главные переключатели и противоречия',
        '`standardized_OD_basis.csv` устраняет асимметрию старых допущений общими bands для всех пар: базовый лидер проекта переключается с GOJ_compact на UFA_compact. '
        'В осторожном frozen-сценарии лидер TJM_compact. Все базовые/осторожные варианты отрицательны; это не выбор базы. '
        'Эта смена — ограничение идентификации спроса, не новые доказанные продажи.',
        '`new_base_tie_thresholds` разделяет равенство с лучшей прямой сетью и выход в ноль. '
        '`sensitivity`, `switch_thresholds`, `project_leader_switch_brackets` меняют cost/fare/OD/base/transfer-market/transfer-capture/transfer-fare/migration. '
        'Общий OD меняется у всех альтернатив; каждый найденный знак-переход сохранён. Скачок greedy-порядка помечен отдельно от нулевого корня; '
        'между точками возможны дополнительные переключения. Fixed fleet5/6 и opportunity использованных часов — отдельные сценарии, фактические цены NULL. '
        'Свободные часы не выручка; UFA public basket не контракт всей сети.',
        'Один резерв у хаба условно в хабе, у Б в SVX: ZIA мгновенно не покрыта. Два резерва = 6 бортов, не 6 рабочих. '
        'Ковёр — наблюдённые нижние счётчики дней, не вероятность. Закрытие узла/общий шок/AOG — детерминированные сценарии с пространственным распространением отмен, '
        'без rebooking, экономии рейсов и утверждённого ferry recovery; компенсация5000₽/поездку условна. '
        '2027–2028 — неизменная сеть и прозрачные сценарии OD/сегментного знаменателя; полная доля RW NULL, OD не делится на сегменты.',
        'Для следующего пересчёта нужны: направленные OD×месяц/paid coverage/net fare/старые RW продажи; зимние календари/собственные кресла/назeмные альтернативы; '
        'block/type-payload/слоты/MCT/багаж/ticketing/ТО/crew/reserve; контракты fuel/handling/fixed base/fleet/opportunity. '
        'Факты в `overrides.markets`, `block_minutes`, `ranking`, `source_records`; единицы и provenance обязательны. '
        'Спорные трактовки собраны в `interpretation_limits.json`, ответы NE-01..15 — `audit_response.json`.',
        f'`validation.json`: {validation["status"]}. Проверены OD/кресла/сегменты/деньги/один тариф, насыщение, обратные стыковки, общий OD, реакция cap/turn/spare, '
        'детерминизм, настоящий max сетки и неизменность старого/Excel. SHA256 всех прочитанных входов, override и обоих скриптов — `input_manifest.json`, включая прежний ranking.csv.']
    content='';previous_table=False
    for line in lines:
        is_table=line.startswith('|')
        content+=('\n' if is_table and previous_table else '\n\n')+line
        previous_table=is_table
    (OUT.parent/'calculations.md').write_text(content.lstrip()+'\n')


def documentation(model):
    dump('override_schema.json',dict(
        config='Optional actual model configuration: planning_cap_block_h, turn_minutes, span_cap_h, spare_aircraft, active_aircraft, bank_wait_minutes, fleet_fixed_rub_aircraft_week, opportunity_rub_block_hour, new_base_fixed_rub_week. Null fixed costs stay unknown.',
        scenarios='base/cautious -> existing scenario coefficient names, e.g. capture_uncertain or transfer_fare_factor. These remain assumptions unless calibrated.',
        markets={'A-B canonical alphabetical IATA pair':dict(
            demand_base='endpoint journeys/week/direction',demand_cautious='same unit',fare_base='RUB net whole one-way journey',fare_cautious='same unit',
            empirical_OD_lower='NULL unless defensible empirical lower',empirical_OD_upper='NULL unless defensible empirical upper',
            observed_OD='NULL unless observed for the exact geography/period/direction',observed_net_fare='same rule',
            rw_direct_seats_A='confirmed incumbent direct seats/week in direction A to B; use actual IATA instead of A',
            evidence='source URL or source id + extraction/date + period + unit + geography + definition',
            source_urls='optional exact URLs',sources='ids in frozen source registry or source_records',range_basis='method supporting scenario bounds',
            capture_group='open/competitive/uncertain, not measured share',cannibal_base='scenario fraction, not observed traffic')},
        block_minutes={'ORIGIN-DESTINATION':'directional minutes; not canonical sorted pair; provide exact source/provenance in source_records'},
        ranking=dict(city_values='IATA -> field overrides with transfer_source/base_source/etc; original team replay remains frozen',
                     confirmed_competitor_bases='IATA list, presence of base is NOT share/dominance',possible_competitor_bases='IATA list tested only as lead stress'),
        source_records='list of {id,url,as_of,period,unit,geography,definition,status}; included in override hash',
        CSV_NULL='Empty CSV cell represents JSON null/UNKNOWN; no missing empirical input is imputed as observed zero'))
    mapping={
      'NE-01':('FIXED','pair_economics + itinerary_sales effective_fare and transfer factor'),
      'NE-02':('FIXED','grid_maxima max over saved grid, separate endpoint'),
      'NE-03':('FIXED','standalone_direct_thresholds interpretation and dated-capacity structural counterexample'),
      'NE-04':('FIXED','input_manifest includes ranking.csv and all consumed files'),
      'NE-05':('FIXED_WITH_LIMIT','config-driven cap/turn/span/spare; explicit reserve geography/cost; recovery not approved'),
      'NE-06':('UNRESOLVED_EMPIRICAL','OD/net fare/capture remain scenarios; common-bands sensitivity'),
      'NE-07':('CONDITIONAL_MODEL','common upper fleet, closed chains, unused resource; available fleet/crew/TO UNKNOWN'),
      'NE-08':('UNRESOLVED_PRODUCT','bidirectional timed transfers only; protected ticket/MCT/baggage UNKNOWN'),
      'NE-09':('UNRESOLVED_EVIDENCE','no broad new research; calendar and matched fares still gaps'),
      'NE-10':('BOUNDARY_ONLY','no withdrawal savings; lost old sales/avoidable flight costs NULL'),
      'NE-11':('CONDITIONAL_COST','public UFA basket extrapolation explicit; fixed/opportunity/base separate'),
      'NE-12':('PARTIAL_SCENARIOS','correlated cancellation/AOG experiments; no probability or complete recovery model'),
      'NE-13':('CONDITIONAL_MODEL','five independently constructed hub geometries and canonical OD registry, no GOJ relabel'),
      'NE-14':('FROZEN_REPLAY_ONLY','historic raw HTML extraction not repeated'),
      'NE-15':('SCOPE_EXPLICIT','CSV scenario results only; no interactive optimisation or investment claim')}
    dump('audit_response.json',[dict(id=i,status=x[0],response=x[1],as_of=AS_OF) for i,x in mapping.items()])
    dump('interpretation_limits.json',dict(as_of=AS_OF,items=[
      dict(issue='City-screen leader vs economics leader',detail='CEK leads team scoring; cannot infer route OD or ready base. Different screening weights/unknowns change top3.'),
      dict(issue='Asymmetry of assumed OD evidence',detail='Frozen exact-OD plus new bands gives GOJ compact baseline lead; applying common bands to every pair gives UFA compact. Neither is measured demand.'),
      dict(issue='Cautious vs base leader',detail='TJM compact leads cautious assumed contribution while every project remains below no-launch before fixed costs.'),
      dict(issue='Basing vs fortress',detail='Presence statement is not dominance, airport share or OD share. TJM indexed home-carrier statement is accepted presence evidence; KZN remains a separate stress. No route-share inference.'),
      dict(issue='Legacy A vs new GOJ dense',detail='Same physical rays/hours can have different bank partition and additional explicitly assumed OD products. Legacy A reproduction remains separate.'),
      dict(issue='SSJ green screening vs actual feasibility',detail='Range screening is not type/variant/payload/wind/route dispatch. Algebraic chain feasibility does not verify crew/TO/slots.'),
      dict(issue='Day counts vs disruption',detail='Restriction announcements give observed lower counts, not event duration/probability. Correlated shocks are deterministic scenarios.'),
      dict(issue='Switch boundary vs breakeven',detail='Best-project changes, tie with best direct, and zero crossings are different outputs. Greedy sorting can make discontinuities.'),
      dict(issue='Unknown connecting baseline',detail='Confirmed direct migration is seat capped; unverified connecting migration is a separate fractional scenario. Capacity and realised sales remain UNKNOWN.')]))


def standardized_basis(model, feasible):
    """Separate neutral-input experiment; restore the exact baseline afterwards."""
    original=copy.deepcopy(model.markets)
    rows=[]
    for basis in ['frozen_exact_OD_plus_new_bands','common_bands_all_OD']:
        if basis=='common_bands_all_OD':
            for key,m in model.markets.items():
                a,b=key.split('-')
                # Same mapping for every endpoint pair, irrespective of candidate hub.
                m.update(model.band_values(a,b))
        for sc in ['base','cautious']:
            for priority in ['local_first','transfer_first']:
                results=[]
                for name in feasible:
                    r=model.evaluate(model.networks[name],sc,priority)[0]
                    r['OD_basis']=basis;results.append(r)
                best=max(results,key=lambda r:r['contribution_before_base_fleet_opportunity'])['network']
                for r in results:r['best_enumerated_project_this_basis']=best
                rows+=results
    model.markets=original
    csvout('standardized_OD_basis.csv',rows)


def export_pair_economics(model,summary,sales,capacity):
    rows=[];thresholds=[]
    for r in summary:
        name,sc,priority=r['network'],r['scenario'],r['priority']
        net=model.networks[name]
        selected=[s for s in sales if s['network']==name and s['scenario']==sc and s['priority']==priority]
        for key in sorted({pair(s['origin'],s['destination']) for s in selected}):
            ss=[s for s in selected if pair(s['origin'],s['destination'])==key]
            m=model.markets[key]
            rows.append(dict(network=name,scenario=sc,priority=priority,pair=key,
                product='transfer' if ss[0]['transfer'] else 'nonstop',
                reference_market_fare=m['fare_'+sc],effective_fare=ss[0]['effective_fare'],
                transfer_fare_factor=ss[0]['transfer_fare_factor'],
                D_week_direction=m['demand_'+sc],sold_OD=sum(s['sold_journeys'] for s in ss),
                flown_segments=sum(s['segment_pax'] for s in ss),
                gross_revenue=sum(s['gross_revenue'] for s in ss),
                incremental_revenue=sum(s['incremental_revenue'] for s in ss),
                passenger_margin=sum(s['incremental_revenue']-s['new_pax_variable']+s['saved_old_pax_variable'] for s in ss),
                note='Fare is per whole OD journey, not allocated twice to hub rays'))
        if priority!='local_first':continue
        for key in sorted({pair(l['origin'],l['destination']) for l in net['legs']}):
            m=model.markets[key];p=model.scenarios[sc]
            legs=[l for l in net['legs'] if pair(l['origin'],l['destination'])==key]
            cost=sum(model.flight_cost(l,sc) for l in legs)
            unit=m['fare_'+sc]-p['pax_cost'];f=len(legs)/2
            q=p['capture_'+m['capture_group']]*(1-math.exp(-f/p['frequency_scale']))
            required=cost/(2*unit*q) if unit>0 and q>0 else None
            thresholds.append(dict(network=name,scenario=sc,pair=key,
                standalone_direct_required_OD_week_direction=required,
                standalone_direct_required_pax_departure=cost/len(legs)/unit if unit>0 else None,
                source='scenario standalone direct fare/cost; no migration or connecting revenue',
                unit='endpoint journeys/week/direction; passengers/departure',
                interpretation='NOT a necessary local-demand threshold for hub ray; evaluate whole network transfer margin once'))
    csvout('pair_economics.csv',rows);csvout('standalone_direct_thresholds.csv',thresholds)
    csvout('physical_constraints.csv',[dict(iata=i,runway_m=next((r['runway_m'] for r in model.longlist if r['iata']==i),None),
        aircraft_variant_dispatch=None,slots=None,crew=None,maintenance_capacity_contract=None,
        protected_transfer_MCT_RW=None,source='longlist runway only; exact airports in project_flights; existing evidence does not verify spare capacity or RW contract',
        as_of=AS_OF,period='proposed December2026 schedule',geography=i,unit='runway metres; remaining fields UNKNOWN',
        status='CONDITIONAL_OPERATION_NOT_READY_BASE') for i in sorted({l[k] for n in model.networks.values() for l in n['legs'] for k in ['origin','destination']})])


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    protected=list(LEGACY.rglob('*'))+[ROOT/'outputs/longlist.xlsx']
    protected={p:digest(p) for p in protected if p.is_file()}
    override=OUT/'overrides.json'
    if not override.exists():
        dump('overrides.json',dict(config={},scenarios={},markets={},block_minutes={},
            ranking={},source_records=[],evidence_note='Add verified inputs with source/date/unit/geography/period in market evidence/sources. No logic rewrite required. All values otherwise are frozen assumptions.'))
    read(ROOT/'context/14_synthesis/contributions/network_economics/findings.json')
    replay=replay_old()
    tops=ranking()
    model=Model();model.make_networks();reinforce=reinforcements(model)
    export_registry(model)
    audits={};auditrows=[];alllegs=[];pairs=[];products=[]
    for n,net in model.networks.items():
        a,rr=model.audit(net);audits[n]=a;auditrows+=rr;alllegs+=net['legs']
        for key in sorted({pair(l['origin'],l['destination']) for l in net['legs']}):
            x,y=key.split('-');m=model.markets[key]
            rr=[l for l in net['legs'] if pair(l['origin'],l['destination'])==key]
            d=model.distance(x,y);green=2150 if set((x,y))&{'AER','MRV','VOG'} else 2300
            pairs.append(dict(network=n,pair=key,departures_A_to_B=sum(l['origin']==x for l in rr),
                departures_B_to_A=sum(l['origin']==y for l in rr),straight_line_km=d,
                screening_green_threshold_km=green,within_reference_green=d<=green,
                block_A_to_B=model.block(x,y),block_B_to_A=model.block(y,x),
                source=m['range_basis'],as_of=AS_OF,period='2026-12-07/13',geography=key,unit='departures/week/direction; km; minutes',
                physical_limit='range is only screening, not actual SSJ variant dispatch; slots/payload/winds/airport UNKNOWN'))
        for (x,y),its in sorted(net['itineraries'].items()):
            for it in its:products.append(dict(network=n,origin=x,destination=y,**it,
                physical_product_status='geometric time-valid, protected ticket/MCT/through baggage UNVERIFIED' if it['transfer'] else 'conditional nonstop',
                canonical_OD=pair(x,y),**META))
    csvout('project_flights.csv',alllegs);csvout('network_pairs.csv',pairs)
    csvout('itinerary_calendar.csv',products);csvout('operational_audit.csv',auditrows)
    csvout('resource_summary.csv',audits.values());csvout('bank_assignment.csv',model.bank_details)
    summary=[];sales=[];capacity=[]
    for net in model.networks.values():
        for sc in ['base','cautious']:
            for priority in ['local_first','transfer_first']:
                r,s,c=model.evaluate(net,sc,priority,detail=True);r['resource_feasible']=audits[net['name']]['feasible'];summary.append(r);sales+=s;capacity+=c
    csvout('network_comparison.csv',summary);csvout('itinerary_sales.csv',sales);csvout('flight_capacity.csv',capacity)
    feasible=[n for n,a in audits.items() if a['feasible']]
    resources=resource_sensitivity(model)
    sens,thresholds,maxima=sensitivity(model,feasible)
    export_pair_economics(model,summary,sales,capacity)
    standardized_basis(model,feasible)
    base=fixed_costs(model,summary,audits)
    disruption_scenarios(model,summary,sales)
    horizon(model,summary)
    winners=[]
    for sc in ['base','cautious']:
        for priority in ['local_first','transfer_first']:
            rr=[r for r in summary if r['scenario']==sc and r['priority']==priority and r['network'] in feasible]
            best=max(rr,key=lambda r:r['contribution_before_base_fleet_opportunity'])
            winners.append(dict(scenario=sc,priority=priority,best_enumerated_project=best['network'],
                contribution=best['contribution_before_base_fleet_opportunity'],
                best_including_no_launch=best['network'] if best['contribution_before_base_fleet_opportunity']>0 else 'NO_LAUNCH',
                scope='fixed tested route sets and frequencies only; before base/fleet/opportunity'))
    dump('best_enumerated.json',winners)
    dump('configuration.json',dict(config=model.cfg,scenarios=model.scenarios,metadata=META,
        accounting='additive; existing flights remain; no cancelled-flight savings credited',
        date_basis='UTC absolute minute from 2026-12-07T00:00Z; local airport windows UNKNOWN',
        demand_unit='endpoint journeys/week/direction',money_unit='RUB/model week; net fare RUB/journey'))
    documentation(model)
    validation=validate(model,summary,audits,resources,sens,maxima,protected)
    report(model,replay,tops,summary,audits,base,reinforce,validation)
    print(json.dumps(dict(status='PASS',city_top3=tops,resource_feasible=feasible,best=winners,
        output='context/15_team_update/model',calculation='context/15_team_update/calculations.md'),ensure_ascii=False))


if __name__=='__main__':main()
