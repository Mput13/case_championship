from pathlib import Path
import csv,json,hashlib,math,re,calendar
from datetime import date,timedelta
from calendar_engine import generate
ROOT=Path(__file__).resolve().parent; BASE=ROOT.parent
P03=BASE/'audit/inputs/audit_model/79dc698b/context/35_full_programme_execution_20261112/P03'
STEP=BASE/'audit/inputs/audit_model/dceadc98'
read_inputs=[]
def rows(p):
 p=Path(p);read_inputs.append(p);return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def js(p):
 p=Path(p);read_inputs.append(p);return json.loads(p.read_text())
def write(name,data):
 if name.endswith('.json'): (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');return
 keys=list(dict.fromkeys(k for r in data for k in r));
 with (ROOT/name).open('w') as f:
  w=csv.DictWriter(f,keys);w.writeheader();w.writerows(data)
# Completed source-review is the admission gate; no raw supplemental/calendar copies.
review=BASE/'source_review'
read_inputs.append(review/'README.md');(review/'README.md').read_text()
admission=rows(review/'source_admission.csv');findings=rows(review/'findings.csv')
canonical={p.name:rows(p) for p in sorted(review.glob('canonical_*.csv'))}
write('source_admission_gates.csv',admission)
write('source_review_delta.json',dict(status='COMPLETED_INPUT_GATE_APPLIED',numeric_updates_observed_OD=0,numeric_updates_net_yield=0,numeric_updates_contracts=0,quarantines=['S07 applies ZIA-TBS not SVX-TBS; SVX type UNKNOWN','forward WZ1403 not reverse proof','SVX-BRU endpoint/country unresolved; no numerical or domestic admission'],historical_only=['SVX-TBS9/week summer2026','KUF-TAS2/week2025/26'],target_week_unknown=['TJM-MRV Yamal'],calendar='KUF-GOJ Mon/Fri exceptions27/30Nov; extra30Dec; throughMarch2027 includesDecember2026; secondary only',commercial='4200kg compartment not residual; RW sells blocks not partner purchase right',technical='F11 confirms old non-Git raw+existing venv; no new provenance'))
contract=js(BASE/'audit/common_contract.json');res=contract['resource']; extra=js(ROOT/'extra_pins.json')
net=rows(STEP/'data/processed/network_routes.csv'); air=rows(P03/'airport_constraints.csv'); types=rows(P03/'aircraft_type_parameters.csv')
write('source_index.csv',rows(P03/'sources.csv'))
keep=rows(P03/'existing_commitments.csv'); mins=rows(P03/'minimum_resource_required.csv');rules=js(P03/'operating_rules.json')
for n in ['prior_task_refs.csv','keep_policies_sp08.csv','committed_payment_refs.csv','assignments_sp07.csv','fleet_calendar_sp07.csv','return_template_aircraft_days.csv','flights_sp04.csv']:
 rows(ROOT/'inputs/context/35_full_programme_execution_20261112/P03/sp_adapter'/n)
js(P03/'handoff.json');js(BASE/'audit/inputs/audit_model/982f13d9/context/35_full_programme_execution_20261112/P06/producer_contract.json')
# All published P03 airport coverage retained, no distance or competitor exclusion.
write('airport_aircraft_gates.csv',[dict(**r,tail_variant_assignment='UNKNOWN',MTOW='UNKNOWN',payload_route_alternate='UNKNOWN',transit_rights='UNKNOWN',future_dispatch='requires_ops_check',hard_exclusion='NONE_INFERRED',evidence_note='P03 snapshot only; even published reception is not2027/28 approval') for r in air])
# Directed primary snapshot clocks; never reverse or average directions.
off={'KUF':4,'SVX':5,'MRV':3,'NJC':5,'OMS':6,'REN':5,'KJA':7,'GOJ':3}
service=rows(ROOT/'inputs/context/28_evening_run_20261110/network/v2/outputs/primary_service_rows.csv');blocks=[]
for r in service:
 src=r['source_id'];parts=[x.strip() for x in r['row'].split('|')]
 if src not in ['kuf_dep','kuf_arr','svx_dep','svx_arr'] or len(parts)!=8:continue
 base=src[:3].upper();peer=parts[7];a,b=(base,peer) if src.endswith('dep') else (peer,base)
 if a not in off or b not in off:continue
 clocks=[]
 for c in parts[:2]:
  m=re.search(r'(\d\d):(\d\d)',c)
  if not m:break
  clocks.append(int(m[1])*60+int(m[2])+(1440 if '(+1)' in c else 0))
 if len(clocks)!=2:continue
 duration=clocks[1]-clocks[0]+(off[a]-off[b])*60
 if duration<=0:duration+=1440
 blocks.append(dict(origin=a,destination=b,aircraft_variant=parts[6],flight=parts[5],period_raw=parts[3],weekdays_raw=parts[2],departure_local=parts[0],arrival_local=parts[1],published_minutes=duration,nominal_minutes='',high_minutes='',evidence='PRIMARY_PUBLISHED_OFFER_SNAPSHOT_NOT_FLOWN',source_id=src,source_row=r['source_table_row'],source_url=r['source_url'],source_body_sha256=r['source_sha256'],future_transfer='requires_ops_check; no automatic2027-28 applicability',basis='local clocks converted with separate UTC offsets',ops_status='requires_ops_check'))
corrected=canonical['canonical_calendar_directed_schedule_rows.csv']; rows(BASE/'coordinator/calendar_corrected/sources.csv')
for r in corrected:
 if r['source_id'] not in ['S1','S2','S4']:continue
 a,b=('KUF','GOJ') if r['source_id'] in ['S1','S2'] else (('SVX','GOJ') if 'Yekaterinburg' in r['origin'] else ('GOJ','SVX'))
 def clock(x):return int(x[:2])*60+int(x[3:5])
 duration=(clock(r['arrival_local'])-clock(r['departure_local'])+(off[a]-off[b])*60)%1440
 blocks.append(dict(origin=a,destination=b,aircraft_variant='UNKNOWN',flight=r['flight'],period_raw=r['season'],weekdays_raw=r['day_or_date'],departure_local=r['departure_local'],arrival_local=r['arrival_local'],published_minutes=duration,nominal_minutes='',high_minutes='',evidence='CORRECTED_SAVED_LISTING_SECONDARY_OR_BOARD_UNVERIFIED',source_id=r['source_id'],source_row='',source_url='see coordinator/calendar_corrected/sources.csv',source_body_sha256='',future_transfer='requires_ops_check',basis='timezone-corrected clocks; original authenticity not upgraded',ops_status='requires_ops_check'))
# Complete candidate families from P03 network/KEEP + domestic/supplemental source scopes.
pairs={(r['from'],r['to']) for r in net if r['from'] in ['SVX','KUF','GOJ','CEK','MRV','TJM','MOW','OMS'] or r['to'] in ['SVX','KUF','GOJ','CEK','MRV','TJM','MOW','OMS']}
pairs|={(r['a'],r['b']) for r in keep}
for r in rows(BASE/'market_domestic/directed_services.csv')+canonical['canonical_supplemental_directed_services.csv']+canonical['canonical_portfolio_pairs.csv']:
 pairs.add((r['origin_iata'],r['destination_iata']))
pairs|={(b,a) for a,b in pairs}
known={(r['origin'],r['destination']) for r in blocks}
for a,b in sorted(pairs-known):
 blocks.append(dict(origin=a,destination=b,aircraft_variant='RRJ95B/LR or SJ100 must be assigned separately',published_minutes='',nominal_minutes='',high_minutes='',evidence='QUARANTINED_UNRESOLVED_ENDPOINT' if 'BRU' in [a,b] else 'UNKNOWN_CASE_SPECIFIC_BLOCK',source_id='P03/author candidate scope + source_review canonical admission',future_transfer='requires_ops_check',basis='No justified directed nominal/high; threshold only, do not use geometry as flight time',ops_status='requires_ops_check'))
# Preserve GOJ proxy solely as archived cost-screen; not engine-ready blocks.
proxy=rows(ROOT/'inputs/context/35_full_programme_execution_20261112/P03/sp_adapter/flights_sp04.csv')
for a,b in sorted(set((r['origin_airport'],r['destination_airport']) for r in proxy)):
 v=next(r['block_minutes'] for r in proxy if r['origin_airport']==a and r['destination_airport']==b)
 blocks.append(dict(origin=a,destination=b,aircraft_variant='SJ100_PD8 diagnostic transfer only',published_minutes='',nominal_minutes='',high_minutes='',costscreen_minutes=v,evidence='P03_GEOMETRIC_DIAGNOSTIC_COSTSCREEN_ONLY',source_id='P03-A020',basis='P03 rounded proxy; no valid published block for ready schedule',ops_status='requires_ops_check'))
# Explicit same-direction/variant historical analogue scenarios; not approved future blocks.
analogue_groups={}
for r in blocks:
 if r['evidence']=='PRIMARY_PUBLISHED_OFFER_SNAPSHOT_NOT_FLOWN' and r.get('aircraft_variant','').startswith('RRJ'):
  analogue_groups.setdefault((r['origin'],r['destination'],r['aircraft_variant']),[]).append(r)
for (a,b,v),group in sorted(analogue_groups.items()):
 values=[int(r['published_minutes']) for r in group]
 blocks.append(dict(origin=a,destination=b,aircraft_variant=v,published_minutes='',nominal_minutes=min(values),high_minutes=max(values),evidence='SCENARIO_HISTORICAL_SAME_DIRECTED_ROUTE_VARIANT_ANALOGUE',source_id=';'.join(sorted(set(r['source_id'] for r in group))),source_row=';'.join(r['source_row'] for r in group),basis='historical published min/max of exact directed route+variant; preserves direction; not confidence bounds or2027 block guarantee',future_transfer='requires_ops_check: same physical airports; exact variant; route/season/wind/ATC/slot and payload must be accepted before use',ops_status='requires_ops_check'))
write('directed_blocks.csv',blocks)
# Daily shared E/S envelope, alternative evaluations never simultaneous pools.
resource=[];start=date(2027,1,1);end=date(2029,1,1)
for e in range(3):
 for s,deliveries in res['deliveries'].items():
  for i in range((end-start).days):
   day=start+timedelta(days=i)
   units=[dict(id='EX-'+str(j+1),type='RRJ95_EXISTING_VARIANT_UNKNOWN',role='working',delivery='',entry='2027-01-01',state='CONDITIONAL_RELEASE') for j in range(e)]
   units+=[dict(id='RES-1',type='RRJ95_EXISTING_VARIANT_UNKNOWN',role='reserve',delivery='',entry='2027-01-01',state='CONDITIONAL_SEPARATE_DONOR')]
   for d in deliveries:
    state='NOT_DELIVERED' if day.isoformat()<d['delivery'] else ('INDUCTION_NO_FLIGHTS' if day.isoformat()<d['entry'] else 'CONDITIONAL_ENTRY')
    units.append(dict(id=d['id'],type='SJ100_PD8',role='working',delivery=d['delivery'],entry=d['entry'],state=state))
   for u in units:
    resource.append(dict(evaluation_resource=f'E{e}/{s}',date=day.isoformat(),slot_id=u['id'],aircraft_type=u['type'],role=u['role'],delivery_date=u['delivery'],entry_date=u['entry'],state=u['state'],scenario_working_available=int(u['role']=='working' and u['state'] in ['CONDITIONAL_RELEASE','CONDITIONAL_ENTRY']),actual_tail='UNKNOWN',actual_available='UNKNOWN',location='UNKNOWN',positioning='UNKNOWN_PAID_GATE',maintenance='UNKNOWN',crew='UNKNOWN',donor='UNKNOWN_REQUIRED_SEPARATE_FOR_EACH_EXISTING_SLOT_AND_RESERVE',contract='UNKNOWN',reserve_owner='ONE_PROGRAMME_PER_EVALUATION',source='audit/common_contract.json; AUDIT-SC01'))
write('resource_calendar.csv',resource)
# Current fixed physical legs retained, no silent resize or invented confirmed DOW.
reflegs=[];definitions=[]
for case in ['base','cautious']:
 for programme,selected in [('dashboard_fixed_triangles',[r for r in net if r['scenario']==case and r['variant'].startswith('Прямые')]),('hub_OMS_reference',[r for r in net if r['scenario']==case and r['variant']=='Хаб OMS']),('hub_GOJ_reference',[r for r in net if r['scenario']==case and r['variant']=='Хаб GOJ'])]:
  for j,r in enumerate(selected):
   for a,b in [(r['from'],r['to']),(r['to'],r['from'])]:
    reflegs.append(dict(programme=programme,case=case,pattern=r['variant'],origin_market=a,destination_market=b,scenario_physical_origin='ZIA' if a=='MOW' else a,scenario_physical_destination='ZIA' if b=='MOW' else b,airport_resolution='ZIA_ANALYST_SCENARIO_NOT_PUBLISHED' if 'MOW' in [a,b] else 'named',freq_week_direction=r['freq_week_each_way'],actual_flight_dates='UNKNOWN',DOW='UNKNOWN',calendar_status='ABSTRACT_VOLUME_ONLY',source='dceadc98:data/processed/network_routes.csv'))
  weekly=sum(float(r['freq_week_each_way'])*2 for r in selected)
  if programme.startswith('dashboard'):
   # Same formula as P03 only a labelled necessary cost-screen, never ops block.
   hours=sum((0.5+float(r['km'])/750*1.2)*float(r['freq_week_each_way'])*2 for r in selected);lower=math.ceil(hours/56)
  else:
   m=next(r for r in mins if r['programme_id']==f'ARCHIVE_HUB_{"OMS" if "OMS" in programme else "GOJ"}_{case}' and r['block_proxy_k']=='1.2' and r['screening_utilisation']=='8');hours=float(m['block_proxy_hours_week']);lower=int(m['minimum_working_tails_hours_only'])
  definitions.append(dict(programme=programme,case=case,weekly=weekly,hours=hours,lower=lower,triangles=len(set(r['variant'] for r in selected)) if programme.startswith('dashboard') else 0,pairs=len(set(tuple(sorted([r['from'],r['to']])) for r in selected))))
write('reference_physical_legs.csv',reflegs)
feas=[]
for monthindex in range(24):
 year=2027+monthindex//12;month=monthindex%12+1;day=f'{year}-{month:02d}-01'
 for e in range(3):
  for s,deliveries in res['deliveries'].items():
   n=e+sum(d['entry']<=day for d in deliveries)
   for d in definitions:
    fail=n<d['lower']
    feas.append(dict(programme=d['programme'],case=d['case'],resource=f'E{e}/{s}',month=day[:7],working_slots=n,reserve_slots_conditional=1,triangles=d['triangles'],unique_pairs=d['pairs'],physical_departures_representative_week=d['weekly'],actual_flight_dates='UNKNOWN',costscreen_BH_week=d['hours'],costscreen_min_working=d['lower'],status='INFEASIBLE_UNDER_NAMED_PROXY_8BH_SCENARIO' if fail else 'CONDITIONAL_UNDATED',dated_schedule='UNKNOWN',crew='UNKNOWN',maintenance='UNKNOWN',critical_gate='actual directed blocks; DOW/operating weeks; airport MOW resolution; donor/positioning/crew/MRO/reserve',source='P03 necessary hours-only screen; not dispatch rejection; no resize'))
   feas.append(dict(programme='KEEP',case='COMMON_SAME_EXTERNAL_SCENARIO',resource=f'E{e}/{s}',month=day[:7],working_slots=n,reserve_slots_conditional=1,status='UNKNOWN_DATED_AFFECTED_KEEP',actual_flight_dates='UNKNOWN',dated_schedule='UNKNOWN',crew='UNKNOWN',maintenance='UNKNOWN',critical_gate='P03 existing obligations/previous tasks/committed payments; E0S0 forbids added flight; retime only same physical flight with donor proof',source='P03 existing_commitments + prior_task_refs; absent data is not0'))
write('reference_feasibility.csv',feas)
# Explicit scenario dates for a single representative week per month, without invented clocks/tails.
# Forward and reverse three-leg loops are separate rotations (six total legs per f).
scenario_dates=[]
for mi in range(24):
 year=2027+mi//12;month=mi%12+1;first=date(year,month,1);monday=first+timedelta(days=(-first.weekday())%7)
 for case in ['base','cautious']:
  chosen=[r for r in net if r['scenario']==case and r['variant'].startswith('Прямые')]
  for variant in sorted(set(r['variant'] for r in chosen)):
   group=[r for r in chosen if r['variant']==variant];path=[group[0]['from']]+[r['to'] for r in group]
   assert len(path)==4 and path[0]==path[-1]
   f=int(float(group[0]['freq_week_each_way']))
   for orientation,loop in [('forward',path),('reverse',list(reversed(path)))]:
    for k in range(f):
     day=monday+timedelta(days=k%7);rid=f'{case}/{variant}/{day}/{orientation}/{k}'
     for i,(a,b) in enumerate(zip(loop,loop[1:])):
      scenario_dates.append(dict(programme='dashboard_fixed_triangles',case=case,rotation_id=rid,scenario_departure_date=day.isoformat(),leg=i+1,origin='ZIA' if a=='MOW' else a,destination='ZIA' if b=='MOW' else b,departure_clock='UNKNOWN',arrival_clock='UNKNOWN',tail='UNASSIGNED_RESOURCE_DEFICIT',actual_flight_date='UNKNOWN',status='SCENARIO_DATE_ONLY_NOT_VALIDATED_SCHEDULE',gate='directed blocks+N(t)+MOW airport+positioning+crew/MRO; same monthly E/S rows'))
  for hub in ['OMS','GOJ']:
   for row in [r for r in net if r['scenario']==case and r['variant']=='Хаб '+hub]:
    for k in range(int(float(row['freq_week_each_way']))):
     day=monday+timedelta(days=k%7);rid=f'{case}/hub_{hub}/{row["to"]}/{day}/{k}'
     for i,(a,b) in enumerate([(row['from'],row['to']),(row['to'],row['from'])]):
      scenario_dates.append(dict(programme='hub_'+hub+'_reference',case=case,rotation_id=rid,scenario_departure_date=day.isoformat(),leg=i+1,origin='ZIA' if a=='MOW' else a,destination='ZIA' if b=='MOW' else b,departure_clock='UNKNOWN',arrival_clock='UNKNOWN',tail='UNASSIGNED',actual_flight_date='UNKNOWN',status='SCENARIO_DATE_ONLY_NOT_VALIDATED_SCHEDULE',gate='operating weeks and actual DOW unknown; no annual expansion'))
write('reference_scenario_dates.csv',scenario_dates)
# API proof: deliberately synthetic legs, no RW market result.
tz={'KUF':'Europe/Samara','GOJ':'Europe/Moscow','SVX':'Asia/Yekaterinburg'}
request=dict(timezones=tz,turn_minutes=45,blocks=[dict(origin=a,destination=b,nominal_minutes=60,high_minutes=75,evidence='SYNTHETIC_API_TEST_NOT_RW') for a in tz for b in tz if a!=b],tails=[dict(id='DEMO-W',type='RRJ95_SCENARIO',initial_location='KUF',available_from='2027-01-01T00:00:00Z',available_to='2029-01-01T00:00:00Z',donor='UNKNOWN'),dict(id='DEMO-R',type='RRJ95_SCENARIO',reserve=True)],patterns=[])
for name,path,days in [('normalRT',['KUF','GOJ','KUF'],[1]),('triangle',['KUF','GOJ','SVX','KUF'],[2]),('addfreq',['KUF','GOJ','KUF'],[3])]:
 request['patterns'].append(dict(id=name,path=path,weekdays=days,frequency_per_week=1,operating_weeks=['2027-01-04'],start='2027-01-04',end='2027-01-10',departure_local='09:00',workingtailids=['DEMO-W']))
write('example_request.json',request);result=generate(request);write('example_result.json',result)
write('pattern_examples.csv',[dict(**r,scope='SYNTHETIC_ONLY_NOT_RW_MARKET_RESULT') for r in result['rotations']])
write('assumptions.csv',[dict(id=k,value=v,status=s,limitation=l) for k,v,s,l in [
 ('OPS01','E0/E1/E2 + separate reserve; S0/S1/S1D6','SCENARIO','audit shared N(t); no published fleet release'),
 ('OPS02','8BH per UTC day;45min turns','P03_SCENARIO','not legal crew duty/rest limit; actual local policy UNKNOWN'),
 ('OPS03','ZIA for all reference MOW legs','SCENARIO_RESOLUTION_ONLY','MOW is city; actual DME/ZIA flight assignment UNKNOWN, no implicit ferry'),
 ('OPS04','same-directed-route/variant historical min/max as conditional analogue; unsupported blank','SCENARIO_OR_UNKNOWN','historical published envelope is not future approved block or probability bound; no arbitrary+20%'),
 ('OPS05','P03 geometric hours used only necessary resource costscreen','COSTSCREEN_ONLY','does not make ready schedule; payload/route/AFM/NOTAM separate'),
 ('OPS06','synthetic60/75min demo legs','SYNTHETIC','proves counting/calendar API only; no analogue inference'),
 ('OPS07','base/cautious fixed author lists kept separately','ARCHIVED_SCENARIO','no demand rank or economic evaluation'),
 ('OPS08','BH split UTC midnight; cycles departure date','ACCOUNTING_CONVENTION','local dates also retained; no duplication across year boundary')]])
# Manifest: read-only pinned inputs + local completed sources; hash all consumed bytes.
read_inputs.extend([BASE/'audit/inputs/audit_model/982f13d9/context/35_full_programme_execution_20261112/P06/engine'/n for n in ['common.py','operations.py']])
manifest=[];auditmanifest=js(BASE/'audit/source_manifest.json');bylocal={str(Path(r['local_path']).resolve()):r for r in auditmanifest}
for p in sorted(set(read_inputs),key=str):
 if p==ROOT/'extra_pins.json':continue
 item=dict(local_path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='saved research input; no new primary verification')
 pin=bylocal.get(str(p.resolve())) or next((x for x in extra if (BASE/x['local_path']).resolve()==p.resolve()),None)
 if pin:
  assert item['sha256']==pin['sha256'], 'Pinned input hash mismatch: '+str(p)
  item.update(commit=pin['commit'],git_path=pin['path'])
 manifest.append(item)
raw=BASE.parent/'30_defense_research_20261111/inputs/model_schedule/latest/data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv'
manifest.append(dict(local_path=str(raw),sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),scope='AUDIT SNAPSHOT hash verification only; not Git-primary pin; not new source evidence; not used for ops demand'))
write('source_manifest.json',manifest)
write('handoff.json',dict(status='COMPLETED_SCOPED_CONDITIONAL_OPS_INPUT',write_scope='ops_inputs/',ready_for='final assembler; do not wait route_economics',source_review_gate='source_review_delta.json; source_admission_gates.csv; canonical copies only',numeric_source_updates=0,route_economics_read=False,network_selection=False,contract='audit/common_contract.json',calendar_API='calendar_engine.generate(request) or CLI',block_policy='published historical minutes retained; explicit same-direction/type historical min/max analogue scenarios only; unsupported nominal/high blank',reserve_policy='RES-1 unique within evaluation; alternative networks compete for same pool',critical_gates=['actual released tail+donor+reserve contract','dated KEEP commitments','direction/season/type specific blocks','physical MOW airport','positioning+crew/rest+MRO windows','payload/AFM/NOTAM/rights'],output_semantics='physical consistency does not imply operational approval',raw_snapshot_sha256=manifest[-1]['sha256']))
print(json.dumps(dict(block_rows=len(blocks),resource_rows=len(resource),reference_rows=len(feas),demo_status=result['status']),ensure_ascii=False))
