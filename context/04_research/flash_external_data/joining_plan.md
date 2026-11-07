# План объединения внешних данных для анализа маршрутной сети Red Wings (Кейс №5)
> Архив Flash: содержит выявленные ошибки. Для расчётов использовать [проверки Terra](../../07_verification/README.md). Исходные утверждения ниже сохранены для аудита.
**Дата фиксации:** 7 ноября 2026 г.
**Целевая папка:** `context/04_research/flash_external_data/`
**Связанные файлы:** [`sources.csv`](sources.csv), [`report.md`](report.md)

---

## 1. Концептуальная модель данных (Core Data Architecture)

Для решения задач кейса №5 (формирование лонглиста городов для хаба, выбор между гипотезой хаба и гипотезой прямых межрегиональных рейсов P2P, моделирование пассажиропотока 8–12 маршрутов) внешние данные структурируются вокруг четырех базовых сущностей:

```
 [Аэропорты (Airports)] ────── (1:N) ────── [ВПП (Runways)]
         │
         │ (N:1 via IATA / Coords)
         ▼
 [Города и Агломерации (Cities & Agglomerations)]
         │
         │ (N:M декартово произведение пар А -> Б)
         ▼
 [Маршрутные сегменты (Route Segments O-D)]
         │
         ├─── (Join via Coords / Distance) ─── [Наземные альтернативы (OSRM / РЖД)]
         ├─── (Join via Route O-D) ──────────── [Субсидии (ПП №1242 / ПП №215)]
         ├─── (Join via Airport ICAO) ───────── [Тарифы и ограничения (AIP / ФАС / NOTAM)]
         └─── (Join via Coords / IATA) ──────── [Климат и сезонность (Open-Meteo)]
```

---

## 2. Сущности, атрибуты и ключи объединения (Keys & Schemas)

### Таблица 1. Справочник аэропортов (`dim_airports`)
Формируется на основе [`OurAirports`](https://davidmegginson.github.io/ourairports-data/airports.csv) (SRC-11) и Реестра аэродромов Росавиации (SRC-10).

| Поле | Тип | Описание | Первичный / Внешний ключ |
| :--- | :--- | :--- | :--- |
| `airport_id` | INT | Внутренний ID OurAirports | PK |
| `icao_code` | VARCHAR(4) | 4-буквенный код ICAO (например, `USSS`, `UNNT`, `UWUU`) | UK / Join Key |
| `iata_code` | VARCHAR(3) | 3-буквенный код IATA (например, `SVX`, `OVB`, `UFA`) | UK / Core Business Key |
| `airport_name_ru` | VARCHAR(100) | Официальное наименование на русском (Кольцово, Толмачево) | Match key к Росавиации |
| `latitude_deg` | DECIMAL(9,6) | Географическая широта WGS84 | Coords key |
| `longitude_deg` | DECIMAL(9,6) | Географическая долгота WGS84 | Coords key |
| `elevation_ft` | INT | Высота аэродрома над уровнем моря (футы) | Operational check |
| `iso_region` | VARCHAR(10) | Код региона ISO (например, `RU-SVE`, `RU-NVS`, `RU-BA`) | FK к Росстату / ЕМИСС |
| `municipality` | VARCHAR(100) | Город привязки | Match key к БДМО |
| `scheduled_service` | BOOLEAN | Признак наличия регулярного коммерческого сообщения | Filter flag |
| `airfield_class` | VARCHAR(5) | Класс аэродрома по Росавиации (А, Б, В, Г) | Infrastructure flag |

### Таблица 2. Характеристики ВПП (`dim_runways`)
Формируется на основе [`OurAirports runways.csv`](https://davidmegginson.github.io/ourairports-data/runways.csv) (SRC-12).

| Поле | Тип | Описание | Связь |
| :--- | :--- | :--- | :--- |
| `runway_id` | INT | ID полосы OurAirports | PK |
| `airport_ident` | VARCHAR(4) | Код ICAO аэропорта привязки | FK -> `dim_airports.icao_code` |
| `length_m` | INT | Длина ВПП в метрах (рассчитывается: `length_ft * 0.3048`) | Operational constraint |
| `width_m` | INT | Ширина ВПП в метрах | Operational constraint |
| `surface_type` | VARCHAR(20) | Тип покрытия (ASP = асфальт, CON = бетон) | Твердое покрытие (обязательно для SSJ) |
| `is_lighted` | BOOLEAN | Наличие светосигнального оборудования (ночные рейсы) | Schedule constraint |
| `is_closed` | BOOLEAN | Признак закрытия ВПП | Filter flag |

> **Критическое правило валидации флота (SSJ-100 / Ту-214):**
> Для регулярной эксплуатации полностью загруженного Superjet 100 (MTOW 45.88 т для SSJ-100-95B и 49.45 т для SSJ-100-95LR) требуется полоса с твердым покрытием длиной не менее **1 800–2 050 м**. Для Ту-214 (MTOW 110.75 т) — не менее **2 500 м**. Полосы с длиной менее 1 800 м или грунтовым покрытием исключаются из числа кандидатов для базы и магистральных спиц.

---

### Таблица 3. Социально-экономический профиль городов и агломераций (`dim_cities_agglomerations`)
Формируется объединением БДМО Росстата (SRC-01), Бюллетеня населения (SRC-02), данных Минэкономразвития РФ (SRC-03), ЕМИСС по доходам (SRC-04, SRC-05) и докладов ИЭГ (SRC-06).

| Поле | Тип | Описание | Источник |
| :--- | :--- | :--- | :--- |
| `city_id` | INT | Внутренний ID города | PK |
| `city_name_ru` | VARCHAR(100) | Наименование города (Екатеринбург, Уфа, Самара) | Core Key |
| `oktmo_code` | VARCHAR(11) | Код ОКТМО городского округа | Росстат БДМО |
| `region_iso` | VARCHAR(10) | Код субъекта РФ (ISO 3166-2:RU) | Росстат / ЕМИСС |
| `pop_city_core` | INT | Численность населения городского округа (на 1 янв.) | Росстат (SRC-01/02) |
| `agglomeration_name`| VARCHAR(100) | Наименование агломерации по Стратегии РФ (SRC-03) | Минэкономразвития |
| `pop_agglomeration` | INT | Совокупное население агломерации (ядро + спутники) | ИЭГ (SRC-06) / Расчет |
| `average_wage_rub` | DECIMAL(10,2)| Среднемесячная начисленная заработная плата в МО | ЕМИСС 58560 (SRC-04) |
| `grp_per_capita_rub`| DECIMAL(12,2)| ВРП субъекта на душу населения | ЕМИСС 59448 (SRC-05) |
| `gup_billion_rub` | DECIMAL(10,2)| Валовой городской продукт агломерации | ИЭГ (SRC-06) |
| `tourist_arrivals` | INT | Размещенные лица в КСР региона за год | ЕМИСС 43085 (SRC-07) |
| `mining_employees` | INT | Занятые в добыче полезных ископаемых (сырьевой спрос) | ЕМИСС 57257 (SRC-27) |

---

### Таблица 4. Маршрутные пары и мультимодальные альтернативы (`fct_route_segments`)
Строится для каждой исследуемой пары аэропортов (Origin -> Destination).

| Поле | Тип | Описание | Формула / Источник |
| :--- | :--- | :--- | :--- |
| `route_id` | VARCHAR(7) | Составной ключ маршрута: `{origin_iata}_{dest_iata}` | PK |
| `origin_iata` | VARCHAR(3) | Код IATA аэропорта отправления | FK -> `dim_airports.iata_code` |
| `dest_iata` | VARCHAR(3) | Код IATA аэропорта назначения | FK -> `dim_airports.iata_code` |
| `great_circle_km` | DECIMAL(8,2) | Ортодромное расстояние полета (км) | Haversine(`coords_origin`, `coords_dest`) |
| `flight_time_est_min`| INT | Расчетное полетное время на SSJ-100 (мин) | `(great_circle_km / 800) * 60 + 35` (руление/набор) |
| `road_distance_km` | DECIMAL(8,2) | Расстояние по автодорогам | OSRM API (SRC-24) |
| `driving_time_hours`| DECIMAL(5,2) | Время движения на автомобиле/автобусе (ч) | OSRM API (SRC-24) |
| `train_fastest_hours`| DECIMAL(5,2)| Время хода быстрейшего поезда (ч) | Яндекс Расписания API (SRC-22) |
| `train_daily_freq` | INT | Число ежедневных ж/д рейсов | Яндекс Расписания API (SRC-22) |
| `is_subsidized_1242`| BOOLEAN | Включен ли маршрут в Перечень субсидий № 1242 | Росавиация (SRC-14) |
| `subsidy_co_fin_pct`| INT | Доля софинансирования субъекта РФ (%) | Росавиация (SRC-14) |
| `fare_yield_benchmark`| DECIMAL(8,2)| Базовая цена за 1000 км пути (руб.) | ЕМИСС 31448 (SRC-09) |
| `ground_cannibalization`| VARCHAR(10)| Уровень конкуренции с наземным транспортом | HIGH / MODERATE / LOW |

---

## 3. Правила классификации наземной конкуренции (Ground Cannibalization Rules)

При анализе прямых пар городов критически важно отфильтровать маршруты, где авиация заведомо проигрывает наземному транспорту:

1. **`HIGH_CANNIBALIZATION` (Авиация нежизнеспособна без экстраординарных субсидий):**
   * Критерий: Ж/д время хода $\le 4.5$ часов ИЛИ автодистанция $\le 350$ км.
   * *Примеры:* Москва — Нижний Новгород («Ласточка» 3 ч 40 мин vs перелет 1 ч 15 мин + 3 ч в аэропортах); Екатеринбург — Челябинск (автобус/авто 2.5 ч, поезд 3 ч 50 мин); Екатеринбург — Тюмень (поезд 4 ч).
2. **`MODERATE_CANNIBALIZATION` (Нишевая конкуренция, бизнес-пассажиры и трансфер):**
   * Критерий: Ж/д время хода от 4.5 до 10 часов ИЛИ автодистанция 350–700 км.
   * *Примеры:* Екатеринбург — Пермь (поезд 5 ч); Екатеринбург — Уфа (авто 8 ч через перевалы Уральских гор, поезд 11–13 ч, но самолет летит всего 1 ч 15 мин — прямая экономия свыше 7 часов!).
3. **`LOW_CANNIBALIZATION` (Безоговорочное преимущество авиации):**
   * Критерий: Ж/д время $> 12$ часов ИЛИ автодистанция $> 700$ км, либо отсутствие круглогодичного наземного сообщения (Север, Сибирь, ДФО).
   * *Примеры:* Екатеринбург — Новый Уренгой (поезд 34 ч vs самолет 2 ч 10 мин); Самара — Новый Уренгой; Уфа — Ноябрьск; Екатеринбург — Сочи.

---

## 4. Пайплайн склейки данных (Step-by-Step Join Pipeline)

```python
# Псевдокод ETL-пайплайна объединения внешних источников

import pandas as pd
import numpy as np

# ШАГ 1: Загрузка инфраструктуры аэродромов и фильтрация флота
airports = pd.read_csv("samples/sample_airports_ru.csv")
runways = pd.read_csv("samples/sample_runways_ru.csv")

# Расчет эффективной длины полосы в метрах
runways["length_m"] = runways["length_ft"] * 0.3048
valid_runways = runways[(runways["length_m"] >= 1800) & (runways["surface"].isin(["ASP", "CON"]))]
airports_fleet_ready = airports[airports["ident"].isin(valid_runways["airport_ident"].unique())]

# ШАГ 2: Сопоставление городов с демографией и доходами
cities_demo = pd.read_csv("cities_rosstat_income.csv")  # БДМО + ЕМИСС
hub_candidates = airports_fleet_ready.merge(
    cities_demo,
    left_on="municipality",
    right_on="city_name_ru",
    how="inner"
)

# ШАГ 3: Генерация пар маршрутов (Декартово произведение O-D)
# Исключаем диагональ (рейсы в самого себя)
routes = hub_candidates.merge(airports_fleet_ready, how="cross", suffixes=("_orig", "_dest"))
routes = routes[routes["iata_code_orig"] != routes["iata_code_dest"]]

# ШАГ 4: Расчет ортодромии (Haversine Distance)
def haversine_np(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6367 * c
    return km

routes["dist_km"] = haversine_np(
    routes["longitude_deg_orig"], routes["latitude_deg_orig"],
    routes["longitude_deg_dest"], routes["latitude_deg_dest"]
)

# Фильтр по дальности полета SSJ-100-95B/LR (макс 3000 / 4500 км) и минимум 350 км
routes = routes[(routes["dist_km"] >= 350) & (routes["dist_km"] <= 3000)]

# ШАГ 5: Обогащение субсидиями (ПП № 1242)
subsidies_1242 = pd.read_csv("samples/sample_subsidized_1242_schema.csv")
routes = routes.merge(
    subsidies_1242[["origin_iata", "dest_iata", "fed_subsidy_share_pct", "reg_co_financing_share_pct"]],
    left_on=["iata_code_orig", "iata_code_dest"],
    right_on=["origin_iata", "dest_iata"],
    how="left"
)
routes["is_subsidized"] = routes["fed_subsidy_share_pct"].notna()

# ШАГ 6: Обогащение мультимодальными альтернативами (OSRM / РЖД)
# Если train_hours < 4.5 -> ground_risk = HIGH
```

---

## 5. Методология проксирования ненаблюдаемого спроса (OD Demand Proxying)

Поскольку в открытом доступе **отсутствуют коммерческие матрицы бронирований Origin-Destination (MIDT/Sabre/Сирена)**, для кейса №5 применяется гравитационная модель с поправками на субсидии и вахтовую активность:

$$\text{Пассажиропоток}_{ij} = G \cdot \frac{(\text{Потенциал}_i \cdot \text{Потенциал}_j)^\alpha}{(\text{Дистанция}_{ij})^\beta} \cdot K_{\text{наземный}} \cdot K_{\text{субсидия}} \cdot K_{\text{вахта}}$$

Где:
1. **$\text{Потенциал}_i$**: Функция от населения агломерации ($Pop_i$) и средней заработной платы ($Wage_i$):
   $$\text{Потенциал}_i = \sqrt{Pop_i \cdot \frac{Wage_i}{\overline{Wage}_{РФ}}}$$
2. **$K_{\text{наземный}}$**: Штраф за наличие скоростной ж/д или автодороги ($0.1$ при $T_{train} \le 4$ ч; $0.5$ при $T_{train} \le 8$ ч; $1.0$ при $T_{train} > 12$ ч).
3. **$K_{\text{субсидия}}$**: Мультипликатор доступности тарифа по ПП № 1242 ($1.35–1.50$, стимулирующий скрытый спрос снижением чека на 30–50%).
4. **$K_{\text{вахта}}$**: Коэффициент вахтового спроса для сырьевых аэропортов Севера ($1.4–1.8$ для пар типа Уфа/Самара/Екатеринбург <-> Новый Уренгой/Нижневартовск/Норильск/Сургут).
