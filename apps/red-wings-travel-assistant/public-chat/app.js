"use strict";

const $ = (selector) => document.querySelector(selector);
const elements = {
  form: $("#chat-form"), input: $("#message"), send: $("#send"),
  conversation: $("#conversation"), messages: $("#messages"), welcome: $("#welcome"),
  demoGallery: $("#demo-gallery"), demos: $("#demos"), demosStatus: $("#demos-status"),
  offlineDemo: $("#offline-demo"), offlineStatus: $("#offline-status"), demoExplanation: $("#demo-explanation"),
  demosError: $("#demos-error"), reloadDemos: $("#reload-demos"),
  error: $("#error"), errorMessage: $("#error-message"), errorAction: $("#error-action"),
  newDialog: $("#new-dialog"), resetDialog: $("#reset-dialog"),
  resetTitle: $("#reset-title"), resetDescription: $("#reset-description"), confirmReset: $("#confirm-reset"),
  tripRegion: $("#trip-region"), tripDetails: $("#trip-details"),
  tripPreview: $("#trip-preview"), tripFields: $("#trip-fields"),
  openTrip: $("#open-trip"), tripDialog: $("#trip-dialog"), tripForm: $("#trip-form"), closeTrip: $("#close-trip"),
  tripInputs: $("#trip-inputs"), tripFormError: $("#trip-form-error"), tripFormStatus: $("#trip-form-status"),
  startTrip: $("#start-trip"), replaceConfirm: $("#trip-replace-confirm"), confirmTripStart: $("#confirm-trip-start"), cancelTripStart: $("#cancel-trip-start"),
  dateFrom: $("#date-from"), dateTo: $("#date-to"), dateToField: $("#date-to-field"), flexibleDates: $("#flexible-dates"),
  originAddress: $("#origin-address"), destinationAddress: $("#destination-address"),
  tripWishes: $("#trip-wishes"),
  hasFlight: $("#has-flight"), flightFields: $("#flight-fields"), flightDate: $("#flight-date"), flightOptions: $("#flight-options"),
  flightsStatus: $("#flights-status"), flightDetail: $("#flight-detail"), reloadFlights: $("#reload-flights"),
};

// Only the server-issued identifier is used to continue a session. The visible
// conversation lives in this tab's DOM; no transcript is persisted or uploaded.
let sessionId = null;
let busy = false;
let composing = false;
let hasMessages = false;
let demosLoading = false;
let pendingDemo = null;
let resetTrigger = null;
let activeSuggestions = null;
let errorAction = null;
let currentTrip = null;
let tripStarting = false;
let editorInitialized = false;
let editorSessionId = null;
let flights = [];
let flightsController = null;
let offlineDemo = false;
let offlineSeedId = null;
let offlineDataPromise = null;

const array = (value) => Array.isArray(value) ? value : [];
const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const string = (value) => typeof value === "string" ? value.trim() : "";
const number = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
const modes = {plane: "Самолёт", train: "Поезд", suburban: "Электричка", bus: "Автобус", taxi: "Такси", walk: "Пешком"};
const planStatuses = {verified: "Расписание проверено", partial: "Расписание проверено частично", candidate: "Предварительный вариант"};
const evidenceLabels = {dated: "Расписание на дату", published_pattern: "Опубликованный маршрут", indicative: "Предварительные сведения", unknown: "Не подтверждено"};
const networkLabels = {current: "Действующая сеть", scenario_2027_2028: "Сценарный режим (сеть 2027–2028)"};
const dataModeLabels = {snapshot: "Сохранённый снимок", scenario: "Сценарный режим (сеть 2027–2028)"};
const smartTransferTitle = "Умный трансфер — целевой партнёрский шаттл под рейс WZ";
const basketDescription = "Целевая интеграция White Label РЖД-ЦПР. Требует подключения партнёрского API; сейчас билеты оформляются отдельно.";
const rubles = new Intl.NumberFormat("ru-RU", {style: "currency", currency: "RUB", maximumFractionDigits: 0});
const calendar = new Intl.DateTimeFormat("ru-RU", {day: "numeric", month: "short", year: "numeric", timeZone: "UTC"});

function node(tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== undefined) element.textContent = value;
  return element;
}

function safeUrl(value) {
  if (!string(value)) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

function link(label, value) {
  const href = safeUrl(value);
  if (!href) return null;
  const anchor = node("a", "", string(label) || new URL(href).hostname);
  anchor.href = href;
  anchor.target = "_blank";
  anchor.rel = "noopener noreferrer";
  return anchor;
}

function serviceName(url) {
  const host = url.hostname.replace(/^www\./, "");
  if (host === "flyredwings.com" || host.endsWith(".flyredwings.com")) return "Red Wings";
  if (host === "rasp.yandex.ru" || host.endsWith(".rasp.yandex.net")) return "Яндекс Расписания";
  if (host === "rzd.ru" || host.endsWith(".rzd.ru")) return "РЖД";
  if (host === "yandex.ru" && /^\/maps(?:\/|$)/.test(url.pathname)) return "Яндекс Карты";
  return "";
}

// These are navigation links supplied by the server, never a reservation or a
// claim that route, date, price or seats have been prefilled by this client.
function actionEntries(value) {
  const entries = [];
  const seen = new Set();
  for (const item of array(value)) {
    if (!object(item)) continue;
    const href = safeUrl(item.url);
    if (!href || seen.has(href)) continue;
    seen.add(href);
    const url = new URL(href);
    const service = serviceName(url);
    const label = string(item.label);
    const home = /^\/*$/.test(url.pathname);
    const booking = /билет|купить|покуп|брони|booking|ticket/i.test(label) || /booking|ticket/i.test(url.pathname);
    let title = label || "Открыть страницу участка";
    if (service === "Яндекс Карты") title = url.searchParams.has("rtext") ? "Построить переезд" : "Карты · поиск маршрута";
    else if (service === "Яндекс Расписания") title = home ? "Расписание · поиск маршрута" : "Расписание";
    else if (home) title = service ? `${service} · сайт перевозчика` : "Сайт перевозчика";
    else if (booking && service === "Red Wings") title = "Покупка у Red Wings";
    else if (booking && service === "РЖД") title = "Покупка у РЖД";
    const note = booking && !home ? url.search ? "Маршрут и дату проверьте на сайте." : "Маршрут и дату нужно выбрать на сайте." : "";
    entries.push({url: href, label: title, note});
  }
  return entries;
}

function renderActions(value) {
  const actions = actionEntries(value);
  if (!actions.length) return null;
  const group = node("div", "leg-actions");
  for (const action of actions) {
    const item = node("span", "leg-action");
    item.append(link(action.label, action.url));
    group.append(item);
  }
  return group;
}

function dateLabel(value) {
  if (!string(value)) return "Не уточнено";
  const match = value.match(/^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$/);
  if (!match) return value;
  const date = new Date(`${match[1]}T12:00:00Z`);
  if (Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== match[1]) return value;
  const day = calendar.format(date);
  if (!match[2]) return day;
  const zone = match[3] === "Z" ? "UTC" : match[3] ? `UTC${match[3]}` : "часовой пояс не указан";
  // Preserve the source's wall-clock time, never the browser's local timezone.
  return `${day}, ${match[2]} (${zone})`;
}

function durationLabel(value) {
  const minutes = Math.round(value);
  const hours = Math.floor(minutes / 60);
  return [hours ? `${hours} ч` : "", minutes % 60 || !hours ? `${minutes % 60} мин` : ""].filter(Boolean).join(" ");
}

function transportIcon(mode) {
  const definitions = {
    plane: [["path", {d: "m3 13 7-2 2-8 2-1 1 8 5-1c3 0 3 2 0 3l-5 2-3 7-2 1 1-7-5 1-3-3Z"}]],
    train: [["rect", {x: "6", y: "3", width: "12", height: "15", rx: "3"}], ["path", {d: "M6 11h12M9 18l-2 3m8-3 2 3M9 7h6M9 14h.01M15 14h.01"}]],
    bus: [["rect", {x: "4", y: "5", width: "16", height: "13", rx: "2"}], ["path", {d: "M4 12h16M8 5v7m8-7v7M7 18v3m10-3v3M7 15h.01M17 15h.01"}]],
    taxi: [["path", {d: "m4 11 2-6h12l2 6v7H4v-7Zm0 0h16M7 18v3m10-3v3M7 14h.01M17 14h.01M10 5V3h4v2"}]],
    walk: [["circle", {cx: "14", cy: "4", r: "2"}], ["path", {d: "m10 21 2-7-3-3 3-4 3 4 4 1M5 14l4-3m3 3 5 7"}]],
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  for (const [key, value] of Object.entries({viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.5", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true"})) svg.setAttribute(key, value);
  for (const [tag, attributes] of definitions[mode === "suburban" ? "train" : mode] || []) {
    const shape = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attributes)) shape.setAttribute(key, value);
    svg.append(shape);
  }
  return svg;
}

function nearEnd() {
  const pane = elements.conversation;
  return pane.scrollHeight - pane.scrollTop - pane.clientHeight < 110;
}

function scrollToEnd() {
  requestAnimationFrame(() => { elements.conversation.scrollTop = elements.conversation.scrollHeight; });
}

function resizeInput() {
  elements.input.style.height = "auto";
  const maximum = Math.min(220, (window.visualViewport?.height || window.innerHeight) * .28);
  elements.input.style.height = `${Math.min(elements.input.scrollHeight, maximum)}px`;
  elements.send.disabled = busy || offlineDemo || !elements.input.value.trim();
  elements.newDialog.disabled = busy || !(hasMessages || sessionId || elements.input.value.trim());
  elements.openTrip.disabled = busy || offlineDemo;
  elements.offlineDemo.disabled = busy;
  elements.input.disabled = offlineDemo;
}

function syncViewport() {
  const follow = nearEnd();
  const viewport = window.visualViewport;
  const height = viewport?.height || window.innerHeight;
  const top = viewport?.offsetTop || 0;
  const root = document.documentElement;
  // Safari can pan the visual viewport as well as shrink it for the keyboard.
  // Keep the composer inside that visible area; only the history pane scrolls.
  root.style.setProperty("--app-height", `${Math.round(height)}px`);
  root.style.setProperty("--viewport-top", `${Math.round(top)}px`);
  const textInput = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName?.toUpperCase());
  const keyboardOpen = textInput && window.innerHeight - height > 100;
  root.dataset.keyboardOpen = String(keyboardOpen);
  const touchScreen = window.matchMedia("(max-width: 600px), (hover: none), (pointer: coarse)").matches;
  if (touchScreen || keyboardOpen) elements.input.removeAttribute("aria-describedby");
  else elements.input.setAttribute("aria-describedby", "keyboard-hint");
  resizeInput();
  if (follow && hasMessages) scrollToEnd();
}

function fillMessage(message) {
  elements.input.value = message;
  resizeInput();
  elements.input.focus();
  elements.input.setSelectionRange(message.length, message.length);
}

function clearError() {
  elements.error.hidden = true;
  elements.errorMessage.textContent = "";
  elements.errorAction.textContent = "";
  errorAction = null;
}

function showError(message, label, action) {
  elements.errorMessage.textContent = message;
  elements.errorAction.textContent = label;
  errorAction = action;
  elements.error.hidden = false;
}

function showChatError(message) {
  if (sessionId) showError(message, "Написать уточнение", () => elements.input.focus());
  else showError(message, "Начать новый диалог", () => requestReset());
}

function appendMessage(role, message, author) {
  const article = node("article", `message message-${role}`);
  const label = author || (role === "user" ? "Вы" : "Помощник Red Wings");
  article.setAttribute("aria-label", author || (role === "user" ? "Ваше сообщение" : "Ответ помощника"));
  article.append(node("p", "message-author", label));
  if (string(message)) article.append(node("p", "message-body", message));
  elements.messages.append(article);
  return article;
}

function sourceEntries(value) {
  const seen = new Set();
  return array(value).flatMap((source) => {
    const item = typeof source === "string" ? {url: source} : source;
    if (!object(item)) return [];
    const url = safeUrl(item.url || item.source_url);
    const label = string(item.name) || string(item.title) || string(item.label) || string(item.source_name);
    if (!url && !label) return [];
    const key = url || label;
    if (seen.has(key)) return [];
    seen.add(key);
    return [{url, label: label || serviceName(new URL(url)) || "Источник", checkedAt: string(item.checked_at)}];
  });
}

function sourcesDisclosure(value, title = "Источники") {
  const sources = sourceEntries(value);
  if (!sources.length) return null;
  const details = node("details", "sources");
  details.append(node("summary", "", `${title} (${sources.length})`));
  const list = node("ul");
  for (const source of sources) {
    const item = node("li");
    item.append(link(source.label, source.url) || node("span", "", source.label));
    if (source.checkedAt) item.append(node("span", "source-checked", `Проверено: ${dateLabel(source.checkedAt)}`));
    list.append(item);
  }
  details.append(list);
  return details;
}

function isRedWings(leg) {
  return leg.mode === "plane" && (/red\s*wings|р[еэ]д\s*вингс|^(?:WZ|RWZ)$/i.test(string(leg.carrier)) || /^(?:WZ|RWZ)$/i.test(string(leg.carrier_iata)) || /^(?:WZ|RWZ)\s*\d/i.test(string(leg.number)));
}

function renderLeg(leg, networkMode) {
  if (!object(leg) || !Object.hasOwn(modes, leg.mode) || !string(leg.origin) || !string(leg.destination)) return null;
  const row = node("li", `leg${isRedWings(leg) ? " leg-rw" : ""}`);
  const marker = node("span", "leg-icon");
  marker.append(transportIcon(leg.mode));
  const content = node("div");
  const top = node("div", "leg-top");
  const label = [modes[leg.mode], string(leg.carrier), string(leg.number)].filter(Boolean).join(" · ");
  const evidence = Object.hasOwn(evidenceLabels, leg.evidence_status) ? leg.evidence_status : "unknown";
  const projectedFlight = networkMode === "scenario_2027_2028" && isRedWings(leg);
  const badge = node("span", "leg-evidence", projectedFlight ? "Проектируемый рейс" : evidenceLabels[evidence]);
  badge.dataset.evidence = evidence;
  top.append(node("span", "leg-mode", label));
  if (projectedFlight) top.append(badge);
  content.append(top, node("p", "leg-route", `${leg.origin} → ${leg.destination}`));
  if (string(leg.departure) || string(leg.arrival)) {
    const times = node("dl", "leg-times");
    for (const [title, value] of [["Отправление", leg.departure], ["Прибытие", leg.arrival]]) {
      const item = node("div");
      const description = node("dd");
      if (string(value)) {
        const time = node("time", "", dateLabel(value));
        // Invalid datetime attributes are avoided when a source returns prose.
        if (/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$/.test(value)) time.dateTime = value;
        description.append(time);
      } else description.textContent = "Уточняется";
      item.append(node("dt", "", title), description);
      times.append(item);
    }
    content.append(times);
  } else content.append(node("p", "leg-meta", "Время уточняется"));

  const metadata = node("div", "leg-meta");
  if (number(leg.duration_minutes)) metadata.append(node("span", "", durationLabel(leg.duration_minutes)));
  if (number(leg.price) && leg.currency === "RUB") {
    const basis = leg.price_basis === "person" ? " / чел." : leg.price_basis === "party" ? " за всех пассажиров" : " · единица тарифа не указана";
    metadata.append(node("span", "", `${rubles.format(leg.price)}${basis}`));
  }
  if (leg.overnight === true) metadata.append(node("span", "", "С ночёвкой"));
  if (metadata.childElementCount) content.append(metadata);
  if (string(leg.baggage_note)) content.append(node("p", "leg-note", leg.baggage_note));
  const actions = renderActions(leg.links);
  if (actions) content.append(actions);
  else if (safeUrl(leg.source_url)) {
    content.append(renderActions([{label: "Сведения об участке", url: leg.source_url}]));
  }
  row.append(marker, content);
  return row;
}

function renderConnection(connection, previous, next) {
  if (!object(connection)) return null;
  const note = node("div", "connection");
  const gap = number(connection.available_minutes) ? connection.available_minutes : null;
  if (gap === null) return null;
  const minimum = number(connection.minimum_minutes) ? connection.minimum_minutes : null;
  const nextDay = /^\d{4}-\d{2}-\d{2}T/.test(string(previous.arrival)) && /^\d{4}-\d{2}-\d{2}T/.test(string(next.departure)) && previous.arrival.slice(0, 10) < next.departure.slice(0, 10);
  const longWait = gap !== null && gap > 300;
  const verified = connection.status === "verified" && gap !== null && minimum !== null && gap >= minimum;
  note.dataset.status = !verified ? "unknown" : longWait || nextDay ? "long" : "verified";
  const title = nextDay ? "Ожидание до следующего дня" : longWait ? "Долгое ожидание" : "Стыковка";
  note.append(node("strong", "", `${title} · ${durationLabel(gap)}`));
  return note;
}

function renderConnectionChecks(checks) {
  if (!object(checks)) return null;
  const hasSlack = typeof checks.slack_minutes === "number" && Number.isFinite(checks.slack_minutes);
  if (!hasSlack) return null;
  const section = node("section", "connection-checks");
  section.setAttribute("aria-label", "Расчёт запаса на пересадку");
  const title = `${checks.slack_minutes < 0 ? "Дефицит времени" : checks.method === "conservative_interval" ? "Расчётный запас" : "Запас на пересадку"}: ${durationLabel(Math.abs(checks.slack_minutes))}`;
  section.append(node("h4", "", title));
  const times = node("dl", "leg-times");
  for (const [label, value] of [["Готовность к пересадке", checks.ready_at], ["Отправление", checks.departure_at]]) {
    if (!string(value)) continue;
    const row = node("div");
    row.append(node("dt", "", label), node("dd", "", dateLabel(value)));
    times.append(row);
  }
  if (times.childElementCount) section.append(times);
  return section;
}

function renderTransfers(plan) {
  const priority = {available: 0, unverified: 1, target: 2};
  const options = array(plan.transfer_options).filter(object).sort((a, b) => Number(b.recommended === true && b.status === "available") - Number(a.recommended === true && a.status === "available") || (priority[a.status] ?? 3) - (priority[b.status] ?? 3));
  if (!options.length) return null;
  const section = node("section", "transfer-options");
  section.setAttribute("aria-label", "Варианты наземного доезда");
  section.append(node("h4", "", "Наземный доезд"));
  const list = node("ul", "transfer-list");
  for (const option of options) {
    const target = option.status === "target";
    const available = option.status === "available";
    const item = node("li", "transfer-option");
    const heading = node("div", "transfer-heading");
    heading.append(node("h5", "", target ? smartTransferTitle : string(option.title) || "Общественный транспорт"));
    heading.append(node("span", "transfer-status", target ? "Целевой сервис" : available ? "Доступный сервис" : "Доступность не подтверждена"));
    item.append(heading);
    if (available && option.recommended === true && string(option.recommendation_badge)) item.append(node("strong", "partner-recommendation", option.recommendation_badge));
    if (string(option.description)) item.append(node("p", "", option.description));
    item.append(node("p", "transfer-duration", number(option.duration_minutes) ? `Время в пути: ${durationLabel(option.duration_minutes)}` : "Время в пути не подтверждено"));
    if (target) {
      item.append(node("p", "leg-note", "Бронирование пока недоступно."));
      const sources = sourcesDisclosure(option.links, "О сервисе");
      if (sources) item.append(sources);
    } else {
      const actions = renderActions(option.links);
      if (actions) item.append(actions);
    }
    list.append(item);
  }
  section.append(list);
  const compare = node("button", "text-button transfer-compare", "Сравнить общественный транспорт и Умный трансфер");
  compare.type = "button";
  compare.addEventListener("click", () => {
    fillMessage(`Сравни общественный транспорт и Умный трансфер для этой поездки${string(plan.title) ? `\nВариант: ${plan.title}` : ""}`);
  });
  section.append(compare);
  return section;
}

function renderBasket(basket) {
  if (!object(basket)) return null;
  const details = node("details", "basket");
  details.open = true;
  const summary = node("summary");
  summary.append(node("span", "", "Оформление в одной корзине"), node("span", "basket-status", basket.status === "not_connected" ? "Не подключено" : "Подключение не подтверждено"));
  details.append(summary, node("p", "", basket.status === "not_connected" ? string(basket.description) || basketDescription : "Подключение партнёрского оформления не подтверждено. Билеты оформляются отдельно."));
  const sources = sourcesDisclosure(basket.links, "Об интеграции");
  if (sources) details.append(sources);
  return details;
}

function renderPlan(plan, variant) {
  if (!object(plan)) return null;
  const card = node("section", `plan${plan.requires_red_wings === true ? " plan-rw" : plan.requires_red_wings === false ? " plan-baseline" : ""}`);
  const heading = node("div", "plan-heading");
  const labels = node("div", "plan-labels");
  const kind = plan.requires_red_wings === true ? `С Red Wings${variant ? ` · вариант ${variant}` : ""}` : plan.requires_red_wings === false ? "Наземный вариант" : "Участие Red Wings не уточнено";
  const scenario = plan.network_mode === "scenario_2027_2028";
  labels.append(node("span", "plan-kind", kind));
  const network = node("span", "network-badge", Object.hasOwn(networkLabels, plan.network_mode) ? networkLabels[plan.network_mode] : "Режим сети не указан");
  network.dataset.mode = Object.hasOwn(networkLabels, plan.network_mode) ? plan.network_mode : "unknown";
  heading.append(labels);
  if (scenario) heading.append(network);
  heading.append(node("h3", "", string(plan.title) || "Маршрут"));

  const reason = plan.reasonableness;
  if (object(reason) && reason.status === "detour") {
    const note = node("div", "reasonableness");
    note.dataset.status = ["reasonable", "detour", "unknown"].includes(reason.status) ? reason.status : "unknown";
    if (reason.status === "detour") note.append(node("strong", "", "Маршрут с крюком"));
    heading.append(note);
  }
  card.append(heading);

  const totals = node("dl", "plan-totals");
  for (const [title, value, format, unknown] of [
    ["Вся поездка", plan.total_duration_minutes, durationLabel, "—"],
    ["Стоимость", plan.currency === "RUB" ? plan.total_price : null, (price) => rubles.format(price), "На сайте перевозчика"],
  ]) {
    const item = node("div");
    item.append(node("dt", "", title), node("dd", number(value) ? "" : "unknown", number(value) ? format(value) : unknown));
    totals.append(item);
  }
  card.append(totals);

  const legs = node("ol", "legs");
  const planLegs = array(plan.legs);
  for (let index = 0; index < planLegs.length; index++) {
    const leg = planLegs[index];
    const rendered = renderLeg(leg, plan.network_mode);
    if (rendered) {
      const next = planLegs[index + 1];
      const connection = object(next) && string(leg.id) && string(next.id)
        ? array(plan.connections).find((item) => object(item) && item.from_leg === leg.id && item.to_leg === next.id)
        : null;
      const notice = renderConnection(connection, leg, next);
      if (notice) rendered.lastElementChild.append(notice);
      legs.append(rendered);
    }
  }
  if (legs.childElementCount) card.append(legs);
  const checks = renderConnectionChecks(plan.connection_checks);
  if (checks) card.append(checks);
  const transfers = renderTransfers(plan);
  if (transfers) card.append(transfers);
  const basket = plan.basket?.status === "not_connected" ? null : renderBasket(plan.basket);
  if (basket) card.append(basket);
  const sources = sourcesDisclosure([
    ...planLegs.filter((leg) => object(leg) && (safeUrl(leg.source_url) || string(leg.source_name))).map((leg) => ({name: `${leg.origin || "Участок"} → ${leg.destination || "пункт назначения"} · ${string(leg.source_name) || "источник"}`, url: leg.source_url, checked_at: leg.checked_at})),
    ...array(plan.sources),
    ...array(plan.connections).filter((connection) => object(connection) && safeUrl(connection.source_url)).map((connection) => ({name: "Норматив стыковки", url: connection.source_url})),
  ]);
  if (sources) card.append(sources);
  return card;
}

const tripLabels = {
  city: "Город", address: "Адрес", title: "Место", name: "Название", station: "Станция", airport: "Аэропорт",
  from: "С", to: "По", start: "С", end: "По", date_from: "С", date_to: "По",
  earliest: "Не раньше", latest: "Не позже", kind: "Период", type: "Тип", meaning: "Значение периода",
  adults: "Взрослые", children: "Дети", count: "Количество", ages: "Возраст детей",
  checked: "Багаж", hand: "Ручная кладь", description: "Условия", amount: "Сумма", currency: "Валюта",
  taxi: "Такси", train: "Поезд", bus: "Автобус", overnight: "Ночёвка", night_travel: "Ночной переезд",
  allow_taxi: "Такси", allow_overnight: "Ночёвка", allow_night_travel: "Ночной переезд",
};
const tripValues = {
  unknown: "Не уточнено", departure_window: "Окно выезда", departure: "Выезд", travel_window: "Период поездки",
  trip_dates: "Даты поездки", round_trip: "Туда и обратно", one_way: "В одну сторону",
  allowed: "Допустимо", forbidden: "Не подходит", required: "Обязательно", preferred: "Предпочтительно", optional: "По возможности",
  RUB: "₽",
  outbound_return: "Даты поездки туда и обратно", public: "Общественный транспорт", smart_transfer: "Умный трансфер",
};

function tripValue(value, depth = 0) {
  if (value === null || value === undefined || value === "") return "Не уточнено";
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "Не уточнено";
  if (typeof value === "string") return Object.hasOwn(tripValues, value) ? tripValues[value] : dateLabel(value);
  if (depth > 2) return "";
  if (Array.isArray(value)) return value.map((item) => tripValue(item, depth + 1)).filter(Boolean).join(", ") || "Не уточнено";
  if (!object(value)) return "";
  return Object.entries(value).flatMap(([key, item]) => {
    if (!Object.hasOwn(tripLabels, key)) return [];
    const display = tripValue(item, depth + 1);
    return display ? [`${tripLabels[key]}: ${display}`] : [];
  }).join("; ");
}

function updateTrip(trip) {
  if (!object(trip)) return;
  const core = value => JSON.stringify([value?.origin, value?.destination, value?.date_range]);
  if (core(trip) !== core(currentTrip)) editorInitialized = false;
  currentTrip = trip;
  const fields = [
    ["Откуда", ["origin", "origin_city", "from"]],
    ["Адрес отправления", ["origin_address"]],
    ["Куда", ["destination", "destination_city", "to"]],
    ["Адрес назначения", ["destination_address"]],
    ["Период", ["period", "date_window", "departure_window", "date_range", "dates"]],
    ["Значение периода", ["period_kind", "period_meaning", "date_window_kind"]],
    ["Не раньше", ["date_from", "departure_from"]],
    ["Не позже", ["date_to", "departure_to"]],
    ["Возвращение", ["return_date", "return_window"]],
    ["Прибыть к", ["latest_arrival", "arrival_deadline", "arrive_by"]],
    ["Пассажиры", ["passengers", "travelers"]],
    ["Багаж", ["baggage", "luggage"]],
    ["Такси допустимо", ["allow_taxi", "taxi_allowed"]],
    ["Поезд допустим", ["allow_train", "train_allowed"]],
    ["Ночной переезд допустим", ["allow_night_travel", "allow_overnight_travel"]],
    ["Ночёвка допустима", ["allow_overnight", "allow_overnight_stay"]],
    ["Бюджет", ["budget", "budget_rub"]],
    ["Red Wings обязателен", ["requires_red_wings", "require_red_wings", "red_wings_required"]],
    ["Условия", ["constraints", "preferences"]],
  ];
  const rows = fields.flatMap(([label, keys]) => {
    const key = keys.find((candidate) => Object.hasOwn(trip, candidate));
    if (!key) return [];
    const value = tripValue(trip[key]);
    return value ? [{label, value}] : [];
  });
  elements.tripFields.replaceChildren();
  elements.tripRegion.hidden = !rows.length;
  for (const row of rows) elements.tripFields.append(node("dt", "", row.label), node("dd", "", row.value));
  const origin = rows.find((row) => row.label === "Откуда");
  const destination = rows.find((row) => row.label === "Куда");
  elements.tripPreview.textContent = origin && destination ? `${origin.value} → ${destination.value}` : "";
}

function renderReply(data, {concise = false} = {}) {
  const demo = object(data.demo) ? data.demo : null;
  const article = appendMessage("assistant", "", demo && data.reply_origin === "prepared" ? "Сохранённый пример" : undefined);
  if (demo) {
    article.append(node("h2", "demo-title", string(demo.label) || "Пример поездки"));
    article.append(demoMetadata(demo));
  }
  const hasPlans = array(data.plans).length > 0;
  const reply = concise && hasPlans ? string(data.reply).split(/\n\s*\n/)[0] : data.reply;
  if (string(reply) && !(hasPlans && data.reply_origin === "prepared")) article.append(node("p", "message-body", reply));
  const plans = array(data.plans).filter(object).filter(plan => plan.requires_red_wings === true && array(plan.legs).some(leg => leg.mode === "plane" && leg.carrier_iata === "WZ")).filter(plan => array(plan.legs).every(leg => leg.mode !== "plane" ||
    (leg.carrier_iata === "WZ" || Number(leg.carrier_code) === 617) && (leg.carrier_code == null || Number(leg.carrier_code) === 617) && (!leg.carrier_iata || leg.carrier_iata === "WZ")));
  if (plans.length) {
    const group = node("div", "plan-list");
    group.setAttribute("aria-label", "Варианты поездки");
    let rwCount = 0;
    const displayed = plans.filter((plan) => plan.requires_red_wings !== true || ++rwCount <= 3);
    const modeOf = (plan) => Object.hasOwn(networkLabels, plan.network_mode) ? plan.network_mode : "unknown";
    const modes = ["current", "scenario_2027_2028", "unknown"].filter((mode) => displayed.some((plan) => modeOf(plan) === mode));
    for (const mode of modes) {
      const networkGroup = node("section", "network-group");
      const networkTitle = networkLabels[mode] || "Режим сети не указан";
      networkGroup.setAttribute("aria-label", networkTitle);
      if (modes.length > 1) networkGroup.append(node("p", "network-heading", networkTitle));
      const inNetwork = displayed.filter((plan) => modeOf(plan) === mode);
      for (const [kind, title] of [[true, "Маршруты с Red Wings"], [false, "Наземные варианты"], [null, "Участие Red Wings не уточнено"]]) {
        const matches = inNetwork.filter((plan) => (typeof plan.requires_red_wings === "boolean" ? plan.requires_red_wings : null) === kind);
        if (!matches.length) continue;
        const section = node("section", "plan-group");
        section.setAttribute("aria-label", title);
        section.append(node("p", "plan-group-title", title));
        matches.forEach((plan, index) => section.append(renderPlan(plan, kind === true ? index + 1 : null)));
        networkGroup.append(section);
      }
      group.append(networkGroup);
    }
    if (rwCount > 3) group.append(node("p", "plan-limit", "Показаны первые 3 варианта с Red Wings из ответа."));
    article.append(group);
  }
  const sources = sourcesDisclosure(data.sources);
  if (sources) article.append(sources);
  const suggestions = array(data.suggestions).filter((value) => string(value)).slice(0, 3);
  if (suggestions.length) {
    const group = node("div", "suggestions");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Продолжить обсуждение");
    for (const suggestion of suggestions) {
      const button = node("button", "chip", suggestion);
      button.type = "button";
      button.addEventListener("click", () => fillMessage(suggestion));
      group.append(button);
    }
    activeSuggestions = group;
    article.append(group);
  }
}

const placeKinds = {city: "Город", station: "Станция", airport: "Аэропорт"};

function createPlacePicker(prefix, changed = () => {}) {
  const input = $(`#${prefix === "flight-from" ? prefix : `${prefix}-place`}`);
  const list = $(`#${prefix}-options`);
  const status = $(`#${prefix}-status`);
  let selected = null, options = [], active = -1, timer = null, controller = null, revision = 0;
  const context = (place) => [placeKinds[place.kind], string(place.city) !== string(place.title) ? string(place.city) : "", string(place.region)].filter(Boolean).join(" · ");
  function close() {
    list.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    active = -1;
  }
  function stop() { clearTimeout(timer); timer = null; controller?.abort(); controller = null; revision++; list.removeAttribute("aria-busy"); }
  function choose(place) {
    stop();
    selected = place;
    input.value = place.title;
    input.setCustomValidity("");
    status.textContent = context(place);
    close();
    changed(place);
    input.focus();
  }
  function highlight(index) {
    active = index;
    for (const [i, item] of [...list.children].entries()) item.setAttribute("aria-selected", String(i === active));
    if (active >= 0) {
      input.setAttribute("aria-activedescendant", list.children[active].id);
      list.children[active].scrollIntoView({block: "nearest"});
    }
  }
  async function search(query, version) {
    timer = null;
    controller = new AbortController();
    const signal = controller.signal;
    status.textContent = "Ищу места…";
    list.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(`api-v3/places?q=${encodeURIComponent(query)}`, {headers: {Accept: "application/json"}, credentials: "same-origin", cache: "no-store", signal});
      const data = await response.json();
      if (signal.aborted || version !== revision) return;
      if (!response.ok || !object(data) || data.status === "error" || !Array.isArray(data.places) || data.places.some(place => !object(place) || !string(place.id) || !string(place.title))) throw new Error("places");
      options = data.places;
      list.replaceChildren(...options.map((place, index) => {
        const item = node("li", "place-option");
        item.id = `${prefix}-option-${index}`;
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", "false");
        item.append(node("span", "place-title", place.title), node("span", "place-context", context(place)));
        item.addEventListener("pointerdown", event => event.preventDefault());
        item.addEventListener("click", () => choose(place));
        return item;
      }));
      list.hidden = !options.length || document.activeElement !== input;
      input.setAttribute("aria-expanded", String(!list.hidden));
      status.textContent = options.length ? `Найдено: ${options.length}` : "Место не найдено. Уточните название или регион.";
    } catch (error) {
      if (!signal.aborted && version === revision) { close(); status.textContent = "Не удалось найти места. Измените запрос, чтобы повторить поиск."; }
    } finally { if (version === revision) { controller = null; list.removeAttribute("aria-busy"); } }
  }
  function edit() {
    stop();
    selected = null;
    options = [];
    close();
    input.setCustomValidity("");
    changed(null);
    const query = input.value.trim();
    status.textContent = query.length === 1 ? "Введите хотя бы 2 символа." : "";
    if (query.length >= 2) {
      const version = revision;
      timer = setTimeout(() => search(query, version), 300);
    }
  }
  input.addEventListener("input", event => { if (!event.isComposing) edit(); });
  input.addEventListener("compositionstart", stop);
  input.addEventListener("compositionend", edit);
  input.addEventListener("focus", () => {
    syncViewport();
    if (options.length && !selected) { list.hidden = false; input.setAttribute("aria-expanded", "true"); }
    else if (!selected && !controller && input.value.trim().length >= 2) {
      clearTimeout(timer);
      const version = revision;
      timer = setTimeout(() => search(input.value.trim(), version), 300);
    }
  });
  input.addEventListener("blur", () => { close(); syncViewport(); });
  input.addEventListener("keydown", (event) => {
    if (event.isComposing) return;
    if ((event.key === "ArrowDown" || event.key === "ArrowUp") && options.length) {
      event.preventDefault();
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      highlight(event.key === "ArrowDown" ? (active + 1) % options.length : (active <= 0 ? options.length : active) - 1);
    } else if (event.key === "Enter" && !list.hidden) {
      event.preventDefault();
      if (active >= 0) choose(options[active]);
    } else if (event.key === "Escape" && !list.hidden) { event.preventDefault(); event.stopPropagation(); close(); }
  });
  return {
    input, get selected() { return selected; }, close,
    prefill(value) { stop(); selected = null; options = []; input.value = string(value); status.textContent = ""; input.setCustomValidity(""); close(); },
    valid() { input.setCustomValidity(selected ? "" : "Выберите место из подсказок."); if (!selected) { input.focus(); input.reportValidity(); } return !!selected; },
  };
}

const originPicker = createPlacePicker("origin");
const destinationPicker = createPlacePicker("destination");
const flightFromPicker = createPlacePicker("flight-from", () => { resetFlights(); if (flightFromPicker.selected && elements.hasFlight.checked) loadFlights(); });

function resetFlights() {
  flightsController?.abort();
  flights = [];
  elements.flightOptions.replaceChildren(node("option", "", "Выберите точку вылета и дату"));
  elements.flightOptions.firstElementChild.value = "";
  elements.flightOptions.value = "";
  elements.flightOptions.disabled = true;
  elements.flightOptions.setCustomValidity("");
  elements.flightDetail.replaceChildren();
  elements.flightDetail.hidden = true;
  elements.flightsStatus.textContent = "";
  elements.reloadFlights.hidden = true;
}

async function loadFlights() {
  resetFlights();
  const from = flightFromPicker.selected;
  const date = elements.flightDate.value;
  if (!elements.hasFlight.checked || !from || !date) return;
  flightsController = new AbortController();
  const signal = flightsController.signal;
  elements.flightsStatus.textContent = "Ищу рейсы Red Wings…";
  try {
    const airportArea = from.kind === "station" ? string(from.place_id) || from.id : from.id;
    const response = await fetch(`api-v3/flights?from=${encodeURIComponent(airportArea)}&date=${encodeURIComponent(date)}`, {headers: {Accept: "application/json"}, credentials: "same-origin", cache: "no-store", signal});
    const data = await response.json();
    if (signal.aborted) return;
    if (!response.ok || !object(data) || data.status === "error" || !Array.isArray(data.flights) || data.flights.some(flight => !object(flight) || !string(flight.id) || !string(flight.number))) throw new Error("flights");
    flights = data.flights;
    const incomplete = data.status === "unavailable" || data.status === "partial";
    const placeholder = node("option", "", flights.length ? "Выберите рейс" : incomplete ? "Список пока недоступен" : "Рейсы не найдены");
    placeholder.value = "";
    elements.flightOptions.replaceChildren(placeholder, ...flights.map(flight => {
      const option = node("option", "", `${flight.number} · ${string(flight.origin?.title) || string(flight.origin?.city)} → ${string(flight.destination?.title) || string(flight.destination?.city)} · ${dateLabel(flight.departure || flight.date)}`);
      option.value = flight.id;
      return option;
    }));
    elements.flightOptions.disabled = !flights.length;
    elements.flightsStatus.textContent = incomplete ? string(data.message) || "Расписание проверено не полностью; отсутствие рейса в списке не означает, что его нет." : flights.length ? "" : "В проверенных табло на эту дату рейсы Red Wings не найдены. Попробуйте другую точку или дату.";
    elements.reloadFlights.hidden = !incomplete;
  } catch (error) {
    if (!signal.aborted) {
      elements.flightsStatus.textContent = "Не удалось загрузить рейсы. Данные о расписании недоступны.";
      elements.reloadFlights.hidden = false;
    }
  }
}

function renderSelectedFlight() {
  elements.flightOptions.setCustomValidity("");
  const flight = flights.find(item => item.id === elements.flightOptions.value);
  elements.flightDetail.replaceChildren();
  elements.flightDetail.hidden = !flight;
  if (!flight) return;
  elements.flightDetail.append(node("p", "", `${flight.number} · ${string(flight.origin?.title)} → ${string(flight.destination?.title)}`));
  elements.flightDetail.append(node("p", "", `Вылет: ${dateLabel(flight.departure)}\nПрилёт: ${string(flight.arrival) ? dateLabel(flight.arrival) : "не подтверждён"}`));
  const sources = sourcesDisclosure([{name: "Расписание рейса", url: flight.source_url, checked_at: flight.checked_at}]);
  if (sources) elements.flightDetail.append(sources);
}

function toggleFlexibleDates() {
  const flexible = elements.flexibleDates.checked;
  elements.dateToField.hidden = !flexible;
  elements.dateTo.disabled = !flexible;
  elements.dateTo.required = flexible;
  elements.dateTo.min = elements.dateFrom.value;
  elements.dateTo.setCustomValidity("");
  $("#date-from-label").textContent = flexible ? "Первая дата выезда" : "Дата выезда";
}

function openTripEditor() {
  if (busy) return;
  if (!editorInitialized) {
    elements.replaceConfirm.hidden = true;
    elements.startTrip.hidden = false;
    elements.tripFormError.hidden = true;
    if (editorSessionId !== sessionId) elements.tripWishes.value = "";
    elements.tripWishes.setCustomValidity("");
    originPicker.prefill(currentTrip?.origin?.city);
    destinationPicker.prefill(currentTrip?.destination?.city);
    elements.originAddress.value = string(currentTrip?.origin?.address);
    elements.destinationAddress.value = string(currentTrip?.destination?.address);
    elements.dateFrom.value = string(currentTrip?.date_range?.from);
    elements.dateTo.value = string(currentTrip?.date_range?.to);
    elements.flexibleDates.checked = !!elements.dateTo.value && elements.dateTo.value !== elements.dateFrom.value;
    toggleFlexibleDates();
    flightFromPicker.prefill("");
    elements.flightDate.value = "";
    elements.hasFlight.checked = false;
    toggleFlightFields();
    editorInitialized = true;
    editorSessionId = sessionId;
  }
  elements.tripDialog.showModal();
  originPicker.input.focus();
}

function toggleFlightFields() {
  const enabled = elements.hasFlight.checked;
  elements.flightFields.hidden = !enabled;
  flightFromPicker.input.required = enabled;
  flightFromPicker.input.disabled = !enabled;
  flightFromPicker.input.setCustomValidity("");
  elements.flightDate.required = enabled;
  elements.flightDate.disabled = !enabled;
  elements.flightOptions.required = enabled;
  if (enabled) {
    if (!elements.flightDate.value) elements.flightDate.value = elements.dateFrom.value;
    loadFlights();
  } else resetFlights();
}

function tripStartBody() {
  if (!originPicker.valid() || !destinationPicker.valid()) return null;
  elements.dateTo.setCustomValidity("");
  const wishes = elements.tripWishes.value.trim();
  elements.tripWishes.setCustomValidity(wishes.length > 2000 ? "Пожелания должны быть не длиннее 2000 символов." : "");
  if (elements.flexibleDates.checked && elements.dateTo.value < elements.dateFrom.value) elements.dateTo.setCustomValidity("Последняя дата выезда должна быть не раньше первой.");
  if (elements.hasFlight.checked) {
    if (!flightFromPicker.valid()) return null;
    const flight = flights.find(item => item.id === elements.flightOptions.value);
    if (!flight) {
      elements.tripFormError.textContent = "Выберите рейс из загруженного расписания. Если поиск недоступен, попробуйте другую дату или точку вылета.";
      elements.tripFormError.hidden = false;
      (elements.flightOptions.disabled ? flightFromPicker.input : elements.flightOptions).focus();
      return null;
    }
  }
  if (!elements.tripForm.reportValidity()) return null;
  const body = {origin_id: originPicker.selected.id, destination_id: destinationPicker.selected.id, date_from: elements.dateFrom.value};
  if (elements.flexibleDates.checked) body.date_to = elements.dateTo.value;
  if (elements.hasFlight.checked) body.flight_option_id = elements.flightOptions.value;
  if (elements.originAddress.value.trim()) body.origin_address = elements.originAddress.value.trim();
  if (elements.destinationAddress.value.trim()) body.destination_address = elements.destinationAddress.value.trim();
  if (wishes) body.wishes = wishes;
  return body;
}

async function startTrip(body) {
  if (busy || !body) return;
  busy = true;
  tripStarting = true;
  elements.tripInputs.disabled = true;
  elements.startTrip.disabled = true;
  elements.confirmTripStart.disabled = true;
  elements.cancelTripStart.disabled = true;
  elements.closeTrip.disabled = true;
  elements.tripFormError.hidden = true;
  elements.tripFormStatus.hidden = false;
  elements.tripFormStatus.textContent = "Проверяю расписание и собираю маршрут…";
  elements.tripForm.setAttribute("aria-busy", "true");
  setDemoButtonsDisabled(true);
  resizeInput();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 240000);
  let started = false;
  try {
    // The form starts a server-side search. Never replay an ambiguously accepted POST.
    const response = await fetch("api-v3/chat/start", {method: "POST", headers: {"Content-Type": "application/json", Accept: "application/json"}, credentials: "same-origin", cache: "no-store", body: JSON.stringify(body), signal: controller.signal});
    let data;
    try { data = await response.json(); } catch { throw new Error("Ответ не удалось прочитать. Маршрут мог быть рассчитан; текущий диалог и параметры сохранены."); }
    if (!response.ok || data?.status === "error") throw new Error(string(data?.reply) || string(data?.message) || "Не удалось рассчитать маршрут. Параметры сохранены.");
    if (!object(data) || !["ok", "partial", "needs_input"].includes(data.status) || !string(data.session_id) || typeof data.reply !== "string" || !object(data.trip) || !Array.isArray(data.plans)) throw new Error("Ответ неполный. Маршрут мог быть рассчитан; текущий диалог и параметры сохранены.");
    if (data.reply_origin === "planner") {
      elements.tripFormStatus.textContent = "Агент разбирает найденные варианты…";
      data = await analyzePrepared(data, controller.signal, "Кратко предложи лучший из найденных вариантов: маршрут, время и запас на пересадку. Если вариантов нет, предложи следующий шаг. Не повторяй поиск. Без технических оговорок о прототипе, снимках, источниках, ценах и проверках. Не повторяй содержимое карточек.");
    }
    const newDraft = elements.input.value;
    clearConversation();
    elements.input.value = newDraft;
    sessionId = data.session_id;
    hasMessages = true;
    elements.welcome.hidden = true;
    elements.demoGallery.open = false;
    updateTrip(data.trip);
    editorInitialized = true;
    editorSessionId = sessionId;
    if (body.wishes) appendMessage("user", body.wishes, "Ваши пожелания");
    renderReply(data, {concise: true});
    started = true;
  } catch (error) {
    elements.tripFormError.textContent = error instanceof TypeError || error?.name === "AbortError"
      ? "Ответ не получен. Маршрут мог быть рассчитан; текущий диалог и параметры сохранены."
      : error instanceof Error ? error.message : "Не удалось рассчитать маршрут. Параметры сохранены.";
    elements.tripFormError.hidden = false;
  } finally {
    clearTimeout(timeout);
    busy = false;
    tripStarting = false;
    elements.tripInputs.disabled = false;
    elements.startTrip.disabled = false;
    elements.confirmTripStart.disabled = false;
    elements.cancelTripStart.disabled = false;
    elements.closeTrip.disabled = false;
    elements.tripFormStatus.hidden = true;
    elements.tripFormStatus.textContent = "";
    elements.tripForm.removeAttribute("aria-busy");
    setDemoButtonsDisabled(false);
    resizeInput();
    if (started) {
      elements.replaceConfirm.hidden = true;
      elements.startTrip.hidden = false;
      elements.tripDialog.close();
      elements.input.focus();
      scrollToEnd();
    }
  }
}

async function sendMessage(event) {
  event.preventDefault();
  if (busy || composing || offlineDemo) return;
  const message = elements.input.value.trim();
  if (!message) return;
  busy = true;
  hasMessages = true;
  clearError();
  activeSuggestions?.remove();
  activeSuggestions = null;
  elements.welcome.hidden = true;
  elements.demoGallery.open = false;
  appendMessage("user", message);
  elements.input.value = "";
  resizeInput();
  elements.input.focus();
  elements.newDialog.disabled = true;
  setDemoButtonsDisabled(true);
  elements.form.setAttribute("aria-busy", "true");
  const loading = node("div", "loading", "Готовлю ответ…");
  loading.setAttribute("role", "status");
  elements.messages.append(loading);
  scrollToEnd();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 240000);
  let followResponse = false;
  try {
    if (offlineSeedId && !sessionId) {
      const seed = await seedDemo(offlineSeedId, controller.signal);
      sessionId = seed.session_id;
      offlineSeedId = null;
    }
    const styledMessage = `${message}\n\nФормат ответа: результат поездки и полезное следующее действие. Без длинных технических оговорок о прототипе, сохранённых снимках и проверках источников. Не повторяй справочную информацию из карточек.`;
    const body = {message: styledMessage.length <= 4000 ? styledMessage : message};
    if (sessionId) body.session_id = sessionId;
    // Never automatically replay a POST: a lost response may have been accepted.
    const response = await fetch("api-v3/chat", {
      method: "POST", headers: {"Content-Type": "application/json", Accept: "application/json"},
      credentials: "same-origin", cache: "no-store", body: JSON.stringify(body), signal: controller.signal,
    });
    let data;
    try { data = await response.json(); }
    catch { throw new Error("Ответ не удалось прочитать. Сообщение могло быть обработано."); }
    followResponse = nearEnd();
    if (object(data) && string(data.session_id)) sessionId = data.session_id;
    const valid = object(data) && ["ok", "needs_input", "partial", "error"].includes(data.status) && typeof data.reply === "string";
    if (!valid) throw new Error("Сервис вернул неполный ответ. Сообщение могло быть обработано.");
    if (!response.ok || data.status === "error") {
      if (object(data.trip)) updateTrip(data.trip);
      showChatError(string(data.reply) || "Не удалось получить ответ. Продолжите диалог позже.");
    } else {
      if (!sessionId) throw new Error("Не удалось продолжить диалог: в ответе нет сессии. Начните новый диалог.");
      updateTrip(data.trip);
      renderReply(data);
    }
  } catch (error) {
    followResponse = nearEnd();
    const message = error instanceof TypeError || error?.name === "AbortError"
      ? "Ответ не получен. Сообщение могло быть обработано."
      : error instanceof Error ? error.message : "Не удалось получить ответ.";
    showChatError(message);
  } finally {
    clearTimeout(timeout);
    loading.remove();
    busy = false;
    elements.form.removeAttribute("aria-busy");
    setDemoButtonsDisabled(false);
    resizeInput();
    if (followResponse) scrollToEnd();
  }
}

function demoMetadata(demo) {
  const metadata = node("span", "demo-metadata");
  const mode = node("span", "demo-mode", dataModeLabels[demo.data_mode] || "Режим данных не указан");
  mode.dataset.mode = demo.data_mode;
  metadata.append(mode, node("span", "demo-checked", string(demo.checked_at) ? `Проверено: ${dateLabel(demo.checked_at)}` : "Дата проверки не указана"));
  return metadata;
}

function setDemoButtonsDisabled(disabled) {
  for (const button of elements.demos.querySelectorAll("button")) button.disabled = disabled;
  elements.offlineDemo.disabled = disabled;
}

function loadOfflineData() {
  offlineDataPromise ??= fetch("demo-snapshots.json", {headers: {Accept: "application/json"}, credentials: "same-origin"})
    .then(async response => {
      const data = await response.json();
      if (!response.ok || !Array.isArray(data.demos) || !object(data.snapshots)) throw new Error("Офлайн-примеры не загрузились.");
      return data;
    }).catch(error => { offlineDataPromise = null; throw error; });
  return offlineDataPromise;
}

function setOfflineDemo(enabled) {
  offlineDemo = enabled;
  elements.offlineDemo.textContent = enabled ? "Включить агента" : "Офлайн-демо";
  elements.offlineDemo.setAttribute("aria-pressed", String(enabled));
  elements.offlineStatus.hidden = !enabled;
  elements.demoExplanation.textContent = enabled
    ? "Сохранённые маршруты без запросов к модели и расписаниям."
    : "Агент разберёт заранее проверенный маршрут. Затем можно уточнить поездку в чате.";
  elements.demoGallery.open = true;
  clearError();
  resizeInput();
}

async function seedDemo(id, signal) {
  const response = await fetch("api-v3/chat/demo", {method: "POST", headers: {"Content-Type": "application/json", Accept: "application/json"}, credentials: "same-origin", cache: "no-store", body: JSON.stringify({id}), signal});
  const data = await response.json();
  if (!response.ok || data?.status === "error" || !string(data.session_id)) throw new Error(string(data?.reply) || "Не удалось открыть сессию примера.");
  return data;
}

async function analyzePrepared(seed, signal, message) {
  // One real Pi turn. Never retry an ambiguously accepted model POST.
  const response = await fetch("api-v3/chat", {method: "POST", headers: {"Content-Type": "application/json", Accept: "application/json"}, credentials: "same-origin", cache: "no-store", body: JSON.stringify({session_id: seed.session_id, message}), signal});
  const data = await response.json();
  if (!response.ok || data?.status === "error" || data?.reply_origin !== "llm" || !string(data.session_id) || typeof data.reply !== "string") throw new Error(string(data?.reply) || "Ответ агента не получен. Запрос мог быть обработан; автоматического повтора нет.");
  return data;
}

function requestReset(demo = null, trigger = document.activeElement) {
  if (busy) return;
  pendingDemo = demo;
  resetTrigger = trigger;
  elements.resetTitle.textContent = demo ? "Открыть другой пример?" : "Начать новый диалог?";
  elements.resetDescription.textContent = demo
    ? `«${demo.label}» откроется в новом диалоге. Текущая переписка и черновик исчезнут с экрана после загрузки примера.`
    : "Текущая переписка и условия поездки будут удалены с этого экрана.";
  elements.confirmReset.textContent = demo ? "Открыть пример" : "Начать новый";
  elements.resetDialog.showModal();
}

function selectDemo(demo, trigger) {
  if (busy) return;
  if (hasMessages || sessionId || elements.input.value.trim()) requestReset(demo, trigger);
  else openDemo(demo, trigger);
}

async function loadDemos() {
  if (demosLoading) return;
  demosLoading = true;
  elements.demosError.hidden = true;
  elements.demosStatus.hidden = false;
  elements.demosStatus.textContent = "Загружаю примеры…";
  elements.demos.setAttribute("aria-busy", "true");
  const restoreFocus = document.activeElement === elements.reloadDemos;
  const local = loadOfflineData().catch(() => null);
  try {
    let data;
    try {
      const response = await fetch("api-v3/demos", {headers: {Accept: "application/json"}, credentials: "same-origin", cache: "no-store"});
      if (!response.ok) throw new Error("demos");
      data = await response.json();
    } catch { data = await local; }
    if (!object(data) || !Array.isArray(data.demos) || data.demos.some((demo) => !object(demo) || !string(demo.id) || !string(demo.label))) throw new Error("demos");
    const cards = data.demos.filter(demo => demo.type !== "ground_baseline").map((demo) => {
      const button = node("button", "demo-card");
      button.type = "button";
      button.disabled = busy;
      button.append(node("span", "demo-label", demo.label), demoMetadata(demo));
      button.addEventListener("click", () => selectDemo(demo, button));
      return button;
    });
    elements.demos.replaceChildren(...cards);
    elements.demosStatus.textContent = cards.length ? "" : "Готовых примеров пока нет. Можно описать свою поездку в сообщении.";
    elements.demosStatus.hidden = !!cards.length;
  } catch {
    elements.demosStatus.hidden = true;
    elements.demosError.hidden = false;
  } finally {
    demosLoading = false;
    elements.demos.removeAttribute("aria-busy");
    if (restoreFocus && elements.demosError.hidden && document.activeElement === elements.reloadDemos) {
      (elements.demos.querySelector("button") || elements.demoGallery.querySelector("summary")).focus();
    }
  }
}

async function openDemo(demo, trigger) {
  if (busy) return;
  clearError();
  busy = true;
  elements.newDialog.disabled = true;
  setDemoButtonsDisabled(true);
  resizeInput();
  elements.welcome.hidden = true;
  elements.demoGallery.open = false;
  const progress = node("div", "loading demo-progress");
  progress.setAttribute("role", "status");
  const progressBody = node("div", "demo-progress-body");
  const progressTitle = node("p", "demo-progress-title", offlineDemo ? "Открываю сохранённый пример…" : "Загружаю данные маршрута…");
  const progressTime = node("p", "demo-progress-time", "Прошло 0 с");
  progressTime.setAttribute("aria-hidden", "true");
  progressBody.append(progressTitle, node("p", "demo-progress-route", demo.label), progressTime);
  progress.append(progressBody);
  elements.messages.append(progress);
  const startedAt = performance.now();
  const progressTimer = setInterval(() => { progressTime.textContent = `Прошло ${Math.floor((performance.now() - startedAt) / 1000)} с`; }, 1000);
  scrollToEnd();
  elements.demos.setAttribute("aria-busy", "true");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 240000);
  const draftAtStart = elements.input.value;
  let opened = false;
  try {
    let data;
    if (offlineDemo) data = (await loadOfflineData()).snapshots[demo.id];
    else {
      data = await seedDemo(demo.id, controller.signal);
      progressTitle.textContent = "Агент разбирает маршрут…";
      data = await analyzePrepared(data, controller.signal, "Кратко предложи вариант этой поездки: маршрут, время и запас на пересадку. Используй данные сессии без нового поиска. Без технических оговорок о прототипе, снимках, источниках, ценах и проверках. Не повторяй содержимое карточек. Для сети 2028 сохрани короткое обозначение сценария.");
    }
    if (!object(data) || !["ok", "partial", "needs_input"].includes(data.status) || (!offlineDemo && !string(data.session_id)) || typeof data.reply !== "string" || !object(data.trip) || !Array.isArray(data.plans) || !object(data.demo) || data.demo.id !== demo.id || !Object.hasOwn(dataModeLabels, data.demo.data_mode)) {
      throw new Error("Сервис вернул неполный пример. Сессия могла быть создана; текущий диалог сохранён.");
    }
    const newDraft = elements.input.value === draftAtStart ? "" : elements.input.value;
    clearConversation();
    elements.input.value = newDraft;
    sessionId = offlineDemo ? null : data.session_id;
    offlineSeedId = offlineDemo ? demo.id : null;
    hasMessages = true;
    elements.welcome.hidden = true;
    elements.demoGallery.open = false;
    updateTrip(data.trip);
    renderReply(data, {concise: true});
    opened = true;
    scrollToEnd();
  } catch (error) {
    const message = error instanceof TypeError || error?.name === "AbortError"
      ? "Ответ с примером не получен. Сессия могла быть создана; текущий диалог сохранён."
      : error instanceof Error ? error.message : "Не удалось открыть пример. Текущий диалог сохранён.";
    showError(message, offlineDemo ? "Выбрать другой пример" : "Открыть офлайн-демо", () => {
      if (!offlineDemo) { setOfflineDemo(true); openDemo(demo, trigger); }
      else { elements.demoGallery.open = true; elements.offlineDemo.focus(); }
    });
  } finally {
    clearTimeout(timeout);
    clearInterval(progressTimer);
    progress.remove();
    busy = false;
    setDemoButtonsDisabled(false);
    elements.demos.removeAttribute("aria-busy");
    elements.demosStatus.hidden = true;
    elements.demosStatus.textContent = "";
    resizeInput();
    if (!opened) {
      elements.welcome.hidden = hasMessages;
      elements.demoGallery.open = true;
      scrollToEnd();
    }
    // Do not steal focus if the person moved to the composer during loading.
    if (opened && (document.activeElement === trigger || document.activeElement === elements.confirmReset || document.activeElement === document.body)) elements.input.focus();
    else if (!opened && document.activeElement === document.body) trigger?.focus();
  }
}

function clearConversation() {
  sessionId = null;
  offlineSeedId = null;
  currentTrip = null;
  editorInitialized = false;
  hasMessages = false;
  activeSuggestions = null;
  elements.messages.replaceChildren();
  elements.tripFields.replaceChildren();
  elements.tripPreview.textContent = "";
  elements.tripDetails.open = false;
  elements.tripRegion.hidden = true;
  elements.welcome.hidden = false;
  elements.input.value = "";
  clearError();
  elements.conversation.scrollTop = 0;
}

function resetConversation() {
  clearConversation();
  elements.demoGallery.open = true;
  resizeInput();
  elements.input.focus();
}

elements.form.addEventListener("submit", sendMessage);
elements.openTrip.addEventListener("click", openTripEditor);
elements.closeTrip.addEventListener("click", () => { if (!tripStarting) elements.tripDialog.close(); });
elements.tripDialog.addEventListener("cancel", event => { if (tripStarting) event.preventDefault(); });
elements.tripDialog.addEventListener("close", () => {
  originPicker.close();
  destinationPicker.close();
  flightFromPicker.close();
  syncViewport();
});
elements.tripDialog.addEventListener("focusin", syncViewport);
elements.tripForm.addEventListener("submit", event => {
  event.preventDefault();
  if (busy) return;
  const body = tripStartBody();
  if (!body) return;
  if (hasMessages || sessionId) {
    elements.replaceConfirm.hidden = false;
    elements.startTrip.hidden = true;
    elements.confirmTripStart.focus();
  } else startTrip(body);
});
elements.confirmTripStart.addEventListener("click", () => { if (!busy) startTrip(tripStartBody()); });
elements.cancelTripStart.addEventListener("click", () => {
  elements.replaceConfirm.hidden = true;
  elements.startTrip.hidden = false;
  elements.startTrip.focus();
});
elements.tripInputs.addEventListener("input", event => {
  event.target?.setCustomValidity?.("");
  elements.replaceConfirm.hidden = true;
  elements.startTrip.hidden = false;
});
elements.flexibleDates.addEventListener("change", toggleFlexibleDates);
elements.dateFrom.addEventListener("change", toggleFlexibleDates);
elements.hasFlight.addEventListener("change", toggleFlightFields);
elements.flightDate.addEventListener("change", loadFlights);
elements.flightOptions.addEventListener("change", renderSelectedFlight);
elements.reloadFlights.addEventListener("click", loadFlights);
elements.input.addEventListener("input", resizeInput);
elements.input.addEventListener("focus", syncViewport);
elements.input.addEventListener("blur", syncViewport);
elements.input.addEventListener("compositionstart", () => { composing = true; });
elements.input.addEventListener("compositionend", () => { composing = false; resizeInput(); });
elements.input.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.ctrlKey || event.metaKey || event.altKey || event.isComposing || composing || event.keyCode === 229) return;
  event.preventDefault();
  if (!busy) elements.form.requestSubmit();
});
elements.newDialog.addEventListener("click", () => requestReset());
elements.confirmReset.addEventListener("click", () => {
  if (busy) return;
  const demo = pendingDemo;
  const trigger = resetTrigger;
  pendingDemo = null;
  resetTrigger = null;
  elements.resetDialog.close();
  if (demo) openDemo(demo, trigger);
  else resetConversation();
});
elements.resetDialog.addEventListener("close", () => {
  const trigger = resetTrigger;
  pendingDemo = null;
  resetTrigger = null;
  if (trigger?.isConnected) trigger.focus();
});
elements.reloadDemos.addEventListener("click", loadDemos);
elements.offlineDemo.addEventListener("click", () => {
  if (busy) return;
  setOfflineDemo(!offlineDemo);
  elements.offlineDemo.scrollIntoView({block: "nearest"});
});
elements.errorAction.addEventListener("click", () => errorAction?.());
window.addEventListener("resize", syncViewport);
window.visualViewport?.addEventListener("resize", syncViewport);
window.visualViewport?.addEventListener("scroll", syncViewport);
syncViewport();
loadDemos();
