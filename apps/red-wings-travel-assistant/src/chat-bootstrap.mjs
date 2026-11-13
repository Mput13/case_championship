import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { PlaceIndex } from './place-index.mjs';
import { YandexTransportSource } from './transport-sources.mjs';
import { createLocalTransfer } from './local-transfer.mjs';
import { createChatService } from './chat-service.mjs';
import { decorateJourneyResult, scenarioJourney } from './product-services.mjs';
import { loadDemoCatalogue } from './demo-catalogue.mjs';

export async function createLiveChat({ config, snapshot, schedules } = {}) {
  const source = new YandexTransportSource(config);
  const airportCatalog = JSON.parse(await readFile(new URL('../data/service-airports.json', import.meta.url), 'utf8'));
  const places = new PlaceIndex({ source, airportCatalog,
    cachePath: fileURLToPath(new URL('../.runtime/russian-places.json', import.meta.url)) });
  const { createJourneySearch } = await import('./multimodal-search.mjs');
  const { createTripControls } = await import('./trip-controls.mjs');
  const controls = createTripControls({ places, source });
  const demoCatalogue = await loadDemoCatalogue();
  const transfer = createLocalTransfer({ places, walkRoutingEnabled: config.walkRoutingEnabled });
  const live = createJourneySearch({ source, places, transfer });
  const journeySearch = async (trip, { signal } = {}) => {
    const result = trip.network_mode === 'scenario_2027_2028' ? scenarioJourney(trip) : await live.search(trip, { signal });
    return decorateJourneyResult(result, trip);
  };
  const resolvePlaces = async (query, { signal } = {}) => {
    const result = await places.resolve(query, { signal });
    return { ...result, places: result.places.map(p => ({ ...p, stations: [...new Map([p.matched_station,
      ...p.stations.filter(s => s.type === 'airport' || s.station_type === 'train_station' || s.station_type === 'bus_station')]
      .filter(Boolean).map(s => [s.id, s])).values()].slice(0, 12) })) };
  };
  return createChatService({ config, snapshot, schedules, journeySearch, resolvePlaces, controls, demoCatalogue });
}
