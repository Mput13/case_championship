"""Коэффициенты неизвестных ставок и месячный ресурс; деньги не пересчитываются в UI."""
import csv,json,collections
import programme_builder as b
P=b.ROOT

def main():
    ps={p['programme_id']:p for p in json.loads((P/'programmes.json').read_text())['programmes']};selected=json.loads((P/'finalist_selection.json').read_text())['selected'];rows=[];res=[]
    for d in ['phased','partial','delayed','none']:
        fleet=b.fleet(d)
        for m in b.MONTHS:
            for variant in sorted({t['variant'] for t in fleet}):
                ts=[t for t in fleet if t['variant']==variant];entered=[t for t in ts if t['service_entry_date'][:7]<=m];transferred=[t for t in ts if t['transfer_date'][:7]<=m]
                res.append(dict(delivery=d,month=m,aircraft_variant=variant,transferred=len(transferred),entered_service=len(entered),reserve=sum(t['reserve_role'] for t in entered),scenario_working_tails=sum(not t['reserve_role'] for t in entered),project_available=None,crew_maintenance_status='UNKNOWN; рабочийсценарныйпрофиль не фактическая доступность',status='SCENARIO_MONTH_END_NOT_RW_DELIVERY_PLAN',source='fleet_calendar.json',assumption_ids=['P09-RESOURCE','P09-ENTRY','P09-OPS']))
        kc=b.build_calendar(b.KEEP,d);kbh=sum((b.p05.utc(f['arrival_utc'])-b.p05.utc(f['departure_utc'])).total_seconds()/3600 for f in kc['flights'])
        for pid in selected:
            pc=b.build_calendar(ps[pid],d);pbh=sum((b.p05.utc(f['arrival_utc'])-b.p05.utc(f['departure_utc'])).total_seconds()/3600 for f in pc['flights']);coefficient=pbh-kbh
            for sc in ['base','cautious']:
                r=json.loads((P/'evaluations'/('__'.join([pid,d,sc,'passive'])+'.json')).read_text());H=r['delta_known_operating_subtotal']
                rows.append(dict(programme_id=pid,delivery=d,scenario=sc,H=H,unknown_driver='additional_common_crew_or_MRO_residual_rate_per_BH_ABOVE_INCLUDED_REFERENCE',driver_unit='RUB2026/BH',project_BH=pbh,KEEP_BH=kbh,delta_coefficient=coefficient,break_even_rate=None if abs(coefficient)<1e-10 else H/coefficient,inequality='coefficient*x <= H',direction='upper_bound' if coefficient>1e-10 else 'lower_bound' if coefficient< -1e-10 else 'no_slope',condition='Одна остаточная ставка за раз, остальные неизвестные зафиксированы. Не складывать с уже включённой P04 reference crew/MRO частью.',assumption_id='P09-MISSING;P09-COST',credible_range='UNKNOWN',source_help='Actual payroll/crew roster or MRO contract; separate avoidable/hourly and fixed costs'))
    b.csvwrite(P/'threshold_driver_coefficients.csv',rows);b.dump(P/'ui_resource_monthly.json',dict(result_mode='P09_PROPOSED_FLEET_CALENDAR_SIDECAR_NOT_P06_FINANCIAL_PROJECTION',resource_group='Same per delivery for all main alternatives and KEEP',rows=res))
if __name__=='__main__':main()
