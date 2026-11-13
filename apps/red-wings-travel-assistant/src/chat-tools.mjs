import { TRIP_PATCH_SCHEMA, assertSchema, applyTripPatch, missingTripFields, departureRange } from './journey-trip.mjs';
import { findJourneyOptions, inspectCorridors, normalizeJourneyGraph } from './journey-graph.mjs';
import { isoDate } from './validation.mjs';
import { abortable, acceptJourneyResult } from './chat-callbacks.mjs';

const empty = { type: 'object', properties: {}, additionalProperties: false };
export const TOOL_SCHEMAS = {
  update_trip: TRIP_PATCH_SCHEMA,
  inspect_corridors: empty,
  inspect_baseline: empty,
  find_journey_options: empty,
  resolve_places: { type: 'object', properties: { query: { type: 'string', minLength: 1, maxLength: 240 } }, required: ['query'], additionalProperties: false },
  query_flights: { type: 'object', properties: {
    from_node: { type: 'string', minLength: 1, maxLength: 120 },
    to_node: { type: 'string', minLength: 1, maxLength: 120 },
    dates: { type: 'array', items: { type: 'string', minLength: 10, maxLength: 10 }, minItems: 1, maxItems: 7, uniqueItems: true },
  }, required: ['from_node', 'to_node', 'dates'], additionalProperties: false },
};
// A dated leg needs its actual times and source, not the provider's calendar
// for every future occurrence. Keep raw evidence in server cards/receipts.
const compactPlan = p => ({ ...p, legs: p.legs.map(({ links, published_calendar, ...l }) => l) });
export function createChatTools({ session, schedules, audit, now, signal, journeySearch, resolvePlaces }) {
  async function search() {
    const missing = missingTripFields(session.trip);
    if (missing.length) return { status: 'needs_input', missing_fields: missing, plans: [] };
    if (!journeySearch) return findJourneyOptions(session.graph, session.trip);
    if ((audit.journey_searches ?? 0) >= 2) return { status: 'partial', plans: [], missing_data: ['Лимит двух общих поисков на сообщение исчерпан; весь пользовательский диапазон сохранён.'] };
    audit.journey_searches = (audit.journey_searches ?? 0) + 1;
    const result = await abortable(Promise.resolve().then(() => journeySearch(structuredClone(session.trip), { signal })), signal);
    if (signal.aborted) throw new Error('aborted');
    return acceptJourneyResult(result, session.trip);
  }
  const implementations = {
    update_trip(args) {
      session.trip = applyTripPatch(session.trip, args, { now: now() });
      session.plans = []; session.search = null;
      return { trip: session.trip, missing_fields: missingTripFields(session.trip) };
    },
    inspect_corridors() { return inspectCorridors(session.graph, session.trip); },
    async resolve_places({ query }) {
      if (!resolvePlaces) return { status: 'partial', places: [...session.graph.nodes.values()].filter(n =>
        `${n.city} ${n.title}`.toLocaleLowerCase('ru').includes(query.toLocaleLowerCase('ru'))).slice(0, 20),
        note: 'Проверены только узлы загруженного графа; общий справочник мест не подключён.' };
      const result = await abortable(Promise.resolve().then(() => resolvePlaces(query, { signal })), signal);
      if (signal.aborted) throw new Error('aborted');
      if (!result) throw new Error('invalid_place_result');
      // Major cities may have hundreds of stations. The model needs identities
      // for disambiguation; the server callback retains the full dictionary.
      const view = Array.isArray(result.places) ? { ...result, places: result.places.slice(0, 20).map(p => ({
        id: p.id, title: p.title, region: p.region, country: p.country,
        station_count: p.stations?.length,
        ...(p.stations ? { stations: p.stations.filter(s => s.type === 'airport').slice(0, 4)
          .concat(p.stations.filter(s => s.type !== 'airport').slice(0, 4)) } : {}),
      })) } : result;
      if (Buffer.byteLength(JSON.stringify(view)) > 60000) throw new Error('invalid_place_result');
      return structuredClone(view);
    },
    async inspect_baseline() {
      const result = session.search ?? await search();
      return { ...result, plans: result.plans.filter(p => !p.requires_red_wings).map(compactPlan),
        note: 'Только наземные варианты для сравнения: поезд, электричка, автобус, трансфер. Авиаперелёты в продукте — только Red Wings. Сохранённый рейс не заменяется.' };
    },
    async find_journey_options() {
      const result = await search();
      session.search = result; session.plans = result.plans;
      return { ...result, plans: result.plans.map(compactPlan) };
    },
    async query_flights(args) {
      if (session.trip.network_mode !== 'current') return { status: 'unavailable', missing_data: ['Live-расписание текущей сети не подставляется в сценарную сеть 2027–2028. Нужен отдельный сценарный источник.'] };
      const range = departureRange(session.trip);
      if (!range || missingTripFields(session.trip).length) return { status: 'needs_input', missing_fields: missingTripFields(session.trip) };
      if (!schedules?.search) return { status: 'unavailable', missing_data: ['Не подключён источник датированных авиарасписаний.'] };
      const from = session.graph.nodes.get(args.from_node), to = session.graph.nodes.get(args.to_node);
      if (!from?.schedule_code || !to?.schedule_code || from.type !== 'airport' || to.type !== 'airport' || from.id === to.id) throw new Error('Для запроса нужны разные аэропорты с кодами источника из графа.');
      if (args.dates.some(d => !isoDate(d) || d < range.from || d > range.to)) throw new Error('Даты запроса должны входить в согласованное окно выезда.');
      if (audit.schedule_days + args.dates.length > 7) return { status: 'partial', code: 'schedule_query_budget',
        note: 'На этот ход исчерпан бюджет семи запросов «пара аэропортов × дата». Пользовательский диапазон сохранён целиком; остальные даты не проверены.' };
      if (signal.aborted) throw new Error('aborted');
      audit.schedule_days += args.dates.length;
      const result = await abortable(schedules.search({ origin: { code: from.schedule_code, iata: from.iata, city: from.city },
        destination: { code: to.schedule_code, iata: to.iata, city: to.city }, dates: args.dates, signal }), signal);
      if (signal.aborted) throw new Error('aborted');
      if (!result || result.unavailable) return { status: 'unavailable', missing_data: [result?.coverage_note ?? 'Источник расписания не вернул данные.'] };
      // Only actual adapter observations for the requested pair/dates may enter the graph.
      const observations = (result.flights ?? []).filter(f => f.origin === from.schedule_code && f.destination === to.schedule_code && args.dates.includes(f.departure?.slice(0, 10))).slice(0, 100);
      const extra = normalizeJourneyGraph({}, { airports: [{ ...from, code: from.schedule_code, name: from.title }, { ...to, code: to.schedule_code, name: to.title }],
        flights: observations, sources: result.sources ?? [], checked_at: result.checked_at, data_mode: schedules.mode ?? 'unknown' });
      for (const l of extra.legs.values()) {
        // Map adapter codes back to the graph's physical nodes.
        session.graph.legs.set(l.id, { ...l, from: from.id, to: to.id, origin: from.title, destination: to.title });
      }
      // Bound session-specific observation storage without discarding base evidence.
      const added = [...session.graph.legs.keys()].filter(id => !session.baseLegIds.has(id));
      for (const id of added.slice(0, Math.max(0, added.length - 200))) session.graph.legs.delete(id);
      session.plans = []; session.search = null;
      return { status: result.complete ? 'ok' : 'partial', observed_leg_ids: [...extra.legs.keys()],
        checked_dates: args.dates, missing_dates: result.missing_dates ?? [],
        coverage_note: result.coverage_note, checked_at: result.checked_at ?? null,
        note: 'Проверена только указанная пара и даты. Это не поиск всех перевозчиков или всех коридоров; полный период поездки не изменён.' };
    },
  };
  const descriptions = {
    update_trip: 'Сохранить только новые явно сообщённые сведения; остальные поля сохраняются. Место: city, region, place_id из справочника, node_id только для конкретной станции, address. Смысл дат: unknown, departure_window (окно выезда), outbound_return (туда/обратно). network_mode current либо scenario_2027_2028; ground_preference public/smart_transfer. max_budget — рубли на всю группу. Не угадывать, не заменять выбранный рейс без просьбы, не требовать все необязательные поля.',
    inspect_corridors: 'Прочитать реальные узлы, коридоры, наземные виды транспорта, источники и пробелы для сохранённой поездки; включает baseline. Никаких сетевых запросов.',
    inspect_baseline: 'Проверить только наземные альтернативы для сравнения: поезд, электричка, автобус, трансфер. Не рассматривает авиарейсы других перевозчиков и не меняет сохранённый рейс.',
    find_journey_options: 'Построить серверные карточки из транспортного графа, проверив ограничения, даты, выбранный рейс и запасы на стыковках. Включает отдельно подписанные baseline без RW. Вызвать после update_trip для поиска.',
    resolve_places: 'Найти реальные города/станции/аэропорты по тексту. Для одинаковых названий показать кандидатов и уточнить регион; не угадывать. Никаких URL или команд.',
    query_flights: 'Запросить расписание только между известными узлами-аэропортами и выбранными датами в согласованном окне. Общий бюджет 7 пар-дней на ход; это не ограничение диапазона пользователя. Не запрашивать лишний SVX–CEK, если проверяемый наземный путь достаточен.',
  };
  return Object.entries(implementations).filter(([name]) => !journeySearch || !['inspect_corridors', 'query_flights'].includes(name)).map(([name, run]) => ({ name, label: name, description: descriptions[name], parameters: TOOL_SCHEMAS[name],
    async execute(_id, args) {
      if (signal.aborted) throw new Error('aborted');
      assertSchema(args, TOOL_SCHEMAS[name]);
      let result;
      try { result = await run(args); }
      catch (error) {
        // Validation errors are authored locally. Adapter errors are never exposed.
        if (['query_flights', 'find_journey_options', 'inspect_baseline', 'resolve_places'].includes(name)) {
          result = { status: 'error', message: 'Источник поиска не ответил корректно. Результат неизвестен; автоматического повтора нет.' };
          if (name === 'find_journey_options') { session.plans = []; session.search = { status: 'partial', plans: [], missing_data: [result.message] }; }
        } else result = { status: 'error', message: error.message };
      }
      audit.tool_events.push({ name, status: result.status ?? 'ok' });
      // Cards stay intact server-side. Bound only the model-facing view so a
      // general search cannot consume the entire MAI request on one tool result.
      let view = result;
      if (Buffer.byteLength(JSON.stringify(view)) > 16000) {
        view = { status: result.status, missing_data: result.missing_data, missing_fields: result.missing_fields,
          note: 'Сокращённое представление для диалога. Полные карточки сохранены на сервере.',
          ...(result.plans ? { plan_ids: result.plans.map(p => p.id), plans: result.plans.slice(0, 3).map(p => ({ id: p.id, title: p.title, status: p.status,
            requires_red_wings: p.requires_red_wings, network_mode: p.network_mode, warnings: p.warnings,
            total_price: p.total_price, total_duration_minutes: p.total_duration_minutes,
            legs: p.legs.map(l => ({ mode: l.mode, origin: l.origin, destination: l.destination, number: l.number,
              departure: l.departure, arrival: l.arrival, evidence_status: l.evidence_status, source_url: l.source_url })) })) } : {}),
          ...(result.places ? { places: result.places.slice(0, 10) } : {}),
          ...(result.corridors ? { corridors: result.corridors.slice(0, 3), endpoint_nodes: result.endpoint_nodes?.slice(0, 10) } : {}) };
        while (Buffer.byteLength(JSON.stringify(view)) > 16000) {
          if (view.plans?.length) view.plans.pop();
          else if (view.corridors?.length) view.corridors.pop();
          else if (view.places?.length) view.places.pop();
          else { view = { status: result.status, note: 'Источник вернул слишком большой ответ для модели. Полные карточки доступны в plans; новых фактов из сокращения не выводить.' }; break; }
        }
      }
      return { content: [{ type: 'text', text: JSON.stringify(view) }], details: {} };
    },
  }));
}
