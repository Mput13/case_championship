#!/usr/bin/env python3
"""Build the offline expert dossier. The JavaScript formulas come from the registry."""

import json
import re
import sys

sys.dont_write_bytecode = True
from build_xlsx import (DATA_PRIORITIES, METRICS, QUESTION_PRIORITIES, ROOT, W2, case_code,
                        council_scores, load_registry, read_csv)

OUTPUT = ROOT / "redwings_corporate_dossier.html"
SECTIONS = (
    ("verdict", "Вывод и рамка встречи"),
    ("screening-68", "Скрининг организаций"),
    ("barriers-why-not", "Барьеры для отдельной программы"),
    ("routes-fleet-53", "Дальность и потребный парк"),
    ("hubs-9", "Сопоставление узлов"),
    ("events-2027", "Календарь 2027"),
    ("pilots-3", "Экономика пилотов"),
    ("what-if-console", "Что если"),
    ("playbooks-track-b", "Кейсы и термшиты"),
    ("rw-questions", "Вопросы Red Wings"),
)

CSS = """
:root{color-scheme:light;--bg:#f7f9fc;--paper:#fff;--ink:#141b24;--line:#dce3ec;
      --muted:#4f5f72;--accent:#244d77;--warm:#79511c;--cold:#3d678c;--bad:#963c36}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.56 system-ui,-apple-system,sans-serif}
a{color:var(--accent);text-underline-offset:.17em}
:focus-visible{outline:3px solid #3b73aa;outline-offset:3px}
h1,h2,h3,h4{color:#162c45;line-height:1.23;margin:0 0 .65em;letter-spacing:-.018em}
h1{font-size:clamp(2rem,4.2vw,3.45rem);max-width:16ch}
h2{font-size:clamp(1.4rem,2.3vw,2.1rem)}
h3{font-size:1.13rem;margin-top:1.5em}
h4{font-size:1rem;margin:.85em 0 .45em}
p{margin:.55em 0 1em;max-width:86ch}
ul,ol{padding-left:1.5rem}
li+li{margin-top:.35rem}
.wrapper{display:grid;grid-template-columns:224px minmax(0,1fr);gap:30px;
         max-width:1490px;margin:auto;padding:32px 36px 64px}
.sidebar{position:sticky;top:24px;align-self:start;max-height:450px;overflow:auto}
.brand{font-size:.81rem;font-weight:750;letter-spacing:.065em;text-transform:uppercase;color:var(--accent);
       padding:.5rem .65rem 1rem}
#toc{display:grid;gap:3px}
#toc a{display:block;border-left:3px solid transparent;padding:.47rem .67rem;border-radius:0 5px 5px 0;
       text-decoration:none;color:var(--muted);font-size:.88rem}
#toc a[aria-current=true]{border-color:#426e9b;background:#e8eff7;color:var(--accent);font-weight:680}
#nav-toggle{display:none}
section{scroll-margin-top:22px;background:var(--paper);border:1px solid var(--line);
        border-radius:12px;padding:clamp(17px,3vw,36px);margin-bottom:22px;min-width:0}
.eyebrow,.subtle,small{color:var(--muted);font-size:.86rem}
.eyebrow{font-weight:650;margin:0 0 .7rem}
.lead{font-size:1.08rem;line-height:1.6}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(124px,1fr));gap:10px;margin:1.4rem 0}
.kpi{border:1px solid var(--line);padding:14px;border-radius:8px}
.kpi strong{display:block;font-size:1.55rem;line-height:1.1;color:var(--accent);font-variant-numeric:tabular-nums}
.kpi span{font-size:.85rem;color:var(--muted)}
.filters,.actions,.controls{display:flex;flex-wrap:wrap;align-items:end;gap:12px;margin:12px 0}
label{display:grid;gap:4px;color:#283b50;font-weight:600;font-size:.85rem}
.filters label{min-width: min(135px,100%)}
.filters label.search{flex:1;min-width:min(220px,100%)}
input,select,button{font:inherit;color:var(--ink);border:1px solid #b9c8d8;background:white;border-radius:6px;
                    padding:7px 10px;min-height:38px;max-width:100%}
select{max-width:100%;width:100%;text-overflow:ellipsis}
input[type=number]{width:100%;min-width:4.4rem;font-variant-numeric:tabular-nums}
button{font-weight:620;cursor:pointer}
button:hover,select:hover{border-color:#426e9b}
button.primary,button[aria-pressed=true]{background:var(--accent);color:white;border-color:var(--accent)}
button.evidence{min-height:28px;font-weight:620;color:var(--accent);padding:2px 6px;
                font-size:.75rem;background:#edf4fb;margin:2px 2px 2px 0}
.badge{display:inline-block;border-radius:5px;padding:.14rem .44rem;background:#eaf1f8;color:#2b4d70;
       font-size:.75rem;font-weight:680;vertical-align:baseline;max-width:100%;overflow-wrap:anywhere}
.conditional,.warning{background:#fbf0db;color:#725024}
.insufficient-evidence{background:#eef1f5;color:#445363}
.structural-hypothesis{background:#f0ebf7;color:#573e78}
.edit{background:#f9ecda;color:#714d26}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:8px;margin:12px 0}
.table-wrap[tabindex]{scrollbar-gutter:stable}
.table-scroll{max-height:560px}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:.87rem}
th,td{text-align:left;padding:.58rem .66rem;border-bottom:1px solid #e5ebf2;vertical-align:top}
thead th{background:#edf2f8;color:#233a55;font-weight:700;position:sticky;top:0;z-index:1}
tbody th{font-weight:640}
tr:last-child td,tr:last-child th{border-bottom:0}
tbody tr:nth-child(even){background:#f9fbfd}
.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.negative{color:var(--bad)}
.summary-table .text{min-width:15rem}
.org-table td:nth-child(1){min-width:11rem}
.org-table td:nth-child(2) .badge{white-space:nowrap}
.org-table td:nth-child(3){overflow-wrap:anywhere;min-width:7rem}
.org-table td:last-child{min-width:13rem}
details{border-top:1px solid var(--line);margin:12px 0;padding-top:9px}
summary{cursor:pointer;color:var(--accent);font-weight:660}
.card{padding:15px;border:1px solid var(--line);border-radius:8px;margin:12px 0}
.card h3{margin-top:0}
.minihead{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:.3rem 0 .75rem}
.chart-wrap{overflow:auto;border:1px solid var(--line);border-radius:8px;max-height:465px;background:white}
.hubs-chart{max-height:none}
svg{display:block;font:13px system-ui,sans-serif}
.chart-wrap svg{width:100%;min-width:590px;height:auto}
.legend{display:flex;flex-wrap:wrap;gap:7px 16px;margin:.6rem 0;color:var(--muted);font-size:.83rem}
.legend span::before{display:inline-block;content:"";width:11px;height:11px;background:var(--swatch);margin:0 5px -1px 0;border-radius:2px}
.legend .dash::before{height:0;border-top:2px dashed var(--swatch);background:transparent}
.console-inputs td{min-width:5.4rem}
.changed{background:#fff5e4}
.change-note{display:block;color:var(--warm);font-size:.73rem}
[hidden]{display:none!important}
.message{min-height:1.5rem;color:var(--muted);font-size:.85rem}
.message:empty{display:none}
.request{width:100%;min-height:14em;resize:vertical;font:inherit;border:1px solid var(--line);
         border-radius:7px;padding:.9rem;background:#f9fbfd;color:var(--ink)}
dialog{width:min(620px,calc(100% - 28px));border:1px solid var(--line);border-radius:12px;padding:20px 24px;
       color:var(--ink);box-shadow:0 8px 40px #24374f30;overflow-wrap:anywhere}
dialog::backdrop{background:#12273a66}
dialog dl{display:grid;grid-template-columns:8.5rem minmax(0,1fr);gap:.55rem .8rem}
dialog dt{font-weight:650;color:var(--muted)}
dialog dd{margin:0}
dialog form{margin:0 0 .5rem;display:flex;justify-content:end}
@media(max-width:959px){
 .wrapper{display:block;padding:10px 14px 34px}
 .sidebar{top:0;z-index:3;max-height:390px;overflow:auto;margin:-10px -14px 14px;padding:8px 14px;
          background:var(--bg);border-bottom:1px solid var(--line)}
 .brand{display:none}
 #nav-toggle{display:inline-block}
 #toc{display:none;margin-top:7px}
 #toc.open{display:grid}
 section{scroll-margin-top:61px}
}
@media(max-width:620px){
 .org-table,.org-table tbody,.org-table tr,.org-table td{display:block}
 .org-table thead{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
 .org-table tbody tr{padding:.65rem .8rem;border-bottom:1px solid var(--line)}
 .org-table tbody td{padding:.2rem 0;border:0;min-width:0!important}
 .console-inputs td,.console-inputs th{padding:.45rem .38rem}
 .console-inputs td{min-width:4.6rem}
 .console-inputs input[type=number]{min-width:0}
 .econ-table,.econ-table tbody,.econ-table thead{display:block}
 .econ-table tr{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}
 .econ-table thead th:first-child{display:none}
 .econ-table tbody th{grid-column:1 / -1;border:0;padding-bottom:.12rem}
 .econ-table td,.econ-table thead th{padding:.42rem .26rem;text-align:center}
}
@media(max-width:420px){dialog dl{display:block}dialog dd{margin:0 0 .5rem}.filters label{flex:1}}
@media print{.wrapper{display:block;padding:0}.sidebar,.actions,.filters,dialog{display:none}.table-wrap,.chart-wrap{max-height:none}
 section{border:0;padding:0;break-inside:auto}.card{break-inside:avoid}}
"""

HTML_SECTIONS = {
    "verdict": """
<p class="eyebrow">Срез 24 ноября 2026 · встреча 26–27 ноября</p>
<h1>Корпоративный спрос Red Wings</h1>
<p id="headline" class="lead"></p><div class="kpis" id="kpis"></div>
<p>На встрече можно проверить условия блока на ИННОПРОМ, допуски чартера Уфа ↔ Новый
Уренгой и время до площадки Атомтехэнерго через Ульяновск или Самару. По каждой ветке
нужны плательщик, размер группы, окно и доступные места в обоих направлениях.</p>
<p class="subtle">Волна 2 свела 180 направленных возможностей по 30 городским парам.
24 пары с геометрией, 29 со срезом предложения, 10 с внешней блокировкой хотя бы по
одному сценарию. У 104 записей статус Conditional, у 76 — Insufficient-Evidence.
Подтверждённого объёма на окне и доказанного GAP пока нет.</p>
<details><summary>Оценки Консула</summary><div id="council"></div></details>""",
    "screening-68": """
<h2>Скрининг 68 организаций</h2>
<p>Статус относится к юрлицу. Причина статуса и следующий проверяемый факт приведены рядом
с IDs источников. За организацией события и его оплатой могут стоять разные юридические лица.</p>
<div class="filters"><label>Статус<select id="org-status"></select></label>
<label>Сектор<select id="org-sector"></select></label><label>Роль<select id="org-role"></select></label>
<label class="search">Поиск<input type="search" id="org-search" placeholder="Название, ИНН, источник"></label></div>
<p id="org-count" class="subtle" aria-live="polite"></p><div id="org-table"></div>""",
    "barriers-why-not": """
<h2>Барьеры для отдельной программы</h2>
<p>Сфера вывода — плательщик, когорта, окно и продукт. Формальных отказов по критериям K1–K6
в срезе нет. Доступный поезд и ведомственная перевозка обосновывают проверку конкретных
групп и дат. Подтверждённые окна и места для сравнения пока отсутствуют.</p>
<ul>
<li><strong>ТМС и GAP.</strong> ТЗ на оформление билетов показывает канал закупки.
Разрыв предложения требует проверки рейсов, класса, групповой квоты и времени до объекта
на целевые даты. Кейс Газстройпром / СТНГ учитывается один раз по АП086548 и ИНН 7714572888.</li>
<li><strong>Один борт на 150 пассажиров.</strong> SSJ100 100Y вмещает 100 пассажиров и
не имеет отдельного J. Блокировка соседнего кресла уменьшает полезную ёмкость и применима
только при согласии заказчика на евробизнес. Спорную долю J проверяем отдельно.</li>
<li><strong>LED ↔ NUX.</strong> 2 379,56 км по ортодромии превышают консервативный ориентир
SSJ-95B на 24,56 км. Для зимнего окна нужны расчёт массы и багажа, ветер, запасной,
аэродром и доступность экипажа <span class="badge warning">[NEEDS-RW-DATA]</span>.</li>
</ul><div id="barrier-rules"></div><div id="barrier-table"></div>""",
    "routes-fleet-53": """
<h2>Дальность и потребный парк</h2>
<p>53 пары аэропортов ранжированы по кратчайшему расстоянию на сфере. Для блок-времени
ортодромия умножается на 1,10, затем оценивается 0,45 ч плюс маршрутные километры / 760.
Границы дальности помогают отобрать типы к инженерной проверке.</p>
<div class="filters" id="range-filters" role="group" aria-label="Дальность"></div>
<div class="legend" id="range-legend"></div>
<div class="chart-wrap" id="route-chart" tabindex="0" role="region" aria-label="График дальности"></div>
<div id="route-table"></div>
<p class="subtle">Ориентир 2 355 км относится к SSJ-95B. Линия 3 000 км дана как
ориентир масштаба. Для SJ-100 в модели применяется отдельный экран ≤2 450 км по
ортодромии, для Ту-214 — ≤5 000 маршрутных км.
<span class="badge warning">[NEEDS-RW-DATA]</span></p>
<h3>Парк при 0, 1, 3 и 5 подтверждённых программах</h3>
<p id="fleet-note"></p>
<div class="filters"><label>Тип ВС<select id="fleet-aircraft"></select></label>
<label>Продукт<select id="fleet-product"></select></label></div>
<div id="fleet-table"></div>""",
    "hubs-9": """
<h2>Сопоставление девяти узлов</h2>
<p>Перепробег — удлинение пути с пересадкой относительно прямой ортодромии.
В каждом типе недели посчитаны пары при пределах 25% и 35% и подмножество с
наблюдением обоих плеч. Наблюдения разных дат требуют отдельной проверки стыковки,
расписания, мест и времени в обоих направлениях.</p>
<p>В регулярном срезе SVX и TJM дают по 3 и 4 геометрические пары,
с наблюдением обоих плеч — 0 и 0. У SVO три регулярные связные пары.
Ранжирование по объёму пассажиров пока невозможно.</p>
<div class="legend" id="hub-legend"></div><div id="hub-chart"></div><div id="hub-table"></div>""",
    "events-2027": """
<h2>Календарь 2027</h2>
<p>Четыре подтверждённых события, одно предварительное и шесть без установленных дат.
Подтверждение даты относится к мероприятию. Плательщики, квоты и состав делегаций требуют
отдельной сверки.</p><div id="event-table"></div>
<p class="subtle">ПМГФ перенесён на 20–23 апреля 2027. «Армия-2027» исключена из
прогнозного календаря после исключения из правительственного перечня.
<span id="event-sources"></span></p>""",
    "pilots-3": """
<h2>Экономика трёх пилотов и двух кластеров</h2>
<p>Cash TCT — цена с багажом, доплечьями, ночёвками и ожидаемыми прямыми
расходами при сбое. Lost Work Time переводится в стоимость по полной ставке часа
из сценария. Порог цены RW за выкупленное место компенсирует обслуживание и вытеснение.
Для чартера DOC_max ограничивает допустимую стоимость блок-часа при заданной цене и марже.
Оборот считается до округления направлений.</p>
<div id="pilot-cards"></div>""",
    "what-if-console": """
<h2>Что если</h2>
<p>Выберите ветку и компоновку. Размер группы, квота, вытеснение и расходы могут отличаться
по направлениям. Целевая маржа общая для оборота. Данные эксперта сохраняются в JSON
при экспорте.</p>
<div class="filters"><label>Ветка<select id="scenario"></select></label>
<label class="search">Вариант<select id="variant"></select></label></div>
<p id="console-condition"></p><form id="console-controls"></form>
<div class="actions"><button type="button" class="primary" id="export">Экспорт калибровки (JSON)</button>
<button type="button" id="reset">Сбросить к базе</button></div><p class="message" id="console-state" role="status"></p>
<div id="console-results" aria-live="polite"></div>""",
    "playbooks-track-b": """
<h2>Кейсы и термшиты</h2>
<p>13 квалифицированных кейсов, шесть поправок для РФ и пять термшитов.
Стадия в кейсе показывает, что известно об оферте, контракте или выполнении.
Условия переноса на продукт Red Wings — предмет переговоров.</p>
<div id="benchmarks"></div><h3>Поправки для РФ</h3><div id="adaptations"></div>
<h3>Термшиты</h3><div id="term-sheets"></div>""",
    "rw-questions": """
<h2>Вопросы Red Wings на 26–27 ноября</h2>
<div id="questions"></div><h3>Приоритеты запроса данных <span class="badge warning">[NEEDS-RW-DATA]</span></h3>
<div id="data-priorities"></div><h3>Обезличенный запрос заказчикам</h3>
<textarea class="request" id="customer-request" aria-label="Обезличенный запрос заказчикам" readonly></textarea>
<div class="actions"><button type="button" id="copy-request">Скопировать запрос</button></div>
<p class="message" id="request-state" role="status"></p>""",
}

RUNTIME = r"""
const DIRECTIONS = ["outbound", "inbound"];
const ROUND_UP = (x, d) => Math.sign(x) * Math.ceil(Math.abs(x) * 10 ** d - 1e-10) / 10 ** d;
const ROUND_DOWN = (x, d) => Math.sign(x) * Math.floor(Math.abs(x) * 10 ** d + 1e-10) / 10 ** d;
const round = (x, d = 2) => Math.sign(x) * Math.floor(Math.abs(x) * 10 ** d + 0.500000001) / 10 ** d || 0;
const f = {ROUNDUP: ROUND_UP, ROUNDDOWN: ROUND_DOWN, MIN: Math.min, MAX: Math.max,
           IF: (condition, yes, no) => condition ? yes : no};

function rawDirection(mode, inputs) {
  if (!(inputs.pax > 0)) throw new Error("Размер группы должен быть больше нуля.");
  if (mode !== "TICKET" && (!(inputs.net_revenue_pct > 0 && inputs.net_revenue_pct <= 100) ||
      !(inputs.target_margin_pct >= 0 && inputs.target_margin_pct < 100))) {
    throw new Error("Доля чистой выручки должна быть в (0; 100], маржа — в [0; 100).");
  }
  if (mode === "BLOCK" && !(inputs.quota_seats > 0)) throw new Error("Квота должна быть больше нуля.");
  const values = {...inputs};
  return Object.fromEntries(Object.entries(FORMULAS[mode]).map(([key, formula]) => {
    const value = formula(values);
    if (!Number.isFinite(value)) throw new Error("Проверьте входные значения для " + key);
    values[key] = value;
    return [key, value];
  }));
}

function calculateScenario(variant, delta = {}) {
  const input = Object.fromEntries(DIRECTIONS.map(d => [d, {...variant.inputs[d], ...delta[d]}]));
  if (input.outbound.target_margin_pct !== input.inbound.target_margin_pct) {
    throw new Error("Укажите общую целевую маржу на оба направления.");
  }
  const [outbound, inbound] = DIRECTIONS.map(d => rawDirection(variant.mode, input[d]));
  const totals = Object.fromEntries(SUM_OUTPUTS[variant.mode].map(key => [key, outbound[key] + inbound[key]]));
  if (variant.mode === "CHARTER") {
    totals.rw_doc_max_rub_per_block_h = cycleDOC(totals, input.outbound.target_margin_pct);
  }
  const publish = outputs => Object.fromEntries(Object.entries(outputs).map(([key, val]) => [key, round(val)]));
  return {outbound: publish(outbound), inbound: publish(inbound), round_trip: publish(totals)};
}

if (typeof module !== "undefined" && module.exports) module.exports = {calculateScenario};

function setupPage(data) {
  const $ = id => document.getElementById(id);
  const number = (value, digits = 0) => value == null ? "н/п" : new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: digits, maximumFractionDigits: digits
  }).format(value);
  const esc = value => String(value ?? "Неизвестно").replace(/[&<>"']/g, c =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const plain = value => esc(value).replace(/\*\*/g, "").replace(/`/g, "");
  const evidenceProse = value => plain(value.replace(/`EV-[A-Z0-9]+-\d+(?:;EV-[A-Z0-9]+-\d+)*`\.?/g,"").trim());
  const badge = (value, extra = "") => `<span class="badge ${extra}">${esc(value)}</span>`;
  const status = value => badge(value, value.toLowerCase().replaceAll("_","-"));
  const numeric = (value, digits = 0) =>
    `<td class="num${value < 0 ? " negative" : ""}">${number(value,digits)}</td>`;
  const evidence = values => (typeof values === "string" ? values.split(";") : values)
    .filter(id => id && Object.hasOwn(data.evidence, id))
    .map(id => `<button type="button" class="evidence" data-ev="${esc(id)}">${esc(id)}</button>`).join(" ");

  const table = (headers, rows, {scroll = false, label = "Таблица", cls = ""} = {}) =>
    `<div class="table-wrap${scroll ? " table-scroll" : ""}" tabindex="0" role="region" aria-label="${esc(label)}">
     <table class="${cls}"><thead><tr>${headers.map(h => `<th scope="col">${esc(h)}</th>`).join("")}
     </tr></thead><tbody>${rows.map(row => "<tr>" + row.join("") + "</tr>").join("")}</tbody></table></div>`;
  const td = x => `<td>${esc(x)}</td>`;
  const th = x => `<th scope="row">${esc(x)}</th>`;
  const option = (value, title = value) => `<option value="${esc(value)}">${esc(title)}</option>`;
  const svg = (title, height, children) =>
    `<svg viewBox="0 0 760 ${height}" role="img" aria-label="${esc(title)}">${children}</svg>`;
  const svgText = (x, y, t, extra = "") =>
    `<text x="${x}" y="${y}" fill="#223951" ${extra}>${esc(t)}</text>`;

  const dialog = $("evidence-dialog");
  let evidenceTrigger;
  document.addEventListener("click", event => {
    const trigger = event.target.closest("[data-ev]");
    if (!trigger) return;
    const ev = data.evidence[trigger.dataset.ev];
    if (!ev) return;
    evidenceTrigger = trigger;
    $("source-heading").textContent = ev.evidence_id;
    const url = ev.source_url;
    const fields = [
      ["Издатель", esc(ev.issuer || "Не указан")],
      ["Дата документа", esc(ev.document_date || "Не указана")],
      ["Дата проверки", esc(ev.checked_on || "Не указана")],
      ["URL", /^https?:\/\//i.test(url) ?
        `<a target="_blank" rel="noopener noreferrer" href="${esc(url)}">${esc(url)}</a>` : esc(url || "Не указан")],
      ["Локатор", esc(ev.source_locator || "Не указан")],
      ["Утверждение", esc(ev.supported_claim)],
      ["Уровень", esc(ev.evidence_level)],
      ["Ограничение", esc(ev.limitation)],
    ];
    $("source-fields").innerHTML = fields.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
    dialog.showModal();
  });
  dialog.addEventListener("close", () => evidenceTrigger?.focus());

  $("headline").textContent = data.meta.honest_verdict_ru;
  $("kpis").innerHTML = [
    [data.organizations.length, "юрлиц"], [data.city_pairs, "городских пар"],
    [Object.keys(data.evidence).length, "записей доказательств"],
    [data.fleet.fleet_requirements.base_dedicated_aircraft_open_sources, "выделенных ВС · база"],
  ].map(([v, label]) => `<div class="kpi"><strong>${v}</strong><span>${label}</span></div>`).join("");
  $("council").innerHTML = table(["Участник","Раунд 0","Раунд 1","Раунд 2"], data.scores.map(x => x.map(td)));

  const orgFilters = [["org-status", "status"], ["org-sector", "sector"], ["org-role", "scope_role"]];
  for (const [id, field] of orgFilters) {
    $(id).innerHTML = option("", "Все") + [...new Set(data.organizations.map(o => o[field]))].sort()
      .map(value => option(value)).join("");
    $(id).addEventListener("change", showOrganizations);
  }
  $("org-search").addEventListener("input", showOrganizations);
  function showOrganizations() {
    const query = $("org-search").value.trim().toLocaleLowerCase("ru");
    const selected = data.organizations.filter(o => orgFilters.every(([id, key]) => !$(id).value || $(id).value === o[key])
      && [o.legal_name,o.inn,o.evidence_ids].some(value => value.toLocaleLowerCase("ru").includes(query)));
    $("org-count").textContent = `${selected.length} из ${data.organizations.length}`;
    $("org-table").innerHTML = selected.length ? table(["Юрлицо / ИНН", "Статус", "Сектор / роль",
      "Основание, условие пересмотра и источники"], selected.map(o => [
      `<td><strong>${esc(o.legal_name)}</strong><br><small>ИНН ${esc(o.inn)}</small></td>`,
      `<td>${status(o.status)}</td>`, `<td>${esc(o.sector)}<br><small>${esc(o.scope_role)}</small></td>`,
      `<td>${esc(o.decision_reason)}<br><small>${esc(o.decision_changing_fact)}</small>
        <br>${evidence(o.evidence_ids)}</td>`
    ]), {scroll:true, label:"Организации", cls:"org-table"}) : "<p>Организации по этим фильтрам не найдены.</p>";
  }
  showOrganizations();

  $("barrier-rules").innerHTML = "<h3>Критерии K1–K7</h3>" + table(["Код","Условие"],
    Object.entries(data.barriers.rules).map(([key,value]) => [th(key),td(value)]), {label:"Критерии"});
  $("barrier-table").innerHTML = "<h3>Проверенные сочетания группы, окна и продукта</h3>" +
    table(["Сценарий","Наблюдение","Условие решения"], data.barriers.entries.map(row => [
      `<th scope="row">${plain(row.scenario_ru)}</th>`,
      `<td class="text">${evidenceProse(row.observation_ru)}<br>${evidence(row.evidence_ids)}</td>`,
      `<td class="text">${row.decision_condition_ru ? evidenceProse(row.decision_condition_ru) : "Условие в наблюдении."}</td>`
    ]), {scroll:true, label:"Реестр барьеров", cls:"summary-table"});

  const routeBands = [
    {name:"Все 53", match:() => true},
    {name:"≤2 250 км · SSJ-95B", match:x=>x<=2250},
    {name:">2 250–2 450 км · пограничная зона", match:x=>x>2250 && x<=2450},
    {name:">2 450 км · вне экрана SSJ100", match:x=>x>2450},
  ];
  const routeColor = km => km<=2250 ? "#426e9b" : km<=2450 ? "#bd884b" : "#66778d";
  $("range-legend").innerHTML = '<span class="dash" style="--swatch:#a05f39">2 355 км · ориентир SSJ-95B</span>' +
    '<span class="dash" style="--swatch:#6e577e">3 000 км · ориентир шкалы</span>';
  $("range-filters").innerHTML = routeBands.map((item, i) =>
    `<button type="button" data-band="${i}" aria-pressed="${i===0}">${esc(item.name)}</button>`).join("");
  $("range-filters").addEventListener("click", e => {
    const trigger = e.target.closest("[data-band]");
    if (!trigger) return;
    for (const b of $("range-filters").children) b.setAttribute("aria-pressed", String(b===trigger));
    showRoutes(Number(trigger.dataset.band));
  });
  const fits = {
    FIT:"В экране", BORDERLINE_PAYLOAD_CHECK:"Проверка нагрузки", OUT_OF_RANGE:"Вне экрана",
    CANDIDATE_PERFORMANCE_CHECK:"Проверка характеристик",
    OUTSIDE_STUDY_ENVELOPE:"Вне контура", SCREEN_WIDEBODY_IF_DEMAND_VALIDATED:"Проверить дальний тип при спросе",
    NOT_REQUIRED_BY_DISTANCE_SCREEN:"Дальность сама по себе не требует"
  };
  function showRoutes(index) {
    const pairs = data.fleet.pairs.filter(p => routeBands[index].match(p.gc_distance_km));
    const axis = 105, x = km => axis + km * 0.084;
    const bottom = 43 + pairs.length * 23;
    const ticks = [0,1000,2000,3000,4000,5000,6000,7000].map(km =>
      svgText(x(km), 20, number(km), 'text-anchor="middle" font-size="11"')).join("");
    const limits = [[2355,"#a05f39"],[3000,"#6e577e"]].map(([km,col]) =>
      `<line x1="${x(km)}" y1="26" x2="${x(km)}" y2="${bottom-8}" stroke="${col}" stroke-width="2"
        stroke-dasharray="5 4"/>`).join("");
    const bars = pairs.map((p, i) => {
      const y = 34 + i * 23;
      return svgText(axis - 10, y + 10, p.airport_pair, 'text-anchor="end"') +
        `<rect x="${axis}" y="${y}" width="${x(p.gc_distance_km)-axis}" height="11" fill="${routeColor(p.gc_distance_km)}" rx="2">
        <title>${esc(p.airport_pair)} · ${number(p.gc_distance_km,2)} км</title></rect>` +
        svgText(x(p.gc_distance_km)+5, y+10, number(p.gc_distance_km,2), 'font-size="11"');
    }).join("");
    $("route-chart").innerHTML = svg("Ортодромия " + pairs.length + " пар аэропортов, километры", bottom, ticks + bars + limits);
    $("route-table").innerHTML = table(["Ранг","Пара","Ортодромия, км","Маршрут, км","Блок, ч","SSJ-95B",
      "SJ-100","Ту-214","Дальний тип"], pairs.map(p => [
      numeric(p.rank),th(p.airport_pair),numeric(p.gc_distance_km,2),numeric(p.route_distance_km_k110,2),
      numeric(p.est_block_time_h,2),td(fits[p.ssj95b_100y_fit]),td(fits[p.sj100_pd8_fit]),td(fits[p.tu214_2class_fit]),
      td(fits[p.longhaul_fit])
    ]), {scroll:true,label:"Аэропортовые пары и ограничения"});
  }
  showRoutes(0);
  const fleetReq = data.fleet.fleet_requirements;
  $("fleet-note").textContent = fleetReq.interpretation_ru;
  $("fleet-aircraft").innerHTML = [...new Set(fleetReq.program_scenarios.map(r => r.aircraft_type))].map(a=>option(a)).join("");
  const products = {BLOCK:"Блок",CHARTER:"Чартер",REGULAR_ROTATION:"Регулярная ротация"};
  $("fleet-product").innerHTML = Object.entries(products).map(([key,value])=>option(key,value)).join("");
  $("fleet-product").value = "CHARTER";
  $("fleet-aircraft").addEventListener("change", showFleet);
  $("fleet-product").addEventListener("change", showFleet);
  function showFleet() {
    const rows = fleetReq.program_scenarios.filter(r=>r.aircraft_type===$("fleet-aircraft").value
      && r.product===$("fleet-product").value);
    $("fleet-table").innerHTML = table(["Программ","Пара","Окна","Оборотов на программу/нед.","Блок-ч/нед.",
      "Занятость, ч/нед.","Пик ВС","Активных ВС","С резервом 15%","С резервом 20%"], rows.map(r=>[
      numeric(r.programs_confirmed_assumption),td(r.example_airport_pair),
      td(r.window_plan === "STAGGERED" ? "Разнесены" : "Совпадают"),numeric(r.rotations_per_program_per_week),
      numeric(r.weekly_block_h,2),numeric(r.weekly_aircraft_occupied_h,2),numeric(r.max_simultaneous_aircraft),
      numeric(r.active_aircraft),numeric(r.fleet_with_reserve_15_pct),numeric(r.fleet_with_reserve_20_pct)
    ]), {label:"Условный парк"});
  }
  showFleet();

  const hubKeys = ["geometry_pairs_25","geometry_pairs_35","observed_transit_pairs_25","observed_transit_pairs_35"];
  const hubColors = ["#85a8c4","#4f789e","#dfa566","#9b6535"];
  const hubLabels = ["Геометрия ≤25%","Геометрия ≤35%","Оба плеча ≤25%","Оба плеча ≤35%"];
  const hubs = data.hubs.filter(r=>r.demand_basis_scope==="STRUCTURAL_HYPOTHESIS");
  $("hub-legend").innerHTML = hubLabels.map((label,i)=>`<span style="--swatch:${hubColors[i]}">${label}</span>`).join("");
  const nodeCodes = [...new Set(hubs.map(h=>h.hub_iata))];
  const maxHub = Math.max(1,...hubs.flatMap(h=>hubKeys.map(k=>h[k])));
  const hubHeading = svgText(100,22,"REGULAR",'font-weight="bold"') +
    svgText(420,22,"EVENT_PEAK",'font-weight="bold"');
  const hubBlocks = nodeCodes.map((code, i) => {
    const y = 40+i*45;
    const records = ["REGULAR","EVENT_PEAK"].map(week=>hubs.find(h=>h.hub_iata===code && h.week_type===week));
    return svgText(10,y+18,code,'font-weight="bold"') + records.map((r,week)=>{
      const x=100+week*320;
      return hubKeys.map((k,j)=>{
        const value=r[k], bar=value*260/maxHub, by=y+j*9;
        return `<rect x="${x}" y="${by}" width="${Math.max(2,bar)}" height="6" fill="${hubColors[j]}">
          <title>${esc(code)} · ${r.week_type} · ${hubLabels[j]} · ${value}</title></rect>` +
          svgText(x+Math.max(2,bar)+4,by+6,value,'font-size="9"');
      }).join("");
    }).join("");
  }).join("");
  $("hub-chart").innerHTML = `<div class="chart-wrap hubs-chart" tabindex="0" role="region" aria-label="Диаграмма узлов">${svg(
    "Геометрия и наблюдения по типам недели. Структурные гипотезы", 447, hubHeading + hubBlocks)}</div>`;
  const hubVolume = value => value == null ? "Неизвестно" : number(value);
  $("hub-table").innerHTML = table(["Узел","Тип недели","Основание",...hubLabels,"Связные пары","Локальный объём",
    "Транзит ≤25% / ≤35%","Пиковый объём"], data.hubs.map(r => [
    th(r.hub_iata),td(r.week_type),`<td>${status(r.demand_basis_scope)}</td>`,...hubKeys.map(k=>numeric(r[k])),
    numeric(r.connected_geometry_pairs),td(hubVolume(r.local_od_pax_base)),
    td(hubVolume(r.transit_od_pax_detour25_base)+" / "+hubVolume(r.transit_od_pax_detour35_base)),
    td(hubVolume(r.event_peak_od_pax_base))
  ]), {scroll:true,label:"Срезы узлов по основаниям спроса"});

  const eventLabels = {CONFIRMED:"Подтверждено",PROVISIONAL:"Предварительно",TBD:"Дата неизвестна"};
  const dateOrder = r => r.start_date || "9999";
  $("event-table").innerHTML = table(["Событие","Город / аэропорт","Период","Статус",
    "Организатор / плательщик","Источники"], [...data.events].sort((a,b)=>dateOrder(a).localeCompare(dateOrder(b))).map(r=>[
    th(r.event_name),td(r.host_city+" · "+r.nearest_airport_iata),
    td(r.start_date ? r.start_date+" — "+r.end_date : "Неизвестно"),
    `<td>${badge(eventLabels[r.date_status],r.date_status==="CONFIRMED"?"":"warning")}</td>`,
    td(r.payer_or_organizer),`<td>${evidence(r.evidence_ids)}</td>`
  ]), {scroll:true,label:"События 2027"});
  $("event-sources").innerHTML = evidence(["EV-W13-043","EV-W13-060","EV-W2T4-003","EV-W2T4-004"]);

  const econKeys = [
    "client_cash_tct_rub","client_lost_work_h","client_time_value_rub","client_total_tct_rub",
    "client_door_to_door_h","client_alt_door_to_door_h","client_alt_cash_tct_rub","client_alt_lost_work_h",
    "client_alt_time_value_rub","client_alt_total_tct_rub","client_tct_savings_vs_alt_rub",
    "client_max_unit_contract_price_rub","rw_net_revenue_rub","rw_total_flight_cost_rub",
    "rw_displacement_cost_rub","rw_break_even_charter_price_rub","rw_break_even_seat_price_rub",
    "rw_target_price_per_seat_rub","rw_doc_max_rub_per_block_h","rw_net_contribution_rub",
    "j_passengers","effective_seats_per_aircraft","operational_screen_pass"
  ];
  const comparison = (v, metrics, keys=econKeys) => table(
    ["Показатель", "Вылет " + v.direction_labels.outbound, "Возврат " + v.direction_labels.inbound, "Оборот"],
    keys.filter(k=>metrics.outbound[k]!=null).map(key=>[
      th(data.metrics[key] || key),...["outbound","inbound","round_trip"].map(d=>numeric(metrics[d][key],
        key.endsWith("_h") && !key.includes("_rub") ? 2 : 0))
    ]), {label:"Двусторонняя экономика",cls:"econ-table"});
  const baseKeyList = ["client_cash_tct_rub","client_lost_work_h","client_time_value_rub","client_total_tct_rub",
    "client_alt_total_tct_rub","rw_total_flight_cost_rub","rw_break_even_charter_price_rub",
    "rw_break_even_seat_price_rub","rw_doc_max_rub_per_block_h","rw_net_contribution_rub","operational_screen_pass"];
  const alternativeSummary = c => c.variants.length < 2 ? "" :
    `<details><summary>Варианты (${c.variants.length})</summary>${table(
      ["Пара","Тип ВС","Продукт","J, %","Снижение, %","Эфф. мест","Цена места, ₽","Вклад, ₽","Фильтр"],
      c.variants.map(v=>{
        const m = calculateScenario(v);
        const both = (get) => DIRECTIONS.map(d=>get(d)).map(x=>number(x)).join(" / ");
        return [td(v.airport_pair),td(v.aircraft_type),td(v.variant_id),
          td(both(d=>v.inputs[d].j_share_pct)),td(both(d=>v.inputs[d].payload_seat_haircut_pct)),
          td(both(d=>m[d].effective_seats_per_aircraft)),td(both(d=>m[d].rw_break_even_seat_price_rub)),
          numeric(m.round_trip.rw_net_contribution_rub),td(both(d=>m[d].operational_screen_pass))];
      }), {scroll:true,label:"Варианты, сначала вылет, затем возврат"})}</details>`;
  const clusterTitles = {P1:"Пилот 1 · Уфа ↔ Новый Уренгой",P2:"Пилот 2 · Атомная и промышленная кооперация",
    P3:"Пилот 3 · Форум и зимняя дальность",C4:"СТНГ",C5:"РусГидро"};
  $("pilot-cards").innerHTML = Object.entries(clusterTitles).map(([cluster,title])=>
    `<h3>${title}</h3>`+data.cases.filter(c=>c.cluster_id===cluster).map(c=>{
      const v=c.variants[0], m=calculateScenario(v);
      return `<article class="card"><h4>${c.code} · ${esc(c.title_ru)}</h4>
        <div class="minihead">${status(c.decision)} ${status(c.demand_basis)} ${badge("[MODEL-ESTIMATE]")}</div>
        <p><strong>${esc(v.airport_pair.replace("-"," ↔ "))} · ${esc(v.aircraft_type)}</strong>.
          ${esc(v.condition_ru)}</p>
        ${comparison(v,m,baseKeyList)}${alternativeSummary(c)}
        <p>${evidence(c.evidence_ids)}</p></article>`;
    }).join("")).join("");

  const controls = {
    doc_per_block_h_rub:"DOC, ₽/блок-ч", parking_icing_pct:"Стоянка / ПОО / аэропорты, % к базе",
    target_margin_pct:"Целевая маржа, %", pax:"Летящие пассажиры, чел.", quota_seats:"Квота блока, мест",
    displacement_lf_pct:"Вероятность вытеснения Y, %", j_share_pct:"Доля группы с запросом J, %",
    payload_seat_haircut_pct:"Зимнее снижение ёмкости, %", loaded_hour_rub:"Стоимость рабочего часа, ₽/ч",
  };
  // A variant retains its own edits when the meeting switches to another configuration.
  const deltas = new Map();
  $("scenario").innerHTML = data.cases.map(c=>option(c.code,c.code+" · "+c.title_ru)).join("");
  const selectedCase = () => data.cases.find(c=>c.code===$("scenario").value);
  const selectedVariant = () => selectedCase().variants.find(v=>v.variant_id===$("variant").value);
  const selectionKey = () => selectedCase().code + "/" + selectedVariant().variant_id;
  const currentDelta = () => deltas.get(selectionKey()) || {outbound:{},inbound:{}};
  $("scenario").addEventListener("change", showVariants);
  $("variant").addEventListener("change", showControls);
  $("console-controls").addEventListener("submit", e=>e.preventDefault());

  function showVariants() {
    $("variant").innerHTML = selectedCase().variants.map(v=>option(v.variant_id,v.variant_id+" · "+v.aircraft_type)).join("");
    showControls();
  }
  function showControls() {
    const c=selectedCase(), v=selectedVariant(), delta=currentDelta();
    $("console-condition").textContent = v.condition_ru;
    $("console-controls").innerHTML = table(["Параметр", v.direction_labels.outbound, v.direction_labels.inbound],
      Object.entries(controls).filter(([key])=>Object.hasOwn(v.inputs.outbound,key)
        && (key !== "payload_seat_haircut_pct" || c.code === "P3B")).map(([key,label])=>{
        function field(d) {
          if (key === "target_margin_pct" && d === "inbound") return "<td>Общая для оборота</td>";
          const base = v.inputs[d][key];
          const spec = data.controls[v.input_param_ids[d][key]];
          const value = delta[d][key] ?? base;
          // P2B variants pin a starting J share; calibration can use the full modeled range.
          const range = key === "j_share_pct" ? data.j_share_interval : [spec.min_value,spec.max_value];
          const maximum = key === "target_margin_pct" ? Math.min(99,range[1]) : Math.max(range[1],base);
          const minimum = Math.min(range[0],base);
          const step = ["pax","quota_seats"].includes(key) ? 1 : "any";
          return `<td><input type="number" aria-label="${esc(label+" · "+v.direction_labels[d])}" data-key="${key}"
            data-direction="${d}" min="${minimum}" max="${maximum}" step="${step}" value="${value}" required
            ${minimum === maximum ? "readonly" : ""}>
            <small class="change-note" hidden></small></td>`;
        }
        return [th(label),...DIRECTIONS.map(field)];
      }), {label:"Параметры калибровки",cls:"console-inputs"});
    $("console-state").textContent = "";
    renderCalculation();
  }

  function renderCalculation() {
    const v=selectedVariant(), delta=currentDelta();
    for (const field of $("console-controls").querySelectorAll("input")) {
      const key=field.dataset.key, direction=field.dataset.direction;
      const changed=Object.hasOwn(delta[direction],key), note=field.nextElementSibling;
      field.classList.toggle("changed",changed);
      note.hidden=!changed;
      if (changed) note.textContent="База "+number(v.inputs[direction][key], Number.isInteger(v.inputs[direction][key])?0:2);
    }
    const changed=DIRECTIONS.some(d=>Object.keys(delta[d]).length);
    const reason=$("console-controls").checkValidity();
    $("export").disabled=!reason;
    if (!reason) {
      $("console-results").textContent = "Укажите число в разрешённом диапазоне.";
      return;
    }
    $("console-results").innerHTML = badge(changed?"[MODEL-ESTIMATE · ПРАВКА ЭКСПЕРТА]":"[MODEL-ESTIMATE]",changed?"edit":"")
      + comparison(v,calculateScenario(v,delta));
  }
  $("console-controls").addEventListener("input", e=>{
    const field=e.target;
    if (!field.matches("input[data-key]")) return;
    $("console-state").textContent="";
    if (!field.checkValidity()) {
      renderCalculation();
      return;
    }
    const v=selectedVariant(), delta=currentDelta(), key=field.dataset.key;
    const dirs=key === "target_margin_pct" ? DIRECTIONS : [field.dataset.direction];
    for (const d of dirs) {
      if (field.valueAsNumber === v.inputs[d][key]) delete delta[d][key];
      else delta[d][key]=field.valueAsNumber;
    }
    deltas.set(selectionKey(),delta);
    renderCalculation();
  });
  $("reset").addEventListener("click",()=>{
    deltas.delete(selectionKey());
    showControls();
    $("console-state").textContent="Базовые значения восстановлены.";
  });
  $("export").addEventListener("click",()=>{
    const c=selectedCase(), v=selectedVariant(), delta=currentDelta();
    const changed=DIRECTIONS.some(d=>Object.keys(delta[d]).length);
    const output={schema_version:1,baseline_date:data.meta.as_of,exported_at:new Date().toISOString(),
      case_id:c.case_id,variant_id:v.variant_id,mode:v.mode,evidence_basis:c.demand_basis,
      label:changed?"[MODEL-ESTIMATE · ПРАВКА ЭКСПЕРТА]":"[MODEL-ESTIMATE]",
      direction_labels:v.direction_labels,delta,
      changes:Object.fromEntries(DIRECTIONS.map(d=>[d,Object.fromEntries(Object.entries(delta[d])
        .map(([k,val])=>[k,{base:v.inputs[d][k],expert:val,delta:val-v.inputs[d][k]}]))])),
      outputs:calculateScenario(v,delta)};
    const url=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)],{type:"application/json"}));
    const download=document.createElement("a");
    download.href=url;
    download.download=`redwings-${c.code}-${v.variant_id}-calibration.json`;
    document.body.append(download);
    download.click();
    download.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    $("console-state").textContent="Калибровка передана на скачивание.";
  });
  showVariants();

  const book = data.playbooks;
  $("benchmarks").innerHTML = table(["Кейс","Рынок","Продукт и стадия","Условия переноса",
    "Ограничение / источники"], book.qualified_cases.map(b=>[
    th(b.case_name),td(b.country),td(b.product+" · "+b.stage),td(b.rf_transferable_term),
    `<td class="text">${esc(b.rf_limit)}<br>${evidence(b.qualifying_evidence_ids)}</td>`
  ]), {scroll:true,cls:"summary-table",label:"Квалифицированные кейсы"});
  $("adaptations").innerHTML = table(["Поправка","Условия"],book.rf_adaptations.map(a=>[
    th(a.title_ru),`<td>${plain(a.terms_ru)}<br>${evidence(a.evidence_ids)}</td>`
  ]),{label:"Поправки для РФ"});
  $("term-sheets").innerHTML = book.term_sheets.map(s=>`<details><summary>${esc(s.title_ru)}</summary><ul>
    ${s.terms_ru.map(t=>`<li>${plain(t)}</li>`).join("")}</ul><p>${evidence(s.evidence_ids)}</p></details>`).join("");
  $("questions").innerHTML=table(["Приоритет","Вопрос"],data.questions.map(([priority,question])=>[
    `<td>${badge(priority,priority==="P0"?"warning":"")}</td>`,td(question)
  ]),{label:"Пять вопросов Red Wings"});
  $("data-priorities").innerHTML=table(["Приоритет","Пакет","Данные"],data.priorities.map(x=>x.map(td)),
    {label:"Приоритеты запроса"});
  $("customer-request").value=data.customer_request;
  $("copy-request").addEventListener("click", async ()=>{
    const request=$("customer-request");
    try {
      await navigator.clipboard.writeText(request.value);
      $("request-state").textContent="Запрос скопирован.";
    } catch {
      request.focus();
      request.select();
      try {
        if (!document.execCommand("copy")) throw new Error("copy");
        $("request-state").textContent="Запрос скопирован.";
      } catch {
        $("request-state").textContent="Текст выделен. Используйте команду копирования браузера.";
      }
    }
  });

  const toggle=$("nav-toggle"), toc=$("toc");
  function setMenu(open) {
    toc.classList.toggle("open",open);
    toggle.setAttribute("aria-expanded",String(open));
  }
  toggle.addEventListener("click",()=>setMenu(!toc.classList.contains("open")));
  toc.addEventListener("click",e=>{if (e.target.closest("a")) setMenu(false);});
  const links=[...toc.querySelectorAll("a")];
  const chapters=links.map(link=>$(link.hash.slice(1)));
  function highlight() {
    const top=window.innerWidth<960 ? 73 : 44;
    const visible=chapters.filter(chapter=>chapter.getBoundingClientRect().top<=top).at(-1) || chapters[0];
    for (const link of links) {
      if (link.hash==="#"+visible.id) link.setAttribute("aria-current","true");
      else link.removeAttribute("aria-current");
    }
  }
  window.addEventListener("scroll",highlight,{passive:true});
  window.addEventListener("resize",highlight);
  highlight();
}

if (typeof document !== "undefined") setupPage(JSON.parse(document.getElementById("registry").textContent));
"""


def js_expression(expression):
    functions = {"ROUNDUP", "ROUNDDOWN", "IF", "MIN", "MAX"}
    return re.sub(r"\b[A-Za-z][A-Za-z0-9_]*\b",
                  lambda symbol: ("f." if symbol[0] in functions else "v.") + symbol[0], expression)


def formula_program(spec):
    definitions = []
    for mode, formulas in spec["directional"].items():
        rows = ",\n".join(f'    {item["output_id"]}: v => {js_expression(item["expression"])}' for item in formulas)
        definitions.append(f"  {mode}: {{\n{rows}\n  }}")
    sums = json.dumps(spec["round_trip"]["sum_outputs"], ensure_ascii=False)
    cycle = spec["round_trip"]["rw_doc_max_rub_per_block_h"]
    cycle = re.sub(r"SUM\(([a-z0-9_]+)\)", r"v.\1", cycle).replace("target_margin_pct", "margin")
    return ("const FORMULAS = {\n" + ",\n".join(definitions) + "\n};\n"
            f"const SUM_OUTPUTS = {sums};\nconst cycleDOC = (v, margin) => {cycle};\n")


def pack(registry):
    def strip(variant):
        keys = ("variant_id", "mode", "airport_pair", "aircraft_type", "condition_ru", "direction_labels",
                "inputs", "input_param_ids", "evidence_ids", "gc_distance_km")
        return {key: variant[key] for key in keys}
    case_keys = ("case_id", "cluster_id", "title_ru", "decision", "demand_basis", "confirmed_pax", "evidence_ids")
    shares = [a for a in registry["assumptions"] if a["param_id"].endswith(".j_share_pct")]
    return {
        "meta": registry["meta"],
        "organizations": registry["organizations"],
        "city_pairs": len({row["pair_id"] for row in read_csv(W2 / "opportunities.csv") if row["pair_id"]}),
        "evidence": registry["evidence"],
        "fleet": registry["fleet_matrix"],
        "hubs": registry["hubs_summary"],
        "events": registry["events_2027_future"],
        "barriers": registry["why_not_barriers"],
        "playbooks": registry["benchmarks_and_playbooks"],
        "questions": list(zip(QUESTION_PRIORITIES, registry["rw_5_questions"], strict=True)),
        "priorities": DATA_PRIORITIES,
        "scores": council_scores(),
        "customer_request": registry["anonymized_customer_request"],
        "cases": [
            {**{key: case[key] for key in case_keys}, "code": case_code(case),
             "variants": [strip(v) for v in case["variants"]]}
            for case in registry["pilots_and_clusters"]
        ],
        "controls": {a["param_id"]: {k: a[k] for k in ("min_value", "max_value", "step")}
                     for a in registry["assumptions"]},
        "j_share_interval": [min(a["min_value"] for a in shares), max(a["max_value"] for a in shares)],
        "metrics": METRICS,
    }


def build(registry):
    dataset = json.dumps(pack(registry), ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    dataset = dataset.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    links = "\n".join(f'<a href="#{key}">{label}</a>' for key, label in SECTIONS)
    chapters = "\n".join(f'<section id="{key}">{HTML_SECTIONS[key]}\n</section>' for key, _ in SECTIONS)
    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Корпоративный спрос Red Wings</title><style>{CSS}</style></head>
<body><div class="wrapper"><aside class="sidebar">
<div class="brand">Red Wings · Корпоративный спрос</div>
<button type="button" id="nav-toggle" aria-controls="toc" aria-expanded="false">Оглавление</button>
<nav id="toc" aria-label="Оглавление">{links}</nav></aside>
<main>{chapters}</main></div>
<dialog id="evidence-dialog" aria-labelledby="source-heading"><form method="dialog">
<button type="submit" autofocus>Закрыть</button></form><h2 id="source-heading">Источник</h2>
<dl id="source-fields"></dl></dialog>
<script type="application/json" id="registry">{dataset}</script>
<script>{formula_program(registry["formulas_spec"])}{RUNTIME}</script>
</body></html>
"""


if __name__ == "__main__":
    OUTPUT.write_text(build(load_registry()), encoding="utf-8")
    print(OUTPUT)
