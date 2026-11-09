#!/usr/bin/env python3
"""Assemble tourism handoff and metadata from normalized results; offline."""
import collections
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import urllib.parse
import sys
sys.dont_write_bytecode = True
from normalize_tourism import BASE, MONTH_IDS, write_csv


def read_csv(rel):
    with (BASE/rel).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))


def main():
    coverage=read_csv("primary_coverage.csv")
    profiles=read_csv("normalized/primary_seasonality_profiles.csv")
    reconciliation=read_csv("normalized/primary_mirror_reconciliation.csv")
    # Rebuild registry exactly once after normalize_tourism (which owns mirror entries).
    registry=[x for x in read_csv("source_registry.csv") if not x["source_id"].startswith("fedstat_live_")]
    manifest=json.loads((BASE/"dataset_manifest.json").read_text())
    manifest["datasets"]=[x for x in manifest["datasets"] if not x["dataset_id"].startswith("fedstat_live_")]
    primary=json.loads((BASE/"primary_dataset_manifest.json").read_text())["datasets"]
    manifest["datasets"].extend(primary)
    receipt_index={}
    for filename in ["acquisition_receipts.json","primary_acquisition_receipts.json"]:
        for item in json.loads((BASE/"raw"/filename).read_text())["receipts"]:
            if item.get("path"):receipt_index[item["path"]]=item
    searches={"nights":("ночевок",20),"persons":("Численность лиц размещенных",100),"purposes":("целям поездок",100)}
    for aux in manifest["raw_auxiliary_files"]:
        rel=aux["path"];file=BASE/rel;name=file.name
        receipt=receipt_index.get(rel)
        url=None;timestamp=None;time_basis="UNKNOWN"
        if receipt:
            url=receipt["url"];timestamp=receipt["retrieved_at_utc"];time_basis="HTTP acquisition receipt"
        elif name.startswith("nsedc_search_"):
            slug=name.removeprefix("nsedc_search_").removesuffix(".json")
            query,rows=searches[slug]
            url="https://repository.nsedc.ru/api/3/action/package_search?"+urllib.parse.urlencode({"q":query,"rows":rows})
        elif name=="nsedc_package_31560.json":
            url="https://repository.nsedc.ru/api/3/action/package_show?"+urllib.parse.urlencode({"id":"emiss_31560"})
        elif name=="fedstat_FGrid.js":url="https://www.fedstat.ru/common/js/fgrid/FGrid.js?v=13527C1"
        elif name=="tyumen_headers.txt":url="https://72.rosstat.gov.ru/ofs_tur_obl"
        elif name=="omsk_headers.txt":url="https://55.rosstat.gov.ru/infografika/document/282381"
        elif name=="rosstat_http_headers.txt":url="http://rosstat.gov.ru/statistics/turizm"
        if timestamp is None and url and not name.endswith("headers.txt"):
            timestamp=dt.datetime.fromtimestamp(file.stat().st_mtime,dt.timezone.utc).isoformat()
            time_basis="reconstructed from untouched file save mtime; exact HTTP start not logged"
        aux.update({"source_url":url,"organisation":"Росстат / ЕМИСС" if url and "fedstat.ru" in url else "НЦСЭД" if url and "nsedc.ru" in url else "Росстат" if url else "local research process",
            "retrieved_at_utc":timestamp,"retrieval_time_basis":time_basis,"publication_date":None,
            "grain":"support metadata, source HTML, protocol JS or diagnostic headers; not a measurement table",
            "geographic_coverage":"not independently applicable","temporal_coverage":"not independently applicable",
            "record_count":None,"unit":"metadata or text","license":"UNKNOWN",
            "acquisition_status":"ACCESS_FAILED" if name.endswith("headers.txt") else "ACQUIRED_RAW",
            "limitations":"Support artifact. Receipt files retain only whitelisted headers; no cookies/auth headers. HTML body byte hashes unchanged."})
    for ds in primary:
        indicator=ds["dataset_id"].split("_")[-1]
        registry.append({"source_id":ds["dataset_id"],"source_url":ds["landing_url"],
            "mirror_catalog_url":"","organisation":ds["organisation"],
            "source_title":"Первичная таблица ЕМИСС "+indicator,"acquisition_status":ds["acquisition_status"],
            "retrieved_at_utc":ds["retrieved_at_utc"],"publication_date":"UNKNOWN; publisher_last_update="+str(ds["publisher_last_update_label"]),
            "period":"2022–2026" if indicator in {"62073","62074"} else "2023–2026",
            "grain":ds["grain"],"units":"person" if indicator in {"62073","62074"} else "overnight_stay_count",
            "license":ds["license"],"limitations":ds["limitations"]})
    write_csv("source_registry.csv",registry)
    manifest["normalized_files"]=[{"path":str(p.relative_to(BASE)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
        "size_bytes":p.stat().st_size} for p in sorted((BASE/"normalized").glob("*")) if p.is_file()]
    manifest["collector_files"]=[{"path":str(p.relative_to(BASE)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
        "size_bytes":p.stat().st_size} for p in sorted((BASE/"collectors").glob("*.py"))]
    manifest["reproduce_offline"]=[
        "python3 context/16_agent_research/alternative/modules/tourism/collectors/normalize_tourism.py",
        "python3 context/16_agent_research/alternative/modules/tourism/collectors/normalize_primary.py",
        "python3 context/16_agent_research/alternative/modules/tourism/collectors/finalize_module.py"]
    manifest["source_status_note"]="PARSED includes byte/schema/key checks. Primary/mirror reconciliation is not independent confirmation; no OD or air share validation."
    (BASE/"dataset_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    common={"traveller":"Публичные агрегаты всех размещённых лиц; персональные данные не собирались",
        "origin":"UNKNOWN: регионы проживания не измерены","destination":"Регион или непересекающаяся компонента ОКАТО, не аэропортовая зона",
        "join_keys":"area_id + year + period_end_month + source_snapshot; airport mapping requires versioned area crosswalk",
        "license":"Primary API UNKNOWN; NSED mirror declares Creative Commons Attribution (catalog statement)",
        "update_cost":"4 public read-only table POSTs + 4 passports, ~1.3 MB; standard-library Python; annual mirror 6 small GETs optional",
        "limits":"No observed OD, no air mode, no unique tourists, no automatic new-demand estimate; counts can include repeated accommodation episodes"}
    cards=[]
    for signal,ids,purpose,status,causal,competing,missing,control,ablation in [
      ("T01","62073","Календарь деловых, семейных и туристических ночующих поездок","USABLE_REGIONAL_SEASONALITY",
       "Форма месячного календаря размещения помогает задать/проверить сезонные месяцы предложения, после отдельной калибровки OD и вида транспорта",
       "Рост размещения может отражать локальные поездки, мероприятия, методический досчёт, автомобильный поток или смену предложения размещения",
       "85/85 компонент с полным 2025 годом; в 2026 максимум август; полный круг; методика 2026 изменилась",
       "Оценить способность формы 2023–2024 предсказывать 2025 внутри однородной методики; подтверждённые местные/наземные поездки не должны превращаться в воздушный OD",
       "Сравнить модель с тем же годовым OD и плоской сезонностью против нормированной формы 62073; не менять годовой масштаб"),
      ("T02","62074","Поездки в санаторий и сопровождающие","USABLE_PARTIAL_REGIONAL_SEASONALITY",
       "Неплоский календарь санаторных заездов позволяет проверить сезон/длительность программы; затем нужны происхождение отдыхающих и доступ до санатория",
       "Большая часть заездов может быть местной, оплаченной ведомством или прибывать поездом; кадровые ограничения и закрытие организаций меняют статистику",
       "Без малого бизнеса; 68/85 полных 2025 профилей; пропуски не нули; выборка географически неравномерна",
       "Проверить прирост качества вне выборки на маршрутных данных; места без санаторных целей не должны получать прибавку от признака",
       "Удалить санаторную сезонность при неизменных населении/OD; сравнить с общим профилем размещения только в одинаковом наборе регионов"),
      ("T03","62301;62302","Нагрузка на размещение и длительное санаторное пребывание","USABLE_SAME_SERIES_SEASONALITY_WITH_METADATA_CONFLICT",
       "Ночёвки показывают календарь занятого размещения и длительность относительно заездов; полезны для сезонной частоты после проверки географии поездок",
       "Ночёвки могут расти из-за большей длительности пребывания при неизменном числе поездок; это не рост числа потенциальных авиапассажиров",
       "КСР 85/85 полных 2025 профилей, санатории 68/85; официальный паспорт 62302 описывает лиц ошибочно; raw unit единица, масштаб 1",
       "Сверить ночёвки с заездами и годовой статистикой одного охвата; коэффициент ночёвки/лица не переносить в число поездок",
       "Оценить, добавляют ли ночёвки сигнал сверх 62073/62074; отдельно полностью убрать 62302 из-за дефекта метаданных"),
      ("T04","42102;42103","Годовой масштаб санаторного размещения","PARSED_NOT_INTEGRATED_SCOPE_REVIEW_REQUIRED",
       "Годовые санаторные числа дают альтернативный контроль масштаба, когда отдельно подтверждён полный круг и совместимость лет",
       "Различия с оперативным рядом отражают охват/досчёты, а не изменение спроса; суммы квартального YTD и годового показателя удваивают счёт",
       "Получено 2002/2005–2025; исторические территории и кварталы неоднородны; сохранены отдельно от месячного операционного ряда",
       "Не объединять с оперативным рядом до проверки паспорта, охвата малого бизнеса и годовой методики",
       "Исключить весь годовой модуль до подтверждения определений; месячный календарь остаётся отдельно")]:
        cards.append({"signal_id":signal,"wishlist_ids":"D17;D22;D28","source_ids":ids,"status":status,
            **common,"purpose":purpose,"causal_path":causal,"competing_explanation":competing,
            "unit":"persons or night counts as named; seasonal ratios DERIVED; raw scale preserved",
            "date":"Primary snapshot 2026-11-09; current 2026 rows partial; full-year profiles only through 2025",
            "geographic_coverage":"85 disjoint published area components reference; source-specific missingness in primary_coverage.csv",
            "systematic_missingness":missing,"negative_control":control,"ablation":ablation})
    write_csv("signal_cards.csv",cards)
    rejected=[
      {"item_id":"R01","url":"https://www.rosstat.gov.ru/statistics/turizm","status":"ACCESS_FAILED",
       "exact_error":"web open: (400) Timeout fetching; urllib/curl: CERTIFICATE_VERIFY_FAILED / self signed certificate in certificate chain; diagnostic unverified-TLS GET HTTP 403",
       "consequence":"Official XLSX not acquired; public primary EMISS dataGrid acquired instead; no claim that XLSX does not exist"},
      {"item_id":"R02","url":"https://72.rosstat.gov.ru/ofs_tur_obl","status":"ACCESS_FAILED",
       "exact_error":"curl: (35) LibreSSL SSL_connect: SSL_ERROR_SYSCALL in connection to 72.rosstat.gov.ru:443",
       "consequence":"Regional XLSX not acquired; not zero and not evidence of absent sanatorium demand"},
      {"item_id":"R03","url":"https://55.rosstat.gov.ru/infografika/document/282381","status":"ACCESS_FAILED",
       "exact_error":"curl: (35) LibreSSL SSL_connect: SSL_ERROR_SYSCALL in connection to 55.rosstat.gov.ru:443",
       "consequence":"Regional infographic not acquired"},
      {"item_id":"R04","url":"https://repository.nsedc.ru/dataset/?tags=ночлеги","status":"ACCESS_FAILED",
       "exact_error":"web open: Access Denied: error code 9e4edb5b6b850c41; Anubis v1.25.0",
       "consequence":"Public documented CKAN action API worked without authentication; no browser or bot challenge bypass"},
      {"item_id":"R05","url":"UNKNOWN","status":"LEAD","exact_error":"D28: lawful public repeated hotel price/availability panel not acquired",
       "consequence":"Accommodation activity is available; hotel price/availability panel remains unknown"},
      {"item_id":"R06","url":"UNKNOWN","status":"LEAD","exact_error":"Origin geography of sanatorium visitors not present in acquired datasets",
       "consequence":"SVX→MRV, or any other regional OD, cannot be estimated as observed from these totals"}]
    write_csv("rejected_or_unavailable.csv",rejected)
    # Facts in prose are rendered from the same exported profiles.
    stav=next(x for x in profiles if x["dataset_id"]=="emiss_62074" and x["area_id"]=="OKATO:07000000000" and x["year"]=="2025")
    counts=[]
    for ds in [f"emiss_{i}" for i in MONTH_IDS]:
        rr=[x for x in coverage if x["dataset_id"]==ds and x["year"]=="2025"]
        counts.append(f"| {ds} | {sum(int(x['filled_ytd_months'])>0 for x in rr)} | {sum(int(x['usable_increment_months'])==12 for x in rr)} |")
    equal=sum(int(x["equal_common_values"]) for x in reconciliation)
    added=sum(int(x["primary_only_filled_cells"]) for x in reconciliation)
    findings=f'''# Данные размещения и санаторных поездок

Получены первичные паспорта и таблицы ЕМИСС 62073, 62074, 62301, 62302, а также шесть небольших зеркал НЦСЭД, включая годовые 42102/42103. Сохранены сырые байты и HTTP receipts. Первичная месячная таблица содержит 17 694 числовых ячейки. С зеркалом совпали {equal:,} общих заполненных значений; первичный снимок добавил {added} ячеек. Это сверка одного происхождения, а не независимое подтверждение.

| Ряд | Региональные компоненты с любыми данными 2025, из 85 | Полные месячные профили 2025, из 85 |
|---|---:|---:|
{chr(10).join(counts)}

Панель включает 85 непересекающихся опубликованных территориальных компонент. Для Архангельской и Тюменской областей исключены родительские итоги и оставлены автономные округа и области без них. Это география ЕМИСС; она не определяет аэропортовые зоны тяготения.

Периоды в исходнике — нарастающий январь–месяц. `primary_monthly_increments.csv` содержит разности с типом DERIVED. Они могут отражать пересмотры накопленного ряда. Пропуски и отсутствующие строки дают NULL с причиной, без заполнения нулями. Для сезонных долей нужны все 12 месяцев. В 2026 первичные лица и санаторные ночёвки доходят до августа, КСР-ночёвки до июля; полных годовых профилей нет.

Для локальной проверки: в Ставропольском крае оперативный ряд без малого бизнеса содержит {int(stav['annual_ytd_total']):,} размещённых в санаториях лиц за 2025 год. Доля июнь–август в приращениях YTD — {float(stav['summer_jun_aug_share']):.1%}, декабрь+январь+февраль — {float(stav['winter_dec_jan_feb_share']):.1%}, максимальный месяц — {stav['peak_month']}. Это календарь зарегистрированного размещения, не число приезжих из Свердловской области и не спрос SVX–MRV. Ни доля авиатранспорта, ни происхождение отдыхающих не измерены.

КСР 62073/62301 публикуются по полному кругу. Санатории 62074/62302 исключают малый бизнес. Делить санаторный оперативный числитель на КСР как наблюдённую долю нельзя. С 2026 у общих средств размещения действует другая методика: 2023–2025 и 2026 не склеены в сопоставимый темп роста.

В метаданных 62302 конфликт: официальный заголовок — ночёвки, единица — единица, но текст методики описывает размещённых лиц. Заголовок НЦСЭД дополнительно ошибочно добавляет «тыс. человек». Raw сохранён в масштабе 1; автоматического умножения на 1000 нет. При рискованной интерпретации модуль ночёвок полностью исключается, а календарь лиц остаётся самостоятельным.

Usable: форма региональной сезонности внутри одного ряда и однородного периода, с явным покрытием. Условно: санаторная сезонность только для заполненных территорий. Не usable как наблюдение OD: общий поток размещения, ночёвки и их отношение. Годовые исторические санаторные зеркала получены, но в сезонную модель не интегрированы до проверки их охвата.

Файлы: [первичные наблюдения](normalized/primary_observations.csv.gz), [месячные приращения](normalized/primary_monthly_increments.csv), [сезонные профили](normalized/primary_seasonality_profiles.csv), [покрытие](primary_coverage.csv), [извлечённые первичные методики](normalized/passport_extract.csv), [сверка зеркала](normalized/primary_mirror_reconciliation.csv), [манифест](dataset_manifest.json).
'''
    (BASE/"findings.md").write_text(findings,encoding="utf-8")
    (BASE/"integration_plan.md").write_text('''# Объединение

1. Источник наблюдений: `normalized/primary_observations.csv.gz`; резервный срез НЦСЭД — `normalized/observations_long.csv.gz`. Не складывать снимки одного происхождения. Идентификатор строки включает dataset, snapshot, area, year, month.
2. География: `normalized/areas.csv`, `area_id=OKATO:<11-digit code>`. Поле `in_disjoint_reference_panel` исключает родительские итоги, перекрывающие автономные округа. Сопоставление с аэропортом требует отдельной версионной airport→area связи. По одному названию города ничего не соединять.
3. Присоединять к candidate destination area×month как региональную характеристику календаря. Признак не распределяет региональные числа между аэропортами. MRV/STW и AER/KRR нельзя каждому присвоить весь региональный поток как OD.
4. Для полного года использовать `primary_seasonality_profiles.csv` только при `complete_12_months=True`. В месячной таблице `ytd_value` OBSERVED, `monthly_increment` DERIVED; NULL и `missing_reason` сохранять.
5. Сначала сравнить неизменный годовой OD с плоской сезонностью и с внешним календарём размещения. Только после проверки вне обучающего периода решать, улучшает ли сигнал модель. Масштаб OD, доля авиатранспорта и доля конкретной пары остаются отдельными неизвестными параметрами.
6. Пропуски санаторных рядов систематичны. Coverage не преобразуется в привлекательность. Не переносить наблюдённое отсутствие или пропуск в одной области на остальные.
7. 2026 — методический разрыв для общих средств размещения. Сравнения роста через границу методики требуют отдельного подтверждения. Снимок, скачанный в ноябре 2026, не доказывает доступность значения в прошлом.

Все преобразования используют стандартную библиотеку Python. Сначала `normalize_tourism.py`, затем `normalize_primary.py`, затем `finalize_module.py`. Онлайн: `collect_tourism.py --fetch --fetch-primary` выполняет публичные GET/HEAD и read-only dataGrid POST; сохранённые тела запросов находятся в receipts.
''',encoding="utf-8")
    stamp=dt.datetime.now(dt.timezone.utc).isoformat()
    (BASE/"progress.md").write_text(f'''# Модуль туризма

Срез {stamp}. Модуль готов к проверке ведущим, не считается проверенным автоматически.

Получены шесть gzip-зеркал ЕМИСС и четыре первичных месячных dataGrid JSON с паспортами. Проверены SHA, уникальность ключей, точное соответствие названий регионов и числовое совпадение зеркала с первичным срезом; первичный источник добавил 258 значений. Нормализованы 17 694 первичных наблюдения, 18 360 месячных строк с явными NULL, 85 территориальных компонент.

Сохранены `dataset_manifest.json`, `source_registry.csv`, `signal_cards.csv`, `coverage.csv`, `primary_coverage.csv`, raw/normalized/collectors, ограничения и план соединения. Исходный Росстат XLSX недоступен; первичные данные ЕМИСС доступны. Данные происхождения отдыхающих и воздушного OD не получены. Годовые исторические зеркала ещё не интегрированы по охвату. Финальная интерпретация и независимая проверка ведущим остаются за родителем.
''',encoding="utf-8")
    print("handoff assembled",len(manifest["datasets"]),"datasets",len(cards),"signal cards")


if __name__=="__main__":main()
