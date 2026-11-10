"""Optional owner replay, separate evidence from the independent oracle."""
import csv,json,math,os,subprocess,sys
from pathlib import Path
from prepare import HERE,PREFIX,SUBJECT,SNAP,blob

KEYS={
'connections_v1':{'summary.csv':['case'],'itinerary_assignments.csv':['case','inbound_flight','outbound_flight'],'flight_capacity.csv':['case','flight_id'],'certificates.csv':['case']},
'integer_year_v1':{'annual_comparison.csv':['case'],'annual_market_caps.csv':['case','origin','destination'],'weekly_allocation.csv':['case','week_start'],'weekly_choice_adjustments.csv':['case','week_start'],'OMS_2028_dated_flights.csv':['flight_id'],'OMS_2028_dated_itineraries.csv':['inbound_flight','outbound_flight'],'OMS_2028_capacity.csv':['flight_id']},
'synchronised_v1':{'flights.csv':['flight_id'],'connection_changes.csv':['state','inbound','outbound'],'market_changes.csv':['origin','destination'],'search_trace.csv':['sweep','tail'],'shift_cost_frontier.csv':['shift_cost_per_flight_hour_rub']},
'joint_products_v1':{'dated_connection_union.csv':['date','rw_flight','feed_flight'],'shared_flight_capacity.csv':['scenario','flight_id'],'joint_frontier.csv':['scenario','Tu_old_mission_loss_probe','Tu_allin_new_cost_probe']}}
MODULES={'connections_v1':'dated_connections.py','integer_year_v1':'integer_year_sales.py','synchronised_v1':'synchronised_alternative.py','joint_products_v1':'joint_products.py'}
DIFF=[];MAX=0.

def compare(x,y,path):
    global MAX
    if x==y:return
    if isinstance(x,dict) and isinstance(y,dict):
        assert x.keys()==y.keys(),path
        for k in x:compare(x[k],y[k],path+'/'+str(k))
        return
    try:
        a=float(x);b=float(y)
        if math.isfinite(a) and math.isfinite(b):
            err=abs(a-b);MAX=max(MAX,err)
            if err<=1e-4:return
    except (TypeError,ValueError):pass
    DIFF.append(dict(path=path,expected=x,actual=y))

result=[]
for run,module in MODULES.items():
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    proc=subprocess.run([sys.executable,'-B',str(SNAP/module)],cwd=SNAP,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    (HERE/('owner_'+run+'.log')).write_bytes(proc.stdout)
    assert proc.returncode==0,(module,proc.returncode,proc.stdout.decode()[-2000:])
    n=0;byte_same=0
    for fname,keys in KEYS[run].items():
        rel='runs/'+run+'/'+fname;expected=blob(PREFIX+rel);actual=(SNAP/rel).read_bytes();byte_same+=expected==actual
        old=list(csv.DictReader(expected.decode().splitlines()));new=list(csv.DictReader(actual.decode().splitlines()))
        make=lambda rows:{tuple(r[k] for k in keys):r for r in rows}
        a=make(old);b=make(new);assert len(a)==len(old) and len(b)==len(new),(rel,'duplicate keys')
        compare(a,b,rel);n+=len(old)
    rel='runs/'+run+'/validation.json';compare(json.loads(blob(PREFIX+rel)),json.loads((SNAP/rel).read_text()),rel)
    result.append(dict(module=module,exit_code=proc.returncode,csv_files=len(KEYS[run]),rows=n,csv_byte_identical=byte_same))
    print(module,'replayed',flush=True)
write=dict(subject=SUBJECT,status='PASS' if not DIFF else 'DIFFERENCES',semantic_tolerance_rub_or_quantity=1e-4,max_numeric_difference=MAX,runs=result,differences=DIFF,scope='Owner replay only. Independent oracle evidence is independent_results_all.json')
(HERE/'owner_replay_results.json').write_text(json.dumps(write,indent=2)+'\n')
assert not DIFF,DIFF[:5]
