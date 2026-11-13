"use strict";

const $ = (selector) => document.querySelector(selector);
const form = $("#plan-form");
const results = $("#results");
const submit = $("#submit-button");
const field = (name) => form.elements.namedItem(name);
const list = (value) => Array.isArray(value) ? value : [];
const nonnegative = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
const text = (tag, className, value) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = value ?? "";
  return element;
};
const dateFormatter = new Intl.DateTimeFormat("ru-RU", {day:"numeric", month:"long", year:"numeric"});
const timeFormatter = new Intl.DateTimeFormat("ru-RU", {day:"numeric", month:"short", hour:"2-digit", minute:"2-digit", timeZone:"UTC"});
const rubles = new Intl.NumberFormat("ru-RU", {style:"currency", currency:"RUB", maximumFractionDigits:0});
const names = {plane:"Самолёт", train:"Поезд", suburban:"Электричка", bus:"Автобус", taxi:"Такси", walk:"Пешком", ground:"Наземный транспорт"};
const paths = {
  plane:'<path d="m3 13 7-2 2-8 2-1 1 8 5-1c3 0 3 2 0 3l-5 2-3 7-2 1 1-7-5 1-3-3Z"/>',
  train:'<rect x="6" y="3" width="12" height="15" rx="3"/><path d="M6 11h12M9 18l-2 3m8-3 2 3M9 7h6M9 14h.01M15 14h.01"/>',
  bus:'<rect x="4" y="5" width="16" height="13" rx="2"/><path d="M4 12h16M8 5v7m8-7v7M7 18v3m10-3v3M7 15h.01M17 15h.01"/>',
  taxi:'<path d="m4 11 2-6h12l2 6v7H4v-7Zm0 0h16M7 18v3m10-3v3M7 14h.01M17 14h.01"/>',
  walk:'<circle cx="14" cy="4" r="2"/><path d="m10 21 2-7-3-3 3-4 3 4 4 1M5 14l4-3m3 3 5 7"/>',
  ground:'<path d="M4 18h16M7 18l3-14m7 14L14 4M12 7v3m0 3v2"/>'
};
function icon(mode) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.5");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = paths[mode === "suburban" ? "train" : mode] || paths.ground;
  return svg;
}
function dateLabel(value) {
  if (typeof value !== "string" || !value) return "Дата не указана";
  const parsed = new Date(`${value.slice(0,10)}T12:00:00`);
  return Number.isNaN(parsed.getTime()) ? value : dateFormatter.format(parsed);
}
function timeLabel(value) {
  if (typeof value !== "string" || !value.trim()) return "время уточняется";
  // Keep the source's wall-clock time and offset; the viewer's timezone is irrelevant.
  const match = value.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$/);
  if (!match) return value;
  const parsed = new Date(`${match[1]}T${match[2]}:00Z`);
  if (Number.isNaN(parsed.getTime())) return value;
  const offset = match[3] === "Z" ? "UTC" : match[3] ? `UTC${match[3]}` : "часовой пояс не указан";
  return `${timeFormatter.format(parsed)} (${offset})`;
}
function durationLabel(minutes) {
  const rounded = Math.round(minutes);
  const hours = Math.floor(rounded / 60);
  return [hours ? `${hours} ч` : "", rounded % 60 || !hours ? `${rounded % 60} мин` : ""].filter(Boolean).join(" ");
}
function safeUrl(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}
function externalLink(label, url) {
  const href = safeUrl(url);
  if (!href) return null;
  const link = text("a", "", label || "Открыть источник");
  link.href = href;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  return link;
}
function isRW(leg) {
  return leg.mode === "plane" && (/red\s*wings|ред\s*вингс|рэд\s*вингс|^(?:WZ|RW|RWZ)$/i.test(leg.carrier || "") || /^(?:WZ|RW|RWZ)\s*\d/i.test(leg.flight_number || ""));
}
function setStatus(message, kind = "") {
  const status = $("#request-status");
  status.replaceChildren(text("span", "", message));
  status.dataset.kind = kind;
  status.hidden = !message;
}
function retryButton(container, label, handler) {
  const button = text("button", "text-button", label);
  button.type = "button";
  button.addEventListener("click", handler);
  container.append(button);
}
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers:{Accept:"application/json", ...options.headers}});
  let data;
  try { data = await response.json(); }
  catch { throw new Error("Сервис вернул некорректный ответ. Повторите поиск позже."); }
  if (!response.ok && !(path === "/api/plan" && ["needs_data", "no_routes", "error"].includes(data?.status))) {
    throw new Error(typeof data?.message === "string" ? data.message : "Сервис временно недоступен. Повторите попытку.");
  }
  return data;
}
function setMode(mode) {
  const flight = mode === "flight";
  const fields = $("#flight-fields");
  fields.hidden = !flight;
  fields.disabled = !flight;
  field("flight_number").required = flight;
  field("flight_date").required = flight;
  field("mode").value = flight ? "flight" : "trip";
}
function syncDates() {
  const from = field("date_from").value;
  const to = field("date_to").value;
  field("date_to").min = from;
  field("date_to").setCustomValidity(from && to && to < from ? "Дата окончания должна быть не раньше даты начала." : "");
  const selected = field("flight_date").value;
  field("flight_date").setCustomValidity(field("mode").value === "flight" && selected && ((from && selected < from) || (to && selected > to)) ? "Дата рейса должна входить в период поездки." : "");
}
function validateCities() {
  const origin = field("origin").value.trim();
  const destination = field("destination").value.trim();
  field("origin").setCustomValidity(origin ? "" : "Укажите город отправления.");
  field("destination").setCustomValidity(!destination ? "Укажите город назначения." : origin.toLocaleLowerCase("ru") === destination.toLocaleLowerCase("ru") ? "Выберите другой город назначения." : "");
  field("flight_number").setCustomValidity(field("mode").value === "flight" && !field("flight_number").value.trim() ? "Укажите номер рейса Red Wings." : "");
}
function requestBody() {
  const data = new FormData(form);
  const request = Object.fromEntries(["mode","origin","destination","date_from","date_to","preference"].map(key => [key, String(data.get(key) || "").trim()]));
  for (const name of ["origin_address", "destination_address"]) if (data.get(name)?.trim()) request[name] = data.get(name).trim();
  if (request.mode === "flight") {
    request.flight_number = String(data.get("flight_number") || "").trim();
    request.flight_date = data.get("flight_date");
  }
  return request;
}
function clearResults() {
  $("#variant-list").replaceChildren();
  $("#sources-list").replaceChildren();
  ["#data-notice", "#assistant-note", "#sources-section", "#result-count"].forEach(selector => { $(selector).hidden = true; });
}
function dataNotice(data) {
  const box = $("#data-notice");
  box.replaceChildren();
  const mode = ["live", "snapshot"].includes(data.data_mode) ? data.data_mode : "unavailable";
  box.dataset.mode = mode;
  const labels = {live:"Данные расписания", snapshot:"Сохранённое расписание", unavailable:"Расписание недоступно"};
  box.append(text("strong", "", labels[mode]));
  box.append(text("p", "", mode === "snapshot" ? "Перед покупкой проверьте расписание, места и цену." : mode === "live" ? "Места и цены не проверены." : "Без подтверждённого рейса Red Wings варианты не предлагаются."));
  if (data.checked_at || data.coverage_note || mode === "snapshot") {
    const details = text("details", "data-details", "");
    details.append(text("summary", "", "Покрытие и дата"));
    details.append(text("p", "", data.checked_at ? `Проверено: ${timeLabel(data.checked_at)}` : "Точное время получения снимка не сохранено."));
    if (data.coverage_note) details.append(text("p", "", data.coverage_note));
    box.append(details);
  }
  box.hidden = false;
}
function renderLeg(leg) {
  const rw = isRW(leg);
  const row = text("li", `leg${rw ? " rw" : ""}`, "");
  const marker = text("span", "leg-marker", "");
  marker.append(icon(leg.mode));
  row.append(marker);
  const top = text("div", "leg-topline", "");
  top.append(text("span", "leg-kind", rw ? `Red Wings${leg.flight_number ? ` · ${leg.flight_number}` : ""}` : names[leg.mode] || names.ground));
  const status = {scheduled:"По расписанию", suggestion:"Требует подбора", unknown:"Данные уточняются"}[leg.status] || "Данные уточняются";
  top.append(text("span", `leg-status ${leg.status === "suggestion" ? "suggestion" : ""}`, status));
  row.append(top, text("p", "leg-route", `${leg.origin || "Пункт уточняется"} → ${leg.destination || "Пункт уточняется"}`));
  if (leg.mode === "plane" || leg.departure || leg.arrival) {
    const times = text("div", "leg-times", "");
    times.append(text("span", "", `Отправление: ${timeLabel(leg.departure)}`), text("span", "", `Прибытие: ${timeLabel(leg.arrival)}`));
    row.append(times);
  }
  const details = text("div", "leg-details", "");
  if (leg.carrier && !rw) details.append(text("span", "", leg.carrier));
  if (nonnegative(leg.price)) details.append(text("span", "", rubles.format(leg.price)));
  row.append(details);
  const links = text("div", "leg-links", "");
  const seen = new Set();
  const addLink = (label, url) => {
    const link = externalLink(label, url);
    if (link && !seen.has(link.href)) { seen.add(link.href); links.append(link); }
  };
  addLink(leg.source_name ? `Источник: ${leg.source_name}` : "Источник расписания", leg.source_url);
  list(leg.links).forEach(link => { if (link && typeof link === "object") addLink(link.label, link.url); });
  row.append(links);
  return row;
}
function renderVariant(variant, index) {
  const legs = list(variant.legs);
  const allTimes = legs.length > 0 && legs.every(leg => leg.departure && leg.arrival);
  const completeDuration = nonnegative(variant.duration_minutes) && allTimes;
  const knownPrice = nonnegative(variant.total_price);
  const completePrice = knownPrice && legs.length > 0 && legs.every(leg => nonnegative(leg.price));
  let title = typeof variant.title === "string" ? variant.title : `Вариант ${index + 1}`;
  if ((!completeDuration && /самый быстрый|быстрее всех/i.test(title)) || (!completePrice && /самый деш[её]вый|дешевле всех/i.test(title))) title = `Вариант ${index + 1}`;
  const card = text("article", "variant", "");
  const header = text("header", "variant-header", "");
  const intro = text("div", "", "");
  intro.append(text("h3", "", title));
  if (variant.summary) intro.append(text("p", "variant-summary", variant.summary));
  header.append(intro);
  card.append(header);
  const metrics = text("div", "variant-metrics", "");
  for (const [label, value, known] of [["Всё время в пути", completeDuration ? durationLabel(variant.duration_minutes) : "Уточняется", completeDuration], ["Стоимость поездки", knownPrice ? rubles.format(variant.total_price) : "Уточняется", knownPrice]]) {
    const metric = text("div", "metric", "");
    metric.append(text("span", "", label), text("strong", known ? "" : "unknown", value));
    metrics.append(metric);
  }
  if (completeDuration || knownPrice) card.append(metrics);
  else card.append(text("p", "price-note", "Время всей поездки и стоимость пока не рассчитаны."));
  const chain = text("div", "transport-chain", "");
  chain.setAttribute("aria-label", "Последовательность транспорта");
  legs.forEach((leg, i) => {
    if (i) { const arrow = text("span", "chain-arrow", "›"); arrow.setAttribute("aria-hidden", "true"); chain.append(arrow); }
    const item = text("span", `chain-item${isRW(leg) ? " rw" : ""}`, "");
    item.append(icon(leg.mode), text("span", "", isRW(leg) ? "Red Wings" : names[leg.mode] || names.ground));
    chain.append(item);
  });
  const ordered = text("ol", "legs", "");
  legs.forEach(leg => ordered.append(renderLeg(leg)));
  card.append(chain, ordered);
  const warnings = [...new Set(list(variant.warnings).filter(item => typeof item === "string" && item.trim()))];
  if (legs.filter(leg => leg.status === "scheduled").length > 1) warnings.push("Билеты на участки оформляются отдельно; стыковка не защищена единым билетом.");
  if (warnings.length) {
    const warningList = text("ul", "warnings", "");
    warnings.forEach(warning => warningList.append(text("li", "", warning)));
    card.append(warningList);
  }
  return card;
}
function renderSources(sources) {
  const target = $("#sources-list");
  const seen = new Set();
  list(sources).forEach(source => {
    const url = typeof source === "string" ? source : source?.url || source?.source_url;
    const label = typeof source === "string" ? source : source?.name || source?.label || source?.title || source?.source_name || "Источник";
    const link = externalLink(label, url);
    if (link && !seen.has(link.href)) { seen.add(link.href); const row = text("li", "", ""); row.append(link); target.append(row); }
  });
  $("#sources-section").hidden = !target.children.length;
}
function renderResponse(data) {
  if (!data || !["ok", "no_routes", "needs_data", "error"].includes(data.status)) throw new Error("Не удалось прочитать варианты. Повторите поиск позже.");
  dataNotice(data);
  const variants = data.status === "ok" && data.data_mode !== "unavailable" ? list(data.variants).filter(variant => variant && list(variant.legs).some(leg => leg && isRW(leg) && leg.status === "scheduled")).map(variant => ({...variant, legs:list(variant.legs).filter(leg => leg && typeof leg === "object")})) : [];
  if (variants.length) {
    variants.forEach((variant, index) => $("#variant-list").append(renderVariant(variant, index)));
    const count = $("#result-count");
    count.textContent = `Вариантов: ${variants.length}`;
    count.hidden = false;
    setStatus("");
  } else {
    const defaults = {ok:"Подтверждённых вариантов для этого запроса пока нет. Попробуйте другой период или доступный пример.", no_routes:"В покрытых источниках не найдено подходящих вариантов. Измените даты или направление.", needs_data:"Для этого запроса недостаточно данных. Уточните направление, даты или выбранный рейс.", error:"Не удалось построить маршрут. Повторите поиск позже."};
    setStatus(data.message || defaults[data.status], data.status === "error" ? "error" : "");
    if (data.status === "error") retryButton($("#request-status"), "Повторить", () => form.requestSubmit());
  }
  if (variants.length && data.message) setStatus(data.message);
  if (data.assistant?.text && ["ok", "completed", "success"].includes(data.assistant.status)) {
    $("#assistant-note").textContent = data.assistant.text;
    $("#assistant-note").hidden = false;
  }
  renderSources(data.sources);
}
async function loadHealth() {
  const indicator = $("#health");
  try {
    const health = await api("/api/health");
    const mode = health?.schedule_configured === false ? "unavailable" : ["live", "snapshot"].includes(health?.schedule_mode) ? health.schedule_mode : "unavailable";
    indicator.dataset.mode = mode;
    indicator.textContent = {live:"Актуальное расписание", snapshot:"Снимок расписания", unavailable:"Расписание недоступно"}[mode];
  } catch {
    indicator.dataset.mode = "unavailable";
    indicator.replaceChildren(text("span", "", "Сервис недоступен"));
    retryButton(indicator, "Проверить", loadHealth);
  }
  indicator.hidden = false;
}
async function loadExamples() {
  const container = $("#examples");
  container.replaceChildren(text("p", "muted small", "Загружаем…"));
  try {
    const data = await api("/api/examples");
    if (!Array.isArray(data?.examples)) throw new Error("Invalid examples response");
    const cities = $("#supported-cities");
    cities.replaceChildren();
    list(data.cities).forEach(item => { if (item?.city) { const option = document.createElement("option"); option.value = item.city; cities.append(option); } });
    container.replaceChildren();
    const examples = data.examples.filter(example => example && typeof example.request === "object" && example.request && typeof example.label === "string");
    examples.forEach(example => {
      const button = text("button", "example-button", example.label);
      button.type = "button";
      if (example.request.date_from) button.append(text("span", "", `${dateLabel(example.request.date_from)}${example.request.date_to && example.request.date_to !== example.request.date_from ? ` — ${dateLabel(example.request.date_to)}` : ""}`));
      button.addEventListener("click", () => {
        cancelPending();
        form.reset();
        setMode(example.request.mode);
        ["origin","destination","date_from","date_to","preference","origin_address","destination_address","flight_number","flight_date"].forEach(name => {
          if (typeof example.request[name] === "string") field(name).value = example.request[name];
        });
        syncDates();
        validateCities();
        clearResults();
        setStatus("");
        $("#query-summary").hidden = true;
        $("#empty-state").hidden = false;
        submit.focus();
      });
      container.append(button);
    });
    if (!examples.length) container.append(text("p", "muted small", "Поддержанные примеры пока недоступны."));
  } catch {
    container.replaceChildren(text("p", "muted small", "Не удалось загрузить примеры."));
    retryButton(container, "Повторить", loadExamples);
  }
}
let controller;
let requestId = 0;
function cancelPending() {
  requestId += 1;
  controller?.abort();
  submit.disabled = false;
  submit.querySelector("span").textContent = "Найти варианты";
  results.setAttribute("aria-busy", "false");
}
form.addEventListener("input", () => { syncDates(); validateCities(); });
form.addEventListener("change", event => {
  if (event.target.name === "mode") { setMode(event.target.value); syncDates(); validateCities(); }
});
$("#swap-cities").addEventListener("click", () => {
  const origin = field("origin").value;
  field("origin").value = field("destination").value;
  field("destination").value = origin;
  validateCities();
});
form.addEventListener("submit", async event => {
  event.preventDefault();
  syncDates();
  validateCities();
  if (!form.reportValidity()) return;
  cancelPending();
  const currentId = requestId;
  controller = new AbortController();
  const activeController = controller;
  const request = requestBody();
  clearResults();
  $("#empty-state").hidden = true;
  const query = $("#query-summary");
  query.textContent = `${request.origin} → ${request.destination} · ${dateLabel(request.date_from)}${request.date_from !== request.date_to ? ` — ${dateLabel(request.date_to)}` : ""}${request.mode === "flight" ? ` · ${request.flight_number}, ${dateLabel(request.flight_date)}` : ""}`;
  query.hidden = false;
  submit.disabled = true;
  submit.querySelector("span").textContent = "Ищем варианты…";
  results.setAttribute("aria-busy", "true");
  setStatus("Проверяем рейсы…", "loading");
  const timeout = setTimeout(() => activeController.abort(), 90000);
  try {
    const data = await api("/api/plan", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(request), signal:activeController.signal});
    if (currentId !== requestId) return;
    renderResponse(data);
    $("#results-title").focus({preventScroll:true});
    if (window.matchMedia("(max-width: 760px)").matches) results.scrollIntoView({behavior:"auto", block:"start"});
  } catch (error) {
    if (currentId !== requestId) return;
    setStatus(error.name === "AbortError" ? "Поиск занял слишком много времени. Повторите попытку." : error.message === "Failed to fetch" ? "Нет связи с сервисом. Проверьте подключение и повторите поиск." : error.message, "error");
    retryButton($("#request-status"), "Повторить", () => form.requestSubmit());
  } finally {
    clearTimeout(timeout);
    if (currentId === requestId) {
      submit.disabled = false;
      submit.querySelector("span").textContent = "Найти варианты";
      results.setAttribute("aria-busy", "false");
    }
  }
});
loadHealth();
loadExamples();
