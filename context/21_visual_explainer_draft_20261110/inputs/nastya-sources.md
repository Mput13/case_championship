# Сырые данные: откуда, когда, на каких условиях

Скачано 09.11.2026. Повторить: `py -3.13 src/fetch_static.py` и `py -3.13 src/fetch_kover.py --since 2024-11-01`.

| Файл | В git | Откуда | Условия | Что внутри |
|---|---|---|---|---|
| `favt_posts.csv` | да | [t.me/s/favt_info](https://t.me/s/favt_info), публичный канал Росавиации | публичные сообщения госоргана | 8 306 постов с 01.11.2024 по 09.11.2026: id, время UTC и МСК, текст. Хранится в git, потому что выгрузка идёт ~25 минут, а старые посты могут исчезнуть |
| `ourairports_airports.csv` | нет, скачивается | https://davidmegginson.github.io/ourairports-data/airports.csv | Public Domain ([условия](https://ourairports.com/data/)) | аэропорты мира: коды IATA/ICAO, координаты, тип, регулярные рейсы |
| `ourairports_runways.csv` | нет, скачивается | https://davidmegginson.github.io/ourairports-data/runways.csv | Public Domain | полосы: длина в футах, покрытие |
| `tochno_intercity/` и `tochno_intercity_csv.zip` | нет, скачивается | [«Если быть точным»: транспортная связность](https://tochno.st/datasets/intercity_connectivity), версия 29.06.2026, [архив CSV](https://storage.yandexcloud.net/tochno-st-catalog/Geo/data_intercity_connectivity_162_v20260629/data_intercity_connectivity_162_v20260629_csv.zip) | CC BY 4.0 | 180 городов, все пары, авто / поезд / самолёт: км и часы; население по ВПН-2021; прямые рейсы июнь–декабрь 2026 (Aviastats) и субсидируемые маршруты Росавиации. Время по средней скорости, погрешность около 11% |
| `tochno_intercity_description.pdf` | нет, скачивается | там же, [описание набора](https://storage.yandexcloud.net/tochno-st-catalog/Geo/data_intercity_connectivity_162_v20260629/description_intercity_connectivity_162_v20260629.pdf) | CC BY 4.0 | методика и поля |

## Проверенные, но не скачанные источники

| Источник | Почему не скачан | Что делать |
|---|---|---|
| [Росстат: население по муниципальным образованиям](https://rosstat.gov.ru/compendium/document/13282), файл `BUL_MO_2024.xlsx` (на 01.01.2024) | сайт не отдаёт файлы скриптам | скачать вручную в браузере и положить сюда |
| [Росавиация, открытые данные: пассажиры через аэропорты](https://favt.gov.ru/opendata/7714549744-statperevaeroportpas/) | последние данные — декабрь 2020 | годится только для истории (2019–2020) |
| [Росавиация, перечень международных аэропортов](https://www.favt.gov.ru/dejatelnost-ajeroporty-i-ajerodromy-mezhdunarodnye-ajeroporty) на 25.08.2026 | прочитан на странице | все 20 городов лонглиста в перечне |
| [API Яндекс Расписаний](https://yandex.ru/dev/rasp/raspapi/) | нужен ключ | доля перевозчиков по расписанию аэропорта |
| [Aviastats](https://aviastats.ru/) (Aviasales) | платный сервис для компаний, данные по запросу | часть данных уже есть в наборе «Точно» |
| [Meduza, 03.07.2026](https://meduza.io/feature/2026/07/03/nalety-ukrainskih-dronov-paralizuyut-rabotu-rossiyskih-aeroportov) | статья, датасета нет | эталон для проверки дней «Ковра» |
| [Ютэйр: время стыковки по аэропортам](https://www.utair.ru/support/4/obshie_pravila_perevozki_bagazha/transfer_bagazha) | прочитана страница | цифры перенесены в `data/manual/longlist_manual.csv` |
