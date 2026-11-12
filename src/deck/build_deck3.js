// Презентация v3: светлая, с самолётами и посадочным талоном; 7 слайдов.
// Цифры — outputs/presentation/deck_data.json (src/deck/deck_data.py), карты — src/deck/maps.py.
// Запуск: py -3.13 src/deck/deck_data.py && py -3.13 src/deck/maps.py && node src/deck/build_deck3.js
const fs = require('fs');
const path = require('path');
const NM = process.env.DECK_NODE_MODULES || path.join(__dirname, 'node_modules');  // npm install в src/deck
const PptxGenJS = require(path.join(NM, 'pptxgenjs'));
const JSZip = require(path.join(NM, 'jszip'));
const ROOT = path.join(__dirname, '..', '..');
const OUT = path.join(ROOT, 'outputs', 'presentation');
const D = JSON.parse(fs.readFileSync(path.join(OUT, 'deck_data.json'), 'utf8'));

// светлая палитра: бумага, графит для текста, красный только для акцента, небо и зелёный для прямых рейсов
const C = { bg: 'F6F3EE', card: 'FFFFFF', ink: '262A35', muted: '6B7280', line: 'E2DCD1', red: 'E32A2F', redSoft: 'FBE3E3',
  sky: 'DCE8F1', skyD: '7FA3C4', green: '2F9E6A', greenSoft: 'E1F2E8', sand: 'EDE6DA', asphalt: 'D9D3C7' };
const F = { reg: { fontFace: 'Onest' }, med: { fontFace: 'Onest Medium' }, bold: { fontFace: 'Onest', bold: true } };
const I = v => +(v / 144).toFixed(4);
const NB = '\u00A0';
const ru = (v, d = 0) => Number(v).toLocaleString('ru-RU', { minimumFractionDigits: d, maximumFractionDigits: d }).replace(/\u202F/g, NB);
const sg = (v, d = 0) => (v > 0 ? '+' : v < 0 ? '−' : '') + ru(Math.abs(v), d);

const pres = new PptxGenJS();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Onest', bodyFontFace: 'Onest' };
pres.title = 'Red Wings: путь к №2';
const anim = [];
let auto = 0; const nm = p => `${p}-${++auto}`;

function T(s, text, o) {
  const lines = Array.isArray(text) ? text.filter(r => r.options && r.options.breakLine).length + 1 : String(text).split('\n').length;
  const h = o.h || o.s * (o.lh || 125) / 100 * lines + 8;
  const opt = Object.assign({ x: I(o.x), y: I(o.y), w: I(o.w || 1400), h: I(h), margin: 0, valign: o.va || 'top', fit: 'none', fontSize: o.s / 2, color: o.c || C.ink, align: o.al || 'left', objectName: o.n || nm('t') }, F[o.f || 'reg']);
  if (o.lh) opt.lineSpacingMultiple = o.lh / 100;
  s.addText(text, opt); return opt.objectName;
}
const runs = (parts, base = {}) => parts.map(([t, o = {}]) => ({ text: t, options: Object.assign({}, F[o.f || base.f || 'reg'], o.c ? { color: o.c } : {}, o.br ? { breakLine: true } : {}) }));
function R(s, x, y, w, h, fill, o = {}) {
  const n = o.n || nm('r');
  s.addShape(o.rad ? pres.shapes.ROUNDED_RECTANGLE : pres.shapes.RECTANGLE, { x: I(x), y: I(y), w: I(w), h: I(h), rectRadius: o.rad ? I(o.rad) : undefined,
    fill: fill ? { color: fill } : { color: 'FFFFFF', transparency: 100 }, line: o.st ? { color: o.st, width: (o.sw || 2) / 2, dashType: o.dash || 'solid' } : { type: 'none' }, objectName: n });
  return n;
}
function E(s, cx, cy, d, fill, o = {}) {
  const n = o.n || nm('e');
  s.addShape(pres.shapes.OVAL, { x: I(cx - d / 2), y: I(cy - d / 2), w: I(d), h: I(d), fill: fill ? { color: fill, transparency: o.tr || 0 } : { color: 'FFFFFF', transparency: 100 },
    line: o.st ? { color: o.st, width: (o.sw || 2) / 2 } : { type: 'none' }, objectName: n });
  return n;
}
function P(s, pts, o) {
  const xs = [], ys = [];
  pts.forEach(p => { if (Array.isArray(p)) { xs.push(p[0]); ys.push(p[1]); } else { xs.push(p.q[0], p.to[0]); ys.push(p.q[1], p.to[1]); } });
  let mx = Math.min(...xs), my = Math.min(...ys), w = Math.max(...xs) - mx, h = Math.max(...ys) - my;
  if (w < 2) { mx -= 1; w = 2; } if (h < 2) { my -= 1; h = 2; }
  const points = pts.map((p, i) => Array.isArray(p) ? (i ? { x: I(p[0] - mx), y: I(p[1] - my) } : { x: I(p[0] - mx), y: I(p[1] - my), moveTo: true })
    : { x: I(p.to[0] - mx), y: I(p.to[1] - my), curve: { type: 'quadratic', x1: I(p.q[0] - mx), y1: I(p.q[1] - my) } });
  const n = o.n || nm('p');
  s.addShape(pres.shapes.CUSTOM_GEOMETRY, { x: I(mx), y: I(my), w: I(w), h: I(h), points, fill: { color: 'FFFFFF', transparency: 100 },
    line: { color: o.st, width: (o.sw || 2) / 2, dashType: o.dash || 'solid', cap: 'round' }, objectName: n });
  return n;
}
const PL = [[98,50],[94,46],[86,45],[60,45],[36,14],[27,14],[40,45],[18,45],[10,34],[4,34],[9,50],[4,66],[10,66],[18,55],[40,55],[27,86],[36,86],[60,55],[86,55],[94,54]];
function plane(s, cx, cy, size, rot, col = C.red, name) {
  const k = size / 100, n = name || nm('pl');
  const points = PL.map(([x, y], i) => i ? { x: I(x * k), y: I(y * k) } : { x: I(x * k), y: I(y * k), moveTo: true }).concat([{ close: true }]);
  s.addShape(pres.shapes.CUSTOM_GEOMETRY, { x: I(cx - size / 2), y: I(cy - size / 2), w: I(size), h: I(size), points, rotate: rot, fill: { color: col }, line: { type: 'none' }, objectName: n });
  return n;
}
// облако из трёх кругов
function cloud(s, x, y, k = 1) { E(s, x, y, 70 * k, 'FFFFFF'); E(s, x + 45 * k, y - 18 * k, 90 * k, 'FFFFFF'); E(s, x + 95 * k, y, 70 * k, 'FFFFFF'); R(s, x, y - 2 * k, 95 * k, 36 * k, 'FFFFFF'); }
let NUM = 0;
const num = s => { NUM++; return T(s, 'WZ ' + String(NUM).padStart(2, '0'), { x: 1640, y: 70, w: 160, s: 20, f: 'med', c: C.muted, al: 'right', n: '!!num' }); };
const label = (s, str) => T(s, str, { x: 120, y: 112, w: 1200, s: 24, f: 'med', c: C.red, n: '!!label' });
const title = (s, str, o = {}) => T(s, str, Object.assign({ x: 120, y: 156, w: 1600, s: 60, f: 'bold', c: C.ink, lh: 105, n: '!!title' }, o));
const foot = (s, str) => T(s, str, { x: 120, y: 1000, w: 1680, s: 18, c: C.muted });
const slide = () => { const s = pres.addSlide(); s.background = { color: C.bg }; return s; };
const img = (s, file, x, y, w, h, n) => { const name = n || nm('img'); s.addImage({ path: file, x: I(x), y: I(y), w: I(w), h: I(h), objectName: name }); return name; };

const H = D.hub, V = D.variants, A = D.asm, G = D.general || {};
const hb = V[H].base, dr = V.DIRECT.base;
const rwShare = A.rw_pax_2025[0] / A.market_pax_2025[0] * 100;
const pobeda = D.competitors.carriers.find(c => c.id === 'pobeda');
const gap = pobeda.pax_million - A.rw_pax_2025[0] / 1e6;
const hubAdd = (hb.net_new_segments_year || hb.segments_year) / 1e6;

// ---------- 1. Обложка с посадочным талоном ----------
{
  const s = slide(), a = [];
  cloud(s, 1180, 150, 1.1); cloud(s, 260, 930, 0.8); cloud(s, 1600, 960, 0.9);
  a.push({ n: label(s, 'Кейс Red Wings · команда «День рождения сосиски»'), d: 0 });
  a.push({ n: T(s, 'Путь Red Wings\nк второму месту\nв России', { x: 120, y: 250, w: 950, s: 96, f: 'bold', lh: 100, n: '!!title' }), d: 150 });
  a.push({ n: T(s, 'Растём сетью региональных хабов на новых SJ-100\nи добавляем окупаемые прямые рейсы', { x: 120, y: 640, w: 900, s: 30, c: C.muted, lh: 135 }), d: 350 });
  const route = P(s, [[60, 1020], { q: [650, 960], to: [1020, 700] }], { st: C.skyD, sw: 3, dash: 'dash' });
  // талон
  const tk = [R(s, 1100, 260, 700, 560, C.card, { rad: 30, st: C.line, sw: 2 }), E(s, 1600, 260, 50, C.bg), E(s, 1600, 820, 50, C.bg),
    P(s, [[1600, 300], [1600, 780]], { st: C.line, sw: 3, dash: 'sysDash' }),
    T(s, 'Сейчас', { x: 1150, y: 305, w: 200, s: 20, f: 'med', c: C.muted }), T(s, '2,7', { x: 1150, y: 330, w: 200, s: 80, f: 'bold' }),
    T(s, 'млн пассажиров, 2025', { x: 1150, y: 430, w: 260, s: 18, c: C.muted }),
    T(s, 'Цель', { x: 1415, y: 305, w: 150, s: 20, f: 'med', c: C.muted }), T(s, '№2', { x: 1415, y: 330, w: 180, s: 80, f: 'bold', c: C.red })];
  tk.push(plane(s, 1360, 378, 50, 0, C.red));
  [['Первый хаб', 'Омск', 1150, 500], ['Самолётов', String(hb.aircraft), 1415, 500], ['Итог хаба за год', `${sg(hb.result_mln_year)}${NB}млн${NB}₽`, 1150, 640], ['Горизонт', '2035', 1415, 640]]
    .forEach(([l, v, x, y]) => { tk.push(T(s, l, { x, y, w: 240, s: 20, f: 'med', c: C.muted })); tk.push(T(s, v, { x, y: y + 30, w: 240, s: 36, f: 'bold', c: l.startsWith('Итог') ? C.red : C.ink })); });
  let by = 310; for (let i = 0; i < 30; i++) { const hh = [3, 6, 2, 8, 4, 2, 5][i % 7]; tk.push(R(s, 1645, by, 115, hh, C.ink)); by += hh + [5, 3, 7, 4][i % 4]; }
  tk.forEach(n => a.push({ n, d: 450, dur: 600 }));
  a.push({ n: route, d: 700, t: 'wipe', dur: 1200 });
  plane(s, 1030, 690, 96, -28, C.red, '!!plane');
  a.push({ n: '!!plane', d: 900, t: 'path', dur: 1700, path: motionFrom(60, 1020, 650, 960, 1030, 690) });
  num(s); anim.push(a);
}

// ---------- 2. Задача: польза и разрыв до №2 ----------
{
  const s = slide(), a = [];
  a.push({ n: label(s, 'Задача'), d: 0 });
  a.push({ n: title(s, `Red${NB}Wings нужно ещё ${ru(gap, 1)}${NB}млн пассажиров в${NB}год`), d: 100 });
  // взлётная полоса с перевозчиками
  const x0 = 140, x1 = 1780, k = (x1 - x0) / 15, y = 480;
  R(s, x0 - 40, y - 46, x1 - x0 + 80, 92, C.asphalt, { rad: 46 });
  for (let x = x0; x < x1; x += 60) R(s, x, y - 3, 30, 6, 'FFFFFF');
  const list = D.competitors.carriers.filter(c => c.pax_million <= 15).sort((p, q) => p.pax_million - q.pax_million);
  list.forEach((c, i) => {
    const x = x0 + c.pax_million * k, rw = c.id === 'rw', no2 = c.id === 'pobeda', up = i % 2 === 0, d = 300 + i * 90;
    a.push({ n: plane(s, x, y, rw || no2 ? 74 : 46, 0, rw ? C.red : no2 ? C.ink : C.skyD), d, dur: 400 });
    a.push({ n: T(s, runs([[c.name, { f: rw || no2 ? 'bold' : 'med', br: true }], [ru(c.pax_million, 1) + ' млн', { c: C.muted }]]), { x: x - 120, y: up ? y - 150 : y + 66, w: 240, s: rw || no2 ? 24 : 20, al: 'center', lh: 115, h: 70, c: rw ? C.red : C.ink }), d });
  });
  const xr = x0 + 2.7 * k, xp = x0 + pobeda.pax_million * k;
  a.push({ n: P(s, [[xr, y + 150], [xp, y + 150]], { st: C.red, sw: 3, dash: 'dash' }), d: 1300, t: 'wipe', dur: 800 });
  a.push({ n: T(s, `разрыв ${ru(gap, 1)} млн`, { x: (xr + xp) / 2 - 150, y: y + 160, w: 300, s: 26, f: 'bold', c: C.red, al: 'center' }), d: 1500 });
  // польза
  const cards = [[`${ru(rwShare, 1)}%`, `рынка у Red${NB}Wings сейчас: ${ru(A.rw_pax_2025[0] / 1e6, 1)}${NB}млн из ${ru(A.market_pax_2025[0] / 1e6, 1)}${NB}млн пассажиров`],
    [`${ru(G.hub_gap_pop / 1e6)}${NB}млн`, 'жителей в городах, куда из Омска нет прямого рейса и поезда быстрее 12 часов'],
    ['SJ-100', `Red${NB}Wings первой получает новые российские самолёты: куда их поставить, решает рост`]];
  cards.forEach(([v, t], i) => { const x = 120 + i * 570, d = 1700 + i * 150;
    a.push({ n: R(s, x, 770, 540, 190, C.card, { rad: 22 }), d });
    a.push({ n: T(s, v, { x: x + 30, y: 795, w: 480, s: 40, f: 'bold', c: i === 1 ? C.red : C.ink }), d });
    a.push({ n: T(s, t, { x: x + 30, y: 852, w: 480, s: 20, c: C.muted, lh: 128, h: 90 }), d }); });
  num(s); anim.push(a);
}

// ---------- 3. Наш выбор: хабы + точечные прямые, две карты ----------
{
  const s = slide(), a = [];
  a.push({ n: label(s, 'Наш выбор'), d: 0 });
  a.push({ n: title(s, 'Растём хабами и добавляем окупаемые прямые рейсы', { s: 52 }), d: 100 });
  const mw = 820, mh = Math.round(mw / 1.55), my = 250;
  [[120, 'map_hubs.png', 'Хабы — основа роста', C.red, [`Первый хаб — Омск: ${sg(hb.result_mln_year)}${NB}млн${NB}₽ в год`, `Дальше Самара (опорный аэропорт), Челябинск, Тюмень`, `Хаб собирает пассажиров тонких пар, которым одного рейса мало`]],
   [980, 'map_direct.png', 'Прямые рейсы — точечно', C.green, [`${G.triangles_positive} из ${G.triangles} маршрутов с базы окупаются сами`, 'Запускаем по одной паре, где спроса хватает без пересадок']]]
    .forEach(([x, f, h_, col, pts], i) => { const d = 300 + i * 400;
      a.push({ n: R(s, x - 6, my - 6, mw + 12, mh + 12, C.card, { rad: 22 }), d });
      a.push({ n: img(s, path.join(OUT, 'maps', f), x, my, mw, mh), d, t: 'wipe', dur: 700 });
      const py_ = my + mh - 66, pw = h_.length * 15.5 + 80;
      a.push({ n: R(s, x + 10, py_, pw, 52, C.card, { rad: 26 }), d: d + 200 });
      a.push({ n: R(s, x + 20, py_ + 10, 30, 30, col, { rad: 15 }), d: d + 200 });
      a.push({ n: T(s, h_, { x: x + 62, y: py_ + 9, w: 600, s: 28, f: 'bold', c: C.ink }), d: d + 200 });
      pts.forEach((t, j) => { a.push({ n: plane(s, x + 14, my + mh + 42 + j * 46, 22, 0, col), d: d + 300 + j * 100 });
        a.push({ n: T(s, t, { x: x + 36, y: my + mh + 28 + j * 46, w: mw - 40, s: 22, c: C.ink }), d: d + 300 + j * 100 }); }); });
  foot(s, 'Данные: отчёты аэропортов 2025, расписания, Росавиация, перепись 2021. Спрос между 2 044 парами городов и деньги каждого рейса. Вывод проверен второй моделью коллег на 2027–2028 годы.');
  num(s); anim.push(a);
}

// ---------- 4. Первый хаб — Омск: результат ----------
{
  const s = slide(), a = [];
  cloud(s, 1500, 170, 0.9);
  a.push({ n: label(s, 'Результат'), d: 0 });
  a.push({ n: title(s, 'Первый хаб — Омск'), d: 100 });
  a.push({ n: T(s, `${sg(hb.result_mln_year)}${NB}млн${NB}₽`, { x: 115, y: 270, w: 900, s: 150, f: 'bold', c: C.red }), d: 250 });
  a.push({ n: T(s, 'итог сети за год: выручка минус расходы на рейсы', { x: 120, y: 460, w: 800, s: 26, c: C.muted }), d: 350 });
  const facts = [[`${hb.routes}`, 'лучей из Омска'], [`${ru(hb.segments_year / 1000)}${NB}тыс.`, 'пассажиров в год'], [`${sg(hb.share_pp, 2)}${NB}п.${NB}п.`, `доли рынка: ${ru(rwShare, 2)}% → ${ru(rwShare + hb.share_pp, 2)}%`]];
  facts.forEach(([v, t], i) => { const x = 120 + i * 300, d = 450 + i * 120;
    a.push({ n: T(s, v, { x, y: 540, w: 290, s: 46, f: 'bold' }), d }); a.push({ n: T(s, t, { x, y: 604, w: 280, s: 20, c: C.muted, lh: 125, h: 60 }), d }); });
  // почему Омск — чипсы
  const why = ['1-е место на табло из 15 городов', 'мало дней «Ковра»', 'ТО для SSJ в аэропорту', `${ru(G.hub_transfer_demand / 1e6, 1)}${NB}млн поездок с пересадкой вокруг`];
  T(s, 'Почему Омск', { x: 120, y: 700, w: 400, s: 22, f: 'med', c: C.red });
  let cx = 120, cy = 740;
  why.forEach((t, i) => { const w = t.length * 11.5 + 44; if (cx + w > 1000) { cx = 120; cy += 62; }
    a.push({ n: R(s, cx, cy, w, 48, C.card, { rad: 24, st: C.line, sw: 2 }), d: 800 + i * 80 }); a.push({ n: T(s, t, { x: cx + 22, y: cy + 11, w: w - 30, s: 20, f: 'med' }), d: 800 + i * 80 }); cx += w + 14; });
  // рост парка: самолёты прилетают
  R(s, 1080, 290, 720, 640, C.card, { rad: 26 });
  T(s, 'Сеть растёт с поставками SJ-100', { x: 1120, y: 320, w: 660, s: 26, f: 'bold' });
  const rp = Object.fromEntries(D.ramp.map(r => [r.fleet_cap, r]));
  [[rp[3], D.ramp_when['3']], [rp[4], D.ramp_when['4']], [rp[6], D.ramp_when['6']], [rp[8], 'полная сеть, 2028']].forEach(([r, when], i) => {
    const y = 400 + i * 128, d = 1100 + i * 250;
    a.push({ n: T(s, when, { x: 1120, y, w: 640, s: 20, c: C.muted }), d });
    for (let k = 0; k < r.aircraft; k++) a.push({ n: plane(s, 1140 + k * 52, y + 58, 42, 0, k === r.aircraft - 1 ? C.skyD : C.red), d: d + k * 60, dur: 300 });
    a.push({ n: T(s, `${r.routes} лучей`, { x: 1530, y: y + 40, w: 240, s: 26, f: 'bold', al: 'right' }), d: d + 200 }); });
  T(s, 'красный — рабочий самолёт, голубой — резерв', { x: 1120, y: 905, w: 660, s: 16, c: C.muted });
  foot(s, 'Проверка: вторая модель коллег с поставками по месяцам 2027–2028 годов тоже ставит Омск в верхнюю группу городов.');
  num(s); anim.push(a);
}


// ---------- 5. Как считали хабы ----------
{
  const s = slide(), a = [];
  const od = D.od_fit;
  a.push({ n: label(s, 'Данные и метод · хабы'), d: 0 });
  a.push({ n: title(s, 'Как мы считали хабы'), d: 100 });
  // маршрут из четырёх «аэропортов»
  const xs = [315, 742, 1168, 1595], yl = 330;
  a.push({ n: P(s, [[150, yl], [1700, yl]], { st: C.skyD, sw: 3, dash: 'dash' }), d: 200, t: 'wipe', dur: 1200 });
  const steps = [
    ['Отбор городов', `20 городов и 10 критериев: люди без удобной связи, дни «Ковра», пассажиропоток, пересадки, ТО для SSJ.`, 'Веса задала команда; тройка лидеров держится в 19 из 20 проверок со случайными весами.'],
    ['Спрос между городами', `Формула тяготения по ${od.n_links_fit} парам из отчётов аэропортов: население, время поездом, Москва и курорты.`, `Поездки «откуда — куда» для ${ru(od.pairs_air)} пар, из них ${ru(od.pairs_one_stop)} сейчас с пересадкой.`],
    ['Сеть хаба', 'Лучи добавляем по одному, пока растёт итог. Перебираем от 2 до 10 самолётов, минимум 8 направлений.', `Рейсов = пассажиры / ${ru(A.seats[0] * A.lf_max[0])} мест; самолётов = блок-часы / 70 ч + резерв.`],
    ['Деньги сети', `Билет ${ru(A.fare_fixed_rub[0])}${NB}₽ + ${ru(A.fare_per_km_rub[0], 1)}${NB}₽/км; билет с пересадкой делится между двумя рейсами.`, 'Расходы: топливо с компенсацией государства, ТО, экипаж, навигация, аэропорт.']];
  steps.forEach(([h_, t1, t2], i) => { const x = xs[i], d = 400 + i * 300;
    a.push({ n: E(s, x, yl, 64, C.card, { st: C.red, sw: 5 }), d });
    a.push({ n: T(s, String(i + 1), { x: x - 32, y: yl - 18, w: 64, s: 28, f: 'bold', c: C.red, al: 'center' }), d });
    a.push({ n: R(s, x - 195, yl + 60, 400, 400, C.card, { rad: 22 }), d });
    a.push({ n: T(s, h_, { x: x - 170, y: yl + 85, w: 340, s: 28, f: 'bold', lh: 110, h: 70 }), d });
    a.push({ n: T(s, t1, { x: x - 170, y: yl + 140, w: 340, s: 20, lh: 130, h: 150 }), d });
    a.push({ n: T(s, t2, { x: x - 170, y: yl + 300, w: 340, s: 18, c: C.muted, lh: 128, h: 140 }), d }); });
  plane(s, 1735, yl, 64, 0, C.red, '!!plane');
  // что учитывать дальше
  T(s, 'Что добавить в следующие модели', { x: 120, y: 830, w: 800, s: 22, f: 'med', c: C.red });
  let cx = 120;
  ['несколько хабов вместе', 'спрос по месяцам', 'ответ конкурентов', 'слоты и обороты', 'стоимость базы и аренды'].forEach((t, i) => {
    const w = t.length * 11.5 + 48; a.push({ n: R(s, cx, 870, w, 50, C.card, { rad: 25, st: C.line, sw: 2 }), d: 1800 + i * 80 });
    a.push({ n: T(s, t, { x: cx + 24, y: 882, w: w - 30, s: 20, f: 'med' }), d: 1800 + i * 80 }); cx += w + 14; });
  foot(s, 'Повторяемость: у каждой цифры во входных таблицах указан источник, все допущения в одном файле; расчёт, Excel и панель redwings.altair.ad пересобираются одной командой.');
  num(s); anim.push(a);
}

// ---------- 6. Как считали прямые рейсы ----------
{
  const s = slide(), a = [];
  a.push({ n: label(s, 'Данные и метод · прямые рейсы'), d: 0 });
  a.push({ n: title(s, 'Как мы считали прямые рейсы'), d: 100 });
  // треугольник: база → А → Б → база
  R(s, 120, 270, 820, 640, C.card, { rad: 26 });
  const B0 = [260, 760], P1 = [660, 390], P2 = [860, 690];
  [[B0, P1], [P1, P2], [P2, B0]].forEach(([u, v], i) => {
    a.push({ n: P(s, [u, v], { st: C.green, sw: 5 }), d: 300 + i * 250, t: 'wipe', dur: 500 });
    const mx = (u[0] + v[0]) / 2, my = (u[1] + v[1]) / 2, ang = Math.atan2(v[1] - u[1], v[0] - u[0]) * 180 / Math.PI;
    a.push({ n: plane(s, mx, my, 40, ang, C.green), d: 450 + i * 250 }); });
  a.push({ n: R(s, B0[0] - 22, B0[1] - 22, 44, 44, C.ink, { rad: 8 }), d: 300 });
  a.push({ n: E(s, P1[0], P1[1], 30, C.card, { st: C.ink, sw: 4 }), d: 550 });
  a.push({ n: E(s, P2[0], P2[1], 30, C.card, { st: C.ink, sw: 4 }), d: 800 });
  a.push({ n: T(s, 'база: Москва или Екатеринбург', { x: 150, y: 800, w: 360, s: 20, f: 'med' }), d: 300 });
  a.push({ n: T(s, 'город А', { x: 690, y: 360, w: 200, s: 20, f: 'med' }), d: 550 });
  a.push({ n: T(s, 'город Б', { x: 800, y: 725, w: 130, s: 20, f: 'med' }), d: 800 });
  a.push({ n: T(s, `Самолёт облетает два города и возвращается. ${ru(A.min_freq_week[0])}–${ru(A.direct_max_freq_week[0])} рейсов в неделю. Спрос пары делим с конкурентами по частотам: до ${ru(A.capture_competitive[0] * 100)}%, без конкурента до ${ru(A.capture_open[0] * 100)}%.`, { x: 160, y: 300, w: 340, s: 20, c: C.muted, lh: 130, h: 200 }), d: 900 });
  // один рейс: салон и окупаемость
  const km = 1500, j = 0, bh = A.block_fixed_h[j] + km * A.route_factor[j] / A.block_speed_kmh[j];
  const fixed = (A.fuel_t_per_hour[j] * bh + A.fuel_t_per_cycle[j]) * (A.fuel_rub_per_t[j] - A.fuel_compensation_rub_per_t[j]) + (A.mro_rub_per_hour[j] + A.crew_rub_per_hour[j] + A.navigation_rub_per_hour[j]) * bh + A.ground_rub_per_flight[j] + A.deicing_rub_per_flight[j];
  const fare = A.fare_fixed_rub[j] + A.fare_per_km_rub[j] * km, be = Math.ceil(fixed / (fare - A.pax_cost_rub[j]));
  R(s, 980, 270, 820, 640, C.card, { rad: 26 });
  a.push({ n: T(s, runs([['Рейс на 1 500 км окупается с ', {}], [`${be} пассажиров`, { f: 'bold', c: C.red }], [' из 100', {}]]), { x: 1020, y: 300, w: 760, s: 30, lh: 115, h: 80 }), d: 1100 });
  const sx0 = 1030, sy0 = 400;
  for (let r = 0; r < 20; r++) for (let c = 0; c < 5; c++) { const n = r * 5 + c + 1, x = sx0 + r * 37, y = sy0 + (c < 2 ? c * 30 : 74 + (c - 2) * 30);
    a.push({ n: R(s, x, y, 28, 24, n <= be ? 'C9CED6' : C.green, { rad: 6 }), d: 1200 + r * 40, dur: 200 }); }
  a.push({ n: T(s, `первые ${be} кресел покрывают расходы рейса, остальные дают прибыль`, { x: 1030, y: 572, w: 740, s: 18, c: C.muted }), d: 2000 });
  a.push({ n: T(s, runs([['Выручка', { f: 'bold', br: true }], [`пассажиры × (${ru(A.fare_fixed_rub[0])} ₽ + ${ru(A.fare_per_km_rub[0], 1)} ₽ × км)`, { br: true }],
    ['Расходы рейса', { f: 'bold', br: true }], [`топливо по цене минус компенсация, ТО, экипаж, навигация, аэропорт, ${ru(A.pax_cost_rub[0])} ₽ на пассажира`, {}]]), { x: 1030, y: 615, w: 740, s: 22, lh: 130, h: 200 }), d: 2100 });
  a.push({ n: T(s, `Итог: ${G.triangles_positive} из ${G.triangles} треугольников окупаются сами, их и запускаем по одному.`, { x: 1030, y: 820, w: 740, s: 22, f: 'med', c: C.green, lh: 125, h: 70 }), d: 2200 });
  foot(s, `Проверка по неделе рейсов (коллеги): из Екатеринбурга треугольник через Сочи и Минводы и два челнока в Сочи дают почти равный итог, ${ru(G.tri_check['TRI:SVX-AER-MRV'], 1)} и ${ru(G.tri_check.AER2, 1)}${NB}млн${NB}₽ в месяц, а треугольник связывает три пары городов.`);
  num(s); anim.push(a);
}

// ---------- 5. Путь к №2: дальше 2028 года ----------
{
  const s = slide(), a = [];
  a.push({ n: label(s, 'Путь к №2'), d: 0 });
  a.push({ n: title(s, 'Набираем высоту до 2035 года'), d: 100 });
  // ось лет и траектория набора высоты
  const X = yr => 160 + (yr - 2026) / 9 * 1560, Y = m => 860 - (m - 2) / 12.5 * 520;
  R(s, 100, 905, 1720, 26, C.asphalt, { rad: 13 });
  for (let x = 130; x < 1800; x += 70) R(s, x, 916, 34, 4, 'FFFFFF');
  [2026, 2028, 2030, 2035].forEach(yr => T(s, String(yr), { x: X(yr) - 60, y: 945, w: 120, s: 24, f: 'bold', al: 'center', c: C.muted }));
  // цель
  a.push({ n: P(s, [[X(2026), Y(13.8)], [X(2035) + 40, Y(13.8)]], { st: C.ink, sw: 2, dash: 'dash' }), d: 200 });
  a.push({ n: T(s, `№2 сейчас: «Победа», ${ru(pobeda.pax_million, 1)} млн`, { x: X(2026), y: Y(13.8) - 44, w: 600, s: 22, f: 'med' }), d: 250 });
  const pts = [[2026, 2.7], [2028, 2.7 + hubAdd], [2030, 7.5], [2035, 14.3]];
  a.push({ n: P(s, [[X(2026), Y(2.7)], { q: [X(2029), Y(3.2)], to: [X(2031.5), Y(9)] }, { q: [X(2033.5), Y(13.5)], to: [X(2035), Y(14.3)] }], { st: C.red, sw: 6 }), d: 400, t: 'wipe', dur: 1600 });
  a.push({ n: E(s, X(2026), Y(2.7), 22, C.red), d: 400 });
  plane(s, X(2035) + 10, Y(14.3) - 10, 80, -18, C.red, '!!plane');
  a.push({ n: '!!plane', d: 1800, dur: 400 });
  // этапы: короткие подписи над траекторией
  const st = [[2026.25, 650, '2027–2028', 'Хаб в Омске, первые SJ-100', C.muted, 400],
    [2028.4, 470, '2028–2030', `Хабы в Самаре, Челябинске, Тюмени.\n№2 по числу пар городов\nс прямым рейсом`, C.ink, 470],
    [2031.3, 560, '2030–2035', `№2 по пассажирам:\nоколо 90 новых SJ-100`, C.red, 470]];
  st.forEach(([yr, y, h_, t, col, w], i) => { const x = X(yr), d = 700 + i * 400;
    a.push({ n: R(s, x, y - 10, w, i === 1 ? 215 : i ? 140 : 96, C.card, { rad: 20 }), d });
    a.push({ n: T(s, h_, { x: x + 24, y: y + 4, w: w - 40, s: i ? 26 : 20, f: 'bold', c: col }), d });
    a.push({ n: T(s, t, { x: x + 24, y: y + (i ? 42 : 34), w: w - 40, s: i ? 24 : 20, c: C.ink, lh: 120, h: 100 }), d }); });
  foot(s, 'Число самолётов — расчёт коллег по налёту и загрузке одного SJ-100 (P10, 12.11.2026). Траектория показывает этапы, это не прогноз по годам.');
  num(s); anim.push(a);
}

// ---------- 6. Цифровые сервисы: телефоны ----------
{
  const s = slide(), a = [];
  a.push({ n: label(s, 'Цифровые сервисы'), d: 0 });
  a.push({ n: title(s, 'Всё в один клик'), d: 100 });
  const phones = [
    ['Программа лояльности', 'баллы за полёты между регионами, двойные за пересадку', 'loyal'],
    ['Перебронировать', 'одной кнопкой, если рейс задержал «Ковёр»', 'rebook'],
    ['Купить за минуту', 'без обязательного выбора места', 'buy'],
    ['Багаж и возврат', 'одна цена на всех страницах и простые правила', 'bag']];
  phones.forEach(([h_, t, kind], i) => {
    const x = 150 + i * 430, y = 290, w = 300, hh = 560, d = 300 + i * 220;
    a.push({ n: R(s, x, y, w, hh, C.ink, { rad: 46 }), d });
    a.push({ n: R(s, x + 14, y + 14, w - 28, hh - 28, C.card, { rad: 36 }), d });
    a.push({ n: R(s, x + w / 2 - 40, y + 26, 80, 14, C.ink, { rad: 7 }), d });
    const sx = x + 32, sw = w - 64, sy = y + 70;
    if (kind === 'loyal') {
      a.push({ n: R(s, sx, sy + 20, sw, 150, C.red, { rad: 18 }), d: d + 100 });
      a.push({ n: T(s, 'Мои баллы', { x: sx + 18, y: sy + 36, w: sw - 30, s: 20, f: 'bold', c: 'FFFFFF' }), d: d + 100 });
      a.push({ n: T(s, '2 480 баллов', { x: sx + 18, y: sy + 118, w: sw - 30, s: 24, f: 'bold', c: 'FFFFFF' }), d: d + 100 });
      a.push({ n: plane(s, sx + sw - 34, sy + 60, 36, -20, 'FFFFFF'), d: d + 100 });
      a.push({ n: R(s, sx, sy + 200, sw, 64, C.redSoft, { rad: 14 }), d: d + 200 }); a.push({ n: T(s, '×2 за пересадку', { x: sx + 16, y: sy + 220, w: sw - 20, s: 20, f: 'med', c: C.red }), d: d + 200 });
    } else if (kind === 'rebook') {
      a.push({ n: R(s, sx, sy + 20, sw, 110, C.sky, { rad: 16 }), d: d + 100 });
      a.push({ n: T(s, 'OMS → KUF\nрейс задержан', { x: sx + 16, y: sy + 36, w: sw - 20, s: 20, f: 'med', lh: 120 }), d: d + 100 });
      a.push({ n: R(s, sx, sy + 160, sw, 70, C.red, { rad: 35 }), d: d + 200 }); a.push({ n: T(s, 'Перебронировать', { x: sx, y: sy + 181, w: sw, s: 22, f: 'bold', c: 'FFFFFF', al: 'center' }), d: d + 200 });
      a.push({ n: T(s, '✓ следующий рейс 17:00', { x: sx, y: sy + 255, w: sw, s: 18, c: C.green, al: 'center', f: 'med' }), d: d + 300 });
    } else if (kind === 'buy') {
      ['Омск — Самара', '12 сентября', '1 пассажир'].forEach((t, j) => { a.push({ n: R(s, sx, sy + 20 + j * 64, sw, 52, C.bg, { rad: 12 }), d: d + 100 }); a.push({ n: T(s, t, { x: sx + 16, y: sy + 34 + j * 64, w: sw - 20, s: 18 }), d: d + 100 }); });
      a.push({ n: R(s, sx, sy + 225, sw, 70, C.red, { rad: 35 }), d: d + 200 }); a.push({ n: T(s, 'Оплатить · СБП', { x: sx, y: sy + 246, w: sw, s: 22, f: 'bold', c: 'FFFFFF', al: 'center' }), d: d + 200 });
    } else {
      a.push({ n: R(s, sx + sw / 2 - 60, sy + 30, 120, 140, C.sand, { rad: 18 }), d: d + 100 }); a.push({ n: R(s, sx + sw / 2 - 30, sy + 10, 60, 30, null, { rad: 12, st: C.ink, sw: 5 }), d: d + 100 });
      a.push({ n: T(s, '20 кг · 1 990 ₽', { x: sx, y: sy + 195, w: sw, s: 22, f: 'bold', al: 'center' }), d: d + 200 });
      a.push({ n: T(s, 'одна цена везде', { x: sx, y: sy + 232, w: sw, s: 18, c: C.muted, al: 'center' }), d: d + 200 });
    }
    a.push({ n: P(s, [[x + 30, y + hh - 90], [x + w - 30, y + hh - 90]], { st: C.line, sw: 2 }), d: d + 200 });
    [0, 1, 2].forEach(j => a.push({ n: j === 1 ? plane(s, x + w / 2, y + hh - 55, 30, -45, C.red) : E(s, x + w / 2 + (j - 1) * 80, y + hh - 55, 14, C.line), d: d + 200 }));
    const extra = { loyal: 'до бесплатного полёта 520 баллов', rebook: 'уведомление пришло в 06:40', buy: 'багаж 20 кг · добавлен', bag: 'вернуть билет: 2 шага' }[kind];
    a.push({ n: T(s, extra, { x: sx, y: y + hh - 160, w: sw, s: 17, c: C.muted, al: 'center' }), d: d + 250 });
    a.push({ n: T(s, h_, { x: x - 30, y: y + hh + 26, w: w + 60, s: 26, f: 'bold', al: 'center' }), d: d + 300 });
    a.push({ n: T(s, t, { x: x - 30, y: y + hh + 66, w: w + 60, s: 20, c: C.muted, al: 'center', lh: 125, h: 60 }), d: d + 300 });
  });
  plane(s, 1760, 190, 60, -10, C.red, '!!plane');
  num(s); anim.push(a);
}

// ---------- 7. Расширение в будущем: три окна ----------
{
  const s = slide(), a = [];
  a.push({ n: label(s, 'Расширение в будущем'), d: 0 });
  a.push({ n: title(s, 'Как авиакомпании взлетали резко', { s: 56 }), d: 100 });
  a.push({ n: T(s, 'Они создавали новых пассажиров: забирали людей с поездов и автобусов, быстро занимали освободившиеся ниши и объединяли слабых.', { x: 120, y: 236, w: 1600, s: 24, c: C.muted, lh: 130 }), d: 200 });
  const wins = [
    ['bolt', 'Быстро реагировать', ['Больше кресел под ВЭФ, ПМЭФ и спорт', 'Готовый план подхватить маршруты ушедшего перевозчика за 1–2 месяца', 'Nordwind в 2021 году: 2,9 → 5,9 млн пассажиров']],
    ['merge', 'Объединять компании', ['S7 росла поглощениями', '«Россия» и «Аврора» — объединения внутри группы и с регионом', 'Red Wings — через холдинг Ростеха вместе с регионами']],
    ['compass', 'Искать новые маршруты', ['Рейсы в Горно-Алтайск появились, когда Алтай стал притягивать туристов', 'Забирать пассажиров с поездов, как Azul и Volaris', '«Евразийский мост»: Средняя Азия — регионы России через Омск']]];
  wins.forEach(([ic, h_, pts], i) => { const x = 120 + i * 570, y = 340, w = 540, hh = 560, d = 300 + i * 300;
    a.push({ n: R(s, x, y, w, hh, C.card, { rad: 26 }), d });
    a.push({ n: E(s, x + 70, y + 74, 84, C.redSoft), d });
    if (ic === 'bolt') a.push({ n: plane(s, x + 70, y + 74, 54, -30, C.red), d });
    if (ic === 'merge') { a.push({ n: plane(s, x + 52, y + 60, 34, 25, C.red), d }); a.push({ n: plane(s, x + 52, y + 92, 34, -25, C.red), d }); a.push({ n: plane(s, x + 88, y + 76, 34, 0, C.red), d }); }
    if (ic === 'compass') { a.push({ n: E(s, x + 70, y + 74, 52, null, { st: C.red, sw: 5 }), d }); a.push({ n: plane(s, x + 70, y + 74, 30, -45, C.red), d }); }
    a.push({ n: T(s, h_, { x: x + 130, y: y + 52, w: w - 150, s: 30, f: 'bold', lh: 110, h: 80 }), d });
    pts.forEach((t, j) => { const yy = y + 165 + j * 118;
      a.push({ n: P(s, [[x + 40, yy + 14], [x + 64, yy + 14]], { st: C.red, sw: 4 }), d: d + 150 + j * 100 });
      a.push({ n: T(s, t, { x: x + 80, y: yy, w: w - 110, s: 24, lh: 125, h: 100 }), d: d + 150 + j * 100 }); }); });
  foot(s, 'Примеры: 18 авиакомпаний из 10 стран; события и Горно-Алтайск — консультация эксперта авиакомпании, 12.11.2026. Команда «День рождения сосиски» · redwings.altair.ad');
  plane(s, 1760, 150, 56, -12, C.red, '!!plane');
  num(s); anim.push(a);
}

function motionFrom(x0, y0, qx, qy, x1, y1) {
  const fx = v => v / 1920, fy = v => v / 1080;
  const p0 = [fx(x0 - x1), fy(y0 - y1)], q = [fx(qx - x1), fy(qy - y1)];
  const c1 = [p0[0] + 2 / 3 * (q[0] - p0[0]), p0[1] + 2 / 3 * (q[1] - p0[1])], c2 = [2 / 3 * q[0], 2 / 3 * q[1]];
  const f = v => v.toFixed(4);
  return `M ${f(p0[0])} ${f(p0[1])} C ${f(c1[0])} ${f(c1[1])} ${f(c2[0])} ${f(c2[1])} 0 0 E`;
}

// ---------- анимации и переходы ----------
const MORPH = '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"><mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159"><p:transition spd="slow" p14:dur="800" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"><p159:morph option="byObject"/></p:transition></mc:Choice><mc:Fallback><p:transition spd="slow"><p:fade/></p:transition></mc:Fallback></mc:AlternateContent>';
const SPEED = 0.55;
function effectXml(ctx, spid, src) {
  const id = () => ++ctx.id, d = Math.round(src.d * SPEED), dur = Math.max(150, Math.round((src.dur || 500) * SPEED));
  const tgt = `<p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl>`;
  if (src.t === 'path') { const o = id();
    return `<p:par><p:cTn id="${o}" presetID="0" presetClass="path" presetSubtype="0" accel="50000" decel="50000" fill="hold" nodeType="withEffect"><p:stCondLst><p:cond delay="${d}"/></p:stCondLst><p:childTnLst><p:animMotion origin="layout" path="${src.path}" pathEditMode="relative"><p:cBhvr><p:cTn id="${id()}" dur="${dur}" fill="hold"/>${tgt}<p:attrNameLst><p:attrName>ppt_x</p:attrName><p:attrName>ppt_y</p:attrName></p:attrNameLst></p:cBhvr></p:animMotion></p:childTnLst></p:cTn></p:par>`; }
  const set = `<p:set><p:cBhvr><p:cTn id="${id()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>${tgt}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>`;
  const fx = f => `<p:animEffect transition="in" filter="${f}"><p:cBhvr><p:cTn id="${id()}" dur="${dur}"/>${tgt}</p:cBhvr></p:animEffect>`;
  const body = set + fx(src.t === 'wipe' ? 'wipe(left)' : 'fade'), preset = src.t === 'wipe' ? 22 : 10, sub = src.t === 'wipe' ? 8 : 0, o = id();
  return `<p:par><p:cTn id="${o}" presetID="${preset}" presetClass="entr" presetSubtype="${sub}" fill="hold" nodeType="withEffect"><p:stCondLst><p:cond delay="${d}"/></p:stCondLst><p:childTnLst>${body}</p:childTnLst></p:cTn></p:par>`;
}
function timingXml(items, ids) {
  const ctx = { id: 4 };
  const eff = items.filter(it => ids[it.n]).map(it => effectXml(ctx, ids[it.n], it)).join('');
  const bld = [...new Set(items.filter(it => it.t !== 'path' && ids[it.n]).map(it => ids[it.n]))].map(i => `<p:bldP spid="${i}" grpId="0" animBg="1"/>`).join('');
  return `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst><p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst><p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>${eff}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>${bld ? `<p:bldLst>${bld}</p:bldLst>` : ''}</p:timing>`;
}
(async () => {
  const buf = await pres.write({ outputType: 'nodebuffer' });
  const zip = await JSZip.loadAsync(buf);
  for (let i = 1; i <= anim.length; i++) {
    const p = `ppt/slides/slide${i}.xml`; let xml = await zip.file(p).async('string'); const ids = {};
    for (const m of xml.matchAll(/<p:cNvPr id="(\d+)" name="([^"]+)"/g)) ids[m[2]] = m[1];
    xml = xml.replace(/<p:timing>[\s\S]*?<\/p:timing>/, '').replace('</p:clrMapOvr>', '</p:clrMapOvr>' + (i > 1 ? MORPH : '') + timingXml(anim[i - 1], ids));
    zip.file(p, xml);
  }
  for (const name of Object.keys(zip.files)) { if (!name.endsWith('.xml')) continue; let x = await zip.file(name).async('string');
    if (x.includes('Calibri')) { x = x.replace(/Calibri Light/g, 'Onest').replace(/Calibri/g, 'Onest'); zip.file(name, x); } }
  const out = await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
  const file = path.join(OUT, process.env.DECK_NAME || 'Red_Wings_путь_к_2_v5.pptx');
  fs.writeFileSync(file, out); console.log(file, out.length, 'байт,', anim.length, 'слайдов');
})();
