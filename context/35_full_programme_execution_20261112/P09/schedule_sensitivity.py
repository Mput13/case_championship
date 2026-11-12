"""P03-основанные диагностические точки трассы1.10/1.20 и block limit8/10h."""
import copy,json,math
from collections import Counter,defaultdict
from functools import lru_cache
import programme_builder as b
import evaluate_programmes as e

def main():
    selected=set(json.loads((b.ROOT/'finalist_selection.json').read_text())['selected'])
    ps=[p for p in json.loads((b.ROOT/'programmes.json').read_text())['programmes'] if p['programme_id']in selected]
    rows=[];limits=[];baseblock=b.block
    for p in ps:
        cal=b.build_calendar(p)
        for limit in [8,10]:
            c=copy.deepcopy(cal)
            for t in c['fleet_calendar']:t['max_daily_block_hours']=limit
            op=b.check_operations(dict(context={'period_start':'2027-01','period_end':'2028-12'},resource_operators=['RW_SCENARIO'],**{k:c[k] for k in ['flights','fleet_calendar','assignments']}))
            limits.append(dict(programme_id=p['programme_id'],daily_block_limit_h=limit,status=op['status'],error_count=len(op['errors']),errors=op['errors'][:10],dispatch_ready=False,interpretation='Диагностическая точка author/P03, не установленная доступность экипажа. Неопровергает другие расписания.',assumption_id='P09-PERFORMANCE;P03-A002'))
    for factor in [1.10,1.20]:
        @lru_cache(maxsize=None)
        def block(a,z):return math.ceil((45+b.distance(a,z)*factor/650*60)/5)*5
        b.block=block;e.DAY_CACHE.clear()
        for p in ps:
            for scenario in ['base','cautious']:
                x=e.evaluate(p,'phased',scenario,'passive')
                rows.append(dict(programme_id=p['programme_id'],scenario=scenario,route_distance_multiplier=factor,status=x['status'],journeys=x.get('journeys'),delta_journeys=x.get('delta_journeys'),delta_known_operating_subtotal=x.get('delta_known_operating_subtotal'),full_delta_result=None,assumption_id='P09-AIRWAY-SENSITIVITY',basis='P03 assumptions_v2:1.10 ordinary/1.20south-west; applied to everyleg as explicit proxy sensitivity, no true-route forecast',result_mode='P06_DISJOINT_DATE_COMPONENTS',bank_downgrade_count=sum('BANK4LEGS'in z.get('reason','') for z in x.get('open_work',[]))))
    b.block=baseblock
    b.csvwrite(b.ROOT/'sensitivity_schedule.csv',rows);b.csvwrite(b.ROOT/'daily_resource_limit_checks.csv',limits)
    b.dump(b.ROOT/'schedule_sensitivity_assumption.json',b.assumption('P09-AIRWAY-SENSITIVITY',[1.10,1.20],'длина геодезического участка × множитель','P03 sp_adapter/assumptions_register_v2 source: author network.csv points; не эмпирические границы','Общее P05/P06 time/choice/cost и возможность bank','Прямой пересчёт всех dated legs и совместного спроса; UNKNOWN при операционном нарушении','OFP/ATC реальная трасса; type-specific fuel; сезонные ограничения'))
    print('schedule_sensitivity',len(rows),'resource_checks',len(limits),flush=True)

if __name__=='__main__':main()
