#!/usr/bin/env python3
"""Offline role-level signal cards/coverage; retain source-specific detail."""
import csv
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(name, records, fields):
    with (ROOT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({k: r.get(k) for k in fields} for r in records)


def run():
    fields = ["signal_id", "module", "source_ids", "source_status", "usability", "value_status",
              "traveller", "origin_destination", "purpose", "causal_path", "competing_explanation",
              "unit", "date_geography", "join_keys", "systematic_missingness", "license",
              "refresh_cost", "negative_control_or_ablation", "allowed_use", "not_allowed_use", "detail_path"]
    cards = []
    for r in read("modules/business/signal_cards.csv"):
        cards.append(dict(signal_id=r["signal_id"], module="business", source_ids=r["dataset_id"],
                          source_status="RESTRICTED_USE" if r["signal_id"] == "B03" else "PARSED",
                          usability=r["status"], value_status="OBSERVED",
                          traveller=r["traveller"], origin_destination=r["potential_origin_destination"],
                          purpose=r["purpose"], causal_path=r["causal_path"], competing_explanation=r["competing_explanation"],
                          unit=r["measurement_unit"], date_geography=r["date_and_geography"], join_keys=r["join_keys"],
                          systematic_missingness=r["systematic_missingness"], license=r["license"], refresh_cost=r["refresh_cost"],
                          negative_control_or_ablation=r["negative_control_or_ablation"], allowed_use=r["allowed_use"],
                          not_allowed_use=r["not_allowed_use"], detail_path="modules/business/signal_cards.csv"))
    for r in read("modules/tourism/signal_cards.csv"):
        cards.append(dict(signal_id=r["signal_id"], module="tourism", source_ids=r["source_ids"],
                          source_status="PARSED", usability=r["status"], value_status="DERIVED",
                          traveller=r["traveller"], origin_destination=r["origin"] + "; " + r["destination"],
                          purpose=r["purpose"], causal_path=r["causal_path"], competing_explanation=r["competing_explanation"],
                          unit=r["unit"], date_geography=r["date"] + "; " + r["geographic_coverage"], join_keys=r["join_keys"],
                          systematic_missingness=r["systematic_missingness"], license=r["license"], refresh_cost=r["update_cost"],
                          negative_control_or_ablation=r["negative_control"] + "; " + r["ablation"],
                          allowed_use="Форма месячной сезонности внутри одного ряда/охвата; годовой масштаб OD задаётся отдельно",
                          not_allowed_use=r["limits"], detail_path="modules/tourism/signal_cards.csv"))
    cards += [
        dict(signal_id="W01", module="weather", source_ids="noaa_lite_*_2024;ordinary_airports_reused_core",
             source_status="PARSED", usability="USABLE_HISTORICAL_OPERATIONAL_COVARIATE", value_status="DERIVED",
             traveller="Все пассажиры программы; погодный фактор относится к выполнению рейсов",
             origin_destination="Станция → аэропорт по точному ICAO; маршруты не измерены", purpose="Проверка сезонного резерва и устойчивости расписания",
             causal_path="Погодные условия могут менять потребность в резерве; проверка требует типа ВС, минимума аэродрома и факта задержки",
             competing_explanation="Редкая частота наблюдений; оборудование станции; тип ВС; наземная инфраструктура; непогодные задержки",
             unit="station-hour; degC; m/s; месячные агрегаты DERIVED",
             date_geography="2024; 84 станции RS в селекторе, 83 файла; 74 точных совпадения аэропортов",
             join_keys="station_id;UTC month;ICAO → OurAirports airport_id; versioned snapshots",
             systematic_missingness="1 HTTP404; 4 пустых station-month; 9 ICAO unmatched; 9 станций <350 наблюдённых дней; нет QC/видимости/порывов",
             license="UNKNOWN: точный текст лицензии NOAA не получен; OurAirports Public Domain по data page",
             refresh_cost="83 gzip ~4.2 MB; архив 2024 фиксирован; новый год требует нового источника, ISD после 2025-08-24 не обновляется",
             negative_control_or_ablation="С тем же расписанием убрать погодные признаки; проверять на фактических задержках другого года; не подгонять пороги под победителя",
             allowed_use="Исторический календарь наблюдений и контроль покрытия; исследовательские temp<-20/wind>=12m/s только с явной маркировкой",
             not_allowed_use="Вероятность отмены; текущая погода; лимиты SSJ/Tu; холодные часы не равны закрытым часам",
             detail_path="normalized/join_validation.json;modules/weather_review/review.md"),
        dict(signal_id="R01", module="telegram_correction", source_ids="front71b493d favt_posts;favt_main_repair:*",
             source_status="RESTRICTED_USE", usability="MAIN_TEXT_REPAIR_WITH_COVERAGE_GATE", value_status="OBSERVED",
             traveller="Все пассажиры затронутых аэропортов", origin_destination="Аэропорты, прямо названные в основном тексте; направления не измерены",
             purpose="Проверка ограничений и политики резерва", causal_path="Действующее ограничение может нарушать программу; нужны фактические границы и совместимость дат",
             competing_explanation="Reply цитирует прежнее действие; редактирование публикации; неоднозначное действие по нескольким аэропортам; неполная лента",
             unit="Основной текст публикации; отдельные START/LIFT/CONDITIONAL assertions; publication elapsed не эксплуатационные часы",
             date_geography="Исторические публикации 2024-11/2026-11; текущий public HTML snapshot 2026-11-09",
             join_keys="post_id;source_page_sha256;airport_id only after action-clause review",
             systematic_missingness="Original PARSER_CONTAMINATION; текущая полнота в modules/telegram_correction/coverage.json; отсутствующие тела UNKNOWN",
             license="UNKNOWN; открытые сообщения издателя с атрибуцией", refresh_cost="Ремонт кешированной истории; incremental feed нельзя повторять как новый общий сборщик",
             negative_control_or_ablation="Сопоставить 4687/6503 main vs reply; mixed4685 не размечать одним действием; убрать модуль при незавершённой проверке",
             allowed_use="Проверяемые тексты и подбор событий для проверки; интервалы только с неизвестными границами и происхождением",
             not_allowed_use="Старый текст как событие; гарантированный lower bound; полная история закрытий; post count как риск",
             detail_path="parser_contamination.json;independent_parser_reproduction.json;modules/telegram_correction/coverage.json")]
    write("signal_cards.csv", cards, fields)
    cov = []
    def add(dataset, universe, denominator, covered, unit, status, missing, detail):
        cov.append(dict(dataset_id=dataset, universe=universe, denominator=denominator, covered=covered,
                        unit=unit, status=status, missingness=missing, detail_path=detail))
    for r in read("modules/business/coverage.csv"):
        add(r["dataset_id"],r["universe"],r["denominator"],r["covered"],r["unit"],r["status"],r["missingness"],"modules/business/coverage.csv")
    profiles=read("modules/tourism/normalized/primary_seasonality_profiles.csv")
    for dataset in sorted({r["dataset_id"] for r in profiles}):
        year=[r for r in profiles if r["dataset_id"]==dataset and r["year"]=="2025"]
        n=sum(r["complete_12_months"]=="True" for r in year)
        add(dataset,"2025 disjoint regional components",85,n,"complete 12-month profiles","PARSED",
            "Unfilled regions UNKNOWN; parent Tyumen/Arkhangelsk excluded; 2026 partial; source scopes differ",
            "modules/tourism/primary_coverage.csv")
    wc=read("normalized/weather_coverage_2024.csv")
    add("noaa_lite_2024","RS+ICAO stations spanning year in metadata",84,len(wc),"station files","PARSED","USDD404; selection is archive, not all airports","normalized/weather_validation.json")
    add("noaa_lite_2024","downloaded stations × 12 months",len(wc)*12,sum(int(r["months_with_records"]) for r in wc),"months with any records","PARSED","Four empty months retain NULL; a record is not full-day coverage","normalized/weather_monthly_2024.csv")
    add("noaa_lite_2024","downloaded station calendar-day panel",len(wc)*366,sum(int(r["observed_days"]) for r in wc),"days with >=1 record","PARSED","Days with one record are not fully observed days","normalized/weather_coverage_2024.csv")
    add("noaa_lite_2024","downloaded stations",len(wc),sum(int(r["observed_days"])>=350 for r in wc),"stations with >=350 observed days","PARSED","Exploratory coverage filter, not quality certification","normalized/weather_coverage_2024.csv")
    j=json.loads((ROOT/"normalized/join_validation.json").read_text())
    add("weather_airport_join","downloaded stations",j["station_count"],j["station_mapping_statuses"]["EXACT_ICAO_COORD_WITHIN25KM"],"exact ICAO station–airport matches","PARSED","9 unmatched preserved; no nearest-airport imputation; code validity historical review pending","normalized/join_validation.json")
    t=ROOT/"modules/telegram_correction/coverage.json"
    if t.exists():
        d=json.loads(t.read_text())
        add("favt_main_repair","original pinned CSV post IDs",d["original_records"],d["original_ids_recovered_main"],"original IDs with recovered main body","RESTRICTED_USE",d["coverage_status"]+"; current HTML not historical edit archive; no sample extrapolation",str(t.relative_to(ROOT)))
    write("coverage.csv",cov,["dataset_id","universe","denominator","covered","unit","status","missingness","detail_path"])
    rejected=[]
    for r in read("modules/business/rejected_or_unavailable.csv"):
        rejected.append(dict(entry_id=r["entry_id"],source_url=r["url"],source_status=r["status"],candidate=r["candidate"],reason=r["reason"],next_step=r["next_use_or_boundary"]))
    rejected += [
        dict(entry_id="R-ORIGINAL",source_url="https://github.com/Mput13/case_championship/blob/71b493d0051dc3acf2a7619801e5b0eb022bddd3/src/fetch_telegram.py",source_status="RESTRICTED_USE",candidate="Original front event text",reason="PARSER_CONTAMINATION: reply preview selected before main text; old event outputs quarantined",next_step="Exact main/reply parsing, two reproductions, explicit recovery coverage; original bytes remain"),
        dict(entry_id="W-USDD",source_url="https://noaa-isd-pds.s3.amazonaws.com/isd-lite/data/2024/232201-99999-2024.gz",source_status="ACCESS_FAILED",candidate="Salekhard 2024 ISD-Lite",reason="HTTP404 despite metadata coverage",next_step="Keep NULL; independent source needed, no station substitution"),
        dict(entry_id="T-62302",source_url="https://www.fedstat.ru/indicator/62302",source_status="RESTRICTED_USE",candidate="Sanatorium nights metadata",reason="Official methodology says persons despite nights heading; mirror title adds incorrect thousand-person scale",next_step="Keep raw scale1 and conflict; ablation remove62302; no cross-scope ratio"),
        dict(entry_id="T-ANNUAL",source_url="https://www.fedstat.ru/indicator/42102",source_status="PARSED",candidate="Annual historical sanatorium mirrors42102/42103",reason="Annual scope and history not reconciled with operational monthly series",next_step="PARSED_NOT_INTEGRATED; do not splice to increase coverage"),
        dict(entry_id="L-SEARCH",source_url="UNKNOWN",source_status="LEAD",candidate="Search interest / student and migration proxies",reason="No usable route-level public raw acquired in this slice; counts would not identify trips or air mode",next_step="Not a zero feature; obtain aggregate provenance and causal validation before use")]
    write("rejected_or_unavailable.csv",rejected,["entry_id","source_url","source_status","candidate","reason","next_step"])
    print(json.dumps({"signal_cards":len(cards),"coverage_rows":len(cov),"rejected_or_unavailable":len(rejected)}))


if __name__=="__main__":
    run()
