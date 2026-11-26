#!/usr/bin/env python3
"""Offline evidence join. Writes only beside this file. No credentials or API calls."""
import sys
sys.dont_write_bytecode = True
import calendar, csv, hashlib, json, math, re, statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P09 = ROOT.parent/'35_full_programme_execution_20261112/P09'
SEASONS = ('winter', 'shoulder', 'summer')
def season(month): return 'winter' if int(month) in (12,1,2) else 'summer' if int(month) in (6,7,8) else 'shoulder'
def readcsv(path): return list(csv.DictReader(Path(path).open(encoding='utf-8')))
def dump(name, obj):
    path=ROOT/name; path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def writecsv(name, rows):
    rows=list(rows)
    if not rows:return
    path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
def quantile(xs,q=.5):
    xs=sorted(xs)
    if not xs:return None
    i=(len(xs)-1)*q;lo=int(i);hi=min(len(xs)-1,lo+1)
    return xs[lo]*(hi-i)+xs[hi]*(i-lo) if hi!=lo else xs[lo]
def clip(x,lo,hi):return max(lo,min(hi,x))
def operator(c,number=''):
    n=re.sub(r'\D','',str(number))
    return 'FV' if c=='SU' and n and 6001<=int(n)<=6999 else c

def build():
    manifest=readcsv(ROOT/'routes_manifest_209.csv');by={r['pair']:r for r in manifest}
    subs={r['pair']:r for r in readcsv(ROOT/'swarm/subsidies_2026.csv')}
    econ=json.loads((ROOT/'swarm/competitor_economics_and_baggage.json').read_text())
    strategic=json.loads((ROOT/'swarm/strategic_competitor_risks.json').read_text())
    carrier={}
    for c in econ['competitors']:
        for code in c['iata'].split(' / '):carrier[code]=c
    # Explicit analogues for carriers missing from the economics research.
    aliases={'5N':'DP','HZ':'FV','R3':'IO','YC':'FV','I8':'UT','D2':'RT','KV':'RT','WZ':'FV'}
    def ce(c):return carrier.get(c,carrier[aliases.get(c,'FV')])
    def seats(c,v=''):
        v=(v or '').lower()
        for token,n in [('170',78),('190',110),('crj',50),('atr 72',70),('atr-72',70),('atr 42',46),('ssj',100),('superjet',100),('sukhoi',100),('su 95',100),('rrj',100),('737-500',126),('321',220)]:
            if token in v:return n
        if '737-800' in v:return 189 if c in ('DP','N4','5N') else 160 if c in ('SU','FV') else 176
        return ce(c)['fleet_and_capacity']['primary_seats'] if c not in ('EO',) else 110
    # The raw schedule has no destination IATA. Resolve only unambiguous regional names.
    titles=defaultdict(set)
    for r in manifest:
        titles[r['city_a'].lower()].add(r['a']);titles[r['city_b'].lower()].add(r['b'])
    for r in readcsv(P09/'subject/P05/inputs/BASE/data/processed/catchments.csv'):
        titles[r['main_city'].lower()].add(r['iata'])
    for code,name in [('MRV','Минеральные Воды'),('KUF','Самара'),('AER','Сочи')]:titles[name.lower()]={code}
    schedules=json.loads((ROOT/'yandex_hub_schedules.json').read_text())
    for key,v in schedules.items():titles[v.get('station',{}).get('title','').lower()].add(key.split(':')[0])
    observations={};unresolved=Counter();sample_dates=defaultdict(set)
    for key,v in schedules.items():
        a,day=key.split(':');sample_dates[a].add(day)
        for x in v.get('schedule',[]):
            t=x['thread'];dest=t.get('title','').split(' — ')[-1].strip().lower()
            choices=titles.get(dest,set())
            if len(choices)!=1:unresolved[dest]+=1;continue
            b=next(iter(choices));pair='-'.join(sorted((a,b)))
            if pair not in by or x.get('stops'):continue
            c=operator(t['carrier']['codes'].get('iata') or '',t['number'])
            if not c:continue
            ident=(a,b,x['departure'],re.sub(r'\D','',t['number']))
            observations[ident]=dict(pair=pair,a=a,b=b,date=day,carrier=c,vehicle=t.get('vehicle',''),seats=seats(c,t.get('vehicle','')),source='yandex_departures',flight_number=t['number'])
    spotlight=json.loads((ROOT/'yandex_spotlight_search.json').read_text())
    conn_times=defaultdict(list)
    for key,v in spotlight.items():
        pair,day=key.split(':');a,b=pair.split('-')
        for x in v.get('segments',[]):
            if x.get('has_transfers'):
                duration=(datetime.fromisoformat(x['arrival'])-datetime.fromisoformat(x['departure'])).total_seconds()/60
                if duration>0:conn_times[pair].append(duration)
                continue
            t=x.get('thread',{});c=operator(t.get('carrier',{}).get('codes',{}).get('iata') or '',t.get('number',''))
            if not c:continue
            sample_dates[a].add(day)
            ident=(a,b,x['departure'],re.sub(r'\D','',t.get('number','')))
            observations.setdefault(ident,dict(pair=pair,a=a,b=b,date=day,carrier=c,vehicle=t.get('vehicle',''),seats=seats(c,t.get('vehicle','')),source='yandex_spotlight',flight_number=t.get('number','')))
    # Subs are legal route awards, not observed movements; airport-wide Moscow eligibility
    # is NOT evidence of SU flights from DME or of identical supply at all Moscow airports.
    sub_codes={};sub_freq={};sub_cap={}
    for pair,s in subs.items():
        codes=re.findall(r'\b[A-Z0-9]{2}\b(?=\s*\()',s['carrier_codes_or_names'])
        sub_codes[pair]=sorted(set(codes))
        freqs=[float(z) for z in re.findall(r'(\d+(?:\.\d+)?) рейс/нед',s['subsidy_period_or_freq'])]
        sub_freq[pair]=max(freqs,default=0)
        cap=re.search(r'спецтариф.*?:\s*([\d ]+) руб',s['max_tariff_or_notes'])
        sub_cap[pair]=float(cap[1].replace(' ','')) if cap else None
    def baggage(c,pair,stops):
        dist=float(by[pair]['distance_km']);east={'SVX','CEK','TJM','OMS','OVB','KJA','IKT','VVO','KHV','UUD','PKC','UUS','YKS','GDX','ABA','BAX','HTA'}
        endpoints=set(pair.split('-'));cross=bool(endpoints&east) and bool(endpoints-east)
        subsidy=c in sub_codes[pair] and subs[pair]['subsidized_2026']=='true'
        n=stops+1
        if c=='A4':
            cap=sub_cap[pair]
            central=500 if subsidy and cap and cap<3000 else 1000 if subsidy and cap and cap<=6000 else 4199
            return central*n,central*n,central*n,'published_zone_rule_assumed_bare_fare'
        if c in ('SU','FV'):
            central=5040 if stops else 4720 if cross else 4400
            return central,3200 if not stops and not cross else central,central,'online_addon;3200_is_bundle_spread_not_fixed_addon'
        if c in ('DP','5N'):return (3100 if cross else 3000)*n,2999*n,3699*n,'minimum_online_dynamic_per_segment'
        if c=='S7':return (3000 if dist<1500 else 4000),2500,4200,'through_ticket_assumption_dynamic'
        if c=='U6':return 3500*n,3500*n,4500*n,'per_segment_published_minimum'
        if c=='UT':return 3000*n,2999*n,3800*n,'per_segment_conservative_assumption'
        if c=='N4':return (3500 if cross else 2800)*n,2329*n,4000*n,'dynamic_zone_assumption'
        if c=='EO':return 3000*n,2500*n,3500*n,'dynamic_regional_assumption'
        if c=='RT':return 2500*n,2500*n,2500*n,'20kg_upgrade_assumption'
        if c=='IO':return (2000 if dist<1000 else 3400)*n,2000*n,3400*n,'distance_rule_assumption'
        if c=='WZ':return 2700*n,0,3500*n,'historical_only_fare_brand_unknown'
        return 3000*n,0,4500*n,'UNKNOWN_carrier_analogue'
    quotes=[];seen=set();rejected=Counter()
    for i,r in enumerate(readcsv(ROOT/'travelpayouts_prices_209.csv')):
        pair=r['pair'];p=float(r['price_rub']);stops=int(r['transfers']);c=operator(r['airline'],r['flight_number'])
        key=(pair,r['origin'],r['destination'],c,r['flight_number'],r['departure_at'],p,stops)
        if key in seen:rejected['duplicate_quote']+=1;continue
        seen.add(key)
        if p<500 or p>150000:rejected['absolute_price_outlier']+=1;continue
        # Preserve airport identity; city-search spillovers are not exact-pair evidence.
        if set((r['origin_airport'],r['destination_airport']))!=set(pair.split('-')):
            rejected['airport_mismatch']+=1;continue
        addon,lo,hi,quality=baggage(c,pair,stops)
        quotes.append(dict(pair=pair,carrier=c,stops=stops,season=season(r['departure_at'][5:7]),gross=p+addon,bare=p,baggage=addon,baggage_low=lo,baggage_high=hi,baggage_quality=quality,departure=r['departure_at'],source_row=i+2,query_month=r['query_month']))
    grouped=defaultdict(list)
    for q in quotes:grouped[(q['pair'],q['carrier'],q['stops']==0,q['season'])].append(q)
    cleaned=[]
    for key,qs in grouped.items():
        med=quantile([q['gross'] for q in qs]);valid=[q for q in qs if med/4<=q['gross']<=med*4]
        rejected['within_group_outlier']+=len(qs)-len(valid);cleaned+=valid
    quotes=cleaned
    # Seasonal ratios are matched within route x carrier x product. Distance-band
    # shrinkage avoids confusing summer carrier mix with an actual price change.
    g=defaultdict(list)
    for q in quotes:
        if q['carrier']!='WZ':g[(q['pair'],q['carrier'],q['stops']==0,q['season'])].append(q['gross'])
    ratios=defaultdict(list)
    for pair,c,direct,s in list(g):
        if s=='winter':continue
        w=g.get((pair,c,direct,'winter'))
        if not w:continue
        ratio=clip(quantile(g[(pair,c,direct,s)])/quantile(w),.5,2.0)
        band=int(float(by[pair]['distance_km'])//750)
        ratios[(direct,band,s)].append(ratio);ratios[(direct,'all',s)].append(ratio)
    season_audit=[];route_profile={}
    for pair,row in by.items():
        band=int(float(row['distance_km'])//750)
        for direct in (True,False):
            profile={'winter':1.0}
            for s in ('shoulder','summer'):
                matched=[]
                for c in sorted({q['carrier'] for q in quotes if q['pair']==pair and (q['stops']==0)==direct and q['carrier']!='WZ'}):
                    if (pair,c,direct,s) in g and (pair,c,direct,'winter') in g:
                        matched.append(clip(quantile(g[(pair,c,direct,s)])/quantile(g[(pair,c,direct,'winter')]),.5,2))
                pool=ratios.get((direct,band,s),ratios.get((direct,'all',s),[1.0]))
                pooled=quantile(pool);weight=len(matched)/(len(matched)+2)
                profile[s]=clip(weight*(quantile(matched) or pooled)+(1-weight)*pooled,.6,1.8)
                season_audit.append(dict(pair=pair,direct=direct,season=s,index=profile[s],matched_carriers=len(matched),pool_count=len(pool),distance_band=band,basis='matched_carrier_median_ratio_shrunk_n_over_n_plus2;not_causal_seasonality'))
            # Calendar-day average 2027 = 1; comparable to P05's annual flat reference.
            norm=(90*profile['winter']+92*profile['summer']+183*profile['shoulder'])/365
            route_profile[(pair,direct)]={s:v/norm for s,v in profile.items()}
    obsby=defaultdict(list)
    for o in observations.values():obsby[(o['pair'],o['carrier'])].append(o)
    refs=econ['aircraft_unit_cost_reference']
    def floor(c,v,dist):
        ref=None;vl=(v or '').lower()
        for token,name in [('170','Embraer E170 (S7 78Y)'),('190','Embraer E190 (Ikar 110Y)'),('crj','Bombardier CRJ-200 (UVT/IrAero 50Y)'),('atr','ATR 72-500 (Utair 70Y)')]:
            if token in vl:ref=refs[name];break
        if ref is None and c=='EO':ref=refs['Embraer E190 (Ikar 110Y)']
        if ref is None and c=='FV' and '737' in vl:ref=refs['Boeing 737-800 (FSC 168-176 seats)']
        table=ref['benchmarks_direct'] if ref else ce(c)['cost_floor_model']['benchmarks_direct_rub_per_pax']
        xs=sorted(int(k.split('_')[0]) for k in table)
        def f(field):
            l,h=(xs[0],xs[1]) if dist<xs[0] else (xs[-2],xs[-1]) if dist>xs[-1] else next(((a,b) for a,b in zip(xs,xs[1:]) if a<=dist<=b),(xs[-2],xs[-1]))
            return max(0,table[f'{l}_km'][field]+(dist-l)/(h-l)*(table[f'{h}_km'][field]-table[f'{l}_km'][field]))
        return f('variable_floor_rub_per_pax'),f('full_floor_rub_per_pax')
    rows=[];carrier_rows=[]
    for pair,row in by.items():
        dist=float(row['distance_km']);ref=float(row['ref_gross_rub']);qs=[q for q in quotes if q['pair']==pair]
        ds={q['carrier'] for q in qs if q['stops']==0 and q['carrier']!='WZ'}
        ds|={c for p,c in obsby if p==pair and c!='WZ'}
        # Airport-level eligibility is unknown for Moscow-specific programme rows.
        if not set(pair.split('-'))&{'SVO','DME','VKO','ZIA'}:ds|=set(sub_codes[pair])-{'WZ'}
        direct_carriers=[]
        for c in sorted(ds):
            os=obsby.get((pair,c),[]);counts=Counter((o['a'],o['date']) for o in os if o['date'].startswith('2026-12'))
            # Mean over the two observed dates AND surveyed directions, with observed
            # zeros retained; one-sided sample is mirrored, not divided by two again.
            directions=[a for a in pair.split('-') if a in sample_dates and any(d.startswith('2026-12') for d in sample_dates[a])]
            if counts:
                denom=sum(len([d for d in sample_dates[a] if d.startswith('2026-12')]) for a in directions)
                daily=sum(counts.values())/max(1,denom);quality='two_winter_days_directional_average_not_weekly_schedule'
            elif c in sub_codes[pair] and sub_freq[pair]>0:daily=sub_freq[pair]/7;quality='2026_award_max_weekly_frequency_season_not_2027_schedule'
            else:daily=2/7;quality='ASSUMED_2_weekly_presence_only;range1_to7'
            if c in sub_codes[pair] and sub_freq[pair]>0:daily=max(daily,sub_freq[pair]/7)
            typical=Counter(o['vehicle'] for o in os).most_common(1)
            vehicle=typical[0][0] if typical else ce(c)['fleet_and_capacity']['primary_aircraft']
            seat=statistics.mean(o['seats'] for o in os) if os else seats(c,vehicle)
            cq=[q for q in qs if q['carrier']==c and q['stops']==0]
            bare=quantile([q['bare'] for q in cq]);anc=quantile([q['baggage'] for q in cq])
            prof=route_profile[(pair,True)]
            annual=quantile([q['gross']/prof[q['season']] for q in cq])
            pq=quantile([q['gross']/prof[q['season']] for q in cq],.25)
            if annual is None:annual=ref;pq=ref;price_quality='P05_DISTANCE_FALLBACK_NO_DIRECT_QUOTE'
            else:price_quality='cache_quote_plus_rule_assumed_bare_fare_NOT_checkout'
            var,full=floor(c,vehicle,dist)
            sub=c in sub_codes[pair] and subs[pair]['subsidized_2026']!='false'
            item=dict(carrier=c,vehicle=vehicle,seats_per_dep=seat,daily_departures=daily,weekly_departures=daily*7,daily_seats=daily*seat,frequency_quality=quality,
                quotes=len(cq),fare_annual_20kg=annual,fare_p25_annual_20kg=pq,bare_fare_median=bare,baggage_addon_median=anc,price_quality=price_quality,
                variable_floor_unsubsidized=var,full_floor_unsubsidized=full,variable_floor_subsidy20_stress=var*.8 if sub else var,full_floor_subsidy20_stress=full*.8 if sub else full,
                subsidy_2026_awarded_or_eligible=sub,subsidy_rub_per_pax=None,subsidy_floor_status='0_to30pct_scenario;20pct_stress_NOT_legal_payment' if sub else 'not_matched_2026',
                economic_analogue=c not in carrier,seasonal_fares={s:annual*prof[s] for s in SEASONS},source_flags=sorted(set(o['source'] for o in os)|({'travelpayouts_direct'} if cq else set())|({'subsidy_2026'} if sub else set())))
            direct_carriers.append(item);carrier_rows.append(dict(pair=pair,**item))
        direct_seats=sum(c['daily_seats'] for c in direct_carriers)
        directfare=quantile([c['fare_annual_20kg'] for c in direct_carriers],.5)
        directp25=quantile([c['fare_p25_annual_20kg'] for c in direct_carriers],.25)
        conn=[q for q in qs if q['stops']>0 and q['carrier']!='WZ'];cp=route_profile[(pair,False)]
        connfare=quantile([q['gross']/cp[q['season']] for q in conn])
        connquality='cache_quote_plus_rule;through_ticket_or_per_segment_assumption' if connfare else 'distance_analogue_UNOBSERVED'
        if connfare is None:connfare=ref*1.15
        ctime=quantile(conn_times[pair]) or (90+1.4*dist/750*60+120)
        ctime=max(45+dist/750*60+90,ctime)
        ends=set(pair.split('-'));lcc=any(c['carrier'] in ('DP','N4','5N') and c['seats_per_dep']>=180 for c in direct_carriers)
        f=dict(density=clip(direct_seats/300,0,1),lcc189=1. if lcc else .35 if ends&{'AER','MRV','MCX','LED'} and direct_seats>80 else 0.,
            aeroflot_cluster=1. if 'SVX' in ends else .65 if ends&{'KUF','KZN','UFA','PEE','AER','MRV'} else .2 if any(c['carrier'] in ('SU','FV') for c in direct_carriers) else 0.,
            nordwind_kzn=1. if 'KZN' in ends else .35 if any(c['carrier'] in ('N4','EO') for c in direct_carriers) else .1,
            s7_regional=1. if ends&{'OVB','IKT','VVO','KHV','KJA','BAX'} else .35 if any(c['carrier']=='S7' for c in direct_carriers) else 0.,
            subsidized_incumbent=1. if any(c['subsidy_2026_awarded_or_eligible'] for c in direct_carriers) else 0.)
        weights27=dict(density=.28,lcc189=.18,aeroflot_cluster=.10,nordwind_kzn=.12,s7_regional=.10,subsidized_incumbent=.14)
        weights28=dict(density=.28,lcc189=.18,aeroflot_cluster=.18,nordwind_kzn=.12,s7_regional=.10,subsidized_incumbent=.14)
        w27=sum(weights27[k]*v for k,v in f.items());w28=sum(weights28[k]*v for k,v in f.items())
        rwsub='WZ' in sub_codes[pair]
        anchor=directfare if directfare else min(ref,connfare)
        r=dict(**row,direct_competitors=[c['carrier'] for c in direct_carriers],connecting_competitors=sorted({q['carrier'] for q in conn}),direct_competitor_count=len(direct_carriers),
            competitor_daily_departures=sum(c['daily_departures'] for c in direct_carriers),competitor_weekly_departures=sum(c['weekly_departures'] for c in direct_carriers),competitor_daily_seats=direct_seats,
            F_comp_direct_20kg=directfare,F_comp_direct_p25_20kg=directp25,F_comp_transfer_20kg=connfare,transfer_duration_minutes=ctime,
            competitor_var_floor=min((c['variable_floor_unsubsidized'] for c in direct_carriers),default=None),competitor_full_floor=min((c['full_floor_unsubsidized'] for c in direct_carriers),default=None),
            competitor_var_floor_subsidy20_stress=min((c['variable_floor_subsidy20_stress'] for c in direct_carriers),default=None),
            W_comp_2027=w27,W_comp_2028=w28,risk_factors=f,risk_coefficients_2027=weights27,risk_coefficients_2028=weights28,
            direct_season_indices=route_profile[(pair,True)],transfer_season_indices=cp,subsidized_2026=subs[pair]['subsidized_2026'],subsidized_carriers_2026=sub_codes[pair],rw_subsidized_2026=rwsub,
            rw_future_support_baseline_rub=0,subsidy_source_url=subs[pair]['source_url'],subsidy_period=subs[pair]['subsidy_period_or_freq'],subsidy_special_fare_cap=sub_cap[pair],
            recommended_rw_market_match_annual=min(ref,anchor*1.03),rw_historical_direct_quotes=sum(q['carrier']=='WZ' and q['stops']==0 for q in qs),
            rw_historical_direct_fare_20kg=quantile([q['gross'] for q in qs if q['carrier']=='WZ' and q['stops']==0]),
            quote_count=len(qs),connecting_quote_count=len(conn),price_quality='B_RULE_NORMALIZED_NOT_EXACT_BAGGAGE',
            direct_presence_quality='observed_offer_or_schedule_or_2026_award' if direct_carriers else 'NOT_OBSERVED_NOT_PROVEN_ABSENT',connecting_price_quality=connquality,
            source_flags=sorted(set(s for c in direct_carriers for s in c['source_flags'])|({'travelpayouts_connecting'} if conn else set())),
            direct_carrier_details=direct_carriers)
        rows.append(r)
    hubs=[]
    for h in strategic['hub_assessments_22']:
        code=h['iata'];relevant=[r for r in rows if code in r['pair'].split('-') or code=='MOSCOW' and set(r['pair'].split('-'))&{'DME','SVO','VKO','ZIA'}]
        hubs.append(dict(hub=code,city=h['city_name'],routes=len(relevant),W_comp_2027=statistics.mean(r['W_comp_2027'] for r in relevant),W_comp_2028=statistics.mean(r['W_comp_2028'] for r in relevant),
            direct_density=statistics.mean(r['risk_factors']['density'] for r in relevant),lcc189=statistics.mean(r['risk_factors']['lcc189'] for r in relevant),aeroflot_cluster=statistics.mean(r['risk_factors']['aeroflot_cluster'] for r in relevant),nordwind_kzn=statistics.mean(r['risk_factors']['nordwind_kzn'] for r in relevant),s7_regional=statistics.mean(r['risk_factors']['s7_regional'] for r in relevant),subsidized_incumbent=statistics.mean(r['risk_factors']['subsidized_incumbent'] for r in relevant),
            assessment=h['overall_risk_2026_2028'],risk_status='SCENARIO_EXPOSURE_SCORE_NOT_PROBABILITY',expansion_2027='Q4_25pct_of_2028_intensity',expansion_2028='full_stress_intensity'))
    writecsv('market_competition_209.csv',rows);dump('market_competition_209.json',rows);writecsv('hub_weights_22.csv',hubs)
    writecsv('calibration/competitor_carrier_route.csv',carrier_rows);writecsv('calibration/seasonal_price_indices.csv',season_audit)
    writecsv('calibration/yandex_deduplicated_direct.csv',observations.values())
    summary=dict(routes=len(rows),hubs=len(hubs),raw_quotes=21346,clean_unique_quotes=len(quotes),rejected=dict(rejected),direct_pairs=sum(bool(r['direct_competitors']) for r in rows),
        direct_priced_pairs=sum(any(c['quotes'] for c in r['direct_carrier_details']) for r in rows),connecting_priced_pairs=sum(r['connecting_quote_count']>0 for r in rows),
        subsidy_2026_pairs=sum(r['subsidized_2026']!='false' for r in rows),rw_subsidized_2026_pairs=sum(r['rw_subsidized_2026'] for r in rows),unresolved_schedule_titles=dict(unresolved),
        notes=['Cache fares are offers, not sold yields. Baggage inclusion is unknown; addon is a rule-based scenario, not an exact checkout.',
        'Frequency estimate uses two winter days. Quote-only carriers use assumed 2 flights/week (range 1-7). 2027/28 capacity is a scenario extrapolation.',
        'Subsidy payment per passenger UNKNOWN. 20 percent floor relief is a sensitivity, never regional cofinancing percentage.',
        'All costs are 2026 RUB. Competitor 80k net fuel is conditional; RW main branch retains P09 gross fuel and zero new support.',
        'W_comp is a transparent linear exposure score, not a likelihood or measured elasticity.',
        'Moscow city-wide subsidy eligibility is not treated as exact-airport operated supply.'])
    dump('calibration/market_quality.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return rows

if __name__=='__main__':build()
