from pathlib import Path
import csv,json,difflib
O=Path(__file__).resolve().parent;R=O.parent
read=lambda p:list(csv.DictReader(p.open()))
results=json.loads((O/'independent_results.json').read_text());oms=results['OMS_CURRENT_BASE'];front=read(R/'economics/breakeven_frontier.csv')
findings=[dict(id='F01',priority='P1',file_line='economics/calculate.py:115; economics/seasonality_cases.csv:1; economics/verify.py:44',effect='20 строк UNCHANGED_WEEKLY_PROFILE сохраняют weeks=52 при period_weeks=48/26/22/13; все 30 сезонных строк используют *_year для сумм периода. Риск неверного annualization и сравнения с годовым F.',minimal_fix='После масштабирования z["weeks"]=n; только в seasonality_cases переименовать все *_year в *_period; добавить totals_basis=PERIOD_NOT_ANNUALIZED и проверку weeks==period_weeks. Числа не менять. Согласовать потребителей и проверку колонок.'),dict(id='F02',priority='P2',file_line='economics/README.md:21; economics/baseline_ledger.csv:1; economics/calculate.py:66',effect='other_variable_rub — сумма шести подробных nonfuel колонок, но README явно не объясняет агрегат. Сложение агрегата с деталями повторно завысит OMS12 расходы на 2284087980.968599 руб./52 недели.',minimal_fix='Добавить точное равенство агрегата и cost=net_fuel+other_variable; явно запретить повторное сложение агрегата и деталей. Расчёт верен, правка документации.')]
with (O/'findings.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['id','priority','file_line','effect','minimal_fix']);w.writeheader();w.writerows(findings)
# Review-only patch. Never apply to owner outputs here.
changes={}
p=R/'economics/calculate.py';old=p.read_text();new=old.replace("            season.append(dict(z,case='UNCHANGED_WEEKLY_PROFILE'","            z['weeks']=n\n            season.append(dict(z,case='UNCHANGED_WEEKLY_PROFILE'")
needle="    for h in [b for b in baseline"
new=new.replace(needle,"    season=[{(k[:-5]+'_period' if k.endswith('_year') else k):v for k,v in r.items()} | {'totals_basis':'PERIOD_NOT_ANNUALIZED'} for r in season]\n"+needle)
changes['economics/calculate.py']=(old,new)
p=R/'economics/verify.py';old=p.read_text();new=old.replace("  if r['case']=='UNCHANGED_WEEKLY_PROFILE':", "  check(n+'_period_metadata',float(r['weeks'])==float(r['period_weeks']) and r['totals_basis']=='PERIOD_NOT_ANNUALIZED')\n  if r['case']=='UNCHANGED_WEEKLY_PROFILE':")
new=new.replace("close(float(r[k]),f(k)*float(r['period_weeks'])/52)","close(float(r[k[:-5]+'_period' if k.endswith('_year') else k]),f(k)*float(r['period_weeks'])/52)")
changes['economics/verify.py']=(old,new)
p=R/'economics/README.md';old=p.read_text();new=old.replace('Одна пересадочная поездка', '`other_variable_rub = mro_rub + crew_rub + navigation_rub + ground_rub + deicing_rub + pax_cost_rub`. Это агрегат, а не дополнительная статья. `cost_rub_year = net_fuel_rub + other_variable_rub`: агрегат и его детали повторно не складывать. В seasonality_cases поля `*_period` содержат суммы за `period_weeks`, `weeks` равно этому периоду; суммы не annualized. Остальные денежные и пассажирские потоки этой таблицы также относятся к периоду; ставки, парк и недельные величины не масштабируются.\n\nОдна пересадочная поездка')
changes['economics/README.md']=(old,new)
patch=''
for path,(old,new) in changes.items():
 if path.endswith('.py'):compile(new,path,'exec')
 patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
(O/'minimal_metadata.patch').write_text(patch)
# Exact illustrative corrected rows, not a replacement owner export.
sample=[]
for r in read(R/'economics/seasonality_cases.csv'):
 if r['network_id']=='OMS_CURRENT_BASE' and r['case']=='UNCHANGED_WEEKLY_PROFILE' and r['period_weeks'] in ('48','26'):
  z={(k[:-5]+'_period' if k.endswith('_year') else k):v for k,v in r.items()};z['weeks']=r['period_weeks'];z['totals_basis']='PERIOD_NOT_ANNUALIZED';sample.append(z)
with (O/'seasonality_metadata_example.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(sample[0]));w.writeheader();w.writerows(sample)
claims=[]
def claim(name,value,unit,period,meaning,forbidden):claims.append(dict(claim=name,value=value,unit=unit,period=period,confirmed_meaning=meaning,must_not_say=forbidden))
for n,b in results.items():claim(n,b['contribution_rub_year'],'RUB','52 model weeks','Вклад после переменных расходов; состав и частоты фиксированы','Чистая прибыль; одинаковый фактический парк и календарь; разрешение запуска')
for k in (0,3024,32930):claim('OMS_credit_'+str(k),oms['contribution_rub_year']+(k-32930)*oms['fuel_tonnes'],'RUB','52 model weeks','Меняется только k RUB/model tonne, прочее фиксировано','Будущий гарантированный вычет RW; eligible tonnes равны сжиганию')
for k in ['fuel_tonnes','gross_fuel_rub','fuel_credit_rub','net_fuel_rub','other_variable_rub','forgone_rw_rub','transfer_od_year']:
 claim('OMS_'+k,oms[k],'metric tonnes' if k=='fuel_tonnes' else 'OD journeys' if k=='transfer_od_year' else 'RUB','52 model weeks','Модельный ledger, условная арифметика','Измеренный факт авиакомпании; источник цен подтверждён replay')
claim('credit_threshold',(oms['fuel_credit_rub']-oms['contribution_rub_year'])/oms['fuel_tonnes'],'RUB/tonne','52 model weeks; F=0','При F RUB/52 weeks прибавить F/34599.6553293714','Полная безубыточность при неизвестном F')
for r in front:
 if r['network_id']=='OMS_CURRENT_BASE' and r['k_rub_t']=='32930' and r['F_budget_axis_rub_year']=='0':
  field='required_retained_model_od_fraction' if r['required_retained_model_od_fraction'] else 'required_receipts_or_fare_multiplier'
  claim(field,float(r[field]),'fraction','52 model weeks; F=0','Разные оси: OD пересчитывает пассажиров/pax cost/RW; receipts удерживает пассажиров','Измеренная сезонность; одинаковые эксперименты')
claim('ramp_transfer',results['OMS_RAMP3_BASE']['transfer_od_year'],'OD journeys','52 model weeks','Сценарный поток ramp6','188817 зрелого OMS12 обеспечены стартовой ramp')
claim('ramp_calendar',{'legs':44,'nominal_hours':136,'high_hours':161.5,'capacity_hours':140,'high_turn_failures':22,'connections':110,'screened_45_240_min':15},'mixed: legs, hours, cases','repeating scenario week 2027-09-06/12','Номинальная связность кодов аэропортов и UTC/local подтверждена; high stress FAIL','Физическая невозможность маршрутов; подтверждённый MCT/слоты/парк/crew/ТО')
claim('new_numeric_inputs',0,'admitted updates','review 2026-11-11','Новых чисел из buyers/OMS тарифов нет','Нет реального спроса или расходов')
summary=dict(verdict='CHANGES',pin='0b0fbcb742ea2e54e05b80a5b8e890200fd5daae',strategy='OMS retained',claims=claims,comparison_rule='F_hub-F_direct < delta_contribution; unequal actual modeled fleets 7/8/9 and no verified common calendar',budget_landmarks={'values':[0,100000000,200000000,400000000],'unit':'RUB/52 weeks','meaning':'scenario axis, not base quote'},unknown=['full PnL','RW eligibility and eligible tonnes','future k and cash lag','monthly OD','F/A/deposits/peak cash/payback','MOW airport/real directional blocks/MCT/through ticket','crew/MRO/aircraft delivery/release/slots','H1 MOW/KUF/KJA pilot frequencies'],provenance_limit='Tracked pin files matched stored Git blobs; raw 23.5MB Tochno snapshot explicitly UNTRACKED_RAW_FROM_PRIOR_AUDIT, SHA matched; not all replay dependencies exact Git pin; no live remote freshness check',tests={'count':296,'passed':276,'known_metadata_failures':20,'unexpected_failures':0},patch='minimal_metadata.patch, not applied; syntax compiled only')
(O/'reviewed_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
