"""Канонический P06.compare и точная проекция P12. Без изменения чисел/null."""
import copy,gzip,hashlib,json,time
from pathlib import Path
import programme_builder as b
import evaluate_programmes as e

OUT=b.ROOT/'ui_results';UI=b.ROOT/'ui'
MONTH_FIELDS=['month','evaluation_id','programme_version','evaluation_mode','journeys','passenger_segments','revenue_net','variable_contribution','variable_contribution_before_support','variable_contribution_after_support','known_operating_subtotal','operating_result','operating_cash','investing_cash','tax_cash','financing_cash','cash_before_financing','interest_accrued','tax_accrued','recognized_support','compatible_carried_passengers','RPK_journey_cohort','ASK_flight_month','load_factor','load_factor_status','finance_interest_cash','minimum_cash','funding_before_financing','closing_cash','peak_funding_to_date']
LEG_FIELDS=['flight_instance_id','origin_airport','destination_airport','departure_utc','arrival_utc','aircraft_variant','operator','flight_number','seats','saleable_seats','project_network','role','source_status','scheduled_status','assumption_id','distance_km','reporting_flight_id']
TOP=['engine_version','delta_monthly','delta_annual','delta_summary','project_incremental_funding','project_pre_interest_funding_diagnostic','whole_company_funding','whole_company_funding_status','thresholds','donor_extra_deduction']
PROJECT=['context','bundle_sha256','status','input_acceptance','summary','results_annual','network_target','unknown_dependencies','used_assumption_ids','choice_calibration','global_optimality','own_migration_status','own_migration_transition_matrix']

def projection(full):
    out={k:copy.deepcopy(full[k]) for k in TOP}
    out['project']={k:copy.deepcopy(full['project'][k]) for k in PROJECT}
    out['project']['results_monthly']=[{k:r[k] for k in MONTH_FIELDS if k in r} for r in full['project']['results_monthly']]
    out['project']['operations']=copy.deepcopy(full['project']['operations'])
    out['keep']={k:copy.deepcopy(full['keep'][k]) for k in ['context','status','summary','bundle_sha256','results_annual']}
    out['network_changes']=[{**{k:r[k] for k in ['flight_instance_id','action']},**{side:None if r[side] is None else {k:r[side][k] for k in LEG_FIELDS if k in r[side]} for side in ['project','keep']}} for r in full['network_changes']]
    return out

def verify_projection(small,full):
    """Every present leaf is copied from the identical JSON path, including array index."""
    count=0
    def check(a,z,path='$'):
        nonlocal count
        if isinstance(a,dict):
            for k,v in a.items():assert k in z,path+'.'+k;check(v,z[k],path+'.'+k)
        elif isinstance(a,list):
            assert len(a)==len(z),path
            for i,(x,y) in enumerate(zip(a,z)):check(x,y,f'{path}[{i}]')
        else:assert type(a)==type(z) and a==z,(path,a,z);count+=1
    check(small,full);return count

def write_gzip(path,obj):
    encoder=json.JSONEncoder(ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    h=hashlib.sha256();n=0
    with path.open('wb') as sink:
        with gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0) as gz:
            for text in encoder.iterencode(obj):
                raw=text.encode();h.update(raw);n+=len(raw);gz.write(raw)
    check=hashlib.sha256()
    with gzip.open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):check.update(chunk)
    assert check.hexdigest()==h.hexdigest()
    return dict(path=str(path.relative_to(b.ROOT)),sha256=h.hexdigest(),serialization='UTF8 json sort_keys=True separators=comma/colon allow_nan=False; gzip mtime0',bytes_uncompressed=n,gzip_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes_gzip=path.stat().st_size)

def choose():
    ps=json.loads((b.ROOT/'programmes.json').read_text())['programmes'];data={}
    for path in (b.ROOT/'evaluations').glob('*__phased__*__passive.json'):
        r=json.loads(path.read_text());data[r['programme_id'],r['scenario']]=r
    points=[]
    for p in ps:
        pid=p['programme_id']
        if pid=='KEEP' or 'LOCAL_ONLY'in pid or p.get('stage_fragment'):continue
        rows=[data.get((pid,s),{}) for s in ['base','cautious']]
        if all(x.get('status')=='CONDITIONAL_P05_P06_CALCULATED' for x in rows):
            points.append(dict(programme_id=pid,min_delta_known_subtotal=min(x['delta_known_operating_subtotal'] for x in rows),min_delta_journeys=min(x['delta_journeys'] for x in rows)))
    frontier=[x for x in points if not any(y['min_delta_known_subtotal']>=x['min_delta_known_subtotal'] and y['min_delta_journeys']>=x['min_delta_journeys'] and (y['min_delta_known_subtotal']>x['min_delta_known_subtotal']+1e-5 or y['min_delta_journeys']>x['min_delta_journeys']+1e-5) for y in points if y!=x)]
    required=['SVX_RADIAL','SVX_BANK9','KUF_RADIAL','VOG_BANK9']
    ids=sorted({x['programme_id'] for x in frontier}|set(required))
    ids=[x for x in ids if x in {p['programme_id'] for p in ps}]
    b.dump(b.ROOT/'finalist_selection.json',dict(frontier=frontier,required_architecture_controls=required,selected=ids,criterion='Pareto по худшему из base/cautious: delta поездок и delta ЧАСТИЧНОГО subtotal; без вероятностей/весов. Дополнительные existing-base/existing-hub/new-hub контроли сохраняют архитектурное сравнение.',global_optimum=False,scope='Только перечисленные конструкции. Эмпирический рыночный победитель не установлен.'))
    return [p for p in ps if p['programme_id']in ids]

def main():
    OUT.mkdir(exist_ok=True);UI.mkdir(exist_ok=True)
    selection=choose();checks=[];index=[]
    b.dump(b.ROOT/'projection_contract.json',dict(version='P09-P12-projection-v1',authority='Q-P09-UI01 coordinator accepted B',source_full_compare='Exact return value of P06 core.compare at pin982, canonical gzip',result_mode='P06_FIXED_COMPARE_CANONICAL_WITH_P05_SCENARIO_PRIOR',paths={'$':TOP,'$.project':PROJECT,'$.project.results_monthly[*]':MONTH_FIELDS,'$.project.operations':'whole exact object including rotations','$.keep':['context','status','summary','bundle_sha256','results_annual'],'$.network_changes[*]':['flight_instance_id','action'],'$.network_changes[*].project|keep':LEG_FIELDS},rules=['Every leaf copied from same JSONpath/index; arrays not filtered','No rounding; no null substitution; no unit changes','No revenue aggregation in projection','Omitted unconsumed fields remain in full gzip; fullsource and projection have different byte hashes','Date-component overview is separate result_mode, compared by documented numeric tolerance, never byte-identical claim'],audit_script='canonical_finalists.py:verify_projection',replay='python3 canonical_finalists.py',pending='Координатор добавляет actualP09commit/manifest и ACCEPTED_FOR_UI только после собственных gates; здесь marker PENDING.'))
    for p in selection:
        evaluations=[]
        for scenario in ['base','cautious']:
            name='__'.join([p['programme_id'],'phased',scenario,'passive']);st=time.time()
            a,k=b.build_pair(p,'phased',scenario);full=b.core.compare(a,k)
            compressed=write_gzip(OUT/(name+'.canonical.json.gz'),full)
            small=projection(full);count=verify_projection(small,full)
            overview=json.loads((b.ROOT/'evaluations'/(name+'.json')).read_text())
            diffs=dict(journeys=full['delta_summary']['journeys']-overview['delta_journeys'],known_operating_subtotal=full['thresholds']['net_missing_operating_cost_break_even']-overview['delta_known_operating_subtotal'])
            assert abs(diffs['journeys'])<1e-6 and abs(diffs['known_operating_subtotal'])<.01,diffs
            proof=dict(evaluation_id=full['project']['context']['evaluation_id'],full=compressed,projection_sha256=b.digest(small),verified_same_path_leaves=count,project_bundle_sha256=b.digest(a),keep_bundle_sha256=b.digest(k),programme_sha256=b.digest(p),input_manifest=a['input_manifest'],mode='P06_FIXED_COMPARE_CANONICAL',overview_mode='P06_DISJOINT_DATE_COMPONENTS_WITH_ADDITIVE_P06_FINANCE',overview_path='evaluations/'+name+'.json',overview_sha256=hashlib.sha256((b.ROOT/'evaluations'/(name+'.json')).read_bytes()).hexdigest(),numeric_difference=diffs,tolerance={'journeys_absolute':1e-6,'RUB_absolute':.01},same_float_bytes_claim=False,builder_sha256=hashlib.sha256((b.ROOT/'programme_builder.py').read_bytes()).hexdigest(),method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
            b.dump(OUT/(name+'.receipt.json'),proof);checks.append(proof)
            evaluations.append(dict(label=p['label'],scenario_label='Базовый; поэтапная поставка; без поддержки' if scenario=='base' else 'Осторожный; поэтапная поставка; без поддержки',result_mode=proof['mode'],source_full_result_sha256=compressed['sha256'],source_full_result_path=compressed['path'],projection_sha256=proof['projection_sha256'],audit_receipt='ui_results/'+name+'.receipt.json',source_refs=['input_pins.json','programmes.json','local_rate_corrections.json','competition_row_lineage.json','parameterledger.json'],assumption_ids=[x['assumption_id'] for x in b.ASSUMPTIONS+b.P05_ASSUMPTIONS],result=small,conclusion='Условный сценарий; полный результат и reported share UNKNOWN. Для решения использовать порог непокрытых расходов и контрфакт KEEP.',competition_conclusion='Конкуренты учтены как P05 outside composite; отдельный response10 посчитан в сценарной матрице. P02 неполон, физическая будущая ёмкость неизвестна.',comparison_group_id=p['programme_id']+'-P09-v1'))
            print('canonical',name,'seconds',round(time.time()-st,1),'gzipMB',round(compressed['bytes_gzip']/1e6,2),'difference',diffs,flush=True)
            del full,a,k
        package=dict(dataset_kind='RED_WINGS',synthetic=False,coordinator_acceptance='PENDING_COORDINATOR_ACCEPTANCE',commit=None,manifest_sha256=None,result_mode='P06_FIXED_COMPARE_CANONICAL_EXACT_FIELD_PROJECTION',evaluations=evaluations,release_gates={'F07':'UNKNOWN_P10_COMPATIBLE_REPORTING_AND_WHOLE_BUSINESS'})
        path=UI/(p['programme_id']+'.json');b.dump(path,package)
        index.append(dict(programme_id=p['programme_id'],path=str(path.relative_to(b.ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
    b.dump(UI/'index.json',dict(packages=index,acceptance='PENDING_COORDINATOR_ACCEPTANCE',projection_contract='../projection_contract.json'))
    b.dump(b.ROOT/'canonical_equivalence_checks.json',dict(status='PASS',checks=checks,scope='Исполнение и exact projection; не рыночная или финансовая приёмка'))

if __name__=='__main__':main()
