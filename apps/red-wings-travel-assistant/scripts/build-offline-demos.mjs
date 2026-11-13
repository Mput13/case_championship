import { writeFile } from 'node:fs/promises';
import { loadDemoCatalogue } from '../src/demo-catalogue.mjs';

// Generate only validated public transport facts; no session IDs or credentials.
const catalogue = await loadDemoCatalogue();
const manifest = catalogue.list();
const demos = Object.fromEntries(manifest.demos.map(entry => {
  const demo = catalogue.get(entry.id);
  const { id, label, checked_at, data_mode } = demo;
  return [id, { ...demo.result, trip: demo.trip, reply_origin: 'prepared',
    demo: { id, label, checked_at, data_mode } }];
}));
await writeFile(new URL('../public-chat/demo-snapshots.json', import.meta.url), JSON.stringify({ ...manifest, snapshots: demos }));
console.log(`Built ${manifest.demos.length} validated offline demos`);
