#!/usr/bin/env python3
"""Append the final-fetch colleague updates without overwriting the old map."""
from pathlib import Path
import csv
ROOT=Path(__file__).resolve().parents[1]
def main():
    with (ROOT/'contributions/existing_map/existing_hypotheses.csv').open() as f:rows=list(csv.DictReader(f))
    fields=list(rows[0]);sha='359ad3cfb4fdcc74e14c802fc6256e65c1106dbb'
    additions=[
    ('T17_RANGE','context/17_aircraft_route_review/README.md','Матрица маршрут × модификация вместо единого 2300 км/+20%','Фактические массы, трасса, тип/модификация и OFP; dispatch UNKNOWN','Универсальный фильтр снят в d437041; старый stage16 сохраняется только исторически. Наши геометрические screens тоже не допускают/не отвергают маршрут.','Реальная полезная нагрузка, модификация и доступность конкретного борта','EC_H10;T16_DIRECT_D8'),
    ('T18_UNIT','context/18_unit_economics_audit/README.md','Аудит дохода/затрат, условная частотная функция и тарифные полосы','Раздельные статьи денег; диапазоны OD/частоты не калиброваны','Меньший убыток не основание лётного пилота; изменение частоты структурно зависит от заданной capture function. Полная модель здесь не перезапускалась.','Полученный net fare, demand response и договорная стоимость','T16_PILOT_SVX_MRV;T16_STAGE_GATE'),
    ('T18_SCALE','context/18_unit_economics_audit/evidence/observed_pair_segments.csv','Сегментные 2025 SVX–MRV/SVX–AER как масштаб условного теста','Годовой сегментный рынок × неизвестная endpoint доля × неизвестная сезонность','211k/785k и январские16k переданы коллегой с первичными URL; здесь первоисточники заново не проверены. Это не observed endpoint OD; положительные сценарии до fixed не допуск.','Направления/сезон/конечный OD и paid share нового вылета','T16_PILOT_SVX_MRV;EC_H05'),
    ('T18_NETCOST','context/18_unit_economics_audit/README.md','Эффективная цена топлива и согласование состава net revenue','Чистый дополнительный эффект вычетов/акциза, договор и момент cash; исключение повторных сборов','Никакой налоговый эффект RW не подтверждён. Zero credit и условная чувствительность отдельно; не вычитать валовой вычет без начисления.','Реальная чистая цена/платёжные сроки/включённые услуги','EC_H07;T16_STAGE_GATE')]
    for id,path,claim,mechanism,interpretation,test,related in additions:
        r={k:'' for k in fields};r.update(id=id,original_author='mput, colleague team-update branch; Git contribution, sole intellectual authorship not established',source_path=path,source_sha=sha,source_locator='README sections / CSV full table',original_id=id,original_claim=claim,mechanism=mechanism,geography='Russia; specific pairs in source',evidence_status='COLLEAGUE_UPDATE_READ_NOT_RERUN',corrected_current_interpretation=interpretation,unresolved_test=test,record_type='late_update_method_or_scenario',related_existing_ids=related,value_status='SCENARIO',upstream_provenance='inputs/late_update_manifest.json',source_url=f'https://github.com/Mput13/case_championship/blob/{sha}/{path}',admission_status='SCOPE_LIMITED');rows.append(r)
    with (ROOT/'existing_hypotheses.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    print(f'existing map: {len(rows)} records including 4 late-update records')
if __name__=='__main__':main()
